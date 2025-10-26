#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
明渠串联闸泵群系统 - 使用简化耦合泵站模型

相比原版本的改进：
1. 使用PumpStationSimplified替代PumpStation
2. 泵站流量跟随上游（质量守恒）
3. 泵站能力限制（最大1.3倍额定流量）
4. 扬程随流量调整

作者: Claude
日期: 2025-10-26
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
from solvers.gate import SluiceGate, PumpStationSimplified
from utils.canal_utils import compute_steady_uniform_flow
from utils.result_validator import ResultValidator, quick_validate_steady_state
from utils.visualization_templates import VisualizationTemplates


def main():
    """主函数"""
    
    print("=" * 90)
    print("明渠串联闸泵群系统动态模拟（简化耦合泵站模型）".center(90))
    print("=" * 90)
    print()
    
    # ==================== 1. 参数设置 ====================
    print("▶ 1. 系统参数设置")
    print("-" * 90)
    
    SCENARIO = "mountain"  # 山区调水泵站
    
    # 渠道参数
    L_total = 100000.0
    B = 15.0
    S0 = 0.0001
    n = 0.025
    nx = 501
    
    # 流量参数
    Q_initial = 30.0
    Q_step = 55.0
    
    # 结构物位置
    gate1_pos = 25000.0
    pump_pos = 50000.0
    gate2_pos = 75000.0
    
    # 闸门参数
    gate_opening = 5.0
    gate_Cd = 0.6
    
    # 泵站参数（使用简化模型）
    pump_rated_flow = 30.0
    pump_rated_head = 5.0
    pump_max_overload = 1.3  # 允许30%超载
    pump_min_head = 2.0
    
    # 瞬态模拟参数
    t_total = 3600.0
    dt = 1.0
    
    print(f"渠道参数:")
    print(f"  总长度: {L_total/1000:.1f} km")
    print(f"  渠道宽度: {B:.1f} m")
    print(f"  底坡: {S0*10000:.2f}‰")
    print(f"  网格: {nx}点")
    print()
    
    print(f"泵站模型: PumpStationSimplified（简化耦合模型）")
    print(f"  额定流量: {pump_rated_flow} m³/s")
    print(f"  额定扬程: {pump_rated_head} m")
    print(f"  最大流量: {pump_rated_flow * pump_max_overload} m³/s (允许{(pump_max_overload-1)*100:.0f}%超载)")
    print(f"  特点: 流量跟随上游，质量守恒")
    print()
    
    # ==================== 2. 创建求解器和结构物 ====================
    print("▶ 2. 创建求解器和结构物")
    print("-" * 90)
    
    # 创建闸门
    gate1 = SluiceGate(gate1_pos, B, gate_opening, gate_Cd)
    gate2 = SluiceGate(gate2_pos, B, gate_opening, gate_Cd)
    
    # 创建简化耦合泵站
    pump = PumpStationSimplified(
        position=pump_pos,
        width=B,
        rated_flow=pump_rated_flow,
        rated_head=pump_rated_head,
        max_overload_ratio=pump_max_overload,
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
    
    print(f"求解器: HydrostaticCanalSolver")
    print(f"  网格: {solver.nx}点, Δx={solver.dx:.1f}m")
    print()
    
    # 均匀流水深
    h_uniform = compute_steady_uniform_flow(Q_initial, B, S0, n)
    print(f"均匀流水深: {h_uniform:.3f} m")
    print()
    
    # ==================== 3. 场景配置 ====================
    print(f"▶ 3. 场景配置: {SCENARIO.upper()}")
    print("-" * 90)
    
    pump_idx = np.argmin(np.abs(solver.x - pump_pos))
    
    if SCENARIO == "mountain":
        print("山区调水泵站:")
        print(f"  - 泵后底床抬高 {pump_rated_head:.1f}m")
        solver.z[pump_idx:] += pump_rated_head
        h_downstream_boundary = h_uniform
        print(f"  - 下游边界: h = {h_downstream_boundary:.3f} m")
    else:
        h_downstream_boundary = h_uniform + pump_rated_head
        print(f"  - 下游边界: h = {h_downstream_boundary:.3f} m")
    
    print()
    
    # ==================== 4. 稳态求解 ====================
    print("=" * 90)
    print("▶ 4. 稳态求解")
    print("-" * 90)
    
    solver.h[:] = h_uniform
    solver.hu[:] = Q_initial / B
    
    print("开始稳态求解...")
    result_steady = solver.solve_steady_state(
        Q_target=Q_initial,
        h_downstream=h_downstream_boundary,
        convergence_tol=0.001,
        max_iterations=500,
        dt=dt,
        verbose=True
    )
    
    print()
    if result_steady['converged']:
        print(f"✓ 稳态求解成功")
        print(f"  迭代: {result_steady['iterations']}")
        print(f"  流量误差: {result_steady.get('final_flow_error', 0):.6f}%")
    print()
    
    h_steady = solver.h.copy()
    hu_steady = solver.hu.copy()
    
    # ==================== 5. 瞬态模拟 ====================
    print("=" * 90)
    print("▶ 5. 瞬态模拟（流量阶跃 30→55 m³/s）")
    print("-" * 90)
    
    solver.h[:] = h_steady
    solver.hu[:] = hu_steady
    
    n_steps = int(t_total / dt)
    save_interval = int(600 / dt)
    n_saves = n_steps // save_interval + 1
    
    h_history = np.zeros((n_saves, solver.nx))
    q_history = np.zeros((n_saves, solver.nx))
    time_history = np.zeros(n_saves)
    
    h_history[0, :] = solver.h
    q_history[0, :] = solver.hu * B
    time_history[0] = 0.0
    
    print(f"设置:")
    print(f"  总步数: {n_steps}")
    print(f"  保存间隔: {save_interval}步 = {save_interval*dt:.0f}秒")
    print()
    
    print("开始模拟...")
    print(f"{'时间(分钟)':>12} {'进度':>8} {'泵前Q':>10} {'泵站Q':>10} {'泵后Q':>10} {'泵扬程':>10}")
    print("-" * 80)
    
    save_idx = 1
    for step in range(1, n_steps + 1):
        t_current = step * dt
        
        Q_upstream = Q_step
        h_downstream = h_downstream_boundary
        
        # Preissmann时间推进
        h_new, hu_new = solver.step_preissmann(
            dt=dt,
            max_iter=10,
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
            time_history[save_idx] = t_current
            
            # 泵站处数据
            q_before_pump = q_history[save_idx, pump_idx-1]
            q_at_pump = q_history[save_idx, pump_idx]
            q_after_pump = q_history[save_idx, pump_idx+1]
            pump_head = pump.get_current_head()
            
            progress = (step / n_steps) * 100
            print(f"{t_current/60:12.1f} {progress:7.1f}% {q_before_pump:10.2f} {q_at_pump:10.2f} {q_after_pump:10.2f} {pump_head:10.3f}")
            
            save_idx += 1
    
    print()
    print("✓ 瞬态模拟完成")
    print()
    
    # ==================== 6. 可视化 ====================
    print("=" * 90)
    print("▶ 6. 结果可视化")
    print("-" * 90)
    
    output_dir = os.path.join(project_root, "examples", "example_gate_pump_cascade", "results")
    os.makedirs(output_dir, exist_ok=True)
    
    # 创建对比图
    fig, axes = plt.subplots(3, 2, figsize=(18, 14))
    
    # 选择关键时刻
    time_indices = [0, len(time_history)//2, -1]
    colors = ['blue', 'orange', 'red']
    labels = [f't={time_history[i]:.0f}s' for i in time_indices]
    
    # 子图1: 流量空间分布
    ax = axes[0, 0]
    for t_idx, color, label in zip(time_indices, colors, labels):
        ax.plot(solver.x/1000, q_history[t_idx, :], color=color, linewidth=2, label=label)
    ax.axvline(pump_pos/1000, color='red', linestyle='--', alpha=0.5)
    ax.set_xlabel('Distance (km)')
    ax.set_ylabel('Flow Rate (m³/s)')
    ax.set_title('Flow Rate Distribution (简化模型)')
    ax.legend()
    ax.grid(True, alpha=0.3)
    
    # 子图2: 水深空间分布
    ax = axes[0, 1]
    for t_idx, color, label in zip(time_indices, colors, labels):
        ax.plot(solver.x/1000, h_history[t_idx, :], color=color, linewidth=2, label=label)
    ax.axvline(pump_pos/1000, color='red', linestyle='--', alpha=0.5)
    ax.set_xlabel('Distance (km)')
    ax.set_ylabel('Water Depth (m)')
    ax.set_title('Water Depth Distribution')
    ax.legend()
    ax.grid(True, alpha=0.3)
    
    # 子图3: 泵站附近流量放大
    ax = axes[1, 0]
    zoom_range = slice(pump_idx-10, pump_idx+11)
    for t_idx, color, label in zip(time_indices, colors, labels):
        ax.plot(solver.x[zoom_range]/1000, q_history[t_idx, zoom_range], 
                color=color, linewidth=2.5, marker='o', markersize=6, label=label)
    ax.axvline(pump_pos/1000, color='red', linestyle='--', linewidth=2, alpha=0.7)
    ax.set_xlabel('Distance (km)')
    ax.set_ylabel('Flow Rate (m³/s)')
    ax.set_title('Flow Rate Near Pump Station (Zoomed)')
    ax.legend()
    ax.grid(True, alpha=0.3)
    
    # 子图4: 泵站处时间序列
    ax = axes[1, 1]
    ax.plot(time_history/60, q_history[:, pump_idx-1], 'b-', linewidth=2, label='Pump Inlet')
    ax.plot(time_history/60, q_history[:, pump_idx], 'r-', linewidth=2, label='Pump')
    ax.plot(time_history/60, q_history[:, pump_idx+1], 'g-', linewidth=2, label='Pump Outlet')
    ax.axhline(pump_rated_flow, color='gray', linestyle='--', alpha=0.5, label=f'Rated ({pump_rated_flow} m³/s)')
    ax.axhline(pump_rated_flow*pump_max_overload, color='orange', linestyle='--', alpha=0.5, 
               label=f'Max ({pump_rated_flow*pump_max_overload:.0f} m³/s)')
    ax.set_xlabel('Time (min)')
    ax.set_ylabel('Flow Rate (m³/s)')
    ax.set_title('Pump Station Flow Rate Time Series')
    ax.legend()
    ax.grid(True, alpha=0.3)
    
    # 子图5: 全渠道平均流量
    ax = axes[2, 0]
    q_mean = np.mean(q_history, axis=1)
    q_min = np.min(q_history, axis=1)
    q_max = np.max(q_history, axis=1)
    ax.plot(time_history/60, q_mean, 'b-', linewidth=2.5, label='Mean')
    ax.fill_between(time_history/60, q_min, q_max, alpha=0.3, label='Min-Max Range')
    ax.axhline(Q_initial, color='green', linestyle='--', label=f'Initial ({Q_initial} m³/s)')
    ax.axhline(Q_step, color='red', linestyle='--', label=f'Target ({Q_step} m³/s)')
    ax.set_xlabel('Time (min)')
    ax.set_ylabel('Flow Rate (m³/s)')
    ax.set_title('Channel Average Flow Rate')
    ax.legend()
    ax.grid(True, alpha=0.3)
    
    # 子图6: 质量守恒检查
    ax = axes[2, 1]
    q_in = q_history[:, 0]
    q_out = q_history[:, -1]
    q_diff = q_in - q_out
    ax.plot(time_history/60, q_in, 'b-', linewidth=2, label='Inlet')
    ax.plot(time_history/60, q_out, 'r-', linewidth=2, label='Outlet')
    ax.plot(time_history/60, q_diff, 'g--', linewidth=2, label='Difference (蓄水)')
    ax.set_xlabel('Time (min)')
    ax.set_ylabel('Flow Rate (m³/s)')
    ax.set_title('Mass Conservation Check')
    ax.legend()
    ax.grid(True, alpha=0.3)
    
    plt.tight_layout()
    filepath = os.path.join(output_dir, "PUMP_SIMPLIFIED_MODEL_RESULTS.png")
    plt.savefig(filepath, dpi=150, bbox_inches='tight')
    print(f"✓ 结果图已保存: {filepath}")
    plt.close()
    
    # 保存数据
    np.savez(
        os.path.join(output_dir, "simplified_model_data.npz"),
        x=solver.x,
        time=time_history,
        h_history=h_history,
        q_history=q_history,
        Q_initial=Q_initial,
        Q_step=Q_step,
        pump_pos=pump_pos
    )
    print(f"✓ 数据已保存: simplified_model_data.npz")
    print()
    
    # ==================== 7. 分析总结 ====================
    print("=" * 90)
    print("▶ 7. 模拟总结（简化耦合模型）")
    print("=" * 90)
    print()
    
    print("关键改进:")
    print("  ✓ 泵站流量跟随上游（质量守恒）")
    print("  ✓ 泵站能力限制（最大39 m³/s）")
    print("  ✓ 扬程随流量调整")
    print()
    
    print("最终结果:")
    idx_pump = pump_idx
    print(f"  泵前流量: {q_history[-1, idx_pump-1]:.2f} m³/s")
    print(f"  泵站流量: {q_history[-1, idx_pump]:.2f} m³/s")
    print(f"  泵后流量: {q_history[-1, idx_pump+1]:.2f} m³/s")
    print(f"  泵站扬程: {pump.get_current_head():.3f} m")
    print()
    
    # 质量守恒检查
    q_diff_final = q_history[-1, 0] - q_history[-1, -1]
    print(f"质量守恒检查:")
    print(f"  渠首流入: {q_history[-1, 0]:.2f} m³/s")
    print(f"  渠尾流出: {q_history[-1, -1]:.2f} m³/s")
    print(f"  差值: {q_diff_final:.2f} m³/s （蓄水中）")
    print()
    
    print("=" * 90)
    print("✓ 模拟完成！")
    print("=" * 90)
    print()


if __name__ == "__main__":
    main()
