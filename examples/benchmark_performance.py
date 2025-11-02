#!/usr/bin/env python3
"""
HydroClaude 性能基准测试

测试不同网格规模的计算性能，为实际应用提供参考

作者: HydroClaude Team
日期: 2025-11-02
版本: v1.0
"""

import numpy as np
import time
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).parent.parent))

from solvers.water_temperature import WaterTemperatureSolver
from solvers.dissolved_oxygen import DissolvedOxygenSolver
from solvers.ice_cover import IceCoverSolver
from solvers.nutrients import NutrientsSolver
from solvers.phytoplankton import PhytoplanktonSolver

print("=" * 70)
print("HydroClaude 性能基准测试")
print("=" * 70)
print()

# 测试配置
test_configs = [
    {"n_cells": 50, "desc": "小规模 (5km, 50网格)"},
    {"n_cells": 100, "desc": "中规模 (10km, 100网格)"},
    {"n_cells": 200, "desc": "大规模 (20km, 200网格)"},
    {"n_cells": 500, "desc": "超大规模 (50km, 500网格)"},
]

n_steps = 100  # 运行100步
dt = 3600.0  # 1小时步长

results = []

for config in test_configs:
    n_cells = config["n_cells"]
    desc = config["desc"]

    print(f"[{desc}]")
    print("-" * 70)

    # 初始化
    dx = 100.0
    u = np.full(n_cells, 0.3)
    h = np.full(n_cells, 2.5)
    manning_n = np.full(n_cells, 0.03)

    # 创建求解器
    temp_solver = WaterTemperatureSolver(n_cells, dx, use_numba=False)
    temp_solver.T = np.full(n_cells, 20.0)

    do_solver = DissolvedOxygenSolver(n_cells, dx, kd_20=0.15, SOD_20=1.0, use_numba=False)
    do_solver.DO = np.full(n_cells, 8.0)
    do_solver.BOD = np.full(n_cells, 3.0)

    ice_solver = IceCoverSolver(n_cells=n_cells)

    nutrients_solver = NutrientsSolver(n_cells, dx, use_numba=False)
    nutrients_solver.NH4 = np.full(n_cells, 0.3)
    nutrients_solver.NO3 = np.full(n_cells, 1.2)
    nutrients_solver.PO4 = np.full(n_cells, 0.08)
    nutrients_solver.OrgN = np.full(n_cells, 0.5)
    nutrients_solver.OrgP = np.full(n_cells, 0.05)

    algae_solver = PhytoplanktonSolver(n_cells, dx, use_numba=False)
    algae_solver.Chla = np.full(n_cells, 15.0)

    # 气象参数
    T_air = 25.0
    I_0 = np.full(n_cells, 200.0)
    wind_speed = 3.0
    relative_humidity = 0.7

    # 基准测试
    print(f"运行 {n_steps} 步...")
    start_time = time.time()

    for step in range(n_steps):
        # 水温
        T = temp_solver.step(dt, u, h, T_air, I_0.mean(), wind_speed, relative_humidity)

        # 冰盖
        ice_state = ice_solver.step(dt, T_air, T)

        # 营养盐
        nutrients_state = nutrients_solver.step(dt, u, h, T, do_solver.DO)

        # 藻类
        algae_state = algae_solver.step(
            dt, u, h, T, I_0,
            nutrients_solver.NH4,
            nutrients_solver.NO3,
            nutrients_solver.PO4
        )

        # DO
        do_state = do_solver.step(dt, u, h, T, manning_n)

        # 耦合
        dt_day = dt / 86400.0
        do_solver.DO += algae_state['DO_production'] * dt_day
        do_solver.DO = np.maximum(do_solver.DO, 0.0)

        nutrients_solver.NH4 -= algae_state['NH4_uptake'] * dt_day
        nutrients_solver.NH4 = np.maximum(nutrients_solver.NH4, 0.0)

    end_time = time.time()
    elapsed_time = end_time - start_time

    # 性能指标
    time_per_step = elapsed_time / n_steps * 1000  # ms
    simulated_time = n_steps * dt / 86400.0  # days
    speedup = simulated_time / (elapsed_time / 86400.0)  # 倍速

    print(f"✓ 完成!")
    print(f"  总时间: {elapsed_time:.2f} s")
    print(f"  每步时间: {time_per_step:.2f} ms")
    print(f"  模拟时间: {simulated_time:.1f} 天")
    print(f"  加速比: {speedup:.1f}x (模拟时间/实际时间)")
    print()

    results.append({
        'n_cells': n_cells,
        'desc': desc,
        'elapsed_time': elapsed_time,
        'time_per_step': time_per_step,
        'speedup': speedup
    })

# 总结
print("=" * 70)
print("性能总结")
print("=" * 70)
print()

print(f"{'规模':<30} {'网格数':<10} {'每步耗时':<15} {'加速比':<10}")
print("-" * 70)
for r in results:
    print(f"{r['desc']:<30} {r['n_cells']:<10} {r['time_per_step']:<15.2f}ms {r['speedup']:<10.1f}x")
print()

# 性能建议
print("性能建议:")
print("-" * 70)
print("1. 小规模 (< 100网格): 适合快速原型和教学演示")
print("2. 中规模 (100-200网格): 适合一般河流模拟 (10-20 km)")
print("3. 大规模 (200-500网格): 适合长河道模拟 (20-50 km)")
print("4. 超大规模 (> 500网格): 建议使用Numba加速或并行计算")
print()

# 优化建议
print("优化建议:")
print("-" * 70)
print("✓ 启用Numba加速: use_numba=True (预计提速2-5倍)")
print("✓ 使用自适应时间步长: 在稳定区域使用更大的dt")
print("✓ 多核并行: 使用MPI进行空间分解")
print("✓ GPU加速: 使用CuPy/JAX进行GPU计算")
print()

print("=" * 70)
print("基准测试完成!")
print("=" * 70)
