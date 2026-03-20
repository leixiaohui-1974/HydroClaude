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
