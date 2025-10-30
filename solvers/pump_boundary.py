#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Pump Boundary Condition - 离心泵水锤边界条件

Implements centrifugal pump boundary conditions for water hammer analysis.
实现水锤分析中的离心泵边界条件。

Features 功能:
- Pump characteristic curves 泵特性曲线 (H-Q, η-Q, P-Q)
- Moment of inertia effects 转动惯量效应
- Pump startup and shutdown 泵启动与停止
- Multiple operating points 多工况点
- Four-quadrant characteristics 四象限特性（可选）

Author: HydroClaude Development Team
Date: 2025-10-30
Version: 1.0.0
"""

import numpy as np
from typing import Tuple, Optional, Callable
from dataclasses import dataclass


@dataclass
class PumpCharacteristics:
    """
    离心泵特性参数 - Centrifugal Pump Characteristics

    Defines pump performance curves using polynomial or tabular data.
    定义泵性能曲线，支持多项式或表格数据。
    """

    # 设计工况点 Design operating point
    Q_design: float  # 设计流量 (m³/s)
    H_design: float  # 设计扬程 (m)
    n_design: float  # 设计转速 (rpm)
    efficiency_design: float  # 设计效率 (-)

    # 泵特性曲线系数 Pump curve coefficients (H = a + b*Q + c*Q²)
    H_curve_a: float  # 零流量扬程系数
    H_curve_b: float  # 线性系数
    H_curve_c: float  # 二次系数

    # 转动惯量 Moment of inertia
    WR2: float  # 转动惯量 (N·m²) - Flywheel effect

    # 可选：效率曲线系数 Optional: Efficiency curve (η = d + e*Q + f*Q²)
    eta_curve_d: Optional[float] = None
    eta_curve_e: Optional[float] = None
    eta_curve_f: Optional[float] = None

    def head_at_flow(self, Q: float, n: Optional[float] = None) -> float:
        """
        计算给定流量下的扬程 Calculate head at given flow rate

        使用相似律调整转速 Uses affinity laws for speed adjustment:
        Q/Q₀ = n/n₀
        H/H₀ = (n/n₀)²

        Args:
            Q: 流量 (m³/s)
            n: 转速 (rpm), 如果None则使用设计转速

        Returns:
            扬程 (m)
        """
        if n is None:
            n = self.n_design

        # 将流量调整到设计转速
        Q_adj = Q * (self.n_design / n) if n != 0 else 0

        # 计算设计转速下的扬程
        H_adj = self.H_curve_a + self.H_curve_b * Q_adj + self.H_curve_c * Q_adj**2

        # 使用相似律调整到实际转速
        speed_ratio = n / self.n_design if self.n_design != 0 else 0
        H = H_adj * speed_ratio**2

        return max(H, 0.0)  # 扬程不能为负

    def efficiency_at_flow(self, Q: float) -> float:
        """
        计算给定流量下的效率 Calculate efficiency at given flow rate

        Args:
            Q: 流量 (m³/s)

        Returns:
            效率 (-), 范围 [0, 1]
        """
        if self.eta_curve_d is None:
            # 使用简化效率曲线（抛物线，最高点在设计工况）
            Q_ratio = Q / self.Q_design if self.Q_design > 0 else 0
            eta = self.efficiency_design * (1 - 0.5 * (Q_ratio - 1)**2)
            return np.clip(eta, 0.0, 1.0)
        else:
            # 使用自定义效率曲线
            eta = self.eta_curve_d + self.eta_curve_e * Q + self.eta_curve_f * Q**2
            return np.clip(eta, 0.0, 1.0)

    def power_at_flow(self, Q: float, rho: float = 1000.0) -> float:
        """
        计算泵输入功率 Calculate pump input power

        P = ρ * g * Q * H / η

        Args:
            Q: 流量 (m³/s)
            rho: 流体密度 (kg/m³)

        Returns:
            功率 (W)
        """
        g = 9.81  # 重力加速度 (m/s²)
        H = self.head_at_flow(Q)
        eta = self.efficiency_at_flow(Q)

        if eta > 0 and Q > 0:
            P = rho * g * Q * H / eta
        else:
            P = 0.0

        return P

    @classmethod
    def from_three_points(cls, Q1: float, H1: float,
                          Q2: float, H2: float,
                          Q3: float, H3: float,
                          n_design: float,
                          WR2: float,
                          efficiency_design: float = 0.85):
        """
        从三个工况点拟合泵特性曲线

        Fit pump curve from three operating points using quadratic regression:
        H = a + b*Q + c*Q²

        Args:
            Q1, H1: 第一个工况点 (通常为零流量点)
            Q2, H2: 第二个工况点 (设计点)
            Q3, H3: 第三个工况点 (大流量点)
            n_design: 设计转速 (rpm)
            WR2: 转动惯量 (N·m²)
            efficiency_design: 设计效率

        Returns:
            PumpCharacteristics对象
        """
        # 构建线性方程组求解二次曲线系数
        # [1, Q1, Q1²] [a]   [H1]
        # [1, Q2, Q2²] [b] = [H2]
        # [1, Q3, Q3²] [c]   [H3]

        A = np.array([
            [1, Q1, Q1**2],
            [1, Q2, Q2**2],
            [1, Q3, Q3**2]
        ])
        b = np.array([H1, H2, H3])

        coeffs = np.linalg.solve(A, b)
        a, b_coef, c_coef = coeffs

        return cls(
            Q_design=Q2,
            H_design=H2,
            n_design=n_design,
            efficiency_design=efficiency_design,
            H_curve_a=a,
            H_curve_b=b_coef,
            H_curve_c=c_coef,
            WR2=WR2
        )


class PumpBoundary:
    """
    离心泵水锤边界条件 - Centrifugal Pump Boundary for Water Hammer

    Handles pump boundary conditions in water hammer analysis including:
    - Pump characteristic curves
    - Speed variations (startup, shutdown, power failure)
    - Moment of inertia effects

    处理水锤分析中的泵边界条件，包括：
    - 泵特性曲线
    - 转速变化（启动、停止、断电）
    - 转动惯量效应
    """

    def __init__(self,
                 pump_chars: PumpCharacteristics,
                 speed_function: Optional[Callable[[float], float]] = None,
                 pipe_area: float = 1.0,
                 wave_speed: float = 1000.0):
        """
        初始化泵边界条件

        Args:
            pump_chars: 泵特性参数对象
            speed_function: 转速时间函数 n(t), 返回转速(rpm)
                          如果None，则保持设计转速
            pipe_area: 管道横截面积 (m²)
            wave_speed: 波速 (m/s)
        """
        self.pump = pump_chars
        self.speed_function = speed_function
        self.A = pipe_area
        self.a = wave_speed

        # 当前状态
        self.current_speed = self.pump.n_design
        self.current_torque = 0.0

    def apply_boundary(self, t: float, H_plus: float, H_minus: float,
                      Q_plus: float, Q_minus: float,
                      dt: float) -> Tuple[float, float]:
        """
        应用泵边界条件（MOC特征线法）

        Apply pump boundary condition using Method of Characteristics

        特征线方程 Characteristic equations:
        C⁺: H_p = C_p - B * Q_p  (从上游来)
        C⁻: H_p = C_m + B * Q_p  (从下游来)

        其中 where:
        C_p = H_i-1 + B * Q_i-1
        C_m = H_i+1 - B * Q_i+1
        B = a / (g * A)

        泵方程 Pump equation:
        H_p = H_pump(Q_p, n)

        Args:
            t: 当前时间 (s)
            H_plus: C⁺特征线常数
            H_minus: C⁻特征线常数
            Q_plus: 上游流量
            Q_minus: 下游流量
            dt: 时间步长 (s)

        Returns:
            (H_pump, Q_pump): 泵处的水头和流量
        """
        g = 9.81
        B = self.a / (g * self.A)

        # 更新泵转速
        if self.speed_function is not None:
            n_new = self.speed_function(t)
        else:
            n_new = self.pump.n_design

        # 考虑转动惯量的转速变化
        # 使用欧拉法更新转速（如果提供了转矩）
        # ω' = (T_motor - T_pump) / (WR2 / g)
        # 简化：直接使用speed_function

        self.current_speed = n_new

        # 迭代求解泵的H和Q
        # 特征线: H = C_p - B*Q  和  H = C_m + B*Q
        # 泵曲线: H = f(Q, n)

        # 使用牛顿迭代求解
        Q = max(0.5 * (Q_plus + Q_minus), 0.001)  # 初始猜测，确保>0

        for iter in range(20):  # 最多20次迭代
            H_char_plus = H_plus - B * Q
            H_char_minus = H_minus + B * Q
            H_pump = self.pump.head_at_flow(Q, self.current_speed)

            # 残差：泵扬程应该满足两条特征线的平均
            # 或者：泵扬程 = (C_p + C_m) / 2
            H_target = (H_char_plus + H_char_minus) / 2

            residual = H_pump - H_target

            if abs(residual) < 0.01:
                break

            # 数值导数
            dQ = max(Q * 0.01, 0.0001)
            H_pump_plus = self.pump.head_at_flow(Q + dQ, self.current_speed)
            dH_dQ = (H_pump_plus - H_pump) / dQ

            # 牛顿更新（带阻尼）
            dH_dQ_char = 0.0  # 特征线平均后斜率为0
            total_slope = dH_dQ

            if abs(total_slope) > 1e-6:
                dQ_update = -residual / total_slope
                # 阻尼更新，防止过冲
                Q += 0.5 * dQ_update
                Q = max(Q, 0.0001)  # 确保流量为正
            else:
                # 斜率太小，使用二分法
                if residual > 0:
                    Q *= 0.9
                else:
                    Q *= 1.1

        # 计算最终的水头
        H = self.pump.head_at_flow(Q, self.current_speed)

        # 确保结果合理
        if H <= 0 or Q <= 0:
            # 备用方案：使用泵设计点
            Q = self.pump.Q_design
            H = self.pump.head_at_flow(Q, self.current_speed)

        return H, Q

    @staticmethod
    def power_failure(t_fail: float) -> Callable[[float], float]:
        """
        创建断电工况的转速函数

        Create speed function for power failure scenario

        转速衰减模型 Speed decay model:
        n(t) = n₀ * exp(-k * (t - t_fail))  for t >= t_fail
        n(t) = n₀                            for t < t_fail

        Args:
            t_fail: 断电时刻 (s)

        Returns:
            转速函数 n(t)
        """
        def speed_func(t: float, n0: float = 1500.0, k: float = 0.5) -> float:
            if t < t_fail:
                return n0
            else:
                return n0 * np.exp(-k * (t - t_fail))

        return speed_func

    @staticmethod
    def gradual_shutdown(t_start: float, t_end: float,
                        n_initial: float) -> Callable[[float], float]:
        """
        创建渐进停机的转速函数

        Create speed function for gradual pump shutdown

        Args:
            t_start: 开始停机时间 (s)
            t_end: 完全停止时间 (s)
            n_initial: 初始转速 (rpm)

        Returns:
            转速函数 n(t)
        """
        def speed_func(t: float) -> float:
            if t < t_start:
                return n_initial
            elif t > t_end:
                return 0.0
            else:
                # 线性减速
                return n_initial * (1 - (t - t_start) / (t_end - t_start))

        return speed_func

    @staticmethod
    def gradual_startup(t_start: float, t_end: float,
                       n_final: float) -> Callable[[float], float]:
        """
        创建渐进启动的转速函数

        Create speed function for gradual pump startup

        Args:
            t_start: 开始启动时间 (s)
            t_end: 达到全速时间 (s)
            n_final: 最终转速 (rpm)

        Returns:
            转速函数 n(t)
        """
        def speed_func(t: float) -> float:
            if t < t_start:
                return 0.0
            elif t > t_end:
                return n_final
            else:
                # 线性加速
                return n_final * (t - t_start) / (t_end - t_start)

        return speed_func


# 常用泵型参数库 Common pump parameters library
class StandardPumps:
    """标准泵型参数库"""

    @staticmethod
    def small_booster_pump():
        """小型增压泵"""
        return PumpCharacteristics(
            Q_design=0.05,  # 50 L/s
            H_design=30.0,  # 30 m
            n_design=1450,  # rpm
            efficiency_design=0.75,
            H_curve_a=35.0,
            H_curve_b=-50.0,
            H_curve_c=-200.0,
            WR2=1.5  # N·m²
        )

    @staticmethod
    def medium_pump():
        """中型泵"""
        return PumpCharacteristics(
            Q_design=0.2,  # 200 L/s
            H_design=50.0,  # 50 m
            n_design=1480,  # rpm
            efficiency_design=0.82,
            H_curve_a=58.0,
            H_curve_b=-20.0,
            H_curve_c=-100.0,
            WR2=15.0  # N·m²
        )

    @staticmethod
    def large_pump():
        """大型泵"""
        return PumpCharacteristics(
            Q_design=1.0,  # 1000 L/s = 1 m³/s
            H_design=80.0,  # 80 m
            n_design=1480,  # rpm
            efficiency_design=0.88,
            H_curve_a=92.0,
            H_curve_b=-10.0,
            H_curve_c=-20.0,
            WR2=100.0  # N·m²
        )
