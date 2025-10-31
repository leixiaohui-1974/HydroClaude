#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
MacDonald Test 4 对比测试：标准WENO3 vs 增强WENO3

目标：对比两种求解器在相同配置下的性能
- 标准WENO3
- 增强WENO3

重点指标：
1. 质量守恒误差
2. 负流量问题
3. 上游超临界维持
4. Belanger方程精度

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


def run_test(test_name, weno3_enhanced=False):
    """
    运行MacDonald Test 4

    Args:
        test_name: 测试名称
        weno3_enhanced: 是否使用增强版WENO3

    Returns:
        dict: 测试结果
    """
    print(f"\n{'='*80}")
    print(f"运行: {test_name}")
    print(f"{'='*80}")

    # 测试参数 - 优化配置
    L = 1000.0          # 渠道长度
    B = 10.0            # 渠宽
    S0 = 0.0            # 平底
    n = 0.0             # 无摩阻

    h_upstream = 0.7    # 上游水深
    Q = 20.0            # 流量
    h_downstream = 2.8  # 下游水深

    # 平衡配置：100网格，较好的分辨率和速度
    n_cells = 100
    dx = L / n_cells

    g = 9.81

    # 计算理论值
    u_upstream = Q / (B * h_upstream)
    Fr_upstream = u_upstream / np.sqrt(g * h_upstream)
    h2_theory = h_upstream / 2.0 * (-1.0 + np.sqrt(1.0 + 8.0 * Fr_upstream**2))

    print(f"\n配置:")
    print(f"  网格: {n_cells} cells, dx={dx:.2f}m")
    print(f"  上游: h={h_upstream:.2f}m, Q={Q:.1f}m³/s, Fr={Fr_upstream:.2f}")
    print(f"  理论水跃后: h2={h2_theory:.3f}m")

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
            'name': f'MacDonald Test 4 - {test_name}',
            'description': test_name
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
            'spatial_order': 3,
            'weno3_enhanced': weno3_enhanced,  # 关键区别
            'riemann_solver': 'hll',
            'use_numba': True,
            'cfl': 0.4,  # 统一CFL
            'eps_dry': 1e-6,
            'weno_epsilon': 1e-6,
            'well_balanced': False,
            'dt_max': 0.5,
            # 增强版特有参数（标准版会忽略）
            'entropy_fix': weno3_enhanced,
            'critical_flow_treatment': weno3_enhanced,
            'adaptive_cfl': False,  # 关闭自适应CFL以确保速度
            'cfl_shock': 0.3,
            'entropy_delta': 0.1
        },
        'simulation': {
            'start_time': 0.0,
            'end_time': 50.0,  # 50秒足够形成稳定水跃
            'max_steps': 20000,
            'output_interval': 10.0
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
            'test_name': test_name,
            'weno3_enhanced': weno3_enhanced,
            'n_cells': n_cells,
            'time': engine.solver.t,
            'steps': engine.solver.step_count
        }

        # 1. 质量守恒
        if hasattr(engine, 'statistics') and 'simulation' in engine.statistics:
            mass_error = engine.statistics['simulation'].get('mass_error', np.nan)
            results['mass_error'] = abs(mass_error) if not np.isnan(mass_error) else np.nan
        else:
            results['mass_error'] = np.nan

        # 2. 上游Froude数
        results['Fr_upstream'] = Fr_final[0]

        # 3. 负流量
        results['n_negative'] = np.sum(Q_final < 0)

        # 4. 水跃分析
        supercritical_mask = Fr_final > 1.0
        if np.any(supercritical_mask):
            last_super_idx = np.where(supercritical_mask)[0][-1]
            results['jump_location'] = x_solver[last_super_idx]
            results['h_before_jump'] = h_final[last_super_idx]

            # 水跃后水深（平均后面5-10个单元）
            if last_super_idx + 10 < len(h_final):
                h_after = np.mean(h_final[last_super_idx+5:last_super_idx+10])
            else:
                h_after = h_final[-1]

            results['h_after_jump'] = h_after
            results['belanger_error'] = abs(h_after - h2_theory) / h2_theory * 100
            results['n_supercritical'] = np.sum(supercritical_mask)
        else:
            results['jump_location'] = None
            results['h_before_jump'] = None
            results['h_after_jump'] = None
            results['belanger_error'] = np.nan
            results['n_supercritical'] = 0

        # 5. 最大最小值
        results['h_min'] = np.min(h_final)
        results['h_max'] = np.max(h_final)
        results['Q_min'] = np.min(Q_final)
        results['Q_max'] = np.max(Q_final)

        print(f"\n结果概要:")
        print(f"  模拟时间: {results['time']:.2f}s，步数: {results['steps']}")
        print(f"  质量误差: {results['mass_error']:.2f}%")
        print(f"  上游Fr: {results['Fr_upstream']:.3f}")
        print(f"  负流量单元: {results['n_negative']}/{n_cells}")
        if not np.isnan(results['belanger_error']):
            print(f"  Belanger误差: {results['belanger_error']:.1f}%")

        return results

    finally:
        # 清理
        ic_file_path.unlink(missing_ok=True)
        config_file_path.unlink(missing_ok=True)


def compare_results(results_standard, results_enhanced):
    """对比两个结果"""
    print(f"\n{'='*80}")
    print("对比结果: 标准WENO3 vs 增强WENO3")
    print(f"{'='*80}")

    # 表格对比
    print(f"\n{'指标':<20} {'标准WENO3':>15} {'增强WENO3':>15} {'改善':>15}")
    print(f"{'-'*70}")

    # 质量守恒
    mass_std = results_standard['mass_error']
    mass_enh = results_enhanced['mass_error']
    if not np.isnan(mass_std) and not np.isnan(mass_enh):
        improvement = (mass_std - mass_enh) / mass_std * 100 if mass_std > 0 else 0
        print(f"{'质量守恒误差 (%)':<20} {mass_std:>15.2f} {mass_enh:>15.2f} {improvement:>14.1f}%")

    # 负流量
    neg_std = results_standard['n_negative']
    neg_enh = results_enhanced['n_negative']
    print(f"{'负流量单元':<20} {neg_std:>15} {neg_enh:>15} {'✅' if neg_enh == 0 else '❌':>15}")

    # 上游Fr
    Fr_std = results_standard['Fr_upstream']
    Fr_enh = results_enhanced['Fr_upstream']
    print(f"{'上游Froude数':<20} {Fr_std:>15.3f} {Fr_enh:>15.3f} {'✅' if Fr_enh > 1.0 else '❌':>15}")

    # Belanger误差
    bel_std = results_standard['belanger_error']
    bel_enh = results_enhanced['belanger_error']
    if not np.isnan(bel_std) and not np.isnan(bel_enh):
        improvement = (bel_std - bel_enh) / bel_std * 100 if bel_std > 0 else 0
        print(f"{'Belanger误差 (%)':<20} {bel_std:>15.1f} {bel_enh:>15.1f} {improvement:>14.1f}%")

    # 超临界区域
    super_std = results_standard['n_supercritical']
    super_enh = results_enhanced['n_supercritical']
    print(f"{'超临界单元数':<20} {super_std:>15} {super_enh:>15} {'':<15}")

    # 计算性能
    steps_std = results_standard['steps']
    steps_enh = results_enhanced['steps']
    print(f"{'模拟步数':<20} {steps_std:>15} {steps_enh:>15} {'':<15}")

    print(f"\n{'='*80}")
    print("总结")
    print(f"{'='*80}")

    # 评分
    score_std = 0
    score_enh = 0

    criteria = []

    # 质量守恒 (权重: 3)
    if not np.isnan(mass_std) and not np.isnan(mass_enh):
        if mass_std < 10:
            score_std += 3
        elif mass_std < 20:
            score_std += 2
        elif mass_std < 30:
            score_std += 1

        if mass_enh < 10:
            score_enh += 3
            criteria.append(f"✅ 增强版质量守恒优秀: {mass_enh:.1f}% < 10%")
        elif mass_enh < 20:
            score_enh += 2
            criteria.append(f"✅ 增强版质量守恒良好: {mass_enh:.1f}% < 20%")
        elif mass_enh < 30:
            score_enh += 1
            criteria.append(f"⚠️  增强版质量守恒可接受: {mass_enh:.1f}% < 30%")

    # 负流量 (权重: 2)
    if neg_std == 0:
        score_std += 2
    if neg_enh == 0:
        score_enh += 2
        criteria.append(f"✅ 增强版无负流量")
    else:
        criteria.append(f"⚠️  增强版仍有{neg_enh}个负流量单元")

    # 超临界维持 (权重: 2)
    if Fr_std > 1.0:
        score_std += 2
    if Fr_enh > 1.0:
        score_enh += 2
        criteria.append(f"✅ 增强版维持超临界: Fr={Fr_enh:.3f}")
    else:
        criteria.append(f"❌ 增强版超临界丢失: Fr={Fr_enh:.3f}")

    # Belanger精度 (权重: 2)
    if not np.isnan(bel_std) and not np.isnan(bel_enh):
        if bel_std < 10:
            score_std += 2
        elif bel_std < 20:
            score_std += 1

        if bel_enh < 10:
            score_enh += 2
            criteria.append(f"✅ 增强版Belanger精度优秀: {bel_enh:.1f}% < 10%")
        elif bel_enh < 20:
            score_enh += 1
            criteria.append(f"✅ 增强版Belanger精度良好: {bel_enh:.1f}% < 20%")
        elif bel_enh < 30:
            criteria.append(f"⚠️  增强版Belanger精度可接受: {bel_enh:.1f}% < 30%")

    print(f"\n通过的标准:")
    for criterion in criteria:
        print(f"  {criterion}")

    print(f"\n评分:")
    print(f"  标准WENO3: {score_std}/9")
    print(f"  增强WENO3: {score_enh}/9")

    if score_enh > score_std:
        print(f"\n🎉 增强版WENO3显著优于标准版！(提升{score_enh-score_std}分)")
    elif score_enh == score_std:
        print(f"\n✅ 增强版WENO3与标准版相当")
    else:
        print(f"\n⚠️  增强版WENO3需要进一步优化")

    print(f"\n{'='*80}")


if __name__ == '__main__':
    print("="*80)
    print("MacDonald Test 4 对比测试")
    print("标准WENO3 vs 增强WENO3")
    print("="*80)

    # 运行标准版
    results_standard = run_test("标准WENO3", weno3_enhanced=False)

    # 运行增强版
    results_enhanced = run_test("增强WENO3", weno3_enhanced=True)

    # 对比
    compare_results(results_standard, results_enhanced)
