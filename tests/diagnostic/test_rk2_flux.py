#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
TVD-RK2两个阶段的通量检查

检查RK2的两个阶段是否使用了一致的通量
"""

import sys
import warnings
warnings.filterwarnings("ignore")
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '../..'))

import numpy as np
try:
    from solvers.godunov_fvm_solver import GodunvFVMSolver
except ImportError as e:
    print(f"Import error: {e}")
    print("Make sure project root is in sys.path")
    sys.exit(1)



def test_rk2_flux():
    """检查RK2两个阶段的通量"""

    print("\n" + "="*80)
    print("TVD-RK2通量一致性检查")
    print("="*80)

    # 创建求解器
    B = 5.0
    dx = 20.0

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
    h_n = np.ones(5)
    Q_n = np.ones(5) * 2.0
    bc_left = {'type': 'Q', 'value': 2.0}
    bc_right = {'type': 'h', 'value': 0.7}
    solver.initialize(h_n, Q_n, bc_left, bc_right)

    mass_n = np.sum(h_n) * dx * B
    print(f"\n初始质量 = {mass_n:.3f} m^3")

    # 第1步
    print(f"\n{'='*80}")
    print("RK2 第1步")
    print("="*80)

    dh_dt1, dQ_dt1 = solver._compute_rhs(h_n, Q_n)
    F1_left = solver.last_F_h[0]
    F1_right = solver.last_F_h[-1]
    net_flux1 = (F1_left - F1_right) * B

    print(f"  F_left = {F1_left:.3f} m^2/s")
    print(f"  F_right = {F1_right:.3f} m^2/s")
    print(f"  净通量 * B = {net_flux1:.3f} m^3/s")
    print(f"  Σ(dh_dt) * dx * B = {np.sum(dh_dt1) * dx * B:.3f} m^3/s")

    dt = solver.compute_dt()
    print(f"\n  时间步长 dt = {dt:.3f} s")

    h_star = h_n + dt * dh_dt1
    Q_star = Q_n + dt * dQ_dt1
    h_star = np.maximum(h_star, 0.0)

    mass_star = np.sum(h_star) * dx * B
    delta_mass1 = mass_star - mass_n
    delta_mass1_theory = dt * net_flux1

    print(f"\n  中间状态 h* 质量 = {mass_star:.3f} m^3")
    print(f"  质量变化（实际）= {delta_mass1:.3f} m^3")
    print(f"  质量变化（理论）= {delta_mass1_theory:.3f} m^3")
    print(f"  第1步守恒：{('' if abs(delta_mass1 - delta_mass1_theory) < 0.01 else '')}")

    # 第2步
    print(f"\n{'='*80}")
    print("RK2 第2步")
    print("="*80)

    dh_dt2, dQ_dt2 = solver._compute_rhs(h_star, Q_star)
    F2_left = solver.last_F_h[0]
    F2_right = solver.last_F_h[-1]
    net_flux2 = (F2_left - F2_right) * B

    print(f"  F_left = {F2_left:.3f} m^2/s")
    print(f"  F_right = {F2_right:.3f} m^2/s")
    print(f"  净通量 * B = {net_flux2:.3f} m^3/s")
    print(f"  Σ(dh_dt) * dx * B = {np.sum(dh_dt2) * dx * B:.3f} m^3/s")

    # 最终状态
    h_final = 0.5 * (h_n + h_star) + 0.5 * dt * dh_dt2
    Q_final = 0.5 * (Q_n + Q_star) + 0.5 * dt * dQ_dt2
    h_final = np.maximum(h_final, 0.0)

    mass_final = np.sum(h_final) * dx * B
    delta_mass_total = mass_final - mass_n
    delta_mass_total_theory = 0.5 * dt * (net_flux1 + net_flux2)

    print(f"\n{'='*80}")
    print("RK2 总体")
    print("="*80)
    print(f"  最终质量 = {mass_final:.3f} m^3")
    print(f"  总质量变化（实际）= {delta_mass_total:.3f} m^3")
    print(f"  总质量变化（理论）= {delta_mass_total_theory:.3f} m^3")
    print(f"  差异 = {abs(delta_mass_total - delta_mass_total_theory):.3f} m^3")

    error = abs(delta_mass_total - delta_mass_total_theory) / abs(delta_mass_total_theory) * 100

    print(f"\n{'='*80}")
    if error < 0.1:
        print(" TVD-RK2质量守恒成立")
    else:
        print(f" TVD-RK2质量守恒有问题（误差{error:.1f}%）")

    print("="*80)


if __name__ == "__main__":
    test_rk2_flux()
