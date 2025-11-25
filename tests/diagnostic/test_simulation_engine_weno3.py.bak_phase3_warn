#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
测试SimulationEngine是否正确创建WENO3求解器

日期: 2025-10-29
"""

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..'))

import json
import tempfile
from pathlib import Path
from engine.simulation_engine import SimulationEngine

# 创建Test 4配置（与pytest测试完全相同）
config = {
    'project': {
        'name': 'Test WENO3 via SimulationEngine',
        'description': '测试SimulationEngine是否正确使用WENO3',
        'author': 'Debug',
        'created': '2025-10-29'
    },
    'geometry': {
        'type': 'uniform',
        'channel_width': 10.0,
        'channel_length': 1000.0,
        'bottom_slope': 0.0,
        'manning_n': 0.0
    },
    'mesh': {
        'n_cells': 200
    },
    'initial_conditions': {
        'type': 'uniform',
        'h': 1.5,
        'Q': 20.0
    },
    'boundary_conditions': {
        'left': {'type': 'supercritical', 'h': 0.7, 'Q': 20.0},
        'right': {'type': 'h', 'value': 2.8}
    },
    'solver': {
        'type': 'godunov_fvm',
        'spatial_order': 3,  # WENO3
        'riemann_solver': 'hll',
        'use_numba': True,
        'cfl': 0.4,
        'eps_dry': 1e-6,
        'weno_epsilon': 1e-6,
        'well_balanced': False,
        'dt_max': 0.5
    },
    'simulation': {
        'start_time': 0.0,
        'end_time': 30.0,  # 只运行30秒用于快速诊断
        'max_steps': 10000,
        'output_interval': 30.0
    },
    'output': {
        'directory': '/tmp/test_weno3_engine',
        'formats': ['json'],
        'variables': ['h', 'Q'],
        'statistics': False,
        'plots': {'enabled': False}
    },
    'validation': {
        'enabled': False
    }
}

# 创建临时配置文件
config_file = tempfile.NamedTemporaryFile(
    mode='w', suffix='.json', delete=False
)
json.dump(config, config_file, indent=2)
config_file.close()

print("="*70)
print("SimulationEngine WENO3诊断测试")
print("="*70)
print(f"\n配置文件: {config_file.name}")
print(f"spatial_order: {config['solver']['spatial_order']}")
print(f"dt_max: {config['solver']['dt_max']}")
print()

try:
    # 初始化引擎
    engine = SimulationEngine(config_file.name)
    engine.initialize()

    # 检查求解器类型
    solver = engine.solver
    solver_class = solver.__class__.__name__

    print(f" 求解器类型: {solver_class}")

    if solver_class == 'GodunvFVMWENO3':
        print("   正确使用WENO3求解器！")
    else:
        print(f"   错误！应该是GodunvFVMWENO3，实际是{solver_class}")

    # 检查关键参数
    print(f"  weno_eps: {getattr(solver, 'weno_eps', 'N/A')}")
    print(f"  dt_max: {getattr(solver, 'dt_max', 'N/A')}")
    print(f"  order: {getattr(solver, 'order', 'N/A')}")

    # 运行30秒模拟
    print(f"\n开始模拟（30秒）...")
    engine.run()

    # 检查结果
    final_state = engine.solver
    mass_init = final_state.initial_mass
    mass_final = final_state._compute_total_mass()
    mass_error = abs(mass_final - mass_init) / mass_init * 100

    import numpy as np
    h = final_state.h
    Q = final_state.Q
    h_safe = np.maximum(h, final_state.eps_dry)
    A = h_safe * final_state.B
    u = Q / A
    Fr = np.abs(u) / np.sqrt(final_state.g * h_safe)
    Fr_upstream = Fr[0]

    print(f"\n最终结果:")
    print(f"  质量误差: {mass_error:.2f}%")
    print(f"  上游Fr: {Fr_upstream:.4f}")
    print(f"  模拟时间: {final_state.t:.1f}s")

    print(f"\n验证:")
    if mass_error < 10.0:
        print(f"   质量守恒良好")
    else:
        print(f"   质量守恒差")

    if Fr_upstream > 0.9:
        print(f"   上游超临界维持")
    else:
        print(f"   上游超临界丢失")

    print("="*70)

finally:
    # 清理
    Path(config_file.name).unlink(missing_ok=True)
