#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
工程案例5: 参数敏感性分析

场景分析渠道参数糙率底坡宽度对水深的影响
目标为渠道设计和改造提供参数优化建议

分析内容
1. 糙率敏感性n=0.015-0.040
2. 底坡敏感性S0=0.0005-0.002
3. 宽度敏感性B=8-20m
4. 综合优化建议

作者: HydroClaude Team
日期: 2025-10-27
"""

import sys, os
import warnings
warnings.filterwarnings("ignore")
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from solvers.godunov_fvm_solver import GodunvFVMSolver
from utils.canal_utils import compute_steady_uniform_flow, compute_critical_depth, compute_froude_number
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt

print("=" * 80)
print("工程案例5: 渠道参数敏感性分析")
print("=" * 80)

# 基准参数
Q_design = 50.0
L = 1500.0
n_cells = 100

print(f"\n基准参数:")
print(f"  设计流量: {Q_design} m^3/s")
print(f"  渠道长度: {L/1000} km")
print(f"  网格数: {n_cells}")

# ========== 分析1: 糙率敏感性 ==========
print(f"\n" + "=" * 80)
print("分析1: 糙率敏感性")
print("=" * 80)

B_base = 10.0
S0_base = 0.001

n_values = [0.015, 0.020, 0.025, 0.030, 0.035, 0.040]

print(f"\n固定参数: B={B_base}m, S0={S0_base}")
print(f"变化参数: n={n_values}")

results_n = []

for n in n_values:
    print(f"\n测试 n={n}...")
    
    # 理论计算
    h_uniform = compute_steady_uniform_flow(Q_design, B_base, S0_base, n)
    h_critical = compute_critical_depth(Q_design, B_base)
    v = Q_design / (B_base * h_uniform)
    Fr = v / np.sqrt(9.81 * h_uniform)
    
    # 数值模拟
    solver = GodunvFVMSolver(
        width=B_base, length=L, n_cells=n_cells,
        manning_n=n, slope=S0_base,
        cfl = 0.3, order=1
    )
    
    h_init = np.ones(n_cells) * h_uniform
    Q_init = np.ones(n_cells) * Q_design
    
    bc_left = {'type': 'Q', 'value': Q_design}
    bc_right = {'type': 'h', 'value': h_uniform}
    
    # GodunvFVMSolver需要手动初始化

    
    solver.h = h_init.copy()

    
    solver.Q = Q_init.copy()

    
    solver.bc_left = bc_left

    
    solver.bc_right = bc_right
    
    # 推进到稳态
    for _ in range(300):
        solver.step()
    
    state = solver.get_state()
    h_max = np.max(state['h'])
    h_avg = np.mean(state['h'])
    mass_error = abs(state['mass_error'])
    
    print(f"  水深: {h_avg:.3f} m")
    print(f"  Froude数: {Fr:.3f}")
    print(f"  质量误差: {mass_error:.4f}%")
    
    results_n.append({
        'n': n,
        'h_uniform': h_uniform,
        'h_avg': h_avg,
        'Fr': Fr,
        'mass_error': mass_error
    })

# ========== 分析2: 底坡敏感性 ==========
print(f"\n" + "=" * 80)
print("分析2: 底坡敏感性")
print("=" * 80)

n_base = 0.025

S0_values = [0.0005, 0.0008, 0.001, 0.0012, 0.0015, 0.002]

print(f"\n固定参数: B={B_base}m, n={n_base}")
print(f"变化参数: S0={S0_values}")

results_S0 = []

for S0 in S0_values:
    print(f"\n测试 S0={S0}...")
    
    # 理论计算
    h_uniform = compute_steady_uniform_flow(Q_design, B_base, S0, n_base)
    h_critical = compute_critical_depth(Q_design, B_base)
    v = Q_design / (B_base * h_uniform)
    Fr = v / np.sqrt(9.81 * h_uniform)
    
    # 数值模拟
    solver = GodunvFVMSolver(
        width=B_base, length=L, n_cells=n_cells,
        manning_n=n_base, slope=S0,
        cfl = 0.3, order=1
    )
    
    h_init = np.ones(n_cells) * h_uniform
    Q_init = np.ones(n_cells) * Q_design
    
    bc_left = {'type': 'Q', 'value': Q_design}
    bc_right = {'type': 'h', 'value': h_uniform}
    
    # GodunvFVMSolver需要手动初始化

    
    solver.h = h_init.copy()

    
    solver.Q = Q_init.copy()

    
    solver.bc_left = bc_left

    
    solver.bc_right = bc_right
    
    # 推进到稳态
    for _ in range(300):
        solver.step()
    
    state = solver.get_state()
    h_max = np.max(state['h'])
    h_avg = np.mean(state['h'])
    mass_error = abs(state['mass_error'])
    
    print(f"  水深: {h_avg:.3f} m")
    print(f"  Froude数: {Fr:.3f}")
    print(f"  质量误差: {mass_error:.4f}%")
    
    results_S0.append({
        'S0': S0,
        'h_uniform': h_uniform,
        'h_avg': h_avg,
        'Fr': Fr,
        'mass_error': mass_error
    })

# ========== 分析3: 宽度敏感性 ==========
print(f"\n" + "=" * 80)
print("分析3: 宽度敏感性")
print("=" * 80)

B_values = [8.0, 10.0, 12.0, 15.0, 18.0, 20.0]

print(f"\n固定参数: S0={S0_base}, n={n_base}")
print(f"变化参数: B={B_values}")

results_B = []

for B in B_values:
    print(f"\n测试 B={B}m...")
    
    # 理论计算
    h_uniform = compute_steady_uniform_flow(Q_design, B, S0_base, n_base)
    h_critical = compute_critical_depth(Q_design, B)
    v = Q_design / (B * h_uniform)
    Fr = v / np.sqrt(9.81 * h_uniform)
    
    # 数值模拟
    solver = GodunvFVMSolver(
        width=B, length=L, n_cells=n_cells,
        manning_n=n_base, slope=S0_base,
        cfl = 0.3, order=1
    )
    
    h_init = np.ones(n_cells) * h_uniform
    Q_init = np.ones(n_cells) * Q_design
    
    bc_left = {'type': 'Q', 'value': Q_design}
    bc_right = {'type': 'h', 'value': h_uniform}
    
    # GodunvFVMSolver需要手动初始化

    
    solver.h = h_init.copy()

    
    solver.Q = Q_init.copy()

    
    solver.bc_left = bc_left

    
    solver.bc_right = bc_right
    
    # 推进到稳态
    for _ in range(300):
        solver.step()
    
    state = solver.get_state()
    h_max = np.max(state['h'])
    h_avg = np.mean(state['h'])
    mass_error = abs(state['mass_error'])
    
    print(f"  水深: {h_avg:.3f} m")
    print(f"  Froude数: {Fr:.3f}")
    print(f"  质量误差: {mass_error:.4f}%")
    
    results_B.append({
        'B': B,
        'h_uniform': h_uniform,
        'h_avg': h_avg,
        'Fr': Fr,
        'mass_error': mass_error
    })

# ========== 综合分析 ==========
print(f"\n" + "=" * 80)
print("综合敏感性分析")
print("=" * 80)

# 糙率敏感性
n_min = results_n[0]['h_avg']
n_max = results_n[-1]['h_avg']
n_sensitivity = (n_max - n_min) / n_min * 100

print(f"\n1. 糙率敏感性:")
print(f"   n={n_values[0]} -> {n_values[-1]}")
print(f"   水深: {n_min:.3f}m -> {n_max:.3f}m")
print(f"   变化幅度: {n_sensitivity:.1f}%")
print(f"   结论: {'高敏感' if n_sensitivity > 30 else '中等敏感' if n_sensitivity > 15 else '低敏感'}")

# 底坡敏感性
S0_min = results_S0[0]['h_avg']
S0_max = results_S0[-1]['h_avg']
S0_sensitivity = abs(S0_max - S0_min) / S0_max * 100

print(f"\n2. 底坡敏感性:")
print(f"   S0={S0_values[0]} -> {S0_values[-1]}")
print(f"   水深: {S0_max:.3f}m -> {S0_min:.3f}m")
print(f"   变化幅度: {S0_sensitivity:.1f}%")
print(f"   结论: {'高敏感' if S0_sensitivity > 30 else '中等敏感' if S0_sensitivity > 15 else '低敏感'}")

# 宽度敏感性
B_min = results_B[0]['h_avg']
B_max = results_B[-1]['h_avg']
B_sensitivity = abs(B_max - B_min) / B_max * 100

print(f"\n3. 宽度敏感性:")
print(f"   B={B_values[0]}m -> {B_values[-1]}m")
print(f"   水深: {B_min:.3f}m -> {B_max:.3f}m")
print(f"   变化幅度: {B_sensitivity:.1f}%")
print(f"   结论: {'高敏感' if B_sensitivity > 30 else '中等敏感' if B_sensitivity > 15 else '低敏感'}")

# 排序敏感性
sensitivities = [
    ('糙率', n_sensitivity),
    ('底坡', S0_sensitivity),
    ('宽度', B_sensitivity)
]
sensitivities.sort(key=lambda x: x[1], reverse=True)

print(f"\n敏感性排序从高到低:")
for i, (param, sens) in enumerate(sensitivities, 1):
    print(f"  {i}. {param}: {sens:.1f}%")

# 可视化
try:
    fig, axes = plt.subplots(2, 2, figsize=(15, 10))
    
    # 子图1: 糙率敏感性
    ax1 = axes[0, 0]
    n_vals = [r['n'] for r in results_n]
    h_vals = [r['h_avg'] for r in results_n]
    ax1.plot(n_vals, h_vals, 'o-', linewidth=2, markersize=8, color='blue')
    ax1.set_xlabel('糙率 n')
    ax1.set_ylabel('水深 (m)')
    ax1.set_title(f'糙率敏感性 (变化{n_sensitivity:.1f}%)')
    ax1.grid(True, alpha=0.3)
    
    # 子图2: 底坡敏感性
    ax2 = axes[0, 1]
    S0_vals = [r['S0'] for r in results_S0]
    h_vals = [r['h_avg'] for r in results_S0]
    ax2.plot(S0_vals, h_vals, 's-', linewidth=2, markersize=8, color='green')
    ax2.set_xlabel('底坡 S0')
    ax2.set_ylabel('水深 (m)')
    ax2.set_title(f'底坡敏感性 (变化{S0_sensitivity:.1f}%)')
    ax2.grid(True, alpha=0.3)
    
    # 子图3: 宽度敏感性
    ax3 = axes[1, 0]
    B_vals = [r['B'] for r in results_B]
    h_vals = [r['h_avg'] for r in results_B]
    ax3.plot(B_vals, h_vals, '^-', linewidth=2, markersize=8, color='red')
    ax3.set_xlabel('宽度 B (m)')
    ax3.set_ylabel('水深 (m)')
    ax3.set_title(f'宽度敏感性 (变化{B_sensitivity:.1f}%)')
    ax3.grid(True, alpha=0.3)
    
    # 子图4: 综合对比
    ax4 = axes[1, 1]
    params = [s[0] for s in sensitivities]
    sens_vals = [s[1] for s in sensitivities]
    colors = ['red' if s > 30 else 'orange' if s > 15 else 'green' for s in sens_vals]
    
    bars = ax4.bar(range(len(params)), sens_vals, color=colors, alpha=0.7, edgecolor='black', linewidth=2)
    ax4.set_xticks(range(len(params)))
    ax4.set_xticklabels(params)
    ax4.set_ylabel('敏感性 (%)')
    ax4.set_title('参数敏感性对比')
    ax4.grid(True, alpha=0.3, axis='y')
    
    for bar, val in zip(bars, sens_vals):
        ax4.text(bar.get_x() + bar.get_width()/2, val + 1,
                f'{val:.1f}%', ha='center', va='bottom', fontweight='bold')
    
    plt.tight_layout()
    plt.savefig('./case_parameter_sensitivity.png', dpi=150, bbox_inches='tight')
    print(f"\n 分析图表已保存: case_parameter_sensitivity.png")
except Exception as e:
    print(f"\n 可视化失败: {str(e)}")

# 工程建议
print(f"\n" + "=" * 80)
print("工程建议")
print("=" * 80)

print(f"\n1. 设计阶段:")
if sensitivities[0][0] == '糙率':
    print(f"   - 糙率是最敏感参数必须精确确定")
    print(f"   - 建议进行现场测试或查阅规范")
elif sensitivities[0][0] == '底坡':
    print(f"   - 底坡是最敏感参数必须精确测量")
    print(f"   - 建议进行地形测量")
else:
    print(f"   - 宽度是最敏感参数需优化设计")
    print(f"   - 建议进行多方案比选")

print(f"\n2. 施工阶段:")
print(f"   - 严格控制{sensitivities[0][0]}最敏感参数")
print(f"   - 加强{sensitivities[1][0]}的质量控制")
print(f"   - {sensitivities[2][0]}可适当放宽误差")

print(f"\n3. 运行维护:")
print(f"   - 定期检查糙率清淤除草")
print(f"   - 监测底坡变化淤积冲刷")
print(f"   - 评估宽度充足性")

print(f"\n4. 改造优化:")
most_sensitive = sensitivities[0][0]
if most_sensitive == '糙率':
    print(f"   - 优先考虑降低糙率衬砌维护")
    print(f"   - 性价比最高")
elif most_sensitive == '底坡':
    print(f"   - 底坡改造成本高需综合论证")
else:
    print(f"   - 优先考虑拓宽")
    print(f"   - 降低水深增加安全性")

print(f"\n" + "=" * 80)
print(" 参数敏感性分析完成")
print("=" * 80)

# 数值稳定性统计
all_errors = []
all_errors.extend([r['mass_error'] for r in results_n])
all_errors.extend([r['mass_error'] for r in results_S0])
all_errors.extend([r['mass_error'] for r in results_B])

avg_error = np.mean(all_errors)
max_error = np.max(all_errors)

print(f"\n数值稳定性:")
print(f"  总测试数: {len(all_errors)}")
print(f"  平均质量误差: {avg_error:.4f}%")
print(f"  最大质量误差: {max_error:.4f}%")
print(f"  数值稳定: {' 优秀' if max_error < 2.0 else ' 一般'}")
