#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Preissmann修正版求解器 - 完整测试套件

测试案例：
1. 静水测试（平坦河床，S0=0）
2. 均匀流测试（恒定坡度+恒定流量）
3. 水位阶跃传播

作者: HydroClaude Team
日期: 2025-10-30
"""

import numpy as np
import sys
import os

# 添加路径
sys.path.insert(0, os.path.dirname(__file__))

from preissmann_solver_corrected import PreissmannSolverCorrected


def test_1_still_water():
    """
    测试1: 静水（平坦河床，无坡度）

    物理条件：
    - S0 = 0（平坦河床）
    - 初始：h = 2.0m（均匀），Q = 0
    - 边界：固定水位2.0m

    预期结果：
    - 水深保持2.0m
    - 流量保持0
    - 质量完全守恒
    """
    print("\n" + "="*80)
    print("测试1: 静水（平坦河床）")
    print("="*80)

    solver = PreissmannSolverCorrected(verbose=False, tolerance=1e-6, max_iter=30)

    n_cells = 20
    length = 1000.0
    dx = length / n_cells
    width = 10.0
    manning_n = 0.025
    slope = 0.0  # ⚠️ 关键：平坦河床
    dt = 60.0

    h_init = np.ones(n_cells + 1) * 2.0
    Q_init = np.zeros(n_cells + 1)

    bc = {
        'upstream_level': 2.0,
        'downstream_level': 2.0
    }

    initial_mass = np.sum(h_init[:-1] * width * dx)

    h, Q = h_init.copy(), Q_init.copy()

    mass_errors = []
    success = True

    # 推进20步
    for step in range(20):
        h, Q = solver.solve_canal_step(
            h, Q, dt, dx, width, manning_n, slope, bc
        )

        if np.any(np.isnan(h)) or np.any(np.isnan(Q)):
            print(f"  ❌ 步骤{step+1}出现NaN")
            success = False
            break

        current_mass = np.sum(h[:-1] * width * dx)
        mass_error = abs((current_mass - initial_mass) / initial_mass * 100)
        mass_errors.append(mass_error)

    if success:
        final_mass = np.sum(h[:-1] * width * dx)
        avg_mass_error = np.mean(mass_errors)
        max_mass_error = np.max(mass_errors)
        h_deviation = np.max(np.abs(h - 2.0))
        Q_max = np.max(np.abs(Q))

        print(f"  初始质量: {initial_mass:.2f} m³")
        print(f"  最终质量: {final_mass:.2f} m³")
        print(f"  平均质量误差: {avg_mass_error:.6f}%")
        print(f"  最大质量误差: {max_mass_error:.6f}%")
        print(f"  最大水深偏差: {h_deviation:.6e} m")
        print(f"  最大流量: {Q_max:.6e} m³/s")

        # 判断标准
        success = (max_mass_error < 1.0 and h_deviation < 0.01 and Q_max < 1.0)
        print(f"  结果: {'✅ 通过' if success else '❌ 失败'}")

    return success


def test_2_uniform_flow():
    """
    测试2: 均匀流（恒定坡度+初始均匀流）

    物理条件：
    - S0 = 0.001（恒定坡度）
    - 初始：根据Manning公式计算的均匀流
    - 边界：上下游固定水位

    预期结果：
    - 接近稳态（小变化）
    - 质量守恒良好
    """
    print("\n" + "="*80)
    print("测试2: 均匀流（恒定坡度）")
    print("="*80)

    solver = PreissmannSolverCorrected(verbose=False, tolerance=1e-5, max_iter=30)

    n_cells = 30
    length = 1500.0
    dx = length / n_cells
    width = 10.0
    manning_n = 0.025
    slope = 0.001
    dt = 30.0

    # 初始条件：计算均匀流（Manning公式近似）
    h_uniform = 2.0  # 假设均匀流水深2m
    A = h_uniform * width
    P = width + 2 * h_uniform
    R = A / P
    # Q_uniform = (1/n) * A * R^(2/3) * S0^(1/2)
    Q_uniform = (1.0 / manning_n) * A * R**(2.0/3.0) * slope**0.5

    print(f"  均匀流参数: h={h_uniform:.2f}m, Q={Q_uniform:.3f}m³/s")

    h_init = np.ones(n_cells + 1) * h_uniform
    Q_init = np.ones(n_cells + 1) * Q_uniform

    # 边界：维持均匀流水位
    bc = {
        'upstream_level': h_uniform,
        'downstream_level': h_uniform - slope * length  # 考虑坡度的水位差
    }

    initial_mass = np.sum(h_init[:-1] * width * dx)

    h, Q = h_init.copy(), Q_init.copy()

    mass_errors = []
    success = True

    # 推进50步
    for step in range(50):
        h, Q = solver.solve_canal_step(
            h, Q, dt, dx, width, manning_n, slope, bc
        )

        if np.any(np.isnan(h)) or np.any(np.isnan(Q)):
            print(f"  ❌ 步骤{step+1}出现NaN")
            success = False
            break

        current_mass = np.sum(h[:-1] * width * dx)
        mass_error = abs((current_mass - initial_mass) / initial_mass * 100)
        mass_errors.append(mass_error)

    if success:
        final_mass = np.sum(h[:-1] * width * dx)
        avg_mass_error = np.mean(mass_errors)
        max_mass_error = np.max(mass_errors)

        print(f"  初始质量: {initial_mass:.2f} m³")
        print(f"  最终质量: {final_mass:.2f} m³")
        print(f"  平均质量误差: {avg_mass_error:.6f}%")
        print(f"  最大质量误差: {max_mass_error:.6f}%")
        print(f"  上游水深: h[0]={h[0]:.3f}m (目标{bc['upstream_level']:.3f}m)")
        print(f"  下游水深: h[-1]={h[-1]:.3f}m (目标{bc['downstream_level']:.3f}m)")
        print(f"  平均流量: {np.mean(Q):.3f} m³/s (目标{Q_uniform:.3f}m³/s)")

        # 判断标准：质量误差<10%
        success = (max_mass_error < 10.0)
        print(f"  结果: {'✅ 通过' if success else '❌ 失败'}")

    return success


def test_3_water_level_step():
    """
    测试3: 水位阶跃传播

    物理条件：
    - S0 = 0（平坦河床）
    - 初始：均匀水深2.0m，静止
    - 边界：t>0时上游水位突然升高到2.5m

    预期结果：
    - 水位波向下游传播
    - 质量增加量≈上游进水量
    """
    print("\n" + "="*80)
    print("测试3: 水位阶跃传播")
    print("="*80)

    solver = PreissmannSolverCorrected(verbose=False, tolerance=1e-5, max_iter=30)

    n_cells = 40
    length = 2000.0
    dx = length / n_cells
    width = 10.0
    manning_n = 0.025
    slope = 0.0  # 平坦河床
    dt = 20.0

    # 初始：静水
    h_init = np.ones(n_cells + 1) * 2.0
    Q_init = np.zeros(n_cells + 1)

    initial_mass = np.sum(h_init[:-1] * width * dx)

    h, Q = h_init.copy(), Q_init.copy()

    mass_errors = []
    success = True

    # 推进100步
    for step in range(100):
        # 前20步：静水
        # 后80步：上游水位升高
        if step < 20:
            bc = {
                'upstream_level': 2.0,
                'downstream_level': 2.0
            }
        else:
            bc = {
                'upstream_level': 2.5,  # 升高0.5m
                'downstream_level': 2.0
            }

        h, Q = solver.solve_canal_step(
            h, Q, dt, dx, width, manning_n, slope, bc
        )

        if np.any(np.isnan(h)) or np.any(np.isnan(Q)):
            print(f"  ❌ 步骤{step+1}出现NaN")
            success = False
            break

        current_mass = np.sum(h[:-1] * width * dx)
        # 注意：水位升高会增加质量，所以质量应该增加
        mass_change = current_mass - initial_mass

    if success:
        final_mass = np.sum(h[:-1] * width * dx)
        mass_change_pct = (final_mass - initial_mass) / initial_mass * 100

        print(f"  初始质量: {initial_mass:.2f} m³")
        print(f"  最终质量: {final_mass:.2f} m³")
        print(f"  质量变化: {mass_change_pct:.3f}%")
        print(f"  上游水深: h[0]={h[0]:.3f}m (目标2.5m)")
        print(f"  下游水深: h[-1]={h[-1]:.3f}m (目标2.0m)")
        print(f"  平均水深: {np.mean(h):.3f}m")
        print(f"  最大流量: {np.max(np.abs(Q)):.3f} m³/s")

        # 判断标准：质量应该增加（因为上游水位升高），且幅度合理
        success = (0 < mass_change_pct < 50.0 and not np.any(np.isnan(h)))
        print(f"  结果: {'✅ 通过' if success else '❌ 失败'}")

    return success


if __name__ == "__main__":
    print("\n" + "="*80)
    print("Preissmann修正版求解器 - 完整测试套件")
    print("="*80)

    results = []

    results.append(("静水测试（平坦河床）", test_1_still_water()))
    results.append(("均匀流测试", test_2_uniform_flow()))
    results.append(("水位阶跃传播测试", test_3_water_level_step()))

    print("\n" + "="*80)
    print("测试总结")
    print("="*80)

    for name, result in results:
        status = "✅ 通过" if result else "❌ 失败"
        print(f"  {name}: {status}")

    total_pass = sum(1 for _, r in results if r)
    print(f"\n  总计: {total_pass}/{len(results)} 通过")

    if total_pass == len(results):
        print("\n  🎉 所有测试通过！修正版Preissmann求解器可用")
    elif total_pass > 0:
        print(f"\n  ⚠️ 部分测试通过，需要进一步调试")
    else:
        print(f"\n  ❌ 所有测试失败，需要重新审视算法")

    print("="*80)
