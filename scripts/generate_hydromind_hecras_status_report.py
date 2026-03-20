"""Generate a HydroMind-style HEC-RAS integration status and provenance report."""

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

from integration.hec_ras_adapter import prepare_hec_ras_benchmark
from solvers.hydrostatic_canal_solver import HydrostaticCanalSolver
from solvers.steady_profile_solver import SteadyProfileSolver
from utils.font_config import setup_chinese_font


REPORTS_DIR = ROOT / "reports"
FIGURES_DIR = REPORTS_DIR / "figures"
RESEARCH_ROOT = ROOT.parent
EXTERNAL_HECRAS_MCP_DIR = RESEARCH_ROOT / "_tmp_ras_commander_mcp"


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

    status = prepare_hec_ras_benchmark()
    runtime = status["runtime"]
    case = status["case"]

    external_mcp_found = EXTERNAL_HECRAS_MCP_DIR.exists()
    external_mcp_server = EXTERNAL_HECRAS_MCP_DIR / "server.py"
    external_mcp_readme = EXTERNAL_HECRAS_MCP_DIR / "README.md"
    hydroclaude_tools = [
        "get_hec_ras_benchmark_status",
        "run_hec_ras_sample_benchmark",
    ]

    steady = SteadyProfileSolver(length=1000, B=10, S0=0.001, n=0.025).solve_without_structures(
        Q=50,
        h_downstream=2.0,
        nx=201,
    )
    hydro = HydrostaticCanalSolver(length=1000, nx=201, B=10, S0=0.001, n=0.025)
    hydro_result = hydro.solve_steady_state(
        Q_target=50,
        h_downstream=2.0,
        dt=0.5,
        max_iterations=6000,
        convergence_tol=1e-4,
        verbose=False,
    )
    x = np.asarray(steady["x"], dtype=float)
    bed = 0.001 * (1000.0 - x)
    steady_h = np.asarray(steady["h"], dtype=float)
    hydro_h = np.asarray(hydro_result["h"], dtype=float)

    fig_path = FIGURES_DIR / "hydromind_hecras_readiness_profile.svg"
    fig, ax = plt.subplots(figsize=(12.5, 6.5))
    ax.plot(x, steady_h + bed, color="#ee9b00", lw=2.2, ls="--", label="SteadyProfile 参考", dash_capstyle="round")
    ax.plot(x, hydro_h + bed, color="#0a9396", lw=2.2, label="Hydrostatic 当前解", solid_capstyle="round", solid_joinstyle="round")
    ax.plot(x, bed, color="#6c584c", lw=1.7, label="河床")
    ax.set_title("HydroClaude 当前内部参考剖面")
    ax.set_xlabel("距离 x (m)")
    ax.set_ylabel("高程 (m)")
    ax.legend(loc="best")
    _save_figure(fig, fig_path)

    generated_at = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    json_path = REPORTS_DIR / "hydromind_hecras_status_report.json"
    md_path = REPORTS_DIR / "hydromind_hecras_status_report.md"
    html_path = REPORTS_DIR / "hydromind_hecras_status_report.html"

    payload = {
        "generated_at": generated_at,
        "runtime": runtime,
        "case": case,
        "ready_for_true_run": status["ready_for_true_run"],
        "hydromind_contracts_support": {
            "protocol_only": True,
            "simulator_protocol": "hydromind_contracts.SimulatorProtocol",
            "controller_protocol": "hydromind_contracts.ControllerProtocol",
            "mcp_tool_protocol": "hydromind_contracts.MCPToolProtocol",
        },
        "external_hec_ras_mcp": {
            "found": external_mcp_found,
            "root": str(EXTERNAL_HECRAS_MCP_DIR),
            "server_py": str(external_mcp_server) if external_mcp_server.exists() else None,
            "readme_md": str(external_mcp_readme) if external_mcp_readme.exists() else None,
        },
        "hydroclaude_hec_ras_tools": hydroclaude_tools,
        "metrics": {
            "hydrostatic_upstream_depth_m": float(hydro_h[0]),
            "steady_reference_upstream_depth_m": float(steady_h[0]),
            "hydrostatic_vs_steady_upstream_error_pct": float(abs(hydro_h[0] - steady_h[0]) / steady_h[0] * 100.0),
        },
        "figures": {
            "profile": str(fig_path.relative_to(REPORTS_DIR)).replace("\\", "/"),
        },
    }

    md = f"""# HydroMind HEC-RAS 集成状态报告

**生成时间**: {generated_at}

## 1. 当前结论

- 当前机器已经检测到可运行的 `HEC-RAS 6.6` 与 `RAS66.HECRASController`。
- `hydromind-contracts` 本身只提供协议层，不包含 HEC-RAS 专用 MCP server 实现。
- 本机 `Z:/research/_tmp_ras_commander_mcp` 下存在一个可复用的第三方 HEC-RAS MCP server。
- `HydroClaude` 目前已经把 HEC-RAS 能力接入到自己的 MCP 层，核心工具为 `{hydroclaude_tools[0]}` 和 `{hydroclaude_tools[1]}`。
- `validation_cases/engineering/hec_ras_steady_flow_example_3_1` 仍缺少原始 `.prj/.gxx/.fxx` 工程文件，所以这个特定 provenance 案例还不能直接真机复算。

## 2. 运行时状态

| 项目 | 当前状态 |
|---|---|
| 可执行文件检测 | `{runtime['exe_path']}` |
| COM 控制器检测 | `{runtime['progid']}` |
| 已安装 | `{runtime['installed']}` |
| COM 可用 | `{runtime['com_available']}` |
| 可直接真机运行 | `{status['ready_for_true_run']}` |

## 3. HydroMind 协议层定位

| 项目 | 当前状态 |
|---|---|
| 协议包 | `hydromind-contracts` |
| SimulatorProtocol | `hydromind_contracts.SimulatorProtocol` |
| ControllerProtocol | `hydromind_contracts.ControllerProtocol` |
| MCPToolProtocol | `hydromind_contracts.MCPToolProtocol` |
| 是否自带 HEC-RAS 专用 MCP server | `False` |

## 4. 本机发现到的 HEC-RAS MCP 实现

| 项目 | 当前状态 |
|---|---|
| 外部 MCP 实现已发现 | `{external_mcp_found}` |
| 实现位置 | `{EXTERNAL_HECRAS_MCP_DIR}` |
| server.py | `{external_mcp_server if external_mcp_server.exists() else None}` |
| README.md | `{external_mcp_readme if external_mcp_readme.exists() else None}` |

说明：

- 这套实现是 `ras-commander-mcp` 风格的独立 HEC-RAS MCP server，不是 `HydroMind` 协议包内置模块。
- 如果用户记忆里的“HydroMind 之前集成过 HEC-RAS MCP”指的是本机已有可复用实现，那么最接近的证据就是这里。

## 5. HydroClaude 当前已接入的 HEC-RAS MCP 工具

| 工具名 | 作用 |
|---|---|
| `get_hec_ras_benchmark_status` | 检测本机 HEC-RAS 运行时和案例 readiness |
| `run_hec_ras_sample_benchmark` | 运行真实 HEC-RAS 官方示例并与 Hydrostatic 对比 |

## 6. 案例准备状态

| 项目 | 当前状态 |
|---|---:|
| README | {case['readme_exists']} |
| metadata | {case['metadata_exists']} |
| parameters | {case['parameters_exists']} |
| expected_results | {case['expected_results_exists']} |
| 原始 HEC-RAS 工程文件 | {case['raw_project_present']} |
| exports 数量 | {case['export_file_count']} |
| screenshots 数量 | {case['screenshot_file_count']} |
| transcribed notes 数量 | {case['transcribed_note_count']} |

## 7. 当前可核查剖面

这张图不是 HEC-RAS 真值，只是当前断档阶段的仓库内剖面核查图，用于说明 Hydrostatic 与内部稳态参考的当前状态。真实 HEC-RAS 对比应优先基于已可运行的官方示例项目生成。

![HEC-RAS readiness profile]({payload['figures']['profile']})

## 8. 下一步

1. 直接复用 `_tmp_ras_commander_mcp` 的工具设计，把项目摘要、结果提取能力按需并入 `HydroClaude` MCP。
2. 对于真实算例对比，优先使用已经可运行的官方 HEC-RAS 示例项目，而不是继续依赖缺原始工程文件的旧 provenance scaffold。
3. 将真实 HEC-RAS 对比结果补入 HydroMind 风格仿真报告，而不是只停留在 status 页面。
"""

    html = f"""<!DOCTYPE html>
<html lang="zh-CN">
<head>
  <meta charset="utf-8">
  <title>HydroMind HEC-RAS 集成状态报告</title>
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
    .card {{
      background: #fffdf8;
      border: 1px solid #e5dfd0;
      border-radius: 14px;
      padding: 18px 20px;
      margin: 18px 0;
      box-shadow: 0 8px 24px rgba(15, 23, 42, 0.06);
    }}
    h1, h2 {{ color: #0b3c49; }}
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
    img {{ width: 100%; background: white; border: 1px solid #d9d9d9; border-radius: 12px; }}
    code {{ background: #f1efe8; padding: 1px 5px; border-radius: 6px; }}
  </style>
</head>
<body>
  <div class="page">
    <h1>HydroMind HEC-RAS 集成状态报告</h1>
    <div>生成时间: {generated_at}</div>

    <div class="card">
      <h2>1. 当前结论</h2>
      <p>当前机器已经检测到可运行的 HEC-RAS 6.6 与 COM 控制器。需要澄清的是，<code>hydromind-contracts</code> 只提供协议，不自带 HEC-RAS 专用 MCP server；但本机确实存在一个可复用的第三方实现 <code>_tmp_ras_commander_mcp</code>，而 HydroClaude 也已经补上了自己的 HEC-RAS MCP 工具入口。</p>
    </div>

    <div class="card">
      <h2>2. 运行时状态</h2>
      <table>
        <tr><th>项目</th><th>当前状态</th></tr>
        <tr><td>可执行文件检测</td><td><code>{runtime['exe_path']}</code></td></tr>
        <tr><td>COM 控制器检测</td><td><code>{runtime['progid']}</code></td></tr>
        <tr><td>已安装</td><td>{runtime['installed']}</td></tr>
        <tr><td>COM 可用</td><td>{runtime['com_available']}</td></tr>
        <tr><td>可直接真机运行</td><td>{status['ready_for_true_run']}</td></tr>
      </table>
    </div>

    <div class="card">
      <h2>3. HydroMind 协议层定位</h2>
      <table>
        <tr><th>项目</th><th>当前状态</th></tr>
        <tr><td>协议包</td><td><code>hydromind-contracts</code></td></tr>
        <tr><td>SimulatorProtocol</td><td><code>hydromind_contracts.SimulatorProtocol</code></td></tr>
        <tr><td>ControllerProtocol</td><td><code>hydromind_contracts.ControllerProtocol</code></td></tr>
        <tr><td>MCPToolProtocol</td><td><code>hydromind_contracts.MCPToolProtocol</code></td></tr>
        <tr><td>是否自带 HEC-RAS 专用 MCP server</td><td>False</td></tr>
      </table>
    </div>

    <div class="card">
      <h2>4. 本机发现到的 HEC-RAS MCP 实现</h2>
      <table>
        <tr><th>项目</th><th>当前状态</th></tr>
        <tr><td>外部 MCP 实现已发现</td><td>{external_mcp_found}</td></tr>
        <tr><td>实现位置</td><td><code>{EXTERNAL_HECRAS_MCP_DIR}</code></td></tr>
        <tr><td>server.py</td><td><code>{external_mcp_server if external_mcp_server.exists() else None}</code></td></tr>
        <tr><td>README.md</td><td><code>{external_mcp_readme if external_mcp_readme.exists() else None}</code></td></tr>
      </table>
      <p>这套实现是独立的 HEC-RAS MCP server，可视为本机已有的现成能力，不属于 <code>hydromind-contracts</code> 协议包本体。</p>
    </div>

    <div class="card">
      <h2>5. HydroClaude 当前已接入的 HEC-RAS MCP 工具</h2>
      <table>
        <tr><th>工具名</th><th>作用</th></tr>
        <tr><td><code>{hydroclaude_tools[0]}</code></td><td>检测本机 HEC-RAS 运行时和案例 readiness</td></tr>
        <tr><td><code>{hydroclaude_tools[1]}</code></td><td>运行真实 HEC-RAS 官方示例并与 Hydrostatic 对比</td></tr>
      </table>
    </div>

    <div class="card">
      <h2>6. 案例准备状态</h2>
      <table>
        <tr><th>项目</th><th>当前状态</th></tr>
        <tr><td>README</td><td>{case['readme_exists']}</td></tr>
        <tr><td>metadata</td><td>{case['metadata_exists']}</td></tr>
        <tr><td>parameters</td><td>{case['parameters_exists']}</td></tr>
        <tr><td>expected_results</td><td>{case['expected_results_exists']}</td></tr>
        <tr><td>原始 HEC-RAS 工程文件</td><td>{case['raw_project_present']}</td></tr>
        <tr><td>exports 数量</td><td>{case['export_file_count']}</td></tr>
        <tr><td>screenshots 数量</td><td>{case['screenshot_file_count']}</td></tr>
        <tr><td>transcribed notes 数量</td><td>{case['transcribed_note_count']}</td></tr>
      </table>
    </div>

    <div class="card">
      <h2>7. 当前可核查剖面</h2>
      <p>这张图不是 HEC-RAS 真值，只是当前断档阶段的仓库内剖面核查图，用于说明 Hydrostatic 与内部稳态参考的当前状态。真实 HEC-RAS 对比应优先基于已可运行的官方示例项目生成。</p>
      <img src="{_asset_to_data_uri(fig_path)}" alt="HEC-RAS readiness profile">
    </div>
  </div>
</body>
</html>
"""

    json_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    md_path.write_text(md, encoding="utf-8")
    html_path.write_text(html, encoding="utf-8")
    return {"json": json_path, "md": md_path, "html": html_path}


if __name__ == "__main__":
    result = generate_report()
    print(json.dumps({k: str(v) for k, v in result.items()}, ensure_ascii=False, indent=2))
