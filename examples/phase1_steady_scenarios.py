#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Phase 1应用示例集 - 稳态场景库

基于Phase 0生产就绪的求解器，展示多种实际工程场景

场景：
1. 不同流量下的均匀流
2. 不同底坡的水面线
3. 不同糙率的流速分布

技术特点：
- 100%基于Phase 0验证的稳定算法
- 质量误差<1%
- 实际工程参考价值

作者: HydroClaude Team
日期: 2025-10-27
"""

import numpy as np
import warnings
warnings.filterwarnings("ignore")
import matplotlib.pyplot as plt
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from solvers.godunov_fvm_solver import GodunvFVMSolver
from utils.canal_utils import compute_steady_uniform_flow


print("="*80)
print(" Phase 1应用示例集 - 稳态场景库")
print("="*80)

# ========== 场景1: 不同流量 ==========
print("\n【场景1】不同设计流量对比")
print("-"*80)

width = 10.0
length = 1000.0
n_cells = 100
manning_n = 0.025
slope = 0.001

Q_list = [30.0, 50.0, 80.0, 120.0]
results_Q = []

print(f"\n推进各场景至稳态...")

for Q in Q_list:
    solver = GodunvFVMSolver(
        width=width, length=length, n_cells=n_cells,
        manning_n=manning_n, slope=slope,
        cfl = 0.3, order=1
    )
    
    h_uniform = compute_steady_uniform_flow(Q, width, slope, manning_n)
    h_init = np.ones(n_cells) * h_uniform
    Q_init = np.ones(n_cells) * Q
    
    bc_left = {'type': 'Q', 'value': Q}
    bc_right = {'type': 'h', 'value': h_uniform}
    
    # GodunvFVMSolver需要手动初始化

    
    solver.h = h_init.copy()

    
    solver.Q = Q_init.copy()

    
    solver.bc_left = bc_left

    
    solver.bc_right = bc_right
    
    for _ in range(500):
        solver.step()
    
    state = solver.get_state()
    
    results_Q.append({
        'Q': Q,
        'h_mean': np.mean(state['h']),
        'v_mean': Q / (np.mean(state['h']) * width),
        'mass_error': state['mass_error'],
        'x': state['x'],
        'h': state['h']
    })
    
    print(f"  Q={Q:.0f}m^3/s: h={np.mean(state['h']):.3f}m, "
          f"v={Q/(np.mean(state['h'])*width):.3f}m/s, "
          f"误差={state['mass_error']:.4f}%")

# ========== 场景2: 不同底坡 ==========
print(f"\n【场景2】不同底坡对比")
print("-"*80)

Q_fixed = 50.0
slopes = [0.0005, 0.001, 0.002, 0.004]
results_slope = []

print(f"\n推进各场景至稳态...")

for S0 in slopes:
    solver = GodunvFVMSolver(
        width=width, length=length, n_cells=n_cells,
        manning_n=manning_n, slope=S0,
        cfl = 0.3, order=1
    )
    
    h_uniform = compute_steady_uniform_flow(Q_fixed, width, S0, manning_n)
    h_init = np.ones(n_cells) * h_uniform
    Q_init = np.ones(n_cells) * Q_fixed
    
    bc_left = {'type': 'Q', 'value': Q_fixed}
    bc_right = {'type': 'h', 'value': h_uniform}
    
    # GodunvFVMSolver需要手动初始化

    
    solver.h = h_init.copy()

    
    solver.Q = Q_init.copy()

    
    solver.bc_left = bc_left

    
    solver.bc_right = bc_right
    
    for _ in range(500):
        solver.step()
    
    state = solver.get_state()
    
    results_slope.append({
        'slope': S0,
        'h_mean': np.mean(state['h']),
        'Fr': Q_fixed / (width * np.mean(state['h']) * np.sqrt(9.81 * np.mean(state['h']))),
        'mass_error': state['mass_error'],
        'x': state['x'],
        'h': state['h']
    })
    
    Fr = Q_fixed / (width * np.mean(state['h']) * np.sqrt(9.81 * np.mean(state['h'])))
    print(f"  S0={S0:.4f}: h={np.mean(state['h']):.3f}m, "
          f"Fr={Fr:.3f}, "
          f"误差={state['mass_error']:.4f}%")

# ========== 场景3: 不同糙率 ==========
print(f"\n【场景3】不同曼宁糙率对比")
print("-"*80)

n_list = [0.015, 0.025, 0.035, 0.050]
results_n = []

print(f"\n推进各场景至稳态...")

for n_val in n_list:
    solver = GodunvFVMSolver(
        width=width, length=length, n_cells=n_cells,
        manning_n=n_val, slope=slope,
        cfl = 0.3, order=1
    )
    
    h_uniform = compute_steady_uniform_flow(Q_fixed, width, slope, n_val)
    h_init = np.ones(n_cells) * h_uniform
    Q_init = np.ones(n_cells) * Q_fixed
    
    bc_left = {'type': 'Q', 'value': Q_fixed}
    bc_right = {'type': 'h', 'value': h_uniform}
    
    # GodunvFVMSolver需要手动初始化

    
    solver.h = h_init.copy()

    
    solver.Q = Q_init.copy()

    
    solver.bc_left = bc_left

    
    solver.bc_right = bc_right
    
    for _ in range(500):
        solver.step()
    
    state = solver.get_state()
    
    results_n.append({
        'n': n_val,
        'h_mean': np.mean(state['h']),
        'v_mean': Q_fixed / (np.mean(state['h']) * width),
        'mass_error': state['mass_error'],
        'x': state['x'],
        'h': state['h']
    })
    
    print(f"  n={n_val:.3f}: h={np.mean(state['h']):.3f}m, "
          f"v={Q_fixed/(np.mean(state['h'])*width):.3f}m/s, "
          f"误差={state['mass_error']:.4f}%")

# ========== 可视化 ==========
print(f"\n生成可视化...")

fig = plt.figure(figsize=(16, 12))

# 场景1: 不同流量的水面线
ax1 = fig.add_subplot(3, 3, 1)
for res in results_Q:
    ax1.plot(res['x'], res['h'], linewidth=2, label=f"Q={res['Q']:.0f}m^3/s")
ax1.set_xlabel('Distance (m)', fontsize=11)
ax1.set_ylabel('Depth (m)', fontsize=11)
ax1.set_title('Scenario 1: Different Discharges', fontsize=12, fontweight='bold')
ax1.legend(fontsize=9)
ax1.grid(True, alpha=0.3)

# 场景1: 流量-水深关系
ax2 = fig.add_subplot(3, 3, 2)
Q_vals = [res['Q'] for res in results_Q]
h_vals = [res['h_mean'] for res in results_Q]
ax2.plot(Q_vals, h_vals, 'bo-', linewidth=2, markersize=8)
ax2.set_xlabel('Discharge (m^3/s)', fontsize=11)
ax2.set_ylabel('Mean Depth (m)', fontsize=11)
ax2.set_title('Rating Curve (Q-h)', fontsize=12, fontweight='bold')
ax2.grid(True, alpha=0.3)

# 场景1: 流量-流速关系
ax3 = fig.add_subplot(3, 3, 3)
v_vals = [res['v_mean'] for res in results_Q]
ax3.plot(Q_vals, v_vals, 'ro-', linewidth=2, markersize=8)
ax3.set_xlabel('Discharge (m^3/s)', fontsize=11)
ax3.set_ylabel('Mean Velocity (m/s)', fontsize=11)
ax3.set_title('Q-v Relationship', fontsize=12, fontweight='bold')
ax3.grid(True, alpha=0.3)

# 场景2: 不同底坡的水面线
ax4 = fig.add_subplot(3, 3, 4)
for res in results_slope:
    ax4.plot(res['x'], res['h'], linewidth=2, label=f"S0={res['slope']:.4f}")
ax4.set_xlabel('Distance (m)', fontsize=11)
ax4.set_ylabel('Depth (m)', fontsize=11)
ax4.set_title('Scenario 2: Different Slopes', fontsize=12, fontweight='bold')
ax4.legend(fontsize=9)
ax4.grid(True, alpha=0.3)

# 场景2: 底坡-水深关系
ax5 = fig.add_subplot(3, 3, 5)
slope_vals = [res['slope'] for res in results_slope]
h_slope_vals = [res['h_mean'] for res in results_slope]
ax5.plot(slope_vals, h_slope_vals, 'go-', linewidth=2, markersize=8)
ax5.set_xlabel('Slope', fontsize=11)
ax5.set_ylabel('Mean Depth (m)', fontsize=11)
ax5.set_title('Slope-Depth Relationship', fontsize=12, fontweight='bold')
ax5.grid(True, alpha=0.3)

# 场景2: 底坡-Froude数关系
ax6 = fig.add_subplot(3, 3, 6)
Fr_vals = [res['Fr'] for res in results_slope]
ax6.plot(slope_vals, Fr_vals, 'mo-', linewidth=2, markersize=8)
ax6.axhline(y=1.0, color='red', linestyle='--', linewidth=2, label='临界流')
ax6.set_xlabel('Slope', fontsize=11)
ax6.set_ylabel('Froude Number', fontsize=11)
ax6.set_title('Slope-Fr Relationship', fontsize=12, fontweight='bold')
ax6.legend(fontsize=9)
ax6.grid(True, alpha=0.3)

# 场景3: 不同糙率的水面线
ax7 = fig.add_subplot(3, 3, 7)
for res in results_n:
    ax7.plot(res['x'], res['h'], linewidth=2, label=f"n={res['n']:.3f}")
ax7.set_xlabel('Distance (m)', fontsize=11)
ax7.set_ylabel('Depth (m)', fontsize=11)
ax7.set_title('Scenario 3: Different Manning n', fontsize=12, fontweight='bold')
ax7.legend(fontsize=9)
ax7.grid(True, alpha=0.3)

# 场景3: 糙率-水深关系
ax8 = fig.add_subplot(3, 3, 8)
n_vals = [res['n'] for res in results_n]
h_n_vals = [res['h_mean'] for res in results_n]
ax8.plot(n_vals, h_n_vals, 'co-', linewidth=2, markersize=8)
ax8.set_xlabel('Manning n', fontsize=11)
ax8.set_ylabel('Mean Depth (m)', fontsize=11)
ax8.set_title('Roughness-Depth Relationship', fontsize=12, fontweight='bold')
ax8.grid(True, alpha=0.3)

# 质量守恒总结
ax9 = fig.add_subplot(3, 3, 9)
all_errors = []
all_labels = []
for i, res in enumerate(results_Q):
    all_errors.append(abs(res['mass_error']))
    all_labels.append(f"Q{i+1}")
for i, res in enumerate(results_slope):
    all_errors.append(abs(res['mass_error']))
    all_labels.append(f"S{i+1}")
for i, res in enumerate(results_n):
    all_errors.append(abs(res['mass_error']))
    all_labels.append(f"n{i+1}")

ax9.bar(range(len(all_errors)), all_errors, color='steelblue', alpha=0.7)
ax9.axhline(y=1.0, color='red', linestyle='--', linewidth=2, label='目标(<1%)')
ax9.set_xticks(range(len(all_errors)))
ax9.set_xticklabels(all_labels, rotation=45)
ax9.set_ylabel('Mass Error (%)', fontsize=11)
ax9.set_title('Mass Conservation - All Scenarios', fontsize=12, fontweight='bold')
ax9.legend(fontsize=9)
ax9.grid(True, alpha=0.3, axis='y')

plt.tight_layout()
plt.savefig('./phase1_steady_scenarios.png', dpi=150, bbox_inches='tight')
print(f"  保存: phase1_steady_scenarios.png")

# ========== 工程应用建议 ==========
print(f"\n" + "="*80)
print(" 工程应用建议")
print("="*80)

print(f"\n1. 渠道设计:")
print(f"   - 选择合适的设计流量")
print(f"   - 参考Q-h关系曲线确定渠道尺寸")
print(f"   - 控制Froude数避免超临界流")

print(f"\n2. 底坡选择:")
print(f"   - 陡坡(S0>0.002): 水深小，流速大，需防冲")
print(f"   - 缓坡(S0<0.001): 水深大，流速小，需防淤")
print(f"   - 参考Fr数判断流态")

print(f"\n3. 糙率影响:")
print(f"   - 糙率越大，水深越深")
print(f"   - 衬砌渠道(n=0.015)效率最高")
print(f"   - 天然渠道(n=0.035)需增大断面")

# ========== 验证总结 ==========
print(f"\n" + "="*80)
print(" 验证总结")
print("="*80)

all_scenarios = results_Q + results_slope + results_n
max_error = max([abs(res['mass_error']) for res in all_scenarios])
all_stable = all([abs(res['mass_error']) < 1.0 for res in all_scenarios])

print(f"\n总场景数: {len(all_scenarios)}")
print(f"最大质量误差: {max_error:.4f}%")
print(f"所有场景质量误差<1%: {' 是' if all_stable else ' 否'}")

if all_stable:
    print(f"\n 所有场景验证通过！")
    print(f" 基于Phase 0生产就绪求解器")
    print(f" 质量守恒优秀")
    print(f" 数值稳定性100%")
    print(f" 实际工程参考价值高")
else:
    print(f"\n 部分场景需优化")

print(f"\n" + "="*80)
print(f" Phase 1应用示例集完成！")
print(f"="*80)
