#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
水工建筑物（闸门、堰等）基类

提供通用的过流计算接口，支持不同类型的水工建筑物

作者: Claude
日期: 2025-10-22
"""

import numpy as np
from abc import ABC, abstractmethod


class HydraulicStructure(ABC):
    """水工建筑物抽象基类"""

    def __init__(self, position: float, width: float, g: float = 9.81):
        """
        Args:
            position: 建筑物位置 (m)
            width: 建筑物宽度 (m)
            g: 重力加速度 (m/s²)
        """
        self.position = position
        self.width = width
        self.g = g

    @abstractmethod
    def calculate_discharge(self, h_upstream: float, h_downstream: float) -> tuple:
        """
        计算过流量

        Args:
            h_upstream: 上游水深 (m)
            h_downstream: 下游水深 (m)

        Returns:
            (discharge, flow_type): 流量 (m³/s) 和流态类型
        """
        pass

    @abstractmethod
    def __repr__(self) -> str:
        """对象的字符串表示"""
        pass


class SluiceGate(HydraulicStructure):
    """平板闸门类

    使用堰流公式计算过流量：
    - 淹没出流: Q = Cd * B * e * √(2g * Δh)
    - 自由出流: Q = Cd * B * e * √(2g * h_upstream)

    其中：
        Cd: 流量系数
        B: 闸门宽度
        e: 闸门开度
        Δh: 上下游水位差
    """

    def __init__(self, position: float, width: float, opening: float,
                 Cd: float = 0.6, g: float = 9.81,
                 submerged_threshold: float = 0.1):
        """
        Args:
            position: 闸门位置 (m)
            width: 闸门宽度 (m)
            opening: 闸门开度 (m)
            Cd: 流量系数 (默认0.6)
            g: 重力加速度 (m/s²)
            submerged_threshold: 淹没流判定阈值 (m) - 当水位差小于此值时视为淹没出流
        """
        super().__init__(position, width, g)
        self.opening = opening
        self.Cd = Cd
        self.submerged_threshold = submerged_threshold

    def calculate_discharge(self, h_upstream: float, h_downstream: float) -> tuple:
        """
        计算闸门过流量

        Args:
            h_upstream: 上游水深 (m)
            h_downstream: 下游水深 (m)

        Returns:
            (discharge, flow_type): 流量 (m³/s) 和流态类型 ('free' 或 'submerged')
        """
        e = self.opening

        # 流态判断
        delta_h = h_upstream - h_downstream
        if h_downstream > e or delta_h < self.submerged_threshold:
            # 淹没出流
            delta_h_effective = max(1e-4, delta_h)  # 避免负值或零
            discharge = self.Cd * self.width * e * np.sqrt(2 * self.g * delta_h_effective)
            flow_type = 'submerged'
        else:
            # 自由出流
            discharge = self.Cd * self.width * e * np.sqrt(2 * self.g * h_upstream)
            flow_type = 'free'

        return discharge, flow_type

    def __repr__(self) -> str:
        return (f"SluiceGate(position={self.position}m, width={self.width}m, "
                f"opening={self.opening}m, Cd={self.Cd})")


class BroadCrestedWeir(HydraulicStructure):
    """宽顶堰类

    使用堰流公式：
    Q = Cd * B * h^(3/2) * √(2g)
    """

    def __init__(self, position: float, width: float, crest_height: float,
                 Cd: float = 0.848, g: float = 9.81):
        """
        Args:
            position: 堰的位置 (m)
            width: 堰宽 (m)
            crest_height: 堰顶高程 (m)
            Cd: 流量系数 (默认0.848 for broad-crested weir)
            g: 重力加速度 (m/s²)
        """
        super().__init__(position, width, g)
        self.crest_height = crest_height
        self.Cd = Cd

    def calculate_discharge(self, h_upstream: float, h_downstream: float = None) -> tuple:
        """
        计算堰流量

        Args:
            h_upstream: 上游水深 (m)
            h_downstream: 下游水深 (m，对于自由溢流可忽略)

        Returns:
            (discharge, flow_type): 流量 (m³/s) 和流态类型
        """
        # 堰顶以上水头
        H = max(0.0, h_upstream - self.crest_height)

        if H < 1e-4:
            # 水位低于堰顶，无流量
            return 0.0, 'no_flow'

        # 宽顶堰公式
        discharge = self.Cd * self.width * (H ** 1.5) * np.sqrt(2 * self.g)

        return discharge, 'free'

    def __repr__(self) -> str:
        return (f"BroadCrestedWeir(position={self.position}m, width={self.width}m, "
                f"crest_height={self.crest_height}m, Cd={self.Cd})")


class Orifice(HydraulicStructure):
    """孔口类

    使用孔口流公式：
    Q = Cd * A * √(2g * h)
    """

    def __init__(self, position: float, width: float, height: float,
                 bottom_elevation: float = 0.0, Cd: float = 0.61, g: float = 9.81):
        """
        Args:
            position: 孔口位置 (m)
            width: 孔口宽度 (m)
            height: 孔口高度 (m)
            bottom_elevation: 孔口底部高程 (m)
            Cd: 流量系数 (默认0.61)
            g: 重力加速度 (m/s²)
        """
        super().__init__(position, width, g)
        self.height = height
        self.bottom_elevation = bottom_elevation
        self.Cd = Cd
        self.area = width * height

    def calculate_discharge(self, h_upstream: float, h_downstream: float) -> tuple:
        """
        计算孔口流量

        Args:
            h_upstream: 上游水深 (m)
            h_downstream: 下游水深 (m)

        Returns:
            (discharge, flow_type): 流量 (m³/s) 和流态类型
        """
        # 孔口中心高程
        center_elevation = self.bottom_elevation + self.height / 2

        # 孔口中心处的上游水头
        h_center_upstream = max(0.0, h_upstream - center_elevation)

        if h_center_upstream < 1e-4:
            return 0.0, 'no_flow'

        # 判断是否淹没
        if h_downstream > (center_elevation + self.height / 2):
            # 淹没出流
            h_center_downstream = h_downstream - center_elevation
            delta_h = max(1e-4, h_center_upstream - h_center_downstream)
            discharge = self.Cd * self.area * np.sqrt(2 * self.g * delta_h)
            flow_type = 'submerged'
        else:
            # 自由出流
            discharge = self.Cd * self.area * np.sqrt(2 * self.g * h_center_upstream)
            flow_type = 'free'

        return discharge, flow_type

    def __repr__(self) -> str:
        return (f"Orifice(position={self.position}m, width={self.width}m, "
                f"height={self.height}m, Cd={self.Cd})")
