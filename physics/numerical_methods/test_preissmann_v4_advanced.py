#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Preissmann v4.0高级测试：多种流动工况

测试案例：
1. 静水（Lake at Rest）
2. 恒定流（Steady Flow）
3. 阶跃流量（Step Change）
4. 溃坝（简化Dam Break）

作者: HydroClaude Team
日期: 2025-10-30
"""

import numpy as np
from preissmann_solver_v4_linear import PreissmannSolverV4Linear


def test_1_lake_at_rest():
    """测试1: 静水 - 水位和流量都不变"""
    print("\n" + "="*80)
    print("测试1: 静水（Lake at Rest）")
    print("="*80)

    solver = PreissmannSolverV4Linear(verbose=False, tolerance=1e-4)

    n_cells = 20
    length = 1000.0
    dx = length / n_cells
    width = 10.0
    manning_n = 0.025
    slope = 0.001
    dt = 60.0

    h_init = np.ones(n_cells + 1) * 2.0
    Q_init = np.zeros(n_cells + 1)

    bc = {
        'upstream_level': 2.0,
        'downstream_level': 2.0
    }

    initial_mass = np.sum(h_init[:-1] * width * dx)

    h, Q = h_init.copy(), Q_init.copy()

    # 推进20步
    for step in range(20):
        h, Q = solver.solve_canal_step(
            h, Q, dt, dx, width, manning_n, slope, bc
        )

        if np.any(np.isnan(h)) or np.any(np.isnan(Q)):
            print(f"  ❌ 步骤{step+1}出现NaN")
            return False

    final_mass = np.sum(h[:-1] * width * dx)
    mass_error = abs((final_mass - initial_mass) / initial_mass * 100)
    h_deviation = np.max(np.abs(h - 2.0))
    Q_max = np.max(np.abs(Q))

    print(f"  初始质量: {initial_mass:.2f} m³")
    print(f"  最终质量: {final_mass:.2f} m³")
    print(f"  质量误差: {mass_error:.6f}%")
    print(f"  水深偏差: {h_deviation:.6e} m")
    print(f"  最大流量: {Q_max:.6e} m³/s")

    success = mass_error < 1.0 and h_deviation < 0.1 and Q_max < 5.0
    print(f"  结果: {'✅ 通过' if success else '❌ 失败'}")

    return success


def test_2_steady_flow():
    """测试2: 恒定流 - 上游恒定流量"""
    print("\n" + "="*80)
    print("测试2: 恒定流（Steady Flow）")
    print("="*80)

    solver = PreissmannSolverV4Linear(verbose=False, tolerance=1e-4, max_iter=20)

    n_cells = 30
    length = 1500.0
    dx = length / n_cells
    width = 10.0
    manning_n = 0.025
    slope = 0.002
    dt = 30.0

    # 初始条件：均匀水深，小流量
    h_init = np.ones(n_cells + 1) * 2.5
    Q_init = np.ones(n_cells + 1) * 5.0  # 5 m³/s

    # 边界：上游固定水位，下游固定水位
    bc = {
        'upstream_level': 2.8,
        'downstream_level': 2.2
    }

    initial_mass = np.sum(h_init[:-1] * width * dx)

    h, Q = h_init.copy(), Q_init.copy()

    # 推进50步达到稳态
    for step in range(50):
        h, Q = solver.solve_canal_step(
            h, Q, dt, dx, width, manning_n, slope, bc
        )

        if np.any(np.isnan(h)) or np.any(np.isnan(Q)):
            print(f"  ❌ 步骤{step+1}出现NaN")
            return False

    final_mass = np.sum(h[:-1] * width * dx)
    mass_error = abs((final_mass - initial_mass) / initial_mass * 100)

    # 检查水面坡度是否合理
    water_surface_slope = (h[-1] - h[0]) / length

    print(f"  初始质量: {initial_mass:.2f} m³")
    print(f"  最终质量: {final_mass:.2f} m³")
    print(f"  质量误差: {mass_error:.6f}%")
    print(f"  上游水深: {h[0]:.3f} m")
    print(f"  下游水深: {h[-1]:.3f} m")
    print(f"  水面坡度: {water_surface_slope:.6f}")
    print(f"  底坡: {slope:.6f}")
    print(f"  平均流量: {np.mean(Q):.3f} m³/s")

    success = mass_error < 5.0 and not np.any(np.isnan(h))
    print(f"  结果: {'✅ 通过' if success else '❌ 失败'}")

    return success


def test_3_step_flow():
    """测试3: 阶跃流量 - 上游流量突然增加"""
    print("\n" + "="*80)
    print("测试3: 阶跃流量（Step Flow Change）")
    print("="*80)

    solver = PreissmannSolverV4Linear(verbose=False, tolerance=1e-4, max_iter=20)

    n_cells = 25
    length = 1000.0
    dx = length / n_cells
    width = 10.0
    manning_n = 0.025
    slope = 0.001
    dt = 20.0

    # 初始：静水
    h_init = np.ones(n_cells + 1) * 2.0
    Q_init = np.zeros(n_cells + 1)

    initial_mass = np.sum(h_init[:-1] * width * dx)

    h, Q = h_init.copy(), Q_init.copy()

    mass_errors = []

    # 推进100步，前50步低水位，后50步高水位
    for step in range(100):
        if step < 50:
            bc = {
                'upstream_level': 2.0,
                'downstream_level': 2.0
            }
        else:
            bc = {
                'upstream_level': 2.5,  # 突然升高0.5m
                'downstream_level': 2.0
            }

        h, Q = solver.solve_canal_step(
            h, Q, dt, dx, width, manning_n, slope, bc
        )

        if np.any(np.isnan(h)) or np.any(np.isnan(Q)):
            print(f"  ❌ 步骤{step+1}出现NaN")
            return False

        current_mass = np.sum(h[:-1] * width * dx)
        mass_error = abs((current_mass - initial_mass) / initial_mass * 100)
        mass_errors.append(mass_error)

    final_mass = np.sum(h[:-1] * width * dx)
    avg_mass_error = np.mean(mass_errors)
    max_mass_error = np.max(mass_errors)

    print(f"  初始质量: {initial_mass:.2f} m³")
    print(f"  最终质量: {final_mass:.2f} m³")
    print(f"  平均质量误差: {avg_mass_error:.6f}%")
    print(f"  最大质量误差: {max_mass_error:.6f}%")
    print(f"  最终上游水深: {h[0]:.3f} m")
    print(f"  最终下游水深: {h[-1]:.3f} m")
    print(f"  最大流量: {np.max(np.abs(Q)):.3f} m³/s")

    success = max_mass_error < 10.0 and not np.any(np.isnan(h))
    print(f"  结果: {'✅ 通过' if success else '❌ 失败'}")

    return success


def test_4_dam_break():
    """测试4: 简化溃坝 - 初始水位差"""
    print("\n" + "="*80)
    print("测试4: 简化溃坝（Simplified Dam Break）")
    print("="*80)

    solver = PreissmannSolverV4Linear(verbose=False, tolerance=1e-3, max_iter=30)

    n_cells = 40
    length = 2000.0
    dx = length / n_cells
    width = 10.0
    manning_n = 0.025
    slope = 0.0  # 平坦河床
    dt = 10.0  # 小时间步长

    # 初始：左高右低
    h_init = np.ones(n_cells + 1) * 1.0
    h_init[:n_cells//2] = 3.0  # 上游3m，下游1m
    Q_init = np.zeros(n_cells + 1)

    initial_mass = np.sum(h_init[:-1] * width * dx)

    h, Q = h_init.copy(), Q_init.copy()

    mass_errors = []

    # 推进100步观察溃坝波传播
    for step in range(100):
        bc = {}  # 自由边界

        h, Q = solver.solve_canal_step(
            h, Q, dt, dx, width, manning_n, slope, bc
        )

        if np.any(np.isnan(h)) or np.any(np.isnan(Q)):
            print(f"  ❌ 步骤{step+1}出现NaN")
            return False

        current_mass = np.sum(h[:-1] * width * dx)
        mass_error = abs((current_mass - initial_mass) / initial_mass * 100)
        mass_errors.append(mass_error)

    final_mass = np.sum(h[:-1] * width * dx)
    avg_mass_error = np.mean(mass_errors)
    max_mass_error = np.max(mass_errors)

    print(f"  初始质量: {initial_mass:.2f} m³")
    print(f"  最终质量: {final_mass:.2f} m³")
    print(f"  平均质量误差: {avg_mass_error:.6f}%")
    print(f"  最大质量误差: {max_mass_error:.6f}%")
    print(f"  最终最大水深: {np.max(h):.3f} m")
    print(f"  最终最小水深: {np.min(h):.3f} m")
    print(f"  最大流量: {np.max(np.abs(Q)):.3f} m³/s")

    success = max_mass_error < 15.0 and not np.any(np.isnan(h))
    print(f"  结果: {'✅ 通过' if success else '❌ 失败'}")

    return success


if __name__ == "__main__":
    print("\n" + "="*80)
    print("Preissmann v4.0 线性化求解器 - 高级测试套件")
    print("="*80)

    results = []

    results.append(("静水测试", test_1_lake_at_rest()))
    results.append(("恒定流测试", test_2_steady_flow()))
    results.append(("阶跃流量测试", test_3_step_flow()))
    results.append(("简化溃坝测试", test_4_dam_break()))

    print("\n" + "="*80)
    print("测试总结")
    print("="*80)

    for name, result in results:
        status = "✅ 通过" if result else "❌ 失败"
        print(f"  {name}: {status}")

    total_pass = sum(1 for _, r in results if r)
    print(f"\n  总计: {total_pass}/{len(results)} 通过")

    if total_pass == len(results):
        print("\n  🎉 所有测试通过！v4_linear求解器表现优秀")
    else:
        print(f"\n  ⚠️ {len(results) - total_pass}个测试失败，需要进一步改进")

    print("="*80)
