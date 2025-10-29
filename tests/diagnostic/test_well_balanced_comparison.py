#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Well-Balanced模式对比测试

对比well_balanced=True和False对MacDonald场景质量守恒的影响
"""

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '../..'))

import numpy as np
from solvers.godunov_fvm_solver import GodunvFVMSolver


def test_well_balanced_comparison():
    """对比well_balanced模式"""

    print("\n" + "="*80)
    print("Well-Balanced模式对比测试")
    print("="*80)

    B = 1.0
    L = 1000.0
    n_cells = 20

    Q_bc = 2.0
    g = 9.81
    h_c = (Q_bc**2 / (g * B**2))**(1/3)

    print(f"\n测试场景（类MacDonald）:")
    print(f"  渠道长度: {L} m")
    print(f"  单元数: {n_cells}")
    print(f"  底坡: 0.002")
    print(f"  Manning n: 0.03")
    print(f"  边界: Q={Q_bc} m³/s, h={h_c:.4f} m")

    # 测试1: well_balanced=False（当前MacDonald使用的）
    print(f"\n{'='*80}")
    print("测试1: well_balanced=False（标准格式）")
    print("="*80)

    solver1 = GodunvFVMSolver(
        width=B,
        length=L,
        n_cells=n_cells,
        manning_n=0.03,
        slope=0.002,
        cfl=0.4,
        order=1,
        well_balanced=False
    )

    h_init = np.linspace(h_c * 1.5, h_c, n_cells)
    Q_init = np.ones(n_cells) * Q_bc

    bc_left = {'type': 'Q', 'value': Q_bc}
    bc_right = {'type': 'h', 'value': h_c}

    solver1.initialize(h_init, Q_init, bc_left, bc_right)

    # 运行500s
    t_final = 500.0
    print(f"\n运行到 t={t_final}s...")

    step_count = 0
    while solver1.t < t_final and step_count < 5000:
        solver1.step()
        step_count += 1

        if step_count % 50 == 0:
            mass_error = solver1.get_mass_conservation_error()
            print(f"  t={solver1.t:6.1f}s, 步数={step_count:4d}, 质量误差={mass_error:7.3f}%")

    mass_error_1 = solver1.get_mass_conservation_error()
    Q_avg_1 = np.mean(solver1.Q)

    print(f"\n结果（well_balanced=False）:")
    print(f"  质量误差: {mass_error_1:.2f}%")
    print(f"  平均流量: {Q_avg_1:.4f} m³/s (目标: {Q_bc})")
    print(f"  流量误差: {abs(Q_avg_1 - Q_bc)/Q_bc*100:.2f}%")

    # 测试2: well_balanced=True
    print(f"\n{'='*80}")
    print("测试2: well_balanced=True（Well-Balanced格式）")
    print("="*80)

    solver2 = GodunvFVMSolver(
        width=B,
        length=L,
        n_cells=n_cells,
        manning_n=0.03,
        slope=0.002,
        cfl=0.4,
        order=1,
        well_balanced=True  # 启用well-balanced
    )

    solver2.initialize(h_init, Q_init, bc_left, bc_right)

    print(f"\n运行到 t={t_final}s...")

    step_count = 0
    while solver2.t < t_final and step_count < 5000:
        solver2.step()
        step_count += 1

        if step_count % 50 == 0:
            mass_error = solver2.get_mass_conservation_error()
            print(f"  t={solver2.t:6.1f}s, 步数={step_count:4d}, 质量误差={mass_error:7.3f}%")

    mass_error_2 = solver2.get_mass_conservation_error()
    Q_avg_2 = np.mean(solver2.Q)

    print(f"\n结果（well_balanced=True）:")
    print(f"  质量误差: {mass_error_2:.2f}%")
    print(f"  平均流量: {Q_avg_2:.4f} m³/s (目标: {Q_bc})")
    print(f"  流量误差: {abs(Q_avg_2 - Q_bc)/Q_bc*100:.2f}%")

    # 对比
    print(f"\n{'='*80}")
    print("对比结果")
    print("="*80)

    print(f"\n{'模式':<25} {'质量误差':>12} {'流量误差':>12} {'改善':>12}")
    print("-" * 65)
    print(f"{'well_balanced=False':<25} {mass_error_1:11.2f}% {abs(Q_avg_1-Q_bc)/Q_bc*100:11.2f}%")
    print(f"{'well_balanced=True':<25} {mass_error_2:11.2f}% {abs(Q_avg_2-Q_bc)/Q_bc*100:11.2f}%")

    mass_improvement = mass_error_1 - mass_error_2
    flow_improvement = abs(Q_avg_1-Q_bc)/Q_bc*100 - abs(Q_avg_2-Q_bc)/Q_bc*100

    print("-" * 65)
    print(f"{'改善':<25} {mass_improvement:11.2f}% {flow_improvement:11.2f}%")

    print(f"\n总结:")
    if abs(mass_error_2) < abs(mass_error_1) * 0.5:
        print(f"  ✅ Well-Balanced格式显著改善质量守恒")
    elif abs(mass_error_2) < abs(mass_error_1):
        print(f"  ⚠️ Well-Balanced格式略有改善")
    else:
        print(f"  ✗ Well-Balanced格式无改善或变差")

    if abs(Q_avg_2 - Q_bc) < abs(Q_avg_1 - Q_bc) * 0.5:
        print(f"  ✅ Well-Balanced格式显著改善流量守恒")
    elif abs(Q_avg_2 - Q_bc) < abs(Q_avg_1 - Q_bc):
        print(f"  ⚠️ Well-Balanced格式略有改善流量")
    else:
        print(f"  ✗ Well-Balanced格式无改善或变差流量")

    print("="*80)


if __name__ == "__main__":
    test_well_balanced_comparison()
