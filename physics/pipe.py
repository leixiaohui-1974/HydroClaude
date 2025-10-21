import numpy as np

from core.base import HydraulicComponent
from core.enums import ComponentType
from core.states import ComponentState
from physics.numerical_methods.moc_solver import MOCSolver


class Pipe(HydraulicComponent):
    """有压管道 - 水击方程 + MOC"""

    def __init__(self, name: str, length: float, diameter: float,
                 wave_speed: float = 1000.0, n_sections: int = 11):
        super().__init__(name, ComponentType.PIPE)
        self.length = length
        self.diameter = diameter
        self.wave_speed = wave_speed
        self.n_sections = n_sections

        self.parameters = {
            'roughness': 0.015,
            'wave_speed': wave_speed
        }

        # 初始化
        self.hydraulic_state.P = np.ones(n_sections) * 40.0  # 压力水头
        self.hydraulic_state.Q = np.ones(n_sections) * 5.0

        self.dx = length / (n_sections - 1)
        self.x = np.linspace(0, length, n_sections)

    def update_high_fidelity(self, dt: float, mode: str = 'moc') -> ComponentState:
        """
        高保真更新 - MOC求解水击方程
        """
        g = 9.81
        dx = self.dx
        a = self.wave_speed
        A = np.pi * (self.diameter / 2)**2
        n = self.n_sections

        H = self.hydraulic_state.P.copy()
        Q = self.hydraulic_state.Q.copy()

        H_new = np.zeros(n)
        Q_new = np.zeros(n)

        # 内部节点 - MOC
        for i in range(1, n-1):
            # C+ 特征线（从左向右）
            # H_P = H_i-1 - (a/gA)*Q_i-1 - R*Q_i-1*|Q_i-1|*dt
            i_left = i - 1

            # C- 特征线（从右向左）
            # H_N = H_i+1 + (a/gA)*Q_i+1 + R*Q_i+1*|Q_i+1|*dt
            i_right = i + 1

            # 摩阻系数
            V_left = Q[i_left] / A
            Re = abs(V_left) * self.diameter / 1e-6
            if Re > 2300:
                f = 0.02
            else:
                f = 64 / (Re + 1e-6)

            R = f * dx / (2 * self.diameter * A * g)

            # C+ 特征线常数
            C_plus = H[i_left] - (a / (g * A)) * Q[i_left] - R * Q[i_left] * abs(Q[i_left])

            # C- 特征线常数
            C_minus = H[i_right] + (a / (g * A)) * Q[i_right] + R * Q[i_right] * abs(Q[i_right])

            # 联立求解
            H_new[i] = (C_plus + C_minus) / 2
            Q_new[i] = (g * A / (2 * a)) * (C_plus - C_minus)

        # 上游边界
        if self.upstream_boundary:
            H_new[0], Q_new[0] = MOCSolver.solve_pipe_internal_boundary(
                H[1], Q[1], H[0], Q[0],
                self.upstream_boundary, self.wave_speed, A
            )
        else:
            H_new[0] = H[0]
            Q_new[0] = Q[0]

        # 下游边界
        if self.downstream_boundary:
            H_new[-1], Q_new[-1] = MOCSolver.solve_pipe_internal_boundary(
                H[-2], Q[-2], H[-1], Q[-1],
                self.downstream_boundary, self.wave_speed, A
            )
        else:
            H_new[-1] = H[-1]
            Q_new[-1] = Q[-1]

        # 更新状态
        self.hydraulic_state.P = np.clip(H_new, 10.0, 100.0)
        self.hydraulic_state.Q = Q_new

        self.state.pressure = np.mean(self.hydraulic_state.P)
        self.state.flow = np.mean(self.hydraulic_state.Q)

        return self.state

    def update_reduced_order(self, dt: float) -> ComponentState:
        """降阶模型"""
        # 简化：考虑沿程损失
        Q_avg = np.mean(self.hydraulic_state.Q)
        V = Q_avg / (np.pi * (self.diameter/2)**2)

        f = 0.02
        head_loss = f * (self.length / self.diameter) * (V**2 / (2 * 9.81))

        self.state.pressure = self.hydraulic_state.P[0] - head_loss
        self.state.flow = Q_avg

        return self.state
