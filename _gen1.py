import pathlib

TARGET = "Z:/research/hydroclaude/solvers/network_steady_solver.py"

code_parts = []

code_parts.append("""from __future__ import annotations
""")

# module docstring
dq = chr(34)
tq = dq * 3

code_parts.append(tq + """Multi-reach steady water surface profile solver (NetworkSteadySolver).

Supports serial (A->B->C) and Y-confluence topologies.
Iteratively calls SteadyProfileSolver per reach until junction WSE converges.
""" + tq + """

import logging
from dataclasses import dataclass, field
from typing import Any

import numpy as np

try:
    from solvers.steady_profile_solver import SteadyProfileSolver
except ImportError:
    SteadyProfileSolver = None  # type: ignore[assignment,misc]

try:
    from utils.canal_utils import compute_steady_uniform_flow
except ImportError:
    compute_steady_uniform_flow = None  # type: ignore[assignment]

logger = logging.getLogger(__name__)
_G = 9.81


# ---------------------------------------------------------------------------
# Data definitions
# ---------------------------------------------------------------------------


@dataclass
class ReachDefinition:
    """Single reach parameters."""

    reach_id: str
    length: float
    slope: float
    manning_n: float
    width: float
    cross_section: Any | None = None
    nx: int = 101


@dataclass
class JunctionDefinition:
    """Junction connecting reaches."""

    junction_id: str
    upstream_reaches: list[str] = field(default_factory=list)
    downstream_reaches: list[str] = field(default_factory=list)
    boundary_type: str | None = None   # wse | Q | None
    boundary_value: float | None = None
    elevation: float = 0.0
    junction_type: str = "confluence"  # confluence | bifurcation | source | outlet

""")

pathlib.Path(TARGET).write_text("".join(code_parts), encoding="utf-8")
print(f"written {len("".join(code_parts))} bytes")
