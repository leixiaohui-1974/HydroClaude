#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
工况测试通用工具模块

提供标准化的工况设置、运行、输出功能
"""

import sys
import os
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.animation import FuncAnimation, PillowWriter

# 项目根目录
project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
sys.path.insert(0, project_root)

from solvers.hydrostatic_canal_solver import HydrostaticCanalSolver
from solvers.gate import SluiceGate, PumpStationAdvanced


def create_standard_system():
    """
    创建标准的串联闸泵群系统
    
    Returns:
        solver: 求解器
        structures: 建筑物列表 [gate1, gate2, pump]
    """
    # 系统参数
    L = 100000.0  # 100 km
    nx = 501
    B = 15.0  # 渠道宽度
    n = 0.025  # 糙率
    S0 = 0.0001  # 坡度
    
    # 创建求解器
    from utils.canal_utils import create_mountain_canal
    x, z = create_mountain_canal(length=L, nx=nx, slope=S0, base_elevation=0.0)
    
    solver = HydrostaticCanalSolver(x, z, width=B, roughness=n, dt=1.0)
    
    # 闸门1（25 km处）
    gate1 = SluiceGate(
        position=25000.0,
        width=B,
        discharge_coeff=0.6,
        opening=0.709
    )
    
    # 闸门2（75 km处）
    gate2 = SluiceGate(
        position=75000.0,
        width=B,
        discharge_coeff=0.6,
        opening=1.418
    )
    
    # 泵站（50 km处）- 使用高精度模型
    pump = PumpStationAdvanced(
        position=50000.0,
        width=B,
        rated_flow=30.0,
        rated_head=5.0,
        shutoff_head=6.0,
        bed_elevation_jump=5.0
    )
    
    structures = [gate1, gate2, pump]
    
    return solver, structures


def run_steady_state(solver, structures, Q_initial=30.0, h_downstream=2.0):
    """
    运行稳态模拟
    
    Args:
        solver: 求解器
        structures: 建筑物列表
        Q_initial: 初始流量
        h_downstream: 下游水深
        
    Returns:
        steady_state: 稳态数据字典
    """
    print("\n" + "="*80)
    print("稳态求解".center(80))
    print("="*80)
    
    # 设置边界条件
    solver.set_boundary_conditions(
        upstream_type='discharge',
        upstream_value=Q_initial,
        downstream_type='depth',
        downstream_value=h_downstream
    )
    
    # 初始化
    h_init = np.full(solver.nx, 3.0)
    q_init = np.full(solver.nx, Q_initial)
    solver.set_initial_conditions(h_init, q_init)
    
    # 求解稳态
    converged, iterations, error = solver.solve_steady_state_hydrostatic(
        structures=structures,
        max_iter=2000,
        tol=1e-6
    )
    
    if converged:
        print(f"✓ 稳态收敛: 迭代{iterations}次, 流量误差={error*100:.6f}%")
    else:
        print(f"⚠ 稳态未完全收敛: 迭代{iterations}次, 流量误差={error*100:.6f}%")
    
    # 保存稳态
    steady_state = {
        'x': solver.x.copy(),
        'z': solver.z.copy(),
        'h': solver.h.copy(),
        'q': solver.q.copy(),
        'converged': converged,
        'iterations': iterations,
        'error': error
    }
    
    return steady_state


def run_transient_simulation(solver, structures, duration=3600, save_interval=60):
    """
    运行瞬态模拟
    
    Args:
        solver: 求解器
        structures: 建筑物列表
        duration: 模拟时长（秒）
        save_interval: 保存间隔（秒）
        
    Returns:
        transient_data: 瞬态数据字典
    """
    print("\n" + "="*80)
    print(f"瞬态模拟 (0-{duration}秒)".center(80))
    print("="*80)
    
    n_steps = duration
    save_steps = duration // save_interval
    
    # 存储
    h_history = []
    q_history = []
    time_points = []
    
    print(f"\n进度监控:")
    print("-" * 80)
    
    for step in range(n_steps):
        t = step * solver.dt
        
        # 时间步进
        solver.step_preissmann(structures=structures, theta=0.6)
        
        # 保存数据
        if step % save_interval == 0:
            h_history.append(solver.h.copy())
            q_history.append(solver.q.copy())
            time_points.append(t)
            
            # 打印进度
            progress = (step / n_steps) * 100
            print(f"  t={t:6.0f}s ({progress:5.1f}%) | "
                  f"h_range=[{solver.h.min():.2f}, {solver.h.max():.2f}] m | "
                  f"Q_range=[{solver.q.min():.2f}, {solver.q.max():.2f}] m³/s")
    
    print("✓ 瞬态模拟完成")
    
    transient_data = {
        'x': solver.x.copy(),
        'z': solver.z.copy(),
        'time': np.array(time_points),
        'h_history': np.array(h_history),
        'q_history': np.array(q_history)
    }
    
    return transient_data


def create_animations(scenario_name, output_dir, x, z, time, h_history, q_history,
                     gate_positions=None, pump_position=None):
    """
    创建标准化动画
    
    Args:
        scenario_name: 工况名称
        output_dir: 输出目录
        x: 空间坐标
        z: 渠底高程
        time: 时间点
        h_history: 水深历史
        q_history: 流量历史
        gate_positions: 闸门位置列表
        pump_position: 泵站位置
    """
    print("\n" + "="*80)
    print("生成动画".center(80))
    print("="*80)
    
    os.makedirs(output_dir, exist_ok=True)
    
    # 动画1: 水位纵剖面
    print("  生成水位动画...")
    _create_water_level_animation(
        os.path.join(output_dir, "animation_water_level.gif"),
        scenario_name, x, z, time, h_history,
        gate_positions, pump_position
    )
    
    # 动画2: 流量纵剖面
    print("  生成流量动画...")
    _create_flow_rate_animation(
        os.path.join(output_dir, "animation_flow_rate.gif"),
        scenario_name, x, time, q_history,
        gate_positions, pump_position
    )
    
    print("✓ 动画生成完成")


def _create_water_level_animation(filepath, title, x, z, time, h_history,
                                  gate_positions, pump_position):
    """创建水位动画"""
    fig, ax = plt.subplots(figsize=(14, 6))
    
    # 计算Y轴范围
    z_surfaces = [z + h for h in h_history]
    z_min = z.min() - 0.5
    z_max = max([zs.max() for zs in z_surfaces]) + 0.5
    
    def update(frame):
        ax.clear()
        
        # 渠底
        ax.fill_between(x/1000, z_min, z, color='saddlebrown', alpha=0.7, label='Channel Bed')
        ax.plot(x/1000, z, 'k-', linewidth=2)
        
        # 水面
        z_surface = z + h_history[frame]
        ax.fill_between(x/1000, z, z_surface, color='dodgerblue', alpha=0.6, label='Water')
        ax.plot(x/1000, z_surface, 'b-', linewidth=2.5, label='Water Surface')
        
        # 标记建筑物
        if gate_positions:
            for gp in gate_positions:
                ax.axvline(gp/1000, color='green', linestyle='--', linewidth=2, alpha=0.7)
        if pump_position:
            ax.axvline(pump_position/1000, color='red', linestyle='--', linewidth=2, alpha=0.7)
        
        ax.set_xlim(0, x[-1]/1000)
        ax.set_ylim(z_min, z_max)
        ax.set_xlabel('Distance (km)', fontsize=12)
        ax.set_ylabel('Elevation (m)', fontsize=12)
        ax.set_title(f'{title} - Water Level Profile (t={time[frame]:.0f}s)', fontsize=13, fontweight='bold')
        ax.grid(True, alpha=0.3)
        ax.legend(loc='upper right', fontsize=10)
    
    anim = FuncAnimation(fig, update, frames=len(time), interval=200)
    anim.save(filepath, writer=PillowWriter(fps=5))
    plt.close()
    
    file_size = os.path.getsize(filepath) / 1024 / 1024
    print(f"    ✓ 保存: {os.path.basename(filepath)} ({file_size:.2f} MB)")


def _create_flow_rate_animation(filepath, title, x, time, q_history,
                                gate_positions, pump_position):
    """创建流量动画"""
    fig, ax = plt.subplots(figsize=(14, 6))
    
    # 计算Y轴范围
    q_min = min([q.min() for q in q_history]) * 0.9
    q_max = max([q.max() for q in q_history]) * 1.1
    
    def update(frame):
        ax.clear()
        
        # 流量分布
        ax.plot(x/1000, q_history[frame], 'b-', linewidth=2.5, label='Flow Rate')
        ax.fill_between(x/1000, 0, q_history[frame], color='cyan', alpha=0.3)
        
        # 标记建筑物
        if gate_positions:
            for gp in gate_positions:
                ax.axvline(gp/1000, color='green', linestyle='--', linewidth=2, alpha=0.7, label='Gate')
        if pump_position:
            ax.axvline(pump_position/1000, color='red', linestyle='--', linewidth=2, alpha=0.7, label='Pump')
        
        ax.set_xlim(0, x[-1]/1000)
        ax.set_ylim(q_min, q_max)
        ax.set_xlabel('Distance (km)', fontsize=12)
        ax.set_ylabel('Flow Rate (m³/s)', fontsize=12)
        ax.set_title(f'{title} - Flow Rate Distribution (t={time[frame]:.0f}s)', fontsize=13, fontweight='bold')
        ax.grid(True, alpha=0.3)
        ax.legend(loc='upper right', fontsize=10)
    
    anim = FuncAnimation(fig, update, frames=len(time), interval=200)
    anim.save(filepath, writer=PillowWriter(fps=5))
    plt.close()
    
    file_size = os.path.getsize(filepath) / 1024 / 1024
    print(f"    ✓ 保存: {os.path.basename(filepath)} ({file_size:.2f} MB)")


def create_supplementary_plots(output_dir, x, z, time, h_history, q_history,
                               gate_positions=None, pump_position=None):
    """
    创建补充图表
    
    Args:
        output_dir: 输出目录
        其他参数同上
    """
    print("\n  生成补充图表...")
    
    # 1. 稳态纵剖面
    fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(14, 10))
    
    # 水位
    z_surface_init = z + h_history[0]
    z_surface_final = z + h_history[-1]
    ax1.fill_between(x/1000, z.min()-0.5, z, color='saddlebrown', alpha=0.7)
    ax1.plot(x/1000, z, 'k-', linewidth=2, label='Bed')
    ax1.plot(x/1000, z_surface_init, 'g--', linewidth=2, label=f't={time[0]:.0f}s')
    ax1.plot(x/1000, z_surface_final, 'b-', linewidth=2, label=f't={time[-1]:.0f}s')
    if gate_positions:
        for gp in gate_positions:
            ax1.axvline(gp/1000, color='green', linestyle=':', alpha=0.5)
    if pump_position:
        ax1.axvline(pump_position/1000, color='red', linestyle=':', alpha=0.5)
    ax1.set_xlabel('Distance (km)', fontsize=11)
    ax1.set_ylabel('Elevation (m)', fontsize=11)
    ax1.set_title('Water Level Profile', fontsize=12, fontweight='bold')
    ax1.grid(True, alpha=0.3)
    ax1.legend()
    
    # 流量
    ax2.plot(x/1000, q_history[0], 'g--', linewidth=2, label=f't={time[0]:.0f}s')
    ax2.plot(x/1000, q_history[-1], 'b-', linewidth=2, label=f't={time[-1]:.0f}s')
    if gate_positions:
        for gp in gate_positions:
            ax2.axvline(gp/1000, color='green', linestyle=':', alpha=0.5)
    if pump_position:
        ax2.axvline(pump_position/1000, color='red', linestyle=':', alpha=0.5)
    ax2.set_xlabel('Distance (km)', fontsize=11)
    ax2.set_ylabel('Flow Rate (m³/s)', fontsize=11)
    ax2.set_title('Flow Rate Distribution', fontsize=12, fontweight='bold')
    ax2.grid(True, alpha=0.3)
    ax2.legend()
    
    plt.tight_layout()
    plt.savefig(os.path.join(output_dir, "steady_state_profile.png"), dpi=150, bbox_inches='tight')
    plt.close()
    print(f"    ✓ 保存: steady_state_profile.png")
    
    # 2. 时空演化图
    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(16, 6))
    
    # 水位时空
    im1 = ax1.imshow(h_history, aspect='auto', cmap='Blues', origin='lower',
                     extent=[0, x[-1]/1000, time[0], time[-1]])
    ax1.set_xlabel('Distance (km)', fontsize=11)
    ax1.set_ylabel('Time (s)', fontsize=11)
    ax1.set_title('Water Depth Spatiotemporal Evolution', fontsize=12, fontweight='bold')
    plt.colorbar(im1, ax=ax1, label='Depth (m)')
    
    # 流量时空
    im2 = ax2.imshow(q_history, aspect='auto', cmap='viridis', origin='lower',
                     extent=[0, x[-1]/1000, time[0], time[-1]])
    ax2.set_xlabel('Distance (km)', fontsize=11)
    ax2.set_ylabel('Time (s)', fontsize=11)
    ax2.set_title('Flow Rate Spatiotemporal Evolution', fontsize=12, fontweight='bold')
    plt.colorbar(im2, ax=ax2, label='Flow Rate (m³/s)')
    
    plt.tight_layout()
    plt.savefig(os.path.join(output_dir, "spatiotemporal.png"), dpi=150, bbox_inches='tight')
    plt.close()
    print(f"    ✓ 保存: spatiotemporal.png")


def save_scenario_data(output_dir, scenario_name, x, z, time, h_history, q_history,
                       steady_state, description=""):
    """
    保存工况数据
    
    Args:
        output_dir: 输出目录
        scenario_name: 工况名称
        ...
        description: 工况描述
    """
    print("\n  保存数据...")
    
    data_dict = {
        'scenario_name': scenario_name,
        'description': description,
        'x': x,
        'z': z,
        'time': time,
        'h_history': h_history,
        'q_history': q_history,
        'steady_converged': steady_state['converged'],
        'steady_iterations': steady_state['iterations'],
        'steady_error': steady_state['error']
    }
    
    filepath = os.path.join(output_dir, "data.npz")
    np.savez(filepath, **data_dict)
    
    file_size = os.path.getsize(filepath) / 1024 / 1024
    print(f"    ✓ 保存: data.npz ({file_size:.2f} MB)")


def print_scenario_summary(scenario_name, steady_state, h_history, q_history, time):
    """打印工况总结"""
    print("\n" + "="*80)
    print(f"{scenario_name} - 模拟总结".center(80))
    print("="*80)
    
    print(f"\n稳态求解:")
    print(f"  收敛: {'✓' if steady_state['converged'] else '✗'}")
    print(f"  迭代次数: {steady_state['iterations']}")
    print(f"  流量误差: {steady_state['error']*100:.6f}%")
    
    print(f"\n瞬态模拟:")
    print(f"  时长: {time[-1]:.0f}s")
    print(f"  保存点: {len(time)}个")
    
    print(f"\n最终状态:")
    print(f"  水深范围: [{h_history[-1].min():.2f}, {h_history[-1].max():.2f}] m")
    print(f"  流量范围: [{q_history[-1].min():.2f}, {q_history[-1].max():.2f}] m³/s")
    print(f"  平均流量: {q_history[-1].mean():.2f} m³/s")
    
    # 质量守恒检查
    Q_in = q_history[-1][0]
    Q_out = q_history[-1][-1]
    storage_rate = Q_in - Q_out
    print(f"\n质量守恒:")
    print(f"  入流: {Q_in:.2f} m³/s")
    print(f"  出流: {Q_out:.2f} m³/s")
    print(f"  蓄水速率: {storage_rate:.2f} m³/s")
    
    print("\n" + "="*80)
    print("✓ 工况模拟完成".center(80))
    print("="*80 + "\n")
