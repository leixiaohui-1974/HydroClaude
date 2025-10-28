#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
工程案例2: 渠道防洪风险评估（稳态分析）

场景：评估渠道在不同设计流量下的安全性
目标：确定安全流量上限，制定风险等级

包含4个设计工况：
1. 设计流量75%: Q=45 m³/s
2. 设计流量100%: Q=60 m³/s  
3. 设计流量125%: Q=75 m³/s
4. 设计流量150%: Q=90 m³/s

分析指标：
- 水深安全裕度
- 流速大小
- Froude数
- 风险等级

作者: HydroClaude Team
日期: 2025-10-27
"""

import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from solvers.godunov_fvm_solver import GodunvFVMSolver
from utils.canal_utils import compute_steady_uniform_flow, compute_critical_depth
import numpy as np
import matplotlib.pyplot as plt

print("=" * 80)
print("工程案例2: 渠道防洪风险评估")
print("=" * 80)

# 渠道参数（保守设计）
B = 12.0  # 宽度12m
L = 2000.0  # 长度2km
n_cells = 100
n = 0.028  # 糙率（适中）
S0 = 0.0010  # 底坡（适中）
h_bank = 4.5  # 堤顶高度4.5m

print(f"\n渠道参数:")
print(f"  宽度: {B} m")
print(f"  长度: {L/1000} km")
print(f"  底坡: {S0}")
print(f"  糙率: {n}")
print(f"  堤顶高度: {h_bank} m")

# 设计流量
Q_design = 60.0
print(f"\n设计流量: {Q_design} m³/s")

# 4个评估工况
schemes = [
    {'name': '工况1', 'description': '设计75%', 'Q': 45.0, 'ratio': 0.75, 'color': 'green'},
    {'name': '工况2', 'description': '设计100%', 'Q': 60.0, 'ratio': 1.00, 'color': 'blue'},
    {'name': '工况3', 'description': '设计125%', 'Q': 75.0, 'ratio': 1.25, 'color': 'orange'},
    {'name': '工况4', 'description': '设计150%', 'Q': 90.0, 'ratio': 1.50, 'color': 'red'},
]

print(f"\n评估工况:")
for i, scheme in enumerate(schemes, 1):
    print(f"\n{i}. {scheme['name']}: {scheme['description']}")
    print(f"   流量: {scheme['Q']} m³/s ({scheme['ratio']*100:.0f}%设计流量)")

# 运行每个工况
results = []

print(f"\n{'=' * 80}")
print(f"逐工况稳态模拟")
print(f"{'=' * 80}")

for scheme in schemes:
    print(f"\n{'=' * 80}")
    print(f"{scheme['name']}: {scheme['description']} (Q={scheme['Q']} m³/s)")
    print(f"{'=' * 80}")
    
    Q = scheme['Q']
    
    try:
        # 计算理论水深
        h_uniform = compute_steady_uniform_flow(Q, B, S0, n)
        h_critical = compute_critical_depth(Q, B)
        
        print(f"\n理论值:")
        print(f"  均匀流水深: {h_uniform:.3f} m")
        print(f"  临界水深: {h_critical:.3f} m")
        
        # 创建求解器
        solver = GodunvFVMSolver(
            width=B, length=L, n_cells=n_cells,
            manning_n=n, slope=S0,
            cfl=0.5, order=1
        )
        
        # 初始化
        h_init = np.ones(n_cells) * h_uniform
        Q_init = np.ones(n_cells) * Q
        
        bc_left = {'type': 'Q', 'value': Q}
        bc_right = {'type': 'h', 'value': h_uniform}
        
        solver.initialize(h_init, Q_init, bc_left, bc_right)
        
        # 推进到稳态（增加步数确保收敛）
        for _ in range(600):
            solver.step()
        
        # 获取结果
        state = solver.get_state()
        h_max = np.max(state['h'])
        h_avg = np.mean(state['h'])
        h_min = np.min(state['h'])
        mass_error = abs(state['mass_error'])
        
        # 检查数值有效性
        has_nan = np.any(np.isnan(state['h']))
        
        if not has_nan:
            # 计算流速和Froude数
            v_avg = Q / (B * h_avg)
            Fr = v_avg / np.sqrt(9.81 * h_avg)
            
            # 安全评估
            freeboard = h_bank - h_max  # 超高（安全余量）
            freeboard_ratio = freeboard / h_bank * 100
            
            if freeboard > 1.0:
                risk_level = "✅ 安全"
                risk_color = "green"
            elif freeboard > 0.5:
                risk_level = "🟡 中等风险"
                risk_color = "yellow"
            elif freeboard > 0:
                risk_level = "🟠 较高风险"
                risk_color = "orange"
            else:
                risk_level = "🔴 危险"
                risk_color = "red"
            
            print(f"\n数值模拟结果:")
            print(f"  最大水深: {h_max:.3f} m")
            print(f"  平均水深: {h_avg:.3f} m")
            print(f"  平均流速: {v_avg:.3f} m/s")
            print(f"  Froude数: {Fr:.3f}")
            print(f"  质量误差: {mass_error:.4f}%")
            
            print(f"\n安全评估:")
            print(f"  超高（安全余量）: {freeboard:.3f} m")
            print(f"  安全余量比例: {freeboard_ratio:.1f}%")
            print(f"  风险等级: {risk_level}")
            
            results.append({
                'scheme': scheme,
                'success': True,
                'Q': Q,
                'h_uniform': h_uniform,
                'h_max': h_max,
                'h_avg': h_avg,
                'v_avg': v_avg,
                'Fr': Fr,
                'freeboard': freeboard,
                'freeboard_ratio': freeboard_ratio,
                'risk_level': risk_level,
                'risk_color': risk_color,
                'mass_error': mass_error,
                'x': state['x'],
                'h': state['h']
            })
        else:
            print(f"\n❌ 数值失败：出现NaN")
            results.append({
                'scheme': scheme,
                'success': False,
                'Q': Q
            })
            
    except Exception as e:
        print(f"\n❌ 求解失败: {str(e)}")
        results.append({
            'scheme': scheme,
            'success': False,
            'Q': Q,
            'error': str(e)
        })

# 筛选成功的结果
successful_results = [r for r in results if r['success']]

if len(successful_results) > 0:
    # 综合对比
    print(f"\n" + "=" * 80)
    print("综合对比分析")
    print("=" * 80)
    
    print(f"\n{'工况':<12} {'流量':<12} {'最大水深':<12} {'超高':<12} {'Froude数':<12} {'风险等级':<15}")
    print(f"{'':12} {'(m³/s)':<12} {'(m)':<12} {'(m)':<12} {'':<12} {'':<15}")
    print("-" * 85)
    
    for result in successful_results:
        name = result['scheme']['name']
        Q = result['Q']
        h_max = result['h_max']
        freeboard = result['freeboard']
        Fr = result['Fr']
        risk_level = result['risk_level']
        
        print(f"{name:<12} {Q:<12.1f} {h_max:<12.3f} {freeboard:<12.3f} {Fr:<12.3f} {risk_level:<15}")
    
    # 确定安全流量上限
    print(f"\n安全流量分析:")
    
    safe_results = [r for r in successful_results if r['freeboard'] > 1.0]
    
    if safe_results:
        max_safe_Q = max([r['Q'] for r in safe_results])
        print(f"  ✅ 安全流量上限: {max_safe_Q} m³/s（超高>1.0m）")
    else:
        print(f"  ⚠️ 无完全安全工况")
    
    marginal_results = [r for r in successful_results if 0.5 < r['freeboard'] <= 1.0]
    if marginal_results:
        print(f"  🟡 中等风险流量: {min([r['Q'] for r in marginal_results])}-{max([r['Q'] for r in marginal_results])} m³/s")
    
    # 可视化
    try:
        fig, axes = plt.subplots(2, 2, figsize=(15, 10))
        
        # 子图1: 纵断面水深对比
        ax1 = axes[0, 0]
        for result in successful_results:
            ax1.plot(result['x']/1000, result['h'],
                    label=f"{result['scheme']['name']} (Q={result['Q']:.0f})",
                    color=result['scheme']['color'], linewidth=2)
        ax1.axhline(y=h_bank, color='black', linestyle='--', linewidth=2, label='堤顶高度')
        ax1.set_xlabel('距离 (km)')
        ax1.set_ylabel('水深 (m)')
        ax1.set_title('纵断面水深对比')
        ax1.legend()
        ax1.grid(True, alpha=0.3)
        
        # 子图2: 流量-水深关系
        ax2 = axes[0, 1]
        Qs = [r['Q'] for r in successful_results]
        h_maxs = [r['h_max'] for r in successful_results]
        colors = [r['scheme']['color'] for r in successful_results]
        
        ax2.scatter(Qs, h_maxs, c=colors, s=200, alpha=0.7, edgecolors='black', linewidths=2)
        ax2.axhline(y=h_bank, color='black', linestyle='--', linewidth=2, label='堤顶高度')
        ax2.axhline(y=h_bank-1.0, color='green', linestyle=':', linewidth=1.5, alpha=0.5, label='安全线')
        ax2.set_xlabel('流量 (m³/s)')
        ax2.set_ylabel('最大水深 (m)')
        ax2.set_title('流量-水深关系')
        ax2.legend()
        ax2.grid(True, alpha=0.3)
        
        # 子图3: 安全余量对比
        ax3 = axes[1, 0]
        names = [r['scheme']['name'] for r in successful_results]
        freeboards = [r['freeboard'] for r in successful_results]
        colors = [r['scheme']['color'] for r in successful_results]
        
        bars = ax3.bar(range(len(names)), freeboards, color=colors, alpha=0.7, edgecolor='black', linewidth=2)
        ax3.axhline(y=1.0, color='green', linestyle='--', linewidth=2, label='安全阈值(1.0m)')
        ax3.axhline(y=0.5, color='orange', linestyle='--', linewidth=1.5, label='警戒阈值(0.5m)')
        ax3.set_xticks(range(len(names)))
        ax3.set_xticklabels(names)
        ax3.set_ylabel('超高（安全余量） (m)')
        ax3.set_title('安全余量对比')
        ax3.legend()
        ax3.grid(True, alpha=0.3, axis='y')
        
        for bar, val in zip(bars, freeboards):
            ax3.text(bar.get_x() + bar.get_width()/2, val + 0.1,
                    f'{val:.2f}m', ha='center', va='bottom', fontweight='bold')
        
        # 子图4: 风险等级分布
        ax4 = axes[1, 1]
        ax4.axis('off')
        
        y_pos = 0.9
        ax4.text(0.5, y_pos, '风险评估总结', ha='center', fontsize=14, fontweight='bold')
        y_pos -= 0.15
        
        for result in successful_results:
            name = result['scheme']['name']
            risk = result['risk_level']
            Q = result['Q']
            freeboard = result['freeboard']
            
            ax4.text(0.1, y_pos, f"{name} (Q={Q:.0f} m³/s): {risk}",
                    fontsize=11)
            y_pos -= 0.10
            ax4.text(0.15, y_pos, f"超高: {freeboard:.2f} m",
                    fontsize=9, color='gray')
            y_pos -= 0.12
        
        plt.tight_layout()
        plt.savefig('/workspace/case02_flood_risk_assessment.png', dpi=150, bbox_inches='tight')
        print(f"\n📊 分析图表已保存: case02_flood_risk_assessment.png")
    except Exception as e:
        print(f"\n⚠️ 可视化失败: {str(e)}")
    
    # 工程建议
    print(f"\n" + "=" * 80)
    print("工程建议")
    print("=" * 80)
    
    print(f"\n1. 运行调度:")
    if safe_results:
        print(f"   • 正常运行: 流量≤{max([r['Q'] for r in safe_results])} m³/s")
        print(f"   • 监测水位，保持超高>1.0m")
    
    print(f"\n2. 预警响应:")
    print(f"   • 黄色预警: 水深>{h_bank-1.0:.1f}m")
    print(f"   • 红色预警: 水深>{h_bank-0.5:.1f}m")
    print(f"   • 立即响应: 水深>{h_bank:.1f}m")
    
    print(f"\n3. 工程措施:")
    if any(r['freeboard'] < 1.0 for r in successful_results):
        print(f"   • 建议加固堤防或拓宽渠道")
    print(f"   • 设置水位监测站")
    print(f"   • 制定应急预案")
    
else:
    print(f"\n⚠️ 所有工况求解失败")

# 成功率统计
success_count = len(successful_results)
total_count = len(schemes)
success_rate = success_count / total_count * 100

print(f"\n" + "=" * 80)
print(f"✅ 防洪风险评估完成！")
print(f"✅ 成功率: {success_rate:.0f}% ({success_count}/{total_count})")
print("=" * 80)
