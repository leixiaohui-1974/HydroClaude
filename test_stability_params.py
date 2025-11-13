#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Test different stability parameters for dam break
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
    {'name': 'CFL=0.5 (current)', 'cfl': 0.5, 'entropy_fix': False, 'critical_flow': False},
    {'name': 'CFL=0.3', 'cfl': 0.3, 'entropy_fix': False, 'critical_flow': False},
    {'name': 'CFL=0.2', 'cfl': 0.2, 'entropy_fix': False, 'critical_flow': False},
    {'name': 'CFL=0.3 + Entropy', 'cfl': 0.3, 'entropy_fix': True, 'critical_flow': False},
    {'name': 'CFL=0.3 + Entropy + Critical', 'cfl': 0.3, 'entropy_fix': True, 'critical_flow': True},
]

fig, axes = plt.subplots(len(configs), 2, figsize=(16, 4*len(configs)))

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
        use_numba=True,
        entropy_fix=config['entropy_fix'],
        critical_flow_treatment=config['critical_flow']
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
    while solver.t < t_end:
        solver.step()
        step_count += 1

    print(f"  Steps: {step_count}, Final time: {solver.t:.3f}s")

    # Get solutions
    h_num = solver.h
    u_num = solver.Q / np.maximum(solver.h, solver.eps_dry)
    h_exact, u_exact = ritter_solution(x, solver.t, h_L, x_dam)

    # Compute errors
    mask = (h_exact > 1e-6) | (h_num > 1e-6)
    h_err_L2 = np.sqrt(np.mean((h_num[mask] - h_exact[mask])**2))
    u_err_L2 = np.sqrt(np.mean((u_num[mask] - u_exact[mask])**2))

    print(f"  h L2 error: {h_err_L2:.4f} m")
    print(f"  u L2 error: {u_err_L2:.4f} m/s")

    # Plot
    ax_h = axes[idx, 0] if len(configs) > 1 else axes[0]
    ax_u = axes[idx, 1] if len(configs) > 1 else axes[1]

    # Water depth
    ax_h.plot(x, h_exact, 'k-', linewidth=2, label='Analytical', zorder=1)
    ax_h.plot(x, h_num, 'r.-', linewidth=1, markersize=2, label='Numerical', alpha=0.7, zorder=2)
    ax_h.axvline(x_dam, color='gray', linestyle=':', linewidth=1)
    ax_h.set_ylabel('h (m)', fontsize=11)
    ax_h.set_title(f'{config["name"]} - h L2={h_err_L2:.3f}m', fontsize=12)
    ax_h.legend(fontsize=9)
    ax_h.grid(True, alpha=0.3)
    ax_h.set_xlim([0, L])

    # Velocity
    ax_u.plot(x, u_exact, 'k-', linewidth=2, label='Analytical', zorder=1)
    ax_u.plot(x, u_num, 'b.-', linewidth=1, markersize=2, label='Numerical', alpha=0.7, zorder=2)
    ax_u.axvline(x_dam, color='gray', linestyle=':', linewidth=1)
    ax_u.set_ylabel('u (m/s)', fontsize=11)
    ax_u.set_title(f'{config["name"]} - u L2={u_err_L2:.3f}m/s', fontsize=12)
    ax_u.legend(fontsize=9)
    ax_u.grid(True, alpha=0.3)
    ax_u.set_xlim([0, L])

    if idx == len(configs) - 1:
        ax_h.set_xlabel('x (m)', fontsize=11)
        ax_u.set_xlabel('x (m)', fontsize=11)

plt.tight_layout()
plt.savefig('stability_params_comparison.png', dpi=150, bbox_inches='tight')
print(f"\n Comparison plot saved: stability_params_comparison.png")
