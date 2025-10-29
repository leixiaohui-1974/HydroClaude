#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Well-Balanced格式测试

测试hydrostatic reconstruction是否能保持water-at-rest
这是well-balanced格式的关键性质！

测试场景:
1. 水静止在变化的底床上 (Q=0, ∂η/∂x=0)
2. 理论：应该永远保持静止 (Q=0, h不变)
3. 数值：如果不是well-balanced，会产生spurious flow

作者: HydroClaude Team
日期: 2025-10-29
"""

import numpy as np
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from solvers.godunov_fvm_solver import GodunvFVMSolver


def test_water_at_rest_flat_bottom():
    """测试1: 平底上的静水（基准测试）"""
    print("=" * 80)
    print("测试1: 平底上的静水")
    print("=" * 80)

    # 参数
    b = 10.0
    L = 1000.0
    n_cells = 100
    h_init = 5.0  # 均匀水深

    for well_balanced in [False, True]:
        print(f"\nWell-Balanced: {'启用' if well_balanced else '禁用'}")
        print("-" * 80)

        solver = GodunvFVMSolver(
            width=b, length=L, n_cells=n_cells,
            manning_n=0.0,  # 无摩阻
            slope=0.0,      # 平底
            g=9.81, cfl=0.5,
            well_balanced=well_balanced
        )

        # 初始条件：静水
        h = np.ones(n_cells) * h_init
        Q = np.zeros(n_cells)

        solver.initialize(
            h, Q,
            bc_left={'type': 'h', 'value': h_init},
            bc_right={'type': 'h', 'value': h_init}
        )

        # 推进1000步
        for _ in range(1000):
            solver.step()

        # 分析
        max_Q = np.max(np.abs(solver.Q))
        max_h_dev = np.max(np.abs(solver.h - h_init))

        print(f"  1000步后:")
        print(f"    max|Q|: {max_Q:.3e} m³/s")
        print(f"    max|h-h₀|: {max_h_dev:.3e} m")

        # 判断
        if max_Q < 1e-10 and max_h_dev < 1e-10:
            print(f"    ✅ 保持静止 (Perfect well-balanced)")
        elif max_Q < 1e-6:
            print(f"    ✅ 近似静止 (Good)")
        else:
            print(f"    ⚠️  产生spurious flow")

    print()


def test_water_at_rest_sloped_bottom():
    """测试2: 斜底上的静水（关键测试！）"""
    print("=" * 80)
    print("测试2: 斜底上的静水（Well-Balanced关键测试）")
    print("=" * 80)

    # 参数
    b = 10.0
    L = 1000.0
    n_cells = 100
    S0 = 0.01  # 1%坡度

    # 构造水面平齐的初始条件
    # η = h + z_b = constant
    # 取η=10m（水面高程）
    eta_surface = 10.0

    for well_balanced in [False, True]:
        print(f"\nWell-Balanced: {'启用' if well_balanced else '禁用'}")
        print("-" * 80)

        solver = GodunvFVMSolver(
            width=b, length=L, n_cells=n_cells,
            manning_n=0.0,  # 无摩阻
            slope=S0,       # 斜底
            g=9.81, cfl=0.5,
            well_balanced=well_balanced
        )

        # 初始条件：水面平齐
        h_init = eta_surface - solver.z_b  # h = η - z_b
        Q_init = np.zeros(n_cells)

        print(f"  初始条件:")
        print(f"    水面高程 η: {eta_surface:.2f} m")
        print(f"    底高程范围: [{solver.z_b.min():.2f}, {solver.z_b.max():.2f}] m")
        print(f"    水深范围: [{h_init.min():.2f}, {h_init.max():.2f}] m")

        solver.initialize(
            h_init, Q_init,
            bc_left={'type': 'h', 'value': h_init[0]},
            bc_right={'type': 'h', 'value': h_init[-1]}
        )

        # 推进1000步
        initial_Q = solver.Q.copy()
        initial_h = solver.h.copy()

        for step in range(1000):
            solver.step()

            # 检查是否发散
            if np.any(np.isnan(solver.h)) or np.any(np.isnan(solver.Q)):
                print(f"  ✗ NaN at step {step+1}")
                break

        # 分析
        max_Q = np.max(np.abs(solver.Q))
        Q_rms = np.sqrt(np.mean(solver.Q**2))

        # 水面变化
        eta_final = solver.h + solver.z_b
        eta_deviation = np.max(np.abs(eta_final - eta_surface))

        # 水深变化
        h_change = np.max(np.abs(solver.h - initial_h))

        print(f"\n  1000步后:")
        print(f"    max|Q|: {max_Q:.3e} m³/s")
        print(f"    Q_rms: {Q_rms:.3e} m³/s")
        print(f"    水面偏差: {eta_deviation:.3e} m")
        print(f"    水深变化: {h_change:.3e} m")

        # 判断（well-balanced格式的关键测试！）
        if well_balanced:
            # Well-balanced应该machine precision级别
            if max_Q < 1e-10 and eta_deviation < 1e-10:
                print(f"    ✅✅✅ Perfect Well-Balanced！")
            elif max_Q < 1e-6:
                print(f"    ✅ Good Well-Balanced")
            else:
                print(f"    ⚠️  Well-Balanced效果不理想")
        else:
            # 标准格式会产生spurious flow
            if max_Q > 1e-6:
                print(f"    ⚠️  产生spurious flow (符合预期)")
                print(f"    → 这说明需要well-balanced格式")
            else:
                print(f"    ? 意外地保持静止")

    print()


def test_water_at_rest_varying_slope():
    """测试3: 变化坡度上的静水（最严格测试）"""
    print("=" * 80)
    print("测试3: 变化坡度上的静水（Well-Balanced最严格测试）")
    print("=" * 80)

    # 参数
    b = 10.0
    L = 1000.0
    n_cells = 100

    # 构造复杂的底地形
    x = np.linspace(0.5*L/n_cells, L - 0.5*L/n_cells, n_cells)
    # S0 = 0.01 + 0.005*sin(2πx/L) （正弦变化坡度）
    S0 = 0.01 + 0.005 * np.sin(2 * np.pi * x / L)

    # 水面高程
    eta_surface = 15.0

    for well_balanced in [False, True]:
        print(f"\nWell-Balanced: {'启用' if well_balanced else '禁用'}")
        print("-" * 80)

        solver = GodunvFVMSolver(
            width=b, length=L, n_cells=n_cells,
            manning_n=0.0,
            slope=S0,  # 变化坡度
            g=9.81, cfl=0.5,
            well_balanced=well_balanced
        )

        # 初始条件：水面平齐
        h_init = eta_surface - solver.z_b
        Q_init = np.zeros(n_cells)

        print(f"  初始条件:")
        print(f"    水面高程: {eta_surface:.2f} m")
        print(f"    坡度范围: [{S0.min():.4f}, {S0.max():.4f}]")
        print(f"    底高程范围: [{solver.z_b.min():.2f}, {solver.z_b.max():.2f}] m")
        print(f"    水深范围: [{h_init.min():.2f}, {h_init.max():.2f}] m")

        solver.initialize(
            h_init, Q_init,
            bc_left={'type': 'h', 'value': h_init[0]},
            bc_right={'type': 'h', 'value': h_init[-1]}
        )

        # 推进1000步
        for step in range(1000):
            solver.step()

            if np.any(np.isnan(solver.h)):
                print(f"  ✗ NaN at step {step+1}")
                break

        # 分析
        max_Q = np.max(np.abs(solver.Q))
        eta_final = solver.h + solver.z_b
        eta_deviation = np.max(np.abs(eta_final - eta_surface))

        print(f"\n  1000步后:")
        print(f"    max|Q|: {max_Q:.3e} m³/s")
        print(f"    水面偏差: {eta_deviation:.3e} m")

        if well_balanced:
            if max_Q < 1e-9 and eta_deviation < 1e-9:
                print(f"    ✅✅✅ Excellent Well-Balanced！")
            elif max_Q < 1e-6:
                print(f"    ✅ Good Well-Balanced")
            else:
                print(f"    ⚠️  需要改进")
        else:
            if max_Q > 1e-5:
                print(f"    ⚠️  严重spurious flow (预期)")

    print()


def test_small_perturbation():
    """测试4: 小扰动传播（well-balanced不影响动力学）"""
    print("=" * 80)
    print("测试4: 小扰动传播（验证well-balanced不影响正常动力学）")
    print("=" * 80)

    # 参数
    b = 10.0
    L = 1000.0
    n_cells = 200
    S0 = 0.005
    eta_base = 10.0

    results = {}

    for well_balanced in [False, True]:
        print(f"\nWell-Balanced: {'启用' if well_balanced else '禁用'}")
        print("-" * 80)

        solver = GodunvFVMSolver(
            width=b, length=L, n_cells=n_cells,
            manning_n=0.0,
            slope=S0,
            g=9.81, cfl=0.5,
            well_balanced=well_balanced
        )

        # 初始条件：静水 + 小扰动
        h_init = eta_base - solver.z_b
        # 在中间添加小扰动
        perturbation = 0.1 * np.exp(-((solver.x - L/2)**2) / (L/20)**2)
        h_init += perturbation
        Q_init = np.zeros(n_cells)

        solver.initialize(
            h_init, Q_init,
            bc_left={'type': 'h', 'value': h_init[0]},
            bc_right={'type': 'h', 'value': h_init[-1]}
        )

        # 推进500步
        for _ in range(500):
            solver.step()

        # 记录结果
        results[well_balanced] = {
            'h': solver.h.copy(),
            'Q': solver.Q.copy(),
            'max_Q': np.max(np.abs(solver.Q))
        }

        print(f"  500步后:")
        print(f"    max|Q|: {results[well_balanced]['max_Q']:.4f} m³/s")
        print(f"    扰动已传播")

    # 比较两种格式
    if False in results and True in results:
        h_diff = np.max(np.abs(results[True]['h'] - results[False]['h']))
        Q_diff = np.max(np.abs(results[True]['Q'] - results[False]['Q']))

        print(f"\n两种格式对比:")
        print(f"  h差异: {h_diff:.3e} m")
        print(f"  Q差异: {Q_diff:.3e} m³/s")

        if h_diff < 0.01 and Q_diff < 0.1:
            print(f"  ✅ Well-balanced不影响正常动力学")
        else:
            print(f"  ⚠️  两种格式结果有差异")

    print()


def run_all_tests():
    """运行所有测试"""
    print("\n")
    print("*" * 80)
    print("Well-Balanced格式综合测试")
    print("*" * 80)
    print()

    try:
        test_water_at_rest_flat_bottom()
        test_water_at_rest_sloped_bottom()
        test_water_at_rest_varying_slope()
        test_small_perturbation()

        print("=" * 80)
        print("✅ 所有Well-Balanced测试完成！")
        print("=" * 80)
        return True

    except Exception as e:
        print(f"\n❌ 测试失败: {e}")
        import traceback
        traceback.print_exc()
        return False


if __name__ == '__main__':
    success = run_all_tests()
    sys.exit(0 if success else 1)
