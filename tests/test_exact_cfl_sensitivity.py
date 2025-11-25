#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
测试不同CFL数对精确求解器的影响
Test CFL number sensitivity for Exact Riemann solver
"""

import numpy as np
import warnings
warnings.filterwarnings("ignore")
import sys
import os
sys.path.insert(0, os.path.abspath('.'))

try:
    from solvers.godunov_fvm_solver import GodunvFVMSolver
except ImportError as e:
    print(f"Import error: {e}")
    print("Make sure project root is in sys.path")
    sys.exit(1)


def test_cfl_number(cfl, max_steps=20, max_time=1.0):
    """测试特定CFL数"""
    width = 10.0
    length = 100.0
    n_cells = 100
    dx = length / n_cells

    h_init = np.zeros(n_cells)
    h_init[:25] = 2.0
    h_init[25:] = 1.0
    Q_init = np.zeros(n_cells)

    bc_left = {'type': 'h', 'value': 2.0}
    bc_right = {'type': 'h', 'value': 1.0}

    solver = GodunvFVMSolver(
        width=width,
        length=length,
        n_cells=n_cells,
        manning_n=0.0,
        slope=0.0,
        cfl=cfl,
        order=1,
        riemann_solver='exact',
        use_numba=False
    )

    solver.initialize(h_init.copy(), Q_init.copy(), bc_left, bc_right)
    mass_0 = np.sum(solver.h * solver.B * dx)

    results = {
        'cfl': cfl,
        'steps': [],
        'time': [],
        'dt': [],
        'mass_error_pct': [],
        'h_max': [],
        'crashed': False
    }

    step = 0
    while solver.t < max_time and step < max_steps:
        step += 1
        try:
            dt_used = solver.dt if solver.step_count > 0 else solver.compute_dt()
            solver.step()

            mass = np.sum(solver.h * solver.B * dx)
            mass_error = abs(mass - mass_0) / mass_0 * 100

            results['steps'].append(step)
            results['time'].append(solver.t)
            results['dt'].append(dt_used)
            results['mass_error_pct'].append(mass_error)
            results['h_max'].append(np.max(solver.h))

            if np.any(np.isnan(solver.h)) or np.any(solver.h < 0) or mass_error > 100:
                results['crashed'] = True
                results['crash_step'] = step
                break

        except Exception as e:
            results['crashed'] = True
            results['crash_step'] = step
            results['error'] = str(e)
            break

    return results

def main():
    print("=" * 80)
    print("精确求解器CFL数敏感性测试")
    print("=" * 80)

    cfl_values = [0.1, 0.2, 0.3, 0.4, 0.5]

    all_results = []

    for cfl in cfl_values:
        print(f"\n{'='*80}")
        print(f"CFL = {cfl}")
        print("=" * 80)

        results = test_cfl_number(cfl, max_steps=20, max_time=1.0)
        all_results.append(results)

        print(f"\n初始质量: 1500.00 m^3")
        print(f"\n{'步骤':<6} {'时间(s)':<10} {'dt(s)':<10} {'误差(%)':<12} {'h_max(m)':<10} {'状态':<10}")
        print("-" * 80)

        for i in range(len(results['steps'])):
            step = results['steps'][i]
            time = results['time'][i]
            dt = results['dt'][i]
            error = results['mass_error_pct'][i]
            h_max = results['h_max'][i]

            status = "" if error < 1.0 else ("" if error < 10 else "")
            print(f"{step:<6} {time:<10.3f} {dt:<10.6f} {error:<12.6f} {h_max:<10.3f} {status:<10}")

        if results['crashed']:
            print(f"\n 崩溃于步骤 {results['crash_step']}")
        else:
            if len(results['steps']) > 0:
                final_error = results['mass_error_pct'][-1]
                print(f"\n 达到t=1.0s，最终误差: {final_error:.4f}%")
            else:
                print(f"\n 立即崩溃")

    # 总结
    print("\n" + "=" * 80)
    print("总结对比")
    print("=" * 80)
    print(f"\n{'CFL':<10} {'达到步数':<10} {'达到时间(s)':<15} {'最终误差(%)':<15} {'状态':<15}")
    print("-" * 80)

    for i, cfl in enumerate(cfl_values):
        results = all_results[i]
        n_steps = len(results['steps'])

        if n_steps > 0:
            final_time = results['time'][-1]
            final_error = results['mass_error_pct'][-1]

            if results['crashed']:
                status = f" 崩溃@{results.get('crash_step', '?')}"
            elif final_error < 1.0:
                status = " 优秀"
            elif final_error < 10:
                status = "  可接受"
            else:
                status = " 失败"
        else:
            final_time = 0.0
            final_error = float('nan')
            status = " 立即崩溃"

        print(f"{cfl:<10.2f} {n_steps:<10} {final_time:<15.3f} {final_error:<15.6f} {status:<15}")

    # 推荐
    print("\n" + "=" * 80)
    print("分析")
    print("=" * 80)

    # 检查CFL是否有影响
    errors_at_step_1 = []
    for results in all_results:
        if len(results['mass_error_pct']) > 0:
            errors_at_step_1.append(results['mass_error_pct'][0])

    if len(errors_at_step_1) > 1:
        if max(errors_at_step_1) - min(errors_at_step_1) < 0.001:
            print("\n  所有CFL数产生相同结果")
            print("   -> CFL数不是问题的根源")
            print("   -> 问题可能在通量计算或数值方法本身")
        else:
            print("\n CFL数影响显著")
            # 找到最优CFL
            best_idx = np.argmin(errors_at_step_1)
            print(f"   -> 推荐CFL = {cfl_values[best_idx]}")

if __name__ == "__main__":
    main()

    print("\n" + "=" * 80)
    print("测试完成")
    print("=" * 80)
