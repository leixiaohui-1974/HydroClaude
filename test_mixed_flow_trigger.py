#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""测试 Mixed Flow 是否被触发"""

import sys
import os
import numpy as np

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from integration.hec_ras_adapter import extract_hecras_result_summary
from solvers.steady_profile_solver import SteadyProfileSolver
from physics.cross_section import CrossSection

# 加载 HEC-RAS 数据
hecras = extract_hecras_result_summary(
    "reports/hec_ras_example_project/Mixed Flow Regime Channel/MIXED.p01.hdf"
)

# 提取第一个 profile
profile_idx = 0
profile_name = hecras['profile_names'][profile_idx]
Q = hecras['profiles'][profile_idx]['Q']
h_ds = hecras['profiles'][profile_idx]['depth'][-1]

print(f"Profile: {profile_name}")
print(f"Q = {Q:.3f} m3/s")
print(f"Downstream h = {h_ds:.3f} m")

# 构建 cross sections
xs_list = []
for i, xs_data in enumerate(hecras['cross_sections']):
    xs = CrossSection(
        station=xs_data['station'],
        elevation=xs_data['elevation'],
        roughness=xs_data.get('roughness', 0.015)
    )
    xs_list.append(xs)

# 创建求解器
solver = SteadyProfileSolver(
    length=hecras['total_length'],
    cross_sections=xs_list,
    bed_elevations=hecras['bed_elevations'],
    reach_lengths=hecras['reach_lengths'],
    contraction_coefs=hecras.get('contraction_coefs'),
    expansion_coefs=hecras.get('expansion_coefs'),
)

# 运行求解
result = solver.solve_standard_step_variable_xs(
    Q=Q,
    h_downstream=h_ds,
    n_xs=len(xs_list)
)

print(f"\nMixed flow detected: {result.get('mixed_flow', False)}")
print(f"Froude numbers: {result['froude'][:10]}")

# 检查是否有超临界流
supercritical_count = np.sum(result['froude'] > 1.0)
print(f"Supercritical XS count: {supercritical_count}/{len(result['froude'])}")

# 检查坡度
bed = result['bed']
x = result['x']
for i in range(min(5, len(bed)-1)):
    dx = x[i+1] - x[i]
    if dx > 0:
        S0 = (bed[i] - bed[i+1]) / dx
        print(f"XS {i}: S0 = {S0:.6f}")
