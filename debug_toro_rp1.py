#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
诊断Toro RP1测试卡住的问题
"""

import sys
import os
sys.path.insert(0, os.path.dirname(__file__))

import numpy as np
from solvers.godunov_fvm_weno3 import GodunvFVMWENO3

# RP1参数
h_L = 10.0
u_L = 0.0
h_R = 5.0
u_R = 0.0
L = 100.0
n_cells = 500
x_dam = L / 2.0
B = 10.0

print("="*70)
print("Toro RP1诊断")
print("="*70)
print(f"\n初始条件:")
print(f"  左侧: h_L = {h_L} m, u_L = {u_L} m/s")
print(f"  右侧: h_R = {h_R} m, u_R = {u_R} m/s")
print(f"  域: [0, {L}] m, {n_cells} cells")

# 创建求解器（使用更低的CFL）
cfl = 0.2
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

print(f"\n求解器配置:")
print(f"  CFL: {cfl}")
print(f"  dx: {solver.dx} m")
print(f"  初始水深范围: [{solver.h.min():.3f}, {solver.h.max():.3f}] m")
print(f"  初始流量范围: [{solver.Q.min():.3f}, {solver.Q.max():.3f}] m³/s")

print(f"\n开始模拟 (最多100步)...")
t_target = 0.5

for i in range(100):
    dt_before = solver.compute_dt()
    solver.step()

    if i % 10 == 0 or solver.t > 0.2:
        h_range = [solver.h.min(), solver.h.max()]
        Q_range = [solver.Q.min(), solver.Q.max()]
        u = solver.Q / (solver.B * np.maximum(solver.h, solver.eps_dry))
        u_range = [u.min(), u.max()]

        print(f"\n步{i+1}:")
        print(f"  时间: {solver.t:.6f} s")
        print(f"  dt: {dt_before:.6e} s")
        print(f"  h: [{h_range[0]:.6f}, {h_range[1]:.6f}] m")
        print(f"  Q: [{Q_range[0]:.6f}, {Q_range[1]:.6f}] m³/s")
        print(f"  u: [{u_range[0]:.6f}, {u_range[1]:.6f}] m/s")

        # 检查数值爆炸
        if np.any(np.isnan(solver.h)) or np.any(np.isnan(solver.Q)):
            print(f"\n 数值爆炸！")
            break

        # 检查dt崩溃
        if dt_before < 1e-8:
            print(f"\n️  dt崩溃到{dt_before:.3e}s!")
            print(f"   最大波速: {np.max(np.abs(u) + np.sqrt(solver.g * solver.h)):.6e} m/s")
            break

    if solver.t >= t_target:
        print(f"\n 达到目标时间 {t_target}s")
        break

print(f"\n最终状态:")
print(f"  总步数: {solver.step_count}")
print(f"  最终时间: {solver.t:.6f} s")
print(f"  h范围: [{solver.h.min():.3f}, {solver.h.max():.3f}] m")
