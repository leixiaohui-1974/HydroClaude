#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
充气坝 (Inflatable Dam / Rubber Dam)

充气坝是现代化的可调节挡水建筑物，由橡胶或合成材料制成。

优点：
1. 可完全倒伏 - 洪水期无阻水，泥沙自行冲刷
2. 高度灵活调节 - 充气/放气控制坝高
3. 造价低 - 相比钢闸门便宜30-50%
4. 维护简单 - 无机械传动部件
5. 适应性强 - 可适应不同河床

应用场景：
- 城市景观河道（橡胶坝公园）
- 灌溉渠道水位调节
- 小型水电站
- 防洪临时挡水

流量计算：
1. 充气状态（坝体挡水）：
   类似宽顶堰公式，考虑坝体形状修正
   Q = Cd * b * H^(3/2) * sqrt(2g)

2. 倒伏状态（完全放气）：
   无阻水，按天然河床计算

坝体形状系数：
- 标准圆弧形：Cd = 0.42-0.48
- 流线型：Cd = 0.45-0.52

充气高度控制：
- h_dam(t): 时变坝高 (0 到 h_max)
- 充气/放气速率：通常 5-15 min

参考标准：
- 《充气坝工程技术规范》SL 227-98
- Chanson (2004) "The Hydraulics of Open Channel Flow"
- 各国橡胶坝技术手册

作者：HydroClaude Team
日期：2025-10-28
"""

import numpy as np
from typing import Optional, Tuple
import sys
import os

sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))


class InflatableDam:
    """
    充气坝

    模拟充气坝的过流计算和高度调节
    """

    def __init__(self,
                 width: float,
                 crest_elevation: float,
                 max_height: float,
                 shape_type: str = 'circular',
                 inflation_rate: float = 0.05,
                 deflation_rate: float = 0.10,
                 g: float = 9.81):
        """
        初始化充气坝

        Args:
            width: 坝宽 (m)
            crest_elevation: 坝底高程 (m)
            max_height: 最大充气高度 (m)
            shape_type: 坝体形状 ('circular': 圆弧形, 'streamlined': 流线型)
            inflation_rate: 充气速率 (m/min)，即每分钟升高高度
            deflation_rate: 放气速率 (m/min)，通常比充气快
            g: 重力加速度 (m/s²)
        """
        self.width = width
        self.crest_elevation = crest_elevation
        self.max_height = max_height
        self.shape_type = shape_type
        self.inflation_rate = inflation_rate
        self.deflation_rate = deflation_rate
        self.g = g

        # 当前坝高（充气高度）
        self.current_height = 0.0  # 初始状态：完全倒伏

        # 流量系数（取决于坝体形状）
        if shape_type == 'circular':
            self.Cd_base = 0.45  # 圆弧形
        elif shape_type == 'streamlined':
            self.Cd_base = 0.48  # 流线型（更光滑）
        else:
            self.Cd_base = 0.45

        # 预计算常数
        self.sqrt_2g = np.sqrt(2.0 * g)

    def set_height(self, height: float):
        """
        设置坝高（瞬时设定）

        Args:
            height: 目标坝高 (m)，0表示完全倒伏
        """
        self.current_height = np.clip(height, 0, self.max_height)

    def inflate(self, duration: float) -> float:
        """
        充气操作

        Args:
            duration: 充气时间 (min)

        Returns:
            充气后的坝高 (m)
        """
        # 计算充气增量
        delta_h = self.inflation_rate * duration

        # 更新坝高
        new_height = min(self.current_height + delta_h, self.max_height)
        self.current_height = new_height

        return self.current_height

    def deflate(self, duration: float) -> float:
        """
        放气操作

        Args:
            duration: 放气时间 (min)

        Returns:
            放气后的坝高 (m)
        """
        # 计算放气增量
        delta_h = self.deflation_rate * duration

        # 更新坝高
        new_height = max(self.current_height - delta_h, 0.0)
        self.current_height = new_height

        return self.current_height

    def compute_discharge_coefficient(self, H: float) -> float:
        """
        计算流量系数

        流量系数随水头变化略有调整

        Args:
            H: 堰顶水头 (m)

        Returns:
            流量系数 Cd
        """
        # 基础流量系数
        Cd = self.Cd_base

        # 水头修正（水头越大，流量系数略增）
        if self.current_height > 0 and H > 0:
            # H/P比值修正（P为坝高）
            ratio = H / self.current_height
            # 修正因子
            if ratio > 0.5:
                Cd = self.Cd_base * (1.0 + 0.05 * (ratio - 0.5))

        # 限制范围
        Cd = np.clip(Cd, 0.40, 0.55)

        return Cd

    def compute_discharge(self,
                         h_upstream: float,
                         h_downstream: float) -> Tuple[float, dict]:
        """
        计算过流量

        Args:
            h_upstream: 上游水深（绝对高程）(m)
            h_downstream: 下游水深（绝对高程）(m)

        Returns:
            (Q, info)
            - Q: 流量 (m³/s)
            - info: 详细信息字典
        """
        # 当前堰顶高程
        dam_top_elevation = self.crest_elevation + self.current_height

        # 相对堰顶的水头
        H = max(0, h_upstream - dam_top_elevation)

        # 检查是否过坝
        if H <= 0:
            # 上游水位未超过坝顶
            return 0.0, {
                'flow_type': 'no_overflow',
                'dam_height': self.current_height,
                'dam_top_elevation': dam_top_elevation,
                'H': H,
                'Cd': 0,
                'is_deflated': (self.current_height == 0)
            }

        # 检查下游是否淹没
        H_downstream = max(0, h_downstream - dam_top_elevation)
        is_submerged = (H_downstream / H) > 0.67 if H > 0 else False

        # 计算流量系数
        Cd = self.compute_discharge_coefficient(H)

        # 计算流量
        if not is_submerged:
            # 自由溢流（类似宽顶堰）
            Q = Cd * self.width * self.sqrt_2g * (H ** 1.5)
            flow_type = 'free_overflow'

        else:
            # 淹没溢流
            dH = H - H_downstream
            if dH <= 0:
                Q = 0.0
                flow_type = 'no_head_diff'
            else:
                # 淹没修正
                submergence_ratio = H_downstream / H
                Cd_submerged = Cd * (1.0 - submergence_ratio ** 1.5)
                Q = Cd_submerged * self.width * self.sqrt_2g * (H ** 1.5)
                flow_type = 'submerged_overflow'

        # 返回详细信息
        info = {
            'flow_type': flow_type,
            'dam_height': self.current_height,
            'dam_top_elevation': dam_top_elevation,
            'H': H,
            'H_downstream': H_downstream,
            'Cd': Cd,
            'is_submerged': is_submerged,
            'is_deflated': (self.current_height == 0)
        }

        return Q, info

    def compute_inflation_time(self, target_height: float) -> float:
        """
        计算达到目标坝高所需的充气时间

        Args:
            target_height: 目标坝高 (m)

        Returns:
            所需时间 (min)
        """
        target_height = np.clip(target_height, 0, self.max_height)
        delta_h = abs(target_height - self.current_height)

        if target_height > self.current_height:
            # 充气
            time_needed = delta_h / self.inflation_rate
        elif target_height < self.current_height:
            # 放气
            time_needed = delta_h / self.deflation_rate
        else:
            time_needed = 0.0

        return time_needed

    def get_status(self) -> dict:
        """
        获取充气坝当前状态

        Returns:
            状态字典
        """
        inflation_percent = (self.current_height / self.max_height * 100) if self.max_height > 0 else 0

        return {
            'current_height': self.current_height,
            'max_height': self.max_height,
            'inflation_percent': inflation_percent,
            'is_fully_inflated': (self.current_height >= self.max_height),
            'is_deflated': (self.current_height == 0),
            'dam_top_elevation': self.crest_elevation + self.current_height
        }

    def __repr__(self) -> str:
        status = self.get_status()
        return (f"InflatableDam(width={self.width:.2f}m, "
                f"current_height={self.current_height:.2f}m, "
                f"inflation={status['inflation_percent']:.1f}%)")


if __name__ == "__main__":
    """测试充气坝模块"""

    print("=" * 70)
    print("充气坝模块测试")
    print("=" * 70)

    # 创建充气坝
    dam = InflatableDam(
        width=50.0,              # 坝宽50m（景观河道）
        crest_elevation=100.0,   # 坝底高程100m
        max_height=3.0,          # 最大充气高度3m
        shape_type='circular',   # 圆弧形
        inflation_rate=0.05,     # 充气速率 5cm/min
        deflation_rate=0.10      # 放气速率 10cm/min
    )

    print(f"\n{dam}")
    print(f"初始状态: {dam.get_status()}")

    # 测试案例1：完全倒伏状态（无阻水）
    print("\n[测试1] 完全倒伏状态")
    print("-" * 70)

    h_up = 101.0
    h_down = 100.5

    Q, info = dam.compute_discharge(h_up, h_down)

    print(f"上游水深: {h_up:.2f}m")
    print(f"下游水深: {h_down:.2f}m")
    print(f"坝高: {dam.current_height:.2f}m (倒伏)")
    print(f"\n结果:")
    print(f"  流量 Q = {Q:.2f} m³/s")
    print(f"  流态: {info['flow_type']}")
    print(f"  是否倒伏: {info['is_deflated']}")

    # 测试案例2：充气到2m
    print("\n[测试2] 充气操作")
    print("-" * 70)

    # 充气30分钟
    duration = 30.0  # min
    print(f"充气 {duration:.1f} 分钟...")

    final_height = dam.inflate(duration)

    print(f"充气前: 0.00m")
    print(f"充气后: {final_height:.2f}m")
    print(f"充气率: {dam.inflation_rate:.3f} m/min")
    print(f"预期: {0 + dam.inflation_rate * duration:.2f}m")

    # 测试案例3：充气后过流
    print("\n[测试3] 充气后过流")
    print("-" * 70)

    h_up = 103.5   # 上游水深103.5m
    h_down = 101.0

    Q, info = dam.compute_discharge(h_up, h_down)

    print(f"上游水深: {h_up:.2f}m")
    print(f"下游水深: {h_down:.2f}m")
    print(f"坝顶高程: {info['dam_top_elevation']:.2f}m")
    print(f"堰顶水头 H: {info['H']:.2f}m")
    print(f"\n结果:")
    print(f"  流量 Q = {Q:.2f} m³/s")
    print(f"  流态: {info['flow_type']}")
    print(f"  流量系数 Cd = {info['Cd']:.3f}")
    print(f"  淹没状态: {'淹没' if info['is_submerged'] else '自由'}")

    # 测试案例4：不同充气高度的流量
    print("\n[测试4] 充气高度特性曲线")
    print("-" * 70)

    h_up = 104.0
    h_down = 101.0

    print(f"上游水深: {h_up:.2f}m")
    print(f"下游水深: {h_down:.2f}m\n")
    print(f"{'坝高(m)':>10} {'堰顶水头(m)':>15} {'流量(m³/s)':>15} {'Cd':>10}")
    print("-" * 55)

    for h_dam in [0.0, 0.5, 1.0, 1.5, 2.0, 2.5, 3.0]:
        dam.set_height(h_dam)
        Q, info = dam.compute_discharge(h_up, h_down)
        H = info['H']
        Cd = info['Cd']

        print(f"{h_dam:10.2f} {H:15.2f} {Q:15.2f} {Cd:10.3f}")

    # 测试案例5：放气操作
    print("\n[测试5] 放气操作")
    print("-" * 70)

    # 先充气到最大
    dam.set_height(3.0)
    print(f"初始坝高: {dam.current_height:.2f}m")

    # 放气20分钟
    duration = 20.0
    print(f"放气 {duration:.1f} 分钟...")

    final_height = dam.deflate(duration)

    print(f"放气后: {final_height:.2f}m")
    print(f"放气率: {dam.deflation_rate:.3f} m/min")
    print(f"预期: {3.0 - dam.deflation_rate * duration:.2f}m")

    # 测试案例6：计算所需时间
    print("\n[测试6] 计算充气/放气时间")
    print("-" * 70)

    dam.set_height(0.0)  # 从倒伏状态开始

    target = 2.5
    time_needed = dam.compute_inflation_time(target)

    print(f"当前坝高: {dam.current_height:.2f}m")
    print(f"目标坝高: {target:.2f}m")
    print(f"所需时间: {time_needed:.1f} min ({time_needed/60:.2f} h)")

    # 验证
    dam.inflate(time_needed)
    print(f"充气后: {dam.current_height:.2f}m")
    error = abs(dam.current_height - target)
    print(f"误差: {error:.4f}m")

    # 测试案例7：应急泄洪（快速放气）
    print("\n[测试7] 应急泄洪场景")
    print("-" * 70)

    dam.set_height(3.0)  # 满充气状态
    print(f"初始: 坝高 = {dam.current_height:.2f}m")

    # 洪水来临，需要紧急放气
    print("洪水来临，紧急放气...")

    time_to_deflate = dam.compute_inflation_time(0.0)
    print(f"完全倒伏所需时间: {time_to_deflate:.1f} min")

    dam.deflate(time_to_deflate)
    print(f"放气后: 坝高 = {dam.current_height:.2f}m")

    # 倒伏后流量（无阻水）
    h_up = 104.0
    h_down = 100.5
    Q, info = dam.compute_discharge(h_up, h_down)
    print(f"\n倒伏后流量: Q = {Q:.2f} m³/s")
    print(f"流态: {info['flow_type']}")
    print(f"是否完全倒伏: {info['is_deflated']}")

    print("\n" + "=" * 70)
    print("充气坝模块测试完成!")
    print("=" * 70)
