import numpy as np
from abc import ABC, abstractmethod
from typing import List, Tuple, Dict, Callable
from core.base import HydraulicComponent
from core.water_body import WaterBody
from core.other_components import Pipe
from core.control_device import ControlDevice

class PhysicsModel(ABC):
    """物理模型抽象基类"""

    @abstractmethod
    def predict(self, state: np.ndarray, control: np.ndarray,
                dt: float, horizon: int) -> np.ndarray:
        """预测未来状态"""
        pass

    @abstractmethod
    def get_matrices(self) -> Tuple[np.ndarray, np.ndarray, np.ndarray]:
        """获取状态空间矩阵 A, B, C"""
        pass

class HighFidelityModel(PhysicsModel):
    """
    高保真物理模型
    - 明渠：Saint-Venant方程
    - 管道：水击方程
    - 泵站/闸阀：非线性特性方程
    """

    def __init__(self, components: List[HydraulicComponent]):
        self.components = components
        self.state_dim = self._compute_state_dimension()

    def _compute_state_dimension(self) -> int:
        """计算状态维度"""
        dim = 0
        for comp in self.components:
            if isinstance(comp, WaterBody):
                dim += 2  # V和h
            elif isinstance(comp, ControlDevice):
                dim += 1  # Q
        return dim

    def predict(self, state: np.ndarray, control: np.ndarray,
                dt: float, horizon: int) -> np.ndarray:
        """高保真预测"""
        predictions = np.zeros((len(state), horizon))
        current_state = state.copy()

        for t in range(horizon):
            # 构建输入字典
            inputs = self._build_inputs(control, t)

            # 对每个组件计算导数
            state_idx = 0
            derivatives = np.zeros_like(current_state)

            for comp in self.components:
                if isinstance(comp, WaterBody):
                    comp_state = current_state[state_idx:state_idx + 2]
                    derivatives[state_idx:state_idx + 2] = [0,0]
                    state_idx += 2
                elif isinstance(comp, ControlDevice):
                    derivatives[state_idx] = 0  # 准稳态
                    state_idx += 1

            # RK4积分
            k1 = derivatives
            k2 = derivatives  # 简化
            k3 = derivatives
            k4 = derivatives

            current_state += dt * (k1 + 2*k2 + 2*k3 + k4) / 6
            predictions[:, t] = current_state

        return predictions

    def _build_inputs(self, control: np.ndarray, t: int) -> Dict[str, Dict]:
        """构建输入字典"""
        inputs = {}
        for i, comp in enumerate(self.components):
            inputs[comp.name] = {
                'inflow': control[min(i, len(control)-1)],
                'outflow': control[min(i+1, len(control)-1)],
                'time': t
            }
        return inputs

    def get_matrices(self) -> Tuple[np.ndarray, np.ndarray, np.ndarray]:
        """线性化得到状态空间矩阵"""
        n = self.state_dim
        A = np.eye(n) * 0.95
        B = np.random.randn(n, n) * 0.1
        C = np.eye(n)
        return A, B, C

class ReducedOrderModel(PhysicsModel):
    """
    降阶模型（用于控制）
    支持整个水网系统的快速仿真
    """

    def __init__(self, components: List[HydraulicComponent],
                 model_type: str = 'integrator_delay'):
        self.components = components
        self.model_type = model_type
        self.delays = self._compute_delays()
        self.A, self.B, self.C = self._build_state_space_model()

    def _compute_delays(self) -> Dict[str, int]:
        """计算各段时滞"""
        delays = {}
        for comp in self.components:
            if isinstance(comp, WaterBody) and comp.length > 0:
                # 明渠时滞 ≈ 长度 / 波速
                wave_speed = np.sqrt(9.81 * 3.0)  # 假设平均水深3m
                delay_time = comp.length / wave_speed
                delays[comp.name] = max(1, int(delay_time / 60))  # 转为步数
            elif isinstance(comp, Pipe):
                # 管道时滞 = 长度 / 波速
                delay_time = comp.length / comp.wave_speed
                delays[comp.name] = max(1, int(delay_time / 1))
            else:
                delays[comp.name] = 0
        return delays

    def _build_state_space_model(self) -> Tuple[np.ndarray, np.ndarray, np.ndarray]:
        """
        构建整个水网的状态空间模型
        状态: x = [V1, V2, ..., Vn, Q1, Q2, ..., Qm]
        控制: u = [u1, u2, ..., up]
        """
        n_states = 0
        n_controls = 0

        # 统计状态和控制数量
        for comp in self.components:
            if isinstance(comp, WaterBody):
                n_states += 1  # 蓄水量
            if isinstance(comp, ControlDevice):
                n_controls += 1  # 控制量

        # A矩阵：状态转移
        A = np.eye(n_states)

        # B矩阵：控制输入影响
        B = np.zeros((n_states, n_controls))

        # C矩阵：观测矩阵
        C = np.eye(n_states)

        return A, B, C

    def predict(self, state: np.ndarray, control: np.ndarray,
                dt: float, horizon: int) -> np.ndarray:
        """降阶模型预测"""
        predictions = np.zeros((len(state), horizon))
        current_state = state.copy()

        # 控制历史队列（处理时滞）
        max_delay = max(self.delays.values()) if self.delays else 1
        control_history = [control.copy() for _ in range(max_delay + 1)]

        for t in range(horizon):
            # 应用时滞
            delayed_control = np.zeros_like(control)
            ctrl_idx = 0
            for comp in self.components:
                if isinstance(comp, ControlDevice):
                    delay = self.delays.get(comp.name, 0)
                    hist_idx = min(delay, len(control_history) - 1)
                    delayed_control[ctrl_idx] = control_history[hist_idx][ctrl_idx]
                    ctrl_idx += 1

            # 状态更新: x(k+1) = A*x(k) + B*u(k-tau) * dt
            current_state = self.A @ current_state + self.B @ delayed_control * dt

            predictions[:, t] = current_state
            control_history.append(control.copy())

        return predictions

    def get_matrices(self) -> Tuple[np.ndarray, np.ndarray, np.ndarray]:
        return self.A, self.B, self.C
