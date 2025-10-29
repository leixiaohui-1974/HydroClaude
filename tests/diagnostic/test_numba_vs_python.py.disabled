#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Numba vs Python路径对比测试

检查numba和python路径的质量守恒差异
"""

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '../..'))

import numpy as np
from solvers.godunov_fvm_solver import GodunvFVMSolver


def test_path(use_numba, order):
    """测试特定配置"""

    B = 5.0
    Q_bc = 2.0
    h_bc = 0.7

    solver = GodunvFVMSolver(
        width=B,
        length=1000.0,
        n_cells=20,
        manning_n=0.03,
        slope=0.002,
        cfl=0.4,
        order=order,
        use_numba=use_numba
    )

    h_init = np.linspace(1.0, h_bc, 20)
    Q_init = np.ones(20) * Q_bc

    bc_left = {'type': 'Q', 'value': Q_bc}
    bc_right = {'type': 'h', 'value': h_bc}

    solver.initialize(h_init, Q_init, bc_left, bc_right)

    mass_initial = solver.initial_mass
    cumulative_inflow = 0.0
    cumulative_outflow = 0.0

    # 运行100s
    t_end = 100.0
    while solver.t < t_end:
        dt = solver.compute_dt()
        solver.step()

        if solver.last_F_h is not None:
            cumulative_inflow += solver.last_F_h[0] * dt
            cumulative_outflow += solver.last_F_h[-1] * dt

    mass_final = np.sum(solver.h * solver.dx * solver.B)
    mass_theory = mass_initial + cumulative_inflow - cumulative_outflow
    error = abs(mass_final - mass_theory) / abs(mass_theory) * 100

    return error


def main():
    print("\n" + "="*80)
    print("Numba vs Python路径质量守恒对比")
    print("="*80)

    configs = [
        (False, 1, "Python + order=1"),
        (True, 1, "Numba + order=1"),
        (False, 2, "Python + order=2"),
        (True, 2, "Numba + order=2"),
    ]

    print(f"\n{'配置':<25} {'质量误差':<15} {'状态'}")
    print("-" * 50)

    for use_numba, order, name in configs:
        error = test_path(use_numba, order)
        status = "✓" if error < 1.0 else "✗"
        print(f"{name:<25} {error:>6.2f}%        {status}")

    print("\n" + "="*80)


if __name__ == "__main__":
    main()
