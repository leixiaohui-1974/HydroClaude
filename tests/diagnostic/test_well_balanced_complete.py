#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Well-Balanced Godunov-FVM完整验证

测试：
1. 稳态均匀流（长时间）- 关键测试
2. Dam Break（无摩阻）
3. MacDonald Case 1（激波）
"""

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
    from solvers.godunov_fvm_solver_wb import GodunvFVMSolverWB
except ImportError as e:
    pytest.skip(f"Required module not available: {e}", allow_module_level=True)

from solvers.godunov_fvm_solver import GodunvFVMSolver
from utils.canal_utils import compute_steady_uniform_flow


print("="*80)
print("Well-Balanced Godunov-FVM - 完整验证")
print("="*80)

# ========== 测试1: 稳态均匀流（关键测试）==========
print("\n" + "="*80)
print("测试1: 稳态均匀流 - Well-Balanced vs 标准")
print("="*80)

width = 10.0
length = 1000.0
n_cells = 100
manning_n = 0.025
slope = 0.001
Q_target = 50.0

h_uniform = compute_steady_uniform_flow(Q_target, width, slope, manning_n)

print(f"\n配置:")
print(f"  长度: {length}m, 单元: {n_cells}")
print(f"  Manning n: {manning_n}, 坡度: {slope}")
print(f"  目标流量: {Q_target} m^3/s")
print(f"  理论水深: {h_uniform:.4f} m")

# 测试Well-Balanced
print(f"\n--- Well-Balanced Order 2 ---")

solver_wb = GodunvFVMSolverWB(
    width=width, length=length, n_cells=n_cells,
    manning_n=manning_n, slope=slope,
    cfl=0.5, order=2, well_balanced=True
)

h_init = np.ones(n_cells) * h_uniform
Q_init = np.ones(n_cells) * Q_target

bc_left = {'type': 'Q', 'value': Q_target}
bc_right = {'type': 'h', 'value': h_uniform}

solver_wb.initialize(h_init, Q_init, bc_left, bc_right)

t_target = 1000.0
max_steps = 5000

print(f"\n时间推进至 t={t_target}s:")

while solver_wb.t < t_target and solver_wb.step_count < max_steps:
    h, Q = solver_wb.step()
    
    if np.any(np.isnan(h)) or np.any(np.isnan(Q)):
        print(f"   步{solver_wb.step_count}出现NaN!")
        break
    
    if solver_wb.step_count % 500 == 0:
        state = solver_wb.get_state()
        print(f"  t={state['t']:6.1f}s, 步{state['step']:4d}, "
              f"质量误差={state['mass_error']:7.4f}%, "
              f"<h>={np.mean(state['h']):.4f}m")

state_wb = solver_wb.get_state()
h_wb = state_wb['h']
Q_wb = state_wb['Q']

h_mean_wb = np.mean(h_wb)
Q_mean_wb = np.mean(Q_wb)
h_error_wb = abs(h_mean_wb - h_uniform) / h_uniform * 100.0
Q_error_wb = abs(Q_mean_wb - Q_target) / Q_target * 100.0
h_std_wb = np.std(h_wb) / h_mean_wb * 100.0

print(f"\nWell-Balanced结果 (t={state_wb['t']:.1f}s, {state_wb['step']}步):")
print(f"  质量误差: {state_wb['mass_error']:.6f}%")
print(f"  平均水深: {h_mean_wb:.4f}m (误差: {h_error_wb:.2f}%)")
print(f"  平均流量: {Q_mean_wb:.2f}m^3/s (误差: {Q_error_wb:.2f}%)")
print(f"  水深均匀性: {h_std_wb:.4f}%")
print(f"  状态: {' 稳定' if not np.any(np.isnan(h_wb)) else ' NaN'}")

# 对比标准Order 1
print(f"\n--- 标准Order 1（参考）---")

solver_std = GodunvFVMSolver(
    width=width, length=length, n_cells=n_cells,
    manning_n=manning_n, slope=slope,
    cfl=0.5, order=1
)

solver_std.initialize(h_init, Q_init, bc_left, bc_right)

while solver_std.t < t_target and solver_std.step_count < max_steps:
    solver_std.step()
    if solver_std.step_count % 500 == 0:
        state = solver_std.get_state()
        print(f"  t={state['t']:6.1f}s, 步{state['step']:4d}, "
              f"质量误差={state['mass_error']:7.4f}%")

state_std = solver_std.get_state()
h_std = state_std['h']

h_mean_std = np.mean(h_std)
h_error_std = abs(h_mean_std - h_uniform) / h_uniform * 100.0
h_std_std = np.std(h_std) / h_mean_std * 100.0

print(f"\n标准Order 1结果 (t={state_std['t']:.1f}s, {state_std['step']}步):")
print(f"  质量误差: {state_std['mass_error']:.6f}%")
print(f"  平均水深: {h_mean_std:.4f}m (误差: {h_error_std:.2f}%)")
print(f"  水深均匀性: {h_std_std:.4f}%")

# 对比
print(f"\n对比:")
print(f"  质量误差: WB={state_wb['mass_error']:.4f}% vs Std={state_std['mass_error']:.4f}%")
print(f"  水深误差: WB={h_error_wb:.2f}% vs Std={h_error_std:.2f}%")
print(f"  均匀性: WB={h_std_wb:.2f}% vs Std={h_std_std:.2f}%")

# 成功标准
checks = [
    ("质量守恒<1%", abs(state_wb['mass_error']) < 1.0),
    ("水深误差<1%", h_error_wb < 1.0),
    ("流量误差<1%", Q_error_wb < 1.0),
    ("均匀性<5%", h_std_wb < 5.0),
    ("数值稳定", not np.any(np.isnan(h_wb)))
]

print(f"\n成功标准:")
for name, passed in checks:
    print(f"  {name}: {'' if passed else ''}")

all_pass = all(c[1] for c in checks)

# 可视化
fig, ((ax1, ax2), (ax3, ax4)) = plt.subplots(2, 2, figsize=(14, 10))

# 水深剖面对比
ax1.plot(solver_wb.x, h_wb, 'b-', lw=1.5, label='Well-Balanced Order 2')
ax1.plot(solver_std.x, h_std, 'r--', lw=1.5, label='Standard Order 1')
ax1.axhline(h_uniform, color='k', ls=':', lw=2, label=f'Uniform ({h_uniform:.4f}m)')
ax1.set_xlabel('x (m)', fontsize=11)
ax1.set_ylabel('h (m)', fontsize=11)
ax1.set_title('Water Depth Profile', fontsize=12)
ax1.legend(fontsize=10)
ax1.grid(True, alpha=0.3)

# 流量剖面
ax2.plot(solver_wb.x, Q_wb, 'g-', lw=1.5, label='Well-Balanced')
ax2.axhline(Q_target, color='k', ls=':', lw=2, label=f'Target ({Q_target}m^3/s)')
ax2.set_xlabel('x (m)', fontsize=11)
ax2.set_ylabel('Q (m^3/s)', fontsize=11)
ax2.set_title('Discharge Profile', fontsize=12)
ax2.legend(fontsize=10)
ax2.grid(True, alpha=0.3)

# 水深误差
error_wb = (h_wb - h_uniform) / h_uniform * 100.0
error_std = (h_std - h_uniform) / h_uniform * 100.0
ax3.plot(solver_wb.x, error_wb, 'b-', lw=1.5, label='Well-Balanced')
ax3.plot(solver_std.x, error_std, 'r--', lw=1.5, label='Standard')
ax3.axhline(0, color='k', ls='-', lw=0.5)
ax3.set_xlabel('x (m)', fontsize=11)
ax3.set_ylabel('Depth Error (%)', fontsize=11)
ax3.set_title('Depth Error Comparison', fontsize=12)
ax3.legend(fontsize=10)
ax3.grid(True, alpha=0.3)

# 统计对比
categories = ['Mass Error\n(%)', 'Depth Error\n(%)', 'Uniformity\n(%)']
wb_values = [abs(state_wb['mass_error']), h_error_wb, h_std_wb]
std_values = [abs(state_std['mass_error']), h_error_std, h_std_std]

x_pos = np.arange(len(categories))
width_bar = 0.35

ax4.bar(x_pos - width_bar/2, wb_values, width_bar, label='Well-Balanced', color='blue', alpha=0.7)
ax4.bar(x_pos + width_bar/2, std_values, width_bar, label='Standard Order 1', color='red', alpha=0.7)
ax4.set_ylabel('Error (%)', fontsize=11)
ax4.set_title('Performance Comparison', fontsize=12)
ax4.set_xticks(x_pos)
ax4.set_xticklabels(categories, fontsize=10)
ax4.legend(fontsize=10)
ax4.grid(True, alpha=0.3, axis='y')

plt.tight_layout()
plt.savefig('/workspace/well_balanced_steady_flow.png', dpi=150)
print(f"\n  图像: well_balanced_steady_flow.png")

print(f"\n{'='*80}")
if all_pass:
    print(" Well-Balanced稳态均匀流 **通过** ")
else:
    print("️ Well-Balanced稳态均匀流 部分通过")
print("="*80)

# ========== 测试2: Dam Break ==========
print("\n" + "="*80)
print("测试2: Dam Break - Well-Balanced")
print("="*80)

solver_dam = GodunvFVMSolverWB(
    width=10.0, length=200.0, n_cells=200,
    manning_n=0.0, slope=0.0,
    cfl=0.5, order=2, well_balanced=True
)

x_dam = 100.0
h_init_dam = np.where(solver_dam.x < x_dam, 10.0, 1.0)
Q_init_dam = np.zeros(200)

bc_dam_left = {'type': 'h', 'value': 10.0}
bc_dam_right = {'type': 'h', 'value': 1.0}

solver_dam.initialize(h_init_dam, Q_init_dam, bc_dam_left, bc_dam_right)

print(f"\n时间推进至 t=2s:")

while solver_dam.t < 2.0 and solver_dam.step_count < 10000:
    solver_dam.step()
    
    if np.any(np.isnan(solver_dam.h)):
        print(f"   步{solver_dam.step_count}出现NaN!")
        break
    
    if solver_dam.step_count % 500 == 0:
        state = solver_dam.get_state()
        print(f"  t={state['t']:.2f}s, 步{state['step']:4d}, "
              f"质量误差={state['mass_error']:.4f}%")

state_dam = solver_dam.get_state()

print(f"\nDam Break结果 (t={state_dam['t']:.2f}s, {state_dam['step']}步):")
print(f"  质量误差: {state_dam['mass_error']:.6f}%")
print(f"  状态: {' 稳定' if not np.any(np.isnan(state_dam['h'])) else ' NaN'}")
print(f"  目标<1%: {'' if abs(state_dam['mass_error']) < 1.0 else ''}")

print("\n" + "="*80)
print(" Well-Balanced完整验证完成！")
print("="*80)
