import numpy as np
from typing import Dict, Tuple
from core.component import HydraulicComponent, ComponentType, ComponentState

class WaterBody(HydraulicComponent):
    """水体基类（渠池、水库等）"""

    def __init__(self, name: str, comp_type: ComponentType,
                 volume_min: float, volume_max: float,
                 area: float, length: float = 0.0):
        super().__init__(name, comp_type)
        self.volume_min = volume_min
        self.volume_max = volume_max
        self.area = area
        self.length = length
        self.state.volume = (volume_min + volume_max) / 2
        self.state.level = self.state.volume / area

    def get_constraints(self) -> Dict[str, Tuple[float, float]]:
        return {
            'volume': (self.volume_min, self.volume_max),
            'level': (self.volume_min / self.area, self.volume_max / self.area)
        }

    def update_state(self, dt: float, inputs: Dict[str, float]) -> ComponentState:
        """水量平衡更新（降阶模型）"""
        inflow = inputs.get('inflow', 0.0)
        outflow = inputs.get('outflow', 0.0)
        disturbance = inputs.get('disturbance', 0.0)

        self.state.volume += (inflow - outflow - disturbance) * dt
        self.state.volume = np.clip(self.state.volume,
                                    self.volume_min, self.volume_max)
        self.state.level = self.state.volume / self.area if self.area > 0 else 0

        return self.state

    def compute_derivatives(self, state_vector: np.ndarray,
                          inputs: Dict[str, float]) -> np.ndarray:
        """计算导数（高保真模型基础）"""
        inflow = inputs.get('inflow', 0.0)
        outflow = inputs.get('outflow', 0.0)
        disturbance = inputs.get('disturbance', 0.0)

        dV_dt = inflow - outflow - disturbance
        dh_dt = dV_dt / self.area if self.area > 0 else 0

        return np.array([dV_dt, dh_dt, 0, 0])

class Reservoir(WaterBody):
    """水库"""
    def __init__(self, name: str, volume_min: float, volume_max: float, area: float):
        super().__init__(name, ComponentType.RESERVOIR, volume_min, volume_max, area)

from physics.numerical_methods.preissmann_solver import PreissmannSolver
from physics.numerical_methods.fvm_solver import FVMSolver

class Canal(WaterBody):
    """明渠 - 实现Saint-Venant方程"""

    def __init__(self, name: str, volume_min: float, volume_max: float,
                 area: float, length: float, slope: float = 0.0001,
                 width: float = 10.0, manning_n: float = 0.025,
                 method: str = 'fvm', n_sections: int = 51):
        super().__init__(name, ComponentType.CANAL, volume_min, volume_max, area, length)
        self.slope = slope
        self.width = width
        self.manning_n = manning_n
        self.n_sections = n_sections
        self.method = method

        # 空间离散
        self.dx = length / (n_sections - 1)

        # 初始化空间离散状态
        self.h_nodes = np.ones(self.n_sections) * self.state.level
        self.Q_nodes = np.ones(self.n_sections) * self.state.flow

        # 选择求解器
        if method == 'preissmann':
            self.solver = PreissmannSolver()
        elif method == 'fvm':
            self.solver = FVMSolver()
        else:
            self.solver = FVMSolver() # Default

    def compute_derivatives(self, state_vector: np.ndarray,
                          inputs: Dict[str, float]) -> np.ndarray:
        # This is now handled by the solvers
        return np.zeros_like(state_vector)

    def update_state_high_fidelity(self, dt: float, inputs: Dict[str, float]):
        """高保真更新（求解Saint-Venant方程）"""

        bc = {
            'upstream_level': inputs.get('upstream_level', self.h_nodes[0]),
            'downstream_flow': inputs.get('outflow', self.Q_nodes[-1])
        }

        if self.method == 'preissmann':
            self.h_nodes, self.Q_nodes = self.solver.solve_canal_step(
                self.h_nodes, self.Q_nodes, dt, self.dx,
                self.width, self.manning_n, self.slope, bc
            )
        elif self.method == 'fvm':
            A_nodes = self.h_nodes * self.width
            self.h_nodes, self.Q_nodes = self.solver.solve_canal_step(
                A_nodes, self.Q_nodes, dt, self.dx,
                self.width, self.manning_n, self.slope, bc
            )

        # 更新平均状态
        self.state.level = np.mean(self.h_nodes)
        self.state.volume = self.state.level * self.area
        self.state.flow = np.mean(self.Q_nodes)

class SettlingBasin(WaterBody):
    """稳流池"""
    def __init__(self, name: str, volume_min: float, volume_max: float, area: float):
        super().__init__(name, ComponentType.SETTLING_BASIN, volume_min, volume_max, area)

class StorageTank(WaterBody):
    """调蓄池/高位水池"""
    def __init__(self, name: str, volume_min: float, volume_max: float, area: float):
        super().__init__(name, ComponentType.STORAGE_TANK, volume_min, volume_max, area)
