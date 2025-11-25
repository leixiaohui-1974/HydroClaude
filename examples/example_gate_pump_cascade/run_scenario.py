#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
快速运行工况的辅助脚本
通过参数化方式运行不同工况
"""

import sys
import warnings
warnings.filterwarnings("ignore")
import os
import shutil

# 添加项目根目录
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
from utils.visualization_templates import VisualizationTemplates


def run_scenario(scenario_name, scenario_config):
    """运行单个工况"""
    
    print("\n" + "="*90)
    print(f"工况: {scenario_name}".center(90))
    print("="*90)
    print(f"\n{scenario_config['description']}\n")
    print("-"*90)
    
    # 系统参数
    L_total = 100000.0
    B = 15.0
    S0 = 0.0001
    n = 0.025
    nx = 501
    dt = 0.5  # 减小时间步长，提高稳定性
    
    # 结构物位置
    gate1_pos = 25000.0
    pump_pos = 50000.0
    gate2_pos = 75000.0
    
    # 创建结构物
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
    
    # 配置底床高程
    pump_idx = np.argmin(np.abs(solver.x - pump_pos))
    solver.z[pump_idx:] += 5.0  # 泵后抬高5m
    
    # 稳态求解
    print("▶ 稳态求解...")
    Q_initial = scenario_config.get('Q_initial', 30.0)
    h_uniform = compute_steady_uniform_flow(Q_initial, B, S0, n)
    h_downstream_boundary = h_uniform
    
    solver.h[:] = h_uniform
    solver.hu[:] = Q_initial / B
    
    result_steady = solver.solve_steady_state(
        Q_target=Q_initial,
        h_downstream=h_downstream_boundary,
        convergence_tol=0.0005,  # 更严格的收敛判据
        max_iterations=2000,  # 增加迭代次数
        dt=dt,
        verbose=False
    )
    
    print(f"  稳态收敛: {result_steady['converged']} (迭代{result_steady['iterations']}次)")
    
    h_steady = solver.h.copy()
    hu_steady = solver.hu.copy()
    
    # 瞬态模拟
    print(f"\n▶ 瞬态模拟 (3600秒)...")
    
    solver.h[:] = h_steady
    solver.hu[:] = hu_steady
    
    n_steps = int(3600 / dt)  # 总时长3600s
    save_interval = int(60 / dt)  # 每60s保存一次
    n_saves = n_steps // save_interval + 1
    
    h_history = np.zeros((n_saves, solver.nx))
    q_history = np.zeros((n_saves, solver.nx))
    pump_head_history = np.zeros(n_saves)
    time_history = np.zeros(n_saves)
    
    h_history[0, :] = solver.h
    q_history[0, :] = solver.hu * B
    pump_head_history[0] = pump.get_current_head()
    time_history[0] = 0.0
    
    # 获取边界条件函数
    get_Q_upstream = scenario_config['Q_upstream_func']
    get_h_downstream = scenario_config.get('h_downstream_func', lambda t: h_downstream_boundary)
    get_gate1_opening = scenario_config.get('gate1_opening_func', lambda t: 5.0)
    
    save_idx = 1
    for step in range(1, n_steps + 1):
        t_current = step * dt
        
        # 更新边界条件
        Q_upstream = get_Q_upstream(t_current)
        h_downstream = get_h_downstream(t_current)
        gate1.opening = get_gate1_opening(t_current)
        
        # 时间推进
        h_new, hu_new = solver.step_preissmann(
            dt=dt,
            max_iter=20,  # 增加瞬态迭代次数
            enforce_bc=True,
            Q_in=Q_upstream,
            h_out=h_downstream
        )
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
                      f"泵站Q={(solver.hu[pump_idx]*B):.2f}m^3/s")
            
            save_idx += 1
    
    print("   瞬态模拟完成")
    
    # 创建输出目录
    output_dir = os.path.join(
        os.path.dirname(os.path.abspath(__file__)),
        "results_advanced",
        scenario_name
    )
    os.makedirs(output_dir, exist_ok=True)
    
    # 生成动画和图表
    print(f"\n▶ 生成结果...")
    create_outputs(
        output_dir, solver, time_history, h_history, q_history,
        pump_head_history, scenario_config, gate1_pos, gate2_pos, pump_pos
    )
    
    print(f"\n 工况完成: {scenario_name}")
    print(f"  结果位置: {output_dir}")
    print("="*90 + "\n")
    
    return output_dir


def create_outputs(output_dir, solver, time_history, h_history, q_history,
                   pump_head_history, config, gate1_pos, gate2_pos, pump_pos):
    """创建输出文件"""
    
    # 1. 水位纵剖面动画
    print("  生成水位动画...")
    create_water_level_animation(
        output_dir, solver.x, solver.z, time_history, h_history,
        gate1_pos, gate2_pos, pump_pos
    )
    
    # 2. 时空演化图
    print("  生成时空图...")
    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(16, 6))
    
    im1 = ax1.imshow(h_history, aspect='auto', cmap='Blues', origin='lower',
                     extent=[0, solver.x[-1]/1000, time_history[0], time_history[-1]])
    ax1.set_xlabel('Distance (km)', fontsize=11)
    ax1.set_ylabel('Time (s)', fontsize=11)
    ax1.set_title('Water Depth Evolution', fontsize=12, fontweight='bold')
    plt.colorbar(im1, ax=ax1, label='Depth (m)')
    
    im2 = ax2.imshow(q_history, aspect='auto', cmap='viridis', origin='lower',
                     extent=[0, solver.x[-1]/1000, time_history[0], time_history[-1]])
    ax2.set_xlabel('Distance (km)', fontsize=11)
    ax2.set_ylabel('Time (s)', fontsize=11)
    ax2.set_title('Flow Rate Evolution', fontsize=12, fontweight='bold')
    plt.colorbar(im2, ax=ax2, label='Flow (m^3/s)')
    
    plt.tight_layout()
    plt.savefig(os.path.join(output_dir, "spatiotemporal.png"), dpi=150, bbox_inches='tight')
    plt.close()
    
    # 3. 关键位置时间序列
    print("  生成时间序列...")
    pump_idx = np.argmin(np.abs(solver.x - pump_pos))
    
    fig, ((ax1, ax2), (ax3, ax4)) = plt.subplots(2, 2, figsize=(14, 10))
    
    ax1.plot(time_history/60, h_history[:, pump_idx-1], 'b-', linewidth=2)
    ax1.set_xlabel('Time (min)', fontsize=10)
    ax1.set_ylabel('Water Depth (m)', fontsize=10)
    ax1.set_title('Water Depth Before Pump', fontsize=11, fontweight='bold')
    ax1.grid(True, alpha=0.3)
    
    ax2.plot(time_history/60, q_history[:, pump_idx], 'r-', linewidth=2)
    ax2.set_xlabel('Time (min)', fontsize=10)
    ax2.set_ylabel('Flow Rate (m^3/s)', fontsize=10)
    ax2.set_title('Pump Station Flow', fontsize=11, fontweight='bold')
    ax2.grid(True, alpha=0.3)
    
    ax3.plot(time_history/60, pump_head_history, 'g-', linewidth=2)
    ax3.axhline(5.0, color='gray', linestyle='--', alpha=0.5)
    ax3.set_xlabel('Time (min)', fontsize=10)
    ax3.set_ylabel('Pump Head (m)', fontsize=10)
    ax3.set_title('Pump Station Head', fontsize=11, fontweight='bold')
    ax3.grid(True, alpha=0.3)
    
    ax4.plot(time_history/60, q_history[:, 0], 'b-', linewidth=2, label='Upstream')
    ax4.plot(time_history/60, q_history[:, -1], 'r-', linewidth=2, label='Downstream')
    ax4.set_xlabel('Time (min)', fontsize=10)
    ax4.set_ylabel('Flow Rate (m^3/s)', fontsize=10)
    ax4.set_title('Boundary Flow Rates', fontsize=11, fontweight='bold')
    ax4.legend()
    ax4.grid(True, alpha=0.3)
    
    plt.tight_layout()
    plt.savefig(os.path.join(output_dir, "time_series.png"), dpi=150, bbox_inches='tight')
    plt.close()
    
    # 4. 保存数据
    print("  保存数据...")
    np.savez(
        os.path.join(output_dir, "scenario_data.npz"),
        x=solver.x,
        z=solver.z,
        time=time_history,
        h_history=h_history,
        q_history=q_history,
        pump_head_history=pump_head_history
    )
    
    # 5. 创建报告
    print("  生成报告...")
    with open(os.path.join(output_dir, "SCENARIO_REPORT.md"), 'w', encoding='utf-8') as f:
        f.write(f"# {config['name']}\n\n")
        f.write(f"## 工况说明\n\n{config['description']}\n\n")
        f.write(f"## 最终结果 (t={time_history[-1]:.0f}s)\n\n")
        f.write(f"- 泵前水深: {h_history[-1, pump_idx-1]:.3f} m\n")
        f.write(f"- 泵站流量: {q_history[-1, pump_idx]:.2f} m^3/s\n")
        f.write(f"- 泵站扬程: {pump_head_history[-1]:.3f} m\n")
        f.write(f"- 渠首流量: {q_history[-1, 0]:.2f} m^3/s\n")
        f.write(f"- 渠尾流量: {q_history[-1, -1]:.2f} m^3/s\n")
        f.write(f"- 蓄水速率: {(q_history[-1, 0] - q_history[-1, -1]):.2f} m^3/s\n\n")
        f.write(f"## 输出文件\n\n")
        f.write(f"- `animation_water_level.gif` - 水位纵剖面动画 \n")
        f.write(f"- `spatiotemporal.png` - 时空演化图\n")
        f.write(f"- `time_series.png` - 关键位置时间序列\n")
        f.write(f"- `scenario_data.npz` - 完整数据\n")
    
    print("   所有结果已生成")


def create_water_level_animation(output_dir, x, z, time, h_history, gate1_pos, gate2_pos, pump_pos):
    """创建水位纵剖面动画"""
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
        ax.axvline(gate1_pos/1000, color='green', linestyle='--', linewidth=2, alpha=0.7)
        ax.axvline(pump_pos/1000, color='red', linestyle='--', linewidth=2, alpha=0.7)
        ax.axvline(gate2_pos/1000, color='green', linestyle='--', linewidth=2, alpha=0.7)
        
        ax.set_xlim(0, x[-1]/1000)
        ax.set_ylim(z_min, z_max)
        ax.set_xlabel('Distance (km)', fontsize=12)
        ax.set_ylabel('Elevation (m)', fontsize=12)
        ax.set_title(f'Water Level Profile (t={time[frame]:.0f}s)', fontsize=13, fontweight='bold')
        ax.grid(True, alpha=0.3)
        ax.legend(loc='upper right', fontsize=10)
    
    anim = FuncAnimation(fig, update, frames=len(time), interval=200)
    anim.save(os.path.join(output_dir, "animation_water_level.gif"), writer=PillowWriter(fps=5))
    plt.close()


if __name__ == "__main__":
    # 工况2: 中等流量阶跃
    scenario2 = {
        'name': 'Scenario 02: Medium Flow Step',
        'description': '''**工况类型**: 上游边界扰动（中等幅度）

**初始状态**: Q = 30 m^3/s
**扰动**: t=300s, Q -> 42 m^3/s (+40%)
**观测**: 泵站在能力范围内的响应、工作点求解''',
        'Q_initial': 30.0,
        'Q_upstream_func': lambda t: 42.0 if t >= 300 else 30.0
    }
    
    run_scenario("scenario_02_upstream_flow_medium", scenario2)
