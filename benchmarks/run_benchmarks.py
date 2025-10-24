#!/usr/bin/env python3
"""
HydroClaude 性能基准测试套件

测试不同场景下的性能，提供性能参考数据。

运行方式：
    python benchmarks/run_benchmarks.py

输出：
    - 性能报告（终端）
    - 性能数据（JSON）
    - 性能对比图（PNG）
"""

import sys
import os
from pathlib import Path
import time
import json
import numpy as np
import matplotlib.pyplot as plt
from typing import Dict, List, Tuple, Any
from dataclasses import dataclass, asdict

# 添加项目根目录到路径
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from solvers.hydrostatic_canal_solver import HydrostaticCanalSolver
from solvers.gate import SluiceGate, BroadCrestedWeir, PumpStation
from utils.canal_utils import compute_steady_uniform_flow


@dataclass
class BenchmarkResult:
    """基准测试结果"""
    name: str
    description: str
    execution_time: float
    iterations: int
    flow_error: float
    grid_points: int
    structures: int
    performance_ratio: float  # 实时性能倍数

    def to_dict(self):
        return asdict(self)


class PerformanceBenchmark:
    """性能基准测试类"""

    def __init__(self):
        self.results: List[BenchmarkResult] = []

    def benchmark_simple_canal(self) -> BenchmarkResult:
        """
        基准1：简单渠道（无结构物）

        预期：
        - 执行时间 < 0.1s
        - 迭代次数 = 0
        - 流量误差 < 1e-10
        """
        print("\n[1/7] 基准测试：简单渠道（无结构物）")

        # 参数
        L = 10000.0
        nx = 201
        B = 10.0
        S0 = 0.0005
        n = 0.025
        Q_target = 10.0

        # 创建求解器
        solver = HydrostaticCanalSolver(L, nx, B, S0, n, g=9.81)

        # 初始化
        h_uniform = compute_steady_uniform_flow(Q_target, B, S0, n)
        solver.h[:] = h_uniform
        solver.hu[:] = Q_target / B

        # 基准测试
        start = time.time()
        result = solver.solve_steady_state(
            Q_target=Q_target,
            h_downstream=h_uniform,
            max_iterations=5000,
            convergence_tol=0.1,
            dt=0.5,
            verbose=False
        )
        elapsed = time.time() - start

        # 计算性能
        total_time = 0.0  # 稳态没有物理时间
        perf_ratio = float('inf')  # 无穷大倍实时

        benchmark = BenchmarkResult(
            name="simple_canal",
            description="简单渠道（无结构物）",
            execution_time=elapsed,
            iterations=result['iterations'],
            flow_error=result['Q_error_percent'],
            grid_points=nx,
            structures=0,
            performance_ratio=perf_ratio
        )

        print(f"  执行时间: {elapsed:.4f}s")
        print(f"  迭代次数: {result['iterations']}")
        print(f"  流量误差: {result['Q_error_percent']:.6e}%")

        return benchmark

    def benchmark_single_gate(self) -> BenchmarkResult:
        """
        基准2：单闸门渠道

        预期：
        - 执行时间 < 0.5s
        - 迭代次数 < 10
        - 流量误差 < 1e-6
        """
        print("\n[2/7] 基准测试：单闸门渠道")

        # 参数
        L = 10000.0
        nx = 201
        B = 10.0
        S0 = 0.0005
        n = 0.025
        Q_target = 10.0

        # 创建闸门
        gate = SluiceGate(position=5000.0, width=B, opening=2.0, Cd=0.6)

        # 创建求解器
        solver = HydrostaticCanalSolver(
            L, nx, B, S0, n,
            internal_structures=[(5000.0, gate)],
            g=9.81
        )

        # 初始化
        h_uniform = compute_steady_uniform_flow(Q_target, B, S0, n)
        solver.h[:] = h_uniform
        solver.hu[:] = Q_target / B

        # 基准测试
        start = time.time()
        result = solver.solve_steady_state(
            Q_target=Q_target,
            h_downstream=h_uniform,
            max_iterations=5000,
            convergence_tol=0.1,
            dt=0.5,
            verbose=False
        )
        elapsed = time.time() - start

        benchmark = BenchmarkResult(
            name="single_gate",
            description="单闸门渠道",
            execution_time=elapsed,
            iterations=result['iterations'],
            flow_error=result['Q_error_percent'],
            grid_points=nx,
            structures=1,
            performance_ratio=float('inf')
        )

        print(f"  执行时间: {elapsed:.4f}s")
        print(f"  迭代次数: {result['iterations']}")
        print(f"  流量误差: {result['Q_error_percent']:.6e}%")

        return benchmark

    def benchmark_three_gates(self) -> BenchmarkResult:
        """
        基准3：三闸门渠道

        预期：
        - 执行时间 < 2s
        - 迭代次数 < 50
        - 流量误差 < 1e-6
        """
        print("\n[3/7] 基准测试：三闸门渠道")

        # 参数
        L = 10000.0
        nx = 201
        B = 10.0
        S0 = 0.0005
        n = 0.025
        Q_target = 10.0

        # 创建三个闸门
        gate1 = SluiceGate(position=2500.0, width=B, opening=2.0, Cd=0.6)
        gate2 = SluiceGate(position=5000.0, width=B, opening=1.8, Cd=0.6)
        gate3 = SluiceGate(position=7500.0, width=B, opening=1.6, Cd=0.6)

        # 创建求解器
        solver = HydrostaticCanalSolver(
            L, nx, B, S0, n,
            internal_structures=[
                (2500.0, gate1),
                (5000.0, gate2),
                (7500.0, gate3)
            ],
            g=9.81
        )

        # 初始化
        h_uniform = compute_steady_uniform_flow(Q_target, B, S0, n)
        solver.h[:] = h_uniform
        solver.hu[:] = Q_target / B

        # 基准测试
        start = time.time()
        result = solver.solve_steady_state(
            Q_target=Q_target,
            h_downstream=h_uniform,
            max_iterations=5000,
            convergence_tol=0.1,
            dt=0.5,
            verbose=False
        )
        elapsed = time.time() - start

        benchmark = BenchmarkResult(
            name="three_gates",
            description="三闸门渠道",
            execution_time=elapsed,
            iterations=result['iterations'],
            flow_error=result['Q_error_percent'],
            grid_points=nx,
            structures=3,
            performance_ratio=float('inf')
        )

        print(f"  执行时间: {elapsed:.4f}s")
        print(f"  迭代次数: {result['iterations']}")
        print(f"  流量误差: {result['Q_error_percent']:.6e}%")

        return benchmark

    def benchmark_fine_grid(self) -> BenchmarkResult:
        """
        基准4：细网格（高分辨率）

        预期：
        - 执行时间 < 1s
        - 网格点数 = 1001
        """
        print("\n[4/7] 基准测试：细网格（1001个点）")

        # 参数
        L = 10000.0
        nx = 1001  # 细网格
        B = 10.0
        S0 = 0.0005
        n = 0.025
        Q_target = 10.0

        # 创建闸门
        gate = SluiceGate(position=5000.0, width=B, opening=2.0, Cd=0.6)

        # 创建求解器
        solver = HydrostaticCanalSolver(
            L, nx, B, S0, n,
            internal_structures=[(5000.0, gate)],
            g=9.81
        )

        # 初始化
        h_uniform = compute_steady_uniform_flow(Q_target, B, S0, n)
        solver.h[:] = h_uniform
        solver.hu[:] = Q_target / B

        # 基准测试
        start = time.time()
        result = solver.solve_steady_state(
            Q_target=Q_target,
            h_downstream=h_uniform,
            max_iterations=5000,
            convergence_tol=0.1,
            dt=0.5,
            verbose=False
        )
        elapsed = time.time() - start

        benchmark = BenchmarkResult(
            name="fine_grid",
            description="细网格（1001个点）",
            execution_time=elapsed,
            iterations=result['iterations'],
            flow_error=result['Q_error_percent'],
            grid_points=nx,
            structures=1,
            performance_ratio=float('inf')
        )

        print(f"  执行时间: {elapsed:.4f}s")
        print(f"  迭代次数: {result['iterations']}")
        print(f"  流量误差: {result['Q_error_percent']:.6e}%")

        return benchmark

    def benchmark_unsteady_short(self) -> BenchmarkResult:
        """
        基准5：非稳态（短时）

        预期：
        - 执行时间 < 5s
        - 物理时间 = 60s
        - 性能 > 10× 实时
        """
        print("\n[5/7] 基准测试：非稳态（短时，60秒）")

        # 参数
        L = 10000.0
        nx = 201
        B = 10.0
        S0 = 0.0005
        n = 0.025
        Q_target = 10.0

        # 创建闸门
        gate = SluiceGate(position=5000.0, width=B, opening=2.0, Cd=0.6)

        # 创建求解器
        solver = HydrostaticCanalSolver(
            L, nx, B, S0, n,
            internal_structures=[(5000.0, gate)],
            g=9.81
        )

        # 初始化（使用稳态）
        h_uniform = compute_steady_uniform_flow(Q_target, B, S0, n)
        solver.h[:] = h_uniform
        solver.hu[:] = Q_target / B

        # 时间参数
        dt = 1.0
        total_time = 60.0
        n_steps = int(total_time / dt)

        # 边界条件
        solver.Q_upstream = Q_target
        solver.h_downstream = h_uniform

        # 基准测试
        start = time.time()
        for step in range(n_steps):
            h_new, hu_new = solver.step_preissmann(dt)
            solver.h[:] = h_new
            solver.hu[:] = hu_new
        elapsed = time.time() - start

        # 计算流量误差
        Q_final = solver.hu * B
        Q_mean = Q_final.mean()
        Q_error = abs(Q_mean - Q_target) / Q_target * 100

        # 性能倍数
        perf_ratio = total_time / elapsed

        benchmark = BenchmarkResult(
            name="unsteady_short",
            description="非稳态（60秒物理时间）",
            execution_time=elapsed,
            iterations=n_steps,
            flow_error=Q_error,
            grid_points=nx,
            structures=1,
            performance_ratio=perf_ratio
        )

        print(f"  执行时间: {elapsed:.4f}s")
        print(f"  物理时间: {total_time:.1f}s")
        print(f"  时间步数: {n_steps}")
        print(f"  性能倍数: {perf_ratio:.1f}× 实时")
        print(f"  流量误差: {Q_error:.6e}%")

        return benchmark

    def benchmark_unsteady_medium(self) -> BenchmarkResult:
        """
        基准6：非稳态（中时）

        预期：
        - 执行时间 < 30s
        - 物理时间 = 600s
        - 性能 > 20× 实时
        """
        print("\n[6/7] 基准测试：非稳态（中时，600秒）")

        # 参数
        L = 10000.0
        nx = 201
        B = 10.0
        S0 = 0.0005
        n = 0.025
        Q_target = 10.0

        # 创建闸门
        gate = SluiceGate(position=5000.0, width=B, opening=2.0, Cd=0.6)

        # 创建求解器
        solver = HydrostaticCanalSolver(
            L, nx, B, S0, n,
            internal_structures=[(5000.0, gate)],
            g=9.81
        )

        # 初始化（使用稳态）
        h_uniform = compute_steady_uniform_flow(Q_target, B, S0, n)
        solver.h[:] = h_uniform
        solver.hu[:] = Q_target / B

        # 时间参数
        dt = 1.0
        total_time = 600.0
        n_steps = int(total_time / dt)

        # 边界条件
        solver.Q_upstream = Q_target
        solver.h_downstream = h_uniform

        # 基准测试
        start = time.time()
        for step in range(n_steps):
            h_new, hu_new = solver.step_preissmann(dt)
            solver.h[:] = h_new
            solver.hu[:] = hu_new
        elapsed = time.time() - start

        # 计算流量误差
        Q_final = solver.hu * B
        Q_mean = Q_final.mean()
        Q_error = abs(Q_mean - Q_target) / Q_target * 100

        # 性能倍数
        perf_ratio = total_time / elapsed

        benchmark = BenchmarkResult(
            name="unsteady_medium",
            description="非稳态（600秒物理时间）",
            execution_time=elapsed,
            iterations=n_steps,
            flow_error=Q_error,
            grid_points=nx,
            structures=1,
            performance_ratio=perf_ratio
        )

        print(f"  执行时间: {elapsed:.4f}s")
        print(f"  物理时间: {total_time:.1f}s")
        print(f"  时间步数: {n_steps}")
        print(f"  性能倍数: {perf_ratio:.1f}× 实时")
        print(f"  流量误差: {Q_error:.6e}%")

        return benchmark

    def benchmark_scalability(self) -> BenchmarkResult:
        """
        基准7：可扩展性（长渠道）

        预期：
        - 渠道长度 = 50km
        - 网格点数 = 1001
        - 执行时间 < 2s
        """
        print("\n[7/7] 基准测试：可扩展性（50km渠道）")

        # 参数
        L = 50000.0  # 50 km
        nx = 1001
        B = 15.0
        S0 = 0.0005
        n = 0.025
        Q_target = 20.0

        # 创建三个闸门
        gate1 = SluiceGate(position=15000.0, width=B, opening=2.5, Cd=0.6)
        gate2 = SluiceGate(position=25000.0, width=B, opening=2.3, Cd=0.6)
        gate3 = SluiceGate(position=35000.0, width=B, opening=2.1, Cd=0.6)

        # 创建求解器
        solver = HydrostaticCanalSolver(
            L, nx, B, S0, n,
            internal_structures=[
                (15000.0, gate1),
                (25000.0, gate2),
                (35000.0, gate3)
            ],
            g=9.81
        )

        # 初始化
        h_uniform = compute_steady_uniform_flow(Q_target, B, S0, n)
        solver.h[:] = h_uniform
        solver.hu[:] = Q_target / B

        # 基准测试
        start = time.time()
        result = solver.solve_steady_state(
            Q_target=Q_target,
            h_downstream=h_uniform,
            max_iterations=5000,
            convergence_tol=0.1,
            dt=0.5,
            verbose=False
        )
        elapsed = time.time() - start

        benchmark = BenchmarkResult(
            name="scalability",
            description="可扩展性（50km，1001点，3闸门）",
            execution_time=elapsed,
            iterations=result['iterations'],
            flow_error=result['Q_error_percent'],
            grid_points=nx,
            structures=3,
            performance_ratio=float('inf')
        )

        print(f"  渠道长度: {L/1000:.1f} km")
        print(f"  网格点数: {nx}")
        print(f"  结构物数: 3")
        print(f"  执行时间: {elapsed:.4f}s")
        print(f"  迭代次数: {result['iterations']}")
        print(f"  流量误差: {result['Q_error_percent']:.6e}%")

        return benchmark

    def run_all_benchmarks(self):
        """运行所有基准测试"""
        print("=" * 80)
        print("HydroClaude 性能基准测试套件")
        print("=" * 80)

        # 运行所有基准
        benchmarks = [
            self.benchmark_simple_canal,
            self.benchmark_single_gate,
            self.benchmark_three_gates,
            self.benchmark_fine_grid,
            self.benchmark_unsteady_short,
            self.benchmark_unsteady_medium,
            self.benchmark_scalability
        ]

        for benchmark_func in benchmarks:
            result = benchmark_func()
            self.results.append(result)

        # 打印总结
        self.print_summary()

        # 保存结果
        self.save_results()

        # 生成对比图
        self.plot_comparison()

    def print_summary(self):
        """打印总结"""
        print("\n" + "=" * 80)
        print("基准测试总结")
        print("=" * 80)

        print(f"\n{'基准名称':<30} {'执行时间':>12} {'迭代/步数':>10} {'流量误差':>12} {'性能倍数':>12}")
        print("-" * 80)

        for r in self.results:
            perf_str = f"{r.performance_ratio:.1f}×" if r.performance_ratio != float('inf') else "∞"
            print(f"{r.description:<30} {r.execution_time:>10.4f}s {r.iterations:>10} {r.flow_error:>10.2e}% {perf_str:>12}")

        # 统计
        total_time = sum(r.execution_time for r in self.results)
        avg_time = total_time / len(self.results)

        print("-" * 80)
        print(f"{'总执行时间':<30} {total_time:>10.4f}s")
        print(f"{'平均执行时间':<30} {avg_time:>10.4f}s")
        print()

    def save_results(self):
        """保存结果到JSON"""
        output_file = Path(__file__).parent / "benchmark_results.json"

        data = {
            'timestamp': time.strftime('%Y-%m-%d %H:%M:%S'),
            'results': [r.to_dict() for r in self.results],
            'summary': {
                'total_benchmarks': len(self.results),
                'total_time': sum(r.execution_time for r in self.results),
                'average_time': sum(r.execution_time for r in self.results) / len(self.results)
            }
        }

        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=2, ensure_ascii=False)

        print(f"✓ 结果已保存: {output_file}")

    def plot_comparison(self):
        """生成对比图"""
        fig, axes = plt.subplots(2, 2, figsize=(14, 10))

        # 提取数据
        names = [r.description for r in self.results]
        exec_times = [r.execution_time for r in self.results]
        iterations = [r.iterations for r in self.results]
        flow_errors = [r.flow_error for r in self.results]
        perf_ratios = [r.performance_ratio if r.performance_ratio != float('inf') else 0
                       for r in self.results]

        # 子图1: 执行时间
        axes[0, 0].barh(names, exec_times, color='steelblue')
        axes[0, 0].set_xlabel('Execution Time (s)')
        axes[0, 0].set_title('Benchmark Execution Time')
        axes[0, 0].grid(True, alpha=0.3)

        # 子图2: 迭代次数/时间步数
        axes[0, 1].barh(names, iterations, color='orange')
        axes[0, 1].set_xlabel('Iterations / Steps')
        axes[0, 1].set_title('Iterations / Time Steps')
        axes[0, 1].grid(True, alpha=0.3)

        # 子图3: 流量误差（对数尺度）
        axes[1, 0].barh(names, flow_errors, color='green')
        axes[1, 0].set_xlabel('Flow Error (%)')
        axes[1, 0].set_xscale('log')
        axes[1, 0].set_title('Flow Conservation Error')
        axes[1, 0].grid(True, alpha=0.3)

        # 子图4: 性能倍数
        # 只显示非稳态的性能倍数
        unsteady_names = [names[i] for i, r in enumerate(perf_ratios) if r > 0]
        unsteady_perfs = [r for r in perf_ratios if r > 0]

        if unsteady_names:
            axes[1, 1].barh(unsteady_names, unsteady_perfs, color='purple')
            axes[1, 1].set_xlabel('Performance Ratio (× Real-time)')
            axes[1, 1].set_title('Real-time Performance')
            axes[1, 1].grid(True, alpha=0.3)
        else:
            axes[1, 1].text(0.5, 0.5, 'No unsteady benchmarks',
                           ha='center', va='center', transform=axes[1, 1].transAxes)

        plt.tight_layout()

        # 保存图片
        output_file = Path(__file__).parent / "benchmark_comparison.png"
        plt.savefig(output_file, dpi=150, bbox_inches='tight')
        print(f"✓ 对比图已保存: {output_file}")

        plt.close()


def main():
    """主函数"""
    benchmark = PerformanceBenchmark()
    benchmark.run_all_benchmarks()

    print("\n" + "=" * 80)
    print("基准测试完成！")
    print("=" * 80)
    print()
    print("生成的文件：")
    print("  - benchmarks/benchmark_results.json    # 详细结果数据")
    print("  - benchmarks/benchmark_comparison.png   # 性能对比图")
    print()


if __name__ == "__main__":
    main()
