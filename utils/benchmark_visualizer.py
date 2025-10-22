#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
基准测试可视化工具

生成性能对比图表

作者: Claude
日期: 2025-10-22
"""

import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import numpy as np
import matplotlib.pyplot as plt
import matplotlib as mpl
from typing import List, Dict
from pathlib import Path

from utils.benchmark_framework import BenchmarkFramework, BenchmarkResult

# 设置中文字体
mpl.rcParams['font.sans-serif'] = ['DejaVu Sans', 'Arial Unicode MS', 'SimHei']
mpl.rcParams['axes.unicode_minus'] = False


class BenchmarkVisualizer:
    """基准测试可视化器"""

    def __init__(self, framework: BenchmarkFramework, output_dir: str = None):
        """
        初始化可视化器

        Args:
            framework: BenchmarkFramework实例
            output_dir: 图片输出目录
        """
        self.framework = framework
        self.output_dir = output_dir or framework.output_dir
        Path(self.output_dir).mkdir(parents=True, exist_ok=True)

    def plot_iterations_comparison(self, save_path: str = None) -> str:
        """
        绘制迭代次数对比柱状图

        Returns:
            图片保存路径
        """
        # 按场景分组
        scenarios = list(set(r.scenario_name for r in self.framework.results))
        solvers = list(set(r.solver_name for r in self.framework.results))

        # 准备数据
        data = {}
        for solver in solvers:
            data[solver] = []
            for scenario in scenarios:
                results = [r for r in self.framework.results
                          if r.scenario_name == scenario and r.solver_name == solver]
                if results and results[0].converged:
                    data[solver].append(results[0].iterations)
                else:
                    data[solver].append(0)

        # 绘图
        fig, ax = plt.subplots(figsize=(12, 6))

        x = np.arange(len(scenarios))
        width = 0.35
        offset = width * (len(solvers) - 1) / 2

        colors = ['#1f77b4', '#ff7f0e', '#2ca02c', '#d62728']

        for i, (solver, iterations) in enumerate(data.items()):
            pos = x - offset + i * width
            ax.bar(pos, iterations, width, label=solver, color=colors[i % len(colors)])

        ax.set_xlabel('Test Scenario', fontsize=12)
        ax.set_ylabel('Iterations', fontsize=12)
        ax.set_title('Solver Iteration Comparison', fontsize=14, fontweight='bold')
        ax.set_xticks(x)
        ax.set_xticklabels(scenarios, rotation=15, ha='right')
        ax.legend()
        ax.grid(axis='y', alpha=0.3)

        plt.tight_layout()

        # 保存
        if save_path is None:
            save_path = os.path.join(self.output_dir, 'iterations_comparison.png')
        plt.savefig(save_path, dpi=300, bbox_inches='tight')
        plt.close()

        return save_path

    def plot_time_comparison(self, save_path: str = None) -> str:
        """
        绘制计算时间对比柱状图

        Returns:
            图片保存路径
        """
        scenarios = list(set(r.scenario_name for r in self.framework.results))
        solvers = list(set(r.solver_name for r in self.framework.results))

        # 准备数据
        data = {}
        for solver in solvers:
            data[solver] = []
            for scenario in scenarios:
                results = [r for r in self.framework.results
                          if r.scenario_name == scenario and r.solver_name == solver]
                if results and results[0].converged:
                    data[solver].append(results[0].time)
                else:
                    data[solver].append(0)

        # 绘图
        fig, ax = plt.subplots(figsize=(12, 6))

        x = np.arange(len(scenarios))
        width = 0.35
        offset = width * (len(solvers) - 1) / 2

        colors = ['#1f77b4', '#ff7f0e', '#2ca02c', '#d62728']

        for i, (solver, times) in enumerate(data.items()):
            pos = x - offset + i * width
            ax.bar(pos, times, width, label=solver, color=colors[i % len(colors)])

        ax.set_xlabel('Test Scenario', fontsize=12)
        ax.set_ylabel('Time (seconds)', fontsize=12)
        ax.set_title('Solver Time Comparison', fontsize=14, fontweight='bold')
        ax.set_xticks(x)
        ax.set_xticklabels(scenarios, rotation=15, ha='right')
        ax.legend()
        ax.grid(axis='y', alpha=0.3)

        plt.tight_layout()

        if save_path is None:
            save_path = os.path.join(self.output_dir, 'time_comparison.png')
        plt.savefig(save_path, dpi=300, bbox_inches='tight')
        plt.close()

        return save_path

    def plot_speedup(self, baseline_solver: str, save_path: str = None) -> str:
        """
        绘制加速比图

        Args:
            baseline_solver: 基线求解器名称

        Returns:
            图片保存路径
        """
        scenarios = list(set(r.scenario_name for r in self.framework.results))
        solvers = [s for s in set(r.solver_name for r in self.framework.results) if s != baseline_solver]

        # 计算加速比
        speedup_data = {}
        for solver in solvers:
            speedup_data[solver] = []
            for scenario in scenarios:
                baseline_results = [r for r in self.framework.results
                                  if r.scenario_name == scenario and r.solver_name == baseline_solver]
                solver_results = [r for r in self.framework.results
                                if r.scenario_name == scenario and r.solver_name == solver]

                if baseline_results and solver_results:
                    baseline_result = baseline_results[0]
                    solver_result = solver_results[0]

                    if baseline_result.converged and solver_result.converged and solver_result.time > 0:
                        speedup = baseline_result.time / solver_result.time
                        speedup_data[solver].append(speedup)
                    else:
                        speedup_data[solver].append(0)
                else:
                    speedup_data[solver].append(0)

        # 绘图
        fig, ax = plt.subplots(figsize=(12, 6))

        x = np.arange(len(scenarios))
        width = 0.6 / max(1, len(solvers))

        colors = ['#ff7f0e', '#2ca02c', '#d62728']

        for i, (solver, speedups) in enumerate(speedup_data.items()):
            pos = x + (i - len(solvers)/2 + 0.5) * width
            ax.bar(pos, speedups, width, label=f'{solver} vs {baseline_solver}', color=colors[i % len(colors)])

        # 添加基线
        ax.axhline(y=1.0, color='red', linestyle='--', alpha=0.5, label=f'{baseline_solver} baseline')

        ax.set_xlabel('Test Scenario', fontsize=12)
        ax.set_ylabel('Speedup (x)', fontsize=12)
        ax.set_title(f'Speedup Relative to {baseline_solver}', fontsize=14, fontweight='bold')
        ax.set_xticks(x)
        ax.set_xticklabels(scenarios, rotation=15, ha='right')
        ax.legend()
        ax.grid(axis='y', alpha=0.3)

        plt.tight_layout()

        if save_path is None:
            save_path = os.path.join(self.output_dir, 'speedup_comparison.png')
        plt.savefig(save_path, dpi=300, bbox_inches='tight')
        plt.close()

        return save_path

    def plot_success_rate(self, save_path: str = None) -> str:
        """
        绘制成功率饼图

        Returns:
            图片保存路径
        """
        solvers = list(set(r.solver_name for r in self.framework.results))

        # 计算成功率
        success_rates = {}
        for solver in solvers:
            results = [r for r in self.framework.results if r.solver_name == solver]
            total = len(results)
            success = sum(1 for r in results if r.converged)
            success_rates[solver] = (success, total - success)

        # 绘图
        fig, axes = plt.subplots(1, len(solvers), figsize=(5 * len(solvers), 5))

        if len(solvers) == 1:
            axes = [axes]

        colors = ['#2ca02c', '#d62728']  # 绿色（成功）, 红色（失败）

        for i, solver in enumerate(solvers):
            success, fail = success_rates[solver]
            total = success + fail
            success_pct = success / total * 100 if total > 0 else 0

            axes[i].pie([success, fail], labels=['Success', 'Fail'],
                       colors=colors, autopct='%1.1f%%', startangle=90)
            axes[i].set_title(f'{solver}\n({success}/{total}, {success_pct:.1f}%)', fontweight='bold')

        plt.tight_layout()

        if save_path is None:
            save_path = os.path.join(self.output_dir, 'success_rate.png')
        plt.savefig(save_path, dpi=300, bbox_inches='tight')
        plt.close()

        return save_path

    def plot_scalability(self, save_path: str = None) -> str:
        """
        绘制可扩展性图（时间 vs 网格点数）

        Returns:
            图片保存路径
        """
        # 提取网格大小信息
        grid_sizes = {}
        for scenario in self.framework.scenarios:
            grid_sizes[scenario.name] = scenario.nx

        # 按求解器分组
        solvers = list(set(r.solver_name for r in self.framework.results))

        # 准备数据
        data = {}
        for solver in solvers:
            data[solver] = {'nx': [], 'time': []}
            for result in self.framework.results:
                if result.solver_name == solver and result.converged:
                    nx = grid_sizes.get(result.scenario_name, 0)
                    if nx > 0:
                        data[solver]['nx'].append(nx)
                        data[solver]['time'].append(result.time)

        # 绘图
        fig, ax = plt.subplots(figsize=(10, 6))

        colors = ['#1f77b4', '#ff7f0e', '#2ca02c', '#d62728']
        markers = ['o', 's', '^', 'D']

        for i, solver in enumerate(solvers):
            if data[solver]['nx']:
                # 排序
                sorted_indices = np.argsort(data[solver]['nx'])
                nx_sorted = np.array(data[solver]['nx'])[sorted_indices]
                time_sorted = np.array(data[solver]['time'])[sorted_indices]

                ax.plot(nx_sorted, time_sorted, marker=markers[i % len(markers)],
                       label=solver, color=colors[i % len(colors)], linewidth=2, markersize=8)

        ax.set_xlabel('Grid Points (nx)', fontsize=12)
        ax.set_ylabel('Time (seconds)', fontsize=12)
        ax.set_title('Scalability: Time vs Grid Size', fontsize=14, fontweight='bold')
        ax.legend()
        ax.grid(alpha=0.3)
        ax.set_xscale('log')
        ax.set_yscale('log')

        plt.tight_layout()

        if save_path is None:
            save_path = os.path.join(self.output_dir, 'scalability.png')
        plt.savefig(save_path, dpi=300, bbox_inches='tight')
        plt.close()

        return save_path

    def generate_all_plots(self) -> Dict[str, str]:
        """
        生成所有图表

        Returns:
            Dict: {plot_name: file_path}
        """
        plots = {}

        print("生成可视化图表...")
        print("  1/5 迭代次数对比...", end=" ", flush=True)
        plots['iterations'] = self.plot_iterations_comparison()
        print("✅")

        print("  2/5 计算时间对比...", end=" ", flush=True)
        plots['time'] = self.plot_time_comparison()
        print("✅")

        # 选择基线求解器（第一个求解器）
        solvers = list(set(r.solver_name for r in self.framework.results))
        if len(solvers) > 1:
            print("  3/5 加速比分析...", end=" ", flush=True)
            plots['speedup'] = self.plot_speedup(baseline_solver=solvers[0])
            print("✅")
        else:
            print("  3/5 加速比分析... ⏭️ (需要至少2个求解器)")

        print("  4/5 成功率统计...", end=" ", flush=True)
        plots['success_rate'] = self.plot_success_rate()
        print("✅")

        print("  5/5 可扩展性分析...", end=" ", flush=True)
        plots['scalability'] = self.plot_scalability()
        print("✅")

        print()
        print(f"所有图表已保存到: {self.output_dir}")

        return plots


def main():
    """测试可视化"""
    from utils.benchmark_framework import BenchmarkFramework, create_standard_scenarios
    from solvers.newton_solver import NewtonSolver
    from solvers.continuation_solver import ContinuationSolver

    print("=" * 100)
    print("基准测试可视化演示")
    print("=" * 100)
    print()

    # 创建框架
    framework = BenchmarkFramework(output_dir="benchmark_results")

    # 添加场景
    scenarios = create_standard_scenarios()
    for scenario in scenarios[:4]:  # 测试前4个场景
        framework.add_scenario(scenario)

    # 定义求解器
    def newton_solver(system, U_init):
        system.U_prev = U_init.copy()
        newton = NewtonSolver(max_iter=30, tol_residual=1e-4, verbose=False)
        return newton.solve(
            U_init=U_init,
            residual_func=lambda U: system.compute_residual(U, 0.0),
            jacobian_func=lambda U: system.compute_jacobian(U, 0.0)
        )

    def continuation_solver_func(system, U_init):
        system.U_prev = U_init.copy()
        solver = ContinuationSolver(
            pseudo_dt_sequence=[10.0, 1.0, 0.1],
            newton_max_iter=30,
            newton_tol=1e-4,
            verbose=False
        )
        return solver.solve(system, U_init, t=0.0)

    solvers = {
        "Newton": newton_solver,
        "Continuation": continuation_solver_func
    }

    # 运行测试
    framework.run_all_benchmarks(solvers, verbose=True)

    # 生成可视化
    visualizer = BenchmarkVisualizer(framework)
    plots = visualizer.generate_all_plots()

    print()
    print("=" * 100)
    print("生成的图表:")
    print("=" * 100)
    for name, path in plots.items():
        print(f"  {name}: {path}")


if __name__ == '__main__':
    main()
