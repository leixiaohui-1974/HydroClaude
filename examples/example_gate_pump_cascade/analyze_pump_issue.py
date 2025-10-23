#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
详细分析泵站前后水位问题
"""
import numpy as np
import matplotlib.pyplot as plt

print("="*90)
print("泵站前后水位详细分析".center(90))
print("="*90)

# 加载数据
steady_data = np.load('results/steady_state_data.npz')
transient_data = np.load('results/transient_data.npz')

x = steady_data['x']
h_steady = steady_data['h']
q_steady = steady_data['q']

h_history = transient_data['h_history']
q_history = transient_data['q_history']
time = transient_data['time']

# 结构物位置
gate1_pos = 25000.0  # m
pump_pos = 50000.0   # m
gate2_pos = 75000.0  # m
L_total = 100000.0   # m

# 找到结构物索引
nx = len(x)
gate1_idx = int(gate1_pos / L_total * (nx - 1))
pump_idx = int(pump_pos / L_total * (nx - 1))
gate2_idx = int(gate2_pos / L_total * (nx - 1))

print("\n" + "▶ 结构物位置信息".ljust(90, " "))
print(f"  Gate1: x={x[gate1_idx]/1000:.2f} km, index={gate1_idx}")
print(f"  Pump:  x={x[pump_idx]/1000:.2f} km, index={pump_idx}")
print(f"  Gate2: x={x[gate2_idx]/1000:.2f} km, index={gate2_idx}")

print("\n" + "="*90)
print("1. 稳态纵剖面分析".center(90))
print("="*90)

# 泵站附近详细分析（±5km范围）
pump_vicinity_range = 5000  # m
pump_vicinity_dx = L_total / (nx - 1)
pump_vicinity_points = int(pump_vicinity_range / pump_vicinity_dx)

pump_start_idx = max(0, pump_idx - pump_vicinity_points)
pump_end_idx = min(nx, pump_idx + pump_vicinity_points + 1)

x_pump_vicinity = x[pump_start_idx:pump_end_idx]
h_pump_vicinity = h_steady[pump_start_idx:pump_end_idx]

print(f"\n泵站附近详细水深（±5km范围）:")
print(f"  位置范围: {x_pump_vicinity[0]/1000:.2f} - {x_pump_vicinity[-1]/1000:.2f} km")
print(f"  数据点数: {len(x_pump_vicinity)}")

# 找到泵站上下游的水深（取±1km处避免尖峰影响）
upstream_1km_idx = pump_idx - int(1000 / pump_vicinity_dx)
downstream_1km_idx = pump_idx + int(1000 / pump_vicinity_dx)

if upstream_1km_idx >= 0 and downstream_1km_idx < nx:
    h_upstream_1km = h_steady[upstream_1km_idx]
    h_downstream_1km = h_steady[downstream_1km_idx]
    h_at_pump = h_steady[pump_idx]

    print(f"\n泵站水位详情:")
    print(f"  上游1km处水深: {h_upstream_1km:.4f} m (x={x[upstream_1km_idx]/1000:.2f} km)")
    print(f"  泵站处水深:     {h_at_pump:.4f} m (x={x[pump_idx]/1000:.2f} km)")
    print(f"  下游1km处水深: {h_downstream_1km:.4f} m (x={x[downstream_1km_idx]/1000:.2f} km)")
    print(f"\n  实际扬程效果:")
    print(f"    下游 - 上游: {h_downstream_1km - h_upstream_1km:.4f} m")
    print(f"    泵站 - 上游: {h_at_pump - h_upstream_1km:.4f} m")
    print(f"    泵站 - 下游: {h_at_pump - h_downstream_1km:.4f} m")
    print(f"\n  ⚠️  理论扬程: 5.00 m")
    print(f"  ⚠️  期望结果: 下游水深应该 ≈ 上游水深 + 5.0 m = {h_upstream_1km + 5.0:.4f} m")
    print(f"  ⚠️  实际结果: 下游水深 = {h_downstream_1km:.4f} m")
    print(f"  ⚠️  偏差: {h_downstream_1km - (h_upstream_1km + 5.0):.4f} m")

# 分析泵站处的尖峰
h_max_vicinity = np.max(h_pump_vicinity)
h_min_vicinity = np.min(h_pump_vicinity)
h_max_idx = pump_start_idx + np.argmax(h_pump_vicinity)

print(f"\n泵站附近尖峰分析:")
print(f"  最大水深: {h_max_vicinity:.4f} m (x={x[h_max_idx]/1000:.2f} km)")
print(f"  最小水深: {h_min_vicinity:.4f} m (x={x[pump_start_idx + np.argmin(h_pump_vicinity)]/1000:.2f} km)")
print(f"  尖峰高度: {h_max_vicinity - h_min_vicinity:.4f} m")

if h_max_vicinity - h_min_vicinity > 1.0:
    print(f"  ❌ 警告: 泵站处存在显著尖峰 (>{h_max_vicinity - h_min_vicinity:.2f}m)")

print("\n" + "="*90)
print("2. 非稳态时间演化分析".center(90))
print("="*90)

print(f"\n时间序列信息:")
print(f"  时间点数: {len(time)}")
print(f"  时间范围: {time[0]:.1f} - {time[-1]:.1f} s")
print(f"  时间步长: {time[1] - time[0]:.1f} s (平均)")

# 提取泵站下游水位的时间序列
h_pump_time = h_history[:, pump_idx]
h_downstream_1km_time = h_history[:, downstream_1km_idx]
h_upstream_1km_time = h_history[:, upstream_1km_idx]

print(f"\n泵站下游水位时间演化:")
for i in range(0, len(time), max(1, len(time)//10)):
    print(f"  t={time[i]:7.1f}s: 上游={h_upstream_1km_time[i]:.4f}m, "
          f"泵站={h_pump_time[i]:.4f}m, 下游={h_downstream_1km_time[i]:.4f}m, "
          f"扬程效果={h_downstream_1km_time[i] - h_upstream_1km_time[i]:.4f}m")

# 检查最后几个时间点是否稳定
if len(time) >= 5:
    final_5_values = h_downstream_1km_time[-5:]
    std_final_5 = np.std(final_5_values)
    mean_final_5 = np.mean(final_5_values)

    print(f"\n最后5个时间点统计:")
    print(f"  平均值: {mean_final_5:.4f} m")
    print(f"  标准差: {std_final_5:.6f} m")

    if std_final_5 > 0.01:
        print(f"  ❌ 警告: 最终状态未达到稳态 (标准差={std_final_5:.6f}m > 0.01m)")
    else:
        print(f"  ✅ 最终状态已基本稳定 (标准差={std_final_5:.6f}m < 0.01m)")

print("\n" + "="*90)
print("3. 生成详细分析图".center(90))
print("="*90)

fig, axes = plt.subplots(3, 1, figsize=(14, 10))

# 图1: 稳态纵剖面 - 全局
ax1 = axes[0]
ax1.plot(x/1000, h_steady, 'b-', linewidth=2, label='Steady-State Water Depth')
ax1.axvline(gate1_pos/1000, color='green', linestyle='--', alpha=0.6, label='Gate1')
ax1.axvline(pump_pos/1000, color='red', linestyle='--', alpha=0.6, label='Pump')
ax1.axvline(gate2_pos/1000, color='green', linestyle='--', alpha=0.6, label='Gate2')
ax1.set_xlabel('Distance (km)', fontsize=12)
ax1.set_ylabel('Water Depth (m)', fontsize=12)
ax1.set_title('Steady-State Longitudinal Profile', fontsize=14, fontweight='bold')
ax1.legend(fontsize=10)
ax1.grid(True, alpha=0.3)

# 图2: 稳态纵剖面 - 泵站局部放大
ax2 = axes[1]
ax2.plot(x_pump_vicinity/1000, h_pump_vicinity, 'b-', linewidth=2, marker='o', markersize=3)
ax2.axvline(pump_pos/1000, color='red', linestyle='--', alpha=0.8, linewidth=2, label='Pump Station')
ax2.axhline(h_upstream_1km, color='green', linestyle=':', alpha=0.6, label=f'Upstream (-1km): {h_upstream_1km:.3f}m')
ax2.axhline(h_downstream_1km, color='purple', linestyle=':', alpha=0.6, label=f'Downstream (+1km): {h_downstream_1km:.3f}m')
ax2.axhline(h_upstream_1km + 5.0, color='orange', linestyle='-.', alpha=0.6, linewidth=2,
            label=f'Expected (upstream+5m): {h_upstream_1km + 5.0:.3f}m')
ax2.fill_between([x_pump_vicinity[0]/1000, x_pump_vicinity[-1]/1000],
                  h_upstream_1km, h_upstream_1km + 5.0, alpha=0.1, color='orange')
ax2.set_xlabel('Distance (km)', fontsize=12)
ax2.set_ylabel('Water Depth (m)', fontsize=12)
ax2.set_title('Pump Station Vicinity (±5km) - Steady State', fontsize=14, fontweight='bold')
ax2.legend(fontsize=9, loc='best')
ax2.grid(True, alpha=0.3)

# 图3: 非稳态时间演化 - 泵站上下游水位
ax3 = axes[2]
ax3.plot(time/3600, h_upstream_1km_time, 'g-', linewidth=2, label='Upstream (-1km)', marker='o', markersize=4)
ax3.plot(time/3600, h_pump_time, 'r-', linewidth=2, label='At Pump', marker='s', markersize=4)
ax3.plot(time/3600, h_downstream_1km_time, 'b-', linewidth=2, label='Downstream (+1km)', marker='^', markersize=4)
ax3.axhline(h_upstream_1km + 5.0, color='orange', linestyle='-.', alpha=0.6, linewidth=2,
            label=f'Expected downstream: {h_upstream_1km + 5.0:.3f}m')
ax3.set_xlabel('Time (hours)', fontsize=12)
ax3.set_ylabel('Water Depth (m)', fontsize=12)
ax3.set_title('Transient Evolution at Pump Station', fontsize=14, fontweight='bold')
ax3.legend(fontsize=10, loc='best')
ax3.grid(True, alpha=0.3)

plt.tight_layout()
output_path = 'results/08_pump_issue_analysis.png'
plt.savefig(output_path, dpi=150, bbox_inches='tight')
print(f"\n  Saved: {output_path}")

print("\n" + "="*90)
print("分析完成".center(90))
print("="*90)
