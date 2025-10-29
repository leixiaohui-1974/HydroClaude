#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
简单测试 - 验证h边界条件修复
"""

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '../..'))

import numpy as np
from solvers.godunov_fvm_solver import GodunvFVMSolver


def test_h_boundary_fix():
    """简单快速测试h边界修复"""

    print("\n" + "="*80)
    print("h边界条件修复验证 - 简单测试")
    print("="*80)

    # MacDonald Test 2参数（简化版本）
    B = 1.0
    n = 0.03
    S0 = 0.002
    L = 1000.0  # 短河道
    Q_bc = 2.0
    g = 9.81

    # 临界水深
    h_c = (Q_bc**2 / (g * B**2))**(1/3)

    print(f"\n参数：")
    print(f"  L = {L} m (短河道，快速测试)")
    print(f"  Q_left = {Q_bc} m³/s")
    print(f"  h_right = {h_c:.6f} m (临界水深)")

    # 创建求解器（禁用numba加速）
    n_cells = 50
    solver = GodunvFVMSolver(
        width=B,
        length=L,
        n_cells=n_cells,
        manning_n=n,
        slope=S0,
        cfl=0.4,
        order=1,  # 1阶
        use_numba=False  # 禁用numba
    )

    # 初始化
    h_init = np.ones(n_cells) * h_c * 1.5
    Q_init = np.ones(n_cells) * Q_bc

    bc_left = {'type': 'Q', 'value': Q_bc}
    bc_right = {'type': 'h', 'value': h_c}

    solver.initialize(h_init, Q_init, bc_left, bc_right)

    mass_initial = solver.initial_mass

    # 运行到稳态
    t_end = 500.0
    cumulative_inflow = 0.0
    cumulative_outflow = 0.0

    print(f"\n运行到 t={t_end}s...")

    step_count = 0
    while solver.t < t_end:
        dt = solver.compute_dt()
        solver.step()
        step_count += 1

        # 累积通量
        if solver.last_F_h is not None:
            F_left = solver.last_F_h[0]
            F_right = solver.last_F_h[-1]
            cumulative_inflow += F_left * dt * B
            cumulative_outflow += F_right * dt * B

    # 最终分析
    mass_final = np.sum(solver.h * solver.dx * B)
    delta_mass_actual = mass_final - mass_initial
    delta_mass_theory = cumulative_inflow - cumulative_outflow

    # 质量误差
    mass_error_pct = abs(mass_final - mass_initial) / mass_initial * 100

    # 通量守恒
    discrepancy_pct = abs(delta_mass_actual - delta_mass_theory) / abs(delta_mass_theory) * 100 if delta_mass_theory != 0 else 0

    # 流入流出比
    inflow_outflow_ratio = cumulative_inflow / cumulative_outflow if cumulative_outflow > 0 else 0

    print(f"\n结果：")
    print(f"  总步数：{step_count}")
    print(f"  质量误差：{mass_error_pct:.2f}%")
    print(f"  通量守恒：{discrepancy_pct:.2f}%")
    print(f"  累积流入：{cumulative_inflow:.2f} m³")
    print(f"  累积流出：{cumulative_outflow:.2f} m³")
    print(f"  流入/流出比：{inflow_outflow_ratio:.2f}")

    print(f"\n判断：")
    if mass_error_pct < 5.0:
        print(f"  ✅ 质量守恒良好 ({mass_error_pct:.2f}%)")
    else:
        print(f"  ❌ 质量误差过大 ({mass_error_pct:.2f}%)")

    if 0.9 < inflow_outflow_ratio < 1.1:
        print(f"  ✅ 流量平衡 (比值={inflow_outflow_ratio:.2f})")
    else:
        print(f"  ❌ 流量不平衡 (比值={inflow_outflow_ratio:.2f}, 应该≈1.0)")

    # 整体判断
    print(f"\n{'='*80}")
    if mass_error_pct < 5.0 and 0.9 < inflow_outflow_ratio < 1.1:
        print("✅ 修复成功！")
    else:
        print("❌ 修复未完全生效")

        # 调试信息
        print(f"\n可能原因：")
        if inflow_outflow_ratio > 1.5:
            print(f"  - 流出量仍然不足（{cumulative_outflow:.2f} vs {cumulative_inflow:.2f}）")
            print(f"  - ghost cells设置可能未正确强制临界流量")
        if discrepancy_pct > 1.0:
            print(f"  - 通量守恒有问题 ({discrepancy_pct:.2f}%)")

    print("="*80)

    return {
        'mass_error': mass_error_pct,
        'inflow_outflow_ratio': inflow_outflow_ratio,
        'flux_conservation': discrepancy_pct
    }


if __name__ == "__main__":
    result = test_h_boundary_fix()
