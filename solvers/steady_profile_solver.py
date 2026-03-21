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
        reach_lengths_lob=None,
        reach_lengths_rob=None,
        contraction_coefs=None,
        expansion_coefs=None,
        manning_n_lob=None,
        manning_n_rob=None,
        bank_stations=None,
        bridges=None,
        culverts=None,
        lateral_inflows=None,
        ice_thickness=None,
        n_ice=None,
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
            lateral_inflows: Per-XS lateral inflow array (m³/s). Positive = flow entering.
                When provided, Q at each XS = Q_upstream + cumulative lateral inflows.
                Length must match cross_sections. None = uniform Q throughout.
            ice_thickness: Per-XS 冰盖厚度 (m)，<=0 视为无冰盖
            n_ice: Per-XS 冰底曼宁糙率，<=0 时回退为渠床糙率
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
        self._reach_lengths_lob = reach_lengths_lob  # HEC-RAS Len Left
        self._reach_lengths_rob = reach_lengths_rob  # HEC-RAS Len Right
        self._contraction_coefs = contraction_coefs
        self._expansion_coefs = expansion_coefs
        self._manning_n_lob = manning_n_lob
        self._manning_n_rob = manning_n_rob
        self._bank_stations = bank_stations
        self._bridges = bridges  # list[dict] with bridge physical parameters
        self._culverts = culverts  # list[dict] with culvert parameters from HDF adapter
        self._lateral_inflows = lateral_inflows  # 逐断面区间来水 (m³/s)
        self._ice_thickness = ice_thickness
        self._n_ice = n_ice
        self._manning_n_segments = None  # 每断面完整 n 分段: list[list[(station, n)]]
        self._ineffective_areas = None  # 每断面无效流动区: list[list[{sta_l, sta_r, elev}]]

    # Hydraulic geometry helpers

    def _get_station_ice_params(self, station_index=None) -> Tuple[float, float]:
        """获取断面冰盖厚度与冰底糙率。"""
        idx = 0 if station_index is None else int(station_index)
        ice_t = 0.0
        n_ice = self.n

        if self._ice_thickness is not None and idx < len(self._ice_thickness):
            v = self._ice_thickness[idx]
            if v is not None and float(v) > 0.0:
                ice_t = float(v)
        if self._n_ice is not None and idx < len(self._n_ice):
            v = self._n_ice[idx]
            if v is not None and float(v) > 0.0:
                n_ice = float(v)
        return ice_t, n_ice

    @staticmethod
    def _compute_sabaneev_nc(n_bed: float, n_ice: float, P_bed: float, P_ice: float) -> float:
        """Sabaneev 复合糙率公式。"""
        denom = max(P_bed + P_ice, 1e-9)
        numer = n_bed ** 1.5 * P_bed + n_ice ** 1.5 * P_ice
        return float(max((numer / denom) ** (2.0 / 3.0), 1e-6))

    def _get_raw_geometry(self, h: float, station_index=None) -> Tuple[float, float, float, float]:
        """返回未考虑冰盖修正的 (A, P, R, T)。"""
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

    def _get_geometry(self, h: float, station_index=None) -> Tuple[float, float, float, float]:
        """Return (A, P, R, T) at water depth h."""
        A, P_bed, _R, T = self._get_raw_geometry(h, station_index)
        ice_t, _n_ice = self._get_station_ice_params(station_index)
        if ice_t > 0.0 and T > 0.0:
            # 冰盖修正：有效过水面积扣除冰层占据面积，湿周增加冰底接触周长
            A = max(A - ice_t * T, 1e-9)
            P = P_bed + T
        else:
            P = P_bed
        R = A / max(P, 1e-9)
        return float(A), float(P), float(R), float(T)

    def compute_friction_slope(self, h: float, Q: float, station_index=None) -> float:
        """Manning friction slope, per-station Manning n support."""
        n_local = self.n
        if station_index is not None and self._manning_ns and station_index < len(self._manning_ns):
            n_val = self._manning_ns[station_index]
            if n_val and float(n_val) > 0:
                n_local = float(n_val)
        ice_t, n_ice = self._get_station_ice_params(station_index)
        xs = self._xs
        if station_index is not None and self._xs_array and station_index < len(self._xs_array):
            xs = self._xs_array[station_index]
        if xs is not None and hasattr(xs, "compute_conveyance") and ice_t <= 0.0:
            K, _alpha = xs.compute_conveyance(h)
            if K > 0:
                return float((Q / K) ** 2)
        A, P, R, T = self._get_geometry(h, station_index)
        if ice_t > 0.0 and T > 0.0:
            P_bed = max(P - T, 1e-9)
            n_local = self._compute_sabaneev_nc(n_local, n_ice, P_bed, T)
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

    @staticmethod
    def _segment_area_perimeter(
        stations: np.ndarray, elevations: np.ndarray,
        water_level: float, sta_lo: float, sta_hi: float,
    ) -> Tuple[float, float]:
        """计算 [sta_lo, sta_hi] 区间在给定水位下的面积和湿周。

        湿周不包含区间两端的垂直面（HEC-RAS / Posey 1967 惯例）。
        """
        area = 0.0
        perimeter = 0.0
        for j in range(len(stations) - 1):
            s1, s2 = float(stations[j]), float(stations[j + 1])
            z1, z2 = float(elevations[j]), float(elevations[j + 1])
            if s2 <= sta_lo or s1 >= sta_hi:
                continue
            if s1 < sta_lo:
                frac = (sta_lo - s1) / (s2 - s1)
                z1 = z1 + frac * (z2 - z1); s1 = sta_lo
            if s2 > sta_hi:
                frac = (sta_hi - s1) / (s2 - s1)
                z2 = z1 + frac * (z2 - z1); s2 = sta_hi
            ds = s2 - s1
            dz = z2 - z1
            if ds <= 0.0:
                # 垂直壁：ds=0 但 dz≠0，只贡献湿周不贡献面积
                # 但分区边界（sta_lo/sta_hi）处的垂直面不计入（Posey 惯例）
                if abs(dz) > 0.0 and abs(s1 - sta_lo) > 0.01 and abs(s1 - sta_hi) > 0.01:
                    z_lo = min(z1, z2)
                    z_hi = max(z1, z2)
                    if z_lo < water_level:
                        wet_height = min(water_level, z_hi) - z_lo
                        perimeter += wet_height
                continue
            if z1 >= water_level and z2 >= water_level:
                continue
            elif z1 < water_level and z2 < water_level:
                area += 0.5 * (water_level - z1 + water_level - z2) * ds
                perimeter += np.sqrt(ds ** 2 + dz ** 2)
            elif z1 < water_level <= z2:
                fw = (water_level - z1) / (z2 - z1)
                dsw, dzw = ds * fw, dz * fw
                area += 0.5 * (water_level - z1) * dsw
                perimeter += np.sqrt(dsw ** 2 + dzw ** 2)
            else:
                fw = (water_level - z2) / (z1 - z2)
                dsw, dzw = ds * fw, dz * fw
                area += 0.5 * (water_level - z2) * dsw
                perimeter += np.sqrt(dsw ** 2 + dzw ** 2)
        return area, perimeter

    def _zone_conveyance(
        self,
        stations: np.ndarray,
        elevations: np.ndarray,
        water_level: float,
        sta_min: float,
        sta_max: float,
        n: float,
        n_segments: list | None = None,
        n_slices: int = 5,
    ) -> Tuple[float, float]:
        """HEC-RAS n-value break point 方法计算分区输水能力 K。

        当 n_segments 提供时，按 n 值变化点将分区切分为子区，
        每个子区独立计算 K_i = (1/n_i)*A_i*R_i^(2/3)，K_zone = ΣK_i。
        子区间的虚拟垂直分割面不计入湿周（Posey 1967 惯例）。

        Args:
            n: 单一 Manning n（n_segments 为 None 时使用）
            n_segments: [(station, n_value), ...] 按 station 排序的 n 值分段列表
        Returns:
            (K_zone, A_zone)
        """
        # 先计算整区面积
        A_total, P_total = self._segment_area_perimeter(
            stations, elevations, water_level, sta_min, sta_max)

        if A_total <= 0.0 or P_total <= 0.0:
            return 0.0, 0.0

        # 如果有分段 Manning n，按 n-value break points 细分
        if n_segments and len(n_segments) >= 2:
            # 筛选出落在 [sta_min, sta_max] 内的 n 分段
            breaks = []
            for sta, n_val in n_segments:
                sta_f = float(sta)
                n_f = float(n_val)
                if np.isnan(n_f) or n_f <= 0:
                    continue
                if sta_min <= sta_f <= sta_max:
                    breaks.append((sta_f, n_f))
            # 添加边界
            if not breaks or breaks[0][0] > sta_min + 0.01:
                # 用第一个有效 n 覆盖左边界
                first_n = n
                for _, nv in n_segments:
                    if not np.isnan(float(nv)) and float(nv) > 0:
                        first_n = float(nv)
                        break
                breaks.insert(0, (sta_min, first_n))
            if breaks[-1][0] < sta_max - 0.01:
                breaks.append((sta_max, breaks[-1][1]))

            if len(breaks) >= 2:
                K_zone = 0.0
                for idx in range(len(breaks) - 1):
                    seg_lo = breaks[idx][0]
                    seg_hi = breaks[idx + 1][0]
                    seg_n = breaks[idx][1]
                    if seg_hi - seg_lo < 1e-6 or seg_n <= 0:
                        continue
                    A_s, P_s = self._segment_area_perimeter(
                        stations, elevations, water_level, seg_lo, seg_hi)
                    if A_s > 0.0 and P_s > 0.0:
                        R_s = A_s / P_s
                        K_s = (1.0 / seg_n) * A_s * R_s ** (2.0 / 3.0)
                        K_zone += K_s

                if K_zone > 0.0:
                    return float(K_zone), float(A_total)

        # 单一 n 值：整区计算
        R = A_total / P_total
        K = (1.0 / max(n, 0.001)) * A_total * R ** (2.0 / 3.0)
        return float(K), float(A_total)

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
            A, P, R, T = self._get_geometry(h, station_index)
            n_local = _n_ch(station_index)
            ice_t, n_ice = self._get_station_ice_params(station_index)
            if ice_t > 0.0 and T > 0.0:
                P_bed = max(P - T, 1e-9)
                n_local = self._compute_sabaneev_nc(n_local, n_ice, P_bed, T)
            K = (1.0 / n_local) * A * max(R, 1e-9) ** (2.0 / 3.0)
            return float(K), 1.0

        # 有冰盖时采用整体断面复合糙率，避免分区 K 与冰底阻力耦合不一致
        ice_t, n_ice = self._get_station_ice_params(station_index)
        if ice_t > 0.0:
            A, P, R, T = self._get_geometry(h, station_index)
            n_local = _n_ch(station_index)
            if T > 0.0:
                P_bed = max(P - T, 1e-9)
                n_local = self._compute_sabaneev_nc(n_local, n_ice, P_bed, T)
            K = (1.0 / max(n_local, 0.001)) * A * max(R, 1e-9) ** (2.0 / 3.0)
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

        # 获取完整 Manning n 分段（如果有）用于 n-value break point 细分
        _n_segs = None
        if self._manning_n_segments and station_index < len(self._manning_n_segments):
            _n_segs = self._manning_n_segments[station_index]

        K_lob, A_lob = self._zone_conveyance(
            stations_arr, elevations_arr, water_level,
            sta_min=sta_min_all, sta_max=float(left_bank),
            n=_n_lob(station_index), n_segments=_n_segs,
        )
        K_ch, A_ch = self._zone_conveyance(
            stations_arr, elevations_arr, water_level,
            sta_min=float(left_bank), sta_max=float(right_bank),
            n=_n_ch(station_index), n_segments=_n_segs,
        )
        K_rob, A_rob = self._zone_conveyance(
            stations_arr, elevations_arr, water_level,
            sta_min=float(right_bank), sta_max=sta_max_all,
            n=_n_rob(station_index), n_segments=_n_segs,
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

    def _solve_culvert(
        self,
        Q: float,
        W_downstream: float,
        culvert_dict: dict,
        bed_us: float,
    ) -> float:
        """计算涵洞上游水面高程。

        使用 HDS-5 入口/出口控制方法，取控制水头较大者。
        涵洞参数从 HDF 适配器提取的 dict 获取。

        Args:
            Q: 流量 (m³/s)
            W_downstream: 下游水面高程 (m)
            culvert_dict: 涵洞参数字典
            bed_us: 上游断面床面高程 (m)
        Returns:
            W_upstream: 上游水面高程 (m)
        """
        from physics.structures.culvert import Culvert, CulvertGeometry

        # 提取参数
        shape = str(culvert_dict.get("shape", "circular"))
        diameter_m = float(culvert_dict.get("diameter_m", 0.0))
        height_m = float(culvert_dict.get("height_m", diameter_m))
        width_m = float(culvert_dict.get("width_m", diameter_m))
        length_m = float(culvert_dict.get("length_m", 30.0))
        us_invert = float(culvert_dict.get("us_invert_m", bed_us))
        ds_invert = float(culvert_dict.get("ds_invert_m", us_invert - 0.01))
        n_barrels = int(culvert_dict.get("n_barrels", 1))
        manning_n = float(culvert_dict.get("manning_n", 0.013))
        ke = float(culvert_dict.get("entrance_loss_coef", 0.5))

        slope = (us_invert - ds_invert) / max(length_m, 0.1)

        try:
            geom = CulvertGeometry(
                shape=shape, length=length_m, slope=max(slope, 1e-6),
                diameter=diameter_m if shape == "circular" else None,
                width=width_m if shape != "circular" else None,
                height=height_m if shape != "circular" else None,
                invert_elevation=us_invert,
                n_barrels=n_barrels,
            )
            culvert = Culvert(
                position=0.0, geometry=geom,
                manning_n=manning_n,
                entrance_loss_coef=ke,
            )

            # 上游可用水头 = W_upstream - us_invert（相对于涵洞入口底）
            # 下游水头 = W_downstream - ds_invert
            # 需要求解: 给定 Q，找 HW 使得 culvert 能通过 Q
            h_downstream = max(W_downstream - ds_invert, 0.0)

            # 用涵洞的 required_headwater 方法
            q_per_barrel = Q / max(n_barrels, 1)
            hw_inlet = culvert._required_headwater_inlet(q_per_barrel)
            hw_outlet = culvert._required_headwater_outlet(q_per_barrel, h_downstream)

            # 道路漫顶分流（roadway overtopping）
            road_elev = float(culvert_dict.get("road_elev_m", us_invert + height_m + 1.0))
            road_width = float(culvert_dict.get("road_width_m", 10.0))
            road_cd = float(culvert_dict.get("road_cd", 1.5))

            # 迭代求解：HW 使得 Q_culvert + Q_road = Q_total
            # 初始猜测用不含漫顶的 HW
            hw_required = max(hw_inlet, hw_outlet)

            for _cv_iter in range(20):
                W_trial = us_invert + hw_required
                # 道路漫顶流量
                h_over_road = max(W_trial - road_elev, 0.0)
                Q_road = road_cd * road_width * h_over_road ** 1.5 if h_over_road > 0 else 0.0
                Q_road = min(Q_road, 0.95 * Q)  # 限制不超过总流量95%
                Q_culvert = Q - Q_road

                if Q_culvert <= 0:
                    break

                # 用涵洞流量重新计算 HW
                q_pb = Q_culvert / max(n_barrels, 1)
                hw_in_new = culvert._required_headwater_inlet(q_pb)
                hw_out_new = culvert._required_headwater_outlet(q_pb, h_downstream)
                hw_new = max(hw_in_new, hw_out_new)

                if abs(hw_new - hw_required) < 0.001:
                    hw_required = hw_new
                    break
                hw_required = 0.5 * (hw_required + hw_new)  # 松弛

            W_upstream = us_invert + hw_required
            W_upstream = max(W_upstream, W_downstream + 0.001)

        except Exception:
            W_upstream = W_downstream + 0.1

        return float(W_upstream)

    def _split_deck_overtopping_flow(
        self,
        Q_total: float,
        WSE: float,
        deck_elev: float,
        weir_len: float,
        weir_coef: float = 1.70,
    ) -> tuple[float, float]:
        """桥面板溢顶堰流分流计算。

        当水面高程超过桥面板顶时，部分流量以堰流形式溢过桥面板，
        剩余流量通过桥下孔口。

        Returns
        -------
        (Q_weir, Q_under) : tuple[float, float]
        """
        if (Q_total <= 0.0 or weir_len <= 0.0
                or deck_elev >= 1e8 or WSE <= deck_elev):
            return 0.0, float(max(Q_total, 0.0))

        H = max(float(WSE) - float(deck_elev), 0.0)
        Q_weir = float(weir_coef) * float(weir_len) * H ** 1.5
        # 限制堰流不超过总流量的 95%，保证桥下至少有 5% 流量
        Q_weir = float(np.clip(Q_weir, 0.0, 0.95 * max(float(Q_total), 0.0)))
        Q_under = float(Q_total) - Q_weir
        return Q_weir, Q_under

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
        # TODO-B05: 当 HEC-RAS pier_loss_coef=0 时，桥墩拖曳系数也应为 0
        _pier_loss_coef = float(bridge.get("pier_loss_coef", 0.0))
        C_D = float(bridge.get("pier_cd", 2.0)) if _pier_loss_coef > 0.0 else 0.0
        deck_elev = float(bridge.get("deck_elevation_m", 1e9))
        pier_height = float(bridge.get("pier_height_m", 1e9))
        deck_weir_coef = float(bridge.get("deck_weir_coef", 1.70))
        deck_weir_len_cfg = float(bridge.get("deck_weir_length_m", 0.0))

        n_br = (
            self._manning_ns[us_xs_index]
            if self._manning_ns and us_xs_index < len(self._manning_ns)
            else self.n
        )

        h2 = max(W_downstream - bed_ds, 0.01)
        A2, P2_wet, _R2, T2 = self._get_geometry(h2, ds_xs_index)
        weir_len_ds = (
            deck_weir_len_cfg
            if deck_weir_len_cfg > 0.0
            else max(T2, 1e-6)
        )
        # 下游断面仅用于压顶面积判定，分流公式统一复用辅助函数。
        _Q_weir_ds, Q_under_ds = self._split_deck_overtopping_flow(
            Q_total=Q,
            WSE=W_downstream,
            deck_elev=deck_elev,
            weir_len=weir_len_ds,
            weir_coef=deck_weir_coef,
        )
        A_pier2 = pier_w_total * min(h2, pier_height)
        A2_eff = max(A2 - A_pier2, A2 * 0.3)
        # 壅水判断：使用 EGL (能量梯度线) 而非 WSE
        V2_temp = Q_under_ds / max(A2_eff, 1e-9)
        EGL2 = W_downstream + V2_temp ** 2 / (2.0 * self.g)
        if EGL2 > deck_elev > bed_ds:
            A2_eff = max(A2_eff - (W_downstream - deck_elev) * T2, A2 * 0.1)
        P2_force = self._hydrostatic_pressure_force(h2, ds_xs_index)

        S0_bridge = (bed_us - bed_ds) / max(L_bridge, 0.1)

        W3_trial = W_downstream + max(0.05, abs(bed_us - bed_ds) + 0.05)
        W3_trial = max(W3_trial, bed_us + 0.01)

        for _it in range(40):
            h3 = max(W3_trial - bed_us, 0.01)
            A3, P3_wet, _R3, T3 = self._get_geometry(h3, us_xs_index)
            weir_len = (
                deck_weir_len_cfg
                if deck_weir_len_cfg > 0.0
                else max(min(T2, T3), 1e-6)
            )
            # 桥面板溢顶后，桥孔内只使用桥下分配流量。
            Q_weir, Q_under = self._split_deck_overtopping_flow(
                Q_total=Q,
                WSE=W3_trial,
                deck_elev=deck_elev,
                weir_len=weir_len,
                weir_coef=deck_weir_coef,
            )
            A_pier3 = pier_w_total * min(h3, pier_height)
            A3_eff = max(A3 - A_pier3, A3 * 0.3)
            # 壅水判断：使用 EGL (能量梯度线) 而非 WSE
            V3_temp = Q_under / max(A3_eff, 1e-9)
            EGL3 = W3_trial + V3_temp ** 2 / (2.0 * self.g)
            if EGL3 > deck_elev > bed_us:
                A3_eff = max(A3_eff - (W3_trial - deck_elev) * T3, A3 * 0.1)
            V2 = Q_under / max(A2_eff, 1e-9)
            V3 = Q_under / max(A3_eff, 1e-9)
            P3_force = self._hydrostatic_pressure_force(h3, us_xs_index)

            A_avg = 0.5 * (A2_eff + A3_eff)
            P_wet_avg = 0.5 * (P2_wet + P3_wet)
            R_avg = A_avg / max(P_wet_avg, 1e-6)
            V_avg = Q_under / max(A_avg, 1e-9)
            Sf_avg = min((Q_under * n_br / max(A_avg * R_avg ** (2.0/3.0), 1e-9)) ** 2, 1.0)

            F_f = gamma * A_avg * Sf_avg * L_bridge
            A_pier_avg = 0.5 * (A_pier2 + A_pier3)
            F_pier = 0.5 * rho * C_D * A_pier_avg * V_avg ** 2
            W_x = gamma * A_avg * S0_bridge * L_bridge

            momentum_rhs = beta2 * rho * Q_under * V2 + P2_force + F_f + F_pier + W_x
            imbalance = (beta3 * rho * Q_under * V3 + P3_force) - momentum_rhs

            if abs(imbalance) < max(1.0, abs(momentum_rhs) * 1e-5):
                break

            dW = 1e-3
            W3p = W3_trial + dW
            h3p = max(W3p - bed_us, 0.01)
            A3p, _P3pw, _R3p, T3p = self._get_geometry(h3p, us_xs_index)
            weir_len_p = (
                deck_weir_len_cfg
                if deck_weir_len_cfg > 0.0
                else max(min(T2, T3p), 1e-6)
            )
            _Q_weir_p, Q_under_p = self._split_deck_overtopping_flow(
                Q_total=Q,
                WSE=W3p,
                deck_elev=deck_elev,
                weir_len=weir_len_p,
                weir_coef=deck_weir_coef,
            )
            A_pier3p = pier_w_total * min(h3p, pier_height)
            A3p_eff = max(A3p - A_pier3p, A3p * 0.3)
            # 壅水判断：使用 EGL (能量梯度线) 而非 WSE
            V3p_temp = Q_under_p / max(A3p_eff, 1e-9)
            EGL3p = W3p + V3p_temp ** 2 / (2.0 * self.g)
            if EGL3p > deck_elev > bed_us:
                A3p_eff = max(A3p_eff - (W3p - deck_elev) * T3p, A3p * 0.1)
            V2p = Q_under_p / max(A2_eff, 1e-9)
            V3p = Q_under_p / max(A3p_eff, 1e-9)
            P3p_force = self._hydrostatic_pressure_force(h3p, us_xs_index)
            A_avgp = 0.5 * (A2_eff + A3p_eff)
            P_wet_avgp = 0.5 * (P2_wet + _P3pw)
            R_avgp = A_avgp / max(P_wet_avgp, 1e-6)
            V_avgp = Q_under_p / max(A_avgp, 1e-9)
            Sf_avgp = min((Q_under_p * n_br / max(A_avgp * R_avgp ** (2.0/3.0), 1e-9)) ** 2, 1.0)

            F_fp = gamma * A_avgp * Sf_avgp * L_bridge
            A_pier_avgp = 0.5 * (A_pier2 + A_pier3p)
            F_pierp = 0.5 * rho * C_D * A_pier_avgp * V_avgp ** 2
            W_xp = gamma * A_avgp * S0_bridge * L_bridge

            momentum_rhs_p = beta2 * rho * Q_under_p * V2p + P2_force + F_fp + F_pierp + W_xp
            imbalance_p = (beta3 * rho * Q_under_p * V3p + P3p_force) - momentum_rhs_p
            d_imb_dW = (imbalance_p - imbalance) / dW

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
        deck_weir_coef = float(bridge.get("deck_weir_coef", 1.70))
        deck_weir_len_cfg = float(bridge.get("deck_weir_length_m", 0.0))
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

        def _eff_area(W_trial: float, xs_idx: int, bed_elev: float, Q_local: float = Q) -> tuple[float, float, float]:
            """Return (A_eff, P_wet, alpha) at WSE W_trial for given XS.
            Q_local: 实际过孔流量（溢顶时为 Q_under，非溢顶时为 Q）
            """
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
                V_temp = Q_local / max(A_temp, 1e-9)
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
        h2 = max(W_downstream - bed_ds, 0.01)
        _A2_raw, _P2_raw, _R2_raw, T2 = self._get_geometry(h2, ds_xs_index)
        weir_len_ds = (
            deck_weir_len_cfg
            if deck_weir_len_cfg > 0.0
            else max(T2, 1e-6)
        )
        # 下游断面只用于预估压顶影响，分流公式统一复用辅助函数。
        _Q_weir_ds, Q_under_ds_en = self._split_deck_overtopping_flow(
            Q_total=Q,
            WSE=W_downstream,
            deck_elev=deck_elev,
            weir_len=weir_len_ds,
            weir_coef=deck_weir_coef,
        )
        A2_eff, P2_wet, alpha2 = _eff_area(W_downstream, ds_xs_index, bed_ds, Q_under_ds_en)

        # ── Newton-Raphson 求解 Section 3（上游桥面）WSE ─────────────────────
        # 初始猜测：W_3 ≥ W_2，从下游值开始
        W3_trial = max(W_downstream, bed_us + 0.01)
        W3_trial = max(W3_trial, bed_us + max(W_downstream - bed_ds, 0.01))

        for _it in range(40):
            h3 = max(W3_trial - bed_us, 0.01)
            _A3_raw, _P3_raw, _R3_raw, T3 = self._get_geometry(h3, us_xs_index)
            weir_len = (
                deck_weir_len_cfg
                if deck_weir_len_cfg > 0.0
                else max(min(T2, T3), 1e-6)
            )
            # 速度水头和摩阻损失只使用桥下分配流量。
            Q_weir, Q_under = self._split_deck_overtopping_flow(
                Q_total=Q,
                WSE=W3_trial,
                deck_elev=deck_elev,
                weir_len=weir_len,
                weir_coef=deck_weir_coef,
            )

            V2 = Q_under / max(A2_eff, 1e-9)
            E2 = W_downstream + alpha2 * V2 ** 2 / (2.0 * self.g)
            A3_eff, P3_wet, alpha3 = _eff_area(W3_trial, us_xs_index, bed_us, Q_under)
            V3 = Q_under / max(A3_eff, 1e-9)
            vh3 = alpha3 * V3 ** 2 / (2.0 * self.g)

            # 摩擦损失（Manning 平均）
            A_avg = 0.5 * (A2_eff + A3_eff)
            P_avg = 0.5 * (P2_wet + P3_wet)
            R_avg = A_avg / max(P_avg, 1e-6)
            Sf_avg = min((Q_under * n_br / max(A_avg * R_avg ** (2.0 / 3.0), 1e-9)) ** 2, 1.0)
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
            W3p = W3_trial + dW
            h3p = max(W3p - bed_us, 0.01)
            _A3p_raw, _P3p_raw, _R3p_raw, T3p = self._get_geometry(h3p, us_xs_index)
            weir_len_p = (
                deck_weir_len_cfg
                if deck_weir_len_cfg > 0.0
                else max(min(T2, T3p), 1e-6)
            )
            _Q_weir_p, Q_under_p = self._split_deck_overtopping_flow(
                Q_total=Q,
                WSE=W3p,
                deck_elev=deck_elev,
                weir_len=weir_len_p,
                weir_coef=deck_weir_coef,
            )
            V2p = Q_under_p / max(A2_eff, 1e-9)
            E2p = W_downstream + alpha2 * V2p ** 2 / (2.0 * self.g)
            A3p, P3p, alpha3p = _eff_area(W3p, us_xs_index, bed_us, Q_under_p)
            V3p = Q_under_p / max(A3p, 1e-9)
            vh3p = alpha3p * V3p ** 2 / (2.0 * self.g)
            A_avgp = 0.5 * (A2_eff + A3p)
            P_avgp = 0.5 * (P2_wet + P3p)
            R_avgp = A_avgp / max(P_avgp, 1e-6)
            Sf_avgp = min((Q_under_p * n_br / max(A_avgp * R_avgp ** (2.0 / 3.0), 1e-9)) ** 2, 1.0)
            h_fp = L_bridge * Sf_avgp
            h_pierp = pier_k * vh3p
            vh2p = alpha2 * V2p ** 2 / (2.0 * self.g)
            h_contrp = cc * max(vh3p - vh2p, 0.0)
            f_valp = E2p - (W3p + vh3p + h_fp + h_pierp + h_contrp)

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

        # 逐断面流量数组：支持区间来水（lateral inflows）
        # 断面排列：index 0 = 最上游，index n_xs-1 = 最下游
        # 亚临界回水从下游向上游推进，流量随上游递减
        Q_arr = np.full(n_xs, Q, dtype=float)
        if self._lateral_inflows is not None:
            lat = np.asarray(self._lateral_inflows, dtype=float)
            if len(lat) >= n_xs:
                # lateral_inflows[i] = 从 XS[i] 到 XS[i+1] 之间汇入的流量
                # Q_arr[0] = Q (上游给定流量)
                # Q_arr[i] = Q + sum(lateral_inflows[0:i])
                for k in range(1, n_xs):
                    Q_arr[k] = Q_arr[k - 1] + lat[k - 1]

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

        # --- Culvert index resolution ------------------------------------------
        _culvert_at_us: dict[int, dict] = {}  # us_xs_index -> culvert dict
        if self._culverts:
            for _cv in self._culverts:
                if "us_xs_index" in _cv:
                    _culvert_at_us[int(_cv["us_xs_index"])] = _cv
                elif hasattr(self, "_xs_station_labels") and self._xs_station_labels:
                    _us_rs = str(_cv.get("us_rs", "")).strip()
                    _us_idx = next((j for j, lbl in enumerate(self._xs_station_labels)
                                    if str(lbl).strip() == _us_rs), None)
                    if _us_idx is not None:
                        _cv_copy = dict(_cv)
                        _cv_copy["us_xs_index"] = _us_idx
                        _culvert_at_us[_us_idx] = _cv_copy
        # -----------------------------------------------------------------------
        for i in range(n_xs - 2, -1, -1):
            # 逐断面流量：支持区间来水（HEC-RAS Change in Discharge）
            # 下游断面 i+1 的流量（回水从下游向上游推进）
            Q_ds_local = float(Q_arr[i + 1])
            # 上游断面 i 的流量
            Q_us_local = float(Q_arr[i])
            # 本段使用的平均流量（HEC-RAS 在标准步中使用下游断面流量）
            Q_seg = Q_ds_local

            # HEC-RAS 加权平均 reach length: L = (K_LOB*L_LOB + K_Ch*L_Ch + K_ROB*L_ROB) / K_total
            dx_ch = float(abs(x[i + 1] - x[i]))
            if dx_ch < 1e-6:
                dx_ch = 1.0
            dx_lob = dx_ch  # 默认与主槽相同
            dx_rob = dx_ch
            if self._reach_lengths_lob and i < len(self._reach_lengths_lob):
                dx_lob = max(float(self._reach_lengths_lob[i]), 0.1)
            if self._reach_lengths_rob and i < len(self._reach_lengths_rob):
                dx_rob = max(float(self._reach_lengths_rob[i]), 0.1)

            h_ds = max(W[i + 1] - bed[i + 1], 0.01)
            A_ds, _P_ds, _R_ds, _T_ds = self._get_geometry(h_ds, i + 1)
            V_ds = Q_ds_local / max(A_ds, 1e-9)
            # 三区分区输水计算 (HEC-RAS LOB/Channel/ROB)
            K_ds, alpha_ds = self._compute_subdivided_conveyance(h_ds, i + 1)
            Sf_ds = (Q_ds_local / K_ds) ** 2 if K_ds > 0 else self.compute_friction_slope(h_ds, Q_ds_local, i + 1)

            # 计算下游分区 K 用于加权 reach length
            _K_ds_lob, _K_ds_ch, _K_ds_rob = 0.0, K_ds, 0.0
            if hasattr(self, '_bank_stations') and self._bank_stations and i + 1 < len(self._bank_stations or []):
                xs_ds = self._xs_array[i + 1] if self._xs_array and i + 1 < len(self._xs_array) else None
                if xs_ds is not None and hasattr(xs_ds, 'distances'):
                    _lb, _rb = self._bank_stations[i + 1]
                    _sta = np.asarray(xs_ds.distances)
                    _ele = np.asarray(xs_ds.elevations)
                    _wl = float(xs_ds.min_elevation) + h_ds
                    _n_l = self._manning_n_lob[i+1] if self._manning_n_lob and i+1 < len(self._manning_n_lob) else self.n
                    _n_c = self._manning_ns[i+1] if self._manning_ns and i+1 < len(self._manning_ns) else self.n
                    _n_r = self._manning_n_rob[i+1] if self._manning_n_rob and i+1 < len(self._manning_n_rob) else self.n
                    _K_ds_lob, _ = self._zone_conveyance(_sta, _ele, _wl, float(np.min(_sta)), float(_lb), _n_l)
                    _K_ds_ch, _ = self._zone_conveyance(_sta, _ele, _wl, float(_lb), float(_rb), _n_c)
                    _K_ds_rob, _ = self._zone_conveyance(_sta, _ele, _wl, float(_rb), float(np.max(_sta)), _n_r)

            # 加权平均 reach length
            _K_sum = _K_ds_lob + _K_ds_ch + _K_ds_rob
            if _K_sum > 0:
                dx_seg = (_K_ds_lob * dx_lob + _K_ds_ch * dx_ch + _K_ds_rob * dx_rob) / _K_sum
            else:
                dx_seg = dx_ch
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
            # 重要：在子步内使用上游断面的流量（区间来水已累加）
            Q = Q_us_local  # 覆盖外层参数 Q，让闭包和 Picard 都使用正确流量
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
                # 上游面位置权重：当前子步上游侧位置 = (_sub+1)/n_substeps
                frac_us = (_sub + 1) / n_substeps  # 上游侧靠近 xs[i] 的权重
                w_i_us   = frac_us
                w_ip1_us = 1.0 - frac_us
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
                # 改进初始猜测：使用能量方程的粗略估计，而非简单的床面跟随
                # 先用能量方程估算一个合理的初值
                _bed_rise = max(bed_sub_us - bed_sub_ds, 0.0)
                _Sf_est = _Sf_ds_sub  # 用下游摩阻坡度估算
                _dE_est = dx_sub * _Sf_est  # 能量损失估计
                # 初值：下游水位 + 床面抬升 + 能量损失
                W_trial = W_sub_ds + _bed_rise + _dE_est
                # 但不能过高（限制在下游水深的 2 倍以内）
                W_trial = min(W_trial, W_sub_ds + 2.0 * _h_ds_sub)
                # 也不能低于床面
                W_trial = max(W_trial, bed_sub_us + 0.01)

                # === brentq 求根（主路径）：K-h 高度非线性时比 Picard 稳健 ===
                # 能量方程残差：residual(W_us) = (W_us + alpha_us*V_us^2/2g) - (W_ds + alpha_ds*V_ds^2/2g) - h_f - h_e
                def _energy_residual(W_us_val: float) -> float:
                    h_us_r = max(W_us_val - bed_sub_us, 0.01)
                    h_us_r = min(h_us_r, 100.0)
                    # 上游面几何：按子步位置在 xs[i+1] 和 xs[i] 之间插值
                    _A_us_ip1 = self._get_geometry(h_us_r, i + 1)[0]
                    _A_us_i   = self._get_geometry(h_us_r, i)[0]
                    A_us_r = max(w_ip1_us * _A_us_ip1 + w_i_us * _A_us_i, 1e-9)
                    V_us_r = Q / max(A_us_r, 1e-9)
                    # 上游面输水率：插值
                    _K_us_ip1, _alpha_us_ip1 = self._compute_subdivided_conveyance(h_us_r, i + 1)
                    _K_us_i,   _alpha_us_i   = self._compute_subdivided_conveyance(h_us_r, i)
                    K_us_r     = max(w_ip1_us * _K_us_ip1 + w_i_us * _K_us_i, 1e-9)
                    alpha_us_r = w_ip1_us * _alpha_us_ip1 + w_i_us * _alpha_us_i
                    Sf_us_r = (Q / K_us_r) ** 2 if K_us_r > 0 else self.compute_friction_slope(h_us_r, Q, i)
                    vh_us_r = alpha_us_r * V_us_r ** 2 / (2.0 * self.g)
                    # HEC-RAS 默认: Average Conveyance Equation
                    # Sf_avg = ((Q_us + Q_ds) / (K_us + K_ds))^2
                    Sf_avg_r = min(((Q + Q) / max(K_us_r + _K_ds_sub, 1e-9)) ** 2, 1.0)
                    cc_r = self._contraction_coefs[i] if self._contraction_coefs and i < len(self._contraction_coefs) else contraction_coef
                    ec_r = self._expansion_coefs[i]   if self._expansion_coefs   and i < len(self._expansion_coefs)   else expansion_coef
                    h_f_r = dx_sub * Sf_avg_r
                    h_e_r = cc_r * (vh_us_r - _vh_ds_sub) if vh_us_r > _vh_ds_sub else ec_r * (_vh_ds_sub - vh_us_r)
                    # 残差 = 上游总能量头 - 下游总能量头 - 摩擦损失 - 局部损失
                    return (W_us_val + vh_us_r) - (W_sub_ds + _vh_ds_sub) - h_f_r - h_e_r

                _brentq_ok = False
                # --- brentq 区间策略 ---
                # 亚临界流：残差函数在高水位区有唯一根；超临界流：低水位区也有根。
                # 策略1（优先）：以 W_sub_ds 为下界的区间 [W_ds, W_ds+20]，仅包含亚临界根。
                # 策略2（降级）：扩展下界至 bed+0.001，全范围搜索（可能包含超临界根）。
                # 亚临界流：上游水位总在下游水位之上，以 W_sub_ds 为下界可避免超临界根
                # 亚临界下界：取下游水位与临界水位中的较大者
                # 这确保在陡坡段不会收敛到超临界根
                _y_c_us = self._compute_critical_depth(Q, i)
                _W_critical_us = bed_sub_us + _y_c_us
                _W_lo_narrow = max(W_sub_ds, _W_critical_us)  # 跳过超临界段
                _W_hi = W_sub_ds + 20.0
                try:
                    f_narrow_lo = _energy_residual(_W_lo_narrow)
                    f_hi = _energy_residual(_W_hi)
                    if np.isfinite(f_narrow_lo) and np.isfinite(f_hi) and f_narrow_lo * f_hi <= 0.0:
                        # 窄区间有根（亚临界根），直接求解
                        W_new = brentq(_energy_residual, _W_lo_narrow, _W_hi, xtol=1e-6, maxiter=100)
                        W_new = max(W_new, bed_sub_us + 1e-4)
                        W_trial = W_new
                        _converged = True
                        _brentq_ok = True
                    else:
                        # 窄区间无根，扩展到全范围 [bed+0.001, W_ds+50]，寻找任意根
                        _W_lo_wide = bed_sub_us + 0.001
                        f_wide_lo = _energy_residual(_W_lo_wide)
                        _W_hi_wide = W_sub_ds + 50.0
                        f_hi_wide = _energy_residual(_W_hi_wide)
                        if np.isfinite(f_wide_lo) and np.isfinite(f_hi_wide) and f_wide_lo * f_hi_wide <= 0.0:
                            W_new = brentq(_energy_residual, _W_lo_wide, _W_hi_wide, xtol=1e-6, maxiter=100)
                            W_new = max(W_new, bed_sub_us + 1e-4)
                            W_trial = W_new
                            _converged = True
                            _brentq_ok = True
                except Exception:
                    # brentq 异常（极端边界条件），回退到 Picard
                        _brentq_ok = False

                # === Picard 迭代（回退路径）：brentq 找不到变号区间时使用 ===
                if not _brentq_ok:
                    W_trial_prev = W_trial - 1.0  # 前一步，用于震荡检测
                    W_new = W_trial
                    relax = 1.0  # 松弛因子，震荡时递减
                    _converged = False
                    for _iter in range(80):
                        h_us = max(W_trial - bed_sub_us, 0.01)
                        h_us = min(h_us, 100.0)
                        A_us, _P_us, _R_us, _T_us = self._get_geometry(h_us, i)
                        V_us = Q / max(A_us, 1e-9)
                        K_us, alpha_us = self._compute_subdivided_conveyance(h_us, i)
                        Sf_us = (Q / K_us) ** 2 if K_us > 0 else self.compute_friction_slope(h_us, Q, i)
                        vh_us = alpha_us * V_us ** 2 / (2.0 * self.g)
                        # HEC-RAS 默认: Average Conveyance Equation
                        Sf_avg = min(((Q + Q) / max(K_us + _K_ds_sub, 1e-9)) ** 2, 1.0)
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
                        W_new = max(W_new, bed_sub_us + 1e-4)
                        _delta = abs(W_new - W_trial)
                        if _delta < 1e-4 or _delta / max(abs(W_trial), 1.0) < 1e-4:
                            W_trial = W_new
                            _converged = True
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
            # --- Culvert (HDS-5) ------------------------------------------------
            if i in _culvert_at_us:
                _cv = _culvert_at_us[i]
                W_trial = self._solve_culvert(
                    Q=Q, W_downstream=W[i + 1],
                    culvert_dict=_cv, bed_us=bed[i])
                W_trial = max(W_trial, bed[i] + 1e-4)
                W_trial = min(W_trial, _W_MAX)
            # --------------------------------------------------------------------
            W[i] = W_trial
            h[i] = max(W[i] - bed[i], 0.001)

        # ---- Mixed Flow Detection (HEC-RAS Mixed Flow Mode) -------------------
        # 计算 Froude 数（基于标准步初始解）
        froude_arr = np.zeros(n_xs)
        for _mf_i in range(n_xs):
            _mf_h = max(W[_mf_i] - bed[_mf_i], 0.01)
            _mf_A, _mf_P, _mf_R, _mf_T = self._get_geometry(_mf_h, _mf_i)
            _mf_V = Q / max(_mf_A, 1e-9)
            _mf_D = _mf_A / max(_mf_T, 1e-9)
            froude_arr[_mf_i] = _mf_V / np.sqrt(self.g * max(_mf_D, 1e-9))

        # 检测 1: 基于 Froude 数的超临界流判断
        # 注意：标准步初始解可能在宽浅复合断面发散，导致 Fr 虚高（误报）
        # 因此仅在 Froude 数足够高（> 2.0）且连续多个断面时才触发
        # 避免因求解发散引起的误触发（Critical Creek 类型断面）
        _froude_flag = False
        _consecutive_super = 0
        _min_consecutive_super = 3  # 需要连续 >= 3 个断面
        for _mf_i in range(n_xs):
            if froude_arr[_mf_i] > 2.0:  # 安全系数 2x，避免略超 1.0 的数值误差
                _consecutive_super += 1
                if _consecutive_super >= _min_consecutive_super:
                    _froude_flag = True
                    break
            else:
                _consecutive_super = 0

        # 检测 2: 陡坡段（需要连续 >= 2 个断面 S0 > 1.5*Sc，避免天然河道局部波动误触发）
        _steep_flag = False
        _consecutive_steep = 0
        _min_consecutive = 2  # 至少连续2个断面才判定为陡坡段
        for _mf_i in range(n_xs - 1):
            _dx = float(abs(x[_mf_i + 1] - x[_mf_i]))
            if _dx < 1e-6:
                continue
            _S0_local = float((bed[_mf_i] - bed[_mf_i + 1]) / _dx)
            _Sc_local = self._compute_critical_slope(Q, _mf_i)
            if _S0_local > 1.5 * _Sc_local:  # 加 1.5x 安全系数
                _consecutive_steep += 1
                if _consecutive_steep >= _min_consecutive:
                    _steep_flag = True
                    break
            else:
                _consecutive_steep = 0

        _mixed_flow_flag = _froude_flag or _steep_flag
        if _mixed_flow_flag:
            W, h = self._solve_mixed_flow(Q, W, bed, n_xs, x,
                                          contraction_coef, expansion_coef)
        return {"x": x, "h": h, "W": W, "Q": Q_arr, "bed": bed,
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


    def _compute_critical_slope(self, Q: float, station_index: int) -> float:
        """计算临界坡度 Sc，当 S0 > Sc 时该断面更可能出现超临界流。

        公式:
            Sc = n^2 * Q^2 / (A^2 * R^(4/3))
        其中 A, R 在临界深度处计算。
        """
        y_c = self._compute_critical_depth(Q, station_index)
        A, _P, R, _T = self._get_geometry(y_c, station_index)

        n_local = self.n
        if self._manning_ns and station_index < len(self._manning_ns):
            n_val = self._manning_ns[station_index]
            if n_val and float(n_val) > 0:
                n_local = float(n_val)

        if A > 0.0 and R > 0.0:
            Sc = (n_local * Q / A) ** 2 / (R ** (4.0 / 3.0))
        else:
            Sc = 0.001  # fallback default

        return float(Sc)

    def _identify_steep_sections(self, Q: float, bed: np.ndarray, x: np.ndarray) -> List[int]:
        """基于局部床坡与临界坡对比，识别陡坡段起始断面。

        Returns:
            List[int]: 每个陡坡段入口索引（上游到下游顺序）。
        """
        n_xs = len(bed)
        controls: List[int] = []

        if n_xs < 2:
            return controls

        steep_flags = np.zeros(n_xs - 1, dtype=bool)

        for i in range(n_xs - 1):
            dx = float(abs(x[i + 1] - x[i]))
            if dx < 1e-6:
                continue
            S0_local = float((bed[i] - bed[i + 1]) / dx)
            Sc_local = self._compute_critical_slope(Q, i)
            steep_flags[i] = bool(S0_local > Sc_local)

        for i in range(n_xs - 1):
            if not steep_flags[i]:
                continue
            if i == 0 or (not steep_flags[i - 1]):
                controls.append(i)

        return controls


    def _compute_momentum_function(self, h: float, Q: float, station_index: int) -> float:
        r"""Compute momentum function M = Q^2/(gA) + A*y_bar.

        Notes:
            Uses y_bar = A / T (as requested in task spec).
        """
        h_safe = max(float(h), 1e-6)
        A, _P, _R, T = self._get_geometry(h_safe, station_index)
        A = max(A, 1e-9)
        T = max(T, 1e-9)
        y_bar = A / T
        return float(Q ** 2 / (self.g * A) + A * y_bar)

    def _locate_control_sections(
        self,
        W_subcritical: np.ndarray,
        bed: np.ndarray,
        y_c: np.ndarray,
        Q: float,
        x: np.ndarray,
    ) -> List[int]:
        r"""定位 Split-Flow 控制断面（优先坡度法，回退水深法）。

        优先:
            基于 S0_local > Sc 的陡坡段入口识别控制断面。
        回退:
            若未识别到陡坡，则使用 h_sub < y_c 的旧逻辑。
        """
        controls = self._identify_steep_sections(Q, bed, x)

        if controls:
            return controls

        # fallback: legacy depth-based detection
        h_sub = np.asarray(W_subcritical, dtype=float) - np.asarray(bed, dtype=float)
        h_sub = np.maximum(h_sub, 0.0)
        y_c_arr = np.asarray(y_c, dtype=float)

        is_below_critical = h_sub < y_c_arr
        for i in range(len(is_below_critical)):
            if not is_below_critical[i]:
                continue
            if i == 0 or (not is_below_critical[i - 1]):
                controls.append(i)

        return controls


    def _compute_supercritical_profile(
        self,
        Q: float,
        control_idx: int,
        W_control: float,
        bed: np.ndarray,
        x: np.ndarray,
        y_c: np.ndarray,
        contraction_coef: float = 0.1,
        expansion_coef: float = 0.3,
        end_idx: Optional[int] = None,
    ) -> np.ndarray:
        r"""Compute supercritical profile from control section to downstream.

        Direction:
            upstream -> downstream (opposite of subcritical marching).
        Boundary at control:
            W(control_idx) fixed to critical WSE.
        """
        n_xs = len(bed)
        if end_idx is None:
            end_idx = n_xs - 1
        end_idx = int(np.clip(end_idx, control_idx, n_xs - 1))

        W_super = np.full(n_xs, np.nan, dtype=float)
        # 超临界流边界条件：用正常深度 y_n（不是临界深度 y_c）
        # 在陡坡段，均匀流水深 y_n < y_c，S2 型水面线趋近 y_n
        yc0 = max(float(y_c[control_idx]), 1e-4)
        # 计算控制断面处的正常深度
        if control_idx < n_xs - 1:
            dx_ctrl = float(abs(x[control_idx + 1] - x[control_idx]))
            S0_ctrl = (bed[control_idx] - bed[control_idx + 1]) / max(dx_ctrl, 0.1)
        else:
            S0_ctrl = 0.01
        if S0_ctrl > 1e-6:
            n_local = self.n
            if self._manning_ns and control_idx < len(self._manning_ns):
                nv = self._manning_ns[control_idx]
                if nv and float(nv) > 0:
                    n_local = float(nv)
            # 用 brentq 求正常深度
            def _yn_residual(y):
                A, _P, R, _T = self._get_geometry(y, control_idx)
                if A <= 0 or R <= 0:
                    return -1.0
                return (1.0 / n_local) * A * R ** (2.0 / 3.0) * S0_ctrl ** 0.5 - Q
            try:
                y_n = brentq(_yn_residual, 0.001, yc0 * 2.0, xtol=1e-6, maxiter=100)
            except Exception:
                y_n = 0.95 * yc0  # fallback
        else:
            y_n = 0.95 * yc0
        W_super[control_idx] = float(bed[control_idx]) + min(y_n, 0.95 * yc0)
        W_super[control_idx] = max(W_super[control_idx], float(bed[control_idx]) + 1e-4)

        for i in range(control_idx + 1, end_idx + 1):
            dx_seg = float(abs(x[i] - x[i - 1]))
            if dx_seg < 1e-6:
                dx_seg = 1.0

            h_us = max(W_super[i - 1] - bed[i - 1], 0.001)
            A_us, _P_us, _R_us, _T_us = self._get_geometry(h_us, i - 1)
            V_us = Q / max(A_us, 1e-9)
            K_us, alpha_us = self._compute_subdivided_conveyance(h_us, i - 1)
            Sf_us = (Q / K_us) ** 2 if K_us > 0 else self.compute_friction_slope(h_us, Q, i - 1)
            vh_us = alpha_us * V_us ** 2 / (2.0 * self.g)

            # 超临界流能量方程: W_ds = W_us + vh_us - vh_ds - Sf*dx - h_minor
            # 用 brentq 求根代替 Picard 迭代（稳健性更好）
            def _super_residual(W_ds_val: float) -> float:
                h_d = max(W_ds_val - bed[i], 0.001)
                A_d, _, _, _ = self._get_geometry(h_d, i)
                V_d = Q / max(A_d, 1e-9)
                K_d, alpha_d = self._compute_subdivided_conveyance(h_d, i)
                Sf_d = (Q / K_d) ** 2 if K_d > 0 else Sf_us
                vh_d = alpha_d * V_d ** 2 / (2.0 * self.g)
                Sf_a = min(((Q + Q) / max(K_us + K_d, 1e-9)) ** 2, 1.0)
                _cc = self._contraction_coefs[i] if self._contraction_coefs and i < len(self._contraction_coefs) else contraction_coef
                _ec = self._expansion_coefs[i] if self._expansion_coefs and i < len(self._expansion_coefs) else expansion_coef
                h_m = _cc * (vh_d - vh_us) if vh_d > vh_us else _ec * (vh_us - vh_d)
                # 残差: W_ds + vh_ds - (W_us + vh_us - Sf*dx - h_minor) = 0
                return (W_ds_val + vh_d) - (W_super[i - 1] + vh_us) + dx_seg * Sf_a + h_m

            # 超临界根在 [bed+0.001, W_us] 范围（水面下降）
            _W_lo = bed[i] + 0.001
            _W_hi = W_super[i - 1] + 1.0  # 允许略高于上游（局部抬升）
            try:
                f_lo = _super_residual(_W_lo)
                f_hi = _super_residual(_W_hi)
                if np.isfinite(f_lo) and np.isfinite(f_hi) and f_lo * f_hi <= 0:
                    W_trial = brentq(_super_residual, _W_lo, _W_hi, xtol=1e-6, maxiter=100)
                else:
                    # 扩大搜索范围
                    _W_hi2 = W_super[i - 1] + 5.0
                    f_hi2 = _super_residual(_W_hi2)
                    if np.isfinite(f_lo) and np.isfinite(f_hi2) and f_lo * f_hi2 <= 0:
                        W_trial = brentq(_super_residual, _W_lo, _W_hi2, xtol=1e-6, maxiter=100)
                    else:
                        # Picard fallback
                        W_trial = max(W_super[i - 1] - dx_seg * Sf_us, bed[i] + 0.01)
            except Exception:
                W_trial = max(W_super[i - 1] - dx_seg * Sf_us, bed[i] + 0.01)

            W_trial = max(W_trial, bed[i] + 0.001)
            W_super[i] = W_trial

        return W_super

    def _locate_hydraulic_jump(
        self,
        W_sub: np.ndarray,
        W_super: np.ndarray,
        bed: np.ndarray,
        Q: float,
        start_idx: int = 0,
        end_idx: Optional[int] = None,
    ) -> Optional[int]:
        r"""Locate hydraulic jump using momentum-function matching.

        Jump criterion:
            M_sub - M_super changes sign (or reaches minimal absolute difference).
        """
        n_xs = len(bed)
        if end_idx is None:
            end_idx = n_xs - 1
        start_idx = int(np.clip(start_idx, 0, n_xs - 1))
        end_idx = int(np.clip(end_idx, start_idx, n_xs - 1))

        idx_valid: List[int] = []
        delta_m: List[float] = []

        for i in range(start_idx, end_idx + 1):
            if np.isnan(W_super[i]) or np.isnan(W_sub[i]):
                continue
            h_sub = max(W_sub[i] - bed[i], 0.001)
            h_sup = max(W_super[i] - bed[i], 0.001)
            M_sub = self._compute_momentum_function(h_sub, Q, i)
            M_sup = self._compute_momentum_function(h_sup, Q, i)
            idx_valid.append(i)
            delta_m.append(M_sub - M_sup)

        if len(idx_valid) < 2:
            return None

        for k in range(1, len(idx_valid)):
            d1 = delta_m[k - 1]
            d2 = delta_m[k]
            if d1 == 0.0:
                return idx_valid[k - 1]
            if d1 * d2 < 0.0:
                return idx_valid[k]

        k_min = int(np.argmin(np.abs(np.asarray(delta_m))))
        if np.isfinite(delta_m[k_min]):
            return idx_valid[k_min]

        return None

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
        r"""Split-Flow Method mixed-flow solver (HEC-RAS-style workflow).

        Workflow:
            1) Use given global subcritical profile W_subcritical
            2) Locate control section(s): first h<y_c entry of each interval
            3) Set critical depth at control section as supercritical boundary
            4) March supercritical profile downstream from control section
            5) Locate hydraulic jump by momentum-function matching
            6) Stitch supercritical (upstream of jump) + subcritical (downstream)
        """
        y_c = np.zeros(n_xs, dtype=float)
        for i in range(n_xs):
            y_c[i] = self._compute_critical_depth(Q, i)

        control_sections = self._locate_control_sections(W_subcritical, bed, y_c, Q, x)
        if not control_sections:
            h_final = np.maximum(W_subcritical - bed, 0.001)
            return W_subcritical, h_final

        # 亚临界剖面修正：找到陡→缓过渡点，从缓坡端用临界深度向上游重推回水线
        W_sub_corrected = np.array(W_subcritical, dtype=float)

        for c_idx, control_idx in enumerate(control_sections):
            seg_end = (control_sections[c_idx + 1] - 1) if (c_idx + 1 < len(control_sections)) else (n_xs - 1)
            seg_end = max(seg_end, control_idx)

            # 找到陡坡段末端（第一个 S0 < Sc 的断面）
            transition_idx = seg_end
            for ti in range(control_idx, seg_end + 1):
                if ti >= n_xs - 1:
                    break
                dx_t = float(abs(x[ti + 1] - x[ti]))
                if dx_t < 1e-6:
                    continue
                S0_t = (bed[ti] - bed[ti + 1]) / dx_t
                Sc_t = self._compute_critical_slope(Q, ti)
                if S0_t < Sc_t:
                    transition_idx = ti
                    break

            # 从过渡点用临界深度向上游重推
            W_bc = bed[transition_idx] + y_c[transition_idx]
            W_sub_corrected[transition_idx] = max(W_sub_corrected[transition_idx], W_bc)
            W_prev = W_bc
            for i in range(transition_idx - 1, control_idx - 1, -1):
                dx_i = float(abs(x[i + 1] - x[i]))
                if dx_i < 1e-6:
                    dx_i = 1.0
                h_prev = max(W_prev - bed[i + 1], 0.01)
                K_prev, _ = self._compute_subdivided_conveyance(h_prev, i + 1)
                Sf_prev = (Q / max(K_prev, 1e-9)) ** 2
                bed_rise = max(bed[i] - bed[i + 1], 0.0)
                W_us_est = W_prev + Sf_prev * dx_i + bed_rise
                W_us_est = max(W_us_est, bed[i] + y_c[i])
                W_sub_corrected[i] = W_us_est
                W_prev = W_us_est

        W_final = np.array(W_sub_corrected, dtype=float)

        for c_idx, control_idx in enumerate(control_sections):
            seg_end = (control_sections[c_idx + 1] - 1) if (c_idx + 1 < len(control_sections)) else (n_xs - 1)
            seg_end = max(seg_end, control_idx)

            W_control = bed[control_idx] + y_c[control_idx]

            W_super = self._compute_supercritical_profile(
                Q=Q,
                control_idx=control_idx,
                W_control=W_control,
                bed=bed,
                x=x,
                y_c=y_c,
                contraction_coef=contraction_coef,
                expansion_coef=expansion_coef,
                end_idx=seg_end,
            )

            jump_idx = self._locate_hydraulic_jump(
                W_sub=W_sub_corrected,
                W_super=W_super,
                bed=bed,
                Q=Q,
                start_idx=control_idx,
                end_idx=seg_end,
            )

            if jump_idx is None:
                for i in range(control_idx, seg_end + 1):
                    if not np.isnan(W_super[i]):
                        W_final[i] = W_super[i]
            else:
                for i in range(control_idx, jump_idx):
                    if not np.isnan(W_super[i]):
                        W_final[i] = W_super[i]

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
