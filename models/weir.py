# -*- coding: utf-8 -*-
"""
weir.py - 物理模型模块：堰 (Refactored for robustness)

为不同类型的堰提供独立的物理计算模型。
"""

import math

G = 9.81  # 重力加速度

class WeirModel:
    """堰模型的基类"""
    def __init__(self, crest_height: float, discharge_coeff: float, **kwargs):
        if crest_height < 0 or discharge_coeff <= 0:
            raise ValueError("堰顶高程和流量系数必须为正数")
        self.crest_height = crest_height  # 堰顶高程 P
        self.discharge_coeff = discharge_coeff

    def calculate_discharge(self, upstream_depth: float, downstream_depth: float) -> dict:
        """
        计算过堰流量
        """
        raise NotImplementedError("子类必须实现 'calculate_discharge' 方法")


class BroadCrestedWeirModel(WeirModel):
    """宽顶堰模型"""
    def __init__(self, width: float, **kwargs):
        super().__init__(**kwargs)
        if width <= 0:
            raise ValueError("宽顶堰的 'width' 必须为正数")
        self.width = width

    def calculate_discharge(self, upstream_depth: float, downstream_depth: float) -> dict:
        """
        使用宽顶堰公式计算流量
        """
        head = upstream_depth - self.crest_height

        if head <= 0:
            return { "discharge": 0.0, "flow_regime": "no_flow", "head": 0.0, "error": "上游水位低于堰顶" }

        submergence_ratio = (downstream_depth - self.crest_height) / head if head > 0 else 0
        is_submerged = submergence_ratio > 0.66

        try:
            if not is_submerged:
                discharge = self.discharge_coeff * self.width * (head ** 1.5)
                flow_regime = "free"
            else:
                correction_factor = (1 - submergence_ratio ** 1.5) ** 0.385
                free_flow_discharge = self.discharge_coeff * self.width * (head ** 1.5)
                discharge = free_flow_discharge * correction_factor
                flow_regime = "submerged"
        except (ValueError, TypeError) as e:
            return { "discharge": 0.0, "flow_regime": "calculation_error", "head": head, "error": f"计算出错: {e}" }

        return { "discharge": discharge, "flow_regime": flow_regime, "head": head, "submergence_ratio": submergence_ratio, "error": None }


class SharpCrestedWeirModel(WeirModel):
    """尖顶堰模型"""
    def __init__(self, width: float, **kwargs):
        super().__init__(**kwargs)
        if width <= 0:
            raise ValueError("尖顶堰的 'width' 必须为正数")
        self.width = width

    def calculate_discharge(self, upstream_depth: float, downstream_depth: float) -> dict:
        """
        使用尖顶堰（矩形）公式计算流量
        """
        head = upstream_depth - self.crest_height

        if head <= 0:
            return { "discharge": 0.0, "flow_regime": "no_flow", "head": 0.0, "error": "上游水位低于堰顶" }

        try:
            # Reissner's formula correction factor can be added here in future
            discharge = (2/3) * self.discharge_coeff * self.width * math.sqrt(2 * G) * (head ** 1.5)
            flow_regime = "free"  # Submergence for sharp-crested weirs is complex, simplified for now
        except (ValueError, TypeError) as e:
             return { "discharge": 0.0, "flow_regime": "calculation_error", "head": head, "error": f"计算出错: {e}" }

        return { "discharge": discharge, "flow_regime": flow_regime, "head": head, "error": None }


class VNotchWeirModel(WeirModel):
    """V型堰 (三角堰) 模型"""
    def __init__(self, angle_deg: float, **kwargs):
        super().__init__(**kwargs)
        if not (0 < angle_deg < 180):
            raise ValueError("V型堰 'angle_deg' 必须在 0 到 180 度之间")
        self.angle_rad = math.radians(angle_deg)

    def calculate_discharge(self, upstream_depth: float, downstream_depth: float) -> dict:
        """
        使用V型堰公式计算流量
        """
        head = upstream_depth - self.crest_height

        if head <= 0:
            return { "discharge": 0.0, "flow_regime": "no_flow", "head": 0.0, "error": "上游水位低于堰顶" }

        try:
            term1 = (8/15) * self.discharge_coeff
            term2 = math.tan(self.angle_rad / 2)
            term3 = math.sqrt(2 * G)
            term4 = head ** 2.5
            discharge = term1 * term2 * term3 * term4
            flow_regime = "free"
        except (ValueError, TypeError) as e:
            return { "discharge": 0.0, "flow_regime": "calculation_error", "head": head, "error": f"计算出错: {e}" }

        return { "discharge": discharge, "flow_regime": flow_regime, "head": head, "error": None }


def get_weir_model(weir_type: str, **kwargs) -> WeirModel:
    """
    堰模型工厂函数
    """
    # 从kwargs中提取通用参数
    common_args = {
        'crest_height': kwargs.get('crest_height'),
        'discharge_coeff': kwargs.get('discharge_coeff')
    }

    if weir_type == "broad_crested":
        return BroadCrestedWeirModel(width=kwargs.get('width'), **common_args)
    elif weir_type == "sharp_crested":
        return SharpCrestedWeirModel(width=kwargs.get('width'), **common_args)
    elif weir_type == "v_notch":
        return VNotchWeirModel(angle_deg=kwargs.get('angle_deg'), **common_args)
    else:
        raise ValueError(f"不支持的堰类型: {weir_type}")
