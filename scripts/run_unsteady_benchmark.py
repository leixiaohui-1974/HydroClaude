"""Example 17 unsteady flow benchmark -- read directly from HEC-RAS HDF."""

import sys
import os
import numpy as np
import h5py

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from physics.cross_section import NaturalSection
from solvers.unsteady_preissmann_solver import PreissmannSolver, UnsteadyReachData, UnsteadyState
from solvers.unsteady_boundary import FlowHydrographBC, NormalDepthBC

FT_TO_M   = 0.3048
CFS_TO_M3S = 0.028316846592

HDF_PATH = (
    r"C:/Users/lxh/AppData/Local/Temp/hydroclaude_hecras_suite/051/"
    r"Example 17 - Unsteady Flow Application_hydroclaude_suite_1774013882982323900/"
    r"Diamond.p01.hdf"
)


def load_example17() -> dict:
    """Load geometry, BCs, and reference results from HEC-RAS HDF."""
    with h5py.File(HDF_PATH, "r") as f:
        geom = f["Geometry/Cross Sections"]
        attrs = geom["Attributes"][:]
        n_xs  = len(attrs)

        # Station-elevation data
        se_info = geom["Station Elevation Info"][:]   # [n_xs, 2]: (start_idx, n_pts)
        se_vals = geom["Station Elevation Values"][:]  # [total_pts, 2]: (sta_ft, elev_ft)

        # Manning n
        mann_info = geom["Manning's n Info"][:]    # [n_xs, 2]: (start_idx, n_vals)
        mann_vals = geom["Manning's n Values"][:]  # [total_vals, 2]: (sta_ft, n)

        sections = []
        bed_elevations = []
        manning_n_arr  = []
        reach_info     = []

        for i in range(n_xs):
            river = attrs[i]["River"].decode().strip()
            reach = attrs[i]["Reach"].decode().strip()
            rs    = attrs[i]["RS"].decode().strip()
            reach_info.append((river, reach, rs))

            # Extract station-elevation points
            si     = int(se_info[i][0])
            n_pts  = int(se_info[i][1])
            pts    = se_vals[si:si + n_pts]
            sta_m  = pts[:, 0] * FT_TO_M
            elev_m = pts[:, 1] * FT_TO_M

            sec = NaturalSection(
                name=f"{river}_{reach}_{rs}",
                elevations=elev_m,
                distances=sta_m,
            )
            sections.append(sec)
            bed_elevations.append(float(np.min(elev_m)))

            # Manning n: pick channel value (middle of 3 or first)
            ni_start = int(mann_info[i][0])
            ni_count = int(mann_info[i][1])
            nvals = mann_vals[ni_start:ni_start + ni_count]
            if ni_count >= 3:
                manning_n_arr.append(float(nvals[1, 1]))   # column 1 = n value
            elif ni_count > 0:
                manning_n_arr.append(float(nvals[0, 1]))
            else:
                manning_n_arr.append(0.03)

        bed_elevation = np.array(bed_elevations)
        manning_n     = np.array(manning_n_arr)

        # dx: Len Channel field (ft -> m), for each xs except the last
        # Len Channel is the distance to the NEXT xs (downstream)
        dx_raw = np.array([float(attrs[i]["Len Channel"]) * FT_TO_M for i in range(n_xs - 1)])
        # Guard against zero or negative dx (junction transitions)
        dx = np.where(dx_raw > 1.0, dx_raw, 100.0)

        # Upstream BC: Flow Hydrograph
        bc_grp = f["Event Conditions/Unsteady/Boundary Conditions"]
        fh_grp = bc_grp["Flow Hydrographs"]
        fh_key = list(fh_grp.keys())[0]
        fh_data = fh_grp[fh_key][:]   # [n_pts, 2]: (time_hours, flow_cfs)
        bc_times_s    = fh_data[:, 0] * 3600.0
        bc_flows_m3s  = fh_data[:, 1] * CFS_TO_M3S

        # Downstream BC: Normal Depth slope
        nd_grp = bc_grp["Normal Depths"]
        nd_key = list(nd_grp.keys())[0]
        nd_slope = float(nd_grp[nd_key][0])

        # Reference results (for validation only)
        ts_path = "Results/Unsteady/Output/Output Blocks/Base Output/Unsteady Time Series"
        ws_ref  = f[f"{ts_path}/Cross Sections/Water Surface"][:] * FT_TO_M   # [97, 77]
        fl_ref  = f[f"{ts_path}/Cross Sections/Flow"][:] * CFS_TO_M3S         # [97, 77]
        time_ref = f[f"{ts_path}/Time"][:] * 3600.0                           # [97] seconds

    return {
        "n_xs":         n_xs,
        "dx":           dx,
        "bed_elevation": bed_elevation,
        "manning_n":    manning_n,
        "sections":     sections,
        "bc_times_s":   bc_times_s,
        "bc_flows_m3s": bc_flows_m3s,
        "nd_slope":     nd_slope,
        "ws_ref":       ws_ref,
        "fl_ref":       fl_ref,
        "time_ref":     time_ref,
        "reach_info":   reach_info,
    }


def run_benchmark() -> float:
    """Run Example 17 unsteady flow benchmark. Returns overall MAE (m)."""
    print("Loading Example 17 data...")
    data = load_example17()

    n_xs = data["n_xs"]
    print(f"  Cross sections : {n_xs}")
    reaches = set((r, rch) for r, rch, rs in data["reach_info"])
    print(f"  Reaches: {reaches}")

    # Build solver components
    reach_data = UnsteadyReachData(
        n_xs=n_xs,
        dx=data["dx"],
        bed_elevation=data["bed_elevation"],
        manning_n=data["manning_n"],
        sections=data["sections"],
    )
    upstream_bc   = FlowHydrographBC(data["bc_times_s"], data["bc_flows_m3s"])
    downstream_bc = NormalDepthBC(
        data["sections"][-1],
        manning_n=float(data["manning_n"][-1]),
        bed_slope=data["nd_slope"],
    )

    # Initialize from HEC-RAS first time step (warm start)
    Z_init = data["ws_ref"][0].copy()
    Q_init = data["fl_ref"][0].copy()
    state0 = UnsteadyState(Z=Z_init, Q=Q_init, t=data["time_ref"][0])

    # Time step: 1/4 of output interval, capped at 60 s
    dt_output = data["time_ref"][1] - data["time_ref"][0]
    dt = min(dt_output / 4.0, 60.0)
    print(f"  dt={dt:.1f}s  dt_output={dt_output:.1f}s")

    print("Solving...")

    solver = PreissmannSolver(
        reach_data, theta=0.6, g=9.81,
        nr_max_iter=30, nr_tol=1e-4,
        min_depth=0.05, max_dZ_per_iter=0.5,
    )
    result = solver.solve(
        state0,
        t_end=data["time_ref"][-1],
        dt=dt,
        upstream_bc=upstream_bc,
        downstream_bc=downstream_bc,
        output_interval=dt_output,
        verbose=True,
    )

    # Compare with HEC-RAS results
    print("=== Benchmark Results ===")

    times_out = result["times"]
    Z_hist    = result["Z_history"]
    Q_hist    = result["Q_history"]

    mae_per_step  = []
    rmse_per_step = []
    for k, t_ref in enumerate(data["time_ref"]):
        idx = int(np.argmin(np.abs(times_out - t_ref)))
        if abs(times_out[idx] - t_ref) > dt_output * 0.5:
            continue
        diff = Z_hist[idx] - data["ws_ref"][k]
        mae_per_step.append(float(np.mean(np.abs(diff))))
        rmse_per_step.append(float(np.sqrt(np.mean(diff**2))))

    mae_overall  = float(np.mean(mae_per_step))  if mae_per_step  else float("inf")
    rmse_overall = float(np.mean(rmse_per_step)) if rmse_per_step else float("inf")
    mae_max      = float(np.max(mae_per_step))   if mae_per_step  else float("inf")

    print(f"  Compared steps : {len(mae_per_step)}")
    print(f"  Mean MAE       : {mae_overall:.4f} m")
    print(f"  Max  MAE       : {mae_max:.4f} m")
    print(f"  Mean RMSE      : {rmse_overall:.4f} m")
    print(f"  Target         : MAE < 0.15 m")

    if mae_overall < 0.15:
        verdict = "PASS"
    elif mae_overall < 0.50:
        verdict = "NEAR"
    else:
        verdict = "FAIL"
    print(f"  Verdict        : {verdict}")

    mb = solver.compute_mass_balance(result)
    mb_err = mb["error_percent"]
    print(f"  Mass balance   : {mb_err:.4f}%")

    return mae_overall


if __name__ == "__main__":
    run_benchmark()
