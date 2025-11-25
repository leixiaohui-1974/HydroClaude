#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
单界面精确通量诊断
Single Interface Exact Flux Diagnostics

目标
1. 直接测试exact_riemann_flux函数
2. 检查是否与理论一致
3. 对比HLL和Exact的差异
"""

import numpy as np
import warnings
warnings.filterwarnings("ignore")
import sys
import os
sys.path.insert(0, os.path.abspath('.'))

try:
    from solvers.riemann_exact import exact_riemann_flux
except ImportError as e:
    print(f"Import error: {e}")
    print("Make sure project root is in sys.path")
    sys.exit(1)


def test_exact_flux_static_water():
    """
    测试1: 静水状态应该零通量
    """
    print("=" * 70)
    print("测试1: 静水状态 (h_L=h_R, Q_L=Q_R=0)")
    print("=" * 70)

    h_L = 2.0
    Q_L = 0.0
    h_R = 2.0
    Q_R = 0.0
    B = 10.0
    g = 9.81

    F_h, F_Q = exact_riemann_flux(h_L, Q_L, h_R, Q_R, B, g)

    print(f"左状态: h={h_L}m, Q={Q_L}m^3/s")
    print(f"右状态: h={h_R}m, Q={Q_R}m^3/s")
    print(f"通量: F_h={F_h:.10f} m^3/s, F_Q={F_Q:.10f} m/s^2")

    if abs(F_h) < 1e-10 and abs(F_Q) < 1e-10:
        print(" 通过: 静水零通量")
    else:
        print(f" 失败: 静水应该零通量但F_h={F_h}, F_Q={F_Q}")

def test_exact_flux_dam_break():
    """
    测试2: 溃坝问题
    """
    print("\n" + "=" * 70)
    print("测试2: 溃坝 (h_L=2m, h_R=1m, 静止)")
    print("=" * 70)

    h_L = 2.0
    Q_L = 0.0
    h_R = 1.0
    Q_R = 0.0
    B = 10.0
    g = 9.81

    F_h, F_Q = exact_riemann_flux(h_L, Q_L, h_R, Q_R, B, g)

    # 理论上稀疏波向左激波向右中间星区
    # x/t=0处应该在星区或稀疏波中
    # 通量应该是正的从高处流向低处

    print(f"左状态: h={h_L}m, Q={Q_L}m^3/s")
    print(f"右状态: h={h_R}m, Q={Q_R}m^3/s")
    print(f"通量: F_h={F_h:.6f} m^3/s, F_Q={F_Q:.6f} m/s^2")

    # 计算对应的采样状态
    u_L = Q_L / (h_L * B) if h_L > 1e-6 else 0.0
    u_R = Q_R / (h_R * B) if h_R > 1e-6 else 0.0

    # F_h = Q = h*u*B, 所以 u = F_h / (h*B)
    # 但我们不知道采样的h需要从F_h和F_Q反推

    if F_h > 0:
        print(" 通量为正从高处流向低处")
    else:
        print(f"  通量为负或零: F_h={F_h}")

def test_mass_conservation_single_step():
    """
    测试3: 单步质量守恒
    """
    print("\n" + "=" * 70)
    print("测试3: 单步质量守恒检查")
    print("=" * 70)

    # 简单的两单元系统
    dx = 2.0
    dt = 0.1
    B = 10.0
    g = 9.81

    # 初始状态
    h = np.array([2.0, 1.0])
    Q = np.array([0.0, 0.0])

    # 初始质量
    mass_0 = np.sum(h * B * dx)
    print(f"初始质量: {mass_0:.6f} m^3")
    print(f"初始h: {h}")

    # 计算界面通量3个界面左边界中间右边界
    # 左边界ghost单元 vs h[0]
    F_h_left, _ = exact_riemann_flux(h[0], Q[0], h[0], Q[0], B, g)

    # 中间界面
    F_h_mid, _ = exact_riemann_flux(h[0], Q[0], h[1], Q[1], B, g)

    # 右边界h[1] vs ghost单元
    F_h_right, _ = exact_riemann_flux(h[1], Q[1], h[1], Q[1], B, g)

    print(f"\n界面通量:")
    print(f"  左边界 (i=0): F_h = {F_h_left:.6f} m^3/s")
    print(f"  中间 (i=1):   F_h = {F_h_mid:.6f} m^3/s")
    print(f"  右边界 (i=2): F_h = {F_h_right:.6f} m^3/s")

    # 更新状态
    dh_dt_0 = -(F_h_mid - F_h_left) / dx
    dh_dt_1 = -(F_h_right - F_h_mid) / dx

    h_new = h + dt * np.array([dh_dt_0, dh_dt_1])

    mass_1 = np.sum(h_new * B * dx)
    mass_error = abs(mass_1 - mass_0) / mass_0 * 100

    print(f"\n单步后:")
    print(f"  h_new: {h_new}")
    print(f"  质量: {mass_1:.6f} m^3")
    print(f"  误差: {mass_error:.6f}%")

    if mass_error < 0.01:
        print(" 质量守恒良好 (<0.01%)")
    elif mass_error < 1.0:
        print(f"  质量误差: {mass_error:.6f}%")
    else:
        print(f" 质量守恒失败: {mass_error:.6f}% > 1%")

def test_fixed_boundary_interaction():
    """
    测试4: 固定边界条件的质量累积
    """
    print("\n" + "=" * 70)
    print("测试4: 固定h边界的质量累积问题")
    print("=" * 70)

    # 模拟诊断测试中的情况
    # - 左边界固定h=2m
    # - 右边界固定h=1m
    # - 初始: 左侧2m右侧1m

    dx = 2.0
    dt = 0.2
    B = 10.0
    g = 9.81

    # 三单元系统简化
    h = np.array([2.0, 1.5, 1.0])
    Q = np.array([0.0, 0.0, 0.0])

    print(f"初始h: {h}")

    # 边界条件固定h
    h_ghost_left = 2.0
    h_ghost_right = 1.0

    for step in range(5):
        mass_0 = np.sum(h * B * dx)

        # 4个界面的通量
        F_h = np.zeros(4)

        # 左边界 (ghost vs h[0])
        F_h[0], _ = exact_riemann_flux(h_ghost_left, 0.0, h[0], Q[0], B, g)

        # 内部界面
        F_h[1], _ = exact_riemann_flux(h[0], Q[0], h[1], Q[1], B, g)
        F_h[2], _ = exact_riemann_flux(h[1], Q[1], h[2], Q[2], B, g)

        # 右边界 (h[2] vs ghost)
        F_h[3], _ = exact_riemann_flux(h[2], Q[2], h_ghost_right, 0.0, B, g)

        # 更新h
        dh_dt = -(F_h[1:] - F_h[:-1]) / dx
        h_new = h + dt * dh_dt

        mass_1 = np.sum(h_new * B * dx)
        mass_error = (mass_1 - mass_0) / mass_0 * 100

        print(f"\n步骤 {step+1}:")
        print(f"  界面通量: {F_h}")
        print(f"  dh/dt: {dh_dt}")
        print(f"  h_new: {h_new}")
        print(f"  质量变化: {mass_1 - mass_0:+.6f} m^3 ({mass_error:+.4f}%)")

        # 检查是否有质量累积
        if abs(mass_error) > 1.0:
            print(f"   质量累积: {mass_error:.4f}%")
            break
        elif abs(mass_error) > 0.1:
            print(f"    质量轻微变化: {mass_error:.4f}%")

        h = h_new

    print(f"\n最终h: {h}")

if __name__ == "__main__":
    test_exact_flux_static_water()
    test_exact_flux_dam_break()
    test_mass_conservation_single_step()
    test_fixed_boundary_interaction()

    print("\n" + "=" * 70)
    print("诊断完成")
    print("=" * 70)
