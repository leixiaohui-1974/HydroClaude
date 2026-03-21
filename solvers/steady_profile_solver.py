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


    # Bridge Momentum Method (HEC-RAS Technical Reference Manual Chapter 5)

    def _hydrostatic_pressure_force(self, h: float, station_index: int) -> float:
        """Calculate hydrostatic pressure force P = gamma * A * y_bar_c (N).

        Uses equivalent rectangular section approx: y_bar_c = A / (2 * T),
        where T is water-surface width and A is flow area.

        Args:
            h: water depth (m)
            station_index: cross-section index
        Returns:
            hydrostatic pressure force (N)
        """
        h_safe = max(float(h), 1e-6)
        A, _P, _R, T = self._get_geometry(h_safe, station_index)
        y_bar = A / max(2.0 * T, 1e-6)
        gamma = 9810.0  # N/m^3
        return gamma * A * y_bar

    def _solve_bridge_momentum(
        self,
        Q: float,
        W_downstream: float,
        bridge: dict,
        bed_ds: float,
        bed_us: float,
        ds_xs_index: int,
        us_xs_index: int,
    ) -> float:
        """Compute upstream WSE at bridge using HEC-RAS Momentum Method.

        HEC-RAS TRM Chapter 5 momentum equation (Section 2 to 3):
            beta3*rho*Q*V3 + P3 = beta2*rho*Q*V2 + P2 + F_f + F_pier + W_x

        Section 2 = downstream bridge face (known),
        Section 3 = upstream bridge face (Newton-Raphson iteration).

        Args:
            Q: discharge (m^3/s)
            W_downstream: WSE at downstream bridge face (m)
            bridge: bridge parameter dict
            bed_ds: downstream bed elevation (m)
            bed_us: upstream bed elevation (m)
            ds_xs_index: downstream XS index
            us_xs_index: upstream XS index
        Returns:
            W_upstream: upstream bridge face WSE (m)
        """
        gamma = 9810.0
        rho = 1000.0
        beta2 = 1.0  # Boussinesq momentum correction
        beta3 = 1.0

        L_bridge = max(float(bridge.get("bridge_length_m", 1.0)), 0.1)
        pier_w_total = max(float(bridge.get("total_pier_width_m", 0.0)), 0.0)
        C_D = float(bridge.get("pier_cd", 2.0))
        deck_elev = float(bridge.get("deck_elevation_m", 1e9))
        pier_height = float(bridge.get("pier_height_m", 1e9))

        n_br = (
            self._manning_ns[us_xs_index]
            if self._manning_ns and us_xs_index < len(self._manning_ns)
            else self.n
        )

        h2 = max(W_downstream - bed_ds, 0.01)
        A2, P2_wet, _R2, T2 = self._get_geometry(h2, ds_xs_index)
        A_pier2 = pier_w_total * min(h2, pier_height)
        A2_eff = max(A2 - A_pier2, A2 * 0.3)
        # 壅水判断：使用 EGL (能量梯度线) 而非 WSE
        V2_temp = Q / max(A2_eff, 1e-9)
        EGL2 = W_downstream + V2_temp ** 2 / (2.0 * self.g)
        if EGL2 > deck_elev > bed_ds:
            A2_eff = max(A2_eff - (W_downstream - deck_elev) * T2, A2 * 0.1)
        V2 = Q / max(A2_eff, 1e-9)
        P2_force = self._hydrostatic_pressure_force(h2, ds_xs_index)

        S0_bridge = (bed_us - bed_ds) / max(L_bridge, 0.1)

        W3_trial = W_downstream + max(0.05, abs(bed_us - bed_ds) + 0.05)
        W3_trial = max(W3_trial, bed_us + 0.01)

        for _it in range(40):
            h3 = max(W3_trial - bed_us, 0.01)
            A3, P3_wet, _R3, T3 = self._get_geometry(h3, us_xs_index)
            A_pier3 = pier_w_total * min(h3, pier_height)
            A3_eff = max(A3 - A_pier3, A3 * 0.3)
            # 壅水判断：使用 EGL (能量梯度线) 而非 WSE
            V3_temp = Q / max(A3_eff, 1e-9)
            EGL3 = W3_trial + V3_temp ** 2 / (2.0 * self.g)
            if EGL3 > deck_elev > bed_us:
                A3_eff = max(A3_eff - (W3_trial - deck_elev) * T3, A3 * 0.1)
            V3 = Q / max(A3_eff, 1e-9)
            P3_force = self._hydrostatic_pressure_force(h3, us_xs_index)

            A_avg = 0.5 * (A2_eff + A3_eff)
            P_wet_avg = 0.5 * (P2_wet + P3_wet)
            R_avg = A_avg / max(P_wet_avg, 1e-6)
            V_avg = Q / max(A_avg, 1e-9)
            Sf_avg = min((Q * n_br / max(A_avg * R_avg ** (2.0/3.0), 1e-9)) ** 2, 1.0)

            F_f = gamma * A_avg * Sf_avg * L_bridge
            A_pier_avg = 0.5 * (A_pier2 + A_pier3)
            F_pier = 0.5 * rho * C_D * A_pier_avg * V_avg ** 2
            W_x = gamma * A_avg * S0_bridge * L_bridge

            momentum_rhs = beta2 * rho * Q * V2 + P2_force + F_f + F_pier + W_x
            imbalance = (beta3 * rho * Q * V3 + P3_force) - momentum_rhs

            if abs(imbalance) < max(1.0, abs(momentum_rhs) * 1e-5):
                break

            dW = 1e-3
            h3p = max(h3 + dW, 0.01)
            A3p, _P3pw, _R3p, T3p = self._get_geometry(h3p, us_xs_index)
            A_pier3p = pier_w_total * min(h3p, pier_height)
            A3p_eff = max(A3p - A_pier3p, A3p * 0.3)
            # 壅水判断：使用 EGL (能量梯度线) 而非 WSE
            V3p_temp = Q / max(A3p_eff, 1e-9)
            EGL3p = (W3_trial + dW) + V3p_temp ** 2 / (2.0 * self.g)
            if EGL3p > deck_elev > bed_us:
                A3p_eff = max(A3p_eff - ((W3_trial + dW) - deck_elev) * T3p, A3p * 0.1)
            V3p = Q / max(A3p_eff, 1e-9)
            P3p_force = self._hydrostatic_pressure_force(h3p, us_xs_index)
            d_imb_dW = ((beta3 * rho * Q * V3p + P3p_force) - momentum_rhs - imbalance) / dW

            if abs(d_imb_dW) < 1e-3:
                step = float(np.clip(imbalance / max(gamma * A3, 1.0), -0.5, 0.5))
            else:
                step = float(np.clip(-imbalance / d_imb_dW, -0.5, 0.5))
            W3_trial = max(W3_trial + step, bed_us + 0.005)

        return float(W3_trial)

    def _solve_bridge_energy(
        self,
        Q: float,
        W_downstream: float,
        bridge: dict,
        bed_ds: float,
        bed_us: float,
        ds_xs_index: int,
        us_xs_index: int,
    ) -> float:
        """Compute upstream WSE at bridge using HEC-RAS Energy Method (TRM Section 5.2).

        Energy equation from Section 2 (DS bridge face) to Section 3 (US bridge face):
            W_2 + alpha_2*V_2^2/(2g) = W_3 + alpha_3*V_3^2/(2g) + h_f + h_pier + h_contr

        Args:
            Q: discharge (m^3/s)
            W_downstream: WSE at downstream bridge face Section 2 (m)
            bridge: bridge parameter dict
            bed_ds: downstream bridge face bed elevation (m)
            bed_us: upstream bridge face bed elevation (m)
            ds_xs_index: downstream XS array index
            us_xs_index: upstream XS array index
        Returns:
            W_upstream: upstream bridge face WSE (m)
        """
        L_bridge = max(float(bridge.get("bridge_length_m", 1.0)), 0.1)
        pier_w_total = max(float(bridge.get("total_pier_width_m", 0.0)), 0.0)
        pier_k = float(bridge.get("pier_loss_coef", 0.0))
        pier_height = float(bridge.get("pier_height_m", 1e9))
        deck_elev = float(bridge.get("deck_elevation_m", 1e9))
        cc = float(bridge.get("contraction_coef", 0.1))

        n_br = (
            self._manning_ns[us_xs_index]
            if self._manning_ns and us_xs_index < len(self._manning_ns)
            else self.n
        )

        # ── 桥梁 opening 轮廓（若有）用于构造 NaturalSection ──────────────────
        _op_sta = bridge.get("bridge_opening_stations", [])
        _op_elev = bridge.get("bridge_opening_elevations", [])
        _bridge_ns = None
        if len(_op_sta) > 2 and len(_op_elev) == len(_op_sta):
            try:
                from physics.cross_section import NaturalSection
                _bridge_ns = NaturalSection(
                    "bridge_opening",
                    elevations=np.array(_op_elev, dtype=float),
                    distances=np.array(_op_sta, dtype=float),
                )
            except Exception:
                _bridge_ns = None

        def _eff_area(W_trial: float, xs_idx: int, bed_elev: float) -> tuple[float, float, float]:
            """Return (A_eff, P_wet, alpha) at WSE W_trial for given XS."""
            h = max(W_trial - bed_elev, 0.01)
            A, P_wet, _R, T = self._get_geometry(h, xs_idx)
            # 桥墩面积扣减
            A_pier = pier_w_total * min(h, pier_height)
            if _bridge_ns is not None:
                # 用 NaturalSection 计算桥内净过水面积（相对 NaturalSection 最低点的水深）
                _op_depth = max(W_trial - _bridge_ns.min_elevation, 0.0)
                _geom = _bridge_ns.compute_geometry(_op_depth)
                A_open = max(_geom.area - A_pier, _geom.area * 0.3)
                P_open = max(_geom.perimeter, 1e-6)
            else:
                # 桥面板压顶面积扣减（使用 EGL 判断）
                # 先计算初步的有效面积（仅扣除桥墩）
                A_temp = max(A - A_pier, A * 0.3)
                V_temp = Q / max(A_temp, 1e-9)
                # 计算能量梯度线 EGL
                _, alpha_temp = self._compute_subdivided_conveyance(h, xs_idx)
                EGL_trial = W_trial + alpha_temp * V_temp ** 2 / (2.0 * self.g)
                # 判断是否需要扣除桥面板面积
                A_deck = 0.0
                if EGL_trial > deck_elev > bed_elev:
                    A_deck = (W_trial - deck_elev) * T
                A_open = max(A - A_pier - A_deck, A * 0.3)
                P_open = P_wet
            _, alpha = self._compute_subdivided_conveyance(h, xs_idx)
            return A_open, P_open, alpha

        # ── Section 2（下游桥面）已知量 ──────────────────────────────────────
        A2_eff, P2_wet, alpha2 = _eff_area(W_downstream, ds_xs_index, bed_ds)
        V2 = Q / max(A2_eff, 1e-9)
        E2 = W_downstream + alpha2 * V2 ** 2 / (2.0 * self.g)

        # ── Newton-Raphson 求解 Section 3（上游桥面）WSE ─────────────────────
        # 初始猜测：W_3 ≥ W_2，从下游值开始
        W3_trial = max(W_downstream, bed_us + 0.01)
        W3_trial = max(W3_trial, bed_us + max(W_downstream - bed_ds, 0.01))

        for _it in range(40):
            A3_eff, P3_wet, alpha3 = _eff_area(W3_trial, us_xs_index, bed_us)
            V3 = Q / max(A3_eff, 1e-9)
            vh3 = alpha3 * V3 ** 2 / (2.0 * self.g)

            # 摩擦损失（Manning 平均）
            A_avg = 0.5 * (A2_eff + A3_eff)
            P_avg = 0.5 * (P2_wet + P3_wet)
            R_avg = A_avg / max(P_avg, 1e-6)
            Sf_avg = min((Q * n_br / max(A_avg * R_avg ** (2.0 / 3.0), 1e-9)) ** 2, 1.0)
            h_f = L_bridge * Sf_avg

            # 桥墩局部损失（基于上游桥面速度头）
            h_pier = pier_k * vh3

            # 收缩损失（Section 2 → Section 3 速度头增加时为收缩）
            vh2 = alpha2 * V2 ** 2 / (2.0 * self.g)
            h_contr = cc * max(vh3 - vh2, 0.0)

            # 能量方程残差：f = E2 - (W3 + vh3 + h_f + h_pier + h_contr) = 0
            f_val = E2 - (W3_trial + vh3 + h_f + h_pier + h_contr)

            if abs(f_val) < 1e-4:
                break

            # 数值微分 df/dW3
            dW = 1e-3
            A3p, P3p, alpha3p = _eff_area(W3_trial + dW, us_xs_index, bed_us)
            V3p = Q / max(A3p, 1e-9)
            vh3p = alpha3p * V3p ** 2 / (2.0 * self.g)
            A_avgp = 0.5 * (A2_eff + A3p)
            P_avgp = 0.5 * (P2_wet + P3p)
            R_avgp = A_avgp / max(P_avgp, 1e-6)
            Sf_avgp = min((Q * n_br / max(A_avgp * R_avgp ** (2.0 / 3.0), 1e-9)) ** 2, 1.0)
            h_fp = L_bridge * Sf_avgp
            h_pierp = pier_k * vh3p
            h_contrp = cc * max(vh3p - vh2, 0.0)
            f_valp = E2 - ((W3_trial + dW) + vh3p + h_fp + h_pierp + h_contrp)

            df_dW = (f_valp - f_val) / dW
            if abs(df_dW) < 1e-6:
                step = float(np.clip(f_val * 0.5, -0.5, 0.5))
            else:
                step = float(np.clip(f_val / df_dW, -0.5, 0.5))

            # 能量方程要求 W_3 ≥ W_2（亚临界流），同时不低于床面
            W3_new = max(W3_trial + step, bed_us + 0.005)
            W3_trial = W3_new

        return float(W3_trial)


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
            # --- 改进2：陡坡自适应子步 -------------------------------------------
            # --- 改进2：陡坡自适应子步（v2）-------------------------------------------
            # 触发判据：基于每步能量变化 energy_change = dx_seg * Sf_ds
            # 目标：每子步能量变化 < 0.002m，最多 50 个子步
            n_substeps = 1
            energy_change = dx_seg * Sf_ds
            if energy_change > 0.005 and not (i in _bridge_at_us):
                n_substeps = min(50, max(1, int(energy_change / 0.002)))
            # 子步迭代：每步以前一子步 W 为下游，床面高程线性插值
            # 子步间的断面几何在 i 和 i+1 之间按位置线性插值
            W_sub_ds = W[i + 1]
            bed_sub_ds = bed[i + 1]
            dx_sub = dx_seg / n_substeps
            # 床面高程增量：每子步向 bed[i] 方向推进一格
            _bed_step = (bed[i] - bed[i + 1]) / n_substeps
            for _sub in range(n_substeps):
                bed_sub_us = bed_sub_ds + _bed_step
                # 当前子步下游断面相对位置（0 = 纯 i+1，1 = 纯 i）
                frac_ds = _sub / n_substeps       # 第 _sub 子步下游侧相对 i+1 的距离
                w_i   = frac_ds                    # 靠近 i 的权重
                w_ip1 = 1.0 - frac_ds              # 靠近 i+1 的权重
                # 计算本子步的下游水力量（对两个端面分别算再插值）
                _h_ds_sub = max(W_sub_ds - bed_sub_ds, 0.01)
                # i+1 端面
                _K_ip1, _alpha_ip1 = self._compute_subdivided_conveyance(_h_ds_sub, i + 1)
                _A_ip1 = self._get_geometry(_h_ds_sub, i + 1)[0]
                # i 端面（用同一水深，仅面积和 conveyance 来自 xs[i]）
                _K_i, _alpha_i = self._compute_subdivided_conveyance(_h_ds_sub, i)
                _A_i = self._get_geometry(_h_ds_sub, i)[0]
                # 插值
                _K_ds_sub    = w_ip1 * _K_ip1 + w_i * _K_i
                _alpha_ds_sub = w_ip1 * _alpha_ip1 + w_i * _alpha_i
                _A_ds_sub    = max(w_ip1 * _A_ip1 + w_i * _A_i, 1e-9)
                _Sf_ds_sub   = (Q / _K_ds_sub) ** 2 if _K_ds_sub > 0 else Sf_ds
                _V_ds_sub    = Q / _A_ds_sub
                _vh_ds_sub   = _alpha_ds_sub * _V_ds_sub ** 2 / (2.0 * self.g)
                # 改进初始猜测：考虑床面坡降方向，避免陡坡初始猜测偏低
                _bed_rise     = max(bed_sub_us - bed_sub_ds, 0.0)
                h_init_estimate = max(W_sub_ds - bed_sub_ds, 0.01) + _bed_rise
                W_trial = max(
                    W_sub_ds + _bed_rise,
                    bed_sub_us + h_init_estimate,
                )
                W_trial_prev = W_trial - 1.0  # 前一步，用于震荡检测
                W_new = W_trial
                relax = 1.0  # 松弛因子，震荡时递减
                for _iter in range(80):
                    h_us = max(W_trial - bed_sub_us, 0.01)
                    h_us = min(h_us, 100.0)  # cap depth at 100m
                    A_us, _P_us, _R_us, _T_us = self._get_geometry(h_us, i)
                    V_us = Q / max(A_us, 1e-9)
                    K_us, alpha_us = self._compute_subdivided_conveyance(h_us, i)
                    Sf_us = (Q / K_us) ** 2 if K_us > 0 else self.compute_friction_slope(h_us, Q, i)
                    vh_us = alpha_us * V_us ** 2 / (2.0 * self.g)
                    Sf_avg = 0.5 * (Sf_us + _Sf_ds_sub)
                    # Cap friction slope to avoid explosion
                    Sf_avg = min(Sf_avg, 1.0)
                    # Use per-XS loss coefficients from HEC-RAS when available
                    cc = contraction_coef
                    ec = expansion_coef
                    if self._contraction_coefs and i < len(self._contraction_coefs):
                        cc = self._contraction_coefs[i]
                    if self._expansion_coefs and i < len(self._expansion_coefs):
                        ec = self._expansion_coefs[i]
                    if vh_us > _vh_ds_sub:
                        h_minor = cc * (vh_us - _vh_ds_sub)
                    else:
                        h_minor = ec * (_vh_ds_sub - vh_us)
                    W_new = W_sub_ds + _vh_ds_sub - vh_us + dx_sub * Sf_avg + h_minor
                    # 物理下限：W 不能低于床面
                    W_new = max(W_new, bed_sub_us + 1e-4)
                    # 绝对+相对双重收敛准则
                    _delta = abs(W_new - W_trial)
                    if _delta < 1e-5 or _delta / max(abs(W_trial), 1.0) < 1e-6:
                        W_trial = W_new
                        break
                    # 震荡检测：若 W_new 在 W_trial 两侧来回跳，用松弛因子递减
                    if _iter >= 2 and (W_new - W_trial) * (W_trial - W_trial_prev) < 0:
                        relax = max(0.3, relax * 0.7)
                        W_new = W_trial + relax * (W_new - W_trial)
                    W_trial_prev = W_trial
                    W_trial = W_new
                # 更新子步状态：当前子步上游 W 成为下一子步的下游 W
                W_sub_ds = W_trial
                bed_sub_ds = bed_sub_us
            # 同步 h_us/V_us/alpha_us 供后续 bridge energy 路径使用
            h_us = max(W_trial - bed[i], 0.01)
            A_us, _P_us, _R_us, _T_us = self._get_geometry(h_us, i)
            V_us = Q / max(A_us, 1e-9)
            K_us, alpha_us = self._compute_subdivided_conveyance(h_us, i)
            # -----------------------------------------------------------------------
            # Divergence protection
            if W_trial > _W_MAX or W_trial < bed[i] - 10 or np.isnan(W_trial):
                W_trial = W[i + 1] + (bed[i] - bed[i + 1])  # follow bed slope
                _diverge_count += 1
            # --- Bridge Momentum Method (HEC-RAS TRM Chapter 5) ----------------
            # Default: Momentum Method; set bridge_method="energy" for legacy mode.
            if i in _bridge_at_us:
                _br = _bridge_at_us[i]
                _use_momentum = str(_br.get("bridge_method", "momentum")).lower() != "energy"
                if _use_momentum:
                    W_trial = self._solve_bridge_momentum(
                        Q=Q,
                        W_downstream=W[i + 1],
                        bridge=_br,
                        bed_ds=bed[i + 1],
                        bed_us=bed[i],
                        ds_xs_index=i + 1,
                        us_xs_index=i,
                    )
                else:
                    # Legacy Energy Method path
                    _br_len = max(float(_br.get("bridge_length_m", 0.0)), 1.0)
                    _pier_w = max(float(_br.get("total_pier_width_m", 0.0)), 0.0)
                    _pier_k = float(_br.get("pier_loss_coef", 0.0))
                    _cc = float(_br.get("contraction_coef", 0.3))
                    _ec = float(_br.get("expansion_coef", 0.5))
                    h_br = max(W_trial - bed[i], 0.01)
                    A_br, _P_br, _R_br, _T_br = self._get_geometry(h_br, i)
                    A_pier_e = _pier_w * min(h_br, 30.0)
                    # 改进1：若有 bridge_opening_stations，用 NaturalSection 计算桥内有效过水面积
                    _op_sta = _br.get("bridge_opening_stations", [])
                    _op_elev = _br.get("bridge_opening_elevations", [])
                    if len(_op_sta) > 2 and len(_op_elev) == len(_op_sta):
                        from physics.cross_section import NaturalSection
                        _bridge_xs = NaturalSection(
                            "bridge_opening",
                            elevations=np.array(_op_elev, dtype=float),
                            distances=np.array(_op_sta, dtype=float),
                        )
                        # NaturalSection.compute_geometry 需要相对于最低点的水深
                        _wl_abs = bed[i] + h_br
                        _op_depth = max(_wl_abs - _bridge_xs.min_elevation, 0.0)
                        _bridge_geom = _bridge_xs.compute_geometry(_op_depth)
                        A_eff_e = max(_bridge_geom.area - A_pier_e, _bridge_geom.area * 0.3)
                    else:
                        A_deck_e = 0.0
                        wl_br = bed[i] + h_br
                        deck_e = float(_br.get("deck_elevation_m", 1e6))
                        if wl_br > deck_e and deck_e > bed[i]:
                            A_deck_e = (wl_br - deck_e) * _T_br
                        A_eff_e = max(A_br - A_pier_e - A_deck_e, A_br * 0.3)
                    V_eff_e = Q / max(A_eff_e, 1e-9)
                    vh_eff_e = V_eff_e ** 2 / (2.0 * self.g)
                    h_pier_e = _pier_k * vh_eff_e
                    R_eff_e = A_eff_e / max(_P_br, 1e-6)
                    n_br_e = self._manning_ns[i] if self._manning_ns and i < len(self._manning_ns) else self.n
                    Sf_br_e = (Q * n_br_e / (A_eff_e * R_eff_e ** (2.0/3.0))) ** 2 if A_eff_e > 0 and R_eff_e > 0 else 0
                    h_f_br_e = _br_len * Sf_br_e
                    vh_us_app = alpha_us * V_us ** 2 / (2.0 * self.g)
                    h_contr_e = _cc * max(vh_eff_e - vh_us_app, 0.0)
                    h_ds_app = max(W[i + 1] - bed[i + 1], 0.01)
                    A_ds_app, _, _, _ = self._get_geometry(h_ds_app, i + 1)
                    V_ds_app = Q / max(A_ds_app, 1e-9)
                    _, alpha_ds_app = self._compute_subdivided_conveyance(h_ds_app, i + 1)
                    vh_ds_app = alpha_ds_app * V_ds_app ** 2 / (2.0 * self.g)
                    h_exp_e = _ec * max(vh_eff_e - vh_ds_app, 0.0)
                    W_trial = W_trial + h_pier_e + h_f_br_e + h_contr_e + h_exp_e
                # Re-apply physical limit
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
