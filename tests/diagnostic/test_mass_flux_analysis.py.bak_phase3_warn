#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
质量通量分析

目的：追踪边界处的质量流入流出，找出质量泄漏的位置

策略：
1. 手动计算边界通量
2. 与求解器内部通量对比
3. 检查是否有不一致
"""

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '../..'))

import numpy as np
try:
    from solvers.godunov_fvm_solver import GodunvFVMSolver
except ImportError as e:
    print(f"Import error: {e}")
    print("Make sure project root is in sys.path")
    sys.exit(1)



def analyze_mass_flux():
    """分析质量通量"""

    print("\n" + "="*80)
    print("质量通量分析")
    print("="*80)

    # 创建简单的急流问题
    B = 10.0
    L = 1000.0
    n_cells = 50
    dx = L / n_cells

    solver = GodunvFVMSolver(
        width=B,
        length=L,
        n_cells=n_cells,
        manning_n=0.0,  # 无摩阻，隔离边界效应
        slope=0.0,      # 水平床
        cfl=0.4,
        order=1         # 一阶格式
    )

    # 上游：急流
    h_up = 0.3
    Q_up = 10.0

    # 下游：缓流
    h_down = 2.0

    h_init = np.linspace(h_up, h_down, n_cells)
    Q_init = np.ones(n_cells) * Q_up

    bc_left = {'type': 'supercritical', 'h': h_up, 'Q': Q_up}
    bc_right = {'type': 'h', 'value': h_down}

    solver.initialize(h_init, Q_init, bc_left, bc_right)

    initial_mass = solver.initial_mass
    print(f"\n初始质量: {initial_mass:.2f} m^3")
    print(f"理论每步流入质量: Q * dt * B = {Q_up} * dt * 1 = {Q_up} * dt")

    # 推进10步，详细分析每步
    for step in range(10):
        # 记录推进前状态
        mass_before = solver._compute_total_mass()
        h_before = solver.h.copy()
        Q_before = solver.Q.copy()

        # 计算时间步
        dt = solver.compute_dt()

        # 推进一步
        solver.step()

        # 推进后状态
        mass_after = solver._compute_total_mass()
        h_after = solver.h.copy()
        Q_after = solver.Q.copy()

        # 计算质量变化
        dmass = mass_after - mass_before

        # 理论质量变化（考虑边界流入流出）
        # 左边界（流入）：F_left * dt = Q_up * dt
        # 右边界（流出）：F_right * dt = Q_out * dt
        # 其中 Q_out = u[-1] * h[-1] * B
        u_out = Q_after[-1] / (B * h_after[-1]) if h_after[-1] > 1e-10 else 0.0
        Q_out = u_out * h_after[-1] * B

        # 理论质量变化 = (流入 - 流出) * dt
        dmass_theory = (Q_up - Q_out) * dt

        # 误差
        dmass_error = dmass - dmass_theory

        print(f"\n步骤 {step+1}:")
        print(f"  dt = {dt:.6f} s")
        print(f"  质量变化: {dmass:.6f} m^3 (实际)")
        print(f"  理论质量变化: {dmass_theory:.6f} m^3 (Q_in - Q_out)*dt")
        print(f"  误差: {dmass_error:.6f} m^3 ({abs(dmass_error/dmass_theory*100):.2f}% of theory)")
        print(f"  流入: Q_up = {Q_up:.6f} m^3/s")
        print(f"  流出: Q_out = {Q_out:.6f} m^3/s")
        print(f"  边界值: h[0]={solver.h[0]:.6f}, Q[0]={solver.Q[0]:.6f}")

    # 最终质量守恒
    final_mass = solver._compute_total_mass()
    mass_error_pct = abs((final_mass - initial_mass) / initial_mass * 100)

    print(f"\n" + "="*80)
    print(f"总结 (10步后):")
    print(f"  初始质量: {initial_mass:.2f} m^3")
    print(f"  最终质量: {final_mass:.2f} m^3")
    print(f"  质量误差: {mass_error_pct:.6f}%")
    print("="*80)


if __name__ == "__main__":
    analyze_mass_flux()
