#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
详细分析Jacobian矩阵结构

找出奇异性的根本原因

作者: Claude
日期: 2025-10-22
"""

import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

import numpy as np
from physics.steady_saint_venant import SteadySaintVenantSystem
from utils.canal_utils import compute_steady_uniform_flow


def analyze_jacobian_structure():
    """详细分析Jacobian结构"""

    print("=" * 100)
    print("Jacobian矩阵结构详细分析")
    print("=" * 100)
    print()

    # 使用小网格便于分析
    length = 100.0
    nx = 6  # 更小的网格
    B = 10.0
    S0 = 0.001
    n = 0.025
    Q_target = 10.0

    h_uniform = compute_steady_uniform_flow(Q_target, B, S0, n)

    print(f"网格: nx={nx}, 总变量={2*nx}")
    print()

    # 创建系统
    system = SteadySaintVenantSystem(length, nx, B, S0, n, pseudo_dt=0.1)
    system.set_boundary_conditions(Q_upstream=Q_target, h_downstream=h_uniform)

    # 状态向量
    h = np.ones(nx) * h_uniform
    Q = np.ones(nx) * Q_target
    U = system.pack_state(h, Q)
    system.U_prev = U.copy()

    # 计算Jacobian
    J = system.compute_jacobian(U, t=0.0)
    J_dense = J.toarray()

    print("变量索引对应关系:")
    print("-" * 100)
    for i in range(nx):
        h_idx = 2 * i
        Q_idx = 2 * i + 1
        print(f"  节点 i={i}: h_{i} → index {h_idx}, Q_{i} → index {Q_idx}")
    print()

    print("方程索引对应关系:")
    print("-" * 100)
    for i in range(nx):
        eq_h_idx = 2 * i
        eq_Q_idx = 2 * i + 1
        if i == 0:
            print(f"  节点 i={i}: F[{eq_h_idx}] = Q_0 - Q_upstream (上游边界)")
            print(f"  节点 i={i}: F[{eq_Q_idx}] = 连续性 (伪瞬态)")
        elif i == nx - 1:
            print(f"  节点 i={i}: F[{eq_h_idx}] = h_{i} - h_downstream (下游边界)")
            print(f"  节点 i={i}: F[{eq_Q_idx}] = 连续性 (伪瞬态)")
        else:
            print(f"  节点 i={i}: F[{eq_h_idx}] = 连续性 (伪瞬态)")
            print(f"  节点 i={i}: F[{eq_Q_idx}] = 动量 (伪瞬态)")
    print()

    print("Jacobian对角线元素:")
    print("-" * 100)
    diag = np.diag(J_dense)
    for idx, val in enumerate(diag):
        var_name = f"h_{idx//2}" if idx % 2 == 0 else f"Q_{idx//2}"
        eq_desc = get_equation_description(idx, nx)
        zero_str = "  ← ZERO!" if abs(val) < 1e-10 else ""
        print(f"  J[{idx:2d},{idx:2d}] (∂F_{idx}/∂{var_name}): {val:12.6f}  ({eq_desc}){zero_str}")
    print()

    zero_diag_count = np.sum(np.abs(diag) < 1e-10)
    print(f"零对角元素数量: {zero_diag_count} / {2*nx}")
    print()

    # 检查每一行的非零模式
    print("Jacobian稀疏模式（每行的非零元素）:")
    print("-" * 100)
    for row_idx in range(2*nx):
        nonzero_cols = np.nonzero(J_dense[row_idx, :])[0]
        eq_desc = get_equation_description(row_idx, nx)
        print(f"  F[{row_idx:2d}] ({eq_desc}): {len(nonzero_cols)} 非零元素 at columns {list(nonzero_cols)}")
    print()

    # 计算秩
    rank = np.linalg.matrix_rank(J_dense)
    print(f"矩阵秩: {rank} / {2*nx}")
    print()

    if rank < 2 * nx:
        print("⚠ 矩阵奇异！寻找线性相关的行...")
        # 使用SVD找到零空间
        U_svd, s, Vt = np.linalg.svd(J_dense)
        print(f"奇异值: {s}")
        print(f"最小奇异值: {s.min():.2e}")

        # 找到接近零的奇异值
        zero_sv_indices = np.where(s < 1e-10)[0]
        print(f"接近零的奇异值索引: {zero_sv_indices}")

        if len(zero_sv_indices) > 0:
            # 零空间向量
            null_vec = Vt[zero_sv_indices[0], :]
            print(f"\n零空间向量（归一化）:")
            for idx, val in enumerate(null_vec):
                if abs(val) > 0.01:  # 只显示显著的分量
                    var_name = f"h_{idx//2}" if idx % 2 == 0 else f"Q_{idx//2}"
                    print(f"  {var_name}: {val:.6f}")

    print()

    # 打印完整的Jacobian矩阵（如果足够小）
    if 2 * nx <= 12:
        print("完整Jacobian矩阵:")
        print("-" * 100)
        np.set_printoptions(precision=3, linewidth=200, suppress=True)
        print(J_dense)
        print()


def get_equation_description(idx, nx):
    """获取方程描述"""
    i = idx // 2
    is_h_var = (idx % 2 == 0)

    if i == 0:
        if is_h_var:
            return "Q_0 BC"
        else:
            return "连续性 (上游边界)"
    elif i == nx - 1:
        if is_h_var:
            return "h_n BC"
        else:
            return "连续性 (下游边界)"
    else:
        if is_h_var:
            return "连续性"
        else:
            return "动量"


if __name__ == '__main__':
    analyze_jacobian_structure()
