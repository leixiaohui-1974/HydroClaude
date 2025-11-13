#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Debug visualization for dam break test
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
h_R = 0.0
x_dam = L / 2.0  # Center of domain
t_end = 10.0
B = 10.0

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
h_init = np.where(x <= x_dam, h_L, h_R)
Q_init = np.zeros_like(h_init)

bc_left = {'type': 'transmissive'}
bc_right = {'type': 'transmissive'}

solver.initialize(h_init, Q_init, bc_left, bc_right)

# Run simulation
print(f"Running simulation to t={t_end}s...")
step_count = 0
while solver.t < t_end:
    solver.step()
    step_count += 1
    if step_count % 5 == 0:
        print(f"  Step {step_count}: t={solver.t:.3f}s, dt={solver.dt:.4f}s")

print(f" Simulation completed: {step_count} steps, t={solver.t:.3f}s")

# Get numerical solution
h_num = solver.h
Q_num = solver.Q
u_num = Q_num / np.maximum(h_num, solver.eps_dry)

# Get analytical solution
h_exact, u_exact = ritter_solution(x, solver.t, h_L, x_dam)

# Plot comparison
fig, axes = plt.subplots(2, 1, figsize=(14, 10))

# Water depth
axes[0].plot(x, h_exact, 'k-', linewidth=2, label='Ritter (Analytical)', zorder=1)
axes[0].plot(x, h_num, 'ro-', linewidth=1.5, markersize=3, label='HydroClaude (Numerical)', alpha=0.7, zorder=2)
axes[0].axvline(x_dam, color='gray', linestyle=':', linewidth=1, label='Dam location', zorder=0)
axes[0].set_ylabel('Water Depth h (m)', fontsize=13)
axes[0].set_title(f'SWASHES DB1 Dam Break Test - t={solver.t:.2f}s, Grid={n_cells} cells', fontsize=14, weight='bold')
axes[0].legend(loc='upper right', fontsize=11)
axes[0].grid(True, alpha=0.3)
axes[0].set_xlim([0, L])
axes[0].set_ylim([-0.5, h_L+1])

# Velocity
axes[1].plot(x, u_exact, 'k-', linewidth=2, label='Ritter (Analytical)', zorder=1)
axes[1].plot(x, u_num, 'bo-', linewidth=1.5, markersize=3, label='HydroClaude (Numerical)', alpha=0.7, zorder=2)
axes[1].axvline(x_dam, color='gray', linestyle=':', linewidth=1, zorder=0)
axes[1].set_xlabel('Distance x (m)', fontsize=13)
axes[1].set_ylabel('Velocity u (m/s)', fontsize=13)
axes[1].legend(loc='upper right', fontsize=11)
axes[1].grid(True, alpha=0.3)
axes[1].set_xlim([0, L])

plt.tight_layout()
plt.savefig('debug_dam_break_comparison.png', dpi=150, bbox_inches='tight')
print(f"\n Plot saved: debug_dam_break_comparison.png")

# Compute and print errors
mask = (h_exact > 1e-6) | (h_num > 1e-6)
h_err = np.abs(h_num - h_exact)[mask]
u_err = np.abs(u_num - u_exact)[mask]

print(f"\nError Analysis:")
print(f"  Water depth:")
print(f"    L1:   {np.mean(h_err):.4f} m")
print(f"    L2:   {np.sqrt(np.mean(h_err**2)):.4f} m")
print(f"    L∞:   {np.max(h_err):.4f} m")
print(f"  Velocity:")
print(f"    L1:   {np.mean(u_err):.4f} m/s")
print(f"    L2:   {np.sqrt(np.mean(u_err**2)):.4f} m/s")
print(f"    L∞:   {np.max(u_err):.4f} m/s")

# Check characteristics
from tests.verification.ritter_solution import ritter_characteristics
chars = ritter_characteristics(solver.t, h_L, x_dam)
print(f"\nRitter Wave Characteristics (t={solver.t:.3f}s):")
print(f"  Rarefaction tail:  x = {chars['x_tail']:.1f} m")
print(f"  Shock front:       x = {chars['x_front']:.1f} m")
print(f"  Wave speed:        c = {chars['wave_speed']:.2f} m/s")
print(f"  Front velocity:    u = {chars['u_front']:.2f} m/s")
print(f"  Front depth:       h = {chars['h_front']:.2f} m")
