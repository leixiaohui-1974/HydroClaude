"""通用非恒定流对标脚本 — 从 HEC-RAS HDF 直接读取并求解。"""

import sys
import os
import glob
import numpy as np
import h5py

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from physics.cross_section import NaturalSection
from solvers.unsteady_preissmann_solver import PreissmannSolver, UnsteadyReachData, UnsteadyState
from solvers.unsteady_boundary import FlowHydrographBC, StageHydrographBC, NormalDepthBC

FT_TO_M = 0.3048
CFS_TO_M3S = 0.028316846592

SUITE = "C:/Users/lxh/AppData/Local/Temp/hydroclaude_hecras_suite"


def find_hdf(suite_num: str) -> str:
    """Find the .p*.hdf file in a suite case directory."""
    pattern = f"{SUITE}/{suite_num}/**/*.p*.hdf"
    hdfs = glob.glob(pattern, recursive=True)
    # Filter out geometry-only HDFs
    hdfs = [h for h in hdfs if not h.endswith('.g01.hdf') and not h.endswith('.g02.hdf')]
    if not hdfs:
        raise FileNotFoundError(f"No plan HDF found for suite case {suite_num}")
    return hdfs[0]


def load_case(hdf_path: str) -> dict:
    """Load geometry, BCs, and reference results from HEC-RAS HDF."""
    with h5py.File(hdf_path, "r") as f:
        geom = f["Geometry/Cross Sections"]
        attrs = geom["Attributes"][:]
        n_xs = len(attrs)

        # Station-elevation data
        se_info = geom["Station Elevation Info"][:]
        se_vals = geom["Station Elevation Values"][:]

        # Manning n
        mann_info = geom["Manning's n Info"][:]
        mann_vals = geom["Manning's n Values"][:]

        sections = []
        bed_elevations = []
        manning_n_arr = []
        reach_info = []

        for i in range(n_xs):
            river = attrs[i]["River"].decode().strip()
            reach = attrs[i]["Reach"].decode().strip()
            rs = attrs[i]["RS"].decode().strip()
            reach_info.append((river, reach, rs))

            si = int(se_info[i][0])
            n_pts = int(se_info[i][1])
            pts = se_vals[si:si + n_pts]
            sta_m = pts[:, 0] * FT_TO_M
            elev_m = pts[:, 1] * FT_TO_M

            sec = NaturalSection(
                name=f"{river}_{reach}_{rs}",
                elevations=elev_m,
                distances=sta_m,
            )
            sections.append(sec)
            bed_elevations.append(float(np.min(elev_m)))

            ni_start = int(mann_info[i][0])
            ni_count = int(mann_info[i][1])
            nvals = mann_vals[ni_start:ni_start + ni_count]
            if ni_count >= 3:
                manning_n_arr.append(float(nvals[1, 1]))
            elif ni_count > 0:
                manning_n_arr.append(float(nvals[0, 1]))
            else:
                manning_n_arr.append(0.03)

        bed_elevation = np.array(bed_elevations)
        manning_n = np.array(manning_n_arr)

        # dx from Len Channel
        dx_raw = np.array([float(attrs[i]["Len Channel"]) * FT_TO_M for i in range(n_xs - 1)])
        dx = np.where(dx_raw > 1.0, dx_raw, 100.0)

        # Boundary conditions
        bc_grp = f["Event Conditions/Unsteady/Boundary Conditions"]

        # Upstream: Flow Hydrograph
        fh_grp = bc_grp["Flow Hydrographs"]
        fh_key = list(fh_grp.keys())[0]
        fh_data = fh_grp[fh_key][:]
        bc_times_s = fh_data[:, 0] * 3600.0
        bc_flows_m3s = fh_data[:, 1] * CFS_TO_M3S

        # Downstream: detect type
        ds_bc_type = None
        ds_bc_data = {}
        if "Normal Depths" in bc_grp and len(bc_grp["Normal Depths"]) > 0:
            nd_grp = bc_grp["Normal Depths"]
            nd_key = list(nd_grp.keys())[0]
            ds_bc_type = "normal_depth"
            ds_bc_data["slope"] = float(nd_grp[nd_key][0])
        elif "Stage Hydrographs" in bc_grp and len(bc_grp["Stage Hydrographs"]) > 0:
            sh_grp = bc_grp["Stage Hydrographs"]
            sh_key = list(sh_grp.keys())[0]
            sh_data = sh_grp[sh_key][:]
            ds_bc_type = "stage_hydrograph"
            ds_bc_data["times_s"] = sh_data[:, 0] * 3600.0
            ds_bc_data["stages_m"] = sh_data[:, 1] * FT_TO_M
        elif "Rating Curves" in bc_grp and len(bc_grp["Rating Curves"]) > 0:
            rc_grp = bc_grp["Rating Curves"]
            rc_key = list(rc_grp.keys())[0]
            rc_data = rc_grp[rc_key][:]
            ds_bc_type = "rating_curve"
            ds_bc_data["flows_m3s"] = rc_data[:, 0] * CFS_TO_M3S
            ds_bc_data["stages_m"] = rc_data[:, 1] * FT_TO_M

        # Reference results
        ts_path = "Results/Unsteady/Output/Output Blocks/Base Output/Unsteady Time Series"
        ws_ref = f[f"{ts_path}/Cross Sections/Water Surface"][:] * FT_TO_M
        fl_ref = f[f"{ts_path}/Cross Sections/Flow"][:] * CFS_TO_M3S
        time_ref = f[f"{ts_path}/Time"][:] * 3600.0

    return {
        "n_xs": n_xs,
        "dx": dx,
        "bed_elevation": bed_elevation,
        "manning_n": manning_n,
        "sections": sections,
        "bc_times_s": bc_times_s,
        "bc_flows_m3s": bc_flows_m3s,
        "ds_bc_type": ds_bc_type,
        "ds_bc_data": ds_bc_data,
        "ws_ref": ws_ref,
        "fl_ref": fl_ref,
        "time_ref": time_ref,
        "reach_info": reach_info,
    }


def run_case(suite_num: str, name: str) -> float:
    """Run a single unsteady benchmark case. Returns MAE."""
    print(f"\n{'='*60}")
    print(f"Case {suite_num}: {name}")
    print(f"{'='*60}")

    hdf_path = find_hdf(suite_num)
    print(f"HDF: {os.path.basename(hdf_path)}")

    data = load_case(hdf_path)
    n_xs = data["n_xs"]

    reaches = set((r, rch) for r, rch, rs in data["reach_info"])
    print(f"  XS={n_xs}, Reaches={len(reaches)}, Steps={len(data['time_ref'])}")
    print(f"  Q range: {data['bc_flows_m3s'].min():.1f}-{data['bc_flows_m3s'].max():.1f} m3/s")
    print(f"  dx range: {data['dx'].min():.0f}-{data['dx'].max():.0f} m")
    print(f"  DS BC: {data['ds_bc_type']}")

    # Build solver
    reach_data = UnsteadyReachData(
        n_xs=n_xs,
        dx=data["dx"],
        bed_elevation=data["bed_elevation"],
        manning_n=data["manning_n"],
        sections=data["sections"],
    )

    upstream_bc = FlowHydrographBC(data["bc_times_s"], data["bc_flows_m3s"])

    if data["ds_bc_type"] == "normal_depth":
        downstream_bc = NormalDepthBC(
            data["sections"][-1],
            manning_n=float(data["manning_n"][-1]),
            bed_slope=data["ds_bc_data"]["slope"],
        )
    elif data["ds_bc_type"] == "stage_hydrograph":
        downstream_bc = StageHydrographBC(
            data["ds_bc_data"]["times_s"],
            data["ds_bc_data"]["stages_m"],
        )
    else:
        print(f"  Unsupported DS BC type: {data['ds_bc_type']}, skipping")
        return float("inf")

    # Warm start from HEC-RAS first timestep
    Z_init = data["ws_ref"][0].copy()
    Q_init = data["fl_ref"][0].copy()
    state0 = UnsteadyState(Z=Z_init, Q=Q_init, t=data["time_ref"][0])

    dt_output = data["time_ref"][1] - data["time_ref"][0]
    # 隐式格式允许大时间步，按断面数调整
    if n_xs > 100:
        dt = min(dt_output, 120.0)  # 大案例用大时间步
    else:
        dt = min(dt_output / 2.0, 60.0)
    print(f"  dt={dt:.1f}s, dt_output={dt_output:.1f}s")

    solver = PreissmannSolver(
        reach_data, theta=0.6, g=9.81,
        nr_max_iter=30, nr_tol=1e-4,
        min_depth=0.05, max_dZ_per_iter=0.5,
    )

    print("  Solving...")
    result = solver.solve(
        state0,
        t_end=data["time_ref"][-1],
        dt=dt,
        upstream_bc=upstream_bc,
        downstream_bc=downstream_bc,
        output_interval=dt_output,
        verbose=False,
    )

    # Compare
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

    print(f"  MAE={mae_overall:.4f}m, MaxMAE={mae_max:.4f}m, MB={mb['error_percent']:.3f}%  [{verdict}]")
    return mae_overall


if __name__ == "__main__":
    cases = [
        ("029", "Mixed Flow Regime (153 XS, single reach, no structures)"),
        ("051", "Example 17 - Unsteady Flow (77 XS, 8 reaches)"),
        ("018", "Dam Breaching (192 XS, single reach)"),
    ]

    results = {}
    for num, name in cases:
        try:
            mae = run_case(num, name)
            results[num] = mae
        except Exception as e:
            print(f"  ERROR: {e}")
            import traceback
            traceback.print_exc()
            results[num] = float("inf")

    print(f"\n{'='*60}")
    print("SUMMARY")
    print(f"{'='*60}")
    for num, name in cases:
        mae = results.get(num, float("inf"))
        v = "PASS" if mae < 0.15 else ("NEAR" if mae < 0.50 else "FAIL")
        print(f"  {num} {name[:50]:<50} MAE={mae:.4f}m [{v}]")
