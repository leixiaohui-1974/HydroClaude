import numpy as np
from typing import Tuple

class FVMSolver:
    """
    有限体积法（Finite Volume Method）求解器
    """

    def __init__(self, flux_scheme: str = 'hll', limiter: str = 'minmod'):
        self.flux_scheme = flux_scheme
        self.limiter = limiter

    def solve_canal_step(self, A_old: np.ndarray, Q_old: np.ndarray,
                        dt: float, dx: float,
                        width: float, manning_n: float, slope: float) -> Tuple[np.ndarray, np.ndarray]:
        n = len(A_old)
        g = 9.81

        A_new = A_old.copy()
        Q_new = Q_old.copy()

        U = np.array([A_old, Q_old])

        F_interfaces = np.zeros((2, n+1))

        for i in range(n+1):
            if i == 0:
                U_left = U[:, 0]
                U_right = U[:, 0]
            elif i == n:
                U_left = U[:, -1]
                U_right = U[:, -1]
            else:
                U_left = self._reconstruct_left(U, i, self.limiter)
                U_right = self._reconstruct_right(U, i, self.limiter)

            F_interfaces[:, i] = self._compute_flux(U_left, U_right, g, self.flux_scheme)

        for i in range(n):
            dF = F_interfaces[:, i+1] - F_interfaces[:, i]

            A_i = A_old[i]
            Q_i = Q_old[i]
            h_i = A_i / width

            Sf = 0
            if A_i > 0:
                V_i = Q_i / A_i
                P_wetted = width + 2 * h_i
                R_h = A_i / P_wetted
                if R_h > 0:
                    Sf = (manning_n * V_i)**2 / (R_h**(4/3))

            S = np.array([0, g * A_i * (slope - Sf)])

            U_new = U[:, i] - (dt / dx) * dF + dt * S

            A_new[i] = U_new[0]
            Q_new[i] = U_new[1]

        A_new = np.maximum(A_new, 0.01 * width)

        return A_new / width, Q_new

    def _reconstruct_left(self, U: np.ndarray, i: int, limiter: str) -> np.ndarray:
        if i == 1:
            return U[:, i-1]

        r = (U[:, i-1] - U[:, i-2]) / (U[:, i] - U[:, i-1] + 1e-10)
        phi = self._limiter_function(r, limiter)

        U_left = U[:, i-1] + 0.5 * phi * (U[:, i] - U[:, i-1])
        return U_left

    def _reconstruct_right(self, U: np.ndarray, i: int, limiter: str) -> np.ndarray:
        if i == len(U[0]) - 1:
            return U[:, i]

        r = (U[:, i+1] - U[:, i]) / (U[:, i] - U[:, i-1] + 1e-10)
        phi = self._limiter_function(r, limiter)

        U_right = U[:, i] - 0.5 * phi * (U[:, i] - U[:, i-1])
        return U_right

    def _limiter_function(self, r: np.ndarray, limiter: str) -> np.ndarray:
        if limiter == 'minmod':
            return np.maximum(0, np.minimum(1, r))
        elif limiter == 'superbee':
            return np.maximum(0, np.maximum(np.minimum(2*r, 1), np.minimum(r, 2)))
        elif limiter == 'vanleer':
            return (r + np.abs(r)) / (1 + np.abs(r))
        else:
            return np.ones_like(r)

    def _compute_flux(self, U_left: np.ndarray, U_right: np.ndarray,
                     g: float, scheme: str) -> np.ndarray:
        A_L, Q_L = U_left
        A_R, Q_R = U_right

        if scheme == 'lax-friedrichs':
            F_L = self._physical_flux(A_L, Q_L, g)
            F_R = self._physical_flux(A_R, Q_R, g)

            lambda_max = max(abs(Q_L/A_L) + np.sqrt(g*A_L),
                            abs(Q_R/A_R) + np.sqrt(g*A_R))

            F = 0.5 * (F_L + F_R) - 0.5 * lambda_max * (U_right - U_left)

        elif scheme == 'hll':
            F_L = self._physical_flux(A_L, Q_L, g)
            F_R = self._physical_flux(A_R, Q_R, g)

            S_L = min(Q_L/A_L - np.sqrt(g*A_L), Q_R/A_R - np.sqrt(g*A_R))
            S_R = max(Q_L/A_L + np.sqrt(g*A_L), Q_R/A_R + np.sqrt(g*A_R))

            if S_L >= 0:
                F = F_L
            elif S_R <= 0:
                F = F_R
            else:
                F = (S_R * F_L - S_L * F_R + S_L * S_R * (U_right - U_left)) / (S_R - S_L)

        else:
            F_L = self._physical_flux(A_L, Q_L, g)
            F_R = self._physical_flux(A_R, Q_R, g)
            F = 0.5 * (F_L + F_R)

        return F

    def _physical_flux(self, A: float, Q: float, g: float) -> np.ndarray:
        if A > 0:
            F1 = Q
            F2 = Q**2 / A + 0.5 * g * A**2
        else:
            F1 = 0
            F2 = 0
        return np.array([F1, F2])
