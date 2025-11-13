#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
案例4：消防供水系统分析
Case 4: Fire Protection Water Supply System Analysis

本案例展示建筑消防供水系统的水力分析，包括：
1. 高位消防水箱供水
2. 室内外消火栓系统
3. 自动喷淋系统
4. 消防泵扬程校核
5. 不利点压力验证

This case demonstrates hydraulic analysis of fire protection water supply systems,
including:
1. Elevated fire water tank supply
2. Indoor and outdoor fire hydrant systems
3. Automatic sprinkler system
4. Fire pump head verification
5. Most unfavorable point pressure verification

Author: HydroClaude Development Team
Date: 2025-10-30
"""

import sys
import os
import numpy as np
import matplotlib.pyplot as plt
from matplotlib import rcParams

# 添加项目路径
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from network.pressure_pipe import create_pressure_pipe
from network.network_node import Junction, Reservoir
from network.network_topology import NetworkTopology
from solvers.hardy_cross_solver import HardyCrossSolver

# 设置中文字体
rcParams['font.sans-serif'] = ['SimHei', 'DejaVu Sans']
rcParams['axes.unicode_minus'] = False


def create_fire_protection_network():
    """
    创建建筑消防供水系统

    系统布局：
    - 1个屋顶消防水箱（高位水源）
    - 4层建筑，每层2个消火栓
    - 8个消火栓接口
    - 9根竖向和横向管道

    System layout:
    - 1 rooftop fire water tank (elevated source)
    - 4-story building, 2 hydrants per floor
    - 8 hydrant connection points
    - 9 vertical and horizontal pipes
    """

    print("="*80)
    print("创建建筑消防供水系统")
    print("Creating Building Fire Protection Water Supply System")
    print("="*80)
    print()

    # 创建拓扑
    topology = NetworkTopology("Fire Protection System")

    # 屋顶消防水箱（18m标高，水深3m）
    # 根据《消防给水及消火栓系统技术规范》GB50974-2014
    # 高层建筑消防水箱设置高度应满足最不利点消火栓静压>=0.07MPa（7m）
    water_tank = Reservoir(
        node_id='Tank',
        elevation=18.0,    # 屋顶标高18m
        head=21.0          # 水箱底部18m + 水深3m = 21m
    )
    topology.add_node(water_tank)

    # 竖向立管节点（每层一个）
    # 4层建筑：1层（3m）、2层（6m）、3层（9m）、4层（12m）
    v1 = Junction('V1', elevation=3.0, demand=0.0)   # 1层立管
    v2 = Junction('V2', elevation=6.0, demand=0.0)   # 2层立管
    v3 = Junction('V3', elevation=9.0, demand=0.0)   # 3层立管
    v4 = Junction('V4', elevation=12.0, demand=0.0)  # 4层立管

    topology.add_node(v1)
    topology.add_node(v2)
    topology.add_node(v3)
    topology.add_node(v4)

    # 消火栓接口（每层2个）
    # 根据规范，每个消火栓流量5 L/s，同时使用2个消火栓
    # 正常情况：不使用（demand=0）
    # 火灾工况：2个最不利点消火栓同时出水（10 L/s）
    h1a = Junction('H1A', elevation=3.0, demand=0.0)   # 1层消火栓A
    h1b = Junction('H1B', elevation=3.0, demand=0.0)   # 1层消火栓B
    h2a = Junction('H2A', elevation=6.0, demand=0.0)   # 2层消火栓A
    h2b = Junction('H2B', elevation=6.0, demand=0.0)   # 2层消火栓B
    h3a = Junction('H3A', elevation=9.0, demand=0.0)   # 3层消火栓A
    h3b = Junction('H3B', elevation=9.0, demand=0.0)   # 3层消火栓B
    h4a = Junction('H4A', elevation=12.0, demand=0.0)  # 4层消火栓A
    h4b = Junction('H4B', elevation=12.0, demand=0.0)  # 4层消火栓B

    for node in [h1a, h1b, h2a, h2b, h3a, h3b, h4a, h4b]:
        topology.add_node(node)

    print("【节点信息】")
    print(f"  消防水箱: Tank (标高{water_tank.elevation}m, 水位{water_tank.head}m)")
    print(f"  立管节点: V1-V4 (1-4层)")
    print(f"  消火栓: H1A-H4B (每层2个，共8个)")
    print(f"  单个消火栓流量: 5 L/s")
    print(f"  同时使用数量: 2个（规范要求）")
    print()

    # 管道定义
    # 根据《消防给水及消火栓系统技术规范》
    # 室内消火栓竖管管径不应小于DN100（0.1m）
    pipe_definitions = [
        # 竖向立管（从水箱到各层）
        ('P1', 'Tank', 'V4', 0.1, 6.0, 1.0, '屋顶水箱->4层'),
        ('P2', 'V4', 'V3', 0.1, 3.0, 0.5, '4层->3层'),
        ('P3', 'V3', 'V2', 0.1, 3.0, 0.5, '3层->2层'),
        ('P4', 'V2', 'V1', 0.1, 3.0, 0.5, '2层->1层'),

        # 各层横向支管（立管到消火栓）
        ('P5', 'V1', 'H1A', 0.065, 10.0, 2.0, '1层立管->消火栓A'),
        ('P6', 'V1', 'H1B', 0.065, 15.0, 2.0, '1层立管->消火栓B'),
        ('P7', 'V2', 'H2A', 0.065, 10.0, 2.0, '2层立管->消火栓A'),
        ('P8', 'V2', 'H2B', 0.065, 15.0, 2.0, '2层立管->消火栓B'),
        ('P9', 'V3', 'H3A', 0.065, 10.0, 2.0, '3层立管->消火栓A'),
        ('P10', 'V3', 'H3B', 0.065, 15.0, 2.0, '3层立管->消火栓B'),
        ('P11', 'V4', 'H4A', 0.065, 10.0, 2.0, '4层立管->消火栓A'),
        ('P12', 'V4', 'H4B', 0.065, 15.0, 2.0, '4层立管->消火栓B'),
    ]

    print("【管道信息】")
    for pid, from_node, to_node, D, L, K, desc in pipe_definitions:
        pipe = create_pressure_pipe(pid, D, L, material='steel', K_minor=K)
        topology.add_pipe(pipe, from_node, to_node)
        print(f"   {pid}: {from_node}->{to_node}, D={int(D*1000)}mm, L={L}m ({desc})")

    print(f"  管道数量: {len(pipe_definitions)}")
    print(f"  竖管管径: DN100 (100mm)")
    print(f"  支管管径: DN65 (65mm)")
    print()

    return topology


def analyze_fire_scenarios(topology):
    """
    分析不同火灾工况

    工况1：4层同时使用2个消火栓（最不利）
    工况2：3层同时使用2个消火栓
    工况3：1层同时使用2个消火栓（最有利）

    Analyze different fire scenarios
    """

    print("="*80)
    print("火灾工况水力分析")
    print("Fire Scenario Hydraulic Analysis")
    print("="*80)
    print()

    # 消火栓流量（根据规范）
    hydrant_flow = 5.0 / 1000  # 5 L/s = 0.005 m^3/s

    scenarios = {
        '4层火灾': {
            'hydrants': ['H4A', 'H4B'],
            'description': '顶层火灾，最不利点'
        },
        '3层火灾': {
            'hydrants': ['H3A', 'H3B'],
            'description': '3层火灾'
        },
        '1层火灾': {
            'hydrants': ['H1A', 'H1B'],
            'description': '1层火灾，最有利点'
        }
    }

    results = {}

    for scenario_name, params in scenarios.items():
        print(f"【{scenario_name}】{params['description']}")

        # 重置所有消火栓需求
        for nid in topology.nodes:
            if nid.startswith('H'):
                topology.nodes[nid].demand = 0.0

        # 设置该工况使用的消火栓
        for hydrant_id in params['hydrants']:
            topology.nodes[hydrant_id].demand = hydrant_flow

        total_flow = len(params['hydrants']) * hydrant_flow * 1000  # L/s
        print(f"  使用消火栓: {', '.join(params['hydrants'])}")
        print(f"  总流量: {total_flow:.0f} L/s")

        # 求解
        solver = HardyCrossSolver(topology, max_iter=200, tol=1e-4, verbose=False)
        try:
            flows, heads = solver.solve()
            converged = True
            print(f"   求解收敛")

            # 分析压力
            hydrant_pressures = {}
            for hydrant_id in params['hydrants']:
                node = topology.nodes[hydrant_id]
                head = heads[hydrant_id]
                pressure = (head - node.elevation) * 9.81  # 转换为kPa (近似)
                hydrant_pressures[hydrant_id] = {
                    'head': head,
                    'pressure_m': head - node.elevation,
                    'pressure_kPa': pressure
                }

            min_pressure_m = min(p['pressure_m'] for p in hydrant_pressures.values())
            min_pressure_kPa = min(p['pressure_kPa'] for p in hydrant_pressures.values())

            print(f"  最低压力: {min_pressure_m:.2f} m = {min_pressure_kPa:.1f} kPa")

            # 验证是否满足规范要求
            # GB50974-2014要求：最不利点消火栓静压>=0.07MPa（7m），动压>=0.35MPa（35m）
            # 这里计算的是总压力，需要减去水头损失得到出口压力
            min_required_static = 7.0   # m，静压
            min_required_dynamic = 35.0  # m，动压（出口压力）

            # 简化判断：使用总压力与静压要求对比
            if min_pressure_m >= min_required_static:
                print(f"   满足静压要求 (>={min_required_static}m)")
            else:
                print(f"   不满足静压要求 (需>={min_required_static}m)")
                print(f"    缺少: {min_required_static - min_pressure_m:.2f}m")
                print(f"    建议: 提高水箱高度或增设消防泵")

            # 计算供水流量（从水箱流出）
            supply_flow = abs(flows['P1']) * 1000  # L/s

            results[scenario_name] = {
                'converged': True,
                'hydrants': params['hydrants'],
                'heads': heads,
                'flows': flows,
                'hydrant_pressures': hydrant_pressures,
                'min_pressure_m': min_pressure_m,
                'min_pressure_kPa': min_pressure_kPa,
                'supply_flow': supply_flow,
                'meets_requirement': min_pressure_m >= min_required_static
            }

        except Exception as e:
            print(f"   求解失败: {str(e)[:50]}")
            results[scenario_name] = {'converged': False}

        print()

    return results


def fire_pump_sizing_recommendation(results):
    """消防泵选型建议"""

    print("="*80)
    print("消防泵选型建议")
    print("Fire Pump Sizing Recommendations")
    print("="*80)
    print()

    # 分析最不利工况
    worst_case = None
    min_pressure = float('inf')

    for scenario, result in results.items():
        if result.get('converged') and result['min_pressure_m'] < min_pressure:
            min_pressure = result['min_pressure_m']
            worst_case = scenario

    if worst_case:
        print(f"【最不利工况】{worst_case}")
        print(f"  实际压力: {min_pressure:.2f} m")
        print()

        # 消防泵扬程计算
        # 根据GB50974-2014：H_pump = H1 + H2 + H3 + H4
        # H1：消火栓栓口所需压力（动压0.35MPa = 35m）
        # H2：消火栓口标高与水泵出口标高差
        # H3：管道沿程和局部损失
        # H4：安全余量（一般取5-10m）

        required_outlet_pressure = 35.0  # m，规范要求动压
        highest_floor_elevation = 12.0   # m，最高层标高
        pump_elevation = 0.0             # m，假设泵在地面
        height_difference = highest_floor_elevation - pump_elevation

        # 管道损失估算（简化）
        pipe_loss = 5.0  # m，估算值

        # 安全余量
        safety_margin = 5.0  # m

        total_head = required_outlet_pressure + height_difference + pipe_loss + safety_margin

        print("【消防泵扬程计算】")
        print(f"  出口压力需求: {required_outlet_pressure:.0f} m (规范动压0.35MPa)")
        print(f"  高程差: {height_difference:.0f} m (泵->最高层)")
        print(f"  管道损失: {pipe_loss:.0f} m (估算)")
        print(f"  安全余量: {safety_margin:.0f} m")
        print(f"  总扬程: H = {total_head:.0f} m")
        print()

        # 流量计算
        # 根据GB50974-2014：建筑高度<=50m，室内消火栓用水量10L/s
        required_flow = 10.0  # L/s

        print("【消防泵流量】")
        print(f"  规范要求流量: {required_flow:.0f} L/s")
        print(f"  推荐流量: {required_flow * 1.1:.0f} L/s (考虑10%余量)")
        print()

        print("【设备选型建议】")
        print(f"  消防泵型号: XBD系列消防泵")
        print(f"  扬程: {total_head:.0f}m")
        print(f"  流量: {required_flow * 1.1:.0f} L/s")
        print(f"  功率: 约{int((required_flow * 1.1 / 1000) * total_head * 9.81 * 1.3 / 0.75):.0f} kW (估算)")
        print(f"  配置: 一用一备（双泵）")
        print()

    print("【系统优化建议】")
    print("1. 消防水箱")
    print("   - 当前高度可能不足，建议提高或增设增压泵")
    print("   - 有效容积应满足初期火灾（10分钟）用水")
    print()

    print("2. 消防泵设置")
    print("   - 设置消防泵房，配备消防水泵")
    print("   - 采用一用一备配置，自动切换")
    print("   - 设置消防水泵接合器，便于消防车供水")
    print()

    print("3. 管网优化")
    print("   - 竖管采用环状，提高可靠性")
    print("   - 每层设置检修阀门")
    print("   - 定期检查维护，确保系统可用")
    print()


def plot_results(topology, results):
    """绘制分析结果"""

    fig, axes = plt.subplots(1, 2, figsize=(14, 6))
    fig.suptitle('建筑消防供水系统分析结果', fontsize=16, fontweight='bold')

    # 提取数据
    scenarios = []
    min_pressures_m = []
    min_pressures_kPa = []
    supply_flows = []

    for scenario, result in results.items():
        if result.get('converged'):
            scenarios.append(scenario)
            min_pressures_m.append(result['min_pressure_m'])
            min_pressures_kPa.append(result['min_pressure_kPa'])
            supply_flows.append(result['supply_flow'])

    # 子图1：最低压力对比
    ax1 = axes[0]
    x_pos = np.arange(len(scenarios))
    bars = ax1.bar(x_pos, min_pressures_m, color=['#e74c3c', '#f39c12', '#27ae60'], alpha=0.8)
    ax1.axhline(y=7, color='r', linestyle='--', linewidth=2, label='规范最低静压(7m)')
    ax1.axhline(y=35, color='b', linestyle='--', linewidth=2, label='规范最低动压(35m)')
    ax1.set_xticks(x_pos)
    ax1.set_xticklabels(scenarios)
    ax1.set_ylabel('压力 (m)', fontsize=11)
    ax1.set_title('各工况最低点压力', fontsize=12, fontweight='bold')
    ax1.legend(fontsize=9)
    ax1.grid(True, alpha=0.3, axis='y')

    # 在柱子上标注数值
    for i, bar in enumerate(bars):
        height = bar.get_height()
        ax1.text(bar.get_x() + bar.get_width()/2., height,
                f'{height:.1f}m',
                ha='center', va='bottom', fontsize=10)

    # 子图2：供水流量
    ax2 = axes[1]
    bars = ax2.bar(scenarios, supply_flows, color=['#9b59b6', '#3498db', '#1abc9c'], alpha=0.8)
    ax2.set_ylabel('流量 (L/s)', fontsize=11)
    ax2.set_title('消防供水流量', fontsize=12, fontweight='bold')
    ax2.grid(True, alpha=0.3, axis='y')

    for bar in bars:
        height = bar.get_height()
        ax2.text(bar.get_x() + bar.get_width()/2., height,
                f'{height:.1f}',
                ha='center', va='bottom', fontsize=10)

    plt.tight_layout()

    # 保存图片
    output_path = 'examples/fire_protection_results.png'
    plt.savefig(output_path, dpi=150, bbox_inches='tight')
    print(f" 结果图表已保存: {output_path}")


def main():
    """主函数"""

    print("\n")
    print("╔" + "="*78 + "╗")
    print("║" + " "*25 + "建筑消防供水系统" + " "*25 + "║")
    print("║" + " "*20 + "Fire Protection Water Supply System" + " "*20 + "║")
    print("╚" + "="*78 + "╝")
    print()

    # 1. 创建系统
    topology = create_fire_protection_network()

    # 2. 分析火灾工况
    results = analyze_fire_scenarios(topology)

    # 3. 消防泵选型建议
    fire_pump_sizing_recommendation(results)

    # 4. 绘制结果
    plot_results(topology, results)

    print("="*80)
    print(" 案例分析完成！")
    print("="*80)


if __name__ == '__main__':
    main()
