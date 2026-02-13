#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
逐步通量诊断 - 精确求解器
Step-by-step flux diagnostics for Exact Riemann Solver

目标
1. 检查每个界面的通量计算
2. 对比HLL和Exact求解器
3. 找出质量累积的来源
"""

import numpy as np
import warnings
warnings.filterwarnings("ignore")
import sys
import pytest
import os
sys.path.insert(0, os.path.abspath('.'))

try:
    from solvers.godunov_fvm_solver import GodunvFVMSolver
except ImportError as e:
    pytest.skip(f"Required module not available: {e}", allow_module_level=True)


def single_step_flux_analysis():
    """
    单步通量详细分析
    """
    print("=" * 70)
    print("单步通量详细分析 - HLL vs Exact")
    print("=" * 70)

    # 简单的溃坝问题
    width = 10.0
    length = 100.0
    n_cells = 100
    dx = length / n_cells

    # 初始条件温和的溃坝
    h_init = np.zeros(n_cells)
    h_init[:25] = 2.0  # 左侧2m
    h_init[25:] = 1.0  # 右侧1m
    Q_init = np.zeros(n_cells)

    bc_left = {'type': 'h', 'value': 2.0}
    bc_right = {'type': 'h', 'value': 1.0}

    # 测试两种求解器
    for solver_type in ['hll', 'exact']:
        print(f"\n{'='*70}")
        print(f"求解器类型: {solver_type.upper()}")
        print("=" * 70)

        # 创建求解器
        solver = GodunvFVMSolver(
            width=width,
            length=length,
            n_cells=n_cells,
            manning_n=0.0,
            slope=0.0,
            cfl=0.3,
            order=1,  # 1阶避免重构影响
            riemann_solver=solver_type,
            use_numba=False  # 关闭Numba以便调试
        )

        solver.initialize(h_init.copy(), Q_init.copy(), bc_left, bc_right)

        # 初始质量
        mass_0 = np.sum(solver.h * solver.B * dx)
        print(f"\n初始质量: {mass_0:.6f} m^3")
        print(f"初始h范围: [{solver.h.min():.3f}, {solver.h.max():.3f}] m")

        # 执行单步
        dt = solver.compute_dt()
        print(f"\n时间步长: dt = {dt:.6f} s")
        print(f"CFL数: {solver.cfl}")

        # 手动计算通量避免TVD-RK2复杂性
        print(f"\n通量计算 (n={n_cells}个单元, n+1={n_cells+1}个界面):")
        print("-" * 70)

        # 扩展状态添加ghost cells
        h_ext, Q_ext = solver._extend_with_ghosts(solver.h, solver.Q)

        # 计算所有界面通量
        F_h_all = np.zeros(n_cells + 1)
        F_Q_all = np.zeros(n_cells + 1)

        # 重构1阶直接用单元值
        h_L = h_ext[:-1]
        h_R = h_ext[1:]
        Q_L = Q_ext[:-1]
        Q_R = Q_ext[1:]

        print(f"左状态h_L范围: [{h_L.min():.3f}, {h_L.max():.3f}]")
        print(f"右状态h_R范围: [{h_R.min():.3f}, {h_R.max():.3f}]")

        # 计算通量
        if solver_type == 'hll':
            from solvers.riemann_hll import hll_riemann_flux
            for i in range(n_cells + 1):
                F_h, F_Q = hll_riemann_flux(
                    h_L[i], Q_L[i], h_R[i], Q_R[i], solver.B, solver.g
                )
                F_h_all[i] = F_h
                F_Q_all[i] = F_Q
        else:  # exact
            from solvers.riemann_exact import exact_riemann_flux
            for i in range(n_cells + 1):
                F_h, F_Q = exact_riemann_flux(
                    h_L[i], Q_L[i], h_R[i], Q_R[i], solver.B, solver.g
                )
                F_h_all[i] = F_h
                F_Q_all[i] = F_Q

        print(f"\n通量F_h范围: [{F_h_all.min():.3f}, {F_h_all.max():.3f}] m^3/s")
        print(f"通量F_Q范围: [{F_Q_all.min():.3f}, {F_Q_all.max():.3f}] m/s^2")

        # 显示关键界面的通量
        print(f"\n关键界面通量:")
        print(f"{'界面':<6} {'左h(m)':<10} {'右h(m)':<10} {'F_h(m^3/s)':<15}")
        print("-" * 50)

        key_interfaces = [0, 1, 24, 25, 26, 49, 50]
        for i in key_interfaces:
            print(f"{i:<6} {h_L[i]:<10.3f} {h_R[i]:<10.3f} {F_h_all[i]:<15.6f}")

        # 更新状态
        dh_dt = -(F_h_all[1:] - F_h_all[:-1]) / dx
        h_new = solver.h + dt * dh_dt

        # 新质量
        mass_1 = np.sum(h_new * solver.B * dx)
        mass_error = abs(mass_1 - mass_0) / mass_0 * 100

        print(f"\n单步后质量: {mass_1:.6f} m^3")
        print(f"质量误差: {mass_error:.6f}%")
        print(f"h范围: [{h_new.min():.3f}, {h_new.max():.3f}] m")

        # 检查通量平衡
        total_flux_in = np.sum(np.maximum(F_h_all, 0) * dt)
        total_flux_out = np.sum(np.minimum(F_h_all, 0) * dt)

        print(f"\n通量平衡:")
        print(f"  流入总量: {total_flux_in:.6f} m^3")
        print(f"  流出总量: {total_flux_out:.6f} m^3")
        print(f"  净流量: {total_flux_in + total_flux_out:.6f} m^3")

        # 检查边界通量
        print(f"\n边界通量:")
        print(f"  左边界 (i=0):  F_h = {F_h_all[0]:.6f} m^3/s")
        print(f"  右边界 (i={n_cells}): F_h = {F_h_all[n_cells]:.6f} m^3/s")

        # 检查溃坝中心附近的通量
        print(f"\n溃坝界面附近 (i=24,25,26):")
        for i in [24, 25, 26]:
            print(f"  i={i}: h_L={h_L[i]:.3f}, h_R={h_R[i]:.3f}, F_h={F_h_all[i]:.6f}")

        # 状态判断
        if mass_error < 0.01:
            print(f"\n 质量守恒: {mass_error:.6f}% < 0.01%")
        elif mass_error < 1.0:
            print(f"\n  质量误差: {mass_error:.6f}%")
        else:
            print(f"\n 质量守恒失败: {mass_error:.6f}% > 1%")

def compare_fluxes_at_interface():
    """
    对比单个界面的HLL和Exact通量
    """
    print("\n" + "=" * 70)
    print("单界面通量对比 - HLL vs Exact")
    print("=" * 70)

    from solvers.riemann_hll import hll_riemann_flux
    from solvers.riemann_exact import exact_riemann_flux

    # 测试几种典型状态
    test_cases = [
        ("静水", 2.0, 0.0, 2.0, 0.0),
        ("小跳跃", 2.0, 0.0, 1.9, 0.0),
        ("中跳跃", 2.0, 0.0, 1.5, 0.0),
        ("溃坝", 2.0, 0.0, 1.0, 0.0),
        ("有流速", 2.0, 10.0, 1.0, 5.0),
    ]

    B = 10.0
    g = 9.81

    print(f"\n{'案例':<10} {'h_L':<8} {'Q_L':<8} {'h_R':<8} {'Q_R':<8} {'HLL F_h':<12} {'Exact F_h':<12} {'差异%':<10}")
    print("-" * 90)

    for name, h_L, Q_L, h_R, Q_R in test_cases:
        F_h_hll, _ = hll_riemann_flux(h_L, Q_L, h_R, Q_R, B, g)
        F_h_exact, _ = exact_riemann_flux(h_L, Q_L, h_R, Q_R, B, g)

        if abs(F_h_hll) > 1e-10:
            diff_pct = abs(F_h_exact - F_h_hll) / abs(F_h_hll) * 100
        else:
            diff_pct = 0.0 if abs(F_h_exact) < 1e-10 else 999.9

        print(f"{name:<10} {h_L:<8.2f} {Q_L:<8.2f} {h_R:<8.2f} {Q_R:<8.2f} {F_h_hll:<12.6f} {F_h_exact:<12.6f} {diff_pct:<10.2f}")

if __name__ == "__main__":
    # 单步通量详细分析
    single_step_flux_analysis()

    # 单界面通量对比
    compare_fluxes_at_interface()

    print("\n" + "=" * 70)
    print("诊断完成")
    print("=" * 70)
