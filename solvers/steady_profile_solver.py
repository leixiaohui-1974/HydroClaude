#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""Steady-state water surface profile solver (refactored 2026-03-21)."""

import numpy as np
from scipy.integrate import solve_bvp
from scipy.optimize import fsolve, brentq
from typing import List, Tuple, Optional, Dict
import sys
import os

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from solvers.gate import HydraulicStructure
from utils.canal_utils import compute_steady_uniform_flow

try:
    from physics.cross_section import CrossSection, SectionGeometry
except ImportError:
    CrossSection = None
    SectionGeometry = None


class SteadyProfileSolver:
    """Steady-state water surface profile solver with per-station XS support."""

    def __init__(
        self,
        length: float,
        B: float = 10.0,
        S0: float = 0.001,
        n: float = 0.025,
        g: float = 9.81,
        cross_section=None,
        cross_sections=None,
        bed_elevations=None,
        manning_ns=None,
        reach_lengths=None,
        contraction_coefs=None,
        expansion_coefs=None,
    ) -> None:
        """
        Args:
            length: Reach length (m)
            B: Rectangular channel width (m)
            S0: Bed slope
            n: Manning roughness
            g: Gravity (m/s^2)
            cross_section: Single CrossSection (backward-compat)
            cross_sections: List of CrossSection per station
            bed_elevations: Absolute bed elevation per station (m); enables absolute WSE iteration
            manning_ns: Manning n per station; falls back to self.n when None
            reach_lengths: Actual reach lengths between XS pairs (m); from HEC-RAS Len Channel
            contraction_coefs: Per-XS contraction loss coefficients
            expansion_coefs: Per-XS expansion loss coefficients
        """
        self.length = length
        self.B = B
        self.S0 = S0
        self.n = n
        self.g = g
        self._xs = cross_section
        self._xs_array = cross_sections
        self._bed_elevations = bed_elevations
        self._manning_ns = manning_ns
        self._reach_lengths = reach_lengths
        self._contraction_coefs = contraction_coefs
        self._expansion_coefs = expansion_coefs

    # Hydraulic geometry helpers

    def _get_geometry(self, h: float, station_index=None) -> Tuple[float, float, float, float]:
        """Return (A, P, R, T) at water depth h."""
        xs = self._xs
        if station_index is not None and self._xs_array and station_index < len(self._xs_array):
            xs = self._xs_array[station_index]
        if xs is not None:
            geom = xs.compute_geometry(max(float(h), 1e-6))
            return float(geom.area), float(geom.perimeter), float(geom.hydraulic_radius), float(geom.width)
        h_safe = max(float(h), 1e-6)
        A = self.B * h_safe
        P = self.B + 2 * h_safe
        return A, P, A / P, self.B

    def compute_friction_slope(self, h: float, Q: float, station_index=None) -> float:
        """Manning friction slope, per-station Manning n support."""
        n_local = self.n
        if station_index is not None and self._manning_ns and station_index < len(self._manning_ns):
            n_val = self._manning_ns[station_index]
            if n_val and float(n_val) > 0:
                n_local = float(n_val)
        xs = self._xs
        if station_index is not None and self._xs_array and station_index < len(self._xs_array):
            xs = self._xs_array[station_index]
        if xs is not None and hasattr(xs, "compute_conveyance"):
            K, _alpha = xs.compute_conveyance(h)
            if K > 0:
                return float((Q / K) ** 2)
        A, _P, R, _T = self._get_geometry(h, station_index)
        V = Q / max(A, 1e-9)
        return float((n_local * V) ** 2 / max(R, 1e-9) ** (4.0 / 3.0))

    def compute_froude(self, h: float, Q: float, station_index=None) -> float:
        """Froude number."""
        A, _P, _R, T = self._get_geometry(h, station_index)
        V = Q / max(A, 1e-9)
        xs = self._xs
        if station_index is not None and self._xs_array and station_index < len(self._xs_array):
            xs = self._xs_array[station_index]
        if xs is not None:
            D_h = A / max(T, 1e-9)
            return float(V / np.sqrt(self.g * max(D_h, 1e-9)))
        return float(V / np.sqrt(self.g * max(float(h), 1e-6)))

    def dh_dx(self, h: float, Q: float) -> float:
        """GVF ODE with LPI mixed-flow smoothing."""
        Sf = self.compute_friction_slope(h, Q)
        Fr = self.compute_froude(h, Q)
        if Fr <= 0.8:
            beta = 1.0
        elif Fr >= 1.2:
            beta = 0.0
        else:
            beta = (1.2 - Fr) / 0.4
        return float((self.S0 - Sf) / (1.0 - beta * Fr ** 2))

    # Standard Step Method
    
    def solve_standard_step(
        self,
        Q: float,
        h_downstream: float,
        nx: int = 201,
        alpha: float = 1.0,
        C_expansion: float = 0.1,
        contraction_coef: float = 0.1,
        expansion_coef: float = 0.3,
    ) -> Dict:
        """HEC-RAS Standard Step Method.
    
        When bed_elevations is set, delegates to _solve_standard_step_variable_xs
        for absolute WSE iteration (fully consistent with HEC-RAS).
        """
        if self._bed_elevations is not None:
            return self._solve_standard_step_variable_xs(
                Q, h_downstream, nx=nx, alpha=alpha,
                contraction_coef=contraction_coef,
                expansion_coef=expansion_coef,
            )
        if self._xs_array:
            nx = len(self._xs_array)
        x = np.linspace(0, self.length, nx)
        dx = self.length / (nx - 1)
        h = np.zeros(nx)
        h[-1] = h_downstream
        z = self.S0 * (self.length - x)
    
        def _vh(hv, idx=None):
            xs_local = self._xs
            if idx is not None and self._xs_array and idx < len(self._xs_array):
                xs_local = self._xs_array[idx]
            A, _P, _R, _T = self._get_geometry(hv, idx)
            V = Q / max(A, 1e-9)
            if xs_local is not None and hasattr(xs_local, "compute_conveyance"):
                _K, alpha_local = xs_local.compute_conveyance(hv)
            else:
                alpha_local = alpha
            return alpha_local * V ** 2 / (2.0 * self.g)
    
        _MAX_DEPTH = 1000.0
        divergence_count = 0
        for i in range(nx - 2, -1, -1):
            h_dn = h[i + 1]
            W_dn = z[i + 1] + h_dn
            vh_dn = _vh(h_dn, i + 1)
            Sf_dn = self.compute_friction_slope(h_dn, Q, i + 1)
            h_it = h_dn if i == nx - 2 else max(2.0 * h[i + 1] - h[i + 2], 1e-3)
            converged = False
            for _k in range(30):
                vh_up = _vh(h_it, i)
                Sf_up = self.compute_friction_slope(h_it, Q, i)
                Sf_avg = 0.5 * (Sf_up + Sf_dn)
                h_e = dx * Sf_avg + C_expansion * abs(vh_up - vh_dn)
                F = (z[i] + h_it + vh_up) - (W_dn + vh_dn + h_e)
                delta = 1e-5
                h_pl = h_it + delta
                vh_pl = _vh(h_pl, i)
                Sf_pl = self.compute_friction_slope(h_pl, Q, i)
                h_e_pl = dx * 0.5 * (Sf_pl + Sf_dn) + C_expansion * abs(vh_pl - vh_dn)
                dFdh = ((z[i] + h_pl + vh_pl) - (W_dn + vh_dn + h_e_pl) - F) / delta
                if abs(dFdh) < 1e-12:
                    break
                dh_nwt = float(np.clip(-F / dFdh, -0.5, 0.5))
                h_it = max(h_it + dh_nwt, 1e-4)
                if abs(dh_nwt) < 3e-4:
                    converged = True
                    break
            if not converged:
                h_it = max(h_dn - dx * self.dh_dx(h_dn, Q), 1e-4)
            if h_it > _MAX_DEPTH or np.isnan(h_it) or np.isinf(h_it):
                h_it = h[i + 1]; divergence_count += 1
            h[i] = h_it
        result: Dict = {"x": x, "h": h, "Q": Q * np.ones(nx), "method": "standard_step"}
        if divergence_count > nx * 0.3:
            result["warning"] = "solver_partially_diverged"
            result["divergence_fraction"] = divergence_count / nx
        return result
    
    def _solve_standard_step_variable_xs(
        self,
        Q: float,
        h_downstream: float,
        nx: int = 201,
        alpha: float = 1.0,
        contraction_coef: float = 0.1,
        expansion_coef: float = 0.3,
    ) -> Dict:
        """Absolute WSE Standard Step with per-station geometry.

        Called by solve_standard_step when bed_elevations is set.
        Iterates on absolute water surface elevation W, consistent with HEC-RAS.
        Uses actual HEC-RAS reach lengths, Manning n, and loss coefficients when available.
        """
        bed = np.asarray(self._bed_elevations, dtype=float)
        n_xs = len(bed)
        # Use actual reach lengths from HEC-RAS if available
        if self._reach_lengths and len(self._reach_lengths) >= n_xs:
            rl = np.asarray(self._reach_lengths, dtype=float)
            x = np.zeros(n_xs)
            for k in range(1, n_xs):
                x[k] = x[k-1] + max(rl[k-1], 0.1)
        else:
            x = np.linspace(0, self.length, n_xs)
        h = np.zeros(n_xs)
        W = np.zeros(n_xs)
        h[-1] = h_downstream
        W[-1] = bed[-1] + h_downstream
        # Reasonable W upper bound: max bed + 100m depth
        _W_MAX = float(np.max(bed)) + 100.0
        _diverge_count = 0
        for i in range(n_xs - 2, -1, -1):
            dx_seg = float(abs(x[i + 1] - x[i]))
            if dx_seg < 1e-6:
                dx_seg = 1.0
            h_ds = max(W[i + 1] - bed[i + 1], 0.01)
            A_ds, _P_ds, _R_ds, _T_ds = self._get_geometry(h_ds, i + 1)
            V_ds = Q / max(A_ds, 1e-9)
            Sf_ds = self.compute_friction_slope(h_ds, Q, i + 1)
            vh_ds = alpha * V_ds ** 2 / (2.0 * self.g)
            W_trial = W[i + 1]
            for _iter in range(30):
                h_us = max(W_trial - bed[i], 0.01)
                h_us = min(h_us, 100.0)  # cap depth at 100m
                A_us, _P_us, _R_us, _T_us = self._get_geometry(h_us, i)
                V_us = Q / max(A_us, 1e-9)
                Sf_us = self.compute_friction_slope(h_us, Q, i)
                vh_us = alpha * V_us ** 2 / (2.0 * self.g)
                Sf_avg = 0.5 * (Sf_us + Sf_ds)
                # Cap friction slope to avoid explosion
                Sf_avg = min(Sf_avg, 1.0)
                # Use per-XS loss coefficients from HEC-RAS when available
                cc = contraction_coef
                ec = expansion_coef
                if self._contraction_coefs and i < len(self._contraction_coefs):
                    cc = self._contraction_coefs[i]
                if self._expansion_coefs and i < len(self._expansion_coefs):
                    ec = self._expansion_coefs[i]
                if vh_us > vh_ds:
                    h_minor = cc * (vh_us - vh_ds)
                else:
                    h_minor = ec * (vh_ds - vh_us)
                W_new = W[i + 1] + vh_ds - vh_us + dx_seg * Sf_avg + h_minor
                if abs(W_new - W_trial) < 3e-4:
                    W_trial = W_new; break
                W_trial = W_new
            # Divergence protection
            if W_trial > _W_MAX or W_trial < bed[i] - 10 or np.isnan(W_trial):
                W_trial = W[i + 1] + (bed[i] - bed[i + 1])  # follow bed slope
                _diverge_count += 1
            W[i] = W_trial
            h[i] = max(W[i] - bed[i], 0.001)
        return {"x": x, "h": h, "W": W, "Q": np.full(n_xs, Q), "bed": bed,
                "method": "standard_step_variable_xs"}
    
    # General solve entry

    def solve_without_structures(self, Q: float, h_downstream: float, nx: int = 201, method: str = "standard_step") -> Dict:
        """Solve steady profile with no hydraulic structures."""
        x = np.linspace(0, self.length, nx)
        if method == "standard_step":
            return self.solve_standard_step(Q, h_downstream, nx)
        elif method == "shooting":
            h = np.zeros(nx)
            h[-1] = h_downstream
            dx = self.length / (nx - 1)
            _MAX_DEPTH = 1000.0
            _shoot_divergence = 0
            for i in range(nx - 2, -1, -1):
                h_next = h[i + 1]
                def residual(h_i, _hn=h_next):
                    return h_i - _hn + dx * self.dh_dx((h_i + _hn) / 2.0, Q)
                h_init = h[i + 1] if i == nx - 2 else 2.0 * h[i + 1] - h[i + 2]
                try:
                    h_solved = fsolve(residual, h_init, full_output=True, maxfev=50)
                    h_candidate = float(h_solved[0][0])
                    if abs(h_candidate) > _MAX_DEPTH or np.isnan(h_candidate):
                        raise ValueError("diverged")
                    h[i] = h_candidate
                except Exception:
                    h[i] = float(np.clip(h[i + 1] - dx * self.dh_dx(h[i + 1], Q), 0.001, _MAX_DEPTH))
                    _shoot_divergence += 1
                if h[i] > _MAX_DEPTH or np.isnan(h[i]) or np.isinf(h[i]):
                    h[i] = h[i + 1]; _shoot_divergence += 1
            _result: Dict = {"x": x, "h": h, "Q": Q * np.ones(nx), "method": method}
            if _shoot_divergence > nx * 0.3:
                _result["warning"] = "solver_partially_diverged"
                _result["divergence_fraction"] = _shoot_divergence / nx
            return _result
        else:  # bvp
            def ode_system(x_var, y):
                return np.array([self.dh_dx(float(y[0]), Q)])
            def bc(ya, yb):
                return np.array([yb[0] - h_downstream])
            h_uniform = compute_steady_uniform_flow(Q, self.B, self.S0, self.n, self.g)
            y_init = np.array([h_uniform * np.ones(nx)])
            sol = solve_bvp(ode_system, bc, x, y_init)
            h = sol.sol(x)[0]
        return {"x": x, "h": h, "Q": Q * np.ones(nx), "method": method}

    # Single-gate reach

    def solve_with_single_gate(self, Q: float, h_downstream: float, gate_position: float, gate, nx: int = 201) -> Dict:
        """Solve steady profile for a reach with one gate."""
        x_full = np.linspace(0, self.length, nx)
        gate_idx = int(np.argmin(np.abs(x_full - gate_position)))
        x_gate = float(x_full[gate_idx])
        result_down = self.solve_without_structures(Q, h_downstream, nx - gate_idx, method="shooting")
        h_down = result_down["h"]
        x_down = x_gate + result_down["x"] / self.length * (self.length - x_gate)
        h_gate_down = float(h_down[0])
        def gate_equation(h_up):
            Q_gate, _ = gate.calculate_discharge(h_up, h_gate_down, t=0.0)
            return Q_gate - Q
        try:
            h_gate_up = float(brentq(gate_equation, h_gate_down, h_gate_down + 5.0))
        except Exception:
            h_gate_up = float(fsolve(gate_equation, h_gate_down + 0.1)[0])
        result_up = self.solve_without_structures(Q, h_gate_up, gate_idx + 1, method="shooting")
        h_up = result_up["h"]
        x_up = result_up["x"] / self.length * x_gate
        x_out = np.concatenate([x_up, x_down[1:]])
        h_out = np.concatenate([h_up, h_down[1:]])
        return {"x": x_out, "h": h_out, "Q": Q * np.ones(len(h_out)),
                "gate_position": x_gate, "h_gate_up": h_gate_up,
                "h_gate_down": h_gate_down, "gate_idx": gate_idx}

    # Multi-gate reach

    def solve_with_multiple_gates(self, Q: float, h_downstream: float, gates, nx: int = 201, max_iter: int = 50, tol: float = 1e-4) -> Dict:
        """Solve steady profile for a reach with multiple gates."""
        gates_sorted = sorted(gates, key=lambda g: g[0])
        n_gates = len(gates_sorted)
        x_full = np.linspace(0, self.length, nx)
        gate_positions = [g[0] for g in gates_sorted]
        gate_indices = [int(np.argmin(np.abs(x_full - pos))) for pos in gate_positions]
        segments: List[Dict] = []
        boundaries = [0.0] + [float(x_full[idx]) for idx in gate_indices] + [self.length]
        for i in range(n_gates + 1):
            x_start = boundaries[i]; x_end = boundaries[i + 1]
            if i == n_gates:
                idx_start = gate_indices[-1] if n_gates > 0 else 0; idx_end = nx - 1
            elif i == 0:
                idx_start = 0; idx_end = gate_indices[0]
            else:
                idx_start = gate_indices[i - 1]; idx_end = gate_indices[i]
            nx_seg = idx_end - idx_start + 1
            segments.append({"x_start": x_start, "x_end": x_end, "length": x_end - x_start,
                             "nx": nx_seg, "idx_start": idx_start, "idx_end": idx_end})
        h_uniform = compute_steady_uniform_flow(Q, self.B, self.S0, self.n, self.g)
        h_gates_up = [h_uniform + 0.05 * (i + 1) for i in range(n_gates)]
        h_gates_down = [h_uniform for _ in range(n_gates)]
        max_change = 0.0; iter_count = 0
        for iter_count in range(max_iter):
            h_segments: List[np.ndarray] = []
            x_segments: List[np.ndarray] = []
            for i in range(n_gates, -1, -1):
                seg = segments[i]
                h_bc = h_downstream if i == n_gates else h_gates_up[i]
                ts = SteadyProfileSolver(seg["length"], self.B, self.S0, self.n, self.g, cross_section=self._xs)
                rs = ts.solve_without_structures(Q, h_bc, seg["nx"], method="shooting")
                h_segments.insert(0, rs["h"]); x_segments.insert(0, seg["x_start"] + rs["x"])
                if i > 0:
                    h_gates_down[i - 1] = float(rs["h"][0])
            max_change = 0.0
            for i in range(n_gates):
                _, gate_obj = gates_sorted[i]
                h_dv = h_gates_down[i]
                def gate_eq(h_up, _hd=h_dv):
                    Q_gate, _ = gate_obj.calculate_discharge(h_up, _hd, t=0.0)
                    return Q_gate - Q
                try:
                    h_up_new = float(brentq(gate_eq, h_dv, h_dv + 5.0))
                except Exception:
                    h_up_new = float(fsolve(gate_eq, h_gates_up[i])[0])
                max_change = max(max_change, abs(h_up_new - h_gates_up[i]))
                h_gates_up[i] = 0.3 * h_gates_up[i] + 0.7 * h_up_new
            if max_change < tol:
                break
        return {"x": np.concatenate(x_segments), "h": np.concatenate(h_segments),
                "Q": Q * np.ones(len(np.concatenate(h_segments))),
                "converged": max_change < tol, "iterations": iter_count + 1,
                "h_gates_up": h_gates_up, "h_gates_down": h_gates_down, "gate_positions": gate_positions}


def test_steady_profile_solver() -> None:
    from solvers.gate import SluiceGate
    import time
    solver = SteadyProfileSolver(length=1000.0, B=10.0, S0=0.001, n=0.025)
    Q = 10.0
    h_dn = compute_steady_uniform_flow(Q, 10.0, 0.001, 0.025)
    r1 = solver.solve_without_structures(Q, h_dn, nx=201, method="shooting")
    assert abs(r1["h"][0] - h_dn) < 0.05
    r2 = solver.solve_standard_step(Q, h_dn, nx=201)
    assert abs(r2["h"][0] - h_dn) < 0.05
    bed_elevs = [10.0 - i * 0.1 for i in range(11)]
    sv = SteadyProfileSolver(length=1000.0, B=10.0, S0=0.001, n=0.025, bed_elevations=bed_elevs)
    r3 = sv.solve_standard_step(Q, h_dn)
    assert r3["method"] == "standard_step_variable_xs"
    assert "W" in r3
    print("All self-tests passed.")


if __name__ == "__main__":
    test_steady_profile_solver()
