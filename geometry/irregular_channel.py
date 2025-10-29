#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
天然不规则断面渠道模块

实现任意形状断面的水力几何计算。

断面定义方式：
    通过一系列横断面点（桩号, 高程）定义
    例如：
    stations:   [0,   5,  10, 15, 20]  (m)
    elevations: [5,   2,   0,  2,  5]  (m)

    形状示意：
        |\      /|
        | \    / |
        |  \__/  |

应用场景：
- 天然河道
- 实测断面
- 不规则渠道
- 复杂断面形状

作者: HydroClaude Team
日期: 2025-10-29
"""

import numpy as np
from typing import Dict, List, Tuple, Optional


class IrregularChannel:
    """
    天然不规则断面渠道

    通过一系列横断面点（桩号, 高程）定义任意形状的断面。
    使用数值积分方法计算水力几何参数。

    断面定义：
    - stations: 横断面桩号数组 [x1, x2, ..., xn] (m)，必须单调递增
    - elevations: 对应高程数组 [z1, z2, ..., zn] (m)
    - 至少需要3个点定义一个断面

    水力计算方法：
    - 面积：梯形法则数值积分
    - 水面宽度：查找水线交点
    - 湿周：累加水下线段长度
    - 水力半径：R = A / P
    - 水力深度：D = A / B

    优势：
    - 支持任意复杂形状
    - 可直接使用实测数据
    - 精确处理不对称断面
    - 适用于天然河道
    """

    def __init__(self,
                 stations: np.ndarray,
                 elevations: np.ndarray,
                 length: float,
                 bottom_slope: float,
                 manning_n: float,
                 channel_id: str = "irregular_channel"):
        """
        初始化天然不规则断面渠道

        Args:
            stations: 横断面桩号 [x1, x2, ..., xn] (m)，必须单调递增
            elevations: 对应高程 [z1, z2, ..., zn] (m)
            length: 河段长度 (m)，必须 > 0
            bottom_slope: 底坡 S0 (无量纲)，必须 >= 0
            manning_n: Manning粗糙系数，典型值 0.01-0.05
            channel_id: 渠道标识符

        Raises:
            ValueError: 如果参数不满足约束
        """
        # 转换为numpy数组
        self.x = np.array(stations, dtype=float)
        self.z = np.array(elevations, dtype=float)

        # 参数验证
        if len(self.x) != len(self.z):
            raise ValueError(f"桩号和高程数量必须一致，当前: {len(self.x)} vs {len(self.z)}")

        if len(self.x) < 3:
            raise ValueError(f"至少需要3个点定义断面，当前只有: {len(self.x)}")

        if not np.all(np.diff(self.x) > 0):
            raise ValueError("桩号必须严格单调递增")

        if length <= 0:
            raise ValueError(f"河段长度必须 > 0，当前值: {length}")

        if bottom_slope < 0:
            raise ValueError(f"底坡必须 >= 0，当前值: {bottom_slope}")

        if manning_n <= 0:
            raise ValueError(f"Manning系数必须 > 0，当前值: {manning_n}")

        self.channel_id = channel_id
        self.L = float(length)
        self.S0 = float(bottom_slope)
        self.n = float(manning_n)

        # 计算断面特征
        self.n_points = len(self.x)
        self.z_min = np.min(self.z)  # 最低点高程
        self.z_max = np.max(self.z)  # 最高点高程
        self.width_total = self.x[-1] - self.x[0]  # 总宽度

    def area(self, h: float) -> float:
        """
        计算过水断面积（数值积分）

        使用梯形法则对水下部分进行积分：
        - 水面高程 = z_min + h
        - 对每个线段，计算水下部分的梯形面积
        - 累加所有梯形面积

        Args:
            h: 水深 (m)，相对于最低点

        Returns:
            过水断面积 (m²)
        """
        if h <= 0:
            return 0.0

        water_surface = self.z_min + h

        # 计算每段的水下面积
        A_total = 0.0
        for i in range(self.n_points - 1):
            x1, z1 = self.x[i], self.z[i]
            x2, z2 = self.x[i + 1], self.z[i + 1]

            # 计算水下深度
            d1 = max(0.0, water_surface - z1)
            d2 = max(0.0, water_surface - z2)

            # 如果两点都不在水下，跳过
            if d1 == 0 and d2 == 0:
                continue

            # 梯形面积：0.5 * (d1 + d2) * dx
            dx = x2 - x1
            A_segment = 0.5 * (d1 + d2) * dx
            A_total += A_segment

        return A_total

    def top_width(self, h: float) -> float:
        """
        计算水面宽度

        方法：
        1. 确定水面高程
        2. 找到最左侧和最右侧与水面相交的点
        3. 水面宽度 = x_right - x_left

        处理情况：
        - 线段完全在水下：记录端点
        - 线段与水面相交：线性插值找交点
        - 线段完全在水上：跳过

        Args:
            h: 水深 (m)

        Returns:
            水面宽度 (m)
        """
        if h <= 0:
            return 0.0

        water_surface = self.z_min + h

        x_left = None
        x_right = None

        for i in range(self.n_points - 1):
            x1, z1 = self.x[i], self.z[i]
            x2, z2 = self.x[i + 1], self.z[i + 1]

            # 判断线段与水面的关系
            d1 = water_surface - z1
            d2 = water_surface - z2

            if d1 >= 0 and d2 >= 0:
                # 线段完全在水下
                if x_left is None:
                    x_left = x1
                x_right = x2

            elif d1 < 0 and d2 < 0:
                # 线段完全在水上，跳过
                continue

            else:
                # 线段与水面相交，线性插值找交点
                if d1 * d2 < 0:  # 一个在水上，一个在水下
                    t = d1 / (d1 - d2)
                    x_intersect = x1 + t * (x2 - x1)

                    if x_left is None:
                        x_left = x_intersect
                    x_right = x_intersect

        if x_left is not None and x_right is not None:
            return x_right - x_left
        else:
            return 0.0

    def wetted_perimeter(self, h: float) -> float:
        """
        计算湿周（水下周长）

        方法：
        1. 遍历所有线段
        2. 判断线段是否在水下
        3. 累加水下部分的长度

        处理情况：
        - 线段完全在水下：累加整个线段长度
        - 线段部分在水下：计算水下部分长度
        - 线段完全在水上：不计入

        Args:
            h: 水深 (m)

        Returns:
            湿周 (m)
        """
        if h <= 0:
            return 0.0

        water_surface = self.z_min + h

        P_total = 0.0
        for i in range(self.n_points - 1):
            x1, z1 = self.x[i], self.z[i]
            x2, z2 = self.x[i + 1], self.z[i + 1]

            d1 = water_surface - z1
            d2 = water_surface - z2

            if d1 >= 0 and d2 >= 0:
                # 线段完全在水下
                ds = np.sqrt((x2 - x1)**2 + (z2 - z1)**2)
                P_total += ds

            elif d1 < 0 and d2 < 0:
                # 线段完全在水上
                continue

            else:
                # 线段部分在水下
                # 找到水面交点
                t = d1 / (d1 - d2)
                x_int = x1 + t * (x2 - x1)
                z_int = water_surface

                if d1 >= 0:
                    # z1在水下，z2在水上
                    ds = np.sqrt((x_int - x1)**2 + (z_int - z1)**2)
                else:
                    # z1在水上，z2在水下
                    ds = np.sqrt((x2 - x_int)**2 + (z2 - z_int)**2)

                P_total += ds

        return P_total

    def hydraulic_radius(self, h: float) -> float:
        """
        计算水力半径

        公式：R = A / P

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
                'B': 0.0,
                'P': 0.0,
                'R': 0.0,
                'D': 0.0,
                'h': 0.0
            }

        # 计算基本几何要素
        A = self.area(h)
        B = self.top_width(h)
        P = self.wetted_perimeter(h)

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

        采用牛顿法迭代。

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

        # 初值估计：假设h约为河道深度的一半
        h_max = self.z_max - self.z_min
        h = h_max * 0.5

        for i in range(max_iter):
            # 计算水力要素
            props = self.properties(h)
            A = props['A']
            R = props['R']

            if A <= 0 or R <= 0:
                h *= 1.5
                continue

            # Manning公式
            Q_calc = (1.0 / self.n) * A * R**(2.0/3.0) * np.sqrt(self.S0)

            # 残差
            residual = Q_calc - Q

            if abs(residual) < tol:
                return h

            # 数值微分计算导数
            dh = h * 1e-6
            h_plus = h + dh
            props_plus = self.properties(h_plus)
            A_plus = props_plus['A']
            R_plus = props_plus['R']
            Q_plus = (1.0 / self.n) * A_plus * R_plus**(2.0/3.0) * np.sqrt(self.S0)

            dQ_dh = (Q_plus - Q_calc) / dh

            if abs(dQ_dh) < 1e-12:
                # 导数太小
                h *= 0.9 if residual > 0 else 1.1
            else:
                # 牛顿法更新
                h_new = h - residual / dQ_dh

                # 限制步长
                if h_new <= 0:
                    h_new = h * 0.5
                elif h_new > h_max:
                    h_new = h_max
                elif h_new > 2 * h:
                    h_new = 2 * h

                h = h_new

        raise RuntimeError(f"正常水深计算未收敛，Q={Q:.3f} m³/s，最后h={h:.3f} m")

    def critical_depth(self, Q: float, tol: float = 1e-6, max_iter: int = 100) -> float:
        """
        计算临界水深

        临界流条件：Q² = g * A³ / B

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

        # 初值估计
        h_max = self.z_max - self.z_min
        h = h_max * 0.3

        for i in range(max_iter):
            props = self.properties(h)
            A = props['A']
            B = props['B']

            if A <= 0 or B <= 0:
                h *= 1.5
                continue

            # 临界流条件
            f = Q**2 - g * A**3 / B

            if abs(f) < tol:
                return h

            # 数值微分
            dh = h * 1e-6
            h_plus = h + dh
            props_plus = self.properties(h_plus)
            A_plus = props_plus['A']
            B_plus = props_plus['B']
            f_plus = Q**2 - g * A_plus**3 / B_plus

            df_dh = (f_plus - f) / dh

            if abs(df_dh) < 1e-12:
                h *= 0.9 if f > 0 else 1.1
            else:
                # 牛顿法更新
                h_new = h - f / df_dh

                # 限制步长
                if h_new <= 0:
                    h_new = h * 0.5
                elif h_new > h_max:
                    h_new = h_max
                elif h_new > 2 * h:
                    h_new = 2 * h

                h = h_new

        raise RuntimeError(f"临界水深计算未收敛，Q={Q:.3f} m³/s，最后h={h:.3f} m")

    def froude_number(self, Q: float, h: float) -> float:
        """
        计算Froude数

        公式：Fr = u / √(g*D) = Q / (A * √(g*D))

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

    def get_cross_section_coordinates(self) -> Tuple[np.ndarray, np.ndarray]:
        """
        获取断面坐标（用于绘图）

        Returns:
            (x, z): 桩号和高程数组
        """
        return self.x.copy(), self.z.copy()

    def plot_cross_section(self, h: Optional[float] = None, ax=None):
        """
        绘制断面形状

        Args:
            h: 可选，如果提供则绘制水线
            ax: matplotlib axes对象，如果为None则创建新图
        """
        import matplotlib.pyplot as plt

        if ax is None:
            fig, ax = plt.subplots(figsize=(10, 6))

        # 绘制断面
        ax.plot(self.x, self.z, 'k-', linewidth=2, label='河床')
        ax.fill_between(self.x, self.z, self.z_min - 1, alpha=0.3, color='brown')

        # 绘制水线
        if h is not None and h > 0:
            water_surface = self.z_min + h
            ax.axhline(y=water_surface, color='b', linestyle='--', linewidth=1.5, label=f'水面 (h={h:.2f}m)')

            # 填充水体
            z_water = np.maximum(self.z, water_surface)
            ax.fill_between(self.x, self.z, z_water, where=(self.z < water_surface),
                           alpha=0.5, color='cyan', label='水体')

        ax.set_xlabel('桩号 (m)', fontsize=12)
        ax.set_ylabel('高程 (m)', fontsize=12)
        ax.set_title(f'断面形状 - {self.channel_id}', fontsize=14)
        ax.grid(True, alpha=0.3)
        ax.legend()
        ax.set_aspect('equal')

        return ax

    def __repr__(self) -> str:
        """字符串表示"""
        return (f"IrregularChannel(id='{self.channel_id}', "
                f"n_points={self.n_points}, width={self.width_total:.2f}m, "
                f"L={self.L:.0f}m, S0={self.S0:.5f}, n={self.n:.4f})")


def create_irregular_channel(stations: List[float],
                             elevations: List[float],
                             length: float,
                             bottom_slope: float,
                             manning_n: float,
                             channel_id: str = "irr_channel") -> IrregularChannel:
    """
    便捷函数：创建天然不规则断面渠道

    Args:
        stations: 桩号列表 (m)
        elevations: 高程列表 (m)
        length: 长度 (m)
        bottom_slope: 底坡 S0
        manning_n: Manning系数
        channel_id: 渠道ID

    Returns:
        IrregularChannel实例
    """
    return IrregularChannel(
        stations=np.array(stations),
        elevations=np.array(elevations),
        length=length,
        bottom_slope=bottom_slope,
        manning_n=manning_n,
        channel_id=channel_id
    )


# 常用天然河道断面预设
COMMON_IRREGULAR_SECTIONS = {
    'v_shaped_valley': {
        'description': 'V型河谷',
        'stations': [0, 25, 50, 75, 100],
        'elevations': [10, 5, 0, 5, 10],
        'manning_n': 0.035
    },
    'u_shaped_valley': {
        'description': 'U型河谷',
        'stations': [0, 10, 20, 40, 60, 70, 80],
        'elevations': [8, 4, 2, 0, 2, 4, 8],
        'manning_n': 0.030
    },
    'compound_channel': {
        'description': '复式断面（主槽+滩地）',
        'stations': [0, 20, 30, 40, 50, 70, 80],
        'elevations': [5, 3, 0.5, 0, 0.5, 3, 5],
        'manning_n': 0.025
    },
    'asymmetric_channel': {
        'description': '不对称河道',
        'stations': [0, 15, 30, 50, 60],
        'elevations': [8, 3, 0, 2, 6],
        'manning_n': 0.032
    }
}
