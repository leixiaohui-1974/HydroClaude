#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
涵洞/倒虹吸水工建筑物模块

实现涵洞和倒虹吸过流计算，包括进口控制流和出口控制流。

理论基础：
1. 进口控制流（Inlet Control）：
   - 流量由进口条件控制
   - Q = Cd * A * √(2g * HW)，HW为进口水头
   - 适用于陡坡、短管、自由出流

2. 出口控制流（Outlet Control）：
   - 流量由出口条件和管道摩阻控制
   - 能量方程：H_inlet = H_outlet + h_f + h_e
   - h_f: 摩阻损失（Manning或Darcy-Weisbach）
   - h_e: 局部损失（进口、出口、弯头）

3. 倒虹吸（Inverted Siphon）：
   - 管道式过水建筑物，可跨越低洼地
   - 考虑高程变化和能量损失
   - 需要排气和沉沙设施

作者: HydroClaude Team
日期: 2025-10-29
"""

import numpy as np
from typing import Dict, Optional, Literal, Tuple


class Culvert:
    """
    涵洞/倒虹吸水工建筑物类

    支持进口控制和出口控制两种流态，适用于涵洞、倒虹吸等管道式建筑物。

    Attributes:
        culvert_id: 涵洞标识
        diameter: 管径 (m)，圆形断面
        width: 宽度 (m)，矩形断面
        height: 高度 (m)，矩形断面
        length: 涵洞长度 (m)
        inlet_elevation: 进口底高程 (m)
        outlet_elevation: 出口底高程 (m)
        n_barrels: 孔数（并联管道数）
        manning_n: Manning粗糙系数
        shape: 断面形状 'circular' 或 'rectangular'
        Ke_inlet: 进口损失系数，典型值 0.2-0.5
        Ke_outlet: 出口损失系数，典型值 0.3-1.0
        Ke_bends: 弯头损失系数，典型值 0.1-0.5 per bend
        n_bends: 弯头数量
    """

    def __init__(
        self,
        culvert_id: str,
        length: float,
        inlet_elevation: float,
        outlet_elevation: float,
        shape: Literal["circular", "rectangular"] = "circular",
        diameter: Optional[float] = None,
        width: Optional[float] = None,
        height: Optional[float] = None,
        n_barrels: int = 1,
        manning_n: float = 0.013,
        Ke_inlet: float = 0.5,
        Ke_outlet: float = 1.0,
        n_bends: int = 0,
        Ke_bends: float = 0.2
    ):
        """
        初始化涵洞结构

        Args:
            culvert_id: 涵洞标识
            length: 涵洞长度 (m)
            inlet_elevation: 进口底高程 (m)
            outlet_elevation: 出口底高程 (m)
            shape: 断面形状 'circular' 或 'rectangular'
            diameter: 管径 (m)，圆形断面必须提供
            width: 宽度 (m)，矩形断面必须提供
            height: 高度 (m)，矩形断面必须提供
            n_barrels: 孔数，默认1
            manning_n: Manning粗糙系数，默认0.013（混凝土管）
            Ke_inlet: 进口损失系数，默认0.5
            Ke_outlet: 出口损失系数，默认1.0
            n_bends: 弯头数量，默认0
            Ke_bends: 单个弯头损失系数，默认0.2

        Raises:
            ValueError: 参数不合理时抛出异常
        """
        # 验证基本参数
        if length <= 0:
            raise ValueError(f"length must be > 0, got {length}")
        if n_barrels < 1:
            raise ValueError(f"n_barrels must be >= 1, got {n_barrels}")
        if manning_n <= 0:
            raise ValueError(f"manning_n must be > 0, got {manning_n}")

        # 验证断面参数
        if shape == "circular":
            if diameter is None or diameter <= 0:
                raise ValueError(f"diameter must be provided and > 0 for circular culvert")
            self.diameter = diameter
            self.width = None
            self.height = None
            self.D_h = diameter  # 水力直径
            self.A_full = np.pi * (diameter / 2) ** 2  # 满流断面积
            self.P_full = np.pi * diameter  # 满流湿周
        elif shape == "rectangular":
            if width is None or width <= 0:
                raise ValueError(f"width must be provided and > 0 for rectangular culvert")
            if height is None or height <= 0:
                raise ValueError(f"height must be provided and > 0 for rectangular culvert")
            self.diameter = None
            self.width = width
            self.height = height
            self.D_h = 4 * width * height / (2 * (width + height))  # 水力直径
            self.A_full = width * height  # 满流断面积
            self.P_full = 2 * (width + height)  # 满流湿周
        else:
            raise ValueError(f"shape must be 'circular' or 'rectangular', got {shape}")

        # 基本属性
        self.culvert_id = culvert_id
        self.shape = shape
        self.length = length
        self.z_inlet = inlet_elevation
        self.z_outlet = outlet_elevation
        self.n_barrels = n_barrels
        self.n = manning_n

        # 损失系数
        self.Ke_inlet = Ke_inlet
        self.Ke_outlet = Ke_outlet
        self.n_bends = n_bends
        self.Ke_bends = Ke_bends

        # 底坡
        self.S0 = (inlet_elevation - outlet_elevation) / length

        # 重力加速度
        self.g = 9.81  # m/s²

    def classify_flow_regime(
        self,
        h_upstream: float,
        h_downstream: float
    ) -> Literal["inlet_control", "outlet_control"]:
        """
        判断涵洞流态（进口控制 vs 出口控制）

        简化判据：
        - 进口控制：陡坡、短管、自由出流、下游水位低
        - 出口控制：缓坡、长管、淹没出流、下游水位高

        Args:
            h_upstream: 上游水位高程 (m)
            h_downstream: 下游水位高程 (m)

        Returns:
            流态类型：'inlet_control' 或 'outlet_control'
        """
        # 判据1：下游水位是否淹没涵洞出口
        if h_downstream > (self.z_outlet + 0.8 * self._get_barrel_height()):
            # 下游淹没，通常为出口控制
            return "outlet_control"

        # 判据2：底坡是否足够陡
        if self.S0 > 0.02:  # 陡坡
            return "inlet_control"

        # 判据3：长度与直径比
        L_D_ratio = self.length / self.D_h
        if L_D_ratio < 10:  # 短管
            return "inlet_control"

        # 默认为出口控制
        return "outlet_control"

    def compute_discharge(
        self,
        h_upstream: float,
        h_downstream: float,
        method: Literal["auto", "inlet", "outlet"] = "auto"
    ) -> Dict[str, float]:
        """
        计算涵洞过流流量

        Args:
            h_upstream: 上游水位高程 (m)
            h_downstream: 下游水位高程 (m)
            method: 计算方法
                    - 'auto': 自动判断流态
                    - 'inlet': 强制使用进口控制
                    - 'outlet': 强制使用出口控制

        Returns:
            字典，包含：
            - 'Q': 总流量 (m³/s)，所有孔的总和
            - 'Q_per_barrel': 单孔流量 (m³/s)
            - 'regime': 流态类型
            - 'velocity': 平均流速 (m/s)
            - 'head_loss': 总水头损失 (m)
            - 'friction_loss': 摩阻损失 (m)
            - 'form_loss': 局部损失 (m)

        Raises:
            ValueError: 水位低于涵洞底时抛出异常
        """
        if h_upstream < self.z_inlet:
            raise ValueError(
                f"Upstream water level ({h_upstream:.2f} m) is below "
                f"culvert inlet ({self.z_inlet:.2f} m)"
            )

        # 确定流态
        if method == "auto":
            regime = self.classify_flow_regime(h_upstream, h_downstream)
        elif method == "inlet":
            regime = "inlet_control"
        elif method == "outlet":
            regime = "outlet_control"
        else:
            raise ValueError(f"Unknown method: {method}")

        # 根据流态计算流量
        if regime == "inlet_control":
            result = self._compute_inlet_control(h_upstream, h_downstream)
        else:  # outlet_control
            result = self._compute_outlet_control(h_upstream, h_downstream)

        result['regime'] = regime
        result['Q'] = result['Q_per_barrel'] * self.n_barrels

        return result

    def _compute_inlet_control(
        self,
        h_upstream: float,
        h_downstream: float
    ) -> Dict[str, float]:
        """
        计算进口控制流量

        使用孔流公式：Q = Cd * A * √(2g * HW)
        HW = h_upstream - z_inlet（进口水头）

        Args:
            h_upstream: 上游水位高程 (m)
            h_downstream: 下游水位高程 (m)

        Returns:
            流量计算结果
        """
        # 进口水头
        HW = h_upstream - self.z_inlet
        HW = max(0.0, HW)

        # 有效断面积（满流）
        A = self.A_full

        # 流量系数（进口控制，典型值 0.6-0.65）
        Cd = 0.62

        # 单孔流量
        Q_per_barrel = Cd * A * np.sqrt(2 * self.g * HW)

        # 平均流速
        v = Q_per_barrel / A if A > 0 else 0.0

        # 进口控制下，主要损失在进口
        head_loss = h_upstream - h_downstream
        friction_loss = 0.0  # 进口控制时摩阻可忽略
        form_loss = head_loss

        return {
            'Q_per_barrel': Q_per_barrel,
            'velocity': v,
            'head_loss': head_loss,
            'friction_loss': friction_loss,
            'form_loss': form_loss
        }

    def _compute_outlet_control(
        self,
        h_upstream: float,
        h_downstream: float
    ) -> Dict[str, float]:
        """
        计算出口控制流量

        能量方程：H_up = H_down + h_f + h_e
        h_f = Manning摩阻损失
        h_e = 局部损失 = (Ke_inlet + Ke_outlet + n_bends * Ke_bends) * v²/(2g)

        Args:
            h_upstream: 上游水位高程 (m)
            h_downstream: 下游水位高程 (m)

        Returns:
            流量计算结果
        """
        # 可用水头
        H_available = h_upstream - h_downstream

        if H_available <= 0:
            return {
                'Q_per_barrel': 0.0,
                'velocity': 0.0,
                'head_loss': 0.0,
                'friction_loss': 0.0,
                'form_loss': 0.0
            }

        # 迭代求解流量
        Q_per_barrel = self._solve_outlet_control_iterative(h_upstream, h_downstream)

        # 计算流速
        A = self.A_full
        v = Q_per_barrel / A if A > 0 else 0.0

        # 计算损失
        h_f = self._compute_friction_loss(Q_per_barrel)
        h_e = self._compute_form_loss(v)
        head_loss = h_f + h_e

        return {
            'Q_per_barrel': Q_per_barrel,
            'velocity': v,
            'head_loss': head_loss,
            'friction_loss': h_f,
            'form_loss': h_e
        }

    def _solve_outlet_control_iterative(
        self,
        h_upstream: float,
        h_downstream: float,
        tol: float = 1e-4,
        max_iter: int = 50
    ) -> float:
        """
        迭代求解出口控制流量

        能量方程：h_up = h_down + h_f(Q) + h_e(Q)

        Args:
            h_upstream: 上游水位高程 (m)
            h_downstream: 下游水位高程 (m)
            tol: 收敛容差 (m)
            max_iter: 最大迭代次数

        Returns:
            单孔流量 (m³/s)
        """
        H_available = h_upstream - h_downstream

        # 初始猜测：忽略损失，用简化公式估算
        Q_guess = 0.5 * self.A_full * np.sqrt(2 * self.g * H_available)

        for iteration in range(max_iter):
            # 计算当前流量对应的损失
            v = Q_guess / self.A_full
            h_f = self._compute_friction_loss(Q_guess)
            h_e = self._compute_form_loss(v)
            h_total_loss = h_f + h_e

            # 残差（能量不平衡）
            residual = H_available - h_total_loss

            if abs(residual) < tol:
                return Q_guess

            # 更新流量（比例调整）
            # H_available = h_loss(Q) ∝ Q² （近似）
            # 因此 Q_new = Q_old * √(H_available / h_loss_old)
            if h_total_loss > 0:
                correction_factor = np.sqrt(H_available / h_total_loss)
                # 限制调整幅度以提高稳定性
                correction_factor = np.clip(correction_factor, 0.5, 1.5)
                Q_guess *= correction_factor
            else:
                Q_guess *= 1.1

        # 如果未收敛，返回最后的估计值
        return Q_guess

    def _compute_friction_loss(self, Q_per_barrel: float) -> float:
        """
        计算摩阻损失（Manning公式）

        h_f = (n * Q / A)² * L / R^(4/3)

        Args:
            Q_per_barrel: 单孔流量 (m³/s)

        Returns:
            摩阻损失 (m)
        """
        if Q_per_barrel <= 0:
            return 0.0

        A = self.A_full
        R = A / self.P_full  # 水力半径

        # Manning公式变形
        v = Q_per_barrel / A
        h_f = (self.n * v) ** 2 * self.length / (R ** (4/3))

        return h_f

    def _compute_form_loss(self, v: float) -> float:
        """
        计算局部损失

        h_e = Σ Ke * v² / (2g)

        Args:
            v: 流速 (m/s)

        Returns:
            局部损失 (m)
        """
        if v <= 0:
            return 0.0

        # 总局部损失系数
        Ke_total = self.Ke_inlet + self.Ke_outlet + self.n_bends * self.Ke_bends

        h_e = Ke_total * (v ** 2) / (2 * self.g)

        return h_e

    def _get_barrel_height(self) -> float:
        """获取单孔高度"""
        if self.shape == "circular":
            return self.diameter
        else:  # rectangular
            return self.height

    def compute_backwater_effect(
        self,
        Q_total: float,
        h_downstream: float,
        method: Literal["auto", "inlet", "outlet"] = "auto"
    ) -> float:
        """
        计算涵洞壅水效应（给定总流量和下游水位，反推上游水位）

        Args:
            Q_total: 总流量 (m³/s)，所有孔的总和
            h_downstream: 下游水位高程 (m)
            method: 计算方法，同 compute_discharge()

        Returns:
            上游水位高程 (m)

        Raises:
            ValueError: 迭代不收敛时抛出异常
        """
        if Q_total <= 0:
            return h_downstream

        # 单孔流量
        Q_per_barrel = Q_total / self.n_barrels

        # 迭代求解上游水位
        h_up_guess = h_downstream + 0.5  # 初始猜测

        tol = 1e-4
        max_iter = 100

        for iteration in range(max_iter):
            result = self.compute_discharge(h_up_guess, h_downstream, method=method)
            Q_computed = result['Q']

            residual = Q_computed - Q_total

            if abs(residual) < tol:
                return h_up_guess

            # 数值导数
            dh = 0.01
            result_perturbed = self.compute_discharge(h_up_guess + dh, h_downstream, method=method)
            Q_perturbed = result_perturbed['Q']
            dQ_dh = (Q_perturbed - Q_computed) / dh

            if abs(dQ_dh) > 1e-10:
                # 牛顿迭代
                delta_h = -residual / dQ_dh
                delta_h = np.clip(delta_h, -0.5, 0.5)
                h_up_guess += delta_h
            else:
                # 比例调整
                h_up_guess += 0.1 * residual / Q_total if Q_total > 0 else 0.01

            # 确保上游水位不低于涵洞底
            h_up_guess = max(h_up_guess, self.z_inlet + 0.01)

        raise ValueError(
            f"Backwater calculation did not converge after {max_iter} iterations. "
            f"Q_target = {Q_total:.2f} m³/s"
        )

    def properties(self) -> Dict[str, float]:
        """
        返回涵洞几何属性

        Returns:
            字典，包含涵洞几何参数
        """
        props = {
            'shape': self.shape,
            'length': self.length,
            'inlet_elevation': self.z_inlet,
            'outlet_elevation': self.z_outlet,
            'bottom_slope': self.S0,
            'n_barrels': self.n_barrels,
            'manning_n': self.n,
            'hydraulic_diameter': self.D_h,
            'full_area_per_barrel': self.A_full,
            'full_perimeter': self.P_full,
            'Ke_inlet': self.Ke_inlet,
            'Ke_outlet': self.Ke_outlet,
            'n_bends': self.n_bends,
            'Ke_bends': self.Ke_bends
        }

        if self.shape == "circular":
            props['diameter'] = self.diameter
        else:  # rectangular
            props['width'] = self.width
            props['height'] = self.height

        return props

    def __repr__(self) -> str:
        """字符串表示"""
        if self.shape == "circular":
            shape_str = f"D={self.diameter:.2f}m"
        else:
            shape_str = f"{self.width:.2f}m×{self.height:.2f}m"

        return (
            f"Culvert(id='{self.culvert_id}', "
            f"{shape_str}, "
            f"L={self.length:.1f}m, "
            f"n_barrels={self.n_barrels})"
        )


def create_culvert(
    culvert_id: str,
    length: float,
    inlet_elevation: float,
    outlet_elevation: float,
    **kwargs
) -> Culvert:
    """
    便捷函数：创建涵洞对象

    Args:
        culvert_id: 涵洞标识
        length: 涵洞长度 (m)
        inlet_elevation: 进口底高程 (m)
        outlet_elevation: 出口底高程 (m)
        **kwargs: 其他可选参数

    Returns:
        Culvert 对象

    Example:
        >>> culvert = create_culvert(
        ...     culvert_id="CV001",
        ...     length=50.0,
        ...     inlet_elevation=100.0,
        ...     outlet_elevation=99.5,
        ...     shape="circular",
        ...     diameter=2.0,
        ...     n_barrels=2
        ... )
    """
    return Culvert(
        culvert_id=culvert_id,
        length=length,
        inlet_elevation=inlet_elevation,
        outlet_elevation=outlet_elevation,
        **kwargs
    )
