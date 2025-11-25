# -*- coding: utf-8 -*-
"""
Model Factory Module
负责创建各种水工结构模型的实例
"""
from typing import Dict, Any, Optional

# 导入核心结构类
from web.backend.core.structures.pump_station import PumpStation, PumpCurve, PumpType, STANDARD_PUMP_CURVES
from web.backend.core.structures.advanced_gates import SluiceGate, RadialGate, GateType
from web.backend.core.structures.advanced_weirs import BroadCrestedWeir, SharpCrestedWeir, VNotchWeir, WeirType
from web.backend.core.structures.turbine import Turbine, TurbineType, TurbineCharacteristics, STANDARD_TURBINES
from web.backend.core.structures.valve import Valve, ValveType

def get_pump_model(
    pump_type: str = "single",
    flow_rate: float = 10.0,
    head: float = 15.0,
    num_pumps: int = 1
) -> PumpStation:
    """
    获取泵站模型
    """
    # 简单的泵曲线生成 (基于额定点)
    # H = H_max - (H_max/Q_max^2) * Q^2
    # 假设 H_max = 1.2 * rated_head, Q_max = 1.5 * rated_flow
    H_max = head * 1.2
    Q_max = flow_rate * 1.5
    
    # 简化的二次曲线系数: H = a + c*Q^2
    # a = H_max
    # c = -H_max / Q_max^2
    a = H_max
    c = -H_max / (Q_max**2) if Q_max > 0 else 0
    
    curve = PumpCurve(
        coefficients=(a, 0, c),
        Q_min=0, Q_max=Q_max,
        H_min=0, H_max=H_max
    )
    
    # 映射类型
    p_type = PumpType.SINGLE
    if pump_type == "parallel":
        p_type = PumpType.PARALLEL
    elif pump_type == "series":
        p_type = PumpType.SERIES
        
    return PumpStation(
        name="Pump-Dynamic",
        position=0.0,
        pump_curve=curve,
        pump_type=p_type,
        num_pumps=num_pumps
    )

def get_gate_model(
    gate_type: str = "sluice",
    width: float = 5.0,
    opening: float = 1.0,
    discharge_coeff: float = 0.6
):
    """
    获取闸门模型
    """
    if gate_type == "radial":
        return RadialGate(
            name="Gate-Dynamic",
            position=0.0,
            width=width,
            opening=opening,
            discharge_coeff=discharge_coeff,
            radius=opening * 3.0 # 估算半径
        )
    else:
        return SluiceGate(
            name="Gate-Dynamic",
            position=0.0,
            width=width,
            opening=opening,
            discharge_coeff=discharge_coeff
        )

def get_weir_model(
    weir_type: str = "broad_crested",
    crest_height: float = 1.0,
    discharge_coeff: float = 1.7,
    width: float = 10.0,
    angle_deg: Optional[float] = None
):
    """
    获取堰模型
    """
    if weir_type == "sharp_crested":
        return SharpCrestedWeir(
            name="Weir-Dynamic",
            position=0.0,
            width=width,
            crest_height=crest_height,
            discharge_coeff=discharge_coeff
        )
    elif weir_type == "v_notch":
        return VNotchWeir(
            name="Weir-Dynamic",
            position=0.0,
            crest_height=crest_height,
            notch_angle=angle_deg if angle_deg else 90.0,
            discharge_coeff=discharge_coeff
        )
    else:
        return BroadCrestedWeir(
            name="Weir-Dynamic",
            position=0.0,
            width=width,
            crest_height=crest_height,
            discharge_coeff=discharge_coeff
        )

def get_turbine_model(
    turbine_type: str = "francis",
    rated_power: float = 50.0,
    rated_head: float = 100.0,
    rated_flow: float = 60.0
) -> Turbine:
    """
    获取水轮机模型
    """
    # 映射类型
    t_type = TurbineType.FRANCIS
    if turbine_type == "kaplan":
        t_type = TurbineType.KAPLAN
    elif turbine_type == "pelton":
        t_type = TurbineType.PELTON
        
    # 创建特性
    char = TurbineCharacteristics(
        rated_head=rated_head,
        rated_flow=rated_flow,
        rated_power=rated_power,
        rated_efficiency=0.92, # 默认
        rated_speed=300.0, # 默认
        min_head=rated_head * 0.6,
        max_head=rated_head * 1.3,
        min_flow=rated_flow * 0.2,
        max_flow=rated_flow * 1.1
    )
    
    return Turbine(
        name="Turbine-Dynamic",
        position=0.0,
        turbine_type=t_type,
        characteristics=char
    )

def get_valve_model(
    valve_type: str = "butterfly",
    diameter: float = 1.0
) -> Valve:
    """
    获取阀门模型
    """
    # 映射类型
    v_type = ValveType.BUTTERFLY
    if valve_type == "ball":
        v_type = ValveType.BALL
    elif valve_type == "gate":
        v_type = ValveType.GATE
    elif valve_type == "globe":
        v_type = ValveType.GLOBE
        
    return Valve(
        name="Valve-Dynamic",
        position=0.0,
        valve_type=v_type,
        diameter=diameter,
        cv_full_open=diameter * 100.0 # 粗略估算
    )
