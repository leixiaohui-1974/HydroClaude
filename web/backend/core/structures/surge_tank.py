#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Surge Tank Module
调压井模块

对标商业软件的调压井建模功能

Author: HydroClaude Team
Date: 2025-11-15
"""

import numpy as np
from typing import Dict, Optional, List
from enum import Enum


class SurgeTankType(Enum):
    """调压井类型"""
    SIMPLE = "simple"              # 简单调压井
    DIFFERENTIAL = "differential"  # 差动调压井
    RESTRICTED = "restricted"      # 阻抗调压井
    ONE_WAY = "one_way"           # 单向调压井


class SurgeTank:
    """
    调压井类
    
    功能：
    1. 水位波动计算
    2. 涌浪分析
    3. 阻抗孔设计
    4. 稳定性分析
    5. 极值水位预测
    
    参考商业软件：
    - HEC-RAS: 不支持
    - MIKE: Surge Tank（有限）
    """
    
    def __init__(
        self,
        name: str,
        position: float,
        tank_type: SurgeTankType,
        # 几何参数
        cross_section_area: float,   # 调压井断面积 (m²)
        initial_level: float,         # 初始水位 (m)
        # 阻抗孔参数（可选）
        orifice_area: Optional[float] = None,  # 阻抗孔面积 (m²)
        orifice_coeff: float = 0.8              # 阻抗孔流量系数
    ):
        """
        初始化调压井
        
        Args:
            name: 调压井名称
            position: 位置 (m)
            tank_type: 调压井类型
            cross_section_area: 调压井断面积 (m²)
            initial_level: 初始水位 (m)
            orifice_area: 阻抗孔面积 (m²)
            orifice_coeff: 阻抗孔流量系数
        """
        self.name = name
        self.position = position
        self.tank_type = tank_type
        self.area = cross_section_area
        self.level = initial_level
        self.orifice_area = orifice_area
        self.orifice_coeff = orifice_coeff
        
        # 运行状态
        self.velocity = 0.0  # 调压井水位变化速度 (m/s)
        
        # 历史记录
        self.level_history = [initial_level]
        self.velocity_history = [0.0]
        self.time_history = [0.0]
    
    def compute_flow_through_orifice(
        self,
        h_upstream: float,
        h_tank: float
    ) -> float:
        """
        计算通过阻抗孔的流量
        
        Args:
            h_upstream: 上游水位 (m)
            h_tank: 调压井水位 (m)
            
        Returns:
            流量 (m³/s)
        """
        if self.orifice_area is None:
            # 无阻抗孔，假设自由流动
            return 0.0
        
        g = 9.81
        
        # 水头差
        dh = h_upstream - h_tank
        
        if abs(dh) < 0.001:
            return 0.0
        
        # 流向
        sign = 1 if dh > 0 else -1
        
        # 孔口流量
        Q = sign * self.orifice_coeff * self.orifice_area * np.sqrt(2 * g * abs(dh))
        
        return Q
    
    def update(
        self,
        Q_in: float,
        Q_out: float,
        dt: float
    ) -> float:
        """
        更新调压井水位（一个时间步）
        
        Args:
            Q_in: 入流流量 (m³/s)
            Q_out: 出流流量 (m³/s)
            dt: 时间步长 (s)
            
        Returns:
            新水位 (m)
        """
        # 净入流
        Q_net = Q_in - Q_out
        
        # 水位变化速度
        dh_dt = Q_net / self.area if self.area > 0 else 0
        
        # 更新水位
        self.level += dh_dt * dt
        self.velocity = dh_dt
        
        # 记录
        self.level_history.append(self.level)
        self.velocity_history.append(self.velocity)
        self.time_history.append(self.time_history[-1] + dt)
        
        return self.level
    
    def analyze_surge(
        self,
        initial_flow: float,
        final_flow: float,
        transition_time: float,
        tunnel_length: float,
        tunnel_area: float,
        tunnel_friction: float = 0.015
    ) -> Dict:
        """
        涌浪分析（简化）
        
        Args:
            initial_flow: 初始流量 (m³/s)
            final_flow: 最终流量 (m³/s)
            transition_time: 过渡时间 (s)
            tunnel_length: 引水隧洞长度 (m)
            tunnel_area: 引水隧洞面积 (m²)
            tunnel_friction: 摩阻系数
            
        Returns:
            涌浪分析结果
        """
        g = 9.81
        
        # Thoma临界断面
        A_cr = (tunnel_length * tunnel_area) / (2.5 * tunnel_friction * self.area)
        
        # 是否满足稳定条件
        is_stable = self.area > A_cr
        
        # 估算最大涌浪高度（简化公式）
        delta_Q = final_flow - initial_flow
        V = initial_flow / tunnel_area if tunnel_area > 0 else 0
        
        # 最大升高（拒动工况）
        if delta_Q < 0:  # 负荷突增
            z_max = abs(delta_Q) * V / (g * self.area) * tunnel_length
        else:  # 负荷突减
            z_max = delta_Q * V / (g * self.area) * tunnel_length
        
        # 最低水位（空载工况）
        z_min = -z_max * 0.8  # 简化估算
        
        # 涌浪周期
        T = 2 * np.pi * np.sqrt(tunnel_length / g) if tunnel_length > 0 else 0
        
        return {
            'critical_area': A_cr,
            'is_stable': is_stable,
            'max_surge_height': z_max,
            'min_surge_height': z_min,
            'surge_period': T,
            'max_level': self.level + z_max,
            'min_level': self.level + z_min
        }
    
    def get_status(self) -> Dict:
        """获取状态"""
        return {
            'name': self.name,
            'type': self.tank_type.value,
            'position': self.position,
            'area': self.area,
            'current_level': self.level,
            'velocity': self.velocity,
            'orifice_area': self.orifice_area
        }


# 使用示例
if __name__ == "__main__":
    print("="*60)
    print("调压井模块测试")
    print("="*60)
    
    # 1. 简单调压井
    print("\n1. 简单调压井")
    print("-"*60)
    
    surge_tank = SurgeTank(
        name="ST-001",
        position=5000.0,
        tank_type=SurgeTankType.SIMPLE,
        cross_section_area=200.0,
        initial_level=100.0
    )
    
    print(f"调压井: {surge_tank.name}")
    print(f"类型: {surge_tank.tank_type.value}")
    print(f"断面积: {surge_tank.area}m²")
    print(f"初始水位: {surge_tank.level}m")
    
    # 2. 水位变化模拟
    print(f"\n2. 水位变化模拟（负荷突增）")
    print("-"*60)
    
    dt = 1.0  # 时间步长1秒
    Q_in = 50.0  # 入流
    
    print(f"时间(s)  入流(m³/s)  出流(m³/s)  水位(m)  速度(m/s)")
    
    for t in range(0, 11):
        if t < 5:
            Q_out = 50.0  # 稳定运行
        else:
            Q_out = 30.0  # 负荷突增，出流减少
        
        surge_tank.update(Q_in, Q_out, dt)
        
        print(f"{t:3d}      {Q_in:5.1f}       {Q_out:5.1f}       "
              f"{surge_tank.level:6.2f}   {surge_tank.velocity:6.3f}")
    
    # 3. 涌浪分析
    print(f"\n3. 涌浪分析")
    print("-"*60)
    
    surge_analysis = surge_tank.analyze_surge(
        initial_flow=50.0,
        final_flow=30.0,
        transition_time=10.0,
        tunnel_length=3000.0,
        tunnel_area=15.0,
        tunnel_friction=0.015
    )
    
    print(f"临界断面积: {surge_analysis['critical_area']:.1f}m²")
    print(f"实际断面积: {surge_tank.area:.1f}m²")
    print(f"是否稳定: {'是' if surge_analysis['is_stable'] else '否'}")
    print(f"最大涌浪高度: {surge_analysis['max_surge_height']:.2f}m")
    print(f"最大水位: {surge_analysis['max_level']:.2f}m")
    print(f"最低水位: {surge_analysis['min_level']:.2f}m")
    print(f"涌浪周期: {surge_analysis['surge_period']:.1f}s")
    
    # 4. 阻抗调压井
    print(f"\n4. 阻抗调压井")
    print("-"*60)
    
    restricted_tank = SurgeTank(
        name="ST-002",
        position=5000.0,
        tank_type=SurgeTankType.RESTRICTED,
        cross_section_area=150.0,
        initial_level=100.0,
        orifice_area=3.0,
        orifice_coeff=0.8
    )
    
    print(f"调压井: {restricted_tank.name}")
    print(f"类型: {restricted_tank.tank_type.value}")
    print(f"阻抗孔面积: {restricted_tank.orifice_area}m²")
    
    # 测试通过阻抗孔的流量
    print(f"\n通过阻抗孔的流量:")
    for h_up in [105, 110, 115]:
        Q = restricted_tank.compute_flow_through_orifice(h_up, 100.0)
        print(f"  上游={h_up}m, 调压井=100m -> Q={Q:.2f}m³/s")
    
    print(f"\n状态: {surge_tank.get_status()}")
    
    print("\n" + "="*60)
    print("测试完成")
    print("="*60)
