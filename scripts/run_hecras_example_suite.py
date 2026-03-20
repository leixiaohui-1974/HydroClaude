"""Batch-run HEC-RAS official example projects and classify HydroClaude comparability."""

from __future__ import annotations

import argparse
import json
import re
import shutil
import sys
import tempfile
import time
from datetime import datetime
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from integration.hec_ras_adapter import detect_hec_ras_runtime


def _load_projects() -> list[dict[str, str]]:
    from ras_commander import RasExamples

    RasExamples.get_example_projects("6.6")
    ex = RasExamples()
    df = ex.folder_df
    projects = []
    for _, row in df.dropna(subset=["Project"]).sort_values(["Category", "Project"]).iterrows():
        projects.append({
            "project_name": str(row["Project"]),
            "category": str(row.get("Category", "")),
        })
    return projects


def _extract_project(project_name: str, output_root: Path) -> Path:
    from ras_commander import RasExamples

    last_exc: Exception | None = None
    for _ in range(2):
        try:
            unique_suffix = f"hydroclaude_suite_{time.time_ns()}"
            return RasExamples.extract_project(project_name, output_path=output_root, suffix=unique_suffix)
        except Exception as exc:
            last_exc = exc
            time.sleep(1.0)
    assert last_exc is not None
    raise last_exc


def _find_project_file(extract_root: Path) -> Path:
    root_level = sorted(extract_root.glob("*.prj"))
    if root_level:
        return root_level[0]

    recursive = sorted(extract_root.rglob("*.prj"))
    if not recursive:
        raise FileNotFoundError(f"No .prj file found under extracted project root: {extract_root}")

    def _score(path: Path) -> tuple[int, int, str]:
        parts = [part.lower() for part in path.parts]
        solution_bias = 0 if "solution" in parts else 1
        depth = len(path.relative_to(extract_root).parts)
        return (solution_bias, depth, str(path).lower())

    return min(recursive, key=_score)


def _run_current_plan(prj_path: Path) -> None:
    import win32com.client  # type: ignore[import-untyped]

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


def _read_current_plan_number(prj_text: str) -> str | None:
    match = re.search(r"(?mi)^Current Plan\s*=\s*p?(\d{1,2})\s*$", prj_text)
    if not match:
        return None
    return match.group(1).zfill(2)


def _list_plan_hdfs(project_dir: Path) -> dict[str, Path]:
    plan_hdfs: dict[str, Path] = {}
    for path in project_dir.glob("*.p*.hdf"):
        match = re.search(r"\.p(\d{2})\.hdf$", path.name, flags=re.IGNORECASE)
        if match:
            plan_hdfs[match.group(1)] = path
    return plan_hdfs


def _pick_actual_plan_number(project_dir: Path, declared_plan_number: str | None, before_hdfs: dict[str, Path]) -> tuple[str | None, list[str]]:
    after_hdfs = _list_plan_hdfs(project_dir)
    new_plan_numbers = sorted(num for num in after_hdfs if num not in before_hdfs)
    if declared_plan_number and declared_plan_number in after_hdfs:
        return declared_plan_number, new_plan_numbers
    if len(new_plan_numbers) == 1:
        return new_plan_numbers[0], new_plan_numbers
    if new_plan_numbers:
        newest = max(new_plan_numbers, key=lambda num: after_hdfs[num].stat().st_mtime)
        return newest, new_plan_numbers
    if after_hdfs:
        newest = max(after_hdfs, key=lambda num: after_hdfs[num].stat().st_mtime)
        return newest, new_plan_numbers
    return declared_plan_number, new_plan_numbers


def _read_compute_messages_preview(project_dir: Path, plan_number: str, max_lines: int = 8) -> tuple[list[str], int | None]:
    txt_candidates = list(project_dir.glob(f"*.p{plan_number}.computeMsgs.txt")) + list(project_dir.glob(f"*.P{plan_number}.computeMsgs.txt"))
    if not txt_candidates:
        return [], None
    text = txt_candidates[0].read_text(encoding="utf-8", errors="ignore")
    lines = [line.strip() for line in re.split(r"\r\n|\n", text) if line.strip()]
    return lines[:max_lines], len(lines)


def _classify_comparability(category: str, project_name: str, prj_text: str, flow_files: list[Path], geom_files: list[Path]) -> dict[str, Any]:
    title = prj_text.lower()
    category_lower = category.lower()
    joined_names = " ".join([project_name] + [p.stem for p in flow_files] + [p.stem for p in geom_files]).lower()
    combined = f"{category_lower} {title} {joined_names}"

    hard_blockers = [
        "bridge", "culvert", "inline", "lateral", "storage", "pump", "pipe",
        "2d", "sediment", "dam", "gate", "weir", "press/weir", "mixed flow",
        "junction", "breach", "reservoir", "unsteady",
    ]
    partial_markers = [
        "normal depth", "critical", "mixed", "levee", "structure", "multiple reaches",
    ]

    if "1d steady flow hydraulics" not in category_lower:
        return {
            "level": "not_direct",
            "reason": "不属于单河道稳态回水主线问题，当前不作为 HydroClaude 公平直接对标样例。",
        }

    if any(marker in combined for marker in hard_blockers):
        return {
            "level": "not_direct",
            "reason": "含桥梁/结构物/混合流态/2D 等复杂物理，当前 HydroClaude 不能公平直接对标。",
        }

    if any(marker in combined for marker in partial_markers):
        return {
            "level": "partial",
            "reason": "属于稳态明渠但边界或断面条件较复杂，可做部分口径对照，不适合作为首批公平样例。",
        }

    return {
        "level": "direct_candidate",
        "reason": "看起来接近单河道稳态回水问题，可作为 HydroClaude 直接对比候选。",
    }


def _collect_project_record(project_meta: dict[str, str], output_root: Path) -> dict[str, Any]:
    started = time.perf_counter()
    project_name = project_meta["project_name"]
    record: dict[str, Any] = {
        "project_name": project_name,
        "category": project_meta.get("category", ""),
        "status": "pending",
    }
    try:
        extract_root = _extract_project(project_name, output_root=output_root)
        prj_path = _find_project_file(extract_root)
        project_dir = prj_path.parent
        prj_text = prj_path.read_text(encoding="utf-8", errors="ignore")
        flow_files = sorted(project_dir.glob("*.f*"))
        geom_files = sorted(project_dir.glob("*.g*"))
        declared_plan_number = _read_current_plan_number(prj_text)
        before_hdfs = _list_plan_hdfs(project_dir)

        record["extract_root"] = str(extract_root)
        record["project_dir"] = str(project_dir)
        record["project_file"] = str(prj_path)
        record["flow_file_count"] = len(flow_files)
        record["geometry_file_count"] = len(geom_files)
        record["declared_current_plan"] = declared_plan_number
        record["comparability"] = _classify_comparability(
            project_meta.get("category", ""),
            project_name,
            prj_text,
            flow_files,
            geom_files,
        )

        _run_current_plan(prj_path)
        actual_plan_number, new_plan_numbers = _pick_actual_plan_number(project_dir, declared_plan_number, before_hdfs)
        plan_hdf_files = sorted(str(p) for p in _list_plan_hdfs(project_dir).values())
        record["plan_hdf_files"] = plan_hdf_files
        record["new_plan_numbers"] = new_plan_numbers
        record["actual_plan_number"] = actual_plan_number
        record["status"] = "computed"

        if actual_plan_number:
            try:
                preview, line_count = _read_compute_messages_preview(project_dir, actual_plan_number)
                record["compute_messages_preview"] = preview
                record["compute_message_line_count"] = line_count
                record["result_hdf_path"] = str(_list_plan_hdfs(project_dir).get(actual_plan_number, ""))
            except Exception as exc:
                record["compute_messages_error"] = str(exc)
        else:
            record["compute_messages_error"] = "No plan results HDF could be resolved after compute."
    except Exception as exc:
        record["status"] = "failed"
        record["error"] = str(exc)
    finally:
        record["elapsed_seconds"] = round(time.perf_counter() - started, 2)
    return record


def run_suite(max_projects: int | None = None, start_index: int = 0) -> dict[str, Any]:
    runtime = detect_hec_ras_runtime()
    if not runtime.installed or not runtime.com_available:
        raise RuntimeError("HEC-RAS runtime not available on this machine.")

    projects = _load_projects()
    if start_index:
        projects = projects[start_index:]
    if max_projects is not None:
        projects = projects[:max_projects]

    output_root = Path(tempfile.gettempdir()) / "hydroclaude_hecras_suite"
    output_root.mkdir(parents=True, exist_ok=True)

    records = []
    for idx, project_meta in enumerate(projects, start=start_index + 1):
        run_root = output_root / f"{idx:03d}"
        if run_root.exists():
            shutil.rmtree(run_root, ignore_errors=True)
        run_root.mkdir(parents=True, exist_ok=True)
        records.append(_collect_project_record(project_meta, output_root=run_root))

    summary = {
        "generated_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "runtime": runtime.__dict__,
        "start_index": start_index,
        "project_count": len(records),
        "catalog_project_count": len(_load_projects()),
        "computed_count": sum(1 for r in records if r["status"] == "computed"),
        "failed_count": sum(1 for r in records if r["status"] == "failed"),
        "direct_candidate_count": sum(1 for r in records if r.get("comparability", {}).get("level") == "direct_candidate"),
        "partial_count": sum(1 for r in records if r.get("comparability", {}).get("level") == "partial"),
        "not_direct_count": sum(1 for r in records if r.get("comparability", {}).get("level") == "not_direct"),
        "records": records,
    }
    return summary


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--max-projects", type=int, default=None)
    parser.add_argument("--start-index", type=int, default=0)
    parser.add_argument("--output", type=Path, default=ROOT / "reports" / "hecras_example_suite_report.json")
    args = parser.parse_args()

    summary = run_suite(max_projects=args.max_projects, start_index=args.start_index)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps({
        "output": str(args.output),
        "project_count": summary["project_count"],
        "computed_count": summary["computed_count"],
        "failed_count": summary["failed_count"],
    }, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
