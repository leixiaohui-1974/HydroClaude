#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Ghost Cells和边界通量诊断

检查ghost cells设置和边界通量计算是否正确
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



def test_ghost_cells():
    """测试ghost cells设置"""

    print("\n" + "="*80)
    print("Ghost Cells和边界通量诊断")
    print("="*80)

    # 简单配置
    B = 5.0
    Q_bc = 2.0
    h_bc = 0.7
    n_cells = 10

    solver = GodunvFVMSolver(
        width=B,
        length=500.0,
        n_cells=n_cells,
        manning_n=0.03,
        slope=0.002,
        cfl=0.4,
        order=1,
        use_numba=False  # 使用Python路径便于调试
    )

    # 初始化
    h_init = np.linspace(1.0, h_bc, n_cells)
    Q_init = np.ones(n_cells) * Q_bc

    bc_left = {'type': 'Q', 'value': Q_bc}
    bc_right = {'type': 'h', 'value': h_bc}

    solver.initialize(h_init, Q_init, bc_left, bc_right)

    print(f"\n配置：")
    print(f"  n_cells = {n_cells}")
    print(f"  bc_left = {bc_left}")
    print(f"  bc_right = {bc_right}")

    # 运行几步
    for step in range(5):
        print(f"\n{'-'*80}")
        print(f"步骤 {step+1}")
        print("-"*80)

        # 在step之前，手动调用_extend_with_ghosts看看ghost cells
        h_ext, Q_ext = solver._extend_with_ghosts(solver.h, solver.Q)

        print(f"\nGhost cells（扩展后的数组）：")
        print(f"  h_ext: [ghost_L] + [内部] + [ghost_R]")
        print(f"         [{h_ext[0]:.3f}] + [{h_ext[1]:.3f}...{h_ext[-2]:.3f}] + [{h_ext[-1]:.3f}]")
        print(f"  Q_ext: [ghost_L] + [内部] + [ghost_R]")
        print(f"         [{Q_ext[0]:.3f}] + [{Q_ext[1]:.3f}...{Q_ext[-2]:.3f}] + [{Q_ext[-1]:.3f}]")

        print(f"\n边界单元（内部数组）：")
        print(f"  h[0] = {solver.h[0]:.3f}, h[-1] = {solver.h[-1]:.3f}")
        print(f"  Q[0] = {solver.Q[0]:.3f}, Q[-1] = {solver.Q[-1]:.3f}")

        # 执行一步
        dt = solver.compute_dt()
        solver.step()

        # 检查通量
        if solver.last_F_h is not None:
            print(f"\n界面通量（step后）：")
            print(f"  F_h[0] (左边界) = {solver.last_F_h[0]:.3f} m^2/s")
            print(f"  F_h[-1] (右边界) = {solver.last_F_h[-1]:.3f} m^2/s")

            print(f"\n通量检查：")
            print(f"  左边界：F_h[0]应该~=Q_bc={Q_bc:.3f} -> 实际={solver.last_F_h[0]:.3f} -> {'' if abs(solver.last_F_h[0]-Q_bc)<0.01 else ''}")
            print(f"  右边界：F_h[-1]应该~=Q[-1]={solver.Q[-1]:.3f} -> 实际={solver.last_F_h[-1]:.3f} -> {'' if abs(solver.last_F_h[-1]-solver.Q[-1])<0.01 else ''}")

        print(f"\n质量变化：")
        mass_before = solver.initial_mass if step == 0 else mass_current
        mass_current = np.sum(solver.h * solver.dx * solver.B)
        delta_mass = mass_current - mass_before
        print(f"  质量 = {mass_current:.2f} m^3 (变化={delta_mass:+.2f} m^3)")

    print(f"\n{'='*80}")
    print("诊断总结")
    print("="*80)

    if solver.last_F_h is not None:
        left_ok = abs(solver.last_F_h[0] - Q_bc) < 0.01
        right_Q = solver.Q[-1]
        right_ok = abs(solver.last_F_h[-1] - right_Q) < 0.1  # 允许10%误差

        if left_ok and right_ok:
            print("\n 边界通量设置正确")
        else:
            print("\n 边界通量有问题")
            if not left_ok:
                print(f"   左边界：F_h[0]={solver.last_F_h[0]:.3f} ≠ Q_bc={Q_bc:.3f}")
            if not right_ok:
                print(f"   右边界：F_h[-1]={solver.last_F_h[-1]:.3f} ≠ Q[-1]={right_Q:.3f}")


if __name__ == "__main__":
    test_ghost_cells()
