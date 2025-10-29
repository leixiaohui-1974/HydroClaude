#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Ghost Cells调试测试 - 检查修复后的h边界条件
"""

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '../..'))

import numpy as np
from solvers.godunov_fvm_solver import GodunvFVMSolver


def test_ghost_cells_debug():
    """调试ghost cells设置"""

    print("\n" + "="*80)
    print("Ghost Cells调试 - h边界条件修复验证")
    print("="*80)

    # MacDonald Test 2参数
    B = 1.0
    n = 0.03
    S0 = 0.002
    L = 5000.0
    Q_bc = 2.0
    g = 9.81

    # 临界水深
    h_c = (Q_bc**2 / (g * B**2))**(1/3)

    print(f"\n参数：")
    print(f"  Q_left = {Q_bc} m³/s")
    print(f"  h_right = {h_c:.6f} m (临界水深)")
    print(f"  h_c从Q计算 = {h_c:.6f} m")
    print(f"  差异 = {abs(h_c - h_c):.6f} m (应该为0)")

    # 创建求解器
    n_cells = 100
    solver = GodunvFVMSolver(
        width=B,
        length=L,
        n_cells=n_cells,
        manning_n=n,
        slope=S0,
        cfl=0.5,
        order=2,
        use_numba=True
    )

    # 初始化
    h_init = np.ones(n_cells) * h_c * 1.5
    Q_init = np.ones(n_cells) * Q_bc

    bc_left = {'type': 'Q', 'value': Q_bc}
    bc_right = {'type': 'h', 'value': h_c}

    solver.initialize(h_init, Q_init, bc_left, bc_right)

    print(f"\n初始状态：")
    print(f"  h[-1] = {solver.h[-1]:.6f} m")
    print(f"  Q[-1] = {solver.Q[-1]:.6f} m³/s")

    # 运行几步，观察ghost cells
    print(f"\n运行10步，观察ghost cells设置：")
    print(f"{'步数':<6} {'h[-1]':<12} {'Q[-1]':<12} {'Q_ghost':<12} {'Fr[-1]':<12} {'流入/流出':<12}")
    print("-" * 80)

    for i in range(10):
        # 保存旧的Q
        Q_old = solver.Q[-1]

        # Step
        solver.step()

        # 获取ghost cells (需要手动调用_setup_ghost_cells)
        h_ghost, Q_ghost = solver._setup_ghost_cells(solver.h, solver.Q)

        # 计算Froude数
        if solver.h[-1] > solver.eps_dry:
            u = solver.Q[-1] / (solver.h[-1] * B)
            Fr = abs(u) / np.sqrt(g * solver.h[-1])
        else:
            Fr = 0.0

        # 流入流出
        F_left = solver.last_F_h[0] if solver.last_F_h is not None else 0.0
        F_right = solver.last_F_h[-1] if solver.last_F_h is not None else 0.0

        print(f"{i:<6} {solver.h[-1]:<12.6f} {solver.Q[-1]:<12.6f} {Q_ghost[-1]:<12.6f} {Fr:<12.4f} {F_left:.4f}/{F_right:.4f}")

    # 运行到稳态
    print(f"\n继续运行到 t=3000s...")
    while solver.t < 3000.0:
        solver.step()

    # 最终分析
    mass_final = np.sum(solver.h * solver.dx * B)
    mass_initial = solver.initial_mass

    print(f"\n最终状态：")
    print(f"  t = {solver.t:.2f} s")
    print(f"  h[-1] = {solver.h[-1]:.6f} m")
    print(f"  Q[-1] = {solver.Q[-1]:.6f} m³/s")

    if solver.h[-1] > solver.eps_dry:
        u = solver.Q[-1] / (solver.h[-1] * B)
        Fr = abs(u) / np.sqrt(g * solver.h[-1])
        print(f"  Fr[-1] = {Fr:.6f}")

    # 计算理论临界流量
    Q_critical_theory = B * np.sqrt(g * h_c**3)
    print(f"\n临界流量对比：")
    print(f"  理论临界流量 = {Q_critical_theory:.6f} m³/s")
    print(f"  实际边界流量 = {solver.Q[-1]:.6f} m³/s")
    print(f"  左边界流量 = {Q_bc:.6f} m³/s")

    # 质量守恒
    mass_error_pct = abs(mass_final - mass_initial) / mass_initial * 100
    print(f"\n质量守恒：")
    print(f"  初始质量 = {mass_initial:.4f} m³")
    print(f"  最终质量 = {mass_final:.4f} m³")
    print(f"  质量误差 = {mass_error_pct:.2f}%")

    # 判断
    if mass_error_pct < 5.0:
        print(f"\n✅ 修复成功！质量守恒良好")
    else:
        print(f"\n❌ 修复未生效，质量误差仍然很大")

        # 检查ghost cells逻辑
        h_c_from_Q = (Q_bc**2 / (g * B**2))**(1/3)
        diff_ratio = abs(h_c - h_c_from_Q) / h_c_from_Q

        print(f"\n调试信息：")
        print(f"  h_bc = {h_c:.6f} m")
        print(f"  h_c_from_Q = {h_c_from_Q:.6f} m")
        print(f"  差异比 = {diff_ratio:.6f} (容差=0.1)")

        if diff_ratio < 0.1:
            print(f"  → 应该进入'使用左边界流量'分支")
            print(f"  → Q_ghost应该= {Q_bc:.6f} m³/s")
        else:
            print(f"  → 不满足条件，使用外推")

    print("\n" + "="*80)


if __name__ == "__main__":
    test_ghost_cells_debug()
