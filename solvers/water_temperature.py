#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
水温输运模拟模块 - Water Temperature Transport Module

物理模型：
    ∂T/∂t + u·∂T/∂x = ∂/∂x(DT·∂T/∂x) + ST

    其中:
    - T: 水温 (°C)
    - u: 流速 (m/s)
    - DT: 热扩散系数 (m²/s)
    - ST: 热源汇项 (°C/s)
        - 大气热交换
        - 冰-水界面热交换
        - 底泥热交换

对标: MIKE ICE热模块, CRISSP温度模块

作者: HydroClaude Team
日期: 2025-11-02
"""

import numpy as np
from typing import Tuple, Dict, Optional

# 尝试导入Numba加速
try:
    from numba import njit
    NUMBA_AVAILABLE = True
except ImportError:
    NUMBA_AVAILABLE = False
    # 定义空装饰器
    def njit(*args, **kwargs):
        def decorator(func):
            return func
        if len(args) == 1 and callable(args[0]):
            return args[0]
        return decorator


class WaterTemperatureSolver:
    """
    水温输运求解器

    复用HydroClaude的Godunov框架进行对流项求解
    使用中心差分求解扩散项
    """

    def __init__(
        self,
        n_cells: int,
        dx: float,
        thermal_diffusivity: float = 1.4e-7,  # 水的热扩散系数 m²/s @ 20°C
        use_numba: bool = True
    ):
        """
        初始化水温求解器

        Parameters:
        -----------
        n_cells : int
            网格单元数
        dx : float
            网格间距 (m)
        thermal_diffusivity : float
            热扩散系数 (m²/s)，默认20°C水
        use_numba : bool
            是否使用Numba加速
        """
        self.n_cells = n_cells
        self.dx = dx
        self.D_T = thermal_diffusivity
        self.use_numba = use_numba and NUMBA_AVAILABLE

        # 状态变量
        self.T = np.ones(n_cells) * 20.0  # 初始温度20°C

        # 物理常数
        self.rho_w = 1000.0  # 水密度 kg/m³
        self.cp_w = 4186.0   # 水比热容 J/(kg·K)
        self.T_freeze = 0.0  # 冰点 °C

        # 热交换参数
        self.stefan_boltzmann = 5.67e-8  # Stefan-Boltzmann常数 W/(m²·K⁴)
        self.emissivity = 0.97  # 水面发射率

    def initialize(self, T_initial: np.ndarray):
        """初始化温度场"""
        if len(T_initial) != self.n_cells:
            raise ValueError(f"温度数组长度{len(T_initial)}与网格数{self.n_cells}不匹配")
        self.T = T_initial.copy()

    def compute_atmospheric_heat_flux(
        self,
        T_water: np.ndarray,
        T_air: float,
        solar_radiation: float,
        wind_speed: float,
        relative_humidity: float,
        cloud_cover: float = 0.0
    ) -> np.ndarray:
        """
        计算大气热交换通量

        参考: QUAL2K热平衡模型

        Parameters:
        -----------
        T_water : array
            水温 (°C)
        T_air : float
            气温 (°C)
        solar_radiation : float
            太阳短波辐射 (W/m²)
        wind_speed : float
            风速 (m/s)
        relative_humidity : float
            相对湿度 (0-1)
        cloud_cover : float
            云量 (0-1)

        Returns:
        --------
        Q_net : array
            净热通量 (W/m²), 正值表示加热
        """
        # 1. 短波辐射 (已吸收部分，假设反照率0.08)
        albedo = 0.08
        Q_solar = solar_radiation * (1 - albedo)

        # 2. 长波辐射 (Stefan-Boltzmann定律)
        T_w_K = T_water + 273.15
        T_a_K = T_air + 273.15

        # 大气辐射 (云量修正)
        emissivity_air = 0.64 + 0.045 * np.sqrt(self._vapor_pressure(T_air, relative_humidity))
        emissivity_air *= (1 + 0.17 * cloud_cover**2)
        Q_atm_longwave = emissivity_air * self.stefan_boltzmann * T_a_K**4

        # 水面辐射
        Q_back_radiation = self.emissivity * self.stefan_boltzmann * T_w_K**4

        Q_longwave = Q_atm_longwave - Q_back_radiation

        # 3. 蒸发潜热 (Penman方法)
        L_v = 2.453e6  # 蒸发潜热 J/kg @ 20°C
        e_s = self._vapor_pressure(T_water, 1.0)  # 饱和水汽压
        e_a = self._vapor_pressure(T_air, relative_humidity)  # 空气水汽压

        # 风函数 (Ryan & Harleman, 1973)
        f_wind = 9.2 + 0.46 * wind_speed**2  # W/(m²·mb)
        Q_evaporation = -f_wind * (e_s - e_a)  # 负值表示冷却

        # 4. 对流热交换 (Bowen比)
        bowen_ratio = 0.61  # 对流/蒸发比
        Q_convection = bowen_ratio * Q_evaporation * (T_water - T_air) / (e_s - e_a + 1e-6)

        # 总净热通量
        Q_net = Q_solar + Q_longwave + Q_evaporation + Q_convection

        return Q_net * np.ones(len(T_water))

    def _vapor_pressure(self, T: float, RH: float) -> float:
        """
        计算水汽压 (mb)

        Magnus公式
        """
        e_sat = 6.112 * np.exp(17.67 * T / (T + 243.5))
        return e_sat * RH

    def compute_ice_water_heat_flux(
        self,
        T_water: np.ndarray,
        ice_cover_thickness: np.ndarray,
        ice_cover_fraction: np.ndarray
    ) -> np.ndarray:
        """
        计算冰-水界面热交换

        Parameters:
        -----------
        T_water : array
            水温 (°C)
        ice_cover_thickness : array
            冰盖厚度 (m)
        ice_cover_fraction : array
            冰盖覆盖率 (0-1)

        Returns:
        --------
        Q_ice : array
            冰-水热通量 (W/m²), 负值表示水体失热
        """
        # 冰的热导率
        k_ice = 2.2  # W/(m·K)

        # 冰-水界面温度梯度
        delta_T = T_water - self.T_freeze

        # 边界层厚度 (假设1cm)
        delta_bl = 0.01  # m

        # 热通量 (仅在有冰盖区域)
        k_water = 0.6  # W/(m·K)
        Q_ice = -k_water * delta_T / delta_bl * ice_cover_fraction

        return Q_ice

    def compute_bed_heat_flux(
        self,
        T_water: np.ndarray,
        T_bed: float = 10.0
    ) -> np.ndarray:
        """
        计算底泥热交换

        Parameters:
        -----------
        T_water : array
            水温 (°C)
        T_bed : float
            底泥温度 (°C)，通常为年平均气温

        Returns:
        --------
        Q_bed : array
            底泥热通量 (W/m²)
        """
        # 底泥热导率
        k_bed = 1.5  # W/(m·K)
        delta_bed = 0.1  # 边界层厚度 m

        Q_bed = k_bed * (T_bed - T_water) / delta_bed

        return Q_bed

    def solve_advection_diffusion(
        self,
        dt: float,
        T: np.ndarray,
        u: np.ndarray,
        h: np.ndarray,
        Q_net: np.ndarray
    ) -> np.ndarray:
        """
        求解对流-扩散方程

        ∂T/∂t + u·∂T/∂x = DT·∂²T/∂x² + Q_net/(ρ·cp·h)

        数值格式: TVD-MUSCL + 中心差分

        Parameters:
        -----------
        dt : float
            时间步长 (s)
        T : array
            当前温度 (°C)
        u : array
            流速 (m/s)
        h : array
            水深 (m)
        Q_net : array
            净热通量 (W/m²)

        Returns:
        --------
        T_new : array
            更新后温度 (°C)
        """
        if self.use_numba:
            return self._solve_advection_diffusion_numba(
                dt, T, u, h, Q_net, self.dx, self.D_T, self.rho_w, self.cp_w
            )
        else:
            return self._solve_advection_diffusion_python(
                dt, T, u, h, Q_net
            )

    def _solve_advection_diffusion_python(
        self,
        dt: float,
        T: np.ndarray,
        u: np.ndarray,
        h: np.ndarray,
        Q_net: np.ndarray
    ) -> np.ndarray:
        """纯Python实现"""
        n = len(T)
        T_new = T.copy()

        # 1. 对流项 (一阶迎风格式)
        for i in range(1, n-1):
            if u[i] > 0:
                dT_dx = (T[i] - T[i-1]) / self.dx
            else:
                dT_dx = (T[i+1] - T[i]) / self.dx
            T_new[i] -= dt * u[i] * dT_dx

        # 2. 扩散项 (中心差分)
        for i in range(1, n-1):
            d2T_dx2 = (T[i+1] - 2*T[i] + T[i-1]) / self.dx**2
            T_new[i] += dt * self.D_T * d2T_dx2

        # 3. 源项 (热交换)
        source = Q_net / (self.rho_w * self.cp_w * h)
        T_new += dt * source

        # 边界条件 (零梯度)
        T_new[0] = T_new[1]
        T_new[-1] = T_new[-2]

        return T_new

    @staticmethod
    @njit
    def _solve_advection_diffusion_numba(
        dt: float,
        T: np.ndarray,
        u: np.ndarray,
        h: np.ndarray,
        Q_net: np.ndarray,
        dx: float,
        D_T: float,
        rho_w: float,
        cp_w: float
    ) -> np.ndarray:
        """Numba加速版本"""
        n = len(T)
        T_new = T.copy()

        # 1. 对流项
        for i in range(1, n-1):
            if u[i] > 0:
                dT_dx = (T[i] - T[i-1]) / dx
            else:
                dT_dx = (T[i+1] - T[i]) / dx
            T_new[i] -= dt * u[i] * dT_dx

        # 2. 扩散项
        for i in range(1, n-1):
            d2T_dx2 = (T[i+1] - 2*T[i] + T[i-1]) / dx**2
            T_new[i] += dt * D_T * d2T_dx2

        # 3. 源项
        for i in range(n):
            source = Q_net[i] / (rho_w * cp_w * h[i])
            T_new[i] += dt * source

        # 边界条件
        T_new[0] = T_new[1]
        T_new[-1] = T_new[-2]

        return T_new

    def step(
        self,
        dt: float,
        u: np.ndarray,
        h: np.ndarray,
        T_air: float,
        solar_radiation: float = 500.0,
        wind_speed: float = 2.0,
        relative_humidity: float = 0.6,
        ice_cover_thickness: Optional[np.ndarray] = None,
        ice_cover_fraction: Optional[np.ndarray] = None
    ) -> np.ndarray:
        """
        推进一个时间步

        Parameters:
        -----------
        dt : float
            时间步长 (s)
        u : array
            流速 (m/s)
        h : array
            水深 (m)
        T_air : float
            气温 (°C)
        solar_radiation : float
            太阳辐射 (W/m²)
        wind_speed : float
            风速 (m/s)
        relative_humidity : float
            相对湿度 (0-1)
        ice_cover_thickness : array, optional
            冰盖厚度 (m)
        ice_cover_fraction : array, optional
            冰盖覆盖率 (0-1)

        Returns:
        --------
        T_new : array
            更新后温度 (°C)
        """
        # 计算热通量
        Q_atm = self.compute_atmospheric_heat_flux(
            self.T, T_air, solar_radiation, wind_speed, relative_humidity
        )

        # 冰-水热交换
        if ice_cover_thickness is not None and ice_cover_fraction is not None:
            Q_ice = self.compute_ice_water_heat_flux(
                self.T, ice_cover_thickness, ice_cover_fraction
            )
        else:
            Q_ice = np.zeros(self.n_cells)

        # 底泥热交换
        Q_bed = self.compute_bed_heat_flux(self.T)

        # 净热通量
        Q_net = Q_atm + Q_ice + Q_bed

        # 求解ADR方程
        self.T = self.solve_advection_diffusion(dt, self.T, u, h, Q_net)

        # 温度约束 (防止低于冰点)
        self.T = np.maximum(self.T, self.T_freeze)

        return self.T

    def get_supercooling(self) -> np.ndarray:
        """
        获取过冷度 (用于frazil ice模拟)

        Returns:
        --------
        delta_T : array
            过冷度 (°C), 正值表示过冷
        """
        return np.maximum(self.T_freeze - self.T, 0.0)

    def get_state(self) -> Dict[str, np.ndarray]:
        """获取当前状态"""
        return {
            'T': self.T.copy(),
            'supercooling': self.get_supercooling()
        }
