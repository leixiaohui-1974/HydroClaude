"""HydroClaude MCP Server -- exposes hydraulic solvers as MCP tools.

This package wraps the HydroClaude solver library (Godunov FVM, Hydrostatic
Reconstruction, Hardy-Cross, Steady Profile, PID/MPC controllers) behind
the HydroMind protocol contracts so that it can participate in the HydroMind
multi-engine ecosystem.
"""

__version__ = "0.1.0"

from mcp_server.config import ENGINE_NAME, ENGINE_VERSION, SERVER_PORT
from mcp_server.engine_entry import discover_hydroclaude_engine

__all__ = [
    "ENGINE_NAME",
    "ENGINE_VERSION",
    "SERVER_PORT",
    "discover_hydroclaude_engine",
]
