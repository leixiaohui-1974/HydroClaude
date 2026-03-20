"""Generate a HydroMind-style SI report for the real HEC-RAS Beaver Creek case."""

from __future__ import annotations

import base64
import json
import sys
import tempfile
import shutil
from datetime import datetime
from pathlib import Path

import h5py
import matplotlib
import numpy as np

matplotlib.use("Agg")
import matplotlib.pyplot as plt

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from integration.hec_ras_adapter import CFS_TO_M3S, FT_TO_M, get_hec_ras_compute_messages
from utils.font_config import setup_chinese_font


REPORTS_DIR = ROOT / "reports"
FIGURES_DIR = REPORTS_DIR / "figures"
PROJECT_DIR = REPORTS_DIR / "hec_ras_example_project" / "Example 2 - Beaver Creek"
PROJECT_NAME = "BEAVCREK"
PLAN_NUMBER = "01"


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


def _prepare_temp_project_copy() -> Path:
    """Run HEC-RAS on a temp copy to avoid mutating the source example project."""
    temp_root = Path(tempfile.gettempdir()) / "hydroclaude_hec_ras_runs"
    temp_root.mkdir(parents=True, exist_ok=True)
    target = temp_root / "beaver_creek_hydromind"
    if target.exists():
        shutil.rmtree(target, ignore_errors=True)
    shutil.copytree(PROJECT_DIR, target)
    return target


def _decode(value: bytes | str) -> str:
    return value.decode(errors="ignore").strip() if isinstance(value, bytes) else str(value).strip()


def _load_case_data() -> dict:
    run_dir = _prepare_temp_project_copy()
    prj_path = run_dir / f"{PROJECT_NAME}.prj"
    hdf_path = run_dir / f"{PROJECT_NAME}.p01.hdf"
    _run_current_plan(prj_path)

    with h5py.File(hdf_path, "r") as hdf:
        attrs = hdf["Geometry/Cross Sections/Attributes"][:]
        info = hdf["Geometry/Cross Sections/Station Elevation Info"][:]
        values = hdf["Geometry/Cross Sections/Station Elevation Values"][:]
        base = "Results/Steady/Output/Output Blocks/Base Output/Steady Profiles/Cross Sections"
        ws = hdf[f"{base}/Water Surface"][:]
        eg = hdf[f"{base}/Energy Grade"][:]
        flow = hdf[f"{base}/Flow"][:]
        names = hdf["Results/Steady/Output/Output Blocks/Base Output/Steady Profiles/Profile Names"][:]
        units = _decode(hdf.attrs.get("Units System", b""))

    profile_names = [_decode(item) for item in names]
    river_station_mile = np.asarray([float(_decode(item["RS"]).replace("*", "")) for item in attrs], dtype=float)
    river_station_km = river_station_mile * 1.609344
    river_station_km = river_station_km[::-1]

    min_bed_ft = []
    descriptions = []
    for item, (start, count) in zip(attrs, info):
        seg = values[start:start + count, 1]
        min_bed_ft.append(float(np.min(seg)))
        descriptions.append(_decode(item["Description"]))

    min_bed_ft = np.asarray(min_bed_ft, dtype=float)[::-1]
    ws_ft = np.asarray(ws, dtype=float)[:, ::-1]
    eg_ft = np.asarray(eg, dtype=float)[:, ::-1]
    flow_cfs = np.asarray(flow, dtype=float)[:, ::-1]

    return {
        "project_file": str(prj_path),
        "hdf_file": str(hdf_path),
        "run_dir": str(run_dir),
        "units_system": units,
        "profile_names": profile_names,
        "river_station_km": river_station_km.tolist(),
        "river_station_mile": river_station_mile[::-1].tolist(),
        "min_bed_m": (min_bed_ft * FT_TO_M).tolist(),
        "water_surface_m": (ws_ft * FT_TO_M).tolist(),
        "energy_grade_m": (eg_ft * FT_TO_M).tolist(),
        "flow_m3s": (flow_cfs * CFS_TO_M3S).tolist(),
        "descriptions": descriptions[::-1],
    }


def generate_report() -> dict[str, Path]:
    _style_plot()
    FIGURES_DIR.mkdir(parents=True, exist_ok=True)

    data = _load_case_data()
    compute_messages = get_hec_ras_compute_messages(data["run_dir"], PLAN_NUMBER)

    x = np.asarray(data["river_station_km"], dtype=float)
    bed = np.asarray(data["min_bed_m"], dtype=float)
    ws = np.asarray(data["water_surface_m"], dtype=float)
    flow = np.asarray(data["flow_m3s"], dtype=float)
    profile_names = data["profile_names"]

    profile_fig = FIGURES_DIR / "hydromind_hecras_beaver_profiles.svg"
    flow_fig = FIGURES_DIR / "hydromind_hecras_beaver_flows.svg"

    fig, ax = plt.subplots(figsize=(12.8, 6.8))
    colors = ["#005f73", "#0a9396", "#ee9b00"]
    for idx, name in enumerate(profile_names):
        ax.plot(x, ws[idx], lw=2.4, color=colors[idx % len(colors)], label=f"{name} 水面线")
    ax.plot(x, bed, lw=2.0, color="#6c584c", label="最低床面线")
    ax.set_title("HEC-RAS 官方 Beaver Creek 稳态回水结果")
    ax.set_xlabel("河道断面里程 (km)")
    ax.set_ylabel("高程 (m)")
    ax.legend(loc="best")
    _save_figure(fig, profile_fig)

    fig, ax = plt.subplots(figsize=(12.8, 4.8))
    for idx, name in enumerate(profile_names):
        ax.plot(x, flow[idx], lw=2.2, color=colors[idx % len(colors)], label=f"{name} 流量")
    ax.set_title("HEC-RAS 断面流量分布")
    ax.set_xlabel("河道断面里程 (km)")
    ax.set_ylabel("流量 (m3/s)")
    ax.legend(loc="best")
    _save_figure(fig, flow_fig)

    generated_at = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    md_path = REPORTS_DIR / "hydromind_hecras_beaver_report.md"
    html_path = REPORTS_DIR / "hydromind_hecras_beaver_report.html"
    json_path = REPORTS_DIR / "hydromind_hecras_beaver_report.json"

    max_ws = [float(np.max(ws[idx])) for idx in range(len(profile_names))]
    min_ws = [float(np.min(ws[idx])) for idx in range(len(profile_names))]
    mean_flow = [float(np.mean(flow[idx])) for idx in range(len(profile_names))]

    payload = {
        "generated_at": generated_at,
        "project_dir": str(PROJECT_DIR),
        "project_file": data["project_file"],
        "hdf_file": data["hdf_file"],
        "run_dir": data["run_dir"],
        "units_system_source": data["units_system"],
        "report_units": {
            "distance": "km",
            "elevation": "m",
            "flow": "m3/s",
        },
        "profile_names": profile_names,
        "summary_metrics": [
            {
                "profile": name,
                "mean_flow_m3s": mean_flow[idx],
                "max_water_surface_m": max_ws[idx],
                "min_water_surface_m": min_ws[idx],
            }
            for idx, name in enumerate(profile_names)
        ],
        "compute_messages_preview": compute_messages.get("messages_preview", []),
        "figures": {
            "profiles": str(profile_fig.relative_to(REPORTS_DIR)).replace("\\", "/"),
            "flows": str(flow_fig.relative_to(REPORTS_DIR)).replace("\\", "/"),
        },
    }

    table_rows = "\n".join(
        f"| {name} | {mean_flow[idx]:.4f} | {max_ws[idx]:.4f} | {min_ws[idx]:.4f} |"
        for idx, name in enumerate(profile_names)
    )
    preview_lines = "\n".join(f"- {line}" for line in payload["compute_messages_preview"][:8])

    md = f"""# HydroMind仿真结果报告: HEC-RAS 官方 Beaver Creek 稳态回水样例

**生成时间**: {generated_at}

## 1. 问题描述

本报告直接调用本机 `HEC-RAS 6.6` 对官方 `Example 2 - Beaver Creek` 的 `p01 Press/Weir Method` 方案进行真实计算，并从结果 HDF 中提取稳态断面水面线。原始工程使用的是 `US Customary`，本报告统一换算为国际单位制。

## 2. 当前结果

| 工况 | 平均流量 (m3/s) | 最高水面高程 (m) | 最低水面高程 (m) |
|---|---:|---:|---:|
{table_rows}

## 3. 计算链路证据

{preview_lines}

## 4. 图形证据

![Beaver Creek 三工况水面线]({payload['figures']['profiles']})

![Beaver Creek 断面流量分布]({payload['figures']['flows']})
"""

    html_rows = "\n".join(
        f"<tr><td>{name}</td><td>{mean_flow[idx]:.4f}</td><td>{max_ws[idx]:.4f}</td><td>{min_ws[idx]:.4f}</td></tr>"
        for idx, name in enumerate(profile_names)
    )
    html_msgs = "\n".join(f"<li>{line}</li>" for line in payload["compute_messages_preview"][:8])

    html = f"""<!DOCTYPE html>
<html lang="zh-CN">
<head>
  <meta charset="utf-8">
  <title>HydroMind HEC-RAS Beaver Creek 稳态回水样例</title>
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
      grid-template-columns: repeat(3, 1fr);
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
    .value {{ font-size: 26px; font-weight: 700; margin-top: 8px; color: #0b3c49; }}
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
    code {{ background: #f1efe8; padding: 1px 5px; border-radius: 6px; }}
  </style>
</head>
<body>
  <div class="page">
    <h1>HydroMind仿真结果报告: HEC-RAS 官方 Beaver Creek 稳态回水样例</h1>
    <div>生成时间: {generated_at}</div>

    <div class="hero">
      <div class="metric">
        <div class="label">源工程单位</div>
        <div class="value">{payload['units_system_source']}</div>
      </div>
      <div class="metric">
        <div class="label">报告距离单位</div>
        <div class="value">km</div>
      </div>
      <div class="metric">
        <div class="label">报告流量单位</div>
        <div class="value">m3/s</div>
      </div>
    </div>

    <div class="card">
      <h2>1. 当前状态</h2>
      <p>这份报告展示的是 HEC-RAS 官方 <code>Example 2 - Beaver Creek</code> 在本机上的真实稳态计算结果，不是夹具或手工录入值。工程源单位为 <code>US Customary</code>，但报告输出已全部换算为国际单位制。</p>
    </div>

    <div class="card">
      <h2>2. 核心指标</h2>
      <table>
        <tr><th>工况</th><th>平均流量 (m3/s)</th><th>最高水面高程 (m)</th><th>最低水面高程 (m)</th></tr>
        {html_rows}
      </table>
    </div>

    <div class="card">
      <h2>3. 计算链路证据</h2>
      <ul>
        {html_msgs}
      </ul>
    </div>

    <figure>
      <img src="{_asset_to_data_uri(profile_fig)}" alt="Beaver Creek 三工况水面线">
      <figcaption>三条设计工况的水面线与最低床面线。全部已换算为国际单位制。</figcaption>
    </figure>

    <figure>
      <img src="{_asset_to_data_uri(flow_fig)}" alt="Beaver Creek 断面流量分布">
      <figcaption>三条设计工况在断面上的流量分布。稳态计算下沿程基本守恒。</figcaption>
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
