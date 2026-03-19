"""HydroClaude MCP Server -- main entry point.

Exposes HydroClaude solvers as MCP tools using FastMCP (preferred) or a
minimal HTTP JSON-RPC fallback.

Usage::

    # Standalone
    python -m mcp_server.hydroclaude_server

    # Programmatic
    from mcp_server.hydroclaude_server import create_server
    server = create_server()
    server.run()  # blocks
"""

from __future__ import annotations

import json
import logging
import sys
from http.server import HTTPServer, BaseHTTPRequestHandler
from typing import Any

from mcp_server.config import HOST, SERVER_PORT, LOG_LEVEL, ENGINE_NAME
from mcp_server.adapters.simulator_adapter import HydroClaudeSimulator
from mcp_server.adapters.controller_adapter import HydroClaudeController
from mcp_server.adapters.mcp_tool_adapter import HydroClaudeMCPTool

logger = logging.getLogger(__name__)

# ======================================================================
# FastMCP server (preferred)
# ======================================================================

_FASTMCP_AVAILABLE = False
try:
    from mcp.server.fastmcp import FastMCP  # type: ignore[import-untyped]
    _FASTMCP_AVAILABLE = True
except ImportError:
    pass


def _create_fastmcp_server() -> "FastMCP":
    """Build a FastMCP server with all HydroClaude tools registered."""
    mcp = FastMCP(f"{ENGINE_NAME}-MCP")
    simulator = HydroClaudeSimulator()
    controller = HydroClaudeController()

    # ---- Tools -------------------------------------------------------

    @mcp.tool()
    def run_canal_simulation(
        solver_type: str = "hydrostatic",
        length: float = 1000.0,
        width: float = 10.0,
        slope: float = 0.001,
        manning_n: float = 0.025,
        nx: int = 201,
        Q_upstream: float = 10.0,
        h_downstream: float | None = None,
        duration: float = 300.0,
        dt: float = 0.5,
    ) -> dict:
        """Run 1-D open-channel simulation (hydrostatic / godunov / steady).

        Args:
            solver_type: Solver backend ("hydrostatic", "godunov", "steady").
            length: Channel length in metres.
            width: Channel width in metres.
            slope: Bed slope (dimensionless).
            manning_n: Manning roughness coefficient.
            nx: Number of spatial nodes.
            Q_upstream: Upstream discharge (m3/s).
            h_downstream: Downstream water depth (m), optional.
            duration: Simulation duration (s).
            dt: Time step (s).

        Returns:
            Simulation results dict.
        """
        params: dict[str, Any] = {
            "solver_type": solver_type,
            "length": length,
            "width": width,
            "slope": slope,
            "manning_n": manning_n,
            "nx": nx,
            "Q_upstream": Q_upstream,
        }
        if h_downstream is not None:
            params["h_downstream"] = h_downstream
        return simulator.simulate(params, duration, dt)

    @mcp.tool()
    def run_network_analysis(
        nodes: list[dict],
        pipes: list[dict],
        max_iter: int = 100,
        tol: float = 1e-6,
    ) -> dict:
        """Run Hardy-Cross pipe-network analysis.

        Args:
            nodes: [{id, type, elevation, demand?, head?}, ...]
            pipes: [{id, from, to, length, diameter, roughness}, ...]
            max_iter: Maximum iterations.
            tol: Convergence tolerance (m3/s).

        Returns:
            Flows, heads, and summary.
        """
        tool = HydroClaudeMCPTool()
        return tool.call("run_network_analysis", {
            "nodes": nodes,
            "pipes": pipes,
            "max_iter": max_iter,
            "tol": tol,
        })

    @mcp.tool()
    def run_steady_state(
        Q: float,
        h_downstream: float,
        length: float = 1000.0,
        width: float = 10.0,
        slope: float = 0.001,
        manning_n: float = 0.025,
        nx: int = 201,
        method: str = "shooting",
    ) -> dict:
        """Compute steady-state water surface profile.

        Args:
            Q: Discharge (m3/s).
            h_downstream: Downstream boundary depth (m).
            length: Channel length (m).
            width: Channel width (m).
            slope: Bed slope.
            manning_n: Manning roughness.
            nx: Number of spatial nodes.
            method: "shooting" or "bvp".

        Returns:
            Profile results with x and h arrays.
        """
        params = {
            "solver_type": "steady",
            "Q": Q,
            "h_downstream": h_downstream,
            "length": length,
            "width": width,
            "slope": slope,
            "manning_n": manning_n,
            "nx": nx,
            "method": method,
        }
        return simulator.simulate(params, duration=0, dt=0)

    @mcp.tool()
    def run_controller(
        h_current: float,
        h_target: float,
        controller_type: str = "pid",
        dt: float = 1.0,
        pid_config: dict | None = None,
        mpc_config: dict | None = None,
        constraints: dict | None = None,
    ) -> dict:
        """Compute a control action (PID or MPC) for water level regulation.

        Args:
            h_current: Current water level (m).
            h_target: Target water level (m).
            controller_type: "pid" or "mpc".
            dt: Time step (s).
            pid_config: PID gains {kp, ki, kd, ...}.
            mpc_config: MPC parameters {prediction_horizon, ...}.
            constraints: {output_min, output_max}.

        Returns:
            Control action dict.
        """
        if pid_config:
            controller.set_target({"pid_config": pid_config})
        if mpc_config:
            controller.set_target({"mpc_config": mpc_config})
        state = {"h": h_current, "controller_type": controller_type, "dt": dt}
        target = {"h": h_target}
        return controller.compute_action(state, target, constraints or {})

    @mcp.tool()
    def validate_results(h: list[float], Q: list[float] | None = None) -> dict:
        """Validate simulation results for NaN / Inf / negative values.

        Args:
            h: Water depth array.
            Q: Discharge array (defaults to h if omitted).

        Returns:
            {valid: bool, message: str}
        """
        tool = HydroClaudeMCPTool()
        return tool.call("validate_results", {"h": h, "Q": Q or h})

    @mcp.tool()
    def get_solver_capabilities() -> dict:
        """Return engine metadata and available solver capabilities."""
        tool = HydroClaudeMCPTool()
        return tool.call("get_solver_capabilities", {})

    return mcp


# ======================================================================
# Fallback JSON-RPC server
# ======================================================================

class _JsonRpcHandler(BaseHTTPRequestHandler):
    """Minimal JSON-RPC 2.0 handler backed by HydroClaudeMCPTool."""

    _tool: HydroClaudeMCPTool | None = None

    @classmethod
    def get_tool(cls) -> HydroClaudeMCPTool:
        if cls._tool is None:
            cls._tool = HydroClaudeMCPTool()
        return cls._tool

    def do_POST(self) -> None:  # noqa: N802
        content_length = int(self.headers.get("Content-Length", 0))
        body = self.rfile.read(content_length)
        try:
            request = json.loads(body)
        except json.JSONDecodeError:
            self._send(400, {"error": "Invalid JSON"})
            return

        method = request.get("method", "")
        params = request.get("params", {})
        req_id = request.get("id", None)

        tool = self.get_tool()

        if method == "tools/list":
            result = tool.list_tools()
        elif method == "tools/call":
            tool_name = params.get("name", "")
            tool_params = params.get("arguments", {})
            result = tool.call(tool_name, tool_params)
        else:
            result = {"error": f"Unknown method: {method}"}

        response = {"jsonrpc": "2.0", "id": req_id, "result": result}
        self._send(200, response)

    def do_GET(self) -> None:  # noqa: N802
        """Health check endpoint."""
        self._send(200, {"status": "ok", "engine": ENGINE_NAME})

    def _send(self, code: int, data: Any) -> None:
        self.send_response(code)
        self.send_header("Content-Type", "application/json")
        self.end_headers()
        self.wfile.write(json.dumps(data, default=str).encode())

    def log_message(self, format: str, *args: Any) -> None:  # noqa: A002
        logger.info(format, *args)


# ======================================================================
# Public API
# ======================================================================

def create_server() -> Any:
    """Create the MCP server instance.

    Returns a FastMCP server if the ``mcp`` package is available,
    otherwise an ``HTTPServer`` with the JSON-RPC fallback handler.
    """
    if _FASTMCP_AVAILABLE:
        logger.info("Using FastMCP transport")
        return _create_fastmcp_server()
    else:
        logger.info("FastMCP not available -- falling back to JSON-RPC on port %d", SERVER_PORT)
        return HTTPServer((HOST, SERVER_PORT), _JsonRpcHandler)


def main() -> None:
    """Entry point for ``python -m mcp_server.hydroclaude_server``."""
    logging.basicConfig(
        level=getattr(logging, LOG_LEVEL.upper(), logging.INFO),
        format="%(asctime)s [%(name)s] %(levelname)s: %(message)s",
    )

    server = create_server()

    if _FASTMCP_AVAILABLE:
        logger.info("Starting HydroClaude MCP server (FastMCP)")
        server.run()
    else:
        logger.info("Starting HydroClaude MCP server (JSON-RPC) on %s:%d", HOST, SERVER_PORT)
        try:
            server.serve_forever()
        except KeyboardInterrupt:
            logger.info("Shutting down")
            server.server_close()


if __name__ == "__main__":
    main()
