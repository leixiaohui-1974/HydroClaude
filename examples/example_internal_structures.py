# -*- coding: utf-8 -*-
"""
内部水工建筑物使用示例

演示如何使用内部堰、闸门等建筑物：
1. 串联河段+宽顶堰
2. 串联河段+闸门（可调开度）
3. 串联河段+孔口
4. 多闸门串联系统
5. 堰闸组合控制

Stage 3 - Phase 3.3 示例

作者: HydroClaude Team
日期: 2025-10-29
"""

import numpy as np
import warnings
warnings.filterwarnings("ignore")
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from network import (
    RiverNetwork, Node, Reach,
    create_inflow_boundary, create_outflow_boundary,
    NetworkSolver, solve_network
)
from network.structures import InternalWeir, InternalGate, InternalOrifice
from physics.hydraulic_structures import BroadCrestedWeir, SluiceGate, Orifice
from solvers.godunov_fvm_solver import GodunvFVMSolver


def create_solver(length=500.0, width=15.0, h_init=2.0, Q_init=50.0, slope=0.001):
    """创建求解器"""
    n_cells = max(10, int(length / 50))
    solver = GodunvFVMSolver(
        width=width,
        length=length,
        n_cells=n_cells,
        manning_n=0.025,
        slope=slope
    )
    # 初始化边界条件避免NoneType错误
    solver.bc_left = {'type': 'Q', 'value': 0.0}
    solver.bc_right = {'type': 'h', 'value': 1.0}

    h = np.ones(n_cells) * h_init
    Q = np.ones(n_cells) * Q_init

    solver.h = h
    solver.Q = Q

    return solver


def example_1_weir_control():
    """
    示例1: 宽顶堰控制河道

    模拟一条河道，中间有宽顶堰，研究堰对水流的控制作用。
    """
    print("\n" + "=" * 80)
    print("示例1: 宽顶堰控制河道")
    print("=" * 80)

    # 创建网络
    network = RiverNetwork("堰控河道")

    # 添加节点
    n1 = create_inflow_boundary("上游入口", Q=50.0, elevation=110.0)
    n2 = Node("堰址", "junction", elevation=105.0)
    n3 = create_outflow_boundary("下游出口", h=2.0, elevation=100.0)

    network.add_node(n1)
    network.add_node(n2)
    network.add_node(n3)

    # 添加河段
    s1 = create_solver(length=1000.0, width=20.0, h_init=3.0, Q_init=50.0)
    s2 = create_solver(length=1000.0, width=20.0, h_init=2.5, Q_init=50.0)

    r1 = Reach("上游河段", "上游入口", "堰址", s1)
    r2 = Reach("下游河段", "堰址", "下游出口", s2)

    network.add_reach(r1)
    network.add_reach(r2)

    # 创建宽顶堰
    weir = BroadCrestedWeir(
        crest_elevation=105.0,  # 堰顶高程 (m)
        width=15.0,             # 堰宽 (m)
        discharge_coeff=1.7     # 流量系数
    )

    print("\n堰参数:")
    print(f"  堰顶高程: {weir.z_crest:.1f} m")
    print(f"  堰宽: {weir.B:.1f} m")
    print(f"  流量系数: {weir.C:.2f}")

    # 创建内部堰
    internal_weir = InternalWeir(weir, r1, r2, n2)

    # 添加到网络
    network.add_internal_structure("堰址", internal_weir)

    print(f"\n网络结构:")
    print(f"  节点数: {len(network.nodes)}")
    print(f"  河段数: {len(network.reaches)}")
    print(f"  内部建筑物: 1个宽顶堰")

    # 创建求解器
    print("\n创建网络求解器...")
    solver = NetworkSolver(network, solve_method='sequential')

    # 运行模拟
    print("\n运行模拟...")
    results = solver.run(
        t_end = 30.0,  # 30分钟
        dt=10.0,
        output_interval=300.0,
        verbose=True
    )

    # 检查堰流量
    print("\n堰流量统计:")
    Q_weir = internal_weir.Q_current
    print(f"  最终流量: {Q_weir:.2f} m^3/s")
    print(f"  上游水位: {internal_weir.h_upstream:.3f} m")
    print(f"  下游水位: {internal_weir.h_downstream:.3f} m")
    print(f"  堰顶水头: {internal_weir.h_upstream - weir.z_crest:.3f} m")

    # 流态
    regime = internal_weir.get_flow_regime()
    print(f"  流态: {regime}")

    return network, solver


def example_2_gate_regulation():
    """
    示例2: 闸门调节流量

    模拟闸门开度调节对流量的影响。
    """
    print("\n" + "=" * 80)
    print("示例2: 闸门调节流量")
    print("=" * 80)

    # 创建网络
    network = RiverNetwork("闸控渠道")

    # 节点
    n1 = create_inflow_boundary("进水口", Q=40.0, elevation=110.0)
    n2 = Node("闸门", "junction", elevation=105.0)
    n3 = create_outflow_boundary("出水口", h=2.0, elevation=100.0)

    network.add_node(n1)
    network.add_node(n2)
    network.add_node(n3)

    # 河段
    s1 = create_solver(length=800.0, width=12.0, h_init=3.0, Q_init=40.0)
    s2 = create_solver(length=800.0, width=12.0, h_init=2.5, Q_init=40.0)

    r1 = Reach("进水渠", "进水口", "闸门", s1)
    r2 = Reach("出水渠", "闸门", "出水口", s2)

    network.add_reach(r1)
    network.add_reach(r2)

    # 创建平板闸门
    gate = SluiceGate(
        sill_elevation=105.0,     # 闸底高程 (m)
        width=10.0,               # 闸门宽度 (m)
        opening=0.5,              # 初始开度 (m)
        contraction_coeff=0.6     # 收缩系数
    )

    print("\n闸门参数:")
    print(f"  闸底高程: {gate.z_sill:.1f} m")
    print(f"  闸门宽度: {gate.B:.1f} m")
    print(f"  收缩系数: {gate.C_d:.2f}")

    # 创建内部闸门
    internal_gate = InternalGate(gate, r1, r2, n2)
    network.add_internal_structure("闸门", internal_gate)

    # 测试不同开度
    print("\n闸门开度调节测试:")
    print(f"{'开度 (m)':>10} {'流量 (m^3/s)':>15} {'流态':>12}")
    print("-" * 40)

    for opening in [0.3, 0.5, 0.8, 1.2]:
        internal_gate.set_opening(opening)
        Q = internal_gate.solve()
        regime = internal_gate.get_flow_regime()
        print(f"{opening:>10.1f} {Q:>15.2f} {regime:>12}")

    # 运行模拟（开度=0.8m）
    internal_gate.set_opening(0.8)

    print(f"\n运行模拟（开度={internal_gate.get_opening():.1f}m）...")
    solver = NetworkSolver(network)

    results = solver.run(t_end = 30.0, dt=10.0, verbose=False)

    print(f"\n模拟完成:")
    print(f"  总步数: {results['n_steps']}")
    print(f"  最终流量: {internal_gate.Q_current:.2f} m^3/s")
    print(f"  质量误差: {results['mass_error_history'][-1]:.4f}%")

    return network, solver


def example_3_orifice_culvert():
    """
    示例3: 孔口/涵洞

    模拟涵洞过流。
    """
    print("\n" + "=" * 80)
    print("示例3: 涵洞过流")
    print("=" * 80)

    # 创建网络
    network = RiverNetwork("涵洞系统")

    # 节点
    n1 = create_inflow_boundary("上游", Q=20.0, elevation=110.0)
    n2 = Node("涵洞", "junction", elevation=105.0)
    n3 = create_outflow_boundary("下游", h=2.0, elevation=100.0)

    network.add_node(n1)
    network.add_node(n2)
    network.add_node(n3)

    # 河段
    s1 = create_solver(length=500.0, width=10.0, h_init=2.5, Q_init=20.0)
    s2 = create_solver(length=500.0, width=10.0, h_init=2.0, Q_init=20.0)

    r1 = Reach("进口段", "上游", "涵洞", s1)
    r2 = Reach("出口段", "涵洞", "下游", s2)

    network.add_reach(r1)
    network.add_reach(r2)

    # 创建圆形孔口（涵洞）
    orifice = Orifice(
        center_elevation=106.0,  # 孔口中心高程 (m)
        diameter=2.0,            # 直径 (m)
        discharge_coeff=0.62     # 流量系数
    )

    print("\n涵洞参数:")
    print(f"  孔口中心高程: {orifice.z_center:.1f} m")
    print(f"  直径: {orifice.D:.1f} m")
    print(f"  过流面积: {orifice.A:.3f} m^2")
    print(f"  流量系数: {orifice.C_d:.2f}")

    # 创建内部孔口
    internal_orifice = InternalOrifice(orifice, r1, r2, n2)
    network.add_internal_structure("涵洞", internal_orifice)

    # 运行模拟
    print("\n运行模拟...")
    solver = NetworkSolver(network)

    results = solver.run(t_end = 30.0, dt=5.0, verbose=False)

    print(f"\n涵洞流量:")
    print(f"  过流流量: {internal_orifice.Q_current:.2f} m^3/s")
    print(f"  上游水位: {internal_orifice.h_upstream:.3f} m")
    print(f"  下游水位: {internal_orifice.h_downstream:.3f} m")
    print(f"  水头差: {internal_orifice.delta_h:.3f} m")

    return network, solver


def example_4_series_gates():
    """
    示例4: 多闸门串联系统

    模拟3个闸门串联控制的灌溉渠道。
    """
    print("\n" + "=" * 80)
    print("示例4: 多闸门串联系统")
    print("=" * 80)

    # 创建网络
    network = RiverNetwork("串联闸门灌溉渠道")

    # 节点（4个）
    node_ids = ["总进水口", "闸门1", "闸门2", "闸门3", "末端"]
    elevations = [120.0, 115.0, 110.0, 105.0, 100.0]

    for i, (node_id, elev) in enumerate(zip(node_ids, elevations)):
        if i == 0:
            node = create_inflow_boundary(node_id, Q=60.0, elevation=elev)
        elif i == len(node_ids) - 1:
            node = create_outflow_boundary(node_id, h=2.0, elevation=elev)
        else:
            node = Node(node_id, "junction", elevation=elev)
        network.add_node(node)

    # 河段（4段）
    reach_configs = [
        ("渠段1", "总进水口", "闸门1", 800.0, 15.0, 60.0),
        ("渠段2", "闸门1", "闸门2", 800.0, 15.0, 60.0),
        ("渠段3", "闸门2", "闸门3", 800.0, 15.0, 60.0),
        ("渠段4", "闸门3", "末端", 800.0, 15.0, 60.0),
    ]

    reaches = []
    for reach_id, up, down, length, width, Q_init in reach_configs:
        solver = create_solver(length=length, width=width,
                              h_init=2.5, Q_init=Q_init)
        reach = Reach(reach_id, up, down, solver)
        network.add_reach(reach)
        reaches.append(reach)

    print(f"\n网络结构:")
    print(f"  节点数: {len(network.nodes)}")
    print(f"  河段数: {len(network.reaches)}")
    print(f"  闸门数: 3")

    # 添加3个闸门，开度不同
    gate_openings = [0.8, 1.0, 1.2]  # 逐渐增大开度

    for i, opening in enumerate(gate_openings):
        gate_id = f"闸门{i+1}"
        gate_elev = elevations[i+1]

        gate = SluiceGate(
            sill_elevation=gate_elev,
            width=12.0,
            opening=opening
        )

        internal_gate = InternalGate(gate, reaches[i], reaches[i+1],
                                     network.nodes[gate_id])
        network.add_internal_structure(gate_id, internal_gate)

        print(f"  {gate_id}: 开度={opening:.1f}m, 高程={gate_elev:.1f}m")

    # 运行模拟
    print("\n运行模拟...")
    solver = NetworkSolver(network, solve_method='sequential')

    results = solver.run(
        t_end = 30.0,  # 30分钟
        dt=10.0,
        output_interval=600.0,
        verbose=True
    )

    # 分析各闸门流量
    print("\n各闸门流量:")
    print(f"{'闸门':>8} {'开度 (m)':>12} {'流量 (m^3/s)':>15}")
    print("-" * 38)

    for i in range(3):
        gate_id = f"闸门{i+1}"
        gate_struct = network.nodes[gate_id].internal_structure
        Q = gate_struct.Q_current
        opening = gate_struct.get_opening()
        print(f"{gate_id:>8} {opening:>12.1f} {Q:>15.2f}")

    # 质量守恒
    Q_in, Q_out, error = network.check_global_mass_balance()
    print(f"\n全局质量守恒:")
    print(f"  总入流: {Q_in:.2f} m^3/s")
    print(f"  总出流: {Q_out:.2f} m^3/s")
    print(f"  误差: {error:.4f}%")

    return network, solver


def example_5_weir_gate_combination():
    """
    示例5: 堰闸组合控制

    上游用堰控制，下游用闸门调节。
    """
    print("\n" + "=" * 80)
    print("示例5: 堰闸组合控制系统")
    print("=" * 80)

    # 创建网络
    network = RiverNetwork("堰闸组合系统")

    # 节点
    nodes = [
        ("入口", "boundary", 120.0),
        ("堰", "junction", 110.0),
        ("中间池", "junction", 105.0),
        ("闸", "junction", 100.0),
        ("出口", "boundary", 95.0),
    ]

    for i, (node_id, node_type, elev) in enumerate(nodes):
        if node_type == "boundary":
            if i == 0:
                node = create_inflow_boundary(node_id, Q=50.0, elevation=elev)
            else:
                node = create_outflow_boundary(node_id, h=2.0, elevation=elev)
        else:
            node = Node(node_id, node_type, elevation=elev)
        network.add_node(node)

    # 河段
    reach_data = [
        ("进水段", "入口", "堰", 600.0),
        ("调节池", "堰", "中间池", 400.0),
        ("渠道段", "中间池", "闸", 600.0),
        ("出水段", "闸", "出口", 400.0),
    ]

    reaches = []
    for reach_id, up, down, length in reach_data:
        solver = create_solver(length=length, width=15.0,
                              h_init=2.5, Q_init=50.0)
        reach = Reach(reach_id, up, down, solver)
        network.add_reach(reach)
        reaches.append(reach)

    # 添加堰
    weir = BroadCrestedWeir(crest_elevation=110.0, width=12.0)
    internal_weir = InternalWeir(weir, reaches[0], reaches[1],
                                network.nodes["堰"])
    network.add_internal_structure("堰", internal_weir)

    # 添加闸门
    gate = SluiceGate(sill_elevation=100.0, width=10.0, opening=1.0)
    internal_gate = InternalGate(gate, reaches[2], reaches[3],
                                network.nodes["闸"])
    network.add_internal_structure("闸", internal_gate)

    print("\n系统配置:")
    print("  上游: 宽顶堰控制")
    print("  下游: 闸门调节")

    # 运行模拟
    print("\n运行模拟...")
    solver = NetworkSolver(network)

    results = solver.run(t_end = 30.0, dt=10.0, verbose=False)

    # 对比堰和闸门流量
    print("\n建筑物流量:")
    print(f"  堰流量: {internal_weir.Q_current:.2f} m^3/s")
    print(f"  闸流量: {internal_gate.Q_current:.2f} m^3/s")
    print(f"  差异: {abs(internal_weir.Q_current - internal_gate.Q_current):.4f} m^3/s")

    # 质量守恒
    max_error = max(results['mass_error_history'])
    print(f"\n质量守恒: {max_error:.4f}%")

    return network, solver


if __name__ == "__main__":
    """运行所有示例"""
    print("=" * 80)
    print("内部水工建筑物使用示例集")
    print("Stage 3 - Phase 3.3 Examples")
    print("=" * 80)

    # 示例1: 宽顶堰
    net1, solver1 = example_1_weir_control()

    # 示例2: 闸门调节
    net2, solver2 = example_2_gate_regulation()

    # 示例3: 涵洞
    net3, solver3 = example_3_orifice_culvert()

    # 示例4: 串联闸门
    net4, solver4 = example_4_series_gates()

    # 示例5: 堰闸组合
    net5, solver5 = example_5_weir_gate_combination()

    print("\n" + "=" * 80)
    print(" 所有内部建筑物示例运行完成！")
    print("=" * 80)

    print("\n总结:")
    print("  Stage 3 - Phase 3.3 内部水工建筑物功能:")
    print("  1.  InternalWeir - 宽顶堰/薄壁堰")
    print("     - 自动计算过堰流量")
    print("     - 自由/淹没流态判断")
    print("  2.  InternalGate - 平板闸门")
    print("     - 可调节开度")
    print("     - 自由/淹没出流")
    print("  3.  InternalOrifice - 孔口/涵洞")
    print("     - 孔流公式")
    print("     - 水头差驱动")
    print("  4.  StructureCoupler - 自动耦合")
    print("     - 自动边界条件传递")
    print("     - 质量守恒保证")
    print("  5.  Network集成")
    print("     - add_internal_structure()")
    print("     - 自动构建耦合器")
    print("     - 无缝集成NetworkSolver")
    print("\n  应用场景:")
    print("  - 堰控河道")
    print("  - 闸控灌溉渠道")
    print("  - 涵洞/箱涵")
    print("  - 串联闸门系统")
    print("  - 梯级水库")
