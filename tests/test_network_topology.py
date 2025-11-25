"""
网络拓扑测试

测试network.topology模块的功能：
1. 节点添加和管理
2. 河段添加和管理
3. 拓扑排序
4. 拓扑验证
5. 质量平衡检查

Stage 3 - Task 3.1.1 测试

作者: HydroClaude Team
日期: 2025-10-29
"""

import pytest
import warnings
warnings.filterwarnings("ignore")
import numpy as np
import sys
import os

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from network.topology import Node, Reach, RiverNetwork


# Mock solver for testing
class MockSolver:
    """模拟求解器用于测试"""
    def __init__(self, length=100.0, n_cells=12):
        self.length = length
        self.n_cells = n_cells
        self.h = np.ones(n_cells) * 2.0
        self.Q = np.ones(n_cells) * 10.0
        self.dt = 1.0


@pytest.mark.p1
def test_node_creation():
    """测试节点创建"""
    node = Node("N1", "junction", elevation=100.0, x=0.0, y=0.0)

    assert node.id == "N1"
    assert node.type == "junction"
    assert node.elevation == 100.0
    assert node.x == 0.0
    assert node.y == 0.0
    assert node.h is None
    assert len(node.Q_in) == 0
    assert len(node.Q_out) == 0

    print(" 节点创建测试通过")


@pytest.mark.p1
def test_node_invalid_type():
    """测试无效节点类型"""
    with pytest.raises(ValueError, match="Invalid node type"):
        Node("N1", "invalid_type")

    print(" 无效节点类型检测通过")


@pytest.mark.p1
def test_node_mass_balance():
    """测试节点质量平衡检查"""
    node = Node("N1", "junction")

    # 平衡情况
    node.Q_in = [10.0, 5.0]
    node.Q_out = [15.0]

    is_balanced, error = node.check_mass_balance()
    assert is_balanced
    assert error < 1e-6

    # 不平衡情况
    node.Q_out = [10.0]
    is_balanced, error = node.check_mass_balance()
    assert not is_balanced
    assert error == pytest.approx(5.0)

    # 相对误差
    error_percent = node.get_mass_balance_error()
    assert error_percent == pytest.approx(33.33, abs=0.1)

    print(" 节点质量平衡检查通过")


@pytest.mark.p1
def test_reach_creation():
    """测试河段创建"""
    solver = MockSolver(length=500.0, n_cells=60)
    reach = Reach("R1", "N1", "N2", solver)

    assert reach.id == "R1"
    assert reach.upstream == "N1"
    assert reach.downstream == "N2"
    assert reach.length == 500.0
    assert reach.solver is solver

    print(" 河段创建测试通过")


@pytest.mark.p1
def test_reach_get_values():
    """测试河段获取水力参数"""
    solver = MockSolver()
    solver.h = np.array([2.5, 2.0, 1.8, 1.5])
    solver.Q = np.array([12.0, 11.0, 10.5, 10.0])

    reach = Reach("R1", "N1", "N2", solver)

    assert reach.get_upstream_h() == pytest.approx(2.5)
    assert reach.get_downstream_h() == pytest.approx(1.5)
    assert reach.get_upstream_Q() == pytest.approx(12.0)
    assert reach.get_downstream_Q() == pytest.approx(10.0)
    assert reach.get_average_h() == pytest.approx(1.95)
    assert reach.get_average_Q() == pytest.approx(10.875)

    print(" 河段水力参数获取测试通过")


@pytest.mark.p1
def test_network_creation():
    """测试河网创建"""
    network = RiverNetwork("Test Network")

    assert network.name == "Test Network"
    assert len(network.nodes) == 0
    assert len(network.reaches) == 0
    assert len(network.adjacency) == 0

    print(" 河网创建测试通过")


@pytest.mark.p1
def test_network_add_node():
    """测试添加节点"""
    network = RiverNetwork()

    node1 = Node("N1", "boundary")
    node2 = Node("N2", "junction")

    network.add_node(node1)
    network.add_node(node2)

    assert len(network.nodes) == 2
    assert "N1" in network.nodes
    assert "N2" in network.nodes

    # 重复添加应该报错
    with pytest.raises(ValueError, match="already exists"):
        network.add_node(node1)

    print(" 添加节点测试通过")


@pytest.mark.p2
def test_network_add_reach():
    """测试添加河段"""
    network = RiverNetwork()

    # 先添加节点
    network.add_node(Node("N1", "boundary"))
    network.add_node(Node("N2", "boundary"))

    # 添加河段
    solver = MockSolver()
    reach = Reach("R1", "N1", "N2", solver)
    network.add_reach(reach)

    assert len(network.reaches) == 1
    assert "R1" in network.reaches

    # 检查连接信息更新
    assert "R1" in network.nodes["N1"].downstream_reaches
    assert "R1" in network.nodes["N2"].upstream_reaches
    assert "R1" in network.adjacency["N1"]

    print(" 添加河段测试通过")


@pytest.mark.p2
def test_network_add_reach_missing_node():
    """测试添加河段时节点不存在"""
    network = RiverNetwork()
    network.add_node(Node("N1", "boundary"))

    solver = MockSolver()
    reach = Reach("R1", "N1", "N2", solver)

    with pytest.raises(ValueError, match="not found"):
        network.add_reach(reach)

    print(" 河段添加节点检查通过")


@pytest.mark.p2
def test_simple_network_topology():
    """测试简单串联网络拓扑"""
    network = RiverNetwork("Simple Serial Network")

    # 3节点2河段串联: N1 -> R1 -> N2 -> R2 -> N3
    network.add_node(Node("N1", "boundary", elevation=100.0))
    network.add_node(Node("N2", "junction", elevation=95.0))
    network.add_node(Node("N3", "boundary", elevation=90.0))

    solver1 = MockSolver()
    solver2 = MockSolver()

    network.add_reach(Reach("R1", "N1", "N2", solver1))
    network.add_reach(Reach("R2", "N2", "N3", solver2))

    # 构建拓扑
    order = network.build_topology()

    # 拓扑顺序应该是 R1, R2
    assert order == ["R1", "R2"]
    assert network.topological_order == ["R1", "R2"]

    print(" 简单串联网络拓扑测试通过")


@pytest.mark.p2
def test_y_junction_topology():
    """测试Y型汇流网络拓扑"""
    network = RiverNetwork("Y-Junction Network")

    # Y型: N1 -> R1 -> N3
    #      N2 -> R2 -> N3 -> R3 -> N4

    network.add_node(Node("N1", "boundary", elevation=100.0))
    network.add_node(Node("N2", "boundary", elevation=100.0))
    network.add_node(Node("N3", "junction", elevation=95.0))
    network.add_node(Node("N4", "boundary", elevation=90.0))

    s1, s2, s3 = MockSolver(), MockSolver(), MockSolver()

    network.add_reach(Reach("R1", "N1", "N3", s1))
    network.add_reach(Reach("R2", "N2", "N3", s2))
    network.add_reach(Reach("R3", "N3", "N4", s3))

    order = network.build_topology()

    # R1和R2的顺序可能不确定，但都应该在R3之前
    assert "R3" in order
    assert order.index("R1") < order.index("R3")
    assert order.index("R2") < order.index("R3")

    print(" Y型汇流网络拓扑测试通过")


@pytest.mark.p2
def test_cycle_detection():
    """测试环路检测"""
    network = RiverNetwork()

    # 创建环路: N1 -> R1 -> N2 -> R2 -> N3 -> R3 -> N1
    network.add_node(Node("N1", "junction"))
    network.add_node(Node("N2", "junction"))
    network.add_node(Node("N3", "junction"))

    s1, s2, s3 = MockSolver(), MockSolver(), MockSolver()

    network.add_reach(Reach("R1", "N1", "N2", s1))
    network.add_reach(Reach("R2", "N2", "N3", s2))
    network.add_reach(Reach("R3", "N3", "N1", s3))  # 形成环路

    # 应该检测到环路
    with pytest.raises(ValueError, match="Cycle detected"):
        network.build_topology()

    print(" 环路检测测试通过")


@pytest.mark.p2
def test_get_boundary_nodes():
    """测试获取边界节点"""
    network = RiverNetwork()

    # 创建网络: N1 -> R1 -> N2 -> R2 -> N3
    #          N4 -> R3 -> N2
    network.add_node(Node("N1", "boundary"))
    network.add_node(Node("N2", "junction"))
    network.add_node(Node("N3", "boundary"))
    network.add_node(Node("N4", "boundary"))

    s1, s2, s3 = MockSolver(), MockSolver(), MockSolver()

    network.add_reach(Reach("R1", "N1", "N2", s1))
    network.add_reach(Reach("R2", "N2", "N3", s2))
    network.add_reach(Reach("R3", "N4", "N2", s3))

    upstream = network.get_upstream_nodes()
    downstream = network.get_downstream_nodes()

    # 上游节点: N1, N4 (没有上游河段)
    assert len(upstream) == 2
    assert network.nodes["N1"] in upstream
    assert network.nodes["N4"] in upstream

    # 下游节点: N3 (没有下游河段)
    assert len(downstream) == 1
    assert network.nodes["N3"] in downstream

    print(" 边界节点获取测试通过")


@pytest.mark.p2
def test_get_junction_nodes():
    """测试获取汇流节点"""
    network = RiverNetwork()

    network.add_node(Node("N1", "boundary"))
    network.add_node(Node("N2", "junction"))
    network.add_node(Node("N3", "junction"))
    network.add_node(Node("N4", "boundary"))

    s1, s2, s3 = MockSolver(), MockSolver(), MockSolver()

    network.add_reach(Reach("R1", "N1", "N2", s1))
    network.add_reach(Reach("R2", "N1", "N3", s2))
    network.add_reach(Reach("R3", "N2", "N4", s3))

    # N3 有1个上游河段，不算汇流
    # N2 有1个上游河段，不算汇流
    junctions = network.get_junction_nodes()
    assert len(junctions) == 0

    # 添加第二条河段到N2
    network.add_reach(Reach("R4", "N3", "N2", MockSolver()))

    junctions = network.get_junction_nodes()
    assert len(junctions) == 1
    assert network.nodes["N2"] in junctions

    print(" 汇流节点获取测试通过")


@pytest.mark.p3
def test_validate_topology():
    """测试拓扑验证"""
    # 空网络
    network = RiverNetwork()
    is_valid, errors = network.validate_topology()
    assert not is_valid
    assert len(errors) > 0

    # 孤立节点
    network.add_node(Node("N1", "boundary"))
    is_valid, errors = network.validate_topology()
    assert not is_valid
    assert any("Isolated" in e for e in errors)

    # 正常网络
    network.add_node(Node("N2", "boundary"))
    network.add_reach(Reach("R1", "N1", "N2", MockSolver()))
    is_valid, errors = network.validate_topology()
    assert is_valid
    assert len(errors) == 0

    print(" 拓扑验证测试通过")


@pytest.mark.p3
def test_global_mass_balance():
    """测试全局质量平衡"""
    network = RiverNetwork()

    # 创建简单网络
    network.add_node(Node("N1", "boundary"))
    network.add_node(Node("N2", "boundary"))

    solver = MockSolver()
    solver.Q = np.array([10.0, 10.0, 10.0])  # 恒定流量

    network.add_reach(Reach("R1", "N1", "N2", solver))
    network.build_topology()

    Q_in, Q_out, error = network.check_global_mass_balance()

    assert Q_in == pytest.approx(10.0)
    assert Q_out == pytest.approx(10.0)
    assert error < 0.01  # < 0.01%

    print(" 全局质量平衡测试通过")


if __name__ == "__main__":
    """直接运行测试"""
    print("="*80)
    print("网络拓扑模块测试 - Stage 3 Task 3.1.1")
    print("="*80)

    try:
        # P1 tests
        test_node_creation()
        test_node_invalid_type()
        test_node_mass_balance()
        test_reach_creation()
        test_reach_get_values()
        test_network_creation()
        test_network_add_node()

        # P2 tests
        test_network_add_reach()
        test_network_add_reach_missing_node()
        test_simple_network_topology()
        test_y_junction_topology()
        test_cycle_detection()
        test_get_boundary_nodes()
        test_get_junction_nodes()

        # P3 tests
        test_validate_topology()
        test_global_mass_balance()

        print("\n" + "="*80)
        print(" 所有网络拓扑测试通过！")
        print("="*80)

        print("\n总结:")
        print("  1.  节点管理（创建、验证、质量平衡）")
        print("  2.  河段管理（创建、参数获取）")
        print("  3.  网络拓扑（添加、拓扑排序、验证）")
        print("  4.  边界节点识别（上游、下游、汇流）")
        print("  5.  环路检测")
        print("  6.  质量平衡检查")
        print("\nTask 3.1.1 完成！")

    except Exception as e:
        print(f"\n 测试失败: {e}")
        import traceback
        traceback.print_exc()
        exit(1)
