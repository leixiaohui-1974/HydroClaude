#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
HydroClaude 性能基准测试套件

统一的性能测试入口，包含：
1. 求解器性能对比 (Newton vs 迭代法 vs 延拓)
2. Anderson加速性能验证
3. 不同规模问题的可扩展性测试
4. 内存使用分析

使用方法:
    python benchmark_suite.py --all           # 运行所有测试
    python benchmark_suite.py --solvers       # 仅测试求解器
    python benchmark_suite.py --scaling       # 仅测试可扩展性
    python benchmark_suite.py --quick         # 快速测试（小规模）

作者: Claude
日期: 2025-10-22
"""

import sys
import os
sys.path.insert(0, '.')

import argparse
import time
import json
from datetime import datetime
from pathlib import Path
from typing import Dict, List

import numpy as np

from utils.benchmark_framework import BenchmarkFramework, BenchmarkScenario, BenchmarkResult
from physics.steady_saint_venant import SteadySaintVenantSystem
from solvers.newton_solver import NewtonSolver
from solvers.continuation_solver import ContinuationSolver
from utils.canal_utils import compute_steady_uniform_flow


class HydroClaudeBenchmarkSuite:
    """HydroClaude完整性能基准测试套件"""

    def __init__(self, output_dir: str = "benchmark_results"):
        """
        初始化测试套件

        Args:
            output_dir: 结果输出目录
        """
        self.output_dir = output_dir
        self.framework = BenchmarkFramework(output_dir)
        self.timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")

        # 创建输出目录
        Path(output_dir).mkdir(parents=True, exist_ok=True)

        # 测试结果汇总
        self.summary = {
            'timestamp': self.timestamp,
            'test_suites': [],
            'total_tests': 0,
            'passed_tests': 0,
            'failed_tests': 0,
            'total_time': 0.0
        }

    def define_standard_scenarios(self, mode: str = 'standard'):
        """
        定义标准测试场景

        Args:
            mode: 'quick' (快速), 'standard' (标准), 'comprehensive' (全面)
        """
        scenarios = []

        if mode == 'quick':
            # 快速测试 - 小规模
            scenarios = [
                BenchmarkScenario(
                    name="Quick_Small",
                    length=500.0, nx=11, B=10.0, S0=0.001, n=0.025, Q_target=10.0,
                    description="快速测试 - 小规模"
                ),
                BenchmarkScenario(
                    name="Quick_Medium",
                    length=1000.0, nx=21, B=10.0, S0=0.001, n=0.025, Q_target=15.0,
                    description="快速测试 - 中等规模"
                ),
            ]

        elif mode == 'standard':
            # 标准测试 - 覆盖典型规模
            scenarios = [
                BenchmarkScenario(
                    name="Small_System",
                    length=500.0, nx=11, B=10.0, S0=0.001, n=0.025, Q_target=10.0,
                    description="小规模系统 - 11个节点"
                ),
                BenchmarkScenario(
                    name="Medium_System",
                    length=1000.0, nx=21, B=10.0, S0=0.001, n=0.025, Q_target=15.0,
                    description="中等规模系统 - 21个节点"
                ),
                BenchmarkScenario(
                    name="Large_System",
                    length=2000.0, nx=41, B=12.0, S0=0.0008, n=0.025, Q_target=20.0,
                    description="大规模系统 - 41个节点"
                ),
                BenchmarkScenario(
                    name="Very_Large_System",
                    length=5000.0, nx=101, B=15.0, S0=0.0005, n=0.03, Q_target=30.0,
                    description="超大规模系统 - 101个节点"
                ),
            ]

        elif mode == 'comprehensive':
            # 全面测试 - 包含所有规模和多种配置
            scenarios = [
                # 小规模
                BenchmarkScenario(
                    name="Tiny_System",
                    length=200.0, nx=6, B=8.0, S0=0.001, n=0.025, Q_target=5.0,
                    description="微小系统 - 6个节点"
                ),
                BenchmarkScenario(
                    name="Small_System",
                    length=500.0, nx=11, B=10.0, S0=0.001, n=0.025, Q_target=10.0,
                    description="小规模系统 - 11个节点"
                ),
                # 中等规模
                BenchmarkScenario(
                    name="Medium_System",
                    length=1000.0, nx=21, B=10.0, S0=0.001, n=0.025, Q_target=15.0,
                    description="中等系统 - 21个节点"
                ),
                BenchmarkScenario(
                    name="Medium_Large_System",
                    length=1500.0, nx=31, B=11.0, S0=0.0009, n=0.025, Q_target=18.0,
                    description="中大规模系统 - 31个节点"
                ),
                # 大规模
                BenchmarkScenario(
                    name="Large_System",
                    length=2000.0, nx=41, B=12.0, S0=0.0008, n=0.025, Q_target=20.0,
                    description="大规模系统 - 41个节点"
                ),
                BenchmarkScenario(
                    name="Very_Large_System",
                    length=5000.0, nx=101, B=15.0, S0=0.0005, n=0.03, Q_target=30.0,
                    description="超大规模系统 - 101个节点"
                ),
                # 超大规模
                BenchmarkScenario(
                    name="Huge_System",
                    length=10000.0, nx=201, B=20.0, S0=0.0003, n=0.03, Q_target=50.0,
                    description="巨大系统 - 201个节点"
                ),
            ]

        # 添加到框架
        for scenario in scenarios:
            self.framework.add_scenario(scenario)

        return scenarios

    def test_solvers(self, verbose: bool = True):
        """
        测试不同求解器的性能

        对比：
        - Newton法 (直接法)
        - Newton法 (GMRES)
        - 延拓求解器 (粗 → 精)
        """
        if verbose:
            print("=" * 80)
            print("测试套件 1: 求解器性能对比")
            print("=" * 80)
            print()

        results = []
        start_time = time.time()

        for scenario in self.framework.scenarios:
            if verbose:
                print(f"\n{'='*70}")
                print(f"场景: {scenario.name} ({scenario.description})")
                print(f"{'='*70}")

            # 准备系统
            h_uniform = compute_steady_uniform_flow(
                scenario.Q_target, scenario.B, scenario.S0, scenario.n
            )

            # 初值（稍差，测试鲁棒性）
            h_init = np.ones(scenario.nx) * h_uniform * 0.9
            Q_init = np.ones(scenario.nx) * scenario.Q_target * 0.9

            # 测试1: Newton法 (直接求解器)
            if verbose:
                print("\n[1] Newton法 (直接求解器)")

            result_newton_direct = self._run_newton_solver(
                scenario, h_init, Q_init, h_uniform,
                linear_solver='direct',
                solver_name="Newton (Direct)",
                verbose=verbose
            )
            results.append(result_newton_direct)

            # 测试2: Newton法 (GMRES迭代求解器)
            if verbose:
                print("\n[2] Newton法 (GMRES)")

            result_newton_gmres = self._run_newton_solver(
                scenario, h_init, Q_init, h_uniform,
                linear_solver='gmres',
                solver_name="Newton (GMRES)",
                verbose=verbose
            )
            results.append(result_newton_gmres)

            # 测试3: 延拓求解器
            if verbose:
                print("\n[3] 延拓求解器 (粗→精)")

            result_continuation = self._run_continuation_solver(
                scenario, h_init, Q_init, h_uniform,
                solver_name="Continuation",
                verbose=verbose
            )
            results.append(result_continuation)

        elapsed = time.time() - start_time

        # 更新汇总
        self.summary['test_suites'].append({
            'name': 'Solver Comparison',
            'tests': len(results),
            'passed': sum(1 for r in results if r.converged),
            'failed': sum(1 for r in results if not r.converged),
            'time': elapsed
        })
        self.summary['total_tests'] += len(results)
        self.summary['passed_tests'] += sum(1 for r in results if r.converged)
        self.summary['failed_tests'] += sum(1 for r in results if not r.converged)
        self.summary['total_time'] += elapsed

        if verbose:
            print(f"\n{'='*80}")
            print(f"求解器测试完成: {len(results)}个测试, 耗时 {elapsed:.2f}s")
            print(f"{'='*80}\n")

        return results

    def test_scaling(self, verbose: bool = True):
        """
        测试可扩展性

        随着问题规模增长，性能如何变化
        """
        if verbose:
            print("=" * 80)
            print("测试套件 2: 可扩展性测试")
            print("=" * 80)
            print()

        results = []
        start_time = time.time()

        # 确保场景按规模排序
        scenarios_sorted = sorted(
            self.framework.scenarios,
            key=lambda s: s.nx
        )

        if verbose:
            print(f"测试规模范围: {scenarios_sorted[0].nx} → {scenarios_sorted[-1].nx} 节点\n")

        for scenario in scenarios_sorted:
            if verbose:
                print(f"\n规模: {scenario.nx:4d}个节点 ({scenario.name})")

            # 使用Newton法测试
            h_uniform = compute_steady_uniform_flow(
                scenario.Q_target, scenario.B, scenario.S0, scenario.n
            )
            h_init = np.ones(scenario.nx) * h_uniform
            Q_init = np.ones(scenario.nx) * scenario.Q_target

            result = self._run_newton_solver(
                scenario, h_init, Q_init, h_uniform,
                linear_solver='direct',
                solver_name="Scaling Test",
                verbose=False
            )
            results.append(result)

            if verbose:
                status = "✓" if result.converged else "✗"
                print(f"  {status} 迭代: {result.iterations:3d}, "
                      f"时间: {result.time*1000:7.2f}ms, "
                      f"内存: {result.memory_mb:6.2f}MB")

        elapsed = time.time() - start_time

        # 更新汇总
        self.summary['test_suites'].append({
            'name': 'Scalability',
            'tests': len(results),
            'passed': sum(1 for r in results if r.converged),
            'failed': sum(1 for r in results if not r.converged),
            'time': elapsed
        })
        self.summary['total_tests'] += len(results)
        self.summary['passed_tests'] += sum(1 for r in results if r.converged)
        self.summary['failed_tests'] += sum(1 for r in results if not r.converged)
        self.summary['total_time'] += elapsed

        if verbose:
            print(f"\n{'='*80}")
            print(f"可扩展性测试完成: {len(results)}个测试, 耗时 {elapsed:.2f}s")
            print(f"{'='*80}\n")

        return results

    def _run_newton_solver(self, scenario, h_init, Q_init, h_uniform,
                           linear_solver='direct', solver_name="Newton",
                           verbose=False):
        """运行Newton求解器"""
        system = SteadySaintVenantSystem(
            scenario.length, scenario.nx, scenario.B,
            scenario.S0, scenario.n, pseudo_dt=0.1
        )
        system.set_boundary_conditions(
            Q_upstream=scenario.Q_target,
            h_upstream=h_uniform,
            h_downstream=h_uniform
        )

        U_init = system.pack_state(h_init, Q_init)
        system.U_prev = U_init.copy()

        newton = NewtonSolver(
            max_iter=50,
            tol_residual=1e-6,
            linear_solver=linear_solver,
            line_search=True,
            verbose=False
        )

        try:
            start_time = time.time()
            U_sol, info = newton.solve(
                U_init=U_init,
                residual_func=system.compute_residual,
                jacobian_func=system.compute_jacobian
            )
            elapsed = time.time() - start_time

            h_sol, Q_sol = system.unpack_state(U_sol)
            Q_error = abs(np.mean(Q_sol) - scenario.Q_target) / scenario.Q_target * 100

            result = BenchmarkResult(
                scenario_name=scenario.name,
                solver_name=solver_name,
                converged=info['converged'],
                iterations=info['iterations'],
                time=elapsed,
                final_residual=info['residual_norm'],
                Q_error=Q_error,
                h_min=float(np.min(h_sol)),
                h_max=float(np.max(h_sol)),
                Q_min=float(np.min(Q_sol)),
                Q_max=float(np.max(Q_sol)),
                memory_mb=U_sol.nbytes / 1024 / 1024,
                extra_info={'linear_solver': linear_solver}
            )

            if verbose:
                status = "✓" if result.converged else "✗"
                print(f"  {status} 收敛: {result.converged}, 迭代: {result.iterations}, "
                      f"时间: {elapsed*1000:.2f}ms, Q误差: {Q_error:.4f}%")

            return result

        except Exception as e:
            if verbose:
                print(f"  ✗ 失败: {e}")

            return BenchmarkResult(
                scenario_name=scenario.name,
                solver_name=solver_name,
                converged=False,
                iterations=0,
                time=0.0,
                final_residual=np.inf,
                Q_error=np.inf,
                h_min=0.0, h_max=0.0, Q_min=0.0, Q_max=0.0,
                error_message=str(e)
            )

    def _run_continuation_solver(self, scenario, h_init, Q_init, h_uniform,
                                 solver_name="Continuation", verbose=False):
        """运行延拓求解器"""
        system = SteadySaintVenantSystem(
            scenario.length, scenario.nx, scenario.B,
            scenario.S0, scenario.n, pseudo_dt=10.0
        )
        system.set_boundary_conditions(
            Q_upstream=scenario.Q_target,
            h_upstream=h_uniform,
            h_downstream=h_uniform
        )

        U_init = system.pack_state(h_init, Q_init)

        continuation = ContinuationSolver(
            pseudo_dt_sequence=[10.0, 1.0, 0.1],
            newton_max_iter=20,
            newton_tol=1e-4,
            verbose=False
        )

        try:
            start_time = time.time()
            U_sol, info = continuation.solve(system, U_init)
            elapsed = time.time() - start_time

            h_sol, Q_sol = system.unpack_state(U_sol)
            Q_error = abs(np.mean(Q_sol) - scenario.Q_target) / scenario.Q_target * 100

            # Use total_iterations from info dict (key from continuation solver)
            total_iterations = info.get('total_iterations', 0)

            # Get final residual from last stage
            final_residual = info['stage_info'][-1]['residual_norm'] if info.get('stage_info') else np.inf

            result = BenchmarkResult(
                scenario_name=scenario.name,
                solver_name=solver_name,
                converged=info['converged'],
                iterations=total_iterations,
                time=elapsed,
                final_residual=final_residual,
                Q_error=Q_error,
                h_min=float(np.min(h_sol)),
                h_max=float(np.max(h_sol)),
                Q_min=float(np.min(Q_sol)),
                Q_max=float(np.max(Q_sol)),
                memory_mb=U_sol.nbytes / 1024 / 1024,
                extra_info={'stages': info.get('num_stages', 0)}
            )

            if verbose:
                status = "✓" if result.converged else "✗"
                print(f"  {status} 收敛: {result.converged}, 总迭代: {total_iterations}, "
                      f"时间: {elapsed*1000:.2f}ms, Q误差: {Q_error:.4f}%")

            return result

        except Exception as e:
            if verbose:
                print(f"  ✗ 失败: {e}")

            return BenchmarkResult(
                scenario_name=scenario.name,
                solver_name=solver_name,
                converged=False,
                iterations=0,
                time=0.0,
                final_residual=np.inf,
                Q_error=np.inf,
                h_min=0.0, h_max=0.0, Q_min=0.0, Q_max=0.0,
                error_message=str(e)
            )

    def generate_summary_report(self, filename: str = None):
        """生成汇总报告"""
        if filename is None:
            filename = f"benchmark_summary_{self.timestamp}.md"

        filepath = Path(self.output_dir) / filename

        with open(filepath, 'w', encoding='utf-8') as f:
            f.write("# HydroClaude 性能基准测试报告\n\n")
            f.write(f"**测试时间**: {self.summary['timestamp']}\n\n")
            f.write("---\n\n")

            f.write("## 测试概况\n\n")
            f.write(f"- **总测试数**: {self.summary['total_tests']}\n")
            f.write(f"- **通过**: {self.summary['passed_tests']} "
                   f"({self.summary['passed_tests']/self.summary['total_tests']*100:.1f}%)\n")
            f.write(f"- **失败**: {self.summary['failed_tests']}\n")
            f.write(f"- **总耗时**: {self.summary['total_time']:.2f}s\n\n")

            f.write("---\n\n")

            f.write("## 测试套件详情\n\n")
            for suite in self.summary['test_suites']:
                f.write(f"### {suite['name']}\n\n")
                f.write(f"- 测试数: {suite['tests']}\n")
                f.write(f"- 通过: {suite['passed']}\n")
                f.write(f"- 失败: {suite['failed']}\n")
                f.write(f"- 耗时: {suite['time']:.2f}s\n\n")

            f.write("---\n\n")
            f.write("**测试工具**: benchmark_suite.py\n")
            f.write(f"**生成时间**: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")

        print(f"\n✓ 汇总报告已生成: {filepath}")

        return str(filepath)

    def save_results_json(self, filename: str = None):
        """保存结果为JSON格式"""
        if filename is None:
            filename = f"benchmark_results_{self.timestamp}.json"

        filepath = Path(self.output_dir) / filename

        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(self.summary, f, indent=2, ensure_ascii=False)

        print(f"✓ JSON结果已保存: {filepath}")

        return str(filepath)


def main():
    """主函数"""
    parser = argparse.ArgumentParser(
        description="HydroClaude 性能基准测试套件"
    )
    parser.add_argument('--all', action='store_true',
                       help='运行所有测试')
    parser.add_argument('--solvers', action='store_true',
                       help='仅测试求解器性能')
    parser.add_argument('--scaling', action='store_true',
                       help='仅测试可扩展性')
    parser.add_argument('--quick', action='store_true',
                       help='快速测试（小规模）')
    parser.add_argument('--comprehensive', action='store_true',
                       help='全面测试（大规模）')
    parser.add_argument('--output', type=str, default='benchmark_results',
                       help='输出目录 (默认: benchmark_results)')

    args = parser.parse_args()

    # 如果没有指定任何选项，默认运行所有标准测试
    if not any([args.all, args.solvers, args.scaling]):
        args.all = True

    # 确定测试模式
    if args.quick:
        mode = 'quick'
    elif args.comprehensive:
        mode = 'comprehensive'
    else:
        mode = 'standard'

    # 创建测试套件
    suite = HydroClaudeBenchmarkSuite(output_dir=args.output)

    print("="*80)
    print("HydroClaude 性能基准测试套件")
    print("="*80)
    print(f"模式: {mode}")
    print(f"输出目录: {args.output}")
    print("="*80)
    print()

    # 定义测试场景
    suite.define_standard_scenarios(mode=mode)

    # 运行测试
    if args.all or args.solvers:
        suite.test_solvers(verbose=True)

    if args.all or args.scaling:
        suite.test_scaling(verbose=True)

    # 生成报告
    print("\n" + "="*80)
    print("生成测试报告...")
    print("="*80)

    suite.generate_summary_report()
    suite.save_results_json()

    # 打印最终汇总
    print("\n" + "="*80)
    print("测试完成!")
    print("="*80)
    print(f"总测试数: {suite.summary['total_tests']}")
    print(f"通过: {suite.summary['passed_tests']} / 失败: {suite.summary['failed_tests']}")
    print(f"总耗时: {suite.summary['total_time']:.2f}s")
    success_rate = suite.summary['passed_tests'] / suite.summary['total_tests'] * 100
    print(f"成功率: {success_rate:.1f}%")
    print("="*80)
    print()

    return 0 if suite.summary['failed_tests'] == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
