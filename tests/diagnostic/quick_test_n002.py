#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""快速测试 n=0.02 工况"""

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


# 参数
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

print("快速测试: n=0.02 工况")
print("="*70)

solver = GodunvFVMWENO3(
    width=B, length=L, n_cells=n_cells,
    manning_n=0.02, slope=0.0, g=g,
    cfl=0.4, eps_dry=1e-6, weno_epsilon=1e-6,
    riemann_solver='hll', use_numba=True, dt_max=0.5
)

solver.initialize(h_init.copy(), Q_init.copy(), bc_left, bc_right)

target_time = 50.0
step = 0
max_steps = 5000

while solver.t < target_time and step < max_steps:
    dt = solver.compute_dt()

    if dt < 1e-6:
        print(f" 失败：t={solver.t:.2f}s时dt变为{dt:.2e}")
        break

    if np.any(np.isnan(solver.h)) or np.any(np.isinf(solver.h)):
        print(f" 失败：t={solver.t:.2f}s出现NaN/Inf")
        print(f"   h范围: [{np.min(solver.h):.3f}, {np.max(solver.h):.3f}]")
        break

    solver.step(dt)
    step += 1

    if step % 50 == 0:
        print(f"步{step}: t={solver.t:.2f}s, dt={dt:.6f}, h=[{np.min(solver.h):.3f}, {np.max(solver.h):.3f}]")

print(f"\n最终:")
print(f"  t={solver.t:.2f}s, 步数={step}")

if solver.t >= target_time * 0.9:
    mass_error = abs(solver._compute_total_mass() - solver.initial_mass) / solver.initial_mass * 100
    h_up_final = solver.h[0]
    u_up_final = solver.Q[0] / (h_up_final * B)
    Fr_up = u_up_final / np.sqrt(g * h_up_final)
    n_negative = np.sum(solver.Q < 0)

    print(f"  质量误差={mass_error:.2f}%")
    print(f"  Fr={Fr_up:.3f}")
    print(f"  负流量单元={n_negative}个")
    print(f"   成功")
else:
    print(f"   失败")
