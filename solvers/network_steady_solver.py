from __future__ import annotations
"""Multi-reach steady water surface profile solver (NetworkSteadySolver).

Supports serial (A->B->C) and Y-confluence topologies.
"""

import logging
from dataclasses import dataclass, field
from typing import Any
import numpy as np

try:
    from solvers.steady_profile_solver import SteadyProfileSolver
except ImportError:
    SteadyProfileSolver = None

try:
    from utils.canal_utils import compute_steady_uniform_flow
except ImportError:
    compute_steady_uniform_flow = None

logger = logging.getLogger(__name__)

_G = 9.81


@dataclass
class ReachDefinition:
    reach_id: str
    length: float
    slope: float
    manning_n: float
    width: float
    cross_section: Any | None = None
    nx: int = 101


@dataclass
class JunctionDefinition:
    junction_id: str
    upstream_reaches: list[str] = field(default_factory=list)
    downstream_reaches: list[str] = field(default_factory=list)
    boundary_type: str | None = None
    boundary_value: float | None = None
    elevation: float = 0.0
    junction_type: str = "confluence"


class NetworkSteadySolver:
    """Multi-reach steady WSE iterative solver."""

    def __init__(
        self,
        reaches: list[ReachDefinition],
        junctions: list[JunctionDefinition],
        max_iter: int = 50,
        tol: float = 1e-3,
    ) -> None:
        self.reaches: dict[str, ReachDefinition] = {r.reach_id: r for r in reaches}
        self.junctions: dict[str, JunctionDefinition] = {j.junction_id: j for j in junctions}
        self.max_iter = max_iter
        self.tol = tol
        self._reach_up_junc: dict[str, str] = {}
        self._reach_dn_junc: dict[str, str] = {}
        self._build_reach_junc_map()
        self._topo_order: list[str] = self._build_topo_order()
        self._junction_wse: dict[str, float] = {}
        self._junction_Q: dict[str, float] = {}
        self._reach_results: dict[str, dict] = {}

    def _build_reach_junc_map(self) -> None:
        for junc in self.junctions.values():
            for rid in junc.upstream_reaches:
                self._reach_dn_junc[rid] = junc.junction_id
            for rid in junc.downstream_reaches:
                self._reach_up_junc[rid] = junc.junction_id

    def _build_topo_order(self) -> list[str]:
        # A junction has an upstream source if at least one reach flows INTO it
        # That reach's downstream junction is self._reach_dn_junc[rid]
        has_upstream: set[str] = set(self._reach_dn_junc.values())
        sources = [jid for jid in self.junctions if jid not in has_upstream]
        visited: set[str] = set()
        order: list[str] = []
        in_stack: set[str] = set()

        def dfs(jid: str) -> None:
            if jid in in_stack or jid in visited:
                return
            in_stack.add(jid)
            junc = self.junctions.get(jid)
            if junc is not None:
                for rid in junc.downstream_reaches:
                    dn_jid = self._reach_dn_junc.get(rid)
                    if dn_jid is not None:
                        dfs(dn_jid)
            in_stack.discard(jid)
            visited.add(jid)
            order.append(jid)

        for src in sources:
            dfs(src)
        return list(reversed(order))

    def _make_solver(self, rd: ReachDefinition):
        if SteadyProfileSolver is None:
            raise ImportError("SteadyProfileSolver unavailable")
        solver = SteadyProfileSolver(length=rd.length, B=rd.width, S0=rd.slope, n=rd.manning_n)
        if rd.cross_section is not None and hasattr(solver, "cross_section"):
            solver.cross_section = rd.cross_section
        return solver

    def _normal_depth(self, rd: ReachDefinition, Q: float) -> float:
        if compute_steady_uniform_flow is not None:
            try:
                return float(compute_steady_uniform_flow(Q=Q, B=rd.width, S0=rd.slope, n=rd.manning_n))
            except Exception:
                pass
        B, S0, n = rd.width, max(rd.slope, 1e-8), rd.manning_n
        h = 1.0
        for _ in range(100):
            A = B * h
            P = B + 2.0 * h
            R = A / P
            Q_calc = A / n * R ** (2.0 / 3.0) * S0 ** 0.5
            if abs(Q_calc - Q) < 1e-6:
                break
            h = h * (Q / max(Q_calc, 1e-12)) ** 0.4
        return max(h, 1e-4)

    def _conveyance(self, rd: ReachDefinition, h: float) -> float:
        B, n = rd.width, rd.manning_n
        A = B * h
        P = B + 2.0 * h
        R = A / P if P > 0 else 0.0
        return A * R ** (2.0 / 3.0) / n if A > 0 else 0.0

    @staticmethod
    def _wse_to_h(wse: float, z_bottom: float) -> float:
        return max(wse - z_bottom, 1e-4)

    @staticmethod
    def _h_to_wse(h: float, z_bottom: float) -> float:
        return h + z_bottom

    def solve(self, inflows: dict[str, float]) -> dict:
        """Solve network steady-state profiles.

        Args:
            inflows: {junction_id: Q_m3s} for source junctions.
        Returns:
            Dict: reaches, junction_wse, junction_Q, converged, iterations, max_dWSE.
        """
        self._init_Q(inflows)
        self._init_wse()
        converged = False
        max_dWSE = 0.0
        iteration = 0
        for it in range(self.max_iter):
            iteration = it + 1
            old_wse = dict(self._junction_wse)
            for jid in self._topo_order:
                self._solve_downstream_reaches(jid)
            max_dWSE = (
                max(abs(self._junction_wse[jid] - old_wse.get(jid, 0.0)) for jid in self._junction_wse)
                if self._junction_wse else 0.0
            )
            logger.debug("NetworkSteadySolver iter %d max_dWSE=%.6f m", iteration, max_dWSE)
            if max_dWSE < self.tol:
                converged = True
                break
        return {
            "reaches": self._reach_results,
            "junction_wse": dict(self._junction_wse),
            "junction_Q": dict(self._junction_Q),
            "converged": converged,
            "iterations": iteration,
            "max_dWSE": float(max_dWSE),
        }

    def _init_Q(self, inflows: dict[str, float]) -> None:
        for jid in self.junctions:
            self._junction_Q[jid] = 0.0
        for jid, Q in inflows.items():
            if jid in self._junction_Q:
                self._junction_Q[jid] = float(Q)
        for jid in self._topo_order:
            junc = self.junctions[jid]
            Q_junc = self._junction_Q[jid]
            if not junc.downstream_reaches:
                continue
            if len(junc.downstream_reaches) == 1:
                rid = junc.downstream_reaches[0]
                dn_jid = self._reach_dn_junc.get(rid)
                if dn_jid is not None:
                    self._junction_Q[dn_jid] = self._junction_Q.get(dn_jid, 0.0) + Q_junc
            else:
                n_dn = len(junc.downstream_reaches)
                for rid in junc.downstream_reaches:
                    dn_jid = self._reach_dn_junc.get(rid)
                    if dn_jid is not None:
                        self._junction_Q[dn_jid] = self._junction_Q.get(dn_jid, 0.0) + Q_junc / n_dn

    def _init_wse(self) -> None:
        for jid, junc in self.junctions.items():
            z = junc.elevation
            all_rid = list(junc.upstream_reaches) + list(junc.downstream_reaches)
            h_est = 1.0
            for rid in all_rid:
                rd = self.reaches.get(rid)
                if rd is None:
                    continue
                Q = self._junction_Q.get(jid, 1.0)
                try:
                    h_est = self._normal_depth(rd, max(Q, 0.1))
                    break
                except Exception:
                    pass
            self._junction_wse[jid] = z + h_est
            if junc.boundary_type == "wse" and junc.boundary_value is not None:
                self._junction_wse[jid] = float(junc.boundary_value)

    def _solve_downstream_reaches(self, jid: str) -> None:
        junc = self.junctions[jid]
        Q_total = self._junction_Q.get(jid, 0.0)
        if not junc.downstream_reaches:
            return
        reach_flows = self._split_flow(jid, Q_total)
        wse_results: dict[str, float] = {}
        for rid, Q_reach in reach_flows.items():
            rd = self.reaches.get(rid)
            if rd is None:
                continue
            dn_jid = self._reach_dn_junc.get(rid)
            dn_junc = self.junctions.get(dn_jid) if dn_jid else None
            if (dn_junc is not None and dn_junc.boundary_type == "wse"
                    and dn_junc.boundary_value is not None):
                wse_dn = float(dn_junc.boundary_value)
            elif dn_jid is not None and dn_jid in self._junction_wse:
                wse_dn = self._junction_wse[dn_jid]
            else:
                wse_dn = junc.elevation + self._normal_depth(rd, max(Q_reach, 0.1))
            z_dn = dn_junc.elevation if dn_junc is not None else 0.0
            h_dn = self._wse_to_h(wse_dn, z_dn)
            try:
                solver = self._make_solver(rd)
                result = solver.solve_standard_step(
                    Q=float(Q_reach), h_downstream=float(h_dn), nx=rd.nx,
                )
                h_arr = result["h"]
                x_arr = result["x"]
                self._reach_results[rid] = {
                    "x": x_arr.tolist() if hasattr(x_arr, "tolist") else list(x_arr),
                    "h": h_arr.tolist() if hasattr(h_arr, "tolist") else list(h_arr),
                    "Q": float(Q_reach),
                    "method": result.get("method", "standard_step"),
                }
                z_up = z_dn + rd.slope * rd.length
                wse_results[rid] = float(h_arr[0]) + z_up
            except Exception as exc:
                logger.warning("Reach %s solve failed: %s", rid, exc)
        if wse_results:
            Q_vals = [reach_flows.get(rid, 1.0) for rid in wse_results]
            wse_vals = list(wse_results.values())
            Q_sum = sum(Q_vals)
            if Q_sum > 1e-12:
                self._junction_wse[jid] = sum(w * q for w, q in zip(wse_vals, Q_vals)) / Q_sum
            else:
                self._junction_wse[jid] = float(sum(wse_vals) / len(wse_vals))
        self._update_downstream_wse_from_reaches(jid, reach_flows)

    def _split_flow(self, jid: str, Q_total: float) -> dict[str, float]:
        junc = self.junctions[jid]
        dn_reaches = junc.downstream_reaches
        if not dn_reaches:
            return {}
        if len(dn_reaches) == 1:
            return {dn_reaches[0]: Q_total}
        wse_junc = self._junction_wse.get(jid, junc.elevation + 1.0)
        K_vals: dict[str, float] = {}
        for rid in dn_reaches:
            rd = self.reaches.get(rid)
            if rd is None:
                K_vals[rid] = 1.0
                continue
            h_est = max(wse_junc - junc.elevation, 0.1)
            K_vals[rid] = self._conveyance(rd, h_est)
        K_total = sum(K_vals.values())
        if K_total < 1e-12:
            return {rid: Q_total / len(dn_reaches) for rid in dn_reaches}
        return {rid: Q_total * K / K_total for rid, K in K_vals.items()}

    def _update_downstream_wse_from_reaches(
        self, upstream_jid: str, reach_flows: dict[str, float]
    ) -> None:
        junc = self.junctions[upstream_jid]
        dn_contributions: dict[str, list] = {}
        for rid in junc.downstream_reaches:
            dn_jid = self._reach_dn_junc.get(rid)
            if dn_jid is None:
                continue
            dn_junc = self.junctions.get(dn_jid)
            if dn_junc is not None and dn_junc.boundary_type == "wse":
                continue
            rr = self._reach_results.get(rid)
            if rr is None:
                continue
            h_exit = rr["h"][-1] if rr["h"] else 0.0
            z_dn = self.junctions[dn_jid].elevation if dn_jid in self.junctions else 0.0
            wse_exit = h_exit + z_dn
            Q_reach = reach_flows.get(rid, 1.0)
            if dn_jid not in dn_contributions:
                dn_contributions[dn_jid] = []
            dn_contributions[dn_jid].append((wse_exit, Q_reach))
        for dn_jid, _c in dn_contributions.items():
            dn_junc = self.junctions.get(dn_jid)
            if dn_junc is None:
                continue
            all_up = dn_junc.upstream_reaches
            solved = [r for r in all_up if r in self._reach_results]
            if len(solved) < len(all_up):
                continue
            all_c: list = []
            for up_rid in all_up:
                rr2 = self._reach_results.get(up_rid)
                if rr2 is None:
                    continue
                h_exit2 = rr2["h"][-1] if rr2["h"] else 0.0
                z_dn2 = self.junctions[dn_jid].elevation
                wse2 = h_exit2 + z_dn2
                all_c.append((wse2, rr2.get("Q", 1.0)))
            if not all_c:
                continue
            Q_sum = sum(q for _, q in all_c)
            if Q_sum > 1e-12:
                self._junction_wse[dn_jid] = sum(w * q for w, q in all_c) / Q_sum
            else:
                self._junction_wse[dn_jid] = float(sum(w for w, _ in all_c) / len(all_c))


def build_serial_network(
    reach_params: list[dict],
    downstream_wse: float,
    downstream_elevation: float = 0.0,
) -> tuple:
    """Build a serial (chain) river network A->B->C->....

    Args:
        reach_params: Dicts upstream to downstream, keys:
            reach_id, length, slope, manning_n (or n), width (or B),
            cross_section (opt), nx (opt).
        downstream_wse: Outlet WSE (m).
        downstream_elevation: Outlet bed elevation (m).
    Returns:
        (solver, source_junction_id, outlet_junction_id)
    """
    if not reach_params:
        raise ValueError("reach_params must not be empty")
    reaches: list[ReachDefinition] = []
    junctions: list[JunctionDefinition] = []
    n = len(reach_params)
    junc_ids = ["J" + str(i) for i in range(n + 1)]
    elevations: list[float] = [downstream_elevation]
    for i in range(n - 1, -1, -1):
        rp = reach_params[i]
        dz = float(rp.get("slope", 0.001)) * float(rp.get("length", 1000.0))
        elevations.insert(0, elevations[0] + dz)
    for i, rp in enumerate(reach_params):
        rid = rp.get("reach_id", "R" + str(i))
        reaches.append(ReachDefinition(
            reach_id=rid,
            length=float(rp["length"]),
            slope=float(rp["slope"]),
            manning_n=float(rp.get("manning_n", rp.get("n", 0.025))),
            width=float(rp.get("width", rp.get("B", 10.0))),
            cross_section=rp.get("cross_section"),
            nx=int(rp.get("nx", 101)),
        ))
        up_jid = junc_ids[i]
        dn_jid = junc_ids[i + 1]
        if not any(j.junction_id == up_jid for j in junctions):
            junctions.append(JunctionDefinition(
                junction_id=up_jid,
                upstream_reaches=[],
                downstream_reaches=[rid],
                junction_type="source" if i == 0 else "confluence",
                elevation=elevations[i],
            ))
        else:
            for j in junctions:
                if j.junction_id == up_jid and rid not in j.downstream_reaches:
                    j.downstream_reaches.append(rid)
        is_outlet = (i == n - 1)
        if not any(j.junction_id == dn_jid for j in junctions):
            junctions.append(JunctionDefinition(
                junction_id=dn_jid,
                upstream_reaches=[rid],
                downstream_reaches=[],
                junction_type="outlet" if is_outlet else "confluence",
                boundary_type="wse" if is_outlet else None,
                boundary_value=downstream_wse if is_outlet else None,
                elevation=elevations[i + 1],
            ))
        else:
            for j in junctions:
                if j.junction_id == dn_jid:
                    if rid not in j.upstream_reaches:
                        j.upstream_reaches.append(rid)
                    if i + 1 < n:
                        next_rid = reach_params[i + 1].get("reach_id", "R" + str(i + 1))
                        if next_rid not in j.downstream_reaches:
                            j.downstream_reaches.append(next_rid)
    solver = NetworkSteadySolver(reaches=reaches, junctions=junctions)
    return solver, junc_ids[0], junc_ids[-1]

