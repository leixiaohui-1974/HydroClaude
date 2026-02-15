"""
局部网格加密测试

测试不同的网格加密配置对精度的影响

Author: Claude
Date: 2025-10-23
"""

import sys
import pytest
import warnings
warnings.filterwarnings("ignore")
import os
import numpy as np

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

try:
    # DEPRECATED: Use HydrostaticCanalSolver instead
# # DEPRECATED: Use HydrostaticCanalSolver instead
# # DEPRECATED: Use HydrostaticCanalSolver instead
# # from solvers.single_canal_solver import SingleCanalSolver  # 已废弃
from solvers.hydrostatic_canal_solver import HydrostaticCanalSolver as SingleCanalSolver
except ImportError as e:
    pytest.skip(f"Required module not available: {e}", allow_module_level=True)

from solvers.gate import SluiceGate


def test_grid_config(config_name, use_adaptive_grid, dx_fine, dx_coarse, refinement_radius, nx_uniform=301, verbose=False):
    """
    测试网格配置

    Args:
        config_name: 配置名称
        use_adaptive_grid: 是否使用自适应网格
        dx_fine: 精细区网格间距 (m)
        dx_coarse: 粗糙区网格间距 (m)
        refinement_radius: 加密半径 (m)
        nx_uniform: 均匀网格点数（非自适应时使用）
        verbose: 是否输出详细信息
    """
    # 系统配置
    canal_length = 10000.0
    canal_width = 10.0
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
        nx_total=nx_uniform,
        B=canal_width,
        S0=bed_slope,
        n=manning_n,
        smooth_weight=0.55,  # 使用优化的固定值
        use_adaptive_grid=use_adaptive_grid,
        refinement_radius=refinement_radius,
        dx_fine=dx_fine,
        dx_coarse=dx_coarse
    )

    # 获取实际网格信息
    if use_adaptive_grid:
        actual_nx = len(solver.solver.x)
        actual_dx_min = np.min(np.diff(solver.solver.x))
        actual_dx_max = np.max(np.diff(solver.solver.x))
    else:
        actual_nx = nx_uniform
        actual_dx_min = canal_length / (nx_uniform - 1)
        actual_dx_max = actual_dx_min

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

        return {
            'success': True,
            'config_name': config_name,
            'nx': actual_nx,
            'dx_min': actual_dx_min,
            'dx_max': actual_dx_max,
            'max_error': Q_max_error,
            'mean_error': Q_mean_error,
            'max_gate_error': max(gate_errors),
            'gate_errors': gate_errors,
            'iterations': result.get('iterations', 0)
        }

    except Exception as e:
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
    print("局部网格加密测试")
    print("=" * 80)
    print()

    # 测试配置列表
    test_configs = [
        # (name, use_adaptive_grid, dx_fine, dx_coarse, refinement_radius, nx_uniform)

        # 基准：均匀网格
        ("基准:均匀网格(301点)", False, None, None, None, 301),
        ("均匀细网格(601点)", False, None, None, None, 601),
        ("均匀极细网格(1201点)", False, None, None, None, 1201),

        # 自适应网格：不同dx_fine
        ("自适应:dx_fine=5m", True, 5.0, 33.0, 200.0, 301),
        ("自适应:dx_fine=3m", True, 3.0, 33.0, 200.0, 301),
        ("自适应:dx_fine=2m", True, 2.0, 33.0, 200.0, 301),
        ("自适应:dx_fine=1m", True, 1.0, 33.0, 200.0, 301),

        # 自适应网格：不同refinement_radius
        ("自适应:半径=100m", True, 5.0, 33.0, 100.0, 301),
        ("自适应:半径=300m", True, 5.0, 33.0, 300.0, 301),

        # 自适应网格：不同dx_coarse
        ("自适应:dx_coarse=50m", True, 5.0, 50.0, 200.0, 301),
        ("自适应:dx_coarse=25m", True, 5.0, 25.0, 200.0, 301),

        # 极端精细配置
        ("自适应:极细(dx_fine=0.5m)", True, 0.5, 50.0, 200.0, 301),
    ]

    results = []

    for i, config in enumerate(test_configs, 1):
        config_name = config[0]
        print(f"\n[{i}/{len(test_configs)}] 测试: {config_name}")

        result = test_grid_config(*config, verbose=False)
        results.append(result)

        if result['success']:
            print(f"   网格点数={result['nx']}, dx范围=[{result['dx_min']:.2f}, {result['dx_max']:.2f}]m")
            print(f"    最大误差={result['max_error']:.4f}%, "
                  f"平均误差={result['mean_error']:.4f}%, "
                  f"闸门误差={result['max_gate_error']:.4f}%")
        else:
            print(f"   失败: {result.get('error', 'Unknown')}")

    # 汇总
    print("\n" + "=" * 80)
    print("结果汇总")
    print("=" * 80)
    print()

    successful = [r for r in results if r['success']]

    if successful:
        print(f"{'配置':<30} | {'网格点':>7} | {'dx_min':>7} | {'最大误差':>10} | {'闸门误差':>10}")
        print("-" * 85)

        for r in sorted(successful, key=lambda x: x['max_error']):
            print(f"{r['config_name']:<30} | {r['nx']:>7} | {r['dx_min']:>6.2f}m | "
                  f"{r['max_error']:>9.4f}% | {r['max_gate_error']:>9.4f}%")

        print()

        best = min(successful, key=lambda r: r['max_error'])
        baseline = next((r for r in successful if "基准" in r['config_name']), None)

        print("最佳配置:")
        print(f"  名称: {best['config_name']}")
        print(f"  网格点数: {best['nx']}")
        print(f"  dx范围: [{best['dx_min']:.2f}, {best['dx_max']:.2f}]m")
        print(f"  最大误差: {best['max_error']:.4f}%")
        print(f"  平均误差: {best['mean_error']:.4f}%")
        print(f"  最大闸门误差: {best['max_gate_error']:.4f}%")

        if baseline:
            improvement = baseline['max_error'] / best['max_error']
            diff = baseline['max_error'] - best['max_error']
            efficiency = improvement / (best['nx'] / baseline['nx'])

            print(f"\n相比基准:")
            print(f"  误差改善: {improvement:.3f}x")
            print(f"  绝对改善: {diff:.4f}%")
            print(f"  网格点数比: {best['nx'] / baseline['nx']:.2f}x")
            print(f"  效率(改善/网格增长): {efficiency:.3f}")

            if improvement > 1.5:
                print(f"   网格加密非常有效！")
            elif improvement > 1.2:
                print(f"   网格加密有效")
            elif improvement > 1.05:
                print(f"   网格加密略有改善")
            else:
                print(f"   网格加密改善不明显")

        # 检查目标
        target_1_5 = [r for r in successful if r['max_error'] < 1.5]
        target_1_0 = [r for r in successful if r['max_error'] < 1.0]
        target_0_5 = [r for r in successful if r['max_error'] < 0.5]

        print()
        if target_0_5:
            print(f" 有{len(target_0_5)}个配置达到0.5%目标！")
            for r in target_0_5:
                print(f"  - {r['config_name']}: {r['max_error']:.4f}% (nx={r['nx']})")
        elif target_1_0:
            print(f" 有{len(target_1_0)}个配置达到1.0%目标！")
            for r in target_1_0:
                print(f"  - {r['config_name']}: {r['max_error']:.4f}% (nx={r['nx']})")
        elif target_1_5:
            print(f" 有{len(target_1_5)}个配置达到1.5%目标！")
            for r in target_1_5:
                print(f"  - {r['config_name']}: {r['max_error']:.4f}% (nx={r['nx']})")
        else:
            print(f" 未达到1.5%目标")
            print(f"  最佳: {best['max_error']:.4f}%")
            print(f"  距离1.5%: {best['max_error'] / 1.5:.2f}x")

    print("\n" + "=" * 80)


if __name__ == "__main__":
    main()
