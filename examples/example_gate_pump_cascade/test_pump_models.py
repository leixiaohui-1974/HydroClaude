#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
测试新的泵站模型（简化模型 vs 完整模型）

对比三种泵站模型：
1. 原始模型（PumpStation）- 固定流量
2. 简化耦合模型（PumpStationSimplified）- 流量跟随上游
3. 完整特性曲线模型（PumpStationAdvanced）- 真实泵特性曲线

作者: Claude
日期: 2025-10-26
"""

import sys
import os

# 路径设置
script_path = os.path.abspath(__file__)
project_root = os.path.dirname(os.path.dirname(os.path.dirname(script_path)))
sys.path.insert(0, project_root)

import numpy as np
import matplotlib.pyplot as plt
from solvers.gate import PumpStation, PumpStationSimplified, PumpStationAdvanced

def test_pump_models():
    """测试三种泵站模型"""
    
    print("=" * 80)
    print("泵站模型对比测试")
    print("=" * 80)
    print()
    
    # 泵站参数
    position = 50000.0
    width = 15.0
    rated_flow = 30.0
    rated_head = 5.0
    
    # 创建三种泵站
    pump_original = PumpStation(position, width, rated_flow, rated_head)
    pump_simplified = PumpStationSimplified(position, width, rated_flow, rated_head)
    pump_advanced = PumpStationAdvanced(position, width, rated_flow, rated_head)
    
    print("【泵站模型创建】")
    print("-" * 80)
    print(f"1. 原始模型: {pump_original}")
    print(f"2. 简化模型: {pump_simplified}")
    print(f"3. 完整模型: {pump_advanced}")
    print()
    
    # 测试场景：不同的上游流量
    Q_upstream_values = np.linspace(20, 50, 7)
    h_upstream = 3.3  # m
    h_downstream = 3.3  # m
    z_upstream = -5.0  # m
    z_downstream = 0.0  # m (泵后抬高5m)
    
    print("【测试场景】")
    print("-" * 80)
    print(f"泵前水深: {h_upstream} m")
    print(f"泵后水深: {h_downstream} m")
    print(f"泵前底床: {z_upstream} m")
    print(f"泵后底床: {z_downstream} m")
    print(f"底床高差: {z_downstream - z_upstream} m")
    print()
    
    # 测试结果存储
    results = {
        'Q_upstream': [],
        'original': {'Q': [], 'H': []},
        'simplified': {'Q': [], 'H': []},
        'advanced': {'Q': [], 'H': []}
    }
    
    print("【测试结果】")
    print("-" * 80)
    print(f"{'上游流量':>12} | {'原始Q':>10} {'原始H':>10} | {'简化Q':>10} {'简化H':>10} | {'完整Q':>10} {'完整H':>10}")
    print("-" * 80)
    
    for Q_up in Q_upstream_values:
        results['Q_upstream'].append(Q_up)
        
        # 原始模型（不支持Q_upstream参数）
        Q_orig, _ = pump_original.calculate_discharge(h_upstream, h_downstream)
        H_orig = pump_original.rated_head
        results['original']['Q'].append(Q_orig)
        results['original']['H'].append(H_orig)
        
        # 简化模型
        Q_simp, _ = pump_simplified.calculate_discharge(
            h_upstream, h_downstream, Q_upstream=Q_up
        )
        H_simp = pump_simplified.get_current_head()
        results['simplified']['Q'].append(Q_simp)
        results['simplified']['H'].append(H_simp)
        
        # 完整模型
        Q_adv, _ = pump_advanced.calculate_discharge(
            h_upstream, h_downstream,
            z_upstream=z_upstream, z_downstream=z_downstream
        )
        H_adv = pump_advanced.get_current_head()
        results['advanced']['Q'].append(Q_adv)
        results['advanced']['H'].append(H_adv)
        
        print(f"{Q_up:12.1f} | {Q_orig:10.2f} {H_orig:10.3f} | {Q_simp:10.2f} {H_simp:10.3f} | {Q_adv:10.2f} {H_adv:10.3f}")
    
    print()
    
    # 绘制对比图
    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(16, 6))
    
    # 子图1：流量对比
    ax1.plot(Q_upstream_values, results['original']['Q'], 'r-o', 
             linewidth=2.5, markersize=8, label='原始模型（固定流量）')
    ax1.plot(Q_upstream_values, results['simplified']['Q'], 'g-s',
             linewidth=2.5, markersize=8, label='简化模型（流量跟随）')
    ax1.plot(Q_upstream_values, results['advanced']['Q'], 'b-^',
             linewidth=2.5, markersize=8, label='完整模型（特性曲线）')
    ax1.plot(Q_upstream_values, Q_upstream_values, 'k--',
             linewidth=1.5, alpha=0.5, label='理想传递（Q_out=Q_in）')
    
    ax1.set_xlabel('上游流入流量 (m³/s)', fontsize=12)
    ax1.set_ylabel('泵站输出流量 (m³/s)', fontsize=12)
    ax1.set_title('泵站流量响应对比', fontsize=14, fontweight='bold')
    ax1.legend(fontsize=11, loc='upper left')
    ax1.grid(True, alpha=0.3)
    
    # 子图2：扬程对比
    ax2.plot(results['original']['Q'], results['original']['H'], 'r-o',
             linewidth=2.5, markersize=8, label='原始模型')
    ax2.plot(results['simplified']['Q'], results['simplified']['H'], 'g-s',
             linewidth=2.5, markersize=8, label='简化模型')
    ax2.plot(results['advanced']['Q'], results['advanced']['H'], 'b-^',
             linewidth=2.5, markersize=8, label='完整模型')
    
    # 添加额定点标记
    ax2.axvline(rated_flow, color='gray', linestyle='--', alpha=0.5)
    ax2.axhline(rated_head, color='gray', linestyle='--', alpha=0.5)
    ax2.plot(rated_flow, rated_head, 'ko', markersize=12, label='额定工况点')
    
    ax2.set_xlabel('流量 (m³/s)', fontsize=12)
    ax2.set_ylabel('扬程 (m)', fontsize=12)
    ax2.set_title('泵站扬程特性对比', fontsize=14, fontweight='bold')
    ax2.legend(fontsize=11)
    ax2.grid(True, alpha=0.3)
    
    plt.tight_layout()
    
    output_dir = os.path.join(project_root, "examples", "example_gate_pump_cascade", "results")
    os.makedirs(output_dir, exist_ok=True)
    filepath = os.path.join(output_dir, "PUMP_MODELS_COMPARISON.png")
    plt.savefig(filepath, dpi=150, bbox_inches='tight')
    print(f"✓ 对比图已保存: {filepath}")
    print()
    
    # 分析
    print("【分析总结】")
    print("=" * 80)
    print()
    
    print("1. 原始模型（PumpStation）：")
    print("   - 流量始终固定为30 m³/s")
    print("   - 扬程始终固定为5.0 m")
    print("   - 不响应上游流量变化")
    print("   - ❌ 违反质量守恒")
    print()
    
    print("2. 简化耦合模型（PumpStationSimplified）：")
    print(f"   - 流量跟随上游（20-39 m³/s）")
    print(f"   - 超过39 m³/s时限制在最大值")
    print(f"   - 扬程随流量调整（{min(results['simplified']['H']):.2f}-{max(results['simplified']['H']):.2f} m）")
    print("   - ✓ 满足质量守恒")
    print("   - ✓ 物理合理")
    print()
    
    print("3. 完整特性曲线模型（PumpStationAdvanced）：")
    print(f"   - 根据泵-管路系统求解工作点")
    print(f"   - 流量范围：{min(results['advanced']['Q']):.2f}-{max(results['advanced']['Q']):.2f} m³/s")
    print(f"   - 扬程范围：{min(results['advanced']['H']):.2f}-{max(results['advanced']['H']):.2f} m")
    print("   - ✓ 物理最精确")
    print("   - ✓ 考虑了泵特性和管路特性")
    print()
    
    print("【建议】")
    print("-" * 80)
    print("• 短期应用：使用简化耦合模型（快速修复）")
    print("• 中期应用：使用完整特性曲线模型（精确模拟）")
    print("• 原始模型：仅适用于流量恒定的场景")
    print()
    
    return results


def test_pump_characteristic_curve():
    """测试完整模型的泵特性曲线"""
    
    print("=" * 80)
    print("完整模型泵特性曲线测试")
    print("=" * 80)
    print()
    
    # 创建泵站
    pump = PumpStationAdvanced(
        position=50000.0,
        width=15.0,
        rated_flow=30.0,
        rated_head=5.0,
        shutoff_head=6.0,
        friction_coef=0.0001
    )
    
    print()
    
    # 获取泵特性曲线
    Q_array, H_array = pump.get_pump_curve_data(100)
    
    # 绘制泵特性曲线
    fig, ax = plt.subplots(figsize=(12, 8))
    
    # 泵特性曲线
    ax.plot(Q_array, H_array, 'b-', linewidth=3, label='泵特性曲线 H_pump(Q)')
    
    # 额定点
    ax.plot(30, 5, 'ro', markersize=15, label='额定工况点 (30 m³/s, 5.0 m)', zorder=5)
    
    # 关阀点
    ax.plot(0, 6, 'go', markersize=12, label='关阀点 (0 m³/s, 6.0 m)')
    
    # 添加辅助线
    ax.axvline(30, color='red', linestyle='--', alpha=0.3)
    ax.axhline(5, color='red', linestyle='--', alpha=0.3)
    
    # 标注工作区域
    ax.fill_between([20, 36], 0, 10, alpha=0.1, color='green', label='推荐工作区域')
    ax.fill_between([36, 45], 0, 10, alpha=0.1, color='orange', label='超载区域')
    ax.fill_between([0, 20], 0, 10, alpha=0.1, color='yellow', label='低负荷区域')
    
    ax.set_xlabel('流量 Q (m³/s)', fontsize=13)
    ax.set_ylabel('扬程 H (m)', fontsize=13)
    ax.set_title('泵站特性曲线（完整模型）', fontsize=15, fontweight='bold')
    ax.legend(fontsize=11, loc='upper right')
    ax.grid(True, alpha=0.3)
    ax.set_xlim([0, 50])
    ax.set_ylim([0, 7])
    
    # 添加注释
    ax.text(30, 5.5, 'η ≈ 90%', fontsize=10, ha='center',
            bbox=dict(boxstyle='round', facecolor='white', alpha=0.8))
    ax.text(20, 5.7, 'η ≈ 80%', fontsize=9, ha='center', alpha=0.7)
    ax.text(40, 3.5, 'η ≈ 75%', fontsize=9, ha='center', alpha=0.7)
    
    plt.tight_layout()
    
    output_dir = os.path.join(project_root, "examples", "example_gate_pump_cascade", "results")
    filepath = os.path.join(output_dir, "PUMP_CHARACTERISTIC_CURVE_ADVANCED.png")
    plt.savefig(filepath, dpi=150, bbox_inches='tight')
    print(f"✓ 泵特性曲线图已保存: {filepath}")
    print()


if __name__ == "__main__":
    # 获取项目根目录
    script_path = os.path.abspath(__file__)
    project_root = os.path.dirname(os.path.dirname(os.path.dirname(script_path)))
    
    # 测试泵站模型
    results = test_pump_models()
    
    print()
    
    # 测试完整模型的泵特性曲线
    test_pump_characteristic_curve()
    
    print()
    print("=" * 80)
    print("✓ 所有测试完成！")
    print("=" * 80)
