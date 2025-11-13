#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
性能对比测试：全面评估不同求解策略

对比方法：
1. 固定松弛因子
2. 自适应松弛因子（Aitken加速）

测试场景：
- 例子1：单闸门
- 例子2-场景1：三闸门串联
- 例子2-场景2：混合结构

作者: Claude
日期: 2025-10-22
"""

import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

import numpy as np
import time
import matplotlib.pyplot as plt
# DEPRECATED: Use HydrostaticCanalSolver instead
# # DEPRECATED: Use HydrostaticCanalSolver instead
# from solvers.single_canal_solver import SingleCanalSolver
from solvers.gate import SluiceGate, BroadCrestedWeir, Orifice


def run_performance_comparison():
    """运行性能对比测试"""

    print("=" * 100)
    print("性能对比测试：自适应松弛 vs 固定松弛")
    print("=" * 100)
    print()

    # 通用参数
    canal_length = 10000.0
    canal_width = 10.0
    n_points = 301
    Q_target = 10.0

    all_results = {}

    # ==================== 测试1：单闸门 ====================
    print("\n" + "=" * 100)
    print("测试1：单闸门（例子1）")
    print("=" * 100)

    gate = SluiceGate(position=5000.0, width=canal_width, opening=5.0, Cd=0.6)

    results_test1 = {}

    for adaptive in [False, True]:
        method_name = "自适应松弛" if adaptive else "固定松弛"
        print(f"\n{method_name}:")
        print("-" * 100)

        solver = SingleCanalSolver(
            total_length=canal_length,
            structures=[gate],
            nx_total=n_points,
            B=canal_width,
            S0=0.0005,
            n=0.025
        )

        solver.reset_with_steady_state(Q_target)

        start_time = time.time()
        result = solver.solve_steady_state(
            Q_target=Q_target,
            max_iterations=10000,
            convergence_tol=0.005,
            check_interval=1000,
            adaptive_relax=adaptive,
            verbose=True
        )
        elapsed_time = time.time() - start_time

        results_test1[method_name] = {
            'converged': result['converged'],
            'iterations': result['iterations'],
            'final_error': result['final_error'],
            'elapsed_time': elapsed_time,
            'gate_flows': result['gate_flows']
        }

    all_results["单闸门"] = results_test1

    # ==================== 测试2：三闸门串联 ====================
    print("\n\n" + "=" * 100)
    print("测试2：三闸门串联（例子2-场景1）")
    print("=" * 100)

    gate1 = SluiceGate(position=2500.0, width=canal_width, opening=4.5, Cd=0.6)
    gate2 = SluiceGate(position=5000.0, width=canal_width, opening=4.0, Cd=0.6)
    gate3 = SluiceGate(position=7500.0, width=canal_width, opening=5.0, Cd=0.6)

    results_test2 = {}

    for adaptive in [False, True]:
        method_name = "自适应松弛" if adaptive else "固定松弛"
        print(f"\n{method_name}:")
        print("-" * 100)

        solver = SingleCanalSolver(
            total_length=canal_length,
            structures=[gate1, gate2, gate3],
            nx_total=n_points,
            B=canal_width,
            S0=0.0005,
            n=0.025
        )

        solver.reset_with_steady_state(Q_target)

        start_time = time.time()
        result = solver.solve_steady_state(
            Q_target=Q_target,
            max_iterations=10000,
            convergence_tol=0.005,
            check_interval=1000,
            adaptive_relax=adaptive,
            verbose=True
        )
        elapsed_time = time.time() - start_time

        results_test2[method_name] = {
            'converged': result['converged'],
            'iterations': result['iterations'],
            'final_error': result['final_error'],
            'elapsed_time': elapsed_time,
            'gate_flows': result['gate_flows']
        }

    all_results["三闸门串联"] = results_test2

    # ==================== 测试3：混合结构 ====================
    print("\n\n" + "=" * 100)
    print("测试3：混合结构（例子2-场景2）")
    print("=" * 100)

    gate_mixed = SluiceGate(position=2500.0, width=canal_width, opening=3.5, Cd=0.6)
    weir = BroadCrestedWeir(position=5000.0, width=canal_width, crest_height=0.5, Cd=0.848)
    orifice = Orifice(position=7500.0, width=4.0, height=2.0, bottom_elevation=0.2, Cd=0.61)

    results_test3 = {}

    for adaptive in [False, True]:
        method_name = "自适应松弛" if adaptive else "固定松弛"
        print(f"\n{method_name}:")
        print("-" * 100)

        solver = SingleCanalSolver(
            total_length=canal_length,
            structures=[gate_mixed, weir, orifice],
            nx_total=n_points,
            B=canal_width,
            S0=0.0005,
            n=0.025
        )

        solver.reset_with_steady_state(Q_target)

        start_time = time.time()
        result = solver.solve_steady_state(
            Q_target=Q_target,
            max_iterations=10000,
            convergence_tol=0.005,
            check_interval=1000,
            adaptive_relax=adaptive,
            verbose=True
        )
        elapsed_time = time.time() - start_time

        results_test3[method_name] = {
            'converged': result['converged'],
            'iterations': result['iterations'],
            'final_error': result['final_error'],
            'elapsed_time': elapsed_time,
            'gate_flows': result['gate_flows']
        }

    all_results["混合结构"] = results_test3

    # ==================== 生成汇总报告 ====================
    print("\n\n" + "=" * 100)
    print("汇总报告")
    print("=" * 100)
    print()

    # 表格
    print(f"{'测试场景':<20} {'方法':<15} {'收敛':<8} {'迭代次数':<10} {'误差':<12} {'时间(s)':<10}")
    print("-" * 100)

    for scenario_name, scenario_results in all_results.items():
        for method_name, method_results in scenario_results.items():
            converged_str = "" if method_results['converged'] else ""
            print(f"{scenario_name:<20} {method_name:<15} {converged_str:<8} {method_results['iterations']:<10} "
                  f"{method_results['final_error']*100:>6.4f}%     "
                  f"{method_results['elapsed_time']:>6.2f}s")
        print()

    # 性能改进分析
    print("\n性能改进分析（自适应相对于固定）：")
    print("-" * 100)

    improvements = {}

    for scenario_name, scenario_results in all_results.items():
        fixed = scenario_results['固定松弛']
        adaptive = scenario_results['自适应松弛']

        if fixed['converged'] and adaptive['converged']:
            iter_improvement = (fixed['iterations'] - adaptive['iterations']) / fixed['iterations'] * 100
            time_improvement = (fixed['elapsed_time'] - adaptive['elapsed_time']) / fixed['elapsed_time'] * 100

            improvements[scenario_name] = {
                'iter_improvement': iter_improvement,
                'time_improvement': time_improvement
            }

            print(f"\n{scenario_name}:")
            print(f"  迭代次数: {fixed['iterations']} → {adaptive['iterations']} "
                  f"({'↓' if iter_improvement > 0 else '↑'}{abs(iter_improvement):.1f}%)")
            print(f"  计算时间: {fixed['elapsed_time']:.2f}s → {adaptive['elapsed_time']:.2f}s "
                  f"({'↓' if time_improvement > 0 else '↑'}{abs(time_improvement):.1f}%)")
        elif not fixed['converged'] and adaptive['converged']:
            print(f"\n{scenario_name}:")
            print(f"  固定松弛未收敛，自适应松弛成功收敛！")
            print(f"  自适应结果: {adaptive['iterations']}次迭代, {adaptive['elapsed_time']:.2f}s")

    # ==================== 生成性能对比图 ====================
    print("\n\n生成性能对比可视化...")

    fig, ((ax1, ax2), (ax3, ax4)) = plt.subplots(2, 2, figsize=(16, 12))

    scenarios = list(all_results.keys())
    x_pos = np.arange(len(scenarios))
    width = 0.35

    # 提取数据
    iterations_fixed = [all_results[s]['固定松弛']['iterations'] for s in scenarios]
    iterations_adaptive = [all_results[s]['自适应松弛']['iterations'] for s in scenarios]

    times_fixed = [all_results[s]['固定松弛']['elapsed_time'] for s in scenarios]
    times_adaptive = [all_results[s]['自适应松弛']['elapsed_time'] for s in scenarios]

    errors_fixed = [all_results[s]['固定松弛']['final_error']*100 for s in scenarios]
    errors_adaptive = [all_results[s]['自适应松弛']['final_error']*100 for s in scenarios]

    # 子图1：迭代次数对比
    ax1.bar(x_pos - width/2, iterations_fixed, width, label='固定松弛', color='steelblue', alpha=0.8)
    ax1.bar(x_pos + width/2, iterations_adaptive, width, label='自适应松弛', color='darkorange', alpha=0.8)
    ax1.set_xlabel('测试场景', fontsize=12)
    ax1.set_ylabel('迭代次数', fontsize=12)
    ax1.set_title('迭代次数对比', fontsize=14, fontweight='bold')
    ax1.set_xticks(x_pos)
    ax1.set_xticklabels(scenarios, rotation=15, ha='right')
    ax1.legend(fontsize=11)
    ax1.grid(True, alpha=0.3, axis='y')

    # 子图2：计算时间对比
    ax2.bar(x_pos - width/2, times_fixed, width, label='固定松弛', color='steelblue', alpha=0.8)
    ax2.bar(x_pos + width/2, times_adaptive, width, label='自适应松弛', color='darkorange', alpha=0.8)
    ax2.set_xlabel('测试场景', fontsize=12)
    ax2.set_ylabel('计算时间 (s)', fontsize=12)
    ax2.set_title('计算时间对比', fontsize=14, fontweight='bold')
    ax2.set_xticks(x_pos)
    ax2.set_xticklabels(scenarios, rotation=15, ha='right')
    ax2.legend(fontsize=11)
    ax2.grid(True, alpha=0.3, axis='y')

    # 子图3：最终误差对比
    ax3.bar(x_pos - width/2, errors_fixed, width, label='固定松弛', color='steelblue', alpha=0.8)
    ax3.bar(x_pos + width/2, errors_adaptive, width, label='自适应松弛', color='darkorange', alpha=0.8)
    ax3.set_xlabel('测试场景', fontsize=12)
    ax3.set_ylabel('流量守恒误差 (%)', fontsize=12)
    ax3.set_title('收敛精度对比', fontsize=14, fontweight='bold')
    ax3.set_xticks(x_pos)
    ax3.set_xticklabels(scenarios, rotation=15, ha='right')
    ax3.legend(fontsize=11)
    ax3.grid(True, alpha=0.3, axis='y')

    # 子图4：性能改进百分比
    iter_improvements = [improvements.get(s, {}).get('iter_improvement', 0) for s in scenarios]
    time_improvements = [improvements.get(s, {}).get('time_improvement', 0) for s in scenarios]

    ax4.bar(x_pos - width/2, iter_improvements, width, label='迭代次数', color='green', alpha=0.8)
    ax4.bar(x_pos + width/2, time_improvements, width, label='计算时间', color='purple', alpha=0.8)
    ax4.axhline(y=0, color='k', linestyle='--', linewidth=1)
    ax4.set_xlabel('测试场景', fontsize=12)
    ax4.set_ylabel('性能改进 (%)', fontsize=12)
    ax4.set_title('自适应松弛的性能改进', fontsize=14, fontweight='bold')
    ax4.set_xticks(x_pos)
    ax4.set_xticklabels(scenarios, rotation=15, ha='right')
    ax4.legend(fontsize=11)
    ax4.grid(True, alpha=0.3, axis='y')

    plt.tight_layout()
    os.makedirs('reports/figures', exist_ok=True)
    fig_path = 'reports/figures/performance_comparison_adaptive_vs_fixed.png'
    plt.savefig(fig_path, dpi=150, bbox_inches='tight')
    plt.close(fig)

    print(f"   性能对比图已保存: {fig_path}")

    print("\n" + "=" * 100)
    print("测试完成！")
    print("=" * 100)


if __name__ == "__main__":
    run_performance_comparison()
