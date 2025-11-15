#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Drop Structure Module
跌水结构模块

对标商业软件的跌水/陡坡功能

Author: HydroClaude Team
Date: 2025-11-15
"""

import numpy as np
from typing import Dict, Tuple


class DropStructure:
    """
    跌水结构类
    
    功能：
    1. 能量消散计算
    2. 下游水跃预测
    3. 临界水深计算
    4. 冲刷保护设计
    
    参考商业软件：
    - HEC-RAS: Drop Structure
    - MIKE: Drop/Chute
    """
    
    def __init__(
        self,
        name: str,
        position: float,
        drop_height: float,
        width: float,
        chute_length: float = 0.0,
        chute_slope: float = 0.0,
        roughness: float = 0.013
    ):
        """
        初始化跌水
        
        Args:
            name: 跌水名称
            position: 位置 (m)
            drop_height: 跌水高度 (m)
            width: 宽度 (m)
            chute_length: 陡槽长度 (m, 0表示垂直跌水)
            chute_slope: 陡槽坡度
            roughness: 粗糙系数
        """
        self.name = name
        self.position = position
        self.drop_height = drop_height
        self.width = width
        self.chute_length = chute_length
        self.chute_slope = chute_slope
        self.roughness = roughness
        
        # 流量历史
        self.flow_history = []
        self.energy_loss_history = []
    
    def compute_critical_depth(self, Q: float) -> float:
        """
        计算临界水深
        
        Args:
            Q: 流量 (m³/s)
            
        Returns:
            临界水深 (m)
        """
        g = 9.81
        q = Q / self.width  # 单宽流量
        
        # 临界水深: hc = (q²/g)^(1/3)
        h_c = (q ** 2 / g) ** (1/3)
        
        return h_c
    
    def compute_energy_loss(
        self,
        Q: float,
        h_upstream: float
    ) -> Tuple[float, float, float]:
        """
        计算能量损失和下游水深
        
        Args:
            Q: 流量 (m³/s)
            h_upstream: 上游水深 (m)
            
        Returns:
            (下游水深, 能量损失, 共轭水深)
        """
        g = 9.81
        
        # 上游能量（相对于跌水底部）
        V_up = Q / (self.width * h_upstream)
        E_up = h_upstream + V_up ** 2 / (2 * g) + self.drop_height
        
        # 临界水深
        h_c = self.compute_critical_depth(Q)
        
        if self.chute_length > 0:
            # 有陡槽：在陡槽上达到临界流
            # 陡槽底能量
            E_chute = E_up - self.drop_height
            
            # 陡槽末端水深（假设为临界水深）
            h_chute_end = h_c
            V_chute_end = Q / (self.width * h_chute_end)
            
            # 跌落后水深（自由跌落）
            # 使用抛物线轨迹
            V_bottom = np.sqrt(V_chute_end ** 2 + 2 * g * self.drop_height)
            h_bottom = Q / (self.width * V_bottom)
        else:
            # 垂直跌水
            # 跌水底部流速
            V_bottom = np.sqrt(V_up ** 2 + 2 * g * self.drop_height)
            h_bottom = Q / (self.width * V_bottom)
        
        # 计算共轭水深（水跃后水深）
        Fr_bottom = V_bottom / np.sqrt(g * h_bottom)
        
        if Fr_bottom > 1.0:
            # 超临界流，需要水跃
            # 共轭水深公式
            h_conjugate = (h_bottom / 2) * (np.sqrt(1 + 8 * Fr_bottom ** 2) - 1)
            
            # 水跃后流速
            V_conjugate = Q / (self.width * h_conjugate)
            
            # 水跃能量损失
            delta_E_jump = ((h_conjugate - h_bottom) ** 3) / (4 * h_bottom * h_conjugate)
        else:
            # 亚临界流，无水跃
            h_conjugate = h_bottom
            V_conjugate = V_bottom
            delta_E_jump = 0.0
        
        # 总能量损失
        E_down = h_conjugate + V_conjugate ** 2 / (2 * g)
        delta_E_total = E_up - E_down
        
        # 记录
        self.flow_history.append(Q)
        self.energy_loss_history.append(delta_E_total)
        
        return h_conjugate, delta_E_total, h_bottom
    
    def design_stilling_basin(
        self,
        Q: float,
        h_upstream: float
    ) -> Dict:
        """
        消力池设计
        
        Args:
            Q: 设计流量 (m³/s)
            h_upstream: 上游水深 (m)
            
        Returns:
            设计参数
        """
        h_down, E_loss, h_before = self.compute_energy_loss(Q, h_upstream)
        
        g = 9.81
        V_before = Q / (self.width * h_before)
        Fr_before = V_before / np.sqrt(g * h_before)
        
        # 消力池长度（经验公式）
        if Fr_before < 1.7:
            # Fr小，水跃较弱
            basin_length = 4.0 * h_down
        elif Fr_before < 2.5:
            # Fr中等
            basin_length = 5.0 * h_down
        elif Fr_before < 4.5:
            # Fr较大
            basin_length = 6.0 * h_down
        else:
            # Fr很大
            basin_length = 6.5 * h_down
        
        # 消力池深度
        basin_depth = h_down - h_before
        
        # 齿墙高度（如果需要）
        if Fr_before > 3.0:
            baffle_height = 0.8 * h_before
        else:
            baffle_height = 0.0
        
        return {
            'basin_length': basin_length,
            'basin_depth': basin_depth,
            'baffle_height': baffle_height,
            'conjugate_depth': h_down,
            'supercritical_depth': h_before,
            'froude_number': Fr_before,
            'energy_loss': E_loss
        }
    
    def get_status(self) -> Dict:
        """获取状态"""
        return {
            'name': self.name,
            'position': self.position,
            'drop_height': self.drop_height,
            'width': self.width,
            'chute_length': self.chute_length,
            'chute_slope': self.chute_slope,
            'avg_energy_loss': np.mean(self.energy_loss_history) if self.energy_loss_history else 0
        }


# 使用示例
if __name__ == "__main__":
    print("="*60)
    print("跌水结构模块测试")
    print("="*60)
    
    # 1. 垂直跌水
    print("\n1. 垂直跌水 (高度=3.0m, 宽度=10.0m)")
    print("-"*60)
    drop = DropStructure(
        name="Drop-V1",
        position=1000.0,
        drop_height=3.0,
        width=10.0
    )
    
    Q = 50.0  # 设计流量
    h_up = 2.0  # 上游水深
    
    h_down, E_loss, h_before = drop.compute_energy_loss(Q, h_up)
    
    print(f"流量: {Q:.1f} m³/s")
    print(f"上游水深: {h_up:.2f} m")
    print(f"跌水前水深: {h_before:.3f} m")
    print(f"共轭水深: {h_down:.2f} m")
    print(f"能量损失: {E_loss:.2f} m")
    
    # 消力池设计
    design = drop.design_stilling_basin(Q, h_up)
    print(f"\n消力池设计:")
    print(f"  长度: {design['basin_length']:.2f} m")
    print(f"  深度: {design['basin_depth']:.2f} m")
    print(f"  Froude数: {design['froude_number']:.2f}")
    if design['baffle_height'] > 0:
        print(f"  齿墙高度: {design['baffle_height']:.2f} m")
    
    # 2. 陡槽跌水
    print("\n2. 陡槽跌水 (高度=5.0m, 陡槽长度=20.0m)")
    print("-"*60)
    chute_drop = DropStructure(
        name="Drop-C1",
        position=1200.0,
        drop_height=5.0,
        width=8.0,
        chute_length=20.0,
        chute_slope=0.25
    )
    
    Q = 80.0
    h_up = 2.5
    
    h_down, E_loss, h_before = chute_drop.compute_energy_loss(Q, h_up)
    
    print(f"流量: {Q:.1f} m³/s")
    print(f"上游水深: {h_up:.2f} m")
    print(f"跌水前水深: {h_before:.3f} m")
    print(f"共轭水深: {h_down:.2f} m")
    print(f"能量损失: {E_loss:.2f} m")
    
    design = chute_drop.design_stilling_basin(Q, h_up)
    print(f"\n消力池设计:")
    print(f"  长度: {design['basin_length']:.2f} m")
    print(f"  深度: {design['basin_depth']:.2f} m")
    print(f"  Froude数: {design['froude_number']:.2f}")
    
    print(f"\n状态: {drop.get_status()}")
    
    print("\n" + "="*60)
    print("测试完成")
    print("="*60)
