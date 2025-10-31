#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Test Numba vs Python implementation for dam break
"""

import sys
import os
sys.path.insert(0, os.path.dirname(__file__))

import numpy as np
import matplotlib.pyplot as plt
from solvers.godunov_fvm_weno3 import GodunvFVMWENO3
from tests.verification.ritter_solution import ritter_solution

# Parameters
L = 2000.0
n_cells = 200
h_L = 10.0
x_dam = L / 2.0
t_end = 10.0
B = 10.0

configs = [
    {'name': 'Python (no Numba)', 'use_numba': False, 'cfl': 0.5},
    {'name': 'Numba JIT', 'use_numba': True, 'cfl': 0.5},
]

fig, axes = plt.subplots(2, 2, figsize=(16, 10))

for idx, config in enumerate(configs):
    print(f"\n{'='*60}")
    print(f"Testing: {config['name']}")
    print(f"{'='*60}")

    # Create solver
    solver = GodunvFVMWENO3(
        width=B,
        length=L,
        n_cells=n_cells,
        manning_n=0.0,
        slope=0.0,
        use_enhanced_bc=True,
        well_balanced=False,
        cfl=config['cfl'],
        use_numba=config['use_numba']
    )

    # Initial condition
    x = solver.x
    h_init = np.where(x <= x_dam, h_L, 0.0)
    Q_init = np.zeros_like(h_init)

    bc_left = {'type': 'transmissive'}
    bc_right = {'type': 'transmissive'}

    solver.initialize(h_init, Q_init, bc_left, bc_right)

    # Run simulation
    step_count = 0
    has_nan = False
    while solver.t < t_end and not has_nan:
        solver.step()
        step_count += 1
        if np.any(np.isnan(solver.h)) or np.any(np.isnan(solver.Q)):
            has_nan = True
            print(f"  ❌ NaN detected at step {step_count}, t={solver.t:.3f}s!")
            break

    if not has_nan:
        print(f"  ✅ Steps: {step_count}, Final time: {solver.t:.3f}s")

    # Get solutions
    h_num = solver.h
    u_num = solver.Q / np.maximum(solver.h, solver.eps_dry)
    h_exact, u_exact = ritter_solution(x, solver.t, h_L, x_dam)

    # Compute errors
    if not has_nan:
        mask = (h_exact > 1e-6) | (h_num > 1e-6)
        h_err_L2 = np.sqrt(np.mean((h_num[mask] - h_exact[mask])**2))
        u_err_L2 = np.sqrt(np.mean((u_num[mask] - u_exact[mask])**2))

        print(f"  h L2 error: {h_err_L2:.4f} m ({h_err_L2/h_L*100:.1f}%)")
        print(f"  u L2 error: {u_err_L2:.4f} m/s")
    else:
        h_err_L2 = np.nan
        u_err_L2 = np.nan

    # Plot
    ax_h = axes[idx, 0]
    ax_u = axes[idx, 1]

    # Water depth
    ax_h.plot(x, h_exact, 'k-', linewidth=2, label='Analytical', zorder=1)
    ax_h.plot(x, h_num, 'r.-', linewidth=1, markersize=3, label='Numerical', alpha=0.7, zorder=2)
    ax_h.axvline(x_dam, color='gray', linestyle=':', linewidth=1)
    ax_h.set_ylabel('h (m)', fontsize=12)
    status_str = f'NaN at t={solver.t:.2f}s' if has_nan else f'L2={h_err_L2:.3f}m'
    ax_h.set_title(f'{config["name"]} - {status_str}', fontsize=12, weight='bold')
    ax_h.legend(fontsize=10)
    ax_h.grid(True, alpha=0.3)
    ax_h.set_xlim([0, L])

    # Velocity
    ax_u.plot(x, u_exact, 'k-', linewidth=2, label='Analytical', zorder=1)
    ax_u.plot(x, u_num, 'b.-', linewidth=1, markersize=3, label='Numerical', alpha=0.7, zorder=2)
    ax_u.axvline(x_dam, color='gray', linestyle=':', linewidth=1)
    ax_u.set_ylabel('u (m/s)', fontsize=12)
    status_str = 'NaN' if has_nan else f'L2={u_err_L2:.3f}m/s'
    ax_u.set_title(f'{config["name"]} - {status_str}', fontsize=12, weight='bold')
    ax_u.legend(fontsize=10)
    ax_u.grid(True, alpha=0.3)
    ax_u.set_xlim([0, L])

    ax_h.set_xlabel('x (m)', fontsize=12)
    ax_u.set_xlabel('x (m)', fontsize=12)

plt.tight_layout()
plt.savefig('numba_vs_python_comparison.png', dpi=150, bbox_inches='tight')
print(f"\n✅ Comparison plot saved: numba_vs_python_comparison.png")
