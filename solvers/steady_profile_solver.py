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
        manning_n_lob=None,
        manning_n_rob=None,
        bank_stations=None,
        bridges=None,
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
            manning_ns: Manning n per station (channel zone); falls back to self.n when None
            reach_lengths: Actual reach lengths between XS pairs (m); from HEC-RAS Len Channel
            contraction_coefs: Per-XS contraction loss coefficients
            expansion_coefs: Per-XS expansion loss coefficients
            manning_n_lob: Per-XS Left Overbank Manning n (HEC-RAS 三区分区)
            manning_n_rob: Per-XS Right Overbank Manning n (HEC-RAS 三区分区)
            bank_stations: Per-XS (left_bank_station, right_bank_station) cross-section coords (m)
            bridges: List of bridge dicts with physical parameters for energy method calculation.
                Each dict: {us_xs_index, ds_xs_index, deck_elevation_m, low_chord_elevation_m,
                bridge_length_m, n_piers, total_pier_width_m, pier_loss_coef, ...}
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
        self._manning_n_lob = manning_n_lob
        self._manning_n_rob = manning_n_rob
        self._bank_stations = bank_stations
        self._bridges = bridges  # list[dict] with bridge physical parameters

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
    

    # HEC-RAS 三区 Conveyance 分区计算 (LOB / Channel / ROB)

    def _zone_conveyance(
        self,
        stations: np.ndarray,
        elevations: np.ndarray,
        water_level: float,
        sta_min: float,
        sta_max: float,
        n: float,
    ) -> Tuple[float, float]:
        """Compute conveyance K and flow area for a single overbank zone.

        Clips the station-elevation profile to [sta_min, sta_max] and integrates
        area and wetted perimeter.  Inter-zone vertical faces are NOT counted as
        wetted perimeter (Posey 1967 / HEC-RAS convention).

        Returns:
            (K, A) -- conveyance (m^3/s) and flow area (m^2) for this zone.
        """
        area = 0.0
        perimeter = 0.0

        for j in range(len(stations) - 1):
            s1, s2 = float(stations[j]), float(stations[j + 1])
            z1, z2 = float(elevations[j]), float(elevations[j + 1])

            if s2 <= sta_min or s1 >= sta_max:
                continue

            # Clip to zone boundaries with linear elevation interpolation
            if s1 < sta_min:
                frac = (sta_min - s1) / (s2 - s1)
                z1 = z1 + frac * (z2 - z1)
                s1 = sta_min
            if s2 > sta_max:
                frac = (sta_max - s1) / (s2 - s1)
                z2 = z1 + frac * (z2 - z1)
                s2 = sta_max

            ds = s2 - s1
            if ds <= 0.0:
                continue
            dz = z2 - z1

            if z1 >= water_level and z2 >= water_level:
                continue
            elif z1 < water_level and z2 < water_level:
                d1 = water_level - z1
                d2 = water_level - z2
                area += 0.5 * (d1 + d2) * ds
                perimeter += np.sqrt(ds ** 2 + dz ** 2)
            elif z1 < water_level <= z2:
                frac_wet = (water_level - z1) / (z2 - z1)
                ds_wet = ds * frac_wet
                dz_wet = dz * frac_wet
                area += 0.5 * (water_level - z1) * ds_wet
                perimeter += np.sqrt(ds_wet ** 2 + dz_wet ** 2)
            else:
                frac_wet = (water_level - z2) / (z1 - z2)
                ds_wet = ds * frac_wet
                dz_wet = dz * frac_wet
                area += 0.5 * (water_level - z2) * ds_wet
                perimeter += np.sqrt(ds_wet ** 2 + dz_wet ** 2)

        if area <= 0.0 or perimeter <= 0.0:
            return 0.0, 0.0

        R = area / perimeter
        K = (1.0 / max(n, 0.001)) * area * R ** (2.0 / 3.0)
        return float(K), float(area)

    def _compute_subdivided_conveyance(
        self, h: float, station_index: int
    ) -> Tuple[float, float]:
        """Compute total conveyance K and alpha using HEC-RAS LOB/Channel/ROB subdivision.

        HEC-RAS Hydraulic Reference Manual section 2:
            K_i = (1/n_i) * A_i * R_i^(2/3)
            K_total = K_LOB + K_Ch + K_ROB
            alpha = A_total^2 * sum(K_i^3 / A_i^2) / K_total^3

        Falls back to single-zone calculation when cross-section geometry or bank
        station data is unavailable.

        Args:
            h: Water depth above cross-section minimum elevation (m).
            station_index: Index into self._xs_array and ancillary arrays.

        Returns:
            (K_total, alpha)
        """
        def _n_ch(idx):
            if self._manning_ns and idx < len(self._manning_ns):
                v = self._manning_ns[idx]
                if v and float(v) > 0:
                    return float(v)
            return self.n

        def _n_lob(idx):
            if self._manning_n_lob and idx < len(self._manning_n_lob):
                v = self._manning_n_lob[idx]
                if v and float(v) > 0:
                    return float(v)
            return _n_ch(idx)

        def _n_rob(idx):
            if self._manning_n_rob and idx < len(self._manning_n_rob):
                v = self._manning_n_rob[idx]
                if v and float(v) > 0:
                    return float(v)
            return _n_ch(idx)

        def _fallback():
            A, _P, R, _T = self._get_geometry(h, station_index)
            n_local = _n_ch(station_index)
            K = (1.0 / n_local) * A * max(R, 1e-9) ** (2.0 / 3.0)
            return float(K), 1.0

        xs = self._xs
        if (
            self._xs_array
            and station_index is not None
            and station_index < len(self._xs_array)
        ):
            xs = self._xs_array[station_index]

        if xs is None or not hasattr(xs, "distances") or not hasattr(xs, "elevations"):
            return _fallback()

        if not self._bank_stations or station_index >= len(self._bank_stations):
            return _fallback()

        left_bank, right_bank = self._bank_stations[station_index]
        if left_bank is None or right_bank is None or float(left_bank) >= float(right_bank):
            return _fallback()

        stations_arr = np.asarray(xs.distances, dtype=float)
        elevations_arr = np.asarray(xs.elevations, dtype=float)
        water_level = float(xs.min_elevation) + max(float(h), 1e-6)

        sta_min_all = float(np.min(stations_arr))
        sta_max_all = float(np.max(stations_arr))

        # If bank stations span the entire cross-section (no overbank),
        # fall back to single-zone to avoid numerical artifacts.
        if float(left_bank) <= sta_min_all + 0.01 and float(right_bank) >= sta_max_all - 0.01:
            return _fallback()

        K_lob, A_lob = self._zone_conveyance(
            stations_arr, elevations_arr, water_level,
            sta_min=sta_min_all, sta_max=float(left_bank),
            n=_n_lob(station_index),
        )
        K_ch, A_ch = self._zone_conveyance(
            stations_arr, elevations_arr, water_level,
            sta_min=float(left_bank), sta_max=float(right_bank),
            n=_n_ch(station_index),
        )
        K_rob, A_rob = self._zone_conveyance(
            stations_arr, elevations_arr, water_level,
            sta_min=float(right_bank), sta_max=sta_max_all,
            n=_n_rob(station_index),
        )

        K_total = K_lob + K_ch + K_rob
        A_total = A_lob + A_ch + A_rob

        if K_total <= 0.0 or A_total <= 0.0:
            return _fallback()

        sum_k3_a2 = 0.0
        for K_i, A_i in ((K_lob, A_lob), (K_ch, A_ch), (K_rob, A_rob)):
            if K_i > 0.0 and A_i > 0.0:
                sum_k3_a2 += K_i ** 3 / A_i ** 2

        alpha = A_total ** 2 * sum_k3_a2 / K_total ** 3
        alpha = max(alpha, 1.0)

        return float(K_total), float(alpha)

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
        # --- Bridge index resolution -----------------------------------------
        # Map river stations (us_rs / ds_rs strings) to XS array indices.
        # Requires a matching xs_stations list, which comes from the stations_m
        # field of the HEC-RAS summary (passed in via reach_lengths or external).
        # Fallback: skip if no station labels available.
        _bridge_at_us: dict[int, dict] = {}  # us_xs_index -> bridge dict
        if self._bridges and hasattr(self, "_xs_station_labels") and self._xs_station_labels:
            _labels = self._xs_station_labels
            for _br in self._bridges:
                _us = str(_br.get("us_rs", "")).strip()
                _ds = str(_br.get("ds_rs", "")).strip()
                _us_idx = next((j for j, lbl in enumerate(_labels) if str(lbl).strip() == _us), None)
                _ds_idx = next((j for j, lbl in enumerate(_labels) if str(lbl).strip() == _ds), None)
                if _us_idx is not None:
                    _br_copy = dict(_br)
                    _br_copy["us_xs_index"] = _us_idx
                    _br_copy["ds_xs_index"] = _ds_idx
                    _bridge_at_us[_us_idx] = _br_copy
        # Also support bridges that already carry us_xs_index (numeric index mode)
        elif self._bridges:
            for _br in self._bridges:
                if "us_xs_index" in _br:
                    _bridge_at_us[int(_br["us_xs_index"])] = _br
        # -----------------------------------------------------------------------
        for i in range(n_xs - 2, -1, -1):
            dx_seg = float(abs(x[i + 1] - x[i]))
            if dx_seg < 1e-6:
                dx_seg = 1.0
            h_ds = max(W[i + 1] - bed[i + 1], 0.01)
            A_ds, _P_ds, _R_ds, _T_ds = self._get_geometry(h_ds, i + 1)
            V_ds = Q / max(A_ds, 1e-9)
            # 三区分区输水计算 (HEC-RAS LOB/Channel/ROB)
            K_ds, alpha_ds = self._compute_subdivided_conveyance(h_ds, i + 1)
            Sf_ds = (Q / K_ds) ** 2 if K_ds > 0 else self.compute_friction_slope(h_ds, Q, i + 1)
            vh_ds = alpha_ds * V_ds ** 2 / (2.0 * self.g)
            # 改进初始猜测：当上游床面高于下游水面时（逆坡或陡坡），
            # 直接从 W=bed[i]+h_downstream 作为初始猜测，避免负水深震荡
            h_init_estimate = max(W[i + 1] - bed[i + 1], 0.01)
            W_trial = max(W[i + 1], bed[i] + h_init_estimate)
            W_trial_prev = W_trial - 1.0  # 前一步，用于震荡检测
            W_new = W_trial
            for _iter in range(50):
                h_us = max(W_trial - bed[i], 0.01)
                h_us = min(h_us, 100.0)  # cap depth at 100m
                A_us, _P_us, _R_us, _T_us = self._get_geometry(h_us, i)
                V_us = Q / max(A_us, 1e-9)
                K_us, alpha_us = self._compute_subdivided_conveyance(h_us, i)
                Sf_us = (Q / K_us) ** 2 if K_us > 0 else self.compute_friction_slope(h_us, Q, i)
                vh_us = alpha_us * V_us ** 2 / (2.0 * self.g)
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
                # 物理下限：W 不能低于床面
                W_new = max(W_new, bed[i] + 1e-4)
                if abs(W_new - W_trial) < 3e-4:
                    W_trial = W_new; break
                # 震荡检测：若 W_new 在 W_trial 两侧来回跳，改用二分步
                if _iter >= 2 and (W_new - W_trial) * (W_trial - W_trial_prev) < 0:
                    W_new = 0.5 * (W_trial + W_new)
                W_trial_prev = W_trial
                W_trial = W_new
            # Divergence protection
            if W_trial > _W_MAX or W_trial < bed[i] - 10 or np.isnan(W_trial):
                W_trial = W[i + 1] + (bed[i] - bed[i + 1])  # follow bed slope
                _diverge_count += 1
            # --- Bridge energy-method correction --------------------------------
            # When the current upstream XS is identified as a bridge's upstream face,
            # apply the HEC-RAS Energy Method (4-section approach):
            #
            #   W4 (upstream) = W1 (downstream of bridge) +
            #       contraction loss + friction loss + pier loss + expansion loss
            #
            # W_trial here is the upstream face of the bridge (Section 4).
            # W[i+1] is the downstream approach (Section 1 equivalent).
            # Inside the bridge we model as a single 2→3 step with effective area.
            if i in _bridge_at_us:
                _br = _bridge_at_us[i]
                _br_len = max(float(_br.get("bridge_length_m", 0.0)), 1.0)
                _pier_w = max(float(_br.get("total_pier_width_m", 0.0)), 0.0)
                _pier_k = float(_br.get("pier_loss_coef", 0.0))
                _cc = float(_br.get("contraction_coef", 0.3))
                _ec = float(_br.get("expansion_coef", 0.5))
                _low_chord = float(_br.get("low_chord_elevation_m", 0.0))

                # Effective flow area inside bridge: subtract pier blockage
                h_br = max(W_trial - bed[i], 0.01)
                A_br, _P_br, _R_br, _T_br = self._get_geometry(h_br, i)
                # Pier area approximation: pier_width * depth
                A_pier = _pier_w * h_br
                A_eff = max(A_br - A_pier, A_br * 0.5)  # allow max 50% blockage
                V_eff = Q / max(A_eff, 1e-9)
                vh_eff = V_eff ** 2 / (2.0 * self.g)

                # Pier head loss (K * V^2/2g)
                h_pier = _pier_k * vh_eff

                # Friction loss through bridge opening
                K_br, _alpha_br = self._compute_subdivided_conveyance(h_br, i)
                Sf_br = (Q / K_br) ** 2 if K_br > 0 else self.compute_friction_slope(h_br, Q, i)
                h_f_br = _br_len * Sf_br

                # Velocity head at upstream approach
                vh_us_approach = alpha_us * V_us ** 2 / (2.0 * self.g)
                # Velocity head at downstream approach (W[i+1])
                h_ds_app = max(W[i + 1] - bed[i + 1], 0.01)
                A_ds_app, _, _, _ = self._get_geometry(h_ds_app, i + 1)
                V_ds_app = Q / max(A_ds_app, 1e-9)
                K_ds_app, alpha_ds_app = self._compute_subdivided_conveyance(h_ds_app, i + 1)
                vh_ds_approach = alpha_ds_app * V_ds_app ** 2 / (2.0 * self.g)

                # Contraction loss (entering bridge, Section 4→3)
                dv_contr = max(vh_eff - vh_us_approach, 0.0)
                h_contr = _cc * dv_contr

                # Expansion loss (exiting bridge, Section 2→1)
                dv_exp = max(vh_ds_approach - vh_eff, 0.0)
                h_exp = _ec * dv_exp

                # Total bridge head loss penalty added to W_trial
                h_bridge_total = h_pier + h_f_br + h_contr + h_exp
                W_trial = W_trial + h_bridge_total
                # Re-apply physical limit after bridge correction
                W_trial = max(W_trial, bed[i] + 1e-4)
                W_trial = min(W_trial, _W_MAX)
            # --------------------------------------------------------------------
            W[i] = W_trial
            h[i] = max(W[i] - bed[i], 0.001)
        # ---- Mixed Flow Detection (HEC-RAS Mixed Flow Mode) -------------------
        # 计算每个断面的弗劳德数；若存在 Fr > 1 的区段，启用混合流计算
        froude_arr = np.zeros(n_xs)
        for _mf_i in range(n_xs):
            _mf_h = max(W[_mf_i] - bed[_mf_i], 0.01)
            _mf_A, _mf_P, _mf_R, _mf_T = self._get_geometry(_mf_h, _mf_i)
            _mf_V = Q / max(_mf_A, 1e-9)
            _mf_D = _mf_A / max(_mf_T, 1e-9)
            froude_arr[_mf_i] = _mf_V / np.sqrt(self.g * max(_mf_D, 1e-9))
        _mixed_flow_flag = bool(np.any(froude_arr > 1.0))
        if _mixed_flow_flag:
            W, h = self._solve_mixed_flow(Q, W, bed, n_xs, x,
                                          contraction_coef, expansion_coef)
        return {"x": x, "h": h, "W": W, "Q": np.full(n_xs, Q), "bed": bed,
                "method": "standard_step_variable_xs",
                "mixed_flow": _mixed_flow_flag,
                "froude": froude_arr}
    
    # Mixed Flow Analysis (HEC-RAS Mixed Flow Mode)

    def _compute_critical_depth(self, Q: float, station_index: int) -> float:
        r"""Compute critical depth where Fr=1 (Q^2*T/(g*A^3)=1)."""
        def _criterion(h):
            h_safe = max(h, 1e-4)
            A, _P, _R, T = self._get_geometry(h_safe, station_index)
            if A <= 0.0 or T <= 0.0:
                return -1.0
            return Q ** 2 * T / (self.g * A ** 3) - 1.0
        try:
            f_lo = _criterion(0.001)
            f_hi = _criterion(50.0)
            if f_lo * f_hi > 0:
                raise ValueError("no bracket")
            y_c = brentq(_criterion, 0.001, 50.0, xtol=1e-5, maxiter=100)
        except Exception:
            y_c = float((Q ** 2 / (self.g * max(self.B, 1.0) ** 2)) ** (1.0 / 3.0))
        return float(y_c)

    def _solve_mixed_flow(
        self,
        Q: float,
        W_subcritical: np.ndarray,
        bed: np.ndarray,
        n_xs: int,
        x: np.ndarray,
        contraction_coef: float = 0.1,
        expansion_coef: float = 0.3,
    ):
        r"""Mixed flow analysis: merge sub- and supercritical profiles."""
        # Step 1: critical depth
        y_c = np.zeros(n_xs)
        for i in range(n_xs):
            y_c[i] = self._compute_critical_depth(Q, i)
        W_critical = bed + y_c
        # Step 2: supercritical profile (upstream to downstream)
        W_super = np.full(n_xs, np.nan)
        h_sub_0 = W_subcritical[0] - bed[0]
        if h_sub_0 < y_c[0]:
            W_super[0] = W_subcritical[0]
        else:
            W_super[0] = W_critical[0]
        for i in range(1, n_xs):
            dx_seg = float(abs(x[i] - x[i - 1]))
            if dx_seg < 1e-6:
                dx_seg = 1.0
            h_us = max(W_super[i - 1] - bed[i - 1], 0.001)
            A_us, _P_us, _R_us, _T_us = self._get_geometry(h_us, i - 1)
            V_us = Q / max(A_us, 1e-9)
            K_us, alpha_us = self._compute_subdivided_conveyance(h_us, i - 1)
            Sf_us = (Q / K_us) ** 2 if K_us > 0 else self.compute_friction_slope(h_us, Q, i - 1)
            vh_us = alpha_us * V_us ** 2 / (2.0 * self.g)
            W_trial = max(W_super[i - 1] - 0.1, bed[i] + 0.001)
            for _iter in range(50):
                h_ds = max(W_trial - bed[i], 0.001)
                A_ds, _P_ds, _R_ds, _T_ds = self._get_geometry(h_ds, i)
                V_ds = Q / max(A_ds, 1e-9)
                K_ds, alpha_ds = self._compute_subdivided_conveyance(h_ds, i)
                Sf_ds = (Q / K_ds) ** 2 if K_ds > 0 else self.compute_friction_slope(h_ds, Q, i)
                vh_ds = alpha_ds * V_ds ** 2 / (2.0 * self.g)
                Sf_avg = min(0.5 * (Sf_us + Sf_ds), 1.0)
                cc = contraction_coef
                ec = expansion_coef
                if self._contraction_coefs and i < len(self._contraction_coefs):
                    cc = self._contraction_coefs[i]
                if self._expansion_coefs and i < len(self._expansion_coefs):
                    ec = self._expansion_coefs[i]
                h_minor = cc * (vh_ds - vh_us) if vh_ds > vh_us else ec * (vh_us - vh_ds)
                W_new = W_super[i - 1] + vh_us - vh_ds - dx_seg * Sf_avg + h_minor
                W_new = max(W_new, bed[i] + 0.001)
                if abs(W_new - W_trial) < 3e-4:
                    W_trial = W_new
                    break
                W_trial = 0.5 * (W_trial + W_new)
            W_super[i] = min(max(W_trial, bed[i] + 0.001), W_critical[i])
        # Step 3: select physically correct profile
        W_final = np.copy(W_subcritical)
        for i in range(n_xs):
            if W_subcritical[i] - bed[i] < y_c[i] * 0.99:
                W_final[i] = W_super[i]
        # Step 4: hydraulic jump detection via momentum function
        def _momentum(h_val, idx):
            A, _P, _R, T = self._get_geometry(max(h_val, 0.001), idx)
            y_bar = A / max(T, 1e-9)
            return Q ** 2 / (self.g * max(A, 1e-9)) + A * y_bar
        in_supercritical = False
        jump_indices = []
        for i in range(n_xs - 1, -1, -1):
            h_f = W_final[i] - bed[i]
            A_f, _P_f, _R_f, T_f = self._get_geometry(max(h_f, 0.001), i)
            fr_f = (Q / max(A_f, 1e-9)) / np.sqrt(self.g * max(A_f / max(T_f, 1e-9), 1e-9))
            if fr_f > 1.0 and not in_supercritical:
                in_supercritical = True
            elif fr_f <= 1.0 and in_supercritical:
                jump_indices.append(i + 1)
                in_supercritical = False
        for j_idx in jump_indices:
            if j_idx >= n_xs:
                continue
            h_super_j = W_super[j_idx] - bed[j_idx]
            M_super_j = _momentum(h_super_j, j_idx)
            def _mom_res(h_seq, _M=M_super_j, _idx=j_idx):
                return _momentum(h_seq, _idx) - _M
            try:
                h_seq = brentq(_mom_res, y_c[j_idx], max(y_c[j_idx] * 10.0, 20.0),
                    xtol=1e-4, maxiter=50)
                W_final[j_idx] = bed[j_idx] + h_seq
            except Exception:
                W_final[j_idx] = W_subcritical[j_idx]
        h_final = np.maximum(W_final - bed, 0.001)
        return W_final, h_final

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
