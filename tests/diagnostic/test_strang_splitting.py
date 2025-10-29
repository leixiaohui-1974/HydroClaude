#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Strang Splitting源项处理方法测试

对比coupled RK2 vs Strang Splitting对MacDonald场景质量守恒的影响

目标：验证Strang Splitting能否改善质量守恒（60% → 30-40%）
"""

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '../..'))

import numpy as np
from solvers.godunov_fvm_solver import GodunvFVMSolver


def test_strang_splitting_comparison():
    """对比coupled RK2 vs Strang Splitting源项处理方法"""

    print("\n" + "="*80)
    print("Strang Splitting源项处理方法对比测试")
    print("="*80)

    B = 1.0
    L = 1000.0
    n_cells = 20

    Q_bc = 2.0
    g = 9.81
    h_c = (Q_bc**2 / (g * B**2))**(1/3)

    print(f"\n测试场景（MacDonald类型）:")
    print(f"  渠道长度: {L} m")
    print(f"  单元数: {n_cells}")
    print(f"  底坡: 0.002")
    print(f"  Manning n: 0.03")
    print(f"  边界: Q={Q_bc} m³/s, h={h_c:.4f} m (临界水深)")
    print(f"\n预期：Strang Splitting应改善质量守恒（目标：60% → 30-40%）")

    # 测试1: Coupled RK2（当前标准方法）
    print(f"\n{'='*80}")
    print("测试1: source_term_treatment='coupled' (标准TVD-RK2)")
    print("="*80)

    solver1 = GodunvFVMSolver(
        width=B,
        length=L,
        n_cells=n_cells,
        manning_n=0.03,
        slope=0.002,
        cfl=0.4,
        order=1,
        well_balanced=False,
        source_term_treatment='coupled',  # 标准耦合方法
        use_numba=False
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

    print(f"\n结果（coupled）:")
    print(f"  质量误差: {mass_error_1:.2f}%")
    print(f"  平均流量: {Q_avg_1:.4f} m³/s (目标: {Q_bc})")
    print(f"  流量误差: {abs(Q_avg_1 - Q_bc)/Q_bc*100:.2f}%")

    # 测试2: Strang Splitting（新方法）
    print(f"\n{'='*80}")
    print("测试2: source_term_treatment='strang_splitting' (算子分裂法)")
    print("="*80)

    solver2 = GodunvFVMSolver(
        width=B,
        length=L,
        n_cells=n_cells,
        manning_n=0.03,
        slope=0.002,
        cfl=0.4,
        order=1,
        well_balanced=False,
        source_term_treatment='strang_splitting',  # Strang Splitting
        use_numba=False
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

    print(f"\n结果（strang_splitting）:")
    print(f"  质量误差: {mass_error_2:.2f}%")
    print(f"  平均流量: {Q_avg_2:.4f} m³/s (目标: {Q_bc})")
    print(f"  流量误差: {abs(Q_avg_2 - Q_bc)/Q_bc*100:.2f}%")

    # 对比
    print(f"\n{'='*80}")
    print("对比结果")
    print("="*80)

    print(f"\n{'方法':<35} {'质量误差':>12} {'流量误差':>12} {'改善':>12}")
    print("-" * 75)
    print(f"{'coupled (标准TVD-RK2)':<35} {mass_error_1:11.2f}% {abs(Q_avg_1-Q_bc)/Q_bc*100:11.2f}%")
    print(f"{'strang_splitting (算子分裂)':<35} {mass_error_2:11.2f}% {abs(Q_avg_2-Q_bc)/Q_bc*100:11.2f}%")

    mass_improvement = mass_error_1 - mass_error_2
    flow_improvement = abs(Q_avg_1-Q_bc)/Q_bc*100 - abs(Q_avg_2-Q_bc)/Q_bc*100

    print("-" * 75)
    print(f"{'改善':<35} {mass_improvement:11.2f}% {flow_improvement:11.2f}%")

    print(f"\n总结:")

    # 质量守恒评估
    if mass_error_2 < 5.0:
        if abs(mass_error_2) < abs(mass_error_1) * 0.1:
            print(f"  ✅ Strang Splitting显著改善质量守恒！ (误差<5%，改善>90%)")
        else:
            print(f"  ✅ Strang Splitting达到优秀质量守恒 (误差<5%)")
    elif abs(mass_error_2) < abs(mass_error_1) * 0.7:
        print(f"  ✅ Strang Splitting显著改善质量守恒 (改善>30%)")
    elif abs(mass_error_2) < abs(mass_error_1):
        print(f"  ⚠️ Strang Splitting略有改善 (改善<30%)")
    else:
        print(f"  ✗ Strang Splitting无改善或变差")

    # 流量守恒评估
    if abs(Q_avg_2 - Q_bc) / Q_bc < 0.05:
        print(f"  ✅ Strang Splitting流量守恒优秀 (<5%)")
    elif abs(Q_avg_2 - Q_bc) < abs(Q_avg_1 - Q_bc) * 0.5:
        print(f"  ✅ Strang Splitting流量显著改善 (改善>50%)")
    elif abs(Q_avg_2 - Q_bc) < abs(Q_avg_1 - Q_bc):
        print(f"  ⚠️ Strang Splitting流量略有改善")
    else:
        print(f"  ✗ Strang Splitting流量无改善或变差")

    print("\n" + "="*80)
    print("技术分析:")
    print("="*80)
    print("\nCoupled RK2方法:")
    print("  L(U) = -∂F/∂x + S")
    print("  U^{n+1} = RK2(L(U))")
    print("  问题：通量和源项耦合，数值误差累积")
    print("\nStrang Splitting方法:")
    print("  步骤1: U* = U^n + dt/2 * (-∂F/∂x)  [只通量]")
    print("  步骤2: U** = U* + dt * S            [只源项]")
    print("  步骤3: U^{n+1} = U** + dt/2 * (-∂F/∂x)  [只通量]")
    print("  优点：解耦通量-源项，减少数值误差，保持二阶精度")

    print("="*80)

    return mass_error_1, mass_error_2, mass_improvement


if __name__ == "__main__":
    test_strang_splitting_comparison()
