#!/usr/bin/env python3
"""Controlled A/B diagnosis for Example 17 preprocess sign/master integration."""

from __future__ import annotations

import argparse
import copy
import json
import subprocess
import sys
import tempfile
import time
from datetime import datetime
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
CASE_JSON = ROOT / "reports" / "hecras_unsteady_reference" / "Example17_Unsteady_unsteady_ref.json"
REPORT_DIR = ROOT / "reports" / "hecras_unsteady_diagnostics"
MONITORED_JUNCTIONS = ["Lower", "Upper", "Right"]
WINDOWS = [
    ("300s", 300.0),
    ("7200s", 7200.0),
    ("full", None),
]
CONFIGS = [
    {
        "name": "friction_stub_only",
        "use_preprocess_endpoint_signs": False,
        "use_preprocess_master_hints": False,
    },
    {
        "name": "friction_stub_plus_signs",
        "use_preprocess_endpoint_signs": True,
        "use_preprocess_master_hints": False,
    },
    {
        "name": "friction_stub_plus_signs_master",
        "use_preprocess_endpoint_signs": True,
        "use_preprocess_master_hints": True,
    },
]
COMPONENT_KEYS = [
    "continuity_row_time_s",
    "master_row_replacement_time_s",
    "iter_clip_time_s",
    "step_clip_time_s",
]


def _load_case_json() -> dict:
    with CASE_JSON.open(encoding="utf-8") as f:
        return json.load(f)


def _mask_indices(times: list[float], t_end_s: float | None) -> list[int]:
    if t_end_s is None:
        return list(range(len(times)))
    keep = [idx for idx, value in enumerate(times) if float(value) <= float(t_end_s) + 1e-9]
    if len(keep) < 2:
        raise ValueError(f"time window {t_end_s} s leaves fewer than 2 output points")
    return keep


def _trim_boundary_condition_arrays(bc: dict, t_end_s: float | None) -> None:
    if t_end_s is None or "times_s" not in bc:
        return
    times = list(bc["times_s"])
    keep = [idx for idx, value in enumerate(times) if float(value) <= float(t_end_s) + 1e-9]
    if not keep:
        keep = [0]
    if keep[-1] < len(times) - 1:
        keep.append(keep[-1] + 1)
    keep = sorted(set(keep))
    bc["times_s"] = [times[idx] for idx in keep]
    for key, value in list(bc.items()):
        if key == "times_s":
            continue
        if isinstance(value, list) and len(value) == len(times):
            bc[key] = [value[idx] for idx in keep]


def _build_windowed_case(data: dict, t_end_s: float | None) -> dict:
    if t_end_s is None:
        return copy.deepcopy(data)
    out = copy.deepcopy(data)
    keep = _mask_indices(list(out["times_s"]), t_end_s)
    out["times_s"] = [out["times_s"][idx] for idx in keep]
    if "water_surface_m" in out:
        out["water_surface_m"] = [out["water_surface_m"][idx] for idx in keep]
    if "flow_m3s" in out:
        out["flow_m3s"] = [out["flow_m3s"][idx] for idx in keep]
    for bc in out.get("boundary_conditions", []):
        _trim_boundary_condition_arrays(bc, t_end_s)
    return out


def _aggregate_timing(records: list[dict]) -> dict:
    by_junction: dict[str, dict] = {}
    by_component = {key: 0.0 for key in COMPONENT_KEYS}
    step_map: dict[tuple[str, float], dict] = {}
    for record in records or []:
        jname = str(record.get("junction_name", ""))
        if not jname:
            continue
        item = by_junction.setdefault(
            jname,
            {
                "junction_name": jname,
                "total_tracked_time_s": 0.0,
                "continuity_row_time_s": 0.0,
                "master_row_replacement_time_s": 0.0,
                "iter_clip_time_s": 0.0,
                "step_clip_time_s": 0.0,
                "max_step_residual": 0.0,
            },
        )
        for key in COMPONENT_KEYS:
            value = float(record.get(key, 0.0) or 0.0)
            item[key] += value
            by_component[key] += value
        item["total_tracked_time_s"] += float(record.get("total_tracked_time_s", 0.0) or 0.0)
        item["max_step_residual"] = max(
            item["max_step_residual"],
            float(record.get("step_final_residual", 0.0) or 0.0),
        )
        key = (jname, float(record.get("t_new_s", 0.0) or 0.0))
        step_map[key] = {
            "junction_name": jname,
            "t_new_s": float(record.get("t_new_s", 0.0) or 0.0),
            "total_tracked_time_s": float(record.get("total_tracked_time_s", 0.0) or 0.0),
            "continuity_row_time_s": float(record.get("continuity_row_time_s", 0.0) or 0.0),
            "master_row_replacement_time_s": float(record.get("master_row_replacement_time_s", 0.0) or 0.0),
            "iter_clip_time_s": float(record.get("iter_clip_time_s", 0.0) or 0.0),
            "step_clip_time_s": float(record.get("step_clip_time_s", 0.0) or 0.0),
            "has_explicit_state": bool(record.get("has_explicit_state", False)),
            "master_reach": record.get("master_reach"),
            "master_endpoint": record.get("master_endpoint"),
        }
    slowest_steps = sorted(
        step_map.values(),
        key=lambda item: item["total_tracked_time_s"],
        reverse=True,
    )[:10]
    return {
        "by_junction": by_junction,
        "by_component": by_component,
        "slowest_steps": slowest_steps,
    }


def _diff_step_onset(base_records: list[dict], other_records: list[dict]) -> dict | None:
    base_map = {
        (str(item.get("junction_name", "")), float(item.get("t_new_s", 0.0) or 0.0)): float(item.get("total_tracked_time_s", 0.0) or 0.0)
        for item in base_records or []
    }
    deltas = []
    for item in other_records or []:
        key = (str(item.get("junction_name", "")), float(item.get("t_new_s", 0.0) or 0.0))
        delta = float(item.get("total_tracked_time_s", 0.0) or 0.0) - base_map.get(key, 0.0)
        if delta > 0.0:
            deltas.append(
                {
                    "junction_name": key[0],
                    "t_new_s": key[1],
                    "delta_total_tracked_time_s": delta,
                    "has_explicit_state": bool(item.get("has_explicit_state", False)),
                    "master_reach": item.get("master_reach"),
                    "master_endpoint": item.get("master_endpoint"),
                }
            )
    if not deltas:
        return None
    max_delta = max(item["delta_total_tracked_time_s"] for item in deltas)
    threshold = max(1e-6, 0.1 * max_delta)
    onset_candidates = [
        item for item in deltas
        if item["delta_total_tracked_time_s"] >= threshold
    ]
    onset_candidates.sort(key=lambda item: (item["t_new_s"], -item["delta_total_tracked_time_s"]))
    return onset_candidates[0] if onset_candidates else None


def _pairwise_comparison(base_run: dict, other_run: dict) -> dict:
    base_result = base_run.get("result", {})
    other_result = other_run.get("result", {})
    base_timing = base_result.get("timing_summary", {})
    other_timing = other_result.get("timing_summary", {})
    base_junction = base_timing.get("by_junction", {})
    other_junction = other_timing.get("by_junction", {})
    all_junctions = sorted(set(base_junction) | set(other_junction))
    junction_deltas = []
    for jname in all_junctions:
        delta_total = float(other_junction.get(jname, {}).get("total_tracked_time_s", 0.0)) - float(
            base_junction.get(jname, {}).get("total_tracked_time_s", 0.0)
        )
        junction_deltas.append(
            {
                "junction_name": jname,
                "delta_total_tracked_time_s": delta_total,
                "delta_continuity_row_time_s": float(other_junction.get(jname, {}).get("continuity_row_time_s", 0.0))
                - float(base_junction.get(jname, {}).get("continuity_row_time_s", 0.0)),
                "delta_master_row_replacement_time_s": float(other_junction.get(jname, {}).get("master_row_replacement_time_s", 0.0))
                - float(base_junction.get(jname, {}).get("master_row_replacement_time_s", 0.0)),
                "delta_iter_clip_time_s": float(other_junction.get(jname, {}).get("iter_clip_time_s", 0.0))
                - float(base_junction.get(jname, {}).get("iter_clip_time_s", 0.0)),
                "delta_step_clip_time_s": float(other_junction.get(jname, {}).get("step_clip_time_s", 0.0))
                - float(base_junction.get(jname, {}).get("step_clip_time_s", 0.0)),
            }
        )
    junction_deltas.sort(key=lambda item: item["delta_total_tracked_time_s"], reverse=True)
    component_deltas = {}
    for key in COMPONENT_KEYS:
        component_deltas[key] = float(other_timing.get("by_component", {}).get(key, 0.0)) - float(
            base_timing.get("by_component", {}).get(key, 0.0)
        )
    dominant_component = None
    if component_deltas:
        dominant_component = max(component_deltas.items(), key=lambda item: item[1])[0]
    return {
        "base_config": base_run.get("config_name"),
        "other_config": other_run.get("config_name"),
        "window_label": base_run.get("window_label"),
        "delta_wall_elapsed_s": float(other_run.get("wall_elapsed_s", 0.0) or 0.0) - float(base_run.get("wall_elapsed_s", 0.0) or 0.0),
        "delta_solver_elapsed_s": float(other_result.get("elapsed_solver_s", 0.0) or 0.0) - float(
            base_result.get("elapsed_solver_s", 0.0) or 0.0
        ),
        "delta_step_nonconvergence_count": int(other_result.get("step_nonconvergence_count", 0) or 0)
        - int(base_result.get("step_nonconvergence_count", 0) or 0),
        "delta_max_step_residual": float(other_result.get("max_step_residual", 0.0) or 0.0) - float(
            base_result.get("max_step_residual", 0.0) or 0.0
        ),
        "junction_deltas": junction_deltas,
        "component_deltas": component_deltas,
        "dominant_component": dominant_component,
        "onset": _diff_step_onset(
            base_result.get("junction_timing_records", []),
            other_result.get("junction_timing_records", []),
        ),
    }


def _summarize_result(result: dict) -> dict:
    solver_diag = dict(result.get("solver_diagnostics") or {})
    timing_records = list(solver_diag.get("junction_timing_records", []) or [])
    return {
        "mae": result.get("mae"),
        "mae_max": result.get("mae_max"),
        "ic_mae": result.get("ic_mae"),
        "verdict": result.get("verdict"),
        "elapsed_solver_s": result.get("elapsed"),
        "overall_converged": solver_diag.get("overall_converged"),
        "step_nonconvergence_count": solver_diag.get("step_nonconvergence_count"),
        "max_step_residual": solver_diag.get("max_step_residual"),
        "junction_state_names": solver_diag.get("junction_state_names", []),
        "junction_iter_clip_counts": solver_diag.get("junction_iter_clip_counts", {}),
        "junction_step_clip_counts": solver_diag.get("junction_step_clip_counts", {}),
        "preprocess_usage": solver_diag.get("preprocess_usage", {}),
        "junction_timing_records": timing_records,
        "timing_summary": _aggregate_timing(timing_records),
    }


def _run_child(args: argparse.Namespace) -> int:
    from scripts.run_all_unsteady_benchmark import run_network_case

    result = run_network_case(
        args.json_path,
        args.case_label,
        solver_kwargs={
            "use_preprocess_endpoint_signs": bool(args.use_signs),
            "use_preprocess_master_hints": bool(args.use_master),
            "junction_timing_names": list(MONITORED_JUNCTIONS),
        },
    )
    payload = {
        "config_name": args.config_name,
        "window_label": args.window_label,
        "t_end_s": args.t_end_s,
        "result": _summarize_result(result),
    }
    with Path(args.output_json).open("w", encoding="utf-8") as f:
        json.dump(payload, f, ensure_ascii=False, indent=2)
    return 0


def _report_path() -> Path:
    REPORT_DIR.mkdir(parents=True, exist_ok=True)
    stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    return REPORT_DIR / f"example17_preprocess_ab_{stamp}.json"


def _run_parent(args: argparse.Namespace) -> int:
    base_data = _load_case_json()
    report = {
        "case_json": str(CASE_JSON),
        "generated_at": datetime.now().isoformat(timespec="seconds"),
        "timeout_s": int(args.timeout_s),
        "monitored_junctions": list(MONITORED_JUNCTIONS),
        "runs": [],
        "comparisons": [],
    }
    with tempfile.TemporaryDirectory(prefix="example17_preprocess_ab_") as tmpdir_str:
        tmpdir = Path(tmpdir_str)
        for window_label, t_end_s in WINDOWS:
            for config in CONFIGS:
                window_data = _build_windowed_case(base_data, t_end_s)
                case_json_path = tmpdir / f"{window_label}_{config['name']}.json"
                with case_json_path.open("w", encoding="utf-8") as f:
                    json.dump(window_data, f, ensure_ascii=False, indent=2)
                output_json_path = tmpdir / f"{window_label}_{config['name']}_result.json"
                cmd = [
                    sys.executable,
                    str(Path(__file__).resolve()),
                    "--child",
                    "--json-path",
                    str(case_json_path),
                    "--case-label",
                    f"Example17_{window_label}_{config['name']}",
                    "--config-name",
                    config["name"],
                    "--window-label",
                    window_label,
                    "--output-json",
                    str(output_json_path),
                    "--use-signs",
                    "1" if config["use_preprocess_endpoint_signs"] else "0",
                    "--use-master",
                    "1" if config["use_preprocess_master_hints"] else "0",
                ]
                if t_end_s is not None:
                    cmd.extend(["--t-end-s", str(t_end_s)])
                print(
                    f"[run] window={window_label:>4} config={config['name']:<28} "
                    f"signs={int(config['use_preprocess_endpoint_signs'])} "
                    f"master={int(config['use_preprocess_master_hints'])}"
                )
                started = time.perf_counter()
                try:
                    proc = subprocess.run(
                        cmd,
                        cwd=str(ROOT),
                        capture_output=True,
                        text=True,
                        timeout=float(args.timeout_s),
                    )
                    wall_elapsed_s = time.perf_counter() - started
                except subprocess.TimeoutExpired as exc:
                    wall_elapsed_s = time.perf_counter() - started
                    report["runs"].append(
                        {
                            "config_name": config["name"],
                            "window_label": window_label,
                            "t_end_s": t_end_s,
                            "wall_elapsed_s": wall_elapsed_s,
                            "timed_out": True,
                            "result": {
                                "verdict": "TIMEOUT",
                                "overall_converged": False,
                                "mae": None,
                                "mae_max": None,
                                "elapsed_solver_s": None,
                                "step_nonconvergence_count": None,
                                "max_step_residual": None,
                                "junction_timing_records": [],
                                "timing_summary": {
                                    "by_junction": {},
                                    "by_component": {key: 0.0 for key in COMPONENT_KEYS},
                                    "slowest_steps": [],
                                },
                            },
                            "stdout_tail": (exc.stdout or "")[-4000:],
                            "stderr_tail": (exc.stderr or "")[-4000:],
                        }
                    )
                    print(f"  -> TIMEOUT at {wall_elapsed_s:.1f}s")
                    continue
                run_payload = {
                    "config_name": config["name"],
                    "window_label": window_label,
                    "t_end_s": t_end_s,
                    "wall_elapsed_s": wall_elapsed_s,
                    "timed_out": False,
                    "returncode": int(proc.returncode),
                    "stdout_tail": proc.stdout[-4000:],
                    "stderr_tail": proc.stderr[-4000:],
                }
                if proc.returncode != 0 or not output_json_path.exists():
                    run_payload["result"] = {
                        "verdict": "ERROR",
                        "overall_converged": False,
                        "mae": None,
                        "mae_max": None,
                        "elapsed_solver_s": None,
                        "step_nonconvergence_count": None,
                        "max_step_residual": None,
                        "junction_timing_records": [],
                        "timing_summary": {
                            "by_junction": {},
                            "by_component": {key: 0.0 for key in COMPONENT_KEYS},
                            "slowest_steps": [],
                        },
                    }
                    report["runs"].append(run_payload)
                    print(f"  -> ERROR rc={proc.returncode} at {wall_elapsed_s:.1f}s")
                    continue
                with output_json_path.open(encoding="utf-8") as f:
                    child_payload = json.load(f)
                run_payload["result"] = child_payload["result"]
                report["runs"].append(run_payload)
                result = child_payload["result"]
                print(
                    f"  -> wall={wall_elapsed_s:.1f}s solver={float(result.get('elapsed_solver_s') or 0.0):.1f}s "
                    f"conv={result.get('overall_converged')} mae={result.get('mae')} "
                    f"nonconv={result.get('step_nonconvergence_count')}"
                )
    run_lookup = {
        (item["window_label"], item["config_name"]): item
        for item in report["runs"]
        if not item.get("timed_out") and item.get("result", {}).get("verdict") not in {"ERROR", "TIMEOUT"}
    }
    for window_label, _ in WINDOWS:
        baseline = run_lookup.get((window_label, "friction_stub_only"))
        signs = run_lookup.get((window_label, "friction_stub_plus_signs"))
        full = run_lookup.get((window_label, "friction_stub_plus_signs_master"))
        if baseline and signs:
            report["comparisons"].append(_pairwise_comparison(baseline, signs))
        if signs and full:
            report["comparisons"].append(_pairwise_comparison(signs, full))
    report_path = Path(args.report_json) if args.report_json else _report_path()
    with report_path.open("w", encoding="utf-8") as f:
        json.dump(report, f, ensure_ascii=False, indent=2)
    print(f"[report] {report_path}")
    return 0


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Diagnose Example 17 preprocess sign/master slowdown.")
    parser.add_argument("--timeout-s", type=int, default=300, help="Per-run timeout in seconds for the parent matrix runner.")
    parser.add_argument("--report-json", help="Optional output JSON path.")
    parser.add_argument("--child", action="store_true", help="Internal child mode.")
    parser.add_argument("--json-path", help="Internal child input JSON path.")
    parser.add_argument("--case-label", default="Example17_PreprocessAB", help="Case label passed to run_network_case.")
    parser.add_argument("--config-name", help="Internal child config name.")
    parser.add_argument("--window-label", help="Internal child window label.")
    parser.add_argument("--t-end-s", type=float, help="Internal child window end time.")
    parser.add_argument("--output-json", help="Internal child output path.")
    parser.add_argument("--use-signs", type=int, choices=[0, 1], default=1, help="Internal child endpoint-sign toggle.")
    parser.add_argument("--use-master", type=int, choices=[0, 1], default=1, help="Internal child master-hint toggle.")
    return parser


def main() -> int:
    parser = _build_parser()
    args = parser.parse_args()
    if args.child:
        required = [args.json_path, args.config_name, args.window_label, args.output_json]
        if any(item in (None, "") for item in required):
            parser.error("--child requires --json-path, --config-name, --window-label, and --output-json")
        return _run_child(args)
    return _run_parent(args)


if __name__ == "__main__":
    raise SystemExit(main())
