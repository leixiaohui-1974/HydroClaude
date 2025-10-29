#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
直接质量守恒测试

不依赖通量累积，直接比较初始和最终质量
"""

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '../..'))

import numpy as np
from solvers.godunov_fvm_solver import GodunvFVMSolver


def test_direct_mass():
    """直接质量守恒测试"""

    print("\n" + "="*80)
    print("直接质量守恒测试（不依赖通量累积）")
    print("="*80)

    B = 5.0
    dx = 20.0

    solver = GodunvFVMSolver(
        width=B,
        length=100.0,
        n_cells=5,
        manning_n=0.03,
        slope=0.002,
        cfl=0.4,
        order=1,
        use_numba=False
    )

    # 封闭系统测试：左右都是h边界
    h_init = np.array([1.0, 0.9, 0.8, 0.9, 1.0])
    Q_init = np.zeros(5)  # 静水

    bc_left = {'type': 'h', 'value': 1.0}
    bc_right = {'type': 'h', 'value': 1.0}

    solver.initialize(h_init, Q_init, bc_left, bc_right)

    mass_initial = np.sum(h_init * dx * B)

    print(f"\n场景1：封闭系统（左右h边界，静水）")
    print(f"  初始质量 = {mass_initial:.3f} m³")
    print(f"  理论：封闭系统质量应守恒")

    # 运行100步
    for _ in range(100):
        solver.step()

    mass_final = np.sum(solver.h * dx * B)
    delta_mass = mass_final - mass_initial
    error = abs(delta_mass) / mass_initial * 100

    print(f"\n  最终质量 = {mass_final:.3f} m³")
    print(f"  质量变化 = {delta_mass:.3f} m³ ({error:.2f}%)")

    if error < 0.1:
        print(f"\n  ✅ 质量守恒成立（封闭系统）")
    else:
        print(f"\n  ❌ 质量守恒失败（封闭系统）")

    # 场景2：有流动的系统
    print(f"\n{'='*80}")
    print("场景2：有流动系统（左Q右h）")

    solver2 = GodunvFVMSolver(
        width=B,
        length=100.0,
        n_cells=5,
        manning_n=0.03,
        slope=0.002,
        cfl=0.4,
        order=1,
        use_numba=False
    )

    h_init2 = np.ones(5)
    Q_init2 = np.ones(5) * 2.0

    bc_left2 = {'type': 'Q', 'value': 2.0}
    bc_right2 = {'type': 'h', 'value': 0.7}

    solver2.initialize(h_init2, Q_init2, bc_left2, bc_right2)

    mass_initial2 = np.sum(h_init2 * dx * B)
    print(f"  初始质量 = {mass_initial2:.3f} m³")

    # 运行10步
    for _ in range(10):
        solver2.step()

    mass_final2 = np.sum(solver2.h * dx * B)
    delta_mass2 = mass_final2 - mass_initial2

    print(f"  最终质量 = {mass_final2:.3f} m³")
    print(f"  质量变化 = {delta_mass2:.3f} m³")
    print(f"\n  注：开放系统质量应该变化（有流入流出）")

    # 场景3：单步详细检查
    print(f"\n{'='*80}")
    print("场景3：单步详细质量守恒检查")

    solver3 = GodunvFVMSolver(
        width=B,
        length=100.0,
        n_cells=5,
        manning_n=0.03,
        slope=0.002,
        cfl=0.4,
        order=1,
        use_numba=False
    )

    h_init3 = np.ones(5)
    Q_init3 = np.ones(5) * 2.0

    bc_left3 = {'type': 'Q', 'value': 2.0}
    bc_right3 = {'type': 'h', 'value': 0.7}

    solver3.initialize(h_init3, Q_init3, bc_left3, bc_right3)

    # 手动执行RK2，检查质量守恒
    h_n = solver3.h.copy()
    Q_n = solver3.Q.copy()
    mass_n = np.sum(h_n * dx * B)

    dt = solver3.compute_dt()

    # 第1步
    dh_dt1, dQ_dt1 = solver3._compute_rhs(h_n, Q_n)
    h_star = h_n + dt * dh_dt1
    Q_star = Q_n + dt * dQ_dt1
    h_star = np.maximum(h_star, 0.0)
    mass_star = np.sum(h_star * dx * B)

    # 第2步
    dh_dt2, dQ_dt2 = solver3._compute_rhs(h_star, Q_star)
    h_final = 0.5 * (h_n + h_star) + 0.5 * dt * dh_dt2
    Q_final = 0.5 * (Q_n + Q_star) + 0.5 * dt * dQ_dt2
    h_final = np.maximum(h_final, 0.0)

    # 不调用_apply_bc！
    # h_final, Q_final = solver3._apply_bc(h_final, Q_final)

    mass_final3 = np.sum(h_final * dx * B)
    delta_mass3 = mass_final3 - mass_n

    print(f"  初始质量 = {mass_n:.3f} m³")
    print(f"  手动RK2后质量 = {mass_final3:.3f} m³")
    print(f"  质量变化 = {delta_mass3:.3f} m³")

    # 现在调用solver.step()看看
    solver3.h = h_n.copy()
    solver3.Q = Q_n.copy()
    solver3.t = 0.0
    solver3.step()
    mass_after_step = np.sum(solver3.h * dx * B)
    delta_mass_step = mass_after_step - mass_n

    print(f"\n  solver.step()后质量 = {mass_after_step:.3f} m³")
    print(f"  质量变化 = {delta_mass_step:.3f} m³")

    diff = abs(mass_final3 - mass_after_step)
    print(f"\n  差异 = {diff:.6f} m³")

    if diff < 1e-6:
        print(f"  ✅ 手动RK2和solver.step()结果一致")
    else:
        print(f"  ❌ 手动RK2和solver.step()结果不一致")
        print(f"     这说明solver.step()中有额外操作影响质量")

    print("\n" + "="*80)


if __name__ == "__main__":
    test_direct_mass()
