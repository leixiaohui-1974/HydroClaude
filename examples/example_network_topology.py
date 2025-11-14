# -*- coding: utf-8 -*-
"""
网络拓扑使用示例

演示如何创建和管理河网拓扑结构：
1. 简单串联网络（3节点2河段）
2. Y型汇流网络（4节点3河段）
3. 复杂河网（5节点4河段）

Stage 3 - Task 3.1.1 示例

作者: HydroClaude Team
日期: 2025-10-29
"""

import numpy as np
import sys
import os

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from network.topology import Node, Reach, RiverNetwork
from solvers.godunov_fvm_solver import GodunvFVMSolver


def example_1_simple_serial():
    """
    示例1: 简单串联网络

    拓扑: N1 -> R1 -> N2 -> R2 -> N3

    场景：
    - 3个节点（2个边界节点，1个中间节点）
    - 2个河段串联
    - 演示基本的网络创建和拓扑排序
    """
    print("\n" + "="*80)
    print("示例1: 简单串联网络")
    print("="*80)

    # 1. 创建网络
    network = RiverNetwork("简单串联网络")

    # 2. 添加节点
    n1 = Node("上游", "boundary", elevation=100.0, x=0, y=0)
    n2 = Node("中游", "junction", elevation=95.0, x=500, y=0)
    n3 = Node("下游", "boundary", elevation=90.0, x=1000, y=0)

    network.add_node(n1)
    network.add_node(n2)
    network.add_node(n3)

    print(f"\n添加了 {len(network.nodes)} 个节点:")
    for node in network.nodes.values():
        print(f"  {node}")

    # 3. 创建河段求解器
    solver1 = GodunvFVMSolver(
        width=20.0,
        length=500.0,
        n_cells = 100,
        manning_n=0.025,
        slope=0.001
    )

    solver2 = GodunvFVMSolver(
        width=20.0,
        length=500.0,
        n_cells = 100,
        manning_n=0.025,
        slope=0.001
    )

    # 设置初始条件
    h_init1 = np.ones(50) * 2.0
    Q_init1 = np.ones(50) * 30.0
    h_init2 = np.ones(50) * 2.0
    Q_init2 = np.ones(50) * 30.0

    # 边界条件（临时）
    bc_left1 = {'type': 'Q', 'value': 30.0}
    bc_right1 = {'type': 'h', 'value': 2.0}
    bc_left2 = {'type': 'Q', 'value': 30.0}
    bc_right2 = {'type': 'h', 'value': 1.8}

    solver1.set_initial_conditions(h_init1, Q_init1, bc_left1, bc_right1)
    solver2.set_initial_conditions(h_init2, Q_init2, bc_left2, bc_right2)

    # 4. 添加河段
    r1 = Reach("河段1", "上游", "中游", solver1)
    r2 = Reach("河段2", "中游", "下游", solver2)

    network.add_reach(r1)
    network.add_reach(r2)

    print(f"\n添加了 {len(network.reaches)} 个河段:")
    for reach in network.reaches.values():
        print(f"  {reach}")

    # 5. 构建拓扑
    print("\n构建拓扑...")
    order = network.build_topology()
    print(f" 拓扑排序顺序: {order}")

    # 6. 验证拓扑
    is_valid, errors = network.validate_topology()
    if is_valid:
        print(" 拓扑验证通过")
    else:
        print(" 拓扑验证失败:")
        for error in errors:
            print(f"   - {error}")

    # 7. 打印摘要
    print()
    network.print_summary()

    return network


def example_2_y_junction():
    """
    示例2: Y型汇流网络

    拓扑:
        N1 -> R1 ↘
                   N3 -> R3 -> N4
        N2 -> R2 ↗

    场景：
    - 2条支流汇入主河
    - 演示汇流节点
    """
    print("\n" + "="*80)
    print("示例2: Y型汇流网络")
    print("="*80)

    network = RiverNetwork("Y型汇流网络")

    # 添加节点
    n1 = Node("支流1上游", "boundary", elevation=105.0, x=0, y=100)
    n2 = Node("支流2上游", "boundary", elevation=105.0, x=0, y=-100)
    n3 = Node("汇流点", "junction", elevation=95.0, x=300, y=0)
    n4 = Node("主河下游", "boundary", elevation=90.0, x=800, y=0)

    network.add_node(n1)
    network.add_node(n2)
    network.add_node(n3)
    network.add_node(n4)

    # 创建求解器
    # 支流1 (窄河)
    solver1 = GodunvFVMSolver(
        width=10.0, length=400.0, n_cells = 100,
        manning_n=0.030, slope=0.002
    )
    h1 = np.ones(40) * 1.5
    Q1 = np.ones(40) * 15.0
    solver1.set_initial_conditions(
        h1, Q1,
        {'type': 'Q', 'value': 15.0},
        {'type': 'h', 'value': 1.5}
    )

    # 支流2 (窄河)
    solver2 = GodunvFVMSolver(
        width=10.0, length=400.0, n_cells = 100,
        manning_n=0.030, slope=0.002
    )
    h2 = np.ones(40) * 1.5
    Q2 = np.ones(40) * 15.0
    solver2.set_initial_conditions(
        h2, Q2,
        {'type': 'Q', 'value': 15.0},
        {'type': 'h', 'value': 1.5}
    )

    # 主河 (宽河)
    solver3 = GodunvFVMSolver(
        width=25.0, length=500.0, n_cells = 100,
        manning_n=0.025, slope=0.001
    )
    h3 = np.ones(50) * 2.0
    Q3 = np.ones(50) * 30.0
    solver3.set_initial_conditions(
        h3, Q3,
        {'type': 'Q', 'value': 30.0},
        {'type': 'h', 'value': 1.8}
    )

    # 添加河段
    network.add_reach(Reach("支流1", "支流1上游", "汇流点", solver1))
    network.add_reach(Reach("支流2", "支流2上游", "汇流点", solver2))
    network.add_reach(Reach("主河", "汇流点", "主河下游", solver3))

    # 构建拓扑
    order = network.build_topology()
    print(f"\n拓扑排序顺序: {order}")

    # 检查汇流节点
    junctions = network.get_junction_nodes()
    print(f"\n汇流节点数量: {len(junctions)}")
    for j in junctions:
        print(f"  - {j.id}: {len(j.upstream_reaches)} 条上游河段汇入")

    # 打印摘要
    print()
    network.print_summary()

    # 质量平衡检查
    Q_in, Q_out, error = network.check_global_mass_balance()
    print(f"\n质量平衡检查:")
    print(f"  总入流: {Q_in:.2f} m^3/s")
    print(f"  总出流: {Q_out:.2f} m^3/s")
    print(f"  误差: {error:.4f}%")

    return network


def example_3_complex_network():
    """
    示例3: 复杂河网

    拓扑:
        N1 -> R1 -> N3 -> R3 -> N5
                  ↑
        N2 -> R2 -> ↑

        N4 -> R4 -> N5

    场景：
    - 多个汇流点
    - 复杂拓扑结构
    """
    print("\n" + "="*80)
    print("示例3: 复杂河网")
    print("="*80)

    network = RiverNetwork("复杂河网系统")

    # 添加节点
    nodes_data = [
        ("入口1", "boundary", 110.0, 0, 200),
        ("入口2", "boundary", 108.0, 0, 0),
        ("汇流1", "junction", 100.0, 400, 100),
        ("入口3", "boundary", 105.0, 200, -200),
        ("汇流2", "junction", 90.0, 800, 0),
    ]

    for node_id, node_type, elev, x, y in nodes_data:
        network.add_node(Node(node_id, node_type, elev, x, y))

    # 添加河段
    reaches_data = [
        ("R1", "入口1", "汇流1", 15.0, 450.0),  # width, length
        ("R2", "入口2", "汇流1", 12.0, 400.0),
        ("R3", "汇流1", "汇流2", 20.0, 450.0),
        ("R4", "入口3", "汇流2", 10.0, 550.0),
    ]

    for reach_id, up, down, width, length in reaches_data:
        solver = GodunvFVMSolver(
            width=width,
            length=length,
            n_cells=int(length/10),
            manning_n=0.025,
            slope=0.001
        )

        # 初始化
        n_cells = int(length/10)
        h = np.ones(n_cells) * 2.0
        Q = np.ones(n_cells) * (width * 2.0 * 1.0)  # Q = B*h*v, v=1 m/s

        solver.h = h
        solver.Q = Q

        network.add_reach(Reach(reach_id, up, down, solver))

    # 构建拓扑
    order = network.build_topology()
    print(f"\n拓扑排序顺序: {order}")

    # 分析网络
    print(f"\n网络分析:")
    print(f"  上游边界节点: {[n.id for n in network.get_upstream_nodes()]}")
    print(f"  下游边界节点: {[n.id for n in network.get_downstream_nodes()]}")
    print(f"  汇流节点: {[n.id for n in network.get_junction_nodes()]}")

    # 打印摘要
    print()
    network.print_summary()

    # 可视化（如果有networkx）
    try:
        fig = network.visualize(show_labels=True, show_flow=True)
        if fig:
            print("\n提示: 网络拓扑图已生成（需要 matplotlib 和 networkx）")
            # fig.savefig('complex_network.png')
    except:
        print("\n提示: 安装 networkx 可查看网络拓扑可视化")

    return network


if __name__ == "__main__":
    """运行所有示例"""
    print("="*80)
    print("网络拓扑使用示例集")
    print("Stage 3 - Network Topology Examples")
    print("="*80)

    # 示例1: 简单串联
    net1 = example_1_simple_serial()

    # 示例2: Y型汇流
    net2 = example_2_y_junction()

    # 示例3: 复杂河网
    net3 = example_3_complex_network()

    print("\n" + "="*80)
    print(" 所有网络拓扑示例运行完成！")
    print("="*80)

    print("\n总结:")
    print("  Stage 3 网络拓扑功能:")
    print("  1.  节点管理 - 支持多种节点类型（boundary, junction, etc.）")
    print("  2.  河段管理 - 连接节点，包含求解器")
    print("  3.  拓扑构建 - 自动拓扑排序（上游->下游）")
    print("  4.  拓扑验证 - 检测环路、孤立节点")
    print("  5.  质量平衡 - 全局质量守恒检查")
    print("  6.  网络可视化 - 拓扑图绘制")
    print("\n  可用于:")
    print("  - 串联河段模拟")
    print("  - 支流汇流模拟")
    print("  - 复杂河网系统")
    print("  - 水资源调度优化")
