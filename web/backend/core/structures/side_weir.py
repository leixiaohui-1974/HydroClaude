#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Side Weir Module
侧堰模块

对标商业软件的侧堰/侧向溢流功能

Author: HydroClaude Team
Date: 2025-11-15
"""

import numpy as np
from typing import Dict, Tuple, Optional


class SideWeir:
    """
    侧堰类
    
    功能：
    1. 侧向溢流计算
    2. 分流流量计算
    3. 水位沿程变化
    4. 动量修正
    
    参考商业软件：
    - HEC-RAS: Lateral Structure
    - MIKE: Side Weir
    """
    
    def __init__(
        self,
        name: str,
        position: float,
        length: float,
        crest_height: float,
        width: Optional[float] = None,
        discharge_coeff: float = 0.4,
        side: str = 'left'  # 'left' or 'right'
    ):
        """
        初始化侧堰
        
        Args:
            name: 侧堰名称
            position: 起始位置 (m)
            length: 侧堰长度 (m)
            crest_height: 堰顶高程 (m)
            width: 主渠宽度 (m)
            discharge_coeff: 流量系数
            side: 侧堰位置（左侧/右侧）
        """
        self.name = name
        self.position = position
        self.length = length
        self.crest_height = crest_height
        self.width = width
        self.discharge_coeff = discharge_coeff
        self.side = side
        
        # 流量历史
        self.diversion_flow_history = []
        self.main_flow_history = []
    
    def compute_discharge(
        self,
        h_upstream: float,
        Q_upstream: float,
        channel_width: float
    ) -> Tuple[float, float]:
        """
        计算侧堰分流
        
        Args:
            h_upstream: 上游水深 (m)
            Q_upstream: 上游流量 (m³/s)
            channel_width: 渠道宽度 (m)
            
        Returns:
            (分流流量, 主流流量)
        """
        g = 9.81
        
        # 过堰水头
        H = max(h_upstream - self.crest_height, 0.0)
        
        if H < 0.001:
            # 水位低于堰顶，无分流
            Q_diversion = 0.0
            Q_main = Q_upstream
        else:
            # 侧堰流量（De Marchi公式）
            # Q = Cd * L * sqrt(2g) * H^1.5
            # 但需要考虑主流动量影响
            
            # 主流流速
            A_main = channel_width * h_upstream
            V_main = Q_upstream / A_main if A_main > 0 else 0
            Fr = V_main / np.sqrt(g * h_upstream) if h_upstream > 0 else 0
            
            # 修正系数（考虑主流动量）
            if Fr < 0.5:
                # 亚临界流，修正系数较大
                correction = 1.0 - 0.2 * Fr
            else:
                # 接近临界或超临界，修正系数减小
                correction = 1.0 - 0.5 * Fr
                correction = max(correction, 0.3)
            
            # 侧堰流量
            Q_diversion = (self.discharge_coeff * correction * 
                          self.length * np.sqrt(2 * g) * H ** 1.5)
            
            # 限制分流流量不超过上游流量的80%
            Q_diversion = min(Q_diversion, 0.8 * Q_upstream)
            
            # 主流流量
            Q_main = Q_upstream - Q_diversion
        
        # 记录
        self.diversion_flow_history.append(Q_diversion)
        self.main_flow_history.append(Q_main)
        
        return Q_diversion, Q_main
    
    def get_status(self) -> Dict:
        """获取侧堰状态"""
        return {
            'name': self.name,
            'position': self.position,
            'length': self.length,
            'crest_height': self.crest_height,
            'discharge_coeff': self.discharge_coeff,
            'side': self.side,
            'total_diversion': sum(self.diversion_flow_history) if self.diversion_flow_history else 0
        }


# 使用示例
if __name__ == "__main__":
    print("="*60)
    print("侧堰模块测试")
    print("="*60)
    
    side_weir = SideWeir(
        name="SW-001",
        position=500.0,
        length=20.0,
        crest_height=2.0,
        discharge_coeff=0.4
    )
    
    print("\n测试不同水深和流量组合")
    print("-"*60)
    
    for h, Q in [(2.5, 50.0), (3.0, 80.0), (3.5, 100.0), (4.0, 120.0)]:
        Q_div, Q_main = side_weir.compute_discharge(h, Q, channel_width=10.0)
        print(f"上游: H={h:.1f}m, Q={Q:.1f}m³/s -> "
              f"分流: {Q_div:.2f}m³/s ({Q_div/Q*100:.1f}%), "
              f"主流: {Q_main:.2f}m³/s ({Q_main/Q*100:.1f}%)")
    
    print(f"\n状态: {side_weir.get_status()}")
    print("\n" + "="*60)
    print("测试完成")
    print("="*60)
