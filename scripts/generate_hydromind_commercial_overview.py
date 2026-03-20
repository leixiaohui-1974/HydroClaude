"""Generate a HydroMind-style commercial benchmark overview report."""

from __future__ import annotations

import argparse
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
    return "image/svg+xml" if path.suffix.lower() == ".svg" else "image/png"


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
    hardycross_json = _read_json(REPORTS_DIR / "hydromind_hardycross_simulation_report.json")
    swmm_json = _read_json(REPORTS_DIR / "hydromind_swmm_simulation_report.json")

    god = godunov_json["metrics"]
    hyd = hydrostatic_json["metrics"]
    har = hardycross_json["metrics"]
    swm = swmm_json["metrics"]

    figures = {
        "godunov_steady": _resolve_figure("figures/hydromind_godunov_steady_profile.svg"),
        "godunov_snapshots": _resolve_figure("figures/hydromind_godunov_dynamic_snapshots.svg"),
        "hydrostatic_steady": _resolve_figure(hydrostatic_json["figures"]["steady"]),
        "hydrostatic_snapshots": _resolve_figure(hydrostatic_json["figures"]["snapshots"]),
        "hardycross_topology": _resolve_figure(hardycross_json["figures"]["topology"]),
        "hardycross_comparison": _resolve_figure(hardycross_json["figures"]["comparison"]),
        "swmm_steady": _resolve_figure(swmm_json["figures"]["steady"]),
        "swmm_snapshots": _resolve_figure(swmm_json["figures"]["snapshots"]),
    }

    md_path = REPORTS_DIR / "hydromind_commercial_overview.md"
    html_path = REPORTS_DIR / "hydromind_commercial_overview.html"

    md = f"""# HydroMind商业软件对标总览

**生成时间**: {generated_at}

## 1. 问题描述

当前需要把 Godunov、Hydrostatic、HardyCross 三类求解器的商业软件对标结果统一到一个可人工核查的入口页，重点直接展示仿真结果、误差指标、图形证据和下一步诊断方向，而不是分散在测试日志里。

## 2. 解题思路

1. 读取 Godunov、Hydrostatic、HardyCross、SWMM 四份结构化结果。
2. 沿用 HydroMind 现有中文样式和图片内嵌策略，避免浏览器里继续出现看不见图或中文乱码。
3. 把明渠求解器的水面线、动态快照和过程线，以及 SWMM 真实明渠对标结果，与 HardyCross 的管网流量/水头对标统一放进一页。
4. 明确区分“验收级误差”和“证据链待补的诊断级误差”。

## 3. 核心结论

| 求解器 | 参考软件 | 关键误差 | 收敛/守恒 | 当前结论 |
|---|---|---:|---|---|
| Godunov | HEC-RAS / GVF 参考 | 上游 {god['upstream_error_vs_reference_pct']:.4f}% | `OEJI={god['odd_even_jaggedness_index']:.6f}`，质量误差 {god['mass_error_pct']:.4f}% | 已达到高精度，水面线平滑 |
| Hydrostatic | HEC-RAS / SteadyProfile | 上游 {hyd['upstream_error_vs_reference_pct']:.4f}% | 平均误差 {hyd['average_error_vs_reference_pct']:.4f}%，流量误差 {hyd['mean_discharge_error_pct']:.4f}% | 已恢复到约 1% 量级 |
| HardyCross | EPANET | 最大流量误差 {har['max_flow_error_ls']:.4f} L/s | 迭代 {har['iterations']} 次，连续方程残差 {har['junction_balance_error_ls']:.4f} L/s | 流量结果可信，水头证据链待补 |
| SWMM 动态波明渠 | SWMM / SteadyProfile | 上游 {swm['swmm_vs_steady']['upstream_rel_error_pct']:.4f}% | 最大满流比 {swm['swmm_max_link_fullness_ratio']:.4f}，Fr_max {swm['swmm_max_link_froude']:.4f} | 已形成真实明渠外部对标链 |
"""

    html = f"""<!DOCTYPE html>
<html lang="zh-CN">
<head>
  <meta charset="utf-8">
  <title>HydroMind商业软件对标总览</title>
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
      padding: 30px 26px 54px;
    }}
    .meta {{
      color: #52606d;
      margin-bottom: 24px;
    }}
    h1, h2, h3 {{
      color: #0b3c49;
    }}
    .hero {{
      display: grid;
      grid-template-columns: repeat(4, 1fr);
      gap: 14px;
      margin: 22px 0;
    }}
    .metric {{
      background: linear-gradient(135deg, #eff8f6 0%, #fff8ea 100%);
      border-radius: 14px;
      padding: 16px 18px;
      border: 1px solid #d7e6df;
    }}
    .metric .label {{
      color: #52606d;
      font-size: 14px;
    }}
    .metric .value {{
      font-size: 28px;
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
    th {{
      background: #eef6f7;
    }}
    .links a {{
      display: inline-block;
      margin-right: 16px;
      margin-bottom: 8px;
      color: #0b7285;
      text-decoration: none;
      font-weight: 600;
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
    <h1>HydroMind商业软件对标总览</h1>
    <div class="meta">生成时间: {generated_at}</div>

    <div class="hero">
      <div class="metric">
        <div class="label">Godunov 上游误差</div>
        <div class="value">{god['upstream_error_vs_reference_pct']:.4f}%</div>
      </div>
      <div class="metric">
        <div class="label">Hydrostatic 上游误差</div>
        <div class="value">{hyd['upstream_error_vs_reference_pct']:.4f}%</div>
      </div>
      <div class="metric">
        <div class="label">HardyCross 最大流量误差</div>
        <div class="value">{har['max_flow_error_ls']:.4f} L/s</div>
      </div>
      <div class="metric">
        <div class="label">HardyCross 最大水头误差</div>
        <div class="value">{har['max_head_error_m']:.3f} m</div>
      </div>
      <div class="metric">
        <div class="label">SWMM vs SteadyProfile 平均误差</div>
        <div class="value">{swm['swmm_vs_steady']['mean_rel_error_pct']:.4f}%</div>
      </div>
    </div>

    <div class="card">
      <h2>1. 问题描述</h2>
      <p>本页把核心求解器的商业软件对标结果统一为一个 HydroMind 人工核查入口，直接回答三个问题：当前算得对不对，图形上是否可信，还剩哪些精度问题需要继续修复。</p>
    </div>

    <div class="card">
      <h2>2. 解题思路</h2>
      <ul>
        <li>Godunov 和 Hydrostatic 保留完整明渠水面线、动态快照和过程线，用于判断稳态精度与时程平滑性。</li>
        <li>HardyCross 走 HydroClaude 的网络分析工具链，把 EPANET 3 节点结果转成可核查的流量、水头和连续性指标。</li>
        <li>SWMM 动态波链路专门负责真实明渠/自由液面对标，补上 EPANET 无法覆盖的明渠场景。</li>
        <li>图形统一使用内嵌资源，明渠折线优先 SVG，避免浏览器里继续出现图片丢失和中文显示异常。</li>
        <li>对于证据链尚未闭合的存档指标，在页面上明确标成诊断项，不冒充验收级真值。</li>
      </ul>
    </div>

    <div class="card">
      <h2>3. 核心结论</h2>
      <table>
        <tr><th>求解器</th><th>参考</th><th>关键误差</th><th>收敛/守恒</th><th>当前结论</th><th>详情页</th></tr>
        <tr>
          <td>Godunov</td>
          <td>HEC-RAS / GVF 参考</td>
          <td>上游 {god['upstream_error_vs_reference_pct']:.4f}%<br>平均 {god['average_error_vs_reference_pct']:.4f}%</td>
          <td><code>OEJI={god['odd_even_jaggedness_index']:.6f}</code><br>质量误差 {god['mass_error_pct']:.4f}%</td>
          <td>高精度，水面线已恢复平滑</td>
          <td><a href="hydromind_godunov_simulation_report.html">打开</a></td>
        </tr>
        <tr>
          <td>Hydrostatic</td>
          <td>HEC-RAS / SteadyProfile</td>
          <td>上游 {hyd['upstream_error_vs_reference_pct']:.4f}%<br>平均 {hyd['average_error_vs_reference_pct']:.4f}%</td>
          <td>流量误差 {hyd['mean_discharge_error_pct']:.4f}%<br><code>Fr_max={hyd['max_steady_froude']:.3f}</code></td>
          <td>已恢复到约 1% 精度量级</td>
          <td><a href="hydromind_hydrostatic_simulation_report.html">打开</a></td>
        </tr>
        <tr>
          <td>HardyCross</td>
          <td>EPANET 3 节点真实计算</td>
          <td>最大流量误差 {har['max_flow_error_ls']:.4f} L/s<br>最大水头误差 {har['max_head_error_m']:.3f} m</td>
          <td>迭代 {har['iterations']} 次<br>节点连续残差 {har['junction_balance_error_ls']:.4f} L/s</td>
          <td>已用真实 EPANET 计算复核；当前主算法与 EPANET 基本对齐，历史 fixture 退为诊断项</td>
          <td><a href="hydromind_hardycross_simulation_report.html">打开</a></td>
        </tr>
        <tr>
          <td>SWMM 动态波明渠</td>
          <td>SWMM / SteadyProfile</td>
          <td>上游 {swm['swmm_vs_steady']['upstream_rel_error_pct']:.4f}%<br>平均 {swm['swmm_vs_steady']['mean_rel_error_pct']:.4f}%</td>
          <td>满流比 {swm['swmm_max_link_fullness_ratio']:.4f}<br><code>Fr_max={swm['swmm_max_link_froude']:.4f}</code></td>
          <td>已形成真实明渠外部参考链；Godunov 与 SWMM 高度对齐</td>
          <td><a href="hydromind_swmm_simulation_report.html">打开</a></td>
        </tr>
      </table>
    </div>

    <div class="card">
      <h2>4. 图形核查</h2>
      <div class="fig-grid">
        <figure>
          <img src="{_asset_to_data_uri(figures['godunov_steady'])}" alt="Godunov 稳态水面线">
          <figcaption>图1. Godunov 稳态水面线与参考剖面对比。</figcaption>
        </figure>
        <figure>
          <img src="{_asset_to_data_uri(figures['hydrostatic_steady'])}" alt="Hydrostatic 稳态水面线">
          <figcaption>图2. Hydrostatic 稳态水面线与参考剖面对比。</figcaption>
        </figure>
        <figure>
          <img src="{_asset_to_data_uri(figures['godunov_snapshots'])}" alt="Godunov 动态快照">
          <figcaption>图3. Godunov 动态水面线快照，用于人工核查是否存在残余振荡。</figcaption>
        </figure>
        <figure>
          <img src="{_asset_to_data_uri(figures['hydrostatic_snapshots'])}" alt="Hydrostatic 动态快照">
          <figcaption>图4. Hydrostatic 动态水面线快照，用于核查收敛过程和平滑性。</figcaption>
        </figure>
        <figure>
          <img src="{_asset_to_data_uri(figures['hardycross_topology'])}" alt="HardyCross 管网拓扑">
          <figcaption>图5. HardyCross 管网拓扑、节点水头与管段流量。</figcaption>
        </figure>
        <figure>
          <img src="{_asset_to_data_uri(figures['hardycross_comparison'])}" alt="HardyCross 对比图">
          <figcaption>图6. HardyCross 与 EPANET 的流量和节点水头对比。</figcaption>
        </figure>
        <figure>
          <img src="{_asset_to_data_uri(figures['swmm_steady'])}" alt="SWMM 明渠稳态对比">
          <figcaption>图7. SWMM 动态波明渠最终水面线与 SteadyProfile、Hydrostatic、Godunov 对比。</figcaption>
        </figure>
        <figure>
          <img src="{_asset_to_data_uri(figures['swmm_snapshots'])}" alt="SWMM 明渠动态快照">
          <figcaption>图8. SWMM 动态水面线快照，用于人工核查收敛过程和自由液面形态。</figcaption>
        </figure>
      </div>
    </div>

    <div class="card">
      <h2>5. 人工核查重点</h2>
      <ul>
        <li>Godunov: 重点看稳态线是否继续保持单调平滑，动态快照是否还存在局部锯齿或相邻单元交替振荡。</li>
        <li>Hydrostatic: 重点看稳态剖面与参考线的整体平行性，以及动态快照是否存在非物理突变。</li>
        <li>HardyCross: 当前先以流量守恒和管段流量精度为主验收；节点水头继续作为证据链待补的诊断项跟踪。</li>
        <li>SWMM 明渠: 重点看是否保持非满流，以及 Godunov / Hydrostatic 与真实动态波结果的贴合程度。</li>
      </ul>
    </div>

    <div class="card links">
      <h2>6. 核查入口</h2>
      <a href="hydromind_simulation_overview.html">仿真总览页</a>
      <a href="hydromind_godunov_simulation_report.html">Godunov 详情页</a>
      <a href="hydromind_hydrostatic_simulation_report.html">Hydrostatic 详情页</a>
      <a href="hydromind_hydrostatic_benchmark_reconciliation.html">Hydrostatic 证据链附录</a>
      <a href="hydromind_hardycross_simulation_report.html">HardyCross 详情页</a>
      <a href="hydromind_swmm_simulation_report.html">SWMM 明渠详情页</a>
      <a href="hydromind_hecras_status_report.html">HEC-RAS 集成状态页</a>
    </div>
  </div>
</body>
</html>
"""

    md_path.write_text(md, encoding="utf-8")
    html_path.write_text(html, encoding="utf-8")

    return {"md": md_path, "html": html_path}


def main() -> int:
    parser = argparse.ArgumentParser(description="Generate HydroMind commercial benchmark overview")
    parser.add_argument("--open", action="store_true", help="Open the generated HTML report in Chrome.")
    args = parser.parse_args()

    result = generate_overview()
    print(json.dumps({"md": str(result["md"]), "html": str(result["html"])}, ensure_ascii=False, indent=2))

    if args.open:
        import subprocess

        subprocess.Popen(["cmd", "/c", "start", "", str(result["html"])])
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
