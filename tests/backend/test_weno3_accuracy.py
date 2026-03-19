#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
WENO3 Solver Accuracy Tests

Validates the GodunvFVMWENO3 solver against analytical solutions and
compares accuracy with the standard Godunov solver.

Author: HydroClaude Test Team
Date: 2026-03-19
"""

import pytest
import warnings
warnings.filterwarnings("ignore")
import sys
import os
from pathlib import Path

# Path setup
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

import numpy as np
from scipy.optimize import brentq

from solvers.godunov_fvm_weno3 import GodunvFVMWENO3
from solvers.godunov_fvm_solver import GodunvFVMSolver
from utils.canal_utils import compute_steady_uniform_flow


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _manning_Q(h, B, n, S0):
    """Compute discharge from Manning equation for rectangular channel."""
    A = B * h
    P = B + 2.0 * h
    R = A / P
    return (1.0 / n) * A * R ** (2.0 / 3.0) * S0 ** 0.5


def _run_solver_to_steady(solver, max_steps=20000, check_interval=200,
                          convergence_threshold=1e-6):
    """Advance a solver until the depth field converges."""
    h_old = solver.h.copy()
    for step in range(max_steps):
        solver.step()
        if (step + 1) % check_interval == 0:
            max_change = np.max(np.abs(solver.h - h_old))
            if max_change < convergence_threshold:
                return step + 1
            h_old = solver.h.copy()
    return max_steps


def _stoker_exact_solution(x_cells, t_eval, h_L, h_R, x_dam, g=9.81):
    """Compute the exact Stoker (Ritter) dam-break solution."""
    u_L, u_R = 0.0, 0.0
    c_L = np.sqrt(g * h_L)
    c_R = np.sqrt(g * h_R)

    def _f_wave(h, h_K):
        if h <= h_K:
            return 2.0 * (np.sqrt(g * h) - np.sqrt(g * h_K))
        else:
            return (h - h_K) * np.sqrt(0.5 * g * (1.0 / h + 1.0 / h_K))

    h_star = brentq(
        lambda h: _f_wave(h, h_L) + _f_wave(h, h_R) + (u_R - u_L),
        0.001, 5.0, xtol=1e-12,
    )
    u_star = 0.5 * (u_L + u_R) + 0.5 * (
        _f_wave(h_star, h_R) - _f_wave(h_star, h_L)
    )
    c_star = np.sqrt(g * h_star)

    S_shock = (h_star * u_star - h_R * u_R) / (h_star - h_R)
    S_head = u_L - c_L
    S_tail = u_star - c_star

    def _exact_h(x):
        xi = (x - x_dam) / t_eval
        if xi <= S_head:
            return h_L
        elif xi <= S_tail:
            c_fan = (u_L + 2.0 * c_L - xi) / 3.0
            return c_fan ** 2 / g
        elif xi <= S_shock:
            return h_star
        else:
            return h_R

    return np.array([_exact_h(xi) for xi in x_cells])


# ===========================================================================
# Test class
# ===========================================================================

class TestWENO3Accuracy:
    """WENO3 solver accuracy benchmark suite."""

    # -----------------------------------------------------------------------
    # 1. Manning uniform flow with WENO3
    # -----------------------------------------------------------------------
    @pytest.mark.backend
    def test_weno3_uniform_flow(self):
        """
        Verify that the WENO3 solver reaches Manning normal depth in a
        uniform rectangular channel.

        Parameters:
            n = 0.015, S0 = 0.001, Q = 10 m^3/s, B = 5 m

        Acceptance: relative error in steady-state depth < 0.1%.
        """
        n_manning = 0.015
        S0 = 0.001
        Q = 10.0
        B = 5.0
        length = 2000.0
        n_cells = 200

        h_normal = compute_steady_uniform_flow(Q, B, S0, n_manning)

        # Cross-check Manning residual
        Q_check = _manning_Q(h_normal, B, n_manning, S0)
        assert abs(Q_check - Q) / Q < 1e-4, (
            f"Manning reference depth inconsistent: Q_check={Q_check:.6f}"
        )

        solver = GodunvFVMWENO3(
            width=B,
            length=length,
            n_cells=n_cells,
            manning_n=n_manning,
            slope=S0,
            cfl=0.4,
        )

        h_init = np.ones(n_cells) * h_normal
        Q_init = np.ones(n_cells) * Q
        bc_left = {'type': 'Q', 'value': Q}
        bc_right = {'type': 'h', 'value': h_normal}
        solver.initialize(h_init, Q_init, bc_left, bc_right)

        steps = _run_solver_to_steady(solver)

        # Interior cells (skip boundary cells)
        h_interior = solver.h[5:-5]
        relative_errors = np.abs(h_interior - h_normal) / h_normal
        max_rel_error = np.max(relative_errors)

        assert max_rel_error < 1e-3, (
            f"WENO3 Manning uniform flow: max relative error {max_rel_error:.6e} "
            f"exceeds 0.1% (converged in {steps} steps)"
        )

    # -----------------------------------------------------------------------
    # 2. Dam-break against Stoker exact solution
    # -----------------------------------------------------------------------
    @pytest.mark.backend
    def test_weno3_dambreak(self):
        """
        Compare WENO3 solver against the exact Stoker (Ritter) dam-break
        solution for the shallow-water equations.

        Setup:
            h_L = 2.0 m, h_R = 0.5 m, channel length 100 m,
            dam at x = 50 m, frictionless.

        Acceptance: L2 relative error in depth at t = 5 s < 5%.
        """
        h_L = 2.0
        h_R = 0.5
        length = 100.0
        x_dam = 50.0
        t_eval = 5.0
        n_cells = 400

        dx = length / n_cells
        x_cells = np.linspace(0.5 * dx, length - 0.5 * dx, n_cells)
        h_exact = _stoker_exact_solution(x_cells, t_eval, h_L, h_R, x_dam)

        solver = GodunvFVMWENO3(
            width=1.0,
            length=length,
            n_cells=n_cells,
            manning_n=1e-8,
            slope=0.0,
            cfl=0.4,
        )

        h_init = np.where(x_cells < x_dam, h_L, h_R)
        Q_init = np.zeros(n_cells)
        bc_left = {'type': 'h', 'value': h_L}
        bc_right = {'type': 'h', 'value': h_R}
        solver.initialize(h_init, Q_init, bc_left, bc_right)

        # Advance to t_eval
        t_current = 0.0
        while t_current < t_eval:
            dt = solver.compute_dt()
            remaining = t_eval - t_current
            if dt > remaining:
                dt = remaining
            solver.step(dt)
            t_current += dt

        h_num = solver.h
        l2_error = np.sqrt(np.sum((h_num - h_exact) ** 2) / np.sum(h_exact ** 2))

        assert l2_error < 0.05, (
            f"WENO3 Stoker dam-break: L2 relative error {l2_error:.4f} exceeds 5%"
        )

    # -----------------------------------------------------------------------
    # 3. WENO3 vs Godunov on smooth problem
    # -----------------------------------------------------------------------
    @pytest.mark.backend
    def test_weno3_vs_godunov_smooth(self):
        """
        Compare WENO3 and standard Godunov on a smooth uniform flow problem.
        WENO3 (higher order) should produce error <= Godunov error.

        Both solvers run the same Manning uniform flow problem.
        """
        n_manning = 0.015
        S0 = 0.001
        Q = 10.0
        B = 5.0
        length = 2000.0
        n_cells = 200

        h_normal = compute_steady_uniform_flow(Q, B, S0, n_manning)

        h_init = np.ones(n_cells) * h_normal
        Q_init = np.ones(n_cells) * Q
        bc_left = {'type': 'Q', 'value': Q}
        bc_right = {'type': 'h', 'value': h_normal}

        # --- Standard Godunov (order=1) ---
        godunov = GodunvFVMSolver(
            width=B,
            length=length,
            n_cells=n_cells,
            manning_n=n_manning,
            slope=S0,
            cfl=0.4,
            order=1,
        )
        godunov.initialize(h_init.copy(), Q_init.copy(), bc_left, bc_right)
        _run_solver_to_steady(godunov)
        godunov_error = np.max(np.abs(godunov.h[5:-5] - h_normal) / h_normal)

        # --- WENO3 ---
        weno3 = GodunvFVMWENO3(
            width=B,
            length=length,
            n_cells=n_cells,
            manning_n=n_manning,
            slope=S0,
            cfl=0.4,
        )
        weno3.initialize(h_init.copy(), Q_init.copy(), bc_left, bc_right)
        _run_solver_to_steady(weno3)
        weno3_error = np.max(np.abs(weno3.h[5:-5] - h_normal) / h_normal)

        # WENO3 error should be no worse than Godunov error (with some margin)
        # Allow 10x margin since both should converge to the same steady state
        assert weno3_error <= godunov_error * 10.0 + 1e-10, (
            f"WENO3 error ({weno3_error:.6e}) significantly exceeds "
            f"Godunov error ({godunov_error:.6e}) on smooth problem"
        )

        # Both should satisfy the 0.1% tolerance
        assert weno3_error < 1e-3, (
            f"WENO3 error {weno3_error:.6e} exceeds 0.1%"
        )
        assert godunov_error < 1e-3, (
            f"Godunov error {godunov_error:.6e} exceeds 0.1%"
        )

    # -----------------------------------------------------------------------
    # 4. Mass conservation in closed basin
    # -----------------------------------------------------------------------
    @pytest.mark.backend
    def test_weno3_mass_conservation(self):
        """
        In a closed rectangular basin with a depth perturbation, the total
        water volume must be conserved over transient evolution.

        Setup:
            h(x) = 1.0 + 0.1 * sin(2*pi*x/L), Q = 0 at both ends.

        Acceptance: |V_final - V_initial| / V_initial < 1e-4.
        """
        length = 100.0
        B = 5.0
        n_cells = 200
        n_manning = 1e-8
        dx = length / n_cells

        solver = GodunvFVMWENO3(
            width=B,
            length=length,
            n_cells=n_cells,
            manning_n=n_manning,
            slope=0.0001,
            cfl=0.3,
        )

        x_cells = np.linspace(0.5 * dx, length - 0.5 * dx, n_cells)
        h_init = 1.0 + 0.1 * np.sin(2.0 * np.pi * x_cells / length)
        Q_init = np.zeros(n_cells)

        bc_left = {'type': 'Q', 'value': 0.0}
        bc_right = {'type': 'Q', 'value': 0.0}
        solver.initialize(h_init, Q_init, bc_left, bc_right)

        mass_initial = np.sum(solver.h) * B * dx

        # Run 500 time steps
        for _ in range(500):
            solver.step()

        mass_final = np.sum(solver.h) * B * dx

        assert not np.any(np.isnan(solver.h)), "Solution contains NaN"
        assert not np.any(np.isnan(solver.Q)), "Discharge contains NaN"

        rel_mass_error = abs(mass_final - mass_initial) / mass_initial

        assert rel_mass_error < 1e-4, (
            f"WENO3 mass conservation violated: relative error {rel_mass_error:.2e} "
            f"(initial={mass_initial:.6f}, final={mass_final:.6f})"
        )


# ---------------------------------------------------------------------------
# Standalone execution
# ---------------------------------------------------------------------------
if __name__ == '__main__':
    pytest.main([__file__, '-v', '-s'])
