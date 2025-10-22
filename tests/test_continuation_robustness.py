#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
测试延拓求解器的鲁棒性

测试不同初值（好初值、差初值、极端初值）下的性能

作者: Claude
日期: 2025-10-22
"""

import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import numpy as np
import time
from physics.steady_saint_venant import SteadySaintVenantSystem
from solvers.continuation_solver import ContinuationSolver
from solvers.newton_solver import NewtonSolver
from solvers.gate import SluiceGate
from utils.canal_utils import compute_steady_uniform_flow


def run_initial_condition_test(name, h_init_func, Q_init_func, system, Q_target):
    """
    测试特定初值

    Args:
        name: 初值名称
        h_init_func: h初值生成函数
        Q_init_func: Q初值生成函数
        system: 系统实例
        Q_target: 目标流量

    Returns:
        dict: 测试结果
    """
    print("=" * 100)
    print(f"测试初值: {name}")
    print("=" * 100)
    print()

    nx = system.nx
    h_init = h_init_func(nx)
    Q_init = Q_init_func(nx)

    print(f"初值范围:")
    print(f"  h: {h_init.min():.4f} - {h_init.max():.4f} m")
    print(f"  Q: {Q_init.min():.4f} - {Q_init.max():.4f} m³/s")
    print()

    U_init = system.pack_state(h_init, Q_init)

    # 初始残差
    system.U_prev = U_init.copy()
    F_init = system.compute_residual(U_init, 0.0)
    residual_init = np.linalg.norm(F_init)

    print(f"初始残差: {residual_init:.4e}")
    print()

    results = {}

    # 测试1: 纯Newton（可能失败）
    print("-" * 100)
    print("方法1: 纯Newton (pseudo_dt=0.1)")
    print("-" * 100)

    system_newton = SteadySaintVenantSystem(
        system.length, system.nx, system.B, system.S0, system.n,
        structures=system.structures,
        pseudo_dt=0.1
    )
    system_newton.set_boundary_conditions(
        Q_upstream=system.Q_upstream,
        h_upstream=system.h_upstream,
        h_downstream=system.h_downstream
    )
    system_newton.U_prev = U_init.copy()

    newton = NewtonSolver(max_iter=30, tol_residual=1e-4, verbose=False)

    start = time.time()
    try:
        U_newton, info_newton = newton.solve(
            U_init=U_init,
            residual_func=lambda U: system_newton.compute_residual(U, 0.0),
            jacobian_func=lambda U: system_newton.compute_jacobian(U, 0.0)
        )
        time_newton = time.time() - start

        h_newton, Q_newton = system_newton.unpack_state(U_newton)
        Q_error_newton = abs(np.mean(Q_newton) - Q_target) / Q_target * 100

        results['newton'] = {
            'converged': info_newton['converged'],
            'iterations': info_newton['iterations'],
            'time': time_newton,
            'Q_error': Q_error_newton
        }

        print(f"  收敛: {'✅' if info_newton['converged'] else '❌'}")
        print(f"  迭代次数: {info_newton['iterations']}")
        print(f"  用时: {time_newton:.4f}s")
        print(f"  流量误差: {Q_error_newton:.4f}%")

    except Exception as e:
        results['newton'] = {
            'converged': False,
            'error': str(e)
        }
        print(f"  ❌ 失败: {e}")

    print()

    # 测试2: 延拓求解器
    print("-" * 100)
    print("方法2: 延拓求解器 (pseudo_dt: 10.0 → 1.0 → 0.1)")
    print("-" * 100)

    system_cont = SteadySaintVenantSystem(
        system.length, system.nx, system.B, system.S0, system.n,
        structures=system.structures,
        pseudo_dt=0.1
    )
    system_cont.set_boundary_conditions(
        Q_upstream=system.Q_upstream,
        h_upstream=system.h_upstream,
        h_downstream=system.h_downstream
    )
    system_cont.U_prev = U_init.copy()

    solver_cont = ContinuationSolver(
        pseudo_dt_sequence=[10.0, 1.0, 0.1],
        newton_max_iter=30,
        newton_tol=1e-4,
        verbose=False
    )

    start = time.time()
    try:
        U_cont, info_cont = solver_cont.solve(system_cont, U_init, t=0.0)
        time_cont = time.time() - start

        h_cont, Q_cont = system_cont.unpack_state(U_cont)
        Q_error_cont = abs(np.mean(Q_cont) - Q_target) / Q_target * 100

        results['continuation'] = {
            'converged': info_cont['converged'],
            'iterations': info_cont['total_iterations'],
            'time': time_cont,
            'Q_error': Q_error_cont,
            'stages': info_cont['num_stages']
        }

        print(f"  收敛: {'✅' if info_cont['converged'] else '❌'}")
        print(f"  完成阶段: {info_cont['num_stages']}/3")
        print(f"  总迭代次数: {info_cont['total_iterations']}")
        print(f"  用时: {time_cont:.4f}s")
        print(f"  流量误差: {Q_error_cont:.4f}%")

    except Exception as e:
        results['continuation'] = {
            'converged': False,
            'error': str(e)
        }
        print(f"  ❌ 失败: {e}")

    print()
    print("-" * 100)

    return results


def main():
    """主测试程序"""

    print("=" * 100)
    print("延拓求解器鲁棒性测试 - 三闸门场景")
    print("=" * 100)
    print()

    # 三闸门场景
    length = 10000.0
    nx = 301
    B = 10.0
    S0 = 0.0005
    n = 0.025
    Q_target = 10.0

    gate1 = SluiceGate(position=2500.0, width=B, opening=4.5, Cd=0.6)
    gate2 = SluiceGate(position=5000.0, width=B, opening=4.0, Cd=0.6)
    gate3 = SluiceGate(position=7500.0, width=B, opening=5.0, Cd=0.6)

    h_uniform = compute_steady_uniform_flow(Q_target, B, S0, n)

    print(f"场景参数:")
    print(f"  网格: {nx}点, {length}m")
    print(f"  流量: {Q_target} m³/s")
    print(f"  均匀流水深: {h_uniform:.4f} m")
    print()

    # 创建系统（用于测试）
    system = SteadySaintVenantSystem(
        length, nx, B, S0, n,
        structures=[
            (gate1.position, gate1),
            (gate2.position, gate2),
            (gate3.position, gate3)
        ],
        pseudo_dt=0.1
    )
    system.set_boundary_conditions(
        Q_upstream=Q_target,
        h_upstream=h_uniform,
        h_downstream=h_uniform
    )

    all_results = {}

    # 测试1: 好初值（均匀流）
    all_results['uniform'] = run_initial_condition_test(
        name="均匀流（好初值）",
        h_init_func=lambda nx: np.ones(nx) * h_uniform,
        Q_init_func=lambda nx: np.ones(nx) * Q_target,
        system=system,
        Q_target=Q_target
    )

    # 测试2: 中等初值（线性插值）
    all_results['linear'] = run_initial_condition_test(
        name="线性插值（中等初值）",
        h_init_func=lambda nx: np.linspace(h_uniform * 0.8, h_uniform * 1.2, nx),
        Q_init_func=lambda nx: np.linspace(Q_target * 0.8, Q_target * 1.2, nx),
        system=system,
        Q_target=Q_target
    )

    # 测试3: 差初值（零初值）
    all_results['zero'] = run_initial_condition_test(
        name="零初值（差初值）",
        h_init_func=lambda nx: np.ones(nx) * 0.1,
        Q_init_func=lambda nx: np.ones(nx) * 0.1,
        system=system,
        Q_target=Q_target
    )

    # 测试4: 极端初值（大值）
    all_results['large'] = run_initial_condition_test(
        name="大值初值（极端初值）",
        h_init_func=lambda nx: np.ones(nx) * h_uniform * 5.0,
        Q_init_func=lambda nx: np.ones(nx) * Q_target * 5.0,
        system=system,
        Q_target=Q_target
    )

    # 汇总结果
    print("=" * 100)
    print("汇总结果")
    print("=" * 100)
    print()

    print(f"{'初值类型':<20} {'方法':<15} {'收敛':<8} {'迭代':<10} {'时间(s)':<12} {'流量误差(%)':<15}")
    print("-" * 100)

    for init_name, results in all_results.items():
        # 纯Newton
        if 'newton' in results and 'converged' in results['newton']:
            r = results['newton']
            conv_status = '✅' if r['converged'] else '❌'
            iter_str = str(r['iterations']) if r['converged'] else 'N/A'
            time_str = f"{r['time']:.4f}" if r['converged'] else 'N/A'
            error_str = f"{r['Q_error']:.4f}" if r['converged'] and 'Q_error' in r else 'N/A'

            print(f"{init_name:<20} {'纯Newton':<15} {conv_status:<8} {iter_str:<10} {time_str:<12} {error_str:<15}")

        # 延拓
        if 'continuation' in results and 'converged' in results['continuation']:
            r = results['continuation']
            conv_status = '✅' if r['converged'] else '❌'
            iter_str = str(r['iterations']) if r['converged'] else 'N/A'
            time_str = f"{r['time']:.4f}" if r['converged'] else 'N/A'
            error_str = f"{r['Q_error']:.4f}" if r['converged'] and 'Q_error' in r else 'N/A'

            print(f"{init_name:<20} {'延拓':<15} {conv_status:<8} {iter_str:<10} {time_str:<12} {error_str:<15}")

        print()

    # 结论
    print("=" * 100)
    print("结论")
    print("=" * 100)
    print()

    newton_success = sum(1 for r in all_results.values() if r.get('newton', {}).get('converged', False))
    cont_success = sum(1 for r in all_results.values() if r.get('continuation', {}).get('converged', False))

    print(f"纯Newton成功率: {newton_success}/{len(all_results)} ({newton_success/len(all_results)*100:.0f}%)")
    print(f"延拓求解器成功率: {cont_success}/{len(all_results)} ({cont_success/len(all_results)*100:.0f}%)")
    print()

    if cont_success > newton_success:
        print("✅ 延拓求解器比纯Newton更鲁棒")
    elif cont_success == newton_success and cont_success == len(all_results):
        print("✅ 两种方法在所有测试中都成功，但延拓求解器提供更好的鲁棒性保证")
    else:
        print("⚠️ 需要进一步优化")

    print()


if __name__ == '__main__':
    main()
