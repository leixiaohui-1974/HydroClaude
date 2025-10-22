#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
性能基准测试框架

提供统一的接口来测试和对比不同求解器的性能

作者: Claude
日期: 2025-10-22
"""

import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import numpy as np
import time
from typing import Dict, List, Tuple, Optional, Callable
from dataclasses import dataclass, field
from datetime import datetime

from physics.steady_saint_venant import SteadySaintVenantSystem
from solvers.newton_solver import NewtonSolver
from solvers.continuation_solver import ContinuationSolver
from utils.canal_utils import compute_steady_uniform_flow


@dataclass
class BenchmarkScenario:
    """基准测试场景配置"""
    name: str
    length: float
    nx: int
    B: float
    S0: float
    n: float
    Q_target: float
    structures: List[Tuple[float, object]] = field(default_factory=list)
    description: str = ""

    def __post_init__(self):
        if not self.description:
            self.description = f"{self.name} - {self.nx}点, {len(self.structures)}个结构"


@dataclass
class BenchmarkResult:
    """单次测试结果"""
    scenario_name: str
    solver_name: str
    converged: bool
    iterations: int
    time: float
    final_residual: float
    Q_error: float  # 流量相对误差 (%)
    h_min: float
    h_max: float
    Q_min: float
    Q_max: float
    memory_mb: float = 0.0
    error_message: str = ""
    extra_info: Dict = field(default_factory=dict)


class BenchmarkFramework:
    """
    性能基准测试框架

    功能：
    - 定义测试场景
    - 运行多个求解器
    - 收集性能数据
    - 生成对比报告
    """

    def __init__(self, output_dir: str = "benchmark_results"):
        """
        初始化框架

        Args:
            output_dir: 结果输出目录
        """
        self.output_dir = output_dir
        self.scenarios: List[BenchmarkScenario] = []
        self.results: List[BenchmarkResult] = []

        # 创建输出目录
        os.makedirs(output_dir, exist_ok=True)

    def add_scenario(self, scenario: BenchmarkScenario):
        """添加测试场景"""
        self.scenarios.append(scenario)

    def run_solver(self,
                   scenario: BenchmarkScenario,
                   solver_name: str,
                   solver_func: Callable,
                   verbose: bool = False) -> BenchmarkResult:
        """
        运行单个求解器

        Args:
            scenario: 测试场景
            solver_name: 求解器名称
            solver_func: 求解函数 (system, U_init) -> (U_sol, info)
            verbose: 是否输出详细信息

        Returns:
            BenchmarkResult: 测试结果
        """
        if verbose:
            print(f"  运行 {solver_name}...", end=" ", flush=True)

        try:
            # 创建系统
            system = SteadySaintVenantSystem(
                scenario.length, scenario.nx, scenario.B, scenario.S0, scenario.n,
                structures=scenario.structures,
                pseudo_dt=0.1
            )

            h_uniform = compute_steady_uniform_flow(scenario.Q_target, scenario.B, scenario.S0, scenario.n)

            system.set_boundary_conditions(
                Q_upstream=scenario.Q_target,
                h_upstream=h_uniform,
                h_downstream=h_uniform
            )

            # 初值（均匀流）
            h_init = np.ones(scenario.nx) * h_uniform
            Q_init = np.ones(scenario.nx) * scenario.Q_target
            U_init = system.pack_state(h_init, Q_init)
            system.U_prev = U_init.copy()

            # 运行求解器
            start_time = time.time()
            U_sol, info = solver_func(system, U_init)
            elapsed_time = time.time() - start_time

            # 解析结果
            h_sol, Q_sol = system.unpack_state(U_sol)

            # 计算误差
            Q_avg = np.mean(Q_sol)
            Q_error = abs(Q_avg - scenario.Q_target) / scenario.Q_target * 100

            # 最终残差
            system.U_prev = U_sol.copy()
            F_final = system.compute_residual(U_sol, 0.0)
            final_residual = np.linalg.norm(F_final)

            result = BenchmarkResult(
                scenario_name=scenario.name,
                solver_name=solver_name,
                converged=info.get('converged', False),
                iterations=info.get('iterations', info.get('total_iterations', 0)),
                time=elapsed_time,
                final_residual=final_residual,
                Q_error=Q_error,
                h_min=h_sol.min(),
                h_max=h_sol.max(),
                Q_min=Q_sol.min(),
                Q_max=Q_sol.max(),
                extra_info=info
            )

            if verbose:
                status = "✅" if result.converged else "❌"
                print(f"{status} {result.iterations}iter, {result.time:.4f}s")

        except Exception as e:
            result = BenchmarkResult(
                scenario_name=scenario.name,
                solver_name=solver_name,
                converged=False,
                iterations=0,
                time=0.0,
                final_residual=float('inf'),
                Q_error=float('inf'),
                h_min=0.0,
                h_max=0.0,
                Q_min=0.0,
                Q_max=0.0,
                error_message=str(e)
            )

            if verbose:
                print(f"❌ 失败: {e}")

        return result

    def run_all_benchmarks(self, solvers: Dict[str, Callable], verbose: bool = True):
        """
        运行所有基准测试

        Args:
            solvers: 求解器字典 {name: solver_func}
            verbose: 是否输出详细信息
        """
        if verbose:
            print("=" * 100)
            print("开始基准测试")
            print("=" * 100)
            print(f"场景数: {len(self.scenarios)}")
            print(f"求解器数: {len(solvers)}")
            print(f"总测试数: {len(self.scenarios) * len(solvers)}")
            print()

        for i, scenario in enumerate(self.scenarios, 1):
            if verbose:
                print(f"\n场景 {i}/{len(self.scenarios)}: {scenario.name}")
                print(f"  {scenario.description}")
                print("-" * 100)

            for solver_name, solver_func in solvers.items():
                result = self.run_solver(scenario, solver_name, solver_func, verbose)
                self.results.append(result)

        if verbose:
            print()
            print("=" * 100)
            print("基准测试完成")
            print("=" * 100)

    def get_results_by_scenario(self, scenario_name: str) -> List[BenchmarkResult]:
        """获取特定场景的所有结果"""
        return [r for r in self.results if r.scenario_name == scenario_name]

    def get_results_by_solver(self, solver_name: str) -> List[BenchmarkResult]:
        """获取特定求解器的所有结果"""
        return [r for r in self.results if r.solver_name == solver_name]

    def print_summary_table(self):
        """打印汇总表格"""
        print()
        print("=" * 120)
        print("性能汇总表")
        print("=" * 120)
        print(f"{'场景':<20} {'求解器':<15} {'收敛':<8} {'迭代':<10} {'时间(s)':<12} {'流量误差(%)':<15} {'最终残差':<15}")
        print("-" * 120)

        for scenario in self.scenarios:
            results = self.get_results_by_scenario(scenario.name)
            for result in results:
                conv_status = '✅' if result.converged else '❌'
                iter_str = str(result.iterations) if result.converged else 'N/A'
                time_str = f"{result.time:.4f}" if result.converged else 'N/A'
                error_str = f"{result.Q_error:.4f}" if result.converged and result.Q_error != float('inf') else 'N/A'
                residual_str = f"{result.final_residual:.2e}" if result.converged else 'N/A'

                print(f"{scenario.name:<20} {result.solver_name:<15} {conv_status:<8} {iter_str:<10} {time_str:<12} {error_str:<15} {residual_str:<15}")

            print()

    def compute_speedup(self, baseline_solver: str, target_solver: str) -> Dict[str, float]:
        """
        计算加速比

        Args:
            baseline_solver: 基线求解器名称
            target_solver: 目标求解器名称

        Returns:
            Dict: {scenario_name: speedup}
        """
        speedups = {}

        for scenario in self.scenarios:
            baseline_results = [r for r in self.results
                              if r.scenario_name == scenario.name and r.solver_name == baseline_solver]
            target_results = [r for r in self.results
                            if r.scenario_name == scenario.name and r.solver_name == target_solver]

            if baseline_results and target_results:
                baseline = baseline_results[0]
                target = target_results[0]

                if baseline.converged and target.converged and target.time > 0:
                    speedup = baseline.time / target.time
                    speedups[scenario.name] = speedup

        return speedups


def create_standard_scenarios() -> List[BenchmarkScenario]:
    """创建标准测试场景集"""
    from solvers.gate import SluiceGate, BroadCrestedWeir, Orifice

    scenarios = []

    # 场景1: 无结构（基准）
    scenarios.append(BenchmarkScenario(
        name="无结构",
        length=1000.0,
        nx=51,
        B=10.0,
        S0=0.001,
        n=0.025,
        Q_target=10.0,
        structures=[],
        description="基准场景 - 无水工建筑物"
    ))

    # 场景2: 单闸门
    gate = SluiceGate(position=500.0, width=10.0, opening=5.0, Cd=0.6)
    scenarios.append(BenchmarkScenario(
        name="单闸门",
        length=1000.0,
        nx=51,
        B=10.0,
        S0=0.001,
        n=0.025,
        Q_target=10.0,
        structures=[(500.0, gate)],
        description="单个平板闸门"
    ))

    # 场景3: 三闸门（小网格）
    gate1 = SluiceGate(position=250.0, width=10.0, opening=4.5, Cd=0.6)
    gate2 = SluiceGate(position=500.0, width=10.0, opening=4.0, Cd=0.6)
    gate3 = SluiceGate(position=750.0, width=10.0, opening=5.0, Cd=0.6)
    scenarios.append(BenchmarkScenario(
        name="三闸门-小",
        length=1000.0,
        nx=51,
        B=10.0,
        S0=0.001,
        n=0.025,
        Q_target=10.0,
        structures=[(250.0, gate1), (500.0, gate2), (750.0, gate3)],
        description="三个闸门 - 小网格(51点)"
    ))

    # 场景4: 三闸门（中等网格）
    gate1 = SluiceGate(position=2500.0, width=10.0, opening=4.5, Cd=0.6)
    gate2 = SluiceGate(position=5000.0, width=10.0, opening=4.0, Cd=0.6)
    gate3 = SluiceGate(position=7500.0, width=10.0, opening=5.0, Cd=0.6)
    scenarios.append(BenchmarkScenario(
        name="三闸门-中",
        length=10000.0,
        nx=201,
        B=10.0,
        S0=0.0005,
        n=0.025,
        Q_target=10.0,
        structures=[(2500.0, gate1), (5000.0, gate2), (7500.0, gate3)],
        description="三个闸门 - 中等网格(201点)"
    ))

    # 场景5: 三闸门（大网格）
    scenarios.append(BenchmarkScenario(
        name="三闸门-大",
        length=10000.0,
        nx=501,
        B=10.0,
        S0=0.0005,
        n=0.025,
        Q_target=10.0,
        structures=[(2500.0, gate1), (5000.0, gate2), (7500.0, gate3)],
        description="三个闸门 - 大网格(501点)"
    ))

    # 场景6: 混合结构
    gate = SluiceGate(position=2500.0, width=10.0, opening=3.5, Cd=0.6)
    weir = BroadCrestedWeir(position=5000.0, width=10.0, crest_height=0.5, Cd=0.5)
    orifice = Orifice(position=7500.0, width=4.0, height=2.0, bottom_elevation=0.2, Cd=0.6)
    scenarios.append(BenchmarkScenario(
        name="混合结构",
        length=10000.0,
        nx=201,
        B=10.0,
        S0=0.0005,
        n=0.025,
        Q_target=10.0,
        structures=[(2500.0, gate), (5000.0, weir), (7500.0, orifice)],
        description="闸门+堰+孔口混合"
    ))

    return scenarios


def main():
    """简单测试"""
    print("=" * 100)
    print("基准测试框架演示")
    print("=" * 100)
    print()

    # 创建框架
    framework = BenchmarkFramework(output_dir="benchmark_results")

    # 添加标准场景
    scenarios = create_standard_scenarios()
    for scenario in scenarios[:3]:  # 只测试前3个场景作为演示
        framework.add_scenario(scenario)

    # 定义求解器
    def newton_solver(system, U_init):
        """纯Newton求解器"""
        system.U_prev = U_init.copy()
        newton = NewtonSolver(max_iter=30, tol_residual=1e-4, verbose=False)
        return newton.solve(
            U_init=U_init,
            residual_func=lambda U: system.compute_residual(U, 0.0),
            jacobian_func=lambda U: system.compute_jacobian(U, 0.0)
        )

    def continuation_solver_func(system, U_init):
        """延拓求解器"""
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

    # 打印汇总
    framework.print_summary_table()


if __name__ == '__main__':
    main()
