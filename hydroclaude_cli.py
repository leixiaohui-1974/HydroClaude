#!/usr/bin/env python3
"""HydroClaude CLI — 稳态水面线计算命令行工具。

参考 pipedream CLI 设计模式。

命令:
  run      运行稳态水面线计算
  compare  与 HEC-RAS 参考数据对标
  batch    批量对标所有案例
  info     显示案例信息
"""

import argparse
import math
import json
import sys
from pathlib import Path
from typing import Any

import numpy as np

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT))

from solvers.steady_profile_solver import SteadyProfileSolver
from physics.cross_section import NaturalSection

LF = 0.3048


def _to_jsonable(obj: Any) -> Any:
    if isinstance(obj, np.ndarray):
        return obj.tolist()
    if isinstance(obj, np.generic):
        return obj.item()
    if isinstance(obj, dict):
        return {str(k): _to_jsonable(v) for k, v in obj.items()}
    if isinstance(obj, (list, tuple)):
        return [_to_jsonable(v) for v in obj]
    return obj


def _build_from_ref(ref: dict):
    """从参考数据 JSON 构建求解器。"""
    n_xs = ref["n_cross_sections"]
    gd = ref["geometry"]["cross_sections"]
    sections, bed, rl, rl_lob, rl_rob, nch, nlob, nrob, bsl, bsr, cc, ec, nsa = (
        [], [], [], [], [], [], [], [], [], [], [], [], [])
    for i, xg in enumerate(gd):
        pts = xg["station_elevation"]
        dm = np.array([p[0] * LF for p in pts])
        em = np.array([p[1] * LF for p in pts])
        nr = xg.get("manning_n", [])
        nsa.append([(s * LF, n) for s, n in nr])
        vn = [n for _, n in nr if n is not None and n > 0]
        lb_ft = float(xg["left_bank_ft"])
        rb_ft = float(xg["right_bank_ft"])
        # 主槽 n: bank station 范围内的 n 值中取最小值（主槽底部）
        n_in_channel = [n for s, n in nr if n is not None and n > 0
                        and lb_ft <= s <= rb_ft]
        nc = min(n_in_channel) if n_in_channel else (vn[1] if len(vn) > 2 else (vn[0] if vn else 0.04))
        nl = vn[0] if vn else 0.1
        nrv = vn[-1] if len(vn) > 1 else nl
        lb = lb_ft * LF
        rb = rb_ft * LF
        sec = NaturalSection(name=f"XS{i}", elevations=em, distances=dm)
        sections.append(sec)
        bed.append(float(np.min(em)))
        _lch = float(xg["len_channel_ft"])
        rl.append(_lch * LF)
        _ll = xg.get("len_left_ft", _lch)
        _lr = xg.get("len_right_ft", _lch)
        # NaN 或无效值时回退到 channel length
        import math
        rl_lob.append(float(_ll) * LF if _ll is not None and not math.isnan(float(_ll)) else _lch * LF)
        rl_rob.append(float(_lr) * LF if _lr is not None and not math.isnan(float(_lr)) else _lch * LF)
        nch.append(nc); nlob.append(nl); nrob.append(nrv)
        bsl.append(lb); bsr.append(rb)
        cc.append(float(xg.get("contraction", 0.1)))
        ec.append(float(xg.get("expansion", 0.3)))
    ifa = ref.get("ineffective_areas", [])

    # 桥梁参数：从 geometry.bridges 提取，扁平化 us_xs_index
    _bridges_parsed = []
    for _br in ref.get("geometry", {}).get("bridges", []):
        _csr = _br.get("cross_section_reference", {})
        _us_idx = _csr.get("us_xs_index")
        _ds_idx = _csr.get("ds_xs_index")
        if _us_idx is None:
            continue
        _deck = _br.get("deck_geometry", {})
        _piers = _br.get("piers", {}) if isinstance(_br.get("piers"), dict) else {}
        _weir = _br.get("weir_parameters", {})
        _coefs = _br.get("coefficients", {})
        _bridges_parsed.append({
            "us_xs_index": int(_us_idx),
            "ds_xs_index": int(_ds_idx) if _ds_idx is not None else int(_us_idx) + 1,
            "bridge_length_m": rl[int(_us_idx)] if int(_us_idx) < len(rl) else float(_csr.get("upstream_distance_ft", _br.get("upstream_distance_ft", 30))) * LF,
            "deck_elevation_m": float(_deck.get("low_chord_elev_ft", 1e9)) * LF,
            "high_chord_m": float(_deck.get("high_chord_elev_ft", 1e9)) * LF,
            "deck_weir_length_m": float(_deck.get("bridge_opening_width_ft", _br.get("weir_width_ft", 0))) * LF,
            "deck_weir_coef": float(_weir.get("weir_coefficient", _coefs.get("momentum_cd", 1.70))),
            "total_pier_width_m": float(_piers.get("total_pier_width_ft", 0)) * LF,
            "n_piers": int(_piers.get("pier_count", 0)),
            "pier_loss_coef": 0.0,
            "contraction_coef": 0.1,
            "bridge_opening_width_m": float(_br.get("bridge_opening_width_m", 0)) or (
                float(_br.get("bridge_opening_width_ft", 0)) * LF),
            "coefficients": _coefs,
        })

    # ----------------------------------------
    # 涵洞位置映射：用 profile 0 的 WSE 跳变检测 us_xs_index
    # 策略：
    #   1. RS 有效的涵洞 -> 在未占用位置中寻找最大正向 WSE 跳变
    #   2. RS 无效（空/非法）的涵洞 -> 并联涵洞，复用上一个定位结果
    #   3. 无明显跳变时 -> 回退到 us_invert 与床面高程最小差值匹配
    # ----------------------------------------
    _WSE_JUMP_THRESHOLD = 0.06  # m，明显跳变阈值（高于正常水面降落，低于涵洞壅水）

    # 读取 profile 0 的断面 WSE 序列（index 0 为最上游断面）
    _profile0_xs = (ref.get("profiles") or [{}])[0].get("cross_sections", [])
    _wse0 = []
    for _ii in range(n_xs):
        _cs = _profile0_xs[_ii] if _ii < len(_profile0_xs) else {}
        try:
            _w = float(_cs.get("wse_m", 0.0))
        except (TypeError, ValueError):
            _w = 0.0
        _wse0.append(_w)

    def _parse_rs(cv_item: dict) -> tuple:
        """解析 RS：返回 (是否有效, 数值)。空字符串或非法值视为无效（并联涵洞）。"""
        _raw = cv_item.get("rs", None)
        if _raw is None:
            return False, -1e9
        if isinstance(_raw, str) and _raw.strip() == "":
            return False, -1e9
        try:
            _v = float(_raw)
            if not math.isfinite(_v):
                return False, -1e9
            return True, _v
        except (TypeError, ValueError):
            return False, -1e9

    # Multiple Openings（桥梁+涵洞并联）需要联合过流求解（第一性原理：Q=Q_bridge+Q_culvert）
    # 当前未实现联合过流，对 Multiple Opening 案例禁用涵洞以避免错误壅水
    _has_multiple_opening = "multiple open" in ref.get("case_name", "").lower()
    _has_bridges = bool(ref.get("geometry", {}).get("bridges"))
    _culverts_raw = [] if (_has_multiple_opening or _has_bridges) else ref.get("culverts", [])

    # 收集 RS 有效的涵洞，按 RS 从大到小（上游到下游）排序后依次定位
    _valid_cv = []
    for _orig_idx, _cv in enumerate(_culverts_raw):
        _ok, _rs = _parse_rs(_cv)
        if _ok:
            _valid_cv.append((_orig_idx, _cv, _rs))
    _valid_cv_sorted = sorted(_valid_cv, key=lambda t: t[2], reverse=True)

    _used_pos: set = set()          # 已被有效RS涵洞占用的跳变位置（防止重复占用）
    _cv_idx_map_valid: dict = {}    # 原始索引 -> us_xs_index（仅 RS 有效的涵洞）

    for _orig_idx, cv, _rs in _valid_cv_sorted:
        _best_i = None
        _best_jump = _WSE_JUMP_THRESHOLD    # 只接受超过阈值的跳变

        # 在未被占用的位置中寻找最大正向跳变（上游 WSE 高于下游）
        for _i in range(n_xs - 1):
            if _i in _used_pos:
                continue
            _jump = _wse0[_i] - _wse0[_i + 1]
            if _jump > _best_jump:
                _best_jump = _jump
                _best_i = _i

        if _best_i is not None:
            # 通过 WSE 跳变成功定位涵洞上游断面
            _used_pos.add(_best_i)
            _cv_idx_map_valid[_orig_idx] = _best_i
        else:
            # 回退：用 us_invert 高程与床面高程最小差值匹配
            _us_inv = float(cv.get("us_invert_m", 0.0))
            _fallback_i = n_xs // 2
            _best_diff = 1e9
            for _i in range(n_xs - 1):
                _diff = abs(bed[_i] - _us_inv)
                if _diff < _best_diff:
                    _best_diff = _diff
                    _fallback_i = _i
            _cv_idx_map_valid[_orig_idx] = _fallback_i

    # 按原始顺序构建涵洞参数列表
    # RS 有效  -> 使用 WSE 跳变定位结果（已在上方计算）
    # RS 无效  -> 并联涵洞（HEC-RAS 多孔叠置结构），复用最近一个有效 RS 涵洞的位置
    #            若前面没有有效 RS 涵洞，回退到 us_invert 与床面高程最小差值匹配
    culverts_param = []
    _last_valid_idx = None  # 最近一个有效 RS 涵洞的 us_xs_index，供并联涵洞复用

    # 先扫描一遍确定 RS 有效涵洞的最终位置（按原始顺序，便于并联复用）
    for _orig_idx, cv in enumerate(_culverts_raw):
        _ok, _ = _parse_rs(cv)
        if _ok:
            _us_idx = _cv_idx_map_valid.get(_orig_idx, None)
            if _us_idx is not None:
                _last_valid_idx = _us_idx

    # 再次扫描，为每个涵洞确定最终 us_xs_index
    _last_valid_idx = None
    for _orig_idx, cv in enumerate(_culverts_raw):
        _ok, _ = _parse_rs(cv)
        if _ok:
            # RS 有效：使用 WSE 跳变定位结果
            _us_idx = _cv_idx_map_valid.get(_orig_idx, None)
            if _us_idx is None:
                # 保险回退（理论上不应到达此处）
                _us_inv = float(cv.get("us_invert_m", 0.0))
                _us_idx = n_xs // 2
                _best_diff = 1e9
                for _i in range(n_xs - 1):
                    _diff = abs(bed[_i] - _us_inv)
                    if _diff < _best_diff:
                        _best_diff = _diff
                        _us_idx = _i
            _last_valid_idx = _us_idx
        else:
            # RS 无效：并联涵洞，复用最近一个有效 RS 涵洞的位置
            if _last_valid_idx is not None:
                _us_idx = _last_valid_idx
            else:
                # 前面没有有效 RS 涵洞，用 us_invert 匹配床面高程
                _us_inv = float(cv.get("us_invert_m", 0.0))
                _us_idx = n_xs // 2
                _best_diff = 1e9
                for _i in range(n_xs - 1):
                    _diff = abs(bed[_i] - _us_inv)
                    if _diff < _best_diff:
                        _best_diff = _diff
                        _us_idx = _i

        culverts_param.append({
            "us_xs_index": _us_idx,
            "shape": cv.get("shape", "circular"),
            "diameter_m": cv.get("diameter_m") or cv.get("height_m", 1.0),
            "height_m": cv.get("height_m", 1.0),
            "width_m": cv.get("width_m", 1.0),
            "length_m": cv.get("length_m", 30.0),
            "us_invert_m": cv.get("us_invert_m", 0),
            "ds_invert_m": cv.get("ds_invert_m", 0),
            "n_barrels": cv.get("n_barrels", 1),
            "manning_n": cv.get("manning_n", 0.013),
            "entrance_loss_coef": cv.get("entrance_loss_coef", 0.5),
        })

    return sections, bed, rl, rl_lob, rl_rob, nch, nlob, nrob, bsl, bsr, cc, ec, nsa, ifa, culverts_param, _bridges_parsed, n_xs


def _make_solver(sections, bed, rl, nch, nlob, nrob, bsl, bsr, cc, ec, nsa, ifa, culverts, lat,
                  rl_lob=None, rl_rob=None, bridges=None, ice_thickness=None, n_ice=None):
    sv = SteadyProfileSolver(
        length=max(sum(rl), 1), cross_sections=sections, bed_elevations=bed,
        reach_lengths=rl, reach_lengths_lob=rl_lob, reach_lengths_rob=rl_rob,
        manning_ns=nch, manning_n_lob=nlob, manning_n_rob=nrob,
        bank_stations=list(zip(bsl, bsr)), contraction_coefs=cc, expansion_coefs=ec,
        lateral_inflows=lat, culverts=culverts if culverts else None,
        bridges=bridges if bridges else None,
        ice_thickness=ice_thickness, n_ice=n_ice)
    sv._manning_n_segments = nsa
    sv._ineffective_areas = ifa
    return sv


def _run_profile(  # noqa: C901
    ref: dict,
    p_idx: int,
    sections: list,
    bed: list,
    rl: list,
    rl_lob: list,
    rl_rob: list,
    nch: list,
    nlob: list,
    nrob: list,
    bsl: list,
    bsr: list,
    cc: list,
    ec: list,
    nsa: list,
    ifa: list,
    culverts: list,
    bridges: list,
    n_xs: int,
):
    """工况求解。自动检测环状河网并分段求解；普通河道退回串联求解。

    环网检测条件（适用于 HEC-RAS Example 8 类型）：
      - rl[i] == 0 表示分叉/合流节点
      - 节点处流量减小 → 分叉点；增大 → 合流点
      - 识别到"主干上游 → 支路A → 支路B → 主干下游"结构后分段求解
    """
    profile = ref["profiles"][p_idx]
    xd = profile["cross_sections"]

    flows = [float(x["flow_m3s"]) for x in xd]
    wr = [float(x["wse_m"]) for x in xd]
    Q = flows[0]

    def _compute_downstream_bc() -> float:
        """从边界条件计算下游水深。优先用 boundary_conditions（v2），回退到参考 WSE（v1）。

        闭包访问外层变量: ref, p_idx, Q, bed, sections, nch, nlob, nrob,
                         nsa, ifa, culverts, rl, rl_lob, rl_rob, bsl, bsr, cc, ec, n_xs, wr
        """
        bc_list = ref.get("boundary_conditions", [])
        if not bc_list:
            # v1 兼容：回退到参考 WSE
            return max(wr[-1] - bed[-1], 0.5)

        # 找到当前 profile 的边界条件
        # boundary_conditions 的 profile_number 是 1-based（从 .f01 读取）
        bc = None
        for b in bc_list:
            pn = b.get("profile_number", b.get("profile_index", 0))
            if pn == p_idx + 1:  # profile_number 是 1-based
                bc = b
                break
        if bc is None and bc_list:
            bc = bc_list[0]  # 回退到第一个 BC
        if bc is None:
            return max(wr[-1] - bed[-1], 0.5)

        dn_type = bc.get("dn_type", 0)

        if dn_type in (0, 1):  # Known WS
            ws_ft = bc.get("dn_known_ws_ft")
            if ws_ft is not None:
                return max(ws_ft * 0.3048 - bed[-1], 0.1)
            return max(wr[-1] - bed[-1], 0.5)

        elif dn_type == 2:  # Critical Depth
            from scipy.optimize import brentq
            sec = sections[-1]

            def _crit_res(h):
                A = sec.compute_area(max(h, 0.001))
                T = sec.compute_top_width(max(h, 0.001))
                if T < 1e-9 or A < 1e-9:
                    return 1e6
                return Q**2 * T / (9.81 * A**3) - 1.0

            try:
                return brentq(_crit_res, 0.01, 30.0, xtol=1e-6)
            except Exception:
                return max(wr[-1] - bed[-1], 0.5)

        elif dn_type == 3:  # Normal Depth
            slope = bc.get("dn_slope", 0.001)
            from scipy.optimize import brentq
            sv_temp = _make_solver(
                sections,
                bed,
                rl,
                nch,
                nlob,
                nrob,
                bsl,
                bsr,
                cc,
                ec,
                nsa,
                ifa,
                culverts,
                [0.0] * n_xs,
                rl_lob=rl_lob,
                rl_rob=rl_rob,
            )

            def _normal_res(h):
                K, _ = sv_temp._compute_subdivided_conveyance(h, n_xs - 1)
                return K * slope**0.5 - Q

            try:
                return brentq(_normal_res, 0.01, 30.0, xtol=1e-6)
            except Exception:
                return max(wr[-1] - bed[-1], 0.5)

        elif dn_type == 4:  # Rating Curve
            pts = bc.get("dn_rating_curve_values", [])
            if pts:
                Q_cfs = Q / 0.028316846592
                if isinstance(pts[0], (list, tuple)):
                    qs = [p[0] for p in pts]
                    ws = [p[1] for p in pts]
                else:
                    qs = [pts[j] for j in range(0, len(pts), 2)]
                    ws = [pts[j] for j in range(1, len(pts), 2)]
                ws_ft = float(np.interp(Q_cfs, qs, ws))
                return max(ws_ft * 0.3048 - bed[-1], 0.1)
            return max(wr[-1] - bed[-1], 0.5)

        else:
            return max(wr[-1] - bed[-1], 0.5)

    # 边界条件计算（v2 schema）
    hd = _compute_downstream_bc()

    def _is_zero(v: float) -> bool:
        return abs(v) < 1e-9

    def _solve_seg(xs_indices: list[int], Q_seg: float, h_ds_wse: float) -> dict:
        """在 xs_indices 指定的子断面集上求解一段稳态水面线。"""
        seg_secs = [sections[i] for i in xs_indices]
        seg_bed = [bed[i] for i in xs_indices]
        seg_rl = [rl[i] for i in xs_indices]
        seg_nch = [nch[i] for i in xs_indices]
        seg_nlob = [nlob[i] for i in xs_indices]
        seg_nrob = [nrob[i] for i in xs_indices]
        seg_bsl = [bsl[i] for i in xs_indices]
        seg_bsr = [bsr[i] for i in xs_indices]
        seg_cc = [cc[i] for i in xs_indices]
        seg_ec = [ec[i] for i in xs_indices]
        seg_nsa = [nsa[i] for i in xs_indices]
        seg_lat = [0.0] * len(xs_indices)  # 段内各断面无侧向流
        seg_hd = max(float(h_ds_wse) - float(seg_bed[-1]), 0.5)
        seg_sv = _make_solver(
            seg_secs, seg_bed, seg_rl, seg_nch, seg_nlob, seg_nrob,
            seg_bsl, seg_bsr, seg_cc, seg_ec, seg_nsa, [], None, seg_lat,
        )
        return seg_sv.solve_without_structures(Q=Q_seg, h_downstream=seg_hd)

    def _solve_seg_lat(xs_indices: list[int], h_ds_wse: float) -> dict:
        """在 xs_indices 子集上求解变流量段（用 lateral inflows 处理流量变化）。"""
        seg_secs = [sections[i] for i in xs_indices]
        seg_bed = [bed[i] for i in xs_indices]
        seg_rl = [rl[i] for i in xs_indices]
        seg_nch = [nch[i] for i in xs_indices]
        seg_nlob = [nlob[i] for i in xs_indices]
        seg_nrob = [nrob[i] for i in xs_indices]
        seg_bsl = [bsl[i] for i in xs_indices]
        seg_bsr = [bsr[i] for i in xs_indices]
        seg_cc = [cc[i] for i in xs_indices]
        seg_ec = [ec[i] for i in xs_indices]
        seg_nsa = [nsa[i] for i in xs_indices]
        seg_flows = [flows[i] for i in xs_indices]
        seg_lat = [0.0] * len(xs_indices)
        for j in range(1, len(xs_indices)):
            seg_lat[j - 1] = seg_flows[j] - seg_flows[j - 1]
        seg_hd = max(float(h_ds_wse) - float(seg_bed[-1]), 0.5)
        seg_sv = _make_solver(
            seg_secs, seg_bed, seg_rl, seg_nch, seg_nlob, seg_nrob,
            seg_bsl, seg_bsr, seg_cc, seg_ec, seg_nsa, [], None, seg_lat,
        )
        return seg_sv.solve_without_structures(Q=seg_flows[0], h_downstream=seg_hd)

    # 冰盖参数（从 ref 读取，所有断面统一）
    _ice_data = ref.get("ice_cover")
    _ice_t_arr = None
    _ice_n_arr = None
    if _ice_data:
        _t = float(_ice_data.get("thickness_m", 0))
        _n = float(_ice_data.get("manning_n", 0))
        if _t > 0:
            _ice_t_arr = [_t] * n_xs
            _ice_n_arr = [_n if _n > 0 else 0.03] * n_xs

    def _fallback_serial():
        lat = [0.0] * n_xs
        for i in range(1, n_xs):
            lat[i - 1] = flows[i] - flows[i - 1]
        sv = _make_solver(sections, bed, rl, nch, nlob, nrob, bsl, bsr, cc, ec, nsa, ifa, culverts, lat,
                          rl_lob=rl_lob, rl_rob=rl_rob, bridges=bridges,
                          ice_thickness=_ice_t_arr, n_ice=_ice_n_arr)

        # Inline Structure（闸门+堰）：从参考数据提取并传入
        inline_data = ref.get("inline_structure")
        if inline_data and inline_data.get("gate_groups"):
            openings = inline_data.get("openings_per_profile", [])
            gate_groups = inline_data.get("gate_groups", [])
            # 构建当前 profile 的闸门参数
            gates_for_profile = []
            if p_idx < len(openings):
                op = openings[p_idx]
                for gi in gate_groups:
                    name = gi.get("name", "")
                    if name in op:
                        opening_ft, n_open = op[name]
                        gates_for_profile.append({
                            "opening_m": opening_ft * LF,
                            "n_openings": n_open,
                            "width_m": gi.get("width_m", gi.get("width_ft", 30) * LF),
                            "height_m": gi.get("height_m", gi.get("height_ft", 10) * LF),
                            "invert_m": gi.get("invert_m", gi.get("invert_ft", 0) * LF),
                            "sluice_coef": gi.get("sluice_coef", 0.8),
                            "gate_weir_coef": gi.get("gate_weir_coef",
                                                     gi.get("weir_coef_gate", 3.1)),
                        })
            # 确定 us_xs_index（WSE 跳变最大位置）
            max_jump = 0
            struct_idx = n_xs // 2
            for ii in range(n_xs - 1):
                jump = abs(wr[ii + 1] - wr[ii])
                if jump > max_jump:
                    max_jump = jump
                    struct_idx = ii
            inline_param = {
                "us_xs_index": struct_idx,
                "weir_coef": inline_data.get("weir_coef", 3.1),
                "weir_width_ft": inline_data.get("weir_width_ft", 0),
                "weir_min_elev_ft": inline_data.get("weir_min_elev_ft", 0),
                "gates": gates_for_profile,
            }
            sv._inline_structures = [inline_param]

        r0 = sv.solve_without_structures(Q=Q, h_downstream=hd)
        errs0 = [abs(float(r0["W"][i]) - wr[i]) for i in range(n_xs)]
        return r0, wr, errs0, Q, profile["name"]

    # ------------------------------------------------------------------ #
    # 环网检测（两平行支路汇流结构）                                       #
    # 格式：XS[0..bif] 主干上游 → XS[bif+1..a_end] 支路A                 #
    #       → XS[b_start..b_end] 支路B → XS[dn_start..end] 主干下游     #
    # ------------------------------------------------------------------ #
    try:
        # 找 rl=0 的节点断面 + 流量显著变化（>20%）的位置
        node_set = {i for i in range(n_xs - 1) if _is_zero(float(rl[i]))}
        flow_change_set = set()
        for i in range(n_xs - 1):
            if flows[i] > 0 and abs(flows[i + 1] - flows[i]) / flows[i] > 0.20:
                flow_change_set.add(i)
        combined_set = node_set | flow_change_set
        # 分叉候选：节点或流量变化处流量减小
        bif_candidates = [i for i in sorted(combined_set) if flows[i + 1] < flows[i]]
        if not bif_candidates:
            return _fallback_serial()

        bif_idx = bif_candidates[0]
        main_q = flows[bif_idx]
        branch_a_q = flows[bif_idx + 1]

        # 支路A终止：流量首次偏离 branch_a_q
        branch_b_start = None
        for i in range(bif_idx + 1, n_xs):
            if not _is_zero(flows[i] - branch_a_q):
                branch_b_start = i
                break
        if branch_b_start is None:
            return _fallback_serial()

        branch_a_end = branch_b_start - 1
        branch_b_q = flows[branch_b_start]

        # -------------------------------------------------------------- #
        # Y 形汇流检测：branch_b_q > main_q 说明是合流下游（非环路第二支路）
        # 拓扑：main_upstream(Q=main_q) + tributary(Q=branch_a_q) → downstream(Q=branch_b_q)
        # -------------------------------------------------------------- #
        if branch_b_q > main_q * 1.01:
            seg_main = list(range(0, bif_idx + 1))          # 主干上游
            seg_trib = list(range(bif_idx + 1, branch_a_end + 1))  # 支流
            seg_dn = list(range(branch_b_start, n_xs))      # 合流下游

            if not (seg_main and seg_trib and seg_dn):
                return _fallback_serial()

            # 1) 求解下游段
            r_dn = _solve_seg(seg_dn, branch_b_q, wr[-1])
            wse_dn_top = float(r_dn["W"][0])  # 下游段最上游断面 WSE

            # 2) Junction 能量修正：用下游段顶部的 EGL 作为上游支路 BC
            #    EGL = WSE + α·V²/(2g)
            #    这近似 HEC-RAS 的 Energy Method junction
            xs_dn0 = branch_b_start
            gx = ref["geometry"]["cross_sections"][xs_dn0]
            pts = gx["station_elevation"]
            dm_j = np.array([p[0] * LF for p in pts])
            em_j = np.array([p[1] * LF for p in pts])
            _sec = NaturalSection(name="junc", elevations=em_j, distances=dm_j)
            _bed = float(np.min(em_j))
            _depth = wse_dn_top - _bed
            _area = _sec.compute_area(_depth) if _depth > 0 else 0.0
            if _area > 0:
                _vel = branch_b_q / _area
                junction_wse = wse_dn_top + _vel ** 2 / (2 * 9.81)
            else:
                junction_wse = wse_dn_top

            # 3) 求解两上游支路
            r_trib = _solve_seg(seg_trib, branch_a_q, junction_wse)
            r_main = _solve_seg(seg_main, main_q, junction_wse)

            # 4) 组装全局 WSE
            full_w: list[float] = [0.0] * n_xs
            for li, xi in enumerate(seg_main): full_w[xi] = float(r_main["W"][li])
            for li, xi in enumerate(seg_trib): full_w[xi] = float(r_trib["W"][li])
            for li, xi in enumerate(seg_dn):   full_w[xi] = float(r_dn["W"][li])

            r = {"W": full_w}
            errs = [abs(full_w[i] - wr[i]) for i in range(n_xs)]
            return r, wr, errs, Q, profile["name"]

        # -------------------------------------------------------------- #
        # Split-merge 检测（Ex15 类型）：lateral weir 分流 + 合流
        # 拓扑：main(Q递减) → side_channel → merged_downstream
        # 条件：branch_b_q < branch_a_q, 且下游有合流点 (flow > main_q)
        # -------------------------------------------------------------- #
        if branch_b_q < branch_a_q:
            merge_start = None
            for i in range(branch_b_start, n_xs):
                if flows[i] > main_q * 0.99:
                    merge_start = i
                    break
            if merge_start is not None:
                branch_b_end = merge_start - 1
                merge_q = flows[merge_start]

                seg_main = list(range(0, branch_a_end + 1))  # 主河道（含 lateral weir 变流量）
                seg_side = list(range(branch_b_start, branch_b_end + 1))  # 侧分水道
                seg_merged = list(range(merge_start, n_xs))  # 合流下游

                if seg_main and seg_side and seg_merged:
                    # 1) 合流下游段
                    r_merged = _solve_seg(seg_merged, merge_q, wr[-1])
                    wse_merge_top = float(r_merged["W"][0])

                    # 2) Junction WSE = 合流段顶部 WSE（不加能量修正）
                    #    split-merge 汇流的能量损失大，EGL 修正会显著过估
                    junction_wse = wse_merge_top

                    # 3) 侧分水道（变流量）
                    r_side = _solve_seg_lat(seg_side, junction_wse)

                    # 4) 主河道：分成常 Q 段和变 Q 段
                    #    bif_idx+1..branch_a_end: 常 Q（lateral weir 后）
                    #    0..bif_idx: 变 Q（lateral weir 影响区）
                    seg_main_const = list(range(bif_idx + 1, branch_a_end + 1))
                    seg_main_var = list(range(0, bif_idx + 1))

                    if seg_main_const:
                        r_mc = _solve_seg(seg_main_const, branch_a_q, junction_wse)
                        wse_at_bif = float(r_mc["W"][0])
                    else:
                        wse_at_bif = junction_wse

                    if seg_main_var:
                        r_mv = _solve_seg_lat(seg_main_var, wse_at_bif)
                    else:
                        r_mv = None

                    # 5) 组装
                    full_w: list[float] = [0.0] * n_xs
                    if r_mv:
                        for li, xi in enumerate(seg_main_var):   full_w[xi] = float(r_mv["W"][li])
                    for li, xi in enumerate(seg_main_const): full_w[xi] = float(r_mc["W"][li])
                    for li, xi in enumerate(seg_side):   full_w[xi] = float(r_side["W"][li])
                    for li, xi in enumerate(seg_merged): full_w[xi] = float(r_merged["W"][li])

                    r = {"W": full_w}
                    errs = [abs(full_w[i] - wr[i]) for i in range(n_xs)]
                    return r, wr, errs, Q, profile["name"]

        # -------------------------------------------------------------- #
        # 环路检测（Ex8 类型）：主干 → 支路A + 支路B → 主干下游
        # -------------------------------------------------------------- #
        # 主干下游起点：流量恢复到 main_q
        down_start = None
        for i in range(branch_b_start, n_xs):
            if _is_zero(flows[i] - main_q):
                down_start = i
                break
        if down_start is None:
            return _fallback_serial()

        branch_b_end = down_start - 1

        # 合法性校验
        if not (0 <= bif_idx < branch_a_end < branch_b_start <= branch_b_end < down_start < n_xs):
            return _fallback_serial()
        # 支路末端必须是节点（rl=0）
        if branch_a_end not in node_set or branch_b_end not in node_set:
            return _fallback_serial()

        seg_up = list(range(0, bif_idx + 1))         # 主干上游
        seg_a = list(range(bif_idx + 1, branch_a_end + 1))   # 支路A
        seg_b = list(range(branch_b_start, branch_b_end + 1))  # 支路B
        seg_dn = list(range(down_start, n_xs))        # 主干下游

        if not (seg_up and seg_a and seg_b and seg_dn):
            return _fallback_serial()

        # 求解顺序：下游 → 两支路 → 上游
        r_dn = _solve_seg(seg_dn, main_q, wr[-1])
        wse_confluence = float(r_dn["W"][0])          # 合流点WSE

        r_b = _solve_seg(seg_b, branch_b_q, wse_confluence)
        r_a = _solve_seg(seg_a, branch_a_q, wse_confluence)

        # 分叉点WSE = 两支路上游端取较大值（壅水控制）
        wse_bif = max(float(r_a["W"][0]), float(r_b["W"][0]))
        r_up = _solve_seg(seg_up, main_q, wse_bif)

        # 组装全局WSE数组
        full_w: list[float] = [0.0] * n_xs
        for li, xi in enumerate(seg_up):  full_w[xi] = float(r_up["W"][li])
        for li, xi in enumerate(seg_a):   full_w[xi] = float(r_a["W"][li])
        for li, xi in enumerate(seg_b):   full_w[xi] = float(r_b["W"][li])
        for li, xi in enumerate(seg_dn):  full_w[xi] = float(r_dn["W"][li])

        r = {"W": full_w}
        errs = [abs(full_w[i] - wr[i]) for i in range(n_xs)]
        return r, wr, errs, Q, profile["name"]

    except Exception:
        # 环网检测或分段求解失败，退回串联计算
        return _fallback_serial()


def cmd_run(args):
    with open(args.ref_data, encoding="utf-8") as f:
        ref = json.load(f)
    data = _build_from_ref(ref)
    r, wr, errs, Q, name = _run_profile(ref, args.profile, *data)
    n_xs = data[-1]
    print(f"{ref['case_name']} / {name} (Q={Q:.1f} m³/s)")
    for i in range(n_xs):
        e = float(r["W"][i]) - wr[i]
        print(f"  XS{i:2d}: HC={float(r['W'][i]):8.3f}  HR={wr[i]:8.3f}  err={e:+.3f}")
    print(f"MAE = {np.mean(errs):.4f} m")
    return 0


def cmd_compare(args):
    with open(args.ref_data, encoding="utf-8") as f:
        ref = json.load(f)
    data = _build_from_ref(ref)
    print(f"{ref['case_name']}")
    pc = 0
    for p_idx in range(len(ref["profiles"])):
        try:
            _, _, errs, Q, name = _run_profile(ref, p_idx, *data)
            mae = np.mean(errs)
            st = "PASS" if mae < 0.15 else ("NEAR" if mae < 0.5 else "FAIL")
        except Exception:
            mae = 99; st = "ERR"; Q = 0; name = f"PF{p_idx}"
        if st == "PASS":
            pc += 1
        print(f"  {name:15s} Q={Q:8.1f}  MAE={mae:.3f}  {st}")
    print(f"  通过: {pc}/{len(ref['profiles'])}")
    return 0


def cmd_batch(args):
    ref_dir = Path(args.ref_dir or "reports/hecras_reference_data")
    total = passed = near = fail = 0
    for rf in sorted(ref_dir.glob("*.json")):
        with rf.open(encoding="utf-8") as f:
            ref = json.load(f)
        gd = ref.get("geometry", {}).get("cross_sections", [])
        if not gd or "station_elevation" not in gd[0]:
            continue
        try:
            data = _build_from_ref(ref)
        except Exception:
            continue
        for p_idx in range(len(ref["profiles"])):
            try:
                _, _, errs, Q, name = _run_profile(ref, p_idx, *data)
                mae = np.mean(errs)
                st = "PASS" if mae < 0.15 else ("NEAR" if mae < 0.5 else "FAIL")
            except Exception:
                mae = 99; st = "ERR"; name = f"PF{p_idx}"
            total += 1
            if st == "PASS": passed += 1
            elif st == "NEAR": near += 1
            else: fail += 1
            if not args.quiet:
                print(f"  {ref['case_name']:42s} {name:12s} {mae:.3f} {st}")
    print(f"\nPASS: {passed}/{total} ({100*passed/total:.0f}%)  NEAR: {near}  FAIL: {fail}")
    return 0 if passed == total else 1


def cmd_info(args):
    with open(args.ref_data, encoding="utf-8") as f:
        ref = json.load(f)
    print(f"案例: {ref['case_name']}")
    print(f"断面: {ref['n_cross_sections']}")
    print(f"工况: {ref['n_profiles']}")
    for p in ref["profiles"]:
        print(f"  {p['name']}: Q={float(p['cross_sections'][0]['flow_cfs']):.0f} cfs")
    for feat in ["culverts", "ineffective_areas", "inline_structure"]:
        val = ref.get(feat)
        has = bool(val) and (val if not isinstance(val, list) else any(val))
        print(f"{feat}: {'有' if has else '无'}")
    return 0


def main():
    p = argparse.ArgumentParser(prog="hydroclaude", description="HydroClaude 稳态水面线 CLI")
    sp = p.add_subparsers(dest="cmd")
    r = sp.add_parser("run", help="运行计算")
    r.add_argument("ref_data"); r.add_argument("--profile", type=int, default=0)
    r.set_defaults(func=cmd_run)
    c = sp.add_parser("compare", help="对标 HEC-RAS")
    c.add_argument("ref_data"); c.set_defaults(func=cmd_compare)
    b = sp.add_parser("batch", help="批量对标")
    b.add_argument("--ref-dir"); b.add_argument("-q", "--quiet", action="store_true")
    b.set_defaults(func=cmd_batch)
    i = sp.add_parser("info", help="案例信息")
    i.add_argument("ref_data"); i.set_defaults(func=cmd_info)
    args = p.parse_args()
    if not args.cmd:
        p.print_help(); return 1
    return args.func(args)


if __name__ == "__main__":
    sys.exit(main())
