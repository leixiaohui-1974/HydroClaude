import numpy as np
from typing import Tuple
from physics.numerical_methods.preissmann_solver import PreissmannSolver
from physics.numerical_methods.fvm_solver import FVMSolver

class CanalHighFidelity:
    """
    高精度明渠模型
    集成多种数值方法
    """

    def __init__(self, name: str, length: float, width: float,
                 volume_min: float, volume_max: float,
                 slope: float = 0.0001, manning_n: float = 0.025,
                 n_sections: int = 51, method: str = 'preissmann'):
        """
        Args:
            method: 'preissmann', 'fvm', 'moc'
        """
        self.name = name
        self.length = length
        self.width = width
        self.volume_min = volume_min
        self.volume_max = volume_max
        self.slope = slope
        self.manning_n = manning_n
        self.n_sections = n_sections
        self.method = method

        # 空间离散
        self.dx = length / (n_sections - 1)
        self.x = np.linspace(0, length, n_sections)

        # 初始化状态
        self.h = np.ones(n_sections) * 5.0
        self.Q = np.ones(n_sections) * 5.0
        self.A = self.h * width

        # 选择求解器
        if method == 'preissmann':
            self.solver = PreissmannSolver(theta=0.6)
        elif method == 'fvm':
            self.solver = FVMSolver(flux_scheme='hll', limiter='minmod')
        else:
            self.solver = PreissmannSolver(theta=0.6)

        print(f"明渠 '{name}' 初始化: 方法={method}, 节点数={n_sections}")

    def step(self, dt: float, boundary_conditions: dict = None) -> dict:
        """
        前进一步

        Args:
            dt: 时间步长
            boundary_conditions: {'upstream_level': 5.0, 'downstream_flow': 4.0}
        """
        bc = boundary_conditions or {}

        if self.method == 'preissmann':
            self.h, self.Q = self.solver.solve_canal_step(
                self.h, self.Q, dt, self.dx,
                self.width, self.manning_n, self.slope, bc
            )
        elif self.method == 'fvm':
            self.h, self.Q = self.solver.solve_canal_step(
                self.A, self.Q, dt, self.dx,
                self.width, self.manning_n, self.slope, bc
            )

        self.A = self.h * self.width

        return {
            'level': np.mean(self.h),
            'flow': np.mean(self.Q),
            'volume': np.sum(self.A) * self.dx
        }

    def get_profile(self) -> Tuple[np.ndarray, np.ndarray, np.ndarray]:
        """获取空间分布"""
        return self.x, self.h, self.Q
