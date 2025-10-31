#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
RP2改进测试 - 尝试更低CFL和更长域
"""

import sys
import os
sys.path.insert(0, os.path.dirname(__file__))

import numpy as np
from solvers.godunov_fvm_weno3 import GodunvFVMWENO3
from tests.verification.toro_riemann_solver import exact_riemann_solution

# RP2参数 - 增大计算域
h_L = 5.0
u_L = 5.0
h_R = 5.0
u_R = -5.0
L = 200.0  # 增大到200m
n_cells = 1000  # 增加网格密度
x_dam = L / 2.0
B = 10.0
t_end = 0.5

print("="*70)
print("RP2改进测试 - 更低CFL + 更长域")
print("="*70)

for cfl in [0.1, 0.05]:
    print(f"\n{'='*70}")
    print(f"测试CFL = {cfl}")
    print(f"{'='*70}")

    solver = GodunvFVMWENO3(
        width=B,
        length=L,
        n_cells=n_cells,
        manning_n=0.0,
        slope=0.0,
        use_enhanced_bc=True,
        well_balanced=False,
        cfl=cfl,
        use_numba=True
    )

    # 初始条件
    x = solver.x
    h_init = np.where(x <= x_dam, h_L, h_R)
    Q_init = B * np.where(x <= x_dam, h_L * u_L, h_R * u_R)

    bc_left = {'type': 'transmissive'}
    bc_right = {'type': 'transmissive'}

    solver.initialize(h_init, Q_init, bc_left, bc_right)

    # 运行模拟
    print(f"运行至t={t_end}s...")
    step_count = 0
    while solver.t < t_end and step_count < 500:
        solver.step()
        step_count += 1

        if np.any(np.isnan(solver.h)) or np.any(np.isnan(solver.Q)):
            print(f"❌ 数值爆炸在步{step_count}")
            break

    print(f"完成: {solver.step_count}步, t={solver.t:.3f}s")

    # 计算精确解
    h_exact, u_exact = exact_riemann_solution(
        solver.x, solver.t, h_L, u_L, h_R, u_R, x_dam
    )

    # 数值解
    h_num = solver.h
    u_num = solver.Q / (solver.B * np.maximum(solver.h, solver.eps_dry))

    # 误差
    h_L2 = np.sqrt(np.mean((h_num - h_exact)**2))
    h_L2_rel = h_L2 / h_L * 100

    print(f"数值解: h=[{h_num.min():.3f}, {h_num.max():.3f}]")
    print(f"精确解: h=[{h_exact.min():.3f}, {h_exact.max():.3f}]")
    print(f"L2误差: {h_L2:.4f}m ({h_L2_rel:.2f}%)")
    print(f"最大水深误差: {h_num.max() - h_exact.max():.3f}m")
