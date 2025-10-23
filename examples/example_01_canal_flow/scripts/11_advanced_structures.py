"""
示例2：高级水工建筑物组合（重构版）

展示高级功能：
1. 多个闸门同时存在
2. 混合结构（闸门 + 堰 + 孔口）
3. 时变闸门开度
4. 优化的稳态求解

Author: Claude
Date: 2025-10-22
"""

import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

import numpy as np
import matplotlib.pyplot as plt
from solvers.single_canal_solver import SingleCanalSolver
from solvers.gate import SluiceGate, BroadCrestedWeir, Orifice


def run_advanced_structures_demo():
    """演示高级水工建筑物组合"""

    print("=" * 80)
    print("示例2：高级水工建筑物组合")
    print("=" * 80)
    print()

    # ==================== 系统配置 ====================
    canal_length = 10000.0
    canal_width = 10.0
    n_points = 301

    # 渠道参数
    bed_slope = 0.0005
    manning_n = 0.025

    print("系统配置:")
    print(f"  渠道总长度: {canal_length} m")
    print(f"  渠道宽度: {canal_width} m")
    print(f"  空间点数: {n_points}")
    print()

    # ==================== 场景1: 多个闸门 ====================
    print("=" * 80)
    print("场景1: 三个闸门串联")
    print("-" * 80)

    # 创建三个闸门
    gate1 = SluiceGate(position=2500.0, width=canal_width, opening=4.5, Cd=0.6)
    gate2 = SluiceGate(position=5000.0, width=canal_width, opening=4.0, Cd=0.6)
    gate3 = SluiceGate(position=7500.0, width=canal_width, opening=5.0, Cd=0.6)

    print(f"闸门1: {gate1}")
    print(f"闸门2: {gate2}")
    print(f"闸门3: {gate3}")
    print()

    solver1 = SingleCanalSolver(
        total_length=canal_length,
        structures=[gate1, gate2, gate3],
        nx_total=n_points,
        B=canal_width,
        S0=bed_slope,
        n=manning_n
    )

    Q_initial = 10.0
    solver1.reset_with_steady_state(Q_initial)

    # 稳态求解
    result1 = solver1.solve_steady_state(
        Q_target=Q_initial,
        max_iterations=5000,
        convergence_tol=0.001,
        check_interval=500,
        verbose=True
    )

    # 可视化
    profile1 = solver1.get_full_profile()
    x1 = profile1['x']
    Q1 = profile1['Q']

    fig1, ax1 = plt.subplots(figsize=(14, 6))
    ax1.plot(x1, Q1, 'b-', linewidth=2, label='Flow Rate')
    ax1.axhline(y=Q_initial, color='k', linestyle=':', alpha=0.5, label=f'Target: {Q_initial} m³/s')
    for i, gate in enumerate([gate1, gate2, gate3]):
        ax1.axvline(x=gate.position, color='r', linestyle='--', alpha=0.7,
                   label=f'Gate {i+1}' if i == 0 else '')
    ax1.set_xlabel('Distance (m)', fontsize=12)
    ax1.set_ylabel('Flow Rate (m³/s)', fontsize=12)
    ax1.set_title('场景1: 三个闸门串联 - 流量分布', fontsize=14, fontweight='bold')
    ax1.legend(fontsize=11)
    ax1.grid(True, alpha=0.3)

    os.makedirs('reports/figures', exist_ok=True)
    fig1.savefig('reports/figures/example_02_scenario1_multi_gates.png', dpi=150, bbox_inches='tight')
    plt.close(fig1)
    print(f"  ✓ 保存: reports/figures/example_02_scenario1_multi_gates.png")
    print()

    # ==================== 场景2: 混合结构 ====================
    print("=" * 80)
    print("场景2: 混合结构（闸门 + 堰 + 孔口）")
    print("-" * 80)

    # 创建混合结构
    gate_mixed = SluiceGate(position=2500.0, width=canal_width, opening=3.5, Cd=0.6)
    weir = BroadCrestedWeir(position=5000.0, width=canal_width, crest_height=0.5, Cd=0.848)
    orifice = Orifice(position=7500.0, width=4.0, height=2.0, bottom_elevation=0.2, Cd=0.61)

    print(f"闸门: {gate_mixed}")
    print(f"堰:   {weir}")
    print(f"孔口: {orifice}")
    print()

    solver2 = SingleCanalSolver(
        total_length=canal_length,
        structures=[gate_mixed, weir, orifice],
        nx_total=n_points,
        B=canal_width,
        S0=bed_slope,
        n=manning_n
    )

    solver2.reset_with_steady_state(Q_initial)

    result2 = solver2.solve_steady_state(
        Q_target=Q_initial,
        max_iterations=5000,
        convergence_tol=0.001,
        check_interval=500,
        verbose=True
    )

    # 可视化
    profile2 = solver2.get_full_profile()
    x2 = profile2['x']
    h2 = profile2['h']
    Q2 = profile2['Q']

    # 渠底高程
    z_bed2 = (canal_length - x2) * bed_slope
    z_surface2 = z_bed2 + h2

    fig2, (ax2a, ax2b) = plt.subplots(2, 1, figsize=(14, 10))

    # 水面纵剖面
    ax2a.fill_between(x2, z_bed2, z_surface2, color='cyan', alpha=0.5)
    ax2a.plot(x2, z_surface2, 'b-', linewidth=2.5, label='Water Surface')
    ax2a.plot(x2, z_bed2, 'k-', linewidth=2, label='Bed')
    ax2a.axvline(x=gate_mixed.position, color='r', linestyle='--', alpha=0.7, label='Gate')
    ax2a.axvline(x=weir.position, color='g', linestyle='--', alpha=0.7, label='Weir')
    ax2a.axvline(x=orifice.position, color='m', linestyle='--', alpha=0.7, label='Orifice')
    ax2a.set_xlabel('Distance (m)', fontsize=12)
    ax2a.set_ylabel('Elevation (m)', fontsize=12)
    ax2a.set_title('场景2: 混合结构 - 水面纵剖面', fontsize=14, fontweight='bold')
    ax2a.legend(fontsize=10)
    ax2a.grid(True, alpha=0.3)

    # 流量分布
    ax2b.plot(x2, Q2, 'g-', linewidth=2.5)
    ax2b.axhline(y=Q_initial, color='k', linestyle=':', alpha=0.5)
    ax2b.axvline(x=gate_mixed.position, color='r', linestyle='--', alpha=0.7)
    ax2b.axvline(x=weir.position, color='g', linestyle='--', alpha=0.7)
    ax2b.axvline(x=orifice.position, color='m', linestyle='--', alpha=0.7)
    ax2b.set_xlabel('Distance (m)', fontsize=12)
    ax2b.set_ylabel('Flow Rate (m³/s)', fontsize=12)
    ax2b.set_title('流量分布', fontsize=13, fontweight='bold')
    ax2b.grid(True, alpha=0.3)

    plt.tight_layout()
    fig2.savefig('reports/figures/example_02_scenario2_mixed_structures.png', dpi=150, bbox_inches='tight')
    plt.close(fig2)
    print(f"  ✓ 保存: reports/figures/example_02_scenario2_mixed_structures.png")
    print()

    # ==================== 场景3: 时变闸门开度 ====================
    print("=" * 80)
    print("场景3: 时变闸门开度")
    print("-" * 80)

    # 定义时变开度函数：从5m逐渐关闭到2m
    def time_varying_opening(t):
        """闸门开度随时间变化"""
        if t < 1000:
            return 5.0  # 初始完全开启
        elif t < 3000:
            # 线性关闭
            return 5.0 - (t - 1000) / 2000 * 3.0  # 从5m降到2m
        else:
            return 2.0  # 保持在2m

    gate_variable = SluiceGate(
        position=5000.0,
        width=canal_width,
        opening=time_varying_opening,  # 传入函数
        Cd=0.6
    )

    print(f"闸门: 位置={gate_variable.position}m, 开度=f(t) (时变)")
    print(f"  t<1000s:  开度=5.0m (完全开启)")
    print(f"  1000-3000s: 开度从5.0m线性降至2.0m")
    print(f"  t>3000s:  开度=2.0m (部分关闭)")
    print()

    solver3 = SingleCanalSolver(
        total_length=canal_length,
        structures=[gate_variable],
        nx_total=n_points,
        B=canal_width,
        S0=bed_slope,
        n=manning_n
    )

    # 初始稳态（完全开启）
    solver3.reset_with_steady_state(Q_initial)
    result3 = solver3.solve_steady_state(
        Q_target=Q_initial,
        max_iterations=2000,
        convergence_tol=0.01,
        check_interval=500,
        verbose=True
    )

    # 非恒定流模拟（闸门逐渐关闭）
    print("\n开始非恒定流模拟（闸门逐渐关闭）...")
    dt = 5.0
    total_time = 6000.0
    n_steps = int(total_time / dt)

    # 数据记录
    time_series = []
    gate_opening_series = []
    gate_flow_series = []
    inlet_flow_series = []
    outlet_flow_series = []

    for i in range(n_steps):
        solver3.step(dt, Q_upstream=Q_initial)

        # 记录数据
        t = solver3.current_time
        time_series.append(t)
        gate_opening_series.append(gate_variable.get_opening(t))
        gate_flows = solver3.get_gate_flows()
        gate_flow_series.append(gate_flows[0])

        profile = solver3.get_full_profile()
        inlet_flow_series.append(profile['Q'][10])
        outlet_flow_series.append(profile['Q'][-10])

        # 打印进度
        if i % 100 == 0:
            print(f"  t={t:.0f}s: 开度={gate_opening_series[-1]:.2f}m, "
                  f"Q_gate={gate_flow_series[-1]:.2f} m³/s")

    print(f"\n模拟完成！")
    print(f"  最终开度: {gate_opening_series[-1]:.2f} m")
    print(f"  最终闸门流量: {gate_flow_series[-1]:.2f} m³/s")
    print()

    # 可视化时间序列
    fig3, (ax3a, ax3b) = plt.subplots(2, 1, figsize=(14, 10))

    # 闸门开度
    ax3a.plot(time_series, gate_opening_series, 'r-', linewidth=2.5, label='Gate Opening')
    ax3a.set_xlabel('Time (s)', fontsize=12)
    ax3a.set_ylabel('Opening (m)', fontsize=12)
    ax3a.set_title('场景3: 时变闸门开度 - 开度随时间变化', fontsize=14, fontweight='bold')
    ax3a.legend(fontsize=11)
    ax3a.grid(True, alpha=0.3)

    # 流量响应
    ax3b.plot(time_series, inlet_flow_series, 'b-', linewidth=2, label='Inlet Flow')
    ax3b.plot(time_series, gate_flow_series, 'r-', linewidth=2.5, label='Gate Flow')
    ax3b.plot(time_series, outlet_flow_series, 'm-', linewidth=2, label='Outlet Flow')
    ax3b.axhline(y=Q_initial, color='k', linestyle=':', alpha=0.5, label=f'Target: {Q_initial} m³/s')
    ax3b.set_xlabel('Time (s)', fontsize=12)
    ax3b.set_ylabel('Flow Rate (m³/s)', fontsize=12)
    ax3b.set_title('流量响应', fontsize=13, fontweight='bold')
    ax3b.legend(fontsize=11)
    ax3b.grid(True, alpha=0.3)

    plt.tight_layout()
    fig3.savefig('reports/figures/example_02_scenario3_time_varying.png', dpi=150, bbox_inches='tight')
    plt.close(fig3)
    print(f"  ✓ 保存: reports/figures/example_02_scenario3_time_varying.png")

    # ==================== 总结 ====================
    print("\n" + "=" * 80)
    print("分析完成！")
    print("=" * 80)

    print(f"\n生成的文件:")
    print(f"  1. 场景1（三个闸门）: reports/figures/example_02_scenario1_multi_gates.png")
    print(f"  2. 场景2（混合结构）: reports/figures/example_02_scenario2_mixed_structures.png")
    print(f"  3. 场景3（时变开度）: reports/figures/example_02_scenario3_time_varying.png")

    print("\n关键结果:")
    print(f"  场景1 - 三闸门流量守恒误差: {result1['final_error']*100:.4f}%")
    print(f"  场景2 - 混合结构流量守恒误差: {result2['final_error']*100:.4f}%")
    print(f"  场景3 - 闸门关闭后流量减少: {Q_initial:.2f} → {gate_flow_series[-1]:.2f} m³/s")

    print("\n" + "=" * 80)


if __name__ == "__main__":
    run_advanced_structures_demo()
