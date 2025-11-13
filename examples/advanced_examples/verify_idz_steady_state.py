# -*- coding: utf-8 -*-
"""
验证IDZ模型的稳态增益

检查K=-0.3是否正确表示了反向作用

作者：HydroClaude Team
日期：2025-10-24
"""

import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))

import numpy as np
from scipy import signal

print("=" * 80)
print("验证IDZ传递函数的稳态特性")
print("=" * 80)

# IDZ参数
K = -0.3
tau_z = 103.0
tau_d = 206.0
dt = 2.0

print(f"\nIDZ参数:")
print(f"  K = {K}")
print(f"  tau_z = {tau_z}s")
print(f"  tau_d = {tau_d}s")

# 构建连续传递函数 G(s) = K*(1+tau_z*s) / (s*(1+tau_d*s))
# 分子: K + K*tau_z*s
# 分母: tau_d*s^2 + s

num = [K * tau_z, K]  # [K*tau_z, K]
den = [tau_d, 1, 0]    # [tau_d, 1, 0]

sys_c = signal.TransferFunction(num, den)

print(f"\n连续传递函数:")
print(f"  num = {num}")
print(f"  den = {den}")
print(f"  G(s) = {num[0]}*s + {num[1]} / ({den[0]}*s^2 + {den[1]}*s + {den[0]})")

# 离散化
sys_d = sys_c.to_discrete(dt, method='zoh')

print(f"\n离散传递函数 (dt={dt}s):")
print(f"  num_d = {sys_d.num}")
print(f"  den_d = {sys_d.den}")

# 稳态增益测试：施加阶跃输入
print(f"\n" + "=" * 80)
print("阶跃响应测试（验证稳态增益）")
print("=" * 80)

# 生成阶跃输入
t = np.arange(0, 1000, dt)
u_step = np.ones_like(t)  # 单位阶跃

# 计算阶跃响应
tout, y_step = signal.dlsim((sys_d.num, sys_d.den, dt), u_step, t=t)

print(f"\n单位阶跃输入:")
print(f"  u = 1.0 (from t=0 onwards)")

# 检查前几个时间步
print(f"\n前10步响应:")
for i in range(min(10, len(t))):
    print(f"  t={t[i]:.1f}s: y={y_step[i][0]:.6f}")

# 检查最后几步（稳态）
print(f"\n最后10步响应（稳态）:")
for i in range(max(0, len(t)-10), len(t)):
    print(f"  t={t[i]:.1f}s: y={y_step[i][0]:.6f}")

print(f"\n稳态值: y_ss ~= {y_step[-1][0]:.6f}")

# 理论上，有积分器的系统，单位阶跃响应会持续积分
print(f"\n 注意：IDZ模型有积分器（极点在s=0）")
print(f"   单位阶跃输入会导致输出持续增长（或减小）")
print(f"   这是UNSTABLE或MARGINALLY STABLE系统！")

# 测试脉冲响应
print(f"\n" + "=" * 80)
print("脉冲响应测试")
print("=" * 80)

u_impulse = np.zeros_like(t)
u_impulse[0] = 1.0 / dt  # 单位脉冲（近似）

tout, y_impulse = signal.dlsim((sys_d.num, sys_d.den, dt), u_impulse, t=t)

print(f"\n脉冲输入响应（前20步）:")
for i in range(min(20, len(t))):
    print(f"  t={t[i]:.1f}s: y={y_impulse[i][0]:.6f}")

print(f"\n最后几步:")
for i in range(max(0, len(t)-5), len(t)):
    print(f"  t={t[i]:.1f}s: y={y_impulse[i][0]:.6f}")

# 检查增益符号
if y_step[10][0] < 0:
    print(f"\n 增益符号正确：u=+1 -> y<0 (K={K}<0)")
else:
    print(f"\n 增益符号错误：u=+1 -> y>0 (但K={K}<0)")

print(f"\n" + "=" * 80)
print("结论")
print("=" * 80)
print(f"IDZ模型 G(s) = K*(1+tau_z*s)/(s*(1+tau_d*s)) 有积分器")
print(f"这意味着系统对恒定输入会持续积分，导致输出发散")
print(f"这可能不适合建模水渠系统（水位应该稳定在某个值）")
print(f"\n推荐使用一阶模型：H(s) = K/(tau*s+1)")
print("=" * 80)
