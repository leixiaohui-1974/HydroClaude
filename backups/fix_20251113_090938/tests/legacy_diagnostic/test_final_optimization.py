"""
闸门精度最终优化测试

测试非常大的smooth_weight值以验证趋势预测

Author: Claude
Date: 2025-10-23
"""

import sys
import os
import numpy as np

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

try:
    # DEPRECATED: Use HydrostaticCanalSolver instead
# from solvers.single_canal_solver import SingleCanalSolver
except ImportError as e:
    print(f"Import error: {e}")
    print("Make sure project root is in sys.path")
    sys.exit(1)

from solvers.gate import SluiceGate

def test_smooth_weight(smooth_weight, verbose=True):
    """测试特定的平滑权重参数"""
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
            max_iterations=10000,  # 增加最大迭代次数
            convergence_tol=0.001,
            check_interval=500,
            verbose=verbose
        )

        profile = solver.get_full_profile()
        x, Q = profile['x'], profile['Q']
        Q_error = np.abs(Q - Q_initial) / Q_initial * 100
        
        gate_flows = solver.get_gate_flows()
        gate_errors = [abs(gf - Q_initial) / Q_initial * 100 for gf in gate_flows]

        if verbose:
            for i, (gate, gf, err) in enumerate(zip([gate1, gate2, gate3], gate_flows, gate_errors)):
                print(f"  闸门{i+1}: 流量误差={err:.4f}%")

        return {
            'success': True,
            'max_error': np.max(Q_error),
            'mean_error': np.mean(Q_error),
            'max_gate_error': max(gate_errors),
            'iterations': result.get('iterations', 0)
        }

    except Exception as e:
        if verbose:
            print(f"   失败: {e}")
        return {
            'success': False,
            'max_error': float('inf'),
            'mean_error': float('inf'),
            'max_gate_error': float('inf')
        }

print("=" * 80)
print("最终优化测试 - 大smooth_weight值")
print("=" * 80)
print()

smooth_weights = [0.45, 0.55, 0.65, 0.75, 0.85, 0.95]

results = []
for sw in smooth_weights:
    print(f"\n{'='*80}")
    print(f"测试 smooth_weight = {sw:.2f}")
    print('='*80)
    
    result = test_smooth_weight(sw, verbose=True)
    result['smooth_weight'] = sw
    results.append(result)
    
    if result['success']:
        print(f"\n 成功")
        print(f"  最大误差: {result['max_error']:.4f}%")
        print(f"  平均误差: {result['mean_error']:.4f}%")
        print(f"  最大闸门误差: {result['max_gate_error']:.4f}%")
        
        if result['max_error'] < 0.5:
            print(f"\n 达到0.5%目标！ ")

print("\n" + "=" * 80)
print("最终结果汇总")
print("=" * 80)

successful = [r for r in results if r['success']]
if successful:
    best = min(successful, key=lambda r: r['max_error'])
    
    print(f"\n最佳配置: smooth_weight = {best['smooth_weight']:.2f}")
    print(f"  最大误差: {best['max_error']:.4f}%")
    print(f"  平均误差: {best['mean_error']:.4f}%")
    print(f"  最大闸门误差: {best['max_gate_error']:.4f}%")
    
    achieving = [r for r in successful if r['max_error'] < 0.5]
    if achieving:
        print(f"\n 共{len(achieving)}个配置达到0.5%目标！")
    else:
        print(f"\n距离0.5%目标还有: {best['max_error']/0.5:.2f}x")

print("\n" + "=" * 80)
