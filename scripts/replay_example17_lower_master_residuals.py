#!/usr/bin/env python3
"""Example17 Lower master-row residual replay."""

from __future__ import annotations

import argparse
import copy
import json
import subprocess
import sys
import tempfile
import time
from contextlib import contextmanager
from datetime import datetime
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from scripts.diagnose_example17_preprocess_ab import _build_windowed_case


CASE_JSON = ROOT / "reports" / "hecras_unsteady_reference" / "Example17_Unsteady_unsteady_ref.json"
REPORT_DIR = ROOT / "reports" / "hecras_unsteady_diagnostics"
WINDOW_LABEL = "300s"
WINDOW_T_END_S = 300.0
TARGET_JUNCTION = "Lower"
DEBUG_T_END_S = 60.0
FORCED_LOWER_MASTER = {
    "reach_name": "Diamond/South",
    "endpoint": "us",
    "sign": 1.0,
    "raw_sign": -1.0,
    "diagnostic_source": "forced_from_raw_negative_candidate",
}
CONFIGS = [
    {
        "name": "signs_only",
        "use_preprocess_endpoint_signs": True,
        "use_preprocess_master_hints": False,
        "force_lower_master": False,
    },
    {
        "name": "signs_master_current",
        "use_preprocess_endpoint_signs": True,
        "use_preprocess_master_hints": True,
        "force_lower_master": False,
    },
    {
        "name": "signs_master_forced_lower",
        "use_preprocess_endpoint_signs": True,
        "use_preprocess_master_hints": True,
        "force_lower_master": True,
    },
]


def _load_case_json() -> dict:
    with CASE_JSON.open(encoding="utf-8") as f:
        return json.load(f)


@contextmanager
def _patched_lower_master(force_lower_master: bool):
    import scripts.run_all_unsteady_benchmark as benchmark

    if not force_lower_master:
        yield
        return

    original = benchmark._load_hecras_preprocess_connectivity_data

    def patched_loader(d: dict) -> dict:
        out = copy.deepcopy(original(d))
        hints = dict(out.get("junction_master_hints") or {})
        hints[TARGET_JUNCTION] = dict(FORCED_LOWER_MASTER)
        out["junction_master_hints"] = hints
        return out

    benchmark._load_hecras_preprocess_connectivity_data = patched_loader
    try:
        yield
    finally:
        benchmark._load_hecras_preprocess_connectivity_data = original


def _local_bc_map(record: dict) -> dict[str, float]:
    out: dict[str, float] = {}
    for item in record.get("local_bc", []) or []:
        key = f"{item.get('reach_name')}|{item.get('endpoint')}"
        out[key] = float(item.get("residual_local", 0.0) or 0.0)
    return out


def _summarize_lower_debug_records(records: list[dict]) -> dict:
    trajectory = []
    by_step: dict[float, list[dict]] = {}
    for item in records or []:
        if str(item.get("junction_name", "")) != TARGET_JUNCTION:
            continue
        local_bc_residuals = _local_bc_map(item)
        rec = {
            "t_new_s": float(item.get("t_new_s", 0.0) or 0.0),
            "nr_iter": int(item.get("nr_iter", 0) or 0),
            "master_reach": item.get("master_reach"),
            "master_endpoint": item.get("master_endpoint"),
            "continuity_residual": float(item.get("continuity_residual", 0.0) or 0.0),
            "abs_continuity_residual": abs(float(item.get("continuity_residual", 0.0) or 0.0)),
            "step_final_residual": float(item.get("step_final_residual", 0.0) or 0.0),
            "step_converged": bool(item.get("step_converged", False)),
            "local_bc_residuals": local_bc_residuals,
            "max_abs_local_bc_residual": max(
                (abs(value) for value in local_bc_residuals.values()),
                default=0.0,
            ),
        }
        trajectory.append(rec)
        by_step.setdefault(rec["t_new_s"], []).append(rec)
    trajectory.sort(key=lambda item: (item["t_new_s"], item["nr_iter"]))
    step_summary = []
    for t_new_s, items in sorted(by_step.items()):
        last = items[-1]
        step_summary.append(
            {
                "t_new_s": float(t_new_s),
                "nr_iterations": len(items),
                "master_reach": last["master_reach"],
                "master_endpoint": last["master_endpoint"],
                "max_abs_continuity_residual": max(
                    item["abs_continuity_residual"] for item in items
                ),
                "final_continuity_residual": float(last["continuity_residual"]),
                "max_abs_local_bc_residual": max(
                    item["max_abs_local_bc_residual"] for item in items
                ),
                "step_final_residual": float(last["step_final_residual"]),
                "step_converged": bool(last["step_converged"]),
            }
        )
    peak_record = max(
        trajectory,
        key=lambda item: item["abs_continuity_residual"],
        default=None,
    )
    return {
        "trajectory": trajectory,
        "step_summary": step_summary,
        "peak_record": peak_record,
    }


def _compare_lower_replay(base_result: dict, other_result: dict) -> dict:
    base_traj = base_result.get("lower_debug_summary", {}).get("trajectory", [])
    other_traj = other_result.get("lower_debug_summary", {}).get("trajectory", [])
    base_map = {
        (float(item["t_new_s"]), int(item["nr_iter"])): item
        for item in base_traj
    }
    onset = None
    max_delta_record = None
    for item in other_traj:
        key = (float(item["t_new_s"]), int(item["nr_iter"]))
        base_item = base_map.get(key)
        if base_item is None:
            delta_abs_cont = abs(float(item["continuity_residual"]))
            delta_abs_local = float(item["max_abs_local_bc_residual"])
            master_changed = True
        else:
            delta_abs_cont = abs(
                float(item["continuity_residual"]) - float(base_item["continuity_residual"])
            )
            delta_abs_local = 0.0
            keys = set(base_item["local_bc_residuals"]) | set(item["local_bc_residuals"])
            for bc_key in keys:
                delta_abs_local = max(
                    delta_abs_local,
                    abs(
                        float(item["local_bc_residuals"].get(bc_key, 0.0))
                        - float(base_item["local_bc_residuals"].get(bc_key, 0.0))
                    ),
                )
            master_changed = (
                item["master_reach"] != base_item["master_reach"]
                or item["master_endpoint"] != base_item["master_endpoint"]
            )
        candidate = {
            "t_new_s": float(item["t_new_s"]),
            "nr_iter": int(item["nr_iter"]),
            "master_reach": item["master_reach"],
            "master_endpoint": item["master_endpoint"],
            "delta_abs_continuity_residual": float(delta_abs_cont),
            "delta_abs_local_bc_residual": float(delta_abs_local),
            "master_changed": bool(master_changed),
        }
        if onset is None and (
            candidate["master_changed"]
            or candidate["delta_abs_continuity_residual"] > 1e-12
            or candidate["delta_abs_local_bc_residual"] > 1e-12
        ):
            onset = dict(candidate)
        if max_delta_record is None or (
            candidate["delta_abs_continuity_residual"],
            candidate["delta_abs_local_bc_residual"],
        ) > (
            max_delta_record["delta_abs_continuity_residual"],
            max_delta_record["delta_abs_local_bc_residual"],
        ):
            max_delta_record = dict(candidate)
    return {
        "base_config": base_result.get("config_name"),
        "other_config": other_result.get("config_name"),
        "onset": onset,
        "peak_delta": max_delta_record,
        "base_peak_record": base_result.get("lower_debug_summary", {}).get("peak_record"),
        "other_peak_record": other_result.get("lower_debug_summary", {}).get("peak_record"),
    }


def _summarize_result(config_name: str, force_lower_master: bool, result: dict) -> dict:
    solver_diag = dict(result.get("solver_diagnostics") or {})
    debug_records = list(solver_diag.get("junction_debug_records", []) or [])
    return {
        "config_name": config_name,
        "forced_lower_master": bool(force_lower_master),
        "mae": result.get("mae"),
        "mae_max": result.get("mae_max"),
        "elapsed_solver_s": result.get("elapsed"),
        "overall_converged": solver_diag.get("overall_converged"),
        "step_nonconvergence_count": solver_diag.get("step_nonconvergence_count"),
        "max_step_residual": solver_diag.get("max_step_residual"),
        "preprocess_usage": solver_diag.get("preprocess_usage", {}),
        "lower_debug_summary": _summarize_lower_debug_records(debug_records),
    }


def _run_child(args: argparse.Namespace) -> int:
    import scripts.run_all_unsteady_benchmark as benchmark

    with _patched_lower_master(bool(args.force_lower_master)):
        result = benchmark.run_network_case(
            args.json_path,
            args.case_label,
            solver_kwargs={
                "use_preprocess_endpoint_signs": bool(args.use_signs),
                "use_preprocess_master_hints": bool(args.use_master),
                "junction_debug_config": {
                    "junction_names": [TARGET_JUNCTION],
                    "t_end": DEBUG_T_END_S,
                },
                "junction_timing_names": [TARGET_JUNCTION],
            },
        )
    payload = _summarize_result(
        config_name=args.config_name,
        force_lower_master=bool(args.force_lower_master),
        result=result,
    )
    with Path(args.output_json).open("w", encoding="utf-8") as f:
        json.dump(payload, f, ensure_ascii=False, indent=2)
    return 0


def _report_path() -> Path:
    REPORT_DIR.mkdir(parents=True, exist_ok=True)
    stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    return REPORT_DIR / f"example17_lower_master_replay_{stamp}.json"


def _run_parent(args: argparse.Namespace) -> int:
    base_data = _load_case_json()
    window_data = _build_windowed_case(base_data, WINDOW_T_END_S)
    report = {
        "case_json": str(CASE_JSON),
        "generated_at": datetime.now().isoformat(timespec="seconds"),
        "window_label": WINDOW_LABEL,
        "t_end_s": WINDOW_T_END_S,
        "target_junction": TARGET_JUNCTION,
        "debug_t_end_s": DEBUG_T_END_S,
        "forced_lower_master_from_raw": dict(FORCED_LOWER_MASTER),
        "runs": [],
        "comparisons": [],
    }
    with tempfile.TemporaryDirectory(prefix="example17_lower_master_replay_") as tmpdir_str:
        tmpdir = Path(tmpdir_str)
        case_json_path = tmpdir / "example17_300s_window.json"
        with case_json_path.open("w", encoding="utf-8") as f:
            json.dump(window_data, f, ensure_ascii=False, indent=2)
        for config in CONFIGS:
            output_json_path = tmpdir / f"{config['name']}_result.json"
            cmd = [
                sys.executable,
                str(Path(__file__).resolve()),
                "--child",
                "--json-path",
                str(case_json_path),
                "--case-label",
                f"Example17_{WINDOW_LABEL}_{config['name']}",
                "--config-name",
                config["name"],
                "--output-json",
                str(output_json_path),
                "--use-signs",
                "1" if config["use_preprocess_endpoint_signs"] else "0",
                "--use-master",
                "1" if config["use_preprocess_master_hints"] else "0",
                "--force-lower-master",
                "1" if config["force_lower_master"] else "0",
            ]
            print(
                f"[run] config={config['name']:<26} "
                f"signs={int(config['use_preprocess_endpoint_signs'])} "
                f"master={int(config['use_preprocess_master_hints'])} "
                f"force_lower_master={int(config['force_lower_master'])}"
            )
            started = time.perf_counter()
            proc = subprocess.run(
                cmd,
                cwd=str(ROOT),
                capture_output=True,
                text=True,
                timeout=float(args.timeout_s),
            )
            wall_elapsed_s = time.perf_counter() - started
            if proc.returncode != 0 or not output_json_path.exists():
                raise RuntimeError(
                    f"child failed for {config['name']} rc={proc.returncode}\n"
                    f"stdout_tail={proc.stdout[-4000:]}\n"
                    f"stderr_tail={proc.stderr[-4000:]}"
                )
            with output_json_path.open(encoding="utf-8") as f:
                result = json.load(f)
            report["runs"].append(
                {
                    "config_name": config["name"],
                    "wall_elapsed_s": wall_elapsed_s,
                    "stdout_tail": proc.stdout[-4000:],
                    "stderr_tail": proc.stderr[-4000:],
                    "result": result,
                }
            )
            print(
                f"  -> wall={wall_elapsed_s:.1f}s "
                f"solver={float(result.get('elapsed_solver_s') or 0.0):.1f}s "
                f"mae={result.get('mae')} "
                f"nonconv={result.get('step_nonconvergence_count')}"
            )
    run_lookup = {item["config_name"]: item["result"] for item in report["runs"]}
    for base_name, other_name in [
        ("signs_only", "signs_master_current"),
        ("signs_only", "signs_master_forced_lower"),
        ("signs_master_current", "signs_master_forced_lower"),
    ]:
        report["comparisons"].append(
            _compare_lower_replay(run_lookup[base_name], run_lookup[other_name])
        )
    report_path = Path(args.report_json) if args.report_json else _report_path()
    with report_path.open("w", encoding="utf-8") as f:
        json.dump(report, f, ensure_ascii=False, indent=2)
    print(f"[report] {report_path}")
    return 0


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Replay Example17 Lower master-row residuals.")
    parser.add_argument("--timeout-s", type=int, default=300, help="Per-child timeout in seconds.")
    parser.add_argument("--report-json", help="Optional output JSON path.")
    parser.add_argument("--child", action="store_true", help="Internal child mode.")
    parser.add_argument("--json-path", help="Internal child input JSON path.")
    parser.add_argument("--case-label", default="Example17_LowerReplay", help="Case label passed to run_network_case.")
    parser.add_argument("--config-name", help="Internal child config name.")
    parser.add_argument("--output-json", help="Internal child output path.")
    parser.add_argument("--use-signs", type=int, choices=[0, 1], default=1, help="Internal child endpoint-sign toggle.")
    parser.add_argument("--use-master", type=int, choices=[0, 1], default=1, help="Internal child master-hint toggle.")
    parser.add_argument(
        "--force-lower-master",
        type=int,
        choices=[0, 1],
        default=0,
        help="Internal child flag for diagnostic forced Lower master replay.",
    )
    return parser


def main() -> int:
    parser = _build_parser()
    args = parser.parse_args()
    if args.child:
        required = [args.json_path, args.config_name, args.output_json]
        if any(item in (None, "") for item in required):
            parser.error("--child requires --json-path, --config-name, and --output-json")
        return _run_child(args)
    return _run_parent(args)


if __name__ == "__main__":
    raise SystemExit(main())
