"""
实时监控可视化工具

为渠道控制系统提供实时监控界面：
- 实时数据更新
- 多指标动态显示
- 警报和异常检测
- 历史数据记录
- 交互式图表

应用场景：
- SCADA系统集成
- 实时控制监控
- 运行状态诊断
- 性能评估

作者：HydroClaude Team
日期：2025-10-24
"""

import numpy as np
import matplotlib.pyplot as plt
from matplotlib.animation import FuncAnimation
from matplotlib.patches import Rectangle
from collections import deque
from typing import Dict, List, Callable, Optional, Tuple, Any
from dataclasses import dataclass, field
from datetime import datetime
import time


@dataclass
class AlarmConfig:
    """警报配置"""
    name: str
    variable: str  # 监控变量名
    low_threshold: Optional[float] = None  # 下限
    high_threshold: Optional[float] = None  # 上限
    enabled: bool = True


@dataclass
class MonitorVariable:
    """监控变量定义"""
    name: str  # 变量名
    unit: str  # 单位
    display_name: str  # 显示名称
    color: str = 'blue'  # 绘图颜色
    line_style: str = '-'  # 线型
    line_width: float = 2.0


class RealtimeMonitor:
    """
    实时监控器

    支持多变量实时监控，带动态图表和警报功能。
    """

    def __init__(self,
                 variables: List[MonitorVariable],
                 window_size: int = 100,
                 update_interval: int = 100):
        """
        初始化实时监控器

        参数:
            variables: 监控变量列表
            window_size: 显示窗口大小（数据点数）
            update_interval: 更新间隔（毫秒）
        """
        self.variables = {v.name: v for v in variables}
        self.window_size = window_size
        self.update_interval = update_interval

        # 数据缓冲区
        self.time_data = deque(maxlen=window_size)
        self.data_buffers = {
            var.name: deque(maxlen=window_size)
            for var in variables
        }

        # 警报配置
        self.alarms: Dict[str, AlarmConfig] = {}
        self.active_alarms: Dict[str, bool] = {}

        # 统计信息
        self.stats = {var.name: {'min': None, 'max': None, 'mean': None}
                     for var in variables}

        # 时间起点
        self.start_time = time.time()
        self.current_step = 0

        # 图形对象
        self.fig = None
        self.axes = None
        self.lines = {}
        self.animation = None

    def add_alarm(self, alarm: AlarmConfig):
        """
        添加警报

        参数:
            alarm: 警报配置
        """
        self.alarms[alarm.name] = alarm
        self.active_alarms[alarm.name] = False

    def update_data(self, timestamp: float, data: Dict[str, float]):
        """
        更新监控数据

        参数:
            timestamp: 时间戳
            data: 数据字典 {变量名: 值}
        """
        self.time_data.append(timestamp)

        for var_name, value in data.items():
            if var_name in self.data_buffers:
                self.data_buffers[var_name].append(value)

                # 更新统计信息
                buffer_array = np.array(self.data_buffers[var_name])
                if len(buffer_array) > 0:
                    self.stats[var_name]['min'] = np.min(buffer_array)
                    self.stats[var_name]['max'] = np.max(buffer_array)
                    self.stats[var_name]['mean'] = np.mean(buffer_array)

        # 检查警报
        self._check_alarms(data)

        self.current_step += 1

    def _check_alarms(self, data: Dict[str, float]):
        """检查警报条件"""
        for alarm_name, alarm in self.alarms.items():
            if not alarm.enabled:
                continue

            if alarm.variable not in data:
                continue

            value = data[alarm.variable]
            alarm_triggered = False

            # 检查下限
            if alarm.low_threshold is not None and value < alarm.low_threshold:
                alarm_triggered = True

            # 检查上限
            if alarm.high_threshold is not None and value > alarm.high_threshold:
                alarm_triggered = True

            # 更新警报状态
            was_active = self.active_alarms.get(alarm_name, False)
            self.active_alarms[alarm_name] = alarm_triggered

            # 警报触发事件
            if alarm_triggered and not was_active:
                self._on_alarm_triggered(alarm_name, alarm, value)
            elif not alarm_triggered and was_active:
                self._on_alarm_cleared(alarm_name, alarm)

    def _on_alarm_triggered(self, name: str, alarm: AlarmConfig, value: float):
        """警报触发回调"""
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        print(f"[{timestamp}] ⚠️  ALARM: {name} - {alarm.variable} = {value:.3f}")

    def _on_alarm_cleared(self, name: str, alarm: AlarmConfig):
        """警报清除回调"""
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        print(f"[{timestamp}] ✓  CLEARED: {name}")

    def create_dashboard(self,
                        n_rows: int = 2,
                        n_cols: int = 2,
                        figsize: Tuple[int, int] = (14, 10)) -> Tuple[plt.Figure, np.ndarray]:
        """
        创建监控仪表盘

        参数:
            n_rows: 子图行数
            n_cols: 子图列数
            figsize: 图形大小

        返回:
            fig, axes: 图形和轴对象
        """
        self.fig, self.axes = plt.subplots(n_rows, n_cols, figsize=figsize)
        self.fig.suptitle('Real-time Canal Control Monitor', fontsize=16, fontweight='bold')

        # 扁平化axes数组以便索引
        if n_rows * n_cols == 1:
            self.axes = np.array([self.axes])
        else:
            self.axes = self.axes.flatten()

        return self.fig, self.axes

    def setup_plot(self, ax_index: int, var_names: List[str],
                  title: str, ylabel: str,
                  show_legend: bool = True,
                  show_stats: bool = True,
                  y_limits: Optional[Tuple[float, float]] = None):
        """
        设置单个子图

        参数:
            ax_index: 子图索引
            var_names: 要绘制的变量名列表
            title: 子图标题
            ylabel: Y轴标签
            show_legend: 是否显示图例
            show_stats: 是否显示统计信息
            y_limits: Y轴范围（可选）
        """
        if ax_index >= len(self.axes):
            raise ValueError(f"ax_index {ax_index} out of range")

        ax = self.axes[ax_index]

        # 为每个变量创建线条
        for var_name in var_names:
            if var_name not in self.variables:
                continue

            var = self.variables[var_name]
            line, = ax.plot([], [], label=var.display_name,
                          color=var.color, linestyle=var.line_style,
                          linewidth=var.line_width, alpha=0.8)

            self.lines[f"{ax_index}_{var_name}"] = line

        ax.set_xlabel('Time (s)', fontsize=11)
        ax.set_ylabel(ylabel, fontsize=11)
        ax.set_title(title, fontsize=12, fontweight='bold')
        ax.grid(True, alpha=0.3)

        if show_legend:
            ax.legend(loc='upper right', fontsize=9)

        if y_limits:
            ax.set_ylim(y_limits)

        # 添加统计信息文本框（占位）
        if show_stats:
            ax.text(0.02, 0.98, '', transform=ax.transAxes,
                   fontsize=8, verticalalignment='top',
                   bbox=dict(boxstyle='round', facecolor='wheat', alpha=0.5))

    def update_plot(self, frame):
        """动画更新函数"""
        if len(self.time_data) == 0:
            return []

        time_array = np.array(self.time_data)

        # 更新所有线条
        for key, line in self.lines.items():
            parts = key.split('_', 1)
            if len(parts) != 2:
                continue

            ax_index = int(parts[0])
            var_name = parts[1]

            if var_name in self.data_buffers:
                data_array = np.array(self.data_buffers[var_name])
                line.set_data(time_array, data_array)

        # 更新X轴范围
        for ax in self.axes:
            if len(time_array) > 0:
                ax.set_xlim(time_array[0], time_array[-1])
                ax.relim()
                ax.autoscale_view(scalex=False, scaley=True)

        return list(self.lines.values())

    def start(self, save_animation: bool = False, filename: str = 'monitor.mp4'):
        """
        启动实时监控

        参数:
            save_animation: 是否保存动画
            filename: 保存文件名
        """
        if self.fig is None:
            raise ValueError("请先调用create_dashboard()创建仪表盘")

        self.animation = FuncAnimation(
            self.fig,
            self.update_plot,
            interval=self.update_interval,
            blit=True,
            cache_frame_data=False
        )

        if save_animation:
            print(f"保存动画到: {filename}")
            self.animation.save(filename, writer='ffmpeg', fps=10)

        plt.tight_layout()
        plt.show()


class StaticMonitorReport:
    """
    静态监控报告生成器

    用于生成事后分析报告（非实时）
    """

    def __init__(self):
        """初始化报告生成器"""
        self.data_history = {}
        self.time_history = []

    def add_data(self, timestamp: float, data: Dict[str, float]):
        """
        添加历史数据

        参数:
            timestamp: 时间戳
            data: 数据字典
        """
        self.time_history.append(timestamp)

        for var_name, value in data.items():
            if var_name not in self.data_history:
                self.data_history[var_name] = []
            self.data_history[var_name].append(value)

    def generate_report(self,
                       variables: List[MonitorVariable],
                       alarms: List[AlarmConfig],
                       output_path: str,
                       figsize: Tuple[int, int] = (15, 12)):
        """
        生成监控报告

        参数:
            variables: 监控变量列表
            alarms: 警报配置列表
            output_path: 输出路径
            figsize: 图形大小
        """
        time_array = np.array(self.time_history)

        # 创建图形
        n_vars = len(variables)
        n_rows = (n_vars + 1) // 2
        n_cols = 2

        fig, axes = plt.subplots(n_rows, n_cols, figsize=figsize)
        fig.suptitle('Canal Control Monitoring Report', fontsize=16, fontweight='bold')

        if n_vars == 1:
            axes = np.array([axes])
        else:
            axes = axes.flatten()

        # 绘制每个变量
        for idx, var in enumerate(variables):
            if idx >= len(axes):
                break

            ax = axes[idx]

            if var.name in self.data_history:
                data_array = np.array(self.data_history[var.name])

                # 绘制数据
                ax.plot(time_array, data_array, color=var.color,
                       linestyle=var.line_style, linewidth=var.line_width,
                       label=var.display_name, alpha=0.8)

                # 添加警报阈值线
                for alarm in alarms:
                    if alarm.variable == var.name:
                        if alarm.low_threshold is not None:
                            ax.axhline(y=alarm.low_threshold, color='red',
                                     linestyle='--', linewidth=1.5,
                                     label=f'Low Limit ({alarm.low_threshold})',
                                     alpha=0.7)

                        if alarm.high_threshold is not None:
                            ax.axhline(y=alarm.high_threshold, color='red',
                                     linestyle='--', linewidth=1.5,
                                     label=f'High Limit ({alarm.high_threshold})',
                                     alpha=0.7)

                # 统计信息
                mean_val = np.mean(data_array)
                min_val = np.min(data_array)
                max_val = np.max(data_array)
                std_val = np.std(data_array)

                stats_text = f'Mean: {mean_val:.3f} {var.unit}\n'
                stats_text += f'Min: {min_val:.3f} {var.unit}\n'
                stats_text += f'Max: {max_val:.3f} {var.unit}\n'
                stats_text += f'Std: {std_val:.3f} {var.unit}'

                ax.text(0.02, 0.98, stats_text, transform=ax.transAxes,
                       fontsize=9, verticalalignment='top',
                       bbox=dict(boxstyle='round', facecolor='wheat', alpha=0.5))

                ax.set_xlabel('Time (s)', fontsize=11)
                ax.set_ylabel(f'{var.display_name} ({var.unit})', fontsize=11)
                ax.set_title(var.display_name, fontsize=12, fontweight='bold')
                ax.legend(loc='upper right', fontsize=9)
                ax.grid(True, alpha=0.3)

        # 隐藏多余的子图
        for idx in range(n_vars, len(axes)):
            axes[idx].set_visible(False)

        plt.tight_layout()
        plt.savefig(output_path, dpi=150, bbox_inches='tight')
        print(f"监控报告已保存: {output_path}")
        plt.close()


def create_canal_monitor(window_size: int = 100) -> RealtimeMonitor:
    """
    创建渠道监控器（预配置）

    参数:
        window_size: 显示窗口大小

    返回:
        monitor: 实时监控器
    """
    # 定义监控变量
    variables = [
        MonitorVariable('water_depth', 'm', 'Water Depth', color='blue'),
        MonitorVariable('flow_rate', 'm³/s', 'Flow Rate', color='green'),
        MonitorVariable('control_input', 'm/s', 'Control Input', color='orange'),
        MonitorVariable('tracking_error', 'm', 'Tracking Error', color='red')
    ]

    monitor = RealtimeMonitor(variables, window_size=window_size)

    # 添加默认警报
    monitor.add_alarm(AlarmConfig(
        name='Low Water Level',
        variable='water_depth',
        low_threshold=1.5
    ))

    monitor.add_alarm(AlarmConfig(
        name='High Water Level',
        variable='water_depth',
        high_threshold=3.5
    ))

    monitor.add_alarm(AlarmConfig(
        name='High Tracking Error',
        variable='tracking_error',
        high_threshold=0.5
    ))

    return monitor


# ==================== 简化的模拟数据生成器 ====================

class SimulationDataGenerator:
    """仿真数据生成器（用于测试监控器）"""

    def __init__(self, dt: float = 1.0):
        """
        初始化

        参数:
            dt: 采样时间
        """
        self.dt = dt
        self.t = 0.0
        self.h = 2.5  # 水深
        self.q = 0.0  # 流量
        self.u = 0.0  # 控制输入
        self.r = 2.5  # 参考

    def step(self) -> Dict[str, float]:
        """
        生成一步数据

        返回:
            data: 数据字典
        """
        # 简单的动态模型
        self.h += self.u * self.dt + 0.01 * np.random.randn()

        # 简单的控制逻辑
        error = self.r - self.h
        self.u = 0.1 * error

        # 限制
        self.h = np.clip(self.h, 1.0, 4.0)
        self.u = np.clip(self.u, -0.1, 0.1)

        # 计算流量（假设）
        self.q = 10.0 + 2.0 * self.h

        # 更新时间
        self.t += self.dt

        return {
            'water_depth': self.h,
            'flow_rate': self.q,
            'control_input': self.u,
            'tracking_error': error
        }

    def set_reference(self, r: float):
        """设置参考值"""
        self.r = r
