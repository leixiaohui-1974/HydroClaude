#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
明渠串联闸泵群系统模拟结果稳定性分析

使用基础库的StabilityEvaluator对模拟结果进行数值稳定性评估

作者: Claude
日期: 2025-10-23
"""

import sys
import os

# 路径设置
script_path = os.path.abspath(__file__)
project_root = os.path.dirname(os.path.dirname(os.path.dirname(script_path)))
sys.path.insert(0, project_root)

import numpy as np
import matplotlib.pyplot as plt
from utils.stability_evaluator import StabilityEvaluator

def load_data():
    """加载模拟数据"""
    results_dir = os.path.join(project_root, "examples", "example_gate_pump_cascade", "results")

    # 加载稳态数据
    steady_data = np.load(os.path.join(results_dir, "steady_state_data.npz"))
    x = steady_data['x']
    h_steady = steady_data['h']
    q_steady = steady_data['q']
    gate1_pos = steady_data['gate1_pos']
    pump_pos = steady_data['pump_pos']
    gate2_pos = steady_data['gate2_pos']

    # 加载瞬态数据
    transient_data = np.load(os.path.join(results_dir, "transient_data.npz"))
    time = transient_data['time']
    h_history = transient_data['h_history']
    q_history = transient_data['q_history']
    Q_initial = transient_data['Q_initial']
    Q_step = transient_data['Q_step']

    return {
        'x': x,
        'h_steady': h_steady,
        'q_steady': q_steady,
        'gate1_pos': gate1_pos,
        'pump_pos': pump_pos,
        'gate2_pos': gate2_pos,
        'time': time,
        'h_history': h_history,
        'q_history': q_history,
        'Q_initial': Q_initial,
        'Q_step': Q_step
    }

def analyze_structure_vicinity(data):
    """分析结构物附近的水位分布"""
    print("=" * 90)
    print("结构物附近水位分析")
    print("=" * 90)
    print()

    x = data['x']
    h_steady = data['h_steady']
    gate1_pos = data['gate1_pos']
    pump_pos = data['pump_pos']
    gate2_pos = data['gate2_pos']

    structures = [
        ('Gate1', gate1_pos),
        ('Pump', pump_pos),
        ('Gate2', gate2_pos)
    ]

    for name, pos in structures:
        # 找到结构物位置的索引
        idx = np.argmin(np.abs(x - pos))

        # 提取前后各10个网格点（约2km）
        window = 10
        idx_start = max(0, idx - window)
        idx_end = min(len(x), idx + window + 1)

        x_local = x[idx_start:idx_end]
        h_local = h_steady[idx_start:idx_end]

        # 计算局部水深梯度
        dh_dx = np.gradient(h_local, x_local)
        d2h_dx2 = np.gradient(dh_dx, x_local)

        # 统计
        h_at_structure = h_steady[idx]
        h_upstream = h_steady[max(0, idx-5)]
        h_downstream = h_steady[min(len(x)-1, idx+5)]
        dh_structure = h_upstream - h_downstream
        max_gradient = np.max(np.abs(dh_dx))
        max_curvature = np.max(np.abs(d2h_dx2))

        print(f"### {name} (位置: {pos/1000:.1f} km, 索引: {idx}) ###")
        print(f"  结构物处水深: {h_at_structure:.4f} m")
        print(f"  上游水深 (-1km): {h_upstream:.4f} m")
        print(f"  下游水深 (+1km): {h_downstream:.4f} m")
        print(f"  水深跃变: {dh_structure:.4f} m")
        print(f"  最大梯度: {max_gradient:.6f} m/m")
        print(f"  最大曲率: {max_curvature:.8f} 1/m")

        # 检查是否有尖峰
        if max_curvature > 1e-6:
            print(f"  ⚠️  警告: 检测到显著曲率变化，可能存在数值尖峰")

        # 检查梯度是否异常陡峭
        if max_gradient > 0.01:
            print(f"  ⚠️  警告: 水深梯度异常陡峭 (>{0.01:.4f} m/m)")

        print()

def analyze_spatial_oscillations(data):
    """分析空间振荡"""
    print("=" * 90)
    print("空间振荡分析")
    print("=" * 90)
    print()

    x = data['x']
    h_steady = data['h_steady']

    # 计算二阶空间差分（检测高频空间振荡）
    d2h = np.diff(h_steady, n=2)

    # 统计
    d2h_std = np.std(d2h)
    d2h_max = np.max(np.abs(d2h))

    print(f"二阶空间差分统计:")
    print(f"  标准差: {d2h_std:.8f} m")
    print(f"  最大值: {d2h_max:.8f} m")

    # 检测尖峰位置
    threshold = 3 * d2h_std  # 3-sigma规则
    spike_indices = np.where(np.abs(d2h) > threshold)[0]

    if len(spike_indices) > 0:
        print(f"\n  ⚠️  检测到 {len(spike_indices)} 个可能的空间尖峰 (超过3σ阈值):")
        for i in spike_indices[:5]:  # 只显示前5个
            x_spike = x[i+1]  # +1因为二阶差分索引偏移
            print(f"     位置: {x_spike/1000:.3f} km, 二阶差分: {d2h[i]:.8f} m")
    else:
        print(f"  ✅ 未检测到显著空间尖峰")

    print()

def stability_analysis(data):
    """使用StabilityEvaluator进行综合稳定性分析"""
    print("=" * 90)
    print("数值稳定性综合评估 (使用StabilityEvaluator)")
    print("=" * 90)
    print()

    # 准备数据
    time = data['time']
    h_history_list = [data['h_history'][i, :] for i in range(len(time))]
    q_history_list = [data['q_history'][i, :] for i in range(len(time))]

    canal_params = {
        'length': data['x'][-1],
        'width': 15.0,  # B = 15m
        'slope': 0.0001,  # S0 = 0.0001
        'manning_n': 0.025,
        'nx': len(data['x'])
    }

    # 创建评估器
    evaluator = StabilityEvaluator()

    # 评估
    result = evaluator.evaluate(
        time=time,
        h_history=h_history_list,
        Q_history=q_history_list,
        canal_params=canal_params,
        method_name="HydrostaticCanalSolver_Gate-Pump-Cascade"
    )

    # 打印报告
    evaluator.print_report()

    return evaluator, result

def plot_detailed_profile(data):
    """绘制详细的纵剖面图，重点关注结构物附近"""
    print("=" * 90)
    print("生成详细纵剖面分析图")
    print("=" * 90)
    print()

    x = data['x']
    h_steady = data['h_steady']
    gate1_pos = data['gate1_pos']
    pump_pos = data['pump_pos']
    gate2_pos = data['gate2_pos']

    output_dir = os.path.join(project_root, "examples", "example_gate_pump_cascade", "results")

    # 创建3个子图：全局 + 3个结构物局部
    fig = plt.figure(figsize=(18, 12))

    # 子图1: 全局纵剖面
    ax1 = plt.subplot(3, 2, (1, 2))
    ax1.plot(x / 1000, h_steady, 'b-', linewidth=2, label='Water Depth')

    # 标注结构物
    for pos, name in [(gate1_pos, 'Gate1'), (pump_pos, 'Pump'), (gate2_pos, 'Gate2')]:
        ax1.axvline(pos/1000, color='red', linestyle='--', linewidth=1.5, alpha=0.5)
        ax1.text(pos/1000, np.max(h_steady) * 0.98, name,
                color='red', fontsize=10, ha='center', va='top',
                bbox=dict(boxstyle='round', facecolor='white', alpha=0.8))

    ax1.set_xlabel('Distance (km)', fontsize=12)
    ax1.set_ylabel('Water Depth (m)', fontsize=12)
    ax1.set_title('Full Longitudinal Profile', fontsize=14, fontweight='bold')
    ax1.grid(True, alpha=0.3)
    ax1.legend(fontsize=11)

    # 子图2-4: 各结构物局部放大
    structures = [
        ('Gate1', gate1_pos, 3),
        ('Pump', pump_pos, 4),
        ('Gate2', gate2_pos, 5)
    ]

    for name, pos, subplot_idx in structures:
        ax = plt.subplot(3, 2, subplot_idx)

        # 找到结构物位置的索引
        idx = np.argmin(np.abs(x - pos))

        # 提取前后各20个网格点（约4km）
        window = 20
        idx_start = max(0, idx - window)
        idx_end = min(len(x), idx + window + 1)

        x_local = x[idx_start:idx_end]
        h_local = h_steady[idx_start:idx_end]

        ax.plot(x_local / 1000, h_local, 'b-', linewidth=2, marker='o', markersize=3)
        ax.axvline(pos/1000, color='red', linestyle='--', linewidth=2, alpha=0.7, label='Structure')

        ax.set_xlabel('Distance (km)', fontsize=10)
        ax.set_ylabel('Water Depth (m)', fontsize=10)
        ax.set_title(f'{name} Vicinity (±4 km)', fontsize=12, fontweight='bold')
        ax.grid(True, alpha=0.3)
        ax.legend(fontsize=9)

        # 标注最大最小值
        h_min_local = np.min(h_local)
        h_max_local = np.max(h_local)
        idx_min = np.argmin(h_local)
        idx_max = np.argmax(h_local)

        ax.plot(x_local[idx_min]/1000, h_min_local, 'go', markersize=8, label=f'Min: {h_min_local:.4f}m')
        ax.plot(x_local[idx_max]/1000, h_max_local, 'ro', markersize=8, label=f'Max: {h_max_local:.4f}m')
        ax.legend(fontsize=8, loc='best')

    # 子图6: 水深梯度分布
    ax6 = plt.subplot(3, 2, 6)
    dh_dx = np.gradient(h_steady, x)
    ax6.plot(x / 1000, dh_dx, 'g-', linewidth=2)

    # 标注结构物
    for pos, name in [(gate1_pos, 'Gate1'), (pump_pos, 'Pump'), (gate2_pos, 'Gate2')]:
        ax6.axvline(pos/1000, color='red', linestyle='--', linewidth=1.5, alpha=0.5)

    ax6.axhline(0, color='black', linestyle=':', linewidth=1, alpha=0.5)
    ax6.set_xlabel('Distance (km)', fontsize=10)
    ax6.set_ylabel('Water Depth Gradient (m/m)', fontsize=10)
    ax6.set_title('Water Depth Gradient Distribution', fontsize=12, fontweight='bold')
    ax6.grid(True, alpha=0.3)

    plt.tight_layout()

    output_file = os.path.join(output_dir, "07_stability_analysis_detailed_profile.png")
    fig.savefig(output_file, dpi=150, bbox_inches='tight')
    plt.close(fig)

    print(f"  Saved: {output_file}")
    print()

def main():
    """主函数"""
    print("=" * 90)
    print("明渠串联闸泵群系统模拟结果稳定性分析".center(90))
    print("=" * 90)
    print()

    # 加载数据
    print("▶ 加载模拟数据...")
    data = load_data()
    print(f"  ✓ 已加载稳态数据: {len(data['x'])} 个空间点")
    print(f"  ✓ 已加载瞬态数据: {len(data['time'])} 个时间点")
    print()

    # 分析结构物附近水位
    analyze_structure_vicinity(data)

    # 分析空间振荡
    analyze_spatial_oscillations(data)

    # 稳定性综合评估
    evaluator, result = stability_analysis(data)

    # 生成详细纵剖面图
    plot_detailed_profile(data)

    # 总结
    print("=" * 90)
    print("分析总结")
    print("=" * 90)
    print()

    if result['success']:
        print(f"数值稳定性评分: {result['score']:.1f}/100 ({result['stability']})")
        print()

        print("关键指标:")
        print(f"  • 振荡指数: {result['oscillation_index']:.6f} {'✅ 优秀' if result['oscillation_index'] < 0.01 else '⚠️  偏高'}")
        print(f"  • 质量守恒误差: {result['mass_error']:.2f}% {'✅ 优秀' if result['mass_error'] < 5.0 else '⚠️  偏高'}")
        print(f"  • 物理合理性: {result['physical_validity']:.3f} {'✅ 优秀' if result['physical_validity'] > 0.9 else '⚠️  需改进'}")
        print(f"  • 收敛性指数: {result['convergence_index']:.3f} {'✅ 优秀' if result['convergence_index'] > 0.8 else '⚠️  需改进'}")
        print()

        if result['score'] >= 70:
            print("✅ 结论: 模拟结果数值稳定，可信度高")
        elif result['score'] >= 50:
            print("⚠️  结论: 模拟结果基本稳定，建议进一步优化")
        else:
            print("❌ 结论: 模拟结果存在稳定性问题，需要改进")
    else:
        print(f"❌ 稳定性评估失败: {result['message']}")

    print()
    print("=" * 90)
    print("分析完成".center(90))
    print("=" * 90)

if __name__ == "__main__":
    main()
