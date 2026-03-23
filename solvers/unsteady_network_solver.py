"""非恒定流河网求解器 — 多 Reach + Junction 松弛迭代。"""

import numpy as np
from dataclasses import dataclass, field
import sys
import os

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from solvers.unsteady_preissmann_solver import (
    PreissmannSolver, UnsteadyReachData, UnsteadyState
)


@dataclass
class ReachInfo:
    """单个河段信息。"""

    name: str
    reach_data: UnsteadyReachData
    us_type: str  # "external" | "junction"
    us_name: str  # BC 名或 Junction 名
    ds_type: str  # "external" | "junction"
    ds_name: str  # BC 名或 Junction 名


@dataclass
class JunctionInfo:
    """河网节点。"""

    name: str
    upstream_reaches: list = field(default_factory=list)
    downstream_reaches: list = field(default_factory=list)


class UnsteadyNetworkSolver:
    """多 Reach 河网非恒定流求解器。

    策略：Junction 松弛迭代 + 各 Reach 独立 Preissmann 求解。
    每个时间步内对 Junction 水位和流量反复迭代直到流量守恒。
    """

    def __init__(
        self,
        reaches: list,
        junctions: list,
        external_bcs: dict,
        theta: float = 0.6,
        g: float = 9.81,
        nr_max_iter: int = 30,
        nr_tol: float = 1e-4,
        junction_max_iter: int = 20,
        junction_tol: float = 0.01,
        junction_relax: float = 0.5,
        **solver_kwargs,
    ):
        """
        Args:
            reaches: 河段列表。
            junctions: 节点列表（连接关系自动推导）。
            external_bcs: 外部边界条件 dict。
                key 格式: {reach_name}_us 或 {reach_name}_ds。
                value: callable(t)->Q（上游）或 callable(t)->Z（下游）
                       或有 compute_normal_wse(Q) 方法的正常水深对象。
            junction_max_iter: Junction 松弛最大迭代次数。
            junction_tol: Junction 流量守恒容差 (m3/s)。
            junction_relax: 松弛因子 (0~1)。
        """
        self.reaches = {r.name: r for r in reaches}
        self.junctions = {j.name: j for j in junctions}
        self.external_bcs = external_bcs
        self.junction_max_iter = junction_max_iter
        self.junction_tol = junction_tol
        self.junction_relax = junction_relax

        # 自动推导 Junction 连接关系（覆盖已有列表）
        for jname in self.junctions:
            self.junctions[jname].upstream_reaches = []
            self.junctions[jname].downstream_reaches = []
        for rname, rinfo in self.reaches.items():
            if rinfo.ds_type == "junction" and rinfo.ds_name in self.junctions:
                self.junctions[rinfo.ds_name].upstream_reaches.append(rname)
            if rinfo.us_type == "junction" and rinfo.us_name in self.junctions:
                self.junctions[rinfo.us_name].downstream_reaches.append(rname)

        # 为每个 Reach 创建独立 PreissmannSolver
        self.solvers: dict = {}
        for rname, rinfo in self.reaches.items():
            self.solvers[rname] = PreissmannSolver(
                reach=rinfo.reach_data,
                theta=theta,
                g=g,
                nr_max_iter=nr_max_iter,
                nr_tol=nr_tol,
                **solver_kwargs,
            )

        self._topo_order = self._topological_sort()
        self.nr_max_iter = nr_max_iter
        self.nr_tol = nr_tol
        self.max_dZ = solver_kwargs.get("max_dZ_per_iter", 0.5)

    # ------------------------------------------------------------------
    # 拓扑排序
    # ------------------------------------------------------------------

    def _topological_sort(self) -> list:
        """Kahn 算法：上游 reach 先于下游 reach 计算。"""
        reach_names = list(self.reaches.keys())

        in_degree: dict = {n: 0 for n in reach_names}
        for rname, rinfo in self.reaches.items():
            if rinfo.us_type == "junction":
                junc = self.junctions[rinfo.us_name]
                if len(junc.upstream_reaches) > 0:
                    in_degree[rname] += 1

        adj: dict = {n: [] for n in reach_names}
        for rname, rinfo in self.reaches.items():
            if rinfo.ds_type == "junction":
                junc = self.junctions[rinfo.ds_name]
                for ds_rname in junc.downstream_reaches:
                    adj[rname].append(ds_rname)

        queue = [n for n in reach_names if in_degree[n] == 0]
        order: list = []
        while queue:
            node = queue.pop(0)
            order.append(node)
            for nb in adj[node]:
                in_degree[nb] -= 1
                if in_degree[nb] == 0:
                    queue.append(nb)

        processed = set(order)
        for n in reach_names:
            if n not in processed:
                order.append(n)
        return order

    # ------------------------------------------------------------------
    # 初始化
    # ------------------------------------------------------------------

    def initialize(self, Z_dict: dict, Q_dict: dict, t: float = 0.0) -> dict:
        """从给定数组初始化各 Reach 的状态。

        Args:
            Z_dict: {reach_name: Z_array}，缺省用河床 + 0.1m。
            Q_dict: {reach_name: Q_array}，缺省为零流量。
            t: 初始时间 (s)。

        Returns:
            {reach_name: UnsteadyState}
        """
        states: dict = {}
        for rname, rinfo in self.reaches.items():
            n = rinfo.reach_data.n_xs
            Z = np.array(
                Z_dict.get(rname, rinfo.reach_data.bed_elevation + 0.1), dtype=float
            )
            Q = np.array(Q_dict.get(rname, np.zeros(n)), dtype=float)
            states[rname] = UnsteadyState(Z=Z, Q=Q, t=t)
        return states

    # ------------------------------------------------------------------
    # Junction 辅助
    # ------------------------------------------------------------------

    def _get_junction_wse(self, states: dict, jname: str) -> float:
        """获取 Junction 当前水位（所有连接 reach 端部水位的均值）。"""
        junc = self.junctions[jname]
        wse_vals: list = []
        for rname in junc.upstream_reaches:
            if rname in states:
                wse_vals.append(float(states[rname].Z[-1]))
        for rname in junc.downstream_reaches:
            if rname in states:
                wse_vals.append(float(states[rname].Z[0]))
        return float(np.mean(wse_vals)) if wse_vals else 0.0

    def _get_junction_flow_balance(self, states: dict, jname: str) -> float:
        """计算 Junction 流量不平衡（Q_in - Q_out）。"""
        junc = self.junctions[jname]
        q_in = sum(float(states[r].Q[-1]) for r in junc.upstream_reaches if r in states)
        q_out = sum(float(states[r].Q[0]) for r in junc.downstream_reaches if r in states)
        return q_in - q_out

    def _get_junction_width(self, states: dict, jname: str) -> float:
        """获取 Junction 处代表性水面宽（用于 dZ 更新量估算）。"""
        junc = self.junctions[jname]
        widths: list = []
        for rname in junc.upstream_reaches:
            if rname in states:
                rinfo = self.reaches[rname]
                z = float(states[rname].Z[-1])
                bed = float(rinfo.reach_data.bed_elevation[-1])
                depth = max(z - bed, 0.05)
                geom = rinfo.reach_data.sections[-1].compute_geometry(depth)
                widths.append(max(geom.width, 0.1))
        for rname in junc.downstream_reaches:
            if rname in states:
                rinfo = self.reaches[rname]
                z = float(states[rname].Z[0])
                bed = float(rinfo.reach_data.bed_elevation[0])
                depth = max(z - bed, 0.05)
                geom = rinfo.reach_data.sections[0].compute_geometry(depth)
                widths.append(max(geom.width, 0.1))
        return float(np.mean(widths)) if widths else 1.0

    # ------------------------------------------------------------------
    # 单时间步
    # ------------------------------------------------------------------

    def step(self, states: dict, dt: float, t_new: float) -> dict:
        """推进一个时间步 — 全局 NR 求解（所有 reach + junction 同时求解）。

        将各 reach 的 Preissmann 方程拼成一个大稀疏矩阵，
        junction 方程（水位连续 + 流量守恒）替换 reach 端部 BC 行。
        """
        import scipy.sparse as sp
        from scipy.sparse.linalg import spsolve

        t_old = t_new - dt
        reach_order = self._topo_order

        # 1. 全局变量布局: [reach1_Z0,Q0,...,Zn,Qn | reach2_... | ...]
        offsets = {}  # reach_name -> global offset
        offset = 0
        for rname in reach_order:
            offsets[rname] = offset
            offset += 2 * self.reaches[rname].reach_data.n_xs
        global_size = offset

        # 初始化全局 X (from current iterate = old state)
        X = np.zeros(global_size)
        for rname in reach_order:
            n_r = self.reaches[rname].reach_data.n_xs
            o = offsets[rname]
            X[o:o + 2 * n_r:2] = states[rname].Z
            X[o + 1:o + 2 * n_r:2] = states[rname].Q

        # Old state arrays
        Z_n_dict = {rname: states[rname].Z.copy() for rname in reach_order}
        Q_n_dict = {rname: states[rname].Q.copy() for rname in reach_order}

        # Junction -> list of (reach_name, endpoint_type, global_col_Z, global_col_Q)
        junc_connections = {}
        for jname, junc in self.junctions.items():
            conns = []
            for rname in junc.upstream_reaches:
                n_r = self.reaches[rname].reach_data.n_xs
                o = offsets[rname]
                conns.append((rname, "ds", o + 2 * (n_r - 1), o + 2 * (n_r - 1) + 1))
            for rname in junc.downstream_reaches:
                o = offsets[rname]
                conns.append((rname, "us", o, o + 1))
            junc_connections[jname] = conns

        # Identify which reach endpoint is the "master" for each junction
        # Master: uses flow conservation BC. Others: use Z equality to master.
        junc_master = {}  # jname -> (rname, endpoint, col_Z)
        for jname, junc in self.junctions.items():
            conns = junc_connections[jname]
            if conns:
                junc_master[jname] = conns[0]  # first upstream reach is master

        # 2. NR iteration
        for nr_iter in range(self.nr_max_iter):
            F_global = np.zeros(global_size)
            J_global = sp.lil_matrix((global_size, global_size))

            # Get current junction Z from master endpoint (not average)
            junc_Z = {}
            for jname in self.junctions:
                master = junc_master[jname]
                junc_Z[jname] = float(X[master[2]])

            # 2a. Each reach: build Preissmann equations with proper BC
            for rname in reach_order:
                rinfo = self.reaches[rname]
                solver = self.solvers[rname]
                n_r = rinfo.reach_data.n_xs
                o = offsets[rname]

                Z_cur = X[o:o + 2 * n_r:2].copy()
                Q_cur = X[o + 1:o + 2 * n_r:2].copy()
                Z_old = Z_n_dict[rname]
                Q_old = Q_n_dict[rname]

                A, B, K = solver._compute_hydraulics_all(Z_cur, Q_cur)
                A_n, B_n, K_n = solver._compute_hydraulics_all(Z_old, Q_old)

                # Upstream BC
                Z_up_val = None
                Q_up_val = 0.0
                if rinfo.us_type == "external":
                    bc = self.external_bcs.get(rname + "_us")
                    if bc is not None and callable(bc):
                        Q_up_val = float(bc(t_new))
                else:
                    # Junction upstream: Z[0] = Z_junction (will be linked below)
                    Z_up_val = junc_Z[rinfo.us_name]

                # Downstream BC
                ds_bc = None
                ds_junc_Z = None
                if rinfo.ds_type == "external":
                    ds_bc = self.external_bcs.get(rname + "_ds")
                    if ds_bc is None:
                        ds_bc = lambda t: 0.0
                else:
                    # Junction downstream: pass ds_junction_Z to _build_system
                    ds_junc_Z = junc_Z[rinfo.ds_name]
                    ds_bc = lambda t: 0.0  # placeholder

                F_local, J_local = solver._build_system(
                    Z_cur, Q_cur, Z_old, Q_old,
                    A, B, K, A_n, B_n, K_n,
                    dt, Q_up_val, t_new, ds_bc,
                    Z_up=Z_up_val,
                    ds_junction_Z=ds_junc_Z,
                )

                # Copy local block into global
                J_local_lil = J_local if isinstance(J_local, sp.lil_matrix) else J_local.tolil()
                neq_local = 2 * n_r
                F_global[o:o + neq_local] = F_local
                rows_l, cols_l = J_local_lil.nonzero()
                for idx in range(len(rows_l)):
                    r, c = rows_l[idx], cols_l[idx]
                    J_global[o + r, o + c] = J_local_lil[r, c]

            # 2b. Junction coupling: replace BC rows with cross-reach equations
            for jname, junc in self.junctions.items():
                conns = junc_connections[jname]
                if len(conns) < 2:
                    continue

                master = junc_master[jname]
                master_rname, master_ep, master_col_Z, master_col_Q = master
                master_o = offsets[master_rname]
                n_master = self.reaches[master_rname].reach_data.n_xs

                # Master's BC row → flow conservation: ΣQ_in - ΣQ_out = 0
                fc_row = master_o + 2 * n_master - 1  # last row (was DS Z BC)
                J_global[fc_row, :] = 0
                F_val = 0.0
                for rname_c, ep_c, col_Z_c, col_Q_c in conns:
                    if ep_c == "ds":
                        F_val += X[col_Q_c]
                        J_global[fc_row, col_Q_c] = 1.0
                    else:
                        F_val -= X[col_Q_c]
                        J_global[fc_row, col_Q_c] = -1.0
                F_global[fc_row] = F_val

                # Other connections: Z equality to master (already set by ds_junction_Z/Z_up)
                # But those use junc_Z (average), not master_col_Z. Fix: replace with exact coupling.
                for rname_c, ep_c, col_Z_c, col_Q_c in conns:
                    if (rname_c, ep_c) == (master_rname, master_ep):
                        continue
                    o_c = offsets[rname_c]
                    n_c = self.reaches[rname_c].reach_data.n_xs
                    if ep_c == "us":
                        bc_row = o_c  # row 0
                    else:
                        bc_row = o_c + 2 * n_c - 1  # last row
                    # Z_slave - Z_master = 0
                    J_global[bc_row, :] = 0
                    F_global[bc_row] = X[col_Z_c] - X[master_col_Z]
                    J_global[bc_row, col_Z_c] = 1.0
                    J_global[bc_row, master_col_Z] = -1.0

            # 2c. Solve global system
            max_res = float(np.max(np.abs(F_global)))
            if max_res < self.nr_tol:
                break

            try:
                dX = spsolve(J_global.tocsr(), -F_global)
            except Exception:
                break

            if not np.all(np.isfinite(dX)):
                break

            # Limit dZ
            dX_clipped = dX.copy()
            for rname in reach_order:
                o = offsets[rname]
                n_r = self.reaches[rname].reach_data.n_xs
                for i in range(n_r):
                    dz = dX_clipped[o + 2 * i]
                    if abs(dz) > self.max_dZ:
                        dX_clipped[o + 2 * i] = np.sign(dz) * self.max_dZ

            X += dX_clipped

            # Enforce min depth
            for rname in reach_order:
                o = offsets[rname]
                rinfo = self.reaches[rname]
                n_r = rinfo.reach_data.n_xs
                for i in range(n_r):
                    z_min = rinfo.reach_data.bed_elevation[i] + 0.05
                    if X[o + 2 * i] < z_min:
                        X[o + 2 * i] = z_min

        # 3. Extract results
        new_states = {}
        for rname in reach_order:
            o = offsets[rname]
            n_r = self.reaches[rname].reach_data.n_xs
            Z_new = X[o:o + 2 * n_r:2].copy()
            Q_new = X[o + 1:o + 2 * n_r:2].copy()
            new_states[rname] = UnsteadyState(Z=Z_new, Q=Q_new, t=t_new)

        return new_states

    # ------------------------------------------------------------------
    # 完整模拟
    # ------------------------------------------------------------------

    def solve(
        self,
        states0: dict,
        t_end: float,
        dt: float,
        output_interval=None,
        verbose: bool = False,
    ) -> dict:
        """运行完整河网非恒定流模拟。

        Args:
            states0: {reach_name: UnsteadyState} 初始状态。
            t_end: 模拟结束时间 (s)。
            dt: 时间步长 (s)。
            output_interval: 结果保存间隔 (s)，默认等于 dt。
            verbose: 是否打印进度信息。

        Returns:
            {reach_name: {times: ndarray, Z_history: ndarray, Q_history: ndarray}}
            与 PreissmannSolver.solve() 的单 reach 结果格式一致。
        """
        states = {rname: UnsteadyState(Z=s.Z.copy(), Q=s.Q.copy(), t=s.t)
                      for rname, s in states0.items()}

        t = float(next(iter(states.values())).t)
        out_interval = dt if output_interval is None else float(output_interval)
        next_out_t = t + out_interval

        times_out: list = [t]
        Z_hist: dict = {rname: [states[rname].Z.copy()] for rname in self.reaches}
        Q_hist: dict = {rname: [states[rname].Q.copy()] for rname in self.reaches}

        while t < t_end - 1e-10:
            dt_actual = min(dt, t_end - t)
            t_new = t + dt_actual

            new_states = self.step(states, dt_actual, t_new)
            states = new_states
            t = t_new

            if t >= next_out_t - 1e-10:
                times_out.append(t)
                for rname in self.reaches:
                    Z_hist[rname].append(states[rname].Z.copy())
                    Q_hist[rname].append(states[rname].Q.copy())
                next_out_t += out_interval

                if verbose:
                    junc_parts = []
                    for jname in self.junctions:
                        imb = self._get_junction_flow_balance(states, jname)
                        zwse = self._get_junction_wse(states, jname)
                        junc_parts.append(f"{jname}:Z={zwse:.2f},dQ={imb:.3f}")
                    print(f"  t={t:.0f}s  " + " | ".join(junc_parts))

        return {
            rname: {
                "times": np.array(times_out),
                "Z_history": np.array(Z_hist[rname]),
                "Q_history": np.array(Q_hist[rname]),
            }
            for rname in self.reaches
        }
