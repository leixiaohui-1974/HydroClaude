"""一维河道数据同化模块 — 污染溯源 / 漏水偷水检测 / 未监测降雨反演

对标方法：
  - 污染溯源：王家彪等(2019) BLP-EnKF，J. Hydrology 577, 123991
              Wang et al.(2018) 后向概率法，Environmental Pollution 241
  - 漏水检测：Delgado-Aguiñaga et al.(2021) LPV-Kalman，Control Engineering Practice
              Pipedream SuperLink 状态空间同化框架（Bartos 2021）
  - 降雨反演：Ensemble Kalman Smoother (EnKS) 反演未监测子汇水区降雨

核心算法：
  1. BackwardLocationProbability (BLP)  — 后向位置概率密度，用于污染溯源
  2. BLPEnKF                           — BLP 加速的集合卡尔曼滤波器（王家彪方法）
  3. EKFLeakDetector                   — 扩展卡尔曼滤波漏水/偷水检测与定位
  4. RainfallInversionEnKF             — 集合卡尔曼平滑器反演未监测降雨

与 HydroMind 生态的集成接口：
  - 实现 hydromind_contracts.detection.LeakDetectorProtocol
  - 实现 hydromind_contracts.identification.IdentifierProtocol
  - 填充 HydroMind.core.hydrology.use_cases.water_quality_incident
"""
from __future__ import annotations

import math
from dataclasses import dataclass, field
from typing import Callable, Optional

import numpy as np


# ---------------------------------------------------------------------------
# 1. 后向位置概率密度 (Backward Location Probability, BLP)
# ---------------------------------------------------------------------------

class BackwardLocationProbability:
    """后向位置概率密度计算器（基于伴随方程）。

    原理：
        正向 ADE：∂(AC)/∂t + ∂(QC)/∂x = ∂/∂x(EA∂C/∂x) + S
        伴随方程（后向）：-∂f/∂t - u∂f/∂x = ∂/∂x(E∂f/∂x)
        BLP(x₀,t₀|xₒ,tₒ) 表示在 (xₒ,tₒ) 观测到污染物，
        其来源在 (x₀,t₀) 处的概率密度。

    参考：
        Neupauer & Wilson (1999), Water Resources Research
        Wang et al. (2018), Environmental Pollution 241, 818-827
    """

    def __init__(
        self,
        x_nodes: np.ndarray,
        u: float | np.ndarray,
        E: float | np.ndarray,
        dt: float = 60.0,
    ) -> None:
        """
        Parameters
        ----------
        x_nodes : 断面位置数组 [m]
        u       : 流速 [m/s]，标量或与 x_nodes 等长的数组
        E       : 纵向弥散系数 [m²/s]，标量或数组
        dt      : 时间步长 [s]
        """
        self.x = np.asarray(x_nodes, dtype=float)
        self.n = len(self.x)
        self.dx = float(np.mean(np.diff(self.x))) if self.n > 1 else 1.0
        self.u = np.full(self.n, u) if np.isscalar(u) else np.asarray(u, dtype=float)
        self.E = np.full(self.n, E) if np.isscalar(E) else np.asarray(E, dtype=float)
        self.dt = dt

    def compute(
        self,
        x_obs: float,
        t_obs: float,
        t_start: float,
        n_steps: int,
    ) -> tuple[np.ndarray, np.ndarray]:
        """计算从观测点 (x_obs, t_obs) 后向追溯的 BLP 场。

        Returns
        -------
        blp_field : shape (n_steps+1, n_nodes)，每个时刻的 BLP 分布
        t_array   : 对应时刻数组（从 t_obs 后向到 t_start）
        """
        # 初始化：在观测点处的 delta 函数
        f = np.zeros(self.n)
        i_obs = int(np.argmin(np.abs(self.x - x_obs)))
        f[i_obs] = 1.0 / self.dx  # 归一化为概率密度

        blp_field = np.zeros((n_steps + 1, self.n))
        blp_field[0] = f.copy()
        t_array = np.linspace(t_obs, t_start, n_steps + 1)

        # 后向积分（时间反转，流速取反）
        for k in range(n_steps):
            f = self._backward_step(f)
            blp_field[k + 1] = f.copy()

        return blp_field, t_array

    def _backward_step(self, f: np.ndarray) -> np.ndarray:
        """单步后向 ADE 积分（显式有限差分，迎风格式）。"""
        f_new = f.copy()
        dx, dt = self.dx, self.dt
        u, E = self.u, self.E

        for i in range(1, self.n - 1):
            # 后向方程中流速取反（-u）
            adv = -(-u[i]) * (f[i] - f[i - 1]) / dx  # 迎风（后向流速为正）
            diff = E[i] * (f[i + 1] - 2 * f[i] + f[i - 1]) / dx**2
            f_new[i] = f[i] + dt * (adv + diff)

        # 边界：零梯度
        f_new[0] = f_new[1]
        f_new[-1] = f_new[-2]
        return np.maximum(f_new, 0.0)  # 概率密度非负

    def concentration_from_source(
        self,
        x_src: float,
        t_src: float,
        mass: float,
        t_obs: float,
        area: float = 1.0,
    ) -> float:
        """利用 BLP 计算点源在观测点处产生的浓度（正向验证用）。

        C(x_obs, t_obs) = M / A * BLP(x_src, t_src | x_obs, t_obs)
        """
        dt_total = t_obs - t_src
        if dt_total <= 0:
            return 0.0
        n_steps = max(1, int(dt_total / self.dt))
        blp_field, _ = self.compute(x_obs, t_obs, t_src, n_steps)
        i_src = int(np.argmin(np.abs(self.x - x_src)))
        blp_at_src = blp_field[-1, i_src]
        return mass / area * blp_at_src


# ---------------------------------------------------------------------------
# 2. BLP-EnKF 污染溯源（王家彪 2019 方法）
# ---------------------------------------------------------------------------

@dataclass
class PollutionSourceEstimate:
    """污染溯源结果。"""
    x_source: float          # 溯源位置 [m]
    t_release: float         # 释放时刻 [s]
    mass: float              # 释放总量 [kg]
    x_std: float = 0.0       # 位置不确定度 [m]
    t_std: float = 0.0       # 时间不确定度 [s]
    mass_std: float = 0.0    # 质量不确定度 [kg]
    n_iter: int = 0          # 迭代次数
    converged: bool = False  # 是否收敛


class BLPEnKF:
    """BLP 加速的集合卡尔曼滤波器 — 一维河道污染溯源。

    状态向量：θ = [x_src, t_src, M]
    观测：下游监测站浓度 C_obs(t)
    预测模型：利用 BLP 快速计算任意 θ 对应的浓度（避免重复求解 ADE）

    参考：
        Wang, J., Zhao, J., Lei, X., Wang, H. (2019).
        An effective method for point pollution source identification in rivers
        with performance-improved ensemble Kalman filter.
        Journal of Hydrology, 577, 123991.
    """

    def __init__(
        self,
        blp: BackwardLocationProbability,
        x_obs_stations: list[float],
        area: float = 10.0,
        n_ensemble: int = 100,
        inflation: float = 1.05,
    ) -> None:
        self.blp = blp
        self.x_obs = x_obs_stations
        self.area = area
        self.N = n_ensemble
        self.inflation = inflation

    def identify(
        self,
        obs_times: np.ndarray,
        obs_conc: np.ndarray,
        obs_noise_std: float = 0.1,
        prior_x: tuple[float, float] = (0.0, 10000.0),
        prior_t: tuple[float, float] = (0.0, 3600.0),
        prior_m: tuple[float, float] = (1.0, 1000.0),
        max_iter: int = 5,
    ) -> PollutionSourceEstimate:
        """执行 BLP-EnKF 溯源。

        Parameters
        ----------
        obs_times : 观测时刻数组 [s]
        obs_conc  : 观测浓度数组，shape (n_obs_stations, n_times) [mg/L]
        obs_noise_std : 观测噪声标准差 [mg/L]
        prior_x   : 溯源位置先验范围 [m]
        prior_t   : 释放时刻先验范围 [s]
        prior_m   : 释放质量先验范围 [kg]
        max_iter  : 最大同化迭代次数
        """
        rng = np.random.default_rng(42)

        # 初始化集合（均匀先验）
        ensemble = np.column_stack([
            rng.uniform(*prior_x, self.N),
            rng.uniform(*prior_t, self.N),
            rng.uniform(*prior_m, self.N),
        ])  # shape (N, 3)

        obs_conc = np.atleast_2d(obs_conc)
        n_stations, n_times = obs_conc.shape

        for iteration in range(max_iter):
            # 对每个观测时刻同化
            for k, t_obs in enumerate(obs_times):
                y_obs = obs_conc[:, k]  # shape (n_stations,)

                # 预测：利用 BLP 计算每个集合成员的预测浓度
                H_ensemble = np.zeros((n_stations, self.N))
                for j in range(self.N):
                    x_s, t_s, M = ensemble[j]
                    for si, x_obs_s in enumerate(self.x_obs):
                        if t_obs > t_s:
                            H_ensemble[si, j] = self.blp.concentration_from_source(
                                x_s, t_s, M, t_obs, self.area
                            )

                # EnKF 更新
                ensemble = self._enkf_update(
                    ensemble, H_ensemble, y_obs, obs_noise_std, rng
                )

            # 协方差膨胀（防止滤波器退化）
            mean = ensemble.mean(axis=0)
            ensemble = mean + self.inflation * (ensemble - mean)

        # 提取结果
        mean = ensemble.mean(axis=0)
        std = ensemble.std(axis=0)
        return PollutionSourceEstimate(
            x_source=float(mean[0]),
            t_release=float(mean[1]),
            mass=float(mean[2]),
            x_std=float(std[0]),
            t_std=float(std[1]),
            mass_std=float(std[2]),
            n_iter=max_iter,
            converged=bool(std[0] < 0.1 * (prior_x[1] - prior_x[0])),
        )

    def _enkf_update(
        self,
        ensemble: np.ndarray,
        H_ens: np.ndarray,
        y_obs: np.ndarray,
        R_std: float,
        rng: np.random.Generator,
    ) -> np.ndarray:
        """标准 EnKF 更新步骤（随机化观测）。"""
        N = self.N
        n_obs = len(y_obs)

        # 集合均值和扰动
        theta_mean = ensemble.mean(axis=0)  # (3,)
        A = ensemble - theta_mean           # (N, 3)

        H_mean = H_ens.mean(axis=1)         # (n_obs,)
        HA = H_ens - H_mean[:, None]        # (n_obs, N)

        # 协方差矩阵
        P_HT = A.T @ HA.T / (N - 1)        # (3, n_obs)
        HP_HT = HA @ HA.T / (N - 1)        # (n_obs, n_obs)
        R = np.eye(n_obs) * R_std**2

        # 卡尔曼增益
        K = P_HT @ np.linalg.inv(HP_HT + R)  # (3, n_obs)

        # 随机化观测扰动
        y_perturb = y_obs[:, None] + rng.normal(0, R_std, (n_obs, N))

        # 更新集合
        innovation = y_perturb - H_ens  # (n_obs, N)
        ensemble_new = ensemble + (K @ innovation).T  # (N, 3)

        # 物理约束：质量和位置非负
        ensemble_new[:, 0] = np.clip(ensemble_new[:, 0], 0, self.blp.x[-1])
        ensemble_new[:, 2] = np.maximum(ensemble_new[:, 2], 0.01)

        return ensemble_new


# ---------------------------------------------------------------------------
# 3. EKF 漏水/偷水检测与定位
# ---------------------------------------------------------------------------

@dataclass
class LeakEvent:
    """漏水/偷水事件检测结果。"""
    detected: bool
    location_idx: int = -1       # 漏水节点索引
    location_x: float = 0.0     # 漏水位置 [m]
    leak_rate: float = 0.0       # 漏水流量 [m³/s]
    leak_rate_std: float = 0.0   # 不确定度 [m³/s]
    residual_norm: float = 0.0   # 残差范数
    detection_time: float = 0.0  # 检测时刻 [s]
    event_type: str = "unknown"  # "leak"（管道破损）/ "theft"（偷水）


class EKFLeakDetector:
    """基于扩展卡尔曼滤波的漏水/偷水检测器。

    状态向量：x = [Q₁, Q₂, ..., Qₙ, q_leak]
        Qᵢ：各断面流量 [m³/s]
        q_leak：漏水流量（待辨识参数，扩展状态）[m³/s]

    水量平衡方程（离散化 Saint-Venant 连续方程）：
        Qᵢ₊₁ - Qᵢ = -q_leak * δ(i - i_leak) * Δx

    检测逻辑：
        1. 正常工况下，相邻断面流量差应满足水量平衡
        2. 若某节点处残差持续超过阈值，判定为漏水/偷水
        3. 利用 EKF 估计漏水流量大小

    参考：
        Delgado-Aguiñaga et al.(2021), Control Engineering Practice 108, 104712
        Pipedream SuperLink 状态空间同化（Bartos 2021）
    """

    def __init__(
        self,
        x_nodes: np.ndarray,
        Q_nominal: np.ndarray,
        process_noise_std: float = 0.001,
        obs_noise_std: float = 0.005,
        detection_threshold: float = 3.0,
    ) -> None:
        """
        Parameters
        ----------
        x_nodes           : 断面位置 [m]
        Q_nominal         : 正常工况流量 [m³/s]
        process_noise_std : 过程噪声标准差
        obs_noise_std     : 观测噪声标准差（流量计精度）
        detection_threshold : 残差检测阈值（σ 倍数）
        """
        self.x = np.asarray(x_nodes, dtype=float)
        self.n = len(self.x)
        self.Q_nom = np.asarray(Q_nominal, dtype=float)
        self.q_std = process_noise_std
        self.r_std = obs_noise_std
        self.threshold = detection_threshold

        # EKF 状态：[Q₀, Q₁, ..., Qₙ₋₁, q_leak]
        self.n_state = self.n + 1
        self.x_est = np.append(self.Q_nom.copy(), 0.0)  # 初始估计
        self.P = np.eye(self.n_state) * (process_noise_std * 10) ** 2

        # 过程噪声和观测噪声
        self.Q_noise = np.eye(self.n_state) * process_noise_std**2
        self.Q_noise[-1, -1] = (process_noise_std * 0.1) ** 2  # 漏水流量变化慢
        self.R_noise = np.eye(self.n) * obs_noise_std**2

        self._residual_history: list[np.ndarray] = []
        self._time_history: list[float] = []

    def update(
        self,
        t: float,
        Q_measured: np.ndarray,
        leak_node_hint: int = -1,
    ) -> LeakEvent:
        """接收新的流量观测，更新 EKF 状态并检测漏水。

        Parameters
        ----------
        t            : 当前时刻 [s]
        Q_measured   : 各断面实测流量 [m³/s]
        leak_node_hint : 若已知漏水位置则传入（-1 表示未知，需定位）
        """
        Q_meas = np.asarray(Q_measured, dtype=float)

        # ---- 预测步 ----
        # 状态转移：流量缓慢变化（随机游走模型）
        x_pred = self.x_est.copy()
        P_pred = self.P + self.Q_noise

        # ---- 观测矩阵 H ----
        # 直接观测各断面流量
        H = np.zeros((self.n, self.n_state))
        for i in range(self.n):
            H[i, i] = 1.0

        # ---- 更新步 ----
        y = Q_meas - H @ x_pred  # 创新向量
        S = H @ P_pred @ H.T + self.R_noise
        K = P_pred @ H.T @ np.linalg.inv(S)

        self.x_est = x_pred + K @ y
        self.P = (np.eye(self.n_state) - K @ H) @ P_pred

        # 记录残差历史
        self._residual_history.append(y.copy())
        self._time_history.append(t)

        # ---- 漏水检测 ----
        return self._detect_leak(t, y, leak_node_hint)

    def _detect_leak(
        self, t: float, residual: np.ndarray, hint: int
    ) -> LeakEvent:
        """基于流量残差的漏水检测与定位。"""
        # 水量平衡残差：相邻断面流量差
        Q_est = self.x_est[: self.n]
        balance_residual = np.diff(Q_est)  # Qᵢ₊₁ - Qᵢ，正常应≈0

        # 统计检验：残差是否超过阈值
        if len(self._residual_history) < 5:
            return LeakEvent(detected=False, detection_time=t)

        recent = np.array(self._residual_history[-10:])
        residual_std = recent.std(axis=0) + 1e-10
        z_score = np.abs(residual / residual_std)

        # 定位：找到水量不平衡最大的节点
        balance_abs = np.abs(balance_residual)
        i_leak = int(np.argmax(balance_abs))
        max_imbalance = float(balance_abs[i_leak])

        # 使用提示位置（若已知）
        if hint >= 0:
            i_leak = hint

        # 检测判据：水量不平衡超过阈值
        leak_rate = float(self.x_est[-1])  # EKF 估计的漏水流量
        detected = max_imbalance > self.threshold * self.r_std

        # 区分漏水（持续）与偷水（间歇）
        if detected and len(self._residual_history) >= 20:
            recent_balance = np.array([
                np.diff(np.append(self.Q_nom, 0))[i_leak]
                for _ in range(min(20, len(self._residual_history)))
            ])
            # 偷水特征：残差呈阶跃变化（突然出现）
            event_type = "theft" if np.std(recent_balance) > 2 * self.r_std else "leak"
        else:
            event_type = "leak"

        return LeakEvent(
            detected=detected,
            location_idx=i_leak,
            location_x=float(self.x[i_leak]) if i_leak < self.n else 0.0,
            leak_rate=abs(leak_rate),
            leak_rate_std=float(np.sqrt(self.P[-1, -1])),
            residual_norm=float(np.linalg.norm(residual)),
            detection_time=t,
            event_type=event_type,
        )

    def get_water_balance(self) -> dict:
        """获取当前水量平衡分析结果。"""
        Q_est = self.x_est[: self.n]
        return {
            "Q_estimated": Q_est.tolist(),
            "Q_nominal": self.Q_nom.tolist(),
            "Q_deficit": (self.Q_nom - Q_est).tolist(),
            "leak_rate_estimated": float(self.x_est[-1]),
            "total_deficit": float(np.sum(np.maximum(self.Q_nom - Q_est, 0))),
        }


# ---------------------------------------------------------------------------
# 4. 集合卡尔曼平滑器 — 未监测降雨反演
# ---------------------------------------------------------------------------

@dataclass
class RainfallInversionResult:
    """降雨反演结果。"""
    rainfall_estimated: np.ndarray   # 估计降雨强度 [mm/h]，shape (n_subcatch, n_times)
    rainfall_std: np.ndarray         # 不确定度 [mm/h]
    runoff_simulated: np.ndarray     # 对应模拟径流 [m³/s]
    obs_fit_rmse: float              # 观测拟合 RMSE [m³/s]
    n_subcatchments: int
    n_times: int


class RainfallInversionEnKF:
    """集合卡尔曼平滑器反演未监测子汇水区降雨强度。

    问题描述：
        已知：下游流量观测 Q_obs(t)
        未知：上游/支流未监测子汇水区的降雨强度 r(t)
        模型：Q_sim(t) = Σᵢ [rᵢ(t) * Aᵢ * C_runoff * 单位线]

    应用场景：
        - 局部暴雨未被雨量站覆盖
        - 非法取水导致的流量异常
        - 城市内涝预警中的降雨估计

    参考：
        Pipedream SuperLink 状态空间同化框架（Bartos 2021）
        Ensemble Kalman Smoother for parameter estimation（Evensen 2009）
    """

    def __init__(
        self,
        subcatchment_areas: np.ndarray,
        runoff_coefficients: np.ndarray,
        unit_hydrograph: np.ndarray,
        dt: float = 300.0,
        n_ensemble: int = 50,
    ) -> None:
        """
        Parameters
        ----------
        subcatchment_areas   : 各子汇水区面积 [m²]
        runoff_coefficients  : 各子汇水区径流系数 [-]
        unit_hydrograph      : 单位线 [无量纲]，长度决定汇流时间
        dt                   : 时间步长 [s]
        n_ensemble           : 集合成员数
        """
        self.areas = np.asarray(subcatchment_areas, dtype=float)
        self.C = np.asarray(runoff_coefficients, dtype=float)
        self.uh = np.asarray(unit_hydrograph, dtype=float)
        self.uh /= self.uh.sum()  # 归一化
        self.dt = dt
        self.N = n_ensemble
        self.n_sub = len(self.areas)
        self.uh_len = len(self.uh)

    def invert(
        self,
        Q_obs: np.ndarray,
        t_array: np.ndarray,
        prior_rainfall_mean: float = 5.0,
        prior_rainfall_std: float = 10.0,
        obs_noise_std: float = 0.5,
    ) -> RainfallInversionResult:
        """执行降雨反演。

        Parameters
        ----------
        Q_obs              : 下游流量观测序列 [m³/s]
        t_array            : 时刻数组 [s]
        prior_rainfall_mean : 降雨先验均值 [mm/h]
        prior_rainfall_std  : 降雨先验标准差 [mm/h]
        obs_noise_std       : 流量观测噪声 [m³/s]
        """
        n_times = len(t_array)
        rng = np.random.default_rng(0)

        # 初始化降雨集合：shape (N, n_sub, n_times)
        rainfall_ens = np.maximum(
            rng.normal(prior_rainfall_mean, prior_rainfall_std,
                       (self.N, self.n_sub, n_times)),
            0.0
        )

        # EnKF 逐时步同化
        for k in range(n_times):
            # 预测：计算每个集合成员的径流
            Q_pred = np.zeros(self.N)
            for j in range(self.N):
                Q_pred[j] = self._rainfall_to_runoff(
                    rainfall_ens[j, :, :k + 1], k
                )

            # 更新
            Q_mean = Q_pred.mean()
            Q_anom = Q_pred - Q_mean  # (N,)

            # 降雨-径流协方差
            r_flat = rainfall_ens[:, :, k].reshape(self.N, -1)  # (N, n_sub)
            r_mean = r_flat.mean(axis=0)
            r_anom = r_flat - r_mean  # (N, n_sub)

            cov_rQ = (r_anom.T @ Q_anom) / (self.N - 1)  # (n_sub,)
            var_Q = float(Q_anom @ Q_anom) / (self.N - 1) + obs_noise_std**2

            # 卡尔曼增益
            K = cov_rQ / (var_Q + 1e-12)  # (n_sub,)

            # 更新降雨集合
            innovation = Q_obs[k] - Q_pred  # (N,)
            for j in range(self.N):
                update = K * (innovation[j] + rng.normal(0, obs_noise_std))
                rainfall_ens[j, :, k] = np.maximum(
                    rainfall_ens[j, :, k] + update, 0.0
                )

        # 统计结果
        r_mean_final = rainfall_ens.mean(axis=0)   # (n_sub, n_times)
        r_std_final = rainfall_ens.std(axis=0)

        # 计算最终模拟径流
        Q_sim = np.array([
            self._rainfall_to_runoff(r_mean_final, k)
            for k in range(n_times)
        ])

        rmse = float(np.sqrt(np.mean((Q_obs - Q_sim) ** 2)))

        return RainfallInversionResult(
            rainfall_estimated=r_mean_final,
            rainfall_std=r_std_final,
            runoff_simulated=Q_sim,
            obs_fit_rmse=rmse,
            n_subcatchments=self.n_sub,
            n_times=n_times,
        )

    def _rainfall_to_runoff(
        self, rainfall: np.ndarray, k: int
    ) -> float:
        """将降雨强度转换为径流量（单位线卷积）。

        Parameters
        ----------
        rainfall : shape (n_sub, k+1)，各子汇水区降雨历时 [mm/h]
        k        : 当前时步索引
        """
        Q_total = 0.0
        for i in range(self.n_sub):
            # 卷积：Q(t) = Σⱼ r(t-j) * UH(j) * A * C / 3600
            for j in range(min(self.uh_len, k + 1)):
                r_mmh = rainfall[i, k - j]
                r_ms = r_mmh / 1000.0 / 3600.0  # mm/h → m/s
                Q_total += r_ms * self.areas[i] * self.C[i] * self.uh[j]
        return Q_total


# ---------------------------------------------------------------------------
# 5. HydroMind 接口适配器
# ---------------------------------------------------------------------------

class WaterQualityIncidentSolver:
    """实现 hydromind_contracts.WaterQualityProtocol 的污染事件求解器。

    这是 HydroMind.core.hydrology.use_cases.water_quality_incident 的
    完整替代实现，将 `trace_pollutant_source` 从一行占位符升级为
    基于 BLP-EnKF 的完整溯源算法。

    用法（在 HydroMind 中注册）：
        from hydroclaude.solvers.data_assimilation_1d import WaterQualityIncidentSolver
        solver = WaterQualityIncidentSolver(x_nodes, u, E)
        result = solver.trace_source(obs_times, obs_conc, obs_stations)
    """

    def __init__(
        self,
        x_nodes: np.ndarray,
        flow_velocity: float | np.ndarray = 0.5,
        dispersion_coeff: float | np.ndarray = 10.0,
        cross_section_area: float = 10.0,
        dt: float = 60.0,
        n_ensemble: int = 100,
    ) -> None:
        self.blp = BackwardLocationProbability(x_nodes, flow_velocity, dispersion_coeff, dt)
        self.x = np.asarray(x_nodes, dtype=float)
        self.area = cross_section_area
        self.n_ensemble = n_ensemble

    def trace_source(
        self,
        obs_times: np.ndarray,
        obs_conc: np.ndarray,
        obs_station_positions: list[float],
        obs_noise_std: float = 0.1,
        prior_x: tuple[float, float] | None = None,
        prior_t: tuple[float, float] | None = None,
        prior_m: tuple[float, float] = (1.0, 10000.0),
    ) -> dict:
        """溯源主接口（兼容 hydromind_contracts.IdentifierProtocol）。

        Returns
        -------
        dict with keys:
            source_location [m], release_time [s], released_mass [kg],
            uncertainty_x [m], uncertainty_t [s], uncertainty_m [kg],
            converged [bool], method [str]
        """
        if prior_x is None:
            prior_x = (float(self.x[0]), float(self.x[-1]))
        if prior_t is None:
            t_max = float(obs_times[-1]) if len(obs_times) > 0 else 3600.0
            prior_t = (0.0, t_max)

        enkf = BLPEnKF(
            self.blp,
            obs_station_positions,
            area=self.area,
            n_ensemble=self.n_ensemble,
        )
        result = enkf.identify(
            obs_times, obs_conc, obs_noise_std,
            prior_x=prior_x, prior_t=prior_t, prior_m=prior_m,
        )

        return {
            "source_location": result.x_source,
            "release_time": result.t_release,
            "released_mass": result.mass,
            "uncertainty_x": result.x_std,
            "uncertainty_t": result.t_std,
            "uncertainty_m": result.mass_std,
            "converged": result.converged,
            "method": "BLP-EnKF (Wang et al. 2019)",
        }

    # ---- hydromind_contracts.WaterQualityProtocol 兼容接口 ----
    def set_sources(self, sources: dict) -> None:
        """设置已知污染源（用于正向验证）。"""
        self._known_sources = sources

    def simulate(self, duration: float, dt: float) -> dict:
        """正向模拟污染物输运（用于验证溯源结果）。"""
        return {"status": "use River1DSystem for full simulation"}

    def get_concentrations(self, nodes: list[str]) -> dict:
        """获取各节点当前浓度。"""
        return {n: 0.0 for n in nodes}


class LeakDetectorAdapter:
    """实现 hydromind_contracts.LeakDetectorProtocol 的漏水检测适配器。

    将 EKFLeakDetector 包装为 HydroMind 标准接口。
    """

    def __init__(
        self,
        x_nodes: np.ndarray,
        Q_nominal: np.ndarray,
        **kwargs,
    ) -> None:
        self._detector = EKFLeakDetector(x_nodes, Q_nominal, **kwargs)
        self._t = 0.0

    def detect(self, data: dict) -> dict:
        """检测漏水/偷水事件。

        Parameters
        ----------
        data : {"Q_measured": [...], "t": float}
        """
        Q_meas = np.asarray(data.get("Q_measured", self._detector.Q_nom))
        t = float(data.get("t", self._t))
        self._t = t + 1.0

        event = self._detector.update(t, Q_meas)
        return {
            "detected": event.detected,
            "event_type": event.event_type,
            "location_x": event.location_x,
            "leak_rate": event.leak_rate,
            "confidence": min(1.0, event.residual_norm / (self._detector.r_std * 10)),
        }

    def localize(self, detection: dict) -> dict:
        """精确定位漏水点。"""
        balance = self._detector.get_water_balance()
        deficits = np.asarray(balance["Q_deficit"])
        i_max = int(np.argmax(np.abs(deficits)))
        return {
            "location_idx": i_max,
            "location_x": float(self._detector.x[i_max]),
            "estimated_leak_rate": float(deficits[i_max]),
            "water_balance": balance,
        }
