#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
有压管道模块 Pressurized Pipe Module

实现有压管道的水力计算，包括：
- Darcy-Weisbach 公式
- Hazen-Williams 公式
- Colebrook-White 摩阻系数迭代
- 局部损失
- 流量-水头损失双向计算

作者: HydroClaude Team
日期: 2025-10-30
版本: 1.0.0
"""

import numpy as np
from typing import Optional, Dict, Literal


class PressurePipe:
    """
    有压管道类 - Pressurized Pipe

    支持功能:
    1. 摩阻系数计算（Colebrook-White公式）
    2. 水头损失计算（Darcy-Weisbach或Hazen-Williams）
    3. 流量反算（已知水头损失求流量）
    4. 雷诺数计算
    5. 流态判断（层流/湍流）

    应用场景:
    - 城市供水管网
    - 长距离输水管道
    - 工业管道系统
    - 明满流转换管道
    """

    def __init__(
        self,
        pipe_id: str,
        diameter: float,
        length: float,
        roughness: float,
        formula: Literal["darcy", "hazen"] = "darcy",
        K_minor: float = 0.0,
        description: str = ""
    ):
        """
        初始化有压管道

        Args:
            pipe_id: 管道标识
            diameter: 管道内径 (m)，必须 > 0
            length: 管道长度 (m)，必须 > 0
            roughness: 绝对粗糙度 (m)，用于Darcy公式
                典型值：
                - 新铸铁管: 0.00026 m
                - 旧铸铁管: 0.0015 m
                - 混凝土管: 0.0003-0.003 m
                - PVC管: 0.000015 m
                - 钢管: 0.000046 m
            formula: 水头损失计算公式
                - 'darcy': Darcy-Weisbach公式（推荐）
                - 'hazen': Hazen-Williams公式
            K_minor: 局部损失系数之和（无量纲）
                包括：弯头、阀门、异径管等
            description: 管道描述信息

        Raises:
            ValueError: 如果参数不满足物理约束
        """
        # 参数验证
        if diameter <= 0:
            raise ValueError(f"管径必须 > 0，当前值: {diameter}")
        if length <= 0:
            raise ValueError(f"管道长度必须 > 0，当前值: {length}")
        if roughness < 0:
            raise ValueError(f"粗糙度必须 >= 0，当前值: {roughness}")
        if K_minor < 0:
            raise ValueError(f"局部损失系数必须 >= 0，当前值: {K_minor}")
        if formula not in ["darcy", "hazen"]:
            raise ValueError(f"公式类型必须为 'darcy' 或 'hazen'，当前值: {formula}")

        self.pipe_id = pipe_id
        self.D = float(diameter)
        self.L = float(length)
        self.epsilon = float(roughness)
        self.formula = formula
        self.K_minor = float(K_minor)
        self.description = description

        # 计算断面积
        self.A = np.pi * (self.D / 2.0)**2

        # 计算相对粗糙度
        self.relative_roughness = self.epsilon / self.D

    def reynolds_number(self, Q: float, nu: float = 1.0e-6) -> float:
        """
        计算雷诺数 Reynolds Number

        公式: Re = V*D/ν = (4*Q)/(π*D*ν)

        Args:
            Q: 流量 (m³/s)
            nu: 运动粘度 (m²/s)
                默认 1.0e-6 (20°C清水)

        Returns:
            雷诺数（无量纲）
        """
        if abs(Q) < 1e-12:
            return 0.0

        V = abs(Q) / self.A
        Re = V * self.D / nu

        return Re

    def friction_factor_laminar(self, Re: float) -> float:
        """
        层流摩阻系数计算

        公式: f = 64 / Re

        适用条件: Re < 2000

        Args:
            Re: 雷诺数

        Returns:
            摩阻系数 f
        """
        if Re <= 0:
            return 0.0

        return 64.0 / Re

    def friction_factor_colebrook(
        self,
        Q: float,
        nu: float = 1.0e-6,
        max_iter: int = 10,
        tol: float = 1e-6
    ) -> float:
        """
        Colebrook-White公式计算湍流摩阻系数

        隐式方程:
        1/√f = -2*log₁₀(ε/(3.7*D) + 2.51/(Re*√f))

        采用迭代求解:
        1. 使用Swamee-Jain显式公式作为初值
        2. 迭代求解Colebrook方程

        Args:
            Q: 流量 (m³/s)
            nu: 运动粘度 (m²/s)
            max_iter: 最大迭代次数
            tol: 收敛容差

        Returns:
            Darcy-Weisbach摩阻系数 f
        """
        Re = self.reynolds_number(Q, nu)

        # 层流
        if Re < 2000:
            return self.friction_factor_laminar(Re)

        # 湍流: 使用Swamee-Jain公式作为初值
        # f = 0.25 / [log₁₀(ε/(3.7*D) + 5.74/Re^0.9)]²
        rel_rough = self.relative_roughness

        if rel_rough == 0:
            # 光滑管: f = 0.316 / Re^0.25 (Blasius公式)
            return 0.316 / Re**0.25

        # Swamee-Jain初值
        f = 0.25 / (np.log10(rel_rough/3.7 + 5.74/Re**0.9))**2

        # Colebrook迭代
        for _ in range(max_iter):
            # Colebrook公式:
            # 1/√f = -2*log₁₀(ε/(3.7*D) + 2.51/(Re*√f))
            sqrt_f = np.sqrt(f)
            f_new = 1.0 / (-2.0 * np.log10(rel_rough/3.7 + 2.51/(Re*sqrt_f)))**2

            # 检查收敛
            if abs(f_new - f) < tol:
                return f_new

            f = f_new

        # 未收敛时返回当前值
        return f

    def head_loss_darcy(
        self,
        Q: float,
        nu: float = 1.0e-6,
        include_minor: bool = True
    ) -> float:
        """
        Darcy-Weisbach公式计算水头损失

        沿程损失:
        h_f = f * (L/D) * (V²/2g)

        局部损失:
        h_m = K * (V²/2g)

        总损失:
        h_total = h_f + h_m

        Args:
            Q: 流量 (m³/s)
            nu: 运动粘度 (m²/s)
            include_minor: 是否包含局部损失

        Returns:
            总水头损失 (m)
        """
        if abs(Q) < 1e-12:
            return 0.0

        g = 9.81  # m/s²
        V = abs(Q) / self.A

        # 计算摩阻系数
        f = self.friction_factor_colebrook(Q, nu)

        # 沿程损失
        h_friction = f * (self.L / self.D) * (V**2 / (2*g))

        # 局部损失
        h_minor = 0.0
        if include_minor and self.K_minor > 0:
            h_minor = self.K_minor * (V**2 / (2*g))

        return h_friction + h_minor

    def head_loss_hazen(
        self,
        Q: float,
        C: float = 130.0,
        include_minor: bool = True
    ) -> float:
        """
        Hazen-Williams公式计算水头损失

        公式 (SI单位):
        h_f = 10.67 * L * Q^1.852 / (C^1.852 * D^4.87)

        Args:
            Q: 流量 (m³/s)
            C: Hazen-Williams系数（无量纲）
                典型值：
                - 新铸铁管: 130
                - 旧铸铁管: 100
                - 混凝土管: 120-140
                - PVC管: 150
                - 钢管新: 140
                - 钢管旧: 110
            include_minor: 是否包含局部损失

        Returns:
            总水头损失 (m)
        """
        if abs(Q) < 1e-12:
            return 0.0

        # Hazen-Williams公式（SI单位）
        h_friction = 10.67 * self.L * (abs(Q)**1.852) / (C**1.852 * self.D**4.87)

        # 局部损失（使用简化公式）
        h_minor = 0.0
        if include_minor and self.K_minor > 0:
            g = 9.81
            V = abs(Q) / self.A
            h_minor = self.K_minor * (V**2 / (2*g))

        return h_friction + h_minor

    def head_loss(self, Q: float, **kwargs) -> float:
        """
        计算水头损失（根据公式类型自动选择）

        Args:
            Q: 流量 (m³/s)
            **kwargs: 其他参数
                - nu: 运动粘度 (m²/s)，用于Darcy公式
                - C: Hazen-Williams系数，用于Hazen公式
                - include_minor: 是否包含局部损失

        Returns:
            水头损失 (m)
        """
        if self.formula == "darcy":
            nu = kwargs.get('nu', 1.0e-6)
            include_minor = kwargs.get('include_minor', True)
            return self.head_loss_darcy(Q, nu, include_minor)
        else:  # hazen
            C = kwargs.get('C', 130.0)
            include_minor = kwargs.get('include_minor', True)
            return self.head_loss_hazen(Q, C, include_minor)

    def flow_from_head_loss(
        self,
        h_loss: float,
        tol: float = 1e-6,
        max_iter: int = 50,
        **kwargs
    ) -> float:
        """
        根据水头损失反算流量（牛顿法迭代）

        求解方程: h_loss = f(Q)

        Args:
            h_loss: 给定水头损失 (m)
            tol: 收敛容差 (m)
            max_iter: 最大迭代次数
            **kwargs: 传递给head_loss的其他参数

        Returns:
            流量 (m³/s)

        Raises:
            RuntimeError: 如果迭代不收敛
        """
        if h_loss <= 0:
            return 0.0

        # 初值估计（假设湍流粗糙管）
        # h ≈ k*Q² => Q ≈ √(h/k)
        # k ≈ 8*f*L/(π²*D⁵*g), 假设 f ≈ 0.02
        g = 9.81
        f_est = 0.02
        k = 8 * f_est * self.L / (np.pi**2 * self.D**5 * g)
        Q = np.sqrt(h_loss / k) if k > 0 else 1.0

        # 牛顿法迭代
        for i in range(max_iter):
            h_calc = self.head_loss(Q, **kwargs)
            residual = h_calc - h_loss

            if abs(residual) < tol:
                return Q

            # 数值导数 dh/dQ
            dQ = max(Q * 1e-6, 1e-9)
            h_plus = self.head_loss(Q + dQ, **kwargs)
            dh_dQ = (h_plus - h_calc) / dQ

            if abs(dh_dQ) < 1e-12:
                # 导数太小，调整步长
                Q *= 1.1
                continue

            # 牛顿更新
            Q_new = Q - residual / dh_dQ

            # 确保正值
            if Q_new <= 0:
                Q_new = Q * 0.5
            elif Q_new > 10 * Q:  # 限制步长
                Q_new = Q * 2.0

            Q = Q_new

        raise RuntimeError(
            f"流量反算未收敛: h_loss={h_loss:.4f}m, "
            f"最后Q={Q:.6f}m³/s, 残差={residual:.6f}m"
        )

    def properties(self, Q: float, **kwargs) -> Dict[str, float]:
        """
        计算管道所有水力属性

        Args:
            Q: 流量 (m³/s)
            **kwargs: 传递给head_loss的其他参数

        Returns:
            属性字典，包含:
            - Q: 流量 (m³/s)
            - V: 流速 (m/s)
            - Re: 雷诺数
            - f: 摩阻系数
            - h_loss: 水头损失 (m)
            - regime: 流态 ('laminar' or 'turbulent')
        """
        V = abs(Q) / self.A if abs(Q) > 1e-12 else 0.0
        nu = kwargs.get('nu', 1.0e-6)
        Re = self.reynolds_number(Q, nu)

        if self.formula == "darcy":
            f = self.friction_factor_colebrook(Q, nu)
        else:
            # Hazen公式没有显式摩阻系数，用等效值
            f = np.nan

        h_loss = self.head_loss(Q, **kwargs)

        regime = 'laminar' if Re < 2000 else 'turbulent'

        return {
            'Q': Q,
            'V': V,
            'Re': Re,
            'f': f,
            'h_loss': h_loss,
            'regime': regime
        }

    def __repr__(self) -> str:
        """字符串表示"""
        return (
            f"PressurePipe(id='{self.pipe_id}', D={self.D:.3f}m, "
            f"L={self.L:.1f}m, ε={self.epsilon:.6f}m, "
            f"formula='{self.formula}')"
        )


def create_pressure_pipe(
    pipe_id: str,
    diameter: float,
    length: float,
    material: str = "cast_iron",
    formula: str = "darcy",
    K_minor: float = 0.0
) -> PressurePipe:
    """
    便捷创建管道（根据材料自动设置粗糙度）

    Args:
        pipe_id: 管道ID
        diameter: 管径 (m)
        length: 长度 (m)
        material: 材料类型，支持：
            - 'cast_iron_new': 新铸铁管 (ε=0.00026m)
            - 'cast_iron_old': 旧铸铁管 (ε=0.0015m)
            - 'concrete': 混凝土管 (ε=0.001m)
            - 'pvc': PVC管 (ε=0.000015m)
            - 'steel_new': 新钢管 (ε=0.000046m)
            - 'steel_old': 旧钢管 (ε=0.0003m)
        formula: 'darcy' 或 'hazen'
        K_minor: 局部损失系数

    Returns:
        PressurePipe实例

    Raises:
        ValueError: 如果材料类型不支持
    """
    roughness_db = {
        'cast_iron_new': 0.00026,
        'cast_iron_old': 0.0015,
        'cast_iron': 0.00026,  # 别名，默认新管
        'concrete': 0.001,
        'pvc': 0.000015,
        'steel_new': 0.000046,
        'steel_old': 0.0003,
        'steel': 0.000046,  # 别名，默认新管
        'smooth': 0.000001  # 光滑管
    }

    if material not in roughness_db:
        raise ValueError(
            f"不支持的材料类型: {material}\n"
            f"支持的类型: {list(roughness_db.keys())}"
        )

    epsilon = roughness_db[material]

    return PressurePipe(
        pipe_id=pipe_id,
        diameter=diameter,
        length=length,
        roughness=epsilon,
        formula=formula,
        K_minor=K_minor,
        description=f"{material}管道"
    )


# Hazen-Williams系数数据库
HAZEN_WILLIAMS_C = {
    'cast_iron_new': 130,
    'cast_iron_old': 100,
    'cast_iron': 130,
    'concrete_good': 140,
    'concrete_average': 120,
    'concrete_poor': 100,
    'concrete': 120,
    'pvc': 150,
    'steel_new': 140,
    'steel_old': 110,
    'steel': 140,
    'smooth': 150
}


# 典型局部损失系数
MINOR_LOSS_COEFFICIENTS = {
    # 弯头 Elbows
    'elbow_90_smooth': 0.3,
    'elbow_90_threaded': 1.5,
    'elbow_45_smooth': 0.2,
    'elbow_45_threaded': 0.4,

    # 三通 Tees
    'tee_through': 0.4,
    'tee_branch': 1.0,

    # 阀门 Valves (fully open)
    'gate_valve': 0.15,
    'globe_valve': 10.0,
    'ball_valve': 0.05,
    'check_valve': 2.0,
    'butterfly_valve': 0.3,

    # 管道入口/出口 Entrance/Exit
    'entrance_sharp': 0.5,
    'entrance_rounded': 0.04,
    'exit': 1.0,

    # 扩大/收缩 Expansion/Contraction
    'sudden_expansion': 1.0,  # (1 - A1/A2)²
    'sudden_contraction': 0.5,  # (1 - A2/A1)²
    'gradual_expansion': 0.3,
    'gradual_contraction': 0.1
}
