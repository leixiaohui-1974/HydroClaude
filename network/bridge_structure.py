#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
桥梁水工建筑物模块

实现桥梁过水计算，包括自由流和压力流两种流态。

理论基础：
1. 自由流（Free Flow）：下游水位低于桥底或桥面
   - 堰流公式：Q = Cd * B * h^(3/2) * √(2g)
   - 孔流公式：Q = Cd * A * √(2g * Δh)

2. 压力流（Pressure Flow）：下游水位淹没桥孔
   - 孔流公式：Q = Cd * A * √(2g * Δh)
   - Δh = h_upstream - h_downstream

3. 流态判断：
   - 自由流：h_downstream < z_deck
   - 压力流：h_downstream >= z_deck

作者: HydroClaude Team
日期: 2025-10-29
"""

import numpy as np
from typing import Dict, Optional, Literal


class Bridge:
    """
    桥梁水工建筑物类

    支持自由流和压力流计算，适用于河道中的桥梁过水能力分析。

    Attributes:
        bridge_id: 桥梁标识
        W_effective: 有效过流宽度 (m)
        H_opening: 桥孔净空高度 (m)
        z_bottom: 桥底高程 (m)
        z_deck: 桥面高程 (m) = z_bottom + H_opening
        Cd_weir: 堰流流量系数，典型值 0.4-0.6
        Cd_orifice: 孔流流量系数（自由流），典型值 0.6-0.8
        Cd_pressure: 孔流流量系数（压力流），典型值 0.7-0.9
        n_piers: 桥墩数量
        pier_width: 单个桥墩宽度 (m)
    """

    def __init__(
        self,
        bridge_id: str,
        total_width: float,
        opening_height: float,
        bottom_elevation: float,
        n_piers: int = 0,
        pier_width: float = 0.0,
        Cd_weir: float = 0.5,
        Cd_orifice: float = 0.7,
        Cd_pressure: float = 0.8
    ):
        """
        初始化桥梁结构

        Args:
            bridge_id: 桥梁标识
            total_width: 桥孔总宽度 (m)，不含桥墩
            opening_height: 桥孔净空高度 (m)
            bottom_elevation: 桥底高程 (m)
            n_piers: 桥墩数量，默认0（无桥墩）
            pier_width: 单个桥墩宽度 (m)，默认0
            Cd_weir: 堰流流量系数，默认0.5
            Cd_orifice: 孔流流量系数（自由流），默认0.7
            Cd_pressure: 孔流流量系数（压力流），默认0.8

        Raises:
            ValueError: 参数不合理时抛出异常
        """
        # 验证输入参数
        if total_width <= 0:
            raise ValueError(f"total_width must be > 0, got {total_width}")
        if opening_height <= 0:
            raise ValueError(f"opening_height must be > 0, got {opening_height}")
        if n_piers < 0:
            raise ValueError(f"n_piers must be >= 0, got {n_piers}")
        if pier_width < 0:
            raise ValueError(f"pier_width must be >= 0, got {pier_width}")
        if n_piers * pier_width >= total_width:
            raise ValueError(
                f"Total pier width ({n_piers * pier_width:.2f} m) "
                f"must be < total_width ({total_width:.2f} m)"
            )
        if not (0 < Cd_weir < 1):
            raise ValueError(f"Cd_weir must be in (0, 1), got {Cd_weir}")
        if not (0 < Cd_orifice < 1):
            raise ValueError(f"Cd_orifice must be in (0, 1), got {Cd_orifice}")
        if not (0 < Cd_pressure < 1):
            raise ValueError(f"Cd_pressure must be in (0, 1), got {Cd_pressure}")

        # 基本属性
        self.bridge_id = bridge_id
        self.total_width = total_width
        self.H_opening = opening_height
        self.z_bottom = bottom_elevation
        self.z_deck = bottom_elevation + opening_height

        # 桥墩参数
        self.n_piers = n_piers
        self.pier_width = pier_width

        # 有效过流宽度 = 总宽度 - 桥墩宽度
        self.W_effective = total_width - n_piers * pier_width

        # 流量系数
        self.Cd_weir = Cd_weir
        self.Cd_orifice = Cd_orifice
        self.Cd_pressure = Cd_pressure

        # 重力加速度
        self.g = 9.81  # m/s²

    def classify_flow_regime(
        self,
        h_upstream: float,
        h_downstream: float
    ) -> Literal["free_flow_weir", "free_flow_orifice", "pressure_flow"]:
        """
        判断桥梁流态

        Args:
            h_upstream: 上游水位高程 (m)
            h_downstream: 下游水位高程 (m)

        Returns:
            流态类型：
            - "free_flow_weir": 自由流-堰流（上游水位低，流经桥底）
            - "free_flow_orifice": 自由流-孔流（上游水位高但下游未淹没）
            - "pressure_flow": 压力流（下游淹没桥孔）
        """
        # 判断压力流：下游水位是否淹没桥面
        if h_downstream >= self.z_deck:
            return "pressure_flow"

        # 判断自由流类型
        # 如果上游水位接近或超过桥面，且下游未淹没，为自由孔流
        # 否则为堰流
        h_above_bottom = h_upstream - self.z_bottom

        # 经验准则：当上游水深 > 0.8 * H_opening 时，转为孔流
        if h_above_bottom > 0.8 * self.H_opening:
            return "free_flow_orifice"
        else:
            return "free_flow_weir"

    def compute_discharge(
        self,
        h_upstream: float,
        h_downstream: float
    ) -> Dict[str, float]:
        """
        计算桥梁过流流量

        Args:
            h_upstream: 上游水位高程 (m)
            h_downstream: 下游水位高程 (m)

        Returns:
            字典，包含：
            - 'Q': 流量 (m³/s)
            - 'regime': 流态类型
            - 'velocity': 平均流速 (m/s)
            - 'head_loss': 水头损失 (m)

        Raises:
            ValueError: 水位低于桥底时抛出异常
        """
        if h_upstream < self.z_bottom:
            raise ValueError(
                f"Upstream water level ({h_upstream:.2f} m) is below "
                f"bridge bottom ({self.z_bottom:.2f} m)"
            )

        # 判断流态
        regime = self.classify_flow_regime(h_upstream, h_downstream)

        # 根据流态计算流量
        if regime == "free_flow_weir":
            Q = self._compute_weir_flow(h_upstream)
            A = self.W_effective * min(h_upstream - self.z_bottom, self.H_opening)

        elif regime == "free_flow_orifice":
            Q = self._compute_free_orifice_flow(h_upstream, h_downstream)
            A = self.W_effective * self.H_opening

        else:  # pressure_flow
            Q = self._compute_pressure_flow(h_upstream, h_downstream)
            A = self.W_effective * self.H_opening

        # 计算平均流速
        v = Q / A if A > 0 else 0.0

        # 计算水头损失（能量方程）
        # ΔH = (h_up + v_up²/2g) - (h_down + v_down²/2g)
        # 简化：假设桥梁上下游流速相近，水头损失主要为水位差
        head_loss = max(0.0, h_upstream - h_downstream)

        return {
            'Q': Q,
            'regime': regime,
            'velocity': v,
            'head_loss': head_loss
        }

    def _compute_weir_flow(self, h_upstream: float) -> float:
        """
        计算堰流流量

        堰流公式：Q = Cd * B * h^(3/2) * √(2g)

        Args:
            h_upstream: 上游水位高程 (m)

        Returns:
            流量 (m³/s)
        """
        # 堰顶水头（相对于桥底）
        h_over_weir = h_upstream - self.z_bottom

        # 限制最大水头为桥孔高度
        h_over_weir = min(h_over_weir, self.H_opening)

        if h_over_weir <= 0:
            return 0.0

        # 堰流公式
        Q = self.Cd_weir * self.W_effective * (h_over_weir ** 1.5) * np.sqrt(2 * self.g)

        return Q

    def _compute_free_orifice_flow(
        self,
        h_upstream: float,
        h_downstream: float
    ) -> float:
        """
        计算自由孔流流量（下游未淹没）

        孔流公式：Q = Cd * A * √(2g * Δh)
        Δh = h_upstream - max(h_downstream, z_deck)

        Args:
            h_upstream: 上游水位高程 (m)
            h_downstream: 下游水位高程 (m)

        Returns:
            流量 (m³/s)
        """
        # 有效水头差
        # 自由流：下游控制水位取桥面或下游水位的较大值
        h_control = max(h_downstream, self.z_deck)
        dh = h_upstream - h_control

        if dh <= 0:
            return 0.0

        # 孔流面积
        A = self.W_effective * self.H_opening

        # 孔流公式
        Q = self.Cd_orifice * A * np.sqrt(2 * self.g * dh)

        return Q

    def _compute_pressure_flow(
        self,
        h_upstream: float,
        h_downstream: float
    ) -> float:
        """
        计算压力流流量（下游淹没桥孔）

        压力流公式：Q = Cd * A * √(2g * Δh)
        Δh = h_upstream - h_downstream

        Args:
            h_upstream: 上游水位高程 (m)
            h_downstream: 下游水位高程 (m)

        Returns:
            流量 (m³/s)
        """
        # 水头差（上下游水位差）
        dh = h_upstream - h_downstream

        if dh <= 0:
            return 0.0

        # 孔流面积（完全淹没）
        A = self.W_effective * self.H_opening

        # 压力流公式
        Q = self.Cd_pressure * A * np.sqrt(2 * self.g * dh)

        return Q

    def compute_backwater_effect(
        self,
        Q: float,
        h_downstream: float,
        method: str = "iterative"
    ) -> float:
        """
        计算桥梁壅水效应（给定流量和下游水位，反推上游水位）

        Args:
            Q: 流量 (m³/s)
            h_downstream: 下游水位高程 (m)
            method: 计算方法，'iterative'（迭代法）或 'analytical'（解析法）

        Returns:
            上游水位高程 (m)

        Raises:
            ValueError: 迭代不收敛时抛出异常
        """
        if Q <= 0:
            return h_downstream

        if method == "iterative":
            return self._compute_backwater_iterative(Q, h_downstream)
        elif method == "analytical":
            # 简化解析解（假设压力流）
            return self._compute_backwater_analytical(Q, h_downstream)
        else:
            raise ValueError(f"Unknown method: {method}")

    def _compute_backwater_iterative(
        self,
        Q: float,
        h_downstream: float,
        tol: float = 1e-4,
        max_iter: int = 100
    ) -> float:
        """
        迭代法计算上游水位

        使用牛顿迭代法求解：f(h_up) = Q_computed(h_up) - Q_target = 0

        Args:
            Q: 目标流量 (m³/s)
            h_downstream: 下游水位高程 (m)
            tol: 收敛容差 (m³/s)
            max_iter: 最大迭代次数

        Returns:
            上游水位高程 (m)

        Raises:
            ValueError: 迭代不收敛时抛出异常
        """
        # 初始猜测：上游水位 = 下游水位 + 估计水头损失
        # 估计水头损失：从压力流公式反推 dh ≈ (Q / (Cd * A))² / (2g)
        A = self.W_effective * self.H_opening
        dh_est = (Q / (self.Cd_pressure * A)) ** 2 / (2 * self.g)
        h_up = h_downstream + dh_est

        # 确保初始猜测不低于桥底
        h_up = max(h_up, self.z_bottom + 0.1)

        for iteration in range(max_iter):
            # 计算当前上游水位对应的流量
            result = self.compute_discharge(h_up, h_downstream)
            Q_computed = result['Q']

            # 残差
            residual = Q_computed - Q

            if abs(residual) < tol:
                return h_up

            # 数值导数：dQ/dh_up
            dh = max(1e-4, h_up * 1e-6)
            result_perturbed = self.compute_discharge(h_up + dh, h_downstream)
            Q_perturbed = result_perturbed['Q']
            dQ_dh = (Q_perturbed - Q_computed) / dh

            if abs(dQ_dh) < 1e-10:
                # 导数太小，使用比例调整
                adjustment = 0.1 * residual / Q if Q > 0 else 0.01
                h_up += adjustment
            else:
                # 牛顿迭代
                delta_h = -residual / dQ_dh
                # 限制步长以提高稳定性
                delta_h = np.clip(delta_h, -0.5, 0.5)
                h_up += delta_h

            # 确保上游水位不低于桥底
            h_up = max(h_up, self.z_bottom + 0.01)

        raise ValueError(
            f"Backwater calculation did not converge after {max_iter} iterations. "
            f"Q_target = {Q:.2f} m³/s, last Q_computed = {Q_computed:.2f} m³/s"
        )

    def _compute_backwater_analytical(
        self,
        Q: float,
        h_downstream: float
    ) -> float:
        """
        解析法计算上游水位（假设压力流）

        从压力流公式反推：h_up = h_down + (Q / (Cd * A))² / (2g)

        Args:
            Q: 流量 (m³/s)
            h_downstream: 下游水位高程 (m)

        Returns:
            上游水位高程 (m)
        """
        A = self.W_effective * self.H_opening
        dh = (Q / (self.Cd_pressure * A)) ** 2 / (2 * self.g)
        h_upstream = h_downstream + dh

        return h_upstream

    def properties(self) -> Dict[str, float]:
        """
        返回桥梁几何属性

        Returns:
            字典，包含桥梁几何参数
        """
        return {
            'total_width': self.total_width,
            'effective_width': self.W_effective,
            'opening_height': self.H_opening,
            'bottom_elevation': self.z_bottom,
            'deck_elevation': self.z_deck,
            'n_piers': self.n_piers,
            'pier_width': self.pier_width,
            'total_pier_width': self.n_piers * self.pier_width,
            'opening_area': self.W_effective * self.H_opening,
            'Cd_weir': self.Cd_weir,
            'Cd_orifice': self.Cd_orifice,
            'Cd_pressure': self.Cd_pressure
        }

    def __repr__(self) -> str:
        """字符串表示"""
        return (
            f"Bridge(id='{self.bridge_id}', "
            f"W_eff={self.W_effective:.2f}m, "
            f"H={self.H_opening:.2f}m, "
            f"z_bottom={self.z_bottom:.2f}m, "
            f"n_piers={self.n_piers})"
        )


def create_bridge(
    bridge_id: str,
    total_width: float,
    opening_height: float,
    bottom_elevation: float,
    **kwargs
) -> Bridge:
    """
    便捷函数：创建桥梁对象

    Args:
        bridge_id: 桥梁标识
        total_width: 桥孔总宽度 (m)
        opening_height: 桥孔净空高度 (m)
        bottom_elevation: 桥底高程 (m)
        **kwargs: 其他可选参数（n_piers, pier_width, Cd_weir, Cd_orifice, Cd_pressure）

    Returns:
        Bridge 对象

    Example:
        >>> bridge = create_bridge(
        ...     bridge_id="BR001",
        ...     total_width=30.0,
        ...     opening_height=5.0,
        ...     bottom_elevation=100.0,
        ...     n_piers=2,
        ...     pier_width=1.5
        ... )
    """
    return Bridge(
        bridge_id=bridge_id,
        total_width=total_width,
        opening_height=opening_height,
        bottom_elevation=bottom_elevation,
        **kwargs
    )
