#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Slope限制器集合

实现多种TVD (Total Variation Diminishing) slope限制器：
- Minmod
- Van Leer
- Superbee
- MC (Monotonized Central)

用于MUSCL重构保证单调性

作者: Claude
日期: 2025-10-23
"""

import numpy as np


def minmod(a, b, c=None):
    """
    Minmod限制器

    三参数版本:
      minmod(a,b,c) = { min(a,b,c)  if a,b,c > 0
                      { max(a,b,c)  if a,b,c < 0
                      { 0           otherwise

    二参数版本:
      minmod(a,b) = { min(a,b)  if a,b > 0
                    { max(a,b)  if a,b < 0
                    { 0         otherwise

    Args:
        a, b, c: 标量或数组

    Returns:
        限制后的值
    """
    if c is None:
        # 二参数版本
        return np.where(
            a * b > 0,
            np.where(np.abs(a) < np.abs(b), a, b),
            0.0
        )
    else:
        # 三参数版本
        return np.where(
            (a > 0) & (b > 0) & (c > 0),
            np.minimum(np.minimum(a, b), c),
            np.where(
                (a < 0) & (b < 0) & (c < 0),
                np.maximum(np.maximum(a, b), c),
                0.0
            )
        )


def vanleer(a, b):
    """
    Van Leer限制器

    φ(r) = (r + |r|) / (1 + |r|)
    其中 r = a/b

    更平滑但可能稍耗散

    Args:
        a, b: 标量或数组

    Returns:
        限制后的值
    """
    # 避免除零
    eps = 1e-12

    # 计算比值 r
    r = np.where(np.abs(b) > eps, a / b, 0.0)

    # Van Leer限制函数
    phi = (r + np.abs(r)) / (1 + np.abs(r))

    return phi * b


def superbee(a, b):
    """
    Superbee限制器

    φ(r) = max(0, min(2r, 1), min(r, 2))
    其中 r = a/b

    最不耗散但可能产生轻微振荡

    Args:
        a, b: 标量或数组

    Returns:
        限制后的值
    """
    eps = 1e-12

    # 计算比值 r
    r = np.where(np.abs(b) > eps, a / b, 0.0)

    # Superbee限制函数
    phi = np.maximum(
        0,
        np.maximum(
            np.minimum(2 * r, 1),
            np.minimum(r, 2)
        )
    )

    return phi * b


def mc_limiter(a, b):
    """
    MC (Monotonized Central) 限制器

    φ(r) = max(0, min((1+r)/2, 2, 2r))
    其中 r = a/b

    介于Minmod和Superbee之间的平衡

    Args:
        a, b: 标量或数组

    Returns:
        限制后的值
    """
    eps = 1e-12

    # 计算比值 r
    r = np.where(np.abs(b) > eps, a / b, 0.0)

    # MC限制函数
    phi = np.maximum(
        0,
        np.minimum(
            np.minimum((1 + r) / 2, 2),
            2 * r
        )
    )

    return phi * b


def compute_limited_slope(U_minus, U_center, U_plus, dx_minus, dx_center, dx_plus,
                          limiter='minmod', theta=1.5):
    """
    计算TVD限制后的斜率

    用于MUSCL重构的斜率计算

    Args:
        U_minus: i-1单元的值
        U_center: i单元的值
        U_plus: i+1单元的值
        dx_minus: i-1单元的尺寸
        dx_center: i单元的尺寸
        dx_plus: i+1单元的尺寸
        limiter: 限制器类型 ('minmod', 'vanleer', 'superbee', 'mc')
        theta: Minmod的theta参数 (1.0-2.0, 通常1.5)

    Returns:
        sigma: 限制后的斜率
    """
    # 计算三个斜率估计
    grad_backward = (U_center - U_minus) / dx_center
    grad_forward = (U_plus - U_center) / dx_plus
    grad_central = (U_plus - U_minus) / (dx_center + dx_plus)

    if limiter == 'minmod':
        # Minmod三参数版本
        sigma = minmod(theta * grad_backward, grad_central, theta * grad_forward)

    elif limiter == 'vanleer':
        # Van Leer使用backward和forward
        sigma = vanleer(grad_backward, grad_forward)

    elif limiter == 'superbee':
        # Superbee使用backward和forward
        sigma = superbee(grad_backward, grad_forward)

    elif limiter == 'mc':
        # MC限制器
        sigma = mc_limiter(grad_backward, grad_forward)

    else:
        raise ValueError(f"Unknown limiter: {limiter}")

    return sigma


# 测试和可视化
if __name__ == "__main__":
    import matplotlib.pyplot as plt

    print("=" * 70)
    print("Slope限制器测试")
    print("=" * 70)
    print()

    # 测试1: 标量测试
    print("测试1: 标量值")
    a_vals = [1.0, -1.0, 1.0, 0.5]
    b_vals = [2.0, -0.5, -1.0, 1.0]

    print(f"{'a':>6} | {'b':>6} | {'minmod':>8} | {'vanleer':>8} | {'superbee':>8} | {'mc':>8}")
    print("-" * 70)

    for a, b in zip(a_vals, b_vals):
        mm = minmod(a, b)
        vl = vanleer(a, b)
        sb = superbee(a, b)
        mc = mc_limiter(a, b)
        print(f"{a:>6.2f} | {b:>6.2f} | {mm:>8.4f} | {vl:>8.4f} | {sb:>8.4f} | {mc:>8.4f}")

    print()

    # 测试2: 可视化限制器函数
    print("测试2: 生成限制器函数可视化")

    r = np.linspace(-2, 4, 200)

    # 计算各种限制器的phi(r)
    phi_minmod = np.maximum(0, np.minimum(1, r))
    phi_vanleer = (r + np.abs(r)) / (1 + np.abs(r))
    phi_superbee = np.maximum(0, np.maximum(np.minimum(2*r, 1), np.minimum(r, 2)))
    phi_mc = np.maximum(0, np.minimum(np.minimum((1+r)/2, 2), 2*r))

    # TVD区域边界
    r_plot = np.linspace(0, 4, 100)
    tvd_lower = np.maximum(0, r_plot)
    tvd_upper = np.minimum(2, 2*r_plot)

    plt.figure(figsize=(10, 6))

    # 绘制TVD区域
    plt.fill_between(r_plot, tvd_lower, tvd_upper, alpha=0.2, color='gray', label='TVD区域')

    # 绘制限制器
    plt.plot(r, phi_minmod, 'b-', linewidth=2, label='Minmod')
    plt.plot(r, phi_vanleer, 'g-', linewidth=2, label='Van Leer')
    plt.plot(r, phi_superbee, 'r-', linewidth=2, label='Superbee')
    plt.plot(r, phi_mc, 'm-', linewidth=2, label='MC')

    plt.xlabel('r = (U_i - U_{i-1}) / (U_{i+1} - U_i)')
    plt.ylabel('φ(r)')
    plt.title('TVD Slope限制器')
    plt.legend()
    plt.grid(True, alpha=0.3)
    plt.xlim(-0.5, 4)
    plt.ylim(-0.5, 2.5)

    plt.savefig('slope_limiters_comparison.png', dpi=150, bbox_inches='tight')
    print("  ✓ 保存图像: slope_limiters_comparison.png")

    print()

    # 测试3: 数组测试
    print("测试3: 数组操作")
    U = np.array([1.0, 1.5, 1.8, 1.7, 1.9, 2.0])
    dx = np.ones(len(U)) * 0.5

    print(f"  输入数组 U: {U}")
    print(f"  网格间距 dx: {dx}")
    print()

    # 对内部点计算限制后的斜率
    for i in range(1, len(U) - 1):
        sigma_mm = compute_limited_slope(
            U[i-1], U[i], U[i+1],
            dx[i-1], dx[i], dx[i+1],
            limiter='minmod'
        )
        sigma_vl = compute_limited_slope(
            U[i-1], U[i], U[i+1],
            dx[i-1], dx[i], dx[i+1],
            limiter='vanleer'
        )

        print(f"  i={i}: minmod斜率={sigma_mm:.4f}, vanleer斜率={sigma_vl:.4f}")

    print()
    print("✓ 所有测试完成")
