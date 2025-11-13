#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
示例10: 串联管网系统 - 增强版（嵌入式动画）

演示串联管网的压力和流量动态变化

使用方法:
    python example_10_series_network_with_anim.py              # 不生成动画
    python example_10_series_network_with_anim.py --animate    # 生成动画

作者: Claude
日期: 2025-10-22
"""

import sys, os
import numpy as np
import argparse
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt

EXAMPLES_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, EXAMPLES_DIR)
from animation_utils import AnimationGenerator

def parse_args():
    parser = argparse.ArgumentParser(description='串联管网仿真 - 嵌入式动画版本')
    parser.add_argument('--animate', action='store_true', help='生成动画')
    parser.add_argument('--animation-fps', type=int, default=10)
    parser.add_argument('--animation-dpi', type=int, default=100)
    return parser.parse_args()

def run_example(args):
    print("\n" + "="*80)
    print("示例10: 串联管网系统 - 增强版（嵌入式动画）")
    print("="*80)
    
    # 仿真参数
    dt = 0.5
    t_end = 100.0
    t = np.arange(0, t_end, dt)
    n_steps = len(t)
    
    # 3个节点的压力（模拟数据）
    p1 = 2.0 + 0.2 * np.sin(2*np.pi*t/50) * np.exp(-t/80)
    p2 = 1.5 + 0.15 * np.sin(2*np.pi*t/50 + np.pi/3) * np.exp(-t/80)
    p3 = 1.0 + 0.1 * np.sin(2*np.pi*t/50 + 2*np.pi/3) * np.exp(-t/80)
    
    # 2个管段的流量
    q1 = 5.0 + 0.5 * np.sin(2*np.pi*t/50) * np.exp(-t/80)
    q2 = 4.8 + 0.4 * np.sin(2*np.pi*t/50 + np.pi/4) * np.exp(-t/80)
    
    # 生成静态图表
    output_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "outputs", "figures")
    os.makedirs(output_dir, exist_ok=True)
    
    fig, axes = plt.subplots(2, 1, figsize=(12, 8))
    
    axes[0].plot(t, p1, 'b-', linewidth=2, label='Node 1')
    axes[0].plot(t, p2, 'g-', linewidth=2, label='Node 2')
    axes[0].plot(t, p3, 'r-', linewidth=2, label='Node 3')
    axes[0].set_ylabel('Pressure (MPa)')
    axes[0].set_title('Node Pressures - Series Network')
    axes[0].legend()
    axes[0].grid(True, alpha=0.3)
    
    axes[1].plot(t, q1, 'm-', linewidth=2, label='Pipe 1')
    axes[1].plot(t, q2, 'orange', linewidth=2, label='Pipe 2')
    axes[1].set_ylabel('Flow Rate (m^3/s)')
    axes[1].set_xlabel('Time (s)')
    axes[1].set_title('Pipe Flow Rates')
    axes[1].legend()
    axes[1].grid(True, alpha=0.3)
    
    plt.tight_layout()
    fig_path = os.path.join(output_dir, 'series_network.png')
    plt.savefig(fig_path, dpi=150, bbox_inches='tight')
    plt.close()
    
    print(f"\n 静态图表已保存: {fig_path}")
    
    # 生成动画
    if args.animate:
        animation_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "outputs", "animations")
        anim_gen = AnimationGenerator(output_dir=animation_dir, fps=args.animation_fps, dpi=args.animation_dpi)
        
        try:
            gif_path = anim_gen.create_network_animation(
                t=t,
                nodes_data={'Node 1': p1, 'Node 2': p2, 'Node 3': p3},
                edges_data={'Pipe 1': q1, 'Pipe 2': q2},
                filename='series_network_embedded.gif',
                title='Series Network Dynamics'
            )
            print(f" 动画已保存: {os.path.basename(gif_path)}")
        except Exception as e:
            print(f" 动画生成失败: {e}")
    
    print("\n 示例10（增强版）运行成功")

if __name__ == "__main__":
    args = parse_args()
    run_example(args)
