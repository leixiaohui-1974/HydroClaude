#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
MacDonald Test 4 - 标准WENO3参数扫描优化

基于经验教训：
- 放弃复杂的增强算法
- 专注于稳定算法的参数优化
- 系统地测试CFL、网格、epsilon的组合

目标: 从28%质量误差改善到15%以下

作者: HydroClaude Team
日期: 2025-10-30
"""

import sys
import os
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent.parent))

import numpy as np
import tempfile
import json
from engine.simulation_engine import SimulationEngine
from itertools import product


def run_single_test(config_name, n_cells, cfl, weno_eps, simulation_time=50.0):
    """
    运行单个参数配置的测试

    Args:
        config_name: 配置名称
        n_cells: 网格数
        cfl: CFL数
        weno_eps: WENO epsilon
        simulation_time: 模拟时间(秒)

    Returns:
        dict: 测试结果
    """
    # 测试参数
    L = 1000.0
    B = 10.0
    S0 = 0.0
    n = 0.0

    h_upstream = 0.7
    Q = 20.0
    h_downstream = 2.8

    dx = L / n_cells
    g = 9.81

    # 理论值
    u_upstream = Q / (B * h_upstream)
    Fr_upstream = u_upstream / np.sqrt(g * h_upstream)
    h2_theory = h_upstream / 2.0 * (-1.0 + np.sqrt(1.0 + 8.0 * Fr_upstream**2))

    # 初始条件
    x = np.linspace(dx/2, L - dx/2, n_cells)
    h_init = np.linspace(h_upstream, h_downstream, n_cells)
    Q_init = np.ones(n_cells) * Q

    # 创建临时初始条件文件
    ic_data = np.column_stack([x, h_init, Q_init])
    ic_file = tempfile.NamedTemporaryFile(mode='w', suffix='.csv', delete=False)
    ic_file.write('x,h,Q\n')
    np.savetxt(ic_file, ic_data, delimiter=',')
    ic_file.close()
    ic_file_path = Path(ic_file.name)

    # 配置
    config = {
        'project': {
            'name': f'MacDonald Test 4 - {config_name}',
            'description': config_name
        },
        'geometry': {
            'type': 'uniform',
            'channel_width': B,
            'channel_length': L,
            'bottom_slope': S0,
            'manning_n': n
        },
        'mesh': {
            'n_cells': n_cells
        },
        'initial_conditions': {
            'type': 'from_file',
            'file': str(ic_file_path)
        },
        'boundary_conditions': {
            'left': {'type': 'supercritical', 'h': h_upstream, 'Q': Q},
            'right': {'type': 'h', 'value': h_downstream}
        },
        'solver': {
            'type': 'godunov_fvm',
            'spatial_order': 3,  # 标准WENO3
            'weno3_enhanced': False,  # 明确禁用增强版
            'riemann_solver': 'hll',
            'use_numba': True,
            'cfl': cfl,
            'eps_dry': 1e-6,
            'weno_epsilon': weno_eps,
            'well_balanced': False,
            'dt_max': 0.5
        },
        'simulation': {
            'start_time': 0.0,
            'end_time': simulation_time,
            'max_steps': 50000,
            'output_interval': simulation_time
        },
        'output': {
            'directory': 'test_output',
            'formats': [],
            'variables': [],
            'statistics': True,
            'plots': {'enabled': False}
        },
        'validation': {
            'enabled': False
        }
    }

    # 创建临时配置文件
    config_file = tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False)
    json.dump(config, config_file, indent=2, ensure_ascii=False)
    config_file.close()
    config_file_path = Path(config_file.name)

    try:
        # 运行仿真
        engine = SimulationEngine(str(config_file_path))
        engine.initialize()
        engine.run()

        # 获取结果
        h_final = engine.solver.h.copy()
        Q_final = engine.solver.Q.copy()
        x_solver = engine.solver.x.copy()

        # 计算Froude数
        u_final = np.zeros_like(h_final)
        Fr_final = np.zeros_like(h_final)
        mask = h_final > engine.solver.eps_dry
        u_final[mask] = Q_final[mask] / (h_final[mask] * B)
        Fr_final[mask] = np.abs(u_final[mask]) / np.sqrt(g * h_final[mask])

        # 统计结果
        results = {
            'config_name': config_name,
            'n_cells': n_cells,
            'cfl': cfl,
            'weno_eps': weno_eps,
            'dx': dx,
            'time': engine.solver.t,
            'steps': engine.solver.step_count,
            'success': True
        }

        # 质量守恒
        if hasattr(engine, 'statistics') and 'simulation' in engine.statistics:
            mass_error = engine.statistics['simulation'].get('mass_error', np.nan)
            results['mass_error'] = abs(mass_error) if not np.isnan(mass_error) else np.nan
        else:
            results['mass_error'] = np.nan

        # 上游Froude数
        results['Fr_upstream'] = Fr_final[0]

        # 负流量
        results['n_negative'] = np.sum(Q_final < 0)
        results['pct_negative'] = results['n_negative'] / n_cells * 100

        # 水跃分析
        supercritical_mask = Fr_final > 1.0
        if np.any(supercritical_mask):
            last_super_idx = np.where(supercritical_mask)[0][-1]
            h_before = h_final[last_super_idx]

            if last_super_idx + 10 < len(h_final):
                h_after = np.mean(h_final[last_super_idx+5:last_super_idx+10])
            else:
                h_after = h_final[-1]

            results['belanger_error'] = abs(h_after - h2_theory) / h2_theory * 100
            results['n_supercritical'] = np.sum(supercritical_mask)
        else:
            results['belanger_error'] = np.nan
            results['n_supercritical'] = 0

        # 数值范围
        results['h_min'] = np.min(h_final)
        results['h_max'] = np.max(h_final)

        return results

    except Exception as e:
        # 记录失败
        return {
            'config_name': config_name,
            'n_cells': n_cells,
            'cfl': cfl,
            'weno_eps': weno_eps,
            'success': False,
            'error': str(e),
            'mass_error': np.nan,
            'Fr_upstream': np.nan,
            'n_negative': -1,
            'belanger_error': np.nan
        }

    finally:
        # 清理
        ic_file_path.unlink(missing_ok=True)
        config_file_path.unlink(missing_ok=True)


def parameter_sweep():
    """
    系统参数扫描
    """
    print("="*80)
    print("MacDonald Test 4 - 标准WENO3参数优化")
    print("="*80)
    print("\n策略: 稳定算法 + 系统调参 > 复杂算法")
    print()

    # 定义参数空间
    # 基于经验：粗网格不如细网格，低CFL不如中等CFL
    grid_sizes = [100, 150]  # 100已测试，150为中间值，不测200(太慢)
    cfl_values = [0.3, 0.4]  # 0.4已测试，0.3更保守
    epsilon_values = [1e-6]  # 1e-6已测试且合理

    print(f"参数空间:")
    print(f"  网格: {grid_sizes}")
    print(f"  CFL: {cfl_values}")
    print(f"  epsilon: {epsilon_values}")
    print(f"  总组合: {len(grid_sizes) * len(cfl_values) * len(epsilon_values)}")
    print()

    # 测试时间：网格越细需要越长时间达到稳态
    simulation_time = 50.0  # 统一50秒

    results_list = []

    # 参数扫描
    for n_cells, cfl, eps in product(grid_sizes, cfl_values, epsilon_values):
        config_name = f"n{n_cells}_cfl{cfl:.1f}_eps{eps:.0e}"

        print(f"\n{'='*80}")
        print(f"测试配置: {config_name}")
        print(f"  网格: {n_cells} cells, dx={1000.0/n_cells:.2f}m")
        print(f"  CFL: {cfl}")
        print(f"  epsilon: {eps:.0e}")
        print(f"{'='*80}")

        result = run_single_test(config_name, n_cells, cfl, eps, simulation_time)
        results_list.append(result)

        # 打印即时结果
        if result['success']:
            print(f"\n 完成:")
            print(f"  模拟时间: {result['time']:.1f}s, 步数: {result['steps']}")
            print(f"  质量误差: {result['mass_error']:.2f}%")
            print(f"  Fr上游: {result['Fr_upstream']:.3f}")
            print(f"  负流量: {result['n_negative']}/{n_cells} ({result['pct_negative']:.1f}%)")
            if not np.isnan(result['belanger_error']):
                print(f"  Belanger误差: {result['belanger_error']:.1f}%")
        else:
            print(f"\n 失败: {result['error']}")

    # 汇总分析
    print(f"\n{'='*80}")
    print("参数扫描结果汇总")
    print(f"{'='*80}")

    # 表格形式输出
    print(f"\n{'配置':<20} {'质量误差':>10} {'负流量%':>10} {'Fr上游':>10} {'Belanger':>10} {'步数':>8}")
    print("-"*80)

    for result in results_list:
        if result['success']:
            mass_str = f"{result['mass_error']:.2f}%" if not np.isnan(result['mass_error']) else "N/A"
            neg_str = f"{result['pct_negative']:.1f}%"
            fr_str = f"{result['Fr_upstream']:.3f}" if not np.isnan(result['Fr_upstream']) else "N/A"
            bel_str = f"{result['belanger_error']:.1f}%" if not np.isnan(result['belanger_error']) else "N/A"
            steps_str = f"{result['steps']}"

            print(f"{result['config_name']:<20} {mass_str:>10} {neg_str:>10} {fr_str:>10} {bel_str:>10} {steps_str:>8}")
        else:
            print(f"{result['config_name']:<20} {'FAILED':>10} {'-':>10} {'-':>10} {'-':>10} {'-':>8}")

    # 找出最佳配置
    print(f"\n{'='*80}")
    print("最佳配置分析")
    print(f"{'='*80}")

    successful_results = [r for r in results_list if r['success'] and not np.isnan(r['mass_error'])]

    if successful_results:
        # 按质量误差排序
        sorted_by_mass = sorted(successful_results, key=lambda x: x['mass_error'])

        print(f"\n 质量守恒最佳:")
        best_mass = sorted_by_mass[0]
        print(f"  配置: {best_mass['config_name']}")
        print(f"  质量误差: {best_mass['mass_error']:.2f}%")
        print(f"  负流量: {best_mass['pct_negative']:.1f}%")
        print(f"  Fr上游: {best_mass['Fr_upstream']:.3f}")

        # 按负流量排序
        sorted_by_neg = sorted(successful_results, key=lambda x: x['n_negative'])
        best_neg = sorted_by_neg[0]
        print(f"\n 负流量最少:")
        print(f"  配置: {best_neg['config_name']}")
        print(f"  负流量: {best_neg['n_negative']}/{best_neg['n_cells']} ({best_neg['pct_negative']:.1f}%)")
        print(f"  质量误差: {best_neg['mass_error']:.2f}%")

        # 综合评分 (质量误差权重0.6, 负流量权重0.4)
        for r in successful_results:
            mass_score = max(0, 100 - r['mass_error']) / 100  # 归一化到0-1
            neg_score = (1 - r['pct_negative']/100)  # 归一化到0-1
            r['综合得分'] = 0.6 * mass_score + 0.4 * neg_score

        sorted_by_combined = sorted(successful_results, key=lambda x: x['综合得分'], reverse=True)
        best_combined = sorted_by_combined[0]

        print(f"\n 综合最佳 (0.6x质量+0.4x负流量):")
        print(f"  配置: {best_combined['config_name']}")
        print(f"  质量误差: {best_combined['mass_error']:.2f}%")
        print(f"  负流量: {best_combined['pct_negative']:.1f}%")
        print(f"  Fr上游: {best_combined['Fr_upstream']:.3f}")
        print(f"  综合得分: {best_combined['综合得分']:.3f}/1.000")

        # 对比基准(100网格, CFL=0.4, eps=1e-6)
        baseline = next((r for r in results_list if r['config_name'] == 'n100_cfl0.4_eps1e-06'), None)
        if baseline and baseline['success']:
            print(f"\n vs 基准配置(n100_cfl0.4):")
            print(f"  基准质量误差: {baseline['mass_error']:.2f}%")
            print(f"  最佳质量误差: {best_mass['mass_error']:.2f}%")
            improvement = (baseline['mass_error'] - best_mass['mass_error']) / baseline['mass_error'] * 100
            print(f"  改善: {improvement:.1f}%")
    else:
        print("\n️  所有测试均失败或数据无效")

    print(f"\n{'='*80}")
    print("结论与建议")
    print(f"{'='*80}")
    print()
    print("基于参数扫描结果：")
    print("1. 更细的网格通常能改善质量守恒")
    print("2. CFL的影响需要具体分析")
    print("3. MacDonald Test 4本质上是困难问题（强激波+无摩阻）")
    print("4. 28% -> 15%的目标需要更激进的方法（更细网格或改进算法）")
    print()


if __name__ == '__main__':
    parameter_sweep()
