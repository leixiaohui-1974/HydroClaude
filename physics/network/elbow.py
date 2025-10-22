#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
弯头 (Elbow)

弯头是管道系统中改变流动方向的配件，会产生局部损失。

常见类型：
- 90° 弯头
- 45° 弯头
- 任意角度弯头

弯头特性：
- 曲率半径: R/D（长半径 R/D≥1.5，短半径 R/D<1.5）
- 转角角度: θ (度)

局部损失系数经验公式：
    K = K_base * f(θ)

其中：
- K_base 取决于 R/D 比值
  - 长半径弯头 (R/D=1.5): K_base ≈ 0.2-0.3
  - 短半径弯头 (R/D=1.0): K_base ≈ 0.3-0.5
  - 尖角弯头 (R/D→0): K_base ≈ 1.0-1.5

- f(θ) 是角度修正因子
  - 90°: f = 1.0
  - 45°: f ≈ 0.4-0.5
  - 通用: f = sin²(θ/2) 或 f = (θ/90)^1.5

水头损失：
    h_loss = K * V² / (2g)

作者: Claude
日期: 2025-10-22
"""

import numpy as np
from typing import Optional


class Elbow:
    """
    弯头组件

    计算弯头的局部水头损失
    """

    def __init__(self, name: str, angle: float, diameter: float,
                 radius_ratio: float = 1.5,
                 base_loss_coefficient: Optional[float] = None):
        """
        初始化弯头

        Args:
            name: 弯头名称
            angle: 转角角度 (度)，如 90.0 或 45.0
            diameter: 管道直径 (m)
            radius_ratio: 曲率半径比 R/D (默认1.5为长半径)
            base_loss_coefficient: 基础损失系数 K_base
                                   如果为None，根据R/D自动计算
        """
        self.name = name
        self.angle = angle
        self.diameter = diameter
        self.radius_ratio = radius_ratio

        # 计算基础损失系数
        if base_loss_coefficient is not None:
            self.K_base = base_loss_coefficient
        else:
            self.K_base = self._calculate_base_loss_coefficient()

        # 计算总损失系数
        self.K = self._calculate_loss_coefficient()

    def _calculate_base_loss_coefficient(self) -> float:
        """
        根据曲率半径比计算基础损失系数

        经验公式（基于实验数据）：
        - R/D >= 1.5 (长半径): K_base = 0.2
        - R/D = 1.0 (短半径): K_base = 0.4
        - R/D < 1.0 (尖角): K_base = 1.0 + 0.5/(R/D)

        Returns:
            基础损失系数
        """
        R_D = self.radius_ratio

        if R_D >= 1.5:
            # 长半径弯头
            K_base = 0.2
        elif R_D >= 1.0:
            # 短半径弯头（线性插值）
            K_base = 0.2 + (1.0 - 0.2) * (1.5 - R_D) / (1.5 - 1.0)
            K_base = 0.4
        else:
            # 尖角弯头
            K_base = min(1.5, 1.0 + 0.5 / max(R_D, 0.1))

        return K_base

    def _calculate_loss_coefficient(self) -> float:
        """
        计算总损失系数（考虑转角）

        角度修正因子：
        - f(θ) = (θ/90)^1.5  (经验公式)
        - 或 f(θ) = sin²(θ/2)

        Returns:
            总损失系数
        """
        theta_rad = np.radians(self.angle)

        # 方法1: 幂次公式
        angle_factor_1 = (self.angle / 90.0) ** 1.5

        # 方法2: 三角函数公式
        angle_factor_2 = np.sin(theta_rad / 2.0) ** 2

        # 使用平均值（更稳健）
        angle_factor = (angle_factor_1 + angle_factor_2) / 2.0

        K = self.K_base * max(angle_factor, 0.1)  # 保证最小值

        return K

    def calculate_head_loss(self, velocity: float, g: float = 9.81) -> float:
        """
        计算水头损失

        h_loss = K * V² / (2g)

        Args:
            velocity: 管道流速 (m/s)
            g: 重力加速度 (m/s²)

        Returns:
            水头损失 (m)
        """
        h_loss = self.K * velocity**2 / (2.0 * g)
        return h_loss

    def calculate_pressure_drop(self, velocity: float, rho: float = 1000.0,
                               g: float = 9.81) -> float:
        """
        计算压降

        ΔP = ρ * g * h_loss

        Args:
            velocity: 管道流速 (m/s)
            rho: 流体密度 (kg/m³)
            g: 重力加速度 (m/s²)

        Returns:
            压降 (Pa)
        """
        h_loss = self.calculate_head_loss(velocity, g)
        delta_P = rho * g * h_loss
        return delta_P

    def calculate_derivatives(self, velocity: float, rho: float = 1000.0,
                             g: float = 9.81) -> float:
        """
        计算压降对流速的导数（用于牛顿迭代）

        ΔP = ρ * g * K * V² / (2g) = ρ * K * V² / 2
        dΔP/dV = ρ * K * V

        Args:
            velocity: 管道流速 (m/s)
            rho: 流体密度 (kg/m³)
            g: 重力加速度 (m/s²)

        Returns:
            导数 dΔP/dV (Pa·s/m)
        """
        dDP_dV = rho * self.K * velocity
        return dDP_dV

    def __repr__(self) -> str:
        return (f"Elbow(name='{self.name}', angle={self.angle}°, "
                f"D={self.diameter}m, R/D={self.radius_ratio:.1f}, K={self.K:.3f})")


def test_elbow():
    """测试弯头类"""
    print("=" * 80)
    print("弯头组件测试")
    print("=" * 80)
    print()

    # 测试1: 90度弯头（长半径 vs 短半径）
    print("【测试1】90° 弯头 - 长半径 vs 短半径")
    print("-" * 80)

    elbow_90_long = Elbow(
        name="Elbow-90-Long",
        angle=90.0,
        diameter=0.5,
        radius_ratio=1.5  # 长半径
    )

    elbow_90_short = Elbow(
        name="Elbow-90-Short",
        angle=90.0,
        diameter=0.5,
        radius_ratio=1.0  # 短半径
    )

    elbow_90_sharp = Elbow(
        name="Elbow-90-Sharp",
        angle=90.0,
        diameter=0.5,
        radius_ratio=0.3  # 尖角
    )

    print(f"长半径: {elbow_90_long}")
    print(f"短半径: {elbow_90_short}")
    print(f"尖角:   {elbow_90_sharp}")
    print()

    # 测试不同流速下的损失
    print("水头损失对比 (V = 3 m/s):")
    print(f"{'类型':<15} {'K系数':<12} {'水头损失(m)':<15} {'压降(kPa)':<15}")
    print("-" * 60)

    V_test = 3.0  # 流速 3 m/s
    for elbow in [elbow_90_long, elbow_90_short, elbow_90_sharp]:
        h_loss = elbow.calculate_head_loss(V_test)
        dp = elbow.calculate_pressure_drop(V_test) / 1000  # 转为kPa
        print(f"{elbow.name:<15} {elbow.K:<12.3f} {h_loss:<15.4f} {dp:<15.2f}")

    print()

    # 测试2: 不同角度的弯头
    print("【测试2】不同角度弯头 (长半径, R/D=1.5)")
    print("-" * 80)

    angles = [30, 45, 60, 90, 120, 180]
    print(f"{'角度(°)':<12} {'K系数':<12} {'水头损失(m)':<15} {'压降(kPa)':<15}")
    print("-" * 60)

    for angle in angles:
        elbow = Elbow(
            name=f"Elbow-{angle}",
            angle=angle,
            diameter=0.5,
            radius_ratio=1.5
        )
        h_loss = elbow.calculate_head_loss(V_test)
        dp = elbow.calculate_pressure_drop(V_test) / 1000
        print(f"{angle:<12} {elbow.K:<12.3f} {h_loss:<15.4f} {dp:<15.2f}")

    print()

    # 测试3: 导数验证
    print("【测试3】导数验证 (90°长半径弯头)")
    print("-" * 80)

    elbow_test = elbow_90_long
    V_test = 2.5

    # 解析导数
    dDP_dV_analytical = elbow_test.calculate_derivatives(V_test)

    # 数值导数
    eps = 1e-6
    DP0 = elbow_test.calculate_pressure_drop(V_test)
    DP1 = elbow_test.calculate_pressure_drop(V_test + eps)
    dDP_dV_numerical = (DP1 - DP0) / eps

    print(f"流速: V = {V_test} m/s")
    print(f"压降: ΔP = {DP0/1000:.3f} kPa")
    print()
    print(f"∂(ΔP)/∂V:")
    print(f"  解析导数: {dDP_dV_analytical:.3f} Pa·s/m")
    print(f"  数值导数: {dDP_dV_numerical:.3f} Pa·s/m")
    rel_error = abs(dDP_dV_analytical - dDP_dV_numerical) / abs(dDP_dV_numerical) * 100
    print(f"  相对误差: {rel_error:.6f}%")

    if rel_error < 0.001:
        print("  ✓ 导数验证通过！")
    else:
        print(f"  ✗ 导数误差较大")

    print()

    # 测试4: 流速-损失曲线
    print("【测试4】流速-损失关系 (90°长半径弯头)")
    print("-" * 80)

    velocities = np.linspace(0.5, 5.0, 10)
    print(f"{'流速(m/s)':<12} {'水头损失(m)':<15} {'压降(kPa)':<15}")
    print("-" * 45)

    for V in velocities:
        h_loss = elbow_90_long.calculate_head_loss(V)
        dp = elbow_90_long.calculate_pressure_drop(V) / 1000
        print(f"{V:<12.2f} {h_loss:<15.4f} {dp:<15.2f}")

    print()
    print("观察: 损失与流速平方成正比 (h ∝ V²)")
    print()

    print("=" * 80)
    print("测试完成！")
    print("=" * 80)


if __name__ == "__main__":
    test_elbow()
