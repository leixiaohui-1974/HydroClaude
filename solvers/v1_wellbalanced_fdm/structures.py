#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
水工结构物：闸门、泵站、堰

完全重新设计，基于HEC-RAS和MIKE 11的方法论：
1. 闸门：淹没/自由流动，精确流量公式
2. 泵站：能量跃变（h⁺ = h⁻ + H_pump），内部边界条件法
3. 堰：宽顶堰，标准堰流公式

关键改进：
- 守恒的边界条件（不再"平滑"邻近节点）
- 精确的导数计算（解析雅可比）
- 干湿处理
- 能量方程兼容

Author: Claude (AI Assistant)
Date: 2025-10-27
License: MIT
"""

import numpy as np
from typing import Tuple, Optional
from enum import Enum


class FlowRegime(Enum):
    """流态类型"""
    FREE_FLOW = "free_flow"          # 自由流动
    SUBMERGED_FLOW = "submerged"     # 淹没流动
    DROWNED_FLOW = "drowned"         # 完全淹没
    DRY = "dry"                      # 干
    REVERSE_FLOW = "reverse"         # 回流


class HydraulicStructure:
    """
    水工结构物基类
    
    所有结构物（闸门、泵站、堰）的基类，定义通用接口。
    
    关键方法：
    - calculate_discharge(): 计算过流量
    - calculate_derivatives(): 计算流量对水深的导数（用于雅可比）
    - get_energy_change(): 能量变化（用于能量方程）
    """
    
    def __init__(self, position: float, width: float, g: float = 9.81):
        """
        初始化结构物
        
        Args:
            position: 位置 (m)
            width: 宽度 (m)
            g: 重力加速度 (m/s²)
        """
        self.position = position
        self.width = width
        self.g = g
        self.name = "Generic Structure"
    
    def calculate_discharge(self, 
                           h_upstream: float, 
                           h_downstream: float,
                           t: Optional[float] = None) -> Tuple[float, FlowRegime]:
        """
        计算过流量（必须由子类实现）
        
        Args:
            h_upstream: 上游水深 (m)
            h_downstream: 下游水深 (m)
            t: 时间 (s)，可选（用于时变结构）
        
        Returns:
            (Q, regime): 流量 (m³/s) 和流态类型
        """
        raise NotImplementedError("子类必须实现calculate_discharge")
    
    def calculate_derivatives(self,
                            h_upstream: float,
                            h_downstream: float,
                            t: Optional[float] = None) -> Tuple[float, float]:
        """
        计算流量对水深的导数（解析）
        
        用于构造雅可比矩阵，提高牛顿法收敛速度。
        
        Args:
            h_upstream, h_downstream: 上下游水深
            t: 时间
        
        Returns:
            (dQ_dh_up, dQ_dh_down): 偏导数
        """
        raise NotImplementedError("子类必须实现calculate_derivatives")
    
    def get_energy_change(self,
                         h_upstream: float,
                         h_downstream: float,
                         Q: float) -> float:
        """
        计算能量变化（用于能量方程）
        
        ΔE = E_down - E_up
        
        对于：
        - 闸门/堰：ΔE < 0（能量损失）
        - 泵站：ΔE > 0（能量增加）
        
        Args:
            h_upstream, h_downstream: 上下游水深
            Q: 流量
        
        Returns:
            ΔE: 能量变化 (m)
        """
        raise NotImplementedError("子类必须实现get_energy_change")
    
    def __repr__(self) -> str:
        return f"{self.name}(position={self.position}m, width={self.width}m)"


class SluiceGate(HydraulicStructure):
    """
    闸门（Sluice Gate）
    
    标准水利闸门，可调节开度a。
    
    流量公式：
    - 自由流动：Q = C_d * a * B * sqrt(2g * h_up)
    - 淹没流动：Q = C_d * a * B * sqrt(2g * (h_up - h_down))
    
    流态判别：
    - h_down / h_up < 0.67: 自由流动
    - h_down / h_up >= 0.67: 淹没流动
    
    参考：HEC-RAS Reference Manual, Section 7.6
    """
    
    def __init__(self,
                 position: float,
                 width: float,
                 opening: float = 1.0,
                 discharge_coeff: float = 0.6,
                 g: float = 9.81,
                 eps_dry: float = 0.01):
        """
        初始化闸门
        
        Args:
            position: 位置 (m)
            width: 闸门宽度 (m)
            opening: 开度 (m)
            discharge_coeff: 流量系数，一般0.55-0.65
            g: 重力加速度 (m/s²)
            eps_dry: 干湿阈值 (m)
        """
        super().__init__(position, width, g)
        self.name = "SluiceGate"
        self.opening = opening
        self.C_d = discharge_coeff
        self.eps_dry = eps_dry
        
        # 流态判别阈值
        self.submergence_ratio_threshold = 0.67
    
    def set_opening(self, opening: float):
        """设置闸门开度"""
        self.opening = max(0.0, opening)
    
    def calculate_discharge(self,
                           h_upstream: float,
                           h_downstream: float,
                           t: Optional[float] = None) -> Tuple[float, FlowRegime]:
        """
        计算闸门流量
        
        流态分类：
        1. 上游干（h_up < eps_dry）→ Q = 0
        2. 开度关闭（a = 0）→ Q = 0
        3. 淹没比 < 0.67 → 自由流动
        4. 淹没比 >= 0.67 → 淹没流动
        
        Args:
            h_upstream: 上游水深
            h_downstream: 下游水深
            t: 时间（可选）
        
        Returns:
            (Q, regime): 流量和流态
        """
        a = self.opening
        
        # 情况1：干或闸门关闭
        if h_upstream < self.eps_dry or a < 1e-6:
            return 0.0, FlowRegime.DRY
        
        # 情况2：开度大于上游水深（全开）
        if a >= h_upstream:
            # 类似堰流
            Q = self.C_d * self.width * h_upstream * np.sqrt(2 * self.g * h_upstream)
            return Q, FlowRegime.FREE_FLOW
        
        # 情况3：淹没比判别
        submergence_ratio = h_downstream / h_upstream
        
        if submergence_ratio < self.submergence_ratio_threshold:
            # 自由流动（下游水位不影响）
            Q = self.C_d * a * self.width * np.sqrt(2 * self.g * h_upstream)
            regime = FlowRegime.FREE_FLOW
        else:
            # 淹没流动（下游水位影响）
            delta_h = max(h_upstream - h_downstream, 0.01)  # 防止负值
            Q = self.C_d * a * self.width * np.sqrt(2 * self.g * delta_h)
            regime = FlowRegime.SUBMERGED_FLOW
        
        return Q, regime
    
    def calculate_derivatives(self,
                            h_upstream: float,
                            h_downstream: float,
                            t: Optional[float] = None) -> Tuple[float, float]:
        """
        计算闸门流量导数（解析）
        
        dQ/dh_up:
        - 自由流动：d/dh(C_d*a*B*sqrt(2gh)) = C_d*a*B*sqrt(g/(2h))
        - 淹没流动：d/dh(C_d*a*B*sqrt(2g(h_up-h_down))) = C_d*a*B*g/sqrt(2g*Δh)
        
        dQ/dh_down:
        - 自由流动：0（下游不影响）
        - 淹没流动：-C_d*a*B*g/sqrt(2g*Δh)
        
        Args:
            h_upstream, h_downstream: 上下游水深
            t: 时间
        
        Returns:
            (dQ_dh_up, dQ_dh_down): 偏导数
        """
        a = self.opening
        
        # 干或关闭
        if h_upstream < self.eps_dry or a < 1e-6:
            return 0.0, 0.0
        
        # 判断流态
        submergence_ratio = h_downstream / h_upstream
        
        if submergence_ratio < self.submergence_ratio_threshold:
            # 自由流动
            dQ_dh_up = 0.5 * self.C_d * a * self.width * np.sqrt(2 * self.g / h_upstream)
            dQ_dh_down = 0.0
        else:
            # 淹没流动
            delta_h = max(h_upstream - h_downstream, 0.01)
            factor = self.C_d * a * self.width * np.sqrt(0.5 * self.g / delta_h)
            dQ_dh_up = factor
            dQ_dh_down = -factor
        
        return dQ_dh_up, dQ_dh_down
    
    def get_energy_change(self,
                         h_upstream: float,
                         h_downstream: float,
                         Q: float) -> float:
        """
        闸门能量损失
        
        局部水头损失：h_loss = K * V²/(2g)
        其中K为局部阻力系数，一般0.5-1.0
        
        Args:
            h_upstream, h_downstream: 上下游水深
            Q: 流量
        
        Returns:
            ΔE: 能量变化（负值，损失）
        """
        # 上游流速
        V_up = Q / (self.width * h_upstream) if h_upstream > self.eps_dry else 0.0
        
        # 局部损失系数
        K_loss = 0.5
        
        # 水头损失
        h_loss = K_loss * V_up**2 / (2 * self.g)
        
        return -h_loss  # 负值表示损失


class PumpStation(HydraulicStructure):
    """
    泵站（Pump Station）
    
    方法：内部边界条件法（v4.0，已验证）
    
    物理模型：
    - 质量守恒：Q⁺ = Q⁻（流量连续）
    - 能量跃变：h⁺ = h⁻ + H_pump（水位抬升）
    
    这是HEC-RAS、MIKE 11等商业软件的标准方法。
    
    特性曲线（可选）：
    - 当前：固定扬程（额定工况）
    - 未来：Q-H曲线（变工况）
    
    参考：
    - HEC-RAS Reference Manual, Section 7.8
    - 本项目：PUMP_FIX_SUMMARY_CN.md
    """
    
    def __init__(self,
                 position: float,
                 width: float,
                 rated_flow: float = 30.0,
                 rated_head: float = 5.0,
                 min_suction_head: float = 2.0,
                 g: float = 9.81,
                 eps_dry: float = 0.01):
        """
        初始化泵站
        
        Args:
            position: 位置 (m)
            width: 宽度 (m)
            rated_flow: 额定流量 (m³/s)
            rated_head: 额定扬程 (m)
            min_suction_head: 最小吸入水头 (m)
            g: 重力加速度
            eps_dry: 干湿阈值
        """
        super().__init__(position, width, g)
        self.name = "PumpStation"
        self.rated_flow = rated_flow
        self.rated_head = rated_head
        self.min_suction_head = min_suction_head
        self.eps_dry = eps_dry
        
        # 运行状态
        self.is_running = True
    
    def set_running_state(self, is_running: bool):
        """设置泵站运行状态"""
        self.is_running = is_running
    
    def calculate_discharge(self,
                           h_upstream: float,
                           h_downstream: float,
                           t: Optional[float] = None) -> Tuple[float, FlowRegime]:
        """
        计算泵站流量
        
        简化模型（额定工况）：
        - 运行中 + h_up >= h_min：Q = Q_rated
        - 低水位（h_up < h_min）：Q = Q_rated * sqrt(h_up / h_min)
        - 停止或干：Q = 0
        
        Args:
            h_upstream: 上游水深
            h_downstream: 下游水深（泵站不依赖下游）
            t: 时间
        
        Returns:
            (Q, regime): 流量和状态
        """
        if not self.is_running:
            return 0.0, FlowRegime.DRY
        
        if h_upstream < self.eps_dry:
            return 0.0, FlowRegime.DRY
        
        if h_upstream >= self.min_suction_head:
            # 正常运行
            Q = self.rated_flow
            regime = FlowRegime.FREE_FLOW
        else:
            # 低水位，流量减少
            ratio = np.sqrt(h_upstream / self.min_suction_head)
            Q = self.rated_flow * ratio
            regime = FlowRegime.SUBMERGED_FLOW
        
        return Q, regime
    
    def calculate_derivatives(self,
                            h_upstream: float,
                            h_downstream: float,
                            t: Optional[float] = None) -> Tuple[float, float]:
        """
        泵站流量导数
        
        特点：
        - 正常运行时（h >= h_min）：dQ/dh = 0（流量恒定）
        - 低水位时（h < h_min）：dQ/dh > 0
        - 不依赖下游：dQ/dh_down = 0
        
        Args:
            h_upstream, h_downstream: 上下游水深
            t: 时间
        
        Returns:
            (dQ_dh_up, dQ_dh_down): 偏导数
        """
        if not self.is_running or h_upstream < self.eps_dry:
            return 0.0, 0.0
        
        if h_upstream >= self.min_suction_head:
            # 正常运行：流量恒定
            dQ_dh_up = 0.0
        else:
            # 低水位：Q = Q_rated * sqrt(h / h_min)
            # dQ/dh = Q_rated / (2*sqrt(h * h_min))
            dQ_dh_up = self.rated_flow / (2.0 * np.sqrt(h_upstream * self.min_suction_head))
        
        # 泵站不依赖下游
        dQ_dh_down = 0.0
        
        return dQ_dh_up, dQ_dh_down
    
    def get_energy_change(self,
                         h_upstream: float,
                         h_downstream: float,
                         Q: float) -> float:
        """
        泵站能量增加
        
        泵站做功，增加水流能量：
        ΔE = H_rated（额定扬程）
        
        Args:
            h_upstream, h_downstream: 上下游水深
            Q: 流量
        
        Returns:
            ΔE: 能量变化（正值，增加）
        """
        if not self.is_running:
            return 0.0
        
        return self.rated_head  # 正值表示增加
    
    def get_head(self,
                h_upstream: float,
                h_downstream: float) -> float:
        """
        获取实际扬程（用于验证）
        
        实际扬程 = 下游水深 - 上游水深
        
        理想情况：应该等于rated_head
        """
        return h_downstream - h_upstream


class BroadCrestedWeir(HydraulicStructure):
    """
    宽顶堰（Broad-Crested Weir）
    
    标准堰流公式：Q = C_d * B * H^(3/2)
    其中H为堰上水头
    
    流态：
    - 自由流动：下游水位低于堰顶
    - 淹没流动：下游水位高于堰顶
    
    参考：HEC-RAS Reference Manual, Section 7.7
    """
    
    def __init__(self,
                 position: float,
                 width: float,
                 crest_height: float = 0.5,
                 discharge_coeff: float = 1.7,
                 g: float = 9.81,
                 eps_dry: float = 0.01):
        """
        初始化宽顶堰
        
        Args:
            position: 位置 (m)
            width: 堰宽 (m)
            crest_height: 堰顶高程 (m)
            discharge_coeff: 流量系数，一般1.6-1.8
            g: 重力加速度
            eps_dry: 干湿阈值
        """
        super().__init__(position, width, g)
        self.name = "BroadCrestedWeir"
        self.crest_height = crest_height
        self.C_d = discharge_coeff
        self.eps_dry = eps_dry
        
        # 淹没判别阈值
        self.submergence_threshold = 0.9
    
    def calculate_discharge(self,
                           h_upstream: float,
                           h_downstream: float,
                           t: Optional[float] = None) -> Tuple[float, FlowRegime]:
        """
        计算堰流量
        
        流态判别：
        1. h_up < p: 无流动（上游水位低于堰顶）
        2. h_down < p: 自由流动
        3. h_down >= p: 淹没流动（需修正系数）
        
        Args:
            h_upstream, h_downstream: 上下游水深
            t: 时间
        
        Returns:
            (Q, regime): 流量和流态
        """
        p = self.crest_height
        
        # 堰上水头
        H_up = h_upstream - p
        H_down = h_downstream - p
        
        # 情况1：无流动
        if H_up <= self.eps_dry:
            return 0.0, FlowRegime.DRY
        
        # 情况2：自由流动
        if H_down <= 0 or H_down / H_up < self.submergence_threshold:
            Q = self.C_d * self.width * H_up**(1.5)
            regime = FlowRegime.FREE_FLOW
        else:
            # 情况3：淹没流动（修正）
            submergence_factor = 1.0 - (H_down / H_up)**1.5
            Q = self.C_d * self.width * H_up**(1.5) * submergence_factor
            regime = FlowRegime.SUBMERGED_FLOW
        
        return max(Q, 0.0), regime
    
    def calculate_derivatives(self,
                            h_upstream: float,
                            h_downstream: float,
                            t: Optional[float] = None) -> Tuple[float, float]:
        """
        堰流量导数
        
        自由流动：
        Q = C*H^(3/2)
        dQ/dH = 1.5*C*H^(1/2)
        
        Args:
            h_upstream, h_downstream: 上下游水深
            t: 时间
        
        Returns:
            (dQ_dh_up, dQ_dh_down): 偏导数
        """
        p = self.crest_height
        H_up = h_upstream - p
        H_down = h_downstream - p
        
        if H_up <= self.eps_dry:
            return 0.0, 0.0
        
        # 自由流动
        if H_down <= 0 or H_down / H_up < self.submergence_threshold:
            dQ_dh_up = 1.5 * self.C_d * self.width * np.sqrt(H_up)
            dQ_dh_down = 0.0
        else:
            # 淹没流动（简化：用数值导数）
            eps = 0.01
            Q_base, _ = self.calculate_discharge(h_upstream, h_downstream)
            Q_pert_up, _ = self.calculate_discharge(h_upstream + eps, h_downstream)
            Q_pert_down, _ = self.calculate_discharge(h_upstream, h_downstream + eps)
            
            dQ_dh_up = (Q_pert_up - Q_base) / eps
            dQ_dh_down = (Q_pert_down - Q_base) / eps
        
        return dQ_dh_up, dQ_dh_down
    
    def get_energy_change(self,
                         h_upstream: float,
                         h_downstream: float,
                         Q: float) -> float:
        """
        堰流能量损失
        
        局部损失 + 流态转换损失
        
        Args:
            h_upstream, h_downstream: 上下游水深
            Q: 流量
        
        Returns:
            ΔE: 能量变化（负值，损失）
        """
        if Q < 1e-6:
            return 0.0
        
        # 流速
        V_up = Q / (self.width * h_upstream) if h_upstream > self.eps_dry else 0.0
        
        # 损失系数
        K_loss = 0.3
        
        # 水头损失
        h_loss = K_loss * V_up**2 / (2 * self.g)
        
        return -h_loss


# ========== 测试代码 ==========

def test_structures():
    """测试各种结构物"""
    print("\n" + "="*60)
    print("测试: 水工结构物")
    print("="*60)
    
    # 测试1：闸门
    print("\n测试1: 闸门流量计算")
    gate = SluiceGate(position=5000.0, width=10.0, opening=3.0)
    h_up, h_down = 4.0, 2.0
    Q, regime = gate.calculate_discharge(h_up, h_down)
    dQ_dup, dQ_ddown = gate.calculate_derivatives(h_up, h_down)
    
    print(f"闸门: {gate}")
    print(f"上游水深: {h_up}m, 下游水深: {h_down}m")
    print(f"流量: {Q:.3f} m³/s")
    print(f"流态: {regime.value}")
    print(f"导数: dQ/dh_up={dQ_dup:.3f}, dQ/dh_down={dQ_ddown:.3f}")
    
    # 测试2：泵站
    print("\n测试2: 泵站能量跃变")
    pump = PumpStation(position=10000.0, width=10.0, 
                       rated_flow=30.0, rated_head=5.0)
    h_up, h_down = 2.0, 7.0  # 下游水位应该高5m
    Q, regime = pump.calculate_discharge(h_up, h_down)
    H_actual = pump.get_head(h_up, h_down)
    dE = pump.get_energy_change(h_up, h_down, Q)
    
    print(f"泵站: {pump}")
    print(f"上游水深: {h_up}m, 下游水深: {h_down}m")
    print(f"流量: {Q:.3f} m³/s")
    print(f"实际扬程: {H_actual:.3f}m (目标: {pump.rated_head}m)")
    print(f"能量增加: {dE:.3f}m")
    
    # 测试3：堰
    print("\n测试3: 宽顶堰")
    weir = BroadCrestedWeir(position=15000.0, width=10.0, crest_height=0.5)
    h_up, h_down = 2.0, 0.8
    Q, regime = weir.calculate_discharge(h_up, h_down)
    dQ_dup, dQ_ddown = weir.calculate_derivatives(h_up, h_down)
    
    print(f"堰: {weir}")
    print(f"上游水深: {h_up}m, 下游水深: {h_down}m")
    print(f"堰上水头: {h_up - weir.crest_height:.3f}m")
    print(f"流量: {Q:.3f} m³/s")
    print(f"流态: {regime.value}")
    
    print("\n" + "="*60)
    print("✓ 结构物测试完成")
    print("="*60)


if __name__ == '__main__':
    test_structures()
