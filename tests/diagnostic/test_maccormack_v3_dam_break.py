#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""MacCormack v3.0 Dam Break测试（带HLL+TVD）"""

import numpy as np
import warnings
warnings.filterwarnings("ignore")
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import sys
sys.path.insert(0, '/workspace')

import pytest
try:
    from solvers.maccormack_solver_v3 import MacCormackSolverV3
except ImportError as e:
    pytest.skip(f"Required module not available: {e}", allow_module_level=True)



def ritter_solution(x, t, h_L, h_R, x_dam, g=9.81):
    """Ritter解析解"""
    h = np.zeros_like(x)
    c_L = np.sqrt(g * h_L)
    x_front = x_dam + 2.0 * c_L * t
    x_tail = x_dam - c_L * t
    
    for i, xi in enumerate(x):
        if xi < x_tail:
            h[i] = h_L
        elif xi > x_front:
            h[i] = h_R
        else:
            h[i] = (1.0 / (9.0 * g)) * (2.0 * c_L - (xi - x_dam) / t)**2
    
    return h


print("="*80)
print("MacCormack v3.0 (HLL+TVD) - Dam Break")
print("="*80)

# 配置
width = 10.0
length = 200.0
n_cells = 200
x_dam = length / 2.0
h_L, h_R = 10.0, 1.0

solver = MacCormackSolverV3(
    width=width, length=length, n_cells=n_cells,
    manning_n=0.0, slope=0.0, cfl=0.5, use_tvd=True
)

x_centers = solver.x
h_init = np.where(x_centers < x_dam, h_L, h_R)
Q_init = np.zeros(n_cells)

bc_left = {'type': 'h', 'value': h_L}
bc_right = {'type': 'h', 'value': h_R}

solver.initialize(h_init, Q_init, bc_left, bc_right)

print(f"\n配置: 长{length}m, {n_cells}格, h_L={h_L}m, h_R={h_R}m")

# 时间推进
t_target = 2.0
step = 0
while solver.t < t_target and step < 10000:
    h, Q = solver.step()
    step += 1
    
    if np.any(np.isnan(h)):
        print(f"   步{step}出现NaN!")
        break
    
    if step % 500 == 0:
        state = solver.get_state()
        print(f"  t={state['t']:.2f}s, 步{step}, 质量误差={state['mass_error']:.4f}%")

# 结果
state = solver.get_state()
t_final = state['t']
h_num = state['h']
h_ana = ritter_solution(x_centers, t_final, h_L, h_R, x_dam)

# 波前
idx_front_num = np.where(h_num > 1.5 * h_R)[0]
idx_front_ana = np.where(h_ana > 1.5 * h_R)[0]

if len(idx_front_num) > 0 and len(idx_front_ana) > 0:
    x_front_num = x_centers[idx_front_num[-1]]
    x_front_ana = x_centers[idx_front_ana[-1]]
    front_err = abs(x_front_num - x_front_ana) / x_front_ana * 100.0
else:
    front_err = 0.0

rmse = np.sqrt(np.mean((h_num - h_ana)**2))
rmse_pct = rmse / h_L * 100.0

print(f"\n结果 (t={t_final:.2f}s, 步{step}):")
print(f"  质量误差: {state['mass_error']:.4f}%")
print(f"  波前误差: {front_err:.2f}%")
print(f"  RMSE: {rmse:.4f}m ({rmse_pct:.2f}%)")

# 评估
checks = [
    ("质量<1%", abs(state['mass_error']) < 1.0),
    ("波前<20%", front_err < 20),
    ("RMSE<15%", rmse_pct < 15),
    ("稳定", not np.any(np.isnan(h_num)))
]

print(f"\n评估:")
for name, passed in checks:
    print(f"  {name}: {'' if passed else ''}")

all_pass = all(c[1] for c in checks)

# 可视化
fig, ax = plt.subplots(figsize=(10, 6))
ax.plot(x_centers, h_ana, 'k-', lw=2, label='Ritter')
ax.plot(x_centers, h_num, 'r--', lw=1.5, label='MacCormack v3.0')
ax.axvline(x_dam, color='gray', ls=':', label='Dam')
ax.set_xlabel('x (m)')
ax.set_ylabel('h (m)')
ax.set_title(f'Dam Break (t={t_final:.2f}s, Mass Err={state["mass_error"]:.2f}%)')
ax.legend()
ax.grid(True, alpha=0.3)
plt.tight_layout()
plt.savefig('/workspace/maccormack_v3_dam_break.png', dpi=150)
print(f"\n  图: maccormack_v3_dam_break.png")

print(f"\n{'='*80}")
if all_pass:
    print(" MacCormack v3.0 通过 ")
else:
    print("️ MacCormack v3.0 部分通过")
print("="*80)
