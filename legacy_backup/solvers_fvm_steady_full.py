#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
完整FVM隐式稳态求解器

使用完整Jacobian矩阵的Newton迭代求解Saint-Venant稳态方程

关键改进（相比fvm_steady_solver.py）：
1. 完整Jacobian矩阵（包括所有耦合项）
2. 稀疏矩阵存储和求解
3. 回溯线搜索确保收敛
4. 从FDM解作为初值

作者: Claude
日期: 2025-10-23
"""

import numpy as np
from scipy.sparse import lil_matrix, csr_matrix
from scipy.sparse.linalg import spsolve
import sys
import os

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from solvers.riemann_solvers import hll_flux_shallow_water
from utils.canal_utils import compute_steady_uniform_flow


class FVMSteadyFullSolver:
    """
    完整FVM隐式稳态求解器

    使用完整Jacobian矩阵的Newton迭代
    """

    def __init__(self, x_grid, B, S0, n, g=9.81, gates=None):
        """
        初始化求解器

        Args:
            x_grid: 网格点坐标 [m]
            B: 渠道宽度 [m]
            S0: 底坡 [-]
            n: Manning糙率 [s/m^(1/3)]
            g: 重力加速度 [m/s²]
            gates: 闸门列表 [(position, opening, Cd), ...]
        """
        self.x = np.array(x_grid)
        self.nx = len(self.x)
        self.B = B
        self.S0 = S0
        self.n = n
        self.g = g

        # 计算单元中心和尺寸
        self.x_cell = 0.5 * (self.x[:-1] + self.x[1:])
        self.dx = np.diff(self.x)
        self.ncells = len(self.x_cell)

        # 状态变量 U = [A, Q] 展开为一维向量
        # U_vec = [A[0], Q[0], A[1], Q[1], ..., A[ncells-1], Q[ncells-1]]
        self.U_vec = np.zeros(2 * self.ncells)

        # 闸门处理
        self.gates = gates if gates is not None else []
        self.gate_interfaces = []

        for gate_pos, gate_opening, gate_Cd in self.gates:
            interface_idx = np.argmin(np.abs(self.x - gate_pos))
            self.gate_interfaces.append({
                'index': interface_idx,
                'position': gate_pos,
                'actual_x': self.x[interface_idx],
                'opening': gate_opening,
                'Cd': gate_Cd
            })

        if len(self.gates) > 0:
            print(f"\n完整FVM稳态求解器初始化:")
            print(f"  检测到{len(self.gates)}个闸门")
            for i, gate_info in enumerate(self.gate_interfaces):
                print(f"  闸门{i+1}: x={gate_info['position']}m (界面{gate_info['index']}), "
                      f"开度={gate_info['opening']}m, Cd={gate_info['Cd']}")

    def initialize(self, h0, Q0):
        """
        初始化状态

        Args:
            h0: 初始水深 [m] (数组或标量)
            Q0: 初始流量 [m³/s] (数组或标量)
        """
        if np.isscalar(h0):
            h0 = np.ones(self.ncells) * h0
        if np.isscalar(Q0):
            Q0 = np.ones(self.ncells) * Q0

        A0 = self.B * np.array(h0)

        # 交错存储：[A[0], Q[0], A[1], Q[1], ...]
        for i in range(self.ncells):
            self.U_vec[2*i] = A0[i]
            self.U_vec[2*i+1] = Q0[i]

    def vec_to_matrix(self, U_vec):
        """
        将一维向量转换为二维矩阵 [ncells, 2]

        Args:
            U_vec: 一维向量 [A[0], Q[0], A[1], Q[1], ...]

        Returns:
            U: 二维矩阵 [ncells, 2]
        """
        U = np.zeros((self.ncells, 2))
        for i in range(self.ncells):
            U[i, 0] = U_vec[2*i]      # A
            U[i, 1] = U_vec[2*i+1]    # Q
        return U

    def matrix_to_vec(self, U):
        """
        将二维矩阵转换为一维向量

        Args:
            U: 二维矩阵 [ncells, 2]

        Returns:
            U_vec: 一维向量
        """
        U_vec = np.zeros(2 * self.ncells)
        for i in range(self.ncells):
            U_vec[2*i] = U[i, 0]      # A
            U_vec[2*i+1] = U[i, 1]    # Q
        return U_vec

    def compute_interface_flux(self, U):
        """
        计算所有界面通量

        Args:
            U: 当前状态 [ncells, 2]

        Returns:
            F: 界面通量 [ncells+1, 2]
        """
        F = np.zeros((self.ncells + 1, 2))

        # 创建闸门索引映射
        gate_indices = {g['index']: g for g in self.gate_interfaces}

        for i in range(1, self.ncells):
            # 左右状态
            U_L = U[i-1]
            U_R = U[i]

            # 检查是否是闸门界面
            if i in gate_indices:
                # 使用闸门通量
                gate_info = gate_indices[i]
                F[i] = self._compute_gate_flux(U_L, U_R, gate_info)
            else:
                # 使用HLL Riemann求解器
                F[i] = hll_flux_shallow_water(U_L, U_R, self.B, self.g)

        return F

    def _compute_gate_flux(self, U_L, U_R, gate_info):
        """
        计算闸门通量

        Args:
            U_L, U_R: 左右状态 [A, Q]
            gate_info: 闸门信息字典

        Returns:
            F: 通量 [F_mass, F_momentum]
        """
        A_L, Q_L = U_L
        A_R, Q_R = U_R

        h_L = A_L / self.B if A_L > 1e-10 else 1e-10
        h_R = A_R / self.B if A_R > 1e-10 else 1e-10

        a = gate_info['opening']
        Cd = gate_info['Cd']

        # 闸门流量
        delta_h = h_L - h_R

        if h_L > a:
            # 淹没出流
            if delta_h > 1e-6:
                Q_gate = Cd * a * self.B * np.sqrt(2 * self.g * delta_h)
            else:
                Q_gate = 0.0
        else:
            # 自由出流
            if h_L > 1e-6:
                Q_gate = Cd * a * self.B * np.sqrt(2 * self.g * h_L)
            else:
                Q_gate = 0.0

        # 质量通量
        F_mass = Q_gate

        # 动量通量
        A_avg = 0.5 * (A_L + A_R)
        h_avg = 0.5 * (h_L + h_R)
        u_gate = Q_gate / A_avg if A_avg > 1e-10 else 0.0

        F_momentum = Q_gate * u_gate + 0.5 * self.g * A_avg * h_avg

        return np.array([F_mass, F_momentum])

    def compute_source_term(self, U):
        """
        计算源项 S = [0, gA(S0 - Sf)]

        Args:
            U: 当前状态 [ncells, 2]

        Returns:
            S: 源项 [ncells, 2]
        """
        S = np.zeros_like(U)

        A = U[:, 0]
        Q = U[:, 1]

        h = A / self.B
        h = np.maximum(h, 1e-10)

        # Manning摩阻坡度
        R = self.B * h / (self.B + 2 * h)
        R = np.maximum(R, 1e-10)

        Sf = np.zeros_like(h)
        mask = A > 1e-10
        Sf[mask] = self.n**2 * Q[mask]**2 / (A[mask]**2 * R[mask]**(4.0/3.0))

        # 源项
        S[:, 0] = 0.0
        S[:, 1] = self.g * A * (self.S0 - Sf)

        return S

    def compute_steady_residual(self, U_vec, Q_upstream, h_downstream):
        """
        计算稳态残差

        Args:
            U_vec: 当前状态向量 [2*ncells]
            Q_upstream: 上游流量边界条件
            h_downstream: 下游水深边界条件

        Returns:
            R_vec: 残差向量 [2*ncells]
        """
        U = self.vec_to_matrix(U_vec)
        R = np.zeros_like(U)

        # 计算界面通量
        F = self.compute_interface_flux(U)

        # 边界通量
        # 上游边界
        A_upstream = U[0, 0]
        h_upstream = A_upstream / self.B
        u_upstream = Q_upstream / A_upstream if A_upstream > 1e-10 else 0.0
        F[0] = np.array([
            Q_upstream,
            Q_upstream * u_upstream + 0.5 * self.g * A_upstream * h_upstream
        ])

        # 下游边界
        A_downstream = self.B * h_downstream
        Q_downstream = U[-1, 1]
        u_downstream = Q_downstream / A_downstream if A_downstream > 1e-10 else 0.0
        F[-1] = np.array([
            Q_downstream,
            Q_downstream * u_downstream + 0.5 * self.g * A_downstream * h_downstream
        ])

        # 计算源项
        S = self.compute_source_term(U)

        # 组装残差
        for i in range(self.ncells):
            flux_diff = (F[i+1] - F[i]) / self.dx[i]
            R[i] = -flux_diff + S[i]

        return self.matrix_to_vec(R)

    def compute_jacobian_fd(self, U_vec, Q_upstream, h_downstream, epsilon=1e-7):
        """
        使用有限差分计算完整Jacobian矩阵

        Args:
            U_vec: 当前状态向量 [2*ncells]
            Q_upstream: 上游流量
            h_downstream: 下游水深
            epsilon: 有限差分步长

        Returns:
            J: 稀疏Jacobian矩阵 [2*ncells, 2*ncells]
        """
        n = len(U_vec)
        J = lil_matrix((n, n))

        # 计算基准残差
        R0 = self.compute_steady_residual(U_vec, Q_upstream, h_downstream)

        # 对每个变量进行扰动
        for j in range(n):
            # 扰动U_vec[j]
            U_perturb = U_vec.copy()

            # 自适应步长
            h_fd = epsilon * max(abs(U_vec[j]), 1.0)
            U_perturb[j] += h_fd

            # 计算扰动后的残差
            R_perturb = self.compute_steady_residual(U_perturb, Q_upstream, h_downstream)

            # 数值导数（第j列）
            dR_dU = (R_perturb - R0) / h_fd

            # 只存储非零元素（稀疏）
            for i in range(n):
                if abs(dR_dU[i]) > 1e-12:
                    J[i, j] = dR_dU[i]

        return J.tocsr()

    def line_search(self, U_vec, dU, R_norm, Q_upstream, h_downstream,
                   alpha_init=1.0, rho=0.5, c=1e-4, max_iter=10):
        """
        回溯线搜索

        Args:
            U_vec: 当前状态
            dU: Newton步
            R_norm: 当前残差范数
            Q_upstream, h_downstream: 边界条件
            alpha_init: 初始步长
            rho: 步长衰减因子
            c: Armijo条件参数
            max_iter: 最大回溯次数

        Returns:
            alpha: 最终步长
        """
        alpha = alpha_init

        for _ in range(max_iter):
            U_new = U_vec + alpha * dU

            # 确保物理约束
            for i in range(self.ncells):
                U_new[2*i] = max(U_new[2*i], self.B * 0.01)  # A > 0

            R_new = self.compute_steady_residual(U_new, Q_upstream, h_downstream)
            R_new_norm = np.linalg.norm(R_new)

            # Armijo条件
            if R_new_norm < (1 - c * alpha) * R_norm:
                return alpha

            alpha *= rho

        return alpha

    def solve_steady_newton(self, Q_target, h_downstream=None,
                           max_iter=50, tol=1e-6, verbose=True):
        """
        使用完整Jacobian的Newton迭代求解稳态

        Args:
            Q_target: 目标流量 [m³/s]
            h_downstream: 下游水深 [m]
            max_iter: 最大迭代次数
            tol: 收敛容差
            verbose: 是否打印信息

        Returns:
            converged: 是否收敛
        """
        if h_downstream is None:
            h_downstream = compute_steady_uniform_flow(Q_target, self.B, self.S0, self.n, self.g)

        if verbose:
            print(f"\n开始完整Jacobian Newton迭代...")
            print(f"  目标流量: {Q_target} m³/s")
            print(f"  下游水深: {h_downstream:.3f} m")
            print(f"  收敛容差: {tol}")
            print(f"  状态变量维度: {len(self.U_vec)}")
            print()

        for iter_count in range(max_iter):
            # 计算残差
            R = self.compute_steady_residual(self.U_vec, Q_target, h_downstream)
            R_norm = np.linalg.norm(R)

            # 计算当前流量误差
            U = self.vec_to_matrix(self.U_vec)
            Q_avg = np.mean(U[:, 1])
            Q_error = abs(Q_avg - Q_target) / Q_target * 100

            if verbose and iter_count % 5 == 0:
                print(f"  Iter {iter_count:3d}: ||R||={R_norm:.6e}, "
                      f"Q_avg={Q_avg:.4f} m³/s, error={Q_error:.4f}%")

            # 检查收敛
            if R_norm < tol:
                if verbose:
                    print(f"\n Newton迭代收敛！(iter={iter_count}, ||R||={R_norm:.6e})")
                    print(f"  最终流量误差: {Q_error:.4f}%")
                return True

            # 计算完整Jacobian
            if verbose and iter_count % 5 == 0:
                print(f"       计算Jacobian矩阵...")

            J = self.compute_jacobian_fd(self.U_vec, Q_target, h_downstream)

            # 求解Newton方程 J * dU = -R
            try:
                dU = spsolve(J, -R)
            except:
                if verbose:
                    print(f"\n Jacobian矩阵奇异，迭代终止")
                return False

            # 线搜索
            alpha = self.line_search(self.U_vec, dU, R_norm, Q_target, h_downstream)

            if verbose and iter_count % 5 == 0:
                print(f"       线搜索步长: alpha={alpha:.6f}")

            # 更新状态
            self.U_vec = self.U_vec + alpha * dU

            # 确保物理约束
            for i in range(self.ncells):
                self.U_vec[2*i] = max(self.U_vec[2*i], self.B * 0.01)  # A > 0

        if verbose:
            print(f"\n Newton迭代未收敛（达到最大迭代次数{max_iter}）")
            print(f"  最终残差: ||R||={R_norm:.6e}")
            print(f"  最终流量误差: {Q_error:.4f}%")

        return False

    def get_results(self):
        """
        获取结果

        Returns:
            dict: 包含x, h, Q, u的字典
        """
        U = self.vec_to_matrix(self.U_vec)
        h = U[:, 0] / self.B
        Q = U[:, 1]
        u = Q / (self.B * h)

        return {
            'x': self.x_cell,
            'h': h,
            'Q': Q,
            'u': u
        }
