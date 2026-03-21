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
    unit_system_source: str  # 单位制来源说明
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
    manning_n_ch_values: list[float] | None  # per xs, channel 糙率
    channel_width_m: list[float] | None  # per xs, if available
    has_structures: bool = False  # True when HDF contains bridges/culverts/weirs/gates
    # Per-XS station-elevation profiles for NaturalSection construction
    xs_profiles: list[dict] | None = None  # [{stations: [...], elevations: [...]}, ...]
    # HEC-RAS reach lengths between XS pairs (channel direction)
    reach_lengths_m: list[float] | None = None  # len = n_xs
    reach_lengths_lob_m: list[float] | None = None
    reach_lengths_rob_m: list[float] | None = None
    # Per-XS bank stations and loss coefficients
    left_bank_m: list[float] | None = None
    right_bank_m: list[float] | None = None
    contraction_coefs: list[float] | None = None
    expansion_coefs: list[float] | None = None
    # Per-XS three-zone Manning n (HEC-RAS LOB / Channel / ROB)
    manning_n_lob_values: list[float] | None = None
    manning_n_rob_values: list[float] | None = None
    # Bridge parameters extracted from HEC-RAS HDF Geometry/Structures
    bridges: list[dict] | None = None  # list of bridge parameter dicts
    # 参数完整性报告
    parameter_completeness: dict[str, bool] | None = None

    def to_dict(self) -> dict[str, Any]:
        return {k: v for k, v in self.__dict__.items()}




def _detect_unit_system_from_hdf(hdf: h5py.File) -> tuple[str, str]:
    """从 HDF 根属性读取单位制，返回 (unit_system, source_description)."""
    attr_name = "Units System"
    if attr_name not in hdf.attrs:
        return "english", "hdf root attr missing"

    raw = hdf.attrs[attr_name]
    if isinstance(raw, np.ndarray):
        raw = raw[0] if raw.size > 0 else b""
    text = _decode_bytes(raw)
    lower = text.lower()

    if "si" in lower:
        return "si", f'hdf root attr "{attr_name}"={text}'
    if "us" in lower or "customary" in lower or "english" in lower:
        return "english", f'hdf root attr "{attr_name}"={text}'

    return "english", f'hdf root attr "{attr_name}" unrecognized: {text} (fallback english)'


def generate_parameter_completeness_report(result_summary: HECRASResultSummary) -> dict[str, bool]:
    """生成关键参数完整性报告"""
    n_xs = result_summary.n_cross_sections

    def _ok_list(v: list[float] | None, exact_len: int | None = None) -> bool:
        if v is None:
            return False
        if exact_len is not None:
            return len(v) == exact_len
        return len(v) > 0

    report = {
        "unit_system_detected": result_summary.unit_system in ("si", "english"),
        "unit_system_source_present": bool(result_summary.unit_system_source),
        "water_surface_present": bool(result_summary.water_surface_m and len(result_summary.water_surface_m) > 0),
        "flow_present": bool(result_summary.flow_m3s and len(result_summary.flow_m3s) > 0),
        "energy_grade_present": bool(result_summary.energy_grade_m) if result_summary.mode == "steady" else True,
        "bed_elevation_present": _ok_list(result_summary.bed_elevation_m, n_xs),
        "channel_width_present": _ok_list(result_summary.channel_width_m, n_xs),
        "manning_ch_present": _ok_list(result_summary.manning_n_ch_values, n_xs),
        "manning_lob_present": _ok_list(result_summary.manning_n_lob_values, n_xs),
        "manning_rob_present": _ok_list(result_summary.manning_n_rob_values, n_xs),
        "reach_lengths_channel_present": _ok_list(result_summary.reach_lengths_m, n_xs),
        "reach_lengths_lob_present": _ok_list(result_summary.reach_lengths_lob_m, n_xs),
        "reach_lengths_rob_present": _ok_list(result_summary.reach_lengths_rob_m, n_xs),
        "bank_stations_present": _ok_list(result_summary.left_bank_m, n_xs) and _ok_list(result_summary.right_bank_m, n_xs),
        "xs_profiles_present": bool(result_summary.xs_profiles),
    }
    return report




def _detect_unit_system_from_hdf(hdf: h5py.File) -> tuple[str, str]:
    """从 HDF 根属性读取单位制，返回 (unit_system, source_description)."""
    attr_name = "Units System"
    if attr_name not in hdf.attrs:
        return "english", "hdf root attr missing"

    raw = hdf.attrs[attr_name]
    if isinstance(raw, np.ndarray):
        raw = raw[0] if raw.size > 0 else b""
    text = _decode_bytes(raw)
    lower = text.lower()

    if "si" in lower:
        return "si", f'hdf root attr "{attr_name}"={text}'
    if "us" in lower or "customary" in lower or "english" in lower:
        return "english", f'hdf root attr "{attr_name}"={text}'

    return "english", f'hdf root attr "{attr_name}" unrecognized: {text} (fallback english)'


def generate_parameter_completeness_report(result_summary: HECRASResultSummary) -> dict[str, bool]:
    """生成关键参数完整性报告"""
    n_xs = result_summary.n_cross_sections

    def _ok_list(v: list[float] | None, exact_len: int | None = None) -> bool:
        if v is None:
            return False
        if exact_len is not None:
            return len(v) == exact_len
        return len(v) > 0

    report = {
        "unit_system_detected": result_summary.unit_system in ("si", "english"),
        "unit_system_source_present": bool(result_summary.unit_system_source),
        "water_surface_present": bool(result_summary.water_surface_m and len(result_summary.water_surface_m) > 0),
        "flow_present": bool(result_summary.flow_m3s and len(result_summary.flow_m3s) > 0),
        "energy_grade_present": bool(result_summary.energy_grade_m) if result_summary.mode == "steady" else True,
        "bed_elevation_present": _ok_list(result_summary.bed_elevation_m, n_xs),
        "channel_width_present": _ok_list(result_summary.channel_width_m, n_xs),
        "manning_ch_present": _ok_list(result_summary.manning_n_ch_values, n_xs),
        "manning_lob_present": _ok_list(result_summary.manning_n_lob_values, n_xs),
        "manning_rob_present": _ok_list(result_summary.manning_n_rob_values, n_xs),
        "reach_lengths_channel_present": _ok_list(result_summary.reach_lengths_m, n_xs),
        "reach_lengths_lob_present": _ok_list(result_summary.reach_lengths_lob_m, n_xs),
        "reach_lengths_rob_present": _ok_list(result_summary.reach_lengths_rob_m, n_xs),
        "bank_stations_present": _ok_list(result_summary.left_bank_m, n_xs) and _ok_list(result_summary.right_bank_m, n_xs),
        "xs_profiles_present": bool(result_summary.xs_profiles),
    }
    return report




def _detect_unit_system_from_hdf(hdf: h5py.File) -> tuple[str, str]:
    """从 HDF 根属性读取单位制，返回 (unit_system, source_description)."""
    attr_name = "Units System"
    if attr_name not in hdf.attrs:
        return "english", "hdf root attr missing"

    raw = hdf.attrs[attr_name]
    if isinstance(raw, np.ndarray):
        raw = raw[0] if raw.size > 0 else b""
    text = _decode_bytes(raw)
    lower = text.lower()

    if "si" in lower:
        return "si", f'hdf root attr "{attr_name}"={text}'
    if "us" in lower or "customary" in lower or "english" in lower:
        return "english", f'hdf root attr "{attr_name}"={text}'

    return "english", f'hdf root attr "{attr_name}" unrecognized: {text} (fallback english)'


def generate_parameter_completeness_report(result_summary: HECRASResultSummary) -> dict[str, bool]:
    """生成关键参数完整性报告"""
    n_xs = result_summary.n_cross_sections

    def _ok_list(v: list[float] | None, exact_len: int | None = None) -> bool:
        if v is None:
            return False
        if exact_len is not None:
            return len(v) == exact_len
        return len(v) > 0

    report = {
        "unit_system_detected": result_summary.unit_system in ("si", "english"),
        "unit_system_source_present": bool(result_summary.unit_system_source),
        "water_surface_present": bool(result_summary.water_surface_m and len(result_summary.water_surface_m) > 0),
        "flow_present": bool(result_summary.flow_m3s and len(result_summary.flow_m3s) > 0),
        "energy_grade_present": bool(result_summary.energy_grade_m) if result_summary.mode == "steady" else True,
        "bed_elevation_present": _ok_list(result_summary.bed_elevation_m, n_xs),
        "channel_width_present": _ok_list(result_summary.channel_width_m, n_xs),
        "manning_ch_present": _ok_list(result_summary.manning_n_ch_values, n_xs),
        "manning_lob_present": _ok_list(result_summary.manning_n_lob_values, n_xs),
        "manning_rob_present": _ok_list(result_summary.manning_n_rob_values, n_xs),
        "reach_lengths_channel_present": _ok_list(result_summary.reach_lengths_m, n_xs),
        "reach_lengths_lob_present": _ok_list(result_summary.reach_lengths_lob_m, n_xs),
        "reach_lengths_rob_present": _ok_list(result_summary.reach_lengths_rob_m, n_xs),
        "bank_stations_present": _ok_list(result_summary.left_bank_m, n_xs) and _ok_list(result_summary.right_bank_m, n_xs),
        "xs_profiles_present": bool(result_summary.xs_profiles),
    }
    return report




def _detect_unit_system_from_hdf(hdf: h5py.File) -> tuple[str, str]:
    """从 HDF 根属性读取单位制，返回 (unit_system, source_description)."""
    attr_name = "Units System"
    if attr_name not in hdf.attrs:
        return "english", "hdf root attr missing"

    raw = hdf.attrs[attr_name]
    if isinstance(raw, np.ndarray):
        raw = raw[0] if raw.size > 0 else b""
    text = _decode_bytes(raw)
    lower = text.lower()

    if "si" in lower:
        return "si", f'hdf root attr "{attr_name}"={text}'
    if "us" in lower or "customary" in lower or "english" in lower:
        return "english", f'hdf root attr "{attr_name}"={text}'

    return "english", f'hdf root attr "{attr_name}" unrecognized: {text} (fallback english)'


def generate_parameter_completeness_report(result_summary: HECRASResultSummary) -> dict[str, bool]:
    """生成关键参数完整性报告"""
    n_xs = result_summary.n_cross_sections

    def _ok_list(v: list[float] | None, exact_len: int | None = None) -> bool:
        if v is None:
            return False
        if exact_len is not None:
            return len(v) == exact_len
        return len(v) > 0

    report = {
        "unit_system_detected": result_summary.unit_system in ("si", "english"),
        "unit_system_source_present": bool(result_summary.unit_system_source),
        "water_surface_present": bool(result_summary.water_surface_m and len(result_summary.water_surface_m) > 0),
        "flow_present": bool(result_summary.flow_m3s and len(result_summary.flow_m3s) > 0),
        "energy_grade_present": bool(result_summary.energy_grade_m) if result_summary.mode == "steady" else True,
        "bed_elevation_present": _ok_list(result_summary.bed_elevation_m, n_xs),
        "channel_width_present": _ok_list(result_summary.channel_width_m, n_xs),
        "manning_ch_present": _ok_list(result_summary.manning_n_ch_values, n_xs),
        "manning_lob_present": _ok_list(result_summary.manning_n_lob_values, n_xs),
        "manning_rob_present": _ok_list(result_summary.manning_n_rob_values, n_xs),
        "reach_lengths_channel_present": _ok_list(result_summary.reach_lengths_m, n_xs),
        "reach_lengths_lob_present": _ok_list(result_summary.reach_lengths_lob_m, n_xs),
        "reach_lengths_rob_present": _ok_list(result_summary.reach_lengths_rob_m, n_xs),
        "bank_stations_present": _ok_list(result_summary.left_bank_m, n_xs) and _ok_list(result_summary.right_bank_m, n_xs),
        "xs_profiles_present": bool(result_summary.xs_profiles),
    }
    return report


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

    with h5py.File(hdf_p, "r") as hdf:
        unit_system, unit_system_source = _detect_unit_system_from_hdf(hdf)
        if unit_system_source == "hdf root attr missing":
            unit_system = _detect_unit_system(prj_p)
            if prj_p and prj_p.exists():
                unit_system_source = f"project file: {prj_p}"
            else:
                unit_system_source = "default english (no hdf attr/project)"
        lf = _length_factor(unit_system)
        qf = _flow_factor(unit_system)
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

            xs_profiles = _try_read_xs_profiles(hdf, lf)

            xs_attrs = _try_read_xs_attributes(hdf, lf)

            bridges = _extract_bridge_params(hdf, lf) if has_structures else []

            manning_n_ch = xs_attrs.get("manning_n_ch_values")
            
            summary = HECRASResultSummary(
                mode="steady",
                unit_system=unit_system,
                unit_system_source=unit_system_source,
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
                manning_n_ch_values=manning_n_ch if manning_n_ch else manning_n,
                channel_width_m=width,
                has_structures=has_structures,
                xs_profiles=xs_profiles,
                reach_lengths_m=xs_attrs.get("reach_lengths_m"),
                reach_lengths_lob_m=xs_attrs.get("reach_lengths_lob_m"),
                reach_lengths_rob_m=xs_attrs.get("reach_lengths_rob_m"),
                left_bank_m=xs_attrs.get("left_bank_m"),
                right_bank_m=xs_attrs.get("right_bank_m"),
                contraction_coefs=xs_attrs.get("contraction_coefs"),
                expansion_coefs=xs_attrs.get("expansion_coefs"),
                manning_n_lob_values=xs_attrs.get("manning_n_lob_values"),
                manning_n_rob_values=xs_attrs.get("manning_n_rob_values"),
                bridges=bridges if bridges else None,
                parameter_completeness=None,
            )
            summary.parameter_completeness = generate_parameter_completeness_report(summary)
            return summary

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
        xs_profiles = _try_read_xs_profiles(hdf, lf)
        xs_attrs = _try_read_xs_attributes(hdf, lf)

        manning_n_ch = xs_attrs.get("manning_n_ch_values")
        
        summary = HECRASResultSummary(
            mode="unsteady",
            unit_system=unit_system,
            unit_system_source=unit_system_source,
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
            manning_n_ch_values=manning_n_ch if manning_n_ch else manning_n,
            channel_width_m=width,
            has_structures=has_structures,
            xs_profiles=xs_profiles,
            reach_lengths_m=xs_attrs.get("reach_lengths_m"),
            reach_lengths_lob_m=xs_attrs.get("reach_lengths_lob_m"),
            reach_lengths_rob_m=xs_attrs.get("reach_lengths_rob_m"),
            left_bank_m=xs_attrs.get("left_bank_m"),
            right_bank_m=xs_attrs.get("right_bank_m"),
            contraction_coefs=xs_attrs.get("contraction_coefs"),
            expansion_coefs=xs_attrs.get("expansion_coefs"),
            manning_n_lob_values=xs_attrs.get("manning_n_lob_values"),
            manning_n_rob_values=xs_attrs.get("manning_n_rob_values"),
            parameter_completeness=None,
        )
        summary.parameter_completeness = generate_parameter_completeness_report(summary)
        return summary


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


def _try_read_xs_attributes(hdf: h5py.File, lf: float) -> dict[str, list]:
    """Read per-XS attributes from Geometry/Cross Sections/Attributes.

    Returns dict with reach_lengths_m, reach_lengths_lob_m, reach_lengths_rob_m,
    left_bank_m, right_bank_m, contraction_coefs, expansion_coefs,
    manning_n_lob_values, manning_n_ch_values, manning_n_rob_values.
    """
    import logging

    logger = logging.getLogger(__name__)
    result: dict[str, list] = {}

    attr_path = "Geometry/Cross Sections/Attributes"
    if attr_path in hdf:
        attrs = hdf[attr_path][:]
        names = set(attrs.dtype.names or [])

        len_channel: list[float] | None = None
        if "Len Channel" in names:
            len_channel = (np.asarray(attrs["Len Channel"], dtype=float) * lf).tolist()
            result["reach_lengths_m"] = len_channel

        if "Len Left" in names:
            result["reach_lengths_lob_m"] = (np.asarray(attrs["Len Left"], dtype=float) * lf).tolist()
        elif len_channel is not None:
            result["reach_lengths_lob_m"] = list(len_channel)
            logger.info("Len Left missing; fallback to Len Channel for LOB reach lengths.")
        else:
            logger.warning("Len Left and Len Channel both missing in Geometry/Cross Sections/Attributes.")

        if "Len Right" in names:
            result["reach_lengths_rob_m"] = (np.asarray(attrs["Len Right"], dtype=float) * lf).tolist()
        elif len_channel is not None:
            result["reach_lengths_rob_m"] = list(len_channel)
            logger.info("Len Right missing; fallback to Len Channel for ROB reach lengths.")
        else:
            logger.warning("Len Right and Len Channel both missing in Geometry/Cross Sections/Attributes.")

        if "Left Bank" in names:
            result["left_bank_m"] = (np.asarray(attrs["Left Bank"], dtype=float) * lf).tolist()
        if "Right Bank" in names:
            result["right_bank_m"] = (np.asarray(attrs["Right Bank"], dtype=float) * lf).tolist()
        if "Contr" in names:
            result["contraction_coefs"] = np.asarray(attrs["Contr"], dtype=float).tolist()
        if "Expan" in names:
            result["expansion_coefs"] = np.asarray(attrs["Expan"], dtype=float).tolist()

    # Read per-XS LOB / CH / ROB Manning n from Manning n Info/Values dataset
    mn_info_path = "Geometry/Cross Sections/Manning's n Info"
    mn_vals_path = "Geometry/Cross Sections/Manning's n Values"
    if mn_info_path in hdf and mn_vals_path in hdf:
        mn_info = hdf[mn_info_path][:]
        mn_vals = np.asarray(hdf[mn_vals_path][:], dtype=float)

        n_lob_list: list[float] = []
        n_ch_list: list[float] = []
        n_rob_list: list[float] = []

        for row in mn_info:
            start = int(row[0])
            count = int(row[1])

            if count >= 1 and start + count <= len(mn_vals):
                lob_idx = start
                rob_idx = start + count - 1
                ch_idx = start + (count // 2)  # 中间列（中间条目）作为 Channel 糙率

                n_lob_list.append(float(mn_vals[lob_idx, 1]))
                n_ch_list.append(float(mn_vals[ch_idx, 1]))
                n_rob_list.append(float(mn_vals[rob_idx, 1]))
            else:
                n_lob_list.append(0.0)
                n_ch_list.append(0.0)
                n_rob_list.append(0.0)

        if n_lob_list:
            result["manning_n_lob_values"] = n_lob_list
            result["manning_n_ch_values"] = n_ch_list
            result["manning_n_rob_values"] = n_rob_list

    return result


def _try_read_xs_profiles(hdf: h5py.File, lf: float) -> list[dict] | None:
    """Read per-cross-section station-elevation profiles from HDF geometry.

    Returns list of {stations: [...], elevations: [...]} dicts, one per XS.
    These can be used to construct NaturalSection objects for each station.
    """
    info_path = "Geometry/Cross Sections/Station Elevation Info"
    vals_path = "Geometry/Cross Sections/Station Elevation Values"
    if info_path not in hdf or vals_path not in hdf:
        return None

    info = hdf[info_path][:]
    vals = np.asarray(hdf[vals_path][:], dtype=float)
    profiles: list[dict] = []
    for row in info:
        start = int(row[0])
        count = int(row[1])
        if count > 2 and start + count <= len(vals):
            xs_stations = (vals[start:start + count, 0] * lf).tolist()
            xs_elevations = (vals[start:start + count, 1] * lf).tolist()
            profiles.append({"stations": xs_stations, "elevations": xs_elevations})
        else:
            profiles.append(None)
    return profiles if any(p is not None for p in profiles) else None


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



def _extract_bridge_params(hdf: h5py.File, lf: float) -> list[dict]:
    """Extract bridge parameters from HEC-RAS HDF Geometry/Structures.

    Returns a list of bridge parameter dicts with keys:
        us_rs, ds_rs, deck_elevation_m, low_chord_elevation_m,
        opening_height_m, bridge_length_m, n_piers,
        total_pier_width_m, pier_loss_coef,
        contraction_coef, expansion_coef.
    """
    bridges: list[dict] = []

    # HEC-RAS stores structure data under Geometry/Structures/Attributes
    attr_path = "Geometry/Structures/Attributes"
    if attr_path not in hdf:
        return bridges

    attrs = hdf[attr_path][:]

    profile_data = (
        hdf["Geometry/Structures/Profile Data"][:]
        if "Geometry/Structures/Profile Data" in hdf
        else None
    )
    table_info = (
        hdf["Geometry/Structures/Table Info"][:]
        if "Geometry/Structures/Table Info" in hdf
        else None
    )
    pier_attrs = (
        hdf["Geometry/Structures/Pier Attributes"][:]
        if "Geometry/Structures/Pier Attributes" in hdf
        else None
    )
    pier_data = (
        hdf["Geometry/Structures/Pier Data"][:]
        if "Geometry/Structures/Pier Data" in hdf
        else None
    )

    for idx, sa in enumerate(attrs):
        # Filter to Bridge type only
        stype_raw = sa["Type"] if "Type" in sa.dtype.names else b""
        stype = _decode_bytes(stype_raw).strip()
        if stype.lower() != "bridge":
            continue

        us_rs = _decode_bytes(sa["US RS"]) if "US RS" in sa.dtype.names else ""
        ds_rs = _decode_bytes(sa["DS RS"]) if "DS RS" in sa.dtype.names else ""

        # Deck and low-chord elevation from profile data
        deck_elev = 0.0
        low_chord_elev = 0.0
        bridge_opening_stations: list[float] = []
        bridge_opening_elevations: list[float] = []
        if profile_data is not None and table_info is not None and idx < len(table_info):
            ti = table_info[idx]
            ti_names = ti.dtype.names if hasattr(ti, "dtype") else []

            # US BR Lid Profile = 桥面板轮廓（包含桥面板+桥底完整 station-elevation 数据）
            lid_idx_name = next(
                (n for n in (ti_names or []) if "lid" in n.lower() and "index" in n.lower()), None
            )
            lid_cnt_name = next(
                (n for n in (ti_names or []) if "lid" in n.lower() and "count" in n.lower()), None
            )
            if lid_idx_name and lid_cnt_name:
                lid_start = int(ti[lid_idx_name])
                lid_count = int(ti[lid_cnt_name])
                if lid_count > 0 and lid_start + lid_count <= len(profile_data):
                    lid_profile = profile_data[lid_start:lid_start + lid_count]
                    deck_elev = float(np.max(lid_profile[:, 1])) * lf
                    # 保存 opening 轮廓供 solver 构造 NaturalSection 使用
                    bridge_opening_stations = (lid_profile[:, 0] * lf).tolist()
                    bridge_opening_elevations = (lid_profile[:, 1] * lf).tolist()

            # US BR Profile = 桥底（低弦）
            br_idx_name = next(
                (n for n in (ti_names or []) if "br profile" in n.lower() and "index" in n.lower()), None
            )
            br_cnt_name = next(
                (n for n in (ti_names or []) if "br profile" in n.lower() and "count" in n.lower()), None
            )
            if br_idx_name and br_cnt_name:
                br_start = int(ti[br_idx_name])
                br_count = int(ti[br_cnt_name])
                if br_count > 0 and br_start + br_count <= len(profile_data):
                    pass  # will read below
                elif lid_idx_name and lid_cnt_name:
                    # Fallback: use Lid Profile min elevation as low chord
                    _lid_s = int(ti[lid_idx_name])
                    _lid_c = int(ti[lid_cnt_name])
                    if _lid_c > 0 and _lid_s + _lid_c <= len(profile_data):
                        low_chord_elev = float(np.min(profile_data[_lid_s:_lid_s + _lid_c, 1])) * lf
                        br_count = 0  # skip next block
                if br_count > 0 and br_start + br_count <= len(profile_data):
                    low_chord_elev = float(np.min(profile_data[br_start:br_start + br_count, 1])) * lf

        # Pier parameters
        n_piers = 0
        total_pier_width_m = 0.0
        if pier_attrs is not None and pier_data is not None:
            pier_struct_field = next(
                (n for n in pier_attrs.dtype.names if "struct" in n.lower()),
                None,
            )
            for pa in pier_attrs:
                # Only count piers belonging to this structure (if field available)
                if pier_struct_field is not None:
                    struct_idx = int(pa[pier_struct_field])
                    if struct_idx != idx:
                        continue

                ps_field = next(
                    (n for n in pa.dtype.names if "index" in n.lower()), None
                )
                pc_field = next(
                    (n for n in pa.dtype.names if "count" in n.lower()), None
                )
                if ps_field and pc_field:
                    ps = int(pa[ps_field])
                    pc = int(pa[pc_field])
                    if pc >= 1 and ps + pc <= len(pier_data):
                        # Pier Data column 0 = pier half-width (station coord)
                        # The pier width is the max station value (represents half-width from center)
                        pier_stations = pier_data[ps:ps + pc, 0]
                        pier_width = float(np.max(pier_stations)) * 2.0 * lf  # full width = 2 × half-width
                        total_pier_width_m += pier_width
                        n_piers += 1

        bridge_length_m = (
            float(sa["Upstream Distance"]) * lf
            if "Upstream Distance" in sa.dtype.names
            else 0.0
        )

        pier_loss_coef = (
            float(sa["BR Pier K"])
            if "BR Pier K" in sa.dtype.names
            else 0.0
        )
        contraction_coef = (
            float(sa["BR Contraction"])
            if "BR Contraction" in sa.dtype.names
            else 0.3
        )
        expansion_coef = (
            float(sa["BR Expansion"])
            if "BR Expansion" in sa.dtype.names
            else 0.5
        )

        opening_height = (
            deck_elev - low_chord_elev
            if deck_elev > low_chord_elev
            else 5.0  # fallback 5 m
        )

        bridge_dict: dict = {
            "us_rs": us_rs,
            "ds_rs": ds_rs,
            "deck_elevation_m": deck_elev,
            "low_chord_elevation_m": low_chord_elev,
            "opening_height_m": opening_height,
            "bridge_length_m": bridge_length_m,
            "n_piers": n_piers,
            "total_pier_width_m": total_pier_width_m,
            "pier_loss_coef": pier_loss_coef,
            "contraction_coef": contraction_coef,
            "expansion_coef": expansion_coef,
        }
        # 桥面板 opening 轮廓（用于 solver 构造 NaturalSection 计算有效过水面积）
        if len(bridge_opening_stations) > 2:
            bridge_dict["bridge_opening_stations"] = bridge_opening_stations
            bridge_dict["bridge_opening_elevations"] = bridge_opening_elevations
        bridges.append(bridge_dict)

    return bridges

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
        "Geometry/Structures/Pier Attributes",
        "Geometry/Structures/Pier Data",
        "Geometry/Structures/Bridge Coefficient Attributes",
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

    # Bed slope and reach length estimation.
    # Priority 1: Use actual HEC-RAS Reach Lengths from Geometry/Cross Sections/Attributes
    # Priority 2: Use station range (if physically meaningful)
    # Priority 3: Heuristic estimation
    stations = np.asarray(result_summary.stations_m, dtype=float)
    n_xs = result_summary.n_cross_sections
    reach_lengths = result_summary.reach_lengths_m
    if reach_lengths and len(reach_lengths) > 0:
        total_distance = float(np.sum(np.asarray(reach_lengths, dtype=float)))
        if total_distance < 1.0:
            total_distance = max(n_xs * 100.0, 100.0)
    else:
        total_distance = _estimate_reach_length(stations, bed, 0.001, n_xs)

    if len(bed) > 1:
        total_drop = abs(float(bed[0]) - float(bed[-1]))
        avg_slope = total_drop / max(total_distance, 1.0)
        avg_slope = np.clip(avg_slope, 1e-6, 0.5)
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
        # 构造 bank_stations 列表：[(left_bank_m, right_bank_m), ...] per XS
        left_banks = result_summary.left_bank_m
        right_banks = result_summary.right_bank_m
        if left_banks and right_banks and len(left_banks) == len(stations_m_list):
            bank_stations_list = list(zip(left_banks, right_banks))
        else:
            bank_stations_list = None

        recommended_params["cross_section_data"] = {
            "type": "multi_station",
            "n_stations": len(stations_m_list),
            "stations": stations_m_list,
            "bed_elevations": bed_elevation_list,
            "channel_widths": width_list,
            "manning_ns": manning_list,
            "xs_profiles": result_summary.xs_profiles,  # per-XS station-elevation for NaturalSection
            "reach_lengths": result_summary.reach_lengths_m,  # actual HEC-RAS reach lengths
            "contraction_coefs": result_summary.contraction_coefs,
            "expansion_coefs": result_summary.expansion_coefs,
            # 三区 Manning n（HEC-RAS LOB/Channel/ROB 分区）
            "manning_n_lob": result_summary.manning_n_lob_values,
            "manning_n_rob": result_summary.manning_n_rob_values,
            "bank_stations": bank_stations_list,
            "bridges": result_summary.bridges,
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
