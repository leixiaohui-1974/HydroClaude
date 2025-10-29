#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
短期质量守恒测试

快速验证Q边界强制是否有效
"""

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '../..'))

import numpy as np
from solvers.godunov_fvm_solver import GodunvFVMSolver


def test_short_mass():
    """短期质量守恒测试"""

    print("\n" + "="*80)
    print("短期质量守恒测试（100s）")
    print("="*80)

    # 参数
    B = 5.0
    Q_bc = 2.0
    h_bc = 0.7
    n_cells = 20

    solver = GodunvFVMSolver(
        width=B,
        length=1000.0,
        n_cells=n_cells,
        manning_n=0.03,
        slope=0.002,
        cfl=0.4,
        order=1,
        use_numba=False
    )

    # 初始化
    h_init = np.linspace(1.0, h_bc, n_cells)
    Q_init = np.ones(n_cells) * Q_bc

    bc_left = {'type': 'Q', 'value': Q_bc}
    bc_right = {'type': 'h', 'value': h_bc}

    solver.initialize(h_init, Q_init, bc_left, bc_right)

    print(f"\n配置：")
    print(f"  bc_left: Q = {Q_bc} m³/s")
    print(f"  bc_right: h = {h_bc} m")
    print(f"  初始质量 = {solver.initial_mass:.2f} m³")

    # 运行100s
    t_end = 100.0
    cumulative_inflow = 0.0
    cumulative_outflow = 0.0

    print(f"\n运行到 t={t_end}s...")
    print(f"\n{'时间(s)':<10} {'实际质量':<12} {'理论质量':<12} {'差异(%)':<10}")
    print("-" * 50)

    while solver.t < t_end:
        dt = solver.compute_dt()
        solver.step()

        # 累积通量
        if solver.last_F_h is not None:
            cumulative_inflow += solver.last_F_h[0] * dt
            cumulative_outflow += solver.last_F_h[-1] * dt

        # 每20s记录
        if int(solver.t) % 20 < dt or solver.t >= t_end:
            mass_actual = np.sum(solver.h * solver.dx * solver.B)
            mass_theory = solver.initial_mass + cumulative_inflow - cumulative_outflow
            error = abs(mass_actual - mass_theory) / abs(mass_theory) * 100

            print(f"{solver.t:<10.1f} {mass_actual:<12.2f} {mass_theory:<12.2f} {error:<10.2f}")

    # 最终分析
    mass_final = np.sum(solver.h * solver.dx * solver.B)
    mass_theory_final = solver.initial_mass + cumulative_inflow - cumulative_outflow
    mass_error = abs(mass_final - mass_theory_final) / abs(mass_theory_final) * 100

    print(f"\n{'='*80}")
    print("最终结果")
    print("="*80)
    print(f"  初始质量：{solver.initial_mass:.2f} m³")
    print(f"  实际质量：{mass_final:.2f} m³")
    print(f"  理论质量：{mass_theory_final:.2f} m³")
    print(f"  质量误差：{mass_error:.2f}%")

    print(f"\n边界通量检查：")
    if solver.last_F_h is not None:
        print(f"  F_h[0] = {solver.last_F_h[0]:.3f} m²/s (应该≈{Q_bc})")
        print(f"  F_h[-1] = {solver.last_F_h[-1]:.3f} m²/s")

        left_ok = abs(solver.last_F_h[0] - Q_bc) < 0.01
        print(f"\n  左边界强制：{'✓' if left_ok else '✗'}")

    print(f"\n{'='*80}")
    if mass_error < 1.0:
        print("✅ 质量守恒良好 (<1.0%)")
    else:
        print(f"❌ 质量守恒较差 ({mass_error:.2f}%)")

    print("="*80)


if __name__ == "__main__":
    test_short_mass()
