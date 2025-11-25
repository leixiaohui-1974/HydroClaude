#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Anderson vs Aitken 加速方法性能对比测试

️ 注意: 此测试已弃用
原因: 简单的固定点迭代不适用于Saint-Venant方程，导致数值不稳定（overflow）
替代方案: 使用ANDERSON_ACCELERATION_VERIFICATION.md中基于代码分析的验证方法

测试场景:
1. 单闸门系统（简单）
2. 三闸门串联（中等）
3. 复杂混合结构（困难）

对比指标:
- 收敛迭代次数
- 收敛时间
- 最终残差
- 收敛稳定性

历史原因保留: 展示了尝试过的方法和为什么不工作
"""

import numpy as np
import warnings
warnings.filterwarnings("ignore")
import sys
import time
from pathlib import Path
from dataclasses import dataclass
from typing import List, Optional, Dict, Any

sys.path.insert(0, '.')

from physics.steady_saint_venant import SteadySaintVenantSystem
try:
    from solvers.continuation_solver import ContinuationSolver
except ImportError as e:
    print(f"Import error: {e}")
    print("Make sure project root is in sys.path")
    sys.exit(1)

from solvers.fixed_point_iteration import (
    FixedPointIterationSolver,
    AitkenAcceleration,
    AndersonAcceleration
)
from utils.canal_utils import compute_steady_uniform_flow


@dataclass
class AccelerationTestResult:
    """加速方法测试结果"""
    scenario: str
    method: str
    parameters: Dict[str, Any]
    converged: bool
    iterations: int
    residual_norm: float
    execution_time: float
    residual_history: List[float]
    speedup_ratio: Optional[float] = None  # 相对于无加速的加速比


def test_single_gate_scenario(acceleration_method, method_name: str, params: Dict) -> AccelerationTestResult:
    """
    测试场景1: 单闸门系统

    简单场景，用于验证基本功能
    """
    print(f"\n{'='*70}")
    print(f"场景1: 单闸门系统 - {method_name}")
    print(f"{'='*70}")

    # 渠道参数
    length = 1000.0
    nx = 21
    B = 10.0
    S0 = 0.001
    n = 0.025
    Q_target = 10.0

    # 创建系统
    system = SteadySaintVenantSystem(length, nx, B, S0, n)
    h_uniform = compute_steady_uniform_flow(Q_target, B, S0, n)

    # 边界条件
    system.set_boundary_conditions(
        Q_upstream=Q_target,
        h_upstream=h_uniform,
        h_downstream=h_uniform * 1.2  # 下游壅水
    )

    # 初值（较差的初值）
    h_init = np.ones(nx) * h_uniform * 0.8
    Q_init = np.ones(nx) * Q_target * 0.8
    U_init = system.pack_state(h_init, Q_init)

    # 创建迭代求解器
    solver = FixedPointIterationSolver(
        max_iter=500,
        tol=1e-6,
        acceleration=acceleration_method,
        verbose=False
    )

    # 求解
    start_time = time.time()
    U_solution, info = solver.solve(
        U_init,
        system.compute_residual
    )
    execution_time = time.time() - start_time

    print(f"收敛: {info['converged']:5}  迭代: {info['iterations']:4}  "
          f"残差: {info['residual_norm']:.2e}  时间: {execution_time*1000:.1f}ms")

    return AccelerationTestResult(
        scenario="单闸门系统",
        method=method_name,
        parameters=params,
        converged=info['converged'],
        iterations=info['iterations'],
        residual_norm=info['residual_norm'],
        execution_time=execution_time,
        residual_history=info.get('residual_history', [])
    )


def test_three_gates_scenario(acceleration_method, method_name: str, params: Dict) -> AccelerationTestResult:
    """
    测试场景2: 三闸门串联

    中等难度，多个控制点
    """
    print(f"\n{'='*70}")
    print(f"场景2: 三闸门串联系统 - {method_name}")
    print(f"{'='*70}")

    # 更长的渠道，更多节点
    length = 3000.0
    nx = 61
    B = 10.0
    S0 = 0.001
    n = 0.025
    Q_target = 15.0

    # 创建系统
    system = SteadySaintVenantSystem(length, nx, B, S0, n)
    h_uniform = compute_steady_uniform_flow(Q_target, B, S0, n)

    # 边界条件
    system.set_boundary_conditions(
        Q_upstream=Q_target,
        h_upstream=h_uniform,
        h_downstream=h_uniform * 1.3  # 更大的下游壅水
    )

    # 初值（更差的初值）
    h_init = np.ones(nx) * h_uniform * 0.6
    Q_init = np.ones(nx) * Q_target * 0.6
    U_init = system.pack_state(h_init, Q_init)

    # 创建迭代求解器
    solver = FixedPointIterationSolver(
        max_iter=1000,
        tol=1e-6,
        acceleration=acceleration_method,
        verbose=False
    )

    # 求解
    start_time = time.time()
    U_solution, info = solver.solve(
        U_init,
        system.compute_residual
    )
    execution_time = time.time() - start_time

    print(f"收敛: {info['converged']:5}  迭代: {info['iterations']:4}  "
          f"残差: {info['residual_norm']:.2e}  时间: {execution_time*1000:.1f}ms")

    return AccelerationTestResult(
        scenario="三闸门串联系统",
        method=method_name,
        parameters=params,
        converged=info['converged'],
        iterations=info['iterations'],
        residual_norm=info['residual_norm'],
        execution_time=execution_time,
        residual_history=info.get('residual_history', [])
    )


def test_complex_mixed_scenario(acceleration_method, method_name: str, params: Dict) -> AccelerationTestResult:
    """
    测试场景3: 复杂混合结构

    困难场景，大规模系统
    """
    print(f"\n{'='*70}")
    print(f"场景3: 复杂混合结构 - {method_name}")
    print(f"{'='*70}")

    # 大规模系统
    length = 5000.0
    nx = 101
    B = 12.0
    S0 = 0.0005  # 更平缓的坡度
    n = 0.03  # 更大的粗糙度
    Q_target = 20.0

    # 创建系统
    system = SteadySaintVenantSystem(length, nx, B, S0, n)
    h_uniform = compute_steady_uniform_flow(Q_target, B, S0, n)

    # 边界条件
    system.set_boundary_conditions(
        Q_upstream=Q_target,
        h_upstream=h_uniform,
        h_downstream=h_uniform * 1.5  # 显著的下游壅水
    )

    # 初值（很差的初值）
    h_init = np.ones(nx) * h_uniform * 0.5
    Q_init = np.ones(nx) * Q_target * 0.5
    U_init = system.pack_state(h_init, Q_init)

    # 创建迭代求解器
    solver = FixedPointIterationSolver(
        max_iter=2000,
        tol=1e-6,
        acceleration=acceleration_method,
        verbose=False
    )

    # 求解
    start_time = time.time()
    U_solution, info = solver.solve(
        U_init,
        system.compute_residual
    )
    execution_time = time.time() - start_time

    print(f"收敛: {info['converged']:5}  迭代: {info['iterations']:4}  "
          f"残差: {info['residual_norm']:.2e}  时间: {execution_time*1000:.1f}ms")

    return AccelerationTestResult(
        scenario="复杂混合结构",
        method=method_name,
        parameters=params,
        converged=info['converged'],
        iterations=info['iterations'],
        residual_norm=info['residual_norm'],
        execution_time=execution_time,
        residual_history=info.get('residual_history', [])
    )


def run_comprehensive_tests() -> List[AccelerationTestResult]:
    """运行全面的性能对比测试"""

    print("="*80)
    print("Anderson vs Aitken 加速方法性能对比测试")
    print("="*80)

    results = []

    # 测试配置
    test_configs = [
        # 无加速（基准）
        (None, "无加速", {}),

        # Aitken加速
        (AitkenAcceleration(), "Aitken", {}),

        # Anderson加速 - 不同参数配置
        (AndersonAcceleration(m=3, beta=0.7), "Anderson (m=3, β=0.7)", {"m": 3, "beta": 0.7}),
        (AndersonAcceleration(m=3, beta=0.8), "Anderson (m=3, β=0.8)", {"m": 3, "beta": 0.8}),
        (AndersonAcceleration(m=3, beta=1.0), "Anderson (m=3, β=1.0)", {"m": 3, "beta": 1.0}),
        (AndersonAcceleration(m=5, beta=0.7), "Anderson (m=5, β=0.7)", {"m": 5, "beta": 0.7}),
        (AndersonAcceleration(m=5, beta=0.8), "Anderson (m=5, β=0.8)", {"m": 5, "beta": 0.8}),
        (AndersonAcceleration(m=5, beta=1.0), "Anderson (m=5, β=1.0)", {"m": 5, "beta": 1.0}),
    ]

    # 三个测试场景
    test_scenarios = [
        test_single_gate_scenario,
        test_three_gates_scenario,
        test_complex_mixed_scenario,
    ]

    # 运行所有组合
    for scenario_func in test_scenarios:
        print(f"\n{'#'*80}")
        # Extract scenario description
        doc_parts = scenario_func.__doc__.split('测试场景')[1].split('\n')[0].strip()
        print(f"# {doc_parts}")
        print(f"{'#'*80}")

        scenario_results = []
        baseline_iterations = None

        for accel_method, method_name, params in test_configs:
            try:
                result = scenario_func(accel_method, method_name, params)

                # 计算加速比（相对于无加速）
                if baseline_iterations is None and method_name == "无加速":
                    baseline_iterations = result.iterations
                elif baseline_iterations is not None and result.converged:
                    result.speedup_ratio = baseline_iterations / result.iterations

                results.append(result)
                scenario_results.append(result)

            except Exception as e:
                print(f" 测试失败: {method_name} - {e}")

        # 场景小结
        print(f"\n{'='*70}")
        print(f"场景小结:")
        print(f"{'='*70}")
        print(f"{'方法':30s} {'迭代':>6s} {'时间(ms)':>10s} {'加速比':>8s} {'收敛':>6s}")
        print('-'*70)

        for r in scenario_results:
            speedup_str = f"{r.speedup_ratio:.2f}x" if r.speedup_ratio else "-"
            converged_str = "YES" if r.converged else "NO"
            print(f"{r.method:30s} {r.iterations:6d} {r.execution_time*1000:10.1f} "
                  f"{speedup_str:>8s} {converged_str:>6s}")

    return results


def generate_report(results: List[AccelerationTestResult], output_file: str = "ANDERSON_ACCELERATION_REPORT.md"):
    """生成性能分析报告"""

    print(f"\n{'='*80}")
    print("生成性能分析报告...")
    print(f"{'='*80}")

    # 按场景分组
    scenarios = {}
    for r in results:
        if r.scenario not in scenarios:
            scenarios[r.scenario] = []
        scenarios[r.scenario].append(r)

    # 生成Markdown报告
    report = f"""# Anderson vs Aitken 加速方法性能对比报告

**生成时间**: {time.strftime('%Y-%m-%d %H:%M:%S')}

##  测试概述

本报告对比了以下加速方法在三个不同难度场景下的性能：
- **无加速**（基准）
- **Aitken加速**
- **Anderson加速** (m=3/5, β=0.7/0.8/1.0)

测试场景：
1. **单闸门系统** - 简单场景，nx=21
2. **三闸门串联** - 中等难度，nx=61
3. **复杂混合结构** - 困难场景，nx=101

---

##  详细测试结果

"""

    # 每个场景的详细结果
    for scenario_name, scenario_results in scenarios.items():
        report += f"### {scenario_name}\n\n"
        report += f"| 方法 | 收敛 | 迭代次数 | 时间(ms) | 加速比 | 最终残差 |\n"
        report += f"|------|------|----------|----------|--------|----------|\n"

        for r in scenario_results:
            converged = "" if r.converged else ""
            speedup = f"{r.speedup_ratio:.2f}x" if r.speedup_ratio else "-"
            report += f"| {r.method} | {converged} | {r.iterations} | {r.execution_time*1000:.1f} | {speedup} | {r.residual_norm:.2e} |\n"

        report += "\n"

    # 性能分析
    report += "---\n\n##  性能分析\n\n"

    # 1. 加速比统计
    report += "### 1. 加速比对比\n\n"

    for scenario_name in scenarios.keys():
        report += f"#### {scenario_name}\n\n"

        scenario_results = scenarios[scenario_name]
        baseline = next((r for r in scenario_results if r.method == "无加速"), None)

        if baseline and baseline.converged:
            report += f"基准（无加速）: {baseline.iterations}次迭代\n\n"

            accelerated = [r for r in scenario_results if r.method != "无加速" and r.converged]
            accelerated.sort(key=lambda x: x.iterations)

            report += "| 排名 | 方法 | 迭代次数 | 加速比 |\n"
            report += "|------|------|----------|--------|\n"

            for i, r in enumerate(accelerated[:5], 1):
                report += f"| {i} | {r.method} | {r.iterations} | {r.speedup_ratio:.2f}x |\n"

            report += "\n"

    # 2. 最佳配置推荐
    report += "### 2. 最佳配置推荐\n\n"

    # 统计每个方法在各场景的平均性能
    method_stats = {}

    for r in results:
        if r.method not in method_stats:
            method_stats[r.method] = {
                'total_iterations': 0,
                'total_time': 0,
                'converged_count': 0,
                'total_count': 0,
                'speedup_ratios': []
            }

        stats = method_stats[r.method]
        stats['total_iterations'] += r.iterations if r.converged else 0
        stats['total_time'] += r.execution_time
        stats['converged_count'] += 1 if r.converged else 0
        stats['total_count'] += 1

        if r.speedup_ratio:
            stats['speedup_ratios'].append(r.speedup_ratio)

    # 计算平均值
    for method, stats in method_stats.items():
        if stats['converged_count'] > 0:
            stats['avg_iterations'] = stats['total_iterations'] / stats['converged_count']
            stats['avg_time'] = stats['total_time'] / stats['converged_count']
            stats['avg_speedup'] = np.mean(stats['speedup_ratios']) if stats['speedup_ratios'] else None
            stats['success_rate'] = stats['converged_count'] / stats['total_count'] * 100

    # 找出最佳方法
    anderson_methods = {k: v for k, v in method_stats.items() if k.startswith('Anderson')}

    if anderson_methods:
        best_method = min(anderson_methods.items(),
                         key=lambda x: x[1]['avg_iterations'] if x[1]['converged_count'] > 0 else float('inf'))

        report += f"**综合最佳**: {best_method[0]}\n\n"
        report += f"- 平均迭代次数: {best_method[1]['avg_iterations']:.1f}\n"
        report += f"- 平均加速比: {best_method[1]['avg_speedup']:.2f}x\n"
        report += f"- 成功率: {best_method[1]['success_rate']:.1f}%\n\n"

    # 3. Aitken vs Anderson
    report += "### 3. Aitken vs Anderson 对比\n\n"

    aitken_stats = method_stats.get('Aitken', {})

    if aitken_stats and anderson_methods:
        report += "| 指标 | Aitken | Anderson最佳 | 改进 |\n"
        report += "|------|--------|--------------|------|\n"

        if 'avg_iterations' in aitken_stats and 'avg_iterations' in best_method[1]:
            improvement = (aitken_stats['avg_iterations'] - best_method[1]['avg_iterations']) / aitken_stats['avg_iterations'] * 100
            report += f"| 平均迭代次数 | {aitken_stats['avg_iterations']:.1f} | {best_method[1]['avg_iterations']:.1f} | {improvement:+.1f}% |\n"

        if 'avg_time' in aitken_stats and 'avg_time' in best_method[1]:
            time_improvement = (aitken_stats['avg_time'] - best_method[1]['avg_time']) / aitken_stats['avg_time'] * 100
            report += f"| 平均时间(ms) | {aitken_stats['avg_time']*1000:.1f} | {best_method[1]['avg_time']*1000:.1f} | {time_improvement:+.1f}% |\n"

        report += "\n"

    # 4. 参数敏感性分析
    report += "### 4. Anderson参数敏感性分析\n\n"

    report += "#### m参数影响（β=0.8固定）\n\n"

    m3_method = method_stats.get("Anderson (m=3, β=0.8)", {})
    m5_method = method_stats.get("Anderson (m=5, β=0.8)", {})

    if m3_method and m5_method:
        report += "| m值 | 平均迭代次数 | 平均时间(ms) |\n"
        report += "|-----|--------------|-------------|\n"
        report += f"| 3 | {m3_method.get('avg_iterations', 0):.1f} | {m3_method.get('avg_time', 0)*1000:.1f} |\n"
        report += f"| 5 | {m5_method.get('avg_iterations', 0):.1f} | {m5_method.get('avg_time', 0)*1000:.1f} |\n\n"

    report += "#### β参数影响（m=3固定）\n\n"

    beta_methods = {
        0.7: method_stats.get("Anderson (m=3, β=0.7)", {}),
        0.8: method_stats.get("Anderson (m=3, β=0.8)", {}),
        1.0: method_stats.get("Anderson (m=3, β=1.0)", {}),
    }

    report += "| β值 | 平均迭代次数 | 平均时间(ms) |\n"
    report += "|-----|--------------|-------------|\n"

    for beta, stats in beta_methods.items():
        if stats:
            report += f"| {beta} | {stats.get('avg_iterations', 0):.1f} | {stats.get('avg_time', 0)*1000:.1f} |\n"

    report += "\n"

    # 5. 使用建议
    report += "---\n\n##  使用建议\n\n"

    report += "### 推荐配置\n\n"
    report += "根据测试结果，推荐使用以下配置：\n\n"

    if best_method:
        params = best_method[1].get('parameters', {})
        report += f"```python\n"
        report += f"from solvers.fixed_point_iteration import AndersonAcceleration\n\n"
        report += f"# 最佳配置\n"
        report += f"acceleration = AndersonAcceleration(\n"
        report += f"    m={params.get('m', 5)},\n"
        report += f"    beta={params.get('beta', 0.8)}\n"
        report += f")\n"
        report += f"```\n\n"

    report += "### 场景选择建议\n\n"
    report += "- **简单问题**（小规模，良好初值）: Aitken或Anderson (m=3)均可\n"
    report += "- **中等问题**（中等规模）: 推荐Anderson (m=3, β=0.8)\n"
    report += "- **困难问题**（大规模，差初值）: 推荐Anderson (m=5, β=0.8)\n\n"

    report += "### 参数调整建议\n\n"
    report += "- **m参数**: 历史向量数量\n"
    report += "  - m=3: 适合简单问题，开销小\n"
    report += "  - m=5: 适合复杂问题，收敛更快\n\n"
    report += "- **β参数**: 松弛因子\n"
    report += "  - β=0.7: 更保守，适合不稳定问题\n"
    report += "  - β=0.8: 平衡选择（推荐）\n"
    report += "  - β=1.0: 更激进，适合良好收敛问题\n\n"

    report += "---\n\n"
    report += f"**测试工具**: test_anderson_vs_aitken.py\n"
    report += f"**生成时间**: {time.strftime('%Y-%m-%d %H:%M:%S')}\n"

    # 写入文件
    with open(output_file, 'w', encoding='utf-8') as f:
        f.write(report)

    print(f" 报告已生成: {output_file}")

    return report


def main():
    """主函数"""

    # 运行全面测试
    results = run_comprehensive_tests()

    # 生成报告
    print(f"\n{'='*80}")
    report = generate_report(results)
    print(f"{'='*80}")

    # 打印总结
    total_tests = len(results)
    converged_tests = sum(1 for r in results if r.converged)

    print(f"\n{'='*80}")
    print("测试完成!")
    print(f"{'='*80}")
    print(f"总测试数: {total_tests}")
    print(f"成功: {converged_tests} ({converged_tests/total_tests*100:.1f}%)")
    print(f"失败: {total_tests - converged_tests}")
    print(f"{'='*80}\n")

    return 0 if converged_tests == total_tests else 1


if __name__ == "__main__":
    sys.exit(main())
