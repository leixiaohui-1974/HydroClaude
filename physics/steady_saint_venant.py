#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
稳态Saint-Venant方程的残差和Jacobian

用于牛顿法求解稳态明渠流动问题
支持闸门等内部边界条件

作者: Claude
日期: 2025-10-22
"""

import numpy as np
from scipy.sparse import lil_matrix, csr_matrix
from typing import List, Tuple, Optional
import sys
import os

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from solvers.gate import HydraulicStructure


class SteadySaintVenantSystem:
    """
    稳态Saint-Venant方程系统（带伪瞬态延拓）

    方程：
    - 连续性：ε·∂Q/∂τ + dQ/dx = 0 （伪瞬态）
    - 动量：  ε·∂h/∂τ + d(Q²/A)/dx + gA·dh/dx = gA(S₀ - Sf)

    其中：
    - h: 水深
    - Q: 流量
    - A = B·h: 断面面积（矩形断面）
    - Sf: Manning摩阻坡度 = (n·V)²/R^(4/3)
    - S₀: 渠底坡度
    - ε: 伪时间步长（小值，避免Jacobian奇异）
    - τ: 伪时间

    当ε→0时，收敛到稳态解
    """

    def __init__(self,
                 length: float,
                 nx: int,
                 B: float,
                 S0: float,
                 n: float,
                 g: float = 9.81,
                 structures: Optional[List[Tuple[float, HydraulicStructure]]] = None,
                 pseudo_dt: float = 0.1):
        """
        Args:
            length: 渠道长度 (m)
            nx: 空间节点数
            B: 渠道宽度 (m)
            S0: 渠底坡度
            n: Manning糙率
            g: 重力加速度 (m/s²)
            structures: 水工建筑物列表 [(position, structure), ...]
        """
        self.length = length
        self.nx = nx
        self.B = B
        self.S0 = S0
        self.n = n
        self.g = g
        self.pseudo_dt = pseudo_dt  # 伪时间步长

        # 空间网格
        self.x = np.linspace(0, length, nx)
        self.dx = length / (nx - 1)

        # 上一步的解（用于伪瞬态项）
        self.U_prev = None

        # 水工建筑物
        self.structures = structures if structures is not None else []
        self.structure_indices = []
        self.structure_objects = []

        # 找到结构物对应的网格索引
        for pos, structure in self.structures:
            idx = np.argmin(np.abs(self.x - pos))
            self.structure_indices.append(idx)
            self.structure_objects.append(structure)

        # 状态向量维度：2*nx（交替存储h和Q）
        # U = [h_0, Q_0, h_1, Q_1, ..., h_{nx-1}, Q_{nx-1}]
        self.n_vars = 2 * nx

        # 边界条件类型
        self.bc_upstream_type = 'Q+h'  # 上游流量+水深边界（两个约束）
        self.bc_downstream_type = 'h'  # 下游水深边界
        self.Q_upstream = 10.0  # 默认值
        self.h_upstream = 1.0   # 默认值（新增）
        self.h_downstream = 1.0  # 默认值

    def set_boundary_conditions(self,
                               Q_upstream: Optional[float] = None,
                               h_upstream: Optional[float] = None,
                               h_downstream: Optional[float] = None):
        """
        设置边界条件

        Args:
            Q_upstream: 上游流量 (m³/s)
            h_upstream: 上游水深 (m)（新增，修复Jacobian奇异性）
            h_downstream: 下游水深 (m)
        """
        if Q_upstream is not None:
            self.Q_upstream = Q_upstream
        if h_upstream is not None:
            self.h_upstream = h_upstream
        if h_downstream is not None:
            self.h_downstream = h_downstream

    def pack_state(self, h: np.ndarray, Q: np.ndarray) -> np.ndarray:
        """
        将h和Q打包成状态向量U

        Args:
            h: 水深数组 (nx,)
            Q: 流量数组 (nx,)

        Returns:
            U: 状态向量 (2*nx,)
        """
        U = np.zeros(self.n_vars)
        U[0::2] = h  # 偶数索引：h
        U[1::2] = Q  # 奇数索引：Q
        return U

    def unpack_state(self, U: np.ndarray) -> Tuple[np.ndarray, np.ndarray]:
        """
        将状态向量U解包成h和Q

        Args:
            U: 状态向量 (2*nx,)

        Returns:
            h: 水深数组 (nx,)
            Q: 流量数组 (nx,)
        """
        h = U[0::2]
        Q = U[1::2]
        return h, Q

    def compute_friction_slope(self, h: np.ndarray, Q: np.ndarray) -> np.ndarray:
        """
        计算Manning摩阻坡度

        Sf = (n·V)² / R^(4/3)

        其中：
        - V = Q/A
        - R = A/P （水力半径，矩形断面）
        - A = B·h
        - P = B + 2h
        """
        # 防止除零
        h_safe = np.maximum(h, 1e-6)

        A = self.B * h_safe  # 断面面积
        P = self.B + 2 * h_safe  # 湿周
        R = A / P  # 水力半径
        V = Q / A  # 流速

        # Manning公式
        Sf = (self.n * V)**2 / R**(4/3)

        return Sf

    def compute_residual(self, U: np.ndarray, t: float = 0.0) -> np.ndarray:
        """
        计算残差向量 F(U)（带伪瞬态项）

        对于每个内部节点i（1 <= i < nx-1）:
        - F_{2i}: 伪瞬态连续性方程残差
        - F_{2i+1}: 伪瞬态动量方程残差

        边界节点（i=0, i=nx-1）:
        - 应用边界条件

        Args:
            U: 状态向量 (2*nx,)
            t: 当前时间（用于时变结构）

        Returns:
            F: 残差向量 (2*nx,)
        """
        h, Q = self.unpack_state(U)
        F = np.zeros(self.n_vars)

        # 获取上一步的解（如果没有，使用当前解）
        if self.U_prev is None:
            h_prev, Q_prev = h.copy(), Q.copy()
        else:
            h_prev, Q_prev = self.unpack_state(self.U_prev)

        # 计算摩阻坡度
        Sf = self.compute_friction_slope(h, Q)

        # ========== 内部节点 ==========
        for i in range(1, self.nx - 1):
            # 检查是否为闸门节点
            if i in self.structure_indices:
                # 闸门节点：用闸门流量约束替代动量方程
                idx_structure = self.structure_indices.index(i)
                structure = self.structure_objects[idx_structure]

                # 上下游水深
                h_up = h[i - 1]
                h_down = h[i + 1]

                # 计算闸门流量
                Q_gate_target, _ = structure.calculate_discharge(h_up, h_down, t)

                # 连续性方程（保持，添加伪时间项）
                pseudo_time_term_Q_gate = (Q[i] - Q_prev[i]) / self.pseudo_dt
                F[2*i] = pseudo_time_term_Q_gate + (Q[i+1] - Q[i-1]) / (2 * self.dx)

                # 闸门流量约束（替代动量方程）
                F[2*i + 1] = Q[i] - Q_gate_target

            else:
                # 普通节点：标准Saint-Venant方程

                # 伪瞬态连续性方程：ε·(Q-Q_prev)/Δτ + dQ/dx = 0
                pseudo_time_term_Q = (Q[i] - Q_prev[i]) / self.pseudo_dt
                F[2*i] = pseudo_time_term_Q + (Q[i+1] - Q[i-1]) / (2 * self.dx)

                # 动量方程：d(Q²/A)/dx + gA·dh/dx = gA(S₀ - Sf)
                # 防止除零
                h_safe = np.maximum(h, 1e-6)
                A = self.B * h_safe

                # 动量通量项：d(Q²/A)/dx
                momentum_flux_i = Q[i]**2 / A[i]
                momentum_flux_ip1 = Q[i+1]**2 / A[i+1]
                momentum_flux_im1 = Q[i-1]**2 / A[i-1]
                d_momentum_flux = (momentum_flux_ip1 - momentum_flux_im1) / (2 * self.dx)

                # 压力项：gA·dh/dx
                dh_dx = (h[i+1] - h[i-1]) / (2 * self.dx)
                pressure_term = self.g * A[i] * dh_dx

                # 源项：gA(S₀ - Sf)
                source_term = self.g * A[i] * (self.S0 - Sf[i])

                # 伪瞬态动量方程：ε·(h-h_prev)/Δτ + 动量方程 = 0
                pseudo_time_term_h = (h[i] - h_prev[i]) / self.pseudo_dt

                # 动量方程残差
                F[2*i + 1] = pseudo_time_term_h + d_momentum_flux + pressure_term - source_term

        # ========== 上游边界（i=0） ==========
        # F[0]: Q[0] = Q_upstream（流量边界）
        # F[1]: h[0] = h_upstream（水深边界，修复Jacobian奇异性）
        F[0] = Q[0] - self.Q_upstream
        F[1] = h[0] - self.h_upstream

        # ========== 下游边界（i=nx-1） ==========
        # F[2*(nx-1)]: h[nx-1] = h_downstream（水深边界，无伪时间项）
        # F[2*(nx-1)+1]: 伪瞬态连续性方程
        i = self.nx - 1
        F[2*i] = h[i] - self.h_downstream

        # 下游边界的第二个方程：伪瞬态连续性（向后差分）
        pseudo_time_term_Qn = (Q[i] - Q_prev[i]) / self.pseudo_dt
        F[2*i + 1] = pseudo_time_term_Qn + (Q[i] - Q[i-1]) / self.dx

        return F

    def compute_jacobian(self, U: np.ndarray, t: float = 0.0) -> csr_matrix:
        """
        计算Jacobian矩阵 J(U) = ∂F/∂U

        Args:
            U: 状态向量 (2*nx,)
            t: 当前时间

        Returns:
            J: Jacobian矩阵 (2*nx, 2*nx)，稀疏格式
        """
        h, Q = self.unpack_state(U)
        J = lil_matrix((self.n_vars, self.n_vars))

        # 计算摩阻坡度及其导数
        Sf = self.compute_friction_slope(h, Q)

        # ========== 内部节点 ==========
        for i in range(1, self.nx - 1):
            # 检查是否为闸门节点
            if i in self.structure_indices:
                # 闸门节点
                idx_structure = self.structure_indices.index(i)
                structure = self.structure_objects[idx_structure]

                h_up = h[i - 1]
                h_down = h[i + 1]

                # 连续性方程 Jacobian（带伪瞬态）
                # F[2*i] = (Q[i]-Q_prev[i])/pseudo_dt + (Q[i+1] - Q[i-1]) / (2*dx)
                J[2*i, 2*i+1] = 1.0 / self.pseudo_dt  # ∂F/∂Q_i（伪时间项）
                J[2*i, 2*(i-1)+1] = -1.0 / (2 * self.dx)  # ∂F/∂Q_{i-1}
                J[2*i, 2*(i+1)+1] = 1.0 / (2 * self.dx)   # ∂F/∂Q_{i+1}

                # 闸门流量约束 Jacobian
                # F[2*i+1] = Q[i] - Q_gate(h_up, h_down)
                J[2*i+1, 2*i+1] = 1.0  # ∂F/∂Q_i

                # 计算 ∂Q_gate/∂h_up 和 ∂Q_gate/∂h_down（解析导数）
                dQ_gate_dh_up, dQ_gate_dh_down = structure.calculate_discharge_derivatives(h_up, h_down, t)

                J[2*i+1, 2*(i-1)] = -dQ_gate_dh_up    # ∂F/∂h_{i-1}
                J[2*i+1, 2*(i+1)] = -dQ_gate_dh_down  # ∂F/∂h_{i+1}

            else:
                # 普通节点：标准Saint-Venant方程

                # 连续性方程 Jacobian（带伪瞬态）
                # F[2*i] = (Q[i]-Q_prev[i])/pseudo_dt + (Q[i+1] - Q[i-1]) / (2*dx)
                J[2*i, 2*i+1] = 1.0 / self.pseudo_dt  # ∂F/∂Q_i（伪时间项，关键！）
                J[2*i, 2*(i-1)+1] = -1.0 / (2 * self.dx)
                J[2*i, 2*(i+1)+1] = 1.0 / (2 * self.dx)

                # 动量方程 Jacobian（解析推导）
                # F[2*i+1] = d(Q²/A)/dx + gA·dh/dx - gA(S₀ - Sf)

                h_safe = np.maximum(h, 1e-6)
                A = self.B * h_safe
                A_im1 = self.B * np.maximum(h[i-1], 1e-6)
                A_ip1 = self.B * np.maximum(h[i+1], 1e-6)

                # ∂F/∂h_{i-1}
                # 来自 d(Q²/A)/dx 和 dh/dx
                dA_dh = self.B
                d_momentum_flux_dh_im1 = -Q[i-1]**2 / A_im1**2 * dA_dh
                d_momentum_flux_dh_im1 *= -1.0 / (2 * self.dx)  # 差分贡献

                dh_dx_dh_im1 = -1.0 / (2 * self.dx)
                pressure_dh_im1 = self.g * A[i] * dh_dx_dh_im1

                J[2*i+1, 2*(i-1)] = d_momentum_flux_dh_im1 + pressure_dh_im1

                # ∂F/∂Q_{i-1}
                d_momentum_flux_dQ_im1 = 2 * Q[i-1] / A_im1 * (-1.0 / (2 * self.dx))
                J[2*i+1, 2*(i-1)+1] = d_momentum_flux_dQ_im1

                # ∂F/∂h_i
                # 来自伪时间项、压力项、源项中的A_i和Sf_i
                pseudo_time_dh_i = 1.0 / self.pseudo_dt  # 伪时间项的导数

                pressure_dh_i = self.g * dA_dh * (h[i+1] - h[i-1]) / (2 * self.dx)

                # Sf对h的导数（数值微分，更精确）
                eps_h = 1e-6
                h_pert = h.copy()
                h_pert[i] += eps_h
                Sf_pert = self.compute_friction_slope(h_pert, Q)
                dSf_dh_i = (Sf_pert[i] - Sf[i]) / eps_h

                source_dh_i = self.g * (dA_dh * (self.S0 - Sf[i]) - A[i] * dSf_dh_i)

                J[2*i+1, 2*i] = pseudo_time_dh_i + pressure_dh_i - source_dh_i

                # ∂F/∂Q_i
                # 来自源项中的Sf_i（数值微分）
                eps_Q = 1e-6
                Q_pert = Q.copy()
                Q_pert[i] += eps_Q
                Sf_pert = self.compute_friction_slope(h, Q_pert)
                dSf_dQ_i = (Sf_pert[i] - Sf[i]) / eps_Q

                source_dQ_i = -self.g * A[i] * dSf_dQ_i

                # 加上伪时间项的贡献
                J[2*i+1, 2*i+1] = source_dQ_i

                # ∂F/∂h_{i+1}
                d_momentum_flux_dh_ip1 = -Q[i+1]**2 / A_ip1**2 * dA_dh
                d_momentum_flux_dh_ip1 *= 1.0 / (2 * self.dx)

                dh_dx_dh_ip1 = 1.0 / (2 * self.dx)
                pressure_dh_ip1 = self.g * A[i] * dh_dx_dh_ip1

                J[2*i+1, 2*(i+1)] = d_momentum_flux_dh_ip1 + pressure_dh_ip1

                # ∂F/∂Q_{i+1}
                d_momentum_flux_dQ_ip1 = 2 * Q[i+1] / A_ip1 * (1.0 / (2 * self.dx))
                J[2*i+1, 2*(i+1)+1] = d_momentum_flux_dQ_ip1

        # ========== 上游边界（i=0） ==========
        # F[0] = Q[0] - Q_upstream
        J[0, 1] = 1.0  # ∂F[0]/∂Q_0

        # F[1] = h[0] - h_upstream（水深边界，修复Jacobian奇异性）
        J[1, 0] = 1.0  # ∂F[1]/∂h_0

        # ========== 下游边界（i=nx-1） ==========
        i = self.nx - 1

        # F[2*i] = h[i] - h_downstream
        J[2*i, 2*i] = 1.0  # ∂F/∂h_{nx-1}

        # F[2*i+1] = (Q[i]-Q_prev[i])/pseudo_dt + (Q[i] - Q[i-1]) / dx
        J[2*i+1, 2*(i-1)+1] = -1.0 / self.dx  # ∂F/∂Q_{nx-2}
        J[2*i+1, 2*i+1] = 1.0 / self.pseudo_dt + 1.0 / self.dx  # ∂F/∂Q_{nx-1}（伪时间+空间）

        return J.tocsr()


def test_steady_saint_venant():
    """测试稳态Saint-Venant系统"""
    print("=" * 80)
    print("稳态Saint-Venant系统测试")
    print("=" * 80)

    # 简单测试：恒定流（无闸门）
    length = 1000.0
    nx = 101
    B = 10.0
    S0 = 0.001
    n = 0.025
    Q_target = 10.0

    system = SteadySaintVenantSystem(length, nx, B, S0, n)

    # 使用恒定均匀流作为初值（应该接近解）
    from utils.canal_utils import compute_steady_uniform_flow
    h_uniform = compute_steady_uniform_flow(Q_target, B, S0, n)

    h_init = np.ones(nx) * h_uniform
    Q_init = np.ones(nx) * Q_target

    # 设置边界条件
    system.set_boundary_conditions(Q_upstream=Q_target, h_downstream=h_uniform)

    U_init = system.pack_state(h_init, Q_init)

    print(f"\n问题设置:")
    print(f"  渠道长度: {length} m")
    print(f"  节点数: {nx}")
    print(f"  目标流量: {Q_target} m³/s")
    print(f"  恒定均匀流水深: {h_uniform:.4f} m")

    # 计算残差
    print(f"\n初始残差:")
    F_init = system.compute_residual(U_init)
    print(f"  ||F|| = {np.linalg.norm(F_init):.3e}")

    # 计算Jacobian
    print(f"\nJacobian计算:")
    J = system.compute_jacobian(U_init)
    print(f"  矩阵大小: {J.shape}")
    print(f"  非零元素: {J.nnz} ({J.nnz/J.shape[0]**2*100:.2f}%)")

    # 验证Jacobian（与数值微分对比）
    print(f"\nJacobian验证（与数值微分对比）:")
    eps = 1e-7

    # 随机选择几个变量验证
    np.random.seed(42)
    test_indices = np.random.choice(system.n_vars, min(10, system.n_vars), replace=False)

    max_error = 0.0
    for j in test_indices:
        # 解析Jacobian
        J_analytical = J[:, j].toarray().flatten()

        # 数值Jacobian
        U_pert = U_init.copy()
        U_pert[j] += eps
        F_pert = system.compute_residual(U_pert)
        J_numerical = (F_pert - F_init) / eps

        # 误差
        error = np.linalg.norm(J_analytical - J_numerical)
        max_error = max(max_error, error)

    print(f"  最大误差: {max_error:.3e}")
    if max_error < 1e-5:
        print(f"  ✓ Jacobian验证通过！")
    else:
        print(f"  ✗ Jacobian误差较大，需检查")

    print("\n" + "=" * 80)


if __name__ == "__main__":
    test_steady_saint_venant()
