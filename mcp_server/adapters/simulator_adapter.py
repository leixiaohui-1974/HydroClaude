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
                - Optional: cross_section_data (dict) -- 断面几何，格式：
                    {"type": "irregular"|"trapezoidal"|"rectangular",
                     "stations": [...], "elevations": [...],  # irregular
                     "bottom_width": ..., "side_slope": ...,  # trapezoidal
                     "channel_width": ...}                      # rectangular
                    不含此字段时按矩形处理（向后兼容）。
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
            elif solver_type == "network":
                result = self._run_network(params)
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


    def _build_cross_section(self, params: dict) -> Any | None:
        """从参数构造 CrossSection 对象。

        Args:
            params: 包含可选 cross_section_data 字段的参数字典。

        Returns:
            CrossSection 实例，或 None（无断面数据或构造失败时降级返回 None）。
        """
        xs_data = params.get("cross_section_data")
        if not xs_data:
            return None

        xs_type = xs_data.get("type", "rectangular")

        if xs_type == "irregular":
            stations = xs_data.get("stations")
            elevations = xs_data.get("elevations")
            if not stations or not elevations:
                logger.warning(
                    "cross_section_data type='irregular' 缺少 stations 或 elevations，降级为矩形断面"
                )
                return None
            try:
                from physics.cross_section import NaturalSection
                return NaturalSection(
                    name="hec_ras_imported",
                    elevations=np.asarray(elevations, dtype=float),
                    distances=np.asarray(stations, dtype=float),
                )
            except (ImportError, AttributeError) as exc:
                logger.warning("无法导入 NaturalSection（%s），降级为矩形断面", exc)
                return None
            except Exception as exc:
                logger.warning("构造 NaturalSection 失败（%s），降级为矩形断面", exc)
                return None

        elif xs_type == "trapezoidal":
            bottom_width = xs_data.get("bottom_width")
            side_slope = xs_data.get("side_slope")
            if bottom_width is None or side_slope is None:
                logger.warning(
                    "cross_section_data type='trapezoidal' 缺少 bottom_width 或 side_slope，降级为矩形断面"
                )
                return None
            try:
                from physics.cross_section import TrapezoidalSection
                return TrapezoidalSection(
                    name="hec_ras_imported",
                    bottom_width=float(bottom_width),
                    side_slope=float(side_slope),
                )
            except (ImportError, AttributeError) as exc:
                logger.warning("无法导入 TrapezoidalSection（%s），降级为矩形断面", exc)
                return None
            except Exception as exc:
                logger.warning("构造 TrapezoidalSection 失败（%s），降级为矩形断面", exc)
                return None

        elif xs_type == "rectangular":
            channel_width = xs_data.get("channel_width", xs_data.get("bottom_width"))
            if channel_width is None:
                logger.warning(
                    "cross_section_data type='rectangular' 缺少 channel_width，跳过断面几何"
                )
                return None
            try:
                from physics.cross_section import RectangularSection
                return RectangularSection(
                    name="hec_ras_imported",
                    width=float(channel_width),
                )
            except (ImportError, AttributeError) as exc:
                logger.warning("无法导入 RectangularSection（%s），跳过断面几何", exc)
                return None
            except Exception as exc:
                logger.warning("构造 RectangularSection 失败（%s），跳过断面几何", exc)
                return None

        elif xs_type == "multi_station":
            # 逐断面模式：返回结构化 dict 而非 CrossSection 对象，
            # 由 _run_steady 直接传给 SteadyProfileSolver 的逐断面参数。
            return {
                "type": "multi_station",
                "bed_elevations": xs_data.get("bed_elevations", []),
                "channel_widths": xs_data.get("channel_widths", []),
                "manning_ns": xs_data.get("manning_ns", []),
                "n_stations": xs_data.get("n_stations", 0),
            }

        else:
            logger.warning(
                "未知断面类型 '%s'，跳过断面几何注入（支持: irregular/trapezoidal/rectangular/multi_station）",
                xs_type,
            )
            return None

    def _inject_cross_section(self, solver: Any, cross_section: Any | None) -> None:
        """将 CrossSection 对象注入求解器（若求解器支持该属性）。

        Skips dict-type cross_section (multi_station) — handled by _run_steady.
        """
        if cross_section is None:
            return
        if isinstance(cross_section, dict):
            return
        if hasattr(solver, "cross_section"):
            solver.cross_section = cross_section
            logger.debug(
                "已将断面几何 %s 注入求解器 %s",
                cross_section.__class__.__name__,
                solver.__class__.__name__,
            )
        else:
            logger.debug(
                "求解器 %s 不支持 cross_section 属性，跳过断面几何注入",
                solver.__class__.__name__,
            )

    def _run_hydrostatic(self, params: dict, duration: float, dt: float) -> dict:
        from solvers.hydrostatic_canal_solver import HydrostaticCanalSolver

        length = float(params.get("length", 1000.0))
        nx = int(params.get("nx", 201))
        B = float(params.get("width", params.get("B", 10.0)))
        S0 = float(params.get("slope", params.get("S0", 0.001)))
        n = float(params.get("manning_n", params.get("n", 0.025)))

        solver = HydrostaticCanalSolver(length=length, nx=nx, B=B, S0=S0, n=n)
        self._inject_cross_section(solver, self._build_cross_section(params))

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
        self._inject_cross_section(solver, self._build_cross_section(params))

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

        xs_data = self._build_cross_section(params)

        if isinstance(xs_data, dict) and xs_data.get("type") == "multi_station":
            # 逐断面模式：为每个断面构造 RectangularSection（用实际宽度），
            # 并传入绝对床底高程和 Manning n，让 solver 走绝对水位路径。
            try:
                from physics.cross_section import RectangularSection
                widths = xs_data.get("channel_widths", [])
                cross_sections = [
                    RectangularSection(f"xs_{k}", float(w) if w else B)
                    for k, w in enumerate(widths)
                ]
            except (ImportError, Exception) as exc:
                logger.warning("构造逐断面 RectangularSection 失败 (%s)，降级为单断面模式", exc)
                cross_sections = None

            bed_elevs = xs_data.get("bed_elevations") or None
            manning_vals = xs_data.get("manning_ns") or None

            solver = SteadyProfileSolver(
                length=length, B=B, S0=S0, n=n,
                cross_sections=cross_sections,
                bed_elevations=bed_elevs,
                manning_ns=manning_vals,
            )
            # multi_station 模式固定使用 standard_step（绝对水位版）
            result = solver.solve_standard_step(Q, h_downstream)
        else:
            solver = SteadyProfileSolver(length=length, B=B, S0=S0, n=n)
            self._inject_cross_section(solver, xs_data)
            result = solver.solve_without_structures(Q, h_downstream, nx=nx, method=method)

        h_arr = np.asarray(result["h"])
        Q_arr = np.asarray(result["Q"])
        self._state = {
            "h": h_arr.tolist(),
            "Q": Q_arr.tolist(),
        }
        return _serialise_result(result)


    def _run_network(self, params: dict) -> dict:
        from solvers.network_steady_solver import (
            NetworkSteadySolver, ReachDefinition, JunctionDefinition,
        )

        reaches_data = params.get("reaches", [])
        junctions_data = params.get("junctions", [])

        if not reaches_data or not junctions_data:
            raise ValueError(
                "network solver requires params[reach_list] and params[junction_list]"
            )

        reaches = []
        for rd in reaches_data:
            reaches.append(ReachDefinition(
                reach_id=str(rd["reach_id"]),
                length=float(rd["length"]),
                slope=float(rd.get("slope", rd.get("S0", 0.001))),
                manning_n=float(rd.get("manning_n", rd.get("n", 0.025))),
                width=float(rd.get("width", rd.get("B", 10.0))),
                cross_section=None,
                nx=int(rd.get("nx", 101)),
            ))

        junctions = []
        for jd in junctions_data:
            junctions.append(JunctionDefinition(
                junction_id=str(jd["junction_id"]),
                upstream_reaches=list(jd.get("upstream_reaches", [])),
                downstream_reaches=list(jd.get("downstream_reaches", [])),
                boundary_type=jd.get("boundary_type"),
                boundary_value=float(jd["boundary_value"]) if jd.get("boundary_value") is not None else None,
                elevation=float(jd.get("elevation", 0.0)),
                junction_type=str(jd.get("junction_type", "confluence")),
            ))

        inflows = {str(k): float(v) for k, v in params.get("inflows", {}).items()}

        solver = NetworkSteadySolver(
            reaches=reaches,
            junctions=junctions,
            max_iter=int(params.get("max_iter", 50)),
            tol=float(params.get("tol", 1e-3)),
        )
        result = solver.solve(inflows)

        self._state = {
            "junction_wse": result["junction_wse"],
            "junction_Q": result["junction_Q"],
        }
        return result


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
