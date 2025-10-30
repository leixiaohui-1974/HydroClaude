"""
Network Node Module - 管网节点模块

This module implements network node classes for pressurized pipe network analysis.

Classes:
    NetworkNode: Base class for all node types
    Junction: Flow junction node
    Reservoir: Constant head source/sink
    Tank: Variable head storage facility

Author: HydroClaude Development Team
Date: 2025-10-30
Version: 1.0.0
"""

import numpy as np
from typing import Optional, List, Dict, Literal, Tuple, Callable
from dataclasses import dataclass, field
import warnings


# Node type definitions
NodeType = Literal["junction", "reservoir", "tank"]


@dataclass
class NodeState:
    """
    节点状态类 - Node State

    用于存储节点的水力状态

    Attributes:
        head: 水头 (m)
        pressure: 压力 (m)
        demand: 当前需水量 (m³/s)
        inflow: 流入流量 (m³/s)
        outflow: 流出流量 (m³/s)
    """
    head: float = 0.0
    pressure: float = 0.0
    demand: float = 0.0
    inflow: float = 0.0
    outflow: float = 0.0

    def net_flow(self) -> float:
        """净流量 = 流入 - 流出 - 需水量"""
        return self.inflow - self.outflow - self.demand


class NetworkNode:
    """
    管网节点基类 - Base Network Node Class

    This is the base class for all network nodes. It provides common
    functionality for junctions, reservoirs, and tanks.

    节点类型:
    - Junction: 汇流节点，连接多根管道
    - Reservoir: 水库节点，恒定水头（无限容量）
    - Tank: 水箱节点，变水头（有限容量）

    Attributes:
        node_id: 节点标识符
        node_type: 节点类型
        elevation: 地面高程 (m)
        coordinates: (x, y) 坐标 (可选)
        demand: 基准需水量 (m³/s)，正值为取水，负值为入流
        demand_pattern: 需水量时变模式 (可选)
    """

    def __init__(
        self,
        node_id: str,
        node_type: NodeType,
        elevation: float,
        coordinates: Optional[Tuple[float, float]] = None,
        demand: float = 0.0,
        initial_head: Optional[float] = None,
        min_pressure: float = 0.0,
        required_pressure: float = 20.0,
        description: str = ""
    ):
        """
        初始化管网节点

        Args:
            node_id: 节点唯一标识符
            node_type: 节点类型 ('junction', 'reservoir', 'tank')
            elevation: 地面高程 (m)
            coordinates: (x, y) 平面坐标 (m)
            demand: 基准需水量 (m³/s)，正值为取水，负值为供水
            initial_head: 初始水头 (m)，用于瞬态分析
            min_pressure: 最小允许压力 (m)，用于约束检查
            required_pressure: 所需压力 (m)，用于设计标准
            description: 节点描述信息

        Raises:
            ValueError: 如果输入参数无效
        """
        # 参数验证
        if not node_id or not isinstance(node_id, str):
            raise ValueError(f"节点ID必须为非空字符串，当前值: {node_id}")

        if node_type not in ["junction", "reservoir", "tank"]:
            raise ValueError(f"节点类型无效: {node_type}，应为 'junction', 'reservoir', 或 'tank'")

        # 基本属性
        self.node_id = node_id
        self.node_type = node_type
        self.elevation = float(elevation)
        self.coordinates = coordinates
        self.description = description

        # 水力属性
        self.demand = float(demand)  # 基准需水量
        self.demand_pattern: Optional[List[float]] = None  # 时变系数
        self.current_demand = self.demand  # 当前需水量

        # 初始状态
        self.initial_head = float(initial_head) if initial_head is not None else elevation
        self.head = self.initial_head
        self.pressure = self.head - self.elevation

        # 压力约束
        self.min_pressure = float(min_pressure)
        self.required_pressure = float(required_pressure)

        # 连接管道
        self.connected_pipes: List[str] = []  # 连接的管道ID列表

        # 状态历史（用于瞬态分析）
        self.state_history: List[NodeState] = []

        # 水质属性（预留接口）
        self.quality: float = 0.0  # 水质浓度

    def add_connected_pipe(self, pipe_id: str):
        """
        添加连接的管道

        Args:
            pipe_id: 管道标识符
        """
        if pipe_id not in self.connected_pipes:
            self.connected_pipes.append(pipe_id)

    def remove_connected_pipe(self, pipe_id: str):
        """
        移除连接的管道

        Args:
            pipe_id: 管道标识符
        """
        if pipe_id in self.connected_pipes:
            self.connected_pipes.remove(pipe_id)

    def continuity_equation(
        self,
        inflows: List[float],
        outflows: List[float],
        demand: Optional[float] = None
    ) -> float:
        """
        节点连续性方程 - Node Continuity Equation

        质量守恒: ΣQ_in - ΣQ_out - Q_demand = 0

        Args:
            inflows: 流入流量列表 (m³/s)
            outflows: 流出流量列表 (m³/s)
            demand: 需水量 (m³/s)，如果为None则使用self.current_demand

        Returns:
            连续性方程残差（应接近0表示守恒）
        """
        Q_in = sum(inflows)
        Q_out = sum(outflows)
        Q_demand = demand if demand is not None else self.current_demand

        # 残差 = 流入 - 流出 - 需水量
        residual = Q_in - Q_out - Q_demand

        return residual

    def set_demand_pattern(self, pattern: List[float]):
        """
        设置需水量时变模式

        Args:
            pattern: 时变系数列表，每个值表示该时段需水量相对基准值的倍数
                    例如: [0.5, 0.8, 1.2, 1.5] 表示4个时段的倍数
        """
        if not pattern or not isinstance(pattern, (list, tuple)):
            raise ValueError("需水量模式必须为非空列表")

        if any(p < 0 for p in pattern):
            raise ValueError("需水量模式系数不能为负")

        self.demand_pattern = list(pattern)

    def get_demand_at_time(self, time_index: int) -> float:
        """
        获取指定时间的需水量

        Args:
            time_index: 时间索引（对应demand_pattern的索引）

        Returns:
            该时刻的需水量 (m³/s)
        """
        if self.demand_pattern is None:
            return self.demand

        # 循环使用模式
        pattern_length = len(self.demand_pattern)
        idx = time_index % pattern_length
        factor = self.demand_pattern[idx]

        return self.demand * factor

    def update_state(self, head: float, inflows: List[float], outflows: List[float]):
        """
        更新节点水力状态

        Args:
            head: 新的水头值 (m)
            inflows: 流入流量列表 (m³/s)
            outflows: 流出流量列表 (m³/s)
        """
        self.head = float(head)
        self.pressure = self.head - self.elevation

        # 保存状态到历史
        state = NodeState(
            head=self.head,
            pressure=self.pressure,
            demand=self.current_demand,
            inflow=sum(inflows),
            outflow=sum(outflows)
        )
        self.state_history.append(state)

    def check_pressure_constraint(self) -> Tuple[bool, str]:
        """
        检查压力约束

        Returns:
            (是否满足约束, 描述信息)
        """
        if self.pressure < self.min_pressure:
            return False, f"压力不足: {self.pressure:.2f}m < {self.min_pressure:.2f}m"

        if self.pressure < self.required_pressure:
            return True, f"压力低于设计标准: {self.pressure:.2f}m < {self.required_pressure:.2f}m"

        return True, "压力正常"

    def properties(self) -> Dict[str, float]:
        """
        获取节点所有水力属性

        Returns:
            属性字典
        """
        return {
            'node_id': self.node_id,
            'elevation': self.elevation,
            'head': self.head,
            'pressure': self.pressure,
            'demand': self.current_demand,
            'num_connections': len(self.connected_pipes)
        }

    def __repr__(self) -> str:
        return (f"NetworkNode(id='{self.node_id}', type='{self.node_type}', "
                f"elev={self.elevation:.2f}m, head={self.head:.2f}m, "
                f"p={self.pressure:.2f}m)")


class Junction(NetworkNode):
    """
    汇流节点类 - Junction Node

    汇流节点是管网中最常见的节点类型，用于连接多根管道。

    特点:
    - 水头未知，需通过管网平差求解
    - 需水量可为正（取水）、负（供水）或零
    - 满足连续性方程

    Typical usage:
        >>> junction = Junction("J1", elevation=10.0, demand=0.05)
        >>> junction.add_connected_pipe("P1")
        >>> junction.add_connected_pipe("P2")
        >>> residual = junction.continuity_equation([0.08], [0.03], 0.05)
    """

    def __init__(
        self,
        node_id: str,
        elevation: float,
        demand: float = 0.0,
        coordinates: Optional[Tuple[float, float]] = None,
        initial_head: Optional[float] = None,
        min_pressure: float = 0.0,
        required_pressure: float = 20.0,
        emitter_coefficient: float = 0.0,
        description: str = ""
    ):
        """
        初始化汇流节点

        Args:
            node_id: 节点ID
            elevation: 地面高程 (m)
            demand: 需水量 (m³/s)
            coordinates: (x, y) 坐标
            initial_head: 初始水头估计 (m)
            min_pressure: 最小允许压力 (m)
            required_pressure: 所需设计压力 (m)
            emitter_coefficient: 消防栓系数 (L/s/m^0.5)，用于模拟消防栓
            description: 描述
        """
        super().__init__(
            node_id=node_id,
            node_type="junction",
            elevation=elevation,
            coordinates=coordinates,
            demand=demand,
            initial_head=initial_head,
            min_pressure=min_pressure,
            required_pressure=required_pressure,
            description=description
        )

        # 汇流节点特有属性
        self.emitter_coefficient = float(emitter_coefficient)  # 消防栓系数

    def emitter_flow(self, pressure: Optional[float] = None) -> float:
        """
        计算消防栓出流量

        Q_emitter = C * √P

        Args:
            pressure: 压力 (m)，如果为None则使用当前压力

        Returns:
            消防栓流量 (m³/s)
        """
        if self.emitter_coefficient == 0:
            return 0.0

        p = pressure if pressure is not None else self.pressure

        if p <= 0:
            return 0.0

        # Q = C * √P，单位转换
        Q = self.emitter_coefficient * np.sqrt(p) / 1000.0  # L/s -> m³/s

        return Q

    def total_demand(self, pressure: Optional[float] = None) -> float:
        """
        总需水量（包括基准需水量和消防栓流量）

        Args:
            pressure: 压力 (m)

        Returns:
            总需水量 (m³/s)
        """
        return self.current_demand + self.emitter_flow(pressure)


class Reservoir(NetworkNode):
    """
    水库节点类 - Reservoir Node

    水库节点表示恒定水头的水源或水池，具有无限容量。

    特点:
    - 水头已知且恒定
    - 容量无限，可提供或接收任意流量
    - 常用于表示取水口、排放口

    Typical usage:
        >>> reservoir = Reservoir("R1", elevation=50.0, head=50.0)
        >>> print(reservoir.available_head())  # 50.0 m
    """

    def __init__(
        self,
        node_id: str,
        elevation: float,
        head: Optional[float] = None,
        coordinates: Optional[Tuple[float, float]] = None,
        head_pattern: Optional[List[float]] = None,
        description: str = ""
    ):
        """
        初始化水库节点

        Args:
            node_id: 节点ID
            elevation: 水库底高程 (m)
            head: 水面高程 (m)，如果为None则等于elevation
            coordinates: (x, y) 坐标
            head_pattern: 水位时变模式（用于潮汐、水库调度等）
            description: 描述
        """
        # 水库的水头已知且固定
        fixed_head = head if head is not None else elevation

        super().__init__(
            node_id=node_id,
            node_type="reservoir",
            elevation=elevation,
            coordinates=coordinates,
            demand=0.0,  # 水库无需水量
            initial_head=fixed_head,
            description=description
        )

        # 水库特有属性
        self.fixed_head = fixed_head  # 固定水头
        self.head = self.fixed_head
        self.head_pattern = head_pattern  # 时变水位模式

    def available_head(self, time_index: Optional[int] = None) -> float:
        """
        获取可用水头

        Args:
            time_index: 时间索引（用于时变水位）

        Returns:
            水头 (m)
        """
        if self.head_pattern is None or time_index is None:
            return self.fixed_head

        # 循环使用时变模式
        pattern_length = len(self.head_pattern)
        idx = time_index % pattern_length

        return self.fixed_head + self.head_pattern[idx]

    def set_head(self, head: float):
        """
        设置水库水位（用于手动调整或优化）

        Args:
            head: 新的水头 (m)
        """
        self.fixed_head = float(head)
        self.head = self.fixed_head
        self.pressure = self.head - self.elevation


class Tank(NetworkNode):
    """
    水箱节点类 - Tank Node

    水箱节点表示有限容量的储水设施，水位随进出流量变化。

    特点:
    - 水头随时间变化（根据进出流量）
    - 有限容量（有最小和最大水位）
    - 常用于调蓄、稳压

    几何形状:
    - Cylindrical: 圆柱形 (默认)
    - Prismatic: 棱柱形

    Typical usage:
        >>> tank = Tank("T1", elevation=30.0, diameter=10.0,
        ...             min_level=0.0, max_level=5.0, initial_level=3.0)
        >>> tank.update_volume(dt=60.0, net_inflow=0.1)  # 1分钟，净流入0.1 m³/s
    """

    def __init__(
        self,
        node_id: str,
        elevation: float,
        diameter: float,
        min_level: float = 0.0,
        max_level: float = 10.0,
        initial_level: float = 5.0,
        coordinates: Optional[Tuple[float, float]] = None,
        geometry: Literal["cylindrical", "prismatic"] = "cylindrical",
        area_curve: Optional[List[Tuple[float, float]]] = None,
        description: str = ""
    ):
        """
        初始化水箱节点

        Args:
            node_id: 节点ID
            elevation: 水箱底部高程 (m)
            diameter: 直径 (m)，用于圆柱形水箱
            min_level: 最低水位 (m，相对于底部)
            max_level: 最高水位 (m，相对于底部)
            initial_level: 初始水位 (m，相对于底部)
            coordinates: (x, y) 坐标
            geometry: 几何形状 ('cylindrical' 或 'prismatic')
            area_curve: 面积曲线 [(level, area), ...]，用于非规则形状
            description: 描述

        Raises:
            ValueError: 如果水位参数不合理
        """
        # 参数验证
        if diameter <= 0:
            raise ValueError(f"水箱直径必须 > 0，当前值: {diameter}")

        if not (min_level <= initial_level <= max_level):
            raise ValueError(
                f"初始水位 {initial_level}m 必须在 [{min_level}, {max_level}]m 范围内"
            )

        # 初始水头 = 底部高程 + 初始水位
        initial_head = elevation + initial_level

        super().__init__(
            node_id=node_id,
            node_type="tank",
            elevation=elevation,
            coordinates=coordinates,
            demand=0.0,  # 水箱无直接需水量
            initial_head=initial_head,
            description=description
        )

        # 水箱几何属性
        self.diameter = float(diameter)
        self.min_level = float(min_level)
        self.max_level = float(max_level)
        self.geometry = geometry
        self.area_curve = area_curve

        # 计算底面积
        if geometry == "cylindrical":
            self.base_area = np.pi * (self.diameter / 2.0) ** 2
        else:  # prismatic
            # 棱柱形假设为正方形
            self.base_area = self.diameter ** 2

        # 水位状态
        self.level = float(initial_level)  # 当前水位（相对于底部）
        self.head = self.elevation + self.level  # 绝对水头
        self.volume = self._calculate_volume(self.level)  # 当前容量
        self.max_volume = self._calculate_volume(self.max_level)
        self.min_volume = self._calculate_volume(self.min_level)

    def _calculate_volume(self, level: float) -> float:
        """
        计算指定水位下的水体积

        Args:
            level: 水位 (m，相对于底部)

        Returns:
            体积 (m³)
        """
        if level <= 0:
            return 0.0

        if self.area_curve is not None:
            # 使用面积曲线积分计算体积
            volume = 0.0
            sorted_curve = sorted(self.area_curve, key=lambda x: x[0])

            for i in range(len(sorted_curve) - 1):
                h1, A1 = sorted_curve[i]
                h2, A2 = sorted_curve[i + 1]

                if level < h1:
                    break

                dh = min(h2, level) - h1
                if dh > 0:
                    # 梯形积分
                    dV = 0.5 * (A1 + A2) * dh
                    volume += dV

                if level <= h2:
                    break

            return volume
        else:
            # 简单几何形状
            return self.base_area * level

    def area_at_level(self, level: float) -> float:
        """
        计算指定水位的水面面积

        Args:
            level: 水位 (m)

        Returns:
            面积 (m²)
        """
        if self.area_curve is not None:
            # 插值查找面积
            sorted_curve = sorted(self.area_curve, key=lambda x: x[0])

            for i in range(len(sorted_curve) - 1):
                h1, A1 = sorted_curve[i]
                h2, A2 = sorted_curve[i + 1]

                if h1 <= level <= h2:
                    # 线性插值
                    t = (level - h1) / (h2 - h1) if h2 > h1 else 0.0
                    return A1 + t * (A2 - A1)

            # 超出范围，使用最近值
            if level < sorted_curve[0][0]:
                return sorted_curve[0][1]
            else:
                return sorted_curve[-1][1]
        else:
            return self.base_area

    def update_volume(self, dt: float, net_inflow: float) -> float:
        """
        更新水箱水位和体积（时间推进）

        dV/dt = Q_in - Q_out
        V(t+dt) = V(t) + (Q_in - Q_out) * dt

        Args:
            dt: 时间步长 (s)
            net_inflow: 净流入量 (m³/s) = Q_in - Q_out

        Returns:
            新的水位 (m)

        Raises:
            RuntimeWarning: 如果水位超出范围
        """
        # 计算体积变化
        dV = net_inflow * dt
        new_volume = self.volume + dV

        # 检查容量约束
        if new_volume < self.min_volume:
            warnings.warn(
                f"水箱 {self.node_id} 水位过低: {new_volume:.2f}m³ < {self.min_volume:.2f}m³"
            )
            new_volume = self.min_volume

        if new_volume > self.max_volume:
            warnings.warn(
                f"水箱 {self.node_id} 水位过高: {new_volume:.2f}m³ > {self.max_volume:.2f}m³"
            )
            new_volume = self.max_volume

        # 反算水位（迭代法，因为area_curve可能非线性）
        # 简化处理：对于规则形状直接计算
        if self.area_curve is None:
            new_level = new_volume / self.base_area
        else:
            # 对于复杂形状，使用二分法反算
            new_level = self._inverse_volume(new_volume)

        # 更新状态
        self.volume = new_volume
        self.level = new_level
        self.head = self.elevation + self.level
        self.pressure = self.level  # 水箱内的压力 = 水深

        return self.level

    def _inverse_volume(self, target_volume: float, tol: float = 1e-3) -> float:
        """
        根据体积反算水位（二分法）

        Args:
            target_volume: 目标体积 (m³)
            tol: 收敛容差 (m)

        Returns:
            水位 (m)
        """
        level_low = self.min_level
        level_high = self.max_level

        for _ in range(50):
            level_mid = 0.5 * (level_low + level_high)
            volume_mid = self._calculate_volume(level_mid)

            if abs(volume_mid - target_volume) < tol:
                return level_mid

            if volume_mid < target_volume:
                level_low = level_mid
            else:
                level_high = level_mid

        # 如果未收敛，返回中间值
        return 0.5 * (level_low + level_high)

    def is_full(self) -> bool:
        """检查水箱是否已满"""
        return self.level >= self.max_level - 0.01  # 1cm容差

    def is_empty(self) -> bool:
        """检查水箱是否已空"""
        return self.level <= self.min_level + 0.01  # 1cm容差

    def fill_percentage(self) -> float:
        """
        计算充水率

        Returns:
            充水率 (0-100%)
        """
        if self.max_level <= self.min_level:
            return 100.0

        fill_ratio = (self.level - self.min_level) / (self.max_level - self.min_level)
        return fill_ratio * 100.0


# 便捷构造函数
def create_junction(
    node_id: str,
    elevation: float,
    demand: float = 0.0,
    **kwargs
) -> Junction:
    """
    便捷创建汇流节点

    Args:
        node_id: 节点ID
        elevation: 地面高程 (m)
        demand: 需水量 (m³/s)
        **kwargs: 其他参数

    Returns:
        Junction实例
    """
    return Junction(node_id=node_id, elevation=elevation, demand=demand, **kwargs)


def create_reservoir(
    node_id: str,
    elevation: float,
    head: Optional[float] = None,
    **kwargs
) -> Reservoir:
    """
    便捷创建水库节点

    Args:
        node_id: 节点ID
        elevation: 水库底高程 (m)
        head: 水面高程 (m)
        **kwargs: 其他参数

    Returns:
        Reservoir实例
    """
    return Reservoir(node_id=node_id, elevation=elevation, head=head, **kwargs)


def create_tank(
    node_id: str,
    elevation: float,
    diameter: float,
    initial_level: float,
    max_level: float,
    **kwargs
) -> Tank:
    """
    便捷创建水箱节点

    Args:
        node_id: 节点ID
        elevation: 水箱底高程 (m)
        diameter: 直径 (m)
        initial_level: 初始水位 (m)
        max_level: 最大水位 (m)
        **kwargs: 其他参数

    Returns:
        Tank实例
    """
    return Tank(
        node_id=node_id,
        elevation=elevation,
        diameter=diameter,
        initial_level=initial_level,
        max_level=max_level,
        **kwargs
    )
