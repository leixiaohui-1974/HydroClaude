"""
节点类型实现

实现各种专业化的节点类型：
- JunctionNode: 汇流节点（多条河段汇入一点）
- BifurcationNode: 分流节点（一条河段分为多条）
- ReservoirNode: 水库节点（大水体，蓄水平衡）
- BoundaryNode: 边界节点（入口/出口）

Stage 3 - Task 3.1.2

作者: HydroClaude Team
日期: 2025-10-29
"""

import numpy as np
from typing import List, Tuple, Optional, Dict
from .topology import Node


class JunctionNode(Node):
    """
    汇流节点

    多条河段汇入一点，需要满足:
    1. 质量守恒: ΣQ_in = ΣQ_out
    2. 能量守恒或动量守恒（可选）

    默认使用能量守恒（简化）:
    E_junction = mean(E_i) for all incoming reaches
    E = h + V²/(2g) + z

    Attributes:
        junction_method (str): 汇流计算方法 ('energy', 'momentum', 'average')
        h_junction (float): 汇流点水位 (m)
    """

    def __init__(self,
                 node_id: str,
                 elevation: float = 0.0,
                 x: float = 0.0,
                 y: float = 0.0,
                 junction_method: str = 'energy'):
        """
        初始化汇流节点

        Args:
            node_id: 节点唯一标识
            elevation: 节点高程 (m)
            x, y: 平面坐标 (m)
            junction_method: 汇流计算方法
                - 'energy': 能量守恒（默认）
                - 'momentum': 动量守恒
                - 'average': 简单平均
        """
        super().__init__(node_id, 'junction', elevation, x, y)

        valid_methods = ['energy', 'momentum', 'average']
        if junction_method not in valid_methods:
            raise ValueError(f"Invalid junction_method: {junction_method}. "
                           f"Must be one of {valid_methods}")

        self.junction_method = junction_method
        self.h_junction = None  # 汇流点水位
        self.g = 9.81  # 重力加速度

    def compute_junction_water_level(self,
                                     h_upstream_list: List[float],
                                     Q_upstream_list: List[float],
                                     A_upstream_list: List[float]) -> float:
        """
        计算汇流节点水位

        Args:
            h_upstream_list: 上游河段水深列表 (m)
            Q_upstream_list: 上游河段流量列表 (m³/s)
            A_upstream_list: 上游河段断面积列表 (m²)

        Returns:
            汇流点水位 (m)
        """
        if not h_upstream_list:
            return self.elevation

        if self.junction_method == 'average':
            # 简单平均水深
            h_avg = np.mean(h_upstream_list)
            self.h_junction = self.elevation + h_avg
            return self.h_junction

        elif self.junction_method == 'energy':
            # 能量守恒
            E_list = []
            for h, Q, A in zip(h_upstream_list, Q_upstream_list, A_upstream_list):
                # 速度
                V = Q / A if A > 1e-6 else 0.0
                # 能量
                E = self.elevation + h + V**2 / (2 * self.g)
                E_list.append(E)

            # 平均能量
            E_avg = np.mean(E_list)

            # 假设汇流点流速为平均流速
            Q_total = sum(Q_upstream_list)
            A_junction = sum(A_upstream_list) / len(A_upstream_list)  # 简化
            V_junction = Q_total / A_junction if A_junction > 1e-6 else 0.0

            # 求解水深: E = z + h + V²/(2g)
            h_junction = E_avg - self.elevation - V_junction**2 / (2 * self.g)
            h_junction = max(0.0, h_junction)

            self.h_junction = self.elevation + h_junction
            return self.h_junction

        elif self.junction_method == 'momentum':
            # 动量守恒（简化版本）
            # ΣρQV = 常数
            momentum_total = sum(Q * Q / A if A > 1e-6 else 0.0
                               for Q, A in zip(Q_upstream_list, A_upstream_list))

            # 平均水深（动量权重）
            h_weighted = sum(h * abs(Q) for h, Q in zip(h_upstream_list, Q_upstream_list))
            Q_total = sum(abs(Q) for Q in Q_upstream_list)
            h_avg = h_weighted / Q_total if Q_total > 1e-6 else np.mean(h_upstream_list)

            self.h_junction = self.elevation + h_avg
            return self.h_junction

        return self.elevation

    def distribute_outflow(self,
                          Q_total: float,
                          n_outflows: int,
                          method: str = 'equal') -> List[float]:
        """
        分配出流

        Args:
            Q_total: 总流量 (m³/s)
            n_outflows: 出流河段数量
            method: 分配方法
                - 'equal': 等分（默认）
                - 'weighted': 加权（需要额外信息）

        Returns:
            出流流量列表 (m³/s)
        """
        if method == 'equal':
            Q_each = Q_total / n_outflows if n_outflows > 0 else 0.0
            return [Q_each] * n_outflows

        # 其他方法可扩展
        return [Q_total / n_outflows] * n_outflows

    def solve_junction(self,
                      upstream_reaches: List,
                      downstream_reaches: List) -> Tuple[float, List[float]]:
        """
        求解汇流节点

        Args:
            upstream_reaches: 上游河段列表
            downstream_reaches: 下游河段列表

        Returns:
            (h_junction, Q_out_list): 汇流点水位，下游流量列表
        """
        # 收集上游信息
        h_list = []
        Q_list = []
        A_list = []

        for reach in upstream_reaches:
            h = reach.get_downstream_h()
            Q = reach.get_downstream_Q()
            # 简化：假设矩形断面
            A = reach.solver.width * h if hasattr(reach.solver, 'width') else 10.0 * h
            h_list.append(h)
            Q_list.append(Q)
            A_list.append(A)

        # 计算汇流点水位
        h_junction = self.compute_junction_water_level(h_list, Q_list, A_list)

        # 计算总流量
        Q_total = sum(Q_list)

        # 分配出流
        Q_out_list = self.distribute_outflow(Q_total, len(downstream_reaches))

        # 更新节点状态
        self.Q_in = Q_list
        self.Q_out = Q_out_list
        self.h = h_junction - self.elevation  # 水深

        return h_junction, Q_out_list

    def __repr__(self) -> str:
        method_str = f"method={self.junction_method}"
        return (f"JunctionNode(id='{self.id}', z={self.elevation:.2f}m, "
                f"{method_str})")


class BifurcationNode(Node):
    """
    分流节点

    一条河段分为多条，需要指定分流规则:
    1. 固定比例分流
    2. 基于水位的动态分流（高级）

    Attributes:
        split_ratios (list): 分流比例列表，和为1.0
        split_method (str): 分流方法 ('fixed', 'dynamic')
    """

    def __init__(self,
                 node_id: str,
                 split_ratios: Optional[List[float]] = None,
                 elevation: float = 0.0,
                 x: float = 0.0,
                 y: float = 0.0,
                 split_method: str = 'fixed'):
        """
        初始化分流节点

        Args:
            node_id: 节点唯一标识
            split_ratios: 分流比例列表 [r1, r2, ...], sum(r) = 1.0
            elevation: 节点高程 (m)
            x, y: 平面坐标 (m)
            split_method: 分流方法
                - 'fixed': 固定比例（默认）
                - 'dynamic': 动态分流（基于水位）
        """
        super().__init__(node_id, 'bifurcation', elevation, x, y)

        self.split_method = split_method

        if split_ratios is None:
            split_ratios = [0.5, 0.5]  # 默认均分两路

        # 验证分流比例
        if abs(sum(split_ratios) - 1.0) > 1e-6:
            raise ValueError(f"Split ratios must sum to 1.0, got {sum(split_ratios)}")

        if any(r < 0 or r > 1 for r in split_ratios):
            raise ValueError("Split ratios must be in [0, 1]")

        self.split_ratios = split_ratios

    def compute_split_flows(self,
                           Q_total: float,
                           h_downstream_list: Optional[List[float]] = None) -> List[float]:
        """
        计算分流流量

        Args:
            Q_total: 总流量 (m³/s)
            h_downstream_list: 下游河段水位列表（动态分流时使用）

        Returns:
            分流流量列表 (m³/s)
        """
        if self.split_method == 'fixed':
            # 固定比例分流
            return [Q_total * r for r in self.split_ratios]

        elif self.split_method == 'dynamic':
            # 动态分流（基于下游水位）
            if h_downstream_list is None or len(h_downstream_list) != len(self.split_ratios):
                # 降级到固定比例
                return [Q_total * r for r in self.split_ratios]

            # 简化：流量与水位差成正比
            # Q_i ∝ (z_node - z_downstream_i)
            delta_h_list = [max(0.0, self.elevation - h) for h in h_downstream_list]

            sum_delta_h = sum(delta_h_list)
            if sum_delta_h < 1e-6:
                # 无水头差，等分
                n = len(h_downstream_list)
                return [Q_total / n] * n

            # 按水头差分配
            Q_list = [Q_total * (dh / sum_delta_h) for dh in delta_h_list]
            return Q_list

        return [Q_total * r for r in self.split_ratios]

    def set_split_ratios(self, ratios: List[float]):
        """
        设置分流比例

        Args:
            ratios: 新的分流比例列表
        """
        if abs(sum(ratios) - 1.0) > 1e-6:
            raise ValueError(f"Split ratios must sum to 1.0, got {sum(ratios)}")
        self.split_ratios = ratios

    def solve_bifurcation(self,
                         upstream_reach,
                         downstream_reaches: List) -> Tuple[float, List[float]]:
        """
        求解分流节点

        Args:
            upstream_reach: 上游河段
            downstream_reaches: 下游河段列表

        Returns:
            (Q_total, Q_split_list): 总流量，分流列表
        """
        # 上游流量
        Q_total = upstream_reach.get_downstream_Q()

        # 下游水位（动态分流时使用）
        h_downstream_list = None
        if self.split_method == 'dynamic':
            h_downstream_list = [reach.get_upstream_h() + reach.solver.slope * reach.length
                                for reach in downstream_reaches]

        # 计算分流
        Q_split_list = self.compute_split_flows(Q_total, h_downstream_list)

        # 更新节点状态
        self.Q_in = [Q_total]
        self.Q_out = Q_split_list
        self.h = upstream_reach.get_downstream_h()

        return Q_total, Q_split_list

    def __repr__(self) -> str:
        ratios_str = "[" + ", ".join(f"{r:.2f}" for r in self.split_ratios) + "]"
        return (f"BifurcationNode(id='{self.id}', ratios={ratios_str}, "
                f"method={self.split_method})")


class ReservoirNode(Node):
    """
    水库节点

    大水体，水位变化缓慢，满足蓄水平衡方程:
    dV/dt = Q_in - Q_out

    其中 V = f(h) 为库容曲线

    Attributes:
        area (float): 水面面积 (m²)
        volume (float): 当前库容 (m³)
        h_min (float): 最低水位 (m)
        h_max (float): 最高水位 (m)
        storage_curve (callable): 库容曲线 V(h)
    """

    def __init__(self,
                 node_id: str,
                 area: float = 1e6,
                 elevation: float = 0.0,
                 x: float = 0.0,
                 y: float = 0.0,
                 h_min: float = 0.0,
                 h_max: float = 10.0):
        """
        初始化水库节点

        Args:
            node_id: 节点唯一标识
            area: 水面面积 (m²)
            elevation: 库底高程 (m)
            x, y: 平面坐标 (m)
            h_min: 最低水位 (m, 相对于库底)
            h_max: 最高水位 (m, 相对于库底)
        """
        super().__init__(node_id, 'reservoir', elevation, x, y)

        self.area = area
        self.h_min = h_min
        self.h_max = h_max

        # 默认库容曲线（线性，可自定义）
        self.storage_curve = None

        # 初始水位和库容
        self.h = (h_min + h_max) / 2  # 初始水深为中间值
        self.volume = self.compute_volume(self.h)

    def compute_volume(self, h: float) -> float:
        """
        计算库容

        Args:
            h: 水深 (m, 相对于库底)

        Returns:
            库容 (m³)
        """
        if self.storage_curve is not None:
            return self.storage_curve(h)

        # 默认：矩形库容 V = A * h
        return self.area * h

    def compute_water_level_from_volume(self, V: float) -> float:
        """
        从库容计算水位

        Args:
            V: 库容 (m³)

        Returns:
            水深 (m, 相对于库底)
        """
        if self.storage_curve is not None:
            # 需要反函数（简化：数值求解）
            # 这里简化为线性
            return V / self.area

        # 默认：h = V / A
        h = V / self.area
        return np.clip(h, self.h_min, self.h_max)

    def update_volume(self, Q_in_total: float, Q_out_total: float, dt: float) -> float:
        """
        更新库容（蓄水平衡方程）

        dV/dt = Q_in - Q_out

        Args:
            Q_in_total: 总入流 (m³/s)
            Q_out_total: 总出流 (m³/s)
            dt: 时间步长 (s)

        Returns:
            新的水位 (m, 相对于库底)
        """
        # 蓄水平衡
        dV = (Q_in_total - Q_out_total) * dt

        # 更新库容
        self.volume = max(0.0, self.volume + dV)

        # 更新水位
        self.h = self.compute_water_level_from_volume(self.volume)

        # 限制在合理范围
        self.h = np.clip(self.h, self.h_min, self.h_max)

        return self.h

    def set_storage_curve(self, curve_function):
        """
        设置库容曲线

        Args:
            curve_function: 函数 V = f(h)
        """
        self.storage_curve = curve_function

    def get_absolute_water_level(self) -> float:
        """获取绝对水位（高程 + 水深）"""
        return self.elevation + self.h

    def __repr__(self) -> str:
        return (f"ReservoirNode(id='{self.id}', area={self.area/1e6:.2f}km², "
                f"h={self.h:.2f}m, V={self.volume/1e6:.2f}M m³)")


class BoundaryNode(Node):
    """
    边界节点

    入口或出口边界，指定:
    - 上游边界: Q(t) or h(t)
    - 下游边界: h(t) or Rating Curve

    Attributes:
        boundary_type (str): 边界类型 ('inflow', 'outflow')
        bc_variable (str): 边界变量 ('Q', 'h', 'rating')
        bc_value: 边界值（可以是常数或函数）
    """

    def __init__(self,
                 node_id: str,
                 boundary_type: str = 'inflow',
                 bc_variable: str = 'Q',
                 bc_value = None,
                 elevation: float = 0.0,
                 x: float = 0.0,
                 y: float = 0.0):
        """
        初始化边界节点

        Args:
            node_id: 节点唯一标识
            boundary_type: 边界类型
                - 'inflow': 入流边界（上游）
                - 'outflow': 出流边界（下游）
            bc_variable: 边界变量
                - 'Q': 流量边界
                - 'h': 水位边界
                - 'rating': Rating Curve边界
            bc_value: 边界值
                - 常数: float
                - 时变: callable(t) -> float
                - Rating curve: callable(h or Q) -> Q or h
            elevation: 节点高程 (m)
            x, y: 平面坐标 (m)
        """
        super().__init__(node_id, 'boundary', elevation, x, y)

        valid_types = ['inflow', 'outflow']
        if boundary_type not in valid_types:
            raise ValueError(f"Invalid boundary_type: {boundary_type}. "
                           f"Must be one of {valid_types}")

        valid_vars = ['Q', 'h', 'rating']
        if bc_variable not in valid_vars:
            raise ValueError(f"Invalid bc_variable: {bc_variable}. "
                           f"Must be one of {valid_vars}")

        self.boundary_type = boundary_type
        self.bc_variable = bc_variable
        self.bc_value = bc_value

    def get_boundary_value(self, t: float = 0.0, **kwargs) -> float:
        """
        获取边界值

        Args:
            t: 时间 (s)
            **kwargs: 其他参数（如rating curve需要的h或Q）

        Returns:
            边界值
        """
        if self.bc_value is None:
            return 0.0

        # 常数
        if isinstance(self.bc_value, (int, float)):
            return float(self.bc_value)

        # 时变或rating curve（callable）
        if callable(self.bc_value):
            if self.bc_variable == 'rating':
                # Rating curve: 需要传入h或Q
                if 'h' in kwargs:
                    return self.bc_value(kwargs['h'])
                elif 'Q' in kwargs:
                    return self.bc_value(kwargs['Q'])
                else:
                    return 0.0
            else:
                # 时变: callable(t)
                return self.bc_value(t)

        return 0.0

    def set_boundary_condition(self, bc_variable: str, bc_value):
        """
        设置边界条件

        Args:
            bc_variable: 'Q', 'h', or 'rating'
            bc_value: 边界值
        """
        self.bc_variable = bc_variable
        self.bc_value = bc_value

    def __repr__(self) -> str:
        value_str = f"{self.bc_variable}"
        if isinstance(self.bc_value, (int, float)):
            value_str += f"={self.bc_value:.2f}"
        elif callable(self.bc_value):
            value_str += "=f(t)"
        return (f"BoundaryNode(id='{self.id}', type={self.boundary_type}, "
                f"{value_str})")


# 便捷函数
def create_junction(node_id: str, elevation: float = 0.0,
                   method: str = 'energy') -> JunctionNode:
    """创建汇流节点（便捷函数）"""
    return JunctionNode(node_id, elevation=elevation, junction_method=method)


def create_bifurcation(node_id: str, split_ratios: List[float],
                      elevation: float = 0.0) -> BifurcationNode:
    """创建分流节点（便捷函数）"""
    return BifurcationNode(node_id, split_ratios=split_ratios, elevation=elevation)


def create_reservoir(node_id: str, area: float = 1e6,
                    elevation: float = 0.0) -> ReservoirNode:
    """创建水库节点（便捷函数）"""
    return ReservoirNode(node_id, area=area, elevation=elevation)


def create_inflow_boundary(node_id: str, Q: float = 0.0,
                          elevation: float = 0.0) -> BoundaryNode:
    """创建入流边界节点（便捷函数）"""
    return BoundaryNode(node_id, boundary_type='inflow',
                       bc_variable='Q', bc_value=Q, elevation=elevation)


def create_outflow_boundary(node_id: str, h: float = 0.0,
                           elevation: float = 0.0) -> BoundaryNode:
    """创建出流边界节点（便捷函数）"""
    return BoundaryNode(node_id, boundary_type='outflow',
                       bc_variable='h', bc_value=h, elevation=elevation)


if __name__ == "__main__":
    """简单测试"""
    print("Testing Node Types Module...")
    print()

    # 测试汇流节点
    junction = JunctionNode("J1", elevation=95.0, junction_method='energy')
    print(f"Created: {junction}")

    # 测试分流节点
    bifurc = BifurcationNode("B1", split_ratios=[0.3, 0.7], elevation=100.0)
    print(f"Created: {bifurc}")

    # 测试水库节点
    reservoir = ReservoirNode("R1", area=5e6, elevation=80.0)
    print(f"Created: {reservoir}")

    # 测试边界节点
    inflow = create_inflow_boundary("IN1", Q=50.0, elevation=110.0)
    outflow = create_outflow_boundary("OUT1", h=2.0, elevation=85.0)
    print(f"Created: {inflow}")
    print(f"Created: {outflow}")

    print()
    print(" Node types module test passed!")
