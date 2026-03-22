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
        self._bank_stations = list(bank_stations) if bank_stations is not None else None
        self._channel_bank_stations = (
            [tuple(bs) if bs is not None else (None, None) for bs in self._bank_stations]
            if self._bank_stations is not None
            else None
        )
        self._bridges = bridges  # list[dict] with bridge physical parameters
        self._culverts = culverts  # list[dict] with culvert parameters from HDF adapter
        self._inline_structures = None  # list[dict] with inline structure params
        self._lateral_inflows = lateral_inflows  # 逐断面区间来水 (m³/s)
        self._ice_thickness = ice_thickness
        self._n_ice = n_ice
        self._manning_n_segments = None  # 每断面完整 n 分段: list[list[(station, n)]]
        self._ineffective_areas = None  # 每断面无效流动区: list[list[{sta_l, sta_r, elev}]]
        # Floodway Encroachment：记录每断面有效过水边界 (left_eff, right_eff)
        # _channel_bank_stations 为原始主槽岸线；_bank_stations 可同步为有效边界输出。
        self._effective_bank_stations = None
        # 最近一次标准步求解的绝对水位线（用于 encroachment 基准 WSE）
        self._last_wse_profile = None

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
        """Belokon-Sabaneev 复合糙率公式 (HEC-RAS TRM)。

        n_c = ((n_b^(3/2) + n_i^(3/2)) / 2)^(2/3)

        注意：HEC-RAS 使用简单平均（除以 2），不是 P 加权平均。
        P_bed 和 P_ice 参数保留用于向后兼容但不影响计算。
        """
        numer = n_bed ** 1.5 + n_ice ** 1.5
        return float(max((numer / 2.0) ** (2.0 / 3.0), 1e-6))

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
        # 非绝对高程模式下，用 z+h 近似记录 WSE，便于后续 encroachment 估计基准
        self._last_wse_profile = np.asarray(z + h, dtype=float).copy()
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

    def _resolve_effective_flow_limits(
        self,
        station_index: int,
        sta_min_all: float,
        sta_max_all: float,
        left_bank: float,
        right_bank: float,
        effective_limits: Optional[Tuple[float, float]] = None,
    ) -> Tuple[float, float]:
        """解析断面的有效过水边界（用于 Floodway Encroachment）。"""
        eff_pair = effective_limits
        if eff_pair is None and self._effective_bank_stations and station_index < len(self._effective_bank_stations):
            eff_pair = self._effective_bank_stations[station_index]

        # 默认：整个断面都可过水
        if eff_pair is None:
            return float(sta_min_all), float(sta_max_all)

        try:
            eff_left = float(eff_pair[0])
            eff_right = float(eff_pair[1])
        except Exception:
            return float(sta_min_all), float(sta_max_all)

        # 有效边界必须位于断面范围内，且不侵入主槽
        eff_left = min(max(eff_left, sta_min_all), float(left_bank))
        eff_right = max(min(eff_right, sta_max_all), float(right_bank))
        if eff_left >= eff_right - 1e-6:
            return float(sta_min_all), float(sta_max_all)
        return float(eff_left), float(eff_right)

    def _solve_depth_for_target_conveyance(
        self,
        target_K: float,
        station_index: int,
        effective_limits: Tuple[float, float],
        h_seed: float,
    ) -> float:
        """在给定有效过水边界下，求解满足 K(h)=target_K 的水深。"""
        target_K = float(target_K)
        if target_K <= 0.0:
            return max(float(h_seed), 1e-4)

        def _residual(h_val: float) -> float:
            h_safe = max(float(h_val), 1e-6)
            K_val, _ = self._compute_subdivided_conveyance(
                h_safe, station_index, effective_limits=effective_limits
            )
            return float(K_val - target_K)

        h_lo = max(1e-4, min(float(h_seed), 0.25 * float(h_seed) + 0.02))
        f_lo = _residual(h_lo)
        for _ in range(12):
            if not np.isfinite(f_lo):
                break
            if f_lo <= 0.0:
                break
            h_lo *= 0.5
            if h_lo < 1e-6:
                h_lo = 1e-6
                break
            f_lo = _residual(h_lo)

        h_hi = max(float(h_seed) + 0.5, float(h_seed) * 1.2 + 0.2)
        f_hi = _residual(h_hi)
        for _ in range(50):
            if np.isfinite(f_hi) and f_hi >= 0.0:
                break
            h_hi = h_hi * 1.35 + 0.3
            if h_hi > 300.0:
                return float("nan")
            f_hi = _residual(h_hi)

        if not np.isfinite(f_lo) or not np.isfinite(f_hi):
            return float("nan")
        if f_lo > 0.0 and f_hi > 0.0:
            return float("nan")
        if abs(f_lo) <= 1e-10:
            return float(h_lo)
        if abs(f_hi) <= 1e-10:
            return float(h_hi)

        try:
            return float(brentq(_residual, h_lo, h_hi, xtol=1e-6, maxiter=120))
        except Exception:
            return float("nan")

    def _apply_encroachment(self, surcharge_m: float, station_index: int) -> Tuple[float, float]:
        """按 Method 4（两侧等比例收缩）确定 Floodway Encroachment 边界。

        输入:
            surcharge_m: 目标壅高（m）
            station_index: 断面索引
        输出:
            (left_encroachment_station, right_encroachment_station)
        """
        if surcharge_m is None or float(surcharge_m) <= 0.0:
            if self._bank_stations and station_index < len(self._bank_stations):
                lb0, rb0 = self._bank_stations[station_index]
                return float(lb0), float(rb0)
            return (0.0, 0.0)

        xs = self._xs
        if self._xs_array and station_index < len(self._xs_array):
            xs = self._xs_array[station_index]
        if xs is None or not hasattr(xs, "distances") or not hasattr(xs, "elevations"):
            if self._bank_stations and station_index < len(self._bank_stations):
                lb0, rb0 = self._bank_stations[station_index]
                return float(lb0), float(rb0)
            return (0.0, 0.0)
        _banks_ref = self._channel_bank_stations if self._channel_bank_stations else self._bank_stations
        if not _banks_ref or station_index >= len(_banks_ref):
            return (0.0, 0.0)

        left_bank, right_bank = _banks_ref[station_index]
        if left_bank is None or right_bank is None:
            return (0.0, 0.0)
        left_bank = float(left_bank)
        right_bank = float(right_bank)
        if left_bank >= right_bank:
            return left_bank, right_bank

        stations_arr = np.asarray(xs.distances, dtype=float)
        elevations_arr = np.asarray(xs.elevations, dtype=float)
        sta_min_all = float(np.min(stations_arr))
        sta_max_all = float(np.max(stations_arr))

        # 没有滩地时无需 encroachment（主槽已覆盖全断面）
        if left_bank <= sta_min_all + 0.01 and right_bank >= sta_max_all - 0.01:
            return left_bank, right_bank

        # 基准 WSE：优先使用最近一次全河段求解结果；否则用岸顶高程近似估计
        if (
            self._last_wse_profile is not None
            and station_index < len(self._last_wse_profile)
            and np.isfinite(self._last_wse_profile[station_index])
        ):
            W_base = float(self._last_wse_profile[station_index])
        else:
            z_lb = float(np.interp(left_bank, stations_arr, elevations_arr))
            z_rb = float(np.interp(right_bank, stations_arr, elevations_arr))
            W_base = max(z_lb, z_rb) + max(float(surcharge_m) * 2.0, 0.5)

        min_elev = float(xs.min_elevation) if hasattr(xs, "min_elevation") else float(np.min(elevations_arr))
        h_base = max(W_base - min_elev, 0.05)

        # 基准输水能力：未侵占（全断面有效）状态
        K_base, _ = self._compute_subdivided_conveyance(
            h_base, station_index, effective_limits=(sta_min_all, sta_max_all)
        )
        if K_base <= 0.0:
            return left_bank, right_bank

        target_surcharge = float(max(surcharge_m, 0.0))
        p_prev = 0.0
        p_hit = None

        # 1) 从两侧漫滩向主槽逐步收缩有效过水宽度（等比例）
        for p in np.linspace(0.0, 1.0, 41):
            left_eff = sta_min_all + p * (left_bank - sta_min_all)
            right_eff = sta_max_all - p * (sta_max_all - right_bank)
            h_new = self._solve_depth_for_target_conveyance(
                target_K=K_base,
                station_index=station_index,
                effective_limits=(left_eff, right_eff),
                h_seed=h_base,
            )
            if not np.isfinite(h_new):
                continue
            W_new = min_elev + h_new
            rise = W_new - W_base
            # 2) 每步重算 K_total 与 WSE，直到达到目标壅高
            if rise >= target_surcharge:
                p_hit = p
                break
            p_prev = p

        if p_hit is None:
            # 未达到目标壅高：取最大可侵占（到主槽岸线）
            p_final = 1.0
        else:
            # 3) 二分细化停止点，逼近目标 surcharge
            p_lo, p_hi = p_prev, p_hit
            for _ in range(24):
                p_mid = 0.5 * (p_lo + p_hi)
                left_eff_m = sta_min_all + p_mid * (left_bank - sta_min_all)
                right_eff_m = sta_max_all - p_mid * (sta_max_all - right_bank)
                h_mid = self._solve_depth_for_target_conveyance(
                    target_K=K_base,
                    station_index=station_index,
                    effective_limits=(left_eff_m, right_eff_m),
                    h_seed=h_base,
                )
                if not np.isfinite(h_mid):
                    p_hi = p_mid
                    continue
                rise_mid = (min_elev + h_mid) - W_base
                if rise_mid >= target_surcharge:
                    p_hi = p_mid
                else:
                    p_lo = p_mid
            p_final = p_hi

        left_final = sta_min_all + p_final * (left_bank - sta_min_all)
        right_final = sta_max_all - p_final * (sta_max_all - right_bank)

        # 4) 记录 encroachment station（有效过水边界）
        n_xs_eff = len(self._xs_array) if self._xs_array else (len(self._bank_stations) if self._bank_stations else 0)
        if n_xs_eff <= 0:
            n_xs_eff = station_index + 1
        if self._effective_bank_stations is None or len(self._effective_bank_stations) < n_xs_eff:
            self._effective_bank_stations = [None] * n_xs_eff
        self._effective_bank_stations[station_index] = (float(left_final), float(right_final))
        # 兼容外部调用：同步更新“有效 bank_stations”输出容器
        if self._bank_stations is not None and station_index < len(self._bank_stations):
            self._bank_stations[station_index] = (float(left_final), float(right_final))

        return float(left_final), float(right_final)

    def _compute_subdivided_conveyance(
        self,
        h: float,
        station_index: int,
        effective_limits: Optional[Tuple[float, float]] = None,
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
            effective_limits: 可选有效过水边界 (left_eff, right_eff)，
                用于 Floodway Encroachment 试算；None 时使用已记录边界或全断面。

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

        _banks_ref = self._channel_bank_stations if self._channel_bank_stations else self._bank_stations
        if not _banks_ref or station_index >= len(_banks_ref):
            return _fallback()

        left_bank, right_bank = _banks_ref[station_index]
        if left_bank is None or right_bank is None or float(left_bank) >= float(right_bank):
            return _fallback()

        stations_arr = np.asarray(xs.distances, dtype=float)
        elevations_arr = np.asarray(xs.elevations, dtype=float)
        water_level = float(xs.min_elevation) + max(float(h), 1e-6)

        sta_min_all = float(np.min(stations_arr))
        sta_max_all = float(np.max(stations_arr))
        left_bank = float(left_bank)
        right_bank = float(right_bank)
        eff_left, eff_right = self._resolve_effective_flow_limits(
            station_index=station_index,
            sta_min_all=sta_min_all,
            sta_max_all=sta_max_all,
            left_bank=left_bank,
            right_bank=right_bank,
            effective_limits=effective_limits,
        )

        # If bank stations span the entire cross-section (no overbank),
        # fall back to single-zone to avoid numerical artifacts.
        if (
            left_bank <= sta_min_all + 0.01
            and right_bank >= sta_max_all - 0.01
            and eff_left <= sta_min_all + 0.01
            and eff_right >= sta_max_all - 0.01
        ):
            return _fallback()

        # 获取完整 Manning n 分段（如果有）用于 n-value break point 细分
        _n_segs = None
        if self._manning_n_segments and station_index < len(self._manning_n_segments):
            _n_segs = self._manning_n_segments[station_index]

        # Encroachment 生效时，仅在 [eff_left, eff_right] 范围内计算有效过水输水能力
        K_lob, A_lob = 0.0, 0.0
        if eff_left < left_bank - 1e-6:
            K_lob, A_lob = self._zone_conveyance(
                stations_arr, elevations_arr, water_level,
                sta_min=eff_left, sta_max=left_bank,
                n=_n_lob(station_index), n_segments=_n_segs,
            )
        K_ch, A_ch = self._zone_conveyance(
            stations_arr, elevations_arr, water_level,
            sta_min=left_bank, sta_max=right_bank,
            n=_n_ch(station_index), n_segments=_n_segs,
        )
        K_rob, A_rob = 0.0, 0.0
        if eff_right > right_bank + 1e-6:
            K_rob, A_rob = self._zone_conveyance(
                stations_arr, elevations_arr, water_level,
                sta_min=right_bank, sta_max=eff_right,
                n=_n_rob(station_index), n_segments=_n_segs,
            )

        K_total = K_lob + K_ch + K_rob
        A_total = A_lob + A_ch + A_rob

        if K_total <= 0.0 or A_total <= 0.0:
            return _fallback()

        # Ineffective Flow Area (HEC-RAS Technical Reference Manual)
        # WSE < trigger elevation: IFA 区段的面积不参与 conveyance，湿周也排除
        # WSE >= trigger elevation: IFA 关闭，使用完整断面
        if self._ineffective_areas and station_index < len(self._ineffective_areas):
            ifa_blocks = self._ineffective_areas[station_index]
            if ifa_blocks:
                # 计算需要排除的无效面积和湿周
                A_ineff = 0.0
                P_ineff = 0.0
                for blk in ifa_blocks:
                    ifa_left = float(blk.get('left_sta_m', blk.get('sta_l', 0)))
                    ifa_right = float(blk.get('right_sta_m', blk.get('sta_r', 0)))
                    ifa_elev = float(blk.get('elevation_m', blk.get('elev', 1e9)))
                    if water_level < ifa_elev:
                        # 仅扣除有效过水边界内的 IFA 区段，避免与 encroachment 重复扣减
                        ifa_left_eff = max(ifa_left, eff_left)
                        ifa_right_eff = min(ifa_right, eff_right)
                        if ifa_right_eff <= ifa_left_eff + 1e-6:
                            continue
                        A_blk, P_blk = self._segment_area_perimeter(
                            stations_arr, elevations_arr, water_level,
                            ifa_left_eff, ifa_right_eff)
                        A_ineff += A_blk
                        P_ineff += P_blk
                if A_ineff > 0.0:
                    A_eff = max(A_total - A_ineff, A_total * 0.05)
                    # 湿周：排除 IFA 段的湿周，但保留活跃区域的湿周
                    _, P_total_full = self._segment_area_perimeter(
                        stations_arr, elevations_arr, water_level,
                        eff_left, eff_right)
                    P_eff = max(P_total_full - P_ineff, P_total_full * 0.1)
                    R_eff = A_eff / max(P_eff, 1e-9)
                    # 等效 n: 从原 K_total 反推
                    R_old = A_total / max(P_total_full, 1e-9)
                    n_equiv = A_total * R_old ** (2.0/3.0) / max(K_total, 1e-9)
                    K_total = (1.0 / max(n_equiv, 0.001)) * A_eff * R_eff ** (2.0/3.0)
                    A_total = A_eff

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

    def _solve_culverts_parallel(
        self,
        Q: float,
        W_downstream: float,
        culvert_list: list,
        bed_us: float,
    ) -> float:
        """并联涵洞组合求解上游水面高程（HEC-RAS Multiple Culverts）。

        对每个涵洞独立计算通流能力，总流量相加后与 Q 对比，
        用 brentq 找到满足总流量 Q 所需的上游水位 HW。

        不同涵洞可有不同倒置高程（us_invert_m）：上游水位低于某涵洞入口时，
        该涵洞不过流；所有涵洞均不过流时返回 W_downstream。

        Args:
            Q: 总流量 (m³/s)
            W_downstream: 下游水面高程 (m)
            culvert_list: 涵洞参数字典列表
            bed_us: 上游断面床面高程 (m)
        Returns:
            W_upstream: 上游水面高程 (m)
        """
        from physics.structures.culvert import Culvert, CulvertGeometry
        from scipy.optimize import brentq as _brentq

        # 构建每个涵洞的 Culvert 对象和关键参数
        culverts_built = []
        for _cv in culvert_list:
            _shape = str(_cv.get("shape", "circular"))
            _diam = float(_cv.get("diameter_m", 0.0))
            _ht = float(_cv.get("height_m", _diam))
            _wd = float(_cv.get("width_m", _diam))
            _len = float(_cv.get("length_m", 30.0))
            _us_inv = float(_cv.get("us_invert_m", bed_us))
            _ds_inv = float(_cv.get("ds_invert_m", _us_inv - 0.01))
            _nb = int(_cv.get("n_barrels", 1))
            _mn = float(_cv.get("manning_n", 0.013))
            _ke = float(_cv.get("entrance_loss_coef", 0.5))
            _slp = (_us_inv - _ds_inv) / max(_len, 0.1)
            _road_elev = float(_cv.get("road_elev_m", _us_inv + _ht + 1.0))
            _road_w = float(_cv.get("road_width_m", 10.0))
            _road_cd = float(_cv.get("road_cd", 1.5))
            try:
                _geom = CulvertGeometry(
                    shape=_shape, length=_len, slope=max(_slp, 1e-6),
                    diameter=_diam if _shape == "circular" else None,
                    width=_wd if _shape != "circular" else None,
                    height=_ht if _shape != "circular" else None,
                    invert_elevation=_us_inv,
                    n_barrels=_nb,
                )
                _culv = Culvert(position=0.0, geometry=_geom, manning_n=_mn, entrance_loss_coef=_ke)
                _h_ds = max(W_downstream - _ds_inv, 0.0)
                culverts_built.append((_culv, _us_inv, _h_ds, _nb, _road_elev, _road_w, _road_cd))
            except Exception:
                continue

        if not culverts_built:
            return W_downstream + 0.1

        def _total_Q(HW: float) -> float:
            """给定上游 WSE，计算所有涵洞 + 道路漫顶的总通流量。"""
            Q_sum = 0.0
            for _culv, _us_inv, _h_ds, _nb, _re, _rw, _rcd in culverts_built:
                _h_us = max(HW - _us_inv, 0.0)
                if _h_us <= 0.0:
                    continue
                # 出口控制流量（给定 h_us 能通过的 Q）
                _Qout = _culv._solve_discharge_by_required_headwater(
                    _h_us, lambda q, _h=_h_ds: _culv._required_headwater_outlet(q, _h))
                # 入口控制流量
                _Qin = _culv._solve_discharge_by_required_headwater(
                    _h_us, _culv._required_headwater_inlet)
                Q_sum += min(_Qout, _Qin)
                # 道路漫顶
                _h_ot = max(HW - _re, 0.0)
                if _h_ot > 0.0:
                    Q_sum += min(_rcd * _rw * _h_ot ** 1.5, Q)
            return Q_sum

        # 搜索上界：从最高倒置高程处开始，指数步长扩展
        W_lo = W_downstream
        W_hi = max(_us_inv for _, _us_inv, *_ in culverts_built) + 0.1
        _step = 0.5
        for _ in range(60):
            if _total_Q(W_hi) >= Q:
                break
            W_hi += _step
            _step = min(_step * 1.5, 5.0)  # 指数增长，上限 5m/步

        # brentq 求解
        try:
            W_us = _brentq(lambda W: _total_Q(W) - Q, W_lo, W_hi, xtol=1e-5, maxiter=80)
        except Exception:
            # 降级：选 us_invert 最低的涵洞单独求解
            best_cv = min(culvert_list, key=lambda cv: float(cv.get("us_invert_m", bed_us)))
            return self._solve_culvert(Q, W_downstream, best_cv, bed_us)

        W_us = max(float(W_us), W_downstream + 0.001)
        return W_us

    def _solve_inline_structure(
        self,
        Q: float,
        W_downstream: float,
        structure: dict,
        bed_us: float,
    ) -> float:
        """计算内联结构（闸门+堰）的上游水面高程。

        按 HEC-RAS Technical Reference Manual:
        Q_total = Σ Q_gate_i + Q_weir
        Q_gate = Cg × Ag × sqrt(2g × ΔH)
        Q_weir = Cw × L × H^(3/2)
        迭代上游水位使 Q_total = Q

        Args:
            Q: 总流量 (m³/s)
            W_downstream: 下游水面高程 (m)
            structure: 内联结构参数字典
            bed_us: 上游断面床面高程 (m)
        Returns:
            W_upstream: 上游水面高程 (m)
        """
        g = self.g
        lf = 0.3048

        # 堰参数
        weir_coef = float(structure.get("weir_coef", 3.1))  # 英制系数
        weir_coef_si = weir_coef * lf ** 0.5  # 转 SI: C_si = C_us * ft^0.5
        weir_width_m = float(structure.get("weir_width_ft", 0)) * lf
        weir_min_elev_m = float(structure.get("weir_min_elev_ft", 0)) * lf
        if np.isnan(weir_min_elev_m):
            weir_min_elev_m = bed_us

        # 闸门参数
        gates = structure.get("gates", [])

        def _compute_Q_at_WSE(W_us: float) -> float:
            """给定上游水位，计算结构可通过的总流量。"""
            Q_total = 0.0

            # 堰流
            H_weir = max(W_us - weir_min_elev_m, 0.0)
            if H_weir > 0 and weir_width_m > 0:
                Q_weir = weir_coef_si * weir_width_m * H_weir ** 1.5
                # 淹没修正
                H_tw = max(W_downstream - weir_min_elev_m, 0.0)
                if H_tw > 0 and H_tw / max(H_weir, 1e-9) > 0.67:
                    subm_ratio = H_tw / max(H_weir, 1e-9)
                    subm_factor = (1.0 - subm_ratio ** 1.5) ** 0.385  # Villemonte
                    Q_weir *= max(subm_factor, 0.01)
                Q_total += Q_weir

            # 闸门流量 (HEC-RAS TRM: Sluice Gate)
            # 自由出流: Q = C_u * W * B * sqrt(2g * H)，H = 上游能量水头
            # 淹没出流: Q = C_s * W * B * sqrt(2g * H_o)，H_o = EGL_us - WSE_ds
            # 过渡区: SB 0.67-0.80 线性插值
            for gate in gates:
                opening_m = float(gate.get("opening_m", 0))
                n_open = int(gate.get("n_openings", 0))
                width_m = float(gate.get("width_m", 0))
                height_m = float(gate.get("height_m", opening_m))
                invert_m = float(gate.get("invert_m", bed_us))
                Cg = float(gate.get("sluice_coef", 0.8))

                if opening_m <= 0 or n_open <= 0 or width_m <= 0:
                    continue

                A_gate = width_m * opening_m * n_open
                # HEC-RAS: H = 上游能量水头 above gate invert
                H = max(W_us - invert_m, 0.0)
                h_ds_gate = max(W_downstream - invert_m, 0.0)
                # H_o = 上游 WSE - 下游 WSE (energy head difference)
                H_o = max(W_us - W_downstream, 0.0)
                # 淹没比
                SB = h_ds_gate / max(H, 1e-9)

                # HEC-RAS TRM: H/B 判定流态
                B = opening_m
                # 近全开闸门（opening >= 0.8*height）不适用 H/B 堰流过渡
                _gate_fully_open = (opening_m >= height_m * 0.85)
                H_over_B = H / max(B, 1e-9) if (B > 0 and not _gate_fully_open) else 99.0
                # 闸门自身的堰流系数（英制）
                gate_wc_us = float(gate.get("gate_weir_coef", 3.1))
                gate_wc_si = gate_wc_us * lf ** 0.5
                L_gate = width_m * n_open

                if H_over_B <= 1.0:
                    # 堰流模式（水位低于闸门开度顶部）
                    Q_gate = gate_wc_si * L_gate * H ** 1.5
                elif H_over_B < 1.25:
                    # 堰流→孔口过渡
                    Q_weir_g = gate_wc_si * L_gate * H ** 1.5
                    Q_orifice_g = Cg * A_gate * np.sqrt(max(2.0 * g * H, 0.0))
                    frac = (H_over_B - 1.0) / 0.25
                    Q_gate = Q_weir_g * (1 - frac) + Q_orifice_g * frac
                else:
                    # 孔口流 + 淹没过渡
                    if SB < 0.67:
                        Q_gate = Cg * A_gate * np.sqrt(max(2.0 * g * H, 0.0))
                    elif SB > 0.80:
                        Q_gate = Cg * A_gate * np.sqrt(max(2.0 * g * H_o, 0.0))
                    else:
                        Q_free = Cg * A_gate * np.sqrt(max(2.0 * g * H, 0.0))
                        Q_subm = Cg * A_gate * np.sqrt(max(2.0 * g * H_o, 0.0))
                        frac = (SB - 0.67) / 0.13
                        Q_gate = Q_free * (1 - frac) + Q_subm * frac

                Q_total += Q_gate

                # 闸门顶溢流：水位超过闸门顶 (invert + height) 时的堰流
                gate_top_m = invert_m + height_m
                H_over = W_us - gate_top_m
                if H_over > 0:
                    L_over = width_m * n_open
                    Q_over = weir_coef_si * L_over * H_over ** 1.5
                    # 淹没修正
                    H_tw_over = max(W_downstream - gate_top_m, 0.0)
                    if H_tw_over > 0 and H_tw_over / max(H_over, 1e-9) > 0.67:
                        sr = H_tw_over / max(H_over, 1e-9)
                        Q_over *= max((1.0 - sr ** 1.5) ** 0.385, 0.01)
                    Q_total += Q_over

            return Q_total

        # 二分法迭代：找 W_us 使 Q_structure(W_us) = Q
        W_lo = max(W_downstream, bed_us + 0.01)
        W_hi = W_downstream + 30.0  # 最大壅水 30m

        for _ in range(100):
            W_mid = 0.5 * (W_lo + W_hi)
            Q_mid = _compute_Q_at_WSE(W_mid)
            if abs(Q_mid - Q) < Q * 0.001:
                break
            if Q_mid < Q:
                W_lo = W_mid
            else:
                W_hi = W_mid

        W_upstream = 0.5 * (W_lo + W_hi)
        return float(max(W_upstream, W_downstream + 0.001))

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


    def _bridge_face_area(
        self,
        xs_index: int,
        water_level: float,
        opening_w: float,
        A_full: float,
        A_pier: float,
    ) -> float:
        """计算桥孔范围有效过水面积（用于速度项），并扣除桥墩面积。

        当 opening_w > 0 时，优先按桥孔范围（bank stations 中心 ± opening_w/2）
        积分实际断面面积；若几何数据不可用或积分面积 <= 0，则回退矩形近似。
        返回值已扣除桥墩面积，下限为 A_full * 0.05。
        """
        idx = int(xs_index)
        opening_w = float(opening_w)
        A_full = float(max(A_full, 1e-9))
        A_pier = float(max(A_pier, 0.0))

        if opening_w <= 0.0:
            return float(max(A_full - A_pier, A_full * 0.05))

        A_bridge_face = 0.0
        xs = None
        if self._xs_array and 0 <= idx < len(self._xs_array):
            xs = self._xs_array[idx]

        # 1) 优先用桥孔范围内的实际断面积分面积
        if (
            xs is not None
            and hasattr(xs, "distances")
            and hasattr(xs, "elevations")
            and self._bank_stations is not None
            and idx < len(self._bank_stations)
            and self._bank_stations[idx] is not None
        ):
            lb, rb = self._bank_stations[idx]
            if lb is not None and rb is not None:
                center = 0.5 * (float(lb) + float(rb))
                sta_left = center - opening_w * 0.5
                sta_right = center + opening_w * 0.5

                stations_arr = np.asarray(xs.distances, dtype=float)
                elevations_arr = np.asarray(xs.elevations, dtype=float)
                sta_min = float(np.min(stations_arr))
                sta_max = float(np.max(stations_arr))
                sta_left = max(sta_left, sta_min)
                sta_right = min(sta_right, sta_max)

                if sta_right > sta_left + 1e-6:
                    A_bridge_face, _ = self._segment_area_perimeter(
                        stations_arr, elevations_arr, float(water_level), sta_left, sta_right
                    )

        # 2) 回退：矩形近似
        if A_bridge_face <= 0.0:
            if xs is not None and hasattr(xs, "min_elevation"):
                h_rect = max(float(water_level) - float(xs.min_elevation), 0.0)
                A_bridge_face = opening_w * h_rect
            else:
                A_bridge_face = A_full

        # 3) 扣除桥墩面积并设置下限
        return float(max(min(A_full, float(A_bridge_face)) - A_pier, A_full * 0.05))

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
        # 桥墩拖曳系数：优先从 coefficients.momentum_cd 读取
        _coefs = bridge.get("coefficients", {})
        C_D = float(_coefs.get("momentum_cd", bridge.get("pier_cd", 2.0)))
        deck_elev = float(bridge.get("deck_elevation_m", 1e9))
        pier_height = float(bridge.get("pier_height_m", 1e9))
        deck_weir_coef = float(bridge.get("deck_weir_coef", 1.70))
        deck_weir_len_cfg = float(bridge.get("deck_weir_length_m", 0.0))
        # 桥孔宽度（从 Lid Profile 提取）用于限制有效面积
        _opening_w = float(bridge.get("bridge_opening_width_m", 0.0))

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
        # 改动：A2_eff 用桥孔范围内实际断面面积（_segment_area_perimeter），回退矩形近似
        A2_eff = self._bridge_face_area(
            xs_index=ds_xs_index,
            water_level=W_downstream,
            opening_w=_opening_w,
            A_full=A2,
            A_pier=A_pier2,
        )
        # 壅水判断：使用 EGL (能量梯度线) 而非 WSE
        V2_temp = Q_under_ds / max(A2_eff, 1e-9)
        EGL2 = W_downstream + V2_temp ** 2 / (2.0 * self.g)
        if EGL2 > deck_elev > bed_ds:
            A2_eff = max(A2_eff - (W_downstream - deck_elev) * T2, A2 * 0.1)
        P2_force = self._hydrostatic_pressure_force(h2, ds_xs_index)

        S0_bridge = (bed_us - bed_ds) / max(L_bridge, 0.1)

        # 压力流检查 (HEC-RAS TRM: High Flow Computations)
        # 当上游 WSE > 低弦 deck_elev 时，用压力流方程提供初始估计
        _sub_inlet_cd = float(_coefs.get("submerged_inlet_cd",
                              _coefs.get("Submerged Inlet Cd", 0.5)))
        _sub_io_cd = float(_coefs.get("submerged_inlet_outlet_cd",
                           _coefs.get("Submerged Inlet-Outlet Cd", 0.8)))
        _A_opening = deck_weir_len_cfg * max(deck_elev - bed_us, 0.1) if deck_elev < 1e8 else 0.0

        W3_trial = W_downstream + max(0.05, abs(bed_us - bed_ds) + 0.05)
        W3_trial = max(W3_trial, bed_us + 0.01)

        # 压力流初始化：如果低流量结果的 EGL > deck，提高初始猜测
        if deck_elev < 1e8 and _A_opening > 0:
            _h_init = max(W3_trial - bed_us, 0.01)
            _A_init = max(self._get_geometry(_h_init, us_xs_index)[0], 1e-9)
            _V_init = Q / _A_init
            _EGL_init = W3_trial + _V_init ** 2 / (2.0 * self.g)
            if _EGL_init > deck_elev:
                # 压力流：Q = Cd * A_opening * sqrt(2g * H_eff)
                _ds_submerged = W_downstream > deck_elev
                _Cd_press = _sub_io_cd if _ds_submerged else _sub_inlet_cd
                if _Cd_press > 0 and _A_opening > 0:
                    # H_eff = (Q / (Cd * A))^2 / (2g)
                    _H_eff = (Q / (_Cd_press * _A_opening)) ** 2 / (2.0 * self.g)
                    # WSE_us ≈ WSE_ds + H_eff (crude estimate for pressure flow)
                    W3_pressure = W_downstream + _H_eff
                    W3_trial = max(W3_trial, W3_pressure)

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
            # 改动：A3_eff 用桥孔范围内实际断面面积（_segment_area_perimeter），回退矩形近似
            A3_eff = self._bridge_face_area(
                xs_index=us_xs_index,
                water_level=W3_trial,
                opening_w=_opening_w,
                A_full=A3,
                A_pier=A_pier3,
            )
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
            # 改动：A3p_eff 用桥孔范围内实际断面面积（_segment_area_perimeter），回退矩形近似
            A3p_eff = self._bridge_face_area(
                xs_index=us_xs_index,
                water_level=W3p,
                opening_w=_opening_w,
                A_full=A3p,
                A_pier=A_pier3p,
            )
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
        # 使用 list 支持同一位置多个并联涵洞（HEC-RAS Multiple Culverts）
        _culvert_at_us: dict[int, list] = {}  # us_xs_index -> list of culvert dicts
        if self._culverts:
            for _cv in self._culverts:
                if "us_xs_index" in _cv:
                    _culvert_at_us.setdefault(int(_cv["us_xs_index"]), []).append(_cv)
                elif hasattr(self, "_xs_station_labels") and self._xs_station_labels:
                    _us_rs = str(_cv.get("us_rs", "")).strip()
                    _us_idx = next((j for j, lbl in enumerate(self._xs_station_labels)
                                    if str(lbl).strip() == _us_rs), None)
                    if _us_idx is not None:
                        _cv_copy = dict(_cv)
                        _cv_copy["us_xs_index"] = _us_idx
                        _culvert_at_us.setdefault(_us_idx, []).append(_cv_copy)

        # --- Inline Structure index resolution ---------------------------------
        _inline_at_us: dict[int, dict] = {}
        if self._inline_structures:
            for _is in self._inline_structures:
                if "us_xs_index" in _is:
                    _inline_at_us[int(_is["us_xs_index"])] = _is
        # -----------------------------------------------------------------------
        for i in range(n_xs - 2, -1, -1):
            # 逐断面流量：支持区间来水（HEC-RAS Change in Discharge）
            # 下游断面 i+1 的流量（回水从下游向上游推进）
            Q_ds_local = float(Q_arr[i + 1])
            # 上游断面 i 的流量
            Q_us_local = float(Q_arr[i])
            # 本段使用的平均流量（HEC-RAS 在标准步中使用下游断面流量）
            Q_seg = Q_ds_local

            # HEC-RAS reach_length=0：此断面与下游断面在同一河流位置（零距离）
            # 无摩擦损失，直接继承下游水位，跳过能量方程计算
            # 注意：有桥梁/涵洞/闸门的断面即使 rl=0 也不能跳过（结构物需单独计算损失）
            _raw_rl_i = float(self._reach_lengths[i]) if self._reach_lengths and i < len(self._reach_lengths) else 1.0
            if _raw_rl_i < 1e-6 and not (i in _bridge_at_us) and not (i in _culvert_at_us) and not (i in _inline_at_us):
                W[i] = W[i + 1]
                h[i] = max(W[i] - bed[i], 0.001)
                continue

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
            _banks_ref = self._channel_bank_stations if self._channel_bank_stations else self._bank_stations
            if _banks_ref and i + 1 < len(_banks_ref):
                xs_ds = self._xs_array[i + 1] if self._xs_array and i + 1 < len(self._xs_array) else None
                if xs_ds is not None and hasattr(xs_ds, 'distances'):
                    _lb, _rb = _banks_ref[i + 1]
                    _sta = np.asarray(xs_ds.distances)
                    _ele = np.asarray(xs_ds.elevations)
                    _wl = float(xs_ds.min_elevation) + h_ds
                    _n_l = self._manning_n_lob[i+1] if self._manning_n_lob and i+1 < len(self._manning_n_lob) else self.n
                    _n_c = self._manning_ns[i+1] if self._manning_ns and i+1 < len(self._manning_ns) else self.n
                    _n_r = self._manning_n_rob[i+1] if self._manning_n_rob and i+1 < len(self._manning_n_rob) else self.n
                    _sta_min = float(np.min(_sta))
                    _sta_max = float(np.max(_sta))
                    _eff_l, _eff_r = self._resolve_effective_flow_limits(
                        station_index=i + 1,
                        sta_min_all=_sta_min,
                        sta_max_all=_sta_max,
                        left_bank=float(_lb),
                        right_bank=float(_rb),
                        effective_limits=None,
                    )
                    if _eff_l < float(_lb) - 1e-6:
                        _K_ds_lob, _ = self._zone_conveyance(_sta, _ele, _wl, _eff_l, float(_lb), _n_l)
                    _K_ds_ch, _ = self._zone_conveyance(_sta, _ele, _wl, float(_lb), float(_rb), _n_c)
                    if _eff_r > float(_rb) + 1e-6:
                        _K_ds_rob, _ = self._zone_conveyance(_sta, _ele, _wl, float(_rb), _eff_r, _n_r)

            # 加权平均 reach length (HEC-RAS TRM 2-3: K-weighted)
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
            # 子步已禁用：天然河道断面间的几何插值会引入累积偏差
            # HEC-RAS 不做断面间插值，而是用 HP Table 在每个断面独立计算
            # 仅在需要的地方（如用户显式请求）启用子步
            if False and not (i in _bridge_at_us):  # 禁用子步
                n_substeps = min(50, max(1, int(energy_change / 0.002)))

            # 子步迭代：每步以前一子步 W 为下游，床面高程线性插值
            # 子步间的断面几何在 i 和 i+1 之间按位置线性插值
            # 重要：子步能量方程必须显式绑定本段流量，不能覆盖外层 Q
            Q_seg_local = Q_us_local
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
                _Sf_ds_sub   = (Q_seg_local / _K_ds_sub) ** 2 if _K_ds_sub > 0 else Sf_ds
                _V_ds_sub    = Q_seg_local / _A_ds_sub
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
                    V_us_r = Q_seg_local / max(A_us_r, 1e-9)
                    # 上游面输水率：插值
                    _K_us_ip1, _alpha_us_ip1 = self._compute_subdivided_conveyance(h_us_r, i + 1)
                    _K_us_i,   _alpha_us_i   = self._compute_subdivided_conveyance(h_us_r, i)
                    K_us_r     = max(w_ip1_us * _K_us_ip1 + w_i_us * _K_us_i, 1e-9)
                    alpha_us_r = w_ip1_us * _alpha_us_ip1 + w_i_us * _alpha_us_i
                    Sf_us_r = (
                        (Q_seg_local / K_us_r) ** 2
                        if K_us_r > 0
                        else self.compute_friction_slope(h_us_r, Q_seg_local, i)
                    )
                    vh_us_r = alpha_us_r * V_us_r ** 2 / (2.0 * self.g)
                    # HEC-RAS 默认: Average Conveyance Equation
                    # Sf_avg = ((Q_us + Q_ds) / (K_us + K_ds))^2
                    Sf_avg_r = min(
                        ((Q_seg_local + Q_seg_local) / max(K_us_r + _K_ds_sub, 1e-9)) ** 2,
                        1.0,
                    )
                    cc_r = self._contraction_coefs[i] if self._contraction_coefs and i < len(self._contraction_coefs) else contraction_coef
                    ec_r = self._expansion_coefs[i]   if self._expansion_coefs   and i < len(self._expansion_coefs)   else expansion_coef
                    h_f_r = dx_sub * Sf_avg_r
                    h_e_r = cc_r * (vh_us_r - _vh_ds_sub) if vh_us_r > _vh_ds_sub else ec_r * (_vh_ds_sub - vh_us_r)
                    # 残差 = 上游总能量头 - 下游总能量头 - 摩擦损失 - 局部损失
                    return (W_us_val + vh_us_r) - (W_sub_ds + _vh_ds_sub) - h_f_r - h_e_r

                _brentq_ok = False
                # --- 亚临界 brentq 区间策略 ---
                # 只在 [max(W_ds, bed+y_c), W_ds+20] 窄区间内寻找亚临界根，
                # 明确跳过可能存在的超临界根。
                _y_c_us = self._compute_critical_depth(Q_seg_local, i)
                _W_critical_us = bed_sub_us + _y_c_us
                _Sc_us = self._compute_critical_slope(Q_seg_local, i)
                _S0_sub = max((bed_sub_us - bed_sub_ds) / max(dx_sub, 0.1), 0.0)
                _is_steep_substep = _S0_sub > _Sc_us
                # 显著逆坡（床面上游抬升 > 0.5m）时允许 WSE 低于下游
                _bed_rise = bed_sub_us - bed_sub_ds
                _W_lo_narrow = _W_critical_us if _bed_rise > 0.5 else max(W_sub_ds, _W_critical_us)
                _W_hi = max(_W_lo_narrow + 1e-4, W_sub_ds + 20.0)
                try:
                    f_narrow_lo = _energy_residual(_W_lo_narrow)
                    f_hi = _energy_residual(_W_hi)
                    if np.isfinite(f_narrow_lo) and np.isfinite(f_hi) and f_narrow_lo * f_hi <= 0.0:
                        W_new = brentq(_energy_residual, _W_lo_narrow, _W_hi, xtol=1e-6, maxiter=100)
                        W_new = max(W_new, bed_sub_us + 1e-4)
                        # Froude 检查：确保找到的是亚临界根 (Fr < 1)
                        _h_check = max(W_new - bed_sub_us, 0.001)
                        _A_check, _, _, _T_check = self._get_geometry(_h_check, i)
                        _V_check = Q_seg_local / max(_A_check, 1e-9)  # 用本段流量计算 Fr，避免变流量段误判
                        _D_check = _A_check / max(_T_check, 1e-9)
                        _Fr_check = _V_check / max(np.sqrt(self.g * _D_check), 1e-9)
                        if _Fr_check > 1.0:
                            # 找到了超临界根——按 HEC-RAS 做法默认临界深度
                            W_new = _W_critical_us
                        W_trial = W_new
                        _converged = True
                        _brentq_ok = True
                    elif _is_steep_substep:
                        # 陡坡子步在窄区间无亚临界根时取临界深度。
                        # 例外：逆坡且下游 WSE 远高于上游临界（桥梁回水池传播）
                        _ds_above_crit = W_sub_ds - _W_critical_us
                        _near_bridge = any(abs(i - bi) <= 5 for bi in _bridge_at_us)
                        _threshold = 0.3 if _near_bridge else 0.7
                        if bed_sub_us > bed_sub_ds + 0.01 and _ds_above_crit > _threshold:
                            _brentq_ok = False
                        else:
                            W_new = _W_critical_us
                            W_trial = W_new
                            _converged = True
                            _brentq_ok = True
                    else:
                        # 缓坡断面窄区间（[max(W_ds,W_crit), W_ds+20]）未找到亚临界根。
                        # 一级回退：放宽到宽区间 [W_crit, W_ds+20]，允许 W_us < W_ds。
                        # 物理依据：当下游 WSE 因误差偏高时，能量方程的真实亚临界根
                        # 可能低于 W_ds，只需保证 W_us >= W_crit（最低物理约束）。
                        _W_lo_wide = _W_critical_us
                        _W_hi_wide = max(_W_lo_wide + 1e-4, W_sub_ds + 20.0)
                        try:
                            f_wide_lo = _energy_residual(_W_lo_wide)
                            f_wide_hi = _energy_residual(_W_hi_wide)
                            if (np.isfinite(f_wide_lo) and np.isfinite(f_wide_hi)
                                    and f_wide_lo * f_wide_hi <= 0.0):
                                W_new = brentq(_energy_residual, _W_lo_wide, _W_hi_wide,
                                               xtol=1e-6, maxiter=100)
                                W_new = max(W_new, bed_sub_us + 1e-4)
                                # Froude 检查：确保找到的是亚临界根
                                _h_check2 = max(W_new - bed_sub_us, 0.001)
                                _A_check2, _, _, _T_check2 = self._get_geometry(_h_check2, i)
                                _V_check2 = Q_seg_local / max(_A_check2, 1e-9)  # 用本段流量计算 Fr，避免变流量段误判
                                _D_check2 = _A_check2 / max(_T_check2, 1e-9)
                                _Fr_check2 = _V_check2 / max(np.sqrt(self.g * _D_check2), 1e-9)
                                if _Fr_check2 > 1.0:
                                    W_new = _W_critical_us
                                W_trial = W_new
                                _converged = True
                                _brentq_ok = True
                            else:
                                _brentq_ok = False
                        except Exception:
                            _brentq_ok = False
                except Exception:
                    # 极端情况下若陡坡子步求根异常，仍按 HEC-RAS 取临界深度；
                    # 缓坡段则回退到 Picard。
                    if _is_steep_substep:
                        W_new = _W_critical_us
                        W_trial = W_new
                        _converged = True
                        _brentq_ok = True
                    else:
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
                        V_us = Q_seg_local / max(A_us, 1e-9)
                        K_us, alpha_us = self._compute_subdivided_conveyance(h_us, i)
                        Sf_us = (
                            (Q_seg_local / K_us) ** 2
                            if K_us > 0
                            else self.compute_friction_slope(h_us, Q_seg_local, i)
                        )
                        vh_us = alpha_us * V_us ** 2 / (2.0 * self.g)
                        # HEC-RAS 默认: Average Conveyance Equation
                        Sf_avg = min(
                            ((Q_seg_local + Q_seg_local) / max(K_us + _K_ds_sub, 1e-9)) ** 2,
                            1.0,
                        )
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
                        # 亚临界解下界：至少等于临界水位（HEC-RAS 混合流默认）
                        W_new = max(W_new, _W_critical_us)
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
            V_us = Q_seg_local / max(A_us, 1e-9)
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
                        Q=Q_seg_local,
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
                    V_eff_e = Q_seg_local / max(A_eff_e, 1e-9)
                    vh_eff_e = V_eff_e ** 2 / (2.0 * self.g)
                    h_pier_e = _pier_k * vh_eff_e
                    R_eff_e = A_eff_e / max(_P_br, 1e-6)
                    n_br_e = self._manning_ns[i] if self._manning_ns and i < len(self._manning_ns) else self.n
                    Sf_br_e = (
                        (Q_seg_local * n_br_e / (A_eff_e * R_eff_e ** (2.0/3.0))) ** 2
                        if A_eff_e > 0 and R_eff_e > 0 else 0
                    )
                    h_f_br_e = _br_len * Sf_br_e
                    vh_us_app = alpha_us * V_us ** 2 / (2.0 * self.g)
                    h_contr_e = _cc * max(vh_eff_e - vh_us_app, 0.0)
                    h_ds_app = max(W[i + 1] - bed[i + 1], 0.01)
                    A_ds_app, _, _, _ = self._get_geometry(h_ds_app, i + 1)
                    V_ds_app = Q_seg_local / max(A_ds_app, 1e-9)
                    _, alpha_ds_app = self._compute_subdivided_conveyance(h_ds_app, i + 1)
                    vh_ds_app = alpha_ds_app * V_ds_app ** 2 / (2.0 * self.g)
                    h_exp_e = _ec * max(vh_eff_e - vh_ds_app, 0.0)
                    W_trial = W_trial + h_pier_e + h_f_br_e + h_contr_e + h_exp_e
                # Re-apply physical limit
                W_trial = max(W_trial, bed[i] + 1e-4)
                W_trial = min(W_trial, _W_MAX)
            # --- Culvert (HDS-5) ------------------------------------------------
            if i in _culvert_at_us:
                _cv_list = _culvert_at_us[i]
                if len(_cv_list) == 1:
                    W_trial = self._solve_culvert(
                        Q=Q_seg_local, W_downstream=W[i + 1],
                        culvert_dict=_cv_list[0], bed_us=bed[i])
                else:
                    # 并联涵洞（Multiple Culverts）：各涵洞共同分担总流量
                    W_trial = self._solve_culverts_parallel(
                        Q=Q_seg_local, W_downstream=W[i + 1],
                        culvert_list=_cv_list, bed_us=bed[i])
                W_trial = max(W_trial, bed[i] + 1e-4)
                W_trial = min(W_trial, _W_MAX)
            # --- Inline Structure (gate + weir) ---------------------------------
            if i in _inline_at_us:
                _is = _inline_at_us[i]
                W_trial = self._solve_inline_structure(
                    Q=Q_seg_local, W_downstream=W[i + 1],
                    structure=_is, bed_us=bed[i])
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
        # 记录最近一次绝对水位线，供 Floodway Encroachment 基准水位使用
        self._last_wse_profile = np.asarray(W, dtype=float).copy()
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

        # HEC-RAS 水跃定位：从上游向下游扫描
        # 当亚临界 Specific Force 明显超过超临界 SF 时判定水跃
        dm_arr = np.asarray(delta_m)
        dm_max = float(np.max(np.abs(dm_arr))) if len(dm_arr) > 0 else 1.0
        threshold = max(dm_max * 0.1, 0.5)

        for k in range(1, len(idx_valid)):
            d_prev = delta_m[k - 1]
            d_curr = delta_m[k]
            if d_curr > threshold and d_prev <= threshold:
                return idx_valid[k]

        for k in range(len(idx_valid)):
            if delta_m[k] > threshold:
                return idx_valid[k]

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
        r"""按 HEC-RAS 6.6 Mixed Flow Regime Calculations 拼接混合流剖面。

        流程：
            1) 直接使用已算好的亚临界标准步剖面
            2) 将“亚临界解等于临界深度”的断面作为控制断面
            3) 从控制断面向下游重算超临界剖面，边界条件为正常深度
            4) 用 Specific Force 首次满足 SF_sub > SF_super 的位置判定水跃
        """
        W_sub = np.asarray(W_subcritical, dtype=float).copy()
        bed_arr = np.asarray(bed, dtype=float)

        y_c = np.zeros(n_xs, dtype=float)
        for i in range(n_xs):
            y_c[i] = self._compute_critical_depth(Q, i)
        W_critical = bed_arr + y_c

        def _specific_force(W_val: float, idx: int) -> float:
            """Specific Force：当前几何接口下取 beta=1，y_bar≈A/T。"""
            h_val = max(float(W_val) - bed_arr[idx], 1e-6)
            A, _P, _R, T = self._get_geometry(h_val, idx)
            A = max(float(A), 1e-9)
            T = max(float(T), 1e-9)
            beta_sf = 1.0
            y_bar = A / T
            return float(Q ** 2 * beta_sf / (self.g * A) + A * y_bar)

        def _local_bed_slope(idx: int) -> float:
            if idx < n_xs - 1:
                dx_seg = float(abs(x[idx + 1] - x[idx]))
                if dx_seg > 1e-6:
                    return float(max((bed_arr[idx] - bed_arr[idx + 1]) / dx_seg, 1e-8))
            if idx > 0:
                dx_seg = float(abs(x[idx] - x[idx - 1]))
                if dx_seg > 1e-6:
                    return float(max((bed_arr[idx - 1] - bed_arr[idx]) / dx_seg, 1e-8))
            return float(max(self.S0, 1e-8))

        def _solve_normal_depth(idx: int) -> float:
            """用 Manning 方程求正常深度，供超临界边界使用。"""
            S0_local = _local_bed_slope(idx)
            if S0_local <= 1e-8:
                return float(max(0.95 * y_c[idx], 1e-4))

            n_local = self.n
            if self._manning_ns and idx < len(self._manning_ns):
                nv = self._manning_ns[idx]
                if nv and float(nv) > 0:
                    n_local = float(nv)

            def _yn_residual(y_val: float) -> float:
                y_safe = max(float(y_val), 1e-6)
                A, _P, R, _T = self._get_geometry(y_safe, idx)
                if A <= 0.0 or R <= 0.0:
                    return -Q
                conveyance = (1.0 / max(n_local, 0.001)) * A * R ** (2.0 / 3.0)
                return conveyance * np.sqrt(S0_local) - Q

            y_lo = 1e-4
            y_hi = max(1.5 * y_c[idx], 1.0)
            try:
                f_lo = _yn_residual(y_lo)
                f_hi = _yn_residual(y_hi)
                _expand = 0
                while (not np.isfinite(f_hi) or f_lo * f_hi > 0.0) and _expand < 12:
                    y_hi *= 2.0
                    f_hi = _yn_residual(y_hi)
                    _expand += 1
                if np.isfinite(f_lo) and np.isfinite(f_hi) and f_lo * f_hi <= 0.0:
                    y_n = brentq(_yn_residual, y_lo, y_hi, xtol=1e-6, maxiter=100)
                else:
                    y_n = 0.95 * y_c[idx]
            except Exception:
                y_n = 0.95 * y_c[idx]

            if (not np.isfinite(y_n)) or y_n <= 0.0:
                y_n = 0.95 * y_c[idx]

            # 数值安全：若正常深度因数值问题高于临界，轻微压到临界以下。
            if y_n >= y_c[idx]:
                y_n = max(0.999 * y_c[idx], 1e-4)
            return float(max(y_n, 1e-4))

        def _compute_supercritical_segment(control_idx: int, end_idx: int) -> np.ndarray:
            """从控制断面向下游推进超临界剖面。"""
            W_super = np.full(n_xs, np.nan, dtype=float)
            y_n_ctrl = _solve_normal_depth(control_idx)
            W_super[control_idx] = max(bed_arr[control_idx] + y_n_ctrl, bed_arr[control_idx] + 1e-4)

            for j in range(control_idx + 1, end_idx + 1):
                dx_seg = float(abs(x[j] - x[j - 1]))
                if dx_seg < 1e-6:
                    dx_seg = 1.0

                h_us = max(W_super[j - 1] - bed_arr[j - 1], 0.001)
                A_us, _P_us, _R_us, _T_us = self._get_geometry(h_us, j - 1)
                V_us = Q / max(A_us, 1e-9)
                K_us, alpha_us = self._compute_subdivided_conveyance(h_us, j - 1)
                Sf_us = (Q / K_us) ** 2 if K_us > 0 else self.compute_friction_slope(h_us, Q, j - 1)
                vh_us = alpha_us * V_us ** 2 / (2.0 * self.g)

                _cc = (
                    self._contraction_coefs[j]
                    if self._contraction_coefs and j < len(self._contraction_coefs)
                    else contraction_coef
                )
                _ec = (
                    self._expansion_coefs[j]
                    if self._expansion_coefs and j < len(self._expansion_coefs)
                    else expansion_coef
                )
                W_lo = bed_arr[j] + 1e-4
                W_hi = max(W_lo + 1e-4, bed_arr[j] + y_c[j] - 1e-4)

                def _super_residual(W_ds_val: float) -> float:
                    h_ds = max(W_ds_val - bed_arr[j], 0.001)
                    A_ds, _P_ds, _R_ds, _T_ds = self._get_geometry(h_ds, j)
                    V_ds = Q / max(A_ds, 1e-9)
                    K_ds, alpha_ds = self._compute_subdivided_conveyance(h_ds, j)
                    vh_ds = alpha_ds * V_ds ** 2 / (2.0 * self.g)
                    Sf_avg = min(((Q + Q) / max(K_us + max(K_ds, 1e-9), 1e-9)) ** 2, 1.0)
                    h_minor = _cc * (vh_ds - vh_us) if vh_ds > vh_us else _ec * (vh_us - vh_ds)
                    return (W_ds_val + vh_ds) - (W_super[j - 1] + vh_us) + dx_seg * Sf_avg + h_minor

                W_trial = min(max(W_super[j - 1] - dx_seg * max(Sf_us, 1e-6), W_lo), W_hi)
                _brentq_ok = False
                try:
                    f_lo = _super_residual(W_lo)
                    f_hi = _super_residual(W_hi)
                    if np.isfinite(f_lo) and np.isfinite(f_hi) and f_lo * f_hi <= 0.0:
                        W_trial = brentq(_super_residual, W_lo, W_hi, xtol=1e-6, maxiter=100)
                        _brentq_ok = True
                except Exception:
                    _brentq_ok = False

                if not _brentq_ok:
                    for _iter in range(60):
                        h_ds = max(W_trial - bed_arr[j], 0.001)
                        A_ds, _P_ds, _R_ds, _T_ds = self._get_geometry(h_ds, j)
                        V_ds = Q / max(A_ds, 1e-9)
                        K_ds, alpha_ds = self._compute_subdivided_conveyance(h_ds, j)
                        vh_ds = alpha_ds * V_ds ** 2 / (2.0 * self.g)
                        Sf_avg = min(((Q + Q) / max(K_us + max(K_ds, 1e-9), 1e-9)) ** 2, 1.0)
                        h_minor = _cc * (vh_ds - vh_us) if vh_ds > vh_us else _ec * (vh_us - vh_ds)
                        W_new = W_super[j - 1] + vh_us - vh_ds - dx_seg * Sf_avg - h_minor
                        W_new = min(max(W_new, W_lo), W_hi)
                        if abs(W_new - W_trial) < 1e-4:
                            W_trial = W_new
                            break
                        W_trial = 0.5 * W_trial + 0.5 * W_new

                W_super[j] = float(min(max(W_trial, W_lo), W_hi))

            return W_super

        # 控制断面：亚临界结果等于临界深度的位置。
        # 连续临界断面视为同一控制带，仅保留每带首个断面向下游推进超临界剖面。
        crit_tol = np.maximum(1e-4, 1e-4 * np.maximum(y_c, 1.0))
        control_mask = np.abs(W_sub - W_critical) <= crit_tol
        if n_xs > 0:
            control_mask[-1] = False

        control_sections: List[int] = []
        for i in range(n_xs):
            if not control_mask[i]:
                continue
            if i == 0 or (not control_mask[i - 1]):
                control_sections.append(i)

        if not control_sections:
            h_final = np.maximum(W_sub - bed_arr, 0.001)
            return W_sub, h_final

        W_final = W_sub.copy()
        for c_idx, control_idx in enumerate(control_sections):
            seg_end = (control_sections[c_idx + 1] - 1) if (c_idx + 1 < len(control_sections)) else (n_xs - 1)
            seg_end = max(seg_end, control_idx)

            W_super = _compute_supercritical_segment(control_idx, seg_end)

            jump_idx: Optional[int] = None
            for j in range(control_idx, seg_end + 1):
                if not np.isfinite(W_super[j]):
                    continue
                sf_sub = _specific_force(W_sub[j], j)
                sf_super = _specific_force(W_super[j], j)
                sf_tol = max(1e-6, 1e-6 * abs(sf_super))
                if sf_sub > sf_super + sf_tol:
                    jump_idx = j
                    break

            jump_stop = seg_end + 1 if jump_idx is None else jump_idx
            for j in range(control_idx, jump_stop):
                if np.isfinite(W_super[j]):
                    W_final[j] = W_super[j]

        h_final = np.maximum(W_final - bed_arr, 0.001)
        return W_final, h_final

    def _solve_looped_network(self, Q_total, branches, junction_nodes):
        '''
        Hardy-Cross 方法求解环状河网的流量分配。

        原理（第一性原理）:
        1. 环路约束: 沿任一闭合环路，总水头损失 = 0
        2. 节点约束: 流入 = 流出（连续方程）
        3. 迭代: 对每个环路计算修正流量 dQ = -sum(h_L) / sum(dh_L/dQ)

        branches: list of dict, 每个分支:
          - xs_indices: 断面索引列表
          - connects: (from_node, to_node)
        junction_nodes: list of dict:
          - inflows: 进入该节点的分支
          - outflows: 离开该节点的分支
        '''
        q_total = float(Q_total)
        n_branch = len(branches or [])
        if n_branch <= 0:
            return {
                "converged": True,
                "iterations": 0,
                "branch_flows": [],
                "branches": [],
                "loops": [],
                "max_loop_residual": 0.0,
                "max_mass_error": 0.0,
            }

        # 基本健壮性检查：确保每条分支都携带连接节点和断面索引
        branch_connects: List[Tuple[object, object]] = []
        branch_xs: List[List[int]] = []
        for i, br in enumerate(branches):
            if not isinstance(br, dict):
                raise ValueError(f"branches[{i}] 必须是 dict")
            xs_idx = [int(v) for v in (br.get("xs_indices") or [])]
            if len(xs_idx) == 0:
                raise ValueError(f"branches[{i}] 缺少 xs_indices")
            conn = br.get("connects")
            if not isinstance(conn, (list, tuple)) or len(conn) != 2:
                raise ValueError(f"branches[{i}] 缺少 connects=(from_node,to_node)")
            branch_connects.append((conn[0], conn[1]))
            branch_xs.append(xs_idx)

        # 构建分支编号映射：支持 junction_nodes 里用索引或分支 id 引用
        branch_ref_to_idx: Dict[object, int] = {}
        for i, br in enumerate(branches):
            branch_ref_to_idx[i] = i
            branch_ref_to_idx[str(i)] = i
            if "id" in br:
                branch_ref_to_idx[br["id"]] = i
                branch_ref_to_idx[str(br["id"])] = i

        def _resolve_branch_indices(values) -> List[int]:
            out: List[int] = []
            for v in (values or []):
                idx = None
                if isinstance(v, int) and 0 <= v < n_branch:
                    idx = v
                elif isinstance(v, str):
                    if v in branch_ref_to_idx:
                        idx = branch_ref_to_idx[v]
                    else:
                        try:
                            vv = int(v)
                            if 0 <= vv < n_branch:
                                idx = vv
                        except Exception:
                            idx = None
                elif isinstance(v, dict) and ("id" in v) and (v["id"] in branch_ref_to_idx):
                    idx = branch_ref_to_idx[v["id"]]
                if idx is not None and idx not in out:
                    out.append(idx)
            return out

        # 用连通图检测闭合环路（无向图），并生成“有方向环路边序列”
        # 每个元素为 (branch_idx, sign): sign=+1 表示沿分支 connects 方向，-1 表示反向
        adjacency: Dict[object, List[Tuple[object, int, int]]] = {}
        for e_idx, (u, v) in enumerate(branch_connects):
            adjacency.setdefault(u, []).append((v, e_idx, +1))
            adjacency.setdefault(v, []).append((u, e_idx, -1))

        def _find_path(start_node, end_node, skip_edge_idx: int) -> Optional[List[Tuple[int, int]]]:
            queue = [start_node]
            prev_node: Dict[object, Optional[object]] = {start_node: None}
            prev_edge: Dict[object, Tuple[int, int]] = {}
            while queue:
                cur = queue.pop(0)
                if cur == end_node:
                    break
                for nxt, e_idx, sgn in adjacency.get(cur, []):
                    if e_idx == skip_edge_idx:
                        continue
                    if nxt in prev_node:
                        continue
                    prev_node[nxt] = cur
                    prev_edge[nxt] = (e_idx, sgn)
                    queue.append(nxt)
            if end_node not in prev_node:
                return None
            path: List[Tuple[int, int]] = []
            cur = end_node
            while prev_node[cur] is not None:
                e_idx, sgn = prev_edge[cur]
                path.append((e_idx, sgn))
                cur = prev_node[cur]
            path.reverse()
            return path

        loops: List[List[Tuple[int, int]]] = []
        seen_loop_keys = set()
        for e_idx, (u, v) in enumerate(branch_connects):
            # 用“v -> u 的树外路径 + e_idx 的 u -> v”构造一个闭合环
            alt_path = _find_path(v, u, skip_edge_idx=e_idx)
            if not alt_path:
                continue
            loop_edges = alt_path + [(e_idx, +1)]
            key = frozenset([k for k, _ in loop_edges])
            if key in seen_loop_keys:
                continue
            seen_loop_keys.add(key)
            loops.append(loop_edges)

        # 初始流量：优先读取外部提供；没有就按边界节点做均分初值
        q = np.zeros(n_branch, dtype=float)
        q_eps = max(1e-8, abs(q_total) * 1e-8)
        has_seed = False
        for i, br in enumerate(branches):
            for key in ("Q_init", "Q", "flow", "flow_m3s", "q"):
                if key in br and br[key] is not None:
                    try:
                        q[i] = float(br[key])
                        has_seed = True
                        break
                    except Exception:
                        continue

        # 解析节点连续方程约束
        node_constraints: List[Tuple[List[int], List[int], float]] = []
        for jn in (junction_nodes or []):
            if not isinstance(jn, dict):
                continue
            inflow_idx = _resolve_branch_indices(jn.get("inflows", []))
            outflow_idx = _resolve_branch_indices(jn.get("outflows", []))
            ext = jn.get("external_flow", jn.get("external", None))
            if ext is None:
                # 若节点未声明外部流量，默认：
                # - 纯出流节点（源）取 +Q_total
                # - 纯入流节点（汇）取 -Q_total
                # - 其余内部节点取 0
                if (len(inflow_idx) == 0) and (len(outflow_idx) > 0):
                    ext_flow = q_total
                elif (len(inflow_idx) > 0) and (len(outflow_idx) == 0):
                    ext_flow = -q_total
                else:
                    ext_flow = 0.0
            else:
                try:
                    ext_flow = float(ext)
                except Exception:
                    ext_flow = 0.0
            node_constraints.append((inflow_idx, outflow_idx, float(ext_flow)))

        if not has_seed:
            # 用边界节点初始化：源节点各出流均分，汇节点各入流均分
            for inflow_idx, outflow_idx, ext_flow in node_constraints:
                if ext_flow > 0.0 and len(outflow_idx) > 0:
                    share = ext_flow / len(outflow_idx)
                    for bi in outflow_idx:
                        if abs(q[bi]) <= q_eps:
                            q[bi] = share
                elif ext_flow < 0.0 and len(inflow_idx) > 0:
                    share = abs(ext_flow) / len(inflow_idx)
                    for bi in inflow_idx:
                        if abs(q[bi]) <= q_eps:
                            q[bi] = share
            # 若仍全为零，给一个极小对称初值避免导数退化
            if float(np.max(np.abs(q))) <= q_eps:
                q[:] = q_total / max(n_branch, 1)

        # 节点连续方程投影：把不平衡误差分配到该节点的出流（或入流）
        def _enforce_node_continuity(n_sweeps: int = 2) -> float:
            max_err = 0.0
            for _ in range(max(1, n_sweeps)):
                for inflow_idx, outflow_idx, ext_flow in node_constraints:
                    if (len(inflow_idx) == 0) and (len(outflow_idx) == 0):
                        continue
                    q_in = float(np.sum([q[k] for k in inflow_idx])) if inflow_idx else 0.0
                    q_out = float(np.sum([q[k] for k in outflow_idx])) if outflow_idx else 0.0
                    err = q_in - q_out - ext_flow
                    max_err = max(max_err, abs(err))
                    if abs(err) <= 1e-14:
                        continue
                    if outflow_idx:
                        corr = err / len(outflow_idx)
                        for k in outflow_idx:
                            q[k] += corr
                    elif inflow_idx:
                        corr = -err / len(inflow_idx)
                        for k in inflow_idx:
                            q[k] += corr
            return max_err

        _enforce_node_continuity(n_sweeps=3)

        # 用曼宁阻力线性化构建分支“等效阻抗”：
        # h_L ≈ R_branch * Q*|Q|，其中 R_branch = Σ[n^2*L/(A^2*R_h^(4/3))]
        if self._reach_lengths is not None and len(self._reach_lengths) > 0:
            _dx_default = float(np.mean([max(float(v), 0.1) for v in self._reach_lengths]))
        else:
            _n_ref = len(self._bed_elevations) if self._bed_elevations is not None else max(
                max((max(xs) for xs in branch_xs), default=1) + 1, 2
            )
            _dx_default = float(self.length) / max(_n_ref - 1, 1)
        _dx_default = max(_dx_default, 0.1)

        def _local_n(idx: int) -> float:
            n_local = self.n
            if self._manning_ns is not None and idx < len(self._manning_ns):
                try:
                    nv = self._manning_ns[idx]
                    if nv is not None and float(nv) > 0.0:
                        n_local = float(nv)
                except Exception:
                    pass
            return float(max(n_local, 1e-4))

        def _branch_resistance(branch_idx: int, q_abs: float) -> float:
            xs_idx = branch_xs[branch_idx]
            if len(xs_idx) == 0:
                return 1e6
            q_ref = max(q_abs, abs(q_total) / max(n_branch, 1) * 0.25, 1e-4)
            seg_idx = xs_idx[:-1] if len(xs_idx) > 1 else xs_idx
            coef = 0.0
            for idx in seg_idx:
                if idx < 0:
                    continue
                try:
                    y_crit = self._compute_critical_depth(q_ref, idx)
                    h_ref = max(1.2 * float(y_crit), 0.05)
                except Exception:
                    h_ref = 0.5
                try:
                    A, _P, Rh, _T = self._get_geometry(h_ref, idx)
                    A = max(float(A), 1e-6)
                    Rh = max(float(Rh), 1e-6)
                except Exception:
                    A = max(self.B * h_ref, 1e-6)
                    Rh = max(h_ref, 1e-6)
                if self._reach_lengths is not None and idx < len(self._reach_lengths):
                    dx = max(float(self._reach_lengths[idx]), 0.1)
                else:
                    dx = _dx_default
                n_loc = _local_n(idx)
                coef += (n_loc ** 2) * dx / max(A ** 2 * Rh ** (4.0 / 3.0), 1e-12)
            return float(max(coef, 1e-9))

        # Hardy-Cross 主迭代
        max_iter = 120
        tol_q = max(1e-6, abs(q_total) * 1e-6)
        converged = False
        max_loop_residual = 0.0
        max_mass_error = _enforce_node_continuity(n_sweeps=2)
        iter_used = 0

        if len(loops) == 0:
            # 无闭合环：只做节点连续修正后直接返回
            converged = max_mass_error <= tol_q
            iter_used = 0
        else:
            for it in range(1, max_iter + 1):
                iter_used = it
                max_corr = 0.0
                max_loop_residual = 0.0

                for loop_edges in loops:
                    numerator = 0.0
                    denominator = 0.0
                    for bi, sgn in loop_edges:
                        q_i = float(q[bi])
                        r_i = _branch_resistance(bi, abs(q_i))
                        h_i = r_i * q_i * abs(q_i)  # 沿分支方向的有符号损失
                        numerator += float(sgn) * h_i
                        denominator += 2.0 * r_i * max(abs(q_i), q_eps)

                    max_loop_residual = max(max_loop_residual, abs(numerator))
                    if denominator <= 1e-14:
                        continue

                    dQ = -numerator / denominator
                    # 数值稳定：限制单次校正幅度，避免环网大步震荡
                    dQ = float(np.clip(dQ, -0.5 * max(abs(q_total), 1.0), 0.5 * max(abs(q_total), 1.0)))
                    max_corr = max(max_corr, abs(dQ))
                    for bi, sgn in loop_edges:
                        q[bi] += float(sgn) * dQ

                max_mass_error = _enforce_node_continuity(n_sweeps=2)
                if max_corr <= tol_q and max_mass_error <= tol_q:
                    converged = True
                    break

        # 组装输出结果
        branch_res = []
        branch_hl = []
        branches_out = []
        for i, br in enumerate(branches):
            r_i = _branch_resistance(i, abs(float(q[i])))
            h_i = r_i * float(q[i]) * abs(float(q[i]))
            branch_res.append(float(r_i))
            branch_hl.append(float(h_i))
            bo = dict(br)
            bo["Q_m3s"] = float(q[i])
            bo["headloss_m"] = float(h_i)
            bo["resistance_coef"] = float(r_i)
            branches_out.append(bo)

        loops_out = []
        for lp in loops:
            loops_out.append(
                [{"branch_index": int(bi), "sign": int(sgn)} for bi, sgn in lp]
            )

        return {
            "converged": bool(converged),
            "iterations": int(iter_used),
            "branch_flows": [float(v) for v in q],
            "branch_headloss": branch_hl,
            "branch_resistance": branch_res,
            "branches": branches_out,
            "loops": loops_out,
            "max_loop_residual": float(max_loop_residual),
            "max_mass_error": float(max_mass_error),
        }



    # -----------------------------------------------------------------------
    # Lateral Weir (侧向堰) - 空间渐变流求解

    def _solve_lateral_weir(
        self,
        Q_upstream: float,
        W_downstream: float,
        weir_params: dict,
        xs_indices: list[int],
    ) -> dict:
        """侧向堰空间渐变流求解 (HEC-RAS Lateral Weir)。

        物理背景：侧向堰是空间渐变流 (Spatially Varied Flow with Decreasing
        Discharge)，主河道流量沿程因侧向溢出而减少。

        核心公式 (de Marchi 1934)：
            dQ/dx = -Cd * (2/3) * sqrt(2g) * h^(3/2)
            其中 h = WSE - crest_elevation（溢流水头，m）

        迭代策略（HEC-RAS Lateral Structure 两步 Picard）：
            1. 根据当前水面线，按 de Marchi 公式估算各堰段侧向溢流量，更新沿程 Q
            2. 固定 Q 后，用标准步能量方程从下游向上游推算水面高程 W
            3. 外层迭代，直到 W 与 Q 同时收敛

        Args:
            Q_upstream: 上游来流量 (m^3/s)
            W_downstream: 下游边界水面高程 (m)
            weir_params: 侧向堰参数字典，包含：
                weir_coef (float): 堰流系数 Cd，默认 0.36（自由流宽顶堰 SI 单位）
                crest_elevation_m (float): 堰顶绝对高程 (m)
                weir_length_m (float): 堰总长度 (m)，0 则按 reach_lengths 自动求和
                start_xs (int): 堰起始断面全局索引（含）
                end_xs (int): 堰结束断面全局索引（含）
                tailwater_elevation_m (float, 可选): 侧向尾水高程，Villemonte 淹没修正
            xs_indices: 参与计算的断面全局索引列表（上游到下游顺序）

        Returns:
            dict 包含：
                W (np.ndarray): 各断面水面高程 (m)
                Q (np.ndarray): 各断面流量 (m^3/s)，沿程递减
                Q_lateral (np.ndarray): 各断面累计侧向溢流量 (m^3/s)
                converged (bool): 外层迭代是否收敛
                iterations (int): 实际迭代次数
                method (str): 固定值 "lateral_weir"
        """
        from scipy.optimize import brentq  # 文件顶部已导入，此处标注来源

        g = self.g
        n_xs = len(xs_indices)

        # 边界情况：无断面或只有一个断面，直接返回
        if n_xs == 0:
            return {
                "W": np.array([], dtype=float),
                "Q": np.array([], dtype=float),
                "Q_lateral": np.array([], dtype=float),
                "converged": True,
                "iterations": 0,
                "method": "lateral_weir",
            }
        if n_xs == 1:
            return {
                "W": np.array([float(W_downstream)], dtype=float),
                "Q": np.array([float(Q_upstream)], dtype=float),
                "Q_lateral": np.array([0.0], dtype=float),
                "converged": True,
                "iterations": 1,
                "method": "lateral_weir",
            }

        # ---- 解析堰参数 ----
        Cd = float(weir_params.get("weir_coef", 0.36))
        crest_elev = float(weir_params["crest_elevation_m"])
        weir_length_cfg = float(weir_params.get("weir_length_m", 0.0))
        start_xs_idx = int(weir_params["start_xs"])
        end_xs_idx = int(weir_params["end_xs"])
        if start_xs_idx > end_xs_idx:
            # 自动纠正顺序（允许调用方传入逆序索引）
            start_xs_idx, end_xs_idx = end_xs_idx, start_xs_idx

        # 可选侧向尾水高程，用于 Villemonte 淹没修正
        tw_raw = weir_params.get("tailwater_elevation_m", None)
        tailwater_elev: float | None = float(tw_raw) if tw_raw is not None else None

        # ---- 提取各断面的床面高程 ----
        # _bed_elevations 是全局绝对高程数组，通过 xs_indices[k] 寻址
        bed = np.array(
            [float(self._bed_elevations[xs_indices[k]]) for k in range(n_xs)],
            dtype=float,
        )

        # ---- 建立相邻断面间距表 (m) ----
        # dx_segs[j] = xs_indices[j] 到 xs_indices[j+1] 之间的沿河距离
        dx_segs = np.ones(n_xs - 1, dtype=float)
        for j in range(n_xs - 1):
            global_j = xs_indices[j]
            if (
                self._reach_lengths is not None
                and global_j < len(self._reach_lengths)
                and float(self._reach_lengths[global_j]) > 0
            ):
                dx_segs[j] = float(self._reach_lengths[global_j])
            else:
                # 无实际距离数据时，均分全河长作近似
                dx_segs[j] = max(self.length / max(n_xs - 1, 1), 1.0)

        # ---- 识别堰段（两端断面都在堰范围内的 j 段才参与溢流计算）----
        weir_seg_mask = np.zeros(n_xs - 1, dtype=bool)
        for j in range(n_xs - 1):
            xs_us_g = xs_indices[j]
            xs_ds_g = xs_indices[j + 1]
            if (
                start_xs_idx <= xs_us_g <= end_xs_idx
                and start_xs_idx <= xs_ds_g <= end_xs_idx
            ):
                weir_seg_mask[j] = True

        # 堰段有效长度：若设定了 weir_length_m，则按比例缩放各段距离使总和等于设定值
        dx_weir = np.where(weir_seg_mask, dx_segs, 0.0).copy()
        if weir_length_cfg > 0.0:
            total_weir_nat = float(np.sum(dx_weir))
            if total_weir_nat > 1e-6:
                dx_weir *= weir_length_cfg / total_weir_nat

        # ---- 局部损失系数辅助函数 ----
        _def_cc, _def_ec = 0.1, 0.3

        def _get_cc(k: int) -> float:
            """取第 k 个本地断面的收缩损失系数；不可用时回退为 0.1。"""
            gi = xs_indices[k]
            if self._contraction_coefs and gi < len(self._contraction_coefs):
                v = self._contraction_coefs[gi]
                if v is not None and float(v) >= 0:
                    return float(v)
            return _def_cc

        def _get_ec(k: int) -> float:
            """取第 k 个本地断面的扩散损失系数；不可用时回退为 0.3。"""
            gi = xs_indices[k]
            if self._expansion_coefs and gi < len(self._expansion_coefs):
                v = self._expansion_coefs[gi]
                if v is not None and float(v) >= 0:
                    return float(v)
            return _def_ec

        # ---- 初始化水位和流量 ----
        # 初始猜测：以下游水深叠加到各断面床面高程（近似平水面，后续迭代修正）
        h_ds_init = max(W_downstream - bed[-1], 1e-3)
        W_old = bed + h_ds_init
        W_old[-1] = W_downstream  # 强制下游边界

        Q_old = np.full(n_xs, float(Q_upstream), dtype=float)
        Q_lateral_old = np.zeros(n_xs, dtype=float)

        converged = False
        it = 0
        max_outer_iter = 50
        relax = 0.7  # 外层 Picard 松弛因子，防止 W 振荡

        for it in range(1, max_outer_iter + 1):

            # ================================================================
            # 第一步：根据当前水面线，按 de Marchi 公式更新沿程流量 Q
            # ================================================================
            Q_new = np.full(n_xs, float(Q_upstream), dtype=float)
            Q_lateral_new = np.zeros(n_xs, dtype=float)
            q_lat_cum = 0.0  # 累计侧向溢出流量 (m^3/s)

            for j in range(n_xs - 1):
                dQ_seg = 0.0
                if weir_seg_mask[j] and dx_weir[j] > 1e-9:
                    # 以本段上游断面 WSE 代表整段溢流水头（前向差分近似）
                    H_w = max(float(W_old[j]) - crest_elev, 0.0)
                    if H_w > 1e-9:
                        # de Marchi 公式：dQ = Cd*(2/3)*sqrt(2g)*h^1.5 * dx_weir
                        dQ_seg = (
                            Cd * (2.0 / 3.0) * np.sqrt(2.0 * g)
                            * (H_w ** 1.5) * dx_weir[j]
                        )

                        # Villemonte (1947) 淹没修正（仅在提供尾水高程时启用）
                        if tailwater_elev is not None:
                            H_tw = max(tailwater_elev - crest_elev, 0.0)
                            subm = H_tw / H_w  # 淹没比
                            if subm > 0.67:
                                if subm >= 1.0:
                                    dQ_seg = 0.0  # 完全淹没
                                else:
                                    # 部分淹没修正：Cs = (1 - subm^1.5)^0.385
                                    dQ_seg *= max((1.0 - subm ** 1.5) ** 0.385, 0.0)

                # 限制：单段溢流不超过上游可用流量，防止 Q 出现负值
                dQ_seg = float(np.clip(dQ_seg, 0.0, max(float(Q_new[j]), 0.0)))
                q_lat_cum += dQ_seg

                # 下一断面流量 = 上游流量 - 本段侧向溢出量（空间渐变流核心）
                Q_new[j + 1] = max(float(Q_new[j]) - dQ_seg, 0.0)
                Q_lateral_new[j + 1] = q_lat_cum

            # ================================================================
            # 第二步：固定 Q_new，用标准步能量方程从下游向上游推算 W
            # ================================================================
            W_calc = np.zeros(n_xs, dtype=float)
            W_calc[-1] = W_downstream  # 下游边界条件

            for j in range(n_xs - 2, -1, -1):
                i_us = xs_indices[j]       # 上游断面全局索引
                i_ds = xs_indices[j + 1]   # 下游断面全局索引
                bed_us = float(bed[j])
                bed_ds = float(bed[j + 1])
                dx = float(dx_segs[j])

                Q_us = float(Q_new[j])
                Q_ds = float(Q_new[j + 1])
                W_ds = float(W_calc[j + 1])

                # 下游断面水力量（本迭代内固定，不随上游猜测值变化）
                h_ds_loc = max(W_ds - bed_ds, 1e-6)
                A_ds_loc, _, _, _ = self._get_geometry(h_ds_loc, i_ds)
                A_ds_loc = max(float(A_ds_loc), 1e-12)
                K_ds_loc, alpha_ds_loc = self._compute_subdivided_conveyance(h_ds_loc, i_ds)
                K_ds_loc = max(float(K_ds_loc), 1e-12)
                V_ds_loc = Q_ds / A_ds_loc
                vh_ds_loc = float(alpha_ds_loc) * V_ds_loc ** 2 / (2.0 * g)

                cc_j = _get_cc(j)
                ec_j = _get_ec(j)

                def _energy_residual(W_us_val: float) -> float:
                    """能量方程残差（与 _solve_standard_step_variable_xs 保持一致）。

                    残差 = (上游总能量头) - (下游总能量头) - 摩阻损失 - 局部损失
                    """
                    h_us_r = max(W_us_val - bed_us, 1e-6)
                    A_us_r, _, _, _ = self._get_geometry(h_us_r, i_us)
                    A_us_r = max(float(A_us_r), 1e-12)
                    K_us_r, alpha_us_r = self._compute_subdivided_conveyance(h_us_r, i_us)
                    K_us_r = max(float(K_us_r), 1e-12)
                    V_us_r = Q_us / A_us_r
                    vh_us_r = float(alpha_us_r) * V_us_r ** 2 / (2.0 * g)
                    # HEC-RAS 平均输水率：Sf_avg = ((Q_us+Q_ds)/(K_us+K_ds))^2
                    Sf_avg_r = min(
                        ((Q_us + Q_ds) / (K_us_r + K_ds_loc)) ** 2,
                        1.0,
                    )
                    h_f_r = dx * Sf_avg_r
                    # 局部损失：速度水头增大取收缩系数，减小取扩散系数
                    h_e_r = (
                        cc_j * (vh_us_r - vh_ds_loc)
                        if vh_us_r > vh_ds_loc
                        else ec_j * (vh_ds_loc - vh_us_r)
                    )
                    return (W_us_val + vh_us_r) - (W_ds + vh_ds_loc) - h_f_r - h_e_r

                # 计算临界水位，作为 brentq 下界（确保找到亚临界解而非超临界解）
                h_crit_us = float(self._compute_critical_depth(max(Q_us, 1e-9), i_us))
                W_lo = max(W_ds, bed_us + h_crit_us)
                W_hi_n = max(W_lo + 1e-4, W_ds + 20.0)
                W_hi_e = max(W_lo + 1e-4, W_ds + 60.0)

                W_us_solved: float
                _ok = False
                try:
                    f_lo = _energy_residual(W_lo)
                    f_hi_n = _energy_residual(W_hi_n)
                    if np.isfinite(f_lo) and np.isfinite(f_hi_n) and f_lo * f_hi_n <= 0.0:
                        # 窄区间存在变号，直接 brentq 求根
                        W_us_solved = float(
                            brentq(_energy_residual, W_lo, W_hi_n, xtol=1e-6, maxiter=100)
                        )
                        _ok = True
                    else:
                        # 扩展到宽区间再试一次
                        f_hi_e = _energy_residual(W_hi_e)
                        if (
                            np.isfinite(f_lo)
                            and np.isfinite(f_hi_e)
                            and f_lo * f_hi_e <= 0.0
                        ):
                            W_us_solved = float(
                                brentq(_energy_residual, W_lo, W_hi_e, xtol=1e-6, maxiter=100)
                            )
                            _ok = True
                except Exception:
                    _ok = False

                if not _ok:
                    # 兜底：离散扫描 121 点，取残差绝对值最小的近似解
                    scan_ws = np.linspace(W_lo, W_hi_e, 121)
                    scan_rs = np.array(
                        [abs(_energy_residual(wv)) for wv in scan_ws], dtype=float
                    )
                    W_us_solved = float(scan_ws[int(np.argmin(scan_rs))])

                # 保证上游水位不低于临界水位（HEC-RAS 混合流模式默认取临界深度）
                W_us_solved = max(W_us_solved, bed_us + h_crit_us)
                W_calc[j] = W_us_solved

            # ================================================================
            # 第三步：外层松弛更新 W，检查双收敛条件
            # ================================================================
            # W_relaxed = (1-relax)*W_old + relax*W_calc，防止水位振荡不收敛
            W_new_relaxed = (1.0 - relax) * W_old + relax * W_calc
            W_new_relaxed[-1] = W_downstream  # 强制下游边界

            delta_W = float(np.max(np.abs(W_new_relaxed - W_old)))
            delta_Q = float(
                np.max(np.abs(Q_new - Q_old)) / max(abs(Q_upstream), 1.0)
            )

            W_old = W_new_relaxed
            Q_old = Q_new.copy()
            Q_lateral_old = Q_lateral_new.copy()

            # 双收敛条件：水位变化 < 0.1 mm 且流量变化 < 0.01%
            if delta_W < 1e-4 and delta_Q < 1e-4:
                converged = True
                break

        return {
            "W": W_old,
            "Q": Q_old,
            "Q_lateral": Q_lateral_old,
            "converged": converged,
            "iterations": it,
            "method": "lateral_weir",
        }

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



    # Stream Junction Energy Method (HEC-RAS TRM, River/Stream Junctions)

    def _solve_junction(
        self,
        Q_total: float,
        W_downstream: float,
        branches: list,
        bed_junction: float,
        max_iter: int = 50,
        tol: float = 1e-4,
    ) -> dict:
        """HEC-RAS Stream Junction Energy Method (TRM River/Stream Junctions).

        汊口所有分支 WSE 一致（WSE_junction），按输水能力 K 分配流量，迭代收敛。

        Args:
            Q_total: 汊口总流量 (m^3/s)
            W_downstream: 下游控制水面高程 (m)
            branches: list[dict], 每项含:
                xs_indices (list[int]): 断面索引，[0]=汊口近端，[-1]=远端
                Q_fraction (float): 初始流量分配比例
                is_outflow (bool): True=分流，False=合流
                W_boundary (float): 外端边界水面高程 (m)
            bed_junction: 汊口床面高程 (m)
            max_iter: 最大迭代次数
            tol: 收敛容差 (m)
        Returns:
            dict(WSE_junction, Q_branches, converged, iterations, EGL_branches[, warning])
        """
        n_br = len(branches)
        if n_br == 0:
            return {
                'WSE_junction': float(max(W_downstream, bed_junction + 1e-4)),
                'Q_branches': [], 'converged': True, 'iterations': 0, 'EGL_branches': [],
            }

        Q_total_abs = max(float(Q_total), 0.0)
        bed_arr = np.asarray(self._bed_elevations, dtype=float) if self._bed_elevations is not None else None

        def _reach_dx(ia, ib):
            """获取两断面之间步长，优先使用 HEC-RAS 实际河长。"""
            if ia == ib:
                return 0.1
            i_min = min(ia, ib)
            if self._reach_lengths is not None and i_min < len(self._reach_lengths):
                try:
                    return max(float(self._reach_lengths[i_min]), 0.1)
                except Exception:
                    pass
            if bed_arr is not None and len(bed_arr) > 1:
                return max(float(self.length) / float(max(len(bed_arr) - 1, 1)), 0.1)
            return 1.0

        def _kah(wse, idx):
            """给定绝对水位与断面索引，返回 (K, alpha, A)。"""
            if bed_arr is not None and 0 <= idx < len(bed_arr):
                h = max(float(wse) - float(bed_arr[idx]), 0.01)
            else:
                h = max(float(wse) - float(bed_junction), 0.01)
            K, alpha = self._compute_subdivided_conveyance(h, idx)
            A = self._get_geometry(h, idx)[0]
            return float(max(K, 1e-9)), float(max(alpha, 1.0)), float(max(A, 1e-9))

        def _minor_loss(vu, vd, ix):
            """局部损失：加速用收缩系数，减速用扩散系数（HEC-RAS TRM 第 2 章）。"""
            cc = 0.1
            ec = 0.3
            if self._contraction_coefs is not None and ix < len(self._contraction_coefs):
                try:
                    cc = float(self._contraction_coefs[ix])
                except Exception:
                    pass
            if self._expansion_coefs is not None and ix < len(self._expansion_coefs):
                try:
                    ec = float(self._expansion_coefs[ix])
                except Exception:
                    pass
            return cc * (vu - vd) if vu > vd else ec * (vd - vu)

        def _solve_step_known_ds(q, ius, ids, Wds):
            """已知下游水位，标准步进求上游水位（亚临界，逆水流方向）。"""
            dx = _reach_dx(ius, ids)
            Kds, ads, Ads = _kah(Wds, ids)
            Vds = q / Ads
            vhds = ads * Vds ** 2 / (2.0 * self.g)
            if bed_arr is not None and ius < len(bed_arr):
                bed_us = float(bed_arr[ius])
            else:
                bed_us = float(bed_junction)

            def _res(Wu):
                Kus, aus, Aus = _kah(Wu, ius)
                Vus = q / Aus
                vhus = aus * Vus ** 2 / (2.0 * self.g)
                # HEC-RAS 平均输水能力公式：Sf = (2Q/(K_us+K_ds))^2
                Sf = min(((q + q) / max(Kus + Kds, 1e-9)) ** 2, 1.0)
                return (Wu + vhus) - (Wds + vhds + dx * Sf + _minor_loss(vhus, vhds, min(ius, ids)))

            lo = max(bed_us + 1e-4, Wds - 20.0)
            hi = max(lo + 1e-3, Wds + 20.0)
            flo, fhi = _res(lo), _res(hi)
            expand = 0
            while np.isfinite(flo) and np.isfinite(fhi) and flo * fhi > 0.0 and expand < 8:
                lo = max(bed_us + 1e-4, lo - 10.0)
                hi += 10.0
                flo, fhi = _res(lo), _res(hi)
                expand += 1
            if np.isfinite(flo) and np.isfinite(fhi) and flo * fhi <= 0.0:
                return float(brentq(_res, lo, hi, xtol=1e-6, maxiter=100))
            return float(max(bed_us + 1e-4, Wds + dx * (q / max(Kds, 1e-9)) ** 2))

        def _solve_step_known_us(q, ius, ids, Wus):
            """已知上游水位，标准步进求下游水位（顺水流方向）。"""
            dx = _reach_dx(ius, ids)
            Kus, aus, Aus = _kah(Wus, ius)
            Vus = q / Aus
            vhus = aus * Vus ** 2 / (2.0 * self.g)
            if bed_arr is not None and ids < len(bed_arr):
                bed_ds = float(bed_arr[ids])
            else:
                bed_ds = float(bed_junction)

            def _res(Wd):
                Kds, ads, Ads = _kah(Wd, ids)
                Vds = q / Ads
                vhds = ads * Vds ** 2 / (2.0 * self.g)
                Sf = min(((q + q) / max(Kus + Kds, 1e-9)) ** 2, 1.0)
                return (Wus + vhus) - (Wd + vhds + dx * Sf + _minor_loss(vhus, vhds, min(ius, ids)))

            lo = max(bed_ds + 1e-4, Wus - 25.0)
            hi = max(lo + 1e-3, Wus + 5.0)
            flo, fhi = _res(lo), _res(hi)
            expand = 0
            while np.isfinite(flo) and np.isfinite(fhi) and flo * fhi > 0.0 and expand < 8:
                lo = max(bed_ds + 1e-4, lo - 10.0)
                hi += 10.0
                flo, fhi = _res(lo), _res(hi)
                expand += 1
            if np.isfinite(flo) and np.isfinite(fhi) and flo * fhi <= 0.0:
                return float(brentq(_res, lo, hi, xtol=1e-6, maxiter=100))
            return float(max(bed_ds + 1e-4, Wus - dx * (q / max(Kus, 1e-9)) ** 2))

        def _march_branch_to_junction(q, br):
            """从分支外端推进到汊口端，返回 (W_jct, EGL_jct, K_jct)。

            分流(is_outflow=True)：逆水流推进（已知下游出口，求上游汊口端水位）。
            合流(is_outflow=False)：顺水流推进（已知上游来水，求下游汊口端水位）。
            xs_indices[0]=汊口近端，xs_indices[-1]=边界远端。
            """
            xs = br.get('xs_indices', [])
            if not xs:
                Wj = float(max(W_downstream, bed_junction + 1e-4))
                Aj = max(1.0, self.B * max(Wj - bed_junction, 0.1))
                Vj = abs(q) / max(Aj, 1e-9)
                return float(Wj), float(Wj + Vj ** 2 / (2.0 * self.g)), 1.0

            path = [int(v) for v in xs]
            # pjct: 从边界远端推进到汊口近端的顺序
            pjct = list(reversed(path))
            is_outflow = bool(br.get('is_outflow', True))
            Wc = float(br.get('W_boundary', W_downstream))
            # 确保初始水位不低于床面
            if bed_arr is not None:
                oi = pjct[0]
                if 0 <= oi < len(bed_arr):
                    Wc = max(Wc, float(bed_arr[oi]) + 1e-4)

            for k in range(len(pjct) - 1):
                ic, inx = pjct[k], pjct[k + 1]
                if is_outflow:
                    # 分流：逆水流方向（已知下游出口，逐步求上游汊口端水位）
                    Wc = _solve_step_known_ds(abs(q), inx, ic, Wc)
                else:
                    # 合流：顺水流方向（已知上游来水，逐步求下游汊口端水位）
                    Wc = _solve_step_known_us(abs(q), ic, inx, Wc)
                if bed_arr is not None and 0 <= inx < len(bed_arr):
                    Wc = max(Wc, float(bed_arr[inx]) + 1e-4)

            ij = path[0]  # 汊口近端断面索引
            Kj, aj, Aj = _kah(Wc, ij)
            Vj = abs(q) / max(Aj, 1e-9)
            EGLj = float(Wc + aj * Vj ** 2 / (2.0 * self.g))
            return float(Wc), EGLj, float(Kj)

        # ── 初始化 ────────────────────────────────────────────────────────────
        # 归一化 Q_fraction，得到初始流量分配
        qf = np.array([max(float(br.get('Q_fraction', 0.0)), 0.0) for br in branches], dtype=float)
        if np.sum(qf) <= 0.0:
            qf = np.full(n_br, 1.0 / n_br, dtype=float)
        else:
            qf /= np.sum(qf)
        Qb = Q_total_abs * qf

        # 用汊口近端断面的 K 比例修正初始流量分配（HEC-RAS K-ratio 方法）
        Wj = float(max(W_downstream, bed_junction + 0.05))
        Ki = np.ones(n_br, dtype=float)
        for i, br in enumerate(branches):
            xs = br.get('xs_indices', [])
            if xs:
                ij = int(xs[0])
                try:
                    if bed_arr is not None and 0 <= ij < len(bed_arr):
                        hj = max(Wj - float(bed_arr[ij]), 0.01)
                    else:
                        hj = max(Wj - bed_junction, 0.01)
                    Kj, _ = self._compute_subdivided_conveyance(hj, ij)
                    Ki[i] = max(float(Kj), 1e-9)
                except Exception:
                    Ki[i] = 1.0
        Ks_init = np.sum(Ki)
        if Ks_init > 0.0:
            Qb = Q_total_abs * (Ki / Ks_init)

        # ── 主迭代（HEC-RAS Stream Junction Energy Method）────────────────────
        # 流程：
        # 1. 各分支从外端推进到汊口端，得各分支汊口端 EGL
        # 2. K 加权平均 EGL -> 新节点水位目标 W_target
        # 3. 在 W_target 下按 K 比例重新分配 Q_total -> Q_target
        # 4. 松弛更新（relax=0.6），检查收敛（EGL 离散度 + dW + dQ）
        EGL: list = [float('nan')] * n_br
        conv = False
        rl = 0.6  # 松弛因子，防止迭代震荡
        it = 0
        for it in range(1, max_iter + 1):
            Wbl: list = []
            EL: list = []
            KL: list = []
            for i, br in enumerate(branches):
                qi = float(max(Qb[i], 0.0))
                Wji, Ei, Ki2 = _march_branch_to_junction(qi, br)
                Wbl.append(Wji)
                EL.append(Ei)
                KL.append(max(Ki2, 1e-9))
            EGL = [float(v) for v in EL]

            # K 加权平均 EGL 作为新节点水位目标
            Ka = np.asarray(KL, dtype=float)
            Ks = float(np.sum(Ka))
            if Ks > 0:
                Wt = float(np.sum(Ka * np.asarray(EL, dtype=float)) / Ks)
            else:
                Wt = float(np.mean(EL))
            Wt = max(Wt, bed_junction + 1e-4)

            # 松弛更新节点水位
            Wn = (1.0 - rl) * Wj + rl * Wt

            # 在新节点水位下按 K 比例重新分配流量
            Kr = np.ones(n_br, dtype=float)
            for i, br in enumerate(branches):
                xs = br.get('xs_indices', [])
                if xs:
                    ij = int(xs[0])
                    if bed_arr is not None and 0 <= ij < len(bed_arr):
                        hj = max(Wn - float(bed_arr[ij]), 0.01)
                    else:
                        hj = max(Wn - bed_junction, 0.01)
                    try:
                        Kj, _ = self._compute_subdivided_conveyance(hj, ij)
                        Kr[i] = max(float(Kj), 1e-9)
                    except Exception:
                        Kr[i] = 1.0
            Krs = np.sum(Kr)
            if Krs > 0:
                Qt = Q_total_abs * (Kr / Krs)
            else:
                Qt = np.full(n_br, Q_total_abs / n_br, dtype=float)

            # 松弛更新流量
            Qn = (1.0 - rl) * Qb + rl * Qt

            # 收敛判断：EGL 离散度 + 节点水位变化 + 流量变化
            es = float(np.max(EL) - np.min(EL)) if len(EL) > 1 else 0.0
            dw = abs(Wn - Wj)
            dq = float(np.max(np.abs(Qn - Qb)))
            q_tol = max(1e-6, 1e-4 * max(Q_total_abs, 1.0))

            Wj = float(Wn)
            Qb = np.asarray(Qn, dtype=float)

            if es < tol and dw < tol and dq < q_tol:
                conv = True
                break

        # ── 返回结果 ──────────────────────────────────────────────────────────
        res = {
            'WSE_junction': float(Wj),
            'Q_branches': [float(v) for v in Qb.tolist()],
            'converged': conv,
            'iterations': it,
            'EGL_branches': [float(v) for v in EGL],
        }
        if not conv:
            res['warning'] = 'junction_solver_not_converged'
        return res



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
