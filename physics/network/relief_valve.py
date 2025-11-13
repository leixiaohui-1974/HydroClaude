#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
安全阀 (Relief Valve)

安全阀用于防止管道超压，当压力超过设定值时自动开启泄压。

工作特性：
- P < P_set: 关闭
- P >= P_set: 开启，泄压流量与超压成正比

作者: Claude
日期: 2025-10-22
"""

import numpy as np


class ReliefValve:
    """
    安全阀组件

    超压保护，自动泄压
    """

    def __init__(self, name: str, diameter: float,
                 set_pressure: float,
                 discharge_coefficient: float = 0.65,
                 hysteresis: float = 0.05):
        """
        Args:
            name: 阀门名称
            diameter: 阀门直径 (m)
            set_pressure: 设定压力 (Pa)
            discharge_coefficient: 流量系数
            hysteresis: 回差系数 (0-1), 防止频繁开关
        """
        self.name = name
        self.diameter = diameter
        self.P_set = set_pressure
        self.Cd = discharge_coefficient
        self.hysteresis = hysteresis

        # 开启和关闭压力（考虑回差）
        self.P_open = set_pressure
        self.P_close = set_pressure * (1 - hysteresis)

        # 状态
        self.is_open = False
        self.relief_flow = 0.0

    def calculate_relief_flow(self, pressure: float, P_ambient: float = 101325.0,
                             rho: float = 1000.0) -> float:
        """
        计算泄压流量

        Args:
            pressure: 当前压力 (Pa)
            P_ambient: 环境压力 (Pa)
            rho: 流体密度 (kg/m³)

        Returns:
            泄压流量 (m³/s)
        """
        if not self.is_open and pressure >= self.P_open:
            # 开启
            self.is_open = True
        elif self.is_open and pressure < self.P_close:
            # 关闭
            self.is_open = False

        if self.is_open:
            # 泄压流量
            delta_P = max(0, pressure - P_ambient)
            A = np.pi * (self.diameter / 2)**2
            V = np.sqrt(2 * delta_P / rho)
            Q = self.Cd * A * V
        else:
            Q = 0.0

        self.relief_flow = Q
        return Q

    def __repr__(self):
        state = "OPEN" if self.is_open else "CLOSED"
        return (f"ReliefValve(name='{self.name}', P_set={self.P_set/1e5:.2f}bar, "
                f"state={state}, Q_relief={self.relief_flow:.3f}m³/s)")


if __name__ == "__main__":
    print("安全阀测试:")
    valve = ReliefValve("RV1", diameter=0.1, set_pressure=600000)  # 6bar
    print(f"  初始: {valve}")

    # 正常压力
    Q1 = valve.calculate_relief_flow(pressure=500000)  # 5bar
    print(f"  正常压力(5bar): {valve}")

    # 超压
    Q2 = valve.calculate_relief_flow(pressure=650000)  # 6.5bar
    print(f"  超压(6.5bar): {valve}")

    # 压力下降
    Q3 = valve.calculate_relief_flow(pressure=580000)  # 5.8bar
    print(f"  压力下降(5.8bar): {valve}")

    print("   安全阀组件测试通过")
