# -*- coding: utf-8 -*-
"""
valve.py - 物理模型模块：阀门

为阀门提供简化的水力计算模型。
"""

import math

class ValveModel:
    """阀门模型的基类"""
    def __init__(self, diameter: float):
        if diameter <= 0:
            raise ValueError("阀门直径必须为正数")
        self.diameter = diameter
        self.area = math.pi * (diameter / 2) ** 2

    def calculate_flow(self, upstream_pressure: float, downstream_pressure: float, opening_percent: float) -> dict:
        """
        根据上下游压力差和开度计算流量。
        """
        raise NotImplementedError("子类必须实现 'calculate_flow' 方法")


class GeneralValveModel(ValveModel):
    """通用阀门模型"""
    def get_loss_coefficient(self, opening_percent: float) -> float:
        """
        估算阀门的局部损失系数 (K)。
        这是一个非常简化的模型，真实值取决于阀门类型（蝶阀、球阀等）。
        假设 K 与开度的平方成反比 (全开时 K 最小，关闭时 K 趋于无穷)。
        """
        if opening_percent <= 0:
            return float('inf')
        if opening_percent >= 100:
            return 0.2  # 假设全开时损失系数很小

        # 简化公式: K = A / (opening)^B
        # 这里使用一个简单的指数关系
        # 当 opening=100, K=0.2; 当 opening=1, K 很大
        return 0.2 / ((opening_percent / 100) ** 2.5)

    def calculate_flow(self, upstream_pressure: float, downstream_pressure: float, opening_percent: float = 100.0) -> dict:
        """
        使用能量方程和局部损失系数计算流量。
        能量方程: P1/rho*g + v1^2/2g = P2/rho*g + v2^2/2g + K * v^2/2g
        简化假设 v1=v2 (管径不变)，则 P1-P2 = K * rho * v^2 / 2
        由此可得: v = sqrt(2 * delta_P / (K * rho))
        Q = A * v
        """
        if opening_percent < 0 or opening_percent > 100:
            raise ValueError("阀门开度必须在 0% 到 100% 之间")

        pressure_diff_pa = upstream_pressure - downstream_pressure

        if pressure_diff_pa <= 0:
            return {
                "flow_rate": 0.0,
                "velocity": 0.0,
                "pressure_diff_pa": pressure_diff_pa,
                "loss_coefficient": self.get_loss_coefficient(opening_percent),
                "error": "下游压力大于或等于上游压力，无流动"
            }

        rho = 1000  # 水的密度
        K = self.get_loss_coefficient(opening_percent)

        if K == float('inf'):
            velocity = 0.0
        else:
            try:
                velocity = math.sqrt(2 * pressure_diff_pa / (K * rho))
            except (ValueError, ZeroDivisionError):
                velocity = 0.0

        flow_rate = self.area * velocity

        return {
            "flow_rate": flow_rate,
            "velocity": velocity,
            "pressure_diff_pa": pressure_diff_pa,
            "loss_coefficient": K,
            "error": None
        }

def get_valve_model(valve_type: str, **kwargs) -> ValveModel:
    """
    阀门模型工厂函数
    """
    # 目前只有一个通用模型，未来可以为 'butterfly', 'ball', 'gate' 等创建更精确的 K 值模型
    if valve_type.lower() in ['general', 'butterfly', 'ball', 'gate', 'globe']:
        return GeneralValveModel(diameter=kwargs['diameter'])
    else:
        raise ValueError(f"不支持的阀门类型: {valve_type}")
