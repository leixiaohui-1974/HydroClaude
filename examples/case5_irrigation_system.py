#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
案例5：农业灌溉系统分析
Case 5: Agricultural Irrigation System Analysis

本案例展示农业灌溉系统的水力分析，包括：
1. 大面积农田灌溉管网
2. 多个灌溉分区
3. 不同作物需水量
4. 季节性用水变化
5. 喷灌和滴灌工况

This case demonstrates hydraulic analysis of agricultural irrigation systems,
including:
1. Large-area farmland irrigation network
2. Multiple irrigation zones
3. Different crop water requirements
4. Seasonal water demand variations
5. Sprinkler and drip irrigation conditions

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

# 添加项目路径
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from network.pressure_pipe import create_pressure_pipe
from network.network_node import Junction, Reservoir
from network.network_topology import NetworkTopology
from solvers.hardy_cross_solver import HardyCrossSolver

# 设置中文字体
rcParams['font.sans-serif'] = ['SimHei', 'DejaVu Sans']
rcParams['axes.unicode_minus'] = False


def create_irrigation_network():
    """
    创建农业灌溉系统

    系统布局：
    - 1个提水泵站（恒定水头）
    - 6个灌溉分区（不同作物）
    - 环状主管 + 支管分配
    - 10根管道

    System layout:
    - 1 water pumping station (constant head)
    - 6 irrigation zones (different crops)
    - Looped main pipe + branch distribution
    - 10 pipes
    """

    print("="*80)
    print("创建农业灌溉系统")
    print("Creating Agricultural Irrigation System")
    print("="*80)
    print()

    # 创建拓扑
    topology = NetworkTopology("Irrigation System")

    # 泵站（提水后恒定水头）
    # 假设泵扬程30m，水源标高0m
    pump_station = Reservoir(
        node_id='Pump',
        elevation=0.0,
        head=30.0  # 泵后压力30m
    )
    topology.add_node(pump_station)

    # 主管网节点（环状）
    j1 = Junction('J1', elevation=0.0, demand=0.0)  # 主管分支点1
    j2 = Junction('J2', elevation=0.0, demand=0.0)  # 主管分支点2
    j3 = Junction('J3', elevation=0.0, demand=0.0)  # 主管分支点3

    topology.add_node(j1)
    topology.add_node(j2)
    topology.add_node(j3)

    # 灌溉分区（6个不同作物区）
    # 灌溉需水量根据作物类型、面积、季节而定
    # 这里假设不同的基准需水量

    # 作物分区：
    # Z1-Z2: 蔬菜区（需水量大）
    # Z3-Z4: 果树区（需水量中等）
    # Z5-Z6: 大田作物（需水量较小）

    zone1 = Junction('Z1', elevation=0.0, demand=0.08)  # 蔬菜1，80 L/s
    zone2 = Junction('Z2', elevation=0.0, demand=0.07)  # 蔬菜2，70 L/s
    zone3 = Junction('Z3', elevation=0.0, demand=0.05)  # 果树1，50 L/s
    zone4 = Junction('Z4', elevation=0.0, demand=0.045) # 果树2，45 L/s
    zone5 = Junction('Z5', elevation=0.0, demand=0.03)  # 大田1，30 L/s
    zone6 = Junction('Z6', elevation=0.0, demand=0.025) # 大田2，25 L/s

    topology.add_node(zone1)
    topology.add_node(zone2)
    topology.add_node(zone3)
    topology.add_node(zone4)
    topology.add_node(zone5)
    topology.add_node(zone6)

    print("【节点信息】")
    print(f"  泵站: Pump (扬程30m)")
    print(f"  主管节点: J1, J2, J3")
    print(f"  灌溉分区: Z1-Z6")
    print(f"    Z1-Z2: 蔬菜区 (总需水 150 L/s)")
    print(f"    Z3-Z4: 果树区 (总需水 95 L/s)")
    print(f"    Z5-Z6: 大田区 (总需水 55 L/s)")
    print(f"  总需水量: 300 L/s")
    print()

    # 管道定义
    # 灌溉系统通常采用PVC管，管径根据流量选择
    pipe_definitions = [
        # 主管（环状）
        ('P1', 'Pump', 'J1', 0.3, 100.0, 1.0, '泵站->主管1'),
        ('P2', 'J1', 'J2', 0.25, 150.0, 0.5, '主管环路1'),
        ('P3', 'J2', 'J3', 0.25, 150.0, 0.5, '主管环路2'),
        ('P4', 'J3', 'J1', 0.2, 180.0, 0.5, '主管环路3'),

        # 支管（到各灌溉分区）
        ('P5', 'J1', 'Z1', 0.15, 200.0, 1.5, '蔬菜区1支管'),
        ('P6', 'J1', 'Z2', 0.15, 250.0, 1.5, '蔬菜区2支管'),
        ('P7', 'J2', 'Z3', 0.12, 180.0, 1.5, '果树区1支管'),
        ('P8', 'J2', 'Z4', 0.12, 200.0, 1.5, '果树区2支管'),
        ('P9', 'J3', 'Z5', 0.1, 150.0, 1.5, '大田区1支管'),
        ('P10', 'J3', 'Z6', 0.1, 180.0, 1.5, '大田区2支管'),
    ]

    print("【管道信息】")
    for pid, from_node, to_node, D, L, K, desc in pipe_definitions:
        pipe = create_pressure_pipe(pid, D, L, material='pvc', K_minor=K)
        topology.add_pipe(pipe, from_node, to_node)
        print(f"   {pid}: {from_node}->{to_node}, D={int(D*1000)}mm, L={L}m ({desc})")

    print(f"  管道数量: {len(pipe_definitions)}")
    print(f"  管材: PVC管（低摩阻）")
    print()

    # 环路分析
    loops = topology.find_loops()
    print(f"【拓扑分析】")
    print(f"  检测到环路数量: {len(loops)}")
    print()

    return topology


def analyze_irrigation_scenarios(topology):
    """
    分析不同灌溉工况

    工况1：全部灌溉（灌溉高峰期）
    工况2：仅蔬菜和果树（春夏季）
    工况3：仅大田（秋季）

    Analyze different irrigation scenarios
    """

    print("="*80)
    print("不同灌溉工况分析")
    print("Different Irrigation Scenarios Analysis")
    print("="*80)
    print()

    # 基准需水量
    base_demands = {
        'Z1': 0.08, 'Z2': 0.07,  # 蔬菜
        'Z3': 0.05, 'Z4': 0.045, # 果树
        'Z5': 0.03, 'Z6': 0.025  # 大田
    }

    scenarios = {
        '全部灌溉': {
            'zones': ['Z1', 'Z2', 'Z3', 'Z4', 'Z5', 'Z6'],
            'factor': 1.0,
            'description': '灌溉高峰期，所有作物同时灌溉'
        },
        '蔬菜果树': {
            'zones': ['Z1', 'Z2', 'Z3', 'Z4'],
            'factor': 1.0,
            'description': '春夏季，蔬菜和果树需水旺盛'
        },
        '大田灌溉': {
            'zones': ['Z5', 'Z6'],
            'factor': 1.0,
            'description': '秋季，大田作物灌溉'
        }
    }

    results = {}

    for scenario_name, params in scenarios.items():
        print(f"【{scenario_name}】{params['description']}")

        # 重置所有分区需求
        for zid in ['Z1', 'Z2', 'Z3', 'Z4', 'Z5', 'Z6']:
            topology.nodes[zid].demand = 0.0

        # 设置该工况灌溉的分区
        total_demand = 0.0
        for zone_id in params['zones']:
            demand = base_demands[zone_id] * params['factor']
            topology.nodes[zone_id].demand = demand
            total_demand += demand

        print(f"  灌溉分区: {', '.join(params['zones'])}")
        print(f"  总需水量: {total_demand * 1000:.0f} L/s")

        # 求解
        solver = HardyCrossSolver(topology, max_iter=200, tol=1e-4, verbose=False)
        try:
            flows, heads = solver.solve()
            converged = True
            print(f"   求解收敛")

            # 分析各分区压力
            zone_pressures = {}
            for zone_id in params['zones']:
                node = topology.nodes[zone_id]
                head = heads[zone_id]
                pressure = head - node.elevation
                zone_pressures[zone_id] = pressure

            min_pressure = min(zone_pressures.values())
            max_pressure = max(zone_pressures.values())
            avg_pressure = np.mean(list(zone_pressures.values()))

            print(f"  压力范围: {min_pressure:.2f} ~ {max_pressure:.2f} m")
            print(f"  平均压力: {avg_pressure:.2f} m")

            # 验证压力要求
            # 喷灌要求：20-30m
            # 滴灌要求：10-15m
            # 这里假设喷灌要求
            min_required = 15.0  # m

            if min_pressure >= min_required:
                print(f"   满足压力要求 (>={min_required}m)")
            else:
                print(f"   最低压力不足 (需>={min_required}m)")
                print(f"    建议: 提高泵扬程或增设增压泵")

            # 计算供水流量
            supply_flow = abs(flows['P1']) * 1000  # L/s

            # 计算泵功率（简化）
            rho = 1000  # kg/m^3
            g = 9.81
            Q = abs(flows['P1'])  # m^3/s
            H = 30.0  # m，泵扬程
            eta = 0.70  # 灌溉泵效率约70%

            power_kw = (rho * g * Q * H / eta) / 1000

            print(f"  供水流量: {supply_flow:.0f} L/s")
            print(f"  泵功率: {power_kw:.1f} kW")

            # 日运行成本（假设灌溉8小时）
            daily_energy = power_kw * 8  # kWh/day
            daily_cost = daily_energy * 0.6  # 元/天（按0.6元/kWh农业电价）

            print(f"  日能耗: {daily_energy:.0f} kWh")
            print(f"  日运行成本: {daily_cost:.0f} 元")

            results[scenario_name] = {
                'converged': True,
                'zones': params['zones'],
                'heads': heads,
                'flows': flows,
                'zone_pressures': zone_pressures,
                'min_pressure': min_pressure,
                'avg_pressure': avg_pressure,
                'supply_flow': supply_flow,
                'power_kw': power_kw,
                'daily_energy': daily_energy,
                'daily_cost': daily_cost
            }

        except Exception as e:
            print(f"   求解失败: {str(e)[:50]}")
            results[scenario_name] = {'converged': False}

        print()

    return results


def irrigation_management_recommendations():
    """灌溉管理建议"""

    print("="*80)
    print("灌溉管理与节水建议")
    print("Irrigation Management and Water-Saving Recommendations")
    print("="*80)
    print()

    print("【1. 灌溉制度优化】")
    print("  - 根据作物生育期制定灌溉计划")
    print("  - 避免全部分区同时灌溉，降低峰值需求")
    print("  - 采用轮灌制度，提高水泵利用率")
    print("  - 夜间灌溉，降低蒸发损失")
    print()

    print("【2. 节水技术应用】")
    print("  - 蔬菜区：采用滴灌，节水30-50%")
    print("  - 果树区：采用微喷灌，节水20-30%")
    print("  - 大田区：采用喷灌，节水15-25%")
    print("  - 安装土壤湿度传感器，精准灌溉")
    print()

    print("【3. 系统维护管理】")
    print("  - 定期检查管道，及时维修漏损")
    print("  - 清洗过滤器，防止喷头堵塞")
    print("  - 冬季排空管道，防止冻裂")
    print("  - 记录用水量，优化灌溉参数")
    print()

    print("【4. 自动化控制】")
    print("  - 安装自动化灌溉控制系统")
    print("  - 根据气象数据自动调整灌溉")
    print("  - 手机APP远程监控和操作")
    print("  - 异常报警功能（漏水、堵塞）")
    print()

    print("【5. 经济效益分析】")
    print("  - 节水灌溉初期投资：约500-800元/亩")
    print("  - 年节水量：30-40%")
    print("  - 年节省成本：150-200元/亩")
    print("  - 投资回收期：3-4年")
    print("  - 增产效益：5-15%")
    print()


def plot_results(topology, results):
    """绘制分析结果"""

    fig, axes = plt.subplots(1, 2, figsize=(14, 6))
    fig.suptitle('农业灌溉系统分析结果', fontsize=16, fontweight='bold')

    # 提取数据
    scenarios = []
    supply_flows = []
    powers = []
    daily_costs = []

    for scenario, result in results.items():
        if result.get('converged'):
            scenarios.append(scenario)
            supply_flows.append(result['supply_flow'])
            powers.append(result['power_kw'])
            daily_costs.append(result['daily_cost'])

    # 子图1：供水流量和功率
    ax1 = axes[0]
    x_pos = np.arange(len(scenarios))
    width = 0.35

    ax1_flow = ax1
    bars1 = ax1_flow.bar(x_pos - width/2, supply_flows, width,
                          label='供水流量', color='#3498db', alpha=0.8)
    ax1_flow.set_ylabel('流量 (L/s)', fontsize=11, color='#3498db')
    ax1_flow.set_xlabel('工况', fontsize=11)
    ax1_flow.tick_params(axis='y', labelcolor='#3498db')

    ax1_power = ax1.twinx()
    bars2 = ax1_power.bar(x_pos + width/2, powers, width,
                           label='泵功率', color='#e74c3c', alpha=0.8)
    ax1_power.set_ylabel('功率 (kW)', fontsize=11, color='#e74c3c')
    ax1_power.tick_params(axis='y', labelcolor='#e74c3c')

    ax1.set_xticks(x_pos)
    ax1.set_xticklabels(scenarios)
    ax1.set_title('供水流量与泵功率', fontsize=12, fontweight='bold')
    ax1.grid(True, alpha=0.3, axis='y')

    # 子图2：日运行成本
    ax2 = axes[1]
    bars = ax2.bar(scenarios, daily_costs, color=['#27ae60', '#f39c12', '#9b59b6'], alpha=0.8)
    ax2.set_ylabel('日运行成本 (元)', fontsize=11)
    ax2.set_title('日运行成本对比', fontsize=12, fontweight='bold')
    ax2.grid(True, alpha=0.3, axis='y')

    for bar in bars:
        height = bar.get_height()
        ax2.text(bar.get_x() + bar.get_width()/2., height,
                f'{height:.0f}元',
                ha='center', va='bottom', fontsize=10)

    plt.tight_layout()

    # 保存图片
    output_path = 'examples/irrigation_system_results.png'
    plt.savefig(output_path, dpi=150, bbox_inches='tight')
    print(f" 结果图表已保存: {output_path}")


def main():
    """主函数"""

    print("\n")
    print("╔" + "="*78 + "╗")
    print("║" + " "*25 + "农业灌溉系统分析" + " "*25 + "║")
    print("║" + " "*20 + "Agricultural Irrigation System Analysis" + " "*20 + "║")
    print("╚" + "="*78 + "╝")
    print()

    # 1. 创建系统
    topology = create_irrigation_network()

    # 2. 分析灌溉工况
    results = analyze_irrigation_scenarios(topology)

    # 3. 灌溉管理建议
    irrigation_management_recommendations()

    # 4. 绘制结果
    plot_results(topology, results)

    print("="*80)
    print(" 案例分析完成！")
    print("="*80)


if __name__ == '__main__':
    main()
