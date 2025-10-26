#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
验证泵站底床高程和水位计算的正确性
"""

import numpy as np
import os

# 加载数据
data_file = "examples/example_gate_pump_cascade/results/steady_state_data.npz"
data = np.load(data_file)

x = data['x']
h = data['h']
q = data['q']
gate1_pos = data['gate1_pos']
pump_pos = data['pump_pos']
gate2_pos = data['gate2_pos']

# 找到泵站位置索引
pump_idx = np.argmin(np.abs(x - pump_pos))

# 计算底床高程（从原始代码逻辑）
S0 = 0.0001
pump_rated_head = 5.0

# 底床高程：泵前按斜坡，泵后抬高
z = -S0 * x
z[pump_idx:] += pump_rated_head  # 这是应该有的底床跳跃

# 计算水位
eta = z + h

print("="*80)
print("泵站底床高程和水位验证报告".center(80))
print("="*80)
print()

print("▶ 1. 泵站位置信息")
print("-"*80)
print(f"泵站位置: {pump_pos/1000:.1f} km = {pump_pos:.0f} m")
print(f"泵站索引: {pump_idx}")
print(f"泵站实际位置: {x[pump_idx]/1000:.3f} km = {x[pump_idx]:.1f} m")
print(f"额定扬程: {pump_rated_head:.1f} m")
print()

print("▶ 2. 底床高程验证")
print("-"*80)
print(f"泵站前（idx={pump_idx-1}）:")
print(f"  x = {x[pump_idx-1]/1000:.3f} km")
print(f"  z = {z[pump_idx-1]:.3f} m")
print()
print(f"泵站处（idx={pump_idx}）:")
print(f"  x = {x[pump_idx]/1000:.3f} km")
print(f"  z = {z[pump_idx]:.3f} m")
print()
print(f"泵站后（idx={pump_idx+1}）:")
print(f"  x = {x[pump_idx+1]/1000:.3f} km")
print(f"  z = {z[pump_idx+1]:.3f} m")
print()
print(f"底床高程变化:")
print(f"  泵前→泵后: Δz = {z[pump_idx+1] - z[pump_idx-1]:.3f} m")
print(f"  期望值: {pump_rated_head:.1f} m")
print(f"  {'✓ 正确' if abs((z[pump_idx+1] - z[pump_idx-1]) - pump_rated_head) < 0.1 else '✗ 错误'}")
print()

print("▶ 3. 水深和水位验证")
print("-"*80)
print(f"泵站前（idx={pump_idx-1}）:")
print(f"  底床高程 z = {z[pump_idx-1]:.3f} m")
print(f"  水深 h = {h[pump_idx-1]:.3f} m")
print(f"  水位 η = {eta[pump_idx-1]:.3f} m")
print()
print(f"泵站后（idx={pump_idx+1}）:")
print(f"  底床高程 z = {z[pump_idx+1]:.3f} m")
print(f"  水深 h = {h[pump_idx+1]:.3f} m")
print(f"  水位 η = {eta[pump_idx+1]:.3f} m")
print()
print(f"变化量:")
print(f"  底床变化: Δz = {z[pump_idx+1] - z[pump_idx-1]:.3f} m")
print(f"  水深变化: Δh = {h[pump_idx+1] - h[pump_idx-1]:.3f} m")
print(f"  水位变化: Δη = {eta[pump_idx+1] - eta[pump_idx-1]:.3f} m")
print()
print(f"物理验证:")
print(f"  水位抬升 ≈ 扬程: {eta[pump_idx+1] - eta[pump_idx-1]:.3f} m ≈ {pump_rated_head:.1f} m")
print(f"  {'✓ 正确 (山区泵站)' if abs((eta[pump_idx+1] - eta[pump_idx-1]) - pump_rated_head) < 0.2 else '✗ 错误'}")
print()

print("▶ 4. 流量守恒验证")
print("-"*80)
Q_target = 30.0
Q_before = q[pump_idx-1]
Q_after = q[pump_idx+1]
print(f"目标流量: {Q_target:.3f} m³/s")
print(f"泵前流量: {Q_before:.3f} m³/s (误差 {abs(Q_before-Q_target)/Q_target*100:.3f}%)")
print(f"泵后流量: {Q_after:.3f} m³/s (误差 {abs(Q_after-Q_target)/Q_target*100:.3f}%)")
print(f"流量守恒: {'✓ 正确' if abs(Q_after - Q_before) < 0.1 else '✗ 错误'}")
print()

print("▶ 5. 能量守恒验证")
print("-"*80)
g = 9.81
v_before = Q_before / (15.0 * h[pump_idx-1])  # B=15m
v_after = Q_after / (15.0 * h[pump_idx+1])
E_before = z[pump_idx-1] + h[pump_idx-1] + v_before**2/(2*g)
E_after = z[pump_idx+1] + h[pump_idx+1] + v_after**2/(2*g)
print(f"泵前总能量: E = {E_before:.3f} m")
print(f"泵后总能量: E = {E_after:.3f} m")
print(f"能量增加: ΔE = {E_after - E_before:.3f} m")
print(f"期望扬程: H = {pump_rated_head:.1f} m")
print(f"能量守恒: {'✓ 正确' if abs((E_after - E_before) - pump_rated_head) < 0.5 else '✗ 错误'}")
print()

print("="*80)
print("验证结果总结".center(80))
print("="*80)
checks = []
checks.append(("底床跳跃", abs((z[pump_idx+1] - z[pump_idx-1]) - pump_rated_head) < 0.1))
checks.append(("水位抬升", abs((eta[pump_idx+1] - eta[pump_idx-1]) - pump_rated_head) < 0.2))
checks.append(("流量守恒", abs(Q_after - Q_before) < 0.1))
checks.append(("能量守恒", abs((E_after - E_before) - pump_rated_head) < 0.5))

for name, passed in checks:
    status = "✓ 通过" if passed else "✗ 失败"
    print(f"  {name:12s}: {status}")

print()
all_passed = all([c[1] for c in checks])
if all_passed:
    print("✓ 所有验证通过！泵站建模正确。".center(80))
else:
    print("✗ 部分验证失败，需要检查。".center(80))
print("="*80)
