"""MCP Tool adapter -- implements MCPToolProtocol from hydromind-contracts.

Provides the ``call`` / ``list_tools`` interface and dispatches to the
concrete tool implementations exposed by the HydroClaude MCP server.
"""

from __future__ import annotations

import logging
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
