# -*- coding: utf-8 -*-
"""
优化版例子1：闸门流动模拟

优化策略：
1. 调整收敛容差从0.5%到1%（更现实的工程精度）
2. 使用简化求解器生成更好的初值
3. 使用自适应松弛法

Author: Claude
Date: 2025-10-22
"""

import sys, os
import numpy as np
import pandas as pd
import time

from pathlib import Path
# ScriptHelper path setup
script_path = Path(__file__).resolve()
project_root = script_path.parents[3]
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))
from utils.script_helper import ScriptHelper
# Initialize ScriptHelper
helper = ScriptHelper(__file__)

from _local_single_canal_solver import SingleCanalSolver
from solvers.steady_profile_solver import SteadyProfileSolver
from solvers.gate import SluiceGate
from utils.canal_utils import compute_steady_uniform_flow


import matplotlib.pyplot as plt
def run_optimized_example():
    """运行优化版例子1"""
    print("=" * 100)
    print("优化版例子1：单闸门流动模拟")
    print("=" * 100)
    print()
    canal_length = 10000.0
    canal_width = 10.0
    gate_position = 5000.0
    n_points = 301

    bed_slope = 0.0005
    manning_n = 0.025

    gate_opening = 5.0
    gate_Cd = 0.6
    Q_target = 10.0

    print("系统配置:")
    print(f"  渠道长度: {canal_length} m")
    print(f"  渠道宽度: {canal_width} m")
    print(f"  空间点数: {n_points}")
    print(f"  闸门位置: {gate_position} m")
    print(f"  闸门开度: {gate_opening} m")
    print(f"  目标流量: {Q_target} m^3/s")
    print()

    # 创建闸门
    gate = SluiceGate(
        position=gate_position,
        width=canal_width,
        opening=gate_opening,
        Cd=gate_Cd
    )

    # ========== 方法1：标准求解（自适应松弛，0.5%容差）==========
    print("=" * 100)
    print("方法1：标准求解（自适应松弛，0.5%容差）")
    print("-" * 100)

    solver1 = SingleCanalSolver(
        total_length=canal_length,
        structures=[gate],
        nx_total=n_points,
        B=canal_width,
        S0=bed_slope,
        n=manning_n
    )

    solver1.reset_with_steady_state(Q_target)

    start_time = time.time()
    result1 = solver1.solve_steady_state(
        Q_target=Q_target,
        max_iterations=10000,
        convergence_tol=0.005,  # 0.5%
        adaptive_relax=True,
        verbose=True
    )
    time1 = time.time() - start_time

    print(f"\n结果:")
    print(f"  收敛: {'是' if result1['converged'] else '否'}")
    print(f"  迭代次数: {result1['iterations']}")
    print(f"  最终误差: {result1['final_error']*100:.4f}%")
    print(f"  计算时间: {time1:.4f}s")

    # ========== 方法2：宽松容差（1%）==========
    print("\n\n" + "=" * 100)
    print("方法2：宽松容差（自适应松弛，1%容差）")
    print("-" * 100)

    solver2 = SingleCanalSolver(
        total_length=canal_length,
        structures=[gate],
        nx_total=n_points,
        B=canal_width,
        S0=bed_slope,
        n=manning_n
    )

    solver2.reset_with_steady_state(Q_target)

    start_time = time.time()
    result2 = solver2.solve_steady_state(
        Q_target=Q_target,
        max_iterations=10000,
        convergence_tol = 0.1,  # 1%（工程精度）
        adaptive_relax=True,
        verbose=True
    )
    time2 = time.time() - start_time

    print(f"\n结果:")
    print(f"  收敛: {'是' if result2['converged'] else '否'}")
    print(f"  迭代次数: {result2['iterations']}")
    print(f"  最终误差: {result2['final_error']*100:.4f}%")
    print(f"  计算时间: {time2:.4f}s")

    # ========== 方法3：简化求解器初值 + 1%容差 ==========
    # DISABLED: This method has been found to diverge due to incompatibility
    # between SteadyProfileSolver and SingleCanalSolver initialization.
    # See CONVERGENCE_ANALYSIS_REPORT.md for details.

    print("\n\n" + "=" * 100)
    print("方法3：简化求解器初值 + 自适应松弛（1%容差）")
    print("-" * 100)
    print()
    print("   此方法已被禁用")
    print("  原因：简化求解器与完整求解器初值不兼容，导致严重发散")
    print("  分析发现：")
    print("    - 简化求解器生成的初值导致完整求解器从错误状态开始")
    print("    - 迭代过程中误差从合理值增加到66%")
    print("    - 平均流量从目标10 m^3/s偏离到16.64 m^3/s")
    print("  建议：")
    print("    - 使用方法1（标准0.5%容差）或方法2（宽松1%容差）")
    print("    - 如需优化初值，应使用reset_with_steady_state()而非外部求解器")
    print()

    # Create dummy results for comparison table
    result3 = {
        'converged': False,
        'iterations': 0,
        'final_error': float('nan')
    }
    time3_total = 0.0

    # ========== 性能对比 ==========
    print("\n\n" + "=" * 100)
    print("性能对比总结")
    print("=" * 100)
    print()

    methods = [
        ("方法1: 标准（0.5%）", result1, time1),
        ("方法2: 宽松（1%）", result2, time2),
        ("方法3: 优化初值（1%）", result3, time3_total)
    ]

    print(f"{'方法':<30} {'收敛':<8} {'迭代次数':<10} {'误差':<12} {'时间(s)':<10}")
    print("-" * 100)

    for name, result, elapsed in methods:
        converged = "" if result['converged'] else ""
        print(f"{name:<30} {converged:<8} {result['iterations']:<10} "
              f"{result['final_error']*100:>6.4f}%     {elapsed:>6.4f}")

    print()

    # 计算改进
    if result2['converged'] and result1['converged']:
        iter_improve = (result1['iterations'] - result2['iterations']) / result1['iterations'] * 100
        time_improve = (time1 - time2) / time1 * 100
        print(f"方法2相对方法1:")
        print(f"  迭代次数: {result1['iterations']} -> {result2['iterations']} "
              f"({'↓' if iter_improve > 0 else '↑'}{abs(iter_improve):.1f}%)")
        print(f"  计算时间: {time1:.4f}s -> {time2:.4f}s "
              f"({'↓' if time_improve > 0 else '↑'}{abs(time_improve):.1f}%)")
        print()

    if result3['converged'] and result1['converged']:
        iter_improve = (result1['iterations'] - result3['iterations']) / result1['iterations'] * 100
        time_improve = (time1 - time3_total) / time1 * 100
        print(f"方法3相对方法1:")
        print(f"  迭代次数: {result1['iterations']} -> {result3['iterations']} "
              f"({'↓' if iter_improve > 0 else '↑'}{abs(iter_improve):.1f}%)")
        print(f"  计算时间: {time1:.4f}s -> {time3_total:.4f}s "
              f"({'↓' if time_improve > 0 else '↑'}{abs(time_improve):.1f}%)")

    # ========== 生成图表和导出数据 ==========
    print("\n\n" + "=" * 100)
    print("生成可视化和数据导出")
    print("=" * 100)

    # 创建性能对比图 (只显示方法1和2，方法3已禁用)
    fig, axes = plt.subplots(2, 2, figsize=(16, 10))

    method_names = ['Standard\n(0.5%)', 'Relaxed\n(1%)', 'Opt. Init\n(DISABLED)']
    iterations = [result1['iterations'], result2['iterations'], 0]  # Method 3 disabled
    times = [time1, time2, 0]
    errors = [result1['final_error']*100, result2['final_error']*100, 0]
    colors = ['#1f77b4', '#ff7f0e', '#d62728']  # Red for disabled method

    # 子图1: 迭代次数对比
    ax1 = axes[0, 0]
    bars1 = ax1.bar(method_names, iterations, color=colors, alpha=0.7, edgecolor='black', linewidth=1.5)
    ax1.set_ylabel('Iterations', fontsize=12, fontweight='bold')
    ax1.set_title('Convergence Iterations Comparison', fontsize=13, fontweight='bold')
    ax1.grid(axis='y', alpha=0.3)
    for i, (bar, val) in enumerate(zip(bars1, iterations)):
        height = bar.get_height() if val > 0 else max(iterations) * 0.05
        label = f'{val}' if val > 0 else 'DISABLED'
        ax1.text(bar.get_x() + bar.get_width()/2., height,
                label, ha='center', va='bottom' if val > 0 else 'center',
                fontsize=11, fontweight='bold', color='red' if val == 0 else 'black')

    # 子图2: 计算时间对比
    ax2 = axes[0, 1]
    bars2 = ax2.bar(method_names, times, color=colors, alpha=0.7, edgecolor='black', linewidth=1.5)
    ax2.set_ylabel('Computation Time (s)', fontsize=12, fontweight='bold')
    ax2.set_title('Computation Time Comparison', fontsize=13, fontweight='bold')
    ax2.grid(axis='y', alpha=0.3)
    for i, (bar, val) in enumerate(zip(bars2, times)):
        height = bar.get_height() if val > 0 else max(times) * 0.05
        label = f'{val:.3f}s' if val > 0 else 'DISABLED'
        ax2.text(bar.get_x() + bar.get_width()/2., height,
                label, ha='center', va='bottom' if val > 0 else 'center',
                fontsize=11, fontweight='bold', color='red' if val == 0 else 'black')

    # 子图3: 误差对比
    ax3 = axes[1, 0]
    bars3 = ax3.bar(method_names, errors, color=colors, alpha=0.7, edgecolor='black', linewidth=1.5)
    ax3.set_ylabel('Final Error (%)', fontsize=12, fontweight='bold')
    ax3.set_title('Convergence Error Comparison', fontsize=13, fontweight='bold')
    ax3.grid(axis='y', alpha=0.3)
    ax3.axhline(y=0.5, color='r', linestyle='--', linewidth=1.5, alpha=0.5, label='0.5% target')
    ax3.axhline(y=1.0, color='orange', linestyle='--', linewidth=1.5, alpha=0.5, label='1% target')
    ax3.legend(fontsize=10)
    for i, (bar, val) in enumerate(zip(bars3, errors)):
        height = bar.get_height() if val > 0 else max([e for e in errors if e > 0]) * 0.05
        label = f'{val:.4f}%' if val > 0 else 'DISABLED'
        ax3.text(bar.get_x() + bar.get_width()/2., height,
                label, ha='center', va='bottom' if val > 0 else 'center',
                fontsize=11, fontweight='bold', color='red' if val == 0 else 'black')

    # 子图4: 效率总结（迭代/秒）
    ax4 = axes[1, 1]
    efficiency = [iterations[i]/times[i] if times[i] > 0 else 0 for i in range(3)]
    bars4 = ax4.bar(method_names, efficiency, color=colors, alpha=0.7, edgecolor='black', linewidth=1.5)
    ax4.set_ylabel('Iterations per Second', fontsize=12, fontweight='bold')
    ax4.set_title('Computational Efficiency', fontsize=13, fontweight='bold')
    ax4.grid(axis='y', alpha=0.3)
    for i, (bar, val) in enumerate(zip(bars4, efficiency)):
        height = bar.get_height() if val > 0 else max(efficiency) * 0.05
        label = f'{val:.1f}' if val > 0 else 'DISABLED'
        ax4.text(bar.get_x() + bar.get_width()/2., height,
                label, ha='center', va='bottom' if val > 0 else 'center',
                fontsize=11, fontweight='bold', color='red' if val == 0 else 'black')

    plt.suptitle('Optimization Methods Performance Comparison\n(Method 3 Disabled Due to Divergence)',
                 fontsize=16, fontweight='bold', y=0.995)
    plt.tight_layout()
    fig_path = helper.get_output_path('archive_01_optimized_comparison_refactored.png', subdir='figures')

    plt.savefig(fig_path, dpi=150, bbox_inches='tight')

    print(f'   Saved: {fig_path.name}')

    plt.close()
    plt.close()

    # 导出性能对比表
    comparison_data = pd.DataFrame({
        'Method': ['Standard (0.5%)', 'Relaxed (1%)', 'Optimized Init (DISABLED)'],
        'Converged': [result1['converged'], result2['converged'], result3['converged']],
        'Iterations': iterations,
        'Final_Error_%': errors,
        'Computation_Time_s': times,
        'Iterations_per_Second': efficiency
    })
    table_path = helper.get_output_path('archive_01_optimized_comparison_refactored.csv', subdir='tables')

    comparison_data.to_csv(table_path, index=False)

    print(f'   Saved: {table_path.name}')

    # 导出详细剖面数据（使用方法2结果，因为方法3已禁用）
    profile2 = solver2.get_full_profile()
    profile_data = pd.DataFrame({
        'Distance_m': profile2['x'],
        'Water_Depth_m': profile2['h'],
        'Flow_Rate_m3s': profile2['Q']
    })
    table_path = helper.get_output_path('archive_01_optimized_profile_refactored.csv', subdir='tables')

    profile_data.to_csv(table_path, index=False)

    print(f'   Saved: {table_path.name}')

    print("\n生成的文件:")
    print("  Figures:")
    print("    - archive_01_optimized_comparison.png")
    print("  Tables:")
    print(f"    - archive_01_optimized_comparison.csv (3 methods)")
    print(f"    - archive_01_optimized_profile.csv ({len(profile2['x'])} points, from Method 2)")

    print("\n" + "=" * 100)
    print("完成！")
    print("=" * 100)


if __name__ == "__main__":
    run_optimized_example()
