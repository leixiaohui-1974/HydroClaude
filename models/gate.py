# -*- coding: utf-8 -*-
"""
gate.py - 物理模型模块：闸门

该模块为不同类型的闸门提供独立的、可测试的物理计算模型。
"""

import math

G = 9.81  # 重力加速度

class GateModel:
    """闸门模型的基类"""
    def __init__(self, width: float, opening: float, discharge_coeff: float):
        if width <= 0 or opening <= 0 or discharge_coeff <= 0:
            raise ValueError("闸门参数必须为正数")
        self.width = width
        self.opening = opening
        self.discharge_coeff = discharge_coeff

    def calculate_discharge(self, upstream_depth: float, downstream_depth: float) -> dict:
        """
        计算流量，并判断流态

        Args:
            upstream_depth (float): 上游水深 (m)
            downstream_depth (float): 下游水深 (m)

        Returns:
            dict: 包含流量、流态和其他水力参数的字典
        """
        raise NotImplementedError("子类必须实现 'calculate_discharge' 方法")

    def _determine_flow_regime(self, upstream_depth: float, downstream_depth: float) -> str:
        """
        判断是自由流还是淹没流 (这是一个通用的判断，具体模型可以重写)
        通常，当 下游水深 / 闸孔开度 > 某个阈值时，可能发生淹没。
        一个常用的简化判断是比较下游水深和闸孔开度。
        """
        # 这是一个简化的判断，更精确的方法需要考虑水力跃迁
        if downstream_depth > self.opening:
            return "submerged"
        return "free"


class SluiceGateModel(GateModel):
    """平板闸门模型"""
    def calculate_discharge(self, upstream_depth: float, downstream_depth: float) -> dict:
        """
        使用标准平板闸门公式计算流量
        """
        if upstream_depth <= 0:
            return {
                "discharge": 0.0,
                "flow_regime": "no_flow",
                "velocity": 0.0,
                "error": None
            }

        if upstream_depth < self.opening:
             return {
                "discharge": 0.0,
                "flow_regime": "no_flow",
                "velocity": 0.0,
                "error": "上游水深小于闸门开度，无法过流"
            }

        flow_regime = self._determine_flow_regime(upstream_depth, downstream_depth)

        try:
            if flow_regime == "free":
                # 自由流公式: Q = C_d * b * a * sqrt(2 * g * h1)
                discharge = self.discharge_coeff * self.width * self.opening * math.sqrt(2 * G * upstream_depth)
            else: # submerged
                # 淹没流公式: Q = C_d * b * a * sqrt(2 * g * (h1 - h2))
                head_diff = upstream_depth - downstream_depth
                if head_diff <= 0:
                    return {
                        "discharge": 0.0,
                        "flow_regime": "submerged_no_flow",
                        "velocity": 0.0,
                        "error": "淹没流条件下，上下游水位差小于等于0"
                    }
                discharge = self.discharge_coeff * self.width * self.opening * math.sqrt(2 * G * head_diff)
        except ValueError as e:
            return {
                "discharge": 0.0,
                "flow_regime": "calculation_error",
                "velocity": 0.0,
                "error": f"计算出错: {e}"
            }

        # 计算过闸流速
        flow_area = self.width * self.opening
        velocity = discharge / flow_area if flow_area > 0 else 0.0

        return {
            "discharge": discharge,
            "flow_regime": flow_regime,
            "velocity": velocity,
            "error": None
        }


class RadialGateModel(GateModel):
    """径向闸门模型"""
    def calculate_discharge(self, upstream_depth: float, downstream_depth: float) -> dict:
        """
        使用径向闸门公式计算流量。
        对于许多应用场景，其公式与平板闸门类似，但流量系数会根据闸门角度和开度变化。
        此处我们假设传入的 discharge_coeff 已经是有效的。
        """
        # 目前，径向闸门的计算逻辑与平板闸门相同，但将其分开是为了未来的扩展
        # 例如，可以引入更复杂的流量系数计算方法
        sluice_model = SluiceGateModel(self.width, self.opening, self.discharge_coeff)
        return sluice_model.calculate_discharge(upstream_depth, downstream_depth)

# 可以在这里添加其他闸门类型，如 VerticalLiftGateModel 等

def get_gate_model(gate_type: str, width: float, opening: float, discharge_coeff: float) -> GateModel:
    """
    闸门模型工厂函数

    Args:
        gate_type (str): 闸门类型 (例如 'sluice', 'radial')
        ... 其他参数 ...

    Returns:
        GateModel: 对应的闸门模型实例
    """
    if gate_type == "sluice":
        return SluiceGateModel(width, opening, discharge_coeff)
    elif gate_type == "radial":
        return RadialGateModel(width, opening, discharge_coeff)
    # 以后可以扩展其他类型
    # elif gate_type == "vertical_lift":
    #     return VerticalLiftGateModel(...)
    else:
        raise ValueError(f"不支持的闸门类型: {gate_type}")
