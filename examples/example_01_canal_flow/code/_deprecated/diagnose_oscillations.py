"""
诊断空间振荡的根本原因

目标：找出导致空间振荡的具体原因并制定解决方案
"""

import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))))

import numpy as np
import matplotlib.pyplot as plt
from scipy.optimize import fsolve


def compute_steady_uniform_flow(Q, B, S0, n):
    """计算恒定均匀流水深"""
    def manning_equation(h):
        if h <= 0:
            return 1e10
        A = B * h
        P = B + 2 * h
        R = A / P
        Q_calc = (1.0 / n) * A * (R ** (2./3.)) * (S0 ** 0.5)
        return Q_calc - Q

    h_min, h_max = 0.01, 20.0
    if manning_equation(h_min) * manning_equation(h_max) > 0:
        h_est = (Q * n / (B * S0**0.5)) ** (3./5.)
        return max(0.5, min(10.0, h_est))

    while h_max - h_min > 1e-6:
        h_mid = (h_min + h_max) / 2
        if manning_equation(h_mid) * manning_equation(h_min) < 0:
            h_max = h_mid
        else:
            h_min = h_mid

    return (h_min + h_max) / 2


def diagnose_oscillations():
    """诊断振荡原因"""

    print("="*70)
    print("空间振荡诊断分析")
    print("="*70)

    # 渠道参数
    L = 1000.0
    B = 10.0
    S0 = 0.001
    n = 0.025
    g = 9.81

    Q_upstream = 8.0
    h_uniform = compute_steady_uniform_flow(Q_upstream, B, S0, n)

    print(f"\n物理参数:")
    print(f"  渠道长度 L = {L} m")
    print(f"  渠道宽度 B = {B} m")
    print(f"  底坡 S0 = {S0}")
    print(f"  Manning糙率 n = {n}")
    print(f"  上游流量 Q = {Q_upstream} m³/s")
    print(f"  恒定均匀流水深 h = {h_uniform:.4f} m")

    # 计算特征参数
    A = B * h_uniform
    V = Q_upstream / A
    c = np.sqrt(g * h_uniform)
    Fr = V / c

    print(f"\n特征参数:")
    print(f"  流速 V = {V:.4f} m/s")
    print(f"  波速 c = {c:.4f} m/s")
    print(f"  Froude数 Fr = {Fr:.4f} ({'亚临界' if Fr < 1 else '超临界'})")

    # 检查不同网格分辨率下的Courant数
    print(f"\n网格分析:")

    nx_values = [21, 51, 101, 201]
    dt = 0.5

    print(f"  时间步长 dt = {dt} s")
    print(f"\n  {'nx':<6} {'dx (m)':<10} {'CFL':<10} {'dx/h':<10} {'建议':<20}")
    print(f"  {'-'*60}")

    for nx in nx_values:
        dx = L / (nx - 1)
        CFL = (V + c) * dt / dx
        dx_over_h = dx / h_uniform

        # 判断标准
        if CFL > 1.0:
            advice = "CFL > 1, 不稳定"
        elif CFL > 0.5:
            advice = "CFL偏大, 可能振荡"
        else:
            advice = "CFL合理"

        if dx_over_h > 20:
            advice += ", dx/h太大"
        elif dx_over_h < 5:
            advice += ", 分辨率高"

        print(f"  {nx:<6} {dx:<10.2f} {CFL:<10.4f} {dx_over_h:<10.2f} {advice:<20}")

    # 分析数值频率
    print(f"\n数值频率分析:")
    print(f"  物理最高频率 f_max ≈ c/dx")

    for nx in [51, 101, 201]:
        dx = L / (nx - 1)
        f_max = c / dx  # Hz
        lambda_min = 2 * dx  # 最小可分辨波长

        print(f"  nx={nx}: dx={dx:.2f}m, f_max={f_max:.4f} Hz, λ_min={lambda_min:.2f}m")

    # 傅里叶分析提示
    print(f"\n可能的振荡原因:")
    print(f"  1. ❌ 中心差分格式无耗散 → 高频模式持续存在")
    print(f"  2. ❌ 边界条件突然施加 → 引入高频分量")
    print(f"  3. ❌ 网格分辨率不足 → 无法正确表示物理解")
    print(f"  4. ❌ 初值与离散方程不完全兼容 → 激发数值模式")

    print(f"\n推荐解决方案:")
    print(f"  1. ✅ 添加数值滤波器（低通滤波）")
    print(f"  2. ✅ 使用更多网格点（nx≥201）")
    print(f"  3. ✅ 使用迎风格式增加耗散")
    print(f"  4. ✅ 改进边界条件（特征线方法）")
    print(f"  5. ✅ 使用隐式时间积分减小CFL要求")

    print(f"\n{'='*70}\n")


if __name__ == '__main__':
    diagnose_oscillations()
