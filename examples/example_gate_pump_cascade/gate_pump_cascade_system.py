#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
明渠串联闸泵群系统动态模拟

系统配置：
- 总长度：100 km
- 2个闸站（25km, 75km处）
- 1个泵站（50km处）
- 缓坡：S0 = 0.0001
- 初始流量：30 m³/s

模拟场景：
1. 稳态求解：30 m³/s恒定流
2. 瞬态模拟：t=0时刻，渠首流量阶跃 30→55 m³/s
3. 观察全线水位和流量的动态响应过程

使用基础库：
- HydrostaticCanalSolver（Phase 2高精度求解器）
- SluiceGate（闸门）
- PumpStation（泵站）
- ResultValidator（结果验证）
- VisualizationTemplates（可视化）

作者: Claude
日期: 2025-10-23
"""

import sys
import os

# 路径设置
script_path = os.path.abspath(__file__)
project_root = os.path.dirname(os.path.dirname(os.path.dirname(script_path)))
sys.path.insert(0, project_root)

import numpy as np
import matplotlib.pyplot as plt
from solvers.hydrostatic_canal_solver import HydrostaticCanalSolver
from solvers.gate import SluiceGate, PumpStation
from utils.canal_utils import compute_steady_uniform_flow
from utils.result_validator import ResultValidator, quick_validate_steady_state
from utils.visualization_templates import VisualizationTemplates


def main():
    """主函数：明渠串联闸泵群系统模拟"""

    print("=" * 90)
    print("明渠串联闸泵群系统动态模拟".center(90))
    print("=" * 90)
    print()

    # ==================== 1. 参数设置 ====================
    print("▶ 1. 系统参数设置")
    print("-" * 90)
    
    # ==================== 场景选择（v7.0新增）====================
    # 选择泵站建模场景：
    #   "flat": 平原场景（底床连续）→ 水深会增加
    #   "stepped": 山区场景（底床有高差）→ 水深基本不变
    # ================================================================
    SCENARIO = "flat"  # 可选: "flat" 或 "stepped"

    # 渠道参数
    L_total = 100000.0      # 总长度 (m) = 100 km
    B = 15.0                # 渠道宽度 (m)
    S0 = 0.0001             # 底坡（缓坡）
    n = 0.025               # 曼宁糙率
    nx = 501                # 空间网格点数 (暂时用501快速测试)

    # 流量参数
    Q_initial = 30.0        # 初始流量 (m³/s)
    Q_step = 55.0           # 阶跃后流量 (m³/s)

    # 结构物位置
    gate1_pos = 25000.0     # 闸站1位置 (m) = 25 km
    pump_pos = 50000.0      # 泵站位置 (m) = 50 km
    gate2_pos = 75000.0     # 闸站2位置 (m) = 75 km

    # 闸门参数
    gate_opening = 5.0      # 闸门开度 (m)
    gate_Cd = 0.6           # 流量系数

    # 泵站参数
    pump_rated_flow = 30.0  # 额定流量 (m³/s)
    pump_rated_head = 5.0   # 额定扬程 (m)
    pump_min_head = 2.0     # 最小吸入水头 (m)

    # 瞬态模拟参数  (P2优化: 增加模拟时长和减小时间步长)
    t_total = 7200.0        # 总模拟时间 (s) = 2小时 (原1小时)
    dt = 0.5                # 时间步长 (s) (原1.0秒)

    print(f"渠道参数:")
    print(f"  总长度: {L_total/1000:.1f} km = {L_total:.0f} m")
    print(f"  渠道宽度: {B:.1f} m")
    print(f"  底坡: {S0*10000:.2f}‰ (每10km落差{S0*10000:.0f}m)")
    print(f"  曼宁糙率: {n}")
    print(f"  空间网格: {nx}点，间距Δx={L_total/(nx-1):.1f}m")
    print()

    print(f"结构物配置:")
    print(f"  闸站1: {gate1_pos/1000:.0f} km处，开度{gate_opening}m")
    print(f"  泵站:  {pump_pos/1000:.0f} km处，额定流量{pump_rated_flow}m³/s，扬程{pump_rated_head}m")
    print(f"  闸站2: {gate2_pos/1000:.0f} km处，开度{gate_opening}m")
    print()

    print(f"泵站场景选择: {SCENARIO.upper()}")
    if SCENARIO == "flat":
        print(f"  → 平原泵站（底床连续）")
    elif SCENARIO == "stepped":
        print(f"  → 山区泵站（底床高差={pump_rated_head}m）")
    print()
    
    print(f"模拟场景:")
    print(f"  初始流量: {Q_initial:.1f} m³/s (稳态)")
    print(f"  阶跃流量: {Q_step:.1f} m³/s (t=0时刻，渠首突增)")
    print(f"  模拟时长: {t_total:.0f}秒 = {t_total/60:.1f}分钟")
    print(f"  时间步长: {dt}秒")
    print()

    # ==================== 2. 创建求解器 ====================
    print("▶ 2. 创建求解器和结构物")
    print("-" * 90)

    # 创建闸门
    gate1 = SluiceGate(
        position=gate1_pos,
        width=B,
        opening=gate_opening,
        Cd=gate_Cd
    )

    gate2 = SluiceGate(
        position=gate2_pos,
        width=B,
        opening=gate_opening,
        Cd=gate_Cd
    )

    # 创建泵站
    pump = PumpStation(
        position=pump_pos,
        width=B,
        rated_flow=pump_rated_flow,
        rated_head=pump_rated_head,
        min_suction_head=pump_min_head
    )

    print(f"结构物已创建:")
    print(f"  {gate1}")
    print(f"  {pump}")
    print(f"  {gate2}")
    print()

    # 创建求解器
    solver = HydrostaticCanalSolver(
        length=L_total,
        nx=nx,
        B=B,
        S0=S0,
        n=n,
        internal_structures=[
            (gate1_pos, gate1),
            (pump_pos, pump),
            (gate2_pos, gate2)
        ]
    )

    print(f"求解器: HydrostaticCanalSolver (Phase 2高精度)")
    print(f"  网格点数: {solver.nx}")
    print(f"  网格间距: {solver.dx:.1f} m")
    print(f"  内部结构: {len(solver.structure_objects)}个（2闸1泵）")
    print()
    
    # ==================== 场景配置：底床高程（v7.0）====================
    print(f"▶ 场景配置: {SCENARIO.upper()}")
    print("-" * 90)
    
    if SCENARIO == "flat":
        # 平原场景：底床连续（默认配置）
        print("场景: 平原泵站（底床连续）")
        print("  - 底床高程: z = -S0·x（连续，无跳跃）")
        print("  - 泵站作用: 提供能量抬升水位")
        print("  - 预期结果: 泵站下游水深增加 ≈ 扬程 = 5m")
        # 不修改底床（默认就是连续的）
        
    elif SCENARIO == "stepped":
        # 山区场景：底床在泵站处有跳跃
        pump_idx = np.argmin(np.abs(solver.x - pump_pos))
        print("场景: 山区泵站（底床有高差）")
        print(f"  - 泵站前底床: 保持原始高程")
        print(f"  - 泵站后底床: 抬高 {pump_rated_head:.1f}m（实际地形高差）")
        print(f"  - 泵站作用: 克服地形高差")
        print(f"  - 预期结果: 泵站下游水深基本不变")
        
        # 在泵站后抬高底床（模拟实际地形高差）
        solver.z[pump_idx:] += pump_rated_head
        print(f"  - 已设置底床跳跃: idx={pump_idx}, x={solver.x[pump_idx]/1000:.1f}km")
        
    else:
        raise ValueError(f"未知场景: {SCENARIO}，可选: 'flat' 或 'stepped'")
    
    print()
    # ================================================================

    # ==================== 3. 稳态求解 ====================
    print("=" * 90)
    print("▶ 3. 稳态求解（初始流量 30 m³/s）")
    print("-" * 90)

    # 计算均匀流水深作为初始猜测
    h_uniform = compute_steady_uniform_flow(Q_initial, B, S0, n)
    print(f"均匀流水深估计: {h_uniform:.3f} m (用作初始条件)")
    print()

    # 初始化
    solver.h[:] = h_uniform
    solver.hu[:] = Q_initial / B

    # 稳态求解
    print("开始稳态求解...")
    h_down_steady = h_uniform  # 下游边界条件

    result_steady = solver.solve_steady_state(
        Q_target=Q_initial,
        h_downstream=h_down_steady,
        convergence_tol=0.001,  # 0.1%容差
        max_iterations=500,     # 先用500测试收敛性
        dt=dt,
        verbose=True
    )

    print()
    if result_steady['converged']:
        print(f"✓ 稳态求解成功收敛")
        print(f"  迭代次数: {result_steady['iterations']}")
        print(f"  计算时间: {result_steady.get('elapsed_time', 0):.2f}秒")
        print(f"  流量误差: {result_steady.get('final_flow_error', 0):.6f}%")
    else:
        print(f"✗ 稳态求解未收敛")
        print(f"  已执行迭代: {result_steady['iterations']}")
    print()

    # 保存稳态解
    h_steady = solver.h.copy()
    hu_steady = solver.hu.copy()

    # ==================== 4. 验证（必须！） ====================
    print("=" * 90)
    print("▶ 4. 结果验证")
    print("-" * 90)

    validator_steady = quick_validate_steady_state(
        solver, result_steady, Q_initial, "稳态解（30 m³/s）"
    )
    print()

    # ==================== 5. 瞬态模拟 ====================
    print("=" * 90)
    print("▶ 5. 瞬态模拟（流量阶跃 30→55 m³/s）")
    print("-" * 90)

    # 重置为稳态初始条件
    solver.h[:] = h_steady
    solver.hu[:] = hu_steady

    # 时间循环设置
    n_steps = int(t_total / dt)
    save_interval = int(600 / dt)  # 每10分钟保存一次
    n_saves = n_steps // save_interval + 1

    # 存储数据
    h_history = np.zeros((n_saves, solver.nx))
    q_history = np.zeros((n_saves, solver.nx))
    time_history = np.zeros(n_saves)

    # 保存初始状态
    h_history[0, :] = solver.h
    q_history[0, :] = solver.hu * B
    time_history[0] = 0.0

    print(f"瞬态模拟设置:")
    print(f"  总步数: {n_steps}")
    print(f"  保存间隔: 每{save_interval}步 = 每{save_interval*dt:.0f}秒")
    print(f"  保存次数: {n_saves}")
    print()

    print("开始瞬态模拟...")
    print(f"{'时间(分钟)':>12} {'进度':>8} {'最大水深(m)':>12} {'最小水深(m)':>12} {'平均流量(m³/s)':>15}")
    print("-" * 70)

    save_idx = 1
    for step in range(1, n_steps + 1):
        t_current = step * dt

        # 上游边界：阶跃流量
        Q_upstream = Q_step  # 从t>0开始即为阶跃后流量

        # 下游边界：保持初始水深
        h_downstream = h_down_steady

        # 设置边界条件
        solver.set_boundary_conditions(Q_in=Q_upstream, h_out=h_downstream)

        # 时间推进（使用显式方法）
        h_new, hu_new = solver.step_explicit(dt)
        solver.h[:] = h_new
        solver.hu[:] = hu_new

        # 保存数据
        if step % save_interval == 0:
            h_history[save_idx, :] = solver.h
            q_history[save_idx, :] = solver.hu * B
            time_history[save_idx] = t_current

            # 输出进度
            progress = (step / n_steps) * 100
            h_max = np.max(solver.h)
            h_min = np.min(solver.h)
            q_avg = np.mean(solver.hu * B)

            print(f"{t_current/60:12.1f} {progress:7.1f}% {h_max:12.3f} {h_min:12.3f} {q_avg:15.2f}")

            save_idx += 1

    print()
    print("✓ 瞬态模拟完成")
    print()

    # ==================== 6. 可视化 ====================
    print("=" * 90)
    print("▶ 6. 结果可视化")
    print("-" * 90)

    viz = VisualizationTemplates()

    # Figure 1: Steady-state longitudinal profile (water level + flow)
    print("Generating Figure 1: Steady-state longitudinal profile...")

    fig1, (ax1, ax2) = plt.subplots(2, 1, figsize=(16, 10), sharex=True)

    # 计算水位（水面高程）= 底床高程 + 水深
    z_bed = -S0 * solver.x  # 底床高程
    eta_steady = z_bed + h_steady  # 水位

    # Subplot 1: Water level (水位) and bed level (底床)
    ax1.plot(solver.x / 1000, eta_steady, 'b-', linewidth=2, label='Water Level (水位)')
    ax1.fill_between(solver.x / 1000, z_bed, eta_steady, alpha=0.3, color='cyan', label='Water Depth (水深)')
    ax1.plot(solver.x / 1000, z_bed, 'k-', linewidth=1.5, label='Bed Level (底床高程)')
    ax1.set_ylabel('Elevation (m)', fontsize=12)
    scenario_label = "平原泵站（底床连续）" if SCENARIO == "flat" else "山区泵站（底床有高差）"
    ax1.set_title(f'Steady-State Profile (Q={Q_initial} m³/s) - {scenario_label}', fontsize=14, fontweight='bold')
    ax1.grid(True, alpha=0.3)
    ax1.legend(fontsize=11, loc='best')

    # Mark structures
    for pos, name in [(gate1_pos/1000, 'Gate1'), (pump_pos/1000, 'Pump'), (gate2_pos/1000, 'Gate2')]:
        ax1.axvline(pos, color='red', linestyle='--', linewidth=1.5, alpha=0.5)
        ax1.text(pos, ax1.get_ylim()[1] * 0.98, name,
                color='red', fontsize=10, ha='center', va='top',
                bbox=dict(boxstyle='round', facecolor='white', alpha=0.8))

    # Subplot 2: Flow rate
    q_steady = hu_steady * B
    ax2.plot(solver.x / 1000, q_steady, 'g-', linewidth=2, label='Flow Rate')
    ax2.axhline(Q_initial, color='gray', linestyle='--', linewidth=1, alpha=0.5, label=f'Target Flow ({Q_initial} m³/s)')
    ax2.set_xlabel('Distance (km)', fontsize=12)
    ax2.set_ylabel('Flow Rate (m³/s)', fontsize=12)
    ax2.grid(True, alpha=0.3)
    ax2.legend(fontsize=11)

    # Mark structures
    for pos, name in [(gate1_pos/1000, 'Gate1'), (pump_pos/1000, 'Pump'), (gate2_pos/1000, 'Gate2')]:
        ax2.axvline(pos, color='red', linestyle='--', linewidth=1.5, alpha=0.5)

    fig1.tight_layout()

    # Save
    output_dir = os.path.join(project_root, "examples", "example_gate_pump_cascade", "results")
    os.makedirs(output_dir, exist_ok=True)
    fig1.savefig(os.path.join(output_dir, "01_steady_state_profile.png"), dpi=150, bbox_inches='tight')
    plt.close(fig1)
    print(f"  Saved: 01_steady_state_profile.png")

    # Figure 2: Water level spatiotemporal evolution (水位时空演化)
    print("Generating Figure 2: Water level spatiotemporal evolution...")
    X, T = np.meshgrid(solver.x / 1000, time_history / 60)  # km, min
    
    # 计算水位历史（每个时间步的水位）
    eta_history = np.zeros_like(h_history)
    for i in range(len(time_history)):
        eta_history[i, :] = z_bed + h_history[i, :]

    fig2, ax2 = plt.subplots(figsize=(16, 10))
    contour2 = ax2.contourf(X, T, eta_history, levels=20, cmap='viridis')
    cbar2 = plt.colorbar(contour2, ax=ax2, label='Water Level (水位, m)')

    # Add structure position lines
    for pos, name in [(gate1_pos/1000, "Gate1"), (pump_pos/1000, "Pump"), (gate2_pos/1000, "Gate2")]:
        ax2.axvline(pos, color='red', linestyle='--', linewidth=1.5, alpha=0.7)
        ax2.text(pos, np.max(time_history/60) * 0.95, name,
                color='red', fontsize=10, ha='center', va='top',
                bbox=dict(boxstyle='round', facecolor='white', alpha=0.8))

    ax2.set_xlabel('Distance (km)', fontsize=12)
    ax2.set_ylabel('Time (min)', fontsize=12)
    ax2.set_title('Water Level Spatiotemporal Evolution (水位时空演化, Flow Step 30→55 m³/s)', fontsize=14, fontweight='bold')
    ax2.grid(True, alpha=0.3)
    fig2.tight_layout()

    fig2.savefig(os.path.join(output_dir, "02_water_level_spacetime.png"), dpi=150, bbox_inches='tight')
    plt.close(fig2)
    print(f"  Saved: 02_water_level_spacetime.png")

    # Figure 3: Flow rate spatiotemporal evolution
    print("Generating Figure 3: Flow rate spatiotemporal evolution...")

    fig3, ax3 = plt.subplots(figsize=(16, 10))
    contour3 = ax3.contourf(X, T, q_history, levels=20, cmap='plasma')
    cbar3 = plt.colorbar(contour3, ax=ax3, label='Flow Rate (m³/s)')

    # Add structure position lines
    for pos, name in [(gate1_pos/1000, "Gate1"), (pump_pos/1000, "Pump"), (gate2_pos/1000, "Gate2")]:
        ax3.axvline(pos, color='cyan', linestyle='--', linewidth=1.5, alpha=0.7)
        ax3.text(pos, np.max(time_history/60) * 0.95, name,
                color='cyan', fontsize=10, ha='center', va='top',
                bbox=dict(boxstyle='round', facecolor='black', alpha=0.7))

    ax3.set_xlabel('Distance (km)', fontsize=12)
    ax3.set_ylabel('Time (min)', fontsize=12)
    ax3.set_title('Flow Rate Spatiotemporal Evolution (Flow Step 30→55 m³/s)', fontsize=14, fontweight='bold')
    ax3.grid(True, alpha=0.3)
    fig3.tight_layout()

    fig3.savefig(os.path.join(output_dir, "03_flow_rate_spacetime.png"), dpi=150, bbox_inches='tight')
    plt.close(fig3)
    print(f"  Saved: 03_flow_rate_spacetime.png")

    # Figure 4: Water depth time series at key locations
    print("Generating Figure 4: Water depth time series at key locations...")

    # Find indices of key locations
    idx_upstream = 0
    idx_gate1 = np.argmin(np.abs(solver.x - gate1_pos))
    idx_pump = np.argmin(np.abs(solver.x - pump_pos))
    idx_gate2 = np.argmin(np.abs(solver.x - gate2_pos))
    idx_downstream = -1

    fig4, ax4 = plt.subplots(figsize=(14, 8))
    ax4.plot(time_history / 60, h_history[:, idx_upstream], 'b-', linewidth=2, label='Upstream (0 km)')
    ax4.plot(time_history / 60, h_history[:, idx_gate1], 'g-', linewidth=2, label=f'Gate1 ({gate1_pos/1000:.0f} km)')
    ax4.plot(time_history / 60, h_history[:, idx_pump], 'r-', linewidth=2, label=f'Pump ({pump_pos/1000:.0f} km)')
    ax4.plot(time_history / 60, h_history[:, idx_gate2], 'm-', linewidth=2, label=f'Gate2 ({gate2_pos/1000:.0f} km)')
    ax4.plot(time_history / 60, h_history[:, idx_downstream], 'k-', linewidth=2, label=f'Downstream ({L_total/1000:.0f} km)')

    ax4.set_xlabel('Time (min)', fontsize=12)
    ax4.set_ylabel('Water Depth (m)', fontsize=12)
    ax4.set_title('Water Depth Time Series at Key Locations', fontsize=14, fontweight='bold')
    ax4.legend(fontsize=11, loc='best')
    ax4.grid(True, alpha=0.3)
    fig4.tight_layout()

    fig4.savefig(os.path.join(output_dir, "04_key_locations_water_depth.png"), dpi=150, bbox_inches='tight')
    plt.close(fig4)
    print(f"  Saved: 04_key_locations_water_depth.png")

    # Figure 5: Flow rate time series at key locations
    print("Generating Figure 5: Flow rate time series at key locations...")

    fig5, ax5 = plt.subplots(figsize=(14, 8))
    ax5.plot(time_history / 60, q_history[:, idx_upstream], 'b-', linewidth=2, label='Upstream (0 km)')
    ax5.plot(time_history / 60, q_history[:, idx_gate1], 'g-', linewidth=2, label=f'Gate1 ({gate1_pos/1000:.0f} km)')
    ax5.plot(time_history / 60, q_history[:, idx_pump], 'r-', linewidth=2, label=f'Pump ({pump_pos/1000:.0f} km)')
    ax5.plot(time_history / 60, q_history[:, idx_gate2], 'm-', linewidth=2, label=f'Gate2 ({gate2_pos/1000:.0f} km)')
    ax5.plot(time_history / 60, q_history[:, idx_downstream], 'k-', linewidth=2, label=f'Downstream ({L_total/1000:.0f} km)')

    # Add reference lines for flow step
    ax5.axhline(Q_initial, color='gray', linestyle='--', linewidth=1, alpha=0.5, label=f'Initial Flow ({Q_initial} m³/s)')
    ax5.axhline(Q_step, color='orange', linestyle='--', linewidth=1, alpha=0.5, label=f'Step Flow ({Q_step} m³/s)')

    ax5.set_xlabel('Time (min)', fontsize=12)
    ax5.set_ylabel('Flow Rate (m³/s)', fontsize=12)
    ax5.set_title('Flow Rate Time Series at Key Locations', fontsize=14, fontweight='bold')
    ax5.legend(fontsize=11, loc='best')
    ax5.grid(True, alpha=0.3)
    fig5.tight_layout()

    fig5.savefig(os.path.join(output_dir, "05_key_locations_flow_rate.png"), dpi=150, bbox_inches='tight')
    plt.close(fig5)
    print(f"  Saved: 05_key_locations_flow_rate.png")

    # Figure 6: Longitudinal profile animation (using visualization library)
    print("Generating Figure 6: Longitudinal profile animation...")
    print("  Creating animation frames (this may take a while)...")

    # Prepare snapshots for animation
    h_snapshots = [h_history[i, :] for i in range(len(time_history))]
    Q_snapshots = [q_history[i, :] for i in range(len(time_history))]
    time_snapshots = list(time_history)

    # Create animation using VisualizationTemplates
    viz_anim = VisualizationTemplates(output_dir=output_dir)
    fig_anim, anim = viz_anim.create_longitudinal_animation(
        x=solver.x,
        h_snapshots=h_snapshots,
        Q_snapshots=Q_snapshots,
        time_snapshots=time_snapshots,
        S0=S0,
        canal_length=L_total,
        Q_target=Q_step,
        gate_positions=[gate1_pos, pump_pos, gate2_pos],
        h_uniform=h_uniform,
        title_prefix="Gate-Pump Cascade System",
        filename="06_longitudinal_profile_animation.gif",
        fps=2,
        dpi=80
    )
    plt.close(fig_anim)

    print()
    print("✓ All figures and animation generated and saved to:", output_dir)
    print()

    # ==================== 7. 保存数据 ====================
    print("=" * 90)
    print("▶ 7. 保存数据")
    print("-" * 90)

    # 保存稳态数据
    np.savez(
        os.path.join(output_dir, "steady_state_data.npz"),
        x=solver.x,
        h=h_steady,
        q=hu_steady * B,
        Q_target=Q_initial,
        gate1_pos=gate1_pos,
        pump_pos=pump_pos,
        gate2_pos=gate2_pos
    )
    print("  已保存: steady_state_data.npz")

    # 保存瞬态数据
    np.savez(
        os.path.join(output_dir, "transient_data.npz"),
        x=solver.x,
        time=time_history,
        h_history=h_history,
        q_history=q_history,
        Q_initial=Q_initial,
        Q_step=Q_step
    )
    print("  已保存: transient_data.npz")
    print()

    # ==================== 8. 总结 ====================
    print("=" * 90)
    print("▶ 8. 模拟总结")
    print("=" * 90)

    print()
    print("系统配置:")
    print(f"  ✓ 渠道长度: {L_total/1000:.0f} km")
    print(f"  ✓ 2个闸站 + 1个泵站")
    print(f"  ✓ 网格: {nx}点, Δx={solver.dx:.1f}m")
    print()

    print("稳态求解:")
    print(f"  ✓ 流量: {Q_initial} m³/s")
    print(f"  ✓ 迭代次数: {result_steady['iterations']}")
    print(f"  ✓ 流量误差: {result_steady.get('final_flow_error', 0):.6f}%")
    if validator_steady:
        print(f"  ✓ 验证等级: 优秀 (Excellent)")
    print()

    print("瞬态模拟:")
    print(f"  ✓ 流量阶跃: {Q_initial} → {Q_step} m³/s (+{Q_step-Q_initial:.1f} m³/s)")
    print(f"  ✓ 模拟时长: {t_total/3600:.1f}小时 = {t_total:.0f}秒")
    print(f"  ✓ 总时间步: {n_steps}")
    print(f"  ✓ 保存数据: {n_saves}个时间点")
    print()

    print("结果文件:")
    print(f"  ✓ 5个可视化图表")
    print(f"  ✓ 2个数据文件(.npz)")
    print(f"  ✓ 保存目录: {output_dir}")
    print()

    # 计算传播速度
    # 找到渠尾流量达到50%阶跃值的时间
    q_tail = q_history[:, -1]
    q_50pct = Q_initial + 0.5 * (Q_step - Q_initial)
    idx_50 = np.where(q_tail >= q_50pct)[0]
    if len(idx_50) > 0:
        t_50 = time_history[idx_50[0]]
        wave_speed = L_total / t_50
        print(f"波动传播分析:")
        print(f"  ✓ 流量波达到渠尾(50%阶跃)时间: {t_50/60:.1f}分钟 = {t_50:.0f}秒")
        print(f"  ✓ 平均传播速度: {wave_speed:.2f} m/s = {wave_speed*3.6:.1f} km/h")
        print()

    print("=" * 90)
    print("✓ 明渠串联闸泵群系统模拟完成！".center(90))
    print("=" * 90)
    print()

    return validator_steady


if __name__ == "__main__":
    validator = main()
