"""
Saint-Venant模型简化诊断脚本

诊断Canal类的MOC求解器是否正常工作
"""

import numpy as np
import sys
import os

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))

from physics.canal import Canal

# 创建Canal模型
canal = Canal(
    name="test_canal",
    volume_min=0.0,
    volume_max=1000 * 10 * 10,
    area=10 * 2.5,
    length=1000.0,
    slope=0.001,
    n_sections=51,
    method='moc',
    manning_n=0.025,
    width=10.0,
    initial_depth=2.5,
    initial_flow=20.0
)

print("="*60)
print("Saint-Venant MOC求解器诊断")
print("="*60)

print(f"\n初始状态:")
print(f"  h[0] = {canal.hydraulic_state.h[0]:.3f} m")
print(f"  h[-1] = {canal.hydraulic_state.h[-1]:.3f} m")
print(f"  Q[0] = {canal.hydraulic_state.Q[0]:.2f} m³/s")
print(f"  Q[-1] = {canal.hydraulic_state.Q[-1]:.2f} m³/s")

# 简单测试：增加入流，看水位是否上升
dt = 10.0
n_steps = 50

print(f"\n测试：增加入流到30 m³/s，持续{n_steps * dt}s")
print("-" * 60)

for k in range(n_steps):
    t = k * dt

    # 设置边界条件：增加入流
    canal.hydraulic_state.Q[0] = 30.0  # 增加入流
    canal.hydraulic_state.Q[-1] = 20.0  # 保持出流

    # 执行MOC更新
    inputs = {'Q_in': 30.0, 'Q_out': 20.0}
    try:
        canal.update_high_fidelity(dt, inputs)
    except Exception as e:
        print(f"错误 at t={t}s: {e}")
        break

    # 每10步打印一次
    if k % 10 == 0:
        print(f"t={t:4.0f}s: h[-1]={canal.hydraulic_state.h[-1]:.3f}m, "
              f"Q[-1]={canal.hydraulic_state.Q[-1]:.2f}m³/s")

print("\n" + "="*60)
print(f"最终状态:")
print(f"  h[0] = {canal.hydraulic_state.h[0]:.3f} m")
print(f"  h[-1] = {canal.hydraulic_state.h[-1]:.3f} m")
print(f"  Q[0] = {canal.hydraulic_state.Q[0]:.2f} m³/s")
print(f"  Q[-1] = {canal.hydraulic_state.Q[-1]:.2f} m³/s")

h_change = canal.hydraulic_state.h[-1] - 2.5
print(f"\n水位变化: Δh = {h_change:.3f} m")

if abs(h_change) < 0.001:
    print("\n❌ 问题：水位没有变化！")
    print("   可能原因：")
    print("   1. 边界条件设置不正确")
    print("   2. MOC求解器没有正常工作")
    print("   3. downstream_boundary未设置")
else:
    print(f"\n✅ 正常：水位变化了 {h_change:.3f} m")

print("="*60)
