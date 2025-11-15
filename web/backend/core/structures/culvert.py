#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Culvert Module
涵洞模块

对标商业软件（HEC-RAS、MIKE）的涵洞功能

Author: HydroClaude Team
Date: 2025-11-15
"""

import numpy as np
from typing import Dict, Optional, Tuple
from enum import Enum


class CulvertType(Enum):
    """涵洞类型"""
    CIRCULAR = "circular"        # 圆形涵洞
    RECTANGULAR = "rectangular"  # 矩形涵洞
    ARCH = "arch"                # 拱形涵洞
    BOX = "box"                  # 箱涵


class CulvertFlowType(Enum):
    """涵洞流态"""
    INLET_CONTROL = "inlet"      # 进口控制
    OUTLET_CONTROL = "outlet"    # 出口控制
    FULL_FLOW = "full"           # 满流
    PART_FULL = "part_full"      # 非满流


class Culvert:
    """
    涵洞类
    
    功能：
    1. 圆形/矩形/拱形涵洞
    2. 进口/出口控制
    3. 进出口损失
    4. 淹没计算
    5. 水力性能分析
    
    参考商业软件：
    - HEC-RAS: Culvert
    - MIKE: Culvert Structure
    """
    
    def __init__(
        self,
        name: str,
        position: float,
        culvert_type: CulvertType,
        length: float,
        # 圆形涵洞
        diameter: Optional[float] = None,
        # 矩形涵洞
        width: Optional[float] = None,
        height: Optional[float] = None,
        # 其他参数
        manning_n: float = 0.013,
        inlet_loss: float = 0.5,
        outlet_loss: float = 1.0,
        num_barrels: int = 1
    ):
        """
        初始化涵洞
        
        Args:
            name: 涵洞名称
            position: 位置 (m)
            culvert_type: 涵洞类型
            length: 涵洞长度 (m)
            diameter: 直径 (m, 圆形涵洞)
            width: 宽度 (m, 矩形涵洞)
            height: 高度 (m, 矩形涵洞)
            manning_n: Manning粗糙系数
            inlet_loss: 进口损失系数
            outlet_loss: 出口损失系数
            num_barrels: 涵洞孔数
        """
        self.name = name
        self.position = position
        self.culvert_type = culvert_type
        self.length = length
        self.diameter = diameter
        self.width = width
        self.height = height
        self.manning_n = manning_n
        self.inlet_loss = inlet_loss
        self.outlet_loss = outlet_loss
        self.num_barrels = num_barrels
        
        # 计算涵洞面积
        if culvert_type == CulvertType.CIRCULAR:
            self.area = np.pi * (diameter / 2) ** 2
            self.wetted_perimeter = np.pi * diameter
        elif culvert_type in [CulvertType.RECTANGULAR, CulvertType.BOX]:
            self.area = width * height
            self.wetted_perimeter = 2 * (width + height)
        elif culvert_type == CulvertType.ARCH:
            # 简化为半圆拱
            self.area = 0.5 * np.pi * (width / 2) ** 2 + width * height
            self.wetted_perimeter = np.pi * width / 2 + 2 * height + width
        
        # 水力半径
        self.hydraulic_radius = self.area / self.wetted_perimeter
        
        # 流量历史
        self.flow_history = []
        self.flow_type_history = []
    
    def compute_discharge(
        self,
        h_upstream: float,
        h_downstream: float,
        slope: float = 0.001
    ) -> Tuple[float, CulvertFlowType]:
        """
        计算涵洞流量
        
        Args:
            h_upstream: 上游水深 (m)
            h_downstream: 下游水深 (m)
            slope: 涵洞坡度
            
        Returns:
            (流量, 流态)
        """
        g = 9.81
        
        # 涵洞进口高程（简化为0）
        inlet_elev = 0.0
        outlet_elev = inlet_elev - slope * self.length
        
        # 涵洞顶部高程
        if self.culvert_type == CulvertType.CIRCULAR:
            crown_elev = inlet_elev + self.diameter
        else:
            crown_elev = inlet_elev + self.height
        
        # 判断进口是否淹没
        inlet_submerged = h_upstream > crown_elev
        
        # 判断出口是否淹没
        outlet_submerged = h_downstream > crown_elev
        
        # 计算流量
        if not inlet_submerged:
            # 进口控制（非淹没进口）
            # 使用孔口公式
            h_inlet = max(h_upstream - inlet_elev, 0.0)
            if h_inlet > 0:
                Q = 0.6 * self.area * np.sqrt(2 * g * h_inlet)
                flow_type = CulvertFlowType.INLET_CONTROL
            else:
                Q = 0.0
                flow_type = CulvertFlowType.PART_FULL
        
        elif inlet_submerged and not outlet_submerged:
            # 进口淹没，出口自由
            # 计算可用水头
            H_available = h_upstream - outlet_elev
            
            # 总损失系数
            K_total = self.inlet_loss + self.outlet_loss
            
            # 摩阻损失
            V = (1.0 / self.manning_n) * self.hydraulic_radius ** (2/3) * slope ** 0.5
            f = (self.manning_n * g / (self.hydraulic_radius ** (1/3))) ** 2
            h_f = f * (self.length / (2 * g)) * V ** 2
            
            # 流速
            V_calc = np.sqrt(2 * g * H_available / (1 + K_total + h_f / H_available))
            Q = self.area * V_calc
            flow_type = CulvertFlowType.FULL_FLOW
        
        elif inlet_submerged and outlet_submerged:
            # 出口控制（进出口都淹没）
            # 水头差
            delta_h = h_upstream - h_downstream
            
            if delta_h > 0:
                # 总损失系数
                K_total = self.inlet_loss + self.outlet_loss
                
                # 摩阻损失系数
                f = (self.manning_n ** 2 * g) / (self.hydraulic_radius ** (4/3))
                K_friction = f * self.length / self.hydraulic_radius
                
                # 总损失
                K_total += K_friction
                
                # 流速
                V = np.sqrt(2 * g * delta_h / K_total)
                Q = self.area * V
                flow_type = CulvertFlowType.OUTLET_CONTROL
            else:
                Q = 0.0
                flow_type = CulvertFlowType.OUTLET_CONTROL
        
        else:
            Q = 0.0
            flow_type = CulvertFlowType.PART_FULL
        
        # 考虑多孔
        Q *= self.num_barrels
        
        # 记录
        self.flow_history.append(Q)
        self.flow_type_history.append(flow_type)
        
        return Q, flow_type
    
    def get_status(self) -> Dict:
        """获取涵洞状态"""
        status = {
            'name': self.name,
            'type': self.culvert_type.value,
            'position': self.position,
            'length': self.length,
            'area': self.area,
            'hydraulic_radius': self.hydraulic_radius,
            'num_barrels': self.num_barrels,
            'manning_n': self.manning_n
        }
        
        if self.culvert_type == CulvertType.CIRCULAR:
            status['diameter'] = self.diameter
        else:
            status['width'] = self.width
            status['height'] = self.height
        
        return status


# 使用示例
if __name__ == "__main__":
    print("="*60)
    print("涵洞模块测试")
    print("="*60)
    
    # 1. 圆形涵洞
    print("\n1. 圆形涵洞 (D=2.0m)")
    print("-"*60)
    circular = Culvert(
        name="Culvert-C1",
        position=1000.0,
        culvert_type=CulvertType.CIRCULAR,
        length=50.0,
        diameter=2.0,
        num_barrels=2
    )
    
    for h_up in [1.5, 2.5, 3.5]:
        Q, flow_type = circular.compute_discharge(h_up, 1.0, slope=0.002)
        print(f"上游水深: {h_up:.1f}m -> 流量: {Q:.2f} m³/s, 流态: {flow_type.value}")
    
    print(f"\n状态: {circular.get_status()}")
    
    # 2. 矩形涵洞
    print("\n2. 矩形涵洞 (2.0m × 1.5m)")
    print("-"*60)
    rectangular = Culvert(
        name="Culvert-R1",
        position=1100.0,
        culvert_type=CulvertType.RECTANGULAR,
        length=60.0,
        width=2.0,
        height=1.5,
        num_barrels=1
    )
    
    for h_up in [1.0, 2.0, 3.0]:
        Q, flow_type = rectangular.compute_discharge(h_up, 0.8, slope=0.002)
        print(f"上游水深: {h_up:.1f}m -> 流量: {Q:.2f} m³/s, 流态: {flow_type.value}")
    
    print(f"\n状态: {rectangular.get_status()}")
    
    # 3. 箱涵
    print("\n3. 箱涵 (3.0m × 2.0m, 3孔)")
    print("-"*60)
    box = Culvert(
        name="Culvert-Box",
        position=1200.0,
        culvert_type=CulvertType.BOX,
        length=80.0,
        width=3.0,
        height=2.0,
        num_barrels=3
    )
    
    for h_up in [1.5, 2.5, 3.5]:
        Q, flow_type = box.compute_discharge(h_up, 1.0, slope=0.001)
        print(f"上游水深: {h_up:.1f}m -> 流量: {Q:.2f} m³/s, 流态: {flow_type.value}")
    
    print(f"\n状态: {box.get_status()}")
    
    print("\n" + "="*60)
    print("测试完成")
    print("="*60)
