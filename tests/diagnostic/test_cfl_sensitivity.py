#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
CFL敏感性测试 - 找出无摩阻Test 4的稳定CFL数

日期: 2025-10-29
"""

import sys
import warnings
warnings.filterwarnings("ignore")
import os
sys.path.insert(0, os.path.dirname(__file__))

import numpy as np
try:
    from solvers.godunov_fvm_weno3 import GodunvFVMWENO3
except ImportError as e:
    print(f"Import error: {e}")
    print("Make sure project root is in sys.path")
    sys.exit(1)


# Test 4参数（无摩阻）
L = 1000.0
B = 10.0
h_upstream = 0.7
Q_val = 20.0
h_downstream = 2.8
n_cells = 200
g = 9.81

h_init = np.linspace(h_upstream, h_downstream, n_cells)
Q_init = np.ones(n_cells) * Q_val

bc_left = {'type': 'supercritical', 'h': h_upstream, 'Q': Q_val}
bc_right = {'type': 'h', 'value': h_downstream}

print("="*70)
print("CFL敏感性测试（无摩阻Test 4）")
print("="*70)

# 测试不同CFL数
cfl_values = [0.4, 0.3, 0.2, 0.1, 0.05]
target_time = 50.0

for cfl in cfl_values:
    print(f"\n测试 CFL = {cfl}")

    solver = GodunvFVMWENO3(
        width=B, length=L, n_cells=n_cells,
        manning_n=0.0, slope=0.0, g=g,
        cfl=cfl, eps_dry=1e-6, weno_epsilon=1e-6,
        riemann_solver='hll', use_numba=True, dt_max=0.5
    )

    solver.initialize(h_init.copy(), Q_init.copy(), bc_left, bc_right)

    step = 0
    max_steps = 5000
    failed = False

    while solver.t < target_time and step < max_steps:
        dt = solver.compute_dt()

        # 检查dt异常
        if dt < 1e-6:
            print(f"   失败：t={solver.t:.2f}s时dt变为{dt:.2e}")
            failed = True
            break

        # 检查非物理值
        if np.any(solver.h < 0) or np.any(np.isnan(solver.h)):
            print(f"   失败：t={solver.t:.2f}s出现非物理h值")
            failed = True
            break

        solver.step(dt)
        step += 1

    if not failed:
        # 检查质量守恒
        mass_error = abs(solver._compute_total_mass() - solver.initial_mass) / solver.initial_mass * 100

        # 检查上游Fr
        h_up_final = solver.h[0]
        u_up_final = solver.Q[0] / (h_up_final * B)
        Fr_up = u_up_final / np.sqrt(g * h_up_final)

        print(f"   成功：t={solver.t:.2f}s, 步数={step}")
        print(f"     质量误差={mass_error:.2f}%, 上游Fr={Fr_up:.3f}")
        print(f"     h范围=[{np.min(solver.h):.3f}, {np.max(solver.h):.3f}]")
        print(f"     Q范围=[{np.min(solver.Q):.3f}, {np.max(solver.Q):.3f}]")

        # 检查是否有负流量
        if np.any(solver.Q < 0):
            print(f"     ️  有{np.sum(solver.Q < 0)}个单元出现负流量")
    else:
        print(f"  最终：t={solver.t:.2f}s, 步数={step}")

print("\n" + "="*70)
