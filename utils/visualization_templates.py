#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
可视化模板库 - Visualization Templates

提供各种水力学分析的标准化可视化模板：
- 静态图表（PNG）：纵剖面、流量分布、时间序列等
- 动画图表（GIF）：水面线动画、流量传播等
- 专业图表：降雨径流、水位流量关系、收敛曲线等

Author: Claude
Date: 2025-10-23
"""

import numpy as np
import matplotlib.pyplot as plt
import matplotlib.animation as animation
from typing import Optional, Dict, List, Tuple, Callable
import os


class VisualizationTemplates:
    """可视化模板类 - 提供各种标准化图表模板"""

    # 默认配置
    DEFAULT_DPI = 150
    DEFAULT_FIGSIZE_SINGLE = (14, 8)
    DEFAULT_FIGSIZE_MULTI = (16, 10)
    DEFAULT_FONT_SIZE = 12
    DEFAULT_TITLE_SIZE = 14
    DEFAULT_LINE_WIDTH = 2.5

    # 颜色方案
    COLOR_WATER = 'cyan'
    COLOR_BED = 'saddlebrown'
    COLOR_SURFACE = 'blue'
    COLOR_FLOW = 'green'
    COLOR_TARGET = 'black'
    COLOR_GATE = 'red'
    COLOR_ERROR = 'orange'

    def __init__(self, output_dir: str = None, dpi: int = None):
        """
        初始化可视化模板

        Args:
            output_dir: 输出目录
            dpi: 图像分辨率
        """
        self.output_dir = output_dir or '.'
        self.dpi = dpi or self.DEFAULT_DPI
        os.makedirs(self.output_dir, exist_ok=True)

    # ==================== 静态图表模板 ====================

    def plot_longitudinal_profile(
        self,
        x: np.ndarray,
        h: np.ndarray,
        S0: float,
        canal_length: float,
        gate_positions: Optional[List[float]] = None,
        h_uniform: Optional[float] = None,
        title: str = "Longitudinal Water Surface Profile",
        filename: Optional[str] = None
    ) -> plt.Figure:
        """
        绘制纵剖面水面线图

        Args:
            x: 位置坐标
            h: 水深数组
            S0: 渠底坡度
            canal_length: 渠道长度
            gate_positions: 闸门位置列表
            h_uniform: 均匀流水深（参考线）
            title: 图表标题
            filename: 保存文件名

        Returns:
            图表对象
        """
        fig, (ax1, ax2) = plt.subplots(2, 1, figsize=self.DEFAULT_FIGSIZE_MULTI)

        # 计算高程
        z_bed = (canal_length - x) * S0
        z_surface = z_bed + h

        # 子图1: 水面+渠底纵剖面
        ax1.fill_between(x, z_bed, z_surface, color=self.COLOR_WATER, alpha=0.5,
                        label='Water')
        ax1.plot(x, z_surface, color=self.COLOR_SURFACE, linewidth=self.DEFAULT_LINE_WIDTH,
                label='Water Surface')
        ax1.plot(x, z_bed, color=self.COLOR_BED, linewidth=2, label='Bed Level')

        if gate_positions:
            for i, pos in enumerate(gate_positions):
                ax1.axvline(x=pos, color=self.COLOR_GATE, linestyle='--',
                          linewidth=2, alpha=0.7, label='Gate' if i == 0 else '')

        ax1.set_xlabel('Distance (m)', fontsize=self.DEFAULT_FONT_SIZE)
        ax1.set_ylabel('Elevation (m)', fontsize=self.DEFAULT_FONT_SIZE)
        ax1.set_title(title, fontsize=self.DEFAULT_TITLE_SIZE, fontweight='bold')
        ax1.grid(True, alpha=0.3)
        ax1.legend(fontsize=11)
        ax1.set_xlim([0, canal_length])

        # 子图2: 水深分布
        ax2.plot(x, h, color=self.COLOR_SURFACE, linewidth=self.DEFAULT_LINE_WIDTH,
                label='Water Depth')

        if h_uniform is not None:
            ax2.axhline(y=h_uniform, color=self.COLOR_TARGET, linestyle=':',
                      alpha=0.5, label=f'Uniform Depth ({h_uniform:.3f}m)')

        if gate_positions:
            for i, pos in enumerate(gate_positions):
                ax2.axvline(x=pos, color=self.COLOR_GATE, linestyle='--',
                          linewidth=2, alpha=0.7)

        ax2.set_xlabel('Distance (m)', fontsize=self.DEFAULT_FONT_SIZE)
        ax2.set_ylabel('Water Depth (m)', fontsize=self.DEFAULT_FONT_SIZE)
        ax2.set_title('Water Depth Distribution', fontsize=self.DEFAULT_TITLE_SIZE,
                     fontweight='bold')
        ax2.grid(True, alpha=0.3)
        ax2.legend(fontsize=11)
        ax2.set_xlim([0, canal_length])

        plt.tight_layout()

        if filename:
            filepath = os.path.join(self.output_dir, filename)
            fig.savefig(filepath, dpi=self.dpi, bbox_inches='tight')
            print(f"  ✓ Saved: {filepath}")

        return fig

    def plot_flow_distribution(
        self,
        x: np.ndarray,
        Q: np.ndarray,
        Q_target: float,
        gate_positions: Optional[List[float]] = None,
        show_error: bool = True,
        title: str = "Flow Distribution",
        filename: Optional[str] = None
    ) -> plt.Figure:
        """
        绘制流量分布图（带误差分析）

        Args:
            x: 位置坐标
            Q: 流量数组
            Q_target: 目标流量
            gate_positions: 闸门位置列表
            show_error: 是否显示误差图
            title: 图表标题
            filename: 保存文件名

        Returns:
            图表对象
        """
        if show_error:
            fig, (ax1, ax2) = plt.subplots(2, 1, figsize=self.DEFAULT_FIGSIZE_MULTI)
        else:
            fig, ax1 = plt.subplots(1, 1, figsize=self.DEFAULT_FIGSIZE_SINGLE)

        # 子图1: 流量分布
        ax1.plot(x, Q, color=self.COLOR_FLOW, linewidth=self.DEFAULT_LINE_WIDTH,
                label='Flow Rate')
        ax1.axhline(y=Q_target, color=self.COLOR_TARGET, linestyle='--',
                  linewidth=1.5, label=f'Target: {Q_target:.4f} m³/s', alpha=0.7)

        if gate_positions:
            for i, pos in enumerate(gate_positions):
                ax1.axvline(x=pos, color=self.COLOR_GATE, linestyle=':',
                          alpha=0.5, label='Gate' if i == 0 else '')

        ax1.set_xlabel('Distance (m)', fontsize=self.DEFAULT_FONT_SIZE)
        ax1.set_ylabel('Flow Rate (m³/s)', fontsize=self.DEFAULT_FONT_SIZE)
        ax1.set_title(title, fontsize=self.DEFAULT_TITLE_SIZE, fontweight='bold')
        ax1.legend(fontsize=11)
        ax1.grid(True, alpha=0.3)

        # 子图2: 相对误差（如果需要）
        if show_error:
            Q_error = np.abs(Q - Q_target) / Q_target * 100
            ax2.plot(x, Q_error, color=self.COLOR_ERROR, linewidth=2,
                    label='Relative Error')

            # 标准线
            ax2.axhline(y=0.01, color='green', linestyle='--', linewidth=1,
                      label='Excellent: 0.01%', alpha=0.7)
            ax2.axhline(y=0.1, color='blue', linestyle='--', linewidth=1,
                      label='Good: 0.1%', alpha=0.7)
            ax2.axhline(y=1.0, color='orange', linestyle='--', linewidth=1,
                      label='Acceptable: 1.0%', alpha=0.7)

            if gate_positions:
                for pos in gate_positions:
                    ax2.axvline(x=pos, color=self.COLOR_GATE, linestyle=':', alpha=0.5)

            ax2.set_xlabel('Distance (m)', fontsize=self.DEFAULT_FONT_SIZE)
            ax2.set_ylabel('Relative Error (%)', fontsize=self.DEFAULT_FONT_SIZE)
            ax2.set_title('Flow Conservation Error', fontsize=self.DEFAULT_TITLE_SIZE,
                         fontweight='bold')
            ax2.legend(fontsize=10)
            ax2.grid(True, alpha=0.3)
            ax2.set_yscale('log')

        plt.tight_layout()

        if filename:
            filepath = os.path.join(self.output_dir, filename)
            fig.savefig(filepath, dpi=self.dpi, bbox_inches='tight')
            print(f"  ✓ Saved: {filepath}")

        return fig

    def plot_time_series(
        self,
        time: np.ndarray,
        variables: Dict[str, np.ndarray],
        xlabel: str = "Time (s)",
        ylabel: str = "Value",
        title: str = "Time Series",
        step_time: Optional[float] = None,
        filename: Optional[str] = None
    ) -> plt.Figure:
        """
        绘制时间序列图

        Args:
            time: 时间数组
            variables: 变量字典 {名称: 数据数组}
            xlabel: X轴标签
            ylabel: Y轴标签
            title: 图表标题
            step_time: 阶跃时刻（如果有）
            filename: 保存文件名

        Returns:
            图表对象
        """
        fig, ax = plt.subplots(figsize=self.DEFAULT_FIGSIZE_SINGLE)

        colors = plt.cm.tab10(np.linspace(0, 1, len(variables)))

        for (name, data), color in zip(variables.items(), colors):
            ax.plot(time, data, linewidth=self.DEFAULT_LINE_WIDTH, label=name, color=color)

        if step_time is not None:
            ax.axvline(x=step_time, color='black', linestyle='--', linewidth=1.5,
                      alpha=0.5, label='Step Time')

        ax.set_xlabel(xlabel, fontsize=self.DEFAULT_FONT_SIZE)
        ax.set_ylabel(ylabel, fontsize=self.DEFAULT_FONT_SIZE)
        ax.set_title(title, fontsize=self.DEFAULT_TITLE_SIZE, fontweight='bold')
        ax.grid(True, alpha=0.3)
        ax.legend(fontsize=11)

        plt.tight_layout()

        if filename:
            filepath = os.path.join(self.output_dir, filename)
            fig.savefig(filepath, dpi=self.dpi, bbox_inches='tight')
            print(f"  ✓ Saved: {filepath}")

        return fig

    def plot_rating_curve(
        self,
        h: np.ndarray,
        Q: np.ndarray,
        h_label: str = "Water Depth (m)",
        Q_label: str = "Discharge (m³/s)",
        title: str = "Rating Curve (h-Q Relationship)",
        fitted_curve: Optional[Tuple[np.ndarray, np.ndarray]] = None,
        filename: Optional[str] = None
    ) -> plt.Figure:
        """
        绘制水位流量关系曲线（率定曲线）

        Args:
            h: 水深数组
            Q: 流量数组
            h_label: 水深标签
            Q_label: 流量标签
            title: 图表标题
            fitted_curve: 拟合曲线 (h_fit, Q_fit)
            filename: 保存文件名

        Returns:
            图表对象
        """
        fig, ax = plt.subplots(figsize=self.DEFAULT_FIGSIZE_SINGLE)

        ax.scatter(h, Q, color='blue', s=50, alpha=0.6, label='Observed Data')

        if fitted_curve is not None:
            h_fit, Q_fit = fitted_curve
            ax.plot(h_fit, Q_fit, color='red', linewidth=2.5, label='Fitted Curve')

        ax.set_xlabel(h_label, fontsize=self.DEFAULT_FONT_SIZE)
        ax.set_ylabel(Q_label, fontsize=self.DEFAULT_FONT_SIZE)
        ax.set_title(title, fontsize=self.DEFAULT_TITLE_SIZE, fontweight='bold')
        ax.grid(True, alpha=0.3)
        ax.legend(fontsize=11)

        plt.tight_layout()

        if filename:
            filepath = os.path.join(self.output_dir, filename)
            fig.savefig(filepath, dpi=self.dpi, bbox_inches='tight')
            print(f"  ✓ Saved: {filepath}")

        return fig

    def plot_convergence_history(
        self,
        iterations: np.ndarray,
        errors: np.ndarray,
        tolerance: float,
        ylabel: str = "Error",
        title: str = "Convergence History",
        log_scale: bool = True,
        filename: Optional[str] = None
    ) -> plt.Figure:
        """
        绘制收敛历史曲线

        Args:
            iterations: 迭代次数数组
            errors: 误差数组
            tolerance: 收敛容差
            ylabel: Y轴标签
            title: 图表标题
            log_scale: 是否使用对数坐标
            filename: 保存文件名

        Returns:
            图表对象
        """
        fig, ax = plt.subplots(figsize=self.DEFAULT_FIGSIZE_SINGLE)

        ax.plot(iterations, errors, color='blue', linewidth=self.DEFAULT_LINE_WIDTH,
               marker='o', markersize=4, label='Error')
        ax.axhline(y=tolerance, color='red', linestyle='--', linewidth=1.5,
                  label=f'Tolerance: {tolerance}')

        ax.set_xlabel('Iteration', fontsize=self.DEFAULT_FONT_SIZE)
        ax.set_ylabel(ylabel, fontsize=self.DEFAULT_FONT_SIZE)
        ax.set_title(title, fontsize=self.DEFAULT_TITLE_SIZE, fontweight='bold')
        ax.grid(True, alpha=0.3)
        ax.legend(fontsize=11)

        if log_scale:
            ax.set_yscale('log')

        plt.tight_layout()

        if filename:
            filepath = os.path.join(self.output_dir, filename)
            fig.savefig(filepath, dpi=self.dpi, bbox_inches='tight')
            print(f"  ✓ Saved: {filepath}")

        return fig

    # ==================== 动画图表模板 ====================

    def create_longitudinal_animation(
        self,
        x: np.ndarray,
        h_snapshots: List[np.ndarray],
        Q_snapshots: List[np.ndarray],
        time_snapshots: List[float],
        S0: float,
        canal_length: float,
        Q_target: float,
        gate_positions: Optional[List[float]] = None,
        h_uniform: Optional[float] = None,
        title_prefix: str = "Longitudinal Profile",
        filename: Optional[str] = None,
        fps: int = 10,
        dpi: int = 80
    ) -> Tuple[plt.Figure, animation.FuncAnimation]:
        """
        创建纵剖面动画（水深+流量）

        Args:
            x: 位置坐标
            h_snapshots: 水深快照列表
            Q_snapshots: 流量快照列表
            time_snapshots: 时间快照列表
            S0: 渠底坡度
            canal_length: 渠道长度
            Q_target: 目标流量
            gate_positions: 闸门位置列表
            h_uniform: 均匀流水深
            title_prefix: 标题前缀
            filename: 保存文件名
            fps: 帧率
            dpi: 分辨率

        Returns:
            (图表对象, 动画对象)
        """
        # 计算渠底高程
        z_bed = (canal_length - x) * S0

        # 预计算范围
        all_z_surfaces = [z_bed + h for h in h_snapshots]
        z_min = np.min([np.min(z) for z in all_z_surfaces]) - 0.3
        z_max = np.max([np.max(z) for z in all_z_surfaces]) + 0.5

        h_min = np.min([np.min(h) for h in h_snapshots])
        h_max = np.max([np.max(h) for h in h_snapshots])

        Q_min = np.min([np.min(Q) for Q in Q_snapshots])
        Q_max = np.max([np.max(Q) for Q in Q_snapshots])

        fig = plt.figure(figsize=self.DEFAULT_FIGSIZE_MULTI)

        def animate(frame_idx):
            plt.clf()

            h_frame = h_snapshots[frame_idx]
            Q_frame = Q_snapshots[frame_idx]
            t_frame = time_snapshots[frame_idx]

            z_surface = z_bed + h_frame

            # 子图1: 纵剖面
            ax1 = plt.subplot(3, 1, 1)
            ax1.fill_between(x, z_bed, z_surface, color=self.COLOR_WATER, alpha=0.5)
            ax1.plot(x, z_surface, color=self.COLOR_SURFACE, linewidth=2.5,
                    label='Water Surface')
            ax1.plot(x, z_bed, color=self.COLOR_BED, linewidth=2, label='Bed Level')

            if gate_positions:
                for pos in gate_positions:
                    ax1.axvline(x=pos, color=self.COLOR_GATE, linestyle='--',
                              linewidth=2, alpha=0.7)

            ax1.set_xlabel('Distance (m)', fontsize=11)
            ax1.set_ylabel('Elevation (m)', fontsize=11)
            ax1.set_title(f'{title_prefix} - t = {t_frame:.0f}s', fontsize=13,
                         fontweight='bold')
            ax1.grid(True, alpha=0.3)
            ax1.legend(fontsize=10, loc='upper right')
            ax1.set_xlim([0, canal_length])
            ax1.set_ylim([z_min, z_max])

            # 子图2: 水深
            ax2 = plt.subplot(3, 1, 2)
            ax2.plot(x, h_frame, color=self.COLOR_SURFACE, linewidth=2.5)

            if h_uniform is not None:
                ax2.axhline(y=h_uniform, color='black', linestyle=':', alpha=0.5)

            if gate_positions:
                for pos in gate_positions:
                    ax2.axvline(x=pos, color=self.COLOR_GATE, linestyle='--',
                              linewidth=2, alpha=0.7)

            ax2.set_xlabel('Distance (m)', fontsize=11)
            ax2.set_ylabel('Water Depth (m)', fontsize=11)
            ax2.set_title('Water Depth Distribution', fontsize=12, fontweight='bold')
            ax2.grid(True, alpha=0.3)
            ax2.set_xlim([0, canal_length])
            ax2.set_ylim([h_min - 0.1, h_max + 0.1])

            # 子图3: 流量
            ax3 = plt.subplot(3, 1, 3)
            ax3.plot(x, Q_frame, color=self.COLOR_FLOW, linewidth=2.5)
            ax3.axhline(y=Q_target, color='black', linestyle=':', alpha=0.5)

            if gate_positions:
                for pos in gate_positions:
                    ax3.axvline(x=pos, color=self.COLOR_GATE, linestyle='--',
                              linewidth=2, alpha=0.7)

            ax3.set_xlabel('Distance (m)', fontsize=11)
            ax3.set_ylabel('Flow Rate (m³/s)', fontsize=11)
            ax3.set_title('Flow Rate Distribution', fontsize=12, fontweight='bold')
            ax3.grid(True, alpha=0.3)
            ax3.set_xlim([0, canal_length])
            ax3.set_ylim([Q_min - 1, Q_max + 1])

            plt.tight_layout()

        anim = animation.FuncAnimation(fig, animate, frames=len(time_snapshots),
                                      interval=1000//fps, blit=False, repeat=True)

        if filename:
            filepath = os.path.join(self.output_dir, filename)
            anim.save(filepath, writer='pillow', fps=fps, dpi=dpi)
            filesize_mb = os.path.getsize(filepath) / (1024 * 1024)
            print(f"  ✓ Saved animation: {filepath} ({filesize_mb:.2f} MB)")

        return fig, anim

    # ==================== 流场可视化 ====================

    def plot_velocity_field(
        self,
        X: np.ndarray,
        Y: np.ndarray,
        U: np.ndarray,
        V: np.ndarray,
        speed: Optional[np.ndarray] = None,
        title: str = "Velocity Field",
        streamlines: bool = True,
        quiver: bool = False,
        filename: Optional[str] = None
    ) -> plt.Figure:
        """
        绘制流场速度图（流线图/矢量图）

        Args:
            X: X坐标网格
            Y: Y坐标网格
            U: X方向速度分量
            V: Y方向速度分量
            speed: 速度大小（用于着色）
            title: 图表标题
            streamlines: 是否绘制流线
            quiver: 是否绘制矢量箭头
            filename: 保存文件名

        Returns:
            图表对象
        """
        fig, ax = plt.subplots(figsize=self.DEFAULT_FIGSIZE_SINGLE)

        # 计算速度大小
        if speed is None:
            speed = np.sqrt(U**2 + V**2)

        # 绘制速度等高线作为背景
        contour = ax.contourf(X, Y, speed, levels=20, cmap='viridis', alpha=0.6)
        plt.colorbar(contour, ax=ax, label='Velocity Magnitude (m/s)')

        # 绘制流线
        if streamlines:
            strm = ax.streamplot(X, Y, U, V, color='white', linewidth=1.5,
                               density=1.5, arrowsize=1.2, arrowstyle='->')

        # 绘制矢量箭头
        if quiver:
            # 降采样以避免过于密集
            skip = max(1, len(X[0]) // 20)
            ax.quiver(X[::skip, ::skip], Y[::skip, ::skip],
                     U[::skip, ::skip], V[::skip, ::skip],
                     alpha=0.7, scale=20)

        ax.set_xlabel('Distance (m)', fontsize=self.DEFAULT_FONT_SIZE)
        ax.set_ylabel('Depth (m)', fontsize=self.DEFAULT_FONT_SIZE)
        ax.set_title(title, fontsize=self.DEFAULT_TITLE_SIZE, fontweight='bold')
        ax.set_aspect('equal')

        plt.tight_layout()

        if filename:
            filepath = os.path.join(self.output_dir, filename)
            fig.savefig(filepath, dpi=self.dpi, bbox_inches='tight')
            print(f"  ✓ Saved: {filepath}")

        return fig

    def plot_contour_map(
        self,
        X: np.ndarray,
        Y: np.ndarray,
        Z: np.ndarray,
        xlabel: str = "X",
        ylabel: str = "Y",
        zlabel: str = "Z",
        title: str = "Contour Map",
        levels: int = 20,
        filled: bool = True,
        show_labels: bool = True,
        filename: Optional[str] = None
    ) -> plt.Figure:
        """
        绘制等高线图

        Args:
            X: X坐标网格
            Y: Y坐标网格
            Z: 数值网格
            xlabel: X轴标签
            ylabel: Y轴标签
            zlabel: 数值标签
            title: 图表标题
            levels: 等高线级数
            filled: 是否填充
            show_labels: 是否显示等高线标签
            filename: 保存文件名

        Returns:
            图表对象
        """
        fig, ax = plt.subplots(figsize=self.DEFAULT_FIGSIZE_SINGLE)

        if filled:
            contour = ax.contourf(X, Y, Z, levels=levels, cmap='coolwarm')
        else:
            contour = ax.contour(X, Y, Z, levels=levels, colors='black')

        if show_labels and not filled:
            ax.clabel(contour, inline=True, fontsize=8)

        plt.colorbar(contour, ax=ax, label=zlabel)

        ax.set_xlabel(xlabel, fontsize=self.DEFAULT_FONT_SIZE)
        ax.set_ylabel(ylabel, fontsize=self.DEFAULT_FONT_SIZE)
        ax.set_title(title, fontsize=self.DEFAULT_TITLE_SIZE, fontweight='bold')
        ax.grid(True, alpha=0.3)

        plt.tight_layout()

        if filename:
            filepath = os.path.join(self.output_dir, filename)
            fig.savefig(filepath, dpi=self.dpi, bbox_inches='tight')
            print(f"  ✓ Saved: {filepath}")

        return fig

    def plot_heatmap(
        self,
        data: np.ndarray,
        xticklabels: Optional[List[str]] = None,
        yticklabels: Optional[List[str]] = None,
        xlabel: str = "X",
        ylabel: str = "Y",
        title: str = "Heatmap",
        cmap: str = 'viridis',
        annot: bool = False,
        fmt: str = '.2f',
        filename: Optional[str] = None
    ) -> plt.Figure:
        """
        绘制热图

        Args:
            data: 数据矩阵
            xticklabels: X轴标签列表
            yticklabels: Y轴标签列表
            xlabel: X轴标签
            ylabel: Y轴标签
            title: 图表标题
            cmap: 颜色映射
            annot: 是否显示数值
            fmt: 数值格式
            filename: 保存文件名

        Returns:
            图表对象
        """
        fig, ax = plt.subplots(figsize=self.DEFAULT_FIGSIZE_SINGLE)

        im = ax.imshow(data, cmap=cmap, aspect='auto')
        plt.colorbar(im, ax=ax)

        # 设置刻度标签
        if xticklabels is not None:
            ax.set_xticks(np.arange(len(xticklabels)))
            ax.set_xticklabels(xticklabels, rotation=45, ha='right')

        if yticklabels is not None:
            ax.set_yticks(np.arange(len(yticklabels)))
            ax.set_yticklabels(yticklabels)

        # 添加数值标注
        if annot:
            for i in range(data.shape[0]):
                for j in range(data.shape[1]):
                    text = ax.text(j, i, format(data[i, j], fmt),
                                 ha="center", va="center", color="w", fontsize=8)

        ax.set_xlabel(xlabel, fontsize=self.DEFAULT_FONT_SIZE)
        ax.set_ylabel(ylabel, fontsize=self.DEFAULT_FONT_SIZE)
        ax.set_title(title, fontsize=self.DEFAULT_TITLE_SIZE, fontweight='bold')

        plt.tight_layout()

        if filename:
            filepath = os.path.join(self.output_dir, filename)
            fig.savefig(filepath, dpi=self.dpi, bbox_inches='tight')
            print(f"  ✓ Saved: {filepath}")

        return fig

    # ==================== 3D可视化 ====================

    def plot_3d_surface(
        self,
        X: np.ndarray,
        Y: np.ndarray,
        Z: np.ndarray,
        xlabel: str = "X",
        ylabel: str = "Y",
        zlabel: str = "Z",
        title: str = "3D Surface",
        cmap: str = 'viridis',
        view_angle: Tuple[int, int] = (30, 45),
        filename: Optional[str] = None
    ) -> plt.Figure:
        """
        绘制3D表面图

        Args:
            X: X坐标网格
            Y: Y坐标网格
            Z: 数值网格
            xlabel: X轴标签
            ylabel: Y轴标签
            zlabel: Z轴标签
            title: 图表标题
            cmap: 颜色映射
            view_angle: 视角 (elevation, azimuth)
            filename: 保存文件名

        Returns:
            图表对象
        """
        from mpl_toolkits.mplot3d import Axes3D

        fig = plt.figure(figsize=self.DEFAULT_FIGSIZE_SINGLE)
        ax = fig.add_subplot(111, projection='3d')

        surf = ax.plot_surface(X, Y, Z, cmap=cmap, alpha=0.8,
                              linewidth=0, antialiased=True)

        fig.colorbar(surf, ax=ax, shrink=0.5, aspect=5)

        ax.set_xlabel(xlabel, fontsize=self.DEFAULT_FONT_SIZE)
        ax.set_ylabel(ylabel, fontsize=self.DEFAULT_FONT_SIZE)
        ax.set_zlabel(zlabel, fontsize=self.DEFAULT_FONT_SIZE)
        ax.set_title(title, fontsize=self.DEFAULT_TITLE_SIZE, fontweight='bold')

        # 设置视角
        ax.view_init(elev=view_angle[0], azim=view_angle[1])

        plt.tight_layout()

        if filename:
            filepath = os.path.join(self.output_dir, filename)
            fig.savefig(filepath, dpi=self.dpi, bbox_inches='tight')
            print(f"  ✓ Saved: {filepath}")

        return fig

    def plot_3d_water_surface(
        self,
        x: np.ndarray,
        time: np.ndarray,
        h: np.ndarray,
        S0: float,
        canal_length: float,
        title: str = "3D Water Surface Evolution",
        filename: Optional[str] = None
    ) -> plt.Figure:
        """
        绘制3D水面演化图（空间-时间-水深）

        Args:
            x: 位置坐标数组
            time: 时间数组
            h: 水深数组 (time x space)
            S0: 渠底坡度
            canal_length: 渠道长度
            title: 图表标题
            filename: 保存文件名

        Returns:
            图表对象
        """
        from mpl_toolkits.mplot3d import Axes3D

        X, T = np.meshgrid(x, time)
        H = h  # shape: (len(time), len(x))

        fig = plt.figure(figsize=(14, 10))
        ax = fig.add_subplot(111, projection='3d')

        surf = ax.plot_surface(X, T, H, cmap='ocean', alpha=0.8,
                              linewidth=0.5, antialiased=True,
                              edgecolor='gray', linewidths=0.2)

        fig.colorbar(surf, ax=ax, shrink=0.5, aspect=5, label='Water Depth (m)')

        ax.set_xlabel('Distance (m)', fontsize=self.DEFAULT_FONT_SIZE)
        ax.set_ylabel('Time (s)', fontsize=self.DEFAULT_FONT_SIZE)
        ax.set_zlabel('Water Depth (m)', fontsize=self.DEFAULT_FONT_SIZE)
        ax.set_title(title, fontsize=self.DEFAULT_TITLE_SIZE, fontweight='bold')

        ax.view_init(elev=25, azim=225)

        plt.tight_layout()

        if filename:
            filepath = os.path.join(self.output_dir, filename)
            fig.savefig(filepath, dpi=self.dpi, bbox_inches='tight')
            print(f"  ✓ Saved: {filepath}")

        return fig

    # ==================== 专业领域图表 ====================

    def plot_backwater_curve(
        self,
        x: np.ndarray,
        h: np.ndarray,
        h_normal: float,
        h_critical: float,
        S0: float,
        canal_length: float,
        gate_position: Optional[float] = None,
        title: str = "Backwater Curve (Gradually Varied Flow)",
        filename: Optional[str] = None
    ) -> plt.Figure:
        """
        绘制回水曲线图（渐变流水面线）

        Args:
            x: 位置坐标
            h: 水深数组
            h_normal: 正常水深
            h_critical: 临界水深
            S0: 渠底坡度
            canal_length: 渠道长度
            gate_position: 闸门位置
            title: 图表标题
            filename: 保存文件名

        Returns:
            图表对象
        """
        fig, ax = plt.subplots(figsize=self.DEFAULT_FIGSIZE_SINGLE)

        # 计算高程
        z_bed = (canal_length - x) * S0
        z_surface = z_bed + h

        # 绘制水面线
        ax.plot(x, z_surface, color='blue', linewidth=3, label='Water Surface')
        ax.fill_between(x, z_bed, z_surface, color='cyan', alpha=0.3)

        # 绘制渠底
        ax.plot(x, z_bed, color='saddlebrown', linewidth=2, label='Bed Level')

        # 参考线
        ax.plot(x, z_bed + h_normal, color='green', linestyle='--',
               linewidth=1.5, label=f'Normal Depth ({h_normal:.3f}m)', alpha=0.7)
        ax.plot(x, z_bed + h_critical, color='red', linestyle='--',
               linewidth=1.5, label=f'Critical Depth ({h_critical:.3f}m)', alpha=0.7)

        # 闸门标记
        if gate_position is not None:
            ax.axvline(x=gate_position, color='red', linestyle=':', linewidth=2,
                      alpha=0.7, label='Control Structure')

        # 标注流态区域
        if h[0] > h_normal:
            flow_type = "M1 Backwater Curve (Subcritical)"
        elif h[0] < h_normal and h[0] > h_critical:
            flow_type = "M2 Drawdown Curve (Subcritical)"
        else:
            flow_type = "Varied Flow Profile"

        ax.text(0.05, 0.95, flow_type, transform=ax.transAxes,
               fontsize=11, verticalalignment='top',
               bbox=dict(boxstyle='round', facecolor='wheat', alpha=0.5))

        ax.set_xlabel('Distance (m)', fontsize=self.DEFAULT_FONT_SIZE)
        ax.set_ylabel('Elevation (m)', fontsize=self.DEFAULT_FONT_SIZE)
        ax.set_title(title, fontsize=self.DEFAULT_TITLE_SIZE, fontweight='bold')
        ax.legend(fontsize=10, loc='best')
        ax.grid(True, alpha=0.3)
        ax.set_xlim([0, canal_length])

        plt.tight_layout()

        if filename:
            filepath = os.path.join(self.output_dir, filename)
            fig.savefig(filepath, dpi=self.dpi, bbox_inches='tight')
            print(f"  ✓ Saved: {filepath}")

        return fig

    def plot_froude_number(
        self,
        x: np.ndarray,
        Fr: np.ndarray,
        gate_positions: Optional[List[float]] = None,
        title: str = "Froude Number Distribution",
        filename: Optional[str] = None
    ) -> plt.Figure:
        """
        绘制Froude数分布图（判断流态）

        Args:
            x: 位置坐标
            Fr: Froude数数组
            gate_positions: 闸门位置列表
            title: 图表标题
            filename: 保存文件名

        Returns:
            图表对象
        """
        fig, ax = plt.subplots(figsize=self.DEFAULT_FIGSIZE_SINGLE)

        # 绘制Froude数
        ax.plot(x, Fr, color='purple', linewidth=2.5, label='Froude Number')

        # 临界流线 Fr=1
        ax.axhline(y=1.0, color='red', linestyle='--', linewidth=2,
                  label='Critical Flow (Fr=1)', alpha=0.7)

        # 流态区域着色
        ax.fill_between(x, 0, np.minimum(Fr, 1), color='blue', alpha=0.2,
                       label='Subcritical (Fr<1)')
        ax.fill_between(x, 1, np.maximum(Fr, 1), color='orange', alpha=0.2,
                       label='Supercritical (Fr>1)')

        # 闸门标记
        if gate_positions:
            for pos in gate_positions:
                ax.axvline(x=pos, color='gray', linestyle=':', alpha=0.5)

        ax.set_xlabel('Distance (m)', fontsize=self.DEFAULT_FONT_SIZE)
        ax.set_ylabel('Froude Number (-)', fontsize=self.DEFAULT_FONT_SIZE)
        ax.set_title(title, fontsize=self.DEFAULT_TITLE_SIZE, fontweight='bold')
        ax.legend(fontsize=11, loc='best')
        ax.grid(True, alpha=0.3)
        ax.set_ylim([0, max(2, np.max(Fr) * 1.1)])

        plt.tight_layout()

        if filename:
            filepath = os.path.join(self.output_dir, filename)
            fig.savefig(filepath, dpi=self.dpi, bbox_inches='tight')
            print(f"  ✓ Saved: {filepath}")

        return fig

    def plot_energy_line(
        self,
        x: np.ndarray,
        h: np.ndarray,
        v: np.ndarray,
        S0: float,
        canal_length: float,
        g: float = 9.81,
        title: str = "Energy and Hydraulic Grade Lines",
        filename: Optional[str] = None
    ) -> plt.Figure:
        """
        绘制能量线和水力坡度线

        Args:
            x: 位置坐标
            h: 水深数组
            v: 流速数组
            S0: 渠底坡度
            canal_length: 渠道长度
            g: 重力加速度
            title: 图表标题
            filename: 保存文件名

        Returns:
            图表对象
        """
        fig, ax = plt.subplots(figsize=self.DEFAULT_FIGSIZE_SINGLE)

        # 计算高程
        z_bed = (canal_length - x) * S0
        z_surface = z_bed + h
        E_total = z_surface + v**2 / (2 * g)  # 总能量线

        # 绘制
        ax.fill_between(x, z_bed, z_surface, color='cyan', alpha=0.4, label='Water')
        ax.plot(x, z_bed, color='saddlebrown', linewidth=2, label='Bed Level')
        ax.plot(x, z_surface, color='blue', linewidth=2.5, label='Water Surface (HGL)')
        ax.plot(x, E_total, color='red', linewidth=2.5, linestyle='--',
               label='Total Energy Line (EGL)')

        ax.set_xlabel('Distance (m)', fontsize=self.DEFAULT_FONT_SIZE)
        ax.set_ylabel('Elevation (m)', fontsize=self.DEFAULT_FONT_SIZE)
        ax.set_title(title, fontsize=self.DEFAULT_TITLE_SIZE, fontweight='bold')
        ax.legend(fontsize=11, loc='best')
        ax.grid(True, alpha=0.3)
        ax.set_xlim([0, canal_length])

        plt.tight_layout()

        if filename:
            filepath = os.path.join(self.output_dir, filename)
            fig.savefig(filepath, dpi=self.dpi, bbox_inches='tight')
            print(f"  ✓ Saved: {filepath}")

        return fig

    def plot_rainfall_runoff(
        self,
        time: np.ndarray,
        rainfall: np.ndarray,
        runoff: np.ndarray,
        title: str = "Rainfall-Runoff Relationship",
        filename: Optional[str] = None
    ) -> plt.Figure:
        """
        绘制降雨径流关系图

        Args:
            time: 时间数组
            rainfall: 降雨强度数组
            runoff: 径流流量数组
            title: 图表标题
            filename: 保存文件名

        Returns:
            图表对象
        """
        fig, (ax1, ax2) = plt.subplots(2, 1, figsize=self.DEFAULT_FIGSIZE_MULTI,
                                       sharex=True)

        # 子图1: 降雨
        ax1.bar(time, rainfall, width=np.diff(time).mean(), color='blue', alpha=0.6,
               label='Rainfall')
        ax1.set_ylabel('Rainfall Intensity (mm/h)', fontsize=self.DEFAULT_FONT_SIZE)
        ax1.set_title(title, fontsize=self.DEFAULT_TITLE_SIZE, fontweight='bold')
        ax1.grid(True, alpha=0.3)
        ax1.legend(fontsize=11)
        ax1.invert_yaxis()  # 倒转Y轴（降雨从上往下）

        # 子图2: 径流
        ax2.plot(time, runoff, color='green', linewidth=self.DEFAULT_LINE_WIDTH,
                label='Runoff')
        ax2.fill_between(time, runoff, alpha=0.3, color='green')
        ax2.set_xlabel('Time (h)', fontsize=self.DEFAULT_FONT_SIZE)
        ax2.set_ylabel('Runoff (m³/s)', fontsize=self.DEFAULT_FONT_SIZE)
        ax2.grid(True, alpha=0.3)
        ax2.legend(fontsize=11)

        plt.tight_layout()

        if filename:
            filepath = os.path.join(self.output_dir, filename)
            fig.savefig(filepath, dpi=self.dpi, bbox_inches='tight')
            print(f"  ✓ Saved: {filepath}")

        return fig


# 便捷函数
def create_standard_profile_plot(
    x, h, Q, S0, canal_length, Q_target,
    gate_positions=None, h_uniform=None,
    output_dir='.', filename='longitudinal_profile.png'
):
    """
    快速创建标准纵剖面图（便捷函数）

    Args:
        x: 位置坐标
        h: 水深数组
        Q: 流量数组
        S0: 渠底坡度
        canal_length: 渠道长度
        Q_target: 目标流量
        gate_positions: 闸门位置列表
        h_uniform: 均匀流水深
        output_dir: 输出目录
        filename: 文件名

    Returns:
        图表对象
    """
    viz = VisualizationTemplates(output_dir=output_dir)

    # 创建纵剖面图
    fig1 = viz.plot_longitudinal_profile(
        x=x, h=h, S0=S0, canal_length=canal_length,
        gate_positions=gate_positions, h_uniform=h_uniform,
        filename=filename.replace('.png', '_profile.png')
    )

    # 创建流量分布图
    fig2 = viz.plot_flow_distribution(
        x=x, Q=Q, Q_target=Q_target,
        gate_positions=gate_positions,
        filename=filename.replace('.png', '_flow.png')
    )

    return fig1, fig2
