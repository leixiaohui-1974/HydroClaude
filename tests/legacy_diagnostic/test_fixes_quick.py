#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
快速测试修复后的求解器

对比修复前后的精度改进
"""

import sys
import os
import numpy as np

sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from solvers.single_canal_solver import SingleCanalSolver
from solvers.gate import SluiceGate

print("="*80)
print("修复后的求解器快速测试")
print("="*80)
print()

# 三闸门场景
total_length = 10000.0
structures = [
    SluiceGate(position=2500.0, width=10.0, opening=4.5),
    SluiceGate(position=5000.0, width=10.0, opening=4.0),  # 最小开度
    SluiceGate(position=7500.0, width=10.0, opening=5.0),
]

Q_target = 10.0

# 测试1: 均匀网格（基准）
print("测试1: 均匀网格 (301点) - 基准")
print("-" * 80)
solver1 = SingleCanalSolver(
    total_length=total_length,
    structures=structures,
    nx_total=301,
    method='preissmann'
)

solver1.reset_with_steady_state(Q_target)
result1 = solver1.solve_steady_state(
    Q_target=Q_target,
    max_iterations=3000,
    convergence_tol=0.001,
    check_interval=500,
    verbose=True
)

gate_flows_1 = solver1.get_gate_flows()
errors_1 = [abs(gf - Q_target) / Q_target * 100 for gf in gate_flows_1]
max_error_1 = max(errors_1)

print(f"\n结果:")
print(f"  最大误差: {max_error_1:.4f}%")
print(f"  收敛状态: {'✓' if result1['converged'] else '✗'}")
print(f"  迭代次数: {result1['iterations']}")
print()

# 测试2: 自适应网格 dx=3m
print("="*80)
print("测试2: 自适应网格 (dx=3m, ~688点)")
print("-" * 80)
solver2 = SingleCanalSolver(
    total_length=total_length,
    structures=structures,
    nx_total=301,
    use_adaptive_grid=True,
    dx_fine=3.0,
    dx_coarse=33.0,
    refinement_radius=200.0,
    method='preissmann'
)

solver2.reset_with_steady_state(Q_target)
result2 = solver2.solve_steady_state(
    Q_target=Q_target,
    max_iterations=5000,
    convergence_tol=0.001,
    check_interval=500,
    verbose=True
)

gate_flows_2 = solver2.get_gate_flows()
errors_2 = [abs(gf - Q_target) / Q_target * 100 for gf in gate_flows_2]
max_error_2 = max(errors_2)

print(f"\n结果:")
print(f"  最大误差: {max_error_2:.4f}%")
print(f"  收敛状态: {'✓' if result2['converged'] else '✗'}")
print(f"  迭代次数: {result2['iterations']}")
print()

# 测试3: 自适应网格 dx=1m（极精细）
print("="*80)
print("测试3: 自适应网格 (dx=1m, ~1459点) - 极精细")
print("-" * 80)
solver3 = SingleCanalSolver(
    total_length=total_length,
    structures=structures,
    nx_total=301,
    use_adaptive_grid=True,
    dx_fine=1.0,
    dx_coarse=40.0,
    refinement_radius=200.0,
    method='preissmann'
)

solver3.reset_with_steady_state(Q_target)
result3 = solver3.solve_steady_state(
    Q_target=Q_target,
    max_iterations=5000,
    convergence_tol=0.0005,
    check_interval=500,
    verbose=True
)

gate_flows_3 = solver3.get_gate_flows()
errors_3 = [abs(gf - Q_target) / Q_target * 100 for gf in gate_flows_3]
max_error_3 = max(errors_3)

print(f"\n结果:")
print(f"  最大误差: {max_error_3:.4f}%")
print(f"  收敛状态: {'✓' if result3['converged'] else '✗'}")
print(f"  迭代次数: {result3['iterations']}")
print()

# 对比报告
print("="*80)
print("修复效果对比")
print("="*80)
print()
print("修复前的测试结果（历史数据）：")
print("  均匀301点:   5.52%误差, 5000次未收敛")
print("  自适应dx=3m: 3.64%误差, 7500次未收敛")
print("  自适应dx=1m: 2.91%误差, 15000次未收敛")
print()
print("修复后的测试结果（本次）：")
print(f"  均匀301点:   {max_error_1:.2f}%误差, {result1['iterations']}次{'收敛' if result1['converged'] else '未收敛'}")
print(f"  自适应dx=3m: {max_error_2:.2f}%误差, {result2['iterations']}次{'收敛' if result2['converged'] else '未收敛'}")
print(f"  自适应dx=1m: {max_error_3:.2f}%误差, {result3['iterations']}次{'收敛' if result3['converged'] else '未收敛'}")
print()
print("改进倍数：")
print(f"  均匀301点:   {5.52/max_error_1:.2f}x精度提升")
print(f"  自适应dx=3m: {3.64/max_error_2:.2f}x精度提升")
print(f"  自适应dx=1m: {2.91/max_error_3:.2f}x精度提升")
print()

# 判断是否达到目标
if max_error_3 < 0.5:
    print("✅ ✅ ✅ 达到阶段1目标（<0.5%）！")
elif max_error_3 < 1.0:
    print("⚠️  接近阶段1目标，还需小幅改进")
else:
    print("❌ 未达到阶段1目标，需要进一步优化")

print()
print("="*80)
