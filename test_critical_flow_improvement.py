#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
测试临界流处理对MacDonald Test 4的改进效果

对比启用/禁用临界流处理在有摩阻水跃上的表现

Author: HydroClaude Team
Date: 2025-10-29
"""

import numpy as np
import sys
import json
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from engine.simulation_engine import SimulationEngine
from engine.model_builder import ModelBuilder


def run_macdonald_test4_realistic(critical_flow_treatment=False):
    """
    运行MacDonald Test 4 Realistic（有摩阻水跃）

    Args:
        critical_flow_treatment: 是否启用临界流处理

    Returns:
        dict: 包含质量误差、最小水深等结果
    """
    print("\n" + "="*80)
    print(f"MacDonald Test 4 Realistic - 临界流处理: {'启用' if critical_flow_treatment else '禁用'}")
    print("="*80)

    # 测试参数（有摩阻版本）
    L = 1000.0
    B = 10.0
    S0 = 0.0
    n = 0.03  # 真实摩阻
    n_cells = 200
    dx = L / n_cells

    # 初始条件：左侧超临界，右侧亚临界（水跃）
    x = np.linspace(dx/2, L - dx/2, n_cells)
    h = np.zeros(n_cells)
    Q = np.zeros(n_cells)

    for i, xi in enumerate(x):
        if xi < 500.0:
            h[i] = 0.5  # 上游超临界
            Q[i] = 25.0
        else:
            h[i] = 2.0  # 下游亚临界
            Q[i] = 25.0

    # 创建初始条件文件
    ic_data = np.column_stack([x, h, Q])
    ic_file = tempfile.NamedTemporaryFile(mode='w', suffix='.csv', delete=False)
    ic_file.write('x,h,Q\n')
    np.savetxt(ic_file, ic_data, delimiter=',')
    ic_file.close()
    ic_file_path = Path(ic_file.name)

    # 创建输出目录
    output_dir = tempfile.mkdtemp(prefix=f'test_critical_flow_{"on" if critical_flow_treatment else "off"}_')

    # 创建配置
    config = {
        'project': {
            'name': f'MacDonald Test 4 Realistic - Critical Flow {"ON" if critical_flow_treatment else "OFF"}',
            'description': '有摩阻水跃测试',
            'author': 'HydroClaude Team',
            'created': '2025-10-29'
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
            'left': {'type': 'Q', 'value': 25.0},
            'right': {'type': 'h', 'value': 2.0}
        },
        'simulation': {
            't_start': 0.0,
            't_end': 200.0,  # 运行到稳态
            'dt_output': 50.0
        },
        'solver': {
            'type': 'godunov_fvm',
            'riemann_solver': 'hll',
            'spatial_order': 3,  # WENO3
            'cfl': 0.4,
            'use_numba': True,
            'entropy_fix': True,  # 启用entropy fix
            'critical_flow_treatment': critical_flow_treatment  # 测试参数
        },
        'output': {
            'directory': output_dir,
            'format': 'json',
            'variables': ['h', 'Q', 'u']
        }
    }

    # 保存配置
    config_file = tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False)
    json.dump(config, config_file, indent=2)
    config_file.close()
    config_file_path = Path(config_file.name)

    # 运行仿真
    print("\n启动仿真...")
    try:
        builder = ModelBuilder(str(config_file_path))
        model = builder.build()
        engine = SimulationEngine(model)
        engine.run()

        # 计算结果统计
        solver = model.solver
        mass_error = abs(solver.compute_mass_error())
        min_h = np.min(solver.h)
        max_h = np.max(solver.h)

        # 计算Froude数分布
        Fr = solver.compute_froude_number()
        critical_cells = np.sum(solver.is_critical_flow(Fr))

        print(f"\n{'='*80}")
        print("仿真完成")
        print(f"{'='*80}")
        print(f"结果统计:")
        print(f"  质量守恒误差: {mass_error:.4f}%")
        print(f"  最小水深: {min_h:.4f} m")
        print(f"  最大水深: {max_h:.4f} m")
        print(f"  Froude数范围: [{Fr.min():.3f}, {Fr.max():.3f}]")
        print(f"  临界流单元数: {critical_cells}")

        # 检查是否有负水深
        has_negative_depth = np.any(solver.h < 0)
        print(f"  负水深: {'是' if has_negative_depth else '否'}")

        results = {
            'mass_error': mass_error,
            'min_h': min_h,
            'max_h': max_h,
            'Fr_min': Fr.min(),
            'Fr_max': Fr.max(),
            'critical_cells': critical_cells,
            'has_negative_depth': has_negative_depth,
            'success': True
        }

    except Exception as e:
        print(f"\n✗ 仿真失败: {e}")
        import traceback
        traceback.print_exc()
        results = {
            'success': False,
            'error': str(e)
        }

    finally:
        # 清理临时文件
        try:
            ic_file_path.unlink()
            config_file_path.unlink()
        except:
            pass

    return results


def main():
    """主函数：对比测试"""

    print("\n" + "="*80)
    print("临界流处理改进效果测试")
    print("="*80)
    print("\n测试案例: MacDonald Test 4 Realistic (有摩阻水跃)")
    print("对比: 禁用 vs 启用 临界流特殊处理")

    # 测试1：禁用临界流处理
    results_off = run_macdonald_test4_realistic(critical_flow_treatment=False)

    # 测试2：启用临界流处理
    results_on = run_macdonald_test4_realistic(critical_flow_treatment=True)

    # 对比分析
    print("\n" + "="*80)
    print("对比分析")
    print("="*80)

    if results_off['success'] and results_on['success']:
        print(f"\n{'指标':<25} {'禁用':<15} {'启用':<15} {'改善':<15}")
        print("-" * 70)

        mass_diff = results_off['mass_error'] - results_on['mass_error']
        print(f"{'质量守恒误差 (%)':<25} {results_off['mass_error']:<15.4f} {results_on['mass_error']:<15.4f} {mass_diff:+.4f}")

        print(f"{'最小水深 (m)':<25} {results_off['min_h']:<15.4f} {results_on['min_h']:<15.4f} {results_on['min_h'] - results_off['min_h']:+.4f}")

        print(f"{'Fr范围':<25} [{results_off['Fr_min']:.2f}, {results_off['Fr_max']:.2f}]"
              f"  [{results_on['Fr_min']:.2f}, {results_on['Fr_max']:.2f}]  N/A")

        print(f"{'临界流单元数':<25} {results_off['critical_cells']:<15} {results_on['critical_cells']:<15} N/A")

        print(f"{'负水深':<25} {'是' if results_off['has_negative_depth'] else '否':<15} "
              f"{'是' if results_on['has_negative_depth'] else '否':<15} N/A")

        print(f"\n{'='*80}")
        print("结论")
        print(f"{'='*80}")

        if mass_diff > 0:
            print(f"✓ 临界流处理改善了质量守恒: {mass_diff:.4f}% 减少")
        elif mass_diff < -0.1:
            print(f"✗ 临界流处理略微增加了质量误差: {abs(mass_diff):.4f}%")
        else:
            print(f"≈ 临界流处理对质量守恒影响很小: {abs(mass_diff):.4f}%")

        if not results_off['has_negative_depth'] and not results_on['has_negative_depth']:
            print("✓ 两种配置均无负水深")
        elif results_off['has_negative_depth'] and not results_on['has_negative_depth']:
            print("✓ 临界流处理消除了负水深")

        # 总体评估
        print(f"\n总体评估:")
        if results_on['mass_error'] < 5.0 and not results_on['has_negative_depth']:
            print("✓ 启用临界流处理后求解器表现良好")
        else:
            print("⚠ 仍需进一步优化")

    else:
        print("\n⚠ 部分测试失败，无法完成对比")
        if not results_off['success']:
            print(f"  禁用临界流处理: 失败 - {results_off.get('error', 'Unknown')}")
        if not results_on['success']:
            print(f"  启用临界流处理: 失败 - {results_on.get('error', 'Unknown')}")

    print("\n" + "="*80)


if __name__ == "__main__":
    main()
