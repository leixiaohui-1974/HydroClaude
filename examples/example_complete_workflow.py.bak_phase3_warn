#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
完整工作流程示例

演示如何使用HydroClaude的所有功能：
1. 求解稳态流动问题
2. 可视化结果
3. 性能基准测试
4. 参数敏感性分析

作者: Claude
日期: 2025-10-22
"""

import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import numpy as np
from physics.steady_saint_venant import SteadySaintVenantSystem
from solvers.newton_solver import NewtonSolver
from solvers.continuation_solver import ContinuationSolver
from solvers.gate import SluiceGate
from utils.canal_utils import compute_steady_uniform_flow
from utils.solution_visualizer import SolutionVisualizer
from utils.sensitivity_analyzer import SensitivityAnalyzer
from utils.benchmark_framework import BenchmarkFramework, BenchmarkScenario
from utils.benchmark_visualizer import BenchmarkVisualizer
from utils.benchmark_reporter import BenchmarkReporter


def demo_basic_solving():
    """演示1: 基本求解"""
    print("\n" + "=" * 100)
    print("演示1: 基本求解 - 三闸门场景")
    print("=" * 100)
    print()

    # 场景配置
    length = 1000.0
    nx = 101
    B = 10.0
    S0 = 0.001
    n = 0.025
    Q_target = 10.0

    # 创建三个闸门
    gate1 = SluiceGate(position=250.0, width=B, opening=4.5, Cd=0.6)
    gate2 = SluiceGate(position=500.0, width=B, opening=4.0, Cd=0.6)
    gate3 = SluiceGate(position=750.0, width=B, opening=5.0, Cd=0.6)

    print("场景配置:")
    print(f"  渠道长度: {length} m")
    print(f"  网格点数: {nx}")
    print(f"  目标流量: {Q_target} m^3/s")
    print(f"  闸门数量: 3个")
    print()

    # 创建系统
    system = SteadySaintVenantSystem(
        length, nx, B, S0, n,
        structures=[
            (gate1.position, gate1),
            (gate2.position, gate2),
            (gate3.position, gate3)
        ],
        pseudo_dt=0.1
    )

    h_uniform = compute_steady_uniform_flow(Q_target, B, S0, n)
    system.set_boundary_conditions(
        Q_upstream=Q_target,
        h_upstream=h_uniform,
        h_downstream=h_uniform
    )

    # 初值
    h_init = np.ones(nx) * h_uniform
    Q_init = np.ones(nx) * Q_target
    U_init = system.pack_state(h_init, Q_init)
    system.U_prev = U_init.copy()

    # 求解（Newton方法）
    print("使用Newton方法求解...")
    newton = NewtonSolver(max_iter=30, tol_residual=1e-4, verbose=True)
    U_sol, info = newton.solve(
        U_init=U_init,
        residual_func=lambda U: system.compute_residual(U, 0.0),
        jacobian_func=lambda U: system.compute_jacobian(U, 0.0)
    )

    h_sol, Q_sol = system.unpack_state(U_sol)

    print()
    print("求解结果:")
    print(f"  收敛状态: {' 成功' if info['converged'] else ' 失败'}")
    print(f"  迭代次数: {info['iterations']}")
    print(f"  水深范围: {h_sol.min():.4f} - {h_sol.max():.4f} m")
    print(f"  流量范围: {Q_sol.min():.4f} - {Q_sol.max():.4f} m^3/s")
    print()

    return system, h_sol, Q_sol


def demo_visualization(system, h_sol, Q_sol):
    """演示2: 结果可视化"""
    print("\n" + "=" * 100)
    print("演示2: 结果可视化")
    print("=" * 100)
    print()

    visualizer = SolutionVisualizer(output_dir="demo_results/visualization")
    plots = visualizer.generate_complete_report(system, h_sol, Q_sol,
                                                scenario_name="Three Gates Demo")

    print("\n生成的可视化图表:")
    for name, path in plots.items():
        print(f"  {name}: {path}")

    return plots


def demo_benchmark():
    """演示3: 性能基准测试"""
    print("\n" + "=" * 100)
    print("演示3: 性能基准测试 - Newton vs Continuation")
    print("=" * 100)
    print()

    # 创建测试框架
    framework = BenchmarkFramework(output_dir="demo_results/benchmark")

    # 添加测试场景（简化版，快速演示）
    from solvers.gate import SluiceGate

    gate = SluiceGate(position=500.0, width=10.0, opening=5.0, Cd=0.6)
    scenario = BenchmarkScenario(
        name="Single Gate",
        length=1000.0,
        nx=51,
        B=10.0,
        S0=0.001,
        n=0.025,
        Q_target=10.0,
        structures=[(500.0, gate)],
        description="Single gate benchmark"
    )
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

    # 生成报告
    reporter = BenchmarkReporter(framework, plots)
    md_report = reporter.generate_markdown_report(filename="demo_benchmark.md")
    html_report = reporter.generate_html_report(filename="demo_benchmark.html")

    print("\n基准测试报告:")
    print(f"  Markdown: {md_report}")
    print(f"  HTML: {html_report}")


def demo_sensitivity():
    """演示4: 参数敏感性分析"""
    print("\n" + "=" * 100)
    print("演示4: 参数敏感性分析 - 闸门开度影响")
    print("=" * 100)
    print()

    # 基础配置
    length = 1000.0
    nx = 51
    B = 10.0
    S0 = 0.001
    n = 0.025
    Q_target = 10.0

    # 创建分析器
    analyzer = SensitivityAnalyzer(output_dir="demo_results/sensitivity")

    # 定义系统创建函数
    def create_system(gate_opening):
        gate = SluiceGate(position=500.0, width=B, opening=gate_opening, Cd=0.6)
        system = SteadySaintVenantSystem(
            length, nx, B, S0, n,
            structures=[(500.0, gate)],
            pseudo_dt=0.1
        )
        h_uniform = compute_steady_uniform_flow(Q_target, B, S0, n)
        system.set_boundary_conditions(
            Q_upstream=Q_target,
            h_upstream=h_uniform,
            h_downstream=h_uniform
        )
        h_init = np.ones(nx) * h_uniform
        Q_init = np.ones(nx) * Q_target
        U_init = system.pack_state(h_init, Q_init)
        system.U_prev = U_init.copy()
        return system, U_init

    # 定义求解函数
    def solve_system(system, U_init):
        newton = NewtonSolver(max_iter=30, tol_residual=1e-4, verbose=False)
        U_sol, info = newton.solve(
            U_init=U_init,
            residual_func=lambda U: system.compute_residual(U, 0.0),
            jacobian_func=lambda U: system.compute_jacobian(U, 0.0)
        )
        h, Q = system.unpack_state(U_sol)
        return h, Q, info

    # 分析闸门开度
    gate_openings = np.linspace(3.0, 7.0, 9)
    result = analyzer.analyze_parameter(
        base_system_func=create_system,
        solver_func=solve_system,
        parameter_name="Gate Opening (m)",
        parameter_values=gate_openings.tolist(),
        output_metric=lambda h, Q: np.max(h),  # 最大水深
        baseline_value=5.0,
        verbose=True
    )

    # 计算敏感性指数
    sensitivity_index = analyzer.compute_sensitivity_index(result)

    print(f"\n敏感性指数: {sensitivity_index:.6f}")
    print("  (负值表示开度增大时水深减小)")

    # 绘制
    plot_path = analyzer.plot_sensitivity(result, output_name="Max Water Depth (m)")
    print(f"\n敏感性曲线: {plot_path}")


def main():
    """主函数 - 运行完整工作流程"""
    print("=" * 100)
    print("HydroClaude 完整工作流程演示")
    print("=" * 100)
    print()
    print("本示例将演示:")
    print("  1. 基本求解（Newton方法）")
    print("  2. 结果可视化（水深、流速、能量线等）")
    print("  3. 性能基准测试（求解器对比）")
    print("  4. 参数敏感性分析（闸门开度影响）")
    print()# input() disabled for automated testing

    # 演示1: 基本求解
    system, h_sol, Q_sol = demo_basic_solving()# input() disabled for automated testing

    # 演示2: 可视化
    demo_visualization(system, h_sol, Q_sol)# input() disabled for automated testing

    # 演示3: 基准测试
    demo_benchmark()# input() disabled for automated testing

    # 演示4: 敏感性分析
    demo_sensitivity()

    print("\n" + "=" * 100)
    print("完整工作流程演示完成！")
    print("=" * 100)
    print()
    print("所有结果已保存到 demo_results/ 目录")
    print()


if __name__ == '__main__':
    main()
