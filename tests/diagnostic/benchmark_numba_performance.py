#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Numba JIT性能基准测试

对比有/无Numba JIT的性能差异

作者: HydroClaude Team
日期: 2025-10-31
Phase: 6.5 - Numba JIT性能优化
"""

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..'))

import time
import numpy as np
try:
    from solvers.godunov_fvm_weno3 import GodunvFVMWENO3
except ImportError as e:
    print(f"Import error: {e}")
    print("Make sure project root is in sys.path")
    sys.exit(1)



def benchmark_with_without_numba(n_cells, n_steps, test_name):
    """
    对比有/无Numba JIT的性能

    Args:
        n_cells: 网格单元数
        n_steps: 运行步数
        test_name: 测试名称
    """
    print(f"\n{'='*80}")
    print(f"测试: {test_name}")
    print(f"网格: {n_cells} cells, 步数: {n_steps}")
    print(f"{'='*80}")

    # 测试参数
    L = 10000.0
    B = 10.0
    S0 = 0.001
    n = 0.025
    Q = 50.0
    h_init = 2.0

    # 边界条件
    bc_left = {'type': 'fixed_Q', 'Q': Q}
    bc_right = {'type': 'fixed_h', 'h': h_init}

    results = {}

    # 测试配置
    configs = [
        {"use_numba": True, "name": "Numba JIT优化"},
        {"use_numba": False, "name": "原生Python"},
    ]

    for config in configs:
        print(f"\n运行: {config['name']}")
        print(f"  use_numba={config['use_numba']}")

        # 创建求解器
        solver = GodunvFVMWENO3(
            width=B,
            length=L,
            n_cells=n_cells,
            manning_n=n,
            slope=S0,
            use_enhanced_bc=True,
            well_balanced=False,
            cfl=0.5,
            use_numba=config['use_numba']
        )

        # 初始条件
        h = np.ones(n_cells) * h_init
        Q_arr = np.ones(n_cells) * Q
        solver.initialize(h, Q_arr, bc_left, bc_right)

        # 预热（对于Numba，触发JIT编译）
        if config['use_numba']:
            print("  预热中（触发JIT编译）...")
            for _ in range(5):
                solver.step()

            # 重置求解器
            solver = GodunvFVMWENO3(
                width=B,
                length=L,
                n_cells=n_cells,
                manning_n=n,
                slope=S0,
                use_enhanced_bc=True,
                well_balanced=False,
                cfl=0.5,
                use_numba=config['use_numba']
            )
            solver.initialize(h, Q_arr, bc_left, bc_right)

        # 正式测试
        print("  正式测试中...")
        start_time = time.time()

        for i in range(n_steps):
            solver.step()

        elapsed_time = time.time() - start_time

        # 获取诊断信息
        diag = solver.get_diagnostics()

        # 保存结果
        results[config['name']] = {
            'time': elapsed_time,
            'sim_time': diag['t'],
            'steps': diag['step_count'],
            'mass_error': diag['mass_error'],
            'ms_per_step': elapsed_time / n_steps * 1000
        }

        print(f"  完成！")
        print(f"    运行时间: {elapsed_time:.3f}s")
        print(f"    模拟时间: {diag['t']:.2f}s")
        print(f"    步数: {diag['step_count']}")
        print(f"    质量误差: {diag['mass_error']:.3f}%")
        print(f"    性能: {elapsed_time/n_steps*1000:.2f}ms/step")

    # 计算加速比
    print(f"\n{'='*80}")
    print(f"性能对比")
    print(f"{'='*80}")

    time_numba = results["Numba JIT优化"]['time']
    time_python = results["原生Python"]['time']
    speedup = time_python / time_numba

    print(f"{'配置':<20} {'运行时间':<15} {'ms/step':<15}")
    print(f"{'-'*50}")
    print(f"{'Numba JIT优化':<20} {time_numba:<15.3f} {results['Numba JIT优化']['ms_per_step']:<15.2f}")
    print(f"{'原生Python':<20} {time_python:<15.3f} {results['原生Python']['ms_per_step']:<15.2f}")
    print(f"\n **加速比: {speedup:.2f}x**\n")

    if speedup >= 2.0:
        print(f" 优秀！达到2x以上加速")
    elif speedup >= 1.5:
        print(f" 良好！达到1.5x以上加速")
    elif speedup >= 1.2:
        print(f"️  一般，仅1.2-1.5x加速")
    else:
        print(f" 加速效果不明显（<1.2x）")

    return speedup


def run_all_benchmarks():
    """运行完整的基准测试套件"""
    print("="*80)
    print("Numba JIT性能基准测试套件")
    print("="*80)

    test_configs = [
        {"n_cells": 200, "n_steps": 100, "name": "小规模 (200 cells, 100 steps)"},
        {"n_cells": 500, "n_steps": 100, "name": "中等规模 (500 cells, 100 steps)"},
        {"n_cells": 1000, "n_steps": 50, "name": "大规模 (1000 cells, 50 steps)"},
    ]

    speedups = []

    for config in test_configs:
        speedup = benchmark_with_without_numba(
            config['n_cells'],
            config['n_steps'],
            config['name']
        )
        speedups.append(speedup)

    # 总结
    print(f"\n{'='*80}")
    print(f"总体性能总结")
    print(f"{'='*80}")

    avg_speedup = np.mean(speedups)

    print(f"\n各规模加速比:")
    for i, config in enumerate(test_configs):
        print(f"  {config['name']:<40} {speedups[i]:.2f}x")

    print(f"\n平均加速比: **{avg_speedup:.2f}x**")

    if avg_speedup >= 2.0:
        print(f"\n **成功！** Numba JIT实现了{avg_speedup:.2f}x加速，达到预期目标（2-5x）")
    elif avg_speedup >= 1.5:
        print(f"\n **有效！** Numba JIT实现了{avg_speedup:.2f}x加速")
    else:
        print(f"\n️  **改进有限** Numba JIT仅实现了{avg_speedup:.2f}x加速")

    print(f"\n{'='*80}")


if __name__ == '__main__':
    run_all_benchmarks()

    print(f"\n Numba JIT性能基准测试完成")
    print(f"{'='*80}")
