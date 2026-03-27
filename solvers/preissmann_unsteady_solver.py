import numpy as np
from scipy.sparse import lil_matrix, csr_matrix
from typing import List, Tuple, Optional
import sys
import os

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from solvers.gate import HydraulicStructure
from solvers.newton_solver import NewtonSolver

class PreissmannUnsteadySolver:
    """
    基于Preissmann四点隐式格式的1D非恒定流求解器。
    求解Saint-Venant方程：
    ∂A/∂t + ∂Q/∂x = 0
    ∂Q/∂t + ∂(Q²/A)/∂x + gA∂h/∂x + gASf = 0

    采用有限差分法离散，并使用Newton-Raphson方法求解非线性方程组。
    """

    def __init__(self,
                 length: float,
                 nx: int,
                 B: float,
                 S0: float,
                 n: float,
                 g: float = 9.81,
                 theta: float = 0.6,
                 structures: Optional[List[Tuple[float, HydraulicStructure]]] = None):
        """
        Args:
            length: 渠道长度 (m)
            nx: 空间节点数
            B: 渠道宽度 (m)
            S0: 渠底坡度
            n: Manning糙率
            g: 重力加速度 (m/s²)
            theta: Preissmann格式的时间加权因子 (0.5-1.0)
            structures: 水工建筑物列表 [(position, structure), ...]
        """
        self.length = length
        self.nx = nx
        self.B = B
        self.S0 = S0
        self.n = n
        self.g = g
        self.theta = theta

        self.x = np.linspace(0, length, nx)
        self.dx = length / (nx - 1)

        self.structures = structures if structures is not None else []
        self.structure_indices = []
        self.structure_objects = []

        for pos, structure in self.structures:
            idx = np.argmin(np.abs(self.x - pos))
            self.structure_indices.append(idx)
            self.structure_objects.append(structure)

        self.n_vars = 2 * nx  # State vector U = [h0, Q0, h1, Q1, ...]

        self.U_old = None # 存储上一时间步的解

        # 边界条件，暂时硬编码，后续可扩展
        self.bc_upstream_type = 'Q_and_h' # 上游流量和水深
        self.bc_downstream_type = 'h' # 下游水深
        self.Q_upstream = 10.0
        self.h_upstream = 1.0
        self.h_downstream = 1.0

    def set_boundary_conditions(self,
                               Q_upstream: Optional[float] = None,
                               h_upstream: Optional[float] = None,
                               h_downstream: Optional[float] = None):
        if Q_upstream is not None:
            self.Q_upstream = Q_upstream
        if h_upstream is not None:
            self.h_upstream = h_upstream
        if h_downstream is not None:
            self.h_downstream = h_downstream

    def pack_state(self, h: np.ndarray, Q: np.ndarray) -> np.ndarray:
        U = np.zeros(self.n_vars)
        U[0::2] = h
        U[1::2] = Q
        return U

    def unpack_state(self, U: np.ndarray) -> Tuple[np.ndarray, np.ndarray]:
        h = U[0::2]
        Q = U[1::2]
        return h, Q

    def compute_lpi_factor(self, h: float, Q: float) -> float:
        """
        计算局部偏惯性(Local Partial Inertia, LPI)因子，用于稳定超临界流。
        当Fr接近或大于1时，减小或忽略对流加速度项。
        """
        if h < 1e-6:
            return 1.0
        u = abs(Q) / (self.B * h)
        Fr = u / np.sqrt(self.g * h)
        Fr_T = 0.8 # 阈值Froude数
        if Fr <= Fr_T:
            return 1.0
        elif Fr >= 1.0:
            return 0.0
        else:
            return (1.0 - Fr) / (1.0 - Fr_T)

    def compute_friction_slope(self, h: np.ndarray, Q: np.ndarray) -> np.ndarray:
        h_safe = np.maximum(h, 1e-6)
        A = self.B * h_safe
        P = self.B + 2 * h_safe
        R = A / P
        V = Q / A
        Sf = (self.n * V)**2 / R**(4/3)
        return Sf

    def compute_residual(self, U_new: np.ndarray, dt: float) -> np.ndarray:
        h_new, Q_new = self.unpack_state(U_new)
        h_old, Q_old = self.unpack_state(self.U_old)
        F = np.zeros(self.n_vars)

        # 计算摩阻坡度
        Sf_new = self.compute_friction_slope(h_new, Q_new)
        Sf_old = self.compute_friction_slope(h_old, Q_old)

        # 内部方程 (i = 0 to nx-2) - Preissmann 格式应用于每个网格单元 (i, i+1)
        # F 向量的索引从 1 到 self.n_vars - 2
        for i in range(self.nx - 1):
            A_new_i = self.B * h_new[i]
            A_new_ip1 = self.B * h_new[i+1]
            A_old_i = self.B * h_old[i]
            A_old_ip1 = self.B * h_old[i+1]

            res_cont = ((A_new_i + A_new_ip1)/2 - (A_old_i + A_old_ip1)/2) / dt + \
                       (self.theta * (Q_new[i+1] - Q_new[i])) / self.dx + \
                       ((1 - self.theta) * (Q_old[i+1] - Q_old[i])) / self.dx
            F[2*i + 1] = res_cont # 单元 i 的连续性方程
            
            u_new_i = Q_new[i] / A_new_i if A_new_i > 1e-6 else 0.0
            u_new_ip1 = Q_new[i+1] / A_new_ip1 if A_new_ip1 > 1e-6 else 0.0
            
            sigma_new_i = self.compute_lpi_factor(h_new[i], Q_new[i])
            sigma_new_ip1 = self.compute_lpi_factor(h_new[i+1], Q_new[i+1])

            E_new_i = sigma_new_i * Q_new[i] * u_new_i + self.g * A_new_i * h_new[i] / 2.0
            E_new_ip1 = sigma_new_ip1 * Q_new[i+1] * u_new_ip1 + self.g * A_new_ip1 * h_new[i+1] / 2.0

            u_old_i = Q_old[i] / A_old_i if A_old_i > 1e-6 else 0.0
            u_old_ip1 = Q_old[i+1] / A_old_ip1 if A_old_ip1 > 1e-6 else 0.0
            
            sigma_old_i = self.compute_lpi_factor(h_old[i], Q_old[i])
            sigma_old_ip1 = self.compute_lpi_factor(h_old[i+1], Q_old[i+1])

            E_old_i = sigma_old_i * Q_old[i] * u_old_i + self.g * A_old_i * h_old[i] / 2.0
            E_old_ip1 = sigma_old_ip1 * Q_old[i+1] * u_old_ip1 + self.g * A_old_ip1 * h_old[i+1] / 2.0

            E_new_avg = (E_new_i + E_new_ip1) / 2.0
            E_old_avg = (E_old_i + E_old_ip1) / 2.0

            A_new_avg = (A_new_i + A_new_ip1) / 2.0
            A_old_avg = (A_old_i + A_old_ip1) / 2.0
            Sf_new_avg = (Sf_new[i] + Sf_new[i+1]) / 2.0
            Sf_old_avg = (Sf_old[i] + Sf_old[i+1]) / 2.0

            res_mom = ((Q_new[i] + Q_new[i+1])/2 - (Q_old[i] + Q_old[i+1])/2) / dt + \
                      (self.theta * (E_new_ip1 - E_new_i)) / self.dx + \
                      ((1 - self.theta) * (E_old_ip1 - E_old_i)) / self.dx - \
                      self.g * (self.theta * A_new_avg * (self.S0 - Sf_new_avg) + \
                                (1 - self.theta) * A_old_avg * (self.S0 - Sf_old_avg))
            F[2*i + 2] = res_mom # 单元 i 的动量方程

        # 边界条件
        # 上游流量边界 Q_new[0] = Q_upstream, 对应 F[0]
        F[0] = Q_new[0] - self.Q_upstream

        # 下游水深边界 h_new[nx-1] = h_downstream, 对应 F[self.n_vars - 1]
        F[self.n_vars - 1] = h_new[self.nx-1] - self.h_downstream

        return F

    def compute_jacobian(self, U_new: np.ndarray, dt: float) -> csr_matrix:
        J = lil_matrix((self.n_vars, self.n_vars))
        h_new, Q_new = self.unpack_state(U_new)

        # Helper functions for derivatives
        def dA_dh(h_val): return self.B
        def dP_dh(h_val): return 2.0
        def dR_dh(h_val): return (self.B * (self.B + 2 * h_val) - self.B * h_val * 2) / (self.B + 2 * h_val)**2
        def dR_dQ(h_val, Q_val): return 0.0

        def dV_dh(h_val, Q_val): return -Q_val / (self.B * h_val)**2 * self.B
        def dV_dQ(h_val, Q_val): return 1.0 / (self.B * h_val)

        def dSf_dh(h_val, Q_val):
            if h_val < 1e-6: return 0.0
            V = Q_val / (self.B * h_val)
            R = (self.B * h_val) / (self.B + 2 * h_val)
            term1 = 2 * self.n**2 * V / R**(4/3) * dV_dh(h_val, Q_val)
            term2 = -4/3 * self.n**2 * V**2 / R**(7/3) * dR_dh(h_val)
            return term1 + term2

        def dSf_dQ(h_val, Q_val):
            if h_val < 1e-6: return 0.0
            V = Q_val / (self.B * h_val)
            R = (self.B * h_val) / (self.B + 2 * h_val)
            term1 = 2 * self.n**2 * V / R**(4/3) * dV_dQ(h_val, Q_val)
            term2 = -4/3 * self.n**2 * V**2 / R**(7/3) * dR_dQ(h_val, Q_val) # This is 0
            return term1 + term2

        # 边界条件
        # 上游流量边界 Q_new[0] = Q_upstream, 对应 F[0]
        J[0, :] = 0.0
        J[0, 1] = 1.0 # d(F[0])/dQ_new[0]

        # 下游水深边界 h_new[nx-1] = h_downstream, 对应 F[self.n_vars - 1]
        J[self.n_vars - 1, :] = 0.0
        J[self.n_vars - 1, self.n_vars - 2] = 1.0 # d(F[self.n_vars - 1])/dh_new[nx-1]

        # 内部方程
        for i in range(self.nx - 1):
            # Indices for h and Q at i and i+1
            idx_hi = 2 * i
            idx_Qi = 2 * i + 1
            idx_hip1 = 2 * (i + 1)
            idx_Qip1 = 2 * (i + 1) + 1

            # Current state values
            hi = h_new[i]
            Qi = Q_new[i]
            hip1 = h_new[i+1]
            Qip1 = Q_new[i+1]

            Ai = self.B * hi
            Aip1 = self.B * hip1

            # Continuity Equation (F[2*i+1])
            # d(res_cont)/dh_new[i]
            J[2*i+1, idx_hi] = (self.B / 2) / dt
            # d(res_cont)/dh_new[i+1]
            J[2*i+1, idx_hip1] = (self.B / 2) / dt
            # d(res_cont)/dQ_new[i]
            J[2*i+1, idx_Qi] = -self.theta / self.dx
            # d(res_cont)/dQ_new[i+1]
            J[2*i+1, idx_Qip1] = self.theta / self.dx

            # Momentum Equation (F[2*i+2])
            sigma_i = self.compute_lpi_factor(hi, Qi)
            sigma_ip1 = self.compute_lpi_factor(hip1, Qip1)
            
            dE_hi_dhi = sigma_i * (-Qi**2 / (self.B * hi**2)) + self.g * self.B * hi if hi > 1e-6 else 0.0
            dE_hi_dQi = sigma_i * (2 * Qi / (self.B * hi)) if hi > 1e-6 else 0.0

            dE_hip1_dhip1 = sigma_ip1 * (-Qip1**2 / (self.B * hip1**2)) + self.g * self.B * hip1 if hip1 > 1e-6 else 0.0
            dE_hip1_dQip1 = sigma_ip1 * (2 * Qip1 / (self.B * hip1)) if hip1 > 1e-6 else 0.0

            J[2*i+2, idx_Qi] += 0.5 / dt
            J[2*i+2, idx_Qip1] += 0.5 / dt

            J[2*i+2, idx_hi] += (self.theta / self.dx) * (-1.0 * dE_hi_dhi)
            J[2*i+2, idx_Qi] += (self.theta / self.dx) * (-1.0 * dE_hi_dQi)
            J[2*i+2, idx_hip1] += (self.theta / self.dx) * (1.0 * dE_hip1_dhip1)
            J[2*i+2, idx_Qip1] += (self.theta / self.dx) * (1.0 * dE_hip1_dQip1)

            dA_avg_dhi = self.B / 2.0
            dA_avg_dhip1 = self.B / 2.0

            dSf_avg_dhi = 0.5 * dSf_dh(hi, Qi)
            dSf_avg_dQi = 0.5 * dSf_dQ(hi, Qi)
            dSf_avg_dhip1 = 0.5 * dSf_dh(hip1, Qip1)
            dSf_avg_dQip1 = 0.5 * dSf_dQ(hip1, Qip1)

            A_new_avg = (Ai + Aip1) / 2.0
            Sf_new_avg = (self.compute_friction_slope(np.array([hi]), np.array([Qi]))[0] + \
                          self.compute_friction_slope(np.array([hip1]), np.array([Qip1]))[0]) / 2.0

            J[2*i+2, idx_hi] -= self.g * self.theta * (dA_avg_dhi * (self.S0 - Sf_new_avg) - A_new_avg * dSf_avg_dhi)
            J[2*i+2, idx_Qi] -= self.g * self.theta * (-A_new_avg * dSf_avg_dQi)
            J[2*i+2, idx_hip1] -= self.g * self.theta * (dA_avg_dhip1 * (self.S0 - Sf_new_avg) - A_new_avg * dSf_avg_dhip1)
            J[2*i+2, idx_Qip1] -= self.g * self.theta * (-A_new_avg * dSf_avg_dQip1)

        return J.tocsr()

    def solve_step(self, U_initial: np.ndarray, dt: float, max_iter: int = 100, tol: float = 1e-6) -> np.ndarray:
        self.U_old = U_initial.copy()
        
        # 定义传递给NewtonSolver的残差和Jacobian函数
        def residual_func(U_current):
            return self.compute_residual(U_current, dt)
        
        def jacobian_func(U_current):
            return self.compute_jacobian(U_current, dt)

        solver = NewtonSolver(max_iter=max_iter, tol_residual=tol, tol_update=tol)
        U_new, info = solver.solve(U_initial, residual_func, jacobian_func)
        converged = info["converged"]
        num_iter = info["iterations"]

        if not converged:
            print(f"Warning: Newton solver did not converge after {num_iter} iterations.")

        # 物理约束：确保水深 h 不为负，防止数值发散
        h_new, Q_new = self.unpack_state(U_new)
        eps_h = 1e-6
        if np.any(~np.isfinite(h_new)) or np.any(h_new < -1.0):
            # 数值发散：回退到上一步的解，避免崩溃
            print("Warning: Numerical blow-up detected. Falling back to previous step.")
            return U_initial.copy()
        h_new = np.maximum(h_new, eps_h)
        U_new = self.pack_state(h_new, Q_new)

        return U_new

    def initialize_state(self, h_initial: float, Q_initial: float):
        h = np.ones(self.nx) * h_initial
        Q = np.ones(self.nx) * Q_initial
        self.U_old = self.pack_state(h, Q)

    def get_h(self) -> np.ndarray:
        return self.unpack_state(self.U_old)[0]

    def get_Q(self) -> np.ndarray:
        return self.unpack_state(self.U_old)[1]

if __name__ == "__main__":
    # 示例用法
    length = 1000.0
    nx = 51
    B = 10.0
    S0 = 0.0001
    n = 0.025
    g = 9.81
    theta = 0.6

    solver = PreissmannUnsteadySolver(length, nx, B, S0, n, g, theta)
    solver.set_boundary_conditions(Q_upstream=10.0, h_upstream=1.0, h_downstream=1.0)
    solver.initialize_state(h_initial=1.0, Q_initial=10.0)

    dt = 10.0 # 假设时间步长
    total_time = 3600.0 # 模拟1小时
    num_steps = int(total_time / dt)

    print("Starting unsteady simulation...")
    for step in range(num_steps):
        print(f"Time step {step+1}/{num_steps}, Current time: {solver.U_old[0]} s")
        U_new = solver.solve_step(solver.U_old, dt)
        solver.U_old = U_new

        if step % 10 == 0:
            h, Q = solver.unpack_state(U_new)
            print(f"  Max h: {np.max(h):.3f}, Min h: {np.min(h):.3f}")
            print(f"  Max Q: {np.max(Q):.3f}, Min Q: {np.min(Q):.3f}")

    print("Simulation finished.")
    h_final, Q_final = solver.unpack_state(solver.U_old)
    print(f"Final h: {h_final[0]:.3f} (upstream), {h_final[-1]:.3f} (downstream)")
    print(f"Final Q: {Q_final[0]:.3f} (upstream), {Q_final[-1]:.3f} (downstream)")
