import numpy as np
from core.base import HydraulicComponent
from core.states import ComponentState, HydraulicState
from physics.numerical_methods.rk_solver import RKSolver

class Pipe(HydraulicComponent):
    """
    有压管道组件 - 水击方程

    支持灵活的参数命名，兼容 name/pipe_id
    """

    def __init__(self, name: str = None, length: float = 1000.0,
                 diameter: float = 1.0,
                 wave_speed: float = 1000.0, n_sections: int = 11,
                 method: str = 'rk4',
                 # 额外参数支持（兼容性）
                 pipe_id: str = None, **kwargs):
        """
        初始化管道组件

        Args:
            name: Pipe name (or use pipe_id)
            length: Pipe length (m)
            diameter: Pipe diameter (m)
            wave_speed: Pressure wave speed (m/s)
            n_sections: Number of spatial discretization points
            method: Numerical method ('rk4', 'rk2')
            pipe_id: Alternative parameter for name
            **kwargs: Other parameters for compatibility
        """
        # 参数兼容性处理
        actual_name = name or pipe_id

        super().__init__(name=actual_name, comp_type="pipe", **kwargs)
        self.length = length
        self.diameter = diameter
        self.wave_speed = wave_speed
        self.n_sections = n_sections
        self.method = method

        self.parameters = {
            'roughness': 0.015,
            'wave_speed': wave_speed
        }

        self.state = ComponentState()
        self.hydraulic_state = HydraulicState()
        self.hydraulic_state.P = np.ones(n_sections) * 40.0
        self.hydraulic_state.Q = np.ones(n_sections) * 5.0

        self.dx = length / (n_sections - 1)
        self.x = np.linspace(0, length, n_sections)

        if self.method in ['rk4', 'rk2']:
            self.solver = RKSolver(method=method)

    def update_high_fidelity(self, dt: float, inputs: dict) -> ComponentState:
        """高保真RK求解"""
        if self.method in ['rk4', 'rk2']:
            self.hydraulic_state.P, self.hydraulic_state.Q = self.solver.solve_pipe_step(
                self.hydraulic_state.P, self.hydraulic_state.Q, dt, self.dx,
                self.diameter, self.wave_speed, self.parameters['roughness']
            )

        # Apply boundary conditions from inputs
        if 'upstream_pressure' in inputs:
            self.hydraulic_state.P[0] = inputs['upstream_pressure']
        if 'downstream_flow' in inputs:
            self.hydraulic_state.Q[-1] = inputs['downstream_flow']

        self.state.pressure = np.mean(self.hydraulic_state.P)
        self.state.flow = np.mean(self.hydraulic_state.Q)

        return self.state

    def update_reduced_order(self, dt: float, inputs: dict) -> ComponentState:
        """降阶模型"""
        # 简化：考虑沿程损失
        Q_avg = np.mean(self.hydraulic_state.Q)
        V = Q_avg / (np.pi * (self.diameter/2)**2)

        f = 0.02
        head_loss = f * (self.length / self.diameter) * (V**2 / (2 * 9.81))

        self.state.pressure = self.hydraulic_state.P[0] - head_loss
        self.state.flow = Q_avg

        return self.state

    def get_constraints(self) -> dict:
        return {} # No specific constraints for pipe
