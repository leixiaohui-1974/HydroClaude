"""从 JSON 参考数据运行非恒定流对标（含 HEC-RAS PT 表和结构物 HTAB）。

用法:
    python scripts/run_unsteady_json_benchmark.py                    # 运行所有单河段案例
    python scripts/run_unsteady_json_benchmark.py MixedFlowRegime    # 运行指定案例
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
from solvers.unsteady_boundary import FlowHydrographBC, StageHydrographBC, NormalDepthBC
from solvers.initial_condition import compute_steady_initial_conditions

REF_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                       "reports", "hecras_unsteady_reference")

# 单河段案例清单（从简单到复杂）
SINGLE_REACH_CASES = [
    ("MixedFlowRegime_unsteady_ref.json", "Mixed Flow Regime (153 XS, no structures)"),
    ("Example20_LateralWeir_unsteady_ref.json", "Lateral Weir (21 XS, structures)"),
    ("CulvertHydraulics_unsteady_ref.json", "Culvert Hydraulics (57 XS, structures)"),
    ("DamBreaching_unsteady_ref.json", "Dam Breaching (192 XS, structures)"),
]


def _load_pt_for_reach(d: dict) -> dict:
    """从 JSON 加载 HEC-RAS 属性表。返回 hecras_pt_* 字段或 None。"""
    pt_list = d.get("hecras_pt")
    if not pt_list or not any(p for p in pt_list):
        return {}
    n_xs = d["n_cross_sections"]
    elev_list, A_list, K_list, B_list, beta_list = [], [], [], [], []
    for i in range(n_xs):
        pt = pt_list[i]
        if pt is None:
            elev_list.append(None)
            A_list.append(None)
            K_list.append(None)
            B_list.append(None)
            beta_list.append(None)
        else:
            elev_list.append(np.array(pt["elevations_m"]))
            A_list.append(np.array(pt["A_m2"]))
            K_list.append(np.array(pt["K_m3s"]))
            B_list.append(np.array(pt["B_m"]))
            beta_list.append(np.array(pt["beta"]))
    # 如果全部都有，返回
    if all(e is not None for e in elev_list):
        return {
            "hecras_pt_elevations": elev_list,
            "hecras_pt_A": A_list,
            "hecras_pt_K": K_list,
            "hecras_pt_B": B_list,
            "hecras_pt_beta": beta_list,
        }
    return {}


def _load_structures(d: dict, xs_rs_list: list) -> list | None:
    """从 JSON 加载结构物 HTAB 数据，映射到断面索引。"""
    struct_list = d.get("structures", [])
    if not struct_list:
        return None
    # 建立 RS → 断面索引映射
    rs_to_idx = {}
    for i, (river, reach, rs) in enumerate(xs_rs_list):
        rs_to_idx[rs] = i
    structures = []
    for s in struct_list:
        if s.get("type", "").lower() not in ("bridge", "culvert"):
            continue
        htab_data = s.get("htab")
        if not htab_data:
            continue
        us_rs = s.get("us_rs", "")
        ds_rs = s.get("ds_rs", "")
        if us_rs not in rs_to_idx or ds_rs not in rs_to_idx:
            continue
        us_idx = rs_to_idx[us_rs]
        ds_idx = rs_to_idx[ds_rs]
        if ds_idx != us_idx + 1:
            continue
        # 构建 HTAB：从 JSON 的曲线列表
        # info array: (n_curves, 2) — [start_index, count]
        # values array: (total_pts, 2) — [Q, HW]
        all_Q = []
        all_HW = []
        info_list = []
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
        info_arr = np.array(info_list)
        if len(all_Q) == 0:
            continue
        vals_arr = np.column_stack([all_Q, all_HW])
        # StructureHTAB 期望原始单位（已经是 SI）
        htab = StructureHTAB(info_arr, vals_arr, ft_to_m=1.0, cfs_to_m3s=1.0)
        structures.append({"cell_index": us_idx, "htab": htab})
    return structures if structures else None


def load_single_reach_case(json_path: str) -> dict:
    """从 JSON 参考数据加载单河段案例。"""
    with open(json_path, encoding="utf-8") as f:
        d = json.load(f)

    n_xs = d["n_cross_sections"]

    # 断面几何
    sections = []
    bed_elevations = []
    xs_rs_list = []
    for i in range(n_xs):
        xs = d["xs_profiles"][i]
        sta = np.array(xs["stations_m"])
        elev = np.array(xs["elevations_m"])
        sec = NaturalSection(name=f"xs_{i}", elevations=elev, distances=sta)
        sections.append(sec)
        bed_elevations.append(float(np.min(elev)))
        river = d["river_names"][i] if i < len(d.get("river_names", [])) else ""
        reach = d["reach_names"][i] if i < len(d.get("reach_names", [])) else ""
        rs = d["river_stations_m"][i] if i < len(d.get("river_stations_m", [])) else ""
        xs_rs_list.append((river, reach, str(rs) if rs is not None else ""))

    bed_elevation = np.array(bed_elevations)
    manning_n = np.array([max(v, 0.001) if v else 0.03 for v in d["manning_n_ch"]])

    # dx
    dx_raw = d["reach_lengths_ch_m"]
    dx = np.array([max(v, 1.0) if v else 100.0 for v in dx_raw[:n_xs - 1]])

    # Manning n 分区
    n_lob = np.array([max(v, 0.01) if v and v > 0 else manning_n[i]
                       for i, v in enumerate(d["manning_n_lob"])])
    n_rob = np.array([max(v, 0.01) if v and v > 0 else manning_n[i]
                       for i, v in enumerate(d["manning_n_rob"])])
    lb = np.array([v if v is not None else 0.0 for v in d["left_bank_sta_m"]])
    rb = np.array([v if v is not None else float(sections[i].distances[-1])
                    for i, v in enumerate(d["right_bank_sta_m"])])

    # HEC-RAS 属性表
    pt_data = _load_pt_for_reach(d)

    # 结构物 HTAB
    structures = _load_structures(d, xs_rs_list)

    # 边界条件
    bcs = d["boundary_conditions"]
    upstream_bc = None
    downstream_bc = None

    for bc in bcs:
        if bc["type"] == "flow_hydrograph":
            upstream_bc = FlowHydrographBC(
                np.array(bc["times_s"]),
                np.array(bc["values_m3s"]),
            )
        elif bc["type"] == "stage_hydrograph":
            downstream_bc = StageHydrographBC(
                np.array(bc["times_s"]),
                np.array(bc["values_m"]),
            )
        elif bc["type"] == "normal_depth":
            downstream_bc = NormalDepthBC(
                sections[-1],
                manning_n=float(manning_n[-1]),
                bed_slope=bc["slope"],
                manning_n_lob=float(n_lob[-1]),
                manning_n_rob=float(n_rob[-1]),
                left_bank=float(lb[-1]),
                right_bank=float(rb[-1]),
            )

    # 参考结果
    ws_ref = np.array(d["water_surface_m"])
    fl_ref = np.array(d["flow_m3s"])
    time_ref = np.array(d["times_s"])

    return {
        "case_name": d["case_name"],
        "n_xs": n_xs,
        "dx": dx,
        "bed_elevation": bed_elevation,
        "manning_n": manning_n,
        "manning_n_lob": n_lob,
        "manning_n_rob": n_rob,
        "left_bank": lb,
        "right_bank": rb,
        "sections": sections,
        "upstream_bc": upstream_bc,
        "downstream_bc": downstream_bc,
        "ws_ref": ws_ref,
        "fl_ref": fl_ref,
        "time_ref": time_ref,
        "has_structures": d.get("has_structures", False),
        "structures": structures,
        **pt_data,
    }


def run_single_reach(json_path: str, name: str) -> float:
    """运行单河段案例，返回 MAE。"""
    print(f"\n{'=' * 70}")
    print(f"  {name}")
    print(f"{'=' * 70}")

    data = load_single_reach_case(json_path)
    n_xs = data["n_xs"]

    has_pt = "hecras_pt_elevations" in data
    n_struct = len(data["structures"]) if data["structures"] else 0
    print(f"  Case: {data['case_name']}")
    print(f"  XS={n_xs}, dx=[{data['dx'].min():.1f}, {data['dx'].max():.1f}]m")
    print(f"  n_ch=[{data['manning_n'].min():.4f}, {data['manning_n'].max():.4f}]")
    print(f"  HEC-RAS PT: {'Yes' if has_pt else 'No'}, Structures: {n_struct}")
    print(f"  Time steps: {len(data['time_ref'])}")

    if data["upstream_bc"] is None or data["downstream_bc"] is None:
        print("  ERROR: Missing boundary condition")
        return float("inf")

    # 构建 reach data
    reach_data = UnsteadyReachData(
        n_xs=n_xs,
        dx=data["dx"],
        bed_elevation=data["bed_elevation"],
        manning_n=data["manning_n"],
        sections=data["sections"],
        manning_n_lob=data["manning_n_lob"],
        manning_n_rob=data["manning_n_rob"],
        left_bank=data["left_bank"],
        right_bank=data["right_bank"],
        hecras_pt_elevations=data.get("hecras_pt_elevations"),
        hecras_pt_A=data.get("hecras_pt_A"),
        hecras_pt_K=data.get("hecras_pt_K"),
        hecras_pt_B=data.get("hecras_pt_B"),
        hecras_pt_beta=data.get("hecras_pt_beta"),
        structures=data["structures"],
    )

    # 稳态求解初始条件（不使用 HEC-RAS 结果）
    Q_initial = float(data["upstream_bc"](data["time_ref"][0]))
    if hasattr(data["downstream_bc"], "compute_normal_wse"):
        ds_wse = data["downstream_bc"].compute_normal_wse(Q_initial)
    elif hasattr(data["downstream_bc"], "__call__"):
        ds_wse = float(data["downstream_bc"](data["time_ref"][0]))
    else:
        ds_wse = data["bed_elevation"][-1] + 1.0
    try:
        Z_init, Q_init = compute_steady_initial_conditions(
            sections=data["sections"],
            bed_elevations=data["bed_elevation"],
            manning_n=data["manning_n"],
            reach_lengths=data["dx"],
            Q_initial=Q_initial,
            downstream_wse=ds_wse,
            manning_n_lob=data["manning_n_lob"],
            manning_n_rob=data["manning_n_rob"],
            left_bank=data["left_bank"],
            right_bank=data["right_bank"],
        )
        ic_source = "steady_solver"
    except Exception as e:
        print(f"  WARN: Steady IC failed ({e}), using normal depth fallback")
        Z_init = data["bed_elevation"] + 1.0
        Q_init = np.full(n_xs, Q_initial)
        ic_source = "fallback"
    # 对比稳态初始条件与 HEC-RAS 的第一步
    ic_diff = Z_init - data["ws_ref"][0]
    ic_mae = float(np.mean(np.abs(ic_diff)))
    print(f"  IC source: {ic_source}, IC MAE vs HEC-RAS t=0: {ic_mae:.4f}m")
    state0 = UnsteadyState(Z=Z_init, Q=Q_init, t=data["time_ref"][0])

    # 时间步长
    dt_output = data["time_ref"][1] - data["time_ref"][0]
    if n_xs > 100:
        dt = min(dt_output, 120.0)
    else:
        dt = min(dt_output / 2.0, 60.0)
    print(f"  dt={dt:.1f}s, dt_output={dt_output:.1f}s")

    solver = PreissmannSolver(
        reach_data, theta=0.6, g=9.81,
        nr_max_iter=30, nr_tol=1e-4,
        min_depth=0.05, max_dZ_per_iter=0.5,
    )

    print("  Solving...")
    t0 = time.perf_counter()
    result = solver.solve(
        state0,
        t_end=data["time_ref"][-1],
        dt=dt,
        upstream_bc=data["upstream_bc"],
        downstream_bc=data["downstream_bc"],
        output_interval=dt_output,
        verbose=False,
        min_dt=5.0,
        max_dt_retries=4,
    )
    elapsed = time.perf_counter() - t0
    print(f"  Elapsed: {elapsed:.1f}s")

    # 对比
    times_out = result["times"]
    Z_hist = result["Z_history"]

    mae_per_step = []
    for k, t_ref in enumerate(data["time_ref"]):
        idx = int(np.argmin(np.abs(times_out - t_ref)))
        if abs(times_out[idx] - t_ref) > dt_output * 0.5:
            continue
        diff = Z_hist[idx] - data["ws_ref"][k]
        mae_per_step.append(float(np.mean(np.abs(diff))))

    mae_overall = float(np.mean(mae_per_step)) if mae_per_step else float("inf")
    mae_max = float(np.max(mae_per_step)) if mae_per_step else float("inf")

    mb = solver.compute_mass_balance(result)
    verdict = "PASS" if mae_overall < 0.15 else ("NEAR" if mae_overall < 0.50 else "FAIL")

    print(f"  MAE={mae_overall:.4f}m, MaxMAE={mae_max:.4f}m, MB={mb['error_percent']:.3f}%")
    print(f"  Verdict: [{verdict}]")
    return mae_overall


if __name__ == "__main__":
    filter_name = sys.argv[1] if len(sys.argv) > 1 else None

    results = {}
    for fn, name in SINGLE_REACH_CASES:
        if filter_name and filter_name not in fn:
            continue
        json_path = os.path.join(REF_DIR, fn)
        if not os.path.exists(json_path):
            print(f"  SKIP: {fn} not found")
            continue
        try:
            mae = run_single_reach(json_path, name)
            results[fn] = mae
        except Exception as e:
            print(f"  ERROR: {e}")
            import traceback
            traceback.print_exc()
            results[fn] = float("inf")

    print(f"\n{'=' * 70}")
    print("SUMMARY")
    print(f"{'=' * 70}")
    passed = 0
    total = len(results)
    for fn, name in SINGLE_REACH_CASES:
        if fn not in results:
            continue
        mae = results[fn]
        v = "PASS" if mae < 0.15 else ("NEAR" if mae < 0.50 else "FAIL")
        if mae < 0.15:
            passed += 1
        print(f"  {fn[:45]:<47} MAE={mae:.4f}m [{v}]")
    print(f"\n  {passed}/{total} PASSED (MAE < 0.15m)")
