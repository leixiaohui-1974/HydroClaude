"""
FVM稳态求解器对比测试

对比三种方法在3闸门问题上的精度：
1. 原始FDM（Preissmann + 平滑）- 基准
2. FVM隐式稳态求解（Newton迭代）- 新方法
3. 目标精度：0.5%

Author: Claude
Date: 2025-10-23
"""

import sys
import os
import numpy as np
import matplotlib.pyplot as plt

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

try:
    # DEPRECATED: Use HydrostaticCanalSolver instead
# from solvers.single_canal_solver import SingleCanalSolver
except ImportError as e:
    print(f"Import error: {e}")
    print("Make sure project root is in sys.path")
    sys.exit(1)

from solvers.fvm_steady_solver import FVMSteadySolver
from solvers.gate import SluiceGate


def run_fdm_baseline_test():
    """
    运行FDM基准测试（Phase 1最优配置）
    """
    print("=" * 70)
    print("测试1: FDM基准（Preissmann + smooth_weight=0.55）")
    print("=" * 70)
    print()

    # 系统配置
    canal_length = 10000.0
    canal_width = 10.0
    n_points = 301
    bed_slope = 0.0005
    manning_n = 0.025
    Q_target = 10.0

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
        method='preissmann',
        smooth_weight=0.55  # Phase 1最优值
    )

    # 初始化并求解
    solver.reset_with_steady_state(Q_target)

    result = solver.solve_steady_state(
        Q_target=Q_target,
        max_iterations=10000,
        convergence_tol=0.001,
        check_interval=500,
        verbose=True
    )

    # 获取结果
    profile = solver.get_full_profile()
    x, h, Q = profile['x'], profile['h'], profile['Q']

    # 计算误差
    Q_error = np.abs(Q - Q_target) / Q_target * 100
    Q_max_error = np.max(Q_error)
    Q_mean_error = np.mean(Q_error)

    # 闸门流量
    gate_flows = solver.get_gate_flows()
    gate_errors = [abs(gf - Q_target) / Q_target * 100 for gf in gate_flows]

    print()
    print("FDM结果:")
    print(f"  最大流量误差: {Q_max_error:.4f}%")
    print(f"  平均流量误差: {Q_mean_error:.4f}%")
    print(f"  闸门流量: {gate_flows}")
    print(f"  闸门误差: {[f'{e:.4f}%' for e in gate_errors]}")
    print()

    return {
        'name': 'FDM (Preissmann)',
        'x': x,
        'h': h,
        'Q': Q,
        'max_error': Q_max_error,
        'mean_error': Q_mean_error,
        'gate_flows': gate_flows,
        'gate_errors': gate_errors,
        'converged': result['converged']
    }


def run_fvm_steady_test():
    """
    运行FVM隐式稳态求解测试
    """
    print("=" * 70)
    print("测试2: FVM隐式稳态求解（Newton迭代）")
    print("=" * 70)
    print()

    # 系统配置
    canal_length = 10000.0
    canal_width = 10.0
    n_points = 301
    bed_slope = 0.0005
    manning_n = 0.025
    Q_target = 10.0

    # 网格
    x_grid = np.linspace(0, canal_length, n_points)

    # 三个闸门
    gates = [
        (2500.0, 4.5, 0.6),  # (position, opening, Cd)
        (5000.0, 4.0, 0.6),
        (7500.0, 5.0, 0.6)
    ]

    # 创建FVM稳态求解器
    solver = FVMSteadySolver(
        x_grid=x_grid,
        B=canal_width,
        S0=bed_slope,
        n=manning_n,
        gates=gates
    )

    # 初始化为均匀流
    from utils.canal_utils import compute_steady_uniform_flow
    h_uniform = compute_steady_uniform_flow(Q_target, canal_width, bed_slope, manning_n, 9.81)
    solver.initialize(h_uniform, Q_target)

    print(f"初始均匀流水深: {h_uniform:.3f} m")

    # 求解稳态
    converged = solver.solve_steady_newton(
        Q_target=Q_target,
        max_iter=100,
        tol=1e-6,
        verbose=True
    )

    # 获取结果
    results = solver.get_results()
    x = results['x']
    h = results['h']
    Q = results['Q']

    # 计算误差
    Q_error = np.abs(Q - Q_target) / Q_target * 100
    Q_max_error = np.max(Q_error)
    Q_mean_error = np.mean(Q_error)

    # 闸门流量
    gate_flows = []
    for gate_info in solver.gate_interfaces:
        idx = gate_info['index']
        if idx < len(Q):
            gate_flows.append(Q[idx])

    gate_errors = [abs(gf - Q_target) / Q_target * 100 for gf in gate_flows]

    print()
    print("FVM稳态结果:")
    print(f"  最大流量误差: {Q_max_error:.4f}%")
    print(f"  平均流量误差: {Q_mean_error:.4f}%")
    print(f"  闸门流量: {gate_flows}")
    print(f"  闸门误差: {[f'{e:.4f}%' for e in gate_errors]}")
    print()

    return {
        'name': 'FVM Steady (Newton)',
        'x': x,
        'h': h,
        'Q': Q,
        'max_error': Q_max_error,
        'mean_error': Q_mean_error,
        'gate_flows': gate_flows,
        'gate_errors': gate_errors,
        'converged': converged
    }


def plot_comparison(result_fdm, result_fvm):
    """
    绘制对比图
    """
    fig, axes = plt.subplots(3, 1, figsize=(14, 12))

    Q_target = 10.0

    # 水深对比
    ax = axes[0]
    ax.plot(result_fdm['x'], result_fdm['h'], 'b-', linewidth=2, label='FDM (Preissmann)', alpha=0.7)
    ax.plot(result_fvm['x'], result_fvm['h'], 'r--', linewidth=2, label='FVM Steady (Newton)', alpha=0.7)
    ax.axvline(2500, color='gray', linestyle=':', alpha=0.5, label='Gates')
    ax.axvline(5000, color='gray', linestyle=':', alpha=0.5)
    ax.axvline(7500, color='gray', linestyle=':', alpha=0.5)
    ax.set_xlabel('x [m]', fontsize=12)
    ax.set_ylabel('h [m]', fontsize=12)
    ax.set_title('Water Depth Comparison', fontsize=14, fontweight='bold')
    ax.legend(fontsize=11)
    ax.grid(True, alpha=0.3)

    # 流量对比
    ax = axes[1]
    ax.plot(result_fdm['x'], result_fdm['Q'], 'b-', linewidth=2, label='FDM (Preissmann)', alpha=0.7)
    ax.plot(result_fvm['x'], result_fvm['Q'], 'r--', linewidth=2, label='FVM Steady (Newton)', alpha=0.7)
    ax.axhline(Q_target, color='k', linestyle='--', linewidth=1.5, alpha=0.5, label=f'Target Q={Q_target} m³/s')
    ax.axvline(2500, color='gray', linestyle=':', alpha=0.5)
    ax.axvline(5000, color='gray', linestyle=':', alpha=0.5)
    ax.axvline(7500, color='gray', linestyle=':', alpha=0.5)
    ax.set_xlabel('x [m]', fontsize=12)
    ax.set_ylabel('Q [m³/s]', fontsize=12)
    ax.set_title(f'Discharge Comparison (FDM: {result_fdm["max_error"]:.4f}%, FVM: {result_fvm["max_error"]:.4f}%)',
                 fontsize=14, fontweight='bold')
    ax.legend(fontsize=11)
    ax.grid(True, alpha=0.3)

    # 流量误差对比
    ax = axes[2]
    Q_error_fdm = np.abs(result_fdm['Q'] - Q_target) / Q_target * 100
    Q_error_fvm = np.abs(result_fvm['Q'] - Q_target) / Q_target * 100
    ax.plot(result_fdm['x'], Q_error_fdm, 'b-', linewidth=2, label='FDM (Preissmann)', alpha=0.7)
    ax.plot(result_fvm['x'], Q_error_fvm, 'r--', linewidth=2, label='FVM Steady (Newton)', alpha=0.7)
    ax.axhline(0.5, color='g', linestyle='--', linewidth=2, alpha=0.7, label='Target Precision (0.5%)')
    ax.axhline(2.32, color='orange', linestyle=':', linewidth=1.5, alpha=0.7, label='FDM Baseline (2.32%)')
    ax.axvline(2500, color='gray', linestyle=':', alpha=0.5)
    ax.axvline(5000, color='gray', linestyle=':', alpha=0.5)
    ax.axvline(7500, color='gray', linestyle=':', alpha=0.5)
    ax.set_xlabel('x [m]', fontsize=12)
    ax.set_ylabel('Discharge Error [%]', fontsize=12)
    ax.set_title('Discharge Error Comparison', fontsize=14, fontweight='bold')
    ax.legend(fontsize=11)
    ax.grid(True, alpha=0.3)

    plt.tight_layout()
    plt.savefig('fvm_steady_comparison.png', dpi=150, bbox_inches='tight')
    print(" Saved comparison plot: fvm_steady_comparison.png")
    print()


def main():
    """
    主测试函数
    """
    print("\n")
    print("*" * 70)
    print("*" + "  FVM Steady Solver - Final Precision Optimization Test".center(68) + "*")
    print("*" * 70)
    print("\n")

    # 运行测试
    result_fdm = run_fdm_baseline_test()
    result_fvm = run_fvm_steady_test()

    # 绘制对比
    plot_comparison(result_fdm, result_fvm)

    # 生成总结报告
    print("=" * 70)
    print("SUMMARY REPORT")
    print("=" * 70)
    print()

    print(f"{'Method':<30} {'Max Error':<15} {'Mean Error':<15} {'Converged':<10}")
    print("-" * 70)
    print(f"{'FDM (Preissmann)':<30} {result_fdm['max_error']:.4f}%{'':<8} "
          f"{result_fdm['mean_error']:.4f}%{'':<8} {'' if result_fdm['converged'] else ''}")
    print(f"{'FVM Steady (Newton)':<30} {result_fvm['max_error']:.4f}%{'':<8} "
          f"{result_fvm['mean_error']:.4f}%{'':<8} {'' if result_fvm['converged'] else ''}")
    print()

    # 计算改进效果
    if result_fvm['max_error'] > 0:
        improvement = result_fdm['max_error'] / result_fvm['max_error']
        absolute_improvement = result_fdm['max_error'] - result_fvm['max_error']
    else:
        improvement = float('inf')
        absolute_improvement = result_fdm['max_error']

    print("Improvement Analysis:")
    print(f"  Precision improvement: {improvement:.2f}x")
    print(f"  Absolute error reduction: {absolute_improvement:.4f}%")
    print()

    # 与目标比较
    fdm_baseline = 2.32
    target = 0.5

    print("Comparison with Targets:")
    print(f"  FDM Baseline (Phase 1-2): {fdm_baseline:.2f}%")
    print(f"  FDM (This test): {result_fdm['max_error']:.4f}%")
    print(f"  FVM Steady (New): {result_fvm['max_error']:.4f}%")
    print(f"  Target Precision: {target:.2f}%")
    print()

    # 最终评估
    if result_fvm['max_error'] < target:
        print(f" SUCCESS! FVM Steady achieved target precision {target}%!")
        print(f"     Improvement over FDM baseline: {fdm_baseline / result_fvm['max_error']:.2f}x")
    elif result_fvm['max_error'] < fdm_baseline:
        gap = target - result_fvm['max_error']
        print(f" EXCELLENT! FVM Steady improved precision (improvement: {improvement:.2f}x)")
        if result_fvm['max_error'] < 1.0:
            print(f"    Very close to target! Gap: {abs(gap):.4f}%")
        else:
            print(f"    Gap to target: {abs(gap):.4f}%")
    elif result_fvm['max_error'] < result_fdm['max_error']:
        print(f" GOOD! FVM Steady improved over FDM ({improvement:.2f}x), but target not reached")
        print(f"   Gap to target: {result_fvm['max_error'] - target:.4f}%")
    else:
        print(f" FVM Steady did not improve precision")
        print(f"  FVM: {result_fvm['max_error']:.4f}% vs FDM: {result_fdm['max_error']:.4f}%")

    print()
    print("=" * 70)


if __name__ == "__main__":
    main()
