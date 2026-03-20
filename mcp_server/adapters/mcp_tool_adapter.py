"""MCP Tool adapter -- implements MCPToolProtocol from hydromind-contracts.

Provides the ``call`` / ``list_tools`` interface and dispatches to the
concrete tool implementations exposed by the HydroClaude MCP server.
"""

from __future__ import annotations

import logging
import warnings
from typing import Any

from mcp_server.adapters.simulator_adapter import HydroClaudeSimulator
from mcp_server.adapters.controller_adapter import HydroClaudeController
from mcp_server.config import ENGINE_CAPABILITIES, ENGINE_NAME, ENGINE_VERSION

logger = logging.getLogger(__name__)

# ======================================================================
# Tool descriptors
# ======================================================================

TOOL_DESCRIPTORS: list[dict[str, Any]] = [
    {
        "name": "run_canal_simulation",
        "description": (
            "Run a 1-D open-channel simulation using HydroClaude solvers "
            "(hydrostatic reconstruction, Godunov FVM, or steady profile)."
        ),
        "inputSchema": {
            "type": "object",
            "properties": {
                "solver_type": {
                    "type": "string",
                    "enum": ["hydrostatic", "godunov", "steady"],
                    "default": "hydrostatic",
                },
                "length": {"type": "number", "description": "Channel length (m)"},
                "width": {"type": "number", "description": "Channel width (m)"},
                "slope": {"type": "number", "description": "Bed slope"},
                "manning_n": {"type": "number", "description": "Manning roughness"},
                "nx": {"type": "integer", "description": "Number of spatial nodes"},
                "Q_upstream": {"type": "number", "description": "Upstream discharge (m3/s)"},
                "h_downstream": {"type": "number", "description": "Downstream depth (m)"},
                "duration": {"type": "number", "description": "Sim duration (s)"},
                "dt": {"type": "number", "description": "Time step (s)"},
            },
        },
    },
    {
        "name": "run_network_analysis",
        "description": (
            "Run pipe-network analysis using the Hardy-Cross method."
        ),
        "inputSchema": {
            "type": "object",
            "properties": {
                "nodes": {
                    "type": "array",
                    "description": "Node definitions [{id, type, elevation, demand?, head?}, ...]",
                },
                "pipes": {
                    "type": "array",
                    "description": "Pipe definitions [{id, from, to, length, diameter, roughness}, ...]",
                },
                "max_iter": {"type": "integer", "default": 100},
                "tol": {"type": "number", "default": 1e-6},
            },
            "required": ["nodes", "pipes"],
        },
    },
    {
        "name": "run_network_benchmark",
        "description": (
            "Run Hardy-Cross pipe-network analysis and compare against a real "
            "EPANET calculation generated from the same network definition."
        ),
        "inputSchema": {
            "type": "object",
            "properties": {
                "nodes": {
                    "type": "array",
                    "description": "Node definitions [{id, type, elevation, demand?, head?}, ...]",
                },
                "pipes": {
                    "type": "array",
                    "description": "Pipe definitions [{id, from, to, length, diameter, roughness}, ...]",
                },
                "max_iter": {"type": "integer", "default": 100},
                "tol": {"type": "number", "default": 1e-6},
                "epanet_units": {
                    "type": "string",
                    "default": "LPS",
                    "description": "EPANET input flow units for generated .inp file.",
                },
                "headloss_model": {
                    "type": "string",
                    "default": "D-W",
                    "enum": ["D-W", "H-W"],
                    "description": "EPANET headloss model for reference run.",
                },
                "inp_path": {
                    "type": "string",
                    "description": "Optional output path for generated EPANET .inp file.",
                },
            },
            "required": ["nodes", "pipes"],
        },
    },
    {
        "name": "run_open_channel_benchmark",
        "description": (
            "Run a real SWMM dynamic-wave open-channel benchmark and compare "
            "against HydroClaude open-channel solvers."
        ),
        "inputSchema": {
            "type": "object",
            "properties": {
                "length": {"type": "number", "default": 1000.0},
                "width": {"type": "number", "default": 10.0},
                "channel_height": {"type": "number", "default": 5.0},
                "slope": {"type": "number", "default": 0.001},
                "manning_n": {"type": "number", "default": 0.025},
                "discharge": {"type": "number", "default": 50.0},
                "h_downstream": {"type": "number", "default": 2.0},
                "dx": {"type": "number", "default": 50.0},
                "duration_hours": {"type": "number", "default": 6.0},
                "inp_path": {
                    "type": "string",
                    "description": "Optional output path for the generated SWMM .inp file.",
                },
            },
        },
    },
    {
        "name": "get_hec_ras_benchmark_status",
        "description": (
            "Inspect HEC-RAS runtime availability and the readiness of the "
            "local HEC-RAS benchmark provenance scaffold."
        ),
        "inputSchema": {
            "type": "object",
            "properties": {
                "case_name": {
                    "type": "string",
                    "default": "hec_ras_steady_flow_example_3_1",
                },
            },
        },
    },
    {
        "name": "run_hec_ras_sample_benchmark",
        "description": (
            "Run the official HEC-RAS 6.6 Mixed Flow Regime Channel sample "
            "and compare it against HydroClaude Hydrostatic."
        ),
        "inputSchema": {
            "type": "object",
            "properties": {
                "output_root": {
                    "type": "string",
                    "description": "Optional folder for extracted HEC-RAS sample project files.",
                },
            },
        },
    },
    {
        "name": "summarize_hec_ras_project",
        "description": (
            "Summarize a local HEC-RAS project using ras-commander metadata "
            "tables and project-level inventory."
        ),
        "inputSchema": {
            "type": "object",
            "properties": {
                "project_path": {"type": "string", "description": "Path to a HEC-RAS project directory."},
                "include_tables": {"type": "boolean", "default": True},
            },
            "required": ["project_path"],
        },
    },
    {
        "name": "read_hec_ras_plan_description",
        "description": "Read the description block from a HEC-RAS plan file.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "project_path": {"type": "string", "description": "Path to a HEC-RAS project directory."},
                "plan_number": {"type": "string", "description": "Plan number such as 01 or 1."},
            },
            "required": ["project_path", "plan_number"],
        },
    },
    {
        "name": "get_hec_ras_compute_messages",
        "description": "Extract compute messages from a HEC-RAS plan HDF file.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "project_path": {"type": "string", "description": "Path to a HEC-RAS project directory."},
                "plan_number": {"type": "string", "description": "Plan number such as 01, 1, or a direct .hdf path."},
            },
            "required": ["project_path", "plan_number"],
        },
    },
    {
        "name": "get_hec_ras_plan_results_summary",
        "description": "Read plan-level summary tables from a HEC-RAS plan HDF file.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "project_path": {"type": "string"},
                "plan_number": {"type": "string"},
            },
            "required": ["project_path", "plan_number"],
        },
    },
    {
        "name": "get_hec_ras_hdf_structure",
        "description": "Explore the structure of a HEC-RAS HDF file.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "hdf_path": {"type": "string"},
                "group_path": {"type": "string", "default": "/"},
                "paths_only": {"type": "boolean", "default": True},
            },
            "required": ["hdf_path"],
        },
    },
    {
        "name": "get_hec_ras_projection_info",
        "description": "Read projection WKT from a HEC-RAS HDF file.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "hdf_path": {"type": "string"},
            },
            "required": ["hdf_path"],
        },
    },
    {
        "name": "hecras_project_summary",
        "description": "Official ras-commander style alias for summarize_hec_ras_project.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "project_path": {"type": "string"},
                "include_tables": {"type": "boolean", "default": True},
            },
            "required": ["project_path"],
        },
    },
    {
        "name": "read_plan_description",
        "description": "Official ras-commander style alias for read_hec_ras_plan_description.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "project_path": {"type": "string"},
                "plan_number": {"type": "string"},
            },
            "required": ["project_path", "plan_number"],
        },
    },
    {
        "name": "get_compute_messages",
        "description": "Official ras-commander style alias for get_hec_ras_compute_messages.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "project_path": {"type": "string"},
                "plan_number": {"type": "string"},
            },
            "required": ["project_path", "plan_number"],
        },
    },
    {
        "name": "get_plan_results_summary",
        "description": "Official ras-commander style alias for get_hec_ras_plan_results_summary.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "project_path": {"type": "string"},
                "plan_number": {"type": "string"},
            },
            "required": ["project_path", "plan_number"],
        },
    },
    {
        "name": "get_hdf_structure",
        "description": "Official ras-commander style alias for get_hec_ras_hdf_structure.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "hdf_path": {"type": "string"},
                "group_path": {"type": "string", "default": "/"},
                "paths_only": {"type": "boolean", "default": True},
            },
            "required": ["hdf_path"],
        },
    },
    {
        "name": "get_projection_info",
        "description": "Official ras-commander style alias for get_hec_ras_projection_info.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "hdf_path": {"type": "string"},
            },
            "required": ["hdf_path"],
        },
    },
    {
        "name": "run_steady_state",
        "description": (
            "Compute the steady-state water surface profile for an open "
            "channel with optional gate structures."
        ),
        "inputSchema": {
            "type": "object",
            "properties": {
                "length": {"type": "number"},
                "width": {"type": "number"},
                "slope": {"type": "number"},
                "manning_n": {"type": "number"},
                "Q": {"type": "number", "description": "Discharge (m3/s)"},
                "h_downstream": {"type": "number"},
                "nx": {"type": "integer", "default": 201},
                "method": {"type": "string", "enum": ["shooting", "bvp"], "default": "shooting"},
            },
            "required": ["Q", "h_downstream"],
        },
    },
    {
        "name": "run_controller",
        "description": (
            "Compute a control action (PID or MPC) for water-level regulation."
        ),
        "inputSchema": {
            "type": "object",
            "properties": {
                "controller_type": {"type": "string", "enum": ["pid", "mpc"], "default": "pid"},
                "h_current": {"type": "number", "description": "Current water level (m)"},
                "h_target": {"type": "number", "description": "Target water level (m)"},
                "dt": {"type": "number", "description": "Time step (s)"},
                "pid_config": {
                    "type": "object",
                    "description": "PID gains {kp, ki, kd, output_min, output_max}",
                },
                "mpc_config": {
                    "type": "object",
                    "description": "MPC parameters {prediction_horizon, control_horizon, ...}",
                },
                "constraints": {"type": "object"},
            },
            "required": ["h_current", "h_target"],
        },
    },
    {
        "name": "validate_results",
        "description": "Validate simulation result arrays (NaN, Inf, negative depth checks).",
        "inputSchema": {
            "type": "object",
            "properties": {
                "h": {"type": "array", "description": "Water depth array"},
                "Q": {"type": "array", "description": "Discharge array"},
            },
            "required": ["h"],
        },
    },
    {
        "name": "get_solver_capabilities",
        "description": "Return engine metadata and available solver capabilities.",
        "inputSchema": {"type": "object", "properties": {}},
    },
]


# ======================================================================
# MCPToolProtocol implementation
# ======================================================================

class HydroClaudeMCPTool:
    """MCPToolProtocol implementation for HydroClaude.

    Satisfies ``hydromind_contracts.MCPToolProtocol`` (duck-typed /
    runtime-checkable Protocol).
    """

    def __init__(self) -> None:
        self._simulator = HydroClaudeSimulator()
        self._controller = HydroClaudeController()
        self._dispatch = {
            "run_canal_simulation": self._tool_run_canal_simulation,
            "run_network_analysis": self._tool_run_network_analysis,
            "run_network_benchmark": self._tool_run_network_benchmark,
            "run_open_channel_benchmark": self._tool_run_open_channel_benchmark,
            "get_hec_ras_benchmark_status": self._tool_get_hec_ras_benchmark_status,
            "run_hec_ras_sample_benchmark": self._tool_run_hec_ras_sample_benchmark,
            "summarize_hec_ras_project": self._tool_summarize_hec_ras_project,
            "read_hec_ras_plan_description": self._tool_read_hec_ras_plan_description,
            "get_hec_ras_compute_messages": self._tool_get_hec_ras_compute_messages,
            "get_hec_ras_plan_results_summary": self._tool_get_hec_ras_plan_results_summary,
            "get_hec_ras_hdf_structure": self._tool_get_hec_ras_hdf_structure,
            "get_hec_ras_projection_info": self._tool_get_hec_ras_projection_info,
            "hecras_project_summary": self._tool_summarize_hec_ras_project,
            "read_plan_description": self._tool_read_hec_ras_plan_description,
            "get_compute_messages": self._tool_get_hec_ras_compute_messages,
            "get_plan_results_summary": self._tool_get_hec_ras_plan_results_summary,
            "get_hdf_structure": self._tool_get_hec_ras_hdf_structure,
            "get_projection_info": self._tool_get_hec_ras_projection_info,
            "run_steady_state": self._tool_run_steady_state,
            "run_controller": self._tool_run_controller,
            "validate_results": self._tool_validate_results,
            "get_solver_capabilities": self._tool_get_solver_capabilities,
        }

    # ------------------------------------------------------------------
    # MCPToolProtocol interface
    # ------------------------------------------------------------------
    def call(self, tool_name: str, params: dict) -> dict:
        handler = self._dispatch.get(tool_name)
        if handler is None:
            return {
                "error": f"Unknown tool: {tool_name}",
                "available_tools": list(self._dispatch.keys()),
            }
        try:
            return handler(params)
        except Exception as exc:
            logger.exception("Tool %s failed", tool_name)
            return {"error": str(exc), "tool": tool_name}

    def list_tools(self) -> list:
        return list(TOOL_DESCRIPTORS)

    # ------------------------------------------------------------------
    # Tool implementations
    # ------------------------------------------------------------------
    def _tool_run_canal_simulation(self, params: dict) -> dict:
        duration = float(params.pop("duration", 0))
        dt = float(params.pop("dt", 0.1))
        return self._simulator.simulate(params, duration, dt)

    def _tool_run_network_analysis(self, params: dict) -> dict:
        """Build a NetworkTopology from node/pipe dicts and solve."""
        nodes_data = params.get("nodes", [])
        pipes_data = params.get("pipes", [])
        max_iter = int(params.get("max_iter", 100))
        tol = float(params.get("tol", 1e-6))

        if not nodes_data or not pipes_data:
            return {"error": "nodes and pipes arrays are required"}

        try:
            from network.network_topology import NetworkTopology
            from network.network_node import Junction, Reservoir
            from network.pressure_pipe import PressurePipe
            from solvers.hardy_cross_solver import HardyCrossSolver
        except ImportError as exc:
            return {"error": f"Network modules unavailable: {exc}"}

        network = NetworkTopology()

        for nd in nodes_data:
            nid = str(nd["id"])
            ntype = nd.get("type", "junction")
            elev = float(nd.get("elevation", 0.0))
            if ntype == "reservoir":
                node = Reservoir(node_id=nid, elevation=elev,
                                 head=float(nd.get("head", elev)))
                network.add_node(node)
            else:
                demand = float(nd.get("demand", 0.0))
                node = Junction(node_id=nid, elevation=elev, demand=demand)
                network.add_node(node)

        for pd in pipes_data:
            pid = str(pd["id"])
            pipe = PressurePipe(
                pipe_id=pid,
                length=float(pd.get("length", 100.0)),
                diameter=float(pd.get("diameter", 0.3)),
                roughness=float(pd.get("roughness", 0.001)),
            )
            network.add_pipe(pipe, str(pd["from"]), str(pd["to"]))

        solver = HardyCrossSolver(network, max_iter=max_iter, tol=tol, verbose=False)
        flows, heads = solver.solve()
        summary = solver.get_results_summary()
        return {
            "flows": flows,
            "heads": heads,
            "summary": summary,
        }

    def _tool_run_network_benchmark(self, params: dict) -> dict:
        """Run Hardy-Cross and compare against a real EPANET reference."""
        analysis = self._tool_run_network_analysis(params)
        if analysis.get("error"):
            return analysis

        nodes_data = params.get("nodes", [])
        pipes_data = params.get("pipes", [])
        epanet_units = str(params.get("epanet_units", "LPS"))
        headloss_model = str(params.get("headloss_model", "D-W"))
        inp_path = params.get("inp_path")

        try:
            from pathlib import Path
            import wntr
            from wntr.network import WaterNetworkModel
            from wntr.network.io import write_inpfile
            from wntr.sim import EpanetSimulator
        except ImportError as exc:
            return {"error": f"EPANET benchmark runtime unavailable: {exc}"}

        wn = WaterNetworkModel()
        wn.options.time.duration = 0
        wn.options.hydraulic.demand_model = "DDA"
        wn.options.hydraulic.inpfile_units = epanet_units
        with warnings.catch_warnings():
            warnings.simplefilter("ignore")
            wn.options.hydraulic.headloss = headloss_model

        for nd in nodes_data:
            nid = str(nd["id"])
            ntype = nd.get("type", "junction")
            elev = float(nd.get("elevation", 0.0))
            if ntype == "reservoir":
                wn.add_reservoir(nid, base_head=float(nd.get("head", elev)))
            else:
                wn.add_junction(
                    nid,
                    base_demand=float(nd.get("demand", 0.0)),
                    demand_pattern=None,
                    elevation=elev,
                )

        for pd in pipes_data:
            wn.add_pipe(
                str(pd["id"]),
                str(pd["from"]),
                str(pd["to"]),
                length=float(pd.get("length", 100.0)),
                diameter=float(pd.get("diameter", 0.3)),
                roughness=float(pd.get("roughness", 0.001)),
                minor_loss=float(pd.get("minor_loss", 0.0)),
            )

        out_path = Path(inp_path) if inp_path else Path("reports") / "network_benchmark_epanet.inp"
        out_path.parent.mkdir(parents=True, exist_ok=True)
        write_inpfile(wn, str(out_path), units=epanet_units)

        results = EpanetSimulator(wn).run_sim(file_prefix=str(out_path.with_suffix("")))
        epanet_heads = {key: float(value) for key, value in results.node["head"].iloc[0].to_dict().items()}
        epanet_flows = {key: float(value) for key, value in results.link["flowrate"].iloc[0].to_dict().items()}

        hc_flows = {key: float(value) for key, value in analysis["flows"].items()}
        hc_heads = {key: float(value) for key, value in analysis["heads"].items()}
        flow_errors = {
            key: abs(hc_flows[key] - epanet_flows[key])
            for key in epanet_flows
            if key in hc_flows
        }
        head_errors = {
            key: abs(hc_heads[key] - epanet_heads[key])
            for key in epanet_heads
            if key in hc_heads
        }

        return {
            "hardycross": analysis,
            "epanet": {
                "engine": "WNTR EpanetSimulator",
                "version": getattr(wntr, "__version__", "unknown"),
                "inp_path": str(out_path),
                "units": epanet_units,
                "headloss_model": headloss_model,
                "flows": epanet_flows,
                "heads": epanet_heads,
            },
            "comparison": {
                "flow_abs_error_max": max(flow_errors.values()) if flow_errors else 0.0,
                "flow_abs_error_mean": sum(flow_errors.values()) / len(flow_errors) if flow_errors else 0.0,
                "head_abs_error_max": max(head_errors.values()) if head_errors else 0.0,
                "head_abs_error_mean": sum(head_errors.values()) / len(head_errors) if head_errors else 0.0,
                "flow_errors": flow_errors,
                "head_errors": head_errors,
            },
        }

    def _tool_run_open_channel_benchmark(self, params: dict) -> dict:
        """Run a real SWMM open-channel benchmark."""
        try:
            from pathlib import Path

            from integration.swmm_benchmark import (
                SWMMOpenChannelCase,
                run_swmm_open_channel_benchmark,
            )
        except ImportError as exc:
            return {"error": f"SWMM benchmark runtime unavailable: {exc}"}

        case = SWMMOpenChannelCase(
            length=float(params.get("length", 1000.0)),
            width=float(params.get("width", 10.0)),
            channel_height=float(params.get("channel_height", 5.0)),
            slope=float(params.get("slope", 0.001)),
            manning_n=float(params.get("manning_n", 0.025)),
            discharge=float(params.get("discharge", 50.0)),
            h_downstream=float(params.get("h_downstream", 2.0)),
            dx=float(params.get("dx", 50.0)),
            duration_hours=float(params.get("duration_hours", 6.0)),
        )
        root = Path(__file__).resolve().parents[2]
        out_path = Path(params.get("inp_path")) if params.get("inp_path") else root / "reports" / "swmm_open_channel_benchmark.inp"
        result = run_swmm_open_channel_benchmark(case=case, inp_path=out_path)
        return result

    def _tool_get_hec_ras_benchmark_status(self, params: dict) -> dict:
        """Inspect HEC-RAS runtime and case-scaffold readiness."""
        try:
            from integration.hec_ras_adapter import prepare_hec_ras_benchmark
        except ImportError as exc:
            return {"error": f"HEC-RAS adapter unavailable: {exc}"}

        case_name = str(params.get("case_name", "hec_ras_steady_flow_example_3_1"))
        return prepare_hec_ras_benchmark(case_name=case_name)

    def _tool_run_hec_ras_sample_benchmark(self, params: dict) -> dict:
        """Run the official HEC-RAS mixed-flow sample benchmark."""
        try:
            from integration.hec_ras_adapter import run_hec_ras_mixed_flow_sample
        except ImportError as exc:
            return {"error": f"HEC-RAS sample benchmark unavailable: {exc}"}

        output_root = params.get("output_root")
        return run_hec_ras_mixed_flow_sample(output_root=output_root)

    def _tool_summarize_hec_ras_project(self, params: dict) -> dict:
        """Summarize a local HEC-RAS project."""
        try:
            from integration.hec_ras_adapter import summarize_hec_ras_project
        except ImportError as exc:
            return {"error": f"HEC-RAS project summary unavailable: {exc}"}

        project_path = params.get("project_path")
        if not project_path:
            return {"error": "project_path is required"}
        include_tables = bool(params.get("include_tables", True))
        return summarize_hec_ras_project(project_path=project_path, include_tables=include_tables)

    def _tool_read_hec_ras_plan_description(self, params: dict) -> dict:
        """Read a HEC-RAS plan description."""
        try:
            from integration.hec_ras_adapter import read_hec_ras_plan_description
        except ImportError as exc:
            return {"error": f"HEC-RAS plan description unavailable: {exc}"}

        project_path = params.get("project_path")
        plan_number = params.get("plan_number")
        if not project_path or not plan_number:
            return {"error": "project_path and plan_number are required"}
        return read_hec_ras_plan_description(project_path=project_path, plan_number=str(plan_number))

    def _tool_get_hec_ras_compute_messages(self, params: dict) -> dict:
        """Read HEC-RAS compute messages from plan HDF."""
        try:
            from integration.hec_ras_adapter import get_hec_ras_compute_messages
        except ImportError as exc:
            return {"error": f"HEC-RAS compute messages unavailable: {exc}"}

        project_path = params.get("project_path")
        plan_number = params.get("plan_number")
        if not project_path or not plan_number:
            return {"error": "project_path and plan_number are required"}
        return get_hec_ras_compute_messages(project_path=project_path, plan_number=str(plan_number))

    def _tool_get_hec_ras_plan_results_summary(self, params: dict) -> dict:
        """Read HEC-RAS plan result summaries."""
        try:
            from integration.hec_ras_adapter import get_hec_ras_plan_results_summary
        except ImportError as exc:
            return {"error": f"HEC-RAS plan results summary unavailable: {exc}"}

        project_path = params.get("project_path")
        plan_number = params.get("plan_number")
        if not project_path or not plan_number:
            return {"error": "project_path and plan_number are required"}
        return get_hec_ras_plan_results_summary(project_path=project_path, plan_number=str(plan_number))

    def _tool_get_hec_ras_hdf_structure(self, params: dict) -> dict:
        """Explore HEC-RAS HDF structure."""
        try:
            from integration.hec_ras_adapter import get_hec_ras_hdf_structure
        except ImportError as exc:
            return {"error": f"HEC-RAS HDF structure unavailable: {exc}"}

        hdf_path = params.get("hdf_path")
        if not hdf_path:
            return {"error": "hdf_path is required"}
        return get_hec_ras_hdf_structure(
            hdf_path=hdf_path,
            group_path=str(params.get("group_path", "/")),
            paths_only=bool(params.get("paths_only", True)),
        )

    def _tool_get_hec_ras_projection_info(self, params: dict) -> dict:
        """Read HEC-RAS projection info."""
        try:
            from integration.hec_ras_adapter import get_hec_ras_projection_info
        except ImportError as exc:
            return {"error": f"HEC-RAS projection info unavailable: {exc}"}

        hdf_path = params.get("hdf_path")
        if not hdf_path:
            return {"error": "hdf_path is required"}
        return get_hec_ras_projection_info(hdf_path=hdf_path)

    def _tool_run_steady_state(self, params: dict) -> dict:
        p = dict(params)
        p["solver_type"] = "steady"
        return self._simulator.simulate(p, duration=0, dt=0)

    def _tool_run_controller(self, params: dict) -> dict:
        state = {
            "h": float(params["h_current"]),
            "controller_type": params.get("controller_type", "pid"),
            "dt": float(params.get("dt", 1.0)),
        }
        target = {"h": float(params["h_target"])}
        constraints = params.get("constraints", {})

        if "pid_config" in params:
            self._controller.set_target({"pid_config": params["pid_config"]})
        if "mpc_config" in params:
            self._controller.set_target({"mpc_config": params["mpc_config"]})

        return self._controller.compute_action(state, target, constraints)

    def _tool_validate_results(self, params: dict) -> dict:
        import numpy as np
        from utils.canal_utils import check_numerical_validity

        h_list = params.get("h", [])
        Q_list = params.get("Q", h_list)  # Default Q to same as h if missing
        h = np.array(h_list, dtype=float)
        Q = np.array(Q_list, dtype=float)
        is_valid, message = check_numerical_validity(h, Q)
        return {"valid": is_valid, "message": message}

    def _tool_get_solver_capabilities(self, _params: dict) -> dict:
        return {
            "engine": ENGINE_NAME,
            "version": ENGINE_VERSION,
            "capabilities": ENGINE_CAPABILITIES,
            "tools": [t["name"] for t in TOOL_DESCRIPTORS],
        }
