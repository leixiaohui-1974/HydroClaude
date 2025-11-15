#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Bridge Module
桥梁模块

对标商业软件的桥梁水力计算功能

Author: HydroClaude Team
Date: 2025-11-15
"""

import numpy as np
from typing import Dict, Tuple, List


class Bridge:
    """
    桥梁类
    
    功能：
    1. 压缩流计算
    2. 桥墩阻水
    3. 壅水计算
    4. 溢流计算
    5. 冲刷预测
    
    参考商业软件：
    - HEC-RAS: Bridge
    - MIKE: Bridge Structure
    """
    
    def __init__(
        self,
        name: str,
        position: float,
        bridge_width: float,
        deck_elevation: float,
        # 桥孔参数
        opening_width: float,
        opening_height: float,
        num_openings: int = 1,
        # 桥墩参数
        pier_width: float = 0.0,
        num_piers: int = 0,
        # 其他参数
        contraction_coeff: float = 0.9,
        expansion_coeff: float = 0.5,
        discharge_coeff: float = 0.8
    ):
        """
        初始化桥梁
        
        Args:
            name: 桥梁名称
            position: 位置 (m)
            bridge_width: 桥梁全宽 (m)
            deck_elevation: 桥面高程 (m)
            opening_width: 单孔净宽 (m)
            opening_height: 桥孔高度 (m)
            num_openings: 桥孔数量
            pier_width: 桥墩宽度 (m)
            num_piers: 桥墩数量
            contraction_coeff: 压缩系数
            expansion_coeff: 扩散系数
            discharge_coeff: 流量系数
        """
        self.name = name
        self.position = position
        self.bridge_width = bridge_width
        self.deck_elevation = deck_elevation
        self.opening_width = opening_width
        self.opening_height = opening_height
        self.num_openings = num_openings
        self.pier_width = pier_width
        self.num_piers = num_piers
        self.contraction_coeff = contraction_coeff
        self.expansion_coeff = expansion_coeff
        self.discharge_coeff = discharge_coeff
        
        # 计算有效过流面积
        total_opening_width = num_openings * opening_width
        pier_blockage = num_piers * pier_width
        self.net_width = total_opening_width - pier_blockage
        self.flow_area = self.net_width * opening_height
        
        # 流量历史
        self.flow_history = []
        self.backwater_history = []
    
    def compute_discharge(
        self,
        h_upstream: float,
        h_downstream: float,
        channel_width: float
    ) -> Tuple[float, float, str]:
        """
        计算过桥流量和壅水
        
        Args:
            h_upstream: 上游水深 (m)
            h_downstream: 下游水深 (m)
            channel_width: 河道宽度 (m)
            
        Returns:
            (流量, 壅水高度, 流态)
        """
        g = 9.81
        
        # 判断流态
        if h_upstream < self.deck_elevation:
            # 水位低于桥面，开放式流动
            flow_mode = "open_channel"
            
            # 考虑桥墩阻水的压缩流
            # 收缩比
            contraction_ratio = self.net_width / channel_width
            
            # 压缩流速
            V_bridge = np.sqrt(2 * g * (h_upstream - h_downstream) / 
                              (1 + (1 / contraction_ratio ** 2 - 1) * self.contraction_coeff))
            
            # 桥下过流面积
            A_bridge = min(h_upstream, self.opening_height) * self.net_width
            
            # 流量
            Q = self.discharge_coeff * A_bridge * V_bridge
            
            # 壅水高度（Yarnell公式简化）
            K = (contraction_ratio - 1) ** 2 + self.num_piers * (self.pier_width / self.net_width)
            V_approach = Q / (channel_width * h_upstream)
            delta_h = K * V_approach ** 2 / (2 * g)
            
        elif h_downstream > self.deck_elevation:
            # 水位淹没桥面，压力流
            flow_mode = "pressure_flow"
            
            # 孔口流公式
            h_diff = max(h_upstream - h_downstream, 0.01)
            Q = self.discharge_coeff * self.flow_area * np.sqrt(2 * g * h_diff)
            
            # 壅水高度
            delta_h = h_upstream - self.deck_elevation
            
        else:
            # 上游淹没桥面，下游自由
            flow_mode = "overflow"
            
            # 堰流公式（溢过桥面）
            H = h_upstream - self.deck_elevation
            Q = 1.7 * self.bridge_width * H ** 1.5
            
            # 加上桥孔流量
            if h_upstream > 0:
                A_opening = min(self.deck_elevation, self.opening_height) * self.net_width
                Q_opening = self.discharge_coeff * A_opening * np.sqrt(2 * g * h_upstream)
                Q += Q_opening
            
            delta_h = H
        
        # 记录
        self.flow_history.append(Q)
        self.backwater_history.append(delta_h)
        
        return Q, delta_h, flow_mode
    
    def estimate_scour(
        self,
        Q: float,
        h_upstream: float,
        bed_material_d50: float = 0.05
    ) -> Dict:
        """
        估算冲刷深度
        
        Args:
            Q: 流量 (m³/s)
            h_upstream: 上游水深 (m)
            bed_material_d50: 床沙中值粒径 (m)
            
        Returns:
            冲刷参数
        """
        g = 9.81
        
        # 桥下流速
        A_bridge = h_upstream * self.net_width
        V_bridge = Q / A_bridge if A_bridge > 0 else 0
        
        # 临界流速（Shields公式简化）
        V_critical = 2.5 * np.sqrt(g * bed_material_d50)
        
        # 冲刷判断
        if V_bridge > V_critical:
            # HEC-18公式（简化）
            # 一般冲刷
            y_g = 0.5 * h_upstream * (V_bridge / V_critical - 1)
            
            # 局部冲刷（桥墩）
            if self.num_piers > 0:
                y_p = 2.0 * self.pier_width * (V_bridge / V_critical) ** 0.65
            else:
                y_p = 0.0
            
            # 总冲刷
            y_total = y_g + y_p
            
            scour_risk = "high" if V_bridge > 2 * V_critical else "moderate"
        else:
            y_g = 0.0
            y_p = 0.0
            y_total = 0.0
            scour_risk = "low"
        
        return {
            'general_scour': y_g,
            'pier_scour': y_p,
            'total_scour': y_total,
            'bridge_velocity': V_bridge,
            'critical_velocity': V_critical,
            'risk_level': scour_risk
        }
    
    def get_status(self) -> Dict:
        """获取状态"""
        return {
            'name': self.name,
            'position': self.position,
            'bridge_width': self.bridge_width,
            'deck_elevation': self.deck_elevation,
            'num_openings': self.num_openings,
            'opening_width': self.opening_width,
            'num_piers': self.num_piers,
            'net_width': self.net_width,
            'flow_area': self.flow_area,
            'avg_backwater': np.mean(self.backwater_history) if self.backwater_history else 0
        }


# 使用示例
if __name__ == "__main__":
    print("="*60)
    print("桥梁模块测试")
    print("="*60)
    
    # 创建桥梁（3孔，有2个桥墩）
    bridge = Bridge(
        name="Bridge-001",
        position=2000.0,
        bridge_width=40.0,
        deck_elevation=8.0,
        opening_width=12.0,
        opening_height=6.0,
        num_openings=3,
        pier_width=2.0,
        num_piers=2
    )
    
    print(f"\n桥梁参数:")
    print(f"  净宽: {bridge.net_width:.2f} m")
    print(f"  过流面积: {bridge.flow_area:.2f} m²")
    
    print("\n测试不同水位情况")
    print("-"*60)
    
    channel_width = 50.0
    
    # 1. 水位低于桥面
    print("\n情况1: 水位低于桥面（开放式流动）")
    h_up, h_down = 5.0, 4.0
    Q, backwater, mode = bridge.compute_discharge(h_up, h_down, channel_width)
    print(f"上游水深: {h_up:.1f}m, 下游水深: {h_down:.1f}m")
    print(f"流量: {Q:.2f} m³/s, 壅水: {backwater:.2f} m, 流态: {mode}")
    
    # 冲刷估算
    scour = bridge.estimate_scour(Q, h_up, bed_material_d50=0.05)
    print(f"冲刷风险: {scour['risk_level']}")
    print(f"  一般冲刷: {scour['general_scour']:.2f} m")
    print(f"  桥墩冲刷: {scour['pier_scour']:.2f} m")
    print(f"  总冲刷: {scour['total_scour']:.2f} m")
    
    # 2. 水位淹没桥面
    print("\n情况2: 水位淹没桥面（压力流）")
    h_up, h_down = 9.0, 8.5
    Q, backwater, mode = bridge.compute_discharge(h_up, h_down, channel_width)
    print(f"上游水深: {h_up:.1f}m, 下游水深: {h_down:.1f}m")
    print(f"流量: {Q:.2f} m³/s, 壅水: {backwater:.2f} m, 流态: {mode}")
    
    # 3. 溢流情况
    print("\n情况3: 上游淹没桥面，下游自由（溢流）")
    h_up, h_down = 9.5, 6.0
    Q, backwater, mode = bridge.compute_discharge(h_up, h_down, channel_width)
    print(f"上游水深: {h_up:.1f}m, 下游水深: {h_down:.1f}m")
    print(f"流量: {Q:.2f} m³/s, 壅水: {backwater:.2f} m, 流态: {mode}")
    
    print(f"\n状态: {bridge.get_status()}")
    
    print("\n" + "="*60)
    print("测试完成")
    print("="*60)
