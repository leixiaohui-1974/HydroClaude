#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
案例8：管网优化与管径选型
Case 8: Network Optimization and Pipe Sizing

本案例展示如何通过对比不同管径方案来优化管网设计：
- 基准方案 vs 优化方案
- 水力性能对比（压力、流速）
- 经济性分析（投资成本、运行成本）
- 优化建议

This example demonstrates network optimization through pipe sizing comparison:
- Baseline vs Optimized design
- Hydraulic performance comparison (pressure, velocity)
- Economic analysis (capital cost, operating cost)
- Optimization recommendations

Author: HydroClaude Development Team
Date: 2025-10-30
"""

import sys
import os
import numpy as np
import matplotlib.pyplot as plt

# 添加项目路径
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from network.pressure_pipe import create_pressure_pipe
from network.network_node import Junction, Reservoir
from network.network_topology import NetworkTopology
from solvers.hardy_cross_solver import HardyCrossSolver


def create_baseline_network():
    """
    创建基准管网（保守设计，管径偏大）

    系统布局：
    - 1个水库（R1）
    - 10个需水节点（J1-J10）
    - 14根管道（形成3个环路）
    """

    topology = NetworkTopology("基准管网 / Baseline Network")

    # 水库
    r1 = Reservoir('R1', elevation=100, head=130)
    topology.add_node(r1)

    # 需水节点（10个节点）
    nodes_config = {
        'J1': (55, 10.0),  # (标高m, 需水量L/s)
        'J2': (58, 8.0),
        'J3': (60, 12.0),
        'J4': (62, 9.0),
        'J5': (57, 11.0),
        'J6': (59, 7.0),
        'J7': (56, 10.0),
        'J8': (61, 8.0),
        'J9': (58, 9.0),
        'J10': (60, 6.0),
    }

    for nid, (elev, demand_ls) in nodes_config.items():
        node = Junction(nid, elevation=elev, demand=demand_ls/1000)
        topology.add_node(node)

    # 管道配置（基准方案：保守设计，管径偏大）
    # (pipe_id, from, to, diameter_mm, length_m, K_minor)
    pipes_baseline = [
        # 主干线（从水库）
        ('P1', 'R1', 'J1', 400, 800, 1.0),
        ('P2', 'J1', 'J2', 350, 500, 0.5),

        # 第一个环路
        ('P3', 'J2', 'J3', 300, 450, 0.5),
        ('P4', 'J3', 'J4', 300, 400, 0.5),
        ('P5', 'J4', 'J5', 250, 420, 0.5),
        ('P6', 'J5', 'J2', 250, 480, 0.5),

        # 第二个环路
        ('P7', 'J3', 'J6', 250, 350, 0.5),
        ('P8', 'J6', 'J7', 250, 380, 0.5),
        ('P9', 'J7', 'J8', 200, 400, 0.5),
        ('P10', 'J8', 'J4', 200, 420, 0.5),

        # 第三个环路
        ('P11', 'J6', 'J9', 200, 360, 0.5),
        ('P12', 'J9', 'J10', 200, 340, 0.5),
        ('P13', 'J10', 'J8', 200, 380, 0.5),

        # 连接管
        ('P14', 'J5', 'J7', 200, 450, 0.6),
    ]

    for pid, from_node, to_node, D_mm, L, K in pipes_baseline:
        pipe = create_pressure_pipe(pid, D_mm/1000, L, material='steel', K_minor=K)
        topology.add_pipe(pipe, from_node, to_node)

    return topology, pipes_baseline


def create_optimized_network():
    """
    创建优化管网（经济设计，管径合理化）

    优化策略：
    - 主干线保持较大管径（保证输水能力）
    - 支线适当减小管径（降低投资）
    - 末端管道进一步优化（经济性优先）
    """

    topology = NetworkTopology("优化管网 / Optimized Network")

    # 水库（与基准方案相同）
    r1 = Reservoir('R1', elevation=100, head=130)
    topology.add_node(r1)

    # 需水节点（与基准方案相同）
    nodes_config = {
        'J1': (55, 10.0),
        'J2': (58, 8.0),
        'J3': (60, 12.0),
        'J4': (62, 9.0),
        'J5': (57, 11.0),
        'J6': (59, 7.0),
        'J7': (56, 10.0),
        'J8': (61, 8.0),
        'J9': (58, 9.0),
        'J10': (60, 6.0),
    }

    for nid, (elev, demand_ls) in nodes_config.items():
        node = Junction(nid, elevation=elev, demand=demand_ls/1000)
        topology.add_node(node)

    # 管道配置（优化方案：合理化管径）
    pipes_optimized = [
        # 主干线（保持）
        ('P1', 'R1', 'J1', 350, 800, 1.0),   # 减小50mm
        ('P2', 'J1', 'J2', 300, 500, 0.5),   # 减小50mm

        # 第一个环路（适度优化）
        ('P3', 'J2', 'J3', 250, 450, 0.5),   # 减小50mm
        ('P4', 'J3', 'J4', 250, 400, 0.5),   # 减小50mm
        ('P5', 'J4', 'J5', 200, 420, 0.5),   # 减小50mm
        ('P6', 'J5', 'J2', 200, 480, 0.5),   # 减小50mm

        # 第二个环路（较大优化）
        ('P7', 'J3', 'J6', 200, 350, 0.5),   # 减小50mm
        ('P8', 'J6', 'J7', 200, 380, 0.5),   # 减小50mm
        ('P9', 'J7', 'J8', 150, 400, 0.5),   # 减小50mm
        ('P10', 'J8', 'J4', 150, 420, 0.5),  # 减小50mm

        # 第三个环路（最大优化）
        ('P11', 'J6', 'J9', 150, 360, 0.5),  # 减小50mm
        ('P12', 'J9', 'J10', 150, 340, 0.5), # 减小50mm
        ('P13', 'J10', 'J8', 150, 380, 0.5), # 减小50mm

        # 连接管
        ('P14', 'J5', 'J7', 150, 450, 0.6),  # 减小50mm
    ]

    for pid, from_node, to_node, D_mm, L, K in pipes_optimized:
        pipe = create_pressure_pipe(pid, D_mm/1000, L, material='steel', K_minor=K)
        topology.add_pipe(pipe, from_node, to_node)

    return topology, pipes_optimized


def analyze_hydraulics(topology, scheme_name):
    """
    分析水力性能

    Returns:
        dict: 包含压力、流速、水头损失等信息
    """

    print(f"【{scheme_name}】")

    try:
        solver = HardyCrossSolver(topology, max_iter=200, tol=1e-4, verbose=False)
        flows, heads = solver.solve()

        if not solver.converged:
            print(f"   求解未收敛")
            return None

        print(f"   求解收敛")

        # 压力分析
        pressures = []
        for nid, node in topology.nodes.items():
            if isinstance(node, Junction):
                pressure = heads[nid] - node.elevation
                pressures.append(pressure)

        min_pressure = min(pressures)
        max_pressure = max(pressures)
        avg_pressure = np.mean(pressures)

        print(f"  压力范围: {min_pressure:.2f} ~ {max_pressure:.2f}m (平均={avg_pressure:.2f}m)")

        # 压力检查
        if min_pressure < 15:
            print(f"     最小压力不足 (< 15m)")
            pressure_adequate = False
        elif min_pressure < 20:
            print(f"     最小压力偏低 (< 20m)")
            pressure_adequate = True
        else:
            print(f"     压力满足要求 (>= 20m)")
            pressure_adequate = True

        # 流速分析
        velocities = []
        max_velocity_pipe = None
        max_velocity_value = 0

        for pid, pipe in topology.pipes.items():
            Q = abs(flows[pid])
            A = np.pi * (pipe.D / 2) ** 2
            V = Q / A
            velocities.append(V)

            if V > max_velocity_value:
                max_velocity_value = V
                max_velocity_pipe = pid

        max_velocity = max(velocities)
        avg_velocity = np.mean(velocities)

        print(f"  流速范围: 平均={avg_velocity:.2f}m/s, 最大={max_velocity:.2f}m/s (管道{max_velocity_pipe})")

        # 流速检查
        if max_velocity > 3.0:
            print(f"     最大流速过高 (> 3.0m/s)")
            velocity_adequate = False
        elif max_velocity > 2.5:
            print(f"     最大流速偏高 (> 2.5m/s)")
            velocity_adequate = True
        else:
            print(f"     流速合理 (<= 2.5m/s)")
            velocity_adequate = True

        # 计算总水头损失
        H_source = topology.nodes['R1'].head
        total_demand = sum(node.demand for node in topology.nodes.values()
                          if isinstance(node, Junction))

        # 计算最远点水头损失
        farthest_node = max(
            [(nid, heads[nid]) for nid, node in topology.nodes.items()
             if isinstance(node, Junction)],
            key=lambda x: H_source - x[1]
        )
        max_head_loss = H_source - farthest_node[1]

        print(f"  总需水量: {total_demand*1000:.1f} L/s")
        print(f"  最大水头损失: {max_head_loss:.2f}m (节点{farthest_node[0]})")

        return {
            'converged': True,
            'min_pressure': min_pressure,
            'max_pressure': max_pressure,
            'avg_pressure': avg_pressure,
            'max_velocity': max_velocity,
            'avg_velocity': avg_velocity,
            'max_head_loss': max_head_loss,
            'pressure_adequate': pressure_adequate,
            'velocity_adequate': velocity_adequate,
            'flows': flows,
            'heads': heads,
        }

    except Exception as e:
        print(f"   分析失败: {e}")
        return None


def economic_analysis(pipes_config, scheme_name):
    """
    经济性分析

    Args:
        pipes_config: 管道配置列表
        scheme_name: 方案名称

    Returns:
        dict: 投资成本、运行成本等
    """

    print(f"【{scheme_name} - 经济分析】")

    # 管材单价 (元/m，包括材料+安装)
    # DN150: 180元/m, DN200: 250元/m, DN250: 350元/m,
    # DN300: 480元/m, DN350: 620元/m, DN400: 780元/m
    unit_prices = {
        150: 180,
        200: 250,
        250: 350,
        300: 480,
        350: 620,
        400: 780,
    }

    total_cost = 0
    total_length = 0
    pipe_costs = []

    for pid, from_node, to_node, D_mm, L, K in pipes_config:
        unit_price = unit_prices.get(D_mm, 250)  # 默认250元/m
        cost = unit_price * L
        total_cost += cost
        total_length += L
        pipe_costs.append((pid, D_mm, L, cost))

    print(f"  总管长: {total_length:.0f}m")
    print(f"  总投资: {total_cost/10000:.2f}万元")
    print(f"  平均单价: {total_cost/total_length:.0f}元/m")

    # 按管径统计
    diameter_stats = {}
    for pid, D_mm, L, cost in pipe_costs:
        if D_mm not in diameter_stats:
            diameter_stats[D_mm] = {'length': 0, 'cost': 0}
        diameter_stats[D_mm]['length'] += L
        diameter_stats[D_mm]['cost'] += cost

    print(f"  管径分布:")
    for D_mm in sorted(diameter_stats.keys()):
        stats = diameter_stats[D_mm]
        print(f"    DN{D_mm}: {stats['length']:.0f}m, {stats['cost']/10000:.2f}万元")

    return {
        'total_cost': total_cost,
        'total_length': total_length,
        'avg_unit_price': total_cost / total_length,
        'diameter_stats': diameter_stats,
    }


def compare_schemes():
    """对比基准方案与优化方案"""

    print()
    print("="*80)
    print("方案对比")
    print("Scheme Comparison")
    print("="*80)
    print()

    # 1. 创建两个方案
    print("【创建管网】")
    baseline_topo, baseline_pipes = create_baseline_network()
    print(f"   基准方案: {len(baseline_topo.nodes)}个节点, {len(baseline_topo.pipes)}根管道")

    optimized_topo, optimized_pipes = create_optimized_network()
    print(f"   优化方案: {len(optimized_topo.nodes)}个节点, {len(optimized_topo.pipes)}根管道")
    print()

    # 2. 水力分析
    print("="*80)
    print("水力性能分析")
    print("="*80)
    print()

    baseline_results = analyze_hydraulics(baseline_topo, "基准方案")
    print()

    optimized_results = analyze_hydraulics(optimized_topo, "优化方案")
    print()

    # 3. 经济分析
    print("="*80)
    print("经济性分析")
    print("="*80)
    print()

    baseline_economics = economic_analysis(baseline_pipes, "基准方案")
    print()

    optimized_economics = economic_analysis(optimized_pipes, "优化方案")
    print()

    # 4. 综合对比
    if baseline_results and optimized_results:
        print("="*80)
        print("综合对比")
        print("="*80)
        print()

        # 经济性对比
        cost_saving = baseline_economics['total_cost'] - optimized_economics['total_cost']
        cost_saving_pct = cost_saving / baseline_economics['total_cost'] * 100

        print("【经济性】")
        print(f"  投资节省: {cost_saving/10000:.2f}万元 ({cost_saving_pct:.1f}%)")

        # 水力性能对比
        print()
        print("【水力性能】")

        pressure_change = optimized_results['min_pressure'] - baseline_results['min_pressure']
        velocity_change = optimized_results['max_velocity'] - baseline_results['max_velocity']

        print(f"  最小压力变化: {pressure_change:+.2f}m")
        if pressure_change < -2:
            print(f"     压力下降较多")
        elif pressure_change < 0:
            print(f"     压力略有下降")
        else:
            print(f"     压力保持或提升")

        print(f"  最大流速变化: {velocity_change:+.2f}m/s")
        if velocity_change > 0.5:
            print(f"     流速增加较多")
        elif velocity_change > 0.2:
            print(f"     流速略有增加")
        else:
            print(f"     流速保持合理")

        # 推荐方案
        print()
        print("【推荐方案】")

        if (optimized_results['pressure_adequate'] and
            optimized_results['velocity_adequate'] and
            cost_saving_pct > 10):
            print(f"   推荐【优化方案】")
            print(f"     理由: 节省投资{cost_saving_pct:.1f}%，且水力性能满足要求")
        elif cost_saving_pct < 5:
            print(f"   推荐【基准方案】")
            print(f"     理由: 投资节省有限({cost_saving_pct:.1f}%)，保守设计更安全")
        else:
            print(f"   需要进一步优化")
            print(f"     理由: 投资可节省{cost_saving_pct:.1f}%，但水力性能需改进")

        return {
            'baseline': {'hydraulics': baseline_results, 'economics': baseline_economics},
            'optimized': {'hydraulics': optimized_results, 'economics': optimized_economics},
        }

    return None


def plot_comparison(results):
    """绘制对比图表"""

    if not results:
        print("无对比数据可绘制")
        return

    baseline = results['baseline']
    optimized = results['optimized']

    fig, axes = plt.subplots(2, 2, figsize=(12, 10))

    # 子图1：压力对比
    ax1 = axes[0, 0]
    categories = ['Min Pressure', 'Avg Pressure', 'Max Pressure']
    baseline_pressures = [
        baseline['hydraulics']['min_pressure'],
        baseline['hydraulics']['avg_pressure'],
        baseline['hydraulics']['max_pressure'],
    ]
    optimized_pressures = [
        optimized['hydraulics']['min_pressure'],
        optimized['hydraulics']['avg_pressure'],
        optimized['hydraulics']['max_pressure'],
    ]

    x = np.arange(len(categories))
    width = 0.35

    ax1.bar(x - width/2, baseline_pressures, width, label='Baseline', color='#3498db', alpha=0.8)
    ax1.bar(x + width/2, optimized_pressures, width, label='Optimized', color='#e74c3c', alpha=0.8)

    ax1.set_ylabel('Pressure (m)', fontsize=11, fontweight='bold')
    ax1.set_title('Pressure Comparison', fontsize=12, fontweight='bold')
    ax1.set_xticks(x)
    ax1.set_xticklabels(categories)
    ax1.legend()
    ax1.grid(True, alpha=0.3, axis='y')
    ax1.axhline(y=15, color='r', linestyle='--', linewidth=1, alpha=0.7)

    # 子图2：流速对比
    ax2 = axes[0, 1]
    velocity_categories = ['Avg Velocity', 'Max Velocity']
    baseline_velocities = [
        baseline['hydraulics']['avg_velocity'],
        baseline['hydraulics']['max_velocity'],
    ]
    optimized_velocities = [
        optimized['hydraulics']['avg_velocity'],
        optimized['hydraulics']['max_velocity'],
    ]

    x2 = np.arange(len(velocity_categories))
    ax2.bar(x2 - width/2, baseline_velocities, width, label='Baseline', color='#3498db', alpha=0.8)
    ax2.bar(x2 + width/2, optimized_velocities, width, label='Optimized', color='#e74c3c', alpha=0.8)

    ax2.set_ylabel('Velocity (m/s)', fontsize=11, fontweight='bold')
    ax2.set_title('Velocity Comparison', fontsize=12, fontweight='bold')
    ax2.set_xticks(x2)
    ax2.set_xticklabels(velocity_categories)
    ax2.legend()
    ax2.grid(True, alpha=0.3, axis='y')
    ax2.axhline(y=3.0, color='r', linestyle='--', linewidth=1, alpha=0.7)

    # 子图3：投资对比
    ax3 = axes[1, 0]
    schemes = ['Baseline', 'Optimized']
    costs = [
        baseline['economics']['total_cost'] / 10000,
        optimized['economics']['total_cost'] / 10000,
    ]

    bars = ax3.bar(schemes, costs, color=['#3498db', '#2ecc71'], alpha=0.8, edgecolor='black', linewidth=1.5)
    ax3.set_ylabel('Total Cost (10k CNY)', fontsize=11, fontweight='bold')
    ax3.set_title('Investment Cost Comparison', fontsize=12, fontweight='bold')
    ax3.grid(True, alpha=0.3, axis='y')

    # 添加数值标签
    for bar, cost in zip(bars, costs):
        height = bar.get_height()
        ax3.text(bar.get_x() + bar.get_width()/2., height,
                f'{cost:.1f}万',
                ha='center', va='bottom', fontweight='bold')

    # 计算节省
    saving = costs[0] - costs[1]
    saving_pct = saving / costs[0] * 100
    ax3.text(0.5, max(costs)*0.5,
            f'Saving:\n{saving:.1f}万\n({saving_pct:.1f}%)',
            ha='center', va='center',
            bbox=dict(boxstyle='round', facecolor='yellow', alpha=0.5),
            fontsize=11, fontweight='bold')

    # 子图4：管径分布对比
    ax4 = axes[1, 1]

    # 获取所有管径
    all_diameters = sorted(set(
        list(baseline['economics']['diameter_stats'].keys()) +
        list(optimized['economics']['diameter_stats'].keys())
    ))

    baseline_lengths = [baseline['economics']['diameter_stats'].get(d, {'length': 0})['length']
                       for d in all_diameters]
    optimized_lengths = [optimized['economics']['diameter_stats'].get(d, {'length': 0})['length']
                        for d in all_diameters]

    x3 = np.arange(len(all_diameters))
    width3 = 0.35

    ax4.bar(x3 - width3/2, baseline_lengths, width3, label='Baseline', color='#3498db', alpha=0.8)
    ax4.bar(x3 + width3/2, optimized_lengths, width3, label='Optimized', color='#e74c3c', alpha=0.8)

    ax4.set_ylabel('Pipe Length (m)', fontsize=11, fontweight='bold')
    ax4.set_title('Pipe Diameter Distribution', fontsize=12, fontweight='bold')
    ax4.set_xticks(x3)
    ax4.set_xticklabels([f'DN{d}' for d in all_diameters])
    ax4.legend()
    ax4.grid(True, alpha=0.3, axis='y')

    plt.tight_layout()

    output_path = os.path.join(os.path.dirname(__file__), 'network_optimization_results.png')
    plt.savefig(output_path, dpi=150, bbox_inches='tight')
    print(f" 结果图表已保存: {output_path}")

    plt.close()


def recommendations():
    """优化建议"""

    print()
    print("="*80)
    print("管网优化建议")
    print("Network Optimization Recommendations")
    print("="*80)
    print()

    print("【1. 管径选择原则】")
    print("  - 主干线：流量大，选择较大管径，降低水头损失")
    print("  - 支线：流量小，可适当减小管径，节省投资")
    print("  - 末端：需水量少，优先考虑经济性")
    print("  - 控制流速：0.6-2.5 m/s为宜，避免过高或过低")
    print()

    print("【2. 优化方法】")
    print("  - 迭代优化：逐步调整管径，平衡水力与经济性")
    print("  - 敏感性分析：识别关键管道，重点优化")
    print("  - 多方案对比：评估不同设计的优缺点")
    print("  - 可靠性检验：确保优化后系统仍满足要求")
    print()

    print("【3. 经济性评估】")
    print("  - 初投资：管道材料+安装成本")
    print("  - 运行成本：泵站能耗（与水头损失相关）")
    print("  - 全生命周期：考虑50年使用期")
    print("  - 投资回收期：一般3-5年为宜")
    print()

    print("【4. 约束条件】")
    print("  - 最小压力：节点压力 >= 15-20m")
    print("  - 最大流速：管道流速 <= 3.0m/s（防水锤）")
    print("  - 最小流速：管道流速 >= 0.3m/s（防沉积）")
    print("  - 标准管径：采用国标系列管径")
    print()

    print("【5. 实施建议】")
    print("  - 分期建设：先建主干线，后建支线")
    print("  - 预留余量：考虑未来需水量增长10-20%")
    print("  - 材料选择：根据水质、地质条件选择合适管材")
    print("  - 施工质量：确保管道连接密封，防止漏损")
    print()


def main():
    """主函数"""

    print()
    print("╔" + "="*78 + "╗")
    print("║" + " "*24 + "管网优化与管径选型" + " "*24 + "║")
    print("║" + " "*18 + "Network Optimization and Pipe Sizing" + " "*18 + "║")
    print("╚" + "="*78 + "╝")

    # 1. 方案对比
    results = compare_schemes()

    # 2. 绘制对比图
    if results:
        plot_comparison(results)

    # 3. 优化建议
    recommendations()

    print("="*80)
    print(" 案例分析完成！")
    print("="*80)
    print()


if __name__ == '__main__':
    main()
