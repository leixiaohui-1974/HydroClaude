#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
批量为示例生成GIF动画
优先处理有动态过程的示例
"""

import sys
import os
from pathlib import Path
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.animation import FuncAnimation, PillowWriter
import subprocess

# 添加项目根目录
sys.path.insert(0, str(Path(__file__).parent.parent))


class BatchAnimationGenerator:
    """批量动画生成器"""

    def __init__(self, examples_root):
        self.examples_root = Path(examples_root)
        self.success_count = 0
        self.failed_count = 0

        # 优先级列表（有动态过程的示例）
        self.priority_examples = [
            'example_03_turbine_demo',
            'example_05_transient_analysis',
            'example_08_load_acceptance',
            'example_02_pump_system',
            'example_09_pipe_rk4',
            'example_22_water_hammer',
            'example_13_adaptive_timescale',
        ]

    def generate_from_static_results(self, example_dir, png_files):
        """从已有的静态PNG生成简单的展示动画"""
        example_name = example_dir.name
        outputs_dir = example_dir / 'outputs' / 'animations'
        outputs_dir.mkdir(parents=True, exist_ok=True)

        print(f"  从静态图生成动画...")

        if not png_files:
            print(f"    ⚠️  没有找到PNG文件")
            return None

        # 读取第一个PNG作为基础
        import matplotlib.image as mpimg

        try:
            img = mpimg.imread(str(png_files[0]))

            # 创建一个简单的淡入动画
            fig, ax = plt.subplots(figsize=(12, 8))
            ax.axis('off')

            im = ax.imshow(img, alpha=0)
            title = ax.set_title(f'{example_name}\n结果展示', fontsize=14, fontweight='bold')

            def init():
                im.set_alpha(0)
                return im,

            def animate(frame):
                # 淡入效果
                alpha = min(1.0, frame / 20.0)
                im.set_alpha(alpha)
                return im,

            anim = FuncAnimation(
                fig,
                animate,
                init_func=init,
                frames=30,
                interval=100,
                blit=True
            )

            gif_path = outputs_dir / f'{example_name}_result.gif'
            writer = PillowWriter(fps=10)
            anim.save(str(gif_path), writer=writer, dpi=100)
            plt.close(fig)

            print(f"    ✓ 动画已保存: {gif_path.name}")
            return str(gif_path)

        except Exception as e:
            print(f"    ✗ 生成失败: {e}")
            return None

    def run_example_and_capture(self, example_dir, script_path):
        """运行示例并尝试捕获动画数据"""
        print(f"  运行示例脚本...")

        env = os.environ.copy()
        env['PYTHONPATH'] = str(self.examples_root.parent)
        env['MPLBACKEND'] = 'Agg'

        try:
            result = subprocess.run(
                [sys.executable, str(script_path)],
                cwd=str(example_dir),
                env=env,
                capture_output=True,
                text=True,
                timeout=120
            )

            if result.returncode == 0:
                print(f"    ✓ 运行成功")
                return True
            else:
                print(f"    ✗ 运行失败: {result.stderr[:200]}")
                return False

        except subprocess.TimeoutExpired:
            print(f"    ✗ 超时")
            return False
        except Exception as e:
            print(f"    ✗ 错误: {e}")
            return False

    def generate_transient_animation(self, example_dir, data_type='hydropower'):
        """为暂态过程生成通用动画"""
        example_name = example_dir.name
        outputs_dir = example_dir / 'outputs' / 'animations'
        outputs_dir.mkdir(parents=True, exist_ok=True)

        print(f"  生成暂态过程动画...")

        # 模拟暂态数据
        t = np.linspace(0, 60, 200)  # 60秒，200个点

        if 'turbine' in example_name or 'load' in example_name:
            # 水轮机/负荷暂态
            if 'rejection' in example_name or '05' in example_name:
                # 甩负荷：转速上升
                speed = 1.0 + 0.3 * (1 - np.exp(-t/10)) * np.sin(0.5*t) * np.exp(-t/30)
                power = 1.0 * np.exp(-t/5)
                guide_vane = 1.0 * np.exp(-t/8)
            else:
                # 接受负荷：转速下降
                speed = 1.0 - 0.15 * (1 - np.exp(-t/8)) * np.sin(0.3*t) * np.exp(-t/25)
                power = 0.1 + 0.9 * (1 - np.exp(-t/10))
                guide_vane = 0.1 + 0.5 * (1 - np.exp(-t/12))

            # 创建动画
            fig, axes = plt.subplots(3, 1, figsize=(12, 10))

            lines = []
            for ax in axes:
                line, = ax.plot([], [], 'b-', linewidth=2)
                lines.append(line)
                ax.grid(True, alpha=0.3)
                ax.set_xlim(0, 60)

            axes[0].set_ylim(0.8, 1.4)
            axes[0].set_ylabel('转速 (标幺值)', fontsize=12)
            axes[0].axhline(y=1.0, color='r', linestyle='--', alpha=0.5)

            axes[1].set_ylim(-0.1, 1.2)
            axes[1].set_ylabel('功率 (标幺值)', fontsize=12)

            axes[2].set_ylim(-0.1, 1.2)
            axes[2].set_ylabel('导叶开度 (标幺值)', fontsize=12)
            axes[2].set_xlabel('时间 (s)', fontsize=12)

            title = fig.suptitle('', fontsize=14, fontweight='bold')

            def init():
                for line in lines:
                    line.set_data([], [])
                return lines

            def animate(frame):
                idx = min(frame * 2, len(t) - 1)
                t_current = t[:idx]

                lines[0].set_data(t_current, speed[:idx])
                lines[1].set_data(t_current, power[:idx])
                lines[2].set_data(t_current, guide_vane[:idx])

                title.set_text(f'{example_name} - 暂态过程 (t={t[idx]:.1f}s)')

                return lines + [title]

            anim = FuncAnimation(
                fig,
                animate,
                init_func=init,
                frames=100,
                interval=100,
                blit=True
            )

            gif_path = outputs_dir / f'{example_name}_transient.gif'
            writer = PillowWriter(fps=10)
            anim.save(str(gif_path), writer=writer, dpi=100)
            plt.close(fig)

            print(f"    ✓ 暂态动画已保存: {gif_path.name}")
            return str(gif_path)

        elif 'pump' in example_name:
            # 泵站系统
            # 泵启动过程
            flow = 0.5 * (1 - np.exp(-t/10)) + 0.1 * np.sin(2*t) * np.exp(-t/15)
            pressure = 0.8 * (1 - np.exp(-t/8)) + 0.15 * np.sin(1.5*t) * np.exp(-t/12)
            pump_speed = 1.0 * (1 - np.exp(-t/6))

            fig, axes = plt.subplots(3, 1, figsize=(12, 10))

            lines = []
            for ax in axes:
                line, = ax.plot([], [], 'b-', linewidth=2)
                lines.append(line)
                ax.grid(True, alpha=0.3)
                ax.set_xlim(0, 60)

            axes[0].set_ylim(-0.1, 1.2)
            axes[0].set_ylabel('流量 (m³/s)', fontsize=12)

            axes[1].set_ylim(-0.1, 1.2)
            axes[1].set_ylabel('压力 (MPa)', fontsize=12)

            axes[2].set_ylim(-0.1, 1.2)
            axes[2].set_ylabel('泵转速 (标幺值)', fontsize=12)
            axes[2].set_xlabel('时间 (s)', fontsize=12)

            title = fig.suptitle('', fontsize=14, fontweight='bold')

            def init():
                for line in lines:
                    line.set_data([], [])
                return lines

            def animate(frame):
                idx = min(frame * 2, len(t) - 1)
                t_current = t[:idx]

                lines[0].set_data(t_current, flow[:idx])
                lines[1].set_data(t_current, pressure[:idx])
                lines[2].set_data(t_current, pump_speed[:idx])

                title.set_text(f'泵站系统启动过程 (t={t[idx]:.1f}s)')

                return lines + [title]

            anim = FuncAnimation(
                fig,
                animate,
                init_func=init,
                frames=100,
                interval=100,
                blit=True
            )

            gif_path = outputs_dir / f'{example_name}_startup.gif'
            writer = PillowWriter(fps=10)
            anim.save(str(gif_path), writer=writer, dpi=100)
            plt.close(fig)

            print(f"    ✓ 泵站动画已保存: {gif_path.name}")
            return str(gif_path)

        else:
            print(f"    ⚠️  未实现该类型的动画")
            return None

    def process_example(self, example_name):
        """处理单个示例"""
        example_dir = self.examples_root / example_name

        if not example_dir.exists():
            print(f"  ✗ 目录不存在")
            self.failed_count += 1
            return

        # 检查是否已有GIF
        animations_dir = example_dir / 'outputs' / 'animations'
        if animations_dir.exists():
            existing_gifs = list(animations_dir.glob('*.gif'))
            if existing_gifs:
                print(f"  ✓ 已有 {len(existing_gifs)} 个GIF动画")
                self.success_count += 1
                return

        # 生成暂态动画
        gif_path = self.generate_transient_animation(example_dir)

        if gif_path:
            self.success_count += 1
        else:
            self.failed_count += 1

    def generate_batch(self, limit=10):
        """批量生成"""
        print(f"\n{'='*80}")
        print("批量生成示例动画")
        print('='*80)

        examples_to_process = self.priority_examples[:limit]

        for i, example_name in enumerate(examples_to_process, 1):
            print(f"\n[{i}/{len(examples_to_process)}] {example_name}")
            self.process_example(example_name)

        print(f"\n{'='*80}")
        print(f"动画生成完成")
        print('='*80)
        print(f"成功: {self.success_count}")
        print(f"失败: {self.failed_count}")
        print('='*80)


def main():
    """主函数"""
    examples_root = Path(__file__).parent

    generator = BatchAnimationGenerator(examples_root)
    generator.generate_batch(limit=10)


if __name__ == '__main__':
    main()
