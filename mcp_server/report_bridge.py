"""Report generation bridge — MCP-first with local fallback.

Calls HydroClaw's hydrowriter_server via the MCP Gateway (port 8040)
or directly (port 8033) to generate reports.  Falls back to the local
``utils.report_generator.ReportGenerator`` when the remote server is
unreachable.

Usage::

    bridge = ReportBridge()
    result = await bridge.generate_simulation_report(results, config)
"""

from __future__ import annotations

import asyncio
import json
import logging
import sys
import threading
import time
from pathlib import Path
from typing import Any, Dict, Optional

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Defaults
# ---------------------------------------------------------------------------
_DEFAULT_GATEWAY_PORT = 8040
_DEFAULT_WRITER_PORT = 8033
_DEFAULT_GATEWAY_HOST = "127.0.0.1"
_DEFAULT_TIMEOUT = 10.0  # seconds


def _run_coro_sync(coro):
    """Run an async coroutine from sync code.

    Uses ``asyncio.run`` in the normal case and falls back to a temporary
    worker thread when the current thread already owns a running event loop.
    """
    try:
        asyncio.get_running_loop()
    except RuntimeError:
        return asyncio.run(coro)

    result_box: dict[str, Any] = {}
    error_box: dict[str, BaseException] = {}

    def _worker() -> None:
        try:
            result_box["result"] = asyncio.run(coro)
        except BaseException as exc:  # pragma: no cover - defensive bridge
            error_box["error"] = exc

    thread = threading.Thread(target=_worker, daemon=True)
    thread.start()
    thread.join()

    if "error" in error_box:
        raise error_box["error"]
    return result_box.get("result")

# ---------------------------------------------------------------------------
# Helpers — HTTP transport via httpx (preferred) or requests fallback
# ---------------------------------------------------------------------------

_http_client_module: Optional[str] = None


def _post(url: str, payload: dict, timeout: float) -> dict:
    """POST JSON and return the parsed response body.

    Tries *httpx* first (async-friendly library already used elsewhere in
    HydroClaw), then falls back to *requests*.  Raises on connection /
    timeout errors so the caller can trigger the local fallback.
    """
    global _http_client_module

    # --- httpx path ---
    if _http_client_module != "requests":
        try:
            import httpx  # type: ignore[import-untyped]

            _http_client_module = "httpx"
            resp = httpx.post(url, json=payload, timeout=timeout)
            resp.raise_for_status()
            return resp.json()
        except ImportError:
            _http_client_module = "requests"  # try requests below
        except Exception:
            raise  # connection / timeout — propagate

    # --- requests path ---
    import requests as _requests  # type: ignore[import-untyped]

    _http_client_module = "requests"
    resp = _requests.post(url, json=payload, timeout=timeout)
    resp.raise_for_status()
    return resp.json()


# ---------------------------------------------------------------------------
# MCP request formatting
# ---------------------------------------------------------------------------

def _build_mcp_gateway_request(tool_name: str, params: Dict[str, Any]) -> dict:
    """Build a ``gateway_call_tool`` request for the MCP Gateway.

    The Gateway (port 8040) expects::

        {
            "tool_name": "<tool>",
            "params": { ... }
        }

    routed via its ``gateway_call_tool`` endpoint.
    """
    return {
        "tool_name": tool_name,
        "params": params,
    }


def _build_mcp_direct_request(method: str, params: Dict[str, Any]) -> dict:
    """Build a direct MCP-style JSON-RPC request for hydrowriter_server.

    Used when talking directly to port 8033.
    """
    return {
        "jsonrpc": "2.0",
        "method": method,
        "params": params,
        "id": int(time.time() * 1000),
    }


# ---------------------------------------------------------------------------
# Local fallback helper
# ---------------------------------------------------------------------------

def _local_generate_report(
    report_type: str,
    data: Dict[str, Any],
    config: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    """Generate a report using the local ReportGenerator.

    Returns a dict that mirrors the shape of the MCP response so callers
    get a consistent interface regardless of backend.
    """
    from utils.report_generator import ReportGenerator

    config = config or {}
    project_name = config.get("project_name", "HydroClaude仿真")
    output_dir = config.get("output_dir", "reports")

    reporter = ReportGenerator(
        project_name=project_name,
        output_dir=output_dir,
    )

    # Populate the reporter based on report_type
    if report_type == "simulation":
        system_info = data.get("system_info") or config
        if system_info:
            reporter.add_system_info(system_info)
        results = data.get("results") or data
        reporter.add_results(results)

    elif report_type == "validation":
        reporter.add_section(
            title="验证数据概要",
            content=f"验证项数: {len(data)}",
            level=2,
        )
        if isinstance(data, dict):
            reporter.add_results(data)
        elif isinstance(data, list):
            for i, item in enumerate(data):
                if isinstance(item, dict):
                    reporter.add_results({f"验证项{i+1}_{k}": v for k, v in item.items()})

    elif report_type == "convergence":
        reporter.add_section(
            title="收敛分析",
            content="自动生成的收敛报告",
            level=2,
        )
        if isinstance(data, dict):
            reporter.add_results(data)

    # Generate all formats
    md_path = reporter.generate_markdown(f"{report_type}_report.md")
    html_path = reporter.generate_html(f"{report_type}_report.html")
    json_path = reporter.generate_summary_json(f"{report_type}_summary.json")

    return {
        "success": True,
        "method": f"generate_{report_type}_report",
        "backend": "local",
        "results": {
            "markdown_path": md_path,
            "html_path": html_path,
            "json_path": json_path,
        },
    }


def _find_hydrowriter_repo() -> Optional[Path]:
    """Locate the sibling HydroWriter repository if present."""
    here = Path(__file__).resolve()
    candidates = [
        here.parents[2] / "HydroWriter",
        here.parents[1] / "HydroWriter",
        Path.cwd().resolve().parents[0] / "HydroWriter" if len(Path.cwd().resolve().parents) > 0 else None,
    ]
    for candidate in candidates:
        if candidate and candidate.exists() and (candidate / "hydrowriter" / "mcp_server.py").exists():
            return candidate
    return None


def _call_inprocess_hydrowriter(tool_name: str, params: Dict[str, Any]) -> Dict[str, Any]:
    """Invoke HydroWriter directly in-process when HTTP MCP is unavailable."""
    repo_root = _find_hydrowriter_repo()
    if repo_root is None:
        raise FileNotFoundError("HydroWriter repository not found for in-process fallback")

    repo_str = str(repo_root)
    if repo_str not in sys.path:
        sys.path.insert(0, repo_str)

    from hydrowriter.mcp_server import HydroWriterMCPServer

    server = HydroWriterMCPServer(config_path=str(repo_root / "configs" / "engines.yaml"))
    handler = getattr(server, tool_name, None)
    if handler is None:
        raise AttributeError(f"HydroWriterMCPServer missing tool: {tool_name}")
    if not callable(handler):
        raise TypeError(f"HydroWriter tool is not callable: {tool_name}")
    return _run_coro_sync(handler(**params))


# ---------------------------------------------------------------------------
# ReportBridge
# ---------------------------------------------------------------------------

class ReportBridge:
    """Bridge that routes report generation to HydroClaw's hydrowriter_server
    via MCP, falling back to the local ``ReportGenerator`` when the remote
    server is not reachable.

    Resolution order:
    1. MCP Gateway on ``gateway_host:gateway_port`` (default 127.0.0.1:8040)
    2. Direct hydrowriter_server on ``writer_host:writer_port`` (default 127.0.0.1:8033)
    3. Local ``utils.report_generator.ReportGenerator``

    Parameters
    ----------
    gateway_host : str
        Hostname of the MCP Gateway.
    gateway_port : int
        Port of the MCP Gateway.
    writer_host : str
        Hostname of the hydrowriter_server (direct fallback).
    writer_port : int
        Port of the hydrowriter_server.
    timeout : float
        HTTP request timeout in seconds (default 10).
    """

    def __init__(
        self,
        gateway_host: Optional[str] = None,
        gateway_port: Optional[int] = None,
        writer_host: Optional[str] = None,
        writer_port: Optional[int] = None,
        timeout: float = _DEFAULT_TIMEOUT,
    ):
        # Import config values; fall back to module-level defaults if the
        # config module does not expose these settings.
        try:
            from mcp_server.config import HOST as _cfg_host
            from mcp_server.config import SERVER_PORT as _cfg_port  # noqa: F841
        except ImportError:
            _cfg_host = _DEFAULT_GATEWAY_HOST

        self.gateway_host = gateway_host or _cfg_host or _DEFAULT_GATEWAY_HOST
        self.gateway_port = gateway_port or _DEFAULT_GATEWAY_PORT
        self.writer_host = writer_host or _cfg_host or _DEFAULT_GATEWAY_HOST
        self.writer_port = writer_port or _DEFAULT_WRITER_PORT
        self.timeout = timeout

        self._gateway_url = f"http://{self.gateway_host}:{self.gateway_port}"
        self._writer_url = f"http://{self.writer_host}:{self.writer_port}"

        # Track which backend was used for the last call (for diagnostics)
        self.last_backend: Optional[str] = None

    # ------------------------------------------------------------------
    # Internal: try remote, then local
    # ------------------------------------------------------------------

    def _call_remote(
        self,
        tool_name: str,
        params: Dict[str, Any],
    ) -> Dict[str, Any]:
        """Try the MCP Gateway first, then direct hydrowriter_server.

        Raises on total failure so the caller can trigger local fallback.
        """
        # 1) Gateway
        try:
            gateway_payload = _build_mcp_gateway_request(tool_name, params)
            result = _post(
                f"{self._gateway_url}/call_tool",
                gateway_payload,
                self.timeout,
            )
            self.last_backend = "mcp_gateway"
            logger.info(
                "Report generated via MCP Gateway (%s): tool=%s",
                self._gateway_url,
                tool_name,
            )
            return result
        except Exception as gw_err:
            logger.debug(
                "MCP Gateway unavailable (%s): %s — trying direct writer",
                self._gateway_url,
                gw_err,
            )

        # 2) Direct hydrowriter_server
        try:
            direct_payload = _build_mcp_direct_request(tool_name, params)
            result = _post(
                f"{self._writer_url}/jsonrpc",
                direct_payload,
                self.timeout,
            )
            # JSON-RPC envelope: unwrap if needed
            if "result" in result:
                result = result["result"]
            self.last_backend = "mcp_direct"
            logger.info(
                "Report generated via direct hydrowriter (%s): tool=%s",
                self._writer_url,
                tool_name,
            )
            return result
        except Exception as direct_err:
            logger.debug(
                "Direct hydrowriter unavailable (%s): %s",
                self._writer_url,
                direct_err,
            )
            raise  # let caller fall back to local

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def generate_simulation_report(
        self,
        results: Dict[str, Any],
        config: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """Generate a simulation report.

        Parameters
        ----------
        results : dict
            Simulation result data (depths, flows, timings, etc.).
        config : dict, optional
            Simulation configuration / system info.

        Returns
        -------
        dict
            ``{"success": bool, "method": str, "backend": str, "results": ...}``
        """
        config = config or {}
        params = {
            "topic": config.get("project_name", "仿真结果报告"),
            "context": json.dumps(
                {"results": _sanitize(results), "config": _sanitize(config)},
                ensure_ascii=False,
                default=str,
            ),
            "style_guide": "专业水利仿真报告，包含系统配置、结果摘要、图表分析",
        }

        try:
            response = self._call_remote("write_chapter", params)
            response["backend"] = self.last_backend
            return response
        except Exception:
            logger.info(
                "Remote HydroWriter unavailable — trying in-process HydroWriter"
            )
        try:
            response = _call_inprocess_hydrowriter("write_chapter", params)
            self.last_backend = "hydrowriter_inprocess"
            response["backend"] = self.last_backend
            return response
        except Exception:
            logger.info(
                "In-process HydroWriter unavailable — using local report generator"
            )
            self.last_backend = "local"
            return _local_generate_report(
                "simulation", results, config,
            )

    def generate_validation_report(
        self,
        validation_data: Dict[str, Any],
    ) -> Dict[str, Any]:
        """Generate a validation / comparison report.

        Parameters
        ----------
        validation_data : dict
            Validation metrics, observed vs. computed, error stats, etc.

        Returns
        -------
        dict
            ``{"success": bool, "method": str, "backend": str, "results": ...}``
        """
        params = {
            "topic": "模型验证报告",
            "context": json.dumps(
                {"validation": _sanitize(validation_data)},
                ensure_ascii=False,
                default=str,
            ),
            "style_guide": "专业模型验证报告，包含误差分析、对比图表、结论",
        }

        try:
            response = self._call_remote("write_chapter", params)
            response["backend"] = self.last_backend
            return response
        except Exception:
            logger.info(
                "Remote HydroWriter unavailable — trying in-process HydroWriter"
            )
        try:
            response = _call_inprocess_hydrowriter("write_chapter", params)
            self.last_backend = "hydrowriter_inprocess"
            response["backend"] = self.last_backend
            return response
        except Exception:
            logger.info(
                "In-process HydroWriter unavailable — using local report generator"
            )
            self.last_backend = "local"
            return _local_generate_report("validation", validation_data)

    def generate_convergence_report(
        self,
        convergence_data: Dict[str, Any],
    ) -> Dict[str, Any]:
        """Generate a convergence analysis report.

        Parameters
        ----------
        convergence_data : dict
            Iteration counts, residual histories, convergence criteria, etc.

        Returns
        -------
        dict
            ``{"success": bool, "method": str, "backend": str, "results": ...}``
        """
        params = {
            "topic": "收敛性分析报告",
            "context": json.dumps(
                {"convergence": _sanitize(convergence_data)},
                ensure_ascii=False,
                default=str,
            ),
            "style_guide": "收敛性分析报告，包含迭代历史、残差曲线、收敛判据",
        }

        try:
            response = self._call_remote("write_chapter", params)
            response["backend"] = self.last_backend
            return response
        except Exception:
            logger.info(
                "Remote HydroWriter unavailable — trying in-process HydroWriter"
            )
        try:
            response = _call_inprocess_hydrowriter("write_chapter", params)
            self.last_backend = "hydrowriter_inprocess"
            response["backend"] = self.last_backend
            return response
        except Exception:
            logger.info(
                "In-process HydroWriter unavailable — using local report generator"
            )
            self.last_backend = "local"
            return _local_generate_report("convergence", convergence_data)


# ---------------------------------------------------------------------------
# Utilities
# ---------------------------------------------------------------------------

def _sanitize(obj: Any) -> Any:
    """Make *obj* JSON-safe by converting numpy / non-serialisable types."""
    try:
        import numpy as np

        if isinstance(obj, np.ndarray):
            return obj.tolist()
        if isinstance(obj, (np.integer,)):
            return int(obj)
        if isinstance(obj, (np.floating,)):
            return float(obj)
    except ImportError:
        pass

    if isinstance(obj, dict):
        return {k: _sanitize(v) for k, v in obj.items()}
    if isinstance(obj, (list, tuple)):
        return [_sanitize(v) for v in obj]
    return obj
