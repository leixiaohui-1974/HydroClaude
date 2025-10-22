#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
示例2: 泵站系统 - 增强版（嵌入式动画）

演示泵站启动过程的动态行为

使用方法:
    python example_02_pump_system_with_anim.py              # 不生成动画
    python example_02_pump_system_with_anim.py --animate    # 生成动画

作者: Claude
日期: 2025-10-22
"""

import sys
import os
import numpy as np
import argparse
import matplotlib.pyplot as plt

# 添加项目根目录
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))))

from physics.tank import Tank
from physics.pump import Pump
from physics.pipe import Pipe
from simulation.plant_simulator import PlantSimulator

# 导入动画工具
EXAMPLES_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, EXAMPLES_DIR)
from animation_utils import AnimationGenerator


def parse_args():
    """解析命令行参数"""
    parser = argparse.ArgumentParser(
        description='泵站系统仿真 - 嵌入式动画版本'
    )
    parser.add_argument('--animate', action='store_true',
                       help='生成动画（默认：不生成）')
    parser.add_argument('--animation-fps', type=int, default=10,
                       help='动画帧率 (默认: 10)')
    parser.add_argument('--animation-dpi', type=int, default=100,
                       help='动画DPI (默认: 100)')
    return parser.parse_args()


def run_example(args):
    """运行泵站系统仿真"""
    print("\n" + "="*80)
    print("示例2: 泵站系统仿真 - 增强版（嵌入式动画）")
    print("="*80)
    if args.animate:
        print(f"动画生成：已启用 (FPS={args.animation_fps}, DPI={args.animation_dpi})")
    else:
        print("动画生成：未启用（使用 --animate 参数启用）")

    # ========================================================================
    # 1. 创建系统组件
    # ========================================================================
    print("\n1. 创建系统组件")
    print("-" * 80)

    tank1 = Tank("Tank1", 0, 1000, 100)  # 初始水位100m
    pump = Pump("Pump1", max_flow=10, rated_head=50)
    pipe = Pipe("Pipe1", length=1000, diameter=0.5)
    tank2 = Tank("Tank2", 0, 1000, 50)   # 初始水位50m

    components = [tank1, pump, pipe, tank2]
    simulator = PlantSimulator(components, mode='reduced')

    print(f"水池1初始水位: {tank1.level:.2f} m")
    print(f"水池2初始水位: {tank2.level:.2f} m")
    print(f"泵额定流量: {pump.max_flow:.2f} m³/s")
    print(f"泵额定扬程: {pump.rated_head:.2f} m")
    print(f"管道长度: {pipe.length:.2f} m")
    print(f"管道直径: {pipe.diameter:.2f} m")

    # ========================================================================
    # 2. 运行仿真
    # ========================================================================
    print("\n2. 运行泵站启动仿真")
    print("-" * 80)

    dt = 10.0      # 时间步长 (s)
    n_steps = 60   # 总步数 (10分钟)

    # 数据存储
    time_history = []
    tank1_level = []
    tank2_level = []
    pump_flow = []
    pump_speed = []

    print(f"时间步长: {dt} s")
    print(f"总步数: {n_steps}")
    print(f"总时间: {dt * n_steps} s\n")

    # 泵速度设定（模拟软启动）
    for i in range(n_steps):
        t = i * dt
        time_history.append(t)

        # 软启动：前10步线性增加到额定转速
        if i < 10:
            speed = 60.0 * (i + 1) / 10.0
        else:
            speed = 60.0

        control_inputs = {'Pump1': {'speed': speed}}
        states = simulator.step(dt, control_inputs)

        # 记录数据
        tank1_level.append(states['Tank1'].level)
        tank2_level.append(states['Tank2'].level)
        pump_speed.append(speed)

        # 计算泵流量（简化）
        level_diff = states['Tank1'].level - states['Tank2'].level
        flow = pump.max_flow * (speed / 60.0) * min(1.0, level_diff / 50.0)
        pump_flow.append(max(0, flow))

        # 打印进度
        if (i + 1) % 10 == 0:
            print(f"Step {i+1}/{n_steps}: t={t:.1f}s, "
                  f"Tank1={states['Tank1'].level:.2f}m, "
                  f"Tank2={states['Tank2'].level:.2f}m, "
                  f"Flow={flow:.2f}m³/s")

    # 转换为numpy数组
    time_history = np.array(time_history)
    tank1_level = np.array(tank1_level)
    tank2_level = np.array(tank2_level)
    pump_flow = np.array(pump_flow)
    pump_speed = np.array(pump_speed)

    print("\n✓ 仿真完成")

    # ========================================================================
    # 3. 生成静态图表
    # ========================================================================
    print("\n3. 生成静态图表")
    print("-" * 80)

    output_dir = os.path.join(
        os.path.dirname(os.path.abspath(__file__)),
        "..", "outputs", "figures"
    )
    os.makedirs(output_dir, exist_ok=True)

    fig, axes = plt.subplots(3, 1, figsize=(12, 10))

    # 水位
    axes[0].plot(time_history, tank1_level, 'b-', linewidth=2, label='Tank 1')
    axes[0].plot(time_history, tank2_level, 'r-', linewidth=2, label='Tank 2')
    axes[0].set_ylabel('Water Level (m)', fontsize=11)
    axes[0].set_title('Pump System - Tank Levels', fontsize=12, fontweight='bold')
    axes[0].grid(True, alpha=0.3)
    axes[0].legend()

    # 流量
    axes[1].plot(time_history, pump_flow, 'g-', linewidth=2)
    axes[1].set_ylabel('Flow Rate (m³/s)', fontsize=11)
    axes[1].set_title('Pump Flow Rate', fontsize=12, fontweight='bold')
    axes[1].grid(True, alpha=0.3)

    # 转速
    axes[2].plot(time_history, pump_speed, 'm-', linewidth=2)
    axes[2].set_ylabel('Pump Speed (rpm)', fontsize=11)
    axes[2].set_xlabel('Time (s)', fontsize=11)
    axes[2].set_title('Pump Speed', fontsize=12, fontweight='bold')
    axes[2].grid(True, alpha=0.3)

    plt.tight_layout()

    fig_path = os.path.join(output_dir, 'pump_system_startup.png')
    plt.savefig(fig_path, dpi=150, bbox_inches='tight')
    plt.close()

    print(f"✓ 静态图表已保存: {fig_path}")

    # ========================================================================
    # 4. 生成动画（如果启用）
    # ========================================================================
    if args.animate:
        print("\n4. 生成动画")
        print("-" * 80)

        animation_dir = os.path.join(
            os.path.dirname(os.path.abspath(__file__)),
            "..", "outputs", "animations"
        )

        anim_gen = AnimationGenerator(
            output_dir=animation_dir,
            fps=args.animation_fps,
            dpi=args.animation_dpi
        )

        try:
            gif_path = anim_gen.create_timeseries_animation(
                t=time_history,
                data={
                    'Tank 1 Level': tank1_level,
                    'Tank 2 Level': tank2_level,
                    'Pump Flow': pump_flow,
                    'Pump Speed': pump_speed,
                },
                filename='pump_system_startup_embedded.gif',
                title='Pump System Startup',
                xlabel='Time (s)',
                ylabels={
                    'Tank 1 Level': 'Level (m)',
                    'Tank 2 Level': 'Level (m)',
                    'Pump Flow': 'Flow (m³/s)',
                    'Pump Speed': 'Speed (rpm)',
                },
                layout=(2, 2)
            )
            print(f"✓ 动画已保存: {os.path.basename(gif_path)}")
        except Exception as e:
            print(f"✗ 动画生成失败: {e}")

    # ========================================================================
    # 完成
    # ========================================================================
    print("\n" + "="*80)
    print("泵站系统仿真完成！")
    print("="*80)
    print(f"\n图表已保存到: {output_dir}")
    if args.animate:
        print(f"动画已保存到: {animation_dir}")
    print("\n✅ 示例2（增强版）运行成功")


if __name__ == "__main__":
    args = parse_args()
    run_example(args)
