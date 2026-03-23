"""Junction Hydraulics 河网非恒定流对标测试。"""

import sys, os, time, glob
import numpy as np
import h5py

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from physics.cross_section import NaturalSection
from solvers.unsteady_preissmann_solver import UnsteadyReachData, UnsteadyState
from solvers.unsteady_network_solver import UnsteadyNetworkSolver, ReachInfo, JunctionInfo
from solvers.unsteady_boundary import FlowHydrographBC, NormalDepthBC

FT_TO_M = 0.3048
CFS_TO_M3S = 0.028316846592

SUITE = "C:/Users/lxh/AppData/Local/Temp/hydroclaude_hecras_suite"


def load_junction_hydraulics():
    """Load Junction Hydraulics case from HDF."""
    hdfs = glob.glob(f"{SUITE}/022/**/*.p*.hdf", recursive=True)
    hdfs = [h for h in hdfs if ".g0" not in h]
    hdf_path = hdfs[0]

    with h5py.File(hdf_path, "r") as f:
        # --- River network topology ---
        rc_attrs = f["Geometry/River Centerlines/Attributes"][:]
        reach_topo = []
        for i in range(len(rc_attrs)):
            reach_topo.append({
                "river": rc_attrs[i]["River Name"].decode().strip(),
                "reach": rc_attrs[i]["Reach Name"].decode().strip(),
                "us_type": rc_attrs[i]["US Type"].decode().strip().lower(),
                "us_name": rc_attrs[i]["US Name"].decode().strip(),
                "ds_type": rc_attrs[i]["DS Type"].decode().strip().lower(),
                "ds_name": rc_attrs[i]["DS Name"].decode().strip(),
            })

        # --- Cross section geometry ---
        geom = f["Geometry/Cross Sections"]
        xs_attrs = geom["Attributes"][:]
        n_xs_total = len(xs_attrs)
        se_info = geom["Station Elevation Info"][:]
        se_vals = geom["Station Elevation Values"][:]
        mann_info = geom["Manning's n Info"][:]
        mann_vals = geom["Manning's n Values"][:]

        # Group XS by reach
        from collections import defaultdict, OrderedDict
        reach_xs_indices = OrderedDict()
        for i in range(n_xs_total):
            river = xs_attrs[i]["River"].decode().strip()
            reach = xs_attrs[i]["Reach"].decode().strip()
            key = f"{river}/{reach}"
            if key not in reach_xs_indices:
                reach_xs_indices[key] = []
            reach_xs_indices[key].append(i)

        # Build ReachInfo for each reach
        reach_infos = []
        reach_sections = {}  # reach_name -> (sections, bed_elev, manning_n, dx)

        for rt in reach_topo:
            rname = f"{rt['river']}/{rt['reach']}"
            xs_indices = reach_xs_indices[rname]
            n_xs = len(xs_indices)

            sections = []
            bed_elevations = []
            manning_n_arr = []

            for idx in xs_indices:
                si = int(se_info[idx][0])
                n_pts = int(se_info[idx][1])
                pts = se_vals[si:si + n_pts]
                sta_m = pts[:, 0] * FT_TO_M
                elev_m = pts[:, 1] * FT_TO_M

                sec = NaturalSection(name=f"xs_{idx}", elevations=elev_m, distances=sta_m)
                sections.append(sec)
                bed_elevations.append(float(np.min(elev_m)))

                ni_start = int(mann_info[idx][0])
                ni_count = int(mann_info[idx][1])
                nvals = mann_vals[ni_start:ni_start + ni_count]
                n_val = 0.03  # default
                if ni_count >= 3:
                    n_val = float(nvals[1, 1])  # channel value
                elif ni_count > 0:
                    n_val = float(nvals[0, 1])
                # Guard against zero Manning n
                if n_val < 0.001:
                    n_val = 0.035
                manning_n_arr.append(n_val)

            # dx from Len Channel
            dx = np.array([
                max(float(xs_attrs[xs_indices[j]]["Len Channel"]) * FT_TO_M, 1.0)
                for j in range(n_xs - 1)
            ])

            # Contraction/expansion loss coefficients
            cc_arr = np.array([float(xs_attrs[idx]["Contr"]) for idx in xs_indices])
            ce_arr = np.array([float(xs_attrs[idx]["Expan"]) for idx in xs_indices])

            # Bank stations (ft -> m) and LOB/ROB Manning n
            lb_arr = np.array([float(xs_attrs[idx]["Left Bank"]) * FT_TO_M for idx in xs_indices])
            rb_arr = np.array([float(xs_attrs[idx]["Right Bank"]) * FT_TO_M for idx in xs_indices])
            n_lob_arr = []
            n_rob_arr = []
            for idx in xs_indices:
                ni_start = int(mann_info[idx][0])
                ni_count = int(mann_info[idx][1])
                nvals = mann_vals[ni_start:ni_start + ni_count]
                if ni_count >= 3:
                    n_lob_arr.append(max(float(nvals[0, 1]), 0.01))   # first = LOB
                    n_rob_arr.append(max(float(nvals[-1, 1]), 0.01))  # last = ROB
                else:
                    n_lob_arr.append(0.06)  # default
                    n_rob_arr.append(0.06)

            # --- HEC-RAS Property Tables (XSEC Value) ---
            pt_grp = geom["Property Tables"]
            pt_xsec_info = pt_grp["XSEC Info"][:]
            pt_xsec_val = pt_grp["XSEC Value"][:]

            hecras_pt_elev = []
            hecras_pt_A = []
            hecras_pt_K = []
            hecras_pt_B = []
            hecras_pt_beta = []

            for idx in xs_indices:
                pt_si = int(pt_xsec_info[idx, 0])
                pt_cnt = int(pt_xsec_info[idx, 1])
                pt_rows = pt_xsec_val[pt_si:pt_si + pt_cnt]

                elev_m = pt_rows[:, 0] * FT_TO_M
                # Cols 4-6: effective/storage area (LOB+Ch+ROB)
                A_m2 = (pt_rows[:, 4] + pt_rows[:, 5] + pt_rows[:, 6]) * FT_TO_M**2
                # Cols 7-9: conveyance K (LOB+Ch+ROB), in cfs -> m3/s
                K_m3s = (pt_rows[:, 7] + pt_rows[:, 8] + pt_rows[:, 9]) * CFS_TO_M3S
                # Col 16: top width (total)
                B_m = pt_rows[:, 16] * FT_TO_M

                # Col 22: momentum correction factor (beta)
                beta_arr = pt_rows[:, 22].copy()
                beta_arr = np.maximum(beta_arr, 1.0)

                hecras_pt_elev.append(elev_m)
                hecras_pt_A.append(A_m2)
                hecras_pt_K.append(K_m3s)
                hecras_pt_B.append(B_m)
                hecras_pt_beta.append(beta_arr)

            reach_data = UnsteadyReachData(
                n_xs=n_xs,
                dx=dx,
                bed_elevation=np.array(bed_elevations),
                manning_n=np.array(manning_n_arr),
                sections=sections,
                contraction_coef=cc_arr,
                expansion_coef=ce_arr,
                manning_n_lob=np.array(n_lob_arr),
                manning_n_rob=np.array(n_rob_arr),
                left_bank=lb_arr,
                right_bank=rb_arr,
                hecras_pt_elevations=hecras_pt_elev,
                hecras_pt_A=hecras_pt_A,
                hecras_pt_K=hecras_pt_K,
                hecras_pt_B=hecras_pt_B,
                hecras_pt_beta=hecras_pt_beta,
            )

            reach_infos.append(ReachInfo(
                name=rname,
                reach_data=reach_data,
                us_type=rt["us_type"],
                us_name=rt["us_name"],
                ds_type=rt["ds_type"],
                ds_name=rt["ds_name"],
            ))

            reach_sections[rname] = {
                "xs_indices": xs_indices,
                "sections": sections,
                "bed_elevation": np.array(bed_elevations),
                "manning_n": np.array(manning_n_arr),
            }

        # --- Junctions with storage ---
        junction_names = set()
        for rt in reach_topo:
            if rt["us_type"] == "junction":
                junction_names.add(rt["us_name"])
            if rt["ds_type"] == "junction":
                junction_names.add(rt["ds_name"])

        # Extract junction storage from Property Tables
        pt_grp2 = geom["Property Tables"]
        jc_info = pt_grp2["Junction Cell Info"][:]
        jc_val = pt_grp2["Junction Cell Value"][:]
        FT3_TO_M3 = FT_TO_M ** 3

        junctions = []
        for ji, jn in enumerate(sorted(junction_names)):
            storage_elev = None
            storage_vol = None
            if ji < len(jc_info):
                jc_si = int(jc_info[ji, 0])
                jc_cnt = int(jc_info[ji, 1])
                jc_rows = jc_val[jc_si:jc_si + jc_cnt]
                storage_elev = jc_rows[:, 0] * FT_TO_M
                storage_vol = jc_rows[:, 1] * FT3_TO_M3
            junctions.append(JunctionInfo(
                name=jn,
                storage_elevations=storage_elev,
                storage_volumes=storage_vol,
            ))

        # --- Boundary Conditions ---
        bc_grp = f["Event Conditions/Unsteady/Boundary Conditions"]
        external_bcs = {}

        # Flow Hydrographs (upstream)
        fh_grp = bc_grp["Flow Hydrographs"]
        for key in fh_grp.keys():
            data = fh_grp[key][:]
            times_s = data[:, 0] * 3600.0
            flows_m3s = data[:, 1] * CFS_TO_M3S
            # Match to reach
            for ri in reach_infos:
                if ri.us_type == "external":
                    # Check if this BC matches
                    if ri.name.split("/")[0] in key:
                        external_bcs[f"{ri.name}_us"] = FlowHydrographBC(times_s, flows_m3s)

        # Normal Depths (downstream)
        if "Normal Depths" in bc_grp:
            nd_grp = bc_grp["Normal Depths"]
            for key in nd_grp.keys():
                slope = float(nd_grp[key][0])
                for ri in reach_infos:
                    if ri.ds_type == "external":
                        if ri.name.split("/")[0] in key or ri.name.split("/")[1] in key:
                            # Pass HEC-RAS K table to NormalDepthBC for accurate normal depth
                            K_elev = None
                            K_vals = None
                            if ri.reach_data.hecras_pt_elevations is not None:
                                K_elev = ri.reach_data.hecras_pt_elevations[-1]
                                K_vals = ri.reach_data.hecras_pt_K[-1]
                            external_bcs[f"{ri.name}_ds"] = NormalDepthBC(
                                ri.reach_data.sections[-1],
                                manning_n=float(ri.reach_data.manning_n[-1]),
                                bed_slope=slope,
                                K_elevations=K_elev,
                                K_values=K_vals,
                            )

        # --- Reference results ---
        ts_path = "Results/Unsteady/Output/Output Blocks/Base Output/Unsteady Time Series"
        ws_ref = f[f"{ts_path}/Cross Sections/Water Surface"][:] * FT_TO_M
        fl_ref = f[f"{ts_path}/Cross Sections/Flow"][:] * CFS_TO_M3S
        time_ref = f[f"{ts_path}/Time"][:] * 3600.0

    return {
        "reach_infos": reach_infos,
        "junctions": junctions,
        "external_bcs": external_bcs,
        "reach_sections": reach_sections,
        "ws_ref": ws_ref,
        "fl_ref": fl_ref,
        "time_ref": time_ref,
        "reach_xs_indices": reach_xs_indices,
    }


def run_benchmark():
    print("=== Junction Hydraulics Network Benchmark ===")
    data = load_junction_hydraulics()

    reach_infos = data["reach_infos"]
    junctions = data["junctions"]
    external_bcs = data["external_bcs"]

    print(f"Reaches: {[r.name for r in reach_infos]}")
    print(f"Junctions: {[j.name for j in junctions]}")
    print(f"External BCs: {list(external_bcs.keys())}")
    print(f"Time steps: {len(data['time_ref'])}")
    print(f"Total XS: {data['ws_ref'].shape[1]}")

    # Build network solver
    solver = UnsteadyNetworkSolver(
        reaches=reach_infos,
        junctions=junctions,
        external_bcs=external_bcs,
        theta=0.6, g=9.81,
        nr_max_iter=30, nr_tol=1e-4,
        junction_max_iter=30, junction_tol=0.1,
        junction_relax=0.3,
        min_depth=0.05, max_dZ_per_iter=0.5,
    )

    # Initialize from HEC-RAS first timestep
    states0 = {}
    for rname, ri in solver.reaches.items():
        xs_idx = data["reach_xs_indices"][rname]
        Z_init = data["ws_ref"][0][xs_idx].copy()
        Q_init = data["fl_ref"][0][xs_idx].copy()
        states0[rname] = UnsteadyState(Z=Z_init, Q=Q_init, t=data["time_ref"][0])

    dt_output = data["time_ref"][1] - data["time_ref"][0]
    dt = min(dt_output / 2.0, 60.0)
    print(f"dt={dt:.1f}s, dt_output={dt_output:.1f}s")

    print("\nSolving...")
    t0 = time.perf_counter()
    results = solver.solve(
        states0,
        t_end=data["time_ref"][-1],
        dt=dt,
        output_interval=dt_output,
        verbose=True,
    )
    t1 = time.perf_counter()
    print(f"Time: {t1 - t0:.1f}s")

    # Compare with HEC-RAS
    print("\n=== Results ===")
    times_out = results[reach_infos[0].name]["times"]

    mae_per_step = []
    for k, t_ref in enumerate(data["time_ref"]):
        idx = int(np.argmin(np.abs(times_out - t_ref)))
        if abs(times_out[idx] - t_ref) > dt_output * 0.5:
            continue

        # Reconstruct full profile from reach results
        Z_calc = np.zeros(data["ws_ref"].shape[1])
        for rname in data["reach_xs_indices"]:
            xs_idx = data["reach_xs_indices"][rname]
            Z_reach = results[rname]["Z_history"][idx]
            for j, xi in enumerate(xs_idx):
                Z_calc[xi] = Z_reach[j]

        diff = Z_calc - data["ws_ref"][k]
        mae_per_step.append(float(np.mean(np.abs(diff))))

    mae_overall = float(np.mean(mae_per_step)) if mae_per_step else float("inf")
    mae_max = float(np.max(mae_per_step)) if mae_per_step else float("inf")

    verdict = "PASS" if mae_overall < 0.15 else ("NEAR" if mae_overall < 0.50 else "FAIL")
    print(f"  Steps compared: {len(mae_per_step)}")
    print(f"  Mean MAE: {mae_overall:.4f} m")
    print(f"  Max  MAE: {mae_max:.4f} m")
    print(f"  Target: MAE < 0.15 m")
    print(f"  Verdict: {verdict}")

    return mae_overall


if __name__ == "__main__":
    run_benchmark()
