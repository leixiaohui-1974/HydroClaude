"""HydroClaude MCP adapter layer.

Adapters bridge the HydroMind contract protocols to the concrete HydroClaude
solver implementations.
"""

from mcp_server.adapters.simulator_adapter import HydroClaudeSimulator
from mcp_server.adapters.controller_adapter import HydroClaudeController
from mcp_server.adapters.mcp_tool_adapter import HydroClaudeMCPTool

__all__ = [
    "HydroClaudeSimulator",
    "HydroClaudeController",
    "HydroClaudeMCPTool",
]
