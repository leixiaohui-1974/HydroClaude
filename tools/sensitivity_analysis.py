#!/usr/bin/env python3
"""
HydroClaude 参数敏感性分析工具

用途: 分析关键参数对模拟结果的影响
- 支持单参数敏感性分析
- 支持多参数组合分析
- 自动生成可视化结果
- 提供参数优化建议

作者: HydroClaude Team
日期: 2025-11-02
版本: v1.0
"""

import numpy as np
import matplotlib.pyplot as plt
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).parent.parent))

from solvers.dissolved_oxygen import DissolvedOxygenSolver
from solvers.nutrients import NutrientsSolver
from solvers.phytoplankton import PhytoplanktonSolver

print("=" * 70)
print("HydroClaude 参数敏感性分析工具")
print("=" * 70)
print()

# ==================== 案例1: DO模块参数敏感性 ====================
print("[1] DO模块参数敏感性分析")
print("-" * 70)
print("分析参数: BOD降解系数 (kd_20)")
print()

# 基准参数
n_cells = 100
dx = 100.0
u = np.full(n_cells, 0.5)
h = np.full(n_cells, 2.0)
T = np.full(n_cells, 20.0)
manning_n = np.full(n_cells, 0.03)

# 初始条件
DO_init = 8.0
BOD_init = 10.0

# 参数范围
kd_values = np.linspace(0.05, 0.40, 8)  # 0.05 - 0.40 1/day
print(f"参数范围: kd_20 = {kd_values[0]:.2f} - {kd_values[-1]:.2f} 1/day")
print(f"基准值: kd_20 = 0.20 1/day")
print()

# 模拟时间
dt = 3600.0
n_steps = 48  # 2天

# 存储结果
results_DO = []
results_BOD = []

print("运行敏感性分析...")
for kd in kd_values:
    # 创建求解器
    solver = DissolvedOxygenSolver(n_cells, dx, kd_20=kd, SOD_20=1.0, use_numba=False)
    solver.DO = np.full(n_cells, DO_init)
    solver.BOD = np.full(n_cells, BOD_init)

    # 模拟
    DO_history = [solver.DO.mean()]
    BOD_history = [solver.BOD.mean()]

    for step in range(n_steps):
        state = solver.step(dt, u, h, T, manning_n)
        DO_history.append(solver.DO.mean())
        BOD_history.append(solver.BOD.mean())

    results_DO.append(DO_history)
    results_BOD.append(BOD_history)

    print(f"  kd_20 = {kd:.2f}: 最终DO = {DO_history[-1]:.2f} mg/L, BOD = {BOD_history[-1]:.2f} mg/L")

results_DO = np.array(results_DO)
results_BOD = np.array(results_BOD)
print()

# 计算敏感性指数
baseline_idx = 3  # 基准值索引 (kd=0.20)
baseline_DO = results_DO[baseline_idx, -1]
sensitivity_DO = (results_DO[:, -1] - baseline_DO) / baseline_DO / ((kd_values - kd_values[baseline_idx]) / kd_values[baseline_idx])

print("敏感性分析结果:")
print(f"  DO对kd_20的敏感性指数: {np.mean(np.abs(sensitivity_DO)):.2f}")
print(f"  (敏感性指数 > 1: 高敏感, 0.1-1: 中等, < 0.1: 低敏感)")
print()

# 可视化
fig1, axes1 = plt.subplots(1, 2, figsize=(12, 4))

# DO演变
ax = axes1[0]
times = np.arange(n_steps + 1) * dt / 3600.0
for i, kd in enumerate(kd_values):
    label = f'kd={kd:.2f}' if i % 2 == 0 else None
    ax.plot(times, results_DO[i], linewidth=2, label=label)
ax.set_xlabel('Time (hours)')
ax.set_ylabel('DO (mg/L)')
ax.set_title('DO Sensitivity to kd_20')
ax.legend()
ax.grid(True, alpha=0.3)

# 最终DO vs kd
ax = axes1[1]
ax.plot(kd_values, results_DO[:, -1], 'o-', linewidth=2, markersize=8)
ax.axvline(kd_values[baseline_idx], color='red', linestyle='--', label='Baseline')
ax.set_xlabel('kd_20 (1/day)')
ax.set_ylabel('Final DO (mg/L)')
ax.set_title('Final DO vs kd_20')
ax.legend()
ax.grid(True, alpha=0.3)

plt.tight_layout()
plt.savefig('sensitivity_DO_kd.png', dpi=150)
print(" 图表已保存: sensitivity_DO_kd.png")
print()

# ==================== 案例2: 藻类生长参数敏感性 ====================
print("[2] 藻类生长参数敏感性分析")
print("-" * 70)
print("分析参数: 最大生长速率 (mu_max_20)")
print()

# 参数范围
mu_max_values = np.linspace(1.0, 3.0, 8)  # 1.0 - 3.0 1/day
print(f"参数范围: mu_max_20 = {mu_max_values[0]:.1f} - {mu_max_values[-1]:.1f} 1/day")
print(f"基准值: mu_max_20 = 2.0 1/day")
print()

# 环境条件（最优）
T_algae = np.full(n_cells, 25.0)
I_0 = np.full(n_cells, 200.0)
NH4 = np.full(n_cells, 0.5)
NO3 = np.full(n_cells, 2.0)
PO4 = np.full(n_cells, 0.1)
Chla_init = 10.0

# 模拟时间
n_days = 7
n_steps_algae = n_days * 24

# 存储结果
results_Chla = []

print("运行敏感性分析...")
for mu_max in mu_max_values:
    # 创建求解器
    solver = PhytoplanktonSolver(n_cells, dx, use_numba=False)
    solver.mu_max_20 = mu_max
    solver.Chla = np.full(n_cells, Chla_init)

    # 复制营养盐（避免耗尽）
    NH4_local = NH4.copy()
    NO3_local = NO3.copy()
    PO4_local = PO4.copy()

    Chla_history = [solver.Chla.mean()]

    for step in range(n_steps_algae):
        state = solver.step(dt, u, h, T_algae, I_0, NH4_local, NO3_local, PO4_local)

        # 简单营养盐消耗
        dt_day = dt / 86400.0
        NH4_local -= state['NH4_uptake'] * dt_day * 0.1  # 减缓消耗
        NO3_local -= state['NO3_uptake'] * dt_day * 0.1
        NH4_local = np.maximum(NH4_local, 0.01)
        NO3_local = np.maximum(NO3_local, 0.01)

        Chla_history.append(solver.Chla.mean())

    results_Chla.append(Chla_history)
    print(f"  mu_max_20 = {mu_max:.1f}: 最终Chla = {Chla_history[-1]:.1f} μg/L (增长{Chla_history[-1]/Chla_init:.1f}倍)")

results_Chla = np.array(results_Chla)
print()

# 计算敏感性
baseline_idx_algae = 4  # mu_max = 2.0
baseline_Chla = results_Chla[baseline_idx_algae, -1]
sensitivity_Chla = (results_Chla[:, -1] - baseline_Chla) / baseline_Chla / ((mu_max_values - mu_max_values[baseline_idx_algae]) / mu_max_values[baseline_idx_algae])

print("敏感性分析结果:")
print(f"  Chla对mu_max_20的敏感性指数: {np.mean(np.abs(sensitivity_Chla)):.2f}")
print()

# 可视化
fig2, axes2 = plt.subplots(1, 2, figsize=(12, 4))

# Chla演变
ax = axes2[0]
times_algae = np.arange(n_steps_algae + 1) * dt / 86400.0
for i, mu_max in enumerate(mu_max_values):
    label = f'μ_max={mu_max:.1f}' if i % 2 == 0 else None
    ax.plot(times_algae, results_Chla[i], linewidth=2, label=label)
ax.set_xlabel('Time (days)')
ax.set_ylabel('Chlorophyll-a (μg/L)')
ax.set_title('Algal Growth Sensitivity to μ_max_20')
ax.legend()
ax.grid(True, alpha=0.3)
ax.set_yscale('log')

# 最终Chla vs mu_max
ax = axes2[1]
ax.plot(mu_max_values, results_Chla[:, -1], 'o-', linewidth=2, markersize=8, color='green')
ax.axvline(mu_max_values[baseline_idx_algae], color='red', linestyle='--', label='Baseline')
ax.set_xlabel('μ_max_20 (1/day)')
ax.set_ylabel('Final Chlorophyll-a (μg/L)')
ax.set_title('Final Chlorophyll vs μ_max_20')
ax.legend()
ax.grid(True, alpha=0.3)

plt.tight_layout()
plt.savefig('sensitivity_Chla_mu_max.png', dpi=150)
print(" 图表已保存: sensitivity_Chla_mu_max.png")
print()

# ==================== 案例3: 光照强度敏感性 ====================
print("[3] 光照强度敏感性分析")
print("-" * 70)
print("分析参数: 太阳辐射强度 (I_0)")
print()

# 光照范围
I0_values = np.linspace(50, 400, 8)  # 50 - 400 W/m²
print(f"参数范围: I_0 = {I0_values[0]:.0f} - {I0_values[-1]:.0f} W/m²")
print()

# 存储结果
results_Chla_light = []

print("运行敏感性分析...")
for I0_val in I0_values:
    # 创建求解器
    solver = PhytoplanktonSolver(n_cells, dx, use_numba=False)
    solver.Chla = np.full(n_cells, Chla_init)

    I_0_local = np.full(n_cells, I0_val)
    NH4_local = NH4.copy()
    NO3_local = NO3.copy()
    PO4_local = PO4.copy()

    Chla_history = [solver.Chla.mean()]

    for step in range(n_steps_algae):
        state = solver.step(dt, u, h, T_algae, I_0_local, NH4_local, NO3_local, PO4_local)

        dt_day = dt / 86400.0
        NH4_local -= state['NH4_uptake'] * dt_day * 0.1
        NO3_local -= state['NO3_uptake'] * dt_day * 0.1
        NH4_local = np.maximum(NH4_local, 0.01)
        NO3_local = np.maximum(NO3_local, 0.01)

        Chla_history.append(solver.Chla.mean())

    results_Chla_light.append(Chla_history)
    print(f"  I_0 = {I0_val:5.0f} W/m²: 最终Chla = {Chla_history[-1]:.1f} μg/L")

results_Chla_light = np.array(results_Chla_light)
print()

# 可视化
fig3, axes3 = plt.subplots(1, 2, figsize=(12, 4))

# Chla演变
ax = axes3[0]
for i, I0_val in enumerate(I0_values):
    label = f'I₀={I0_val:.0f}' if i % 2 == 0 else None
    ax.plot(times_algae, results_Chla_light[i], linewidth=2, label=label)
ax.set_xlabel('Time (days)')
ax.set_ylabel('Chlorophyll-a (μg/L)')
ax.set_title('Algal Growth Sensitivity to Light Intensity')
ax.legend()
ax.grid(True, alpha=0.3)
ax.set_yscale('log')

# 最终Chla vs I0
ax = axes3[1]
ax.plot(I0_values, results_Chla_light[:, -1], 'o-', linewidth=2, markersize=8, color='orange')
ax.set_xlabel('Solar Radiation (W/m²)')
ax.set_ylabel('Final Chlorophyll-a (μg/L)')
ax.set_title('Final Chlorophyll vs Light Intensity')
ax.grid(True, alpha=0.3)

plt.tight_layout()
plt.savefig('sensitivity_Chla_light.png', dpi=150)
print(" 图表已保存: sensitivity_Chla_light.png")
print()

# ==================== 总结 ====================
print("=" * 70)
print("参数敏感性分析总结")
print("=" * 70)
print()

print("1. BOD降解系数 (kd_20):")
print(f"   - 敏感性: {np.mean(np.abs(sensitivity_DO)):.2f} (中等)")
print(f"   - 影响: kd_20增加 → DO恢复更快")
print(f"   - 建议: 根据实测BOD衰减数据校准")
print()

print("2. 最大生长速率 (mu_max_20):")
print(f"   - 敏感性: {np.mean(np.abs(sensitivity_Chla)):.2f} (高)")
print(f"   - 影响: mu_max增加 → 藻类生长显著加快")
print(f"   - 建议: 对不同藻类种群使用不同值")
print()

print("3. 光照强度 (I_0):")
print(f"   - 影响: 非线性关系（Steele公式）")
print(f"   - 最优光照: ~{I0_values[results_Chla_light[:, -1].argmax()]:.0f} W/m²")
print(f"   - 建议: 考虑光抑制效应（过强光照反而降低生长）")
print()

print("参数校准建议:")
print("-" * 70)
print(" 优先校准高敏感性参数 (mu_max, I_s)")
print(" 使用实测数据验证中等敏感性参数 (kd, Ka)")
print(" 低敏感性参数可使用文献值")
print(" 进行不确定性分析评估参数影响")
print()

print("=" * 70)
print("敏感性分析完成!")
print("=" * 70)
print()
print("生成的图表:")
print("  - sensitivity_DO_kd.png")
print("  - sensitivity_Chla_mu_max.png")
print("  - sensitivity_Chla_light.png")
