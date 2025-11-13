#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
诊断Toro RP2测试问题（双稀疏波）
"""

import sys
import os
sys.path.insert(0, os.path.dirname(__file__))

import numpy as np
from solvers.godunov_fvm_weno3 import GodunvFVMWENO3
from tests.verification.toro_riemann_solver import exact_riemann_solution, riemann_structure

# RP2参数
h_L = 5.0
u_L = 5.0  # 非零流速！
h_R = 5.0
u_R = -5.0  # 负流速！
L = 100.0
n_cells = 500
x_dam = L / 2.0
B = 10.0
t_end = 0.5

print("="*70)
print("Toro RP2诊断 - 双稀疏波")
print("="*70)
print(f"\n初始条件:")
print(f"  左侧: h_L = {h_L} m, u_L = {u_L} m/s")
print(f"  右侧: h_R = {h_R} m, u_R = {u_R} m/s")
print(f"  域: [0, {L}] m, {n_cells} cells")

# 波结构分析
structure = riemann_structure(h_L, u_L, h_R, u_R)
print(f"\n精确解波结构:")
print(f"  中间状态: h* = {structure['h_star']:.4f} m, u* = {structure['u_star']:.4f} m/s")
print(f"  左波: {structure['wave_type_L']}")
print(f"  右波: {structure['wave_type_R']}")

# 创建求解器
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

# 初始条件 - 注意：需要从流速转换为流量！
x = solver.x
h_init = np.where(x <= x_dam, h_L, h_R)
# Q = B * h * u
Q_init = B * np.where(x <= x_dam, h_L * u_L, h_R * u_R)

print(f"\n初始条件检查:")
print(f"  h_init范围: [{h_init.min():.3f}, {h_init.max():.3f}] m")
print(f"  Q_init范围: [{Q_init.min():.3f}, {Q_init.max():.3f}] m³/s")
print(f"  左侧Q = B*h*u = {B}*{h_L}*{u_L} = {B*h_L*u_L} m³/s")
print(f"  右侧Q = B*h*u = {B}*{h_R}*{u_R} = {B*h_R*u_R} m³/s")

bc_left = {'type': 'transmissive'}
bc_right = {'type': 'transmissive'}

solver.initialize(h_init, Q_init, bc_left, bc_right)

print(f"\n求解器配置:")
print(f"  CFL: {cfl}")
print(f"  初始水深: [{solver.h.min():.3f}, {solver.h.max():.3f}] m")
print(f"  初始流量: [{solver.Q.min():.3f}, {solver.Q.max():.3f}] m³/s")

# 运行模拟
print(f"\n开始模拟至t={t_end}s...")
step_count = 0
while solver.t < t_end and step_count < 200:
    solver.step()
    step_count += 1

    if step_count % 20 == 0:
        h_range = [solver.h.min(), solver.h.max()]
        Q_range = [solver.Q.min(), solver.Q.max()]
        u = solver.Q / (solver.B * np.maximum(solver.h, solver.eps_dry))
        u_range = [u.min(), u.max()]

        print(f"  步{step_count}: t={solver.t:.3f}s, h=[{h_range[0]:.3f}, {h_range[1]:.3f}], u=[{u_range[0]:.3f}, {u_range[1]:.3f}]")

    if np.any(np.isnan(solver.h)) or np.any(np.isnan(solver.Q)):
        print(f"\n 数值爆炸！")
        break

print(f"\n 模拟完成:")
print(f"  总步数: {solver.step_count}")
print(f"  最终时间: {solver.t:.6f} s")

# 计算精确解
x_exact = solver.x
h_exact, u_exact = exact_riemann_solution(
    x_exact, solver.t, h_L, u_L, h_R, u_R, x_dam
)

# 数值解
h_num = solver.h
u_num = solver.Q / (solver.B * np.maximum(solver.h, solver.eps_dry))

# 误差
h_L2 = np.sqrt(np.mean((h_num - h_exact)**2))
h_scale = max(h_L, h_R)
h_L2_rel = h_L2 / h_scale * 100

u_L2 = np.sqrt(np.mean((u_num - u_exact)**2))

print(f"\n误差分析:")
print(f"  水深L2: {h_L2:.6f} m ({h_L2_rel:.2f}%)")
print(f"  流速L2: {u_L2:.6f} m/s")
print(f"  验收标准: < 8%")
print(f"  状态: {' 通过' if h_L2_rel < 8.0 else ' 失败'}")

# 检查数值解的范围
print(f"\n数值解范围:")
print(f"  h: [{h_num.min():.3f}, {h_num.max():.3f}] m")
print(f"  u: [{u_num.min():.3f}, {u_num.max():.3f}] m/s")

print(f"\n精确解范围:")
print(f"  h: [{h_exact.min():.3f}, {h_exact.max():.3f}] m")
print(f"  u: [{u_exact.min():.3f}, {u_exact.max():.3f}] m/s")
