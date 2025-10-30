#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
水锤MOC求解器 / Water Hammer MOC Solver

特征线法(Method of Characteristics)求解管道瞬变流

基本方程 / Governing Equations:
- 连续性: ∂H/∂t + (a²/gA) * ∂Q/∂x = 0
- 动量:   ∂Q/∂t + gA * ∂H/∂x + (f*Q*|Q|)/(2*D*A) = 0

特征线 / Characteristic Lines:
- C⁺: dx/dt = +a
- C⁻: dx/dt = -a

相容方程 / Compatibility Equations:
- C⁺: H_P + B*Q_P = H_A + B*Q_A - R*Q_A*|Q_A|
- C⁻: H_P - B*Q_P = H_B - B*Q_B + R*Q_B*|Q_B|

其中 / Where:
- B = a / (g*A)
- R = f*Δt / (2*D*A)

作者: HydroClaude Team
日期: 2025-10-30
"""

import numpy as np
from typing import Dict, Optional, Callable, Tuple
from dataclasses import dataclass


@dataclass
class WaterHammerBoundary:
    """
    水锤边界条件 / Water Hammer Boundary Condition

    边界类型 / Boundary Types:
    - 'reservoir': 恒定水头水库 / Constant head reservoir
    - 'valve': 阀门 / Valve
    - 'dead_end': 死端 / Dead end
    """

    bc_type: str
    value: Optional[float] = None  # For reservoir: H_reservoir; For valve: opening_ratio
    closure_function: Optional[Callable[[float], float]] = None  # τ(t), 阀门开度随时间变化


class WaterHammerMOCSolver:
    """
    特征线法(MOC)水锤求解器

    Method of Characteristics solver for water hammer analysis in pipelines.

    Attributes:
        L (float): 管道长度 / Pipe length (m)
        D (float): 管道直径 / Pipe diameter (m)
        A (float): 管道面积 / Pipe area (m²)
        f (float): 摩阻系数 / Friction factor
        a (float): 波速 / Wave speed (m/s)
        dx (float): 空间步长 / Spatial step (m)
        dt (float): 时间步长 / Time step (s)
        nx (int): 空间节点数 / Number of spatial nodes
        g (float): 重力加速度 / Gravitational acceleration (m/s²)

    Examples:
        >>> solver = WaterHammerMOCSolver(L=1000, D=0.5, f=0.02, wave_speed=1000)
        >>> solver.set_grid(nx=51)
        >>> bc_up = WaterHammerBoundary('reservoir', value=100.0)
        >>> bc_down = WaterHammerBoundary('valve', closure_function=lambda t: max(0, 1-t/2))
        >>> result = solver.solve_transient(Q0=0.5, H0_up=100, bc_upstream=bc_up,
        ...                                  bc_downstream=bc_down, duration=10.0)
    """

    def __init__(
        self,
        L: float,
        D: float,
        f: float,
        wave_speed: Optional[float] = None,
        K: float = 2.1e9,
        E: float = 2.0e11,
        e: float = 0.01,
        g: float = 9.81
    ):
        """
        初始化水锤求解器

        Initialize water hammer solver

        Args:
            L: 管道长度 / Pipe length (m)
            D: 管道直径 / Pipe diameter (m)
            f: Darcy-Weisbach摩阻系数 / Friction factor
            wave_speed: 波速 / Wave speed (m/s). 如果未提供，将根据K,E,e计算
            K: 液体体积弹性模量 / Bulk modulus of fluid (Pa), 默认2.1×10⁹ (水)
            E: 管材弹性模量 / Young's modulus of pipe (Pa), 默认2.0×10¹¹ (钢)
            e: 管壁厚度 / Wall thickness (m)
            g: 重力加速度 / Gravitational acceleration (m/s²)
        """
        self.L = L
        self.D = D
        self.A = np.pi * D**2 / 4.0
        self.f = f
        self.g = g

        # 计算波速 / Calculate wave speed
        if wave_speed is not None:
            self.a = wave_speed
        else:
            self.a = self.calculate_wave_speed(K, E, e)

        # 网格参数（待设置）/ Grid parameters (to be set)
        self.dx: Optional[float] = None
        self.dt: Optional[float] = None
        self.nx: Optional[int] = None

        # MOC系数 / MOC coefficients
        self.B: Optional[float] = None  # B = a / (g*A)
        self.R: Optional[float] = None  # R = f*dt / (2*D*A)

    def calculate_wave_speed(
        self,
        K: float = 2.1e9,
        E: float = 2.0e11,
        e: float = 0.01,
        rho: float = 1000.0
    ) -> float:
        """
        计算水锤波速 (Korteweg公式)

        Calculate wave speed using Korteweg formula

        a = √(K/ρ) / √(1 + (K*D)/(E*e))

        Args:
            K: 液体体积弹性模量 / Bulk modulus (Pa), 默认2.1×10⁹ (水)
            E: 管材弹性模量 / Young's modulus (Pa), 默认2.0×10¹¹ (钢)
            e: 管壁厚度 / Wall thickness (m)
            rho: 液体密度 / Fluid density (kg/m³)

        Returns:
            波速 / Wave speed (m/s)
        """
        c_fluid = np.sqrt(K / rho)  # 纯液体中的声速
        correction = 1.0 + (K * self.D) / (E * e)  # 管壁弹性修正
        a = c_fluid / np.sqrt(correction)
        return a

    def set_grid(self, nx: int, cfl: float = 1.0):
        """
        设置网格

        Set computational grid

        Args:
            nx: 空间节点数 / Number of spatial nodes
            cfl: CFL数 / CFL number (默认1.0，确保特征线准确)

        Raises:
            ValueError: 如果CFL条件违反
        """
        self.nx = nx
        self.dx = self.L / (nx - 1)

        # 根据CFL条件确定时间步长 / Determine dt from CFL condition
        # CFL = a * dt / dx <= 1
        self.dt = cfl * self.dx / self.a

        # 计算MOC系数 / Calculate MOC coefficients
        self.B = self.a / (self.g * self.A)
        self.R = self.f * self.dt / (2.0 * self.D * self.A)

        # 验证CFL / Verify CFL
        actual_cfl = self.a * self.dt / self.dx
        if actual_cfl > 1.01:  # 允许1%误差
            raise ValueError(
                f"违反CFL条件: CFL={actual_cfl:.3f} > 1.0. "
                f"请增加nx或减小cfl参数"
            )

    def solve_transient(
        self,
        Q0: float,
        H0_up: float,
        bc_upstream: WaterHammerBoundary,
        bc_downstream: WaterHammerBoundary,
        duration: float,
        friction_model: str = 'steady'
    ) -> Dict[str, np.ndarray]:
        """
        求解瞬变流过程

        Solve transient flow using MOC

        Args:
            Q0: 初始流量 / Initial flow rate (m³/s)
            H0_up: 上游初始水头 / Initial head at upstream (m)
            bc_upstream: 上游边界条件 / Upstream boundary condition
            bc_downstream: 下游边界条件 / Downstream boundary condition
            duration: 模拟时长 / Simulation duration (s)
            friction_model: 摩阻模型 / Friction model ('steady' or 'unsteady')

        Returns:
            结果字典 / Results dictionary:
            {
                't': 时间数组 (nt,) / Time array,
                'x': 空间坐标数组 (nx,) / Spatial coordinates,
                'Q': 流量场 (nt, nx) / Flow rate field,
                'H': 水头场 (nt, nx) / Head field,
                'V': 流速场 (nt, nx) / Velocity field,
                'p': 压力场 (nt, nx) / Pressure field (Pa)
            }
        """
        if self.nx is None or self.dt is None:
            raise RuntimeError("必须先调用set_grid()设置网格")

        # 时间步数 / Number of time steps
        nt = int(duration / self.dt) + 1
        t_array = np.linspace(0, duration, nt)
        x_array = np.linspace(0, self.L, self.nx)

        # 初始化场变量 / Initialize field variables
        Q = np.zeros((nt, self.nx))
        H = np.zeros((nt, self.nx))

        # 初始条件 / Initial conditions
        Q[0, :] = Q0

        # 初始水头分布（考虑沿程损失）/ Initial head distribution
        V0 = Q0 / self.A
        hf_per_length = self.f * V0**2 / (2.0 * self.g * self.D)
        for i in range(self.nx):
            H[0, i] = H0_up - hf_per_length * x_array[i]

        # 时间推进 / Time marching
        for n in range(nt - 1):
            t = t_array[n]

            # 1. 内部节点：使用MOC相容方程 / Interior nodes: MOC compatibility equations
            for i in range(1, self.nx - 1):
                # C+ 特征线从 i-1 来 / C+ from i-1
                Q_A = Q[n, i - 1]
                H_A = H[n, i - 1]
                CP = H_A + self.B * Q_A - self.R * Q_A * abs(Q_A)

                # C- 特征线从 i+1 来 / C- from i+1
                Q_B = Q[n, i + 1]
                H_B = H[n, i + 1]
                CM = H_B - self.B * Q_B + self.R * Q_B * abs(Q_B)

                # 求解 P 点 / Solve for point P
                # H_P + B*Q_P = CP
                # H_P - B*Q_P = CM
                H[n + 1, i] = 0.5 * (CP + CM)
                Q[n + 1, i] = (CP - CM) / (2.0 * self.B)

            # 2. 上游边界 / Upstream boundary (i=0)
            H[n + 1, 0], Q[n + 1, 0] = self._apply_upstream_bc(
                bc_upstream, t + self.dt, Q[n, 1], H[n, 1]
            )

            # 3. 下游边界 / Downstream boundary (i=nx-1)
            H[n + 1, -1], Q[n + 1, -1] = self._apply_downstream_bc(
                bc_downstream, t + self.dt, Q[n, -2], H[n, -2]
            )

        # 计算流速和压力 / Calculate velocity and pressure
        V = Q / self.A
        p = 1000.0 * self.g * H  # 假设基准面在管道底部

        return {
            't': t_array,
            'x': x_array,
            'Q': Q,
            'H': H,
            'V': V,
            'p': p
        }

    def _apply_upstream_bc(
        self,
        bc: WaterHammerBoundary,
        t: float,
        Q_next: float,
        H_next: float
    ) -> Tuple[float, float]:
        """
        应用上游边界条件

        Apply upstream boundary condition

        Args:
            bc: 边界条件 / Boundary condition
            t: 当前时间 / Current time (s)
            Q_next: 相邻节点流量 / Flow at adjacent node (m³/s)
            H_next: 相邻节点水头 / Head at adjacent node (m)

        Returns:
            (H_boundary, Q_boundary): 边界水头和流量 / Boundary head and flow
        """
        # C- 特征线方程 / C- characteristic from i=1
        CM = H_next - self.B * Q_next + self.R * Q_next * abs(Q_next)

        if bc.bc_type == 'reservoir':
            # 恒定水头 / Constant head
            H_b = bc.value
            Q_b = (H_b - CM) / self.B

        elif bc.bc_type == 'dead_end':
            # 死端：Q = 0 / Dead end: Q = 0
            Q_b = 0.0
            H_b = CM

        else:
            raise ValueError(f"未知的上游边界类型: {bc.bc_type}")

        return H_b, Q_b

    def _apply_downstream_bc(
        self,
        bc: WaterHammerBoundary,
        t: float,
        Q_prev: float,
        H_prev: float
    ) -> Tuple[float, float]:
        """
        应用下游边界条件

        Apply downstream boundary condition

        Args:
            bc: 边界条件 / Boundary condition
            t: 当前时间 / Current time (s)
            Q_prev: 相邻节点流量 / Flow at adjacent node (m³/s)
            H_prev: 相邻节点水头 / Head at adjacent node (m)

        Returns:
            (H_boundary, Q_boundary): 边界水头和流量 / Boundary head and flow
        """
        # C+ 特征线方程 / C+ characteristic from i=nx-2
        CP = H_prev + self.B * Q_prev - self.R * Q_prev * abs(Q_prev)

        if bc.bc_type == 'reservoir':
            # 恒定水头 / Constant head
            H_b = bc.value
            Q_b = (CP - H_b) / self.B

        elif bc.bc_type == 'valve':
            # 阀门边界 / Valve boundary
            if bc.closure_function is not None:
                tau = bc.closure_function(t)  # 阀门开度 / Valve opening ratio
            else:
                tau = bc.value if bc.value is not None else 1.0

            if tau < 1e-6:
                # 阀门完全关闭 / Valve fully closed
                Q_b = 0.0
                H_b = CP
            else:
                # 阀门流量方程（非线性）/ Valve flow equation (nonlinear)
                # Q = τ * K * √H，其中 K 是阀门系数
                # 联立 C+ 方程：H + B*Q = CP
                # 得到：H + B*τ*K*√H = CP
                # 令 y = √H，则 y² + B*τ*K*y - CP = 0

                # 估算阀门系数（基于初始条件）
                # K ≈ Q_prev / √H_prev
                K = abs(Q_prev) / max(np.sqrt(abs(H_prev)), 0.1) if H_prev > 0 else 0.1

                # 求解二次方程 y² + B*τ*K*y - CP = 0
                a_coeff = 1.0
                b_coeff = self.B * tau * K
                c_coeff = -CP

                discriminant = b_coeff**2 - 4 * a_coeff * c_coeff

                if discriminant >= 0:
                    y = (-b_coeff + np.sqrt(discriminant)) / (2 * a_coeff)
                    H_b = y**2
                    Q_b = tau * K * y
                else:
                    # 退化到线性模型
                    Q_b = tau * Q_prev
                    H_b = CP - self.B * Q_b

        elif bc.bc_type == 'dead_end':
            # 死端：Q = 0 / Dead end: Q = 0
            Q_b = 0.0
            H_b = CP

        else:
            raise ValueError(f"未知的下游边界类型: {bc.bc_type}")

        return H_b, Q_b

    def joukowsky_head_rise(self, V0: float) -> float:
        """
        Joukowsky公式计算最大压力升高

        Calculate maximum pressure rise using Joukowsky formula

        ΔH = a * ΔV / g

        Args:
            V0: 初始流速 / Initial velocity (m/s)

        Returns:
            最大水头升高 / Maximum head rise (m)
        """
        delta_H = self.a * V0 / self.g
        return delta_H

    def critical_closure_time(self) -> float:
        """
        计算临界关闭时间

        Calculate critical closure time for direct water hammer

        T_critical = 2L / a

        Returns:
            临界关闭时间 / Critical closure time (s)
        """
        T_critical = 2.0 * self.L / self.a
        return T_critical

    def max_pressure_estimate(self, V0: float, closure_time: float) -> float:
        """
        估算最大压力升高

        Estimate maximum pressure rise considering closure time

        Args:
            V0: 初始流速 / Initial velocity (m/s)
            closure_time: 阀门关闭时间 / Valve closure time (s)

        Returns:
            最大水头升高 / Maximum head rise (m)
        """
        delta_H_joukowsky = self.joukowsky_head_rise(V0)
        T_critical = self.critical_closure_time()

        if closure_time < T_critical:
            # 直接水锤 / Direct water hammer
            return delta_H_joukowsky
        else:
            # 间接水锤 / Indirect water hammer
            return delta_H_joukowsky * T_critical / closure_time
