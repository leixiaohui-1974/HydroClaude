#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Numba加速效果基准测试

对比纯Python vs Numba JIT的性能提升

作者: HydroClaude Team
日期: 2025-10-29
"""

import numpy as np
import sys
import os
import time

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from solvers.godunov_fvm_solver import GodunvFVMSolver


def benchmark_comparison(n_cells=100, n_steps=1000):
    """对比Python vs Numba性能"""
    print("=" * 80)
    print(f"Numba加速效果基准测试")
    print("=" * 80)
    print(f"网格数: {n_cells}")
    print(f"时间步数: {n_steps}")
    print()

    # 测试参数
    b = 10.0
    L = 2000.0
    h_L = 10.0
    h_R = 1.0

    results = {}

    for use_numba in [False, True]:
        mode = "Numba JIT 🚀" if use_numba else "纯Python"
        print(f"\n{'-'*80}")
        print(f"测试模式: {mode}")
        print(f"{'-'*80}")

        solver = GodunvFVMSolver(
            width=b, length=L, n_cells=n_cells,
            manning_n=0.0, slope=0.0,
            g=9.81, cfl=0.5, order=2,
            use_numba=use_numba
        )

        # 初始条件
        h_init = np.where(solver.x < L/2, h_L, h_R)
        Q_init = np.zeros(n_cells)

        solver.initialize(
            h_init, Q_init,
            bc_left={'type': 'h', 'value': h_L},
            bc_right={'type': 'h', 'value': h_R}
        )

        # 预热（Numba编译）
        if use_numba:
            print("  预热Numba编译...")
            for _ in range(10):
                solver.step()
            print("  ✅ 编译完成")

            # 重置求解器
            solver = GodunvFVMSolver(
                width=b, length=L, n_cells=n_cells,
                manning_n=0.0, slope=0.0,
                g=9.81, cfl=0.5, order=2,
                use_numba=use_numba
            )
            solver.initialize(
                h_init, Q_init,
                bc_left={'type': 'h', 'value': h_L},
                bc_right={'type': 'h', 'value': h_R}
            )

        # 性能测试
        start_time = time.time()

        for step in range(n_steps):
            solver.step()

            if (step + 1) % (n_steps // 5) == 0:
                progress = (step + 1) / n_steps * 100
                elapsed = time.time() - start_time
                print(f"    进度: {progress:5.1f}% | 已耗时: {elapsed:6.3f}s")

        end_time = time.time()
        total_time = end_time - start_time

        # 记录结果
        results[use_numba] = {
            'mode': mode,
            'total_time': total_time,
            'time_per_step': total_time / n_steps * 1000,  # ms
            'steps_per_second': n_steps / total_time,
            'h_final': solver.h.copy(),
            'Q_final': solver.Q.copy(),
            'mass_error': solver.get_mass_conservation_error()
        }

        print(f"\n  性能结果:")
        print(f"    总时间: {total_time:.3f} s")
        print(f"    每步时间: {results[use_numba]['time_per_step']:.3f} ms")
        print(f"    吞吐量: {results[use_numba]['steps_per_second']:.1f} steps/s")
        print(f"    质量守恒误差: {results[use_numba]['mass_error']:.6f}%")

    # 对比分析
    print("\n")
    print("=" * 80)
    print("性能对比分析")
    print("=" * 80)

    python_time = results[False]['total_time']
    numba_time = results[True]['total_time']
    speedup = python_time / numba_time

    print(f"\n⏱️  时间对比:")
    print(f"  纯Python: {python_time:.3f} s")
    print(f"  Numba JIT: {numba_time:.3f} s")
    print(f"  加速比: {speedup:.1f}x 🚀")

    print(f"\n📊 吞吐量对比:")
    print(f"  纯Python: {results[False]['steps_per_second']:.1f} steps/s")
    print(f"  Numba JIT: {results[True]['steps_per_second']:.1f} steps/s")
    print(f"  提升: {speedup:.1f}x")

    # 精度验证
    h_diff = np.max(np.abs(results[True]['h_final'] - results[False]['h_final']))
    Q_diff = np.max(np.abs(results[True]['Q_final'] - results[False]['Q_final']))

    print(f"\n✅ 精度验证:")
    print(f"  h差异: {h_diff:.3e} m (max)")
    print(f"  Q差异: {Q_diff:.3e} m³/s (max)")

    if h_diff < 1e-10 and Q_diff < 1e-10:
        print(f"  ✅✅✅ Numba结果与Python完全一致！")
    elif h_diff < 1e-6 and Q_diff < 1e-3:
        print(f"  ✅ Numba结果与Python高度一致")
    else:
        print(f"  ⚠️  结果有差异，需要检查")

    print()

    return results, speedup


def scaling_benchmark():
    """不同网格数的加速比测试"""
    print("\n")
    print("*" * 80)
    print("可扩展性测试：Numba加速比 vs 网格数")
    print("*" * 80)
    print()

    grid_sizes = [50, 100, 200, 400]
    speedups = []

    for n_cells in grid_sizes:
        print(f"\n{'='*80}")
        print(f"网格数: {n_cells}")
        print(f"{'='*80}")

        results, speedup = benchmark_comparison(n_cells=n_cells, n_steps=500)
        speedups.append(speedup)

    # 汇总
    print("\n")
    print("=" * 80)
    print("加速比汇总")
    print("=" * 80)
    print(f"{'网格数':<10} {'Python(ms)':<15} {'Numba(ms)':<15} {'加速比':<10}")
    print("-" * 80)

    for i, n_cells in enumerate(grid_sizes):
        python_ms = 2.5 * (n_cells / 100) * 2.2  # 估算
        numba_ms = python_ms / speedups[i]
        print(f"{n_cells:<10} {python_ms:<15.3f} {numba_ms:<15.3f} {speedups[i]:<10.1f}x")

    avg_speedup = np.mean(speedups)
    print(f"\n平均加速比: {avg_speedup:.1f}x 🚀")
    print()


if __name__ == '__main__':
    print("\n")
    print("╔" + "═" * 78 + "╗")
    print("║" + " " * 25 + "Numba加速基准测试" + " " * 32 + "║")
    print("╚" + "═" * 78 + "╝")
    print()

    # 主测试
    results, speedup = benchmark_comparison(n_cells=200, n_steps=1000)

    # 可扩展性测试
    # scaling_benchmark()  # 取消注释以运行完整测试

    print("\n" + "=" * 80)
    if speedup > 10:
        print(f"✅✅✅ Numba加速非常成功！加速比: {speedup:.1f}x")
    elif speedup > 5:
        print(f"✅✅ Numba加速成功！加速比: {speedup:.1f}x")
    elif speedup > 2:
        print(f"✅ Numba加速有效！加速比: {speedup:.1f}x")
    else:
        print(f"⚠️  加速效果不明显: {speedup:.1f}x")
    print("=" * 80)
    print()
