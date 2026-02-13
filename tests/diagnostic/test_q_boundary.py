#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Q边界诊断测试

专门测试Q（流量）边界条件的质量守恒和通量平衡
"""

import sys
import warnings
warnings.filterwarnings("ignore")
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '../..'))

import numpy as np
import pytest
try:
    from solvers.godunov_fvm_solver import GodunvFVMSolver
except ImportError as e:
    pytest.skip(f"Required module not available: {e}", allow_module_level=True)



def test_q_boundary_simple():
    """简单Q边界测试（无摩阻、水平床）"""

    print("\n" + "="*80)
    print("Q边界诊断测试 - 简单场景")
    print("="*80)

    B = 1.0
    L = 200.0
    n_cells = 10

    solver = GodunvFVMSolver(
        width=B,
        length=L,
        n_cells=n_cells,
        manning_n=0.0,  # 无摩阻
        slope=0.0,      # 水平床
        cfl=0.4,
        order=1,
        use_numba=False  # 关闭Numba便于调试
    )

    Q_bc = 2.0
    h_down = 2.0

    # 初始条件：均匀水深
    h_init = np.ones(n_cells) * h_down
    Q_init = np.ones(n_cells) * Q_bc

    bc_left = {'type': 'Q', 'value': Q_bc}
    bc_right = {'type': 'h', 'value': h_down}

    solver.initialize(h_init, Q_init, bc_left, bc_right)

    print(f"\n边界条件:")
    print(f"  左边界: Q = {Q_bc} m^3/s")
    print(f"  右边界: h = {h_down} m")

    print(f"\n初始状态:")
    print(f"  h[0] = {solver.h[0]:.6f} m")
    print(f"  Q[0] = {solver.Q[0]:.6f} m^3/s")
    print(f"  初始质量 = {solver._compute_total_mass():.2f} m^3")

    # 检查ghost cell设置
    h_ext, Q_ext = solver._extend_with_ghosts(solver.h, solver.Q)

    print(f"\nGhost cell检查:")
    print(f"  Ghost (左): h_ext[0]={h_ext[0]:.6f}, Q_ext[0]={Q_ext[0]:.6f}")
    print(f"  单元0:      h_ext[1]={h_ext[1]:.6f}, Q_ext[1]={Q_ext[1]:.6f}")
    print(f"  单元1:      h_ext[2]={h_ext[2]:.6f}, Q_ext[2]={Q_ext[2]:.6f}")

    # 检查界面0的通量
    h_L = h_ext[0]
    h_R = h_ext[1]
    Q_L = Q_ext[0]
    Q_R = Q_ext[1]

    F_h_0, F_Q_0 = solver._hll_flux(h_L, Q_L, h_R, Q_R)

    print(f"\n界面0通量（ghost|单元0）:")
    print(f"  左状态:  h_L={h_L:.6f}, Q_L={Q_L:.6f}")
    print(f"  右状态:  h_R={h_R:.6f}, Q_R={Q_R:.6f}")
    print(f"  计算通量: F_h={F_h_0:.6f} m^3/s")
    print(f"  理论值:   F_h={Q_bc:.6f} m^3/s (应该等于Q_bc)")
    print(f"  误差:     {abs(F_h_0 - Q_bc):.6f} m^3/s ({abs(F_h_0-Q_bc)/Q_bc*100:.2f}%)")

    # 时间演化
    print(f"\n时间演化:")
    print(f"{'步骤':>5} {'h[0](m)':>10} {'Q[0](m^3/s)':>12} {'质量(m^3)':>12} {'误差(%)':>10}")
    print("-" * 65)

    for step in range(10):
        solver.step()
        mass_error = solver.get_mass_conservation_error()

        print(f"{step+1:5d} {solver.h[0]:10.6f} {solver.Q[0]:12.6f} {solver._compute_total_mass():12.2f} {mass_error:10.4f}")

    print("\n" + "="*80)
    print("分析:")
    final_error = solver.get_mass_conservation_error()
    print(f"  最终质量误差 = {final_error:.4f}%")

    if abs(final_error) < 1.0:
        print("   质量守恒良好 (<1%)")
    elif abs(final_error) < 5.0:
        print("   质量守恒一般 (1-5%)")
    else:
        print("   质量守恒失败 (>5%)")

    print("="*80)


def test_q_boundary_with_manning():
    """Q边界测试（有摩阻、有坡度）- 类似MacDonald Test 2"""

    print("\n" + "="*80)
    print("Q边界诊断测试 - MacDonald场景")
    print("="*80)

    B = 1.0
    L = 1000.0  # 缩短以加快测试
    n_cells = 20

    solver = GodunvFVMSolver(
        width=B,
        length=L,
        n_cells=n_cells,
        manning_n=0.03,
        slope=0.002,
        cfl=0.4,
        order=1,
        use_numba=False
    )

    Q_bc = 2.0
    g = 9.81
    h_c = (Q_bc**2 / (g * B**2))**(1/3)  # 临界水深

    print(f"\n特征水深:")
    print(f"  临界水深 h_c = {h_c:.4f} m")

    # 初始条件
    h_init = np.linspace(h_c * 1.5, h_c, n_cells)
    Q_init = np.ones(n_cells) * Q_bc

    bc_left = {'type': 'Q', 'value': Q_bc}
    bc_right = {'type': 'h', 'value': h_c}

    solver.initialize(h_init, Q_init, bc_left, bc_right)

    print(f"\n边界条件:")
    print(f"  左边界: Q = {Q_bc} m^3/s")
    print(f"  右边界: h = {h_c:.4f} m (临界水深)")

    print(f"\n初始质量: {solver._compute_total_mass():.2f} m^3")

    # 运行到稳态
    t_final = 500.0
    print(f"\n运行到 t={t_final}s...")

    while solver.t < t_final:
        solver.step()

        if solver.step_count % 50 == 0:
            mass_error = solver.get_mass_conservation_error()
            print(f"  t={solver.t:6.1f}s, 步数={solver.step_count:4d}, 质量误差={mass_error:7.3f}%")

    print(f"\n最终状态:")
    print(f"  模拟时间: {solver.t:.2f} s")
    print(f"  总步数: {solver.step_count}")

    mass_error = solver.get_mass_conservation_error()
    print(f"  初始质量: {solver.initial_mass:.2f} m^3")
    print(f"  最终质量: {solver._compute_total_mass():.2f} m^3")
    print(f"  质量误差: {mass_error:.4f}%")

    # 计算平均流量
    Q_avg = np.mean(solver.Q)
    print(f"\n流量统计:")
    print(f"  边界条件: Q = {Q_bc} m^3/s")
    print(f"  平均流量: Q_avg = {Q_avg:.4f} m^3/s")
    print(f"  流量误差: {abs(Q_avg - Q_bc)/Q_bc*100:.2f}%")

    print("\n" + "="*80)
    print("分析:")

    if abs(mass_error) < 2.0:
        print("   质量守恒良好 (<2%)")
    elif abs(mass_error) < 10.0:
        print("   质量守恒一般 (2-10%)")
    else:
        print("   质量守恒失败 (>10%)")

    if abs(Q_avg - Q_bc) / Q_bc < 0.02:
        print("   流量守恒良好 (<2%)")
    else:
        print("   流量守恒失败 (>2%)")

    print("="*80)


if __name__ == "__main__":
    test_q_boundary_simple()
    test_q_boundary_with_manning()
