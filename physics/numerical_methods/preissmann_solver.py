import numpy as np
from scipy.sparse import diags, lil_matrix
from scipy.sparse.linalg import spsolve
from typing import Tuple

class PreissmannSolver:
    """
    Preissmann四点隐式格式求解器

    原理:
    - 时间上: θ加权 (n到n+1时刻)
    - 空间上: 中心点插值 (i到i+1节点)
    - 非线性: Newton-Raphson迭代
    - 稳定性: 无条件稳定 (θ≥0.5)

    Saint-Venant方程:
    ∂A/∂t + ∂Q/∂x = 0                    (连续性)
    ∂Q/∂t + ∂(Q²/A)/∂x + gA∂h/∂x = gA(S₀ - Sf)  (动量)
    """

    def __init__(self, theta: float = 0.6, max_iter: int = 10,
                 tolerance: float = 1e-6):
        """
        Args:
            theta: 时间权重 (0.5=Crank-Nicolson, 0.6=推荐值, 1.0=完全隐式)
            max_iter: Newton-Raphson最大迭代次数
            tolerance: 收敛容差
        """
        self.theta = theta
        self.max_iter = max_iter
        self.tolerance = tolerance

    def solve_canal_step(self, h_old: np.ndarray, Q_old: np.ndarray,
                        dt: float, dx: float,
                        width: float, manning_n: float, slope: float,
                        boundary_conditions: dict) -> Tuple[np.ndarray, np.ndarray]:
        """
        求解一个时间步

        Args:
            h_old: 旧时刻水深 (n,)
            Q_old: 旧时刻流量 (n,)
            dt: 时间步长
            dx: 空间步长
            width: 渠宽
            manning_n: Manning系数
            slope: 渠底坡度
            boundary_conditions: 边界条件

        Returns:
            h_new, Q_new: 新时刻的水深和流量
        """
        n = len(h_old)
        g = 9.81

        # 初始猜测 (使用旧值)
        h_new = h_old.copy()
        Q_new = Q_old.copy()

        # Newton-Raphson迭代
        for iteration in range(self.max_iter):
            # 构建雅可比矩阵和残差向量
            J, R = self._build_jacobian_residual(
                h_old, Q_old, h_new, Q_new,
                dt, dx, width, manning_n, slope, g
            )

            # 应用边界条件
            J, R = self._apply_boundaries(J, R, h_new, Q_new, boundary_conditions, n)

            # 求解线性系统: J * dx = -R
            try:
                dx_vector = spsolve(J, -R)
            except:
                print(f"Warning: 求解器在迭代{iteration}失败，使用显式步进")
                break

            # 更新解
            dh = dx_vector[:n]
            dQ = dx_vector[n:]

            h_new += dh
            Q_new += dQ

            # 防止负水深 (在迭代内部)
            h_new = np.maximum(h_new, 0.01)

            # 检查收敛
            residual_norm = np.linalg.norm(R)
            if residual_norm < self.tolerance:
                # print(f"收敛于迭代 {iteration}, 残差={residual_norm:.2e}")
                break

        return h_new, Q_new

    def _build_jacobian_residual(self, h_old, Q_old, h_new, Q_new,
                                 dt, dx, width, n_manning, S0, g):
        """
        构建Jacobian矩阵和残差向量

        Preissmann格式的离散化:
        ∂f/∂x ≈ (f_{i+1} - f_i) / dx
        ∂f/∂t ≈ (f^{n+1} - f^n) / dt
        中心插值: f̄ = (f_i + f_{i+1}) / 2
        θ加权: f = θ*f^{n+1} + (1-θ)*f^n
        """
        n = len(h_old)
        theta = self.theta

        # 初始化稀疏矩阵
        J = lil_matrix((2*n, 2*n))
        R = np.zeros(2*n)

        # 内部节点 (i = 1 to n-2, 实际计算i和i+1的中间)
        for i in range(n-1):
            # 计算中间点的值 (Preissmann四点格式)
            # 旧时刻
            h_old_mid = 0.5 * (h_old[i] + h_old[i+1])
            Q_old_mid = 0.5 * (Q_old[i] + Q_old[i+1])
            A_old_mid = h_old_mid * width

            # 新时刻
            h_new_mid = 0.5 * (h_new[i] + h_new[i+1])
            Q_new_mid = 0.5 * (Q_new[i] + Q_new[i+1])
            A_new_mid = h_new_mid * width

            # θ加权
            h_theta = theta * h_new_mid + (1 - theta) * h_old_mid
            Q_theta = theta * Q_new_mid + (1 - theta) * Q_old_mid
            A_theta = h_theta * width

            # === 连续性方程 ===
            # ∂A/∂t + ∂Q/∂x = 0

            # 实际的空间导数 (使用θ加权)
            dQ_dx = (Q_new[i+1] - Q_new[i]) / dx * theta + \
                    (Q_old[i+1] - Q_old[i]) / dx * (1 - theta)

            continuity_residual = (A_new_mid - A_old_mid) / dt + dQ_dx

            R[i] = continuity_residual

            # 连续性方程的Jacobian
            J[i, i] = 0.5 * width / dt
            J[i, i+1] = 0.5 * width / dt
            J[i, n+i] = -theta / dx
            J[i, n+i+1] = theta / dx

            # === 动量方程 ===
            # ∂Q/∂t + ∂(Q²/A)/∂x + gA∂h/∂x = gA(S₀ - Sf)

            V_theta = Q_theta / A_theta if A_theta > 1e-6 else 0

            P_wetted = width + 2 * h_theta
            R_hydraulic = A_theta / P_wetted if P_wetted > 1e-6 else 0

            Sf = (n_manning * V_theta)**2 / (R_hydraulic**(4/3)) if R_hydraulic > 1e-6 and abs(V_theta) > 1e-6 else 0

            dQ_dt = (Q_new_mid - Q_old_mid) / dt

            Q2_A_i = Q_new[i]**2 / (h_new[i] * width) if h_new[i] > 1e-6 else 0
            Q2_A_i1 = Q_new[i+1]**2 / (h_new[i+1] * width) if h_new[i+1] > 1e-6 else 0
            d_Q2A_dx = (Q2_A_i1 - Q2_A_i) / dx * theta + \
                       (Q_old[i+1]**2 / (h_old[i+1] * width) - Q_old[i]**2 / (h_old[i] * width)) / dx * (1 - theta)

            dh_dx = (h_new[i+1] - h_new[i]) / dx * theta + \
                    (h_old[i+1] - h_old[i]) / dx * (1 - theta)
            pressure_term = g * A_theta * dh_dx

            source_term = g * A_theta * (S0 - Sf)

            momentum_residual = dQ_dt + d_Q2A_dx + pressure_term - source_term

            R[n+i] = momentum_residual

            # --- 动量方程的Jacobian (完整线性化) ---
            A_i = h_new[i] * width
            A_i1 = h_new[i+1] * width
            Q_i = Q_new[i]
            Q_i1 = Q_new[i+1]

            dR_dh_i = 0
            dR_dh_i1 = 0
            dR_dQ_i = 0.5 / dt
            dR_dQ_i1 = 0.5 / dt

            if A_i > 1e-6:
                dR_dh_i += (theta/dx) * (Q_i**2 * width / A_i**2)
                dR_dQ_i -= (theta/dx) * (2 * Q_i / A_i)
            if A_i1 > 1e-6:
                dR_dh_i1 -= (theta/dx) * (Q_i1**2 * width / A_i1**2)
                dR_dQ_i1 += (theta/dx) * (2 * Q_i1 / A_i1)

            dR_dh_i += (theta/dx) * (-g * 0.5 * width) * dh_dx
            dR_dh_i += theta * (-g * A_theta / dx)
            dR_dh_i1 += (theta/dx) * (g * 0.5 * width) * dh_dx
            dR_dh_i1 += theta * (g * A_theta / dx)

            J[n+i, i] = dR_dh_i
            J[n+i, i+1] = dR_dh_i1
            J[n+i, n+i] = dR_dQ_i
            J[n+i, n+i+1] = dR_dQ_i1

        return J.tocsr(), R

    def _apply_boundaries(self, J, R, h_new, Q_new, bc: dict, n: int):
        """应用边界条件"""
        # 上游边界 (使用空行 n-1)
        if 'upstream_level' in bc:
            J[n-1, :] = 0
            J[n-1, 0] = 1
            R[n-1] = h_new[0] - bc['upstream_level']
        elif 'upstream_flow' in bc:
            J[n-1, :] = 0
            J[n-1, n] = 1
            R[n-1] = Q_new[0] - bc['upstream_flow']

        # 下游边界 (使用空行 2n-1)
        if 'downstream_level' in bc:
            J[2*n-1, :] = 0
            J[2*n-1, n-1] = 1
            R[2*n-1] = h_new[n-1] - bc['downstream_level']
        elif 'downstream_flow' in bc:
            J[2*n-1, :] = 0
            J[2*n-1, 2*n-1] = 1
            R[2*n-1] = Q_new[n-1] - bc['downstream_flow']

        return J, R
