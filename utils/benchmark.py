"""
性能基准测试工具 - Benchmark Utility

提供系统性的性能测试和基准分析功能，用于评估求解器性能、
比较不同配置、检测性能回归等。

主要功能：
- 求解器性能基准测试
- 多场景性能对比
- 性能报告生成
- 性能回归检测
- 并行性能测试

使用示例：
    from utils.benchmark import BenchmarkSuite, PerformanceProfiler

    # 创建基准测试套件
    suite = BenchmarkSuite()

    # 添加测试案例
    suite.add_benchmark("canal_flow", params={
        'length': 5000,
        'nx': 100,
        'T': 3600
    })

    # 运行测试
    results = suite.run_all()

    # 生成报告
    suite.generate_report("benchmark_report.html")

作者: Claude Code
创建日期: 2025-10-24
"""

import time
import sys
import os
from pathlib import Path
from typing import Dict, List, Tuple, Callable, Any, Optional
import numpy as np
import json
from dataclasses import dataclass, field, asdict
from datetime import datetime
import tracemalloc
import psutil

# 确保能导入项目模块
sys.path.insert(0, str(Path(__file__).parent.parent))


@dataclass
class BenchmarkResult:
    """基准测试结果"""
    name: str
    status: str  # 'success', 'failed', 'timeout'
    execution_time: float  # 秒
    memory_peak: float  # MB
    cpu_usage: float  # %
    metrics: Dict[str, Any] = field(default_factory=dict)
    error_message: str = ""
    timestamp: str = field(default_factory=lambda: datetime.now().isoformat())

    def to_dict(self) -> Dict:
        """转换为字典"""
        return asdict(self)


class PerformanceProfiler:
    """性能分析器"""

    def __init__(self):
        self.start_time = None
        self.process = psutil.Process()
        self.initial_cpu_times = None
        self.tracemalloc_started = False

    def start(self):
        """开始性能分析"""
        # 记录开始时间
        self.start_time = time.time()

        # 记录初始CPU时间
        self.initial_cpu_times = self.process.cpu_times()

        # 开始内存跟踪
        if not self.tracemalloc_started:
            tracemalloc.start()
            self.tracemalloc_started = True
        else:
            tracemalloc.clear_traces()

    def stop(self) -> Dict[str, float]:
        """
        停止性能分析并返回结果

        Returns:
            包含execution_time, memory_peak, cpu_usage的字典
        """
        # 计算执行时间
        execution_time = time.time() - self.start_time

        # 获取峰值内存
        current, peak = tracemalloc.get_traced_memory()
        memory_peak = peak / (1024 * 1024)  # 转换为MB

        # 计算CPU使用率
        final_cpu_times = self.process.cpu_times()
        cpu_time = (
            (final_cpu_times.user - self.initial_cpu_times.user) +
            (final_cpu_times.system - self.initial_cpu_times.system)
        )
        cpu_usage = (cpu_time / execution_time * 100) if execution_time > 0 else 0

        return {
            'execution_time': execution_time,
            'memory_peak': memory_peak,
            'cpu_usage': cpu_usage
        }


class BenchmarkSuite:
    """基准测试套件"""

    def __init__(self, name: str = "HydroClaude Benchmarks"):
        self.name = name
        self.benchmarks: List[Tuple[str, Callable, Dict]] = []
        self.results: List[BenchmarkResult] = []
        self.profiler = PerformanceProfiler()

    def add_benchmark(self, name: str, func: Callable, params: Dict = None,
                     timeout: float = 300):
        """
        添加基准测试

        Args:
            name: 测试名称
            func: 测试函数
            params: 测试参数
            timeout: 超时时间（秒）
        """
        self.benchmarks.append((name, func, params or {}, timeout))

    def run_benchmark(self, name: str, func: Callable, params: Dict,
                     timeout: float) -> BenchmarkResult:
        """运行单个基准测试"""
        print(f"\n运行基准测试: {name}")
        print(f"参数: {params}")

        # 开始性能分析
        self.profiler.start()

        result = BenchmarkResult(
            name=name,
            status='unknown',
            execution_time=0.0,
            memory_peak=0.0,
            cpu_usage=0.0
        )

        try:
            # 运行测试函数
            start = time.time()
            metrics = func(**params)

            # 检查是否超时
            if time.time() - start > timeout:
                result.status = 'timeout'
                result.error_message = f"Timeout after {timeout}s"
            else:
                result.status = 'success'
                result.metrics = metrics or {}

        except Exception as e:
            result.status = 'failed'
            result.error_message = str(e)
            print(f"  ❌ 失败: {e}")

        # 停止性能分析并获取结果
        perf_stats = self.profiler.stop()
        result.execution_time = perf_stats['execution_time']
        result.memory_peak = perf_stats['memory_peak']
        result.cpu_usage = perf_stats['cpu_usage']

        # 打印结果
        if result.status == 'success':
            print(f"  ✅ 成功")
        print(f"  执行时间: {result.execution_time:.3f}s")
        print(f"  峰值内存: {result.memory_peak:.2f} MB")
        print(f"  CPU使用率: {result.cpu_usage:.1f}%")

        if result.metrics:
            print(f"  性能指标: {result.metrics}")

        return result

    def run_all(self, verbose: bool = True) -> List[BenchmarkResult]:
        """运行所有基准测试"""
        print("=" * 70)
        print(f"  {self.name}")
        print("=" * 70)
        print(f"\n总计 {len(self.benchmarks)} 个基准测试\n")

        self.results = []

        for name, func, params, timeout in self.benchmarks:
            result = self.run_benchmark(name, func, params, timeout)
            self.results.append(result)

        self.print_summary()

        return self.results

    def print_summary(self):
        """打印测试摘要"""
        print("\n" + "=" * 70)
        print("  测试摘要")
        print("=" * 70 + "\n")

        total = len(self.results)
        success = sum(1 for r in self.results if r.status == 'success')
        failed = sum(1 for r in self.results if r.status == 'failed')
        timeout = sum(1 for r in self.results if r.status == 'timeout')

        print(f"总计: {total}")
        print(f"  ✅ 成功: {success}")
        print(f"  ❌ 失败: {failed}")
        print(f"  ⏱️  超时: {timeout}")
        print(f"\n成功率: {success/total*100:.1f}%")

        # 性能统计
        if success > 0:
            successful_results = [r for r in self.results if r.status == 'success']

            total_time = sum(r.execution_time for r in successful_results)
            avg_time = total_time / len(successful_results)
            max_memory = max(r.memory_peak for r in successful_results)
            avg_cpu = sum(r.cpu_usage for r in successful_results) / len(successful_results)

            print(f"\n性能统计:")
            print(f"  总执行时间: {total_time:.2f}s")
            print(f"  平均执行时间: {avg_time:.3f}s")
            print(f"  最大内存使用: {max_memory:.2f} MB")
            print(f"  平均CPU使用率: {avg_cpu:.1f}%")

    def save_results(self, filename: str = "benchmark_results.json"):
        """保存测试结果到JSON文件"""
        data = {
            'suite_name': self.name,
            'timestamp': datetime.now().isoformat(),
            'total_tests': len(self.results),
            'results': [r.to_dict() for r in self.results]
        }

        output_path = Path(filename)
        output_path.write_text(json.dumps(data, indent=2, ensure_ascii=False))
        print(f"\n结果已保存到: {output_path}")

    def generate_report(self, filename: str = "benchmark_report.html"):
        """生成HTML性能报告"""
        html_content = self._generate_html_report()

        output_path = Path(filename)
        output_path.write_text(html_content, encoding='utf-8')
        print(f"HTML报告已生成: {output_path}")

    def _generate_html_report(self) -> str:
        """生成HTML报告内容"""
        # 统计数据
        total = len(self.results)
        success = sum(1 for r in self.results if r.status == 'success')
        failed = sum(1 for r in self.results if r.status == 'failed')

        html = f"""<!DOCTYPE html>
<html>
<head>
    <meta charset="utf-8">
    <title>{self.name} - 性能基准报告</title>
    <style>
        body {{
            font-family: 'Segoe UI', Arial, sans-serif;
            margin: 0;
            padding: 20px;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        }}
        .container {{
            max-width: 1400px;
            margin: 0 auto;
            background: white;
            border-radius: 10px;
            padding: 30px;
            box-shadow: 0 10px 40px rgba(0,0,0,0.3);
        }}
        h1 {{
            color: #333;
            border-bottom: 3px solid #667eea;
            padding-bottom: 10px;
        }}
        .summary {{
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(150px, 1fr));
            gap: 15px;
            margin: 20px 0;
        }}
        .summary-card {{
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: white;
            padding: 15px;
            border-radius: 8px;
            text-align: center;
        }}
        .summary-card h3 {{
            margin: 0 0 8px 0;
            font-size: 1.8em;
        }}
        table {{
            width: 100%;
            border-collapse: collapse;
            margin: 20px 0;
        }}
        th, td {{
            padding: 12px;
            text-align: left;
            border-bottom: 1px solid #ddd;
        }}
        th {{
            background-color: #667eea;
            color: white;
            font-weight: bold;
        }}
        tr:hover {{
            background-color: #f5f5f5;
        }}
        .status {{
            display: inline-block;
            padding: 4px 12px;
            border-radius: 12px;
            font-weight: bold;
            font-size: 0.9em;
        }}
        .status.success {{
            background-color: #4caf50;
            color: white;
        }}
        .status.failed, .status.timeout {{
            background-color: #f44336;
            color: white;
        }}
        .chart {{
            margin: 30px 0;
            padding: 20px;
            background: #f9f9f9;
            border-radius: 8px;
        }}
        .bar {{
            background: linear-gradient(90deg, #667eea 0%, #764ba2 100%);
            height: 30px;
            border-radius: 4px;
            margin: 8px 0;
            position: relative;
        }}
        .bar-label {{
            position: absolute;
            right: 10px;
            top: 50%;
            transform: translateY(-50%);
            color: white;
            font-weight: bold;
        }}
        .footer {{
            text-align: center;
            margin-top: 30px;
            padding-top: 20px;
            border-top: 1px solid #ddd;
            color: #666;
        }}
    </style>
</head>
<body>
    <div class="container">
        <h1>🏆 {self.name}</h1>
        <p>生成时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}</p>

        <div class="summary">
            <div class="summary-card">
                <h3>{total}</h3>
                <p>总测试数</p>
            </div>
            <div class="summary-card">
                <h3>{success}</h3>
                <p>成功</p>
            </div>
            <div class="summary-card">
                <h3>{failed}</h3>
                <p>失败</p>
            </div>
            <div class="summary-card">
                <h3>{success/total*100:.1f}%</h3>
                <p>成功率</p>
            </div>
        </div>

        <h2>📊 详细结果</h2>
        <table>
            <thead>
                <tr>
                    <th>测试名称</th>
                    <th>状态</th>
                    <th>执行时间 (s)</th>
                    <th>峰值内存 (MB)</th>
                    <th>CPU使用率 (%)</th>
                    <th>性能指标</th>
                </tr>
            </thead>
            <tbody>
"""

        for r in self.results:
            metrics_str = ", ".join(f"{k}: {v}" for k, v in r.metrics.items()) if r.metrics else "-"

            html += f"""
                <tr>
                    <td>{r.name}</td>
                    <td><span class="status {r.status}">{r.status}</span></td>
                    <td>{r.execution_time:.3f}</td>
                    <td>{r.memory_peak:.2f}</td>
                    <td>{r.cpu_usage:.1f}</td>
                    <td style="font-size: 0.85em;">{metrics_str}</td>
                </tr>
"""

        html += """
            </tbody>
        </table>

        <h2>⏱️ 执行时间对比</h2>
        <div class="chart">
"""

        # 添加执行时间柱状图
        successful_results = [r for r in self.results if r.status == 'success']
        if successful_results:
            max_time = max(r.execution_time for r in successful_results)

            for r in successful_results:
                width_pct = (r.execution_time / max_time * 100) if max_time > 0 else 0
                html += f"""
            <div style="margin: 15px 0;">
                <div style="font-weight: bold; margin-bottom: 5px;">{r.name}</div>
                <div class="bar" style="width: {width_pct}%;">
                    <span class="bar-label">{r.execution_time:.3f}s</span>
                </div>
            </div>
"""

        html += """
        </div>

        <div class="footer">
            <p>Generated with <a href="https://claude.com/claude-code">Claude Code</a></p>
        </div>
    </div>
</body>
</html>
"""

        return html


# ============================================================================
# 预定义基准测试案例
# ============================================================================

def benchmark_canal_solver_basic(length: float = 5000, nx: int = 100,
                                 T: float = 3600, dt: float = 1.0) -> Dict:
    """
    渠道求解器基础性能测试

    Args:
        length: 渠道长度 (m)
        nx: 网格数量
        T: 模拟时间 (s)
        dt: 时间步长 (s)

    Returns:
        性能指标字典
    """
    from solvers.hydrostatic_canal_solver import HydrostaticCanalSolver

    # 创建求解器
    solver = HydrostaticCanalSolver(
        length=length,
        nx=nx,
        width=10.0,
        manning_n=0.025,
        slope=0.0001,
        dt=dt
    )

    # 设置边界条件
    solver.Q_in = 20.0
    solver.h_downstream = 2.0

    # 运行模拟
    n_steps = int(T / dt)
    for _ in range(n_steps):
        solver.step()

    # 计算性能指标
    metrics = {
        'n_steps': n_steps,
        'final_time': solver.t,
        'cells_per_second': nx * n_steps / (time.time() - solver.t),
        'mean_water_depth': float(np.mean(solver.h))
    }

    return metrics


def benchmark_steady_state_convergence(length: float = 10000, nx: int = 200,
                                      Q_target: float = 30.0) -> Dict:
    """
    稳态收敛性能测试

    Args:
        length: 渠道长度 (m)
        nx: 网格数量
        Q_target: 目标流量 (m³/s)

    Returns:
        性能指标字典
    """
    from solvers.hydrostatic_canal_solver import HydrostaticCanalSolver

    solver = HydrostaticCanalSolver(
        length=length,
        nx=nx,
        width=12.0,
        manning_n=0.025,
        slope=0.0002,
        dt=10.0
    )

    # 求解稳态
    start = time.time()
    h_steady, Q_steady = solver.solve_steady_state(
        Q_target=Q_target,
        h_downstream=2.5,
        max_iter=1000,
        tol=1e-6
    )
    convergence_time = time.time() - start

    metrics = {
        'convergence_time': convergence_time,
        'final_Q': float(Q_steady),
        'Q_error': float(abs(Q_steady - Q_target)),
        'mean_depth': float(np.mean(h_steady))
    }

    return metrics


def benchmark_mpc_control(T: float = 3600, dt: float = 10.0) -> Dict:
    """
    MPC控制器性能测试

    Args:
        T: 模拟时间 (s)
        dt: 时间步长 (s)

    Returns:
        性能指标字典
    """
    from solvers.hydrostatic_canal_solver import HydrostaticCanalSolver
    from control.mpc_controller import MPCController

    # 创建求解器
    solver = HydrostaticCanalSolver(
        length=5000,
        nx=50,
        width=10.0,
        manning_n=0.025,
        slope=0.0001,
        dt=dt
    )

    # 创建MPC控制器
    controller = MPCController(
        horizon=10,
        dt=dt,
        target_level=2.5
    )

    # 运行控制模拟
    n_steps = int(T / dt)
    errors = []

    for step in range(n_steps):
        # 获取当前状态
        current_h = float(solver.h[25])  # 中点水位

        # 计算控制输入
        u = controller.compute_control(current_h)

        # 应用控制
        solver.Q_in = u
        solver.step()

        # 记录误差
        errors.append(abs(current_h - 2.5))

    metrics = {
        'n_steps': n_steps,
        'mean_absolute_error': float(np.mean(errors)),
        'max_error': float(np.max(errors)),
        'final_error': float(errors[-1])
    }

    return metrics


def create_standard_benchmark_suite() -> BenchmarkSuite:
    """
    创建标准基准测试套件

    Returns:
        配置好的BenchmarkSuite对象
    """
    suite = BenchmarkSuite("HydroClaude 标准性能基准")

    # 基础求解器测试 - 不同网格规模
    suite.add_benchmark(
        "Canal_Solver_Small",
        benchmark_canal_solver_basic,
        {'length': 5000, 'nx': 50, 'T': 1800, 'dt': 2.0},
        timeout=60
    )

    suite.add_benchmark(
        "Canal_Solver_Medium",
        benchmark_canal_solver_basic,
        {'length': 10000, 'nx': 100, 'T': 3600, 'dt': 2.0},
        timeout=120
    )

    suite.add_benchmark(
        "Canal_Solver_Large",
        benchmark_canal_solver_basic,
        {'length': 20000, 'nx': 200, 'T': 3600, 'dt': 2.0},
        timeout=300
    )

    # 稳态收敛测试
    suite.add_benchmark(
        "Steady_State_Convergence",
        benchmark_steady_state_convergence,
        {'length': 10000, 'nx': 150, 'Q_target': 25.0},
        timeout=30
    )

    # MPC控制测试
    suite.add_benchmark(
        "MPC_Control_Performance",
        benchmark_mpc_control,
        {'T': 1800, 'dt': 10.0},
        timeout=120
    )

    return suite


def main():
    """主函数 - 运行标准基准测试"""
    print("\n" + "="*70)
    print("  HydroClaude 性能基准测试工具")
    print("="*70 + "\n")

    # 创建并运行标准测试套件
    suite = create_standard_benchmark_suite()
    results = suite.run_all()

    # 保存结果
    suite.save_results("benchmark_results.json")

    # 生成HTML报告
    suite.generate_report("benchmark_report.html")

    print("\n✅ 基准测试完成！")


if __name__ == "__main__":
    main()
