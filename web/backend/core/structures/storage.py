#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Storage/Reservoir Module
水池/水库模块

对标商业软件的调蓄池/水库功能

Author: HydroClaude Team
Date: 2025-11-15
"""

import numpy as np
from typing import Dict, List, Optional, Tuple


class Storage:
    """
    调蓄池/水库类
    
    功能：
    1. 容积-水位关系
    2. 入流-出流平衡
    3. 水位演算
    4. 滞洪演算
    5. 溢流计算
    
    参考商业软件：
    - HEC-RAS: Storage Area
    - MIKE: Basin
    - InfoWorks: Storage Tank
    """
    
    def __init__(
        self,
        name: str,
        position: float,
        # 容积曲线（水位-面积-容积）
        elevation: List[float],
        area: List[float],
        # 或直接给定容积
        volume: Optional[List[float]] = None,
        # 初始条件
        initial_elevation: float = 0.0,
        initial_volume: float = 0.0,
        # 溢流参数
        spillway_elevation: Optional[float] = None,
        spillway_width: Optional[float] = None,
        spillway_coeff: float = 1.7
    ):
        """
        初始化调蓄池
        
        Args:
            name: 名称
            position: 位置 (m)
            elevation: 水位列表 (m)
            area: 对应面积列表 (m²)
            volume: 对应容积列表 (m³, 可选)
            initial_elevation: 初始水位 (m)
            initial_volume: 初始容积 (m³)
            spillway_elevation: 溢洪道高程 (m)
            spillway_width: 溢洪道宽度 (m)
            spillway_coeff: 溢洪道流量系数
        """
        self.name = name
        self.position = position
        self.elevation = np.array(elevation)
        self.area = np.array(area)
        
        # 计算容积曲线（如果没有提供）
        if volume is None:
            self.volume = self._compute_volume_curve()
        else:
            self.volume = np.array(volume)
        
        # 初始条件
        self.current_elevation = initial_elevation
        self.current_volume = initial_volume
        
        # 溢洪道
        self.spillway_elevation = spillway_elevation
        self.spillway_width = spillway_width
        self.spillway_coeff = spillway_coeff
        
        # 历史记录
        self.elevation_history = [initial_elevation]
        self.volume_history = [initial_volume]
        self.inflow_history = []
        self.outflow_history = []
        self.spillway_flow_history = []
    
    def _compute_volume_curve(self) -> np.ndarray:
        """计算容积曲线（分层求和法）"""
        volume = np.zeros_like(self.elevation)
        
        for i in range(1, len(self.elevation)):
            dh = self.elevation[i] - self.elevation[i-1]
            avg_area = (self.area[i] + self.area[i-1]) / 2
            dv = avg_area * dh
            volume[i] = volume[i-1] + dv
        
        return volume
    
    def get_area(self, elev: float) -> float:
        """根据水位插值得到面积"""
        if elev <= self.elevation[0]:
            return self.area[0]
        elif elev >= self.elevation[-1]:
            return self.area[-1]
        else:
            return float(np.interp(elev, self.elevation, self.area))
    
    def get_volume(self, elev: float) -> float:
        """根据水位插值得到容积"""
        if elev <= self.elevation[0]:
            return self.volume[0]
        elif elev >= self.elevation[-1]:
            # 超过最高水位，外推
            extra_volume = (elev - self.elevation[-1]) * self.area[-1]
            return self.volume[-1] + extra_volume
        else:
            return float(np.interp(elev, self.elevation, self.volume))
    
    def get_elevation(self, vol: float) -> float:
        """根据容积反算水位"""
        if vol <= self.volume[0]:
            return self.elevation[0]
        elif vol >= self.volume[-1]:
            # 超过最大容积，外推
            extra_height = (vol - self.volume[-1]) / self.area[-1]
            return self.elevation[-1] + extra_height
        else:
            return float(np.interp(vol, self.volume, self.elevation))
    
    def compute_spillway_flow(self) -> float:
        """计算溢洪道流量"""
        if self.spillway_elevation is None or self.spillway_width is None:
            return 0.0
        
        H = max(self.current_elevation - self.spillway_elevation, 0.0)
        
        if H < 0.001:
            return 0.0
        
        # 堰流公式
        Q_spillway = self.spillway_coeff * self.spillway_width * H ** 1.5
        
        return Q_spillway
    
    def route(
        self,
        Q_in: float,
        Q_out: float,
        dt: float
    ) -> Tuple[float, float]:
        """
        水量平衡演算（一个时间步）
        
        Args:
            Q_in: 入流流量 (m³/s)
            Q_out: 控制出流流量 (m³/s)
            dt: 时间步长 (s)
            
        Returns:
            (新水位, 总出流)
        """
        # 溢洪道流量
        Q_spillway = self.compute_spillway_flow()
        
        # 总出流
        Q_total_out = Q_out + Q_spillway
        
        # 水量平衡
        dV = (Q_in - Q_total_out) * dt
        
        # 新容积
        new_volume = self.current_volume + dV
        new_volume = max(new_volume, self.volume[0])  # 不低于最低容积
        
        # 新水位
        new_elevation = self.get_elevation(new_volume)
        
        # 更新状态
        self.current_volume = new_volume
        self.current_elevation = new_elevation
        
        # 记录
        self.elevation_history.append(new_elevation)
        self.volume_history.append(new_volume)
        self.inflow_history.append(Q_in)
        self.outflow_history.append(Q_out)
        self.spillway_flow_history.append(Q_spillway)
        
        return new_elevation, Q_total_out
    
    def get_status(self) -> Dict:
        """获取状态"""
        return {
            'name': self.name,
            'current_elevation': self.current_elevation,
            'current_volume': self.current_volume,
            'current_area': self.get_area(self.current_elevation),
            'max_elevation': float(self.elevation[-1]),
            'max_volume': float(self.volume[-1]),
            'spillway_elevation': self.spillway_elevation,
            'spillway_width': self.spillway_width
        }


# 使用示例
if __name__ == "__main__":
    print("="*60)
    print("调蓄池/水库模块测试")
    print("="*60)
    
    # 创建调蓄池（梯形断面）
    elevation = [0.0, 2.0, 4.0, 6.0, 8.0, 10.0]
    area = [100.0, 400.0, 900.0, 1600.0, 2500.0, 3600.0]  # 面积随高度增加
    
    storage = Storage(
        name="Basin-001",
        position=1000.0,
        elevation=elevation,
        area=area,
        initial_elevation=3.0,
        spillway_elevation=8.0,
        spillway_width=10.0
    )
    
    print(f"\n初始状态:")
    print(f"  水位: {storage.current_elevation:.2f} m")
    print(f"  容积: {storage.current_volume:.2f} m³")
    print(f"  面积: {storage.get_area(storage.current_elevation):.2f} m²")
    
    # 模拟洪水过程
    print("\n模拟洪水演算（入流100 m³/s，出流30 m³/s）")
    print("-"*60)
    
    dt = 60.0  # 时间步长60秒
    
    for t in range(0, 3600, 300):  # 模拟1小时
        Q_in = 100.0  # 入流
        Q_out = 30.0  # 控制出流
        
        new_elev, total_out = storage.route(Q_in, Q_out, dt)
        
        if t % 600 == 0:
            spillway_Q = storage.spillway_flow_history[-1]
            print(f"时间 {t//60:3d} min: "
                  f"水位={new_elev:.2f}m, "
                  f"入流={Q_in:.1f}m³/s, "
                  f"控制出流={Q_out:.1f}m³/s, "
                  f"溢流={spillway_Q:.1f}m³/s, "
                  f"总出流={total_out:.1f}m³/s")
    
    print(f"\n最终状态: {storage.get_status()}")
    
    print("\n" + "="*60)
    print("测试完成")
    print("="*60)
