import numpy as np
from core.base import HydraulicComponent
from core.states import ComponentState, HydraulicState
from physics.moc_solver import MOCSolver
from physics.numerical_methods.preissmann_solver import PreissmannSolver
from physics.numerical_methods.fvm_solver import FVMSolver

class Canal(HydraulicComponent):
    """明渠 - Saint-Venant方程 + MOC"""

    def __init__(self, name: str, volume_min: float, volume_max: float,
                 area: float, length: float, slope: float = 0.0001,
                 n_sections: int = 11, method: str = 'moc'):
        super().__init__(name, "canal")
        self.volume_min = volume_min
        self.volume_max = volume_max
        self.area = area
        self.length = length
        self.slope = slope
        self.n_sections = n_sections
        self.method = method

        self.parameters = {
            'manning_n': 0.025,
            'width': 10.0,
            'area': area
        }

        self.state = ComponentState()
        self.hydraulic_state = HydraulicState()
        self.hydraulic_state.h = np.ones(n_sections) * 5.0
        self.hydraulic_state.Q = np.ones(n_sections) * 5.0

        self.dx = length / (n_sections - 1)
        self.x = np.linspace(0, length, n_sections)

        if self.method == 'preissmann':
            self.solver = PreissmannSolver(theta=0.6)
        elif self.method == 'fvm':
            self.solver = FVMSolver(flux_scheme='hll', limiter='minmod')

    def update_high_fidelity(self, dt: float, inputs: dict) -> ComponentState:
        """高保真MOC求解"""
        if self.method == 'moc':
            g = 9.81
            n = self.n_sections

            h = self.hydraulic_state.h.copy()
            Q = self.hydraulic_state.Q.copy()
            h_new = np.zeros(n)
            Q_new = np.zeros(n)
            c = np.sqrt(g * h)

            # 内部节点
            for i in range(1, n-1):
                n_manning = self.parameters['manning_n']
                width = self.parameters['width']
                A_section = h[i] * width
                P = width + 2 * h[i]
                R = A_section / P if P > 0 else 0

                Sf = 0
                if R > 0 and Q[i] > 0:
                    V = Q[i] / A_section
                    Sf = (n_manning * V)**2 / (R**(4/3))

                C_plus = h[i-1] + ((Q[i-1]/A_section + c[i-1]) / g) * Q[i-1] \
                        - c[i-1] * (Sf - self.slope) * dt
                C_minus = h[i+1] - ((c[i+1] - Q[i+1]/A_section) / g) * Q[i+1] \
                         + c[i+1] * (Sf - self.slope) * dt

                h_new[i] = (C_plus + C_minus) / 2
                Q_new[i] = (g / (2 * c[i])) * (C_plus - C_minus) if c[i] > 0 else Q[i]

            # 边界
            if self.downstream_boundary:
                h_new[-1], Q_new[-1] = MOCSolver.solve_canal_boundary(
                    h[-2], Q[-2], h[-1], Q[-1],
                    self.downstream_boundary, self.dx, dt, self.area
                )
            else:
                h_new[0] = h[0]
                Q_new[0] = Q[0]
                h_new[-1] = h[-1]
                Q_new[-1] = Q[-1]

            self.hydraulic_state.h = np.clip(h_new, 0.1, 20.0)
            self.hydraulic_state.Q = np.clip(Q_new, 0, 100.0)

            self.state.level = np.mean(self.hydraulic_state.h)
            self.state.volume = self.state.level * self.area
            self.state.flow = np.mean(self.hydraulic_state.Q)

        elif self.method == 'preissmann':
            # 设置边界条件
            boundary_conditions = {
                'upstream_flow': inputs.get('upstream_flow', self.hydraulic_state.Q[0]),
                'downstream_level': inputs.get('downstream_level', self.hydraulic_state.h[-1])
            }
            self.hydraulic_state.h, self.hydraulic_state.Q = self.solver.solve_canal_step(
                self.hydraulic_state.h, self.hydraulic_state.Q, dt, self.dx,
                self.parameters['width'], self.parameters['manning_n'], self.slope,
                boundary_conditions
            )
            self.state.level = np.mean(self.hydraulic_state.h)
            self.state.flow = np.mean(self.hydraulic_state.Q)

        elif self.method == 'fvm':
            A = self.hydraulic_state.h * self.parameters['width']
            self.hydraulic_state.h, self.hydraulic_state.Q = self.solver.solve_canal_step(
                A, self.hydraulic_state.Q, dt, self.dx,
                self.parameters['width'], self.parameters['manning_n'], self.slope
            )
            self.state.level = np.mean(self.hydraulic_state.h)
            self.state.flow = np.mean(self.hydraulic_state.Q)

        return self.state

    def update_reduced_order(self, dt: float, inputs: dict) -> ComponentState:
        """降阶模型"""
        inflow = inputs.get('inflow', self.hydraulic_state.Q[0])
        outflow = inputs.get('outflow', self.hydraulic_state.Q[-1])

        dV = (inflow - outflow) * dt
        self.state.volume += dV
        self.state.volume = np.clip(self.state.volume, self.volume_min, self.volume_max)
        self.state.level = self.state.volume / self.area
        self.state.flow = (inflow + outflow) / 2

        return self.state

    def get_constraints(self) -> dict:
        return {
            'volume': (self.volume_min, self.volume_max),
            'level': (self.volume_min / self.area, self.volume_max / self.area)
        }
