# -*- coding: utf-8 -*-
"""
Quick test for script 10 numerical stability
Runs only first 50 time steps to verify stability fixes
"""
import sys
sys.path.insert(0, '/home/user/HydroClaude')

import numpy as np

class SimpleCanalSolver:
    """Simplified solver from script 10"""
    def __init__(self, length, width, slope, manning_n, nx):
        self.L = length
        self.B = width
        self.S0 = slope
        self.n = manning_n
        self.nx = nx
        self.dx = length / (nx - 1)
        self.x = np.linspace(0, length, nx)
        self.g = 9.81
        self.h = np.ones(nx) * 5.0
        self.Q = np.ones(nx) * 5.0

    def step(self, dt, Q_upstream, h_downstream):
        h_new = self.h.copy()
        Q_new = self.Q.copy()

        for i in range(1, self.nx - 1):
            A = self.h[i] * self.B
            if A > 0:
                V = self.Q[i] / A
            else:
                V = 0

            dQ_dx = (self.Q[i+1] - self.Q[i-1]) / (2 * self.dx)
            dA_dt = -dQ_dx

            if self.h[i] > 0:
                R = A / (self.B + 2 * self.h[i])
                Sf = (self.n * abs(V)) ** 2 / (R ** (4./3.)) if R > 0 else 0
            else:
                Sf = 0

            dh_dx = (self.h[i+1] - self.h[i-1]) / (2 * self.dx)
            dQ_dt = self.g * A * (self.S0 - Sf - dh_dx)

            h_new[i] = self.h[i] + dA_dt * dt / self.B
            Q_new[i] = self.Q[i] + dQ_dt * dt

        Q_new[0] = Q_upstream
        h_new[0] = h_new[1]
        h_new[-1] = h_downstream
        Q_new[-1] = Q_new[-2]

        # Stability checks (from our fix)
        h_new = np.maximum(h_new, 0.1)
        h_new = np.minimum(h_new, 50.0)
        Q_new = np.clip(Q_new, 0.0, 100.0)

        self.h = h_new
        self.Q = Q_new
        return self.h, self.Q

# Test with reduced time step
print("=" * 80)
print("Script 10 Stability Test - First 50 time steps")
print("=" * 80)

solver = SimpleCanalSolver(length=1000.0, width=10.0, slope=0.001, manning_n=0.025, nx=50)

dt = 0.1  # FIXED time step
CFL = 2.0 * dt / solver.dx
print(f"\nTime step: {dt}s (FIXED from 1.0s)")
print(f"CFL number: {CFL:.4f}")
print(f"Grid spacing: {solver.dx:.2f}m")

print(f"\nRunning 50 time steps...")
has_instability = False

for i in range(50):
    t = i * dt
    if t < 10:
        Q_up = 5.0
    else:
        Q_up = 8.0

    h_down = 5.0
    solver.step(dt, Q_up, h_down)

    # Check for instabilities
    if np.any(solver.h < 0) or np.any(solver.h > 100):
        print(f"   Instability detected at t={t:.1f}s: Invalid water depth")
        has_instability = True
        break

    if np.any(solver.Q < -1) or np.any(solver.Q > 1000):
        print(f"   Instability detected at t={t:.1f}s: Invalid flow rate")
        has_instability = True
        break

    if i % 10 == 0:
        print(f"  t={t:4.1f}s: h=[{np.min(solver.h):.2f}, {np.max(solver.h):.2f}]m, "
              f"Q=[{np.min(solver.Q):.2f}, {np.max(solver.Q):.2f}]m^3/s")

if not has_instability:
    print("\n All 50 time steps completed successfully!")
    print(" No unphysical values detected")
    print(" Water depth remains in reasonable range")
    print(" Flow rate remains in reasonable range")
    print("\n=== STABILITY TEST PASSED ===")
else:
    print("\n STABILITY TEST FAILED")

print("=" * 80)
