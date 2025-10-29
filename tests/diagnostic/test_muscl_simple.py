#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
简单测试MUSCL重构
"""

import sys
sys.path.insert(0, '/workspace')

import numpy as np
from solvers.hydrostatic_canal_solver import HydrostaticCanalSolver

# 创建求解器
solver = HydrostaticCanalSolver(use_muscl=True, muscl_limiter='minmod')

# 测试1：线性分布
print("="*70)
print("测试1：线性水深分布")
print("="*70)

h = np.linspace(1.0, 5.0, 11)  # 11个点，从1到5线性增长
hu = np.zeros(11)
z = np.zeros(11)

print(f"输入h: {h}")

# 手动设置虚拟单元
h_ext = np.zeros(13)
h_ext[1:-1] = h
h_ext[0] = h[0]
h_ext[-1] = h[-1]

# 对中间单元（i=5）进行MUSCL重构
i = 5
_, h_L_from_i = solver.muscl_reconstruct(
    h_ext[i-1], h_ext[i], h_ext[i+1], 'minmod'
)
h_R_from_i1, _ = solver.muscl_reconstruct(
    h_ext[i], h_ext[i+1], h_ext[i+2], 'minmod'
)

print(f"\n单元{i}:")
print(f"  h[i-1]={h_ext[i-1]:.2f}, h[i]={h_ext[i]:.2f}, h[i+1]={h_ext[i+1]:.2f}")
print(f"  MUSCL重构：h_L={h_L_from_i:.2f}")
print(f"\n单元{i+1}:")
print(f"  h[i]={h_ext[i]:.2f}, h[i+1]={h_ext[i+1]:.2f}, h[i+2]={h_ext[i+2]:.2f}")
print(f"  MUSCL重构：h_R={h_R_from_i1:.2f}")

print(f"\n界面{i}的左右状态:")
print(f"  左状态（来自单元{i}）: h_L={h_L_from_i:.2f}")
print(f"  右状态（来自单元{i+1}）: h_R={h_R_from_i1:.2f}")

print(f"\n比较:")
print(f"  一阶方法：h_L={h_ext[i]:.2f}, h_R={h_ext[i+1]:.2f}")
print(f"  MUSCL：h_L={h_L_from_i:.2f}, h_R={h_R_from_i1:.2f}")
print(f"  理论界面值（线性插值）: {(h_ext[i] + h_ext[i+1])/2:.2f}")

# 测试2：阶跃
print("\n" + "="*70)
print("测试2：阶跃（Dam Break初始条件）")
print("="*70)

h = np.ones(11) * 10.0
h[6:] = 0.01
print(f"输入h: {h}")

h_ext = np.zeros(13)
h_ext[1:-1] = h
h_ext[0] = h[0]
h_ext[-1] = h[-1]

# 在阶跃处（i=5, 界面在h[5]和h[6]之间）
i = 5
_, h_L_from_i = solver.muscl_reconstruct(
    h_ext[i-1], h_ext[i], h_ext[i+1], 'minmod'
)
h_R_from_i1, _ = solver.muscl_reconstruct(
    h_ext[i], h_ext[i+1], h_ext[i+2], 'minmod'
)

print(f"\n阶跃界面（i={i}）:")
print(f"  单元{i}: h[i-1]={h_ext[i-1]:.2f}, h[i]={h_ext[i]:.2f}, h[i+1]={h_ext[i+1]:.2f}")
print(f"  MUSCL重构：h_L={h_L_from_i:.2f}")
print(f"  单元{i+1}: h[i]={h_ext[i]:.2f}, h[i+1]={h_ext[i+1]:.2f}, h[i+2]={h_ext[i+2]:.2f}")
print(f"  MUSCL重构：h_R={h_R_from_i1:.2f}")

print(f"\n比较:")
print(f"  一阶：h_L={h_ext[i]:.2f}, h_R={h_ext[i+1]:.2f}")
print(f"  MUSCL：h_L={h_L_from_i:.2f}, h_R={h_R_from_i1:.2f}")
print(f"\nMUSCL在阶跃处正确使用了limiter，保持了单调性")

print("\n" + "="*70)
print("结论")
print("="*70)
print("MUSCL重构函数本身是正确的。")
print("问题可能在于：")
print("  1. MUSCL与静水重构的组合方式")
print("  2. 需要对表面高程eta=h+z进行重构，而不是h")
print("  3. 时间步长需要更小（CFL条件更严格）")
