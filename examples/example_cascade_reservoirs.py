"""
梯级水库完整示例

模拟梯级水库系统，包含：
- 3个串联水库
- 水库间连接河段
- 溢洪道（堰）
- 泄洪闸
- 联合调度

拓扑结构:
[上游来水] → [水库1+堰] → [河段1] → [水库2+闸] → [河段2] → [水库3+堰] → [下游]

Stage 3 - Task 3.4.2 示例2

作者: HydroClaude Team
日期: 2025-10-29
"""

import numpy as np
import sys
import os

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from network import (
    RiverNetwork, Node, Reach,
    ReservoirNode,
    create_inflow_boundary, create_outflow_boundary,
    NetworkSolver
)
from network.structures import InternalWeir, InternalGate
from physics.hydraulic_structures import BroadCrestedWeir, SluiceGate
from solvers.godunov_fvm_solver import GodunvFVMSolver


def create_solver(length, width, Q_init, slope=0.001):
    """创建河段求解器"""
    n_cells = max(10, int(length / 100))

    solver = GodunvFVMSolver(
        width=width,
        length=length,
        n_cells=n_cells,
        manning_n=0.030,  # 天然河道糙率
        slope=slope
    )

    h_init = 3.0
    h = np.ones(n_cells) * h_init
    Q = np.ones(n_cells) * Q_init

    solver.set_initial_conditions(
        h, Q,
        {'type': 'Q', 'value': Q_init},
        {'type': 'h', 'value': h_init}
    )

    return solver


def build_cascade_system():
    """
    构建梯级水库系统

    Returns:
        RiverNetwork实例
    """
    print("=" * 80)
    print("梯级水库系统构建")
    print("=" * 80)

    network = RiverNetwork("梯级水库")

    # ========== 节点 ==========
    print("\n[1] 添加节点...")

    # 上游来水（边界）
    inflow = create_inflow_boundary(
        "上游来水",
        Q=200.0,  # 200 m³/s
        elevation=500.0
    )
    network.add_node(inflow)

    # 水库1
    reservoir1 = ReservoirNode(
        "水库1",
        elevation=480.0,
        storage_curve_type='linear',
        surface_area=2e6,  # 200万 m²
        h_min=0.0,
        h_max=50.0,
        volume_init=5e7  # 初始库容 5000万 m³
    )
    network.add_node(reservoir1)

    # 溢洪道1（节点）
    spillway1 = Node("溢洪道1", "junction", elevation=475.0)
    network.add_node(spillway1)

    # 水库2
    reservoir2 = ReservoirNode(
        "水库2",
        elevation=450.0,
        storage_curve_type='linear',
        surface_area=1.5e6,  # 150万 m²
        h_min=0.0,
        h_max=40.0,
        volume_init=3e7  # 初始库容 3000万 m³
    )
    network.add_node(reservoir2)

    # 泄洪闸2（节点）
    gate2 = Node("泄洪闸2", "junction", elevation=445.0)
    network.add_node(gate2)

    # 水库3
    reservoir3 = ReservoirNode(
        "水库3",
        elevation=420.0,
        storage_curve_type='linear',
        surface_area=1e6,  # 100万 m²
        h_min=0.0,
        h_max=30.0,
        volume_init=2e7  # 初始库容 2000万 m³
    )
    network.add_node(reservoir3)

    # 溢洪道3（节点）
    spillway3 = Node("溢洪道3", "junction", elevation=415.0)
    network.add_node(spillway3)

    # 下游出口（边界）
    outflow = create_outflow_boundary(
        "下游出口",
        h=5.0,
        elevation=400.0
    )
    network.add_node(outflow)

    print(f"  节点总数: {len(network.nodes)}")
    print(f"    水库: 3")
    print(f"    溢洪道: 2")
    print(f"    泄洪闸: 1")

    # ========== 河段 ==========
    print("\n[2] 添加河段...")

    # 入库河段1
    reach_in1 = Reach(
        "入库河段1",
        "上游来水",
        "水库1",
        create_solver(length=2000.0, width=50.0, Q_init=200.0, slope=0.004)
    )
    network.add_reach(reach_in1)

    # 出库河段1: 水库1 → 溢洪道1
    reach_out1 = Reach(
        "出库河段1",
        "水库1",
        "溢洪道1",
        create_solver(length=500.0, width=40.0, Q_init=200.0, slope=0.010)
    )
    network.add_reach(reach_out1)

    # 连接河段1: 溢洪道1 → 水库2
    connect1 = Reach(
        "连接河段1",
        "溢洪道1",
        "水库2",
        create_solver(length=5000.0, width=40.0, Q_init=200.0, slope=0.005)
    )
    network.add_reach(connect1)

    # 出库河段2: 水库2 → 泄洪闸2
    reach_out2 = Reach(
        "出库河段2",
        "水库2",
        "泄洪闸2",
        create_solver(length=500.0, width=35.0, Q_init=200.0, slope=0.010)
    )
    network.add_reach(reach_out2)

    # 连接河段2: 泄洪闸2 → 水库3
    connect2 = Reach(
        "连接河段2",
        "泄洪闸2",
        "水库3",
        create_solver(length=4000.0, width=35.0, Q_init=200.0, slope=0.006)
    )
    network.add_reach(connect2)

    # 出库河段3: 水库3 → 溢洪道3
    reach_out3 = Reach(
        "出库河段3",
        "水库3",
        "溢洪道3",
        create_solver(length=500.0, width=30.0, Q_init=200.0, slope=0.010)
    )
    network.add_reach(reach_out3)

    # 下泄河段: 溢洪道3 → 下游出口
    reach_down = Reach(
        "下泄河段",
        "溢洪道3",
        "下游出口",
        create_solver(length=3000.0, width=30.0, Q_init=200.0, slope=0.005)
    )
    network.add_reach(reach_down)

    print(f"  河段总数: {len(network.reaches)}")

    # ========== 水工建筑物 ==========
    print("\n[3] 添加水工建筑物...")

    # 溢洪道1 - 宽顶堰
    weir1 = BroadCrestedWeir(
        crest_elevation=478.0,  # 堰顶高程
        width=30.0,
        discharge_coeff=1.7
    )
    internal_weir1 = InternalWeir(weir1, reach_out1, connect1, spillway1)
    network.add_internal_structure("溢洪道1", internal_weir1)
    print(f"  溢洪道1: 堰顶高程={weir1.z_crest:.1f}m, 宽度={weir1.B:.1f}m")

    # 泄洪闸2 - 平板闸门
    gate = SluiceGate(
        sill_elevation=445.0,
        width=25.0,
        opening=3.0,  # 开度3.0m
        contraction_coeff=0.6
    )
    internal_gate = InternalGate(gate, reach_out2, connect2, gate2)
    network.add_internal_structure("泄洪闸2", internal_gate)
    print(f"  泄洪闸2: 闸底高程={gate.z_sill:.1f}m, 开度={gate.opening:.1f}m")

    # 溢洪道3 - 宽顶堰
    weir3 = BroadCrestedWeir(
        crest_elevation=418.0,
        width=25.0,
        discharge_coeff=1.7
    )
    internal_weir3 = InternalWeir(weir3, reach_out3, reach_down, spillway3)
    network.add_internal_structure("溢洪道3", internal_weir3)
    print(f"  溢洪道3: 堰顶高程={weir3.z_crest:.1f}m, 宽度={weir3.B:.1f}m")

    # ========== 拓扑 ==========
    print("\n[4] 构建拓扑...")
    network.build_topology()
    print(f"  拓扑顺序: {network.topological_order}")

    return network


def simulate_cascade(network, scenario_name, t_end=7200.0):
    """
    运行梯级水库模拟

    Args:
        network: 网络实例
        scenario_name: 场景名称
        t_end: 模拟时间 (s)

    Returns:
        模拟结果
    """
    print("\n" + "=" * 80)
    print(f"场景: {scenario_name}")
    print("=" * 80)

    solver = NetworkSolver(network, solve_method='sequential')

    print(f"\n运行模拟 (t=0 → {t_end/3600:.1f}h)...")
    results = solver.run(
        t_end=t_end,
        dt=20.0,
        output_interval=1800.0,  # 每30分钟输出
        verbose=True
    )

    return results


def analyze_cascade_results(network, results):
    """
    分析梯级水库结果

    Args:
        network: 网络实例
        results: 模拟结果
    """
    print("\n" + "=" * 80)
    print("结果分析")
    print("=" * 80)

    # 1. 水库状态
    print("\n[1] 水库状态")
    print(f"  {'水库':<10} {'库容(万m³)':<15} {'水位(m)':<12} {'蓄水率(%)':<12}")
    print(f"  {'-'*52}")

    for res_id in ["水库1", "水库2", "水库3"]:
        reservoir = network.nodes[res_id]
        if isinstance(reservoir, ReservoirNode):
            volume_m3 = reservoir.volume
            volume_wan = volume_m3 / 1e4
            water_level = reservoir.h
            capacity_rate = (reservoir.h - reservoir.h_min) / (reservoir.h_max - reservoir.h_min) * 100

            print(f"  {res_id:<10} {volume_wan:<15.1f} {water_level:<12.2f} {capacity_rate:<12.1f}")

    # 2. 溢洪道/泄洪闸流量
    print("\n[2] 泄流建筑物")

    # 溢洪道1
    weir1 = network.nodes["溢洪道1"].internal_structure
    print(f"\n  溢洪道1:")
    print(f"    流量: {weir1.Q_current:.2f} m³/s")
    print(f"    上游水位: {weir1.h_upstream:.2f} m")
    print(f"    堰顶水头: {weir1.h_upstream - weir1.structure.z_crest:.2f} m")
    print(f"    流态: {weir1.get_flow_regime()}")

    # 泄洪闸2
    gate2 = network.nodes["泄洪闸2"].internal_structure
    print(f"\n  泄洪闸2:")
    print(f"    流量: {gate2.Q_current:.2f} m³/s")
    print(f"    开度: {gate2.get_opening():.2f} m")
    print(f"    上游水位: {gate2.h_upstream:.2f} m")
    print(f"    流态: {gate2.get_flow_regime()}")

    # 溢洪道3
    weir3 = network.nodes["溢洪道3"].internal_structure
    print(f"\n  溢洪道3:")
    print(f"    流量: {weir3.Q_current:.2f} m³/s")
    print(f"    上游水位: {weir3.h_upstream:.2f} m")
    print(f"    堰顶水头: {weir3.h_upstream - weir3.structure.z_crest:.2f} m")

    # 3. 水量平衡
    print(f"\n[3] 水量平衡")

    Q_in, Q_out, mass_error = network.check_global_mass_balance()
    print(f"  总入流: {Q_in:.2f} m³/s")
    print(f"  总出流: {Q_out:.2f} m³/s")
    print(f"  误差: {mass_error:.4f}%")

    if mass_error < 5.0:
        print(f"  ✅ 良好 (< 5%)")
    else:
        print(f"  ⚠️  需改进")

    # 4. 性能
    print(f"\n[4] 计算性能")
    print(f"  总步数: {results['n_steps']}")
    print(f"  计算时间: {results['total_time']:.2f} s")


def scenario_1_normal_operation(network):
    """场景1: 正常运行"""
    print("\n" + "=" * 80)
    print("场景1: 正常运行模式")
    print("=" * 80)
    print("泄洪闸2开度: 3.0m")

    results = simulate_cascade(network, "正常运行", t_end=7200.0)
    analyze_cascade_results(network, results)

    return results


def scenario_2_flood_discharge(network):
    """场景2: 加大泄洪"""
    print("\n" + "=" * 80)
    print("场景2: 加大泄洪模式")
    print("=" * 80)

    # 增大泄洪闸开度
    gate_node = network.nodes["泄洪闸2"]
    if hasattr(gate_node, 'internal_structure'):
        gate_node.internal_structure.set_opening(5.0)  # 3.0m → 5.0m
        print("调整泄洪闸2开度: 3.0m → 5.0m")

    results = simulate_cascade(network, "加大泄洪", t_end=7200.0)
    analyze_cascade_results(network, results)

    # 恢复开度
    gate_node.internal_structure.set_opening(3.0)

    return results


def main():
    """主函数"""
    print("=" * 80)
    print("梯级水库完整示例")
    print("Stage 3 - Task 3.4.2 示例2")
    print("=" * 80)

    # 1. 构建系统
    network = build_cascade_system()

    # 2. 场景1: 正常运行
    results1 = scenario_1_normal_operation(network)

    # 3. 场景2: 加大泄洪
    results2 = scenario_2_flood_discharge(network)

    # 4. 总结
    print("\n" + "=" * 80)
    print("示例完成")
    print("=" * 80)
    print("\n主要功能演示:")
    print("  ✅ 梯级水库系统构建")
    print("  ✅ 水库节点 (ReservoirNode)")
    print("  ✅ 溢洪道控制 (InternalWeir)")
    print("  ✅ 泄洪闸控制 (InternalGate)")
    print("  ✅ 水库库容计算")
    print("  ✅ 联合调度模拟")

    print("\n应用价值:")
    print("  - 梯级水库联合调度")
    print("  - 防洪调度优化")
    print("  - 水位控制策略")
    print("  - 泄洪方案设计")
    print("  - 水库群优化运行")


if __name__ == "__main__":
    main()
