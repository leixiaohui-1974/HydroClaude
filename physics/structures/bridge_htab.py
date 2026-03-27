"""桥梁 HTAB（水位-流量曲线族）独立生成器。

该模块不依赖 ``SteadyProfileSolver`` 实例，直接基于桥上下游桥面断面、
桥长、桥面高程、桥墩参数和糙率，生成与 ``StructureHTAB`` 兼容的评级曲线族。

实现策略遵循 HEC-RAS Bridge HTAB 的核心物理分区：

1. **低流态 / 非压流**：
   使用桥下游桥面断面（section 2）到桥上游桥面断面（section 3）的简化能量方程。
2. **高流态 / 压流**：
   当低弦被淹没（由 WSE 或 EGL 判别）后，改用孔口流 + 桥面漫顶堰流。
3. **HTAB 组装**：
   输出 free-flow 曲线和一组不同 TW 条件下的 submerged 曲线。

全部内部计算均使用 SI 单位：m, m², m³/s。
"""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np

from physics.property_table import (
    segment_area_perimeter,
    subdivided_conveyance_with_beta,
)
from solvers.unsteady_preissmann_solver import StructureHTAB


G = 9.81
EPS = 1.0e-9


@dataclass
class BridgeHTABParams:
    """生成桥梁 HTAB 所需的全部输入参数。"""

    us_stations: np.ndarray
    us_elevations: np.ndarray
    ds_stations: np.ndarray
    ds_elevations: np.ndarray
    us_bank_stations: tuple[float, float]
    ds_bank_stations: tuple[float, float]
    us_manning_n: list[float]
    ds_manning_n: list[float]
    bridge_length_m: float
    deck_elevation_m: float
    high_chord_m: float
    pier_stations_m: list[float]
    pier_widths_m: list[float]
    pier_top_elevations_m: list[float]
    pier_bottom_elevations_m: list[float]
    contraction_coef: float = 0.3
    expansion_coef: float = 0.5
    deck_weir_coef: float = 1.44
    max_submergence_ratio: float = 0.95
    submerged_inlet_cd: float = 0.34
    submerged_inlet_outlet_cd: float = 0.7
    use_energy: bool = True
    use_momentum: bool = False
    use_yarnell: bool = False
    use_eg_for_pressure: bool = False

    def __post_init__(self) -> None:
        self.us_stations = np.asarray(self.us_stations, dtype=float)
        self.us_elevations = np.asarray(self.us_elevations, dtype=float)
        self.ds_stations = np.asarray(self.ds_stations, dtype=float)
        self.ds_elevations = np.asarray(self.ds_elevations, dtype=float)

        if self.us_stations.size != self.us_elevations.size:
            raise ValueError("US stations/elevations 长度不一致")
        if self.ds_stations.size != self.ds_elevations.size:
            raise ValueError("DS stations/elevations 长度不一致")
        if self.us_stations.size < 2 or self.ds_stations.size < 2:
            raise ValueError("桥梁 HTAB 至少需要两个断面点")
        if len(self.us_manning_n) != 3 or len(self.ds_manning_n) != 3:
            raise ValueError("Manning n 必须按 [LOB, Channel, ROB] 提供 3 个值")

        n_piers = len(self.pier_stations_m)
        if not (
            len(self.pier_widths_m) == n_piers
            and len(self.pier_top_elevations_m) == n_piers
            and len(self.pier_bottom_elevations_m) == n_piers
        ):
            raise ValueError("桥墩参数长度不一致")

        if self.bridge_length_m <= 0.0:
            raise ValueError("bridge_length_m 必须为正")
        if self.high_chord_m < self.deck_elevation_m:
            raise ValueError("high_chord_m 不得低于 deck_elevation_m")


def _interp_elevation(stations: np.ndarray, elevations: np.ndarray, station: float) -> float:
    """按站号线性插值地面高程。"""
    return float(np.interp(station, stations, elevations))


def _pier_blockage_area(
    stations: np.ndarray,
    elevations: np.ndarray,
    water_level: float,
    params: BridgeHTABParams,
) -> tuple[float, float]:
    """计算给定断面在当前水位下的桥墩阻塞面积和有效阻塞宽度。"""
    area = 0.0
    width = 0.0
    for sta, pier_w, pier_top, pier_bot in zip(
        params.pier_stations_m,
        params.pier_widths_m,
        params.pier_top_elevations_m,
        params.pier_bottom_elevations_m,
    ):
        local_bed = _interp_elevation(stations, elevations, sta)
        wet_bottom = max(local_bed, pier_bot)
        wet_top = min(water_level, pier_top)
        sub_h = max(0.0, wet_top - wet_bottom)
        if sub_h <= 0.0:
            continue
        area += pier_w * sub_h
        width += pier_w
    return float(area), float(width)


def _section_width(stations: np.ndarray) -> float:
    return float(np.max(stations) - np.min(stations))


def _section_properties(
    stations: np.ndarray,
    elevations: np.ndarray,
    water_level: float,
    bank_stations: tuple[float, float],
    manning_n: list[float],
    params: BridgeHTABParams,
) -> dict[str, float]:
    """计算断面在指定水位下的面积、输水能力、速度系数等。"""
    left_bank, right_bank = bank_stations
    n_lob, n_ch, n_rob = manning_n

    area_total, perimeter_total = segment_area_perimeter(
        stations,
        elevations,
        water_level,
        float(np.min(stations)),
        float(np.max(stations)),
    )
    k_total, _, beta = subdivided_conveyance_with_beta(
        stations,
        elevations,
        water_level,
        left_bank,
        right_bank,
        n_lob,
        n_ch,
        n_rob,
    )

    pier_block_area, pier_block_width = _pier_blockage_area(
        stations,
        elevations,
        water_level,
        params,
    )

    area_eff = max(area_total - pier_block_area, EPS)
    blockage_ratio = min(max(pier_block_area / max(area_total, EPS), 0.0), 0.95)

    # 将桥墩影响折算到输水能力：K 近似随有效面积的 5/3 次方缩放。
    if area_total > EPS and k_total > EPS:
        area_ratio = max(area_eff / area_total, 0.05)
        k_eff = k_total * area_ratio ** (5.0 / 3.0)
    else:
        k_eff = EPS

    hydraulic_radius = area_total / max(perimeter_total, 1.0e-6) if area_total > EPS else 0.0
    velocity = 0.0
    top_width = max(_section_width(stations) - pier_block_width, 0.1)

    return {
        "area_total": float(area_total),
        "area_eff": float(area_eff),
        "perimeter": float(perimeter_total),
        "k_total": float(max(k_total, EPS)),
        "k_eff": float(max(k_eff, EPS)),
        "beta": float(max(beta, 1.0)),
        "hydraulic_radius": float(max(hydraulic_radius, 0.0)),
        "top_width": float(top_width),
        "pier_block_area": float(pier_block_area),
        "blockage_ratio": float(blockage_ratio),
        "velocity": float(velocity),
    }


def _compute_low_flow_residual(hw: float, Q: float, tw: float, params: BridgeHTABParams) -> float:
    """低流态简化能量方程残差。"""
    us = _section_properties(
        params.us_stations,
        params.us_elevations,
        hw,
        params.us_bank_stations,
        params.us_manning_n,
        params,
    )
    ds = _section_properties(
        params.ds_stations,
        params.ds_elevations,
        tw,
        params.ds_bank_stations,
        params.ds_manning_n,
        params,
    )

    v_us = Q / max(us["area_eff"], EPS)
    v_ds = Q / max(ds["area_eff"], EPS)
    us["velocity"] = v_us
    ds["velocity"] = v_ds

    sf_us = (Q / max(us["k_eff"], EPS)) ** 2
    sf_ds = (Q / max(ds["k_eff"], EPS)) ** 2
    hf = params.bridge_length_m * 0.5 * (sf_us + sf_ds)

    v_bridge = max(v_us, v_ds)
    blockage = max(us["blockage_ratio"], ds["blockage_ratio"])
    k_pier = min(1.5 * blockage + 2.0 * blockage ** 2, 1.5)
    h_pier = k_pier * v_bridge ** 2 / (2.0 * G)

    dv2 = v_us ** 2 - v_ds ** 2
    if dv2 >= 0.0:
        h_transition = params.contraction_coef * dv2 / (2.0 * G)
    else:
        h_transition = params.expansion_coef * abs(dv2) / (2.0 * G)

    lhs = hw + us["beta"] * v_us ** 2 / (2.0 * G)
    rhs = tw + ds["beta"] * v_ds ** 2 / (2.0 * G) + hf + h_pier + h_transition
    return float(lhs - rhs)


def _solve_low_flow_hw(Q: float, tw: float, params: BridgeHTABParams) -> float:
    """Newton-Raphson + 兜底二分法求低流态上游水位。"""
    bed_us = float(np.min(params.us_elevations))
    lower = max(tw, bed_us + 1.0e-4)
    guess = max(lower + 0.05, tw + 0.25)

    hw = guess
    for _ in range(20):
        f0 = _compute_low_flow_residual(hw, Q, tw, params)
        if abs(f0) < 1.0e-7:
            return max(hw, tw)
        dh = max(1.0e-4, 1.0e-4 * max(abs(hw), 1.0))
        fp = _compute_low_flow_residual(hw + dh, Q, tw, params)
        deriv = (fp - f0) / dh
        if abs(deriv) < 1.0e-8:
            break
        hw_new = hw - f0 / deriv
        hw_new = min(max(hw_new, lower), lower + 30.0)
        if abs(hw_new - hw) < 1.0e-6:
            return max(hw_new, tw)
        hw = hw_new

    lo = lower
    flo = _compute_low_flow_residual(lo, Q, tw, params)
    hi = max(hw, lo + 0.5)
    fhi = _compute_low_flow_residual(hi, Q, tw, params)
    for _ in range(30):
        if flo == 0.0:
            return max(lo, tw)
        if flo * fhi <= 0.0:
            break
        hi += 1.0
        fhi = _compute_low_flow_residual(hi, Q, tw, params)

    for _ in range(60):
        mid = 0.5 * (lo + hi)
        fm = _compute_low_flow_residual(mid, Q, tw, params)
        if abs(fm) < 1.0e-7 or abs(hi - lo) < 1.0e-6:
            return max(mid, tw)
        if flo * fm <= 0.0:
            hi = mid
            fhi = fm
        else:
            lo = mid
            flo = fm

    return max(0.5 * (lo + hi), tw)


def _compute_trigger_metric(hw: float, Q: float, params: BridgeHTABParams) -> float:
    """返回用于压流判别的上游控制高程（WSE 或 EGL）。"""
    us = _section_properties(
        params.us_stations,
        params.us_elevations,
        hw,
        params.us_bank_stations,
        params.us_manning_n,
        params,
    )
    v_us = Q / max(us["area_eff"], EPS)
    if params.use_eg_for_pressure:
        return float(hw + us["beta"] * v_us ** 2 / (2.0 * G))
    return float(hw)


def _compute_opening_geometry(params: BridgeHTABParams) -> tuple[float, float, float]:
    """估算桥下低弦以下有效开口面积、净宽和形心高程。"""
    us = _section_properties(
        params.us_stations,
        params.us_elevations,
        params.deck_elevation_m,
        params.us_bank_stations,
        params.us_manning_n,
        params,
    )
    ds = _section_properties(
        params.ds_stations,
        params.ds_elevations,
        params.deck_elevation_m,
        params.ds_bank_stations,
        params.ds_manning_n,
        params,
    )
    area_opening = max(min(us["area_eff"], ds["area_eff"]), 0.05)
    clear_width = max(min(us["top_width"], ds["top_width"]), 0.1)
    bottom = max(
        float(np.min(params.us_elevations)),
        float(np.min(params.ds_elevations)),
        min(params.pier_bottom_elevations_m) if params.pier_bottom_elevations_m else -1.0e9,
    )
    centroid = 0.5 * (bottom + params.deck_elevation_m)
    return float(area_opening), float(clear_width), float(centroid)


def _deck_weir_flow(hw: float, tw: float, crest: float, length: float, coef: float, params: BridgeHTABParams) -> float:
    """桥面漫顶堰流，含 Villemonte 下游淹没修正。"""
    head_up = max(hw - crest, 0.0)
    if head_up <= 0.0:
        return 0.0

    q_free = coef * length * head_up ** 1.5
    if tw <= crest:
        return float(q_free)

    sub_ratio = min(max((tw - crest) / max(head_up, EPS), 0.0), params.max_submergence_ratio)
    correction = max((1.0 - sub_ratio ** 1.5), 0.0) ** 0.385
    return float(q_free * correction)


def _high_flow_discharge(hw: float, tw: float, params: BridgeHTABParams) -> float:
    """给定 HW/TW 计算压流 + 漫顶总流量。"""
    area_opening, clear_width, centroid = _compute_opening_geometry(params)

    if tw >= params.deck_elevation_m:
        head = max(hw - tw, 0.0)
        q_open = params.submerged_inlet_outlet_cd * area_opening * np.sqrt(2.0 * G * head)
    else:
        head = max(hw - centroid, 0.0)
        q_open = params.submerged_inlet_cd * area_opening * np.sqrt(2.0 * G * head)

    q_weir = _deck_weir_flow(
        hw,
        tw,
        params.high_chord_m,
        clear_width,
        params.deck_weir_coef,
        params,
    )
    return float(q_open + q_weir)


def _solve_high_flow_hw(Q: float, tw: float, params: BridgeHTABParams) -> float:
    """二分法求压流工况下的上游水位。"""
    lower = max(tw, params.deck_elevation_m) + 1.0e-4
    upper = max(lower + 1.0, params.high_chord_m + 1.0)

    def residual(hw: float) -> float:
        return _high_flow_discharge(hw, tw, params) - Q

    f_lo = residual(lower)
    f_hi = residual(upper)
    for _ in range(40):
        if f_hi >= 0.0:
            break
        upper += 1.0
        f_hi = residual(upper)

    if f_lo >= 0.0:
        return lower

    for _ in range(80):
        mid = 0.5 * (lower + upper)
        f_mid = residual(mid)
        if abs(f_mid) < 1.0e-7 or abs(upper - lower) < 1.0e-6:
            return max(mid, tw)
        if f_mid >= 0.0:
            upper = mid
        else:
            lower = mid

    return max(0.5 * (lower + upper), tw)


def compute_bridge_hw(Q: float, tw: float, params: BridgeHTABParams) -> float:
    """根据给定流量和尾水位计算桥上游水位。

    Parameters
    ----------
    Q : float
        流量 (m³/s)，按正值处理。
    tw : float
        下游桥面断面尾水位 (m)。
    params : BridgeHTABParams
        桥梁 HTAB 参数。

    Returns
    -------
    float
        上游桥面断面水位 HW (m)。
    """
    Q_abs = abs(float(Q))
    if Q_abs <= 1.0e-12:
        return float(tw)

    if not params.use_energy and (params.use_momentum or params.use_yarnell):
        # 当前实现仅提供独立能量法 + 压流法；保留接口语义但不扩 scope。
        pass

    hw_low = _solve_low_flow_hw(Q_abs, tw, params)
    trigger = _compute_trigger_metric(hw_low, Q_abs, params)
    if trigger < params.deck_elevation_m:
        return max(hw_low, tw)

    hw_high = _solve_high_flow_hw(Q_abs, tw, params)
    return max(hw_high, hw_low, tw)


def _default_tw_bounds(params: BridgeHTABParams) -> tuple[float, float]:
    bed_ds = float(np.min(params.ds_elevations))
    tw_min = bed_ds
    tw_max = max(params.high_chord_m + 5.0, params.deck_elevation_m + 5.0)
    return tw_min, tw_max


def _default_q_max(params: BridgeHTABParams, tw_max: float) -> float:
    area_opening, clear_width, centroid = _compute_opening_geometry(params)
    head_pressure = max(params.high_chord_m + 5.0 - centroid, 0.5)
    q_pressure = params.submerged_inlet_cd * area_opening * np.sqrt(2.0 * G * head_pressure)
    q_weir = params.deck_weir_coef * clear_width * max(5.0, 0.5) ** 1.5
    return float(max(q_pressure + q_weir, 10.0))


def generate_bridge_htab(
    params: BridgeHTABParams,
    n_tw: int = 50,
    n_q: int = 20,
    q_max: float | None = None,
    tw_min: float | None = None,
    tw_max: float | None = None,
) -> StructureHTAB:
    """生成完整桥梁 HTAB 曲线族。

    输出数据格式与 ``StructureHTAB`` 完全兼容：

    - curve[0] 为 free-flow 曲线
    - curve[1..] 为不同尾水位下的 submerged 曲线
    - values 每行均为 ``[Q, HW]``，且已经是 SI 单位
    """
    if n_tw < 1:
        raise ValueError("n_tw 必须 >= 1")
    if n_q < 2:
        raise ValueError("n_q 必须 >= 2")

    tw_min_default, tw_max_default = _default_tw_bounds(params)
    tw_min = tw_min_default if tw_min is None else float(tw_min)
    tw_max = tw_max_default if tw_max is None else float(tw_max)
    if tw_max <= tw_min:
        raise ValueError("tw_max 必须大于 tw_min")

    if q_max is None:
        q_max = _default_q_max(params, tw_max)
    q_max = float(q_max)
    if q_max <= 0.0:
        raise ValueError("q_max 必须为正")

    q_values = np.linspace(0.0, q_max, n_q + 1)
    tw_levels = np.linspace(tw_min, tw_max, n_tw)

    curves: list[np.ndarray] = []

    # Free-flow 曲线：采用极低尾水位近似自由出流。
    free_tw = tw_min
    free_curve = np.zeros((n_q + 1, 2), dtype=float)
    for i, q in enumerate(q_values):
        hw = compute_bridge_hw(float(q), free_tw, params)
        if i > 0:
            hw = max(hw, free_curve[i - 1, 1])
        free_curve[i] = [q, max(hw, free_tw)]
    curves.append(free_curve)

    for tw in tw_levels:
        curve = np.zeros((n_q + 1, 2), dtype=float)
        curve[0] = [0.0, tw]
        last_hw = tw
        for i, q in enumerate(q_values[1:], start=1):
            hw = compute_bridge_hw(float(q), float(tw), params)
            hw = max(hw, last_hw, tw)
            curve[i] = [q, hw]
            last_hw = hw
        curves.append(curve)

    info = np.zeros((len(curves), 2), dtype=int)
    values = np.zeros((sum(len(c) for c in curves), 2), dtype=float)

    start = 0
    for i, curve in enumerate(curves):
        count = len(curve)
        info[i] = [start, count]
        values[start:start + count] = curve
        start += count

    return StructureHTAB(info, values, ft_to_m=1.0, cfs_to_m3s=1.0)
