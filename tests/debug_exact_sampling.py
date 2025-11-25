#!/usr/bin/env python
"""
调试精确Riemann求解器采样逻辑
"""

import numpy as np
import warnings
warnings.filterwarnings("ignore")
import sys
import os

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

try:
    from solvers.riemann_exact import _solve_star_region_newton, _sample_solution
except ImportError as e:
    print(f"Import error: {e}")
    print("Make sure project root is in sys.path")
    sys.exit(1)



def debug_exact_solver():
    """调试精确求解器的星区求解和采样"""

    print("="*70)
    print("调试精确Riemann求解器采样逻辑")
    print("="*70)
    print()

    # Dam break初始条件
    h_L = 3.0
    h_R = 1.0
    Q_L = 0.0
    Q_R = 0.0
    B = 10.0
    g = 9.81

    u_L = Q_L / (h_L * B) if h_L > 0 else 0.0
    u_R = Q_R / (h_R * B) if h_R > 0 else 0.0

    print(f"初始条件:")
    print(f"  左侧: h={h_L}m, u={u_L}m/s, Q={Q_L}m^3/s")
    print(f"  右侧: h={h_R}m, u={u_R}m/s, Q={Q_R}m^3/s")
    print()

    # 计算星区
    print("[1/2] 求解星区状态...")
    h_star, u_star = _solve_star_region_newton(
        h_L, u_L, h_R, u_R, g,
        max_iter=50, tol=1e-10
    )

    print(f"  h_star = {h_star:.6f} m")
    print(f"  u_star = {u_star:.6f} m/s")
    print()

    # 计算波速
    c_L = np.sqrt(g * h_L)
    c_R = np.sqrt(g * h_R)
    c_star = np.sqrt(g * h_star)

    print(f"波速:")
    print(f"  c_L = {c_L:.4f} m/s")
    print(f"  c_R = {c_R:.4f} m/s")
    print(f"  c_star = {c_star:.4f} m/s")
    print()

    # 判断波类型
    print(f"波结构:")
    if h_star > h_L:
        S_L = u_L - c_L * np.sqrt((h_star + h_L) / (2.0 * h_L))
        print(f"  左波: 激波 (S_L = {S_L:.4f} m/s)")
    else:
        S_head_L = u_L - c_L
        S_tail_L = u_star - c_star
        print(f"  左波: 稀疏波 (S_head = {S_head_L:.4f}, S_tail = {S_tail_L:.4f} m/s)")

    if h_star > h_R:
        S_R = u_R + c_R * np.sqrt((h_star + h_R) / (2.0 * h_R))
        print(f"  右波: 激波 (S_R = {S_R:.4f} m/s)")
    else:
        S_head_R = u_star + c_star
        S_tail_R = u_R + c_R
        print(f"  右波: 稀疏波 (S_head = {S_head_R:.4f}, S_tail = {S_tail_R:.4f} m/s)")
    print()

    # 采样在x/t=0处
    print("[2/2] 在x/t=0处采样...")
    h_sample, u_sample = _sample_solution(
        h_L, u_L, h_R, u_R, h_star, u_star, g
    )

    print(f"  h_sample = {h_sample:.6f} m")
    print(f"  u_sample = {u_sample:.6f} m/s")
    print()

    # 计算通量
    Q_sample = h_sample * u_sample * B
    F_h = Q_sample
    F_Q = Q_sample * u_sample + 0.5 * g * h_sample**2 * B

    print(f"通量:")
    print(f"  Q_sample = {Q_sample:.6f} m^3/s")
    print(f"  F_h = {F_h:.6f} m^3/s")
    print(f"  F_Q = {F_Q:.6f} m^3/s^2")
    print()

    # 对比如果使用星区状态
    Q_star = h_star * u_star * B
    F_h_star = Q_star
    F_Q_star = Q_star * u_star + 0.5 * g * h_star**2 * B

    print(f"对比如果直接使用星区状态:")
    print(f"  F_h_star = {F_h_star:.6f} m^3/s")
    print(f"  F_Q_star = {F_Q_star:.6f} m^3/s^2")
    print()

    # 分析
    if abs(F_h - F_h_star) < 1e-6:
        print(" 采样给出星区状态预期对于s=0在星区内")
    elif u_sample == u_L and h_sample == h_L:
        print("  采样给出左状态")
    elif u_sample == u_R and h_sample == h_R:
        print("  采样给出右状态")
    else:
        print("  采样给出中间状态可能在稀疏波扇区内")

    print()
    print("="*70)


if __name__ == '__main__':
    debug_exact_solver()
