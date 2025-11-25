#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
性能分析工具

分析GodunvFVMSolver的性能瓶颈，为优化提供依据

作者: HydroClaude Team
日期: 2025-10-29
"""

import numpy as np
import sys
import os
import time
import cProfile
import pstats
from io import StringIO

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

try:
    from solvers.godunov_fvm_solver import GodunvFVMSolver
except ImportError as e:
    print(f"Import error: {e}")
    print("Make sure project root is in sys.path")
    sys.exit(1)



def benchmark_dam_break(n_cells=120, n_steps=1000, enable_profiling=False):
    """
    基准测试：溃坝问题

    Args:
        n_cells: 网格数
        n_steps: 时间步数
        enable_profiling: 是否启用详细profiling
    """
    print("=" * 80)
    print(f"性能基准测试：溃坝问题")
    print("=" * 80)
    print(f"网格数: {n_cells}")
    print(f"时间步数: {n_steps}")
    print()

    # 创建求解器
    b = 10.0
    L = 2000.0
    h_L = 10.0
    h_R = 1.0

    solver = GodunvFVMSolver(
        width=b, length=L, n_cells=n_cells,
        manning_n=0.0, slope=0.0,
        g=9.81, cfl=0.3, order=1
    )

    # 初始条件
    h_init = np.where(solver.x < L/2, h_L, h_R)
    Q_init = np.zeros(n_cells)

    solver.initialize(
        h_init, Q_init,
        bc_left={'type': 'h', 'value': h_L},
        bc_right={'type': 'h', 'value': h_R}
    )

    # 性能测试
    if enable_profiling:
        # 详细profiling
        pr = cProfile.Profile()
        pr.enable()

    start_time = time.time()

    for step in range(n_steps):
        solver.step()

        if (step + 1) % (n_steps // 10) == 0:
            progress = (step + 1) / n_steps * 100
            elapsed = time.time() - start_time
            print(f"  进度: {progress:5.1f}% | 已耗时: {elapsed:6.2f}s | 步数: {step+1}")

    end_time = time.time()

    if enable_profiling:
        pr.disable()

    # 结果
    total_time = end_time - start_time
    time_per_step = total_time / n_steps * 1000  # ms
    steps_per_second = n_steps / total_time

    print()
    print("性能结果:")
    print(f"  总时间: {total_time:.3f} s")
    print(f"  每步时间: {time_per_step:.3f} ms")
    print(f"  吞吐量: {steps_per_second:.1f} steps/s")
    print(f"  模拟时间: t = {solver.t:.2f} s")
    print()

    # 显示profiling结果
    if enable_profiling:
        print("=" * 80)
        print("详细性能分析（按累计时间排序，前20项）")
        print("=" * 80)
        s = StringIO()
        ps = pstats.Stats(pr, stream=s)
        ps.strip_dirs()
        ps.sort_stats('cumulative')
        ps.print_stats(20)
        print(s.getvalue())

        print("=" * 80)
        print("详细性能分析（按每次调用时间排序，前20项）")
        print("=" * 80)
        s = StringIO()
        ps = pstats.Stats(pr, stream=s)
        ps.strip_dirs()
        ps.sort_stats('time')
        ps.print_stats(20)
        print(s.getvalue())

    return {
        'total_time': total_time,
        'time_per_step': time_per_step,
        'steps_per_second': steps_per_second,
        'n_cells': n_cells,
        'n_steps': n_steps
    }


def scaling_test():
    """可扩展性测试：不同网格数的性能"""
    print("\n")
    print("*" * 80)
    print("可扩展性测试：网格数对性能的影响")
    print("*" * 80)
    print()

    grid_sizes = [50, 100, 200, 400]
    n_steps = 500  # 固定步数

    results = []

    for n_cells in grid_sizes:
        print(f"\n{'='*80}")
        print(f"测试网格数: {n_cells}")
        print(f"{'='*80}")

        result = benchmark_dam_break(n_cells=n_cells, n_steps=n_steps, enable_profiling=False)
        results.append(result)

        # 计算相对于50网格的加速比
        if len(results) > 1:
            baseline = results[0]['time_per_step']
            current = result['time_per_step']
            slowdown = current / baseline
            print(f"  相对于{grid_sizes[0]}网格的减速比: {slowdown:.2f}x")

    # 汇总
    print("\n")
    print("=" * 80)
    print("可扩展性测试总结")
    print("=" * 80)
    print(f"{'网格数':<10} {'每步时间(ms)':<15} {'吞吐量(steps/s)':<20} {'减速比':<10}")
    print("-" * 80)

    baseline = results[0]['time_per_step']
    for i, result in enumerate(results):
        slowdown = result['time_per_step'] / baseline
        print(f"{result['n_cells']:<10} {result['time_per_step']:<15.3f} {result['steps_per_second']:<20.1f} {slowdown:<10.2f}")

    print()


def hotspot_analysis():
    """热点分析：找出最耗时的函数"""
    print("\n")
    print("*" * 80)
    print("热点分析：详细profiling")
    print("*" * 80)
    print()

    benchmark_dam_break(n_cells=200, n_steps=500, enable_profiling=True)


if __name__ == '__main__':
    print("\n")
    print("╔" + "═" * 78 + "╗")
    print("║" + " " * 20 + "HydroClaude 性能分析工具" + " " * 32 + "║")
    print("╚" + "═" * 78 + "╝")
    print()

    # 1. 快速基准测试
    print("\n【第1步】快速基准测试（100网格，1000步）")
    benchmark_dam_break(n_cells=120, n_steps=1000, enable_profiling=False)

    # 2. 可扩展性测试
    print("\n【第2步】可扩展性测试")
    scaling_test()

    # 3. 热点分析
    print("\n【第3步】热点分析")
    hotspot_analysis()

    print("\n")
    print("=" * 80)
    print(" 性能分析完成！")
    print("=" * 80)
    print()
    print("建议：")
    print("1. 查看cumulative时间，找出最耗时的函数")
    print("2. 考虑使用Numba JIT编译优化热点函数")
    print("3. 向量化循环操作")
    print()
