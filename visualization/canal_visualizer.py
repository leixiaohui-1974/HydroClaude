#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
明渠水力学可视化模块

提供标准化的可视化功能：
- 时空分布图
- 时间序列图
- 方法对比图
- 性能评估图
- 动画生成

作者: Claude
日期: 2025-10-21
"""

import numpy as np
import warnings

# 全局抑制所有matplotlib相关警告（包括字体警告）
warnings.filterwarnings('ignore', category=UserWarning)
warnings.filterwarnings('ignore', module='matplotlib')
warnings.filterwarnings('ignore', module='matplotlib.font_manager')

import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.animation import FuncAnimation, PillowWriter
from typing import Dict, List, Optional, Tuple
import sys
import os

# 添加父目录到路径
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from utils.canal_utils import setup_chinese_fonts


class CanalVisualizer:
    """明渠可视化器"""

    def __init__(self, use_chinese: bool = True, font_size: int = 11):
        """
        初始化可视化器

        Args:
            use_chinese: 是否使用中文字体
            font_size: 字体大小
        """
        if use_chinese:
            setup_chinese_fonts(font_size)

        self.colors = {
            'EXPLICIT': '#1f77b4',
            'PREISSMANN': '#ff7f0e',
            'HLL': '#2ca02c',
            'theory': '#d62728'
        }

        self.linestyles = {
            'EXPLICIT': '-',
            'PREISSMANN': '--',
            'HLL': '-.',
            'theory': ':'
        }

    def plot_spatial_distribution(self, x: np.ndarray, h: np.ndarray, Q: np.ndarray,
                                  h_theory: float, Q_theory: float,
                                  title: str = "空间分布",
                                  save_path: Optional[str] = None,
                                  h_margin: float = 0.01,
                                  Q_margin: float = 0.05):
        """
        绘制空间分布图

        Args:
            x: 空间坐标数组
            h: 水深数组
            Q: 流量数组
            h_theory: 理论水深值
            Q_theory: 理论流量值
            title: 图表标题
            save_path: 保存路径
            h_margin: 水深Y轴边界
            Q_margin: 流量Y轴边界
        """
        fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(12, 8))

        # 水深分布
        ax1.plot(x, h, 'b-', linewidth=2, label='数值解')
        ax1.axhline(h_theory, color='r', linestyle='--', linewidth=2,
                   label=f'理论值 ({h_theory:.6f} m)')
        ax1.set_xlabel('距离 x (m)')
        ax1.set_ylabel('水深 h (m)')
        ax1.set_title(f'{title} - 水深分布')
        ax1.grid(True, alpha=0.3)
        ax1.legend()
        ax1.set_ylim([h_theory - h_margin, h_theory + h_margin])

        # 流量分布
        ax2.plot(x, Q, 'g-', linewidth=2, label='数值解')
        ax2.axhline(Q_theory, color='r', linestyle='--', linewidth=2,
                   label=f'理论值 ({Q_theory:.6f} m³/s)')
        ax2.set_xlabel('距离 x (m)')
        ax2.set_ylabel('流量 Q (m³/s)')
        ax2.set_title(f'{title} - 流量分布')
        ax2.grid(True, alpha=0.3)
        ax2.legend()
        ax2.set_ylim([Q_theory - Q_margin, Q_theory + Q_margin])

        plt.tight_layout()

        if save_path:
            plt.savefig(save_path, dpi=150, bbox_inches='tight')
            print(f"图表已保存: {save_path}")

        plt.close()

    def plot_time_series(self, time: np.ndarray, data_dict: Dict[str, np.ndarray],
                        title: str = "时间序列",
                        save_path: Optional[str] = None):
        """
        绘制时间序列图

        Args:
            time: 时间数组
            data_dict: 数据字典，包含各变量的时间序列
            title: 图表标题
            save_path: 保存路径
        """
        fig, axes = plt.subplots(len(data_dict), 1,
                                figsize=(12, 4*len(data_dict)))

        if len(data_dict) == 1:
            axes = [axes]

        for ax, (var_name, data) in zip(axes, data_dict.items()):
            ax.plot(time, data, linewidth=2)
            ax.set_xlabel('时间 t (s)')
            ax.set_ylabel(var_name)
            ax.set_title(f'{title} - {var_name}')
            ax.grid(True, alpha=0.3)

        plt.tight_layout()

        if save_path:
            plt.savefig(save_path, dpi=150, bbox_inches='tight')
            print(f"图表已保存: {save_path}")

        plt.close()

    def plot_methods_comparison(self, x: np.ndarray, results: Dict[str, Dict],
                               h_theory: float, Q_theory: float,
                               title: str = "方法对比",
                               save_path: Optional[str] = None,
                               h_margin_pct: float = 0.05,
                               Q_margin_pct: float = 0.1):
        """
        绘制多个方法的对比图

        Args:
            x: 空间坐标数组
            results: 结果字典 {'method_name': {'h': array, 'Q': array}, ...}
            h_theory: 理论水深值
            Q_theory: 理论流量值
            title: 图表标题
            save_path: 保存路径
            h_margin_pct: 水深Y轴边距百分比（默认5%）
            Q_margin_pct: 流量Y轴边距百分比（默认10%）
        """
        fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(14, 10))

        # 水深对比
        for method_name, data in results.items():
            color = self.colors.get(method_name.upper(), None)
            linestyle = self.linestyles.get(method_name.upper(), '-')
            ax1.plot(x, data['h'], linestyle=linestyle, linewidth=2,
                    color=color, label=method_name)

        ax1.axhline(h_theory, color=self.colors['theory'], linestyle=':',
                   linewidth=2, label=f'Theory ({h_theory:.6f} m)')
        ax1.set_xlabel('Distance x (m)')
        ax1.set_ylabel('Depth h (m)')
        ax1.set_title(f'{title} - Water Depth')
        ax1.grid(True, alpha=0.3)
        ax1.legend()

        # 设置合理的Y轴范围（避免科学计数法混淆）
        h_margin = h_theory * h_margin_pct
        ax1.set_ylim([h_theory - h_margin, h_theory + h_margin])

        # 流量对比
        for method_name, data in results.items():
            color = self.colors.get(method_name.upper(), None)
            linestyle = self.linestyles.get(method_name.upper(), '-')
            ax2.plot(x, data['Q'], linestyle=linestyle, linewidth=2,
                    color=color, label=method_name)

        ax2.axhline(Q_theory, color=self.colors['theory'], linestyle=':',
                   linewidth=2, label=f'Theory ({Q_theory:.6f} m³/s)')
        ax2.set_xlabel('Distance x (m)')
        ax2.set_ylabel('Flow Rate Q (m³/s)')
        ax2.set_title(f'{title} - Flow Rate')
        ax2.grid(True, alpha=0.3)
        ax2.legend()

        # 设置合理的Y轴范围（避免科学计数法混淆）
        Q_margin = Q_theory * Q_margin_pct
        ax2.set_ylim([Q_theory - Q_margin, Q_theory + Q_margin])

        plt.tight_layout()

        if save_path:
            plt.savefig(save_path, dpi=150, bbox_inches='tight')
            print(f"图表已保存: {save_path}")

        plt.close()

    def plot_convergence(self, time: np.ndarray, cv_history: np.ndarray,
                        title: str = "收敛性分析",
                        save_path: Optional[str] = None):
        """
        绘制收敛性图表

        Args:
            time: 时间数组
            cv_history: 变异系数历史
            title: 图表标题
            save_path: 保存路径
        """
        fig, ax = plt.subplots(figsize=(10, 6))

        ax.semilogy(time, cv_history, 'b-', linewidth=2)
        ax.axhline(0.01, color='r', linestyle='--', linewidth=2,
                  label='Convergence Threshold (CV < 0.01%)')
        ax.set_xlabel('Time t (s)')
        ax.set_ylabel('Coefficient of Variation CV (%)')
        ax.set_title(title)
        ax.grid(True, alpha=0.3, which='both')
        ax.legend()

        plt.tight_layout()

        if save_path:
            plt.savefig(save_path, dpi=150, bbox_inches='tight')
            print(f"图表已保存: {save_path}")

        plt.close()

    def create_animation(self, x: np.ndarray, h_history: List[np.ndarray],
                        Q_history: List[np.ndarray], time: np.ndarray,
                        h_theory: float, Q_theory: float,
                        save_path: str, fps: int = 10,
                        title: str = "Canal Flow Animation"):
        """
        创建动画

        Args:
            x: 空间坐标数组
            h_history: 水深历史记录
            Q_history: 流量历史记录
            time: 时间数组
            h_theory: 理论水深值
            Q_theory: 理论流量值
            save_path: 保存路径（.gif）
            fps: 帧率
            title: 动画标题
        """
        fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(12, 8))

        def animate(frame):
            ax1.clear()
            ax2.clear()

            # 水深
            ax1.plot(x, h_history[frame], 'b-', linewidth=2, label='h(x,t)')
            ax1.axhline(h_theory, color='r', linestyle='--', linewidth=2,
                       label=f'Theory: {h_theory:.6f} m')
            ax1.set_xlabel('Distance x (m)')
            ax1.set_ylabel('Depth h (m)')
            ax1.set_title(f'{title} - Depth (t = {time[frame]:.1f} s)')
            ax1.grid(True, alpha=0.3)
            ax1.legend()
            ax1.set_ylim([h_theory - 0.01, h_theory + 0.01])

            # 流量
            ax2.plot(x, Q_history[frame], 'g-', linewidth=2, label='Q(x,t)')
            ax2.axhline(Q_theory, color='r', linestyle='--', linewidth=2,
                       label=f'Theory: {Q_theory:.6f} m³/s')
            ax2.set_xlabel('Distance x (m)')
            ax2.set_ylabel('Flow Rate Q (m³/s)')
            ax2.set_title(f'{title} - Flow Rate (t = {time[frame]:.1f} s)')
            ax2.grid(True, alpha=0.3)
            ax2.legend()
            ax2.set_ylim([Q_theory - 0.05, Q_theory + 0.05])

            plt.tight_layout()

        # 抽帧以减小文件大小
        n_frames = len(time)
        frame_skip = max(1, n_frames // 100)  # 最多100帧
        frames = list(range(0, n_frames, frame_skip))

        anim = FuncAnimation(fig, animate, frames=frames,
                           interval=1000/fps, repeat=True)

        writer = PillowWriter(fps=fps)
        anim.save(save_path, writer=writer)
        print(f"动画已保存: {save_path}")

        plt.close()


if __name__ == '__main__':
    # 测试可视化器
    print("=== 明渠可视化器测试 ===\n")

    viz = CanalVisualizer(use_chinese=True)

    # 生成测试数据
    x = np.linspace(0, 1000, 201)
    h = np.ones_like(x) * 0.806 + np.random.normal(0, 0.0001, len(x))
    Q = np.ones_like(x) * 8.0 + np.random.normal(0, 0.001, len(x))

    # 测试空间分布图
    print("测试空间分布图...")
    viz.plot_spatial_distribution(
        x, h, Q,
        h_theory=0.806,
        Q_theory=8.0,
        title="测试",
        save_path="/tmp/test_spatial.png"
    )

    print("\n 可视化器测试完成")
