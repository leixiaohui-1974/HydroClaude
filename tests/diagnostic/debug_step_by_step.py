#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
单步调试：在35秒前后详细追踪每一步

找出dt为什么变成0
日期: 2025-10-29
"""

import sys
import os
sys.path.insert(0, os.path.dirname(__file__))

import numpy as np
from solvers.godunov_fvm_weno3 import GodunvFVMWENO3

# Test 4参数
L = 1000.0
B = 10.0
S0 = 0.0
n = 0.0  # 关键：无摩阻
h_upstream = 0.7
Q = 20.0
h_downstream = 2.8
n_cells = 200
g = 9.81

# 线性初始条件
h_init = np.linspace(h_upstream, h_downstream, n_cells)
Q_init = np.ones(n_cells) * Q

solver = GodunvFVMWENO3(
    width=B,
    length=L,
    n_cells=n_cells,
    manning_n=n,
    slope=S0,
    g=g,
    cfl=0.4,
    eps_dry=1e-6,
    weno_epsilon=1e-6,
    riemann_solver='hll',
    use_numba=True,
    dt_max=0.5
)

bc_left = {'type': 'supercritical', 'h': h_upstream, 'Q': Q}
bc_right = {'type': 'fixed_h', 'h': h_downstream}

solver.initialize(h_init, Q_init, bc_left, bc_right)

print("="*70)
print("单步调试：35秒前后的详细状态")
print("="*70)

# 运行到34秒
print("阶段1: 快速运行到34秒...")
while solver.t < 34.0:
    solver.step()

print(f"  已到达 t={solver.t:.2f}s")

# 从34秒开始，详细记录每一步
print("\n阶段2: 从34秒开始单步调试...")
step_count = 0
target_t = 37.0

while solver.t < target_t and step_count < 100:
    # 保存状态
    t_before = solver.t
    h_before = solver.h.copy()
    Q_before = solver.Q.copy()

    # 计算dt
    dt_computed = solver.compute_dt()

    # 执行步进
    solver.step(dt_computed)

    # 检查变化
    t_after = solver.t
    h_after = solver.h.copy()
    Q_after = solver.Q.copy()

    dt_actual = t_after - t_before
    h_change = np.max(np.abs(h_after - h_before))
    Q_change = np.max(np.abs(Q_after - Q_before))

    # 计算lambda_max用于诊断
    h_safe = np.maximum(h_after, solver.eps_dry)
    A = h_safe * solver.B
    u = Q_after / A
    c = np.sqrt(solver.g * h_safe)
    lambda_max = np.max(np.abs(u) + c)

    print(f"步{step_count:3d}: t={t_before:7.3f}→{t_after:7.3f}, "
          f"dt={dt_computed:.6f}, Δt={dt_actual:.6f}, "
          f"λ_max={lambda_max:.4f}, "
          f"Δh={h_change:.2e}, ΔQ={Q_change:.2e}")

    # 检测异常
    if dt_computed < 1e-6:
        print(f"\n❌ dt变成极小值！")
        print(f"  dt_computed={dt_computed:.10f}")
        print(f"  CFL*dx/lambda_max = {solver.cfl * solver.dx / lambda_max:.10f}")
        print(f"  dt_max = {solver.dt_max}")

        # 详细状态
        print(f"\n  h统计: min={np.min(h_after):.6f}, max={np.max(h_after):.6f}, mean={np.mean(h_after):.6f}")
        print(f"  Q统计: min={np.min(Q_after):.6f}, max={np.max(Q_after):.6f}, mean={np.mean(Q_after):.6f}")
        print(f"  u统计: min={np.min(u):.6f}, max={np.max(u):.6f}")
        print(f"  c统计: min={np.min(c):.6f}, max={np.max(c):.6f}")

        # 检查NaN/Inf
        if np.any(np.isnan(h_after)):
            nan_indices = np.where(np.isnan(h_after))[0]
            print(f"  ⚠️  h中有NaN，位置: {nan_indices[:10]}")
        if np.any(np.isinf(h_after)):
            inf_indices = np.where(np.isinf(h_after))[0]
            print(f"  ⚠️  h中有Inf，位置: {inf_indices[:10]}")

        break

    if dt_actual < 1e-10:
        print(f"\n⚠️  时间没有推进！dt_actual={dt_actual:.2e}")
        print(f"  可能原因：数值舍入或状态未更新")
        break

    step_count += 1

print(f"\n最终: t={solver.t:.3f}s, 总步数={step_count}")
print("="*70)
