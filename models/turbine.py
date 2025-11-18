# -*- coding: utf-8 -*-
"""
turbine.py - 物理模型模块：水轮机

为水轮机提供简化的性能计算模型。
"""

import math

class TurbineModel:
    """水轮机模型的基类"""
    def __init__(self, rated_power: float, rated_head: float, rated_flow: float, efficiency: float = 0.9):
        if rated_power <= 0 or rated_head <= 0 or rated_flow <= 0:
            raise ValueError("水轮机的额定参数必须为正数")
        self.rated_power_mw = rated_power  # 额定功率 (MW)
        self.rated_head = rated_head      # 额定水头 (m)
        self.rated_flow = rated_flow      # 额定流量 (m³/s)
        self.efficiency = efficiency      # 额定效率

    def calculate_performance(self, current_head: float, current_flow: float) -> dict:
        """
        根据当前的水头和流量，估算水轮机的输出功率和效率。
        """
        raise NotImplementedError("子类必须实现 'calculate_performance' 方法")

class SimplifiedTurbineModel(TurbineModel):
    """简化的通用水轮机模型"""
    def calculate_performance(self, current_head: float, current_flow: float) -> dict:
        """
        使用功率公式和简化的效率曲线来估算性能。

        功率公式: P = rho * g * Q * H * eta
        """
        if current_head <= 0 or current_flow <= 0:
            return {
                "power_mw": 0.0,
                "efficiency": 0.0,
                "head": current_head,
                "flow": current_flow,
                "error": "水头或流量为零，无法发电"
            }

        rho = 1000  # 水的密度
        g = 9.81    # 重力加速度

        # 简化效率估算：
        # 假设效率与水头和流量偏离额定点的程度有关
        head_ratio = current_head / self.rated_head
        flow_ratio = current_flow / self.rated_flow

        # 这是一个非常简化的效率模型，实际模型要复杂得多
        # 当流量或水头偏离额定值时，效率会下降
        efficiency_factor = 1.0 - 0.5 * abs(1.0 - head_ratio) - 0.5 * abs(1.0 - flow_ratio)
        current_efficiency = self.efficiency * max(0, efficiency_factor)

        # 计算功率
        power_watts = rho * g * current_flow * current_head * current_efficiency
        power_mw = power_watts / 1_000_000

        return {
            "power_mw": power_mw,
            "efficiency": current_efficiency,
            "head": current_head,
            "flow": current_flow,
            "error": None
        }

def get_turbine_model(turbine_type: str, **kwargs) -> TurbineModel:
    """
    水轮机模型工厂函数
    """
    # 目前我们只有一个简化的通用模型，未来可以根据 turbine_type 扩展
    # 例如：'francis', 'kaplan', 'pelton' 可以有不同的效率曲线模型

    if turbine_type.lower() in ['francis', 'kaplan', 'pelton', 'simplified']:
         return SimplifiedTurbineModel(
            rated_power=kwargs['rated_power'],
            rated_head=kwargs['rated_head'],
            rated_flow=kwargs['rated_flow'],
            efficiency=kwargs.get('efficiency', 0.9)
        )
    else:
        raise ValueError(f"不支持的水轮机类型: {turbine_type}")
