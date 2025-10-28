#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
工程案例3: 渠道改造方案对比

场景：某老旧渠道需要改造提升过流能力
目标：评估不同改造方案，选择最优方案

方案对比：
- 原方案：B=8m, n=0.035（老旧混凝土）
- 方案A：拓宽 B=12m, n=0.035（保持原糙率）
- 方案B：衬砌 B=8m, n=0.020（新混凝土）
- 方案C：综合 B=10m, n=0.025（适度拓宽+翻新）

分析指标：
- 过流能力
- Q-h关系
- 经济性
- 推荐方案

作者: HydroClaude Team
日期: 2025-10-27
"""

import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from solvers.godunov_fvm_solver import GodunvFVMSolver
from utils.canal_utils import compute_steady_uniform_flow, compute_critical_depth
from utils.hydraulic_tools import HydraulicTools
import numpy as np
import matplotlib.pyplot as plt

print("=" * 80)
print("工程案例3: 渠道改造方案对比分析")
print("=" * 80)

# 渠道基本参数
L = 2000.0  # 长度2km
n_cells = 100
S0 = 0.0012  # 底坡
g = 9.81

print(f"\n渠道基本参数:")
print(f"  长度: {L/1000} km")
print(f"  底坡: {S0}")
print(f"  网格数: {n_cells}")

# 四个方案
schemes = [
    {
        'name': '原方案',
        'description': '老旧渠道',
        'B': 8.0,
        'n': 0.035,
        'cost': 0,  # 基准成本
        'color': 'gray'
    },
    {
        'name': '方案A',
        'description': '拓宽（8→12m）',
        'B': 12.0,
        'n': 0.035,
        'cost': 120,  # 万元/km
        'color': 'red'
    },
    {
        'name': '方案B',
        'description': '衬砌（n=0.035→0.020）',
        'B': 8.0,
        'n': 0.020,
        'cost': 80,  # 万元/km
        'color': 'blue'
    },
    {
        'name': '方案C',
        'description': '综合（B=10m, n=0.025）',
        'B': 10.0,
        'n': 0.025,
        'cost': 100,  # 万元/km
        'color': 'green'
    }
]

print(f"\n改造方案:")
for i, scheme in enumerate(schemes, 1):
    print(f"\n{i}. {scheme['name']}: {scheme['description']}")
    print(f"   宽度: {scheme['B']} m")
    print(f"   糙率: {scheme['n']}")
    print(f"   成本: {scheme['cost']} 万元/km")

# 分析每个方案
results = []
tools = HydraulicTools()

print(f"\n" + "=" * 80)
print("逐方案分析")
print("=" * 80)

for scheme in schemes:
    print(f"\n{'=' * 80}")
    print(f"{scheme['name']}: {scheme['description']}")
    print(f"{'=' * 80}")
    
    B = scheme['B']
    n = scheme['n']
    
    # 1. 计算Q-h关系曲线
    Q_range = (20, 120)
    Q_curve, h_curve = tools.generate_rating_curve(
        width=B, slope=S0, manning_n=n,
        Q_range=Q_range, n_points=20
    )
    
    # 2. 计算渠道过流能力（假设最大水深3.5m）
    h_max = 3.5
    # 使用Manning公式计算最大流量
    A_max = B * h_max
    R_max = A_max / (B + 2 * h_max)
    Q_max = (1/n) * A_max * R_max**(2/3) * np.sqrt(S0)
    v_max = Q_max / A_max
    Fr_max = v_max / np.sqrt(9.81 * h_max)
    
    print(f"\n过流能力分析（h_max={h_max}m）:")
    print(f"  最大流量: {Q_max:.2f} m³/s")
    print(f"  最大流速: {v_max:.2f} m/s")
    print(f"  Froude数: {Fr_max:.3f}")
    print(f"  流态: {'超临界' if Fr_max > 1 else '亚临界'}")
    
    # 3. 运行稳态模拟（Q=60 m³/s）
    Q_design = 60.0
    print(f"\n设计流量模拟（Q={Q_design} m³/s）:")
    
    solver = GodunvFVMSolver(
        width=B, length=L, n_cells=n_cells,
        manning_n=n, slope=S0,
        cfl=0.5, order=1
    )
    
    h_uniform = compute_steady_uniform_flow(Q_design, B, S0, n)
    h_init = np.ones(n_cells) * h_uniform
    Q_init = np.ones(n_cells) * Q_design
    
    bc_left = {'type': 'Q', 'value': Q_design}
    bc_right = {'type': 'h', 'value': h_uniform}
    
    solver.initialize(h_init, Q_init, bc_left, bc_right)
    
    # 推进到稳态
    for _ in range(500):
        solver.step()
    
    state = solver.get_state()
    mass_error = state['mass_error']
    
    print(f"  均匀流水深: {h_uniform:.3f} m")
    print(f"  质量误差: {mass_error:.4f}%")
    print(f"  数值稳定: {'✅' if abs(mass_error) < 2.0 else '⚠️'}")
    
    # 4. 经济性分析
    total_cost = scheme['cost'] * (L / 1000)  # 总成本（万元）
    if Q_max > 0:
        cost_per_capacity = total_cost / Q_max  # 万元/(m³/s)
    else:
        cost_per_capacity = float('inf')
    
    results.append({
        'scheme': scheme,
        'Q_curve': Q_curve,
        'h_curve': h_curve,
        'Q_max': Q_max,
        'v_max': v_max,
        'Fr_max': Fr_max,
        'h_design': h_uniform,
        'mass_error': mass_error,
        'total_cost': total_cost,
        'cost_per_capacity': cost_per_capacity
    })

# 综合对比
print(f"\n" + "=" * 80)
print("综合对比分析")
print("=" * 80)

print(f"\n{'方案':<12} {'过流能力':<15} {'设计水深':<15} {'总成本':<15} {'单位成本':<20}")
print(f"{'':12} {'(m³/s)':<15} {'(m)':<15} {'(万元)':<15} {'(万元/[m³/s])':<20}")
print("-" * 85)

for result in results:
    name = result['scheme']['name']
    Q_max = result['Q_max']
    h_design = result['h_design']
    total_cost = result['total_cost']
    cost_per_cap = result['cost_per_capacity']
    
    if cost_per_cap == float('inf'):
        cost_str = "∞"
    else:
        cost_str = f"{cost_per_cap:.2f}"
    
    print(f"{name:<12} {Q_max:<15.2f} {h_design:<15.3f} {total_cost:<15.1f} {cost_str:<20}")

# 性能指标对比
print(f"\n性能提升对比（相对于原方案）:")
baseline = results[0]  # 原方案

print(f"\n{'方案':<12} {'过流能力提升':<18} {'水深降低':<15} {'综合评分':<15}")
print("-" * 60)

scores = []
for result in results:
    name = result['scheme']['name']
    
    # 过流能力提升
    Q_improve = (result['Q_max'] - baseline['Q_max']) / baseline['Q_max'] * 100
    
    # 水深降低（同流量下）
    h_reduce = (baseline['h_design'] - result['h_design']) / baseline['h_design'] * 100
    
    # 综合评分 = 过流能力提升 + 水深降低 - 成本系数
    cost_factor = result['total_cost'] / 100  # 归一化
    score = Q_improve + h_reduce - cost_factor
    
    print(f"{name:<12} {Q_improve:>+6.1f}%         {h_reduce:>+6.1f}%       {score:>6.1f}")
    
    scores.append({
        'name': name,
        'Q_improve': Q_improve,
        'h_reduce': h_reduce,
        'score': score
    })

# 推荐方案
print(f"\n" + "=" * 80)
print("推荐方案")
print("=" * 80)

best_idx = np.argmax([s['score'] for s in scores])
best_scheme = scores[best_idx]
best_result = results[best_idx]

print(f"\n🏆 推荐: {best_scheme['name']}")
print(f"\n优势:")
print(f"  1. 过流能力提升: {best_scheme['Q_improve']:+.1f}%")
print(f"  2. 水深降低: {best_scheme['h_reduce']:+.1f}%")
print(f"  3. 综合评分最高: {best_scheme['score']:.1f}")
print(f"  4. 最大过流能力: {best_result['Q_max']:.2f} m³/s")

print(f"\n投资:")
print(f"  总投资: {best_result['total_cost']:.1f} 万元")
print(f"  单位投资: {best_result['cost_per_capacity']:.2f} 万元/(m³/s)")

# 可视化
try:
    fig, axes = plt.subplots(2, 2, figsize=(15, 10))
    
    # 子图1: Q-h关系曲线对比
    ax1 = axes[0, 0]
    for result in results:
        ax1.plot(result['Q_curve'], result['h_curve'],
                label=result['scheme']['name'],
                color=result['scheme']['color'], linewidth=2)
    ax1.set_xlabel('流量 Q (m³/s)')
    ax1.set_ylabel('水深 h (m)')
    ax1.set_title('Q-h关系曲线对比')
    ax1.legend()
    ax1.grid(True, alpha=0.3)
    
    # 子图2: 过流能力对比
    ax2 = axes[0, 1]
    names = [r['scheme']['name'] for r in results]
    Q_maxs = [r['Q_max'] for r in results]
    colors = [r['scheme']['color'] for r in results]
    
    bars = ax2.bar(range(len(names)), Q_maxs, color=colors, alpha=0.7, edgecolor='black')
    ax2.set_xticks(range(len(names)))
    ax2.set_xticklabels(names)
    ax2.set_ylabel('最大流量 (m³/s)')
    ax2.set_title('过流能力对比（h_max=3.5m）')
    ax2.grid(True, alpha=0.3, axis='y')
    
    for bar, val in zip(bars, Q_maxs):
        ax2.text(bar.get_x() + bar.get_width()/2, val + 1,
                f'{val:.1f}', ha='center', va='bottom', fontweight='bold')
    
    # 子图3: 经济性对比
    ax3 = axes[1, 0]
    costs = [r['total_cost'] for r in results]
    
    bars = ax3.bar(range(len(names)), costs, color=colors, alpha=0.7, edgecolor='black')
    ax3.set_xticks(range(len(names)))
    ax3.set_xticklabels(names)
    ax3.set_ylabel('总投资 (万元)')
    ax3.set_title('投资成本对比')
    ax3.grid(True, alpha=0.3, axis='y')
    
    for bar, val in zip(bars, costs):
        if val > 0:
            ax3.text(bar.get_x() + bar.get_width()/2, val + 2,
                    f'{val:.0f}', ha='center', va='bottom', fontweight='bold')
    
    # 子图4: 综合评分
    ax4 = axes[1, 1]
    score_vals = [s['score'] for s in scores]
    
    bars = ax4.barh(range(len(names)), score_vals, color=colors, alpha=0.7, edgecolor='black')
    ax4.set_yticks(range(len(names)))
    ax4.set_yticklabels(names)
    ax4.set_xlabel('综合评分')
    ax4.set_title('综合评分对比（越高越好）')
    ax4.grid(True, alpha=0.3, axis='x')
    
    for bar, val in zip(bars, score_vals):
        ax4.text(val + 1, bar.get_y() + bar.get_height()/2,
                f'{val:.1f}', ha='left', va='center', fontweight='bold')
    
    plt.tight_layout()
    plt.savefig('/workspace/case_channel_renovation.png', dpi=150, bbox_inches='tight')
    print(f"\n📊 分析图表已保存: case_channel_renovation.png")
except Exception as e:
    print(f"\n⚠️ 可视化失败: {str(e)}")

# 工程建议
print(f"\n" + "=" * 80)
print("工程建议")
print("=" * 80)

print(f"\n1. 推荐采用: {best_scheme['name']}")
print(f"   • 参数: B={best_result['scheme']['B']}m, n={best_result['scheme']['n']}")
print(f"   • 投资: {best_result['total_cost']:.1f}万元")

print(f"\n2. 施工建议:")
print(f"   • 分段施工，避免全线停水")
print(f"   • 施工期设置临时导流")
print(f"   • 质量监控，确保糙率达标")

print(f"\n3. 运行管理:")
print(f"   • 最大流量不超过{best_result['Q_max']:.0f} m³/s")
print(f"   • 定期清淤，保持糙率")
print(f"   • 监测水深，及时调度")

print(f"\n" + "=" * 80)
print("✅ 渠道改造方案分析完成！")
print("=" * 80)
