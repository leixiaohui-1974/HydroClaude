"""
Phase 2高精度求解器验证脚本

测试三阶段收敛策略的精度提升效果

Author: Claude
Date: 2025-10-23
"""

import sys
import os
import numpy as np

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from solvers.single_canal_solver import SingleCanalSolver
from solvers.gate import SluiceGate

def test_phase2_precision():
    """测试Phase 2高精度求解器"""

    print("=" * 80)
    print("Phase 2 高精度求解器验证")
    print("=" * 80)
    print()

    # 系统配置（与脚本11相同）
    canal_length = 10000.0
    canal_width = 10.0
    n_points = 301
    bed_slope = 0.0005
    manning_n = 0.025
    Q_initial = 10.0

    # 创建三个闸门（与脚本11相同）
    gate1 = SluiceGate(position=2500.0, width=canal_width, opening=4.5, Cd=0.6)
    gate2 = SluiceGate(position=5000.0, width=canal_width, opening=4.0, Cd=0.6)
    gate3 = SluiceGate(position=7500.0, width=canal_width, opening=5.0, Cd=0.6)

    print("测试配置:")
    print(f"  渠道长度: {canal_length} m")
    print(f"  网格点数: {n_points}")
    print(f"  目标流量: {Q_initial} m³/s")
    print(f"  闸门1: 位置={gate1.position}m, 开度={gate1.get_opening(0)}m")
    print(f"  闸门2: 位置={gate2.position}m, 开度={gate2.get_opening(0)}m")
    print(f"  闸门3: 位置={gate3.position}m, 开度={gate3.get_opening(0)}m")
    print()

    # 创建求解器
    solver = SingleCanalSolver(
        total_length=canal_length,
        structures=[gate1, gate2, gate3],
        nx_total=n_points,
        B=canal_width,
        S0=bed_slope,
        n=manning_n
    )

    # 初始化
    solver.reset_with_steady_state(Q_initial)

    # ==================== 基准测试: 标准求解器 ====================
    print("=" * 80)
    print("基准测试: 标准求解器")
    print("=" * 80)

    solver_baseline = SingleCanalSolver(
        total_length=canal_length,
        structures=[gate1, gate2, gate3],
        nx_total=n_points,
        B=canal_width,
        S0=bed_slope,
        n=manning_n
    )
    solver_baseline.reset_with_steady_state(Q_initial)

    result_baseline = solver_baseline.solve_steady_state(
        Q_target=Q_initial,
        max_iterations=5000,
        convergence_tol=0.001,
        check_interval=500,
        verbose=True
    )

    profile_baseline = solver_baseline.get_full_profile()
    Q_baseline = profile_baseline['Q']
    Q_baseline_error = np.abs(Q_baseline - Q_initial) / Q_initial * 100
    Q_baseline_max_error = np.max(Q_baseline_error)

    print(f"\n标准求解器结果:")
    print(f"  最大相对误差: {Q_baseline_max_error:.4f}%")
    print(f"  迭代次数: {result_baseline['iterations']}")
    print()

    # ==================== 新方法: Phase 2三阶段求解器 ====================
    print("\n" + "=" * 80)
    print("Phase 2: 三阶段高精度求解器")
    print("=" * 80)

    solver_phase2 = SingleCanalSolver(
        total_length=canal_length,
        structures=[gate1, gate2, gate3],
        nx_total=n_points,
        B=canal_width,
        S0=bed_slope,
        n=manning_n
    )
    solver_phase2.reset_with_steady_state(Q_initial)

    result_phase2 = solver_phase2.solve_steady_state_phase2(
        Q_target=Q_initial,
        verbose=True
    )

    profile_phase2 = solver_phase2.get_full_profile()
    Q_phase2 = profile_phase2['Q']
    Q_phase2_error = np.abs(Q_phase2 - Q_initial) / Q_initial * 100
    Q_phase2_max_error = np.max(Q_phase2_error)

    print(f"\nPhase 2求解器结果:")
    print(f"  最大相对误差: {Q_phase2_max_error:.4f}%")
    print(f"  总迭代次数: {result_phase2['total_iterations']}")
    print()

    # ==================== 对比分析 ====================
    print("\n" + "=" * 80)
    print("精度对比分析")
    print("=" * 80)

    precision_improvement = Q_baseline_max_error / Q_phase2_max_error if Q_phase2_max_error > 0 else float('inf')

    print(f"\n标准求解器:")
    print(f"  最大误差: {Q_baseline_max_error:.4f}%")
    print(f"  迭代次数: {result_baseline['iterations']}")
    print(f"  仿真时间: {solver_baseline.current_time:.0f}s")

    print(f"\nPhase 2求解器:")
    print(f"  最大误差: {Q_phase2_max_error:.4f}%")
    print(f"  迭代次数: {result_phase2['total_iterations']}")
    print(f"  仿真时间: {solver_phase2.current_time:.0f}s")

    print(f"\n性能提升:")
    print(f"  精度提升: {precision_improvement:.2f}x")
    print(f"  是否达到目标(0.5%): {'✓ 是' if Q_phase2_max_error < 0.5 else '✗ 否'}")

    # 判断测试成功与否
    if Q_phase2_max_error < Q_baseline_max_error:
        print("\n✓✓✓ Phase 2求解器精度提升成功！")
        return True
    else:
        print("\n✗✗✗ Phase 2求解器未能提升精度")
        return False


if __name__ == "__main__":
    success = test_phase2_precision()
    sys.exit(0 if success else 1)
