#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
薄壁堰 (Sharp-Crested Weir)

薄壁堰是一种薄板制成的溢流建筑物，水流越过堰顶形成薄层跌落水舌。
适用于流量测量、小型溢流建筑物等。

支持三种类型：
1. 矩形薄壁堰 (Rectangular)
   Q = (2/3) * C * B * sqrt(2g) * H^(3/2)

2. 三角堰 (Triangular/V-notch)
   Q = (8/15) * C * tan(θ/2) * sqrt(2g) * H^(5/2)

3. 梯形堰 (Trapezoidal/Cipolletti)
   Q = (2/3) * C * sqrt(2g) * [B*H^(3/2) + (8/15)*tan(θ/2)*H^(5/2)]

其中：
- C: 流量系数 (通常 0.6-0.65)
- B: 堰宽 (m)
- H: 堰顶以上水头 (m)
- θ: 三角堰缺口角度 (度)
- g: 重力加速度 (m/s²)

作者: Claude
日期: 2025-10-22
"""

import numpy as np
from typing import Optional
import sys
import os

# 添加父目录到路径
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from solvers.gate import HydraulicStructure


class SharpCrestedWeir(HydraulicStructure):
    """
    薄壁堰类

    支持矩形、三角和梯形薄壁堰的流量计算。
    提供解析导数用于牛顿迭代求解器。
    """

    def __init__(self, position: float, width: float, crest_elevation: float,
                 weir_type: str = 'rectangular', notch_angle: float = 90.0,
                 discharge_coefficient: float = 0.62, g: float = 9.81,
                 contraction_factor: float = 1.0):
        """
        初始化薄壁堰

        Args:
            position: 堰位置 (m)
            width: 堰宽 (m)，对于三角堰无意义
            crest_elevation: 堰顶高程 (m)
            weir_type: 堰类型 ('rectangular', 'triangular', 'trapezoidal')
            notch_angle: 三角堰缺口角度 (度)，仅三角堰和梯形堰使用
            discharge_coefficient: 流量系数 C (无量纲，典型值 0.62)
            g: 重力加速度 (m/s²)
            contraction_factor: 收缩系数 (考虑侧收缩影响)，1.0表示无收缩
        """
        super().__init__(position, width, g)
        self.crest_elevation = crest_elevation
        self.weir_type = weir_type.lower()
        self.notch_angle = notch_angle
        self.C = discharge_coefficient
        self.contraction_factor = contraction_factor

        # 验证堰类型
        valid_types = ['rectangular', 'triangular', 'trapezoidal']
        if self.weir_type not in valid_types:
            raise ValueError(f"Invalid weir type '{weir_type}'. Must be one of {valid_types}")

        # 预计算常数
        self.sqrt_2g = np.sqrt(2.0 * self.g)

        if self.weir_type in ['triangular', 'trapezoidal']:
            # 三角堰相关常数
            theta_rad = np.radians(notch_angle)
            self.tan_half_theta = np.tan(theta_rad / 2.0)
            # 三角堰系数：(8/15) * C * tan(θ/2) * sqrt(2g)
            self.C_triangular = (8.0 / 15.0) * self.C * self.tan_half_theta * self.sqrt_2g

        if self.weir_type in ['rectangular', 'trapezoidal']:
            # 矩形堰系数：(2/3) * C * B * sqrt(2g) * contraction_factor
            self.C_rectangular = (2.0 / 3.0) * self.C * self.width * self.sqrt_2g * self.contraction_factor

    def calculate_discharge(self, h_upstream: float, h_downstream: float,
                           t: Optional[float] = None) -> tuple:
        """
        计算过流量

        Args:
            h_upstream: 上游水深 (m)
            h_downstream: 下游水深 (m)，薄壁堰通常为自由出流，不受下游影响
            t: 当前时间 (s)，用于时变参数（本类未使用）

        Returns:
            (discharge, flow_type):
                - discharge: 流量 (m³/s)
                - flow_type: 流态类型 (通常为 'free')
        """
        # 计算堰顶以上水头
        H = h_upstream - self.crest_elevation

        # 如果上游水位低于堰顶，无流量
        if H <= 0:
            return 0.0, 'no_flow'

        # 计算流量（薄壁堰通常为自由出流）
        if self.weir_type == 'rectangular':
            # 矩形薄壁堰：Q = (2/3) * C * B * sqrt(2g) * H^(3/2)
            Q = self.C_rectangular * (H ** 1.5)

        elif self.weir_type == 'triangular':
            # 三角堰（V型缺口）：Q = (8/15) * C * tan(θ/2) * sqrt(2g) * H^(5/2)
            Q = self.C_triangular * (H ** 2.5)

        elif self.weir_type == 'trapezoidal':
            # 梯形堰（Cipolletti堰）：组合矩形和三角部分
            # Q = Q_rect + Q_tri
            Q_rect = self.C_rectangular * (H ** 1.5)
            Q_tri = self.C_triangular * (H ** 2.5)
            Q = Q_rect + Q_tri

        else:
            Q = 0.0

        # 检查下游淹没（简化判断）
        if h_downstream > self.crest_elevation + 0.67 * H:
            flow_type = 'submerged'
            # 注意：薄壁堰淹没流况下流量公式会变化，这里简化处理
            # 实际应用中可能需要引入淹没系数
        else:
            flow_type = 'free'

        return Q, flow_type

    def calculate_discharge_derivatives(self, h_upstream: float, h_downstream: float,
                                        t: Optional[float] = None) -> tuple:
        """
        计算过流量对上下游水深的解析导数

        用于牛顿求解器的Jacobian矩阵构建

        Args:
            h_upstream: 上游水深 (m)
            h_downstream: 下游水深 (m)
            t: 当前时间 (s)，用于时变参数（本类未使用）

        Returns:
            (dQ_dh_up, dQ_dh_down):
                - dQ_dh_up: ∂Q/∂h_upstream
                - dQ_dh_down: ∂Q/∂h_downstream (通常为0，自由出流)
        """
        # 计算堰顶以上水头
        H = h_upstream - self.crest_elevation

        # 如果上游水位低于堰顶，导数为0
        if H <= 1e-6:
            return 0.0, 0.0

        # 计算导数（dH/dh_up = 1）
        if self.weir_type == 'rectangular':
            # Q = C_rect * H^(3/2)
            # dQ/dH = C_rect * (3/2) * H^(1/2)
            # dQ/dh_up = dQ/dH * dH/dh_up = C_rect * (3/2) * H^(1/2) * 1
            dQ_dh_up = self.C_rectangular * 1.5 * np.sqrt(H)

        elif self.weir_type == 'triangular':
            # Q = C_tri * H^(5/2)
            # dQ/dH = C_tri * (5/2) * H^(3/2)
            dQ_dh_up = self.C_triangular * 2.5 * (H ** 1.5)

        elif self.weir_type == 'trapezoidal':
            # Q = Q_rect + Q_tri
            # dQ/dH = dQ_rect/dH + dQ_tri/dH
            dQ_rect_dH = self.C_rectangular * 1.5 * np.sqrt(H)
            dQ_tri_dH = self.C_triangular * 2.5 * (H ** 1.5)
            dQ_dh_up = dQ_rect_dH + dQ_tri_dH

        else:
            dQ_dh_up = 0.0

        # 薄壁堰为自由出流，不受下游影响
        dQ_dh_down = 0.0

        return dQ_dh_up, dQ_dh_down

    def __repr__(self) -> str:
        """对象的字符串表示"""
        if self.weir_type == 'rectangular':
            return (f"SharpCrestedWeir(type=rectangular, pos={self.position}m, "
                    f"width={self.width}m, crest_elev={self.crest_elevation}m, C={self.C:.3f})")
        elif self.weir_type == 'triangular':
            return (f"SharpCrestedWeir(type=triangular, pos={self.position}m, "
                    f"angle={self.notch_angle}°, crest_elev={self.crest_elevation}m, C={self.C:.3f})")
        else:  # trapezoidal
            return (f"SharpCrestedWeir(type=trapezoidal, pos={self.position}m, "
                    f"width={self.width}m, angle={self.notch_angle}°, "
                    f"crest_elev={self.crest_elevation}m, C={self.C:.3f})")


def test_sharp_crested_weir():
    """测试薄壁堰类"""
    print("=" * 80)
    print("薄壁堰 (Sharp-Crested Weir) 测试")
    print("=" * 80)

    # 创建三种类型的薄壁堰
    weir_rect = SharpCrestedWeir(
        position=500.0,
        width=2.0,
        crest_elevation=1.0,
        weir_type='rectangular',
        discharge_coefficient=0.62
    )

    weir_tri = SharpCrestedWeir(
        position=500.0,
        width=0.0,  # 三角堰不需要宽度
        crest_elevation=1.0,
        weir_type='triangular',
        notch_angle=90.0,  # 90度V型缺口
        discharge_coefficient=0.58
    )

    weir_trap = SharpCrestedWeir(
        position=500.0,
        width=2.0,
        crest_elevation=1.0,
        weir_type='trapezoidal',
        notch_angle=60.0,
        discharge_coefficient=0.62
    )

    print(f"\n堰参数:")
    print(f"  1. {weir_rect}")
    print(f"  2. {weir_tri}")
    print(f"  3. {weir_trap}")
    print()

    # 测试不同水位
    h_upstream_values = [1.1, 1.2, 1.3, 1.5, 2.0]
    h_downstream = 0.5  # 下游水位（不影响结果）

    print("过流量计算测试:")
    print("-" * 80)
    print(f"{'上游水深(m)':<15} {'矩形堰(m³/s)':<20} {'三角堰(m³/s)':<20} {'梯形堰(m³/s)':<20}")
    print("-" * 80)

    for h_up in h_upstream_values:
        Q_rect, _ = weir_rect.calculate_discharge(h_up, h_downstream)
        Q_tri, _ = weir_tri.calculate_discharge(h_up, h_downstream)
        Q_trap, _ = weir_trap.calculate_discharge(h_up, h_downstream)
        print(f"{h_up:<15.2f} {Q_rect:<20.4f} {Q_tri:<20.4f} {Q_trap:<20.4f}")

    print()
    print("=" * 80)
    print("导数验证（矩形堰）:")
    print("-" * 80)

    # 选择测试点
    h_up_test = 1.5
    h_down_test = 0.5

    Q0, _ = weir_rect.calculate_discharge(h_up_test, h_down_test)
    dQ_dh_up_analytical, dQ_dh_down_analytical = weir_rect.calculate_discharge_derivatives(h_up_test, h_down_test)

    # 数值导数
    eps = 1e-6
    Q_up, _ = weir_rect.calculate_discharge(h_up_test + eps, h_down_test)

    dQ_dh_up_numerical = (Q_up - Q0) / eps

    print(f"测试点: h_up={h_up_test}m, h_down={h_down_test}m")
    print(f"流量: Q={Q0:.4f} m³/s")
    print()
    print(f"∂Q/∂h_up:")
    print(f"  解析导数: {dQ_dh_up_analytical:.6f}")
    print(f"  数值导数: {dQ_dh_up_numerical:.6f}")
    print(f"  相对误差: {abs(dQ_dh_up_analytical - dQ_dh_up_numerical)/abs(dQ_dh_up_numerical)*100:.4f}%")
    print()
    print(f"∂Q/∂h_down:")
    print(f"  解析导数: {dQ_dh_down_analytical:.6f} (应为0，自由出流)")

    print()
    print("=" * 80)
    print("三角堰流量-水头关系特性:")
    print("-" * 80)
    print("三角堰对低流量测量更敏感（H^2.5关系），适合小流量测量")
    print()
    print(f"{'水头(m)':<12} {'矩形堰(m³/s)':<20} {'三角堰(m³/s)':<20} {'比值(三/矩)':<15}")
    print("-" * 80)

    for H in [0.05, 0.1, 0.2, 0.3, 0.5]:
        h_up = 1.0 + H
        Q_rect, _ = weir_rect.calculate_discharge(h_up, h_downstream)
        Q_tri, _ = weir_tri.calculate_discharge(h_up, h_downstream)
        ratio = Q_tri / Q_rect if Q_rect > 0 else 0.0
        print(f"{H:<12.3f} {Q_rect:<20.5f} {Q_tri:<20.5f} {ratio:<15.3f}")

    print()
    print("=" * 80)
    print("测试完成！")
    print("=" * 80)


if __name__ == "__main__":
    test_sharp_crested_weir()
