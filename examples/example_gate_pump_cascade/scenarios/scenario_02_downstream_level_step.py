#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
工况2: 下游水位阶跃

初始状态: h_downstream = 2.0 m
扰动: t=300s, h_downstream → 3.5 m
观测: 回水效应、流量变化、上游影响
"""

import sys
import os
script_dir = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, script_dir)

from scenario_utils import *


def main():
    """主函数"""
    scenario_name = "Scenario 02: Downstream Level Step"
    output_dir = os.path.join(os.path.dirname(script_dir), "results_scenarios", "scenario_02")
    
    print("\n" + "="*90)
    print(scenario_name.center(90))
    print("="*90)
    print("\n工况说明:")
    print("  初始水位: 2.0 m")
    print("  扰动时刻: t=300s")
    print("  目标水位: 3.5 m")
    print("  观测内容: 回水效应、流量变化、上游影响")
    print("="*90)
    
    # 创建系统
    solver, structures = create_standard_system()
    gate1, gate2, pump = structures
    
    # 稳态求解
    steady_state = run_steady_state(solver, structures, Q_initial=30.0, h_downstream=2.0)
    
    # 瞬态模拟 - 下游水位阶跃
    print("\n" + "="*80)
    print("设置瞬态边界条件".center(80))
    print("="*80)
    print("  t < 300s: h_downstream = 2.0 m")
    print("  t >=300s: h_downstream = 3.5 m")
    
    def downstream_bc(t):
        if t < 300:
            return 2.0
        else:
            return 3.5
    
    solver.h = steady_state['h'].copy()
    solver.q = steady_state['q'].copy()
    
    duration = 3600
    save_interval = 60
    n_steps = duration
    
    h_history = []
    q_history = []
    time_points = []
    
    print("\n进度监控:")
    print("-" * 80)
    
    for step in range(n_steps):
        t = step * solver.dt
        
        h_down = downstream_bc(t)
        solver.set_boundary_conditions(
            upstream_type='discharge',
            upstream_value=30.0,
            downstream_type='depth',
            downstream_value=h_down
        )
        
        solver.step_preissmann(structures=structures, theta=0.6)
        
        if step % save_interval == 0:
            h_history.append(solver.h.copy())
            q_history.append(solver.q.copy())
            time_points.append(t)
            
            progress = (step / n_steps) * 100
            print(f"  t={t:6.0f}s ({progress:5.1f}%) | "
                  f"h_down={h_down:4.2f} m | "
                  f"Q_mean={solver.q.mean():.2f} m³/s")
    
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
                      steady_state, description="Downstream water level step from 2.0 to 3.5 m at t=300s")
    
    print_scenario_summary(scenario_name, steady_state, h_history, q_history, time_points)
    
    print(f"\n所有结果已保存到: {output_dir}")


if __name__ == "__main__":
    main()
