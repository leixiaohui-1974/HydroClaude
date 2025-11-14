# -*- coding: utf-8 -*-
"""
泵站提水灌溉示例

演示泵站在河网系统中的应用：
1. 提水灌溉系统
2. 泵站控制策略
3. 能耗计算

拓扑结构:
[水源] -> [进水渠] -> [泵站] -> [出水渠] -> [高位池]

Stage 3 - Task 3.3.3 Example

作者: HydroClaude Team
日期: 2025-10-29
"""

import numpy as np
import sys
import os

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from network.topology import (
    Node,
    RiverNetwork, 
    Reach
)
from solvers.godunov_fvm_solver import GodunvFVMSolver
from network.pump_station import create_pump_station

# 创建缺失的边界函数
def create_inflow_boundary(name, Q, elevation):
    """创建入流边界节点"""
    node = Node(node_id=name, node_type='boundary', elevation=elevation)
    node.boundary_Q = Q  # 固定流量
    return node

def create_outflow_boundary(name, h, elevation):
    """创建出流边界节点"""
    node = Node(node_id=name, node_type='boundary', elevation=elevation)
    node.boundary_h = h  # 固定水深
    return node


def create_solver(length, width, Q_init, slope=0.001):
    """创建渠道求解器"""
    n_cells = max(10, int(length / 50))

    solver = GodunvFVMSolver(
        width=width,
        length=length,
        n_cells=n_cells,
        manning_n=0.020,
        slope=slope
    )

    h_init = 2.0
    h = np.ones(n_cells) * h_init
    Q = np.ones(n_cells) * Q_init

    solver.set_initial_conditions(
        h, Q,
        {'type': 'Q', 'value': Q_init},
        {'type': 'h', 'value': h_init}
    )

    return solver


def build_pumping_system():
    """
    构建提水灌溉系统

    Returns:
        (network, pump_station): 网络和泵站节点
    """
    print("=" * 80)
    print("提水灌溉系统构建")
    print("=" * 80)

    network = RiverNetwork("提水灌溉系统")

    # ========== 节点 ==========
    print("\n[1] 添加节点...")

    # 水源（低位）
    water_source = create_inflow_boundary(
        "水源",
        Q=80.0,  # 80 m^3/s
        elevation=50.0
    )
    network.add_node(water_source)

    # 泵站（提升水位）
    pump_station = create_pump_station(
        "提水泵站",
        elevation=50.0,  # 与水源同高程
        n_pumps=3,  # 3台泵
        pump_rated_flow=30.0,  # 单泵30 m^3/s
        pump_rated_head=80.0,  # 单泵扬程80m
        control_mode='constant_flow',
        target_flow=70.0,  # 目标70 m^3/s
        x=1000.0
    )
    network.add_node(pump_station)

    # 高位池（终点）
    high_reservoir = create_outflow_boundary(
        "高位池",
        h=3.0,
        elevation=120.0  # 高程120m，比水源高70m
    )
    network.add_node(high_reservoir)

    print(f"  节点数: {len(network.nodes)}")
    print(f"  水源高程: {water_source.elevation:.1f} m")
    print(f"  泵站高程: {pump_station.elevation:.1f} m")
    print(f"  高位池高程: {high_reservoir.elevation:.1f} m")
    print(f"  提升高度: {high_reservoir.elevation - water_source.elevation:.1f} m")

    # ========== 河段 ==========
    print("\n[2] 添加河段...")

    # 进水渠: 水源 -> 泵站
    inlet_reach = Reach(
        "进水渠",
        "水源",
        "提水泵站",
        create_solver(length=500.0, width=8.0, Q_init=80.0, slope=0.001)
    )
    network.add_reach(inlet_reach)

    # 出水渠: 泵站 -> 高位池
    outlet_reach = Reach(
        "出水渠",
        "提水泵站",
        "高位池",
        create_solver(length=1000.0, width=6.0, Q_init=70.0, slope=0.001)
    )
    network.add_reach(outlet_reach)

    print(f"  河段数: {len(network.reaches)}")

    # ========== 泵站信息 ==========
    print("\n[3] 泵站配置:")
    print(f"  泵数量: {len(pump_station.pumps)}")
    print(f"  控制模式: {pump_station.control_mode}")
    print(f"  目标流量: {pump_station.target_flow:.1f} m^3/s")

    for i, pump in enumerate(pump_station.pumps):
        print(f"    泵{i+1}: 额定流量={pump.rated_flow:.1f} m^3/s, "
              f"额定扬程={pump.rated_head:.1f} m, "
              f"最大效率={pump.eta_max*100:.1f}%")

    # 拓扑
    print("\n[4] 构建拓扑...")
    network.build_topology()
    print(f"  拓扑顺序: {network.topological_order}")

    return network, pump_station


def scenario_1_normal_pumping(network, pump_station):
    """场景1: 正常提水运行"""
    print("\n" + "=" * 80)
    print("场景1: 正常提水运行")
    print("=" * 80)

    print(f"目标流量: {pump_station.target_flow:.1f} m^3/s")

    # 创建求解器
    solver = NetworkSolver(network, solve_method='sequential')

    # 运行模拟
    print("\n运行模拟 (30分钟)...")
    results = solver.run(
        t_end = 30.0,
        dt=10.0,
        output_interval=600.0,
        verbose=True
    )

    return results


def analyze_pumping_results(network, pump_station, results):
    """分析提水结果"""
    print("\n" + "=" * 80)
    print("结果分析")
    print("=" * 80)

    # 1. 泵站运行状态
    print("\n[1] 泵站运行状态")
    pump_station.print_status()

    # 2. 流量平衡
    Q_in, Q_out, mass_error = network.check_global_mass_balance()

    print(f"\n[2] 流量平衡")
    print(f"  进水流量: {Q_in:.2f} m^3/s")
    print(f"  出水流量: {Q_out:.2f} m^3/s")
    print(f"  误差: {mass_error:.4f}%")

    if mass_error < 5.0:
        print(f"   良好")
    else:
        print(f"    需改进")

    # 3. 能耗统计
    print(f"\n[3] 能耗统计")
    print(f"  运行时间: {pump_station.operating_hours:.2f} h")
    print(f"  总功率: {pump_station.total_power:.2f} kW")
    print(f"  累计能耗: {pump_station.total_energy:.2f} kWh")
    print(f"  平均效率: {pump_station.total_efficiency*100:.1f}%")

    # 估算成本（假设电价0.5元/kWh）
    cost = pump_station.total_energy * 0.5
    print(f"  估算电费: {cost:.2f} 元")

    # 单位水量能耗
    total_water = Q_out * pump_station.operating_hours * 3600  # m^3
    if total_water > 0:
        energy_per_m3 = pump_station.total_energy / (total_water / 1000)  # kWh/千m^3
        print(f"  单位水量能耗: {energy_per_m3:.4f} kWh/千m^3")

    # 4. 计算性能
    print(f"\n[4] 计算性能")
    print(f"  总步数: {results['n_steps']}")
    print(f"  计算时间: {results['total_time']:.2f} s")


def scenario_2_reduced_demand(network, pump_station):
    """场景2: 减少用水需求"""
    print("\n" + "=" * 80)
    print("场景2: 减少用水需求（目标流量50 m^3/s）")
    print("=" * 80)

    # 调整目标流量
    pump_station.target_flow = 50.0
    print(f"调整目标流量: 70 m^3/s -> 50 m^3/s")

    # 重置能耗统计
    pump_station.total_energy = 0.0
    pump_station.operating_hours = 0.0

    # 运行模拟
    solver = NetworkSolver(network, solve_method='sequential')

    results = solver.run(
        t_end = 30.0,
        dt=10.0,
        verbose=False
    )

    return results


def main():
    """主函数"""
    print("=" * 80)
    print("泵站提水灌溉示例")
    print("Stage 3 - Task 3.3.3 Example")
    print("=" * 80)

    # 1. 构建系统
    network, pump_station = build_pumping_system()

    # 2. 场景1: 正常运行
    results1 = scenario_1_normal_pumping(network, pump_station)
    analyze_pumping_results(network, pump_station, results1)

    # 3. 场景2: 减少需求
    results2 = scenario_2_reduced_demand(network, pump_station)
    analyze_pumping_results(network, pump_station, results2)

    # 4. 对比分析
    print("\n" + "=" * 80)
    print("场景对比")
    print("=" * 80)

    # 重新获取场景1数据（需要重新运行）
    pump_station.target_flow = 70.0
    pump_station.total_energy = 0.0
    pump_station.operating_hours = 0.0

    solver1 = NetworkSolver(network)
    results1_new = solver1.run(t_end = 30.0, dt=10.0, verbose=False)
    energy1 = pump_station.total_energy

    pump_station.target_flow = 50.0
    pump_station.total_energy = 0.0
    pump_station.operating_hours = 0.0

    solver2 = NetworkSolver(network)
    results2_new = solver2.run(t_end = 30.0, dt=10.0, verbose=False)
    energy2 = pump_station.total_energy

    print(f"\n  场景1 (70 m^3/s): 能耗 {energy1:.2f} kWh")
    print(f"  场景2 (50 m^3/s): 能耗 {energy2:.2f} kWh")
    print(f"  节能比例: {(energy1-energy2)/energy1*100:.1f}%")

    # 5. 总结
    print("\n" + "=" * 80)
    print("示例完成")
    print("=" * 80)
    print("\n主要功能演示:")
    print("   泵站节点 (PumpStationNode)")
    print("   多泵并联运行")
    print("   定流量控制策略")
    print("   提升水位（50m -> 120m）")
    print("   功率和效率计算")
    print("   能耗统计")

    print("\n应用价值:")
    print("  - 提水灌溉系统设计")
    print("  - 泵站运行优化")
    print("  - 能耗分析和节能")
    print("  - 泵站调度策略")


if __name__ == "__main__":
    main()
