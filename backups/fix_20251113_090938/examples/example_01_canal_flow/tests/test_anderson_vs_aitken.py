#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Anderson加速 vs Aitken加速性能对比

对比三种方法：
1. Aitken加速（基准）
2. Anderson加速（默认参数：m=5, beta=1.0）
3. Anderson加速（保守参数：m=3, beta=0.7）

作者: Claude
日期: 2025-10-22
"""

import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

import numpy as np
import time
# DEPRECATED: Use HydrostaticCanalSolver instead
# from solvers.canal_solver import CanalSolver
from solvers.canal_solver_anderson import CanalSolverAnderson
from solvers.gate import SluiceGate, BroadCrestedWeir, Orifice


def compare_acceleration_methods():
    """对比Anderson加速和Aitken加速"""

    print("=" * 100)
    print("Anderson加速 vs Aitken加速性能对比")
    print("=" * 100)
    print()

    # 渠道参数
    length = 10000.0
    nx = 301
    B = 10.0
    S0 = 0.0005
    n = 0.025

    # 测试场景
    scenarios = []

    # 场景1：单闸门
    print("准备测试场景...")
    gate1 = SluiceGate(B=B, e=5.0, Cd=0.6)
    scenarios.append({
        'name': '单闸门',
        'structures': [{'x': 5000.0, 'structure': gate1}],
        'Q_target': 10.0,
        'max_iter': 10000
    })

    # 场景2：三闸门串联
    gate1 = SluiceGate(B=B, e=4.5, Cd=0.6)
    gate2 = SluiceGate(B=B, e=4.0, Cd=0.6)
    gate3 = SluiceGate(B=B, e=5.0, Cd=0.6)
    scenarios.append({
        'name': '三闸门串联',
        'structures': [
            {'x': 2500.0, 'structure': gate1},
            {'x': 5000.0, 'structure': gate2},
            {'x': 7500.0, 'structure': gate3}
        ],
        'Q_target': 10.0,
        'max_iter': 20000
    })

    # 场景3：混合结构
    gate = SluiceGate(B=B, e=3.5, Cd=0.6)
    weir = BroadCrestedWeir(B=B, P=0.5, Cd=0.5)
    orifice = Orifice(B_orifice=4.0, H_orifice=2.0, z_bottom=0.2, Cd=0.6)
    scenarios.append({
        'name': '混合结构',
        'structures': [
            {'x': 2500.0, 'structure': gate},
            {'x': 5000.0, 'structure': weir},
            {'x': 7500.0, 'structure': orifice}
        ],
        'Q_target': 10.0,
        'max_iter': 10000
    })

    # 汇总结果
    all_results = []

    # 对每个场景进行测试
    for scenario in scenarios:
        print("\n" + "=" * 100)
        print(f"场景: {scenario['name']}")
        print("=" * 100)
        print()

        results = []

        # 方法1：Aitken加速（基准）
        print("方法1: Aitken加速（基准）")
        print("-" * 100)

        solver = CanalSolver(
            length=length,
            nx=nx,
            B=B,
            S0=S0,
            n=n
        )

        for struct_info in scenario['structures']:
            solver.add_structure(struct_info['x'], struct_info['structure'])

        # 初始化为恒定均匀流
        h_init, Q_init = solver.compute_uniform_flow(scenario['Q_target'])
        solver.set_initial_conditions(h_init, Q_init)

        start_time = time.time()
        success = solver.solve_steady_state(
            Q_target=scenario['Q_target'],
            max_iter=scenario['max_iter'],
            tol=0.01,
            adaptive_relax=True,
            verbose=False
        )
        elapsed = time.time() - start_time

        Q_avg = np.mean([solver.Q[idx] for idx in solver.structure_indices])
        error = abs(Q_avg - scenario['Q_target']) / scenario['Q_target'] * 100

        result_aitken = {
            'scenario': scenario['name'],
            'method': 'Aitken',
            'converged': success,
            'iterations': solver.steady_iteration_count,
            'error': error,
            'time': elapsed
        }
        results.append(result_aitken)

        print(f"  收敛: {'' if success else ''}")
        print(f"  迭代次数: {solver.steady_iteration_count}")
        print(f"  最终误差: {error:.4f}%")
        print(f"  计算时间: {elapsed:.4f}s")
        print()

        # 方法2：Anderson加速（默认参数: m=5, beta=1.0）
        print("方法2: Anderson加速（m=5, beta=1.0）")
        print("-" * 100)

        solver_anderson1 = CanalSolverAnderson(
            length=length,
            nx=nx,
            B=B,
            S0=S0,
            n=n,
            anderson_m=5,
            anderson_beta=1.0,
            anderson_reg=1e-8
        )

        for struct_info in scenario['structures']:
            solver_anderson1.add_structure(struct_info['x'], struct_info['structure'])

        # 初始化为恒定均匀流
        h_init, Q_init = solver_anderson1.compute_uniform_flow(scenario['Q_target'])
        solver_anderson1.set_initial_conditions(h_init, Q_init)

        start_time = time.time()
        success = solver_anderson1.solve_steady_state_anderson(
            Q_target=scenario['Q_target'],
            max_iter=scenario['max_iter'],
            tol=0.01,
            verbose=False,
            internal_bc_max_iter=20
        )
        elapsed = time.time() - start_time

        Q_avg = np.mean([solver_anderson1.Q[idx] for idx in solver_anderson1.structure_indices])
        error = abs(Q_avg - scenario['Q_target']) / scenario['Q_target'] * 100

        anderson_stats = solver_anderson1.get_anderson_stats()

        result_anderson1 = {
            'scenario': scenario['name'],
            'method': 'Anderson(m=5,β=1.0)',
            'converged': success,
            'iterations': solver_anderson1.steady_iteration_count,
            'error': error,
            'time': elapsed,
            'anderson_restarts': anderson_stats['restart_count']
        }
        results.append(result_anderson1)

        print(f"  收敛: {'' if success else ''}")
        print(f"  迭代次数: {solver_anderson1.steady_iteration_count}")
        print(f"  最终误差: {error:.4f}%")
        print(f"  计算时间: {elapsed:.4f}s")
        print(f"  Anderson重启次数: {anderson_stats['restart_count']}")
        print()

        # 方法3：Anderson加速（保守参数: m=3, beta=0.7）
        print("方法3: Anderson加速（m=3, beta=0.7，保守）")
        print("-" * 100)

        solver_anderson2 = CanalSolverAnderson(
            length=length,
            nx=nx,
            B=B,
            S0=S0,
            n=n,
            anderson_m=3,
            anderson_beta=0.7,
            anderson_reg=1e-8
        )

        for struct_info in scenario['structures']:
            solver_anderson2.add_structure(struct_info['x'], struct_info['structure'])

        # 初始化为恒定均匀流
        h_init, Q_init = solver_anderson2.compute_uniform_flow(scenario['Q_target'])
        solver_anderson2.set_initial_conditions(h_init, Q_init)

        start_time = time.time()
        success = solver_anderson2.solve_steady_state_anderson(
            Q_target=scenario['Q_target'],
            max_iter=scenario['max_iter'],
            tol=0.01,
            verbose=False,
            internal_bc_max_iter=20
        )
        elapsed = time.time() - start_time

        Q_avg = np.mean([solver_anderson2.Q[idx] for idx in solver_anderson2.structure_indices])
        error = abs(Q_avg - scenario['Q_target']) / scenario['Q_target'] * 100

        anderson_stats = solver_anderson2.get_anderson_stats()

        result_anderson2 = {
            'scenario': scenario['name'],
            'method': 'Anderson(m=3,β=0.7)',
            'converged': success,
            'iterations': solver_anderson2.steady_iteration_count,
            'error': error,
            'time': elapsed,
            'anderson_restarts': anderson_stats['restart_count']
        }
        results.append(result_anderson2)

        print(f"  收敛: {'' if success else ''}")
        print(f"  迭代次数: {solver_anderson2.steady_iteration_count}")
        print(f"  最终误差: {error:.4f}%")
        print(f"  计算时间: {elapsed:.4f}s")
        print(f"  Anderson重启次数: {anderson_stats['restart_count']}")
        print()

        # 性能对比
        print("性能对比")
        print("-" * 100)
        print(f"{'方法':<25} {'收敛':<8} {'迭代次数':<12} {'误差':<12} {'时间(s)':<10} {'相对Aitken':<12}")
        print("-" * 100)

        for r in results:
            converged_str = '' if r['converged'] else ''
            rel_perf = ""
            if r['method'] != 'Aitken' and result_aitken['time'] > 0:
                speedup = (result_aitken['time'] - r['time']) / result_aitken['time'] * 100
                if speedup > 0:
                    rel_perf = f"快{speedup:.1f}%"
                else:
                    rel_perf = f"慢{-speedup:.1f}%"

            print(f"{r['method']:<25} {converged_str:<8} {r['iterations']:<12} {r['error']:<11.4f}% {r['time']:<10.4f} {rel_perf:<12}")

        print()

        all_results.extend(results)

    # 总体汇总
    print("\n" + "=" * 100)
    print("总体汇总")
    print("=" * 100)
    print()
    print(f"{'场景':<15} {'方法':<25} {'收敛':<8} {'迭代次数':<12} {'误差(%)':<12} {'时间(s)':<10}")
    print("-" * 100)

    for r in all_results:
        converged_str = '' if r['converged'] else ''
        print(f"{r['scenario']:<15} {r['method']:<25} {converged_str:<8} {r['iterations']:<12} {r['error']:<12.4f} {r['time']:<10.4f}")

    print()

    # 统计分析
    print("=" * 100)
    print("统计分析")
    print("=" * 100)
    print()

    # 按方法分组
    methods = ['Aitken', 'Anderson(m=5,β=1.0)', 'Anderson(m=3,β=0.7)']
    for method in methods:
        method_results = [r for r in all_results if r['method'] == method]
        if method_results:
            avg_time = np.mean([r['time'] for r in method_results])
            avg_iter = np.mean([r['iterations'] for r in method_results])
            success_rate = sum([1 for r in method_results if r['converged']]) / len(method_results) * 100

            print(f"{method}:")
            print(f"  平均时间: {avg_time:.4f}s")
            print(f"  平均迭代: {avg_iter:.1f}")
            print(f"  成功率: {success_rate:.1f}%")
            print()

    # 结论
    print("=" * 100)
    print("结论")
    print("=" * 100)
    print()

    aitken_results = [r for r in all_results if r['method'] == 'Aitken']
    anderson1_results = [r for r in all_results if r['method'] == 'Anderson(m=5,β=1.0)']
    anderson2_results = [r for r in all_results if r['method'] == 'Anderson(m=3,β=0.7)']

    if aitken_results and anderson1_results:
        aitken_avg_time = np.mean([r['time'] for r in aitken_results])
        anderson1_avg_time = np.mean([r['time'] for r in anderson1_results])
        speedup1 = (aitken_avg_time - anderson1_avg_time) / aitken_avg_time * 100

        if speedup1 > 0:
            print(f" Anderson加速（m=5, beta=1.0）平均快 {speedup1:.1f}%")
        else:
            print(f" Anderson加速（m=5, beta=1.0）平均慢 {-speedup1:.1f}%")

    if aitken_results and anderson2_results:
        aitken_avg_time = np.mean([r['time'] for r in aitken_results])
        anderson2_avg_time = np.mean([r['time'] for r in anderson2_results])
        speedup2 = (aitken_avg_time - anderson2_avg_time) / aitken_avg_time * 100

        if speedup2 > 0:
            print(f" Anderson加速（m=3, beta=0.7）平均快 {speedup2:.1f}%")
        else:
            print(f" Anderson加速（m=3, beta=0.7）平均慢 {-speedup2:.1f}%")

    print()
    print("建议：")
    if anderson1_results and all(r['converged'] for r in anderson1_results):
        print("- Anderson加速（m=5, beta=1.0）在所有场景下均收敛，推荐使用")
    if anderson2_results and all(r['converged'] for r in anderson2_results):
        print("- Anderson加速（m=3, beta=0.7）更保守，适合数值不稳定的问题")

    print()


if __name__ == '__main__':
    compare_acceleration_methods()
