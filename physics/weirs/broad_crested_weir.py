#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
宽顶堰 (Broad-Crested Weir)

宽顶堰是一种堰顶长度较长的溢流建筑物，水流在堰顶形成近似均匀流。
适用于中小型溢洪道、分水建筑物等。

流量计算公式：
- 自由溢流：Q = C * B * H^(3/2) * sqrt(2g)
- 淹没溢流：Q = C * B * H_up^(3/2) * sqrt(2g) * σ

其中：
- C: 流量系数 (通常 0.3-0.5，标准值约 0.385)
- B: 堰宽 (m)
- H: 堰顶以上水头 (m)
- σ: 淹没系数 (取决于淹没度 H_down/H_up)
- g: 重力加速度 (m/s²)

淹没判别：当 H_down/H_up > 0.67 时视为淹没流

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


class BroadCrestedWeir(HydraulicStructure):
    """
    宽顶堰类

    用于计算宽顶堰的过流量，支持自由流和淹没流两种流态。
    提供解析导数用于牛顿迭代求解器。
    """

    def __init__(self, position: float, width: float, crest_elevation: float,
                 discharge_coefficient: float = 0.385, g: float = 9.81,
                 submergence_threshold: float = 0.67):
        """
        初始化宽顶堰

        Args:
            position: 堰位置 (m)
            width: 堰宽 (m)
            crest_elevation: 堰顶高程 (m)
            discharge_coefficient: 流量系数 C (无量纲，典型值 0.385)
            g: 重力加速度 (m/s²)
            submergence_threshold: 淹没判别阈值 (H_down/H_up，典型值 0.67)
        """
        super().__init__(position, width, g)
        self.crest_elevation = crest_elevation
        self.C = discharge_coefficient
        self.submergence_threshold = submergence_threshold

        # 预计算常数
        self.C_sqrt_2g = self.C * np.sqrt(2.0 * self.g)

    def calculate_discharge(self, h_upstream: float, h_downstream: float,
                           t: Optional[float] = None) -> tuple:
        """
        计算过流量

        Args:
            h_upstream: 上游水深 (m)
            h_downstream: 下游水深 (m)
            t: 当前时间 (s)，用于时变参数（本类未使用）

        Returns:
            (discharge, flow_type):
                - discharge: 流量 (m³/s)
                - flow_type: 流态类型 ('free' 或 'submerged')
        """
        # 计算堰顶以上水头
        H_up = h_upstream - self.crest_elevation
        H_down = h_downstream - self.crest_elevation

        # 如果上游水位低于堰顶，无流量
        if H_up <= 0:
            return 0.0, 'no_flow'

        # 判断是否淹没
        if H_down <= 0:
            # 下游水位低于堰顶，必然自由流
            flow_type = 'free'
            submergence_ratio = 0.0
        else:
            submergence_ratio = H_down / H_up
            flow_type = 'submerged' if submergence_ratio > self.submergence_threshold else 'free'

        # 计算流量
        if flow_type == 'free':
            # 自由溢流：Q = C * B * H^(3/2) * sqrt(2g)
            Q = self.C_sqrt_2g * self.width * (H_up ** 1.5)
        else:
            # 淹没溢流：Q = C * B * H_up^(3/2) * sqrt(2g) * σ
            # 淹没系数：σ = (1 - (H_down/H_up)^(3/2))^0.385
            # 简化形式：σ ≈ 1 - 0.385 * (H_down/H_up)^(3/2) （线性近似）
            # 使用更精确的Villemonte公式：
            # σ = sqrt(1 - (H_down/H_up)^1.5)
            sigma = np.sqrt(1.0 - submergence_ratio ** 1.5)
            Q = self.C_sqrt_2g * self.width * (H_up ** 1.5) * sigma

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
                - dQ_dh_down: ∂Q/∂h_downstream
        """
        # 计算堰顶以上水头
        H_up = h_upstream - self.crest_elevation
        H_down = h_downstream - self.crest_elevation

        # 如果上游水位低于堰顶，导数为0
        if H_up <= 1e-6:
            return 0.0, 0.0

        # 判断流态
        if H_down <= 0:
            flow_type = 'free'
            submergence_ratio = 0.0
        else:
            submergence_ratio = H_down / H_up
            flow_type = 'submerged' if submergence_ratio > self.submergence_threshold else 'free'

        # 计算导数
        if flow_type == 'free':
            # 自由流：Q = C * B * sqrt(2g) * H_up^(3/2)
            # dQ/dh_up = C * B * sqrt(2g) * (3/2) * H_up^(1/2)
            dQ_dh_up = 1.5 * self.C_sqrt_2g * self.width * np.sqrt(H_up)
            dQ_dh_down = 0.0  # 自由流不受下游影响
        else:
            # 淹没流：Q = C * B * sqrt(2g) * H_up^(3/2) * sqrt(1 - (H_down/H_up)^1.5)
            # 令 r = H_down/H_up, σ = sqrt(1 - r^1.5)
            # Q = C * B * sqrt(2g) * H_up^(3/2) * σ

            r = submergence_ratio
            r_15 = r ** 1.5
            sigma = np.sqrt(1.0 - r_15)

            if sigma < 1e-6:
                # 完全淹没，流量趋于0，导数也趋于0
                return 0.0, 0.0

            # dQ/dh_up:
            # Q = C * B * sqrt(2g) * H_up^1.5 * sqrt(1 - r^1.5)
            # 其中 r = H_down/H_up，所以 r 也是 h_up 的函数
            # 用链式法则：
            # dQ/dh_up = C*B*sqrt(2g) * [1.5*H_up^0.5 * σ + H_up^1.5 * dσ/dh_up]
            # dσ/dr = -0.75 * r^0.5 / σ
            # dr/dh_up = -H_down/H_up^2
            # dσ/dh_up = dσ/dr * dr/dh_up = -0.75*r^0.5/σ * (-H_down/H_up^2) = 0.75*r^0.5*H_down/(σ*H_up^2)

            dsigma_dr = -0.75 * np.sqrt(r) / sigma if sigma > 1e-6 else 0.0
            dr_dh_up = -H_down / (H_up ** 2)
            dsigma_dh_up = dsigma_dr * dr_dh_up

            dQ_dh_up = self.C_sqrt_2g * self.width * (
                1.5 * np.sqrt(H_up) * sigma + (H_up ** 1.5) * dsigma_dh_up
            )

            # dQ/dh_down:
            # dr/dh_down = 1/H_up
            # dσ/dh_down = dσ/dr * dr/dh_down = -0.75*r^0.5/(σ*H_up)
            dr_dh_down = 1.0 / H_up
            dsigma_dh_down = dsigma_dr * dr_dh_down

            dQ_dh_down = self.C_sqrt_2g * self.width * (H_up ** 1.5) * dsigma_dh_down

        return dQ_dh_up, dQ_dh_down

    def __repr__(self) -> str:
        """对象的字符串表示"""
        return (f"BroadCrestedWeir(pos={self.position}m, width={self.width}m, "
                f"crest_elev={self.crest_elevation}m, C={self.C:.3f})")


def test_broad_crested_weir():
    """测试宽顶堰类"""
    print("=" * 80)
    print("宽顶堰 (Broad-Crested Weir) 测试")
    print("=" * 80)

    # 创建宽顶堰
    weir = BroadCrestedWeir(
        position=500.0,      # 位置 500m
        width=10.0,          # 堰宽 10m
        crest_elevation=2.0, # 堰顶高程 2m
        discharge_coefficient=0.385
    )

    print(f"\n堰参数: {weir}")
    print()

    # 测试不同水位情况
    test_cases = [
        # (h_up, h_down, 描述)
        (2.5, 1.5, "上游水位 2.5m，下游水位 1.5m（自由流）"),
        (3.0, 2.0, "上游水位 3.0m，下游水位 2.0m（可能淹没）"),
        (3.5, 2.8, "上游水位 3.5m，下游水位 2.8m（淹没流）"),
        (1.8, 1.5, "上游水位低于堰顶"),
        (2.8, 2.7, "上下游水位相近（强淹没）"),
    ]

    print("过流量计算测试:")
    print("-" * 80)
    print(f"{'上游水深(m)':<15} {'下游水深(m)':<15} {'流量(m³/s)':<15} {'流态':<15}")
    print("-" * 80)

    for h_up, h_down, description in test_cases:
        Q, flow_type = weir.calculate_discharge(h_up, h_down)
        print(f"{h_up:<15.2f} {h_down:<15.2f} {Q:<15.3f} {flow_type:<15}")
        print(f"  → {description}")

    print()
    print("=" * 80)
    print("导数验证（解析 vs 数值）:")
    print("-" * 80)

    # 选择一个测试点
    h_up_test = 3.0
    h_down_test = 2.0

    Q0, _ = weir.calculate_discharge(h_up_test, h_down_test)
    dQ_dh_up_analytical, dQ_dh_down_analytical = weir.calculate_discharge_derivatives(h_up_test, h_down_test)

    # 数值导数
    eps = 1e-6
    Q_up, _ = weir.calculate_discharge(h_up_test + eps, h_down_test)
    Q_down, _ = weir.calculate_discharge(h_up_test, h_down_test + eps)

    dQ_dh_up_numerical = (Q_up - Q0) / eps
    dQ_dh_down_numerical = (Q_down - Q0) / eps

    print(f"测试点: h_up={h_up_test}m, h_down={h_down_test}m")
    print(f"流量: Q={Q0:.3f} m³/s")
    print()
    print(f"∂Q/∂h_up:")
    print(f"  解析导数: {dQ_dh_up_analytical:.6f}")
    print(f"  数值导数: {dQ_dh_up_numerical:.6f}")
    print(f"  相对误差: {abs(dQ_dh_up_analytical - dQ_dh_up_numerical)/abs(dQ_dh_up_numerical)*100:.4f}%")
    print()
    print(f"∂Q/∂h_down:")
    print(f"  解析导数: {dQ_dh_down_analytical:.6f}")
    print(f"  数值导数: {dQ_dh_down_numerical:.6f}")
    print(f"  相对误差: {abs(dQ_dh_down_analytical - dQ_dh_down_numerical)/abs(dQ_dh_down_numerical)*100:.4f}%")

    print()
    print("=" * 80)
    print("测试完成！")
    print("=" * 80)


if __name__ == "__main__":
    test_broad_crested_weir()
