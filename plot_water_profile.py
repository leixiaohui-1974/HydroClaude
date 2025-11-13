#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""绘制详细的水位纵剖面图"""

import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.patches import Rectangle
import matplotlib.patches as mpatches

# 中文字体设置
plt.rcParams['font.sans-serif'] = ['DejaVu Sans']
plt.rcParams['axes.unicode_minus'] = False

# 加载稳态数据
data = np.load('examples/example_gate_pump_cascade/results/steady_state_data.npz')
x = data['x']
h = data['h']
q = data['q']
gate1_pos = data['gate1_pos']
pump_pos = data['pump_pos']
gate2_pos = data['gate2_pos']

# 计算底床高程
S0 = 0.0001
z = -S0 * x
pump_idx = np.argmin(np.abs(x - pump_pos))
z[pump_idx:] += 5.0

# 计算水位
eta = z + h

# 找到关键位置
gate1_idx = np.argmin(np.abs(x - gate1_pos))
gate2_idx = np.argmin(np.abs(x - gate2_pos))

# 创建图表
fig, ax = plt.subplots(figsize=(18, 10))

# 绘制底床
ax.fill_between(x/1000, z, -20, color='saddlebrown', alpha=0.3, label='Bed')
ax.plot(x/1000, z, 'k-', linewidth=2, label='Bed Level')

# 绘制水位
ax.plot(x/1000, eta, 'b-', linewidth=3, label='Water Level', zorder=3)

# 填充水体
ax.fill_between(x/1000, z, eta, color='cyan', alpha=0.4, label='Water')

# 标记关键位置
# 闸门1
ax.axvline(gate1_pos/1000, color='red', linestyle='--', linewidth=2, alpha=0.7)
ax.text(gate1_pos/1000, ax.get_ylim()[1]*0.95, 'Gate 1\n(25km)', 
        color='red', fontsize=12, ha='center', va='top',
        bbox=dict(boxstyle='round', facecolor='white', edgecolor='red', alpha=0.9))

# 泵站
ax.axvline(pump_pos/1000, color='purple', linestyle='--', linewidth=2, alpha=0.7)
ax.text(pump_pos/1000, ax.get_ylim()[1]*0.95, 'Pump Station\n(50km)', 
        color='purple', fontsize=12, ha='center', va='top',
        bbox=dict(boxstyle='round', facecolor='white', edgecolor='purple', alpha=0.9))

# 闸门2
ax.axvline(gate2_pos/1000, color='red', linestyle='--', linewidth=2, alpha=0.7)
ax.text(gate2_pos/1000, ax.get_ylim()[1]*0.95, 'Gate 2\n(75km)', 
        color='red', fontsize=12, ha='center', va='top',
        bbox=dict(boxstyle='round', facecolor='white', edgecolor='red', alpha=0.9))

# 标注泵站前后水位
# 泵站前
ax.plot(x[pump_idx-1]/1000, eta[pump_idx-1], 'o', color='darkblue', 
        markersize=12, zorder=5, markeredgecolor='white', markeredgewidth=2)
ax.annotate(f'Before Pump\n{chr(951)}={eta[pump_idx-1]:.2f}m', 
            xy=(x[pump_idx-1]/1000, eta[pump_idx-1]), 
            xytext=(x[pump_idx-1]/1000-5, eta[pump_idx-1]+2),
            fontsize=11, color='darkblue', fontweight='bold',
            bbox=dict(boxstyle='round', facecolor='lightblue', alpha=0.9),
            arrowprops=dict(arrowstyle='->', color='darkblue', lw=2))

# 泵站后
ax.plot(x[pump_idx+1]/1000, eta[pump_idx+1], 'o', color='darkgreen', 
        markersize=12, zorder=5, markeredgecolor='white', markeredgewidth=2)
ax.annotate(f'After Pump\n{chr(951)}={eta[pump_idx+1]:.2f}m', 
            xy=(x[pump_idx+1]/1000, eta[pump_idx+1]), 
            xytext=(x[pump_idx+1]/1000+5, eta[pump_idx+1]+2),
            fontsize=11, color='darkgreen', fontweight='bold',
            bbox=dict(boxstyle='round', facecolor='lightgreen', alpha=0.9),
            arrowprops=dict(arrowstyle='->', color='darkgreen', lw=2))

# 绘制泵站扬程箭头
y_mid = (eta[pump_idx-1] + eta[pump_idx+1]) / 2
ax.annotate('', xy=(pump_pos/1000+0.5, eta[pump_idx+1]), 
            xytext=(pump_pos/1000+0.5, eta[pump_idx-1]),
            arrowprops=dict(arrowstyle='<->', color='red', lw=3))
ax.text(pump_pos/1000+1.5, y_mid, f'Pump Head\n{chr(916)}{chr(951)}=5.00m', 
        fontsize=12, color='red', fontweight='bold',
        bbox=dict(boxstyle='round', facecolor='yellow', alpha=0.9))

# 标注渠首和渠尾
ax.plot(x[0]/1000, eta[0], 's', color='navy', markersize=10, zorder=5)
ax.text(x[0]/1000, eta[0]+1.5, f'Upstream\n{chr(951)}={eta[0]:.2f}m', 
        fontsize=10, ha='center', color='navy',
        bbox=dict(boxstyle='round', facecolor='lightcyan', alpha=0.8))

ax.plot(x[-1]/1000, eta[-1], 's', color='navy', markersize=10, zorder=5)
ax.text(x[-1]/1000, eta[-1]+1.5, f'Downstream\n{chr(951)}={eta[-1]:.2f}m', 
        fontsize=10, ha='center', color='navy',
        bbox=dict(boxstyle='round', facecolor='lightcyan', alpha=0.8))

# 图表设置
ax.set_xlabel('Distance (km)', fontsize=14, fontweight='bold')
ax.set_ylabel('Elevation (m)', fontsize=14, fontweight='bold')
ax.set_title('Steady Flow Water Level Profile - Series Gate-Pump System\n' + 
             f'Q=30 m³/s, Pump Head=5m, Channel Length=100km',
             fontsize=16, fontweight='bold')
ax.grid(True, alpha=0.3, linestyle='--')
ax.legend(fontsize=11, loc='upper right')

# 设置y轴范围，确保所有重要信息可见
y_min = min(z.min(), eta.min()) - 2
y_max = max(z.max(), eta.max()) + 3
ax.set_ylim(y_min, y_max)

plt.tight_layout()

# 保存图表
output_path = 'examples/example_gate_pump_cascade/results/detailed_water_profile.png'
fig.savefig(output_path, dpi=150, bbox_inches='tight')
print(f' 图表已保存: {output_path}')

# 创建第二个图：局部放大泵站区域
fig2, ax2 = plt.subplots(figsize=(14, 8))

# 选择泵站周围±10km的区域
pump_region_mask = (x >= (pump_pos - 10000)) & (x <= (pump_pos + 10000))
x_region = x[pump_region_mask]
z_region = z[pump_region_mask]
h_region = h[pump_region_mask]
eta_region = eta[pump_region_mask]

# 绘制
ax2.fill_between(x_region/1000, z_region, z_region.min()-1, 
                 color='saddlebrown', alpha=0.3)
ax2.plot(x_region/1000, z_region, 'k-', linewidth=3, label='Bed Level')
ax2.plot(x_region/1000, eta_region, 'b-', linewidth=4, label='Water Level', zorder=3)
ax2.fill_between(x_region/1000, z_region, eta_region, color='cyan', alpha=0.5)

# 标记泵站位置
ax2.axvline(pump_pos/1000, color='purple', linestyle='--', linewidth=3, alpha=0.7)
ax2.text(pump_pos/1000, ax2.get_ylim()[1]*0.95, 'Pump Station', 
         color='purple', fontsize=14, ha='center', va='top', fontweight='bold',
         bbox=dict(boxstyle='round', facecolor='white', edgecolor='purple', linewidth=2))

# 标注关键数据
pump_idx_region = np.argmin(np.abs(x_region - pump_pos))
idx_before = pump_idx_region - 1
idx_after = pump_idx_region + 1

# 泵前
ax2.plot(x_region[idx_before]/1000, eta_region[idx_before], 'o', 
         color='red', markersize=15, zorder=5)
ax2.text(x_region[idx_before]/1000, eta_region[idx_before]-1.5, 
         f'Before Pump\nh={h_region[idx_before]:.3f}m\n{chr(951)}={eta_region[idx_before]:.3f}m', 
         fontsize=12, ha='center', color='red', fontweight='bold',
         bbox=dict(boxstyle='round', facecolor='yellow', alpha=0.9))

# 泵后
ax2.plot(x_region[idx_after]/1000, eta_region[idx_after], 'o', 
         color='green', markersize=15, zorder=5)
ax2.text(x_region[idx_after]/1000, eta_region[idx_after]+1.5, 
         f'After Pump\nh={h_region[idx_after]:.3f}m\n{chr(951)}={eta_region[idx_after]:.3f}m', 
         fontsize=12, ha='center', color='green', fontweight='bold',
         bbox=dict(boxstyle='round', facecolor='lightgreen', alpha=0.9))

# 扬程箭头
ax2.annotate('', xy=(pump_pos/1000+0.5, eta_region[idx_after]), 
             xytext=(pump_pos/1000+0.5, eta_region[idx_before]),
             arrowprops=dict(arrowstyle='<->', color='red', lw=4))
delta_h = h_region[idx_after] - h_region[idx_before]
delta_eta = eta_region[idx_after] - eta_region[idx_before]
ax2.text(pump_pos/1000+1.5, (eta_region[idx_before]+eta_region[idx_after])/2, 
         f'{chr(916)}{chr(951)}={delta_eta:.3f}m\n{chr(916)}h={delta_h:.3f}m', 
         fontsize=13, color='red', fontweight='bold',
         bbox=dict(boxstyle='round', facecolor='orange', alpha=0.9))

ax2.set_xlabel('Distance (km)', fontsize=14, fontweight='bold')
ax2.set_ylabel('Elevation (m)', fontsize=14, fontweight='bold')
ax2.set_title('Pump Station Region - Zoomed View (±10km)\n' + 
              'Demonstrating Water Level Jump at Pump',
              fontsize=16, fontweight='bold')
ax2.grid(True, alpha=0.4, linestyle='--')
ax2.legend(fontsize=12, loc='best')

plt.tight_layout()

output_path2 = 'examples/example_gate_pump_cascade/results/pump_region_detail.png'
fig2.savefig(output_path2, dpi=150, bbox_inches='tight')
print(f' 局部放大图已保存: {output_path2}')

print('\n所有图表生成完成！')
