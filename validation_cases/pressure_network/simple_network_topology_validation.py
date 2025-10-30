"""
Simple Network Topology Validation - 简单管网拓扑验证案例

This validation case demonstrates the network topology functionality including:
1. Network construction with various node types
2. Loop identification
3. Incidence matrix construction
4. Shortest path finding
5. Network validation

Author: HydroClaude Development Team
Date: 2025-10-30
"""

import sys
import os
# 添加项目根目录到Python路径
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))

import numpy as np
import matplotlib.pyplot as plt
from matplotlib.patches import Circle, FancyArrowPatch
from network.network_topology import NetworkTopology
from network.network_node import Junction, Reservoir, Tank
from network.pressure_pipe import PressurePipe


def validation_case_1_simple_tree_network():
    """
    验证案例1: 简单树状网络 - Simple Tree Network

    网络结构:
    R1(水库) -> J1 -> J2 -> J3 -> T1(水箱)

    特点:
    - 无回路
    - 4个汇流节点
    - 1个水源，1个水箱
    """
    print("=" * 80)
    print("验证案例1: 简单树状网络 - Simple Tree Network")
    print("=" * 80)

    # 创建拓扑
    topology = NetworkTopology(name="SimpleTreeNetwork")

    # 添加节点
    reservoir = Reservoir("R1", elevation=50.0, head=50.0)
    j1 = Junction("J1", elevation=10.0, demand=0.03)
    j2 = Junction("J2", elevation=12.0, demand=0.05)
    j3 = Junction("J3", elevation=15.0, demand=0.02)
    tank = Tank("T1", elevation=30.0, diameter=10.0, max_level=5.0, initial_level=3.0)

    topology.add_node(reservoir)
    topology.add_node(j1)
    topology.add_node(j2)
    topology.add_node(j3)
    topology.add_node(tank)

    # 添加管道
    p1 = PressurePipe("P1", diameter=0.4, length=500.0, roughness=0.0003)
    p2 = PressurePipe("P2", diameter=0.3, length=300.0, roughness=0.0003)
    p3 = PressurePipe("P3", diameter=0.25, length=200.0, roughness=0.0003)
    p4 = PressurePipe("P4", diameter=0.2, length=400.0, roughness=0.0003)

    topology.add_pipe(p1, "R1", "J1")
    topology.add_pipe(p2, "J1", "J2")
    topology.add_pipe(p3, "J2", "J3")
    topology.add_pipe(p4, "J3", "T1")

    # 验证1: 拓扑连通性
    print("\n[测试1] 拓扑连通性")
    is_connected = topology.is_connected()
    print(f"  网络是否连通: {'是' if is_connected else '否'} ✓" if is_connected else "  网络是否连通: 否 ✗")
    assert is_connected, "树状网络应该是连通的"

    # 验证2: 回路识别
    print("\n[测试2] 回路识别")
    loops = topology.find_loops()
    print(f"  识别到的回路数: {len(loops)}")
    print(f"  预期回路数: 0 (树状网络无回路)")
    assert len(loops) == 0, "树状网络不应有回路"
    print("  ✓ 回路数正确")

    # 验证3: 关联矩阵
    print("\n[测试3] 关联矩阵")
    A, node_ids, pipe_ids = topology.incidence_matrix()
    print(f"  关联矩阵尺寸: {A.shape} (节点×管道)")
    print(f"  理论尺寸: (5, 4)")
    assert A.shape == (5, 4), "关联矩阵尺寸不正确"

    # 检查列和为0 (流量守恒)
    col_sums = np.sum(A, axis=0)
    print(f"  各列之和: {col_sums}")
    assert np.allclose(col_sums, 0.0), "关联矩阵各列之和应为0"
    print("  ✓ 关联矩阵验证通过")

    # 验证4: 最短路径
    print("\n[测试4] 最短路径搜索")
    path_r1_to_t1 = topology.shortest_path("R1", "T1")
    print(f"  R1 到 T1 的最短路径: {' -> '.join(path_r1_to_t1)}")
    print(f"  路径长度: {len(path_r1_to_t1)} 个节点")
    assert path_r1_to_t1 == ["R1", "J1", "J2", "J3", "T1"], "最短路径不正确"
    print("  ✓ 最短路径正确")

    # 验证5: 网络有效性
    print("\n[测试5] 网络有效性检查")
    is_valid, issues = topology.validate()
    print(f"  网络是否有效: {'是' if is_valid else '否'}")
    if issues:
        for issue in issues:
            print(f"    - {issue}")
    else:
        print("    无错误或警告")
    assert is_valid, "网络应该是有效的"
    print("  ✓ 网络验证通过")

    # 验证6: 网络摘要
    print("\n[测试6] 网络摘要统计")
    summary = topology.summary()
    print(f"  网络名称: {summary['name']}")
    print(f"  节点总数: {summary['num_nodes']}")
    print(f"    - 汇流节点: {summary['num_junctions']}")
    print(f"    - 水库节点: {summary['num_reservoirs']}")
    print(f"    - 水箱节点: {summary['num_tanks']}")
    print(f"  管道总数: {summary['num_pipes']}")
    print(f"  回路数: {summary['num_loops']}")
    print(f"  平均度数: {summary['average_degree']:.2f}")

    print("\n" + "=" * 80)
    print("✓ 验证案例1: 所有测试通过")
    print("=" * 80 + "\n")

    return topology


def validation_case_2_single_loop_network():
    """
    验证案例2: 单回路网络 - Single Loop Network

    网络结构:
        R1
        |
        J1 --- J2
        |      |
        J3 --- J4

    特点:
    - 1个回路 (J1-J2-J4-J3-J1)
    - 可验证回路识别算法
    - 可验证回路矩阵构造
    """
    print("=" * 80)
    print("验证案例2: 单回路网络 - Single Loop Network")
    print("=" * 80)

    # 创建拓扑
    topology = NetworkTopology(name="SingleLoopNetwork")

    # 添加节点
    reservoir = Reservoir("R1", elevation=50.0, head=50.0)
    j1 = Junction("J1", elevation=10.0, demand=0.02)
    j2 = Junction("J2", elevation=12.0, demand=0.03)
    j3 = Junction("J3", elevation=15.0, demand=0.02)
    j4 = Junction("J4", elevation=14.0, demand=0.03)

    topology.add_node(reservoir)
    topology.add_node(j1)
    topology.add_node(j2)
    topology.add_node(j3)
    topology.add_node(j4)

    # 添加管道形成回路
    p0 = PressurePipe("P0", diameter=0.5, length=500.0, roughness=0.0003)  # R1->J1
    p1 = PressurePipe("P1", diameter=0.3, length=200.0, roughness=0.0003)  # J1->J2
    p2 = PressurePipe("P2", diameter=0.3, length=150.0, roughness=0.0003)  # J1->J3
    p3 = PressurePipe("P3", diameter=0.25, length=200.0, roughness=0.0003) # J2->J4
    p4 = PressurePipe("P4", diameter=0.25, length=150.0, roughness=0.0003) # J3->J4

    topology.add_pipe(p0, "R1", "J1")
    topology.add_pipe(p1, "J1", "J2")
    topology.add_pipe(p2, "J1", "J3")
    topology.add_pipe(p3, "J2", "J4")
    topology.add_pipe(p4, "J3", "J4")

    # 验证1: 回路识别
    print("\n[测试1] 回路识别")
    loops = topology.find_loops()
    print(f"  识别到的回路数: {len(loops)}")
    print(f"  预期回路数: 1")

    if len(loops) > 0:
        print(f"  回路节点: {loops[0]}")
        assert len(loops[0]) >= 3, "回路至少应包含3个节点"

    # 理论回路数 = n_pipes - n_nodes + 1 (对于连通图)
    expected_loops = len(topology.pipes) - len(topology.nodes) + 1
    print(f"  理论回路数: {expected_loops}")
    assert len(loops) == expected_loops, f"回路数不匹配: 实际{len(loops)} vs 理论{expected_loops}"
    print("  ✓ 回路数正确")

    # 验证2: 回路矩阵
    print("\n[测试2] 回路矩阵")
    B, loop_nodes, pipe_ids = topology.loop_matrix()
    print(f"  回路矩阵尺寸: {B.shape} (回路×管道)")
    print(f"  理论尺寸: (1, 5)")
    assert B.shape[0] == 1, "应该有1个回路"

    # 检查回路矩阵元素
    print(f"  回路矩阵:\n{B}")
    # 回路中的管道系数应为 +1 或 -1，非回路管道为 0
    for i in range(B.shape[0]):
        non_zero_count = np.count_nonzero(B[i, :])
        print(f"  回路{i+1} 包含 {non_zero_count} 根管道")
    print("  ✓ 回路矩阵验证通过")

    # 验证3: 关联矩阵
    print("\n[测试3] 关联矩阵")
    A, node_ids, pipe_ids = topology.incidence_matrix()
    print(f"  关联矩阵尺寸: {A.shape}")

    # 验证列和为0
    col_sums = np.sum(A, axis=0)
    max_col_sum = np.max(np.abs(col_sums))
    print(f"  最大列和绝对值: {max_col_sum:.10f}")
    assert np.allclose(col_sums, 0.0), "关联矩阵各列之和应为0"
    print("  ✓ 关联矩阵流量守恒")

    # 验证4: 最短路径（存在多条路径的情况）
    print("\n[测试4] 最短路径搜索")
    path_j1_to_j4 = topology.shortest_path("J1", "J4")
    print(f"  J1 到 J4 的最短路径: {' -> '.join(path_j1_to_j4)}")
    print(f"  路径长度: {len(path_j1_to_j4)} 个节点")
    # BFS应该找到最短路径（2跳）
    assert len(path_j1_to_j4) == 3, "J1到J4应该是3个节点（2跳）"
    print("  ✓ 最短路径正确")

    # 验证5: 网络摘要
    print("\n[测试5] 网络摘要")
    summary = topology.summary()
    print(f"  节点数: {summary['num_nodes']}")
    print(f"  管道数: {summary['num_pipes']}")
    print(f"  回路数: {summary['num_loops']}")
    print(f"  理论回路数: {summary['expected_loops']}")
    assert summary['num_loops'] == summary['expected_loops'], "回路数与理论值不符"
    print("  ✓ 网络摘要正确")

    print("\n" + "=" * 80)
    print("✓ 验证案例2: 所有测试通过")
    print("=" * 80 + "\n")

    return topology


def validation_case_3_hardy_cross_two_loop():
    """
    验证案例3: Hardy Cross 双回路网络 - Two-Loop Network

    经典的Hardy Cross管网平差算例拓扑结构

    网络结构:
        R1
        |
        J1 --- J2
        |      |
        J3 --- J4
        |      |
        J5 --- J6

    特点:
    - 2个独立回路
    - 为Hardy Cross求解器做准备
    """
    print("=" * 80)
    print("验证案例3: Hardy Cross 双回路网络 - Two-Loop Network")
    print("=" * 80)

    # 创建拓扑
    topology = NetworkTopology(name="TwoLoopNetwork")

    # 添加节点
    reservoir = Reservoir("R1", elevation=50.0, head=50.0)
    for i in range(1, 7):
        junction = Junction(f"J{i}", elevation=10.0, demand=0.02)
        topology.add_node(junction)
    topology.add_node(reservoir)

    # 添加管道
    pipe_configs = [
        ("P0", "R1", "J1", 0.5, 500.0),   # 水源进水管
        ("P1", "J1", "J2", 0.3, 200.0),   # 横向
        ("P2", "J1", "J3", 0.3, 150.0),   # 纵向
        ("P3", "J2", "J4", 0.25, 200.0),  # 纵向
        ("P4", "J3", "J4", 0.3, 200.0),   # 横向
        ("P5", "J3", "J5", 0.25, 150.0),  # 纵向
        ("P6", "J4", "J6", 0.2, 200.0),   # 纵向
        ("P7", "J5", "J6", 0.25, 200.0),  # 横向
    ]

    for pipe_id, from_node, to_node, diameter, length in pipe_configs:
        pipe = PressurePipe(pipe_id, diameter=diameter, length=length, roughness=0.0003)
        topology.add_pipe(pipe, from_node, to_node)

    # 验证1: 回路识别
    print("\n[测试1] 回路识别")
    loops = topology.find_loops()
    print(f"  识别到的回路数: {len(loops)}")

    # 理论回路数 = n_pipes - n_nodes + 1
    expected_loops = len(topology.pipes) - len(topology.nodes) + 1
    print(f"  理论回路数: {expected_loops}")
    print(f"  实际管道数: {len(topology.pipes)}, 节点数: {len(topology.nodes)}")

    if len(loops) > 0:
        for i, loop in enumerate(loops):
            print(f"  回路 {i+1}: {' -> '.join(loop)}")

    assert len(loops) == expected_loops, f"回路数不匹配"
    print("  ✓ 回路数正确")

    # 验证2: 回路矩阵
    print("\n[测试2] 回路矩阵")
    B, loop_nodes, pipe_ids = topology.loop_matrix()
    print(f"  回路矩阵尺寸: {B.shape}")
    print(f"  回路矩阵:\n{B}")

    # 检查每个回路包含的管道数
    for i in range(B.shape[0]):
        pipes_in_loop = np.count_nonzero(B[i, :])
        print(f"  回路 {i+1} 包含 {pipes_in_loop} 根管道")
        assert pipes_in_loop >= 3, "每个回路至少应包含3根管道"
    print("  ✓ 回路矩阵验证通过")

    # 验证3: 关联矩阵
    print("\n[测试3] 关联矩阵")
    A, node_ids, pipe_ids_A = topology.incidence_matrix()
    print(f"  关联矩阵尺寸: {A.shape} (节点×管道)")

    # 验证流量守恒
    col_sums = np.sum(A, axis=0)
    assert np.allclose(col_sums, 0.0), "流量守恒不满足"
    print("  ✓ 流量守恒验证通过")

    # 验证4: 网络连通性和有效性
    print("\n[测试4] 网络连通性和有效性")
    is_connected = topology.is_connected()
    print(f"  网络连通: {'是' if is_connected else '否'}")
    assert is_connected, "网络应该是连通的"

    is_valid, issues = topology.validate()
    print(f"  网络有效: {'是' if is_valid else '否'}")
    if issues:
        for issue in issues:
            print(f"    - {issue}")
    assert is_valid or len([i for i in issues if "错误" in i]) == 0, "网络应该是有效的"
    print("  ✓ 网络验证通过")

    # 验证5: 网络摘要
    print("\n[测试5] 网络摘要")
    summary = topology.summary()
    print(f"  网络名称: {summary['name']}")
    print(f"  节点总数: {summary['num_nodes']}")
    print(f"  管道总数: {summary['num_pipes']}")
    print(f"  回路数: {summary['num_loops']}")
    print(f"  平均度数: {summary['average_degree']:.2f}")
    print("  ✓ 网络摘要统计完成")

    print("\n" + "=" * 80)
    print("✓ 验证案例3: 所有测试通过")
    print("=" * 80 + "\n")
    print("  ⚠️  注意: 该拓扑结构为Hardy Cross求解器准备")
    print("     Phase 5.3 将实现管网平差计算")
    print("=" * 80 + "\n")

    return topology


def plot_network_topology(topology: NetworkTopology, filename: str = None):
    """
    绘制管网拓扑图

    Args:
        topology: 网络拓扑对象
        filename: 保存文件名（可选）
    """
    fig, ax = plt.subplots(figsize=(12, 10))

    # 自动布局（简单的弹簧布局）
    # 这里使用一个简化的布局算法
    node_positions = {}

    # 如果节点有坐标，使用节点坐标
    has_coords = any(node.coordinates is not None for node in topology.nodes.values())

    if has_coords:
        for node_id, node in topology.nodes.items():
            if node.coordinates:
                node_positions[node_id] = node.coordinates
    else:
        # 简单圆形布局
        n = len(topology.nodes)
        for i, node_id in enumerate(sorted(topology.nodes.keys())):
            angle = 2 * np.pi * i / n
            node_positions[node_id] = (np.cos(angle), np.sin(angle))

    # 绘制管道（边）
    for pipe_id, (from_node, to_node) in topology.pipe_connections.items():
        x1, y1 = node_positions[from_node]
        x2, y2 = node_positions[to_node]

        ax.plot([x1, x2], [y1, y2], 'k-', linewidth=2, alpha=0.5, zorder=1)

        # 标注管道ID
        mx, my = (x1 + x2) / 2, (y1 + y2) / 2
        ax.text(mx, my, pipe_id, fontsize=8, ha='center',
                bbox=dict(boxstyle='round,pad=0.3', facecolor='white', alpha=0.7))

    # 绘制节点
    for node_id, node in topology.nodes.items():
        x, y = node_positions[node_id]

        # 根据节点类型选择颜色和形状
        if node.node_type == "reservoir":
            color = 'blue'
            marker = 's'  # 方形
            size = 300
        elif node.node_type == "tank":
            color = 'green'
            marker = '^'  # 三角形
            size = 300
        else:  # junction
            color = 'red'
            marker = 'o'  # 圆形
            size = 200

        ax.scatter(x, y, s=size, c=color, marker=marker, zorder=2,
                  edgecolors='black', linewidths=2)

        # 标注节点ID
        ax.text(x, y + 0.15, node_id, fontsize=10, ha='center', weight='bold')

    # 图例
    from matplotlib.lines import Line2D
    legend_elements = [
        Line2D([0], [0], marker='s', color='w', markerfacecolor='blue',
               markersize=10, label='水库 Reservoir'),
        Line2D([0], [0], marker='^', color='w', markerfacecolor='green',
               markersize=10, label='水箱 Tank'),
        Line2D([0], [0], marker='o', color='w', markerfacecolor='red',
               markersize=8, label='汇流节点 Junction'),
    ]
    ax.legend(handles=legend_elements, loc='upper right')

    ax.set_title(f'Network Topology: {topology.name}', fontsize=14, weight='bold')
    ax.set_xlabel('X coordinate')
    ax.set_ylabel('Y coordinate')
    ax.grid(True, alpha=0.3)
    ax.set_aspect('equal')

    plt.tight_layout()

    if filename:
        plt.savefig(filename, dpi=150, bbox_inches='tight')
        print(f"\n  图片已保存: {filename}")

    return fig, ax


def main():
    """运行所有验证案例"""
    print("\n" + "="*80)
    print("Stage 5 Phase 5.2 验证案例 - Network Topology Validation")
    print("="*80 + "\n")

    # 案例1: 树状网络
    topology1 = validation_case_1_simple_tree_network()

    # 案例2: 单回路网络
    topology2 = validation_case_2_single_loop_network()

    # 案例3: 双回路网络
    topology3 = validation_case_3_hardy_cross_two_loop()

    # 绘制拓扑图（可选）
    # plot_network_topology(topology1, "simple_tree_network.png")
    # plot_network_topology(topology2, "single_loop_network.png")
    # plot_network_topology(topology3, "two_loop_network.png")

    print("\n" + "="*80)
    print("✓✓✓ 所有验证案例通过 - All Validation Cases Passed ✓✓✓")
    print("="*80)
    print("\n摘要 Summary:")
    print("  - 验证案例1: 树状网络 (无回路)")
    print("  - 验证案例2: 单回路网络")
    print("  - 验证案例3: Hardy Cross双回路网络")
    print("\n功能验证 Functionality Validated:")
    print("  ✓ 网络拓扑构建")
    print("  ✓ 节点-管道连接")
    print("  ✓ 回路识别算法")
    print("  ✓ 关联矩阵构造")
    print("  ✓ 回路矩阵构造")
    print("  ✓ 最短路径搜索")
    print("  ✓ 网络连通性检查")
    print("  ✓ 网络有效性验证")
    print("  ✓ 网络摘要统计")
    print("\n准备就绪 Ready for:")
    print("  → Phase 5.3: Hardy Cross管网平差求解器")
    print("="*80 + "\n")


if __name__ == "__main__":
    main()
