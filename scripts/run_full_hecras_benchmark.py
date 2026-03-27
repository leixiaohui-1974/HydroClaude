#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""HydroClaude + HEC-RAS 全量对标脚本（Applications Guide 16 个案例）。

用法示例:

    python scripts/run_full_hecras_benchmark.py
    python scripts/run_full_hecras_benchmark.py --no-hecras
    python scripts/run_full_hecras_benchmark.py --no-hc
    python scripts/run_full_hecras_benchmark.py --case 3
    python scripts/run_full_hecras_benchmark.py --output-dir reports
"""

from __future__ import annotations

import argparse
import json
import re
import shutil
import subprocess
import sys
import tempfile
import time
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
APP_GUIDE_DIR = ROOT / "reports" / "hecras_examples_raw" / "Applications Guide"
REF_DATA_DIR = ROOT / "reports" / "hecras_reference_data"
REPORTS_DIR = ROOT / "reports"

HECRAS_VERSION = "6.6"
HYDROCLAUDE_VERSION = "dev"


@dataclass(frozen=True)
class CaseConfig:
    """单个案例的配置。"""
    src_dir: str
    json_filename: str
    plan_suffix: str
    prj_filename: str


CASE_MAP: list[CaseConfig] = [
    CaseConfig("Example 1 - Critical Creek",
               "example_1__critical_creek_CRITCREK.p01.json", "p01", "CRITCREK.prj"),
    CaseConfig("Example 2 - Beaver Creek",
               "example_2__beaver_creek_BEAVCREK.p01.json", "p01", "BEAVCREK.prj"),
    CaseConfig("Example 3 - Single Culvert",
               "example_3__single_culvert_TWINPIPE.p01.json", "p01", "TWINPIPE.prj"),
    CaseConfig("Example 4 - Multiple Culverts",
               "example_4__multiple_culverts_MULTCULV.p01.json", "p01", "MULTCULV.prj"),
    CaseConfig("Example 5 - Multiple Openings",
               "example_5__multiple_openings_MULTOPEN.p02.json", "p02", "MULTOPEN.prj"),
    CaseConfig("Example 6 - Floodway Determination",
               "example_6__floodway_determination_FLODENCR.p01.json", "p01", "FLODENCR.prj"),
    CaseConfig("Example 7 - Multiple Plans",
               "example_7__multiple_plans_NAPA.p01.json", "p01", "NAPA.prj"),
    CaseConfig("Example 8 - Looped Network",
               "example_8__looped_network_LOOP.p01.json", "p01", "LOOP.prj"),
    CaseConfig("Example 9 - Mixed Flow Analysis",
               "example_9__mixed_flow_analysis_MIXFLOW.p02.json", "p02", "MIXFLOW.prj"),
    CaseConfig("Example 10 - Stream Junction",
               "example_10__stream_junction_JUNCTION.p02.json", "p02", "JUNCTION.prj"),
    CaseConfig("Example 11 - Bridge Scour",
               "example_11__bridge_scour_SCOUR.p01.json", "p01", "SCOUR.prj"),
    CaseConfig("Example 12 - Inline Structure",
               "example_12__inline_structure_NIT.p01.json", "p01", "NIT.prj"),
    CaseConfig("Example 13 - Singler Bridge (WSPRO)",
               "example_13__singler_bridge_wspro_BOGCHIT.p01.json", "p01", "BOGCHIT.prj"),
    CaseConfig("Example 14 - Ice Covered River",
               "example_14__ice_covered_river_thames.p01.json", "p01", "thames.prj"),
    CaseConfig("Example 15 - Split Flow Junction with Lateral Weir",
               "example_15__split_flow_junction_with_lateral_weir_SPLIT_LW.p01.json",
               "p01", "SPLIT_LW.prj"),
    CaseConfig("Example 16 - Channel Modification",
               "example_16__channel_modification_CHANMOD.p02.json", "p02", "CHANMOD.prj"),
]

# 解析 batch 输出: case_name(42) + profile(12) + mae + status
_PROFILE_LINE_RE = re.compile(
    r"^\s+(?P<case>.+?)\s{2,}(?P<profile>\S.*?)\s{2,}"
    r"(?P<mae>\d+(?:\.\d+)?)\s+(?P<status>PASS|NEAR|FAIL|ERR)\s*$"
)
_SUMMARY_LINE_RE = re.compile(
    r"PASS:\s*(?P<pass_n>\d+)/(?P<total>\d+)\s*\([^)]+\)"
    r"\s*NEAR:\s*(?P<near>\d+)\s*FAIL:\s*(?P<fail>\d+)"
)


def _norm(name: str) -> str:
    return re.sub(r"\s+", " ", name.strip()).lower()



def run_single_hecras_case(case: CaseConfig) -> tuple[bool, str | None, float]:
    """在临时目录运行单个 HEC-RAS 案例，完成后清理临时目录。

    Args:
        case: 案例配置

    Returns:
        (success, error_message, elapsed_seconds)
    """
    start = time.perf_counter()
    temp_root: Path | None = None
    try:
        from ras_commander import RasCmdr, init_ras_project  # type: ignore[import-untyped]

        src = APP_GUIDE_DIR / case.src_dir
        if not src.exists():
            return False, f"源目录不存在: {src}", time.perf_counter() - start

        temp_root = Path(tempfile.mkdtemp(prefix="hydroclaude_hecras_"))
        tmp_case = temp_root / "case"
        shutil.copytree(src, tmp_case)

        prj_path = tmp_case / case.prj_filename
        if not prj_path.exists():
            return False, f"工程文件不存在: {prj_path}", time.perf_counter() - start

        ras = init_ras_project(prj_path, ras_version=HECRAS_VERSION)
        plan_num = case.plan_suffix.lstrip("p")
        result = RasCmdr.compute_plan(plan_num, ras_object=ras, force_rerun=True, num_cores=2)

        ok = bool(getattr(result, "success", False))
        if ok:
            return True, None, time.perf_counter() - start
        return False, "compute_plan 返回 success=False", time.perf_counter() - start

    except Exception as exc:
        return False, f"{type(exc).__name__}: {exc}", time.perf_counter() - start
    finally:
        if temp_root is not None:
            shutil.rmtree(temp_root, ignore_errors=True)


def _parse_hc_output(stdout: str) -> tuple[dict[str, list[dict]], dict | None]:
    """解析 hydroclaude_cli.py batch 输出。

    batch 输出格式: {case_name:42s} {profile_name:12s} {mae:.3f} {status}
    当案例名超过 42 字符时，分隔符可能不足 2 个空格。
    策略：先提取末尾 mae+status，再用已知案例名列表匹配行首。
    """
    # 已知案例名列表（用于健壮匹配）
    _known_cases = {_norm(c.src_dir) for c in CASE_MAP}

    # 宽松正则：提取末尾的 mae 和 status
    _LOOSE_RE = re.compile(
        r"^\s+(?P<rest>.+?)\s{2,}(?P<mae>\d+\.\d+)\s+(?P<status>PASS|NEAR|FAIL|ERR)\s*$"
    )

    parsed: dict[str, list[dict]] = {}
    summary_stats: dict | None = None

    for line in stdout.splitlines():
        m_sum = _SUMMARY_LINE_RE.search(line)
        if m_sum:
            summary_stats = {
                "pass_n": int(m_sum.group("pass_n")),
                "total": int(m_sum.group("total")),
                "near": int(m_sum.group("near")),
                "fail": int(m_sum.group("fail")),
            }
            continue

        # 先尝试标准正则（2+ 空格分隔）
        m = _PROFILE_LINE_RE.match(line)
        if m:
            case_name = m.group("case").strip()
            parsed.setdefault(_norm(case_name), []).append({
                "case_name": case_name,
                "profile_name": m.group("profile").strip(),
                "mae_m": float(m.group("mae")),
                "status": m.group("status").upper(),
            })
            continue

        # 宽松正则：case_name 超长时（如 Example 15）
        m2 = _LOOSE_RE.match(line)
        if not m2:
            continue
        rest = m2.group("rest")
        mae_val = float(m2.group("mae"))
        status = m2.group("status").upper()

        # 在已知案例名中找最长前缀匹配
        matched_case: str | None = None
        matched_len = 0
        for known_norm in _known_cases:
            # 找原始大小写的案例名
            for c in CASE_MAP:
                orig = c.src_dir
                if _norm(orig) == known_norm and rest.lower().startswith(known_norm):
                    if len(known_norm) > matched_len:
                        matched_case = orig
                        matched_len = len(known_norm)

        if matched_case is None:
            continue

        profile_name = rest[matched_len:].strip()
        parsed.setdefault(_norm(matched_case), []).append({
            "case_name": matched_case,
            "profile_name": profile_name,
            "mae_m": mae_val,
            "status": status,
        })

    return parsed, summary_stats


def run_hydroclaude_batch(timeout_s: int = 300) -> tuple[dict, dict | None, str | None]:
    """运行 hydroclaude_cli.py batch 并解析输出。"""
    cmd = [sys.executable, str(ROOT / "hydroclaude_cli.py"), "batch"]
    cmd_str = " ".join(str(c) for c in cmd)
    print(f"  命令: {cmd_str}")
    try:
        proc = subprocess.run(
            cmd, capture_output=True, text=True, cwd=str(ROOT), timeout=timeout_s,
        )
    except subprocess.TimeoutExpired:
        return {}, None, f"超时(>{timeout_s}s)"
    except Exception as exc:
        return {}, None, f"启动失败: {exc}"

    if proc.stdout:
        for ln in proc.stdout.splitlines()[-6:]:
            print(f"  [HC] {ln}")

    parsed, summary = _parse_hc_output(proc.stdout or "")
    err: str | None = None
    if proc.returncode != 0:
        stderr_s = (proc.stderr or "").strip()[:200]
        err = f"返回码 {proc.returncode}: {stderr_s}"
    return parsed, summary, err



def _agg_status(profiles: list[dict]) -> tuple[float | None, str]:
    """案例级联合状态: ERR > FAIL > NEAR > PASS。"""
    if not profiles:
        return None, "ERR"
    maes = [float(p["mae_m"]) for p in profiles]
    mean_mae = sum(maes) / len(maes)
    sts = {p["status"].upper() for p in profiles}
    for bad in ("ERR", "FAIL", "NEAR"):
        if bad in sts:
            return mean_mae, bad
    return mean_mae, "PASS"


def build_case_results(
    cases: list[CaseConfig],
    run_hecras: bool,
    run_hc: bool,
) -> tuple[list[dict[str, Any]], dict | None]:
    """执行 HEC-RAS 和 HydroClaude，组装各案例对比结果。"""
    hecras_map: dict[str, tuple] = {}
    if run_hecras:
        for i, case in enumerate(cases, 1):
            print(f"[HEC-RAS] ({i}/{len(cases)}) {case.src_dir}")
            ok, err, t = run_single_hecras_case(case)
            hecras_map[_norm(case.src_dir)] = (ok, err, t)
            status_lbl = "OK" if ok else "FAIL"
            print(f"  -> {status_lbl}  ({t:.1f}s)" + (f"  {err}" if err else ""))
    else:
        for case in cases:
            hecras_map[_norm(case.src_dir)] = (None, None, None)

    hc_parsed: dict = {}
    hc_summary_stats: dict | None = None
    hc_run_error: str | None = None
    if run_hc:
        print("[HydroClaude] 运行 batch ...")
        hc_parsed, hc_summary_stats, hc_run_error = run_hydroclaude_batch()
        if hc_run_error:
            print(f"  [WARN] {hc_run_error}")

    case_results: list[dict[str, Any]] = []
    for case in cases:
        norm = _norm(case.src_dir)
        h_ok, h_err, h_t = hecras_map.get(norm, (None, "映射错误", None))

        profiles: list[dict] = []
        hc_mae: float | None = None
        hc_st = "NOT_RUN"
        hc_err: str | None = None

        if run_hc:
            profiles = hc_parsed.get(norm, [])
            if profiles:
                hc_mae, hc_st = _agg_status(profiles)
            else:
                hc_st = "ERR"
                hc_err = hc_run_error or "未在 batch 输出中找到该案例"

        case_results.append({
            "case_name": case.src_dir,
            "hecras_run_success": h_ok,
            "hecras_run_error": h_err,
            "hecras_run_time_s": round(h_t, 2) if h_t is not None else None,
            "hc_profiles": profiles,
            "hc_mae_mean": round(hc_mae, 4) if hc_mae is not None else None,
            "hc_status": hc_st,
            "hc_error": hc_err,
        })

    return case_results, hc_summary_stats


def build_summary(
    cases: list[CaseConfig],
    case_results: list[dict[str, Any]],
    hc_summary_stats: dict | None,
) -> dict[str, Any]:
    """构建最终汇总 JSON。"""
    hr_ok = sum(1 for c in case_results if c["hecras_run_success"] is True)
    hr_fail = sum(1 for c in case_results if c["hecras_run_success"] is False)
    hc_pass = sum(1 for c in case_results if c["hc_status"] == "PASS")
    hc_near = sum(1 for c in case_results if c["hc_status"] == "NEAR")
    hc_fail = sum(1 for c in case_results if c["hc_status"] in {"FAIL", "ERR"})
    all_p: list[dict] = [p for c in case_results for p in c["hc_profiles"]]
    hc_total = len(all_p)
    hc_pass_p = sum(1 for p in all_p if p["status"] == "PASS")
    maes = [float(p["mae_m"]) for p in all_p]
    overall_mae: float | None = (sum(maes) / len(maes)) if maes else None

    return {
        "generated_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "hecras_version": HECRAS_VERSION,
        "hydroclaude_version": HYDROCLAUDE_VERSION,
        "total_cases": len(cases),
        "hecras_success": hr_ok,
        "hecras_failed": hr_fail,
        "hc_pass": hc_pass,
        "hc_near": hc_near,
        "hc_fail": hc_fail,
        "hc_total_profiles": hc_total,
        "hc_pass_profiles": hc_pass_p,
        "overall_mae_m": round(overall_mae, 4) if overall_mae is not None else None,
        "hc_batch_summary": hc_summary_stats,
        "cases": case_results,
    }



def write_text_report(summary: dict[str, Any], out_path: Path) -> None:
    """写入对齐格式的文本报告。"""
    W = 72
    lines: list[str] = [
        "HydroClaude vs HEC-RAS 对标报告",
        f"生成时间: {summary['generated_at']}",
        f"HEC-RAS 版本: {summary['hecras_version']}",
        f"HydroClaude 版本: {summary['hydroclaude_version']}",
        "",
        "=" * W,
        f"{'Case Name':<44} {'HEC-RAS':<10} {'HC MAE':<12} Status",
        "-" * W,
    ]
    for c in summary["cases"]:
        name = c["case_name"][:44]
        if c["hecras_run_success"] is True:
            hr_s = "OK"
        elif c["hecras_run_success"] is False:
            hr_s = "FAIL"
        else:
            hr_s = "SKIP"
        m = c["hc_mae_mean"]
        mae_text = f"{m:.3f} m" if isinstance(m, (int, float)) else "-"
        lines.append(f"{name:<44} {hr_s:<10} {mae_text:<12} {c['hc_status']}")

    lines.append("-" * W)
    lines.append(
        f"PASS: {summary['hc_pass']}/{summary['total_cases']}"
        f"  NEAR: {summary['hc_near']}  FAIL: {summary['hc_fail']}"
    )
    lines.append(f"HEC-RAS OK: {summary['hecras_success']}/{summary['total_cases']}")
    om = summary.get("overall_mae_m")
    lines.append(
        f"Overall MAE: {om:.4f} m" if isinstance(om, (int, float)) else "Overall MAE: -"
    )
    lines.append("=" * W)
    out_path.write_text("\n".join(lines), encoding="utf-8")



def _build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        description="Run HydroClaude + HEC-RAS benchmark (Applications Guide 16 cases)"
    )
    p.add_argument("--no-hecras", action="store_true",
                   help="跳过 HEC-RAS 运行")
    p.add_argument("--no-hc", action="store_true",
                   help="跳过 HydroClaude 运行")
    p.add_argument("--case", type=int, default=None, metavar="N",
                   help="只运行第 N 个案例 (1-based, 1~16)")
    p.add_argument("--output-dir", type=Path, default=REPORTS_DIR,
                   help="报告输出目录 (默认 reports/)")
    return p


def main() -> int:
    args = _build_parser().parse_args()

    if args.case is not None:
        if args.case < 1 or args.case > len(CASE_MAP):
            print(f"[ERROR] --case 超出范围, 应为 1~{len(CASE_MAP)}",
                  file=sys.stderr)
            return 2
        cases = [CASE_MAP[args.case - 1]]
    else:
        cases = list(CASE_MAP)

    run_hecras = not args.no_hecras
    run_hc = not args.no_hc

    if run_hecras and not APP_GUIDE_DIR.exists():
        print(f"[ERROR] Applications Guide 目录不存在: {APP_GUIDE_DIR}",
              file=sys.stderr)
        return 2

    output_dir: Path = args.output_dir
    output_dir.mkdir(parents=True, exist_ok=True)

    print("=== HydroClaude 全量对标 ===")
    print(f"案例数: {len(cases)}  HEC-RAS: {'on' if run_hecras else 'skip'}"
          f"  HydroClaude: {'on' if run_hc else 'skip'}")
    print()

    t0 = time.perf_counter()
    case_results, hc_stats = build_case_results(cases, run_hecras, run_hc)
    elapsed = time.perf_counter() - t0

    summary = build_summary(cases, case_results, hc_stats)
    summary["total_elapsed_s"] = round(elapsed, 1)

    date_tag = datetime.now().strftime("%Y%m%d")
    json_path = output_dir / f"full_benchmark_{date_tag}.json"
    txt_path = output_dir / f"full_benchmark_{date_tag}.txt"

    with open(json_path, "w", encoding="utf-8") as f:
        json.dump(summary, f, ensure_ascii=False, indent=2)
    write_text_report(summary, txt_path)

    print()
    print("=" * 72)
    print(f"对标完成  耗时: {elapsed:.0f}s")
    print(f"  HEC-RAS OK: {summary['hecras_success']}  FAIL: {summary['hecras_failed']}")
    print(f"  HydroClaude PASS: {summary['hc_pass']}  NEAR: {summary['hc_near']}"
          f"  FAIL: {summary['hc_fail']}")
    if summary["overall_mae_m"] is not None:
        print(f"  Overall MAE: {summary['overall_mae_m']:.4f} m")
    print(f"  JSON: {json_path}")
    print(f"  TXT:  {txt_path}")
    print("=" * 72)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())