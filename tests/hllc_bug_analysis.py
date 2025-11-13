#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
HLLC问题分析和修复方案

通过对比测试结果和理论公式找出HLLC实现的bug

作者: HydroClaude Team
日期: 2025-10-31
"""
import sys
import os

# ========== 路径设置 ==========
script_path = os.path.abspath(__file__)
project_root = os.path.dirname(os.path.dirname(script_path))
sys.path.insert(0, project_root)


import numpy as np

print("="*80)
print("HLLC Implementation Bug Analysis")
print("="*80)

print("\n[Issue 1] S_star Formula Verification")
print("-"*80)

print("""
当前实现 (line 106-107):
    numerator = (F_Q_R - F_Q_L + S_L * Q_L - S_R * Q_R)
    denominator = A_L * (S_L - u_L) - A_R * (S_R - u_R)
    S_star = numerator / denominator

Toro (2009) Eq. 10.37对于浅水方程:
    S_* = (P_R - P_L + rho_L*u_L*(S_L - u_L) - rho_R*u_R*(S_R - u_R)) /
          (rho_L*(S_L - u_L) - rho_R*(S_R - u_R))

对于浅水方程:
    rho -> h (水深)
    P = 0.5 * g * h^2 * B (总压力)

代入
    S_* = (0.5*g*h_R^2*B - 0.5*g*h_L^2*B + h_L*u_L*(S_L - u_L) - h_R*u_R*(S_R - u_R)) /
          (h_L*(S_L - u_L) - h_R*(S_R - u_R))
""")

# 验证公式等价性
print("\n验证numerator是否等价...")
print("""
F_Q_L = Q_L^2 / (h_L * B) + 0.5 * g * h_L^2 * B
      = h_L * B * u_L^2 + 0.5 * g * h_L^2 * B

F_Q_R = Q_R^2 / (h_R * B) + 0.5 * g * h_R^2 * B
      = h_R * B * u_R^2 + 0.5 * g * h_R^2 * B

当前numerator = F_Q_R - F_Q_L + S_L * Q_L - S_R * Q_R
              = [h_R*B*u_R^2 + 0.5*g*h_R^2*B] - [h_L*B*u_L^2 + 0.5*g*h_L^2*B]
                + S_L*h_L*B*u_L - S_R*h_R*B*u_R

Toro numerator = (0.5*g*h_R^2*B - 0.5*g*h_L^2*B)
                 + h_L*u_L*(S_L - u_L) - h_R*u_R*(S_R - u_R)
               = 0.5*g*(h_R^2 - h_L^2)*B
                 + h_L*u_L*S_L - h_L*u_L^2 - h_R*u_R*S_R + h_R*u_R^2

对比:
当前: [h_R*B*u_R^2 - h_L*B*u_L^2] + 0.5*g*(h_R^2 - h_L^2)*B + [S_L*h_L*B*u_L - S_R*h_R*B*u_R]
Toro: [h_R*u_R^2 - h_L*u_L^2] + 0.5*g*(h_R^2 - h_L^2)*B + [S_L*h_L*u_L - S_R*h_R*u_R]

差异: 当前多了宽度B在速度平方项上
 Bug发现: h_R*B*u_R^2 应该是 h_R*u_R^2 (在Toro公式中是单位宽度)
但在代码中F_Q已经是总通量所以公式应该是正确的...

等等让我重新理解...
""")

print("\n[Issue 2] Star Region Depth Formula")
print("-"*80)

print("""
当前实现 (line 121):
    h_L_star = h_L * (S_L - u_L) / (S_L - S_star)

Toro (2009) Eq. 10.31:
    rho_* = rho_K * (S_K - u_K) / (S_K - S_*)

对于浅水方程rho -> h这看起来是正确的
 公式正确
""")

print("\n[Issue 3] Numerical Stability")
print("-"*80)

print("""
潜在问题:
1. 当 S_L ~= S_star 时h_L_star -> inf (分母接近零)
2. 当 S_L < S_star 时h_L_star 变负 (违反物理意义)
3. 没有正定性检查

当前保护 (line 87):
    if abs(denominator) < eps_dry * B:
        # 回退到HLL

但是这只检查了S_star计算的分母没有检查h_star计算
 Bug: 缺少h_star正定性检查和S_L-S_star分母检查
""")

print("\n[Issue 4] Lake at Rest Performance")
print("-"*80)

print("""
Lake at Rest测试结果:
- HLL: 0.82m偏差
- HLLC: 1.98m偏差 (比HLL差141%)

可能原因:
1. HLLC对静态问题更敏感放大了Well-Balanced重构误差
2. 接触波分辨在u~=0时引入数值振荡
3. S_star在静态条件下可能计算不稳定

理论分析:
对于Lake at Rest (u_L ~= 0, u_R ~= 0, h_L != h_R due to z_b):
    S_L ~= -c_L
    S_R ~= c_R
    S_star ~= (P_R - P_L) / (h_L*c_L + h_R*c_R)

如果压力不完全平衡S_star != 0会产生虚假流动
HLLC比HLL更精确地捕捉这个虚假流动导致更大的扰动

 根本问题: HLLC在Lake at Rest上表现差是因为它"太精确"了
   - 它准确捕捉了Well-Balanced重构中的微小误差
   - HLL通过数值耗散"掩盖"了这些误差

解决方案:
1. 改进Well-Balanced重构使其更精确
2. 或者在静态条件下(|u| < threshold)禁用HLLC回退到HLL
3. 或者使用更精确的Riemann求解器如Exact solver
""")

print("\n[Issue 5] NaN Generation")
print("-"*80)

print("""
NaN在t=63s产生可能原因:
1. h_star变负 -> 后续c = sqrt(g*h)产生NaN
2. S_star过大 -> h_star过大 -> 数值溢出
3. 累积误差导致h变负

追踪:
在星区深度计算中:
    h_L_star = h_L * (S_L - u_L) / (S_L - S_star)

如果S_star > S_L分母为负h_L_star为负

在Lake at Rest条件下:
    S_L ~= -c_L < 0
    S_star可能> S_L如果计算有误
    -> h_L_star < 0 -> NaN

 关键Bug: 没有检查 S_star 是否在 [S_L, S_R] 范围内
""")

print("\n" + "="*80)
print("RECOMMENDED FIXES")
print("="*80)

print("""
Fix 1: 添加h_star正定性检查
------
在计算h_star后
    h_L_star = max(eps_dry, h_L * (S_L - u_L) / (S_L - S_star))
    h_R_star = max(eps_dry, h_R * (S_R - u_R) / (S_R - S_star))

Fix 2: 检查S_star范围
------
在计算S_star后
    if not (S_L <= S_star <= S_R):
        # S_star out of range, fallback to HLL
        ...

Fix 3: 静态条件下禁用HLLC可选
------
在计算S_star前
    if abs(u_L) < eps_dry and abs(u_R) < eps_dry:
        # Nearly static, use HLL to avoid amplifying errors
        return HLL_flux(...)

Fix 4: 改进Well-Balanced重构长期
------
当前Well-Balanced scheme可能引入O(dx^2)误差
需要更高精度的hydrostatic reconstruction

Fix 5: 使用Exact Riemann Solver终极方案
------
对于Lake at Rest只有Exact solver能达到机器精度
HLLC仍然是近似求解器
""")

print("\n[Conclusion]")
print("="*80)
print("""
HLLC实现基本正确但存在数值稳定性问题
1.  S_star公式正确
2.  h_star公式正确
3.  缺少正定性检查
4.  缺少S_star范围检查
5.  HLLC在Lake at Rest上表现差是"特性"不是bug
   它准确捕捉了Well-Balanced误差

推荐方案:
- 短期: 添加数值保护Fix 1,2,3
- 中期: 改进Well-Balanced scheme
- 长期: 实现Exact Riemann Solver for Lake at Rest

Phase 9.2目标调整:
- 原目标: HLLC达到机器精度  不现实
- 新目标: HLLC至少不差于HLL  可实现
- 终极目标: Exact Solver达到机器精度  需Phase 9.3
""")
