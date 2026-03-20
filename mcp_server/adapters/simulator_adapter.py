"""Simulator adapter -- implements SimulatorProtocol from hydromind-contracts.

Wraps HydroClaude solvers (GodunvFVMSolver, HydrostaticCanalSolver,
SteadyProfileSolver) behind the uniform ``SimulatorProtocol`` interface.
"""

from __future__ import annotations

import logging
from typing import Any

import numpy as np

logger = logging.getLogger(__name__)


class HydroClaudeSimulator:
    """SimulatorProtocol implementation backed by HydroClaude solvers.

    Satisfies ``hydromind_contracts.SimulatorProtocol`` (duck-typed /
    runtime-checkable Protocol).

    Supported solver types (set via *params["solver_type"]*):
        - ``"hydrostatic"`` -- HydrostaticCanalSolver (default)
        - ``"godunov"``     -- GodunvFVMSolver
        - ``"steady"``      -- SteadyProfileSolver
    """

    def __init__(self) -> None:
        self._state: dict = {}
        self._boundary: dict = {}
        self._last_result: dict = {}

    # ------------------------------------------------------------------
    # SimulatorProtocol.simulate
    # ------------------------------------------------------------------
    def simulate(self, params: dict, duration: float, dt: float) -> dict:
        """Run a simulation using the requested HydroClaude solver.

        Args:
            params: Model parameters.  Expected keys depend on solver_type:
                - Common: solver_type, length, width (B), slope (S0),
                  manning_n, nx, Q_upstream, h_downstream
                - godunov extras: cfl, order, riemann_solver
                - steady extras: method ("shooting" | "bvp")
            duration: Simulation duration in seconds.
            dt: Time step in seconds.

        Returns:
            Dictionary with keys:
                - time, h, Q (arrays serialised as lists)
                - summary (dict with convergence info, mass balance, etc.)
                - solver_type (str)
        """
        solver_type = params.get("solver_type", "hydrostatic")
        try:
            if solver_type == "godunov":
                result = self._run_godunov(params, duration, dt)
            elif solver_type == "steady":
                result = self._run_steady(params)
            else:
                result = self._run_hydrostatic(params, duration, dt)
        except Exception as exc:
            logger.exception("Simulation failed")
            return {
                "error": str(exc),
                "solver_type": solver_type,
                "success": False,
            }

        self._last_result = result
        result["success"] = True
        result["solver_type"] = solver_type
        return result

    # ------------------------------------------------------------------
    # SimulatorProtocol.get_state
    # ------------------------------------------------------------------
    def get_state(self) -> dict:
        """Return the current internal state (latest simulation snapshot)."""
        return dict(self._state)

    # ------------------------------------------------------------------
    # SimulatorProtocol.set_boundary
    # ------------------------------------------------------------------
    def set_boundary(self, conditions: dict) -> None:
        """Store boundary conditions for the next simulation run."""
        self._boundary.update(conditions)

    # ==================================================================
    # Private solver drivers
    # ==================================================================

    def _run_hydrostatic(self, params: dict, duration: float, dt: float) -> dict:
        from solvers.hydrostatic_canal_solver import HydrostaticCanalSolver

        length = float(params.get("length", 1000.0))
        nx = int(params.get("nx", 201))
        B = float(params.get("width", params.get("B", 10.0)))
        S0 = float(params.get("slope", params.get("S0", 0.001)))
        n = float(params.get("manning_n", params.get("n", 0.025)))

        solver = HydrostaticCanalSolver(length=length, nx=nx, B=B, S0=S0, n=n)

        Q_upstream = float(
            params.get("Q_upstream", self._boundary.get("Q_upstream", 10.0))
        )
        h_downstream = params.get(
            "h_downstream", self._boundary.get("h_downstream", None)
        )

        # Prefer transient solve; fall back to steady-state
        if duration > 0 and dt > 0:
            result = solver.solve_transient(
                t_end=duration,
                dt=dt,
                Q_upstream=Q_upstream,
                h_downstream=float(h_downstream) if h_downstream is not None else None,
                save_interval=max(1, int(10 / dt)) if dt < 10 else 1,
                verbose=False,
            )
        else:
            h_ds = float(h_downstream) if h_downstream is not None else 1.0
            result = solver.solve_steady_state(
                Q_target=Q_upstream,
                h_downstream=h_ds,
                verbose=False,
            )

        self._state = {
            "h": solver.h.tolist() if hasattr(solver, "h") else [],
            "hu": (solver.hu.tolist() if hasattr(solver, "hu") else []),
        }
        return _serialise_result(result)

    def _run_godunov(self, params: dict, duration: float, dt: float) -> dict:
        from solvers.godunov_fvm_solver import GodunvFVMSolver
        from utils.canal_utils import compute_steady_uniform_flow

        width = float(params.get("width", params.get("B", 10.0)))
        length = float(params.get("length", 1000.0))
        n_cells = int(params.get("n_cells", params.get("nx", 200)))
        manning_n = float(params.get("manning_n", params.get("n", 0.025)))
        slope = params.get("slope", params.get("S0", 0.001))
        cfl = float(params.get("cfl", 0.5))
        order = int(params.get("order", 2))
        riemann = params.get("riemann_solver", "hll")
        dt_max = params.get("dt_max", None)

        solver = GodunvFVMSolver(
            width=width,
            length=length,
            n_cells=n_cells,
            manning_n=manning_n,
            slope=float(slope),
            cfl=cfl,
            order=order,
            riemann_solver=riemann,
            dt_max=float(dt_max) if dt_max is not None else None,
        )

        Q_upstream = float(
            params.get("Q_upstream", params.get("Q", self._boundary.get("Q_upstream", 10.0)))
        )
        h_downstream = params.get(
            "h_downstream",
            params.get("initial_depth", self._boundary.get("h_downstream", None)),
        )
        if h_downstream is None:
            h_downstream = compute_steady_uniform_flow(
                Q=Q_upstream,
                B=width,
                S0=float(slope),
                n=manning_n,
            )
        h_downstream = float(h_downstream)

        h_init_uniform = compute_steady_uniform_flow(
            Q=Q_upstream,
            B=width,
            S0=float(slope),
            n=manning_n,
        )
        h_init = np.ones(n_cells) * h_init_uniform
        Q_init = np.ones(n_cells) * Q_upstream
        bc_left = {"type": "Q", "value": Q_upstream}
        bc_right = {"type": "h", "value": h_downstream}
        solver.initialize(h_init, Q_init, bc_left, bc_right)

        # Time-stepping loop
        t = 0.0
        h_history: list[list[float]] = []
        q_history: list[list[float]] = []
        time_points: list[float] = []
        step_count = 0
        save_every = max(1, int(10.0 / max(dt, 1e-6)))

        while t < duration:
            step_dt = solver.compute_dt() if hasattr(solver, "compute_dt") else dt
            step_dt = min(step_dt, duration - t)
            solver.step(step_dt)
            t += step_dt
            step_count += 1
            if step_count % save_every == 0:
                h_history.append(solver.h.tolist())
                q_history.append(solver.Q.tolist())
                time_points.append(t)

        self._state = {
            "h": solver.h.tolist(),
            "Q": solver.Q.tolist() if hasattr(solver, "Q") else [],
        }
        q_in = float(solver.Q[0]) if len(solver.Q) else 0.0
        q_out = float(solver.Q[-1]) if len(solver.Q) else 0.0
        mass_error = abs(q_in - q_out) / abs(q_in) * 100 if abs(q_in) > 1e-12 else 0.0
        return {
            "x": solver.x.tolist(),
            "time": time_points,
            "h_history": h_history,
            "Q_history": q_history,
            "h_final": solver.h.tolist(),
            "Q_final": solver.Q.tolist(),
            "steps": step_count,
            "summary": {
                "Q_in": q_in,
                "Q_out": q_out,
                "mass_error_percent": mass_error,
                "h_upstream": float(solver.h[0]) if len(solver.h) else 0.0,
                "h_downstream": float(solver.h[-1]) if len(solver.h) else 0.0,
                "Q_mean": float(np.mean(solver.Q)) if len(solver.Q) else 0.0,
                "h_mean": float(np.mean(solver.h)) if len(solver.h) else 0.0,
            },
        }

    def _run_steady(self, params: dict) -> dict:
        from solvers.steady_profile_solver import SteadyProfileSolver

        length = float(params.get("length", 1000.0))
        B = float(params.get("width", params.get("B", 10.0)))
        S0 = float(params.get("slope", params.get("S0", 0.001)))
        n = float(params.get("manning_n", params.get("n", 0.025)))
        Q = float(params.get("Q", params.get("Q_upstream", 10.0)))
        h_downstream = float(params.get("h_downstream", 1.0))
        nx = int(params.get("nx", 201))
        method = params.get("method", "shooting")

        solver = SteadyProfileSolver(length=length, B=B, S0=S0, n=n)
        result = solver.solve_without_structures(Q, h_downstream, nx=nx, method=method)

        self._state = {
            "h": result["h"].tolist(),
            "Q": result["Q"].tolist(),
        }
        return _serialise_result(result)


# ======================================================================
# Helpers
# ======================================================================

def _serialise_result(result: dict) -> dict:
    """Convert numpy arrays to lists for JSON serialisation."""
    out: dict[str, Any] = {}
    for key, val in result.items():
        if isinstance(val, np.ndarray):
            out[key] = val.tolist()
        elif isinstance(val, np.integer):
            out[key] = int(val)
        elif isinstance(val, np.floating):
            out[key] = float(val)
        elif isinstance(val, list) and val and isinstance(val[0], np.ndarray):
            out[key] = [v.tolist() for v in val]
        else:
            out[key] = val
    return out
