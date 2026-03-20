"""Generate a HydroMind-style overview for HEC-RAS official example suite runs."""

from __future__ import annotations

import argparse
import base64
import json
import sys
from collections import Counter, defaultdict
from datetime import datetime
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from utils.font_config import setup_chinese_font


REPORTS_DIR = ROOT / "reports"
FIGURES_DIR = REPORTS_DIR / "figures"


def _style_plot() -> None:
    setup_chinese_font()
    plt.rcParams["figure.figsize"] = (11, 5.8)
    plt.rcParams["axes.grid"] = True
    plt.rcParams["grid.alpha"] = 0.22
    plt.rcParams["axes.spines.top"] = False
    plt.rcParams["axes.spines.right"] = False


def _save_figure(fig: plt.Figure, path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fig.tight_layout()
    fig.savefig(path, bbox_inches="tight")
    plt.close(fig)


def _asset_to_data_uri(path: Path) -> str:
    mime = "image/svg+xml" if path.suffix.lower() == ".svg" else "image/png"
    payload = base64.b64encode(path.read_bytes()).decode("ascii")
    return f"data:{mime};base64,{payload}"


def _load_records(pattern: str) -> tuple[list[dict], list[Path]]:
    paths = sorted(REPORTS_DIR.glob(pattern))
    records: list[dict] = []
    for path in paths:
        payload = json.loads(path.read_text(encoding="utf-8"))
        records.extend(payload.get("records", []))
    deduped = {}
    for record in records:
        deduped[record["project_name"]] = record
    return sorted(deduped.values(), key=lambda r: (r.get("category", ""), r["project_name"])), paths


def _normalized_level(record: dict) -> str:
    category = str(record.get("category", "")).lower()
    level = record.get("comparability", {}).get("level", "unknown")
    if "1d steady flow hydraulics" not in category:
        return "not_direct"
    return level


def _build_figures(records: list[dict]) -> dict[str, Path]:
    _style_plot()
    FIGURES_DIR.mkdir(parents=True, exist_ok=True)

    status_counts = Counter(record.get("status", "unknown") for record in records)
    comparability_counts = Counter(_normalized_level(record) for record in records)

    status_fig = FIGURES_DIR / "hecras_suite_status.svg"
    comp_fig = FIGURES_DIR / "hecras_suite_comparability.svg"

    fig, ax = plt.subplots(figsize=(10.8, 5.6))
    labels = ["computed", "failed"]
    values = [status_counts.get(label, 0) for label in labels]
    colors = ["#2a9d8f", "#bb3e03"]
    ax.bar(labels, values, color=colors, width=0.58)
    ax.set_title("HEC-RAS 官方案例运行状态")
    ax.set_ylabel("案例数")
    for idx, value in enumerate(values):
        ax.text(idx, value + 0.2, str(value), ha="center", va="bottom", fontsize=11)
    _save_figure(fig, status_fig)

    fig, ax = plt.subplots(figsize=(10.8, 5.6))
    labels = ["direct_candidate", "partial", "not_direct"]
    values = [comparability_counts.get(label, 0) for label in labels]
    colors = ["#0a9396", "#ee9b00", "#6c757d"]
    ax.bar(labels, values, color=colors, width=0.58)
    ax.set_title("HydroClaude 可直接对标性分类")
    ax.set_ylabel("案例数")
    for idx, value in enumerate(values):
        ax.text(idx, value + 0.2, str(value), ha="center", va="bottom", fontsize=11)
    _save_figure(fig, comp_fig)

    return {"status": status_fig, "comparability": comp_fig}


def generate_report(pattern: str = "hecras_example_suite_chunk_*.json") -> dict[str, Path]:
    records, source_paths = _load_records(pattern)
    if not records:
        raise FileNotFoundError(f"No suite chunk JSON files matched reports/{pattern}")

    generated_at = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    figures = _build_figures(records)

    computed = [r for r in records if r.get("status") == "computed"]
    failed = [r for r in records if r.get("status") == "failed"]
    direct = [r for r in records if _normalized_level(r) == "direct_candidate"]
    partial = [r for r in records if _normalized_level(r) == "partial"]

    by_category: dict[str, Counter] = defaultdict(Counter)
    for record in records:
        by_category[record.get("category", "未分类")][record.get("status", "unknown")] += 1

    category_lines = []
    for category in sorted(by_category):
        counts = by_category[category]
        category_lines.append(
            f"| {category} | {counts.get('computed', 0)} | {counts.get('failed', 0)} | {counts.get('computed', 0) + counts.get('failed', 0)} |"
        )

    failed_lines = "\n".join(
        f"| {r['project_name']} | {r.get('category', '')} | {str(r.get('error', ''))[:120]} |"
        for r in failed[:20]
    ) or "| 无 | - | - |"

    direct_lines = "\n".join(
        f"| {r['project_name']} | {r.get('category', '')} | {r.get('declared_current_plan', '-') or '-'} | {r.get('result_hdf_path', '-') or '-'} |"
        for r in direct[:20]
    ) or "| 暂无 | - | - | - |"

    partial_lines = "\n".join(
        f"| {r['project_name']} | {r.get('category', '')} | {r.get('comparability', {}).get('reason', '')} |"
        for r in partial[:20]
    ) or "| 暂无 | - | - |"

    md_path = REPORTS_DIR / "hydromind_hecras_example_suite_report.md"
    html_path = REPORTS_DIR / "hydromind_hecras_example_suite_report.html"
    json_path = REPORTS_DIR / "hydromind_hecras_example_suite_report.json"

    md = f"""# HydroMind仿真结果报告: HEC-RAS 官方案例套件巡检

**生成时间**: {generated_at}

## 1. 问题描述

需要把 `HEC-RAS 6.6 Example Projects` 的官方案例真实跑起来，并回答两个问题：

1. 当前机器上到底有多少个案例能被真实 HEC-RAS 计算完成。
2. 哪些案例适合与 `HydroClaude` 做公平直接的数值对标，哪些只能作为复杂物理能力边界检查。

## 2. 解题思路

1. 通过 `ras_commander + HEC-RAS COM` 在本机真实打开项目并执行 `Compute_CurrentPlan`。
2. 每个案例提取到本地临时目录，避免污染官方原始样例并减少弹窗/锁文件干扰。
3. 不再把计划号写死为 `01`，而是从 `.prj` 的 `Current Plan` 和新生成的 `*.p??.hdf` 自动识别真实结果 plan。
4. 汇总运行状态、可对标性分类和失败案例，输出人工核查页。

## 3. 核心结论

| 指标 | 数值 |
|---|---:|
| 已汇总案例数 | {len(records)} |
| 成功计算数 | {len(computed)} |
| 失败数 | {len(failed)} |
| 可直接对标候选 | {len(direct)} |
| 部分可对比 | {len(partial)} |
| 数据来源分片 | {len(source_paths)} |

## 4. 分类统计

![运行状态](figures/{figures['status'].name})

![可对标性分类](figures/{figures['comparability'].name})

## 5. 分类汇总

| 类别 | 成功计算 | 失败 | 合计 |
|---|---:|---:|---:|
{chr(10).join(category_lines)}

## 6. 直接对标候选

| 案例 | 类别 | Plan | 结果 HDF |
|---|---|---|---|
{direct_lines}

## 7. 部分可比较案例

| 案例 | 类别 | 原因 |
|---|---|---|
{partial_lines}

## 8. 失败案例

| 案例 | 类别 | 报错摘要 |
|---|---|---|
{failed_lines}
"""

    source_links = "".join(f"<li>{path.name}</li>" for path in source_paths)
    category_rows = "".join(f"<tr>{''.join(f'<td>{cell}</td>' for cell in line.strip('|').split('|'))}</tr>" for line in category_lines)
    direct_rows = "".join(f"<tr>{''.join(f'<td>{cell}</td>' for cell in line.strip('|').split('|'))}</tr>" for line in direct_lines.splitlines())
    partial_rows = "".join(f"<tr>{''.join(f'<td>{cell}</td>' for cell in line.strip('|').split('|'))}</tr>" for line in partial_lines.splitlines())
    failed_rows = "".join(f"<tr>{''.join(f'<td>{cell}</td>' for cell in line.strip('|').split('|'))}</tr>" for line in failed_lines.splitlines())

    html = f"""<!DOCTYPE html>
<html lang="zh-CN">
<head>
  <meta charset="utf-8">
  <title>HydroMind仿真结果报告: HEC-RAS 官方案例套件巡检</title>
  <style>
    body {{
      margin: 0;
      font-family: "Microsoft YaHei", "PingFang SC", "Noto Sans CJK SC", Arial, sans-serif;
      background: #f4f1ea;
      color: #1f2933;
    }}
    .page {{
      max-width: 1380px;
      margin: 0 auto;
      padding: 28px 26px 56px;
    }}
    .hero {{
      display: grid;
      grid-template-columns: repeat(6, 1fr);
      gap: 14px;
      margin: 20px 0 24px;
    }}
    .metric {{
      background: linear-gradient(135deg, #eff8f6 0%, #fff8ea 100%);
      border-radius: 14px;
      padding: 16px 18px;
      border: 1px solid #d7e6df;
    }}
    .label {{ color: #52606d; font-size: 14px; }}
    .value {{ font-size: 28px; font-weight: 700; margin-top: 8px; color: #0b3c49; }}
    .card {{
      background: #fffdf8;
      border: 1px solid #e5dfd0;
      border-radius: 14px;
      padding: 18px 20px;
      margin: 18px 0;
      box-shadow: 0 8px 24px rgba(15, 23, 42, 0.06);
    }}
    .fig-grid {{
      display: grid;
      grid-template-columns: 1fr 1fr;
      gap: 18px;
    }}
    figure {{
      margin: 0;
      background: white;
      border: 1px solid #d9d9d9;
      border-radius: 12px;
      overflow: hidden;
    }}
    figure img {{ display: block; width: 100%; background: white; }}
    figcaption {{ padding: 10px 12px 14px; color: #52606d; font-size: 14px; }}
    table {{
      width: 100%;
      border-collapse: collapse;
      margin-top: 10px;
    }}
    th, td {{
      border-bottom: 1px solid #e5e7eb;
      padding: 10px 12px;
      text-align: left;
      vertical-align: top;
    }}
    th {{ background: #eef6f7; }}
    ul {{ margin: 8px 0 0 18px; }}
  </style>
</head>
<body>
  <div class="page">
    <h1>HydroMind仿真结果报告: HEC-RAS 官方案例套件巡检</h1>
    <div>生成时间: {generated_at}</div>

    <div class="hero">
      <div class="metric"><div class="label">已汇总案例数</div><div class="value">{len(records)}</div></div>
      <div class="metric"><div class="label">成功计算数</div><div class="value">{len(computed)}</div></div>
      <div class="metric"><div class="label">失败数</div><div class="value">{len(failed)}</div></div>
      <div class="metric"><div class="label">直接对标候选</div><div class="value">{len(direct)}</div></div>
      <div class="metric"><div class="label">部分可比较</div><div class="value">{len(partial)}</div></div>
      <div class="metric"><div class="label">数据分片</div><div class="value">{len(source_paths)}</div></div>
    </div>

    <div class="card">
      <h2>1. 问题描述</h2>
      <p>本页不是测试日志，而是 `HEC-RAS` 官方案例真实求解状态的巡检结果。核心目标是看清楚哪些案例已经跑通，哪些案例适合与 `HydroClaude` 做公平对标，以及剩余阻塞到底来自算法能力还是工程集成噪声。</p>
    </div>

    <div class="card">
      <h2>2. 解题思路</h2>
      <ul>
        <li>每个案例都提取到本地临时目录运行，避免污染原始样例并减小锁文件与弹窗干扰。</li>
        <li>计划号从 `.prj` 的 `Current Plan` 和生成的 `*.p??.hdf` 自动识别，不再假定都是 `p01`。</li>
        <li>对每个案例记录运行状态、真实结果 HDF、compute messages 预览和可对标性分类。</li>
        <li>把复杂结构物、混合流态、2D、泥沙等案例与单河道稳态回水候选分开，避免不公平对标。</li>
      </ul>
    </div>

    <div class="card">
      <h2>3. 统计图</h2>
      <div class="fig-grid">
        <figure>
          <img src="{_asset_to_data_uri(figures['status'])}" alt="HEC-RAS 官方案例运行状态">
          <figcaption>图1. 当前已汇总官方案例的真实运行状态。</figcaption>
        </figure>
        <figure>
          <img src="{_asset_to_data_uri(figures['comparability'])}" alt="HydroClaude 可直接对标性分类">
          <figcaption>图2. 当前案例对 HydroClaude 的公平直接对标可行性。</figcaption>
        </figure>
      </div>
    </div>

    <div class="card">
      <h2>4. 数据来源分片</h2>
      <ul>{source_links}</ul>
    </div>

    <div class="card">
      <h2>5. 分类汇总</h2>
      <table>
        <tr><th>类别</th><th>成功计算</th><th>失败</th><th>合计</th></tr>
        {category_rows}
      </table>
    </div>

    <div class="card">
      <h2>6. 直接对标候选</h2>
      <table>
        <tr><th>案例</th><th>类别</th><th>Plan</th><th>结果 HDF</th></tr>
        {direct_rows}
      </table>
    </div>

    <div class="card">
      <h2>7. 部分可比较案例</h2>
      <table>
        <tr><th>案例</th><th>类别</th><th>原因</th></tr>
        {partial_rows}
      </table>
    </div>

    <div class="card">
      <h2>8. 失败案例</h2>
      <table>
        <tr><th>案例</th><th>类别</th><th>报错摘要</th></tr>
        {failed_rows}
      </table>
    </div>
  </div>
</body>
</html>
"""

    json_payload = {
        "generated_at": generated_at,
        "source_files": [str(path) for path in source_paths],
        "record_count": len(records),
        "computed_count": len(computed),
        "failed_count": len(failed),
        "direct_candidate_count": len(direct),
        "partial_count": len(partial),
        "records": records,
    }

    md_path.write_text(md, encoding="utf-8")
    html_path.write_text(html, encoding="utf-8")
    json_path.write_text(json.dumps(json_payload, ensure_ascii=False, indent=2), encoding="utf-8")
    return {"md": md_path, "html": html_path, "json": json_path}


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--pattern", default="hecras_example_suite_chunk_*.json")
    args = parser.parse_args()
    result = generate_report(pattern=args.pattern)
    print(json.dumps({key: str(value) for key, value in result.items()}, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
