#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
快速测试所有工况的初始恒定流状态
验证修复后的泵站是否在所有工况中都正常工作
"""

import sys
import os
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.gridspec import GridSpec

# 路径设置
project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, project_root)

from solvers.hydrostatic_canal_solver import HydrostaticCanalSolver
from solvers.gate import SluiceGate, PumpStation
from utils.canal_utils import compute_steady_uniform_flow

# 导入工况配置
exec(open('examples/example_gate_pump_cascade/enhanced_scenario_test.py', encoding='utf-8').read())

print("="*100)
print("串联明渠闸泵群系统 - 所有工况快速验证".center(100))
print("="*100)
print(f"\n总工况数: {len(FOCUSED_SCENARIOS)}")
print("\n测试目标:")
print("  1. 验证所有工况的恒定流初始状态是否合理")
print("  2. 检查泵站模型在所有工况中是否正常工作")
print("  3. 统计收敛性和流量守恒情况")
print("\n" + "="*100)

# 系统参数（与enhanced_scenario_test.py保持一致）
L_total = 100000.0
B = 15.0
S0 = 0.0001
n = 0.025
nx = 151  # 使用更粗网格加快测试
dt = 1.0

gate1_pos = 25000.0
pump_pos = 50000.0
gate2_pos = 75000.0

# 结果汇总
results_summary = []

for i, (scenario_id, config) in enumerate(FOCUSED_SCENARIOS.items(), 1):
    print(f"\n{'='*100}")
    print(f"[{i}/{len(FOCUSED_SCENARIOS)}] 测试工况: {config['name']}")
    print(f"{'='*100}")
    print(f"描述: {config['description']}")
    print(f"类别: {config['category']}")
    
    try:
        # 创建结构物
        gate1 = SluiceGate(gate1_pos, B, 5.0, 0.6)
        gate2 = SluiceGate(gate2_pos, B, 5.0, 0.6)
        pump = PumpStation(
            position=pump_pos,
            width=B,
            rated_flow=30.0,
            rated_head=5.0,
            min_suction_head=2.0
        )
        
        # 创建求解器
        solver = HydrostaticCanalSolver(
            length=L_total,
            nx=nx,
            B=B,
            S0=S0,
            n=n,
            internal_structures=[
                (gate1_pos, gate1),
                (pump_pos, pump),
                (gate2_pos, gate2)
            ]
        )
        
        # 配置底床高程
        pump_idx = np.argmin(np.abs(solver.x - pump_pos))
        solver.z[pump_idx:] += 5.0
        
        # 初始化
        Q_initial = config.get('Q_initial', 30.0)
        h_uniform = compute_steady_uniform_flow(Q_initial, B, S0, n)
        h_downstream_boundary = h_uniform
        
        solver.h[:] = h_uniform
        solver.hu[:] = Q_initial / B
        
        # 稳态求解
        result = solver.solve_steady_state(
            Q_target=Q_initial,
            h_downstream=h_downstream_boundary,
            convergence_tol = 0.1,
            max_iterations=1000,
            dt=dt,
            verbose=False
        )
        
        # 分析结果
        h_steady = result['h']
        Q_steady = solver.get_Q()
        
        Q_mean = np.mean(Q_steady)
        Q_error = abs(Q_mean - Q_initial) / Q_initial * 100
        
        h_min = np.min(h_steady)
        h_max = np.max(h_steady)
        h_mean = np.mean(h_steady)
        
        # 检查水深梯度
        h_diff = np.diff(h_steady)
        max_jump = np.max(np.abs(h_diff))
        
        # Froude数
        g = 9.81
        v = Q_steady / (B * h_steady + 1e-6)
        Fr = v / np.sqrt(g * h_steady + 1e-6)
        Fr_max = np.max(Fr)
        
        # 判断是否通过
        passed = (
            result['converged'] and
            Q_error < 0.1 and
            max_jump < 1.0 and
            Fr_max < 1.5 and
            h_min > 0.1
        )
        
        status = " 通过" if passed else " 失败"
        
        print(f"\n结果:")
        print(f"  收敛状态: {'' if result['converged'] else ''} (迭代{result['iterations']}次)")
        print(f"  流量误差: {Q_error:.4f}% {'' if Q_error < 0.1 else ''}")
        print(f"  水深范围: [{h_min:.3f}, {h_max:.3f}] m (均值: {h_mean:.3f} m)")
        print(f"  最大水深跳跃: {max_jump:.3f} m {'' if max_jump < 1.0 else ''}")
        print(f"  最大Froude数: {Fr_max:.3f} {'' if Fr_max < 1.5 else ''}")
        print(f"  综合评价: {status}")
        
        results_summary.append({
            'scenario_id': scenario_id,
            'name': config['name'],
            'category': config['category'],
            'converged': result['converged'],
            'iterations': result['iterations'],
            'Q_error': Q_error,
            'h_min': h_min,
            'h_max': h_max,
            'max_jump': max_jump,
            'Fr_max': Fr_max,
            'passed': passed
        })
        
    except Exception as e:
        print(f"\n 工况测试失败: {str(e)}")
        import traceback
        traceback.print_exc()
        
        results_summary.append({
            'scenario_id': scenario_id,
            'name': config['name'],
            'category': config['category'],
            'converged': False,
            'iterations': 0,
            'Q_error': 999.0,
            'h_min': 0.0,
            'h_max': 0.0,
            'max_jump': 999.0,
            'Fr_max': 999.0,
            'passed': False
        })

# ==================== 生成总结报告 ====================
print("\n" + "="*100)
print("测试总结".center(100))
print("="*100)

n_total = len(results_summary)
n_passed = sum(1 for r in results_summary if r['passed'])
n_failed = n_total - n_passed
success_rate = n_passed / n_total * 100 if n_total > 0 else 0

print(f"\n总体统计:")
print(f"  总工况数: {n_total}")
print(f"  通过: {n_passed} ({success_rate:.1f}%)")
print(f"  失败: {n_failed}")

# 按类别统计
categories = {}
for r in results_summary:
    cat = r['category']
    if cat not in categories:
        categories[cat] = {'total': 0, 'passed': 0}
    categories[cat]['total'] += 1
    if r['passed']:
        categories[cat]['passed'] += 1

print(f"\n按类别统计:")
for cat, stats in categories.items():
    rate = stats['passed'] / stats['total'] * 100 if stats['total'] > 0 else 0
    print(f"  {cat}: {stats['passed']}/{stats['total']} ({rate:.0f}%)")

# 详细结果表
print(f"\n详细结果:")
print(f"{'工况ID':<25} {'收敛':<6} {'迭代':<8} {'流量误差%':<12} {'最大跳跃m':<12} {'最大Fr':<10} {'状态':<8}")
print("-" * 100)
for r in results_summary:
    status_symbol = "" if r['passed'] else ""
    converged_symbol = "" if r['converged'] else ""
    print(f"{r['scenario_id']:<25} {converged_symbol:<6} {r['iterations']:<8} "
          f"{r['Q_error']:<12.4f} {r['max_jump']:<12.3f} {r['Fr_max']:<10.3f} {status_symbol:<8}")

# 生成可视化总结
print(f"\n生成可视化总结...")
fig = plt.figure(figsize=(20, 12))
gs = GridSpec(2, 2, figure=fig, hspace=0.3, wspace=0.3)

# 1. 收敛性统计
ax1 = fig.add_subplot(gs[0, 0])
categories_list = list(categories.keys())
passed_counts = [categories[cat]['passed'] for cat in categories_list]
total_counts = [categories[cat]['total'] for cat in categories_list]
failed_counts = [total_counts[i] - passed_counts[i] for i in range(len(categories_list))]

x_pos = np.arange(len(categories_list))
ax1.bar(x_pos - 0.2, passed_counts, 0.4, label='Passed', color='green', alpha=0.7)
ax1.bar(x_pos + 0.2, failed_counts, 0.4, label='Failed', color='red', alpha=0.7)
ax1.set_xticks(x_pos)
ax1.set_xticklabels(categories_list, rotation=15, ha='right', fontsize=10)
ax1.set_ylabel('Number of Scenarios', fontsize=12)
ax1.set_title('Convergence Statistics by Category', fontsize=14, fontweight='bold')
ax1.legend(fontsize=11)
ax1.grid(True, alpha=0.3, axis='y')

# 2. 流量误差分布
ax2 = fig.add_subplot(gs[0, 1])
scenario_names = [r['scenario_id'] for r in results_summary]
q_errors = [r['Q_error'] for r in results_summary]
colors = ['green' if r['passed'] else 'red' for r in results_summary]
ax2.bar(range(len(scenario_names)), q_errors, color=colors, alpha=0.7)
ax2.axhline(0.1, color='orange', linestyle='--', linewidth=2, alpha=0.7, label='Threshold: 0.1%')
ax2.set_xticks(range(len(scenario_names)))
ax2.set_xticklabels(scenario_names, rotation=45, ha='right', fontsize=9)
ax2.set_ylabel('Flow Error (%)', fontsize=12)
ax2.set_title('Flow Conservation Error', fontsize=14, fontweight='bold')
ax2.legend(fontsize=11)
ax2.grid(True, alpha=0.3, axis='y')
ax2.set_yscale('log')
ax2.set_ylim(0.0001, max(max(q_errors), 1.0))

# 3. 水深跳跃分布
ax3 = fig.add_subplot(gs[1, 0])
max_jumps = [r['max_jump'] for r in results_summary]
ax3.bar(range(len(scenario_names)), max_jumps, color=colors, alpha=0.7)
ax3.axhline(1.0, color='orange', linestyle='--', linewidth=2, alpha=0.7, label='Threshold: 1.0m')
ax3.set_xticks(range(len(scenario_names)))
ax3.set_xticklabels(scenario_names, rotation=45, ha='right', fontsize=9)
ax3.set_ylabel('Max Water Depth Jump (m)', fontsize=12)
ax3.set_title('Maximum Water Depth Gradient', fontsize=14, fontweight='bold')
ax3.legend(fontsize=11)
ax3.grid(True, alpha=0.3, axis='y')

# 4. Froude数分布
ax4 = fig.add_subplot(gs[1, 1])
fr_maxs = [r['Fr_max'] for r in results_summary]
ax4.bar(range(len(scenario_names)), fr_maxs, color=colors, alpha=0.7)
ax4.axhline(1.0, color='red', linestyle='--', linewidth=2, alpha=0.7, label='Critical: Fr=1')
ax4.axhline(1.5, color='orange', linestyle='--', linewidth=2, alpha=0.7, label='Threshold: Fr=1.5')
ax4.set_xticks(range(len(scenario_names)))
ax4.set_xticklabels(scenario_names, rotation=45, ha='right', fontsize=9)
ax4.set_ylabel('Maximum Froude Number', fontsize=12)
ax4.set_title('Maximum Froude Number Distribution', fontsize=14, fontweight='bold')
ax4.legend(fontsize=11)
ax4.grid(True, alpha=0.3, axis='y')

plt.suptitle(f'All Scenarios Quick Test Summary (Success Rate: {success_rate:.1f}%)', 
             fontsize=16, fontweight='bold')

output_path = 'examples/example_gate_pump_cascade/results_enhanced/all_scenarios_quick_test.png'
os.makedirs(os.path.dirname(output_path), exist_ok=True)
plt.savefig(output_path, dpi=150, bbox_inches='tight')
plt.close()

print(f" 可视化总结已保存至: {output_path}")

# 保存JSON报告
import json
report_path = 'examples/example_gate_pump_cascade/results_enhanced/all_scenarios_quick_test.json'
with open(report_path, 'w', encoding='utf-8') as f:
    json.dump({
        'summary': {
            'total': n_total,
            'passed': n_passed,
            'failed': n_failed,
            'success_rate': success_rate
        },
        'by_category': categories,
        'details': results_summary
    }, f, indent=2, ensure_ascii=False)

print(f" JSON报告已保存至: {report_path}")

print("\n" + "="*100)
if success_rate == 100:
    print(" 所有工况测试通过！".center(100))
elif success_rate >= 80:
    print(f" 大部分工况通过 ({success_rate:.1f}%)，少数需要进一步调查".center(100))
else:
    print(f" 多个工况失败 ({n_failed}个)，需要修复".center(100))
print("="*100 + "\n")
