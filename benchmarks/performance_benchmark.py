#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
性能基准测试脚本
Performance Benchmark Script

对比Numba JIT加速前后的性能差异

Author: HydroClaude Team
Date: 2025-10-30
"""

import sys
import os
import time
import numpy as np
import matplotlib.pyplot as plt

# 添加项目根目录到路径
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from network.pressure_pipe import PressurePipe
from utils.performance import (
    friction_factor_colebrook_jit,
    head_loss_complete_jit
)


def benchmark_colebrook_white():
    """基准测试：Colebrook-White摩阻系数计算"""
    print("\n" + "="*80)
    print("【1】Colebrook-White摩阻系数计算性能测试")
    print("="*80)

    # 创建测试管道
    pipe = PressurePipe('test', diameter=0.3, length=100, roughness=0.00026)

    # 测试流量范围
    Q_values = np.linspace(0.01, 1.0, 1000)

    # 原始版本
    print("\n原始版本 (无JIT):")
    start = time.time()
    for Q in Q_values:
        _ = pipe.friction_factor_colebrook(Q)
    time_orig = time.time() - start
    print(f"  耗时: {time_orig:.4f}s")

    # JIT版本
    print("\nNumba JIT版本:")
    start = time.time()
    for Q in Q_values:
        _ = friction_factor_colebrook_jit(Q, pipe.D, pipe.epsilon, 10, 1e-6)
    time_jit = time.time() - start
    print(f"  耗时: {time_jit:.4f}s")

    speedup = time_orig / time_jit if time_jit > 0 else 0
    print(f"\n✅ 加速比: {speedup:.1f}x")

    return {
        'test': 'Colebrook-White',
        'samples': len(Q_values),
        'time_orig': time_orig,
        'time_jit': time_jit,
        'speedup': speedup
    }


def benchmark_head_loss():
    """基准测试：水头损失计算"""
    print("\n" + "="*80)
    print("【2】水头损失计算性能测试")
    print("="*80)

    # 创建测试管道
    pipe = PressurePipe('test', diameter=0.3, length=100, roughness=0.00026)

    # 测试流量范围
    Q_values = np.linspace(0.01, 1.0, 1000)

    # 原始版本
    print("\n原始版本 (无JIT):")
    start = time.time()
    for Q in Q_values:
        _ = pipe.head_loss(Q)
    time_orig = time.time() - start
    print(f"  耗时: {time_orig:.4f}s")

    # JIT版本
    print("\nNumba JIT版本:")
    start = time.time()
    for Q in Q_values:
        _ = head_loss_complete_jit(Q, pipe.D, pipe.L, pipe.epsilon, pipe.K_minor, 10, 1e-6)
    time_jit = time.time() - start
    print(f"  耗时: {time_jit:.4f}s")

    speedup = time_orig / time_jit if time_jit > 0 else 0
    print(f"\n✅ 加速比: {speedup:.1f}x")

    return {
        'test': 'Head Loss',
        'samples': len(Q_values),
        'time_orig': time_orig,
        'time_jit': time_jit,
        'speedup': speedup
    }


def benchmark_large_network():
    """基准测试：大规模管网计算"""
    print("\n" + "="*80)
    print("【3】大规模管网计算性能测试")
    print("="*80)

    # 模拟1000个管道的管网
    n_pipes = 1000
    n_iterations = 10

    print(f"\n模拟场景: {n_pipes}个管道，{n_iterations}次迭代")
    print(f"总计算次数: {n_pipes * n_iterations} = {n_pipes * n_iterations:,}")

    # 创建管道列表
    pipes = [
        PressurePipe(f'P{i}', diameter=0.3, length=100, roughness=0.00026)
        for i in range(n_pipes)
    ]

    # 随机流量
    Q_values = np.random.uniform(0.01, 0.5, n_pipes)

    # 原始版本
    print("\n原始版本 (无JIT):")
    start = time.time()
    for _ in range(n_iterations):
        for i, pipe in enumerate(pipes):
            _ = pipe.head_loss(Q_values[i])
    time_orig = time.time() - start
    print(f"  耗时: {time_orig:.4f}s")

    # JIT版本
    print("\nNumba JIT版本:")
    start = time.time()
    for _ in range(n_iterations):
        for i, pipe in enumerate(pipes):
            _ = head_loss_complete_jit(
                Q_values[i], pipe.D, pipe.L, pipe.epsilon, pipe.K_minor, 10, 1e-6
            )
    time_jit = time.time() - start
    print(f"  耗时: {time_jit:.4f}s")

    speedup = time_orig / time_jit if time_jit > 0 else 0
    print(f"\n✅ 加速比: {speedup:.1f}x")

    # 估算实际工程应用收益
    print(f"\n💡 工程应用估算:")
    print(f"   对于{n_pipes}个管道的中型管网:")
    print(f"   - 原方法每次迭代: {time_orig/n_iterations:.3f}s")
    print(f"   - JIT方法每次迭代: {time_jit/n_iterations:.3f}s")
    print(f"   - 每次迭代节省: {(time_orig-time_jit)/n_iterations:.3f}s")
    print(f"   - 100次迭代节省: {(time_orig-time_jit)*10:.2f}s")

    return {
        'test': 'Large Network',
        'samples': n_pipes * n_iterations,
        'time_orig': time_orig,
        'time_jit': time_jit,
        'speedup': speedup
    }


def plot_results(results):
    """绘制性能对比图"""
    try:
        fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(14, 5))

        tests = [r['test'] for r in results]
        speedups = [r['speedup'] for r in results]
        times_orig = [r['time_orig'] for r in results]
        times_jit = [r['time_jit'] for r in results]

        # 子图1: 加速比
        colors = ['#2ecc71' if s > 10 else '#f39c12' if s > 5 else '#e74c3c'
                  for s in speedups]
        bars1 = ax1.bar(tests, speedups, color=colors, alpha=0.7, edgecolor='black')
        ax1.set_ylabel('加速比 Speedup (x)', fontsize=12)
        ax1.set_title('Numba JIT加速效果', fontsize=14, fontweight='bold')
        ax1.axhline(y=1, color='r', linestyle='--', label='无加速线')
        ax1.legend()
        ax1.grid(axis='y', alpha=0.3)

        # 在柱子上添加数值
        for bar in bars1:
            height = bar.get_height()
            ax1.text(bar.get_x() + bar.get_width()/2., height,
                    f'{height:.1f}x',
                    ha='center', va='bottom', fontweight='bold')

        # 子图2: 时间对比
        x = np.arange(len(tests))
        width = 0.35
        bars2 = ax2.bar(x - width/2, times_orig, width, label='原始版本',
                       color='#e74c3c', alpha=0.7, edgecolor='black')
        bars3 = ax2.bar(x + width/2, times_jit, width, label='JIT版本',
                       color='#2ecc71', alpha=0.7, edgecolor='black')

        ax2.set_ylabel('时间 Time (s)', fontsize=12)
        ax2.set_title('计算时间对比', fontsize=14, fontweight='bold')
        ax2.set_xticks(x)
        ax2.set_xticklabels(tests)
        ax2.legend()
        ax2.grid(axis='y', alpha=0.3)

        plt.tight_layout()
        plt.savefig('benchmarks/performance_benchmark_results.png', dpi=150)
        print("\n📊 性能对比图已保存: benchmarks/performance_benchmark_results.png")
        plt.close()
    except Exception as e:
        print(f"\n⚠️ 无法生成图表: {e}")


def main():
    """主函数"""
    print("="*80)
    print("HydroClaude Performance Benchmark")
    print("Numba JIT性能基准测试")
    print("="*80)

    results = []

    # 测试1: Colebrook-White
    results.append(benchmark_colebrook_white())

    # 测试2: 水头损失
    results.append(benchmark_head_loss())

    # 测试3: 大规模管网
    results.append(benchmark_large_network())

    # 总结
    print("\n" + "="*80)
    print("性能测试总结 / Performance Summary")
    print("="*80)
    print()
    print(f"{'测试项目':<20} {'样本数':>10} {'原始(s)':>10} {'JIT(s)':>10} {'加速比':>10}")
    print("-"*80)

    for r in results:
        print(f"{r['test']:<20} {r['samples']:>10,} {r['time_orig']:>10.4f} "
              f"{r['time_jit']:>10.4f} {r['speedup']:>9.1f}x")

    avg_speedup = np.mean([r['speedup'] for r in results])
    print("-"*80)
    print(f"{'平均加速比':<20} {'':>10} {'':>10} {'':>10} {avg_speedup:>9.1f}x")
    print()

    if avg_speedup > 15:
        print("🎉 优秀！Numba JIT显著提升了计算性能！")
    elif avg_speedup > 8:
        print("✅ 良好！性能提升明显，建议在生产环境中启用JIT。")
    else:
        print("⚠️ 一般。性能提升有限，但在大规模计算中仍有价值。")

    print("="*80)

    # 绘制结果
    plot_results(results)


if __name__ == '__main__':
    main()
