"""
闸门精度优化脚本

系统性测试不同平滑参数对闸门区域精度的影响

Author: Claude
Date: 2025-10-23
"""

import sys
import os
import numpy as np

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from solvers.single_canal_solver import SingleCanalSolver
from solvers.gate import SluiceGate

def test_smooth_weight(smooth_weight, verbose=False):
    """测试特定的平滑权重参数

    Args:
        smooth_weight: 平滑权重 (0-1)
        verbose: 是否打印详细信息

    Returns:
        dict: 包含误差统计的结果
    """
    # 系统配置（与脚本11完全相同）
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
        n=manning_n
    )

    # 临时修改平滑权重
    original_smooth_weight = None
    if hasattr(solver.solver, 'smooth_weight'):
        original_smooth_weight = solver.solver.smooth_weight
        solver.solver.smooth_weight = smooth_weight

    # 初始化并求解
    solver.reset_with_steady_state(Q_initial)

    try:
        result = solver.solve_steady_state(
            Q_target=Q_initial,
            max_iterations=5000,
            convergence_tol=0.001,
            check_interval=500,
            verbose=verbose
        )

        # 获取结果
        profile = solver.get_full_profile()
        x = profile['x']
        Q = profile['Q']

        # 计算误差
        Q_error = np.abs(Q - Q_initial) / Q_initial * 100
        Q_max_error = np.max(Q_error)
        Q_mean_error = np.mean(Q_error)

        # 分析闸门区域误差
        gate_errors = []
        gate_flows = solver.get_gate_flows()

        for i, (gate, gf) in enumerate(zip([gate1, gate2, gate3], gate_flows)):
            error = abs(gf - Q_initial) / Q_initial * 100
            gate_errors.append(error)

            # 找到闸门附近的网格点误差
            gate_pos = gate.position
            nearby_mask = (x >= gate_pos - 100) & (x <= gate_pos + 100)
            nearby_error = np.max(Q_error[nearby_mask])

            if verbose:
                print(f"  闸门{i+1} (x={gate_pos}m): 流量误差={error:.4f}%, "
                      f"附近网格最大误差={nearby_error:.4f}%")

        # 恢复原始权重
        if original_smooth_weight is not None:
            solver.solver.smooth_weight = original_smooth_weight

        return {
            'success': True,
            'converged': result.get('converged', False),
            'iterations': result.get('iterations', 0),
            'max_error': Q_max_error,
            'mean_error': Q_mean_error,
            'gate_errors': gate_errors,
            'max_gate_error': max(gate_errors) if gate_errors else float('inf')
        }

    except Exception as e:
        if verbose:
            print(f"  ✗ 求解失败: {e}")

        # 恢复原始权重
        if original_smooth_weight is not None:
            solver.solver.smooth_weight = original_smooth_weight

        return {
            'success': False,
            'error': str(e),
            'max_error': float('inf'),
            'mean_error': float('inf'),
            'max_gate_error': float('inf')
        }


def main():
    """主测试函数"""

    print("=" * 80)
    print("闸门精度优化 - 平滑权重参数扫描")
    print("=" * 80)
    print()

    # 测试不同的平滑权重值
    smooth_weights = [0.03, 0.05, 0.08, 0.10, 0.12, 0.15, 0.20]

    print("配置:")
    print(f"  测试参数: smooth_weight = {smooth_weights}")
    print(f"  评估指标: 最大误差、平均误差、闸门区域误差")
    print()

    results = []

    print("=" * 80)
    print("参数扫描")
    print("=" * 80)
    print()

    for sw in smooth_weights:
        print(f"测试 smooth_weight = {sw:.2f}")
        print("-" * 40)

        result = test_smooth_weight(sw, verbose=True)
        result['smooth_weight'] = sw
        results.append(result)

        if result['success']:
            print(f"  ✓ 成功")
            print(f"    最大误差: {result['max_error']:.4f}%")
            print(f"    平均误差: {result['mean_error']:.4f}%")
            print(f"    最大闸门误差: {result['max_gate_error']:.4f}%")
            print(f"    迭代次数: {result['iterations']}")
        else:
            print(f"  ✗ 失败: {result.get('error', 'Unknown error')}")

        print()

    # 分析结果
    print("=" * 80)
    print("结果分析")
    print("=" * 80)
    print()

    # 过滤成功的结果
    successful_results = [r for r in results if r['success']]

    if not successful_results:
        print("✗ 所有测试都失败了！")
        return

    # 找到最佳配置
    best_max_error = min(successful_results, key=lambda r: r['max_error'])
    best_mean_error = min(successful_results, key=lambda r: r['mean_error'])
    best_gate_error = min(successful_results, key=lambda r: r['max_gate_error'])

    print("最佳配置:")
    print()

    print(f"1. 最小最大误差:")
    print(f"   smooth_weight = {best_max_error['smooth_weight']:.2f}")
    print(f"   最大误差 = {best_max_error['max_error']:.4f}%")
    print(f"   平均误差 = {best_max_error['mean_error']:.4f}%")
    print(f"   最大闸门误差 = {best_max_error['max_gate_error']:.4f}%")
    print()

    print(f"2. 最小平均误差:")
    print(f"   smooth_weight = {best_mean_error['smooth_weight']:.2f}")
    print(f"   最大误差 = {best_mean_error['max_error']:.4f}%")
    print(f"   平均误差 = {best_mean_error['mean_error']:.4f}%")
    print(f"   最大闸门误差 = {best_mean_error['max_gate_error']:.4f}%")
    print()

    print(f"3. 最小闸门误差:")
    print(f"   smooth_weight = {best_gate_error['smooth_weight']:.2f}")
    print(f"   最大误差 = {best_gate_error['max_error']:.4f}%")
    print(f"   平均误差 = {best_gate_error['mean_error']:.4f}%")
    print(f"   最大闸门误差 = {best_gate_error['max_gate_error']:.4f}%")
    print()

    # 总结表格
    print("所有成功测试的总结:")
    print()
    print(f"{'smooth_weight':>13} | {'最大误差':>10} | {'平均误差':>10} | {'最大闸门误差':>12} | {'迭代':>6}")
    print("-" * 80)

    for r in successful_results:
        print(f"{r['smooth_weight']:>13.2f} | {r['max_error']:>9.4f}% | "
              f"{r['mean_error']:>9.4f}% | {r['max_gate_error']:>11.4f}% | "
              f"{r['iterations']:>6}")

    print()

    # 检查是否达到目标
    target_error = 0.5
    achieving_target = [r for r in successful_results if r['max_error'] < target_error]

    if achieving_target:
        print(f"✓ 有 {len(achieving_target)} 个配置达到了 {target_error}% 的目标误差！")
        for r in achieving_target:
            print(f"  - smooth_weight = {r['smooth_weight']:.2f}: "
                  f"最大误差 = {r['max_error']:.4f}%")
    else:
        best = min(successful_results, key=lambda r: r['max_error'])
        print(f"✗ 没有配置达到 {target_error}% 的目标")
        print(f"  最接近的配置: smooth_weight = {best['smooth_weight']:.2f}, "
              f"最大误差 = {best['max_error']:.4f}%")
        print(f"  距离目标还有: {best['max_error'] / target_error:.2f}x")

    print()
    print("=" * 80)


if __name__ == "__main__":
    main()
