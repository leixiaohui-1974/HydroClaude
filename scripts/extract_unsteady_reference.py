"""HEC-RAS unsteady flow reference data extraction script.
Extracts reference WSE/flow time series (validation only,
NOT used as solver input), plus geometry and BCs (actual inputs).
"""
from __future__ import annotations
import json
from pathlib import Path
from typing import Any, Dict, List, Optional
import h5py
import numpy as np

SUITE_BASE = Path("C:/Users/lxh/AppData/Local/Temp/hydroclaude_hecras_suite")
OUTPUT_DIR = Path("Z:/research/hydroclaude/reports/hecras_unsteady_reference")
LF = 0.3048
CFS_TO_M3S = 0.028316846592
HR_TO_S = 3600.0
CASES = [
    ("055", "Example20_LateralWeir", "*.p07.hdf"),
    ("022", "JunctionHydraulics",    "*.p02.hdf"),
    ("030", "MultipleReaches",       "*.p01.hdf"),
    ("051", "Example17_Unsteady",    "*.p01.hdf"),
    ("016", "CulvertHydraulics",     "*.p01.hdf"),
    ("029", "MixedFlowRegime",       "*.p02.hdf"),
    ("018", "DamBreaching",          "*.p06.hdf"),
]

class _NumpyEncoder(json.JSONEncoder):
    def default(self, obj):
        if isinstance(obj, np.ndarray): return obj.tolist()
        if isinstance(obj, np.integer): return int(obj)
        if isinstance(obj, np.floating):
            f = float(obj)
            return None if (np.isnan(f) or np.isinf(f)) else f
        if isinstance(obj, np.bool_): return bool(obj)
        if isinstance(obj, (bytes, bytearray)):
            return obj.decode("utf-8", errors="ignore").strip()
        return super().default(obj)


def _b2s(x) -> str:
    if x is None: return ""
    if isinstance(x, (bytes, bytearray, np.bytes_)):
        return x.decode("utf-8", errors="ignore").strip()
    if isinstance(x, str): return x.strip()
    if isinstance(x, np.ndarray):
        if x.dtype.kind in ("S", "U", "O"): return _b2s(x.item())
    return str(x).strip()

def _safe_f(x, default=None):
    try:
        v = float(x)
        return None if (np.isnan(v) or np.isinf(v)) else v
    except Exception: return default

def _read(hdf, path):
    try: return hdf[path][...] if path in hdf else None
    except Exception: return None

def _unit_system(hdf) -> str:
    try:
        raw = hdf.attrs.get("Units System", b"US Customary")
        s = _b2s(raw).lower()
        if "si" in s or "metric" in s: return "si"
    except Exception: pass
    return "english"

def _field_s(row, name: str) -> str:
    try:
        if name in row.dtype.names: return _b2s(row[name])
    except Exception: pass
    return ""

def _field_f(row, name: str):
    try:
        if name in row.dtype.names: return _safe_f(row[name])
    except Exception: pass
    return None

def _extract_geometry(hdf, is_english: bool) -> Dict[str, Any]:
    lf = LF if is_english else 1.0
    out: Dict[str, Any] = {
        "n_cross_sections": 0, "river_names": [], "reach_names": [],
        "river_stations_m": [], "bed_elevation_m": [],
        "manning_n_ch": [], "manning_n_lob": [], "manning_n_rob": [],
        "reach_lengths_ch_m": [], "reach_lengths_lob_m": [], "reach_lengths_rob_m": [],
        "left_bank_sta_m": [], "right_bank_sta_m": [], "xs_profiles": [],
    }
    attrs_arr = _read(hdf, "Geometry/Cross Sections/Attributes")
    if attrs_arr is None: return out
    n_xs = int(attrs_arr.shape[0])
    out["n_cross_sections"] = n_xs
    se_info = _read(hdf, "Geometry/Cross Sections/Station Elevation Info")
    se_vals = _read(hdf, "Geometry/Cross Sections/Station Elevation Values")
    n_key = "Geometry/Cross Sections/Manning" + chr(39) + "s n"
    n_info = _read(hdf, n_key + " Info")
    n_vals = _read(hdf, n_key + " Values")
    for i in range(n_xs):
        row = attrs_arr[i]
        out["river_names"].append(_field_s(row, "River"))
        out["reach_names"].append(_field_s(row, "Reach"))
        rs_str = _field_s(row, "RS")
        rs_m = None
        try:
            rv = _safe_f(rs_str)
            if rv is not None: rs_m = rv * lf
        except Exception: pass
        out["river_stations_m"].append(rs_m)
        len_ch = _field_f(row, "Len Channel")
        len_lob = _field_f(row, "Len Left")
        len_rob = _field_f(row, "Len Right")
        left_bank = _field_f(row, "Left Bank")
        right_bank = _field_f(row, "Right Bank")
        out["reach_lengths_ch_m"].append(len_ch * lf if len_ch is not None else None)
        out["reach_lengths_lob_m"].append(len_lob * lf if len_lob is not None else None)
        out["reach_lengths_rob_m"].append(len_rob * lf if len_rob is not None else None)
        out["left_bank_sta_m"].append(left_bank * lf if left_bank is not None else None)
        out["right_bank_sta_m"].append(right_bank * lf if right_bank is not None else None)
        bed_elev_m = None; stations_m: List[float] = []; elevations_m: List[float] = []
        if se_info is not None and se_vals is not None and i < se_info.shape[0]:
            try:
                start = int(se_info[i, 0]); count = int(se_info[i, 1])
                if count > 0 and start >= 0 and (start + count) <= se_vals.shape[0]:
                    seg = se_vals[start : start + count]
                    stations_m = [float(seg[j, 0]) * lf for j in range(count)]
                    elevations_m = [float(seg[j, 1]) * lf for j in range(count)]
                    if elevations_m: bed_elev_m = min(elevations_m)
            except Exception: pass
        out["bed_elevation_m"].append(bed_elev_m)
        out["xs_profiles"].append({"stations_m": stations_m, "elevations_m": elevations_m})
        n_lob = n_ch = n_rob = None
        if n_info is not None and n_vals is not None and i < n_info.shape[0]:
            try:
                ns = int(n_info[i, 0]); nc = int(n_info[i, 1])
                if nc > 0 and ns >= 0 and (ns + nc) <= n_vals.shape[0]:
                    seg = n_vals[ns : ns + nc]
                    if nc == 1: n_lob = n_ch = n_rob = _safe_f(seg[0, 1])
                    elif nc == 2:
                        n_lob = _safe_f(seg[0, 1]); n_ch = _safe_f(seg[1, 1]); n_rob = n_ch
                    else:
                        n_lob = _safe_f(seg[0, 1]); n_ch = _safe_f(seg[1, 1])
                        n_rob = _safe_f(seg[nc - 1, 1])
            except Exception: pass
        out["manning_n_lob"].append(n_lob)
        out["manning_n_ch"].append(n_ch)
        out["manning_n_rob"].append(n_rob)
    return out


def _extract_bcs(hdf, is_english: bool):
    lf = LF if is_english else 1.0
    cfs = CFS_TO_M3S if is_english else 1.0
    bcs = []
    root = "Event Conditions/Unsteady/Boundary Conditions"
    def grp_items(path):
        try:
            if path in hdf: return list(hdf[path].items())
        except Exception: pass
        return []
    for loc_key, ds in grp_items(root + "/Flow Hydrographs"):
        try:
            arr = ds[...]
            if arr.ndim == 2 and arr.shape[1] >= 2:
                times_s = [float(t) * HR_TO_S for t in arr[:, 0]]
                values_m3s = [float(v) * cfs for v in arr[:, 1]]
            else:
                times_s = []; values_m3s = [float(v) * cfs for v in arr.ravel()]
            bcs.append({"type": "flow_hydrograph", "location": _b2s(loc_key),
                "times_s": times_s, "values_m3s": values_m3s})
        except Exception: continue
    for loc_key, ds in grp_items(root + "/Normal Depths"):
        try:
            arr = ds[...]
            slope = _safe_f(arr.ravel()[0])
            bcs.append({"type": "normal_depth", "location": _b2s(loc_key), "slope": slope})
        except Exception: continue
    for loc_key, ds in grp_items(root + "/Stage Hydrographs"):
        try:
            arr = ds[...]
            if arr.ndim == 2 and arr.shape[1] >= 2:
                times_s = [float(t) * HR_TO_S for t in arr[:, 0]]
                values_m = [float(v) * lf for v in arr[:, 1]]
            else:
                times_s = []; values_m = [float(v) * lf for v in arr.ravel()]
            bcs.append({"type": "stage_hydrograph", "location": _b2s(loc_key),
                "times_s": times_s, "values_m": values_m})
        except Exception: continue
    for loc_key, ds in grp_items(root + "/Rating Curves"):
        try:
            arr = ds[...]
            if arr.ndim == 2 and arr.shape[1] >= 2:
                flow_m3s = [float(v) * cfs for v in arr[:, 0]]
                stage_m = [float(v) * lf for v in arr[:, 1]]
            else:
                flow_m3s = []; stage_m = []
            bcs.append({"type": "rating_curve", "location": _b2s(loc_key),
                "flow_m3s": flow_m3s, "stage_m": stage_m})
        except Exception: continue
    return bcs

def _extract_timeseries(hdf, is_english: bool):
    lf = LF if is_english else 1.0
    cfs = CFS_TO_M3S if is_english else 1.0
    ts_root = "Results/Unsteady/Output/Output Blocks/Base Output/Unsteady Time Series"
    out = {"n_timesteps": 0, "times_s": [], "time_stamps": [],
           "water_surface_m": [], "flow_m3s_ts": []}
    time_arr = _read(hdf, ts_root + "/Time")
    if time_arr is None: return out
    times_s = [float(t) * HR_TO_S for t in time_arr]
    out["times_s"] = times_s; out["n_timesteps"] = len(times_s)
    stamp_arr = _read(hdf, ts_root + "/Time Date Stamp")
    if stamp_arr is not None: out["time_stamps"] = [_b2s(s) for s in stamp_arr]
    ws_arr = _read(hdf, ts_root + "/Cross Sections/Water Surface")
    if ws_arr is not None: out["water_surface_m"] = (ws_arr * lf).tolist()
    flow_arr = _read(hdf, ts_root + "/Cross Sections/Flow")
    if flow_arr is not None: out["flow_m3s_ts"] = (flow_arr * cfs).tolist()
    return out


def _check_structures(hdf) -> bool:
    try:
        struct_attrs = _read(hdf, "Geometry/Structures/Attributes")
        if struct_attrs is not None and len(struct_attrs) > 0: return True
    except Exception: pass
    return False


def _extract_case(suite_num, case_name, hdf_pattern):
    suite_dirs = sorted(SUITE_BASE.glob(suite_num + "*"))
    if not suite_dirs:
        print("  [WARN] %s: suite dir not found" % case_name); return None
    suite_dir = suite_dirs[0]
    if not suite_dir.is_dir():
        print("  [WARN] %s: not a dir" % case_name); return None
    inner_dirs = [d for d in suite_dir.iterdir() if d.is_dir()]
    search_dir = inner_dirs[0] if inner_dirs else suite_dir
    hdf_files = sorted(search_dir.glob(hdf_pattern))
    if not hdf_files:
        print("  [WARN] %s: no HDF %s in %s" % (case_name, hdf_pattern, search_dir))
        return None
    hdf_path = hdf_files[0]
    print("  reading: %s" % hdf_path.name)
    with h5py.File(hdf_path, "r") as f:
        unit_sys = _unit_system(f)
        is_eng = unit_sys == "english"
        geom = _extract_geometry(f, is_eng)
        bcs = _extract_bcs(f, is_eng)
        ts = _extract_timeseries(f, is_eng)
        has_struct = _check_structures(f)
    result: Dict[str, Any] = {"case_name": case_name, "source_hdf": str(hdf_path),
        "mode": "unsteady", "unit_system": unit_sys}
    result.update(geom)
    result["boundary_conditions"] = bcs
    result["n_timesteps"] = ts["n_timesteps"]
    result["times_s"] = ts["times_s"]
    result["time_stamps"] = ts["time_stamps"]
    result["water_surface_m"] = ts["water_surface_m"]
    result["flow_m3s"] = ts["flow_m3s_ts"]
    result["has_structures"] = has_struct
    return result


def main():
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    print("Output dir: %s" % OUTPUT_DIR)
    print()
    successes = failures = 0
    for suite_num, case_name, hdf_pattern in CASES:
        print("[%s] %s ..." % (suite_num, case_name))
        try:
            data = _extract_case(suite_num, case_name, hdf_pattern)
            if data is None: failures += 1; continue
            out_path = OUTPUT_DIR / ("%s_unsteady_ref.json" % case_name)
            with out_path.open("w", encoding="utf-8") as fout:
                json.dump(data, fout, cls=_NumpyEncoder, indent=2, ensure_ascii=False)
            n_xs = data.get("n_cross_sections", 0)
            n_ts = data.get("n_timesteps", 0)
            n_bc = len(data.get("boundary_conditions", []))
            print("  => xs=%d  timesteps=%d  bcs=%d  structures=%s" % (
                n_xs, n_ts, n_bc, data.get("has_structures", False)))
            print("  => saved: %s" % out_path.name)
            successes += 1
        except Exception as exc:
            import traceback
            print("  [ERROR] %s: %s" % (case_name, exc))
            traceback.print_exc()
            failures += 1
    print()
    print("Done: %d success, %d failed" % (successes, failures))


if __name__ == "__main__":
    main()
