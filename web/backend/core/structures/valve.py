#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Valve Module
阀门模块

对标商业软件的阀门建模功能

Author: HydroClaude Team
Date: 2025-11-15
"""

import numpy as np
from typing import Dict, Optional, Tuple
from enum import Enum


class ValveType(Enum):
    """阀门类型"""
    BUTTERFLY = "butterfly"    # 蝶阀
    BALL = "ball"              # 球阀
    GATE = "gate"              # 闸阀
    GLOBE = "globe"            # 截止阀
    CHECK = "check"            # 止回阀
    NEEDLE = "needle"          # 针阀
    CONE = "cone"              # 锥阀


class ValveState(Enum):
    """阀门状态"""
    FULLY_OPEN = "fully_open"
    PARTIALLY_OPEN = "partially_open"
    FULLY_CLOSED = "fully_closed"
    OPENING = "opening"
    CLOSING = "closing"


class Valve:
    """
    阀门类
    
    功能：
    1. 多种阀门类型
    2. 流量系数计算
    3. 水头损失
    4. 启闭特性
    5. 空化预测
    6. 水锤防护
    
    参考商业软件：
    - HEC-RAS: 不支持
    - MIKE: Valve（有限）
    - InfoWorks: Valve
    """
    
    def __init__(
        self,
        name: str,
        position: float,
        valve_type: ValveType,
        diameter: float,
        # 流量系数
        cv_full_open: float = 100.0,  # 全开流量系数
        # 启闭时间
        opening_time: float = 60.0,    # 开启时间 (s)
        closing_time: float = 60.0     # 关闭时间 (s)
    ):
        """
        初始化阀门
        
        Args:
            name: 阀门名称
            position: 位置 (m)
            valve_type: 阀门类型
            diameter: 直径 (m)
            cv_full_open: 全开流量系数
            opening_time: 开启时间 (s)
            closing_time: 关闭时间 (s)
        """
        self.name = name
        self.position = position
        self.valve_type = valve_type
        self.diameter = diameter
        self.cv_full_open = cv_full_open
        self.opening_time = opening_time
        self.closing_time = closing_time
        
        # 阀门开度 (0-1)
        self.opening = 1.0  # 默认全开
        
        # 运行状态
        self.state = ValveState.FULLY_OPEN
        
        # 历史记录
        self.opening_history = []
        self.flow_history = []
        self.headloss_history = []
    
    def get_flow_coefficient(self, opening: float) -> float:
        """
        获取流量系数
        
        Args:
            opening: 开度 (0-1)
            
        Returns:
            流量系数
        """
        if opening <= 0:
            return 0.0
        
        if self.valve_type == ValveType.BUTTERFLY:
            # 蝶阀：线性特性较好，但小开度时阻力大
            if opening < 0.2:
                cv = self.cv_full_open * (opening / 0.2) ** 2
            else:
                cv = self.cv_full_open * opening ** 1.5
        
        elif self.valve_type == ValveType.BALL:
            # 球阀：快开特性，小开度流量大
            cv = self.cv_full_open * opening ** 0.5
        
        elif self.valve_type == ValveType.GATE:
            # 闸阀：线性特性
            cv = self.cv_full_open * opening
        
        elif self.valve_type == ValveType.GLOBE:
            # 截止阀：抛物线特性
            cv = self.cv_full_open * opening ** 2
        
        elif self.valve_type == ValveType.NEEDLE:
            # 针阀：精细调节，开度3次方
            cv = self.cv_full_open * opening ** 3
        
        elif self.valve_type == ValveType.CONE:
            # 锥阀：类似球阀
            cv = self.cv_full_open * opening ** 0.7
        
        else:
            # 默认线性
            cv = self.cv_full_open * opening
        
        return cv
    
    def compute_headloss(
        self,
        flow: float,
        opening: Optional[float] = None
    ) -> float:
        """
        计算水头损失
        
        Args:
            flow: 流量 (m³/s)
            opening: 开度 (0-1)，None表示使用当前开度
            
        Returns:
            水头损失 (m)
        """
        if opening is None:
            opening = self.opening
        
        if opening <= 0 or flow <= 0:
            return 0.0
        
        # 流量系数
        cv = self.get_flow_coefficient(opening)
        
        if cv <= 0:
            return 1e6  # 接近无穷大
        
        # 阀门面积
        A = np.pi * (self.diameter / 2) ** 2
        
        # 流速
        V = flow / A
        
        # 局部阻力系数
        # h = K * V²/(2g)
        # K = (A/Cv)²
        K = (A / cv) ** 2 if cv > 0 else 1e6
        
        g = 9.81
        h = K * V ** 2 / (2 * g)
        
        return h
    
    def compute_discharge(
        self,
        h_upstream: float,
        h_downstream: float,
        opening: Optional[float] = None
    ) -> float:
        """
        计算过阀流量
        
        Args:
            h_upstream: 上游水头 (m)
            h_downstream: 下游水头 (m)
            opening: 开度 (0-1)
            
        Returns:
            流量 (m³/s)
        """
        if opening is None:
            opening = self.opening
        
        if opening <= 0:
            return 0.0
        
        # 水头差
        delta_h = h_upstream - h_downstream
        
        if delta_h <= 0:
            return 0.0
        
        # 流量系数
        cv = self.get_flow_coefficient(opening)
        
        if cv <= 0:
            return 0.0
        
        # 阀门面积
        A = np.pi * (self.diameter / 2) ** 2
        
        # 流量公式：Q = Cv * sqrt(2g * dH)
        g = 9.81
        Q = cv * np.sqrt(2 * g * delta_h)
        
        return Q
    
    def set_opening(self, target_opening: float, dt: float = 1.0):
        """
        设置阀门开度（考虑启闭时间）
        
        Args:
            target_opening: 目标开度 (0-1)
            dt: 时间步长 (s)
        """
        target_opening = max(0.0, min(1.0, target_opening))
        
        if target_opening > self.opening:
            # 开启
            max_change = dt / self.opening_time
            self.opening = min(self.opening + max_change, target_opening)
            
            if self.opening >= 1.0:
                self.state = ValveState.FULLY_OPEN
            else:
                self.state = ValveState.OPENING
        
        elif target_opening < self.opening:
            # 关闭
            max_change = dt / self.closing_time
            self.opening = max(self.opening - max_change, target_opening)
            
            if self.opening <= 0.0:
                self.state = ValveState.FULLY_CLOSED
            else:
                self.state = ValveState.CLOSING
        
        else:
            # 不变
            if self.opening >= 1.0:
                self.state = ValveState.FULLY_OPEN
            elif self.opening <= 0.0:
                self.state = ValveState.FULLY_CLOSED
            else:
                self.state = ValveState.PARTIALLY_OPEN
    
    def check_cavitation(
        self,
        flow: float,
        p_upstream: float,
        p_downstream: float
    ) -> Dict:
        """
        空化校核
        
        Args:
            flow: 流量 (m³/s)
            p_upstream: 上游压力 (m水柱)
            p_downstream: 下游压力 (m水柱)
            
        Returns:
            空化参数
        """
        # 汽化压力（20°C，简化为0.25m水柱）
        p_v = 0.25
        
        # 阀门最小压力点（简化为下游压力）
        p_min = p_downstream
        
        # 空化指数
        # sigma = (p_min - p_v) / (p_up - p_down)
        delta_p = p_upstream - p_downstream
        
        if delta_p > 0:
            sigma = (p_min - p_v) / delta_p
            
            # 临界空化指数（经验值）
            if self.valve_type == ValveType.BUTTERFLY:
                sigma_c = 2.0
            elif self.valve_type == ValveType.BALL:
                sigma_c = 1.5
            elif self.valve_type == ValveType.GLOBE:
                sigma_c = 2.5
            else:
                sigma_c = 2.0
            
            # 空化风险
            if sigma < sigma_c / 2:
                risk = "high"
            elif sigma < sigma_c:
                risk = "moderate"
            else:
                risk = "low"
        else:
            sigma = 999.0
            sigma_c = 2.0
            risk = "none"
        
        return {
            'cavitation_index': sigma,
            'critical_index': sigma_c,
            'risk_level': risk,
            'is_safe': sigma > sigma_c
        }
    
    def get_status(self) -> Dict:
        """获取状态"""
        return {
            'name': self.name,
            'type': self.valve_type.value,
            'state': self.state.value,
            'opening': self.opening,
            'diameter': self.diameter,
            'cv_full_open': self.cv_full_open,
            'current_cv': self.get_flow_coefficient(self.opening)
        }


# 使用示例
if __name__ == "__main__":
    print("="*60)
    print("阀门模块测试")
    print("="*60)
    
    # 1. 蝶阀
    print("\n1. 蝶阀 (Butterfly Valve)")
    print("-"*60)
    
    butterfly = Valve(
        name="BV-001",
        position=100.0,
        valve_type=ValveType.BUTTERFLY,
        diameter=1.5,
        cv_full_open=200.0,
        closing_time=30.0
    )
    
    print(f"阀门: {butterfly.name}")
    print(f"类型: {butterfly.valve_type.value}")
    print(f"直径: {butterfly.diameter}m")
    
    print(f"\n不同开度的流量系数:")
    for opening in [0.2, 0.4, 0.6, 0.8, 1.0]:
        cv = butterfly.get_flow_coefficient(opening)
        print(f"  开度={opening*100:.0f}% -> Cv={cv:.1f}")
    
    print(f"\n不同开度的水头损失 (Q=1.0 m³/s):")
    Q_test = 1.0
    for opening in [0.4, 0.6, 0.8, 1.0]:
        h_loss = butterfly.compute_headloss(Q_test, opening)
        print(f"  开度={opening*100:.0f}% -> h_loss={h_loss:.3f}m")
    
    # 2. 球阀
    print("\n2. 球阀 (Ball Valve)")
    print("-"*60)
    
    ball = Valve(
        name="BV-002",
        position=200.0,
        valve_type=ValveType.BALL,
        diameter=1.0,
        cv_full_open=150.0
    )
    
    print(f"阀门: {ball.name}")
    print(f"类型: {ball.valve_type.value}")
    
    print(f"\n不同开度的流量系数 (快开特性):")
    for opening in [0.2, 0.4, 0.6, 0.8, 1.0]:
        cv = ball.get_flow_coefficient(opening)
        print(f"  开度={opening*100:.0f}% -> Cv={cv:.1f}")
    
    # 3. 闸阀
    print("\n3. 闸阀 (Gate Valve)")
    print("-"*60)
    
    gate = Valve(
        name="GV-001",
        position=300.0,
        valve_type=ValveType.GATE,
        diameter=2.0,
        cv_full_open=300.0
    )
    
    print(f"阀门: {gate.name}")
    print(f"类型: {gate.valve_type.value}")
    
    print(f"\n不同开度的流量系数 (线性特性):")
    for opening in [0.2, 0.4, 0.6, 0.8, 1.0]:
        cv = gate.get_flow_coefficient(opening)
        print(f"  开度={opening*100:.0f}% -> Cv={cv:.1f}")
    
    # 4. 过阀流量计算
    print("\n4. 过阀流量计算")
    print("-"*60)
    
    print(f"\n蝶阀 (D=1.5m, 不同开度):")
    h_up, h_down = 10.0, 5.0
    for opening in [0.4, 0.6, 0.8, 1.0]:
        Q = butterfly.compute_discharge(h_up, h_down, opening)
        print(f"  开度={opening*100:.0f}%, dH={h_up-h_down}m -> Q={Q:.2f} m³/s")
    
    # 5. 启闭过程模拟
    print("\n5. 启闭过程模拟 (关闭30秒)")
    print("-"*60)
    
    butterfly.opening = 1.0
    print(f"初始状态: 开度={butterfly.opening*100:.0f}%, 状态={butterfly.state.value}")
    
    for t in [0, 10, 20, 30]:
        butterfly.set_opening(0.0, dt=10.0)
        print(f"t={t:2d}s: 开度={butterfly.opening*100:.1f}%, 状态={butterfly.state.value}")
    
    # 6. 空化校核
    print("\n6. 空化校核")
    print("-"*60)
    
    cav = butterfly.check_cavitation(
        flow=2.0,
        p_upstream=50.0,
        p_downstream=30.0
    )
    print(f"空化指数: {cav['cavitation_index']:.2f}")
    print(f"临界值: {cav['critical_index']:.2f}")
    print(f"风险等级: {cav['risk_level']}")
    print(f"是否安全: {'是' if cav['is_safe'] else '否'}")
    
    print(f"\n状态: {butterfly.get_status()}")
    
    print("\n" + "="*60)
    print("测试完成")
    print("="*60)
