#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
示例16：堰类组件在灌区引水渠系统中的应用

演示场景：
一条干渠需要完成以下功能：
1. 进水口：闸门控制进水量
2. 中段：侧堰分水到支渠
3. 末端：薄壁堰测量流量
4. 溢洪道：超标准流量时安全溢流

系统组成：
- 干渠总长 2000m
- 进水闸 @ 0m
- 侧堰分水 @ 800m（分水到1号支渠）
- 安全溢流堰 @ 1200m
- 薄壁量水堰 @ 1800m

功能演示：
- 稳态流量分配计算
- 非恒定流仿真（上游流量变化）
- 各堰流量时程曲线
- 水面线可视化

作者: Claude
日期: 2025-10-22
"""

import sys
import os
import numpy as np
import matplotlib.pyplot as plt

# 添加项目根目录到路径
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from physics.weirs import BroadCrestedWeir, SharpCrestedWeir, SideWeir
from physics.spillway import Spillway
from solvers.gate import SluiceGate
from solvers.single_canal_solver import SingleCanalSolver


def run_irrigation_system_simulation():
    """运行灌区引水渠系统仿真"""

    print("=" * 80)
    print("示例16：堰类组件在灌区引水渠系统中的应用")
    print("=" * 80)
    print()

    # ==================== 系统配置 ====================
    canal_length = 2000.0    # 干渠总长 (m)
    canal_width = 8.0        # 干渠宽度 (m)
    bed_slope = 0.0003       # 底坡
    manning_n = 0.025        # 曼宁糙率
    nx_total = 201           # 空间节点数

    # 渠底高程（简化为水平，实际可根据底坡计算）
    bed_elevation = 0.0

    print("系统配置:")
    print(f"  干渠总长: {canal_length} m")
    print(f"  渠道宽度: {canal_width} m")
    print(f"  底坡: {bed_slope*1000:.2f}‰")
    print(f"  曼宁糙率: {manning_n}")
    print()

    # ==================== 创建水工建筑物 ====================
    # 1. 进水闸 @ 0m
    inlet_gate = SluiceGate(
        position=100.0,
        width=canal_width,
        opening=3.0,   # 闸门开度 3m
        Cd=0.6
    )

    # 2. 侧堰分水 @ 800m（分水到支渠）
    side_weir_1 = SideWeir(
        position=800.0,
        length=30.0,          # 侧堰长度 30m
        crest_elevation=2.5,  # 侧堰堰顶高程 2.5m
        channel_width=canal_width,
        discharge_coefficient=0.4
    )

    # 3. 安全溢流堰 @ 1200m（防洪）
    safety_spillway = Spillway(
        position=1200.0,
        length=canal_width,
        crest_elevation=3.5,  # 溢流堰堰顶 3.5m（高于正常水位）
        gate_height=None,     # 自由溢流
        spillway_coefficient=2.0
    )

    # 4. 薄壁量水堰 @ 1800m（测量末端流量）
    measurement_weir = SharpCrestedWeir(
        position=1800.0,
        width=canal_width,
        crest_elevation=1.0,  # 量水堰堰顶较低
        weir_type='rectangular',
        discharge_coefficient=0.62
    )

    structures = [inlet_gate, side_weir_1, safety_spillway, measurement_weir]

    print("水工建筑物配置:")
    for i, structure in enumerate(structures, 1):
        print(f"  {i}. {structure}")
    print()

    # ==================== 创建求解器 ====================
    solver = SingleCanalSolver(
        total_length=canal_length,
        structures=structures,
        nx_total=nx_total,
        B=canal_width,
        S0=bed_slope,
        n=manning_n,
        method='preissmann'
    )

    print(f"求解器: {solver}")
    print()

    # ==================== 步骤1: 稳态流量分配 ====================
    print("=" * 80)
    print("步骤1: 稳态流量分配计算")
    print("-" * 80)

    Q_inlet = 15.0  # 进水流量 15 m³/s
    h_uniform = solver.reset_with_steady_state(Q_inlet)

    print(f"  进水流量: {Q_inlet} m³/s")
    print(f"  初始水深: {h_uniform:.4f} m")
    print()

    # 求解稳态
    print("  求解稳态...")
    result = solver.solve_steady_state(
        Q_target=Q_inlet,
        max_iterations=3000,
        convergence_tol=0.01,
        check_interval=500,
        verbose=True
    )

    # 获取稳态剖面
    profile_steady = solver.get_full_profile()
    x_full = profile_steady['x']
    h_steady = profile_steady['h']
    Q_steady = profile_steady['Q']

    # 获取各堰流量
    gate_flows_steady = solver.get_gate_flows()

    print()
    print("稳态结果:")
    print(f"  进水闸流量: {gate_flows_steady[0]:.3f} m³/s")
    print(f"  侧堰分水量: 计算中... (需要额外计算)")
    print(f"  溢流堰流量: {gate_flows_steady[2]:.3f} m³/s")
    print(f"  量水堰流量: {gate_flows_steady[3]:.3f} m³/s")
    print(f"  流量守恒误差: {result['final_error']*100:.4f}%")
    print()

    # 计算侧堰流量（需要获取侧堰位置的水位和主渠道流量）
    # 找到侧堰位置的索引
    side_weir_idx = np.argmin(np.abs(x_full - side_weir_1.position))
    h_side_weir = h_steady[side_weir_idx]
    Q_main_at_side_weir = Q_steady[side_weir_idx]

    Q_side_weir, _ = side_weir_1.calculate_discharge(
        h_upstream=h_side_weir,
        h_downstream=0.0,  # 支渠水位（简化）
        Q_channel=Q_main_at_side_weir
    )

    print(f"  【补充】侧堰实际分水量: {Q_side_weir:.3f} m³/s")
    print(f"  【补充】末端到达流量: {Q_inlet - Q_side_weir:.3f} m³/s (理论)")
    print()

    # ==================== 可视化稳态剖面 ====================
    print("生成稳态剖面图...")

    fig_steady = plt.figure(figsize=(16, 10))

    # 子图1: 水深剖面
    ax1 = plt.subplot(3, 1, 1)
    ax1.plot(x_full, h_steady, 'b-', linewidth=2, label='Water Depth')
    ax1.axhline(y=h_uniform, color='k', linestyle=':', alpha=0.5, label=f'Uniform Depth ({h_uniform:.3f}m)')

    # 标注各个建筑物
    for structure in structures:
        ax1.axvline(x=structure.position, color='r', linestyle='--', linewidth=1.5, alpha=0.6)
        ax1.text(structure.position, h_steady.max() * 1.05, structure.__class__.__name__,
                rotation=90, verticalalignment='bottom', fontsize=9)

    ax1.set_xlabel('Distance (m)', fontsize=12)
    ax1.set_ylabel('Water Depth (m)', fontsize=12)
    ax1.set_title('Steady State - Water Depth Profile', fontsize=14, fontweight='bold')
    ax1.grid(True, alpha=0.3)
    ax1.legend(fontsize=10)
    ax1.set_xlim([0, canal_length])

    # 子图2: 流量剖面
    ax2 = plt.subplot(3, 1, 2)
    ax2.plot(x_full, Q_steady, 'g-', linewidth=2, label='Flow Rate')
    ax2.axhline(y=Q_inlet, color='k', linestyle=':', alpha=0.5, label=f'Inlet Flow ({Q_inlet} m³/s)')

    for structure in structures:
        ax2.axvline(x=structure.position, color='r', linestyle='--', linewidth=1.5, alpha=0.6)

    ax2.set_xlabel('Distance (m)', fontsize=12)
    ax2.set_ylabel('Flow Rate (m³/s)', fontsize=12)
    ax2.set_title('Steady State - Flow Rate Distribution', fontsize=14, fontweight='bold')
    ax2.grid(True, alpha=0.3)
    ax2.legend(fontsize=10)
    ax2.set_xlim([0, canal_length])

    # 子图3: 流速剖面
    ax3 = plt.subplot(3, 1, 3)
    V_steady = Q_steady / (canal_width * h_steady)
    ax3.plot(x_full, V_steady, 'm-', linewidth=2, label='Velocity')

    for structure in structures:
        ax3.axvline(x=structure.position, color='r', linestyle='--', linewidth=1.5, alpha=0.6)

    ax3.set_xlabel('Distance (m)', fontsize=12)
    ax3.set_ylabel('Velocity (m/s)', fontsize=12)
    ax3.set_title('Steady State - Velocity Profile', fontsize=14, fontweight='bold')
    ax3.grid(True, alpha=0.3)
    ax3.legend(fontsize=10)
    ax3.set_xlim([0, canal_length])

    plt.tight_layout()
    os.makedirs('reports/figures', exist_ok=True)
    steady_fig_path = 'reports/figures/example_16_weirs_steady_state.png'
    plt.savefig(steady_fig_path, dpi=150, bbox_inches='tight')
    plt.close(fig_steady)
    print(f"   稳态剖面图已保存: {steady_fig_path}")
    print()

    # ==================== 步骤2: 非恒定流仿真 ====================
    print("=" * 80)
    print("步骤2: 非恒定流仿真 - 上游流量阶跃")
    print("-" * 80)

    Q_before = Q_inlet
    Q_after = 20.0      # 阶跃到 20 m³/s (+33%)
    step_time = 1000.0  # 阶跃时刻

    print(f"  阶跃前流量: {Q_before} m³/s")
    print(f"  阶跃后流量: {Q_after} m³/s")
    print(f"  阶跃时刻: {step_time} s")
    print()

    # 重新初始化
    solver.reset_with_steady_state(Q_before)
    solver.solve_steady_state(Q_target=Q_before, max_iterations=2000, convergence_tol=0.01, verbose=False)
    solver.clear_history()

    # 仿真参数
    dt = 2.0
    total_time = 4000.0
    n_steps = int(total_time / dt)

    # 监测点
    monitor_positions = {
        'Inlet': 50.0,
        'SideWeir_Up': side_weir_1.position - 50.0,
        'SideWeir_Down': side_weir_1.position + 50.0,
        'Spillway': safety_spillway.position,
        'MeasWeir': measurement_weir.position,
        'Outlet': 1950.0,
    }

    # 数据存储
    time_series = []
    monitor_data = {name: {'h': [], 'Q': []} for name in monitor_positions}
    structure_flows = {i: [] for i in range(len(structures))}

    print("开始非恒定流仿真...")

    for i in range(n_steps):
        t = i * dt

        # 上游边界：流量阶跃
        Q_up_bc = Q_before if t < step_time else Q_after

        # 更新
        solver.step(dt, Q_up_bc, h_downstream=None)

        # 获取当前剖面
        profile = solver.get_full_profile()
        gate_flows = solver.get_gate_flows()

        # 记录数据
        time_series.append(t)

        for idx, flow in enumerate(gate_flows):
            structure_flows[idx].append(flow)

        # 监测点数据
        for name, pos in monitor_positions.items():
            idx = np.argmin(np.abs(profile['x'] - pos))
            monitor_data[name]['h'].append(profile['h'][idx])
            monitor_data[name]['Q'].append(profile['Q'][idx])

        # 打印进度
        if i % 200 == 0 or abs(t - step_time) < dt:
            marker = " <-- STEP" if abs(t - step_time) < dt else ""
            print(f"  t={t:7.0f}s: Q_inlet={monitor_data['Inlet']['Q'][-1]:5.2f}, "
                  f"Q_outlet={monitor_data['Outlet']['Q'][-1]:5.2f} m³/s{marker}")

    print()
    print(f"仿真完成！")
    print()

    # ==================== 可视化非恒定流结果 ====================
    print("生成非恒定流时程曲线图...")

    fig_unsteady = plt.figure(figsize=(16, 12))

    # 子图1: 各建筑物流量时程
    ax1 = plt.subplot(3, 2, 1)
    ax1.plot(time_series, structure_flows[0], label='Inlet Gate', linewidth=2)
    ax1.plot(time_series, structure_flows[2], label='Spillway', linewidth=2)
    ax1.plot(time_series, structure_flows[3], label='Measurement Weir', linewidth=2)
    ax1.axvline(x=step_time, color='k', linestyle='--', alpha=0.5)
    ax1.axhline(y=Q_before, color='gray', linestyle=':', alpha=0.5)
    ax1.axhline(y=Q_after, color='gray', linestyle=':', alpha=0.5)
    ax1.set_xlabel('Time (s)', fontsize=11)
    ax1.set_ylabel('Flow Rate (m³/s)', fontsize=11)
    ax1.set_title('Structure Flow Rates', fontsize=12, fontweight='bold')
    ax1.grid(True, alpha=0.3)
    ax1.legend(fontsize=9)

    # 子图2: 入口和出口流量对比
    ax2 = plt.subplot(3, 2, 2)
    ax2.plot(time_series, monitor_data['Inlet']['Q'], 'b-', label='Inlet', linewidth=2)
    ax2.plot(time_series, monitor_data['Outlet']['Q'], 'r-', label='Outlet', linewidth=2)
    ax2.axvline(x=step_time, color='k', linestyle='--', alpha=0.5)
    ax2.set_xlabel('Time (s)', fontsize=11)
    ax2.set_ylabel('Flow Rate (m³/s)', fontsize=11)
    ax2.set_title('Inlet vs Outlet Flow', fontsize=12, fontweight='bold')
    ax2.grid(True, alpha=0.3)
    ax2.legend(fontsize=9)

    # 子图3: 侧堰上下游流量
    ax3 = plt.subplot(3, 2, 3)
    ax3.plot(time_series, monitor_data['SideWeir_Up']['Q'], 'g-', label='Upstream of Side Weir', linewidth=2)
    ax3.plot(time_series, monitor_data['SideWeir_Down']['Q'], 'm-', label='Downstream of Side Weir', linewidth=2)
    ax3.axvline(x=step_time, color='k', linestyle='--', alpha=0.5)
    ax3.set_xlabel('Time (s)', fontsize=11)
    ax3.set_ylabel('Flow Rate (m³/s)', fontsize=11)
    ax3.set_title('Side Weir Diversion', fontsize=12, fontweight='bold')
    ax3.grid(True, alpha=0.3)
    ax3.legend(fontsize=9)

    # 子图4: 关键位置水深
    ax4 = plt.subplot(3, 2, 4)
    ax4.plot(time_series, monitor_data['Inlet']['h'], label='Inlet', linewidth=2)
    ax4.plot(time_series, monitor_data['SideWeir_Up']['h'], label='Side Weir', linewidth=2)
    ax4.plot(time_series, monitor_data['Spillway']['h'], label='Spillway', linewidth=2)
    ax4.axvline(x=step_time, color='k', linestyle='--', alpha=0.5)
    ax4.set_xlabel('Time (s)', fontsize=11)
    ax4.set_ylabel('Water Depth (m)', fontsize=11)
    ax4.set_title('Water Depth at Key Locations', fontsize=12, fontweight='bold')
    ax4.grid(True, alpha=0.3)
    ax4.legend(fontsize=9)

    # 子图5: 侧堰分水量估算（上下游流量差）
    ax5 = plt.subplot(3, 2, 5)
    side_weir_diversion = np.array(monitor_data['SideWeir_Up']['Q']) - np.array(monitor_data['SideWeir_Down']['Q'])
    ax5.plot(time_series, side_weir_diversion, 'c-', label='Side Weir Diversion', linewidth=2)
    ax5.axvline(x=step_time, color='k', linestyle='--', alpha=0.5)
    ax5.set_xlabel('Time (s)', fontsize=11)
    ax5.set_ylabel('Diverted Flow (m³/s)', fontsize=11)
    ax5.set_title('Side Weir Diversion Rate', fontsize=12, fontweight='bold')
    ax5.grid(True, alpha=0.3)
    ax5.legend(fontsize=9)

    # 子图6: 流量守恒检查（入口 vs 出口+分水）
    ax6 = plt.subplot(3, 2, 6)
    total_outflow = np.array(monitor_data['Outlet']['Q']) + side_weir_diversion
    inflow = np.array(monitor_data['Inlet']['Q'])
    balance_error = (inflow - total_outflow) / inflow * 100
    ax6.plot(time_series, balance_error, 'r-', linewidth=2)
    ax6.axvline(x=step_time, color='k', linestyle='--', alpha=0.5)
    ax6.axhline(y=0, color='k', linestyle=':', alpha=0.5)
    ax6.set_xlabel('Time (s)', fontsize=11)
    ax6.set_ylabel('Balance Error (%)', fontsize=11)
    ax6.set_title('Flow Balance Check', fontsize=12, fontweight='bold')
    ax6.grid(True, alpha=0.3)

    plt.tight_layout()
    unsteady_fig_path = 'reports/figures/example_16_weirs_unsteady_flow.png'
    plt.savefig(unsteady_fig_path, dpi=150, bbox_inches='tight')
    plt.close(fig_unsteady)
    print(f"   非恒定流时程曲线图已保存: {unsteady_fig_path}")
    print()

    # ==================== 总结 ====================
    print("=" * 80)
    print("仿真总结")
    print("=" * 80)
    print()
    print("本示例展示了堰类组件在灌区引水渠系统中的综合应用：")
    print()
    print("【已实现的功能】")
    print("  1.  进水闸门控制")
    print("  2.  侧堰分水（考虑主渠道流速影响）")
    print("  3.  安全溢流堰（防洪）")
    print("  4.  薄壁量水堰（流量测量）")
    print("  5.  稳态流量分配计算")
    print("  6.  非恒定流过渡过程仿真")
    print("  7.  多建筑物协同作用分析")
    print()
    print("【生成的文件】")
    print(f"  1. 稳态剖面图: {steady_fig_path}")
    print(f"  2. 非恒定流时程图: {unsteady_fig_path}")
    print()
    print("【应用场景】")
    print("  - 灌区引水渠设计与优化")
    print("  - 分水建筑物选型与配置")
    print("  - 流量测量与监测方案")
    print("  - 防洪安全校核")
    print("  - 调度运行方案制定")
    print()
    print("=" * 80)


if __name__ == "__main__":
    run_irrigation_system_simulation()
