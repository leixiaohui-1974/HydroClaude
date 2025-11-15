#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Hydropower Station Module
水电站模块

对标商业软件的水电站整体建模功能

Author: HydroClaude Team
Date: 2025-11-15
"""

import numpy as np
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass
from .turbine import Turbine, TurbineCharacteristics, TurbineType
from .valve import Valve, ValveType


@dataclass
class HydropowerConfig:
    """水电站配置"""
    # 基本信息
    name: str
    installed_capacity: float      # 装机容量 (MW)
    num_units: int                  # 机组数量
    
    # 水库参数
    normal_water_level: float       # 正常蓄水位 (m)
    dead_water_level: float         # 死水位 (m)
    design_water_level: float       # 设计水位 (m)
    
    # 引水系统
    intake_elevation: float         # 进水口高程 (m)
    
    # 尾水系统
    tailrace_elevation: float       # 尾水位高程 (m)
    
    # 以下为有默认值的字段
    intake_loss_coeff: float = 0.5  # 进水口损失系数
    
    # 压力管道
    penstock_length: float = 1000.0    # 压力管道长度 (m)
    penstock_diameter: float = 3.0     # 压力管道直径 (m)
    penstock_roughness: float = 0.0002 # 粗糙度 (m)
    
    # 尾水管
    tailrace_loss_coeff: float = 1.0 # 尾水管损失系数


class HydropowerStation:
    """
    水电站类
    
    功能：
    1. 多机组协调运行
    2. 水头-流量-功率计算
    3. 水力损失综合计算
    4. 经济运行优化
    5. 年发电量估算
    6. 调度策略
    
    参考商业软件：
    - RETScreen: 水电分析
    - HOMER: 水电优化
    - HydroCalc: 专业水电软件
    """
    
    def __init__(
        self,
        config: HydropowerConfig,
        turbines: List[Turbine],
        valves: Optional[List[Valve]] = None
    ):
        """
        初始化水电站
        
        Args:
            config: 水电站配置
            turbines: 水轮机列表
            valves: 阀门列表（可选）
        """
        self.config = config
        self.turbines = turbines
        self.valves = valves or []
        
        # 运行状态
        self.current_reservoir_level = config.normal_water_level
        self.current_tailrace_level = config.tailrace_elevation
        self.total_power = 0.0
        self.total_flow = 0.0
        
        # 历史记录
        self.power_history = []
        self.flow_history = []
        self.efficiency_history = []
    
    def compute_gross_head(self) -> float:
        """
        计算毛水头
        
        Returns:
            毛水头 (m)
        """
        H_gross = (self.current_reservoir_level - 
                   self.current_tailrace_level)
        return H_gross
    
    def compute_headloss(self, flow: float) -> Dict:
        """
        计算水头损失
        
        Args:
            flow: 总流量 (m³/s)
            
        Returns:
            各部分水头损失
        """
        g = 9.81
        
        # 1. 进水口损失
        A_intake = np.pi * (self.config.penstock_diameter / 2) ** 2
        V_intake = flow / A_intake if A_intake > 0 else 0
        h_intake = self.config.intake_loss_coeff * V_intake ** 2 / (2 * g)
        
        # 2. 压力管道沿程损失（Darcy-Weisbach）
        D = self.config.penstock_diameter
        L = self.config.penstock_length
        eps = self.config.penstock_roughness
        
        # Reynolds数
        nu = 1e-6  # 运动粘度 (m²/s)
        Re = V_intake * D / nu if nu > 0 else 1e6
        
        # 摩阻系数（Colebrook-White公式简化）
        if Re > 4000:
            # 湍流
            f = 0.25 / (np.log10(eps/(3.7*D) + 5.74/Re**0.9)) ** 2
        else:
            # 层流
            f = 64 / Re
        
        # 沿程损失
        h_friction = f * (L / D) * V_intake ** 2 / (2 * g)
        
        # 3. 阀门损失
        h_valves = 0.0
        if self.valves:
            for valve in self.valves:
                h_valves += valve.compute_headloss(flow)
        
        # 4. 尾水管损失
        h_tailrace = self.config.tailrace_loss_coeff * V_intake ** 2 / (2 * g)
        
        # 总损失
        h_total = h_intake + h_friction + h_valves + h_tailrace
        
        return {
            'intake': h_intake,
            'friction': h_friction,
            'valves': h_valves,
            'tailrace': h_tailrace,
            'total': h_total
        }
    
    def compute_net_head(self, flow: float) -> float:
        """
        计算净水头
        
        Args:
            flow: 流量 (m³/s)
            
        Returns:
            净水头 (m)
        """
        H_gross = self.compute_gross_head()
        losses = self.compute_headloss(flow)
        H_net = H_gross - losses['total']
        
        return max(H_net, 0.0)
    
    def compute_station_output(
        self,
        target_power: Optional[float] = None,
        target_flow: Optional[float] = None
    ) -> Dict:
        """
        计算电站出力
        
        Args:
            target_power: 目标功率 (MW)
            target_flow: 目标流量 (m³/s)
            
        Returns:
            运行参数
        """
        if target_flow is not None:
            # 给定流量，计算功率
            Q = target_flow
        elif target_power is not None:
            # 给定功率，迭代计算流量
            # 简化：假设线性关系
            Q_est = target_power / (9.81 * self.compute_gross_head() * 0.9) * 1000
            Q = Q_est
        else:
            # 额定工况
            Q = sum(t.char.rated_flow for t in self.turbines)
        
        # 净水头
        H_net = self.compute_net_head(Q)
        
        # 分配到各机组
        num_running = len([t for t in self.turbines if t.is_running])
        if num_running == 0:
            num_running = len(self.turbines)  # 假设全部运行
        
        Q_unit = Q / num_running
        
        # 计算各机组功率和效率
        total_power = 0.0
        total_efficiency = 0.0
        
        for i, turbine in enumerate(self.turbines):
            if i < num_running:
                P, eta = turbine.compute_power(H_net, Q_unit)
                total_power += P
                total_efficiency += eta
            else:
                P, eta = 0, 0
        
        avg_efficiency = total_efficiency / num_running if num_running > 0 else 0
        
        self.total_power = total_power
        self.total_flow = Q
        
        # 记录
        self.power_history.append(total_power)
        self.flow_history.append(Q)
        self.efficiency_history.append(avg_efficiency)
        
        return {
            'gross_head': self.compute_gross_head(),
            'net_head': H_net,
            'headloss': self.compute_headloss(Q),
            'flow': Q,
            'power': total_power,
            'efficiency': avg_efficiency,
            'num_units_running': num_running
        }
    
    def optimize_operation(self, available_flow: float) -> Dict:
        """
        优化运行（经济运行）
        
        Args:
            available_flow: 可用流量 (m³/s)
            
        Returns:
            最优运行方案
        """
        # 简化：尝试不同机组组合，找到最高效率
        best_efficiency = 0.0
        best_result = None
        
        max_units = len(self.turbines)
        
        for num_units in range(1, max_units + 1):
            Q_unit = available_flow / num_units
            
            # 检查是否在运行范围内
            if (Q_unit < self.turbines[0].char.min_flow or
                Q_unit > self.turbines[0].char.max_flow):
                continue
            
            # 计算效率
            H_net = self.compute_net_head(available_flow)
            P_unit, eta_unit = self.turbines[0].compute_power(H_net, Q_unit)
            
            if eta_unit > best_efficiency:
                best_efficiency = eta_unit
                best_result = {
                    'num_units': num_units,
                    'flow_per_unit': Q_unit,
                    'power_per_unit': P_unit,
                    'total_power': P_unit * num_units,
                    'efficiency': eta_unit
                }
        
        return best_result or {
            'num_units': 0,
            'flow_per_unit': 0,
            'power_per_unit': 0,
            'total_power': 0,
            'efficiency': 0
        }
    
    def estimate_annual_energy(
        self,
        flow_duration_curve: List[Tuple[float, float]]
    ) -> Dict:
        """
        估算年发电量
        
        Args:
            flow_duration_curve: 流量历时曲线 [(流量, 保证率), ...]
            
        Returns:
            年发电量估算
        """
        total_energy = 0.0  # MWh
        
        hours_per_year = 8760
        
        for i in range(len(flow_duration_curve) - 1):
            Q1, p1 = flow_duration_curve[i]
            Q2, p2 = flow_duration_curve[i + 1]
            
            # 平均流量
            Q_avg = (Q1 + Q2) / 2
            
            # 持续小时数
            hours = (p2 - p1) * hours_per_year / 100
            
            # 计算功率
            result = self.compute_station_output(target_flow=Q_avg)
            P = result['power']
            
            # 电量
            E = P * hours
            total_energy += E
        
        # 利用小时数
        utilization_hours = (total_energy / self.config.installed_capacity 
                            if self.config.installed_capacity > 0 else 0)
        
        # 平均负荷因子
        load_factor = utilization_hours / hours_per_year
        
        return {
            'annual_energy': total_energy,  # MWh/年
            'utilization_hours': utilization_hours,  # 小时/年
            'load_factor': load_factor,  # 0-1
            'capacity_factor': load_factor  # 同上
        }
    
    def get_status(self) -> Dict:
        """获取状态"""
        return {
            'name': self.config.name,
            'installed_capacity': self.config.installed_capacity,
            'num_units': self.config.num_units,
            'reservoir_level': self.current_reservoir_level,
            'tailrace_level': self.current_tailrace_level,
            'gross_head': self.compute_gross_head(),
            'current_power': self.total_power,
            'current_flow': self.total_flow,
            'turbines_status': [t.get_status() for t in self.turbines]
        }


# 使用示例
if __name__ == "__main__":
    from turbine import STANDARD_TURBINES
    
    print("="*60)
    print("水电站模块测试")
    print("="*60)
    
    # 创建水电站配置
    config = HydropowerConfig(
        name="Test Hydropower Station",
        installed_capacity=90.0,  # MW
        num_units=2,
        normal_water_level=150.0,
        dead_water_level=140.0,
        design_water_level=148.0,
        intake_elevation=145.0,
        penstock_length=500.0,
        penstock_diameter=3.5,
        tailrace_elevation=50.0
    )
    
    # 创建水轮机
    turbines = [
        Turbine(
            name=f"Unit-{i+1}",
            position=0.0,
            turbine_type=TurbineType.FRANCIS,
            characteristics=STANDARD_TURBINES['francis_medium'],
            num_units=1
        )
        for i in range(2)
    ]
    
    # 创建水电站
    station = HydropowerStation(
        config=config,
        turbines=turbines
    )
    
    print(f"\n水电站: {station.config.name}")
    print(f"装机容量: {station.config.installed_capacity}MW")
    print(f"机组数量: {station.config.num_units}")
    print(f"毛水头: {station.compute_gross_head():.1f}m")
    
    # 1. 不同流量下的出力计算
    print(f"\n1. 不同流量下的出力")
    print("-"*60)
    
    for Q in [60, 80, 100]:
        result = station.compute_station_output(target_flow=Q)
        print(f"\nQ={Q} m³/s:")
        print(f"  净水头: {result['net_head']:.2f}m")
        print(f"  总损失: {result['headloss']['total']:.2f}m")
        print(f"  输出功率: {result['power']:.2f}MW")
        print(f"  平均效率: {result['efficiency']*100:.1f}%")
    
    # 2. 经济运行优化
    print(f"\n2. 经济运行优化")
    print("-"*60)
    
    for Q_available in [40, 70, 100]:
        optimal = station.optimize_operation(Q_available)
        print(f"\n可用流量={Q_available} m³/s:")
        print(f"  最优机组数: {optimal['num_units']}")
        print(f"  单机流量: {optimal['flow_per_unit']:.1f}m³/s")
        print(f"  单机功率: {optimal['power_per_unit']:.2f}MW")
        print(f"  总功率: {optimal['total_power']:.2f}MW")
        print(f"  效率: {optimal['efficiency']*100:.1f}%")
    
    # 3. 年发电量估算
    print(f"\n3. 年发电量估算")
    print("-"*60)
    
    # 简化的流量历时曲线（保证率）
    flow_duration = [
        (120, 0),    # 0%保证率（最大流量）
        (100, 20),   # 20%保证率
        (80, 50),    # 50%保证率
        (60, 75),    # 75%保证率
        (40, 90),    # 90%保证率
        (30, 100)    # 100%保证率（最小流量）
    ]
    
    energy = station.estimate_annual_energy(flow_duration)
    print(f"年发电量: {energy['annual_energy']/1000:.1f} GWh")
    print(f"利用小时数: {energy['utilization_hours']:.0f} h/年")
    print(f"负荷因子: {energy['load_factor']*100:.1f}%")
    
    print(f"\n状态: {station.get_status()}")
    
    print("\n" + "="*60)
    print("测试完成")
    print("="*60)
