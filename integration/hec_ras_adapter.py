"""HEC-RAS runtime detection and benchmark scaffolding.

This module provides the minimum integration surface needed to connect
HydroClaude/HydroMind to a local Windows HEC-RAS installation.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any
import json
import re
import tempfile
import time

import h5py
import numpy as np


COMMON_HECRAS_PATHS = [
    Path(r"C:\Program Files (x86)\HEC\HEC-RAS\6.6\Ras.exe"),
    Path(r"C:\Program Files\HEC\HEC-RAS\6.6\RAS.exe"),
    Path(r"C:\Program Files\HEC\HEC-RAS\6.5\RAS.exe"),
    Path(r"C:\Program Files\HEC\HEC-RAS\6.4\RAS.exe"),
    Path(r"C:\Program Files (x86)\HEC\HEC-RAS\5.0.7\RAS.exe"),
]

COMMON_PROGIDS = [
    "RAS66.HECRASController",
    "RAS65.HECRASController",
    "RAS64.HECRASController",
    "RAS507.HECRASController",
    "RAS506.HECRASController",
    "RAS41.HECRASController",
]

FT_TO_M = 0.3048
CFS_TO_M3S = 0.028316846592


HECRAS_ADAPTER_VERSION = "hec_ras_adapter_v2"


@dataclass
class HECRASRuntimeStatus:
    installed: bool
    com_available: bool
    exe_path: str | None
    progid: str | None
    notes: list[str]


def detect_hec_ras_runtime() -> HECRASRuntimeStatus:
    """Detect a local HEC-RAS runtime and COM controller."""
    exe_path = None
    for candidate in COMMON_HECRAS_PATHS:
        if candidate.exists():
            exe_path = str(candidate)
            break

    notes: list[str] = []
    progid = None
    com_available = False
    try:
        import win32com.client  # type: ignore[import-untyped]

        for candidate in COMMON_PROGIDS:
            try:
                controller = win32com.client.Dispatch(candidate)
                progid = candidate
                com_available = True
                try:
                    if hasattr(controller, "QuitRAS"):
                        controller.QuitRAS()
                except Exception:
                    pass
                break
            except Exception:
                continue
    except Exception as exc:
        notes.append(f"pywin32 unavailable: {exc}")

    installed = exe_path is not None or com_available
    if not exe_path:
        notes.append("No common HEC-RAS executable path found on this machine.")
    if not com_available:
        notes.append("No known HECRASController COM ProgID could be instantiated.")

    return HECRASRuntimeStatus(
        installed=installed,
        com_available=com_available,
        exe_path=exe_path,
        progid=progid,
        notes=notes,
    )


def collect_hec_ras_case_scaffold(case_dir: str | Path) -> dict[str, Any]:
    """Summarize the provenance scaffold for a HEC-RAS benchmark case."""
    root = Path(case_dir)
    evidence_dir = root / "evidence"
    export_files = sorted(str(path) for path in (evidence_dir / "exports").glob("*") if path.is_file())
    screenshot_files = sorted(str(path) for path in (evidence_dir / "screenshots").glob("*") if path.is_file())
    note_files = sorted(str(path) for path in (evidence_dir / "transcribed_notes").glob("*") if path.is_file())

    status = {
        "case_dir": str(root),
        "readme_exists": (root / "README.md").exists(),
        "metadata_exists": (root / "case_metadata.yaml").exists(),
        "parameters_exists": (root / "parameters.yaml").exists(),
        "expected_results_exists": (root / "expected_results.yaml").exists(),
        "raw_project_present": any(root.glob("*.prj")),
        "export_file_count": len(export_files),
        "screenshot_file_count": len(screenshot_files),
        "transcribed_note_count": len(note_files),
        "export_files": export_files,
        "screenshot_files": screenshot_files,
        "note_files": note_files,
    }
    return status


def prepare_hec_ras_benchmark(case_name: str = "hec_ras_steady_flow_example_3_1") -> dict[str, Any]:
    """Return the current benchmark scaffold and runtime status."""
    root = Path(__file__).resolve().parents[1]
    case_dir = root / "validation_cases" / "engineering" / case_name
    runtime = detect_hec_ras_runtime()
    scaffold = collect_hec_ras_case_scaffold(case_dir)
    return {
        "runtime": asdict(runtime),
        "case": scaffold,
        "ready_for_true_run": bool(runtime.installed and runtime.com_available and scaffold["raw_project_present"]),
    }


def export_hec_ras_status_json(output_path: str | Path, case_name: str = "hec_ras_steady_flow_example_3_1") -> Path:
    """Write the HEC-RAS readiness state to JSON."""
    path = Path(output_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    payload = prepare_hec_ras_benchmark(case_name=case_name)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    return path


def _init_ras_project(project_path: str | Path) -> tuple[Path, Any]:
    """Initialise a HEC-RAS project through ras-commander."""
    from ras_commander import init_ras_project

    path = Path(project_path)
    if not path.exists() or not path.is_dir():
        raise FileNotFoundError(f"HEC-RAS project directory not found: {path}")

    runtime = detect_hec_ras_runtime()
    ras_version = runtime.exe_path or "6.6"
    ras = init_ras_project(path, ras_version)
    return path, ras


def _resolve_plan_hdf_path(project_path: Path, plan_number: str, ras: Any) -> Path:
    """Resolve a plan number or direct HDF path to a plan HDF file."""
    if plan_number.isdigit() and len(plan_number) == 1:
        plan_number = plan_number.zfill(2)

    direct_path = Path(plan_number)
    if plan_number.lower().endswith(".hdf") and direct_path.exists():
        return direct_path

    plan_hdf_path = None
    if hasattr(ras, "plan_df") and ras.plan_df is not None:
        plan_row = ras.plan_df[ras.plan_df["plan_number"] == plan_number]
        if not plan_row.empty and "HDF_Results_Path" in plan_row.columns:
            hdf_rel_path = plan_row["HDF_Results_Path"].iloc[0]
            if hdf_rel_path:
                plan_hdf_path = project_path / hdf_rel_path

    if not plan_hdf_path:
        potential_paths = list(project_path.glob(f"*.p{plan_number}.hdf")) + list(project_path.glob(f"*.P{plan_number}.hdf"))
        if potential_paths:
            plan_hdf_path = potential_paths[0]

    if not plan_hdf_path or not plan_hdf_path.exists():
        raise FileNotFoundError(f"Plan '{plan_number}' not found or has no results HDF file in {project_path}")

    return plan_hdf_path


def _safe_records(df: Any, max_rows: int = 50) -> list[dict[str, Any]]:
    """Convert a pandas DataFrame to plain JSON-safe records."""
    if df is None:
        return []
    limited = df.head(max_rows).copy()
    limited = limited.replace({np.nan: None})
    return json.loads(limited.to_json(orient="records", force_ascii=False))


def summarize_hec_ras_project(project_path: str | Path, include_tables: bool = True) -> dict[str, Any]:
    """Return a structured summary of a HEC-RAS project via ras-commander."""
    path, ras = _init_ras_project(project_path)

    summary: dict[str, Any] = {
        "project_path": str(path),
        "project_name": getattr(ras, "project_name", path.name),
        "prj_file": str(getattr(ras, "prj_file", "")) if getattr(ras, "prj_file", None) else None,
        "runtime": asdict(detect_hec_ras_runtime()),
    }
    if not include_tables:
        return summary

    summary["tables"] = {
        "plans": _safe_records(getattr(ras, "plan_df", None)),
        "geometries": _safe_records(getattr(ras, "geom_df", None)),
        "steady_flows": _safe_records(getattr(ras, "flow_df", None)),
        "unsteady_flows": _safe_records(getattr(ras, "unsteady_df", None)),
        "boundaries": _safe_records(getattr(ras, "boundaries_df", None)),
    }
    summary["counts"] = {
        "plans": len(summary["tables"]["plans"]),
        "geometries": len(summary["tables"]["geometries"]),
        "steady_flows": len(summary["tables"]["steady_flows"]),
        "unsteady_flows": len(summary["tables"]["unsteady_flows"]),
        "boundaries": len(summary["tables"]["boundaries"]),
    }
    return summary


def read_hec_ras_plan_description(project_path: str | Path, plan_number: str) -> dict[str, Any]:
    """Read the multi-line description block from a HEC-RAS plan file."""
    from ras_commander import RasPlan

    path, ras = _init_ras_project(project_path)
    normalized = plan_number.zfill(2) if plan_number.isdigit() and len(plan_number) == 1 else plan_number
    description = RasPlan.read_plan_description(normalized, ras)
    return {
        "project_path": str(path),
        "project_name": getattr(ras, "project_name", path.name),
        "plan_number": normalized,
        "description": description or "",
    }


def get_hec_ras_compute_messages(project_path: str | Path, plan_number: str) -> dict[str, Any]:
    """Extract compute messages from a HEC-RAS plan HDF."""
    path, ras = _init_ras_project(project_path)
    hdf_path = _resolve_plan_hdf_path(path, plan_number, ras)

    dataset_path = "/Results/Summary/Compute Messages (text)"
    with h5py.File(hdf_path, "r") as hdf_file:
        if dataset_path not in hdf_file:
            return {
                "project_path": str(path),
                "plan_number": plan_number,
                "hdf_path": str(hdf_path),
                "dataset_found": False,
                "messages_text": "",
            }
        data = hdf_file[dataset_path][()]

    if isinstance(data, bytes):
        text = data.decode("utf-8", errors="ignore")
    elif isinstance(data, np.ndarray) and data.dtype.kind == "S":
        text = "\n".join(item.decode("utf-8", errors="ignore") if isinstance(item, bytes) else str(item) for item in data)
    else:
        text = str(data)

    lines = [line.strip() for line in re.split(r"\r\n|\n", text) if line.strip()]
    return {
        "project_path": str(path),
        "project_name": getattr(ras, "project_name", path.name),
        "plan_number": plan_number,
        "hdf_path": str(hdf_path),
        "dataset_found": True,
        "line_count": len(lines),
        "messages_preview": lines[:40],
        "messages_text": text,
    }


def get_hec_ras_plan_results_summary(project_path: str | Path, plan_number: str) -> dict[str, Any]:
    """Read plan-level result summaries from a HEC-RAS plan HDF."""
    from ras_commander import HdfResultsPlan

    path, ras = _init_ras_project(project_path)
    hdf_path = _resolve_plan_hdf_path(path, plan_number, ras)

    payload: dict[str, Any] = {
        "project_path": str(path),
        "project_name": getattr(ras, "project_name", path.name),
        "plan_number": plan_number,
        "hdf_path": str(hdf_path),
    }

    for key, fn in {
        "unsteady_info": HdfResultsPlan.get_unsteady_info,
        "unsteady_summary": HdfResultsPlan.get_unsteady_summary,
        "volume_accounting": HdfResultsPlan.get_volume_accounting,
        "runtime_data": HdfResultsPlan.get_runtime_data,
    }.items():
        try:
            payload[key] = _safe_records(fn(hdf_path))
        except Exception as exc:
            payload[f"{key}_error"] = str(exc)

    return payload


def get_hec_ras_hdf_structure(hdf_path: str | Path, group_path: str = "/", paths_only: bool = True) -> dict[str, Any]:
    """Explore the structure of a HEC-RAS HDF file."""
    path = Path(hdf_path)
    if not path.exists():
        raise FileNotFoundError(f"HDF file not found: {path}")

    items: list[str] = []
    with h5py.File(path, "r") as hdf:
        if group_path != "/" and group_path not in hdf:
            raise KeyError(f"Group path not found in HDF: {group_path}")

        root = hdf[group_path] if group_path != "/" else hdf

        def _collect(name: str, obj: Any) -> None:
            prefix = "Group" if isinstance(obj, h5py.Group) else "Dataset"
            items.append(f"{prefix}: /{name}")

        root.visititems(_collect)

    return {
        "hdf_path": str(path),
        "group_path": group_path,
        "paths_only": paths_only,
        "item_count": len(items),
        "items": items[:1000],
    }


def get_hec_ras_projection_info(hdf_path: str | Path) -> dict[str, Any]:
    """Read spatial projection WKT from a HEC-RAS HDF file."""
    from ras_commander import HdfBase

    path = Path(hdf_path)
    if not path.exists():
        raise FileNotFoundError(f"HDF file not found: {path}")

    projection = HdfBase.get_projection(path)
    return {
        "hdf_path": str(path),
        "projection_wkt": projection or "",
        "has_projection": bool(projection),
    }


def run_hec_ras_mixed_flow_sample(output_root: str | Path | None = None) -> dict[str, Any]:
    """Run the official HEC-RAS mixed-flow sample and compare with Hydrostatic."""
    from ras_commander import RasExamples
    import win32com.client  # type: ignore[import-untyped]

    from solvers.hydrostatic_canal_solver import HydrostaticCanalSolver

    root = Path(output_root) if output_root else Path(tempfile.gettempdir()) / "hydroclaude_hec_ras_example_project"
    root.mkdir(parents=True, exist_ok=True)
    project_dir = RasExamples.extract_project("Mixed Flow Regime Channel", output_path=root, suffix="hydromind")
    prj_path = next(project_dir.glob("*.prj"))
    g_path = next(project_dir.glob("*.g01"))
    p_path = next(project_dir.glob("*.P01"))

    ras = win32com.client.gencache.EnsureDispatch("RAS66.HECRASController")
    try:
        ras.Project_Open(str(prj_path))
        try:
            ras.Compute_HideComputationWindow()
        except Exception:
            pass
        ras.Compute_CurrentPlan(None, None, True)
    finally:
        try:
            ras.QuitRas()
        except Exception:
            pass

    hdf_candidates = []
    for _ in range(20):
        hdf_candidates = list(project_dir.glob("*.p01.hdf")) + list(project_dir.glob("*.P01.hdf"))
        if hdf_candidates:
            break
        time.sleep(1.0)
    if not hdf_candidates:
        raise FileNotFoundError(f"No HEC-RAS plan HDF found after compute in {project_dir}")
    hdf_path = hdf_candidates[0]

    text = g_path.read_text(encoding="utf-8", errors="ignore")
    pattern = re.compile(
        r"Type RM Length L Ch R =\s*1\s*,\s*([0-9.]+)\s*,,\s*([0-9.]*)[, ]*.*?#Sta/Elev=\s*4\s*\n\s*0\s+[0-9.]+\s+0\s+([0-9.]+)\s+20\s+([0-9.]+)",
        re.S,
    )
    xs = []
    for rs_str, len_str, bed_left, _ in pattern.findall(text):
        xs.append((float(rs_str), float(len_str) if len_str else 0.0, float(bed_left)))
    xs = sorted(xs, key=lambda item: item[0], reverse=True)
    reach_lengths = np.asarray([item[1] for item in xs], dtype=float)
    bed = np.asarray([item[2] for item in xs], dtype=float)
    x = np.zeros(len(xs), dtype=float)
    for idx in range(1, len(xs)):
        x[idx] = x[idx - 1] + reach_lengths[idx - 1]
    slope_segments = np.diff(bed) * -1.0 / np.diff(x)

    with h5py.File(hdf_path, "r") as hdf:
        base = "Results/Steady/Output/Output Blocks/Base Output/Steady Profiles/Cross Sections"
        ws = hdf[f"{base}/Water Surface"][:]
        eg = hdf[f"{base}/Energy Grade"][:]
        flow = hdf[f"{base}/Flow"][:]
        names = hdf["Results/Steady/Output/Output Blocks/Base Output/Steady Profiles/Profile Names"][:]
    profile_names = [item.decode(errors="ignore").strip() if isinstance(item, bytes) else str(item) for item in names]

    profile_index = 0
    hec_stage = np.asarray(ws[profile_index], dtype=float)
    hec_depth = hec_stage - bed
    hec_energy = np.asarray(eg[profile_index], dtype=float)
    hec_flow = np.asarray(flow[profile_index], dtype=float)

    hydro = HydrostaticCanalSolver(
        length=float(x[-1]),
        x_grid=x,
        B=20.0,
        S0=slope_segments,
        n=0.015,
        g=32.2,
    )
    hydro_result = hydro.solve_steady_state(
        Q_target=float(hec_flow[0]),
        h_downstream=float(hec_depth[-1]),
        dt=0.2,
        max_iterations=8000,
        convergence_tol=1e-4,
        verbose=False,
    )
    hydro_depth = np.asarray(hydro_result["h"], dtype=float)
    hydro_stage = hydro_depth + bed

    abs_error = np.abs(hydro_depth - hec_depth)
    rel_error = abs_error / np.maximum(np.abs(hec_depth), 1e-9)

    return {
        "project": {
            "project_dir": str(project_dir),
            "project_file": str(prj_path),
            "geometry_file": str(g_path),
            "plan_file": str(p_path),
            "hdf_file": str(hdf_path),
            "profile_name": profile_names[profile_index],
        },
        "hec_ras": {
            "x_ft": x.tolist(),
            "x_m": (x * FT_TO_M).tolist(),
            "bed_ft": bed.tolist(),
            "bed_m": (bed * FT_TO_M).tolist(),
            "stage_ft": hec_stage.tolist(),
            "stage_m": (hec_stage * FT_TO_M).tolist(),
            "depth_ft": hec_depth.tolist(),
            "depth_m": (hec_depth * FT_TO_M).tolist(),
            "energy_grade_ft": hec_energy.tolist(),
            "energy_grade_m": (hec_energy * FT_TO_M).tolist(),
            "flow_cfs": hec_flow.tolist(),
            "flow_m3s": (hec_flow * CFS_TO_M3S).tolist(),
            "profile_names": profile_names,
        },
        "hydrostatic": {
            "depth_ft": hydro_depth.tolist(),
            "depth_m": (hydro_depth * FT_TO_M).tolist(),
            "stage_ft": hydro_stage.tolist(),
            "stage_m": (hydro_stage * FT_TO_M).tolist(),
            "q_error_pct": float(hydro_result["Q_error_percent"]),
        },
        "metrics": {
            "upstream_rel_error_pct": float(rel_error[0] * 100.0),
            "mean_rel_error_pct": float(np.mean(rel_error) * 100.0),
            "max_rel_error_pct": float(np.max(rel_error) * 100.0),
            "mean_abs_error_ft": float(np.mean(abs_error)),
            "mean_abs_error_m": float(np.mean(abs_error) * FT_TO_M),
            "max_abs_error_ft": float(np.max(abs_error)),
            "max_abs_error_m": float(np.max(abs_error) * FT_TO_M),
            "hec_flow_cfs": float(hec_flow[0]),
            "hec_flow_m3s": float(hec_flow[0] * CFS_TO_M3S),
            "hec_downstream_depth_ft": float(hec_depth[-1]),
            "hec_downstream_depth_m": float(hec_depth[-1] * FT_TO_M),
            "hec_upstream_depth_ft": float(hec_depth[0]),
            "hec_upstream_depth_m": float(hec_depth[0] * FT_TO_M),
            "hydrostatic_upstream_depth_ft": float(hydro_depth[0]),
            "hydrostatic_upstream_depth_m": float(hydro_depth[0] * FT_TO_M),
        },
    }


# ======================================================================
# Unified HEC-RAS result extraction API (v2)
# ======================================================================

def _detect_unit_system(project_file: Path | None) -> str:
    """Detect unit system from a HEC-RAS .prj file."""
    if not project_file or not project_file.exists():
        return "english"
    text = project_file.read_text(encoding="utf-8", errors="ignore").lower()
    if "si units" in text:
        return "si"
    return "english"


def _length_factor(unit_system: str) -> float:
    return 1.0 if unit_system == "si" else FT_TO_M


def _flow_factor(unit_system: str) -> float:
    return 1.0 if unit_system == "si" else CFS_TO_M3S


def _decode_bytes(value: Any) -> str:
    if isinstance(value, bytes):
        return value.decode("utf-8", errors="ignore").strip()
    return str(value).strip()


def _decode_station_attrs(arr: np.ndarray) -> tuple[np.ndarray, list[str], list[str]]:
    """Decode cross-section attributes into (stations, rivers, reaches)."""
    stations: list[float] = []
    rivers: list[str] = []
    reaches: list[str] = []
    for row in arr:
        raw = row["Station"]
        text = _decode_bytes(raw)
        try:
            stations.append(float(text))
        except (ValueError, TypeError):
            stations.append(float("nan"))
        rivers.append(_decode_bytes(row["River"]))
        reaches.append(_decode_bytes(row["Reach"]))
    return np.asarray(stations, dtype=float), rivers, reaches


@dataclass
class HECRASResultSummary:
    """Structured summary of HEC-RAS results for comparison pipeline."""
    mode: str  # "steady" or "unsteady"
    unit_system: str
    hdf_path: str
    n_cross_sections: int
    n_profiles: int
    rivers: list[str]
    reaches: list[str]
    stations_m: list[float]
    water_surface_m: list[list[float]]  # [profile][xs]
    flow_m3s: list[list[float]]         # [profile][xs]
    energy_grade_m: list[list[float]]   # [profile][xs]  (steady only)
    profile_names: list[str]
    bed_elevation_m: list[float] | None  # per xs, if available
    manning_n_values: list[float] | None  # per xs, if available
    channel_width_m: list[float] | None  # per xs, if available
    has_structures: bool = False  # True when HDF contains bridges/culverts/weirs/gates

    def to_dict(self) -> dict[str, Any]:
        return {k: v for k, v in self.__dict__.items()}


def extract_hecras_result_summary(
    hdf_path: str | Path,
    project_file: str | Path | None = None,
) -> HECRASResultSummary:
    """Extract a unified result summary from a HEC-RAS plan HDF.

    This is the single entry point for the comparison pipeline to consume
    HEC-RAS results.  It handles both steady and unsteady result layouts
    and automatically converts to SI units.

    Args:
        hdf_path: Path to a plan .hdf file.
        project_file: Optional .prj file for unit detection.

    Returns:
        Structured result summary ready for comparison.
    """
    hdf_p = Path(hdf_path)
    if not hdf_p.exists():
        raise FileNotFoundError(f"HDF not found: {hdf_p}")

    prj_p = Path(project_file) if project_file else None
    unit_system = _detect_unit_system(prj_p)
    lf = _length_factor(unit_system)
    qf = _flow_factor(unit_system)

    with h5py.File(hdf_p, "r") as hdf:
        # --- Try steady first ---
        steady_base = "Results/Steady/Output/Output Blocks/Base Output/Steady Profiles/Cross Sections"
        if f"{steady_base}/Water Surface" in hdf:
            attrs = hdf["Results/Steady/Output/Geometry Info/Cross Section Attributes"][:]
            stations_raw, rivers, reaches = _decode_station_attrs(attrs)
            stations_m = (np.nan_to_num(stations_raw, nan=0.0) * lf).tolist()
            ws = (np.asarray(hdf[f"{steady_base}/Water Surface"][:], dtype=float) * lf).tolist()
            flow = (np.asarray(hdf[f"{steady_base}/Flow"][:], dtype=float) * qf).tolist()
            eg = (np.asarray(hdf[f"{steady_base}/Energy Grade"][:], dtype=float) * lf).tolist()
            pn_raw = hdf["Results/Steady/Output/Output Blocks/Base Output/Steady Profiles/Profile Names"][:]
            profile_names = [_decode_bytes(item) for item in pn_raw]

            bed_elev = _try_read_bed_elevation(hdf, lf)
            manning_n = _try_read_manning(hdf)
            width = _try_read_channel_width(hdf, lf)
            has_structures = _detect_structures(hdf)

            return HECRASResultSummary(
                mode="steady",
                unit_system=unit_system,
                hdf_path=str(hdf_p),
                n_cross_sections=len(stations_m),
                n_profiles=len(profile_names),
                rivers=rivers,
                reaches=reaches,
                stations_m=stations_m,
                water_surface_m=ws,
                flow_m3s=flow,
                energy_grade_m=eg,
                profile_names=profile_names,
                bed_elevation_m=bed_elev,
                manning_n_values=manning_n,
                channel_width_m=width,
                has_structures=has_structures,
            )

        # --- Unsteady fallback ---
        us_base = "Results/Unsteady/Output/Output Blocks/Base Output/Unsteady Time Series/Cross Sections"
        if f"{us_base}/Water Surface" not in hdf:
            raise KeyError("No steady or unsteady cross-section results found in HDF")

        attrs = hdf[f"{us_base}/Cross Section Attributes"][:]
        stations_raw, rivers, reaches = _decode_station_attrs(attrs)
        stations_m = (np.nan_to_num(stations_raw, nan=0.0) * lf).tolist()
        ws = (np.asarray(hdf[f"{us_base}/Water Surface"][:], dtype=float) * lf).tolist()
        flow = (np.asarray(hdf[f"{us_base}/Flow"][:], dtype=float) * qf).tolist()

        bed_elev = _try_read_bed_elevation(hdf, lf)
        manning_n = _try_read_manning(hdf)
        width = _try_read_channel_width(hdf, lf)
        has_structures = _detect_structures(hdf)

        return HECRASResultSummary(
            mode="unsteady",
            unit_system=unit_system,
            hdf_path=str(hdf_p),
            n_cross_sections=len(stations_m),
            n_profiles=len(ws),
            rivers=rivers,
            reaches=reaches,
            stations_m=stations_m,
            water_surface_m=ws,
            flow_m3s=flow,
            energy_grade_m=[],
            profile_names=[f"timestep_{i}" for i in range(len(ws))],
            bed_elevation_m=bed_elev,
            manning_n_values=manning_n,
            channel_width_m=width,
            has_structures=has_structures,
        )


def _try_read_bed_elevation(hdf: h5py.File, lf: float) -> list[float] | None:
    """Try to read minimum bed elevation per cross-section.

    Resolution order:
    1. Min Ch El from cross-section attributes (direct field)
    2. Station Elevation Values — compute min elevation per XS from raw geometry
    """
    # Method 1: Direct Min Ch El attribute
    for path in ["Results/Steady/Output/Geometry Info/Cross Section Attributes",
                 "Results/Unsteady/Output/Geometry Info/Cross Section Attributes"]:
        if path in hdf:
            attrs = hdf[path][:]
            if "Min Ch El" in attrs.dtype.names:
                return (np.asarray(attrs["Min Ch El"], dtype=float) * lf).tolist()

    # Method 2: Compute from raw station-elevation geometry
    info_path = "Geometry/Cross Sections/Station Elevation Info"
    vals_path = "Geometry/Cross Sections/Station Elevation Values"
    if info_path in hdf and vals_path in hdf:
        info = hdf[info_path][:]
        vals = np.asarray(hdf[vals_path][:], dtype=float)
        min_elevs: list[float] = []
        for row in info:
            start = int(row[0])
            count = int(row[1])
            if count > 0 and start + count <= len(vals):
                elevations = vals[start:start + count, 1]  # column 1 = elevation
                min_elevs.append(float(np.min(elevations)) * lf)
            else:
                min_elevs.append(float("nan"))
        if min_elevs:
            return min_elevs

    return None


def _try_read_manning(hdf: h5py.File) -> list[float] | None:
    """Try to read Manning's n per cross-section from geometry."""
    for path in ["Geometry/Cross Sections/Manning's n Values",
                 "Geometry/Cross Sections/Mannings n"]:
        if path in hdf:
            data = np.asarray(hdf[path][:], dtype=float)
            if data.ndim == 1:
                return data.tolist()
            # Multi-column (LOB, Channel, ROB) — take channel (middle)
            if data.ndim == 2 and data.shape[1] >= 2:
                return data[:, data.shape[1] // 2].tolist()
    return None


def _try_read_channel_width(hdf: h5py.File, lf: float) -> list[float] | None:
    """Try to read main channel top width per cross-section.

    Resolution order:
    1. Top Width from steady results (profile-indexed)
    2. Estimated from Station Elevation geometry (full station range)
    """
    # Method 1: Top Width from results
    path = "Results/Steady/Output/Output Blocks/Base Output/Steady Profiles/Cross Sections/Top Width"
    if path in hdf:
        data = np.asarray(hdf[path][:], dtype=float)
        if data.ndim == 1:
            return (data * lf).tolist()
        if data.ndim == 2:
            return (data[0] * lf).tolist()

    # Method 2: Estimate from station-elevation geometry (max station - min station)
    info_path = "Geometry/Cross Sections/Station Elevation Info"
    vals_path = "Geometry/Cross Sections/Station Elevation Values"
    if info_path in hdf and vals_path in hdf:
        info = hdf[info_path][:]
        vals = np.asarray(hdf[vals_path][:], dtype=float)
        widths: list[float] = []
        for row in info:
            start = int(row[0])
            count = int(row[1])
            if count > 0 and start + count <= len(vals):
                stations = vals[start:start + count, 0]
                widths.append(float(np.max(stations) - np.min(stations)) * lf)
            else:
                widths.append(float("nan"))
        if widths:
            return widths

    return None


def _estimate_reach_length(
    stations: np.ndarray, bed: np.ndarray, avg_slope: float, n_xs: int,
) -> float:
    """Estimate physical reach length from available data.

    HEC-RAS River Station numbers are not always physical distances.
    When the station range yields an unreasonably short channel (< 10 m
    for > 5 cross-sections), fall back to bed-drop / slope or a
    heuristic based on cross-section count.
    """
    # Primary: station range
    if len(stations) > 1:
        station_range = float(abs(stations[0] - stations[-1]))
        if station_range > 10.0 or n_xs <= 5:
            return max(station_range, 1.0)

    # Fallback 1: bed drop / slope
    if len(bed) > 1 and avg_slope > 1e-4:
        bed_drop = float(abs(bed[0] - bed[-1]))
        length_est = bed_drop / avg_slope
        if length_est > 10.0:
            return length_est

    # Fallback 2: assume 100m spacing between cross-sections
    return max(float(n_xs) * 100.0, 100.0)


def _detect_structures(hdf: h5py.File) -> bool:
    """Return True when the HDF contains *actual* hydraulic structures.

    The ``Geometry/Structures`` group exists in almost every HEC-RAS HDF
    (even when empty) because it stores standard metadata.  We look for
    specific sub-groups that indicate real bridges, culverts, or gates.
    """
    # Direct structure group paths (unambiguous)
    direct_paths = [
        "Geometry/Bridges",
        "Geometry/Bridge Culverts",
        "Geometry/Culverts",
        "Geometry/Inline Structures",
        "Geometry/Lateral Structures",
    ]
    for path in direct_paths:
        if path in hdf:
            try:
                obj = hdf[path]
                if isinstance(obj, h5py.Group) and len(obj) > 0:
                    return True
            except Exception:
                pass

    # Inside Geometry/Structures, look for actual structure data
    # (Culvert Groups, Bridge Data, Gate Groups, etc.)
    struct_indicators = [
        "Geometry/Structures/Culvert Groups",
        "Geometry/Structures/Bridge Data",
        "Geometry/Structures/Gate Groups",
        "Geometry/Structures/Weir Data",
    ]
    for path in struct_indicators:
        if path in hdf:
            return True

    return False


def diagnose_flow_regime(result_summary: HECRASResultSummary, g: float = 9.81) -> dict[str, Any]:
    """Diagnose the flow regime from HEC-RAS results using hydraulic principles.

    Uses HEC-RAS's standard energy equation approach:
    - Compute Froude number at each cross-section
    - Classify as subcritical/supercritical/mixed
    - Identify backwater curve type (M1, M2, S1, S2, etc.)
    - Recommend appropriate HydroClaude solver and parameters

    This is the "principle-driven diagnostic" step that should run BEFORE
    any HydroMind simulation, to avoid blindly trying solvers.

    Returns:
        Dictionary with diagnostic info and solver recommendation.
    """
    if not result_summary.water_surface_m or not result_summary.flow_m3s:
        return {"error": "No water surface or flow data available", "solver_recommendation": "hydrostatic"}

    # For unsteady cases, use the peak-WSE timestep for diagnosis;
    # for steady cases, use the first (and usually only) profile.
    if len(result_summary.water_surface_m) > 1:
        all_ws = np.asarray(result_summary.water_surface_m, dtype=float)
        peak_idx = int(np.argmax(np.nanmean(all_ws, axis=1)))
        ws = all_ws[peak_idx]
        flow = np.asarray(result_summary.flow_m3s[peak_idx], dtype=float)
    else:
        ws = np.asarray(result_summary.water_surface_m[0], dtype=float)
        flow = np.asarray(result_summary.flow_m3s[0], dtype=float)
    bed = np.asarray(result_summary.bed_elevation_m, dtype=float) if result_summary.bed_elevation_m else None
    width = np.asarray(result_summary.channel_width_m, dtype=float) if result_summary.channel_width_m else None

    if bed is None:
        # Estimate bed as minimum water surface minus a reasonable depth
        bed = ws - np.maximum(ws - np.nanmin(ws), 0.5)

    depth = ws - bed
    depth = np.maximum(depth, 1e-6)

    if width is None:
        width = np.full_like(depth, 10.0)  # fallback

    # Cross-sectional area and velocity
    area = width * depth
    velocity = np.where(area > 1e-6, np.abs(flow) / area, 0.0)

    # Froude number
    froude = velocity / np.sqrt(g * depth)
    froude_mean = float(np.nanmean(froude))
    froude_max = float(np.nanmax(froude))
    froude_min = float(np.nanmin(froude))

    # Flow regime classification
    subcritical_frac = float(np.nanmean(froude < 1.0))
    supercritical_frac = float(np.nanmean(froude > 1.0))
    near_critical_frac = float(np.nanmean(np.abs(froude - 1.0) < 0.15))

    if supercritical_frac > 0.3:
        regime = "mixed_or_supercritical"
    elif near_critical_frac > 0.2:
        regime = "near_critical"
    else:
        regime = "subcritical"

    # Bed slope estimation.
    # Station numbers in HEC-RAS are identifiers, not always physical distances.
    # Use _estimate_reach_length for a reliable distance, then compute slope.
    stations = np.asarray(result_summary.stations_m, dtype=float)
    n_xs = result_summary.n_cross_sections
    if len(bed) > 1:
        total_drop = abs(float(bed[0]) - float(bed[-1]))
        # First estimate length from stations
        station_range = abs(float(stations[0]) - float(stations[-1])) if len(stations) > 1 else 0
        # Use heuristic length if station range is suspiciously small
        if station_range > 10.0 and n_xs <= 50:
            total_distance = station_range
        elif total_drop > 0.01:
            # Estimate from typical open-channel slope (0.001-0.01)
            total_distance = total_drop / 0.005  # assume moderate slope
            total_distance = max(total_distance, n_xs * 50.0)  # min 50m per xs
        else:
            total_distance = max(n_xs * 100.0, 100.0)
        avg_slope = total_drop / max(total_distance, 1.0)
        avg_slope = np.clip(avg_slope, 1e-6, 0.5)  # cap at 50% slope
    else:
        avg_slope = 0.001

    # Manning's n — use HEC-RAS geometry value or estimate from energy slope
    manning_values = result_summary.manning_n_values
    if manning_values and len(manning_values) > 0:
        avg_manning = float(np.nanmean(manning_values))
    else:
        # Estimate from Manning equation: n = R^(2/3) * S_f^(1/2) / V
        P = width + 2 * depth
        R = area / np.maximum(P, 1e-6)
        # Use bed slope as proxy for friction slope in uniform flow
        n_est = R**(2.0/3.0) * avg_slope**0.5 / np.maximum(velocity, 1e-6)
        n_est = np.clip(n_est, 0.005, 0.15)
        avg_manning = float(np.nanmedian(n_est))

    # Backwater curve type identification (HEC-RAS standard step method logic)
    # Compare actual depth to normal depth to classify M1/M2/S1/S2/etc.
    Q_repr = float(np.nanmean(np.abs(flow)))
    B_repr = float(np.nanmean(width))

    # Normal depth estimate (Manning uniform flow)
    try:
        from utils.canal_utils import compute_steady_uniform_flow
        y_n = compute_steady_uniform_flow(Q=Q_repr, B=B_repr, S0=avg_slope, n=avg_manning)
    except Exception:
        y_n = (Q_repr * avg_manning / (B_repr * avg_slope**0.5))**0.6

    # Critical depth (rectangular approximation)
    y_c = (Q_repr**2 / (g * B_repr**2))**(1.0/3.0)

    avg_depth = float(np.nanmean(depth))

    if avg_slope > 0:
        if y_n > y_c:
            # Mild slope
            if avg_depth > y_n:
                curve_type = "M1"
            elif avg_depth > y_c:
                curve_type = "M2"
            else:
                curve_type = "M3"
        else:
            # Steep slope
            if avg_depth > y_c:
                curve_type = "S1"
            elif avg_depth > y_n:
                curve_type = "S2"
            else:
                curve_type = "S3"
    else:
        curve_type = "unknown"

    # Safety override: when Froude is clearly subcritical, force mild-slope
    # classification to prevent solver divergence from incorrect S-type assignment.
    if froude_mean < 0.5 and regime == "subcritical" and curve_type.startswith("S"):
        curve_type = "M1"  # Conservative: treat as downstream-controlled backwater

    # Solver recommendation based on diagnosis
    # S1 is steep-slope supercritical: shooting integration travels upstream,
    # which diverges when the characteristic direction is downstream.
    # S1/S2/S3 must use Godunov (shock-capturing, correct characteristic direction).
    if regime == "subcritical" and result_summary.mode == "steady" and curve_type in ("M1", "M2"):
        solver_rec = "steady"
        solver_reason = (
            f"亚临界稳态回水（{curve_type}型），适合 SteadyProfileSolver "
            f"的标准步长法（Standard Step Method），与 HEC-RAS 原理一致。"
        )
    elif curve_type in ("S1", "S2", "S3"):
        solver_rec = "godunov"
        solver_reason = (
            f"陡坡超临界曲线（{curve_type}型），特征线方向向下游，"
            f"shooting 法会从错误方向积分而发散，必须使用 Godunov FVM 求解器。"
        )
    elif regime == "subcritical" and result_summary.mode == "steady":
        solver_rec = "hydrostatic"
        solver_reason = (
            f"稳态但曲线类型为 {curve_type}，用 HydrostaticCanalSolver "
            f"的时间推进法趋近稳态更稳健。"
        )
    elif regime == "near_critical":
        solver_rec = "godunov"
        solver_reason = (
            "近临界流/混合流态，需要 Godunov FVM 求解器处理跨临界过渡，"
            "HEC-RAS 在此类问题上也使用类似的有限体积方法（LPI）。"
        )
    elif regime == "mixed_or_supercritical":
        solver_rec = "godunov"
        solver_reason = (
            "存在超临界区段，必须使用具有激波捕捉能力的 Godunov FVM 求解器。"
        )
    else:
        solver_rec = "hydrostatic"
        solver_reason = "默认使用 HydrostaticCanalSolver 时间推进法。"

    # Recommended numerical parameters
    n_xs = result_summary.n_cross_sections
    recommended_params = {
        "solver_type": solver_rec,
        "manning_n": round(avg_manning, 4),
        "slope": round(avg_slope, 6),
        "width": round(B_repr, 2),
        "Q_upstream": round(Q_repr, 3),
        "h_downstream": round(float(depth[-1]), 4),
        "length": round(_estimate_reach_length(stations, bed, avg_slope, n_xs), 1),
        "nx": max(n_xs * 2, 101),  # at least 2x HEC-RAS resolution
    }
    if solver_rec == "godunov":
        recommended_params.update({
            "cfl": 0.5,
            "order": 2,
            "riemann_solver": "hll",
            "n_cells": max(n_xs * 2, 200),
        })
    elif solver_rec == "steady":
        recommended_params["method"] = "shooting"

    # 传递 HEC-RAS 真实逐断面几何，供 HydroClaudeSimulator._build_cross_section 使用。
    # 优先使用 multi_station 模式：包含逐断面 bed 高程、宽度、Manning n，
    # 使 SteadyProfileSolver 可以用绝对水位 W 迭代，与 HEC-RAS 完全一致。
    if result_summary.bed_elevation_m and result_summary.stations_m:
        stations_m_list = list(result_summary.stations_m)
        bed_elevation_list = list(result_summary.bed_elevation_m)
        width_list = (
            list(result_summary.channel_width_m)
            if result_summary.channel_width_m and len(result_summary.channel_width_m) == len(stations_m_list)
            else [round(B_repr, 2)] * len(stations_m_list)
        )
        manning_list = (
            list(result_summary.manning_n_values)
            if result_summary.manning_n_values and len(result_summary.manning_n_values) == len(stations_m_list)
            else [round(avg_manning, 4)] * len(stations_m_list)
        )
        recommended_params["cross_section_data"] = {
            "type": "multi_station",
            "n_stations": len(stations_m_list),
            "stations": stations_m_list,
            "bed_elevations": bed_elevation_list,
            "channel_widths": width_list,
            "manning_ns": manning_list,
        }
    elif result_summary.channel_width_m:
        recommended_params["cross_section_data"] = {
            "type": "rectangular",
            "channel_width": round(B_repr, 2),
        }

    return {
        "regime": regime,
        "curve_type": curve_type,
        "froude_mean": round(froude_mean, 4),
        "froude_max": round(froude_max, 4),
        "froude_min": round(froude_min, 4),
        "subcritical_fraction": round(subcritical_frac, 3),
        "avg_slope": round(avg_slope, 6),
        "avg_manning_n": round(avg_manning, 4),
        "avg_depth_m": round(avg_depth, 4),
        "normal_depth_m": round(float(y_n), 4),
        "critical_depth_m": round(float(y_c), 4),
        "representative_Q_m3s": round(Q_repr, 3),
        "representative_width_m": round(B_repr, 2),
        "has_structures": result_summary.has_structures,
        "solver_recommendation": solver_rec,
        "solver_reason": solver_reason,
        "recommended_params": recommended_params,
    }
