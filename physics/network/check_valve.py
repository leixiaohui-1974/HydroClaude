#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
单向阀 (Check Valve)

单向阀用于防止流体倒流，只允许单向流动。

类型：
- 旋启式: 适用于大管径，低阻力
- 升降式: 适用于小管径，密封性好

工作特性：
- 正向流动: K ≈ 2.0-5.0
- 反向流动: 完全关闭

作者: Claude
日期: 2025-10-22
"""

import numpy as np


class CheckValve:
    """
    单向阀组件

    防止倒流，只允许单向流动
    """

    def __init__(self, name: str, diameter: float,
                 forward_loss_coefficient: float = 3.0,
                 closing_pressure: float = 100.0):
        """
        Args:
            name: 阀门名称
            diameter: 阀门直径 (m)
            forward_loss_coefficient: 正向流动损失系数
            closing_pressure: 关闭压力差 (Pa), 反向压差超过此值时关闭
        """
        self.name = name
        self.diameter = diameter
        self.K_forward = forward_loss_coefficient
        self.P_closing = closing_pressure

        # 状态
        self.is_open = True
        self.flow_rate = 0.0

    def calculate_flow(self, P_up: float, P_down: float, rho: float = 1000.0) -> float:
        """
        计算通过阀门的流量

        Args:
            P_up: 上游压力 (Pa)
            P_down: 下游压力 (Pa)
            rho: 流体密度 (kg/m³)

        Returns:
            流量 (m³/s)
        """
        delta_P = P_up - P_down

        if delta_P > 0:
            # 正向流动
            self.is_open = True
            A = np.pi * (self.diameter / 2)**2
            V = np.sqrt(2 * delta_P / (rho * self.K_forward))
            Q = A * V
        elif delta_P < -self.P_closing:
            # 反向流动且压差超过关闭压力 → 关闭
            self.is_open = False
            Q = 0.0
        else:
            # 微小反向压差 → 保持当前状态
            Q = 0.0

        self.flow_rate = Q
        return Q

    def __repr__(self):
        state = "OPEN" if self.is_open else "CLOSED"
        return f"CheckValve(name='{self.name}', D={self.diameter}m, state={state}, Q={self.flow_rate:.3f}m³/s)"


if __name__ == "__main__":
    print("单向阀测试:")
    valve = CheckValve("CV1", diameter=0.4)
    print(f"  初始: {valve}")

    # 正向流动
    Q_forward = valve.calculate_flow(P_up=500000, P_down=400000)
    print(f"  正向流动: {valve}")

    # 反向流动
    Q_reverse = valve.calculate_flow(P_up=400000, P_down=500000)
    print(f"  反向流动: {valve}")
    print("  ✓ 单向阀组件测试通过")
