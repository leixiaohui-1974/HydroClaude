"""Unsteady flow Preissmann Box Scheme solver."""

import numpy as np
from dataclasses import dataclass
from typing import Any, Optional, List
import scipy.sparse as sp
from scipy.sparse.linalg import spsolve
from physics.property_table import subdivided_conveyance


@dataclass
class UnsteadyReachData:
    n_xs: int
    dx: np.ndarray
    bed_elevation: np.ndarray
    manning_n: np.ndarray             # Channel Manning n [n_xs]
    sections: list
    contraction_coef: np.ndarray = None   # Cc [n_xs], default 0.1
    expansion_coef: np.ndarray = None     # Ce [n_xs], default 0.3
    manning_n_lob: np.ndarray = None  # Left overbank Manning n [n_xs]
    manning_n_rob: np.ndarray = None  # Right overbank Manning n [n_xs]
    left_bank: np.ndarray = None      # Left bank station [n_xs] (m)
    right_bank: np.ndarray = None     # Right bank station [n_xs] (m)
    # Pre-built HEC-RAS property tables (optional, takes precedence over computed)
    # Each is a list of (elevations, values) arrays per XS, in SI units
    hecras_pt_elevations: list = None  # [n_xs] of np.ndarray (m)
    hecras_pt_A: list = None           # [n_xs] of np.ndarray (m²) — storage area
    hecras_pt_K: list = None           # [n_xs] of np.ndarray (m³/s) — conveyance
    hecras_pt_B: list = None           # [n_xs] of np.ndarray (m) — top width
    hecras_pt_beta: list = None        # [n_xs] of np.ndarray — momentum correction factor
    dx_lob: np.ndarray = None          # LOB reach lengths [n_xs-1] (m)
    dx_rob: np.ndarray = None          # ROB reach lengths [n_xs-1] (m)


@dataclass
class UnsteadyState:
    Z: np.ndarray
    Q: np.ndarray
    t: float


def _safe_depth(Z: float, bed: float, min_depth: float) -> float:
    return max(Z - bed, min_depth)


class PreissmannSolver:
    def __init__(self, reach: UnsteadyReachData, theta: float = 0.6, g: float = 9.81,
                 nr_max_iter: int = 30, nr_tol: float = 1e-4,
                 min_depth: float = 0.05, max_dZ_per_iter: float = 0.5,
                 lpi_enabled: bool = True, lpi_threshold: float = 1.0,
                 lpi_exponent: float = 2.0,
                 slot_enabled: bool = True, slot_width_ratio: float = 0.01,
                 slot_depth: float = 0.05):
        self.reach = reach
        self.theta = theta
        self.g = g
        self.nr_max_iter = nr_max_iter
        self.nr_tol = nr_tol
        self.min_depth = min_depth
        self.max_dZ_per_iter = max_dZ_per_iter
        self.n = reach.n_xs
        # LPI (Local Partial Inertia) — suppress inertia near/above Fr=1
        self.lpi_enabled = lpi_enabled
        self.lpi_threshold = lpi_threshold
        self.lpi_exponent = lpi_exponent
        # Preissmann Slot — prevent matrix singularity at dry bed
        self.slot_enabled = slot_enabled
        self.slot_width_ratio = slot_width_ratio
        self.slot_depth = slot_depth
        # Pre-build property tables for fast geometry lookup
        self._build_property_tables()

    def _build_property_tables(self, n_pts: int = 201, max_depth: float = 30.0):
        """Pre-compute A/B/K vs depth for all cross sections.

        Priority:
        1. HEC-RAS pre-built property tables (hecras_pt_*) — most accurate
        2. Subdivided K from LOB/Channel/ROB (bank stations + Manning n)
        3. Single-n fallback
        """
        n = self.n
        reach = self.reach

        # --- Option 1: HEC-RAS property tables ---
        if (reach.hecras_pt_elevations is not None
                and reach.hecras_pt_A is not None
                and reach.hecras_pt_K is not None
                and reach.hecras_pt_B is not None):
            # Use depth-based lookup: depth = Z - bed_elevation
            # HEC-RAS tables are elevation-based; convert to depth for solver
            self._pt_depths = np.linspace(0, max_depth, n_pts)
            self._pt_A = np.zeros((n, n_pts))
            self._pt_B = np.zeros((n, n_pts))
            self._pt_P = np.zeros((n, n_pts))
            self._pt_K = np.zeros((n, n_pts))
            self._pt_beta = np.ones((n, n_pts))  # momentum correction factor
            has_beta = reach.hecras_pt_beta is not None
            for i in range(n):
                bed = reach.bed_elevation[i]
                elev_table = reach.hecras_pt_elevations[i]
                depth_table = elev_table - bed
                A_table = reach.hecras_pt_A[i]
                K_table = reach.hecras_pt_K[i]
                B_table = reach.hecras_pt_B[i]
                for j, d in enumerate(self._pt_depths):
                    if d <= 0:
                        continue
                    self._pt_A[i, j] = max(float(np.interp(d, depth_table, A_table)), 1e-10)
                    self._pt_K[i, j] = max(float(np.interp(d, depth_table, K_table)), 1e-10)
                    self._pt_B[i, j] = max(float(np.interp(d, depth_table, B_table)), 1e-6)
                    if has_beta:
                        beta_table = reach.hecras_pt_beta[i]
                        self._pt_beta[i, j] = max(float(np.interp(d, depth_table, beta_table)), 1.0)
            return

        # --- Option 2/3: Compute from cross-section geometry ---
        self._pt_depths = np.linspace(0, max_depth, n_pts)
        self._pt_A = np.zeros((n, n_pts))
        self._pt_B = np.zeros((n, n_pts))
        self._pt_P = np.zeros((n, n_pts))
        self._pt_K = np.zeros((n, n_pts))
        self._pt_beta = np.ones((n, n_pts))  # default beta=1.0
        has_subdivide = (reach.left_bank is not None and reach.right_bank is not None
                         and reach.manning_n_lob is not None and reach.manning_n_rob is not None)
        for i in range(n):
            sec = reach.sections[i]
            n_ch = reach.manning_n[i]
            for j, d in enumerate(self._pt_depths):
                if d <= 0:
                    continue
                geom = sec.compute_geometry(float(d))
                a = max(geom.area, 1e-10)
                b = max(geom.width, 1e-6)
                p = max(geom.perimeter, 1e-6)
                self._pt_A[i, j] = a
                self._pt_B[i, j] = b
                self._pt_P[i, j] = p
                if has_subdivide and hasattr(sec, 'distances') and hasattr(sec, 'elevations'):
                    lb = reach.left_bank[i]
                    rb = reach.right_bank[i]
                    n_lob = reach.manning_n_lob[i]
                    n_rob = reach.manning_n_rob[i]
                    wl = reach.bed_elevation[i] + d
                    K_total, _A = subdivided_conveyance(
                        np.asarray(sec.distances), np.asarray(sec.elevations),
                        wl, lb, rb, n_lob, n_ch, n_rob)
                    self._pt_K[i, j] = max(K_total, 1e-10)
                else:
                    r = a / p
                    self._pt_K[i, j] = max((1.0 / n_ch) * a * r ** (2.0 / 3.0), 1e-10)

    def solve(self, state0: UnsteadyState, t_end: float, dt: float,
              upstream_bc: Any, downstream_bc: Any,
              output_interval = None, verbose: bool = False) -> dict:
        reach = self.reach
        n = self.n
        Z = np.array(state0.Z, dtype=float)
        Q = np.array(state0.Q, dtype=float)
        t = float(state0.t)
        for i in range(n):
            if np.isnan(Z[i]): Z[i] = reach.bed_elevation[i] + self.min_depth
            if np.isnan(Q[i]): Q[i] = 0.0
        out_interval = dt if output_interval is None else float(output_interval)
        times_out = [t]
        Z_out = [Z.copy()]
        Q_out = [Q.copy()]
        next_out_t = t + out_interval
        while t < t_end - 1e-10:
            dt_actual = min(dt, t_end - t)
            t_new = t + dt_actual
            Z_new, Q_new, converged, nr_iter = self._advance_one_step(
                Z, Q, t, t_new, dt_actual, upstream_bc, downstream_bc)
            if verbose:
                q_up = upstream_bc(t_new)
                print(f"  t={t_new:8.1f}s  NR={nr_iter}  conv={converged}  Q={q_up:.2f}  Zmax={Z_new.max():.3f}")
            Z, Q, t = Z_new, Q_new, t_new
            if t >= next_out_t - 1e-10:
                times_out.append(t)
                Z_out.append(Z.copy())
                Q_out.append(Q.copy())
                next_out_t += out_interval
        return {"times": np.array(times_out), "Z_history": np.array(Z_out), "Q_history": np.array(Q_out)}

    def compute_mass_balance(self, result: dict) -> dict:
        times = result["times"]
        Z_hist = result["Z_history"]
        Q_hist = result["Q_history"]
        if len(times) < 2: return {"error_percent": 0.0}
        reach = self.reach
        vol_in  = float(np.trapz(Q_hist[:, 0],  times))
        vol_out = float(np.trapz(Q_hist[:, -1], times))
        def _storage(Z_arr):
            s = 0.0
            for i in range(reach.n_xs):
                depth = max(Z_arr[i] - reach.bed_elevation[i], 0.0)
                geom = reach.sections[i].compute_geometry(depth)
                dx_i = (reach.dx[0]/2 if i == 0 else reach.dx[-1]/2 if i == reach.n_xs-1
                        else (reach.dx[i-1]+reach.dx[i])/2)
                s += geom.area * dx_i
            return s
        delta_s = _storage(Z_hist[-1]) - _storage(Z_hist[0])
        net_in = vol_in - vol_out
        if abs(net_in) < 1e-10 and abs(delta_s) < 1e-10: ep = 0.0
        elif abs(net_in) < 1e-10: ep = 100.0
        else: ep = abs(net_in - delta_s) / max(abs(net_in), 1e-10) * 100.0
        return {"error_percent": ep}

    def _advance_one_step(self, Z_n, Q_n, t_n, t_np1, dt, upstream_bc, downstream_bc, Z_upstream=None):
        """Advance one time step. If Z_upstream is given, use stage BC at upstream (for junction)."""
        n = self.n
        reach = self.reach
        Z = Z_n.copy()
        Q = Q_n.copy()
        Q_up = float(upstream_bc(t_np1)) if Z_upstream is None else 0.0
        A_n, B_n, K_n, bm_n = self._compute_hydraulics_all(Z_n, Q_n)
        converged = False
        nr_iter = 0
        for nr_iter in range(1, self.nr_max_iter + 1):
            A, B, K, bm = self._compute_hydraulics_all(Z, Q)
            F, J = self._build_system(Z, Q, Z_n, Q_n, A, B, K, bm, A_n, B_n, K_n, bm_n,
                                      dt, Q_up, t_np1, downstream_bc, Z_up=Z_upstream)
            try:
                delta = spsolve(J.tocsr(), -F)
            except Exception:
                break
            if not np.all(np.isfinite(delta)): break
            dZ = np.clip(delta[0::2], -self.max_dZ_per_iter, self.max_dZ_per_iter)
            dQ = delta[1::2]
            Z = Z + dZ
            Q = Q + dQ
            for i in range(n):
                z_min = reach.bed_elevation[i] + self.min_depth
                if Z[i] < z_min: Z[i] = z_min
            if np.max(np.abs(dZ)) < self.nr_tol and np.max(np.abs(dQ)) < self.nr_tol:
                converged = True
                break
        return Z, Q, converged, nr_iter

    def _compute_lpi_sigma(self, A, B, Q):
        n = self.n
        if not self.lpi_enabled:
            return np.ones(n - 1)
        A_avg = 0.5 * (A[:-1] + A[1:])
        B_avg = 0.5 * (B[:-1] + B[1:])
        Q_avg = 0.5 * (Q[:-1] + Q[1:])
        D_avg = A_avg / np.maximum(B_avg, 0.01)
        V_avg = Q_avg / np.maximum(A_avg, 1e-6)
        Fr = np.abs(V_avg) / np.maximum(np.sqrt(self.g * D_avg), 1e-6)
        sigma = np.ones(n - 1)
        mask = Fr > self.lpi_threshold
        if np.any(mask):
            sigma[mask] = np.maximum(0.0, 1.0 - (Fr[mask] / self.lpi_threshold) ** self.lpi_exponent)
        return sigma

    def _compute_hydraulics_all(self, Z, Q):
        """Fast geometry lookup using pre-computed property tables (np.interp)."""
        n = self.n
        depths = np.maximum(Z - self.reach.bed_elevation, self.min_depth)
        d_tab = self._pt_depths
        A = np.array([np.interp(depths[i], d_tab, self._pt_A[i]) for i in range(n)])
        B = np.array([np.interp(depths[i], d_tab, self._pt_B[i]) for i in range(n)])
        K = np.array([np.interp(depths[i], d_tab, self._pt_K[i]) for i in range(n)])
        beta_m = np.array([np.interp(depths[i], d_tab, self._pt_beta[i]) for i in range(n)])
        A = np.maximum(A, 1e-6)
        B = np.maximum(B, 0.1)
        K = np.maximum(K, 1e-6)
        beta_m = np.maximum(beta_m, 1.0)
        if self.slot_enabled:
            mask = depths < self.slot_depth
            if np.any(mask):
                slot_w = np.maximum(B * self.slot_width_ratio, 0.05)
                A[mask] = np.maximum(A[mask], slot_w[mask] * self.slot_depth)
                B[mask] = np.maximum(B[mask], slot_w[mask])
        return A, B, K, beta_m

    def _build_system(self, Z, Q, Z_n, Q_n, A, B, K, bm, A_n, B_n, K_n, bm_n, dt, Q_up, t_np1, downstream_bc, Z_up=None, ds_junction_Z=None):
        n = len(Z)
        neq = 2 * n
        reach = self.reach
        theta = self.theta
        g = self.g
        nm1 = n - 1
        F = np.zeros(neq)
        if Z_up is not None:
            # Upstream stage BC: Z[0] = Z_up (used for junction downstream reaches)
            F[0] = Z[0] - Z_up
            # J[0,0] = 1.0 (dF/dZ_0), set below via COO
        else:
            # Upstream flow BC: Q[0] = Q_up (default)
            F[0] = Q[0] - Q_up
        sigma   = self._compute_lpi_sigma(A,   B,   Q)
        sigma_n = self._compute_lpi_sigma(A_n, B_n, Q_n)
        dx = reach.dx
        A_L  = A[:-1];   A_R  = A[1:]
        B_L  = B[:-1];   B_R  = B[1:]
        K_L  = K[:-1];   K_R  = K[1:]
        Q_L  = Q[:-1];   Q_R  = Q[1:]
        Z_L  = Z[:-1];   Z_R  = Z[1:]
        bm_L = bm[:-1];  bm_R = bm[1:]
        A_Ln = A_n[:-1]; A_Rn = A_n[1:]
        K_Ln = K_n[:-1]; K_Rn = K_n[1:]
        Q_Ln = Q_n[:-1]; Q_Rn = Q_n[1:]
        Z_Ln = Z_n[:-1]; Z_Rn = Z_n[1:]
        bm_Ln = bm_n[:-1]; bm_Rn = bm_n[1:]
        A_avg   = 0.5 * (A_L   + A_R)
        K_avg   = 0.5 * (K_L   + K_R)
        Q_avg   = 0.5 * (Q_L   + Q_R)
        A_avg_n = 0.5 * (A_Ln  + A_Rn)
        K_avg_n = 0.5 * (K_Ln  + K_Rn)
        Q_avg_n = 0.5 * (Q_Ln  + Q_Rn)
        K2   = K_avg**2   + 1e-30
        K2_n = K_avg_n**2 + 1e-30
        Sf   = Q_avg   * np.abs(Q_avg)   / K2
        Sf_n = Q_avg_n * np.abs(Q_avg_n) / K2_n
        gA   = g * A_avg
        gA_n = g * A_avg_n
        beta_L  = bm_L  * Q_L**2  / A_L
        beta_R  = bm_R  * Q_R**2  / A_R
        beta_Ln = bm_Ln * Q_Ln**2 / A_Ln
        beta_Rn = bm_Rn * Q_Rn**2 / A_Rn
        dZ   = Z_R  - Z_L
        dZ_n = Z_Rn - Z_Ln
        # Contraction/expansion loss: Sf_loss = C * |V²_R/2g - V²_L/2g| / dx
        # C = Cc if contracting (V increases), Ce if expanding
        Cc = reach.contraction_coef
        Ce = reach.expansion_coef
        if Cc is not None and Ce is not None:
            V_L = Q_L / A_L
            V_R = Q_R / A_R
            dV2 = V_R**2 - V_L**2  # positive = contraction
            C_loss = np.where(dV2 > 0, 0.5 * (Cc[:-1] + Cc[1:]), 0.5 * (Ce[:-1] + Ce[1:]))
            Sf_loss = C_loss * np.abs(dV2) / (2.0 * g * dx)
            V_Ln = Q_Ln / A_Ln
            V_Rn = Q_Rn / A_Rn
            dV2_n = V_Rn**2 - V_Ln**2
            C_loss_n = np.where(dV2_n > 0, 0.5 * (Cc[:-1] + Cc[1:]), 0.5 * (Ce[:-1] + Ce[1:]))
            Sf_loss_n = C_loss_n * np.abs(dV2_n) / (2.0 * g * dx)
        else:
            Sf_loss = 0.0
            Sf_loss_n = 0.0
        eq_c = 2 * np.arange(nm1) + 1
        F[eq_c] = (
            (A_R + A_L - A_Rn - A_Ln) / (2.0 * dt)
            + theta       * (Q_R  - Q_L)  / dx
            + (1.0-theta) * (Q_Rn - Q_Ln) / dx
        )
        eq_m = 2 * np.arange(nm1) + 2
        F[eq_m] = (
            sigma   * (Q_R  + Q_L  - Q_Rn  - Q_Ln) / (2.0 * dt)
            + sigma   * theta       * (beta_R  - beta_L)  / dx
            + sigma_n * (1.0-theta) * (beta_Rn - beta_Ln) / dx
            + theta       * gA   * dZ   / dx
            + (1.0-theta) * gA_n * dZ_n / dx
            + theta       * gA   * (Sf   + Sf_loss)
            + (1.0-theta) * gA_n * (Sf_n + Sf_loss_n)
        )
        col_Z_L = 2 * np.arange(nm1)
        col_Q_L = 2 * np.arange(nm1) + 1
        col_Z_R = 2 * np.arange(nm1) + 2
        col_Q_R = 2 * np.arange(nm1) + 3
        Jc_ZL = B_L / (2.0 * dt)
        Jc_QL = -theta / dx
        Jc_ZR = B_R / (2.0 * dt)
        Jc_QR = theta / dx
        dbeta_L_dZL = -bm_L * (Q_L**2) / (A_L**2) * B_L
        dbeta_L_dQL =  2.0 * bm_L * Q_L / A_L
        dbeta_R_dZR = -bm_R * (Q_R**2) / (A_R**2) * B_R
        dbeta_R_dQR =  2.0 * bm_R * Q_R / A_R
        dSf_dQavg = 2.0 * np.abs(Q_avg) / K2
        dgASf_dZL = g * 0.5 * B_L * Sf
        dgASf_dZR = g * 0.5 * B_R * Sf
        dgASf_dQL = gA * dSf_dQavg * 0.5
        dgASf_dQR = gA * dSf_dQavg * 0.5
        dgAdZ_dZL = g * 0.5 * B_L * dZ / dx - gA / dx
        dgAdZ_dZR = g * 0.5 * B_R * dZ / dx + gA / dx
        Jm_ZL = theta * (sigma * (-dbeta_L_dZL / dx) + dgAdZ_dZL + dgASf_dZL)
        Jm_QL = sigma / (2.0 * dt) + theta * (sigma * (-dbeta_L_dQL / dx) + dgASf_dQL)
        Jm_ZR = theta * (sigma * ( dbeta_R_dZR / dx) + dgAdZ_dZR + dgASf_dZR)
        Jm_QR = sigma / (2.0 * dt) + theta * (sigma * ( dbeta_R_dQR / dx) + dgASf_dQR)
        # Upstream BC Jacobian: col=0 for Z_up BC, col=1 for Q_up BC
        us_col = np.array([0 if Z_up is not None else 1])
        rows = np.concatenate([us_col * 0, eq_c, eq_c, eq_c, eq_c, eq_m, eq_m, eq_m, eq_m])
        cols = np.concatenate([us_col, col_Z_L, col_Q_L, col_Z_R, col_Q_R, col_Z_L, col_Q_L, col_Z_R, col_Q_R])
        vals = np.concatenate([[1.0], Jc_ZL, Jc_QL, Jc_ZR, Jc_QR, Jm_ZL, Jm_QL, Jm_ZR, Jm_QR])
        J = sp.coo_matrix((vals, (rows, cols)), shape=(neq, neq)).tolil()

        # Downstream BC layout
        # When ds_junction_Z or Z_up is set: keep ALL momentum, DS BC at last row
        # Otherwise (default): overwrite last momentum with DS Z, Q smoothing at last row
        keep_all_momentum = (Z_up is not None) or (ds_junction_Z is not None)

        if keep_all_momentum:
            eq_ds = neq - 1
            if ds_junction_Z is not None:
                # Junction downstream: Z[-1] = Z_junction
                F[eq_ds] = Z[-1] - ds_junction_Z
                J[eq_ds, 2*(n-1)] = 1.0
            elif hasattr(downstream_bc, "compute_normal_wse"):
                Z_ds = downstream_bc.compute_normal_wse(Q[-1])
                F[eq_ds] = Z[-1] - Z_ds
                J[eq_ds, 2*(n-1)] = 1.0
                dq = max(abs(Q[-1]) * 1e-4, 1e-4)
                Z_dsp = downstream_bc.compute_normal_wse(Q[-1] + dq)
                J[eq_ds, 2*(n-1)+1] = -(Z_dsp - Z_ds) / dq
            else:
                F[eq_ds] = Z[-1] - float(downstream_bc(t_np1))
                J[eq_ds, 2*(n-1)] = 1.0
        else:
            eq_ds_z = 2 * (n - 1)
            eq_ds_q = 2 * (n - 1) + 1
            if hasattr(downstream_bc, "compute_normal_wse"):
                Z_ds = downstream_bc.compute_normal_wse(Q[-1])
                F[eq_ds_z] = Z[-1] - Z_ds
                J[eq_ds_z, 2*(n-1)] = 1.0
                dq = max(abs(Q[-1]) * 1e-4, 1e-4)
                Z_dsp = downstream_bc.compute_normal_wse(Q[-1] + dq)
                J[eq_ds_z, 2*(n-1)+1] = -(Z_dsp - Z_ds) / dq
            else:
                F[eq_ds_z] = Z[-1] - float(downstream_bc(t_np1))
                J[eq_ds_z, 2*(n-1)] = 1.0
            F[eq_ds_q] = Q[-1] - Q[-2]
            J[eq_ds_q, 2*(n-1)+1] =  1.0
            J[eq_ds_q, 2*(n-2)+1] = -1.0
        return F, J
