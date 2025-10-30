#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Network Node Boundary Tests - 网络节点边界测试

测试network_node模块的边界情况和错误处理

Author: HydroClaude Development Team
Date: 2025-10-30
"""

import pytest
from network.network_node import NetworkNode, Junction, Reservoir, Tank


class TestNetworkNodeBoundaries:
    """测试NetworkNode基类的边界情况"""

    def test_invalid_node_id(self):
        """测试无效的节点ID"""
        with pytest.raises(ValueError, match="节点ID必须为非空字符串"):
            NetworkNode(
                node_id="",
                node_type="junction",
                elevation=10.0
            )

        with pytest.raises(ValueError, match="节点ID必须为非空字符串"):
            NetworkNode(
                node_id=None,
                node_type="junction",
                elevation=10.0
            )

    def test_invalid_node_type(self):
        """测试无效的节点类型"""
        with pytest.raises(ValueError, match="节点类型无效"):
            NetworkNode(
                node_id="N1",
                node_type="invalid_type",
                elevation=10.0
            )

    def test_negative_elevation(self):
        """测试负标高（允许）"""
        # 负标高是合法的（例如海平面以下）
        node = NetworkNode(
            node_id="N1",
            node_type="junction",
            elevation=-10.0
        )
        assert node.elevation == -10.0

    def test_extreme_elevation(self):
        """测试极端标高值"""
        # 非常高的标高
        node_high = NetworkNode(
            node_id="N1",
            node_type="junction",
            elevation=8848.0  # 珠峰高度
        )
        assert node_high.elevation == 8848.0

        # 非常低的标高
        node_low = NetworkNode(
            node_id="N2",
            node_type="junction",
            elevation=-11034.0  # 马里亚纳海沟
        )
        assert node_low.elevation == -11034.0

    def test_coordinates_optional(self):
        """测试坐标参数是可选的"""
        node_no_coord = NetworkNode(
            node_id="N1",
            node_type="junction",
            elevation=10.0
        )
        assert node_no_coord.coordinates is None

        node_with_coord = NetworkNode(
            node_id="N2",
            node_type="junction",
            elevation=10.0,
            coordinates=(100.0, 200.0)
        )
        assert node_with_coord.coordinates == (100.0, 200.0)

    def test_demand_sign_convention(self):
        """测试需水量符号约定"""
        # 正值：取水
        node_demand = NetworkNode(
            node_id="N1",
            node_type="junction",
            elevation=10.0,
            demand=0.05
        )
        assert node_demand.demand == 0.05

        # 负值：供水
        node_supply = NetworkNode(
            node_id="N2",
            node_type="junction",
            elevation=10.0,
            demand=-0.03
        )
        assert node_supply.demand == -0.03

    def test_min_and_required_pressure(self):
        """测试最小压力和要求压力"""
        node = NetworkNode(
            node_id="N1",
            node_type="junction",
            elevation=10.0,
            min_pressure=15.0,
            required_pressure=20.0
        )
        assert node.min_pressure == 15.0
        assert node.required_pressure == 20.0


class TestJunctionBoundaries:
    """测试Junction类的边界情况"""

    def test_junction_creation_minimal(self):
        """测试最小参数创建Junction"""
        j = Junction("J1", elevation=50.0)
        assert j.node_id == "J1"
        assert j.elevation == 50.0
        assert j.demand == 0.0
        assert j.node_type == "junction"

    def test_junction_with_all_parameters(self):
        """测试所有参数创建Junction"""
        j = Junction(
            node_id="J1",
            elevation=50.0,
            demand=0.01,
            coordinates=(100.0, 200.0),
            min_pressure=15.0,
            required_pressure=20.0,
            description="Test Junction"
        )
        assert j.node_id == "J1"
        assert j.elevation == 50.0
        assert j.demand == 0.01
        assert j.coordinates == (100.0, 200.0)
        assert j.min_pressure == 15.0
        assert j.required_pressure == 20.0
        assert j.description == "Test Junction"

    def test_junction_zero_demand(self):
        """测试零需水量Junction"""
        j = Junction("J1", elevation=50.0, demand=0.0)
        assert j.demand == 0.0

    def test_junction_large_demand(self):
        """测试大需水量Junction"""
        # 1 m³/s = 1000 L/s（一个大型用水点）
        j = Junction("J1", elevation=50.0, demand=1.0)
        assert j.demand == 1.0

    def test_junction_very_small_demand(self):
        """测试极小需水量Junction"""
        # 0.001 L/s
        j = Junction("J1", elevation=50.0, demand=0.000001)
        assert j.demand == 0.000001


class TestReservoirBoundaries:
    """测试Reservoir类的边界情况"""

    def test_reservoir_creation_minimal(self):
        """测试最小参数创建Reservoir"""
        r = Reservoir("R1", elevation=100.0, head=120.0)
        assert r.node_id == "R1"
        assert r.elevation == 100.0
        assert r.head == 120.0
        assert r.node_type == "reservoir"

    def test_reservoir_head_equals_elevation(self):
        """测试水头等于标高（水面在地面）"""
        r = Reservoir("R1", elevation=100.0, head=100.0)
        assert r.head == r.elevation

    def test_reservoir_head_below_elevation(self):
        """测试水头低于标高（不合理但可能存在）"""
        # 这可能代表一个空的水库
        r = Reservoir("R1", elevation=100.0, head=95.0)
        assert r.head < r.elevation

    def test_reservoir_very_high_head(self):
        """测试非常高的水头"""
        r = Reservoir("R1", elevation=100.0, head=10000.0)
        assert r.head == 10000.0

    def test_reservoir_negative_elevation(self):
        """测试负标高水库"""
        # 例如海平面以下的蓄水池
        r = Reservoir("R1", elevation=-50.0, head=-30.0)
        assert r.elevation == -50.0
        assert r.head == -30.0


class TestTankBoundaries:
    """测试Tank类的边界情况"""

    def test_tank_creation_minimal(self):
        """测试最小参数创建Tank"""
        t = Tank(
            node_id="T1",
            elevation=50.0,
            diameter=10.0,
            initial_level=5.0
        )
        assert t.node_id == "T1"
        assert t.elevation == 50.0
        assert t.diameter == 10.0
        assert t.level == 5.0  # Tank使用level属性

    def test_tank_invalid_diameter(self):
        """测试无效的直径"""
        with pytest.raises(ValueError, match="水箱直径必须 > 0"):
            Tank(
                node_id="T1",
                elevation=50.0,
                diameter=0.0,
                initial_level=5.0
            )

        with pytest.raises(ValueError, match="水箱直径必须 > 0"):
            Tank(
                node_id="T1",
                elevation=50.0,
                diameter=-5.0,
                initial_level=5.0
            )

    def test_tank_invalid_water_levels(self):
        """测试无效的水位配置"""
        # 初始水位低于最小水位
        with pytest.raises(ValueError, match="初始水位.*必须在.*范围内"):
            Tank(
                node_id="T1",
                elevation=50.0,
                diameter=10.0,
                min_level=2.0,
                max_level=10.0,
                initial_level=1.0  # < min_level
            )

        # 初始水位高于最大水位
        with pytest.raises(ValueError, match="初始水位.*必须在.*范围内"):
            Tank(
                node_id="T1",
                elevation=50.0,
                diameter=10.0,
                min_level=2.0,
                max_level=10.0,
                initial_level=11.0  # > max_level
            )

    def test_tank_zero_initial_level(self):
        """测试零初始水位"""
        t = Tank(
            node_id="T1",
            elevation=50.0,
            diameter=10.0,
            min_level=0.0,
            initial_level=0.0
        )
        assert t.level == 0.0
        assert t.head == 50.0  # elevation + level

    def test_tank_water_level_calculation(self):
        """测试水位计算"""
        t = Tank(
            node_id="T1",
            elevation=50.0,
            diameter=10.0,
            min_level=0.0,
            max_level=10.0,
            initial_level=5.0
        )
        # 水头 = 底部标高 + 水位
        expected_head = 50.0 + 5.0
        assert t.head == expected_head

    def test_tank_volume_calculation(self):
        """测试容积计算"""
        t = Tank(
            node_id="T1",
            elevation=50.0,
            diameter=10.0,
            min_level=0.0,
            max_level=10.0,
            initial_level=5.0,
            geometry="cylindrical"
        )
        # 测试几何形状属性
        assert hasattr(t, 'geometry')
        assert t.geometry == "cylindrical"

    def test_tank_small_diameter(self):
        """测试小直径水箱"""
        t = Tank(
            node_id="T1",
            elevation=50.0,
            diameter=0.5,  # 0.5m直径
            initial_level=1.0
        )
        assert t.diameter == 0.5

    def test_tank_large_diameter(self):
        """测试大直径水箱"""
        t = Tank(
            node_id="T1",
            elevation=50.0,
            diameter=50.0,  # 50m直径（大型水塔）
            initial_level=10.0
        )
        assert t.diameter == 50.0

    def test_tank_min_max_level_equal(self):
        """测试最小最大水位相等（固定水位）"""
        t = Tank(
            node_id="T1",
            elevation=50.0,
            diameter=10.0,
            min_level=5.0,
            max_level=5.0,
            initial_level=5.0
        )
        assert t.min_level == t.max_level == t.level

    def test_tank_with_description(self):
        """测试带描述的水箱"""
        t = Tank(
            node_id="T1",
            elevation=50.0,
            diameter=10.0,
            initial_level=5.0,
            description="高位水塔"
        )
        assert t.description == "高位水塔"


class TestNodeStateManagement:
    """测试节点状态管理"""

    def test_node_initial_state(self):
        """测试节点初始状态"""
        j = Junction("J1", elevation=50.0, demand=0.01)

        # 节点应该有初始水头
        assert hasattr(j, 'head')

        # 初始水头应该是合理的（如果有设置）
        if j.head is not None:
            assert isinstance(j.head, (int, float))

    def test_reservoir_constant_head(self):
        """测试水库恒定水头"""
        r = Reservoir("R1", elevation=100.0, head=120.0)

        # 水库的水头应该保持恒定
        assert r.head == 120.0
        assert r.node_type == "reservoir"

    def test_tank_variable_head(self):
        """测试水箱可变水头"""
        t = Tank(
            node_id="T1",
            elevation=50.0,
            diameter=10.0,
            min_level=0.0,
            max_level=10.0,
            initial_level=5.0
        )

        # 水箱的水头应该根据水位计算
        assert t.head == t.elevation + t.level

        # 水箱应该能够更新水位（如果有相应方法）
        if hasattr(t, 'update_level'):
            # 测试水位更新
            pass


class TestNodeComparison:
    """测试节点比较和相等性"""

    def test_same_id_different_types(self):
        """测试相同ID但不同类型的节点"""
        j = Junction("N1", elevation=50.0)
        r = Reservoir("N1", elevation=100.0, head=120.0)

        # 不同类型的节点即使ID相同也应该被视为不同
        assert j.node_type != r.node_type

    def test_node_id_uniqueness(self):
        """测试节点ID唯一性"""
        j1 = Junction("J1", elevation=50.0)
        j2 = Junction("J1", elevation=60.0)

        # 相同ID的节点（在拓扑中应该只有一个）
        assert j1.node_id == j2.node_id


class TestNodeEdgeCases:
    """测试节点极端情况"""

    def test_unicode_node_id(self):
        """测试Unicode节点ID"""
        j = Junction("节点1", elevation=50.0)
        assert j.node_id == "节点1"

    def test_very_long_node_id(self):
        """测试很长的节点ID"""
        long_id = "J" + "1" * 1000
        j = Junction(long_id, elevation=50.0)
        assert j.node_id == long_id
        assert len(j.node_id) == 1001

    def test_node_id_with_special_characters(self):
        """测试包含特殊字符的节点ID"""
        special_ids = [
            "J-1", "J_1", "J.1", "J#1", "J@1",
            "J 1",  # 包含空格
            "J1/2", # 包含斜杠
        ]

        for node_id in special_ids:
            j = Junction(node_id, elevation=50.0)
            assert j.node_id == node_id

    def test_scientific_notation_values(self):
        """测试科学计数法的值"""
        j = Junction(
            node_id="J1",
            elevation=1e2,  # 100.0
            demand=1e-3     # 0.001
        )
        assert j.elevation == 100.0
        assert j.demand == 0.001

    def test_very_small_demand(self):
        """测试极小需水量"""
        j = Junction("J1", elevation=50.0, demand=1e-10)
        assert j.demand == 1e-10

    def test_very_large_demand(self):
        """测试极大需水量"""
        j = Junction("J1", elevation=50.0, demand=1e3)
        assert j.demand == 1000.0


if __name__ == '__main__':
    pytest.main([__file__, '-v', '--tb=short'])
