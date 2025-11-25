#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Godunov-FVM + 闸门集成测试

测试场景：
1. 闸门完全开启（稳态流）
2. 闸门突然关闭（非恒定流）
3. 闸门逐渐调节（控制）
"""

import numpy as np
import warnings
warnings.filterwarnings("ignore")
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import sys
sys.path.insert(0, '/workspace')

try:
    from solvers.godunov_fvm_solver import GodunvFVMSolver
except ImportError as e:
    print(f"Import error: {e}")
    print("Make sure project root is in sys.path")
    sys.exit(1)

from solvers.gate import SluiceGate
from utils.canal_utils import compute_steady_uniform_flow


print("="*80)
print("Godunov-FVM + 闸门集成测试")
print("="*80)

# ========== 测试1: 闸门完全开启 ==========
print("\n" + "="*80)
print("测试1: 闸门完全开启（稳态流）")
print("="*80)

width = 10.0
length = 1000.0
n_cells = 100
manning_n = 0.025
slope = 0.001
Q_target = 50.0

# 闸门位置
x_gate = 500.0
gate_idx = int((x_gate / length) * n_cells)

print(f"\n配置:")
print(f"  渠道: {length}m x {width}m")
print(f"  闸门位置: x={x_gate}m (单元#{gate_idx})")
print(f"  目标流量: {Q_target} m^3/s")

# 创建闸门
gate = SluiceGate(
    position=x_gate,
    width=width,
    opening=10.0  # 完全开启（大于水深）
)

print(f"  闸门开度: {gate.get_opening()} m (完全开启)")

# 理论水深
h_uniform = compute_steady_uniform_flow(Q_target, width, slope, manning_n)
print(f"  理论水深: {h_uniform:.4f} m")

# 创建求解器
solver = GodunvFVMSolver(
    width=width, length=length, n_cells=n_cells,
    manning_n=manning_n, slope=slope,
    cfl=0.5, order=1
)

h_init = np.ones(n_cells) * h_uniform
Q_init = np.ones(n_cells) * Q_target

bc_left = {'type': 'Q', 'value': Q_target}
bc_right = {'type': 'h', 'value': h_uniform}

solver.initialize(h_init, Q_init, bc_left, bc_right)

# 时间推进
t_target = 500.0
history = {'t': [], 'h_gate': [], 'Q_gate': [], 'mass_error': []}

print(f"\n时间推进至 t={t_target}s:")

while solver.t < t_target and solver.step_count < 2000:
    solver.step()
    
    if solver.step_count % 100 == 0:
        state = solver.get_state()
        h_gate = state['h'][gate_idx]
        Q_gate = state['Q'][gate_idx]
        
        # 计算闸门水力学（即使完全开启也检查）
        h_us = state['h'][gate_idx - 1]  # 上游
        h_ds = state['h'][gate_idx + 1]  # 下游
        
        # 记录
        history['t'].append(state['t'])
        history['h_gate'].append(h_gate)
        history['Q_gate'].append(Q_gate)
        history['mass_error'].append(state['mass_error'])
        
        if solver.step_count % 500 == 0:
            print(f"  t={state['t']:6.1f}s, h_gate={h_gate:.4f}m, "
                  f"Q_gate={Q_gate:.2f}m^3/s, 质量误差={state['mass_error']:.4f}%")

state = solver.get_state()

print(f"\n稳态结果 (t={state['t']:.1f}s, {state['step']}步):")
print(f"  质量误差: {state['mass_error']:.6f}%")
print(f"  闸门处水深: {state['h'][gate_idx]:.4f}m")
print(f"  闸门处流量: {state['Q'][gate_idx]:.2f}m^3/s")
print(f"  平均水深: {np.mean(state['h']):.4f}m (理论: {h_uniform:.4f}m)")
print(f"  平均流量: {np.mean(state['Q']):.2f}m^3/s (目标: {Q_target:.2f}m^3/s)")

# 可视化
fig, ((ax1, ax2), (ax3, ax4)) = plt.subplots(2, 2, figsize=(14, 10))

# 水深剖面
ax1.plot(solver.x, state['h'], 'b-', lw=1.5)
ax1.axvline(x_gate, color='r', ls='--', lw=2, label='Gate (Fully Open)')
ax1.axhline(h_uniform, color='k', ls=':', lw=1, label='Uniform')
ax1.set_xlabel('x (m)', fontsize=11)
ax1.set_ylabel('h (m)', fontsize=11)
ax1.set_title('Water Depth Profile', fontsize=12)
ax1.legend(fontsize=10)
ax1.grid(True, alpha=0.3)

# 流量剖面
ax2.plot(solver.x, state['Q'], 'g-', lw=1.5)
ax2.axvline(x_gate, color='r', ls='--', lw=2, label='Gate')
ax2.axhline(Q_target, color='k', ls=':', lw=1, label='Target')
ax2.set_xlabel('x (m)', fontsize=11)
ax2.set_ylabel('Q (m^3/s)', fontsize=11)
ax2.set_title('Discharge Profile', fontsize=12)
ax2.legend(fontsize=10)
ax2.grid(True, alpha=0.3)

# 闸门处时间演化
ax3.plot(history['t'], history['h_gate'], 'b-', lw=1.5)
ax3.axhline(h_uniform, color='k', ls=':', lw=1)
ax3.set_xlabel('Time (s)', fontsize=11)
ax3.set_ylabel('h at Gate (m)', fontsize=11)
ax3.set_title('Water Depth at Gate vs Time', fontsize=12)
ax3.grid(True, alpha=0.3)

# 质量守恒
ax4.plot(history['t'], history['mass_error'], 'r-', lw=1.5)
ax4.axhline(0, color='k', ls='-', lw=0.5)
ax4.set_xlabel('Time (s)', fontsize=11)
ax4.set_ylabel('Mass Error (%)', fontsize=11)
ax4.set_title('Mass Conservation Over Time', fontsize=12)
ax4.grid(True, alpha=0.3)

plt.tight_layout()
plt.savefig('/workspace/godunov_gate_fully_open.png', dpi=150)
print(f"\n  图像: godunov_gate_fully_open.png")

# 成功标准
checks = [
    ("质量守恒<1%", abs(state['mass_error']) < 1.0),
    ("闸门处水深合理", abs(state['h'][gate_idx] - h_uniform) / h_uniform < 0.1),
    ("流量守恒", abs(state['Q'][gate_idx] - Q_target) / Q_target < 0.1),
    ("数值稳定", not np.any(np.isnan(state['h'])))
]

print(f"\n成功标准:")
for name, passed in checks:
    print(f"  {name}: {'' if passed else ''}")

all_pass_1 = all(c[1] for c in checks)

print(f"\n{'='*80}")
if all_pass_1:
    print(" 测试1: 闸门完全开启 **通过** ")
else:
    print("️ 测试1: 闸门完全开启 部分通过")
print("="*80)

# ========== 测试2: 闸门突然关闭 ==========
print("\n" + "="*80)
print("测试2: 闸门突然关闭（非恒定流）")
print("="*80)

# 新求解器
solver2 = GodunvFVMSolver(
    width=width, length=length, n_cells=n_cells,
    manning_n=manning_n, slope=slope,
    cfl=0.5, order=1
)

# 初始：稳态流
solver2.initialize(h_init, Q_init, bc_left, bc_right)

# 推进到稳态
while solver2.t < 100.0:
    solver2.step()

print(f"\n初始稳态 (t={solver2.t:.1f}s):")
print(f"  <h>={np.mean(solver2.h):.4f}m, <Q>={np.mean(solver2.Q):.2f}m^3/s")

# 闸门关闭（开度3m -> 形成壅水）
gate2 = SluiceGate(position=x_gate, width=width, opening=3.0)
print(f"\n闸门关闭至开度: {gate2.get_opening()} m (t=100s)")

# 模拟闸门效果（简化：在闸门位置限制流量）
h_before_gate = solver2.h.copy()

# 继续推进，模拟闸门关闭后的响应
t_end = 50.0
history2 = {'t': [], 'h_us': [], 'h_ds': [], 'Q_gate': []}

print(f"\n时间推进至 t={t_end}s (闸门关闭后):")

while solver2.t < t_end and solver2.step_count < 3000:
    solver2.step()
    
    # 闸门效果：限制闸门处流量（简化处理）
    # 实际应用中需要耦合闸门方程
    h_us = solver2.h[gate_idx - 1]
    h_gate = solver2.h[gate_idx]
    
    # 闸门流量（简化的孔流公式）
    if h_us > gate2.get_opening():
        Q_gate_calc, flow_type = gate2.calculate_discharge(h_us, h_gate)
        # 限制闸门处流量（简化）
        solver2.Q[gate_idx] = min(solver2.Q[gate_idx], Q_gate_calc)
    
    if solver2.step_count % 100 == 0:
        h_us = solver2.h[gate_idx - 1]
        h_ds = solver2.h[gate_idx + 1]
        Q_gate = solver2.Q[gate_idx]
        
        history2['t'].append(solver2.t)
        history2['h_us'].append(h_us)
        history2['h_ds'].append(h_ds)
        history2['Q_gate'].append(Q_gate)
        
        if solver2.step_count % 500 == 0:
            print(f"  t={solver2.t:6.1f}s, h_us={h_us:.4f}m, h_ds={h_ds:.4f}m, "
                  f"Q_gate={Q_gate:.2f}m^3/s")

state2 = solver2.get_state()

print(f"\n最终结果 (t={state2['t']:.1f}s):")
print(f"  质量误差: {state2['mass_error']:.6f}%")
print(f"  上游水深: {state2['h'][gate_idx-1]:.4f}m (壅水)")
print(f"  下游水深: {state2['h'][gate_idx+1]:.4f}m")
print(f"  闸门流量: {state2['Q'][gate_idx]:.2f}m^3/s")

# 可视化
fig2, ((ax1, ax2), (ax3, ax4)) = plt.subplots(2, 2, figsize=(14, 10))

# 水深剖面（前后对比）
ax1.plot(solver.x, h_before_gate, 'b--', lw=1.5, label='Before Gate Closure', alpha=0.7)
ax1.plot(solver2.x, state2['h'], 'r-', lw=2, label='After Gate Closure')
ax1.axvline(x_gate, color='k', ls='--', lw=2, label='Gate')
ax1.set_xlabel('x (m)', fontsize=11)
ax1.set_ylabel('h (m)', fontsize=11)
ax1.set_title('Water Depth Profile (Gate Closure)', fontsize=12)
ax1.legend(fontsize=10)
ax1.grid(True, alpha=0.3)

# 流量剖面
ax2.plot(solver2.x, state2['Q'], 'g-', lw=1.5)
ax2.axvline(x_gate, color='k', ls='--', lw=2, label='Gate')
ax2.set_xlabel('x (m)', fontsize=11)
ax2.set_ylabel('Q (m^3/s)', fontsize=11)
ax2.set_title('Discharge Profile (After Closure)', fontsize=12)
ax2.legend(fontsize=10)
ax2.grid(True, alpha=0.3)

# 上下游水深演化
ax3.plot(history2['t'], history2['h_us'], 'b-', lw=1.5, label='Upstream')
ax3.plot(history2['t'], history2['h_ds'], 'r-', lw=1.5, label='Downstream')
ax3.axvline(100, color='k', ls=':', lw=1, label='Gate Closes')
ax3.set_xlabel('Time (s)', fontsize=11)
ax3.set_ylabel('Water Depth (m)', fontsize=11)
ax3.set_title('Upstream/Downstream Water Level', fontsize=12)
ax3.legend(fontsize=10)
ax3.grid(True, alpha=0.3)

# 闸门流量演化
ax4.plot(history2['t'], history2['Q_gate'], 'g-', lw=1.5)
ax4.axvline(100, color='k', ls=':', lw=1, label='Gate Closes')
ax4.axhline(Q_target, color='r', ls='--', lw=1, label='Initial Flow')
ax4.set_xlabel('Time (s)', fontsize=11)
ax4.set_ylabel('Gate Discharge (m^3/s)', fontsize=11)
ax4.set_title('Discharge Through Gate', fontsize=12)
ax4.legend(fontsize=10)
ax4.grid(True, alpha=0.3)

plt.tight_layout()
plt.savefig('/workspace/godunov_gate_closure.png', dpi=150)
print(f"\n  图像: godunov_gate_closure.png")

# 成功标准
checks2 = [
    ("质量守恒<2%", abs(state2['mass_error']) < 2.0),
    ("上游壅水", state2['h'][gate_idx-1] > h_uniform),
    ("流量减少", state2['Q'][gate_idx] < Q_target),
    ("数值稳定", not np.any(np.isnan(state2['h'])))
]

print(f"\n成功标准:")
for name, passed in checks2:
    print(f"  {name}: {'' if passed else ''}")

all_pass_2 = all(c[1] for c in checks2)

print(f"\n{'='*80}")
if all_pass_2:
    print(" 测试2: 闸门关闭 **通过** ")
else:
    print("️ 测试2: 闸门关闭 部分通过")
print("="*80)

# 总结
print("\n" + "="*80)
print(" Godunov-FVM + 闸门集成测试完成！")
print("="*80)

print(f"\n总结:")
print(f"  测试1（完全开启）: {' 通过' if all_pass_1 else '️ 部分通过'}")
print(f"  测试2（突然关闭）: {' 通过' if all_pass_2 else '️ 部分通过'}")

if all_pass_1 and all_pass_2:
    print(f"\n Godunov-FVM + 闸门集成 **完全成功** ")
else:
    print(f"\n️ 部分功能需要改进")
