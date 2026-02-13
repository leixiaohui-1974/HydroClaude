#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
水跃初始条件测试 - 用包含水跃的初场替代线性初场

MacDonald Test 4的真正挑战不是"捕捉"水跃，而是"维持"水跃。
让我们从一个已经包含水跃的初始条件开始。

水跃理论（动量方程）：
h2/h1 = 0.5 * (√(1 + 8*Fr1^2) - 1)
其中 Fr1 = Q/(B*h1*√(g*h1)) 是上游Froude数

日期: 2025-10-29
"""

import sys
import warnings
warnings.filterwarnings("ignore")
import os
sys.path.insert(0, os.path.dirname(__file__))

import numpy as np
import pytest
try:
    from solvers.godunov_fvm_weno3 import GodunvFVMWENO3
except ImportError as e:
    pytest.skip(f"Required module not available: {e}", allow_module_level=True)


# Test 4参数
L = 1000.0
B = 10.0
h_upstream = 0.7
Q_val = 20.0
h_downstream = 2.8
n_cells = 200
g = 9.81
dx = L / n_cells

# 计算理论水跃
u1 = Q_val / (B * h_upstream)
Fr1 = u1 / np.sqrt(g * h_upstream)
h2_theory = h_upstream * 0.5 * (np.sqrt(1 + 8*Fr1**2) - 1)

print("="*70)
print("水跃初始条件测试")
print("="*70)
print(f"上游：h1={h_upstream}m, u1={u1:.2f}m/s, Fr1={Fr1:.3f}")
print(f"理论水跃：h2={h2_theory:.3f}m")
print(f"下游边界：h_down={h_downstream}m")
print()

# 测试不同的水跃位置
jump_positions = [0.3, 0.4, 0.5, 0.6, 0.7]  # 相对位置

for jump_rel_pos in jump_positions:
    jump_loc = L * jump_rel_pos
    print(f"\n{'='*70}")
    print(f"测试：水跃位于 x={jump_loc:.1f}m (相对位置{jump_rel_pos:.1f})")
    print(f"{'='*70}")

    # 创建包含水跃的初始条件
    x = np.linspace(dx/2, L - dx/2, n_cells)
    h_init = np.zeros(n_cells)
    Q_init = np.ones(n_cells) * Q_val

    # 方案1：阶跃函数（理想化水跃）
    idx_jump = np.argmin(np.abs(x - jump_loc))
    h_init[:idx_jump] = h_upstream  # 上游：急流
    n_downstream = n_cells - idx_jump
    h_init[idx_jump:] = np.linspace(h2_theory, h_downstream, n_downstream)  # 下游：缓流过渡

    print(f"  初始h范围：[{np.min(h_init):.3f}, {np.max(h_init):.3f}]")
    print(f"  水跃位置：单元{idx_jump} (x={x[idx_jump]:.1f}m)")

    # 测试CFL=0.4（标准）
    for cfl in [0.4, 0.3]:
        print(f"\n  CFL={cfl}:")

        solver = GodunvFVMWENO3(
            width=B, length=L, n_cells=n_cells,
            manning_n=0.0, slope=0.0, g=g,
            cfl=cfl, eps_dry=1e-6, weno_epsilon=1e-6,
            riemann_solver='hll', use_numba=True, dt_max=0.5
        )

        bc_left = {'type': 'supercritical', 'h': h_upstream, 'Q': Q_val}
        bc_right = {'type': 'h', 'value': h_downstream}
        solver.initialize(h_init.copy(), Q_init.copy(), bc_left, bc_right)

        target_time = 50.0
        step = 0
        max_steps = 5000
        failed = False

        while solver.t < target_time and step < max_steps:
            dt = solver.compute_dt()

            if dt < 1e-6:
                print(f"     失败：t={solver.t:.2f}s时dt变为{dt:.2e}")
                failed = True
                break

            if np.any(solver.h < 0) or np.any(np.isnan(solver.h)):
                print(f"     失败：t={solver.t:.2f}s出现非物理h值")
                failed = True
                break

            solver.step(dt)
            step += 1

        if not failed:
            mass_error = abs(solver._compute_total_mass() - solver.initial_mass) / solver.initial_mass * 100
            h_up_final = solver.h[0]
            u_up_final = solver.Q[0] / (h_up_final * B)
            Fr_up = u_up_final / np.sqrt(g * h_up_final)
            n_negative = np.sum(solver.Q < 0)

            print(f"     成功：t={solver.t:.2f}s, 步数={step}")
            print(f"       质量误差={mass_error:.2f}%, Fr={Fr_up:.3f}")
            print(f"       h范围=[{np.min(solver.h):.3f}, {np.max(solver.h):.3f}]")

            if n_negative > 0:
                print(f"       ️  {n_negative}个单元负流量")

            if mass_error < 5.0 and Fr_up > 1.0 and n_negative == 0:
                print(f"        优秀！")
                break  # 找到好的配置，停止测试这个位置的其他CFL
        else:
            print(f"    最终：t={solver.t:.2f}s, 步数={step}")

print(f"\n{'='*70}")
print("结论：")
print("  如果从包含水跃的初场开始能稳定运行，说明WENO3可以维持水跃")
print("  如果仍然失败，说明WENO3对水跃不连续性本身敏感")
print(f"{'='*70}")
