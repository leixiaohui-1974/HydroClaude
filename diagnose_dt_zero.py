#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
诊断：为什么在35秒dt变成0

日期: 2025-10-29
"""

import sys
import os
sys.path.insert(0, os.path.dirname(__file__))

import json
import tempfile
from pathlib import Path
import numpy as np
from solvers.godunov_fvm_weno3 import GodunvFVMWENO3

# Test 4参数
L = 1000.0
B = 10.0
S0 = 0.0
n = 0.0  # 无摩阻
h_upstream = 0.7
Q = 20.0
h_downstream = 2.8
n_cells = 200
g = 9.81

# 线性初始条件
h_init = np.linspace(h_upstream, h_downstream, n_cells)
Q_init = np.ones(n_cells) * Q

# 创建WENO3求解器（参数完全一致）
solver = GodunvFVMWENO3(
    width=B,
    length=L,
    n_cells=n_cells,
    manning_n=n,  # 注意：manning_n=0
    slope=S0,
    g=g,
    cfl=0.4,
    eps_dry=1e-6,
    weno_epsilon=1e-6,
    riemann_solver='hll',
    use_numba=True,
    dt_max=0.5
)

bc_left = {
    'type': 'supercritical',
    'h': h_upstream,
    'Q': Q
}
bc_right = {
    'type': 'fixed_h',
    'h': h_downstream
}

solver.initialize(h_init, Q_init, bc_left, bc_right)

print("="*70)
print("诊断：为什么在35秒dt变成0")
print("="*70)
print(f"关键参数: manning_n={n} (无摩阻), dt_max={solver.dt_max}")
print()

# 运行到40秒，监控35秒附近
t_target = 40.0
step = 0
last_report = 0.0

while solver.t < t_target and step < 100000:
    # 计算dt
    dt = solver.compute_dt()

    # 检查状态
    if solver.t >= 30.0 and solver.t < 40.0:
        # 详细监控30-40秒区间
        if solver.t - last_report >= 0.5:
            h_safe = np.maximum(solver.h, solver.eps_dry)
            A = h_safe * solver.B
            u = solver.Q / A
            c = np.sqrt(solver.g * h_safe)
            lambda_max = np.max(np.abs(u) + c)

            print(f"t={solver.t:6.2f}s: dt={dt:.6f}, lambda_max={lambda_max:.6f}, "
                  f"h_range=[{np.min(solver.h):.4f}, {np.max(solver.h):.4f}]")

            last_report = solver.t

    # 检测异常
    if dt < 1e-6:
        print(f"\n dt变得极小！")
        print(f"  t={solver.t:.4f}s, step={step}")
        print(f"  dt={dt:.10f}")

        h_safe = np.maximum(solver.h, solver.eps_dry)
        A = h_safe * solver.B
        u = solver.Q / A
        c = np.sqrt(solver.g * h_safe)
        speeds = np.abs(u) + c
        lambda_max = np.max(speeds)

        print(f"\n状态诊断:")
        print(f"  h: min={np.min(solver.h):.6f}, max={np.max(solver.h):.6f}")
        print(f"  Q: min={np.min(solver.Q):.6f}, max={np.max(solver.Q):.6f}")
        print(f"  u: min={np.min(u):.6f}, max={np.max(u):.6f}")
        print(f"  c: min={np.min(c):.6f}, max={np.max(c):.6f}")
        print(f"  lambda_max={lambda_max:.6f}")

        # 检查NaN/Inf
        if np.any(np.isnan(solver.h)) or np.any(np.isinf(solver.h)):
            print(f"  ️  h中包含NaN或Inf！")
        if np.any(np.isnan(solver.Q)) or np.any(np.isinf(solver.Q)):
            print(f"  ️  Q中包含NaN或Inf！")

        # CFL计算
        cfl_dt = solver.cfl * solver.dx / lambda_max if lambda_max > 1e-10 else 1.0
        print(f"\nCFL分析:")
        print(f"  CFL*dx/lambda_max = {cfl_dt:.6f}")
        print(f"  dt_max = {solver.dt_max}")
        print(f"  min(cfl_dt, dt_max) = {min(cfl_dt, solver.dt_max):.6f}")
        print(f"  实际dt = {dt:.6f}")

        break

    # 执行步进
    solver.step(dt)
    step += 1

print(f"\n最终:")
print(f"  总步数: {step}")
print(f"  模拟时间: {solver.t:.2f}s")
print("="*70)
