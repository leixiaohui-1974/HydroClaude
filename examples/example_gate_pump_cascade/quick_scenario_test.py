#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
串联明渠闸泵群系统 - 快速工况测试（精简版）

优化：
1. 减少模拟时间到 1200秒（20分钟）
2. 选择8个代表性工况
3. 减少网格点数到 301
4. 增大时间步长到 1.0s

作者: Claude
日期: 2025-10-26
"""

import sys
import warnings
warnings.filterwarnings("ignore")
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

# 导入完整测试脚本的所有函数
from comprehensive_scenario_test import *

# 覆盖关键参数
QUICK_SCENARIOS = {
    # 上游流量扰动
    'S01_flow_step_small': SCENARIOS['S01_flow_step_small'].copy(),
    'S03_flow_step_large': SCENARIOS['S03_flow_step_large'].copy(),
    'S05_flow_fluctuation': SCENARIOS['S05_flow_fluctuation'].copy(),
    
    # 下游水位扰动
    'S06_downstream_h_step_up': SCENARIOS['S06_downstream_h_step_up'].copy(),
    
    # 闸门开度调节
    'S10_gate1_close_more': SCENARIOS['S10_gate1_close_more'].copy(),
    
    # 多重扰动
    'S13_combined_flow_and_gate': SCENARIOS['S13_combined_flow_and_gate'].copy(),
    
    # 极端工况
    'S16_extreme_flow_increase': SCENARIOS['S16_extreme_flow_increase'].copy(),
    'S17_rapid_gate_closure': SCENARIOS['S17_rapid_gate_closure'].copy(),
}

# 修改所有工况的模拟时间
for config in QUICK_SCENARIOS.values():
    config['t_total'] = 1200.0  # 减少到1200秒

def run_single_scenario_quick(scenario_id, config, output_base_dir):
    """
    快速运行单个工况（使用更粗的网格和更大的时间步长）
    """
    print("\n" + "="*100)
    print(f"{config['name']} [快速模式]".center(100))
    print("="*100)
    print(f"\n{config['description']}")
    print(f"类别: {config['category']}")
    print("-"*100)
    
    start_time = time.time()
    
    # ==================== 系统参数（优化版）====================
    L_total = 100000.0
    B = 15.0
    S0 = 0.0001
    n = 0.025
    nx = 301  # 减少网格点（从501到301）
    dt = 1.0  # 增大时间步长（从0.5到1.0）
    
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
    print(f"   时间步长: {dt}s (快速模式)")
    
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
            convergence_tol = 0.1,  # 放宽收敛判据（快速模式）
            max_iterations=1000,  # 减少最大迭代次数
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
    
    t_total = config.get('t_total', 1200.0)
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
                max_iter=15,  # 减少迭代次数（快速模式）
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
                print(f"   出现负水深 (t={t_current:.1f}s, min_h={np.min(h_new):.3f}m)")
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
                
                if save_idx % 5 == 0:
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
        import traceback
        traceback.print_exc()
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


def main():
    """主函数"""
    print("\n" + "="*100)
    print("串联明渠闸泵群系统 - 快速工况测试（精简版）".center(100))
    print("="*100)
    print(f"\n开始时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"共设计 {len(QUICK_SCENARIOS)} 个代表性工况")
    print("\n优化设置:")
    print("  - 模拟时间: 1200秒 (20分钟)")
    print("  - 网格点数: 301 (减少约40%)")
    print("  - 时间步长: 1.0秒 (加快2倍)")
    print("  - 预计总耗时: 20-30分钟")
    
    categories = {}
    for scenario_id, config in QUICK_SCENARIOS.items():
        cat = config['category']
        categories[cat] = categories.get(cat, 0) + 1
    
    print("\n工况分类统计:")
    for cat, count in categories.items():
        print(f"  - {cat}: {count}个")
    
    print("\n" + "="*100)
    
    # 创建输出基础目录
    base_dir = os.path.dirname(os.path.abspath(__file__))
    output_base_dir = os.path.join(base_dir, "results_quick")
    os.makedirs(output_base_dir, exist_ok=True)
    
    # 运行所有工况
    results = []
    start_time_total = time.time()
    
    for i, (scenario_id, config) in enumerate(QUICK_SCENARIOS.items(), 1):
        print(f"\n进度: [{i}/{len(QUICK_SCENARIOS)}]")
        
        result = run_single_scenario_quick(scenario_id, config, output_base_dir)
        results.append(result)
        
        # 短暂延迟
        time.sleep(0.5)
    
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
    
    # 生成总结报告（使用与完整版相同的函数）
    summary_report_path = os.path.join(output_base_dir, "QUICK_TEST_SUMMARY.md")
    
    with open(summary_report_path, 'w', encoding='utf-8') as f:
        f.write(f"# 串联明渠闸泵群系统 - 快速工况测试总结\n\n")
        f.write(f"**测试模式**: 快速测试（精简版）\n\n")
        f.write(f"**测试日期**: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n")
        f.write(f"**总耗时**: {elapsed_total:.1f}秒 ({elapsed_total/60:.1f}分钟)\n\n")
        f.write("---\n\n")
        
        f.write(f"## 测试设置\n\n")
        f.write(f"- **模拟时间**: 1200秒 (20分钟)\n")
        f.write(f"- **网格点数**: 301点\n")
        f.write(f"- **时间步长**: 1.0秒\n")
        f.write(f"- **工况数**: {len(QUICK_SCENARIOS)}个代表性工况\n\n")
        
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
                name = QUICK_SCENARIOS[scenario_id]['name']
                elapsed = result['elapsed_time']
                mass_error = result['analysis']['mass_conservation_error']
                h_var = result['analysis']['h_variation_coefficient']
                
                status = ""
                mass_status = "" if mass_error < 0.01 else ""
                stable_status = "" if h_var < 0.05 else ""
                
                f.write(f"| {scenario_id} | {name} | {status} | {elapsed:.1f} | {mass_error:.6f} {mass_status} | {h_var:.6f} {stable_status} |\n")
            else:
                scenario_id = result.get('scenario_id', '?')
                name = QUICK_SCENARIOS.get(scenario_id, {}).get('name', '未知')
                error = result.get('error', '未知错误')
                stage = result.get('stage', '?')
                f.write(f"| {scenario_id} | {name} |  | - | 失败于{stage}: {error[:30]} | - |\n")
        
        f.write("\n---\n\n")
        
        if n_success > 0:
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
        
        f.write(f"## 结论\n\n")
        
        if n_success == len(results):
            f.write(f"###  快速测试全部通过\n\n")
            f.write(f"所有{len(results)}个代表性工况均运行成功。\n\n")
        else:
            f.write(f"###  快速测试需要关注\n\n")
            if n_failed > 0:
                f.write(f"- {n_failed}个工况运行失败，需要检查\n\n")
        
        f.write("---\n\n")
        f.write(f"*报告自动生成于 {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}*\n")
    
    print(f"\n 总结报告已生成: {summary_report_path}")
    
    # 生成JSON格式结果
    json_results = []
    for result in results:
        if result.get('success', False):
            json_results.append({
                'scenario_id': result['scenario_id'],
                'name': QUICK_SCENARIOS[result['scenario_id']]['name'],
                'category': QUICK_SCENARIOS[result['scenario_id']]['category'],
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
        print(" 所有快速测试完成！".center(100))
    else:
        print(f" {n_success}/{len(results)} 工况完成".center(100))
    print("="*100 + "\n")
    
    return results


if __name__ == "__main__":
    results = main()
