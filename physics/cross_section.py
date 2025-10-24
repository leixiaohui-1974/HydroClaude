"""
河道断面模块

支持多种断面类型：
1. 矩形断面
2. 梯形断面
3. 复式断面（主槽+滩地）
4. 自然河道断面（基于测量点）

功能：
- 计算过水面积 A(h)
- 计算湿周 P(h)
- 计算水力半径 R(h) = A/P
- 计算水面宽度 B(h)
- 计算断面几何参数

用于IDZ模型参数估计和在线辨识

作者：HydroClaude Team
日期：2025-10-24
"""

import numpy as np
from typing import List, Tuple, Optional
from dataclasses import dataclass
from enum import Enum
from scipy.interpolate import interp1d


class SectionType(Enum):
    """断面类型"""
    RECTANGULAR = "rectangular"     # 矩形
    TRAPEZOIDAL = "trapezoidal"    # 梯形
    COMPOUND = "compound"          # 复式
    NATURAL = "natural"            # 自然河道


@dataclass
class SectionGeometry:
    """断面几何参数"""
    area: float          # 过水面积 (m²)
    perimeter: float     # 湿周 (m)
    width: float         # 水面宽度 (m)
    hydraulic_radius: float  # 水力半径 (m)
    hydraulic_depth: float   # 水力深度 (m)


class CrossSection:
    """
    河道断面基类
    """

    def __init__(self, name: str):
        self.name = name
        self.section_type = None

    def compute_geometry(self, depth: float) -> SectionGeometry:
        """
        计算断面几何参数

        Args:
            depth: 水深 (m)

        Returns:
            断面几何参数
        """
        raise NotImplementedError

    def compute_area(self, depth: float) -> float:
        """计算过水面积"""
        return self.compute_geometry(depth).area

    def compute_perimeter(self, depth: float) -> float:
        """计算湿周"""
        return self.compute_geometry(depth).perimeter

    def compute_hydraulic_radius(self, depth: float) -> float:
        """计算水力半径"""
        geom = self.compute_geometry(depth)
        return geom.hydraulic_radius

    def compute_width(self, depth: float) -> float:
        """计算水面宽度"""
        return self.compute_geometry(depth).width


class RectangularSection(CrossSection):
    """
    矩形断面

    简单、常用于渠道
    """

    def __init__(self, name: str, width: float):
        """
        Args:
            name: 断面名称
            width: 底宽 (m)
        """
        super().__init__(name)
        self.section_type = SectionType.RECTANGULAR
        self.width = width

    def compute_geometry(self, depth: float) -> SectionGeometry:
        """计算矩形断面几何参数"""
        if depth <= 0:
            return SectionGeometry(0, 0, self.width, 0, 0)

        area = self.width * depth
        perimeter = self.width + 2 * depth
        width = self.width
        hydraulic_radius = area / perimeter
        hydraulic_depth = depth

        return SectionGeometry(
            area=area,
            perimeter=perimeter,
            width=width,
            hydraulic_radius=hydraulic_radius,
            hydraulic_depth=hydraulic_depth
        )


class TrapezoidalSection(CrossSection):
    """
    梯形断面

    最常用的渠道断面形式
    """

    def __init__(self, name: str, bottom_width: float, side_slope: float):
        """
        Args:
            name: 断面名称
            bottom_width: 底宽 (m)
            side_slope: 边坡系数 m (水平:垂直 = m:1)
        """
        super().__init__(name)
        self.section_type = SectionType.TRAPEZOIDAL
        self.bottom_width = bottom_width
        self.side_slope = side_slope  # m值

    def compute_geometry(self, depth: float) -> SectionGeometry:
        """计算梯形断面几何参数"""
        if depth <= 0:
            return SectionGeometry(0, 0, self.bottom_width, 0, 0)

        b = self.bottom_width
        m = self.side_slope
        h = depth

        # 过水面积
        area = (b + m * h) * h

        # 湿周
        perimeter = b + 2 * h * np.sqrt(1 + m**2)

        # 水面宽度
        width = b + 2 * m * h

        # 水力半径
        hydraulic_radius = area / perimeter

        # 水力深度
        hydraulic_depth = area / width

        return SectionGeometry(
            area=area,
            perimeter=perimeter,
            width=width,
            hydraulic_radius=hydraulic_radius,
            hydraulic_depth=hydraulic_depth
        )


class CompoundSection(CrossSection):
    """
    复式断面

    由主槽和滩地组成，适用于河道
    """

    def __init__(self, name: str,
                 main_bottom_width: float,
                 main_depth: float,
                 main_side_slope: float,
                 flood_width_left: float,
                 flood_width_right: float,
                 flood_side_slope: float = 0.0):
        """
        Args:
            name: 断面名称
            main_bottom_width: 主槽底宽 (m)
            main_depth: 主槽深度 (m)
            main_side_slope: 主槽边坡系数
            flood_width_left: 左滩地宽度 (m)
            flood_width_right: 右滩地宽度 (m)
            flood_side_slope: 滩地边坡系数
        """
        super().__init__(name)
        self.section_type = SectionType.COMPOUND

        self.main_bottom_width = main_bottom_width
        self.main_depth = main_depth
        self.main_side_slope = main_side_slope

        self.flood_width_left = flood_width_left
        self.flood_width_right = flood_width_right
        self.flood_side_slope = flood_side_slope

    def compute_geometry(self, depth: float) -> SectionGeometry:
        """计算复式断面几何参数"""
        if depth <= 0:
            return SectionGeometry(0, 0, 0, 0, 0)

        b_main = self.main_bottom_width
        h_main = self.main_depth
        m_main = self.main_side_slope

        # 主槽部分
        if depth <= h_main:
            # 水深在主槽内
            h = depth
            area = (b_main + m_main * h) * h
            perimeter = b_main + 2 * h * np.sqrt(1 + m_main**2)
            width = b_main + 2 * m_main * h

        else:
            # 水深超过主槽
            # 主槽满水
            area_main = (b_main + m_main * h_main) * h_main
            perim_main = b_main + 2 * h_main * np.sqrt(1 + m_main**2)
            width_main = b_main + 2 * m_main * h_main

            # 滩地水深
            h_flood = depth - h_main

            # 左滩地
            area_left = self.flood_width_left * h_flood
            perim_left = h_flood

            # 右滩地
            area_right = self.flood_width_right * h_flood
            perim_right = h_flood

            # 总计
            area = area_main + area_left + area_right
            perimeter = perim_main + perim_left + perim_right
            width = width_main + self.flood_width_left + self.flood_width_right

        hydraulic_radius = area / perimeter if perimeter > 0 else 0
        hydraulic_depth = area / width if width > 0 else 0

        return SectionGeometry(
            area=area,
            perimeter=perimeter,
            width=width,
            hydraulic_radius=hydraulic_radius,
            hydraulic_depth=hydraulic_depth
        )


class NaturalSection(CrossSection):
    """
    自然河道断面

    基于实测断面点
    """

    def __init__(self, name: str, elevations: np.ndarray, distances: np.ndarray):
        """
        Args:
            name: 断面名称
            elevations: 高程数组 (m)
            distances: 距离数组 (m)，从左到右
        """
        super().__init__(name)
        self.section_type = SectionType.NATURAL

        # 确保数据有序
        sorted_idx = np.argsort(distances)
        self.distances = distances[sorted_idx]
        self.elevations = elevations[sorted_idx]

        # 找到最低点
        self.min_elevation = np.min(self.elevations)

    def compute_geometry(self, depth: float) -> SectionGeometry:
        """计算自然断面几何参数"""
        if depth <= 0:
            return SectionGeometry(0, 0, 0, 0, 0)

        # 水位
        water_level = self.min_elevation + depth

        # 找到水下部分
        underwater = self.elevations < water_level

        if not np.any(underwater):
            return SectionGeometry(0, 0, 0, 0, 0)

        # 计算过水面积（梯形法则）
        area = 0.0
        perimeter = 0.0
        x_waterline_left = None   # 水面线左端
        x_waterline_right = None  # 水面线右端

        for i in range(len(self.distances) - 1):
            x1, y1 = self.distances[i], self.elevations[i]
            x2, y2 = self.distances[i + 1], self.elevations[i + 1]

            # 段长
            seg_length = np.sqrt((x2 - x1)**2 + (y2 - y1)**2)

            # 水深
            d1 = max(0, water_level - y1)
            d2 = max(0, water_level - y2)

            if d1 > 0 or d2 > 0:
                # 梯形面积
                seg_area = 0.5 * (d1 + d2) * (x2 - x1)
                area += seg_area

                # 湿周 - 处理完全浸没和部分浸没
                if d1 > 0 and d2 > 0:
                    # 完全浸没：整段都在水下
                    perimeter += seg_length
                elif d1 == 0 and d2 > 0:
                    # 部分浸没：从水线开始到x2
                    # 找到水线交点位置
                    if y2 != y1:
                        x_intersection = x1 + (water_level - y1) / (y2 - y1) * (x2 - x1)
                        y_intersection = water_level
                        partial_length = np.sqrt((x2 - x_intersection)**2 + (y2 - y_intersection)**2)
                        perimeter += partial_length
                    # else: y1 == y2 == water_level, 水平线段，湿周为0
                elif d1 > 0 and d2 == 0:
                    # 部分浸没：从x1到水线结束
                    # 找到水线交点位置
                    if y2 != y1:
                        x_intersection = x1 + (water_level - y1) / (y2 - y1) * (x2 - x1)
                        y_intersection = water_level
                        partial_length = np.sqrt((x_intersection - x1)**2 + (y_intersection - y1)**2)
                        perimeter += partial_length
                    # else: y1 == y2 == water_level, 水平线段，湿周为0

                # 水面宽度：找水线与断面的交点
                # 情况1：d1=0, d2>0 - 水线从这段开始（左端）
                if d1 == 0 and d2 > 0 and x_waterline_left is None:
                    # 线性插值找交点
                    if y2 != y1:
                        x_waterline_left = x1 + (water_level - y1) / (y2 - y1) * (x2 - x1)
                    else:
                        x_waterline_left = x1

                # 情况2：d1>0, d2=0 - 水线在这段结束（右端）
                if d1 > 0 and d2 == 0:
                    # 线性插值找交点
                    if y2 != y1:
                        x_waterline_right = x1 + (water_level - y1) / (y2 - y1) * (x2 - x1)
                    else:
                        x_waterline_right = x1

                # 情况3：d1>0, d2>0 - 整段都在水下
                if d1 > 0 and d2 > 0:
                    if x_waterline_left is None:
                        x_waterline_left = x1
                    x_waterline_right = x2  # 持续更新右端

        # 水面宽度
        if x_waterline_left is not None and x_waterline_right is not None:
            width = x_waterline_right - x_waterline_left
        else:
            width = 0

        hydraulic_radius = area / perimeter if perimeter > 0 else 0
        hydraulic_depth = area / width if width > 0 else 0

        return SectionGeometry(
            area=area,
            perimeter=perimeter,
            width=width,
            hydraulic_radius=hydraulic_radius,
            hydraulic_depth=hydraulic_depth
        )


def compute_idz_parameters_from_section(
    section: CrossSection,
    length: float,
    normal_depth: float,
    normal_flow: float,
    manning_n: float,
    bed_slope: float
) -> dict:
    """
    从断面几何和水力条件计算IDZ参数

    考虑断面形状对参数的影响

    Args:
        section: 断面对象
        length: 渠道长度 (m)
        normal_depth: 正常水深 (m)
        normal_flow: 正常流量 (m³/s)
        manning_n: 曼宁系数
        bed_slope: 底坡

    Returns:
        IDZ参数字典
    """
    # 计算正常水深下的断面几何
    geom = section.compute_geometry(normal_depth)

    # 正常流速
    velocity = normal_flow / geom.area if geom.area > 0 else 0

    # 弗劳德数
    froude = velocity / np.sqrt(9.81 * geom.hydraulic_depth)

    # 波速
    wave_celerity = velocity + np.sqrt(9.81 * geom.hydraulic_depth)

    # IDZ参数估计
    # 增益：水位变化 / 流量变化
    # 考虑断面形状：dh/dQ = 1 / (dA/dh * v)
    # 数值微分估计 dA/dh
    delta_h = 0.01  # 1cm微分步长
    geom_plus = section.compute_geometry(normal_depth + delta_h)
    geom_minus = section.compute_geometry(normal_depth - delta_h)

    dA_dh = (geom_plus.area - geom_minus.area) / (2 * delta_h)

    # IDZ增益（简化）
    K = length / (dA_dh * velocity) if (dA_dh > 0 and velocity > 0) else length / geom.area

    # 零点时间常数（回水效应）
    tau_z = length / (velocity * (1 + froude**2))

    # 延迟时间常数
    tau_d = length / (velocity * np.sqrt(1 + froude**2))

    # 纯滞后（波传播时间）
    theta = length / wave_celerity

    return {
        'K': K,
        'tau_z': tau_z,
        'tau_d': tau_d,
        'theta': theta,
        'section_geometry': geom,
        'velocity': velocity,
        'froude': froude,
        'wave_celerity': wave_celerity,
        'dA_dh': dA_dh
    }


if __name__ == "__main__":
    """测试断面模块"""

    print("=" * 70)
    print("河道断面模块测试")
    print("=" * 70)

    # 测试1：矩形断面
    print("\n[测试1] 矩形断面")
    print("-" * 70)

    rect = RectangularSection("Rect1", width=10.0)

    depths = [0.5, 1.0, 2.0, 3.0]
    print(f"{'水深(m)':>8} {'面积(m²)':>10} {'湿周(m)':>10} {'水力半径(m)':>12} {'宽度(m)':>10}")
    for h in depths:
        geom = rect.compute_geometry(h)
        print(f"{h:8.2f} {geom.area:10.2f} {geom.perimeter:10.2f} "
              f"{geom.hydraulic_radius:12.3f} {geom.width:10.2f}")

    # 测试2：梯形断面
    print("\n[测试2] 梯形断面 (m=1.5)")
    print("-" * 70)

    trap = TrapezoidalSection("Trap1", bottom_width=8.0, side_slope=1.5)

    print(f"{'水深(m)':>8} {'面积(m²)':>10} {'湿周(m)':>10} {'水力半径(m)':>12} {'宽度(m)':>10}")
    for h in depths:
        geom = trap.compute_geometry(h)
        print(f"{h:8.2f} {geom.area:10.2f} {geom.perimeter:10.2f} "
              f"{geom.hydraulic_radius:12.3f} {geom.width:10.2f}")

    # 测试3：复式断面
    print("\n[测试3] 复式断面")
    print("-" * 70)

    compound = CompoundSection(
        "Compound1",
        main_bottom_width=10.0,
        main_depth=3.0,
        main_side_slope=1.0,
        flood_width_left=20.0,
        flood_width_right=20.0
    )

    depths_compound = [1.0, 2.0, 3.0, 4.0, 5.0]
    print(f"{'水深(m)':>8} {'面积(m²)':>10} {'湿周(m)':>10} {'水力半径(m)':>12} {'宽度(m)':>10}")
    for h in depths_compound:
        geom = compound.compute_geometry(h)
        print(f"{h:8.2f} {geom.area:10.2f} {geom.perimeter:10.2f} "
              f"{geom.hydraulic_radius:12.3f} {geom.width:10.2f}")

    # 测试4：自然河道断面
    print("\n[测试4] 自然河道断面")
    print("-" * 70)

    # 模拟实测断面数据
    distances = np.array([0, 5, 10, 15, 20, 25, 30, 35, 40])
    elevations = np.array([5.0, 3.5, 2.0, 1.0, 0.5, 1.2, 2.5, 4.0, 5.5])

    natural = NaturalSection("Natural1", elevations, distances)

    print(f"最低高程: {natural.min_elevation:.2f}m")
    print(f"\n{'水深(m)':>8} {'面积(m²)':>10} {'湿周(m)':>10} {'水力半径(m)':>12} {'宽度(m)':>10}")
    for h in [0.5, 1.0, 1.5, 2.0, 3.0]:
        geom = natural.compute_geometry(h)
        print(f"{h:8.2f} {geom.area:10.2f} {geom.perimeter:10.2f} "
              f"{geom.hydraulic_radius:12.3f} {geom.width:10.2f}")

    # 测试5：IDZ参数计算
    print("\n[测试5] IDZ参数计算（考虑断面形状）")
    print("-" * 70)

    sections = [
        ("矩形", rect),
        ("梯形", trap),
        ("复式", compound)
    ]

    for name, section in sections:
        params = compute_idz_parameters_from_section(
            section=section,
            length=1000.0,
            normal_depth=2.0,
            normal_flow=20.0,
            manning_n=0.025,
            bed_slope=0.0001
        )

        print(f"\n{name}断面:")
        print(f"  K = {params['K']:.2f} m/(m³/s)")
        print(f"  τ_z = {params['tau_z']:.1f} s")
        print(f"  τ_d = {params['tau_d']:.1f} s")
        print(f"  θ = {params['theta']:.1f} s")
        print(f"  流速 = {params['velocity']:.3f} m/s")
        print(f"  弗劳德数 = {params['froude']:.3f}")
        print(f"  dA/dh = {params['dA_dh']:.2f} m²/m")

    print("\n" + "=" * 70)
    print("断面模块测试完成！")
    print("=" * 70)
