#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
测试不同边界条件策略对精确求解器的影响
Test different boundary condition strategies for Exact Riemann solver

目标：
1. 对比不同relaxation_factor值
2. 评估质量守恒和数值稳定性
3. 找到最优边界条件策略
"""

import numpy as np
import sys
import os
sys.path.insert(0, os.path.abspath('.'))

try:
    from solvers.godunov_fvm_solver import GodunvFVMSolver
except ImportError as e:
    print(f"Import error: {e}")
    print("Make sure project root is in sys.path")
    sys.exit(1)


def test_boundary_relaxation(relaxation_factor, max_steps=10):
    """
    测试特定relaxation_factor下的精确求解器

    Args:
        relaxation_factor: 边界条件松弛因子 (0-1)
        max_steps: 最大步数

    Returns:
        dict: 测试结果
    """
    # 简单溃坝设置
    width = 10.0
    length = 100.0
    n_cells = 100
    dx = length / n_cells

    # 初始条件
    h_init = np.zeros(n_cells)
    h_init[:25] = 2.0  # 左侧2m
    h_init[25:] = 1.0  # 右侧1m
    Q_init = np.zeros(n_cells)

    # 固定h边界
    bc_left = {'type': 'h', 'value': 2.0}
    bc_right = {'type': 'h', 'value': 1.0}

    # 创建求解器（暂时修改relaxation_factor）
    solver = GodunvFVMSolver(
        width=width,
        length=length,
        n_cells=n_cells,
        manning_n=0.0,
        slope=0.0,
        cfl=0.3,
        order=1,
        riemann_solver='exact',
        use_numba=False  # 关闭Numba便于调试
    )

    # 临时修改relaxation_factor（hack方式）
    original_apply_bc = solver._apply_bc

    def modified_apply_bc(h, Q):
        """修改的边界条件函数"""
        # 仅对supercritical边界强制
        if solver.bc_left['type'] == 'supercritical':
            h_bc_value = solver.bc_left['h']
            Q_bc_value = solver.bc_left['Q']
            h_bc, u_bc = solver.characteristic_bc.apply_supercritical_inlet(
                h_bc_value=h_bc_value, Q_bc_value=Q_bc_value, B=solver.B
            )
            h[0] = h_bc
            Q[0] = Q_bc_value

        if solver.bc_right['type'] == 'supercritical':
            h_bc, u_bc = solver.characteristic_bc.apply_supercritical_outlet(
                h_interior=h[-2] if len(h) > 1 else h[-1],
                u_interior=Q[-2]/(h[-2]*solver.B) if len(h) > 1 and h[-2] > solver.eps_dry else 0.0
            )
            h[-1] = h_bc
            Q[-1] = u_bc * h_bc * solver.B

        # 使用指定的relaxation_factor
        rf = relaxation_factor

        # 左边界relaxation
        if solver.bc_left['type'] == 'h':
            value = solver.bc_left['value']
            h_target = value if not callable(value) else value(solver.t)
            h[0] = h[0] + rf * (h_target - h[0])
        elif solver.bc_left['type'] == 'Q':
            value = solver.bc_left['value']
            Q_target = value if not callable(value) else value(solver.t)
            Q[0] = Q[0] + rf * (Q_target - Q[0])

        # 右边界relaxation
        if solver.bc_right['type'] == 'h':
            value = solver.bc_right['value']
            h_target = value if not callable(value) else value(solver.t)
            h[-1] = h[-1] + rf * (h_target - h[-1])
        elif solver.bc_right['type'] == 'Q':
            value = solver.bc_right['value']
            Q_target = value if not callable(value) else value(solver.t)
            Q[-1] = Q[-1] + rf * (Q_target - Q[-1])

        return h, Q

    # 替换边界条件函数
    solver._apply_bc = modified_apply_bc

    # 初始化
    solver.initialize(h_init.copy(), Q_init.copy(), bc_left, bc_right)

    # 初始质量
    mass_0 = np.sum(solver.h * solver.B * dx)

    # 逐步模拟
    results = {
        'relaxation_factor': relaxation_factor,
        'steps': [],
        'time': [],
        'mass': [],
        'mass_error_pct': [],
        'h_max': [],
        'h_min': [],
        'crashed': False,
        'crash_step': None
    }

    for step in range(1, max_steps + 1):
        try:
            solver.step()

            mass = np.sum(solver.h * solver.B * dx)
            mass_error_pct = abs(mass - mass_0) / mass_0 * 100

            results['steps'].append(step)
            results['time'].append(solver.t)
            results['mass'].append(mass)
            results['mass_error_pct'].append(mass_error_pct)
            results['h_max'].append(np.max(solver.h))
            results['h_min'].append(np.min(solver.h))

            # 检查是否崩溃
            if np.any(np.isnan(solver.h)) or np.any(solver.h < 0) or mass_error_pct > 100:
                results['crashed'] = True
                results['crash_step'] = step
                break

            # 检查是否严重不守恒
            if mass_error_pct > 50:
                results['crashed'] = True
                results['crash_step'] = step
                break

        except Exception as e:
            results['crashed'] = True
            results['crash_step'] = step
            results['error'] = str(e)
            break

    # 恢复原函数
    solver._apply_bc = original_apply_bc

    return results

def main():
    """主测试函数"""
    print("=" * 80)
    print("精确求解器边界条件策略对比测试")
    print("=" * 80)

    # 测试不同的relaxation_factor值
    test_cases = [
        ('完全自由 (不推荐)', 0.0),
        ('温和松弛 (当前)', 0.5),
        ('强松弛', 0.8),
        ('完全强制', 1.0),
    ]

    all_results = []

    for name, rf in test_cases:
        print(f"\n{'='*80}")
        print(f"测试: {name} (relaxation_factor={rf})")
        print("=" * 80)

        results = test_boundary_relaxation(rf, max_steps=10)
        all_results.append(results)

        # 打印结果
        print(f"\n初始质量: 1500.00 m^3")
        print(f"Relaxation Factor: {rf}")
        print(f"\n{'步骤':<6} {'时间(s)':<10} {'质量(m^3)':<15} {'误差(%)':<12} {'h_max(m)':<10} {'状态':<10}")
        print("-" * 80)

        for i, step in enumerate(results['steps']):
            time = results['time'][i]
            mass = results['mass'][i]
            error = results['mass_error_pct'][i]
            h_max = results['h_max'][i]

            status = "" if error < 1.0 else ("" if error < 10 else "")

            print(f"{step:<6} {time:<10.3f} {mass:<15.6f} {error:<12.6f} {h_max:<10.3f} {status:<10}")

        if results['crashed']:
            print(f"\n 模拟崩溃于步骤 {results['crash_step']}")
        else:
            final_error = results['mass_error_pct'][-1]
            if final_error < 1.0:
                print(f"\n 模拟稳定完成，最终误差: {final_error:.4f}%")
            elif final_error < 10:
                print(f"\n  模拟完成但质量误差较大: {final_error:.4f}%")
            else:
                print(f"\n 质量守恒失败: {final_error:.4f}%")

    # 总结对比
    print("\n" + "=" * 80)
    print("总结对比")
    print("=" * 80)
    print(f"\n{'策略':<20} {'RF':<6} {'最大步数':<10} {'最终误差(%)':<15} {'状态':<10}")
    print("-" * 80)

    for i, (name, rf) in enumerate(test_cases):
        results = all_results[i]
        max_steps = len(results['steps'])

        if max_steps > 0:
            final_error = results['mass_error_pct'][-1]

            if results['crashed']:
                status = f" 崩溃@{results['crash_step']}"
            elif final_error < 1.0:
                status = " 稳定"
            elif final_error < 10:
                status = "  可用"
            else:
                status = " 失败"
        else:
            final_error = float('nan')
            status = " 立即崩溃"

        print(f"{name:<20} {rf:<6.1f} {max_steps:<10} {final_error:<15.6f} {status:<10}")

    # 推荐
    print("\n" + "=" * 80)
    print("推荐方案")
    print("=" * 80)

    # 找到最稳定的配置
    best_rf = None
    best_steps = 0
    best_error = float('inf')

    for i, (name, rf) in enumerate(test_cases):
        results = all_results[i]
        if len(results['steps']) > 0 and not results['crashed']:
            if results['mass_error_pct'][-1] < best_error:
                best_error = results['mass_error_pct'][-1]
                best_rf = rf
                best_steps = len(results['steps'])

    if best_rf is not None:
        print(f"\n 最优配置: relaxation_factor = {best_rf}")
        print(f"   - 完成步数: {best_steps}")
        print(f"   - 最终误差: {best_error:.6f}%")

        if best_error < 1.0:
            print(f"   - 评估: 可用于生产 ")
        elif best_error < 10:
            print(f"   - 评估: 可用但需注意质量误差 ")
        else:
            print(f"   - 评估: 不推荐使用 ")
    else:
        print("\n 所有配置都失败")
        print("   精确求解器需要重新设计边界条件策略")

if __name__ == "__main__":
    main()

    print("\n" + "=" * 80)
    print("测试完成")
    print("=" * 80)
