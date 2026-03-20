"""Real SWMM open-channel benchmark helpers.

Builds and runs a minimal SWMM dynamic-wave open-channel model, extracts
timeseries from the generated ``.out`` file, and compares the final profile
against HydroClaude solvers and the independent steady-profile reference.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any

import numpy as np


@dataclass
class SWMMOpenChannelCase:
    """Configuration for a rectangular open-channel backwater benchmark."""

    length: float = 1000.0
    width: float = 10.0
    channel_height: float = 5.0
    slope: float = 0.001
    manning_n: float = 0.025
    discharge: float = 50.0
    h_downstream: float = 2.0
    dx: float = 50.0
    duration_hours: float = 6.0
    routing_step_seconds: int = 5
    report_step_minutes: int = 5
    start_date: str = "03/20/2026"
    start_time: str = "00:00:00"


def _series_to_arrays(series: dict) -> tuple[np.ndarray, np.ndarray]:
    items = list(series.items())
    times = np.asarray([item[0] for item in items], dtype="datetime64[s]")
    values = np.asarray([float(item[1]) for item in items], dtype=float)
    return times, values


def build_swmm_input(case: SWMMOpenChannelCase) -> str:
    """Return a complete SWMM ``.inp`` string for the benchmark case."""
    n_links = int(round(case.length / case.dx))
    if n_links <= 0:
        raise ValueError("length/dx must define at least one SWMM conduit")

    hours = int(case.duration_hours)
    report_step = f"00:{case.report_step_minutes:02d}:00"
    routing_step = f"0:00:{case.routing_step_seconds:02d}"

    junction_lines = ["[JUNCTIONS]", ";Name           Elevation  MaxDepth  InitDepth  SurDepth  Aponded"]
    conduit_lines = [
        "[CONDUITS]",
        ";Name           From Node        To Node          Length    Roughness InOffset  OutOffset InitFlow  MaxFlow",
    ]
    xsection_lines = [
        "[XSECTIONS]",
        ";Link           Shape        Geom1     Geom2     Geom3     Geom4     Barrels    Culvert",
    ]
    coord_lines = ["[COORDINATES]"]

    for idx in range(n_links):
        node_id = f"J{idx}"
        elevation = case.slope * (case.length - idx * case.dx)
        init_depth = case.h_downstream + (case.discharge / max(case.discharge, 1e-9)) * 0.5
        init_depth = min(case.channel_height - 0.2, init_depth + 0.03 * (n_links - idx))
        junction_lines.append(
            f"{node_id:<17}{elevation:>8.3f}      {case.channel_height:>4.1f}       {init_depth:>4.2f}        0         0"
        )
        coord_lines.append(f"{node_id} {idx * case.dx:.0f} 0")

    coord_lines.append(f"OUT1 {case.length:.0f} 0")

    for idx in range(n_links):
        from_node = f"J{idx}"
        to_node = "OUT1" if idx == n_links - 1 else f"J{idx + 1}"
        conduit_lines.append(
            f"C{idx:<16}{from_node:<17}{to_node:<17}{case.dx:<10.0f}{case.manning_n:<10.3f}0         0         {case.discharge:<8.3f}0"
        )
        xsection_lines.append(
            f"C{idx:<16}RECT_OPEN    {case.channel_height:<9.3f}{case.width:<10.3f}0         0         1"
        )

    return "\n".join(
        [
            "[TITLE]",
            "HydroClaude SWMM Open Channel Benchmark",
            "",
            "[OPTIONS]",
            "FLOW_UNITS              CMS",
            "INFILTRATION            HORTON",
            "FLOW_ROUTING            DYNWAVE",
            f"START_DATE              {case.start_date}",
            f"START_TIME              {case.start_time}",
            f"REPORT_START_DATE       {case.start_date}",
            f"REPORT_START_TIME       {case.start_time}",
            f"END_DATE                {case.start_date}",
            f"END_TIME                {hours:02d}:00:00",
            "SWEEP_START             01/01",
            "SWEEP_END               12/31",
            "DRY_DAYS                0",
            f"REPORT_STEP             {report_step}",
            "WET_STEP                00:00:30",
            "DRY_STEP                00:05:00",
            f"ROUTING_STEP            {routing_step}",
            "ALLOW_PONDING           NO",
            "INERTIAL_DAMPING        PARTIAL",
            "VARIABLE_STEP           0.75",
            "LENGTHENING_STEP        0",
            "MIN_SURFAREA            0",
            "NORMAL_FLOW_LIMITED     BOTH",
            "SKIP_STEADY_STATE       NO",
            "FORCE_MAIN_EQUATION     H-W",
            "LINK_OFFSETS            DEPTH",
            "MIN_SLOPE               0",
            "IGNORE_RAINFALL         YES",
            "IGNORE_RDII             YES",
            "IGNORE_SNOWMELT         YES",
            "IGNORE_GROUNDWATER      YES",
            "IGNORE_ROUTING          NO",
            "IGNORE_QUALITY          YES",
            "MAX_TRIALS              20",
            "HEAD_TOLERANCE          0.0015",
            "SYS_FLOW_TOL            5",
            "LAT_FLOW_TOL            5",
            "",
            *junction_lines,
            "",
            "[OUTFALLS]",
            ";Name           Elevation  Type       Stage Data       Gated Route To",
            f"OUT1             0.000      FIXED      {case.h_downstream:.3f}            NO",
            "",
            *conduit_lines,
            "",
            *xsection_lines,
            "",
            "[INFLOWS]",
            ";Node           Parameter        Time Series      Type     Mfactor  Sfactor  Baseline Pattern",
            "J0               FLOW             INFLOW           FLOW     1.0      1.0      0",
            "",
            "[TIMESERIES]",
            ";Name           Date       Time       Value",
            f"INFLOW                      00:00      {case.discharge:.3f}",
            f"INFLOW                      {hours:02d}:00      {case.discharge:.3f}",
            "",
            "[REPORT]",
            "INPUT      NO",
            "CONTROLS   NO",
            "SUBCATCHMENTS NONE",
            "NODES ALL",
            "LINKS ALL",
            "",
            *coord_lines,
            "",
        ]
    )


def write_swmm_input(case: SWMMOpenChannelCase, inp_path: str | Path) -> Path:
    path = Path(inp_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(build_swmm_input(case), encoding="utf-8")
    return path


def extract_swmm_results(out_path: str | Path, case: SWMMOpenChannelCase) -> dict[str, Any]:
    """Extract node/link timeseries from a completed SWMM ``.out`` file."""
    from pyswmm import Output
    from pyswmm.output import LinkSeries, NodeSeries

    out_file = Path(out_path)
    n_links = int(round(case.length / case.dx))
    node_ids = [f"J{idx}" for idx in range(n_links)]
    link_ids = [f"C{idx}" for idx in range(n_links)]
    x_nodes = np.arange(n_links, dtype=float) * case.dx
    bed_nodes = case.slope * (case.length - x_nodes)

    with Output(str(out_file)) as out:
        sample_times, sample_depths = _series_to_arrays(NodeSeries(out)[node_ids[0]].invert_depth)
        nt = len(sample_times)
        depth_history = np.zeros((nt, len(node_ids)), dtype=float)
        head_history = np.zeros_like(depth_history)
        flow_history = np.zeros((nt, len(link_ids)), dtype=float)
        link_depth_history = np.zeros_like(flow_history)

        for idx, node_id in enumerate(node_ids):
            _, node_depths = _series_to_arrays(NodeSeries(out)[node_id].invert_depth)
            _, node_heads = _series_to_arrays(NodeSeries(out)[node_id].hydraulic_head)
            depth_history[:, idx] = node_depths
            head_history[:, idx] = node_heads

        for idx, link_id in enumerate(link_ids):
            _, link_flows = _series_to_arrays(LinkSeries(out)[link_id].flow_rate)
            _, link_depths = _series_to_arrays(LinkSeries(out)[link_id].flow_depth)
            flow_history[:, idx] = link_flows
            link_depth_history[:, idx] = link_depths

    seconds = (sample_times - sample_times[0]).astype("timedelta64[s]").astype(int).astype(float)
    stage_history = depth_history + bed_nodes[None, :]
    return {
        "time_seconds": seconds,
        "time_iso": [str(t) for t in sample_times],
        "node_ids": node_ids,
        "link_ids": link_ids,
        "x_nodes": x_nodes.tolist(),
        "bed_nodes": bed_nodes.tolist(),
        "depth_history": depth_history.tolist(),
        "stage_history": stage_history.tolist(),
        "head_history": head_history.tolist(),
        "flow_history": flow_history.tolist(),
        "link_depth_history": link_depth_history.tolist(),
        "final_depths": depth_history[-1].tolist(),
        "final_stages": stage_history[-1].tolist(),
        "final_link_flows": flow_history[-1].tolist(),
        "final_link_depths": link_depth_history[-1].tolist(),
    }


def run_swmm_open_channel_benchmark(
    case: SWMMOpenChannelCase,
    inp_path: str | Path,
    hydro_duration: float = 200.0,
    hydro_dt: float = 0.5,
) -> dict[str, Any]:
    """Run SWMM and compare against HydroClaude + steady-profile references."""
    from swmm.toolkit import solver

    from mcp_server.adapters.simulator_adapter import HydroClaudeSimulator
    from solvers.steady_profile_solver import SteadyProfileSolver

    inp_file = write_swmm_input(case, inp_path)
    rpt_file = inp_file.with_suffix(".rpt")
    out_file = inp_file.with_suffix(".out")
    solver.swmm_run(str(inp_file), str(rpt_file), str(out_file))

    swmm = extract_swmm_results(out_file, case)
    x_nodes = np.asarray(swmm["x_nodes"], dtype=float)
    bed_nodes = np.asarray(swmm["bed_nodes"], dtype=float)
    swmm_depths = np.asarray(swmm["final_depths"], dtype=float)
    swmm_stages = np.asarray(swmm["final_stages"], dtype=float)
    swmm_flows = np.asarray(swmm["final_link_flows"], dtype=float)
    swmm_link_depths = np.asarray(swmm["final_link_depths"], dtype=float)

    steady_solver = SteadyProfileSolver(length=case.length, B=case.width, S0=case.slope, n=case.manning_n)
    steady = steady_solver.solve_without_structures(Q=case.discharge, h_downstream=case.h_downstream, nx=201)
    x_ref = np.asarray(steady["x"], dtype=float)
    h_ref = np.asarray(steady["h"], dtype=float)
    q_ref = np.asarray(steady["Q"], dtype=float)
    ref_depths = np.interp(x_nodes, x_ref, h_ref)
    ref_stages = ref_depths + bed_nodes

    simulator = HydroClaudeSimulator()
    common_params = {
        "length": case.length,
        "width": case.width,
        "slope": case.slope,
        "manning_n": case.manning_n,
        "nx": 201,
        "Q_upstream": case.discharge,
        "h_downstream": case.h_downstream,
    }
    hydrostatic = simulator.simulate({"solver_type": "hydrostatic", **common_params}, duration=0.0, dt=hydro_dt)
    godunov = simulator.simulate({"solver_type": "godunov", **common_params}, duration=hydro_duration, dt=hydro_dt)

    hydro_x = np.asarray(hydrostatic["x"], dtype=float) if "x" in hydrostatic else x_ref
    hydro_depths = np.interp(x_nodes, hydro_x, np.asarray(hydrostatic["h"], dtype=float))
    hydro_stages = hydro_depths + bed_nodes

    god_x = np.asarray(godunov["x"], dtype=float)
    god_depths = np.interp(x_nodes, god_x, np.asarray(godunov["h_final"], dtype=float))
    god_stages = god_depths + bed_nodes

    def _error_metrics(values: np.ndarray, reference: np.ndarray) -> dict[str, float]:
        abs_error = np.abs(values - reference)
        rel_error = abs_error / np.maximum(np.abs(reference), 1e-9)
        return {
            "max_abs_error_m": float(np.max(abs_error)),
            "mean_abs_error_m": float(np.mean(abs_error)),
            "max_rel_error_pct": float(np.max(rel_error) * 100.0),
            "mean_rel_error_pct": float(np.mean(rel_error) * 100.0),
            "upstream_rel_error_pct": float(rel_error[0] * 100.0),
            "downstream_rel_error_pct": float(rel_error[-1] * 100.0),
        }

    swmm_vs_steady = _error_metrics(swmm_depths, ref_depths)
    hydro_vs_swmm = _error_metrics(hydro_depths, swmm_depths)
    god_vs_swmm = _error_metrics(god_depths, swmm_depths)

    swmm_velocity = swmm_flows / np.maximum(case.width * swmm_link_depths, 1e-9)
    swmm_froude = np.abs(swmm_velocity) / np.sqrt(9.81 * np.maximum(swmm_link_depths, 1e-9))

    report = {
        "case": asdict(case),
        "files": {
            "inp": str(inp_file),
            "rpt": str(rpt_file),
            "out": str(out_file),
        },
        "swmm": swmm,
        "steady_profile": {
            "x": x_ref.tolist(),
            "h": h_ref.tolist(),
            "Q": q_ref.tolist(),
            "sampled_depths": ref_depths.tolist(),
            "sampled_stages": ref_stages.tolist(),
        },
        "hydrostatic": {
            "x": hydro_x.tolist(),
            "h": hydrostatic["h"],
            "Q": hydrostatic["Q"],
            "sampled_depths": hydro_depths.tolist(),
            "sampled_stages": hydro_stages.tolist(),
            "iterations": int(hydrostatic.get("iterations", 0)),
        },
        "godunov": {
            "x": godunov["x"],
            "h": godunov["h_final"],
            "Q": godunov["Q_final"],
            "sampled_depths": god_depths.tolist(),
            "sampled_stages": god_stages.tolist(),
            "steps": int(godunov.get("steps", 0)),
            "summary": godunov.get("summary", {}),
        },
        "metrics": {
            "swmm_vs_steady": swmm_vs_steady,
            "hydrostatic_vs_swmm": hydro_vs_swmm,
            "godunov_vs_swmm": god_vs_swmm,
            "swmm_mean_flow_m3s": float(np.mean(swmm_flows)),
            "swmm_mean_link_depth_m": float(np.mean(swmm_link_depths)),
            "swmm_max_link_froude": float(np.max(swmm_froude)),
            "swmm_max_link_fullness_ratio": float(np.max(swmm_link_depths / case.channel_height)),
            "swmm_continuity_indicator_pct": float(abs(np.mean(swmm_flows) - case.discharge) / max(case.discharge, 1e-9) * 100.0),
        },
    }
    return report
