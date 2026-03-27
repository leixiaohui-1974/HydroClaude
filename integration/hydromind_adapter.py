"""HydroClaude -> HydroMind 协议适配器

归属仓库：HydroClaude/integration/
作用：让 HydroClaude 的高保真求解器实现 hydromind-contracts 定义的标准协议，
      使 HydroMind/HydroClaw 生态中的任何上层模块（调度、控制、ODD、SIL）
      都能通过统一接口调用 HydroClaude 的仿真能力。

实现的协议（来自 hydromind-contracts）：
  - HydraulicSolverProtocol   -> PreissmannUnsteadySolver 适配
  - WaterQualityProtocol      -> River1DSystem 适配
  - LeakDetectorProtocol      -> EKFLeakDetector 适配
  - IdentifierProtocol        -> BLPEnKF 适配

依赖关系：
  HydroClaude（本仓库）
    solvers/preissmann_unsteady_solver.py
    solvers/river1d_system.py
  pipedream-hydrology-integration-lab（外部，可选）
    data_assimilation/assimilation_1d.py
  hydromind-contracts（外部，可选）
    hydromind_contracts.*Protocol
"""
from __future__ import annotations

import sys
import os
from typing import Any, Optional

import numpy as np

# ── HydroClaude 内部导入 ─────────────────────────────────────────────────────
_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _root not in sys.path:
    sys.path.insert(0, _root)

from solvers.preissmann_unsteady_solver import PreissmannUnsteadySolver
from solvers.river1d_system import River1DSystem


# ── pipedream 数据同化模块（可选，运行时导入）────────────────────────────────
def _import_assimilation():
    """延迟导入 pipedream 数据同化模块，避免强依赖。"""
    try:
        pipedream_path = os.path.join(
            os.path.dirname(__file__), "..", "..",
            "pipedream-hydrology-integration-lab"
        )
        if pipedream_path not in sys.path:
            sys.path.insert(0, pipedream_path)
        from data_assimilation.assimilation_1d import (
            BLPEnKF, BackwardLocationProbability,
            EKFLeakDetector, PollutionSourceEstimate, LeakEvent
        )
        return BLPEnKF, BackwardLocationProbability, EKFLeakDetector
    except ImportError:
        return None, None, None


# ===========================================================================
# 1. 水动力求解器适配器
#    实现 hydromind_contracts.HydraulicSolverProtocol
# ===========================================================================

class HydroClaude1DSolverAdapter:
    """将 PreissmannUnsteadySolver 包装为 HydroMind 标准水动力接口。

    使用示例（在 HydroMind/HydroClaw 中）：

        from hydroclaude.integration.hydromind_adapter import HydroClaude1DSolverAdapter

        solver = HydroClaude1DSolverAdapter(
            length=10000, n_nodes=51, width=5.0,
            slope=0.0001, manning_n=0.025
        )
        solver.set_initial_conditions(Q0=10.0, h0=1.5)
        solver.advance(dt=300, Q_upstream=12.0)
        h = solver.get_h_profile()
        state = solver.get_state()
    """

    def __init__(
        self,
        length: float,
        n_nodes: int,
        width: float,
        slope: float,
        manning_n: float,
        theta: float = 0.6,
    ) -> None:
        self._solver = PreissmannUnsteadySolver(
            length=length,
            nx=n_nodes,
            B=width,
            S0=slope,
            n=manning_n,
            theta=theta,
        )
        self._length = length
        self._n_nodes = n_nodes
        self._t = 0.0

    # ── HydraulicSolverProtocol 接口 ─────────────────────────────────────────

    def set_initial_conditions(self, Q0: float, h0: float) -> None:
        self._solver.set_boundary_conditions(Q_upstream=Q0, h_upstream=h0, h_downstream=h0)
        self._solver.initialize_state(h_initial=h0, Q_initial=Q0)

    def get_normal_depth(self, Q: float) -> float:
        """Manning 公式正常水深：h_n = (Q*n / (B*sqrt(S0)))^(3/5)"""
        B = self._solver.B
        S0 = self._solver.S0
        n = self._solver.n
        if S0 <= 0 or B <= 0:
            return 1.0
        # Manning: Q = (1/n)*A*R^(2/3)*S0^(1/2)，矩形断面宽浅渠近似 R≈h
        return float((Q * n / (B * S0 ** 0.5)) ** 0.6)

    def advance(
        self,
        dt: float,
        Q_upstream: float,
        h_downstream: Optional[float] = None,
    ) -> None:
        h_ds = h_downstream if h_downstream is not None else self._solver.h_downstream
        self._solver.set_boundary_conditions(Q_upstream=Q_upstream, h_downstream=h_ds)
        U_new = self._solver.solve_step(self._solver.U_old, dt)
        self._solver.U_old = U_new
        self._t += dt

    def get_h_profile(self) -> np.ndarray:
        return self._solver.get_h()

    def get_state(self) -> dict[str, Any]:
        h = self._solver.get_h()
        Q = self._solver.get_Q()
        g = self._solver.g
        B = self._solver.B
        A = B * h
        Fr = np.where(h > 1e-6, np.abs(Q / A) / np.sqrt(g * h), 0.0)
        return {
            "t": self._t,
            "h": h,
            "Q": Q,
            "x": self._solver.x.copy(),
            "Fr": Fr,
        }

    # ── SuperLink 状态空间接口（供 MPC/KF 使用）─────────────────────────────

    def get_state_matrices(self) -> dict[str, np.ndarray]:
        """返回线性化状态空间矩阵 A, B, C, D（用于 MPC/KF）。

        线性化围绕当前工作点展开：
            delta_xdot = A * delta_x + B * delta_u
            delta_y    = C * delta_x + D * delta_u
        其中 x = [h1...hn, Q1...Qn], u = [Q_in, h_out], y = [h, Q]
        """
        n = self._n_nodes
        # 利用 Preissmann 雅可比矩阵构建线性化状态空间表示
        J = self._solver.compute_jacobian(self._solver.U_old, dt=1.0).toarray()
        n_state = 2 * n
        A = J[:n_state, :n_state]
        B_mat = np.zeros((n_state, 2))
        B_mat[0, 0] = 1.0   # Q_upstream 影响第 0 个方程
        B_mat[-1, 1] = 1.0  # h_downstream 影响最后一个方程
        C_mat = np.eye(n_state)
        return {"A": A, "B": B_mat, "C": C_mat, "D": np.zeros((n_state, 2))}

    def get_reduced_state_matrices(self, n_modes: int = 5) -> dict[str, np.ndarray]:
        """返回 POD 降阶后的状态空间矩阵（供 MPC 使用）。"""
        full = self.get_state_matrices()
        A, B, C = full["A"], full["B"], full["C"]
        # POD：对 A 做特征值分解，保留主要模态
        eigvals, eigvecs = np.linalg.eig(A)
        idx = np.argsort(-np.abs(eigvals))[:n_modes]
        V = eigvecs[:, idx].real
        A_r = V.T @ A @ V
        B_r = V.T @ B
        C_r = C @ V
        return {"A_r": A_r, "B_r": B_r, "C_r": C_r, "V": V, "n_modes": n_modes}


# ===========================================================================
# 2. 水质仿真适配器
#    实现 hydromind_contracts.WaterQualityProtocol
# ===========================================================================

class HydroClaude1DWaterQualityAdapter:
    """将 River1DSystem 包装为 HydroMind 标准水质接口。

    使用示例（在 HydroMind/HydroClaw 中）：

        from hydroclaude.integration.hydromind_adapter import HydroClaude1DWaterQualityAdapter

        wq = HydroClaude1DWaterQualityAdapter(
            length=10000, n_nodes=51, width=5.0,
            slope=0.0001, manning_n=0.025
        )
        wq.set_sources({"node_10": {"BOD": 20.0, "NH4": 5.0}})
        result = wq.simulate(duration=86400, dt=300)
        conc = wq.get_concentrations(["node_10", "node_25", "node_50"])
    """

    def __init__(
        self,
        length: float,
        n_nodes: int,
        width: float,
        slope: float,
        manning_n: float,
        enable_ice: bool = False,
    ) -> None:
        self._system = River1DSystem(
            length=length,
            nx=n_nodes,
            B=width,
            S0=slope,
            n_bed=manning_n,
            enable_ice_cover=enable_ice,
            enable_ice_jam=enable_ice,
        )
        # River1DSystem 需要显式调用 initialize() 才会设置 U_old
        self._system.initialize(h0=1.0, Q0=5.0)
        self._n = n_nodes
        self._x = np.linspace(0, length, n_nodes)
        self._sources: dict[str, dict] = {}
        self._time_series: list[float] = []
        self._conc_history: dict[str, list] = {}

    # ── WaterQualityProtocol 接口 ─────────────────────────────────────────

    def set_sources(self, sources: dict) -> None:
        """配置污染源。

        sources 格式：
            {"node_10": {"BOD": 20.0, "NH4": 5.0, "type": "continuous"}}
        节点名称格式：node_<index>（0-based）
        """
        self._sources = sources
        # 将点源存储在系统的 _point_sources 属性中（如果支持）
        # 否则通过初始条件设置的方式注入
        for node_id, spec in sources.items():
            idx = self._node_id_to_index(node_id)
            if idx is not None:
                for constituent, value in spec.items():
                    if constituent == "BOD" and hasattr(self._system, '_BOD'):
                        self._system._BOD[idx] = float(value)
                    elif constituent == "NH4" and hasattr(self._system, '_NH4'):
                        self._system._NH4[idx] = float(value)
                    elif constituent == "NO3" and hasattr(self._system, '_NO3'):
                        self._system._NO3[idx] = float(value)
                    elif constituent == "DO" and hasattr(self._system, '_DO'):
                        self._system._DO[idx] = float(value)

    def simulate(self, duration: float, dt: float) -> dict:
        """运行水质仿真。"""
        self._time_series = []
        self._conc_history = {
            var: [] for var in ("DO", "BOD", "NH4", "NO3", "TP", "algae", "T_water")
        }

        n_steps = int(duration / dt)
        converged = True

        for _ in range(n_steps):
            try:
                self._system.step(dt=dt)
                t = self._system.t
                self._time_series.append(t)
                state = self._system.get_state()
                # River1DSystem 的 get_state 使用 'Chla' 而非 'algae'，'T' 而非 'T_water'
                var_map = {'algae': 'Chla', 'T_water': 'T'}
                for var in self._conc_history:
                    key = var_map.get(var, var)
                    if key in state:
                        self._conc_history[var].append(state[key].tolist())
                    elif var in state:
                        self._conc_history[var].append(state[var].tolist())
            except Exception:
                converged = False
                break

        return {
            "time_series": self._time_series,
            "concentrations": self._conc_history,
            "converged": converged,
            "n_steps": len(self._time_series),
        }

    def get_concentrations(self, nodes: list[str]) -> dict:
        """获取当前时刻指定节点的浓度。"""
        state = self._system.get_state()
        result = {}
        for node_id in nodes:
            idx = self._node_id_to_index(node_id)
            if idx is None:
                continue
            result[node_id] = {
                "DO": float(state["DO"][idx]) if "DO" in state else None,
                "BOD": float(state["BOD"][idx]) if "BOD" in state else None,
                "NH4": float(state["NH4"][idx]) if "NH4" in state else None,
                "NO3": float(state["NO3"][idx]) if "NO3" in state else None,
                "T_water": float(state["T"][idx]) if "T" in state else None,
                "x": float(self._x[idx]),
            }
        return result

    def get_ice_state(self) -> dict:
        """获取冰期状态（冰盖厚度、复合糙率）。"""
        return self._system.get_ice_state() if hasattr(self._system, "get_ice_state") else {}

    # ── 辅助方法 ──────────────────────────────────────────────────────────

    def _node_id_to_index(self, node_id: str) -> Optional[int]:
        """将节点名称转换为数组索引。"""
        if node_id.startswith("node_"):
            try:
                idx = int(node_id.split("_")[1])
                return min(idx, self._n - 1)
            except (ValueError, IndexError):
                pass
        # 尝试按距离匹配（格式："x=5000"）
        if node_id.startswith("x="):
            try:
                x_target = float(node_id[2:])
                return int(np.argmin(np.abs(self._x - x_target)))
            except ValueError:
                pass
        return None


# ===========================================================================
# 3. 漏水检测适配器
#    实现 hydromind_contracts.LeakDetectorProtocol
# ===========================================================================

class HydroClaude1DLeakDetectorAdapter:
    """将 pipedream.EKFLeakDetector 包装为 HydroMind 标准检测接口。

    使用示例（在 HydroMind/HydroClaw 中）：

        from hydroclaude.integration.hydromind_adapter import HydroClaude1DLeakDetectorAdapter

        detector = HydroClaude1DLeakDetectorAdapter(
            x_nodes=np.linspace(0, 10000, 21),
            Q_nominal=np.full(21, 10.0)
        )
        result = detector.detect({"Q_measured": Q_obs, "t": 3600.0})
        location = detector.localize(result)
    """

    def __init__(
        self,
        x_nodes: np.ndarray,
        Q_nominal: np.ndarray,
        process_noise_std: float = 0.001,
        obs_noise_std: float = 0.005,
        detection_threshold: float = 3.0,
    ) -> None:
        _, _, EKFLeakDetector = _import_assimilation()
        if EKFLeakDetector is None:
            raise ImportError(
                "pipedream data_assimilation 模块未找到。"
                "请确保 pipedream-hydrology-integration-lab 仓库已克隆到同级目录。"
            )
        self._detector = EKFLeakDetector(
            x_nodes=np.asarray(x_nodes),
            Q_nominal=np.asarray(Q_nominal),
            process_noise_std=process_noise_std,
            obs_noise_std=obs_noise_std,
            detection_threshold=detection_threshold,
        )
        self._last_event = None

    # ── LeakDetectorProtocol 接口 ─────────────────────────────────────────

    def detect(self, data: dict) -> dict:
        """检测漏水/偷水事件。

        data 格式：
            {"Q_measured": np.ndarray, "t": float}
        """
        Q_meas = np.asarray(data["Q_measured"])
        t = float(data.get("t", 0.0))
        event = self._detector.update(t=t, Q_measured=Q_meas)
        self._last_event = event
        return {
            "leak_detected": event.detected,
            "magnitude": event.leak_rate,
            "confidence": min(1.0, event.residual_norm / (self._detector.r_std * 10 + 1e-12)),
            "event_type": event.event_type,
            "location_x": event.location_x,
            "water_balance": self._detector.get_water_balance(),
        }

    def localize(self, detection: dict) -> dict:
        """定位漏水/偷水位置。"""
        if self._last_event is None or not detection.get("leak_detected"):
            return {"pipe_id": "unknown", "zone": "unknown", "candidates": []}
        event = self._last_event
        return {
            "pipe_id": f"reach_{event.location_idx}",
            "zone": f"x={event.location_x:.0f}m",
            "candidates": [
                {
                    "reach": f"reach_{event.location_idx}",
                    "x": event.location_x,
                    "score": 1.0,
                }
            ],
        }


# ===========================================================================
# 4. 污染溯源适配器
#    实现 hydromind_contracts.IdentifierProtocol
# ===========================================================================

class HydroClaude1DPollutionSourceAdapter:
    """将 pipedream.BLPEnKF 包装为 HydroMind 标准辨识接口。

    使用示例（在 HydroMind/HydroClaw 中）：

        from hydroclaude.integration.hydromind_adapter import HydroClaude1DPollutionSourceAdapter

        identifier = HydroClaude1DPollutionSourceAdapter(
            x_nodes=np.linspace(0, 10000, 51),
            u=0.5, E=1.0, x_obs_stations=[5000, 8000, 10000]
        )
        result = identifier.identify(
            data={"obs_times": t_arr, "obs_conc": C_arr, "obs_noise_std": 0.1},
            method="BLP-EnKF"
        )
    """

    def __init__(
        self,
        x_nodes: np.ndarray,
        u: float,
        E: float,
        x_obs_stations: list[float],
        area: float = 10.0,
        n_ensemble: int = 100,
    ) -> None:
        BLPEnKF, BackwardLocationProbability, _ = _import_assimilation()
        if BLPEnKF is None:
            raise ImportError(
                "pipedream data_assimilation 模块未找到。"
                "请确保 pipedream-hydrology-integration-lab 仓库已克隆到同级目录。"
            )
        blp = BackwardLocationProbability(
            x_nodes=np.asarray(x_nodes), u=u, E=E
        )
        self._enkf = BLPEnKF(
            blp=blp,
            x_obs_stations=x_obs_stations,
            area=area,
            n_ensemble=n_ensemble,
        )
        self._last_result = None

    # ── IdentifierProtocol 接口 ───────────────────────────────────────────

    def identify(self, data: dict, method: str = "BLP-EnKF") -> dict:
        """执行污染溯源辨识。

        data 格式：
            {"obs_times": np.ndarray,       # 观测时刻 (s)
             "obs_conc": np.ndarray,         # 形状 (n_stations, n_times)
             "obs_noise_std": float,         # 观测噪声标准差
             "prior_x": (float, float),      # 污染源位置先验范围 (m)
             "prior_t": (float, float),      # 释放时刻先验范围 (s)
             "prior_m": (float, float)}      # 污染物质量先验范围 (kg)
        """
        result = self._enkf.identify(
            obs_times=np.asarray(data["obs_times"]),
            obs_conc=np.asarray(data["obs_conc"]),
            obs_noise_std=float(data.get("obs_noise_std", 0.1)),
            prior_x=data.get("prior_x", (0.0, float(self._enkf.blp.x[-1]))),
            prior_t=data.get("prior_t", (0.0, float(data["obs_times"][-1]))),
            prior_m=data.get("prior_m", (1.0, 1000.0)),
        )
        self._last_result = result
        return {
            "parameters": {
                "x_source": result.x_source,
                "t_release": result.t_release,
                "mass": result.mass,
            },
            "uncertainty": {
                "x_std": result.x_std,
                "t_std": result.t_std,
                "mass_std": result.mass_std,
            },
            "fitness": 1.0 / (result.x_std + 1e-6),
            "metadata": {
                "method": method,
                "n_iter": result.n_iter,
                "converged": result.converged,
            },
        }

    def validate(self, model: dict, test_data: dict) -> dict:
        """验证溯源结果（正向模拟对比）。"""
        params = model.get("parameters", {})
        x_src = params.get("x_source", 0.0)
        t_src = params.get("t_release", 0.0)
        mass = params.get("mass", 1.0)

        obs_times = np.asarray(test_data["obs_times"])
        obs_conc = np.asarray(test_data["obs_conc"])

        blp = self._enkf.blp
        C_pred = np.array([
            blp.concentration_from_source(x_src, t_src, mass, t, area=self._enkf.area)
            for t in obs_times
        ])
        if obs_conc.ndim == 2:
            C_obs_mean = obs_conc.mean(axis=0)
        else:
            C_obs_mean = obs_conc

        rmse = float(np.sqrt(np.mean((C_pred - C_obs_mean) ** 2)))
        return {
            "rmse": rmse,
            "correlation": float(np.corrcoef(C_pred, C_obs_mean)[0, 1])
            if len(C_pred) > 1 else 0.0,
            "n_obs": len(obs_times),
        }
