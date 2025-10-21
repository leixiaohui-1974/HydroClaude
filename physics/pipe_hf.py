import numpy as np
from typing import Tuple
from physics.numerical_methods.rk_solver import RKSolver

class PipeHighFidelity:
    """高精度管道模型"""

    def __init__(self, name: str, length: float, diameter: float,
                 wave_speed: float = 1000.0, roughness: float = 0.02,
                 n_sections: int = 51, method: str = 'rk4'):
        """
        Args:
            method: 'rk4', 'rk2', 'moc'
        """
        self.name = name
        self.length = length
        self.diameter = diameter
        self.wave_speed = wave_speed
        self.roughness = roughness
        self.n_sections = n_sections
        self.method = method

        self.dx = length / (n_sections - 1)
        self.x = np.linspace(0, length, n_sections)

        # 初始化
        self.H = np.ones(n_sections) * 40.0  # 水头
        self.Q = np.ones(n_sections) * 5.0   # 流量

        # 选择求解器
        if method in ['rk4', 'rk2']:
            self.solver = RKSolver(method=method)

        print(f"管道 '{name}' 初始化: 方法={method}, 节点数={n_sections}")

    def step(self, dt: float, boundary_conditions: dict = None) -> dict:
        """前进一步"""
        bc = boundary_conditions or {}

        if self.method in ['rk4', 'rk2']:
            self.H, self.Q = self.solver.solve_pipe_step(
                self.H, self.Q, dt, self.dx,
                self.diameter, self.wave_speed, self.roughness
            )

        # 应用边界条件
        if 'upstream_pressure' in bc:
            self.H[0] = bc['upstream_pressure']
        if 'downstream_flow' in bc:
            self.Q[-1] = bc['downstream_flow']

        return {
            'pressure': np.mean(self.H),
            'flow': np.mean(self.Q)
        }

    def get_profile(self) -> Tuple[np.ndarray, np.ndarray, np.ndarray]:
        """获取分布"""
        return self.x, self.H, self.Q
