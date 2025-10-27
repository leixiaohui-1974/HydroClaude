#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
泵站模型 - 完整实现

支持多种泵站类型和控制模式
Author: HydroClaude Development Team  
Date: 2025-10-27
"""

import numpy as np
from typing import Tuple, Optional
from scipy.interpolate import interp1d


class Pump:
    """泵站基类"""
    
    def __init__(self, position: float, width: float,
                 H_Q_curve: list, control_mode: str = 'constant_flow',
                 target_value: float = 10.0, g: float = 9.81):
        """
        初始化泵站
        
        Args:
            position: 位置 (m)
            width: 宽度 (m)
            H_Q_curve: H-Q特性曲线 [(Q1, H1), (Q2, H2), ...]
            control_mode: 控制模式 ('constant_flow', 'constant_head', 'variable_speed')
            target_value: 目标值
            g: 重力加速度
        """
        self.position = position
        self.width = width
        self.g = g
        self.control_mode = control_mode
        self.target_value = target_value
        self.is_running = True
        
        # 特性曲线
        self.H_Q_curve = sorted(H_Q_curve, key=lambda x: x[0])
        self.Q_values = np.array([p[0] for p in self.H_Q_curve])
        self.H_values = np.array([p[1] for p in self.H_Q_curve])
        
        # 插值函数
        self.H_of_Q = interp1d(self.Q_values, self.H_values, 
                              kind='linear', fill_value='extrapolate')
        self.Q_of_H = interp1d(self.H_values, self.Q_values,
                              kind='linear', fill_value='extrapolate')
        
        print(f"泵站: 位置={position}m, Q={self.Q_values[0]:.1f}-{self.Q_values[-1]:.1f}m³/s")
    
    def calculate_head(self, Q: float) -> float:
        """根据流量计算扬程"""
        if not self.is_running:
            return 0.0
        Q_clamped = np.clip(Q, self.Q_values[0], self.Q_values[-1])
        return float(self.H_of_Q(Q_clamped))
    
    def calculate_discharge(self, h_upstream: float, h_downstream: float,
                          t: Optional[float] = None) -> Tuple[float, str]:
        """计算泵站流量"""
        if not self.is_running:
            return 0.0, 'off'
        
        H_actual = h_downstream - h_upstream
        
        if self.control_mode == 'constant_flow':
            Q = self.target_value
            H_required = self.calculate_head(Q)
            if H_actual > H_required * 1.2:
                Q = float(self.Q_of_H(H_actual))
                status = 'head_limited'
            else:
                status = 'normal'
        elif self.control_mode == 'constant_head':
            Q = float(self.Q_of_H(self.target_value))
            status = 'normal'
        elif self.control_mode == 'variable_speed':
            Q_target = self.target_value
            H_design = self.calculate_head(Q_target)
            if H_design > 0.01:
                speed_ratio = np.sqrt(H_actual / H_design)
                speed_ratio = np.clip(speed_ratio, 0.5, 1.2)
                Q = Q_target * speed_ratio
            else:
                Q = Q_target
            status = 'variable_speed'
        else:
            Q = self.target_value
            status = 'normal'
        
        Q = np.clip(Q, 0.0, self.Q_values[-1])
        return Q, status


class CentrifugalPump(Pump):
    """离心泵"""
    
    @classmethod
    def from_design_point(cls, position: float, width: float,
                         Q_design: float, H_design: float,
                         control_mode: str = 'constant_flow',
                         target_value: Optional[float] = None, g: float = 9.81):
        """从设计点创建离心泵"""
        H0 = H_design * 1.15
        a = (H0 - H_design) / (Q_design ** 2)
        Q_points = np.linspace(0, Q_design * 1.2, 10)
        H_points = H0 - a * Q_points ** 2
        H_points = np.maximum(H_points, 0)
        H_Q_curve = list(zip(Q_points, H_points))
        
        if target_value is None:
            target_value = Q_design
        
        return cls(position, width, H_Q_curve, control_mode, target_value, g)


def main():
    """测试"""
    print("="*80)
    print("泵站模型测试")
    print("="*80)
    
    pump = CentrifugalPump.from_design_point(
        position=5000, width=10.0, Q_design=10.0, H_design=5.0
    )
    
    print("\n测试不同水位:")
    for h_up, h_down in [(1.0, 6.0), (2.0, 7.0), (3.0, 8.0)]:
        Q, status = pump.calculate_discharge(h_up, h_down)
        H = h_down - h_up
        print(f"  h_up={h_up:.1f}m, h_down={h_down:.1f}m, H={H:.1f}m")
        print(f"    → Q={Q:.2f}m³/s, 状态:{status}")
    
    print("\n✓ 泵站测试完成！")


if __name__ == '__main__':
    main()
