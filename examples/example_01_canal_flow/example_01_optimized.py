"""
优化版例子1：闸门流动模拟

优化策略：
1. 调整收敛容差从0.5%到1%（更现实的工程精度）
2. 使用简化求解器生成更好的初值
3. 使用自适应松弛法

Author: Claude
Date: 2025-10-22
"""

import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

import numpy as np
import time
from solvers.single_canal_solver import SingleCanalSolver
from solvers.steady_profile_solver import SteadyProfileSolver
from solvers.gate import SluiceGate
from utils.canal_utils import compute_steady_uniform_flow


def run_optimized_example():
    """运行优化版例子1"""

    print("=" * 100)
    print("优化版例子1：单闸门流动模拟")
    print("=" * 100)
    print()

    # 系统配置
    canal_length = 10000.0
    canal_width = 10.0
    gate_position = 5000.0
    n_points = 301

    bed_slope = 0.0005
    manning_n = 0.025

    gate_opening = 5.0
    gate_Cd = 0.6
    Q_target = 10.0

    print("系统配置:")
    print(f"  渠道长度: {canal_length} m")
    print(f"  渠道宽度: {canal_width} m")
    print(f"  空间点数: {n_points}")
    print(f"  闸门位置: {gate_position} m")
    print(f"  闸门开度: {gate_opening} m")
    print(f"  目标流量: {Q_target} m³/s")
    print()

    # 创建闸门
    gate = SluiceGate(
        position=gate_position,
        width=canal_width,
        opening=gate_opening,
        Cd=gate_Cd
    )

    # ========== 方法1：标准求解（自适应松弛，0.5%容差）==========
    print("=" * 100)
    print("方法1：标准求解（自适应松弛，0.5%容差）")
    print("-" * 100)

    solver1 = SingleCanalSolver(
        total_length=canal_length,
        structures=[gate],
        nx_total=n_points,
        B=canal_width,
        S0=bed_slope,
        n=manning_n
    )

    solver1.reset_with_steady_state(Q_target)

    start_time = time.time()
    result1 = solver1.solve_steady_state(
        Q_target=Q_target,
        max_iterations=10000,
        convergence_tol=0.005,  # 0.5%
        adaptive_relax=True,
        verbose=True
    )
    time1 = time.time() - start_time

    print(f"\n结果:")
    print(f"  收敛: {'是' if result1['converged'] else '否'}")
    print(f"  迭代次数: {result1['iterations']}")
    print(f"  最终误差: {result1['final_error']*100:.4f}%")
    print(f"  计算时间: {time1:.4f}s")

    # ========== 方法2：宽松容差（1%）==========
    print("\n\n" + "=" * 100)
    print("方法2：宽松容差（自适应松弛，1%容差）")
    print("-" * 100)

    solver2 = SingleCanalSolver(
        total_length=canal_length,
        structures=[gate],
        nx_total=n_points,
        B=canal_width,
        S0=bed_slope,
        n=manning_n
    )

    solver2.reset_with_steady_state(Q_target)

    start_time = time.time()
    result2 = solver2.solve_steady_state(
        Q_target=Q_target,
        max_iterations=10000,
        convergence_tol=0.01,  # 1%（工程精度）
        adaptive_relax=True,
        verbose=True
    )
    time2 = time.time() - start_time

    print(f"\n结果:")
    print(f"  收敛: {'是' if result2['converged'] else '否'}")
    print(f"  迭代次数: {result2['iterations']}")
    print(f"  最终误差: {result2['final_error']*100:.4f}%")
    print(f"  计算时间: {time2:.4f}s")

    # ========== 方法3：简化求解器初值 + 1%容差 ==========
    print("\n\n" + "=" * 100)
    print("方法3：简化求解器初值 + 自适应松弛（1%容差）")
    print("-" * 100)

    # 步骤1：使用简化求解器快速预求解
    print("\n步骤1：使用简化求解器预求解...")

    profile_solver = SteadyProfileSolver(
        length=canal_length,
        B=canal_width,
        S0=bed_slope,
        n=manning_n
    )

    h_downstream = compute_steady_uniform_flow(Q_target, canal_width, bed_slope, manning_n)

    start_time_init = time.time()
    result_init = profile_solver.solve_with_single_gate(
        Q=Q_target,
        h_downstream=h_downstream,
        gate_position=gate_position,
        gate=gate,
        nx=n_points
    )
    time_init = time.time() - start_time_init

    print(f"  简化求解器完成: {time_init:.4f}s")
    print(f"  闸前水深: {result_init['h_gate_up']:.4f} m")
    print(f"  闸后水深: {result_init['h_gate_down']:.4f} m")

    # 步骤2：使用预求解结果作为初值
    print("\n步骤2：使用预求解结果精细求解...")

    solver3 = SingleCanalSolver(
        total_length=canal_length,
        structures=[gate],
        nx_total=n_points,
        B=canal_width,
        S0=bed_slope,
        n=manning_n
    )

    # 使用简化求解器的结果作为初值
    solver3.solver.h[:] = result_init['h']
    solver3.solver.Q[:] = result_init['Q']

    start_time = time.time()
    result3 = solver3.solve_steady_state(
        Q_target=Q_target,
        max_iterations=10000,
        convergence_tol=0.01,  # 1%
        adaptive_relax=True,
        verbose=True
    )
    time3 = time.time() - start_time
    time3_total = time3 + time_init

    print(f"\n结果:")
    print(f"  收敛: {'是' if result3['converged'] else '否'}")
    print(f"  迭代次数: {result3['iterations']}")
    print(f"  最终误差: {result3['final_error']*100:.4f}%")
    print(f"  精细求解时间: {time3:.4f}s")
    print(f"  总时间（含预求解）: {time3_total:.4f}s")

    # ========== 性能对比 ==========
    print("\n\n" + "=" * 100)
    print("性能对比总结")
    print("=" * 100)
    print()

    methods = [
        ("方法1: 标准（0.5%）", result1, time1),
        ("方法2: 宽松（1%）", result2, time2),
        ("方法3: 优化初值（1%）", result3, time3_total)
    ]

    print(f"{'方法':<30} {'收敛':<8} {'迭代次数':<10} {'误差':<12} {'时间(s)':<10}")
    print("-" * 100)

    for name, result, elapsed in methods:
        converged = "✓" if result['converged'] else "✗"
        print(f"{name:<30} {converged:<8} {result['iterations']:<10} "
              f"{result['final_error']*100:>6.4f}%     {elapsed:>6.4f}")

    print()

    # 计算改进
    if result2['converged'] and result1['converged']:
        iter_improve = (result1['iterations'] - result2['iterations']) / result1['iterations'] * 100
        time_improve = (time1 - time2) / time1 * 100
        print(f"方法2相对方法1:")
        print(f"  迭代次数: {result1['iterations']} → {result2['iterations']} "
              f"({'↓' if iter_improve > 0 else '↑'}{abs(iter_improve):.1f}%)")
        print(f"  计算时间: {time1:.4f}s → {time2:.4f}s "
              f"({'↓' if time_improve > 0 else '↑'}{abs(time_improve):.1f}%)")
        print()

    if result3['converged'] and result1['converged']:
        iter_improve = (result1['iterations'] - result3['iterations']) / result1['iterations'] * 100
        time_improve = (time1 - time3_total) / time1 * 100
        print(f"方法3相对方法1:")
        print(f"  迭代次数: {result1['iterations']} → {result3['iterations']} "
              f"({'↓' if iter_improve > 0 else '↑'}{abs(iter_improve):.1f}%)")
        print(f"  计算时间: {time1:.4f}s → {time3_total:.4f}s "
              f"({'↓' if time_improve > 0 else '↑'}{abs(time_improve):.1f}%)")

    print("\n" + "=" * 100)
    print("完成！")
    print("=" * 100)


if __name__ == "__main__":
    run_optimized_example()
