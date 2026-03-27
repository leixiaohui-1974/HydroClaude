# HydroClaude MCP Integration Guide

## Architecture

HydroClaude is the hydraulic simulation engine in the HydroMind ecosystem, exposed as an MCP (Model Context Protocol) server on **port 8005**. It receives computation requests from the HydroMind gateway and returns structured results conforming to `hydromind-contracts`.

```
HydroMind Gateway (port 8040)
    |
    +-- HydroClaude  (port 8005) -- hydraulic simulation
    +-- HydroOS      (port 8001) -- runtime management
    +-- Other engines ...
```

## Starting the MCP Server

```bash
# Start on default port 8005
python -m mcp_server.hydroclaude_server

# Or via entry point (if installed)
hydroclaude-mcp
```

The server registers itself with the HydroMind gateway at `http://localhost:8040` on startup.

## Available Tools

| Tool | Description |
|------|-------------|
| `run_canal_simulation` | 1-D open channel simulation (hydrostatic / godunov / steady) |
| `run_network_analysis` | Hardy-Cross pipe network analysis |
| `run_steady_state` | Steady-state water surface profile computation |
| `run_controller` | PID / MPC water level control |
| `validate_results` | Result validation (NaN / Inf / negative depth checks) |
| `get_solver_capabilities` | Engine metadata and capability query |

## Protocol Compliance with hydromind-contracts

HydroClaude implements the three Protocols defined in `hydromind-contracts`:

- **SimulatorProtocol** -- `mcp_server.adapters.simulator_adapter.HydroClaudeSimulator`
- **ControllerProtocol** -- `mcp_server.adapters.controller_adapter.HydroClaudeController`
- **MCPToolProtocol** -- `mcp_server.adapters.mcp_tool_adapter.HydroClaudeMCPTool`

Each adapter wraps the corresponding HydroClaude solver and translates between contract data models and internal representations.

## Registration with HydroMind Gateway

On startup the MCP server sends a registration request to the gateway:

```
POST http://localhost:8040/api/engines/register
{
  "engine_id": "hydroclaude",
  "name": "HydroClaude Hydraulic Engine",
  "port": 8005,
  "tools": ["run_canal_simulation", "run_network_analysis", ...]
}
```

The gateway periodically health-checks registered engines via `GET /health`.

## Testing

```bash
pytest tests/backend/test_mcp_server.py -v
```
