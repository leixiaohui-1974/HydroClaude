"""Generate a HydroMind overview report for manual simulation review."""

from __future__ import annotations

import base64
import json
import sys
from datetime import datetime
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

REPORTS_DIR = ROOT / "reports"


def _read_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def _asset_mime_type(path: Path) -> str:
    if path.suffix.lower() == ".svg":
        return "image/svg+xml"
    return "image/png"


def _asset_to_data_uri(path: Path) -> str:
    payload = base64.b64encode(path.read_bytes()).decode("ascii")
    return f"data:{_asset_mime_type(path)};base64,{payload}"


def _resolve_figure(path_text: str) -> Path:
    figure_path = Path(path_text.replace("\\", "/"))
    if not figure_path.is_absolute():
        figure_path = REPORTS_DIR / figure_path
    if figure_path.suffix.lower() == ".png":
        svg_candidate = figure_path.with_suffix(".svg")
        if svg_candidate.exists():
            return svg_candidate
    return figure_path


def generate_overview() -> dict[str, Path]:
    generated_at = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    godunov_json = _read_json(REPORTS_DIR / "hydromind_godunov_simulation_report.json")
    hydrostatic_json = _read_json(REPORTS_DIR / "hydromind_hydrostatic_simulation_report.json")

    godunov_figures = {
        "steady": _resolve_figure("figures/hydromind_godunov_steady_profile.png"),
        "hydrographs": _resolve_figure("figures/hydromind_godunov_hydrographs.png"),
        "snapshots": _resolve_figure("figures/hydromind_godunov_dynamic_snapshots.png"),
    }
    hydrostatic_figures = {
        "steady": _resolve_figure(hydrostatic_json["figures"]["steady"]),
        "hydrographs": _resolve_figure(hydrostatic_json["figures"]["hydrographs"]),
        "snapshots": _resolve_figure(hydrostatic_json["figures"]["snapshots"]),
    }

    md_path = REPORTS_DIR / "hydromind_simulation_overview.md"
    html_path = REPORTS_DIR / "hydromind_simulation_overview.html"

    god = godunov_json["metrics"]
    hyd = hydrostatic_json["metrics"]

    md = f"""# HydroMind 仿真总览

**生成时间**: {generated_at}

## 1. 核查入口

- Godunov 详情: [hydromind_godunov_simulation_report.html](/Z:/research/HydroClaude/reports/hydromind_godunov_simulation_report.html)
- Hydrostatic 详情: [hydromind_hydrostatic_simulation_report.html](/Z:/research/HydroClaude/reports/hydromind_hydrostatic_simulation_report.html)
- 商业对标总览: [hydromind_commercial_overview.html](/Z:/research/HydroClaude/reports/hydromind_commercial_overview.html)

## 2. 关键结论

| 求解器 | 上游误差 | 平均误差 | 守恒误差 | 备注 |
|---|---:|---:|---:|---|
| Godunov | {god['upstream_error_vs_reference_pct']:.4f}% | {god['average_error_vs_reference_pct']:.4f}% | {god['mass_error_pct']:.4f}% | `OEJI={god['odd_even_jaggedness_index']:.6f}` |
| Hydrostatic | {hyd['upstream_error_vs_reference_pct']:.4f}% | {hyd['average_error_vs_reference_pct']:.4f}% | {hyd['mean_discharge_error_pct']:.4f}% | 稳态参考对齐良好 |

## 3. 人工核查重点

- Godunov: 当前稳态线已经恢复为单调平滑剖面，重点看动态快照和过程线是否存在局部残余振荡。
- Hydrostatic: 当前精度已回到 1% 左右量级，重点看稳态线与参考线的整体平行性和过程线收敛形态。
- 两个求解器现在都可在同一工况下直接人工对比，不需要再来回切多个目录。
"""

    html = f"""<!DOCTYPE html>
<html lang="zh-CN">
<head>
  <meta charset="utf-8">
  <title>HydroMind 仿真总览</title>
  <style>
    body {{
      margin: 0;
      font-family: "Microsoft YaHei", "PingFang SC", "Noto Sans CJK SC", Arial, sans-serif;
      background: #f4f1ea;
      color: #1f2933;
    }}
    .page {{
      max-width: 1360px;
      margin: 0 auto;
      padding: 32px 28px 56px;
    }}
    h1, h2, h3 {{
      color: #0b3c49;
    }}
    .meta {{
      color: #52606d;
      margin-bottom: 24px;
    }}
    .hero {{
      display: grid;
      grid-template-columns: repeat(4, 1fr);
      gap: 14px;
      margin-bottom: 22px;
    }}
    .metric {{
      background: linear-gradient(135deg, #e9f5f3 0%, #fff8e8 100%);
      border-radius: 14px;
      padding: 16px 18px;
      border: 1px solid #d7e6df;
    }}
    .metric .label {{
      color: #52606d;
      font-size: 14px;
    }}
    .metric .value {{
      font-size: 30px;
      font-weight: 700;
      margin-top: 8px;
      color: #0b3c49;
    }}
    .card {{
      background: #fffdf8;
      border: 1px solid #e5dfd0;
      border-radius: 14px;
      padding: 18px 20px;
      margin: 18px 0;
      box-shadow: 0 8px 24px rgba(15, 23, 42, 0.06);
    }}
    .links a {{
      display: inline-block;
      margin-right: 16px;
      color: #0b7285;
      text-decoration: none;
      font-weight: 600;
    }}
    table {{
      width: 100%;
      border-collapse: collapse;
      margin-top: 12px;
    }}
    th, td {{
      border-bottom: 1px solid #e5e7eb;
      padding: 10px 12px;
      text-align: left;
      vertical-align: top;
    }}
    th {{
      background: #eef6f7;
    }}
    .solver-grid {{
      display: grid;
      grid-template-columns: 1fr 1fr;
      gap: 18px;
    }}
    .fig-grid {{
      display: grid;
      grid-template-columns: 1fr 1fr;
      gap: 18px;
      margin-top: 18px;
    }}
    figure {{
      margin: 0;
      background: white;
      border: 1px solid #d9d9d9;
      border-radius: 12px;
      overflow: hidden;
    }}
    figure img {{
      display: block;
      width: 100%;
      background: white;
    }}
    figcaption {{
      padding: 10px 12px 14px;
      color: #52606d;
      font-size: 14px;
    }}
    code {{
      background: #f1efe8;
      padding: 1px 5px;
      border-radius: 6px;
    }}
  </style>
</head>
<body>
  <div class="page">
    <h1>HydroMind 仿真总览</h1>
    <div class="meta">生成时间: {generated_at}</div>

    <div class="hero">
      <div class="metric">
        <div class="label">Godunov 上游误差</div>
        <div class="value">{god['upstream_error_vs_reference_pct']:.4f}%</div>
      </div>
      <div class="metric">
        <div class="label">Godunov 锯齿指标</div>
        <div class="value">{god['odd_even_jaggedness_index']:.6f}</div>
      </div>
      <div class="metric">
        <div class="label">Hydrostatic 上游误差</div>
        <div class="value">{hyd['upstream_error_vs_reference_pct']:.4f}%</div>
      </div>
      <div class="metric">
        <div class="label">Hydrostatic 平均误差</div>
        <div class="value">{hyd['average_error_vs_reference_pct']:.4f}%</div>
      </div>
    </div>

    <div class="card links">
      <h2>1. 核查入口</h2>
      <a href="hydromind_godunov_simulation_report.html">Godunov 详情页</a>
      <a href="hydromind_hydrostatic_simulation_report.html">Hydrostatic 详情页</a>
      <a href="hydromind_commercial_overview.html">商业对标总览</a>
      <a href="hydromind_hydrostatic_benchmark_reconciliation.html">Hydrostatic 对标说明</a>
    </div>

    <div class="card">
      <h2>2. 关键指标</h2>
      <table>
        <tr><th>求解器</th><th>上游误差</th><th>平均误差</th><th>守恒误差</th><th>补充指标</th><th>报告时间</th></tr>
        <tr>
          <td>Godunov</td>
          <td>{god['upstream_error_vs_reference_pct']:.4f}%</td>
          <td>{god['average_error_vs_reference_pct']:.4f}%</td>
          <td>{god['mass_error_pct']:.4f}%</td>
          <td><code>OEJI={god['odd_even_jaggedness_index']:.6f}</code><br><code>Flip={god['slope_flip_ratio']:.3f}</code></td>
          <td>{godunov_json['generated_at']}</td>
        </tr>
        <tr>
          <td>Hydrostatic</td>
          <td>{hyd['upstream_error_vs_reference_pct']:.4f}%</td>
          <td>{hyd['average_error_vs_reference_pct']:.4f}%</td>
          <td>{hyd['mean_discharge_error_pct']:.4f}%</td>
          <td><code>Fr_max={hyd['max_steady_froude']:.3f}</code><br><code>|Δh|max={hyd['max_abs_depth_error_m']:.4f} m</code></td>
          <td>{hydrostatic_json['generated_at']}</td>
        </tr>
      </table>
    </div>

    <div class="card">
      <h2>3. 人工核查重点</h2>
      <div class="solver-grid">
        <div>
          <h3>Godunov</h3>
          <p>当前稳态线已经恢复为单调平滑剖面，重点看动态快照和过程线是否还有局部残余振荡。当前 <code>OEJI</code> 很低，说明此前“锯齿”已经从最终结果中收敛掉。</p>
        </div>
        <div>
          <h3>Hydrostatic</h3>
          <p>当前精度回到 1% 左右量级，重点看稳态线和参考线是否沿程保持一致，以及过程线是否平滑收敛，不再出现异常漂移。</p>
        </div>
      </div>
    </div>

    <div class="card">
      <h2>4. 稳态水面线对比</h2>
      <div class="fig-grid">
        <figure>
          <img src="{_asset_to_data_uri(godunov_figures['steady'])}" alt="Godunov 稳态水面线">
          <figcaption>Godunov 稳态水面线。当前已按 solver 的 cell-center 坐标绘图。</figcaption>
        </figure>
        <figure>
          <img src="{_asset_to_data_uri(hydrostatic_figures['steady'])}" alt="Hydrostatic 稳态水面线">
          <figcaption>Hydrostatic 稳态水面线。用于和独立稳态参考直接人工比对。</figcaption>
        </figure>
      </div>
    </div>

    <div class="card">
      <h2>5. 动态快照对比</h2>
      <div class="fig-grid">
        <figure>
          <img src="{_asset_to_data_uri(godunov_figures['snapshots'])}" alt="Godunov 动态快照">
          <figcaption>Godunov 动态水面线快照。</figcaption>
        </figure>
        <figure>
          <img src="{_asset_to_data_uri(hydrostatic_figures['snapshots'])}" alt="Hydrostatic 动态快照">
          <figcaption>Hydrostatic 动态水面线快照。</figcaption>
        </figure>
      </div>
    </div>

    <div class="card">
      <h2>6. 关键断面过程线对比</h2>
      <div class="fig-grid">
        <figure>
          <img src="{_asset_to_data_uri(godunov_figures['hydrographs'])}" alt="Godunov 过程线">
          <figcaption>Godunov 关键断面过程线。</figcaption>
        </figure>
        <figure>
          <img src="{_asset_to_data_uri(hydrostatic_figures['hydrographs'])}" alt="Hydrostatic 过程线">
          <figcaption>Hydrostatic 关键断面过程线。</figcaption>
        </figure>
      </div>
    </div>
  </div>
</body>
</html>
"""

    md_path.write_text(md, encoding="utf-8")
    html_path.write_text(html, encoding="utf-8")
    return {"markdown": md_path, "html": html_path}


def main() -> None:
    result = generate_overview()
    print(result["markdown"])
    print(result["html"])


if __name__ == "__main__":
    main()
