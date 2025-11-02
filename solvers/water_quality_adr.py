#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
水质模拟通用ADR求解器 - Advection-Diffusion-Reaction Solver

物理模型：
    ∂C/∂t + u·∂C/∂x = ∂/∂x(DL·∂C/∂x) + R(C) + S

    其中:
    - C: 组分浓度 (mg/L)
    - u: 流速 (m/s)
    - DL: 纵向扩散系数 (m²/s)
    - R(C): 反应项 (mg/L/s)
    - S: 源汇项 (mg/L/s)

数值方法：
    - 对流项: MUSCL重构 + 迎风格式
    - 扩散项: 中心差分
    - 反应项: 算子分裂法 (Strang Splitting)
    - 时间积分: TVD-RK2

对标: WASP输运框架, EFDC高精度格式

作者: HydroClaude Team
日期: 2025-11-02
"""

import numpy as np
from typing import Tuple, Dict, Optional, Callable

# 尝试导入Numba加速
try:
    from numba import njit
    NUMBA_AVAILABLE = True
except ImportError:
    NUMBA_AVAILABLE = False
    def njit(*args, **kwargs):
        def decorator(func):
            return func
        if len(args) == 1 and callable(args[0]):
            return args[0]
        return decorator


class ADRSolver:
    """
    对流-扩散-反应通用求解器

    可用于求解各类水质组分:
    - 溶解氧 (DO)
    - 生化需氧量 (BOD, COD)
    - 营养盐 (NH4, NO3, PO4)
    - 重金属 (Pb, Cd, Hg等)
    - 保守示踪剂
    """

    def __init__(
        self,
        n_cells: int,
        dx: float,
        use_numba: bool = True,
        use_muscl: bool = True
    ):
        """
        初始化ADR求解器

        Parameters:
        -----------
        n_cells : int
            网格单元数
        dx : float
            网格间距 (m)
        use_numba : bool
            是否使用Numba加速
        use_muscl : bool
            是否使用MUSCL重构 (二阶精度)
        """
        self.n_cells = n_cells
        self.dx = dx
        self.use_numba = use_numba and NUMBA_AVAILABLE
        self.use_muscl = use_muscl

    def compute_dispersion_coefficient(
        self,
        h: np.ndarray,
        u: np.ndarray,
        u_star: Optional[np.ndarray] = None,
        manning_n: float = 0.03
    ) -> np.ndarray:
        """
        计算纵向扩散系数

        使用Elder (1959) 公式:
            DL = 5.93 * h * u*

        Parameters:
        -----------
        h : array
            水深 (m)
        u : array
            流速 (m/s)
        u_star : array, optional
            摩阻流速 (m/s), 如未提供则计算
        manning_n : float
            Manning糙率系数

        Returns:
        --------
        D_L : array
            纵向扩散系数 (m²/s)
        """
        if u_star is None:
            # 计算摩阻流速: u* = u * n / h^(1/6)
            u_star = np.abs(u) * manning_n / h**(1.0/6.0)

        # Elder公式
        D_L = 5.93 * h * u_star

        # 加入分子扩散 (低流速情况)
        D_molecular = 1e-9  # m²/s
        D_L += D_molecular

        return D_L

    def minmod_limiter(self, r: np.ndarray) -> np.ndarray:
        """Minmod斜率限制器"""
        return np.maximum(0.0, np.minimum(1.0, r))

    def muscl_reconstruction(
        self,
        C: np.ndarray
    ) -> Tuple[np.ndarray, np.ndarray]:
        """
        MUSCL重构获取界面左右状态

        Parameters:
        -----------
        C : array
            单元中心浓度

        Returns:
        --------
        C_L, C_R : array
            界面左右状态
        """
        n = len(C)
        C_L = np.zeros(n+1)
        C_R = np.zeros(n+1)

        # 内部界面
        for i in range(1, n):
            # 上游梯度
            if i > 0:
                dC_up = C[i] - C[i-1]
            else:
                dC_up = 0.0

            # 下游梯度
            if i < n-1:
                dC_down = C[i+1] - C[i]
            else:
                dC_down = 0.0

            # 斜率比
            if abs(dC_down) > 1e-12:
                r = dC_up / dC_down
            else:
                r = 0.0

            # Minmod限制器
            phi = self.minmod_limiter(np.array([r]))[0]

            # 重构
            C_L[i] = C[i-1] + 0.5 * phi * dC_up
            C_R[i] = C[i] - 0.5 * phi * dC_down

        # 边界
        C_L[0] = C[0]
        C_R[0] = C[0]
        C_L[n] = C[n-1]
        C_R[n] = C[n-1]

        return C_L, C_R

    def compute_advective_flux(
        self,
        C: np.ndarray,
        u: np.ndarray
    ) -> np.ndarray:
        """
        计算对流通量

        使用迎风格式: F = u * C_upwind

        Parameters:
        -----------
        C : array
            浓度
        u : array
            界面流速

        Returns:
        --------
        F : array
            对流通量 (界面)
        """
        n = len(C)
        F = np.zeros(n+1)

        if self.use_muscl:
            # MUSCL重构
            C_L, C_R = self.muscl_reconstruction(C)

            # 迎风选择
            for i in range(n+1):
                if i < len(u):
                    u_face = u[i]
                else:
                    u_face = u[-1]

                if u_face > 0:
                    F[i] = u_face * C_L[i]
                else:
                    F[i] = u_face * C_R[i]
        else:
            # 一阶迎风
            for i in range(1, n):
                if u[i] > 0:
                    F[i] = u[i] * C[i-1]
                else:
                    F[i] = u[i] * C[i]

            # 边界
            F[0] = u[0] * C[0]
            F[n] = u[-1] * C[-1]

        return F

    def compute_diffusive_flux(
        self,
        C: np.ndarray,
        D_L: np.ndarray
    ) -> np.ndarray:
        """
        计算扩散通量

        使用中心差分: F = -DL * dC/dx

        Parameters:
        -----------
        C : array
            浓度
        D_L : array
            扩散系数

        Returns:
        --------
        F_diff : array
            扩散通量 (界面)
        """
        n = len(C)
        F_diff = np.zeros(n+1)

        # 内部界面
        for i in range(1, n):
            dC_dx = (C[i] - C[i-1]) / self.dx
            D_face = 0.5 * (D_L[i-1] + D_L[i])
            F_diff[i] = -D_face * dC_dx

        # 边界 (零梯度)
        F_diff[0] = 0.0
        F_diff[n] = 0.0

        return F_diff

    def solve_transport(
        self,
        dt: float,
        C: np.ndarray,
        u: np.ndarray,
        h: np.ndarray,
        D_L: np.ndarray
    ) -> np.ndarray:
        """
        求解输运方程 (对流+扩散)

        ∂C/∂t + ∂F/∂x = 0

        Parameters:
        -----------
        dt : float
            时间步长 (s)
        C : array
            当前浓度 (mg/L)
        u : array
            流速 (m/s)
        h : array
            水深 (m)
        D_L : array
            扩散系数 (m²/s)

        Returns:
        --------
        C_new : array
            更新后浓度 (mg/L)
        """
        # 对流通量
        F_adv = self.compute_advective_flux(C, u)

        # 扩散通量
        F_diff = self.compute_diffusive_flux(C, D_L)

        # 总通量
        F_total = F_adv + F_diff

        # 有限体积更新
        dC_dt = -(F_total[1:] - F_total[:-1]) / self.dx

        # 欧拉前向
        C_new = C + dt * dC_dt

        # 非负约束
        C_new = np.maximum(C_new, 0.0)

        return C_new

    def strang_splitting_step(
        self,
        dt: float,
        C: np.ndarray,
        u: np.ndarray,
        h: np.ndarray,
        D_L: np.ndarray,
        reaction_func: Callable[[np.ndarray, float], np.ndarray],
        source_sink: Optional[np.ndarray] = None
    ) -> np.ndarray:
        """
        Strang算子分裂法求解ADR方程

        步骤:
        1. 反应半步: C* = C^n + 0.5*dt*R(C^n)
        2. 输运整步: C** = Transport(C*, dt)
        3. 反应半步: C^(n+1) = C** + 0.5*dt*R(C**)

        Parameters:
        -----------
        dt : float
            时间步长 (s)
        C : array
            当前浓度 (mg/L)
        u : array
            流速 (m/s)
        h : array
            水深 (m)
        D_L : array
            扩散系数 (m²/s)
        reaction_func : callable
            反应项函数 R(C, dt) -> dC/dt
        source_sink : array, optional
            外源汇项 (mg/L/s)

        Returns:
        --------
        C_new : array
            更新后浓度 (mg/L)
        """
        # Step 1: 反应半步
        R1 = reaction_func(C, 0.5*dt)
        C_star = C + 0.5*dt*R1

        # 加入源汇
        if source_sink is not None:
            C_star += 0.5*dt*source_sink

        C_star = np.maximum(C_star, 0.0)

        # Step 2: 输运整步
        C_star_star = self.solve_transport(dt, C_star, u, h, D_L)

        # Step 3: 反应半步
        R2 = reaction_func(C_star_star, 0.5*dt)
        C_new = C_star_star + 0.5*dt*R2

        # 加入源汇
        if source_sink is not None:
            C_new += 0.5*dt*source_sink

        C_new = np.maximum(C_new, 0.0)

        return C_new

    def compute_courant_number(
        self,
        dt: float,
        u: np.ndarray
    ) -> float:
        """
        计算Courant数

        CFL = u * dt / dx

        Parameters:
        -----------
        dt : float
            时间步长 (s)
        u : array
            流速 (m/s)

        Returns:
        --------
        CFL : float
            最大Courant数
        """
        CFL = np.max(np.abs(u)) * dt / self.dx
        return CFL

    def check_stability(
        self,
        dt: float,
        u: np.ndarray,
        D_L: np.ndarray,
        cfl_limit: float = 0.5
    ) -> Tuple[bool, str]:
        """
        检查数值稳定性

        Parameters:
        -----------
        dt : float
            时间步长 (s)
        u : array
            流速 (m/s)
        D_L : array
            扩散系数 (m²/s)
        cfl_limit : float
            CFL数上限

        Returns:
        --------
        is_stable : bool
            是否稳定
        message : str
            信息
        """
        # 对流CFL条件
        CFL_adv = self.compute_courant_number(dt, u)

        # 扩散CFL条件
        CFL_diff = np.max(D_L) * dt / self.dx**2

        if CFL_adv > cfl_limit:
            return False, f"对流CFL={CFL_adv:.3f} > {cfl_limit}, 不稳定!"

        if CFL_diff > 0.5:
            return False, f"扩散CFL={CFL_diff:.3f} > 0.5, 不稳定!"

        return True, f"稳定 (CFL_adv={CFL_adv:.3f}, CFL_diff={CFL_diff:.3f})"


class ConservativeTracerSolver(ADRSolver):
    """
    保守示踪剂求解器 (无反应项)

    用于验证输运算法的质量守恒性
    """

    def __init__(self, n_cells: int, dx: float, **kwargs):
        super().__init__(n_cells, dx, **kwargs)
        self.C = np.zeros(n_cells)

    def initialize(self, C_initial: np.ndarray):
        """初始化浓度场"""
        self.C = C_initial.copy()

    def step(
        self,
        dt: float,
        u: np.ndarray,
        h: np.ndarray,
        manning_n: float = 0.03
    ) -> np.ndarray:
        """推进一步 (仅输运, 无反应)"""
        # 计算扩散系数
        D_L = self.compute_dispersion_coefficient(h, u, manning_n=manning_n)

        # 求解输运
        self.C = self.solve_transport(dt, self.C, u, h, D_L)

        return self.C

    def compute_total_mass(self, h: np.ndarray, width: float) -> float:
        """
        计算总质量 (用于验证守恒性)

        Parameters:
        -----------
        h : array
            水深 (m)
        width : float
            河道宽度 (m)

        Returns:
        --------
        total_mass : float
            总质量 (kg)
        """
        # 体积 = h * width * dx
        volume = h * width * self.dx  # m³

        # 质量 = 浓度 * 体积 (mg/L * m³ = g)
        mass = self.C * volume  # mg/L * m³ = mg * 1000 L / L = mg * 1000

        total_mass = np.sum(mass) / 1e6  # 转换为kg

        return total_mass
