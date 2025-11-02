#!/usr/bin/env python3
"""
HydroClaude 结果可视化工具

功能: 为模拟结果生成专业级可视化图表
- 时间序列图
- 空间分布图
- 相关性分析
- 对比图表
- 多面板布局
- 自定义样式

用法:
    python tools/visualize_results.py simulation_results.npz --plot-type all
    python tools/visualize_results.py simulation_results.npz --plot-type timeseries
    python tools/visualize_results.py simulation_results.npz --plot-type spatial --time-index -1

作者: HydroClaude Team
日期: 2025-11-02
版本: v1.0
"""

import numpy as np
import matplotlib.pyplot as plt
from matplotlib.gridspec import GridSpec
from pathlib import Path
import argparse
from datetime import datetime

class ResultsVisualizer:
    """结果可视化器"""

    def __init__(self, data_file, output_dir=None, style='seaborn-v0_8-darkgrid'):
        """
        初始化可视化器

        Parameters:
        -----------
        data_file : str
            NPZ数据文件路径
        output_dir : str, optional
            输出目录
        style : str
            Matplotlib 样式
        """
        self.data_file = Path(data_file)
        self.data = None
        self.times = None

        # 输出目录
        if output_dir is None:
            self.output_dir = self.data_file.parent / 'figures'
        else:
            self.output_dir = Path(output_dir)
        self.output_dir.mkdir(exist_ok=True)

        # 设置绘图风格
        try:
            plt.style.use(style)
        except:
            plt.style.use('default')

        # 颜色方案
        self.colors = {
            'water_temperature': '#FF6B6B',
            'dissolved_oxygen': '#4ECDC4',
            'ice_thickness': '#95E1D3',
            'ice_cover_fraction': '#A8E6CF',
            'NH4': '#FFD93D',
            'NO3': '#FFA07A',
            'PO4': '#DDA15E',
            'chlorophyll_a': '#06D6A0',
            'TN': '#FFB703',
            'TP': '#FB8500'
        }

    def load_data(self):
        """加载NPZ数据"""
        print(f"加载数据: {self.data_file}")
        self.data = np.load(self.data_file)

        # 提取时间
        if 'times' in self.data:
            self.times = self.data['times']
        else:
            # 假设时间序列
            n_times = len(next(iter(self.data.values())))
            self.times = np.arange(n_times)

        print(f"  时间点数: {len(self.times)}")
        print(f"  变量数: {len(self.data.keys())}")
        print()

    def plot_timeseries(self, variables=None, save=True):
        """
        绘制时间序列图

        Parameters:
        -----------
        variables : list, optional
            要绘制的变量列表
        save : bool
            是否保存图片
        """
        if self.data is None:
            self.load_data()

        # 选择变量
        if variables is None:
            variables = [k for k in self.data.keys() if k != 'times']

        # 过滤空数组
        valid_vars = []
        for var in variables:
            if var in self.data and len(self.data[var]) > 0:
                valid_vars.append(var)
        variables = valid_vars

        if len(variables) == 0:
            print("⚠ 没有有效变量可绘制")
            return

        print(f"绘制时间序列图: {len(variables)} 个变量")

        # 创建子图
        n_vars = len(variables)
        fig, axes = plt.subplots(n_vars, 1, figsize=(12, 3*n_vars), sharex=True)

        if n_vars == 1:
            axes = [axes]

        for i, var in enumerate(variables):
            ax = axes[i]
            data = self.data[var]

            # 检查数据维度
            if len(data.shape) == 1:
                # 时间序列
                y = data
            else:
                # 空间分布，取平均
                y = data.mean(axis=1)

            # 调整时间和数据长度
            times = self.times[:len(y)]

            # 绘制
            color = self.colors.get(var, 'blue')
            ax.plot(times, y, color=color, linewidth=2, label=var)

            # 标注
            ax.set_ylabel(self._get_label(var), fontsize=12)
            ax.legend(loc='upper right')
            ax.grid(True, alpha=0.3)

        # X轴标签
        axes[-1].set_xlabel('时间 (天)', fontsize=12)

        # 标题
        fig.suptitle('HydroClaude 模拟结果 - 时间序列', fontsize=16, fontweight='bold')
        plt.tight_layout()

        # 保存
        if save:
            output_file = self.output_dir / 'timeseries.png'
            plt.savefig(output_file, dpi=300, bbox_inches='tight')
            print(f"✓ 保存: {output_file}")

        plt.close()

    def plot_dashboard(self, save=True):
        """
        绘制仪表板（多面板综合图）

        Parameters:
        -----------
        save : bool
            是否保存图片
        """
        if self.data is None:
            self.load_data()

        print("绘制综合仪表板")

        # 创建图形
        fig = plt.figure(figsize=(16, 10))
        gs = GridSpec(3, 3, figure=fig, hspace=0.3, wspace=0.3)

        # 1. 水温和冰盖
        ax1 = fig.add_subplot(gs[0, :2])
        self._plot_temperature_ice(ax1)

        # 2. 溶解氧
        ax2 = fig.add_subplot(gs[1, :2])
        self._plot_do(ax2)

        # 3. 营养盐
        ax3 = fig.add_subplot(gs[2, :2])
        self._plot_nutrients(ax3)

        # 4. 叶绿素
        ax4 = fig.add_subplot(gs[0, 2])
        self._plot_chlorophyll(ax4)

        # 5. 统计摘要
        ax5 = fig.add_subplot(gs[1, 2])
        self._plot_statistics(ax5)

        # 6. 相关性矩阵
        ax6 = fig.add_subplot(gs[2, 2])
        self._plot_correlation(ax6)

        # 标题
        fig.suptitle('HydroClaude 模拟结果仪表板', fontsize=18, fontweight='bold')

        # 保存
        if save:
            output_file = self.output_dir / 'dashboard.png'
            plt.savefig(output_file, dpi=300, bbox_inches='tight')
            print(f"✓ 保存: {output_file}")

        plt.close()

    def _plot_temperature_ice(self, ax):
        """绘制水温和冰盖"""
        # 水温
        if 'water_temperature' in self.data and len(self.data['water_temperature']) > 0:
            T = self.data['water_temperature']
            if len(T.shape) > 1:
                T = T.mean(axis=1)
            times = self.times[:len(T)]
            ax.plot(times, T, color=self.colors['water_temperature'],
                   linewidth=2, label='水温')
            ax.set_ylabel('水温 (°C)', color=self.colors['water_temperature'])
            ax.tick_params(axis='y', labelcolor=self.colors['water_temperature'])

        # 冰盖（双Y轴）
        if 'ice_thickness' in self.data and len(self.data['ice_thickness']) > 0:
            ice = self.data['ice_thickness']
            if len(ice.shape) > 1:
                ice = ice.mean(axis=1)
            times_ice = self.times[:len(ice)]

            ax2 = ax.twinx()
            ax2.plot(times_ice, ice, color=self.colors['ice_thickness'],
                    linewidth=2, linestyle='--', label='冰厚')
            ax2.set_ylabel('冰厚 (m)', color=self.colors['ice_thickness'])
            ax2.tick_params(axis='y', labelcolor=self.colors['ice_thickness'])

        ax.set_xlabel('时间 (天)')
        ax.grid(True, alpha=0.3)
        ax.legend(loc='upper left')
        ax.set_title('水温和冰盖动态')

    def _plot_do(self, ax):
        """绘制溶解氧"""
        if 'dissolved_oxygen' in self.data and len(self.data['dissolved_oxygen']) > 0:
            DO = self.data['dissolved_oxygen']
            if len(DO.shape) > 1:
                DO = DO.mean(axis=1)
            times = self.times[:len(DO)]

            ax.plot(times, DO, color=self.colors['dissolved_oxygen'],
                   linewidth=2, label='溶解氧')
            ax.axhline(y=5.0, color='red', linestyle='--',
                      alpha=0.5, label='低氧阈值 (5 mg/L)')
            ax.set_ylabel('溶解氧 (mg/L)')
            ax.set_xlabel('时间 (天)')
            ax.grid(True, alpha=0.3)
            ax.legend()
            ax.set_title('溶解氧变化')

    def _plot_nutrients(self, ax):
        """绘制营养盐"""
        nutrient_vars = ['NH4', 'NO3', 'PO4']
        labels = ['NH₄⁺', 'NO₃⁻', 'PO₄³⁻']

        for var, label in zip(nutrient_vars, labels):
            if var in self.data and len(self.data[var]) > 0:
                data = self.data[var]
                if len(data.shape) > 1:
                    data = data.mean(axis=1)
                times = self.times[:len(data)]

                color = self.colors.get(var, 'gray')
                ax.plot(times, data, color=color, linewidth=2, label=label)

        ax.set_ylabel('浓度 (mg/L)')
        ax.set_xlabel('时间 (天)')
        ax.grid(True, alpha=0.3)
        ax.legend()
        ax.set_title('营养盐动态')

    def _plot_chlorophyll(self, ax):
        """绘制叶绿素"""
        if 'chlorophyll_a' in self.data and len(self.data['chlorophyll_a']) > 0:
            Chla = self.data['chlorophyll_a']
            if len(Chla.shape) > 1:
                Chla = Chla.mean(axis=1)
            times = self.times[:len(Chla)]

            ax.plot(times, Chla, color=self.colors['chlorophyll_a'],
                   linewidth=2)
            ax.fill_between(times, 0, Chla, color=self.colors['chlorophyll_a'],
                           alpha=0.3)
            ax.set_ylabel('叶绿素 a\n(μg/L)')
            ax.set_xlabel('时间 (天)')
            ax.grid(True, alpha=0.3)
            ax.set_title('藻类生物量')

    def _plot_statistics(self, ax):
        """绘制统计摘要"""
        ax.axis('off')

        # 计算关键统计
        stats_text = "统计摘要\n" + "="*20 + "\n\n"

        key_vars = ['water_temperature', 'dissolved_oxygen', 'chlorophyll_a']
        labels = ['水温 (°C)', '溶解氧 (mg/L)', '叶绿素 (μg/L)']

        for var, label in zip(key_vars, labels):
            if var in self.data and len(self.data[var]) > 0:
                data = self.data[var]
                if len(data.shape) > 1:
                    data = data.mean(axis=1)

                mean_val = data.mean()
                min_val = data.min()
                max_val = data.max()

                stats_text += f"{label}\n"
                stats_text += f"  均值: {mean_val:.2f}\n"
                stats_text += f"  范围: {min_val:.2f} - {max_val:.2f}\n\n"

        ax.text(0.1, 0.9, stats_text, transform=ax.transAxes,
               fontsize=10, verticalalignment='top',
               family='monospace',
               bbox=dict(boxstyle='round', facecolor='wheat', alpha=0.5))

    def _plot_correlation(self, ax):
        """绘制相关性矩阵"""
        # 收集数据
        vars_to_correlate = ['water_temperature', 'dissolved_oxygen',
                            'NH4', 'NO3', 'chlorophyll_a']
        var_data = {}

        for var in vars_to_correlate:
            if var in self.data and len(self.data[var]) > 0:
                data = self.data[var]
                if len(data.shape) > 1:
                    data = data.mean(axis=1)
                var_data[var] = data

        if len(var_data) < 2:
            ax.text(0.5, 0.5, '数据不足', ha='center', va='center',
                   transform=ax.transAxes)
            ax.axis('off')
            return

        # 对齐数据长度
        min_len = min(len(v) for v in var_data.values())
        for k in var_data:
            var_data[k] = var_data[k][:min_len]

        # 计算相关性
        var_names = list(var_data.keys())
        n_vars = len(var_names)
        corr_matrix = np.zeros((n_vars, n_vars))

        for i, var1 in enumerate(var_names):
            for j, var2 in enumerate(var_names):
                corr_matrix[i, j] = np.corrcoef(var_data[var1], var_data[var2])[0, 1]

        # 绘制热图
        im = ax.imshow(corr_matrix, cmap='RdBu_r', vmin=-1, vmax=1)
        ax.set_xticks(range(n_vars))
        ax.set_yticks(range(n_vars))
        ax.set_xticklabels([self._short_label(v) for v in var_names],
                          rotation=45, ha='right', fontsize=8)
        ax.set_yticklabels([self._short_label(v) for v in var_names],
                          fontsize=8)
        ax.set_title('相关性矩阵', fontsize=10)

        # 添加数值
        for i in range(n_vars):
            for j in range(n_vars):
                text = ax.text(j, i, f'{corr_matrix[i, j]:.2f}',
                             ha="center", va="center", color="black", fontsize=7)

        plt.colorbar(im, ax=ax, fraction=0.046, pad=0.04)

    def plot_spatial(self, time_index=-1, variables=None, save=True):
        """
        绘制空间分布图

        Parameters:
        -----------
        time_index : int
            时间索引
        variables : list, optional
            要绘制的变量
        save : bool
            是否保存
        """
        if self.data is None:
            self.load_data()

        time_value = self.times[time_index]
        print(f"绘制空间分布: t = {time_value:.2f} 天")

        # 找出空间变量
        spatial_vars = []
        for var in self.data.keys():
            if var == 'times':
                continue
            data = self.data[var]
            if len(data.shape) > 1 and data.shape[0] > 0:
                spatial_vars.append(var)

        if len(spatial_vars) == 0:
            print("⚠ 没有空间分布数据")
            return

        if variables is not None:
            spatial_vars = [v for v in spatial_vars if v in variables]

        # 创建子图
        n_vars = len(spatial_vars)
        fig, axes = plt.subplots(n_vars, 1, figsize=(12, 3*n_vars), sharex=True)

        if n_vars == 1:
            axes = [axes]

        for i, var in enumerate(spatial_vars):
            ax = axes[i]
            data = self.data[var][time_index, :]
            x = np.arange(len(data)) * 100  # 假设dx=100m

            color = self.colors.get(var, 'blue')
            ax.plot(x, data, color=color, linewidth=2)
            ax.fill_between(x, 0, data, color=color, alpha=0.3)
            ax.set_ylabel(self._get_label(var))
            ax.grid(True, alpha=0.3)

        axes[-1].set_xlabel('距离 (m)')
        fig.suptitle(f'空间分布 (t = {time_value:.2f} 天)',
                    fontsize=16, fontweight='bold')
        plt.tight_layout()

        if save:
            output_file = self.output_dir / f'spatial_t{time_index:04d}.png'
            plt.savefig(output_file, dpi=300, bbox_inches='tight')
            print(f"✓ 保存: {output_file}")

        plt.close()

    def _get_label(self, var_name):
        """获取变量标签"""
        labels = {
            'water_temperature': '水温 (°C)',
            'dissolved_oxygen': '溶解氧 (mg/L)',
            'ice_thickness': '冰厚 (m)',
            'ice_cover_fraction': '冰盖面积比 (-)',
            'NH4': 'NH₄⁺ (mg/L)',
            'NO3': 'NO₃⁻ (mg/L)',
            'PO4': 'PO₄³⁻ (mg/L)',
            'chlorophyll_a': '叶绿素 a (μg/L)'
        }
        return labels.get(var_name, var_name)

    def _short_label(self, var_name):
        """获取短标签"""
        labels = {
            'water_temperature': '水温',
            'dissolved_oxygen': 'DO',
            'ice_thickness': '冰厚',
            'NH4': 'NH4',
            'NO3': 'NO3',
            'PO4': 'PO4',
            'chlorophyll_a': 'Chla'
        }
        return labels.get(var_name, var_name[:6])


def main():
    """命令行接口"""
    parser = argparse.ArgumentParser(description='Visualize HydroClaude simulation results')
    parser.add_argument('input', type=str, help='Input NPZ file')
    parser.add_argument('--plot-type', type=str, default='all',
                       choices=['timeseries', 'dashboard', 'spatial', 'all'],
                       help='Plot type')
    parser.add_argument('--output-dir', type=str, default=None,
                       help='Output directory')
    parser.add_argument('--variables', type=str, nargs='+', default=None,
                       help='Variables to plot')
    parser.add_argument('--time-index', type=int, default=-1,
                       help='Time index for spatial plot')
    parser.add_argument('--style', type=str, default='seaborn-v0_8-darkgrid',
                       help='Matplotlib style')

    args = parser.parse_args()

    print("=" * 70)
    print("HydroClaude 结果可视化工具")
    print("=" * 70)
    print()

    # 创建可视化器
    viz = ResultsVisualizer(args.input, args.output_dir, args.style)

    # 加载数据
    viz.load_data()

    # 生成图表
    if args.plot_type == 'timeseries' or args.plot_type == 'all':
        viz.plot_timeseries(args.variables)

    if args.plot_type == 'dashboard' or args.plot_type == 'all':
        viz.plot_dashboard()

    if args.plot_type == 'spatial' or args.plot_type == 'all':
        viz.plot_spatial(args.time_index, args.variables)

    print()
    print("=" * 70)
    print(f"可视化完成! 输出目录: {viz.output_dir}")
    print("=" * 70)


if __name__ == '__main__':
    main()
