#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
梯形断面渠道模块

实现梯形断面的水力几何计算。

梯形断面定义：
    底宽：B_bottom
    边坡：m:1 (水平:垂直)
    水深：h

断面形状：
    |\              /|
    | \            / |
    |  \          /  |
    |   \        /   |
    |    \______/    |
    |<-   B_bottom ->|

作者: HydroClaude Team
日期: 2025-10-29
"""

import numpy as np
from typing import Dict, Optional, Tuple


class TrapezoidalChannel:
    """
    梯形断面渠道

    断面几何：
    - 底宽：B_bottom (m)
    - 边坡系数：m:1 (H:V)，例如 m=2 表示水平方向2m，垂直方向1m
    - 渠道长度：L (m)
    - 底坡：S0 (无量纲)
    - Manning粗糙系数：n

    水力要素计算：
    - 过水断面积：A = (B + m*h) * h
    - 水面宽：B = B_bottom + 2*m*h
    - 湿周：P = B_bottom + 2*h*√(1 + m²)
    - 水力半径：R = A / P
    - 水力深度：D = A / B

    应用场景：
    - 人工渠道
    - 灌溉渠系
    - 排水沟渠
    - 梯形河道
    """

    def __init__(self,
                 bottom_width: float,
                 side_slope: float,
                 length: float,
                 bottom_slope: float,
                 manning_n: float,
                 channel_id: str = "trapezoidal_channel"):
        """
        初始化梯形断面渠道

        Args:
            bottom_width: 底宽 B_bottom (m)，必须 > 0
            side_slope: 边坡系数 m (H:V比例)，必须 >= 0
                       m=0: 矩形断面
                       m=1: 1:1边坡
                       m=1.5: 1.5:1边坡（常用）
                       m=2: 2:1边坡
            length: 渠道长度 L (m)，必须 > 0
            bottom_slope: 底坡 S0 (无量纲)，必须 >= 0
            manning_n: Manning粗糙系数，典型值 0.01-0.05
            channel_id: 渠道标识符

        Raises:
            ValueError: 如果参数不满足物理约束
        """
        # 参数验证
        if bottom_width <= 0:
            raise ValueError(f"底宽必须 > 0，当前值: {bottom_width}")
        if side_slope < 0:
            raise ValueError(f"边坡系数必须 >= 0，当前值: {side_slope}")
        if length <= 0:
            raise ValueError(f"渠道长度必须 > 0，当前值: {length}")
        if bottom_slope < 0:
            raise ValueError(f"底坡必须 >= 0，当前值: {bottom_slope}")
        if manning_n <= 0:
            raise ValueError(f"Manning系数必须 > 0，当前值: {manning_n}")

        self.channel_id = channel_id
        self.B_bottom = float(bottom_width)
        self.m = float(side_slope)
        self.L = float(length)
        self.S0 = float(bottom_slope)
        self.n = float(manning_n)

        # 计算边坡长度系数（用于湿周计算）
        self.slope_length_factor = np.sqrt(1.0 + self.m**2)

    def area(self, h: float) -> float:
        """
        计算过水断面积

        公式：A = (B_bottom + m*h) * h

        推导：
        - 矩形部分：B_bottom * h
        - 两侧三角形：2 * (0.5 * m*h * h) = m*h²
        - 总面积：B_bottom*h + m*h² = (B_bottom + m*h) * h

        Args:
            h: 水深 (m)

        Returns:
            过水断面积 (m²)
        """
        if h <= 0:
            return 0.0
        return (self.B_bottom + self.m * h) * h

    def top_width(self, h: float) -> float:
        """
        计算水面宽度

        公式：B = B_bottom + 2*m*h

        推导：
        - 底宽：B_bottom
        - 两侧增加宽度：2 * m*h
        - 总宽度：B_bottom + 2*m*h

        Args:
            h: 水深 (m)

        Returns:
            水面宽度 (m)
        """
        if h <= 0:
            return self.B_bottom
        return self.B_bottom + 2.0 * self.m * h

    def wetted_perimeter(self, h: float) -> float:
        """
        计算湿周

        公式：P = B_bottom + 2*h*√(1 + m²)

        推导：
        - 底部湿周：B_bottom
        - 两侧斜边长度：2 * √(h² + (m*h)²) = 2*h*√(1 + m²)
        - 总湿周：B_bottom + 2*h*√(1 + m²)

        Args:
            h: 水深 (m)

        Returns:
            湿周 (m)
        """
        if h <= 0:
            return self.B_bottom
        return self.B_bottom + 2.0 * h * self.slope_length_factor

    def hydraulic_radius(self, h: float) -> float:
        """
        计算水力半径

        公式：R = A / P

        水力半径是断面水力特性的重要参数，用于：
        - Manning公式计算流速
        - Chezy公式
        - 能量损失计算

        Args:
            h: 水深 (m)

        Returns:
            水力半径 (m)
        """
        if h <= 0:
            return 0.0

        A = self.area(h)
        P = self.wetted_perimeter(h)

        if P > 0:
            return A / P
        else:
            return 0.0

    def hydraulic_depth(self, h: float) -> float:
        """
        计算水力深度

        公式：D = A / B

        水力深度用于：
        - Froude数计算：Fr = u / √(g*D)
        - 临界水深判断
        - 能量方程

        Args:
            h: 水深 (m)

        Returns:
            水力深度 (m)
        """
        if h <= 0:
            return 0.0

        A = self.area(h)
        B = self.top_width(h)

        if B > 0:
            return A / B
        else:
            return 0.0

    def properties(self, h: float) -> Dict[str, float]:
        """
        计算所有水力要素

        一次性计算所有几何和水力参数，提高效率。

        Args:
            h: 水深 (m)

        Returns:
            包含所有水力要素的字典：
            - A: 过水断面积 (m²)
            - B: 水面宽度 (m)
            - P: 湿周 (m)
            - R: 水力半径 (m)
            - D: 水力深度 (m)
            - h: 水深 (m)
        """
        if h <= 0:
            return {
                'A': 0.0,
                'B': self.B_bottom,
                'P': self.B_bottom,
                'R': 0.0,
                'D': 0.0,
                'h': 0.0
            }

        # 计算基本几何要素
        A = (self.B_bottom + self.m * h) * h
        B = self.B_bottom + 2.0 * self.m * h
        P = self.B_bottom + 2.0 * h * self.slope_length_factor

        # 计算派生要素
        R = A / P if P > 0 else 0.0
        D = A / B if B > 0 else 0.0

        return {
            'A': A,
            'B': B,
            'P': P,
            'R': R,
            'D': D,
            'h': h
        }

    def normal_depth(self, Q: float, tol: float = 1e-6, max_iter: int = 100) -> float:
        """
        计算正常水深（均匀流水深）

        使用Manning公式迭代求解：
        Q = (1/n) * A * R^(2/3) * √S0

        采用牛顿法迭代：
        h_new = h_old - f(h) / f'(h)

        Args:
            Q: 流量 (m³/s)
            tol: 收敛容差 (m)
            max_iter: 最大迭代次数

        Returns:
            正常水深 h_n (m)

        Raises:
            RuntimeError: 如果迭代不收敛
        """
        if Q <= 0:
            return 0.0
        if self.S0 <= 0:
            raise ValueError("计算正常水深需要非零底坡")

        g = 9.81

        # 初值估计：假设宽浅渠道 h ≈ (Q*n / (B*√S0))^(3/5)
        h = (Q * self.n / (self.B_bottom * np.sqrt(self.S0)))**(3.0/5.0)

        for i in range(max_iter):
            # 计算水力要素
            props = self.properties(h)
            A = props['A']
            R = props['R']
            B = props['B']
            P = props['P']

            if A <= 0 or R <= 0:
                h *= 1.5
                continue

            # Manning公式：Q = (1/n) * A * R^(2/3) * √S0
            Q_calc = (1.0 / self.n) * A * R**(2.0/3.0) * np.sqrt(self.S0)

            # 残差
            residual = Q_calc - Q

            if abs(residual) < tol:
                return h

            # 计算导数 dQ/dh（数值微分）
            dh = h * 1e-6
            h_plus = h + dh
            props_plus = self.properties(h_plus)
            A_plus = props_plus['A']
            R_plus = props_plus['R']
            Q_plus = (1.0 / self.n) * A_plus * R_plus**(2.0/3.0) * np.sqrt(self.S0)

            dQ_dh = (Q_plus - Q_calc) / dh

            if abs(dQ_dh) < 1e-12:
                # 导数太小，使用二分法后退
                h *= 0.9 if residual > 0 else 1.1
            else:
                # 牛顿法更新
                h_new = h - residual / dQ_dh

                # 限制步长，保证正值
                if h_new <= 0:
                    h_new = h * 0.5
                elif h_new > 2 * h:
                    h_new = 2 * h

                h = h_new

        raise RuntimeError(f"正常水深计算未收敛，Q={Q:.3f} m³/s，最后h={h:.3f} m")

    def critical_depth(self, Q: float, tol: float = 1e-6, max_iter: int = 100) -> float:
        """
        计算临界水深

        临界流条件：Fr = 1，即 u / √(g*D) = 1
        其中 u = Q/A, D = A/B

        推导：Q² = g * A³ / B

        采用牛顿法迭代求解。

        Args:
            Q: 流量 (m³/s)
            tol: 收敛容差 (m)
            max_iter: 最大迭代次数

        Returns:
            临界水深 h_c (m)

        Raises:
            RuntimeError: 如果迭代不收敛
        """
        if Q <= 0:
            return 0.0

        g = 9.81

        # 初值估计：假设矩形 h_c ≈ (Q² / (g*B²))^(1/3)
        h = (Q**2 / (g * self.B_bottom**2))**(1.0/3.0)

        for i in range(max_iter):
            props = self.properties(h)
            A = props['A']
            B = props['B']

            if A <= 0 or B <= 0:
                h *= 1.5
                continue

            # 临界流条件：Q² = g * A³ / B
            f = Q**2 - g * A**3 / B

            if abs(f) < tol:
                return h

            # 计算导数 df/dh（数值微分）
            dh = h * 1e-6
            h_plus = h + dh
            props_plus = self.properties(h_plus)
            A_plus = props_plus['A']
            B_plus = props_plus['B']
            f_plus = Q**2 - g * A_plus**3 / B_plus

            df_dh = (f_plus - f) / dh

            if abs(df_dh) < 1e-12:
                # 导数太小
                h *= 0.9 if f > 0 else 1.1
            else:
                # 牛顿法更新
                h_new = h - f / df_dh

                # 限制步长
                if h_new <= 0:
                    h_new = h * 0.5
                elif h_new > 2 * h:
                    h_new = 2 * h

                h = h_new

        raise RuntimeError(f"临界水深计算未收敛，Q={Q:.3f} m³/s，最后h={h:.3f} m")

    def froude_number(self, Q: float, h: float) -> float:
        """
        计算Froude数

        公式：Fr = u / √(g*D) = Q / (A * √(g*D))

        Fr < 1: 亚临界流（缓流）
        Fr = 1: 临界流
        Fr > 1: 超临界流（急流）

        Args:
            Q: 流量 (m³/s)
            h: 水深 (m)

        Returns:
            Froude数 (无量纲)
        """
        if h <= 0 or Q == 0:
            return 0.0

        g = 9.81
        props = self.properties(h)
        A = props['A']
        D = props['D']

        if A <= 0 or D <= 0:
            return 0.0

        u = Q / A
        Fr = u / np.sqrt(g * D)

        return Fr

    def __repr__(self) -> str:
        """字符串表示"""
        return (f"TrapezoidalChannel(id='{self.channel_id}', "
                f"B={self.B_bottom:.2f}m, m={self.m:.2f}, "
                f"L={self.L:.0f}m, S0={self.S0:.5f}, n={self.n:.4f})")


def create_trapezoidal_channel(bottom_width: float,
                                side_slope: float,
                                length: float,
                                bottom_slope: float,
                                manning_n: float,
                                channel_id: str = "trap_channel") -> TrapezoidalChannel:
    """
    便捷函数：创建梯形断面渠道

    Args:
        bottom_width: 底宽 (m)
        side_slope: 边坡系数 m:1
        length: 长度 (m)
        bottom_slope: 底坡 S0
        manning_n: Manning系数
        channel_id: 渠道ID

    Returns:
        TrapezoidalChannel实例
    """
    return TrapezoidalChannel(
        bottom_width=bottom_width,
        side_slope=side_slope,
        length=length,
        bottom_slope=bottom_slope,
        manning_n=manning_n,
        channel_id=channel_id
    )


# 常用梯形断面预设
COMMON_TRAPEZOIDAL_SECTIONS = {
    'irrigation_main': {
        'description': '主干灌溉渠道',
        'bottom_width': 5.0,
        'side_slope': 1.5,
        'manning_n': 0.020
    },
    'irrigation_branch': {
        'description': '支渠',
        'bottom_width': 2.0,
        'side_slope': 1.5,
        'manning_n': 0.022
    },
    'drainage_channel': {
        'description': '排水渠',
        'bottom_width': 3.0,
        'side_slope': 2.0,
        'manning_n': 0.025
    },
    'highway_drainage': {
        'description': '公路边沟',
        'bottom_width': 0.5,
        'side_slope': 1.5,
        'manning_n': 0.016
    }
}
