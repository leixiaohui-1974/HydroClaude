"""Engine entry point for hydromind.engines discovery.

This module is referenced by the ``hydromind.engines`` entry-point group
in ``setup.py`` so that ``hydromind_contracts.engine_registry.discover_engines()``
can find and load the HydroClaude engine at runtime.
"""

from __future__ import annotations

from mcp_server.config import ENGINE_CAPABILITIES, ENGINE_NAME, ENGINE_VERSION


def discover_hydroclaude_engine() -> dict:
    """Return engine metadata for the HydroMind engine registry.

    This function is the target of the entry-point::

        [hydromind.engines]
        hydroclaude = mcp_server.engine_entry:discover_hydroclaude_engine

    Returns:
        Dictionary with keys:
            - name (str)
            - version (str)
            - capabilities (list[str])
            - simulator_class (str) -- importable path
            - controller_class (str) -- importable path
            - mcp_tool_class (str) -- importable path
            - server_module (str) -- importable path for standalone startup
    """
    return {
        "name": ENGINE_NAME,
        "version": ENGINE_VERSION,
        "capabilities": ENGINE_CAPABILITIES,
        "simulator_class": "mcp_server.adapters.simulator_adapter:HydroClaudeSimulator",
        "controller_class": "mcp_server.adapters.controller_adapter:HydroClaudeController",
        "mcp_tool_class": "mcp_server.adapters.mcp_tool_adapter:HydroClaudeMCPTool",
        "server_module": "mcp_server.hydroclaude_server",
    }
