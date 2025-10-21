import numpy as np
from core.base import HydraulicComponent
from core.states import ComponentState, HydraulicState
from physics.numerical_methods.rk_solver import RKSolver

class Pipe(HydraulicComponent):
    """有压管道 - 水击方程"""

    def __init__(self, name: str, length: float, diameter: float,
                 wave_speed: float = 1000.0, n_sections: int = 11,
                 method: str = 'rk4'):
        super().__init__(name, "pipe")
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
