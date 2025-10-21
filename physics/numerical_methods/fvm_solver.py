import numpy as np
from typing import Tuple

class FVMSolver:
    """
    有限体积法（Finite Volume Method）求解器

    优势:
    - 严格守恒
    - 适合间断问题
    - 支持复杂边界

    守恒型方程:
    ∂U/∂t + ∂F/∂x = S
    U = [A, Q]ᵀ (守恒变量)
    F = [Q, Q²/A + gA²/2]ᵀ (通量)
    S = [0, gA(S₀-Sf)]ᵀ (源项)
    """

    def __init__(self, flux_scheme: str = 'hll', limiter: str = 'minmod'):
        """
        Args:
            flux_scheme: 通量格式 ('hll', 'roe', 'lax-friedrichs')
            limiter: 限制器 ('minmod', 'superbee', 'vanleer')
        """
        self.flux_scheme = flux_scheme
        self.limiter = limiter

    def solve_canal_step(self, A_old: np.ndarray, Q_old: np.ndarray,
                        dt: float, dx: float,
                        width: float, manning_n: float, slope: float,
                        boundary_conditions: dict) -> Tuple[np.ndarray, np.ndarray]:
        """
        FVM求解一步

        有限体积离散:
        U_i^{n+1} = U_i^n - (dt/dx)(F_{i+1/2} - F_{i-1/2}) + dt*S_i
        """
        n = len(A_old)
        g = 9.81

        A_new = A_old.copy()
        Q_new = Q_old.copy()

        # 计算单元中心的守恒变量
        U = np.array([A_old, Q_old])

        # 计算界面通量
        F_interfaces = np.zeros((2, n+1))

        for i in range(n+1):
            if i == 0:
                # 左边界 (ghost cell)
                U_left = U[:, 0]
                if 'upstream_level' in boundary_conditions:
                    h_bc = boundary_conditions['upstream_level']
                    U_left[0] = h_bc * width
                    U_left[1] = U[1, 0] # Neumann for Q
                U_right = U[:, 0]
            elif i == n:
                # 右边界 (ghost cell)
                U_left = U[:, -1]
                U_right = U[:, -1]
                if 'downstream_flow' in boundary_conditions:
                    U_right[1] = boundary_conditions['downstream_flow']
                    U_right[0] = U[0, -1] # Neumann for A
            else:
                # 内部界面: 重构左右状态
                U_left = self._reconstruct_left(U, i, self.limiter)
                U_right = self._reconstruct_right(U, i, self.limiter)

            # 计算界面通量
            F_interfaces[:, i] = self._compute_flux(U_left, U_right, g, width, self.flux_scheme)

        # 更新守恒变量
        for i in range(n):
            # 通量差
            dF = F_interfaces[:, i+1] - F_interfaces[:, i]

            # 源项
            A_i = A_old[i]
            Q_i = Q_old[i]
            h_i = A_i / width

            # 摩阻
            if A_i > 0:
                V_i = Q_i / A_i
                P_wetted = width + 2 * h_i
                R_h = A_i / P_wetted
                if R_h > 0:
                    Sf = (manning_n * V_i)**2 / (R_h**(4/3))
                else:
                    Sf = 0
            else:
                Sf = 0

            S = np.array([0, g * A_i * (slope - Sf)])

            # 更新
            U_new = U[:, i] - (dt / dx) * dF + dt * S

            A_new[i] = U_new[0]
            Q_new[i] = U_new[1]

        # 强制设置边界
        if 'upstream_level' in boundary_conditions:
            A_new[0] = boundary_conditions['upstream_level'] * width
        if 'downstream_flow' in boundary_conditions:
            Q_new[-1] = boundary_conditions['downstream_flow']

        # 限制正值
        A_new = np.maximum(A_new, 0.01 * width)

        return A_new / width, Q_new  # 返回h和Q

    def _reconstruct_left(self, U: np.ndarray, i: int, limiter: str) -> np.ndarray:
        """重构界面左侧状态 (MUSCL格式)"""
        if i == 1:
            return U[:, i-1]

        # 计算梯度
        r = (U[:, i-1] - U[:, i-2]) / (U[:, i] - U[:, i-1] + 1e-10)
        phi = self._limiter_function(r, limiter)

        # 重构
        U_left = U[:, i-1] + 0.5 * phi * (U[:, i] - U[:, i-1])
        return U_left

    def _reconstruct_right(self, U: np.ndarray, i: int, limiter: str) -> np.ndarray:
        """重构界面右侧状态"""
        if i == len(U[0]) - 1:
            return U[:, i]

        r = (U[:, i+1] - U[:, i]) / (U[:, i] - U[:, i-1] + 1e-10)
        phi = self._limiter_function(r, limiter)

        U_right = U[:, i] - 0.5 * phi * (U[:, i] - U[:, i-1])
        return U_right

    def _limiter_function(self, r: np.ndarray, limiter: str) -> np.ndarray:
        """TVD限制器函数"""
        if limiter == 'minmod':
            return np.maximum(0, np.minimum(1, r))
        elif limiter == 'superbee':
            return np.maximum(0, np.maximum(np.minimum(2*r, 1), np.minimum(r, 2)))
        elif limiter == 'vanleer':
            return (r + np.abs(r)) / (1 + np.abs(r))
        else:
            return np.ones_like(r)  # 无限制

    def _compute_flux(self, U_left: np.ndarray, U_right: np.ndarray,
                     g: float, width: float, scheme: str) -> np.ndarray:
        """计算界面数值通量"""
        A_L, Q_L = U_left
        A_R, Q_R = U_right

        # Handle dry states to prevent division by zero
        if A_L <= 1e-6: A_L, Q_L = 0, 0
        if A_R <= 1e-6: A_R, Q_R = 0, 0

        F_L = self._physical_flux(A_L, Q_L, g, width)
        F_R = self._physical_flux(A_R, Q_R, g, width)

        # Wave speed calculations (celerity c = sqrt(g*h))
        h_L = A_L / width if width > 0 else 0
        h_R = A_R / width if width > 0 else 0
        v_L = Q_L / A_L if A_L > 0 else 0
        v_R = Q_R / A_R if A_R > 0 else 0
        c_L = np.sqrt(g * h_L)
        c_R = np.sqrt(g * h_R)

        if scheme == 'lax-friedrichs':
            lambda_max = max(abs(v_L) + c_L, abs(v_R) + c_R)
            F = 0.5 * (F_L + F_R) - 0.5 * lambda_max * (U_right - U_left)
        elif scheme == 'hll':
            S_L = min(v_L - c_L, v_R - c_R)
            S_R = max(v_L + c_L, v_R + c_R)

            if S_L >= 0:
                F = F_L
            elif S_R <= 0:
                F = F_R
            else:
                denominator = S_R - S_L
                if abs(denominator) < 1e-9:
                    F = 0.5 * (F_L + F_R)
                else:
                    F = (S_R*F_L - S_L*F_R + S_L*S_R*(U_right - U_left)) / denominator
        else: # Default to centered flux
            F = 0.5 * (F_L + F_R)

        return F

    def _physical_flux(self, A: float, Q: float, g: float, width: float) -> np.ndarray:
        """物理通量 for a rectangular channel"""
        if A > 1e-6 and width > 0:
            F1 = Q
            F2 = Q**2 / A + 0.5 * g * A**2 / width
        else:
            F1, F2 = 0, 0
        return np.array([F1, F2])
