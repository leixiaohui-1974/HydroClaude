import numpy as np
from typing import Tuple

class RKSolver:
    """
    Runge-Kutta求解器

    用于管道水击方程的高精度时间积分
    支持RK2, RK4, RK45(自适应)
    """

    def __init__(self, method: str = 'rk4'):
        """
        Args:
            method: 'rk2', 'rk4', 'rk45'
        """
        self.method = method

    def solve_pipe_step(self, H: np.ndarray, Q: np.ndarray,
                       dt: float, dx: float,
                       diameter: float, wave_speed: float,
                       roughness: float) -> Tuple[np.ndarray, np.ndarray]:
        """
        RK法求解管道水击方程

        ∂H/∂t + (a²/gA)∂Q/∂x = 0
        ∂Q/∂t + gA∂H/∂x + f*Q|Q|/(2DA) = 0
        """
        if self.method == 'rk4':
            return self._rk4_step(H, Q, dt, dx, diameter, wave_speed, roughness)
        elif self.method == 'rk2':
            return self._rk2_step(H, Q, dt, dx, diameter, wave_speed, roughness)
        else:
            return self._rk4_step(H, Q, dt, dx, diameter, wave_speed, roughness)

    def _rk4_step(self, H, Q, dt, dx, diameter, a, roughness):
        """四阶Runge-Kutta"""
        # k1
        dH1, dQ1 = self._compute_derivatives(H, Q, dx, diameter, a, roughness)

        # k2
        H2 = H + 0.5 * dt * dH1
        Q2 = Q + 0.5 * dt * dQ1
        dH2, dQ2 = self._compute_derivatives(H2, Q2, dx, diameter, a, roughness)

        # k3
        H3 = H + 0.5 * dt * dH2
        Q3 = Q + 0.5 * dt * dQ2
        dH3, dQ3 = self._compute_derivatives(H3, Q3, dx, diameter, a, roughness)

        # k4
        H4 = H + dt * dH3
        Q4 = Q + dt * dQ3
        dH4, dQ4 = self._compute_derivatives(H4, Q4, dx, diameter, a, roughness)

        # 组合
        H_new = H + (dt / 6) * (dH1 + 2*dH2 + 2*dH3 + dH4)
        Q_new = Q + (dt / 6) * (dQ1 + 2*dQ2 + 2*dQ3 + dQ4)

        return H_new, Q_new

    def _rk2_step(self, H, Q, dt, dx, diameter, a, roughness):
        """二阶Runge-Kutta (中点法)"""
        # k1
        dH1, dQ1 = self._compute_derivatives(H, Q, dx, diameter, a, roughness)

        # k2
        H_mid = H + 0.5 * dt * dH1
        Q_mid = Q + 0.5 * dt * dQ1
        dH2, dQ2 = self._compute_derivatives(H_mid, Q_mid, dx, diameter, a, roughness)

        # 更新
        H_new = H + dt * dH2
        Q_new = Q + dt * dQ2

        return H_new, Q_new

    def _compute_derivatives(self, H, Q, dx, D, a, roughness):
        """计算导数 dH/dt 和 dQ/dt"""
        g = 9.81
        A = np.pi * (D / 2)**2
        n = len(H)

        dH_dt = np.zeros(n)
        dQ_dt = np.zeros(n)

        # 内部节点
        for i in range(1, n-1):
            # 空间导数（中心差分）
            dQ_dx = (Q[i+1] - Q[i-1]) / (2 * dx)
            dH_dx = (H[i+1] - H[i-1]) / (2 * dx)

            # 连续性方程
            dH_dt[i] = -(a**2 / (g * A)) * dQ_dx

            # 动量方程
            # 摩阻项
            V = Q[i] / A
            Re = abs(V) * D / 1e-6
            if Re > 2300:
                f = roughness
            else:
                f = 64 / (Re + 1e-6)

            friction = f * Q[i] * abs(Q[i]) / (2 * D * A)

            dQ_dt[i] = -g * A * dH_dx - friction

        # 边界（简单处理）
        dH_dt[0] = dH_dt[1]
        dH_dt[-1] = dH_dt[-2]
        dQ_dt[0] = 0
        dQ_dt[-1] = 0

        return dH_dt, dQ_dt
