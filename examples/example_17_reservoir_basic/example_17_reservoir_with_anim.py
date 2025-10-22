#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
示例17: 水库调度 - 增强版（嵌入式动画）

演示水库的入流、出流和水位动态变化

使用方法:
    python example_17_reservoir_with_anim.py              # 不生成动画
    python example_17_reservoir_with_anim.py --animate    # 生成动画

作者: Claude
日期: 2025-10-22
"""

import sys, os
import numpy as np
import argparse
import matplotlib.pyplot as plt

EXAMPLES_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, EXAMPLES_DIR)
from animation_utils import AnimationGenerator

def parse_args():
    parser = argparse.ArgumentParser(description='水库调度仿真 - 嵌入式动画版本')
    parser.add_argument('--animate', action='store_true', help='生成动画')
    parser.add_argument('--animation-fps', type=int, default=10)
    parser.add_argument('--animation-dpi', type=int, default=100)
    return parser.parse_args()

def run_example(args):
    print("\n" + "="*80)
    print("示例17: 水库调度 - 增强版（嵌入式动画）")
    print("="*80)
    
    # 仿真参数（24小时，每小时一个时间步）
    hours = np.arange(0, 24, 0.5)
    n_steps = len(hours)
    
    # 入流（模拟日变化）
    inflow = 100 + 50 * np.sin(2*np.pi*hours/24 + np.pi/2)
    
    # 出流（调度策略：白天多发电）
    outflow = 80 + 30 * np.sin(2*np.pi*hours/24 - np.pi/6)
    
    # 水位（基于入流出流计算）
    level = np.zeros(n_steps)
    level[0] = 100.0  # 初始水位100m
    
    for i in range(1, n_steps):
        dt = 0.5  # 0.5小时
        # 简化：水位变化 = (入流 - 出流) / 水库面积
        area = 1000000  # 100万平方米
        dlevel = (inflow[i] - outflow[i]) * 3600 * dt / area
        level[i] = level[i-1] + dlevel
    
    # 蓄水量
    storage = (level - 50) * 1000000  # 相对于死水位的蓄水量
    
    # 生成静态图表
    output_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "outputs", "figures")
    os.makedirs(output_dir, exist_ok=True)
    
    fig, axes = plt.subplots(4, 1, figsize=(12, 12))
    
    axes[0].plot(hours, inflow, 'b-', linewidth=2)
    axes[0].set_ylabel('Inflow (m³/s)')
    axes[0].set_title('Reservoir Operation - Inflow')
    axes[0].grid(True, alpha=0.3)
    
    axes[1].plot(hours, outflow, 'r-', linewidth=2)
    axes[1].set_ylabel('Outflow (m³/s)')
    axes[1].set_title('Outflow (Power Generation)')
    axes[1].grid(True, alpha=0.3)
    
    axes[2].plot(hours, level, 'g-', linewidth=2)
    axes[2].set_ylabel('Water Level (m)')
    axes[2].set_title('Reservoir Water Level')
    axes[2].grid(True, alpha=0.3)
    
    axes[3].plot(hours, storage/1e6, 'm-', linewidth=2)
    axes[3].set_ylabel('Storage (Million m³)')
    axes[3].set_xlabel('Time (hours)')
    axes[3].set_title('Water Storage')
    axes[3].grid(True, alpha=0.3)
    
    plt.tight_layout()
    fig_path = os.path.join(output_dir, 'reservoir_operation.png')
    plt.savefig(fig_path, dpi=150, bbox_inches='tight')
    plt.close()
    
    print(f"\n✓ 静态图表已保存: {fig_path}")
    
    # 生成动画
    if args.animate:
        animation_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "outputs", "animations")
        anim_gen = AnimationGenerator(output_dir=animation_dir, fps=args.animation_fps, dpi=args.animation_dpi)
        
        try:
            gif_path = anim_gen.create_timeseries_animation(
                t=hours,
                data={
                    'Inflow': inflow,
                    'Outflow': outflow,
                    'Water Level': level,
                    'Storage': storage/1e6,
                },
                filename='reservoir_operation_embedded.gif',
                title='Reservoir Operation (24h)',
                xlabel='Time (hours)',
                ylabels={
                    'Inflow': 'Flow (m³/s)',
                    'Outflow': 'Flow (m³/s)',
                    'Water Level': 'Level (m)',
                    'Storage': 'Storage (Mm³)',
                },
                layout=(2, 2)
            )
            print(f"✓ 动画已保存: {os.path.basename(gif_path)}")
        except Exception as e:
            print(f"✗ 动画生成失败: {e}")
    
    print("\n✅ 示例17（增强版）运行成功")

if __name__ == "__main__":
    args = parse_args()
    run_example(args)
