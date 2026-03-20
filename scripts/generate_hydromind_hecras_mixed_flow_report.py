"""Generate a HydroMind report for a real HEC-RAS mixed-flow sample run."""

from __future__ import annotations

import base64
import json
import sys
from datetime import datetime
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from integration.hec_ras_adapter import run_hec_ras_mixed_flow_sample
from utils.font_config import setup_chinese_font


REPORTS_DIR = ROOT / "reports"
FIGURES_DIR = REPORTS_DIR / "figures"


def _style_plot() -> None:
    setup_chinese_font()
    plt.rcParams["figure.figsize"] = (12, 6)
    plt.rcParams["axes.grid"] = True
    plt.rcParams["grid.alpha"] = 0.25
    plt.rcParams["axes.spines.top"] = False
    plt.rcParams["axes.spines.right"] = False


def _save_figure(fig: plt.Figure, path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fig.tight_layout()
    fig.savefig(path, bbox_inches="tight")
    plt.close(fig)


def _asset_to_data_uri(path: Path) -> str:
    payload = base64.b64encode(path.read_bytes()).decode("ascii")
    mime = "image/svg+xml" if path.suffix.lower() == ".svg" else "image/png"
    return f"data:{mime};base64,{payload}"


def generate_report() -> dict[str, Path]:
    _style_plot()
    FIGURES_DIR.mkdir(parents=True, exist_ok=True)

    # Use the validated local-temp extraction path. UNC/shared output roots are
    # less reliable for ras-commander example extraction and HDF generation.
    result = run_hec_ras_mixed_flow_sample()
    project = result["project"]
    metrics = result["metrics"]
    hec = result["hec_ras"]
    hydro = result["hydrostatic"]

    x = np.asarray(hec["x_m"], dtype=float)
    bed = np.asarray(hec["bed_m"], dtype=float)
    hec_stage = np.asarray(hec["stage_m"], dtype=float)
    hec_depth = np.asarray(hec["depth_m"], dtype=float)
    hec_energy = np.asarray(hec["energy_grade_m"], dtype=float)
    hydro_stage = np.asarray(hydro["stage_m"], dtype=float)
    hydro_depth = np.asarray(hydro["depth_m"], dtype=float)
    abs_error = np.abs(hydro_depth - hec_depth)
    rel_error = abs_error / np.maximum(np.abs(hec_depth), 1e-9)
    profile_name = project["profile_name"]

    steady_fig = FIGURES_DIR / "hydromind_hecras_mixed_flow_profile.svg"
    error_fig = FIGURES_DIR / "hydromind_hecras_mixed_flow_error.svg"

    fig, ax = plt.subplots(figsize=(12.5, 6.5))
    ax.plot(x, hec_stage, color="#005f73", lw=2.5, label=f"HEC-RAS {profile_name}", solid_capstyle="round", solid_joinstyle="round")
    ax.plot(x, hydro_stage, color="#bb3e03", lw=2.0, ls="--", label="Hydrostatic 同几何近似", dash_capstyle="round")
    ax.plot(x, bed, color="#6c584c", lw=1.7, label="河床", solid_capstyle="round")
    ax.set_title("真实 HEC-RAS 混合流态样例对比")
    ax.set_xlabel("沿程距离 x (m)")
    ax.set_ylabel("高程 (m)")
    ax.legend(loc="best")
    _save_figure(fig, steady_fig)

    fig, axes = plt.subplots(2, 1, figsize=(12.5, 8.2), sharex=True)
    axes[0].plot(x, abs_error, color="#bb3e03", lw=2.2, solid_capstyle="round", solid_joinstyle="round")
    axes[0].set_title("水深绝对误差")
    axes[0].set_ylabel("|Δh| (m)")
    axes[1].plot(x, rel_error * 100.0, color="#005f73", lw=2.2, solid_capstyle="round", solid_joinstyle="round")
    axes[1].set_title("水深相对误差")
    axes[1].set_ylabel("误差 (%)")
    axes[1].set_xlabel("沿程距离 x (m)")
    _save_figure(fig, error_fig)

    generated_at = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    payload = {
        "generated_at": generated_at,
        "project": project,
        "metrics": metrics,
        "figures": {
            "profile": str(steady_fig.relative_to(REPORTS_DIR)).replace("\\", "/"),
            "error": str(error_fig.relative_to(REPORTS_DIR)).replace("\\", "/"),
        },
    }

    md_path = REPORTS_DIR / "hydromind_hecras_mixed_flow_report.md"
    html_path = REPORTS_DIR / "hydromind_hecras_mixed_flow_report.html"
    json_path = REPORTS_DIR / "hydromind_hecras_mixed_flow_report.json"

    md = f"""# HydroMind仿真结果报告: 真实 HEC-RAS 混合流态样例

**生成时间**: {generated_at}

## 1. 问题描述

为了把 `HEC-RAS` 真实外部求解链真正接到 HydroMind，这里使用官方 `HEC-RAS 6.6 Example Projects` 中的 `Mixed Flow Regime Channel` 项目，完成了真实 `Project_Open -> Compute_CurrentPlan -> HDF 结果读取` 闭环。

## 2. 当前结果

| 指标 | 数值 |
|---|---:|
| 真实 HEC-RAS 流量 | {payload['metrics']['hec_flow_m3s']:.4f} m3/s |
| HEC-RAS 上游水深 | {payload['metrics']['hec_upstream_depth_m']:.4f} m |
| Hydrostatic 上游水深 | {payload['metrics']['hydrostatic_upstream_depth_m']:.4f} m |
| 平均绝对误差 | {payload['metrics']['mean_abs_error_m']:.4f} m |
| 上游相对误差 | {payload['metrics']['upstream_rel_error_pct']:.4f}% |
| 平均相对误差 | {payload['metrics']['mean_rel_error_pct']:.4f}% |
| 最大相对误差 | {payload['metrics']['max_rel_error_pct']:.4f}% |

## 3. 结论

- `HEC-RAS` 真实外部建模、计算、结果提取链已经跑通。
- 当前选取的是官方 `Mixed Flow Regime Channel` 样例，它确实属于更难的混合流态/法线坡边界工况。
- 现阶段 `Hydrostatic` 在这个样例上的误差仍然很大，说明这不是“报表或夹具问题”，而是一个真实算法/边界条件能力差距。
- 这份报告的意义是把 `HEC-RAS` 从“口头对标”推进到了“真实外部求解器已接通，但当前工况尚未对齐”。

## 4. 图形证据

![HEC-RAS 混合流态水面线]({payload['figures']['profile']})

![HEC-RAS 混合流态误差]({payload['figures']['error']})
"""

    html = f"""<!DOCTYPE html>
<html lang="zh-CN">
<head>
  <meta charset="utf-8">
  <title>HydroMind 真实 HEC-RAS 混合流态样例</title>
  <style>
    body {{
      margin: 0;
      font-family: "Microsoft YaHei", "PingFang SC", "Noto Sans CJK SC", Arial, sans-serif;
      background: #f4f1ea;
      color: #1f2933;
    }}
    .page {{
      max-width: 1280px;
      margin: 0 auto;
      padding: 28px 26px 54px;
    }}
    .hero {{
      display: grid;
      grid-template-columns: repeat(4, 1fr);
      gap: 14px;
      margin: 18px 0 24px;
    }}
    .metric {{
      background: linear-gradient(135deg, #eff8f6 0%, #fff8ea 100%);
      border: 1px solid #d7e6df;
      border-radius: 14px;
      padding: 16px 18px;
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
    table {{
      width: 100%;
      border-collapse: collapse;
      margin-top: 10px;
    }}
    th, td {{
      border-bottom: 1px solid #e5e7eb;
      padding: 10px 12px;
      text-align: left;
    }}
    th {{ background: #eef6f7; }}
    figure {{
      margin: 18px 0;
      background: white;
      border: 1px solid #d9d9d9;
      border-radius: 12px;
      overflow: hidden;
    }}
    figure img {{ display: block; width: 100%; background: white; }}
    figcaption {{ padding: 10px 12px 14px; color: #52606d; font-size: 14px; }}
  </style>
</head>
<body>
  <div class="page">
    <h1>HydroMind仿真结果报告: 真实 HEC-RAS 混合流态样例</h1>
    <div>生成时间: {generated_at}</div>

    <div class="hero">
      <div class="metric">
        <div class="label">HEC-RAS 流量</div>
        <div class="value">{payload['metrics']['hec_flow_m3s']:.3f} m3/s</div>
      </div>
      <div class="metric">
        <div class="label">上游相对误差</div>
        <div class="value">{payload['metrics']['upstream_rel_error_pct']:.2f}%</div>
      </div>
      <div class="metric">
        <div class="label">平均相对误差</div>
        <div class="value">{payload['metrics']['mean_rel_error_pct']:.2f}%</div>
      </div>
      <div class="metric">
        <div class="label">最大相对误差</div>
        <div class="value">{payload['metrics']['max_rel_error_pct']:.2f}%</div>
      </div>
    </div>

    <div class="card">
      <h2>1. 当前状态</h2>
      <p>这份报告已经不再是 HEC-RAS readiness 检查，而是真实官方 HEC-RAS 6.6 示例项目的自动计算结果。当前外部引擎链已经打通，误差大是算法问题，不是“还没接好 HEC-RAS”。</p>
    </div>

    <div class="card">
      <h2>2. 核心指标</h2>
      <table>
        <tr><th>指标</th><th>数值</th></tr>
        <tr><td>真实 HEC-RAS 流量</td><td>{payload['metrics']['hec_flow_m3s']:.4f} m3/s</td></tr>
        <tr><td>HEC-RAS 上游水深</td><td>{payload['metrics']['hec_upstream_depth_m']:.4f} m</td></tr>
        <tr><td>Hydrostatic 上游水深</td><td>{payload['metrics']['hydrostatic_upstream_depth_m']:.4f} m</td></tr>
        <tr><td>平均绝对误差</td><td>{payload['metrics']['mean_abs_error_m']:.4f} m</td></tr>
        <tr><td>上游相对误差</td><td>{payload['metrics']['upstream_rel_error_pct']:.4f}%</td></tr>
        <tr><td>平均相对误差</td><td>{payload['metrics']['mean_rel_error_pct']:.4f}%</td></tr>
        <tr><td>最大相对误差</td><td>{payload['metrics']['max_rel_error_pct']:.4f}%</td></tr>
      </table>
    </div>

    <div class="card">
      <h2>3. 结果判断</h2>
      <p>这个官方样例是典型的混合流态与法线坡边界工况。HydroClaude 当前用下游定深近似来逼近 HEC-RAS，因此在该样例上出现大误差是合理暴露出来的真实缺口。它说明下一步需要补的是 <code>normal-depth / mixed-regime</code> 边界与更稳健的混合流态处理，而不是再修报表。</p>
    </div>

    <figure>
      <img src="{_asset_to_data_uri(steady_fig)}" alt="HEC-RAS 混合流态水面线">
      <figcaption>真实 HEC-RAS 水面线与 Hydrostatic 同几何近似对比。当前差异已经可直观看到。</figcaption>
    </figure>

    <figure>
      <img src="{_asset_to_data_uri(error_fig)}" alt="HEC-RAS 混合流态误差">
      <figcaption>误差纵剖面。这里反映的是当前算法能力差距，而不是外部链未打通。</figcaption>
    </figure>
  </div>
</body>
</html>
"""

    md_path.write_text(md, encoding="utf-8")
    html_path.write_text(html, encoding="utf-8")
    json_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    return {"md": md_path, "html": html_path, "json": json_path}


if __name__ == "__main__":
    result = generate_report()
    print(json.dumps({k: str(v) for k, v in result.items()}, ensure_ascii=False, indent=2))
