#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Reservoir/Lake Module
水库/湖泊模块

包括：水库、湖泊、调蓄池等

Author: HydroClaude Team
Date: 2025-11-15
"""

import numpy as np
from typing import Dict, List, Optional, Tuple


class Reservoir:
    """
    水库/湖泊类
    
    功能：
    1. 容积-水位-面积关系
    2. 水量平衡
    3. 调度规则
    4. 库容曲线
    5. 泄流计算
    
    参考商业软件：
    - HEC-ResSim: 水库调度
    - MIKE: Reservoir
    """
    
    def __init__(
        self,
        name: str,
        # 特征水位
        dead_level: float,           # 死水位 (m)
        normal_level: float,          # 正常蓄水位 (m)
        flood_limit_level: float,     # 防洪限制水位 (m)
        design_flood_level: float,    # 设计洪水位 (m)
        check_flood_level: float,     # 校核洪水位 (m)
        # 容积曲线
        elevation: List[float],       # 高程列表 (m)
        area: List[float],            # 对应面积列表 (m²)
        volume: Optional[List[float]] = None,  # 容积列表 (m³)
        # 初始条件
        initial_level: float = None
    ):
        """
        初始化水库
        
        Args:
            name: 水库名称
            dead_level: 死水位
            normal_level: 正常蓄水位
            flood_limit_level: 防洪限制水位
            design_flood_level: 设计洪水位
            check_flood_level: 校核洪水位
            elevation: 高程列表
            area: 面积列表
            volume: 容积列表
            initial_level: 初始水位
        """
        self.name = name
        self.dead_level = dead_level
        self.normal_level = normal_level
        self.flood_limit_level = flood_limit_level
        self.design_flood_level = design_flood_level
        self.check_flood_level = check_flood_level
        
        self.elevation = np.array(elevation)
        self.area = np.array(area)
        
        # 计算容积曲线
        if volume is None:
            self.volume = self._compute_volume_curve()
        else:
            self.volume = np.array(volume)
        
        # 当前状态
        self.current_level = initial_level or normal_level
        self.current_volume = self.get_volume(self.current_level)
        
        # 历史记录
        self.level_history = [self.current_level]
        self.volume_history = [self.current_volume]
        self.inflow_history = []
        self.outflow_history = []
    
    def _compute_volume_curve(self) -> np.ndarray:
        """计算容积曲线（分层求和法）"""
        volume = np.zeros_like(self.elevation)
        
        for i in range(1, len(self.elevation)):
            dh = self.elevation[i] - self.elevation[i-1]
            avg_area = (self.area[i] + self.area[i-1]) / 2
            dv = avg_area * dh
            volume[i] = volume[i-1] + dv
        
        return volume
    
    def get_area(self, level: float) -> float:
        """根据水位插值得到面积"""
        return float(np.interp(level, self.elevation, self.area))
    
    def get_volume(self, level: float) -> float:
        """根据水位插值得到容积"""
        if level <= self.elevation[0]:
            return self.volume[0]
        elif level >= self.elevation[-1]:
            # 超过最高水位，外推
            extra_volume = (level - self.elevation[-1]) * self.area[-1]
            return self.volume[-1] + extra_volume
        else:
            return float(np.interp(level, self.elevation, self.volume))
    
    def get_level(self, volume: float) -> float:
        """根据容积反算水位"""
        if volume <= self.volume[0]:
            return self.elevation[0]
        elif volume >= self.volume[-1]:
            # 超过最大容积，外推
            extra_height = (volume - self.volume[-1]) / self.area[-1]
            return self.elevation[-1] + extra_height
        else:
            return float(np.interp(volume, self.volume, self.elevation))
    
    def update(
        self,
        Q_in: float,
        Q_out: float,
        dt: float
    ) -> Tuple[float, float]:
        """
        水量平衡更新
        
        Args:
            Q_in: 入流 (m³/s)
            Q_out: 出流 (m³/s)
            dt: 时间步长 (s)
            
        Returns:
            (新水位, 新容积)
        """
        # 水量平衡
        dV = (Q_in - Q_out) * dt
        
        # 新容积
        new_volume = self.current_volume + dV
        new_volume = max(new_volume, self.volume[0])
        
        # 新水位
        new_level = self.get_level(new_volume)
        
        # 更新状态
        self.current_volume = new_volume
        self.current_level = new_level
        
        # 记录
        self.level_history.append(new_level)
        self.volume_history.append(new_volume)
        self.inflow_history.append(Q_in)
        self.outflow_history.append(Q_out)
        
        return new_level, new_volume
    
    def get_characteristic_volumes(self) -> Dict:
        """获取特征库容"""
        return {
            'dead_storage': self.get_volume(self.dead_level),
            'normal_storage': self.get_volume(self.normal_level),
            'flood_control_storage': self.get_volume(self.flood_limit_level),
            'total_storage': self.get_volume(self.check_flood_level),
            'active_storage': (self.get_volume(self.normal_level) - 
                             self.get_volume(self.dead_level))
        }
    
    def check_level_status(self) -> str:
        """检查水位状态"""
        if self.current_level < self.dead_level:
            return "低于死水位 ⚠️"
        elif self.current_level < self.flood_limit_level:
            return "正常运行 ✅"
        elif self.current_level < self.design_flood_level:
            return "超防洪限制水位 ⚠️"
        elif self.current_level < self.check_flood_level:
            return "设计洪水位 ❗"
        else:
            return "超校核洪水位 🚨"
    
    def get_status(self) -> Dict:
        """获取状态"""
        return {
            'name': self.name,
            'current_level': self.current_level,
            'current_volume': self.current_volume,
            'current_area': self.get_area(self.current_level),
            'level_status': self.check_level_status(),
            'dead_level': self.dead_level,
            'normal_level': self.normal_level,
            'flood_limit_level': self.flood_limit_level
        }


# 使用示例
if __name__ == "__main__":
    print("="*60)
    print("水库/湖泊模块测试")
    print("="*60)
    
    # 创建水库
    elevation = [100, 110, 120, 130, 140, 150, 160, 170, 180]
    area = [0.5e6, 1.0e6, 1.8e6, 2.8e6, 4.0e6, 5.5e6, 7.2e6, 9.0e6, 11.0e6]  # m²
    
    reservoir = Reservoir(
        name="Three-Gorges-Reservoir",
        dead_level=145.0,
        normal_level=175.0,
        flood_limit_level=145.0,
        design_flood_level=175.0,
        check_flood_level=180.0,
        elevation=elevation,
        area=area,
        initial_level=160.0
    )
    
    print(f"\n水库: {reservoir.name}")
    print(f"特征水位:")
    print(f"  死水位: {reservoir.dead_level}m")
    print(f"  正常蓄水位: {reservoir.normal_level}m")
    print(f"  防洪限制水位: {reservoir.flood_limit_level}m")
    print(f"  设计洪水位: {reservoir.design_flood_level}m")
    print(f"  校核洪水位: {reservoir.check_flood_level}m")
    
    # 特征库容
    print(f"\n特征库容:")
    char_volumes = reservoir.get_characteristic_volumes()
    for key, value in char_volumes.items():
        print(f"  {key}: {value/1e9:.2f} billion m³")
    
    # 初始状态
    print(f"\n初始状态:")
    print(f"  水位: {reservoir.current_level:.2f}m")
    print(f"  库容: {reservoir.current_volume/1e9:.2f} billion m³")
    print(f"  水面面积: {reservoir.get_area(reservoir.current_level)/1e6:.2f} km²")
    print(f"  状态: {reservoir.check_level_status()}")
    
    # 模拟洪水过程
    print(f"\n模拟洪水过程:")
    print("-"*60)
    print(f"{'时间(h)':<10} {'入流(m³/s)':<15} {'出流(m³/s)':<15} {'水位(m)':<15} {'状态':<20}")
    print("-"*60)
    
    dt = 3600.0  # 1小时
    
    # 洪水过程线（简化）
    flood_hydrograph = [
        (0, 5000, 3000),
        (6, 10000, 5000),
        (12, 20000, 8000),
        (18, 15000, 10000),
        (24, 10000, 8000),
        (30, 8000, 7000),
        (36, 6000, 6000)
    ]
    
    for t, Q_in, Q_out in flood_hydrograph:
        new_level, new_volume = reservoir.update(Q_in, Q_out, dt)
        status = reservoir.check_level_status()
        
        print(f"{t:<10} {Q_in:<15} {Q_out:<15} {new_level:<15.2f} {status:<20}")
    
    print(f"\n最终状态: {reservoir.get_status()}")
    
    print("\n" + "="*60)
    print("测试完成")
    print("="*60)
