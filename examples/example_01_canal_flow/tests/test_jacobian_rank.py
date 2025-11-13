#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
测试Jacobian矩阵的秩和条件数

验证伪瞬态项是否真正消除了奇异性

作者: Claude
日期: 2025-10-22
"""

import os
import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

import numpy as np
from physics.steady_saint_venant import SteadySaintVenantSystem
from utils.canal_utils import compute_steady_uniform_flow


def test_jacobian_rank():
    """测试Jacobian矩阵的秩"""

    print("=" * 100)
    print("Jacobian矩阵秩和条件数测试")
    print("=" * 100)
    print()

    # 渠道参数（使用小网格便于分析）
    length = 100.0
    nx = 11  # 小网格
    B = 10.0
    S0 = 0.001
    n = 0.025
    Q_target = 10.0

    # 计算恒定均匀流水深
    h_uniform = compute_steady_uniform_flow(Q_target, B, S0, n)

    print(f"网格参数:")
    print(f"  nx = {nx}")
    print(f"  总变量数 = {2*nx} (h和Q交替)")
    print(f"  理论均匀流水深 = {h_uniform:.4f} m")
    print()

    # 测试不同的pseudo_dt值
    pseudo_dt_values = [float('inf'), 10.0, 1.0, 0.1, 0.01, 0.001]

    print("测试不同伪时间步长的影响:")
    print("-" * 100)
    print(f"{'pseudo_dt':<15} {'矩阵秩':<12} {'理论秩':<12} {'条件数':<20} {'奇异性':<15}")
    print("-" * 100)

    for pseudo_dt in pseudo_dt_values:
        # 创建系统
        if pseudo_dt == float('inf'):
            # 无伪瞬态（纯稳态，应该奇异）
            system = SteadySaintVenantSystem(length, nx, B, S0, n, pseudo_dt=1e20)
            dt_label = "∞ (纯稳态)"
        else:
            system = SteadySaintVenantSystem(length, nx, B, S0, n, pseudo_dt=pseudo_dt)
            dt_label = f"{pseudo_dt}"

        system.set_boundary_conditions(Q_upstream=Q_target, h_downstream=h_uniform)

        # 使用均匀流作为状态点
        h = np.ones(nx) * h_uniform
        Q = np.ones(nx) * Q_target
        U = system.pack_state(h, Q)

        # 设置U_prev
        system.U_prev = U.copy()

        # 计算Jacobian
        J = system.compute_jacobian(U, t=0.0)
        J_dense = J.toarray()

        # 计算秩
        rank = np.linalg.matrix_rank(J_dense)
        expected_rank = 2 * nx

        # 计算条件数
        try:
            cond = np.linalg.cond(J_dense)
            cond_str = f"{cond:.2e}"
        except:
            cond_str = "inf (奇异)"

        # 判断是否奇异
        is_singular = (rank < expected_rank)
        singular_str = " 奇异" if is_singular else " 非奇异"

        print(f"{dt_label:<15} {rank:<12} {expected_rank:<12} {cond_str:<20} {singular_str:<15}")

    print()
    print("分析：")
    print("- 如果伪瞬态修复有效，pseudo_dt < ∞ 时应该非奇异")
    print("- 条件数应该随着pseudo_dt减小而改善（但不能太小）")
    print("- pseudo_dt太小（如0.001）会导致数值不稳定")
    print()

    # 详细检查一个情况
    print("\n" + "=" * 100)
    print("详细检查：pseudo_dt = 0.1")
    print("=" * 100)
    print()

    system = SteadySaintVenantSystem(length, nx, B, S0, n, pseudo_dt=0.1)
    system.set_boundary_conditions(Q_upstream=Q_target, h_downstream=h_uniform)
    system.U_prev = U.copy()

    J = system.compute_jacobian(U, t=0.0)
    J_dense = J.toarray()

    print("Jacobian矩阵属性:")
    print(f"  形状: {J_dense.shape}")
    print(f"  秩: {np.linalg.matrix_rank(J_dense)} / {2*nx}")
    print(f"  条件数: {np.linalg.cond(J_dense):.2e}")
    print(f"  最小奇异值: {np.linalg.svd(J_dense, compute_uv=False).min():.2e}")
    print(f"  最大奇异值: {np.linalg.svd(J_dense, compute_uv=False).max():.2e}")
    print()

    # 检查Jacobian的对角线
    diag = np.diag(J_dense)
    print("Jacobian对角线元素统计:")
    print(f"  最小值: {diag.min():.6f}")
    print(f"  最大值: {diag.max():.6f}")
    print(f"  零元素数: {np.sum(diag == 0)}")
    print()

    # 检查连续性方程的行（偶数行）
    continuity_rows = J_dense[::2, :]  # 偶数行
    print("连续性方程行（偶数行）分析:")
    print(f"  形状: {continuity_rows.shape}")

    # 检查第一个内部节点（i=1）的连续性方程
    i = 1
    row_idx = 2 * i
    row = J_dense[row_idx, :]
    print(f"\n内部节点 i={i} 的连续性方程 Jacobian:")
    print(f"  行索引: {row_idx}")

    # 找到非零元素
    nonzero_indices = np.nonzero(row)[0]
    print(f"  非零元素索引: {nonzero_indices}")
    for idx in nonzero_indices:
        var_name = f"h_{idx//2}" if idx % 2 == 0 else f"Q_{idx//2}"
        print(f"    J[{row_idx},{idx}] ({var_name}) = {row[idx]:.6f}")

    # 检查是否包含伪瞬态项（应该在 J[2*i, 2*i+1]）
    expected_pseudo_idx = 2 * i + 1
    if expected_pseudo_idx in nonzero_indices:
        print(f"\n   包含伪瞬态项 J[{row_idx},{expected_pseudo_idx}] = {row[expected_pseudo_idx]:.6f}")
        print(f"    预期值: 1/pseudo_dt = {1.0/0.1:.6f}")
    else:
        print(f"\n   缺少伪瞬态项 J[{row_idx},{expected_pseudo_idx}]")

    print()


if __name__ == '__main__':
    test_jacobian_rank()
