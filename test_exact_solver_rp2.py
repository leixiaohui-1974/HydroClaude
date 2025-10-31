#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
测试精确Riemann求解器对RP2的处理
"""

import sys
import os
sys.path.insert(0, os.path.dirname(__file__))

import numpy as np
import matplotlib.pyplot as plt
from tests.verification.toro_riemann_solver import exact_riemann_solution, riemann_structure

# RP2参数
h_L = 5.0
u_L = 5.0
h_R = 5.0
u_R = -5.0
t = 0.5
x_dam = 50.0

print("="*70)
print("测试精确Riemann求解器 - RP2")
print("="*70)

# 波结构
structure = riemann_structure(h_L, u_L, h_R, u_R)
print(f"\n波结构:")
print(f"  h* = {structure['h_star']:.4f} m")
print(f"  u* = {structure['u_star']:.4f} m/s")
print(f"  左波: {structure['wave_type_L']}")
print(f"  右波: {structure['wave_type_R']}")

if structure['wave_type_L'] == 'shock':
    print(f"  左激波速度: S_L = {structure['S_L']:.4f} m/s")
else:
    print(f"  左稀疏波: λ_tail={structure['lambda_L_tail']:.4f}, λ_head={structure['lambda_L_head']:.4f}")

if structure['wave_type_R'] == 'shock':
    print(f"  右激波速度: S_R = {structure['S_R']:.4f} m/s")
else:
    print(f"  右稀疏波: λ_head={structure['lambda_R_head']:.4f}, λ_tail={structure['lambda_R_tail']:.4f}")

# 计算精确解
x = np.linspace(0, 100, 1000)
h, u = exact_riemann_solution(x, t, h_L, u_L, h_R, u_R, x_dam)

print(f"\n精确解统计:")
print(f"  h范围: [{h.min():.4f}, {h.max():.4f}] m")
print(f"  u范围: [{u.min():.4f}, {u.max():.4f}] m/s")

# 检查中间区域
center_mask = (x > x_dam - 5) & (x < x_dam + 5)
h_center = h[center_mask]
u_center = u[center_mask]
print(f"\n中心区域 (x∈[45, 55]m):")
print(f"  h范围: [{h_center.min():.4f}, {h_center.max():.4f}] m")
print(f"  u范围: [{u_center.min():.4f}, {u_center.max():.4f}] m/s")

# 绘图
fig, axes = plt.subplots(2, 1, figsize=(12, 8))

axes[0].plot(x, h, 'b-', linewidth=2)
axes[0].axvline(x_dam, color='k', linestyle=':', label='Initial disc.')
axes[0].axhline(structure['h_star'], color='r', linestyle='--', label=f"h* = {structure['h_star']:.2f}m")
axes[0].set_ylabel('Water Depth h (m)', fontsize=12)
axes[0].set_title(f'RP2 Exact Solution - t={t}s', fontsize=14, weight='bold')
axes[0].legend()
axes[0].grid(True, alpha=0.3)
axes[0].set_ylim([0, max(h)*1.1])

axes[1].plot(x, u, 'r-', linewidth=2)
axes[1].axvline(x_dam, color='k', linestyle=':')
axes[1].axhline(structure['u_star'], color='b', linestyle='--', label=f"u* = {structure['u_star']:.2f}m/s")
axes[1].set_xlabel('Distance x (m)', fontsize=12)
axes[1].set_ylabel('Velocity u (m/s)', fontsize=12)
axes[1].legend()
axes[1].grid(True, alpha=0.3)

plt.tight_layout()
plt.savefig('rp2_exact_solution.png', dpi=150)
print(f"\n✅ 图像已保存: rp2_exact_solution.png")
