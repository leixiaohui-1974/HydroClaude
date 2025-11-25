#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
静水测试

检查完全静止的水是否保持静止（Lake at Rest）
"""

import sys
import warnings
warnings.filterwarnings("ignore")
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '../..'))

import numpy as np
try:
    from solvers.godunov_fvm_solver import GodunvFVMSolver
except ImportError as e:
    print(f"Import error: {e}")
    print("Make sure project root is in sys.path")
    sys.exit(1)



def test_static_water():
    """静水测试"""

    print("\n" + "="*80)
    print("静水测试（Lake at Rest）")
    print("="*80)

    B = 5.0
    dx = 20.0

    solver = GodunvFVMSolver(
        width=B,
        length=100.0,
        n_cells=5,
        manning_n=0.03,
        slope=0.0,  # 平底
        cfl=0.4,
        order=1,
        use_numba=False
    )

    # 完全静水：h恒定，Q=0
    h_init = np.ones(5) * 1.0
    Q_init = np.zeros(5)

    bc_left = {'type': 'h', 'value': 1.0}
    bc_right = {'type': 'h', 'value': 1.0}

    solver.initialize(h_init, Q_init, bc_left, bc_right)

    mass_initial = np.sum(h_init * dx * B)

    print(f"\n初始状态：")
    print(f"  h = {h_init}")
    print(f"  Q = {Q_init}")
    print(f"  质量 = {mass_initial:.3f} m^3")

    print(f"\n运行10步...")
    print(f"\n{'步':<6} {'max|Q|':<12} {'max|Δh|':<12} {'质量':<12} {'Δm':<12}")
    print("-" * 60)

    for step in range(10):
        h_before = solver.h.copy()

        solver.step()

        max_Q = np.max(np.abs(solver.Q))
        max_dh = np.max(np.abs(solver.h - h_before))
        mass = np.sum(solver.h * dx * B)
        delta_mass = mass - mass_initial

        print(f"{step:<6} {max_Q:<12.6f} {max_dh:<12.6f} {mass:<12.3f} {delta_mass:<12.3f}")

    print(f"\n{'='*80}")
    print("理论：")
    print("  Lake at Rest：静水应保持静止")
    print("  - max|Q|应该=0")
    print("  - max|Δh|应该=0")
    print("  - 质量应该守恒")

    mass_final = np.sum(solver.h * dx * B)
    max_Q_final = np.max(np.abs(solver.Q))
    mass_error = abs(mass_final - mass_initial) / mass_initial * 100

    print(f"\n实际：")
    print(f"  最终max|Q| = {max_Q_final:.6f}")
    print(f"  质量误差 = {mass_error:.2f}%")

    if max_Q_final < 1e-10 and mass_error < 0.01:
        print(f"\n Lake at Rest成立")
    else:
        print(f"\n Lake at Rest失败")
        if max_Q_final > 1e-10:
            print(f"   静水产生了流动")
        if mass_error > 0.01:
            print(f"   质量不守恒")

    print("="*80)


if __name__ == "__main__":
    test_static_water()
