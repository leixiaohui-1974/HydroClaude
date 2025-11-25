#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Froude数分析

检查急缓流转换区域
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



def analyze_froude():
    """分析Froude数分布"""

    B = 10.0
    L = 200.0
    n_cells = 10
    g = 9.81

    solver = GodunvFVMSolver(
        width=B,
        length=L,
        n_cells=n_cells,
        manning_n=0.0,
        slope=0.0,
        cfl=0.4,
        order=1
    )

    h_up = 0.3
    Q_up = 10.0
    h_down = 2.0

    h_init = np.linspace(h_up, h_down, n_cells)
    Q_init = np.ones(n_cells) * Q_up

    bc_left = {'type': 'supercritical', 'h': h_up, 'Q': Q_up}
    bc_right = {'type': 'h', 'value': h_down}

    solver.initialize(h_init, Q_init, bc_left, bc_right)

    print("\n" + "="*80)
    print("Froude数分析")
    print("="*80)

    # 推进几步
    for step in range(5):
        solver.step()

    # 计算每个单元的Froude数
    print(f"\n第{step+1}步后的状态:")
    print(f"\n{'单元':>4} {'x(m)':>8} {'h(m)':>8} {'Q(m^3/s)':>10} {'u(m/s)':>8} {'Fr':>8} {'状态':>10}")
    print("-" * 80)

    for i in range(n_cells):
        x = solver.x[i]
        h = solver.h[i]
        Q = solver.Q[i]
        u = Q / (B * h) if h > 1e-10 else 0.0
        Fr = u / np.sqrt(g * h) if h > 1e-10 else 0.0

        if Fr < 0.9:
            status = "缓流"
        elif Fr < 1.1:
            status = "临界"
        else:
            status = "急流"

        print(f"{i:4d} {x:8.1f} {h:8.4f} {Q:10.4f} {u:8.4f} {Fr:8.4f} {status:>10}")

    print("="*80)


if __name__ == "__main__":
    analyze_froude()
