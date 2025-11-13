"""
诊断网格细化导致精度恶化的原因

测试假设：smooth_weight=0.55是为dx=33.33m优化的，对细网格不合适

Author: Claude
Date: 2025-10-23
"""

import sys
import os
import numpy as np

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from solvers.single_canal_solver import SingleCanalSolver
from solvers.gate import SluiceGate


def test_grid_with_smooth_weight(nx, smooth_weight):
    """测试特定网格点数和smooth_weight组合"""
    canal_length = 10000.0
    canal_width = 10.0
    bed_slope = 0.0005
    manning_n = 0.025
    Q_initial = 10.0

    gate1 = SluiceGate(position=2500.0, width=canal_width, opening=4.5, Cd=0.6)
    gate2 = SluiceGate(position=5000.0, width=canal_width, opening=4.0, Cd=0.6)
    gate3 = SluiceGate(position=7500.0, width=canal_width, opening=5.0, Cd=0.6)

    solver = SingleCanalSolver(
        total_length=canal_length,
        structures=[gate1, gate2, gate3],
        nx_total=nx,
        B=canal_width,
        S0=bed_slope,
        n=manning_n,
        smooth_weight=smooth_weight,
        use_adaptive_grid=False  # 均匀网格
    )

    solver.reset_with_steady_state(Q_initial)

    try:
        result = solver.solve_steady_state(
            Q_target=Q_initial,
            max_iterations=10000,
            convergence_tol=0.001,
            check_interval=500,
            verbose=False
        )

        profile = solver.get_full_profile()
        Q = profile['Q']
        Q_error = np.abs(Q - Q_initial) / Q_initial * 100

        gate_flows = solver.get_gate_flows()
        gate_errors = [abs(gf - Q_initial) / Q_initial * 100 for gf in gate_flows]

        return {
            'success': True,
            'max_error': np.max(Q_error),
            'max_gate_error': max(gate_errors),
            'converged': result.get('converged', False)
        }
    except Exception as e:
        return {
            'success': False,
            'max_error': float('inf'),
            'max_gate_error': float('inf'),
            'error': str(e)
        }


print("=" * 80)
print("诊断网格细化导致精度恶化的原因")
print("=" * 80)
print()

# 测试不同网格点数，每个测试多个smooth_weight值
grid_configs = [
    (301, 33.33),   # 基准
    (601, 16.67),   # 2x细化
    (1201, 8.33),   # 4x细化
]

smooth_weights = [0.10, 0.20, 0.30, 0.40, 0.55, 0.70, 0.85]

for nx, dx in grid_configs:
    print(f"\n{'='*80}")
    print(f"网格: nx={nx}, dx={dx:.2f}m")
    print('='*80)
    print(f"{'smooth_weight':>15} | {'最大误差':>12} | {'闸门误差':>12} | {'状态':>8}")
    print("-" * 80)

    best_sw = None
    best_error = float('inf')

    for sw in smooth_weights:
        result = test_grid_with_smooth_weight(nx, sw)

        if result['success']:
            status = "" if result['max_error'] < 10 else ""
            print(f"{sw:>15.2f} | {result['max_error']:>11.4f}% | "
                  f"{result['max_gate_error']:>11.4f}% | {status:>8}")

            if result['max_error'] < best_error:
                best_error = result['max_error']
                best_sw = sw
        else:
            print(f"{sw:>15.2f} | {'失败':>11} | {'失败':>11} | ")

    print()
    print(f"最佳配置: smooth_weight={best_sw:.2f}, 最大误差={best_error:.4f}%")

print("\n" + "=" * 80)
print("结论")
print("=" * 80)
print()
print("如果细网格在任何smooth_weight下都表现很差，")
print("则问题不是smooth_weight，而是数值格式本身。")
print()
