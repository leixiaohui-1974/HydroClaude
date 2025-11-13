#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
绘图助手 - 提供常用的绘图函数，消除重复代码

提供的功能：
1. 标准化的图表样式
2. 常用图表类型（纵剖面、时序图、等值线图等）
3. 自动处理中文字体问题
4. 统一的保存和显示接口

作者: Claude
日期: 2025-10-23
"""

import numpy as np
import matplotlib.pyplot as plt
from matplotlib.figure import Figure
from matplotlib.axes import Axes
from typing import Optional, List, Tuple, Union
from pathlib import Path


# 默认图表样式配置
DEFAULT_STYLE = {
    'figure.figsize': (12, 8),
    'figure.dpi': 100,
    'axes.grid': True,
    'axes.axisbelow': True,
    'grid.alpha': 0.3,
    'lines.linewidth': 2,
    'font.size': 11,
    'axes.labelsize': 12,
    'axes.titlesize': 14,
    'xtick.labelsize': 10,
    'ytick.labelsize': 10,
    'legend.fontsize': 11,
}


class PlotHelper:
    """绘图助手类 - 提供常用的绘图函数"""

    def __init__(self, style: Optional[dict] = None, use_chinese: bool = False):
        """
        初始化绘图助手

        Args:
            style: 自定义样式字典（会覆盖默认样式）
            use_chinese: 是否尝试配置中文字体（默认False，避免警告）
        """
        self.style = DEFAULT_STYLE.copy()
        if style:
            self.style.update(style)

        if use_chinese:
            self._setup_chinese_font()

    def _setup_chinese_font(self):
        """尝试设置中文字体"""
        try:
            plt.rcParams['font.sans-serif'] = ['SimHei', 'DejaVu Sans']
            plt.rcParams['axes.unicode_minus'] = False
        except:
            pass  # 忽略字体设置失败

    def apply_style(self):
        """应用样式到matplotlib"""
        plt.rcParams.update(self.style)

    def create_figure(self, nrows: int = 1, ncols: int = 1,
                     figsize: Optional[Tuple[float, float]] = None,
                     **kwargs) -> Tuple[Figure, Union[Axes, np.ndarray]]:
        """
        创建图表

        Args:
            nrows: 子图行数
            ncols: 子图列数
            figsize: 图表大小 (width, height)，None则使用默认
            **kwargs: 传递给plt.subplots的其他参数

        Returns:
            (fig, axes): 图表和轴对象
        """
        if figsize is None:
            figsize = self.style.get('figure.figsize', (12, 8))

        fig, axes = plt.subplots(nrows, ncols, figsize=figsize, **kwargs)
        return fig, axes

    def plot_profile(self, x: np.ndarray, y: np.ndarray,
                    xlabel: str = "Distance (m)", ylabel: str = "Value",
                    title: str = "Profile",
                    structures: Optional[List[Tuple[float, str]]] = None,
                    reference_lines: Optional[List[Tuple[float, str]]] = None,
                    figsize: Optional[Tuple[float, float]] = None,
                    save_path: Optional[Union[str, Path]] = None) -> Figure:
        """
        绘制纵剖面图

        Args:
            x: x坐标数组
            y: y坐标数组（可以是单个数组或列表）
            xlabel: x轴标签
            ylabel: y轴标签
            title: 图表标题
            structures: 结构物列表 [(位置, 名称), ...]
            reference_lines: 参考线列表 [(y值, 标签), ...]
            figsize: 图表大小
            save_path: 保存路径（None则不保存）

        Returns:
            Figure对象
        """
        fig, ax = self.create_figure(figsize=figsize)

        # 绘制主曲线
        if isinstance(y, list):
            for i, y_data in enumerate(y):
                ax.plot(x, y_data, linewidth=2, label=f'Series {i+1}')
            ax.legend()
        else:
            ax.plot(x, y, 'b-', linewidth=2)

        # 添加结构物标记
        if structures:
            for pos, name in structures:
                ax.axvline(pos, color='red', linestyle='--', linewidth=1.5, alpha=0.5)
                ax.text(pos, ax.get_ylim()[1] * 0.98, name,
                       color='red', fontsize=10, ha='center', va='top',
                       bbox=dict(boxstyle='round', facecolor='white', alpha=0.8))

        # 添加参考线
        if reference_lines:
            for y_val, label in reference_lines:
                ax.axhline(y_val, color='gray', linestyle='--', linewidth=1, alpha=0.5, label=label)
            ax.legend()

        ax.set_xlabel(xlabel, fontsize=12)
        ax.set_ylabel(ylabel, fontsize=12)
        ax.set_title(title, fontsize=14, fontweight='bold')
        ax.grid(True, alpha=0.3)

        fig.tight_layout()

        if save_path:
            fig.savefig(save_path, dpi=150, bbox_inches='tight')

        return fig

    def plot_dual_profile(self, x: np.ndarray,
                         y1: np.ndarray, y2: np.ndarray,
                         ylabel1: str = "Variable 1",
                         ylabel2: str = "Variable 2",
                         xlabel: str = "Distance (m)",
                         title: str = "Dual Profile",
                         structures: Optional[List[Tuple[float, str]]] = None,
                         figsize: Optional[Tuple[float, float]] = None,
                         save_path: Optional[Union[str, Path]] = None) -> Figure:
        """
        绘制双y轴纵剖面图

        Args:
            x: x坐标数组
            y1: 第一个y数组
            y2: 第二个y数组
            ylabel1: 第一个y轴标签
            ylabel2: 第二个y轴标签
            xlabel: x轴标签
            title: 图表标题
            structures: 结构物列表
            figsize: 图表大小
            save_path: 保存路径

        Returns:
            Figure对象
        """
        if figsize is None:
            figsize = (16, 10)

        fig, (ax1, ax2) = plt.subplots(2, 1, figsize=figsize, sharex=True)

        # 第一个子图
        ax1.plot(x, y1, 'b-', linewidth=2)
        ax1.set_ylabel(ylabel1, fontsize=12)
        ax1.set_title(title, fontsize=14, fontweight='bold')
        ax1.grid(True, alpha=0.3)

        # 第二个子图
        ax2.plot(x, y2, 'g-', linewidth=2)
        ax2.set_xlabel(xlabel, fontsize=12)
        ax2.set_ylabel(ylabel2, fontsize=12)
        ax2.grid(True, alpha=0.3)

        # 添加结构物标记
        if structures:
            for pos, name in structures:
                ax1.axvline(pos, color='red', linestyle='--', linewidth=1.5, alpha=0.5)
                ax1.text(pos, ax1.get_ylim()[1] * 0.98, name,
                        color='red', fontsize=10, ha='center', va='top',
                        bbox=dict(boxstyle='round', facecolor='white', alpha=0.8))
                ax2.axvline(pos, color='red', linestyle='--', linewidth=1.5, alpha=0.5)

        fig.tight_layout()

        if save_path:
            fig.savefig(save_path, dpi=150, bbox_inches='tight')

        return fig

    def plot_time_series(self, time: np.ndarray, data: Union[np.ndarray, List[np.ndarray]],
                        labels: Optional[List[str]] = None,
                        xlabel: str = "Time (s)",
                        ylabel: str = "Value",
                        title: str = "Time Series",
                        reference_lines: Optional[List[Tuple[float, str]]] = None,
                        figsize: Optional[Tuple[float, float]] = None,
                        save_path: Optional[Union[str, Path]] = None) -> Figure:
        """
        绘制时间序列图

        Args:
            time: 时间数组
            data: 数据数组（可以是单个数组或列表）
            labels: 图例标签列表
            xlabel: x轴标签
            ylabel: y轴标签
            title: 图表标题
            reference_lines: 参考线列表
            figsize: 图表大小
            save_path: 保存路径

        Returns:
            Figure对象
        """
        fig, ax = self.create_figure(figsize=figsize)

        # 绘制数据
        if isinstance(data, list):
            for i, y_data in enumerate(data):
                label = labels[i] if labels and i < len(labels) else f'Series {i+1}'
                ax.plot(time, y_data, linewidth=2, label=label)
            ax.legend(fontsize=11, loc='best')
        else:
            ax.plot(time, data, 'b-', linewidth=2)

        # 添加参考线
        if reference_lines:
            for y_val, label in reference_lines:
                ax.axhline(y_val, color='gray', linestyle='--', linewidth=1, alpha=0.5, label=label)
            ax.legend()

        ax.set_xlabel(xlabel, fontsize=12)
        ax.set_ylabel(ylabel, fontsize=12)
        ax.set_title(title, fontsize=14, fontweight='bold')
        ax.grid(True, alpha=0.3)

        fig.tight_layout()

        if save_path:
            fig.savefig(save_path, dpi=150, bbox_inches='tight')

        return fig

    def plot_contour(self, X: np.ndarray, Y: np.ndarray, Z: np.ndarray,
                    xlabel: str = "X", ylabel: str = "Y",
                    zlabel: str = "Z",
                    title: str = "Contour Map",
                    levels: int = 20,
                    cmap: str = 'viridis',
                    vlines: Optional[List[Tuple[float, str]]] = None,
                    figsize: Optional[Tuple[float, float]] = None,
                    save_path: Optional[Union[str, Path]] = None) -> Figure:
        """
        绘制等值线图

        Args:
            X: X网格
            Y: Y网格
            Z: Z数据
            xlabel: x轴标签
            ylabel: y轴标签
            zlabel: 色标标签
            title: 图表标题
            levels: 等值线数量
            cmap: 色图
            vlines: 竖直线列表 [(x位置, 标签), ...]
            figsize: 图表大小
            save_path: 保存路径

        Returns:
            Figure对象
        """
        if figsize is None:
            figsize = (16, 10)

        fig, ax = plt.subplots(figsize=figsize)

        # 绘制等值线
        contour = ax.contourf(X, Y, Z, levels=levels, cmap=cmap)
        cbar = plt.colorbar(contour, ax=ax, label=zlabel)

        # 添加竖直线
        if vlines:
            for x_val, label in vlines:
                ax.axvline(x_val, color='red', linestyle='--', linewidth=1.5, alpha=0.7)
                ax.text(x_val, ax.get_ylim()[1] * 0.95, label,
                       color='red', fontsize=10, ha='center', va='top',
                       bbox=dict(boxstyle='round', facecolor='white', alpha=0.8))

        ax.set_xlabel(xlabel, fontsize=12)
        ax.set_ylabel(ylabel, fontsize=12)
        ax.set_title(title, fontsize=14, fontweight='bold')
        ax.grid(True, alpha=0.3)

        fig.tight_layout()

        if save_path:
            fig.savefig(save_path, dpi=150, bbox_inches='tight')

        return fig

    @staticmethod
    def save_figure(fig: Figure, path: Union[str, Path],
                   dpi: int = 150, **kwargs):
        """
        保存图表

        Args:
            fig: Figure对象
            path: 保存路径
            dpi: 分辨率
            **kwargs: 传递给savefig的其他参数
        """
        fig.savefig(path, dpi=dpi, bbox_inches='tight', **kwargs)

    @staticmethod
    def close_figure(fig: Figure):
        """关闭图表"""
        plt.close(fig)


# 便捷函数
def quick_plot_profile(x: np.ndarray, y: np.ndarray,
                      xlabel: str = "Distance (m)",
                      ylabel: str = "Value",
                      title: str = "Profile",
                      save_path: Optional[Union[str, Path]] = None) -> Figure:
    """
    快速绘制纵剖面图

    Args:
        x: x坐标
        y: y坐标
        xlabel: x轴标签
        ylabel: y轴标签
        title: 标题
        save_path: 保存路径

    Returns:
        Figure对象
    """
    helper = PlotHelper()
    return helper.plot_profile(x, y, xlabel, ylabel, title, save_path=save_path)


def quick_plot_time_series(time: np.ndarray, data: np.ndarray,
                           xlabel: str = "Time (s)",
                           ylabel: str = "Value",
                           title: str = "Time Series",
                           save_path: Optional[Union[str, Path]] = None) -> Figure:
    """
    快速绘制时间序列图

    Args:
        time: 时间数组
        data: 数据数组
        xlabel: x轴标签
        ylabel: y轴标签
        title: 标题
        save_path: 保存路径

    Returns:
        Figure对象
    """
    helper = PlotHelper()
    return helper.plot_time_series(time, data, xlabel=xlabel, ylabel=ylabel,
                                  title=title, save_path=save_path)


if __name__ == "__main__":
    """测试绘图助手"""
    print("=" * 80)
    print("PlotHelper测试")
    print("=" * 80)
    print()

    # 创建助手
    helper = PlotHelper()

    # 测试数据
    x = np.linspace(0, 100, 100)
    y1 = np.sin(x / 10) + 3
    y2 = np.cos(x / 10) + 5

    print("测试1: 简单纵剖面图")
    fig1 = helper.plot_profile(x, y1, xlabel="Distance (km)", ylabel="Water Depth (m)",
                               title="Test Profile")
    print("   纵剖面图创建成功")
    plt.close(fig1)

    print("测试2: 带结构物的纵剖面图")
    structures = [(25, "Gate 1"), (50, "Pump"), (75, "Gate 2")]
    fig2 = helper.plot_profile(x, y1, structures=structures,
                               title="Profile with Structures")
    print("   带结构物的纵剖面图创建成功")
    plt.close(fig2)

    print("测试3: 双剖面图")
    fig3 = helper.plot_dual_profile(x, y1, y2,
                                    ylabel1="Water Depth (m)",
                                    ylabel2="Flow Rate (m³/s)",
                                    structures=structures)
    print("   双剖面图创建成功")
    plt.close(fig3)

    print("测试4: 时间序列图")
    time = np.linspace(0, 3600, 100)
    data = [y1, y2]
    labels = ["Series 1", "Series 2"]
    fig4 = helper.plot_time_series(time, data, labels=labels,
                                   xlabel="Time (s)",
                                   title="Time Series")
    print("   时间序列图创建成功")
    plt.close(fig4)

    print("测试5: 等值线图")
    X, Y = np.meshgrid(x, np.linspace(0, 60, 50))
    Z = np.sin(X/10) * np.cos(Y/10) + 3
    fig5 = helper.plot_contour(X, Y, Z, xlabel="Distance (km)",
                               ylabel="Time (min)",
                               zlabel="Water Depth (m)",
                               vlines=structures)
    print("   等值线图创建成功")
    plt.close(fig5)

    print()
    print(" PlotHelper测试完成！")
    print("=" * 80)
