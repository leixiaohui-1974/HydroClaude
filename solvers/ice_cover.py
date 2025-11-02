#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
冰盖厚度模拟模块 - Ice Cover Thickness Solver

物理模型：
    Stefan方程 (经典冰盖增长模型):
        ρi·Lf·dh/dt = ki·(Tf - Ts)/h - kw·(Tw - Tf)/δw

    其中:
    - h: 冰盖厚度 (m)
    - ρi: 冰密度 (kg/m³)
    - Lf: 融化潜热 (J/kg)
    - ki: 冰热导率 (W/(m·K))
    - kw: 水热导率 (W/(m·K))
    - Tf: 冰点温度 (0°C)
    - Ts: 冰表面温度 (°C)
    - Tw: 水温 (°C)
    - δw: 水边界层厚度 (m)

对标: MIKE ICE, CRISSP冰盖模块

作者: HydroClaude Team
日期: 2025-11-02
"""

import numpy as np
from typing import Dict, Optional, Tuple


class IceCoverSolver:
    """
    冰盖厚度求解器

    基于Stefan方程求解冰盖演化
    """

    def __init__(
        self,
        n_cells: int,
        rho_ice: float = 917.0,      # 冰密度 kg/m³
        L_fusion: float = 3.34e5,    # 融化潜热 J/kg
        k_ice: float = 2.2,          # 冰热导率 W/(m·K)
        k_water: float = 0.6,        # 水热导率 W/(m·K)
        T_freeze: float = 0.0        # 冰点 °C
    ):
        """
        初始化冰盖求解器

        Parameters:
        -----------
        n_cells : int
            网格单元数
        rho_ice : float
            冰密度 (kg/m³)
        L_fusion : float
            融化潜热 (J/kg)
        k_ice : float
            冰热导率 (W/(m·K))
        k_water : float
            水热导率 (W/(m·K))
        T_freeze : float
            冰点温度 (°C)
        """
        self.n_cells = n_cells

        # 物理常数
        self.rho_ice = rho_ice
        self.L_fusion = L_fusion
        self.k_ice = k_ice
        self.k_water = k_water
        self.T_freeze = T_freeze

        # 状态变量
        self.h_ice = np.zeros(n_cells)          # 冰盖厚度 (m)
        self.ice_fraction = np.zeros(n_cells)   # 冰盖覆盖率 (0-1)

        # 边界层厚度
        self.delta_bl = 0.01  # 水边界层厚度 m

    def initialize(
        self,
        h_ice_initial: Optional[np.ndarray] = None,
        ice_fraction_initial: Optional[np.ndarray] = None
    ):
        """
        初始化冰盖状态

        Parameters:
        -----------
        h_ice_initial : array, optional
            初始冰盖厚度 (m)
        ice_fraction_initial : array, optional
            初始冰盖覆盖率 (0-1)
        """
        if h_ice_initial is not None:
            self.h_ice = h_ice_initial.copy()

        if ice_fraction_initial is not None:
            self.ice_fraction = ice_fraction_initial.copy()

    def compute_surface_temperature(
        self,
        T_air: float,
        h_ice: np.ndarray,
        Q_solar: float = 0.0
    ) -> np.ndarray:
        """
        计算冰表面温度

        简化模型: 假设稳态热平衡
            ki*(Tf - Ts)/h = h_air*(Ts - Ta) + ε*σ*Ts⁴

        这里使用简化版本:
            Ts ≈ (Ta + Tf)/2  (线性插值)

        Parameters:
        -----------
        T_air : float
            气温 (°C)
        h_ice : array
            冰盖厚度 (m)
        Q_solar : float
            太阳辐射 (W/m²), 暂未使用

        Returns:
        --------
        T_surface : array
            冰表面温度 (°C)
        """
        # 简化假设: 表面温度为气温和冰点的平均
        # (更精确的模型需要迭代求解热平衡方程)
        T_surface = np.full(len(h_ice), 0.5 * (T_air + self.T_freeze))
        T_surface = np.minimum(T_surface, self.T_freeze)

        return T_surface

    def solve_stefan_equation(
        self,
        dt: float,
        T_air: float,
        T_water: np.ndarray,
        h_ice: np.ndarray
    ) -> np.ndarray:
        """
        求解Stefan方程获取冰盖厚度变化

        ρi·Lf·dh/dt = ki·(Tf - Ts)/h - kw·(Tw - Tf)/δw

        Parameters:
        -----------
        dt : float
            时间步长 (s)
        T_air : float
            气温 (°C)
        T_water : array
            水温 (°C)
        h_ice : array
            当前冰盖厚度 (m)

        Returns:
        --------
        h_ice_new : array
            更新后冰盖厚度 (m)
        """
        h_ice_new = h_ice.copy()

        # 计算冰表面温度
        T_surface = self.compute_surface_temperature(T_air, h_ice)

        for i in range(self.n_cells):
            # 检查是否有冰
            if h_ice[i] > 1e-6:
                # 现有冰盖增长/融化

                # 向上热通量 (通过冰层)
                Q_up = self.k_ice * (self.T_freeze - T_surface[i]) / h_ice[i]

                # 向下热通量 (从水体)
                Q_down = self.k_water * (T_water[i] - self.T_freeze) / self.delta_bl

                # 净热通量 (正值表示冰增长)
                Q_net = Q_up - Q_down

                # 厚度变化率
                dh_dt = Q_net / (self.rho_ice * self.L_fusion)

                # 更新厚度
                h_ice_new[i] = h_ice[i] + dh_dt * dt

                # 融化处理
                if h_ice_new[i] < 0:
                    h_ice_new[i] = 0.0
                    self.ice_fraction[i] = 0.0

            else:
                # 检查是否开始结冰
                if T_water[i] <= self.T_freeze and T_air < 0:
                    # 初始成冰 (假设形成1mm薄冰)
                    h_ice_new[i] = 0.001  # 1mm
                    self.ice_fraction[i] = 0.1  # 初始10%覆盖
                else:
                    h_ice_new[i] = 0.0

        return h_ice_new

    def update_ice_fraction(
        self,
        h_ice: np.ndarray,
        T_water: np.ndarray
    ):
        """
        更新冰盖覆盖率

        简化模型:
        - h > 0.1m: 100%覆盖
        - 0 < h < 0.1m: 线性插值
        - h = 0: 0%覆盖

        Parameters:
        -----------
        h_ice : array
            冰盖厚度 (m)
        T_water : array
            水温 (°C)
        """
        for i in range(self.n_cells):
            if h_ice[i] >= 0.1:
                self.ice_fraction[i] = 1.0
            elif h_ice[i] > 0:
                self.ice_fraction[i] = h_ice[i] / 0.1  # 线性增长
            else:
                self.ice_fraction[i] = 0.0

    def step(
        self,
        dt: float,
        T_air: float,
        T_water: np.ndarray
    ) -> Dict[str, np.ndarray]:
        """
        推进一个时间步

        Parameters:
        -----------
        dt : float
            时间步长 (s)
        T_air : float
            气温 (°C)
        T_water : array
            水温 (°C)

        Returns:
        --------
        state : dict
            {'h_ice': array, 'ice_fraction': array}
        """
        # 求解Stefan方程
        self.h_ice = self.solve_stefan_equation(dt, T_air, T_water, self.h_ice)

        # 更新覆盖率
        self.update_ice_fraction(self.h_ice, T_water)

        return self.get_state()

    def get_state(self) -> Dict[str, np.ndarray]:
        """获取当前状态"""
        return {
            'h_ice': self.h_ice.copy(),
            'ice_fraction': self.ice_fraction.copy()
        }

    def get_diagnostics(self, T_air: float, T_water: np.ndarray) -> Dict[str, np.ndarray]:
        """
        获取诊断信息

        Returns:
        --------
        diag : dict
            诊断信息
        """
        T_surface = self.compute_surface_temperature(T_air, self.h_ice)

        # 计算热通量
        Q_up = np.zeros(self.n_cells)
        Q_down = np.zeros(self.n_cells)

        mask = self.h_ice > 1e-6
        Q_up[mask] = self.k_ice * (self.T_freeze - T_surface[mask]) / self.h_ice[mask]
        Q_down[mask] = self.k_water * (T_water[mask] - self.T_freeze) / self.delta_bl

        diag = {
            'T_surface': T_surface,
            'heat_flux_up': Q_up,
            'heat_flux_down': Q_down,
            'heat_flux_net': Q_up - Q_down,
            'ice_volume': np.sum(self.h_ice),
            'ice_covered_cells': np.sum(self.ice_fraction > 0.01)
        }

        return diag


class StefanAnalyticalSolution:
    """
    Stefan问题解析解 (用于验证冰盖求解器)

    经典1D Stefan问题:
        h(t) = λ * √(2*α*t)

    其中:
        - α = k/(ρ·cp) 热扩散系数
        - λ 为Stefan数的函数,需要迭代求解
    """

    def __init__(
        self,
        T_air: float,      # 恒定气温 (°C)
        T_water: float,    # 恒定水温 (°C)
        rho_ice: float = 917.0,
        L_fusion: float = 3.34e5,
        k_ice: float = 2.2
    ):
        self.T_air = T_air
        self.T_water = T_water
        self.rho_ice = rho_ice
        self.L_fusion = L_fusion
        self.k_ice = k_ice

        # 计算Stefan数
        cp_ice = 2108.0  # J/(kg·K)
        self.alpha = k_ice / (rho_ice * cp_ice)

        # Stefan常数 (需要数值求解超越方程)
        # 这里使用简化近似
        self.stefan_constant = self._compute_stefan_constant()

    def _compute_stefan_constant(self) -> float:
        """
        计算Stefan常数 (简化版本)

        精确解需要求解超越方程,这里使用近似公式
        """
        # 简化假设
        delta_T = abs(self.T_air)
        lam = np.sqrt(delta_T / 10.0)  # 经验公式
        return lam

    def compute_thickness(self, t: float) -> float:
        """
        计算解析解冰盖厚度

        h(t) = λ * √(2*α*t)

        Parameters:
        -----------
        t : float
            时间 (s)

        Returns:
        --------
        h : float
            冰盖厚度 (m)
        """
        h = self.stefan_constant * np.sqrt(2 * self.alpha * t)
        return h
