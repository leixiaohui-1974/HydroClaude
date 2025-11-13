"""
节点类型测试

测试network.nodes模块的功能：
1. JunctionNode - 汇流节点
2. BifurcationNode - 分流节点
3. ReservoirNode - 水库节点
4. BoundaryNode - 边界节点

Stage 3 - Task 3.1.2 测试

作者: HydroClaude Team
日期: 2025-10-29
"""

import pytest
import numpy as np
import sys
import os

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from network.nodes import (
    JunctionNode, BifurcationNode, ReservoirNode, BoundaryNode,
    create_junction, create_bifurcation, create_reservoir,
    create_inflow_boundary, create_outflow_boundary
)


# ============================================================================
# JunctionNode Tests
# ============================================================================

@pytest.mark.p1
def test_junction_node_creation():
    """测试汇流节点创建"""
    junction = JunctionNode("J1", elevation=95.0, junction_method='energy')

    assert junction.id == "J1"
    assert junction.type == "junction"
    assert junction.elevation == 95.0
    assert junction.junction_method == 'energy'
    assert junction.h_junction is None

    print(" 汇流节点创建测试通过")


@pytest.mark.p1
def test_junction_invalid_method():
    """测试无效汇流方法"""
    with pytest.raises(ValueError, match="Invalid junction_method"):
        JunctionNode("J1", junction_method='invalid')

    print(" 无效汇流方法检测通过")


@pytest.mark.p2
def test_junction_average_method():
    """测试简单平均方法"""
    junction = JunctionNode("J1", elevation=90.0, junction_method='average')

    h_list = [2.0, 2.5, 1.8]
    Q_list = [10.0, 15.0, 8.0]
    A_list = [20.0, 25.0, 18.0]

    h_junction = junction.compute_junction_water_level(h_list, Q_list, A_list)

    expected_h = 90.0 + np.mean(h_list)  # elevation + average depth
    assert h_junction == pytest.approx(expected_h, abs=0.01)

    print(" 汇流节点简单平均方法测试通过")


@pytest.mark.p2
def test_junction_energy_method():
    """测试能量守恒方法"""
    junction = JunctionNode("J1", elevation=90.0, junction_method='energy')

    # 3条河段汇入
    h_list = [2.0, 2.0, 2.0]
    Q_list = [10.0, 10.0, 10.0]
    A_list = [20.0, 20.0, 20.0]

    h_junction = junction.compute_junction_water_level(h_list, Q_list, A_list)

    # 能量应该守恒
    assert h_junction > 90.0  # 水位应该在库底之上
    assert h_junction < 95.0  # 合理范围

    print(" 汇流节点能量守恒方法测试通过")


@pytest.mark.p2
def test_junction_distribute_outflow():
    """测试出流分配"""
    junction = JunctionNode("J1")

    Q_total = 30.0
    n_outflows = 3

    Q_out_list = junction.distribute_outflow(Q_total, n_outflows, method='equal')

    assert len(Q_out_list) == 3
    assert all(Q == pytest.approx(10.0) for Q in Q_out_list)
    assert sum(Q_out_list) == pytest.approx(Q_total)

    print(" 汇流节点出流分配测试通过")


# ============================================================================
# BifurcationNode Tests
# ============================================================================

@pytest.mark.p1
def test_bifurcation_node_creation():
    """测试分流节点创建"""
    bifurc = BifurcationNode("B1", split_ratios=[0.3, 0.7], elevation=100.0)

    assert bifurc.id == "B1"
    assert bifurc.type == "bifurcation"
    assert bifurc.split_ratios == [0.3, 0.7]
    assert bifurc.split_method == 'fixed'

    print(" 分流节点创建测试通过")


@pytest.mark.p1
def test_bifurcation_invalid_ratios():
    """测试无效分流比例"""
    # 和不为1
    with pytest.raises(ValueError, match="must sum to 1.0"):
        BifurcationNode("B1", split_ratios=[0.3, 0.5])

    # 负数 (这个会先触发sum检查，因为0.6 + -0.4 = 0.2 ≠ 1.0)
    with pytest.raises(ValueError, match="must sum to 1.0"):
        BifurcationNode("B1", split_ratios=[0.6, -0.4])

    # 超过1 (这个也会先触发sum检查，因为0.6 + 1.4 = 2.0 ≠ 1.0)
    with pytest.raises(ValueError, match="must sum to 1.0"):
        BifurcationNode("B1", split_ratios=[0.6, 1.4])

    # 测试范围检查：和为1但有负数
    with pytest.raises(ValueError, match="must be in"):
        BifurcationNode("B1", split_ratios=[1.5, -0.5])

    # 测试范围检查：和为1但超过1
    with pytest.raises(ValueError, match="must be in"):
        BifurcationNode("B1", split_ratios=[-0.2, 1.2])

    print(" 无效分流比例检测通过")


@pytest.mark.p2
def test_bifurcation_fixed_split():
    """测试固定比例分流"""
    bifurc = BifurcationNode("B1", split_ratios=[0.25, 0.75])

    Q_total = 40.0
    Q_split = bifurc.compute_split_flows(Q_total)

    assert len(Q_split) == 2
    assert Q_split[0] == pytest.approx(10.0)
    assert Q_split[1] == pytest.approx(30.0)
    assert sum(Q_split) == pytest.approx(Q_total)

    print(" 固定比例分流测试通过")


@pytest.mark.p2
def test_bifurcation_dynamic_split():
    """测试动态分流"""
    bifurc = BifurcationNode("B1", split_ratios=[0.5, 0.5],
                             elevation=100.0, split_method='dynamic')

    Q_total = 30.0

    # 下游水位不同（第一条水位低，流量应该更大）
    h_downstream = [95.0, 98.0]  # 第一条水头差5m，第二条2m

    Q_split = bifurc.compute_split_flows(Q_total, h_downstream)

    assert len(Q_split) == 2
    assert sum(Q_split) == pytest.approx(Q_total)
    # 第一条（水头差大）流量应该更大
    assert Q_split[0] > Q_split[1]

    print(" 动态分流测试通过")


@pytest.mark.p2
def test_bifurcation_set_ratios():
    """测试设置分流比例"""
    bifurc = BifurcationNode("B1", split_ratios=[0.5, 0.5])

    # 更改比例
    bifurc.set_split_ratios([0.2, 0.8])
    assert bifurc.split_ratios == [0.2, 0.8]

    Q_split = bifurc.compute_split_flows(50.0)
    assert Q_split[0] == pytest.approx(10.0)
    assert Q_split[1] == pytest.approx(40.0)

    print(" 分流比例设置测试通过")


# ============================================================================
# ReservoirNode Tests
# ============================================================================

@pytest.mark.p1
def test_reservoir_node_creation():
    """测试水库节点创建"""
    reservoir = ReservoirNode("R1", area=5e6, elevation=80.0,
                             h_min=0.0, h_max=20.0)

    assert reservoir.id == "R1"
    assert reservoir.type == "reservoir"
    assert reservoir.area == 5e6
    assert reservoir.elevation == 80.0
    assert reservoir.h_min == 0.0
    assert reservoir.h_max == 20.0

    # 初始水深应该是中间值
    assert reservoir.h == pytest.approx(10.0)

    print(" 水库节点创建测试通过")


@pytest.mark.p2
def test_reservoir_compute_volume():
    """测试库容计算"""
    reservoir = ReservoirNode("R1", area=1e6, elevation=80.0)

    # 默认线性库容: V = A * h
    h = 5.0
    V = reservoir.compute_volume(h)

    expected_V = 1e6 * 5.0  # = 5M m^3
    assert V == pytest.approx(expected_V)

    print(" 水库库容计算测试通过")


@pytest.mark.p2
def test_reservoir_update_volume():
    """测试库容更新"""
    reservoir = ReservoirNode("R1", area=1e6, elevation=80.0)

    # 初始状态
    h_init = reservoir.h
    V_init = reservoir.volume

    # 更新：入流 > 出流
    Q_in = 100.0  # m^3/s
    Q_out = 50.0  # m^3/s
    dt = 3600.0  # 1小时 = 3600s

    h_new = reservoir.update_volume(Q_in, Q_out, dt)

    # 净入流
    dV = (Q_in - Q_out) * dt  # = 50 * 3600 = 180000 m^3
    expected_V = V_init + dV
    expected_h = expected_V / reservoir.area

    assert reservoir.volume == pytest.approx(expected_V)
    assert reservoir.h == pytest.approx(expected_h, abs=0.01)
    assert h_new > h_init  # 水位应该上升

    print(" 水库蓄水平衡更新测试通过")


@pytest.mark.p2
def test_reservoir_limits():
    """测试水库水位限制"""
    reservoir = ReservoirNode("R1", area=1e6, elevation=80.0,
                             h_min=0.0, h_max=10.0)

    # 巨大入流，应该限制在h_max
    Q_in = 10000.0
    Q_out = 0.0
    dt = 10000.0

    h_new = reservoir.update_volume(Q_in, Q_out, dt)

    assert reservoir.h == pytest.approx(reservoir.h_max)
    assert h_new == pytest.approx(reservoir.h_max)

    print(" 水库水位限制测试通过")


@pytest.mark.p3
def test_reservoir_custom_storage_curve():
    """测试自定义库容曲线"""
    reservoir = ReservoirNode("R1", area=1e6, elevation=80.0)

    # 设置非线性库容曲线: V = A * h^1.5
    def custom_curve(h):
        return reservoir.area * (h ** 1.5)

    reservoir.set_storage_curve(custom_curve)

    h = 4.0
    V = reservoir.compute_volume(h)

    expected_V = 1e6 * (4.0 ** 1.5)  # = 1e6 * 8 = 8M m^3
    assert V == pytest.approx(expected_V)

    print(" 自定义库容曲线测试通过")


# ============================================================================
# BoundaryNode Tests
# ============================================================================

@pytest.mark.p1
def test_boundary_node_creation():
    """测试边界节点创建"""
    inflow = BoundaryNode("IN1", boundary_type='inflow',
                         bc_variable='Q', bc_value=50.0)

    assert inflow.id == "IN1"
    assert inflow.type == "boundary"
    assert inflow.boundary_type == 'inflow'
    assert inflow.bc_variable == 'Q'
    assert inflow.bc_value == 50.0

    print(" 边界节点创建测试通过")


@pytest.mark.p1
def test_boundary_invalid_type():
    """测试无效边界类型"""
    with pytest.raises(ValueError, match="Invalid boundary_type"):
        BoundaryNode("B1", boundary_type='invalid')

    with pytest.raises(ValueError, match="Invalid bc_variable"):
        BoundaryNode("B1", bc_variable='invalid')

    print(" 无效边界类型检测通过")


@pytest.mark.p2
def test_boundary_constant_value():
    """测试常数边界条件"""
    boundary = BoundaryNode("B1", bc_variable='Q', bc_value=30.0)

    value = boundary.get_boundary_value(t=0.0)
    assert value == pytest.approx(30.0)

    value = boundary.get_boundary_value(t=3600.0)
    assert value == pytest.approx(30.0)  # 常数

    print(" 常数边界条件测试通过")


@pytest.mark.p2
def test_boundary_time_varying():
    """测试时变边界条件"""
    # 时变流量: Q(t) = 10 + 0.01*t
    def Q_func(t):
        return 10.0 + 0.01 * t

    boundary = BoundaryNode("B1", bc_variable='Q', bc_value=Q_func)

    value_0 = boundary.get_boundary_value(t=0.0)
    value_3600 = boundary.get_boundary_value(t=3600.0)

    assert value_0 == pytest.approx(10.0)
    assert value_3600 == pytest.approx(46.0)  # 10 + 0.01*3600

    print(" 时变边界条件测试通过")


@pytest.mark.p2
def test_boundary_rating_curve():
    """测试Rating Curve边界"""
    # Rating curve: Q = 10 * h^1.5
    def rating_curve(h):
        return 10.0 * (h ** 1.5)

    boundary = BoundaryNode("B1", bc_variable='rating', bc_value=rating_curve)

    Q = boundary.get_boundary_value(h=2.0)
    expected_Q = 10.0 * (2.0 ** 1.5)  # ~= 28.28
    assert Q == pytest.approx(expected_Q)

    print(" Rating Curve边界条件测试通过")


@pytest.mark.p2
def test_boundary_set_condition():
    """测试设置边界条件"""
    boundary = BoundaryNode("B1", bc_variable='Q', bc_value=10.0)

    # 更改边界条件
    boundary.set_boundary_condition('h', 2.5)

    assert boundary.bc_variable == 'h'
    assert boundary.bc_value == 2.5

    value = boundary.get_boundary_value()
    assert value == pytest.approx(2.5)

    print(" 边界条件设置测试通过")


# ============================================================================
# Convenience Functions Tests
# ============================================================================

@pytest.mark.p3
def test_convenience_functions():
    """测试便捷函数"""
    junction = create_junction("J1", elevation=90.0, method='energy')
    assert isinstance(junction, JunctionNode)
    assert junction.junction_method == 'energy'

    bifurc = create_bifurcation("B1", split_ratios=[0.4, 0.6])
    assert isinstance(bifurc, BifurcationNode)
    assert bifurc.split_ratios == [0.4, 0.6]

    reservoir = create_reservoir("R1", area=2e6)
    assert isinstance(reservoir, ReservoirNode)
    assert reservoir.area == 2e6

    inflow = create_inflow_boundary("IN1", Q=50.0)
    assert isinstance(inflow, BoundaryNode)
    assert inflow.boundary_type == 'inflow'
    assert inflow.bc_variable == 'Q'

    outflow = create_outflow_boundary("OUT1", h=2.0)
    assert isinstance(outflow, BoundaryNode)
    assert outflow.boundary_type == 'outflow'
    assert outflow.bc_variable == 'h'

    print(" 便捷函数测试通过")


if __name__ == "__main__":
    """直接运行测试"""
    print("="*80)
    print("节点类型测试 - Stage 3 Task 3.1.2")
    print("="*80)

    try:
        # JunctionNode tests
        print("\n【汇流节点测试】")
        test_junction_node_creation()
        test_junction_invalid_method()
        test_junction_average_method()
        test_junction_energy_method()
        test_junction_distribute_outflow()

        # BifurcationNode tests
        print("\n【分流节点测试】")
        test_bifurcation_node_creation()
        test_bifurcation_invalid_ratios()
        test_bifurcation_fixed_split()
        test_bifurcation_dynamic_split()
        test_bifurcation_set_ratios()

        # ReservoirNode tests
        print("\n【水库节点测试】")
        test_reservoir_node_creation()
        test_reservoir_compute_volume()
        test_reservoir_update_volume()
        test_reservoir_limits()
        test_reservoir_custom_storage_curve()

        # BoundaryNode tests
        print("\n【边界节点测试】")
        test_boundary_node_creation()
        test_boundary_invalid_type()
        test_boundary_constant_value()
        test_boundary_time_varying()
        test_boundary_rating_curve()
        test_boundary_set_condition()

        # Convenience functions
        print("\n【便捷函数测试】")
        test_convenience_functions()

        print("\n" + "="*80)
        print(" 所有节点类型测试通过！")
        print("="*80)

        print("\n总结:")
        print("  1.  JunctionNode - 汇流节点（能量/动量/平均）")
        print("  2.  BifurcationNode - 分流节点（固定/动态）")
        print("  3.  ReservoirNode - 水库节点（蓄水平衡）")
        print("  4.  BoundaryNode - 边界节点（Q/h/Rating Curve）")
        print("  5.  便捷函数 - create_*")
        print("\nTask 3.1.2 测试完成！")

    except Exception as e:
        print(f"\n 测试失败: {e}")
        import traceback
        traceback.print_exc()
        exit(1)
