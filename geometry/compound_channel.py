#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
复合断面渠道模块

实现复合断面（主槽+滩地）的水力计算。

复合断面特点：
- 主槽：低水位流动区域，通常Manning系数较小
- 滩地：高水位漫滩区域，通常Manning系数较大（植被）
- 分区流速法：各区域独立计算流速

典型应用：
- 平原河流（有明显主槽和滩地）
- 防洪河道
- 自然河道整治
- 漫滩模拟

作者: HydroClaude Team
日期: 2025-10-29
"""

import numpy as np
from typing import Dict, List, Tuple, Optional
from .irregular_channel import IrregularChannel


class CompoundChannel:
    """
    复合断面渠道（主槽+滩地）

    断面组成：
    - 主槽（Main Channel）：低水位流动区域
    - 左滩地（Left Floodplain）：左侧漫滩区域
    - 右滩地（Right Floodplain）：右侧漫滩区域

    分区Manning系数：
    - 主槽：n_main（通常较小，如0.025）
    - 滩地：n_floodplain（通常较大，如0.035-0.050，有植被）

    流量计算方法：
    1. 分区流速法（推荐）：
       - 各区域独立计算 Q_i = A_i * v_i
       - v_i = (1/n_i) * R_i^(2/3) * √S0
       - Q_total = Σ Q_i

    2. 等效Manning系数法：
       - n_eq = (Σ P_i * n_i^1.5)^(2/3) / P_total
       - Q_total = (1/n_eq) * A_total * R_total^(2/3) * √S0

    断面定义方式：
    - 左滩地：桩号 0 到 x_left_bank
    - 主槽：桩号 x_left_bank 到 x_right_bank
    - 右滩地：桩号 x_right_bank 到 x_end

    或者：
    - 通过bankfull_elevation（满槽水位）自动划分
    """

    def __init__(self,
                 stations: np.ndarray,
                 elevations: np.ndarray,
                 bankfull_elevation: float,
                 length: float,
                 bottom_slope: float,
                 manning_n_main: float,
                 manning_n_floodplain: float,
                 left_bank_station: Optional[float] = None,
                 right_bank_station: Optional[float] = None,
                 channel_id: str = "compound_channel"):
        """
        初始化复合断面渠道

        Args:
            stations: 横断面桩号 [x1, x2, ..., xn] (m)
            elevations: 对应高程 [z1, z2, ..., zn] (m)
            bankfull_elevation: 满槽水位/堤岸高程 (m)，用于划分主槽和滩地
            length: 河段长度 (m)
            bottom_slope: 底坡 S0
            manning_n_main: 主槽Manning系数（通常较小，如0.020-0.030）
            manning_n_floodplain: 滩地Manning系数（通常较大，如0.035-0.060）
            left_bank_station: 左岸桩号 (m)，如果为None则自动判断
            right_bank_station: 右岸桩号 (m)，如果为None则自动判断
            channel_id: 渠道标识符

        Raises:
            ValueError: 如果参数不满足约束
        """
        self.x = np.array(stations, dtype=float)
        self.z = np.array(elevations, dtype=float)
        self.z_bankfull = float(bankfull_elevation)
        self.L = float(length)
        self.S0 = float(bottom_slope)
        self.n_main = float(manning_n_main)
        self.n_flood = float(manning_n_floodplain)
        self.channel_id = channel_id

        # 参数验证
        if len(self.x) != len(self.z):
            raise ValueError(f"桩号和高程数量必须一致")

        if len(self.x) < 3:
            raise ValueError(f"至少需要3个点定义断面")

        if not np.all(np.diff(self.x) > 0):
            raise ValueError("桩号必须严格单调递增")

        if length <= 0:
            raise ValueError(f"河段长度必须 > 0")

        if bottom_slope < 0:
            raise ValueError(f"底坡必须 >= 0")

        if manning_n_main <= 0 or manning_n_floodplain <= 0:
            raise ValueError(f"Manning系数必须 > 0")

        # 确定左右岸桩号
        if left_bank_station is None or right_bank_station is None:
            # 自动判断：找到满槽水位与断面相交的点
            self._auto_determine_banks()
        else:
            self.x_left_bank = float(left_bank_station)
            self.x_right_bank = float(right_bank_station)

        # 断面特征
        self.z_min = np.min(self.z)
        self.z_max = np.max(self.z)
        self.width_total = self.x[-1] - self.x[0]

        # 创建整体断面（用于几何计算）
        self._full_section = IrregularChannel(
            self.x, self.z, self.L, self.S0, self.n_main, f"{channel_id}_full"
        )

    def _auto_determine_banks(self):
        """
        自动确定左右岸桩号

        方法：找到满槽水位与断面相交的左右两个点
        """
        intersections = []

        for i in range(len(self.x) - 1):
            z1, z2 = self.z[i], self.z[i + 1]
            x1, x2 = self.x[i], self.x[i + 1]

            # 判断线段是否与满槽水位相交
            if (z1 <= self.z_bankfull < z2) or (z2 <= self.z_bankfull < z1):
                # 线性插值找交点
                t = (self.z_bankfull - z1) / (z2 - z1)
                x_int = x1 + t * (x2 - x1)
                intersections.append(x_int)

        if len(intersections) >= 2:
            # 取最左和最右的交点
            self.x_left_bank = intersections[0]
            self.x_right_bank = intersections[-1]
        else:
            # 如果找不到交点，使用默认值（断面中间1/3区域）
            width = self.x[-1] - self.x[0]
            self.x_left_bank = self.x[0] + width / 3.0
            self.x_right_bank = self.x[-1] - width / 3.0

    def _get_subdivision_properties(self, h: float) -> Dict[str, Dict[str, float]]:
        """
        计算各子区域的水力要素

        分区方法：
        1. 左滩地：x < x_left_bank
        2. 主槽：x_left_bank <= x <= x_right_bank
        3. 右滩地：x > x_right_bank

        Args:
            h: 水深 (m)，相对于最低点

        Returns:
            各区域的水力要素字典
        """
        if h <= 0:
            return {
                'left_flood': {'A': 0, 'P': 0, 'R': 0, 'n': self.n_flood},
                'main': {'A': 0, 'P': 0, 'R': 0, 'n': self.n_main},
                'right_flood': {'A': 0, 'P': 0, 'R': 0, 'n': self.n_flood}
            }

        water_surface = self.z_min + h

        # 初始化各区域
        regions = {
            'left_flood': {'A': 0.0, 'P': 0.0, 'R': 0.0, 'n': self.n_flood},
            'main': {'A': 0.0, 'P': 0.0, 'R': 0.0, 'n': self.n_main},
            'right_flood': {'A': 0.0, 'P': 0.0, 'R': 0.0, 'n': self.n_flood}
        }

        # 计算面积和湿周
        for i in range(len(self.x) - 1):
            x1, z1 = self.x[i], self.z[i]
            x2, z2 = self.x[i + 1], self.z[i + 1]

            # 水下深度
            d1 = max(0.0, water_surface - z1)
            d2 = max(0.0, water_surface - z2)

            if d1 == 0 and d2 == 0:
                continue  # 线段不在水下

            # 确定线段属于哪个区域
            x_mid = 0.5 * (x1 + x2)

            if x_mid < self.x_left_bank:
                region = 'left_flood'
            elif x_mid <= self.x_right_bank:
                region = 'main'
            else:
                region = 'right_flood'

            # 计算面积（梯形）
            dx = x2 - x1
            A_segment = 0.5 * (d1 + d2) * dx
            regions[region]['A'] += A_segment

            # 计算湿周
            if d1 > 0 and d2 > 0:
                # 完全在水下
                ds = np.sqrt(dx**2 + (z2 - z1)**2)
                regions[region]['P'] += ds
            else:
                # 部分在水下
                if d1 > 0:
                    t = d1 / (d1 + (z2 - water_surface))
                    x_int = x1 + t * dx
                    ds = np.sqrt((x_int - x1)**2 + (water_surface - z1)**2)
                else:
                    t = (water_surface - z1) / (z2 - z1)
                    x_int = x1 + t * dx
                    ds = np.sqrt((x2 - x_int)**2 + (z2 - water_surface)**2)
                regions[region]['P'] += ds

        # 计算水力半径
        for region in regions.values():
            if region['P'] > 0:
                region['R'] = region['A'] / region['P']

        return regions

    def area(self, h: float) -> float:
        """计算总过水断面积"""
        return self._full_section.area(h)

    def top_width(self, h: float) -> float:
        """计算水面宽度"""
        return self._full_section.top_width(h)

    def wetted_perimeter(self, h: float) -> float:
        """计算总湿周"""
        return self._full_section.wetted_perimeter(h)

    def hydraulic_radius(self, h: float) -> float:
        """计算整体水力半径"""
        return self._full_section.hydraulic_radius(h)

    def hydraulic_depth(self, h: float) -> float:
        """计算整体水力深度"""
        return self._full_section.hydraulic_depth(h)

    def properties(self, h: float) -> Dict[str, float]:
        """计算整体水力要素"""
        return self._full_section.properties(h)

    def compute_discharge_divided(self, h: float) -> Tuple[float, Dict[str, float]]:
        """
        使用分区流速法计算流量

        方法：
        - 各区域独立计算流量：Q_i = A_i * v_i
        - v_i = (1/n_i) * R_i^(2/3) * √S0
        - Q_total = Q_left_flood + Q_main + Q_right_flood

        Args:
            h: 水深 (m)

        Returns:
            (Q_total, Q_dict): 总流量和各区域流量字典
        """
        if h <= 0 or self.S0 <= 0:
            return 0.0, {'left_flood': 0.0, 'main': 0.0, 'right_flood': 0.0}

        # 获取各区域水力要素
        regions = self._get_subdivision_properties(h)

        Q_dict = {}
        Q_total = 0.0

        for region_name, props in regions.items():
            A = props['A']
            R = props['R']
            n = props['n']

            if A > 0 and R > 0:
                # Manning公式
                Q_i = (1.0 / n) * A * R**(2.0/3.0) * np.sqrt(self.S0)
            else:
                Q_i = 0.0

            Q_dict[region_name] = Q_i
            Q_total += Q_i

        return Q_total, Q_dict

    def compute_discharge_equivalent(self, h: float) -> float:
        """
        使用等效Manning系数法计算流量

        方法：
        - 计算等效Manning系数：n_eq = (Σ P_i * n_i^1.5)^(2/3) / P_total
        - 使用整体断面：Q = (1/n_eq) * A * R^(2/3) * √S0

        注意：此方法精度略低于分区流速法

        Args:
            h: 水深 (m)

        Returns:
            流量 (m³/s)
        """
        if h <= 0 or self.S0 <= 0:
            return 0.0

        # 获取各区域水力要素
        regions = self._get_subdivision_properties(h)

        # 计算等效Manning系数
        numerator = 0.0
        P_total = 0.0

        for props in regions.values():
            P_i = props['P']
            n_i = props['n']
            if P_i > 0:
                numerator += P_i * n_i**1.5
                P_total += P_i

        if P_total > 0:
            n_eq = (numerator / P_total)**(2.0/3.0)
        else:
            n_eq = self.n_main

        # 使用整体断面计算流量
        props_full = self.properties(h)
        A = props_full['A']
        R = props_full['R']

        Q = (1.0 / n_eq) * A * R**(2.0/3.0) * np.sqrt(self.S0)

        return Q

    def normal_depth(self, Q: float, method: str = 'divided',
                     tol: float = 1e-6, max_iter: int = 100) -> float:
        """
        计算正常水深

        Args:
            Q: 流量 (m³/s)
            method: 计算方法，'divided'（分区法，推荐）或'equivalent'（等效法）
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

        # 初值估计
        h_max = self.z_max - self.z_min
        h = h_max * 0.5

        for i in range(max_iter):
            # 计算当前水深对应的流量
            if method == 'divided':
                Q_calc, _ = self.compute_discharge_divided(h)
            else:
                Q_calc = self.compute_discharge_equivalent(h)

            # 残差
            residual = Q_calc - Q

            if abs(residual) < tol:
                return h

            # 数值微分
            dh = h * 1e-6
            h_plus = h + dh

            if method == 'divided':
                Q_plus, _ = self.compute_discharge_divided(h_plus)
            else:
                Q_plus = self.compute_discharge_equivalent(h_plus)

            dQ_dh = (Q_plus - Q_calc) / dh

            if abs(dQ_dh) < 1e-12:
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

        Args:
            Q: 流量 (m³/s)
            tol: 收敛容差 (m)
            max_iter: 最大迭代次数

        Returns:
            临界水深 h_c (m)
        """
        return self._full_section.critical_depth(Q, tol, max_iter)

    def froude_number(self, Q: float, h: float) -> float:
        """
        计算Froude数

        Args:
            Q: 流量 (m³/s)
            h: 水深 (m)

        Returns:
            Froude数
        """
        return self._full_section.froude_number(Q, h)

    def is_overbank(self, h: float) -> bool:
        """
        判断是否漫滩

        Args:
            h: 水深 (m)

        Returns:
            True如果水位超过满槽水位
        """
        water_surface = self.z_min + h
        return water_surface > self.z_bankfull

    def get_subdivision_info(self, h: float) -> Dict[str, any]:
        """
        获取分区详细信息

        Args:
            h: 水深 (m)

        Returns:
            包含各区域详细信息的字典
        """
        regions = self._get_subdivision_properties(h)
        Q_total, Q_dict = self.compute_discharge_divided(h)

        info = {
            'total_discharge': Q_total,
            'is_overbank': self.is_overbank(h),
            'regions': {}
        }

        for region_name, props in regions.items():
            info['regions'][region_name] = {
                'area': props['A'],
                'wetted_perimeter': props['P'],
                'hydraulic_radius': props['R'],
                'manning_n': props['n'],
                'discharge': Q_dict[region_name],
                'discharge_fraction': Q_dict[region_name] / Q_total if Q_total > 0 else 0.0
            }

        return info

    def __repr__(self) -> str:
        """字符串表示"""
        return (f"CompoundChannel(id='{self.channel_id}', "
                f"n_main={self.n_main:.3f}, n_flood={self.n_flood:.3f}, "
                f"L={self.L:.0f}m, S0={self.S0:.5f})")


def create_compound_channel(stations: List[float],
                            elevations: List[float],
                            bankfull_elevation: float,
                            length: float,
                            bottom_slope: float,
                            manning_n_main: float,
                            manning_n_floodplain: float,
                            left_bank_station: Optional[float] = None,
                            right_bank_station: Optional[float] = None,
                            channel_id: str = "comp_channel") -> CompoundChannel:
    """
    便捷函数：创建复合断面渠道

    Args:
        stations: 桩号列表 (m)
        elevations: 高程列表 (m)
        bankfull_elevation: 满槽水位 (m)
        length: 长度 (m)
        bottom_slope: 底坡 S0
        manning_n_main: 主槽Manning系数
        manning_n_floodplain: 滩地Manning系数
        left_bank_station: 左岸桩号 (m)
        right_bank_station: 右岸桩号 (m)
        channel_id: 渠道ID

    Returns:
        CompoundChannel实例
    """
    return CompoundChannel(
        stations=np.array(stations),
        elevations=np.array(elevations),
        bankfull_elevation=bankfull_elevation,
        length=length,
        bottom_slope=bottom_slope,
        manning_n_main=manning_n_main,
        manning_n_floodplain=manning_n_floodplain,
        left_bank_station=left_bank_station,
        right_bank_station=right_bank_station,
        channel_id=channel_id
    )
