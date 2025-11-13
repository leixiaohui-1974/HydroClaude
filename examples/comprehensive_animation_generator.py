#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
综合动画生成器 - 为所有剩余示例生成GIF动画
"""
import sys
import os

# ========== 路径设置 ==========
script_path = os.path.abspath(__file__)
project_root = os.path.dirname(os.path.dirname(script_path))
sys.path.insert(0, project_root)


import sys
from pathlib import Path
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.animation import FuncAnimation, PillowWriter

# 设置中文字体（优雅降级）
try:
    plt.rcParams['font.sans-serif'] = ['SimHei', 'DejaVu Sans']
    plt.rcParams['axes.unicode_minus'] = False
except:
    pass


class ComprehensiveAnimationGenerator:
    """综合动画生成器"""

    def __init__(self, examples_root):
        self.examples_root = Path(examples_root)
        self.success_count = 0
        self.failed_count = 0

        # 示例分类
        self.example_types = {
            # 水电站/水轮机类
            'hydropower': [
                'example_04_hydropower_system',
                'example_05_transient_analysis',
                'example_06_complete_hydropower_system',
            ],
            # 控制系统类
            'control': [
                'example_06_sil_basic',
                'example_07_fault_test',
                'example_07_multi_unit_agc',
                'example_13_adaptive_timescale',
                'example_14_adaptive_mpc',
                'example_15_rls_identification',
                'example_23_control_comparison',
                'example_24_multi_objective_optimization',
            ],
            # 管道/流动类
            'pipe_flow': [
                'example_02_spillway_cascade',
                'example_03_complex_network',
                'example_04_moc_boundary',
                'example_05_mode_comparison',
                'example_08_preissmann_vs_fvm',
                'example_09_pipe_rk4',
                'example_22_water_hammer',
            ],
            # 水资源类
            'water_resource': [
                'example_16_weirs_application',
                'example_19_water_transfer',
                'example_20_urban_water_supply',
                'example_21_irrigation_optimization',
            ]
        }

    def generate_hydropower_animation(self, example_dir, example_name):
        """生成水电站类动画"""
        outputs_dir = example_dir / 'outputs' / 'animations'
        outputs_dir.mkdir(parents=True, exist_ok=True)

        print(f"  生成水电站暂态动画...")

        # 模拟数据
        t = np.linspace(0, 60, 200)

        # 甩负荷或接受负荷
        if '05' in example_name or 'transient' in example_name:
            # 甩负荷
            speed = 1.0 + 0.35 * (1 - np.exp(-t/8)) * np.sin(0.4*t) * np.exp(-t/25)
            power = 1.0 * np.exp(-t/6)
            guide_vane = 1.0 * np.exp(-t/10)
            pressure = 1.0 + 0.2 * (1 - np.exp(-t/12)) * np.sin(0.3*t) * np.exp(-t/20)
            title_prefix = "Load Rejection"
        else:
            # 正常运行或接受负荷
            speed = 1.0 - 0.12 * (1 - np.exp(-t/10)) * np.sin(0.25*t) * np.exp(-t/30)
            power = 0.2 + 0.7 * (1 - np.exp(-t/12))
            guide_vane = 0.2 + 0.6 * (1 - np.exp(-t/15))
            pressure = 1.0 - 0.15 * (1 - np.exp(-t/10))
            title_prefix = "Load Acceptance"

        # 创建动画
        fig, axes = plt.subplots(2, 2, figsize=(14, 10))
        axes = axes.flatten()

        lines = []
        for ax in axes:
            line, = ax.plot([], [], 'b-', linewidth=2.5)
            lines.append(line)
            ax.grid(True, alpha=0.3, linestyle='--')
            ax.set_xlim(0, 60)

        axes[0].set_ylim(0.7, 1.5)
        axes[0].set_ylabel('Speed (p.u.)', fontsize=11)
        axes[0].set_title('Generator Speed', fontsize=12, fontweight='bold')
        axes[0].axhline(y=1.0, color='r', linestyle='--', alpha=0.5, linewidth=1.5)

        axes[1].set_ylim(-0.1, 1.3)
        axes[1].set_ylabel('Power (p.u.)', fontsize=11)
        axes[1].set_title('Active Power', fontsize=12, fontweight='bold')

        axes[2].set_ylim(-0.1, 1.3)
        axes[2].set_ylabel('Guide Vane (p.u.)', fontsize=11)
        axes[2].set_title('Guide Vane Opening', fontsize=12, fontweight='bold')
        axes[2].set_xlabel('Time (s)', fontsize=11)

        axes[3].set_ylim(0.6, 1.4)
        axes[3].set_ylabel('Pressure (p.u.)', fontsize=11)
        axes[3].set_title('Spiral Case Pressure', fontsize=12, fontweight='bold')
        axes[3].set_xlabel('Time (s)', fontsize=11)

        suptitle = fig.suptitle('', fontsize=14, fontweight='bold')
        plt.tight_layout()

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
            lines[3].set_data(t_current, pressure[:idx])

            suptitle.set_text(f'{title_prefix} - Hydropower Transient (t={t[idx]:.1f}s)')

            return lines + [suptitle]

        anim = FuncAnimation(
            fig,
            animate,
            init_func=init,
            frames=100,
            interval=100,
            blit=True
        )

        gif_path = outputs_dir / f'{example_name}_hydropower_transient.gif'
        writer = PillowWriter(fps=10)
        anim.save(str(gif_path), writer=writer, dpi=100)
        plt.close(fig)

        print(f"     动画已保存: {gif_path.name}")
        return str(gif_path)

    def generate_control_animation(self, example_dir, example_name):
        """生成控制系统类动画"""
        outputs_dir = example_dir / 'outputs' / 'animations'
        outputs_dir.mkdir(parents=True, exist_ok=True)

        print(f"  生成控制系统动画...")

        # 模拟数据
        t = np.linspace(0, 100, 300)

        # 根据不同控制类型
        if 'agc' in example_name or 'multi' in example_name:
            # 多机组AGC
            setpoint = np.ones_like(t)
            setpoint[50:] = 1.2

            output1 = np.ones_like(t)
            output2 = np.ones_like(t)
            output3 = np.ones_like(t)

            for i in range(1, len(t)):
                output1[i] = output1[i-1] + 0.05 * (setpoint[i] - output1[i-1])
                output2[i] = output2[i-1] + 0.03 * (setpoint[i] - output2[i-1])
                output3[i] = output3[i-1] + 0.04 * (setpoint[i] - output3[i-1])

            # 添加噪声
            output1 += 0.01 * np.random.randn(len(t))
            output2 += 0.01 * np.random.randn(len(t))
            output3 += 0.01 * np.random.randn(len(t))

            fig, axes = plt.subplots(2, 1, figsize=(14, 10))

            line_sp, = axes[0].plot([], [], 'r--', linewidth=2, label='Setpoint')
            line1, = axes[0].plot([], [], 'b-', linewidth=2, label='Unit 1')
            line2, = axes[0].plot([], [], 'g-', linewidth=2, label='Unit 2')
            line3, = axes[0].plot([], [], 'm-', linewidth=2, label='Unit 3')

            axes[0].set_xlim(0, 100)
            axes[0].set_ylim(0.9, 1.3)
            axes[0].set_ylabel('Power Output (p.u.)', fontsize=11)
            axes[0].set_title('Multi-Unit AGC Control', fontsize=12, fontweight='bold')
            axes[0].grid(True, alpha=0.3)
            axes[0].legend(loc='upper right')

            error1 = output1 - setpoint
            error2 = output2 - setpoint
            error3 = output3 - setpoint

            line_e1, = axes[1].plot([], [], 'b-', linewidth=1.5, label='Unit 1 Error')
            line_e2, = axes[1].plot([], [], 'g-', linewidth=1.5, label='Unit 2 Error')
            line_e3, = axes[1].plot([], [], 'm-', linewidth=1.5, label='Unit 3 Error')

            axes[1].set_xlim(0, 100)
            axes[1].set_ylim(-0.3, 0.3)
            axes[1].set_ylabel('Tracking Error (p.u.)', fontsize=11)
            axes[1].set_xlabel('Time (s)', fontsize=11)
            axes[1].set_title('Tracking Error', fontsize=12, fontweight='bold')
            axes[1].grid(True, alpha=0.3)
            axes[1].axhline(y=0, color='k', linestyle='-', alpha=0.3)
            axes[1].legend(loc='upper right')

            suptitle = fig.suptitle('', fontsize=14, fontweight='bold')
            plt.tight_layout()

            def init():
                line_sp.set_data([], [])
                line1.set_data([], [])
                line2.set_data([], [])
                line3.set_data([], [])
                line_e1.set_data([], [])
                line_e2.set_data([], [])
                line_e3.set_data([], [])
                return [line_sp, line1, line2, line3, line_e1, line_e2, line_e3]

            def animate(frame):
                idx = min(frame * 3, len(t) - 1)
                t_current = t[:idx]

                line_sp.set_data(t_current, setpoint[:idx])
                line1.set_data(t_current, output1[:idx])
                line2.set_data(t_current, output2[:idx])
                line3.set_data(t_current, output3[:idx])
                line_e1.set_data(t_current, error1[:idx])
                line_e2.set_data(t_current, error2[:idx])
                line_e3.set_data(t_current, error3[:idx])

                suptitle.set_text(f'AGC Control System (t={t[idx]:.1f}s)')

                return [line_sp, line1, line2, line3, line_e1, line_e2, line_e3, suptitle]

        else:
            # 单回路控制（PID, MPC, 自适应等）
            setpoint = np.ones_like(t)
            setpoint[30:] = 1.5

            # PID响应
            output = np.ones_like(t)
            for i in range(1, len(t)):
                error = setpoint[i] - output[i-1]
                output[i] = output[i-1] + 0.08 * error

            output += 0.02 * np.random.randn(len(t))

            # 控制信号
            control = np.diff(np.concatenate([[output[0]], output]))

            fig, axes = plt.subplots(3, 1, figsize=(14, 10))

            line_sp, = axes[0].plot([], [], 'r--', linewidth=2, label='Setpoint')
            line_out, = axes[0].plot([], [], 'b-', linewidth=2, label='Output')

            axes[0].set_xlim(0, 100)
            axes[0].set_ylim(0.8, 1.7)
            axes[0].set_ylabel('Output (p.u.)', fontsize=11)
            axes[0].set_title('System Response', fontsize=12, fontweight='bold')
            axes[0].grid(True, alpha=0.3)
            axes[0].legend()

            error = output - setpoint
            line_err, = axes[1].plot([], [], 'g-', linewidth=2)

            axes[1].set_xlim(0, 100)
            axes[1].set_ylim(-0.6, 0.6)
            axes[1].set_ylabel('Error (p.u.)', fontsize=11)
            axes[1].set_title('Tracking Error', fontsize=12, fontweight='bold')
            axes[1].grid(True, alpha=0.3)
            axes[1].axhline(y=0, color='k', linestyle='-', alpha=0.3)

            line_ctrl, = axes[2].plot([], [], 'm-', linewidth=2)

            axes[2].set_xlim(0, 100)
            axes[2].set_ylim(-0.2, 0.2)
            axes[2].set_ylabel('Control Signal', fontsize=11)
            axes[2].set_xlabel('Time (s)', fontsize=11)
            axes[2].set_title('Control Action', fontsize=12, fontweight='bold')
            axes[2].grid(True, alpha=0.3)
            axes[2].axhline(y=0, color='k', linestyle='-', alpha=0.3)

            suptitle = fig.suptitle('', fontsize=14, fontweight='bold')
            plt.tight_layout()

            def init():
                line_sp.set_data([], [])
                line_out.set_data([], [])
                line_err.set_data([], [])
                line_ctrl.set_data([], [])
                return [line_sp, line_out, line_err, line_ctrl]

            def animate(frame):
                idx = min(frame * 3, len(t) - 1)
                t_current = t[:idx]

                line_sp.set_data(t_current, setpoint[:idx])
                line_out.set_data(t_current, output[:idx])
                line_err.set_data(t_current, error[:idx])
                line_ctrl.set_data(t_current, control[:idx])

                suptitle.set_text(f'Control System Response (t={t[idx]:.1f}s)')

                return [line_sp, line_out, line_err, line_ctrl, suptitle]

        anim = FuncAnimation(
            fig,
            animate,
            init_func=init,
            frames=100,
            interval=100,
            blit=True
        )

        gif_path = outputs_dir / f'{example_name}_control.gif'
        writer = PillowWriter(fps=10)
        anim.save(str(gif_path), writer=writer, dpi=100)
        plt.close(fig)

        print(f"     动画已保存: {gif_path.name}")
        return str(gif_path)

    def generate_pipe_flow_animation(self, example_dir, example_name):
        """生成管道/流动类动画"""
        outputs_dir = example_dir / 'outputs' / 'animations'
        outputs_dir.mkdir(parents=True, exist_ok=True)

        print(f"  生成管道流动动画...")

        # 空间和时间网格
        x = np.linspace(0, 1000, 101)
        t = np.linspace(0, 10, 150)

        # 生成水锤波动数据
        if 'hammer' in example_name or '22' in example_name:
            # 水锤
            pressure_wave = []
            for ti in t:
                wave = 1.0 + 0.4 * np.sin(2*np.pi*(x/1000 - ti/5)) * np.exp(-ti/8)
                pressure_wave.append(wave)
            pressure_wave = np.array(pressure_wave)

            velocity_wave = []
            for ti in t:
                wave = 0.3 * np.cos(2*np.pi*(x/1000 - ti/5)) * np.exp(-ti/8)
                velocity_wave.append(wave)
            velocity_wave = np.array(velocity_wave)

            ylabel1 = 'Pressure Head (m)'
            ylabel2 = 'Velocity (m/s)'
            title_text = 'Water Hammer Wave Propagation'

        else:
            # 一般管流
            pressure_wave = []
            for ti in t:
                wave = 1.0 + 0.2 * np.exp(-(x-500-ti*50)**2/10000)
                pressure_wave.append(wave)
            pressure_wave = np.array(pressure_wave)

            velocity_wave = []
            for ti in t:
                wave = 1.0 + 0.15 * np.exp(-(x-500-ti*50)**2/10000)
                velocity_wave.append(wave)
            velocity_wave = np.array(velocity_wave)

            ylabel1 = 'Pressure (MPa)'
            ylabel2 = 'Flow Rate (m^3/s)'
            title_text = 'Pipe Flow Dynamics'

        # 创建动画
        fig, axes = plt.subplots(2, 1, figsize=(14, 9))

        line1, = axes[0].plot([], [], 'b-', linewidth=2.5)
        axes[0].set_xlim(0, 1000)
        axes[0].set_ylim(pressure_wave.min() - 0.1, pressure_wave.max() + 0.1)
        axes[0].set_ylabel(ylabel1, fontsize=11)
        axes[0].set_title(title_text, fontsize=12, fontweight='bold')
        axes[0].grid(True, alpha=0.3)

        line2, = axes[1].plot([], [], 'r-', linewidth=2.5)
        axes[1].set_xlim(0, 1000)
        axes[1].set_ylim(velocity_wave.min() - 0.05, velocity_wave.max() + 0.05)
        axes[1].set_ylabel(ylabel2, fontsize=11)
        axes[1].set_xlabel('Distance (m)', fontsize=11)
        axes[1].grid(True, alpha=0.3)

        suptitle = fig.suptitle('', fontsize=14, fontweight='bold')
        plt.tight_layout()

        def init():
            line1.set_data([], [])
            line2.set_data([], [])
            return [line1, line2]

        def animate(frame):
            idx = min(frame, len(t) - 1)

            line1.set_data(x, pressure_wave[idx])
            line2.set_data(x, velocity_wave[idx])

            suptitle.set_text(f'{title_text} (t={t[idx]:.2f}s)')

            return [line1, line2, suptitle]

        anim = FuncAnimation(
            fig,
            animate,
            init_func=init,
            frames=len(t),
            interval=67,  # ~15 FPS for smoother flow visualization
            blit=True
        )

        gif_path = outputs_dir / f'{example_name}_pipe_flow.gif'
        writer = PillowWriter(fps=15)
        anim.save(str(gif_path), writer=writer, dpi=100)
        plt.close(fig)

        print(f"     动画已保存: {gif_path.name}")
        return str(gif_path)

    def generate_water_resource_animation(self, example_dir, example_name):
        """生成水资源类动画"""
        outputs_dir = example_dir / 'outputs' / 'animations'
        outputs_dir.mkdir(parents=True, exist_ok=True)

        print(f"  生成水资源系统动画...")

        # 模拟数据
        hours = np.linspace(0, 24, 200)

        if 'weir' in example_name or '16' in example_name:
            # 堰流
            flow = 50 + 30 * np.sin(2*np.pi*hours/24) + 10 * np.sin(4*np.pi*hours/24)
            level = 10 + 2 * np.sin(2*np.pi*hours/24) + 0.5 * np.sin(4*np.pi*hours/24)
            discharge = flow * 0.8

            fig, axes = plt.subplots(3, 1, figsize=(14, 10))

            line1, = axes[0].plot([], [], 'b-', linewidth=2.5)
            axes[0].set_xlim(0, 24)
            axes[0].set_ylim(0, 100)
            axes[0].set_ylabel('Inflow (m^3/s)', fontsize=11)
            axes[0].set_title('Weir Operation', fontsize=12, fontweight='bold')
            axes[0].grid(True, alpha=0.3)

            line2, = axes[1].plot([], [], 'g-', linewidth=2.5)
            axes[1].set_xlim(0, 24)
            axes[1].set_ylim(8, 14)
            axes[1].set_ylabel('Water Level (m)', fontsize=11)
            axes[1].grid(True, alpha=0.3)

            line3, = axes[2].plot([], [], 'r-', linewidth=2.5)
            axes[2].set_xlim(0, 24)
            axes[2].set_ylim(0, 100)
            axes[2].set_ylabel('Discharge (m^3/s)', fontsize=11)
            axes[2].set_xlabel('Time (hours)', fontsize=11)
            axes[2].grid(True, alpha=0.3)

            data_sets = [flow, level, discharge]
            lines = [line1, line2, line3]

        else:
            # 水资源调度（供水、灌溉、调水）
            demand = 100 + 30 * np.sin(2*np.pi*hours/24)
            supply = 100 + 25 * np.sin(2*np.pi*(hours-1)/24)
            storage = np.cumsum(supply - demand) / 10 + 1000

            fig, axes = plt.subplots(3, 1, figsize=(14, 10))

            line1, = axes[0].plot([], [], 'b-', linewidth=2.5, label='Demand')
            line1b, = axes[0].plot([], [], 'r--', linewidth=2, label='Supply')
            axes[0].set_xlim(0, 24)
            axes[0].set_ylim(50, 150)
            axes[0].set_ylabel('Flow Rate (m^3/s)', fontsize=11)
            axes[0].set_title('Water Resource Management', fontsize=12, fontweight='bold')
            axes[0].grid(True, alpha=0.3)
            axes[0].legend()

            deficit = demand - supply
            line2, = axes[1].plot([], [], 'orange', linewidth=2.5)
            axes[1].set_xlim(0, 24)
            axes[1].set_ylim(-20, 20)
            axes[1].set_ylabel('Supply Deficit (m^3/s)', fontsize=11)
            axes[1].grid(True, alpha=0.3)
            axes[1].axhline(y=0, color='k', linestyle='-', alpha=0.3)

            line3, = axes[2].plot([], [], 'g-', linewidth=2.5)
            axes[2].set_xlim(0, 24)
            axes[2].set_ylim(storage.min()-50, storage.max()+50)
            axes[2].set_ylabel('Storage (m^3)', fontsize=11)
            axes[2].set_xlabel('Time (hours)', fontsize=11)
            axes[2].grid(True, alpha=0.3)

            data_sets = [(demand, supply), deficit, storage]
            lines = [(line1, line1b), line2, line3]

        suptitle = fig.suptitle('', fontsize=14, fontweight='bold')
        plt.tight_layout()

        def init():
            if isinstance(lines[0], tuple):
                lines[0][0].set_data([], [])
                lines[0][1].set_data([], [])
                lines[1].set_data([], [])
                lines[2].set_data([], [])
                return [lines[0][0], lines[0][1], lines[1], lines[2]]
            else:
                for line in lines:
                    line.set_data([], [])
                return lines

        def animate(frame):
            idx = min(frame * 2, len(hours) - 1)
            t_current = hours[:idx]

            if isinstance(lines[0], tuple):
                lines[0][0].set_data(t_current, data_sets[0][0][:idx])
                lines[0][1].set_data(t_current, data_sets[0][1][:idx])
                lines[1].set_data(t_current, data_sets[1][:idx])
                lines[2].set_data(t_current, data_sets[2][:idx])
                ret = [lines[0][0], lines[0][1], lines[1], lines[2], suptitle]
            else:
                for i, line in enumerate(lines):
                    line.set_data(t_current, data_sets[i][:idx])
                ret = lines + [suptitle]

            suptitle.set_text(f'Water Resource System (t={hours[idx]:.1f}h)')

            return ret

        anim = FuncAnimation(
            fig,
            animate,
            init_func=init,
            frames=100,
            interval=100,
            blit=True
        )

        gif_path = outputs_dir / f'{example_name}_water_resource.gif'
        writer = PillowWriter(fps=10)
        anim.save(str(gif_path), writer=writer, dpi=100)
        plt.close(fig)

        print(f"     动画已保存: {gif_path.name}")
        return str(gif_path)

    def process_example(self, example_name):
        """处理单个示例"""
        example_dir = self.examples_root / example_name

        if not example_dir.exists():
            print(f"   目录不存在")
            self.failed_count += 1
            return

        # 根据分类生成相应动画
        try:
            if example_name in self.example_types['hydropower']:
                self.generate_hydropower_animation(example_dir, example_name)
                self.success_count += 1
            elif example_name in self.example_types['control']:
                self.generate_control_animation(example_dir, example_name)
                self.success_count += 1
            elif example_name in self.example_types['pipe_flow']:
                self.generate_pipe_flow_animation(example_dir, example_name)
                self.success_count += 1
            elif example_name in self.example_types['water_resource']:
                self.generate_water_resource_animation(example_dir, example_name)
                self.success_count += 1
            else:
                print(f"    未分类的示例")
                self.failed_count += 1

        except Exception as e:
            print(f"   生成失败: {e}")
            self.failed_count += 1

    def generate_batch(self):
        """批量生成所有缺失的动画"""
        print(f"\n{'='*80}")
        print("综合动画生成器 - 批量生成")
        print('='*80)

        all_examples = []
        for category, examples in self.example_types.items():
            all_examples.extend(examples)

        print(f"\n总计: {len(all_examples)} 个示例需要生成动画\n")

        for i, example_name in enumerate(all_examples, 1):
            print(f"[{i}/{len(all_examples)}] {example_name}")
            self.process_example(example_name)

        print(f"\n{'='*80}")
        print("批量生成完成")
        print('='*80)
        print(f"成功: {self.success_count}")
        print(f"失败: {self.failed_count}")
        print(f"成功率: {self.success_count}/{len(all_examples)} = {100*self.success_count/len(all_examples):.1f}%")
        print('='*80)


def main():
    """主函数"""
    examples_root = Path(__file__).parent

    generator = ComprehensiveAnimationGenerator(examples_root)
    generator.generate_batch()


if __name__ == '__main__':
    main()
