#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
诊断细网格时间步长崩溃问题
"""

import sys
import os
sys.path.insert(0, os.path.dirname(__file__))

import numpy as np
from solvers.godunov_fvm_weno3 import GodunvFVMWENO3

# Parameters
L = 2000.0
n_cells = 1000
h_L = 10.0
x_dam = L / 2.0
t_target = 8.0  # 目标时间（问题发生在7.378s附近）
B = 10.0

print(f"诊断细网格问题 (n={n_cells})")
print("="*70)

# Create solver
solver = GodunvFVMWENO3(
    width=B,
    length=L,
    n_cells=n_cells,
    manning_n=0.0,
    slope=0.0,
    use_enhanced_bc=True,
    well_balanced=False,
    cfl=0.5,
    use_numba=True
)

# Initial condition
x = solver.x
h_init = np.where(x <= x_dam, h_L, 0.0)
Q_init = np.zeros_like(h_init)

bc = {'type': 'transmissive'}
solver.initialize(h_init, Q_init, bc, bc)

# Run until target time
step_count = 0
dt_history = []
t_history = []
min_h_history = []
max_u_history = []

print(f"\n运行模拟到 t={t_target}s...")
while solver.t < t_target and step_count < 100000:
    dt_before = solver.compute_dt()
    solver.step()
    step_count += 1

    # 记录历史
    dt_history.append(solver.dt)
    t_history.append(solver.t)
    min_h_history.append(np.min(solver.h))
    max_u_history.append(np.max(np.abs(solver.Q / np.maximum(solver.h, solver.eps_dry))))

    # 检查异常
    if solver.dt < 1e-6:
        print(f"\n️  步{step_count}: dt崩溃为{solver.dt:.2e}s!")
        print(f"  时间: {solver.t:.6f}s")
        print(f"  h range: [{np.min(solver.h):.6e}, {np.max(solver.h):.6f}]")
        print(f"  Q range: [{np.min(solver.Q):.6f}, {np.max(solver.Q):.6f}]")
        print(f"  NaN检测: h有NaN={np.any(np.isnan(solver.h))}, Q有NaN={np.any(np.isnan(solver.Q))}")

        # 检查极小水深单元
        small_h_mask = (solver.h > 0) & (solver.h < 1e-3)
        n_small = np.sum(small_h_mask)
        print(f"  极小水深单元 (0 < h < 1mm): {n_small} 个")
        if n_small > 0:
            print(f"  最小h位置: x={x[np.argmin(solver.h)]:.1f}m, h={np.min(solver.h):.6e}m")

        # 检查速度
        A = solver.h * B
        u = solver.Q / np.maximum(A, solver.eps_dry * B)
        c = np.sqrt(9.81 * np.maximum(solver.h, solver.eps_dry))
        lambda_max = np.max(np.abs(u) + c)
        print(f"  最大波速: {lambda_max:.6f} m/s")
        print(f"  CFL dt应该是: {solver.cfl * solver.dx / lambda_max:.6e}s")

        break

    if step_count % 100 == 0:
        print(f"  步{step_count}: t={solver.t:.3f}s, dt={solver.dt:.4f}s, min(h)={np.min(solver.h):.2e}m")

print(f"\n模拟统计:")
print(f"  总步数: {step_count}")
print(f"  最终时间: {solver.t:.6f}s")
print(f"  平均dt: {np.mean(dt_history):.6f}s")
print(f"  最小dt: {np.min(dt_history):.6e}s")
print(f"  最大dt: {np.max(dt_history):.6f}s")

# Plot dt evolution
import matplotlib.pyplot as plt

fig, axes = plt.subplots(2, 2, figsize=(14, 10))

axes[0, 0].plot(t_history, dt_history, 'b-', linewidth=1)
axes[0, 0].set_xlabel('Time (s)')
axes[0, 0].set_ylabel('dt (s)')
axes[0, 0].set_title('Time Step Evolution')
axes[0, 0].grid(True, alpha=0.3)
axes[0, 0].set_yscale('log')

axes[0, 1].plot(t_history, min_h_history, 'r-', linewidth=1)
axes[0, 1].set_xlabel('Time (s)')
axes[0, 1].set_ylabel('min(h) (m)')
axes[0, 1].set_title('Minimum Water Depth')
axes[0, 1].grid(True, alpha=0.3)
axes[0, 1].set_yscale('log')

axes[1, 0].plot(range(len(dt_history)), dt_history, 'g-', linewidth=1)
axes[1, 0].set_xlabel('Step Number')
axes[1, 0].set_ylabel('dt (s)')
axes[1, 0].set_title('Time Step vs Step Number')
axes[1, 0].grid(True, alpha=0.3)
axes[1, 0].set_yscale('log')

axes[1, 1].plot(t_history, max_u_history, 'm-', linewidth=1)
axes[1, 1].set_xlabel('Time (s)')
axes[1, 1].set_ylabel('max(|u|) (m/s)')
axes[1, 1].set_title('Maximum Velocity')
axes[1, 1].grid(True, alpha=0.3)

plt.tight_layout()
plt.savefig('debug_fine_grid_dt_evolution.png', dpi=150, bbox_inches='tight')
print(f"\n 诊断图保存: debug_fine_grid_dt_evolution.png")
