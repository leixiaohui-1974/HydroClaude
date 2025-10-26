#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
工况4: 泵站能力测试

初始状态: Q_upstream = 30 m³/s (在泵站能力范围内)
扰动: t=300s, Q_upstream → 45 m³/s (超过泵站能力)
观测: 泵站响应、泵前水位上升、流量限制
"""

import sys
import os
script_dir = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, script_dir)

from scenario_utils import *


def main():
    """主函数"""
    scenario_name = "Scenario 04: Pump Capacity Test"
    output_dir = os.path.join(os.path.dirname(script_dir), "results_scenarios", "scenario_04")
    
    print("\n" + "="*90)
    print(scenario_name.center(90))
    print("="*90)
    print("\n工况说明:")
    print("  初始流量: 30 m³/s (泵站额定流量)")
    print("  扰动时刻: t=300s")
    print("  目标流量: 45 m³/s (超过泵站能力)")
    print("  观测内容: 泵站响应、泵前蓄水、流量限制")
    print("="*90)
    
    # 创建系统
    solver, structures = create_standard_system()
    gate1, gate2, pump = structures
    
    # 稳态求解
    steady_state = run_steady_state(solver, structures, Q_initial=30.0, h_downstream=2.0)
    
    # 瞬态模拟
    print("\n" + "="*80)
    print("设置瞬态边界条件".center(80))
    print("="*80)
    print("  t < 300s: Q_upstream = 30 m³/s")
    print("  t >=300s: Q_upstream = 45 m³/s (超过泵站能力)")
    
    def upstream_bc(t):
        if t < 300:
            return 30.0
        else:
            return 45.0
    
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
        
        Q_up = upstream_bc(t)
        solver.set_boundary_conditions(
            upstream_type='discharge',
            upstream_value=Q_up,
            downstream_type='depth',
            downstream_value=2.0
        )
        
        solver.step_preissmann(structures=structures, theta=0.6)
        
        if step % save_interval == 0:
            h_history.append(solver.h.copy())
            q_history.append(solver.q.copy())
            time_points.append(t)
            
            # 找泵站位置
            pump_idx = np.argmin(np.abs(solver.x - pump.position))
            h_pump_upstream = solver.h[max(0, pump_idx-1)]
            q_pump = solver.q[pump_idx]
            
            progress = (step / n_steps) * 100
            print(f"  t={t:6.0f}s ({progress:5.1f}%) | "
                  f"Q_up={Q_up:5.1f} m³/s | "
                  f"h_pump={h_pump_upstream:.2f} m | "
                  f"Q_pump={q_pump:.2f} m³/s")
    
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
                      steady_state, description="Pump capacity test: upstream flow from 30 to 45 m³/s at t=300s")
    
    print_scenario_summary(scenario_name, steady_state, h_history, q_history, time_points)
    
    print(f"\n所有结果已保存到: {output_dir}")


if __name__ == "__main__":
    main()
