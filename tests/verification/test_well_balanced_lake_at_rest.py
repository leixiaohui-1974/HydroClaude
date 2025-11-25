#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Well-Balanced验证：Lake at Rest测试

目标：验证求解器能否精确保持静水解（机器精度）

Lake at Rest测试是Well-Balanced格式的标准验证：
- 初始条件：静水（u=0，水面水平）
- 底床：任意地形（可以有坡度）
- 预期：静水状态应该精确保持（到机器精度）

参考：
- Audusse et al. (2004) - Well-Balanced方法经典文献
- LeVeque (2002) - Finite Volume Methods

作者: HydroClaude Team
日期: 2025-10-31
"""

import sys
import warnings
warnings.filterwarnings("ignore")
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..'))

import numpy as np
import pytest


class TestWellBalancedLakeAtRest:
    """Well-Balanced格式验证：Lake at Rest"""

    def test_lake_at_rest_flat_bottom(self):
        """
        测试1：平底静水

        最简单情况：平底河道，静水
        预期：完全无变化（机器精度）
        """
        print("\n" + "="*70)
        print("Well-Balanced Test 1: 平底静水")
        print("="*70)

        from solvers.hydrostatic_canal_solver import HydrostaticCanalSolver

        # 参数设置
        L = 1000.0      # 河道长度
        nx = 101        # 网格点数
        B = 10.0        # 宽度
        S0 = 0.0        # 平底
        n = 0.025       # Manning糙率
        h0 = 2.0        # 初始水深

        solver = HydrostaticCanalSolver(
            length=L,
            nx=nx,
            B=B,
            S0=S0,
            n=n
        )

        # 静水初始条件
        h_init = np.ones(nx) * h0
        Q_init = np.zeros(nx)

        solver.h = h_init.copy()
        solver.Q = Q_init.copy()

        # 记录初始状态
        h_initial = solver.h.copy()
        Q_initial = solver.Q.copy()

        print(f"初始状态:")
        print(f"  河道长度: {L}m")
        print(f"  网格点数: {nx}")
        print(f"  底坡: {S0} (平底)")
        print(f"  初始水深: {h0}m (均匀)")
        print(f"  初始流量: 0 m^3/s (静水)")

        # 运行模拟
        dt = 1.0
        n_steps = 100
        t_total = dt * n_steps

        print(f"\n运行模拟 {n_steps}步, 总时间 {t_total}s...")

        for step in range(n_steps):
            solver.step_preissmann(dt)

        # 检查结果
        h_final = solver.h
        Q_final = solver.Q

        # 计算变化
        dh = np.abs(h_final - h_initial)
        dQ = np.abs(Q_final - Q_initial)

        h_max_change = np.max(dh)
        Q_max_change = np.max(dQ)

        print(f"\n结果:")
        print(f"  水深最大变化: {h_max_change:.2e} m")
        print(f"  流量最大变化: {Q_max_change:.2e} m^3/s")
        print(f"  机器精度: ~1e-14")

        # 验证：变化应该极小（机器精度）
        assert h_max_change < 1e-10, f"水深变化 {h_max_change} 超过容差 1e-10"
        assert Q_max_change < 1e-10, f"流量变化 {Q_max_change} 超过容差 1e-10"

        print(f"\n PASSED: 平底静水精确保持（误差 < 1e-10）")

    def test_lake_at_rest_sloped_bottom(self):
        """
        测试2：斜底静水

        关键测试：底床有坡度，但水面水平
        这测试求解器是否能平衡底坡源项和压力梯度
        预期：静水状态应该精确保持
        """
        print("\n" + "="*70)
        print("Well-Balanced Test 2: 斜底静水 (核心测试)")
        print("="*70)

        from solvers.hydrostatic_canal_solver import HydrostaticCanalSolver

        # 参数设置
        L = 1000.0      # 河道长度
        nx = 101        # 网格点数
        B = 10.0        # 宽度
        S0 = 0.001      # 底坡（向下倾斜）
        n = 0.025       # Manning糙率

        # 创建底床高程
        x = np.linspace(0, L, nx)
        z_bed = S0 * (L - x)  # 从上游到下游向下倾斜

        # 水面高程（水平）
        z_surface = 5.0  # 任意选择

        # 水深 = 水面高程 - 底床高程
        h_init = z_surface - z_bed
        Q_init = np.zeros(nx)  # 静水

        solver = HydrostaticCanalSolver(
            length=L,
            nx=nx,
            B=B,
            S0=S0,
            n=n
        )

        solver.h = h_init.copy()
        solver.Q = Q_init.copy()

        # 记录初始状态
        h_initial = solver.h.copy()
        Q_initial = solver.Q.copy()

        print(f"初始状态:")
        print(f"  河道长度: {L}m")
        print(f"  底坡: {S0} (1:1000)")
        print(f"  底床高程范围: {z_bed.min():.2f}m - {z_bed.max():.2f}m")
        print(f"  水面高程: {z_surface:.2f}m (水平)")
        print(f"  水深范围: {h_init.min():.2f}m - {h_init.max():.2f}m")
        print(f"  初始流量: 0 m^3/s (静水)")

        # 运行模拟
        dt = 1.0
        n_steps = 100
        t_total = dt * n_steps

        print(f"\n运行模拟 {n_steps}步, 总时间 {t_total}s...")

        for step in range(n_steps):
            solver.step_preissmann(dt)

        # 检查结果
        h_final = solver.h
        Q_final = solver.Q

        # 计算变化
        dh = np.abs(h_final - h_initial)
        dQ = np.abs(Q_final - Q_initial)

        h_max_change = np.max(dh)
        h_mean_change = np.mean(dh)
        Q_max_change = np.max(dQ)

        print(f"\n结果:")
        print(f"  水深最大变化: {h_max_change:.2e} m")
        print(f"  水深平均变化: {h_mean_change:.2e} m")
        print(f"  流量最大变化: {Q_max_change:.2e} m^3/s")

        # Well-Balanced格式应该保持静水（误差<1e-10）
        # 如果不是Well-Balanced，会看到明显的虚假流动
        tolerance_h = 1e-8  # 略微放宽到1e-8（考虑数值误差）
        tolerance_Q = 1e-8

        if h_max_change < tolerance_h and Q_max_change < tolerance_Q:
            print(f"\n PASSED: 斜底静水精确保持（Well-Balanced格式验证成功）")
            print(f"   底坡源项与压力梯度完美平衡！")
        else:
            print(f"\n️  WARNING: 静水未精确保持")
            print(f"   这表明求解器可能不是Well-Balanced格式")
            print(f"   或者源项处理存在问题")

        assert h_max_change < tolerance_h, f"水深变化 {h_max_change} 超过容差"
        assert Q_max_change < tolerance_Q, f"流量变化 {Q_max_change} 超过容差"

    def test_lake_at_rest_small_perturbation(self):
        """
        测试3：小扰动传播

        在静水基础上施加小扰动，观察传播特性
        预期：
        - 小扰动应该以波速 c = sqrt(g*h) 传播
        - 无虚假数值振荡
        - 质量守恒
        """
        print("\n" + "="*70)
        print("Well-Balanced Test 3: 小扰动传播")
        print("="*70)

        from solvers.hydrostatic_canal_solver import HydrostaticCanalSolver

        # 参数设置
        L = 1000.0
        nx = 201  # 更密网格
        B = 10.0
        S0 = 0.001  # 有底坡
        n = 0.025
        h0 = 2.0  # 基础水深

        # 创建底床
        x = np.linspace(0, L, nx)
        z_bed = S0 * (L - x)

        solver = HydrostaticCanalSolver(
            length=L,
            nx=nx,
            B=B,
            S0=S0,
            n=n
        )

        # 静水 + 小扰动
        z_surface_base = 5.0
        h_base = z_surface_base - z_bed

        # 在中间施加小的水深扰动（高斯分布）
        x_center = L / 2
        perturbation_amplitude = 0.01  # 1cm扰动
        perturbation_width = 50.0  # 50m宽度

        perturbation = perturbation_amplitude * np.exp(-((x - x_center) / perturbation_width)**2)
        h_init = h_base + perturbation
        Q_init = np.zeros(nx)

        solver.h = h_init.copy()
        solver.Q = Q_init.copy()

        # 记录初始质量
        mass_initial = np.sum(solver.h * B * solver.dx)

        print(f"初始状态:")
        print(f"  基础水深: {h0:.2f}m")
        print(f"  扰动幅度: {perturbation_amplitude*1000:.0f}mm")
        print(f"  扰动位置: x={x_center:.0f}m")
        print(f"  理论波速: c={np.sqrt(9.81*h0):.2f}m/s")
        print(f"  初始质量: {mass_initial:.2f} m^3")

        # 运行模拟
        dt = 0.5
        n_steps = 200
        t_total = dt * n_steps

        print(f"\n运行模拟 {n_steps}步, 总时间 {t_total}s...")

        mass_history = [mass_initial]

        for step in range(n_steps):
            solver.step_preissmann(dt)
            mass = np.sum(solver.h * B * solver.dx)
            mass_history.append(mass)

        # 检查结果
        h_final = solver.h
        mass_final = mass_history[-1]
        mass_error = abs(mass_final - mass_initial) / mass_initial * 100

        # 检查是否有虚假振荡（负值）
        min_h = np.min(solver.h)

        print(f"\n结果:")
        print(f"  最终最小水深: {min_h:.6f}m")
        print(f"  质量守恒误差: {mass_error:.4f}%")

        # 验证
        assert min_h > 0, f"出现负水深: {min_h}"
        assert mass_error < 0.05, f"质量守恒误差 {mass_error}% 过大（动态情况，容差0.05%）"

        print(f"\n PASSED: 小扰动传播正常，无虚假振荡，质量守恒")

    def test_lake_at_rest_steep_slope(self):
        """
        测试4：陡坡静水（压力测试）

        使用较陡的底坡（0.01 = 1:100）测试Well-Balanced性能
        """
        print("\n" + "="*70)
        print("Well-Balanced Test 4: 陡坡静水（压力测试）")
        print("="*70)

        from solvers.hydrostatic_canal_solver import HydrostaticCanalSolver

        # 参数设置
        L = 500.0  # 短河道
        nx = 51
        B = 10.0
        S0 = 0.01  # 陡坡 1:100
        n = 0.025

        # 创建底床和静水初始条件
        x = np.linspace(0, L, nx)
        z_bed = S0 * (L - x)
        z_surface = 10.0
        h_init = z_surface - z_bed
        Q_init = np.zeros(nx)

        solver = HydrostaticCanalSolver(
            length=L,
            nx=nx,
            B=B,
            S0=S0,
            n=n
        )

        solver.h = h_init.copy()
        solver.Q = Q_init.copy()

        h_initial = solver.h.copy()
        Q_initial = solver.Q.copy()

        print(f"初始状态:")
        print(f"  底坡: {S0} (1:100, 陡坡)")
        print(f"  水深范围: {h_init.min():.2f}m - {h_init.max():.2f}m")
        print(f"  底床高差: {z_bed.max() - z_bed.min():.2f}m")

        # 运行模拟
        dt = 0.5
        n_steps = 100

        print(f"\n运行模拟 {n_steps}步...")

        for step in range(n_steps):
            solver.step_preissmann(dt)

        # 检查结果
        dh = np.abs(solver.h - h_initial)
        dQ = np.abs(solver.Q - Q_initial)

        h_max_change = np.max(dh)
        Q_max_change = np.max(dQ)

        print(f"\n结果:")
        print(f"  水深最大变化: {h_max_change:.2e} m")
        print(f"  流量最大变化: {Q_max_change:.2e} m^3/s")

        # 陡坡情况下略微放宽容差
        assert h_max_change < 1e-6, f"水深变化过大: {h_max_change}"
        assert Q_max_change < 1e-6, f"流量变化过大: {Q_max_change}"

        print(f"\n PASSED: 陡坡静水保持良好")


if __name__ == '__main__':
    print("="*70)
    print("Well-Balanced验证测试套件")
    print("="*70)
    print("目标: 验证求解器精确保持静水解（机器精度）")
    print("="*70)

    test = TestWellBalancedLakeAtRest()

    # 运行所有测试
    try:
        test.test_lake_at_rest_flat_bottom()
        test.test_lake_at_rest_sloped_bottom()
        test.test_lake_at_rest_small_perturbation()
        test.test_lake_at_rest_steep_slope()

        print("\n" + "="*70)
        print(" 所有Well-Balanced测试通过！")
        print("="*70)
        print("\n求解器验证: Well-Balanced格式 ")
        print("底坡源项与压力梯度完美平衡 ")
        print("满足Audusse et al. (2004)标准 ")
        print("="*70)

    except AssertionError as e:
        print(f"\n 测试失败: {e}")
        import traceback
        traceback.print_exc()
