#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
对比两种step()调用方式

1. step() - 让solver内部计算dt
2. dt = compute_dt(); step(dt) - 显式传递dt

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

# Test 4参数
L = 1000.0
B = 10.0
h_upstream = 0.7
Q_val = 20.0
h_downstream = 2.8
n_cells = 200
dx = L / n_cells

# 创建IC文件
x = np.linspace(dx/2, L - dx/2, n_cells)
h_init = np.linspace(h_upstream, h_downstream, n_cells)
Q_init = np.ones(n_cells) * Q_val

ic_data = np.column_stack([x, h_init, Q_init])
ic_file = tempfile.NamedTemporaryFile(mode='w', suffix='.csv', delete=False)
ic_file.write('x,h,Q\n')
np.savetxt(ic_file, ic_data, delimiter=',')
ic_file.close()
ic_file_path = Path(ic_file.name)

config = {
    'project': {'name': 'Test'},
    'geometry': {'type': 'uniform', 'channel_width': B, 'channel_length': L, 'bottom_slope': 0.0, 'manning_n': 0.0},
    'mesh': {'n_cells': n_cells},
    'initial_conditions': {'type': 'from_file', 'file': str(ic_file_path)},
    'boundary_conditions': {
        'left': {'type': 'supercritical', 'h': h_upstream, 'Q': Q_val},
        'right': {'type': 'h', 'value': h_downstream}
    },
    'solver': {
        'type': 'godunov_fvm', 'spatial_order': 3, 'riemann_solver': 'hll',
        'use_numba': True, 'cfl': 0.4, 'eps_dry': 1e-6, 'weno_epsilon': 1e-6,
        'well_balanced': False, 'dt_max': 0.5
    },
    'simulation': {'start_time': 0.0, 'end_time': 50.0, 'max_steps': 10000, 'output_interval': 50.0},
    'output': {'directory': '/tmp/test', 'formats': [], 'variables': [], 'statistics': False, 'plots': {'enabled': False}},
    'validation': {'enabled': False}
}

config_file = tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False)
json.dump(config, config_file, indent=2)
config_file.close()

print("="*70)
print("对比两种step()调用方式")
print("="*70)

# ========== 方式1: step()不传dt（ModelBuilder方式，会失败）==========
print("\n方式1: solver.step() - 不传dt")
builder1 = ModelBuilder.from_config_file(config_file.name)
solver1 = builder1.build_solver()

step = 0
while solver1.t < 40.0 and step < 500:
    solver1.step()  # 不传dt
    step += 1
    if step % 50 == 0:
        print(f"  步{step}: t={solver1.t:.2f}s, dt={solver1.dt:.6f}")

print(f"结果: t={solver1.t:.2f}s, 步数={step}")

# ========== 方式2: 显式compute_dt + step(dt)（成功方式）==========
print("\n方式2: dt=compute_dt(); step(dt) - 显式传dt")
builder2 = ModelBuilder.from_config_file(config_file.name)
solver2 = builder2.build_solver()

step = 0
while solver2.t < 40.0 and step < 500:
    dt = solver2.compute_dt()  # 显式计算
    solver2.step(dt)  # 传递dt
    step += 1
    if step % 50 == 0:
        print(f"  步{step}: t={solver2.t:.2f}s, dt={dt:.6f}")

print(f"结果: t={solver2.t:.2f}s, 步数={step}")

# 清理
ic_file_path.unlink(missing_ok=True)
Path(config_file.name).unlink(missing_ok=True)

print("\n" + "="*70)
