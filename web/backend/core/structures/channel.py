#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Channel/Canal Module
河道/渠道模块

包括：河流、渠道、管道等水流通道

Author: HydroClaude Team
Date: 2025-11-15
"""

import numpy as np
from typing import Dict, Optional, List
from enum import Enum


class ChannelType(Enum):
    """通道类型"""
    RIVER = "river"              # 天然河道
    CANAL = "canal"              # 人工渠道
    PIPE = "pipe"                # 压力管道
    TUNNEL = "tunnel"            # 隧洞
    PENSTOCK = "penstock"        # 压力钢管


class CrossSectionShape(Enum):
    """断面形状"""
    RECTANGULAR = "rectangular"   # 矩形
    TRAPEZOIDAL = "trapezoidal"  # 梯形
    CIRCULAR = "circular"         # 圆形
    PARABOLIC = "parabolic"      # 抛物线形
    NATURAL = "natural"           # 天然断面


class Channel:
    """
    河道/渠道类
    
    功能：
    1. 明渠/管道水流计算
    2. Manning公式
    3. 正常水深/临界水深
    4. 水面曲线
    5. 糙率影响
    
    参考商业软件：
    - HEC-RAS: River/Channel
    - MIKE: Channel
    """
    
    def __init__(
        self,
        name: str,
        channel_type: ChannelType,
        length: float,
        # 断面参数
        shape: CrossSectionShape,
        width: Optional[float] = None,      # 底宽 (m)
        depth: Optional[float] = None,      # 设计水深 (m)
        side_slope: float = 0.0,            # 边坡 (1:m)
        diameter: Optional[float] = None,   # 直径 (m, 圆形)
        # 水力参数
        slope: float = 0.001,               # 底坡
        manning_n: float = 0.025,           # Manning粗糙系数
        # 位置
        start_position: float = 0.0,
        end_position: Optional[float] = None
    ):
        """
        初始化河道/渠道
        
        Args:
            name: 名称
            channel_type: 通道类型
            length: 长度 (m)
            shape: 断面形状
            width: 底宽 (m)
            depth: 设计水深 (m)
            side_slope: 边坡系数
            diameter: 直径 (m)
            slope: 底坡
            manning_n: Manning系数
            start_position: 起点位置
            end_position: 终点位置
        """
        self.name = name
        self.channel_type = channel_type
        self.length = length
        self.shape = shape
        self.width = width
        self.depth = depth
        self.side_slope = side_slope
        self.diameter = diameter
        self.slope = slope
        self.manning_n = manning_n
        self.start_position = start_position
        self.end_position = end_position or (start_position + length)
        
        # 历史记录
        self.flow_history = []
        self.depth_history = []
    
    def compute_area(self, depth: float) -> float:
        """计算过流面积"""
        if self.shape == CrossSectionShape.RECTANGULAR:
            return self.width * depth
        
        elif self.shape == CrossSectionShape.TRAPEZOIDAL:
            return (self.width + self.side_slope * depth) * depth
        
        elif self.shape == CrossSectionShape.CIRCULAR:
            if depth >= self.diameter:
                return np.pi * (self.diameter / 2) ** 2
            else:
                # 部分满流
                r = self.diameter / 2
                theta = 2 * np.arccos((r - depth) / r)
                return r ** 2 * (theta - np.sin(theta)) / 2
        
        elif self.shape == CrossSectionShape.PARABOLIC:
            # 抛物线: y = k*x^2
            return 2/3 * self.width * depth
        
        return 0.0
    
    def compute_wetted_perimeter(self, depth: float) -> float:
        """计算湿周"""
        if self.shape == CrossSectionShape.RECTANGULAR:
            return self.width + 2 * depth
        
        elif self.shape == CrossSectionShape.TRAPEZOIDAL:
            side_length = depth * np.sqrt(1 + self.side_slope ** 2)
            return self.width + 2 * side_length
        
        elif self.shape == CrossSectionShape.CIRCULAR:
            if depth >= self.diameter:
                return np.pi * self.diameter
            else:
                r = self.diameter / 2
                theta = 2 * np.arccos((r - depth) / r)
                return r * theta
        
        elif self.shape == CrossSectionShape.PARABOLIC:
            # 简化
            return self.width + 2 * depth
        
        return 0.0
    
    def compute_hydraulic_radius(self, depth: float) -> float:
        """计算水力半径"""
        A = self.compute_area(depth)
        P = self.compute_wetted_perimeter(depth)
        return A / P if P > 0 else 0.0
    
    def compute_normal_depth(self, flow: float) -> float:
        """
        计算正常水深（Manning公式）
        
        Args:
            flow: 流量 (m³/s)
            
        Returns:
            正常水深 (m)
        """
        # 使用迭代法求解
        h = 1.0  # 初始猜测
        
        for _ in range(50):
            A = self.compute_area(h)
            R = self.compute_hydraulic_radius(h)
            
            # Manning公式: Q = (1/n) * A * R^(2/3) * S^(1/2)
            Q_calc = (1.0 / self.manning_n) * A * (R ** (2/3)) * (self.slope ** 0.5)
            
            # 误差
            error = Q_calc - flow
            
            if abs(error) < 0.001:
                break
            
            # 牛顿法更新
            dh = 0.001
            A_plus = self.compute_area(h + dh)
            R_plus = self.compute_hydraulic_radius(h + dh)
            Q_plus = (1.0 / self.manning_n) * A_plus * (R_plus ** (2/3)) * (self.slope ** 0.5)
            
            dQ_dh = (Q_plus - Q_calc) / dh
            
            if abs(dQ_dh) > 1e-6:
                h = h - error / dQ_dh
                h = max(0.01, min(h, self.depth * 2 if self.depth else 10.0))
        
        return h
    
    def compute_critical_depth(self, flow: float) -> float:
        """
        计算临界水深
        
        Args:
            flow: 流量 (m³/s)
            
        Returns:
            临界水深 (m)
        """
        g = 9.81
        
        # 矩形断面简化公式
        if self.shape == CrossSectionShape.RECTANGULAR:
            return (flow ** 2 / (g * self.width ** 2)) ** (1/3)
        
        # 其他断面用迭代法
        h = 1.0
        
        for _ in range(50):
            A = self.compute_area(h)
            T = self.width + 2 * self.side_slope * h if self.shape == CrossSectionShape.TRAPEZOIDAL else self.width
            
            # Fr = 1条件: V = sqrt(g * A / T)
            V = flow / A if A > 0 else 0
            Fr = V / np.sqrt(g * A / T) if T > 0 else 0
            
            error = Fr - 1.0
            
            if abs(error) < 0.01:
                break
            
            # 更新
            h += error * 0.1
            h = max(0.01, h)
        
        return h
    
    def compute_froude_number(self, flow: float, depth: float) -> float:
        """计算Froude数"""
        g = 9.81
        A = self.compute_area(depth)
        T = self.width  # 简化
        
        if A > 0 and T > 0:
            V = flow / A
            return V / np.sqrt(g * A / T)
        
        return 0.0
    
    def compute_headloss(self, flow: float, depth: float) -> float:
        """计算沿程水头损失"""
        R = self.compute_hydraulic_radius(depth)
        A = self.compute_area(depth)
        
        if A > 0:
            V = flow / A
            # Darcy-Weisbach公式
            f = (self.manning_n ** 2 * 9.81) / (R ** (1/3))
            h_f = f * (self.length / (4 * R)) * (V ** 2 / (2 * 9.81))
            return h_f
        
        return 0.0
    
    def get_status(self) -> Dict:
        """获取状态"""
        return {
            'name': self.name,
            'type': self.channel_type.value,
            'shape': self.shape.value,
            'length': self.length,
            'width': self.width,
            'slope': self.slope,
            'manning_n': self.manning_n
        }


# 使用示例
if __name__ == "__main__":
    print("="*60)
    print("河道/渠道模块测试")
    print("="*60)
    
    # 1. 矩形渠道
    print("\n1. 矩形渠道")
    print("-"*60)
    
    canal = Channel(
        name="Main-Canal",
        channel_type=ChannelType.CANAL,
        length=5000.0,
        shape=CrossSectionShape.RECTANGULAR,
        width=10.0,
        depth=3.0,
        slope=0.0005,
        manning_n=0.020
    )
    
    print(f"渠道: {canal.name}")
    print(f"类型: {canal.channel_type.value}")
    print(f"断面: {canal.shape.value}")
    print(f"底宽: {canal.width}m")
    print(f"底坡: {canal.slope}")
    
    Q = 30.0
    h_n = canal.compute_normal_depth(Q)
    h_c = canal.compute_critical_depth(Q)
    Fr = canal.compute_froude_number(Q, h_n)
    
    print(f"\nQ={Q}m³/s:")
    print(f"  正常水深: {h_n:.2f}m")
    print(f"  临界水深: {h_c:.2f}m")
    print(f"  Froude数: {Fr:.2f}")
    print(f"  流态: {'超临界' if Fr > 1 else '亚临界'}")
    
    # 2. 梯形渠道
    print("\n2. 梯形渠道")
    print("-"*60)
    
    trap_canal = Channel(
        name="Trap-Canal",
        channel_type=ChannelType.CANAL,
        length=3000.0,
        shape=CrossSectionShape.TRAPEZOIDAL,
        width=5.0,
        depth=2.5,
        side_slope=1.5,  # 1:1.5
        slope=0.001,
        manning_n=0.025
    )
    
    print(f"渠道: {trap_canal.name}")
    print(f"底宽: {trap_canal.width}m")
    print(f"边坡: 1:{trap_canal.side_slope}")
    
    for Q in [20, 30, 40]:
        h_n = trap_canal.compute_normal_depth(Q)
        A = trap_canal.compute_area(h_n)
        print(f"  Q={Q}m³/s -> h={h_n:.2f}m, A={A:.2f}m²")
    
    # 3. 圆形管道
    print("\n3. 圆形管道")
    print("-"*60)
    
    pipe = Channel(
        name="Pressure-Pipe",
        channel_type=ChannelType.PIPE,
        length=1000.0,
        shape=CrossSectionShape.CIRCULAR,
        diameter=2.5,
        slope=0.002,
        manning_n=0.013
    )
    
    print(f"管道: {pipe.name}")
    print(f"直径: {pipe.diameter}m")
    
    Q = 5.0
    h_n = pipe.compute_normal_depth(Q)
    h_loss = pipe.compute_headloss(Q, h_n)
    
    print(f"Q={Q}m³/s:")
    print(f"  正常水深: {h_n:.2f}m")
    print(f"  沿程损失: {h_loss:.2f}m")
    
    print(f"\n状态: {canal.get_status()}")
    
    print("\n" + "="*60)
    print("测试完成")
    print("="*60)
