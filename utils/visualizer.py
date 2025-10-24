"""
高级可视化工具 - Advanced Visualization Utility

提供统一、高级的可视化接口，用于展示水力模拟结果、控制系统性能、
参数估计过程等。支持多种图表类型和自定义样式。

主要功能：
- 水面线可视化
- 时间序列可视化
- 控制性能可视化
- 参数估计收敛可视化
- 多子图布局
- 动画生成
- 交互式图表（可选）

使用示例：
    from utils.visualizer import HydroVisualizer

    # 创建可视化器
    viz = HydroVisualizer(style='scientific')

    # 绘制水面线
    viz.plot_water_surface(x, h, z_bed, title="稳态水面线")

    # 绘制时间序列
    viz.plot_time_series(time, water_level, label="水位")

    # 保存图片
    viz.save_figure("result.png", dpi=300)

作者: Claude Code
创建日期: 2025-10-24
"""

import numpy as np
import matplotlib.pyplot as plt
import matplotlib.gridspec as gridspec
from matplotlib.patches import Rectangle, FancyBboxPatch
from matplotlib.collections import LineCollection
from typing import Dict, List, Tuple, Optional, Union, Any
from pathlib import Path
import json


class HydroVisualizer:
    """水力模拟高级可视化器"""

    # 预定义配色方案
    COLOR_SCHEMES = {
        'default': {
            'water': '#1f77b4',
            'bed': '#8c564b',
            'control': '#ff7f0e',
            'target': '#2ca02c',
            'error': '#d62728'
        },
        'scientific': {
            'water': '#0077be',
            'bed': '#654321',
            'control': '#ff6600',
            'target': '#00a651',
            'error': '#cc0000'
        },
        'presentation': {
            'water': '#4472c4',
            'bed': '#a5a5a5',
            'control': '#ed7d31',
            'target': '#70ad47',
            'error': '#e74c3c'
        }
    }

    # 预定义样式
    STYLES = {
        'default': {
            'font.family': 'sans-serif',
            'font.size': 10,
            'axes.labelsize': 12,
            'axes.titlesize': 14,
            'legend.fontsize': 10,
            'figure.dpi': 100
        },
        'scientific': {
            'font.family': 'serif',
            'font.size': 11,
            'axes.labelsize': 13,
            'axes.titlesize': 15,
            'legend.fontsize': 11,
            'figure.dpi': 150,
            'axes.grid': True,
            'grid.alpha': 0.3
        },
        'presentation': {
            'font.family': 'sans-serif',
            'font.size': 14,
            'axes.labelsize': 16,
            'axes.titlesize': 18,
            'legend.fontsize': 14,
            'figure.dpi': 120,
            'lines.linewidth': 2.5
        }
    }

    def __init__(self, style: str = 'default', color_scheme: str = 'default',
                 figsize: Tuple[float, float] = (10, 6)):
        """
        初始化可视化器

        Args:
            style: 样式名称 ('default', 'scientific', 'presentation')
            color_scheme: 配色方案名称
            figsize: 默认图形尺寸
        """
        self.style = style
        self.color_scheme = color_scheme
        self.figsize = figsize
        self.fig = None
        self.axes = None

        # 应用样式
        if style in self.STYLES:
            plt.rcParams.update(self.STYLES[style])

        # 获取颜色
        self.colors = self.COLOR_SCHEMES.get(color_scheme, self.COLOR_SCHEMES['default'])

    def create_figure(self, nrows: int = 1, ncols: int = 1,
                     figsize: Optional[Tuple[float, float]] = None,
                     **kwargs) -> Tuple[plt.Figure, np.ndarray]:
        """
        创建新图形

        Args:
            nrows: 行数
            ncols: 列数
            figsize: 图形尺寸
            **kwargs: 传递给plt.subplots的其他参数

        Returns:
            (fig, axes)元组
        """
        if figsize is None:
            figsize = self.figsize

        self.fig, self.axes = plt.subplots(nrows, ncols, figsize=figsize, **kwargs)

        return self.fig, self.axes

    def plot_water_surface(self, x: np.ndarray, h: np.ndarray,
                          z_bed: Optional[np.ndarray] = None,
                          ax: Optional[plt.Axes] = None,
                          title: str = "水面线",
                          xlabel: str = "距离 (m)",
                          ylabel: str = "高程 (m)",
                          fill_water: bool = True,
                          show_bed: bool = True,
                          **kwargs) -> plt.Axes:
        """
        绘制水面线

        Args:
            x: 位置坐标
            h: 水深
            z_bed: 河床高程（可选）
            ax: 目标坐标轴
            title: 标题
            xlabel: x轴标签
            ylabel: y轴标签
            fill_water: 是否填充水体
            show_bed: 是否显示河床
            **kwargs: 其他绘图参数

        Returns:
            绘图坐标轴
        """
        if ax is None:
            if self.fig is None:
                self.create_figure()
            ax = self.axes if isinstance(self.axes, plt.Axes) else self.axes[0]

        # 计算水面高程
        if z_bed is not None:
            water_surface = z_bed + h
        else:
            z_bed = np.zeros_like(x)
            water_surface = h

        # 绘制水面线
        ax.plot(x, water_surface, color=self.colors['water'],
               linewidth=2, label='水面线', **kwargs)

        # 填充水体
        if fill_water:
            ax.fill_between(x, z_bed, water_surface,
                           color=self.colors['water'], alpha=0.3)

        # 绘制河床
        if show_bed:
            ax.plot(x, z_bed, color=self.colors['bed'],
                   linewidth=1.5, label='河床', linestyle='--')
            ax.fill_between(x, z_bed - 0.5, z_bed,
                           color=self.colors['bed'], alpha=0.2)

        ax.set_xlabel(xlabel)
        ax.set_ylabel(ylabel)
        ax.set_title(title)
        ax.legend()
        ax.grid(True, alpha=0.3)

        return ax

    def plot_time_series(self, time: np.ndarray, data: Union[np.ndarray, Dict[str, np.ndarray]],
                        ax: Optional[plt.Axes] = None,
                        title: str = "时间序列",
                        xlabel: str = "时间 (s)",
                        ylabel: str = "值",
                        labels: Optional[List[str]] = None,
                        colors: Optional[List[str]] = None,
                        show_legend: bool = True,
                        **kwargs) -> plt.Axes:
        """
        绘制时间序列

        Args:
            time: 时间数组
            data: 数据（数组或字典）
            ax: 目标坐标轴
            title: 标题
            xlabel: x轴标签
            ylabel: y轴标签
            labels: 数据标签列表
            colors: 颜色列表
            show_legend: 是否显示图例
            **kwargs: 其他绘图参数

        Returns:
            绘图坐标轴
        """
        if ax is None:
            if self.fig is None:
                self.create_figure()
            ax = self.axes if isinstance(self.axes, plt.Axes) else self.axes[0]

        # 处理数据格式
        if isinstance(data, dict):
            # 字典格式：{label: array}
            for i, (label, values) in enumerate(data.items()):
                color = colors[i] if colors and i < len(colors) else None
                ax.plot(time, values, label=label, color=color, **kwargs)
        elif data.ndim == 1:
            # 一维数组
            label = labels[0] if labels else None
            color = colors[0] if colors else None
            ax.plot(time, data, label=label, color=color, **kwargs)
        else:
            # 二维数组：每列一条曲线
            for i in range(data.shape[1]):
                label = labels[i] if labels and i < len(labels) else f"Series {i+1}"
                color = colors[i] if colors and i < len(colors) else None
                ax.plot(time, data[:, i], label=label, color=color, **kwargs)

        ax.set_xlabel(xlabel)
        ax.set_ylabel(ylabel)
        ax.set_title(title)
        if show_legend:
            ax.legend()
        ax.grid(True, alpha=0.3)

        return ax

    def plot_control_performance(self, time: np.ndarray,
                                actual: np.ndarray,
                                target: Union[float, np.ndarray],
                                control: Optional[np.ndarray] = None,
                                ax: Optional[Union[plt.Axes, List[plt.Axes]]] = None,
                                title: str = "控制性能",
                                **kwargs) -> Union[plt.Axes, List[plt.Axes]]:
        """
        绘制控制性能（状态跟踪 + 控制输入）

        Args:
            time: 时间数组
            actual: 实际值
            target: 目标值
            control: 控制输入（可选）
            ax: 目标坐标轴（单个或列表）
            title: 标题
            **kwargs: 其他参数

        Returns:
            坐标轴或坐标轴列表
        """
        # 确定是否需要两个子图
        need_two_plots = control is not None

        if ax is None:
            if need_two_plots:
                self.create_figure(nrows=2, ncols=1, figsize=(10, 8),
                                 sharex=True)
                ax = self.axes
            else:
                self.create_figure()
                ax = [self.axes] if isinstance(self.axes, plt.Axes) else [self.axes[0]]
        elif not isinstance(ax, list):
            ax = [ax]

        # 第一个子图：状态跟踪
        ax[0].plot(time, actual, label='实际值', color=self.colors['water'],
                  linewidth=2)

        if isinstance(target, (int, float)):
            ax[0].axhline(y=target, label='目标值', color=self.colors['target'],
                         linestyle='--', linewidth=2)
        else:
            ax[0].plot(time, target, label='目标值', color=self.colors['target'],
                      linestyle='--', linewidth=2)

        ax[0].set_ylabel('状态值')
        ax[0].set_title(title)
        ax[0].legend()
        ax[0].grid(True, alpha=0.3)

        # 第二个子图：控制输入
        if need_two_plots and len(ax) > 1:
            ax[1].plot(time, control, label='控制输入', color=self.colors['control'],
                      linewidth=2)
            ax[1].set_xlabel('时间 (s)')
            ax[1].set_ylabel('控制输入')
            ax[1].legend()
            ax[1].grid(True, alpha=0.3)

        return ax if need_two_plots else ax[0]

    def plot_parameter_convergence(self, iterations: np.ndarray,
                                   estimated: np.ndarray,
                                   true_value: Optional[float] = None,
                                   ax: Optional[plt.Axes] = None,
                                   title: str = "参数收敛过程",
                                   param_name: str = "参数",
                                   **kwargs) -> plt.Axes:
        """
        绘制参数估计收敛过程

        Args:
            iterations: 迭代步数
            estimated: 估计值历史
            true_value: 真实值（可选）
            ax: 目标坐标轴
            title: 标题
            param_name: 参数名称
            **kwargs: 其他参数

        Returns:
            绘图坐标轴
        """
        if ax is None:
            if self.fig is None:
                self.create_figure()
            ax = self.axes if isinstance(self.axes, plt.Axes) else self.axes[0]

        # 绘制估计值演化
        ax.plot(iterations, estimated, label=f'估计的{param_name}',
               color=self.colors['water'], linewidth=2, **kwargs)

        # 绘制真实值
        if true_value is not None:
            ax.axhline(y=true_value, label=f'真实{param_name}',
                      color=self.colors['target'], linestyle='--', linewidth=2)

            # 计算误差百分比
            if len(estimated) > 0:
                final_error = abs(estimated[-1] - true_value) / true_value * 100
                ax.text(0.7, 0.95, f'最终误差: {final_error:.2f}%',
                       transform=ax.transAxes, verticalalignment='top',
                       bbox=dict(boxstyle='round', facecolor='wheat', alpha=0.5))

        ax.set_xlabel('迭代步数')
        ax.set_ylabel(param_name)
        ax.set_title(title)
        ax.legend()
        ax.grid(True, alpha=0.3)

        return ax

    def plot_comparison(self, x: np.ndarray,
                       data_dict: Dict[str, np.ndarray],
                       ax: Optional[plt.Axes] = None,
                       title: str = "对比分析",
                       xlabel: str = "x",
                       ylabel: str = "y",
                       styles: Optional[Dict[str, Dict]] = None,
                       **kwargs) -> plt.Axes:
        """
        绘制多组数据对比

        Args:
            x: x轴数据
            data_dict: 数据字典 {label: y_data}
            ax: 目标坐标轴
            title: 标题
            xlabel: x轴标签
            ylabel: y轴标签
            styles: 样式字典 {label: {color, linestyle, ...}}
            **kwargs: 其他参数

        Returns:
            绘图坐标轴
        """
        if ax is None:
            if self.fig is None:
                self.create_figure()
            ax = self.axes if isinstance(self.axes, plt.Axes) else self.axes[0]

        for i, (label, y_data) in enumerate(data_dict.items()):
            # 获取该系列的样式
            style = styles.get(label, {}) if styles else {}

            # 合并kwargs和特定样式
            plot_kwargs = {**kwargs, **style}

            ax.plot(x, y_data, label=label, **plot_kwargs)

        ax.set_xlabel(xlabel)
        ax.set_ylabel(ylabel)
        ax.set_title(title)
        ax.legend()
        ax.grid(True, alpha=0.3)

        return ax

    def plot_structure(self, x_pos: float, structure_type: str,
                      ax: plt.Axes,
                      height: float = 1.0,
                      **kwargs):
        """
        在水面线图上绘制结构物标记

        Args:
            x_pos: 结构物位置
            structure_type: 结构物类型
            ax: 目标坐标轴
            height: 标记高度
            **kwargs: 其他参数
        """
        # 结构物图标映射
        structure_markers = {
            'gate': ('▼', 'red'),
            'pump': ('⊗', 'blue'),
            'weir': ('═', 'green'),
            'drop': ('⊥', 'orange')
        }

        marker, color = structure_markers.get(structure_type.lower(), ('│', 'black'))

        # 获取y轴范围
        y_min, y_max = ax.get_ylim()

        # 绘制垂直线
        ax.axvline(x=x_pos, color=color, linestyle=':', alpha=0.7, **kwargs)

        # 添加标记
        ax.text(x_pos, y_max * 0.95, marker,
               horizontalalignment='center',
               verticalalignment='top',
               fontsize=14, color=color)

    def create_dashboard(self, time: np.ndarray,
                        water_level: np.ndarray,
                        flow_rate: np.ndarray,
                        control_input: np.ndarray,
                        target_level: Union[float, np.ndarray],
                        title: str = "控制系统仪表板",
                        figsize: Tuple[float, float] = (14, 10)) -> plt.Figure:
        """
        创建控制系统仪表板（多子图综合展示）

        Args:
            time: 时间数组
            water_level: 水位数据
            flow_rate: 流量数据
            control_input: 控制输入
            target_level: 目标水位
            title: 标题
            figsize: 图形尺寸

        Returns:
            图形对象
        """
        fig = plt.figure(figsize=figsize)
        gs = gridspec.GridSpec(3, 2, figure=fig, hspace=0.3, wspace=0.3)

        # 1. 水位跟踪
        ax1 = fig.add_subplot(gs[0, :])
        ax1.plot(time, water_level, label='实际水位', color=self.colors['water'], linewidth=2)
        if isinstance(target_level, (int, float)):
            ax1.axhline(y=target_level, label='目标水位', color=self.colors['target'],
                       linestyle='--', linewidth=2)
        else:
            ax1.plot(time, target_level, label='目标水位', color=self.colors['target'],
                    linestyle='--', linewidth=2)
        ax1.set_ylabel('水位 (m)')
        ax1.set_title('水位跟踪')
        ax1.legend()
        ax1.grid(True, alpha=0.3)

        # 2. 流量变化
        ax2 = fig.add_subplot(gs[1, 0])
        ax2.plot(time, flow_rate, color='#2ca02c', linewidth=2)
        ax2.set_ylabel('流量 (m³/s)')
        ax2.set_title('流量变化')
        ax2.grid(True, alpha=0.3)

        # 3. 控制输入
        ax3 = fig.add_subplot(gs[1, 1])
        ax3.plot(time, control_input, color=self.colors['control'], linewidth=2)
        ax3.set_ylabel('控制输入')
        ax3.set_title('控制信号')
        ax3.grid(True, alpha=0.3)

        # 4. 误差分析
        ax4 = fig.add_subplot(gs[2, 0])
        if isinstance(target_level, (int, float)):
            error = water_level - target_level
        else:
            error = water_level - target_level
        ax4.plot(time, error, color=self.colors['error'], linewidth=2)
        ax4.axhline(y=0, color='black', linestyle='-', linewidth=0.5)
        ax4.set_xlabel('时间 (s)')
        ax4.set_ylabel('误差 (m)')
        ax4.set_title('跟踪误差')
        ax4.grid(True, alpha=0.3)

        # 5. 性能指标
        ax5 = fig.add_subplot(gs[2, 1])
        ax5.axis('off')

        # 计算性能指标
        mae = np.mean(np.abs(error))
        rmse = np.sqrt(np.mean(error**2))
        max_error = np.max(np.abs(error))

        # 显示指标
        metrics_text = f"""
        性能指标:

        MAE:  {mae:.4f} m
        RMSE: {rmse:.4f} m
        最大误差: {max_error:.4f} m

        控制信号统计:
        均值: {np.mean(control_input):.2f}
        标准差: {np.std(control_input):.2f}
        """

        ax5.text(0.1, 0.5, metrics_text, transform=ax5.transAxes,
                fontsize=11, verticalalignment='center',
                fontfamily='monospace',
                bbox=dict(boxstyle='round', facecolor='lightblue', alpha=0.3))

        fig.suptitle(title, fontsize=16, fontweight='bold')

        self.fig = fig
        return fig

    def save_figure(self, filename: str, dpi: int = 300,
                   bbox_inches: str = 'tight', **kwargs):
        """
        保存当前图形

        Args:
            filename: 文件名
            dpi: 分辨率
            bbox_inches: 边界框设置
            **kwargs: 其他参数
        """
        if self.fig is None:
            print("警告：没有可保存的图形")
            return

        output_path = Path(filename)
        self.fig.savefig(output_path, dpi=dpi, bbox_inches=bbox_inches, **kwargs)
        print(f"图形已保存: {output_path}")

    def close(self):
        """关闭当前图形"""
        if self.fig is not None:
            plt.close(self.fig)
            self.fig = None
            self.axes = None


def demo():
    """演示可视化功能"""
    print("="*70)
    print("  HydroVisualizer 演示")
    print("="*70 + "\n")

    # 创建可视化器
    viz = HydroVisualizer(style='scientific', color_scheme='scientific')

    # 示例1：水面线
    print("1. 绘制水面线...")
    x = np.linspace(0, 5000, 100)
    z_bed = -0.0001 * x  # 河床坡度
    h = 2.5 - 0.00005 * x + 0.2 * np.sin(x / 500)  # 水深

    viz.create_figure(figsize=(12, 5))
    viz.plot_water_surface(x, h, z_bed, title="渠道水面线示例")
    viz.save_figure("demo_water_surface.png")
    viz.close()

    # 示例2：控制性能
    print("2. 绘制控制性能...")
    time = np.linspace(0, 3600, 360)
    target = 2.5
    actual = target + 0.5 * np.exp(-time/600) * np.sin(time/100) + np.random.normal(0, 0.05, len(time))
    control = 15 + 5 * np.exp(-time/800) * np.cos(time/150)

    viz.create_figure(nrows=2, ncols=1, figsize=(12, 8), sharex=True)
    viz.plot_control_performance(time, actual, target, control, ax=viz.axes,
                                title="PID控制性能示例")
    viz.save_figure("demo_control_performance.png")
    viz.close()

    # 示例3：参数收敛
    print("3. 绘制参数收敛...")
    iterations = np.arange(0, 200)
    true_value = 0.025
    estimated = true_value + 0.01 * np.exp(-iterations/30) + np.random.normal(0, 0.0005, len(iterations))

    viz.create_figure()
    viz.plot_parameter_convergence(iterations, estimated, true_value,
                                  title="糙率参数估计收敛",
                                  param_name="Manning糙率")
    viz.save_figure("demo_parameter_convergence.png")
    viz.close()

    # 示例4：仪表板
    print("4. 创建控制仪表板...")
    dashboard_fig = viz.create_dashboard(time, actual, control, control, target,
                                        title="控制系统综合仪表板")
    viz.save_figure("demo_dashboard.png", dpi=200)
    viz.close()

    print("\n✅ 演示完成！生成了4个示例图片。")


if __name__ == "__main__":
    demo()
