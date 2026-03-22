#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""batch regen HEC-RAS reference JSON (schema v2.0).

Features:
1. Iterate 19 cases, call HECRASInputExtractor to extract data;
2. If old JSON exists, merge validation fields by profile name + xs index:
   alpha, friction_slope, conveyance_total, area_flow_total,
   velocity_total, manning_n_channel;
3. Expand new profiles cross_sections from key-list to full records;
4. Output to reports/hecras_reference_data/.
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from integration.hecras_input_extractor import HECRASInputExtractor  # noqa: E402

SOURCE_ROOT = PROJECT_ROOT / "reports" / "hecras_examples_raw"
OUTPUT_ROOT = PROJECT_ROOT / "reports" / "hecras_reference_data"

CASE_MAP: List[Tuple[str, str, str]] = [
    ("Applications Guide/Example 1 - Critical Creek",
     "example_1__critical_creek_CRITCREK.p01.json", "p01"),
    ("Applications Guide/Example 2 - Beaver Creek",
     "example_2__beaver_creek_BEAVCREK.p01.json", "p01"),
    ("Applications Guide/Example 3 - Single Culvert",
     "example_3__single_culvert_TWINPIPE.p01.json", "p01"),
    ("Applications Guide/Example 4 - Multiple Culverts",
     "example_4__multiple_culverts_MULTCULV.p01.json", "p01"),
    ("Applications Guide/Example 5 - Multiple Openings",
     "example_5__multiple_openings_MULTOPEN.p02.json", "p02"),
    ("Applications Guide/Example 6 - Floodway Determination",
     "example_6__floodway_determination_FLODENCR.p01.json", "p01"),
    ("Applications Guide/Example 7 - Multiple Plans",
     "example_7__multiple_plans_NAPA.p01.json", "p01"),
    ("Applications Guide/Example 8 - Looped Network",
     "example_8__looped_network_LOOP.p01.json", "p01"),
    ("Applications Guide/Example 9 - Mixed Flow Analysis",
     "example_9__mixed_flow_analysis_MIXFLOW.p02.json", "p02"),
    ("Applications Guide/Example 10 - Stream Junction",
     "example_10__stream_junction_JUNCTION.p02.json", "p02"),
    ("Applications Guide/Example 11 - Bridge Scour",
     "example_11__bridge_scour_SCOUR.p01.json", "p01"),
    ("Applications Guide/Example 12 - Inline Structure",
     "example_12__inline_structure_NIT.p01.json", "p01"),
    ("Applications Guide/Example 13 - Singler Bridge (WSPRO)",
     "example_13__singler_bridge_wspro_BOGCHIT.p01.json", "p01"),
    ("Applications Guide/Example 14 - Ice Covered River",
     "example_14__ice_covered_river_thames.p01.json", "p01"),
    ("Applications Guide/Example 15 - Split Flow Junction with Lateral Weir",
     "example_15__split_flow_junction_with_lateral_weir_SPLIT_LW.p01.json", "p01"),
    ("Applications Guide/Example 16 - Channel Modification",
     "example_16__channel_modification_CHANMOD.p02.json", "p02"),
    ("1D Steady Flow Hydraulics/Chapter 4 Example Data",
     "chapter_4_example_data_EX1.p01.json", "p01"),
    ("1D Steady Flow Hydraulics/ConSpan Culvert",
     "conspan_culvert_ConSpan.p01.json", "p01"),
    ("1D Steady Flow Hydraulics/Mixed Flow Regime Channel",
     "mixed_flow_regime_channel_MIXED.p01.json", "p01"),
]

VALIDATION_FIELDS: Tuple[str, ...] = (
    "alpha",
    "friction_slope",
    "conveyance_total",
    "area_flow_total",
    "velocity_total",
    "manning_n_channel",
)


def _as_list(value: Any) -> List[Any]:
    if value is None:
        return []
    if isinstance(value, list):
        return value
    return [value]


def _read_json(path: Path) -> Dict[str, Any]:
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def _write_json(path: Path, data: Dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)


def merge_profiles(new_profiles: list, old_profiles: list) -> list:
    """Merge profiles and expand cross_sections to full records.

    Args:
        new_profiles: profiles from HECRASInputExtractor.extract_all().
        old_profiles: profiles from old JSON with validation fields.

    Returns:
        Merged profiles list with wse/flow + validation fields per xs.
    """
    old_by_name: Dict[str, Dict[str, Any]] = {}
    for p in _as_list(old_profiles):
        if not isinstance(p, dict):
            continue
        name = p.get("name")
        if isinstance(name, str) and name:
            old_by_name[name] = p

    merged: List[Dict[str, Any]] = []

    for profile in _as_list(new_profiles):
        if not isinstance(profile, dict):
            continue

        profile_name = profile.get("name")
        old_profile = old_by_name.get(profile_name) if isinstance(profile_name, str) else None

        xs_keys = _as_list(profile.get("cross_sections"))
        wse_ft_arr = _as_list(profile.get("water_surface_ft"))
        wse_m_arr = _as_list(profile.get("water_surface_m"))
        flow_cfs_arr = _as_list(profile.get("flow_cfs"))
        flow_m3s_arr = _as_list(profile.get("flow_m3s"))

        old_xs_list: List[Any] = []
        if isinstance(old_profile, dict):
            old_xs_list = _as_list(old_profile.get("cross_sections"))

        n = max(
            len(xs_keys), len(wse_ft_arr), len(wse_m_arr),
            len(flow_cfs_arr), len(flow_m3s_arr),
        )
        if n == 0:
            n = len(old_xs_list)

        expanded_xs: List[Dict[str, Any]] = []
        for i in range(n):
            key_info: Dict[str, Any] = {}
            if i < len(xs_keys) and isinstance(xs_keys[i], dict):
                key_info = xs_keys[i]
            row: Dict[str, Any] = {
                "index": i,
                "river": key_info.get("river"),
                "reach": key_info.get("reach"),
                "station": key_info.get("station"),
                "name": key_info.get("name"),
                "wse_ft": wse_ft_arr[i] if i < len(wse_ft_arr) else None,
                "wse_m": wse_m_arr[i] if i < len(wse_m_arr) else None,
                "flow_cfs": flow_cfs_arr[i] if i < len(flow_cfs_arr) else None,
                "flow_m3s": flow_m3s_arr[i] if i < len(flow_m3s_arr) else None,
            }
            if i < len(old_xs_list) and isinstance(old_xs_list[i], dict):
                old_row = old_xs_list[i]
                for field in VALIDATION_FIELDS:
                    if field in old_row:
                        row[field] = old_row[field]
            expanded_xs.append(row)

        p_out = dict(profile)
        p_out["cross_sections"] = expanded_xs
        merged.append(p_out)

    return merged


def _process_case(
    src_dir: str,
    output_filename: str,
    plan_suffix: str,
    *,
    dry_run: bool,
    force: bool,
) -> None:
    """Extract a single case and write JSON output."""
    case_dir = SOURCE_ROOT / src_dir
    output_path = OUTPUT_ROOT / output_filename

    if not case_dir.exists():
        raise FileNotFoundError(f"案例目录不存在: {case_dir}")

    if output_path.exists() and not force:
        print(f"[SKIP] {output_filename} (已存在，使用 --force 重新生成)")
        return

    old_data: Dict[str, Any] = {}
    if output_path.exists():
        try:
            old_data = _read_json(output_path)
        except Exception as exc:
            print(f"  警告: 无法读取旧 JSON ({exc})，跳过验证字段合并")

    extractor = HECRASInputExtractor(case_dir, plan_suffix)
    new_data = extractor.extract_all()

    merged = merge_profiles(
        new_profiles=_as_list(new_data.get("profiles")),
        old_profiles=_as_list(old_data.get("profiles")),
    )

    new_data["profiles"] = merged
    new_data["reference_profiles"] = merged
    new_data["n_profiles"] = len(merged)

    if dry_run:
        n_xs = new_data.get("n_cross_sections", "?")
        print(f"[DRY] {output_filename} (n_profiles={len(merged)}, n_xs={n_xs})")
        return

    _write_json(output_path, new_data)
    n_xs = new_data.get("n_cross_sections", "?")
    print(f"[OK]  {output_filename} (n_profiles={len(merged)}, n_xs={n_xs})")


def run(
    dry_run: bool = False,
    case_filter: Optional[str] = None,
    force: bool = False,
) -> int:
    """Main entry point, returns number of successful cases.

    Args:
        dry_run: If True, only print without writing files.
        case_filter: Filter by output filename prefix (None = all).
        force: Regenerate even if output file exists.

    Returns:
        Number of successfully processed cases.
    """
    selected: List[Tuple[str, str, str]] = CASE_MAP
    if case_filter:
        prefix = case_filter.lower()
        selected = [c for c in CASE_MAP if c[1].lower().startswith(prefix)]
        if not selected:
            print(f"警告: 没有找到前缀为 {case_filter!r} 的案例")

    total = len(selected)
    success = 0

    for src_dir, output_filename, plan_suffix in selected:
        try:
            _process_case(
                src_dir, output_filename, plan_suffix,
                dry_run=dry_run, force=force,
            )
            success += 1
        except Exception as exc:
            print(f"[FAIL] {output_filename}: {exc}")

    print(f"\n{success}/{total} 成功")
    return success


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="批量重新生成 HEC-RAS 参考数据 JSON（schema v2.0）。"
    )
    parser.add_argument(
        "--dry-run", action="store_true",
        help="只打印处理结果，不写文件",
    )
    parser.add_argument(
        "--case", default=None,
        metavar="PREFIX",
        help="只处理某个案例（按输出文件名前缀匹配，如 example_1）",
    )
    parser.add_argument(
        "--force", action="store_true",
        help="即使输出文件已存在也重新生成",
    )
    return parser


if __name__ == "__main__":
    args = _build_parser().parse_args()
    result = run(
        dry_run=args.dry_run,
        case_filter=args.case,
        force=args.force,
    )
    sys.exit(0 if result > 0 else 1)
