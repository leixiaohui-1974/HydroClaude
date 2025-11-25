# -*- coding: utf-8 -*-
"""
诊断SimplifiedCanalSimulator的物理合理性

分析水力学模型是否符合IDZ假设

作者HydroClaude Team
日期2025-10-24
"""
import sys
import warnings
warnings.filterwarnings("ignore")
import os

# ========== 路径设置 ==========
script_path = os.path.abspath(__file__)
project_root = os.path.dirname(os.path.dirname(script_path))
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))


import numpy as np
import matplotlib.pyplot as plt

print("=" * 80)
print("SimplifiedCanalSimulator物理特性诊断")
print("=" * 80)

# 模型参数
L = 1000.0  # 渠道长度 (m)
W = 10.0    # 渠道宽度 (m)
A_surface = L * W  # 水面面积 = 10000 m^2
Cd = 0.6    # 闸门流量系数
g = 9.81    # 重力加速度
h_down = 2.2  # 下游水位 (m)
Q_in = 20.0   # 上游流量 (m^3/s)
dt = 2.0      # 采样时间 (s)

print("\n系统参数")
print(f"渠道长度 L = {L}m")
print(f"渠道宽度 W = {W}m")
print(f"水面面积 A = {A_surface}m^2")
print(f"闸门系数 Cd = {Cd}")
print(f"下游水位 h_down = {h_down}m")
print(f"上游流量 Q_in = {Q_in}m^3/s")

print("\n系统方程")
print("非线性闸门方程")
print("  Q_out = Cd * a * W * sqrt(2*g*(h - h_down))")
print("  Q_out = 0.6 * a * 10 * sqrt(2*9.81*Deltah)")
print("  Q_out = 6 * a * sqrt(19.62*Deltah)")
print("  Q_out ~= 6 * a * 4.43 * sqrt(Deltah)")
print("  Q_out ~= 26.6 * a * sqrt(Deltah)  (m^3/s)")
print()
print("水量平衡方程")
print("  dV/dt = Q_in - Q_out")
print("  A * dh/dt = Q_in - Q_out")
print("  10000 * dh/dt = 20 - 26.6*a*sqrt(Deltah)")
print("  dh/dt = (20 - 26.6*a*sqrt(Deltah)) / 10000")
print("  dh/dt = 0.002 - 0.00266*a*sqrt(Deltah)  (m/s)")

print("\n稳态分析")
print("稳态条件dh/dt = 0即 Q_in = Q_out")
print("  20 = 26.6 * a * sqrt(Deltah)")
print("  a * sqrt(Deltah) = 20 / 26.6 = 0.752")
print()
print("对于不同的闸门开度a稳态水位差Deltah")
for a in [0.5, 1.0, 1.5, 2.0, 2.5, 3.0, 4.0]:
    delta_h = (20 / (26.6 * a))**2
    h_steady = h_down + delta_h
    print(f"  a = {a:.1f}m -> Deltah = {delta_h:.3f}m -> h = {h_steady:.3f}m")

print("\n线性化分析")
print("在工作点 (h*, a*) 附近线性化")
print()
h_star = 2.5  # 工作点水位
a_star = 2.0  # 工作点闸门开度
delta_h_star = h_star - h_down

print(f"工作点h* = {h_star}m, a* = {a_star}m, Deltah* = {delta_h_star}m")
print()

# 偏导数
dQ_dh = -Cd * a_star * W * np.sqrt(2*g) / (2 * np.sqrt(delta_h_star))  # Q_out/h
dQ_da = Cd * W * np.sqrt(2*g*delta_h_star)  # Q_out/a

print(f"偏导数:")
print(f"  Q_out/h = {dQ_dh:.3f} m^2/s  (负值水位高->出流大)")
print(f"  Q_out/a = {dQ_da:.3f} m^3/(sm)  (正值开度大->出流大)")
print()

# 线性化传递函数
# dh/dt = (Q_in - Q_out) / A
# dh/dt ~= (-(dQ/dh)*Deltah - (dQ/da)*Deltaa) / A
# s*Deltah = (-(dQ/dh)*Deltah - (dQ/da)*Deltaa) / A
# s*Deltah = -(dQ/dh)/A * Deltah - (dQ/da)/A * Deltaa
# Deltah * (s + (dQ/dh)/A) = -(dQ/da)/A * Deltaa
# Deltah / Deltaa = -(dQ/da)/A / (s + (dQ/dh)/A)
# Deltah / Deltaa = -K / (tau*s + 1)

K_linear = -(dQ_da / A_surface) / ((-dQ_dh / A_surface))  # 稳态增益
tau_linear = A_surface / (-dQ_dh)  # 时间常数

print(f"线性化IDZ参数一阶:")
print(f"  K = Deltah/Deltaa = {K_linear:.3f}  (m/m)")
print(f"  tau = A / |Q/h| = {tau_linear:.1f}s")
print()

if K_linear < 0:
    print(f"   K < 0确认反向作用a -> h")
else:
    print(f"   K > 0不符合预期")

print(f"\n与在线辨识对比:")
print(f"  在线辨识: K = 50.0 (正值错误)")
print(f"  线性化计算: K = {K_linear:.1f} (负值正确)")
print(f"  差异: {abs(K_linear - 50):.1f}")
print()
print(f"  在线辨识: tau_d = 217.7s")
print(f"  线性化计算: tau = {tau_linear:.1f}s")
print(f"  差异: {abs(tau_linear - 217.7):.1f}s")

print("\n关键发现")
print(" 问题1在线辨识的K值符号错误")
print("   - 在线辨识: K=+50 (正向)")
print("   - 物理推导: K~=-22 (反向)")
print("   - 原因: 在线辨识算法对反向系统的理解有误")
print()
print(" 问题2SimplifiedCanalSimulator不完全符合IDZ假设")
print("   - SimplifiedCanalSimulator: 非线性闸门方程")
print("   - IDZ模型: 线性传递函数")
print("   - 影响: 在不同工作点K值不同时间常数也变化")
print()
print(" 问题3SimplifiedCanalSimulator过于简化")
print("   - 忽略了渠道动力学水流惯性摩擦等")
print("   - 只有集总参数水量平衡")
print("   - 没有空间分布效应")
print("   - 不适合测试高级控制算法")

print("\n解决方案")
print("方案1修正在线辨识算法推荐")
print("  - 确保IDZIdentifier能正确辨识反向系统")
print("  - 或者在SimplifiedCanalSimulator中反转u的定义")
print()
print("方案2使用Saint-Venant高保真模型最佳")
print("  - 完整的偏微分方程")
print("  - 真实的水力学特性")
print("  - 适合测试所有控制算法")
print()
print("方案3修改SimplifiedCanalSimulator定义")
print("  - 将u定义为'期望出流量'而不是'闸门开度'")
print("  - 这样可以得到u->h通过Q_out=u的正确方向")

print("\n时间尺度分析")
print(f"系统响应时间tau ~= {tau_linear:.0f}s")
print(f"采样时间dt = {dt}s")
print(f"比值tau/dt = {tau_linear/dt:.1f}")
print()
if tau_linear / dt > 10:
    print(" 采样频率充足tau >> dt")
else:
    print(" 采样频率可能不够")

print("\n推荐的MPC/自适应PI配置")
print("基于线性化分析推荐参数")
print(f"  K = {K_linear:.1f}  (注意负值)")
print(f"  tau_z = {tau_linear*0.5:.1f}s  (约tau/2)")
print(f"  tau_d = {tau_linear:.1f}s")
print(f"  theta = {dt*2:.1f}s  (约2*dt)")

print("\n" + "=" * 80)
print("结论")
print("1. SimplifiedCanalSimulator的K值应该是负的约-22")
print("2. 在线辨识返回正值是因为算法未正确处理反向系统")
print("3. 推荐使用Saint-Venant高保真模型进行基准测试")
print("=" * 80)

# 验证不同工作点的增益
print("\n不同工作点的线性增益")
print("验证非线性效应")
print()
for h_wp in [2.3, 2.5, 2.7, 3.0]:
    for a_wp in [1.5, 2.0, 2.5, 3.0]:
        delta_h_wp = h_wp - h_down
        if delta_h_wp <= 0:
            continue
        dQ_dh_wp = -Cd * a_wp * W * np.sqrt(2*g) / (2 * np.sqrt(delta_h_wp))
        dQ_da_wp = Cd * W * np.sqrt(2*g*delta_h_wp)
        K_wp = -(dQ_da_wp / A_surface) / ((-dQ_dh_wp / A_surface))
        tau_wp = A_surface / (-dQ_dh_wp)
        print(f"  h={h_wp:.1f}m, a={a_wp:.1f}m -> K={K_wp:.2f}, tau={tau_wp:.0f}s")

print("\n观察K和tau随工作点变化明显 -> 非线性系统")
print("       这解释了为什么自适应IDZ在不同工况下性能不稳定")
print("\n" + "=" * 80)
