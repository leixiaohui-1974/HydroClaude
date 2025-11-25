# -*- coding: utf-8 -*-
"""
网络验证工具使用示例

演示如何使用验证和可视化工具：
1. 基本网络验证
2. 检测和修复常见问题
3. 网络健康评分
4. 高程剖面可视化
5. 流量分布可视化

Stage 3 - Task 3.1.3 示例

作者: HydroClaude Team
日期: 2025-10-29
"""

import numpy as np
import warnings
warnings.filterwarnings("ignore")
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from network.topology import Node, Reach, RiverNetwork
from network.nodes import create_inflow_boundary, create_outflow_boundary, create_junction
from network.validation import NetworkValidator, NetworkVisualizer, validate_network, visualize_network
from solvers.godunov_fvm_solver import GodunvFVMSolver


def create_test_solver(length=100.0, width=10.0, h_init=2.0, Q_init=20.0):
    """创建测试求解器"""
    n_cells = int(length / 10)
    solver = GodunvFVMSolver(
        width=width,
        length=length,
        n_cells=n_cells,
        manning_n=0.025,
        slope=0.001
    )

    h = np.ones(n_cells) * h_init
    Q = np.ones(n_cells) * Q_init

    solver.h = h
    solver.Q = Q

    return solver


def example_1_basic_validation():
    """
    示例1: 基本网络验证

    创建一个简单网络并进行验证
    """
    print("\n" + "="*80)
    print("示例1: 基本网络验证")
    print("="*80)

    # 创建网络
    network = RiverNetwork("简单河网")

    # 添加节点
    n1 = create_inflow_boundary("上游入口", Q=50.0, elevation=110.0)
    n2 = Node("中游节点", "junction", elevation=100.0)
    n3 = create_outflow_boundary("下游出口", h=2.0, elevation=95.0)

    network.add_node(n1)
    network.add_node(n2)
    network.add_node(n3)

    # 添加河段
    solver1 = create_test_solver(length=500.0, width=15.0, Q_init=50.0)
    solver2 = create_test_solver(length=500.0, width=15.0, Q_init=50.0)

    network.add_reach(Reach("河段1", "上游入口", "中游节点", solver1))
    network.add_reach(Reach("河段2", "中游节点", "下游出口", solver2))

    # 执行验证
    print("\n执行网络验证...")
    is_valid, health_score = validate_network(network, verbose=True)

    if is_valid:
        print("\n 网络验证通过！")
    else:
        print("\n 网络验证失败！")

    return network


def example_2_detect_problems():
    """
    示例2: 检测网络问题

    演示如何检测各种常见问题
    """
    print("\n" + "="*80)
    print("示例2: 检测网络问题")
    print("="*80)

    # 问题1: 高程不一致
    print("\n【问题1: 高程不一致】")
    network1 = RiverNetwork("高程不一致网络")

    n1 = Node("N1", "boundary", elevation=90.0)   # 上游 90m
    n2 = Node("N2", "boundary", elevation=100.0)  # 下游 100m（错误！）

    network1.add_node(n1)
    network1.add_node(n2)
    network1.add_reach(Reach("R1", "N1", "N2", create_test_solver()))

    validator1 = NetworkValidator(network1)
    validator1.validate_all(verbose=False)

    print(f"错误数: {len(validator1.errors)}")
    for error in validator1.errors:
        print(f"  - {error}")

    # 问题2: 孤立节点
    print("\n【问题2: 孤立节点】")
    network2 = RiverNetwork("孤立节点网络")

    network2.add_node(Node("N1", "boundary", elevation=100.0))
    network2.add_node(Node("N2", "boundary", elevation=95.0))
    network2.add_node(Node("孤立", "junction", elevation=98.0))  # 孤立！

    network2.add_reach(Reach("R1", "N1", "N2", create_test_solver()))

    validator2 = NetworkValidator(network2)
    validator2.validate_all(verbose=False)

    print(f"错误数: {len(validator2.errors)}")
    for error in validator2.errors:
        print(f"  - {error}")

    # 问题3: 环路
    print("\n【问题3: 环路】")
    network3 = RiverNetwork("环路网络")

    network3.add_node(Node("N1", "junction"))
    network3.add_node(Node("N2", "junction"))
    network3.add_node(Node("N3", "junction"))

    network3.add_reach(Reach("R1", "N1", "N2", create_test_solver()))
    network3.add_reach(Reach("R2", "N2", "N3", create_test_solver()))
    network3.add_reach(Reach("R3", "N3", "N1", create_test_solver()))  # 环路！

    validator3 = NetworkValidator(network3)
    validator3.validate_all(verbose=False)

    print(f"错误数: {len(validator3.errors)}")
    for error in validator3.errors:
        print(f"  - {error}")


def example_3_health_score():
    """
    示例3: 网络健康评分

    演示不同网络的健康评分
    """
    print("\n" + "="*80)
    print("示例3: 网络健康评分")
    print("="*80)

    networks = []

    # 网络A: 完美网络
    net_a = RiverNetwork("完美网络")
    net_a.add_node(create_inflow_boundary("IN", Q=50.0, elevation=110.0))
    net_a.add_node(create_outflow_boundary("OUT", h=2.0, elevation=90.0))
    net_a.add_reach(Reach("R1", "IN", "OUT",
                         create_test_solver(length=1000.0)))
    networks.append(("完美网络", net_a))

    # 网络B: 有警告的网络（零坡度）
    net_b = RiverNetwork("零坡度网络")
    net_b.add_node(Node("N1", "boundary", elevation=100.0))
    net_b.add_node(Node("N2", "boundary", elevation=100.0))  # 零坡度
    net_b.add_reach(Reach("R1", "N1", "N2", create_test_solver()))
    networks.append(("零坡度网络", net_b))

    # 网络C: 有错误的网络（高程倒置）
    net_c = RiverNetwork("高程倒置网络")
    net_c.add_node(Node("N1", "boundary", elevation=90.0))   # 上游低
    net_c.add_node(Node("N2", "boundary", elevation=100.0))  # 下游高
    net_c.add_reach(Reach("R1", "N1", "N2", create_test_solver()))
    networks.append(("高程倒置网络", net_c))

    # 评估所有网络
    print("\n网络健康评分对比：")
    print(f"{'网络名称':^20} {'健康评分':^12} {'评级':^15}")
    print("-" * 50)

    for name, network in networks:
        validator = NetworkValidator(network)
        is_valid, score = validator.validate_all(verbose=False)

        if score >= 90:
            rating = "优秀 *****"
        elif score >= 75:
            rating = "良好 ****"
        elif score >= 60:
            rating = "合格 ***"
        elif score >= 40:
            rating = "需改进 **"
        else:
            rating = "不合格 *"

        print(f"{name:^20} {score:^12.1f} {rating:^15}")


def example_4_elevation_profile():
    """
    示例4: 高程剖面可视化

    创建复杂网络并绘制高程剖面图
    """
    print("\n" + "="*80)
    print("示例4: 高程剖面可视化")
    print("="*80)

    # 创建多河段网络
    network = RiverNetwork("长江段")

    # 节点（从上游到下游，高程逐渐降低）
    nodes_data = [
        ("重庆", "boundary", 180.0),
        ("宜昌", "junction", 50.0),
        ("武汉", "junction", 20.0),
        ("南京", "junction", 10.0),
        ("上海", "boundary", 0.0),
    ]

    for node_id, node_type, elevation in nodes_data:
        if node_type == "boundary":
            if elevation > 100:
                node = create_inflow_boundary(node_id, Q=10000.0, elevation=elevation)
            else:
                node = create_outflow_boundary(node_id, h=5.0, elevation=elevation)
        else:
            node = Node(node_id, node_type, elevation=elevation)
        network.add_node(node)

    # 河段
    reaches_data = [
        ("重庆-宜昌", "重庆", "宜昌", 600000.0, 500.0),  # 600km, 500m宽
        ("宜昌-武汉", "宜昌", "武汉", 400000.0, 800.0),  # 400km, 800m宽
        ("武汉-南京", "武汉", "南京", 500000.0, 1000.0), # 500km, 1km宽
        ("南京-上海", "南京", "上海", 300000.0, 1200.0), # 300km, 1.2km宽
    ]

    for reach_id, up, down, length, width in reaches_data:
        solver = create_test_solver(length=length, width=width,
                                   h_init=10.0, Q_init=10000.0)
        network.add_reach(Reach(reach_id, up, down, solver))

    # 验证网络
    print("\n网络验证:")
    is_valid, score = validate_network(network, verbose=False)
    print(f"  健康评分: {score:.1f}/100")

    # 绘制高程剖面
    print("\n绘制高程剖面图...")
    try:
        visualizer = NetworkVisualizer(network)
        fig = visualizer.plot_elevation_profile()

        if fig:
            print(" 高程剖面图已生成")
            # fig.savefig('elevation_profile.png', dpi=150, bbox_inches='tight')
            # print("  已保存到: elevation_profile.png")
    except Exception as e:
        print(f"  可视化需要matplotlib: {e}")

    return network


def example_5_comprehensive_analysis():
    """
    示例5: 综合网络分析

    对复杂网络进行全面分析和可视化
    """
    print("\n" + "="*80)
    print("示例5: 综合网络分析")
    print("="*80)

    # 创建Y型汇流网络
    network = RiverNetwork("Y型汇流系统")

    # 节点
    network.add_node(create_inflow_boundary("支流1", Q=30.0, elevation=120.0))
    network.add_node(create_inflow_boundary("支流2", Q=20.0, elevation=120.0))
    network.add_node(create_junction("汇流点", elevation=100.0))
    network.add_node(create_outflow_boundary("出口", h=2.0, elevation=90.0))

    # 河段
    s1 = create_test_solver(length=500.0, width=10.0, Q_init=30.0)
    s2 = create_test_solver(length=500.0, width=8.0, Q_init=20.0)
    s3 = create_test_solver(length=800.0, width=20.0, Q_init=50.0)

    network.add_reach(Reach("支流1河段", "支流1", "汇流点", s1))
    network.add_reach(Reach("支流2河段", "支流2", "汇流点", s2))
    network.add_reach(Reach("主河河段", "汇流点", "出口", s3))

    # 完整验证
    print("\n【完整验证】")
    validator = NetworkValidator(network)
    is_valid, health_score = validator.validate_all(verbose=False)

    summary = validator.get_validation_summary()

    print(f"\n验证结果:")
    print(f"  通过: {' 是' if summary['is_valid'] else ' 否'}")
    print(f"  健康评分: {summary['health_score']:.1f}/100")
    print(f"  错误: {len(summary['errors'])}")
    print(f"  警告: {len(summary['warnings'])}")
    print(f"  信息: {len(summary['info'])}")

    # 质量平衡
    print("\n【质量平衡】")
    Q_in, Q_out, error = network.check_global_mass_balance()
    print(f"  总入流: {Q_in:.2f} m^3/s")
    print(f"  总出流: {Q_out:.2f} m^3/s")
    print(f"  误差: {error:.4f}%")

    # 可视化
    print("\n【可视化】")
    try:
        # 方法1: 高程剖面
        print("  生成高程剖面图...")
        fig1 = visualize_network(network, plot_type='elevation')

        # 方法2: 流量分布
        print("  生成流量分布图...")
        fig2 = visualize_network(network, plot_type='flow')

        # 方法3: 综合摘要
        print("  生成综合摘要图...")
        fig3 = visualize_network(network, plot_type='summary')

        print(" 所有图表已生成")

    except Exception as e:
        print(f"  可视化需要matplotlib和networkx: {e}")

    return network


if __name__ == "__main__":
    """运行所有示例"""
    print("="*80)
    print("网络验证工具使用示例集")
    print("Stage 3 - Network Validation & Visualization Examples")
    print("="*80)

    # 示例1: 基本验证
    net1 = example_1_basic_validation()

    # 示例2: 问题检测
    example_2_detect_problems()

    # 示例3: 健康评分
    example_3_health_score()

    # 示例4: 高程剖面
    net4 = example_4_elevation_profile()

    # 示例5: 综合分析
    net5 = example_5_comprehensive_analysis()

    print("\n" + "="*80)
    print(" 所有网络验证示例运行完成！")
    print("="*80)

    print("\n总结:")
    print("  Stage 3 网络验证工具:")
    print("  1.  NetworkValidator - 全面验证")
    print("     - 拓扑完整性检查")
    print("     - 高程一致性验证")
    print("     - 孤立节点检测")
    print("     - 环路检测")
    print("     - 边界条件检查")
    print("     - 初始条件验证")
    print("     - 健康评分（0-100）")
    print("  2.  NetworkVisualizer - 增强可视化")
    print("     - 拓扑图")
    print("     - 高程剖面图")
    print("     - 流量分布图")
    print("     - 综合摘要图")
    print("  3.  便捷函数")
    print("     - validate_network()")
    print("     - visualize_network()")
    print("\n  应用价值:")
    print("  - 自动检测建模错误")
    print("  - 确保物理合理性")
    print("  - 提供详细诊断报告")
    print("  - 直观的可视化展示")
