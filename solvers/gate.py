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


class PumpStation(HydraulicStructure):
    """泵站类（简化模型）

    在固定转速下，泵站提供额定流量和扬程。
    简化模型假设：
    1. 泵站在额定转速下运行
    2. 流量由泵特性曲线和上游水位决定
    3. 泵站增加水头（下游可以高于上游）

    模型：
    - 当上游水位足够：Q = Q_rated
    - 当上游水位不足：Q = Q_rated * (h_upstream / h_min)^0.5
    - 扬程：H_pump = H_rated（固定）
    """

    def __init__(self, position: float, width: float,
                 rated_flow: float = 30.0,
                 rated_head: float = 5.0,
                 min_suction_head: float = 2.0,
                 g: float = 9.81):
        """
        Args:
            position: 泵站位置 (m)
            width: 泵站宽度 (m)
            rated_flow: 额定流量 (m³/s)
            rated_head: 额定扬程 (m)
            min_suction_head: 最小吸入水头 (m)，低于此值流量减少
            g: 重力加速度 (m/s²)
        """
        super().__init__(position, width, g)
        self.rated_flow = rated_flow
        self.rated_head = rated_head
        self.min_suction_head = min_suction_head

        # 泵站运行状态（固定转速）
        self.is_running = True

    def calculate_discharge(self, h_upstream: float, h_downstream: float,
                          t: Optional[float] = None) -> tuple:
        """
        计算泵站过流量

        简化模型：
        1. 如果上游水位 >= min_suction_head：Q = Q_rated
        2. 如果上游水位 < min_suction_head：Q = Q_rated * sqrt(h_upstream / min_suction_head)
        3. 泵站不依赖下游水位（主动提水）

        Args:
            h_upstream: 上游水深 (m)
            h_downstream: 下游水深 (m)（泵站不依赖此值）
            t: 当前时间 (s)

        Returns:
            (discharge, flow_type): 流量 (m³/s) 和流态类型
        """
        if not self.is_running:
            return 0.0, 'pump_off'

        # 检查最小吸入水头
        if h_upstream < 0.1:  # 极低水位，泵站停止
            return 0.0, 'insufficient_water'

        if h_upstream >= self.min_suction_head:
            # 正常运行：额定流量
            discharge = self.rated_flow
            flow_type = 'rated'
        else:
            # 低水位：流量按平方根减少
            # Q = Q_rated * sqrt(h_up / h_min)
            ratio = np.sqrt(h_upstream / self.min_suction_head)
            discharge = self.rated_flow * ratio
            flow_type = 'reduced'

        return discharge, flow_type

    def calculate_discharge_derivatives(self, h_upstream: float, h_downstream: float,
                                        t: Optional[float] = None) -> tuple:
        """
        计算泵站流量对水深的导数（解析）

        泵站特点：
        1. 在正常运行时（h >= h_min），流量不依赖水位：dQ/dh = 0
        2. 在低水位时（h < h_min），流量与水位相关：dQ/dh_up > 0
        3. 流量不依赖下游水位：dQ/dh_down = 0

        Args:
            h_upstream: 上游水深 (m)
            h_downstream: 下游水深 (m)
            t: 当前时间 (s)

        Returns:
            (dQ_dh_up, dQ_dh_down): 流量对上下游水深的导数
        """
        if not self.is_running or h_upstream < 0.1:
            return 0.0, 0.0

        if h_upstream >= self.min_suction_head:
            # 正常运行：流量恒定，导数为零
            dQ_dh_up = 0.0
        else:
            # 低水位：Q = Q_rated * sqrt(h_up / h_min)
            # dQ/dh_up = Q_rated / (2 * sqrt(h_up * h_min))
            dQ_dh_up = self.rated_flow / (2.0 * np.sqrt(h_upstream * self.min_suction_head))

        # 泵站不依赖下游水位（主动提水）
        dQ_dh_down = 0.0

        return dQ_dh_up, dQ_dh_down

    def set_running_state(self, is_running: bool):
        """
        设置泵站运行状态

        Args:
            is_running: True=运行，False=停止
        """
        self.is_running = is_running

    def get_momentum_source(self, h: float, dx: float, spread_points: int = 5) -> float:
        """
        计算泵站扬程引起的动量源项

        物理意义：泵站提供能量（扬程），在明渠中表现为水位抬升。
        在动量方程中，这相当于一个压力梯度源项。

        动量方程：∂(hu)/∂t + ∂(hu²/h + 0.5gh²)/∂x = -ghS_f + S_pump

        泵站源项：S_pump = g * h * (ΔH/Δx)
        其中：
        - ΔH = rated_head（泵站额定扬程）
        - Δx = spread_points * dx（泵站作用范围，通常2-5个网格）

        Args:
            h: 当前位置水深 (m)
            dx: 网格间距 (m)
            spread_points: 泵站作用范围（网格点数）

        Returns:
            S_pump: 动量源项 (m/s²)
        """
        if not self.is_running:
            return 0.0

        # 泵站作用范围
        pump_length = spread_points * dx

        # 动量源项：S = g * h * (ΔH / L_pump)
        # 这个源项使下游动量增加，表现为水位抬升
        S_pump = self.g * h * self.rated_head / pump_length

        return S_pump

    def __repr__(self) -> str:
        state = "ON" if self.is_running else "OFF"
        return (f"PumpStation(position={self.position}m, Q_rated={self.rated_flow}m³/s, "
                f"H_rated={self.rated_head}m, state={state})")


class PumpStationSimplified(HydraulicStructure):
    """泵站简化耦合模型（短期方案）
    
    特点：
    1. 流量跟随上游流入流量（质量守恒）
    2. 限制最大流量（泵站能力）
    3. 根据流量调整扬程（简化泵特性）
    
    物理意义：
    - 泵站传递流量，不阻断流动
    - 超过泵站能力时，多余流量导致泵前蓄水
    - 扬程随流量变化（超载时降低）
    
    适用场景：
    - 明渠串联泵站系统
    - 快速修复质量守恒问题
    """
    
    def __init__(self, position: float, width: float,
                 rated_flow: float = 30.0,
                 rated_head: float = 5.0,
                 max_overload_ratio: float = 1.3,
                 min_suction_head: float = 2.0,
                 g: float = 9.81):
        """
        Args:
            position: 泵站位置 (m)
            width: 泵站宽度 (m)
            rated_flow: 额定流量 (m³/s)
            rated_head: 额定扬程 (m)
            max_overload_ratio: 最大超载系数（允许超过额定流量的倍数）
            min_suction_head: 最小吸入水头 (m)
            g: 重力加速度 (m/s²)
        """
        super().__init__(position, width, g)
        self.rated_flow = rated_flow
        self.rated_head = rated_head
        self.max_overload_ratio = max_overload_ratio
        self.min_suction_head = min_suction_head
        
        self.max_flow = rated_flow * max_overload_ratio
        
        # 运行状态
        self.is_running = True
        self.current_head = rated_head
        self.current_flow = rated_flow
    
    def calculate_discharge(self, h_upstream: float, h_downstream: float,
                          t: Optional[float] = None, Q_upstream: Optional[float] = None) -> tuple:
        """
        计算泵站流量（简化耦合模型）
        
        核心思想：
        1. 泵站流量跟随上游流入流量（质量守恒）
        2. 但受限于泵站最大能力
        3. 超出能力的流量会导致泵前水位上升
        
        Args:
            h_upstream: 上游水深 (m)
            h_downstream: 下游水深 (m)
            t: 当前时间 (s)
            Q_upstream: 上游流入流量 (m³/s)，如果未提供则使用额定流量
        
        Returns:
            (discharge, flow_type): 流量 (m³/s) 和流态类型
        """
        if not self.is_running:
            self.current_flow = 0.0
            self.current_head = 0.0
            return 0.0, 'pump_off'
        
        # 检查最小吸入水头
        if h_upstream < 0.1:
            self.current_flow = 0.0
            self.current_head = 0.0
            return 0.0, 'insufficient_water'
        
        # 如果未提供上游流量，使用额定流量（兼容旧接口）
        if Q_upstream is None:
            Q_upstream = self.rated_flow
        
        # 泵站流量 = 上游流量，但限制在最大能力内
        if Q_upstream <= self.max_flow:
            # 泵站可以处理
            discharge = Q_upstream
            
            # 根据流量计算扬程
            if discharge <= self.rated_flow:
                # 额定或以下：扬程稳定
                self.current_head = self.rated_head
                flow_type = 'normal'
            else:
                # 超载：扬程线性降低
                # H = H_rated * (2 - Q/Q_rated)
                ratio = discharge / self.rated_flow
                self.current_head = self.rated_head * (2.0 - ratio)
                self.current_head = max(0.0, self.current_head)
                flow_type = 'overload'
        else:
            # 超过泵站最大能力
            discharge = self.max_flow
            self.current_head = self.rated_head * (2.0 - self.max_overload_ratio)
            self.current_head = max(0.0, self.current_head)
            flow_type = 'max_capacity'
        
        self.current_flow = discharge
        return discharge, flow_type
    
    def calculate_discharge_derivatives(self, h_upstream: float, h_downstream: float,
                                       t: Optional[float] = None) -> tuple:
        """
        计算流量对水深的导数
        
        简化模型中，流量主要由上游决定，对本地水深的导数较小
        """
        if not self.is_running or h_upstream < 0.1:
            return 0.0, 0.0
        
        # 简化：假设流量对水深的依赖较弱
        # 实际中应该通过迭代求解工作点
        dQ_dh_up = 0.1  # 小的正值，表示水位升高有助于流量
        dQ_dh_down = 0.0  # 泵站主动提水，不依赖下游
        
        return dQ_dh_up, dQ_dh_down
    
    def set_running_state(self, is_running: bool):
        """设置泵站运行状态"""
        self.is_running = is_running
    
    def get_current_head(self) -> float:
        """获取当前扬程"""
        return self.current_head
    
    def __repr__(self) -> str:
        state = "ON" if self.is_running else "OFF"
        return (f"PumpStationSimplified(position={self.position}m, "
                f"Q_rated={self.rated_flow}m³/s, Q_current={self.current_flow:.1f}m³/s, "
                f"H_rated={self.rated_head}m, H_current={self.current_head:.2f}m, state={state})")


class PumpStationAdvanced(HydraulicStructure):
    """泵站完整特性曲线模型（中期方案）
    
    特点：
    1. 真实的泵特性曲线 H = f(Q)
    2. 考虑管路特性曲线
    3. 迭代求解工作点
    4. 泵前水位影响流量
    
    物理模型：
    - 泵特性：H_pump = a - b·Q - c·Q²
    - 管路特性：H_required = H_static + k·Q²
    - 工作点：H_pump(Q) = H_required(Q)
    
    适用场景：
    - 精确模拟泵站工况
    - 研究变工况运行
    - 优化设计
    """
    
    def __init__(self, position: float, width: float,
                 rated_flow: float = 30.0,
                 rated_head: float = 5.0,
                 shutoff_head: Optional[float] = None,
                 friction_coef: float = 0.0001,
                 min_suction_head: float = 2.0,
                 g: float = 9.81):
        """
        Args:
            position: 泵站位置 (m)
            width: 泵站宽度 (m)
            rated_flow: 额定流量 (m³/s)
            rated_head: 额定扬程 (m)
            shutoff_head: 关阀扬程 (m)，默认为1.2倍额定扬程
            friction_coef: 管路摩阻系数
            min_suction_head: 最小吸入水头 (m)
            g: 重力加速度 (m/s²)
        """
        super().__init__(position, width, g)
        self.rated_flow = rated_flow
        self.rated_head = rated_head
        self.min_suction_head = min_suction_head
        self.friction_coef = friction_coef
        
        # 关阀扬程（Q=0时的扬程）
        if shutoff_head is None:
            self.shutoff_head = rated_head * 1.2
        else:
            self.shutoff_head = shutoff_head
        
        # 拟合泵特性曲线系数
        # H = a - b·Q - c·Q²
        # 边界条件：
        #   Q = 0: H = shutoff_head
        #   Q = Q_rated: H = H_rated
        # 假设在Q = 1.5*Q_rated时，H = 0.5*H_rated (典型泵曲线)
        
        self.a = self.shutoff_head
        
        # 求解 b 和 c
        # H_rated = a - b·Q_rated - c·Q_rated²
        # 0.5·H_rated = a - b·(1.5·Q_rated) - c·(1.5·Q_rated)²
        
        Q_r = rated_flow
        H_r = rated_head
        a = self.shutoff_head
        
        # 联立方程求解
        # H_r = a - b·Q_r - c·Q_r²  ... (1)
        # 0.5·H_r = a - b·1.5·Q_r - c·2.25·Q_r²  ... (2)
        # 
        # (1) - (2): 0.5·H_r = b·0.5·Q_r + c·1.25·Q_r²
        # → b·Q_r + 2.5·c·Q_r² = H_r
        # 
        # 从(1): b = (a - H_r - c·Q_r²) / Q_r
        # 代入: (a - H_r - c·Q_r²) + 2.5·c·Q_r² = H_r
        # → a - H_r + 1.5·c·Q_r² = H_r
        # → c = (2·H_r - a) / (1.5·Q_r²)
        
        self.c = (2 * H_r - a) / (1.5 * Q_r**2)
        self.b = (a - H_r - self.c * Q_r**2) / Q_r
        
        # 运行状态
        self.is_running = True
        self.current_head = rated_head
        self.current_flow = rated_flow
        
        print(f"泵特性曲线系数: a={self.a:.3f}, b={self.b:.5f}, c={self.c:.7f}")
    
    def calculate_pump_head(self, Q: float) -> float:
        """
        根据流量计算泵提供的扬程
        H = a - b·Q - c·Q²
        """
        H = self.a - self.b * Q - self.c * Q**2
        return max(0.0, H)
    
    def calculate_required_head(self, h_upstream: float, h_downstream: float,
                               z_upstream: float, z_downstream: float, Q: float) -> float:
        """
        计算系统所需扬程
        H_required = (z_down + h_down) - (z_up + h_up) + k·Q²
        """
        H_static = (z_downstream + h_downstream) - (z_upstream + h_upstream)
        H_friction = self.friction_coef * Q**2
        return H_static + H_friction
    
    def calculate_discharge(self, h_upstream: float, h_downstream: float,
                          t: Optional[float] = None, 
                          z_upstream: Optional[float] = None,
                          z_downstream: Optional[float] = None) -> tuple:
        """
        计算泵站流量（完整特性曲线模型）
        
        求解工作点：H_pump(Q) = H_required(Q)
        
        Args:
            h_upstream: 上游水深 (m)
            h_downstream: 下游水深 (m)
            t: 当前时间 (s)
            z_upstream: 上游底床高程 (m)
            z_downstream: 下游底床高程 (m)
        
        Returns:
            (discharge, flow_type): 流量 (m³/s) 和流态类型
        """
        if not self.is_running:
            self.current_flow = 0.0
            self.current_head = 0.0
            return 0.0, 'pump_off'
        
        # 检查最小吸入水头
        if h_upstream < 0.1:
            self.current_flow = 0.0
            self.current_head = 0.0
            return 0.0, 'insufficient_water'
        
        # 如果未提供底床高程，假设连续
        if z_upstream is None or z_downstream is None:
            # 兼容模式：使用额定流量
            self.current_flow = self.rated_flow
            self.current_head = self.rated_head
            return self.rated_flow, 'rated'
        
        # 牛顿迭代求解工作点
        Q = self.rated_flow  # 初值
        max_iterations = 20
        tolerance = 0.001
        
        for iteration in range(max_iterations):
            # 计算泵提供的扬程
            H_pump = self.calculate_pump_head(Q)
            
            # 计算系统所需扬程
            H_required = self.calculate_required_head(
                h_upstream, h_downstream,
                z_upstream, z_downstream, Q
            )
            
            # 残差
            residual = H_pump - H_required
            
            if abs(residual) < tolerance:
                # 收敛
                break
            
            # 计算导数
            dH_pump_dQ = -self.b - 2 * self.c * Q
            dH_required_dQ = 2 * self.friction_coef * Q
            dH_dQ = dH_pump_dQ - dH_required_dQ
            
            if abs(dH_dQ) < 1e-6:
                # 导数太小，停止迭代
                break
            
            # 牛顿更新
            Q_new = Q - residual / dH_dQ
            
            # 限制范围
            Q_new = max(0.0, min(Q_new, 2.0 * self.rated_flow))
            
            Q = Q_new
        
        # 更新状态
        self.current_flow = Q
        self.current_head = self.calculate_pump_head(Q)
        
        # 判断工况
        if Q <= self.rated_flow * 0.9:
            flow_type = 'low_flow'
        elif Q <= self.rated_flow * 1.1:
            flow_type = 'rated'
        else:
            flow_type = 'overload'
        
        return Q, flow_type
    
    def calculate_discharge_derivatives(self, h_upstream: float, h_downstream: float,
                                       t: Optional[float] = None) -> tuple:
        """
        计算流量对水深的导数（数值微分）
        """
        if not self.is_running or h_upstream < 0.1:
            return 0.0, 0.0
        
        # 简化：小的正值
        dQ_dh_up = 0.5
        dQ_dh_down = 0.0
        
        return dQ_dh_up, dQ_dh_down
    
    def set_running_state(self, is_running: bool):
        """设置泵站运行状态"""
        self.is_running = is_running
    
    def get_current_head(self) -> float:
        """获取当前扬程"""
        return self.current_head
    
    def get_pump_curve_data(self, n_points: int = 50) -> tuple:
        """
        获取泵特性曲线数据（用于绘图）
        
        Returns:
            (Q_array, H_array): 流量和扬程数组
        """
        Q_array = np.linspace(0, 1.5 * self.rated_flow, n_points)
        H_array = np.array([self.calculate_pump_head(Q) for Q in Q_array])
        return Q_array, H_array
    
    def __repr__(self) -> str:
        state = "ON" if self.is_running else "OFF"
        return (f"PumpStationAdvanced(position={self.position}m, "
                f"Q_rated={self.rated_flow}m³/s, Q_current={self.current_flow:.1f}m³/s, "
                f"H_shutoff={self.shutoff_head:.2f}m, H_current={self.current_head:.2f}m, state={state})")
