"""
内部水工建筑物 (Internal Hydraulic Structures)

将堰、闸等水工建筑物从外边界转化为内部边界，作为特殊的河段耦合器。

主要功能:
1. InternalStructure基类 - 通用内部建筑物框架
2. InternalWeir - 内部堰（宽顶堰、薄壁堰）
3. InternalGate - 内部闸门（平板闸门）
4. InternalOrifice - 内部孔口
5. 自动耦合和边界条件传递

Stage 3 - Task 3.3.2

作者: HydroClaude Team
日期: 2025-10-29
"""

import numpy as np
from typing import Optional, Tuple, Dict
from abc import ABC, abstractmethod


class InternalStructure(ABC):
    """
    内部水工建筑物基类

    将水工建筑物作为特殊的河段耦合器，连接上下游河段。

    工作原理:
    1. 从上下游河段获取水位
    2. 调用建筑物的compute_discharge()计算过流流量
    3. 将流量设置为上下游河段的边界条件

    属性:
        structure: 水工建筑物对象 (BroadCrestedWeir, SluiceGate等)
        upstream_reach: 上游河段 (Reach对象)
        downstream_reach: 下游河段 (Reach对象)
        node: 耦合节点 (Node对象)
        Q_current: 当前过流流量 (m³/s)
        h_upstream: 上游水位 (m)
        h_downstream: 下游水位 (m)
    """

    def __init__(self,
                 structure,
                 upstream_reach,
                 downstream_reach,
                 node,
                 name: str = "Internal Structure"):
        """
        初始化内部水工建筑物

        Args:
            structure: 水工建筑物对象 (必须有compute_discharge方法)
            upstream_reach: 上游河段 (Reach对象)
            downstream_reach: 下游河段 (Reach对象)
            node: 耦合节点 (Node对象)
            name: 名称
        """
        self.structure = structure
        self.upstream = upstream_reach
        self.downstream = downstream_reach
        self.node = node
        self.name = name

        # 状态变量
        self.Q_current = 0.0
        self.h_upstream = 0.0
        self.h_downstream = 0.0
        self.delta_h = 0.0

        # 验证建筑物接口
        if not hasattr(structure, 'compute_discharge'):
            raise ValueError(f"Structure must have compute_discharge() method")

    @abstractmethod
    def compute_discharge(self) -> float:
        """
        计算过流流量（由子类实现）

        Returns:
            流量 Q (m³/s)
        """
        pass

    def update_water_levels(self):
        """从上下游河段更新水位"""
        # 上游水位 = 上游河段末端水深 + 河床高程
        # 注意：solver.S0是坡度数组，取平均值
        self.h_upstream = (self.upstream.get_downstream_h() +
                          np.mean(self.upstream.solver.S0) * self.upstream.length)

        # 下游水位 = 下游河段起点水深 + 河床高程
        self.h_downstream = self.downstream.get_upstream_h()

        # 水位差
        self.delta_h = self.h_upstream - self.h_downstream

    def solve(self) -> float:
        """
        求解内部建筑物边界条件

        工作流程:
        1. 更新上下游水位
        2. 计算过流流量
        3. 设置边界条件

        Returns:
            流量 Q (m³/s)
        """
        # Step 1: 更新水位
        self.update_water_levels()

        # Step 2: 计算流量
        self.Q_current = self.compute_discharge()

        # Step 3: 设置边界条件
        # 上游河段右边界 = 流量BC
        self.upstream.solver.bc_right = {'type': 'Q', 'value': self.Q_current}

        # 下游河段左边界 = 流量BC
        self.downstream.solver.bc_left = {'type': 'Q', 'value': self.Q_current}

        # 更新节点状态
        self.node.Q_in = [self.Q_current]
        self.node.Q_out = [self.Q_current]
        self.node.h = self.h_upstream  # 节点水位取上游水位

        return self.Q_current

    def check_mass_balance(self, tol: float = 1e-3) -> Tuple[bool, float]:
        """
        检查质量平衡

        对于内部建筑物，Q_in = Q_out（质量守恒）

        Args:
            tol: 容差 (m³/s)

        Returns:
            (is_balanced, error): 是否平衡，误差值
        """
        Q_in = self.upstream.get_downstream_Q()
        Q_out = self.downstream.get_upstream_Q()

        error = abs(Q_in - Q_out)
        is_balanced = error < tol

        return is_balanced, error

    def get_status(self) -> Dict:
        """获取状态信息"""
        return {
            'name': self.name,
            'structure_type': type(self.structure).__name__,
            'Q': self.Q_current,
            'h_upstream': self.h_upstream,
            'h_downstream': self.h_downstream,
            'delta_h': self.delta_h
        }

    def print_status(self):
        """打印状态"""
        print(f"\n内部建筑物状态: {self.name}")
        print(f"  类型: {type(self.structure).__name__}")
        print(f"  上游河段: {self.upstream.id}")
        print(f"  下游河段: {self.downstream.id}")
        print(f"  上游水位: {self.h_upstream:.3f} m")
        print(f"  下游水位: {self.h_downstream:.3f} m")
        print(f"  水位差: {self.delta_h:.3f} m")
        print(f"  过流流量: {self.Q_current:.3f} m³/s")

        # 质量平衡
        is_balanced, error = self.check_mass_balance()
        print(f"  质量平衡: {'' if is_balanced else ''} (误差={error:.4f} m³/s)")


class InternalWeir(InternalStructure):
    """
    内部堰

    支持的堰类型:
    - BroadCrestedWeir (宽顶堰)
    - SharpCrestedWeir (薄壁堰)

    示例:
        from physics.hydraulic_structures import BroadCrestedWeir

        weir = BroadCrestedWeir(crest_elevation=2.0, width=10.0)
        internal_weir = InternalWeir(weir, upstream_reach, downstream_reach, node)

        # 求解过堰流量
        Q = internal_weir.solve()
    """

    def __init__(self,
                 weir,
                 upstream_reach,
                 downstream_reach,
                 node,
                 name: Optional[str] = None):
        """
        初始化内部堰

        Args:
            weir: 堰对象 (BroadCrestedWeir, SharpCrestedWeir等)
            upstream_reach: 上游河段
            downstream_reach: 下游河段
            node: 耦合节点
            name: 名称（可选，默认使用堰名称）
        """
        if name is None:
            name = f"Internal {weir.name}"

        super().__init__(weir, upstream_reach, downstream_reach, node, name)

        # 验证堰类型
        from physics.hydraulic_structures import BroadCrestedWeir, SharpCrestedWeir
        if not isinstance(weir, (BroadCrestedWeir, SharpCrestedWeir)):
            raise TypeError(f"Expected BroadCrestedWeir or SharpCrestedWeir, got {type(weir)}")

    def compute_discharge(self) -> float:
        """
        计算过堰流量

        Returns:
            流量 Q (m³/s)
        """
        # 调用堰的compute_discharge方法
        Q = self.structure.compute_discharge(
            h_upstream=self.h_upstream,
            h_downstream=self.h_downstream
        )

        return Q

    def get_flow_regime(self) -> str:
        """获取流态"""
        if hasattr(self.structure, 'get_regime'):
            regime = self.structure.get_regime(self.h_upstream, self.h_downstream)
            return regime.value if regime else "N/A"
        return "unknown"


class InternalGate(InternalStructure):
    """
    内部闸门

    支持的闸门类型:
    - SluiceGate (平板闸门)

    特点:
    - 可调节开度
    - 支持自由/淹没出流

    示例:
        from physics.hydraulic_structures import SluiceGate

        gate = SluiceGate(sill_elevation=0.0, width=8.0, opening=0.5)
        internal_gate = InternalGate(gate, upstream_reach, downstream_reach, node)

        # 调节开度
        internal_gate.set_opening(1.0)

        # 求解过闸流量
        Q = internal_gate.solve()
    """

    def __init__(self,
                 gate,
                 upstream_reach,
                 downstream_reach,
                 node,
                 name: Optional[str] = None):
        """
        初始化内部闸门

        Args:
            gate: 闸门对象 (SluiceGate)
            upstream_reach: 上游河段
            downstream_reach: 下游河段
            node: 耦合节点
            name: 名称（可选）
        """
        if name is None:
            name = f"Internal {gate.name}"

        super().__init__(gate, upstream_reach, downstream_reach, node, name)

        # 验证闸门类型
        from physics.hydraulic_structures import SluiceGate
        if not isinstance(gate, SluiceGate):
            raise TypeError(f"Expected SluiceGate, got {type(gate)}")

    def compute_discharge(self) -> float:
        """
        计算过闸流量

        Returns:
            流量 Q (m³/s)
        """
        Q = self.structure.compute_discharge(
            h_upstream=self.h_upstream,
            h_downstream=self.h_downstream
        )

        return Q

    def set_opening(self, opening: float):
        """
        设置闸门开度

        Args:
            opening: 开度 (m)
        """
        self.structure.set_opening(opening)

    def get_opening(self) -> float:
        """获取当前开度"""
        return self.structure.opening

    def get_flow_regime(self) -> str:
        """获取流态"""
        regime = self.structure.get_regime(self.h_upstream, self.h_downstream)
        return regime.value if regime else "N/A"


class InternalOrifice(InternalStructure):
    """
    内部孔口

    支持的孔口类型:
    - Orifice (圆形孔口)

    用于:
    - 涵洞
    - 泄水孔
    - 箱涵

    示例:
        from physics.hydraulic_structures import Orifice

        orifice = Orifice(center_elevation=1.0, diameter=1.5)
        internal_orifice = InternalOrifice(orifice, upstream_reach, downstream_reach, node)

        Q = internal_orifice.solve()
    """

    def __init__(self,
                 orifice,
                 upstream_reach,
                 downstream_reach,
                 node,
                 name: Optional[str] = None):
        """
        初始化内部孔口

        Args:
            orifice: 孔口对象 (Orifice)
            upstream_reach: 上游河段
            downstream_reach: 下游河段
            node: 耦合节点
            name: 名称（可选）
        """
        if name is None:
            name = f"Internal {orifice.name}"

        super().__init__(orifice, upstream_reach, downstream_reach, node, name)

        # 验证孔口类型
        from physics.hydraulic_structures import Orifice
        if not isinstance(orifice, Orifice):
            raise TypeError(f"Expected Orifice, got {type(orifice)}")

    def compute_discharge(self) -> float:
        """
        计算过流量

        Returns:
            流量 Q (m³/s)
        """
        Q = self.structure.compute_discharge(
            h_upstream=self.h_upstream,
            h_downstream=self.h_downstream
        )

        return Q


# 便捷函数

def create_internal_weir(weir, upstream_reach, downstream_reach, node) -> InternalWeir:
    """
    创建内部堰（便捷函数）

    Args:
        weir: 堰对象
        upstream_reach: 上游河段
        downstream_reach: 下游河段
        node: 耦合节点

    Returns:
        InternalWeir实例

    示例:
        from physics.hydraulic_structures import BroadCrestedWeir
        weir = BroadCrestedWeir(crest_elevation=2.0, width=10.0)
        internal_weir = create_internal_weir(weir, reach1, reach2, node)
    """
    return InternalWeir(weir, upstream_reach, downstream_reach, node)


def create_internal_gate(gate, upstream_reach, downstream_reach, node) -> InternalGate:
    """
    创建内部闸门（便捷函数）

    Args:
        gate: 闸门对象
        upstream_reach: 上游河段
        downstream_reach: 下游河段
        node: 耦合节点

    Returns:
        InternalGate实例

    示例:
        from physics.hydraulic_structures import SluiceGate
        gate = SluiceGate(sill_elevation=0.0, width=8.0, opening=0.5)
        internal_gate = create_internal_gate(gate, reach1, reach2, node)
    """
    return InternalGate(gate, upstream_reach, downstream_reach, node)


def create_internal_orifice(orifice, upstream_reach, downstream_reach, node) -> InternalOrifice:
    """
    创建内部孔口（便捷函数）

    Args:
        orifice: 孔口对象
        upstream_reach: 上游河段
        downstream_reach: 下游河段
        node: 耦合节点

    Returns:
        InternalOrifice实例

    示例:
        from physics.hydraulic_structures import Orifice
        orifice = Orifice(center_elevation=1.0, diameter=1.5)
        internal_orifice = create_internal_orifice(orifice, reach1, reach2, node)
    """
    return InternalOrifice(orifice, upstream_reach, downstream_reach, node)


if __name__ == "__main__":
    """简单测试"""
    print("Network Internal Structures Module")
    print("Converts hydraulic structures to internal boundaries")
    print()
    print("Main classes:")
    print("  - InternalStructure: 内部建筑物基类")
    print("  - InternalWeir: 内部堰")
    print("  - InternalGate: 内部闸门")
    print("  - InternalOrifice: 内部孔口")
    print()
    print("Convenience functions:")
    print("  - create_internal_weir()")
    print("  - create_internal_gate()")
    print("  - create_internal_orifice()")
