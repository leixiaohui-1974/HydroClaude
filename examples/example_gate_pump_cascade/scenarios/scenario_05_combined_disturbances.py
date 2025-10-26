#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
工况5: 组合扰动

多重扰动测试：
  t=300s: 上游流量增加 (30→40 m³/s)
  t=600s: 闸门1开度增加 (0.709→1.0 m)
  t=900s: 下游水位上升 (2.0→2.5 m)
观测: 多重扰动叠加效应
"""

import sys
import os
script_dir = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, script_dir)

from scenario_utils import *


def main():
    """主函数"""
    scenario_name = "Scenario 05: Combined Disturbances"
    output_dir = os.path.join(os.path.dirname(script_dir), "results_scenarios", "scenario_05")
    
    print("\n" + "="*90)
    print(scenario_name.center(90))
    print("="*90)
    print("\n工况说明:")
    print("  多重扰动序列:")
    print("    t=300s: 上游流量 30→40 m³/s")
    print("    t=600s: 闸门1开度 0.709→1.0 m")
    print("    t=900s: 下游水位 2.0→2.5 m")
    print("  观测内容: 多重扰动叠加效应、系统响应")
    print("="*90)
    
    # 创建系统
    solver, structures = create_standard_system()
    gate1, gate2, pump = structures
    
    # 稳态求解
    steady_state = run_steady_state(solver, structures, Q_initial=30.0, h_downstream=2.0)
    
    # 瞬态模拟 - 组合扰动
    print("\n" + "="*80)
    print("设置瞬态边界条件".center(80))
    print("="*80)
    print("  t <  300s: 初始状态")
    print("  t >= 300s: 上游流量 → 40 m³/s")
    print("  t >= 600s: 闸门1开度 → 1.0 m")
    print("  t >= 900s: 下游水位 → 2.5 m")
    
    def upstream_bc(t):
        if t < 300:
            return 30.0
        else:
            return 40.0
    
    def downstream_bc(t):
        if t < 900:
            return 2.0
        else:
            return 2.5
    
    solver.h = steady_state['h'].copy()
    solver.q = steady_state['q'].copy()
    
    duration = 1800  # 30分钟
    save_interval = 30
    n_steps = duration
    
    h_history = []
    q_history = []
    time_points = []
    
    print("\n进度监控:")
    print("-" * 80)
    
    for step in range(n_steps):
        t = step * solver.dt
        
        # 更新边界条件
        Q_up = upstream_bc(t)
        h_down = downstream_bc(t)
        solver.set_boundary_conditions(
            upstream_type='discharge',
            upstream_value=Q_up,
            downstream_type='depth',
            downstream_value=h_down
        )
        
        # 更新闸门开度
        if t >= 600:
            gate1.opening = 1.0
        
        solver.step_preissmann(structures=structures, theta=0.6)
        
        if step % save_interval == 0:
            h_history.append(solver.h.copy())
            q_history.append(solver.q.copy())
            time_points.append(t)
            
            progress = (step / n_steps) * 100
            print(f"  t={t:6.0f}s ({progress:5.1f}%) | "
                  f"Q_up={Q_up:5.1f} | gate1={gate1.opening:.3f} | h_down={h_down:.2f}")
    
    print("✓ 瞬态模拟完成")
    
    import numpy as np
    time_points = np.array(time_points)
    h_history = np.array(h_history)
    q_history = np.array(q_history)
    
    # 创建输出
    create_animations(scenario_name, output_dir, solver.x, solver.z, time_points, h_history, q_history,
                     gate_positions=[gate1.position, gate2.position], pump_position=pump.position)
    
    create_supplementary_plots(output_dir, solver.x, solver.z, time_points, h_history, q_history,
                              gate_positions=[gate1.position, gate2.position], pump_position=pump.position)
    
    save_scenario_data(output_dir, scenario_name, solver.x, solver.z, time_points, h_history, q_history, 
                      steady_state, description="Combined disturbances: flow, gate, and level changes")
    
    print_scenario_summary(scenario_name, steady_state, h_history, q_history, time_points)
    
    print(f"\n所有结果已保存到: {output_dir}")


if __name__ == "__main__":
    main()
