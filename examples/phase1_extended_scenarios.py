#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Phase 1扩展场景库 - 20个场景完整版

Phase 1完善：从12个扩充到20个场景
新增场景：
- 不同渠道宽度（4个）
- 组合参数（4个）

目标：展示HydroClaude的广泛适用性

作者: HydroClaude Team
日期: 2025-10-27
"""

import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from solvers.godunov_fvm_solver import GodunvFVMSolver
from utils.canal_utils import compute_steady_uniform_flow
import numpy as np
import matplotlib.pyplot as plt

print("=" * 80)
print("Phase 1扩展场景库 - 20个完整场景")
print("=" * 80)

# 定义所有20个场景
scenarios = [
    # 原有12个场景（Group 1-3）
    # Group 1: 不同流量
    {"name": "Q30", "Q": 30, "B": 10, "S0": 0.001, "n": 0.025, "group": "流量组"},
    {"name": "Q50", "Q": 50, "B": 10, "S0": 0.001, "n": 0.025, "group": "流量组"},
    {"name": "Q80", "Q": 80, "B": 10, "S0": 0.001, "n": 0.025, "group": "流量组"},
    {"name": "Q120", "Q": 120, "B": 10, "S0": 0.001, "n": 0.025, "group": "流量组"},
    
    # Group 2: 不同底坡
    {"name": "S0.0005", "Q": 50, "B": 10, "S0": 0.0005, "n": 0.025, "group": "底坡组"},
    {"name": "S0.001", "Q": 50, "B": 10, "S0": 0.001, "n": 0.025, "group": "底坡组"},
    {"name": "S0.002", "Q": 50, "B": 10, "S0": 0.002, "n": 0.025, "group": "底坡组"},
    {"name": "S0.003", "Q": 50, "B": 10, "S0": 0.003, "n": 0.025, "group": "底坡组"},
    
    # Group 3: 不同糙率
    {"name": "n0.015", "Q": 50, "B": 10, "S0": 0.001, "n": 0.015, "group": "糙率组"},
    {"name": "n0.025", "Q": 50, "B": 10, "S0": 0.001, "n": 0.025, "group": "糙率组"},
    {"name": "n0.035", "Q": 50, "B": 10, "S0": 0.001, "n": 0.035, "group": "糙率组"},
    {"name": "n0.050", "Q": 50, "B": 10, "S0": 0.001, "n": 0.050, "group": "糙率组"},
    
    # 新增 Group 4: 不同渠道宽度
    {"name": "B5", "Q": 30, "B": 5, "S0": 0.001, "n": 0.025, "group": "宽度组"},
    {"name": "B10", "Q": 50, "B": 10, "S0": 0.001, "n": 0.025, "group": "宽度组"},
    {"name": "B20", "Q": 100, "B": 20, "S0": 0.001, "n": 0.025, "group": "宽度组"},
    {"name": "B30", "Q": 150, "B": 30, "S0": 0.001, "n": 0.025, "group": "宽度组"},
    
    # 新增 Group 5: 组合参数
    {"name": "小流量缓坡", "Q": 20, "B": 10, "S0": 0.0005, "n": 0.015, "group": "组合组"},
    {"name": "大流量陡坡", "Q": 100, "B": 10, "S0": 0.003, "n": 0.025, "group": "组合组"},
    {"name": "中流量粗糙", "Q": 50, "B": 10, "S0": 0.001, "n": 0.040, "group": "组合组"},
    {"name": "变化组合", "Q": 80, "B": 10, "S0": 0.0015, "n": 0.030, "group": "组合组"},
]

print(f"\n总场景数: {len(scenarios)}")
print(f"分组统计:")
groups = {}
for s in scenarios:
    g = s['group']
    groups[g] = groups.get(g, 0) + 1
for g, count in groups.items():
    print(f"  {g}: {count}个")

# 运行所有场景
results = []

print(f"\n开始运行所有场景...")
print(f"{'场景名':<15} {'Q':<8} {'B':<8} {'S0':<10} {'n':<8} {'质量误差':<12} {'状态':<10}")
print("-" * 90)

for i, scenario in enumerate(scenarios, 1):
    name = scenario['name']
    Q = scenario['Q']
    B = scenario['B']
    S0 = scenario['S0']
    n = scenario['n']
    
    try:
        # 创建求解器
        solver = GodunvFVMSolver(
            width=B, length=1000.0, n_cells=100,
            manning_n=n, slope=S0,
            cfl = 0.3, order=1
        )
        
        # 计算均匀流
        h_uniform = compute_steady_uniform_flow(Q, B, S0, n)
        
        # 初始化
        h_init = np.ones(100) * h_uniform
        Q_init = np.ones(100) * Q
        
        bc_left = {'type': 'Q', 'value': Q}
        bc_right = {'type': 'h', 'value': h_uniform}
        
        # GodunvFVMSolver需要手动初始化

        
        solver.h = h_init.copy()

        
        solver.Q = Q_init.copy()

        
        solver.bc_left = bc_left

        
        solver.bc_right = bc_right
        
        # 推进500步
        for _ in range(500):
            solver.step()
        
        # 结果
        state = solver.get_state()
        mass_error = state['mass_error']
        
        # 检查稳定性
        has_nan = np.any(np.isnan(state['h'])) or np.any(np.isnan(state['Q']))
        
        if has_nan:
            status = " NaN"
            success = False
        elif abs(mass_error) < 2.0:
            status = " 优秀"
            success = True
        elif abs(mass_error) < 5.0:
            status = "🟡 良好"
            success = True
        else:
            status = " 偏大"
            success = False
        
        results.append({
            'name': name,
            'Q': Q,
            'B': B,
            'S0': S0,
            'n': n,
            'mass_error': mass_error,
            'success': success,
            'status': status,
            'group': scenario['group']
        })
        
        print(f"{name:<15} {Q:<8.1f} {B:<8.1f} {S0:<10.4f} {n:<8.3f} {mass_error:<12.4f}% {status:<10}")
        
    except Exception as e:
        print(f"{name:<15} {Q:<8.1f} {B:<8.1f} {S0:<10.4f} {n:<8.3f} {'异常':<12}  失败")
        results.append({
            'name': name,
            'Q': Q,
            'B': B,
            'S0': S0,
            'n': n,
            'mass_error': float('nan'),
            'success': False,
            'status': " 异常",
            'group': scenario['group']
        })

# 统计
print("\n" + "=" * 80)
print("统计结果")
print("=" * 80)

total = len(results)
success_count = sum([1 for r in results if r['success']])
success_rate = success_count / total * 100

print(f"\n总场景数: {total}")
print(f"成功数: {success_count}")
print(f"成功率: {success_rate:.1f}%")

# 按分组统计
print(f"\n分组成功率:")
for group_name in set([r['group'] for r in results]):
    group_results = [r for r in results if r['group'] == group_name]
    group_total = len(group_results)
    group_success = sum([1 for r in group_results if r['success']])
    group_rate = group_success / group_total * 100
    print(f"  {group_name}: {group_success}/{group_total} ({group_rate:.1f}%)")

# 质量误差统计
valid_errors = [r['mass_error'] for r in results if r['success'] and not np.isnan(r['mass_error'])]
if len(valid_errors) > 0:
    print(f"\n质量误差统计（成功场景）:")
    print(f"  平均: {np.mean(valid_errors):.4f}%")
    print(f"  最大: {np.max(valid_errors):.4f}%")
    print(f"  最小: {np.min(valid_errors):.4f}%")
    print(f"  标准差: {np.std(valid_errors):.4f}%")

# 评价
print("\n" + "=" * 80)
print("综合评价")
print("=" * 80)

if success_rate >= 95:
    print(f"\n 优秀！成功率{success_rate:.1f}%")
elif success_rate >= 90:
    print(f"\n 良好！成功率{success_rate:.1f}%")
elif success_rate >= 80:
    print(f"\n🟡 可接受，成功率{success_rate:.1f}%")
else:
    print(f"\n 需改进，成功率{success_rate:.1f}%")

print(f"\nPhase 1扩展场景库:")
print(f"  - 场景数量: 12 -> 20个 (+67%)")
print(f"  - 成功率: {success_rate:.1f}%")
print(f"  - 平均质量误差: {np.mean(valid_errors):.4f}%")

if success_rate >= 90:
    print(f"\n Phase 1场景库完善成功！")
else:
    print(f"\n 仍有部分场景需要优化")

# 可视化（可选）
try:
    fig, axes = plt.subplots(2, 2, figsize=(14, 10))
    
    # 子图1: 按分组的成功率
    ax1 = axes[0, 0]
    group_names = list(set([r['group'] for r in results]))
    group_rates = []
    for gn in group_names:
        gr = [r for r in results if r['group'] == gn]
        rate = sum([1 for r in gr if r['success']]) / len(gr) * 100
        group_rates.append(rate)
    
    ax1.bar(range(len(group_names)), group_rates, color='steelblue')
    ax1.set_xticks(range(len(group_names)))
    ax1.set_xticklabels(group_names, rotation=45, ha='right')
    ax1.set_ylabel('成功率 (%)')
    ax1.set_title('各分组成功率')
    ax1.axhline(y=90, color='r', linestyle='--', alpha=0.5, label='90%目标线')
    ax1.legend()
    ax1.grid(True, alpha=0.3)
    
    # 子图2: 质量误差分布
    ax2 = axes[0, 1]
    valid_errors = [abs(r['mass_error']) for r in results if r['success'] and not np.isnan(r['mass_error'])]
    if len(valid_errors) > 0:
        ax2.hist(valid_errors, bins=15, color='green', alpha=0.7, edgecolor='black')
        ax2.set_xlabel('质量误差 (%)')
        ax2.set_ylabel('频数')
        ax2.set_title('质量误差分布')
        ax2.axvline(x=1.0, color='r', linestyle='--', label='1%参考线')
        ax2.legend()
        ax2.grid(True, alpha=0.3)
    
    # 子图3: 参数空间覆盖（Q vs S0）
    ax3 = axes[1, 0]
    success_results = [r for r in results if r['success']]
    fail_results = [r for r in results if not r['success']]
    
    if len(success_results) > 0:
        ax3.scatter([r['Q'] for r in success_results], [r['S0'] for r in success_results], 
                   c='green', marker='o', s=100, label='成功', alpha=0.7)
    if len(fail_results) > 0:
        ax3.scatter([r['Q'] for r in fail_results], [r['S0'] for r in fail_results], 
                   c='red', marker='x', s=100, label='失败', alpha=0.7)
    
    ax3.set_xlabel('流量 Q (m^3/s)')
    ax3.set_ylabel('底坡 S0')
    ax3.set_title('参数空间覆盖（Q-S0）')
    ax3.legend()
    ax3.grid(True, alpha=0.3)
    
    # 子图4: 统计饼图
    ax4 = axes[1, 1]
    labels = ['成功', '失败']
    sizes = [success_count, total - success_count]
    colors = ['green', 'red']
    explode = (0.1, 0)
    
    ax4.pie(sizes, explode=explode, labels=labels, colors=colors,
            autopct='%1.1f%%', shadow=True, startangle=90)
    ax4.set_title('总体成功率')
    
    plt.tight_layout()
    plt.savefig('./phase1_extended_scenarios.png', dpi=150, bbox_inches='tight')
    print(f"\n 图表已保存: phase1_extended_scenarios.png")
except Exception as e:
    print(f"\n 可视化失败: {str(e)}")

print("\n" + "=" * 80)
