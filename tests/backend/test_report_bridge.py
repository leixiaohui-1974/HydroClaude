"""Tests for mcp_server.report_bridge — MCP report generation bridge.

Covers:
- Local fallback when MCP servers are unreachable
- MCP request formatting (gateway + direct)
- Timeout / connection-error handling
- Mock HTTP calls for the MCP server path
"""

from __future__ import annotations

import json
import sys
import types
from pathlib import Path
from typing import Any, Dict
from unittest.mock import MagicMock, patch

import pytest

# ---------------------------------------------------------------------------
# Ensure project root is on sys.path so "mcp_server" and "utils" resolve.
# ---------------------------------------------------------------------------
_PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(_PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(_PROJECT_ROOT))

from mcp_server.report_bridge import (
    ReportBridge,
    _build_mcp_direct_request,
    _build_mcp_gateway_request,
    _local_generate_report,
    _sanitize,
)


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture()
def bridge() -> ReportBridge:
    """A bridge pointing at localhost with a short timeout."""
    return ReportBridge(
        gateway_host="127.0.0.1",
        gateway_port=8040,
        writer_host="127.0.0.1",
        writer_port=8033,
        timeout=2.0,
    )


@pytest.fixture()
def sample_results() -> Dict[str, Any]:
    return {
        "max_depth": 3.5,
        "min_depth": 1.2,
        "avg_flow": 15.3,
        "iterations": 42,
    }


@pytest.fixture()
def sample_config() -> Dict[str, Any]:
    return {
        "project_name": "测试项目",
        "output_dir": "test_reports",
        "length": 10000.0,
        "slope": 0.001,
    }


@pytest.fixture()
def sample_validation() -> Dict[str, Any]:
    return {
        "rmse": 0.023,
        "nse": 0.95,
        "r_squared": 0.97,
        "bias": -0.002,
    }


@pytest.fixture()
def sample_convergence() -> Dict[str, Any]:
    return {
        "iterations": 25,
        "final_residual": 1e-8,
        "converged": True,
        "residual_history": [1e-1, 1e-3, 1e-5, 1e-8],
    }


# ===================================================================
# 1. MCP request formatting
# ===================================================================

class TestRequestFormatting:
    """Verify the shape of MCP request payloads."""

    def test_gateway_request_has_tool_name_and_params(self):
        req = _build_mcp_gateway_request("write_chapter", {"topic": "t"})
        assert req["tool_name"] == "write_chapter"
        assert req["params"] == {"topic": "t"}

    def test_direct_request_is_jsonrpc(self):
        req = _build_mcp_direct_request("write_chapter", {"topic": "t"})
        assert req["jsonrpc"] == "2.0"
        assert req["method"] == "write_chapter"
        assert req["params"] == {"topic": "t"}
        assert isinstance(req["id"], int)

    def test_gateway_request_empty_params(self):
        req = _build_mcp_gateway_request("get_engine_status", {})
        assert req["params"] == {}

    def test_direct_request_empty_params(self):
        req = _build_mcp_direct_request("get_engine_status", {})
        assert req["params"] == {}


# ===================================================================
# 2. Local fallback
# ===================================================================

class TestLocalFallback:
    """Local report generation should work without any running server."""

    def test_simulation_report_fallback(
        self, bridge: ReportBridge, sample_results, sample_config, tmp_path
    ):
        sample_config["output_dir"] = str(tmp_path)
        result = bridge.generate_simulation_report(sample_results, sample_config)

        assert result["success"] is True
        assert result["backend"] == "local"
        assert "markdown_path" in result["results"]
        assert "html_path" in result["results"]
        assert "json_path" in result["results"]
        # Files should actually exist
        assert Path(result["results"]["markdown_path"]).exists()
        assert Path(result["results"]["html_path"]).exists()

    def test_validation_report_fallback(
        self, bridge: ReportBridge, sample_validation, tmp_path
    ):
        # Patch output_dir into a default config via the local generator
        with patch(
            "mcp_server.report_bridge._local_generate_report",
            wraps=_local_generate_report,
        ) as wrapped:
            result = bridge.generate_validation_report(sample_validation)

        assert result["success"] is True
        assert result["backend"] == "local"
        assert result["method"] == "generate_validation_report"

    def test_convergence_report_fallback(
        self, bridge: ReportBridge, sample_convergence
    ):
        result = bridge.generate_convergence_report(sample_convergence)

        assert result["success"] is True
        assert result["backend"] == "local"
        assert result["method"] == "generate_convergence_report"

    def test_last_backend_is_local_after_fallback(
        self, bridge: ReportBridge, sample_results
    ):
        bridge.generate_simulation_report(sample_results)
        assert bridge.last_backend == "local"

    def test_local_generate_report_simulation(self, tmp_path):
        data = {"max_depth": 2.0}
        config = {"project_name": "Unit Test", "output_dir": str(tmp_path)}
        result = _local_generate_report("simulation", data, config)

        assert result["success"] is True
        assert result["backend"] == "local"
        md = Path(result["results"]["markdown_path"])
        assert md.exists()
        content = md.read_text(encoding="utf-8")
        assert "Unit Test" in content

    def test_local_generate_report_validation_list(self, tmp_path):
        data = [{"rmse": 0.01}, {"rmse": 0.02}]
        config = {"output_dir": str(tmp_path)}
        result = _local_generate_report("validation", data, config)
        assert result["success"] is True

    def test_local_generate_report_convergence(self, tmp_path):
        data = {"iterations": 10, "converged": True}
        config = {"output_dir": str(tmp_path)}
        result = _local_generate_report("convergence", data, config)
        assert result["success"] is True


# ===================================================================
# 3. Timeout and connection error handling
# ===================================================================

class TestTimeoutHandling:
    """Verify that timeouts and connection errors trigger local fallback."""

    def test_timeout_triggers_fallback(self, bridge: ReportBridge, sample_results):
        """When both gateway and direct server time out, we get local."""
        import mcp_server.report_bridge as rb_mod

        def fake_post(url, payload, timeout):
            raise ConnectionError("simulated timeout")

        with patch.object(rb_mod, "_post", side_effect=fake_post):
            result = bridge.generate_simulation_report(sample_results)

        assert result["success"] is True
        assert result["backend"] == "local"

    def test_connection_refused_triggers_fallback(
        self, bridge: ReportBridge, sample_validation
    ):
        import mcp_server.report_bridge as rb_mod

        def fake_post(url, payload, timeout):
            raise OSError("Connection refused")

        with patch.object(rb_mod, "_post", side_effect=fake_post):
            result = bridge.generate_validation_report(sample_validation)

        assert result["success"] is True
        assert result["backend"] == "local"

    def test_custom_timeout_value(self):
        b = ReportBridge(timeout=30.0)
        assert b.timeout == 30.0

    def test_default_timeout(self):
        b = ReportBridge()
        assert b.timeout == 10.0


# ===================================================================
# 4. Mocked MCP server calls
# ===================================================================

class TestMCPServerCalls:
    """Mock _post to simulate a working MCP server."""

    def _mock_mcp_response(self) -> dict:
        return {
            "success": True,
            "method": "write_chapter",
            "results": {
                "content": "# Report\n\nGenerated content here.",
                "draft_length": 120,
                "final_length": 100,
                "average_score": 0.85,
                "engines_used": ["claude", "gpt"],
            },
        }

    def test_gateway_success(self, bridge: ReportBridge, sample_results, sample_config):
        """When the gateway responds, we should use it and set backend."""
        import mcp_server.report_bridge as rb_mod

        with patch.object(rb_mod, "_post", return_value=self._mock_mcp_response()):
            result = bridge.generate_simulation_report(sample_results, sample_config)

        assert result["success"] is True
        assert result["backend"] == "mcp_gateway"
        assert "content" in result["results"]

    def test_gateway_down_direct_succeeds(
        self, bridge: ReportBridge, sample_results
    ):
        """When gateway fails but direct writer works, use direct."""
        import mcp_server.report_bridge as rb_mod

        call_count = 0

        def selective_post(url, payload, timeout):
            nonlocal call_count
            call_count += 1
            if "8040" in url:
                raise ConnectionError("gateway down")
            return self._mock_mcp_response()

        with patch.object(rb_mod, "_post", side_effect=selective_post):
            result = bridge.generate_simulation_report(sample_results)

        assert result["backend"] == "mcp_direct"
        assert call_count == 2  # gateway attempt + direct attempt

    def test_gateway_success_for_validation(
        self, bridge: ReportBridge, sample_validation
    ):
        import mcp_server.report_bridge as rb_mod

        with patch.object(rb_mod, "_post", return_value=self._mock_mcp_response()):
            result = bridge.generate_validation_report(sample_validation)

        assert result["success"] is True
        assert result["backend"] == "mcp_gateway"

    def test_gateway_success_for_convergence(
        self, bridge: ReportBridge, sample_convergence
    ):
        import mcp_server.report_bridge as rb_mod

        with patch.object(rb_mod, "_post", return_value=self._mock_mcp_response()):
            result = bridge.generate_convergence_report(sample_convergence)

        assert result["success"] is True
        assert result["backend"] == "mcp_gateway"

    def test_direct_jsonrpc_unwrap(self, bridge: ReportBridge, sample_results):
        """Direct writer returns JSON-RPC envelope — verify unwrap."""
        import mcp_server.report_bridge as rb_mod

        jsonrpc_response = {
            "jsonrpc": "2.0",
            "id": 1,
            "result": self._mock_mcp_response(),
        }

        call_count = 0

        def selective_post(url, payload, timeout):
            nonlocal call_count
            call_count += 1
            if "8040" in url:
                raise ConnectionError("gateway down")
            return jsonrpc_response

        with patch.object(rb_mod, "_post", side_effect=selective_post):
            result = bridge.generate_simulation_report(sample_results)

        # The JSON-RPC "result" field should be unwrapped
        assert result["backend"] == "mcp_direct"
        assert result["success"] is True

    def test_params_contain_topic_and_context(
        self, bridge: ReportBridge, sample_results, sample_config
    ):
        """Verify the params sent to the MCP server contain expected fields."""
        import mcp_server.report_bridge as rb_mod

        captured_payloads = []

        def capture_post(url, payload, timeout):
            captured_payloads.append(payload)
            return self._mock_mcp_response()

        with patch.object(rb_mod, "_post", side_effect=capture_post):
            bridge.generate_simulation_report(sample_results, sample_config)

        assert len(captured_payloads) == 1
        payload = captured_payloads[0]
        # Gateway format
        assert payload["tool_name"] == "write_chapter"
        params = payload["params"]
        assert "topic" in params
        assert "context" in params
        assert "style_guide" in params
        # Context should be valid JSON containing our data
        ctx = json.loads(params["context"])
        assert "results" in ctx
        assert "config" in ctx


# ===================================================================
# 5. Sanitize helper
# ===================================================================

class TestSanitize:
    """Verify _sanitize handles numpy and nested structures."""

    def test_plain_dict_passthrough(self):
        d = {"a": 1, "b": "hello"}
        assert _sanitize(d) == d

    def test_nested_dict(self):
        d = {"a": {"b": [1, 2, 3]}}
        assert _sanitize(d) == d

    def test_numpy_array(self):
        try:
            import numpy as np

            arr = np.array([1.0, 2.0, 3.0])
            result = _sanitize(arr)
            assert result == [1.0, 2.0, 3.0]
            assert isinstance(result, list)
        except ImportError:
            pytest.skip("numpy not installed")

    def test_numpy_scalar(self):
        try:
            import numpy as np

            val = np.float64(3.14)
            result = _sanitize(val)
            assert isinstance(result, float)
        except ImportError:
            pytest.skip("numpy not installed")

    def test_numpy_integer(self):
        try:
            import numpy as np

            val = np.int64(42)
            result = _sanitize(val)
            assert isinstance(result, int)
            assert result == 42
        except ImportError:
            pytest.skip("numpy not installed")

    def test_nested_numpy(self):
        try:
            import numpy as np

            d = {"arr": np.array([1, 2]), "val": np.float32(1.5)}
            result = _sanitize(d)
            assert result["arr"] == [1, 2]
            assert isinstance(result["val"], float)
        except ImportError:
            pytest.skip("numpy not installed")


# ===================================================================
# 6. Bridge configuration
# ===================================================================

class TestBridgeConfig:
    """Verify bridge picks up config defaults correctly."""

    def test_default_ports(self):
        b = ReportBridge()
        assert b.gateway_port == 8040
        assert b.writer_port == 8033

    def test_custom_ports(self):
        b = ReportBridge(gateway_port=9040, writer_port=9033)
        assert b.gateway_port == 9040
        assert b.writer_port == 9033

    def test_urls_built_correctly(self):
        b = ReportBridge(gateway_host="10.0.0.1", gateway_port=9040)
        assert b._gateway_url == "http://10.0.0.1:9040"

    def test_last_backend_starts_none(self):
        b = ReportBridge()
        assert b.last_backend is None
