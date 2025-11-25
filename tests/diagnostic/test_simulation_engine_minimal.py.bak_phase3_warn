#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
最小化SimulationEngine测试 - 去除所有输出逻辑

只保留纯模拟循环，找出真正的问题
日期: 2025-10-29
"""

import sys
import os
sys.path.insert(0, os.path.dirname(__file__))

import json
import tempfile
from pathlib import Path
from engine.model_builder import ModelBuilder
import numpy as np

# Test 4配置
L = 1000.0
B = 10.0
h_upstream = 0.7
Q = 20.0
h_downstream = 2.8
n_cells = 200
dx = L / n_cells

# 创建IC文件
x = np.linspace(dx/2, L - dx/2, n_cells)
h_init = np.linspace(h_upstream, h_downstream, n_cells)
Q_init = np.ones(n_cells) * Q

ic_data = np.column_stack([x, h_init, Q_init])
ic_file = tempfile.NamedTemporaryFile(mode='w', suffix='.csv', delete=False)
ic_file.write('x,h,Q\n')
np.savetxt(ic_file, ic_data, delimiter=',')
ic_file.close()
ic_file_path = Path(ic_file.name)

config = {
    'project': {'name': 'Minimal Test'},
    'geometry': {
        'type': 'uniform',
        'channel_width': B,
        'channel_length': L,
        'bottom_slope': 0.0,
        'manning_n': 0.0
    },
    'mesh': {'n_cells': n_cells},
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
        'end_time': 50.0,
        'max_steps': 10000,
        'output_interval': 50.0  # 只在最后输出
    },
    'output': {
        'directory': '/tmp/minimal_test',
        'formats': [],
        'variables': [],
        'statistics': False,
        'plots': {'enabled': False}
    },
    'validation': {'enabled': False}
}

# 保存配置
config_file = tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False)
json.dump(config, config_file, indent=2)
config_file.close()

print("="*70)
print("最小化SimulationEngine测试")
print("="*70)

try:
    # 通过ModelBuilder创建求解器（模拟SimulationEngine的初始化）
    builder = ModelBuilder.from_config_file(config_file.name)
    solver = builder.build_solver()

    print(f" 求解器类型: {solver.__class__.__name__}")
    print(f" dt_max: {solver.dt_max}")
    print()

    # 纯模拟循环（去除所有SimulationEngine的额外逻辑）
    print("开始纯模拟循环（无输出/统计）...")
    t_end = 50.0
    step = 0

    while solver.t < t_end and step < 10000:
        # ️ 关键：直接调用step()，不传dt（模拟SimulationEngine）
        solver.step()
        step += 1

        # 简单进度（每秒报告）
        if step % 50 == 0:
            print(f"  步{step}: t={solver.t:.2f}s, dt={solver.dt:.6f}")

    print(f"\n最终:")
    print(f"  模拟时间: {solver.t:.2f}s / {t_end}s")
    print(f"  总步数: {step}")

    if solver.t >= t_end * 0.9:
        print(f"   成功运行")
    else:
        print(f"   提前停止")

finally:
    ic_file_path.unlink(missing_ok=True)
    Path(config_file.name).unlink(missing_ok=True)

print("="*70)
