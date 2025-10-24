"""
性能基准测试框架

用于评估和比较不同控制策略的性能，包括：
- PID控制
- MPC控制
- 自适应MPC控制
- 前馈+反馈控制

性能指标：
- 跟踪误差（MAE, RMSE, Max Error）
- 调节时间（Settling Time）
- 超调量（Overshoot）
- 能耗（Energy Consumption）
- 控制输入平滑度（Control Smoothness）

标准测试场景：
- 阶跃响应
- 斜坡跟踪
- 正弦扰动
- 多目标切换
- 扰动抑制

作者：HydroClaude Team
日期：2025-10-24
"""

import numpy as np
import matplotlib.pyplot as plt
from typing import List, Dict, Tuple, Callable, Optional, Any
from dataclasses import dataclass, field
from abc import ABC, abstractmethod
import time
import json
from pathlib import Path


@dataclass
class PerformanceMetrics:
    """性能指标"""
    name: str

    # 跟踪误差
    mae: float = 0.0  # 平均绝对误差
    rmse: float = 0.0  # 均方根误差
    max_error: float = 0.0  # 最大误差

    # 动态性能
    settling_time: float = 0.0  # 调节时间（2%带）
    overshoot: float = 0.0  # 超调量（%）
    rise_time: float = 0.0  # 上升时间（10%-90%）

    # 能耗和平滑度
    total_energy: float = 0.0  # 总能耗
    control_variation: float = 0.0  # 控制输入变化率

    # 计算时间
    computation_time: float = 0.0  # 平均计算时间（毫秒）

    # 原始数据
    time_series: np.ndarray = field(default_factory=lambda: np.array([]))
    reference: np.ndarray = field(default_factory=lambda: np.array([]))
    output: np.ndarray = field(default_factory=lambda: np.array([]))
    control: np.ndarray = field(default_factory=lambda: np.array([]))

    def compute_metrics(self, dt: float = 1.0):
        """从原始数据计算所有性能指标"""
        if len(self.output) == 0 or len(self.reference) == 0:
            return

        # 跟踪误差
        errors = self.reference - self.output
        self.mae = np.mean(np.abs(errors))
        self.rmse = np.sqrt(np.mean(errors**2))
        self.max_error = np.max(np.abs(errors))

        # 动态性能（假设第一个阶跃）
        self._compute_step_response_metrics(dt)

        # 能耗（假设控制输入为流量，积分得到体积）
        if len(self.control) > 0:
            self.total_energy = np.sum(np.abs(self.control)) * dt

            # 控制平滑度（控制输入变化率）
            if len(self.control) > 1:
                control_diff = np.diff(self.control)
                self.control_variation = np.sum(np.abs(control_diff)) / len(control_diff)

    def _compute_step_response_metrics(self, dt: float):
        """计算阶跃响应指标"""
        if len(self.reference) < 2:
            return

        # 检测第一个阶跃
        ref_diff = np.diff(self.reference)
        step_indices = np.where(np.abs(ref_diff) > 0.1 * np.std(self.reference))[0]

        if len(step_indices) == 0:
            return

        step_idx = step_indices[0] + 1
        if step_idx >= len(self.reference) - 1:
            return

        initial_value = self.output[step_idx - 1]
        final_value = self.reference[step_idx]
        step_size = final_value - initial_value

        if abs(step_size) < 1e-6:
            return

        # 超调量
        output_after_step = self.output[step_idx:]
        if step_size > 0:
            peak_value = np.max(output_after_step)
            self.overshoot = max(0, (peak_value - final_value) / step_size * 100)
        else:
            peak_value = np.min(output_after_step)
            self.overshoot = max(0, (final_value - peak_value) / abs(step_size) * 100)

        # 调节时间（2%带）
        tolerance = 0.02 * abs(step_size)
        settled_mask = np.abs(output_after_step - final_value) <= tolerance

        # 找到最后一次进入2%带之前的时刻
        if np.any(settled_mask):
            # 反向查找，找到最后一次离开2%带的时刻
            for i in range(len(settled_mask) - 1, -1, -1):
                if not settled_mask[i]:
                    settling_idx = i + 1
                    break
            else:
                settling_idx = 0

            self.settling_time = settling_idx * dt
        else:
            self.settling_time = len(output_after_step) * dt

        # 上升时间（10%-90%）
        target_10 = initial_value + 0.1 * step_size
        target_90 = initial_value + 0.9 * step_size

        if step_size > 0:
            idx_10 = np.where(output_after_step >= target_10)[0]
            idx_90 = np.where(output_after_step >= target_90)[0]
        else:
            idx_10 = np.where(output_after_step <= target_10)[0]
            idx_90 = np.where(output_after_step <= target_90)[0]

        if len(idx_10) > 0 and len(idx_90) > 0:
            self.rise_time = (idx_90[0] - idx_10[0]) * dt

    def to_dict(self) -> Dict[str, Any]:
        """转换为字典（用于JSON序列化）"""
        return {
            'name': self.name,
            'mae': float(self.mae),
            'rmse': float(self.rmse),
            'max_error': float(self.max_error),
            'settling_time': float(self.settling_time),
            'overshoot': float(self.overshoot),
            'rise_time': float(self.rise_time),
            'total_energy': float(self.total_energy),
            'control_variation': float(self.control_variation),
            'computation_time': float(self.computation_time)
        }


class BenchmarkScenario(ABC):
    """基准测试场景基类"""

    def __init__(self, name: str, duration: float, dt: float):
        """
        初始化

        参数：
            name: 场景名称
            duration: 持续时间（秒）
            dt: 采样时间（秒）
        """
        self.name = name
        self.duration = duration
        self.dt = dt
        self.n_steps = int(duration / dt)
        self.time = np.arange(0, duration, dt)

    @abstractmethod
    def get_reference(self, t: float) -> float:
        """
        获取参考信号

        参数：
            t: 当前时间（秒）

        返回：
            reference: 参考值
        """
        pass

    @abstractmethod
    def get_disturbance(self, t: float) -> float:
        """
        获取扰动信号

        参数：
            t: 当前时间（秒）

        返回：
            disturbance: 扰动值
        """
        pass

    def generate_reference_trajectory(self) -> np.ndarray:
        """生成完整参考轨迹"""
        return np.array([self.get_reference(t) for t in self.time])

    def generate_disturbance_trajectory(self) -> np.ndarray:
        """生成完整扰动轨迹"""
        return np.array([self.get_disturbance(t) for t in self.time])


class StepResponseScenario(BenchmarkScenario):
    """阶跃响应场景"""

    def __init__(self, duration: float = 600.0, dt: float = 1.0,
                 initial_value: float = 2.0, final_value: float = 3.0,
                 step_time: float = 60.0):
        """
        初始化阶跃响应场景

        参数：
            duration: 持续时间（秒）
            dt: 采样时间（秒）
            initial_value: 初始值
            final_value: 最终值
            step_time: 阶跃时刻（秒）
        """
        super().__init__("Step Response", duration, dt)
        self.initial_value = initial_value
        self.final_value = final_value
        self.step_time = step_time

    def get_reference(self, t: float) -> float:
        return self.final_value if t >= self.step_time else self.initial_value

    def get_disturbance(self, t: float) -> float:
        return 0.0


class RampTrackingScenario(BenchmarkScenario):
    """斜坡跟踪场景"""

    def __init__(self, duration: float = 600.0, dt: float = 1.0,
                 initial_value: float = 2.0, ramp_rate: float = 0.01,
                 ramp_start: float = 60.0):
        """
        初始化斜坡跟踪场景

        参数：
            duration: 持续时间（秒）
            dt: 采样时间（秒）
            initial_value: 初始值
            ramp_rate: 斜坡速率（单位/秒）
            ramp_start: 斜坡开始时刻（秒）
        """
        super().__init__("Ramp Tracking", duration, dt)
        self.initial_value = initial_value
        self.ramp_rate = ramp_rate
        self.ramp_start = ramp_start

    def get_reference(self, t: float) -> float:
        if t < self.ramp_start:
            return self.initial_value
        return self.initial_value + self.ramp_rate * (t - self.ramp_start)

    def get_disturbance(self, t: float) -> float:
        return 0.0


class SinusoidalTrackingScenario(BenchmarkScenario):
    """正弦跟踪场景"""

    def __init__(self, duration: float = 600.0, dt: float = 1.0,
                 mean_value: float = 2.5, amplitude: float = 0.5,
                 frequency: float = 0.01):
        """
        初始化正弦跟踪场景

        参数：
            duration: 持续时间（秒）
            dt: 采样时间（秒）
            mean_value: 平均值
            amplitude: 振幅
            frequency: 频率（Hz）
        """
        super().__init__("Sinusoidal Tracking", duration, dt)
        self.mean_value = mean_value
        self.amplitude = amplitude
        self.frequency = frequency

    def get_reference(self, t: float) -> float:
        return self.mean_value + self.amplitude * np.sin(2 * np.pi * self.frequency * t)

    def get_disturbance(self, t: float) -> float:
        return 0.0


class DisturbanceRejectionScenario(BenchmarkScenario):
    """扰动抑制场景"""

    def __init__(self, duration: float = 600.0, dt: float = 1.0,
                 setpoint: float = 2.5, disturbance_magnitude: float = 0.3,
                 disturbance_time: float = 200.0):
        """
        初始化扰动抑制场景

        参数：
            duration: 持续时间（秒）
            dt: 采样时间（秒）
            setpoint: 设定值
            disturbance_magnitude: 扰动幅度
            disturbance_time: 扰动时刻（秒）
        """
        super().__init__("Disturbance Rejection", duration, dt)
        self.setpoint = setpoint
        self.disturbance_magnitude = disturbance_magnitude
        self.disturbance_time = disturbance_time

    def get_reference(self, t: float) -> float:
        return self.setpoint

    def get_disturbance(self, t: float) -> float:
        return self.disturbance_magnitude if t >= self.disturbance_time else 0.0


class MultiSetpointScenario(BenchmarkScenario):
    """多目标切换场景"""

    def __init__(self, duration: float = 1200.0, dt: float = 1.0,
                 setpoints: List[float] = None,
                 switch_times: List[float] = None):
        """
        初始化多目标切换场景

        参数：
            duration: 持续时间（秒）
            dt: 采样时间（秒）
            setpoints: 设定值列表
            switch_times: 切换时刻列表
        """
        super().__init__("Multi-Setpoint", duration, dt)

        if setpoints is None:
            setpoints = [2.0, 3.0, 2.5, 2.8, 2.2]
        if switch_times is None:
            switch_times = [0, 300, 600, 900, 1200]

        self.setpoints = setpoints
        self.switch_times = switch_times

    def get_reference(self, t: float) -> float:
        for i in range(len(self.switch_times) - 1):
            if self.switch_times[i] <= t < self.switch_times[i + 1]:
                return self.setpoints[i]
        return self.setpoints[-1]

    def get_disturbance(self, t: float) -> float:
        return 0.0


class ControllerInterface(ABC):
    """控制器接口"""

    @abstractmethod
    def reset(self):
        """重置控制器状态"""
        pass

    @abstractmethod
    def compute_control(self, reference: float, output: float,
                       disturbance: float = 0.0) -> float:
        """
        计算控制输入

        参数：
            reference: 参考值
            output: 当前输出
            disturbance: 扰动（可选）

        返回：
            control: 控制输入
        """
        pass

    @abstractmethod
    def get_name(self) -> str:
        """获取控制器名称"""
        pass


class BenchmarkRunner:
    """基准测试运行器"""

    def __init__(self, system_model: Callable[[float, float], float],
                 dt: float = 1.0):
        """
        初始化基准测试运行器

        参数：
            system_model: 系统模型函数 f(u, disturbance) -> y
                         应该是一个有状态的仿真器
            dt: 采样时间（秒）
        """
        self.system_model = system_model
        self.dt = dt
        self.results: Dict[str, List[PerformanceMetrics]] = {}

    def run_benchmark(self, controller: ControllerInterface,
                     scenario: BenchmarkScenario,
                     verbose: bool = True) -> PerformanceMetrics:
        """
        运行单个基准测试

        参数：
            controller: 控制器
            scenario: 测试场景
            verbose: 是否显示进度

        返回：
            metrics: 性能指标
        """
        if verbose:
            print(f"\n运行基准测试: {controller.get_name()} - {scenario.name}")

        # 初始化
        controller.reset()

        # 存储数据
        time_series = []
        reference_series = []
        output_series = []
        control_series = []
        computation_times = []

        # 仿真循环
        current_output = scenario.get_reference(0)  # 初始输出等于初始参考

        for step in range(scenario.n_steps):
            t = step * self.dt

            # 获取参考和扰动
            ref = scenario.get_reference(t)
            dist = scenario.get_disturbance(t)

            # 计算控制（计时）
            start_time = time.time()
            control = controller.compute_control(ref, current_output, dist)
            computation_time = (time.time() - start_time) * 1000  # 毫秒
            computation_times.append(computation_time)

            # 系统仿真
            current_output = self.system_model(control, dist)

            # 存储数据
            time_series.append(t)
            reference_series.append(ref)
            output_series.append(current_output)
            control_series.append(control)

            if verbose and step % 100 == 0:
                print(f"  进度: {step}/{scenario.n_steps} "
                      f"(误差: {abs(ref - current_output):.4f})")

        # 计算性能指标
        metrics = PerformanceMetrics(
            name=f"{controller.get_name()} - {scenario.name}",
            time_series=np.array(time_series),
            reference=np.array(reference_series),
            output=np.array(output_series),
            control=np.array(control_series)
        )
        metrics.compute_metrics(dt=self.dt)
        metrics.computation_time = np.mean(computation_times)

        if verbose:
            print(f"  完成! MAE={metrics.mae:.4f}, RMSE={metrics.rmse:.4f}, "
                  f"计算时间={metrics.computation_time:.2f}ms")

        return metrics

    def run_comparison(self, controllers: List[ControllerInterface],
                      scenarios: List[BenchmarkScenario],
                      save_results: bool = True,
                      output_dir: str = "benchmark_results") -> Dict[str, List[PerformanceMetrics]]:
        """
        运行多个控制器和场景的对比测试

        参数：
            controllers: 控制器列表
            scenarios: 测试场景列表
            save_results: 是否保存结果
            output_dir: 输出目录

        返回：
            results: 结果字典 {场景名: [性能指标列表]}
        """
        print("=" * 80)
        print("性能基准测试开始")
        print("=" * 80)

        results = {}

        for scenario in scenarios:
            scenario_results = []

            print(f"\n{'=' * 80}")
            print(f"场景: {scenario.name}")
            print(f"{'=' * 80}")

            for controller in controllers:
                metrics = self.run_benchmark(controller, scenario, verbose=True)
                scenario_results.append(metrics)

            results[scenario.name] = scenario_results

        self.results = results

        # 保存结果
        if save_results:
            self.save_results(output_dir)
            self.plot_comparison(output_dir)

        # 打印总结
        self.print_summary()

        return results

    def save_results(self, output_dir: str = "benchmark_results"):
        """保存结果为JSON文件"""
        output_path = Path(output_dir)
        output_path.mkdir(exist_ok=True)

        # 转换为可序列化的格式
        serializable_results = {}
        for scenario_name, metrics_list in self.results.items():
            serializable_results[scenario_name] = [m.to_dict() for m in metrics_list]

        # 保存JSON
        json_path = output_path / "benchmark_results.json"
        with open(json_path, 'w', encoding='utf-8') as f:
            json.dump(serializable_results, f, indent=2, ensure_ascii=False)

        print(f"\n结果已保存到: {json_path}")

    def plot_comparison(self, output_dir: str = "benchmark_results"):
        """绘制对比图"""
        output_path = Path(output_dir)
        output_path.mkdir(exist_ok=True)

        for scenario_name, metrics_list in self.results.items():
            if len(metrics_list) == 0:
                continue

            # 创建4个子图
            fig, axes = plt.subplots(2, 2, figsize=(15, 10))
            fig.suptitle(f'Performance Comparison - {scenario_name}', fontsize=16)

            # 子图1: 输出跟踪
            ax = axes[0, 0]
            for metrics in metrics_list:
                ax.plot(metrics.time_series, metrics.output,
                       label=metrics.name.split(' - ')[0], alpha=0.7)
            ax.plot(metrics_list[0].time_series, metrics_list[0].reference,
                   'k--', label='Reference', linewidth=2)
            ax.set_xlabel('Time (s)')
            ax.set_ylabel('Output')
            ax.set_title('Output Tracking')
            ax.legend()
            ax.grid(True, alpha=0.3)

            # 子图2: 跟踪误差
            ax = axes[0, 1]
            for metrics in metrics_list:
                error = metrics.reference - metrics.output
                ax.plot(metrics.time_series, error,
                       label=metrics.name.split(' - ')[0], alpha=0.7)
            ax.axhline(y=0, color='k', linestyle='--', linewidth=1)
            ax.set_xlabel('Time (s)')
            ax.set_ylabel('Tracking Error')
            ax.set_title('Tracking Error')
            ax.legend()
            ax.grid(True, alpha=0.3)

            # 子图3: 控制输入
            ax = axes[1, 0]
            for metrics in metrics_list:
                ax.plot(metrics.time_series, metrics.control,
                       label=metrics.name.split(' - ')[0], alpha=0.7)
            ax.set_xlabel('Time (s)')
            ax.set_ylabel('Control Input')
            ax.set_title('Control Input')
            ax.legend()
            ax.grid(True, alpha=0.3)

            # 子图4: 性能指标柱状图
            ax = axes[1, 1]
            metric_names = ['MAE', 'RMSE', 'Max Error']
            x = np.arange(len(metric_names))
            width = 0.8 / len(metrics_list)

            for i, metrics in enumerate(metrics_list):
                values = [metrics.mae, metrics.rmse, metrics.max_error]
                offset = (i - len(metrics_list)/2) * width
                ax.bar(x + offset, values, width,
                      label=metrics.name.split(' - ')[0], alpha=0.7)

            ax.set_xlabel('Metric')
            ax.set_ylabel('Value')
            ax.set_title('Performance Metrics')
            ax.set_xticks(x)
            ax.set_xticklabels(metric_names)
            ax.legend()
            ax.grid(True, alpha=0.3, axis='y')

            plt.tight_layout()

            # 保存图片
            safe_name = scenario_name.replace(' ', '_').replace('/', '_')
            fig_path = output_path / f"comparison_{safe_name}.png"
            plt.savefig(fig_path, dpi=150, bbox_inches='tight')
            plt.close()

            print(f"对比图已保存: {fig_path}")

    def print_summary(self):
        """打印性能总结"""
        print("\n" + "=" * 80)
        print("性能总结")
        print("=" * 80)

        for scenario_name, metrics_list in self.results.items():
            print(f"\n场景: {scenario_name}")
            print("-" * 80)
            print(f"{'控制器':<30} {'MAE':<10} {'RMSE':<10} {'Max Err':<10} {'Overshoot':<12} {'Time(ms)':<10}")
            print("-" * 80)

            for metrics in metrics_list:
                controller_name = metrics.name.split(' - ')[0]
                print(f"{controller_name:<30} "
                      f"{metrics.mae:<10.4f} "
                      f"{metrics.rmse:<10.4f} "
                      f"{metrics.max_error:<10.4f} "
                      f"{metrics.overshoot:<12.2f} "
                      f"{metrics.computation_time:<10.2f}")
