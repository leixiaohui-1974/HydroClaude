#!/usr/bin/env python
"""Verify the HydroMind writer chain end-to-end.

This script ensures the local HydroWriter MCP HTTP service is available,
checks its JSON-RPC tool discovery endpoint, and verifies that
``mcp_server.report_bridge.ReportBridge`` resolves to the direct MCP writer
path instead of falling back to the in-process or local generator.
"""

from __future__ import annotations

import json
import subprocess
import sys
import time
from pathlib import Path
from typing import Any

import requests


ROOT = Path(__file__).resolve().parents[1]
HYDROWRITER_ROOT = ROOT.parent / "HydroWriter"
WRITER_HEALTH_URL = "http://127.0.0.1:8033/health"
WRITER_JSONRPC_URL = "http://127.0.0.1:8033/jsonrpc"


def _wait_for_writer(timeout_seconds: float = 20.0) -> bool:
    deadline = time.time() + timeout_seconds
    while time.time() < deadline:
        try:
            response = requests.get(WRITER_HEALTH_URL, timeout=2.0)
            if response.status_code == 200:
                return True
        except Exception:
            pass
        time.sleep(1.0)
    return False


def _start_writer_if_needed() -> str:
    if _wait_for_writer(timeout_seconds=1.0):
        return "already_running"

    if not HYDROWRITER_ROOT.exists():
        raise FileNotFoundError(f"HydroWriter repository not found: {HYDROWRITER_ROOT}")

    subprocess.Popen(
        [sys.executable, "-m", "hydrowriter.mcp_server"],
        cwd=str(HYDROWRITER_ROOT),
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
        creationflags=getattr(subprocess, "CREATE_NEW_PROCESS_GROUP", 0),
    )

    if not _wait_for_writer():
        raise RuntimeError("HydroWriter MCP service did not become healthy on port 8033")
    return "started"


def _check_list_tools() -> dict[str, Any]:
    payload = {"jsonrpc": "2.0", "method": "list_tools", "params": {}, "id": 1}
    response = requests.post(WRITER_JSONRPC_URL, json=payload, timeout=10.0)
    response.raise_for_status()
    result = response.json()
    tools = result.get("result", {}).get("results", [])
    tool_names = {tool["name"] for tool in tools}
    required = {"write_chapter", "review_content", "generate_ppt", "get_engine_status"}
    missing = sorted(required - tool_names)
    if missing:
        raise AssertionError(f"HydroWriter list_tools missing entries: {missing}")
    return {"tool_count": len(tools), "tool_names": sorted(tool_names)}


def _check_report_bridge() -> dict[str, Any]:
    sys.path.insert(0, str(ROOT))
    from mcp_server.report_bridge import ReportBridge

    bridge = ReportBridge(timeout=10.0)
    result = bridge.generate_simulation_report(
        results={"summary": {"metric": 7, "purpose": "hydromind-chain-smoke"}},
        config={"project_name": "HydroMind writer chain verification", "output_dir": "reports"},
    )
    if bridge.last_backend != "mcp_direct":
        raise AssertionError(f"Expected mcp_direct backend, got {bridge.last_backend!r}")
    return {
        "backend": bridge.last_backend,
        "method": result.get("method"),
    }


def main() -> int:
    startup_state = _start_writer_if_needed()
    tool_info = _check_list_tools()
    bridge_info = _check_report_bridge()

    print(
        json.dumps(
            {
                "writer": startup_state,
                "health_url": WRITER_HEALTH_URL,
                "list_tools": tool_info,
                "report_bridge": bridge_info,
            },
            ensure_ascii=False,
            indent=2,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
