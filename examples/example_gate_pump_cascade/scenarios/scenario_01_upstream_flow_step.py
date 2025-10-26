#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
工况1: 上游流量阶跃

初始状态: Q_upstream = 30 m³/s
扰动: t=300s, Q_upstream → 55 m³/s
观测: 流量波传播、水位响应、泵站工作点变化
"""

import sys
import os

# 添加路径
script_dir = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, script_dir)

from scenario_utils import (
    create_standard_system,
    run_steady_state,
    run_transient_simulation,
    create_animations,
    create_supplementary_plots,
    save_scenario_data,
    print_scenario_summary
)


def main():
    """主函数"""
    scenario_name = "Scenario 01: Upstream Flow Step"
    output_dir = os.path.join(os.path.dirname(script_dir), "results_scenarios", "scenario_01")
    
    print("\n" + "="*90)
    print(scenario_name.center(90))
    print("="*90)
    print("\n工况说明:")
    print("  初始流量: 30 m³/s")
    print("  扰动时刻: t=300s")
    print("  目标流量: 55 m³/s")
    print("  观测内容: 流量波传播、水位响应、泵站工作点")
    print("="*90)
    
    # 1. 创建系统
    solver, structures = create_standard_system()
    gate1, gate2, pump = structures
    
    # 2. 稳态求解
    steady_state = run_steady_state(solver, structures, Q_initial=30.0, h_downstream=2.0)
    
    # 3. 瞬态模拟 - 上游流量阶跃
    print("\n" + "="*80)
    print("设置瞬态边界条件".center(80))
    print("="*80)
    print("  t < 300s: Q_upstream = 30 m³/s")
    print("  t >=300s: Q_upstream = 55 m³/s")
    
    # 定义时间变化的边界条件
    def upstream_bc(t):
        if t < 300:
            return 30.0
        else:
            return 55.0
    
    # 重置求解器（使用稳态作为初值）
    solver.h = steady_state['h'].copy()
    solver.q = steady_state['q'].copy()
    
    # 运行瞬态（手动循环以应用时间变化的BC）
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
        
        # 更新上游边界条件
        Q_up = upstream_bc(t)
        solver.set_boundary_conditions(
            upstream_type='discharge',
            upstream_value=Q_up,
            downstream_type='depth',
            downstream_value=2.0
        )
        
        # 时间步进
        solver.step_preissmann(structures=structures, theta=0.6)
        
        # 保存
        if step % save_interval == 0:
            h_history.append(solver.h.copy())
            q_history.append(solver.q.copy())
            time_points.append(t)
            
            progress = (step / n_steps) * 100
            print(f"  t={t:6.0f}s ({progress:5.1f}%) | "
                  f"Q_up={Q_up:5.1f} m³/s | "
                  f"h_range=[{solver.h.min():.2f}, {solver.h.max():.2f}] m")
    
    print("✓ 瞬态模拟完成")
    
    import numpy as np
    time_points = np.array(time_points)
    h_history = np.array(h_history)
    q_history = np.array(q_history)
    
    # 4. 创建动画
    create_animations(
        scenario_name, output_dir,
        solver.x, solver.z, time_points, h_history, q_history,
        gate_positions=[gate1.position, gate2.position],
        pump_position=pump.position
    )
    
    # 5. 创建补充图表
    create_supplementary_plots(
        output_dir, solver.x, solver.z, time_points, h_history, q_history,
        gate_positions=[gate1.position, gate2.position],
        pump_position=pump.position
    )
    
    # 6. 保存数据
    save_scenario_data(
        output_dir, scenario_name, solver.x, solver.z,
        time_points, h_history, q_history, steady_state,
        description="Upstream flow step from 30 to 55 m³/s at t=300s"
    )
    
    # 7. 打印总结
    print_scenario_summary(scenario_name, steady_state, h_history, q_history, time_points)
    
    print(f"\n所有结果已保存到: {output_dir}")


if __name__ == "__main__":
    main()
