"""Tests for the HydroClaude MCP server package.

Tests cover:
- MCPToolProtocol compliance (call / list_tools)
- SimulatorProtocol compliance (simulate / get_state / set_boundary)
- ControllerProtocol compliance (compute_action / set_target)
- Individual tool functions
- Error handling (invalid params, missing data)
- Engine discovery function
"""

from __future__ import annotations

import sys
import os
import math
import pytest

# Ensure project root is on sys.path so that solver imports work.
_PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
if _PROJECT_ROOT not in sys.path:
    sys.path.insert(0, _PROJECT_ROOT)


# ==================================================================
# Fixtures
# ==================================================================

@pytest.fixture
def simulator():
    from mcp_server.adapters.simulator_adapter import HydroClaudeSimulator
    return HydroClaudeSimulator()


@pytest.fixture
def controller():
    from mcp_server.adapters.controller_adapter import HydroClaudeController
    return HydroClaudeController()


@pytest.fixture
def mcp_tool():
    from mcp_server.adapters.mcp_tool_adapter import HydroClaudeMCPTool
    return HydroClaudeMCPTool()


# ==================================================================
# Protocol compliance
# ==================================================================

class TestProtocolCompliance:
    """Verify that adapters satisfy the hydromind-contracts protocols."""

    def test_simulator_has_protocol_methods(self, simulator):
        assert callable(getattr(simulator, "simulate", None))
        assert callable(getattr(simulator, "get_state", None))
        assert callable(getattr(simulator, "set_boundary", None))

    def test_controller_has_protocol_methods(self, controller):
        assert callable(getattr(controller, "compute_action", None))
        assert callable(getattr(controller, "set_target", None))

    def test_mcp_tool_has_protocol_methods(self, mcp_tool):
        assert callable(getattr(mcp_tool, "call", None))
        assert callable(getattr(mcp_tool, "list_tools", None))

    def test_simulator_isinstance_check(self, simulator):
        """Runtime isinstance check against SimulatorProtocol."""
        try:
            from hydromind_contracts.simulation import SimulatorProtocol
            assert isinstance(simulator, SimulatorProtocol)
        except ImportError:
            pytest.skip("hydromind_contracts not installed")

    def test_controller_isinstance_check(self, controller):
        try:
            from hydromind_contracts.control import ControllerProtocol
            assert isinstance(controller, ControllerProtocol)
        except ImportError:
            pytest.skip("hydromind_contracts not installed")

    def test_mcp_tool_isinstance_check(self, mcp_tool):
        try:
            from hydromind_contracts.mcp_tool import MCPToolProtocol
            assert isinstance(mcp_tool, MCPToolProtocol)
        except ImportError:
            pytest.skip("hydromind_contracts not installed")


# ==================================================================
# Simulator tests
# ==================================================================

class TestSimulator:
    """Unit tests for HydroClaudeSimulator."""

    def test_simulate_hydrostatic_steady(self, simulator):
        result = simulator.simulate(
            params={
                "solver_type": "hydrostatic",
                "length": 500.0,
                "width": 8.0,
                "slope": 0.001,
                "manning_n": 0.025,
                "nx": 51,
                "Q_upstream": 5.0,
                "h_downstream": 1.0,
            },
            duration=0,
            dt=0,
        )
        assert result.get("success") is True, f"Simulation failed: {result}"
        assert result["solver_type"] == "hydrostatic"

    def test_simulate_hydrostatic_transient(self, simulator):
        result = simulator.simulate(
            params={
                "solver_type": "hydrostatic",
                "length": 200.0,
                "width": 5.0,
                "slope": 0.0005,
                "manning_n": 0.020,
                "nx": 21,
                "Q_upstream": 3.0,
                "h_downstream": 0.8,
            },
            duration=60.0,
            dt=0.5,
        )
        assert result.get("success") is True, f"Simulation failed: {result}"

    def test_simulate_steady_profile(self, simulator):
        result = simulator.simulate(
            params={
                "solver_type": "steady",
                "length": 1000.0,
                "width": 10.0,
                "slope": 0.001,
                "manning_n": 0.025,
                "Q": 10.0,
                "h_downstream": 1.0,
                "nx": 101,
                "method": "shooting",
            },
            duration=0,
            dt=0,
        )
        assert result.get("success") is True, f"Simulation failed: {result}"
        assert "h" in result

    def test_get_state_empty_initially(self, simulator):
        state = simulator.get_state()
        assert isinstance(state, dict)

    def test_set_boundary_persists(self, simulator):
        simulator.set_boundary({"Q_upstream": 15.0, "h_downstream": 2.0})
        # Boundary should be remembered
        assert simulator._boundary["Q_upstream"] == 15.0

    def test_invalid_solver_type_does_not_crash(self, simulator):
        """Unknown solver_type should return an error dict, not raise."""
        result = simulator.simulate(
            params={"solver_type": "nonexistent"},
            duration=10.0,
            dt=1.0,
        )
        # It will try hydrostatic (default fallthrough) or return error
        assert isinstance(result, dict)


# ==================================================================
# Controller tests
# ==================================================================

class TestController:
    """Unit tests for HydroClaudeController."""

    def test_pid_basic(self, controller):
        result = controller.compute_action(
            state={"h": 0.5, "controller_type": "pid", "dt": 1.0},
            target={"h": 1.0},
            constraints={},
        )
        assert "u" in result
        assert "error" in result
        assert result["controller_type"] == "pid"
        # Error should be positive (target > measurement)
        assert result["error"] > 0

    def test_pid_with_constraints(self, controller):
        controller.set_target({
            "pid_config": {"kp": 2.0, "ki": 0.5, "kd": 0.1},
        })
        result = controller.compute_action(
            state={"h": 1.5, "controller_type": "pid"},
            target={"h": 1.0},
            constraints={"output_min": -1.0, "output_max": 1.0},
        )
        assert isinstance(result["u"], float)

    def test_set_target_updates_type(self, controller):
        controller.set_target({"controller_type": "mpc"})
        assert controller._controller_type == "mpc"

    def test_mpc_graceful_on_missing_deps(self, controller):
        """MPC should not crash even if cvxpy is missing; returns error info."""
        result = controller.compute_action(
            state={"h": 0.8, "controller_type": "mpc"},
            target={"h": 1.2},
            constraints={},
        )
        assert isinstance(result, dict)
        assert "u" in result


# ==================================================================
# MCP Tool tests
# ==================================================================

class TestMCPTool:
    """Unit tests for HydroClaudeMCPTool."""

    def test_list_tools_returns_descriptors(self, mcp_tool):
        tools = mcp_tool.list_tools()
        assert isinstance(tools, list)
        assert len(tools) >= 5
        names = {t["name"] for t in tools}
        assert "run_canal_simulation" in names
        assert "run_network_analysis" in names
        assert "run_steady_state" in names
        assert "run_controller" in names
        assert "validate_results" in names
        assert "get_solver_capabilities" in names

    def test_get_solver_capabilities(self, mcp_tool):
        result = mcp_tool.call("get_solver_capabilities", {})
        assert result["engine"] == "hydroclaude"
        assert "capabilities" in result
        assert isinstance(result["capabilities"], list)

    def test_validate_results_valid(self, mcp_tool):
        result = mcp_tool.call("validate_results", {
            "h": [1.0, 1.1, 1.2, 1.0],
            "Q": [5.0, 5.1, 5.0, 4.9],
        })
        assert result["valid"] is True

    def test_validate_results_with_nan(self, mcp_tool):
        result = mcp_tool.call("validate_results", {
            "h": [1.0, float("nan"), 1.2],
        })
        assert result["valid"] is False

    def test_validate_results_negative(self, mcp_tool):
        result = mcp_tool.call("validate_results", {
            "h": [1.0, -0.5, 1.2],
        })
        assert result["valid"] is False

    def test_unknown_tool_returns_error(self, mcp_tool):
        result = mcp_tool.call("nonexistent_tool", {})
        assert "error" in result

    def test_run_canal_simulation_tool(self, mcp_tool):
        result = mcp_tool.call("run_canal_simulation", {
            "solver_type": "steady",
            "Q": 8.0,
            "h_downstream": 1.0,
            "length": 500.0,
            "width": 10.0,
            "slope": 0.001,
            "manning_n": 0.025,
            "nx": 51,
            "duration": 0,
            "dt": 0,
        })
        assert result.get("success") is True or "h" in result

    def test_run_steady_state_tool(self, mcp_tool):
        result = mcp_tool.call("run_steady_state", {
            "Q": 10.0,
            "h_downstream": 1.0,
            "length": 1000.0,
            "width": 10.0,
            "slope": 0.001,
            "manning_n": 0.025,
            "nx": 51,
        })
        assert result.get("success") is True

    def test_run_controller_tool(self, mcp_tool):
        result = mcp_tool.call("run_controller", {
            "h_current": 0.5,
            "h_target": 1.0,
            "controller_type": "pid",
            "dt": 1.0,
        })
        assert "u" in result
        assert result["error"] == pytest.approx(0.5)


# ==================================================================
# Error handling
# ==================================================================

class TestErrorHandling:
    """Ensure graceful handling of bad inputs."""

    def test_simulate_missing_params_uses_defaults(self, simulator):
        """Empty params should still work with defaults."""
        result = simulator.simulate(params={}, duration=0, dt=0)
        assert isinstance(result, dict)

    def test_validate_empty_arrays(self, mcp_tool):
        result = mcp_tool.call("validate_results", {"h": [], "Q": []})
        assert isinstance(result, dict)
        # Empty arrays have no NaN/Inf/negative -> valid
        assert result["valid"] is True

    def test_network_analysis_empty_input(self, mcp_tool):
        result = mcp_tool.call("run_network_analysis", {"nodes": [], "pipes": []})
        assert "error" in result

    def test_controller_extreme_values(self, controller):
        result = controller.compute_action(
            state={"h": 1e6},
            target={"h": 0.0},
            constraints={},
        )
        assert isinstance(result, dict)
        assert math.isfinite(result.get("u", 0.0))


# ==================================================================
# Engine discovery
# ==================================================================

class TestEngineDiscovery:
    """Test the engine entry point function."""

    def test_discover_returns_metadata(self):
        from mcp_server.engine_entry import discover_hydroclaude_engine
        info = discover_hydroclaude_engine()
        assert info["name"] == "hydroclaude"
        assert info["version"] == "2.0.0"
        assert "capabilities" in info
        assert "simulator_class" in info
        assert "controller_class" in info
        assert "mcp_tool_class" in info
        assert "server_module" in info

    def test_engine_capabilities_non_empty(self):
        from mcp_server.engine_entry import discover_hydroclaude_engine
        info = discover_hydroclaude_engine()
        assert len(info["capabilities"]) > 0

    def test_import_paths_are_valid_strings(self):
        from mcp_server.engine_entry import discover_hydroclaude_engine
        info = discover_hydroclaude_engine()
        for key in ("simulator_class", "controller_class", "mcp_tool_class"):
            assert ":" in info[key], f"{key} should be 'module:class' format"


# ==================================================================
# Config
# ==================================================================

class TestConfig:
    """Test server configuration module."""

    def test_config_defaults(self):
        from mcp_server.config import HOST, SERVER_PORT, LOG_LEVEL, ENGINE_NAME
        assert SERVER_PORT == 8005
        assert isinstance(HOST, str)
        assert isinstance(LOG_LEVEL, str)
        assert ENGINE_NAME == "hydroclaude"

    def test_capabilities_list(self):
        from mcp_server.config import ENGINE_CAPABILITIES
        assert isinstance(ENGINE_CAPABILITIES, list)
        assert "godunov_fvm" in ENGINE_CAPABILITIES
        assert "hardy_cross" in ENGINE_CAPABILITIES
        assert "pid_control" in ENGINE_CAPABILITIES
