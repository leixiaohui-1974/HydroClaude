#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
溢洪道 (Spillway)

溢洪道是水库大坝的泄洪建筑物，用于安全排泄超过水库调蓄能力的洪水。

支持两种类型：
1. 自由溢流堰 (Free-overflow spillway)
   - WES标准剖面（Waterways Experiment Station）
   - Q = C * L * H^(3/2)

2. 闸控溢流堰 (Gated spillway)
   - 组合闸门孔流和堰流
   - 闸门全开：堰流
   - 闸门部分开：孔流 + 堰流

流量计算公式：
- 自由溢流：Q = C * L * H^(3/2) * sqrt(2g)
- 闸门孔流：Q = Cd * L * e * sqrt(2g * Δh)
- 组合流：根据开度自动判别

其中：
- C: 堰流系数 (WES标准约 2.0-2.2)
- Cd: 孔流系数 (约 0.6-0.8)
- L: 堰长（净宽）(m)
- H: 堰顶以上水头 (m)
- e: 闸门开度 (m)
- g: 重力加速度 (m/s²)

作者: Claude
日期: 2025-10-22
"""

import numpy as np
from typing import Optional, Union, Callable
import sys
import os

# 添加父目录到路径
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from solvers.gate import HydraulicStructure


class Spillway(HydraulicStructure):
    """
    溢洪道类

    支持自由溢流和闸控溢流两种模式。
    自动根据闸门开度和水位判别流态（堰流、孔流或组合流）。
    """

    def __init__(self, position: float, length: float, crest_elevation: float,
                 gate_height: Optional[float] = None,
                 gate_opening: Union[float, Callable[[float], float], None] = None,
                 spillway_coefficient: float = 2.1,
                 gate_discharge_coefficient: float = 0.7,
                 g: float = 9.81,
                 design_head: float = None):
        """
        初始化溢洪道

        Args:
            position: 溢洪道位置 (m)
            length: 堰长（净宽）(m)
            crest_elevation: 堰顶高程 (m)
            gate_height: 闸门高度 (m)，None表示无闸门（自由溢流）
            gate_opening: 闸门开度 (m) 或时间函数 callable(t)
                         None表示闸门全开或无闸门
            spillway_coefficient: WES堰流系数 (无量纲，标准值 2.0-2.2)
            gate_discharge_coefficient: 闸门孔流系数 (无量纲，典型值 0.6-0.8)
            g: 重力加速度 (m/s²)
            design_head: 设计水头 (m)，用于WES剖面优化，None则使用实际水头
        """
        super().__init__(position, length, g)
        self.length = length  # 堰长
        self.crest_elevation = crest_elevation
        self.gate_height = gate_height
        self.gate_opening = gate_opening
        self.C_weir = spillway_coefficient
        self.Cd_gate = gate_discharge_coefficient
        self.design_head = design_head

        # 判断是否有闸门
        self.has_gate = (gate_height is not None)

        # 预计算常数
        self.sqrt_2g = np.sqrt(2.0 * self.g)
        # 注意: WES标准堰流系数C=2.0-2.2已经包含了sqrt(2g)因子
        # 标准公式为 Q = C * L * H^(3/2)，不需要再乘以sqrt(2g)

        # 检查gate_opening类型
        self.gate_opening_is_callable = callable(gate_opening)

    def get_gate_opening(self, t: Optional[float] = None) -> float:
        """
        获取当前闸门开度

        Args:
            t: 当前时间 (s)

        Returns:
            闸门开度 (m)
        """
        if not self.has_gate:
            return self.gate_height if self.gate_height else 0.0

        if self.gate_opening is None:
            # 无开度指定，视为全开
            return self.gate_height

        if self.gate_opening_is_callable:
            # 时变开度
            return self.gate_opening(t if t is not None else self.current_time)
        else:
            # 常数开度
            return self.gate_opening

    def calculate_discharge(self, h_upstream: float, h_downstream: float,
                           t: Optional[float] = None) -> tuple:
        """
        计算过流量

        根据闸门状态和水位自动判别流态：
        1. 无闸门或闸门全开：堰流
        2. 闸门部分开且水头 > 开度：孔流（淹没或自由）
        3. 闸门部分开但水头 <= 开度：堰流

        Args:
            h_upstream: 上游水深 (m)
            h_downstream: 下游水深 (m)
            t: 当前时间 (s)，用于时变闸门开度

        Returns:
            (discharge, flow_type):
                - discharge: 流量 (m³/s)
                - flow_type: 流态类型
        """
        # 计算堰顶以上水头
        H = h_upstream - self.crest_elevation

        # 如果上游水位低于堰顶，无流量
        if H <= 0:
            return 0.0, 'no_flow'

        # 获取闸门开度
        e = self.get_gate_opening(t)

        # 判断流态
        if not self.has_gate or e is None or e >= H:
            # 情况1：无闸门，或闸门全开，或开度大于水头 → 堰流
            flow_type = 'weir_flow'
            # WES堰流：Q = C * L * H^(3/2)  (C已包含sqrt(2g)因子)
            Q = self.C_weir * self.length * (H ** 1.5)

        else:
            # 情况2：闸门部分开 → 孔流
            # 判断淹没度
            h_gate_bottom = self.crest_elevation  # 闸门底部高程（假设闸门在堰顶）
            h_gate_opening_top = h_gate_bottom + e  # 闸门开口顶部高程

            if h_downstream > h_gate_opening_top:
                # 淹没孔流
                flow_type = 'orifice_submerged'
                # Q = Cd * L * e * sqrt(2g * Δh)
                delta_h = h_upstream - h_downstream
                Q = self.Cd_gate * self.length * e * self.sqrt_2g * np.sqrt(max(0, delta_h))
            else:
                # 自由孔流
                flow_type = 'orifice_free'
                # Q = Cd * L * e * sqrt(2g * H)
                # 这里H是闸门中心线处的水头，简化为堰顶以上水头
                Q = self.Cd_gate * self.length * e * self.sqrt_2g * np.sqrt(H)

        return Q, flow_type

    def calculate_discharge_derivatives(self, h_upstream: float, h_downstream: float,
                                        t: Optional[float] = None) -> tuple:
        """
        计算过流量对上下游水深的解析导数

        用于牛顿求解器的Jacobian矩阵构建

        Args:
            h_upstream: 上游水深 (m)
            h_downstream: 下游水深 (m)
            t: 当前时间 (s)，用于时变参数

        Returns:
            (dQ_dh_up, dQ_dh_down):
                - dQ_dh_up: ∂Q/∂h_upstream
                - dQ_dh_down: ∂Q/∂h_downstream
        """
        # 计算堰顶以上水头
        H = h_upstream - self.crest_elevation

        # 如果上游水位低于堰顶，导数为0
        if H <= 1e-6:
            return 0.0, 0.0

        # 获取闸门开度
        e = self.get_gate_opening(t)

        # 根据流态计算导数
        if not self.has_gate or e is None or e >= H:
            # 堰流：Q = C * L * H^(3/2)
            # dQ/dH = C * L * (3/2) * H^(1/2)
            # dQ/dh_up = dQ/dH = 1.5 * C * L * sqrt(H)
            dQ_dh_up = 1.5 * self.C_weir * self.length * np.sqrt(H)
            dQ_dh_down = 0.0  # 堰流不受下游影响

        else:
            # 孔流
            h_gate_opening_top = self.crest_elevation + e

            if h_downstream > h_gate_opening_top:
                # 淹没孔流：Q = Cd * L * e * sqrt(2g * Δh)
                # Δh = h_up - h_down
                # dQ/dh_up = Cd * L * e * sqrt(2g) / (2 * sqrt(Δh))
                # dQ/dh_down = -dQ/dh_up
                delta_h = max(1e-6, h_upstream - h_downstream)
                coeff = self.Cd_gate * self.length * e * self.sqrt_2g / (2.0 * np.sqrt(delta_h))
                dQ_dh_up = coeff
                dQ_dh_down = -coeff
            else:
                # 自由孔流：Q = Cd * L * e * sqrt(2g * H)
                # dQ/dH = Cd * L * e * sqrt(2g) / (2 * sqrt(H))
                coeff = self.Cd_gate * self.length * e * self.sqrt_2g / (2.0 * np.sqrt(H))
                dQ_dh_up = coeff
                dQ_dh_down = 0.0  # 自由孔流不受下游影响

        return dQ_dh_up, dQ_dh_down

    def __repr__(self) -> str:
        """对象的字符串表示"""
        if self.has_gate:
            return (f"Spillway(pos={self.position}m, length={self.length}m, "
                    f"crest_elev={self.crest_elevation}m, gate_height={self.gate_height}m, "
                    f"C_weir={self.C_weir:.2f}, Cd_gate={self.Cd_gate:.2f})")
        else:
            return (f"Spillway(pos={self.position}m, length={self.length}m, "
                    f"crest_elev={self.crest_elevation}m, C_weir={self.C_weir:.2f}, type=free-overflow)")


def test_spillway():
    """测试溢洪道类"""
    print("=" * 80)
    print("溢洪道 (Spillway) 测试")
    print("=" * 80)

    # 测试1：自由溢流堰（无闸门）
    spillway_free = Spillway(
        position=1000.0,
        length=50.0,          # 堰长50m
        crest_elevation=100.0,
        gate_height=None,     # 无闸门
        spillway_coefficient=2.1
    )

    # 测试2：闸控溢洪道（闸门固定开度）
    spillway_gated = Spillway(
        position=1000.0,
        length=50.0,
        crest_elevation=100.0,
        gate_height=8.0,      # 闸门高8m
        gate_opening=3.0,     # 开度3m
        spillway_coefficient=2.1,
        gate_discharge_coefficient=0.7
    )

    # 测试3：时变闸门开度
    def time_varying_opening(t):
        """时变开度：从0逐渐开到5m"""
        return min(5.0, t / 100.0)

    spillway_time_varying = Spillway(
        position=1000.0,
        length=50.0,
        crest_elevation=100.0,
        gate_height=8.0,
        gate_opening=time_varying_opening,
        spillway_coefficient=2.1,
        gate_discharge_coefficient=0.7
    )

    print(f"\n溢洪道参数:")
    print(f"  1. {spillway_free}")
    print(f"  2. {spillway_gated}")
    print(f"  3. {spillway_time_varying}")
    print()

    # 测试不同水位的流量
    test_water_levels = [
        # (h_up, h_down, 描述)
        (102.0, 98.0, "上游102m，下游98m"),
        (105.0, 98.0, "上游105m，下游98m"),
        (110.0, 98.0, "上游110m，下游98m"),
        (105.0, 104.0, "上游105m，下游104m（淹没）"),
    ]

    print("自由溢流堰 - 过流量计算:")
    print("-" * 80)
    print(f"{'上游水位(m)':<15} {'下游水位(m)':<15} {'水头(m)':<12} {'流量(m³/s)':<15} {'流态':<20}")
    print("-" * 80)

    for h_up, h_down, description in test_water_levels:
        H = h_up - spillway_free.crest_elevation
        Q, flow_type = spillway_free.calculate_discharge(h_up, h_down)
        print(f"{h_up:<15.1f} {h_down:<15.1f} {H:<12.1f} {Q:<15.2f} {flow_type:<20}")
        print(f"  → {description}")

    print()
    print("闸控溢洪道（开度3m）- 过流量计算:")
    print("-" * 80)
    print(f"{'上游水位(m)':<15} {'下游水位(m)':<15} {'流量(m³/s)':<15} {'流态':<25}")
    print("-" * 80)

    for h_up, h_down, description in test_water_levels:
        Q, flow_type = spillway_gated.calculate_discharge(h_up, h_down)
        print(f"{h_up:<15.1f} {h_down:<15.1f} {Q:<15.2f} {flow_type:<25}")
        print(f"  → {description}")

    print()
    print("=" * 80)
    print("时变闸门开度测试:")
    print("-" * 80)
    print(f"{'时间(s)':<12} {'开度(m)':<12} {'流量(m³/s)':<15} {'流态':<25}")
    print("-" * 80)

    h_up_test = 105.0
    h_down_test = 98.0

    for t in [0, 100, 200, 300, 500, 800]:
        spillway_time_varying.update_time(t)
        e = spillway_time_varying.get_gate_opening(t)
        Q, flow_type = spillway_time_varying.calculate_discharge(h_up_test, h_down_test, t)
        print(f"{t:<12.0f} {e:<12.2f} {Q:<15.2f} {flow_type:<25}")

    print()
    print("=" * 80)
    print("导数验证（自由溢流）:")
    print("-" * 80)

    h_up_test = 105.0
    h_down_test = 98.0

    Q0, _ = spillway_free.calculate_discharge(h_up_test, h_down_test)
    dQ_dh_up_analytical, dQ_dh_down_analytical = spillway_free.calculate_discharge_derivatives(h_up_test, h_down_test)

    # 数值导数
    eps = 1e-6
    Q_up, _ = spillway_free.calculate_discharge(h_up_test + eps, h_down_test)

    dQ_dh_up_numerical = (Q_up - Q0) / eps

    print(f"测试点: h_up={h_up_test}m, h_down={h_down_test}m")
    print(f"流量: Q={Q0:.2f} m³/s")
    print()
    print(f"∂Q/∂h_up:")
    print(f"  解析导数: {dQ_dh_up_analytical:.4f}")
    print(f"  数值导数: {dQ_dh_up_numerical:.4f}")
    print(f"  相对误差: {abs(dQ_dh_up_analytical - dQ_dh_up_numerical)/abs(dQ_dh_up_numerical)*100:.4f}%")

    print()
    print("=" * 80)
    print("测试完成！")
    print("=" * 80)


if __name__ == "__main__":
    test_spillway()
