#!/usr/bin/env python3
"""Metadata-driven entrypoint for unsteady HEC-RAS benchmarks."""

from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))


REPORT_DIR = ROOT / "reports" / "hecras_unsteady_validation"
DEFAULT_CASE_ROOT = ROOT / "validation_cases" / "unsteady"
BASIS_REGISTRY_PATH = DEFAULT_CASE_ROOT / "metadata" / "basis_registry.json"
REQUIRED_KEYS = [
    "case_id",
    "title",
    "category",
    "status",
    "modeling_basis_case",
    "steady_basis_case",
    "hec_ras_mode",
    "hydroclaude_solver",
    "runner_mode",
    "unit_system",
    "validation_targets",
]


def _load_metadata(path: Path) -> dict[str, Any]:
    with path.open(encoding="utf-8") as f:
        data = json.load(f)
    missing = [k for k in REQUIRED_KEYS if k not in data]
    if missing:
        raise ValueError(f"Metadata missing keys: {missing}")
    return data


def _load_basis_registry() -> dict[str, Any]:
    with BASIS_REGISTRY_PATH.open(encoding="utf-8") as f:
        data = json.load(f)
    if "modeling_basis_cases" not in data or "steady_basis_cases" not in data:
        raise ValueError("basis_registry.json must contain modeling_basis_cases and steady_basis_cases")
    return data


def _resolve_optional_path(raw: str | None) -> str | None:
    if not raw:
        return None
    path = Path(raw)
    if not path.is_absolute():
        path = ROOT / path
    return str(path.resolve())


def _inventory_only(meta: dict[str, Any]) -> dict[str, Any]:
    return {
        "status": "inventory_only",
        "mae": None,
        "mae_max": None,
        "ic_mae": None,
        "verdict": "PLANNED",
        "notes": meta.get("notes", []),
    }


def _check_pipeline_prerequisites(meta: dict[str, Any], registry: dict[str, Any]) -> dict[str, Any]:
    modeling_basis = str(meta.get("modeling_basis_case", "")).strip()
    steady_basis = str(meta.get("steady_basis_case", "")).strip()
    if not modeling_basis:
        raise ValueError("modeling_basis_case is required for all unsteady benchmark cases")
    if not steady_basis:
        raise ValueError("steady_basis_case is required for all unsteady benchmark cases")
    modeling_entry = registry["modeling_basis_cases"].get(modeling_basis)
    if modeling_entry is None:
        raise ValueError(f"Unknown modeling_basis_case: {modeling_basis}")
    steady_entry = registry["steady_basis_cases"].get(steady_basis)
    if steady_entry is None:
        raise ValueError(f"Unknown steady_basis_case: {steady_basis}")

    missing_artifacts: list[str] = []
    for raw in modeling_entry.get("artifacts", []):
        path = ROOT / raw
        if not path.exists():
            missing_artifacts.append(raw)
    for raw in steady_entry.get("artifacts", []):
        path = ROOT / raw
        if not path.exists():
            missing_artifacts.append(raw)
    if missing_artifacts:
        raise FileNotFoundError(f"Basis artifacts not found: {missing_artifacts}")

    notes: list[str] = []
    steady_status = str(steady_entry.get("basis_status", "")).strip() or "unknown"
    if steady_status != "same_project":
        notes.append(
            f"Steady basis status is `{steady_status}`; current run is not a same-project three-stage closure."
        )
    if steady_entry.get("notes"):
        notes.extend([str(item) for item in steady_entry["notes"]])

    return {
        "modeling_basis": {
            "id": modeling_basis,
            "status": modeling_entry.get("basis_status"),
            "project_name": modeling_entry.get("hec_ras_project_name"),
            "plan_title": modeling_entry.get("hec_ras_plan_title"),
            "artifacts": modeling_entry.get("artifacts", []),
        },
        "steady_basis": {
            "id": steady_basis,
            "status": steady_status,
            "description": steady_entry.get("description"),
            "artifacts": steady_entry.get("artifacts", []),
        },
        "notes": notes,
    }


def _run_single_reach(meta: dict[str, Any], ref_json: str) -> dict[str, Any]:
    from scripts.run_all_unsteady_benchmark import run_single_reach

    return run_single_reach(ref_json, meta["title"])


def _run_network(meta: dict[str, Any], ref_json: str) -> dict[str, Any]:
    from scripts.run_all_unsteady_benchmark import run_network_case

    return run_network_case(ref_json, meta["title"])


def _append_unique_notes(result: dict[str, Any], extra_notes: list[str]) -> dict[str, Any]:
    merged = [str(item) for item in result.get("notes", [])]
    for note in extra_notes:
        if note not in merged:
            merged.append(note)
    if merged:
        result["notes"] = merged
    return result


def _execute_case(meta: dict[str, Any]) -> dict[str, Any]:
    runner_mode = meta["runner_mode"]
    ref_json = _resolve_optional_path(meta.get("source_reference_json"))
    registry = _load_basis_registry()
    pipeline_info = _check_pipeline_prerequisites(meta, registry)

    if runner_mode == "inventory_only":
        result = _inventory_only(meta)
        result["pipeline_prerequisites"] = pipeline_info
        return _append_unique_notes(result, pipeline_info["notes"])

    if not ref_json:
        raise FileNotFoundError("source_reference_json is required for executable runner modes")

    if runner_mode == "single_reach_json_preissmann":
        result = _run_single_reach(meta, ref_json)
        result["pipeline_prerequisites"] = pipeline_info
        return _append_unique_notes(result, pipeline_info["notes"])

    if runner_mode == "network_json_preissmann":
        result = _run_network(meta, ref_json)
        result["pipeline_prerequisites"] = pipeline_info
        return _append_unique_notes(result, pipeline_info["notes"])

    raise ValueError(f"Unsupported runner_mode: {runner_mode}")


def _report_paths(case_id: str) -> tuple[Path, Path]:
    REPORT_DIR.mkdir(parents=True, exist_ok=True)
    stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    base = REPORT_DIR / f"{case_id}_{stamp}"
    return base.with_suffix(".json"), base.with_suffix(".md")


def _write_reports(meta: dict[str, Any], result: dict[str, Any]) -> tuple[Path, Path]:
    json_path, md_path = _report_paths(meta["case_id"])
    payload = {
        "metadata": meta,
        "result": result,
        "generated_at": datetime.now().isoformat(timespec="seconds"),
    }
    with json_path.open("w", encoding="utf-8") as f:
        json.dump(payload, f, ensure_ascii=False, indent=2)

    lines = [
        f"# {meta['title']}",
        "",
        f"- case_id: `{meta['case_id']}`",
        f"- category: `{meta['category']}`",
        f"- status: `{meta['status']}`",
        f"- modeling_basis_case: `{meta['modeling_basis_case']}`",
        f"- steady_basis_case: `{meta['steady_basis_case']}`",
        f"- hec_ras_mode: `{meta['hec_ras_mode']}`",
        f"- hydroclaude_solver: `{meta['hydroclaude_solver']}`",
        f"- runner_mode: `{meta['runner_mode']}`",
        f"- verdict: `{result.get('verdict')}`",
        f"- mae: `{result.get('mae')}`",
        f"- mae_max: `{result.get('mae_max')}`",
        f"- ic_mae: `{result.get('ic_mae')}`",
        "",
        "## Pipeline Prerequisites",
        "",
    ]
    pipeline = result.get("pipeline_prerequisites") or {}
    modeling = pipeline.get("modeling_basis") or {}
    steady = pipeline.get("steady_basis") or {}
    if modeling:
        lines.extend(
            [
                f"- modeling project: `{modeling.get('project_name')}`",
                f"- modeling plan: `{modeling.get('plan_title')}`",
                f"- modeling status: `{modeling.get('status')}`",
            ]
        )
        for item in modeling.get("artifacts", []):
            lines.append(f"- modeling artifact: `{item}`")
    if steady:
        lines.extend(
            [
                f"- steady description: `{steady.get('description')}`",
                f"- steady status: `{steady.get('status')}`",
            ]
        )
        for item in steady.get("artifacts", []):
            lines.append(f"- steady artifact: `{item}`")
    lines.extend(
        [
            "",
        "## Validation Targets",
        "",
        ]
    )
    for item in meta.get("validation_targets", []):
        lines.append(f"- {item}")
    if result.get("notes"):
        lines.extend(["", "## Notes", ""])
        for note in result["notes"]:
            lines.append(f"- {note}")
    if result.get("error"):
        lines.extend(["", "## Error", "", "```text", str(result['error']), "```"])
    md_path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return json_path, md_path


def _discover_metadata(case_root: Path) -> list[Path]:
    return sorted(case_root.glob("**/case_metadata.json"))


def _run_case_path(path: Path) -> int:
    meta = _load_metadata(path)
    result = _execute_case(meta)
    json_path, md_path = _write_reports(meta, result)
    print(f"{meta['case_id']}: {result.get('verdict')}  mae={result.get('mae')}")
    print(f"  json: {json_path}")
    print(f"  md:   {md_path}")
    verdict = str(result.get("verdict", "FAIL")).upper()
    return 0 if verdict in {"PASS", "NEAR", "PLANNED", "BLOCKED"} else 1


def main() -> int:
    parser = argparse.ArgumentParser(description="Run metadata-driven unsteady HEC-RAS benchmark cases.")
    parser.add_argument("metadata", nargs="?", help="Path to case_metadata.json")
    parser.add_argument("--all", action="store_true", help="Run all metadata cases under validation_cases/unsteady")
    args = parser.parse_args()

    if args.all:
        rc = 0
        for path in _discover_metadata(DEFAULT_CASE_ROOT):
            rc = max(rc, _run_case_path(path))
        return rc

    if not args.metadata:
        parser.print_help()
        return 1

    return _run_case_path(Path(args.metadata))


if __name__ == "__main__":
    raise SystemExit(main())
