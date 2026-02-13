#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
单步质量详细诊断

检查一个时间步内质量是如何变化的
"""

import sys
import warnings
warnings.filterwarnings("ignore")
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '../..'))

import numpy as np
import pytest
try:
    from solvers.godunov_fvm_solver import GodunvFVMSolver
except ImportError as e:
    pytest.skip(f"Required module not available: {e}", allow_module_level=True)



def test_single_step_mass():
    """单步质量诊断"""

    print("\n" + "="*80)
    print("单步质量详细诊断")
    print("="*80)

    # 简单配置
    B = 5.0
    Q_bc = 2.0
    h_bc = 0.7

    solver = GodunvFVMSolver(
        width=B,
        length=100.0,
        n_cells=5,
        manning_n=0.03,
        slope=0.002,
        cfl=0.4,
        order=1,
        use_numba=False
    )

    # 初始化
    h_init = np.ones(5) * 1.0
    Q_init = np.ones(5) * Q_bc

    bc_left = {'type': 'Q', 'value': Q_bc}
    bc_right = {'type': 'h', 'value': h_bc}

    solver.initialize(h_init, Q_init, bc_left, bc_right)

    dx = solver.dx

    print(f"\n配置：")
    print(f"  n_cells = 5, dx = {dx} m")
    print(f"  bc_left: Q = {Q_bc} m^3/s")
    print(f"  bc_right: h = {h_bc} m")

    # 步前状态
    mass_before = np.sum(solver.h * dx * B)
    print(f"\n步前质量 = {mass_before:.3f} m^3")
    print(f"  h = {solver.h}")

    # 计算时间步长
    dt = solver.compute_dt()
    print(f"\n时间步长 dt = {dt:.3f} s")

    # 执行一步
    solver.step()

    # 步后状态
    mass_after = np.sum(solver.h * dx * B)
    delta_mass = mass_after - mass_before

    print(f"\n步后质量 = {mass_after:.3f} m^3")
    print(f"  h = {solver.h}")
    print(f"\n质量变化 = {delta_mass:.3f} m^3")

    # 从通量计算理论质量变化
    if solver.last_F_h is not None:
        F_left = solver.last_F_h[0]
        F_right = solver.last_F_h[-1]
        net_flux = F_left - F_right
        delta_mass_theory = net_flux * dt * B

        print(f"\n边界通量：")
        print(f"  F_left = {F_left:.3f} m^2/s")
        print(f"  F_right = {F_right:.3f} m^2/s")
        print(f"  净通量 = {net_flux:.3f} m^2/s")
        print(f"\n理论质量变化 = {delta_mass_theory:.3f} m^3")

        # 比较
        error = abs(delta_mass - delta_mass_theory)
        error_percent = error / abs(delta_mass_theory) * 100 if abs(delta_mass_theory) > 1e-10 else 0.0

        print(f"\n{'='*80}")
        print(f"实际 vs 理论：")
        print(f"  实际质量变化：{delta_mass:.3f} m^3")
        print(f"  理论质量变化：{delta_mass_theory:.3f} m^3")
        print(f"  差异：{error:.3f} m^3 ({error_percent:.1f}%)")

        if error_percent < 1.0:
            print(f"\n 单步质量守恒良好")
        else:
            print(f"\n 单步质量守恒有问题")

            # 详细诊断
            print(f"\n详细诊断：")

            # 检查每个单元的质量变化
            print(f"\n单元级质量变化：")
            print(f"  {'单元':<6} {'h_before':<10} {'h_after':<10} {'Δh':<10} {'Δm (m^3)':<12}")
            print("-" * 60)

            h_before = h_init  # 注意：这只是第一步，之后需要保存
            for i in range(5):
                dh = solver.h[i] - h_before[i]
                dm = dh * dx * B
                print(f"  {i:<6} {h_before[i]:<10.3f} {solver.h[i]:<10.3f} {dh:<10.3f} {dm:<12.3f}")

            total_dm = np.sum((solver.h - h_before) * dx * B)
            print(f"\n  总计：{total_dm:.3f} m^3")

    print("\n" + "="*80)


if __name__ == "__main__":
    test_single_step_mass()
