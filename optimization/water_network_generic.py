"""
通用水网优化调度 Pyomo 模型模板。

功能要点：
1. 支持节点-边任意拓扑的质量守恒；
2. 节点状态区分角色（storage / level / auxiliary），仅 storage 状态参与蓄量平衡；
3. 支持线性容量约束、节点缺水松弛与惩罚系数；
4. 泵/闸的分段效率曲线以线性增量方式建模；
5. 目标函数最小化能耗与缺水惩罚，可按需扩展情景覆盖。
"""

from __future__ import annotations

import copy
import warnings
from typing import Dict, Iterable, List, Optional, Tuple, TYPE_CHECKING

from pyomo.environ import (
    ConcreteModel,
    Constraint,
    Expression,
    NonNegativeReals,
    Objective,
    Param,
    Reals,
    Set,
    Var,
    minimize,
)

if TYPE_CHECKING:
    from water_network_schema import EdgeSpec, NetworkConfig, NodeSpec, SeriesSpec

# 导入异常类和验证函数
try:
    from .exceptions import ConfigurationError, TimeSeriesError, ValidationError
    from .validation import validate_network_config
    from .defaults import OPTIMIZATION_DEFAULTS
    from .feasibility import check_solver_results
except ImportError:
    # 如果无法导入，定义简单版本
    class ConfigurationError(Exception):
        pass

    class TimeSeriesError(Exception):
        pass

    class ValidationError(Exception):
        pass

    def validate_network_config(config):
        pass  # 降级处理

    # 如果无法导入defaults，使用硬编码值
    class _OptimizationDefaults:
        shortage_penalty = 1e5
        pump_cost = 200.0
        idz_slack_penalty = 1e6

    OPTIMIZATION_DEFAULTS = _OptimizationDefaults()


def _resolve_time_index(network_cfg: "NetworkConfig") -> List[str]:
    horizon = network_cfg.get("horizon", {}) or {}
    periods = horizon.get("periods")
    if isinstance(periods, list) and periods:
        return [str(p) for p in periods]
    if isinstance(periods, str):
        return [p.strip() for p in periods.split(",") if p.strip()]

    for series in network_cfg.get("series", {}).values():
        times = series.get("times", [])
        if times:
            return [str(t) for t in times]

    raise ValueError("时间索引缺失：请在 horizon.periods 或任一时间序列中提供 times。")


def _series_to_map(series: "SeriesSpec", time_index: Iterable[str]) -> Dict[str, float]:
    values = series.get("values", [])
    default_value = series.get("default", 0.0)
    data: Dict[str, float] = {}
    for idx, t in enumerate(time_index):
        if idx < len(values):
            data[t] = float(values[idx])
        else:
            data[t] = float(default_value)
    return data


def _apply_overrides(base_cfg: Dict, overrides: Dict) -> Dict:
    result = copy.deepcopy(base_cfg)
    for key, value in overrides.items():
        if key in result and isinstance(result[key], dict) and isinstance(value, dict):
            result[key] = _apply_overrides(result[key], value)
        else:
            result[key] = copy.deepcopy(value)
    return result


def _collect_edges(edges: List["EdgeSpec"]) -> Tuple[Dict[str, str], Dict[str, str]]:
    from_map: Dict[str, str] = {}
    to_map: Dict[str, str] = {}
    for edge in edges:
        edge_id = edge["id"]
        from_map[edge_id] = edge["from_node"]
        to_map[edge_id] = edge["to_node"]
    return from_map, to_map


def _build_piecewise_segments(edges: List["EdgeSpec"]) -> Tuple[
    Dict[str, List[int]],
    Dict[Tuple[str, int], float],
    Dict[Tuple[str, int], float],
]:
    """
    根据边的效率曲线生成分段容量与成本信息。

    默认假设 efficiency_curve = ([流量断点], [分段成本或效率])：
    - 若第二个列表长度与断点数相同，取相邻区间的前一项；
    - 若长度为断点数-1，则直接对应每个区间；
    - 区间容量 = 上下断点差值。
    """

    piecewise_edges: Dict[str, List[int]] = {}
    segment_capacity: Dict[Tuple[str, int], float] = {}
    segment_cost: Dict[Tuple[str, int], float] = {}

    for edge in edges:
        attr = edge.get("attributes", {}) or {}
        curve = attr.get("efficiency_curve")
        if not curve:
            continue
        flow_points, cost_points = curve
        if not flow_points or len(flow_points) < 2:
            continue

        flows = [float(f) for f in flow_points]
        if len(cost_points) >= len(flows):
            costs = [float(cost_points[i]) for i in range(len(flows))]
        else:
            costs = [float(cost_points[min(i, len(cost_points) - 1)]) for i in range(len(flows))]

        pairs = sorted(zip(flows, costs), key=lambda x: x[0])
        sorted_flows = [p[0] for p in pairs]
        sorted_costs = [p[1] for p in pairs]

        segments = []
        for idx in range(len(sorted_flows) - 1):
            lower = sorted_flows[idx]
            upper = sorted_flows[idx + 1]
            cap = max(0.0, upper - lower)
            if cap <= 0:
                continue
            seg_cost = sorted_costs[idx]
            segments.append((cap, seg_cost))

        if not segments:
            continue

        edge_id = edge["id"]
        piecewise_edges[edge_id] = list(range(len(segments)))
        for seg_idx, (cap, seg_cost) in enumerate(segments):
            segment_capacity[(edge_id, seg_idx)] = cap
            segment_cost[(edge_id, seg_idx)] = seg_cost

    return piecewise_edges, segment_capacity, segment_cost


def build_water_network_model(
    network_cfg: "NetworkConfig",
    *,
    scenario_overrides: Optional[Dict] = None,
    validate: bool = True,
) -> ConcreteModel:
    """
    根据网络配置构建 Pyomo 模型。

    Args:
        network_cfg: 网络配置字典
        scenario_overrides: 情景覆盖配置
        validate: 是否进行配置验证（默认True）

    Returns:
        ConcreteModel: 构建的Pyomo优化模型

    Raises:
        ConfigurationError: 配置错误
        ValidationError: 验证失败
        TimeSeriesError: 时间序列错误
    """

    cfg = _apply_overrides(network_cfg, scenario_overrides or {})

    # 验证配置
    if validate:
        try:
            validate_network_config(cfg)
        except Exception as e:
            # 捕获并重新抛出更详细的错误
            raise type(e)(f"配置验证失败: {str(e)}") from e
    time_index = _resolve_time_index(cfg)
    nodes: List["NodeSpec"] = cfg.get("nodes", [])
    edges: List["EdgeSpec"] = cfg.get("edges", [])
    series_lib: Dict[str, "SeriesSpec"] = cfg.get("series", {})
    weights = cfg.get("objective_weights", {})

    piecewise_segments, segment_capacity, segment_cost = _build_piecewise_segments(edges)

    model = ConcreteModel(name="GenericWaterNetwork")

    # 集合
    model.T = Set(initialize=time_index, ordered=True, doc="调度时间序列")
    node_ids = [node["id"] for node in nodes]
    edge_ids = [edge["id"] for edge in edges]
    model.N = Set(initialize=node_ids, doc="网络节点集合")
    model.E = Set(initialize=edge_ids, doc="网络边集合")

    from_map, to_map = _collect_edges(edges)
    incoming = {n: [e for e in edge_ids if to_map[e] == n] for n in node_ids}
    outgoing = {n: [e for e in edge_ids if from_map[e] == n] for n in node_ids}
    prev_time = {t: time_index[i - 1] if i > 0 else None for i, t in enumerate(time_index)}

    # 边容量和曲线映射
    edge_capacity_map: Dict[str, float] = {}
    for edge in edges:
        attr = edge.get("attributes", {}) or {}
        capacity = attr.get("capacity")
        if capacity is not None:
            edge_capacity_map[edge["id"]] = float(capacity)

    sos2_curves: Dict[str, object] = {}  # 预留SOS2曲线支持

    # 时间序列参数
    inflow_data: Dict[Tuple[str, str], float] = {}
    demand_data: Dict[Tuple[str, str], float] = {}

    shortage_nodes: set[str] = set()
    shortage_penalty_map: Dict[str, float] = {}

    state_specs: Dict[Tuple[str, str], Dict] = {}
    state_initial: Dict[Tuple[str, str], float] = {}
    state_bounds: Dict[Tuple[str, str], Tuple[Optional[float], Optional[float]]] = {}
    storage_state_map: Dict[str, Tuple[str, str]] = {}
    state_piecewise_relations: List[Tuple] = []  # 状态分段线性关系列表

    for node in nodes:
        node_id = node["id"]
        attr = node.get("attributes", {}) or {}
        misc = attr.get("misc", {}) if isinstance(attr, dict) else {}

        inflow_key = misc.get("inflow_series")
        if inflow_key:
            inflow_series = _series_to_map(series_lib[inflow_key], time_index)
            for t in time_index:
                inflow_data[(node_id, t)] = inflow_series[t]

        demand_key = attr.get("demand_profile") or misc.get("demand_series")
        if demand_key:
            demand_series = _series_to_map(series_lib[demand_key], time_index)
            for t in time_index:
                demand_data[(node_id, t)] = demand_series[t]
            shortage_nodes.add(node_id)
            penalty = attr.get("shortage_penalty", misc.get("shortage_penalty", 1.0))
            shortage_penalty_map[node_id] = float(penalty)

        states = node.get("states", {}) or {}
        for state_name, state_spec in states.items():
            key = (node_id, state_name)
            state_specs[key] = state_spec
            state_initial[key] = state_spec.get("initial", 0.0)
            bounds = state_spec.get("bounds")
            if bounds:
                state_bounds[key] = bounds
            role = state_spec.get("role", "storage")
            if role == "storage" and node_id not in storage_state_map:
                storage_state_map[node_id] = key

    for n in shortage_nodes:
        shortage_penalty_map.setdefault(n, 1.0)

    def _param_init_inflow(m, n, t):
        return inflow_data.get((n, t), 0.0)

    def _param_init_demand(m, n, t):
        return demand_data.get((n, t), 0.0)

    model.inflow = Param(model.N, model.T, initialize=_param_init_inflow, mutable=True, doc="节点外源入流")
    model.demand = Param(model.N, model.T, initialize=_param_init_demand, mutable=True, doc="节点需求")

    # 变量
    def _flow_bounds(m, e, t):
        cap = edge_capacity_map.get(e)
        if cap is not None:
            return (0.0, float(cap))
        curve = sos2_curves.get(e)
        if curve:
            return (0.0, float(curve.breakpoints[-1]))
        return (0.0, None)

    model.flow = Var(
        model.E,
        model.T,
        bounds=_flow_bounds,
        within=NonNegativeReals,
        doc="节点流量变量",
    )

    state_index = list(state_specs.keys())
    if state_index:
        model.state_index = Set(initialize=state_index, doc="节点-状态组合")

        def _state_bounds(m, node_id, state_name, t):
            return state_bounds.get((node_id, state_name), (None, None))

        model.state = Var(
            model.state_index,
            model.T,
            domain=Reals,
            bounds=_state_bounds,
            doc="节点状态变量",
        )
    else:
        model.state_index = Set(initialize=[], doc="空状态集合")

    if state_piecewise_relations:
        model.state_piecewise = Block(
            range(len(state_piecewise_relations)),
            doc="state piecewise relations",
        )
        for idx, (target_key, driver_key, breakpoints, values, label) in enumerate(
            state_piecewise_relations
        ):
            blk = model.state_piecewise[idx]
            blk.label = label
            for t in time_index:
                blk.add_component(
                    f"pw_{t}",
                    Piecewise(
                        model.state[target_key, t],
                        model.state[driver_key, t],
                        pw_pts=breakpoints,
                        f_rule=values,
                        pw_repn="SOS2",
                        pw_constr_type="EQ",
                        warn_domain_coverage=False,
                    ),
                )

    if shortage_nodes:
        model.shortage_nodes = Set(initialize=list(shortage_nodes), doc="允许缺水的节点")
        model.shortage = Var(
            model.shortage_nodes,
            model.T,
            within=NonNegativeReals,
            doc="缺水松弛变量",
        )
        model.shortage_penalty_factor = Param(
            model.shortage_nodes,
            initialize=lambda m, n: shortage_penalty_map.get(n, 1.0),
            mutable=True,
            doc="节点缺水惩罚系数",
        )
    else:
        model.shortage_nodes = Set(initialize=[], doc="无缺水节点")

    if piecewise_segments:
        model.pw_edges = Set(
            initialize=list(piecewise_segments.keys()),
            ordered=True,
            doc="采用分段效率的边",
        )
        model.pw_segments = Set(
            model.pw_edges,
            initialize=lambda m, e: piecewise_segments[e],
            ordered=True,
            doc="分段索引",
        )

        # 创建分段索引集合（边, 分段）
        segment_index = [(e, s) for e in piecewise_segments.keys() for s in piecewise_segments[e]]
        model.segment_index = Set(initialize=segment_index, dimen=2, doc="分段索引")

        model.segment_flow = Var(
            model.segment_index,
            model.T,
            within=NonNegativeReals,
            doc="分段流量变量",
        )
    else:
        model.pw_edges = Set(initialize=[], doc="无分段效率边")
        model.pw_segments = Set(initialize=[], doc="空分段集合")
        model.segment_index = Set(initialize=[], dimen=3, doc="empty segment index")

    # 约束
    def mass_balance_rule(m, n, t):
        inflow_sum = sum(m.flow[e, t] for e in incoming[n]) + m.inflow[n, t]
        outflow_sum = sum(m.flow[e, t] for e in outgoing[n]) + m.demand[n, t]

        shortage_term = 0.0
        if n in shortage_nodes:
            shortage_term = m.shortage[n, t]

        state_key = storage_state_map.get(n)
        if state_key:
            prev_t = prev_time[t]
            if prev_t is None:
                initial_value = state_initial.get(state_key, 0.0)
                return m.state[state_key, t] == initial_value + inflow_sum + shortage_term - outflow_sum
            return m.state[state_key, t] == m.state[state_key, prev_t] + inflow_sum + shortage_term - outflow_sum

        return inflow_sum + shortage_term == outflow_sum

    model.mass_balance = Constraint(model.N, model.T, rule=mass_balance_rule, doc="节点质量守恒")

    def capacity_rule(m, e, t):
        cap = edge_capacity_map.get(e)
        if cap is None:
            return Constraint.Skip
        return m.flow[e, t] <= cap

    model.flow_capacity = Constraint(model.E, model.T, rule=capacity_rule, doc="边容量约束")

    if piecewise_segments:
        def segment_capacity_rule(m, e, s, t):
            cap = segment_capacity.get((e, s))
            if cap is None:
                return Constraint.Skip
            return m.segment_flow[(e, s), t] <= cap

        model.segment_capacity_limit = Constraint(
            model.segment_index,
            model.T,
            rule=segment_capacity_rule,
            doc="segment capacity limit",
        )

        def segment_flow_sum_rule(m, e, t):
            if e not in piecewise_segments:
                return Constraint.Skip
            return sum(m.segment_flow[(e, s), t] for s in piecewise_segments[e]) == m.flow[e, t]

        model.segment_flow_sum = Constraint(
            model.E,
            model.T,
            rule=segment_flow_sum_rule,
            doc="segment flow consistency",
        )

    # 目标函数
    pump_cost_weight = float(weights.get("pumping_cost", OPTIMIZATION_DEFAULTS.pump_cost))
    shortage_weight = float(weights.get("shortage_penalty", OPTIMIZATION_DEFAULTS.shortage_penalty))

    edge_energy_cost = {
        edge["id"]: edge.get("attributes", {}).get("energy_cost", 0.0)
        for edge in edges
    }
    edges_with_piecewise = set(piecewise_segments.keys())

    def energy_expr(m):
        linear_part = sum(
            edge_energy_cost[e] * m.flow[e, t]
            for e in model.E
            for t in model.T
            if e not in edges_with_piecewise
        )
        if not piecewise_segments:
            return linear_part
        piecewise_part = sum(
            segment_cost[(e, s)] * m.segment_flow[(e, s), t]
            for e in model.pw_edges
            for s in model.pw_segments[e]
            for t in model.T
        )
        return linear_part + piecewise_part

    def shortage_volume_expr(m):
        if not shortage_nodes:
            return 0.0
        return sum(m.shortage[n, t] for n in model.shortage_nodes for t in model.T)

    def shortage_penalty_expr(m):
        if not shortage_nodes:
            return 0.0
        return sum(
            m.shortage_penalty_factor[n] * m.shortage[n, t]
            for n in model.shortage_nodes
            for t in model.T
        )

    model.total_energy_cost = Expression(rule=energy_expr, doc="能耗成本")
    model.total_shortage_volume = Expression(rule=shortage_volume_expr, doc="缺水体积")
    model.total_shortage_penalty = Expression(rule=shortage_penalty_expr, doc="缺水罚值")

    model.obj = Objective(
        expr=pump_cost_weight * model.total_energy_cost + shortage_weight * model.total_shortage_penalty,
        sense=minimize,
        doc="最小化能耗与缺水罚值",
    )

    return model


__all__ = ["build_water_network_model"]

