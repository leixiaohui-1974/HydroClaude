"""
性能对比测试：自适应松弛因子 vs 固定松弛因子

对比三个场景的收敛性能：
1. 单闸门
2. 三闸门串联
3. 混合结构（闸门+堰+孔口）

Author: Claude
Date: 2025-10-22
"""

import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

import numpy as np
import time
# DEPRECATED: Use HydrostaticCanalSolver instead
# from solvers.single_canal_solver import SingleCanalSolver
from solvers.gate import SluiceGate, BroadCrestedWeir, Orifice


def test_scenario(name: str, structures: list, Q_target: float = 10.0,
                 canal_length: float = 10000.0, canal_width: float = 10.0,
                 n_points: int = 301):
    """
    测试单个场景，对比固定松弛和自适应松弛的性能

    Returns:
        dict: 包含两种方法的性能指标
    """
    print(f"\n{'='*80}")
    print(f"场景: {name}")
    print(f"{'='*80}")

    results = {}

    for adaptive in [False, True]:
        mode_name = "自适应松弛" if adaptive else "固定松弛"
        print(f"\n{mode_name}:")
        print("-" * 80)

        # 创建求解器
        solver = SingleCanalSolver(
            total_length=canal_length,
            structures=structures,
            nx_total=n_points,
            B=canal_width,
            S0=0.0005,
            n=0.025
        )

        # 初始化
        solver.reset_with_steady_state(Q_target)

        # 计时开始
        start_time = time.time()

        # 稳态求解
        result = solver.solve_steady_state(
            Q_target=Q_target,
            max_iterations=10000,
            convergence_tol=0.005,  # 目标：< 0.5% (更现实的目标)
            check_interval=1000,
            adaptive_relax=adaptive,
            verbose=True
        )

        # 计时结束
        elapsed_time = time.time() - start_time

        # 记录结果
        results[mode_name] = {
            'converged': result['converged'],
            'iterations': result['iterations'],
            'final_error': result['final_error'],
            'elapsed_time': elapsed_time,
            'gate_flows': result['gate_flows']
        }

        print(f"\n结果:")
        print(f"  收敛: {'是' if result['converged'] else '否'}")
        print(f"  迭代次数: {result['iterations']}")
        print(f"  最终误差: {result['final_error']*100:.4f}%")
        print(f"  计算时间: {elapsed_time:.2f}s")
        print(f"  闸门流量: {', '.join([f'{q:.3f}' for q in result['gate_flows']])} m³/s")

    return results


def main():
    """主测试程序"""

    print("=" * 80)
    print("自适应松弛因子性能对比测试")
    print("=" * 80)
    print("\n测试目标：")
    print("  - 对比固定松弛因子和自适应松弛因子（Aitken加速）的收敛性能")
    print("  - 目标收敛精度：< 0.5%")
    print("  - 最大迭代次数：10000")
    print()

    # 通用参数
    canal_length = 10000.0
    canal_width = 10.0
    n_points = 301
    Q_target = 10.0

    all_results = {}

    # ========== 场景1: 单闸门 ==========
    gate1 = SluiceGate(position=5000.0, width=canal_width, opening=5.0, Cd=0.6)
    results1 = test_scenario(
        name="单闸门",
        structures=[gate1],
        Q_target=Q_target,
        canal_length=canal_length,
        canal_width=canal_width,
        n_points=n_points
    )
    all_results["单闸门"] = results1

    # ========== 场景2: 三闸门串联 ==========
    gate_a = SluiceGate(position=2500.0, width=canal_width, opening=4.5, Cd=0.6)
    gate_b = SluiceGate(position=5000.0, width=canal_width, opening=4.0, Cd=0.6)
    gate_c = SluiceGate(position=7500.0, width=canal_width, opening=5.0, Cd=0.6)
    results2 = test_scenario(
        name="三闸门串联",
        structures=[gate_a, gate_b, gate_c],
        Q_target=Q_target,
        canal_length=canal_length,
        canal_width=canal_width,
        n_points=n_points
    )
    all_results["三闸门串联"] = results2

    # ========== 场景3: 混合结构 ==========
    gate_mixed = SluiceGate(position=2500.0, width=canal_width, opening=3.5, Cd=0.6)
    weir = BroadCrestedWeir(position=5000.0, width=canal_width, crest_height=0.5, Cd=0.848)
    orifice = Orifice(position=7500.0, width=4.0, height=2.0, bottom_elevation=0.2, Cd=0.61)
    results3 = test_scenario(
        name="混合结构（闸门+堰+孔口）",
        structures=[gate_mixed, weir, orifice],
        Q_target=Q_target,
        canal_length=canal_length,
        canal_width=canal_width,
        n_points=n_points
    )
    all_results["混合结构"] = results3

    # ========== 生成汇总报告 ==========
    print(f"\n\n{'='*80}")
    print("汇总报告")
    print("=" * 80)
    print()

    # 创建对比表格
    print(f"{'场景':<20} {'方法':<15} {'迭代次数':<12} {'最终误差':<15} {'计算时间':<12} {'收敛':<8}")
    print("-" * 90)

    for scenario_name, scenario_results in all_results.items():
        for method_name, method_results in scenario_results.items():
            converged_str = "" if method_results['converged'] else ""
            print(f"{scenario_name:<20} {method_name:<15} {method_results['iterations']:<12} "
                  f"{method_results['final_error']*100:>6.4f}%       "
                  f"{method_results['elapsed_time']:>6.2f}s      {converged_str:<8}")
        print()

    # 计算改进百分比
    print("\n性能改进分析:")
    print("-" * 80)

    for scenario_name, scenario_results in all_results.items():
        fixed = scenario_results['固定松弛']
        adaptive = scenario_results['自适应松弛']

        # 迭代次数改进
        if fixed['converged'] and adaptive['converged']:
            iter_improvement = (fixed['iterations'] - adaptive['iterations']) / fixed['iterations'] * 100
            error_improvement = (fixed['final_error'] - adaptive['final_error']) / fixed['final_error'] * 100
            time_improvement = (fixed['elapsed_time'] - adaptive['elapsed_time']) / fixed['elapsed_time'] * 100

            print(f"\n{scenario_name}:")
            print(f"  迭代次数: {fixed['iterations']} → {adaptive['iterations']} "
                  f"({'↓' if iter_improvement > 0 else '↑'}{abs(iter_improvement):.1f}%)")
            print(f"  最终误差: {fixed['final_error']*100:.4f}% → {adaptive['final_error']*100:.4f}% "
                  f"({'↓' if error_improvement > 0 else '↑'}{abs(error_improvement):.1f}%)")
            print(f"  计算时间: {fixed['elapsed_time']:.2f}s → {adaptive['elapsed_time']:.2f}s "
                  f"({'↓' if time_improvement > 0 else '↑'}{abs(time_improvement):.1f}%)")
        elif not fixed['converged'] and adaptive['converged']:
            print(f"\n{scenario_name}:")
            print(f"  固定松弛未收敛，自适应松弛成功收敛！")
            print(f"  自适应结果: {adaptive['iterations']}次迭代, 误差{adaptive['final_error']*100:.4f}%")

    print("\n" + "=" * 80)
    print("测试完成！")
    print("=" * 80)


if __name__ == "__main__":
    main()
