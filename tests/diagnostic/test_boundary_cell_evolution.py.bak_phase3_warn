#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
边界单元演化监控

检查边界单元是否被强制覆盖
"""

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '../..'))

import numpy as np
try:
    from solvers.godunov_fvm_solver import GodunvFVMSolver
except ImportError as e:
    print(f"Import error: {e}")
    print("Make sure project root is in sys.path")
    sys.exit(1)



def test_boundary_evolution():
    """监控边界单元演化"""

    print("\n" + "="*80)
    print("边界单元演化监控")
    print("="*80)

    B = 5.0
    Q_bc = 2.0
    h_bc = 0.7

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

    h_init = np.ones(5) * 1.0
    Q_init = np.ones(5) * Q_bc

    bc_left = {'type': 'Q', 'value': Q_bc}
    bc_right = {'type': 'h', 'value': h_bc}

    solver.initialize(h_init, Q_init, bc_left, bc_right)

    print(f"\n边界条件：")
    print(f"  左：Q = {Q_bc} m^3/s")
    print(f"  右：h = {h_bc} m")

    print(f"\n{'步骤':<6} {'h[0]':<10} {'h[-1]':<10} {'Q[0]':<10} {'Q[-1]':<10} {'质量':<12}")
    print("-" * 60)

    dx = solver.dx
    for step in range(10):
        h0_before = solver.h[0]
        h_1_before = solver.h[-1]
        Q0_before = solver.Q[0]
        Q_1_before = solver.Q[-1]
        mass_before = np.sum(solver.h * dx * B)

        dt = solver.compute_dt()
        solver.step()

        h0_after = solver.h[0]
        h_1_after = solver.h[-1]
        Q0_after = solver.Q[0]
        Q_1_after = solver.Q[-1]
        mass_after = np.sum(solver.h * dx * B)

        print(f"{step:<6} {h0_after:<10.3f} {h_1_after:<10.3f} {Q0_after:<10.3f} {Q_1_after:<10.3f} {mass_after:<12.2f}")

        # 检查是否被强制
        if step == 0:
            # 第一步：检查Q[0]是否被强制为Q_bc
            if abs(Q0_after - Q_bc) < 1e-6:
                print(f"   ️ Q[0]被强制为{Q_bc}")

            # 检查h[-1]是否被强制为h_bc
            if abs(h_1_after - h_bc) < 1e-6:
                print(f"   ️ h[-1]被强制为{h_bc}")

    print("\n" + "="*80)
    print("分析：")
    print("  如果Q[0]或h[-1]保持不变（或跳跃式变化），说明被强制")
    print("  如果平滑演化，说明由守恒律自然演化")
    print("="*80)


if __name__ == "__main__":
    test_boundary_evolution()
