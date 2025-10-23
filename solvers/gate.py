#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
水工建筑物（闸门、堰等）基类

提供通用的过流计算接口，支持不同类型的水工建筑物
支持时变参数（如可变闸门开度）

作者: Claude
日期: 2025-10-22
"""

import numpy as np
from abc import ABC, abstractmethod
from typing import Union, Callable, Optional


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
        self.current_time = 0.0  # 当前时间（用于时变参数）

    def update_time(self, t: float):
        """
        更新当前时间（用于时变参数）

        Args:
            t: 当前时间 (s)
        """
        self.current_time = t

    @abstractmethod
    def calculate_discharge(self, h_upstream: float, h_downstream: float,
                          t: Optional[float] = None) -> tuple:
        """
        计算过流量

        Args:
            h_upstream: 上游水深 (m)
            h_downstream: 下游水深 (m)
            t: 当前时间 (s)，用于时变参数

        Returns:
            (discharge, flow_type): 流量 (m³/s) 和流态类型
        """
        pass

    @abstractmethod
    def calculate_discharge_derivatives(self, h_upstream: float, h_downstream: float,
                                        t: Optional[float] = None) -> tuple:
        """
        计算过流量对水深的导数（解析）

        Args:
            h_upstream: 上游水深 (m)
            h_downstream: 下游水深 (m)
            t: 当前时间 (s)，用于时变参数

        Returns:
            (dQ_dh_up, dQ_dh_down): 流量对上下游水深的导数
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
        e: 闸门开度（可时变）
        Δh: 上下游水位差

    支持时变开度：opening可以是常数或时间函数
    """

    def __init__(self, position: float, width: float,
                 opening: Union[float, Callable[[float], float]],
                 Cd: float = 0.6, g: float = 9.81,
                 submerged_threshold: float = 0.1):
        """
        Args:
            position: 闸门位置 (m)
            width: 闸门宽度 (m)
            opening: 闸门开度 (m) 或 开度函数 opening(t) -> float
            Cd: 流量系数 (默认0.6)
            g: 重力加速度 (m/s²)
            submerged_threshold: 淹没流判定阈值 (m)
        """
        super().__init__(position, width, g)
        self.opening_func = opening if callable(opening) else lambda t: opening
        self.Cd = Cd
        self.submerged_threshold = submerged_threshold

    def get_opening(self, t: Optional[float] = None) -> float:
        """
        获取当前开度

        Args:
            t: 时间 (s)，如果为None则使用self.current_time

        Returns:
            当前开度 (m)
        """
        if t is None:
            t = self.current_time
        return self.opening_func(t)

    def calculate_discharge(self, h_upstream: float, h_downstream: float,
                          t: Optional[float] = None) -> tuple:
        """
        计算闸门过流量

        Args:
            h_upstream: 上游水深 (m)
            h_downstream: 下游水深 (m)
            t: 当前时间 (s)

        Returns:
            (discharge, flow_type): 流量 (m³/s) 和流态类型 ('free' 或 'submerged')
        """
        # 获取当前开度（支持时变）
        e = self.get_opening(t)

        # 流态判断
        delta_h = h_upstream - h_downstream
        if h_downstream > e or delta_h < self.submerged_threshold:
            # 淹没出流
            # ✅ 精度修复：降低截断阈值（PRECISION FIX #1 - MINIMAL）
            # 使用更小的截断阈值以提高精度，但保持数值稳定性
            delta_h_min = 1e-6  # 降低阈值从1e-4到1e-6（提高100倍精度）
            delta_h_effective = max(delta_h_min, delta_h)
            discharge = self.Cd * self.width * e * np.sqrt(2 * self.g * delta_h_effective)
            flow_type = 'submerged'
        else:
            # 自由出流
            discharge = self.Cd * self.width * e * np.sqrt(2 * self.g * h_upstream)
            flow_type = 'free'

        return discharge, flow_type

    def calculate_discharge_derivatives(self, h_upstream: float, h_downstream: float,
                                        t: Optional[float] = None) -> tuple:
        """
        计算闸门流量对水深的导数（解析）

        Args:
            h_upstream: 上游水深 (m)
            h_downstream: 下游水深 (m)
            t: 当前时间 (s)

        Returns:
            (dQ_dh_up, dQ_dh_down): 流量对上下游水深的导数
        """
        # 获取当前开度
        e = self.get_opening(t)

        # 流态判断
        delta_h = h_upstream - h_downstream
        if h_downstream > e or delta_h < self.submerged_threshold:
            # 淹没出流: Q = Cd * B * e * √(2g * Δh)
            # 其中 Δh = max(1e-4, h_up - h_down)
            delta_h_effective = max(1e-4, delta_h)

            # dQ/dh_up = Cd * B * e * (1/2) * (2g * Δh)^(-1/2) * 2g
            #          = Cd * B * e * g / √(2g * Δh)
            # dQ/dh_down = -dQ/dh_up

            if delta_h > 1e-4:
                # 正常情况：导数正常计算
                dQ_dh_up = self.Cd * self.width * e * self.g / np.sqrt(2 * self.g * delta_h_effective)
                dQ_dh_down = -dQ_dh_up
            else:
                # 特殊情况：delta_h很小，导数在截断点
                # 在截断点 delta_h = 1e-4 处的导数
                dQ_dh_up = self.Cd * self.width * e * self.g / np.sqrt(2 * self.g * 1e-4)
                dQ_dh_down = -dQ_dh_up
        else:
            # 自由出流: Q = Cd * B * e * √(2g * h_up)
            # dQ/dh_up = Cd * B * e * g / √(2g * h_up)
            # dQ/dh_down = 0 (自由出流不依赖下游水深)
            dQ_dh_up = self.Cd * self.width * e * self.g / np.sqrt(2 * self.g * h_upstream)
            dQ_dh_down = 0.0

        return dQ_dh_up, dQ_dh_down

    def __repr__(self) -> str:
        try:
            current_opening = self.get_opening()
            return (f"SluiceGate(position={self.position}m, width={self.width}m, "
                    f"opening={current_opening:.2f}m@t={self.current_time:.0f}s, Cd={self.Cd})")
        except:
            return (f"SluiceGate(position={self.position}m, width={self.width}m, "
                    f"opening=f(t), Cd={self.Cd})")


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

    def calculate_discharge(self, h_upstream: float, h_downstream: float = None,
                          t: Optional[float] = None) -> tuple:
        """
        计算堰流量

        Args:
            h_upstream: 上游水深 (m)
            h_downstream: 下游水深 (m，对于自由溢流可忽略)
            t: 当前时间 (s)

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

    def calculate_discharge_derivatives(self, h_upstream: float, h_downstream: float = None,
                                        t: Optional[float] = None) -> tuple:
        """
        计算堰流量对水深的导数（解析）

        Args:
            h_upstream: 上游水深 (m)
            h_downstream: 下游水深 (m，对于自由溢流可忽略)
            t: 当前时间 (s)

        Returns:
            (dQ_dh_up, dQ_dh_down): 流量对上下游水深的导数
        """
        # 堰顶以上水头
        H = max(0.0, h_upstream - self.crest_height)

        if H < 1e-4:
            # 水位低于堰顶，导数为零
            return 0.0, 0.0

        # 宽顶堰公式: Q = Cd * B * H^(3/2) * √(2g)
        # dQ/dh_up = Cd * B * (3/2) * H^(1/2) * √(2g)
        dQ_dh_up = self.Cd * self.width * 1.5 * np.sqrt(H * 2 * self.g)

        # 自由溢流不依赖下游水深
        dQ_dh_down = 0.0

        return dQ_dh_up, dQ_dh_down

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

    def calculate_discharge(self, h_upstream: float, h_downstream: float,
                          t: Optional[float] = None) -> tuple:
        """
        计算孔口流量

        Args:
            h_upstream: 上游水深 (m)
            h_downstream: 下游水深 (m)
            t: 当前时间 (s)

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

    def calculate_discharge_derivatives(self, h_upstream: float, h_downstream: float,
                                        t: Optional[float] = None) -> tuple:
        """
        计算孔口流量对水深的导数（解析）

        Args:
            h_upstream: 上游水深 (m)
            h_downstream: 下游水深 (m)
            t: 当前时间 (s)

        Returns:
            (dQ_dh_up, dQ_dh_down): 流量对上下游水深的导数
        """
        # 孔口中心高程
        center_elevation = self.bottom_elevation + self.height / 2

        # 孔口中心处的上游水头
        h_center_upstream = max(0.0, h_upstream - center_elevation)

        if h_center_upstream < 1e-4:
            return 0.0, 0.0

        # 判断是否淹没
        if h_downstream > (center_elevation + self.height / 2):
            # 淹没出流: Q = Cd * A * √(2g * Δh)
            h_center_downstream = h_downstream - center_elevation
            delta_h = max(1e-4, h_center_upstream - h_center_downstream)

            # dQ/dh_up = Cd * A * g / √(2g * Δh)
            # dQ/dh_down = -dQ/dh_up
            dQ_dh_up = self.Cd * self.area * self.g / np.sqrt(2 * self.g * delta_h)
            dQ_dh_down = -dQ_dh_up
        else:
            # 自由出流: Q = Cd * A * √(2g * h_center_up)
            # dQ/dh_up = Cd * A * g / √(2g * h_center_up)
            # dQ/dh_down = 0
            dQ_dh_up = self.Cd * self.area * self.g / np.sqrt(2 * self.g * h_center_upstream)
            dQ_dh_down = 0.0

        return dQ_dh_up, dQ_dh_down

    def __repr__(self) -> str:
        return (f"Orifice(position={self.position}m, width={self.width}m, "
                f"height={self.height}m, Cd={self.Cd})")


class Spillway(HydraulicStructure):
    """溢洪道类 - 大坝泄洪设施

    支持多种溢洪道类型：
    - WES标准溢洪道（WES Standard Spillway）
    - 实用堰（Ogee Spillway）
    - 宽顶堰式溢洪道

    流量公式：
    - 自由溢流：Q = Cd * B * H^(3/2)
    - 淹没溢流：Q = Cd * B * H^(3/2) * submergence_factor

    其中：
        Cd: 流量系数（WES标准约2.1）
        B: 溢洪道宽度
        H: 堰顶以上水头
    """

    def __init__(self, position: float, width: float, crest_elevation: float,
                 spillway_type: str = 'wes', Cd: float = 2.1, g: float = 9.81,
                 submergence_threshold: float = 0.67):
        """
        Args:
            position: 溢洪道位置 (m)
            width: 溢洪道宽度 (m)
            crest_elevation: 堰顶高程 (m)
            spillway_type: 溢洪道类型 ('wes', 'ogee', 'broad_crested')
            Cd: 流量系数（WES标准约2.1，宽顶堰约0.848）
            g: 重力加速度 (m/s²)
            submergence_threshold: 淹没判定阈值（下游水位/上游水头比）
        """
        super().__init__(position, width, g)
        self.crest_elevation = crest_elevation
        self.spillway_type = spillway_type
        self.Cd = Cd
        self.submergence_threshold = submergence_threshold

    def calculate_discharge(self, h_upstream: float, h_downstream: float = None,
                          t: Optional[float] = None) -> tuple:
        """
        计算溢洪道流量

        Args:
            h_upstream: 上游水深 (m)
            h_downstream: 下游水深 (m，用于淹没修正)
            t: 当前时间 (s)

        Returns:
            (discharge, flow_type): 流量 (m³/s) 和流态类型
        """
        # 堰顶以上水头
        H = max(0.0, h_upstream - self.crest_elevation)

        if H < 1e-4:
            # 水位低于堰顶，无流量
            return 0.0, 'no_flow'

        # 基本流量公式
        if self.spillway_type in ['wes', 'ogee']:
            # WES标准溢洪道 / 实用堰：Q = Cd * B * H^(3/2)
            Q_free = self.Cd * self.width * (H ** 1.5)

        elif self.spillway_type == 'broad_crested':
            # 宽顶堰式：Q = Cd * B * H^(3/2) * sqrt(2g)
            Q_free = self.Cd * self.width * (H ** 1.5) * np.sqrt(2 * self.g)

        else:
            raise ValueError(f"Unknown spillway type: {self.spillway_type}")

        # 淹没修正
        if h_downstream is not None and h_downstream > self.crest_elevation:
            # 下游水位高于堰顶，可能淹没
            h_tail = h_downstream - self.crest_elevation
            submergence_ratio = h_tail / H

            if submergence_ratio > self.submergence_threshold:
                # 淹没出流，流量折减
                # 使用Villemonte公式：Q_submerged = Q_free * (1 - (h_tail/H)^1.5)^0.385
                submergence_factor = (1.0 - submergence_ratio ** 1.5) ** 0.385
                submergence_factor = max(0.1, submergence_factor)
                Q = Q_free * submergence_factor
                return Q, 'submerged'

        return Q_free, 'free'

    def calculate_discharge_derivatives(self, h_upstream: float,
                                        h_downstream: float = None,
                                        t: Optional[float] = None) -> tuple:
        """
        计算流量对水深的导数（解析）

        Args:
            h_upstream: 上游水深 (m)
            h_downstream: 下游水深 (m)
            t: 当前时间 (s)

        Returns:
            (dQ/dh_up, dQ/dh_down): 导数
        """
        H = max(1e-4, h_upstream - self.crest_elevation)

        if H < 1e-4:
            return 0.0, 0.0

        # 自由溢流导数
        if self.spillway_type in ['wes', 'ogee']:
            # Q = Cd * B * H^(3/2)
            # dQ/dH = (3/2) * Cd * B * H^(1/2)
            dQ_dH = 1.5 * self.Cd * self.width * np.sqrt(H)

        elif self.spillway_type == 'broad_crested':
            # Q = Cd * B * H^(3/2) * sqrt(2g)
            # dQ/dH = (3/2) * Cd * B * H^(1/2) * sqrt(2g)
            dQ_dH = 1.5 * self.Cd * self.width * np.sqrt(H * 2 * self.g)
        else:
            dQ_dH = 0.0

        # dQ/dh_up = dQ/dH * dH/dh_up = dQ/dH * 1
        dQ_dh_up = dQ_dH

        # 自由溢流时，不依赖下游水深
        # （淹没时的导数较复杂，这里简化处理）
        dQ_dh_down = 0.0

        return dQ_dh_up, dQ_dh_down

    def __repr__(self) -> str:
        return (f"Spillway(type={self.spillway_type}, position={self.position}m, "
                f"width={self.width}m, crest={self.crest_elevation}m, Cd={self.Cd})")


class Transition(HydraulicStructure):
    """渐变段类 - 断面过渡

    用于明渠断面尺寸变化，如宽度、深度的渐变。

    能量方程：
    h₁ + V₁²/(2g) = h₂ + V₂²/(2g) + h_loss

    其中 h_loss = K * (V₁ - V₂)²/(2g)
    K为局部损失系数（扩散：0.2-0.3，收缩：0.1-0.2）
    """

    def __init__(self, position: float, width_upstream: float,
                 width_downstream: float, K_loss: float = 0.2, g: float = 9.81):
        """
        Args:
            position: 渐变段位置 (m)
            width_upstream: 上游宽度 (m)
            width_downstream: 下游宽度 (m)
            K_loss: 局部损失系数（扩散0.2-0.3，收缩0.1-0.2）
            g: 重力加速度 (m/s²)
        """
        super().__init__(position, width_upstream, g)
        self.width_upstream = width_upstream
        self.width_downstream = width_downstream
        self.K_loss = K_loss

        # 判断类型
        if width_downstream > width_upstream:
            self.transition_type = 'expansion'  # 扩散
        elif width_downstream < width_upstream:
            self.transition_type = 'contraction'  # 收缩
        else:
            self.transition_type = 'uniform'  # 等宽

    def calculate_discharge(self, h_upstream: float, h_downstream: float,
                          t: Optional[float] = None) -> tuple:
        """
        计算通过渐变段的流量

        使用能量方程和连续性方程：
        Q = A₁*V₁ = A₂*V₂
        E₁ = E₂ + h_loss

        Args:
            h_upstream: 上游水深 (m)
            h_downstream: 下游水深 (m)
            t: 当前时间 (s)

        Returns:
            (discharge, flow_type): 流量 (m³/s) 和流态类型
        """
        # 断面面积
        A1 = h_upstream * self.width_upstream
        A2 = h_downstream * self.width_downstream

        if A1 < 1e-6 or A2 < 1e-6:
            return 0.0, 'no_flow'

        # 简化计算：假设流速水头较小，忽略损失
        # 使用连续性方程：Q = A*V
        # 从上下游水深差估算流量

        # 比能（忽略流速水头的粗略估计）
        E1 = h_upstream
        E2 = h_downstream + self.K_loss * 0.1  # 粗略估计损失

        # 流速估算（简化）
        if E1 > E2:
            V1 = np.sqrt(2 * self.g * (E1 - E2))
            Q = A1 * V1
        else:
            Q = 0.0

        return Q, self.transition_type

    def calculate_discharge_derivatives(self, h_upstream: float, h_downstream: float,
                                        t: Optional[float] = None) -> tuple:
        """
        计算流量对水深的导数（简化处理）

        Args:
            h_upstream: 上游水深 (m)
            h_downstream: 下游水深 (m)
            t: 当前时间 (s)

        Returns:
            (dQ/dh_up, dQ/dh_down): 导数
        """
        # 简化处理：数值微分
        eps = 1e-4
        Q0 = self.calculate_discharge(h_upstream, h_downstream)[0]
        Q_up = self.calculate_discharge(h_upstream + eps, h_downstream)[0]
        Q_down = self.calculate_discharge(h_upstream, h_downstream + eps)[0]

        dQ_dh_up = (Q_up - Q0) / eps if Q0 > 1e-6 else 0.0
        dQ_dh_down = (Q_down - Q0) / eps if Q0 > 1e-6 else 0.0

        return dQ_dh_up, dQ_dh_down

    def __repr__(self) -> str:
        return (f"Transition(type={self.transition_type}, position={self.position}m, "
                f"width={self.width_upstream}m→{self.width_downstream}m, K={self.K_loss})")


class Drop(HydraulicStructure):
    """跌水类 - 高程跌落

    用于渠道高程突然变化，类似小型瀑布。
    能量损失显著。

    流量公式：
    Q = Cd * B * h * sqrt(2g * (h + Δz))

    其中：
        Cd: 流量系数（约0.6）
        B: 跌水宽度
        h: 上游水深
        Δz: 跌水高度（高程差）
    """

    def __init__(self, position: float, width: float, drop_height: float,
                 Cd: float = 0.6, g: float = 9.81):
        """
        Args:
            position: 跌水位置 (m)
            width: 跌水宽度 (m)
            drop_height: 跌水高度/高程差 (m)
            Cd: 流量系数（约0.6）
            g: 重力加速度 (m/s²)
        """
        super().__init__(position, width, g)
        self.drop_height = drop_height
        self.Cd = Cd

    def calculate_discharge(self, h_upstream: float, h_downstream: float = None,
                          t: Optional[float] = None) -> tuple:
        """
        计算跌水流量

        Q = Cd * B * h * sqrt(2g * (h + Δz))

        Args:
            h_upstream: 上游水深 (m)
            h_downstream: 下游水深 (m，跌水不受下游影响）
            t: 当前时间 (s)

        Returns:
            (discharge, flow_type): 流量 (m³/s) 和流态类型
        """
        if h_upstream < 1e-4:
            return 0.0, 'no_flow'

        # 跌水流量公式
        # Q = Cd * B * h * sqrt(2g * (h + Δz))
        total_head = h_upstream + self.drop_height
        Q = self.Cd * self.width * h_upstream * np.sqrt(2 * self.g * total_head)

        return Q, 'drop'

    def calculate_discharge_derivatives(self, h_upstream: float, h_downstream: float = None,
                                        t: Optional[float] = None) -> tuple:
        """
        计算流量对水深的导数（解析）

        Q = Cd * B * h * sqrt(2g * (h + Δz))
        dQ/dh = Cd * B * [sqrt(2g(h+Δz)) + h * g/sqrt(2g(h+Δz))]

        Args:
            h_upstream: 上游水深 (m)
            h_downstream: 下游水深 (m)
            t: 当前时间 (s)

        Returns:
            (dQ/dh_up, dQ/dh_down): 导数
        """
        if h_upstream < 1e-4:
            return 0.0, 0.0

        h = h_upstream
        delta_z = self.drop_height
        total_head = h + delta_z

        # Q = Cd * B * h * sqrt(2g * total_head)
        # dQ/dh = Cd * B * [sqrt(2g*total_head) + h * g/sqrt(2g*total_head)]
        sqrt_term = np.sqrt(2 * self.g * total_head)
        dQ_dh_up = self.Cd * self.width * (sqrt_term + h * self.g / sqrt_term)

        # 跌水不受下游影响
        dQ_dh_down = 0.0

        return dQ_dh_up, dQ_dh_down

    def __repr__(self) -> str:
        return (f"Drop(position={self.position}m, width={self.width}m, "
                f"height={self.drop_height}m, Cd={self.Cd})")
