#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Turbine Module
水轮机模块

对标商业软件的水轮机建模功能

Author: HydroClaude Team
Date: 2025-11-15
"""

import numpy as np
from typing import Dict, Optional, Tuple, List
from enum import Enum
from dataclasses import dataclass


class TurbineType(Enum):
    """水轮机类型"""
    FRANCIS = "francis"      # 混流式
    KAPLAN = "kaplan"        # 轴流式（可调桨）
    PELTON = "pelton"        # 冲击式（水斗式）
    BULB = "bulb"            # 灯泡式
    TURGO = "turgo"          # 斜击式
    CROSSFLOW = "crossflow"  # 贯流式


@dataclass
class TurbineCharacteristics:
    """水轮机特性曲线"""
    # 设计参数
    rated_head: float           # 额定水头 (m)
    rated_flow: float           # 额定流量 (m³/s)
    rated_power: float          # 额定功率 (MW)
    rated_efficiency: float     # 额定效率 (0-1)
    rated_speed: float          # 额定转速 (rpm)
    
    # 运行范围
    min_head: float = 0.0       # 最小水头 (m)
    max_head: float = 0.0       # 最大水头 (m)
    min_flow: float = 0.0       # 最小流量 (m³/s)
    max_flow: float = 0.0       # 最大流量 (m³/s)
    
    # 特性曲线（可选，使用数据表）
    head_data: Optional[List[float]] = None      # 水头数据点
    flow_data: Optional[List[float]] = None      # 流量数据点
    efficiency_data: Optional[List[float]] = None # 效率数据点
    power_data: Optional[List[float]] = None      # 功率数据点


class Turbine:
    """
    水轮机类
    
    功能：
    1. 多种水轮机类型（Francis/Kaplan/Pelton等）
    2. 功率-效率计算
    3. 特性曲线
    4. 运行工况分析
    5. 调节性能
    6. 空化预测
    
    参考商业软件：
    - HEC-RAS: 不支持
    - MIKE: Turbine（有限）
    - InfoWorks: 不支持
    - RETScreen: 有水电分析
    """
    
    def __init__(
        self,
        name: str,
        position: float,
        turbine_type: TurbineType,
        characteristics: TurbineCharacteristics,
        num_units: int = 1
    ):
        """
        初始化水轮机
        
        Args:
            name: 水轮机名称
            position: 位置 (m)
            turbine_type: 水轮机类型
            characteristics: 水轮机特性
            num_units: 机组数量
        """
        self.name = name
        self.position = position
        self.turbine_type = turbine_type
        self.char = characteristics
        self.num_units = num_units
        
        # 运行状态
        self.is_running = False
        self.current_head = 0.0
        self.current_flow = 0.0
        self.current_power = 0.0
        self.current_efficiency = 0.0
        
        # 历史记录
        self.head_history = []
        self.flow_history = []
        self.power_history = []
        self.efficiency_history = []
        
        # 建立插值函数（如果有数据）
        self._build_interpolation()
    
    def _build_interpolation(self):
        """建立特性曲线插值"""
        if (self.char.head_data is not None and 
            self.char.flow_data is not None and
            self.char.efficiency_data is not None):
            
            from scipy.interpolate import interp2d
            # 2D插值：效率 = f(水头, 流量)
            # 这里简化，实际应该用综合特性曲线
            pass
    
    def compute_efficiency(self, head: float, flow: float) -> float:
        """
        计算效率
        
        Args:
            head: 净水头 (m)
            flow: 流量 (m³/s)
            
        Returns:
            效率 (0-1)
        """
        # 单位流量
        Q11 = flow / (head ** 0.5) if head > 0 else 0
        
        # 额定单位流量
        Q11_rated = (self.char.rated_flow / 
                     (self.char.rated_head ** 0.5))
        
        if self.turbine_type == TurbineType.FRANCIS:
            # 混流式水轮机效率曲线（经验公式）
            # 在额定点附近效率最高
            q_ratio = Q11 / Q11_rated if Q11_rated > 0 else 0
            
            # 抛物线拟合（在0.6-1.2倍额定流量范围内）
            if 0.3 < q_ratio < 1.3:
                # 峰值在1.0处
                eta = self.char.rated_efficiency * (
                    1 - 0.5 * (q_ratio - 1.0) ** 2
                )
            elif q_ratio <= 0.3:
                # 低负荷区
                eta = self.char.rated_efficiency * 0.7 * (q_ratio / 0.3)
            else:
                # 过负荷区
                eta = self.char.rated_efficiency * 0.8
            
        elif self.turbine_type == TurbineType.KAPLAN:
            # 轴流式水轮机（可调桨，效率曲线较平坦）
            q_ratio = Q11 / Q11_rated if Q11_rated > 0 else 0
            
            if 0.4 < q_ratio < 1.2:
                # 可调桨叶片，效率高且平坦
                eta = self.char.rated_efficiency * (
                    1 - 0.15 * (q_ratio - 1.0) ** 2
                )
            elif q_ratio <= 0.4:
                eta = self.char.rated_efficiency * 0.85 * (q_ratio / 0.4)
            else:
                eta = self.char.rated_efficiency * 0.9
            
        elif self.turbine_type == TurbineType.PELTON:
            # 冲击式水轮机（适用于高水头）
            # 部分负荷性能好
            q_ratio = flow / self.char.rated_flow if self.char.rated_flow > 0 else 0
            
            if 0.2 < q_ratio < 1.1:
                # Pelton效率曲线相对平坦
                eta = self.char.rated_efficiency * (
                    0.95 + 0.05 * (1 - abs(q_ratio - 0.8) / 0.6)
                )
            elif q_ratio <= 0.2:
                eta = self.char.rated_efficiency * 0.7
            else:
                eta = self.char.rated_efficiency * 0.85
        
        else:
            # 其他类型，使用通用曲线
            q_ratio = flow / self.char.rated_flow if self.char.rated_flow > 0 else 0
            eta = self.char.rated_efficiency * (
                0.9 + 0.1 * (1 - (q_ratio - 1.0) ** 2)
            )
        
        # 限制在合理范围
        eta = max(0.0, min(eta, 0.98))
        
        return eta
    
    def compute_power(self, head: float, flow: float) -> Tuple[float, float]:
        """
        计算输出功率
        
        Args:
            head: 净水头 (m)
            flow: 流量 (m³/s)
            
        Returns:
            (功率 MW, 效率)
        """
        g = 9.81  # m/s²
        rho = 1000  # kg/m³
        
        # 计算效率
        efficiency = self.compute_efficiency(head, flow)
        
        # 水力功率
        P_hydraulic = rho * g * flow * head / 1e6  # MW
        
        # 输出功率
        P_output = P_hydraulic * efficiency
        
        # 限制在额定功率以内
        P_output = min(P_output, self.char.rated_power * 1.1)
        
        return P_output, efficiency
    
    def compute_optimal_flow(self, head: float) -> float:
        """
        计算给定水头下的最优流量（最高效率点）
        
        Args:
            head: 净水头 (m)
            
        Returns:
            最优流量 (m³/s)
        """
        if self.turbine_type in [TurbineType.FRANCIS, TurbineType.KAPLAN]:
            # 混流式和轴流式，最优点在额定单位流量附近
            Q11_rated = (self.char.rated_flow / 
                        (self.char.rated_head ** 0.5))
            Q_optimal = Q11_rated * (head ** 0.5)
        
        elif self.turbine_type == TurbineType.PELTON:
            # 冲击式，最优点在80%额定流量
            Q_optimal = self.char.rated_flow * 0.8 * (
                head / self.char.rated_head
            )
        
        else:
            # 其他类型
            Q_optimal = self.char.rated_flow * (
                head / self.char.rated_head
            ) ** 0.5
        
        # 限制在运行范围内
        Q_optimal = max(self.char.min_flow, 
                       min(Q_optimal, self.char.max_flow))
        
        return Q_optimal
    
    def check_cavitation(self, head: float, elevation: float) -> Dict:
        """
        空化校核
        
        Args:
            head: 净水头 (m)
            elevation: 水轮机安装高程 (m)
            
        Returns:
            空化参数
        """
        # 临界空化系数（与比转速相关）
        # ns = n * sqrt(P) / H^(5/4)  (比转速)
        
        if head > 0:
            P = self.char.rated_power
            H = head
            n = self.char.rated_speed
            
            # 比转速
            ns = n * np.sqrt(P) / (H ** 1.25)
            
            # 临界空化系数（经验公式）
            if self.turbine_type == TurbineType.FRANCIS:
                sigma_c = 0.08 + (ns / 1000) ** 2
            elif self.turbine_type == TurbineType.KAPLAN:
                sigma_c = 0.10 + (ns / 800) ** 1.5
            elif self.turbine_type == TurbineType.PELTON:
                sigma_c = 0.0  # Pelton不存在空化问题
            else:
                sigma_c = 0.05
            
            # 大气压（简化为10m水柱）
            P_atm = 10.0  # m
            
            # 汽化压力（20°C，简化为0.25m水柱）
            P_v = 0.25  # m
            
            # 允许吸出高度
            Hs_max = P_atm - P_v - sigma_c * H
            
            # 实际吸出高度（相对于下游水位）
            Hs_actual = elevation  # 简化
            
            # 空化余量
            cavitation_margin = Hs_max - Hs_actual
            
            # 是否安全
            is_safe = cavitation_margin > 0.5  # 至少0.5m余量
        else:
            ns = 0
            sigma_c = 0
            Hs_max = 0
            cavitation_margin = 0
            is_safe = True
        
        return {
            'specific_speed': ns,
            'critical_sigma': sigma_c,
            'max_suction_height': Hs_max,
            'cavitation_margin': cavitation_margin,
            'is_safe': is_safe
        }
    
    def start(self, head: float, flow: float):
        """启动水轮机"""
        self.is_running = True
        self.current_head = head
        self.current_flow = flow
        power, efficiency = self.compute_power(head, flow)
        self.current_power = power
        self.current_efficiency = efficiency
        
        # 记录
        self.head_history.append(head)
        self.flow_history.append(flow)
        self.power_history.append(power)
        self.efficiency_history.append(efficiency)
    
    def stop(self):
        """停止水轮机"""
        self.is_running = False
        self.current_flow = 0.0
        self.current_power = 0.0
    
    def get_status(self) -> Dict:
        """获取状态"""
        return {
            'name': self.name,
            'type': self.turbine_type.value,
            'is_running': self.is_running,
            'num_units': self.num_units,
            'current_head': self.current_head,
            'current_flow': self.current_flow,
            'current_power': self.current_power,
            'current_efficiency': self.current_efficiency,
            'rated_power': self.char.rated_power,
            'rated_head': self.char.rated_head,
            'rated_flow': self.char.rated_flow
        }


# 标准水轮机参数库
STANDARD_TURBINES = {
    'francis_small': TurbineCharacteristics(
        rated_head=50.0,
        rated_flow=10.0,
        rated_power=4.5,
        rated_efficiency=0.90,
        rated_speed=500.0,
        min_head=30.0,
        max_head=70.0,
        min_flow=3.0,
        max_flow=12.0
    ),
    'francis_medium': TurbineCharacteristics(
        rated_head=100.0,
        rated_flow=50.0,
        rated_power=45.0,
        rated_efficiency=0.93,
        rated_speed=375.0,
        min_head=70.0,
        max_head=130.0,
        min_flow=15.0,
        max_flow=60.0
    ),
    'kaplan_small': TurbineCharacteristics(
        rated_head=20.0,
        rated_flow=50.0,
        rated_power=9.0,
        rated_efficiency=0.91,
        rated_speed=300.0,
        min_head=12.0,
        max_head=28.0,
        min_flow=20.0,
        max_flow=60.0
    ),
    'pelton_high': TurbineCharacteristics(
        rated_head=500.0,
        rated_flow=5.0,
        rated_power=22.5,
        rated_efficiency=0.90,
        rated_speed=500.0,
        min_head=350.0,
        max_head=600.0,
        min_flow=2.0,
        max_flow=6.0
    )
}


# 使用示例
if __name__ == "__main__":
    print("="*60)
    print("水轮机模块测试")
    print("="*60)
    
    # 1. Francis混流式水轮机
    print("\n1. Francis混流式水轮机")
    print("-"*60)
    
    francis = Turbine(
        name="Francis-01",
        position=0.0,
        turbine_type=TurbineType.FRANCIS,
        characteristics=STANDARD_TURBINES['francis_medium'],
        num_units=2
    )
    
    print(f"水轮机: {francis.name}")
    print(f"类型: {francis.turbine_type.value}")
    print(f"额定: H={francis.char.rated_head}m, "
          f"Q={francis.char.rated_flow}m³/s, "
          f"P={francis.char.rated_power}MW")
    
    # 不同工况测试
    print(f"\n不同工况测试:")
    for h, q in [(80, 40), (100, 50), (120, 55)]:
        P, eta = francis.compute_power(h, q)
        print(f"  H={h}m, Q={q}m³/s -> "
              f"P={P:.2f}MW, η={eta*100:.1f}%")
    
    # 最优流量
    print(f"\n最优运行点:")
    for h in [80, 100, 120]:
        Q_opt = francis.compute_optimal_flow(h)
        P_opt, eta_opt = francis.compute_power(h, Q_opt)
        print(f"  H={h}m -> Q_opt={Q_opt:.1f}m³/s, "
              f"P={P_opt:.2f}MW, η={eta_opt*100:.1f}%")
    
    # 空化校核
    cav = francis.check_cavitation(100, -2.0)
    print(f"\n空化校核 (H=100m, 安装高程=-2.0m):")
    print(f"  比转速: {cav['specific_speed']:.1f}")
    print(f"  临界空化系数: {cav['critical_sigma']:.3f}")
    print(f"  允许吸出高度: {cav['max_suction_height']:.2f}m")
    print(f"  空化余量: {cav['cavitation_margin']:.2f}m")
    print(f"  是否安全: {'是' if cav['is_safe'] else '否'}")
    
    # 2. Kaplan轴流式水轮机
    print("\n2. Kaplan轴流式水轮机")
    print("-"*60)
    
    kaplan = Turbine(
        name="Kaplan-01",
        position=0.0,
        turbine_type=TurbineType.KAPLAN,
        characteristics=STANDARD_TURBINES['kaplan_small'],
        num_units=3
    )
    
    print(f"水轮机: {kaplan.name}")
    print(f"类型: {kaplan.turbine_type.value}")
    print(f"额定: H={kaplan.char.rated_head}m, "
          f"Q={kaplan.char.rated_flow}m³/s, "
          f"P={kaplan.char.rated_power}MW")
    
    print(f"\n不同工况测试:")
    for h, q in [(15, 40), (20, 50), (25, 55)]:
        P, eta = kaplan.compute_power(h, q)
        print(f"  H={h}m, Q={q}m³/s -> "
              f"P={P:.2f}MW, η={eta*100:.1f}%")
    
    # 3. Pelton冲击式水轮机
    print("\n3. Pelton冲击式水轮机")
    print("-"*60)
    
    pelton = Turbine(
        name="Pelton-01",
        position=0.0,
        turbine_type=TurbineType.PELTON,
        characteristics=STANDARD_TURBINES['pelton_high'],
        num_units=1
    )
    
    print(f"水轮机: {pelton.name}")
    print(f"类型: {pelton.turbine_type.value}")
    print(f"额定: H={pelton.char.rated_head}m, "
          f"Q={pelton.char.rated_flow}m³/s, "
          f"P={pelton.char.rated_power}MW")
    
    print(f"\n不同工况测试:")
    for h, q in [(450, 4.5), (500, 5.0), (550, 5.3)]:
        P, eta = pelton.compute_power(h, q)
        print(f"  H={h}m, Q={q}m³/s -> "
              f"P={P:.2f}MW, η={eta*100:.1f}%")
    
    print(f"\n状态: {francis.get_status()}")
    
    print("\n" + "="*60)
    print("测试完成")
    print("="*60)
