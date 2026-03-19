"""HydroClaude MCP Server configuration."""

import os

# ---------------------------------------------------------------------------
# Server networking
# ---------------------------------------------------------------------------
HOST: str = os.environ.get("HYDROCLAUDE_MCP_HOST", "0.0.0.0")
SERVER_PORT: int = int(os.environ.get("HYDROCLAUDE_MCP_PORT", "8005"))
LOG_LEVEL: str = os.environ.get("HYDROCLAUDE_LOG_LEVEL", "INFO")

# ---------------------------------------------------------------------------
# Engine metadata -- used by engine_registry discovery
# ---------------------------------------------------------------------------
ENGINE_NAME: str = "hydroclaude"
ENGINE_VERSION: str = "2.0.0"
ENGINE_CAPABILITIES: list[str] = [
    "canal_simulation",
    "network_analysis",
    "steady_state",
    "transient_simulation",
    "pid_control",
    "mpc_control",
    "hardy_cross",
    "godunov_fvm",
    "hydrostatic_reconstruction",
    "steady_profile",
    "water_hammer",
]
