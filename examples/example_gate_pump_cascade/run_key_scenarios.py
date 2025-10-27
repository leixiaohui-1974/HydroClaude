#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
运行关键工况的非恒定流模拟
选择有代表性的工况进行完整测试
"""

import sys
import os
import time
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt

# 路径设置
project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, project_root)

from solvers.hydrostatic_canal_solver import HydrostaticCanalSolver
from solvers.gate import SluiceGate, PumpStation
from utils.canal_utils import compute_steady_uniform_flow

# 选择关键工况（代表不同类别）
KEY_SCENARIOS = {
    'S01_flow_step_small': {
        'name': '工况01: 上游流量小幅阶跃',
        'description': '初始30 m³/s，t=300s阶跃至35 m³/s (+17%)',
        'category': '上游流量扰动',
        'Q_initial': 30.0,
        'Q_upstream_func': lambda t: 35.0 if t >= 300 else 30.0,
        'h_downstream_func': None,
        'gate1_opening_func': None,
        't_total': 1800.0,  # 缩短到30分钟
    },
    
    'S03_flow_step_large': {
        'name': '工况03: 上游流量大幅阶跃',
        'description': '初始30 m³/s，t=300s阶跃至55 m³/s (+83%)',
        'category': '上游流量扰动',
        'Q_initial': 30.0,
        'Q_upstream_func': lambda t: 55.0 if t >= 300 else 30.0,
        'h_downstream_func': None,
        'gate1_opening_func': None,
        't_total': 1800.0,
    },
    
    'S10_gate1_close_more': {
        'name': '工况10: 闸门1开度减小',
        'description': '初始5m，t=300s阶跃至3m（减小泄流）',
        'category': '闸门开度调节',
        'Q_initial': 30.0,
        'Q_upstream_func': lambda t: 30.0,
        'h_downstream_func': None,
        'gate1_opening_func': lambda t: 3.0 if t >= 300 else 5.0,
        't_total': 1800.0,
    },
}

def run_scenario_transient(scenario_id, config, output_base_dir):
    """运行单个工况的非恒定流模拟"""
    print("\n" + "="*100)
    print(f"{config['name']}".center(100))
    print("="*100)
    print(f"描述: {config['description']}")
    print(f"类别: {config['category']}")
    
    start_time = time.time()
    
    # 系统参数
    L_total = 100000.0
    B = 15.0
    S0 = 0.0001
    n = 0.025
    nx = 201  # 适中的网格
    dt = 0.5
    
    gate1_pos = 25000.0
    pump_pos = 50000.0
    gate2_pos = 75000.0
    
    # 创建结构物
    gate1 = SluiceGate(gate1_pos, B, 5.0, 0.6)
    gate2 = SluiceGate(gate2_pos, B, 5.0, 0.6)
    pump = PumpStation(
        position=pump_pos,
        width=B,
        rated_flow=30.0,
        rated_head=5.0,
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
    solver.z[pump_idx:] += 5.0
    
    # 稳态求解
    print("\n▶ 稳态求解...")
    Q_initial = config.get('Q_initial', 30.0)
    h_uniform = compute_steady_uniform_flow(Q_initial, B, S0, n)
    h_downstream_boundary = h_uniform
    
    solver.h[:] = h_uniform
    solver.hu[:] = Q_initial / B
    
    result_steady = solver.solve_steady_state(
        Q_target=Q_initial,
        h_downstream=h_downstream_boundary,
        convergence_tol=0.01,
        max_iterations=500,
        dt=dt,
        verbose=True
    )
    
    if not result_steady['converged']:
        print(f"  ✗ 稳态未收敛，跳过瞬态模拟")
        return {'success': False, 'stage': 'steady_state'}
    
    h_steady = solver.h.copy()
    hu_steady = solver.hu.copy()
    
    # 瞬态模拟
    print("\n▶ 瞬态模拟...")
    solver.h[:] = h_steady
    solver.hu[:] = hu_steady
    
    t_total = config.get('t_total', 1800.0)
    n_steps = int(t_total / dt)
    save_interval = int(20 / dt)  # 每20s保存一次
    n_saves = n_steps // save_interval + 1
    
    # 历史数据
    h_history = np.zeros((n_saves, solver.nx))
    q_history = np.zeros((n_saves, solver.nx))
    time_history = np.zeros(n_saves)
    
    h_history[0, :] = solver.h
    q_history[0, :] = solver.hu * B
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
            
            # Preissmann时间推进（关闭泵站掩码以避免累积）
            h_new, hu_new = solver.step_preissmann(
                dt=dt,
                max_iter=10,
                enforce_bc=True,
                Q_in=Q_upstream,
                h_out=h_downstream,
                use_pump_mask=False  # 非恒定流不使用泵站掩码
            )
            
            # 检查数值稳定性
            if np.any(np.isnan(h_new)) or np.any(np.isinf(h_new)) or np.any(h_new < 0):
                print(f"  ✗ 数值不稳定 (t={t_current:.1f}s)")
                failed = True
                break
            
            solver.h[:] = h_new
            solver.hu[:] = hu_new
            
            # 保存数据
            if step % save_interval == 0:
                h_history[save_idx, :] = solver.h
                q_history[save_idx, :] = solver.hu * B
                time_history[save_idx] = t_current
                
                if save_idx % 10 == 0:
                    progress = (step / n_steps) * 100
                    print(f"  进度: {progress:5.1f}% | t={t_current:6.0f}s | "
                          f"泵前h={solver.h[pump_idx-1]:.3f}m")
                
                save_idx += 1
        
        if not failed:
            print("  ✓ 瞬态模拟完成")
            
    except Exception as e:
        print(f"  ✗ 瞬态模拟失败: {str(e)}")
        return {'success': False, 'stage': 'transient', 'error': str(e)}
    
    if failed:
        return {'success': False, 'stage': 'transient'}
    
    # 截取有效数据
    if save_idx < n_saves:
        h_history = h_history[:save_idx, :]
        q_history = q_history[:save_idx, :]
        time_history = time_history[:save_idx]
    
    elapsed_time = time.time() - start_time
    
    # 简单绘图
    print("\n▶ 生成结果图...")
    output_dir = os.path.join(output_base_dir, scenario_id)
    os.makedirs(output_dir, exist_ok=True)
    
    fig, axes = plt.subplots(2, 2, figsize=(16, 10))
    
    # 水位纵剖面（初始和最终）
    ax = axes[0, 0]
    eta_0 = solver.z + h_history[0, :]
    eta_f = solver.z + h_history[-1, :]
    ax.plot(solver.x/1000, solver.z, 'k-', linewidth=2, label='Bed')
    ax.plot(solver.x/1000, eta_0, 'b-', linewidth=2, label='t=0s')
    ax.plot(solver.x/1000, eta_f, 'r-', linewidth=2, label=f't={time_history[-1]:.0f}s')
    ax.axvline(gate1_pos/1000, color='green', linestyle='--', alpha=0.5)
    ax.axvline(pump_pos/1000, color='red', linestyle='--', alpha=0.5)
    ax.axvline(gate2_pos/1000, color='green', linestyle='--', alpha=0.5)
    ax.set_xlabel('Distance (km)', fontsize=12)
    ax.set_ylabel('Elevation (m)', fontsize=12)
    ax.set_title('Longitudinal Profile', fontsize=14, fontweight='bold')
    ax.legend(fontsize=10)
    ax.grid(True, alpha=0.3)
    
    # 水深时空演化
    ax = axes[0, 1]
    X, T = np.meshgrid(solver.x/1000, time_history/60)
    c = ax.contourf(X, T, h_history, levels=20, cmap='viridis')
    plt.colorbar(c, ax=ax, label='Water Depth (m)')
    ax.axvline(gate1_pos/1000, color='white', linestyle='--', alpha=0.5)
    ax.axvline(pump_pos/1000, color='white', linestyle='--', alpha=0.5)
    ax.axvline(gate2_pos/1000, color='white', linestyle='--', alpha=0.5)
    ax.set_xlabel('Distance (km)', fontsize=12)
    ax.set_ylabel('Time (min)', fontsize=12)
    ax.set_title('Water Depth Spatiotemporal', fontsize=14, fontweight='bold')
    
    # 关键位置时间序列
    ax = axes[1, 0]
    gate1_idx = np.argmin(np.abs(solver.x - gate1_pos))
    pump_idx = np.argmin(np.abs(solver.x - pump_pos))
    gate2_idx = np.argmin(np.abs(solver.x - gate2_pos))
    
    ax.plot(time_history/60, h_history[:, 0], 'b-', linewidth=2, label='Upstream (0km)')
    ax.plot(time_history/60, h_history[:, gate1_idx], 'g-', linewidth=2, label=f'Gate1 ({gate1_pos/1000:.0f}km)')
    ax.plot(time_history/60, h_history[:, pump_idx], 'r-', linewidth=2, label=f'Pump ({pump_pos/1000:.0f}km)')
    ax.plot(time_history/60, h_history[:, -1], 'orange', linewidth=2, label='Downstream (100km)')
    ax.set_xlabel('Time (min)', fontsize=12)
    ax.set_ylabel('Water Depth (m)', fontsize=12)
    ax.set_title('Water Depth at Key Locations', fontsize=14, fontweight='bold')
    ax.legend(fontsize=10)
    ax.grid(True, alpha=0.3)
    
    # 流量时间序列
    ax = axes[1, 1]
    ax.plot(time_history/60, q_history[:, 0], 'b-', linewidth=2, label='Upstream')
    ax.plot(time_history/60, q_history[:, pump_idx], 'r-', linewidth=2, label='Pump')
    ax.plot(time_history/60, q_history[:, -1], 'orange', linewidth=2, label='Downstream')
    ax.axhline(Q_initial, color='gray', linestyle='--', alpha=0.5, label=f'Initial: {Q_initial:.0f} m³/s')
    ax.set_xlabel('Time (min)', fontsize=12)
    ax.set_ylabel('Flow Rate (m³/s)', fontsize=12)
    ax.set_title('Flow Rate Time Series', fontsize=14, fontweight='bold')
    ax.legend(fontsize=10)
    ax.grid(True, alpha=0.3)
    
    plt.suptitle(f'{config["name"]} - Transient Simulation Results', fontsize=16, fontweight='bold')
    plt.tight_layout()
    plt.savefig(os.path.join(output_dir, 'transient_results.png'), dpi=150, bbox_inches='tight')
    plt.close()
    
    # 保存数据
    np.savez(
        os.path.join(output_dir, 'data.npz'),
        x=solver.x,
        z=solver.z,
        time=time_history,
        h_history=h_history,
        q_history=q_history,
        h_steady=h_steady,
        q_steady=hu_steady * B
    )
    
    print(f"  ✓ 结果已保存至: {output_dir}")
    print(f"\n✓ {config['name']} 完成 (耗时: {elapsed_time:.1f}秒)")
    
    return {
        'success': True,
        'scenario_id': scenario_id,
        'elapsed_time': elapsed_time,
        'output_dir': output_dir
    }


def main():
    """主函数"""
    print("\n" + "="*100)
    print("串联明渠闸泵群系统 - 关键工况非恒定流测试".center(100))
    print("="*100)
    print(f"\n关键工况数: {len(KEY_SCENARIOS)}")
    print("\n" + "="*100)
    
    # 创建输出目录
    base_dir = os.path.dirname(os.path.abspath(__file__))
    output_base_dir = os.path.join(base_dir, "results_enhanced")
    os.makedirs(output_base_dir, exist_ok=True)
    
    # 运行所有关键工况
    results = []
    start_time_total = time.time()
    
    for i, (scenario_id, config) in enumerate(KEY_SCENARIOS.items(), 1):
        print(f"\n进度: [{i}/{len(KEY_SCENARIOS)}]")
        result = run_scenario_transient(scenario_id, config, output_base_dir)
        results.append(result)
    
    elapsed_total = time.time() - start_time_total
    
    # 总结
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
        print(f"\n成功工况:")
        for result in results:
            if result.get('success'):
                scenario_id = result['scenario_id']
                name = KEY_SCENARIOS[scenario_id]['name']
                elapsed = result['elapsed_time']
                print(f"  ✓ {name} ({elapsed:.1f}秒)")
    
    if n_failed > 0:
        print(f"\n失败工况:")
        for result in results:
            if not result.get('success'):
                scenario_id = result['scenario_id']
                name = KEY_SCENARIOS[scenario_id]['name']
                stage = result.get('stage', 'unknown')
                print(f"  ✗ {name} (失败阶段: {stage})")
    
    print("\n" + "="*100)
    if n_success == len(results):
        print("✓✓✓ 所有关键工况测试通过！".center(100))
    else:
        print(f"⚠ {n_success}/{len(results)} 工况通过".center(100))
    print("="*100 + "\n")
    
    return results


if __name__ == "__main__":
    results = main()
