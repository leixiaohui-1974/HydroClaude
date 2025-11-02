#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Frazil Ice多组分模拟模块 - Frazil Ice Multi-Size-Class Model

物理模型：
    ∂Ni/∂t + u·∂Ni/∂x - ws,i·∂Ni/∂z = ∂/∂x(εt·∂Ni/∂x) + Si

    其中:
    - Ni: 第i粒径组冰晶数密度 (#/m³)
    - ws,i: 沉降速度 (m/s)
    - εt: 湍流扩散系数 (m²/s)
    - Si: 源汇项 (成核/生长/絮凝/融化)

关键过程:
    1. 初级成核: Np = C1 · ΔT^α · (u/h)^β
    2. 次级成核: Ns = C2 · Σ(Ni·Vi·di) · ΔT
    3. 热生长: dri/dt = Nu·λi·ΔT / (ρi·Lf·ri)
    4. 絮凝: Jij = αflocc · G · Ni·Nj · (ri+rj)³
    5. 沉降: ws = (2/9) · g · (ρi-ρw) · ri² / μ

对标: MIKE ICE Frazil模块, CRISSP多组分模型

作者: HydroClaude Team
日期: 2025-11-02
"""

import numpy as np
from typing import Dict, Optional, Tuple

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


class FrazilIceSolver:
    """
    Frazil Ice多组分求解器

    使用对数粒径分布表示冰晶群体
    """

    def __init__(
        self,
        n_cells: int,
        dx: float,
        n_size_classes: int = 10,
        r_min: float = 1e-5,    # 最小半径 10 μm
        r_max: float = 1e-2,    # 最大半径 10 mm
        use_numba: bool = True
    ):
        """
        初始化Frazil Ice求解器

        Parameters:
        -----------
        n_cells : int
            网格单元数
        dx : float
            网格间距 (m)
        n_size_classes : int
            粒径组数
        r_min : float
            最小半径 (m)
        r_max : float
            最大半径 (m)
        use_numba : bool
            是否使用Numba加速
        """
        self.n_cells = n_cells
        self.dx = dx
        self.n_classes = n_size_classes
        self.use_numba = use_numba and NUMBA_AVAILABLE

        # 粒径bins (对数分布)
        self.r_bins = np.logspace(
            np.log10(r_min), np.log10(r_max), n_size_classes
        )

        # 粒径bin边界
        self.r_edges = np.logspace(
            np.log10(r_min), np.log10(r_max), n_size_classes + 1
        )

        # 状态变量: 数密度 N[cell, size_class]
        self.N = np.zeros((n_cells, n_size_classes))

        # 物理常数
        self.rho_ice = 917.0     # 冰密度 kg/m³
        self.rho_water = 1000.0  # 水密度 kg/m³
        self.L_fusion = 3.34e5   # 融化潜热 J/kg
        self.k_ice = 2.2         # 冰热导率 W/(m·K)
        self.T_freeze = 0.0      # 冰点 °C
        self.g = 9.81            # 重力加速度 m/s²
        self.nu = 1e-6           # 运动粘度 m²/s @ 0°C
        self.Pr = 13.4           # Prandtl数 @ 0°C

        # 成核参数 (经验系数)
        self.C_primary = 1e6     # 初级成核系数 (#/m³/s)
        self.alpha_nucleation = 2.0  # 过冷度指数
        self.beta_nucleation = 0.5   # 流速指数

        self.C_secondary = 1e3   # 次级成核系数

        # 絮凝参数
        self.alpha_flocc = 0.25  # 絮凝效率
        self.break_prob = 0.1    # 破碎概率

        # 湍流参数
        self.epsilon_t_base = 1e-3  # 基础湍流耗散率 m²/s³

    def initialize(self, N_initial: Optional[np.ndarray] = None):
        """
        初始化粒径分布

        Parameters:
        -----------
        N_initial : array (n_cells, n_classes), optional
            初始数密度分布
        """
        if N_initial is not None:
            self.N = N_initial.copy()
        else:
            self.N = np.zeros((self.n_cells, self.n_classes))

    def compute_primary_nucleation(
        self,
        T: np.ndarray,
        u: np.ndarray,
        h: np.ndarray
    ) -> np.ndarray:
        """
        计算初级成核率

        模型: Np = C1 · ΔT^α · (u/h)^β

        Parameters:
        -----------
        T : array
            水温 (°C)
        u : array
            流速 (m/s)
        h : array
            水深 (m)

        Returns:
        --------
        N_primary : array
            初级成核率 (#/m³/s), 在最小粒径组
        """
        # 过冷度
        delta_T = np.maximum(self.T_freeze - T, 0.0)

        # 湍流强度
        turbulence = np.abs(u) / (h + 1e-6)

        # 初级成核率 (仅在过冷区域)
        N_primary = np.zeros(self.n_cells)
        mask = delta_T > 0

        N_primary[mask] = (
            self.C_primary
            * delta_T[mask]**self.alpha_nucleation
            * turbulence[mask]**self.beta_nucleation
        )

        return N_primary

    def compute_secondary_nucleation(
        self,
        T: np.ndarray
    ) -> np.ndarray:
        """
        计算次级成核率（碰撞产生新晶核）

        模型: Ns = C2 · Σ(Ni·Vi·di) · ΔT

        Parameters:
        -----------
        T : array
            水温 (°C)

        Returns:
        --------
        N_secondary : array
            次级成核率 (#/m³/s)
        """
        # 过冷度
        delta_T = np.maximum(self.T_freeze - T, 0.0)

        # 计算总冰体积与表面积
        N_secondary = np.zeros(self.n_cells)

        for i in range(self.n_cells):
            if delta_T[i] > 0:
                # 体积加权数密度
                total_volume_number = 0.0
                for j in range(self.n_classes):
                    V_j = (4.0/3.0) * np.pi * self.r_bins[j]**3
                    d_j = 2.0 * self.r_bins[j]
                    total_volume_number += self.N[i, j] * V_j * d_j

                N_secondary[i] = self.C_secondary * total_volume_number * delta_T[i]

        return N_secondary

    def compute_growth_rate(
        self,
        T: np.ndarray,
        u: np.ndarray
    ) -> np.ndarray:
        """
        计算冰晶热生长速率

        模型: dri/dt = Nu·λi·ΔT / (ρi·Lf·ri)
              Nu = 2 + 0.6·Re^0.5·Pr^0.33

        Parameters:
        -----------
        T : array
            水温 (°C)
        u : array
            流速 (m/s)

        Returns:
        --------
        dr_dt : array (n_cells, n_classes)
            半径增长率 (m/s)
        """
        # 过冷度
        delta_T = np.maximum(self.T_freeze - T, 0.0)

        # 增长率数组
        dr_dt = np.zeros((self.n_cells, self.n_classes))

        for i in range(self.n_cells):
            if delta_T[i] > 0:
                for j in range(self.n_classes):
                    r_j = self.r_bins[j]

                    # Reynolds数
                    Re = 2.0 * r_j * np.abs(u[i]) / self.nu

                    # Nusselt数
                    Nu = 2.0 + 0.6 * Re**0.5 * self.Pr**0.33

                    # 热生长率
                    dr_dt[i, j] = (
                        Nu * self.k_ice * delta_T[i]
                        / (self.rho_ice * self.L_fusion * r_j)
                    )

        return dr_dt

    def compute_flocculation(
        self,
        u: np.ndarray,
        h: np.ndarray
    ) -> np.ndarray:
        """
        计算絮凝率（湍流碰撞）

        模型: Jij = αflocc · G · Ni·Nj · (ri+rj)³
              G = (εt/ν)^0.5  (湍流剪切率)

        Parameters:
        -----------
        u : array
            流速 (m/s)
        h : array
            水深 (m)

        Returns:
        --------
        dN_flocc : array (n_cells, n_classes)
            絮凝导致的数密度变化率 (#/m³/s)
        """
        dN_flocc = np.zeros((self.n_cells, self.n_classes))

        for i in range(self.n_cells):
            # 湍流耗散率 (简化估计)
            epsilon_t = self.epsilon_t_base * (np.abs(u[i])**3 / h[i])

            # 湍流剪切率
            G = np.sqrt(epsilon_t / self.nu)

            # 对每个粒径组计算絮凝
            for j in range(self.n_classes - 1):
                for k in range(j + 1, self.n_classes):
                    # 碰撞核
                    collision_kernel = (
                        self.alpha_flocc * G
                        * (self.r_bins[j] + self.r_bins[k])**3
                    )

                    # 碰撞率
                    collision_rate = (
                        collision_kernel
                        * self.N[i, j]
                        * self.N[i, k]
                    )

                    # 小颗粒减少
                    dN_flocc[i, j] -= collision_rate
                    dN_flocc[i, k] -= collision_rate

                    # 大颗粒增加 (移到下一个粒径组)
                    if k < self.n_classes - 1:
                        dN_flocc[i, k + 1] += collision_rate

        return dN_flocc

    def compute_settling_velocity(self) -> np.ndarray:
        """
        计算沉降速度 (Stokes定律)

        ws = (2/9) · g · (ρi - ρw) · ri² / μ

        Returns:
        --------
        ws : array (n_classes,)
            沉降速度 (m/s)
        """
        # 动力粘度
        mu = self.nu * self.rho_water

        # Stokes沉降速度
        ws = (
            (2.0 / 9.0) * self.g
            * (self.rho_water - self.rho_ice)  # 注意: 冰比水轻, ws为负(上浮)
            * self.r_bins**2
            / mu
        )

        return ws

    def compute_melting(
        self,
        T: np.ndarray,
        dt: float
    ):
        """
        计算融化过程 (正温区域)

        Parameters:
        -----------
        T : array
            水温 (°C)
        dt : float
            时间步长 (s)
        """
        # 正温区域: 冰晶完全融化
        mask = T > self.T_freeze

        self.N[mask, :] = 0.0

    def transport_frazil(
        self,
        dt: float,
        u: np.ndarray,
        h: np.ndarray,
        D_t: np.ndarray
    ):
        """
        输运frazil ice (对流-扩散)

        使用一阶迎风格式 + 中心差分扩散

        Parameters:
        -----------
        dt : float
            时间步长 (s)
        u : array
            流速 (m/s)
        h : array
            水深 (m)
        D_t : array
            湍流扩散系数 (m²/s)
        """
        # 沉降速度
        ws = self.compute_settling_velocity()

        # 对每个粒径组求解输运方程
        for j in range(self.n_classes):
            N_old = self.N[:, j].copy()

            # 对流项 (一阶迎风)
            dN_conv = np.zeros(self.n_cells)
            for i in range(1, self.n_cells - 1):
                if u[i] > 0:
                    dN_conv[i] = -u[i] * (N_old[i] - N_old[i-1]) / self.dx
                else:
                    dN_conv[i] = -u[i] * (N_old[i+1] - N_old[i]) / self.dx

            # 扩散项 (中心差分)
            dN_diff = np.zeros(self.n_cells)
            for i in range(1, self.n_cells - 1):
                dN_diff[i] = (
                    D_t[i] * (N_old[i+1] - 2*N_old[i] + N_old[i-1]) / self.dx**2
                )

            # 沉降项 (垂向对流, 简化为源汇项)
            # ws < 0 表示上浮
            dN_settling = -np.abs(ws[j]) * N_old / (h + 1e-6)

            # 更新
            self.N[:, j] += dt * (dN_conv + dN_diff + dN_settling)

            # 非负约束
            self.N[:, j] = np.maximum(self.N[:, j], 0.0)

    def step(
        self,
        dt: float,
        T: np.ndarray,
        u: np.ndarray,
        h: np.ndarray,
        D_t: Optional[np.ndarray] = None
    ) -> Dict[str, np.ndarray]:
        """
        推进一个时间步

        使用算子分裂:
        1. 成核
        2. 生长
        3. 絮凝
        4. 输运
        5. 融化

        Parameters:
        -----------
        dt : float
            时间步长 (s)
        T : array
            水温 (°C)
        u : array
            流速 (m/s)
        h : array
            水深 (m)
        D_t : array, optional
            湍流扩散系数 (m²/s)

        Returns:
        --------
        state : dict
            当前状态
        """
        if D_t is None:
            # 使用Elder公式估计
            u_star = np.abs(u) * 0.03 / h**(1.0/6.0)
            D_t = 5.93 * h * u_star

        # ========== Step 1: 成核 ==========
        # 初级成核 (最小粒径组)
        N_primary = self.compute_primary_nucleation(T, u, h)
        self.N[:, 0] += N_primary * dt

        # 次级成核 (最小粒径组)
        N_secondary = self.compute_secondary_nucleation(T)
        self.N[:, 0] += N_secondary * dt

        # ========== Step 2: 生长 ==========
        dr_dt = self.compute_growth_rate(T, u)

        # 移动颗粒到更大粒径组 (简化处理)
        for i in range(self.n_cells):
            for j in range(self.n_classes - 1):
                if dr_dt[i, j] > 0:
                    # 计算生长导致的粒径变化
                    r_new = self.r_bins[j] + dr_dt[i, j] * dt

                    # 如果超过当前组上限, 移到下一组
                    if r_new > self.r_edges[j+1]:
                        transfer_fraction = 0.5  # 简化: 50%移动
                        transfer_N = self.N[i, j] * transfer_fraction

                        self.N[i, j] -= transfer_N
                        self.N[i, j+1] += transfer_N

        # ========== Step 3: 絮凝 ==========
        dN_flocc = self.compute_flocculation(u, h)
        self.N += dN_flocc * dt
        self.N = np.maximum(self.N, 0.0)

        # ========== Step 4: 输运 ==========
        self.transport_frazil(dt, u, h, D_t)

        # ========== Step 5: 融化 ==========
        self.compute_melting(T, dt)

        return self.get_state()

    def get_state(self) -> Dict[str, np.ndarray]:
        """获取当前状态"""
        return {
            'N': self.N.copy(),
            'r_bins': self.r_bins,
            'total_number': np.sum(self.N, axis=1),
            'total_volume': self.compute_total_volume(),
            'mean_diameter': self.compute_mean_diameter()
        }

    def compute_total_volume(self) -> np.ndarray:
        """
        计算总冰体积分数

        Returns:
        --------
        phi : array
            冰体积分数 (无量纲)
        """
        phi = np.zeros(self.n_cells)

        for i in range(self.n_cells):
            total_volume = 0.0
            for j in range(self.n_classes):
                V_j = (4.0/3.0) * np.pi * self.r_bins[j]**3
                total_volume += self.N[i, j] * V_j

            phi[i] = total_volume

        return phi

    def compute_mean_diameter(self) -> np.ndarray:
        """
        计算平均粒径 (数量加权)

        Returns:
        --------
        d_mean : array
            平均直径 (m)
        """
        d_mean = np.zeros(self.n_cells)

        for i in range(self.n_cells):
            total_N = np.sum(self.N[i, :])
            if total_N > 1e-6:
                # 数量加权平均
                d_mean[i] = np.sum(self.N[i, :] * 2*self.r_bins) / total_N
            else:
                d_mean[i] = 0.0

        return d_mean

    def get_diagnostics(self, T: np.ndarray, u: np.ndarray, h: np.ndarray) -> Dict:
        """
        获取诊断信息

        Returns:
        --------
        diag : dict
            诊断信息
        """
        diag = {
            'total_number_density': np.sum(self.N, axis=1),
            'total_ice_volume_fraction': self.compute_total_volume(),
            'mean_diameter': self.compute_mean_diameter(),
            'primary_nucleation_rate': self.compute_primary_nucleation(T, u, h),
            'secondary_nucleation_rate': self.compute_secondary_nucleation(T),
            'settling_velocity': self.compute_settling_velocity(),
            'size_distribution': self.N.copy()
        }

        return diag
