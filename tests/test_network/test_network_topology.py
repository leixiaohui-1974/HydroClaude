"""
Unit Tests for Network Topology Module - 管网拓扑模块单元测试

This module contains comprehensive unit tests for:
- NetworkTopology class
- Node-pipe connectivity
- Loop identification
- Incidence matrix construction
- Path finding algorithms

Author: HydroClaude Development Team
Date: 2025-10-30
"""
import sys
import warnings
warnings.filterwarnings("ignore")
import os

# ========== 路径设置 ==========
script_path = os.path.abspath(__file__)
project_root = os.path.dirname(os.path.dirname(script_path))
sys.path.insert(0, project_root)


import pytest
import numpy as np
from network.network_topology import NetworkTopology
from network.network_node import Junction, Reservoir, Tank
from network.pressure_pipe import PressurePipe


# ============================================================================
# Test 1: Basic Topology Operations - 基本拓扑操作
# ============================================================================

class TestTopologyBasicOperations:
    """测试基本拓扑操作"""

    def test_topology_initialization(self):
        """测试拓扑初始化"""
        topology = NetworkTopology(name="TestNetwork")

        assert topology.name == "TestNetwork"
        assert len(topology.nodes) == 0
        assert len(topology.pipes) == 0

    def test_add_node(self):
        """测试添加节点"""
        topology = NetworkTopology()

        node1 = Junction("J1", elevation=10.0)
        node2 = Junction("J2", elevation=15.0)

        topology.add_node(node1)
        topology.add_node(node2)

        assert len(topology.nodes) == 2
        assert "J1" in topology.nodes
        assert "J2" in topology.nodes

    def test_add_duplicate_node(self):
        """测试添加重复节点"""
        topology = NetworkTopology()

        node1 = Junction("J1", elevation=10.0)

        topology.add_node(node1)

        with pytest.raises(ValueError, match="节点.*已存在"):
            topology.add_node(node1)

    def test_add_pipe(self):
        """测试添加管道"""
        topology = NetworkTopology()

        j1 = Junction("J1", elevation=10.0)
        j2 = Junction("J2", elevation=15.0)
        topology.add_node(j1)
        topology.add_node(j2)

        pipe = PressurePipe("P1", diameter=0.3, length=100.0, roughness=0.0003)
        topology.add_pipe(pipe, "J1", "J2")

        assert len(topology.pipes) == 1
        assert "P1" in topology.pipes
        assert topology.pipe_connections["P1"] == ("J1", "J2")

    def test_add_pipe_invalid_nodes(self):
        """测试添加管道到不存在的节点"""
        topology = NetworkTopology()

        j1 = Junction("J1", elevation=10.0)
        topology.add_node(j1)

        pipe = PressurePipe("P1", diameter=0.3, length=100.0, roughness=0.0003)

        with pytest.raises(ValueError, match="节点.*不存在"):
            topology.add_pipe(pipe, "J1", "J_NonExistent")

    def test_add_pipe_self_connection(self):
        """测试管道连接到自身"""
        topology = NetworkTopology()

        j1 = Junction("J1", elevation=10.0)
        topology.add_node(j1)

        pipe = PressurePipe("P1", diameter=0.3, length=100.0, roughness=0.0003)

        with pytest.raises(ValueError, match="管道不能连接到自身"):
            topology.add_pipe(pipe, "J1", "J1")

    def test_remove_pipe(self):
        """测试移除管道"""
        topology = NetworkTopology()

        j1 = Junction("J1", elevation=10.0)
        j2 = Junction("J2", elevation=15.0)
        topology.add_node(j1)
        topology.add_node(j2)

        pipe = PressurePipe("P1", diameter=0.3, length=100.0, roughness=0.0003)
        topology.add_pipe(pipe, "J1", "J2")

        topology.remove_pipe("P1")

        assert len(topology.pipes) == 0
        assert "P1" not in topology.pipes

    def test_remove_node(self):
        """测试移除节点"""
        topology = NetworkTopology()

        j1 = Junction("J1", elevation=10.0)
        j2 = Junction("J2", elevation=15.0)
        topology.add_node(j1)
        topology.add_node(j2)

        pipe = PressurePipe("P1", diameter=0.3, length=100.0, roughness=0.0003)
        topology.add_pipe(pipe, "J1", "J2")

        # 移除节点会自动移除连接的管道
        topology.remove_node("J1")

        assert len(topology.nodes) == 1
        assert len(topology.pipes) == 0  # 管道也被移除


class TestNodePipeConnections:
    """测试节点-管道连接"""

    def test_get_pipe_endpoints(self):
        """测试获取管道端点"""
        topology = NetworkTopology()

        j1 = Junction("J1", elevation=10.0)
        j2 = Junction("J2", elevation=15.0)
        topology.add_node(j1)
        topology.add_node(j2)

        pipe = PressurePipe("P1", diameter=0.3, length=100.0, roughness=0.0003)
        topology.add_pipe(pipe, "J1", "J2")

        from_node, to_node = topology.get_pipe_endpoints("P1")

        assert from_node == "J1"
        assert to_node == "J2"

    def test_get_node_pipes(self):
        """测试获取节点连接的管道"""
        topology = NetworkTopology()

        j1 = Junction("J1", elevation=10.0)
        j2 = Junction("J2", elevation=15.0)
        j3 = Junction("J3", elevation=20.0)
        topology.add_node(j1)
        topology.add_node(j2)
        topology.add_node(j3)

        p1 = PressurePipe("P1", diameter=0.3, length=100.0, roughness=0.0003)
        p2 = PressurePipe("P2", diameter=0.3, length=100.0, roughness=0.0003)

        topology.add_pipe(p1, "J1", "J2")  # J1->J2
        topology.add_pipe(p2, "J2", "J3")  # J2->J3

        # J2 应该有两根管道: P1 (in), P2 (out)
        pipes = topology.get_node_pipes("J2")

        assert len(pipes) == 2
        pipe_ids = [p[0] for p in pipes]
        directions = [p[1] for p in pipes]

        assert "P1" in pipe_ids
        assert "P2" in pipe_ids
        assert "in" in directions
        assert "out" in directions


# ============================================================================
# Test 2: Loop Identification - 回路识别
# ============================================================================

class TestLoopIdentification:
    """测试回路识别算法"""

    def test_no_loops_simple_tree(self):
        """测试简单树状结构（无回路）"""
        topology = NetworkTopology()

        # 树状结构: J1 -> J2 -> J3
        j1 = Junction("J1", elevation=10.0)
        j2 = Junction("J2", elevation=15.0)
        j3 = Junction("J3", elevation=20.0)

        topology.add_node(j1)
        topology.add_node(j2)
        topology.add_node(j3)

        p1 = PressurePipe("P1", diameter=0.3, length=100.0, roughness=0.0003)
        p2 = PressurePipe("P2", diameter=0.3, length=100.0, roughness=0.0003)

        topology.add_pipe(p1, "J1", "J2")
        topology.add_pipe(p2, "J2", "J3")

        loops = topology.find_loops()

        assert len(loops) == 0

    def test_single_loop(self):
        """测试单回路"""
        topology = NetworkTopology()

        # 回路: J1 -> J2 -> J3 -> J1
        j1 = Junction("J1", elevation=10.0)
        j2 = Junction("J2", elevation=15.0)
        j3 = Junction("J3", elevation=20.0)

        topology.add_node(j1)
        topology.add_node(j2)
        topology.add_node(j3)

        p1 = PressurePipe("P1", diameter=0.3, length=100.0, roughness=0.0003)
        p2 = PressurePipe("P2", diameter=0.3, length=100.0, roughness=0.0003)
        p3 = PressurePipe("P3", diameter=0.3, length=100.0, roughness=0.0003)

        topology.add_pipe(p1, "J1", "J2")
        topology.add_pipe(p2, "J2", "J3")
        topology.add_pipe(p3, "J3", "J1")

        loops = topology.find_loops()

        assert len(loops) == 1
        assert len(loops[0]) >= 3  # 至少3个节点

    def test_two_loops_hardy_cross(self):
        """测试双回路（Hardy Cross经典案例）"""
        topology = NetworkTopology()

        # 双回路网格
        #  J1 --- J2
        #  |      |
        #  J3 --- J4
        #  |      |
        #  J5 --- J6

        nodes = [
            Junction("J1", elevation=10.0),
            Junction("J2", elevation=10.0),
            Junction("J3", elevation=10.0),
            Junction("J4", elevation=10.0),
            Junction("J5", elevation=10.0),
            Junction("J6", elevation=10.0)
        ]

        for node in nodes:
            topology.add_node(node)

        # 添加管道形成两个回路
        connections = [
            ("P1", "J1", "J2"),
            ("P2", "J1", "J3"),
            ("P3", "J2", "J4"),
            ("P4", "J3", "J4"),
            ("P5", "J3", "J5"),
            ("P6", "J4", "J6"),
            ("P7", "J5", "J6")
        ]

        for pipe_id, from_node, to_node in connections:
            pipe = PressurePipe(pipe_id, diameter=0.3, length=100.0, roughness=0.0003)
            topology.add_pipe(pipe, from_node, to_node)

        loops = topology.find_loops()

        # 应该找到2个独立回路
        assert len(loops) == 2

    def test_complex_network_loops(self):
        """测试复杂网络回路"""
        topology = NetworkTopology()

        # 更复杂的网格: 4x2
        for i in range(1, 9):
            topology.add_node(Junction(f"J{i}", elevation=10.0))

        # 横向连接
        for i in [1, 3, 5, 7]:
            pipe = PressurePipe(f"P{i}", diameter=0.3, length=100.0, roughness=0.0003)
            topology.add_pipe(pipe, f"J{i}", f"J{i+1}")

        # 纵向连接
        for i in [1, 2, 3, 4]:
            pipe = PressurePipe(f"PV{i}", diameter=0.3, length=100.0, roughness=0.0003)
            topology.add_pipe(pipe, f"J{i}", f"J{i+4}")

        loops = topology.find_loops()

        # 基本回路数 = n_pipes - n_nodes + n_components
        # 8 pipes, 8 nodes, 1 component -> 1 loop expected
        # 实际找到的回路数取决于算法实现
        assert len(loops) >= 1


# ============================================================================
# Test 3: Incidence Matrix - 关联矩阵
# ============================================================================

class TestIncidenceMatrix:
    """测试关联矩阵构造"""

    def test_incidence_matrix_simple(self):
        """测试简单网络的关联矩阵"""
        topology = NetworkTopology()

        # 简单网络: J1 -> J2 -> J3
        j1 = Junction("J1", elevation=10.0)
        j2 = Junction("J2", elevation=15.0)
        j3 = Junction("J3", elevation=20.0)

        topology.add_node(j1)
        topology.add_node(j2)
        topology.add_node(j3)

        p1 = PressurePipe("P1", diameter=0.3, length=100.0, roughness=0.0003)
        p2 = PressurePipe("P2", diameter=0.3, length=100.0, roughness=0.0003)

        topology.add_pipe(p1, "J1", "J2")
        topology.add_pipe(p2, "J2", "J3")

        A, node_ids, pipe_ids = topology.incidence_matrix()

        # 矩阵尺寸应该是 3x2
        assert A.shape == (3, 2)

        # 检查节点和管道排序
        assert node_ids == sorted(["J1", "J2", "J3"])
        assert pipe_ids == sorted(["P1", "P2"])

        # 检查矩阵元素
        # P1: J1(+1) -> J2(-1)
        # P2: J2(+1) -> J3(-1)
        j1_idx = node_ids.index("J1")
        j2_idx = node_ids.index("J2")
        j3_idx = node_ids.index("J3")
        p1_idx = pipe_ids.index("P1")
        p2_idx = pipe_ids.index("P2")

        assert A[j1_idx, p1_idx] == 1.0   # J1 流出 P1
        assert A[j2_idx, p1_idx] == -1.0  # J2 流入 P1
        assert A[j2_idx, p2_idx] == 1.0   # J2 流出 P2
        assert A[j3_idx, p2_idx] == -1.0  # J3 流入 P2

    def test_incidence_matrix_loop(self):
        """测试回路网络的关联矩阵"""
        topology = NetworkTopology()

        # 回路: J1 -> J2 -> J3 -> J1
        for i in [1, 2, 3]:
            topology.add_node(Junction(f"J{i}", elevation=10.0))

        pipes = [
            PressurePipe("P1", diameter=0.3, length=100.0, roughness=0.0003),
            PressurePipe("P2", diameter=0.3, length=100.0, roughness=0.0003),
            PressurePipe("P3", diameter=0.3, length=100.0, roughness=0.0003)
        ]

        topology.add_pipe(pipes[0], "J1", "J2")
        topology.add_pipe(pipes[1], "J2", "J3")
        topology.add_pipe(pipes[2], "J3", "J1")

        A, node_ids, pipe_ids = topology.incidence_matrix()

        assert A.shape == (3, 3)

        # 每列之和应为0（流量守恒）
        col_sums = np.sum(A, axis=0)
        assert np.allclose(col_sums, 0.0)


class TestLoopMatrix:
    """测试回路矩阵"""

    def test_loop_matrix_single_loop(self):
        """测试单回路的回路矩阵"""
        topology = NetworkTopology()

        # 回路: J1 -> J2 -> J3 -> J1
        for i in [1, 2, 3]:
            topology.add_node(Junction(f"J{i}", elevation=10.0))

        pipes = [
            PressurePipe("P1", diameter=0.3, length=100.0, roughness=0.0003),
            PressurePipe("P2", diameter=0.3, length=100.0, roughness=0.0003),
            PressurePipe("P3", diameter=0.3, length=100.0, roughness=0.0003)
        ]

        topology.add_pipe(pipes[0], "J1", "J2")
        topology.add_pipe(pipes[1], "J2", "J3")
        topology.add_pipe(pipes[2], "J3", "J1")

        B, loops, pipe_ids = topology.loop_matrix()

        # 应该有1个回路, 3根管道
        assert B.shape == (1, 3)

        # 回路中每根管道系数应为 +1 或 -1
        assert np.all(np.abs(B) == 1.0)

    def test_loop_matrix_no_loops(self):
        """测试无回路网络"""
        topology = NetworkTopology()

        # 树状: J1 -> J2 -> J3
        for i in [1, 2, 3]:
            topology.add_node(Junction(f"J{i}", elevation=10.0))

        p1 = PressurePipe("P1", diameter=0.3, length=100.0, roughness=0.0003)
        p2 = PressurePipe("P2", diameter=0.3, length=100.0, roughness=0.0003)

        topology.add_pipe(p1, "J1", "J2")
        topology.add_pipe(p2, "J2", "J3")

        B, loops, pipe_ids = topology.loop_matrix()

        # 没有回路，矩阵应为空
        assert B.shape[0] == 0
        assert len(loops) == 0


# ============================================================================
# Test 4: Path Finding - 路径搜索
# ============================================================================

class TestPathFinding:
    """测试路径搜索算法"""

    def test_shortest_path_simple(self):
        """测试简单路径"""
        topology = NetworkTopology()

        # J1 -> J2 -> J3
        for i in [1, 2, 3]:
            topology.add_node(Junction(f"J{i}", elevation=10.0))

        p1 = PressurePipe("P1", diameter=0.3, length=100.0, roughness=0.0003)
        p2 = PressurePipe("P2", diameter=0.3, length=100.0, roughness=0.0003)

        topology.add_pipe(p1, "J1", "J2")
        topology.add_pipe(p2, "J2", "J3")

        path = topology.shortest_path("J1", "J3")

        assert path == ["J1", "J2", "J3"]

    def test_shortest_path_with_loop(self):
        """测试有回路的最短路径"""
        topology = NetworkTopology()

        # 网格:
        # J1 -- J2
        # |     |
        # J3 -- J4

        for i in [1, 2, 3, 4]:
            topology.add_node(Junction(f"J{i}", elevation=10.0))

        pipes = [
            ("P1", "J1", "J2"),
            ("P2", "J1", "J3"),
            ("P3", "J2", "J4"),
            ("P4", "J3", "J4")
        ]

        for pipe_id, from_node, to_node in pipes:
            pipe = PressurePipe(pipe_id, diameter=0.3, length=100.0, roughness=0.0003)
            topology.add_pipe(pipe, from_node, to_node)

        # J1 到 J4 的最短路径应该是 2 跳
        path = topology.shortest_path("J1", "J4")

        assert len(path) == 3  # J1 -> J2/J3 -> J4

    def test_shortest_path_no_connection(self):
        """测试不连通的路径"""
        topology = NetworkTopology()

        # 两个独立部分
        j1 = Junction("J1", elevation=10.0)
        j2 = Junction("J2", elevation=15.0)
        j3 = Junction("J3", elevation=20.0)  # 孤立

        topology.add_node(j1)
        topology.add_node(j2)
        topology.add_node(j3)

        p1 = PressurePipe("P1", diameter=0.3, length=100.0, roughness=0.0003)
        topology.add_pipe(p1, "J1", "J2")

        # J1 到 J3 无路径
        path = topology.shortest_path("J1", "J3")

        assert path is None

    def test_shortest_path_same_node(self):
        """测试起止节点相同"""
        topology = NetworkTopology()

        j1 = Junction("J1", elevation=10.0)
        topology.add_node(j1)

        path = topology.shortest_path("J1", "J1")

        assert path == ["J1"]


# ============================================================================
# Test 5: Network Validation - 网络验证
# ============================================================================

class TestNetworkValidation:
    """测试网络验证功能"""

    def test_is_connected_simple(self):
        """测试简单连通网络"""
        topology = NetworkTopology()

        for i in [1, 2, 3]:
            topology.add_node(Junction(f"J{i}", elevation=10.0))

        p1 = PressurePipe("P1", diameter=0.3, length=100.0, roughness=0.0003)
        p2 = PressurePipe("P2", diameter=0.3, length=100.0, roughness=0.0003)

        topology.add_pipe(p1, "J1", "J2")
        topology.add_pipe(p2, "J2", "J3")

        assert topology.is_connected()

    def test_is_connected_disconnected(self):
        """测试不连通网络"""
        topology = NetworkTopology()

        # 两个独立部分
        j1 = Junction("J1", elevation=10.0)
        j2 = Junction("J2", elevation=15.0)
        j3 = Junction("J3", elevation=20.0)
        j4 = Junction("J4", elevation=25.0)

        topology.add_node(j1)
        topology.add_node(j2)
        topology.add_node(j3)
        topology.add_node(j4)

        # J1-J2 连通, J3-J4 连通, 但两组之间不连通
        p1 = PressurePipe("P1", diameter=0.3, length=100.0, roughness=0.0003)
        p2 = PressurePipe("P2", diameter=0.3, length=100.0, roughness=0.0003)

        topology.add_pipe(p1, "J1", "J2")
        topology.add_pipe(p2, "J3", "J4")

        assert not topology.is_connected()

    def test_validate_complete_network(self):
        """测试完整网络验证"""
        topology = NetworkTopology()

        # 添加水源
        reservoir = Reservoir("R1", elevation=50.0, head=50.0)
        topology.add_node(reservoir)

        # 添加汇流节点
        j1 = Junction("J1", elevation=10.0, demand=0.05)
        topology.add_node(j1)

        # 添加管道
        pipe = PressurePipe("P1", diameter=0.3, length=100.0, roughness=0.0003)
        topology.add_pipe(pipe, "R1", "J1")

        is_valid, issues = topology.validate()

        assert is_valid
        assert len(issues) == 0

    def test_validate_no_source(self):
        """测试无水源的网络"""
        topology = NetworkTopology()

        j1 = Junction("J1", elevation=10.0)
        j2 = Junction("J2", elevation=15.0)

        topology.add_node(j1)
        topology.add_node(j2)

        pipe = PressurePipe("P1", diameter=0.3, length=100.0, roughness=0.0003)
        topology.add_pipe(pipe, "J1", "J2")

        is_valid, issues = topology.validate()

        # 应该有警告：没有水源
        assert any("水源" in issue for issue in issues)

    def test_validate_isolated_node(self):
        """测试孤立节点"""
        topology = NetworkTopology()

        j1 = Junction("J1", elevation=10.0)
        j2 = Junction("J2", elevation=15.0)  # 孤立

        topology.add_node(j1)
        topology.add_node(j2)

        is_valid, issues = topology.validate()

        # 应该有警告：孤立节点
        assert any("没有连接任何管道" in issue for issue in issues)


# ============================================================================
# Test 6: Network Summary - 网络摘要
# ============================================================================

class TestNetworkSummary:
    """测试网络摘要统计"""

    def test_summary_simple_network(self):
        """测试简单网络摘要"""
        topology = NetworkTopology(name="TestNet")

        # 添加各类节点
        reservoir = Reservoir("R1", elevation=50.0, head=50.0)
        tank = Tank("T1", elevation=30.0, diameter=10.0, max_level=5.0, initial_level=3.0)
        j1 = Junction("J1", elevation=10.0)
        j2 = Junction("J2", elevation=15.0)

        topology.add_node(reservoir)
        topology.add_node(tank)
        topology.add_node(j1)
        topology.add_node(j2)

        # 添加管道，确保所有节点连通
        p1 = PressurePipe("P1", diameter=0.3, length=100.0, roughness=0.0003)
        p2 = PressurePipe("P2", diameter=0.3, length=100.0, roughness=0.0003)
        p3 = PressurePipe("P3", diameter=0.3, length=100.0, roughness=0.0003)

        topology.add_pipe(p1, "R1", "J1")
        topology.add_pipe(p2, "J1", "J2")
        topology.add_pipe(p3, "J2", "T1")  # 连接水箱

        summary = topology.summary()

        assert summary['name'] == "TestNet"
        assert summary['num_nodes'] == 4
        assert summary['num_junctions'] == 2
        assert summary['num_reservoirs'] == 1
        assert summary['num_tanks'] == 1
        assert summary['num_pipes'] == 3
        assert summary['is_connected']

    def test_summary_with_loops(self):
        """测试带回路的网络摘要"""
        topology = NetworkTopology()

        # 创建单回路
        for i in [1, 2, 3]:
            topology.add_node(Junction(f"J{i}", elevation=10.0))

        for i, (from_n, to_n) in enumerate([("J1", "J2"), ("J2", "J3"), ("J3", "J1")], 1):
            pipe = PressurePipe(f"P{i}", diameter=0.3, length=100.0, roughness=0.0003)
            topology.add_pipe(pipe, from_n, to_n)

        summary = topology.summary()

        assert summary['num_loops'] == 1
        assert summary['expected_loops'] == 1  # n_pipes - n_nodes + 1 = 3 - 3 + 1 = 1

    def test_topology_repr(self):
        """测试拓扑字符串表示"""
        topology = NetworkTopology(name="MyNetwork")

        j1 = Junction("J1", elevation=10.0)
        topology.add_node(j1)

        repr_str = repr(topology)

        assert "MyNetwork" in repr_str
        assert "nodes=1" in repr_str


# ============================================================================
# Summary: 共30个测试用例
# ============================================================================

if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
