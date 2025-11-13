#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
仿真引擎

统一的仿真运行接口，支持：
1. 从配置文件创建和运行仿真
2. 标准化的结果输出
3. 自动后处理和可视化
4. 进度监控和日志记录

作者: HydroClaude Team
日期: 2025-10-28
"""

import numpy as np
import sys
import os
from typing import Dict, Any, Optional, Tuple
from pathlib import Path
import time
import json
from datetime import datetime

# 添加项目路径
sys.path.insert(0, str(Path(__file__).parent.parent))

from engine.model_builder import ModelBuilder
from engine.config_parser import ConfigParser


class SimulationEngine:
    """
    仿真引擎

    功能：
    1. 加载配置文件
    2. 构建模型
    3. 运行仿真
    4. 输出结果
    5. 生成报告
    """

    def __init__(self, config_file: str):
        """
        初始化仿真引擎

        Args:
            config_file: 配置文件路径
        """
        self.config_file = Path(config_file)
        self.config = None
        self.builder = None
        self.solver = None
        self.results = {}
        self.start_time = None
        self.end_time = None

    def initialize(self):
        """初始化：加载配置和构建模型"""
        print("=" * 80)
        print("HydroClaude 仿真引擎")
        print("=" * 80)
        print(f"配置文件: {self.config_file.name}")
        print(f"时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print()

        # 1. 解析配置文件
        print("[1/3] 加载配置文件...")
        self.builder = ModelBuilder.from_config_file(str(self.config_file))
        self.config = self.builder.config
        print("   配置加载成功")
        print()

        # 2. 构建求解器
        print("[2/3] 构建求解器...")
        self.solver = self.builder.build_solver()
        print(f"   求解器创建成功")
        print(f"    - 类型: {self.config['solver']['type']}")
        print(f"    - 网格数: {self.solver.n_cells}")
        print(f"    - dx = {self.solver.dx:.3f} m")
        print(f"    - Riemann求解器: {self.config['solver']['riemann_solver'].upper()}")
        print()

        # 3. 准备输出目录
        print("[3/3] 准备输出...")
        output_dir = Path(self.config['output']['directory'])
        output_dir.mkdir(parents=True, exist_ok=True)
        print(f"   输出目录: {output_dir}")
        print()

        print("=" * 80)
        print("初始化完成，准备开始仿真")
        print("=" * 80)
        print()

    def run(self):
        """运行仿真"""
        sim_cfg = self.config['simulation']

        t_start = sim_cfg['start_time']
        t_end = sim_cfg['end_time']
        output_interval = sim_cfg['output_interval']
        max_steps = sim_cfg['max_steps']

        print("仿真参数:")
        print(f"  开始时间: {t_start} s")
        print(f"  结束时间: {t_end} s")
        print(f"  模拟时长: {t_end - t_start} s")
        print(f"  输出间隔: {output_interval} s")
        print(f"  最大步数: {max_steps}")
        print()

        # 记录初始质量
        initial_mass = self.solver.initial_mass

        # 时间推进
        print("=" * 80)
        print("开始时间推进...")
        print("=" * 80)

        self.start_time = time.time()
        last_output_time = t_start
        last_progress_time = self.start_time
        step = 0

        # 存储输出时刻的数据
        output_times = []
        output_data = []

        # 初始状态输出
        output_times.append(self.solver.t)
        # 计算流速 u = Q / A = Q / (h * B)
        h_safe = np.maximum(self.solver.h, self.solver.eps_dry)
        u_init = self.solver.Q / (h_safe * self.solver.B)

        output_data.append({
            'h': self.solver.h.copy(),
            'Q': self.solver.Q.copy(),
            'u': u_init.copy(),
            't': self.solver.t,
            'dt': 0.0,
            'step': 0
        })

        while self.solver.t < t_end and step < max_steps:
            # 推进一步
            self.solver.step()
            step += 1

            # 输出数据
            if self.solver.t - last_output_time >= output_interval:
                output_times.append(self.solver.t)
                # 计算流速 u = Q / A = Q / (h * B)
                h_safe = np.maximum(self.solver.h, self.solver.eps_dry)
                u_current = self.solver.Q / (h_safe * self.solver.B)

                output_data.append({
                    'h': self.solver.h.copy(),
                    'Q': self.solver.Q.copy(),
                    'u': u_current.copy(),
                    't': self.solver.t,
                    'dt': self.solver.dt,
                    'step': step
                })
                last_output_time = self.solver.t

            # 进度报告（每5秒）
            current_time = time.time()
            if current_time - last_progress_time >= 5.0:
                elapsed = current_time - self.start_time
                progress = (self.solver.t - t_start) / (t_end - t_start) * 100

                # 估算剩余时间
                if progress > 0:
                    total_estimated = elapsed / (progress / 100)
                    eta = total_estimated - elapsed
                else:
                    eta = 0

                print(f"  进度: {progress:5.1f}% | t={self.solver.t:8.2f}s | "
                      f"步数: {step:8d} | dt={self.solver.dt:8.4f}s | "
                      f"已耗时: {elapsed:6.1f}s | 预计剩余: {eta:6.1f}s")

                last_progress_time = current_time

        self.end_time = time.time()

        # 仿真完成
        print()
        print("=" * 80)
        print("仿真完成!")
        print("=" * 80)

        wall_time = self.end_time - self.start_time

        print(f"  总步数: {step}")
        print(f"  模拟时间: {self.solver.t:.2f} s")
        print(f"  墙钟时间: {wall_time:.2f} s")
        print(f"  平均每步: {wall_time/step*1000:.3f} ms")
        print()

        # 质量守恒检查
        mass_error = self.solver.get_mass_conservation_error()
        current_mass = self.solver._compute_total_mass()
        print(f"质量守恒:")
        print(f"  初始质量: {initial_mass:.2f} m³")
        print(f"  当前质量: {current_mass:.2f} m³")
        print(f"  质量误差: {mass_error:.6f}%")

        if abs(mass_error) < 0.1:
            print(f"   质量守恒良好 (<0.1%)")
        elif abs(mass_error) < 1.0:
            print(f"   质量守恒可接受 (<1.0%)")
        else:
            print(f"   质量守恒较差 (>1.0%)")
        print()

        # 计算最终流速
        h_final_safe = np.maximum(self.solver.h, self.solver.eps_dry)
        u_final = self.solver.Q / (h_final_safe * self.solver.B)

        # 保存结果
        self.results = {
            'config': self.config,
            'output_times': output_times,
            'output_data': output_data,
            'final_state': {
                'h': self.solver.h.copy(),
                'Q': self.solver.Q.copy(),
                'u': u_final.copy(),
                't': self.solver.t
            },
            'statistics': {
                'n_steps': step,
                'sim_time': self.solver.t,
                'wall_time': wall_time,
                'time_per_step': wall_time / step,
                'mass_error': mass_error
            },
            'grid': {
                'x': self.solver.x.copy(),
                'dx': self.solver.dx,
                'n_cells': self.solver.n_cells
            }
        }

    def save_results(self):
        """保存结果到文件"""
        output_cfg = self.config['output']
        output_dir = Path(output_cfg['directory'])

        print("=" * 80)
        print("保存结果...")
        print("=" * 80)

        formats = output_cfg['formats']

        # 1. 保存CSV格式
        if 'csv' in formats:
            self._save_csv(output_dir)

        # 2. 保存HDF5格式
        if 'hdf5' in formats:
            self._save_hdf5(output_dir)

        # 3. 保存统计信息
        if output_cfg['statistics']:
            self._save_statistics(output_dir)

        # 4. 生成图表
        if output_cfg['plots']['enabled']:
            self._generate_plots(output_dir)

        print()

    def _save_csv(self, output_dir: Path):
        """保存CSV格式结果"""
        try:
            import pandas as pd
        except ImportError:
            print(f"   CSV格式跳过（需要安装pandas）")
            return

        csv_dir = output_dir / 'csv'
        csv_dir.mkdir(exist_ok=True)

        # 保存最终状态
        df_final = pd.DataFrame({
            'x': self.results['grid']['x'],
            'h': self.results['final_state']['h'],
            'Q': self.results['final_state']['Q'],
            'u': self.results['final_state']['u']
        })

        final_file = csv_dir / 'final_state.csv'
        df_final.to_csv(final_file, index=False)
        print(f"   最终状态: {final_file}")

        # 保存时间序列（选定位置）
        # 选择几个关键位置
        n_cells = len(self.results['grid']['x'])
        key_indices = [0, n_cells//4, n_cells//2, 3*n_cells//4, n_cells-1]

        for idx in key_indices:
            x_loc = self.results['grid']['x'][idx]

            data = {
                't': self.results['output_times'],
                'h': [d['h'][idx] for d in self.results['output_data']],
                'Q': [d['Q'][idx] for d in self.results['output_data']],
                'u': [d['u'][idx] for d in self.results['output_data']]
            }

            df_ts = pd.DataFrame(data)
            ts_file = csv_dir / f'timeseries_x{x_loc:.1f}m.csv'
            df_ts.to_csv(ts_file, index=False)

        print(f"   时间序列: {len(key_indices)}个位置")

    def _save_hdf5(self, output_dir: Path):
        """保存HDF5格式结果"""
        try:
            import h5py

            hdf5_file = output_dir / 'results.h5'

            with h5py.File(hdf5_file, 'w') as f:
                # 网格
                grid_grp = f.create_group('grid')
                grid_grp.create_dataset('x', data=self.results['grid']['x'])
                grid_grp.attrs['dx'] = self.results['grid']['dx']
                grid_grp.attrs['n_cells'] = self.results['grid']['n_cells']

                # 最终状态
                final_grp = f.create_group('final_state')
                final_grp.create_dataset('h', data=self.results['final_state']['h'])
                final_grp.create_dataset('Q', data=self.results['final_state']['Q'])
                final_grp.create_dataset('u', data=self.results['final_state']['u'])
                final_grp.attrs['t'] = self.results['final_state']['t']

                # 时间序列
                ts_grp = f.create_group('time_series')
                ts_grp.create_dataset('times', data=self.results['output_times'])

                # 所有输出时刻的数据
                n_outputs = len(self.results['output_data'])
                n_cells = len(self.results['grid']['x'])

                h_array = np.zeros((n_outputs, n_cells))
                Q_array = np.zeros((n_outputs, n_cells))
                u_array = np.zeros((n_outputs, n_cells))

                for i, data in enumerate(self.results['output_data']):
                    h_array[i, :] = data['h']
                    Q_array[i, :] = data['Q']
                    u_array[i, :] = data['u']

                ts_grp.create_dataset('h', data=h_array)
                ts_grp.create_dataset('Q', data=Q_array)
                ts_grp.create_dataset('u', data=u_array)

                # 统计信息
                stats_grp = f.create_group('statistics')
                for key, value in self.results['statistics'].items():
                    stats_grp.attrs[key] = value

            print(f"   HDF5格式: {hdf5_file}")

        except ImportError:
            print(f"   HDF5格式跳过（需要安装h5py）")

    def _save_statistics(self, output_dir: Path):
        """保存统计信息"""
        stats_file = output_dir / 'statistics.json'

        stats = {
            'project': self.config['project'],
            'simulation': self.results['statistics'],
            'timestamp': datetime.now().isoformat()
        }

        with open(stats_file, 'w', encoding='utf-8') as f:
            json.dump(stats, f, indent=2, ensure_ascii=False)

        print(f"   统计信息: {stats_file}")

    def _generate_plots(self, output_dir: Path):
        """生成图表"""
        import matplotlib.pyplot as plt

        plots_dir = output_dir / 'plots'
        plots_dir.mkdir(exist_ok=True)

        # 设置中文字体
        plt.rcParams['font.sans-serif'] = ['SimHei', 'DejaVu Sans']
        plt.rcParams['axes.unicode_minus'] = False

        # 1. 最终状态图
        fig, axes = plt.subplots(2, 1, figsize=(12, 8))

        x = self.results['grid']['x']
        h = self.results['final_state']['h']
        Q = self.results['final_state']['Q']
        t = self.results['final_state']['t']

        axes[0].plot(x, h, 'b-', linewidth=2)
        axes[0].set_xlabel('Position (m)', fontsize=12)
        axes[0].set_ylabel('Depth h (m)', fontsize=12)
        axes[0].set_title(f'Water Depth at t = {t:.2f} s', fontsize=14)
        axes[0].grid(True, alpha=0.3)

        axes[1].plot(x, Q, 'r-', linewidth=2)
        axes[1].set_xlabel('Position (m)', fontsize=12)
        axes[1].set_ylabel('Discharge Q (m³/s)', fontsize=12)
        axes[1].set_title(f'Discharge at t = {t:.2f} s', fontsize=14)
        axes[1].grid(True, alpha=0.3)

        plt.tight_layout()

        plot_file = plots_dir / 'final_state.png'
        plt.savefig(plot_file, dpi=self.config['output']['plots']['dpi'], bbox_inches='tight')
        plt.close()

        print(f"   最终状态图: {plot_file}")

        # 2. 时空演化图（如果有多个输出）
        if len(self.results['output_data']) > 1:
            self._plot_spacetime_evolution(plots_dir)

    def _plot_spacetime_evolution(self, plots_dir: Path):
        """绘制时空演化图"""
        import matplotlib.pyplot as plt

        n_outputs = len(self.results['output_data'])
        n_cells = len(self.results['grid']['x'])

        # 创建网格
        X = np.tile(self.results['grid']['x'], (n_outputs, 1))
        T = np.tile(np.array(self.results['output_times']).reshape(-1, 1), (1, n_cells))

        # 水深演化
        H = np.array([data['h'] for data in self.results['output_data']])

        fig, ax = plt.subplots(figsize=(12, 8))

        contour = ax.contourf(X, T, H, levels=20, cmap='viridis')
        plt.colorbar(contour, ax=ax, label='Depth h (m)')

        ax.set_xlabel('Position (m)', fontsize=12)
        ax.set_ylabel('Time (s)', fontsize=12)
        ax.set_title('Water Depth Evolution', fontsize=14)

        plot_file = plots_dir / 'spacetime_evolution.png'
        plt.savefig(plot_file, dpi=self.config['output']['plots']['dpi'], bbox_inches='tight')
        plt.close()

        print(f"   时空演化图: {plot_file}")

    def validate(self):
        """验证结果（如果有解析解）"""
        val_cfg = self.config['validation']

        if not val_cfg['enabled']:
            return

        print("=" * 80)
        print("验证结果...")
        print("=" * 80)

        solution_type = val_cfg['analytical_solution']

        if solution_type is None:
            print("  未指定解析解类型，跳过验证")
            return

        # 获取解析解
        x = self.results['grid']['x']
        t = self.results['final_state']['t']

        h_analytical, u_analytical = self.builder.get_analytical_solution(t, x)

        if h_analytical is None:
            print(f"  不支持的解析解类型: {solution_type}")
            return

        # 数值解
        h_numerical = self.results['final_state']['h']
        u_numerical = self.results['final_state']['u']

        # 计算误差
        h_rmse = np.sqrt(np.mean((h_numerical - h_analytical)**2))
        u_rmse = np.sqrt(np.mean((u_numerical - u_analytical)**2))

        h_max_error = np.max(np.abs(h_numerical - h_analytical))
        u_max_error = np.max(np.abs(u_numerical - u_analytical))

        print(f"  解析解类型: {solution_type}")
        print(f"  水深RMSE: {h_rmse:.4f} m")
        print(f"  水深最大误差: {h_max_error:.4f} m")
        print(f"  流速RMSE: {u_rmse:.4f} m/s")
        print(f"  流速最大误差: {u_max_error:.4f} m/s")

        # 检查容差
        tol = val_cfg['tolerance']

        if h_rmse < tol['h_rmse']:
            print(f"   水深误差在容差内 (< {tol['h_rmse']} m)")
        else:
            print(f"   水深误差超出容差 (> {tol['h_rmse']} m)")

        # 保存对比图
        self._plot_validation(x, h_analytical, h_numerical, u_analytical, u_numerical)

        print()

    def _plot_validation(self, x, h_analytical, h_numerical, u_analytical, u_numerical):
        """绘制验证对比图"""
        import matplotlib.pyplot as plt

        output_dir = Path(self.config['output']['directory'])
        plots_dir = output_dir / 'plots'

        fig, axes = plt.subplots(2, 1, figsize=(12, 10))

        # 水深对比
        axes[0].plot(x, h_analytical, 'k--', linewidth=2, label='Analytical')
        axes[0].plot(x, h_numerical, 'b-', linewidth=1.5, label='Numerical')
        axes[0].set_xlabel('Position (m)', fontsize=12)
        axes[0].set_ylabel('Depth h (m)', fontsize=12)
        axes[0].set_title('Water Depth Comparison', fontsize=14)
        axes[0].legend(fontsize=10)
        axes[0].grid(True, alpha=0.3)

        # 流速对比
        axes[1].plot(x, u_analytical, 'k--', linewidth=2, label='Analytical')
        axes[1].plot(x, u_numerical, 'r-', linewidth=1.5, label='Numerical')
        axes[1].set_xlabel('Position (m)', fontsize=12)
        axes[1].set_ylabel('Velocity u (m/s)', fontsize=12)
        axes[1].set_title('Velocity Comparison', fontsize=14)
        axes[1].legend(fontsize=10)
        axes[1].grid(True, alpha=0.3)

        plt.tight_layout()

        plot_file = plots_dir / 'validation_comparison.png'
        plt.savefig(plot_file, dpi=self.config['output']['plots']['dpi'], bbox_inches='tight')
        plt.close()

        print(f"   验证对比图: {plot_file}")


def main():
    """主函数"""
    import argparse

    parser = argparse.ArgumentParser(description='HydroClaude 仿真引擎')
    parser.add_argument('config', help='配置文件路径 (JSON格式)')
    parser.add_argument('--no-plots', action='store_true', help='不生成图表')
    parser.add_argument('--validate', action='store_true', help='启用验证（需要解析解）')

    args = parser.parse_args()

    try:
        # 创建引擎
        engine = SimulationEngine(args.config)

        # 初始化
        engine.initialize()

        # 运行
        engine.run()

        # 保存结果
        engine.save_results()

        # 验证
        if args.validate or engine.config['validation']['enabled']:
            engine.validate()

        print("=" * 80)
        print(" 仿真完成！")
        print("=" * 80)

    except Exception as e:
        print(f"\n 仿真失败:")
        print(f"{e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == '__main__':
    main()
