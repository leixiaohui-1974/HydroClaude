import numpy as np
from typing import Dict, Tuple
from core.component import HydraulicComponent, ComponentType, ComponentState

from physics.numerical_methods.rk_solver import RKSolver

class Pipe(HydraulicComponent):
    """有压管道 - 实现水击方程（MOC）"""

    def __init__(self, name: str, length: float, diameter: float,
                 roughness: float = 0.015, wave_speed: float = 1000.0,
                 method: str = 'rk4', n_sections: int = 51):
        super().__init__(name, ComponentType.PIPE)
        self.length = length
        self.diameter = diameter
        self.roughness = roughness
        self.wave_speed = wave_speed
        self.n_sections = n_sections
        self.method = method

        # 空间离散
        self.dx = length / (n_sections - 1)

        # 空间离散状态
        self.H_nodes = np.ones(self.n_sections) * 40.0
        self.Q_nodes = np.ones(self.n_sections) * self.state.flow

        # 选择求解器
        if method in ['rk4', 'rk2']:
            self.solver = RKSolver(method=method)
        else:
            self.solver = RKSolver()

    def compute_derivatives(self, state_vector: np.ndarray,
                          inputs: Dict[str, float]) -> np.ndarray:
        # This is now handled by the RKSolver
        return np.zeros_like(state_vector)

    def update_state(self, dt: float, inputs: Dict[str, float]) -> ComponentState:
        """简化更新（降阶模型）"""
        flow = inputs.get('flow', 0.0)
        upstream_pressure = inputs.get('upstream_pressure', 40.0)

        self.state.flow = flow

        # 沿程损失（Darcy-Weisbach）
        if flow > 0:
            A = np.pi * (self.diameter / 2)**2
            velocity = flow / A
            Re = velocity * self.diameter / 1e-6
            f = 0.02 if Re > 2300 else 64 / (Re + 1e-6)
            head_loss = f * (self.length / self.diameter) * (velocity**2 / (2 * 9.81))
        else:
            head_loss = 0

        self.state.pressure = max(0, upstream_pressure - head_loss)
        self.state.velocity = self.state.flow / (np.pi * (self.diameter/2)**2)

        return self.state

    def update_state_high_fidelity(self, dt: float, inputs: Dict[str, float]):
        """高保真更新（求解水击方程）"""
        bc = {
            'upstream_pressure': inputs.get('upstream_pressure', self.H_nodes[0]),
            'downstream_flow': inputs.get('outflow', self.Q_nodes[-1])
        }

        self.H_nodes, self.Q_nodes = self.solver.solve_pipe_step(
            self.H_nodes, self.Q_nodes, dt, self.dx,
            self.diameter, self.wave_speed, self.roughness
        )

        # 应用边界条件
        if 'upstream_pressure' in bc:
            self.H_nodes[0] = bc['upstream_pressure']
        if 'downstream_flow' in bc:
            self.Q_nodes[-1] = bc['downstream_flow']

        self.state.pressure = np.mean(self.H_nodes)
        self.state.flow = np.mean(self.Q_nodes)

    def get_constraints(self) -> Dict[str, Tuple[float, float]]:
        max_flow = np.pi * (self.diameter/2)**2 * 5.0  # 最大流速5m/s
        return {
            'flow': (0, max_flow),
            'pressure': (10, 100)
        }

class DistributionPoint(HydraulicComponent):
    """分水口"""

    def __init__(self, name: str, base_flow: float = 0.5):
        super().__init__(name, ComponentType.DISTRIBUTION)
        self.base_flow = base_flow
        self.state.flow = base_flow

    def update_state(self, dt: float, inputs: Dict[str, float]) -> ComponentState:
        # 模拟用水变化
        time_of_day = inputs.get('time', 0.0) % 24
        self.state.flow = self.base_flow * (1 + 0.5 * np.sin(2 * np.pi * time_of_day / 24))
        self.state.flow += np.random.normal(0, 0.05)
        self.state.flow = max(0, self.state.flow)
        return self.state

    def get_constraints(self) -> Dict[str, Tuple[float, float]]:
        return {'flow': (0, self.base_flow * 2)}

    def compute_derivatives(self, state_vector: np.ndarray,
                          inputs: Dict[str, float]) -> np.ndarray:
        return np.zeros(4)
