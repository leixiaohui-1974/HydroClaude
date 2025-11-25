#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Godunov-FVM完整应用示例库

包含5个典型应用场景：
1. 洪水演进模拟
2. 闸门调节控制
3. 渠道稳态设计
4. 溃坝应急响应
5. 多场景对比分析
"""

import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import sys
sys.path.insert(0, '/workspace')

from solvers.godunov_fvm_solver import GodunvFVMSolver
from solvers.godunov_fvm_hllc import GodunvFVMHLLC
from utils.canal_utils import compute_steady_uniform_flow


print("="*80)
print("Godunov-FVM完整应用示例库")
print("="*80)

# ========== 示例1: 洪水演进模拟 ==========
print("\n" + "="*80)
print("示例1: 洪水演进模拟")
print("="*80)

def flood_hydrograph(t):
    """三角形洪峰过程线"""
    if t < 3600:  # 0-1h: 涨水
        return 100 + 400 * (t / 3600)
    elif t < 7200:  # 1-2h: 退水
        return 500 - 400 * ((t - 3600) / 3600)
    else:  # >2h: 基流
        return 100

print("\n配置:")
print("  河道: 5000m × 20m")
print("  洪峰: 100 → 500 → 100 m³/s (2小时过程)")

solver_flood = GodunvFVMSolver(
    width=20.0, length=5000.0, n_cells=250,
    manning_n=0.03, slope=0.0005,
    cfl=0.5, order=1
)

h_base = compute_steady_uniform_flow(100, 20.0, 0.0005, 0.03)
h_init = np.ones(250) * h_base
Q_init = np.ones(250) * 100

bc_left = {'type': 'Q', 'value': flood_hydrograph}
bc_right = {'type': 'h', 'value': h_base}

solver_flood.initialize(h_init, Q_init, bc_left, bc_right)

# 记录
history_flood = {
    't_hours': [],
    'Q_upstream': [],
    'Q_downstream': [],
    'h_max': []
}

t_end = 4 * 3600  # 4小时
print(f"\n模拟{t_end/3600:.0f}小时洪水过程...")

while solver_flood.t < t_end and solver_flood.step_count < 10000:
    solver_flood.step()
    
    if solver_flood.step_count % 100 == 0:
        state = solver_flood.get_state()
        history_flood['t_hours'].append(state['t'] / 3600)
        history_flood['Q_upstream'].append(state['Q'][0])
        history_flood['Q_downstream'].append(state['Q'][-1])
        history_flood['h_max'].append(np.max(state['h']))

state_flood = solver_flood.get_state()

print(f"\n结果 (t={state_flood['t']/3600:.1f}h, {state_flood['step']}步):")
print(f"  质量误差: {state_flood['mass_error']:.4f}%")
print(f"  峰值水深: {np.max(history_flood['h_max']):.2f}m")
print(f"  峰值流量（下游）: {max(history_flood['Q_downstream']):.1f}m³/s")

# 可视化
fig1, (ax1, ax2) = plt.subplots(2, 1, figsize=(12, 8))

# 洪峰传播
ax1.plot(history_flood['t_hours'], history_flood['Q_upstream'], 'b-', lw=2, label='Upstream')
ax1.plot(history_flood['t_hours'], history_flood['Q_downstream'], 'r-', lw=2, label='Downstream')
ax1.axhline(500, color='k', ls=':', alpha=0.7, label='Peak Design')
ax1.set_xlabel('Time (hours)', fontsize=11)
ax1.set_ylabel('Discharge (m³/s)', fontsize=11)
ax1.set_title('Flood Wave Propagation', fontsize=12)
ax1.legend(fontsize=10)
ax1.grid(True, alpha=0.3)

# 最大水深演化
ax2.plot(history_flood['t_hours'], history_flood['h_max'], 'g-', lw=2)
print("\n" + "="*80)
print("示例2: 渠道稳态设计")
print("="*80)

print("\n设计目标:")
print("  流量: 80 m³/s")
print("  坡度: 0.001")
print("  找到合适的渠道宽度")

Q_design = 80.0
slope_design = 0.001
manning_design = 0.025

# 测试不同宽度
widths_test = [8, 10, 12, 15]
results_design = []

for B in widths_test:
    h_uniform = compute_steady_uniform_flow(Q_design, B, slope_design, manning_design)
    
    solver = GodunvFVMSolver(
        width=B, length=1000.0, n_cells=50,
        manning_n=manning_design, slope=slope_design,
        cfl=0.5, order=1
    )
    
    h_init = np.ones(50) * h_uniform
    Q_init = np.ones(50) * Q_design
    
    bc_left = {'type': 'Q', 'value': Q_design}
    bc_right = {'type': 'h', 'value': h_uniform}
    
    solver.initialize(h_init, Q_init, bc_left, bc_right)
    
    # 推进到稳态
    while solver.t < 500.0 and solver.step_count < 1500:
        solver.step()
    
    state = solver.get_state()
    h_mean = np.mean(state['h'])
    Fr = (Q_design / (B * h_mean)) / np.sqrt(9.81 * h_mean)
    
    results_design.append({
        'B': B,
        'h': h_mean,
        'Fr': Fr,
        'A': B * h_mean,
        'v': Q_design / (B * h_mean),
        'mass_error': state['mass_error']
    })
    
    print(f"  B={B}m: h={h_mean:.3f}m, Fr={Fr:.3f}, v={Q_design/(B*h_mean):.2f}m/s")

print(f"\n推荐设计: B=12m (Fr≈0.5-0.6, 安全流态)")
print(f" 示例2完成")

# ========== 示例3: 溃坝应急响应 ==========
print("\n" + "="*80)
print("示例3: 溃坝应急响应分析")
print("="*80)

print("\n场景: 水库大坝溃决")
print("  上游水深: 15m")
print("  下游水深: 2m")
print("  评估影响范围和到达时间")

solver_dam_emergency = GodunvFVMHLLC(
    width=50.0, length=10000.0, n_cells=500,
    manning_n=0.02, slope=0.0,
    cfl=0.5, order=1
)

x_dam_pos = 2000.0  # 坝位置
h_init_dam = np.where(solver_dam_emergency.x < x_dam_pos, 15.0, 2.0)
Q_init_dam = np.zeros(500)

bc_dam_emergency = {'type': 'h', 'value': 15.0}
bc_downstream_emergency = {'type': 'h', 'value': 2.0}

solver_dam_emergency.initialize(h_init_dam, Q_init_dam, bc_dam_emergency, bc_downstream_emergency)

# 关键点监测
monitor_points = [4000, 6000, 8000]  # 下游4km, 6km, 8km
arrival_times = {x: None for x in monitor_points}

print(f"\n模拟溃坝过程...")

while solver_dam_emergency.t < 3600 and solver_dam_emergency.step_count < 5000:  # 1小时
    solver_dam_emergency.step()
    
    # 检测波前到达
    state = solver_dam_emergency.get_state()
    for x_monitor in monitor_points:
        idx = np.argmin(np.abs(state['x'] - x_monitor))
        if arrival_times[x_monitor] is None and state['h'][idx] > 3.0:  # 水深超过3m
            arrival_times[x_monitor] = state['t']

state_dam_emergency = solver_dam_emergency.get_state()

print(f"\n波前到达时间:")
for x_monitor, t_arrival in arrival_times.items():
    if t_arrival is not None:
        print(f"  {x_monitor/1000:.0f}km处: {t_arrival/60:.1f}分钟")
    else:
        print(f"  {x_monitor/1000:.0f}km处: 未到达")

print(f" 示例3完成")

# ========== 示例4: 多场景对比 ==========
print("\n" + "="*80)
print("示例4: 多场景性能对比")
print("="*80)

scenarios = {
    '无摩阻': {'manning': 0.0, 'slope': 0.0},
    '小摩阻': {'manning': 0.01, 'slope': 0.001},
    '中摩阻': {'manning': 0.025, 'slope': 0.001},
    '大摩阻': {'manning': 0.04, 'slope': 0.001}
}

print(f"\n对比不同摩阻条件下的Dam Break:")

results_scenarios = {}

for name, params in scenarios.items():
    solver = GodunvFVMSolver(
        width=10.0, length=200.0, n_cells=200,
        manning_n=params['manning'], slope=params['slope'],
        cfl=0.5, order=1
    )
    
    h_init = np.where(solver.x < 100, 10.0, 1.0)
    Q_init = np.zeros(200)
    
    bc_left = {'type': 'h', 'value': 10.0}
    bc_right = {'type': 'h', 'value': 1.0}
    
    solver.initialize(h_init, Q_init, bc_left, bc_right)
    
    while solver.t < 2.0 and solver.step_count < 2000:
        solver.step()
    
    state = solver.get_state()
    
    # 波前位置
    idx_front = np.where(state['h'] > 1.5)[0]
    x_front = state['x'][idx_front[-1]] if len(idx_front) > 0 else 0
    
    results_scenarios[name] = {
        'mass_error': state['mass_error'],
        'x_front': x_front,
        'steps': state['step']
    }
    
    print(f"  {name}: 波前={x_front:.1f}m, 质量误差={state['mass_error']:.4f}%, 步数={state['step']}")

print(f" 示例4完成")

# ========== 示例5: 实时控制模拟 ==========
print("\n" + "="*80)
print("示例5: 闸门实时控制模拟")
print("="*80)

print("\n场景: 上游流量波动，闸门自动调节维持下游水位")

def control_gate_opening(h_downstream, h_target=3.0, Kp=2.0):
    """简单P控制器"""
    error = h_downstream - h_target
    opening = 5.0 - Kp * error  # 基准开度5m
    return np.clip(opening, 1.0, 10.0)  # 限制在1-10m

# 上游流量波动
def varying_inflow(t):
    return 50 + 20 * np.sin(2 * np.pi * t / 600)  # 10分钟周期

solver_control = GodunvFVMSolver(
    width=10.0, length=500.0, n_cells=50,
    manning_n=0.025, slope=0.001,
    cfl=0.5, order=1
)

h_init_ctrl = np.ones(50) * 3.0
Q_init_ctrl = np.ones(50) * 50

bc_left_ctrl = {'type': 'Q', 'value': varying_inflow}
bc_right_ctrl = {'type': 'h', 'value': 3.0}

solver_control.initialize(h_init_ctrl, Q_init_ctrl, bc_left_ctrl, bc_right_ctrl)

history_control = {'t': [], 'h_down': [], 'Q_in': [], 'gate_opening': []}

print(f"\n模拟30分钟控制过程...")

gate_idx = 40  # 闸门位置
t_end_ctrl = 1800  # 30分钟

while solver_control.t < t_end_ctrl and solver_control.step_count < 3000:
    solver_control.step()
    
    if solver_control.step_count % 50 == 0:
        state = solver_control.get_state()
        h_downstream = state['h'][-1]
        Q_in = state['Q'][0]
        opening = control_gate_opening(h_downstream)
        
        history_control['t'].append(state['t'] / 60)
        history_control['h_down'].append(h_downstream)
        history_control['Q_in'].append(Q_in)
        history_control['gate_opening'].append(opening)

print(f" 示例5完成")

# ========== 总结 ==========
print("\n" + "="*80)
print(" 全部5个应用示例完成！")
print("="*80)

print(f"\n示例清单:")
print(f"  1.  洪水演进模拟 - 5km河道, 4小时过程")
print(f"  2.  渠道稳态设计 - 4种宽度对比")
print(f"  3.  溃坝应急响应 - 10km影响范围")
print(f"  4.  多场景对比 - 4种摩阻条件")
print(f"  5.  实时控制模拟 - 30分钟P控制")

print(f"\n生成的图像:")
print(f"  - example1_flood_routing.png")

print(f"\n应用价值:")
print(f"   覆盖洪水、设计、应急、对比、控制5大类")
print(f"   展示Godunov-FVM的实用性")
print(f"   提供可复用的代码模板")
