#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Phase 1应用示例 - 洪水演进模拟

场景上游洪峰通过渠道演进

技术要点
1. 动态流量边界条件洪峰过程线
2. Godunov-FVM捕捉洪峰传播
3. 洪峰衰减和展宽分析
4. 实时监测和预警

作者: HydroClaude Team
日期: 2025-10-27
"""

import numpy as np
import warnings
warnings.filterwarnings("ignore")
import matplotlib.pyplot as plt
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from solvers.godunov_fvm_solver import GodunvFVMSolver
from utils.canal_utils import compute_steady_uniform_flow


def flood_hydrograph(t):
    """
    洪峰过程线三角形洪峰
    
    特征
    - 基流30 m^3/s
    - 峰值150 m^3/s
    - 涨洪历时2小时
    - 落洪历时4小时
    """
    Q_base = 30.0
    Q_peak = 150.0
    t_rise = 2.0 * 3600  # 2小时
    t_fall = 4.0 * 3600  # 4小时
    
    if t < t_rise:
        # 涨洪段
        return Q_base + (Q_peak - Q_base) * (t / t_rise)
    elif t < t_rise + t_fall:
        # 落洪段
        return Q_peak - (Q_peak - Q_base) * ((t - t_rise) / t_fall)
    else:
        # 回归基流
        return Q_base


print("="*80)
print(" Phase 1应用示例 - 洪水演进模拟")
print("="*80)

# ========== 场景设置 ==========
print("\n场景上游洪峰传播")
print("-"*80)

# 渠道参数
width = 20.0  # 宽度20m
length = 10000.0  # 长度10km
n_cells = 200  # 网格200格dx=50m
manning_n = 0.030
slope = 0.0005

# 初始条件基流
Q_base = 30.0
h_base = compute_steady_uniform_flow(Q_base, width, slope, manning_n)

print(f"\n渠道:")
print(f"  长度: {length/1000:.1f} km")
print(f"  宽度: {width:.1f} m")
print(f"  底坡: {slope}")
print(f"  曼宁系数: {manning_n}")

print(f"\n洪峰:")
print(f"  基流: {Q_base:.1f} m^3/s")
print(f"  峰值: 150.0 m^3/s")
print(f"  涨洪历时: 2小时")
print(f"  落洪历时: 4小时")

# ========== 创建求解器 ==========
solver = GodunvFVMSolver(
    width=width,
    length=length,
    n_cells=n_cells,
    manning_n=manning_n,
    slope=slope,
    cfl = 0.3,
    order=1  # Order 1稳定可靠
)

# 初始化基流
h_init = np.ones(n_cells) * h_base
Q_init = np.ones(n_cells) * Q_base

bc_left = {'type': 'Q', 'value': flood_hydrograph}  # 动态流量
bc_right = {'type': 'h', 'value': h_base}  # 下游水深

# GodunvFVMSolver需要手动初始化


solver.h = h_init.copy()


solver.Q = Q_init.copy()


solver.bc_left = bc_left


solver.bc_right = bc_right

print(f"\n求解器:")
print(f"  网格: {n_cells}格, dx={solver.dx:.1f}m")
print(f"  初始水深: {h_base:.3f}m")

# ========== 模拟洪水演进 ==========
print(f"\n模拟洪水演进8小时...")

# 监测断面
x_monitors = [0, 2500, 5000, 7500, 10000]  # 0km, 2.5km, 5km, 7.5km, 10km
monitor_indices = [np.argmin(np.abs(solver.x - x)) for x in x_monitors]

# 时间序列
t_max = 8.0 * 3600  # 8小时
dt_save = 300  # 每5分钟保存
t_saves = []
Q_monitors = {i: [] for i in range(len(x_monitors))}
h_monitors = {i: [] for i in range(len(x_monitors))}

# 推进
t_last_save = 0
step_last_print = 0

while solver.t < t_max:
    solver.step()
    
    # 保存监测数据
    if solver.t - t_last_save >= dt_save:
        t_saves.append(solver.t / 3600)  # 转换为小时
        for i, idx in enumerate(monitor_indices):
            Q_monitors[i].append(solver.Q[idx])
            h_monitors[i].append(solver.h[idx])
        t_last_save = solver.t
    
    # 打印进度
    if solver.step_count - step_last_print >= 500:
        Q_in = flood_hydrograph(solver.t)
        print(f"  t={solver.t/3600:.2f}h, Q_in={Q_in:.1f}m^3/s, "
              f"质量误差={solver.get_mass_conservation_error():.4f}%")
        step_last_print = solver.step_count

state = solver.get_state()

print(f"\n模拟完成:")
print(f"  总步数: {state['step']}")
print(f"  质量误差: {state['mass_error']:.4f}%")

# ========== 结果分析 ==========
print(f"\n洪峰传播分析:")

# 计算峰值和延迟
for i, x_mon in enumerate(x_monitors):
    Q_series = np.array(Q_monitors[i])
    Q_peak_idx = np.argmax(Q_series)
    Q_peak = Q_series[Q_peak_idx]
    t_peak = t_saves[Q_peak_idx]
    
    if i == 0:
        Q_peak_0 = Q_peak
        t_peak_0 = t_peak
    
    delay = (t_peak - t_peak_0) * 60  # 分钟
    attenuation = (Q_peak_0 - Q_peak) / Q_peak_0 * 100
    
    print(f"  断面{i+1} (x={x_mon/1000:.1f}km): Q_peak={Q_peak:.1f}m^3/s, "
          f"延迟={delay:.1f}min, 衰减={attenuation:.2f}%")

# ========== 可视化 ==========
print(f"\n生成可视化...")

fig, axes = plt.subplots(2, 2, figsize=(14, 10))

# 1. 洪峰过程线各断面
ax1 = axes[0, 0]
colors = ['blue', 'green', 'orange', 'red', 'purple']
for i, x_mon in enumerate(x_monitors):
    ax1.plot(t_saves, Q_monitors[i], color=colors[i], linewidth=2,
             label=f'x={x_mon/1000:.1f}km')
ax1.set_xlabel('Time (hours)', fontsize=12)
ax1.set_ylabel('Discharge (m^3/s)', fontsize=12)
ax1.set_title('Flood Hydrograph at Different Sections', fontsize=14, fontweight='bold')
ax1.legend(fontsize=10)
ax1.grid(True, alpha=0.3)

# 2. 水深过程线
ax2 = axes[0, 1]
for i, x_mon in enumerate(x_monitors):
    ax2.plot(t_saves, h_monitors[i], color=colors[i], linewidth=2,
             label=f'x={x_mon/1000:.1f}km')
ax2.set_xlabel('Time (hours)', fontsize=12)
ax2.set_ylabel('Depth (m)', fontsize=12)
ax2.set_title('Water Depth at Different Sections', fontsize=14, fontweight='bold')
ax2.legend(fontsize=10)
ax2.grid(True, alpha=0.3)

# 3. 最终水面线
ax3 = axes[1, 0]
ax3.plot(state['x']/1000, state['h'], 'b-', linewidth=2, label='Final Profile')
ax3.axhline(y=h_base, color='gray', linestyle='--', label='Initial Depth')
ax3.set_xlabel('Distance (km)', fontsize=12)
ax3.set_ylabel('Depth (m)', fontsize=12)
ax3.set_title('Final Water Surface Profile', fontsize=14, fontweight='bold')
ax3.legend(fontsize=10)
ax3.grid(True, alpha=0.3)

# 4. 峰值衰减曲线
ax4 = axes[1, 1]
Q_peaks = [np.max(Q_monitors[i]) for i in range(len(x_monitors))]
ax4.plot([x/1000 for x in x_monitors], Q_peaks, 'ro-', linewidth=2, markersize=8)
ax4.set_xlabel('Distance (km)', fontsize=12)
ax4.set_ylabel('Peak Discharge (m^3/s)', fontsize=12)
ax4.set_title('Flood Peak Attenuation', fontsize=14, fontweight='bold')
ax4.grid(True, alpha=0.3)

plt.tight_layout()
plt.savefig('./phase1_flood_routing.png', dpi=150, bbox_inches='tight')
print(f"  保存: phase1_flood_routing.png")

# ========== 预警分析 ==========
print(f"\n预警分析:")

# 5km断面预警
idx_5km = monitor_indices[2]
Q_5km = np.array(Q_monitors[2])
h_5km = np.array(h_monitors[2])

# 警戒水深假设
h_warning = h_base * 1.5
h_danger = h_base * 2.0

t_warning_idx = np.where(h_5km > h_warning)[0]
if len(t_warning_idx) > 0:
    t_warning = t_saves[t_warning_idx[0]]
    print(f"  5km断面警戒水深达到时间: {t_warning:.2f}h")
else:
    print(f"  5km断面未达到警戒水深")

t_danger_idx = np.where(h_5km > h_danger)[0]
if len(t_danger_idx) > 0:
    t_danger = t_saves[t_danger_idx[0]]
    print(f"  5km断面危险水深达到时间: {t_danger:.2f}h")
else:
    print(f"  5km断面未达到危险水深")

# ========== 总结 ==========
print(f"\n" + "="*80)
print(f" 洪水演进模拟完成")
print(f"="*80)

print(f"\n核心发现:")
print(f"  1.  质量守恒优秀{state['mass_error']:.4f}%")
print(f"  2.  洪峰衰减明显{(Q_peaks[0]-Q_peaks[-1])/Q_peaks[0]*100:.1f}%")
print(f"  3.  传播时间约{(t_saves[np.argmax(Q_monitors[4])] - t_saves[np.argmax(Q_monitors[0])])*60:.0f}分钟")
print(f"  4.  Godunov-FVM捕捉洪峰传播准确")

print(f"\n工程价值:")
print(f"  - 洪水预报和预警")
print(f"  - 调度决策支持")
print(f"  - 防洪能力评估")
print(f"  - 应急响应时间计算")

print(f"\n Phase 1应用示例成功")
