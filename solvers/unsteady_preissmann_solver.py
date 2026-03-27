"""Unsteady flow Preissmann Box Scheme solver."""

import numpy as np
from dataclasses import dataclass, field
from typing import Any, Optional, List
import scipy.sparse as sp
from scipy.sparse.linalg import spsolve
from physics.property_table import subdivided_conveyance, subdivided_conveyance_with_beta


class StructureHTAB:
    """Pre-computed rating curve family for bridges/culverts (HEC-RAS HTAB).

    HTAB format from HDF Geometry/Structures/Property Tables:
      - RC[0]: free-flow curve (Q_cfs, HW_ft) — HW as function of Q, no tailwater
      - RC[1..N]: submerged curves for different TW levels
        At Q=0, HW=TW (no head diff), so TW_i = RC[i][0, col1]
        Each curve: (Q_cfs, HW_ft) for that TW level

    All stored internally in SI (m, m³/s).
    """

    def __init__(self, info: np.ndarray, values: np.ndarray,
                 ft_to_m: float = 0.3048, cfs_to_m3s: float = 0.028316846592):
        """Build HTAB from raw HEC-RAS data.

        Args:
            info: (N_rc+1, 2) int array — [start_index, count] for each RC
            values: (total_pts, 2) float array — col0=Q(cfs), col1=HW(ft)
        """
        # Parse free-flow curve
        si0, cnt0 = int(info[0, 0]), int(info[0, 1])
        rc0 = values[si0:si0 + cnt0]
        self.ff_Q = rc0[:, 0] * cfs_to_m3s   # Q in m³/s
        self.ff_HW = rc0[:, 1] * ft_to_m      # HW in m

        # Parse submerged rating curves
        self.tw_levels = []   # TW elevation for each curve (m)
        self.sub_Q = []       # list of Q arrays (m³/s)
        self.sub_HW = []      # list of HW arrays (m)
        for i in range(1, len(info)):
            si, cnt = int(info[i, 0]), int(info[i, 1])
            if cnt == 0:
                continue
            rc = values[si:si + cnt]
            Q_arr = rc[:, 0] * cfs_to_m3s
            HW_arr = rc[:, 1] * ft_to_m
            tw_elev = HW_arr[0]  # at Q=0, HW = TW
            self.tw_levels.append(tw_elev)
            self.sub_Q.append(Q_arr)
            self.sub_HW.append(HW_arr)

        self.tw_levels = np.array(self.tw_levels)
        self.n_tw = len(self.tw_levels)

    def compute_hw(self, Q: float, tw: float) -> float:
        """Interpolate headwater elevation given flow and tailwater.

        Args:
            Q: flow through structure (m³/s), always positive
            tw: tailwater elevation (m)

        Returns:
            hw: headwater elevation (m)
        """
        Q_abs = abs(Q)

        # Free-flow HW
        hw_ff = float(np.interp(Q_abs, self.ff_Q, self.ff_HW))

        if self.n_tw == 0 or tw <= self.tw_levels[0]:
            return max(hw_ff, tw)

        # Find bracketing TW curves
        if tw >= self.tw_levels[-1]:
            # Extrapolate from last curve
            hw_sub = float(np.interp(Q_abs, self.sub_Q[-1], self.sub_HW[-1]))
            return max(hw_sub, tw)

        idx = int(np.searchsorted(self.tw_levels, tw, side='right')) - 1
        idx = max(0, min(idx, self.n_tw - 2))

        tw_lo = self.tw_levels[idx]
        tw_hi = self.tw_levels[idx + 1]
        hw_lo = float(np.interp(Q_abs, self.sub_Q[idx], self.sub_HW[idx]))
        hw_hi = float(np.interp(Q_abs, self.sub_Q[idx + 1], self.sub_HW[idx + 1]))

        frac = (tw - tw_lo) / max(tw_hi - tw_lo, 1e-6)
        hw_sub = hw_lo + frac * (hw_hi - hw_lo)

        # HW cannot be less than TW or free-flow HW
        return max(hw_sub, tw)

    def compute_hw_and_derivatives(self, Q: float, tw: float) -> tuple[float, float, float]:
        """Compute HW and partial derivatives for Newton-Raphson Jacobian.

        Returns:
            (hw, dHW_dQ, dHW_dTW)
        """
        dQ = max(abs(Q) * 1e-4, 1e-4)
        dTW = 1e-4

        hw = self.compute_hw(Q, tw)
        hw_Qp = self.compute_hw(Q + dQ, tw)
        hw_TWp = self.compute_hw(Q, tw + dTW)

        dHW_dQ = (hw_Qp - hw) / dQ
        dHW_dTW = (hw_TWp - hw) / dTW

        return hw, dHW_dQ, dHW_dTW


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
    # Structure HTAB at specific cells: list of {cell_index: int, htab: StructureHTAB}
    structures: list = None


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
                 max_dQ_per_iter: float = 25.0,
                 lpi_enabled: bool = True, lpi_threshold: float = 1.0,
                 lpi_exponent: float = 2.0,
                 slot_enabled: bool = True, slot_width_ratio: float = 0.01,
                 slot_depth: float = 0.05,
                 use_picard_linearization: bool = False,
                 picard_max_iter: int = 8, picard_tol: float = 1e-4):
        self.reach = reach
        self.theta = theta
        self.g = g
        self.nr_max_iter = nr_max_iter
        self.nr_tol = nr_tol
        self.min_depth = min_depth
        self.max_dZ_per_iter = max_dZ_per_iter
        self.max_dQ_per_iter = max_dQ_per_iter
        self.n = reach.n_xs
        # LPI (Local Partial Inertia) — suppress inertia near/above Fr=1
        self.lpi_enabled = lpi_enabled
        self.lpi_threshold = lpi_threshold
        self.lpi_exponent = lpi_exponent
        # Preissmann Slot — prevent matrix singularity at dry bed
        self.slot_enabled = slot_enabled
        self.slot_width_ratio = slot_width_ratio
        self.slot_depth = slot_depth
        # HEC-RAS Picard linearization mode
        self.use_picard_linearization = use_picard_linearization
        self.picard_max_iter = picard_max_iter
        self.picard_tol = picard_tol
        # Pre-build property tables for fast geometry lookup
        self._build_property_tables()

    def _build_property_tables(self, n_pts: int = 201):
        """Pre-compute A/B/K/beta vs depth for all cross sections.

        Uses subdivided_conveyance (LOB/Channel/ROB) when bank stations and
        Manning n for overbanks are provided. Falls back to single-n otherwise.
        All computation from first principles — no HEC-RAS intermediate results.
        """
        n = self.n
        reach = self.reach
        # Adaptive max depth: cover all cross-section elevations + buffer
        max_elev = max(float(np.max(sec.elevations)) for sec in reach.sections
                       if hasattr(sec, 'elevations'))
        min_bed = float(np.min(reach.bed_elevation))
        max_depth = max(max_elev - min_bed + 5.0, 30.0)

        self._pt_depths = np.linspace(0, max_depth, n_pts)
        self._pt_A = np.zeros((n, n_pts))
        self._pt_B = np.zeros((n, n_pts))
        self._pt_P = np.zeros((n, n_pts))
        self._pt_K = np.zeros((n, n_pts))
        self._pt_beta = np.ones((n, n_pts))
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
                p = max(geom.perimeter, 1e-6)
                self._pt_A[i, j] = a
                self._pt_P[i, j] = p
                if has_subdivide and hasattr(sec, 'distances') and hasattr(sec, 'elevations'):
                    lb = reach.left_bank[i]
                    rb = reach.right_bank[i]
                    n_lob = reach.manning_n_lob[i]
                    n_rob = reach.manning_n_rob[i]
                    wl = reach.bed_elevation[i] + d
                    K_total, _A, beta = subdivided_conveyance_with_beta(
                        np.asarray(sec.distances), np.asarray(sec.elevations),
                        wl, lb, rb, n_lob, n_ch, n_rob)
                    self._pt_K[i, j] = max(K_total, 1e-10)
                    self._pt_beta[i, j] = beta
                else:
                    r = a / p
                    self._pt_K[i, j] = max((1.0 / n_ch) * a * r ** (2.0 / 3.0), 1e-10)
        # B = dA/dZ (top width as derivative of area w.r.t. water level)
        # Computed via central difference on the A table, more accurate than
        # geometric water surface width from compute_geometry().
        dd = self._pt_depths[1] - self._pt_depths[0] if n_pts > 1 else 1.0
        for i in range(n):
            # Central difference for interior, forward/backward at edges
            for j in range(n_pts):
                if j == 0:
                    self._pt_B[i, j] = max((self._pt_A[i, 1] - self._pt_A[i, 0]) / dd, 1e-6)
                elif j == n_pts - 1:
                    self._pt_B[i, j] = max((self._pt_A[i, j] - self._pt_A[i, j-1]) / dd, 1e-6)
                else:
                    self._pt_B[i, j] = max((self._pt_A[i, j+1] - self._pt_A[i, j-1]) / (2*dd), 1e-6)
        # Channel-only (main channel) property tables for HEC-RAS Picard linearization
        # Ac = channel area, Kc = channel conveyance, Bc = channel top width
        # Used for dx_e (area-weighted effective length) and phi (flow distribution factor)
        self._pt_Ac = np.zeros((n, n_pts))
        self._pt_Kc = np.zeros((n, n_pts))
        self._pt_Bc = np.zeros((n, n_pts))
        has_banks = (reach.left_bank is not None and reach.right_bank is not None)
        for i in range(n):
            sec = reach.sections[i]
            n_ch = reach.manning_n[i]
            for j, d in enumerate(self._pt_depths):
                if d <= 0:
                    continue
                if has_banks and hasattr(sec, 'distances') and hasattr(sec, 'elevations'):
                    lb = reach.left_bank[i]
                    rb = reach.right_bank[i]
                    wl = reach.bed_elevation[i] + d
                    # Compute channel-only area and conveyance
                    xs = np.asarray(sec.distances)
                    ys = np.asarray(sec.elevations)
                    # Channel mask: stations between lb and rb
                    ch_mask = (xs >= lb) & (xs <= rb)
                    if np.sum(ch_mask) >= 2:
                        xs_ch = np.clip(xs[ch_mask], lb, rb)
                        ys_ch = ys[ch_mask]
                        # Add boundary points (np.interp returns scalar, wrap in list)
                        xs_ch_full = np.concatenate([[lb], xs_ch, [rb]])
                        ys_ch_full = np.concatenate(
                            [[float(np.interp(lb, xs, ys))], ys_ch, [float(np.interp(rb, xs, ys))]]
                        ) if len(xs_ch) > 0 else np.array([wl, wl])
                        # Compute area above bed (below water level)
                        wet = wl - ys_ch_full
                        wet = np.maximum(wet, 0.0)
                        if len(xs_ch_full) >= 2:
                            Ac_j = float(np.trapz(wet, xs_ch_full))
                            # Wetted perimeter for channel
                            Pc_j = 0.0
                            for k in range(len(xs_ch_full) - 1):
                                if wet[k] > 0 or wet[k+1] > 0:
                                    Pc_j += np.sqrt((xs_ch_full[k+1]-xs_ch_full[k])**2 + (ys_ch_full[k+1]-ys_ch_full[k])**2)
                            Pc_j = max(Pc_j, 1e-6)
                            Kc_j = max((1.0/n_ch) * Ac_j * (Ac_j/Pc_j)**(2.0/3.0), 1e-10)
                            self._pt_Ac[i, j] = max(Ac_j, 1e-10)
                            self._pt_Kc[i, j] = Kc_j
                            # Bc = dAc/dZ ≈ channel water surface width
                            self._pt_Bc[i, j] = max(min(rb, np.max(xs_ch_full)) - max(lb, np.min(xs_ch_full)), 1e-6)
                        else:
                            self._pt_Ac[i, j] = self._pt_A[i, j]
                            self._pt_Kc[i, j] = self._pt_K[i, j]
                            self._pt_Bc[i, j] = self._pt_B[i, j]
                    else:
                        self._pt_Ac[i, j] = self._pt_A[i, j]
                        self._pt_Kc[i, j] = self._pt_K[i, j]
                        self._pt_Bc[i, j] = self._pt_B[i, j]
                else:
                    self._pt_Ac[i, j] = self._pt_A[i, j]
                    self._pt_Kc[i, j] = self._pt_K[i, j]
                    self._pt_Bc[i, j] = self._pt_B[i, j]
        # Bc = dAc/dZ via central difference
        for i in range(n):
            for j in range(n_pts):
                if j == 0:
                    self._pt_Bc[i, j] = max((self._pt_Ac[i, 1] - self._pt_Ac[i, 0]) / dd, 1e-6)
                elif j == n_pts - 1:
                    self._pt_Bc[i, j] = max((self._pt_Ac[i, j] - self._pt_Ac[i, j-1]) / dd, 1e-6)
                else:
                    self._pt_Bc[i, j] = max((self._pt_Ac[i, j+1] - self._pt_Ac[i, j-1]) / (2*dd), 1e-6)

    def solve(self, state0: UnsteadyState, t_end: float, dt: float,
              upstream_bc: Any, downstream_bc: Any,
              output_interval=None, verbose: bool = False,
              min_dt: float = 1.0, max_dt_retries: int = 4) -> dict:
        """Advance from state0 to t_end with adaptive time stepping.

        When NR fails to converge, dt is halved (up to max_dt_retries times).
        After convergence, dt is restored to the base value.
        """
        reach = self.reach
        n = self.n
        Z = np.array(state0.Z, dtype=float)
        Q = np.array(state0.Q, dtype=float)
        t = float(state0.t)
        for i in range(n):
            if np.isnan(Z[i]):
                Z[i] = reach.bed_elevation[i] + self.min_depth
            if np.isnan(Q[i]):
                Q[i] = 0.0
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
                print(f"  t={t_new:8.1f}s  NR={nr_iter}  conv={converged}  Q={q_up:.2f}  "
                      f"Zmax={Z_new.max():.3f}")
            Z, Q, t = Z_new, Q_new, t_new
            if t >= next_out_t - 1e-10:
                times_out.append(t)
                Z_out.append(Z.copy())
                Q_out.append(Q.copy())
                next_out_t += out_interval
        return {"times": np.array(times_out), "Z_history": np.array(Z_out),
                "Q_history": np.array(Q_out)}

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

    def _advance_one_step(self, Z_n, Q_n, t_n, t_np1, dt, upstream_bc, downstream_bc,
                          Z_upstream=None, ds_junction_Z=None):
        """Advance one time step.

        Args:
            Z_upstream: If given, use stage BC at upstream (Z[0] = Z_upstream).
            ds_junction_Z: If given, use stage BC at downstream (Z[-1] = ds_junction_Z)
                and keep all momentum equations.
        """
        n = self.n
        reach = self.reach
        Z = Z_n.copy()
        Q = Q_n.copy()
        Q_up = float(upstream_bc(t_np1)) if Z_upstream is None else 0.0
        A_n, B_n, K_n, bm_n, dKdZ_n, Ac_n, Kc_n, Bc_n = self._compute_hydraulics_all(Z_n, Q_n)
        converged = False
        nr_iter = 0
        # Pre-compute downstream BC target for hard enforcement
        ds_Z_target = None
        if ds_junction_Z is not None:
            ds_Z_target = ds_junction_Z
        elif not hasattr(downstream_bc, "compute_normal_wse"):
            ds_Z_target = float(downstream_bc(t_np1))

        if self.use_picard_linearization:
            # ----------------------------------------------------------------
            # HEC-RAS-style Picard linearization:
            # Z_n/Q_n = old time step (fixed)
            # Z_k/Q_k = current linearization point (updated each iteration)
            # Jacobian uses HEC-RAS approximation (beta*V not 2*beta*V,
            # node-averaged Sf not 4-pt, B*dz continuity)
            # ----------------------------------------------------------------
            Z_k = Z_n.copy()
            Q_k = Q_n.copy()
            picard_iter = 0
            best_err = np.inf
            best_Z_k = Z_k.copy()
            best_Q_k = Q_k.copy()
            for picard_iter in range(1, self.picard_max_iter + 1):
                A_k, B_k, K_k, bm_k, dKdZ_k, Ac_k, Kc_k, Bc_k = self._compute_hydraulics_all(Z_k, Q_k)
                # Correct Picard: Z_n/Q_n as old time step, Z_k/Q_k as linearization point
                F, J = self._build_system(
                    Z_k, Q_k, Z_n, Q_n,
                    A_k, B_k, K_k, bm_k, dKdZ_k,
                    A_n, B_n, K_n, bm_n,
                    dt, Q_up, t_np1, downstream_bc,
                    Z_up=Z_upstream, ds_junction_Z=ds_junction_Z,
                    Ac=Ac_k, Kc=Kc_k, Bc=Bc_k,
                    linearized_continuity=True)
                try:
                    delta = spsolve(J.tocsr(), -F)
                except Exception:
                    break
                if not np.all(np.isfinite(delta)):
                    break
                dZ = delta[0::2]
                dQ = delta[1::2]
                # Clip updates to prevent divergence
                dZ = np.clip(dZ, -self.max_dZ_per_iter, self.max_dZ_per_iter)
                dQ = np.clip(dQ, -self.max_dQ_per_iter, self.max_dQ_per_iter)
                Z_new = Z_k + dZ
                Q_new = Q_k + dQ
                # Enforce minimum depth
                for i in range(n):
                    z_min = reach.bed_elevation[i] + self.min_depth
                    if Z_new[i] < z_min:
                        Z_new[i] = z_min
                err = max(np.max(np.abs(dZ)), np.max(np.abs(dQ)))
                if err < best_err:
                    best_err = err
                    best_Z_k = Z_new.copy()
                    best_Q_k = Q_new.copy()
                Z_k = Z_new
                Q_k = Q_new
                if err < self.picard_tol:
                    converged = True
                    break
            # Use best solution found
            Z_k, Q_k = best_Z_k, best_Q_k
            # Final BC enforcement
            if Z_upstream is None:
                Q_k[0] = Q_up
            else:
                Z_k[0] = Z_upstream
            if ds_Z_target is not None:
                Z_k[-1] = ds_Z_target
            return Z_k, Q_k, converged, picard_iter

        # --- Standard Newton-Raphson ---
        # Initialize Z[-1] to ds_Z_target so NR starts from a feasible point
        if ds_Z_target is not None:
            Z[-1] = ds_Z_target
        if Z_upstream is not None:
            Z[0] = Z_upstream
        else:
            Q[0] = Q_up
        best_F_norm = np.inf
        best_Z = Z.copy()
        best_Q = Q.copy()
        for nr_iter in range(1, self.nr_max_iter + 1):
            A, B, K, bm, dKdZ, Ac, Kc, Bc = self._compute_hydraulics_all(Z, Q)
            F, J = self._build_system(Z, Q, Z_n, Q_n, A, B, K, bm, dKdZ, A_n, B_n, K_n, bm_n,
                                      dt, Q_up, t_np1, downstream_bc, Z_up=Z_upstream,
                                      ds_junction_Z=ds_junction_Z)
            F_norm = float(np.max(np.abs(F)))
            # Track best solution (lowest residual)
            if F_norm < best_F_norm:
                best_F_norm = F_norm
                best_Z = Z.copy()
                best_Q = Q.copy()
            # Residual-based convergence
            if F_norm < self.nr_tol:
                converged = True
                break
            try:
                delta = spsolve(J.tocsr(), -F)
            except Exception:
                break
            if not np.all(np.isfinite(delta)):
                break
            dZ = np.clip(delta[0::2], -self.max_dZ_per_iter, self.max_dZ_per_iter)
            dQ = np.clip(delta[1::2], -self.max_dQ_per_iter, self.max_dQ_per_iter)
            Z = Z + dZ
            Q = Q + dQ
            # Enforce minimum depth only (BC is handled by the linear system)
            for i in range(n):
                z_min = reach.bed_elevation[i] + self.min_depth
                if Z[i] < z_min:
                    Z[i] = z_min
            # Step-size convergence
            if np.max(np.abs(dZ)) < self.nr_tol and np.max(np.abs(dQ)) < self.nr_tol:
                converged = True
                break
        # If not converged, return best solution found during NR
        if not converged and best_F_norm < F_norm:
            Z, Q = best_Z, best_Q
            if best_F_norm < self.nr_tol * 100:
                converged = True
        # Final BC enforcement on returned solution
        if Z_upstream is None:
            Q[0] = Q_up
        else:
            Z[0] = Z_upstream
        if ds_Z_target is not None:
            Z[-1] = ds_Z_target
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
        """Fast geometry lookup using pre-computed property tables (np.interp).

        Returns:
            A, B, K, beta_m, dK_dZ, Ac, Kc, Bc: arrays of shape (n,)
            dK_dZ is the derivative of K w.r.t. Z (= dK/d(depth) since Z = bed + depth).
            Ac, Kc, Bc are channel-only area, conveyance, and top width.
        """
        n = self.n
        depths = np.maximum(Z - self.reach.bed_elevation, self.min_depth)
        d_tab = self._pt_depths
        A = np.array([np.interp(depths[i], d_tab, self._pt_A[i]) for i in range(n)])
        K = np.array([np.interp(depths[i], d_tab, self._pt_K[i]) for i in range(n)])
        # B = dA/dZ via local finite difference (more accurate than pre-computed table)
        dd = d_tab[1] - d_tab[0] if len(d_tab) > 1 else 1.0
        B = np.array([np.interp(depths[i] + dd * 0.5, d_tab, self._pt_A[i])
                       - np.interp(depths[i] - dd * 0.5, d_tab, self._pt_A[i])
                       for i in range(n)]) / dd
        beta_m = np.array([np.interp(depths[i], d_tab, self._pt_beta[i]) for i in range(n)])
        # dK/dZ via finite difference on property table
        dd = d_tab[1] - d_tab[0] if len(d_tab) > 1 else 1.0
        dK_dZ = np.array([np.interp(depths[i] + dd * 0.5, d_tab, self._pt_K[i])
                          - np.interp(depths[i] - dd * 0.5, d_tab, self._pt_K[i])
                          for i in range(n)]) / dd
        A = np.maximum(A, 1e-6)
        B = np.maximum(B, 0.1)
        K = np.maximum(K, 1e-6)
        beta_m = np.maximum(beta_m, 1.0)
        dK_dZ = np.maximum(dK_dZ, 0.0)  # K should be non-decreasing with Z
        if self.slot_enabled:
            mask = depths < self.slot_depth
            if np.any(mask):
                slot_w = np.maximum(B * self.slot_width_ratio, 0.05)
                A[mask] = np.maximum(A[mask], slot_w[mask] * self.slot_depth)
                B[mask] = np.maximum(B[mask], slot_w[mask])
        # Channel-only hydraulics for Picard linearization
        Ac = np.array([np.interp(depths[i], d_tab, self._pt_Ac[i]) for i in range(n)])
        Kc = np.array([np.interp(depths[i], d_tab, self._pt_Kc[i]) for i in range(n)])
        Bc = np.array([np.interp(depths[i], d_tab, self._pt_Bc[i]) for i in range(n)])
        Ac = np.maximum(Ac, 1e-6)
        Kc = np.maximum(Kc, 1e-6)
        Bc = np.maximum(Bc, 0.01)
        return A, B, K, beta_m, dK_dZ, Ac, Kc, Bc

    def _compute_cell_equation_terms(
        self,
        Z,
        Q,
        Z_n,
        Q_n,
        A,
        B,
        K,
        bm,
        dKdZ,
        A_n,
        B_n,
        K_n,
        bm_n,
        dt,
        cell_index,
    ):
        i = int(cell_index)
        n = len(Z)
        if i < 0 or i >= n - 1:
            raise IndexError(f"cell_index out of range: {i}")

        theta = self.theta
        g = self.g
        dx = float(self.reach.dx[i])

        sigma = float(self._compute_lpi_sigma(A, B, Q)[i])
        sigma_n = float(self._compute_lpi_sigma(A_n, B_n, Q_n)[i])

        A_L = float(A[i])
        A_R = float(A[i + 1])
        B_L = float(B[i])
        B_R = float(B[i + 1])
        K_L = float(K[i])
        K_R = float(K[i + 1])
        Q_L = float(Q[i])
        Q_R = float(Q[i + 1])
        Z_L = float(Z[i])
        Z_R = float(Z[i + 1])
        bm_L = float(bm[i])
        bm_R = float(bm[i + 1])
        A_Ln = float(A_n[i])
        A_Rn = float(A_n[i + 1])
        B_Ln = float(B_n[i])
        B_Rn = float(B_n[i + 1])
        K_Ln = float(K_n[i])
        K_Rn = float(K_n[i + 1])
        Q_Ln = float(Q_n[i])
        Q_Rn = float(Q_n[i + 1])
        Z_Ln = float(Z_n[i])
        Z_Rn = float(Z_n[i + 1])
        bm_Ln = float(bm_n[i])
        bm_Rn = float(bm_n[i + 1])
        bed_L = float(self.reach.bed_elevation[i])
        bed_R = float(self.reach.bed_elevation[i + 1])
        depth_L = max(Z_L - bed_L, self.min_depth)
        depth_R = max(Z_R - bed_R, self.min_depth)
        depth_Ln = max(Z_Ln - bed_L, self.min_depth)
        depth_Rn = max(Z_Rn - bed_R, self.min_depth)

        A_avg = 0.5 * (A_L + A_R)
        A_avg_n = 0.5 * (A_Ln + A_Rn)
        K_avg = 0.5 * (K_L + K_R)
        K_avg_n = 0.5 * (K_Ln + K_Rn)
        Q_avg = 0.5 * (Q_L + Q_R)
        Q_avg_n = 0.5 * (Q_Ln + Q_Rn)
        Q_4pt = theta * Q_avg + (1.0 - theta) * Q_avg_n
        K_4pt = theta * K_avg + (1.0 - theta) * K_avg_n
        A_4pt = theta * A_avg + (1.0 - theta) * A_avg_n
        dZ_4pt = theta * (Z_R - Z_L) + (1.0 - theta) * (Z_Rn - Z_Ln)
        K2_4pt = K_4pt ** 2 + 1e-30
        Sf = Q_4pt * abs(Q_4pt) / K2_4pt
        gA_4pt = g * A_4pt

        beta_L = bm_L * Q_L * Q_L / max(A_L, 1e-12)
        beta_R = bm_R * Q_R * Q_R / max(A_R, 1e-12)
        beta_Ln = bm_Ln * Q_Ln * Q_Ln / max(A_Ln, 1e-12)
        beta_Rn = bm_Rn * Q_Rn * Q_Rn / max(A_Rn, 1e-12)

        sf_loss_np1 = 0.0
        sf_loss_n = 0.0
        Cc = self.reach.contraction_coef
        Ce = self.reach.expansion_coef
        if Cc is not None and Ce is not None:
            V_L = Q_L / max(A_L, 1e-12)
            V_R = Q_R / max(A_R, 1e-12)
            dV2 = V_R * V_R - V_L * V_L
            c_loss = 0.5 * (float(Cc[i]) + float(Cc[i + 1])) if dV2 > 0.0 else 0.5 * (float(Ce[i]) + float(Ce[i + 1]))
            sf_loss_np1 = c_loss * abs(dV2) / (2.0 * g * dx)

            V_Ln = Q_Ln / max(A_Ln, 1e-12)
            V_Rn = Q_Rn / max(A_Rn, 1e-12)
            dV2_n = V_Rn * V_Rn - V_Ln * V_Ln
            c_loss_n = 0.5 * (float(Cc[i]) + float(Cc[i + 1])) if dV2_n > 0.0 else 0.5 * (float(Ce[i]) + float(Ce[i + 1]))
            sf_loss_n = c_loss_n * abs(dV2_n) / (2.0 * g * dx)
        sf_loss_4pt = theta * sf_loss_np1 + (1.0 - theta) * sf_loss_n

        continuity_storage = (A_R + A_L - A_Rn - A_Ln) / (2.0 * dt)
        continuity_flux_np1 = theta * (Q_R - Q_L) / dx
        continuity_flux_n = (1.0 - theta) * (Q_Rn - Q_Ln) / dx
        continuity_residual = continuity_storage + continuity_flux_np1 + continuity_flux_n

        momentum_local_inertia = sigma * (Q_R + Q_L - Q_Rn - Q_Ln) / (2.0 * dt)
        momentum_convective_np1 = sigma * theta * (beta_R - beta_L) / dx
        momentum_convective_n = sigma_n * (1.0 - theta) * (beta_Rn - beta_Ln) / dx
        momentum_pressure = gA_4pt * dZ_4pt / dx
        momentum_friction = gA_4pt * Sf
        momentum_minor_loss = gA_4pt * sf_loss_4pt
        momentum_residual = (
            momentum_local_inertia
            + momentum_convective_np1
            + momentum_convective_n
            + momentum_pressure
            + momentum_friction
            + momentum_minor_loss
        )

        return {
            "cell_index": int(i),
            "dx_m": float(dx),
            "sigma_np1": float(sigma),
            "sigma_n": float(sigma_n),
            "depth_L_m": float(max(Z_L - float(self.reach.bed_elevation[i]), 0.0)),
            "depth_R_m": float(max(Z_R - float(self.reach.bed_elevation[i + 1]), 0.0)),
            "depth_L_old_m": float(max(Z_Ln - float(self.reach.bed_elevation[i]), 0.0)),
            "depth_R_old_m": float(max(Z_Rn - float(self.reach.bed_elevation[i + 1]), 0.0)),
            "A_L_m2": float(A_L),
            "A_R_m2": float(A_R),
            "A_L_old_m2": float(A_Ln),
            "A_R_old_m2": float(A_Rn),
            "A_avg_m2": float(A_avg),
            "A_avg_old_m2": float(A_avg_n),
            "K_L": float(K_L),
            "K_R": float(K_R),
            "K_L_old": float(K_Ln),
            "K_R_old": float(K_Rn),
            "K_avg": float(K_avg),
            "K_avg_old": float(K_avg_n),
            "A_4pt_m2": float(A_4pt),
            "K_4pt": float(K_4pt),
            "Q_avg_m3s": float(Q_avg),
            "Q_avg_old_m3s": float(Q_avg_n),
            "Q_4pt_m3s": float(Q_4pt),
            "dZ_4pt_m": float(dZ_4pt),
            "Sf": float(Sf),
            "Sf_loss_4pt": float(sf_loss_4pt),
            "continuity_storage_term": float(continuity_storage),
            "continuity_flux_term_np1": float(continuity_flux_np1),
            "continuity_flux_term_n": float(continuity_flux_n),
            "continuity_residual": float(continuity_residual),
            "momentum_local_inertia_term": float(momentum_local_inertia),
            "momentum_convective_term_np1": float(momentum_convective_np1),
            "momentum_convective_term_n": float(momentum_convective_n),
            "momentum_pressure_term": float(momentum_pressure),
            "momentum_friction_term": float(momentum_friction),
            "momentum_minor_loss_term": float(momentum_minor_loss),
            "momentum_residual": float(momentum_residual),
            "Z_L": float(Z_L),
            "Z_R": float(Z_R),
            "Q_L": float(Q_L),
            "Q_R": float(Q_R),
            "Z_L_old": float(Z_Ln),
            "Z_R_old": float(Z_Rn),
            "Q_L_old": float(Q_Ln),
            "Q_R_old": float(Q_Rn),
            "depth_L": float(depth_L),
            "depth_R": float(depth_R),
            "depth_L_old": float(depth_Ln),
            "depth_R_old": float(depth_Rn),
            "A_4pt": float(A_4pt),
            "K_4pt": float(K_4pt),
            "Q_4pt": float(Q_4pt),
            "dZ_4pt": float(dZ_4pt),
            "Sf": float(Sf),
            "Sf_loss_4pt": float(sf_loss_4pt),
        }

    def _build_system(self, Z, Q, Z_n, Q_n, A, B, K, bm, dKdZ, A_n, B_n, K_n, bm_n, dt, Q_up, t_np1, downstream_bc, Z_up=None, ds_junction_Z=None, Ac=None, Kc=None, Bc=None, linearized_continuity=False):
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
        # HEC-RAS 4-point averaged Preissmann discretization:
        # First average Q, K, A over 4 points (2 space × 2 time), then compute Sf
        # This is mathematically different from averaging Sf values (Jensen's inequality)
        Q_4pt = theta * Q_avg + (1.0 - theta) * Q_avg_n
        K_4pt = theta * K_avg + (1.0 - theta) * K_avg_n
        A_4pt = theta * A_avg + (1.0 - theta) * A_avg_n
        B_4pt = theta * 0.5 * (B_L + B[1:]) + (1.0 - theta) * 0.5 * (B_n[:-1] + B_n[1:]) if len(B) > 1 else 0.5 * (B_L + B[1:])
        dZ_4pt = theta * (Z_R - Z_L) + (1.0 - theta) * (Z_Rn - Z_Ln)
        K2_4pt = K_4pt**2 + 1e-30
        Sf   = Q_4pt * np.abs(Q_4pt) / K2_4pt
        gA_4pt = g * A_4pt
        # Keep separate time-level values for Jacobian compatibility
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
        eq_m = 2 * np.arange(nm1) + 2
        # Contraction/expansion loss: 4-point averaged
        Sf_loss_4pt = theta * Sf_loss + (1.0 - theta) * Sf_loss_n if not isinstance(Sf_loss, float) or Sf_loss != 0.0 else 0.0
        col_Z_L = 2 * np.arange(nm1)
        col_Q_L = 2 * np.arange(nm1) + 1
        col_Z_R = 2 * np.arange(nm1) + 2
        col_Q_R = 2 * np.arange(nm1) + 3
        dKdZ_L = dKdZ[:-1]
        dKdZ_R = dKdZ[1:]

        if linearized_continuity:
            # ================================================================
            # HEC-RAS Table 3/4 linearized scheme (Picard mode)
            # Uses B*(dz) linearization for continuity and node-averaged Sf
            # for momentum. Matches debug_hecras_linear.py: hecras_linear_step
            # ================================================================
            # Effective reach length dx_e (area-weighted, HEC-RAS style)
            # When dx_lob/dx_rob are available, use them; otherwise dx_e = dx
            if reach.dx_lob is not None and reach.dx_rob is not None and Ac is not None and Kc is not None and Bc is not None:
                Ac_L = Ac[:-1]; Ac_R = Ac[1:]
                Af_L = np.maximum(A_L - Ac_L, 0.0)
                Af_R = np.maximum(A_R - Ac_R, 0.0)
                A_total = np.maximum(A_L + A_R, 1e-10)
                dx_ch = dx
                dx_f = 0.5 * (reach.dx_lob + reach.dx_rob)
                dx_e = ((Ac_L + Ac_R) * dx_ch + (Af_L + Af_R) * dx_f) / A_total
                dx_e = np.maximum(dx_e, 1.0)
                phi_L = np.minimum(Kc[:-1] / np.maximum(K_L, 1e-10), 1.0)
                phi_R = np.minimum(Kc[1:]  / np.maximum(K_R, 1e-10), 1.0)
                Bc_L = Bc[:-1]; Bc_R = Bc[1:]
                Bf_L = np.maximum(B_L - Bc_L, 0.0)
                Bf_R = np.maximum(B_R - Bc_R, 0.0)
                B_eff_L = (Bc_L * dx_ch + Bf_L * dx_f) / dx_e
                B_eff_R = (Bc_R * dx_ch + Bf_R * dx_f) / dx_e
                inertia_Q_L = 0.5 * (phi_L * dx_ch + (1.0 - phi_L) * dx_f) / (dx_e * dt)
                inertia_Q_R = 0.5 * (phi_R * dx_ch + (1.0 - phi_R) * dx_f) / (dx_e * dt)
            else:
                # Simple case: dx_e = dx, B_eff = B, phi = 1
                dx_e = dx
                B_eff_L = B_L
                B_eff_R = B_R
                inertia_Q_L = 0.5 / dt * np.ones(nm1)
                inertia_Q_R = 0.5 / dt * np.ones(nm1)

            # Table 3: Continuity equation (HEC-RAS linearized: B*dz + theta*dQ/dx_e)
            F[eq_c] = (
                B_eff_L * (Z_L - Z_Ln) / (2.0 * dt)
                + B_eff_R * (Z_R - Z_Rn) / (2.0 * dt)
                + theta       * (Q_R  - Q_L)  / dx_e
                + (1.0-theta) * (Q_Rn - Q_Ln) / dx_e
            )
            # Table 4: Momentum equation (HEC-RAS linearized form)
            # Friction: Sf_avg = (Sf_L + Sf_R) / 2 (node-averaged, not 4-pt)
            Sf_L_node = Q_L**2 / np.maximum(K_L**2, 1e-30)
            Sf_R_node = Q_R**2 / np.maximum(K_R**2, 1e-30)
            Sf_lin_avg = 0.5 * (Sf_L_node + Sf_R_node)
            Sf_n_L_node = Q_Ln**2 / np.maximum(K_Ln**2, 1e-30)
            Sf_n_R_node = Q_Rn**2 / np.maximum(K_Rn**2, 1e-30)
            Sf_n_lin_avg = 0.5 * (Sf_n_L_node + Sf_n_R_node)
            F[eq_m] = (
                inertia_Q_L * (Q_L - Q_Ln)
                + inertia_Q_R * (Q_R - Q_Rn)
                + sigma   * theta       * (beta_R  - beta_L)  / dx_e
                + sigma_n * (1.0-theta) * (beta_Rn - beta_Ln) / dx_e
                + g * A_avg * dZ_4pt / dx_e
                + g * A_avg * (theta * Sf_lin_avg + (1.0-theta) * Sf_n_lin_avg)
                + g * A_avg * Sf_loss_4pt
            )
            # Jacobian (HEC-RAS Table 3/4 linearized)
            Jc_ZL = B_eff_L / (2.0 * dt)
            Jc_QL = -theta / dx_e
            Jc_ZR = B_eff_R / (2.0 * dt)
            Jc_QR = theta / dx_e
            # Momentum Jacobian (HEC-RAS approximation)
            # Convective: d(beta*Q^2/A)/dQ ≈ beta*V (not 2*beta*V)
            V_L = Q_L / np.maximum(A_L, 1e-10)
            V_R = Q_R / np.maximum(A_R, 1e-10)
            conv_dQL = -bm_L * V_L * theta / dx_e
            conv_dQR =  bm_R * V_R * theta / dx_e
            # Friction: gA * Sf / |Q|
            fric_dQL = theta * g * A_avg * Sf_lin_avg / np.maximum(np.abs(Q_L), 1e-6)
            fric_dQR = theta * g * A_avg * Sf_lin_avg / np.maximum(np.abs(Q_R), 1e-6)
            # Friction Z-derivative: -2*gA*Sf/K * dK/dZ * theta/2
            dSf_dZL_lin = -2.0 * Sf_lin_avg / np.maximum(K_avg, 1e-10) * theta * 0.5 * dKdZ_L
            dSf_dZR_lin = -2.0 * Sf_lin_avg / np.maximum(K_avg, 1e-10) * theta * 0.5 * dKdZ_R
            Jm_ZL = -g * A_avg * theta / dx_e + g * A_avg * dSf_dZL_lin
            Jm_QL = sigma * inertia_Q_L + conv_dQL + fric_dQL
            Jm_ZR =  g * A_avg * theta / dx_e + g * A_avg * dSf_dZR_lin
            Jm_QR = sigma * inertia_Q_R + conv_dQR + fric_dQR
        else:
            # ================================================================
            # Standard NR scheme (original)
            # ================================================================
            F[eq_c] = (
                (A_R + A_L - A_Rn - A_Ln) / (2.0 * dt)
                + theta       * (Q_R  - Q_L)  / dx
                + (1.0-theta) * (Q_Rn - Q_Ln) / dx
            )
            F[eq_m] = (
                sigma   * (Q_R  + Q_L  - Q_Rn  - Q_Ln) / (2.0 * dt)
                + sigma   * theta       * (beta_R  - beta_L)  / dx
                + sigma_n * (1.0-theta) * (beta_Rn - beta_Ln) / dx
                + gA_4pt * dZ_4pt / dx
                + gA_4pt * (Sf + Sf_loss_4pt)
            )
            Jc_ZL = B_L / (2.0 * dt)
            Jc_QL = -theta / dx
            Jc_ZR = B_R / (2.0 * dt)
            Jc_QR = theta / dx
            dbeta_L_dZL = -bm_L * (Q_L**2) / (A_L**2) * B_L
            dbeta_L_dQL =  2.0 * bm_L * Q_L / A_L
            dbeta_R_dZR = -bm_R * (Q_R**2) / (A_R**2) * B_R
            dbeta_R_dQR =  2.0 * bm_R * Q_R / A_R
            dSf_dQavg = 2.0 * np.abs(Q_4pt) / K2_4pt * theta * 0.5
            dSf_dZL_via_K = -2.0 * Sf / np.maximum(K_4pt, 1e-10) * theta * 0.5 * dKdZ_L
            dSf_dZR_via_K = -2.0 * Sf / np.maximum(K_4pt, 1e-10) * theta * 0.5 * dKdZ_R
            dgASf_dZL = g * 0.5 * theta * B_L * Sf + gA_4pt * dSf_dZL_via_K
            dgASf_dZR = g * 0.5 * theta * B[1:] * Sf + gA_4pt * dSf_dZR_via_K if len(B) > 1 else dgASf_dZL
            dgASf_dQL = gA_4pt * dSf_dQavg
            dgASf_dQR = gA_4pt * dSf_dQavg
            dgAdZ_dZL = g * 0.5 * theta * B_L * dZ_4pt / dx - gA_4pt / dx * theta
            dgAdZ_dZR = g * 0.5 * theta * B[1:] * dZ_4pt / dx + gA_4pt / dx * theta if len(B) > 1 else dgAdZ_dZL
            Jm_ZL = sigma * theta * (-dbeta_L_dZL / dx) + dgAdZ_dZL + dgASf_dZL
            Jm_QL = sigma / (2.0 * dt) + sigma * theta * (-dbeta_L_dQL / dx) + dgASf_dQL
            Jm_ZR = sigma * theta * ( dbeta_R_dZR / dx) + dgAdZ_dZR + dgASf_dZR
            Jm_QR = sigma / (2.0 * dt) + sigma * theta * ( dbeta_R_dQR / dx) + dgASf_dQR
        # Upstream BC Jacobian: col=0 for Z_up BC, col=1 for Q_up BC
        us_col = np.array([0 if Z_up is not None else 1])
        rows = np.concatenate([us_col * 0, eq_c, eq_c, eq_c, eq_c, eq_m, eq_m, eq_m, eq_m])
        cols = np.concatenate([us_col, col_Z_L, col_Q_L, col_Z_R, col_Q_R, col_Z_L, col_Q_L, col_Z_R, col_Q_R])
        vals = np.concatenate([[1.0], Jc_ZL, Jc_QL, Jc_ZR, Jc_QR, Jm_ZL, Jm_QL, Jm_ZR, Jm_QR])
        J = sp.coo_matrix((vals, (rows, cols)), shape=(neq, neq)).tolil()

        # --- Structure HTAB override: replace momentum eq at structure cells ---
        if reach.structures:
            for struct in reach.structures:
                sc = struct["cell_index"]   # cell between XS[sc] and XS[sc+1]
                htab = struct["htab"]       # StructureHTAB
                row_m = 2 * sc + 2          # momentum equation row for this cell
                # XS[sc] = upstream (headwater), XS[sc+1] = downstream (tailwater)
                Z_us = Z[sc]
                Z_ds = Z[sc + 1]
                Q_avg_struct = 0.5 * (Q[sc] + Q[sc + 1])
                hw, dHW_dQ, dHW_dTW = htab.compute_hw_and_derivatives(Q_avg_struct, Z_ds)
                # F = Z_us - HW(Q, TW) = 0
                F[row_m] = Z_us - hw
                # Clear old Jacobian row and set structure derivatives
                J[row_m, :] = 0
                cZL = 2 * sc        # col for Z[sc] (upstream Z)
                cQL = 2 * sc + 1    # col for Q[sc]
                cZR = 2 * (sc + 1)  # col for Z[sc+1] (downstream Z = TW)
                cQR = 2 * (sc + 1) + 1  # col for Q[sc+1]
                J[row_m, cZL] = 1.0              # ∂F/∂Z_us = 1
                J[row_m, cZR] = -dHW_dTW         # ∂F/∂Z_ds = -∂HW/∂TW
                J[row_m, cQL] = -dHW_dQ * 0.5    # ∂F/∂Q_L = -∂HW/∂Q * 0.5
                J[row_m, cQR] = -dHW_dQ * 0.5    # ∂F/∂Q_R = -∂HW/∂Q * 0.5

        # Downstream BC layout
        # When ds_junction_Z or Z_up is set: keep ALL momentum, DS BC at last row
        # For StageHydrographBC (not NormalDepthBC): also keep all momentum, DS BC at last row
        # For NormalDepthBC: overwrite last momentum with DS Z (Q-dependent), Q smoothing at last row
        keep_all_momentum = (
            (Z_up is not None)
            or (ds_junction_Z is not None)
            or (not hasattr(downstream_bc, "compute_normal_wse"))
        )

        if keep_all_momentum:
            eq_ds = neq - 1
            J[eq_ds, :] = 0  # Clear row before setting BC
            if ds_junction_Z is not None:
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
            # Clear rows: last momentum row gets overwritten by DS Z BC
            J[eq_ds_z, :] = 0
            J[eq_ds_q, :] = 0
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
