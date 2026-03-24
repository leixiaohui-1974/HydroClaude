"""全部非恒定流案例统一对标脚本。

自动处理：
- 不同 BC 类型 (flow_hydrograph, stage_hydrograph, normal_depth, rating_curve)
- 稳态 IC（普通案例）或正常水深 IC（溃坝等）
- 结构物 HTAB（如果 JSON 中有）
- 单河段案例
"""

import sys
import os
import json
import time
import numpy as np

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from physics.cross_section import NaturalSection
from solvers.unsteady_preissmann_solver import (
    PreissmannSolver, UnsteadyReachData, UnsteadyState, StructureHTAB,
)
from solvers.unsteady_boundary import (
    FlowHydrographBC, StageHydrographBC, NormalDepthBC, RatingCurveBC,
)
from solvers.initial_condition import compute_steady_initial_conditions, compute_normal_depth_ic

REF_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                       "reports", "hecras_unsteady_reference")

CASES = [
    "MixedFlowRegime_unsteady_ref.json",
    "Example20_LateralWeir_unsteady_ref.json",
    "BridgeHydraulics_unsteady_ref.json",
    "CulvertHydraulics_unsteady_ref.json",
    "DamBreaching_unsteady_ref.json",
]


def _load_sections(d):
    """加载断面几何和参数。"""
    n_xs = d["n_cross_sections"]
    sections, bed = [], []
    for i in range(n_xs):
        xs = d["xs_profiles"][i]
        sec = NaturalSection(name=f"xs_{i}",
                             elevations=np.array(xs["elevations_m"]),
                             distances=np.array(xs["stations_m"]))
        sections.append(sec)
        bed.append(float(np.min(xs["elevations_m"])))
    bed_arr = np.array(bed)
    manning_n = np.array([max(v, 0.001) if v else 0.03 for v in d["manning_n_ch"]])
    dx = np.array([max(v, 1.0) if v else 100.0 for v in d["reach_lengths_ch_m"][:n_xs - 1]])
    lb = np.array([v if v is not None else 0.0 for v in d["left_bank_sta_m"]])
    rb = np.array([v if v is not None else float(sections[i].distances[-1])
                    for i, v in enumerate(d["right_bank_sta_m"])])
    n_lob = np.array([max(v, 0.01) if v and v > 0 else manning_n[i]
                       for i, v in enumerate(d["manning_n_lob"])])
    n_rob = np.array([max(v, 0.01) if v and v > 0 else manning_n[i]
                       for i, v in enumerate(d["manning_n_rob"])])
    return sections, bed_arr, manning_n, dx, lb, rb, n_lob, n_rob


def _load_bcs(d, sections, manning_n, n_lob, n_rob, lb, rb):
    """加载边界条件。"""
    upstream_bc = None
    downstream_bc = None
    for bc in d["boundary_conditions"]:
        if bc["type"] == "flow_hydrograph" and upstream_bc is None:
            upstream_bc = FlowHydrographBC(np.array(bc["times_s"]), np.array(bc["values_m3s"]))
        elif bc["type"] == "stage_hydrograph":
            downstream_bc = StageHydrographBC(np.array(bc["times_s"]), np.array(bc["values_m"]))
        elif bc["type"] == "normal_depth":
            downstream_bc = NormalDepthBC(
                sections[-1], manning_n=float(manning_n[-1]), bed_slope=bc["slope"],
                manning_n_lob=float(n_lob[-1]), manning_n_rob=float(n_rob[-1]),
                left_bank=float(lb[-1]), right_bank=float(rb[-1]))
        elif bc["type"] == "rating_curve":
            # Handle both key naming conventions
            flows_key = "flows_m3s" if "flows_m3s" in bc else "flow_m3s"
            stages_key = "stages_m" if "stages_m" in bc else "stage_m"
            rc_flows = np.array(bc[flows_key])
            rc_stages = np.array(bc[stages_key])
            # Ensure flows are sorted ascending (HEC-RAS may store as stage,flow)
            if len(rc_flows) > 1 and rc_stages[0] > rc_stages[-1]:
                rc_flows, rc_stages = rc_stages, rc_flows
            downstream_bc = RatingCurveBC(flows=rc_flows, stages=rc_stages)
    return upstream_bc, downstream_bc


def _load_structures(d, n_xs):
    """加载结构物 HTAB（如果有）。"""
    struct_list = d.get("structures", [])
    if not struct_list:
        return None
    structures = []
    for s in struct_list:
        if s.get("type", "").lower() not in ("bridge", "culvert"):
            continue
        htab_data = s.get("htab")
        if not htab_data:
            continue
        # 找对应断面索引：结构物 RS 是原始单位，river_stations_m 已转米
        us_rs_str = s.get("us_rs", "")
        ds_rs_str = s.get("ds_rs", "")
        try:
            us_rs_val = float(us_rs_str)
            ds_rs_val = float(ds_rs_str)
        except (ValueError, TypeError):
            continue
        # 判断单位：如果 river_stations 是米且 RS 值更大，说明 RS 是英制
        rs_list = d.get("river_stations_m", [])
        valid_rs = [r for r in rs_list if r is not None]
        is_english = d.get("unit_system", "english") == "english"
        lf = 0.3048 if is_english else 1.0
        us_rs_m = us_rs_val * lf
        ds_rs_m = ds_rs_val * lf
        # 找最近匹配的断面（最近邻）
        us_idx = ds_idx = -1
        best_us_dist = best_ds_dist = float("inf")
        for i in range(n_xs):
            rs = rs_list[i]
            if rs is None:
                continue
            d_us = abs(float(rs) - us_rs_m)
            d_ds = abs(float(rs) - ds_rs_m)
            if d_us < best_us_dist:
                best_us_dist = d_us
                us_idx = i
            if d_ds < best_ds_dist:
                best_ds_dist = d_ds
                ds_idx = i
        if us_idx < 0 or ds_idx < 0 or ds_idx != us_idx + 1:
            continue
        if best_us_dist > 1.0 or best_ds_dist > 1.0:
            continue  # No reasonable match
        # Build HTAB
        all_Q, all_HW, info_list = [], [], []
        offset = 0
        for curve in htab_data:
            if curve is None:
                info_list.append([offset, 0])
                continue
            Q = curve["Q_m3s"]
            HW = curve["HW_m"]
            cnt = len(Q)
            info_list.append([offset, cnt])
            all_Q.extend(Q)
            all_HW.extend(HW)
            offset += cnt
        if not all_Q:
            continue
        info_arr = np.array(info_list)
        vals_arr = np.column_stack([all_Q, all_HW])
        htab = StructureHTAB(info_arr, vals_arr, ft_to_m=1.0, cfs_to_m3s=1.0)
        structures.append({"cell_index": us_idx, "htab": htab})
    return structures if structures else None


def run_case(fn):
    """运行单个案例，返回结果字典。"""
    path = os.path.join(REF_DIR, fn)
    d = json.load(open(path, encoding="utf-8"))
    n_xs = d["n_cross_sections"]
    case_name = d["case_name"]

    sections, bed, manning_n, dx, lb, rb, n_lob, n_rob = _load_sections(d)
    upstream_bc, downstream_bc = _load_bcs(d, sections, manning_n, n_lob, n_rob, lb, rb)
    structures = _load_structures(d, n_xs)

    if upstream_bc is None or downstream_bc is None:
        return {"case": case_name, "n_xs": n_xs, "status": "NO_BC"}

    # 初始条件
    Q0 = float(upstream_bc(d["times_s"][0]))
    if hasattr(downstream_bc, "compute_normal_wse"):
        ds_wse = downstream_bc.compute_normal_wse(Q0)
    else:
        ds_wse = float(downstream_bc(d["times_s"][0]))

    # 判断是否为溃坝类型（上下游水位差 > 5m）
    is_dam_break = (bed[0] - bed[-1]) > 10.0 and "dam" in case_name.lower()

    try:
        if is_dam_break:
            Z_init, Q_init = compute_normal_depth_ic(
                sections=sections, bed_elevations=bed, manning_n=manning_n,
                reach_lengths=dx, Q_initial=Q0,
                manning_n_lob=n_lob, manning_n_rob=n_rob, left_bank=lb, right_bank=rb)
        else:
            Z_init, Q_init = compute_steady_initial_conditions(
                sections=sections, bed_elevations=bed, manning_n=manning_n,
                reach_lengths=dx, Q_initial=Q0, downstream_wse=ds_wse,
                manning_n_lob=n_lob, manning_n_rob=n_rob, left_bank=lb, right_bank=rb)
    except Exception:
        Z_init, Q_init = compute_normal_depth_ic(
            sections=sections, bed_elevations=bed, manning_n=manning_n,
            reach_lengths=dx, Q_initial=Q0,
            manning_n_lob=n_lob, manning_n_rob=n_rob, left_bank=lb, right_bank=rb)

    ic_mae = float(np.mean(np.abs(Z_init - np.array(d["water_surface_m"][0]))))

    # 构建求解器
    t0 = time.perf_counter()
    reach_data = UnsteadyReachData(
        n_xs=n_xs, dx=dx, bed_elevation=bed, manning_n=manning_n,
        sections=sections, left_bank=lb, right_bank=rb,
        manning_n_lob=n_lob, manning_n_rob=n_rob,
        structures=structures)
    solver = PreissmannSolver(
        reach_data, theta=0.6, g=9.81, nr_max_iter=30, nr_tol=1e-4,
        min_depth=0.05, max_dZ_per_iter=0.5)
    pt_time = time.perf_counter() - t0

    # 求解
    state0 = UnsteadyState(Z=Z_init, Q=Q_init, t=d["times_s"][0])
    dt_output = d["times_s"][1] - d["times_s"][0]
    dt = min(dt_output, 120.0) if n_xs > 50 else min(dt_output / 2.0, 60.0)

    t0 = time.perf_counter()
    result = solver.solve(
        state0, t_end=d["times_s"][-1], dt=dt,
        upstream_bc=upstream_bc, downstream_bc=downstream_bc,
        output_interval=dt_output, verbose=False)
    solve_time = time.perf_counter() - t0

    # 对比
    ws_ref = np.array(d["water_surface_m"])
    mae_list = []
    for k, t_ref in enumerate(d["times_s"]):
        idx = np.argmin(np.abs(result["times"] - t_ref))
        if abs(result["times"][idx] - t_ref) > dt_output:
            continue
        mae_list.append(float(np.mean(np.abs(result["Z_history"][idx] - ws_ref[k]))))

    mae = np.mean(mae_list) if mae_list else float("inf")
    v = "PASS" if mae < 0.15 else ("NEAR" if mae < 0.50 else "FAIL")

    return {
        "case": case_name, "n_xs": n_xs, "ic_mae": ic_mae, "mae": mae,
        "status": v, "pt_time": pt_time, "solve_time": solve_time,
        "n_struct": len(structures) if structures else 0,
    }


if __name__ == "__main__":
    filter_name = sys.argv[1] if len(sys.argv) > 1 else None

    print("%-20s %3s %4s %8s %8s %6s %6s %6s" % (
        "Case", "XS", "St", "IC_MAE", "MAE", "Result", "PT", "Solve"))
    print("-" * 72)

    for fn in CASES:
        if filter_name and filter_name not in fn:
            continue
        path = os.path.join(REF_DIR, fn)
        if not os.path.exists(path):
            continue
        try:
            r = run_case(fn)
            if "ic_mae" not in r:
                print("%-20s %3d %4s %8s %8s %6s" % (
                    r["case"][:20], r["n_xs"], "-", "-", "-", r["status"]))
            else:
                print("%-20s %3d %4d %8.4f %8.4f %6s %5.1fs %5.1fs" % (
                    r["case"][:20], r["n_xs"], r["n_struct"],
                    r["ic_mae"], r["mae"], r["status"],
                    r["pt_time"], r["solve_time"]))
        except Exception as e:
            print("%-20s ERROR: %s" % (fn[:20], str(e)[:50]))
