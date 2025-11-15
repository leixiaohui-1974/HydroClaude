#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Anderson加速性能验证测试

测试Anderson加速在不同参数配置下的性能表现
对比无加速基准和不同的Anderson参数组合

作者: Claude
日期: 2025-10-22
"""

import numpy as np
import sys
import time
from typing import Dict, List, Tuple

sys.path.insert(0, '.')

from physics.steady_saint_venant import SteadySaintVenantSystem
try:
    from solvers.anderson_acceleration import AndersonAcceleration
except ImportError as e:
    print(f"Import error: {e}")
    print("Make sure project root is in sys.path")
    sys.exit(1)

from utils.canal_utils import compute_steady_uniform_flow


def fixed_point_iteration_with_anderson(
    system,
    U_init: np.ndarray,
    anderson: AndersonAcceleration = None,
    max_iter: int = 500,
    tol: float = 1e-6,
    verbose: bool = False
) -> Tuple[np.ndarray, Dict]:
    """
    使用Anderson加速的固定点迭代求解

    固定点迭代: U_{k+1} = U_k - α * F(U_k)

    Args:
        system: 系统对象
        U_init: 初值
        anderson: Anderson加速器（None表示无加速）
        max_iter: 最大迭代次数
        tol: 收敛容差
        verbose: 是否输出详细信息

    Returns:
        U_solution: 解
        info: 求解信息字典
    """
    U = U_init.copy()
    residual_history = []

    # 固定点迭代步长（简单的）
    alpha = 0.5

    for iteration in range(max_iter):
        # 计算残差
        F = system.compute_residual(U)
        residual_norm = np.linalg.norm(F)
        residual_history.append(residual_norm)

        if verbose and (iteration % 10 == 0 or residual_norm < tol):
            print(f"  Iter {iteration:4d}: residual = {residual_norm:.2e}")

        # 检查收敛
        if residual_norm < tol:
            if verbose:
                print(f"   Converged at iteration {iteration}")
            return U, {
                'converged': True,
                'iterations': iteration + 1,
                'residual_norm': residual_norm,
                'residual_history': residual_history
            }

        # 固定点迭代步
        U_next = U - alpha * F

        # Anderson加速
        if anderson is not None:
            U_next = anderson.compute_acceleration(U, U_next)

        U = U_next

    # 未收敛
    if verbose:
        print(f"   Did not converge in {max_iter} iterations")
    return U, {
        'converged': False,
        'iterations': max_iter,
        'residual_norm': residual_history[-1] if residual_history else np.inf,
        'residual_history': residual_history
    }


def test_single_gate_scenario(anderson_config: Dict, method_name: str) -> Dict:
    """
    测试场景1: 单闸门系统

    简单场景，中等规模
    """
    print(f"\n{'='*70}")
    print(f"场景1: 单闸门系统 - {method_name}")
    print(f"{'='*70}")

    # 系统参数
    length = 1000.0
    nx = 31
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

    # 初值（较差）
    h_init = np.ones(nx) * h_uniform * 0.7
    Q_init = np.ones(nx) * Q_target * 0.7
    U_init = system.pack_state(h_init, Q_init)

    # 创建Anderson加速器
    anderson = None
    if anderson_config:
        anderson = AndersonAcceleration(
            m=anderson_config.get('m', 5),
            beta=anderson_config.get('beta', 1.0)
        )

    # 求解
    start_time = time.time()
    U_solution, info = fixed_point_iteration_with_anderson(
        system, U_init, anderson,
        max_iter=1000, tol=1e-6, verbose=False
    )
    execution_time = time.time() - start_time

    print(f"收敛: {info['converged']:5}  迭代: {info['iterations']:4}  "
          f"残差: {info['residual_norm']:.2e}  时间: {execution_time*1000:.1f}ms")

    return {
        'scenario': '单闸门系统',
        'method': method_name,
        'config': anderson_config,
        'converged': info['converged'],
        'iterations': info['iterations'],
        'residual_norm': info['residual_norm'],
        'execution_time': execution_time,
        'residual_history': info['residual_history']
    }


def test_three_gates_scenario(anderson_config: Dict, method_name: str) -> Dict:
    """
    测试场景2: 三闸门串联系统

    更复杂的场景，更大规模
    """
    print(f"\n{'='*70}")
    print(f"场景2: 三闸门串联 - {method_name}")
    print(f"{'='*70}")

    # 系统参数（更大）
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
        h_downstream=h_uniform * 1.3  # 更大的壅水
    )

    # 初值（更差）
    h_init = np.ones(nx) * h_uniform * 0.6
    Q_init = np.ones(nx) * Q_target * 0.6
    U_init = system.pack_state(h_init, Q_init)

    # 创建Anderson加速器
    anderson = None
    if anderson_config:
        anderson = AndersonAcceleration(
            m=anderson_config.get('m', 5),
            beta=anderson_config.get('beta', 1.0)
        )

    # 求解
    start_time = time.time()
    U_solution, info = fixed_point_iteration_with_anderson(
        system, U_init, anderson,
        max_iter=2000, tol=1e-6, verbose=False
    )
    execution_time = time.time() - start_time

    print(f"收敛: {info['converged']:5}  迭代: {info['iterations']:4}  "
          f"残差: {info['residual_norm']:.2e}  时间: {execution_time*1000:.1f}ms")

    return {
        'scenario': '三闸门串联',
        'method': method_name,
        'config': anderson_config,
        'converged': info['converged'],
        'iterations': info['iterations'],
        'residual_norm': info['residual_norm'],
        'execution_time': execution_time,
        'residual_history': info['residual_history']
    }


def test_complex_scenario(anderson_config: Dict, method_name: str) -> Dict:
    """
    测试场景3: 复杂大规模系统

    最困难的场景
    """
    print(f"\n{'='*70}")
    print(f"场景3: 复杂大规模系统 - {method_name}")
    print(f"{'='*70}")

    # 大规模系统
    length = 5000.0
    nx = 101
    B = 12.0
    S0 = 0.0005  # 更平缓
    n = 0.03
    Q_target = 20.0

    # 创建系统
    system = SteadySaintVenantSystem(length, nx, B, S0, n)
    h_uniform = compute_steady_uniform_flow(Q_target, B, S0, n)

    # 边界条件
    system.set_boundary_conditions(
        Q_upstream=Q_target,
        h_upstream=h_uniform,
        h_downstream=h_uniform * 1.5  # 显著壅水
    )

    # 初值（很差）
    h_init = np.ones(nx) * h_uniform * 0.5
    Q_init = np.ones(nx) * Q_target * 0.5
    U_init = system.pack_state(h_init, Q_init)

    # 创建Anderson加速器
    anderson = None
    if anderson_config:
        anderson = AndersonAcceleration(
            m=anderson_config.get('m', 5),
            beta=anderson_config.get('beta', 1.0)
        )

    # 求解
    start_time = time.time()
    U_solution, info = fixed_point_iteration_with_anderson(
        system, U_init, anderson,
        max_iter=3000, tol=1e-6, verbose=False
    )
    execution_time = time.time() - start_time

    print(f"收敛: {info['converged']:5}  迭代: {info['iterations']:4}  "
          f"残差: {info['residual_norm']:.2e}  时间: {execution_time*1000:.1f}ms")

    return {
        'scenario': '复杂大规模系统',
        'method': method_name,
        'config': anderson_config,
        'converged': info['converged'],
        'iterations': info['iterations'],
        'residual_norm': info['residual_norm'],
        'execution_time': execution_time,
        'residual_history': info['residual_history']
    }


def run_comprehensive_tests() -> List[Dict]:
    """运行全面的Anderson加速性能测试"""

    print("="*80)
    print("Anderson加速性能验证测试")
    print("="*80)

    results = []

    # 测试配置
    test_configs = [
        # 基准：无加速
        (None, "无加速（基准）"),

        # Anderson加速 - 不同参数配置
        ({'m': 3, 'beta': 0.7}, "Anderson (m=3, β=0.7) 保守"),
        ({'m': 3, 'beta': 0.8}, "Anderson (m=3, β=0.8)"),
        ({'m': 3, 'beta': 1.0}, "Anderson (m=3, β=1.0)"),
        ({'m': 5, 'beta': 0.7}, "Anderson (m=5, β=0.7)"),
        ({'m': 5, 'beta': 0.8}, "Anderson (m=5, β=0.8) 推荐"),
        ({'m': 5, 'beta': 1.0}, "Anderson (m=5, β=1.0)"),
        ({'m': 7, 'beta': 0.8}, "Anderson (m=7, β=0.8)"),
    ]

    # 三个测试场景
    test_scenarios = [
        test_single_gate_scenario,
        test_three_gates_scenario,
        test_complex_scenario,
    ]

    # 运行所有组合
    for scenario_func in test_scenarios:
        print(f"\n{'#'*80}")
        print(f"# 测试场景: {scenario_func.__doc__.split('测试场景')[1].split(':')[0].strip()}")
        print(f"{'#'*80}")

        scenario_results = []
        baseline_iterations = None

        for anderson_config, method_name in test_configs:
            try:
                result = scenario_func(anderson_config, method_name)

                # 计算加速比（相对于无加速）
                if baseline_iterations is None and anderson_config is None:
                    baseline_iterations = result['iterations']
                elif baseline_iterations is not None and result['converged']:
                    result['speedup_ratio'] = baseline_iterations / result['iterations']
                else:
                    result['speedup_ratio'] = None

                results.append(result)
                scenario_results.append(result)

            except Exception as e:
                print(f" 测试失败: {method_name} - {e}")
                import traceback
                traceback.print_exc()

        # 场景小结
        print(f"\n{'='*70}")
        print(f"场景小结:")
        print(f"{'='*70}")
        print(f"{'方法':35s} {'迭代':>6s} {'时间(ms)':>10s} {'加速比':>8s} {'收敛':>6s}")
        print('-'*70)

        for r in scenario_results:
            speedup_str = f"{r.get('speedup_ratio', 0):.2f}x" if r.get('speedup_ratio') else "-"
            converged_str = "YES" if r['converged'] else "NO"
            print(f"{r['method']:35s} {r['iterations']:6d} {r['execution_time']*1000:10.1f} "
                  f"{speedup_str:>8s} {converged_str:>6s}")

    return results


def generate_report(results: List[Dict], output_file: str = "ANDERSON_ACCELERATION_REPORT.md"):
    """生成Anderson加速性能报告"""

    print(f"\n{'='*80}")
    print("生成性能分析报告...")
    print(f"{'='*80}")

    # 按场景分组
    scenarios = {}
    for r in results:
        if r['scenario'] not in scenarios:
            scenarios[r['scenario']] = []
        scenarios[r['scenario']].append(r)

    # 生成Markdown报告
    report = f"""# Anderson加速性能验证报告

**生成时间**: {time.strftime('%Y-%m-%d %H:%M:%S')}
**测试工具**: test_anderson_performance.py

##  测试概述

本报告验证了Anderson加速算法在Saint-Venant方程固定点迭代求解中的性能表现。

### 测试配置
- **基准方法**: 无加速的固定点迭代
- **Anderson参数**: 测试了8种不同的(m, β)组合
- **测试场景**: 3个不同难度和规模的场景

### Anderson参数说明
- **m**: 历史深度，保存最近m个迭代向量
- **β**: 松弛因子，控制更新步长（0-1）

---

##  详细测试结果

"""

    # 每个场景的详细结果
    for scenario_name, scenario_results in scenarios.items():
        report += f"### {scenario_name}\n\n"
        report += f"| 方法 | 收敛 | 迭代次数 | 时间(ms) | 加速比 | 最终残差 |\n"
        report += f"|------|------|----------|----------|--------|----------|\n"

        for r in scenario_results:
            converged = "" if r['converged'] else ""
            speedup = f"{r.get('speedup_ratio', 0):.2f}x" if r.get('speedup_ratio') else "-"
            report += f"| {r['method']} | {converged} | {r['iterations']} | {r['execution_time']*1000:.1f} | {speedup} | {r['residual_norm']:.2e} |\n"

        report += "\n"

    # 性能分析
    report += "---\n\n##  性能分析\n\n"

    # 1. 加速比统计
    report += "### 1. 加速效果对比\n\n"

    for scenario_name in scenarios.keys():
        report += f"#### {scenario_name}\n\n"

        scenario_results = scenarios[scenario_name]
        baseline = next((r for r in scenario_results if r['config'] is None), None)

        if baseline and baseline['converged']:
            report += f"基准（无加速）: {baseline['iterations']}次迭代，{baseline['execution_time']*1000:.1f}ms\n\n"

            accelerated = [r for r in scenario_results if r['config'] is not None and r['converged']]
            accelerated.sort(key=lambda x: x['iterations'])

            report += "| 排名 | 方法 | 迭代次数 | 减少 | 加速比 |\n"
            report += "|------|------|----------|------|--------|\n"

            for i, r in enumerate(accelerated[:5], 1):
                reduction = baseline['iterations'] - r['iterations']
                report += f"| {i} | {r['method']} | {r['iterations']} | -{reduction} | {r.get('speedup_ratio', 0):.2f}x |\n"

            report += "\n"

    # 2. 最佳配置推荐
    report += "### 2. 最佳配置分析\n\n"

    # 统计每个方法的平均性能
    method_stats = {}

    for r in results:
        method = r['method']
        if method not in method_stats:
            method_stats[method] = {
                'total_iterations': 0,
                'total_time': 0,
                'converged_count': 0,
                'total_count': 0,
                'speedup_ratios': []
            }

        stats = method_stats[method]
        stats['total_iterations'] += r['iterations'] if r['converged'] else 0
        stats['total_time'] += r['execution_time']
        stats['converged_count'] += 1 if r['converged'] else 0
        stats['total_count'] += 1

        if r.get('speedup_ratio'):
            stats['speedup_ratios'].append(r['speedup_ratio'])

    # 计算平均值
    for method, stats in method_stats.items():
        if stats['converged_count'] > 0:
            stats['avg_iterations'] = stats['total_iterations'] / stats['converged_count']
            stats['avg_time'] = stats['total_time'] / stats['converged_count']
            stats['avg_speedup'] = np.mean(stats['speedup_ratios']) if stats['speedup_ratios'] else None
            stats['success_rate'] = stats['converged_count'] / stats['total_count'] * 100

    # 找出最佳Anderson方法
    anderson_methods = {k: v for k, v in method_stats.items() if 'Anderson' in k}

    if anderson_methods:
        best_method = min(anderson_methods.items(),
                         key=lambda x: x[1]['avg_iterations'] if x[1]['converged_count'] > 0 else float('inf'))

        report += f"**综合最佳配置**: {best_method[0]}\n\n"
        report += f"- 平均迭代次数: {best_method[1]['avg_iterations']:.1f}\n"
        report += f"- 平均加速比: {best_method[1]['avg_speedup']:.2f}x\n"
        report += f"- 平均时间: {best_method[1]['avg_time']*1000:.1f}ms\n"
        report += f"- 成功率: {best_method[1]['success_rate']:.1f}%\n\n"

    # 3. 参数敏感性分析
    report += "### 3. Anderson参数敏感性\n\n"

    report += "#### m参数影响（固定β=0.8）\n\n"

    m_comparison = {
        3: method_stats.get("Anderson (m=3, β=0.8)", {}),
        5: method_stats.get("Anderson (m=5, β=0.8) 推荐", {}),
        7: method_stats.get("Anderson (m=7, β=0.8)", {}),
    }

    report += "| m值 | 平均迭代次数 | 平均加速比 | 平均时间(ms) |\n"
    report += "|-----|--------------|------------|-------------|\n"

    for m, stats in m_comparison.items():
        if stats:
            report += f"| {m} | {stats.get('avg_iterations', 0):.1f} | {stats.get('avg_speedup', 0):.2f}x | {stats.get('avg_time', 0)*1000:.1f} |\n"

    report += "\n#### β参数影响（固定m=5）\n\n"

    beta_comparison = {
        0.7: method_stats.get("Anderson (m=5, β=0.7)", {}),
        0.8: method_stats.get("Anderson (m=5, β=0.8) 推荐", {}),
        1.0: method_stats.get("Anderson (m=5, β=1.0)", {}),
    }

    report += "| β值 | 平均迭代次数 | 平均加速比 | 平均时间(ms) |\n"
    report += "|-----|--------------|------------|-------------|\n"

    for beta, stats in beta_comparison.items():
        if stats:
            report += f"| {beta} | {stats.get('avg_iterations', 0):.1f} | {stats.get('avg_speedup', 0):.2f}x | {stats.get('avg_time', 0)*1000:.1f} |\n"

    report += "\n"

    # 4. 使用建议
    report += "---\n\n##  使用建议\n\n"

    if best_method:
        report += "### 推荐配置\n\n"
        report += f"基于测试结果，推荐使用 **{best_method[0]}** 配置：\n\n"
        config = [r for r in results if r['method'] == best_method[0]][0]['config']
        if config:
            report += f"```python\n"
            report += "try:\n"
            report += "    from solvers.anderson_acceleration import AndersonAcceleration\n"
            report += "except ImportError as e:\n"
            report += "    print(f\"Import error: {e}\")\n"
            report += "    print(\"Make sure project root is in sys.path\")\n"
            report += "    sys.exit(1)\n\n"
            report += f"anderson = AndersonAcceleration(\n"
            report += f"    m={config['m']},  # 历史深度\n"
            report += f"    beta={config['beta']}  # 松弛因子\n"
            report += f")\n"
            report += f"```\n\n"

    report += "### 参数选择指南\n\n"
    report += "**m参数（历史深度）**:\n"
    report += "- m=3: 适合简单问题，内存开销小\n"
    report += "- m=5: **推荐**，平衡性能和开销\n"
    report += "- m=7: 复杂问题可能更好，但开销增加\n\n"

    report += "**β参数（松弛因子）**:\n"
    report += "- β=0.7: 保守，适合不稳定问题\n"
    report += "- β=0.8: **推荐**，平衡稳定性和速度\n"
    report += "- β=1.0: 激进，可能更快但稳定性略差\n\n"

    report += "### 应用场景\n\n"
    report += "Anderson加速特别适合于:\n"
    report += "- 固定点迭代收敛缓慢的问题\n"
    report += "- 大规模非线性系统\n"
    report += "- 需要多次求解相似问题的场景\n\n"

    report += "---\n\n"
    report += f"**测试工具**: test_anderson_performance.py\n"
    report += f"**Anderson实现**: solvers/anderson_acceleration.py\n"
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
    converged_tests = sum(1 for r in results if r['converged'])

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
