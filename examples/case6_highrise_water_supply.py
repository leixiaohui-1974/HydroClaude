#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
案例6：高层建筑分区供水系统
Case 6: High-Rise Building Zoned Water Supply System

本案例展示高层建筑分区供水系统的水力分析，包括：
1. 三区供水（低区/中区/高区）
2. 各区独立水箱供水
3. 不同楼层用水分析
4. 压力分区控制
5. 减压和增压措施

This case demonstrates hydraulic analysis of high-rise building zoned water supply,
including:
1. Three-zone supply (low/middle/high)
2. Independent water tanks for each zone
3. Water use analysis at different floors
4. Pressure zone control
5. Pressure reduction and boosting measures

Author: HydroClaude Development Team
Date: 2025-10-30
"""

import sys
import warnings
warnings.filterwarnings("ignore")
import os
import numpy as np
import matplotlib.pyplot as plt
from matplotlib import rcParams

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from network.pressure_pipe import create_pressure_pipe
from network.network_node import Junction, Reservoir
from network.network_topology import NetworkTopology
from solvers.hardy_cross_solver import HardyCrossSolver

rcParams['font.sans-serif'] = ['SimHei', 'DejaVu Sans']
rcParams['axes.unicode_minus'] = False


def create_highrise_supply_network():
    """
    创建30层高层建筑分区供水系统

    分区方案：
    - 低区：1-10层（市政直供+低区水箱）
    - 中区：11-20层（中区泵+中区水箱）
    - 高区：21-30层（高区泵+高区水箱）
    """

    print("="*80)
    print("创建高层建筑分区供水系统")
    print("Creating High-Rise Building Zoned Water Supply System")
    print("="*80)
    print()

    topology = NetworkTopology("High-Rise Water Supply")

    # 假设每层高度3m，共30层，总高90m
    # 分区供水：低区(0-30m), 中区(30-60m), 高区(60-90m)

    # 各区水箱（模拟恒定水头）
    tank_low = Reservoir('TL', elevation=30.0, head=33.0)   # 低区水箱10层顶
    tank_mid = Reservoir('TM', elevation=60.0, head=63.0)   # 中区水箱20层顶
    tank_high = Reservoir('TH', elevation=90.0, head=93.0)  # 高区水箱30层顶

    topology.add_node(tank_low)
    topology.add_node(tank_mid)
    topology.add_node(tank_high)

    # 各区代表楼层节点（简化：每区选3层）
    # 低区：2层、6层、9层
    # 中区：12层、16层、19层
    # 高区：22层、26层、29层

    # 每户用水量约0.5 L/s，每层假设4户
    floor_demand = 4 * 0.5 / 1000  # m^3/s

    # 低区节点
    f2 = Junction('F2', elevation=6.0, demand=floor_demand)
    f6 = Junction('F6', elevation=18.0, demand=floor_demand)
    f9 = Junction('F9', elevation=27.0, demand=floor_demand)

    # 中区节点
    f12 = Junction('F12', elevation=36.0, demand=floor_demand)
    f16 = Junction('F16', elevation=48.0, demand=floor_demand)
    f19 = Junction('F19', elevation=57.0, demand=floor_demand)

    # 高区节点
    f22 = Junction('F22', elevation=66.0, demand=floor_demand)
    f26 = Junction('F26', elevation=78.0, demand=floor_demand)
    f29 = Junction('F29', elevation=87.0, demand=floor_demand)

    for node in [f2, f6, f9, f12, f16, f19, f22, f26, f29]:
        topology.add_node(node)

    print("【分区方案】")
    print(f"  低区 (1-10层):  水箱标高 {tank_low.elevation}m")
    print(f"  中区 (11-20层): 水箱标高 {tank_mid.elevation}m")
    print(f"  高区 (21-30层): 水箱标高 {tank_high.elevation}m")
    print(f"  每层需水量: {floor_demand*1000:.1f} L/s (4户x0.5L/s)")
    print()

    # 管道定义（竖管DN100，支管DN50）
    pipe_definitions = [
        # 低区竖管及支管
        ('P1', 'TL', 'F9', 0.1, 6.0, 0.5, '低区水箱->9层'),
        ('P2', 'F9', 'F6', 0.1, 9.0, 0.5, '9层->6层'),
        ('P3', 'F6', 'F2', 0.1, 12.0, 0.5, '6层->2层'),

        # 中区竖管及支管
        ('P4', 'TM', 'F19', 0.1, 6.0, 0.5, '中区水箱->19层'),
        ('P5', 'F19', 'F16', 0.1, 9.0, 0.5, '19层->16层'),
        ('P6', 'F16', 'F12', 0.1, 12.0, 0.5, '16层->12层'),

        # 高区竖管及支管
        ('P7', 'TH', 'F29', 0.1, 6.0, 0.5, '高区水箱->29层'),
        ('P8', 'F29', 'F26', 0.1, 9.0, 0.5, '29层->26层'),
        ('P9', 'F26', 'F22', 0.1, 12.0, 0.5, '26层->22层'),
    ]

    print("【管道信息】")
    for pid, from_node, to_node, D, L, K, desc in pipe_definitions:
        pipe = create_pressure_pipe(pid, D, L, material='steel', K_minor=K)
        topology.add_pipe(pipe, from_node, to_node)
        print(f"   {pid}: {from_node}->{to_node}, D={int(D*1000)}mm ({desc})")

    print()
    return topology


def analyze_single_zone(tank_node, floor_nodes, pipe_defs, zone_name):
    """分析单个分区"""

    # 创建该区的独立拓扑
    zone_topo = NetworkTopology(f"{zone_name} Zone")

    # 添加水箱和楼层节点
    zone_topo.add_node(tank_node)
    for node in floor_nodes:
        zone_topo.add_node(node)

    # 添加管道
    for pid, from_node, to_node, D, L, K in pipe_defs:
        pipe = create_pressure_pipe(pid, D, L, material='steel', K_minor=K)
        zone_topo.add_pipe(pipe, from_node, to_node)

    # 求解
    solver = HardyCrossSolver(zone_topo, max_iter=200, tol=1e-4, verbose=False)
    flows, heads = solver.solve()

    # 分析压力
    zone_pressures = []
    for node in floor_nodes:
        head = heads[node.node_id]
        pressure_m = head - node.elevation
        pressure_mpa = pressure_m * 0.00981

        floor_num = int(node.node_id[1:])
        zone_pressures.append({
            'floor': floor_num,
            'pressure_m': pressure_m,
            'pressure_mpa': pressure_mpa
        })

    return zone_pressures


def analyze_pressure_zones(topology):
    """分析各区压力分布"""

    print("="*80)
    print("各分区压力分析")
    print("Pressure Analysis for Each Zone")
    print("="*80)
    print()

    all_results = {}

    # 每户用水量
    floor_demand = 4 * 0.5 / 1000

    # 低区
    tank_low = Reservoir('TL', elevation=30.0, head=33.0)
    f2 = Junction('F2', elevation=6.0, demand=floor_demand)
    f6 = Junction('F6', elevation=18.0, demand=floor_demand)
    f9 = Junction('F9', elevation=27.0, demand=floor_demand)

    low_pipes = [
        ('P1', 'TL', 'F9', 0.1, 6.0, 0.5),
        ('P2', 'F9', 'F6', 0.1, 9.0, 0.5),
        ('P3', 'F6', 'F2', 0.1, 12.0, 0.5),
    ]

    print("【低区】")
    try:
        zone_pressures = analyze_single_zone(tank_low, [f2, f6, f9], low_pipes, '低区')

        for p in zone_pressures:
            print(f"  {p['floor']}层: 压力 {p['pressure_m']:.2f}m = {p['pressure_mpa']:.3f}MPa")

        min_p = min(p['pressure_m'] for p in zone_pressures)
        max_p = max(p['pressure_m'] for p in zone_pressures)
        print(f"  压力范围: {min_p:.2f} ~ {max_p:.2f} m")

        if min_p < 5.0:
            print(f"   最低压力不足 (需>=5m)")
        elif max_p > 35.0:
            print(f"   最高压力过大 (需<=35m)，建议设置减压阀")
        else:
            print(f"   压力范围合理 (5-35m)")

        all_results['低区'] = {
            'floors': zone_pressures,
            'min_pressure': min_p,
            'max_pressure': max_p
        }
    except Exception as e:
        print(f"   求解失败: {e}")

    print()

    # 中区
    tank_mid = Reservoir('TM', elevation=60.0, head=63.0)
    f12 = Junction('F12', elevation=36.0, demand=floor_demand)
    f16 = Junction('F16', elevation=48.0, demand=floor_demand)
    f19 = Junction('F19', elevation=57.0, demand=floor_demand)

    mid_pipes = [
        ('P4', 'TM', 'F19', 0.1, 6.0, 0.5),
        ('P5', 'F19', 'F16', 0.1, 9.0, 0.5),
        ('P6', 'F16', 'F12', 0.1, 12.0, 0.5),
    ]

    print("【中区】")
    try:
        zone_pressures = analyze_single_zone(tank_mid, [f12, f16, f19], mid_pipes, '中区')

        for p in zone_pressures:
            print(f"  {p['floor']}层: 压力 {p['pressure_m']:.2f}m = {p['pressure_mpa']:.3f}MPa")

        min_p = min(p['pressure_m'] for p in zone_pressures)
        max_p = max(p['pressure_m'] for p in zone_pressures)
        print(f"  压力范围: {min_p:.2f} ~ {max_p:.2f} m")

        if min_p < 5.0:
            print(f"   最低压力不足 (需>=5m)")
        elif max_p > 35.0:
            print(f"   最高压力过大 (需<=35m)，建议设置减压阀")
        else:
            print(f"   压力范围合理 (5-35m)")

        all_results['中区'] = {
            'floors': zone_pressures,
            'min_pressure': min_p,
            'max_pressure': max_p
        }
    except Exception as e:
        print(f"   求解失败: {e}")

    print()

    # 高区
    tank_high = Reservoir('TH', elevation=90.0, head=93.0)
    f22 = Junction('F22', elevation=66.0, demand=floor_demand)
    f26 = Junction('F26', elevation=78.0, demand=floor_demand)
    f29 = Junction('F29', elevation=87.0, demand=floor_demand)

    high_pipes = [
        ('P7', 'TH', 'F29', 0.1, 6.0, 0.5),
        ('P8', 'F29', 'F26', 0.1, 9.0, 0.5),
        ('P9', 'F26', 'F22', 0.1, 12.0, 0.5),
    ]

    print("【高区】")
    try:
        zone_pressures = analyze_single_zone(tank_high, [f22, f26, f29], high_pipes, '高区')

        for p in zone_pressures:
            print(f"  {p['floor']}层: 压力 {p['pressure_m']:.2f}m = {p['pressure_mpa']:.3f}MPa")

        min_p = min(p['pressure_m'] for p in zone_pressures)
        max_p = max(p['pressure_m'] for p in zone_pressures)
        print(f"  压力范围: {min_p:.2f} ~ {max_p:.2f} m")

        if min_p < 5.0:
            print(f"   最低压力不足 (需>=5m)")
        elif max_p > 35.0:
            print(f"   最高压力过大 (需<=35m)，建议设置减压阀")
        else:
            print(f"   压力范围合理 (5-35m)")

        all_results['高区'] = {
            'floors': zone_pressures,
            'min_pressure': min_p,
            'max_pressure': max_p
        }
    except Exception as e:
        print(f"   求解失败: {e}")

    print()

    return all_results


def pressure_control_recommendations():
    """压力控制建议"""

    print("="*80)
    print("压力控制与优化建议")
    print("Pressure Control and Optimization Recommendations")
    print("="*80)
    print()

    print("【1. 分区供水原则】")
    print("  - 垂直分区：每区高度不超过50m")
    print("  - 压力分区：入户压力控制在0.05-0.35MPa")
    print("  - 独立系统：各区独立水箱和泵站")
    print("  - 互为备用：相邻区可紧急连通")
    print()

    print("【2. 减压措施】")
    print("  - 低区底层：安装减压阀或减压孔板")
    print("  - 减压阀设置：楼层压力>0.35MPa时必须设置")
    print("  - 串联减压：压差大时采用串联减压")
    print("  - 支管减压：在各户支管上设置")
    print()

    print("【3. 泵站设计】")
    print("  - 中高区泵站：采用变频调速泵")
    print("  - 配置方案：一用一备或两用一备")
    print("  - 扬程计算：H = H1 + H2 + H3")
    print("    H1: 最高层压力要求 (15m)")
    print("    H2: 提升高度 (分区高差)")
    print("    H3: 管道损失 (5-8m)")
    print()

    print("【4. 水箱设置】")
    print("  - 有效容积：满足该区1-2小时用水")
    print("  - 设置位置：各区最高层顶部")
    print("  - 水位控制：浮球阀+液位传感器")
    print("  - 溢流排空：安全装置必须完善")
    print()

    print("【5. 节能措施】")
    print("  - 变频泵：根据用水量自动调节")
    print("  - 分时供水：夜间低负荷运行")
    print("  - 管网优化：减少管道弯头和阀门")
    print("  - 漏损控制：定期检漏，及时维修")
    print()


def plot_results(results):
    """绘制压力分布图"""

    if not results:
        print("无数据可绘制")
        return

    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(14, 6))
    fig.suptitle('高层建筑分区供水压力分析', fontsize=16, fontweight='bold')

    # 子图1：各楼层压力分布
    colors = {'低区': '#3498db', '中区': '#2ecc71', '高区': '#e74c3c'}

    for zone_name, data in results.items():
        floors = [f['floor'] for f in data['floors']]
        pressures = [f['pressure_m'] for f in data['floors']]
        ax1.plot(pressures, floors, 'o-', label=zone_name,
                 color=colors[zone_name], linewidth=2, markersize=8)

    ax1.axvline(x=5, color='g', linestyle='--', linewidth=1.5, label='最低要求(5m)')
    ax1.axvline(x=35, color='r', linestyle='--', linewidth=1.5, label='最高限制(35m)')
    ax1.set_xlabel('压力 (m)', fontsize=11)
    ax1.set_ylabel('楼层', fontsize=11)
    ax1.set_title('各楼层压力分布', fontsize=12, fontweight='bold')
    ax1.legend(fontsize=10)
    ax1.grid(True, alpha=0.3)

    # 子图2：各区压力范围
    zones = list(results.keys())
    min_pressures = [results[z]['min_pressure'] for z in zones]
    max_pressures = [results[z]['max_pressure'] for z in zones]

    x = np.arange(len(zones))
    width = 0.35

    ax2.bar(x - width/2, min_pressures, width, label='最低压力',
            color='#3498db', alpha=0.8)
    ax2.bar(x + width/2, max_pressures, width, label='最高压力',
            color='#e74c3c', alpha=0.8)

    ax2.axhline(y=5, color='g', linestyle='--', linewidth=1.5)
    ax2.axhline(y=35, color='r', linestyle='--', linewidth=1.5)
    ax2.set_xticks(x)
    ax2.set_xticklabels(zones)
    ax2.set_ylabel('压力 (m)', fontsize=11)
    ax2.set_title('各区压力范围', fontsize=12, fontweight='bold')
    ax2.legend(fontsize=10)
    ax2.grid(True, alpha=0.3, axis='y')

    plt.tight_layout()

    output_path = 'examples/highrise_water_supply_results.png'
    plt.savefig(output_path, dpi=150, bbox_inches='tight')
    print(f" 结果图表已保存: {output_path}")


def main():
    """主函数"""

    print("\n")
    print("╔" + "="*78 + "╗")
    print("║" + " "*23 + "高层建筑分区供水系统" + " "*23 + "║")
    print("║" + " "*16 + "High-Rise Building Zoned Water Supply System" + " "*16 + "║")
    print("╚" + "="*78 + "╝")
    print()

    # 1. 创建系统
    topology = create_highrise_supply_network()

    # 2. 分析压力分布
    results = analyze_pressure_zones(topology)

    # 3. 控制建议
    pressure_control_recommendations()

    # 4. 绘制结果
    plot_results(results)

    print("="*80)
    print(" 案例分析完成！")
    print("="*80)


if __name__ == '__main__':
    main()
