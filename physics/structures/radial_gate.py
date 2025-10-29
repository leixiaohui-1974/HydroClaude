#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
弧形闸门 (Radial Gate / Tainter Gate)

弧形闸门是大型水库、船闸常用的泄流建筑物。

相比平板闸门的优点：
1. 水压合力通过铰链，启闭力小
2. 开度灵活调节（0-100%）
3. 泄流能力强
4. 结构稳定性好

流量计算：
1. 自由出流（下游水深较低）：
   Q = Cd * b * a * sqrt(2*g*H1)

2. 淹没出流（下游水深较高）：
   Q = Cd * b * a * sqrt(2*g*(H1-H2))

其中：
- b: 闸门宽度 (m)
- a: 闸门开度（垂直开启高度）(m)
- H1: 上游水头（相对堰顶）(m)
- H2: 下游水头（相对堰顶）(m)
- Cd: 流量系数（0.6-0.8，取决于开度和结构）

流量系数经验公式：
- 自由出流：Cd = 0.65 - 0.75 （开度较大时取上限）
- 淹没出流：Cd = 0.60 - 0.70

淹没判别：
- 淹没度 S = H2 / H1
- S < 0.67: 自由出流
- S >= 0.67: 淹没出流

参考标准：
- USACE EM 1110-2-1603 "Hydraulic Design of Spillways"
- USBR "Design of Small Dams"
- Chow (1959) "Open-Channel Hydraulics"

作者：HydroClaude Team
日期：2025-10-28
"""

import numpy as np
from typing import Optional, Tuple
import sys
import os

sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))


class RadialGate:
    """
    弧形闸门

    模拟弧形闸门的过流计算
    """

    def __init__(self,
                 width: float,
                 crest_elevation: float,
                 radius: float,
                 design_head: float,
                 max_opening: float = None,
                 g: float = 9.81):
        """
        初始化弧形闸门

        Args:
            width: 闸门宽度 (m)
            crest_elevation: 堰顶高程 (m)
            radius: 弧形半径 (m)
            design_head: 设计水头 (m)
            max_opening: 最大开度 (m)，默认为半径
            g: 重力加速度 (m/s²)
        """
        self.width = width
        self.crest_elevation = crest_elevation
        self.radius = radius
        self.design_head = design_head
        self.max_opening = max_opening if max_opening is not None else radius
        self.g = g

        # 预计算常数
        self.sqrt_2g = np.sqrt(2.0 * g)

    def compute_discharge_coefficient(self,
                                      opening: float,
                                      H_upstream: float,
                                      is_submerged: bool = False) -> float:
        """
        计算流量系数

        经验公式：
        - 自由出流：Cd = Cd_base + k * (a/H)
        - 淹没出流：Cd = Cd_base * (1 - k_sub * S)

        Args:
            opening: 闸门开度 (m)
            H_upstream: 上游水头 (m)
            is_submerged: 是否淹没

        Returns:
            流量系数 Cd
        """
        if not is_submerged:
            # 自由出流
            # 基础流量系数
            Cd_base = 0.65

            # 开度修正（开度越大，流量系数越大）
            if H_upstream > 0:
                opening_ratio = opening / H_upstream
                # 限制在合理范围
                opening_ratio = min(opening_ratio, 1.0)
                k = 0.10  # 修正系数
                Cd = Cd_base + k * opening_ratio
            else:
                Cd = Cd_base

            # 限制范围
            Cd = np.clip(Cd, 0.60, 0.75)

        else:
            # 淹没出流
            Cd_base = 0.60
            # 淹没会降低流量系数
            Cd = Cd_base

        return Cd

    def check_submergence(self,
                         h_upstream: float,
                         h_downstream: float) -> Tuple[bool, float]:
        """
        检查淹没状态

        判据：淹没度 S = H2 / H1

        Args:
            h_upstream: 上游水深（绝对高程）(m)
            h_downstream: 下游水深（绝对高程）(m)

        Returns:
            (is_submerged, submergence_ratio)
            - is_submerged: 是否淹没
            - submergence_ratio: 淹没度 S
        """
        # 相对堰顶的水头
        H1 = max(0, h_upstream - self.crest_elevation)
        H2 = max(0, h_downstream - self.crest_elevation)

        if H1 <= 0:
            return False, 0.0

        S = H2 / H1

        # 淹没判据
        S_critical = 0.67  # 临界淹没度
        is_submerged = (S >= S_critical)

        return is_submerged, S

    def compute_discharge(self,
                         h_upstream: float,
                         h_downstream: float,
                         opening: float,
                         opening_type: str = 'absolute') -> Tuple[float, dict]:
        """
        计算过流量

        Args:
            h_upstream: 上游水深（绝对高程）(m)
            h_downstream: 下游水深（绝对高程）(m)
            opening: 闸门开度
                     - opening_type='absolute': 开度为绝对高度 (m)
                     - opening_type='percent': 开度为百分比 (0-100)
            opening_type: 开度类型 ('absolute' 或 'percent')

        Returns:
            (Q, info)
            - Q: 流量 (m³/s)
            - info: 详细信息字典
        """
        # 转换开度
        if opening_type == 'percent':
            opening_abs = opening / 100.0 * self.max_opening
        else:
            opening_abs = opening

        # 限制开度范围
        opening_abs = np.clip(opening_abs, 0, self.max_opening)

        # 相对堰顶的水头
        H1 = max(0, h_upstream - self.crest_elevation)
        H2 = max(0, h_downstream - self.crest_elevation)

        # 检查是否有水流
        if H1 <= 0 or opening_abs <= 0:
            return 0.0, {
                'flow_type': 'no_flow',
                'H1': H1,
                'H2': H2,
                'opening': opening_abs,
                'Cd': 0,
                'is_submerged': False,
                'submergence_ratio': 0
            }

        # 检查淹没
        is_submerged, S = self.check_submergence(h_upstream, h_downstream)

        # 计算流量系数
        Cd = self.compute_discharge_coefficient(opening_abs, H1, is_submerged)

        # 计算流量
        if not is_submerged:
            # 自由出流
            Q = Cd * self.width * opening_abs * self.sqrt_2g * np.sqrt(H1)
            flow_type = 'free_flow'

        else:
            # 淹没出流
            dH = H1 - H2
            if dH <= 0:
                # 无水头差，无流量
                Q = 0.0
                flow_type = 'no_head_diff'
            else:
                Q = Cd * self.width * opening_abs * self.sqrt_2g * np.sqrt(dH)
                flow_type = 'submerged_flow'

        # 返回详细信息
        info = {
            'flow_type': flow_type,
            'H1': H1,
            'H2': H2,
            'dH': H1 - H2,
            'opening': opening_abs,
            'Cd': Cd,
            'is_submerged': is_submerged,
            'submergence_ratio': S
        }

        return Q, info

    def compute_opening_for_target_flow(self,
                                       h_upstream: float,
                                       h_downstream: float,
                                       Q_target: float,
                                       tol: float = 0.01,
                                       max_iter: int = 50) -> Tuple[float, dict]:
        """
        反算闸门开度（给定目标流量）

        使用二分法求解

        Args:
            h_upstream: 上游水深 (m)
            h_downstream: 下游水深 (m)
            Q_target: 目标流量 (m³/s)
            tol: 容差
            max_iter: 最大迭代次数

        Returns:
            (opening, info)
            - opening: 所需开度 (m)
            - info: 详细信息
        """
        # 二分法求解
        a_min, a_max = 0.0, self.max_opening

        for i in range(max_iter):
            a_mid = (a_min + a_max) / 2

            Q, info = self.compute_discharge(h_upstream, h_downstream, a_mid, 'absolute')

            error = Q - Q_target

            if abs(error) < tol:
                info['converged'] = True
                info['iterations'] = i + 1
                return a_mid, info

            if error > 0:
                # 流量过大，减小开度
                a_max = a_mid
            else:
                # 流量过小，增大开度
                a_min = a_mid

        # 未收敛
        info['converged'] = False
        info['iterations'] = max_iter
        return a_mid, info

    def __repr__(self) -> str:
        return (f"RadialGate(width={self.width:.2f}m, "
                f"radius={self.radius:.2f}m, "
                f"crest_elev={self.crest_elevation:.2f}m, "
                f"max_opening={self.max_opening:.2f}m)")


if __name__ == "__main__":
    """测试弧形闸门模块"""

    print("=" * 70)
    print("弧形闸门模块测试")
    print("=" * 70)

    # 创建弧形闸门
    gate = RadialGate(
        width=15.0,             # 闸门宽度15m
        crest_elevation=100.0,  # 堰顶高程100m
        radius=8.0,             # 弧形半径8m
        design_head=10.0        # 设计水头10m
    )

    print(f"\n{gate}")

    # 测试案例1：自由出流
    print("\n[测试1] 自由出流")
    print("-" * 70)

    h_up = 110.0    # 上游水深110m（堰顶以上10m）
    h_down = 101.0  # 下游水深101m（堰顶以上1m，自由出流）
    opening = 5.0   # 开度5m

    Q, info = gate.compute_discharge(h_up, h_down, opening, 'absolute')

    print(f"上游水深: {h_up:.2f}m")
    print(f"下游水深: {h_down:.2f}m")
    print(f"开度: {opening:.2f}m")
    print(f"\n结果:")
    print(f"  流量 Q = {Q:.2f} m³/s")
    print(f"  流态: {info['flow_type']}")
    print(f"  流量系数 Cd = {info['Cd']:.3f}")
    print(f"  上游水头 H1 = {info['H1']:.2f}m")
    print(f"  淹没状态: {'淹没' if info['is_submerged'] else '自由'}")
    print(f"  淹没度 S = {info['submergence_ratio']:.3f}")

    # 测试案例2：淹没出流
    print("\n[测试2] 淹没出流")
    print("-" * 70)

    h_up = 110.0    # 上游水深110m
    h_down = 108.0  # 下游水深108m（淹没）
    opening = 5.0

    Q, info = gate.compute_discharge(h_up, h_down, opening, 'absolute')

    print(f"上游水深: {h_up:.2f}m")
    print(f"下游水深: {h_down:.2f}m")
    print(f"开度: {opening:.2f}m")
    print(f"\n结果:")
    print(f"  流量 Q = {Q:.2f} m³/s")
    print(f"  流态: {info['flow_type']}")
    print(f"  流量系数 Cd = {info['Cd']:.3f}")
    print(f"  水头差 dH = {info['dH']:.2f}m")
    print(f"  淹没状态: {'淹没' if info['is_submerged'] else '自由'}")
    print(f"  淹没度 S = {info['submergence_ratio']:.3f}")

    # 测试案例3：不同开度下的流量
    print("\n[测试3] 开度特性曲线")
    print("-" * 70)

    h_up = 110.0
    h_down = 101.0
    openings = [1.0, 2.0, 3.0, 4.0, 5.0, 6.0, 7.0, 8.0]

    print(f"{'开度(m)':>10} {'流量(m³/s)':>15} {'Cd':>10}")
    print("-" * 40)

    for a in openings:
        Q, info = gate.compute_discharge(h_up, h_down, a, 'absolute')
        print(f"{a:10.2f} {Q:15.2f} {info['Cd']:10.3f}")

    # 测试案例4：反算开度
    print("\n[测试4] 反算开度")
    print("-" * 70)

    Q_target = 500.0  # 目标流量500 m³/s
    h_up = 110.0
    h_down = 101.0

    opening_needed, info = gate.compute_opening_for_target_flow(h_up, h_down, Q_target)

    print(f"目标流量: {Q_target:.2f} m³/s")
    print(f"上游水深: {h_up:.2f}m")
    print(f"下游水深: {h_down:.2f}m")
    print(f"\n结果:")
    print(f"  所需开度: {opening_needed:.3f}m")
    print(f"  收敛状态: {'成功' if info['converged'] else '失败'}")
    print(f"  迭代次数: {info['iterations']}")
    print(f"  实际流量: {info.get('Q', 0):.2f} m³/s")

    # 验证
    Q_check, _ = gate.compute_discharge(h_up, h_down, opening_needed, 'absolute')
    error = abs(Q_check - Q_target) / Q_target * 100
    print(f"  验证流量: {Q_check:.2f} m³/s")
    print(f"  误差: {error:.3f}%")

    print("\n" + "=" * 70)
    print("弧形闸门模块测试完成!")
    print("=" * 70)
