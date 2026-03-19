#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
HLLC Riemann Solver Accuracy Tests

Validates the HLLC (HLL with Contact) Riemann solver against:
1. Stoker exact dam-break solution
2. HLL solver comparison (HLLC should be at least as accurate)
3. Mass conservation in a closed basin

Author: HydroClaude Test Team
Date: 2026-03-19
"""

import pytest
import warnings
warnings.filterwarnings("ignore")
import sys
import os
from pathlib import Path

project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

import numpy as np
from scipy.optimize import brentq

from solvers.godunov_fvm_hllc import GodunvFVMHLLC
from solvers.godunov_fvm_solver import GodunvFVMSolver


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _stoker_exact_solution(x_cells, x_dam, t_eval, h_L, h_R, g=9.81):
    """Compute exact Stoker (Ritter) dam-break solution at given time."""
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

    # Right wave is a shock (h_star > h_R)
    S_shock = (h_star * u_star - h_R * u_R) / (h_star - h_R)

    # Left wave is a rarefaction (h_star < h_L)
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

    h_exact = np.array([_exact_h(xi) for xi in x_cells])
    return h_exact


# ===========================================================================
# Test class
# ===========================================================================

class TestHLLCAccuracy:
    """HLLC Riemann solver accuracy test suite."""

    # -----------------------------------------------------------------------
    # 1. Dam-break against Stoker exact solution
    # -----------------------------------------------------------------------
    @pytest.mark.backend
    def test_hllc_dambreak(self):
        """
        Compare HLLC Godunov solver against exact Stoker dam-break solution.

        Setup:
            h_L = 2.0 m, h_R = 0.5 m, channel length 100 m,
            dam at x = 50 m, frictionless.

        Acceptance: L2 relative error in depth at t = 5 s < 5 %.
        """
        g = 9.81
        h_L = 2.0
        h_R = 0.5
        length = 100.0
        x_dam = 50.0
        t_eval = 5.0
        n_cells = 400

        # --- numerical solution with HLLC ---
        solver = GodunvFVMHLLC(
            width=1.0,
            length=length,
            n_cells=n_cells,
            manning_n=1e-8,
            slope=0.0,
            cfl=0.4,
            order=2,
        )

        dx = length / n_cells
        x_cells = np.linspace(0.5 * dx, length - 0.5 * dx, n_cells)
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

        # --- exact solution ---
        h_exact = _stoker_exact_solution(x_cells, x_dam, t_eval, h_L, h_R, g)

        # --- comparison ---
        h_num = solver.h
        l2_error = np.sqrt(np.sum((h_num - h_exact) ** 2) / np.sum(h_exact ** 2))

        assert not np.any(np.isnan(h_num)), "HLLC solution contains NaN"
        assert l2_error < 0.05, (
            f"HLLC dam-break: L2 relative error {l2_error:.4f} exceeds 5 %"
        )

    # -----------------------------------------------------------------------
    # 2. HLLC vs HLL comparison
    # -----------------------------------------------------------------------
    @pytest.mark.backend
    def test_hllc_vs_hll_comparison(self):
        """
        Run both HLL and HLLC on the same dam-break problem.
        HLLC error should be <= HLL error (or very close).
        Both should be stable (no NaN).
        """
        g = 9.81
        h_L = 2.0
        h_R = 0.5
        length = 100.0
        x_dam = 50.0
        t_eval = 5.0
        n_cells = 400

        dx = length / n_cells
        x_cells = np.linspace(0.5 * dx, length - 0.5 * dx, n_cells)
        h_exact = _stoker_exact_solution(x_cells, x_dam, t_eval, h_L, h_R, g)

        h_init = np.where(x_cells < x_dam, h_L, h_R)
        Q_init = np.zeros(n_cells)
        bc_left = {'type': 'h', 'value': h_L}
        bc_right = {'type': 'h', 'value': h_R}

        # --- HLL solver (GodunvFVMSolver with riemann_solver='hll') ---
        solver_hll = GodunvFVMSolver(
            width=1.0,
            length=length,
            n_cells=n_cells,
            manning_n=1e-8,
            slope=0.0,
            cfl=0.4,
            order=2,
            riemann_solver='hll',
            use_numba=False,
        )
        solver_hll.initialize(h_init.copy(), Q_init.copy(), bc_left.copy(), bc_right.copy())

        t_current = 0.0
        while t_current < t_eval:
            dt = solver_hll.compute_dt()
            remaining = t_eval - t_current
            if dt > remaining:
                dt = remaining
            solver_hll.step(dt)
            t_current += dt

        h_hll = solver_hll.h.copy()

        # --- HLLC solver ---
        solver_hllc = GodunvFVMHLLC(
            width=1.0,
            length=length,
            n_cells=n_cells,
            manning_n=1e-8,
            slope=0.0,
            cfl=0.4,
            order=2,
        )
        solver_hllc.initialize(h_init.copy(), Q_init.copy(), bc_left.copy(), bc_right.copy())

        t_current = 0.0
        while t_current < t_eval:
            dt = solver_hllc.compute_dt()
            remaining = t_eval - t_current
            if dt > remaining:
                dt = remaining
            solver_hllc.step(dt)
            t_current += dt

        h_hllc = solver_hllc.h.copy()

        # --- verify both are stable ---
        assert not np.any(np.isnan(h_hll)), "HLL solution contains NaN"
        assert not np.any(np.isnan(h_hllc)), "HLLC solution contains NaN"

        # --- compute errors ---
        l2_hll = np.sqrt(np.sum((h_hll - h_exact) ** 2) / np.sum(h_exact ** 2))
        l2_hllc = np.sqrt(np.sum((h_hllc - h_exact) ** 2) / np.sum(h_exact ** 2))

        # Both should be within 5%
        assert l2_hll < 0.05, f"HLL L2 error {l2_hll:.4f} exceeds 5 %"
        assert l2_hllc < 0.05, f"HLLC L2 error {l2_hllc:.4f} exceeds 5 %"

        # HLLC should be at least as good as HLL (allow 10% relative slack)
        assert l2_hllc <= l2_hll * 1.10, (
            f"HLLC error ({l2_hllc:.4f}) significantly worse than HLL ({l2_hll:.4f})"
        )

    # -----------------------------------------------------------------------
    # 3. Mass conservation in closed basin
    # -----------------------------------------------------------------------
    @pytest.mark.backend
    def test_hllc_mass_conservation(self):
        """
        In a closed rectangular basin (Q=0 at both ends), the total water
        volume must be conserved over a transient evolution.

        Setup:
            Perturbation on flat bottom: h(x) = 1.0 + 0.1*sin(2*pi*x/L)
            No inflow/outflow.

        Acceptance: |V_final - V_initial| / V_initial < 1e-4.
        """
        length = 100.0
        B = 5.0
        n_cells = 200
        dx = length / n_cells

        solver = GodunvFVMHLLC(
            width=B,
            length=length,
            n_cells=n_cells,
            manning_n=1e-8,
            slope=0.0,
            cfl=0.4,
            order=1,
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
            f"HLLC mass conservation violated: relative error {rel_mass_error:.2e} "
            f"(initial={mass_initial:.6f}, final={mass_final:.6f})"
        )


# ---------------------------------------------------------------------------
# Standalone execution
# ---------------------------------------------------------------------------
if __name__ == '__main__':
    pytest.main([__file__, '-v', '-s'])
