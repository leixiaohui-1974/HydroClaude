# -*- coding: utf-8 -*-
"""
pump.py - 物理模型模块：泵

为不同配置的泵站提供独立的物理计算模型。
"""

import math
from typing import List, Tuple

class PumpModel:
    """泵模型的基类"""
    def __init__(self, flow_rate: float, head: float, efficiency: float = 0.85):
        if flow_rate <= 0 or head <= 0:
            raise ValueError("泵的设计流量和扬程必须为正数")
        self.rated_flow = flow_rate  # 额定流量 Q_r
        self.rated_head = head      # 额定扬程 H_r
        self.efficiency = efficiency  # 泵的效率

    def get_performance_curve(self, num_points: int = 20) -> List[Tuple[float, float]]:
        """
        生成一个简化的泵性能曲线 (H-Q 曲线)
        假设曲线为: H = A - B * Q^2，并通过额定点和关死点 (Q=0, H=1.3*H_r)

        Returns:
            List[Tuple[float, float]]: 一系列 (流量, 扬程) 点
        """
        # 确定系数 A 和 B
        H_shutdown = 1.3 * self.rated_head
        A = H_shutdown
        B = (H_shutdown - self.rated_head) / (self.rated_flow ** 2)

        curve_points = []
        max_flow = self.rated_flow * 1.5
        for i in range(num_points):
            Q = (i / (num_points - 1)) * max_flow
            H = A - B * Q**2
            if H < 0: H = 0
            curve_points.append((Q, H))

        return curve_points

    def calculate_performance(self, system_head: float) -> dict:
        """
        根据系统扬程计算泵的实际工作点（流量、功率）
        """
        raise NotImplementedError("子类必须实现 'calculate_performance' 方法")

    def _calculate_power(self, flow: float, head: float) -> float:
        """计算功率 (kW)"""
        if self.efficiency == 0:
            return float('inf')
        G = 9.81  # 重力加速度
        rho = 1000  # 水的密度
        # 功率公式: P = (rho * g * Q * H) / eta
        power_watts = (rho * G * flow * head) / self.efficiency
        return power_watts / 1000  # 转换为 kW


class SinglePumpModel(PumpModel):
    """单泵模型"""
    def calculate_performance(self, system_head: float) -> dict:
        """
        计算单泵在给定系统扬程下的工作点
        """
        H_shutdown = 1.3 * self.rated_head
        A = H_shutdown
        B = (H_shutdown - self.rated_head) / (self.rated_flow ** 2)

        if system_head > H_shutdown:
            # 系统扬程超过了泵的最大扬程
            return {
                "flow_rate": 0.0,
                "head": H_shutdown,
                "power_kw": 0.0,
                "num_pumps": 1,
                "error": "系统扬程超过泵的关死扬程"
            }

        # 从 H = A - B * Q^2 反算 Q
        try:
            flow_rate = math.sqrt((A - system_head) / B)
        except ValueError:
            flow_rate = 0.0

        power = self._calculate_power(flow_rate, system_head)

        return {
            "flow_rate": flow_rate,
            "head": system_head,
            "power_kw": power,
            "num_pumps": 1,
            "error": None
        }


class ParallelPumpsModel(PumpModel):
    """并联泵模型"""
    def __init__(self, flow_rate: float, head: float, num_pumps: int, efficiency: float = 0.85):
        super().__init__(flow_rate, head, efficiency)
        if num_pumps <= 0:
            raise ValueError("并联泵数量必须为正整数")
        self.num_pumps = num_pumps

    def calculate_performance(self, system_head: float) -> dict:
        """
        计算并联泵组的工作点。并联时，流量为单泵的 N 倍，扬程不变。
        """
        single_pump = SinglePumpModel(self.rated_flow, self.rated_head, self.efficiency)
        single_pump_performance = single_pump.calculate_performance(system_head)

        if single_pump_performance["error"]:
            return {
                "flow_rate": 0.0,
                "head": single_pump_performance["head"],
                "power_kw": 0.0,
                "num_pumps": self.num_pumps,
                "error": single_pump_performance["error"]
            }

        total_flow = single_pump_performance["flow_rate"] * self.num_pumps
        total_power = single_pump_performance["power_kw"] * self.num_pumps

        return {
            "flow_rate": total_flow,
            "head": system_head,
            "power_kw": total_power,
            "num_pumps": self.num_pumps,
            "error": None
        }


class SeriesPumpsModel(PumpModel):
    """串联泵模型"""
    def __init__(self, flow_rate: float, head: float, num_pumps: int, efficiency: float = 0.85):
        super().__init__(flow_rate, head, efficiency)
        if num_pumps <= 0:
            raise ValueError("串联泵数量必须为正整数")
        self.num_pumps = num_pumps

    def calculate_performance(self, system_head: float) -> dict:
        """
        计算串联泵组的工作点。串联时，扬程为单泵的 N 倍，流量不变。
        """
        # 等效的单泵系统扬程
        equivalent_system_head = system_head / self.num_pumps

        single_pump = SinglePumpModel(self.rated_flow, self.rated_head, self.efficiency)
        single_pump_performance = single_pump.calculate_performance(equivalent_system_head)

        if single_pump_performance["error"]:
            return {
                "flow_rate": 0.0,
                "head": single_pump_performance["head"] * self.num_pumps,
                "power_kw": 0.0,
                "num_pumps": self.num_pumps,
                "error": single_pump_performance["error"]
            }

        total_power = single_pump_performance["power_kw"] * self.num_pumps

        return {
            "flow_rate": single_pump_performance["flow_rate"],
            "head": system_head,
            "power_kw": total_power,
            "num_pumps": self.num_pumps,
            "error": None
        }


def get_pump_model(pump_type: str, flow_rate: float, head: float, num_pumps: int, efficiency: float = 0.85) -> PumpModel:
    """
    泵模型工厂函数
    """
    if pump_type == "single":
        return SinglePumpModel(flow_rate, head, efficiency)
    elif pump_type == "parallel":
        return ParallelPumpsModel(flow_rate, head, num_pumps, efficiency)
    elif pump_type == "series":
        return SeriesPumpsModel(flow_rate, head, num_pumps, efficiency)
    else:
        raise ValueError(f"不支持的泵类型: {pump_type}")
