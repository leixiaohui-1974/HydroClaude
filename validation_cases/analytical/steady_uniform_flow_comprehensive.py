#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
恒定均匀流验证 (Steady Uniform Flow)

理论基础：
Manning公式: Q = (1/n) * A * R^(2/3) * sqrt(S0)

对于恒定均匀流：
- 水深处处相等（等于正常水深yn）
- 流量处处相等
- 水面坡度 = 能坡 = 底坡

验证案例：
1. 矩形断面
2. 梯形断面

验收标准：
- 计算流量与理论流量误差 < 1%
- 水深沿程变化 < 0.01m
- 质量守恒误差 < 0.1%

作者：HydroClaude Team
日期：2025-10-28
"""

import numpy as np
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from solvers.godunov_fvm_solver import GodunvFVMSolver


def compute_flow_manning(A: float, R: float, S0: float, n: float) -> float:
    """
    Manning公式计算流量

    Q = (1/n) * A * R^(2/3) * sqrt(S0)

    Args:
        A: 过水面积 (m²)
        R: 水力半径 (m)
        S0: 底坡
        n: 曼宁系数

    Returns:
        流量 Q (m³/s)
    """
    Q = (1.0 / n) * A * (R ** (2.0/3.0)) * np.sqrt(S0)
    return Q


def rectangular_channel_test():
    """矩形断面恒定均匀流验证"""

    print("\n" + "=" * 80)
    print("验证案例1：矩形断面恒定均匀流")
    print("=" * 80)

    # 参数
    b = 10.0      # 渠宽 (m)
    h = 2.0       # 水深 (m)
    L = 1000.0    # 渠长 (m)
    S0 = 0.001    # 底坡
    n = 0.025     # 曼宁系数
    g = 9.81

    # 理论计算
    A = b * h
    P = b + 2 * h
    R = A / P
    Q_theory = compute_flow_manning(A, R, S0, n)

    print(f"\n参数设置:")
    print(f"  渠宽 b = {b} m")
    print(f"  水深 h = {h} m")
    print(f"  底坡 S0 = {S0}")
    print(f"  曼宁系数 n = {n}")
    print(f"  渠长 L = {L} m")

    print(f"\n理论计算:")
    print(f"  面积 A = {A:.3f} m²")
    print(f"  湿周 P = {P:.3f} m")
    print(f"  水力半径 R = {R:.3f} m")
    print(f"  理论流量 Q = {Q_theory:.3f} m³/s")

    # 数值求解
    print(f"\nHydroClaude数值求解:")

    n_cells = 100
    solver = GodunvFVMSolver(
        width=b,
        length=L,
        n_cells=n_cells,
        manning_n=n,
        slope=S0,
        g=g,
        cfl=0.5
    )

    # 初始条件：均匀流
    solver.h = h * np.ones(n_cells)
    solver.Q = Q_theory * np.ones(n_cells)

    # 边界条件：上游固定流量，下游固定水深
    solver.bc_left = {'type': 'Q', 'value': Q_theory}
    solver.bc_right = {'type': 'h', 'value': h}

    # 记录初始质量
    solver.initial_mass = np.sum(solver.h * solver.dx * b)

    # 时间推进（应该保持稳态）
    print("  时间推进...")
    n_steps = 1000
    for i in range(n_steps):
        solver.step()

    print(f"  完成 {n_steps} 步")

    # 结果分析
    h_mean = np.mean(solver.h)
    h_std = np.std(solver.h)
    h_min = np.min(solver.h)
    h_max = np.max(solver.h)

    Q_mean = np.mean(solver.Q)
    Q_numerical = Q_mean

    error_Q = abs(Q_numerical - Q_theory) / Q_theory * 100
    error_h = h_std

    # 质量守恒
    final_mass = np.sum(solver.h * solver.dx * b)
    mass_error = abs(final_mass - solver.initial_mass) / solver.initial_mass * 100

    print(f"\n结果分析:")
    print(f"  水深: mean={h_mean:.4f}m, std={h_std:.4f}m, range=[{h_min:.4f}, {h_max:.4f}]")
    print(f"  数值流量 Q = {Q_numerical:.3f} m³/s")
    print(f"  流量误差 = {error_Q:.3f}%")
    print(f"  质量守恒误差 = {mass_error:.4f}%")

    # 判断
    passed = True
    tolerance_Q = 1.0  # %
    tolerance_h = 0.01  # m
    tolerance_mass = 0.1  # %

    if error_Q < tolerance_Q:
        print(f"✓ 流量误差测试通过: {error_Q:.3f}% < {tolerance_Q}%")
    else:
        print(f"✗ 流量误差测试失败: {error_Q:.3f}% >= {tolerance_Q}%")
        passed = False

    if error_h < tolerance_h:
        print(f"✓ 水深均匀性测试通过: std={error_h:.4f}m < {tolerance_h}m")
    else:
        print(f"✗ 水深均匀性测试失败: std={error_h:.4f}m >= {tolerance_h}m")
        passed = False

    if mass_error < tolerance_mass:
        print(f"✓ 质量守恒测试通过: {mass_error:.4f}% < {tolerance_mass}%")
    else:
        print(f"✗ 质量守恒测试失败: {mass_error:.4f}% >= {tolerance_mass}%")
        passed = False

    return {
        'test_name': 'rectangular_steady_uniform',
        'passed': passed,
        'error_Q': error_Q,
        'error_h': error_h,
        'mass_error': mass_error
    }


def trapezoidal_channel_test():
    """梯形断面恒定均匀流验证"""

    print("\n" + "=" * 80)
    print("验证案例2：梯形断面恒定均匀流")
    print("=" * 80)

    # 参数
    b = 8.0       # 底宽 (m)
    m = 1.5       # 边坡系数
    h = 2.5       # 水深 (m)
    L = 1000.0    # 渠长 (m)
    S0 = 0.0005   # 底坡
    n = 0.025     # 曼宁系数
    g = 9.81

    # 理论计算
    A = (b + m * h) * h
    P = b + 2 * h * np.sqrt(1 + m**2)
    R = A / P
    Q_theory = compute_flow_manning(A, R, S0, n)

    print(f"\n参数设置:")
    print(f"  底宽 b = {b} m")
    print(f"  边坡系数 m = {m}")
    print(f"  水深 h = {h} m")
    print(f"  底坡 S0 = {S0}")
    print(f"  曼宁系数 n = {n}")
    print(f"  渠长 L = {L} m")

    print(f"\n理论计算:")
    print(f"  面积 A = {A:.3f} m²")
    print(f"  湿周 P = {P:.3f} m")
    print(f"  水力半径 R = {R:.3f} m")
    print(f"  理论流量 Q = {Q_theory:.3f} m³/s")

    # 数值求解
    # 注意：当前GodunvFVMSolver只支持矩形断面
    # 这里用等效宽度近似
    B_top = b + 2 * m * h  # 水面宽度
    B_eq = A / h  # 等效宽度

    print(f"\n注：使用等效矩形断面近似 (B_eq = A/h = {B_eq:.3f}m)")

    n_cells = 100
    solver = GodunvFVMSolver(
        width=B_eq,
        length=L,
        n_cells=n_cells,
        manning_n=n,
        slope=S0,
        g=g,
        cfl=0.5
    )

    # 初始条件：均匀流
    solver.h = h * np.ones(n_cells)
    solver.Q = Q_theory * np.ones(n_cells)

    # 边界条件
    solver.bc_left = {'type': 'Q', 'value': Q_theory}
    solver.bc_right = {'type': 'h', 'value': h}

    solver.initial_mass = np.sum(solver.h * solver.dx * B_eq)

    # 时间推进
    print(f"\nHydroClaude数值求解:")
    print("  时间推进...")
    n_steps = 1000
    for i in range(n_steps):
        solver.step()

    print(f"  完成 {n_steps} 步")

    # 结果分析
    h_mean = np.mean(solver.h)
    h_std = np.std(solver.h)

    Q_numerical = np.mean(solver.Q)
    error_Q = abs(Q_numerical - Q_theory) / Q_theory * 100

    final_mass = np.sum(solver.h * solver.dx * B_eq)
    mass_error = abs(final_mass - solver.initial_mass) / solver.initial_mass * 100

    print(f"\n结果分析:")
    print(f"  水深: mean={h_mean:.4f}m, std={h_std:.4f}m")
    print(f"  数值流量 Q = {Q_numerical:.3f} m³/s")
    print(f"  流量误差 = {error_Q:.3f}%")
    print(f"  质量守恒误差 = {mass_error:.4f}%")

    # 判断
    passed = True
    tolerance_Q = 2.0  # % (放宽，因为使用等效断面)
    tolerance_h = 0.01
    tolerance_mass = 0.1

    if error_Q < tolerance_Q:
        print(f"✓ 流量误差测试通过: {error_Q:.3f}% < {tolerance_Q}%")
    else:
        print(f"✗ 流量误差测试失败: {error_Q:.3f}% >= {tolerance_Q}%")
        passed = False

    if h_std < tolerance_h:
        print(f"✓ 水深均匀性测试通过: std={h_std:.4f}m < {tolerance_h}m")
    else:
        print(f"✗ 水深均匀性测试失败: std={h_std:.4f}m >= {tolerance_h}m")
        passed = False

    if mass_error < tolerance_mass:
        print(f"✓ 质量守恒测试通过: {mass_error:.4f}% < {tolerance_mass}%")
    else:
        print(f"✗ 质量守恒测试失败: {mass_error:.4f}% >= {tolerance_mass}%")
        passed = False

    return {
        'test_name': 'trapezoidal_steady_uniform',
        'passed': passed,
        'error_Q': error_Q,
        'error_h': h_std,
        'mass_error': mass_error
    }


def main():
    """运行所有验证案例"""

    print("=" * 80)
    print("恒定均匀流验证测试套件")
    print("=" * 80)

    results = []

    # 案例1：矩形断面
    result1 = rectangular_channel_test()
    results.append(result1)

    # 案例2：梯形断面
    result2 = trapezoidal_channel_test()
    results.append(result2)

    # 总结
    print("\n" + "=" * 80)
    print("验证测试总结")
    print("=" * 80)

    all_passed = all(r['passed'] for r in results)

    for result in results:
        status = "✓ 通过" if result['passed'] else "✗ 失败"
        print(f"{result['test_name']:40s}: {status}")

    print("=" * 80)

    if all_passed:
        print("🎉 所有恒定均匀流验证测试通过!")
    else:
        print("❌ 部分验证测试失败!")

    print("=" * 80 + "\n")

    return results, all_passed


if __name__ == '__main__':
    results, all_passed = main()

    import sys
    sys.exit(0 if all_passed else 1)
