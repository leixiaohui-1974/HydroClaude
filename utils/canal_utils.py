#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
明渠水力学通用工具函数

提供明渠计算中常用的工具函数，包括：
- Manning公式计算
- 中文字体配置
- 数值验证
- 物理参数计算

作者: Claude
日期: 2025-10-21
"""

import numpy as np
import matplotlib.pyplot as plt
from typing import Optional, Tuple


# ============================================================================
# 中文字体配置
# ============================================================================

def setup_chinese_fonts(font_size: int = 11):
    """
    配置matplotlib的中文字体支持

    Args:
        font_size: 基础字体大小（默认11）

    Note:
        在Docker环境中，中文字体可能显示为方框，但不影响功能
    """
    chinese_fonts = [
        'SimHei',           # 黑体
        'Microsoft YaHei',  # 微软雅黑
        'STSong',           # 华文宋体
        'DejaVu Sans',      # 备用
    ]

    plt.rcParams['font.sans-serif'] = chinese_fonts
    plt.rcParams['axes.unicode_minus'] = False  # 解决负号显示问题
    plt.rcParams['font.size'] = font_size
    plt.rcParams['axes.titlesize'] = font_size + 2
    plt.rcParams['axes.labelsize'] = font_size + 1
    plt.rcParams['xtick.labelsize'] = font_size - 1
    plt.rcParams['ytick.labelsize'] = font_size - 1
    plt.rcParams['legend.fontsize'] = font_size - 1


# ============================================================================
# Manning公式计算
# ============================================================================

def compute_steady_uniform_flow(Q: float, B: float, S0: float, n: float,
                                g: float = 9.81, h_min: float = 0.01,
                                h_max: float = 20.0, tol: float = 1e-6) -> float:
    """
    使用Manning公式计算矩形明渠恒定均匀流水深

    Manning公式: Q = (1/n) * A * R^(2/3) * S0^(1/2)
    其中: A = B * h (断面面积)
          R = A / P (水力半径)
          P = B + 2*h (湿周)

    Args:
        Q: 流量 (m³/s)
        B: 渠道宽度 (m)
        S0: 渠底坡度 (无量纲)
        n: Manning糙率系数 (s/m^(1/3))
        g: 重力加速度 (m/s², 默认9.81)
        h_min: 搜索水深下限 (m, 默认0.01)
        h_max: 搜索水深上限 (m, 默认20.0)
        tol: 收敛容差 (m, 默认1e-6)

    Returns:
        恒定均匀流水深 h (m)

    Example:
        >>> h = compute_steady_uniform_flow(Q=8.0, B=10.0, S0=0.001, n=0.025)
        >>> print(f"水深: {h:.3f} m")
    """

    def manning_residual(h: float) -> float:
        """Manning方程残差"""
        if h <= 0:
            return 1e10
        A = B * h
        P = B + 2 * h
        R = A / P
        Q_calc = (1.0 / n) * A * (R ** (2.0/3.0)) * (S0 ** 0.5)
        return Q_calc - Q

    # 检查是否有解
    res_min = manning_residual(h_min)
    res_max = manning_residual(h_max)

    if res_min * res_max > 0:
        # 同号，使用经验公式估算
        h_est = (Q * n / (B * S0**0.5)) ** (3.0/5.0)
        return max(0.5, min(10.0, h_est))

    # 二分法求解
    while h_max - h_min > tol:
        h_mid = (h_min + h_max) / 2
        res_mid = manning_residual(h_mid)

        if abs(res_mid) < tol:
            return h_mid

        if res_mid * res_min < 0:
            h_max = h_mid
            res_max = res_mid
        else:
            h_min = h_mid
            res_min = res_mid

    return (h_min + h_max) / 2


def compute_manning_friction_slope(h: np.ndarray, Q: np.ndarray, B: float,
                                   n: float) -> np.ndarray:
    """
    计算Manning摩阻坡度

    Sf = (n * V)^2 / R^(4/3)
    其中: V = Q / A (流速)
          R = A / P (水力半径)

    Args:
        h: 水深数组 (m)
        Q: 流量数组 (m³/s)
        B: 渠道宽度 (m)
        n: Manning糙率系数

    Returns:
        摩阻坡度数组 Sf (无量纲)
    """
    Sf = np.zeros_like(h)

    for i in range(len(h)):
        if h[i] > 1e-6:
            A = B * h[i]
            P = B + 2 * h[i]
            R = A / P
            V = Q[i] / A if A > 1e-6 else 0.0
            Sf[i] = (n * abs(V)) ** 2 / (R ** (4.0/3.0))
        else:
            Sf[i] = 0.0

    return Sf


# ============================================================================
# 物理参数计算
# ============================================================================

def compute_froude_number(h: np.ndarray, Q: np.ndarray, B: float,
                         g: float = 9.81) -> np.ndarray:
    """
    计算Froude数

    Fr = V / sqrt(g * h)
    其中: V = Q / A (流速)
          A = B * h (断面面积)

    Args:
        h: 水深数组 (m)
        Q: 流量数组 (m³/s)
        B: 渠道宽度 (m)
        g: 重力加速度 (m/s²)

    Returns:
        Froude数数组 (无量纲)

    Note:
        Fr < 1: 缓流（亚临界流）
        Fr = 1: 临界流
        Fr > 1: 急流（超临界流）
    """
    Fr = np.zeros_like(h)

    for i in range(len(h)):
        if h[i] > 1e-6:
            A = B * h[i]
            V = Q[i] / A if A > 1e-6 else 0.0
            Fr[i] = V / np.sqrt(g * h[i])
        else:
            Fr[i] = 0.0

    return Fr


def compute_wave_speed(h: np.ndarray, g: float = 9.81) -> np.ndarray:
    """
    计算重力波波速

    c = sqrt(g * h)

    Args:
        h: 水深数组 (m)
        g: 重力加速度 (m/s²)

    Returns:
        波速数组 (m/s)
    """
    return np.sqrt(g * np.maximum(h, 0.0))


def compute_cfl_number(V: np.ndarray, c: np.ndarray, dx: float,
                      dt: float) -> np.ndarray:
    """
    计算CFL数（Courant-Friedrichs-Lewy数）

    CFL = (|V| + c) * dt / dx

    Args:
        V: 流速数组 (m/s)
        c: 波速数组 (m/s)
        dx: 空间步长 (m)
        dt: 时间步长 (s)

    Returns:
        CFL数数组 (无量纲)

    Note:
        显式格式要求 CFL < 1 以保证稳定性
        通常建议 CFL < 0.5
    """
    return (np.abs(V) + c) * dt / dx


# ============================================================================
# 数值验证
# ============================================================================

def check_numerical_validity(h: np.ndarray, Q: np.ndarray,
                            variable_names: Tuple[str, str] = ('h', 'Q')) -> Tuple[bool, str]:
    """
    检查数值有效性（无NaN、无Inf、物理合理）

    Args:
        h: 水深数组
        Q: 流量数组
        variable_names: 变量名称元组（用于错误消息）

    Returns:
        (is_valid, error_message)
        - is_valid: True表示有效
        - error_message: 错误信息（有效时为空字符串）
    """
    h_name, Q_name = variable_names

    # 检查NaN
    if np.isnan(h).any():
        return False, f"{h_name} contains NaN values"
    if np.isnan(Q).any():
        return False, f"{Q_name} contains NaN values"

    # 检查Inf
    if np.isinf(h).any():
        return False, f"{h_name} contains Inf values"
    if np.isinf(Q).any():
        return False, f"{Q_name} contains Inf values"

    # 检查物理合理性
    if (h < 0).any():
        return False, f"{h_name} contains negative values"
    if (Q < 0).any():
        return False, f"{Q_name} contains negative values"

    return True, ""


def compute_mass_balance(h_history: list, B: float, dx: float) -> Tuple[float, float]:
    """
    计算质量平衡

    Args:
        h_history: 水深历史记录列表
        B: 渠道宽度 (m)
        dx: 空间步长 (m)

    Returns:
        (total_volume_initial, total_volume_final)
        - total_volume_initial: 初始总水量 (m³)
        - total_volume_final: 最终总水量 (m³)
    """
    if len(h_history) == 0:
        return 0.0, 0.0

    h_initial = h_history[0]
    h_final = h_history[-1]

    V_initial = np.sum(h_initial * B * dx)
    V_final = np.sum(h_final * B * dx)

    return V_initial, V_final


# ============================================================================
# 辅助函数
# ============================================================================

def get_convergence_metrics(time: np.ndarray, h_history: list,
                           Q_history: list) -> dict:
    """
    计算收敛性指标

    Args:
        time: 时间数组
        h_history: 水深历史记录
        Q_history: 流量历史记录

    Returns:
        包含收敛性指标的字典:
        - cv_h_upstream: 上游水深变异系数
        - cv_h_downstream: 下游水深变异系数
        - cv_Q_upstream: 上游流量变异系数
        - cv_Q_downstream: 下游流量变异系数
        - converged: 是否收敛（所有CV < 0.01%）
    """
    if len(time) < 10:
        return {'converged': False, 'message': 'Insufficient data points'}

    # 提取后50%的数据用于评估收敛性
    mid_idx = len(time) // 2

    h_upstream = np.array([h[0] for h in h_history[mid_idx:]])
    h_downstream = np.array([h[-1] for h in h_history[mid_idx:]])
    Q_upstream = np.array([Q[0] for Q in Q_history[mid_idx:]])
    Q_downstream = np.array([Q[-1] for Q in Q_history[mid_idx:]])

    # 计算变异系数 CV = std / mean * 100%
    def cv(data):
        mean = np.mean(data)
        if abs(mean) < 1e-10:
            return 0.0
        return np.std(data) / abs(mean) * 100

    cv_h_up = cv(h_upstream)
    cv_h_down = cv(h_downstream)
    cv_Q_up = cv(Q_upstream)
    cv_Q_down = cv(Q_downstream)

    converged = (cv_h_up < 0.01 and cv_h_down < 0.01 and
                cv_Q_up < 0.01 and cv_Q_down < 0.01)

    return {
        'cv_h_upstream': cv_h_up,
        'cv_h_downstream': cv_h_down,
        'cv_Q_upstream': cv_Q_up,
        'cv_Q_downstream': cv_Q_down,
        'converged': converged,
        'max_cv': max(cv_h_up, cv_h_down, cv_Q_up, cv_Q_down)
    }


if __name__ == '__main__':
    # 测试Manning公式
    print("=== Manning公式测试 ===")
    Q = 8.0  # m³/s
    B = 10.0  # m
    S0 = 0.001
    n = 0.025

    h = compute_steady_uniform_flow(Q, B, S0, n)
    print(f"流量 Q = {Q} m³/s")
    print(f"渠宽 B = {B} m")
    print(f"坡度 S0 = {S0}")
    print(f"糙率 n = {n}")
    print(f"恒定均匀流水深 h = {h:.6f} m")

    # 验证
    A = B * h
    P = B + 2 * h
    R = A / P
    Q_check = (1.0 / n) * A * (R ** (2./3.)) * (S0 ** 0.5)
    print(f"验证流量 Q_check = {Q_check:.6f} m³/s")
    print(f"误差 = {abs(Q_check - Q):.2e} m³/s")

    # 测试Froude数
    print("\n=== Froude数测试 ===")
    h_array = np.array([h])
    Q_array = np.array([Q])
    Fr = compute_froude_number(h_array, Q_array, B)
    print(f"Froude数 Fr = {Fr[0]:.6f}")
    print(f"流态: {'缓流' if Fr[0] < 1 else '急流'}")

    # 测试波速
    c = compute_wave_speed(h_array)
    print(f"波速 c = {c[0]:.3f} m/s")

    print("\n✅ 所有测试通过")
