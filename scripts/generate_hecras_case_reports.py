"""Generate per-case HydroMind-style reports for HEC-RAS official examples."""

from __future__ import annotations

import argparse
import base64
import json
import re
import sys
from collections import defaultdict
from datetime import datetime
from pathlib import Path
from typing import Any

import h5py
import matplotlib
import numpy as np

matplotlib.use("Agg")
import matplotlib.pyplot as plt

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from integration.hec_ras_adapter import CFS_TO_M3S, FT_TO_M, summarize_hec_ras_project
from utils.font_config import setup_chinese_font


REPORTS_DIR = ROOT / "reports"
CASE_DIR = REPORTS_DIR / "hecras_cases"


def _style_plot() -> None:
    setup_chinese_font()
    plt.rcParams["figure.figsize"] = (12, 6)
    plt.rcParams["axes.grid"] = True
    plt.rcParams["grid.alpha"] = 0.24
    plt.rcParams["axes.spines.top"] = False
    plt.rcParams["axes.spines.right"] = False


def _save_figure(fig: plt.Figure, path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fig.tight_layout()
    fig.savefig(path, bbox_inches="tight")
    plt.close(fig)


def _asset_to_data_uri(path: Path) -> str:
    mime = "image/svg+xml" if path.suffix.lower() == ".svg" else "image/png"
    return f"data:{mime};base64,{base64.b64encode(path.read_bytes()).decode('ascii')}"


def _slugify(text: str) -> str:
    cleaned = re.sub(r"[^A-Za-z0-9]+", "_", text).strip("_").lower()
    return cleaned or "case"


def _parse_chunk_range(path: Path) -> tuple[int, int] | None:
    match = re.search(r"chunk_(\d+)_(\d+)\.json$", path.name)
    if not match:
        return None
    return int(match.group(1)), int(match.group(2))


def _select_record_paths(pattern: str) -> list[Path]:
    paths = sorted(REPORTS_DIR.glob(pattern))
    ranges = {path: _parse_chunk_range(path) for path in paths}
    filtered: list[Path] = []
    for path in paths:
        current = ranges[path]
        if current is None:
            filtered.append(path)
            continue
        start, end = current
        contained = False
        for other, other_range in ranges.items():
            if other == path or other_range is None:
                continue
            other_start, other_end = other_range
            if other_start <= start and other_end >= end and (other_start, other_end) != (start, end):
                contained = True
                break
        if not contained:
            filtered.append(path)
    return filtered


def _load_records(pattern: str) -> list[dict[str, Any]]:
    records: dict[str, dict[str, Any]] = {}
    for path in _select_record_paths(pattern):
        payload = json.loads(path.read_text(encoding="utf-8"))
        for record in payload.get("records", []):
            item = dict(record)
            item["_source_json"] = path.name
            records[record["project_name"]] = item
    return sorted(records.values(), key=lambda item: (item.get("category", ""), item["project_name"]))


def _unit_system(project_file: Path | None) -> str:
    if not project_file or not project_file.exists():
        return "english"
    text = project_file.read_text(encoding="utf-8", errors="ignore").lower()
    if "si units" in text:
        return "si"
    return "english"


def _length_factor(unit_system: str) -> float:
    return 1.0 if unit_system == "si" else FT_TO_M


def _flow_factor(unit_system: str) -> float:
    return 1.0 if unit_system == "si" else CFS_TO_M3S


def _decode_text_array(arr: np.ndarray) -> list[str]:
    values = []
    for item in arr:
        if isinstance(item, bytes):
            values.append(item.decode("utf-8", errors="ignore").strip())
        else:
            values.append(str(item).strip())
    return values


def _decode_station_attrs(arr: np.ndarray) -> tuple[np.ndarray, list[str], list[str], list[str]]:
    stations = []
    labels = []
    rivers = []
    reaches = []
    for row in arr:
        raw_station = row["Station"]
        station_text = raw_station.decode("utf-8", errors="ignore").strip() if isinstance(raw_station, bytes) else str(raw_station).strip()
        try:
            stations.append(float(station_text))
        except Exception:
            stations.append(float("nan"))
        river = row["River"].decode("utf-8", errors="ignore").strip() if isinstance(row["River"], bytes) else str(row["River"]).strip()
        reach = row["Reach"].decode("utf-8", errors="ignore").strip() if isinstance(row["Reach"], bytes) else str(row["Reach"]).strip()
        rivers.append(river)
        reaches.append(reach)
        labels.append(f"{river} / {reach} / RS {station_text}")
    return np.asarray(stations, dtype=float), labels, rivers, reaches


def _grouped_order(stations: np.ndarray, rivers: list[str], reaches: list[str]) -> np.ndarray:
    groups: dict[tuple[str, str], list[int]] = defaultdict(list)
    group_order: list[tuple[str, str]] = []
    for idx, key in enumerate(zip(rivers, reaches)):
        if key not in groups:
            group_order.append(key)
        groups[key].append(idx)
    ordered: list[int] = []
    for key in group_order:
        indices = sorted(groups[key], key=lambda item: np.nan_to_num(stations[item], nan=-1.0), reverse=True)
        ordered.extend(indices)
    return np.asarray(ordered, dtype=int)


def _build_profile_axis(stations_m: np.ndarray, rivers: list[str], reaches: list[str]) -> tuple[np.ndarray, list[str]]:
    x = np.zeros(len(stations_m), dtype=float)
    segment_labels: list[str] = []
    offset = 0.0
    start = 0
    while start < len(stations_m):
        key = (rivers[start], reaches[start])
        end = start
        while end < len(stations_m) and (rivers[end], reaches[end]) == key:
            end += 1
        segment = np.asarray(stations_m[start:end], dtype=float)
        reference = float(np.nanmax(segment)) if segment.size else 0.0
        local_x = reference - segment
        if local_x.size:
            x[start:end] = offset + local_x
            offset = float(x[end - 1]) + max(float(np.nanmax(local_x)) * 0.06, 40.0)
        segment_labels.append(" / ".join(key))
        start = end
    return x, segment_labels


def _decode_bytes(value: Any) -> str:
    if isinstance(value, bytes):
        return value.decode("utf-8", errors="ignore").strip()
    return str(value).strip()


def _polyline_vertices(info: np.ndarray, parts: np.ndarray, points: np.ndarray, index: int) -> np.ndarray:
    point_start, point_count, part_start, part_count = [int(v) for v in info[index]]
    if point_count <= 0:
        return np.empty((0, 2), dtype=float)
    part_rows = parts[part_start:part_start + max(part_count, 1)]
    if len(part_rows) == 0:
        return np.asarray(points[point_start:point_start + point_count], dtype=float)
    vertices: list[np.ndarray] = []
    for row in part_rows:
        local_start, local_count = [int(v) for v in row]
        segment = np.asarray(points[point_start + local_start: point_start + local_start + local_count], dtype=float)
        if len(segment):
            vertices.append(segment)
    if not vertices:
        return np.empty((0, 2), dtype=float)
    return np.vstack(vertices)


def _extract_geometry_map(record: dict[str, Any]) -> dict[str, Any] | None:
    hdf_path = Path(record.get("result_hdf_path") or "")
    if not hdf_path.exists() or not hdf_path.is_file() or hdf_path.suffix.lower() != ".hdf":
        return None
    try:
        with h5py.File(hdf_path, "r") as hdf:
            if "Geometry/River Centerlines/Polyline Info" not in hdf:
                return None
            center_info = np.asarray(hdf["Geometry/River Centerlines/Polyline Info"][:])
            center_parts = np.asarray(hdf["Geometry/River Centerlines/Polyline Parts"][:])
            center_points = np.asarray(hdf["Geometry/River Centerlines/Polyline Points"][:], dtype=float)
            center_attrs = np.asarray(hdf["Geometry/River Centerlines/Attributes"][:])
            centers = []
            for idx in range(len(center_info)):
                vertices = _polyline_vertices(center_info, center_parts, center_points, idx)
                if len(vertices) == 0:
                    continue
                centers.append({
                    "label": f"{_decode_bytes(center_attrs[idx]['River Name'])} / {_decode_bytes(center_attrs[idx]['Reach Name'])}",
                    "points": vertices,
                })

            cross_sections = []
            if "Geometry/Cross Sections/Polyline Info" in hdf:
                xs_info = np.asarray(hdf["Geometry/Cross Sections/Polyline Info"][:])
                xs_parts = np.asarray(hdf["Geometry/Cross Sections/Polyline Parts"][:])
                xs_points = np.asarray(hdf["Geometry/Cross Sections/Polyline Points"][:], dtype=float)
                xs_attrs = np.asarray(hdf["Geometry/Cross Sections/Attributes"][:])
                step = max(1, len(xs_info) // 18)
                for idx in range(0, len(xs_info), step):
                    vertices = _polyline_vertices(xs_info, xs_parts, xs_points, idx)
                    if len(vertices) == 0:
                        continue
                    cross_sections.append({
                        "label": f"{_decode_bytes(xs_attrs[idx]['River'])} / {_decode_bytes(xs_attrs[idx]['Reach'])} / RS {_decode_bytes(xs_attrs[idx]['RS'])}",
                        "points": vertices,
                    })
    except Exception:
        return None
    if not centers:
        return None
    return {"centerlines": centers, "cross_sections": cross_sections}


def _summarize_project(record: dict[str, Any]) -> dict[str, Any] | None:
    project_dir = Path(record["project_dir"])
    try:
        return summarize_hec_ras_project(project_dir)
    except Exception:
        return None


def _extract_results(record: dict[str, Any]) -> dict[str, Any]:
    hdf_path = Path(record.get("result_hdf_path") or "")
    if not hdf_path.exists():
        raise FileNotFoundError(f"Result HDF not found: {hdf_path}")

    project_file = Path(record["project_file"]) if record.get("project_file") else None
    unit_system = _unit_system(project_file)
    lf = _length_factor(unit_system)
    qf = _flow_factor(unit_system)

    with h5py.File(hdf_path, "r") as hdf:
        if "Results/Steady/Output/Output Blocks/Base Output/Steady Profiles/Cross Sections/Water Surface" in hdf:
            attrs = hdf["Results/Steady/Output/Geometry Info/Cross Section Attributes"][:]
            stations_raw, labels, rivers, reaches = _decode_station_attrs(attrs)
            stations = np.nan_to_num(stations_raw * lf, nan=0.0)
            ws = np.asarray(hdf["Results/Steady/Output/Output Blocks/Base Output/Steady Profiles/Cross Sections/Water Surface"][:], dtype=float) * lf
            flow = np.asarray(hdf["Results/Steady/Output/Output Blocks/Base Output/Steady Profiles/Cross Sections/Flow"][:], dtype=float) * qf
            eg = np.asarray(hdf["Results/Steady/Output/Output Blocks/Base Output/Steady Profiles/Cross Sections/Energy Grade"][:], dtype=float) * lf
            profile_names = _decode_text_array(hdf["Results/Steady/Output/Output Blocks/Base Output/Steady Profiles/Profile Names"][:])
            order = _grouped_order(stations, rivers, reaches)
            stations = stations[order]
            rivers = [rivers[idx] for idx in order]
            reaches = [reaches[idx] for idx in order]
            profile_axis_m, segment_labels = _build_profile_axis(stations, rivers, reaches)
            return {
                "mode": "steady",
                "unit_system": unit_system,
                "stations_m": stations,
                "profile_axis_m": profile_axis_m,
                "segment_labels": segment_labels,
                "rivers": rivers,
                "reaches": reaches,
                "labels": [labels[idx] for idx in order],
                "water_surface_m": ws[:, order],
                "flow_m3s": flow[:, order],
                "energy_grade_m": eg[:, order],
                "profile_names": profile_names,
            }

        attrs = hdf["Results/Unsteady/Output/Output Blocks/Base Output/Unsteady Time Series/Cross Sections/Cross Section Attributes"][:]
        stations_raw, labels, rivers, reaches = _decode_station_attrs(attrs)
        stations = np.nan_to_num(stations_raw * lf, nan=0.0)
        ws = np.asarray(hdf["Results/Unsteady/Output/Output Blocks/Base Output/Unsteady Time Series/Cross Sections/Water Surface"][:], dtype=float) * lf
        flow = np.asarray(hdf["Results/Unsteady/Output/Output Blocks/Base Output/Unsteady Time Series/Cross Sections/Flow"][:], dtype=float) * qf
        time_hours = np.asarray(hdf["Results/Unsteady/Output/Output Blocks/Base Output/Unsteady Time Series/Time"][:], dtype=float) * 24.0
        max_ws = np.asarray(hdf["Results/Unsteady/Output/Output Blocks/Base Output/Summary Output/Cross Sections/Maximum Water Surface"][:], dtype=float) * lf
        min_ws = np.asarray(hdf["Results/Unsteady/Output/Output Blocks/Base Output/Summary Output/Cross Sections/Minimum Water Surface"][:], dtype=float) * lf
        order = _grouped_order(stations, rivers, reaches)
        stations = stations[order]
        rivers = [rivers[idx] for idx in order]
        reaches = [reaches[idx] for idx in order]
        profile_axis_m, segment_labels = _build_profile_axis(stations, rivers, reaches)
        return {
            "mode": "unsteady",
            "unit_system": unit_system,
            "stations_m": stations,
            "profile_axis_m": profile_axis_m,
            "segment_labels": segment_labels,
            "rivers": rivers,
            "reaches": reaches,
            "labels": [labels[idx] for idx in order],
            "water_surface_m": ws[:, order],
            "flow_m3s": flow[:, order],
            "time_hours": time_hours,
            "max_water_surface_m": max_ws[:, order],
            "min_water_surface_m": min_ws[:, order],
        }


def _plot_topology(report_dir: Path, record: dict[str, Any], summary: dict[str, Any] | None) -> Path:
    _style_plot()
    geometry_map = _extract_geometry_map(record)
    fig, ax = plt.subplots(figsize=(11.8, 5.8))
    if geometry_map and geometry_map.get("centerlines"):
        for center in geometry_map["centerlines"]:
            vertices = center["points"]
            ax.plot(vertices[:, 0], vertices[:, 1], lw=3.0, color="#0b7285", solid_capstyle="round", solid_joinstyle="round")
        for xs in geometry_map.get("cross_sections", []):
            vertices = xs["points"]
            ax.plot(vertices[:, 0], vertices[:, 1], lw=0.9, color="#adb5bd", alpha=0.8)
        ax.set_title(f"河道平面示意图: {record['project_name']}", fontsize=15, fontweight="bold", color="#0b3c49")
        ax.set_xlabel("平面 X 坐标")
        ax.set_ylabel("平面 Y 坐标")
        ax.set_aspect("equal", adjustable="datalim")
        legend_lines = [
            plt.Line2D([0], [0], color="#0b7285", lw=3.0, label="河道中心线"),
            plt.Line2D([0], [0], color="#adb5bd", lw=1.0, label="代表性断面"),
        ]
        ax.legend(handles=legend_lines, loc="best")
    else:
        ax.axis("off")
        geom = (summary or {}).get("tables", {}).get("geometries", [])
        flows = (summary or {}).get("tables", {}).get("steady_flows", []) or (summary or {}).get("tables", {}).get("unsteady_flows", [])
        geom0 = geom[0] if geom else {}
        flow0 = flows[0] if flows else {}
        boxes = [
            (0.08, 0.35, 0.22, 0.3, f"案例\n{record['project_name']}"),
            (0.39, 0.35, 0.22, 0.3, f"当前 Plan\np{record.get('actual_plan_number', '--')}"),
            (0.70, 0.35, 0.22, 0.3, f"几何/流量\nXS {geom0.get('num_cross_sections', '-')} 断面\nFlow {flow0.get('Flow Title', flow0.get('description', '-')) or '-'}"),
        ]
        for x, y, w, h, text in boxes:
            rect = plt.Rectangle((x, y), w, h, fc="#fffdf8", ec="#0b7285", lw=1.6, transform=ax.transAxes)
            ax.add_patch(rect)
            ax.text(x + w / 2, y + h / 2, text, ha="center", va="center", fontsize=12, transform=ax.transAxes)
        ax.annotate("", xy=(0.39, 0.5), xytext=(0.30, 0.5), arrowprops=dict(arrowstyle="->", lw=1.8, color="#0b7285"), xycoords=ax.transAxes)
        ax.annotate("", xy=(0.70, 0.5), xytext=(0.61, 0.5), arrowprops=dict(arrowstyle="->", lw=1.8, color="#0b7285"), xycoords=ax.transAxes)
        ax.text(0.5, 0.82, f"项目拓扑与计算链: {record.get('category', '未分类')}", ha="center", fontsize=15, fontweight="bold", color="#0b3c49", transform=ax.transAxes)
        if geom:
            info = geom[0]
            note = (
                f"1D断面数 {info.get('num_cross_sections', 0)} | "
                f"桥梁 {info.get('num_bridges', 0)} | "
                f"涵洞 {info.get('num_culverts', 0)} | "
                f"闸/门 {info.get('num_gates', 0)}"
            )
            ax.text(0.5, 0.16, note, ha="center", fontsize=11, color="#52606d", transform=ax.transAxes)

    path = report_dir / "topology.svg"
    _save_figure(fig, path)
    return path


def _plot_results(report_dir: Path, record: dict[str, Any], results: dict[str, Any]) -> tuple[Path, Path]:
    _style_plot()
    x_km = np.asarray(results.get("profile_axis_m", results["stations_m"]), dtype=float) / 1000.0
    x_label = "剖面累计距离 (km, SI)"

    profile_path = report_dir / "result_profile.svg"
    ts_path = report_dir / "result_timeseries.svg"

    if results["mode"] == "steady":
        ws = np.asarray(results["water_surface_m"], dtype=float)
        flow = np.asarray(results["flow_m3s"], dtype=float)
        eg = np.asarray(results["energy_grade_m"], dtype=float)
        names = results["profile_names"]
        indices = sorted(set([0, len(names) // 2, len(names) - 1]))

        fig, ax = plt.subplots(figsize=(12.6, 6.4))
        palette = ["#005f73", "#0a9396", "#bb3e03"]
        for color, idx in zip(palette, indices):
            ax.plot(
                x_km,
                ws[idx],
                lw=2.3,
                color=color,
                label=f"水面线 {names[idx]}",
                solid_capstyle="round",
                solid_joinstyle="round",
                antialiased=True,
            )
        ax.plot(x_km, eg[indices[0]], lw=1.6, color="#6c584c", ls="--", label=f"能量线 {names[indices[0]]}")
        ax.set_title("稳态水面线结果图")
        ax.set_xlabel(x_label)
        ax.set_ylabel("高程 (m)")
        ax.legend(loc="best")
        _save_figure(fig, profile_path)

        fig, axes = plt.subplots(2, 1, figsize=(12.6, 8.2), sharex=True)
        for color, idx in zip(palette, indices):
            axes[0].plot(x_km, flow[idx], lw=2.2, color=color, label=f"流量 {names[idx]}")
        axes[0].set_ylabel("流量 (m3/s)")
        axes[0].set_title("稳态剖面流量分布")
        axes[0].legend(loc="best")
        axes[1].plot(x_km, ws[indices[-1]] - ws[indices[0]], lw=2.2, color="#ae2012")
        axes[1].set_ylabel("水位差 (m)")
        axes[1].set_xlabel(x_label)
        axes[1].set_title("首末工况水位差")
        _save_figure(fig, ts_path)
        return profile_path, ts_path

    ws = np.asarray(results["water_surface_m"], dtype=float)
    flow = np.asarray(results["flow_m3s"], dtype=float)
    time_h = np.asarray(results["time_hours"], dtype=float)
    max_ws = np.asarray(results["max_water_surface_m"], dtype=float)
    min_ws = np.asarray(results["min_water_surface_m"], dtype=float)

    fig, ax = plt.subplots(figsize=(12.6, 6.4))
    ax.plot(x_km, ws[-1], lw=2.4, color="#005f73", label="末时刻水面线", solid_capstyle="round", solid_joinstyle="round")
    ax.plot(x_km, np.nanmax(max_ws, axis=0), lw=1.8, color="#ee9b00", label="最大水面线包络")
    ax.plot(x_km, np.nanmin(min_ws, axis=0), lw=1.8, color="#bb3e03", label="最小水面线包络")
    ax.set_title("非恒定工况水面线结果图")
    ax.set_xlabel(x_label)
    ax.set_ylabel("高程 (m)")
    ax.legend(loc="best")
    _save_figure(fig, profile_path)

    section_indices = sorted(set([0, ws.shape[1] // 2, ws.shape[1] - 1]))
    fig, axes = plt.subplots(2, 1, figsize=(12.6, 8.4), sharex=True)
    palette = ["#005f73", "#0a9396", "#bb3e03"]
    for color, idx in zip(palette, section_indices):
        label = f"RS {results['labels'][idx].split('RS ')[-1]}"
        axes[0].plot(time_h, ws[:, idx], lw=2.1, color=color, label=label)
        axes[1].plot(time_h, flow[:, idx], lw=2.1, color=color, label=label)
    axes[0].set_ylabel("水位 (m)")
    axes[0].set_title("关键断面水位过程线")
    axes[0].legend(loc="best")
    axes[1].set_ylabel("流量 (m3/s)")
    axes[1].set_xlabel("时间 (h)")
    axes[1].set_title("关键断面流量过程线")
    _save_figure(fig, ts_path)
    return profile_path, ts_path


def _result_table(record: dict[str, Any], summary: dict[str, Any] | None, results: dict[str, Any] | None) -> list[tuple[str, str]]:
    rows = [
        ("案例名称", record["project_name"]),
        ("类别", record.get("category", "-")),
        ("运行状态", record.get("status", "-")),
        ("当前 Plan", f"p{record.get('actual_plan_number', '-') or '-'}"),
        ("结果来源", record.get("_source_json", "-")),
        ("结果 HDF", Path(record.get("result_hdf_path", "-")).name if record.get("result_hdf_path") else "-"),
    ]
    if summary:
        counts = summary.get("counts", {})
        rows.extend([
            ("Plan 数", str(counts.get("plans", 0))),
            ("几何文件数", str(counts.get("geometries", 0))),
            ("边界/流量文件数", str(counts.get("steady_flows", 0) + counts.get("unsteady_flows", 0))),
        ])
        geometries = summary.get("tables", {}).get("geometries", [])
        if geometries:
            geom = geometries[0]
            rows.extend([
                ("断面数", str(geom.get("num_cross_sections", 0))),
                ("桥梁数", str(geom.get("num_bridges", 0))),
                ("涵洞数", str(geom.get("num_culverts", 0))),
                ("闸门数", str(geom.get("num_gates", 0))),
            ])
    if results:
        if results["mode"] == "steady":
            rows.extend([
                ("结果模式", "稳态"),
                ("剖面数", str(len(results["profile_names"]))),
                ("最大水位", f"{float(np.nanmax(results['water_surface_m'])):.3f} m"),
                ("最小水位", f"{float(np.nanmin(results['water_surface_m'])):.3f} m"),
                ("代表流量", f"{float(np.nanmax(results['flow_m3s'])):.3f} m3/s"),
                ("河段数", str(len(results.get("segment_labels", [])))),
            ])
        else:
            rows.extend([
                ("结果模式", "非恒定"),
                ("时步数", str(int(results["water_surface_m"].shape[0]))),
                ("断面数", str(int(results["water_surface_m"].shape[1]))),
                ("河段数", str(len(results.get("segment_labels", [])))),
                ("总历时", f"{float(results['time_hours'][-1] - results['time_hours'][0]):.2f} h"),
                ("最大水位", f"{float(np.nanmax(results['water_surface_m'])):.3f} m"),
                ("最大流量", f"{float(np.nanmax(results['flow_m3s'])):.3f} m3/s"),
            ])
    return rows


def _hero_metrics(results: dict[str, Any] | None) -> list[tuple[str, str]]:
    if not results:
        return [
            ("结果状态", "当前未提取到通用仿真结果图"),
            ("说明", "需针对该物理模块单独定制结果提取"),
            ("长度单位", "m"),
            ("流量单位", "m3/s"),
        ]
    if results["mode"] == "steady":
        return [
            ("结果模式", "稳态"),
            ("最大水位", f"{float(np.nanmax(results['water_surface_m'])):.3f} m"),
            ("最小水位", f"{float(np.nanmin(results['water_surface_m'])):.3f} m"),
            ("代表流量", f"{float(np.nanmax(results['flow_m3s'])):.3f} m3/s"),
        ]
    return [
        ("结果模式", "非恒定"),
        ("峰值水位", f"{float(np.nanmax(results['water_surface_m'])):.3f} m"),
        ("峰值流量", f"{float(np.nanmax(results['flow_m3s'])):.3f} m3/s"),
        ("总历时", f"{float(results['time_hours'][-1] - results['time_hours'][0]):.2f} h"),
    ]


def _ai_conclusion(record: dict[str, Any], summary: dict[str, Any] | None, results: dict[str, Any] | None) -> list[str]:
    conclusions = []
    if record.get("status") != "computed":
        conclusions.append("该案例当前还没有形成可供人工核查的通用水力结果图，需要继续补结果提取适配。")
        conclusions.append(f"当前阻塞: {record.get('error', '未记录具体错误')}")
        return conclusions

    reason = record.get("comparability", {}).get("reason", "")
    conclusions.append("本页展示的是该案例当前实际求得的水面线、过程线或峰值包络结果。")
    if reason:
        conclusions.append(f"对标建议: {reason}")
    if summary and summary.get("tables", {}).get("geometries"):
        geom = summary["tables"]["geometries"][0]
        if geom.get("num_bridges", 0) or geom.get("num_culverts", 0) or geom.get("num_gates", 0):
            conclusions.append("该几何包含结构物，优先作为复杂边界/结构能力校核案例，不建议直接拿来判断 HydroClaude 单河道主求解器精度。")
        else:
            conclusions.append("该几何以 1D 断面为主，适合作为后续 HydroClaude 明渠基线映射候选。")
    if results:
        if results.get("segment_labels"):
            conclusions.append(f"结果曲线已按 {len(results['segment_labels'])} 个 river/reach 河段分组重排，避免多河段案例因断面编号交错而出现假性锯齿。")
        if results["mode"] == "steady":
            conclusions.append("报告中的水面线图反映的是 HEC-RAS 多剖面稳态结果，适合人工核查回水线单调性、能量线位置和不同工况间的水位差。")
        else:
            conclusions.append("报告中的末时刻水面线与关键断面过程线反映的是非恒定解的传播和峰值响应，可直接用于人工检查是否存在异常振荡或不合理尖峰。")
    conclusions.append("全部结果已统一换算为国际单位，图表使用中文字体配置，避免浏览器查看时汉字乱码。")
    return conclusions


def _write_case_report(record: dict[str, Any]) -> dict[str, Path]:
    slug = _slugify(record["project_name"])
    report_dir = CASE_DIR / slug
    report_dir.mkdir(parents=True, exist_ok=True)

    summary = _summarize_project(record) if record.get("status") == "computed" else None
    results = None
    topology_fig = _plot_topology(report_dir, record, summary)
    profile_fig = None
    ts_fig = None
    result_error = None
    if record.get("status") == "computed":
        try:
            results = _extract_results(record)
            profile_fig, ts_fig = _plot_results(report_dir, record, results)
        except Exception as exc:
            result_error = str(exc)

    generated_at = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    title = f"HydroMind仿真结果报告: {record['project_name']}"
    rows = _result_table(record, summary, results)
    hero_metrics = _hero_metrics(results)
    conclusions = _ai_conclusion(record, summary, results)
    result_rows = "\n".join(f"| {k} | {v} |" for k, v in rows)
    hero_rows = "\n".join(f"| {k} | {v} |" for k, v in hero_metrics)
    conclusion_md = "\n".join(f"- {item}" for item in conclusions)
    index_rel = "../index.html"
    suite_rel = "../../hydromind_hecras_example_suite_report.html"

    md_path = report_dir / "report.md"
    html_path = report_dir / "report.html"
    json_path = report_dir / "report.json"

    md = f"""# HydroMind水网仿真结果报告: {record['project_name']}

**生成时间**: {generated_at}

## 1. 问题描述

本报告只关注该案例的水网/河网仿真结果。重点是当前水面线、过程线、峰值响应和河道平面结构，不讨论测试流程。

## 2. 工况与参考

| 指标 | 数值 |
|---|---|
| 参考软件 | HEC-RAS |
| 当前 Plan | p{record.get('actual_plan_number', '-') or '-'} |
| 单位体系 | 国际单位制 (SI) |
| 聚合来源 | {record.get('_source_json', '-')} |

## 3. 水网拓扑图

![项目拓扑图](topology.svg)

## 4. 核心结论

| 指标 | 数值 |
|---|---|
{hero_rows}

## 5. 解题思路

1. 在本机通过 `HEC-RAS COM + ras_commander` 真实打开工程并执行 `Compute_CurrentPlan`。
2. 自动识别当前 `Plan` 与结果 `HDF`，避免误把所有案例都当成 `p01`。
3. 将结果统一转换为国际单位，并提取能够支持人工核查的水面线、过程线和关键统计指标。
4. 若案例包含复杂结构物、混合流态或非恒定控制，则在结论中明确标为复杂能力校核，不冒充公平直接对标样例。

## 6. 结果图

![结果剖面图]({profile_fig.name if profile_fig else 'topology.svg'})

![结果过程图]({ts_fig.name if ts_fig else 'topology.svg'})

## 7. 结果表

| 指标 | 数值 |
|---|---|
{result_rows}

## 8. AI 结论建议

{conclusion_md}

## 9. 导航

- [返回案例索引]({index_rel})
- [返回套件总览]({suite_rel})
"""

    figures_html = ""
    if profile_fig:
        figures_html += f"""
    <figure>
      <img src="{_asset_to_data_uri(profile_fig)}" alt="结果剖面图">
      <figcaption>图2. 结果剖面图，全部已换算为国际单位。</figcaption>
    </figure>
"""
    if ts_fig:
        figures_html += f"""
    <figure>
      <img src="{_asset_to_data_uri(ts_fig)}" alt="结果过程图">
      <figcaption>图3. 关键结果过程图，用于人工核查水面线演变或关键断面响应。</figcaption>
    </figure>
"""
    if result_error:
        figures_html += f"<p>结果图提取失败: {result_error}</p>"

    table_html = "".join(f"<tr><td>{k}</td><td>{v}</td></tr>" for k, v in rows)
    hero_html = "".join(
        f'<div class="metric"><div class="label">{k}</div><div class="value">{v}</div></div>'
        for k, v in hero_metrics
    )
    conclusion_html = "".join(f"<li>{item}</li>" for item in conclusions)
    reference_html = "".join(
        f"<tr><td>{key}</td><td>{value}</td></tr>"
        for key, value in [
            ("参考软件", "HEC-RAS"),
            ("当前 Plan", f"p{record.get('actual_plan_number', '-') or '-'}"),
            ("单位体系", "国际单位制 (SI)"),
            ("聚合来源", record.get("_source_json", "-")),
        ]
    )
    html = f"""<!DOCTYPE html>
<html lang="zh-CN">
<head>
  <meta charset="utf-8">
  <title>HydroMind水网仿真结果报告: {record['project_name']}</title>
  <style>
    body {{
      margin: 0;
      font-family: "Microsoft YaHei", "PingFang SC", "Noto Sans CJK SC", Arial, sans-serif;
      background: #f4f1ea;
      color: #1f2933;
    }}
    .page {{
      max-width: 1320px;
      margin: 0 auto;
      padding: 28px 26px 56px;
    }}
    .card {{
      background: #fffdf8;
      border: 1px solid #e5dfd0;
      border-radius: 14px;
      padding: 18px 20px;
      margin: 18px 0;
      box-shadow: 0 8px 24px rgba(15, 23, 42, 0.06);
    }}
    .hero {{
      display: grid;
      grid-template-columns: repeat(4, 1fr);
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
    figure {{
      margin: 18px 0;
      background: white;
      border: 1px solid #d9d9d9;
      border-radius: 12px;
      overflow: hidden;
    }}
    figure img {{ display: block; width: 100%; background: white; }}
    figcaption {{ padding: 10px 12px 14px; color: #52606d; font-size: 14px; }}
    ul {{ margin: 8px 0 0 18px; }}
    .links a {{
      display: inline-block;
      margin-right: 14px;
      color: #0b7285;
      font-weight: 700;
      text-decoration: none;
    }}
  </style>
</head>
<body>
  <div class="page">
    <h1>HydroMind水网仿真结果报告: {record['project_name']}</h1>
    <div>生成时间: {generated_at}</div>

    <div class="card">
      <h2>1. 问题描述</h2>
      <p>本页只关注 `{record['project_name']}` 的水网/河网仿真结果。重点是当前水面线、过程线、峰值响应和河道平面结构，不讨论测试流程。案例类别为 `{record.get('category', '-')}`。</p>
    </div>

    <div class="card">
      <h2>2. 工况与参考</h2>
      <table>
        <tr><th>指标</th><th>数值</th></tr>
        {reference_html}
      </table>
    </div>

    <div class="card">
      <h2>3. 水网拓扑图</h2>
      <figure>
        <img src="{_asset_to_data_uri(topology_fig)}" alt="项目拓扑图">
        <figcaption>图1. 优先展示 HEC-RAS 几何中的真实河道平面示意；若案例缺少通用几何坐标，则退回项目结构示意。</figcaption>
      </figure>
    </div>

    <div class="card">
      <h2>4. 核心结论</h2>
      <div class="hero">
        {hero_html}
      </div>
    </div>

    <div class="card">
      <h2>5. 解题思路</h2>
      <ul>
        <li>真实调用 HEC-RAS 打开工程并执行当前 plan 计算。</li>
        <li>自动识别结果 HDF，统一转成国际单位。</li>
        <li>按稳态或非恒定结果类型提取水面线、包络线和关键过程线。</li>
        <li>结合结构物与边界复杂度给出 AI 对标建议。</li>
      </ul>
    </div>

    <div class="card">
      <h2>6. 结果图</h2>
      {figures_html}
    </div>

    <div class="card">
      <h2>7. 结果表</h2>
      <table>
        <tr><th>指标</th><th>数值</th></tr>
        {table_html}
      </table>
    </div>

    <div class="card">
      <h2>8. AI 结论建议</h2>
      <ul>{conclusion_html}</ul>
    </div>

    <div class="card links">
      <h2>9. 导航</h2>
      <a href="{index_rel}">返回案例索引</a>
      <a href="{suite_rel}">返回套件总览</a>
    </div>
  </div>
</body>
</html>
"""

    payload = {
        "generated_at": generated_at,
        "record": record,
        "summary": summary,
        "results_mode": results["mode"] if results else None,
        "result_extract_error": result_error,
        "table_rows": rows,
        "ai_conclusions": conclusions,
    }
    md_path.write_text(md, encoding="utf-8")
    html_path.write_text(html, encoding="utf-8")
    json_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    return {"md": md_path, "html": html_path, "json": json_path}


def generate_reports(pattern: str = "hecras_example_suite_chunk_*.json", limit: int | None = None) -> dict[str, Any]:
    records = _load_records(pattern)
    if limit is not None:
        records = records[:limit]
    items = []
    for record in records:
        items.append({
            "project_name": record["project_name"],
            **{key: str(value) for key, value in _write_case_report(record).items()},
        })
    output = {
        "generated_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "source_paths": [str(path.name) for path in _select_record_paths(pattern)],
        "report_count": len(items),
        "items": items,
    }
    index_path = CASE_DIR / "index.json"
    index_path.write_text(json.dumps(output, ensure_ascii=False, indent=2), encoding="utf-8")
    md_index = CASE_DIR / "INDEX.md"
    html_index = CASE_DIR / "index.html"

    grouped: dict[str, list[dict[str, Any]]] = {}
    for item, record in zip(items, records):
        grouped.setdefault(record.get("category", "未分类"), []).append({"item": item, "record": record})

    md_sections = []
    html_sections = []
    for category in sorted(grouped):
        md_sections.append(f"## {category}\n")
        html_sections.append(f"<div class=\"card\"><h2>{category}</h2><table><tr><th>案例</th><th>状态</th><th>Plan</th><th>详情页</th></tr>")
        for bundle in grouped[category]:
            record = bundle["record"]
            item = bundle["item"]
            slug = _slugify(record["project_name"])
            rel_html = f"{slug}/report.html"
            md_sections.append(
                f"- {record['project_name']} | 状态: {record.get('status', '-')} | Plan: p{record.get('actual_plan_number', '-') or '-'} | [HTML]({rel_html})"
            )
            html_sections.append(
                f"<tr><td>{record['project_name']}</td><td>{record.get('status', '-')}</td><td>p{record.get('actual_plan_number', '-') or '-'}</td><td><a href=\"{rel_html}\">打开详情页</a></td></tr>"
            )
        html_sections.append("</table></div>")

    source_line = ", ".join(output["source_paths"])
    md_text = f"# HEC-RAS 官方案例水网仿真结果报告索引\n\n**生成时间**: {output['generated_at']}\n\n聚合来源: `{source_line}`\n\n共生成 `{len(items)}` 份案例结果报告。\n\n" + "\n".join(md_sections)
    html_text = f"""<!DOCTYPE html>
<html lang="zh-CN">
<head>
  <meta charset="utf-8">
  <title>HEC-RAS 官方案例水网仿真结果报告索引</title>
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
      padding: 28px 26px 56px;
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
    }}
    th {{ background: #eef6f7; }}
    a {{ color: #0b7285; text-decoration: none; font-weight: 600; }}
  </style>
</head>
<body>
  <div class="page">
    <h1>HEC-RAS 官方案例水网仿真结果报告索引</h1>
    <div>生成时间: {output['generated_at']}</div>
    <div>聚合来源: {source_line}</div>
    <div>共生成 {len(items)} 份案例结果报告。</div>
    {''.join(html_sections)}
  </div>
</body>
</html>
"""
    md_index.write_text(md_text, encoding="utf-8")
    html_index.write_text(html_text, encoding="utf-8")
    return output


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--pattern", default="hecras_example_suite_chunk_*.json")
    parser.add_argument("--limit", type=int, default=None)
    args = parser.parse_args()
    result = generate_reports(pattern=args.pattern, limit=args.limit)
    print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
