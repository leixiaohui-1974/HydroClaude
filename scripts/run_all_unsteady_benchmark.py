"""Non-steady flow benchmark for all 7 cases.\n\nSingle reach: 4 cases\nNetwork: 3 cases\nRules: no HEC-RAS PT, no HEC-RAS IC, NormalDepthBC with subdivision\n"""

import sys, os, json, time, threading, traceback
from collections import OrderedDict
import numpy as np
import re
import h5py

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from physics.cross_section import NaturalSection
from solvers.unsteady_preissmann_solver import (
    PreissmannSolver, UnsteadyReachData, UnsteadyState, StructureHTAB,
)
from solvers.unsteady_network_solver import (
    UnsteadyNetworkSolver,
    ReachInfo,
    JunctionInfo,
    StorageAreaInfo,
    StorageConnectionInfo,
    LateralStructureInfo,
)
from solvers.unsteady_boundary import FlowHydrographBC, StageHydrographBC, NormalDepthBC, RatingCurveBC
from solvers.initial_condition import compute_steady_initial_conditions

REF_DIR = os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
    "reports", "hecras_unsteady_reference",
)

SINGLE_REACH_CASES = [
    ("MixedFlowRegime_unsteady_ref.json", "MixedFlowRegime"),
    ("Example20_LateralWeir_unsteady_ref.json", "Example20_LateralWeir"),
    ("CulvertHydraulics_unsteady_ref.json", "CulvertHydraulics"),
    ("DamBreaching_unsteady_ref.json", "DamBreaching"),
]

NETWORK_CASES = [
    ("MultipleReaches_unsteady_ref.json", "MultipleReaches"),
    ("JunctionHydraulics_unsteady_ref.json", "JunctionHydraulics"),
    ("Example17_Unsteady_unsteady_ref.json", "Example17_Unsteady"),
]

CASE_TIMEOUT = 300
LF = 0.3048
CFS_TO_M3S = 0.028316846592


def _load_structures(d, xs_rs_list):
    """Load structure HTAB data from JSON."""
    struct_list = d.get("structures", [])
    if not struct_list:
        return None

    def _safe_float(value):
        try:
            return float(value)
        except Exception:
            return None

    xs_rows = []
    for i, (river, reach, rs) in enumerate(xs_rs_list):
        xs_rows.append({
            "index": i,
            "river": str(river or ""),
            "reach": str(reach or ""),
            "rs_m": _safe_float(rs),
        })

    def _structure_rs_m(struct_item, key):
        numeric_key = f"{key}_m"
        numeric = _safe_float(struct_item.get(numeric_key))
        if numeric is not None:
            return numeric
        raw = _safe_float(struct_item.get(key))
        if raw is None:
            return None
        if str(d.get("unit_system", "")).lower() == "english":
            return raw * 0.3048
        return raw

    def _match_xs_index(struct_item, rs_m):
        if rs_m is None:
            return None
        river = str(struct_item.get("river", "") or "")
        reach = str(struct_item.get("reach", "") or "")
        candidates = [
            row for row in xs_rows
            if row["rs_m"] is not None and row["river"] == river and row["reach"] == reach
        ]
        if not candidates:
            candidates = [row for row in xs_rows if row["rs_m"] is not None]
        if not candidates:
            return None
        best = min(candidates, key=lambda row: abs(row["rs_m"] - rs_m))
        return int(best["index"])

    structures = []
    for s in struct_list:
        if s.get("type", "").lower() not in ("bridge", "culvert"):
            continue
        htab_data = s.get("htab")
        if not htab_data:
            continue
        us_idx = _match_xs_index(s, _structure_rs_m(s, "us_rs"))
        ds_idx = _match_xs_index(s, _structure_rs_m(s, "ds_rs"))
        if us_idx is None or ds_idx is None:
            continue
        if ds_idx < us_idx:
            us_idx, ds_idx = ds_idx, us_idx
        if ds_idx != us_idx + 1:
            continue
        all_Q, all_HW, info_list = [], [], []
        offset = 0
        for curve in htab_data:
            if curve is None:
                info_list.append([offset, 0])
                continue
            cnt = len(curve["Q_m3s"])
            info_list.append([offset, cnt])
            all_Q.extend(curve["Q_m3s"])
            all_HW.extend(curve["HW_m"])
            offset += cnt
        if not all_Q:
            continue
        info_arr = np.array(info_list)
        vals_arr = np.column_stack([all_Q, all_HW])
        htab = StructureHTAB(info_arr, vals_arr, ft_to_m=1.0, cfs_to_m3s=1.0)
        structures.append({
            "cell_index": us_idx,
            "htab": htab,
            "use_energy_grade_for_pressure": bool(s.get("use_energy_grade_for_pressure", False)),
            "use_critical_upstream": bool(s.get("use_critical_upstream", False)),
            "use_friction_in_momentum": bool(s.get("use_friction_in_momentum", False)),
            "use_weight_in_momentum": bool(s.get("use_weight_in_momentum", False)),
            "upstream_distance_m": _safe_float(s.get("upstream_distance_m")),
        })
    return structures if structures else None


def _build_section_arrays(d, xs_indices):
    """Build per-reach geometry arrays from global JSON data at given XS indices."""
    sections = []
    bed_elevations = []
    xs_rs_list = []
    for gi in xs_indices:
        xs = d["xs_profiles"][gi]
        sta = np.array(xs["stations_m"])
        elev = np.array(xs["elevations_m"])
        sec = NaturalSection(name=f"xs_{gi}", elevations=elev, distances=sta)
        sections.append(sec)
        bed_elevations.append(float(np.min(elev)))
        river = d["river_names"][gi] if gi < len(d.get("river_names", [])) else ""
        reach = d["reach_names"][gi] if gi < len(d.get("reach_names", [])) else ""
        rs = d["river_stations_m"][gi] if gi < len(d.get("river_stations_m", [])) else ""
        xs_rs_list.append((river, reach, str(rs) if rs is not None else ""))

    manning_n_full = d["manning_n_ch"]
    n_lob_full = d["manning_n_lob"]
    n_rob_full = d["manning_n_rob"]
    lb_full = d["left_bank_sta_m"]
    rb_full = d["right_bank_sta_m"]
    contr_full = d.get("contraction_coef", [None] * len(xs_indices))
    expan_full = d.get("expansion_coef", [None] * len(xs_indices))
    dx_raw = d["reach_lengths_ch_m"]

    mn_ch = [manning_n_full[gi] for gi in xs_indices]
    manning_n = np.array([max(v, 0.001) if v else 0.03 for v in mn_ch])
    n_lob_raw = [n_lob_full[gi] for gi in xs_indices]
    n_rob_raw = [n_rob_full[gi] for gi in xs_indices]
    n_lob = np.array([max(v, 0.01) if v and v > 0 else manning_n[i] for i, v in enumerate(n_lob_raw)])
    n_rob = np.array([max(v, 0.01) if v and v > 0 else manning_n[i] for i, v in enumerate(n_rob_raw)])
    lb = np.array([v if v is not None else 0.0 for v in [lb_full[gi] for gi in xs_indices]])
    rb = np.array([v if v is not None else float(sections[i].distances[-1])
                   for i, v in enumerate([rb_full[gi] for gi in xs_indices])])
    contraction = np.array([
        float(v) if v is not None else 0.1
        for v in [contr_full[gi] for gi in xs_indices]
    ])
    expansion = np.array([
        float(v) if v is not None else 0.3
        for v in [expan_full[gi] for gi in xs_indices]
    ])
    dx = np.array([max(dx_raw[gi], 1.0) if dx_raw[gi] else 100.0 for gi in xs_indices[:-1]])

    return {
        "sections": sections,
        "bed_elevation": np.array(bed_elevations),
        "manning_n": manning_n,
        "manning_n_lob": n_lob,
        "manning_n_rob": n_rob,
        "left_bank": lb,
        "right_bank": rb,
        "contraction_coef": contraction,
        "expansion_coef": expansion,
        "dx": dx,
        "xs_rs_list": xs_rs_list,
        "n_xs": len(xs_indices),
    }


def _compute_ic(sa, Q_initial, downstream_wse):
    """Compute steady-state IC; fallback on error."""
    try:
        Z_init, Q_init = compute_steady_initial_conditions(
            sections=sa["sections"],
            bed_elevations=sa["bed_elevation"],
            manning_n=sa["manning_n"],
            reach_lengths=sa["dx"],
            Q_initial=Q_initial,
            downstream_wse=downstream_wse,
            manning_n_lob=sa["manning_n_lob"],
            manning_n_rob=sa["manning_n_rob"],
            left_bank=sa["left_bank"],
            right_bank=sa["right_bank"],
            contraction_coefs=sa["contraction_coef"],
            expansion_coefs=sa["expansion_coef"],
        )
        return Z_init, Q_init, "steady_solver"
    except Exception as e:
        Z_init = sa["bed_elevation"] + 1.0
        Q_init = np.full(sa["n_xs"], Q_initial)
        return Z_init, Q_init, f"fallback({e})"


def _calc_mae(Z_hist, ws_ref, times_out, time_ref, dt_output):
    """Compute mean MAE across all output timesteps."""
    mae_per_step = []
    for k, t_ref in enumerate(time_ref):
        idx = int(np.argmin(np.abs(times_out - t_ref)))
        if abs(times_out[idx] - t_ref) > dt_output * 0.5:
            continue
        diff = Z_hist[idx] - ws_ref[k]
        mae_per_step.append(float(np.mean(np.abs(diff))))
    if not mae_per_step:
        return float("inf"), float("inf")
    return float(np.mean(mae_per_step)), float(np.max(mae_per_step))


def _verdict(mae):
    if mae < 0.15:
        return "PASS"
    elif mae < 0.50:
        return "NEAR"
    return "FAIL"


def run_single_reach(json_path, case_label):
    """Run a single-reach unsteady case, return result dict."""
    sep = "=" * 70
    print(f"\n{sep}")
    print(f"  [SINGLE] {case_label}")
    print(sep)

    with open(json_path, encoding="utf-8") as f:
        d = json.load(f)

    n_xs = d["n_cross_sections"]
    sa = _build_section_arrays(d, list(range(n_xs)))
    structures = _load_structures(d, sa["xs_rs_list"])
    n_struct = len(structures) if structures else 0
    print(f"  XS={n_xs}, structures={n_struct}")

    bcs = d["boundary_conditions"]
    upstream_bc = None
    downstream_bc = None
    for bc in bcs:
        if bc["type"] == "flow_hydrograph":
            upstream_bc = FlowHydrographBC(
                np.array(bc["times_s"]), np.array(bc["values_m3s"]))
        elif bc["type"] == "stage_hydrograph":
            downstream_bc = StageHydrographBC(
                np.array(bc["times_s"]), np.array(bc["values_m"]))
        elif bc["type"] == "normal_depth":
            downstream_bc = NormalDepthBC(
                section=sa["sections"][-1],
                manning_n=float(sa["manning_n"][-1]),
                bed_slope=bc["slope"],
                manning_n_lob=float(sa["manning_n_lob"][-1]),
                manning_n_rob=float(sa["manning_n_rob"][-1]),
                left_bank=float(sa["left_bank"][-1]),
                right_bank=float(sa["right_bank"][-1]),
            )
        elif bc["type"] == "rating_curve":
            downstream_bc = RatingCurveBC(
                flows=np.array(bc["flow_m3s"]),
                stages=np.array(bc["stage_m"]),
            )

    if upstream_bc is None or downstream_bc is None:
        return {"case": case_label, "ic_mae": float("inf"), "mae": float("inf"),
                "verdict": "FAIL", "error": "Missing BC"}

    ws_ref = np.array(d["water_surface_m"])
    time_ref = np.array(d["times_s"])

    Q0 = float(upstream_bc(time_ref[0]))
    if hasattr(downstream_bc, "compute_normal_wse"):
        ds_wse = downstream_bc.compute_normal_wse(Q0)
    elif callable(downstream_bc):
        ds_wse = float(downstream_bc(time_ref[0]))
    else:
        ds_wse = sa["bed_elevation"][-1] + 1.0

    Z_init, Q_init, ic_src = _compute_ic(sa, Q0, ds_wse)
    ic_mae = float(np.mean(np.abs(Z_init - ws_ref[0])))
    print(f"  IC: {ic_src}, IC_MAE={ic_mae:.4f}m")

    reach_data = UnsteadyReachData(
        n_xs=n_xs,
        dx=sa["dx"],
        bed_elevation=sa["bed_elevation"],
        manning_n=sa["manning_n"],
        sections=sa["sections"],
        manning_n_lob=sa["manning_n_lob"],
        manning_n_rob=sa["manning_n_rob"],
        left_bank=sa["left_bank"],
        right_bank=sa["right_bank"],
        contraction_coef=sa["contraction_coef"],
        expansion_coef=sa["expansion_coef"],
        structures=structures,
    )

    dt_output = time_ref[1] - time_ref[0]
    dt = min(dt_output / 2.0, 60.0) if n_xs <= 100 else (min(dt_output, 120.0) if n_xs <= 150 else dt_output)
    print(f"  dt={dt:.1f}s, dt_output={dt_output:.1f}s")

    solver = PreissmannSolver(
        reach_data, theta=0.6, g=9.81,
        nr_max_iter=30, nr_tol=1e-4,
        min_depth=0.05, max_dZ_per_iter=0.5,
    )

    state0 = UnsteadyState(Z=Z_init, Q=Q_init, t=time_ref[0])
    t0 = time.perf_counter()
    result = solver.solve(
        state0, t_end=time_ref[-1], dt=dt,
        upstream_bc=upstream_bc, downstream_bc=downstream_bc,
        output_interval=dt_output, verbose=False,
        min_dt=5.0, max_dt_retries=4,
    )
    elapsed = time.perf_counter() - t0
    print(f"  Elapsed: {elapsed:.1f}s")

    times_out = result["times"]
    Z_hist = result["Z_history"]
    mae_mean, mae_max = _calc_mae(Z_hist, ws_ref, times_out, time_ref, dt_output)
    v = _verdict(mae_mean)
    print(f"  MAE={mae_mean:.4f}m, MaxMAE={mae_max:.4f}m  [{v}]")

    return {
        "case": case_label,
        "ic_mae": ic_mae,
        "mae": mae_mean,
        "mae_max": mae_max,
        "verdict": v,
        "elapsed": elapsed,
    }


def _group_xs_by_reach(d):
    groups = OrderedDict()
    for i, (rv, rch) in enumerate(zip(d["river_names"], d["reach_names"])):
        k = rv + "/" + rch
        if k not in groups:
            groups[k] = []
        groups[k].append(i)
    return groups

def _parse_bc_location(loc):
    river_part, reach_part = "", ""
    for part in loc.split("  "):
        part = part.strip()
        if part.startswith("River:"):
            river_part = part[6:].strip()
        elif part.startswith("Reach:"):
            reach_part = part[6:].strip()
    return river_part + "/" + reach_part


def _weir_coef_to_si(raw_coef, unit_system):
    """Convert HEC-RAS weir coefficient to SI form for Q = C L H^1.5."""
    try:
        coef = float(raw_coef)
    except Exception:
        return None
    if str(unit_system or "").lower() == "english":
        return coef * (CFS_TO_M3S / (LF ** 2.5))
    return coef


def _project_sidecar_paths(d):
    source_hdf = d.get("source_hdf")
    if not source_hdf:
        return None, None
    hdf_path = os.path.abspath(source_hdf)
    base, _ = os.path.splitext(hdf_path)
    g_candidates = []
    u_candidates = []
    folder = os.path.dirname(hdf_path)
    if os.path.isdir(folder):
        g_candidates = sorted([os.path.join(folder, name) for name in os.listdir(folder) if re.search(r"\.g\d+$", name, re.I)])
        u_candidates = sorted([os.path.join(folder, name) for name in os.listdir(folder) if re.search(r"\.u\d+$", name, re.I)])
    g_path = g_candidates[0] if g_candidates else None
    u_path = u_candidates[0] if u_candidates else None
    return g_path, u_path


def _parse_explicit_network_layout(d):
    g_path, u_path = _project_sidecar_paths(d)
    if not g_path or not os.path.exists(g_path):
        return None
    text = open(g_path, encoding="utf-8", errors="ignore").read()
    layout = {
        "junctions": {},
        "reach_storage_downstream": {},
        "storage_initial_elevation_m": {},
        "storage_areas": [],
        "connections": [],
        "lateral_structures": [],
    }
    lines = text.splitlines()
    i = 0
    current_reach = None
    current_rm = None
    while i < len(lines):
        line = lines[i].rstrip("\n")
        if line.startswith("River Reach="):
            parts = line.split("=", 1)[1].split(",")
            if len(parts) >= 2:
                river = parts[0].strip()
                reach = parts[1].strip()
                current_reach = river + "/" + reach
        elif line.startswith("Type RM Length L Ch R ="):
            parts = line.split("=", 1)[1].split(",")
            current_rm = parts[1].strip() if len(parts) >= 2 else None
        elif line.startswith("Reach Downstream Storage Area=") and current_reach:
            storage_name = line.split("=", 1)[1].strip()
            layout["reach_storage_downstream"][current_reach] = storage_name
        elif line.startswith("Storage Area="):
            storage_name = line.split("=", 1)[1].split(",")[0].strip()
            if storage_name and storage_name not in layout["storage_areas"]:
                layout["storage_areas"].append(storage_name)
        elif line.startswith("Connection="):
            conn_name = line.split("=", 1)[1].split(",")[0].strip()
            conn = {
                "name": conn_name,
                "up_storage_area": "",
                "down_storage_area": "",
                "routing_type": None,
                "weir_width": None,
                "weir_coef": None,
                "crest_elevation": None,
                "culvert_count": 0,
                "culvert_diameter": None,
                "culvert_length": None,
                "culvert_manning_n": None,
                "culvert_inlet_coef": None,
                "culvert_loss_coef": None,
                "culvert_selector_1": None,
                "culvert_selector_2": None,
                "culvert_selector_3": None,
                "culvert_us_invert": None,
                "culvert_ds_invert": None,
            }
            j = i + 1
            while j < len(lines):
                sub = lines[j].strip()
                if sub.startswith("Connection=") or sub.startswith("River Reach=") or sub.startswith("Storage Area=") or sub.startswith("Junct Name="):
                    break
                if sub.startswith("Connection Up SA="):
                    conn["up_storage_area"] = sub.split("=", 1)[1].strip()
                elif sub.startswith("Connection Dn SA="):
                    conn["down_storage_area"] = sub.split("=", 1)[1].strip()
                elif sub.startswith("Conn Routing Type="):
                    try:
                        conn["routing_type"] = int(sub.split("=", 1)[1].strip())
                    except Exception:
                        pass
                elif sub.startswith("Conn Weir WD="):
                    try:
                        width = float(sub.split("=", 1)[1].strip())
                        if str(d.get("unit_system", "")).lower() == "english":
                            width *= 0.3048
                        conn["weir_width"] = width
                    except Exception:
                        pass
                elif sub.startswith("Conn Weir Coef="):
                    try:
                        conn["weir_coef"] = _weir_coef_to_si(sub.split("=", 1)[1].strip(), d.get("unit_system", ""))
                    except Exception:
                        pass
                elif sub.startswith("Conn Weir SE="):
                    k = j + 1
                    if k < len(lines):
                        nums = re.findall(r"[-+]?\d*\.?\d+(?:[Ee][-+]?\d+)?", lines[k])
                        elevs = []
                        for idx_num, raw in enumerate(nums):
                            if idx_num % 2 == 1:
                                try:
                                    elev = float(raw)
                                    if str(d.get("unit_system", "")).lower() == "english":
                                        elev *= 0.3048
                                    elevs.append(elev)
                                except Exception:
                                    pass
                        if elevs:
                            conn["crest_elevation"] = min(elevs)
                elif sub.startswith("Connection Culv="):
                    raw = sub.split("=", 1)[1]
                    parts = [p.strip() for p in raw.split(",")]
                    try:
                        conn["culvert_count"] = int(parts[0])
                    except Exception:
                        pass
                    try:
                        conn["culvert_diameter"] = float(parts[1]) * (0.3048 if str(d.get("unit_system", "")).lower() == "english" else 1.0)
                    except Exception:
                        pass
                    try:
                        conn["culvert_length"] = float(parts[3]) * (0.3048 if str(d.get("unit_system", "")).lower() == "english" else 1.0)
                    except Exception:
                        pass
                    try:
                        conn["culvert_manning_n"] = float(parts[4])
                    except Exception:
                        pass
                    try:
                        conn["culvert_inlet_coef"] = 1.6
                    except Exception:
                        pass
                    try:
                        conn["culvert_loss_coef"] = float(parts[5])
                    except Exception:
                        pass
                    try:
                        conn["culvert_selector_1"] = int(parts[6])
                    except Exception:
                        pass
                    try:
                        conn["culvert_selector_2"] = int(parts[7])
                    except Exception:
                        pass
                    try:
                        conn["culvert_selector_3"] = int(parts[8])
                    except Exception:
                        pass
                    try:
                        conn["culvert_us_invert"] = float(parts[9]) * (0.3048 if str(d.get("unit_system", "")).lower() == "english" else 1.0)
                    except Exception:
                        pass
                    try:
                        conn["culvert_ds_invert"] = float(parts[10]) * (0.3048 if str(d.get("unit_system", "")).lower() == "english" else 1.0)
                    except Exception:
                        pass
                j += 1
            layout["connections"].append(conn)
            i = j - 1
        elif line.startswith("Lateral Weir End="):
            storage_name = line.split(",")[-1].strip()
            if current_reach and storage_name:
                lat = {
                    "reach": current_reach,
                    "storage_area": storage_name,
                    "rs_m": None,
                    "distance_to_us_xs_m": None,
                    "name": f"{current_reach}->{storage_name}",
                    "length_m": None,
                    "weir_width": None,
                    "weir_coef": None,
                    "crest_elevation": None,
                    "culvert_count": 0,
                    "culvert_diameter": None,
                    "culvert_length": None,
                    "culvert_manning_n": None,
                    "culvert_inlet_coef": None,
                    "culvert_loss_coef": None,
                    "culvert_selector_1": None,
                    "culvert_selector_2": None,
                    "culvert_selector_3": None,
                    "culvert_us_invert": None,
                    "culvert_ds_invert": None,
                }
                try:
                    if current_rm not in (None, ""):
                        rs = float(current_rm)
                        if str(d.get("unit_system", "")).lower() == "english":
                            rs *= 0.3048
                        lat["rs_m"] = rs
                except Exception:
                    pass
                j = i + 1
                while j < len(lines):
                    sub = lines[j].strip()
                    if sub.startswith("Type RM Length L Ch R =") or sub.startswith("River Reach=") or sub.startswith("Connection=") or sub.startswith("Storage Area=") or sub.startswith("Junct Name=") or sub.startswith("Lateral Weir End="):
                        break
                    if sub.startswith("Lateral Weir WD="):
                        try:
                            value = float(sub.split("=", 1)[1].strip())
                            if str(d.get("unit_system", "")).lower() == "english":
                                value *= 0.3048
                            lat["weir_width"] = value
                        except Exception:
                            pass
                    elif sub.startswith("Lateral Weir Distance="):
                        try:
                            value = float(sub.split("=", 1)[1].strip())
                            if str(d.get("unit_system", "")).lower() == "english":
                                value *= 0.3048
                            lat["distance_to_us_xs_m"] = value
                        except Exception:
                            pass
                    elif sub.startswith("Lateral Weir Coef="):
                        try:
                            lat["weir_coef"] = _weir_coef_to_si(sub.split("=", 1)[1].strip(), d.get("unit_system", ""))
                        except Exception:
                            pass
                    elif sub.startswith("Lateral Weir SE="):
                        k = j + 1
                        if k < len(lines):
                            nums = re.findall(r"[-+]?\d*\.?\d+(?:[Ee][-+]?\d+)?", lines[k])
                            stations = []
                            elevs = []
                            for idx_num, raw in enumerate(nums):
                                try:
                                    value = float(raw)
                                    if str(d.get("unit_system", "")).lower() == "english":
                                        value *= 0.3048
                                except Exception:
                                    continue
                                if idx_num % 2 == 0:
                                    stations.append(value)
                                else:
                                    try:
                                        elevs.append(value)
                                    except Exception:
                                        pass
                            if elevs:
                                lat["crest_elevation"] = min(elevs)
                            if stations:
                                lat["length_m"] = max(stations) - min(stations)
                    elif sub.startswith("LW Culv="):
                        raw = sub.split("=", 1)[1]
                        parts = [p.strip() for p in raw.split(",")]
                        try:
                            lat["culvert_count"] = int(parts[0])
                        except Exception:
                            pass
                        try:
                            lat["culvert_diameter"] = float(parts[1]) * (0.3048 if str(d.get("unit_system", "")).lower() == "english" else 1.0)
                        except Exception:
                            pass
                        try:
                            lat["culvert_length"] = float(parts[3]) * (0.3048 if str(d.get("unit_system", "")).lower() == "english" else 1.0)
                        except Exception:
                            pass
                        try:
                            lat["culvert_manning_n"] = float(parts[4])
                        except Exception:
                            pass
                        try:
                            lat["culvert_inlet_coef"] = 1.6
                        except Exception:
                            pass
                        try:
                            lat["culvert_loss_coef"] = float(parts[5])
                        except Exception:
                            pass
                        try:
                            lat["culvert_selector_1"] = int(parts[6])
                        except Exception:
                            pass
                        try:
                            lat["culvert_selector_2"] = int(parts[7])
                        except Exception:
                            pass
                        try:
                            lat["culvert_selector_3"] = int(parts[8])
                        except Exception:
                            pass
                        try:
                            lat["culvert_us_invert"] = float(parts[9]) * (0.3048 if str(d.get("unit_system", "")).lower() == "english" else 1.0)
                        except Exception:
                            pass
                        try:
                            lat["culvert_ds_invert"] = float(parts[10]) * (0.3048 if str(d.get("unit_system", "")).lower() == "english" else 1.0)
                        except Exception:
                            pass
                    j += 1
                layout["lateral_structures"].append(lat)
                i = j - 1
        elif line.startswith("Junct Name="):
            jname = line.split("=", 1)[1].strip()
            up_reaches = []
            dn_reaches = []
            j = i + 1
            while j < len(lines):
                sub = lines[j].strip()
                if sub.startswith("Junct Name=") or sub.startswith("River Reach=") or sub.startswith("Storage Area=") or sub.startswith("Connection="):
                    break
                if sub.startswith("Up River,Reach="):
                    parts = sub.split("=", 1)[1].split(",")
                    if len(parts) >= 2:
                        up_reaches.append(parts[0].strip() + "/" + parts[1].strip())
                elif sub.startswith("Dn River,Reach="):
                    parts = sub.split("=", 1)[1].split(",")
                    if len(parts) >= 2:
                        dn_reaches.append(parts[0].strip() + "/" + parts[1].strip())
                j += 1
            layout["junctions"][jname] = {"upstream_reaches": up_reaches, "downstream_reaches": dn_reaches}
            i = j - 1
        i += 1
    if u_path and os.path.exists(u_path):
        u_text = open(u_path, encoding="utf-8", errors="ignore").read()
        for match in re.finditer(r"Initial Storage Elev=([^,]+),([^\r\n]+)", u_text):
            name = match.group(1).strip()
            try:
                elev = float(match.group(2).strip())
            except Exception:
                continue
            if str(d.get("unit_system", "")).lower() == "english":
                elev *= 0.3048
            layout["storage_initial_elevation_m"][name] = elev
    return layout


def _network_layout_notes(d):
    layout = _parse_explicit_network_layout(d)
    if not layout:
        return []
    notes = []
    if layout["storage_areas"]:
        notes.append("Detected storage areas in source project: " + ", ".join(layout["storage_areas"]))
    if layout["connections"]:
        conn_names = [item["name"] for item in layout["connections"] if item.get("name")]
        notes.append(
            "Detected storage-area connections represented by HydroClaude experimental storage coupling: "
            + ", ".join(conn_names)
        )
    if layout["lateral_structures"]:
        lat_desc = [item["reach"] + " -> " + item["storage_area"] for item in layout["lateral_structures"]]
        notes.append(
            "Detected lateral structures to storage areas represented by HydroClaude experimental storage coupling: "
            + ", ".join(lat_desc)
        )
    if layout["junctions"]:
        notes.append("Topology inferred from explicit HEC-RAS junction definitions in geometry text.")
    return notes


def _unsupported_network_features(d):
    layout = _parse_explicit_network_layout(d)
    if not layout:
        return []
    unsupported = []
    return unsupported


def _compute_network_exchange_diagnostics(solver, results):
    times = None
    for key, value in results.items():
        if key in {"storage_areas", "junction_states"}:
            continue
        if isinstance(value, dict) and "times" in value:
            times = np.array(value["times"], dtype=float)
            break
    if times is None or len(times) == 0:
        return {}

    storage_hist = results.get("storage_areas", {})
    diagnostics = {"storage_connections": [], "lateral_structures": []}

    def _first_event_time(series, predicate):
        for idx, value in enumerate(series):
            if predicate(float(value)):
                return float(times[idx])
        return None

    for conn in solver.storage_connections:
        q_series = []
        q_weir_series = []
        q_culvert_series = []
        for idx, t_cur in enumerate(times):
            z_up = float(storage_hist[conn.up_storage_area]["Z_history"][idx])
            z_dn = float(storage_hist[conn.down_storage_area]["Z_history"][idx])
            q_weir, q_culvert = solver._compute_storage_connection_flow_components(conn, z_up, z_dn)
            q_series.append(float(q_weir + q_culvert))
            q_weir_series.append(float(q_weir))
            q_culvert_series.append(float(q_culvert))
        q_arr = np.array(q_series, dtype=float)
        q_weir_arr = np.array(q_weir_series, dtype=float)
        q_culvert_arr = np.array(q_culvert_series, dtype=float)
        i_max = int(np.argmax(np.abs(q_arr)))
        diagnostics["storage_connections"].append({
            "name": conn.name,
            "max_abs_q_m3s": float(np.max(np.abs(q_arr))),
            "time_of_max_s": float(times[i_max]),
            "q_end_m3s": float(q_arr[-1]),
            "mean_abs_q_m3s": float(np.mean(np.abs(q_arr))),
            "max_abs_weir_q_m3s": float(np.max(np.abs(q_weir_arr))),
            "max_abs_culvert_q_m3s": float(np.max(np.abs(q_culvert_arr))),
            "q_weir_end_m3s": float(q_weir_arr[-1]),
            "q_culvert_end_m3s": float(q_culvert_arr[-1]),
            "first_culvert_active_s": _first_event_time(q_culvert_arr, lambda q: abs(q) > 1e-9),
            "first_reverse_flow_s": _first_event_time(q_arr, lambda q: q < -1e-9),
        })

    for lat in solver.lateral_structures:
        q_series = []
        q_weir_series = []
        q_culvert_series = []
        rinfo = solver.reaches[lat.reach_name]
        reach_result = results[lat.reach_name]
        z_hist = np.array(reach_result["Z_history"], dtype=float)
        q_hist = np.array(reach_result["Q_history"], dtype=float)
        for idx, t_cur in enumerate(times):
            z_storage = float(storage_hist[lat.storage_area]["Z_history"][idx])
            z_stage = float(solver._representative_lateral_stage(z_hist[idx], rinfo.reach_data.dx, lat))
            z_head = float(solver._representative_lateral_headwater(z_hist[idx], q_hist[idx], rinfo, lat))
            q_weir, q_culvert = solver._compute_lateral_structure_flow_components(lat, z_stage, z_storage)
            q_series.append(float(q_weir + q_culvert))
            q_weir_series.append(float(q_weir))
            q_culvert_series.append(float(q_culvert))
        q_arr = np.array(q_series, dtype=float)
        q_weir_arr = np.array(q_weir_series, dtype=float)
        q_culvert_arr = np.array(q_culvert_series, dtype=float)
        i_max = int(np.argmax(np.abs(q_arr)))
        diagnostics["lateral_structures"].append({
            "name": lat.name,
            "reach_name": lat.reach_name,
            "storage_area": lat.storage_area,
            "max_abs_q_m3s": float(np.max(np.abs(q_arr))),
            "time_of_max_s": float(times[i_max]),
            "q_end_m3s": float(q_arr[-1]),
            "mean_abs_q_m3s": float(np.mean(np.abs(q_arr))),
            "max_abs_weir_q_m3s": float(np.max(np.abs(q_weir_arr))),
            "max_abs_culvert_q_m3s": float(np.max(np.abs(q_culvert_arr))),
            "q_weir_end_m3s": float(q_weir_arr[-1]),
            "q_culvert_end_m3s": float(q_culvert_arr[-1]),
            "first_culvert_active_s": _first_event_time(q_culvert_arr, lambda q: abs(q) > 1e-9),
            "first_reverse_flow_s": _first_event_time(q_arr, lambda q: q < -1e-9),
        })

    return diagnostics


def _compute_junction_stage_proxy_diagnostics(reach_topology, reach_groups, results, ws_ref, time_ref):
    times = None
    for key, value in results.items():
        if key in {"storage_areas", "junction_states"}:
            continue
        if isinstance(value, dict) and "times" in value:
            times = np.array(value["times"], dtype=float)
            break
    if times is None or len(times) == 0:
        return {}

    junction_map = {}
    for rt in reach_topology:
        if rt["ds_type"] == "junction":
            junction_map.setdefault(rt["ds_name"], []).append((rt["name"], "ds"))
        if rt["us_type"] == "junction":
            junction_map.setdefault(rt["us_name"], []).append((rt["name"], "us"))
    if not junction_map:
        return {}

    junction_results = results.get("junction_states", {})
    diagnostics = {}
    for jname, endpoints in junction_map.items():
        calc_mean_series = []
        calc_spread_series = []
        calc_junction_series = []
        ref_mean_series = []
        ref_spread_series = []
        valid_times = []
        for k, t_ref in enumerate(time_ref):
            idx = int(np.argmin(np.abs(times - t_ref)))
            if abs(times[idx] - t_ref) > max(1.0, 0.5 * abs(time_ref[1] - time_ref[0])):
                continue
            calc_vals = []
            ref_vals = []
            for rname, endpoint in endpoints:
                reach_result = results.get(rname)
                idxs = reach_groups.get(rname)
                if reach_result is None or idxs is None or len(idxs) == 0:
                    continue
                if endpoint == "us":
                    calc_vals.append(float(reach_result["Z_history"][idx][0]))
                    ref_vals.append(float(ws_ref[k][idxs[0]]))
                else:
                    calc_vals.append(float(reach_result["Z_history"][idx][-1]))
                    ref_vals.append(float(ws_ref[k][idxs[-1]]))
            if not calc_vals or not ref_vals:
                continue
            valid_times.append(float(times[idx]))
            calc_mean = float(np.mean(calc_vals))
            calc_spread = float(max(calc_vals) - min(calc_vals))
            calc_mean_series.append(calc_mean)
            calc_spread_series.append(calc_spread)
            ref_mean_series.append(float(np.mean(ref_vals)))
            ref_spread_series.append(float(max(ref_vals) - min(ref_vals)))
            if jname in junction_results:
                jseries = junction_results[jname]
                calc_junction_series.append(float(jseries["Z_history"][idx]))
                calc_mean_series[-1] = float(jseries.get("endpoint_mean_history", jseries["Z_history"])[idx])
                calc_spread_series[-1] = float(jseries.get("endpoint_spread_history", np.zeros_like(jseries["Z_history"]))[idx])
            else:
                calc_junction_series.append(calc_mean)
        if not valid_times:
            continue
        calc_j_arr = np.array(calc_junction_series, dtype=float)
        calc_mean_arr = np.array(calc_mean_series, dtype=float)
        calc_spread_arr = np.array(calc_spread_series, dtype=float)
        ref_mean_arr = np.array(ref_mean_series, dtype=float)
        ref_spread_arr = np.array(ref_spread_series, dtype=float)
        mean_bias_arr = calc_j_arr - ref_mean_arr
        spread_gap_arr = calc_spread_arr - ref_spread_arr
        i_bias = int(np.argmax(np.abs(mean_bias_arr)))
        i_spread = int(np.argmax(np.abs(spread_gap_arr)))
        diagnostics[jname] = {
            "endpoint_count": len(endpoints),
            "source": junction_results.get(jname, {}).get("source", "endpoint_mean"),
            "endpoints": [
                {"reach_name": rname, "endpoint": endpoint}
                for rname, endpoint in endpoints
            ],
            "times_s": [float(v) for v in valid_times],
            "calc_junction_stage_m": [float(v) for v in calc_j_arr],
            "calc_endpoint_mean_m": [float(v) for v in calc_mean_arr],
            "calc_endpoint_spread_m": [float(v) for v in calc_spread_arr],
            "ref_endpoint_mean_m": [float(v) for v in ref_mean_arr],
            "ref_endpoint_spread_m": [float(v) for v in ref_spread_arr],
            "max_abs_mean_bias_m": float(np.max(np.abs(mean_bias_arr))),
            "time_of_max_abs_mean_bias_s": float(valid_times[i_bias]),
            "mean_bias_at_max_m": float(mean_bias_arr[i_bias]),
            "max_abs_spread_gap_m": float(np.max(np.abs(spread_gap_arr))),
            "time_of_max_abs_spread_gap_s": float(valid_times[i_spread]),
            "spread_gap_at_max_m": float(spread_gap_arr[i_spread]),
            "mean_abs_mean_bias_m": float(np.mean(np.abs(mean_bias_arr))),
            "mean_abs_spread_gap_m": float(np.mean(np.abs(spread_gap_arr))),
        }
    return diagnostics


def _compute_junction_endpoint_bias_diagnostics(reach_topology, reach_groups, results, ws_ref, flow_ref, time_ref):
    times = None
    for key, value in results.items():
        if key in {"storage_areas", "junctions"}:
            continue
        if isinstance(value, dict) and "times" in value:
            times = np.array(value["times"], dtype=float)
            break
    if times is None or len(times) == 0:
        return {}

    junction_map = {}
    for rt in reach_topology:
        if rt["ds_type"] == "junction":
            junction_map.setdefault(rt["ds_name"], []).append((rt["name"], "ds"))
        if rt["us_type"] == "junction":
            junction_map.setdefault(rt["us_name"], []).append((rt["name"], "us"))
    if not junction_map:
        return {}

    dt_ref = abs(float(time_ref[1] - time_ref[0])) if len(time_ref) >= 2 else 1.0
    diagnostics = {}
    for jname, endpoints in junction_map.items():
        endpoint_items = []
        for rname, endpoint in endpoints:
            reach_result = results.get(rname)
            idxs = reach_groups.get(rname)
            if reach_result is None or idxs is None or len(idxs) == 0:
                continue
            z_bias_series = []
            q_bias_series = []
            valid_times = []
            for k, t_ref in enumerate(time_ref):
                idx = int(np.argmin(np.abs(times - t_ref)))
                if abs(times[idx] - t_ref) > max(1.0, 0.5 * dt_ref):
                    continue
                local_idx = 0 if endpoint == "us" else -1
                global_idx = idxs[0] if endpoint == "us" else idxs[-1]
                z_calc = float(reach_result["Z_history"][idx][local_idx])
                q_calc = float(reach_result["Q_history"][idx][local_idx])
                z_ref = float(ws_ref[k][global_idx])
                q_ref = float(flow_ref[k][global_idx]) if flow_ref is not None else float("nan")
                valid_times.append(float(times[idx]))
                z_bias_series.append(z_calc - z_ref)
                q_bias_series.append(q_calc - q_ref)
            if not valid_times:
                continue
            z_bias_arr = np.array(z_bias_series, dtype=float)
            q_bias_arr = np.array(q_bias_series, dtype=float)
            i_z = int(np.argmax(np.abs(z_bias_arr)))
            i_q = int(np.argmax(np.abs(q_bias_arr)))
            endpoint_items.append({
                "reach_name": rname,
                "endpoint": endpoint,
                "times_s": [float(v) for v in valid_times],
                "z_bias_m": [float(v) for v in z_bias_arr],
                "q_bias_m3s": [float(v) for v in q_bias_arr],
                "max_abs_z_bias_m": float(np.max(np.abs(z_bias_arr))),
                "time_of_max_abs_z_bias_s": float(valid_times[i_z]),
                "z_bias_at_max_m": float(z_bias_arr[i_z]),
                "mean_abs_z_bias_m": float(np.mean(np.abs(z_bias_arr))),
                "max_abs_q_bias_m3s": float(np.max(np.abs(q_bias_arr))),
                "time_of_max_abs_q_bias_s": float(valid_times[i_q]),
                "q_bias_at_max_m3s": float(q_bias_arr[i_q]),
                "mean_abs_q_bias_m3s": float(np.mean(np.abs(q_bias_arr))),
            })
        if endpoint_items:
            diagnostics[jname] = endpoint_items
    return diagnostics


def _compute_branch_cell_term_bias_diagnostics(
    solver,
    reach_topology,
    reach_groups,
    results,
    ws_ref,
    flow_ref,
    time_ref,
    junction_names=None,
    t_start=None,
    t_end=None,
    snapshot_times_s=None,
):
    if flow_ref is None:
        return {}
    times = None
    for key, value in results.items():
        if key in {"storage_areas", "junctions"}:
            continue
        if isinstance(value, dict) and "times" in value:
            times = np.array(value["times"], dtype=float)
            break
    if times is None or len(times) < 2 or len(time_ref) < 2:
        return {}

    junction_map = {}
    for rt in reach_topology:
        if rt["ds_type"] == "junction":
            junction_map.setdefault(rt["ds_name"], []).append((rt["name"], "ds"))
        if rt["us_type"] == "junction":
            junction_map.setdefault(rt["us_name"], []).append((rt["name"], "us"))
    if not junction_map:
        return {}

    dt_ref = abs(float(time_ref[1] - time_ref[0]))
    snapshot_targets = [float(v) for v in (snapshot_times_s or [])]
    diagnostics = {}
    selected_junctions = set(junction_names or [])
    for jname, endpoints in junction_map.items():
        if selected_junctions and jname not in selected_junctions:
            continue
        branch_items = []
        for rname, endpoint in endpoints:
            reach_result = results.get(rname)
            idxs = reach_groups.get(rname)
            local_solver = solver.solvers.get(rname)
            if reach_result is None or idxs is None or local_solver is None or len(idxs) < 2:
                continue
            term_diff_series = {
                "continuity_residual": [],
                "continuity_storage_term": [],
                "continuity_flux_term_np1": [],
                "continuity_flux_term_n": [],
                "momentum_residual": [],
                "momentum_local_inertia_term": [],
                "momentum_convective_term": [],
                "momentum_pressure_term": [],
                "momentum_friction_plus_loss_term": [],
            }
            property_diff_series = {
                "depth_mean_m": [],
                "A_4pt_m2": [],
                "K_4pt": [],
                "Q_4pt_m3s": [],
                "dZ_4pt_m": [],
                "Sf": [],
                "Sf_loss_4pt": [],
            }
            valid_times = []
            cell_index = 0 if endpoint == "us" else len(idxs) - 2
            local_calc_index = 0 if endpoint == "us" else -1
            global_calc_index = idxs[0] if endpoint == "us" else idxs[-1]
            for k in range(1, len(time_ref)):
                t_ref = float(time_ref[k])
                if t_start is not None and t_ref < float(t_start) - 1e-9:
                    continue
                if t_end is not None and t_ref > float(t_end) + 1e-9:
                    continue
                idx = int(np.argmin(np.abs(times - t_ref)))
                if abs(times[idx] - t_ref) > max(1.0, 0.5 * dt_ref):
                    continue
                if idx <= 0:
                    continue

                Z_calc = np.array(reach_result["Z_history"][idx], dtype=float)
                Q_calc = np.array(reach_result["Q_history"][idx], dtype=float)
                Z_calc_old = np.array(reach_result["Z_history"][idx - 1], dtype=float)
                Q_calc_old = np.array(reach_result["Q_history"][idx - 1], dtype=float)
                dt_calc = float(times[idx] - times[idx - 1])
                if dt_calc <= 0.0:
                    continue

                A, B, K, bm, dKdZ = local_solver._compute_hydraulics_all(Z_calc, Q_calc)
                A_n, B_n, K_n, bm_n, _dKdZ_n = local_solver._compute_hydraulics_all(Z_calc_old, Q_calc_old)
                calc_terms = local_solver._compute_cell_equation_terms(
                    Z_calc, Q_calc, Z_calc_old, Q_calc_old,
                    A, B, K, bm, dKdZ,
                    A_n, B_n, K_n, bm_n,
                    dt_calc, cell_index,
                )

                Z_ref = np.array(ws_ref[k][idxs], dtype=float)
                Q_ref = np.array(flow_ref[k][idxs], dtype=float)
                Z_ref_old = np.array(ws_ref[k - 1][idxs], dtype=float)
                Q_ref_old = np.array(flow_ref[k - 1][idxs], dtype=float)
                A, B, K, bm, dKdZ = local_solver._compute_hydraulics_all(Z_ref, Q_ref)
                A_n, B_n, K_n, bm_n, _dKdZ_n = local_solver._compute_hydraulics_all(Z_ref_old, Q_ref_old)
                ref_terms = local_solver._compute_cell_equation_terms(
                    Z_ref, Q_ref, Z_ref_old, Q_ref_old,
                    A, B, K, bm, dKdZ,
                    A_n, B_n, K_n, bm_n,
                    dt_ref, cell_index,
                )

                valid_times.append(float(times[idx]))
                term_diff_series["continuity_residual"].append(
                    float(calc_terms["continuity_residual"] - ref_terms["continuity_residual"])
                )
                term_diff_series["continuity_storage_term"].append(
                    float(calc_terms["continuity_storage_term"] - ref_terms["continuity_storage_term"])
                )
                term_diff_series["continuity_flux_term_np1"].append(
                    float(calc_terms["continuity_flux_term_np1"] - ref_terms["continuity_flux_term_np1"])
                )
                term_diff_series["continuity_flux_term_n"].append(
                    float(calc_terms["continuity_flux_term_n"] - ref_terms["continuity_flux_term_n"])
                )
                term_diff_series["momentum_residual"].append(
                    float(calc_terms["momentum_residual"] - ref_terms["momentum_residual"])
                )
                term_diff_series["momentum_local_inertia_term"].append(
                    float(calc_terms["momentum_local_inertia_term"] - ref_terms["momentum_local_inertia_term"])
                )
                term_diff_series["momentum_convective_term"].append(
                    float(
                        (calc_terms["momentum_convective_term_np1"] + calc_terms["momentum_convective_term_n"])
                        - (ref_terms["momentum_convective_term_np1"] + ref_terms["momentum_convective_term_n"])
                    )
                )
                term_diff_series["momentum_pressure_term"].append(
                    float(calc_terms["momentum_pressure_term"] - ref_terms["momentum_pressure_term"])
                )
                term_diff_series["momentum_friction_plus_loss_term"].append(
                    float(
                        (calc_terms["momentum_friction_term"] + calc_terms["momentum_minor_loss_term"])
                        - (ref_terms["momentum_friction_term"] + ref_terms["momentum_minor_loss_term"])
                    )
                )
                property_diff_series["depth_mean_m"].append(
                    float(
                        0.5 * (calc_terms["depth_L_m"] + calc_terms["depth_R_m"])
                        - 0.5 * (ref_terms["depth_L_m"] + ref_terms["depth_R_m"])
                    )
                )
                for name in ["A_4pt_m2", "K_4pt", "Q_4pt_m3s", "dZ_4pt_m", "Sf", "Sf_loss_4pt"]:
                    property_diff_series[name].append(float(calc_terms[name] - ref_terms[name]))

            if not valid_times:
                continue
            summary = {
                "reach_name": rname,
                "endpoint": endpoint,
                "cell_location": "first_cell" if endpoint == "us" else "last_cell",
                "calc_endpoint_index": int(local_calc_index),
                "ref_endpoint_index": int(global_calc_index),
                "times_s": [float(v) for v in valid_times],
                "snapshots": [],
            }
            ranking_keys = []
            for term_name, values in term_diff_series.items():
                arr = np.array(values, dtype=float)
                i_max = int(np.argmax(np.abs(arr)))
                summary[term_name + "_diff"] = [float(v) for v in arr]
                summary["max_abs_" + term_name + "_diff"] = float(np.max(np.abs(arr)))
                summary["time_of_max_abs_" + term_name + "_diff_s"] = float(valid_times[i_max])
                summary[term_name + "_diff_at_max"] = float(arr[i_max])
                summary["mean_abs_" + term_name + "_diff"] = float(np.mean(np.abs(arr)))
                ranking_keys.append(float(np.max(np.abs(arr))) if "momentum_" in term_name else 0.0)
            for prop_name, values in property_diff_series.items():
                arr = np.array(values, dtype=float)
                i_max = int(np.argmax(np.abs(arr)))
                summary[prop_name + "_diff"] = [float(v) for v in arr]
                summary["max_abs_" + prop_name + "_diff"] = float(np.max(np.abs(arr)))
                summary["time_of_max_abs_" + prop_name + "_diff_s"] = float(valid_times[i_max])
                summary[prop_name + "_diff_at_max"] = float(arr[i_max])
                summary["mean_abs_" + prop_name + "_diff"] = float(np.mean(np.abs(arr)))
            summary["dominant_momentum_term"] = max(
                [
                    "momentum_local_inertia_term",
                    "momentum_convective_term",
                    "momentum_pressure_term",
                    "momentum_friction_plus_loss_term",
                ],
                key=lambda name: summary["mean_abs_" + name + "_diff"],
            )
            summary["max_abs_momentum_term_diff"] = float(max(ranking_keys))
            if snapshot_targets:
                for target_t in snapshot_targets:
                    idx_snap = min(range(len(valid_times)), key=lambda ii: abs(valid_times[ii] - target_t))
                    snap_t = float(valid_times[idx_snap])
                    ref_k = min(range(1, len(time_ref)), key=lambda kk: abs(float(time_ref[kk]) - snap_t))
                    idx = int(np.argmin(np.abs(times - snap_t)))
                    Z_calc = np.array(reach_result["Z_history"][idx], dtype=float)
                    Q_calc = np.array(reach_result["Q_history"][idx], dtype=float)
                    Z_calc_old = np.array(reach_result["Z_history"][idx - 1], dtype=float)
                    Q_calc_old = np.array(reach_result["Q_history"][idx - 1], dtype=float)
                    dt_calc = float(times[idx] - times[idx - 1])
                    A, B, K, bm, dKdZ = local_solver._compute_hydraulics_all(Z_calc, Q_calc)
                    A_n, B_n, K_n, bm_n, _dKdZ_n = local_solver._compute_hydraulics_all(Z_calc_old, Q_calc_old)
                    calc_terms = local_solver._compute_cell_equation_terms(
                        Z_calc, Q_calc, Z_calc_old, Q_calc_old,
                        A, B, K, bm, dKdZ,
                        A_n, B_n, K_n, bm_n,
                        dt_calc, cell_index,
                    )
                    Z_ref = np.array(ws_ref[ref_k][idxs], dtype=float)
                    Q_ref = np.array(flow_ref[ref_k][idxs], dtype=float)
                    Z_ref_old = np.array(ws_ref[ref_k - 1][idxs], dtype=float)
                    Q_ref_old = np.array(flow_ref[ref_k - 1][idxs], dtype=float)
                    A, B, K, bm, dKdZ = local_solver._compute_hydraulics_all(Z_ref, Q_ref)
                    A_n, B_n, K_n, bm_n, _dKdZ_n = local_solver._compute_hydraulics_all(Z_ref_old, Q_ref_old)
                    ref_terms = local_solver._compute_cell_equation_terms(
                        Z_ref, Q_ref, Z_ref_old, Q_ref_old,
                        A, B, K, bm, dKdZ,
                        A_n, B_n, K_n, bm_n,
                        dt_ref, cell_index,
                    )
                    summary["snapshots"].append({
                        "requested_time_s": float(target_t),
                        "time_s": float(snap_t),
                        "calc": {
                            "momentum_pressure_term": float(calc_terms["momentum_pressure_term"]),
                            "momentum_friction_plus_loss_term": float(calc_terms["momentum_friction_term"] + calc_terms["momentum_minor_loss_term"]),
                            "momentum_local_inertia_term": float(calc_terms["momentum_local_inertia_term"]),
                            "momentum_convective_term": float(calc_terms["momentum_convective_term_np1"] + calc_terms["momentum_convective_term_n"]),
                            "depth_L_m": float(calc_terms["depth_L_m"]),
                            "depth_R_m": float(calc_terms["depth_R_m"]),
                            "depth_mean_m": float(0.5 * (calc_terms["depth_L_m"] + calc_terms["depth_R_m"])),
                            "A_L_m2": float(calc_terms["A_L_m2"]),
                            "A_R_m2": float(calc_terms["A_R_m2"]),
                            "A_4pt_m2": float(calc_terms["A_4pt_m2"]),
                            "K_L": float(calc_terms["K_L"]),
                            "K_R": float(calc_terms["K_R"]),
                            "K_4pt": float(calc_terms["K_4pt"]),
                            "Q_4pt_m3s": float(calc_terms["Q_4pt_m3s"]),
                            "dZ_4pt_m": float(calc_terms["dZ_4pt_m"]),
                            "Sf": float(calc_terms["Sf"]),
                            "Sf_loss_4pt": float(calc_terms["Sf_loss_4pt"]),
                        },
                        "ref": {
                            "momentum_pressure_term": float(ref_terms["momentum_pressure_term"]),
                            "momentum_friction_plus_loss_term": float(ref_terms["momentum_friction_term"] + ref_terms["momentum_minor_loss_term"]),
                            "momentum_local_inertia_term": float(ref_terms["momentum_local_inertia_term"]),
                            "momentum_convective_term": float(ref_terms["momentum_convective_term_np1"] + ref_terms["momentum_convective_term_n"]),
                            "depth_L_m": float(ref_terms["depth_L_m"]),
                            "depth_R_m": float(ref_terms["depth_R_m"]),
                            "depth_mean_m": float(0.5 * (ref_terms["depth_L_m"] + ref_terms["depth_R_m"])),
                            "A_L_m2": float(ref_terms["A_L_m2"]),
                            "A_R_m2": float(ref_terms["A_R_m2"]),
                            "A_4pt_m2": float(ref_terms["A_4pt_m2"]),
                            "K_L": float(ref_terms["K_L"]),
                            "K_R": float(ref_terms["K_R"]),
                            "K_4pt": float(ref_terms["K_4pt"]),
                            "Q_4pt_m3s": float(ref_terms["Q_4pt_m3s"]),
                            "dZ_4pt_m": float(ref_terms["dZ_4pt_m"]),
                            "Sf": float(ref_terms["Sf"]),
                            "Sf_loss_4pt": float(ref_terms["Sf_loss_4pt"]),
                        },
                    })
            branch_items.append(summary)
        if branch_items:
            diagnostics[jname] = branch_items
    return diagnostics


def _compute_branch_cell_snapshot_diagnostics(
    solver,
    reach_groups,
    reach_infos,
    results,
    ws_ref,
    flow_ref,
    hecras_pt,
    time_ref,
    branch_targets,
    time_targets_s,
):
    if flow_ref is None or not branch_targets or not time_targets_s:
        return []
    times = None
    for key, value in results.items():
        if key in {"storage_areas", "junctions"}:
            continue
        if isinstance(value, dict) and "times" in value:
            times = np.array(value["times"], dtype=float)
            break
    if times is None or len(times) < 2 or len(time_ref) < 2:
        return []

    reach_info_map = {ri.name: ri for ri in reach_infos}
    dt_ref = abs(float(time_ref[1] - time_ref[0]))
    snapshots = []

    def _interp_hecras_pt(pt_item, stage_m):
        if not pt_item:
            return None
        elev = np.array(pt_item.get("elevations_m", []), dtype=float)
        if elev.size == 0:
            return None
        out = {"stage_m": float(stage_m)}
        for src_key, out_key in [
            ("A_m2", "A_m2"),
            ("K_m3s", "K_m3s"),
            ("B_m", "B_m"),
            ("beta", "beta"),
        ]:
            vals = np.array(pt_item.get(src_key, []), dtype=float)
            if vals.size != elev.size:
                continue
            out[out_key] = float(np.interp(stage_m, elev, vals, left=vals[0], right=vals[-1]))
        return out

    def _solver_section_snapshot_from_arrays(rinfo, local_solver, Z_arr, Q_arr, local_index):
        A_arr, B_arr, K_arr, _bm_arr, _dKdZ_arr = local_solver._compute_hydraulics_all(
            np.array(Z_arr, dtype=float),
            np.array(Q_arr, dtype=float),
        )
        bed = float(rinfo.reach_data.bed_elevation[local_index])
        stage_m = float(Z_arr[local_index])
        return {
            "stage_m": stage_m,
            "depth_m": float(max(stage_m - bed, 0.05)),
            "A_m2": float(A_arr[local_index]),
            "K_m3s": float(K_arr[local_index]),
            "B_m": float(B_arr[local_index]),
        }

    for target in branch_targets:
        jname = str(target.get("junction_name", ""))
        rname = str(target.get("reach_name", ""))
        cell_location = str(target.get("cell_location", ""))
        endpoint = str(target.get("endpoint", "us" if cell_location == "first_cell" else "ds"))
        idxs = reach_groups.get(rname)
        reach_result = results.get(rname)
        local_solver = solver.solvers.get(rname)
        rinfo = reach_info_map.get(rname)
        if idxs is None or reach_result is None or local_solver is None or rinfo is None or len(idxs) < 2:
            continue
        cell_index = 0 if endpoint == "us" else len(idxs) - 2
        xs_local_index = 0 if endpoint == "us" else len(idxs) - 1
        xs_global_index = idxs[0] if endpoint == "us" else idxs[-1]
        pt_item = None
        if hecras_pt is not None and xs_global_index < len(hecras_pt):
            pt_item = hecras_pt[xs_global_index]
        for t_target in time_targets_s:
            idx_ref = int(np.argmin(np.abs(np.array(time_ref, dtype=float) - float(t_target))))
            t_ref = float(time_ref[idx_ref])
            idx_calc = int(np.argmin(np.abs(times - t_ref)))
            if idx_ref <= 0 or idx_calc <= 0:
                continue
            if abs(float(times[idx_calc]) - t_ref) > max(1.0, 0.5 * dt_ref):
                continue

            Z_calc = np.array(reach_result["Z_history"][idx_calc], dtype=float)
            Q_calc = np.array(reach_result["Q_history"][idx_calc], dtype=float)
            Z_calc_old = np.array(reach_result["Z_history"][idx_calc - 1], dtype=float)
            Q_calc_old = np.array(reach_result["Q_history"][idx_calc - 1], dtype=float)
            dt_calc = float(times[idx_calc] - times[idx_calc - 1])
            if dt_calc <= 0.0:
                continue
            A, B, K, bm, dKdZ = local_solver._compute_hydraulics_all(Z_calc, Q_calc)
            A_n, B_n, K_n, bm_n, _dKdZ_n = local_solver._compute_hydraulics_all(Z_calc_old, Q_calc_old)
            calc_terms = local_solver._compute_cell_equation_terms(
                Z_calc, Q_calc, Z_calc_old, Q_calc_old,
                A, B, K, bm, dKdZ,
                A_n, B_n, K_n, bm_n,
                dt_calc, cell_index,
            )

            Z_ref = np.array(ws_ref[idx_ref][idxs], dtype=float)
            Q_ref = np.array(flow_ref[idx_ref][idxs], dtype=float)
            Z_ref_old = np.array(ws_ref[idx_ref - 1][idxs], dtype=float)
            Q_ref_old = np.array(flow_ref[idx_ref - 1][idxs], dtype=float)
            A, B, K, bm, dKdZ = local_solver._compute_hydraulics_all(Z_ref, Q_ref)
            A_n, B_n, K_n, bm_n, _dKdZ_n = local_solver._compute_hydraulics_all(Z_ref_old, Q_ref_old)
            ref_terms = local_solver._compute_cell_equation_terms(
                Z_ref, Q_ref, Z_ref_old, Q_ref_old,
                A, B, K, bm, dKdZ,
                A_n, B_n, K_n, bm_n,
                dt_ref, cell_index,
            )

            snapshots.append({
                "junction_name": jname,
                "reach_name": rname,
                "endpoint": endpoint,
                "cell_location": "first_cell" if endpoint == "us" else "last_cell",
                "xs_local_index": int(xs_local_index),
                "xs_global_index": int(xs_global_index),
                "time_s": float(t_ref),
                "calc": dict(calc_terms),
                "ref": dict(ref_terms),
                "diff": {
                    key: float(calc_terms[key] - ref_terms[key])
                    for key in [
                        "depth_L_m",
                        "depth_R_m",
                        "A_L_m2",
                        "A_R_m2",
                        "A_4pt_m2",
                        "K_L",
                        "K_R",
                        "K_4pt",
                        "Q_4pt_m3s",
                        "dZ_4pt_m",
                        "Sf",
                        "Sf_loss_4pt",
                        "momentum_pressure_term",
                        "momentum_friction_term",
                        "momentum_minor_loss_term",
                        "momentum_local_inertia_term",
                        "momentum_convective_term_np1",
                        "momentum_convective_term_n",
                    ]
                },
                "hecras_input_compare": {
                    "calc_stage": {
                        "solver": _solver_section_snapshot_from_arrays(
                            rinfo,
                            local_solver,
                            Z_calc,
                            Q_calc,
                            xs_local_index,
                        ),
                        "hecras_pt": _interp_hecras_pt(pt_item, float(Z_calc[xs_local_index])),
                    },
                    "ref_stage": {
                        "solver": _solver_section_snapshot_from_arrays(
                            rinfo,
                            local_solver,
                            Z_ref,
                            Q_ref,
                            xs_local_index,
                        ),
                        "hecras_pt": _interp_hecras_pt(pt_item, float(Z_ref[xs_local_index])),
                    },
                },
            })
    snapshots.sort(key=lambda item: (item["junction_name"], item["reach_name"], item["time_s"]))
    return snapshots


def _summarize_junction_stage_biases(junction_stage_proxy, solver_diagnostics):
    if not junction_stage_proxy:
        return []
    solver_diagnostics = dict(solver_diagnostics or {})
    explicit_states = set(solver_diagnostics.get("junction_state_names", []) or [])
    iter_clip_counts = dict(solver_diagnostics.get("junction_iter_clip_counts", {}) or {})
    step_clip_counts = dict(solver_diagnostics.get("junction_step_clip_counts", {}) or {})
    ranking = []
    for jname, item in junction_stage_proxy.items():
        ranking.append({
            "junction_name": jname,
            "explicit_state": bool(jname in explicit_states),
            "source": item.get("source", "endpoint_mean"),
            "endpoint_count": int(item.get("endpoint_count", 0)),
            "max_abs_mean_bias_m": float(item.get("max_abs_mean_bias_m", 0.0)),
            "time_of_max_abs_mean_bias_s": float(item.get("time_of_max_abs_mean_bias_s", 0.0)),
            "mean_bias_at_max_m": float(item.get("mean_bias_at_max_m", 0.0)),
            "mean_abs_mean_bias_m": float(item.get("mean_abs_mean_bias_m", 0.0)),
            "max_abs_spread_gap_m": float(item.get("max_abs_spread_gap_m", 0.0)),
            "time_of_max_abs_spread_gap_s": float(item.get("time_of_max_abs_spread_gap_s", 0.0)),
            "spread_gap_at_max_m": float(item.get("spread_gap_at_max_m", 0.0)),
            "mean_abs_spread_gap_m": float(item.get("mean_abs_spread_gap_m", 0.0)),
            "junction_iter_clip_count": int(iter_clip_counts.get(jname, 0)),
            "junction_step_clip_count": int(step_clip_counts.get(jname, 0)),
        })
    ranking.sort(
        key=lambda item: (
            item["max_abs_mean_bias_m"],
            item["mean_abs_mean_bias_m"],
            item["max_abs_spread_gap_m"],
        ),
        reverse=True,
    )
    return ranking


def _summarize_branch_cell_term_biases(branch_cell_term_bias):
    if not branch_cell_term_bias:
        return []
    ranking = []
    for jname, items in branch_cell_term_bias.items():
        for item in items:
            ranking.append({
                "junction_name": jname,
                "reach_name": item.get("reach_name"),
                "endpoint": item.get("endpoint"),
                "cell_location": item.get("cell_location"),
                "dominant_momentum_term": item.get("dominant_momentum_term"),
                "max_abs_momentum_term_diff": float(item.get("max_abs_momentum_term_diff", 0.0)),
                "max_abs_momentum_pressure_term_diff": float(item.get("max_abs_momentum_pressure_term_diff", 0.0)),
                "max_abs_momentum_friction_plus_loss_term_diff": float(item.get("max_abs_momentum_friction_plus_loss_term_diff", 0.0)),
                "max_abs_momentum_convective_term_diff": float(item.get("max_abs_momentum_convective_term_diff", 0.0)),
                "max_abs_momentum_local_inertia_term_diff": float(item.get("max_abs_momentum_local_inertia_term_diff", 0.0)),
                "mean_abs_momentum_pressure_term_diff": float(item.get("mean_abs_momentum_pressure_term_diff", 0.0)),
                "mean_abs_momentum_friction_plus_loss_term_diff": float(item.get("mean_abs_momentum_friction_plus_loss_term_diff", 0.0)),
                "mean_abs_momentum_convective_term_diff": float(item.get("mean_abs_momentum_convective_term_diff", 0.0)),
                "mean_abs_momentum_local_inertia_term_diff": float(item.get("mean_abs_momentum_local_inertia_term_diff", 0.0)),
            })
    ranking.sort(
        key=lambda item: (
            item["max_abs_momentum_term_diff"],
            item["mean_abs_momentum_pressure_term_diff"],
            item["mean_abs_momentum_friction_plus_loss_term_diff"],
        ),
        reverse=True,
    )
    return ranking


def _load_storage_area_data(d):
    """Load storage-area geometry and initial stages from source HDF."""
    source_hdf = d.get("source_hdf")
    if not source_hdf or not os.path.exists(source_hdf):
        return {}

    is_english = str(d.get("unit_system", "")).lower() == "english"
    lf = 0.3048 if is_english else 1.0
    af = lf * lf
    vf = lf * lf * lf
    storage_data = {}
    try:
        with h5py.File(source_hdf, "r") as hdf:
            attrs = hdf.get("Geometry/Storage Areas/Attributes")
            info = hdf.get("Geometry/Storage Areas/Volume Elevation Info")
            vals = hdf.get("Geometry/Storage Areas/Volume Elevation Values")
            init_names = hdf.get("Event Conditions/Unsteady/Initial Conditions/Storage Area Names")
            init_elev = hdf.get("Event Conditions/Unsteady/Initial Conditions/Storage Area Elevations")
            init_map = {}
            if init_names is not None and init_elev is not None:
                for raw_name, raw_stage in zip(init_names[:], init_elev[:]):
                    name = raw_name.decode("utf-8", errors="ignore").strip()
                    init_map[name] = float(raw_stage) * lf
            if attrs is None:
                return {}
            attrs_arr = attrs[:]
            info_arr = info[:] if info is not None else None
            vals_arr = vals[:] if vals is not None else None
            for idx, row in enumerate(attrs_arr):
                name = row["Name"].decode("utf-8", errors="ignore").strip()
                mode = row["Mode"].decode("utf-8", errors="ignore").strip()
                item = {
                    "name": name,
                    "mode": mode,
                    "initial_stage": init_map.get(name),
                    "storage_elevations": None,
                    "storage_volumes": None,
                    "area": None,
                    "min_elevation": None,
                }
                if mode == "Elev Vol RC" and info_arr is not None and vals_arr is not None:
                    start, count = info_arr[idx]
                    if count > 0:
                        rows = vals_arr[start:start + count]
                        item["storage_volumes"] = rows[:, 0] * vf
                        item["storage_elevations"] = rows[:, 1] * lf
                else:
                    area = float(row["Avg Area"]) if not np.isnan(row["Avg Area"]) else None
                    min_elev = float(row["Min Elev"]) if not np.isnan(row["Min Elev"]) else None
                    item["area"] = area * af if area is not None else None
                    item["min_elevation"] = min_elev * lf if min_elev is not None else None
                storage_data[name] = item
    except Exception:
        return {}
    return storage_data


def _load_hecras_junction_input_data(d):
    source_hdf = d.get("source_hdf")
    if not source_hdf or not os.path.exists(source_hdf):
        return {"junction_attrs": {}, "reach_connections": {}}
    out = {"junction_attrs": {}, "reach_connections": {}}
    try:
        with h5py.File(source_hdf, "r") as hdf:
            attrs = hdf.get("Geometry/Junctions/Attributes")
            if attrs is not None:
                for idx, row in enumerate(attrs[:]):
                    name = row["Name"].decode("utf-8", errors="ignore").strip()
                    out["junction_attrs"][name] = {
                        "hecras_index": int(idx),
                        "momentum": bool(int(row["Momentum"])),
                        "add_weight": bool(int(row["Add Weight"])),
                        "add_friction": bool(int(row["Add Friction"])),
                        "unsteady_energy": bool(int(row["Unsteady Energy"])),
                    }
            rc_root = "Geometry/GeomPreprocess/Reach Connections"
            if rc_root in hdf:
                rc = hdf[rc_root]
                for key in [
                    "ICSD", "ICSU", "IDSTYP", "IUSTYP",
                    "IRDCON", "IRUCON", "NDCON", "NUCON",
                    "NNDCON", "NNUCON", "QSIGND", "QSIGNU",
                ]:
                    if key in rc:
                        out["reach_connections"][key] = rc[key][:].tolist()
    except Exception:
        return {"junction_attrs": {}, "reach_connections": {}}
    return out


def _load_hecras_centerline_input_data(d):
    source_hdf = d.get("source_hdf")
    if not source_hdf or not os.path.exists(source_hdf):
        return {}
    out = {}
    lf = 0.3048 if str(d.get("unit_system", "")).lower() == "english" else 1.0
    try:
        with h5py.File(source_hdf, "r") as hdf:
            attrs = hdf.get("Geometry/River Centerlines/Attributes")
            if attrs is None:
                return out
            for row in attrs[:]:
                river = row["River Name"].decode("utf-8", errors="ignore").strip()
                reach = row["Reach Name"].decode("utf-8", errors="ignore").strip()
                key = river + "/" + reach
                us_type = row["US Type"].decode("utf-8", errors="ignore").strip()
                us_name = row["US Name"].decode("utf-8", errors="ignore").strip()
                ds_type = row["DS Type"].decode("utf-8", errors="ignore").strip()
                ds_name = row["DS Name"].decode("utf-8", errors="ignore").strip()
                us_dist = float(row["Junction to US XS"]) * lf if np.isfinite(row["Junction to US XS"]) else None
                ds_dist = float(row["DS XS to Junction"]) * lf if np.isfinite(row["DS XS to Junction"]) else None
                out[key] = {
                    "us_type_raw": us_type,
                    "us_name_raw": us_name,
                    "ds_type_raw": ds_type,
                    "ds_name_raw": ds_name,
                    "us_junction_distance_m": us_dist,
                    "ds_junction_distance_m": ds_dist,
                }
    except Exception:
        return {}
    return out


def _load_hecras_preprocess_connectivity_data(d):
    source_hdf = d.get("source_hdf")
    if not source_hdf or not os.path.exists(source_hdf):
        return {"reach_rows": {}, "reach_endpoint_signs": {}, "junction_endpoint_signs": {}, "junction_master_hints": {}}
    out = {"reach_rows": {}, "reach_endpoint_signs": {}, "junction_endpoint_signs": {}, "junction_master_hints": {}}
    try:
        centerline = _load_hecras_centerline_input_data(d)
        with h5py.File(source_hdf, "r") as hdf:
            rc = hdf.get("Geometry/GeomPreprocess/Reach Connections")
            node2ics = hdf.get("Geometry/GeomPreprocess/NODE2ICS")
            node_info = hdf.get("Geometry/GeomPreprocess/Node Info/Node Attributes")
            if rc is None or node2ics is None or node_info is None:
                return out
            ics2node = np.array(node2ics["ICS2NODE"][:], dtype=int)
            icsu = np.array(rc["ICSU"][:], dtype=int)
            icsd = np.array(rc["ICSD"][:], dtype=int)
            iustyp = np.array(rc["IUSTYP"][:], dtype=int)
            idstyp = np.array(rc["IDSTYP"][:], dtype=int)
            irucon = np.array(rc["IRUCON"][:], dtype=int)
            irdcon = np.array(rc["IRDCON"][:], dtype=int)
            nucon = np.array(rc["NUCON"][:], dtype=int)
            ndcon = np.array(rc["NDCON"][:], dtype=int)
            nnucon = np.array(rc["NNUCON"][:], dtype=int)
            nndcon = np.array(rc["NNDCON"][:], dtype=int)
            qsignu = np.array(rc["QSIGNU"][:], dtype=float)
            qsignd = np.array(rc["QSIGND"][:], dtype=float)

            def _node_row(node_index_1b):
                if node_index_1b <= 0 or node_index_1b > len(node_info):
                    return None
                return node_info[node_index_1b - 1]

            def _node_reach_name(node_index_1b):
                row = _node_row(node_index_1b)
                if row is None:
                    return None
                river = row["River"].decode("utf-8", errors="ignore").strip() if "River" in row.dtype.names else row[0].decode("utf-8", errors="ignore").strip()
                reach = row["Reach"].decode("utf-8", errors="ignore").strip() if "Reach" in row.dtype.names else row[1].decode("utf-8", errors="ignore").strip()
                node_type = row["Type"].decode("utf-8", errors="ignore").strip() if "Type" in row.dtype.names else row[4].decode("utf-8", errors="ignore").strip()
                if node_type != "Cross Section":
                    return None
                if not river or not reach:
                    return None
                return river + "/" + reach

            reach_rows_by_index = {}
            for idx in range(len(icsu)):
                u_node = int(ics2node[int(icsu[idx]) - 1]) if 0 < int(icsu[idx]) <= len(ics2node) else 0
                d_node = int(ics2node[int(icsd[idx]) - 1]) if 0 < int(icsd[idx]) <= len(ics2node) else 0
                rname = _node_reach_name(u_node) or _node_reach_name(d_node)
                if not rname:
                    continue
                reach_rows_by_index[idx + 1] = rname
                out["reach_rows"][rname] = {
                    "row_index_1b": int(idx + 1),
                    "icsu_1b": int(icsu[idx]),
                    "icsd_1b": int(icsd[idx]),
                    "iustyp": int(iustyp[idx]),
                    "idstyp": int(idstyp[idx]),
                }

            endpoint_signs = {}

            def _assign_endpoint_sign(rname, endpoint, sign):
                if not rname or abs(float(sign)) <= 1e-9:
                    return
                endpoint_signs[f"{rname}|{endpoint}"] = float(sign)

            for idx in range(len(icsu)):
                rname = reach_rows_by_index.get(idx + 1)
                if not rname:
                    continue
                for j in range(int(qsignd.shape[1])):
                    sign = float(qsignd[idx, j])
                    if abs(sign) <= 1e-9:
                        continue
                    if int(ndcon[idx, j]) == int(icsd[idx]):
                        _assign_endpoint_sign(rname, "ds", sign)
                    conn_idx = int(irdcon[idx, j])
                    if conn_idx > 0:
                        _assign_endpoint_sign(reach_rows_by_index.get(conn_idx), "us", sign)
                for j in range(int(qsignu.shape[1])):
                    sign = float(qsignu[idx, j])
                    if abs(sign) <= 1e-9:
                        continue
                    if int(nucon[idx, j]) == int(icsu[idx]):
                        _assign_endpoint_sign(rname, "us", sign)
                    conn_idx = int(irucon[idx, j])
                    if conn_idx > 0:
                        _assign_endpoint_sign(reach_rows_by_index.get(conn_idx), "ds", sign)

            out["reach_endpoint_signs"] = dict(endpoint_signs)
            for rname, info in centerline.items():
                if info.get("us_type_raw", "").strip().lower() == "junction":
                    sign = endpoint_signs.get(f"{rname}|us")
                    if sign is not None:
                        out["junction_endpoint_signs"].setdefault(info["us_name_raw"], {})[f"{rname}|us"] = float(sign)
                if info.get("ds_type_raw", "").strip().lower() == "junction":
                    sign = endpoint_signs.get(f"{rname}|ds")
                    if sign is not None:
                        out["junction_endpoint_signs"].setdefault(info["ds_name_raw"], {})[f"{rname}|ds"] = float(sign)
            for idx in range(len(icsu)):
                rname = reach_rows_by_index.get(idx + 1)
                if not rname:
                    continue
                info = centerline.get(rname, {})
                if info.get("us_type_raw", "").strip().lower() == "junction" and np.any(np.abs(qsignu[idx]) > 1e-9):
                    own_sign = None
                    for j in range(int(qsignu.shape[1])):
                        if int(nucon[idx, j]) == int(icsu[idx]) and abs(float(qsignu[idx, j])) > 1e-9:
                            own_sign = float(qsignu[idx, j])
                            break
                    if own_sign is None:
                        nz = [float(v) for v in qsignu[idx] if abs(float(v)) > 1e-9]
                        if nz:
                            own_sign = nz[-1]
                    if own_sign is not None:
                        out["junction_master_hints"][info["us_name_raw"]] = {
                            "reach_name": rname,
                            "endpoint": "us",
                            "sign": float(own_sign),
                        }
                if info.get("ds_type_raw", "").strip().lower() == "junction" and np.any(np.abs(qsignd[idx]) > 1e-9):
                    own_sign = None
                    for j in range(int(qsignd.shape[1])):
                        if int(ndcon[idx, j]) == int(icsd[idx]) and abs(float(qsignd[idx, j])) > 1e-9:
                            own_sign = float(qsignd[idx, j])
                            break
                    if own_sign is None:
                        nz = [float(v) for v in qsignd[idx] if abs(float(v)) > 1e-9]
                        if nz:
                            own_sign = nz[-1]
                    if own_sign is not None:
                        out["junction_master_hints"][info["ds_name_raw"]] = {
                            "reach_name": rname,
                            "endpoint": "ds",
                            "sign": float(own_sign),
                        }
    except Exception:
        return {"reach_rows": {}, "reach_endpoint_signs": {}, "junction_endpoint_signs": {}, "junction_master_hints": {}}
    return out

def _infer_network_topology(d, reach_groups, bcs):
    explicit_layout = _parse_explicit_network_layout(d)
    storage_area_data = _load_storage_area_data(d)
    hecras_junction_inputs = _load_hecras_junction_input_data(d)
    hecras_centerline_inputs = _load_hecras_centerline_input_data(d)
    reach_us_rs = {}
    reach_ds_rs = {}
    for rname, idxs in reach_groups.items():
        reach_us_rs[rname] = float(d["river_stations_m"][idxs[0]])
        reach_ds_rs[rname] = float(d["river_stations_m"][idxs[-1]])
    bc_reach_us = set()
    bc_reach_ds = set()
    bc_map = {}
    for bc in bcs:
        loc = bc.get("location", "")
        rname_bc = _parse_bc_location(loc)
        if bc["type"] == "flow_hydrograph":
            bc_reach_us.add(rname_bc)
            bc_map[rname_bc + "_us"] = FlowHydrographBC(np.array(bc["times_s"]), np.array(bc["values_m3s"]))
        elif bc["type"] == "normal_depth":
            bc_reach_ds.add(rname_bc)
            bc_map[rname_bc + "_ds"] = ("normal_depth", bc["slope"])
        elif bc["type"] == "stage_hydrograph":
            bc_reach_ds.add(rname_bc)
            bc_map[rname_bc + "_ds"] = ("stage_hydrograph", np.array(bc["times_s"]), np.array(bc["values_m"]))
    def _map_centerline_endpoint(rname, side):
        raw = hecras_centerline_inputs.get(rname, {})
        type_key = "us_type_raw" if side == "us" else "ds_type_raw"
        name_key = "us_name_raw" if side == "us" else "ds_name_raw"
        raw_type = str(raw.get(type_key, "") or "").strip().lower()
        raw_name = str(raw.get(name_key, "") or "").strip()
        if raw_type == "junction" and raw_name:
            return "junction", raw_name
        if raw_type == "storage area" and raw_name:
            return "storage_area", raw_name
        if raw_type == "external":
            return "external", rname + ("_us" if side == "us" else "_ds")
        return None
    if explicit_layout:
        reach_topology = []
        upstream_lookup = {}
        downstream_lookup = {}
        for jname, info in explicit_layout["junctions"].items():
            for rname in info["upstream_reaches"]:
                downstream_lookup[rname] = jname
            for rname in info["downstream_reaches"]:
                upstream_lookup[rname] = jname
        for rname in reach_groups:
            us_endpoint = _map_centerline_endpoint(rname, "us")
            ds_endpoint = _map_centerline_endpoint(rname, "ds")
            if us_endpoint is not None:
                us_type, us_name = us_endpoint
            elif rname in bc_reach_us:
                us_type, us_name = "external", rname + "_us"
            elif rname in upstream_lookup:
                us_type, us_name = "junction", upstream_lookup[rname]
            else:
                us_type, us_name = "external", rname + "_us_fallback"
            if ds_endpoint is not None:
                ds_type, ds_name = ds_endpoint
            elif rname in explicit_layout["reach_storage_downstream"]:
                ds_type, ds_name = "storage_area", explicit_layout["reach_storage_downstream"][rname]
            elif rname in downstream_lookup:
                ds_type, ds_name = "junction", downstream_lookup[rname]
            elif rname in bc_reach_ds:
                ds_type, ds_name = "external", rname + "_ds"
            else:
                ds_type, ds_name = "external", rname + "_ds_fallback"
            if ds_type == "storage_area":
                storage_name = ds_name
                stage0 = explicit_layout["storage_initial_elevation_m"].get(storage_name)
                if storage_name in storage_area_data and stage0 is not None:
                    storage_area_data[storage_name]["initial_stage"] = stage0
            reach_topology.append({"name": rname, "us_type": us_type, "us_name": us_name, "ds_type": ds_type, "ds_name": ds_name})
        js_data = d.get("junction_storage", [])
        junction_list = []
        explicit_names = list(explicit_layout["junctions"].keys())
        for ji, jname in enumerate(explicit_names):
            sel, svol = None, None
            if ji < len(js_data) and js_data[ji]:
                sel = np.array(js_data[ji]["elevations_m"])
                svol = np.array(js_data[ji]["volumes_m3"])
            junction_list.append({"name": jname, "storage_elevations": sel, "storage_volumes": svol})
        storage_list = []
        for sname in explicit_layout["storage_areas"]:
            item = storage_area_data.get(sname, {"name": sname})
            if item.get("initial_stage") is None and sname in explicit_layout["storage_initial_elevation_m"]:
                item["initial_stage"] = explicit_layout["storage_initial_elevation_m"][sname]
            storage_list.append(item)
        return reach_topology, junction_list, storage_list, explicit_layout["connections"], bc_map
    RS_TOL = 0.02
    jc = [0]
    rs_to_j = {}
    def get_or_create_j(rs_val):
        for k, v in rs_to_j.items():
            if abs(k - rs_val) < RS_TOL:
                return v
        jname = "J" + str(jc[0])
        jc[0] += 1
        rs_to_j[rs_val] = jname
        return jname
    reach_topology = []
    for rname in reach_groups:
        us_rs = reach_us_rs[rname]
        ds_rs = reach_ds_rs[rname]
        if rname in bc_reach_us:
            us_type, us_name = "external", rname + "_us"
        else:
            us_type, us_name = "junction", get_or_create_j(us_rs)
        if rname in bc_reach_ds:
            ds_type, ds_name = "external", rname + "_ds"
        else:
            ds_type, ds_name = "junction", get_or_create_j(ds_rs)
        reach_topology.append({"name": rname, "us_type": us_type, "us_name": us_name, "ds_type": ds_type, "ds_name": ds_name})
    # Merge orphan junctions into real junctions
    # An "orphan" junction has no downstream reaches connecting FROM it
    # A "real" junction has at least one downstream reach
    junc_us_reaches = {}  # j -> list of reaches that have j as their US (j feeds into them)
    junc_ds_reaches = {}  # j -> list of reaches that feed into j (j is their DS end)
    for rt in reach_topology:
        if rt["us_type"] == "junction":
            junc_us_reaches.setdefault(rt["us_name"], []).append(rt["name"])
        if rt["ds_type"] == "junction":
            junc_ds_reaches.setdefault(rt["ds_name"], []).append(rt["name"])
    orphan_juncs = [j for j in junc_ds_reaches if j not in junc_us_reaches]
    real_juncs = [j for j in junc_ds_reaches if j in junc_us_reaches]
    if orphan_juncs and real_juncs:
        # Merge all orphans into the first real junction with DS reaches
        # (heuristic: the real junction with the most downstream connectivity)
        target_j = max(real_juncs, key=lambda j: len(junc_us_reaches.get(j, [])))
        remap = {oj: target_j for oj in orphan_juncs}
        for rt in reach_topology:
            if rt["ds_type"] == "junction" and rt["ds_name"] in remap:
                candidate = remap[rt["ds_name"]]
                if rt["us_type"] == "junction" and rt["us_name"] == candidate:
                    continue
                rt["ds_name"] = candidate
    all_jnames = set()
    for rt in reach_topology:
        if rt["us_type"] == "junction": all_jnames.add(rt["us_name"])
        if rt["ds_type"] == "junction": all_jnames.add(rt["ds_name"])
    js_data = d.get("junction_storage", [])
    junction_list = []
    for ji, jname in enumerate(sorted(all_jnames)):
        sel, svol = None, None
        if ji < len(js_data):
            js = js_data[ji]
            sel = np.array(js["elevations_m"])
            svol = np.array(js["volumes_m3"])
        junction_list.append({"name": jname, "storage_elevations": sel, "storage_volumes": svol})
    return reach_topology, junction_list, [], [], bc_map


def _topological_reach_order(reach_topology):
    reach_names = [rt["name"] for rt in reach_topology]
    in_degree = {name: 0 for name in reach_names}
    adjacency = {name: [] for name in reach_names}
    by_us_junc = {}
    by_ds_junc = {}
    for rt in reach_topology:
        if rt["us_type"] == "junction":
            by_us_junc.setdefault(rt["us_name"], []).append(rt["name"])
        if rt["ds_type"] == "junction":
            by_ds_junc.setdefault(rt["ds_name"], []).append(rt["name"])
    for jname, downstream_reaches in by_us_junc.items():
        upstream_reaches = by_ds_junc.get(jname, [])
        if upstream_reaches:
            for ds_r in downstream_reaches:
                in_degree[ds_r] += 1
                for us_r in upstream_reaches:
                    adjacency[us_r].append(ds_r)
    queue = [name for name in reach_names if in_degree[name] == 0]
    order = []
    while queue:
        name = queue.pop(0)
        order.append(name)
        for nb in adjacency[name]:
            in_degree[nb] -= 1
            if in_degree[nb] == 0:
                queue.append(nb)
    for name in reach_names:
        if name not in order:
            order.append(name)
    return order


def _default_split_junction_state_names(reach_topology):
    upstream_counts = {}
    downstream_counts = {}
    for rt in reach_topology:
        if rt["ds_type"] == "junction":
            upstream_counts[rt["ds_name"]] = upstream_counts.get(rt["ds_name"], 0) + 1
        if rt["us_type"] == "junction":
            downstream_counts[rt["us_name"]] = downstream_counts.get(rt["us_name"], 0) + 1
    names = []
    all_names = set(upstream_counts) | set(downstream_counts)
    for jname in sorted(all_names):
        if upstream_counts.get(jname, 0) == 1 and downstream_counts.get(jname, 0) > 1:
            names.append(jname)
    return names


def _estimate_initial_network_flows(reach_topology, external_bcs, t0):
    flow_map = {}
    changed = True
    while changed:
        changed = False
        for rt in reach_topology:
            rname = rt["name"]
            prev = flow_map.get(rname)
            q0 = None
            if rt["us_type"] == "external":
                us_bc = external_bcs.get(rname + "_us")
                if us_bc is not None and callable(us_bc):
                    q0 = float(us_bc(t0))
            else:
                upstream_q = [
                    flow_map[up_rt["name"]]
                    for up_rt in reach_topology
                    if up_rt["ds_type"] == "junction"
                    and up_rt["ds_name"] == rt["us_name"]
                    and up_rt["name"] in flow_map
                ]
                downstream_reaches = [
                    ds_rt["name"]
                    for ds_rt in reach_topology
                    if ds_rt["us_type"] == "junction"
                    and ds_rt["us_name"] == rt["us_name"]
                ]
                if upstream_q and downstream_reaches:
                    total_q = float(sum(upstream_q))
                    q0 = total_q / max(len(downstream_reaches), 1)
            if q0 is not None and (prev is None or abs(prev - q0) > 1e-9):
                flow_map[rname] = q0
                changed = True
    for rt in reach_topology:
        flow_map.setdefault(rt["name"], 1.0)
    return flow_map


def _compute_network_initial_states(
    reach_infos,
    reach_sa_map,
    reach_groups,
    external_bcs,
    ws_ref0,
    time0,
    storage_stage0=None,
):
    topo = [
        {
            "name": ri.name,
            "us_type": ri.us_type,
            "us_name": ri.us_name,
            "ds_type": ri.ds_type,
            "ds_name": ri.ds_name,
        }
        for ri in reach_infos
    ]
    flow_map = _estimate_initial_network_flows(topo, external_bcs, time0)
    reach_lookup = {ri.name: ri for ri in reach_infos}
    reverse_order = list(reversed(_topological_reach_order(topo)))
    junction_stage = {}
    storage_stage0 = dict(storage_stage0 or {})
    states0 = {}
    ic_maes = {}
    for rname in reverse_order:
        ri = reach_lookup[rname]
        sa = reach_sa_map[rname]
        idxs = reach_groups[rname]
        q0 = float(flow_map.get(rname, 1.0))
        ds_bc = external_bcs.get(rname + "_ds")
        if ri.ds_type == "external" and ds_bc is not None:
            if hasattr(ds_bc, "compute_normal_wse"):
                ds_wse = ds_bc.compute_normal_wse(q0)
            else:
                ds_wse = float(ds_bc(time0))
        elif ri.ds_type == "storage_area" and ri.ds_name in storage_stage0:
            ds_wse = float(storage_stage0[ri.ds_name])
        elif ri.ds_type == "junction" and ri.ds_name in junction_stage:
            ds_wse = float(junction_stage[ri.ds_name])
        else:
            ds_wse = float(sa["bed_elevation"][-1] + 1.0)
        Z_init, Q_init, ic_src = _compute_ic(sa, q0, ds_wse)
        if ri.us_type == "junction":
            current = junction_stage.get(ri.us_name)
            stage_new = float(Z_init[0])
            junction_stage[ri.us_name] = stage_new if current is None else 0.5 * (current + stage_new)
        if ri.ds_type == "junction":
            current = junction_stage.get(ri.ds_name)
            stage_new = float(Z_init[-1])
            junction_stage[ri.ds_name] = stage_new if current is None else 0.5 * (current + stage_new)
        ic_ref_row = ws_ref0[np.array(idxs)]
        ic_mae = float(np.mean(np.abs(Z_init - ic_ref_row)))
        ic_maes[rname] = (ic_mae, ic_src, q0)
        states0[rname] = UnsteadyState(Z=Z_init, Q=Q_init, t=time0)
    return states0, ic_maes


def _warm_start_network_states(
    solver,
    states0,
    storage_stage0,
    ws_ref0,
    reach_groups,
    max_steps=8,
    dt=60.0,
    tol=0.02,
):
    if not (solver.storage_connections or solver.lateral_structures):
        return states0, {"enabled": False}

    states = {
        rname: UnsteadyState(Z=state.Z.copy(), Q=state.Q.copy(), t=state.t)
        for rname, state in states0.items()
    }
    storage_states = dict(storage_stage0 or {})
    time0 = float(next(iter(states.values())).t)
    t = time0
    max_dz_last = None
    max_dq_last = None
    converged = False
    steps_taken = 0

    for _ in range(max_steps):
        new_states, _ = solver.step(
            states,
            dt,
            t + dt,
            storage_states=storage_states,
            freeze_storage=True,
        )
        max_dz = 0.0
        max_dq = 0.0
        for rname in states:
            max_dz = max(max_dz, float(np.max(np.abs(new_states[rname].Z - states[rname].Z))))
            max_dq = max(max_dq, float(np.max(np.abs(new_states[rname].Q - states[rname].Q))))
        states = new_states
        t += dt
        steps_taken += 1
        max_dz_last = max_dz
        max_dq_last = max_dq
        if max_dz < tol:
            converged = True
            break

    ic_maes = {}
    for rname, idxs in reach_groups.items():
        ic_maes[rname] = float(np.mean(np.abs(states[rname].Z - ws_ref0[np.array(idxs)])))

    states = {
        rname: UnsteadyState(Z=state.Z.copy(), Q=state.Q.copy(), t=time0)
        for rname, state in states.items()
    }

    return states, {
        "enabled": True,
        "accepted": False,
        "steps": steps_taken,
        "converged": converged,
        "max_dz_last": max_dz_last,
        "max_dq_last": max_dq_last,
        "ic_maes": ic_maes,
    }


def run_network_case(json_path, case_label, solver_kwargs=None):
    sep = "=" * 70
    print(chr(10) + sep)
    print("  [NETWORK] " + case_label)
    print(sep)
    with open(json_path, encoding="utf-8") as f:
        d = json.load(f)
    ws_ref = np.array(d["water_surface_m"])
    time_ref = np.array(d["times_s"])
    dt_output = time_ref[1] - time_ref[0]
    n_xs_total = d["n_cross_sections"]
    unsupported = _unsupported_network_features(d)
    layout_notes = _network_layout_notes(d)
    print(f"  Total XS={n_xs_total}, T={len(time_ref)}, dt_output={dt_output:.1f}s")
    if unsupported:
        print("  BLOCKED: unsupported network physics -> " + ", ".join(unsupported))
        return {
            "case": case_label,
            "ic_mae": None,
            "mae": None,
            "mae_max": None,
            "verdict": "BLOCKED",
            "elapsed": 0.0,
            "notes": layout_notes + [
                "HydroClaude current network runner does not yet model these HEC-RAS features as first-principles dynamic components: "
                + ", ".join(unsupported)
            ],
        }
    reach_groups = _group_xs_by_reach(d)
    print("  Reaches: " + str(list(reach_groups.keys())))
    bcs = d["boundary_conditions"]
    reach_topology, junction_list, storage_list, storage_connections_raw, bc_map = _infer_network_topology(d, reach_groups, bcs)
    explicit_layout = _parse_explicit_network_layout(d)
    hecras_junction_inputs = _load_hecras_junction_input_data(d)
    hecras_centerline_inputs = _load_hecras_centerline_input_data(d)
    hecras_preprocess_inputs = _load_hecras_preprocess_connectivity_data(d)
    print("  Junctions: " + str([j["name"] for j in junction_list]))
    if storage_list:
        print("  Storage areas: " + str([s["name"] for s in storage_list]))
    for rt in reach_topology:
        msg = "    " + rt["name"] + ": " + rt["us_type"]
        msg += "(" + rt["us_name"] + ") -> " + rt["ds_type"] + "(" + rt["ds_name"] + ")"
        print(msg)
    reach_infos = []
    reach_sa_map = {}
    has_network_structures = False
    for rt in reach_topology:
        rname = rt["name"]
        idxs = reach_groups[rname]
        sa = _build_section_arrays(d, idxs)
        structures = _load_structures(d, sa["xs_rs_list"])
        if structures:
            has_network_structures = True
        reach_data = UnsteadyReachData(
            n_xs=sa["n_xs"], dx=sa["dx"], bed_elevation=sa["bed_elevation"],
            manning_n=sa["manning_n"], sections=sa["sections"],
            manning_n_lob=sa["manning_n_lob"], manning_n_rob=sa["manning_n_rob"],
            left_bank=sa["left_bank"], right_bank=sa["right_bank"],
            contraction_coef=sa["contraction_coef"], expansion_coef=sa["expansion_coef"],
            structures=structures,
        )
        reach_infos.append(ReachInfo(
            name=rname, reach_data=reach_data,
            us_type=rt["us_type"], us_name=rt["us_name"],
            ds_type=rt["ds_type"], ds_name=rt["ds_name"],
            us_junction_distance_m=hecras_centerline_inputs.get(rname, {}).get("us_junction_distance_m"),
            ds_junction_distance_m=hecras_centerline_inputs.get(rname, {}).get("ds_junction_distance_m"),
        ))
        reach_sa_map[rname] = sa
    junctions = []
    for j in junction_list:
        attrs = hecras_junction_inputs["junction_attrs"].get(j["name"], {})
        master_hint = hecras_preprocess_inputs.get("junction_master_hints", {}).get(j["name"], {})
        junctions.append(JunctionInfo(
            name=j["name"],
            storage_elevations=j["storage_elevations"],
            storage_volumes=j["storage_volumes"],
            hecras_index=attrs.get("hecras_index"),
            hecras_momentum=bool(attrs.get("momentum", False)),
            hecras_add_weight=bool(attrs.get("add_weight", False)),
            hecras_add_friction=bool(attrs.get("add_friction", False)),
            hecras_unsteady_energy=bool(attrs.get("unsteady_energy", False)),
            hecras_master_reach=master_hint.get("reach_name"),
            hecras_master_endpoint=master_hint.get("endpoint"),
            preprocess_endpoint_signs=dict(
                hecras_preprocess_inputs.get("junction_endpoint_signs", {}).get(j["name"], {})
            ),
        ))
    storage_areas = [
        StorageAreaInfo(
            name=item["name"],
            storage_elevations=item.get("storage_elevations"),
            storage_volumes=item.get("storage_volumes"),
            area=item.get("area"),
            min_elevation=item.get("min_elevation"),
            initial_stage=item.get("initial_stage"),
        )
        for item in storage_list
    ]
    storage_connections = [
        StorageConnectionInfo(
            name=item["name"],
            up_storage_area=item["up_storage_area"],
            down_storage_area=item["down_storage_area"],
            weir_width=item.get("weir_width"),
            weir_coef=item.get("weir_coef"),
            crest_elevation=item.get("crest_elevation"),
            culvert_count=item.get("culvert_count", 0),
            culvert_diameter=item.get("culvert_diameter"),
            culvert_length=item.get("culvert_length"),
            culvert_manning_n=item.get("culvert_manning_n"),
            culvert_inlet_coef=item.get("culvert_inlet_coef"),
            culvert_loss_coef=item.get("culvert_loss_coef"),
            culvert_selector_1=item.get("culvert_selector_1"),
            culvert_selector_2=item.get("culvert_selector_2"),
            culvert_selector_3=item.get("culvert_selector_3"),
            culvert_us_invert=item.get("culvert_us_invert"),
            culvert_ds_invert=item.get("culvert_ds_invert"),
        )
        for item in storage_connections_raw
        if item.get("up_storage_area") and item.get("down_storage_area")
    ]
    lateral_structures = []
    for item in (explicit_layout.get("lateral_structures", []) if explicit_layout else []):
        rname = item.get("reach")
        if rname not in reach_sa_map:
            continue
        rs_target = item.get("rs_m")
        xs_rows = reach_sa_map[rname]["xs_rs_list"]
        position_fraction = 0.5
        if rs_target is None:
            cell_index = 0
        else:
            rs_values = []
            for _, _, rs in xs_rows:
                try:
                    rs_values.append(float(rs))
                except Exception:
                    rs_values.append(None)
            cell_index = None
            for idx in range(max(len(rs_values) - 1, 0)):
                rs_up = rs_values[idx]
                rs_dn = rs_values[idx + 1]
                if rs_up is None or rs_dn is None:
                    continue
                rs_max = max(rs_up, rs_dn)
                rs_min = min(rs_up, rs_dn)
                if rs_min - 1e-9 <= rs_target <= rs_max + 1e-9:
                    cell_index = idx
                    span = abs(rs_up - rs_dn)
                    if span > 1e-9:
                        if item.get("distance_to_us_xs_m") is not None:
                            dx_cell = float(reach_sa_map[rname]["dx"][idx]) if idx < len(reach_sa_map[rname]["dx"]) else span
                            position_fraction = min(max(float(item["distance_to_us_xs_m"]) / max(dx_cell, 1e-6), 0.0), 1.0)
                        else:
                            position_fraction = min(max(abs(rs_up - rs_target) / span, 0.0), 1.0)
                    break
            if cell_index is None:
                best_idx = min(
                    [idx for idx, val in enumerate(rs_values[:-1]) if val is not None] or [0],
                    key=lambda idx: abs(rs_values[idx] - rs_target),
                )
                cell_index = max(0, min(best_idx, reach_sa_map[rname]["n_xs"] - 2))
        lateral_structures.append(
            LateralStructureInfo(
                name=item.get("name", f"{rname}->{item.get('storage_area','')}"),
                reach_name=rname,
                cell_index=cell_index,
                position_fraction=position_fraction,
                storage_area=item["storage_area"],
                weir_width=item.get("weir_width"),
                weir_coef=item.get("weir_coef"),
                length_m=item.get("length_m"),
                crest_elevation=item.get("crest_elevation"),
                culvert_count=item.get("culvert_count", 0),
                culvert_diameter=item.get("culvert_diameter"),
                culvert_length=item.get("culvert_length"),
                culvert_manning_n=item.get("culvert_manning_n"),
                culvert_inlet_coef=item.get("culvert_inlet_coef"),
                culvert_loss_coef=item.get("culvert_loss_coef"),
                culvert_selector_1=item.get("culvert_selector_1"),
                culvert_selector_2=item.get("culvert_selector_2"),
                culvert_selector_3=item.get("culvert_selector_3"),
                culvert_us_invert=item.get("culvert_us_invert"),
                culvert_ds_invert=item.get("culvert_ds_invert"),
            )
        )
    storage_stage0 = {
        item["name"]: float(item["initial_stage"])
        for item in storage_list
        if item.get("initial_stage") is not None
    }
    external_bcs = {}
    for ri in reach_infos:
        rname = ri.name
        sa = reach_sa_map[rname]
        if ri.us_type == "external":
            key = ri.us_name
            if key in bc_map:
                external_bcs[rname + "_us"] = bc_map[key]
        if ri.ds_type == "external":
            key = ri.ds_name
            if key in bc_map:
                bc_info = bc_map[key]
                if isinstance(bc_info, tuple) and bc_info[0] == "normal_depth":
                    external_bcs[rname + "_ds"] = NormalDepthBC(
                        section=sa["sections"][-1], manning_n=float(sa["manning_n"][-1]),
                        bed_slope=bc_info[1], manning_n_lob=float(sa["manning_n_lob"][-1]),
                        manning_n_rob=float(sa["manning_n_rob"][-1]),
                        left_bank=float(sa["left_bank"][-1]), right_bank=float(sa["right_bank"][-1]))
                elif isinstance(bc_info, tuple) and bc_info[0] == "stage_hydrograph":
                    external_bcs[rname + "_ds"] = StageHydrographBC(bc_info[1], bc_info[2])
                elif callable(bc_info):
                    external_bcs[rname + "_ds"] = bc_info
    print("  External BCs: " + str(list(external_bcs.keys())))
    states0, ic_info = _compute_network_initial_states(
        reach_infos,
        reach_sa_map,
        reach_groups,
        external_bcs,
        ws_ref[0],
        time_ref[0],
        storage_stage0=storage_stage0,
    )
    base_ic_mae_total = float(np.mean([item[0] for item in ic_info.values()]))
    solver_cfg = dict(solver_kwargs or {})
    diagnostic_focus = dict(solver_cfg.pop("diagnostic_focus", {}) or {})
    auto_split = solver_cfg.pop("auto_split_junction_states", None)
    if auto_split is None:
        auto_split = bool(explicit_layout)
    if auto_split and "junction_state_names" not in solver_cfg:
        solver_cfg["junction_state_names"] = _default_split_junction_state_names(reach_topology)
    if solver_cfg.get("junction_state_names"):
        print("  Junction stage states: " + str(list(solver_cfg["junction_state_names"])))
    if diagnostic_focus:
        print("  Diagnostic focus: " + str(diagnostic_focus))
    solver = UnsteadyNetworkSolver(
        reaches=reach_infos, junctions=junctions, external_bcs=external_bcs,
        storage_areas=storage_areas,
        storage_connections=storage_connections,
        lateral_structures=lateral_structures,
        theta=0.6, g=9.81, nr_max_iter=30, nr_tol=1e-4,
        junction_max_iter=30, junction_tol=0.1, junction_relax=0.3,
        min_depth=0.05, max_dZ_per_iter=0.5,
        **solver_cfg,
    )
    warm_start_diag = {"enabled": False}
    warm_states, warm_start_diag = _warm_start_network_states(
        solver,
        states0,
        storage_stage0,
        ws_ref[0],
        reach_groups,
        max_steps=8,
        dt=min(dt_output / 2.0, 60.0),
        tol=0.02,
    )
    if warm_start_diag.get("enabled"):
        warm_ic_mae_total = float(np.mean(list(warm_start_diag["ic_maes"].values())))
        if warm_ic_mae_total + 1e-9 < base_ic_mae_total:
            states0 = warm_states
            warm_start_diag["accepted"] = True
            for rname, (_, ic_src, q0) in list(ic_info.items()):
                ic_info[rname] = (
                    float(warm_start_diag["ic_maes"][rname]),
                    ic_src + "+network_warm",
                    q0,
                )
            base_ic_mae_total = warm_ic_mae_total
            print(
                "  Warm start: accepted "
                + f"(steps={warm_start_diag['steps']}, max_dZ={warm_start_diag['max_dz_last']:.4f}m, "
                + f"IC_MAE={warm_ic_mae_total:.4f}m)"
            )
        else:
            print(
                "  Warm start: rejected "
                + f"(IC_MAE {warm_ic_mae_total:.4f}m >= {base_ic_mae_total:.4f}m)"
            )
    for rname in _topological_reach_order(reach_topology):
        ic_mae, ic_src, q0 = ic_info[rname]
        print("  " + rname + ": IC=" + ic_src + " Q0=" + str(round(q0, 4)) + " IC_MAE=" + str(round(ic_mae, 4)) + "m")
    ic_mae_total = float(np.mean([item[0] for item in ic_info.values()]))
    dt = min(dt_output / 2.0, 60.0)
    print(f"  dt={dt:.1f}s")
    print("  Solving...")
    t0 = time.perf_counter()
    results = solver.solve(
        states0,
        t_end=time_ref[-1],
        dt=dt,
        storage_states0=storage_stage0,
        output_interval=dt_output,
        verbose=False,
    )
    elapsed = time.perf_counter() - t0
    print(f"  Elapsed: {elapsed:.1f}s")
    first_rname = reach_infos[0].name
    times_out = results[first_rname]["times"]
    mae_per_step = []
    for k, t_ref in enumerate(time_ref):
        idx = int(np.argmin(np.abs(times_out - t_ref)))
        if abs(times_out[idx] - t_ref) > dt_output * 0.5:
            continue
        Z_calc = np.full(n_xs_total, np.nan)
        for rname, idxs in reach_groups.items():
            Z_r = results[rname]["Z_history"][idx]
            for j_idx, gi in enumerate(idxs):
                Z_calc[gi] = Z_r[j_idx]
        valid = ~np.isnan(Z_calc)
        diff = Z_calc[valid] - ws_ref[k][valid]
        mae_per_step.append(float(np.mean(np.abs(diff))))
    mae_mean = float(np.mean(mae_per_step)) if mae_per_step else float("inf")
    mae_max = float(np.max(mae_per_step)) if mae_per_step else float("inf")
    v = _verdict(mae_mean)
    solver_diagnostics = results.get("solver_diagnostics", {})
    if warm_start_diag.get("enabled"):
        solver_diagnostics = dict(solver_diagnostics)
        solver_diagnostics["warm_start"] = {
            "accepted": bool(warm_start_diag.get("accepted")),
            "steps": int(warm_start_diag.get("steps", 0)),
            "converged": bool(warm_start_diag.get("converged", False)),
            "max_dz_last": float(warm_start_diag.get("max_dz_last") or 0.0),
            "max_dq_last": float(warm_start_diag.get("max_dq_last") or 0.0),
            "ic_mae_total": float(ic_mae_total),
        }
    exchange_diagnostics = _compute_network_exchange_diagnostics(solver, results)
    if exchange_diagnostics:
        solver_diagnostics = dict(solver_diagnostics)
        solver_diagnostics["exchange_diagnostics"] = exchange_diagnostics
    junction_stage_proxy = _compute_junction_stage_proxy_diagnostics(
        reach_topology,
        reach_groups,
        results,
        ws_ref,
        time_ref,
    )
    if junction_stage_proxy:
        solver_diagnostics = dict(solver_diagnostics)
        solver_diagnostics["junction_stage_proxy_diagnostics"] = junction_stage_proxy
        junction_bias_ranking = _summarize_junction_stage_biases(
            junction_stage_proxy,
            solver_diagnostics,
        )
        solver_diagnostics["junction_stage_bias_ranking"] = junction_bias_ranking
        if junction_bias_ranking:
            top_parts = []
            for item in junction_bias_ranking[:3]:
                top_parts.append(
                    item["junction_name"]
                    + f":{item['mean_bias_at_max_m']:+.3f}m@{item['time_of_max_abs_mean_bias_s']:.0f}s"
                    + f",clip={item['junction_iter_clip_count']}/{item['junction_step_clip_count']}"
                )
            print("  Junction bias top: " + "; ".join(top_parts))
    junction_endpoint_bias = _compute_junction_endpoint_bias_diagnostics(
        reach_topology,
        reach_groups,
        results,
        ws_ref,
        np.array(d["flow_m3s"], dtype=float) if "flow_m3s" in d else None,
        time_ref,
    )
    if junction_endpoint_bias:
        solver_diagnostics = dict(solver_diagnostics)
        solver_diagnostics["junction_endpoint_bias_diagnostics"] = junction_endpoint_bias
    branch_cell_term_bias = _compute_branch_cell_term_bias_diagnostics(
        solver,
        reach_topology,
        reach_groups,
        results,
        ws_ref,
        np.array(d["flow_m3s"], dtype=float) if "flow_m3s" in d else None,
        time_ref,
        junction_names=diagnostic_focus.get("junction_names"),
        t_start=diagnostic_focus.get("t_start"),
        t_end=diagnostic_focus.get("t_end"),
    )
    if branch_cell_term_bias:
        solver_diagnostics = dict(solver_diagnostics)
        solver_diagnostics["branch_cell_term_bias_diagnostics"] = branch_cell_term_bias
        branch_bias_ranking = _summarize_branch_cell_term_biases(branch_cell_term_bias)
        solver_diagnostics["branch_cell_term_bias_ranking"] = branch_bias_ranking
        if branch_bias_ranking:
            top_parts = []
            for item in branch_bias_ranking[:4]:
                top_parts.append(
                    item["junction_name"]
                    + "/"
                    + item["reach_name"]
                    + ":"
                    + item["cell_location"]
                    + f",dom={item['dominant_momentum_term']}"
                    + f",|dM|={item['max_abs_momentum_term_diff']:.3f}"
                )
            print("  Branch term bias top: " + "; ".join(top_parts))
    branch_snapshot_diag = _compute_branch_cell_snapshot_diagnostics(
        solver,
        reach_groups,
        reach_infos,
        results,
        ws_ref,
        np.array(d["flow_m3s"], dtype=float) if "flow_m3s" in d else None,
        d.get("hecras_pt"),
        time_ref,
        branch_targets=list(diagnostic_focus.get("branch_snapshot_targets", []) or []),
        time_targets_s=list(diagnostic_focus.get("snapshot_times_s", []) or []),
    )
    if branch_snapshot_diag:
        solver_diagnostics = dict(solver_diagnostics)
        solver_diagnostics["branch_cell_snapshot_diagnostics"] = branch_snapshot_diag
    solver_diagnostics = dict(solver_diagnostics)
    solver_diagnostics["hecras_junction_inputs"] = hecras_junction_inputs
    solver_diagnostics["hecras_centerline_inputs"] = hecras_centerline_inputs
    solver_diagnostics["hecras_preprocess_inputs"] = hecras_preprocess_inputs
    print(f"  MAE={mae_mean:.4f}m, MaxMAE={mae_max:.4f}m  [{v}]")
    return {"case": case_label, "ic_mae": ic_mae_total, "mae": mae_mean,
            "mae_max": mae_max, "verdict": v, "elapsed": elapsed, "notes": layout_notes,
            "solver_diagnostics": solver_diagnostics}


def run_with_timeout(fn, json_path, case_label, timeout=CASE_TIMEOUT):
    result_c = [None]
    error_c = [None]
    def worker():
        try:
            result_c[0] = fn(json_path, case_label)
        except Exception:
            error_c[0] = traceback.format_exc()
    t = threading.Thread(target=worker, daemon=True)
    t.start()
    t.join(timeout=timeout)
    if t.is_alive():
        return {"case": case_label, "ic_mae": float("inf"), "mae": float("inf"),
                "verdict": "FAIL", "error": "TIMEOUT (>" + str(timeout) + "s)"}
    if error_c[0]:
        return {"case": case_label, "ic_mae": float("inf"), "mae": float("inf"),
                "verdict": "FAIL", "error": error_c[0][-400:]}
    return result_c[0]


def main():
    all_results = []
    sep = "=" * 70
    print(chr(10) + sep)
    print("  HydroClaude 7 unsteady benchmark cases")
    print(sep)
    print("\n[1] Single-reach cases")
    for fn, label in SINGLE_REACH_CASES:
        json_path = os.path.join(REF_DIR, fn)
        if not os.path.exists(json_path):
            print("  SKIP: " + fn + " not found")
            all_results.append({"case": label, "ic_mae": float("inf"), "mae": float("inf"), "verdict": "SKIP"})
            continue
        res = run_with_timeout(run_single_reach, json_path, label, timeout=CASE_TIMEOUT)
        all_results.append(res)
    print("\n[2] Multi-reach network cases")
    for fn, label in NETWORK_CASES:
        json_path = os.path.join(REF_DIR, fn)
        if not os.path.exists(json_path):
            print("  SKIP: " + fn + " not found")
            all_results.append({"case": label, "ic_mae": float("inf"), "mae": float("inf"), "verdict": "SKIP"})
            continue
        res = run_with_timeout(run_network_case, json_path, label, timeout=CASE_TIMEOUT)
        all_results.append(res)
    print(chr(10) + sep)
    print("  SUMMARY")
    print(sep)
    print("  " + "Case".ljust(42) + "IC_MAE".rjust(8) + "MAE".rjust(8) + "Verdict".rjust(8))
    print("  " + "-" * 67)
    passed = 0
    for r in all_results:
        ic = r.get("ic_mae", float("inf"))
        mae = r.get("mae", float("inf"))
        v = r.get("verdict", "FAIL")
        ic_str = f"{ic:.4f}" if np.isfinite(ic) else "   inf"
        mae_str = f"{mae:.4f}" if np.isfinite(mae) else "   inf"
        flag = " *" if r.get("error") else ""
        print("  " + r["case"].ljust(42) + ic_str.rjust(8) + mae_str.rjust(8) + " [" + v + "]" + flag)
        if v == "PASS":
            passed += 1
    total = len(all_results)
    print(f"\n  {passed}/{total} PASSED (MAE < 0.15m)")
    print("  NEAR = 0.15~0.50m, FAIL = >0.50m or error")
    for r in all_results:
        if r.get("error"):
            print("\n  [" + r["case"] + "] ERROR:\n" + r["error"])


if __name__ == "__main__":
    main()
