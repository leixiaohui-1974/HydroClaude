#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
打印ghost cells调试信息
"""

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '../..'))

import numpy as np
from solvers.godunov_fvm_solver import GodunvFVMSolver


# 重写_setup_ghost_cells添加调试信息
original_setup_ghost_cells = GodunvFVMSolver._setup_ghost_cells

def debug_setup_ghost_cells(self, h, Q):
    """带调试输出的_setup_ghost_cells"""
    h_ext, Q_ext = original_setup_ghost_cells(self, h, Q)

    # 只在前10步打印
    if self.t < 50.0:
        n = len(h)
        print(f"t={self.t:.2f}: h_bc={h_ext[n+1]:.6f}, Q_ghost={Q_ext[n+1]:.6f}, Q[n-1]={Q[n-1]:.6f}")

        # 检查是否进入临界分支
        B = self.B
        g = self.g
        h_bc = h_ext[n+1]

        if self.bc_left['type'] == 'Q':
            Q_left = self.bc_left['value'] if not callable(self.bc_left['value']) else self.bc_left['value'](self.t)
            h_c_from_Q = (Q_left**2 / (g * B**2))**(1/3)
            diff_ratio = abs(h_bc - h_c_from_Q) / h_c_from_Q

            print(f"  → Q_left={Q_left:.4f}, h_c_from_Q={h_c_from_Q:.6f}, diff_ratio={diff_ratio:.6f}")

            if diff_ratio < 0.1:
                print(f"  → 应该使用Q_left, 实际Q_ghost={Q_ext[n+1]:.6f}, 是否相等? {abs(Q_ext[n+1]-Q_left)<0.001}")

    return h_ext, Q_ext

# Monkey patch
GodunvFVMSolver._setup_ghost_cells = debug_setup_ghost_cells


def test():
    """测试"""
    print("\n" + "="*80)
    print("Ghost Cells调试 - 打印设置信息")
    print("="*80)

    B = 1.0
    n = 0.03
    S0 = 0.002
    L = 1000.0
    Q_bc = 2.0
    g = 9.81

    h_c = (Q_bc**2 / (g * B**2))**(1/3)

    print(f"\n参数：Q_left={Q_bc}, h_right={h_c:.6f}")

    solver = GodunvFVMSolver(
        width=B,
        length=L,
        n_cells=50,
        manning_n=n,
        slope=S0,
        cfl=0.4,
        order=1,
        use_numba=False
    )

    h_init = np.ones(50) * h_c * 1.5
    Q_init = np.ones(50) * Q_bc

    bc_left = {'type': 'Q', 'value': Q_bc}
    bc_right = {'type': 'h', 'value': h_c}

    solver.initialize(h_init, Q_init, bc_left, bc_right)

    print(f"\n前10步的ghost cells设置：\n")

    for i in range(10):
        solver.step()

    print("\n" + "="*80)


if __name__ == "__main__":
    test()
