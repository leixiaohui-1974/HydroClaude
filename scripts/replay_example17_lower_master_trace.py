#!/usr/bin/env python3
"""Replay Example 17 Lower junction residual traces for master-row diagnosis."""

from __future__ import annotations

import json
import sys
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from scripts.diagnose_example17_preprocess_ab import _build_windowed_case, _load_case_json
from scripts.run_all_unsteady_benchmark import run_network_case

REPORT_DIR = ROOT / "reports" / "hecras_unsteady_diagnostics"
WINDOW_T_END_S = 300.0


def _tmp_case_path() -> Path:
    REPORT_DIR.mkdir(parents=True, exist_ok=True)
    return REPORT_DIR / "_tmp_example17_lower_replay_300s.json"


def _extract_lower_trace(result: dict) -> list[dict]:
    solver_diag = dict(result.get("solver_diagnostics") or {})
    rows = []
    for record in solver_diag.get("junction_debug_records", []) or []:
        if str(record.get("junction_name")) != "Lower":
            continue
        local_bc_rows = []
        for item in record.get("local_bc", []) or []:
            local_bc_rows.append(
                {
                    "reach_name": item.get("reach_name"),
                    "endpoint": item.get("endpoint"),
                    "residual_local": float(item.get("residual_local", 0.0) or 0.0),
                    "dF_dZ_local": float(item.get("dF_dZ_local", 0.0) or 0.0),
                    "dF_dQ_local": float(item.get("dF_dQ_local", 0.0) or 0.0),
                    "target_stage": float(item.get("target_stage", 0.0) or 0.0),
                }
            )
        replaced_rows = []
        for item in record.get("replaced_stage_rows", []) or []:
            replaced_rows.append(
                {
                    "reach_name": item.get("reach_name"),
                    "endpoint": item.get("endpoint"),
                    "bc_row_global": int(item.get("bc_row_global", 0) or 0),
                    "replacement_residual": float(item.get("replacement_residual", 0.0) or 0.0),
                    "dF_dZ_endpoint": float(item.get("dF_dZ_endpoint", 0.0) or 0.0),
                    "dF_dZ_master": float(item.get("dF_dZ_master", 0.0) or 0.0),
                }
            )
        rows.append(
            {
                "t_new_s": float(record.get("t_new_s", 0.0) or 0.0),
                "picard_iter": int(record.get("picard_iter", 0) or 0),
                "nr_iter": int(record.get("nr_iter", 0) or 0),
                "replacement_mode": record.get("replacement_mode"),
                "master_reach": record.get("master_reach"),
                "master_endpoint": record.get("master_endpoint"),
                "master_fc_row": int(record.get("master_fc_row", 0) or 0),
                "master_stage": float(record.get("master_stage", 0.0) or 0.0),
                "master_flow": float(record.get("master_flow", 0.0) or 0.0),
                "continuity_residual": float(record.get("continuity_residual", 0.0) or 0.0),
                "master_fc_residual": float(record.get("master_fc_residual", 0.0) or 0.0),
                "nr_global_max_residual_pre_solve": float(
                    record.get("nr_global_max_residual_pre_solve", 0.0) or 0.0
                ),
                "q_in_sum": float(record.get("q_in_sum", 0.0) or 0.0),
                "q_out_sum": float(record.get("q_out_sum", 0.0) or 0.0),
                "dVdt": float(record.get("dVdt", 0.0) or 0.0),
                "step_converged": bool(record.get("step_converged", False)),
                "step_final_residual": float(record.get("step_final_residual", 0.0) or 0.0),
                "local_bc": local_bc_rows,
                "replaced_stage_rows": replaced_rows,
            }
        )
    rows.sort(key=lambda item: (item["t_new_s"], item["picard_iter"], item["nr_iter"]))
    return rows


def _summarize_trace(rows: list[dict]) -> dict:
    unique_masters = []
    seen = set()
    max_abs_continuity = 0.0
    max_abs_local = 0.0
    max_abs_replaced = 0.0
    first_row = rows[0] if rows else None
    for row in rows:
        key = (row["master_reach"], row["master_endpoint"])
        if key not in seen:
            seen.add(key)
            unique_masters.append({"reach_name": key[0], "endpoint": key[1]})
        max_abs_continuity = max(max_abs_continuity, abs(float(row["continuity_residual"])))
        for item in row["local_bc"]:
            max_abs_local = max(max_abs_local, abs(float(item["residual_local"])))
        for item in row["replaced_stage_rows"]:
            max_abs_replaced = max(max_abs_replaced, abs(float(item["replacement_residual"])))
    return {
        "record_count": len(rows),
        "first_record": first_row,
        "unique_masters": unique_masters,
        "max_abs_continuity_residual": max_abs_continuity,
        "max_abs_local_bc_residual": max_abs_local,
        "max_abs_replaced_stage_residual": max_abs_replaced,
    }


def _compare_traces(base_rows: list[dict], other_rows: list[dict]) -> dict:
    base_map = {
        (row["t_new_s"], row["picard_iter"], row["nr_iter"]): row
        for row in base_rows
    }
    differences = []
    for row in other_rows:
        key = (row["t_new_s"], row["picard_iter"], row["nr_iter"])
        base = base_map.get(key)
        if base is None:
            differences.append(
                {
                    "t_new_s": row["t_new_s"],
                    "picard_iter": row["picard_iter"],
                    "nr_iter": row["nr_iter"],
                    "reason": "missing_in_base",
                }
            )
            continue
        master_changed = (
            base["master_reach"] != row["master_reach"]
            or base["master_endpoint"] != row["master_endpoint"]
        )
        cont_delta = float(row["continuity_residual"]) - float(base["continuity_residual"])
        global_delta = float(row["nr_global_max_residual_pre_solve"]) - float(
            base["nr_global_max_residual_pre_solve"]
        )
        if master_changed or abs(cont_delta) > 1e-9 or abs(global_delta) > 1e-9:
            differences.append(
                {
                    "t_new_s": row["t_new_s"],
                    "picard_iter": row["picard_iter"],
                    "nr_iter": row["nr_iter"],
                    "base_master_reach": base["master_reach"],
                    "base_master_endpoint": base["master_endpoint"],
                    "other_master_reach": row["master_reach"],
                    "other_master_endpoint": row["master_endpoint"],
                    "delta_continuity_residual": cont_delta,
                    "delta_global_max_residual": global_delta,
                    "base_replaced_stage_rows": base["replaced_stage_rows"],
                    "other_replaced_stage_rows": row["replaced_stage_rows"],
                }
            )
    differences.sort(key=lambda item: (item["t_new_s"], item["picard_iter"], item["nr_iter"]))
    return {
        "first_difference": differences[0] if differences else None,
        "difference_count": len(differences),
    }


def _run_case(
    case_json_path: Path,
    case_label: str,
    *,
    use_master: bool,
    forced_master_hints: dict | None = None,
) -> dict:
    return run_network_case(
        str(case_json_path),
        case_label,
        solver_kwargs={
            "use_preprocess_endpoint_signs": True,
            "use_preprocess_master_hints": bool(use_master),
            "forced_preprocess_master_hints": dict(forced_master_hints or {}),
            "junction_timing_names": ["Lower"],
            "junction_debug_config": {
                "junction_names": ["Lower"],
                "t_start": 0.0,
                "t_end": WINDOW_T_END_S,
            },
        },
    )


def main() -> int:
    case_data = _build_windowed_case(_load_case_json(), WINDOW_T_END_S)
    case_json_path = _tmp_case_path()
    case_json_path.write_text(json.dumps(case_data, ensure_ascii=False, indent=2), encoding="utf-8")
    runs = []
    configs = [
        {
            "name": "signs_only",
            "use_master": False,
            "forced_master_hints": {},
        },
        {
            "name": "forced_bad_lower_master",
            "use_master": False,
            "forced_master_hints": {
                "Lower": {
                    "reach_name": "Diamond/South",
                    "endpoint": "us",
                }
            },
        },
    ]
    for config in configs:
        result = _run_case(
            case_json_path,
            f"Example17_LowerReplay_{config['name']}",
            use_master=bool(config["use_master"]),
            forced_master_hints=dict(config["forced_master_hints"]),
        )
        trace_rows = _extract_lower_trace(result)
        solver_diag = dict(result.get("solver_diagnostics") or {})
        runs.append(
            {
                "config_name": config["name"],
                "forced_master_hints": config["forced_master_hints"],
                "elapsed_s": float(result.get("elapsed", 0.0) or 0.0),
                "mae_m": float(result.get("mae", 0.0) or 0.0),
                "max_mae_m": float(result.get("mae_max", 0.0) or 0.0),
                "overall_converged": bool(solver_diag.get("overall_converged", False)),
                "step_nonconvergence_count": int(solver_diag.get("step_nonconvergence_count", 0) or 0),
                "max_step_residual": float(solver_diag.get("max_step_residual", 0.0) or 0.0),
                "preprocess_usage": solver_diag.get("preprocess_usage", {}),
                "lower_trace_summary": _summarize_trace(trace_rows),
                "lower_trace": trace_rows,
            }
        )
    comparison = _compare_traces(runs[0]["lower_trace"], runs[1]["lower_trace"])
    report = {
        "generated_at": datetime.now().isoformat(timespec="seconds"),
        "window_t_end_s": WINDOW_T_END_S,
        "runs": runs,
        "comparison": comparison,
    }
    stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    report_path = REPORT_DIR / f"example17_lower_master_replay_{stamp}.json"
    report_path.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"[report] {report_path}")
    print(json.dumps(
        {
            "report": str(report_path),
            "comparison": comparison,
            "run_summaries": [
                {
                    "config_name": item["config_name"],
                    "elapsed_s": item["elapsed_s"],
                    "mae_m": item["mae_m"],
                    "max_mae_m": item["max_mae_m"],
                    "overall_converged": item["overall_converged"],
                    "step_nonconvergence_count": item["step_nonconvergence_count"],
                    "max_step_residual": item["max_step_residual"],
                    "lower_trace_summary": item["lower_trace_summary"],
                }
                for item in runs
            ],
        },
        ensure_ascii=False,
        indent=2,
    ))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
