#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
侧堰 (Side Weir)

侧堰是位于渠道侧壁的溢流建筑物，水流沿堰长方向侧向溢出。
常用于分洪、排涝、溢流等场景。

侧堰流量特点：
1. 水流非正交越堰（斜向流动）
2. 沿程流量连续变化
3. 流量系数受侧向流动影响

De Marchi公式（经典侧堰公式）：
    Q = C * L * H^(3/2) * sqrt(2g) * φ

其中：
- C: 流量系数 (考虑侧向流动的修正，约 0.3-0.5)
- L: 堰长 (m)
- H: 堰顶以上平均水头 (m)
- φ: 侧向流动修正系数
- g: 重力加速度 (m/s²)

侧向流动修正：
当弗劳德数Fr较小时，φ ≈ 1.0
当Fr增大时，φ减小（侧向溢流能力下降）

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


class SideWeir(HydraulicStructure):
    """
    侧堰类

    模拟侧堰的侧向溢流过程。
    考虑主渠道流速对侧向溢流的影响。
    """

    def __init__(self, position: float, length: float, crest_elevation: float,
                 channel_width: float,
                 discharge_coefficient: float = 0.4,
                 g: float = 9.81):
        """
        初始化侧堰

        Args:
            position: 侧堰起点位置 (m)
            length: 侧堰长度 (m)
            crest_elevation: 侧堰堰顶高程 (m)
            channel_width: 主渠道宽度 (m)
            discharge_coefficient: 侧堰流量系数 (约 0.3-0.5，考虑侧向流动修正)
            g: 重力加速度 (m/s²)
        """
        super().__init__(position, length, g)
        self.length = length
        self.crest_elevation = crest_elevation
        self.channel_width = channel_width
        self.C = discharge_coefficient

        # 预计算常数
        self.sqrt_2g = np.sqrt(2.0 * self.g)
        self.C_sqrt_2g = self.C * self.sqrt_2g

    def calculate_froude_correction(self, Fr: float) -> float:
        """
        计算弗劳德数修正系数

        当Fr较小时（亚临界流），修正系数接近1.0
        当Fr增大时，侧向溢流能力下降

        Args:
            Fr: 弗劳德数 (无量纲)

        Returns:
            修正系数 φ (0-1)
        """
        # 经验公式：φ = 1 / sqrt(1 + Fr²)
        # 或更简单的：φ = exp(-k * Fr²)，k为经验系数
        k = 0.5  # 经验系数
        phi = np.exp(-k * Fr ** 2)
        return phi

    def calculate_discharge(self, h_upstream: float, h_downstream: float,
                           t: Optional[float] = None,
                           Q_channel: Optional[float] = None) -> tuple:
        """
        计算侧堰过流量

        Args:
            h_upstream: 主渠道水深 (m)
            h_downstream: 分水渠道水深 (m)（用于判断淹没，简化可忽略）
            t: 当前时间 (s)，用于时变参数（本类未使用）
            Q_channel: 主渠道流量 (m³/s)，用于计算弗劳德数修正

        Returns:
            (discharge, flow_type):
                - discharge: 侧堰溢流量 (m³/s)
                - flow_type: 流态类型
        """
        # 计算堰顶以上水头
        H = h_upstream - self.crest_elevation

        # 如果主渠道水位低于侧堰堰顶，无溢流
        if H <= 0:
            return 0.0, 'no_flow'

        # 计算弗劳德数修正系数
        phi = 1.0  # 默认无修正

        if Q_channel is not None and Q_channel > 0:
            # 计算主渠道流速和弗劳德数
            A_channel = self.channel_width * h_upstream
            V_channel = Q_channel / A_channel if A_channel > 0 else 0.0
            Fr = V_channel / np.sqrt(self.g * h_upstream) if h_upstream > 0 else 0.0

            # 计算修正系数
            phi = self.calculate_froude_correction(Fr)

        # 侧堰流量公式：Q = C * L * H^(3/2) * sqrt(2g) * φ
        Q = self.C_sqrt_2g * self.length * (H ** 1.5) * phi

        # 判断流态（简化：只判断是否溢流）
        if phi < 0.7:
            flow_type = 'oblique_flow'  # 斜向流动（Fr较大）
        else:
            flow_type = 'normal_flow'   # 近似正向流动

        return Q, flow_type

    def calculate_discharge_derivatives(self, h_upstream: float, h_downstream: float,
                                        t: Optional[float] = None,
                                        Q_channel: Optional[float] = None) -> tuple:
        """
        计算过流量对主渠道水深的解析导数

        用于牛顿求解器的Jacobian矩阵构建

        注意：这里简化处理，假设Q_channel不变，只对h_upstream求导

        Args:
            h_upstream: 主渠道水深 (m)
            h_downstream: 分水渠道水深 (m)
            t: 当前时间 (s)，用于时变参数
            Q_channel: 主渠道流量 (m³/s)

        Returns:
            (dQ_dh_up, dQ_dh_down):
                - dQ_dh_up: ∂Q/∂h_upstream
                - dQ_dh_down: ∂Q/∂h_downstream (通常为0或很小)
        """
        # 计算堰顶以上水头
        H = h_upstream - self.crest_elevation

        # 如果主渠道水位低于侧堰堰顶，导数为0
        if H <= 1e-6:
            return 0.0, 0.0

        # 简化处理：假设φ为常数（对h的依赖性较弱）
        # 实际上φ是Fr的函数，Fr又是h和Q的函数，完整导数会更复杂

        phi = 1.0
        if Q_channel is not None and Q_channel > 0:
            A_channel = self.channel_width * h_upstream
            V_channel = Q_channel / A_channel if A_channel > 0 else 0.0
            Fr = V_channel / np.sqrt(self.g * h_upstream) if h_upstream > 0 else 0.0
            phi = self.calculate_froude_correction(Fr)

        # Q = C * L * sqrt(2g) * H^(3/2) * φ
        # dQ/dH = C * L * sqrt(2g) * (3/2) * H^(1/2) * φ  (忽略φ对H的依赖)
        # dQ/dh_up = dQ/dH * dH/dh_up = (3/2) * C * L * sqrt(2g*H) * φ

        dQ_dh_up = 1.5 * self.C_sqrt_2g * self.length * np.sqrt(H) * phi

        # 侧堰通常为自由溢流，不受分水渠道水位影响（简化）
        dQ_dh_down = 0.0

        return dQ_dh_up, dQ_dh_down

    def __repr__(self) -> str:
        """对象的字符串表示"""
        return (f"SideWeir(pos={self.position}m, length={self.length}m, "
                f"crest_elev={self.crest_elevation}m, C={self.C:.3f})")


def test_side_weir():
    """测试侧堰类"""
    print("=" * 80)
    print("侧堰 (Side Weir) 测试")
    print("=" * 80)

    # 创建侧堰
    side_weir = SideWeir(
        position=500.0,       # 侧堰起点位置 500m
        length=20.0,          # 侧堰长度 20m
        crest_elevation=2.0,  # 堰顶高程 2m
        channel_width=10.0,   # 主渠道宽度 10m
        discharge_coefficient=0.4
    )

    print(f"\n侧堰参数: {side_weir}")
    print()

    # 测试1：不同水位下的溢流量（不考虑主渠道流速）
    print("测试1：不同水位下的侧堰溢流量（静水）")
    print("-" * 80)
    print(f"{'主渠道水深(m)':<18} {'水头(m)':<12} {'侧堰流量(m³/s)':<18} {'流态':<15}")
    print("-" * 80)

    for h in [2.0, 2.2, 2.5, 3.0, 3.5]:
        H = h - side_weir.crest_elevation
        Q, flow_type = side_weir.calculate_discharge(h, 1.5, Q_channel=None)
        print(f"{h:<18.2f} {H:<12.2f} {Q:<18.3f} {flow_type:<15}")

    print()
    print("测试2：主渠道流速对侧堰溢流的影响")
    print("-" * 80)
    print("当主渠道流速增大（Fr增大）时，侧向溢流能力下降")
    print()
    print(f"{'主渠道流量(m³/s)':<20} {'流速(m/s)':<15} {'Fr':<12} {'修正系数φ':<15} {'侧堰流量(m³/s)':<18}")
    print("-" * 80)

    h_test = 3.0  # 主渠道水深
    A_channel = side_weir.channel_width * h_test

    Q_channel_values = [0, 20, 50, 100, 150, 200]

    for Q_ch in Q_channel_values:
        V = Q_ch / A_channel if Q_ch > 0 else 0.0
        Fr = V / np.sqrt(side_weir.g * h_test) if Q_ch > 0 else 0.0
        phi = side_weir.calculate_froude_correction(Fr)
        Q_side, flow_type = side_weir.calculate_discharge(h_test, 1.5, Q_channel=Q_ch)

        print(f"{Q_ch:<20.1f} {V:<15.3f} {Fr:<12.3f} {phi:<15.3f} {Q_side:<18.3f}")

    print()
    print("观察：随着主渠道流量（流速）增大，侧堰溢流量逐渐减小")
    print()

    print("=" * 80)
    print("导数验证:")
    print("-" * 80)

    h_up_test = 3.0
    h_down_test = 1.5
    Q_channel_test = 50.0

    Q0, _ = side_weir.calculate_discharge(h_up_test, h_down_test, Q_channel=Q_channel_test)
    dQ_dh_up_analytical, dQ_dh_down_analytical = side_weir.calculate_discharge_derivatives(
        h_up_test, h_down_test, Q_channel=Q_channel_test
    )

    # 数值导数
    eps = 1e-6
    Q_up, _ = side_weir.calculate_discharge(h_up_test + eps, h_down_test, Q_channel=Q_channel_test)

    dQ_dh_up_numerical = (Q_up - Q0) / eps

    print(f"测试点: h_main={h_up_test}m, Q_main={Q_channel_test}m³/s")
    print(f"侧堰流量: Q={Q0:.3f} m³/s")
    print()
    print(f"∂Q/∂h_main:")
    print(f"  解析导数: {dQ_dh_up_analytical:.6f}")
    print(f"  数值导数: {dQ_dh_up_numerical:.6f}")

    # 注意：由于φ也是h的函数（通过Fr），解析导数这里简化了
    # 所以可能与数值导数有偏差，这是正常的
    if abs(dQ_dh_up_analytical) > 1e-6:
        rel_error = abs(dQ_dh_up_analytical - dQ_dh_up_numerical) / abs(dQ_dh_up_numerical) * 100
        print(f"  相对误差: {rel_error:.2f}% (注：解析导数简化了φ的依赖性)")
    print()

    print("=" * 80)
    print("侧堰应用场景:")
    print("-" * 80)
    print("1. 防洪分洪：将超过渠道设计流量的洪水侧向分出")
    print("2. 灌溉分水：沿渠道侧向分水到支渠")
    print("3. 城市排水：道路侧向排水到排水渠")
    print("4. 水位控制：通过侧堰自动溢流控制上游水位")
    print()

    print("=" * 80)
    print("测试完成！")
    print("=" * 80)


if __name__ == "__main__":
    test_side_weir()
