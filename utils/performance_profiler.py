#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
性能分析和优化工具

提供以下功能：
1. 代码性能分析（运行时间、内存使用）
2. 瓶颈识别
3. 优化建议生成
4. 性能对比（优化前后）
5. 计算效率评估

作者: Claude
日期: 2025-10-24
"""

import time
import numpy as np
from typing import Dict, List, Callable, Any, Optional, Tuple
from dataclasses import dataclass, field
from functools import wraps
import sys
import tracemalloc


@dataclass
class PerformanceMetrics:
    """性能指标"""
    function_name: str
    call_count: int = 0
    total_time: float = 0.0
    min_time: float = float('inf')
    max_time: float = 0.0
    avg_time: float = 0.0
    memory_usage: float = 0.0  # MB
    call_times: List[float] = field(default_factory=list)

    def update(self, elapsed_time: float, memory_mb: float = 0.0):
        """更新性能指标"""
        self.call_count += 1
        self.total_time += elapsed_time
        self.min_time = min(self.min_time, elapsed_time)
        self.max_time = max(self.max_time, elapsed_time)
        self.avg_time = self.total_time / self.call_count
        self.memory_usage = max(self.memory_usage, memory_mb)
        self.call_times.append(elapsed_time)


class PerformanceProfiler:
    """
    性能分析器

    用法：
    ```python
    profiler = PerformanceProfiler()

    @profiler.profile
    def my_function():
        # ...

    # 运行代码
    my_function()

    # 查看报告
    profiler.print_report()
    ```
    """

    def __init__(self, enable_memory_tracking: bool = False):
        """
        初始化性能分析器

        Args:
            enable_memory_tracking: 是否启用内存跟踪（会增加开销）
        """
        self.metrics: Dict[str, PerformanceMetrics] = {}
        self.enable_memory_tracking = enable_memory_tracking
        self._tracking_memory = False

    def profile(self, func: Callable) -> Callable:
        """
        装饰器：分析函数性能

        Args:
            func: 要分析的函数

        Returns:
            包装后的函数
        """
        @wraps(func)
        def wrapper(*args, **kwargs):
            func_name = f"{func.__module__}.{func.__name__}"

            # 初始化指标
            if func_name not in self.metrics:
                self.metrics[func_name] = PerformanceMetrics(func_name)

            # 内存跟踪
            memory_before = 0.0
            if self.enable_memory_tracking:
                if not self._tracking_memory:
                    tracemalloc.start()
                    self._tracking_memory = True
                tracemalloc.reset_peak()

            # 时间测量
            start_time = time.perf_counter()

            # 执行函数
            result = func(*args, **kwargs)

            # 记录时间
            elapsed_time = time.perf_counter() - start_time

            # 记录内存
            memory_usage = 0.0
            if self.enable_memory_tracking:
                current, peak = tracemalloc.get_traced_memory()
                memory_usage = peak / 1024 / 1024  # MB

            # 更新指标
            self.metrics[func_name].update(elapsed_time, memory_usage)

            return result

        return wrapper

    def reset(self):
        """重置所有统计数据"""
        self.metrics.clear()
        if self._tracking_memory:
            tracemalloc.stop()
            self._tracking_memory = False

    def get_metrics(self) -> Dict[str, PerformanceMetrics]:
        """获取所有性能指标"""
        return self.metrics

    def get_sorted_by_total_time(self) -> List[Tuple[str, PerformanceMetrics]]:
        """按总时间排序的函数列表"""
        return sorted(self.metrics.items(), key=lambda x: x[1].total_time, reverse=True)

    def get_bottlenecks(self, top_n: int = 5) -> List[Tuple[str, PerformanceMetrics]]:
        """
        识别性能瓶颈

        Args:
            top_n: 返回前N个瓶颈

        Returns:
            瓶颈函数列表
        """
        sorted_metrics = self.get_sorted_by_total_time()
        return sorted_metrics[:top_n]

    def print_report(self, detailed: bool = False):
        """
        打印性能报告

        Args:
            detailed: 是否打印详细信息
        """
        if not self.metrics:
            print("没有性能数据")
            return

        print("\n" + "=" * 90)
        print("性能分析报告")
        print("=" * 90)

        # 汇总统计
        total_functions = len(self.metrics)
        total_calls = sum(m.call_count for m in self.metrics.values())
        total_time = sum(m.total_time for m in self.metrics.values())

        print(f"\n汇总:")
        print(f"  分析函数数: {total_functions}")
        print(f"  总调用次数: {total_calls}")
        print(f"  总运行时间: {total_time:.4f} 秒")

        # 按总时间排序
        sorted_metrics = self.get_sorted_by_total_time()

        print(f"\n按总时间排序:")
        print("-" * 90)
        print(f"{'函数名':<50} {'调用次数':>10} {'总时间(s)':>12} {'平均(ms)':>12} {'最大(ms)':>12}")
        print("-" * 90)

        for func_name, metrics in sorted_metrics:
            # 简化函数名显示
            display_name = func_name.split('.')[-1] if not detailed else func_name
            print(f"{display_name:<50} {metrics.call_count:>10} "
                  f"{metrics.total_time:>12.6f} "
                  f"{metrics.avg_time*1000:>12.4f} "
                  f"{metrics.max_time*1000:>12.4f}")

        # 内存使用
        if self.enable_memory_tracking:
            print(f"\n内存使用:")
            print("-" * 90)
            print(f"{'函数名':<50} {'峰值内存(MB)':>20}")
            print("-" * 90)
            sorted_by_memory = sorted(
                self.metrics.items(),
                key=lambda x: x[1].memory_usage,
                reverse=True
            )
            for func_name, metrics in sorted_by_memory[:10]:
                display_name = func_name.split('.')[-1] if not detailed else func_name
                print(f"{display_name:<50} {metrics.memory_usage:>20.4f}")

        # 瓶颈分析
        print(f"\n性能瓶颈 (Top 5):")
        print("-" * 90)
        bottlenecks = self.get_bottlenecks(5)
        for i, (func_name, metrics) in enumerate(bottlenecks, 1):
            percentage = (metrics.total_time / total_time * 100) if total_time > 0 else 0
            display_name = func_name.split('.')[-1] if not detailed else func_name
            print(f"  {i}. {display_name}")
            print(f"     总时间: {metrics.total_time:.6f}s ({percentage:.1f}%)")
            print(f"     平均时间: {metrics.avg_time*1000:.4f}ms")
            print(f"     调用次数: {metrics.call_count}")

        print("\n" + "=" * 90)

    def generate_optimization_suggestions(self) -> List[str]:
        """
        生成优化建议

        Returns:
            优化建议列表
        """
        suggestions = []

        if not self.metrics:
            return ["没有足够的性能数据生成建议"]

        # 识别瓶颈
        bottlenecks = self.get_bottlenecks(3)
        total_time = sum(m.total_time for m in self.metrics.values())

        for func_name, metrics in bottlenecks:
            percentage = (metrics.total_time / total_time * 100)
            if percentage > 30:
                suggestions.append(
                    f" {func_name} 占用了 {percentage:.1f}% 的总时间，"
                    f"建议重点优化此函数"
                )

        # 检查频繁调用
        for func_name, metrics in self.metrics.items():
            if metrics.call_count > 1000 and metrics.avg_time > 0.001:
                suggestions.append(
                    f" {func_name} 被调用了 {metrics.call_count} 次，"
                    f"平均耗时 {metrics.avg_time*1000:.2f}ms，"
                    f"考虑使用缓存或向量化优化"
                )

        # 检查时间波动
        for func_name, metrics in self.metrics.items():
            if metrics.call_count > 10:
                time_std = np.std(metrics.call_times)
                if time_std / metrics.avg_time > 0.5:
                    suggestions.append(
                        f"ℹ {func_name} 的执行时间波动较大 "
                        f"(std={time_std*1000:.2f}ms)，可能存在数据相关的性能问题"
                    )

        # 内存建议
        if self.enable_memory_tracking:
            for func_name, metrics in self.metrics.items():
                if metrics.memory_usage > 100:  # 超过100MB
                    suggestions.append(
                        f" {func_name} 峰值内存使用 {metrics.memory_usage:.1f}MB，"
                        f"建议检查是否有不必要的内存分配"
                    )

        if not suggestions:
            suggestions.append(" 未发现明显的性能问题")

        return suggestions


class SimulationOptimizer:
    """
    模拟优化器

    提供针对水力模拟的优化建议
    """

    @staticmethod
    def analyze_grid_efficiency(nx: int, dx: float, dt: float,
                                u_max: float, h_max: float) -> Dict[str, Any]:
        """
        分析网格效率

        Args:
            nx: 网格点数
            dx: 空间步长 (m)
            dt: 时间步长 (s)
            u_max: 最大流速 (m/s)
            h_max: 最大水深 (m)

        Returns:
            分析结果
        """
        g = 9.81

        # 计算CFL数
        c_max = u_max + np.sqrt(g * h_max)  # 最大波速
        cfl = c_max * dt / dx

        # 评估
        result = {
            'nx': nx,
            'dx': dx,
            'dt': dt,
            'cfl': cfl,
            'wave_speed': c_max,
            'is_stable': cfl < 1.0,
            'efficiency_score': 0.0,
            'suggestions': []
        }

        # 稳定性检查
        if cfl >= 1.0:
            result['suggestions'].append(
                f" CFL数 ({cfl:.3f}) >= 1.0，模拟可能不稳定！"
                f"建议减小dt至 {dx/c_max*0.9:.4f}s 或增大dx"
            )
        elif cfl > 0.9:
            result['suggestions'].append(
                f" CFL数 ({cfl:.3f}) 接近上限，建议留有更多余量"
            )
        elif cfl < 0.3:
            result['suggestions'].append(
                f"ℹ CFL数 ({cfl:.3f}) 较小，可以适当增大dt提高计算效率"
            )
        else:
            result['suggestions'].append(
                f" CFL数 ({cfl:.3f}) 合理，稳定性和效率平衡良好"
            )

        # 网格分辨率评估
        if nx < 50:
            result['suggestions'].append(
                f" 网格点数 ({nx}) 较少，可能精度不足"
            )
        elif nx > 500:
            result['suggestions'].append(
                f"ℹ 网格点数 ({nx}) 较多，计算成本较高，确认是否必要"
            )

        # 效率评分 (0-100)
        # 基于CFL数的合理性
        if 0.5 <= cfl <= 0.9:
            cfl_score = 100
        elif 0.3 <= cfl < 0.5:
            cfl_score = 80
        elif cfl < 0.3:
            cfl_score = 60
        elif 0.9 < cfl < 1.0:
            cfl_score = 70
        else:
            cfl_score = 0

        # 基于网格数的合理性
        if 100 <= nx <= 300:
            grid_score = 100
        elif 50 <= nx < 100 or 300 < nx <= 500:
            grid_score = 80
        else:
            grid_score = 60

        result['efficiency_score'] = (cfl_score + grid_score) / 2

        return result

    @staticmethod
    def suggest_optimal_parameters(L: float, T: float,
                                   u_typical: float, h_typical: float,
                                   target_accuracy: str = 'medium') -> Dict[str, Any]:
        """
        建议最优计算参数

        Args:
            L: 计算域长度 (m)
            T: 模拟时间 (s)
            u_typical: 典型流速 (m/s)
            h_typical: 典型水深 (m)
            target_accuracy: 目标精度 ('low', 'medium', 'high')

        Returns:
            建议参数
        """
        g = 9.81
        c_typical = u_typical + np.sqrt(g * h_typical)

        # 根据精度目标设置网格
        if target_accuracy == 'low':
            nx = max(50, int(L / 50))  # 每50m一个点
            cfl_target = 0.8
        elif target_accuracy == 'high':
            nx = max(200, int(L / 5))  # 每5m一个点
            cfl_target = 0.5
        else:  # medium
            nx = max(100, int(L / 10))  # 每10m一个点
            cfl_target = 0.7

        dx = L / (nx - 1)
        dt = cfl_target * dx / c_typical

        # 估计计算成本
        n_steps = int(T / dt)
        estimated_time = nx * n_steps * 1e-6  # 粗略估计（秒）

        return {
            'nx': nx,
            'dx': dx,
            'dt': dt,
            'cfl': cfl_target,
            'n_steps': n_steps,
            'estimated_runtime': estimated_time,
            'memory_estimate_mb': nx * n_steps * 8 / 1024 / 1024 * 3,  # 3个变量
            'recommendations': [
                f"建议网格点数: {nx}",
                f"建议空间步长: {dx:.2f} m",
                f"建议时间步长: {dt:.4f} s",
                f"预计时间步数: {n_steps}",
                f"预计运行时间: {estimated_time:.2f} 秒"
            ]
        }


# 全局profiler实例
_global_profiler = PerformanceProfiler()


def profile(func: Callable) -> Callable:
    """
    便捷装饰器：使用全局profiler

    用法：
    ```python
    @profile
    def my_function():
        ...
    ```
    """
    return _global_profiler.profile(func)


def print_performance_report():
    """打印全局profiler的报告"""
    _global_profiler.print_report()


def get_optimization_suggestions():
    """获取全局profiler的优化建议"""
    return _global_profiler.generate_optimization_suggestions()


if __name__ == "__main__":
    # 测试代码
    print("性能分析工具测试")
    print("=" * 80)

    # 创建profiler
    profiler = PerformanceProfiler(enable_memory_tracking=True)

    # 测试函数
    @profiler.profile
    def slow_function():
        """模拟慢函数"""
        time.sleep(0.01)
        return sum(range(10000))

    @profiler.profile
    def fast_function():
        """模拟快函数"""
        return np.sum(np.arange(10000))

    @profiler.profile
    def variable_time_function(n):
        """执行时间可变的函数"""
        time.sleep(n * 0.001)
        return n ** 2

    # 运行测试
    print("\n运行性能测试...")
    for _ in range(10):
        slow_function()
        fast_function()
        for i in range(5):
            variable_time_function(i)

    # 打印报告
    profiler.print_report()

    # 优化建议
    print("\n优化建议:")
    print("-" * 80)
    suggestions = profiler.generate_optimization_suggestions()
    for suggestion in suggestions:
        print(f"  {suggestion}")

    # 测试网格分析
    print("\n" + "=" * 80)
    print("网格效率分析测试")
    print("=" * 80)

    optimizer = SimulationOptimizer()

    # 测试案例1：合理参数
    result1 = optimizer.analyze_grid_efficiency(
        nx=100, dx=10.0, dt=0.1,
        u_max=2.0, h_max=3.0
    )
    print("\n案例1 - 合理参数:")
    print(f"  效率评分: {result1['efficiency_score']:.1f}/100")
    print(f"  CFL数: {result1['cfl']:.3f}")
    print("  建议:")
    for sug in result1['suggestions']:
        print(f"    {sug}")

    # 测试案例2：不稳定参数
    result2 = optimizer.analyze_grid_efficiency(
        nx=50, dx=20.0, dt=0.5,
        u_max=3.0, h_max=4.0
    )
    print("\n案例2 - 可能不稳定:")
    print(f"  效率评分: {result2['efficiency_score']:.1f}/100")
    print(f"  CFL数: {result2['cfl']:.3f}")
    print(f"  稳定性: {'' if result2['is_stable'] else ''}")
    print("  建议:")
    for sug in result2['suggestions']:
        print(f"    {sug}")

    # 参数优化建议
    print("\n" + "=" * 80)
    print("参数优化建议")
    print("=" * 80)

    optimal = optimizer.suggest_optimal_parameters(
        L=1000.0, T=600.0,
        u_typical=2.0, h_typical=3.0,
        target_accuracy='medium'
    )

    print("\n给定条件:")
    print("  渠道长度: 1000 m")
    print("  模拟时间: 600 s")
    print("  典型流速: 2.0 m/s")
    print("  典型水深: 3.0 m")
    print("  目标精度: medium")

    print("\n优化建议:")
    for rec in optimal['recommendations']:
        print(f"  {rec}")
    print(f"  预计内存使用: {optimal['memory_estimate_mb']:.2f} MB")

    print("\n" + "=" * 80)
