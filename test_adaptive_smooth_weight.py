"""
自适应平滑权重测试脚本

对比不同的平滑权重策略：
1. 固定权重 smooth_weight=0.55 (基准)
2. 残差自适应模式
3. 距离自适应模式
4. 混合自适应模式（推荐）

Author: Claude
Date: 2025-10-23
"""

import sys
import os
import numpy as np

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from solvers.single_canal_solver import SingleCanalSolver
from solvers.gate import SluiceGate
from solvers.adaptive_smooth_config import (
    AdaptiveSmoothConfig,
    DEFAULT_CONFIG,
    AGGRESSIVE_CONFIG,
    CONSERVATIVE_CONFIG,
    DISTANCE_ONLY_CONFIG,
    RESIDUAL_ONLY_CONFIG
)


def test_config(config_name, config, verbose=True):
    """
    测试特定配置

    Args:
        config_name: 配置名称
        config: AdaptiveSmoothConfig对象（或None表示固定权重）
        verbose: 是否输出详细信息
    """
    # 系统配置
    canal_length = 10000.0
    canal_width = 10.0
    n_points = 301
    bed_slope = 0.0005
    manning_n = 0.025
    Q_initial = 10.0

    # 三个闸门
    gate1 = SluiceGate(position=2500.0, width=canal_width, opening=4.5, Cd=0.6)
    gate2 = SluiceGate(position=5000.0, width=canal_width, opening=4.0, Cd=0.6)
    gate3 = SluiceGate(position=7500.0, width=canal_width, opening=5.0, Cd=0.6)

    # 创建求解器
    solver = SingleCanalSolver(
        total_length=canal_length,
        structures=[gate1, gate2, gate3],
        nx_total=n_points,
        B=canal_width,
        S0=bed_slope,
        n=manning_n,
        smooth_weight=0.55,  # 固定权重（config=None时使用）
        adaptive_smooth_config=config  # 自适应配置
    )

    # 初始化
    solver.reset_with_steady_state(Q_initial)

    # 求解
    try:
        result = solver.solve_steady_state(
            Q_target=Q_initial,
            max_iterations=10000,
            convergence_tol=0.001,
            check_interval=500,
            verbose=verbose
        )

        # 获取结果
        profile = solver.get_full_profile()
        x, Q = profile['x'], profile['Q']

        # 计算误差
        Q_error = np.abs(Q - Q_initial) / Q_initial * 100
        Q_max_error = np.max(Q_error)
        Q_mean_error = np.mean(Q_error)

        # 分析闸门区域误差
        gate_flows = solver.get_gate_flows()
        gate_errors = [abs(gf - Q_initial) / Q_initial * 100 for gf in gate_flows]

        if verbose:
            print(f"\n闸门流量误差:")
            for i, (gate, gf, err) in enumerate(zip([gate1, gate2, gate3], gate_flows, gate_errors), 1):
                print(f"  闸门{i}: 流量误差={err:.4f}%")

        return {
            'success': True,
            'config_name': config_name,
            'max_error': Q_max_error,
            'mean_error': Q_mean_error,
            'max_gate_error': max(gate_errors),
            'gate_errors': gate_errors,
            'iterations': result.get('iterations', 0)
        }

    except Exception as e:
        if verbose:
            print(f"\n✗ 求解失败: {e}")

        return {
            'success': False,
            'config_name': config_name,
            'error': str(e),
            'max_error': float('inf'),
            'mean_error': float('inf'),
            'max_gate_error': float('inf')
        }


def main():
    """主测试函数"""

    print("=" * 80)
    print("自适应平滑权重测试")
    print("=" * 80)
    print()

    # 测试配置列表
    test_configs = [
        ("固定权重(0.55)", None),  # 固定权重基准
        ("固定权重(0.55)-via-config", AdaptiveSmoothConfig(mode='fixed', fixed_weight=0.55)),
        ("残差自适应", RESIDUAL_ONLY_CONFIG),
        ("距离自适应", DISTANCE_ONLY_CONFIG),
        ("混合自适应(保守)", CONSERVATIVE_CONFIG),
        ("混合自适应(激进)", AGGRESSIVE_CONFIG),
        ("混合自适应(默认)", AdaptiveSmoothConfig(mode='hybrid'))
    ]

    results = []

    for config_name, config in test_configs:
        print("\n" + "=" * 80)
        print(f"测试: {config_name}")
        print("=" * 80)

        if config is not None:
            print(f"配置: {config}")
        else:
            print("配置: 固定smooth_weight=0.55")

        print()

        result = test_config(config_name, config, verbose=True)
        results.append(result)

        if result['success']:
            print(f"\n✓ 成功")
            print(f"  最大误差: {result['max_error']:.4f}%")
            print(f"  平均误差: {result['mean_error']:.4f}%")
            print(f"  最大闸门误差: {result['max_gate_error']:.4f}%")
            print(f"  迭代次数: {result['iterations']}")
        else:
            print(f"\n✗ 失败")

    # 汇总结果
    print("\n" + "=" * 80)
    print("结果汇总")
    print("=" * 80)
    print()

    # 过滤成功的结果
    successful = [r for r in results if r['success']]

    if not successful:
        print("✗ 所有测试都失败了！")
        return

    # 表格输出
    print(f"{'配置':<25} | {'最大误差':>10} | {'平均误差':>10} | {'闸门误差':>10} | {'迭代':>6}")
    print("-" * 80)

    for r in successful:
        print(f"{r['config_name']:<25} | {r['max_error']:>9.4f}% | "
              f"{r['mean_error']:>9.4f}% | {r['max_gate_error']:>9.4f}% | "
              f"{r['iterations']:>6}")

    print()

    # 找到最佳配置
    best = min(successful, key=lambda r: r['max_error'])
    baseline = next((r for r in successful if r['config_name'] == "固定权重(0.55)"), None)

    print("最佳配置:")
    print(f"  名称: {best['config_name']}")
    print(f"  最大误差: {best['max_error']:.4f}%")
    print(f"  平均误差: {best['mean_error']:.4f}%")
    print(f"  最大闸门误差: {best['max_gate_error']:.4f}%")

    if baseline and best['config_name'] != "固定权重(0.55)":
        improvement = baseline['max_error'] / best['max_error']
        print(f"\n相比基准（固定权重0.55）的改善:")
        print(f"  基准最大误差: {baseline['max_error']:.4f}%")
        print(f"  优化后误差: {best['max_error']:.4f}%")
        print(f"  改善倍数: {improvement:.2f}x")

    # 检查是否达到目标
    target_1_5_percent = [r for r in successful if r['max_error'] < 1.5]
    target_1_0_percent = [r for r in successful if r['max_error'] < 1.0]

    print()
    if target_1_0_percent:
        print(f"✓✓✓ 有 {len(target_1_0_percent)} 个配置达到了1.0%目标！")
        for r in target_1_0_percent:
            print(f"  - {r['config_name']}: {r['max_error']:.4f}%")
    elif target_1_5_percent:
        print(f"✓✓ 有 {len(target_1_5_percent)} 个配置达到了1.5%目标！")
        for r in target_1_5_percent:
            print(f"  - {r['config_name']}: {r['max_error']:.4f}%")
    else:
        print(f"⚠ 未达到1.5%目标，最佳: {best['max_error']:.4f}%")

    print("\n" + "=" * 80)


if __name__ == "__main__":
    main()
