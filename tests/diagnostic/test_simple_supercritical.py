#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
简单急流测试

纯急流，避免水跃
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



def test_simple_supercritical():
    """简单急流测试：上下游都是急流"""

    print("\n" + "="*80)
    print("简单急流测试（无水跃）")
    print("="*80)

    B = 10.0
    L = 100.0
    n_cells = 20
    g = 9.81

    solver = GodunvFVMSolver(
        width=B,
        length=L,
        n_cells=n_cells,
        manning_n=0.0,
        slope=0.01,  # 陡坡
        cfl=0.4,
        order=1
    )

    # 上下游都是急流
    h_up = 0.3
    Q_up = 10.0
    h_down = 0.35  # 略微增加，但仍然是急流

    u_up = Q_up / (B * h_up)
    Fr_up = u_up / np.sqrt(g * h_up)

    u_down = Q_up / (B * h_down)  # 假设流量守恒
    Fr_down = u_down / np.sqrt(g * h_down)

    print(f"\n上游: h={h_up}m, Q={Q_up}m^3/s, u={u_up:.2f}m/s, Fr={Fr_up:.2f}")
    print(f"下游: h={h_down}m, Q={Q_up}m^3/s, u={u_down:.2f}m/s, Fr={Fr_down:.2f}")

    if Fr_up < 1 or Fr_down < 1:
        print(" 不是纯急流情况")
        return

    print(" 两端都是急流")

    h_init = np.linspace(h_up, h_down, n_cells)
    Q_init = np.ones(n_cells) * Q_up

    bc_left = {'type': 'supercritical', 'h': h_up, 'Q': Q_up}
    bc_right = {'type': 'supercritical', 'h': h_down, 'Q': Q_up}

    solver.initialize(h_init, Q_init, bc_left, bc_right)

    initial_mass = solver.initial_mass
    print(f"\n初始质量: {initial_mass:.2f} m^3")

    # 推进20步
    for step in range(20):
        solver.step()

    final_mass = solver._compute_total_mass()
    mass_error_pct = abs((final_mass - initial_mass) / initial_mass * 100)

    print(f"\n推进20步后:")
    print(f"  最终质量: {final_mass:.2f} m^3")
    print(f"  质量误差: {mass_error_pct:.6f}%")

    # 检查流量沿程分布
    print(f"\n流量沿程分布:")
    for i in range(0, n_cells, 5):
        Q = solver.Q[i]
        print(f"  单元{i}: Q = {Q:.4f} m^3/s")

    if mass_error_pct < 1.0:
        print("\n 质量守恒良好")
    else:
        print(f"\n 质量守恒较差: {mass_error_pct:.2f}%")


if __name__ == "__main__":
    test_simple_supercritical()
