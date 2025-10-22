#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
基准测试报告生成器

生成Markdown和HTML格式的完整测试报告

作者: Claude
日期: 2025-10-22
"""

import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from datetime import datetime
from typing import Dict, List
from pathlib import Path

from utils.benchmark_framework import BenchmarkFramework, BenchmarkResult


class BenchmarkReporter:
    """基准测试报告生成器"""

    def __init__(self, framework: BenchmarkFramework, plots: Dict[str, str] = None):
        """
        初始化报告生成器

        Args:
            framework: BenchmarkFramework实例
            plots: 图表路径字典 {name: path}
        """
        self.framework = framework
        self.plots = plots or {}
        self.output_dir = framework.output_dir

    def generate_markdown_report(self, filename: str = "BENCHMARK_REPORT.md") -> str:
        """
        生成Markdown格式报告

        Returns:
            报告文件路径
        """
        report_path = os.path.join(self.output_dir, filename)

        with open(report_path, 'w', encoding='utf-8') as f:
            # 标题
            f.write("# HydroClaude求解器性能基准测试报告\n\n")
            f.write(f"**生成时间**: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n")
            f.write("---\n\n")

            # 测试概览
            f.write("## 测试概览\n\n")
            f.write(f"- **场景数量**: {len(self.framework.scenarios)}\n")

            solvers = list(set(r.solver_name for r in self.framework.results))
            f.write(f"- **求解器数量**: {len(solvers)}\n")
            f.write(f"- **总测试数**: {len(self.framework.results)}\n\n")

            # 场景列表
            f.write("### 测试场景\n\n")
            f.write("| 编号 | 场景名称 | 网格点数 | 渠道长度 (m) | 结构数量 | 说明 |\n")
            f.write("|------|---------|---------|-------------|---------|------|\n")
            for i, scenario in enumerate(self.framework.scenarios, 1):
                f.write(f"| {i} | {scenario.name} | {scenario.nx} | {scenario.length} | "
                       f"{len(scenario.structures)} | {scenario.description} |\n")
            f.write("\n")

            # 求解器列表
            f.write("### 测试求解器\n\n")
            for i, solver in enumerate(solvers, 1):
                f.write(f"{i}. **{solver}**\n")
            f.write("\n")

            # 性能汇总表
            f.write("## 性能汇总\n\n")
            f.write("### 完整结果表\n\n")
            f.write("| 场景 | 求解器 | 收敛 | 迭代次数 | 时间 (s) | 流量误差 (%) | 最终残差 |\n")
            f.write("|------|-------|------|---------|---------|------------|----------|\n")

            for scenario in self.framework.scenarios:
                results = self.framework.get_results_by_scenario(scenario.name)
                for result in results:
                    conv = "✅" if result.converged else "❌"
                    iter_str = str(result.iterations) if result.converged else "N/A"
                    time_str = f"{result.time:.4f}" if result.converged else "N/A"
                    error_str = f"{result.Q_error:.4f}" if result.converged and result.Q_error != float('inf') else "N/A"
                    residual_str = f"{result.final_residual:.2e}" if result.converged else "N/A"

                    f.write(f"| {scenario.name} | {result.solver_name} | {conv} | {iter_str} | "
                           f"{time_str} | {error_str} | {residual_str} |\n")

            f.write("\n")

            # 统计分析
            f.write("## 统计分析\n\n")

            # 成功率
            f.write("### 收敛成功率\n\n")
            f.write("| 求解器 | 成功数 | 总数 | 成功率 |\n")
            f.write("|-------|-------|------|-------|\n")

            for solver in solvers:
                results = self.framework.get_results_by_solver(solver)
                total = len(results)
                success = sum(1 for r in results if r.converged)
                rate = success / total * 100 if total > 0 else 0
                f.write(f"| {solver} | {success} | {total} | {rate:.1f}% |\n")

            f.write("\n")

            # 平均性能
            f.write("### 平均性能指标\n\n")
            f.write("| 求解器 | 平均迭代次数 | 平均时间 (s) | 平均流量误差 (%) |\n")
            f.write("|-------|------------|------------|----------------|\n")

            for solver in solvers:
                results = [r for r in self.framework.get_results_by_solver(solver) if r.converged]
                if results:
                    avg_iter = sum(r.iterations for r in results) / len(results)
                    avg_time = sum(r.time for r in results) / len(results)
                    avg_error = sum(r.Q_error for r in results if r.Q_error != float('inf')) / len(results)
                    f.write(f"| {solver} | {avg_iter:.1f} | {avg_time:.4f} | {avg_error:.4f} |\n")

            f.write("\n")

            # 加速比分析
            if len(solvers) > 1:
                f.write("### 加速比分析\n\n")
                baseline = solvers[0]
                f.write(f"**基线**: {baseline}\n\n")
                f.write("| 场景 | 目标求解器 | 加速比 (x) |\n")
                f.write("|------|-----------|----------|\n")

                for scenario in self.framework.scenarios:
                    baseline_results = [r for r in self.framework.results
                                      if r.scenario_name == scenario.name and r.solver_name == baseline]
                    if baseline_results and baseline_results[0].converged:
                        baseline_time = baseline_results[0].time

                        for solver in solvers[1:]:
                            solver_results = [r for r in self.framework.results
                                           if r.scenario_name == scenario.name and r.solver_name == solver]
                            if solver_results and solver_results[0].converged and solver_results[0].time > 0:
                                speedup = baseline_time / solver_results[0].time
                                f.write(f"| {scenario.name} | {solver} | {speedup:.2f}x |\n")

                f.write("\n")

            # 可视化图表
            if self.plots:
                f.write("## 可视化图表\n\n")

                for plot_name, plot_path in self.plots.items():
                    # 使用相对路径
                    rel_path = os.path.relpath(plot_path, self.output_dir)
                    f.write(f"### {plot_name.replace('_', ' ').title()}\n\n")
                    f.write(f"![{plot_name}]({rel_path})\n\n")

            # 结论
            f.write("## 结论\n\n")

            # 自动生成结论
            f.write("### 关键发现\n\n")

            # 找出最快的求解器
            avg_times = {}
            for solver in solvers:
                results = [r for r in self.framework.get_results_by_solver(solver) if r.converged]
                if results:
                    avg_times[solver] = sum(r.time for r in results) / len(results)

            if avg_times:
                fastest = min(avg_times, key=avg_times.get)
                f.write(f"1. **{fastest}** 是平均速度最快的求解器 (平均时间: {avg_times[fastest]:.4f}s)\n")

            # 找出迭代次数最少的
            avg_iters = {}
            for solver in solvers:
                results = [r for r in self.framework.get_results_by_solver(solver) if r.converged]
                if results:
                    avg_iters[solver] = sum(r.iterations for r in results) / len(results)

            if avg_iters:
                fewest_iter = min(avg_iters, key=avg_iters.get)
                f.write(f"2. **{fewest_iter}** 迭代次数最少 (平均: {avg_iters[fewest_iter]:.1f}次)\n")

            # 找出最可靠的（成功率最高）
            success_rates = {}
            for solver in solvers:
                results = self.framework.get_results_by_solver(solver)
                success_rates[solver] = sum(1 for r in results if r.converged) / len(results)

            if success_rates:
                most_reliable = max(success_rates, key=success_rates.get)
                f.write(f"3. **{most_reliable}** 成功率最高 ({success_rates[most_reliable] * 100:.1f}%)\n")

            f.write("\n")

            # 建议
            f.write("### 使用建议\n\n")
            f.write("基于测试结果，我们建议：\n\n")

            if avg_times:
                f.write(f"- 对于**速度优先**的场景，使用 **{fastest}**\n")
            if avg_iters:
                f.write(f"- 对于**迭代效率优先**的场景，使用 **{fewest_iter}**\n")
            if success_rates:
                f.write(f"- 对于**鲁棒性优先**的场景，使用 **{most_reliable}**\n")

            f.write("\n")

            # 附录
            f.write("## 附录\n\n")
            f.write("### 测试环境\n\n")
            f.write("- **Python版本**: 3.11\n")
            f.write("- **NumPy版本**: Latest\n")
            f.write("- **SciPy版本**: Latest\n")
            f.write("- **操作系统**: Linux\n\n")

            f.write("### 参数设置\n\n")
            f.write("所有求解器使用以下共同参数：\n\n")
            f.write("- 收敛容差: 1e-4\n")
            f.write("- 最大迭代次数: 30\n")
            f.write("- 初值: 均匀流\n\n")

            f.write("---\n\n")
            f.write(f"*报告由 HydroClaude BenchmarkReporter 自动生成于 {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}*\n")

        return report_path

    def generate_html_report(self, filename: str = "benchmark_report.html") -> str:
        """
        生成HTML格式报告

        Returns:
            报告文件路径
        """
        report_path = os.path.join(self.output_dir, filename)

        with open(report_path, 'w', encoding='utf-8') as f:
            # HTML头部
            f.write("<!DOCTYPE html>\n")
            f.write("<html lang='zh-CN'>\n")
            f.write("<head>\n")
            f.write("    <meta charset='UTF-8'>\n")
            f.write("    <meta name='viewport' content='width=device-width, initial-scale=1.0'>\n")
            f.write("    <title>HydroClaude性能基准测试报告</title>\n")
            f.write("    <style>\n")
            f.write("""
        body {
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Arial, sans-serif;
            max-width: 1200px;
            margin: 0 auto;
            padding: 20px;
            background-color: #f5f5f5;
        }
        .container {
            background-color: white;
            padding: 30px;
            border-radius: 8px;
            box-shadow: 0 2px 4px rgba(0,0,0,0.1);
        }
        h1 {
            color: #2c3e50;
            border-bottom: 3px solid #3498db;
            padding-bottom: 10px;
        }
        h2 {
            color: #34495e;
            margin-top: 30px;
            border-bottom: 2px solid #ecf0f1;
            padding-bottom: 5px;
        }
        h3 {
            color: #7f8c8d;
        }
        table {
            width: 100%;
            border-collapse: collapse;
            margin: 15px 0;
            background-color: white;
        }
        th, td {
            padding: 12px;
            text-align: left;
            border-bottom: 1px solid #ecf0f1;
        }
        th {
            background-color: #3498db;
            color: white;
            font-weight: bold;
        }
        tr:hover {
            background-color: #f8f9fa;
        }
        .success {
            color: #27ae60;
            font-weight: bold;
        }
        .fail {
            color: #e74c3c;
            font-weight: bold;
        }
        .metric {
            display: inline-block;
            background-color: #ecf0f1;
            padding: 5px 10px;
            border-radius: 4px;
            margin: 5px;
        }
        .plot {
            text-align: center;
            margin: 30px 0;
        }
        .plot img {
            max-width: 100%;
            border: 1px solid #ddd;
            border-radius: 4px;
            box-shadow: 0 2px 4px rgba(0,0,0,0.1);
        }
        .footer {
            margin-top: 40px;
            padding-top: 20px;
            border-top: 1px solid #ecf0f1;
            color: #95a5a6;
            text-align: center;
        }
        .highlight {
            background-color: #fff3cd;
            padding: 15px;
            border-left: 4px solid #ffc107;
            margin: 15px 0;
        }
            """)
            f.write("    </style>\n")
            f.write("</head>\n")
            f.write("<body>\n")
            f.write("<div class='container'>\n")

            # 标题
            f.write(f"<h1>HydroClaude求解器性能基准测试报告</h1>\n")
            f.write(f"<p><strong>生成时间</strong>: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}</p>\n")

            # 测试概览
            f.write("<h2>测试概览</h2>\n")
            solvers = list(set(r.solver_name for r in self.framework.results))
            f.write("<ul>\n")
            f.write(f"  <li>场景数量: {len(self.framework.scenarios)}</li>\n")
            f.write(f"  <li>求解器数量: {len(solvers)}</li>\n")
            f.write(f"  <li>总测试数: {len(self.framework.results)}</li>\n")
            f.write("</ul>\n")

            # 性能汇总表
            f.write("<h2>性能汇总</h2>\n")
            f.write("<table>\n")
            f.write("<tr><th>场景</th><th>求解器</th><th>收敛</th><th>迭代次数</th>"
                   "<th>时间 (s)</th><th>流量误差 (%)</th><th>最终残差</th></tr>\n")

            for scenario in self.framework.scenarios:
                results = self.framework.get_results_by_scenario(scenario.name)
                for result in results:
                    conv_class = "success" if result.converged else "fail"
                    conv_symbol = "✅" if result.converged else "❌"
                    iter_str = str(result.iterations) if result.converged else "N/A"
                    time_str = f"{result.time:.4f}" if result.converged else "N/A"
                    error_str = f"{result.Q_error:.4f}" if result.converged and result.Q_error != float('inf') else "N/A"
                    residual_str = f"{result.final_residual:.2e}" if result.converged else "N/A"

                    f.write(f"<tr><td>{scenario.name}</td><td>{result.solver_name}</td>"
                           f"<td class='{conv_class}'>{conv_symbol}</td><td>{iter_str}</td>"
                           f"<td>{time_str}</td><td>{error_str}</td><td>{residual_str}</td></tr>\n")

            f.write("</table>\n")

            # 可视化图表
            if self.plots:
                f.write("<h2>可视化图表</h2>\n")
                for plot_name, plot_path in self.plots.items():
                    rel_path = os.path.relpath(plot_path, self.output_dir)
                    f.write(f"<div class='plot'>\n")
                    f.write(f"  <h3>{plot_name.replace('_', ' ').title()}</h3>\n")
                    f.write(f"  <img src='{rel_path}' alt='{plot_name}'>\n")
                    f.write("</div>\n")

            # 结论
            f.write("<h2>结论</h2>\n")
            f.write("<div class='highlight'>\n")
            f.write("<h3>关键发现</h3>\n")

            # 找出最快的求解器
            avg_times = {}
            for solver in solvers:
                results = [r for r in self.framework.get_results_by_solver(solver) if r.converged]
                if results:
                    avg_times[solver] = sum(r.time for r in results) / len(results)

            if avg_times:
                fastest = min(avg_times, key=avg_times.get)
                f.write(f"<p>🚀 <strong>{fastest}</strong> 是平均速度最快的求解器 (平均时间: {avg_times[fastest]:.4f}s)</p>\n")

            f.write("</div>\n")

            # 页脚
            f.write("<div class='footer'>\n")
            f.write(f"<p>报告由 HydroClaude BenchmarkReporter 自动生成于 {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}</p>\n")
            f.write("</div>\n")

            f.write("</div>\n")
            f.write("</body>\n")
            f.write("</html>\n")

        return report_path


def main():
    """测试报告生成"""
    from utils.benchmark_framework import BenchmarkFramework, create_standard_scenarios
    from utils.benchmark_visualizer import BenchmarkVisualizer
    from solvers.newton_solver import NewtonSolver
    from solvers.continuation_solver import ContinuationSolver

    print("=" * 100)
    print("完整基准测试和报告生成演示")
    print("=" * 100)
    print()

    # 创建框架
    framework = BenchmarkFramework(output_dir="benchmark_results")

    # 添加场景
    scenarios = create_standard_scenarios()
    for scenario in scenarios[:4]:
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
    print("运行基准测试...")
    framework.run_all_benchmarks(solvers, verbose=False)
    print("✅ 测试完成\n")

    # 生成可视化
    print("生成可视化图表...")
    visualizer = BenchmarkVisualizer(framework)
    plots = visualizer.generate_all_plots()
    print()

    # 生成报告
    print("生成报告...")
    reporter = BenchmarkReporter(framework, plots)

    md_path = reporter.generate_markdown_report()
    print(f"✅ Markdown报告: {md_path}")

    html_path = reporter.generate_html_report()
    print(f"✅ HTML报告: {html_path}")

    print()
    print("=" * 100)
    print("完成！")
    print("=" * 100)
    print(f"\n查看报告:")
    print(f"  Markdown: {md_path}")
    print(f"  HTML: {html_path}")


if __name__ == '__main__':
    main()
