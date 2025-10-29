#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
特征线方法边界条件（Characteristic-Based Boundary Conditions）

基于Riemann不变量和特征线理论的边界条件实现，用于处理：
- 临界流边界条件（Critical Flow BC）
- 急流边界条件（Supercritical Flow BC）
- 缓流边界条件（Subcritical Flow BC）
- 非反射边界条件（Non-reflecting BC）

理论基础：
- 浅水方程的特征线理论
- Riemann不变量
- 自动流态识别（基于Froude数）

参考文献：
- LeVeque (2002): Finite Volume Methods for Hyperbolic Problems
- Toro (2001): Shock-Capturing Methods for Free-Surface Shallow Flows
- Chow (1959): Open-Channel Hydraulics

作者: HydroClaude Team
日期: 2025-10-29
"""

import numpy as np
from typing import Tuple, Optional, Callable
from enum import Enum


class FlowRegime(Enum):
    """流态类型"""
    SUBCRITICAL = "subcritical"    # 缓流 (Fr < 1)
    CRITICAL = "critical"           # 临界流 (Fr ≈ 1)
    SUPERCRITICAL = "supercritical" # 急流 (Fr > 1)


class BoundaryConditionType(Enum):
    """边界条件类型"""
    FIXED_DEPTH = "h"              # 固定水深
    FIXED_DISCHARGE = "Q"          # 固定流量
    CRITICAL_DEPTH = "critical"    # 临界水深
    NORMAL_DEPTH = "normal"        # 正常水深
    TRANSMISSIVE = "transmissive"  # 透射边界（非反射）
    RIEMANN = "riemann"            # Riemann不变量


class CharacteristicBC:
    """
    特征线方法边界条件

    根据流态（Froude数）自动选择合适的边界条件处理方法：

    缓流（Fr < 1）:
    - 上游: 1个特征线进入 → 需要指定1个物理量
    - 下游: 1个特征线进入 → 需要指定1个物理量

    急流（Fr > 1）:
    - 上游: 2个特征线进入 → 需要指定2个物理量
    - 下游: 0个特征线进入 → 完全外推

    临界流（Fr ≈ 1）:
    - 特殊处理，使用临界流条件
    """

    def __init__(self, g: float = 9.81):
        """
        初始化边界条件处理器

        参数:
            g: 重力加速度 (m/s²)
        """
        self.g = g
        self.critical_threshold = 0.05  # Fr在[1-δ, 1+δ]内视为临界流

    def compute_froude_number(
        self,
        h: float,
        u: float,
        g: Optional[float] = None
    ) -> float:
        """
        计算Froude数

        Fr = u / sqrt(g*h)

        参数:
            h: 水深 (m)
            u: 流速 (m/s)
            g: 重力加速度 (m/s²)

        返回:
            Froude数
        """
        if g is None:
            g = self.g

        if h < 1e-10:
            return 0.0

        return abs(u) / np.sqrt(g * h)

    def identify_flow_regime(
        self,
        h: float,
        u: float
    ) -> FlowRegime:
        """
        识别流态

        参数:
            h: 水深 (m)
            u: 流速 (m/s)

        返回:
            流态类型
        """
        Fr = self.compute_froude_number(h, u)

        if abs(Fr - 1.0) < self.critical_threshold:
            return FlowRegime.CRITICAL
        elif Fr < 1.0:
            return FlowRegime.SUBCRITICAL
        else:
            return FlowRegime.SUPERCRITICAL

    def compute_riemann_invariants(
        self,
        h: float,
        u: float
    ) -> Tuple[float, float]:
        """
        计算Riemann不变量

        浅水方程的Riemann不变量：
        R+ = u + 2*sqrt(g*h)  (沿C+特征线不变)
        R- = u - 2*sqrt(g*h)  (沿C-特征线不变)

        特征速度：
        λ+ = u + sqrt(g*h)
        λ- = u - sqrt(g*h)

        参数:
            h: 水深 (m)
            u: 流速 (m/s)

        返回:
            (R+, R-) Riemann不变量
        """
        c = np.sqrt(self.g * h)  # 波速
        R_plus = u + 2.0 * c
        R_minus = u - 2.0 * c

        return R_plus, R_minus

    def recover_from_riemann_invariants(
        self,
        R_plus: float,
        R_minus: float
    ) -> Tuple[float, float]:
        """
        从Riemann不变量恢复物理量

        h = ((R+ - R-) / 4)² / g
        u = (R+ + R-) / 2

        参数:
            R_plus: R+ Riemann不变量
            R_minus: R- Riemann不变量

        返回:
            (h, u) 水深和流速
        """
        u = 0.5 * (R_plus + R_minus)
        c = 0.25 * (R_plus - R_minus)
        h = (c * c) / self.g

        return h, u

    def apply_subcritical_inlet(
        self,
        h_ghost: float,
        u_ghost: float,
        h_interior: float,
        u_interior: float,
        bc_value: float,
        bc_type: str = 'Q',
        B: float = 1.0
    ) -> Tuple[float, float]:
        """
        缓流入口边界条件（左边界，上游）

        Fr < 1时：
        - C+ (λ+ = u + c > 0): 特征线从内部流向边界 → 使用内部信息
        - C- (λ- = u - c < 0): 特征线从边界流向内部 → 使用边界条件

        因此需要指定1个物理量（通常是Q或h）

        参数:
            h_ghost: 虚拟单元水深 (m) - 将被更新
            u_ghost: 虚拟单元流速 (m/s) - 将被更新
            h_interior: 内部单元水深 (m)
            u_interior: 内部单元流速 (m/s)
            bc_value: 边界条件值
            bc_type: 边界条件类型 ('Q' 或 'h')
            B: 渠宽 (m)

        返回:
            (h_bc, u_bc) 边界处的水深和流速
        """
        # 从内部外推R+（沿C+特征线）
        R_plus_interior, _ = self.compute_riemann_invariants(h_interior, u_interior)

        if bc_type == 'Q':
            # 指定流量Q (m³/s)
            Q_bc = bc_value

            # 初始猜测
            h_bc = h_interior

            for _ in range(20):
                u_bc = Q_bc / (B * h_bc) if h_bc > 1e-10 else 0.0
                _, R_minus_bc = self.compute_riemann_invariants(h_bc, u_bc)

                # 使用R+_interior和R-_bc恢复
                h_new, u_new = self.recover_from_riemann_invariants(
                    R_plus_interior, R_minus_bc
                )

                # 更新猜测
                if abs(h_new - h_bc) < 1e-6:
                    break
                h_bc = 0.5 * (h_bc + h_new)

            u_bc = Q_bc / (B * h_bc) if h_bc > 1e-10 else 0.0

        elif bc_type == 'h':
            # 指定水深h
            h_bc = bc_value

            # 从h_bc计算R-
            # 但u_bc未知，需要迭代
            u_bc = u_interior  # 初始猜测

            for _ in range(20):
                _, R_minus_bc = self.compute_riemann_invariants(h_bc, u_bc)

                # 使用R+_interior和R-_bc恢复
                _, u_new = self.recover_from_riemann_invariants(
                    R_plus_interior, R_minus_bc
                )

                if abs(u_new - u_bc) < 1e-6:
                    break
                u_bc = 0.5 * (u_bc + u_new)

        else:
            raise ValueError(f"Unsupported bc_type: {bc_type}")

        return h_bc, u_bc

    def apply_subcritical_outlet(
        self,
        h_ghost: float,
        u_ghost: float,
        h_interior: float,
        u_interior: float,
        bc_value: float,
        bc_type: str = 'h',
        B: float = 1.0
    ) -> Tuple[float, float]:
        """
        缓流出口边界条件（右边界，下游）

        Fr < 1时：
        - C+ (λ+ = u + c > 0): 特征线从内部流向边界 → 使用内部信息
        - C- (λ- = u - c < 0): 特征线从外部流向内部 → 使用边界条件

        因此需要指定1个物理量（通常是h）

        参数:
            h_ghost: 虚拟单元水深 (m)
            u_ghost: 虚拟单元流速 (m/s)
            h_interior: 内部单元水深 (m)
            u_interior: 内部单元流速 (m/s)
            bc_value: 边界条件值
            bc_type: 边界条件类型 ('h' 或 'Q')

        返回:
            (h_bc, u_bc) 边界处的水深和流速
        """
        # 从内部外推R+（沿C+特征线）
        R_plus_interior, _ = self.compute_riemann_invariants(h_interior, u_interior)

        if bc_type == 'h':
            # 指定水深h
            h_bc = bc_value

            # 迭代求解u_bc
            u_bc = u_interior  # 初始猜测

            for _ in range(20):
                _, R_minus_bc = self.compute_riemann_invariants(h_bc, u_bc)

                # 使用R+_interior和R-_bc恢复
                _, u_new = self.recover_from_riemann_invariants(
                    R_plus_interior, R_minus_bc
                )

                if abs(u_new - u_bc) < 1e-6:
                    break
                u_bc = 0.5 * (u_bc + u_new)

        elif bc_type == 'Q':
            # 指定流量Q
            Q_bc = bc_value

            # 迭代求解h_bc
            h_bc = h_interior

            for _ in range(20):
                u_bc = Q_bc / (B * h_bc) if h_bc > 1e-10 else 0.0
                _, R_minus_bc = self.compute_riemann_invariants(h_bc, u_bc)

                h_new, _ = self.recover_from_riemann_invariants(
                    R_plus_interior, R_minus_bc
                )

                if abs(h_new - h_bc) < 1e-6:
                    break
                h_bc = 0.5 * (h_bc + h_new)

            u_bc = Q_bc / (B * h_bc) if h_bc > 1e-10 else 0.0

        else:
            raise ValueError(f"Unsupported bc_type: {bc_type}")

        return h_bc, u_bc

    def apply_supercritical_inlet(
        self,
        h_bc_value: float,
        Q_bc_value: float,
        B: float = 1.0
    ) -> Tuple[float, float]:
        """
        急流入口边界条件（左边界，上游）

        Fr > 1时：
        - C+ (λ+ = u + c > 0): 特征线从内部流向边界
        - C- (λ- = u - c > 0): 特征线从内部流向边界

        两条特征线都从内部流向边界，因此需要指定2个物理量（h和Q）

        参数:
            h_bc_value: 指定的边界水深 (m)
            Q_bc_value: 指定的边界流量 (m³/s)
            B: 渠宽 (m)

        返回:
            (h_bc, u_bc) 边界处的水深和流速
        """
        h_bc = h_bc_value
        u_bc = Q_bc_value / (B * h_bc) if h_bc > 1e-10 else 0.0

        return h_bc, u_bc

    def apply_supercritical_outlet(
        self,
        h_interior: float,
        u_interior: float
    ) -> Tuple[float, float]:
        """
        急流出口边界条件（右边界，下游）

        Fr > 1时：
        - C+ (λ+ = u + c > 0): 特征线从内部流向边界
        - C- (λ- = u - c > 0): 特征线从内部流向边界

        所有信息都从内部传出，因此完全外推（零阶外推）

        参数:
            h_interior: 内部单元水深 (m)
            u_interior: 内部单元流速 (m/s)

        返回:
            (h_bc, u_bc) 边界处的水深和流速
        """
        # 零阶外推
        h_bc = h_interior
        u_bc = u_interior

        return h_bc, u_bc

    def apply_critical_depth_bc(
        self,
        Q: float,
        B: float,
        g: Optional[float] = None
    ) -> Tuple[float, float]:
        """
        临界水深边界条件

        临界流条件：Fr = 1
        即 u / sqrt(g*h) = 1

        结合连续性方程：Q = u * h * B

        可得：h_c = (Q²/(g*B²))^(1/3)

        参数:
            Q: 流量 (m³/s)
            B: 渠宽 (m)
            g: 重力加速度 (m/s²)

        返回:
            (h_c, u_c) 临界水深和流速
        """
        if g is None:
            g = self.g

        # 临界水深公式
        h_c = (Q**2 / (g * B**2))**(1.0/3.0)

        # 临界流速
        u_c = Q / (B * h_c) if h_c > 1e-10 else 0.0

        return h_c, u_c

    def apply_transmissive_bc(
        self,
        h_interior: float,
        u_interior: float,
        h_prev: float,
        u_prev: float,
        dt: float,
        dx: float
    ) -> Tuple[float, float]:
        """
        透射边界条件（非反射边界）

        允许波动自由通过边界而不反射
        使用一阶外推公式：

        ∂h/∂t + c * ∂h/∂x = 0

        其中 c = u + sqrt(g*h) 是波速

        参数:
            h_interior: 内部单元水深 (m)
            u_interior: 内部单元流速 (m/s)
            h_prev: 上一时刻边界水深 (m)
            u_prev: 上一时刻边界流速 (m/s)
            dt: 时间步长 (s)
            dx: 空间步长 (m)

        返回:
            (h_bc, u_bc) 边界处的水深和流速
        """
        # 波速
        c = u_interior + np.sqrt(self.g * h_interior)

        # 一阶外推
        if abs(c) > 1e-10:
            h_bc = h_prev - (c * dt / dx) * (h_interior - h_prev)
            u_bc = u_prev - (c * dt / dx) * (u_interior - u_prev)
        else:
            h_bc = h_interior
            u_bc = u_interior

        # 确保物理合理性
        h_bc = max(h_bc, 1e-10)

        return h_bc, u_bc


def test_characteristic_bc():
    """测试特征线边界条件"""
    print("="*80)
    print("特征线边界条件测试")
    print("="*80)

    bc = CharacteristicBC(g=9.81)

    # 测试1: Froude数计算
    print("\n测试1: Froude数计算")
    h = 2.0
    u = 3.0
    Fr = bc.compute_froude_number(h, u)
    print(f"h = {h} m, u = {u} m/s")
    print(f"Fr = {Fr:.3f}")
    print(f"流态: {bc.identify_flow_regime(h, u).value}")

    # 测试2: Riemann不变量
    print("\n测试2: Riemann不变量")
    R_plus, R_minus = bc.compute_riemann_invariants(h, u)
    print(f"R+ = {R_plus:.3f}")
    print(f"R- = {R_minus:.3f}")

    h_recovered, u_recovered = bc.recover_from_riemann_invariants(R_plus, R_minus)
    print(f"恢复: h = {h_recovered:.3f} m (误差: {abs(h_recovered-h)*100:.6f}%)")
    print(f"恢复: u = {u_recovered:.3f} m/s (误差: {abs(u_recovered-u)*100:.6f}%)")

    # 测试3: 缓流入口BC
    print("\n测试3: 缓流入口边界条件")
    h_interior = 2.0
    u_interior = 1.0  # Fr = 0.23 < 1
    Q_bc = 30.0  # 指定流量
    B = 10.0

    h_bc, u_bc = bc.apply_subcritical_inlet(
        None, None, h_interior, u_interior, Q_bc, bc_type='Q', B=B
    )
    Fr_bc = bc.compute_froude_number(h_bc, u_bc)
    print(f"内部: h = {h_interior} m, u = {u_interior} m/s, Fr = {bc.compute_froude_number(h_interior, u_interior):.3f}")
    print(f"边界: h = {h_bc:.3f} m, u = {u_bc:.3f} m/s, Fr = {Fr_bc:.3f}")
    print(f"流量: Q = {u_bc * h_bc * B:.3f} m³/s (目标: {Q_bc} m³/s)")

    # 测试4: 临界水深BC
    print("\n测试4: 临界水深边界条件")
    Q = 20.0
    B = 10.0
    h_c, u_c = bc.apply_critical_depth_bc(Q, B)
    Fr_c = bc.compute_froude_number(h_c, u_c)
    print(f"临界水深: h_c = {h_c:.3f} m")
    print(f"临界流速: u_c = {u_c:.3f} m/s")
    print(f"Froude数: Fr = {Fr_c:.3f} (应≈1.0)")
    print(f"流量: Q = {u_c * h_c * B:.3f} m³/s")

    # 测试5: 急流边界
    print("\n测试5: 急流边界条件")
    h_super = 0.5
    Q_super = 20.0
    u_super = Q_super / (B * h_super)
    Fr_super = bc.compute_froude_number(h_super, u_super)
    print(f"急流入口: h = {h_super} m, u = {u_super:.3f} m/s, Fr = {Fr_super:.3f}")

    h_bc_super, u_bc_super = bc.apply_supercritical_inlet(h_super, Q_super, B)
    print(f"边界条件: h = {h_bc_super} m, u = {u_bc_super:.3f} m/s")

    print("\n" + "="*80)
    print("✅ 所有测试完成")
    print("="*80)


if __name__ == '__main__':
    test_characteristic_bc()
