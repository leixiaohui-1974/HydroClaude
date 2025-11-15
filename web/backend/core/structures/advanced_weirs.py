#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Advanced Weir Types Module
高级堰类型模块

对标商业软件（HEC-RAS、MIKE）的多类型堰

Author: HydroClaude Team
Date: 2025-11-15
"""

import numpy as np
from typing import Optional, Dict
from enum import Enum


class WeirType(Enum):
    """堰类型"""
    SHARP_CRESTED = "sharp"      # 尖顶堰（薄壁堰）
    BROAD_CRESTED = "broad"      # 宽顶堰
    V_NOTCH = "v_notch"          # V型堰（三角堰）
    RECTANGULAR = "rectangular"   # 矩形堰
    TRAPEZOIDAL = "trapezoidal"  # 梯形堰
    CIPOLLETTI = "cipolletti"    # Cipolletti堰
    OGEE = "ogee"                # 溢流堰（溢流面）


class BaseWeir:
    """堰基类"""
    
    def __init__(
        self,
        name: str,
        position: float,
        width: float,
        crest_height: float,
        discharge_coeff: float = 1.7
    ):
        """
        初始化堰
        
        Args:
            name: 堰名称
            position: 位置 (m)
            width: 堰宽 (m)
            crest_height: 堰顶高程 (m)
            discharge_coeff: 流量系数
        """
        self.name = name
        self.position = position
        self.width = width
        self.crest_height = crest_height
        self.discharge_coeff = discharge_coeff
        
        # 运行记录
        self.flow_history = []
        self.head_history = []
    
    def compute_discharge(
        self,
        h_upstream: float,
        h_downstream: Optional[float] = None
    ) -> float:
        """
        计算过堰流量（需要在子类中实现）
        
        Args:
            h_upstream: 上游水深 (m)
            h_downstream: 下游水深 (m, 可选)
            
        Returns:
            流量 (m³/s)
        """
        raise NotImplementedError
    
    def get_status(self) -> Dict:
        """获取堰状态"""
        return {
            'name': self.name,
            'type': self.__class__.__name__,
            'position': self.position,
            'width': self.width,
            'crest_height': self.crest_height,
            'discharge_coeff': self.discharge_coeff
        }


class SharpCrestedWeir(BaseWeir):
    """
    尖顶堰（薄壁堰）
    
    特点：
    1. 堰顶尖锐，水流与堰面接触极小
    2. 流量公式精确，常用于测流
    3. 适用于小流量
    
    流量公式：
    Q = Cd * b * H^1.5
    其中：
    - Cd: 流量系数，通常1.7-1.84
    - b: 堰宽
    - H: 过堰水头
    
    参考：HEC-RAS Sharp-Crested Weir
    """
    
    def __init__(
        self,
        name: str,
        position: float,
        width: float,
        crest_height: float,
        discharge_coeff: float = 1.84,  # Francis公式
        contraction_coeff: float = 1.0
    ):
        """
        初始化尖顶堰
        
        Args:
            contraction_coeff: 收缩系数（端部收缩影响）
        """
        super().__init__(name, position, width, crest_height, discharge_coeff)
        self.contraction_coeff = contraction_coeff
    
    def compute_discharge(
        self,
        h_upstream: float,
        h_downstream: Optional[float] = None
    ) -> float:
        """计算尖顶堰流量"""
        # 过堰水头
        H = max(h_upstream - self.crest_height, 0.0)
        
        if H < 0.001:
            return 0.0
        
        # 有效堰宽（考虑端部收缩）
        b_eff = self.width * self.contraction_coeff
        
        # Francis公式: Q = Cd * b_eff * H^1.5
        Q = self.discharge_coeff * b_eff * H**1.5
        
        # 淹没修正（如果提供下游水深）
        if h_downstream is not None:
            h_ratio = (h_downstream - self.crest_height) / H
            if h_ratio > 0.1:  # 淹没开始影响
                # 淹没系数（Villemonte公式）
                submergence_factor = (1 - h_ratio**1.5)**0.385
                Q *= submergence_factor
        
        self.flow_history.append(Q)
        self.head_history.append(H)
        
        return Q
    
    def get_status(self) -> Dict:
        status = super().get_status()
        status['contraction_coeff'] = self.contraction_coeff
        return status


class BroadCrestedWeir(BaseWeir):
    """
    宽顶堰
    
    特点：
    1. 堰顶较宽，水流在堰顶达到临界流
    2. 流量公式基于临界流理论
    3. 适用于大流量
    
    流量公式：
    Q = Cd * b * sqrt(g) * H^1.5
    其中：
    - Cd: 流量系数，通常1.6-1.7
    - 临界水深: hc = 0.67 * H
    
    参考：HEC-RAS Broad-Crested Weir
    """
    
    def __init__(
        self,
        name: str,
        position: float,
        width: float,
        crest_height: float,
        crest_length: float = 2.0,
        discharge_coeff: float = 1.7
    ):
        """
        初始化宽顶堰
        
        Args:
            crest_length: 堰顶长度 (m)
        """
        super().__init__(name, position, width, crest_height, discharge_coeff)
        self.crest_length = crest_length
    
    def compute_discharge(
        self,
        h_upstream: float,
        h_downstream: Optional[float] = None
    ) -> float:
        """计算宽顶堰流量"""
        # 过堰水头
        H = max(h_upstream - self.crest_height, 0.0)
        
        if H < 0.001:
            return 0.0
        
        g = 9.81
        
        # 宽顶堰公式
        Q = self.discharge_coeff * self.width * np.sqrt(g) * H**1.5
        
        # 淹没修正
        if h_downstream is not None:
            # 临界水深
            h_critical = self.crest_height + 0.67 * H
            
            if h_downstream > h_critical:
                # 淹没流
                # 使用淹没系数修正
                h_ratio = (h_downstream - self.crest_height) / H
                if h_ratio > 0.67:
                    submergence_factor = np.sqrt(1 - ((h_ratio - 0.67) / 0.33)**2)
                    Q *= submergence_factor
        
        self.flow_history.append(Q)
        self.head_history.append(H)
        
        return Q
    
    def get_status(self) -> Dict:
        status = super().get_status()
        status['crest_length'] = self.crest_length
        return status


class VNotchWeir(BaseWeir):
    """
    V型堰（三角堰）
    
    特点：
    1. V型切口，流量与水头的2.5次方成正比
    2. 小流量测量精度高
    3. 90°V型堰最常用
    
    流量公式：
    Q = Cd * (8/15) * sqrt(2g) * tan(θ/2) * H^2.5
    其中：
    - θ: V型角度
    - 90°堰: Cd ≈ 1.4
    
    参考：HEC-RAS V-Notch Weir
    """
    
    def __init__(
        self,
        name: str,
        position: float,
        crest_height: float,
        notch_angle: float = 90.0,
        discharge_coeff: float = 1.4
    ):
        """
        初始化V型堰
        
        Args:
            notch_angle: V型角度 (度)
        """
        super().__init__(name, position, width=0.0, crest_height=crest_height, discharge_coeff=discharge_coeff)
        self.notch_angle = notch_angle
    
    def compute_discharge(
        self,
        h_upstream: float,
        h_downstream: Optional[float] = None
    ) -> float:
        """计算V型堰流量"""
        # 过堰水头
        H = max(h_upstream - self.crest_height, 0.0)
        
        if H < 0.001:
            return 0.0
        
        g = 9.81
        theta = self.notch_angle * np.pi / 180
        
        # V型堰公式
        Q = self.discharge_coeff * (8.0/15.0) * np.sqrt(2*g) * np.tan(theta/2) * H**2.5
        
        self.flow_history.append(Q)
        self.head_history.append(H)
        
        return Q
    
    def get_status(self) -> Dict:
        status = super().get_status()
        status['notch_angle'] = self.notch_angle
        del status['width']  # V型堰没有固定宽度
        return status


class RectangularWeir(BaseWeir):
    """
    矩形堰
    
    特点：
    1. 最常见的堰型
    2. 可以是整孔或部分孔
    3. 适用于中等流量
    
    流量公式：
    Q = Cd * b * H^1.5
    
    参考：HEC-RAS Rectangular Weir
    """
    
    def compute_discharge(
        self,
        h_upstream: float,
        h_downstream: Optional[float] = None
    ) -> float:
        """计算矩形堰流量"""
        H = max(h_upstream - self.crest_height, 0.0)
        
        if H < 0.001:
            return 0.0
        
        Q = self.discharge_coeff * self.width * H**1.5
        
        # 淹没修正
        if h_downstream is not None:
            h_ratio = (h_downstream - self.crest_height) / H
            if h_ratio > 0.1:
                submergence_factor = (1 - h_ratio**1.5)**0.385
                Q *= submergence_factor
        
        self.flow_history.append(Q)
        self.head_history.append(H)
        
        return Q


class TrapezoidalWeir(BaseWeir):
    """
    梯形堰（Cipolletti堰）
    
    特点：
    1. 侧边坡度1:4（水平:垂直）
    2. 可自动补偿端部收缩
    3. 流量公式简单
    
    流量公式：
    Q = Cd * b * H^1.5
    其中b是底宽
    
    参考：MIKE Trapezoidal Weir
    """
    
    def __init__(
        self,
        name: str,
        position: float,
        width: float,
        crest_height: float,
        side_slope: float = 0.25,  # 1:4
        discharge_coeff: float = 1.859
    ):
        """
        初始化梯形堰
        
        Args:
            side_slope: 侧边坡度（水平/垂直）
        """
        super().__init__(name, position, width, crest_height, discharge_coeff)
        self.side_slope = side_slope
    
    def compute_discharge(
        self,
        h_upstream: float,
        h_downstream: Optional[float] = None
    ) -> float:
        """计算梯形堰流量"""
        H = max(h_upstream - self.crest_height, 0.0)
        
        if H < 0.001:
            return 0.0
        
        # 有效宽度（考虑侧边扩展）
        b_eff = self.width + 2 * self.side_slope * H
        
        # Cipolletti公式
        Q = self.discharge_coeff * b_eff * H**1.5
        
        self.flow_history.append(Q)
        self.head_history.append(H)
        
        return Q
    
    def get_status(self) -> Dict:
        status = super().get_status()
        status['side_slope'] = self.side_slope
        return status


class OgeeWeir(BaseWeir):
    """
    溢流堰（溢流面堰）
    
    特点：
    1. 堰面为抛物线形（与自由落水轨迹吻合）
    2. 流量系数高，过流能力强
    3. 广泛用于大坝溢洪道
    
    流量公式：
    Q = C * L * H^1.5
    其中：
    - C: 流量系数，通常2.0-2.2
    - 设计水头时C最大
    
    参考：HEC-RAS Ogee Spillway
    """
    
    def __init__(
        self,
        name: str,
        position: float,
        width: float,
        crest_height: float,
        design_head: float = 3.0,
        discharge_coeff: float = 2.1
    ):
        """
        初始化溢流堰
        
        Args:
            design_head: 设计水头 (m)
        """
        super().__init__(name, position, width, crest_height, discharge_coeff)
        self.design_head = design_head
    
    def compute_discharge(
        self,
        h_upstream: float,
        h_downstream: Optional[float] = None
    ) -> float:
        """计算溢流堰流量"""
        H = max(h_upstream - self.crest_height, 0.0)
        
        if H < 0.001:
            return 0.0
        
        # 调整流量系数（根据水头比）
        head_ratio = H / self.design_head
        if head_ratio < 1.0:
            # 低于设计水头，系数降低
            Cd = self.discharge_coeff * (0.9 + 0.1 * head_ratio)
        else:
            # 高于设计水头，系数略降
            Cd = self.discharge_coeff * (1.0 - 0.05 * (head_ratio - 1.0))
        
        Cd = max(Cd, self.discharge_coeff * 0.85)  # 不低于85%
        
        # 流量公式
        Q = Cd * self.width * H**1.5
        
        # 淹没修正
        if h_downstream is not None:
            tail_water_depth = h_downstream - self.crest_height
            if tail_water_depth > 0:
                h_ratio = tail_water_depth / H
                if h_ratio > 0.2:
                    # 尾水影响
                    submergence_factor = 1.0 - 0.2 * (h_ratio - 0.2)
                    Q *= max(submergence_factor, 0.5)
        
        self.flow_history.append(Q)
        self.head_history.append(H)
        
        return Q
    
    def get_status(self) -> Dict:
        status = super().get_status()
        status['design_head'] = self.design_head
        return status


# 使用示例
if __name__ == "__main__":
    print("="*60)
    print("高级堰类型测试")
    print("="*60)
    
    # 测试条件
    h_up = 5.0   # 上游水深
    h_down = 2.0 # 下游水深
    crest_h = 2.0  # 堰顶高程
    
    weirs = []
    
    # 1. 尖顶堰
    print("\n1. 尖顶堰 (Sharp-Crested Weir)")
    print("-" * 60)
    sharp = SharpCrestedWeir("SW-001", 500, width=5.0, crest_height=crest_h)
    Q = sharp.compute_discharge(h_up, h_down)
    print(f"流量: {Q:.2f} m³/s")
    print(f"状态: {sharp.get_status()}")
    weirs.append(("尖顶堰", Q))
    
    # 2. 宽顶堰
    print("\n2. 宽顶堰 (Broad-Crested Weir)")
    print("-" * 60)
    broad = BroadCrestedWeir("BW-001", 600, width=5.0, crest_height=crest_h, crest_length=3.0)
    Q = broad.compute_discharge(h_up, h_down)
    print(f"流量: {Q:.2f} m³/s")
    print(f"状态: {broad.get_status()}")
    weirs.append(("宽顶堰", Q))
    
    # 3. V型堰
    print("\n3. V型堰 (V-Notch Weir)")
    print("-" * 60)
    v_notch = VNotchWeir("VW-001", 700, crest_height=crest_h, notch_angle=90.0)
    Q = v_notch.compute_discharge(h_up)
    print(f"流量: {Q:.2f} m³/s")
    print(f"状态: {v_notch.get_status()}")
    weirs.append(("V型堰", Q))
    
    # 4. 矩形堰
    print("\n4. 矩形堰 (Rectangular Weir)")
    print("-" * 60)
    rect = RectangularWeir("RW-001", 800, width=5.0, crest_height=crest_h)
    Q = rect.compute_discharge(h_up, h_down)
    print(f"流量: {Q:.2f} m³/s")
    print(f"状态: {rect.get_status()}")
    weirs.append(("矩形堰", Q))
    
    # 5. 梯形堰
    print("\n5. 梯形堰 (Trapezoidal/Cipolletti Weir)")
    print("-" * 60)
    trap = TrapezoidalWeir("TW-001", 900, width=5.0, crest_height=crest_h)
    Q = trap.compute_discharge(h_up, h_down)
    print(f"流量: {Q:.2f} m³/s")
    print(f"状态: {trap.get_status()}")
    weirs.append(("梯形堰", Q))
    
    # 6. 溢流堰
    print("\n6. 溢流堰 (Ogee Weir)")
    print("-" * 60)
    ogee = OgeeWeir("OW-001", 1000, width=5.0, crest_height=crest_h, design_head=3.0)
    Q = ogee.compute_discharge(h_up, h_down)
    print(f"流量: {Q:.2f} m³/s")
    print(f"状态: {ogee.get_status()}")
    weirs.append(("溢流堰", Q))
    
    # 流量对比
    print("\n" + "="*60)
    print("流量对比（相同上游水深，堰顶高程）")
    print("="*60)
    for name, Q in weirs:
        print(f"{name:20s}: {Q:8.2f} m³/s")
    
    print("\n" + "="*60)
    print("测试完成")
    print("="*60)
