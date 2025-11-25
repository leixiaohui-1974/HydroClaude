#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Ghost Cell 一致性测试

检查ghost cell的设置是否与Riemann求解器的通量计算一致
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



def test_ghost_cell_consistency():
    """测试ghost cell一致性"""

    print("\n" + "="*80)
    print("Ghost Cell 一致性测试")
    print("="*80)

    B = 10.0
    g = 9.81

    # 创建求解器
    solver = GodunvFVMSolver(
        width=B,
        length=100.0,
        n_cells=5,
        manning_n=0.0,
        slope=0.0,
        cfl=0.4,
        order=1
    )

    # 设置边界条件
    h_bc = 0.3
    Q_bc = 10.0

    h = np.array([h_bc, 0.5, 0.8, 1.5, 2.0])
    Q = np.array([Q_bc, Q_bc, Q_bc, Q_bc, Q_bc])

    bc_left = {'type': 'supercritical', 'h': h_bc, 'Q': Q_bc}
    bc_right = {'type': 'h', 'value': 2.0}

    solver.initialize(h, Q, bc_left, bc_right)

    # 扩展ghost cells
    h_ext, Q_ext = solver._extend_with_ghosts(h, Q)

    print(f"\n边界条件:")
    print(f"  左边界: supercritical, h={h_bc}, Q={Q_bc}")
    print(f"  右边界: h=2.0")

    print(f"\n扩展后的数组 (包含ghost cells):")
    print(f"  h_ext: {h_ext}")
    print(f"  Q_ext: {Q_ext}")

    print(f"\nGhost cell和边界单元对比:")
    print(f"  Ghost cell (左):  h_ext[0] = {h_ext[0]:.4f}, Q_ext[0] = {Q_ext[0]:.4f}")
    print(f"  边界单元 (单元0): h_ext[1] = {h_ext[1]:.4f}, Q_ext[1] = {Q_ext[1]:.4f}")
    print(f"  差异: Δh = {abs(h_ext[1]-h_ext[0]):.6f}, ΔQ = {abs(Q_ext[1]-Q_ext[0]):.6f}")

    # 手动计算界面0的通量（ghost和单元0之间）
    h_L = h_ext[0]  # ghost cell
    h_R = h_ext[1]  # 单元0
    Q_L = Q_ext[0]
    Q_R = Q_ext[1]

    print(f"\n手动计算界面0通量 (HLL):")
    print(f"  左状态 (ghost):  h_L={h_L:.4f}, Q_L={Q_L:.4f}")
    print(f"  右状态 (单元0): h_R={h_R:.4f}, Q_R={Q_R:.4f}")

    # 计算通量
    F_h, F_Q = solver._hll_flux(h_L, Q_L, h_R, Q_R)

    print(f"  计算得到的通量: F_h={F_h:.6f} m^3/s")
    print(f"  理论边界通量:   F_h_theory={Q_bc:.6f} m^3/s")
    print(f"  误差: {abs(F_h - Q_bc):.6f} m^3/s ({abs(F_h-Q_bc)/Q_bc*100:.2f}%)")

    # 如果状态完全相同，通量应该等于Q
    if abs(h_L - h_R) < 1e-10 and abs(Q_L - Q_R) < 1e-10:
        print(f"\n Ghost cell和边界单元状态相同，HLL通量应该=Q_bc")
        if abs(F_h - Q_bc) < 1e-6:
            print(f" 通量计算正确")
        else:
            print(f" 通量计算有误！")
    else:
        print(f"\n Ghost cell和边界单元状态不同，这会导致边界通量不等于Q_bc")
        print(f"  这是质量泄漏的根源！")

    # 计算界面1的通量（单元0和单元1之间）
    h_L = h_ext[1]  # 单元0
    h_R = h_ext[2]  # 单元1
    Q_L = Q_ext[1]
    Q_R = Q_ext[2]

    F_h_1, F_Q_1 = solver._hll_flux(h_L, Q_L, h_R, Q_R)

    print(f"\n界面1通量 (单元0和单元1之间):")
    print(f"  左状态 (单元0): h_L={h_L:.4f}, Q_L={Q_L:.4f}")
    print(f"  右状态 (单元1): h_R={h_R:.4f}, Q_R={Q_R:.4f}")
    print(f"  计算得到的通量: F_h={F_h_1:.6f} m^3/s")

    print(f"\n单元0的质量平衡:")
    print(f"  流入 (界面0): F_in  = {F_h:.6f} m^3/s")
    print(f"  流出 (界面1): F_out = {F_h_1:.6f} m^3/s")
    print(f"  净流入:         ΔF   = {F_h - F_h_1:.6f} m^3/s")

    if abs(F_h - F_h_1) > 1e-6:
        dx = 100.0 / 5
        dh_dt = -(F_h_1 - F_h) / dx
        print(f"  -> 单元0水深变化率: dh/dt = {dh_dt:.6f} m/s")
        print(f"  -> 但边界条件强制 h[0]=0.3，这个变化被\"删除\"")
        print(f"  -> 质量泄漏 = {dh_dt * B * dx:.6f} m^3/s")

    print("\n" + "="*80)


if __name__ == "__main__":
    test_ghost_cell_consistency()
