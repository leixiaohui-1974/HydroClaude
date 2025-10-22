"""
配置验证模块：验证网络配置的完整性和正确性
"""
from typing import Dict, List, Set, Optional, Any
from .exceptions import (
    ConfigurationError,
    ValidationError,
    TopologyError,
    TimeSeriesError,
    DataError,
)


def validate_network_config(config: Dict[str, Any]) -> None:
    """
    验证网络配置的完整性和正确性

    Args:
        config: 网络配置字典

    Raises:
        ConfigurationError: 配置缺失或格式错误
        ValidationError: 验证失败
        TopologyError: 拓扑错误
        TimeSeriesError: 时间序列错误
    """
    _validate_basic_structure(config)
    _validate_time_horizon(config)
    _validate_nodes(config)
    _validate_edges(config)
    _validate_topology(config)
    _validate_time_series(config)
    _validate_objective_weights(config)


def _validate_basic_structure(config: Dict[str, Any]) -> None:
    """验证基本结构"""
    required_keys = ["horizon", "nodes", "edges"]
    missing = [key for key in required_keys if key not in config]

    if missing:
        raise ConfigurationError(
            f"配置缺少必需字段: {', '.join(missing)}"
        )

    if not isinstance(config.get("nodes"), list):
        raise ConfigurationError("'nodes' 必须是列表类型")

    if not isinstance(config.get("edges"), list):
        raise ConfigurationError("'edges' 必须是列表类型")


def _validate_time_horizon(config: Dict[str, Any]) -> None:
    """验证时间范围"""
    horizon = config.get("horizon", {})

    if not isinstance(horizon, dict):
        raise ConfigurationError("'horizon' 必须是字典类型")

    # 检查时间周期定义
    periods = horizon.get("periods")
    if periods is None:
        # 尝试从series中获取
        series = config.get("series", {})
        if not series:
            raise TimeSeriesError(
                "未定义时间周期：请在 horizon.periods 或任一时间序列中提供 times"
            )
        # 检查是否有时间序列包含times
        has_times = any("times" in s for s in series.values() if isinstance(s, dict))
        if not has_times:
            raise TimeSeriesError("未找到时间序列定义")
    elif isinstance(periods, list):
        if len(periods) == 0:
            raise TimeSeriesError("时间周期列表不能为空")
        # 检查重复
        if len(periods) != len(set(map(str, periods))):
            raise TimeSeriesError("时间周期包含重复值")
    elif not isinstance(periods, str):
        raise ConfigurationError("horizon.periods 必须是列表或字符串")


def _validate_nodes(config: Dict[str, Any]) -> None:
    """验证节点配置"""
    nodes = config.get("nodes", [])

    if len(nodes) == 0:
        raise ValidationError("网络至少需要一个节点")

    node_ids = set()
    valid_kinds = {
        "reservoir",
        "junction",
        "demand",
        "source",
        "sink",
        "pump_station",
        "gate",
        "hydropower",
        "storage_pool",
    }

    for idx, node in enumerate(nodes):
        if not isinstance(node, dict):
            raise ConfigurationError(f"节点 #{idx} 必须是字典类型")

        # 检查必需字段
        if "id" not in node:
            raise ConfigurationError(f"节点 #{idx} 缺少 'id' 字段")

        node_id = node["id"]

        # 检查ID唯一性
        if node_id in node_ids:
            raise ValidationError(f"节点ID重复: {node_id}")
        node_ids.add(node_id)

        # 检查节点类型
        kind = node.get("kind")
        if kind and kind not in valid_kinds:
            raise ValidationError(
                f"节点 '{node_id}' 的类型 '{kind}' 无效。"
                f"有效类型: {', '.join(sorted(valid_kinds))}"
            )

        # 验证状态定义
        states = node.get("states", {})
        if states and not isinstance(states, dict):
            raise ConfigurationError(f"节点 '{node_id}' 的 states 必须是字典")

        for state_name, state_spec in states.items():
            if not isinstance(state_spec, dict):
                raise ConfigurationError(
                    f"节点 '{node_id}' 的状态 '{state_name}' 配置必须是字典"
                )

            # 检查role
            role = state_spec.get("role")
            if role and role not in ("storage", "level", "auxiliary"):
                raise ValidationError(
                    f"节点 '{node_id}' 状态 '{state_name}' 的角色 '{role}' 无效"
                )

            # 检查bounds
            bounds = state_spec.get("bounds")
            if bounds is not None:
                if not isinstance(bounds, (list, tuple)) or len(bounds) != 2:
                    raise ValidationError(
                        f"节点 '{node_id}' 状态 '{state_name}' 的 bounds 必须是长度为2的元组"
                    )
                lower, upper = bounds
                if (
                    lower is not None
                    and upper is not None
                    and float(lower) > float(upper)
                ):
                    raise ValidationError(
                        f"节点 '{node_id}' 状态 '{state_name}' 的下界 {lower} 大于上界 {upper}"
                    )


def _validate_edges(config: Dict[str, Any]) -> None:
    """验证边配置"""
    edges = config.get("edges", [])
    nodes = config.get("nodes", [])
    node_ids = {node["id"] for node in nodes}

    edge_ids = set()
    valid_kinds = {
        "open_channel",
        "pipeline",
        "pump",
        "gate_flow",
        "turbine",
        "spillway",
        "gravity",
    }

    for idx, edge in enumerate(edges):
        if not isinstance(edge, dict):
            raise ConfigurationError(f"边 #{idx} 必须是字典类型")

        # 检查必需字段
        if "id" not in edge:
            raise ConfigurationError(f"边 #{idx} 缺少 'id' 字段")

        edge_id = edge["id"]

        # 检查ID唯一性
        if edge_id in edge_ids:
            raise ValidationError(f"边ID重复: {edge_id}")
        edge_ids.add(edge_id)

        # 检查from_node和to_node
        if "from_node" not in edge:
            raise ConfigurationError(f"边 '{edge_id}' 缺少 'from_node' 字段")
        if "to_node" not in edge:
            raise ConfigurationError(f"边 '{edge_id}' 缺少 'to_node' 字段")

        from_node = edge["from_node"]
        to_node = edge["to_node"]

        if from_node not in node_ids:
            raise TopologyError(f"边 '{edge_id}' 的起点 '{from_node}' 不存在")
        if to_node not in node_ids:
            raise TopologyError(f"边 '{edge_id}' 的终点 '{to_node}' 不存在")

        # 检查边类型
        kind = edge.get("kind")
        if kind and kind not in valid_kinds:
            raise ValidationError(
                f"边 '{edge_id}' 的类型 '{kind}' 无效。"
                f"有效类型: {', '.join(sorted(valid_kinds))}"
            )

        # 验证属性
        attributes = edge.get("attributes", {})
        if attributes and not isinstance(attributes, dict):
            raise ConfigurationError(f"边 '{edge_id}' 的 attributes 必须是字典")

        # 检查capacity
        capacity = attributes.get("capacity")
        if capacity is not None and float(capacity) < 0:
            raise ValidationError(
                f"边 '{edge_id}' 的容量 {capacity} 不能为负"
            )

        # 检查efficiency_curve
        curve = attributes.get("efficiency_curve")
        if curve is not None:
            if not isinstance(curve, (list, tuple)) or len(curve) != 2:
                raise ValidationError(
                    f"边 '{edge_id}' 的 efficiency_curve 必须是长度为2的元组"
                )
            breakpoints, values = curve
            if not isinstance(breakpoints, (list, tuple)) or not isinstance(
                values, (list, tuple)
            ):
                raise ValidationError(
                    f"边 '{edge_id}' 的 efficiency_curve 中的断点和值必须是列表"
                )
            if len(breakpoints) < 2:
                raise ValidationError(
                    f"边 '{edge_id}' 的 efficiency_curve 至少需要2个断点"
                )
            if len(values) == 0:
                raise ValidationError(
                    f"边 '{edge_id}' 的 efficiency_curve 值列表不能为空"
                )


def _validate_topology(config: Dict[str, Any]) -> None:
    """验证拓扑结构（检测孤立节点等）"""
    nodes = config.get("nodes", [])
    edges = config.get("edges", [])

    if len(nodes) == 0:
        return

    node_ids = {node["id"] for node in nodes}
    connected_nodes = set()

    for edge in edges:
        connected_nodes.add(edge["from_node"])
        connected_nodes.add(edge["to_node"])

    # 检测孤立节点（警告而非错误）
    isolated = node_ids - connected_nodes
    if isolated and len(edges) > 0:
        # 只在有边的情况下检查孤立节点
        import warnings

        warnings.warn(
            f"检测到孤立节点（未连接任何边）: {', '.join(sorted(isolated))}"
        )


def _validate_time_series(config: Dict[str, Any]) -> None:
    """验证时间序列"""
    series = config.get("series", {})
    if not series:
        return

    if not isinstance(series, dict):
        raise ConfigurationError("'series' 必须是字典类型")

    for series_id, series_spec in series.items():
        if not isinstance(series_spec, dict):
            raise ConfigurationError(
                f"时间序列 '{series_id}' 配置必须是字典"
            )

        # 检查values
        values = series_spec.get("values")
        if values is not None:
            if not isinstance(values, (list, tuple)):
                raise TimeSeriesError(
                    f"时间序列 '{series_id}' 的 values 必须是列表"
                )
            if len(values) == 0:
                raise TimeSeriesError(
                    f"时间序列 '{series_id}' 的 values 不能为空"
                )

        # 检查times
        times = series_spec.get("times")
        if times is not None:
            if not isinstance(times, (list, tuple)):
                raise TimeSeriesError(
                    f"时间序列 '{series_id}' 的 times 必须是列表"
                )
            if values and len(times) > 0 and len(values) > len(times):
                raise TimeSeriesError(
                    f"时间序列 '{series_id}' 的 values 长度 ({len(values)}) "
                    f"超过 times 长度 ({len(times)})"
                )


def _validate_objective_weights(config: Dict[str, Any]) -> None:
    """验证目标函数权重"""
    weights = config.get("objective_weights", {})
    if not weights:
        return

    if not isinstance(weights, dict):
        raise ConfigurationError("'objective_weights' 必须是字典类型")

    valid_weights = {
        "energy_revenue",
        "pumping_cost",
        "shortage_penalty",
        "flood_risk",
        "ecological",
        "navigation",
    }

    for weight_name, weight_value in weights.items():
        if weight_name not in valid_weights:
            import warnings

            warnings.warn(
                f"未知的权重名称: {weight_name}。"
                f"有效权重: {', '.join(sorted(valid_weights))}"
            )

        try:
            float(weight_value)
        except (TypeError, ValueError):
            raise ValidationError(
                f"权重 '{weight_name}' 的值 '{weight_value}' 不是有效数字"
            )
