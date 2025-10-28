#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
复式断面复合糙率计算模块

复式断面（主槽+滩地）通常具有不同的糙率系数：
- 主槽：通常较光滑，n = 0.020-0.030
- 滩地：通常较粗糙，n = 0.040-0.080（植被、灌木）

支持3种复合糙率计算方法：
1. HEC-RAS方法（推荐）：分区输沙能力相加
2. Horton公式：等效糙率系数
3. Lotter公式：加权平均法

参考标准：
- HEC-RAS Hydraulic Reference Manual
- Chow (1959) "Open-Channel Hydraulics"
- USGS Water Supply Paper 2339

作者：HydroClaude Team
日期：2025-10-28
"""

import numpy as np
from typing import List, Tuple, Dict, Optional
from enum import Enum


class CompositeMethod(Enum):
    """复合糙率计算方法"""
    HEC_RAS = "hec_ras"      # HEC-RAS方法（分区输沙能力）
    HORTON = "horton"        # Horton公式（等效糙率）
    LOTTER = "lotter"        # Lotter公式（加权平均）


class RoughnessZone:
    """糙率分区"""

    def __init__(self, name: str, area: float, perimeter: float,
                 manning_n: float, width: float = 0.0):
        """
        初始化糙率分区

        Args:
            name: 分区名称 (如 'main', 'left_flood', 'right_flood')
            area: 过水面积 A (m²)
            perimeter: 湿周 P (m)
            manning_n: 曼宁糙率系数 n
            width: 水面宽度 B (m)，可选
        """
        self.name = name
        self.area = area
        self.perimeter = perimeter
        self.manning_n = manning_n
        self.width = width

        # 计算水力半径
        self.hydraulic_radius = area / perimeter if perimeter > 0 else 0.0

    def compute_conveyance(self) -> float:
        """
        计算本分区的输沙能力（流量模数）

        K = (1/n) * A * R^(2/3)

        Returns:
            输沙能力 K (m³/s)
        """
        if self.area <= 0 or self.manning_n <= 0:
            return 0.0

        K = (1.0 / self.manning_n) * self.area * (self.hydraulic_radius ** (2.0/3.0))
        return K

    def __repr__(self) -> str:
        return (f"RoughnessZone(name='{self.name}', A={self.area:.2f}m², "
                f"P={self.perimeter:.2f}m, n={self.manning_n:.4f})")


class CompositeRoughness:
    """
    复合糙率计算器

    用于复式断面、天然河道等具有不同糙率分区的情况
    """

    def __init__(self, method: CompositeMethod = CompositeMethod.HEC_RAS):
        """
        初始化复合糙率计算器

        Args:
            method: 计算方法
        """
        self.method = method

    def compute_composite_conveyance(self, zones: List[RoughnessZone]) -> float:
        """
        计算复合断面的总输沙能力

        Args:
            zones: 糙率分区列表

        Returns:
            总输沙能力 K_total (m³/s)
        """
        if not zones:
            return 0.0

        if self.method == CompositeMethod.HEC_RAS:
            return self._compute_hec_ras(zones)
        elif self.method == CompositeMethod.HORTON:
            return self._compute_horton(zones)
        elif self.method == CompositeMethod.LOTTER:
            return self._compute_lotter(zones)
        else:
            raise ValueError(f"Unknown method: {self.method}")

    def _compute_hec_ras(self, zones: List[RoughnessZone]) -> float:
        """
        HEC-RAS方法：分区输沙能力相加

        K_total = Σ K_i = Σ [(1/n_i) * A_i * R_i^(2/3)]

        这是最常用和最准确的方法，被HEC-RAS、MIKE 11等采用

        Args:
            zones: 糙率分区列表

        Returns:
            总输沙能力 K_total
        """
        K_total = sum(zone.compute_conveyance() for zone in zones)
        return K_total

    def _compute_horton(self, zones: List[RoughnessZone]) -> float:
        """
        Horton公式：计算等效糙率系数

        n_composite = [(Σ P_i * n_i^(3/2)) / P_total]^(2/3)

        然后用等效糙率计算总输沙能力：
        K_total = (1/n_composite) * A_total * R_total^(2/3)

        Args:
            zones: 糙率分区列表

        Returns:
            总输沙能力 K_total
        """
        # 计算总面积和总湿周
        A_total = sum(zone.area for zone in zones)
        P_total = sum(zone.perimeter for zone in zones)

        if P_total <= 0 or A_total <= 0:
            return 0.0

        # Horton公式计算等效糙率
        numerator = sum(zone.perimeter * (zone.manning_n ** 1.5) for zone in zones)
        n_composite = (numerator / P_total) ** (2.0/3.0)

        # 用等效糙率计算输沙能力
        R_total = A_total / P_total
        K_total = (1.0 / n_composite) * A_total * (R_total ** (2.0/3.0))

        return K_total

    def _compute_lotter(self, zones: List[RoughnessZone]) -> float:
        """
        Lotter公式：加权平均法

        K_total = (Σ K_i * P_i) / P_total

        考虑各分区的湿周比例

        Args:
            zones: 糙率分区列表

        Returns:
            总输沙能力 K_total
        """
        P_total = sum(zone.perimeter for zone in zones)

        if P_total <= 0:
            return 0.0

        # 加权求和
        weighted_sum = sum(zone.compute_conveyance() * zone.perimeter for zone in zones)
        K_total = weighted_sum / P_total

        return K_total

    def compute_composite_manning_n(self, zones: List[RoughnessZone]) -> float:
        """
        计算等效曼宁糙率系数

        从复合输沙能力反推等效糙率：
        n_eq = A_total * R_total^(2/3) / K_total

        Args:
            zones: 糙率分区列表

        Returns:
            等效曼宁系数 n_eq
        """
        A_total = sum(zone.area for zone in zones)
        P_total = sum(zone.perimeter for zone in zones)

        if P_total <= 0 or A_total <= 0:
            return 0.025  # 默认值

        R_total = A_total / P_total
        K_total = self.compute_composite_conveyance(zones)

        if K_total <= 0:
            return 0.025

        # 从 K = (1/n) * A * R^(2/3) 反推 n
        n_eq = A_total * (R_total ** (2.0/3.0)) / K_total

        return n_eq

    def compute_flow_distribution(self, zones: List[RoughnessZone],
                                  Q_total: float, slope: float) -> Dict[str, float]:
        """
        计算各分区的流量分配

        Q_i = K_i * sqrt(slope)
        Q_total = Σ Q_i

        因此：Q_i = (K_i / K_total) * Q_total

        Args:
            zones: 糙率分区列表
            Q_total: 总流量 (m³/s)
            slope: 能坡 S (m/m)

        Returns:
            各分区流量字典 {'zone_name': Q_i}
        """
        K_total = self.compute_composite_conveyance(zones)

        if K_total <= 0:
            return {zone.name: 0.0 for zone in zones}

        flow_distribution = {}
        for zone in zones:
            K_i = zone.compute_conveyance()
            Q_i = (K_i / K_total) * Q_total
            flow_distribution[zone.name] = Q_i

        return flow_distribution


def compute_friction_slope_composite(zones: List[RoughnessZone],
                                     Q_total: float) -> float:
    """
    计算复合断面的摩阻坡度

    由Manning公式：Q = K * sqrt(Sf)
    因此：Sf = (Q / K)²

    Args:
        zones: 糙率分区列表
        Q_total: 总流量 (m³/s)

    Returns:
        摩阻坡度 Sf (m/m)
    """
    calc = CompositeRoughness(method=CompositeMethod.HEC_RAS)
    K_total = calc.compute_composite_conveyance(zones)

    if K_total <= 0:
        return 0.0

    Sf = (Q_total / K_total) ** 2
    return Sf


if __name__ == "__main__":
    """测试复合糙率模块"""

    print("=" * 70)
    print("复合糙率计算模块测试")
    print("=" * 70)

    # 测试案例：复式断面
    print("\n[测试1] 复式断面 - 三个分区")
    print("-" * 70)

    # 参数设置
    # 主槽: 底宽10m, 水深2m, 边坡1:1.5, n=0.025
    # 滩地: 左右各15m宽, 水深1m, n=0.060

    # 主槽
    h_main = 2.0
    b_main = 10.0
    m_main = 1.5
    A_main = (b_main + m_main * h_main) * h_main
    P_main = b_main + 2 * h_main * np.sqrt(1 + m_main**2)

    # 滩地水深
    h_flood = 1.0

    # 左滩地
    b_left = 15.0
    A_left = b_left * h_flood
    P_left = h_flood  # 只计算底部湿周

    # 右滩地
    b_right = 15.0
    A_right = b_right * h_flood
    P_right = h_flood

    print(f"主槽: A={A_main:.2f}m², P={P_main:.2f}m, n=0.025")
    print(f"左滩: A={A_left:.2f}m², P={P_left:.2f}m, n=0.060")
    print(f"右滩: A={A_right:.2f}m², P={P_right:.2f}m, n=0.060")

    # 创建糙率分区
    zone_main = RoughnessZone("main", A_main, P_main, 0.025)
    zone_left = RoughnessZone("left_flood", A_left, P_left, 0.060)
    zone_right = RoughnessZone("right_flood", A_right, P_right, 0.060)

    zones = [zone_main, zone_left, zone_right]

    # 测试不同方法
    methods = [
        (CompositeMethod.HEC_RAS, "HEC-RAS方法"),
        (CompositeMethod.HORTON, "Horton公式"),
        (CompositeMethod.LOTTER, "Lotter公式")
    ]

    print(f"\n{'方法':<20} {'K (m³/s)':<15} {'n_eq':<10}")
    print("-" * 50)

    for method, name in methods:
        calc = CompositeRoughness(method=method)
        K_total = calc.compute_composite_conveyance(zones)
        n_eq = calc.compute_composite_manning_n(zones)
        print(f"{name:<20} {K_total:>12.2f}   {n_eq:>8.4f}")

    # 测试流量分配
    print("\n[测试2] 流量分配")
    print("-" * 70)

    Q_total = 100.0  # m³/s
    slope = 0.001

    calc = CompositeRoughness(method=CompositeMethod.HEC_RAS)
    flow_dist = calc.compute_flow_distribution(zones, Q_total, slope)

    print(f"总流量: Q = {Q_total} m³/s")
    print(f"坡度: S = {slope}")
    print(f"\n各分区流量分配:")

    for name, Q_i in flow_dist.items():
        percentage = (Q_i / Q_total) * 100
        print(f"  {name:15s}: Q = {Q_i:6.2f} m³/s ({percentage:5.1f}%)")

    # 验证质量守恒
    Q_sum = sum(flow_dist.values())
    print(f"\n质量守恒检查: Σ Q_i = {Q_sum:.2f} m³/s")
    assert abs(Q_sum - Q_total) < 1e-10, "质量守恒失败!"
    print("✓ 质量守恒验证通过")

    # 测试摩阻坡度计算
    print("\n[测试3] 摩阻坡度计算")
    print("-" * 70)

    Sf = compute_friction_slope_composite(zones, Q_total)
    print(f"流量 Q = {Q_total} m³/s")
    print(f"摩阻坡度 Sf = {Sf:.6f}")

    # 对比单一糙率的情况
    A_total = sum(z.area for z in zones)
    P_total = sum(z.perimeter for z in zones)
    R_total = A_total / P_total
    n_single = 0.025  # 假设全断面使用主槽糙率
    K_single = (1/n_single) * A_total * R_total**(2/3)
    Sf_single = (Q_total / K_single)**2

    print(f"\n对比：如果全断面使用 n=0.025:")
    print(f"  Sf_single = {Sf_single:.6f}")
    print(f"  相对差异 = {abs(Sf - Sf_single)/Sf*100:.1f}%")

    print("\n" + "=" * 70)
    print("复合糙率模块测试完成!")
    print("=" * 70)
