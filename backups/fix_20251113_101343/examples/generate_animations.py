#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
为所有示例生成动态GIF动画
"""

import os
import sys
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.animation import FuncAnimation, PillowWriter
from pathlib import Path
import json


class AnimationGenerator:
    """动画生成器"""

    def __init__(self, examples_root):
        self.examples_root = Path(examples_root)

    def generate_canal_flow_animation(self, example_dir):
        """生成明渠流动动画"""
        print(f"  生成明渠流动动画...")

        # 使用Preissmann方法重新仿真并生成动画
        sys.path.insert(0, str(self.examples_root.parent))

        # DEPRECATED: Use HydrostaticCanalSolver instead
# # DEPRECATED: Use HydrostaticCanalSolver instead
# from solvers.canal_solver import CanalSolver
        from utils.canal_utils import compute_steady_uniform_flow

        # 参数设置
        length = 1000.0
        B = 10.0
        S0 = 0.001
        n = 0.025
        nx = 201
        Q_upstream = 8.0
        h_downstream = compute_steady_uniform_flow(Q_upstream, B, S0, n)

        # 创建求解器
        solver = CanalSolver(
            length=length,
            width=B,
            slope=S0,
            manning_n=n,
            nx=nx,
            method='PREISSMANN'
        )

        # 边界条件
        boundary_conditions = {
            'upstream': {'type': 'discharge', 'value': Q_upstream},
            'downstream': {'type': 'depth', 'value': h_downstream}
        }

        # 初始化
        h_init = np.full(nx, h_downstream)
        u_init = np.full(nx, Q_upstream / (B * h_downstream))

        # 时间参数
        t_end = 200.0
        dt = 0.5

        # 运行仿真
        result = solver.solve(
            h_init=h_init,
            u_init=u_init,
            t_end=t_end,
            dt=dt,
            boundary_conditions=boundary_conditions
        )

        # 创建动画
        x = solver.x
        h_history = result['h_history']
        u_history = result['u_history']

        # 每隔5个时间步取一帧（控制帧数）
        frame_stride = max(1, len(result['t_history']) // 100)
        t_frames = result['t_history'][::frame_stride]
        h_frames = [h_history[i] for i in range(0, len(h_history), frame_stride)]
        u_frames = [u_history[i] for i in range(0, len(u_history), frame_stride)]

        # 创建图形
        fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(12, 8))

        # 计算y轴范围
        h_min = min(h.min() for h in h_frames)
        h_max = max(h.max() for h in h_frames)
        u_min = min(u.min() for u in u_frames)
        u_max = max(u.max() for u in u_frames)

        line1, = ax1.plot([], [], 'b-', linewidth=2, label='水深')
        ax1.axhline(y=h_downstream, color='r', linestyle='--', alpha=0.5, label='理论值')
        ax1.set_xlim(0, length)
        ax1.set_ylim(h_min - 0.1, h_max + 0.1)
        ax1.set_xlabel('距离 (m)', fontsize=12)
        ax1.set_ylabel('水深 (m)', fontsize=12)
        ax1.legend(loc='upper right')
        ax1.grid(True, alpha=0.3)
        title1 = ax1.set_title('', fontsize=14, fontweight='bold')

        line2, = ax2.plot([], [], 'g-', linewidth=2, label='流速')
        ax2.set_xlim(0, length)
        ax2.set_ylim(u_min - 0.05, u_max + 0.05)
        ax2.set_xlabel('距离 (m)', fontsize=12)
        ax2.set_ylabel('流速 (m/s)', fontsize=12)
        ax2.legend(loc='upper right')
        ax2.grid(True, alpha=0.3)

        def init():
            line1.set_data([], [])
            line2.set_data([], [])
            return line1, line2

        def animate(frame):
            t = t_frames[frame]
            h = h_frames[frame]
            u = u_frames[frame]

            line1.set_data(x, h)
            line2.set_data(x, u)
            title1.set_text(f'明渠非恒定流动 - 时间: {t:.1f}s')

            return line1, line2, title1

        # 创建动画
        anim = FuncAnimation(
            fig,
            animate,
            init_func=init,
            frames=len(t_frames),
            interval=100,  # 100ms per frame (不会太快)
            blit=True
        )

        # 保存GIF
        output_dir = example_dir / 'outputs' / 'animations'
        output_dir.mkdir(parents=True, exist_ok=True)
        gif_path = output_dir / 'canal_flow_animation.gif'

        writer = PillowWriter(fps=10)  # 10 FPS，不会太快
        anim.save(str(gif_path), writer=writer, dpi=100)

        plt.close(fig)

        print(f"     动画已保存: {gif_path}")
        return str(gif_path)

    def generate_simple_animation(self, example_dir, example_name):
        """生成简单的示意动画（当无法生成实际仿真动画时）"""
        print(f"  生成示意动画...")

        output_dir = example_dir / 'outputs' / 'animations'
        output_dir.mkdir(parents=True, exist_ok=True)

        # 创建一个简单的示意动画
        fig, ax = plt.subplots(figsize=(10, 6))

        t = np.linspace(0, 10, 100)

        line, = ax.plot([], [], 'b-', linewidth=2)
        ax.set_xlim(0, 10)
        ax.set_ylim(-1.5, 1.5)
        ax.set_xlabel('时间 (s)', fontsize=12)
        ax.set_ylabel('响应', fontsize=12)
        ax.set_title(f'{example_name} - 动态响应示意', fontsize=14, fontweight='bold')
        ax.grid(True, alpha=0.3)

        def init():
            line.set_data([], [])
            return line,

        def animate(frame):
            t_frame = t[:frame]
            y_frame = np.sin(2 * np.pi * 0.5 * t_frame) * np.exp(-0.1 * t_frame)
            line.set_data(t_frame, y_frame)
            return line,

        anim = FuncAnimation(
            fig,
            animate,
            init_func=init,
            frames=len(t),
            interval=100,
            blit=True
        )

        gif_path = output_dir / f'{example_name}_animation.gif'
        writer = PillowWriter(fps=10)
        anim.save(str(gif_path), writer=writer, dpi=100)

        plt.close(fig)

        print(f"     示意动画已保存: {gif_path}")
        return str(gif_path)

    def generate_all_animations(self):
        """为所有示例生成动画"""
        print(f"\n{'='*80}")
        print("生成所有示例的动画")
        print('='*80)

        example_dirs = sorted([d for d in self.examples_root.glob('example_*') if d.is_dir()])

        animations = {}

        for i, example_dir in enumerate(example_dirs, 1):
            print(f"\n[{i}/{len(example_dirs)}] {example_dir.name}")

            try:
                # 特殊处理：为example_01生成实际的仿真动画
                if example_dir.name == 'example_01_canal_flow':
                    gif_path = self.generate_canal_flow_animation(example_dir)
                    animations[example_dir.name] = gif_path
                else:
                    # 其他示例生成示意动画
                    gif_path = self.generate_simple_animation(example_dir, example_dir.name)
                    animations[example_dir.name] = gif_path

            except Exception as e:
                print(f"   错误: {e}")
                animations[example_dir.name] = None

        print(f"\n{'='*80}")
        print(f"动画生成完成: {sum(1 for v in animations.values() if v)}/{len(animations)}")
        print('='*80)

        return animations


def main():
    """主函数"""
    examples_root = Path(__file__).parent

    generator = AnimationGenerator(examples_root)

    # 只为前5个示例生成动画（测试）
    # generator.generate_all_animations()

    # 先只生成example_01的动画
    example_01 = examples_root / 'example_01_canal_flow'
    if example_01.exists():
        try:
            generator.generate_canal_flow_animation(example_01)
        except Exception as e:
            print(f"Error: {e}")
            import traceback
            traceback.print_exc()


if __name__ == '__main__':
    main()
