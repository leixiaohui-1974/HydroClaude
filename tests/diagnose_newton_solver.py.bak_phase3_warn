#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Newton求解器诊断
Diagnose Newton solver outputs

检查h_star和u_star是否合理
"""

import numpy as np
import sys
import os
sys.path.insert(0, os.path.abspath('.'))

try:
    from solvers.riemann_exact import exact_riemann_flux, _solve_star_region_newton
except ImportError as e:
    print(f"Import error: {e}")
    print("Make sure project root is in sys.path")
    sys.exit(1)


def test_newton_outputs():
    """测试Newton求解器的输出是否合理"""
    print("=" * 70)
    print("Newton求解器输出诊断")
    print("=" * 70)

    g = 9.81
    B = 10.0

    # 测试案例
    test_cases = [
        ("静水", 2.0, 0.0, 2.0, 0.0),
        ("小跳跃", 2.0, 0.0, 1.9, 0.0),
        ("溃坝", 2.0, 0.0, 1.0, 0.0),
        ("大跳跃", 2.0, 0.0, 0.5, 0.0),
        ("反向溃坝", 1.0, 0.0, 2.0, 0.0),
        ("有流速", 2.0, 10.0, 1.0, 5.0),
    ]

    print(f"\n{'案例':<12} {'h_L':<8} {'u_L':<8} {'h_R':<8} {'u_R':<8} {'h_star':<10} {'u_star':<10} {'F_h':<12}")
    print("-" * 90)

    for name, h_L, Q_L, h_R, Q_R in test_cases:
        u_L = Q_L / (h_L * B)
        u_R = Q_R / (h_R * B)

        # 求解星区
        h_star, u_star = _solve_star_region_newton(h_L, u_L, h_R, u_R, g, max_iter=50, tol=1e-10)

        # 计算通量
        F_h, F_Q = exact_riemann_flux(h_L, Q_L, h_R, Q_R, B, g)

        # 检查物理合理性
        c_L = np.sqrt(g * h_L)
        c_R = np.sqrt(g * h_R)

        # h_star应该在h_L和h_R之间或附近
        h_min = min(h_L, h_R)
        h_max = max(h_L, h_R)

        # u_star应该在u_L和u_R之间或附近
        u_min = min(u_L, u_R)
        u_max = max(u_L, u_R)

        # 标记异常
        flag = ""
        if h_star < 0.5 * h_min or h_star > 2.0 * h_max:
            flag += "h"
        if abs(u_star) > max(abs(u_L), abs(u_R), c_L, c_R):
            flag += "u"
        if abs(F_h) > 100:
            flag += "F"

        print(f"{name:<12} {h_L:<8.2f} {u_L:<8.2f} {h_R:<8.2f} {u_R:<8.2f} {h_star:<10.4f} {u_star:<10.4f} {F_h:<12.4f} {flag}")

def test_extreme_cases():
    """测试极端情况"""
    print("\n" + "=" * 70)
    print("极端情况测试")
    print("=" * 70)

    g = 9.81
    B = 10.0

    # 极端情况
    extreme_cases = [
        ("干床右侧", 2.0, 0.0, 0.001, 0.0),
        ("干床左侧", 0.001, 0.0, 2.0, 0.0),
        ("极大跳跃", 10.0, 0.0, 0.1, 0.0),
        ("超临界流", 1.0, 50.0, 1.0, 50.0),
    ]

    print(f"\n{'案例':<12} {'h_L':<8} {'u_L':<8} {'h_R':<8} {'u_R':<8} {'h_star':<10} {'u_star':<10} {'状态':<10}")
    print("-" * 90)

    for name, h_L, Q_L, h_R, Q_R in extreme_cases:
        u_L = Q_L / (h_L * B)
        u_R = Q_R / (h_R * B)

        try:
            h_star, u_star = _solve_star_region_newton(h_L, u_L, h_R, u_R, g, max_iter=50, tol=1e-10)

            # 检查收敛性
            if h_star > 0 and np.isfinite(h_star) and np.isfinite(u_star):
                status = ""
            else:
                status = "非物理"

            print(f"{name:<12} {h_L:<8.2f} {u_L:<8.4f} {h_R:<8.2f} {u_R:<8.4f} {h_star:<10.4f} {u_star:<10.4f} {status:<10}")
        except Exception as e:
            print(f"{name:<12} {h_L:<8.2f} {u_L:<8.4f} {h_R:<8.2f} {u_R:<8.4f} {'ERROR':<10} {'ERROR':<10} 异常")

if __name__ == "__main__":
    test_newton_outputs()
    test_extreme_cases()

    print("\n" + "=" * 70)
    print("诊断完成")
    print("=" * 70)
