"""
详细诊断Canal MOC边界条件实现

检查修复后的边界条件是否正确计算
"""

import numpy as np
import matplotlib.pyplot as plt
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
    initial_flow=20.0,
    h_max=5.0  # 限制最大水位，避免过度上升
)

print("="*80)
print("Canal MOC边界条件详细诊断")
print("="*80)

dt = 10.0
n_steps = 50

# 记录数据
time_hist = []
h_upstream = []
h_downstream = []
Q_in_hist = []
Q_out_hist = []

print(f"\n初始状态:")
print(f"  上游: h={canal.hydraulic_state.h[0]:.3f}m, Q={canal.hydraulic_state.Q[0]:.2f}m³/s")
print(f"  下游: h={canal.hydraulic_state.h[-1]:.3f}m, Q={canal.hydraulic_state.Q[-1]:.2f}m³/s")

# 测试：小幅增加入流
Q_in = 22.0  # 从20增加到22（小幅变化）
Q_out = 20.0

print(f"\n测试：入流={Q_in}m³/s, 出流={Q_out}m³/s")
print(f"净入流={Q_in - Q_out}m³/s")
print("-"*80)

for k in range(n_steps):
    t = k * dt

    # 更新
    inputs = {'Q_in': Q_in, 'Q_out': Q_out}
    canal.update_high_fidelity(dt, inputs)

    # 记录
    time_hist.append(t)
    h_upstream.append(canal.hydraulic_state.h[0])
    h_downstream.append(canal.hydraulic_state.h[-1])
    Q_in_hist.append(canal.hydraulic_state.Q[0])
    Q_out_hist.append(canal.hydraulic_state.Q[-1])

    # 打印关键步骤
    if k % 10 == 0:
        print(f"t={t:4.0f}s: "
              f"h_up={canal.hydraulic_state.h[0]:.3f}m, "
              f"h_down={canal.hydraulic_state.h[-1]:.3f}m, "
              f"Q_in={canal.hydraulic_state.Q[0]:.2f}m³/s, "
              f"Q_out={canal.hydraulic_state.Q[-1]:.2f}m³/s")

print("\n" + "="*80)
print("最终状态:")
print(f"  上游: h={canal.hydraulic_state.h[0]:.3f}m, Q={canal.hydraulic_state.Q[0]:.2f}m³/s")
print(f"  下游: h={canal.hydraulic_state.h[-1]:.3f}m, Q={canal.hydraulic_state.Q[-1]:.2f}m³/s")

delta_h_up = canal.hydraulic_state.h[0] - 2.5
delta_h_down = canal.hydraulic_state.h[-1] - 2.5

print(f"\n水位变化:")
print(f"  上游: Δh = {delta_h_up:.3f}m")
print(f"  下游: Δh = {delta_h_down:.3f}m")

# 理论分析
volume_added = (Q_in - Q_out) * dt * n_steps  # m³
area_total = 10 * 1000  # m²
expected_delta_h = volume_added / area_total
print(f"\n理论水位变化（质量守恒）:")
print(f"  累积体积: {volume_added:.1f}m³")
print(f"  渠道面积: {area_total:.1f}m²")
print(f"  预期Δh: {expected_delta_h:.3f}m")

# 可视化
fig, axes = plt.subplots(2, 2, figsize=(12, 8))

# 子图1: 水位时程
ax1 = axes[0, 0]
ax1.plot(time_hist, h_upstream, 'b-', label='上游', linewidth=2)
ax1.plot(time_hist, h_downstream, 'r--', label='下游', linewidth=2)
ax1.axhline(2.5, color='gray', linestyle=':', label='初始水位')
ax1.set_xlabel('Time (s)')
ax1.set_ylabel('Water Depth (m)')
ax1.set_title('Water Depth Evolution')
ax1.legend()
ax1.grid(True, alpha=0.3)

# 子图2: 流量时程
ax2 = axes[0, 1]
ax2.plot(time_hist, Q_in_hist, 'b-', label='入流', linewidth=2)
ax2.plot(time_hist, Q_out_hist, 'r--', label='出流', linewidth=2)
ax2.axhline(Q_in, color='b', linestyle=':', alpha=0.5)
ax2.axhline(Q_out, color='r', linestyle=':', alpha=0.5)
ax2.set_xlabel('Time (s)')
ax2.set_ylabel('Flow Rate (m³/s)')
ax2.set_title('Flow Rate Evolution')
ax2.legend()
ax2.grid(True, alpha=0.3)

# 子图3: 沿程水位分布（最终）
ax3 = axes[1, 0]
ax3.plot(canal.x, canal.hydraulic_state.h, 'b-', linewidth=2)
ax3.axhline(2.5, color='gray', linestyle=':', label='初始水位')
ax3.set_xlabel('Distance (m)')
ax3.set_ylabel('Water Depth (m)')
ax3.set_title('Final Water Depth Profile')
ax3.legend()
ax3.grid(True, alpha=0.3)

# 子图4: 沿程流量分布（最终）
ax4 = axes[1, 1]
ax4.plot(canal.x, canal.hydraulic_state.Q, 'r-', linewidth=2)
ax4.axhline(Q_in, color='b', linestyle=':', label=f'入流={Q_in}')
ax4.axhline(Q_out, color='r', linestyle=':', label=f'出流={Q_out}')
ax4.set_xlabel('Distance (m)')
ax4.set_ylabel('Flow Rate (m³/s)')
ax4.set_title('Final Flow Rate Profile')
ax4.legend()
ax4.grid(True, alpha=0.3)

plt.tight_layout()
plt.savefig('canal_boundary_diagnosis.png', dpi=150, bbox_inches='tight')
print(f"\n✅ 诊断图已保存: canal_boundary_diagnosis.png")
print("="*80)
