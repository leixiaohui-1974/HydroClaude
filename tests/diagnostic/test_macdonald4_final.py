#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
MacDonald Test 4简化测试 - 终极诊断

完全复制pytest配置但简化输出
日期: 2025-10-29
"""

import sys
import os
sys.path.insert(0, os.path.dirname(__file__))

import json
import tempfile
from pathlib import Path
from engine.simulation_engine import SimulationEngine
import numpy as np

# 完全复制pytest的Test 4配置
L = 1000.0
B = 10.0
S0 = 0.0
n = 0.0
h_upstream = 0.7
Q = 20.0
h_downstream = 2.8
n_cells = 200
dx = L / n_cells
g = 9.81

# 线性初始条件
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

# 创建配置（完全一致）
config = {
    'project': {
        'name': 'MacDonald Test 4 - Final Diagnosis',
        'description': 'P1测试：水跃激波传播',
        'author': 'Debug',
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
        'left': {'type': 'supercritical', 'h': h_upstream, 'Q': Q},
        'right': {'type': 'h', 'value': h_downstream}
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
        'end_time': 150.0,  # 完整运行
        'max_steps': 100000,
        'output_interval': 15.0
    },
    'output': {
        'directory': '/tmp/test_macdonald4_final',
        'formats': ['json'],
        'variables': ['h', 'Q', 'u'],
        'statistics': True,
        'plots': {'enabled': False}
    },
    'validation': {
        'enabled': False
    }
}

# 创建临时配置文件
config_file = tempfile.NamedTemporaryFile(
    mode='w', suffix='.json', delete=False, encoding='utf-8'
)
json.dump(config, config_file, indent=2, ensure_ascii=False)
config_file.close()
config_file_path = Path(config_file.name)

print("="*70)
print("MacDonald Test 4 - 终极诊断")
print("="*70)
print(f"配置: spatial_order=3 (WENO3), dt_max=0.5")
print()

try:
    # 运行仿真
    engine = SimulationEngine(str(config_file_path))
    engine.initialize()

    # ✅ 验证使用了WENO3求解器
    solver_class_name = engine.solver.__class__.__name__
    print(f"✓ 求解器类型: {solver_class_name}")

    if solver_class_name != 'GodunvFVMWENO3':
        print(f"❌ 错误！应该使用WENO3，实际使用{solver_class_name}")
        sys.exit(1)

    print(f"✓ dt_max: {engine.solver.dt_max}")
    print(f"✓ weno_eps: {engine.solver.weno_eps}")
    print()

    engine.run()

    # 获取最终结果
    solver = engine.solver
    t_final = solver.t

    # 计算质量误差
    final_mass = solver._compute_total_mass()
    initial_mass = solver.initial_mass
    mass_error_percent = abs((final_mass - initial_mass) / initial_mass * 100)
    h_final = solver.h.copy()
    Q_final = solver.Q.copy()
    u_final = Q_final / (h_final * B)

    # Froude数
    h_safe = np.maximum(h_final, solver.eps_dry)
    Fr = np.abs(u_final) / np.sqrt(g * h_safe)
    Fr_upstream_avg = np.mean(Fr[:10])

    print(f"\n最终结果:")
    print(f"  模拟时间: {t_final:.1f}s / 150.0s")
    print(f"  质量误差: {mass_error_percent:.2f}%")
    print(f"  上游Fr: {Fr_upstream_avg:.4f}")

    print(f"\n验证:")
    if mass_error_percent < 10.0:
        print(f"  ✅ 质量守恒良好")
    else:
        print(f"  ❌ 质量守恒差")

    if Fr_upstream_avg > 0.8:
        print(f"  ✅ 上游超临界维持")
    else:
        print(f"  ❌ 上游超临界丢失")

    print("="*70)

finally:
    # 清理
    ic_file_path.unlink(missing_ok=True)
    config_file_path.unlink(missing_ok=True)
