#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Numba JIT优化核心计算内核

使用Numba JIT编译加速关键计算密集型函数

作者: HydroClaude Team
日期: 2025-10-31
Phase: 6.5 - Numba JIT性能优化
"""

import numpy as np
from numba import njit
from typing import Tuple


@njit(cache=True)
def hll_flux_kernel(
    h_L: float,
    Q_L: float,
    h_R: float,
    Q_R: float,
    B: float,
    g: float,
    eps_dry: float,
    use_entropy_fix: bool,
    use_critical_flow_treatment: bool
) -> Tuple[float, float]:
    """
    HLL Riemann求解器内核（JIT编译版本）

    Args:
        h_L: 左侧水深 (m)
        Q_L: 左侧流量 (m³/s)
        h_R: 右侧水深 (m)
        Q_R: 右侧流量 (m³/s)
        B: 渠道宽度 (m)
        g: 重力加速度 (m/s²)
        eps_dry: 干床阈值 (m)
        use_entropy_fix: 是否使用熵修正
        use_critical_flow_treatment: 是否使用临界流处理

    Returns:
        (F_h, F_Q): 界面通量
    """
    # 干床检测
    if h_L < eps_dry and h_R < eps_dry:
        return 0.0, 0.0

    # 左状态
    A_L = max(h_L * B, eps_dry * B)
    u_L = Q_L / A_L
    c_L = np.sqrt(g * max(h_L, 0.0))

    # 右状态
    A_R = max(h_R * B, eps_dry * B)
    u_R = Q_R / A_R
    c_R = np.sqrt(g * max(h_R, 0.0))

    # 波速估计（Davis估计）
    S_L = min(u_L - c_L, u_R - c_R)
    S_R = max(u_L + c_L, u_R + c_R)

    # Entropy修正（如果启用）
    if use_entropy_fix:
        # 计算delta（通常取最大波速的10%）
        delta = 0.1 * max(abs(S_L), abs(S_R), 1e-10)

        # 对两个波速都应用entropy修正
        S_L = entropy_fix_kernel(S_L, delta)
        S_R = entropy_fix_kernel(S_R, delta)

    # 通量（左右）
    F_h_L = Q_L
    F_Q_L = Q_L**2 / A_L + 0.5 * g * h_L**2 * B

    F_h_R = Q_R
    F_Q_R = Q_R**2 / A_R + 0.5 * g * h_R**2 * B

    # HLL通量
    if S_L >= 0:
        # 超音速向右
        F_h = F_h_L
        F_Q = F_Q_L
    elif S_R <= 0:
        # 超音速向左
        F_h = F_h_R
        F_Q = F_Q_R
    else:
        # 跨音速（HLL平均）
        U_h_L = h_L
        U_h_R = h_R
        U_Q_L = Q_L
        U_Q_R = Q_R

        F_h = (S_R * F_h_L - S_L * F_h_R + S_L * S_R * (U_h_R - U_h_L)) / (S_R - S_L)
        F_Q = (S_R * F_Q_L - S_L * F_Q_R + S_L * S_R * (U_Q_R - U_Q_L)) / (S_R - S_L)

    # 临界流特殊处理（如果启用）
    if use_critical_flow_treatment:
        # 计算左右Froude数
        Fr_L = abs(u_L) / c_L if c_L > 1e-10 else 0.0
        Fr_R = abs(u_R) / c_R if c_R > 1e-10 else 0.0

        # 平均Froude数
        Fr_avg = 0.5 * (Fr_L + Fr_R)

        # 如果接近临界流（0.9 < Fr < 1.1），增加数值耗散
        if 0.9 < Fr_avg < 1.1:
            # 耗散强度随着接近Fr=1而增加
            # alpha在Fr=1时最大（0.5），在Fr=0.9或1.1时为0
            alpha = 0.5 * (1.0 - abs(Fr_avg - 1.0) / 0.1)

            # Lax-Friedrichs型耗散
            max_speed = max(abs(u_L) + c_L, abs(u_R) + c_R, 1e-10)

            # 增加耗散项（类似于人工粘性）
            dissipation_h = alpha * max_speed * (h_R - h_L)
            dissipation_Q = alpha * max_speed * (Q_R - Q_L)

            F_h -= dissipation_h
            F_Q -= dissipation_Q

    return F_h, F_Q


@njit(cache=True)
def entropy_fix_kernel(lambda_val: float, delta: float) -> float:
    """
    Harten-Hyman Entropy修正内核（JIT编译版本）

    在跨音速区域平滑波速，防止数值振荡

    Args:
        lambda_val: 原始波速
        delta: 修正参数（通常为最大波速的10%）

    Returns:
        修正后的波速
    """
    if abs(lambda_val) >= delta:
        return lambda_val
    else:
        return (lambda_val**2 + delta**2) / (2.0 * delta)


@njit(cache=True)
def compute_source_term_kernel(
    h: float,
    Q: float,
    A: float,
    R: float,
    n: float,
    g: float,
    S0: float,
    well_balanced: bool
) -> float:
    """
    源项计算内核（JIT编译版本）

    Args:
        h: 水深 (m)
        Q: 流量 (m³/s)
        A: 断面面积 (m²)
        R: 水力半径 (m)
        n: Manning糙率系数
        g: 重力加速度 (m/s²)
        S0: 底坡
        well_balanced: 是否使用Well-Balanced格式

    Returns:
        源项值
    """
    # 摩阻坡度
    if R > 1e-10 and abs(Q) > 1e-6:
        Sf = n**2 * Q**2 / (A**2 * R**(4.0/3.0))
        Sf = np.sign(Q) * Sf
    else:
        Sf = 0.0

    # Well-balanced格式：底坡源项已通过hydrostatic reconstruction处理
    # 只需要添加摩阻项
    if well_balanced:
        return -g * A * Sf
    else:
        # 标准格式：包含底坡和摩阻
        return g * A * (S0 - Sf)


@njit(cache=True)
def compute_friction_slope(
    Q: float,
    A: float,
    R: float,
    n: float
) -> float:
    """
    计算摩阻坡度（JIT编译版本）

    Args:
        Q: 流量 (m³/s)
        A: 断面面积 (m²)
        R: 水力半径 (m)
        n: Manning糙率系数

    Returns:
        摩阻坡度 Sf
    """
    if R > 1e-10 and abs(Q) > 1e-6:
        Sf = n**2 * Q**2 / (A**2 * R**(4.0/3.0))
        return np.sign(Q) * Sf
    else:
        return 0.0


# 批量HLL flux计算（向量化版本 - 实验性）
@njit(cache=True, parallel=False)
def hll_flux_batch_kernel(
    h_L: np.ndarray,
    Q_L: np.ndarray,
    h_R: np.ndarray,
    Q_R: np.ndarray,
    B: float,
    g: float,
    eps_dry: float,
    use_entropy_fix: bool,
    use_critical_flow_treatment: bool
) -> Tuple[np.ndarray, np.ndarray]:
    """
    批量HLL Riemann求解器（实验性 - 用于未来优化）

    Args:
        h_L: 左侧水深数组 (m)
        Q_L: 左侧流量数组 (m³/s)
        h_R: 右侧水深数组 (m)
        Q_R: 右侧流量数组 (m³/s)
        B: 渠道宽度 (m)
        g: 重力加速度 (m/s²)
        eps_dry: 干床阈值 (m)
        use_entropy_fix: 是否使用熵修正
        use_critical_flow_treatment: 是否使用临界流处理

    Returns:
        (F_h, F_Q): 界面通量数组
    """
    n = len(h_L)
    F_h = np.zeros(n)
    F_Q = np.zeros(n)

    for i in range(n):
        F_h[i], F_Q[i] = hll_flux_kernel(
            h_L[i], Q_L[i], h_R[i], Q_R[i],
            B, g, eps_dry,
            use_entropy_fix, use_critical_flow_treatment
        )

    return F_h, F_Q
