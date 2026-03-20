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
import os
import sys
import threading
import time
from http.server import HTTPServer, BaseHTTPRequestHandler
from urllib.error import URLError
from urllib.request import Request, urlopen
from typing import Any

from mcp_server.config import HOST, SERVER_PORT, LOG_LEVEL, ENGINE_NAME, ENGINE_VERSION, ENGINE_CAPABILITIES
from mcp_server.adapters.simulator_adapter import HydroClaudeSimulator
from mcp_server.adapters.controller_adapter import HydroClaudeController
from mcp_server.adapters.mcp_tool_adapter import HydroClaudeMCPTool

logger = logging.getLogger(__name__)
_SERVER_TRANSPORT = os.environ.get("HYDROCLAUDE_MCP_TRANSPORT", "http").lower()

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
    def run_network_benchmark(
        nodes: list[dict],
        pipes: list[dict],
        max_iter: int = 100,
        tol: float = 1e-6,
        epanet_units: str = "LPS",
        headloss_model: str = "D-W",
        inp_path: str | None = None,
    ) -> dict:
        """Run Hardy-Cross and compare against a real EPANET reference.

        Args:
            nodes: [{id, type, elevation, demand?, head?}, ...]
            pipes: [{id, from, to, length, diameter, roughness}, ...]
            max_iter: Maximum Hardy-Cross iterations.
            tol: Convergence tolerance (m3/s).
            epanet_units: EPANET input flow units.
            headloss_model: EPANET headloss model ("D-W" or "H-W").
            inp_path: Optional path for generated .inp file.

        Returns:
            Hardy-Cross results, EPANET results, and comparison metrics.
        """
        tool = HydroClaudeMCPTool()
        payload: dict[str, Any] = {
            "nodes": nodes,
            "pipes": pipes,
            "max_iter": max_iter,
            "tol": tol,
            "epanet_units": epanet_units,
            "headloss_model": headloss_model,
        }
        if inp_path is not None:
            payload["inp_path"] = inp_path
        return tool.call("run_network_benchmark", payload)

    @mcp.tool()
    def run_open_channel_benchmark(
        length: float = 1000.0,
        width: float = 10.0,
        channel_height: float = 5.0,
        slope: float = 0.001,
        manning_n: float = 0.025,
        discharge: float = 50.0,
        h_downstream: float = 2.0,
        dx: float = 50.0,
        duration_hours: float = 6.0,
        inp_path: str | None = None,
    ) -> dict:
        """Run a real SWMM open-channel benchmark.

        Args:
            length: Channel length in metres.
            width: Rectangular channel width in metres.
            channel_height: Channel wall height in metres.
            slope: Bed slope.
            manning_n: Manning roughness.
            discharge: Upstream inflow (m3/s).
            h_downstream: Downstream fixed depth (m).
            dx: SWMM reach length (m).
            duration_hours: SWMM simulation duration in hours.
            inp_path: Optional output path for generated SWMM input file.

        Returns:
            SWMM, HydroClaude, and steady-profile comparison data.
        """
        tool = HydroClaudeMCPTool()
        payload: dict[str, Any] = {
            "length": length,
            "width": width,
            "channel_height": channel_height,
            "slope": slope,
            "manning_n": manning_n,
            "discharge": discharge,
            "h_downstream": h_downstream,
            "dx": dx,
            "duration_hours": duration_hours,
        }
        if inp_path is not None:
            payload["inp_path"] = inp_path
        return tool.call("run_open_channel_benchmark", payload)

    @mcp.tool()
    def get_hec_ras_benchmark_status(
        case_name: str = "hec_ras_steady_flow_example_3_1",
    ) -> dict:
        """Inspect HEC-RAS runtime and benchmark-case readiness.

        Args:
            case_name: Engineering benchmark case directory name under
                ``validation_cases/engineering``.

        Returns:
            Runtime availability, provenance-scaffold inventory, and whether
            a true external HEC-RAS run is currently possible.
        """
        tool = HydroClaudeMCPTool()
        return tool.call("get_hec_ras_benchmark_status", {"case_name": case_name})

    @mcp.tool()
    def run_hec_ras_sample_benchmark(
        output_root: str | None = None,
    ) -> dict:
        """Run the official HEC-RAS 6.6 mixed-flow sample benchmark.

        Args:
            output_root: Optional folder for extracted sample project files.

        Returns:
            Real HEC-RAS sample results, Hydrostatic comparison, and metrics.
        """
        tool = HydroClaudeMCPTool()
        payload: dict[str, Any] = {}
        if output_root is not None:
            payload["output_root"] = output_root
        return tool.call("run_hec_ras_sample_benchmark", payload)

    @mcp.tool()
    def summarize_hec_ras_project(
        project_path: str,
        include_tables: bool = True,
    ) -> dict:
        """Summarize a local HEC-RAS project via ras-commander metadata.

        Args:
            project_path: Path to a HEC-RAS project directory.
            include_tables: Whether to include plan/geometry/flow tables.

        Returns:
            Structured project inventory and metadata tables.
        """
        tool = HydroClaudeMCPTool()
        return tool.call("summarize_hec_ras_project", {
            "project_path": project_path,
            "include_tables": include_tables,
        })

    @mcp.tool()
    def read_hec_ras_plan_description(
        project_path: str,
        plan_number: str,
    ) -> dict:
        """Read a HEC-RAS plan description block.

        Args:
            project_path: Path to a HEC-RAS project directory.
            plan_number: Plan number such as ``01`` or ``1``.

        Returns:
            Structured plan description payload.
        """
        tool = HydroClaudeMCPTool()
        return tool.call("read_hec_ras_plan_description", {
            "project_path": project_path,
            "plan_number": plan_number,
        })

    @mcp.tool()
    def get_hec_ras_compute_messages(
        project_path: str,
        plan_number: str,
    ) -> dict:
        """Extract compute messages from a HEC-RAS plan HDF.

        Args:
            project_path: Path to a HEC-RAS project directory.
            plan_number: Plan number such as ``01`` or ``1``.

        Returns:
            HDF path, preview lines, and raw compute messages text.
        """
        tool = HydroClaudeMCPTool()
        return tool.call("get_hec_ras_compute_messages", {
            "project_path": project_path,
            "plan_number": plan_number,
        })

    @mcp.tool()
    def get_hec_ras_plan_results_summary(
        project_path: str,
        plan_number: str,
    ) -> dict:
        """Read plan-level summary tables from a HEC-RAS plan HDF."""
        tool = HydroClaudeMCPTool()
        return tool.call("get_hec_ras_plan_results_summary", {
            "project_path": project_path,
            "plan_number": plan_number,
        })

    @mcp.tool()
    def get_hec_ras_hdf_structure(
        hdf_path: str,
        group_path: str = "/",
        paths_only: bool = True,
    ) -> dict:
        """Explore the structure of a HEC-RAS HDF file."""
        tool = HydroClaudeMCPTool()
        return tool.call("get_hec_ras_hdf_structure", {
            "hdf_path": hdf_path,
            "group_path": group_path,
            "paths_only": paths_only,
        })

    @mcp.tool()
    def get_hec_ras_projection_info(hdf_path: str) -> dict:
        """Read projection WKT from a HEC-RAS HDF file."""
        tool = HydroClaudeMCPTool()
        return tool.call("get_hec_ras_projection_info", {"hdf_path": hdf_path})

    @mcp.tool()
    def hecras_project_summary(project_path: str, include_tables: bool = True) -> dict:
        """ras-commander compatible alias for HEC-RAS project summary."""
        tool = HydroClaudeMCPTool()
        return tool.call("hecras_project_summary", {
            "project_path": project_path,
            "include_tables": include_tables,
        })

    @mcp.tool()
    def read_plan_description(project_path: str, plan_number: str) -> dict:
        """ras-commander compatible alias for plan description."""
        tool = HydroClaudeMCPTool()
        return tool.call("read_plan_description", {
            "project_path": project_path,
            "plan_number": plan_number,
        })

    @mcp.tool()
    def get_compute_messages(project_path: str, plan_number: str) -> dict:
        """ras-commander compatible alias for compute messages."""
        tool = HydroClaudeMCPTool()
        return tool.call("get_compute_messages", {
            "project_path": project_path,
            "plan_number": plan_number,
        })

    @mcp.tool()
    def get_plan_results_summary(project_path: str, plan_number: str) -> dict:
        """ras-commander compatible alias for plan results summary."""
        tool = HydroClaudeMCPTool()
        return tool.call("get_plan_results_summary", {
            "project_path": project_path,
            "plan_number": plan_number,
        })

    @mcp.tool()
    def get_hdf_structure(hdf_path: str, group_path: str = "/", paths_only: bool = True) -> dict:
        """ras-commander compatible alias for HDF structure browsing."""
        tool = HydroClaudeMCPTool()
        return tool.call("get_hdf_structure", {
            "hdf_path": hdf_path,
            "group_path": group_path,
            "paths_only": paths_only,
        })

    @mcp.tool()
    def get_projection_info(hdf_path: str) -> dict:
        """ras-commander compatible alias for HDF projection info."""
        tool = HydroClaudeMCPTool()
        return tool.call("get_projection_info", {"hdf_path": hdf_path})

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

    By default, HydroClaude serves HTTP JSON-RPC on ``SERVER_PORT`` so that
    HydroMind gateway components can call it over the network. Set
    ``HYDROCLAUDE_MCP_TRANSPORT=stdio`` to force stdio FastMCP mode.
    """
    if _FASTMCP_AVAILABLE and _SERVER_TRANSPORT == "stdio":
        logger.info("Using FastMCP transport")
        return _create_fastmcp_server()
    else:
        logger.info(
            "Using HTTP JSON-RPC transport on %s:%d (FastMCP stdio=%s)",
            HOST,
            SERVER_PORT,
            "enabled" if _FASTMCP_AVAILABLE else "unavailable",
        )
        return HTTPServer((HOST, SERVER_PORT), _JsonRpcHandler)


def _build_registration_payload() -> dict[str, Any]:
    client_host = "127.0.0.1" if HOST in {"0.0.0.0", "::"} else HOST
    endpoint = f"http://{client_host}:{SERVER_PORT}"
    tool = HydroClaudeMCPTool()
    return {
        "engine_id": ENGINE_NAME,
        "name": ENGINE_NAME,
        "version": ENGINE_VERSION,
        "transport": "jsonrpc",
        "endpoint": endpoint,
        "health_url": endpoint,
        "tools": [item["name"] for item in tool.list_tools()],
        "capabilities": ENGINE_CAPABILITIES,
        "source": "hydroclaude_server",
    }


def _register_with_gateway_once() -> bool:
    gateway_host = os.environ.get("HYDROMAS_GATEWAY_HOST", "127.0.0.1")
    gateway_port = int(os.environ.get("HYDROMAS_GATEWAY_PORT", "8040"))
    url = f"http://{gateway_host}:{gateway_port}/api/gateway/engines/register"
    payload = _build_registration_payload()
    body = json.dumps(payload).encode("utf-8")
    request = Request(
        url,
        data=body,
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    try:
        with urlopen(request, timeout=5) as response:
            response.read()
        logger.info("Registered HydroClaude with HydroMAS gateway at %s", url)
        return True
    except URLError as exc:
        logger.warning("HydroClaude gateway registration failed: %s", exc)
        return False


def _start_gateway_registration_thread() -> None:
    if os.environ.get("HYDROCLAUDE_DISABLE_GATEWAY_REGISTER", "").lower() in {"1", "true", "yes"}:
        return
    if _SERVER_TRANSPORT != "http":
        return

    def _worker() -> None:
        time.sleep(1.0)
        for _ in range(5):
            if _register_with_gateway_once():
                return
            time.sleep(2.0)

    threading.Thread(target=_worker, daemon=True).start()


def main() -> None:
    """Entry point for ``python -m mcp_server.hydroclaude_server``."""
    logging.basicConfig(
        level=getattr(logging, LOG_LEVEL.upper(), logging.INFO),
        format="%(asctime)s [%(name)s] %(levelname)s: %(message)s",
    )

    server = create_server()

    if _FASTMCP_AVAILABLE and _SERVER_TRANSPORT == "stdio":
        logger.info("Starting HydroClaude MCP server (FastMCP)")
        server.run()
    else:
        logger.info("Starting HydroClaude MCP server (JSON-RPC) on %s:%d", HOST, SERVER_PORT)
        _start_gateway_registration_thread()
        try:
            server.serve_forever()
        except KeyboardInterrupt:
            logger.info("Shutting down")
            server.server_close()


if __name__ == "__main__":
    main()
