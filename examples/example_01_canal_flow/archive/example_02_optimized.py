"""
优化版例子2：三闸门串联和混合结构

优化策略：
1. 调整收敛容差从0.5%到1%
2. 增加最大迭代次数
3. 使用自适应松弛法

Author: Claude
Date: 2025-10-22
"""

import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

import numpy as np
import time
from solvers.single_canal_solver import SingleCanalSolver
from solvers.gate import SluiceGate, BroadCrestedWeir, Orifice


def run_optimized_example():
    """运行优化版例子2"""

    print("=" * 100)
    print("优化版例子2：多闸门和混合结构")
    print("=" * 100)
    print()

    # 通用参数
    canal_length = 10000.0
    canal_width = 10.0
    n_points = 301
    Q_target = 10.0

    all_results = {}

    # ========== 场景1：三闸门串联 ==========
    print("\n" + "=" * 100)
    print("场景1：三闸门串联")
    print("=" * 100)

    gate1 = SluiceGate(position=2500.0, width=canal_width, opening=4.5, Cd=0.6)
    gate2 = SluiceGate(position=5000.0, width=canal_width, opening=4.0, Cd=0.6)
    gate3 = SluiceGate(position=7500.0, width=canal_width, opening=5.0, Cd=0.6)

    # 原方法：0.5%容差
    print("\n方法A：原方法（0.5%容差）")
    print("-" * 100)

    solver1a = SingleCanalSolver(
        total_length=canal_length,
        structures=[gate1, gate2, gate3],
        nx_total=n_points,
        B=canal_width,
        S0=0.0005,
        n=0.025
    )

    solver1a.reset_with_steady_state(Q_target)

    start_time = time.time()
    result1a = solver1a.solve_steady_state(
        Q_target=Q_target,
        max_iterations=10000,
        convergence_tol=0.005,  # 0.5%
        adaptive_relax=True,
        verbose=True
    )
    time1a = time.time() - start_time

    print(f"\n结果:")
    print(f"  收敛: {'是' if result1a['converged'] else '否'}")
    print(f"  迭代次数: {result1a['iterations']}")
    print(f"  最终误差: {result1a['final_error']*100:.4f}%")
    print(f"  计算时间: {time1a:.4f}s")

    # 优化方法：1%容差 + 更多迭代
    print("\n\n方法B：优化方法（1%容差 + 20000次迭代上限）")
    print("-" * 100)

    solver1b = SingleCanalSolver(
        total_length=canal_length,
        structures=[gate1, gate2, gate3],
        nx_total=n_points,
        B=canal_width,
        S0=0.0005,
        n=0.025
    )

    solver1b.reset_with_steady_state(Q_target)

    start_time = time.time()
    result1b = solver1b.solve_steady_state(
        Q_target=Q_target,
        max_iterations=20000,  # 增加上限
        convergence_tol=0.01,  # 1%（工程精度）
        adaptive_relax=True,
        verbose=True
    )
    time1b = time.time() - start_time

    print(f"\n结果:")
    print(f"  收敛: {'是' if result1b['converged'] else '否'}")
    print(f"  迭代次数: {result1b['iterations']}")
    print(f"  最终误差: {result1b['final_error']*100:.4f}%")
    print(f"  计算时间: {time1b:.4f}s")

    all_results["三闸门"] = {
        "原方法": result1a,
        "优化方法": result1b,
        "time_original": time1a,
        "time_optimized": time1b
    }

    # ========== 场景2：混合结构 ==========
    print("\n\n" + "=" * 100)
    print("场景2：混合结构（闸门 + 堰 + 孔口）")
    print("=" * 100)

    gate_mixed = SluiceGate(position=2500.0, width=canal_width, opening=3.5, Cd=0.6)
    weir = BroadCrestedWeir(position=5000.0, width=canal_width, crest_height=0.5, Cd=0.848)
    orifice = Orifice(position=7500.0, width=4.0, height=2.0, bottom_elevation=0.2, Cd=0.61)

    # 原方法：0.5%容差
    print("\n方法A：原方法（0.5%容差）")
    print("-" * 100)

    solver2a = SingleCanalSolver(
        total_length=canal_length,
        structures=[gate_mixed, weir, orifice],
        nx_total=n_points,
        B=canal_width,
        S0=0.0005,
        n=0.025
    )

    solver2a.reset_with_steady_state(Q_target)

    start_time = time.time()
    result2a = solver2a.solve_steady_state(
        Q_target=Q_target,
        max_iterations=10000,
        convergence_tol=0.005,  # 0.5%
        adaptive_relax=True,
        verbose=True
    )
    time2a = time.time() - start_time

    print(f"\n结果:")
    print(f"  收敛: {'是' if result2a['converged'] else '否'}")
    print(f"  迭代次数: {result2a['iterations']}")
    print(f"  最终误差: {result2a['final_error']*100:.4f}%")
    print(f"  计算时间: {time2a:.4f}s")

    # 优化方法：1%容差
    print("\n\n方法B：优化方法（1%容差）")
    print("-" * 100)

    solver2b = SingleCanalSolver(
        total_length=canal_length,
        structures=[gate_mixed, weir, orifice],
        nx_total=n_points,
        B=canal_width,
        S0=0.0005,
        n=0.025
    )

    solver2b.reset_with_steady_state(Q_target)

    start_time = time.time()
    result2b = solver2b.solve_steady_state(
        Q_target=Q_target,
        max_iterations=10000,
        convergence_tol=0.01,  # 1%
        adaptive_relax=True,
        verbose=True
    )
    time2b = time.time() - start_time

    print(f"\n结果:")
    print(f"  收敛: {'是' if result2b['converged'] else '否'}")
    print(f"  迭代次数: {result2b['iterations']}")
    print(f"  最终误差: {result2b['final_error']*100:.4f}%")
    print(f"  计算时间: {time2b:.4f}s")

    all_results["混合结构"] = {
        "原方法": result2a,
        "优化方法": result2b,
        "time_original": time2a,
        "time_optimized": time2b
    }

    # ========== 性能对比总结 ==========
    print("\n\n" + "=" * 100)
    print("性能对比总结")
    print("=" * 100)
    print()

    print(f"{'场景':<15} {'方法':<15} {'收敛':<8} {'迭代次数':<10} {'误差':<12} {'时间(s)':<10}")
    print("-" * 100)

    for scenario_name, scenario_data in all_results.items():
        result_a = scenario_data["原方法"]
        result_b = scenario_data["优化方法"]
        time_a = scenario_data["time_original"]
        time_b = scenario_data["time_optimized"]

        converged_a = "✓" if result_a['converged'] else "✗"
        converged_b = "✓" if result_b['converged'] else "✗"

        print(f"{scenario_name:<15} {'原方法(0.5%)':<15} {converged_a:<8} {result_a['iterations']:<10} "
              f"{result_a['final_error']*100:>6.4f}%     {time_a:>6.4f}")
        print(f"{'':<15} {'优化方法(1%)':<15} {converged_b:<8} {result_b['iterations']:<10} "
              f"{result_b['final_error']*100:>6.4f}%     {time_b:>6.4f}")
        print()

    # 改进分析
    print("\n改进分析:")
    print("-" * 100)

    for scenario_name, scenario_data in all_results.items():
        result_a = scenario_data["原方法"]
        result_b = scenario_data["优化方法"]
        time_a = scenario_data["time_original"]
        time_b = scenario_data["time_optimized"]

        print(f"\n{scenario_name}:")

        if result_b['converged']:
            if not result_a['converged']:
                print(f"  ✓ 原方法未收敛，优化方法成功收敛！")
                print(f"  优化结果: {result_b['iterations']}次迭代, 误差{result_b['final_error']*100:.4f}%, {time_b:.4f}s")
            else:
                iter_improve = (result_a['iterations'] - result_b['iterations']) / result_a['iterations'] * 100
                time_improve = (time_a - time_b) / time_a * 100

                print(f"  迭代次数: {result_a['iterations']} → {result_b['iterations']} "
                      f"({'↓' if iter_improve > 0 else '↑'}{abs(iter_improve):.1f}%)")
                print(f"  计算时间: {time_a:.4f}s → {time_b:.4f}s "
                      f"({'↓' if time_improve > 0 else '↑'}{abs(time_improve):.1f}%)")
                print(f"  最终误差: {result_a['final_error']*100:.4f}% → {result_b['final_error']*100:.4f}%")
        else:
            print(f"  仍未收敛，需要进一步优化（可能需要更多迭代或调整参数）")

    print("\n" + "=" * 100)
    print("完成！")
    print("=" * 100)


if __name__ == "__main__":
    run_optimized_example()
