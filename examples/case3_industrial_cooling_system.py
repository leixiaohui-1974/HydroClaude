#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
案例3：工业冷却水循环系统
Case 3: Industrial Cooling Water Circulation System

本案例展示工业冷却水系统的水力分析，包括：
1. 多台循环泵并联运行
2. 冷却塔供水分析
3. 多个用水点压力保证
4. 不同运行工况对比
5. 能耗分析与优化建议

This case demonstrates hydraulic analysis of industrial cooling water systems,
including:
1. Multiple circulation pumps in parallel
2. Cooling tower water supply analysis
3. Pressure guarantee at multiple water points
4. Comparison of different operating conditions
5. Energy consumption analysis and optimization recommendations

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
from network.network_node import Junction, Reservoir, Tank
from network.network_topology import NetworkTopology
from solvers.hardy_cross_solver import HardyCrossSolver

# 设置中文字体
rcParams['font.sans-serif'] = ['SimHei', 'DejaVu Sans']
rcParams['axes.unicode_minus'] = False


def create_industrial_cooling_network():
    """
    创建工业冷却水循环系统

    系统布局：
    - 1个冷却塔（相当于恒定水头水源）
    - 2台循环泵（并联，可单台或双台运行）
    - 6个用水点（不同车间的冷却设备）
    - 12根管道（环状+枝状混合）

    System layout:
    - 1 cooling tower (constant head source)
    - 2 circulation pumps (parallel, single or dual operation)
    - 6 water points (cooling equipment in different workshops)
    - 12 pipes (looped + branched hybrid)
    """

    print("="*80)
    print("创建工业冷却水循环系统")
    print("Creating Industrial Cooling Water Circulation System")
    print("="*80)
    print()

    # 节点定义
    # 冷却塔池（恒定水位）
    cooling_tower = Reservoir(
        node_id='CT1',
        elevation=0.0,      # 地面标高
        head=5.0            # 冷却塔水池水位 5m
    )

    # 泵房节点（2台泵并联）
    pump_station = Junction(
        node_id='PS1',
        elevation=0.0,
        demand=0.0          # 泵站无需水量
    )

    # 主管网节点
    j1 = Junction('J1', elevation=0.0, demand=0.0)   # 主管分支点
    j2 = Junction('J2', elevation=0.0, demand=0.0)   # 环网节点
    j3 = Junction('J3', elevation=0.0, demand=0.0)   # 环网节点

    # 用水点（6个车间）
    workshop1 = Junction('W1', elevation=0.0, demand=50.0/1000)   # 50 L/s = 0.050 m³/s
    workshop2 = Junction('W2', elevation=0.0, demand=60.0/1000)   # 60 L/s
    workshop3 = Junction('W3', elevation=0.0, demand=70.0/1000)   # 70 L/s
    workshop4 = Junction('W4', elevation=0.0, demand=55.0/1000)   # 55 L/s
    workshop5 = Junction('W5', elevation=0.0, demand=45.0/1000)   # 45 L/s
    workshop6 = Junction('W6', elevation=0.0, demand=80.0/1000)   # 80 L/s

    # 回水管汇集点
    return_point = Junction('RP1', elevation=0.0, demand=-360.0/1000)  # 总回水量（负需求）

    print("【节点信息】")
    print(f"  冷却塔池: 水位 {cooling_tower.head}m")
    print(f"  泵站节点: PS1")
    print(f"  用水点: W1-W6")
    print(f"  总用水量: {(50+60+70+55+45+80):.0f} L/s = {(50+60+70+55+45+80)/1000:.3f} m³/s")
    print(f"  回水点: RP1")
    print()

    # 创建拓扑（先创建空拓扑）
    topology = NetworkTopology("Industrial Cooling System")

    # 添加节点
    for node in [cooling_tower, pump_station, j1, j2, j3,
                 workshop1, workshop2, workshop3, workshop4, workshop5, workshop6,
                 return_point]:
        topology.add_node(node)

    # 管道定义（管道ID, 起点, 终点, 管径, 长度, 局部损失系数）
    pipe_definitions = [
        ('P1', 'CT1', 'PS1', 0.5, 10.0, 0.5, '吸水管'),
        ('P2', 'PS1', 'J1', 0.5, 50.0, 1.0, '泵后主管'),
        ('P3', 'J1', 'J2', 0.4, 100.0, 0.5, '主管环路1'),
        ('P4', 'J2', 'J3', 0.4, 100.0, 0.5, '主管环路2'),
        ('P5', 'J3', 'J1', 0.35, 120.0, 0.5, '主管环路3'),
        ('P6', 'J1', 'W1', 0.25, 80.0, 2.0, '车间1支管'),
        ('P7', 'J1', 'W2', 0.25, 90.0, 2.0, '车间2支管'),
        ('P8', 'J2', 'W3', 0.3, 70.0, 2.0, '车间3支管'),
        ('P9', 'J2', 'W4', 0.25, 85.0, 2.0, '车间4支管'),
        ('P10', 'J3', 'W5', 0.25, 75.0, 2.0, '车间5支管'),
        ('P11', 'J3', 'W6', 0.3, 95.0, 2.0, '车间6支管'),
        ('P12', 'RP1', 'CT1', 0.5, 200.0, 1.5, '回水总管'),
    ]

    print("【管道信息】")
    total_length = 0
    for pid, from_node, to_node, D, L, K, desc in pipe_definitions:
        # 创建管道（钢管，使用材料自动设置粗糙度）
        pipe = create_pressure_pipe(pid, D, L, material='steel', K_minor=K)

        # 添加到拓扑
        topology.add_pipe(pipe, from_node, to_node)

        total_length += L
        print(f"  ✓ {pid}: {from_node}→{to_node}, D={int(D*1000)}mm, L={L}m ({desc})")

    print(f"  管道数量: {len(pipe_definitions)}")
    print(f"  管径范围: 250-500mm")
    print(f"  总管长: {total_length:.0f}m")
    print()

    # 环路分析
    loops = topology.find_loops()
    print(f"【拓扑分析】")
    print(f"  检测到环路数量: {len(loops)}")
    for i, loop in enumerate(loops, 1):
        print(f"  环路{i}: {' -> '.join(loop[:4])}...")
    print()

    return topology


def simulate_pump_scenarios(topology):
    """
    模拟不同泵运行工况

    工况1：单台泵运行（节能模式）
    工况2：双台泵并联运行（满负荷模式）
    工况3：高峰用水（1.2倍需求）

    Simulate different pump operating scenarios:
    Scenario 1: Single pump operation (energy-saving mode)
    Scenario 2: Dual pumps parallel operation (full load mode)
    Scenario 3: Peak water usage (1.2x demand)
    """

    print("="*80)
    print("泵站运行工况模拟")
    print("Pump Station Operating Scenarios Simulation")
    print("="*80)
    print()

    # 泵的特性参数
    # 单台泵：设计流量 250 L/s, 设计扬程 35m
    single_pump_head = 35.0  # m
    dual_pump_head = 33.0    # m (并联时扬程略降低，流量增加)

    scenarios = {
        '单泵运行': {
            'pump_head': single_pump_head,
            'demand_factor': 0.85,  # 减少需求以适应单泵能力
            'description': '节能模式，适用于低负荷时段'
        },
        '双泵并联': {
            'pump_head': dual_pump_head,
            'demand_factor': 1.0,   # 正常需求
            'description': '正常运行模式'
        },
        '高峰工况': {
            'pump_head': dual_pump_head,
            'demand_factor': 1.2,   # 高峰需求
            'description': '满负荷运行，双泵全开'
        }
    }

    results = {}

    for scenario_name, params in scenarios.items():
        print(f"【{scenario_name}】{params['description']}")
        print(f"  泵扬程: {params['pump_head']:.1f}m")
        print(f"  需求系数: {params['demand_factor']:.2f}")

        # 调整需求
        demand_factor = params['demand_factor']
        base_demands = {
            'W1': 50.0/1000, 'W2': 60.0/1000, 'W3': 70.0/1000,
            'W4': 55.0/1000, 'W5': 45.0/1000, 'W6': 80.0/1000,
            'RP1': -360.0/1000
        }

        for nid, base_demand in base_demands.items():
            topology.nodes[nid].demand = base_demand * demand_factor

        # 调整泵站节点的"固定水头"来模拟泵的作用
        # 这是简化处理：实际应该用泵特性曲线
        # 这里假设泵站出口水头 = 冷却塔水位 + 泵扬程
        pump_head_total = 5.0 + params['pump_head']  # 冷却塔水位5m + 泵扬程

        # 将泵站节点临时转换为固定水头节点进行计算
        # 保存原始节点
        original_ps = topology.nodes['PS1']

        # 创建临时的"水库"节点代表泵后压力
        temp_reservoir = Reservoir('PS1', elevation=0.0, head=pump_head_total)
        topology.nodes['PS1'] = temp_reservoir

        # 求解
        solver = HardyCrossSolver(topology, max_iter=100, tol=1e-6, verbose=False)
        try:
            flows, heads = solver.solve()
            converged = True
            iterations = solver.iterations
        except:
            converged = False
            flows, heads = {}, {}
            iterations = 0

        # 恢复原始节点
        topology.nodes['PS1'] = original_ps

        if converged:
            print(f"  ✓ 求解收敛，迭代{iterations}次")

            # 计算各车间压力
            workshop_ids = ['W1', 'W2', 'W3', 'W4', 'W5', 'W6']
            pressures = {}

            for wid in workshop_ids:
                node = topology.nodes[wid]
                head = heads[wid]
                pressure = head - node.elevation
                pressures[wid] = pressure

            min_pressure = min(pressures.values())
            max_pressure = max(pressures.values())
            avg_pressure = np.mean(list(pressures.values()))

            print(f"  压力范围: {min_pressure:.1f} ~ {max_pressure:.1f} m")
            print(f"  平均压力: {avg_pressure:.1f} m")

            # 检查压力要求（工业冷却水一般要求>20m）
            min_required = 20.0
            if min_pressure < min_required:
                print(f"  ⚠️ 最低压力{min_pressure:.1f}m < 要求{min_required}m")
            else:
                print(f"  ✓ 最低压力满足要求 (>{min_required}m)")

            # 计算泵站出口流量（P2管道流量）
            pump_flow = abs(flows['P2']) * 1000  # 转换为L/s
            print(f"  泵站出口流量: {pump_flow:.1f} L/s")

            # 估算能耗（简化计算）
            # 功率 P = ρ * g * Q * H / η (W)
            # 假设泵效率 η = 0.75
            rho = 1000  # kg/m³
            g = 9.81    # m/s²
            Q = abs(flows['P2'])  # m³/s
            H = params['pump_head']  # m
            eta = 0.75

            power_kw = (rho * g * Q * H / eta) / 1000  # kW

            # 如果是双泵，功率分摊
            if '双泵' in scenario_name or '高峰' in scenario_name:
                power_per_pump = power_kw / 2
                print(f"  总功率: {power_kw:.1f} kW (单泵 {power_per_pump:.1f} kW × 2)")
            else:
                print(f"  运行功率: {power_kw:.1f} kW (单泵)")

            # 每日运行能耗（假设运行12小时）
            daily_energy = power_kw * 12  # kWh/day
            print(f"  日能耗(12h): {daily_energy:.0f} kWh")

            results[scenario_name] = {
                'converged': True,
                'iterations': iterations,
                'heads': heads,
                'flows': flows,
                'pressures': pressures,
                'min_pressure': min_pressure,
                'avg_pressure': avg_pressure,
                'pump_flow': pump_flow,
                'power_kw': power_kw,
                'daily_energy': daily_energy
            }
        else:
            print(f"  ✗ 求解未收敛")
            results[scenario_name] = {'converged': False}

        print()

    return results


def analyze_energy_optimization(results):
    """能耗分析与优化建议"""

    print("="*80)
    print("能耗分析与优化建议")
    print("Energy Consumption Analysis and Optimization")
    print("="*80)
    print()

    # 提取能耗数据
    scenarios = []
    powers = []
    energies = []

    for scenario, result in results.items():
        if result.get('converged', False):
            scenarios.append(scenario)
            powers.append(result['power_kw'])
            energies.append(result['daily_energy'])

    # 能耗对比
    print("【能耗对比】")
    for i, scenario in enumerate(scenarios):
        print(f"  {scenario}:")
        print(f"    运行功率: {powers[i]:.1f} kW")
        print(f"    日能耗:   {energies[i]:.0f} kWh")
        if i > 0:
            saving = ((energies[0] - energies[i]) / energies[0]) * 100
            if saving > 0:
                print(f"    相比单泵: 增加 {-saving:.1f}%")
            else:
                print(f"    相比单泵: 减少 {saving:.1f}%")
    print()

    # 优化建议
    print("【优化建议】")
    print()
    print("1. 运行策略优化")
    print("   - 低负荷时段（夜间、周末）：采用单泵运行")
    print("   - 正常生产时段：双泵并联运行")
    print("   - 短时高峰：启动备用泵")
    print("   - 预计节能潜力：15-20%")
    print()

    print("2. 变频调速改造")
    print("   - 为循环泵配置变频器")
    print("   - 根据实际需求调节转速")
    print("   - 流量减少10%时，功率降低约27%")
    print("   - 投资回收期：1-2年")
    print()

    print("3. 管网优化")
    print("   - 检查阀门开度，减少节流损失")
    print("   - 定期清洗管道，降低水头损失")
    print("   - 优化回水系统，避免憋压运行")
    print()

    print("4. 自动控制系统")
    print("   - 安装压力传感器，实时监测")
    print("   - PLC自动控制泵启停和转速")
    print("   - 根据压力反馈优化运行")
    print("   - 避免过度供压造成能源浪费")
    print()

    # 年度经济效益估算
    if len(energies) >= 2:
        # 假设：全年300天运行，每天12小时
        # 50%时间低负荷(单泵)，50%时间正常负荷(双泵)
        annual_energy_current = (energies[0] * 0.5 + energies[1] * 0.5) * 300

        # 优化后：通过变频调速，平均节能15%
        annual_energy_optimized = annual_energy_current * 0.85

        energy_saving = annual_energy_current - annual_energy_optimized

        # 电费按0.8元/kWh计算
        cost_saving = energy_saving * 0.8

        print("【年度经济效益估算】")
        print(f"  当前年能耗: {annual_energy_current:.0f} kWh/年")
        print(f"  优化后能耗: {annual_energy_optimized:.0f} kWh/年")
        print(f"  年节能量:   {energy_saving:.0f} kWh")
        print(f"  年节约电费: {cost_saving/10000:.1f} 万元 (按0.8元/kWh)")
        print()


def plot_results(topology, results):
    """绘制分析结果"""

    fig, axes = plt.subplots(2, 2, figsize=(14, 10))
    fig.suptitle('工业冷却水循环系统分析结果', fontsize=16, fontweight='bold')

    # 提取数据
    scenarios = []
    min_pressures = []
    avg_pressures = []
    pump_flows = []
    powers = []

    workshop_pressures = {wid: [] for wid in ['W1', 'W2', 'W3', 'W4', 'W5', 'W6']}

    for scenario, result in results.items():
        if result.get('converged', False):
            scenarios.append(scenario)
            min_pressures.append(result['min_pressure'])
            avg_pressures.append(result['avg_pressure'])
            pump_flows.append(result['pump_flow'])
            powers.append(result['power_kw'])

            for wid in workshop_pressures:
                workshop_pressures[wid].append(result['pressures'][wid])

    # 子图1：各车间压力分布
    ax1 = axes[0, 0]
    x_workshops = np.arange(len(workshop_pressures))
    width = 0.25

    for i, scenario in enumerate(scenarios):
        pressures = [workshop_pressures[wid][i] for wid in ['W1', 'W2', 'W3', 'W4', 'W5', 'W6']]
        ax1.bar(x_workshops + i*width, pressures, width, label=scenario, alpha=0.8)

    ax1.axhline(y=20, color='r', linestyle='--', linewidth=1.5, label='最低要求(20m)')
    ax1.set_xlabel('车间编号', fontsize=11)
    ax1.set_ylabel('压力 (m)', fontsize=11)
    ax1.set_title('各车间压力分布', fontsize=12, fontweight='bold')
    ax1.set_xticks(x_workshops + width)
    ax1.set_xticks([x + width for x in x_workshops])
    ax1.set_xticklabels(['W1', 'W2', 'W3', 'W4', 'W5', 'W6'])
    ax1.legend(fontsize=9)
    ax1.grid(True, alpha=0.3)

    # 子图2：泵站流量对比
    ax2 = axes[0, 1]
    bars = ax2.bar(scenarios, pump_flows, color=['#3498db', '#2ecc71', '#e74c3c'], alpha=0.8)
    ax2.set_ylabel('流量 (L/s)', fontsize=11)
    ax2.set_title('泵站出口流量对比', fontsize=12, fontweight='bold')
    ax2.grid(True, alpha=0.3, axis='y')

    # 在柱子上标注数值
    for bar in bars:
        height = bar.get_height()
        ax2.text(bar.get_x() + bar.get_width()/2., height,
                f'{height:.0f}',
                ha='center', va='bottom', fontsize=10)

    # 子图3：运行功率对比
    ax3 = axes[1, 0]
    bars = ax3.bar(scenarios, powers, color=['#9b59b6', '#f39c12', '#e67e22'], alpha=0.8)
    ax3.set_ylabel('功率 (kW)', fontsize=11)
    ax3.set_title('运行功率对比', fontsize=12, fontweight='bold')
    ax3.grid(True, alpha=0.3, axis='y')

    for bar in bars:
        height = bar.get_height()
        ax3.text(bar.get_x() + bar.get_width()/2., height,
                f'{height:.0f}',
                ha='center', va='bottom', fontsize=10)

    # 子图4：压力统计
    ax4 = axes[1, 1]
    x_pos = np.arange(len(scenarios))
    ax4.plot(x_pos, min_pressures, 'o-', label='最低压力', linewidth=2, markersize=8)
    ax4.plot(x_pos, avg_pressures, 's-', label='平均压力', linewidth=2, markersize=8)
    ax4.axhline(y=20, color='r', linestyle='--', linewidth=1.5, label='最低要求(20m)')
    ax4.set_xticks(x_pos)
    ax4.set_xticklabels(scenarios)
    ax4.set_ylabel('压力 (m)', fontsize=11)
    ax4.set_title('系统压力统计', fontsize=12, fontweight='bold')
    ax4.legend(fontsize=10)
    ax4.grid(True, alpha=0.3)

    plt.tight_layout()

    # 保存图片
    output_path = 'examples/industrial_cooling_results.png'
    plt.savefig(output_path, dpi=150, bbox_inches='tight')
    print(f"📊 结果图表已保存: {output_path}")

    # plt.show()


def main():
    """主函数"""

    print("\n")
    print("╔" + "="*78 + "╗")
    print("║" + " "*21 + "工业冷却水循环系统分析" + " "*21 + "║")
    print("║" + " "*12 + "Industrial Cooling Water Circulation System Analysis" + " "*12 + "║")
    print("╚" + "="*78 + "╝")
    print()

    # 1. 创建系统
    topology = create_industrial_cooling_network()

    # 2. 模拟不同泵运行工况
    results = simulate_pump_scenarios(topology)

    # 3. 能耗分析与优化建议
    analyze_energy_optimization(results)

    # 4. 绘制结果
    plot_results(topology, results)

    print("="*80)
    print("✅ 案例分析完成！")
    print("="*80)


if __name__ == '__main__':
    main()
