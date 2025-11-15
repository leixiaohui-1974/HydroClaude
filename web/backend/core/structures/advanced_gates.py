#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Advanced Gate Types Module
高级闸门类型模块

对标商业软件（HEC-RAS、MIKE）的多类型闸门

Author: HydroClaude Team
Date: 2025-11-15
"""

import numpy as np
from typing import Optional, Dict
from enum import Enum


class GateType(Enum):
    """闸门类型"""
    SLUICE = "sluice"           # 滑动闸门（平板闸门）
    RADIAL = "radial"           # 径向闸门（弧形闸门）
    VERTICAL_LIFT = "vertical"  # 垂直提升闸门
    ROLLER = "roller"           # 滚轮闸门
    FLAP = "flap"               # 翻板闸门


class FlowRegime(Enum):
    """流态"""
    FREE_FLOW = "free"         # 自由流
    SUBMERGED = "submerged"    # 淹没流
    ORIFICE = "orifice"        # 孔流
    WEIR = "weir"              # 堰流


class BaseGate:
    """闸门基类"""
    
    def __init__(
        self,
        name: str,
        position: float,
        width: float,
        opening: float,
        discharge_coeff: float = 0.6
    ):
        """
        初始化闸门
        
        Args:
            name: 闸门名称
            position: 位置 (m)
            width: 闸门宽度 (m)
            opening: 开度 (m)
            discharge_coeff: 流量系数
        """
        self.name = name
        self.position = position
        self.width = width
        self.opening = opening
        self.discharge_coeff = discharge_coeff
        
        # 运行记录
        self.flow_history = []
        self.regime_history = []
    
    def compute_discharge(
        self,
        h_upstream: float,
        h_downstream: float
    ) -> tuple[float, FlowRegime]:
        """
        计算过闸流量（需要在子类中实现）
        
        Args:
            h_upstream: 上游水深 (m)
            h_downstream: 下游水深 (m)
            
        Returns:
            (流量, 流态)
        """
        raise NotImplementedError
    
    def get_status(self) -> Dict:
        """获取闸门状态"""
        return {
            'name': self.name,
            'type': self.__class__.__name__,
            'position': self.position,
            'width': self.width,
            'opening': self.opening,
            'discharge_coeff': self.discharge_coeff
        }


class SluiceGate(BaseGate):
    """
    滑动闸门（平板闸门）
    
    特点：
    1. 最常见的闸门类型
    2. 垂直提升，底部出流
    3. 可自由流或淹没流
    
    流量公式：
    - 自由流: Q = Cd * b * a * sqrt(2*g*h1)
    - 淹没流: Q = Cd * b * a * sqrt(2*g*(h1-h2))
    
    参考：HEC-RAS Sluice Gate
    """
    
    def compute_discharge(
        self,
        h_upstream: float,
        h_downstream: float
    ) -> tuple[float, FlowRegime]:
        """计算滑动闸门流量"""
        g = 9.81
        a = self.opening  # 开度
        b = self.width
        Cd = self.discharge_coeff
        
        # 判断流态
        if h_downstream < 0.67 * h_upstream:
            # 自由流
            Q = Cd * b * a * np.sqrt(2 * g * h_upstream)
            regime = FlowRegime.FREE_FLOW
        else:
            # 淹没流
            dh = max(h_upstream - h_downstream, 0.01)
            Q = Cd * b * a * np.sqrt(2 * g * dh)
            regime = FlowRegime.SUBMERGED
        
        # 记录
        self.flow_history.append(Q)
        self.regime_history.append(regime)
        
        return Q, regime


class RadialGate(BaseGate):
    """
    径向闸门（弧形闸门、塔宾特门）
    
    特点：
    1. 圆弧形门叶，铰链在圆心
    2. 启闭力小，适用于大型水工建筑
    3. 流量系数随开度变化
    
    流量公式：
    - 自由流: Q = Cd(θ) * b * a * sqrt(2*g*h1)
    - 淹没流: Q = Cd(θ) * b * a * sqrt(2*g*(h1-h2))
    
    参考：HEC-RAS Radial Gate, MIKE Radial Gate
    """
    
    def __init__(
        self,
        name: str,
        position: float,
        width: float,
        opening: float,
        radius: float = 5.0,
        discharge_coeff: float = 0.7
    ):
        """
        初始化径向闸门
        
        Args:
            radius: 闸门半径 (m)
        """
        super().__init__(name, position, width, opening, discharge_coeff)
        self.radius = radius
    
    def _compute_adjusted_cd(self, opening_ratio: float) -> float:
        """
        计算调整后的流量系数
        
        径向闸门的Cd随开度变化：
        - 小开度：Cd较小（约0.5-0.6）
        - 中等开度：Cd较大（约0.7-0.8）
        - 大开度：Cd降低（约0.6-0.7）
        """
        # 使用抛物线拟合
        # 在opening_ratio=0.5时达到最大Cd
        Cd_max = self.discharge_coeff * 1.15
        Cd_min = self.discharge_coeff * 0.85
        
        # 抛物线：Cd = Cd_min + (Cd_max-Cd_min) * (1 - (r-0.5)^2 / 0.25)
        Cd = Cd_min + (Cd_max - Cd_min) * (1 - (opening_ratio - 0.5)**2 / 0.25)
        
        return Cd
    
    def compute_discharge(
        self,
        h_upstream: float,
        h_downstream: float
    ) -> tuple[float, FlowRegime]:
        """计算径向闸门流量"""
        g = 9.81
        a = self.opening
        b = self.width
        
        # 调整流量系数
        opening_ratio = min(a / self.radius, 1.0)
        Cd = self._compute_adjusted_cd(opening_ratio)
        
        # 判断流态
        if h_downstream < 0.67 * h_upstream:
            # 自由流
            Q = Cd * b * a * np.sqrt(2 * g * h_upstream)
            regime = FlowRegime.FREE_FLOW
        else:
            # 淹没流
            dh = max(h_upstream - h_downstream, 0.01)
            Q = Cd * b * a * np.sqrt(2 * g * dh)
            regime = FlowRegime.SUBMERGED
        
        self.flow_history.append(Q)
        self.regime_history.append(regime)
        
        return Q, regime
    
    def get_status(self) -> Dict:
        """获取状态"""
        status = super().get_status()
        status['radius'] = self.radius
        status['opening_angle'] = np.arcsin(self.opening / self.radius) * 180 / np.pi
        return status


class VerticalLiftGate(BaseGate):
    """
    垂直提升闸门
    
    特点：
    1. 整体垂直提升
    2. 可用于顶部溢流（大开度）或底部孔流（小开度）
    3. 适用于船闸、大型水闸
    
    流量公式：
    - 底部孔流 (a < 0.5*h1): Q = Cd * b * a * sqrt(2*g*h1)
    - 堰流 (a > 0.8*h1): Q = Cd_weir * b * (h1-H)^1.5
    - 过渡流 (0.5*h1 < a < 0.8*h1): 插值
    
    参考：HEC-RAS Vertical Lift Gate
    """
    
    def __init__(
        self,
        name: str,
        position: float,
        width: float,
        opening: float,
        gate_height: float = 10.0,
        discharge_coeff: float = 0.65,
        weir_coeff: float = 1.7
    ):
        """
        初始化垂直提升闸门
        
        Args:
            gate_height: 闸门总高度 (m)
            weir_coeff: 堰流系数
        """
        super().__init__(name, position, width, opening, discharge_coeff)
        self.gate_height = gate_height
        self.weir_coeff = weir_coeff
    
    def compute_discharge(
        self,
        h_upstream: float,
        h_downstream: float
    ) -> tuple[float, FlowRegime]:
        """计算垂直提升闸门流量"""
        g = 9.81
        a = self.opening
        b = self.width
        
        # 闸门底部高程
        gate_bottom = self.gate_height - a
        
        # 判断流态
        if a < 0.5 * h_upstream:
            # 底部孔流
            Cd = self.discharge_coeff
            
            if h_downstream < 0.67 * h_upstream:
                # 自由孔流
                Q = Cd * b * a * np.sqrt(2 * g * h_upstream)
                regime = FlowRegime.ORIFICE
            else:
                # 淹没孔流
                dh = max(h_upstream - h_downstream, 0.01)
                Q = Cd * b * a * np.sqrt(2 * g * dh)
                regime = FlowRegime.SUBMERGED
        
        elif a > 0.8 * h_upstream:
            # 堰流（闸门高度提升很高）
            # 溢流水头
            H_overflow = max(h_upstream - gate_bottom, 0.0)
            Q = self.weir_coeff * b * H_overflow**1.5
            regime = FlowRegime.WEIR
        
        else:
            # 过渡流态（插值）
            # 在0.5*h1和0.8*h1之间线性插值
            ratio = (a - 0.5*h_upstream) / (0.3*h_upstream)
            
            # 孔流流量
            Cd = self.discharge_coeff
            if h_downstream < 0.67 * h_upstream:
                Q_orifice = Cd * b * a * np.sqrt(2 * g * h_upstream)
            else:
                dh = max(h_upstream - h_downstream, 0.01)
                Q_orifice = Cd * b * a * np.sqrt(2 * g * dh)
            
            # 堰流流量
            H_overflow = max(h_upstream - gate_bottom, 0.0)
            Q_weir = self.weir_coeff * b * H_overflow**1.5
            
            # 插值
            Q = (1 - ratio) * Q_orifice + ratio * Q_weir
            regime = FlowRegime.FREE_FLOW
        
        self.flow_history.append(Q)
        self.regime_history.append(regime)
        
        return Q, regime
    
    def get_status(self) -> Dict:
        """获取状态"""
        status = super().get_status()
        status['gate_height'] = self.gate_height
        status['gate_bottom_elevation'] = self.gate_height - self.opening
        return status


class RollerGate(BaseGate):
    """
    滚轮闸门
    
    特点：
    1. 门叶通过滚轮沿轨道运行
    2. 启闭灵活，摩擦力小
    3. 适用于大跨度闸门
    
    水力特性类似径向闸门
    
    参考：MIKE Roller Gate
    """
    
    def compute_discharge(
        self,
        h_upstream: float,
        h_downstream: float
    ) -> tuple[float, FlowRegime]:
        """计算滚轮闸门流量（类似径向闸门）"""
        g = 9.81
        a = self.opening
        b = self.width
        Cd = self.discharge_coeff * 1.05  # 滚轮闸门Cd略高
        
        if h_downstream < 0.67 * h_upstream:
            Q = Cd * b * a * np.sqrt(2 * g * h_upstream)
            regime = FlowRegime.FREE_FLOW
        else:
            dh = max(h_upstream - h_downstream, 0.01)
            Q = Cd * b * a * np.sqrt(2 * g * dh)
            regime = FlowRegime.SUBMERGED
        
        self.flow_history.append(Q)
        self.regime_history.append(regime)
        
        return Q, regime


class FlapGate(BaseGate):
    """
    翻板闸门
    
    特点：
    1. 门叶绕底部铰链旋转
    2. 可自动翻转（受水压控制）
    3. 适用于防洪、自动调节
    
    流量公式：
    - 自由流: Q = Cd * b * L * sqrt(2*g*h1)
      其中L为翻转后的有效高度
    
    参考：MIKE Flap Gate
    """
    
    def __init__(
        self,
        name: str,
        position: float,
        width: float,
        opening: float,  # 翻转角度 (度)
        gate_length: float = 5.0,
        discharge_coeff: float = 0.65
    ):
        """
        初始化翻板闸门
        
        Args:
            gate_length: 闸门长度 (m)
            opening: 翻转角度 (度, 0=垂直, 90=水平)
        """
        super().__init__(name, position, width, opening, discharge_coeff)
        self.gate_length = gate_length
        self.angle = opening  # 使用opening存储角度
    
    def compute_discharge(
        self,
        h_upstream: float,
        h_downstream: float
    ) -> tuple[float, FlowRegime]:
        """计算翻板闸门流量"""
        g = 9.81
        b = self.width
        
        # 翻转角度（弧度）
        theta = self.angle * np.pi / 180
        
        # 有效过流高度
        L_eff = self.gate_length * np.sin(theta)
        
        # 闸门顶部高程
        gate_top = self.gate_length * np.cos(theta)
        
        if h_upstream > gate_top:
            # 溢流
            H = h_upstream - gate_top
            Q = self.discharge_coeff * b * L_eff * np.sqrt(2 * g * H)
            regime = FlowRegime.WEIR
        else:
            # 无流量
            Q = 0.0
            regime = FlowRegime.FREE_FLOW
        
        self.flow_history.append(Q)
        self.regime_history.append(regime)
        
        return Q, regime
    
    def get_status(self) -> Dict:
        """获取状态"""
        status = super().get_status()
        status['gate_length'] = self.gate_length
        status['angle'] = self.angle
        status['gate_top_elevation'] = self.gate_length * np.cos(self.angle * np.pi / 180)
        return status


# 使用示例
if __name__ == "__main__":
    print("="*60)
    print("高级闸门类型测试")
    print("="*60)
    
    # 测试条件
    h_up = 8.0   # 上游水深
    h_down = 3.0 # 下游水深
    
    # 1. 滑动闸门
    print("\n1. 滑动闸门 (Sluice Gate)")
    print("-" * 60)
    sluice = SluiceGate("SG-001", 500, width=10.0, opening=2.0, discharge_coeff=0.6)
    Q, regime = sluice.compute_discharge(h_up, h_down)
    print(f"流量: {Q:.2f} m³/s, 流态: {regime.value}")
    print(f"状态: {sluice.get_status()}")
    
    # 2. 径向闸门
    print("\n2. 径向闸门 (Radial Gate)")
    print("-" * 60)
    radial = RadialGate("RG-001", 600, width=10.0, opening=2.5, radius=6.0, discharge_coeff=0.7)
    Q, regime = radial.compute_discharge(h_up, h_down)
    print(f"流量: {Q:.2f} m³/s, 流态: {regime.value}")
    print(f"状态: {radial.get_status()}")
    
    # 3. 垂直提升闸门
    print("\n3. 垂直提升闸门 (Vertical Lift Gate)")
    print("-" * 60)
    vertical = VerticalLiftGate("VG-001", 700, width=10.0, opening=3.0, gate_height=12.0)
    Q, regime = vertical.compute_discharge(h_up, h_down)
    print(f"流量: {Q:.2f} m³/s, 流态: {regime.value}")
    print(f"状态: {vertical.get_status()}")
    
    # 4. 滚轮闸门
    print("\n4. 滚轮闸门 (Roller Gate)")
    print("-" * 60)
    roller = RollerGate("RLG-001", 800, width=10.0, opening=2.0, discharge_coeff=0.65)
    Q, regime = roller.compute_discharge(h_up, h_down)
    print(f"流量: {Q:.2f} m³/s, 流态: {regime.value}")
    print(f"状态: {roller.get_status()}")
    
    # 5. 翻板闸门
    print("\n5. 翻板闸门 (Flap Gate)")
    print("-" * 60)
    flap = FlapGate("FG-001", 900, width=10.0, opening=45.0, gate_length=5.0)
    Q, regime = flap.compute_discharge(h_up, h_down)
    print(f"流量: {Q:.2f} m³/s, 流态: {regime.value}")
    print(f"状态: {flap.get_status()}")
    
    print("\n" + "="*60)
    print("测试完成")
    print("="*60)
