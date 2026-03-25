"""非恒定流河网求解器 — 多 Reach + Junction 松弛迭代。"""

import numpy as np
from dataclasses import dataclass, field
import sys
import os
import warnings

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
    us_junction_distance_m: float | None = None
    ds_junction_distance_m: float | None = None


@dataclass
class JunctionInfo:
    """河网节点。"""

    name: str
    upstream_reaches: list = field(default_factory=list)
    downstream_reaches: list = field(default_factory=list)
    # Junction storage: elevation (m) vs cumulative volume (m³) from HEC-RAS
    storage_elevations: np.ndarray = None
    storage_volumes: np.ndarray = None
    hecras_index: int | None = None
    hecras_momentum: bool = False
    hecras_add_weight: bool = False
    hecras_add_friction: bool = False
    hecras_unsteady_energy: bool = False
    hecras_master_reach: str | None = None
    hecras_master_endpoint: str | None = None
    preprocess_endpoint_signs: dict = field(default_factory=dict)


@dataclass
class StorageAreaInfo:
    """独立库区节点。"""

    name: str
    storage_elevations: np.ndarray = None
    storage_volumes: np.ndarray = None
    area: float | None = None
    min_elevation: float | None = None
    initial_stage: float | None = None


@dataclass
class StorageConnectionInfo:
    """库区之间的水力连接。"""

    name: str
    up_storage_area: str
    down_storage_area: str
    weir_width: float | None = None
    weir_coef: float | None = None
    crest_elevation: float | None = None
    culvert_count: int = 0
    culvert_diameter: float | None = None
    culvert_length: float | None = None
    culvert_manning_n: float | None = None
    culvert_inlet_coef: float | None = None
    culvert_loss_coef: float | None = None
    culvert_selector_1: int | None = None
    culvert_selector_2: int | None = None
    culvert_selector_3: int | None = None
    culvert_us_invert: float | None = None
    culvert_ds_invert: float | None = None


@dataclass
class LateralStructureInfo:
    """河道到库区的侧向结构。"""

    name: str
    reach_name: str
    cell_index: int
    storage_area: str
    position_fraction: float = 0.5
    length_m: float | None = None
    weir_width: float | None = None
    weir_coef: float | None = None
    crest_elevation: float | None = None
    culvert_count: int = 0
    culvert_diameter: float | None = None
    culvert_length: float | None = None
    culvert_manning_n: float | None = None
    culvert_inlet_coef: float | None = None
    culvert_loss_coef: float | None = None
    culvert_selector_1: int | None = None
    culvert_selector_2: int | None = None
    culvert_selector_3: int | None = None
    culvert_us_invert: float | None = None
    culvert_ds_invert: float | None = None


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
        storage_areas: list | None = None,
        storage_connections: list | None = None,
        lateral_structures: list | None = None,
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
        self.storage_areas = {s.name: s for s in (storage_areas or [])}
        self.storage_connections = list(storage_connections or [])
        self.lateral_structures = list(lateral_structures or [])
        self.external_bcs = external_bcs
        self.junction_max_iter = junction_max_iter
        self.junction_tol = junction_tol
        self.junction_relax = junction_relax
        junction_debug_config = solver_kwargs.pop("junction_debug_config", None)
        junction_state_names = solver_kwargs.pop("junction_state_names", None)
        network_only_keys = {
            "max_storage_dZ_per_iter",
            "max_storage_dZ_per_step",
            "max_junction_dZ_per_iter",
            "max_junction_dZ_per_step",
            "storage_picard_max_iter",
            "storage_picard_tol",
            "storage_picard_relax",
        }
        reach_solver_kwargs = dict(solver_kwargs)
        for key in network_only_keys:
            reach_solver_kwargs.pop(key, None)

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
                **reach_solver_kwargs,
            )

        self._topo_order = self._topological_sort()
        self.nr_max_iter = nr_max_iter
        self.nr_tol = nr_tol
        self.g = g
        self.max_dZ = solver_kwargs.get("max_dZ_per_iter", 0.5)
        self.max_dQ = solver_kwargs.get("max_dQ_per_iter", 25.0)
        self.max_storage_dZ = solver_kwargs.get("max_storage_dZ_per_iter", 0.25)
        self.max_storage_step_dZ = solver_kwargs.get("max_storage_dZ_per_step", 0.75)
        self.max_junction_dZ = solver_kwargs.get("max_junction_dZ_per_iter", 0.25)
        self.max_junction_step_dZ = solver_kwargs.get("max_junction_dZ_per_step", 0.75)
        self.storage_picard_max_iter = int(solver_kwargs.get("storage_picard_max_iter", 8))
        self.storage_picard_tol = float(solver_kwargs.get("storage_picard_tol", 0.01))
        self.storage_picard_relax = float(solver_kwargs.get("storage_picard_relax", 0.5))
        self._last_step_converged = True
        self._last_step_residual = 0.0
        self.junction_debug_config = dict(junction_debug_config or {})
        self.junction_debug_names = set(self.junction_debug_config.get("junction_names", []) or [])
        self.junction_debug_t_start = self.junction_debug_config.get("t_start")
        self.junction_debug_t_end = self.junction_debug_config.get("t_end")
        self.junction_state_names = {
            jname for jname in (junction_state_names or [])
            if jname in self.junctions and (
                len(self.junctions[jname].upstream_reaches) + len(self.junctions[jname].downstream_reaches) >= 2
            )
        }
        self._last_step_junction_debug: list = []
        self._last_step_junction_states: dict = {}
        self._last_step_junction_iter_clip_counts: dict = {}
        self._last_step_junction_step_clip_counts: dict = {}

    def _junction_debug_enabled(self, t_new: float | None = None) -> bool:
        if not self.junction_debug_names:
            return False
        if t_new is None:
            return True
        if self.junction_debug_t_start is not None and t_new < float(self.junction_debug_t_start) - 1e-9:
            return False
        if self.junction_debug_t_end is not None and t_new > float(self.junction_debug_t_end) + 1e-9:
            return False
        return True

    def _capture_local_bc_debug(
        self,
        local_bc_debug: dict,
        jname: str,
        rname: str,
        endpoint: str,
        F_local,
        J_local_lil,
        n_r: int,
        target_stage: float,
    ) -> None:
        if endpoint == "us":
            row = 0
            col_z = 0
            col_q = 1
        else:
            row = 2 * n_r - 1
            col_z = 2 * (n_r - 1)
            col_q = 2 * (n_r - 1) + 1
        local_bc_debug.setdefault(jname, {})[(rname, endpoint)] = {
            "reach_name": rname,
            "endpoint": endpoint,
            "row_local": int(row),
            "residual_local": float(F_local[row]),
            "dF_dZ_local": float(J_local_lil[row, col_z]),
            "dF_dQ_local": float(J_local_lil[row, col_q]),
            "target_stage": float(target_stage),
        }

    def _junction_endpoint_stage_relation(
        self,
        rinfo: ReachInfo,
        junc: JunctionInfo,
        endpoint: str,
        z_endpoint: float,
        q_endpoint: float,
        z_junction: float,
        k_endpoint: float,
        dkdz_endpoint: float,
    ) -> tuple[float, float, float, float]:
        residual = float(z_endpoint - z_junction)
        dres_dz = 1.0
        dres_dq = 0.0
        dres_dj = -1.0
        if endpoint == "us":
            stub_len = rinfo.us_junction_distance_m
        else:
            stub_len = rinfo.ds_junction_distance_m
        if (
            junc.hecras_add_friction
            and stub_len is not None
            and float(stub_len) > 1e-9
            and k_endpoint is not None
            and float(k_endpoint) > 1e-9
        ):
            k_val = max(float(k_endpoint), 1e-9)
            q_val = float(q_endpoint)
            sf_signed = q_val * abs(q_val) / (k_val * k_val)
            residual += sf_signed * float(stub_len)
            dres_dq += 2.0 * abs(q_val) / (k_val * k_val) * float(stub_len)
            dres_dz += (
                -2.0 * q_val * abs(q_val) / (k_val * k_val * k_val)
                * max(float(dkdz_endpoint), 0.0)
                * float(stub_len)
            )
        return float(residual), float(dres_dz), float(dres_dq), float(dres_dj)

    def _capture_branch_cell_debug(
        self,
        jname: str,
        conns: list,
        offsets: dict,
        X,
        Z_n_dict: dict,
        Q_n_dict: dict,
        reach_debug_cache: dict,
        dt: float,
    ) -> list:
        branch_terms = []
        for rname_c, ep_c, _col_Z_c, _col_Q_c in conns:
            rinfo = self.reaches.get(rname_c)
            solver = self.solvers.get(rname_c)
            if rinfo is None or solver is None:
                continue
            n_r = rinfo.reach_data.n_xs
            if n_r < 2:
                continue
            if ep_c == "us":
                cell_index = 0
                location = "first_cell"
            else:
                cell_index = n_r - 2
                location = "last_cell"
            cache = reach_debug_cache.get(rname_c)
            if cache is None:
                o = offsets[rname_c]
                Z_cur = X[o:o + 2 * n_r:2].copy()
                Q_cur = X[o + 1:o + 2 * n_r:2].copy()
                Z_old = Z_n_dict[rname_c]
                Q_old = Q_n_dict[rname_c]
                A, B, K, bm, dKdZ = solver._compute_hydraulics_all(Z_cur, Q_cur)
                A_n, B_n, K_n, bm_n, dKdZ_n = solver._compute_hydraulics_all(Z_old, Q_old)
            else:
                Z_cur = cache["Z_cur"]
                Q_cur = cache["Q_cur"]
                Z_old = cache["Z_old"]
                Q_old = cache["Q_old"]
                A = cache["A"]
                B = cache["B"]
                K = cache["K"]
                bm = cache["bm"]
                dKdZ = cache["dKdZ"]
                A_n = cache["A_n"]
                B_n = cache["B_n"]
                K_n = cache["K_n"]
                bm_n = cache["bm_n"]
                dKdZ_n = cache["dKdZ_n"]
            terms = solver._compute_cell_equation_terms(
                Z_cur,
                Q_cur,
                Z_old,
                Q_old,
                A,
                B,
                K,
                bm,
                dKdZ,
                A_n,
                B_n,
                K_n,
                bm_n,
                dt,
                cell_index,
            )
            terms["junction_name"] = jname
            terms["reach_name"] = rname_c
            terms["endpoint"] = ep_c
            terms["cell_location"] = location
            branch_terms.append(terms)
        return branch_terms

    def _storage_volume(self, storage: StorageAreaInfo, stage: float) -> float:
        """库区库容 V(stage)。"""
        if storage.storage_elevations is not None and storage.storage_volumes is not None:
            return float(np.interp(stage, storage.storage_elevations, storage.storage_volumes))
        area = float(storage.area) if storage.area is not None else 0.0
        z0 = float(storage.min_elevation) if storage.min_elevation is not None else 0.0
        return max(stage - z0, 0.0) * max(area, 0.0)

    def _storage_dv_dz(self, storage: StorageAreaInfo, stage: float) -> float:
        """库区 dV/dZ(stage)。"""
        if storage.storage_elevations is not None and storage.storage_volumes is not None:
            dz_eps = 0.01
            v0 = self._storage_volume(storage, stage)
            v1 = self._storage_volume(storage, stage + dz_eps)
            return max((v1 - v0) / dz_eps, 1e-6)
        area = float(storage.area) if storage.area is not None else 0.0
        return max(area, 1e-6)

    def _storage_stage_bounds(self, storage: StorageAreaInfo) -> tuple[float, float]:
        """Reasonable stage bounds for storage-state clipping."""
        if storage.storage_elevations is not None and len(storage.storage_elevations) > 0:
            lo = float(np.min(storage.storage_elevations))
            hi = float(np.max(storage.storage_elevations))
            return lo - 0.5, hi + 0.5
        lo = float(storage.min_elevation) if storage.min_elevation is not None else 0.0
        hi = max(lo + 20.0, float(storage.initial_stage) + 10.0 if storage.initial_stage is not None else lo + 20.0)
        return lo - 0.5, hi

    def _compute_storage_connection_flow(self, conn: StorageConnectionInfo, z_up: float, z_dn: float) -> float:
        """Positive discharge means up_storage_area -> down_storage_area."""
        q_weir, q_culvert = self._compute_storage_connection_flow_components(conn, z_up, z_dn)
        return float(q_weir + q_culvert)

    def _compute_storage_connection_flow_components(self, conn: StorageConnectionInfo, z_up: float, z_dn: float) -> tuple[float, float]:
        q_weir = self._compute_structure_weir_flow(
            width=conn.weir_width,
            coef=conn.weir_coef,
            crest_elevation=conn.crest_elevation,
            z_up_stage=z_up,
            z_dn_stage=z_dn,
        )
        q_culvert = self._compute_structure_culvert_flow(
            conn,
            z_up_head=z_up,
            z_up_stage=z_up,
            z_dn_stage=z_dn,
            inlet_starts_at_invert=True,
        )
        return float(q_weir), float(q_culvert)

    def _compute_structure_weir_flow(self, width, coef, crest_elevation, z_up_stage: float, z_dn_stage: float) -> float:
        direction = 1.0 if z_up_stage >= z_dn_stage else -1.0
        z_hi = float(max(z_up_stage, z_dn_stage))
        z_lo = float(min(z_up_stage, z_dn_stage))
        if not width or not coef or crest_elevation is None:
            return 0.0
        width = max(float(width), 0.0)
        coef = max(float(coef), 0.0)
        h_hi = max(z_hi - float(crest_elevation), 0.0)
        h_lo = max(z_lo - float(crest_elevation), 0.0)
        if width <= 0.0 or coef <= 0.0 or h_hi <= 0.0:
            return 0.0
        q_free = coef * width * h_hi ** 1.5
        if h_lo > 1e-9:
            sub_ratio = min(h_lo / max(h_hi, 1e-9), 0.999999)
            q_weir = q_free * max(1.0 - sub_ratio, 0.0) ** 0.385
        else:
            q_weir = q_free
        return float(direction * q_weir)

    def _compute_structure_culvert_flow(
        self,
        conn: StorageConnectionInfo,
        z_up_head: float,
        z_up_stage: float,
        z_dn_stage: float,
        inlet_starts_at_invert: bool = False,
    ) -> float:
        direction = 1.0 if z_up_head >= z_dn_stage else -1.0
        z_hi_head = float(z_up_head if direction > 0.0 else z_dn_stage)
        z_hi_stage = float(z_up_stage if direction > 0.0 else z_dn_stage)
        z_lo_stage = float(z_dn_stage if direction > 0.0 else z_up_stage)
        if not (conn.culvert_count and conn.culvert_diameter and conn.culvert_length and conn.culvert_manning_n):
            return 0.0
        n_barrels = max(int(conn.culvert_count), 1)
        dia = max(float(conn.culvert_diameter), 1e-6)
        length = max(float(conn.culvert_length), 1e-6)
        manning_n = max(float(conn.culvert_manning_n), 1e-4)
        loss_coef = max(float(conn.culvert_loss_coef) if conn.culvert_loss_coef is not None else 0.5, 0.0)
        inlet_coef = max(float(conn.culvert_inlet_coef) if conn.culvert_inlet_coef is not None else 1.6, 0.0)
        if direction > 0.0:
            invert_hi = float(conn.culvert_us_invert if conn.culvert_us_invert is not None else 0.0)
            invert_lo = float(conn.culvert_ds_invert if conn.culvert_ds_invert is not None else invert_hi)
        else:
            invert_hi = float(conn.culvert_ds_invert if conn.culvert_ds_invert is not None else 0.0)
            invert_lo = float(conn.culvert_us_invert if conn.culvert_us_invert is not None else invert_hi)
        crown_hi = invert_hi + dia
        headwater_depth = max(z_hi_stage - invert_hi, 0.0)
        delta_h = max(z_hi_head - z_lo_stage, 0.0)
        if headwater_depth <= 0.0 or delta_h <= 0.0:
            return 0.0
        area = 0.25 * np.pi * dia * dia
        radius = dia / 4.0
        conveyance = (1.0 / manning_n) * area * radius ** (2.0 / 3.0)
        q_outlet = conveyance * np.sqrt(max((z_hi_stage - z_lo_stage), 0.0) / length)
        q_orifice = area * np.sqrt(2.0 * self.g * delta_h / max(1.0 + loss_coef, 1e-6))
        if headwater_depth < dia:
            inlet_head = max(
                z_hi_head - (invert_hi if inlet_starts_at_invert else crown_hi),
                0.0,
            )
            q_inlet = inlet_coef * dia * max(inlet_head, 0.0) ** 1.5
        else:
            q_inlet = q_orifice
        q_culvert = min(q_inlet, q_outlet, q_orifice)
        return float(direction * n_barrels * q_culvert)

    def _compute_lateral_structure_flow(self, lat: LateralStructureInfo, z_reach: float, z_storage: float) -> float:
        return self._compute_lateral_structure_flow_with_energy(lat, z_reach, z_reach, z_storage)

    def _compute_lateral_structure_flow_with_energy(self, lat: LateralStructureInfo, z_reach_stage: float, z_reach_energy: float, z_storage: float) -> float:
        """Positive discharge means reach -> storage."""
        q_weir, q_culvert = self._compute_lateral_structure_flow_components(lat, z_reach_stage, z_storage)
        return float(q_weir + q_culvert)

    def _compute_lateral_structure_flow_components(self, lat: LateralStructureInfo, z_reach_stage: float, z_storage: float) -> tuple[float, float]:
        conn_like = StorageConnectionInfo(
            name=lat.name,
            up_storage_area="reach",
            down_storage_area=lat.storage_area,
            weir_width=lat.weir_width,
            weir_coef=lat.weir_coef,
            crest_elevation=lat.crest_elevation,
            culvert_count=lat.culvert_count,
            culvert_diameter=lat.culvert_diameter,
            culvert_length=lat.culvert_length,
            culvert_manning_n=lat.culvert_manning_n,
            culvert_inlet_coef=lat.culvert_inlet_coef,
            culvert_loss_coef=lat.culvert_loss_coef,
            culvert_selector_1=lat.culvert_selector_1,
            culvert_selector_2=lat.culvert_selector_2,
            culvert_selector_3=lat.culvert_selector_3,
            culvert_us_invert=lat.culvert_us_invert,
            culvert_ds_invert=lat.culvert_ds_invert,
        )
        q_weir = self._compute_structure_weir_flow(
            width=lat.weir_width,
            coef=lat.weir_coef,
            crest_elevation=lat.crest_elevation,
            z_up_stage=z_reach_stage,
            z_dn_stage=z_storage,
        )
        q_culvert = self._compute_structure_culvert_flow(
            conn_like,
            z_up_head=z_reach_stage,
            z_up_stage=z_reach_stage,
            z_dn_stage=z_storage,
        )
        return float(q_weir), float(q_culvert)

    def _reach_stage_at_position(self, z_values: np.ndarray, dx_values: np.ndarray, cell_index: int, position_fraction: float) -> float:
        n = len(z_values)
        if n == 0:
            return 0.0
        if n == 1:
            return float(z_values[0])
        sc = max(0, min(int(cell_index), n - 2))
        frac = float(min(max(position_fraction, 0.0), 1.0))
        return (1.0 - frac) * float(z_values[sc]) + frac * float(z_values[sc + 1])

    def _representative_lateral_headwater(self, z_values: np.ndarray, q_values: np.ndarray, rinfo: ReachInfo, lat: LateralStructureInfo) -> float:
        return self._representative_lateral_stage(z_values, rinfo.reach_data.dx, lat)

    def _representative_lateral_stage(self, z_values: np.ndarray, dx_values: np.ndarray, lat: LateralStructureInfo) -> float:
        sc = max(0, min(int(lat.cell_index), len(z_values) - 2))
        frac0 = min(max(float(lat.position_fraction), 0.0), 1.0)
        z0 = self._reach_stage_at_position(z_values, dx_values, sc, frac0)
        if lat.length_m is None or lat.length_m <= 1e-9:
            return z0
        dx_cell = float(dx_values[sc]) if sc < len(dx_values) else 1.0
        frac1 = frac0 + float(lat.length_m) / max(dx_cell, 1e-6)
        sc1 = sc
        while frac1 > 1.0 and sc1 < len(z_values) - 2:
            frac1 -= 1.0
            sc1 += 1
            dx_cell = float(dx_values[sc1]) if sc1 < len(dx_values) else 1.0
        frac1 = min(max(frac1, 0.0), 1.0)
        z1 = self._reach_stage_at_position(z_values, dx_values, sc1, frac1)
        return 0.5 * (z0 + z1)

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

    def _get_junction_endpoint_spread(self, states: dict, jname: str) -> float:
        """获取 Junction 连接端点水位 spread（max-min）。"""
        junc = self.junctions[jname]
        wse_vals: list = []
        for rname in junc.upstream_reaches:
            if rname in states:
                wse_vals.append(float(states[rname].Z[-1]))
        for rname in junc.downstream_reaches:
            if rname in states:
                wse_vals.append(float(states[rname].Z[0]))
        if not wse_vals:
            return 0.0
        return float(max(wse_vals) - min(wse_vals))

    def _get_junction_flow_balance(self, states: dict, jname: str) -> float:
        """计算 Junction 流量不平衡（Q_in - Q_out）。"""
        junc = self.junctions[jname]
        balance = 0.0
        for rname in junc.upstream_reaches:
            if rname in states:
                balance += self._junction_endpoint_flow_sign(junc, rname, "ds") * float(states[rname].Q[-1])
        for rname in junc.downstream_reaches:
            if rname in states:
                balance += self._junction_endpoint_flow_sign(junc, rname, "us") * float(states[rname].Q[0])
        return float(balance)

    def _junction_endpoint_flow_sign(self, junc: JunctionInfo, rname: str, endpoint: str) -> float:
        key = f"{rname}|{endpoint}"
        sign = junc.preprocess_endpoint_signs.get(key)
        if sign is not None and np.isfinite(sign) and abs(float(sign)) > 1e-9:
            return float(sign)
        return 1.0 if endpoint == "ds" else -1.0

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

    def _update_storage_states(
        self,
        states: dict,
        storage_states_old: dict,
        storage_stage_guess: dict,
        dt: float,
    ) -> dict:
        """Update storage stages from reach/storage exchange using Picard lagging."""
        new_storage = {}
        for sname, storage in self.storage_areas.items():
            stage_old = float(storage_states_old[sname])
            stage_guess = float(storage_stage_guess[sname])
            net_q = 0.0
            for rname, rinfo in self.reaches.items():
                if rinfo.ds_type == "storage_area" and rinfo.ds_name == sname:
                    net_q += float(states[rname].Q[-1])
                if rinfo.us_type == "storage_area" and rinfo.us_name == sname:
                    net_q -= float(states[rname].Q[0])
            for conn in self.storage_connections:
                z_up = float(storage_stage_guess[conn.up_storage_area])
                z_dn = float(storage_stage_guess[conn.down_storage_area])
                q_conn = self._compute_storage_connection_flow(conn, z_up, z_dn)
                if conn.up_storage_area == sname:
                    net_q -= q_conn
                if conn.down_storage_area == sname:
                    net_q += q_conn
            for lat in self.lateral_structures:
                if lat.storage_area != sname or lat.reach_name not in states:
                    continue
                rstate = states[lat.reach_name]
                rinfo = self.reaches[lat.reach_name]
                z_stage = self._representative_lateral_stage(rstate.Z, rinfo.reach_data.dx, lat)
                z_energy = self._representative_lateral_headwater(rstate.Z, rstate.Q, rinfo, lat)
                q_lat = self._compute_lateral_structure_flow_with_energy(lat, z_stage, z_energy, stage_guess)
                net_q += q_lat

            vol_old = self._storage_volume(storage, stage_old)
            vol_target = vol_old + dt * net_q
            if storage.storage_elevations is not None and storage.storage_volumes is not None:
                stage_new = float(np.interp(
                    vol_target,
                    storage.storage_volumes,
                    storage.storage_elevations,
                    left=float(storage.storage_elevations[0]),
                    right=float(storage.storage_elevations[-1]),
                ))
            else:
                area = max(float(storage.area) if storage.area is not None else 1.0, 1e-6)
                z0 = float(storage.min_elevation) if storage.min_elevation is not None else 0.0
                stage_new = z0 + max(vol_target, 0.0) / area
            z_lo, z_hi = self._storage_stage_bounds(storage)
            stage_new = min(max(stage_new, max(z_lo, stage_old - self.max_storage_step_dZ)), min(z_hi, stage_old + self.max_storage_step_dZ))
            new_storage[sname] = stage_new
        return new_storage

    # ------------------------------------------------------------------
    # 单时间步
    # ------------------------------------------------------------------

    def step(self, states: dict, dt: float, t_new: float, storage_states: dict | None = None, freeze_storage: bool = False) -> tuple[dict, dict]:
        """推进一个时间步 — 全局 NR 求解（所有 reach + junction 同时求解）。

        将各 reach 的 Preissmann 方程拼成一个大稀疏矩阵，
        junction 方程（水位连续 + 流量守恒）替换 reach 端部 BC 行。
        """
        import scipy.sparse as sp
        from scipy.sparse.linalg import spsolve, lsmr, MatrixRankWarning

        reach_order = self._topo_order
        storage_states = dict(storage_states or {})

        # 1. 全局变量布局: [reach1_Z0,Q0,...,Zn,Qn | reach2_... | ...]
        offsets = {}  # reach_name -> global offset
        offset = 0
        for rname in reach_order:
            offsets[rname] = offset
            offset += 2 * self.reaches[rname].reach_data.n_xs
        storage_offsets = {}
        storage_order = [] if freeze_storage else list(self.storage_areas.keys())
        for sname in storage_order:
            storage_offsets[sname] = offset
            offset += 1
        junction_state_order = [
            jname for jname in self.junction_state_names
            if jname in self.junctions
        ]
        junction_state_offsets = {}
        for jname in junction_state_order:
            junction_state_offsets[jname] = offset
            offset += 1
        global_size = offset
        junction_iter_clip_counts = {jname: 0 for jname in junction_state_order}
        junction_step_clip_counts = {jname: 0 for jname in junction_state_order}

        # 初始化全局 X (from current iterate = old state)
        X = np.zeros(global_size)
        for rname in reach_order:
            n_r = self.reaches[rname].reach_data.n_xs
            o = offsets[rname]
            X[o:o + 2 * n_r:2] = states[rname].Z
            X[o + 1:o + 2 * n_r:2] = states[rname].Q
        for sname in storage_order:
            storage = self.storage_areas[sname]
            stage = storage_states.get(sname)
            if stage is None:
                if storage.initial_stage is not None:
                    stage = float(storage.initial_stage)
                elif storage.storage_elevations is not None and len(storage.storage_elevations) > 0:
                    stage = float(storage.storage_elevations[0])
                else:
                    stage = float(storage.min_elevation or 0.0)
            X[storage_offsets[sname]] = float(stage)
        junction_old = {}
        for jname in junction_state_order:
            z_old = self._get_junction_wse(states, jname)
            junction_old[jname] = float(z_old)
            X[junction_state_offsets[jname]] = float(z_old)

        # Old state arrays
        Z_n_dict = {rname: states[rname].Z.copy() for rname in reach_order}
        Q_n_dict = {rname: states[rname].Q.copy() for rname in reach_order}
        storage_old = {sname: float(X[storage_offsets[sname]]) for sname in storage_order}

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
        converged = False
        max_res = float("inf")
        capture_junction_debug = self._junction_debug_enabled(t_new)
        current_junction_debug: list = []
        for nr_iter in range(self.nr_max_iter):
            F_global = np.zeros(global_size)
            J_global = sp.lil_matrix((global_size, global_size))
            local_bc_debug: dict = {}
            reach_debug_cache: dict = {}

            # Get current junction Z from master endpoint (not average)
            junc_Z = {}
            for jname in self.junctions:
                if jname in junction_state_offsets:
                    junc_Z[jname] = float(X[junction_state_offsets[jname]])
                else:
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

                A, B, K, bm, dKdZ = solver._compute_hydraulics_all(Z_cur, Q_cur)
                A_n, B_n, K_n, bm_n, dKdZ_n = solver._compute_hydraulics_all(Z_old, Q_old)

                # Upstream BC
                Z_up_val = None
                Q_up_val = 0.0
                if rinfo.us_type == "external":
                    bc = self.external_bcs.get(rname + "_us")
                    if bc is not None and callable(bc):
                        Q_up_val = float(bc(t_new))
                elif rinfo.us_type == "storage_area":
                    Z_up_val = float(storage_states[rinfo.us_name]) if freeze_storage else float(X[storage_offsets[rinfo.us_name]])
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
                elif rinfo.ds_type == "storage_area":
                    ds_junc_Z = float(storage_states[rinfo.ds_name]) if freeze_storage else float(X[storage_offsets[rinfo.ds_name]])
                    ds_bc = lambda t: 0.0
                else:
                    # Junction downstream: pass ds_junction_Z to _build_system
                    ds_junc_Z = junc_Z[rinfo.ds_name]
                    ds_bc = lambda t: 0.0  # placeholder

                F_local, J_local = solver._build_system(
                    Z_cur, Q_cur, Z_old, Q_old,
                    A, B, K, bm, dKdZ, A_n, B_n, K_n, bm_n,
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
                if capture_junction_debug:
                    reach_debug_cache[rname] = {
                        "Z_cur": Z_cur.copy(),
                        "Q_cur": Q_cur.copy(),
                        "Z_old": Z_old.copy(),
                        "Q_old": Q_old.copy(),
                        "A": A.copy(),
                        "B": B.copy(),
                        "K": K.copy(),
                        "bm": bm.copy(),
                        "dKdZ": dKdZ.copy(),
                        "A_n": A_n.copy(),
                        "B_n": B_n.copy(),
                        "K_n": K_n.copy(),
                        "bm_n": bm_n.copy(),
                        "dKdZ_n": dKdZ_n.copy(),
                    }
                if capture_junction_debug:
                    if rinfo.us_type == "junction" and rinfo.us_name in self.junction_debug_names and Z_up_val is not None:
                        self._capture_local_bc_debug(
                            local_bc_debug,
                            rinfo.us_name,
                            rname,
                            "us",
                            F_local,
                            J_local_lil,
                            n_r,
                            float(Z_up_val),
                        )
                    if rinfo.ds_type == "junction" and rinfo.ds_name in self.junction_debug_names and ds_junc_Z is not None:
                        self._capture_local_bc_debug(
                            local_bc_debug,
                            rinfo.ds_name,
                            rname,
                            "ds",
                            F_local,
                            J_local_lil,
                            n_r,
                            float(ds_junc_Z),
                        )
                if rinfo.us_type == "junction" and rinfo.us_name in junction_state_offsets:
                    jcol = junction_state_offsets[rinfo.us_name]
                    junc = self.junctions[rinfo.us_name]
                    bc_row = o
                    z_ep = float(X[o])
                    q_ep = float(X[o + 1])
                    res, dres_dz, dres_dq, dres_dj = self._junction_endpoint_stage_relation(
                        rinfo,
                        junc,
                        "us",
                        z_ep,
                        q_ep,
                        float(X[jcol]),
                        float(K[0]),
                        float(dKdZ[0]),
                    )
                    J_global[bc_row, :] = 0
                    F_global[bc_row] = res
                    J_global[bc_row, o] = dres_dz
                    J_global[bc_row, o + 1] = dres_dq
                    J_global[bc_row, jcol] = dres_dj
                if rinfo.ds_type == "junction" and rinfo.ds_name in junction_state_offsets:
                    jcol = junction_state_offsets[rinfo.ds_name]
                    junc = self.junctions[rinfo.ds_name]
                    bc_row = o + 2 * n_r - 1
                    col_z = o + 2 * (n_r - 1)
                    col_q = col_z + 1
                    z_ep = float(X[col_z])
                    q_ep = float(X[col_q])
                    res, dres_dz, dres_dq, dres_dj = self._junction_endpoint_stage_relation(
                        rinfo,
                        junc,
                        "ds",
                        z_ep,
                        q_ep,
                        float(X[jcol]),
                        float(K[-1]),
                        float(dKdZ[-1]),
                    )
                    J_global[bc_row, :] = 0
                    F_global[bc_row] = res
                    J_global[bc_row, col_z] = dres_dz
                    J_global[bc_row, col_q] = dres_dq
                    J_global[bc_row, jcol] = dres_dj

                for lat in self.lateral_structures:
                    if lat.reach_name != rname:
                        continue
                    if freeze_storage:
                        z_storage = float(storage_states.get(lat.storage_area, 0.0))
                        col_s = None
                    else:
                        if lat.storage_area not in storage_offsets:
                            continue
                        col_s = storage_offsets[lat.storage_area]
                        z_storage = float(X[col_s])
                    sc = max(0, min(int(lat.cell_index), n_r - 2))
                    row_c = o + 2 * sc + 1
                    col_z_l = o + 2 * sc
                    col_z_r = o + 2 * (sc + 1)
                    z_reach_arr = X[o:o + 2 * n_r:2]
                    q_reach_arr = X[o + 1:o + 2 * n_r:2]
                    dx_values = rinfo.reach_data.dx
                    z_stage = self._representative_lateral_stage(z_reach_arr, dx_values, lat)
                    z_energy = self._representative_lateral_headwater(z_reach_arr, q_reach_arr, rinfo, lat)
                    q_lat = self._compute_lateral_structure_flow_with_energy(lat, z_stage, z_energy, z_storage)
                    dx_cell = max(float(rinfo.reach_data.dx[sc]), 1.0)
                    F_global[row_c] += q_lat / dx_cell
                    eps = 1e-4
                    z_trial = z_reach_arr.copy()
                    z_trial[sc] += eps
                    q_zl = self._compute_lateral_structure_flow_with_energy(
                        lat,
                        self._representative_lateral_stage(z_trial, dx_values, lat),
                        self._representative_lateral_headwater(z_trial, q_reach_arr, rinfo, lat),
                        z_storage,
                    )
                    z_trial = z_reach_arr.copy()
                    z_trial[sc + 1] += eps
                    q_zr = self._compute_lateral_structure_flow_with_energy(
                        lat,
                        self._representative_lateral_stage(z_trial, dx_values, lat),
                        self._representative_lateral_headwater(z_trial, q_reach_arr, rinfo, lat),
                        z_storage,
                    )
                    J_global[row_c, col_z_l] += (q_zl - q_lat) / eps / dx_cell
                    J_global[row_c, col_z_r] += (q_zr - q_lat) / eps / dx_cell
                    q_trial = q_reach_arr.copy()
                    q_trial[sc] += eps
                    q_ql = self._compute_lateral_structure_flow_with_energy(
                        lat,
                        z_stage,
                        self._representative_lateral_headwater(z_reach_arr, q_trial, rinfo, lat),
                        z_storage,
                    )
                    q_trial = q_reach_arr.copy()
                    q_trial[sc + 1] += eps
                    q_qr = self._compute_lateral_structure_flow_with_energy(
                        lat,
                        z_stage,
                        self._representative_lateral_headwater(z_reach_arr, q_trial, rinfo, lat),
                        z_storage,
                    )
                    J_global[row_c, col_z_l + 1] += (q_ql - q_lat) / eps / dx_cell
                    J_global[row_c, col_z_r + 1] += (q_qr - q_lat) / eps / dx_cell
                    if col_s is not None:
                        q_zs = self._compute_lateral_structure_flow_with_energy(
                            lat, z_stage, z_energy, float(X[col_s] + eps)
                        )
                        J_global[row_c, col_s] += (q_zs - q_lat) / eps / dx_cell

            # 2b. Junction coupling: replace BC rows with cross-reach equations
            current_junction_debug = []
            for jname, junc in self.junctions.items():
                conns = junc_connections[jname]
                if len(conns) < 2:
                    continue

                if jname in junction_state_offsets:
                    jcol = junction_state_offsets[jname]
                    J_global[jcol, :] = 0
                    F_val = 0.0
                    for rname_c, ep_c, col_Z_c, col_Q_c in conns:
                        q_sign = self._junction_endpoint_flow_sign(junc, rname_c, ep_c)
                        F_val += q_sign * X[col_Q_c]
                        J_global[jcol, col_Q_c] = q_sign

                    dVdt = 0.0
                    dVdZdt = 0.0
                    if junc.storage_elevations is not None and junc.storage_volumes is not None:
                        Z_junc_new = float(X[jcol])
                        Z_junc_old = float(junction_old[jname])
                        V_new = float(np.interp(Z_junc_new, junc.storage_elevations, junc.storage_volumes))
                        V_old = float(np.interp(Z_junc_old, junc.storage_elevations, junc.storage_volumes))
                        dVdt = (V_new - V_old) / dt
                        F_val -= dVdt
                        dz_eps = 0.01
                        V_plus = float(np.interp(Z_junc_new + dz_eps, junc.storage_elevations, junc.storage_volumes))
                        dVdZ = (V_plus - V_new) / dz_eps
                        dVdZdt = dVdZ / dt
                        J_global[jcol, jcol] += -dVdZdt

                    F_global[jcol] = F_val

                    if capture_junction_debug and jname in self.junction_debug_names:
                        endpoint_states = []
                        q_in = 0.0
                        q_out = 0.0
                        for rname_c, ep_c, col_Z_c, col_Q_c in conns:
                            z_c = float(X[col_Z_c])
                            q_c = float(X[col_Q_c])
                            q_sign = self._junction_endpoint_flow_sign(junc, rname_c, ep_c)
                            endpoint_states.append({
                                "reach_name": rname_c,
                                "endpoint": ep_c,
                                "Z": z_c,
                                "Q": q_c,
                                "continuity_sign": float(q_sign),
                            })
                            if q_sign > 0.0:
                                q_in += q_c
                            else:
                                q_out += q_c
                        current_junction_debug.append({
                            "junction_name": jname,
                            "t_new_s": float(t_new),
                            "nr_iter": int(nr_iter + 1),
                            "freeze_storage": bool(freeze_storage),
                            "master_reach": "__junction_state__",
                            "master_endpoint": "junction",
                            "master_stage": float(X[jcol]),
                            "master_flow": 0.0,
                            "master_fc_row": int(jcol),
                            "q_in_sum": float(q_in),
                            "q_out_sum": float(q_out),
                            "dVdt": float(dVdt),
                            "continuity_residual": float(F_val),
                            "dF_dZ_master_storage": float(-dVdZdt),
                            "endpoint_states": endpoint_states,
                            "local_bc": list(local_bc_debug.get(jname, {}).values()),
                            "branch_equation_terms": self._capture_branch_cell_debug(
                                jname,
                                conns,
                                offsets,
                                X,
                                Z_n_dict,
                                Q_n_dict,
                                reach_debug_cache,
                                dt,
                            ),
                        })
                    continue

                master = junc_master[jname]
                master_rname, master_ep, master_col_Z, master_col_Q = master
                master_o = offsets[master_rname]
                n_master = self.reaches[master_rname].reach_data.n_xs

                # Master's BC row → flow conservation with junction storage:
                # ΣQ_in - ΣQ_out - dV_junc/dt = 0
                # dV_junc/dt ≈ (V(Z_junc) - V(Z_junc_old)) / dt
                fc_row = master_o + 2 * n_master - 1
                J_global[fc_row, :] = 0
                F_val = 0.0
                for rname_c, ep_c, col_Z_c, col_Q_c in conns:
                    q_sign = self._junction_endpoint_flow_sign(junc, rname_c, ep_c)
                    F_val += q_sign * X[col_Q_c]
                    J_global[fc_row, col_Q_c] = q_sign

                # Junction storage: dV/dt term
                dVdt = 0.0
                dVdZdt = 0.0
                if junc.storage_elevations is not None and junc.storage_volumes is not None:
                    Z_junc_new = float(X[master_col_Z])
                    # Old junction Z from master reach's old state
                    if master_ep == "ds":
                        Z_junc_old = float(Z_n_dict[master_rname][-1])
                    else:
                        Z_junc_old = float(Z_n_dict[master_rname][0])
                    V_new = float(np.interp(Z_junc_new, junc.storage_elevations,
                                            junc.storage_volumes))
                    V_old = float(np.interp(Z_junc_old, junc.storage_elevations,
                                            junc.storage_volumes))
                    dVdt = (V_new - V_old) / dt
                    F_val -= dVdt
                    # Jacobian: dF/dZ_master = -dV/dZ / dt
                    dz_eps = 0.01
                    V_plus = float(np.interp(Z_junc_new + dz_eps, junc.storage_elevations,
                                             junc.storage_volumes))
                    dVdZ = (V_plus - V_new) / dz_eps
                    dVdZdt = dVdZ / dt
                    J_global[fc_row, master_col_Z] += -dVdZdt

                F_global[fc_row] = F_val

                # Other connections: Z equality to master
                for rname_c, ep_c, col_Z_c, col_Q_c in conns:
                    if (rname_c, ep_c) == (master_rname, master_ep):
                        continue
                    o_c = offsets[rname_c]
                    n_c = self.reaches[rname_c].reach_data.n_xs
                    if ep_c == "us":
                        bc_row = o_c  # row 0
                    else:
                        bc_row = o_c + 2 * n_c - 1  # last row
                    J_global[bc_row, :] = 0
                    F_global[bc_row] = X[col_Z_c] - X[master_col_Z]
                    J_global[bc_row, col_Z_c] = 1.0
                    J_global[bc_row, master_col_Z] = -1.0

                if capture_junction_debug and jname in self.junction_debug_names:
                    endpoint_states = []
                    q_in = 0.0
                    q_out = 0.0
                    for rname_c, ep_c, col_Z_c, col_Q_c in conns:
                        z_c = float(X[col_Z_c])
                        q_c = float(X[col_Q_c])
                        q_sign = self._junction_endpoint_flow_sign(junc, rname_c, ep_c)
                        endpoint_states.append({
                            "reach_name": rname_c,
                            "endpoint": ep_c,
                            "Z": z_c,
                            "Q": q_c,
                            "continuity_sign": float(q_sign),
                        })
                        if q_sign > 0.0:
                            q_in += q_c
                        else:
                            q_out += q_c
                    current_junction_debug.append({
                        "junction_name": jname,
                        "t_new_s": float(t_new),
                        "nr_iter": int(nr_iter + 1),
                        "freeze_storage": bool(freeze_storage),
                        "master_reach": master_rname,
                        "master_endpoint": master_ep,
                        "master_stage": float(X[master_col_Z]),
                        "master_flow": float(X[master_col_Q]),
                        "master_fc_row": int(fc_row),
                        "q_in_sum": float(q_in),
                        "q_out_sum": float(q_out),
                        "dVdt": float(dVdt),
                        "continuity_residual": float(F_val),
                        "dF_dZ_master_storage": float(-dVdZdt),
                        "endpoint_states": endpoint_states,
                        "local_bc": list(local_bc_debug.get(jname, {}).values()),
                        "branch_equation_terms": self._capture_branch_cell_debug(
                            jname,
                            conns,
                            offsets,
                            X,
                            Z_n_dict,
                            Q_n_dict,
                            reach_debug_cache,
                            dt,
                        ),
                    })

            # 2c. Storage-area coupling: endpoint stage equality + storage continuity
            for sname in storage_order:
                s_col = storage_offsets[sname]
                storage = self.storage_areas[sname]
                connected = []
                for rname in reach_order:
                    rinfo = self.reaches[rname]
                    n_r = rinfo.reach_data.n_xs
                    o = offsets[rname]
                    if rinfo.ds_type == "storage_area" and rinfo.ds_name == sname:
                        connected.append((rname, "ds", o + 2 * (n_r - 1), o + 2 * (n_r - 1) + 1))
                    if rinfo.us_type == "storage_area" and rinfo.us_name == sname:
                        connected.append((rname, "us", o, o + 1))

                for rname_c, ep_c, col_Z_c, _col_Q_c in connected:
                    o_c = offsets[rname_c]
                    n_c = self.reaches[rname_c].reach_data.n_xs
                    bc_row = o_c if ep_c == "us" else o_c + 2 * n_c - 1
                    J_global[bc_row, :] = 0
                    F_global[bc_row] = X[col_Z_c] - X[s_col]
                    J_global[bc_row, col_Z_c] = 1.0
                    J_global[bc_row, s_col] = -1.0

                J_global[s_col, :] = 0
                stage_new = float(X[s_col])
                stage_old = float(storage_old[sname])
                F_storage = (self._storage_volume(storage, stage_new) - self._storage_volume(storage, stage_old)) / dt
                J_global[s_col, s_col] = self._storage_dv_dz(storage, stage_new) / dt
                for _rname_c, ep_c, _col_Z_c, col_Q_c in connected:
                    if ep_c == "ds":
                        F_storage -= X[col_Q_c]
                        J_global[s_col, col_Q_c] = -1.0
                    else:
                        F_storage += X[col_Q_c]
                        J_global[s_col, col_Q_c] = 1.0

                for conn in self.storage_connections:
                    if conn.up_storage_area == sname or conn.down_storage_area == sname:
                        col_up = storage_offsets[conn.up_storage_area]
                        col_dn = storage_offsets[conn.down_storage_area]
                        z_up = float(X[col_up])
                        z_dn = float(X[col_dn])
                        q_conn = self._compute_storage_connection_flow(conn, z_up, z_dn)
                        if conn.up_storage_area == sname:
                            F_storage += q_conn
                        if conn.down_storage_area == sname:
                            F_storage -= q_conn
                        eps = 1e-4
                        q_up_p = self._compute_storage_connection_flow(conn, z_up + eps, z_dn)
                        q_dn_p = self._compute_storage_connection_flow(conn, z_up, z_dn + eps)
                        sign = 1.0 if conn.up_storage_area == sname else -1.0
                        J_global[s_col, col_up] += sign * (q_up_p - q_conn) / eps
                        J_global[s_col, col_dn] += sign * (q_dn_p - q_conn) / eps

                for lat in self.lateral_structures:
                    if lat.storage_area != sname or lat.reach_name not in offsets:
                        continue
                    rinfo = self.reaches[lat.reach_name]
                    o_r = offsets[lat.reach_name]
                    sc = max(0, min(int(lat.cell_index), rinfo.reach_data.n_xs - 2))
                    col_z_l = o_r + 2 * sc
                    col_z_r = o_r + 2 * (sc + 1)
                    z_reach_arr = X[o_r:o_r + 2 * rinfo.reach_data.n_xs:2]
                    q_reach_arr = X[o_r + 1:o_r + 2 * rinfo.reach_data.n_xs:2]
                    dx_values = rinfo.reach_data.dx
                    z_stage = self._representative_lateral_stage(z_reach_arr, dx_values, lat)
                    z_energy = self._representative_lateral_headwater(z_reach_arr, q_reach_arr, rinfo, lat)
                    z_storage = float(X[s_col])
                    q_lat = self._compute_lateral_structure_flow_with_energy(lat, z_stage, z_energy, z_storage)
                    F_storage -= q_lat
                    eps = 1e-4
                    z_trial = z_reach_arr.copy()
                    z_trial[sc] += eps
                    q_zl = self._compute_lateral_structure_flow_with_energy(
                        lat,
                        self._representative_lateral_stage(z_trial, dx_values, lat),
                        self._representative_lateral_headwater(z_trial, q_reach_arr, rinfo, lat),
                        z_storage,
                    )
                    z_trial = z_reach_arr.copy()
                    z_trial[sc + 1] += eps
                    q_zr = self._compute_lateral_structure_flow_with_energy(
                        lat,
                        self._representative_lateral_stage(z_trial, dx_values, lat),
                        self._representative_lateral_headwater(z_trial, q_reach_arr, rinfo, lat),
                        z_storage,
                    )
                    q_trial = q_reach_arr.copy()
                    q_trial[sc] += eps
                    q_ql = self._compute_lateral_structure_flow_with_energy(
                        lat,
                        z_stage,
                        self._representative_lateral_headwater(z_reach_arr, q_trial, rinfo, lat),
                        z_storage,
                    )
                    q_trial = q_reach_arr.copy()
                    q_trial[sc + 1] += eps
                    q_qr = self._compute_lateral_structure_flow_with_energy(
                        lat,
                        z_stage,
                        self._representative_lateral_headwater(z_reach_arr, q_trial, rinfo, lat),
                        z_storage,
                    )
                    q_zs = self._compute_lateral_structure_flow_with_energy(lat, z_stage, z_energy, float(X[s_col] + eps))
                    J_global[s_col, col_z_l] += -(q_zl - q_lat) / eps
                    J_global[s_col, col_z_r] += -(q_zr - q_lat) / eps
                    J_global[s_col, col_z_l + 1] += -(q_ql - q_lat) / eps
                    J_global[s_col, col_z_r + 1] += -(q_qr - q_lat) / eps
                    J_global[s_col, s_col] += -(q_zs - q_lat) / eps
                F_global[s_col] = F_storage

            # 2d. Solve global system
            max_res = float(np.max(np.abs(F_global)))
            if max_res < self.nr_tol:
                converged = True
                break

            try:
                with warnings.catch_warnings(record=True) as caught:
                    warnings.simplefilter("always", MatrixRankWarning)
                    dX = spsolve(J_global.tocsr(), -F_global)
                if any(isinstance(w.message, MatrixRankWarning) for w in caught):
                    raise MatrixRankWarning("singular")
            except Exception:
                try:
                    J_reg = J_global.tolil()
                    reg_eps = 1e-6
                    for ireg in range(global_size):
                        J_reg[ireg, ireg] = J_reg[ireg, ireg] + reg_eps
                    dX = lsmr(J_reg.tocsr(), -F_global, atol=1e-8, btol=1e-8, maxiter=200)[0]
                except Exception:
                    break

            if not np.all(np.isfinite(dX)):
                try:
                    J_reg = J_global.tolil()
                    reg_eps = 1e-6
                    for ireg in range(global_size):
                        J_reg[ireg, ireg] = J_reg[ireg, ireg] + reg_eps
                    dX = lsmr(J_reg.tocsr(), -F_global, atol=1e-8, btol=1e-8, maxiter=200)[0]
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
                    dq = dX_clipped[o + 2 * i + 1]
                    if abs(dq) > self.max_dQ:
                        dX_clipped[o + 2 * i + 1] = np.sign(dq) * self.max_dQ
            for sname in storage_order:
                scol = storage_offsets[sname]
                dz = dX_clipped[scol]
                if abs(dz) > self.max_storage_dZ:
                    dX_clipped[scol] = np.sign(dz) * self.max_storage_dZ
            for jname in junction_state_order:
                jcol = junction_state_offsets[jname]
                dz = dX_clipped[jcol]
                if abs(dz) > self.max_junction_dZ:
                    junction_iter_clip_counts[jname] += 1
                    dX_clipped[jcol] = np.sign(dz) * self.max_junction_dZ

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
            for sname in storage_order:
                scol = storage_offsets[sname]
                z_lo, z_hi = self._storage_stage_bounds(self.storage_areas[sname])
                z_old = storage_old[sname]
                z_lo = max(z_lo, z_old - self.max_storage_step_dZ)
                z_hi = min(z_hi, z_old + self.max_storage_step_dZ)
                if X[scol] < z_lo:
                    X[scol] = z_lo
                elif X[scol] > z_hi:
                    X[scol] = z_hi
            for jname in junction_state_order:
                jcol = junction_state_offsets[jname]
                z_old = junction_old[jname]
                z_lo = z_old - self.max_junction_step_dZ
                z_hi = z_old + self.max_junction_step_dZ
                if X[jcol] < z_lo:
                    junction_step_clip_counts[jname] += 1
                    X[jcol] = z_lo
                elif X[jcol] > z_hi:
                    junction_step_clip_counts[jname] += 1
                    X[jcol] = z_hi

        # 3. Extract results
        new_states = {}
        for rname in reach_order:
            o = offsets[rname]
            n_r = self.reaches[rname].reach_data.n_xs
            Z_new = X[o:o + 2 * n_r:2].copy()
            Q_new = X[o + 1:o + 2 * n_r:2].copy()
            new_states[rname] = UnsteadyState(Z=Z_new, Q=Q_new, t=t_new)
        new_storage_states = {sname: float(X[storage_offsets[sname]]) for sname in storage_order}
        if freeze_storage:
            new_storage_states = dict(storage_states)
        self._last_step_converged = converged
        self._last_step_residual = max_res
        self._last_step_junction_states = {
            jname: float(X[junction_state_offsets[jname]])
            for jname in junction_state_order
        }
        self._last_step_junction_iter_clip_counts = dict(junction_iter_clip_counts)
        self._last_step_junction_step_clip_counts = dict(junction_step_clip_counts)
        self._last_step_junction_debug = []
        for item in current_junction_debug:
            rec = dict(item)
            rec["step_converged"] = bool(converged)
            rec["step_final_residual"] = float(max_res)
            self._last_step_junction_debug.append(rec)

        return new_states, new_storage_states

    def _merge_solver_diagnostics(self, *items: dict) -> dict:
        merged = {
            "converged": True,
            "attempted_substeps": 0,
            "substep_splits": 0,
            "step_nonconvergence_count": 0,
            "max_step_residual": 0.0,
            "picard_iterations": 0,
            "junction_debug_records": [],
            "junction_iter_clip_counts": {},
            "junction_step_clip_counts": {},
        }
        for item in items:
            if not item:
                continue
            merged["converged"] = merged["converged"] and bool(item.get("converged", True))
            merged["attempted_substeps"] += int(item.get("attempted_substeps", 0))
            merged["substep_splits"] += int(item.get("substep_splits", 0))
            merged["step_nonconvergence_count"] += int(item.get("step_nonconvergence_count", 0))
            merged["max_step_residual"] = max(
                merged["max_step_residual"],
                float(item.get("max_step_residual", 0.0)),
            )
            merged["picard_iterations"] += int(item.get("picard_iterations", 0))
            merged["junction_debug_records"].extend(item.get("junction_debug_records", []))
            for key in ("junction_iter_clip_counts", "junction_step_clip_counts"):
                src = item.get(key, {}) or {}
                dst = merged[key]
                for jname, count in src.items():
                    dst[jname] = int(dst.get(jname, 0)) + int(count)
        return merged

    def _init_internal_exchange_diagnostics(self) -> dict:
        return {
            "storage_connections": {
                conn.name: {
                    "name": conn.name,
                    "max_abs_q_m3s": 0.0,
                    "time_of_max_s": None,
                    "first_active_s": None,
                    "first_reverse_flow_s": None,
                }
                for conn in self.storage_connections
            },
            "lateral_structures": {
                lat.name: {
                    "name": lat.name,
                    "reach_name": lat.reach_name,
                    "storage_area": lat.storage_area,
                    "max_abs_q_m3s": 0.0,
                    "time_of_max_s": None,
                    "first_active_s": None,
                    "first_reverse_flow_s": None,
                }
                for lat in self.lateral_structures
            },
        }

    def _update_internal_exchange_diagnostics(
        self,
        diagnostics: dict,
        states: dict,
        storage_states: dict,
        t: float,
    ) -> None:
        for conn in self.storage_connections:
            q_conn = float(
                self._compute_storage_connection_flow(
                    conn,
                    float(storage_states[conn.up_storage_area]),
                    float(storage_states[conn.down_storage_area]),
                )
            )
            item = diagnostics["storage_connections"][conn.name]
            if abs(q_conn) > item["max_abs_q_m3s"]:
                item["max_abs_q_m3s"] = abs(q_conn)
                item["time_of_max_s"] = float(t)
            if item["first_active_s"] is None and abs(q_conn) > 1e-9:
                item["first_active_s"] = float(t)
            if item["first_reverse_flow_s"] is None and q_conn < -1e-9:
                item["first_reverse_flow_s"] = float(t)

        for lat in self.lateral_structures:
            if lat.reach_name not in states or lat.storage_area not in storage_states:
                continue
            rinfo = self.reaches[lat.reach_name]
            rstate = states[lat.reach_name]
            z_stage = self._representative_lateral_stage(rstate.Z, rinfo.reach_data.dx, lat)
            q_lat = float(
                self._compute_lateral_structure_flow(
                    lat,
                    z_stage,
                    float(storage_states[lat.storage_area]),
                )
            )
            item = diagnostics["lateral_structures"][lat.name]
            if abs(q_lat) > item["max_abs_q_m3s"]:
                item["max_abs_q_m3s"] = abs(q_lat)
                item["time_of_max_s"] = float(t)
            if item["first_active_s"] is None and abs(q_lat) > 1e-9:
                item["first_active_s"] = float(t)
            if item["first_reverse_flow_s"] is None and q_lat < -1e-9:
                item["first_reverse_flow_s"] = float(t)

    def _advance_interval_once(
        self,
        states: dict,
        storage_states: dict,
        dt: float,
        t_new: float,
    ) -> tuple[dict, dict, dict]:
        diagnostics = {
            "converged": True,
            "attempted_substeps": 1,
            "substep_splits": 0,
            "step_nonconvergence_count": 0,
            "max_step_residual": 0.0,
            "picard_iterations": 0,
            "junction_debug_records": [],
            "junction_iter_clip_counts": {},
            "junction_step_clip_counts": {},
        }

        if self.storage_areas:
            storage_guess = dict(storage_states)
            new_states = None
            new_storage_states = dict(storage_states)
            picard_converged = False
            for picard_iter in range(1, self.storage_picard_max_iter + 1):
                trial_states, _ = self.step(
                    states,
                    dt,
                    t_new,
                    storage_states=storage_guess,
                    freeze_storage=True,
                )
                diagnostics["picard_iterations"] += 1
                diagnostics["max_step_residual"] = max(
                    diagnostics["max_step_residual"],
                    float(self._last_step_residual),
                )
                for item in self._last_step_junction_debug:
                    rec = dict(item)
                    rec["picard_iter"] = int(picard_iter)
                    diagnostics["junction_debug_records"].append(rec)
                for key, src in (
                    ("junction_iter_clip_counts", self._last_step_junction_iter_clip_counts),
                    ("junction_step_clip_counts", self._last_step_junction_step_clip_counts),
                ):
                    for jname, count in src.items():
                        diagnostics[key][jname] = int(diagnostics[key].get(jname, 0)) + int(count)
                if not self._last_step_converged:
                    diagnostics["step_nonconvergence_count"] += 1
                storage_update = self._update_storage_states(
                    trial_states,
                    storage_states,
                    storage_guess,
                    dt,
                )
                relaxed_storage = {}
                max_storage_change = 0.0
                for sname in self.storage_areas:
                    z_old = float(storage_guess[sname])
                    z_new = float(storage_update[sname])
                    z_relaxed = (
                        (1.0 - self.storage_picard_relax) * z_old
                        + self.storage_picard_relax * z_new
                    )
                    relaxed_storage[sname] = z_relaxed
                    max_storage_change = max(max_storage_change, abs(z_relaxed - z_old))
                new_states = trial_states
                new_storage_states = relaxed_storage
                storage_guess = relaxed_storage
                if self._last_step_converged and max_storage_change < self.storage_picard_tol:
                    picard_converged = True
                    break
            diagnostics["converged"] = picard_converged
            return new_states, new_storage_states, diagnostics

        new_states, new_storage_states = self.step(
            states,
            dt,
            t_new,
            storage_states=storage_states,
        )
        diagnostics["max_step_residual"] = max(
            diagnostics["max_step_residual"],
            float(self._last_step_residual),
        )
        for item in self._last_step_junction_debug:
            rec = dict(item)
            rec["picard_iter"] = 0
            diagnostics["junction_debug_records"].append(rec)
        for key, src in (
            ("junction_iter_clip_counts", self._last_step_junction_iter_clip_counts),
            ("junction_step_clip_counts", self._last_step_junction_step_clip_counts),
        ):
            for jname, count in src.items():
                diagnostics[key][jname] = int(diagnostics[key].get(jname, 0)) + int(count)
        if not self._last_step_converged:
            diagnostics["step_nonconvergence_count"] += 1
        diagnostics["converged"] = bool(self._last_step_converged)
        return new_states, new_storage_states, diagnostics

    def _advance_interval_adaptive(
        self,
        states: dict,
        storage_states: dict,
        t: float,
        dt: float,
        min_dt: float,
        depth: int,
        max_depth: int,
    ) -> tuple[dict, dict, dict]:
        t_new = t + dt
        trial_states, trial_storage_states, diagnostics = self._advance_interval_once(
            states,
            storage_states,
            dt,
            t_new,
        )
        should_split = (
            (not diagnostics["converged"])
            and diagnostics["max_step_residual"] > max(self.nr_tol * 100.0, 0.1)
            and dt > min_dt + 1e-10
            and depth < max_depth
        )
        if not should_split:
            return trial_states, trial_storage_states, diagnostics

        half_dt = 0.5 * dt
        first_states, first_storage_states, diag_first = self._advance_interval_adaptive(
            states,
            storage_states,
            t,
            half_dt,
            min_dt,
            depth + 1,
            max_depth,
        )
        second_states, second_storage_states, diag_second = self._advance_interval_adaptive(
            first_states,
            first_storage_states,
            t + half_dt,
            dt - half_dt,
            min_dt,
            depth + 1,
            max_depth,
        )
        split_diag = dict(diagnostics)
        split_diag["attempted_substeps"] = 0
        split_diag["substep_splits"] = 1
        split_diag["converged"] = False
        merged = self._merge_solver_diagnostics(split_diag, diag_first, diag_second)
        return second_states, second_storage_states, merged

    # ------------------------------------------------------------------
    # 完整模拟
    # ------------------------------------------------------------------

    def solve(
        self,
        states0: dict,
        t_end: float,
        dt: float,
        storage_states0: dict | None = None,
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
        storage_states = dict(storage_states0 or {})
        min_dt = min(dt, max(5.0, 0.25 * dt))
        max_substep_depth = 2

        t = float(next(iter(states.values())).t)
        out_interval = dt if output_interval is None else float(output_interval)
        next_out_t = t + out_interval

        times_out: list = [t]
        Z_hist: dict = {rname: [states[rname].Z.copy()] for rname in self.reaches}
        Q_hist: dict = {rname: [states[rname].Q.copy()] for rname in self.reaches}
        storage_hist: dict = {}
        junction_hist: dict = {}
        step_nonconvergence_count = 0
        max_step_residual = 0.0
        attempted_substeps = 0
        substep_splits = 0
        total_picard_iterations = 0
        internal_exchange_diag = self._init_internal_exchange_diagnostics()
        junction_debug_records: list = []
        junction_iter_clip_counts: dict = {}
        junction_step_clip_counts: dict = {}
        for sname, storage in self.storage_areas.items():
            stage0 = storage_states.get(sname)
            if stage0 is None:
                if storage.initial_stage is not None:
                    stage0 = float(storage.initial_stage)
                elif storage.storage_elevations is not None and len(storage.storage_elevations) > 0:
                    stage0 = float(storage.storage_elevations[0])
                else:
                    stage0 = float(storage.min_elevation or 0.0)
                storage_states[sname] = stage0
            storage_hist[sname] = [float(stage0)]
        for jname in self.junctions:
            z0 = float(self._get_junction_wse(states, jname))
            junction_hist[jname] = {
                "Z_history": [float(self._last_step_junction_states.get(jname, z0))],
                "endpoint_mean_history": [z0],
                "endpoint_spread_history": [float(self._get_junction_endpoint_spread(states, jname))],
                "source": "explicit_state" if jname in self.junction_state_names else "endpoint_mean",
            }

        while t < t_end - 1e-10:
            dt_actual = min(dt, t_end - t)
            t_new = t + dt_actual

            new_states, new_storage_states, interval_diag = self._advance_interval_adaptive(
                states,
                storage_states,
                t,
                dt_actual,
                min_dt,
                depth=0,
                max_depth=max_substep_depth,
            )
            max_step_residual = max(max_step_residual, float(interval_diag["max_step_residual"]))
            step_nonconvergence_count += int(interval_diag["step_nonconvergence_count"])
            attempted_substeps += int(interval_diag["attempted_substeps"])
            substep_splits += int(interval_diag["substep_splits"])
            total_picard_iterations += int(interval_diag["picard_iterations"])
            junction_debug_records.extend(interval_diag.get("junction_debug_records", []))
            for key, dst in (
                ("junction_iter_clip_counts", junction_iter_clip_counts),
                ("junction_step_clip_counts", junction_step_clip_counts),
            ):
                for jname, count in (interval_diag.get(key, {}) or {}).items():
                    dst[jname] = int(dst.get(jname, 0)) + int(count)
            states = new_states
            storage_states = new_storage_states
            t = t_new
            self._update_internal_exchange_diagnostics(
                internal_exchange_diag,
                states,
                storage_states,
                t,
            )

            if t >= next_out_t - 1e-10:
                times_out.append(t)
                for rname in self.reaches:
                    Z_hist[rname].append(states[rname].Z.copy())
                    Q_hist[rname].append(states[rname].Q.copy())
                for sname in self.storage_areas:
                    storage_hist[sname].append(float(storage_states[sname]))
                for jname, item in junction_hist.items():
                    endpoint_mean = float(self._get_junction_wse(states, jname))
                    z_j = float(self._last_step_junction_states.get(jname, endpoint_mean))
                    item["Z_history"].append(z_j)
                    item["endpoint_mean_history"].append(endpoint_mean)
                    item["endpoint_spread_history"].append(
                        float(self._get_junction_endpoint_spread(states, jname))
                    )
                next_out_t += out_interval

                if verbose:
                    junc_parts = []
                    for jname in self.junctions:
                        imb = self._get_junction_flow_balance(states, jname)
                        zwse = self._get_junction_wse(states, jname)
                        junc_parts.append(f"{jname}:Z={zwse:.2f},dQ={imb:.3f}")
                    print(f"  t={t:.0f}s  " + " | ".join(junc_parts))

        result = {
            rname: {
                "times": np.array(times_out),
                "Z_history": np.array(Z_hist[rname]),
                "Q_history": np.array(Q_hist[rname]),
            }
            for rname in self.reaches
        }
        if storage_hist:
            result["storage_areas"] = {
                sname: {
                    "times": np.array(times_out),
                    "Z_history": np.array(storage_hist[sname]),
                }
                for sname in storage_hist
            }
        if junction_hist:
            result["junction_states"] = {
                jname: {
                    "times": np.array(times_out),
                    "Z_history": np.array(item["Z_history"], dtype=float),
                    "endpoint_mean_history": np.array(item["endpoint_mean_history"], dtype=float),
                    "endpoint_spread_history": np.array(item["endpoint_spread_history"], dtype=float),
                    "source": item["source"],
                }
                for jname, item in junction_hist.items()
            }
        result["solver_diagnostics"] = {
            "junction_state_names": list(sorted(self.junction_state_names)),
            "step_nonconvergence_count": int(step_nonconvergence_count),
            "max_step_residual": float(max_step_residual),
            "storage_picard_enabled": bool(self.storage_areas),
            "attempted_substeps": int(attempted_substeps),
            "substep_splits": int(substep_splits),
            "total_picard_iterations": int(total_picard_iterations),
            "adaptive_min_dt": float(min_dt),
            "internal_exchange_diagnostics": {
                "storage_connections": list(internal_exchange_diag["storage_connections"].values()),
                "lateral_structures": list(internal_exchange_diag["lateral_structures"].values()),
            },
            "junction_debug_records": list(junction_debug_records),
            "junction_iter_clip_counts": dict(junction_iter_clip_counts),
            "junction_step_clip_counts": dict(junction_step_clip_counts),
        }
        return result
