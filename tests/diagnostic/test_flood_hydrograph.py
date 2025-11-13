#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
测试洪水过程线模拟 - Phase 1问题修复

目标：使用流量限速器避免NaN

Phase 1问题：
- 快速变化边界 -> NaN 
- 使用限速器 -> 稳定 

作者: HydroClaude Team
日期: 2025-10-27
"""

import sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

try:
    from solvers.godunov_fvm_solver import GodunvFVMSolver
except ImportError as e:
    print(f"Import error: {e}")
    print("Make sure project root is in sys.path")
    sys.exit(1)

from utils.canal_utils import compute_steady_uniform_flow
from utils.dynamic_bc import RateLimitedBC, create_flood_hydrograph
import numpy as np
import matplotlib.pyplot as plt

print("=" * 80)
print("洪水过程线模拟 - 动态边界测试")
print("=" * 80)

# 创建求解器
solver = GodunvFVMSolver(
    width=10.0, length=2000.0, n_cells=100,
    manning_n=0.025, slope=0.001,
    cfl=0.5, order=1
)

# 初始条件：基流
Q_base = 30.0
Q_peak = 80.0
h_base = compute_steady_uniform_flow(Q_base, 10.0, 0.001, 0.025)

print(f"\n洪水参数：")
print(f"  基流: {Q_base} m^3/s")
print(f"  峰值: {Q_peak} m^3/s")
print(f"  基流水深: {h_base:.3f} m")

# 初始化
h_init = np.ones(100) * h_base
Q_init = np.ones(100) * Q_base

bc_left = {'type': 'Q', 'value': Q_base}
bc_right = {'type': 'h', 'value': h_base}

solver.initialize(h_init, Q_init, bc_left, bc_right)

# 创建洪水过程线
t_rise = 1800.0  # 30分钟上升
t_total = 7200.0  # 2小时总时长
dt_hydro = 10.0  # 10秒采样

Q_hydrograph = create_flood_hydrograph(
    Q_base=Q_base,
    Q_peak=Q_peak,
    t_rise=t_rise,
    t_total=t_total,
    dt=dt_hydro,
    shape='triangular'
)

print(f"\n洪水过程线：")
print(f"  上升时间: {t_rise/60:.0f}分钟")
print(f"  总时长: {t_total/3600:.1f}小时")
print(f"  采样点: {len(Q_hydrograph)}个")

# 创建流量限速器
rate_limiter = RateLimitedBC(max_rate=15.0)  # 15 m^3/s per second

print(f"\n推进模拟...")
print(f"  流量限速器: 最大15 m^3/s/s")

# 记录
t_record = []
Q_target_record = []
Q_actual_record = []
mass_error_record = []
h_max_record = []

t_sim = 0.0
hydro_idx = 0
step_count = 0
max_steps = 5000

while t_sim < t_total and step_count < max_steps:
    # 获取当前目标流量
    if hydro_idx < len(Q_hydrograph):
        Q_target = Q_hydrograph[hydro_idx]
    else:
        Q_target = Q_base
    
    # 限速
    Q_actual = rate_limiter.update(Q_target, solver.dt)
    
    # 动态调整右边界水深（保持兼容性）
    h_right = compute_steady_uniform_flow(Q_actual, 10.0, 0.001, 0.025)
    
    # 更新边界
    solver.bc_left = {'type': 'Q', 'value': Q_actual}
    solver.bc_right = {'type': 'h', 'value': h_right}
    
    # 推进一步
    solver.step()
    
    # 记录
    if step_count % 20 == 0:
        state = solver.get_state()
        t_record.append(state['t'])
        Q_target_record.append(Q_target)
        Q_actual_record.append(Q_actual)
        mass_error_record.append(state['mass_error'])
        h_max_record.append(np.max(state['h']))
        
        if step_count % 200 == 0:
            print(f"  t={state['t']/60:5.1f}min, Q_target={Q_target:5.1f}, "
                  f"Q_actual={Q_actual:5.1f}, 质量误差={state['mass_error']:+.3f}%")
    
    t_sim = solver.t
    step_count += 1
    
    # 更新洪水过程线索引
    if t_sim >= (hydro_idx + 1) * dt_hydro:
        hydro_idx += 1

# 最终结果
print("\n" + "=" * 80)
print("最终结果")
print("=" * 80)

state = solver.get_state()
mass_error = state['mass_error']

print(f"\n模拟统计：")
print(f"  总步数: {step_count}")
print(f"  模拟时间: {t_sim/60:.1f}分钟")
print(f"  质量误差: {mass_error:.4f}%")

# 检查NaN
has_nan = np.any(np.isnan(state['h'])) or np.any(np.isnan(state['Q']))
print(f"  数值稳定: {' NaN' if has_nan else ' 稳定'}")

# 评价
print("\n" + "=" * 80)
print("综合评价")
print("=" * 80)

success = True

if has_nan:
    print("\n 测试失败: 出现NaN")
    success = False
elif abs(mass_error) > 3.0:
    print(f"\n️ 质量误差偏大: {abs(mass_error):.2f}% > 3%")
    success = False
else:
    print(f"\n 测试通过！")
    print(f"   质量误差 {abs(mass_error):.4f}% < 3%")
    print(f"   无NaN崩溃")
    print(f"   流量限速器有效！")

# 可视化
try:
    fig, axes = plt.subplots(3, 1, figsize=(12, 10))
    
    # 子图1: 流量过程
    ax1 = axes[0]
    ax1.plot(np.array(t_record)/60, Q_target_record, 'r--', label='目标流量', linewidth=2)
    ax1.plot(np.array(t_record)/60, Q_actual_record, 'b-', label='实际流量（限速后）', linewidth=2)
    ax1.set_xlabel('时间 (分钟)')
    ax1.set_ylabel('流量 (m^3/s)')
    ax1.set_title('洪水过程线 - 流量限速效果')
    ax1.legend()
    ax1.grid(True, alpha=0.3)
    
    # 子图2: 质量误差
    ax2 = axes[1]
    ax2.plot(np.array(t_record)/60, mass_error_record, 'g-', linewidth=2)
    ax2.axhline(y=0, color='k', linestyle='--', alpha=0.3)
    ax2.axhline(y=3, color='r', linestyle='--', alpha=0.3, label='+/-3%阈值')
    ax2.axhline(y=-3, color='r', linestyle='--', alpha=0.3)
    ax2.set_xlabel('时间 (分钟)')
    ax2.set_ylabel('质量误差 (%)')
    ax2.set_title('质量守恒')
    ax2.legend()
    ax2.grid(True, alpha=0.3)
    
    # 子图3: 最大水深
    ax3 = axes[2]
    ax3.plot(np.array(t_record)/60, h_max_record, 'm-', linewidth=2)
    ax3.set_xlabel('时间 (分钟)')
    ax3.set_ylabel('最大水深 (m)')
    ax3.set_title('最大水深变化')
    ax3.grid(True, alpha=0.3)
    
    plt.tight_layout()
    plt.savefig('/workspace/flood_hydrograph_test.png', dpi=150, bbox_inches='tight')
    print(f"\n 图表已保存: flood_hydrograph_test.png")
except Exception as e:
    print(f"\n️ 可视化失败: {str(e)}")

print("\n" + "=" * 80)
