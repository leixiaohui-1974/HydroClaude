"""
Dual Flow Pipe Module - 明满流管道模块

Implements Preissmann Slot method for open-channel/pressurized flow transition.

Author: HydroClaude Development Team
Date: 2025-10-30
Version: 1.0.0
"""

import numpy as np
from typing import Tuple, Literal


class DualFlowPipe:
    """
    明满流转换管道 - Dual Flow Pipe (Open/Pressurized)
    
    使用Preissmann Slot法（虚拟狭缝法）实现明流和满流的平滑过渡。
    
    原理 Principle:
    在圆管顶部添加虚拟狭缝，使满管流也能用明渠方程求解。
    当h > D时，水进入虚拟狭缝，形成有压流动。
    
    优点 Advantages:
    - 方程统一，无需切换判断
    - 连续性好，数值稳定
    - 避免明满流切换的数值震荡
    """

    def __init__(self, diameter: float, length: float, roughness: float,
                 slot_width: float = None, wave_speed: float = 1000.0):
        """
        初始化明满流管道
        
        Args:
            diameter: 管径 (m)
            length: 长度 (m)
            roughness: 粗糙度 (Manning's n or absolute roughness)
            slot_width: 虚拟狭缝宽度 (m)，如果为None则自动计算
            wave_speed: 波速 (m/s)，用于计算狭缝宽度
        """
        self.D = float(diameter)
        self.L = float(length)
        self.n = float(roughness)
        self.c = float(wave_speed)
        
        # 计算狭缝宽度
        if slot_width is None:
            self.b_slot = self._calculate_slot_width()
        else:
            self.b_slot = float(slot_width)
        
        # 管道满流面积
        self.A_full = np.pi * (self.D / 2.0)**2
    
    def _calculate_slot_width(self) -> float:
        """
        计算Preissmann虚拟狭缝宽度
        
        公式: b = A_full / (g * dt * c)
        简化: b = A_full / (波速 * 特征时间)
        
        实际应用中通常取：b = 0.01 * D 到 0.1 * D
        """
        # 保守估计：取较小的狭缝宽度以保证数值稳定
        b = 0.01 * self.D
        return b
    
    def flow_area(self, h: float) -> float:
        """
        计算过水面积（考虑虚拟狭缝）
        
        Args:
            h: 水深 (m)，h < D为明流，h >= D为满流
        
        Returns:
            过水面积 (m²)
        """
        if h <= 0:
            return 0.0
        elif h < self.D:
            # 明流：圆管部分充满
            return self._circular_area(h)
        else:
            # 满流：圆管全满 + 虚拟狭缝
            A_slot = self.b_slot * (h - self.D)
            return self.A_full + A_slot
    
    def _circular_area(self, h: float) -> float:
        """
        圆管部分充满时的过水面积
        
        A = (D²/4) * (θ - sin(θ))
        其中 θ = 2*arccos((D/2 - h)/(D/2)) = 2*arccos(1 - 2h/D)
        """
        if h <= 0:
            return 0.0
        if h >= self.D:
            return self.A_full
        
        # 无量纲水深
        h_ratio = h / self.D
        
        # 角度θ（弧度）
        theta = 2.0 * np.arccos(1.0 - 2.0 * h_ratio)
        
        # 面积
        A = (self.D**2 / 4.0) * (theta - np.sin(theta))
        
        return A
    
    def wetted_perimeter(self, h: float) -> float:
        """
        计算湿周
        
        Args:
            h: 水深 (m)
        
        Returns:
            湿周 (m)
        """
        if h <= 0:
            return 0.0
        elif h < self.D:
            # 明流：圆弧长度
            h_ratio = h / self.D
            theta = 2.0 * np.arccos(1.0 - 2.0 * h_ratio)
            P = (self.D / 2.0) * theta
            return P
        else:
            # 满流：整个圆周
            return np.pi * self.D
    
    def hydraulic_radius(self, h: float) -> float:
        """
        计算水力半径 R = A / P
        
        Args:
            h: 水深 (m)
        
        Returns:
            水力半径 (m)
        """
        A = self.flow_area(h)
        P = self.wetted_perimeter(h)
        
        if P > 0:
            return A / P
        else:
            return 0.0
    
    def top_width(self, h: float) -> float:
        """
        计算水面宽度
        
        Args:
            h: 水深 (m)
        
        Returns:
            水面宽度 (m)
        """
        if h <= 0:
            return 0.0
        elif h < self.D:
            # 明流：弦长
            h_ratio = h / self.D
            if h_ratio >= 1.0:
                return self.D
            T = self.D * np.sqrt(h_ratio * (2.0 - h_ratio))
            return T
        else:
            # 满流：虚拟狭缝宽度
            return self.b_slot
    
    def is_pressurized(self, h: float, threshold: float = 0.99) -> bool:
        """
        判断是否为满管流
        
        Args:
            h: 水深 (m)
            threshold: 满管判断阈值（默认0.99，即99%充满度）
        
        Returns:
            True表示满管流，False表示明渠流
        """
        return h >= threshold * self.D
    
    def flow_type(self, h: float) -> Literal["open", "transitional", "pressurized"]:
        """
        判断流态类型
        
        Args:
            h: 水深 (m)
        
        Returns:
            "open": 明流
            "transitional": 过渡流
            "pressurized": 满管流
        """
        h_ratio = h / self.D
        
        if h_ratio < 0.95:
            return "open"
        elif h_ratio < 1.05:
            return "transitional"
        else:
            return "pressurized"
    
    def critical_depth(self, Q: float) -> float:
        """
        计算临界水深（明流时）
        
        使用迭代法求解: Q² * T / (g * A³) = 1
        
        Args:
            Q: 流量 (m³/s)
        
        Returns:
            临界水深 (m)
        """
        if Q <= 0:
            return 0.0
        
        g = 9.81
        
        # 初始估计
        h_c = 0.5 * self.D
        
        # 迭代求解
        for _ in range(20):
            A = self.flow_area(h_c)
            T = self.top_width(h_c)
            
            if A <= 0 or T <= 0:
                break
            
            # Froude数平方
            Fr2 = Q**2 * T / (g * A**3)
            
            # 残差
            residual = Fr2 - 1.0
            
            if abs(residual) < 1e-6:
                break
            
            # 简单修正
            if Fr2 > 1.0:
                h_c *= 1.05
            else:
                h_c *= 0.95
            
            # 边界限制
            h_c = max(0.01 * self.D, min(h_c, 0.99 * self.D))
        
        return h_c
    
    def properties(self, h: float) -> dict:
        """
        计算指定水深的所有水力特性
        
        Args:
            h: 水深 (m)
        
        Returns:
            水力特性字典
        """
        return {
            'h': h,
            'A': self.flow_area(h),
            'P': self.wetted_perimeter(h),
            'R': self.hydraulic_radius(h),
            'T': self.top_width(h),
            'flow_type': self.flow_type(h),
            'is_pressurized': self.is_pressurized(h)
        }
    
    def __repr__(self) -> str:
        return (f"DualFlowPipe(D={self.D:.3f}m, L={self.L:.1f}m, "
                f"b_slot={self.b_slot:.6f}m)")
