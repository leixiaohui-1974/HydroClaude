#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Riemann求解器集合

实现多种Riemann求解器用于浅水方程：
- HLL (Harten-Lax-van Leer)
- HLLC (HLL with Contact)

作者: Claude
日期: 2025-10-23
"""

import numpy as np


def hll_flux_shallow_water(U_L, U_R, B, g=9.81):
    """
    HLL Riemann求解器用于浅水方程（矩形断面）

    Args:
        U_L: 左状态 [A, Q]
        U_R: 右状态 [A, Q]
        B: 渠道宽度 (m)
        g: 重力加速度 (m/s²)

    Returns:
        F_hll: HLL通量 [F_A, F_Q]
    """
    # 提取左右状态
    A_L, Q_L = U_L
    A_R, Q_R = U_R

    # 计算水深（矩形断面）
    h_L = A_L / B if A_L > 1e-10 else 1e-10
    h_R = A_R / B if A_R > 1e-10 else 1e-10

    # 计算流速
    u_L = Q_L / A_L if A_L > 1e-10 else 0.0
    u_R = Q_R / A_R if A_R > 1e-10 else 0.0

    # 计算波速
    c_L = np.sqrt(g * h_L)
    c_R = np.sqrt(g * h_R)

    # Roe平均
    sqrt_h_L = np.sqrt(h_L)
    sqrt_h_R = np.sqrt(h_R)
    h_roe = (sqrt_h_L * h_L + sqrt_h_R * h_R) / (sqrt_h_L + sqrt_h_R)
    u_roe = (sqrt_h_L * u_L + sqrt_h_R * u_R) / (sqrt_h_L + sqrt_h_R)
    c_roe = np.sqrt(g * h_roe)

    # 波速估计
    s_L = min(u_L - c_L, u_roe - c_roe)
    s_R = max(u_R + c_R, u_roe + c_roe)

    # 左右通量
    # F = [Q, Q²/A + gI₁]
    # 对于矩形断面：I₁ = A*h/2 = A²/(2B)
    F_L = np.array([
        Q_L,
        Q_L**2 / A_L + 0.5 * g * A_L * h_L if A_L > 1e-10 else 0.0
    ])

    F_R = np.array([
        Q_R,
        Q_R**2 / A_R + 0.5 * g * A_R * h_R if A_R > 1e-10 else 0.0
    ])

    # HLL通量
    if s_L >= 0:
        # 超音速向右
        return F_L
    elif s_R <= 0:
        # 超音速向左
        return F_R
    else:
        # 亚音速，使用HLL公式
        F_hll = (s_R * F_L - s_L * F_R + s_L * s_R * (U_R - U_L)) / (s_R - s_L)
        return F_hll


def hllc_flux_shallow_water(U_L, U_R, B, g=9.81):
    """
    HLLC Riemann求解器（带接触间断）

    更精确但计算量稍大

    Args:
        U_L, U_R: 左右状态
        B: 渠道宽度
        g: 重力加速度

    Returns:
        F_hllc: HLLC通量
    """
    # 提取状态
    A_L, Q_L = U_L
    A_R, Q_R = U_R

    h_L = A_L / B if A_L > 1e-10 else 1e-10
    h_R = A_R / B if A_R > 1e-10 else 1e-10

    u_L = Q_L / A_L if A_L > 1e-10 else 0.0
    u_R = Q_R / A_R if A_R > 1e-10 else 0.0

    c_L = np.sqrt(g * h_L)
    c_R = np.sqrt(g * h_R)

    # Roe平均
    sqrt_h_L = np.sqrt(h_L)
    sqrt_h_R = np.sqrt(h_R)
    h_roe = (sqrt_h_L * h_L + sqrt_h_R * h_R) / (sqrt_h_L + sqrt_h_R)
    u_roe = (sqrt_h_L * u_L + sqrt_h_R * u_R) / (sqrt_h_L + sqrt_h_R)
    c_roe = np.sqrt(g * h_roe)

    # 波速
    s_L = min(u_L - c_L, u_roe - c_roe)
    s_R = max(u_R + c_R, u_roe + c_roe)

    # 中间波速（接触间断）
    s_star = (s_L * h_R * (u_R - s_R) - s_R * h_L * (u_L - s_L)) / \
             (h_R * (u_R - s_R) - h_L * (u_L - s_L))

    # 通量
    F_L = np.array([Q_L, Q_L**2 / A_L + 0.5 * g * A_L * h_L if A_L > 1e-10 else 0.0])
    F_R = np.array([Q_R, Q_R**2 / A_R + 0.5 * g * A_R * h_R if A_R > 1e-10 else 0.0])

    if s_L >= 0:
        return F_L
    elif s_R <= 0:
        return F_R
    elif s_L < 0 < s_star:
        # 左星区
        U_star_L = np.array([
            h_L * (s_L - u_L) / (s_L - s_star),
            h_L * (s_L - u_L) / (s_L - s_star) * s_star * B
        ])
        return F_L + s_L * (U_star_L - U_L)
    else:  # s_star < 0 < s_R
        # 右星区
        U_star_R = np.array([
            h_R * (s_R - u_R) / (s_R - s_star),
            h_R * (s_R - u_R) / (s_R - s_star) * s_star * B
        ])
        return F_R + s_R * (U_star_R - U_R)


def rusanov_flux(U_L, U_R, B, g=9.81):
    """
    Rusanov (Local Lax-Friedrichs) 通量

    最简单但耗散较大的求解器

    Args:
        U_L, U_R: 左右状态
        B: 渠道宽度
        g: 重力加速度

    Returns:
        F_rusanov: Rusanov通量
    """
    A_L, Q_L = U_L
    A_R, Q_R = U_R

    h_L = A_L / B if A_L > 1e-10 else 1e-10
    h_R = A_R / B if A_R > 1e-10 else 1e-10

    u_L = Q_L / A_L if A_L > 1e-10 else 0.0
    u_R = Q_R / A_R if A_R > 1e-10 else 0.0

    c_L = np.sqrt(g * h_L)
    c_R = np.sqrt(g * h_R)

    # 最大波速
    s_max = max(abs(u_L) + c_L, abs(u_R) + c_R)

    # 通量
    F_L = np.array([Q_L, Q_L**2 / A_L + 0.5 * g * A_L * h_L if A_L > 1e-10 else 0.0])
    F_R = np.array([Q_R, Q_R**2 / A_R + 0.5 * g * A_R * h_R if A_R > 1e-10 else 0.0])

    return 0.5 * (F_L + F_R) - 0.5 * s_max * (U_R - U_L)


# 测试函数
if __name__ == "__main__":
    print("=" * 60)
    print("Riemann求解器单元测试")
    print("=" * 60)
    print()

    # 测试1: Dam break问题
    print("测试1: Dam break (溃坝)")
    B = 10.0
    g = 9.81

    # 左状态：高水位
    h_L = 2.0
    u_L = 0.0
    A_L = B * h_L
    Q_L = A_L * u_L

    # 右状态：低水位
    h_R = 1.0
    u_R = 0.0
    A_R = B * h_R
    Q_R = A_R * u_R

    U_L = np.array([A_L, Q_L])
    U_R = np.array([A_R, Q_R])

    F_hll = hll_flux_shallow_water(U_L, U_R, B, g)
    F_hllc = hllc_flux_shallow_water(U_L, U_R, B, g)
    F_rusanov = rusanov_flux(U_L, U_R, B, g)

    print(f"  左状态: h={h_L}m, u={u_L}m/s")
    print(f"  右状态: h={h_R}m, u={u_R}m/s")
    print(f"  HLL通量:     {F_hll}")
    print(f"  HLLC通量:    {F_hllc}")
    print(f"  Rusanov通量: {F_rusanov}")
    print()

    # 测试2: 超音速流动
    print("测试2: 超音速流动")
    h_L = 1.5
    u_L = 5.0  # 超音速（Fr > 1）
    A_L = B * h_L
    Q_L = A_L * u_L

    h_R = 1.0
    u_R = 1.0
    A_R = B * h_R
    Q_R = A_R * u_R

    U_L = np.array([A_L, Q_L])
    U_R = np.array([A_R, Q_R])

    F_hll = hll_flux_shallow_water(U_L, U_R, B, g)

    Fr_L = u_L / np.sqrt(g * h_L)
    print(f"  左Froude数: {Fr_L:.2f}")
    print(f"  HLL通量: {F_hll}")
    print()

    print("✓ 单元测试完成")
