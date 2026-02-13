#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
网格加密全面测试

充分测试各种网格配置，生成完整的性能对比报告

作者: Claude
日期: 2025-10-23
"""

import sys
import pytest
import warnings
warnings.filterwarnings("ignore")
import os
import numpy as np
import time

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


def comprehensive_test():
    """
    全面测试网格配置
    """

    print("\n" + "=" * 100)
    print(" " * 35 + "网格加密全面测试")
    print("=" * 100)
    print()

    # 系统配置
    canal_length = 10000.0
    canal_width = 10.0
    bed_slope = 0.0005
    manning_n = 0.025
    Q_initial = 10.0

    # 创建三个闸门
    gate1 = SluiceGate(position=2500.0, width=canal_width, opening=4.5, Cd=0.6)
    gate2 = SluiceGate(position=5000.0, width=canal_width, opening=4.0, Cd=0.6)
    gate3 = SluiceGate(position=7500.0, width=canal_width, opening=5.0, Cd=0.6)

    print("测试场景: 三个闸门串联（最困难场景）")
    print(f"  渠道长度: {canal_length} m")
    print(f"  闸门1: 位置={gate1.position}m, 开度={gate1.get_opening(0)}m")
    print(f"  闸门2: 位置={gate2.position}m, 开度={gate2.get_opening(0)}m (最小，最大阻力)")
    print(f"  闸门3: 位置={gate3.position}m, 开度={gate3.get_opening(0)}m")
    print(f"  目标流量: {Q_initial} m^3/s")
    print()

    # 定义测试配置
    test_configs = [
        # 基准测试
        {
            "name": "基准-均匀粗网格",
            "use_adaptive": False,
            "nx": 201,
            "dx_fine": None,
            "radius": None,
            "dx_coarse": None,
            "max_iter": 5000,
            "tol": 0.001
        },
        {
            "name": "基准-均匀标准网格",
            "use_adaptive": False,
            "nx": 301,
            "dx_fine": None,
            "radius": None,
            "dx_coarse": None,
            "max_iter": 5000,
            "tol": 0.001
        },
        {
            "name": "基准-均匀密网格",
            "use_adaptive": False,
            "nx": 501,
            "dx_fine": None,
            "radius": None,
            "dx_coarse": None,
            "max_iter": 5000,
            "tol": 0.001
        },

        # 自适应网格测试 - 不同精细度
        {
            "name": "自适应-粗加密(dx=10m)",
            "use_adaptive": True,
            "nx": 301,
            "dx_fine": 10.0,
            "radius": 200.0,
            "dx_coarse": 40.0,
            "max_iter": 5000,
            "tol": 0.001
        },
        {
            "name": "自适应-标准(dx=5m)",
            "use_adaptive": True,
            "nx": 301,
            "dx_fine": 5.0,
            "radius": 200.0,
            "dx_coarse": 33.0,
            "max_iter": 5000,
            "tol": 0.001
        },
        {
            "name": "自适应-精细(dx=3m)",
            "use_adaptive": True,
            "nx": 301,
            "dx_fine": 3.0,
            "radius": 200.0,
            "dx_coarse": 33.0,
            "max_iter": 7500,
            "tol": 0.0005
        },
        {
            "name": "自适应-超精细(dx=2m)",
            "use_adaptive": True,
            "nx": 301,
            "dx_fine": 2.0,
            "radius": 200.0,
            "dx_coarse": 35.0,
            "max_iter": 10000,
            "tol": 0.0001
        },
        {
            "name": "自适应-极精细(dx=1m)",
            "use_adaptive": True,
            "nx": 301,
            "dx_fine": 1.0,
            "radius": 200.0,
            "dx_coarse": 40.0,
            "max_iter": 15000,
            "tol": 0.0001
        },

        # 自适应网格测试 - 不同加密半径
        {
            "name": "自适应-小半径(+/-150m)",
            "use_adaptive": True,
            "nx": 301,
            "dx_fine": 5.0,
            "radius": 150.0,
            "dx_coarse": 33.0,
            "max_iter": 5000,
            "tol": 0.001
        },
        {
            "name": "自适应-大半径(+/-300m)",
            "use_adaptive": True,
            "nx": 301,
            "dx_fine": 5.0,
            "radius": 300.0,
            "dx_coarse": 33.0,
            "max_iter": 7500,
            "tol": 0.001
        },
        {
            "name": "自适应-超大半径(+/-500m)",
            "use_adaptive": True,
            "nx": 301,
            "dx_fine": 5.0,
            "radius": 500.0,
            "dx_coarse": 40.0,
            "max_iter": 7500,
            "tol": 0.001
        },

        # 组合优化配置
        {
            "name": "优化-平衡配置",
            "use_adaptive": True,
            "nx": 301,
            "dx_fine": 3.0,
            "radius": 250.0,
            "dx_coarse": 35.0,
            "max_iter": 10000,
            "tol": 0.0005
        },
        {
            "name": "优化-极致配置",
            "use_adaptive": True,
            "nx": 301,
            "dx_fine": 1.5,
            "radius": 300.0,
            "dx_coarse": 40.0,
            "max_iter": 20000,
            "tol": 0.0001
        },
    ]

    results = []

    # 运行所有测试
    for i, config in enumerate(test_configs):
        print("\n" + "=" * 100)
        print(f"测试 {i+1}/{len(test_configs)}: {config['name']}")
        print("=" * 100)

        if config['use_adaptive']:
            print(f"  配置: 自适应网格")
            print(f"    精细区间距: {config['dx_fine']} m")
            print(f"    加密半径: +/-{config['radius']} m")
            print(f"    粗网格间距: {config['dx_coarse']} m")
        else:
            print(f"  配置: 均匀网格")
            print(f"    网格点数: {config['nx']}")
            print(f"    网格间距: {canal_length/(config['nx']-1):.2f} m")

        print(f"  迭代设置: max_iter={config['max_iter']}, tol={config['tol']}")
        print()

        # 创建求解器
        start_time = time.time()

        solver = SingleCanalSolver(
            total_length=canal_length,
            structures=[gate1, gate2, gate3],
            nx_total=config['nx'],
            B=canal_width,
            S0=bed_slope,
            n=manning_n,
            use_adaptive_grid=config['use_adaptive'],
            refinement_radius=config['radius'] if config['use_adaptive'] else 200.0,
            dx_fine=config['dx_fine'] if config['use_adaptive'] else 5.0,
            dx_coarse=config['dx_coarse'] if config['use_adaptive'] else 33.0
        )

        setup_time = time.time() - start_time

        solver.reset_with_steady_state(Q_initial)

        # 求解
        solve_start = time.time()
        result = solver.solve_steady_state(
            Q_target=Q_initial,
            max_iterations=config['max_iter'],
            convergence_tol=config['tol'],
            check_interval=500,
            verbose=True
        )
        solve_time = time.time() - solve_start

        # 获取结果
        profile = solver.get_full_profile()
        Q = profile['Q']
        x = profile['x']
        h = profile['h']

        # 计算误差
        Q_error = np.abs(Q - Q_initial) / Q_initial * 100
        max_error = np.max(Q_error)
        mean_error = np.mean(Q_error[1:-1])  # 排除边界

        gate_flows = solver.get_gate_flows()
        gate_errors = [abs(gf - Q_initial) / Q_initial * 100 for gf in gate_flows]

        # 计算守恒性
        Q_std = np.std(Q[1:-1])
        conservation_quality = Q_std / Q_initial * 100

        # 记录结果
        result_data = {
            "name": config['name'],
            "use_adaptive": config['use_adaptive'],
            "n_points": len(x),
            "dx_min": np.min(np.diff(x)) if len(x) > 1 else 0,
            "dx_max": np.max(np.diff(x)) if len(x) > 1 else 0,
            "dx_mean": np.mean(np.diff(x)) if len(x) > 1 else 0,
            "max_error": max_error,
            "mean_error": mean_error,
            "gate1_error": gate_errors[0],
            "gate2_error": gate_errors[1],
            "gate3_error": gate_errors[2],
            "conservation_quality": conservation_quality,
            "iterations": result['iterations'],
            "converged": result['converged'],
            "setup_time": setup_time,
            "solve_time": solve_time,
            "total_time": setup_time + solve_time,
            "final_convergence_error": result['final_error'] * 100
        }

        results.append(result_data)

        # 打印摘要
        print(f"\n结果摘要:")
        print(f"  网格点数: {result_data['n_points']}")
        print(f"  网格间距: {result_data['dx_min']:.2f} - {result_data['dx_max']:.2f} m (平均: {result_data['dx_mean']:.2f} m)")
        print(f"  最大误差: {max_error:.4f}%")
        print(f"  平均误差: {mean_error:.4f}%")
        print(f"  闸门误差: G1={gate_errors[0]:.4f}%, G2={gate_errors[1]:.4f}%, G3={gate_errors[2]:.4f}%")
        print(f"  守恒性指标: {conservation_quality:.4f}% (越小越好)")
        print(f"  迭代次数: {result['iterations']}")
        print(f"  收敛状态: {' 收敛' if result['converged'] else ' 未收敛'}")
        print(f"  计算时间: {solve_time:.2f}s")

    # 生成完整报告
    print("\n\n" + "=" * 100)
    print(" " * 40 + "完整测试报告")
    print("=" * 100)
    print()

    # 表格1: 基本信息
    print("表1: 网格配置与误差")
    print("-" * 100)
    print(f"{'配置':<25} | {'点数':>6} | {'dx范围':>12} | {'最大误差':>9} | {'平均误差':>9} | {'G2误差':>9}")
    print("-" * 100)

    for r in results:
        dx_range = f"{r['dx_min']:.1f}-{r['dx_max']:.1f}m" if r['dx_min'] != r['dx_max'] else f"{r['dx_mean']:.1f}m"
        print(f"{r['name']:<25} | {r['n_points']:6d} | {dx_range:>12} | {r['max_error']:8.4f}% | "
              f"{r['mean_error']:8.4f}% | {r['gate2_error']:8.4f}%")

    # 表格2: 性能对比
    print("\n表2: 计算性能")
    print("-" * 100)
    print(f"{'配置':<25} | {'点数':>6} | {'迭代次数':>9} | {'计算时间':>9} | {'单步耗时':>9} | {'收敛状态'}")
    print("-" * 100)

    for r in results:
        time_per_iter = r['solve_time'] / r['iterations'] * 1000  # ms
        status = "" if r['converged'] else ""
        print(f"{r['name']:<25} | {r['n_points']:6d} | {r['iterations']:9d} | {r['solve_time']:8.2f}s | "
              f"{time_per_iter:8.2f}ms | {status}")

    # 找出最佳配置
    print("\n\n" + "=" * 100)
    print("关键发现")
    print("=" * 100)
    print()

    # 按误差排序
    sorted_by_error = sorted(results, key=lambda x: x['max_error'])
    best_accuracy = sorted_by_error[0]

    print(f"1. 最高精度配置: {best_accuracy['name']}")
    print(f"   最大误差: {best_accuracy['max_error']:.4f}%")
    print(f"   网格点数: {best_accuracy['n_points']}")
    print(f"   计算时间: {best_accuracy['solve_time']:.2f}s")
    print()

    # 按性价比排序（误差改善/时间增加）
    baseline = results[1]  # 均匀标准网格
    cost_effectiveness = []
    for r in results[3:]:  # 跳过基准测试
        error_improvement = baseline['max_error'] / r['max_error']
        time_cost = r['solve_time'] / baseline['solve_time']
        ce_ratio = error_improvement / time_cost if time_cost > 0 else 0
        cost_effectiveness.append((r, error_improvement, time_cost, ce_ratio))

    cost_effectiveness.sort(key=lambda x: x[3], reverse=True)
    best_ce = cost_effectiveness[0]

    print(f"2. 最佳性价比配置: {best_ce[0]['name']}")
    print(f"   精度提升: {best_ce[1]:.2f}x")
    print(f"   时间成本: {best_ce[2]:.2f}x")
    print(f"   性价比指标: {best_ce[3]:.2f}")
    print(f"   最大误差: {best_ce[0]['max_error']:.4f}%")
    print()

    # 阶段1目标评估
    target_met = [r for r in results if r['max_error'] < 0.5]

    print(f"3. 阶段1目标评估 (目标: <0.5%)")
    if target_met:
        print(f"    达标配置数: {len(target_met)}/{len(results)}")
        for r in target_met:
            print(f"     - {r['name']}: {r['max_error']:.4f}%")
    else:
        print(f"    无配置达标")
        print(f"   最接近: {sorted_by_error[0]['name']} ({sorted_by_error[0]['max_error']:.4f}%)")
        print(f"   差距: {sorted_by_error[0]['max_error'] - 0.5:.4f}%")
    print()

    # 网格加密效益分析
    print(f"4. 网格加密效益分析")
    uniform_201 = results[0]
    uniform_301 = results[1]
    uniform_501 = results[2]

    print(f"   均匀网格:")
    print(f"     201点: {uniform_201['max_error']:.4f}%")
    print(f"     301点: {uniform_301['max_error']:.4f}% (基准)")
    print(f"     501点: {uniform_501['max_error']:.4f}%")
    print(f"     点数增加2.5x -> 精度提升{uniform_301['max_error']/uniform_501['max_error']:.2f}x")
    print()

    adaptive_configs = [r for r in results if r['use_adaptive'] and 'dx=' in r['name'] and '半径' not in r['name']]
    if adaptive_configs:
        print(f"   自适应网格 (按dx排序):")
        for r in sorted(adaptive_configs, key=lambda x: x['dx_min'], reverse=True):
            improvement = uniform_301['max_error'] / r['max_error']
            print(f"     dx~={r['dx_min']:.1f}m: {r['max_error']:.4f}% (提升{improvement:.2f}x, {r['n_points']}点, {r['solve_time']:.1f}s)")
    print()

    print("=" * 100)
    print()

    return results


if __name__ == "__main__":
    results = comprehensive_test()

    print(f"\n测试完成！共测试 {len(results)} 种配置。")
    print(f"结果已保存在内存中，可用于进一步分析。")
