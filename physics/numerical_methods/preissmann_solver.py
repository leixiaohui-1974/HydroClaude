import numpy as np
from scipy.sparse import lil_matrix
from scipy.sparse.linalg import spsolve

class PreissmannSolver:
    """
    Preissmann四点隐式格式求解器
    """

    def __init__(self, theta: float = 0.6, max_iter: int = 10,
                 tolerance: float = 1e-6):
        self.theta = theta
        self.max_iter = max_iter
        self.tolerance = tolerance

    def solve_canal_step(self, h_old: np.ndarray, Q_old: np.ndarray,
                        dt: float, dx: float,
                        width: float, manning_n: float, slope: float,
                        boundary_conditions: dict):
        n = len(h_old)
        g = 9.81

        h_new = h_old.copy()
        Q_new = Q_old.copy()

        # 确保初始值合理
        h_new = np.maximum(h_new, 0.1)
        Q_new = np.maximum(Q_new, 0.01)

        for iteration in range(self.max_iter):
            J, R = self._build_jacobian_residual(
                h_old, Q_old, h_new, Q_new,
                dt, dx, width, manning_n, slope, g
            )

            J, R = self._apply_boundaries(J, R, boundary_conditions, n)

            try:
                # 添加小的对角元素以提高数值稳定性
                J_dense = J.toarray()
                for i in range(2*n):
                    if abs(J_dense[i, i]) < 1e-10:
                        J_dense[i, i] = 1e-6

                from scipy.sparse import csr_matrix
                J = csr_matrix(J_dense)

                dx_vector = spsolve(J, -R)
            except Exception as e:
                print(f"Warning: 求解器在迭代{iteration}失败: {e}")
                break

            dh = dx_vector[:n]
            dQ = dx_vector[n:]

            # 限制每次迭代的变化量
            dh = np.clip(dh, -0.5, 0.5)
            dQ = np.clip(dQ, -1.0, 1.0)

            h_new += dh
            Q_new += dQ

            # 确保物理合理性
            h_new = np.maximum(h_new, 0.01)
            Q_new = np.maximum(Q_new, 0.0)

            residual_norm = np.linalg.norm(R)
            if residual_norm < self.tolerance:
                break

        return h_new, Q_new

    def _build_jacobian_residual(self, h_old, Q_old, h_new, Q_new,
                                 dt, dx, width, n_manning, S0, g):
        n = len(h_old)
        theta = self.theta

        J = lil_matrix((2*n, 2*n))
        R = np.zeros(2*n)

        for i in range(n-1):
            h_old_mid = 0.5 * (h_old[i] + h_old[i+1])
            Q_old_mid = 0.5 * (Q_old[i] + Q_old[i+1])
            A_old_mid = h_old_mid * width

            h_new_mid = 0.5 * (h_new[i] + h_new[i+1])
            Q_new_mid = 0.5 * (Q_new[i] + Q_new[i+1])
            A_new_mid = h_new_mid * width

            h_theta = theta * h_new_mid + (1 - theta) * h_old_mid
            Q_theta = theta * Q_new_mid + (1 - theta) * Q_old_mid
            A_theta = h_theta * width

            dQ_dx = (Q_new[i+1] - Q_new[i]) / dx * theta + \
                    (Q_old[i+1] - Q_old[i]) / dx * (1 - theta)

            continuity_residual = (A_new_mid - A_old_mid) / dt + dQ_dx

            R[i] = continuity_residual

            J[i, i] = 0.5 * width / dt
            J[i, i+1] = 0.5 * width / dt
            J[i, n+i] = -theta / dx
            J[i, n+i+1] = theta / dx

            V_theta = Q_theta / A_theta if A_theta > 0 else 0

            P_wetted = width + 2 * h_theta
            R_hydraulic = A_theta / P_wetted if P_wetted > 0 else 0

            Sf = 0
            if R_hydraulic > 0 and abs(V_theta) > 1e-6:
                Sf = (n_manning * V_theta)**2 / (R_hydraulic**(4/3))

            dQ_dt = (Q_new_mid - Q_old_mid) / dt

            Q2_A_i = Q_new[i]**2 / (h_new[i] * width) if h_new[i] > 0 else 0
            Q2_A_i1 = Q_new[i+1]**2 / (h_new[i+1] * width) if h_new[i+1] > 0 else 0
            d_Q2A_dx = (Q2_A_i1 - Q2_A_i) / dx * theta

            dh_dx = (h_new[i+1] - h_new[i]) / dx * theta + \
                    (h_old[i+1] - h_old[i]) / dx * (1 - theta)
            pressure_term = g * A_theta * dh_dx

            source_term = g * A_theta * (S0 - Sf)

            momentum_residual = dQ_dt + d_Q2A_dx + pressure_term - source_term

            R[n+i] = momentum_residual

            J[n+i, i] = -0.5 * g * width * theta / dx
            J[n+i, i+1] = 0.5 * g * width * theta / dx

            J[n+i, n+i] = 0.5 / dt + theta * 2 * Q_new[i] / (h_new[i] * width * dx)
            J[n+i, n+i+1] = 0.5 / dt - theta * 2 * Q_new[i+1] / (h_new[i+1] * width * dx)

        return J.tocsr(), R

    def _apply_boundaries(self, J, R, bc: dict, n: int):
        """应用边界条件"""
        # 上游边界
        if 'upstream_level' in bc:
            # 固定水位
            J[0, :] = 0
            J[0, 0] = 1
            R[0] = 0  # h[0]已经被设为目标值
        elif 'upstream_flow' in bc:
            # 固定流量
            J[n, :] = 0
            J[n, n] = 1
            R[n] = 0  # Q[0]已经被设为目标值
        else:
            # 默认：自由边界（保持当前状态）
            J[0, :] = 0
            J[0, 0] = 1
            R[0] = 0

        # 下游边界
        if 'downstream_level' in bc:
            # 固定水位
            J[n-1, :] = 0
            J[n-1, n-1] = 1
            R[n-1] = 0
        elif 'downstream_flow' in bc:
            # 固定流量
            J[2*n-1, :] = 0
            J[2*n-1, 2*n-1] = 1
            R[2*n-1] = 0
        else:
            # 默认：自由边界
            J[n-1, :] = 0
            J[n-1, n-1] = 1
            R[n-1] = 0

        return J, R
