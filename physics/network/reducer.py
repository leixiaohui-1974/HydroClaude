#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
渐变管 (Reducer/Expander)

渐变管用于连接不同直径的管道，包括：
- 渐缩管 (Reducer): 大管径→小管径
- 渐扩管 (Expander): 小管径→大管径

损失系数与截面变化率、锥角有关。

作者: Claude
日期: 2025-10-22
"""

import numpy as np


class Reducer:
    """渐缩管 - 大管径→小管径"""

    def __init__(self, name: str, D1: float, D2: float,
                 cone_angle: float = 20.0):
        """
        Args:
            name: 组件名称
            D1: 上游管径 (m)
            D2: 下游管径 (m), D2 < D1
            cone_angle: 锥角 (度)
        """
        self.name = name
        self.D1 = D1
        self.D2 = D2
        self.cone_angle = cone_angle
        self.area_ratio = (D2 / D1) ** 2
        # 渐缩损失系数 (经验公式)
        self.K = 0.5 * (1 - self.area_ratio)**2

    def calculate_head_loss(self, V1: float, g: float = 9.81) -> float:
        """h_loss = K * V1² / (2g)"""
        return self.K * V1**2 / (2 * g)

    def __repr__(self):
        return f"Reducer(D1={self.D1}m, D2={self.D2}m, K={self.K:.3f})"


class Expander:
    """渐扩管 - 小管径→大管径"""

    def __init__(self, name: str, D1: float, D2: float,
                 cone_angle: float = 10.0):
        """
        Args:
            name: 组件名称
            D1: 上游管径 (m)
            D2: 下游管径 (m), D2 > D1
            cone_angle: 锥角 (度)
        """
        self.name = name
        self.D1 = D1
        self.D2 = D2
        self.cone_angle = cone_angle
        self.area_ratio = (D1 / D2) ** 2
        # 渐扩损失系数 (Borda-Carnot公式)
        self.K = (1 - self.area_ratio)**2

    def calculate_head_loss(self, V1: float, g: float = 9.81) -> float:
        """h_loss = K * V1² / (2g)"""
        return self.K * V1**2 / (2 * g)

    def __repr__(self):
        return f"Expander(D1={self.D1}m, D2={self.D2}m, K={self.K:.3f})"


if __name__ == "__main__":
    print("渐变管测试:")
    reducer = Reducer("R1", D1=0.5, D2=0.3)
    expander = Expander("E1", D1=0.3, D2=0.5)
    print(f"  {reducer}")
    print(f"  {expander}")
    V = 3.0
    print(f"  V={V}m/s: h_loss_reducer={reducer.calculate_head_loss(V):.4f}m, "
          f"h_loss_expander={expander.calculate_head_loss(V):.4f}m")
    print("  ✓ 渐变管组件测试通过")
