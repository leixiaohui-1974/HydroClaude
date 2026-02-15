#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
MacDonald Test 2质量守恒问题诊断

Test 2在修复后质量误差33.6%，需要诊断原因
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



def test_macdonald_test2_mass():
    """诊断Test 2质量守恒"""

    print("\n" + "="*80)
    print("MacDonald Test 2质量守恒诊断")
    print("="*80)

    # Test 2参数
    B = 5.0
    L = 5000.0
    S0 = 0.002
    n = 0.03
    Q = 2.0
    g = 9.81
    n_cells = 100

    # 临界水深
    h_c = (Q**2 / (g * B**2))**(1/3)

    # 正常水深
    h_n = 2.414  # 从测试输出获取

    print(f"\n参数：")
    print(f"  Q = {Q} m^3/s")
    print(f"  h_c = {h_c:.3f} m")
    print(f"  h_n = {h_n:.3f} m")
    print(f"  n_cells = {n_cells}")

    # 创建求解器
    solver = GodunvFVMSolver(
        width=B,
        length=L,
        n_cells=n_cells,
        manning_n=n,
        slope=S0,
        cfl=0.5,
        order=1,  # 改为1阶测试
        use_numba=False  # 关闭numba
    )

    # 初始条件：从h_n到h_c
    h_init = np.linspace(h_n, h_c * 1.1, n_cells)
    Q_init = np.ones(n_cells) * Q

    # 边界条件
    bc_left = {'type': 'Q', 'value': Q}
    bc_right = {'type': 'h', 'value': h_c}

    solver.initialize(h_init, Q_init, bc_left, bc_right)

    print(f"\n初始质量 = {solver.initial_mass:.2f} m^3")

    # 运行到稳态
    t_end = 50.0
    cumulative_inflow = 0.0
    cumulative_outflow = 0.0

    print(f"\n运行到 t={t_end}s，每300s记录一次...")
    print(f"\n{'时间(s)':<10} {'实际质量':<12} {'理论质量':<12} {'差异(%)':<10} {'h[-1]':<10}")
    print("-" * 60)

    while solver.t < t_end:
        dt = solver.compute_dt()
        solver.step()

        # 累积通量
        if solver.last_F_h is not None:
            cumulative_inflow += solver.last_F_h[0] * dt
            cumulative_outflow += solver.last_F_h[-1] * dt

        # 记录
        if int(solver.t) % 300 < dt or solver.t >= t_end:
            mass_actual = np.sum(solver.h * solver.dx * solver.B)
            mass_theory = solver.initial_mass + cumulative_inflow - cumulative_outflow
            error = abs(mass_actual - mass_theory) / abs(mass_theory) * 100

            print(f"{solver.t:<10.1f} {mass_actual:<12.2f} {mass_theory:<12.2f} {error:<10.2f} {solver.h[-1]:<10.3f}")

    # 最终分析
    mass_final = np.sum(solver.h * solver.dx * solver.B)
    mass_theory_final = solver.initial_mass + cumulative_inflow - cumulative_outflow
    mass_error = abs(mass_final - mass_theory_final) / abs(mass_theory_final) * 100

    print(f"\n{'='*80}")
    print("最终结果")
    print("="*80)
    print(f"  初始质量：{solver.initial_mass:.2f} m^3")
    print(f"  实际质量：{mass_final:.2f} m^3")
    print(f"  理论质量：{mass_theory_final:.2f} m^3")
    print(f"  累积流入：{cumulative_inflow:.2f} m^3")
    print(f"  累积流出：{cumulative_outflow:.2f} m^3")
    print(f"  质量误差：{mass_error:.2f}%")

    print(f"\n边界单元状态：")
    print(f"  h[0] = {solver.h[0]:.3f} m")
    print(f"  h[-1] = {solver.h[-1]:.3f} m (目标={h_c:.3f} m)")
    print(f"  Q[0] = {solver.Q[0]:.3f} m^3/s (目标={Q:.3f} m^3/s)")
    print(f"  Q[-1] = {solver.Q[-1]:.3f} m^3/s")

    # 检查边界通量
    if solver.last_F_h is not None:
        print(f"\n最后一步的边界通量：")
        print(f"  F_h[0] (左) = {solver.last_F_h[0]:.3f} m^2/s")
        print(f"  F_h[-1] (右) = {solver.last_F_h[-1]:.3f} m^2/s")
        print(f"  Q[0] (期望) = {Q:.3f} m^3/s")
        print(f"  Q[-1] * 1 = {solver.Q[-1]:.3f} m^3/s")

    # 质量守恒评估
    print(f"\n{'='*80}")
    if mass_error < 1.0:
        print(" 质量守恒良好 (<1.0%)")
    else:
        print(f" 质量守恒较差 ({mass_error:.2f}%)")
        print(f"\n可能原因：")
        print(f"  1. 右边界h={h_c:.3f}是临界水深，流动不稳定")
        print(f"  2. 边界单元h[-1]={solver.h[-1]:.3f}偏离目标，影响通量计算")
        print(f"  3. order=2可能在临界流附近不稳定")

    print("="*80)


if __name__ == "__main__":
    test_macdonald_test2_mass()
