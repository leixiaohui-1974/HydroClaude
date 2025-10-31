#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Debug script for dam break timestep issue
"""

import sys
import os
sys.path.insert(0, os.path.dirname(__file__))

import numpy as np
from solvers.godunov_fvm_weno3 import GodunvFVMWENO3

# Parameters
L = 2000.0
n_cells = 200
h_L = 10.0
h_R = 0.0
x_dam = 0.0
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

print(f"\nInitial condition:")
print(f"  x range: [{x.min():.1f}, {x.max():.1f}] m")
print(f"  h range: [{h_init.min():.1f}, {h_init.max():.1f}] m")
print(f"  h mean: {h_init.mean():.3f} m")
print(f"  Number of wet cells: {np.sum(h_init > 0.1)}")
print(f"  Number of dry cells: {np.sum(h_init < 0.1)}")

# Boundary conditions
bc_left = {'type': 'transmissive'}
bc_right = {'type': 'transmissive'}

solver.initialize(h_init, Q_init, bc_left, bc_right)

print(f"\nAfter initialization:")
print(f"  solver.h range: [{solver.h.min():.6f}, {solver.h.max():.6f}] m")
print(f"  solver.Q range: [{solver.Q.min():.6f}, {solver.Q.max():.6f}] m³/s")
print(f"  solver.t: {solver.t} s")

# Compute first timestep
dt = solver.compute_dt()
print(f"\nFirst timestep calculation:")
print(f"  dt: {dt:.6f} s")
print(f"  dx: {solver.dx} m")
print(f"  cfl: {solver.cfl}")

# Check wave speeds
h_safe = np.maximum(solver.h, solver.eps_dry)
A = h_safe * solver.B
u = solver.Q / A
c = np.sqrt(solver.g * h_safe)
lambda_vals = np.abs(u) + c

print(f"\nWave speed analysis:")
print(f"  h_safe range: [{h_safe.min():.6e}, {h_safe.max():.6e}] m")
print(f"  u range: [{u.min():.6f}, {u.max():.6f}] m/s")
print(f"  c range: [{c.min():.6f}, {c.max():.6f}] m/s")
print(f"  lambda range: [{lambda_vals.min():.6f}, {lambda_vals.max():.6f}] m/s")
print(f"  lambda_max: {lambda_vals.max():.6f} m/s")

# Take one step
print(f"\nTaking one step...")
solver.step()

print(f"\nAfter one step:")
print(f"  solver.t: {solver.t:.6f} s")
print(f"  solver.dt: {solver.dt:.6f} s")
print(f"  solver.step_count: {solver.step_count}")
print(f"  h range: [{solver.h.min():.6f}, {solver.h.max():.6f}] m")
print(f"  Q range: [{solver.Q.min():.6f}, {solver.Q.max():.6f}] m³/s")
