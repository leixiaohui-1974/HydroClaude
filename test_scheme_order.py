#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Test different spatial schemes for dam break
"""

import sys
import os
sys.path.insert(0, os.path.dirname(__file__))

import numpy as np
import matplotlib.pyplot as plt
from solvers.godunov_fvm_solver import GodunvFVMSolver
from solvers.godunov_fvm_weno3 import GodunvFVMWENO3
from tests.verification.ritter_solution import ritter_solution

# Parameters
L = 2000.0
n_cells = 200
h_L = 10.0
x_dam = L / 2.0
t_end = 10.0
B = 10.0

print(f"\nTesting different spatial schemes for dam break")
print(f"Domain: [0, {L}]m, Dam at x={x_dam}m")
print(f"Grid: {n_cells} cells, h_L={h_L}m, t_end={t_end}s")
print("="*70)

results = []

# Test 1: First-order
print(f"\n1. First-order Godunov")
solver1 = GodunvFVMSolver(
    width=B, length=L, n_cells=n_cells,
    manning_n=0.0, slope=0.0,
    cfl=0.5, order=1
)
x = solver1.x
h_init = np.where(x <= x_dam, h_L, 0.0)
Q_init = np.zeros_like(h_init)
bc = {'type': 'transmissive'}
solver1.initialize(h_init, Q_init, bc, bc)

step1 = 0
while solver1.t < t_end:
    solver1.step()
    step1 += 1

h1 = solver1.h
u1 = solver1.Q / np.maximum(solver1.h, solver1.eps_dry)
h_exact, u_exact = ritter_solution(x, solver1.t, h_L, x_dam)
mask = (h_exact > 1e-6) | (h1 > 1e-6)
err1_h = np.sqrt(np.mean((h1[mask] - h_exact[mask])**2))
err1_u = np.sqrt(np.mean((u1[mask] - u_exact[mask])**2))

print(f"  Steps: {step1}, t={solver1.t:.3f}s")
print(f"  h L2: {err1_h:.4f}m ({err1_h/h_L*100:.1f}%)")
print(f"  u L2: {err1_u:.4f}m/s")
results.append({'name': '1st Order', 'h': h1, 'u': u1, 'err_h': err1_h, 'err_u': err1_u})

# Test 2: MUSCL (2nd order)
print(f"\n2. MUSCL (2nd order)")
solver2 = GodunvFVMSolver(
    width=B, length=L, n_cells=n_cells,
    manning_n=0.0, slope=0.0,
    cfl=0.5, order=2
)
h_init = np.where(solver2.x <= x_dam, h_L, 0.0)
solver2.initialize(h_init, Q_init, bc, bc)

step2 = 0
while solver2.t < t_end:
    solver2.step()
    step2 += 1

h2 = solver2.h
u2 = solver2.Q / np.maximum(solver2.h, solver2.eps_dry)
mask = (h_exact > 1e-6) | (h2 > 1e-6)
err2_h = np.sqrt(np.mean((h2[mask] - h_exact[mask])**2))
err2_u = np.sqrt(np.mean((u2[mask] - u_exact[mask])**2))

print(f"  Steps: {step2}, t={solver2.t:.3f}s")
print(f"  h L2: {err2_h:.4f}m ({err2_h/h_L*100:.1f}%)")
print(f"  u L2: {err2_u:.4f}m/s")
results.append({'name': 'MUSCL (2nd)', 'h': h2, 'u': u2, 'err_h': err2_h, 'err_u': err2_u})

# Test 3: WENO3
print(f"\n3. WENO3 (3rd order)")
solver3 = GodunvFVMWENO3(
    width=B, length=L, n_cells=n_cells,
    manning_n=0.0, slope=0.0,
    use_enhanced_bc=True, well_balanced=False,
    cfl=0.5, use_numba=False
)
h_init = np.where(solver3.x <= x_dam, h_L, 0.0)
solver3.initialize(h_init, Q_init, bc, bc)

step3 = 0
while solver3.t < t_end:
    solver3.step()
    step3 += 1

h3 = solver3.h
u3 = solver3.Q / np.maximum(solver3.h, solver3.eps_dry)
mask = (h_exact > 1e-6) | (h3 > 1e-6)
err3_h = np.sqrt(np.mean((h3[mask] - h_exact[mask])**2))
err3_u = np.sqrt(np.mean((u3[mask] - u_exact[mask])**2))

print(f"  Steps: {step3}, t={solver3.t:.3f}s")
print(f"  h L2: {err3_h:.4f}m ({err3_h/h_L*100:.1f}%)")
print(f"  u L2: {err3_u:.4f}m/s")
results.append({'name': 'WENO3 (3rd)', 'h': h3, 'u': u3, 'err_h': err3_h, 'err_u': err3_u})

# Plot comparison
fig, axes = plt.subplots(3, 2, figsize=(16, 12))

for idx, res in enumerate(results):
    ax_h = axes[idx, 0]
    ax_u = axes[idx, 1]

    # Water depth
    ax_h.plot(x, h_exact, 'k-', linewidth=2, label='Analytical', zorder=1)
    ax_h.plot(x, res['h'], 'r.-', linewidth=1, markersize=2, label='Numerical', alpha=0.7, zorder=2)
    ax_h.axvline(x_dam, color='gray', linestyle=':', linewidth=1)
    ax_h.set_ylabel('h (m)', fontsize=12)
    ax_h.set_title(f'{res["name"]} - h L2={res["err_h"]:.3f}m ({res["err_h"]/h_L*100:.1f}%)', fontsize=12, weight='bold')
    ax_h.legend(fontsize=10)
    ax_h.grid(True, alpha=0.3)
    ax_h.set_xlim([0, L])
    ax_h.set_ylim([-0.5, h_L+1])

    # Velocity
    ax_u.plot(x, u_exact, 'k-', linewidth=2, label='Analytical', zorder=1)
    ax_u.plot(x, res['u'], 'b.-', linewidth=1, markersize=2, label='Numerical', alpha=0.7, zorder=2)
    ax_u.axvline(x_dam, color='gray', linestyle=':', linewidth=1)
    ax_u.set_ylabel('u (m/s)', fontsize=12)
    ax_u.set_title(f'{res["name"]} - u L2={res["err_u"]:.3f}m/s', fontsize=12, weight='bold')
    ax_u.legend(fontsize=10)
    ax_u.grid(True, alpha=0.3)
    ax_u.set_xlim([0, L])

    if idx == 2:
        ax_h.set_xlabel('x (m)', fontsize=12)
        ax_u.set_xlabel('x (m)', fontsize=12)

plt.tight_layout()
plt.savefig('scheme_order_comparison.png', dpi=150, bbox_inches='tight')
print(f"\n✅ Comparison plot saved: scheme_order_comparison.png")

# Summary
print(f"\n{'='*70}")
print(f"Summary:")
print(f"{'='*70}")
print(f"{'Scheme':<15} {'h L2 (m)':<12} {'h L2 (%)':<12} {'u L2 (m/s)':<12}")
print(f"{'-'*70}")
for res in results:
    print(f"{res['name']:<15} {res['err_h']:<12.4f} {res['err_h']/h_L*100:<12.1f} {res['err_u']:<12.4f}")
