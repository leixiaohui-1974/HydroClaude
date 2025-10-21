import numpy as np

from core.base import HydraulicComponent
from core.enums import ComponentType
from core.states import ComponentState
from physics.numerical_methods.moc_solver import MOCSolver


class Canal(HydraulicComponent):
    """明渠 - Saint-Venant方程 + MOC"""

    def __init__(self, name: str, volume_min: float, volume_max: float,
                 area: float, length: float, slope: float = 0.0001,
                 n_sections: int = 11):  # 奇数个节点便于MOC
        super().__init__(name, ComponentType.CANAL)
        self.volume_min = volume_min
        self.volume_max = volume_max
        self.area = area
        self.length = length
        self.slope = slope
        self.n_sections = n_sections

        # 参数
        self.parameters = {
            'manning_n': 0.025,
            'width': 10.0,
            'area': area
        }

        # 初始化空间分布状态
        self.hydraulic_state.h = np.ones(n_sections) * 5.0
        self.hydraulic_state.Q = np.ones(n_sections) * 5.0
        self.hydraulic_state.V = self.hydraulic_state.Q / area

        # 空间离散
        self.dx = length / (n_sections - 1)
        self.x = np.linspace(0, length, n_sections)

    def update_high_fidelity(self, dt: float, mode: str = 'moc') -> ComponentState:
        """
        高保真更新 - MOC求解Saint-Venant方程
        """
        g = 9.81
        dx = self.dx
        n = self.n_sections

        h = self.hydraulic_state.h.copy()
        Q = self.hydraulic_state.Q.copy()

        h_new = np.zeros(n)
        Q_new = np.zeros(n)

        # 波速
        c = np.sqrt(g * h)

        # 内部节点 - MOC特征线法
        for i in range(1, n-1):
            # C+ 特征线（从左侧传播）
            i_left = i - 1
            dt_c_plus = dx / (self.hydraulic_state.V[i_left] + c[i_left])

            # C- 特征线（从右侧传播）
            i_right = i + 1
            dt_c_minus = dx / (c[i_right] - self.hydraulic_state.V[i_right])

            # 实际时间步长
            dt_actual = min(dt, dt_c_plus, dt_c_minus)

            # 摩阻项（Manning）
            n_manning = self.parameters['manning_n']
            width = self.parameters['width']
            A_section = h[i] * width
            P_wetted = width + 2 * h[i]
            R = A_section / P_wetted if P_wetted > 0 else 0

            if R > 0 and Q[i] > 0:
                V = Q[i] / A_section
                Sf = (n_manning * V)**2 / (R**(4/3))
            else:
                Sf = 0

            # C+ 特征线方程
            # dh + (V+c)/g * dQ = -c*(Sf - S0)*dt
            C_plus = h[i_left] + ((self.hydraulic_state.V[i_left] + c[i_left]) / g) * Q[i_left] \
                    - c[i_left] * (Sf - self.slope) * dt_actual

            # C- 特征线方程
            # dh - (c-V)/g * dQ = c*(Sf - S0)*dt
            C_minus = h[i_right] - ((c[i_right] - self.hydraulic_state.V[i_right]) / g) * Q[i_right] \
                     + c[i_right] * (Sf - self.slope) * dt_actual

            # 联立求解
            # h_new[i] = (C_plus + C_minus) / 2
            # Q_new[i] = g/(2*c[i]) * (C_plus - C_minus)

            h_new[i] = (C_plus + C_minus) / 2
            if c[i] > 0:
                Q_new[i] = (g / (2 * c[i])) * (C_plus - C_minus)
            else:
                Q_new[i] = Q[i]

        # 上游边界
        if self.upstream_boundary:
            h_new[0], Q_new[0] = MOCSolver.solve_canal_internal_boundary(
                h[1], Q[1], h[0], Q[0],
                self.upstream_boundary, dx, dt, self.area
            )
        else:
            h_new[0] = h[0]
            Q_new[0] = Q[0]

        # 下游边界
        if self.downstream_boundary:
            h_new[-1], Q_new[-1] = MOCSolver.solve_canal_internal_boundary(
                h[-2], Q[-2], h[-1], Q[-1],
                self.downstream_boundary, dx, dt, self.area
            )
        else:
            h_new[-1] = h[-1]
            Q_new[-1] = Q[-1]

        # 更新状态
        self.hydraulic_state.h = np.clip(h_new, 0.1, 20.0)
        self.hydraulic_state.Q = np.clip(Q_new, 0, 100.0)
        self.hydraulic_state.V = self.hydraulic_state.Q / self.area

        # 更新集总状态
        self.state.level = np.mean(self.hydraulic_state.h)
        self.state.volume = self.state.level * self.area * self.length / self.n_sections
        self.state.flow = np.mean(self.hydraulic_state.Q)

        return self.state

    def update_reduced_order(self, dt: float) -> ComponentState:
        """降阶模型 - 积分延迟"""
        inflow = self.hydraulic_state.Q[0]
        outflow = self.hydraulic_state.Q[-1]

        dV = (inflow - outflow) * dt
        self.state.volume += dV
        self.state.volume = np.clip(self.state.volume, self.volume_min, self.volume_max)
        self.state.level = self.state.volume / self.area
        self.state.flow = (inflow + outflow) / 2

        return self.state
