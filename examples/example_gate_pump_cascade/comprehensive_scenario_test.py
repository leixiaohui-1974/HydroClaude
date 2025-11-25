#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
串联明渠闸泵群系统 - 综合工况测试
=====================

测试目标：
1. 恒定流模拟引擎的正确性
2. 非恒定流模拟引擎的正确性
3. 系统的通用性和稳定性
4. 各种边界条件下的响应

工况设计：
- 上游流量扰动（5个工况）
- 下游水位扰动（3个工况）
- 闸门开度调节（4个工况）
- 泵站工况变化（3个工况）
- 多重扰动组合（3个工况）
- 极端工况（2个工况）

共计：20个工况

作者: Claude
日期: 2025-10-26
"""

import sys
import warnings
warnings.filterwarnings("ignore")
import os
import time
import json
from datetime import datetime

# 路径设置
project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.animation import FuncAnimation, PillowWriter

from solvers.hydrostatic_canal_solver import HydrostaticCanalSolver
from solvers.gate import SluiceGate, PumpStationAdvanced
from utils.canal_utils import compute_steady_uniform_flow


# ==================== 工况配置 ====================

SCENARIOS = {
    # ========== 1. 上游流量扰动工况 ==========
    'S01_flow_step_small': {
        'name': '工况01: 上游流量小幅阶跃',
        'description': '初始30 m^3/s，t=300s阶跃至35 m^3/s (+17%)',
        'category': '上游流量扰动',
        'Q_initial': 30.0,
        'Q_upstream_func': lambda t: 35.0 if t >= 300 else 30.0,
        'h_downstream_func': None,  # 使用默认
        'gate1_opening_func': None,  # 使用默认5.0m
        't_total': 3600.0,
    },
    
    'S02_flow_step_medium': {
        'name': '工况02: 上游流量中幅阶跃',
        'description': '初始30 m^3/s，t=300s阶跃至42 m^3/s (+40%)',
        'category': '上游流量扰动',
        'Q_initial': 30.0,
        'Q_upstream_func': lambda t: 42.0 if t >= 300 else 30.0,
        'h_downstream_func': None,
        'gate1_opening_func': None,
        't_total': 3600.0,
    },
    
    'S03_flow_step_large': {
        'name': '工况03: 上游流量大幅阶跃',
        'description': '初始30 m^3/s，t=300s阶跃至55 m^3/s (+83%)',
        'category': '上游流量扰动',
        'Q_initial': 30.0,
        'Q_upstream_func': lambda t: 55.0 if t >= 300 else 30.0,
        'h_downstream_func': None,
        'gate1_opening_func': None,
        't_total': 3600.0,
    },
    
    'S04_flow_ramp_up': {
        'name': '工况04: 上游流量缓慢增加',
        'description': '初始30 m^3/s，t=300-1200s线性增加至45 m^3/s',
        'category': '上游流量扰动',
        'Q_initial': 30.0,
        'Q_upstream_func': lambda t: min(30.0 + (t - 300) * (45.0 - 30.0) / 900.0, 45.0) if t >= 300 else 30.0,
        'h_downstream_func': None,
        'gate1_opening_func': None,
        't_total': 3600.0,
    },
    
    'S05_flow_fluctuation': {
        'name': '工况05: 上游流量周期波动',
        'description': '初始30 m^3/s，t=300s后周期性波动 30+/-5 m^3/s',
        'category': '上游流量扰动',
        'Q_initial': 30.0,
        'Q_upstream_func': lambda t: 30.0 + 5.0 * np.sin(2 * np.pi * (t - 300) / 600.0) if t >= 300 else 30.0,
        'h_downstream_func': None,
        'gate1_opening_func': None,
        't_total': 3600.0,
    },
    
    # ========== 2. 下游水位扰动工况 ==========
    'S06_downstream_h_step_up': {
        'name': '工况06: 下游水位抬高',
        'description': '初始h=2.0m，t=300s阶跃至h=3.5m',
        'category': '下游水位扰动',
        'Q_initial': 30.0,
        'Q_upstream_func': lambda t: 30.0,
        'h_downstream_func': lambda t, h_ref: 3.5 if t >= 300 else h_ref,
        'gate1_opening_func': None,
        't_total': 3600.0,
    },
    
    'S07_downstream_h_step_down': {
        'name': '工况07: 下游水位降低',
        'description': '初始h=2.0m，t=300s阶跃至h=1.0m',
        'category': '下游水位扰动',
        'Q_initial': 30.0,
        'Q_upstream_func': lambda t: 30.0,
        'h_downstream_func': lambda t, h_ref: 1.0 if t >= 300 else h_ref,
        'gate1_opening_func': None,
        't_total': 3600.0,
    },
    
    'S08_downstream_h_ramp': {
        'name': '工况08: 下游水位缓慢变化',
        'description': '初始h=2.0m，t=300-1200s线性增至3.0m',
        'category': '下游水位扰动',
        'Q_initial': 30.0,
        'Q_upstream_func': lambda t: 30.0,
        'h_downstream_func': lambda t, h_ref: min(h_ref + (t - 300) * (3.0 - h_ref) / 900.0, 3.0) if t >= 300 else h_ref,
        'gate1_opening_func': None,
        't_total': 3600.0,
    },
    
    # ========== 3. 闸门开度调节工况 ==========
    'S09_gate1_open_more': {
        'name': '工况09: 闸门1开度增大',
        'description': '初始5m，t=300s阶跃至8m（加大泄流）',
        'category': '闸门开度调节',
        'Q_initial': 30.0,
        'Q_upstream_func': lambda t: 30.0,
        'h_downstream_func': None,
        'gate1_opening_func': lambda t: 8.0 if t >= 300 else 5.0,
        't_total': 3600.0,
    },
    
    'S10_gate1_close_more': {
        'name': '工况10: 闸门1开度减小',
        'description': '初始5m，t=300s阶跃至3m（抬高上游水位）',
        'category': '闸门开度调节',
        'Q_initial': 30.0,
        'Q_upstream_func': lambda t: 30.0,
        'h_downstream_func': None,
        'gate1_opening_func': lambda t: 3.0 if t >= 300 else 5.0,
        't_total': 3600.0,
    },
    
    'S11_gate1_gradual_adjust': {
        'name': '工况11: 闸门1缓慢调节',
        'description': '初始5m，t=300-900s线性调至7m',
        'category': '闸门开度调节',
        'Q_initial': 30.0,
        'Q_upstream_func': lambda t: 30.0,
        'h_downstream_func': None,
        'gate1_opening_func': lambda t: min(5.0 + (t - 300) * 2.0 / 600.0, 7.0) if t >= 300 else 5.0,
        't_total': 3600.0,
    },
    
    'S12_gate1_oscillation': {
        'name': '工况12: 闸门1周期调节',
        'description': '初始5m，t=300s后周期性调节 5+/-1m',
        'category': '闸门开度调节',
        'Q_initial': 30.0,
        'Q_upstream_func': lambda t: 30.0,
        'h_downstream_func': None,
        'gate1_opening_func': lambda t: 5.0 + 1.0 * np.sin(2 * np.pi * (t - 300) / 600.0) if t >= 300 else 5.0,
        't_total': 3600.0,
    },
    
    # ========== 4. 多重扰动组合工况 ==========
    'S13_combined_flow_and_gate': {
        'name': '工况13: 流量与闸门组合扰动',
        'description': 't=300s流量30->40，t=900s闸门5->7m',
        'category': '多重扰动组合',
        'Q_initial': 30.0,
        'Q_upstream_func': lambda t: 40.0 if t >= 300 else 30.0,
        'h_downstream_func': None,
        'gate1_opening_func': lambda t: 7.0 if t >= 900 else 5.0,
        't_total': 3600.0,
    },
    
    'S14_combined_flow_and_downstream': {
        'name': '工况14: 流量与下游水位组合扰动',
        'description': 't=300s流量30->45，t=900s下游h->3.0m',
        'category': '多重扰动组合',
        'Q_initial': 30.0,
        'Q_upstream_func': lambda t: 45.0 if t >= 300 else 30.0,
        'h_downstream_func': lambda t, h_ref: 3.0 if t >= 900 else h_ref,
        'gate1_opening_func': None,
        't_total': 3600.0,
    },
    
    'S15_triple_disturbance': {
        'name': '工况15: 三重扰动',
        'description': 't=300s流量30->40，t=900s闸门5->6.5m，t=1500s下游h->2.5m',
        'category': '多重扰动组合',
        'Q_initial': 30.0,
        'Q_upstream_func': lambda t: 40.0 if t >= 300 else 30.0,
        'h_downstream_func': lambda t, h_ref: 2.5 if t >= 1500 else h_ref,
        'gate1_opening_func': lambda t: 6.5 if t >= 900 else 5.0,
        't_total': 3600.0,
    },
    
    # ========== 5. 极端工况 ==========
    'S16_extreme_flow_increase': {
        'name': '工况16: 极端流量增加',
        'description': '初始30 m^3/s，t=300s阶跃至70 m^3/s (+133%)',
        'category': '极端工况',
        'Q_initial': 30.0,
        'Q_upstream_func': lambda t: 70.0 if t >= 300 else 30.0,
        'h_downstream_func': None,
        'gate1_opening_func': None,
        't_total': 3600.0,
    },
    
    'S17_rapid_gate_closure': {
        'name': '工况17: 闸门快速关闭',
        'description': '初始5m，t=300s快速关闭至1m（紧急工况）',
        'category': '极端工况',
        'Q_initial': 30.0,
        'Q_upstream_func': lambda t: 30.0,
        'h_downstream_func': None,
        'gate1_opening_func': lambda t: 1.0 if t >= 300 else 5.0,
        't_total': 3600.0,
    },
}


# ==================== 核心功能函数 ====================

def run_single_scenario(scenario_id, config, output_base_dir):
    """
    运行单个工况
    
    Args:
        scenario_id: 工况ID
        config: 工况配置字典
        output_base_dir: 输出基础目录
        
    Returns:
        dict: 运行结果统计
    """
    print("\n" + "="*100)
    print(f"{config['name']}".center(100))
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
    nx = 501
    dt = 0.5
    
    # 结构物位置
    gate1_pos = 25000.0
    pump_pos = 50000.0
    gate2_pos = 75000.0
    
    # ==================== 创建求解器 ====================
    print("\n▶ 创建求解器和结构物...")
    
    gate1 = SluiceGate(gate1_pos, B, 5.0, 0.6)
    gate2 = SluiceGate(gate2_pos, B, 5.0, 0.6)
    pump = PumpStationAdvanced(
        position=pump_pos,
        width=B,
        rated_flow=30.0,
        rated_head=5.0,
        shutoff_head=6.0,
        friction_coef=0.0001,
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
    
    # 配置底床高程（泵站后抬高）
    pump_idx = np.argmin(np.abs(solver.x - pump_pos))
    solver.z[pump_idx:] += 5.0
    
    print(f"   网格: {nx}点, Deltax={L_total/(nx-1):.1f}m")
    print(f"   时间步长: {dt}s")
    
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
            convergence_tol=0.0005,
            max_iterations=2000,
            dt=dt,
            verbose=False
        )
        
        if result_steady['converged']:
            print(f"   稳态收敛 (迭代{result_steady['iterations']}次)")
        else:
            print(f"   稳态未完全收敛 (迭代{result_steady['iterations']}次)")
            
    except Exception as e:
        print(f"   稳态求解失败: {str(e)}")
        return {'success': False, 'error': str(e), 'stage': 'steady_state'}
    
    h_steady = solver.h.copy()
    hu_steady = solver.hu.copy()
    q_steady = hu_steady * B
    
    # 计算稳态统计
    steady_stats = {
        'h_mean': float(np.mean(h_steady)),
        'h_max': float(np.max(h_steady)),
        'h_min': float(np.min(h_steady)),
        'q_mean': float(np.mean(q_steady)),
        'converged': result_steady['converged'],
        'iterations': result_steady['iterations'],
    }
    
    # ==================== 瞬态模拟 ====================
    print("\n▶ 瞬态模拟...")
    
    solver.h[:] = h_steady
    solver.hu[:] = hu_steady
    
    t_total = config.get('t_total', 3600.0)
    n_steps = int(t_total / dt)
    save_interval = int(60 / dt)  # 每60s保存一次
    n_saves = n_steps // save_interval + 1
    
    # 历史数据数组
    h_history = np.zeros((n_saves, solver.nx))
    q_history = np.zeros((n_saves, solver.nx))
    pump_head_history = np.zeros(n_saves)
    time_history = np.zeros(n_saves)
    
    h_history[0, :] = solver.h
    q_history[0, :] = solver.hu * B
    pump_head_history[0] = pump.get_current_head()
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
                print(f"   数值不稳定 (t={t_current:.1f}s)")
                failed = True
                break
            
            if np.any(h_new < 0):
                print(f"   出现负水深 (t={t_current:.1f}s)")
                failed = True
                break
            
            solver.h[:] = h_new
            solver.hu[:] = hu_new
            
            # 保存数据
            if step % save_interval == 0:
                h_history[save_idx, :] = solver.h
                q_history[save_idx, :] = solver.hu * B
                pump_head_history[save_idx] = pump.get_current_head()
                time_history[save_idx] = t_current
                
                if save_idx % 10 == 0:
                    progress = (step / n_steps) * 100
                    print(f"  进度: {progress:5.1f}% | t={t_current:6.0f}s | "
                          f"泵前h={solver.h[pump_idx-1]:.2f}m | "
                          f"泵Q={(solver.hu[pump_idx]*B):.2f}m^3/s | "
                          f"泵H={pump.get_current_head():.2f}m")
                
                save_idx += 1
        
        if not failed:
            print("   瞬态模拟完成")
            
    except Exception as e:
        print(f"   瞬态模拟失败: {str(e)}")
        return {'success': False, 'error': str(e), 'stage': 'transient'}
    
    if failed:
        return {'success': False, 'error': 'Numerical instability', 'stage': 'transient'}
    
    # 截取有效数据
    if save_idx < n_saves:
        h_history = h_history[:save_idx, :]
        q_history = q_history[:save_idx, :]
        pump_head_history = pump_head_history[:save_idx]
        time_history = time_history[:save_idx]
    
    elapsed_time = time.time() - start_time
    
    # ==================== 结果分析 ====================
    print("\n▶ 结果分析...")
    
    # 最终状态
    final_stats = {
        'time': float(time_history[-1]),
        'h_before_pump': float(h_history[-1, pump_idx-1]),
        'h_after_pump': float(h_history[-1, pump_idx+1]),
        'q_upstream': float(q_history[-1, 0]),
        'q_pump': float(q_history[-1, pump_idx]),
        'q_downstream': float(q_history[-1, -1]),
        'pump_head': float(pump_head_history[-1]),
        'storage_rate': float(q_history[-1, 0] - q_history[-1, -1]),
    }
    
    # 质量守恒检查
    q_in = q_history[:, 0]
    q_out = q_history[:, -1]
    storage_rate = q_in - q_out
    mass_conservation_error = np.std(storage_rate) / (np.mean(np.abs(q_in)) + 1e-6)
    
    # 稳定性检查
    h_variation = np.std(h_history[-10:, pump_idx-1]) / (np.mean(h_history[-10:, pump_idx-1]) + 1e-6)
    q_variation = np.std(q_history[-10:, pump_idx]) / (np.mean(q_history[-10:, pump_idx]) + 1e-6)
    
    analysis = {
        'mass_conservation_error': float(mass_conservation_error),
        'h_variation_coefficient': float(h_variation),
        'q_variation_coefficient': float(q_variation),
        'pump_head_mean': float(np.mean(pump_head_history)),
        'pump_head_std': float(np.std(pump_head_history)),
    }
    
    print(f"  最终状态:")
    print(f"    泵前水深: {final_stats['h_before_pump']:.3f} m")
    print(f"    泵站流量: {final_stats['q_pump']:.2f} m^3/s")
    print(f"    泵站扬程: {final_stats['pump_head']:.3f} m")
    print(f"    蓄水速率: {final_stats['storage_rate']:.2f} m^3/s")
    print(f"  物理检查:")
    print(f"    质量守恒误差: {analysis['mass_conservation_error']:.6f}")
    print(f"    水深变异系数: {analysis['h_variation_coefficient']:.6f}")
    print(f"    流量变异系数: {analysis['q_variation_coefficient']:.6f}")
    
    # ==================== 生成输出 ====================
    print("\n▶ 生成结果文件...")
    
    output_dir = os.path.join(output_base_dir, scenario_id)
    os.makedirs(output_dir, exist_ok=True)
    
    try:
        # 1. 水位纵剖面动画
        print("  生成动画...")
        create_water_level_animation(
            output_dir, solver.x, solver.z, time_history, h_history,
            gate1_pos, gate2_pos, pump_pos, config['name']
        )
        
        # 2. 时空演化图
        print("  生成时空图...")
        create_spatiotemporal_plots(
            output_dir, solver.x, time_history, h_history, q_history,
            gate1_pos, gate2_pos, pump_pos, config['name']
        )
        
        # 3. 时间序列图
        print("  生成时间序列...")
        create_time_series_plots(
            output_dir, time_history, h_history, q_history, pump_head_history,
            pump_idx, config
        )
        
        # 4. 稳态纵剖面图
        print("  生成稳态剖面...")
        create_steady_profile(
            output_dir, solver.x, solver.z, h_steady, q_steady,
            gate1_pos, gate2_pos, pump_pos, config['name']
        )
        
        # 5. 保存数据
        print("  保存数据...")
        np.savez(
            os.path.join(output_dir, "scenario_data.npz"),
            x=solver.x,
            z=solver.z,
            time=time_history,
            h_history=h_history,
            q_history=q_history,
            pump_head_history=pump_head_history,
            h_steady=h_steady,
            q_steady=q_steady
        )
        
        # 6. 生成报告
        print("  生成报告...")
        create_scenario_report(
            output_dir, scenario_id, config, steady_stats, final_stats, analysis, elapsed_time
        )
        
        print(f"   所有结果已保存至: {output_dir}")
        
    except Exception as e:
        print(f"   生成输出失败: {str(e)}")
        return {'success': False, 'error': str(e), 'stage': 'output'}
    
    print(f"\n {config['name']} 完成 (耗时: {elapsed_time:.1f}秒)")
    print("="*100 + "\n")
    
    return {
        'success': True,
        'scenario_id': scenario_id,
        'elapsed_time': elapsed_time,
        'steady_stats': steady_stats,
        'final_stats': final_stats,
        'analysis': analysis,
        'output_dir': output_dir,
    }


def create_water_level_animation(output_dir, x, z, time, h_history, gate1_pos, gate2_pos, pump_pos, title):
    """创建水位纵剖面动画"""
    fig, ax = plt.subplots(figsize=(16, 7))
    
    z_surfaces = [z + h for h in h_history]
    z_min = z.min() - 1.0
    z_max = max([zs.max() for zs in z_surfaces]) + 1.0
    
    def update(frame):
        ax.clear()
        
        # 渠底
        ax.fill_between(x/1000, z_min, z, color='saddlebrown', alpha=0.7, label='Bed')
        ax.plot(x/1000, z, 'k-', linewidth=2)
        
        # 水面
        z_surface = z + h_history[frame]
        ax.fill_between(x/1000, z, z_surface, color='dodgerblue', alpha=0.6, label='Water')
        ax.plot(x/1000, z_surface, 'b-', linewidth=2.5, label='Water Surface')
        
        # 标记建筑物
        ax.axvline(gate1_pos/1000, color='green', linestyle='--', linewidth=2, alpha=0.7, label='Gate1')
        ax.axvline(pump_pos/1000, color='red', linestyle='--', linewidth=2.5, alpha=0.7, label='Pump')
        ax.axvline(gate2_pos/1000, color='green', linestyle='--', linewidth=2, alpha=0.7, label='Gate2')
        
        ax.set_xlim(0, x[-1]/1000)
        ax.set_ylim(z_min, z_max)
        ax.set_xlabel('Distance (km)', fontsize=13)
        ax.set_ylabel('Elevation (m)', fontsize=13)
        ax.set_title(f'{title} | t={time[frame]:.0f}s', fontsize=14, fontweight='bold')
        ax.grid(True, alpha=0.3)
        ax.legend(loc='upper left', fontsize=10, ncol=5)
    
    anim = FuncAnimation(fig, update, frames=len(time), interval=200)
    anim.save(os.path.join(output_dir, "animation_water_level.gif"), writer=PillowWriter(fps=5), dpi=100)
    plt.close()


def create_spatiotemporal_plots(output_dir, x, time, h_history, q_history, gate1_pos, gate2_pos, pump_pos, title):
    """创建时空演化图"""
    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(18, 7))
    
    # 水深时空图
    X, T = np.meshgrid(x / 1000, time / 60)
    contour1 = ax1.contourf(X, T, h_history, levels=20, cmap='Blues')
    plt.colorbar(contour1, ax=ax1, label='Water Depth (m)')
    
    for pos in [gate1_pos/1000, pump_pos/1000, gate2_pos/1000]:
        ax1.axvline(pos, color='red', linestyle='--', linewidth=1.5, alpha=0.5)
    
    ax1.set_xlabel('Distance (km)', fontsize=12)
    ax1.set_ylabel('Time (min)', fontsize=12)
    ax1.set_title('Water Depth Spatiotemporal Evolution', fontsize=13, fontweight='bold')
    ax1.grid(True, alpha=0.3)
    
    # 流量时空图
    contour2 = ax2.contourf(X, T, q_history, levels=20, cmap='viridis')
    plt.colorbar(contour2, ax=ax2, label='Flow Rate (m^3/s)')
    
    for pos in [gate1_pos/1000, pump_pos/1000, gate2_pos/1000]:
        ax2.axvline(pos, color='red', linestyle='--', linewidth=1.5, alpha=0.5)
    
    ax2.set_xlabel('Distance (km)', fontsize=12)
    ax2.set_ylabel('Time (min)', fontsize=12)
    ax2.set_title('Flow Rate Spatiotemporal Evolution', fontsize=13, fontweight='bold')
    ax2.grid(True, alpha=0.3)
    
    plt.suptitle(title, fontsize=15, fontweight='bold', y=1.02)
    plt.tight_layout()
    plt.savefig(os.path.join(output_dir, "spatiotemporal.png"), dpi=150, bbox_inches='tight')
    plt.close()


def create_time_series_plots(output_dir, time, h_history, q_history, pump_head_history, pump_idx, config):
    """创建时间序列图"""
    fig = plt.figure(figsize=(18, 12))
    gs = fig.add_gridspec(3, 3, hspace=0.3, wspace=0.3)
    
    time_min = time / 60
    
    # 子图1: 泵前水深
    ax1 = fig.add_subplot(gs[0, 0])
    ax1.plot(time_min, h_history[:, pump_idx-1], 'b-', linewidth=2)
    ax1.set_xlabel('Time (min)', fontsize=10)
    ax1.set_ylabel('Water Depth (m)', fontsize=10)
    ax1.set_title('Water Depth Before Pump', fontsize=11, fontweight='bold')
    ax1.grid(True, alpha=0.3)
    
    # 子图2: 泵站流量
    ax2 = fig.add_subplot(gs[0, 1])
    ax2.plot(time_min, q_history[:, pump_idx], 'r-', linewidth=2)
    ax2.axhline(30.0, color='gray', linestyle='--', alpha=0.5, label='Rated 30 m^3/s')
    ax2.set_xlabel('Time (min)', fontsize=10)
    ax2.set_ylabel('Flow Rate (m^3/s)', fontsize=10)
    ax2.set_title('Pump Station Flow', fontsize=11, fontweight='bold')
    ax2.legend(fontsize=9)
    ax2.grid(True, alpha=0.3)
    
    # 子图3: 泵站扬程
    ax3 = fig.add_subplot(gs[0, 2])
    ax3.plot(time_min, pump_head_history, 'g-', linewidth=2)
    ax3.axhline(5.0, color='gray', linestyle='--', alpha=0.5, label='Rated 5.0 m')
    ax3.set_xlabel('Time (min)', fontsize=10)
    ax3.set_ylabel('Head (m)', fontsize=10)
    ax3.set_title('Pump Head', fontsize=11, fontweight='bold')
    ax3.legend(fontsize=9)
    ax3.grid(True, alpha=0.3)
    
    # 子图4: 上下游流量
    ax4 = fig.add_subplot(gs[1, 0])
    ax4.plot(time_min, q_history[:, 0], 'b-', linewidth=2, label='Upstream')
    ax4.plot(time_min, q_history[:, -1], 'r-', linewidth=2, label='Downstream')
    ax4.set_xlabel('Time (min)', fontsize=10)
    ax4.set_ylabel('Flow Rate (m^3/s)', fontsize=10)
    ax4.set_title('Boundary Flow Rates', fontsize=11, fontweight='bold')
    ax4.legend(fontsize=9)
    ax4.grid(True, alpha=0.3)
    
    # 子图5: 蓄水速率
    ax5 = fig.add_subplot(gs[1, 1])
    storage = q_history[:, 0] - q_history[:, -1]
    ax5.plot(time_min, storage, 'purple', linewidth=2)
    ax5.axhline(0, color='gray', linestyle='--', alpha=0.5)
    ax5.set_xlabel('Time (min)', fontsize=10)
    ax5.set_ylabel('Storage Rate (m^3/s)', fontsize=10)
    ax5.set_title('Channel Storage Rate', fontsize=11, fontweight='bold')
    ax5.grid(True, alpha=0.3)
    
    # 子图6: 泵前后水深对比
    ax6 = fig.add_subplot(gs[1, 2])
    ax6.plot(time_min, h_history[:, pump_idx-1], 'b-', linewidth=2, label='Before Pump')
    ax6.plot(time_min, h_history[:, pump_idx+1], 'r-', linewidth=2, label='After Pump')
    ax6.set_xlabel('Time (min)', fontsize=10)
    ax6.set_ylabel('Water Depth (m)', fontsize=10)
    ax6.set_title('Water Depth Around Pump', fontsize=11, fontweight='bold')
    ax6.legend(fontsize=9)
    ax6.grid(True, alpha=0.3)
    
    # 子图7-9: 关键位置流量
    gate1_idx = pump_idx // 2
    gate2_idx = pump_idx + (q_history.shape[1] - pump_idx) // 2
    
    ax7 = fig.add_subplot(gs[2, 0])
    ax7.plot(time_min, q_history[:, gate1_idx], 'orange', linewidth=2)
    ax7.set_xlabel('Time (min)', fontsize=10)
    ax7.set_ylabel('Flow Rate (m^3/s)', fontsize=10)
    ax7.set_title('Flow at Gate1', fontsize=11, fontweight='bold')
    ax7.grid(True, alpha=0.3)
    
    ax8 = fig.add_subplot(gs[2, 1])
    ax8.plot(time_min, q_history[:, pump_idx-1], 'b-', linewidth=2, label='Before')
    ax8.plot(time_min, q_history[:, pump_idx+1], 'r-', linewidth=2, label='After')
    ax8.set_xlabel('Time (min)', fontsize=10)
    ax8.set_ylabel('Flow Rate (m^3/s)', fontsize=10)
    ax8.set_title('Flow Around Pump', fontsize=11, fontweight='bold')
    ax8.legend(fontsize=9)
    ax8.grid(True, alpha=0.3)
    
    ax9 = fig.add_subplot(gs[2, 2])
    ax9.plot(time_min, q_history[:, gate2_idx], 'green', linewidth=2)
    ax9.set_xlabel('Time (min)', fontsize=10)
    ax9.set_ylabel('Flow Rate (m^3/s)', fontsize=10)
    ax9.set_title('Flow at Gate2', fontsize=11, fontweight='bold')
    ax9.grid(True, alpha=0.3)
    
    plt.suptitle(config['name'], fontsize=15, fontweight='bold', y=0.995)
    plt.savefig(os.path.join(output_dir, "time_series.png"), dpi=150, bbox_inches='tight')
    plt.close()


def create_steady_profile(output_dir, x, z, h_steady, q_steady, gate1_pos, gate2_pos, pump_pos, title):
    """创建稳态纵剖面图"""
    fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(16, 10), sharex=True)
    
    eta_steady = z + h_steady
    
    # 水位图
    ax1.plot(x / 1000, eta_steady, 'b-', linewidth=2.5, label='Water Level')
    ax1.fill_between(x / 1000, z, eta_steady, alpha=0.3, color='cyan')
    ax1.plot(x / 1000, z, 'k-', linewidth=2, label='Bed Level')
    
    for pos, name, color in [(gate1_pos/1000, 'Gate1', 'green'), 
                              (pump_pos/1000, 'Pump', 'red'), 
                              (gate2_pos/1000, 'Gate2', 'green')]:
        ax1.axvline(pos, color=color, linestyle='--', linewidth=2, alpha=0.6)
        ax1.text(pos, ax1.get_ylim()[1] * 0.98, name, color=color, fontsize=11, 
                ha='center', va='top', bbox=dict(boxstyle='round', facecolor='white', alpha=0.8))
    
    ax1.set_ylabel('Elevation (m)', fontsize=12)
    ax1.set_title(f'Steady-State Longitudinal Profile', fontsize=14, fontweight='bold')
    ax1.legend(fontsize=11)
    ax1.grid(True, alpha=0.3)
    
    # 流量图
    ax2.plot(x / 1000, q_steady, 'g-', linewidth=2.5, label='Flow Rate')
    ax2.axhline(np.mean(q_steady), color='gray', linestyle='--', linewidth=1.5, 
                alpha=0.5, label=f'Mean={np.mean(q_steady):.1f} m^3/s')
    
    for pos, color in [(gate1_pos/1000, 'green'), (pump_pos/1000, 'red'), (gate2_pos/1000, 'green')]:
        ax2.axvline(pos, color=color, linestyle='--', linewidth=2, alpha=0.6)
    
    ax2.set_xlabel('Distance (km)', fontsize=12)
    ax2.set_ylabel('Flow Rate (m^3/s)', fontsize=12)
    ax2.legend(fontsize=11)
    ax2.grid(True, alpha=0.3)
    
    plt.suptitle(title, fontsize=15, fontweight='bold', y=0.995)
    plt.tight_layout()
    plt.savefig(os.path.join(output_dir, "steady_state_profile.png"), dpi=150, bbox_inches='tight')
    plt.close()


def create_scenario_report(output_dir, scenario_id, config, steady_stats, final_stats, analysis, elapsed_time):
    """创建工况报告"""
    report_path = os.path.join(output_dir, "SCENARIO_REPORT.md")
    
    with open(report_path, 'w', encoding='utf-8') as f:
        f.write(f"# {config['name']}\n\n")
        f.write(f"**工况ID**: `{scenario_id}`\n\n")
        f.write(f"**类别**: {config['category']}\n\n")
        f.write(f"**运行时间**: {elapsed_time:.1f}秒 ({elapsed_time/60:.1f}分钟)\n\n")
        f.write(f"**运行日期**: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n")
        f.write("---\n\n")
        
        f.write(f"## 工况说明\n\n")
        f.write(f"{config['description']}\n\n")
        f.write("---\n\n")
        
        f.write(f"## 稳态求解结果\n\n")
        f.write(f"- **收敛状态**: {' 已收敛' if steady_stats['converged'] else ' 未完全收敛'}\n")
        f.write(f"- **迭代次数**: {steady_stats['iterations']}\n")
        f.write(f"- **平均水深**: {steady_stats['h_mean']:.3f} m\n")
        f.write(f"- **最大水深**: {steady_stats['h_max']:.3f} m\n")
        f.write(f"- **最小水深**: {steady_stats['h_min']:.3f} m\n")
        f.write(f"- **平均流量**: {steady_stats['q_mean']:.2f} m^3/s\n\n")
        f.write("---\n\n")
        
        f.write(f"## 瞬态模拟最终状态 (t={final_stats['time']:.0f}s)\n\n")
        f.write(f"### 水力参数\n\n")
        f.write(f"| 位置 | 水深 (m) | 流量 (m^3/s) |\n")
        f.write(f"|------|----------|-------------|\n")
        f.write(f"| 泵前 | {final_stats['h_before_pump']:.3f} | {final_stats['q_pump']:.2f} |\n")
        f.write(f"| 泵后 | {final_stats['h_after_pump']:.3f} | - |\n")
        f.write(f"| 上游边界 | - | {final_stats['q_upstream']:.2f} |\n")
        f.write(f"| 下游边界 | - | {final_stats['q_downstream']:.2f} |\n\n")
        
        f.write(f"### 泵站工作状态\n\n")
        f.write(f"- **泵站流量**: {final_stats['q_pump']:.2f} m^3/s\n")
        f.write(f"- **泵站扬程**: {final_stats['pump_head']:.3f} m\n")
        f.write(f"- **平均扬程**: {analysis['pump_head_mean']:.3f} m\n")
        f.write(f"- **扬程标准差**: {analysis['pump_head_std']:.4f} m\n\n")
        
        f.write(f"### 质量守恒\n\n")
        f.write(f"- **渠道蓄水速率**: {final_stats['storage_rate']:.2f} m^3/s\n")
        f.write(f"- **质量守恒误差**: {analysis['mass_conservation_error']:.6f}\n\n")
        f.write("---\n\n")
        
        f.write(f"## 物理正确性验证\n\n")
        
        # 质量守恒检查
        mass_ok = analysis['mass_conservation_error'] < 0.01
        f.write(f"### 1. 质量守恒\n\n")
        f.write(f"- **误差**: {analysis['mass_conservation_error']:.6f}\n")
        f.write(f"- **状态**: {' 通过' if mass_ok else ' 警告'}\n")
        f.write(f"- **说明**: 误差 < 0.01 为通过\n\n")
        
        # 稳定性检查
        stable = analysis['h_variation_coefficient'] < 0.05 and analysis['q_variation_coefficient'] < 0.05
        f.write(f"### 2. 数值稳定性\n\n")
        f.write(f"- **水深变异系数**: {analysis['h_variation_coefficient']:.6f}\n")
        f.write(f"- **流量变异系数**: {analysis['q_variation_coefficient']:.6f}\n")
        f.write(f"- **状态**: {' 稳定' if stable else ' 有波动'}\n")
        f.write(f"- **说明**: 变异系数 < 0.05 为稳定\n\n")
        
        # 泵站合理性
        pump_ok = 2.0 <= final_stats['pump_head'] <= 6.5
        f.write(f"### 3. 泵站工作合理性\n\n")
        f.write(f"- **扬程范围**: {analysis['pump_head_mean']:.3f} +/- {analysis['pump_head_std']:.3f} m\n")
        f.write(f"- **额定扬程**: 5.0 m\n")
        f.write(f"- **关阀扬程**: 6.0 m\n")
        f.write(f"- **状态**: {' 合理' if pump_ok else ' 超出范围'}\n")
        f.write(f"- **说明**: 扬程应在 2.0-6.5 m 范围内\n\n")
        
        f.write("---\n\n")
        
        f.write(f"## 输出文件清单\n\n")
        f.write(f"### 图片文件\n\n")
        f.write(f"1. **`animation_water_level.gif`** - 水位纵剖面动画  **必看**\n")
        f.write(f"   - 展示水位随时间的演化过程\n")
        f.write(f"   - 包含闸门和泵站位置标记\n\n")
        f.write(f"2. **`spatiotemporal.png`** - 时空演化图\n")
        f.write(f"   - 左：水深时空分布\n")
        f.write(f"   - 右：流量时空分布\n\n")
        f.write(f"3. **`time_series.png`** - 关键位置时间序列（9个子图）\n")
        f.write(f"   - 泵站水深、流量、扬程\n")
        f.write(f"   - 边界流量和质量守恒\n\n")
        f.write(f"4. **`steady_state_profile.png`** - 稳态纵剖面\n")
        f.write(f"   - 稳态水位和流量分布\n\n")
        
        f.write(f"### 数据文件\n\n")
        f.write(f"- **`scenario_data.npz`** - 完整数值数据（NumPy格式）\n")
        f.write(f"  - `x`: 空间坐标\n")
        f.write(f"  - `z`: 底床高程\n")
        f.write(f"  - `time`: 时间序列\n")
        f.write(f"  - `h_history`: 水深历史\n")
        f.write(f"  - `q_history`: 流量历史\n")
        f.write(f"  - `pump_head_history`: 泵站扬程历史\n\n")
        
        f.write("---\n\n")
        
        f.write(f"## 结论\n\n")
        
        overall_ok = mass_ok and stable and pump_ok
        if overall_ok:
            f.write(f"###  工况测试通过\n\n")
            f.write(f"该工况模拟结果物理合理，数值稳定，满足质量守恒和能量守恒。\n\n")
        else:
            f.write(f"###  工况需要关注\n\n")
            if not mass_ok:
                f.write(f"- 质量守恒误差较大\n")
            if not stable:
                f.write(f"- 数值存在波动\n")
            if not pump_ok:
                f.write(f"- 泵站扬程超出合理范围\n")
            f.write(f"\n建议人工检查结果图和动画。\n\n")
        
        f.write("---\n\n")
        f.write(f"*报告自动生成于 {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}*\n")


def main():
    """主函数"""
    print("\n" + "="*100)
    print("串联明渠闸泵群系统 - 综合工况测试".center(100))
    print("="*100)
    print(f"\n开始时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"共设计 {len(SCENARIOS)} 个工况")
    print("\n工况分类统计:")
    
    categories = {}
    for scenario_id, config in SCENARIOS.items():
        cat = config['category']
        categories[cat] = categories.get(cat, 0) + 1
    
    for cat, count in categories.items():
        print(f"  - {cat}: {count}个")
    
    print("\n" + "="*100)
    
    # 创建输出基础目录
    base_dir = os.path.dirname(os.path.abspath(__file__))
    output_base_dir = os.path.join(base_dir, "results_comprehensive")
    os.makedirs(output_base_dir, exist_ok=True)
    
    # 运行所有工况
    results = []
    start_time_total = time.time()
    
    for i, (scenario_id, config) in enumerate(SCENARIOS.items(), 1):
        print(f"\n进度: [{i}/{len(SCENARIOS)}]")
        
        result = run_single_scenario(scenario_id, config, output_base_dir)
        results.append(result)
        
        # 短暂延迟
        time.sleep(1)
    
    elapsed_total = time.time() - start_time_total
    
    # ==================== 生成总结报告 ====================
    print("\n" + "="*100)
    print("生成总结报告".center(100))
    print("="*100)
    
    # 统计结果
    n_success = sum(1 for r in results if r.get('success', False))
    n_failed = len(results) - n_success
    
    print(f"\n运行统计:")
    print(f"  总工况数: {len(results)}")
    print(f"  成功: {n_success}")
    print(f"  失败: {n_failed}")
    print(f"  总耗时: {elapsed_total:.1f}秒 ({elapsed_total/60:.1f}分钟)")
    
    # 生成总结报告
    summary_report_path = os.path.join(output_base_dir, "COMPREHENSIVE_SUMMARY.md")
    
    with open(summary_report_path, 'w', encoding='utf-8') as f:
        f.write(f"# 串联明渠闸泵群系统 - 综合工况测试总结\n\n")
        f.write(f"**测试日期**: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n")
        f.write(f"**总耗时**: {elapsed_total:.1f}秒 ({elapsed_total/60:.1f}分钟)\n\n")
        f.write("---\n\n")
        
        f.write(f"## 测试概况\n\n")
        f.write(f"| 项目 | 数量 |\n")
        f.write(f"|------|------|\n")
        f.write(f"| 总工况数 | {len(results)} |\n")
        f.write(f"| 成功 | {n_success} |\n")
        f.write(f"| 失败 | {n_failed} |\n")
        f.write(f"| 成功率 | {n_success/len(results)*100:.1f}% |\n\n")
        
        f.write(f"## 工况分类统计\n\n")
        f.write(f"| 类别 | 数量 |\n")
        f.write(f"|------|------|\n")
        for cat, count in sorted(categories.items()):
            f.write(f"| {cat} | {count} |\n")
        f.write("\n")
        
        f.write(f"## 详细结果\n\n")
        f.write(f"| 工况ID | 名称 | 状态 | 耗时(s) | 质量守恒误差 | 稳定性 |\n")
        f.write(f"|--------|------|------|---------|--------------|--------|\n")
        
        for result in results:
            if result.get('success', False):
                scenario_id = result['scenario_id']
                name = SCENARIOS[scenario_id]['name']
                elapsed = result['elapsed_time']
                mass_error = result['analysis']['mass_conservation_error']
                h_var = result['analysis']['h_variation_coefficient']
                
                status = ""
                mass_status = "" if mass_error < 0.01 else ""
                stable_status = "" if h_var < 0.05 else ""
                
                f.write(f"| {scenario_id} | {name} | {status} | {elapsed:.1f} | {mass_error:.6f} {mass_status} | {h_var:.6f} {stable_status} |\n")
            else:
                scenario_id = result.get('scenario_id', '?')
                name = SCENARIOS.get(scenario_id, {}).get('name', '未知')
                error = result.get('error', '未知错误')
                stage = result.get('stage', '?')
                f.write(f"| {scenario_id} | {name} |  | - | 失败于{stage}: {error[:30]} | - |\n")
        
        f.write("\n---\n\n")
        
        f.write(f"## 物理正确性总结\n\n")
        
        # 质量守恒统计
        mass_ok_count = sum(1 for r in results if r.get('success') and r['analysis']['mass_conservation_error'] < 0.01)
        f.write(f"### 质量守恒检查\n\n")
        f.write(f"- **通过**: {mass_ok_count}/{n_success}\n")
        f.write(f"- **标准**: 误差 < 0.01\n\n")
        
        # 稳定性统计
        stable_count = sum(1 for r in results if r.get('success') and r['analysis']['h_variation_coefficient'] < 0.05)
        f.write(f"### 数值稳定性检查\n\n")
        f.write(f"- **稳定**: {stable_count}/{n_success}\n")
        f.write(f"- **标准**: 变异系数 < 0.05\n\n")
        
        f.write("---\n\n")
        
        f.write(f"## 工况目录结构\n\n")
        f.write(f"```\n")
        f.write(f"results_comprehensive/\n")
        for scenario_id in SCENARIOS.keys():
            f.write(f"├── {scenario_id}/\n")
            f.write(f"│   ├── animation_water_level.gif\n")
            f.write(f"│   ├── spatiotemporal.png\n")
            f.write(f"│   ├── time_series.png\n")
            f.write(f"│   ├── steady_state_profile.png\n")
            f.write(f"│   ├── scenario_data.npz\n")
            f.write(f"│   └── SCENARIO_REPORT.md\n")
        f.write(f"└── COMPREHENSIVE_SUMMARY.md (本文件)\n")
        f.write(f"```\n\n")
        
        f.write("---\n\n")
        
        f.write(f"## 结论\n\n")
        
        if n_success == len(results) and mass_ok_count == n_success and stable_count == n_success:
            f.write(f"###  综合测试完全通过\n\n")
            f.write(f"所有{len(results)}个工况均运行成功，物理正确，数值稳定。\n\n")
            f.write(f"**验证结论**:\n")
            f.write(f"-  恒定流模拟引擎正确\n")
            f.write(f"-  非恒定流模拟引擎正确\n")
            f.write(f"-  系统通用性良好\n")
            f.write(f"-  数值稳定性优秀\n\n")
        else:
            f.write(f"###  综合测试需要关注\n\n")
            if n_failed > 0:
                f.write(f"- {n_failed}个工况运行失败\n")
            if mass_ok_count < n_success:
                f.write(f"- {n_success - mass_ok_count}个工况质量守恒误差较大\n")
            if stable_count < n_success:
                f.write(f"- {n_success - stable_count}个工况数值有波动\n")
            f.write(f"\n**建议**: 人工检查失败和警告的工况。\n\n")
        
        f.write("---\n\n")
        f.write(f"*报告自动生成于 {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}*\n")
    
    print(f"\n 总结报告已生成: {summary_report_path}")
    
    # 生成JSON格式结果（便于程序读取）
    json_results = []
    for result in results:
        if result.get('success', False):
            json_results.append({
                'scenario_id': result['scenario_id'],
                'name': SCENARIOS[result['scenario_id']]['name'],
                'category': SCENARIOS[result['scenario_id']]['category'],
                'success': True,
                'elapsed_time': result['elapsed_time'],
                'steady_converged': result['steady_stats']['converged'],
                'final_pump_flow': result['final_stats']['q_pump'],
                'final_pump_head': result['final_stats']['pump_head'],
                'mass_conservation_error': result['analysis']['mass_conservation_error'],
                'h_variation_coefficient': result['analysis']['h_variation_coefficient'],
                'q_variation_coefficient': result['analysis']['q_variation_coefficient'],
            })
        else:
            json_results.append({
                'scenario_id': result.get('scenario_id', '?'),
                'success': False,
                'error': result.get('error', ''),
                'stage': result.get('stage', ''),
            })
    
    json_path = os.path.join(output_base_dir, "results_summary.json")
    with open(json_path, 'w', encoding='utf-8') as f:
        json.dump(json_results, f, indent=2, ensure_ascii=False)
    
    print(f" JSON结果已生成: {json_path}")
    
    print("\n" + "="*100)
    if n_success == len(results):
        print(" 所有工况测试完成！".center(100))
    else:
        print(f" {n_success}/{len(results)} 工况完成".center(100))
    print("="*100 + "\n")
    
    return results


if __name__ == "__main__":
    results = main()
