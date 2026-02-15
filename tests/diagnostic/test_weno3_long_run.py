#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
WENO3长时间运行诊断 - 找出dt何时变成0

日期: 2025-10-29
"""

import sys
import warnings
warnings.filterwarnings("ignore")
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..'))

import numpy as np
import pytest
try:
    from solvers.godunov_fvm_weno3 import GodunvFVMWENO3
except ImportError as e:
    pytest.skip(f"Required module not available: {e}", allow_module_level=True)


# Test 4参数（与pytest完全一致）
L = 1000.0  # 改为1000m（与Test 4一致）
B = 10.0
n_cells = 200
manning_n = 0.03
S0 = 0.0
g = 9.81

Q = 20.0
h_up = 0.7
h_down = 2.8

# 创建WENO3求解器
solver = GodunvFVMWENO3(
    width=B,
    length=L,
    n_cells=n_cells,
    manning_n=manning_n,
    slope=S0,
    g=g,
    cfl=0.4,
    eps_dry=1e-6,
    weno_epsilon=1e-6,
    riemann_solver='hll',
    use_numba=True,
    dt_max=0.5
)

# 线性初始条件
h_init = np.linspace(h_up, h_down, n_cells)
Q_init = np.ones(n_cells) * Q

bc_left = {
    'type': 'supercritical',
    'h': h_up,
    'Q': Q
}
bc_right = {
    'type': 'fixed_h',
    'h': h_down
}

solver.initialize(h_init, Q_init, bc_left, bc_right)

print("="*70)
print("WENO3长时间运行诊断 - 追踪dt变化")
print("="*70)
print(f"目标运行时间: 100秒")
print(f"dt_max: {solver.dt_max}")
print()

t_end = 100.0
step_count = 0
last_report_t = 0.0
dt_min = 1e10
dt_max_seen = 0.0
dt_history = []

while solver.t < t_end and step_count < 100000:
    dt = solver.compute_dt()
    dt_history.append((solver.t, dt))

    dt_min = min(dt_min, dt)
    dt_max_seen = max(dt_max_seen, dt)

    solver.step(dt)
    step_count += 1

    # 每10秒报告
    if solver.t - last_report_t >= 10.0:
        print(f"  t={solver.t:6.1f}s, 步数={step_count:5d}, dt={dt:.6f}s, dt_min={dt_min:.6f}s")
        last_report_t = solver.t

    # 检测dt异常
    if dt < 1e-5:
        print(f"\n️  警告：dt变得非常小！")
        print(f"  t={solver.t:.3f}s, dt={dt:.9f}s")
        print(f"  step={step_count}")

        # 检查状态
        h_safe = np.maximum(solver.h, solver.eps_dry)
        A = h_safe * solver.B
        u = solver.Q / A
        c = np.sqrt(solver.g * h_safe)
        lambda_max = np.max(np.abs(u) + c)

        print(f"  lambda_max={lambda_max:.6f}")
        print(f"  max(|u|+c)={lambda_max:.6f}")
        print(f"  CFL*dx/lambda_max={solver.cfl * solver.dx / lambda_max:.6f}")
        print(f"  min(h)={np.min(solver.h):.6f}, max(h)={np.max(solver.h):.6f}")
        print(f"  min(Q)={np.min(solver.Q):.6f}, max(Q)={np.max(solver.Q):.6f}")

        # 找出最近10步的dt变化
        print(f"\n  最近10步dt历史:")
        for i, (t_hist, dt_hist) in enumerate(dt_history[-10:]):
            print(f"    步{step_count-10+i}: t={t_hist:.3f}s, dt={dt_hist:.9f}s")

        break

print(f"\n最终统计:")
print(f"  总步数: {step_count}")
print(f"  模拟时间: {solver.t:.2f}s / {t_end}s")
print(f"  dt范围: {dt_min:.9f} ~ {dt_max_seen:.6f}s")

if solver.t >= t_end * 0.9:
    print(f"\n 成功运行到接近目标时间")
else:
    print(f"\n 提前停止 ({solver.t/t_end*100:.1f}%)")
print("="*70)
