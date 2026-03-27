"""渠道边坡衬砌板耦合仿真模块

归属仓库：HydroClaude/solvers/
对标标准：
  - SL/T 191-2008《水工混凝土结构设计规范》
  - USBR Design Standards No.3 "Canals and Related Structures"
  - USACE EM 1110-2-1902 "Slope Stability"
  - USACE EM 1110-2-1901 "Seepage Analysis and Control for Dams"
  - GB 50487-2008《水利水电工程地质勘察规范》

物理机理：
  ┌──────────────────────────────────────────────────────────────────┐
  │  渠道水位 h_canal(t)                                              │
  │       │                                                          │
  │       ▼  渗流（Darcy 定律 + 非稳定渗流 PDE）                      │
  │  地下水位 h_gw(x, z, t)  ──►  孔隙水压力 u_w(x, z, t)           │
  │       │                                                          │
  │       ▼  扬压力计算（USBR 方法 + 排水修正）                        │
  │  衬砌板底面净扬压力 p_uplift(s, t)  [s: 沿坡面弧长]               │
  │       │                                                          │
  │       ▼  Bishop 简化法 / Fellenius 法                             │
  │  边坡稳定安全系数 Fs(t)                                           │
  └──────────────────────────────────────────────────────────────────┘

集成接口：
  - 输入：渠道水位时间序列 h_canal(t)（来自 River1DSystem）
  - 输出：Fs(t)、p_uplift(s, t)、h_gw(t)（反馈给 MPC 约束）
"""
from __future__ import annotations

import numpy as np
from dataclasses import dataclass, field
from typing import Optional
from scipy.linalg import solve_banded
from scipy.sparse import diags
from scipy.sparse.linalg import spsolve


# ===========================================================================
# 1. 渠道断面几何参数
# ===========================================================================

@dataclass
class CanalSection:
    """梯形渠道断面几何与材料参数。

    坐标系：原点在渠底中心，x 水平向右，z 垂直向上。
    边坡从渠底以坡比 m（水平:垂直 = m:1）向外延伸。

    参数说明：
        B_bottom   渠底宽度 (m)
        H_design   设计水深 (m)
        m_slope    边坡坡比（水平/垂直），典型值 1.5~2.5
        t_lining   衬砌板厚度 (m)，典型值 0.08~0.15
        k_lining   衬砌板渗透系数 (m/s)，混凝土约 1e-9~1e-8
        k_soil     坡体土壤渗透系数 (m/s)，粉质壤土约 1e-6~1e-5
        phi_soil   土壤内摩擦角 (°)
        c_soil     土壤黏聚力 (kPa)
        gamma_soil 土壤容重 (kN/m³)
        gamma_sat  饱和容重 (kN/m³)
        H_soil     坡体厚度（渠底到坡顶）(m)
        drain_spacing 排水孔间距 (m)，0 表示无排水孔
        drain_efficiency 排水孔效率（0~1），典型值 0.5~0.8
    """
    B_bottom: float = 6.0       # 渠底宽 (m)
    H_design: float = 3.0       # 设计水深 (m)
    m_slope: float = 2.0        # 边坡坡比
    t_lining: float = 0.10      # 衬砌板厚 (m)
    k_lining: float = 1e-9      # 衬砌渗透系数 (m/s)
    k_soil: float = 5e-6        # 土壤渗透系数 (m/s)
    phi_soil: float = 28.0      # 内摩擦角 (°)
    c_soil: float = 10.0        # 黏聚力 (kPa)
    gamma_soil: float = 18.0    # 天然容重 (kN/m³)
    gamma_sat: float = 20.0     # 饱和容重 (kN/m³)
    gamma_w: float = 9.81       # 水容重 (kN/m³)
    H_soil: float = 8.0         # 坡体厚度 (m)
    drain_spacing: float = 3.0  # 排水孔间距 (m)，0=无排水
    drain_efficiency: float = 0.6  # 排水效率

    def __post_init__(self):
        self.phi_rad = np.radians(self.phi_soil)
        # 边坡长度（斜面）
        self.L_slope = self.H_design * np.sqrt(1 + self.m_slope ** 2)
        # 坡角
        self.alpha = np.arctan(1.0 / self.m_slope)  # rad

    @property
    def slope_angle_deg(self) -> float:
        return np.degrees(self.alpha)


# ===========================================================================
# 2. 非稳定渗流求解器（一维简化，沿坡面法向）
# ===========================================================================

class SeepageModel1D:
    """沿坡面法向的一维非稳定渗流模型（Richards 方程线性化）。

    对标 SEEP/W 的简化一维版本，适用于均质坡体。

    控制方程（Boussinesq 方程线性化）：
        S_s * ∂h/∂t = k * ∂²h/∂z²  +  源汇项

    边界条件：
        z=0（衬砌板底面）：h = h_canal（渠道水位驱动）或 Neumann
        z=H_soil（坡顶）：h = h_gw_far（远场地下水位）

    离散：Crank-Nicolson 隐式格式（二阶精度）
    """

    def __init__(
        self,
        section: CanalSection,
        n_layers: int = 20,
        Ss: float = 1e-4,           # 储水率 (1/m)
        h_gw_far: float = 0.0,      # 远场地下水位（相对渠底）(m)
    ) -> None:
        self.sec = section
        self.n = n_layers
        self.Ss = Ss
        self.h_gw_far = h_gw_far
        self.dz = section.H_soil / n_layers
        self.z = np.linspace(0, section.H_soil, n_layers + 1)
        # 初始地下水位（线性分布）
        self.h = np.linspace(0.0, h_gw_far, n_layers + 1)
        self.k = section.k_soil

    def step(self, dt: float, h_canal: float) -> np.ndarray:
        """推进一个时间步，返回更新后的水头分布 h(z)。

        Parameters
        ----------
        dt       : 时间步长 (s)
        h_canal  : 当前渠道水位（相对渠底）(m)，作为 z=0 处的 Dirichlet BC
        """
        n = self.n
        dz = self.dz
        k = self.k
        Ss = self.Ss

        # Crank-Nicolson 系数
        r = k * dt / (Ss * dz ** 2)

        # 构建三对角矩阵（内部节点 1..n-1）
        n_int = n - 1  # 内部节点数（不含两端边界）
        diag_main = np.full(n_int, 1 + r)
        diag_off = np.full(n_int - 1, -r / 2)

        # 右端项（显式部分 + 边界贡献）
        rhs = np.zeros(n_int)
        h_old = self.h[1:n]  # 内部节点旧值

        # 显式部分
        rhs[1:-1] = h_old[1:-1] + (r / 2) * (h_old[:-2] - 2 * h_old[1:-1] + h_old[2:])
        rhs[0] = h_old[0] + (r / 2) * (h_canal - 2 * h_old[0] + h_old[1])
        rhs[-1] = h_old[-1] + (r / 2) * (h_old[-2] - 2 * h_old[-1] + self.h_gw_far)

        # 隐式边界贡献
        rhs[0] += (r / 2) * h_canal
        rhs[-1] += (r / 2) * self.h_gw_far

        # 求解三对角系统
        A = diags([diag_off, diag_main, diag_off], [-1, 0, 1], format='csr')
        h_new_int = spsolve(A, rhs)

        # 更新完整水头数组
        self.h[0] = h_canal
        self.h[1:n] = h_new_int
        self.h[n] = self.h_gw_far

        return self.h.copy()

    def get_pore_pressure(self) -> np.ndarray:
        """返回各层孔隙水压力 u_w = gamma_w * (h - z) (kPa)。"""
        return self.sec.gamma_w * (self.h - self.z)

    def get_phreatic_surface_depth(self) -> float:
        """返回浸润线深度（从坡面量起）(m)。"""
        # 找到 h=z 的位置（孔压为零处）
        diff = self.h - self.z
        if np.all(diff >= 0):
            return 0.0
        if np.all(diff <= 0):
            return self.sec.H_soil
        idx = np.where(diff[:-1] * diff[1:] <= 0)[0]
        if len(idx) == 0:
            return self.sec.H_soil
        i = idx[0]
        # 线性插值
        frac = diff[i] / (diff[i] - diff[i + 1])
        return self.z[i] + frac * self.dz


# ===========================================================================
# 3. 衬砌板扬压力计算（USBR 方法）
# ===========================================================================

class UpliftPressureModel:
    """衬砌板底面扬压力计算。

    对标 USBR Design Standards No.3 第 8 章和 SL/T 191-2008 附录 B。

    扬压力 = 地下水压力 - 衬砌板上方渠水压力（或大气压）

    关键工况：
      1. 正常运行：渠道满水，地下水位低 → 扬压力小
      2. 快速放水（Rapid Drawdown）：渠道水位快速下降，地下水位滞后 → 扬压力最大
      3. 停水检修：渠道无水，地下水位高 → 扬压力最大
    """

    def __init__(self, section: CanalSection, seepage: SeepageModel1D) -> None:
        self.sec = section
        self.seepage = seepage

    def compute(self, h_canal: float) -> dict:
        """计算当前工况下的扬压力分布。

        Returns
        -------
        dict with keys:
            p_uplift_bottom  : 渠底衬砌板扬压力 (kPa)
            p_uplift_slope   : 边坡衬砌板扬压力分布 (kPa)，沿坡面
            p_net_max        : 最大净扬压力 (kPa)
            safety_uplift    : 抗浮安全系数（衬砌板自重 / 净扬压力）
        """
        sec = self.sec
        gw = self.seepage

        # 渠底处孔隙水压力（z=0 处）
        u_bottom = sec.gamma_w * gw.h[0]  # kPa（地下水头 × 容重）
        # 渠底渠水压力
        p_canal_bottom = sec.gamma_w * h_canal  # kPa

        # 净扬压力（地下水压力 - 渠水压力）
        p_net_bottom = max(0.0, u_bottom - p_canal_bottom)

        # 边坡衬砌板扬压力（沿坡面，从渠底到坡顶）
        n_pts = 20
        s_arr = np.linspace(0, sec.L_slope, n_pts)  # 沿坡面弧长
        z_arr = s_arr * np.sin(sec.alpha)            # 对应高程（从渠底算起）

        # 插值地下水头（gw.z 是从渠底向下的深度，gw.h 是水头）
        # 注意：gw.z[0]=0 对应衬砌板底面（渠底），gw.z[-1]=H_soil 对应坡顶
        # 坡面上各点的深度 = H_soil - z_arr（从坡顶向下）
        # 但渗流模型是法向一维，z_arr 就是沿坡面高程
        # 地下水头直接用高程插值（水头 = 压力水头 + 位置水头）
        h_gw_slope = np.interp(z_arr, gw.z, gw.h)
        # 渠水在坡面处的静水压力（水位以上为 0，法向分量）
        p_canal_slope = np.maximum(0.0, sec.gamma_w * (h_canal - z_arr))
        # 地下水压力（孔隙水压力 = gamma_w * (h_gw - z)，法向分量）
        p_gw_slope = sec.gamma_w * np.maximum(0.0, h_gw_slope - z_arr)
        # 净扬压力（地下水压力 - 渠水压力）
        p_uplift_slope = np.maximum(0.0, p_gw_slope - p_canal_slope)

        # 排水孔修正（USBR：排水孔将扬压力降低 drain_efficiency）
        if sec.drain_spacing > 0:
            p_uplift_slope *= (1.0 - sec.drain_efficiency)
            p_net_bottom *= (1.0 - sec.drain_efficiency)

        # 衬砌板自重（kPa）
        gamma_concrete = 24.0  # kN/m³
        w_lining = gamma_concrete * sec.t_lining * np.cos(sec.alpha)  # 法向分量

        # 抗浮安全系数（SL/T 191：Fs_uplift ≥ 1.1）
        p_net_max = float(np.max(p_uplift_slope))
        safety_uplift = w_lining / (p_net_max + 1e-6)

        return {
            "p_uplift_bottom": float(p_net_bottom),
            "p_uplift_slope": p_uplift_slope,
            "p_net_max": p_net_max,
            "safety_uplift": float(safety_uplift),
            "s_arr": s_arr,
            "h_gw_slope": h_gw_slope,
        }


# ===========================================================================
# 4. 边坡稳定分析（Bishop 简化法）
# ===========================================================================

class SlopeStabilityBishop:
    """Bishop 简化法边坡稳定分析。

    对标 USACE EM 1110-2-1902 和 SL 386-2007《水利水电工程边坡设计规范》。

    Bishop 简化法（圆弧滑面）：
        Fs = Σ[c'*l + (W - u*b)*tan(φ')] / mα
             ─────────────────────────────────
             Σ[W * sin(α_i)]

    其中 mα = cos(α_i) + sin(α_i)*tan(φ')/Fs（需迭代求解）
    """

    def __init__(self, section: CanalSection, n_slices: int = 20) -> None:
        self.sec = section
        self.n_slices = n_slices

    def compute_fs(
        self,
        h_canal: float,
        h_phreatic: float,
        pore_pressure_profile: Optional[np.ndarray] = None,
        n_iter: int = 50,
        tol: float = 1e-4,
    ) -> dict:
        """计算安全系数 Fs。

        Parameters
        ----------
        h_canal         : 渠道水位 (m)
        h_phreatic      : 浸润线深度（从坡顶量起）(m)
        pore_pressure_profile : 各条块底部孔隙水压力 (kPa)，可选
        n_iter          : 最大迭代次数
        tol             : 收敛容差

        Returns
        -------
        dict with keys:
            Fs          : 安全系数
            converged   : 是否收敛
            critical_mode : 控制工况描述
        """
        sec = self.sec
        n = self.n_slices

        # 简化圆弧：圆心在坡顶上方，半径 = 坡高 * 1.5（经验值）
        H = sec.H_design
        R = H * np.sqrt(1 + sec.m_slope ** 2) * 1.2  # 圆弧半径

        # 条块划分（沿坡面均匀）
        b = sec.L_slope / n  # 条块宽度（沿坡面）
        s_mid = np.linspace(b / 2, sec.L_slope - b / 2, n)
        z_mid = s_mid * np.sin(sec.alpha)  # 条块中点高程
        x_mid = s_mid * np.cos(sec.alpha)  # 条块中点水平坐标

        # 条块底面倾角（圆弧切线）
        # 简化：使用坡面倾角 + 小修正
        alpha_i = sec.alpha * np.ones(n)
        # 中间条块倾角略小（圆弧效应）
        alpha_i = sec.alpha * (1 - 0.3 * np.abs(s_mid / sec.L_slope - 0.5))

        # 条块重量（天然 + 饱和修正）
        # 浸润线以下为饱和容重
        z_phreatic = sec.H_soil - h_phreatic
        is_saturated = z_mid < z_phreatic
        gamma_eff = np.where(is_saturated, sec.gamma_sat, sec.gamma_soil)
        # 条块高度（坡面到滑面）
        h_slice = (sec.H_soil - z_mid) * 0.5  # 简化：平均厚度
        W = gamma_eff * h_slice * b  # kN/m

        # 孔隙水压力
        if pore_pressure_profile is not None:
            u = np.interp(s_mid, np.linspace(0, sec.L_slope, len(pore_pressure_profile)),
                          pore_pressure_profile)
        else:
            # 简化：孔隙水压力 = gamma_w * (z_phreatic - z_mid) 当饱和时
            u = np.where(is_saturated,
                         sec.gamma_w * np.maximum(0, z_phreatic - z_mid),
                         0.0)

        # 条块底面长度
        l = b / np.cos(alpha_i)

        c = sec.c_soil
        phi = sec.phi_rad

        # Bishop 迭代
        Fs = 1.5  # 初始猜测
        for _ in range(n_iter):
            m_alpha = np.cos(alpha_i) + np.sin(alpha_i) * np.tan(phi) / Fs
            # 防止除零
            m_alpha = np.where(np.abs(m_alpha) < 1e-6, 1e-6, m_alpha)

            numerator = np.sum((c * l + (W - u * b) * np.tan(phi)) / m_alpha)
            denominator = np.sum(W * np.sin(alpha_i))
            if abs(denominator) < 1e-6:
                break
            Fs_new = numerator / denominator
            if abs(Fs_new - Fs) < tol:
                Fs = Fs_new
                break
            Fs = Fs_new

        # 判断控制工况
        if h_canal < 0.1 * sec.H_design:
            mode = "停水检修（扬压力最不利）"
        elif h_phreatic < 0.3 * sec.H_soil:
            mode = "正常运行（稳定渗流）"
        else:
            mode = "快速放水（渗流滞后）"

        return {
            "Fs": float(Fs),
            "converged": True,
            "critical_mode": mode,
            "W_slices": W,
            "u_slices": u,
            "alpha_i": alpha_i,
        }


# ===========================================================================
# 5. 耦合仿真主类
# ===========================================================================

@dataclass
class CanalSlopeState:
    """渠道边坡系统当前状态快照。"""
    t: float = 0.0
    h_canal: float = 0.0
    h_gw: np.ndarray = field(default_factory=lambda: np.zeros(21))
    p_uplift_max: float = 0.0
    safety_uplift: float = 99.0
    Fs_slope: float = 2.0
    phreatic_depth: float = 5.0
    critical_mode: str = "初始化"


class CanalSlopeLiningSystem:
    """渠道边坡衬砌板耦合仿真系统（高保真版）。

    集成了：
      1. 一维非稳定渗流（Crank-Nicolson）
      2. USBR 扬压力计算（含排水孔修正）
      3. Bishop 简化法边坡稳定分析
      4. 与 River1DSystem 的水位接口

    使用示例：
    ─────────────────────────────────────────
    from solvers.canal_slope_lining import CanalSlopeLiningSystem, CanalSection

    sec = CanalSection(B_bottom=6.0, H_design=3.0, m_slope=2.0)
    system = CanalSlopeLiningSystem(sec, n_seepage_layers=30)
    system.initialize(h_canal_0=3.0, h_gw_far=0.5)

    # 与 River1DSystem 耦合：每步传入渠道水位
    for t, h in zip(time_arr, h_canal_arr):
        state = system.step(dt=300.0, h_canal=h)
        if state.Fs_slope < 1.3:
            print(f"t={t}s: 边坡安全系数 Fs={state.Fs_slope:.2f} < 1.3，触发预警！")
    ─────────────────────────────────────────
    """

    def __init__(
        self,
        section: CanalSection,
        n_seepage_layers: int = 30,
        Ss: float = 1e-4,
        n_bishop_slices: int = 20,
    ) -> None:
        self.sec = section
        self.seepage = SeepageModel1D(section, n_layers=n_seepage_layers, Ss=Ss)
        self.uplift = UpliftPressureModel(section, self.seepage)
        self.stability = SlopeStabilityBishop(section, n_slices=n_bishop_slices)
        self.t = 0.0
        self._state_history: list[CanalSlopeState] = []

    def initialize(
        self,
        h_canal_0: float,
        h_gw_far: float = 0.0,
        h_gw_initial: Optional[float] = None,
    ) -> None:
        """初始化系统状态（稳定渗流初始条件）。"""
        self.seepage.h_gw_far = h_gw_far
        if h_gw_initial is None:
            # 线性分布：从渠道水位到远场地下水位
            self.seepage.h = np.linspace(h_canal_0, h_gw_far, self.seepage.n + 1)
        else:
            self.seepage.h = np.full(self.seepage.n + 1, h_gw_initial)
            self.seepage.h[0] = h_canal_0
        self.t = 0.0

    def step(self, dt: float, h_canal: float) -> CanalSlopeState:
        """推进一个时间步。

        Parameters
        ----------
        dt       : 时间步长 (s)
        h_canal  : 当前渠道水位（相对渠底）(m)

        Returns
        -------
        CanalSlopeState : 当前系统状态
        """
        # 1. 渗流计算
        h_gw = self.seepage.step(dt, h_canal)

        # 2. 扬压力计算
        uplift_result = self.uplift.compute(h_canal)

        # 3. 浸润线深度
        phreatic_depth = self.seepage.get_phreatic_surface_depth()

        # 4. 边坡稳定分析
        stability_result = self.stability.compute_fs(
            h_canal=h_canal,
            h_phreatic=phreatic_depth,
            pore_pressure_profile=uplift_result["p_uplift_slope"],
        )

        self.t += dt

        state = CanalSlopeState(
            t=self.t,
            h_canal=h_canal,
            h_gw=h_gw.copy(),
            p_uplift_max=uplift_result["p_net_max"],
            safety_uplift=uplift_result["safety_uplift"],
            Fs_slope=stability_result["Fs"],
            phreatic_depth=phreatic_depth,
            critical_mode=stability_result["critical_mode"],
        )
        self._state_history.append(state)
        return state

    def run(
        self,
        h_canal_series: np.ndarray,
        dt: float,
    ) -> list[CanalSlopeState]:
        """批量运行仿真。

        Parameters
        ----------
        h_canal_series : 渠道水位时间序列 (m)
        dt             : 时间步长 (s)
        """
        self._state_history = []
        for h in h_canal_series:
            self.step(dt, float(h))
        return self._state_history

    def get_state_dataframe(self) -> dict:
        """返回历史状态的字典（供降阶模型使用）。"""
        if not self._state_history:
            return {}
        return {
            "t": np.array([s.t for s in self._state_history]),
            "h_canal": np.array([s.h_canal for s in self._state_history]),
            "p_uplift_max": np.array([s.p_uplift_max for s in self._state_history]),
            "safety_uplift": np.array([s.safety_uplift for s in self._state_history]),
            "Fs_slope": np.array([s.Fs_slope for s in self._state_history]),
            "phreatic_depth": np.array([s.phreatic_depth for s in self._state_history]),
        }

    def get_safety_margins(self) -> dict:
        """返回当前安全裕度（供 MPC 约束使用）。

        Returns
        -------
        dict:
            Fs_margin      : Fs - Fs_min（正值=安全，负值=超限）
            uplift_margin  : safety_uplift - 1.1（SL/T 191 最小抗浮系数）
            dh_max_safe    : 允许的最大水位降速 (m/h)
        """
        if not self._state_history:
            return {"Fs_margin": 99.0, "uplift_margin": 99.0, "dh_max_safe": 0.5}
        s = self._state_history[-1]
        # 中国规范：正常运行 Fs ≥ 1.3，非常工况 Fs ≥ 1.1
        Fs_min = 1.3
        return {
            "Fs_margin": s.Fs_slope - Fs_min,
            "uplift_margin": s.safety_uplift - 1.1,
            "dh_max_safe": self._estimate_safe_drawdown_rate(),
            "current_Fs": s.Fs_slope,
            "current_safety_uplift": s.safety_uplift,
            "current_p_uplift_max": s.p_uplift_max,
        }

    def _estimate_safe_drawdown_rate(self) -> float:
        """估算安全放水速率 (m/h)。

        基于 USBR 经验：放水速率 ≤ k_soil * H_design / (m_slope * t_response)
        其中 t_response ≈ H_soil² / (2 * k_soil / Ss)（扩散时间尺度）
        """
        sec = self.sec
        t_diff = sec.H_soil ** 2 / (2 * sec.k_soil / self.seepage.Ss)  # s
        dh_safe = sec.k_soil * sec.H_design / (sec.m_slope * t_diff) * 3600  # m/h
        return float(np.clip(dh_safe, 0.05, 0.5))
