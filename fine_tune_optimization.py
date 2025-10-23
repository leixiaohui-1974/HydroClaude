"""
精细调优 - 在0.45-0.60范围内寻找最优smooth_weight

Author: Claude
Date: 2025-10-23
"""

import sys
import os
import numpy as np

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from solvers.single_canal_solver import SingleCanalSolver
from solvers.gate import SluiceGate

def test_smooth_weight(smooth_weight):
    """快速测试smooth_weight"""
    canal_length = 10000.0
    canal_width = 10.0
    n_points = 301
    bed_slope = 0.0005
    manning_n = 0.025
    Q_initial = 10.0

    gate1 = SluiceGate(position=2500.0, width=canal_width, opening=4.5, Cd=0.6)
    gate2 = SluiceGate(position=5000.0, width=canal_width, opening=4.0, Cd=0.6)
    gate3 = SluiceGate(position=7500.0, width=canal_width, opening=5.0, Cd=0.6)

    solver = SingleCanalSolver(
        total_length=canal_length,
        structures=[gate1, gate2, gate3],
        nx_total=n_points,
        B=canal_width,
        S0=bed_slope,
        n=manning_n,
        smooth_weight=smooth_weight
    )

    solver.reset_with_steady_state(Q_initial)

    try:
        result = solver.solve_steady_state(
            Q_target=Q_initial,
            max_iterations=10000,
            convergence_tol=0.001,
            check_interval=500,
            verbose=False  # 关闭详细输出加快速度
        )

        profile = solver.get_full_profile()
        Q = profile['Q']
        Q_error = np.abs(Q - Q_initial) / Q_initial * 100
        
        gate_flows = solver.get_gate_flows()
        gate_errors = [abs(gf - Q_initial) / Q_initial * 100 for gf in gate_flows]

        return {
            'success': True,
            'max_error': np.max(Q_error),
            'mean_error': np.mean(Q_error),
            'max_gate_error': max(gate_errors),
            'iterations': result.get('iterations', 0)
        }

    except Exception as e:
        return {
            'success': False,
            'max_error': float('inf'),
            'mean_error': float('inf'),
            'max_gate_error': float('inf')
        }

print("=" * 80)
print("精细调优: 0.45 - 0.60 范围")
print("=" * 80)
print()

# 在0.45-0.60之间测试，步长0.01
smooth_weights = np.arange(0.45, 0.61, 0.01)

results = []
print(f"测试 {len(smooth_weights)} 个配置...\n")

for i, sw in enumerate(smooth_weights, 1):
    result = test_smooth_weight(sw)
    result['smooth_weight'] = sw
    results.append(result)
    
    if result['success']:
        status = "✓"
        error_str = f"{result['max_error']:.4f}%"
    else:
        status = "✗"
        error_str = "失败"
    
    print(f"[{i:2d}/{len(smooth_weights)}] sw={sw:.2f}: {status} 最大误差={error_str}")

print("\n" + "=" * 80)
print("最优结果")
print("=" * 80)

successful = [r for r in results if r['success']]
if successful:
    best = min(successful, key=lambda r: r['max_error'])
    
    print(f"\n🎯 最优配置:")
    print(f"  smooth_weight = {best['smooth_weight']:.2f}")
    print(f"  最大误差 = {best['max_error']:.4f}%")
    print(f"  平均误差 = {best['mean_error']:.4f}%")
    print(f"  最大闸门误差 = {best['max_gate_error']:.4f}%")
    print(f"  迭代次数 = {best['iterations']}")
    
    # 相比默认值的改善
    default_error = 9.14  # 从之前的测试得知
    improvement = default_error / best['max_error']
    print(f"\n📈 改善效果:")
    print(f"  默认值(0.10)误差: {default_error:.2f}%")
    print(f"  优化后误差: {best['max_error']:.4f}%")
    print(f"  改善倍数: {improvement:.2f}x")
    
    # 距离目标
    target = 0.5
    gap = best['max_error'] / target
    print(f"\n🎯 距离目标(0.5%):")
    print(f"  当前: {best['max_error']:.4f}%")
    print(f"  差距: {gap:.2f}x")
    
    # 显示前5名
    print(f"\n📊 前5名配置:")
    top5 = sorted(successful, key=lambda r: r['max_error'])[:5]
    for i, r in enumerate(top5, 1):
        print(f"  {i}. sw={r['smooth_weight']:.2f}: "
              f"最大误差={r['max_error']:.4f}%, "
              f"闸门误差={r['max_gate_error']:.4f}%")

print("\n" + "=" * 80)
