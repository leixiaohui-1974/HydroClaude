#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
案例7：区域供水管网系统
Case 7: Regional Water Supply Network System

本案例展示大规模区域供水管网的水力分析：
- 多水源供水（2个水库 + 1个高位水塔）
- 复杂环状拓扑（18个节点 + 25根管道）
- 分区供水（居民区、商业区、工业区）
- 多工况分析（高峰/平均/低谷）
- 供水可靠性分析

This example demonstrates hydraulic analysis of a large-scale regional water network:
- Multiple water sources (2 reservoirs + 1 elevated tank)
- Complex looped topology (18 nodes + 25 pipes)
- Zoned supply (residential, commercial, industrial)
- Multi-scenario analysis (peak/average/minimum)
- Supply reliability analysis

Author: HydroClaude Development Team
Date: 2025-10-30
"""

import sys
import warnings
warnings.filterwarnings("ignore")
import os
import numpy as np
import matplotlib.pyplot as plt
from matplotlib import font_manager

# 添加项目路径
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from network.pressure_pipe import create_pressure_pipe
from network.network_node import Junction, Reservoir, Tank
from network.network_topology import NetworkTopology
from solvers.hardy_cross_solver import HardyCrossSolver


def create_regional_network():
    """
    创建区域供水管网

    系统布局：
    - 水源：R1（北部水库，标高100m）、R2（东部水库，标高95m）、T1（中心水塔，标高120m）
    - 供水分区：
      * 北部居民区（N1-N5）：标高50-60m，需水量中等
      * 东部工业区（E1-E3）：标高45-50m，需水量大
      * 南部商业区（S1-S4）：标高55-65m，需水量变化大
      * 西部居民区（W1-W3）：标高60-70m，需水量稳定
    - 管网：25根管道，形成复杂环状结构

    Returns:
        NetworkTopology: 区域供水管网拓扑
    """

    print("="*80)
    print("创建区域供水管网")
    print("Creating Regional Water Supply Network")
    print("="*80)
    print()

    # 创建拓扑
    topology = NetworkTopology("区域供水管网 / Regional Water Network")

    # ========== 1. 水源节点 ==========
    print("【水源配置】")

    # 北部水库（主水源）
    r1 = Reservoir('R1', elevation=100, head=135)
    topology.add_node(r1)
    print(f"   北部水库 R1: 标高={r1.elevation}m, 水位={r1.head}m")

    # 东部水库（辅助水源）
    r2 = Reservoir('R2', elevation=95, head=125)
    topology.add_node(r2)
    print(f"   东部水库 R2: 标高={r2.elevation}m, 水位={r2.head}m")

    # 中心水塔（调节水源）
    t1 = Tank('T1', elevation=80, diameter=15.0,
              min_level=0.0, max_level=50.0, initial_level=40.0)
    topology.add_node(t1)
    print(f"   中心水塔 T1: 底部标高={t1.elevation}m, 水位={t1.head}m")

    print()

    # ========== 2. 需水节点 ==========
    print("【需水节点配置】")

    # 北部居民区 (North Residential)
    north_nodes = {
        'N1': (55, 15.0, "北部主干道"),
        'N2': (58, 12.0, "北部小区A"),
        'N3': (60, 10.0, "北部小区B"),
        'N4': (57, 8.0, "北部工业园"),
        'N5': (56, 6.0, "北部学校"),
    }

    print("  北部居民区 (标高55-60m):")
    for nid, (elev, demand_ls, desc) in north_nodes.items():
        demand = demand_ls / 1000  # L/s -> m^3/s
        node = Junction(nid, elevation=elev, demand=demand)
        topology.add_node(node)
        print(f"    - {nid}: {desc}, 需水量={demand_ls:.1f}L/s")

    # 东部工业区 (East Industrial)
    east_nodes = {
        'E1': (48, 25.0, "东部化工厂"),
        'E2': (47, 20.0, "东部制造厂"),
        'E3': (45, 15.0, "东部物流园"),
    }

    print("  东部工业区 (标高45-50m):")
    for nid, (elev, demand_ls, desc) in east_nodes.items():
        demand = demand_ls / 1000
        node = Junction(nid, elevation=elev, demand=demand)
        topology.add_node(node)
        print(f"    - {nid}: {desc}, 需水量={demand_ls:.1f}L/s")

    # 南部商业区 (South Commercial)
    south_nodes = {
        'S1': (60, 18.0, "南部购物中心"),
        'S2': (62, 15.0, "南部酒店群"),
        'S3': (65, 12.0, "南部商业街"),
        'S4': (58, 10.0, "南部写字楼"),
    }

    print("  南部商业区 (标高55-65m):")
    for nid, (elev, demand_ls, desc) in south_nodes.items():
        demand = demand_ls / 1000
        node = Junction(nid, elevation=elev, demand=demand)
        topology.add_node(node)
        print(f"    - {nid}: {desc}, 需水量={demand_ls:.1f}L/s")

    # 西部居民区 (West Residential)
    west_nodes = {
        'W1': (65, 10.0, "西部高档小区"),
        'W2': (68, 8.0, "西部别墅区"),
        'W3': (70, 6.0, "西部社区"),
    }

    print("  西部居民区 (标高60-70m):")
    for nid, (elev, demand_ls, desc) in west_nodes.items():
        demand = demand_ls / 1000
        node = Junction(nid, elevation=elev, demand=demand)
        topology.add_node(node)
        print(f"    - {nid}: {desc}, 需水量={demand_ls:.1f}L/s")

    print()

    # ========== 3. 管道连接 ==========
    print("【管网拓扑】")

    # 管道配置：(pipe_id, from_node, to_node, diameter_m, length_m, K_minor, description)
    pipe_configs = [
        # 主干线 (从水源到各区)
        ('P1', 'R1', 'N1', 0.50, 1500, 1.0, "北水库->北区主干"),
        ('P2', 'R2', 'E1', 0.45, 1200, 1.0, "东水库->东区主干"),
        ('P3', 'T1', 'S1', 0.40, 800, 0.8, "水塔->南区主干"),

        # 北部居民区环路
        ('P4', 'N1', 'N2', 0.30, 600, 0.5, "北区环路1"),
        ('P5', 'N2', 'N3', 0.30, 500, 0.5, "北区环路2"),
        ('P6', 'N3', 'N4', 0.25, 450, 0.5, "北区环路3"),
        ('P7', 'N4', 'N5', 0.25, 400, 0.5, "北区环路4"),
        ('P8', 'N5', 'N1', 0.30, 550, 0.5, "北区环路5"),

        # 东部工业区环路
        ('P9', 'E1', 'E2', 0.35, 500, 0.6, "东区环路1"),
        ('P10', 'E2', 'E3', 0.30, 450, 0.6, "东区环路2"),
        ('P11', 'E3', 'E1', 0.30, 520, 0.6, "东区环路3"),

        # 南部商业区环路
        ('P12', 'S1', 'S2', 0.30, 400, 0.5, "南区环路1"),
        ('P13', 'S2', 'S3', 0.25, 350, 0.5, "南区环路2"),
        ('P14', 'S3', 'S4', 0.25, 380, 0.5, "南区环路3"),
        ('P15', 'S4', 'S1', 0.30, 420, 0.5, "南区环路4"),

        # 西部居民区环路
        ('P16', 'W1', 'W2', 0.25, 350, 0.5, "西区环路1"),
        ('P17', 'W2', 'W3', 0.20, 300, 0.5, "西区环路2"),
        ('P18', 'W3', 'W1', 0.25, 380, 0.5, "西区环路3"),

        # 区域连接管 (形成大环)
        ('P19', 'N3', 'T1', 0.35, 700, 0.8, "北区->水塔连接"),
        ('P20', 'E2', 'T1', 0.35, 650, 0.8, "东区->水塔连接"),
        ('P21', 'S2', 'W1', 0.30, 600, 0.7, "南区->西区连接"),
        ('P22', 'W1', 'N4', 0.30, 550, 0.7, "西区->北区连接"),
        ('P23', 'E3', 'S4', 0.28, 580, 0.7, "东区->南区连接"),

        # 冗余连接 (提高可靠性)
        ('P24', 'N2', 'E1', 0.25, 800, 0.8, "北区->东区冗余"),
        ('P25', 'S3', 'W2', 0.22, 650, 0.7, "南区->西区冗余"),
    ]

    for pid, from_node, to_node, D, L, K, desc in pipe_configs:
        pipe = create_pressure_pipe(pid, D, L, material='steel', K_minor=K)
        topology.add_pipe(pipe, from_node, to_node)

    print(f"   创建了 {len(pipe_configs)} 根管道")
    print(f"    - 主干线: 3根")
    print(f"    - 北部环路: 5根")
    print(f"    - 东部环路: 3根")
    print(f"    - 南部环路: 4根")
    print(f"    - 西部环路: 3根")
    print(f"    - 区域连接: 5根")
    print(f"    - 冗余连接: 2根")

    # 检测环路
    print()
    print("【网络验证】")
    loops = topology.find_loops()
    print(f"   检测到 {len(loops)} 个独立环路")
    print(f"   网络创建完成，共 {len(topology.nodes)} 个节点，{len(topology.pipes)} 根管道")

    return topology


def analyze_demand_scenarios(topology):
    """
    分析多种需水工况

    工况定义：
    - 高峰工况：需水量 x 1.8（早晚高峰、夏季用水高峰）
    - 平均工况：需水量 x 1.0（正常工作日）
    - 低谷工况：需水量 x 0.4（夜间低谷）

    Args:
        topology: 管网拓扑

    Returns:
        dict: 各工况分析结果
    """

    print()
    print("="*80)
    print("多工况水力分析")
    print("Multi-Scenario Hydraulic Analysis")
    print("="*80)
    print()

    # 保存原始需水量
    original_demands = {}
    for nid, node in topology.nodes.items():
        if hasattr(node, 'demand'):
            original_demands[nid] = node.demand

    # 定义工况
    scenarios = {
        '高峰工况': 1.8,
        '平均工况': 1.0,
        '低谷工况': 0.4,
    }

    results = {}

    for scenario_name, factor in scenarios.items():
        print(f"【{scenario_name}】 (需水量系数 = {factor})")

        # 调整需水量
        for nid, original_demand in original_demands.items():
            topology.nodes[nid].demand = original_demand * factor

        # 计算总需水量
        total_demand = sum(original_demands.values()) * factor
        print(f"  总需水量: {total_demand*1000:.1f} L/s ({total_demand*3600:.1f} m^3/h)")

        # 求解
        try:
            solver = HardyCrossSolver(topology, max_iter=200, tol=1e-4, verbose=False)
            flows, heads = solver.solve()

            converged = solver.converged

            if converged:
                print(f"   求解收敛")

                # 分析压力分布
                pressures = []
                for nid, node in topology.nodes.items():
                    if isinstance(node, Junction):
                        head = heads[nid]
                        pressure = head - node.elevation
                        pressures.append(pressure)

                min_pressure = min(pressures)
                max_pressure = max(pressures)
                avg_pressure = np.mean(pressures)

                print(f"  节点压力: 最小={min_pressure:.2f}m, 最大={max_pressure:.2f}m, 平均={avg_pressure:.2f}m")

                # 压力检查
                if min_pressure < 15:
                    print(f"     最小压力 < 15m (不满足规范要求)")
                elif min_pressure < 20:
                    print(f"     最小压力 < 20m (偏低)")
                else:
                    print(f"     压力满足要求 (>=20m)")

                # 分析流速
                velocities = []
                for pid, pipe in topology.pipes.items():
                    Q = abs(flows[pid])
                    A = np.pi * (pipe.D / 2) ** 2
                    V = Q / A
                    velocities.append(V)

                max_velocity = max(velocities)
                avg_velocity = np.mean(velocities)

                print(f"  管道流速: 最大={max_velocity:.2f}m/s, 平均={avg_velocity:.2f}m/s")

                # 流速检查
                if max_velocity > 3.0:
                    print(f"     最大流速 > 3.0m/s (可能产生水锤)")
                elif max_velocity > 2.5:
                    print(f"     最大流速 > 2.5m/s (偏高)")
                else:
                    print(f"     流速合理 (<=2.5m/s)")

                # 计算各水源供水量
                source_flows = {}
                for pid in ['P1', 'P2', 'P3']:
                    source_flows[pid] = abs(flows[pid])

                print(f"  水源供水量:")
                print(f"    R1 (北水库): {source_flows['P1']*1000:.1f} L/s ({source_flows['P1']/total_demand*100:.1f}%)")
                print(f"    R2 (东水库): {source_flows['P2']*1000:.1f} L/s ({source_flows['P2']/total_demand*100:.1f}%)")
                print(f"    T1 (水塔):   {source_flows['P3']*1000:.1f} L/s ({source_flows['P3']/total_demand*100:.1f}%)")

                results[scenario_name] = {
                    'converged': True,
                    'flows': flows.copy(),
                    'heads': heads.copy(),
                    'min_pressure': min_pressure,
                    'max_pressure': max_pressure,
                    'avg_pressure': avg_pressure,
                    'max_velocity': max_velocity,
                    'avg_velocity': avg_velocity,
                    'source_flows': source_flows.copy(),
                    'total_demand': total_demand,
                }
            else:
                print(f"   求解未收敛")
                results[scenario_name] = {'converged': False}

        except Exception as e:
            print(f"   求解失败: {e}")
            results[scenario_name] = {'converged': False, 'error': str(e)}

        print()

    # 恢复原始需水量
    for nid, original_demand in original_demands.items():
        topology.nodes[nid].demand = original_demand

    return results


def reliability_analysis(topology):
    """
    供水可靠性分析

    分析不同水源失效情况下的系统表现
    """

    print("="*80)
    print("供水可靠性分析")
    print("Supply Reliability Analysis")
    print("="*80)
    print()

    print("【分析场景】")
    print("  1. 正常工况：所有水源工作")
    print("  2. R1失效：北部水库停用")
    print("  3. R2失效：东部水库停用")
    print("  4. T1失效：中心水塔停用")
    print()

    # 保存原始水头
    original_heads = {
        'R1': topology.nodes['R1'].head,
        'R2': topology.nodes['R2'].head,
        'T1': topology.nodes['T1'].head,
    }

    scenarios = {
        '正常工况': {},
        'R1失效': {'R1': 0},
        'R2失效': {'R2': 0},
        'T1失效': {'T1': 0},
    }

    print("【可靠性评估】")
    for scenario_name, failed_sources in scenarios.items():
        print(f"{scenario_name}:")

        # 设置失效水源
        for source_id, _ in failed_sources.items():
            # 将水头设置为很低，模拟失效
            topology.nodes[source_id].head = topology.nodes[source_id].elevation + 0.1

        try:
            solver = HardyCrossSolver(topology, max_iter=200, tol=1e-4, verbose=False)
            flows, heads = solver.solve()

            if solver.converged:
                # 检查压力是否满足要求
                min_pressure = float('inf')
                critical_node = None

                for nid, node in topology.nodes.items():
                    if isinstance(node, Junction):
                        pressure = heads[nid] - node.elevation
                        if pressure < min_pressure:
                            min_pressure = pressure
                            critical_node = nid

                if min_pressure >= 15:
                    print(f"   系统正常工作，最小压力={min_pressure:.2f}m (节点{critical_node})")
                elif min_pressure >= 10:
                    print(f"   系统降级运行，最小压力={min_pressure:.2f}m (节点{critical_node})")
                else:
                    print(f"   系统供水不足，最小压力={min_pressure:.2f}m (节点{critical_node})")
            else:
                print(f"   求解未收敛，系统可能无法满足需求")

        except Exception as e:
            print(f"   分析失败: {e}")

        # 恢复原始水头
        for source_id, original_head in original_heads.items():
            topology.nodes[source_id].head = original_head

    print()


def recommendations():
    """工程优化建议"""

    print("="*80)
    print("工程优化建议")
    print("Engineering Recommendations")
    print("="*80)
    print()

    print("【1. 水源配置】")
    print("  - 主水源：北部水库R1，供水能力最强")
    print("  - 辅助水源：东部水库R2，分担东部工业区负荷")
    print("  - 调节水源：中心水塔T1，调节峰谷差异")
    print("  - 建议：增加水塔容积，提高调节能力")
    print()

    print("【2. 管网优化】")
    print("  - 主干线：适当增大管径，降低输水损失")
    print("  - 环状网络：增加冗余连接，提高供水可靠性")
    print("  - 分区供水：考虑高程差异，必要时设置减压阀")
    print("  - 管材选择：主干线用球墨铸铁，支线用HDPE")
    print()

    print("【3. 压力控制】")
    print("  - 高程点（W2, W3）：最小压力可能不足，建议设置局部增压")
    print("  - 低程点（E3）：最大压力可能过高，建议设置减压阀")
    print("  - 压力监测：在关键节点安装压力传感器")
    print()

    print("【4. 可靠性提升】")
    print("  - 水源冗余：确保任一水源失效时系统仍可运行")
    print("  - 管网冗余：增加区域间连接管，形成多路供水")
    print("  - 应急预案：制定水源切换、管道抢修预案")
    print("  - 分区阀门：各区域设置隔离阀，便于维修")
    print()

    print("【5. 运行调度】")
    print("  - 高峰工况：全开R1+R2，T1供水")
    print("  - 平均工况：R1为主，R2辅助，T1调节")
    print("  - 低谷工况：R1单独供水，T1储水")
    print("  - 经济运行：根据电价峰谷差，优化泵站运行")
    print()


def plot_results(topology, results):
    """绘制分析结果"""

    # 设置中文字体
    try:
        plt.rcParams['font.sans-serif'] = ['SimHei', 'DejaVu Sans']
        plt.rcParams['axes.unicode_minus'] = False
    except:
        pass

    fig, axes = plt.subplots(2, 2, figsize=(14, 10))

    # 子图1：各工况压力对比
    ax1 = axes[0, 0]
    scenario_names = ['高峰工况', '平均工况', '低谷工况']
    colors = ['#e74c3c', '#3498db', '#2ecc71']

    data_to_plot = []
    for scenario in scenario_names:
        if scenario in results and results[scenario].get('converged', False):
            data_to_plot.append([
                results[scenario]['min_pressure'],
                results[scenario]['avg_pressure'],
                results[scenario]['max_pressure'],
            ])

    if data_to_plot:
        x = np.arange(3)
        width = 0.25
        for i, (scenario, color) in enumerate(zip(scenario_names, colors)):
            if i < len(data_to_plot):
                ax1.bar(x + i*width, data_to_plot[i], width, label=scenario, color=color, alpha=0.8)

        ax1.set_ylabel('Pressure (m)', fontsize=11, fontweight='bold')
        ax1.set_title('Pressure Distribution Across Scenarios', fontsize=12, fontweight='bold')
        ax1.set_xticks(x + width)
        ax1.set_xticklabels(['Min', 'Avg', 'Max'])
        ax1.legend()
        ax1.grid(True, alpha=0.3)
        ax1.axhline(y=15, color='r', linestyle='--', linewidth=1, label='Min Required (15m)')

    # 子图2：各工况流速对比
    ax2 = axes[0, 1]

    velocity_data = []
    for scenario in scenario_names:
        if scenario in results and results[scenario].get('converged', False):
            velocity_data.append([
                results[scenario]['avg_velocity'],
                results[scenario]['max_velocity'],
            ])

    if velocity_data:
        x = np.arange(2)
        width = 0.25
        for i, (scenario, color) in enumerate(zip(scenario_names, colors)):
            if i < len(velocity_data):
                ax2.bar(x + i*width, velocity_data[i], width, label=scenario, color=color, alpha=0.8)

        ax2.set_ylabel('Velocity (m/s)', fontsize=11, fontweight='bold')
        ax2.set_title('Velocity Distribution Across Scenarios', fontsize=12, fontweight='bold')
        ax2.set_xticks(x + width)
        ax2.set_xticklabels(['Avg', 'Max'])
        ax2.legend()
        ax2.grid(True, alpha=0.3)
        ax2.axhline(y=3.0, color='r', linestyle='--', linewidth=1, label='Max Limit (3.0m/s)')

    # 子图3：水源供水比例（平均工况）
    ax3 = axes[1, 0]

    if '平均工况' in results and results['平均工况'].get('converged', False):
        source_flows = results['平均工况']['source_flows']
        total = sum(source_flows.values())

        labels = ['R1 (North)', 'R2 (East)', 'T1 (Center)']
        sizes = [source_flows['P1']/total*100, source_flows['P2']/total*100, source_flows['P3']/total*100]
        colors_pie = ['#3498db', '#e74c3c', '#2ecc71']

        ax3.pie(sizes, labels=labels, colors=colors_pie, autopct='%1.1f%%',
                startangle=90, textprops={'fontsize': 10, 'weight': 'bold'})
        ax3.set_title('Water Source Distribution (Average Scenario)', fontsize=12, fontweight='bold')

    # 子图4：需水量变化
    ax4 = axes[1, 1]

    demand_data = []
    for scenario in scenario_names:
        if scenario in results and results[scenario].get('converged', False):
            demand_data.append(results[scenario]['total_demand'] * 1000)  # Convert to L/s

    if demand_data:
        ax4.bar(scenario_names, demand_data, color=colors, alpha=0.8, edgecolor='black', linewidth=1.5)
        ax4.set_ylabel('Total Demand (L/s)', fontsize=11, fontweight='bold')
        ax4.set_title('Total Water Demand Across Scenarios', fontsize=12, fontweight='bold')
        ax4.grid(True, axis='y', alpha=0.3)

        # 添加数值标签
        for i, v in enumerate(demand_data):
            ax4.text(i, v + max(demand_data)*0.02, f'{v:.1f}', ha='center', va='bottom', fontweight='bold')

    plt.tight_layout()

    # 保存图片
    output_path = os.path.join(os.path.dirname(__file__), 'regional_water_supply_results.png')
    plt.savefig(output_path, dpi=150, bbox_inches='tight')
    print(f" 结果图表已保存: {output_path}")

    plt.close()


def main():
    """主函数"""

    # 打印标题
    print()
    print("╔" + "="*78 + "╗")
    print("║" + " "*22 + "区域供水管网系统分析" + " "*22 + "║")
    print("║" + " "*16 + "Regional Water Supply Network Analysis" + " "*16 + "║")
    print("╚" + "="*78 + "╝")
    print()

    # 1. 创建管网
    topology = create_regional_network()

    # 2. 多工况分析
    results = analyze_demand_scenarios(topology)

    # 3. 可靠性分析
    reliability_analysis(topology)

    # 4. 工程建议
    recommendations()

    # 5. 绘制结果
    plot_results(topology, results)

    print("="*80)
    print(" 案例分析完成！")
    print("="*80)
    print()


if __name__ == '__main__':
    main()
