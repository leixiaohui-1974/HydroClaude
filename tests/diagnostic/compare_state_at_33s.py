#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
在33秒时对比两种方法的完整状态

找出为什么同样的初始化产生不同的运行结果
日期: 2025-10-29
"""

import sys
import warnings
warnings.filterwarnings("ignore")
import os
sys.path.insert(0, os.path.dirname(__file__))

import json
import tempfile
from pathlib import Path
from engine.model_builder import ModelBuilder
import numpy as np
try:
    from solvers.godunov_fvm_weno3 import GodunvFVMWENO3
except ImportError as e:
    print(f"Import error: {e}")
    print("Make sure project root is in sys.path")
    sys.exit(1)


# Test 4参数
L = 1000.0
B = 10.0
h_upstream = 0.7
Q_val = 20.0
h_downstream = 2.8
n_cells = 200
g = 9.81

print("="*70)
print("在33秒时对比状态")
print("="*70)

# ========== 方法1: 直接创建（成功）==========
print("\n方法1: 直接创建WENO3")
h_init1 = np.linspace(h_upstream, h_downstream, n_cells)
Q_init1 = np.ones(n_cells) * Q_val

solver1 = GodunvFVMWENO3(
    width=B, length=L, n_cells=n_cells,
    manning_n=0.0, slope=0.0, g=g,
    cfl=0.4, eps_dry=1e-6, weno_epsilon=1e-6,
    riemann_solver='hll', use_numba=True, dt_max=0.5
)

bc_left = {'type': 'supercritical', 'h': h_upstream, 'Q': Q_val}
bc_right = {'type': 'h', 'value': h_downstream}  # 修复：使用正确的BC格式
solver1.initialize(h_init1, Q_init1, bc_left, bc_right)

# 运行到33秒
while solver1.t < 33.0:
    solver1.step()

print(f"  t={solver1.t:.2f}s")
print(f"  h范围: [{np.min(solver1.h):.6f}, {np.max(solver1.h):.6f}]")
print(f"  Q范围: [{np.min(solver1.Q):.6f}, {np.max(solver1.Q):.6f}]")
print(f"  前5个h: {solver1.h[:5]}")
print(f"  后5个h: {solver1.h[-5:]}")

# ========== 方法2: ModelBuilder（失败）==========
print("\n方法2: ModelBuilder")

# 创建IC文件
dx = L / n_cells
x = np.linspace(dx/2, L - dx/2, n_cells)
h_init2 = np.linspace(h_upstream, h_downstream, n_cells)
Q_init2 = np.ones(n_cells) * Q_val

ic_data = np.column_stack([x, h_init2, Q_init2])
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
    'simulation': {'start_time': 0.0, 'end_time': 50.0, 'max_steps': 1000, 'output_interval': 50.0},
    'output': {'directory': '/tmp/test', 'formats': [], 'variables': [], 'statistics': False, 'plots': {'enabled': False}},
    'validation': {'enabled': False}
}

config_file = tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False)
json.dump(config, config_file, indent=2)
config_file.close()

builder = ModelBuilder.from_config_file(config_file.name)
solver2 = builder.build_solver()

# 运行到33秒
while solver2.t < 33.0:
    solver2.step()

print(f"  t={solver2.t:.2f}s")
print(f"  h范围: [{np.min(solver2.h):.6f}, {np.max(solver2.h):.6f}]")
print(f"  Q范围: [{np.min(solver2.Q):.6f}, {np.max(solver2.Q):.6f}]")
print(f"  前5个h: {solver2.h[:5]}")
print(f"  后5个h: {solver2.h[-5:]}")

# ========== 对比 ==========
print("\n在33秒时的状态差异:")
h_diff = solver2.h - solver1.h
Q_diff = solver2.Q - solver1.Q

print(f"  h差异: max={np.max(np.abs(h_diff)):.2e}, mean={np.mean(np.abs(h_diff)):.2e}")
print(f"  Q差异: max={np.max(np.abs(Q_diff)):.2e}, mean={np.mean(np.abs(Q_diff)):.2e}")

if np.max(np.abs(h_diff)) > 1e-6:
    print(f"  ️  状态已经出现显著差异！")
    diff_indices = np.where(np.abs(h_diff) > 1e-6)[0]
    print(f"  h不同的位置数量: {len(diff_indices)}")
    for idx in diff_indices[:5]:
        print(f"    索引{idx}: direct={solver1.h[idx]:.10f}, builder={solver2.h[idx]:.10f}, diff={h_diff[idx]:.2e}")

# 继续运行看谁先停滞
print("\n继续运行到36秒:")
print("方法1（直接）:")
count1 = 0
while solver1.t < 36.0 and count1 < 100:
    dt1 = solver1.compute_dt()
    if dt1 < 1e-6:
        print(f"   t={solver1.t:.3f}s时dt变小: {dt1:.2e}")
        break
    solver1.step(dt1)
    count1 += 1
print(f"  最终t={solver1.t:.2f}s, 步数={count1}")

print("方法2（ModelBuilder）:")
count2 = 0
while solver2.t < 36.0 and count2 < 100:
    dt2 = solver2.compute_dt()
    if dt2 < 1e-6:
        print(f"   t={solver2.t:.3f}s时dt变小: {dt2:.2e}")
        break
    solver2.step(dt2)
    count2 += 1
print(f"  最终t={solver2.t:.2f}s, 步数={count2}")

# 清理
ic_file_path.unlink(missing_ok=True)
Path(config_file.name).unlink(missing_ok=True)

print("\n" + "="*70)
