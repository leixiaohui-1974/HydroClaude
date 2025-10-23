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
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
import time
from solvers.single_canal_solver import SingleCanalSolver
from solvers.steady_profile_solver import SteadyProfileSolver
from solvers.gate import SluiceGate
from utils.canal_utils import compute_steady_uniform_flow

from output_helper import get_output_path, save_figure, save_table, save_animation


def run_optimized_example():
    """运行优化版例子1"""

    print("=" * 100)
    print("优化版例子1：单闸门流动模拟")
    print("=" * 100)
    print()

    # 系统配置
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
    print(f"  目标流量: {Q_target} m³/s")
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
        convergence_tol=0.01,  # 1%（工程精度）
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
    print("\n\n" + "=" * 100)
    print("方法3：简化求解器初值 + 自适应松弛（1%容差）")
    print("-" * 100)

    # 步骤1：使用简化求解器快速预求解
    print("\n步骤1：使用简化求解器预求解...")

    profile_solver = SteadyProfileSolver(
        length=canal_length,
        B=canal_width,
        S0=bed_slope,
        n=manning_n
    )

    h_downstream = compute_steady_uniform_flow(Q_target, canal_width, bed_slope, manning_n)

    start_time_init = time.time()
    result_init = profile_solver.solve_with_single_gate(
        Q=Q_target,
        h_downstream=h_downstream,
        gate_position=gate_position,
        gate=gate,
        nx=n_points
    )
    time_init = time.time() - start_time_init

    print(f"  简化求解器完成: {time_init:.4f}s")
    print(f"  闸前水深: {result_init['h_gate_up']:.4f} m")
    print(f"  闸后水深: {result_init['h_gate_down']:.4f} m")

    # 步骤2：使用预求解结果作为初值
    print("\n步骤2：使用预求解结果精细求解...")

    solver3 = SingleCanalSolver(
        total_length=canal_length,
        structures=[gate],
        nx_total=n_points,
        B=canal_width,
        S0=bed_slope,
        n=manning_n
    )

    # 使用简化求解器的结果作为初值
    solver3.solver.h[:] = result_init['h']
    solver3.solver.Q[:] = result_init['Q']

    start_time = time.time()
    result3 = solver3.solve_steady_state(
        Q_target=Q_target,
        max_iterations=10000,
        convergence_tol=0.01,  # 1%
        adaptive_relax=True,
        verbose=True
    )
    time3 = time.time() - start_time
    time3_total = time3 + time_init

    print(f"\n结果:")
    print(f"  收敛: {'是' if result3['converged'] else '否'}")
    print(f"  迭代次数: {result3['iterations']}")
    print(f"  最终误差: {result3['final_error']*100:.4f}%")
    print(f"  精细求解时间: {time3:.4f}s")
    print(f"  总时间（含预求解）: {time3_total:.4f}s")

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
        converged = "✓" if result['converged'] else "✗"
        print(f"{name:<30} {converged:<8} {result['iterations']:<10} "
              f"{result['final_error']*100:>6.4f}%     {elapsed:>6.4f}")

    print()

    # 计算改进
    if result2['converged'] and result1['converged']:
        iter_improve = (result1['iterations'] - result2['iterations']) / result1['iterations'] * 100
        time_improve = (time1 - time2) / time1 * 100
        print(f"方法2相对方法1:")
        print(f"  迭代次数: {result1['iterations']} → {result2['iterations']} "
              f"({'↓' if iter_improve > 0 else '↑'}{abs(iter_improve):.1f}%)")
        print(f"  计算时间: {time1:.4f}s → {time2:.4f}s "
              f"({'↓' if time_improve > 0 else '↑'}{abs(time_improve):.1f}%)")
        print()

    if result3['converged'] and result1['converged']:
        iter_improve = (result1['iterations'] - result3['iterations']) / result1['iterations'] * 100
        time_improve = (time1 - time3_total) / time1 * 100
        print(f"方法3相对方法1:")
        print(f"  迭代次数: {result1['iterations']} → {result3['iterations']} "
              f"({'↓' if iter_improve > 0 else '↑'}{abs(iter_improve):.1f}%)")
        print(f"  计算时间: {time1:.4f}s → {time3_total:.4f}s "
              f"({'↓' if time_improve > 0 else '↑'}{abs(time_improve):.1f}%)")

    # ========== 生成图表和导出数据 ==========
    print("\n\n" + "=" * 100)
    print("生成可视化和数据导出")
    print("=" * 100)

    # 创建性能对比图
    fig, axes = plt.subplots(2, 2, figsize=(16, 10))

    method_names = ['Standard\n(0.5%)', 'Relaxed\n(1%)', 'Optimized Init\n(1%)']
    iterations = [result1['iterations'], result2['iterations'], result3['iterations']]
    times = [time1, time2, time3_total]
    errors = [result1['final_error']*100, result2['final_error']*100, result3['final_error']*100]
    colors = ['#1f77b4', '#ff7f0e', '#2ca02c']

    # 子图1: 迭代次数对比
    ax1 = axes[0, 0]
    bars1 = ax1.bar(method_names, iterations, color=colors, alpha=0.7, edgecolor='black', linewidth=1.5)
    ax1.set_ylabel('Iterations', fontsize=12, fontweight='bold')
    ax1.set_title('Convergence Iterations Comparison', fontsize=13, fontweight='bold')
    ax1.grid(axis='y', alpha=0.3)
    for i, (bar, val) in enumerate(zip(bars1, iterations)):
        height = bar.get_height()
        ax1.text(bar.get_x() + bar.get_width()/2., height,
                f'{val}', ha='center', va='bottom', fontsize=11, fontweight='bold')

    # 子图2: 计算时间对比
    ax2 = axes[0, 1]
    bars2 = ax2.bar(method_names, times, color=colors, alpha=0.7, edgecolor='black', linewidth=1.5)
    ax2.set_ylabel('Computation Time (s)', fontsize=12, fontweight='bold')
    ax2.set_title('Computation Time Comparison', fontsize=13, fontweight='bold')
    ax2.grid(axis='y', alpha=0.3)
    for i, (bar, val) in enumerate(zip(bars2, times)):
        height = bar.get_height()
        ax2.text(bar.get_x() + bar.get_width()/2., height,
                f'{val:.3f}s', ha='center', va='bottom', fontsize=11, fontweight='bold')

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
        height = bar.get_height()
        ax3.text(bar.get_x() + bar.get_width()/2., height,
                f'{val:.4f}%', ha='center', va='bottom', fontsize=11, fontweight='bold')

    # 子图4: 效率总结（迭代/秒）
    ax4 = axes[1, 1]
    efficiency = [iterations[i]/times[i] for i in range(3)]
    bars4 = ax4.bar(method_names, efficiency, color=colors, alpha=0.7, edgecolor='black', linewidth=1.5)
    ax4.set_ylabel('Iterations per Second', fontsize=12, fontweight='bold')
    ax4.set_title('Computational Efficiency', fontsize=13, fontweight='bold')
    ax4.grid(axis='y', alpha=0.3)
    for i, (bar, val) in enumerate(zip(bars4, efficiency)):
        height = bar.get_height()
        ax4.text(bar.get_x() + bar.get_width()/2., height,
                f'{val:.1f}', ha='center', va='bottom', fontsize=11, fontweight='bold')

    plt.suptitle('Optimization Methods Performance Comparison', fontsize=16, fontweight='bold', y=0.995)
    plt.tight_layout()
    save_figure(fig, 'archive_01_optimized_comparison.png')
    plt.close()

    # 导出性能对比表
    comparison_data = pd.DataFrame({
        'Method': ['Standard (0.5%)', 'Relaxed (1%)', 'Optimized Init (1%)'],
        'Converged': [result1['converged'], result2['converged'], result3['converged']],
        'Iterations': iterations,
        'Final_Error_%': errors,
        'Computation_Time_s': times,
        'Iterations_per_Second': efficiency
    })
    save_table(comparison_data, 'archive_01_optimized_comparison.csv', index=False)

    # 导出详细剖面数据（方法3最优结果）
    profile3 = solver3.get_full_profile()
    profile_data = pd.DataFrame({
        'Distance_m': profile3['x'],
        'Water_Depth_m': profile3['h'],
        'Flow_Rate_m3s': profile3['Q']
    })
    save_table(profile_data, 'archive_01_optimized_profile.csv', index=False)

    print("\n生成的文件:")
    print("  Figures:")
    print("    - archive_01_optimized_comparison.png")
    print("  Tables:")
    print(f"    - archive_01_optimized_comparison.csv (3 methods)")
    print(f"    - archive_01_optimized_profile.csv ({len(profile3['x'])} points)")

    print("\n" + "=" * 100)
    print("完成！")
    print("=" * 100)


if __name__ == "__main__":
    run_optimized_example()
