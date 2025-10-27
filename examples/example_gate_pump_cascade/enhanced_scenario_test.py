#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
串联明渠闸泵群系统 - 增强版工况测试

改进点：
1. 动画中显示边界条件和控制条件的实时变化
2. 详细的初始恒定流状态分析
3. 深入的数值稳定性分析（包括CFL条件、质量守恒）
4. 增强的可视化输出
5. 聚焦重点工况进行精细化分析

作者: Claude
日期: 2025-10-27
"""

import sys
import os
import time
import json
from datetime import datetime

# 路径设置
project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, project_root)

import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.animation import FuncAnimation, PillowWriter
from matplotlib.patches import Rectangle
from matplotlib.gridspec import GridSpec

from solvers.hydrostatic_canal_solver import HydrostaticCanalSolver
from solvers.gate import SluiceGate, PumpStation
from utils.canal_utils import compute_steady_uniform_flow


# ==================== 工况配置 ====================

FOCUSED_SCENARIOS = {
    # ========== 1. 上游流量扰动工况 ==========
    'S01_flow_step_small': {
        'name': '工况01: 上游流量小幅阶跃',
        'description': '初始30 m³/s，t=300s阶跃至35 m³/s (+17%)',
        'category': '上游流量扰动',
        'Q_initial': 30.0,
        'Q_upstream_func': lambda t: 35.0 if t >= 300 else 30.0,
        'h_downstream_func': None,
        'gate1_opening_func': None,
        't_total': 2400.0,
    },
    
    'S03_flow_step_large': {
        'name': '工况03: 上游流量大幅阶跃',
        'description': '初始30 m³/s，t=300s阶跃至55 m³/s (+83%)',
        'category': '上游流量扰动',
        'Q_initial': 30.0,
        'Q_upstream_func': lambda t: 55.0 if t >= 300 else 30.0,
        'h_downstream_func': None,
        'gate1_opening_func': None,
        't_total': 2400.0,
    },
    
    'S05_flow_fluctuation': {
        'name': '工况05: 上游流量周期波动',
        'description': '初始30 m³/s，t=300s后周期性波动 30±5 m³/s',
        'category': '上游流量扰动',
        'Q_initial': 30.0,
        'Q_upstream_func': lambda t: 30.0 + 5.0 * np.sin(2 * np.pi * (t - 300) / 600.0) if t >= 300 else 30.0,
        'h_downstream_func': None,
        'gate1_opening_func': None,
        't_total': 2400.0,
    },
    
    # ========== 2. 下游水位扰动工况 ==========
    'S06_downstream_h_step_up': {
        'name': '工况06: 下游水位抬高',
        'description': '初始均匀流水深，t=300s阶跃至+1.0m',
        'category': '下游水位扰动',
        'Q_initial': 30.0,
        'Q_upstream_func': lambda t: 30.0,
        'h_downstream_func': lambda t, h_ref: h_ref + 1.0 if t >= 300 else h_ref,
        'gate1_opening_func': None,
        't_total': 2400.0,
    },
    
    # ========== 3. 闸门开度调节工况 ==========
    'S10_gate1_close_more': {
        'name': '工况10: 闸门1开度减小',
        'description': '初始5m，t=300s阶跃至3m（减小泄流）',
        'category': '闸门开度调节',
        'Q_initial': 30.0,
        'Q_upstream_func': lambda t: 30.0,
        'h_downstream_func': None,
        'gate1_opening_func': lambda t: 3.0 if t >= 300 else 5.0,
        't_total': 2400.0,
    },
    
    # ========== 4. 多重扰动组合工况 ==========
    'S13_combined_flow_and_gate': {
        'name': '工况13: 流量增加+闸门调节组合',
        'description': '初始30 m³/s，t=300s流量→40 m³/s，t=900s闸门5m→7m',
        'category': '多重扰动组合',
        'Q_initial': 30.0,
        'Q_upstream_func': lambda t: 40.0 if t >= 300 else 30.0,
        'h_downstream_func': None,
        'gate1_opening_func': lambda t: 7.0 if t >= 900 else 5.0,
        't_total': 2400.0,
    },
    
    # ========== 5. 极端工况 ==========
    'S16_extreme_flow_increase': {
        'name': '工况16: 极端流量突增',
        'description': '初始30 m³/s，t=300s突增至80 m³/s (+167%)',
        'category': '极端工况',
        'Q_initial': 30.0,
        'Q_upstream_func': lambda t: 80.0 if t >= 300 else 30.0,
        'h_downstream_func': None,
        'gate1_opening_func': None,
        't_total': 2400.0,
    },
    
    'S17_rapid_gate_closure': {
        'name': '工况17: 闸门快速关闭',
        'description': '初始5m，t=300s快速关闭至1m（模拟事故）',
        'category': '极端工况',
        'Q_initial': 30.0,
        'Q_upstream_func': lambda t: 30.0,
        'h_downstream_func': None,
        'gate1_opening_func': lambda t: 1.0 if t >= 300 else 5.0,
        't_total': 2400.0,
    },
}


def analyze_steady_state_detailed(solver, h_steady, q_steady, gate1_pos, gate2_pos, pump_pos):
    """详细分析稳态结果"""
    print("\n" + "="*80)
    print("详细稳态分析".center(80))
    print("="*80)
    
    # 基本统计
    print(f"\n▶ 基本统计:")
    print(f"  水深范围: {np.min(h_steady):.3f} - {np.max(h_steady):.3f} m (均值: {np.mean(h_steady):.3f} m)")
    print(f"  流量范围: {np.min(q_steady):.2f} - {np.max(q_steady):.2f} m³/s (均值: {np.mean(q_steady):.2f} m³/s)")
    
    # 关键位置统计
    gate1_idx = np.argmin(np.abs(solver.x - gate1_pos))
    pump_idx = np.argmin(np.abs(solver.x - pump_pos))
    gate2_idx = np.argmin(np.abs(solver.x - gate2_pos))
    
    print(f"\n▶ 关键位置水深:")
    print(f"  闸门1前: {h_steady[gate1_idx-1]:.3f} m, 后: {h_steady[gate1_idx+1]:.3f} m")
    print(f"  泵站前:  {h_steady[pump_idx-1]:.3f} m, 后: {h_steady[pump_idx+1]:.3f} m")
    print(f"  闸门2前: {h_steady[gate2_idx-1]:.3f} m, 后: {h_steady[gate2_idx+1]:.3f} m")
    
    print(f"\n▶ 关键位置流量:")
    print(f"  闸门1前: {q_steady[gate1_idx-1]:.2f} m³/s, 后: {q_steady[gate1_idx+1]:.2f} m³/s")
    print(f"  泵站前:  {q_steady[pump_idx-1]:.2f} m³/s, 后: {q_steady[pump_idx+1]:.2f} m³/s")
    print(f"  闸门2前: {q_steady[gate2_idx-1]:.2f} m³/s, 后: {q_steady[gate2_idx+1]:.2f} m³/s")
    
    # 质量守恒检查
    q_in = q_steady[0]
    q_out = q_steady[-1]
    mass_error = abs(q_in - q_out) / (q_in + 1e-6)
    
    print(f"\n▶ 稳态质量守恒:")
    print(f"  上游流量: {q_in:.2f} m³/s")
    print(f"  下游流量: {q_out:.2f} m³/s")
    print(f"  相对误差: {mass_error:.6f} ({'✓ 通过' if mass_error < 0.01 else '⚠ 警告'})")
    
    print("="*80)
    
    return {
        'h_mean': float(np.mean(h_steady)),
        'h_min': float(np.min(h_steady)),
        'h_max': float(np.max(h_steady)),
        'q_mean': float(np.mean(q_steady)),
        'q_min': float(np.min(q_steady)),
        'q_max': float(np.max(q_steady)),
        'q_in': float(q_in),
        'q_out': float(q_out),
        'mass_error_steady': float(mass_error),
        'h_at_gate1_before': float(h_steady[gate1_idx-1]),
        'h_at_pump_before': float(h_steady[pump_idx-1]),
        'h_at_gate2_before': float(h_steady[gate2_idx-1]),
    }


def analyze_stability_detailed(time_history, h_history, q_history, pump_idx, dt):
    """详细稳定性分析"""
    print("\n" + "="*80)
    print("详细稳定性分析".center(80))
    print("="*80)
    
    # 1. CFL条件检查
    dx = 100000.0 / (h_history.shape[1] - 1)  # 假设总长度100km
    
    # 计算流速
    u_history = np.zeros_like(h_history)
    for i in range(h_history.shape[0]):
        u_history[i, :] = q_history[i, :] / (15.0 * (h_history[i, :] + 1e-6))  # B=15m
    
    # 计算波速
    g = 9.81
    c_history = np.sqrt(g * h_history)
    
    # CFL数
    cfl = (np.abs(u_history) + c_history) * dt / dx
    cfl_max = np.max(cfl)
    cfl_mean = np.mean(cfl)
    
    print(f"\n▶ CFL条件:")
    print(f"  时间步长: dt = {dt:.2f} s")
    print(f"  空间步长: dx = {dx:.1f} m")
    print(f"  最大CFL: {cfl_max:.4f} ({'✓ 满足' if cfl_max < 1.0 else '⚠ 超标'})")
    print(f"  平均CFL: {cfl_mean:.4f}")
    
    # 2. 质量守恒时间序列分析
    q_in = q_history[:, 0]
    q_out = q_history[:, -1]
    storage_rate = q_in - q_out
    
    # 计算总蓄水量（通过积分）
    total_storage = np.trapz(storage_rate, time_history)
    
    # 通过水深变化计算蓄水量
    B = 15.0
    total_volume_change = B * dx * np.sum(h_history[-1, :] - h_history[0, :])
    
    mass_balance_error = abs(total_storage - total_volume_change) / (abs(total_storage) + 1e-6)
    
    print(f"\n▶ 质量守恒分析:")
    print(f"  平均流入: {np.mean(q_in):.2f} m³/s")
    print(f"  平均流出: {np.mean(q_out):.2f} m³/s")
    print(f"  平均蓄水速率: {np.mean(storage_rate):.2f} m³/s")
    print(f"  累计流入-流出: {total_storage:.1f} m³")
    print(f"  渠道容积变化: {total_volume_change:.1f} m³")
    print(f"  质量平衡误差: {mass_balance_error:.6f} ({'✓ 通过' if mass_balance_error < 0.05 else '⚠ 警告'})")
    
    # 3. 后期稳定性检查（最后10%的数据）
    n_tail = max(int(len(time_history) * 0.1), 10)
    h_tail = h_history[-n_tail:, pump_idx-1]
    q_tail = q_history[-n_tail:, pump_idx]
    
    h_cv = np.std(h_tail) / (np.mean(h_tail) + 1e-6)
    q_cv = np.std(q_tail) / (np.mean(q_tail) + 1e-6)
    
    print(f"\n▶ 后期稳定性 (最后{n_tail}个时间点):")
    print(f"  泵前水深变异系数: {h_cv:.6f} ({'✓ 稳定' if h_cv < 0.01 else '⚠ 波动'})")
    print(f"  泵站流量变异系数: {q_cv:.6f} ({'✓ 稳定' if q_cv < 0.01 else '⚠ 波动'})")
    
    # 4. 全局变化率检查
    dh_dt = np.gradient(h_history[:, pump_idx-1], time_history)
    dq_dt = np.gradient(q_history[:, pump_idx], time_history)
    
    print(f"\n▶ 变化率统计:")
    print(f"  最大水深变化率: {np.max(np.abs(dh_dt)):.6f} m/s")
    print(f"  最大流量变化率: {np.max(np.abs(dq_dt)):.6f} m³/s²")
    
    print("="*80)
    
    return {
        'cfl_max': float(cfl_max),
        'cfl_mean': float(cfl_mean),
        'mass_balance_error': float(mass_balance_error),
        'total_storage': float(total_storage),
        'total_volume_change': float(total_volume_change),
        'h_cv_tail': float(h_cv),
        'q_cv_tail': float(q_cv),
        'max_dh_dt': float(np.max(np.abs(dh_dt))),
        'max_dq_dt': float(np.max(np.abs(dq_dt))),
    }


def create_enhanced_animation(output_dir, x, z, time, h_history, q_history, config, 
                             gate1_pos, gate2_pos, pump_pos, pump_head_history):
    """
    创建增强版动画，包含边界条件和控制条件的实时显示
    """
    print("  生成增强版动画...")
    
    # 准备边界条件数据
    Q_upstream_values = np.array([config['Q_upstream_func'](t) for t in time])
    
    # 下游水位（如果有定义）
    if config.get('h_downstream_func') is not None:
        h_uniform = compute_steady_uniform_flow(config['Q_initial'], 15.0, 0.0001, 0.025)
        h_downstream_values = np.array([config['h_downstream_func'](t, h_uniform) for t in time])
    else:
        h_downstream_values = None
    
    # 闸门开度（如果有定义）
    if config.get('gate1_opening_func') is not None:
        gate1_opening_values = np.array([config['gate1_opening_func'](t) for t in time])
    else:
        gate1_opening_values = None
    
    # 创建图形
    fig = plt.figure(figsize=(20, 12))
    gs = GridSpec(3, 2, figure=fig, height_ratios=[2, 1, 1], hspace=0.3, wspace=0.3)
    
    # 主图：水位纵剖面
    ax_main = fig.add_subplot(gs[0, :])
    
    # 子图：边界条件和控制
    ax_q_upstream = fig.add_subplot(gs[1, 0])
    ax_pump = fig.add_subplot(gs[1, 1])
    ax_gate = fig.add_subplot(gs[2, 0])
    ax_storage = fig.add_subplot(gs[2, 1])
    
    # 主图设置
    eta = z + h_history[0, :]
    z_min = np.min(z) - 1
    z_max = np.max(eta) + 2
    
    def init():
        ax_main.clear()
        ax_q_upstream.clear()
        ax_pump.clear()
        ax_gate.clear()
        ax_storage.clear()
    
    def update(frame):
        # 清空
        ax_main.clear()
        ax_q_upstream.clear()
        ax_pump.clear()
        ax_gate.clear()
        ax_storage.clear()
        
        t_current = time[frame]
        
        # ========== 主图：水位纵剖面 ==========
        z_surface = z + h_history[frame, :]
        
        ax_main.plot(x/1000, z, 'k-', linewidth=2.5, label='Bed')
        ax_main.fill_between(x/1000, z, z_surface, color='dodgerblue', alpha=0.6, label='Water')
        ax_main.plot(x/1000, z_surface, 'b-', linewidth=2.5, label='Water Surface')
        
        # 标记建筑物
        ax_main.axvline(gate1_pos/1000, color='green', linestyle='--', linewidth=2, alpha=0.7, label='Gate1')
        ax_main.axvline(pump_pos/1000, color='red', linestyle='--', linewidth=2.5, alpha=0.7, label='Pump')
        ax_main.axvline(gate2_pos/1000, color='green', linestyle='--', linewidth=2, alpha=0.7, label='Gate2')
        
        ax_main.set_xlim(0, x[-1]/1000)
        ax_main.set_ylim(z_min, z_max)
        ax_main.set_xlabel('Distance (km)', fontsize=13, fontweight='bold')
        ax_main.set_ylabel('Elevation (m)', fontsize=13, fontweight='bold')
        ax_main.set_title(f'{config["name"]} | t={t_current:.0f}s ({t_current/60:.1f}min)', 
                         fontsize=15, fontweight='bold')
        ax_main.grid(True, alpha=0.3)
        ax_main.legend(loc='upper left', fontsize=11, ncol=5)
        
        # ========== 上游流量边界条件 ==========
        ax_q_upstream.plot(time[:frame+1]/60, Q_upstream_values[:frame+1], 'b-', linewidth=2)
        ax_q_upstream.plot(time[frame]/60, Q_upstream_values[frame], 'ro', markersize=10)
        ax_q_upstream.axhline(config['Q_initial'], color='gray', linestyle='--', alpha=0.5, 
                             label=f'Initial: {config["Q_initial"]:.0f} m³/s')
        ax_q_upstream.set_xlim(0, time[-1]/60)
        ax_q_upstream.set_ylim(min(Q_upstream_values)*0.9, max(Q_upstream_values)*1.1)
        ax_q_upstream.set_xlabel('Time (min)', fontsize=11)
        ax_q_upstream.set_ylabel('Flow Rate (m³/s)', fontsize=11)
        ax_q_upstream.set_title('Upstream Boundary: Flow Rate', fontsize=12, fontweight='bold')
        ax_q_upstream.grid(True, alpha=0.3)
        ax_q_upstream.legend(fontsize=9)
        ax_q_upstream.text(0.98, 0.98, f'Q = {Q_upstream_values[frame]:.1f} m³/s', 
                          transform=ax_q_upstream.transAxes, fontsize=13, fontweight='bold',
                          va='top', ha='right', bbox=dict(boxstyle='round', facecolor='yellow', alpha=0.8))
        
        # ========== 泵站工作状态 ==========
        pump_idx = np.argmin(np.abs(x - pump_pos))
        
        ax_pump.plot(time[:frame+1]/60, pump_head_history[:frame+1], 'r-', linewidth=2)
        ax_pump.plot(time[frame]/60, pump_head_history[frame], 'ro', markersize=10)
        ax_pump.axhline(5.0, color='gray', linestyle='--', alpha=0.5, label='Rated: 5.0 m')
        ax_pump.axhline(6.0, color='orange', linestyle='--', alpha=0.5, label='Shutoff: 6.0 m')
        ax_pump.set_xlim(0, time[-1]/60)
        ax_pump.set_ylim(0, 8)
        ax_pump.set_xlabel('Time (min)', fontsize=11)
        ax_pump.set_ylabel('Head (m)', fontsize=11)
        ax_pump.set_title('Pump Station: Head', fontsize=12, fontweight='bold')
        ax_pump.grid(True, alpha=0.3)
        ax_pump.legend(fontsize=9)
        ax_pump.text(0.98, 0.98, f'H = {pump_head_history[frame]:.2f} m', 
                    transform=ax_pump.transAxes, fontsize=13, fontweight='bold',
                    va='top', ha='right', bbox=dict(boxstyle='round', facecolor='yellow', alpha=0.8))
        
        # ========== 闸门开度（如果有变化）==========
        if gate1_opening_values is not None:
            ax_gate.plot(time[:frame+1]/60, gate1_opening_values[:frame+1], 'g-', linewidth=2)
            ax_gate.plot(time[frame]/60, gate1_opening_values[frame], 'ro', markersize=10)
            ax_gate.axhline(5.0, color='gray', linestyle='--', alpha=0.5, label='Initial: 5.0 m')
            ax_gate.set_xlim(0, time[-1]/60)
            ax_gate.set_ylim(min(gate1_opening_values)*0.8, max(gate1_opening_values)*1.2)
            ax_gate.set_xlabel('Time (min)', fontsize=11)
            ax_gate.set_ylabel('Opening (m)', fontsize=11)
            ax_gate.set_title('Gate1: Opening', fontsize=12, fontweight='bold')
            ax_gate.grid(True, alpha=0.3)
            ax_gate.legend(fontsize=9)
            ax_gate.text(0.98, 0.98, f'a = {gate1_opening_values[frame]:.2f} m', 
                        transform=ax_gate.transAxes, fontsize=13, fontweight='bold',
                        va='top', ha='right', bbox=dict(boxstyle='round', facecolor='yellow', alpha=0.8))
        else:
            ax_gate.text(0.5, 0.5, 'Gate Opening: Constant 5.0 m', 
                        transform=ax_gate.transAxes, fontsize=14, fontweight='bold',
                        ha='center', va='center')
            ax_gate.set_xlim(0, 1)
            ax_gate.set_ylim(0, 1)
            ax_gate.axis('off')
        
        # ========== 渠道蓄水情况（通过水深变化估算）==========
        # 计算每个时刻的平均水深
        h_mean_history = np.mean(h_history[:frame+1, :], axis=1)
        
        ax_storage.plot(time[:frame+1]/60, h_mean_history, 'purple', linewidth=2)
        ax_storage.plot(time[frame]/60, h_mean_history[-1], 'ro', markersize=10)
        ax_storage.axhline(h_mean_history[0], color='gray', linestyle='--', alpha=0.5, 
                          label=f'Initial: {h_mean_history[0]:.3f} m')
        ax_storage.set_xlim(0, time[-1]/60)
        ax_storage.set_xlabel('Time (min)', fontsize=11)
        ax_storage.set_ylabel('Mean Depth (m)', fontsize=11)
        ax_storage.set_title('Channel: Mean Water Depth', fontsize=12, fontweight='bold')
        ax_storage.grid(True, alpha=0.3)
        ax_storage.legend(fontsize=9)
        
        change = h_mean_history[-1] - h_mean_history[0]
        ax_storage.text(0.98, 0.02, f'Δh = {change:+.3f} m', 
                       transform=ax_storage.transAxes, fontsize=13, fontweight='bold',
                       va='bottom', ha='right', 
                       bbox=dict(boxstyle='round', 
                                facecolor='lightgreen' if abs(change) < 0.5 else 'yellow', 
                                alpha=0.8))
    
    anim = FuncAnimation(fig, update, init_func=init, frames=len(time), interval=200)
    anim.save(os.path.join(output_dir, "animation_enhanced.gif"), writer=PillowWriter(fps=5), dpi=100)
    plt.close()
    
    print("  ✓ 增强版动画已生成")


def create_comprehensive_steady_state_figure(output_dir, x, z, h_steady, q_steady, 
                                            gate1_pos, gate2_pos, pump_pos, title, steady_analysis):
    """创建综合稳态图（包含更多细节）"""
    fig = plt.figure(figsize=(20, 12))
    gs = GridSpec(3, 2, figure=fig, height_ratios=[1.5, 1, 1], hspace=0.3, wspace=0.3)
    
    # 水位纵剖面
    ax1 = fig.add_subplot(gs[0, :])
    eta_steady = z + h_steady
    
    ax1.plot(x / 1000, eta_steady, 'b-', linewidth=2.5, label='Water Level', zorder=3)
    ax1.fill_between(x / 1000, z, eta_steady, alpha=0.3, color='cyan', zorder=2)
    ax1.plot(x / 1000, z, 'k-', linewidth=2, label='Bed Level', zorder=1)
    
    # 标记关键位置
    for pos, name, color in [(gate1_pos/1000, 'Gate1', 'green'), 
                              (pump_pos/1000, 'Pump', 'red'), 
                              (gate2_pos/1000, 'Gate2', 'green')]:
        ax1.axvline(pos, color=color, linestyle='--', linewidth=2, alpha=0.6, zorder=4)
        ax1.text(pos, ax1.get_ylim()[1] * 0.98, name, color=color, fontsize=12, fontweight='bold',
                ha='center', va='top', bbox=dict(boxstyle='round', facecolor='white', alpha=0.9))
    
    ax1.set_xlabel('Distance (km)', fontsize=13, fontweight='bold')
    ax1.set_ylabel('Elevation (m)', fontsize=13, fontweight='bold')
    ax1.set_title('Steady-State Longitudinal Profile', fontsize=15, fontweight='bold')
    ax1.legend(fontsize=12, loc='upper left')
    ax1.grid(True, alpha=0.3)
    
    # 水深分布
    ax2 = fig.add_subplot(gs[1, 0])
    ax2.plot(x / 1000, h_steady, 'b-', linewidth=2.5)
    ax2.axhline(steady_analysis['h_mean'], color='gray', linestyle='--', linewidth=1.5, 
                alpha=0.5, label=f'Mean: {steady_analysis["h_mean"]:.3f} m')
    
    for pos, color in [(gate1_pos/1000, 'green'), (pump_pos/1000, 'red'), (gate2_pos/1000, 'green')]:
        ax2.axvline(pos, color=color, linestyle='--', linewidth=1.5, alpha=0.6)
    
    ax2.set_xlabel('Distance (km)', fontsize=12)
    ax2.set_ylabel('Water Depth (m)', fontsize=12)
    ax2.set_title('Water Depth Distribution', fontsize=13, fontweight='bold')
    ax2.legend(fontsize=10)
    ax2.grid(True, alpha=0.3)
    
    # 流量分布
    ax3 = fig.add_subplot(gs[1, 1])
    ax3.plot(x / 1000, q_steady, 'g-', linewidth=2.5)
    ax3.axhline(steady_analysis['q_mean'], color='gray', linestyle='--', linewidth=1.5,
                alpha=0.5, label=f'Mean: {steady_analysis["q_mean"]:.2f} m³/s')
    
    for pos, color in [(gate1_pos/1000, 'green'), (pump_pos/1000, 'red'), (gate2_pos/1000, 'green')]:
        ax3.axvline(pos, color=color, linestyle='--', linewidth=1.5, alpha=0.6)
    
    ax3.set_xlabel('Distance (km)', fontsize=12)
    ax3.set_ylabel('Flow Rate (m³/s)', fontsize=12)
    ax3.set_title('Flow Rate Distribution', fontsize=13, fontweight='bold')
    ax3.legend(fontsize=10)
    ax3.grid(True, alpha=0.3)
    
    # 比能和弗劳德数
    B = 15.0
    g = 9.81
    v = q_steady / (B * h_steady + 1e-6)
    Fr = v / np.sqrt(g * h_steady + 1e-6)
    E = h_steady + v**2 / (2 * g)
    
    ax4 = fig.add_subplot(gs[2, 0])
    ax4.plot(x / 1000, Fr, 'orange', linewidth=2.5)
    ax4.axhline(1.0, color='red', linestyle='--', linewidth=1.5, alpha=0.5, label='Critical Fr=1')
    
    for pos, color in [(gate1_pos/1000, 'green'), (pump_pos/1000, 'red'), (gate2_pos/1000, 'green')]:
        ax4.axvline(pos, color=color, linestyle='--', linewidth=1.5, alpha=0.6)
    
    ax4.set_xlabel('Distance (km)', fontsize=12)
    ax4.set_ylabel('Froude Number', fontsize=12)
    ax4.set_title('Froude Number Distribution', fontsize=13, fontweight='bold')
    ax4.legend(fontsize=10)
    ax4.grid(True, alpha=0.3)
    ax4.set_ylim(0, max(2.0, np.max(Fr) * 1.1))
    
    # 比能
    ax5 = fig.add_subplot(gs[2, 1])
    ax5.plot(x / 1000, E, 'purple', linewidth=2.5)
    
    for pos, color in [(gate1_pos/1000, 'green'), (pump_pos/1000, 'red'), (gate2_pos/1000, 'green')]:
        ax5.axvline(pos, color=color, linestyle='--', linewidth=1.5, alpha=0.6)
    
    ax5.set_xlabel('Distance (km)', fontsize=12)
    ax5.set_ylabel('Specific Energy (m)', fontsize=12)
    ax5.set_title('Specific Energy Distribution', fontsize=13, fontweight='bold')
    ax5.grid(True, alpha=0.3)
    
    plt.suptitle(f'{title} - Comprehensive Steady State Analysis', 
                fontsize=16, fontweight='bold', y=0.995)
    plt.savefig(os.path.join(output_dir, "steady_state_comprehensive.png"), dpi=150, bbox_inches='tight')
    plt.close()


def run_enhanced_scenario(scenario_id, config, output_base_dir):
    """运行单个增强版工况"""
    print("\n" + "="*100)
    print(f"{config['name']} [增强分析模式]".center(100))
    print("="*100)
    print(f"\n{config['description']}")
    print(f"类别: {config['category']}")
    print("-"*100)
    
    start_time = time.time()
    
    # ==================== 系统参数 ====================
    L_total = 100000.0
    B = 15.0
    S0 = 0.0001
    n = 0.025
    nx = 501  # 使用更精细的网格
    dt = 0.5  # 使用更小的时间步长确保稳定性
    
    gate1_pos = 25000.0
    pump_pos = 50000.0
    gate2_pos = 75000.0
    
    # ==================== 创建求解器 ====================
    print("\n▶ 创建求解器和结构物...")
    
    gate1 = SluiceGate(gate1_pos, B, 5.0, 0.6)
    gate2 = SluiceGate(gate2_pos, B, 5.0, 0.6)
    pump = PumpStation(
        position=pump_pos,
        width=B,
        rated_flow=30.0,
        rated_head=5.0,
        min_suction_head=2.0
    )
    
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
    
    # 配置底床高程（泵站后抬高5.0m，与泵站额定扬程一致）
    # 注意：根据能量方程 h_down = h_up + (z_up - z_down) + H_pump
    # 如果 z_down = z_up + H_pump，则 h_down ≈ h_up（水深基本不变）
    pump_idx = np.argmin(np.abs(solver.x - pump_pos))
    solver.z[pump_idx:] += 5.0
    
    print(f"  ✓ 网格: {nx}点, Δx={L_total/(nx-1):.1f}m")
    print(f"  ✓ 时间步长: {dt}s")
    
    # ==================== 稳态求解 ====================
    print("\n▶ 稳态求解...")
    
    Q_initial = config.get('Q_initial', 30.0)
    h_uniform = compute_steady_uniform_flow(Q_initial, B, S0, n)
    h_downstream_boundary = h_uniform
    
    solver.h[:] = h_uniform
    solver.hu[:] = Q_initial / B
    
    try:
        result_steady = solver.solve_steady_state(
            Q_target=Q_initial,
            h_downstream=h_downstream_boundary,
            convergence_tol=0.0001,  # 更严格的收敛判据
            max_iterations=2000,
            dt=dt,
            verbose=False
        )
        
        if result_steady['converged']:
            print(f"  ✓ 稳态收敛 (迭代{result_steady['iterations']}次)")
        else:
            print(f"  ⚠ 稳态未完全收敛 (迭代{result_steady['iterations']}次)")
            
    except Exception as e:
        print(f"  ✗ 稳态求解失败: {str(e)}")
        return {'success': False, 'error': str(e), 'stage': 'steady_state'}
    
    h_steady = solver.h.copy()
    hu_steady = solver.hu.copy()
    q_steady = hu_steady * B
    
    # 详细稳态分析
    steady_analysis = analyze_steady_state_detailed(
        solver, h_steady, q_steady, gate1_pos, gate2_pos, pump_pos
    )
    steady_analysis['converged'] = result_steady['converged']
    steady_analysis['iterations'] = result_steady['iterations']
    
    # ==================== 瞬态模拟 ====================
    print("\n▶ 瞬态模拟...")
    
    solver.h[:] = h_steady
    solver.hu[:] = hu_steady
    
    t_total = config.get('t_total', 2400.0)
    n_steps = int(t_total / dt)
    save_interval = int(30 / dt)  # 每30s保存一次（更频繁）
    n_saves = n_steps // save_interval + 1
    
    # 历史数据数组
    h_history = np.zeros((n_saves, solver.nx))
    q_history = np.zeros((n_saves, solver.nx))
    pump_head_history = np.zeros(n_saves)
    pump_flow_history = np.zeros(n_saves)
    time_history = np.zeros(n_saves)
    
    h_history[0, :] = solver.h
    q_history[0, :] = solver.hu * B
    pump_head_history[0] = pump.rated_head  # PumpStation使用固定额定扬程
    pump_flow_history[0] = q_history[0, pump_idx]
    time_history[0] = 0.0
    
    # 获取边界条件函数
    Q_upstream_func = config['Q_upstream_func']
    h_downstream_func = config.get('h_downstream_func', None)
    gate1_opening_func = config.get('gate1_opening_func', None)
    
    print(f"  总步数: {n_steps}, 保存次数: {n_saves}")
    
    # 时间推进
    save_idx = 1
    failed = False
    
    try:
        for step in range(1, n_steps + 1):
            t_current = step * dt
            
            # 更新边界条件
            Q_upstream = Q_upstream_func(t_current)
            
            if h_downstream_func is not None:
                h_downstream = h_downstream_func(t_current, h_downstream_boundary)
            else:
                h_downstream = h_downstream_boundary
            
            if gate1_opening_func is not None:
                gate1.opening = gate1_opening_func(t_current)
            
            # Preissmann时间推进
            h_new, hu_new = solver.step_preissmann(
                dt=dt,
                max_iter=20,
                enforce_bc=True,
                Q_in=Q_upstream,
                h_out=h_downstream
            )
            
            # 检查数值稳定性
            if np.any(np.isnan(h_new)) or np.any(np.isinf(h_new)):
                print(f"  ✗ 数值不稳定 (t={t_current:.1f}s)")
                failed = True
                break
            
            if np.any(h_new < 0):
                print(f"  ✗ 出现负水深 (t={t_current:.1f}s, min_h={np.min(h_new):.3f}m)")
                failed = True
                break
            
            solver.h[:] = h_new
            solver.hu[:] = hu_new
            
            # 保存数据
            if step % save_interval == 0:
                h_history[save_idx, :] = solver.h
                q_history[save_idx, :] = solver.hu * B
                pump_head_history[save_idx] = pump.rated_head  # PumpStation使用固定额定扬程
                pump_flow_history[save_idx] = q_history[save_idx, pump_idx]
                time_history[save_idx] = t_current
                
                if save_idx % 10 == 0:
                    progress = (step / n_steps) * 100
                    print(f"  进度: {progress:5.1f}% | t={t_current:6.0f}s | "
                          f"泵前h={solver.h[pump_idx-1]:.3f}m | "
                          f"泵Q={q_history[save_idx, pump_idx]:.2f}m³/s | "
                          f"泵H={pump.rated_head:.3f}m")
                
                save_idx += 1
        
        if not failed:
            print("  ✓ 瞬态模拟完成")
            
    except Exception as e:
        print(f"  ✗ 瞬态模拟失败: {str(e)}")
        import traceback
        traceback.print_exc()
        return {'success': False, 'error': str(e), 'stage': 'transient'}
    
    if failed:
        return {'success': False, 'error': 'Numerical instability', 'stage': 'transient'}
    
    # 截取有效数据
    if save_idx < n_saves:
        h_history = h_history[:save_idx, :]
        q_history = q_history[:save_idx, :]
        pump_head_history = pump_head_history[:save_idx]
        pump_flow_history = pump_flow_history[:save_idx]
        time_history = time_history[:save_idx]
    
    elapsed_time = time.time() - start_time
    
    # ==================== 详细稳定性分析 ====================
    stability_analysis = analyze_stability_detailed(
        time_history, h_history, q_history, pump_idx, dt
    )
    
    # ==================== 生成输出 ====================
    print("\n▶ 生成结果文件...")
    
    output_dir = os.path.join(output_base_dir, scenario_id)
    os.makedirs(output_dir, exist_ok=True)
    
    try:
        # 1. 综合稳态图
        print("  生成综合稳态图...")
        create_comprehensive_steady_state_figure(
            output_dir, solver.x, solver.z, h_steady, q_steady,
            gate1_pos, gate2_pos, pump_pos, config['name'], steady_analysis
        )
        
        # 2. 增强版动画
        create_enhanced_animation(
            output_dir, solver.x, solver.z, time_history, h_history, q_history, config,
            gate1_pos, gate2_pos, pump_pos, pump_head_history
        )
        
        # 3. 保存数据
        print("  保存数据...")
        np.savez(
            os.path.join(output_dir, "enhanced_data.npz"),
            x=solver.x,
            z=solver.z,
            time=time_history,
            h_history=h_history,
            q_history=q_history,
            pump_head_history=pump_head_history,
            pump_flow_history=pump_flow_history,
            h_steady=h_steady,
            q_steady=q_steady
        )
        
        # 4. 生成详细报告
        print("  生成详细报告...")
        # TODO: 生成增强版报告
        
        print(f"  ✓ 所有结果已保存至: {output_dir}")
        
    except Exception as e:
        print(f"  ✗ 生成输出失败: {str(e)}")
        import traceback
        traceback.print_exc()
        return {'success': False, 'error': str(e), 'stage': 'output'}
    
    print(f"\n✓ {config['name']} 完成 (耗时: {elapsed_time:.1f}秒)")
    print("="*100 + "\n")
    
    return {
        'success': True,
        'scenario_id': scenario_id,
        'elapsed_time': elapsed_time,
        'steady_analysis': steady_analysis,
        'stability_analysis': stability_analysis,
        'output_dir': output_dir,
    }


def main():
    """主函数"""
    print("\n" + "="*100)
    print("串联明渠闸泵群系统 - 增强版工况测试".center(100))
    print("="*100)
    print(f"\n开始时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"聚焦工况数: {len(FOCUSED_SCENARIOS)}")
    print("\n增强功能:")
    print("  - 动画中显示边界条件和控制条件的实时变化")
    print("  - 详细的初始恒定流状态分析")
    print("  - 深入的数值稳定性分析（CFL、质量守恒）")
    print("  - 更精细的网格和时间步长")
    print("\n" + "="*100)
    
    # 创建输出基础目录
    base_dir = os.path.dirname(os.path.abspath(__file__))
    output_base_dir = os.path.join(base_dir, "results_enhanced")
    os.makedirs(output_base_dir, exist_ok=True)
    
    # 运行所有工况
    results = []
    start_time_total = time.time()
    
    for i, (scenario_id, config) in enumerate(FOCUSED_SCENARIOS.items(), 1):
        print(f"\n进度: [{i}/{len(FOCUSED_SCENARIOS)}]")
        
        result = run_enhanced_scenario(scenario_id, config, output_base_dir)
        results.append(result)
        
        time.sleep(0.5)
    
    elapsed_total = time.time() - start_time_total
    
    # ==================== 生成总结 ====================
    print("\n" + "="*100)
    print("测试总结".center(100))
    print("="*100)
    
    n_success = sum(1 for r in results if r.get('success', False))
    n_failed = len(results) - n_success
    
    print(f"\n运行统计:")
    print(f"  总工况数: {len(results)}")
    print(f"  成功: {n_success}")
    print(f"  失败: {n_failed}")
    print(f"  总耗时: {elapsed_total:.1f}秒 ({elapsed_total/60:.1f}分钟)")
    
    if n_success > 0:
        print(f"\n物理正确性:")
        for result in results:
            if result.get('success'):
                scenario_id = result['scenario_id']
                name = FOCUSED_SCENARIOS[scenario_id]['name']
                mass_error = result['stability_analysis']['mass_balance_error']
                cfl_max = result['stability_analysis']['cfl_max']
                
                print(f"\n  {name}:")
                print(f"    质量平衡误差: {mass_error:.6f} ({'✓' if mass_error < 0.05 else '⚠'})")
                print(f"    最大CFL数: {cfl_max:.4f} ({'✓' if cfl_max < 1.0 else '⚠'})")
    
    print("\n" + "="*100)
    print("✓ 增强版测试完成！".center(100))
    print("="*100 + "\n")
    
    return results


if __name__ == "__main__":
    results = main()
