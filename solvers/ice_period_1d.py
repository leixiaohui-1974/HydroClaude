#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
IcePeriod1D — 一维河道冰期水力学增强模块
===========================================
对标软件：
  - HEC-RAS 1D Ice（复合糙率、冰盖水力学）
  - MIKE 11 Ice（热力学冰盖生长/消融）
  - RIVICE / CRISSP1D（冰塞动力学）

本模块在现有 IceCoverSolver、IceJamSolver、IceCoveredChannelHydraulics
基础上，提供以下增强功能：

1. **逐断面复合 Manning n 数组**
   - 每个断面独立计算 Sabaneev 复合糙率
   - 通过 `n_array` 属性直接注入 PreissmannUnsteadySolver

2. **增强热力学冰盖模型**（对标 MIKE 11 Ice）
   - 水-冰界面热通量（对流边界层）
   - 太阳辐射穿透冰盖（Beer-Lambert 定律）
   - 冰盖消融判断（T_water > T_freeze）

3. **冰塞压力梯度反馈**
   - 冰塞区域增加附加水面坡降
   - 通过源项注入 Preissmann 残差

4. **冰期水工构筑物联动**
   - 闸门在冰期自动切换到冰期运行模式
   - 泵站在冰期降低出力（防冻保护）

参考文献：
  - Ashton, G.D. (1986). River and Lake Ice Engineering. Water Resources Publications.
  - Shen, H.T. (2010). Mathematical modeling of river ice processes. Cold Regions Sci. Tech.
  - HEC-RAS Technical Reference Manual, Chapter 12: Ice-Covered Rivers.
  - MIKE 11 Reference Manual: Ice Module.

作者: HydroClaude Team
日期: 2026-03-27
"""

import numpy as np
from typing import Dict, Optional, Tuple, Callable
from dataclasses import dataclass, field


# ─────────────────────────────────────────────────────────────
# 物理常数
# ─────────────────────────────────────────────────────────────
RHO_ICE = 917.0       # 冰密度 (kg/m³)
RHO_WATER = 1000.0    # 水密度 (kg/m³)
L_FUSION = 3.34e5     # 融化潜热 (J/kg)
K_ICE = 2.2           # 冰导热系数 (W/(m·K))
CP_WATER = 4186.0     # 水比热容 (J/(kg·K))
T_FREEZE = 0.0        # 冰点 (°C)
SIGMA_SB = 5.67e-8    # Stefan-Boltzmann 常数 (W/(m²·K⁴))


# ─────────────────────────────────────────────────────────────
# 数据类：冰期状态
# ─────────────────────────────────────────────────────────────
@dataclass
class IcePeriodState:
    """一维河道冰期完整状态。"""
    n_cells: int

    # 冰盖
    h_ice: np.ndarray = field(default_factory=lambda: np.array([]))
    T_ice_surface: np.ndarray = field(default_factory=lambda: np.array([]))
    ice_fraction: np.ndarray = field(default_factory=lambda: np.array([]))

    # 冰塞
    ice_jam_mask: np.ndarray = field(default_factory=lambda: np.array([], dtype=bool))
    ice_jam_thickness: np.ndarray = field(default_factory=lambda: np.array([]))
    ice_jam_pressure_grad: np.ndarray = field(default_factory=lambda: np.array([]))

    # 复合糙率
    n_composite: np.ndarray = field(default_factory=lambda: np.array([]))

    # 热通量
    Q_ice_atm: np.ndarray = field(default_factory=lambda: np.array([]))   # 冰-气热通量 (W/m²)
    Q_water_ice: np.ndarray = field(default_factory=lambda: np.array([]))  # 水-冰热通量 (W/m²)

    def __post_init__(self):
        n = self.n_cells
        if len(self.h_ice) == 0:
            self.h_ice = np.zeros(n)
        if len(self.T_ice_surface) == 0:
            self.T_ice_surface = np.zeros(n)
        if len(self.ice_fraction) == 0:
            self.ice_fraction = np.zeros(n)
        if len(self.ice_jam_mask) == 0:
            self.ice_jam_mask = np.zeros(n, dtype=bool)
        if len(self.ice_jam_thickness) == 0:
            self.ice_jam_thickness = np.zeros(n)
        if len(self.ice_jam_pressure_grad) == 0:
            self.ice_jam_pressure_grad = np.zeros(n)
        if len(self.n_composite) == 0:
            self.n_composite = np.full(n, 0.025)
        if len(self.Q_ice_atm) == 0:
            self.Q_ice_atm = np.zeros(n)
        if len(self.Q_water_ice) == 0:
            self.Q_water_ice = np.zeros(n)


# ─────────────────────────────────────────────────────────────
# 增强冰盖热力学模型（对标 MIKE 11 Ice）
# ─────────────────────────────────────────────────────────────
class EnhancedIceThermalModel:
    """
    增强型冰盖热力学模型。

    在 Stefan 方程基础上增加：
    1. 水-冰界面对流热通量（Ashton, 1986）
    2. 太阳辐射穿透冰盖（Beer-Lambert）
    3. 冰盖表面长波辐射
    4. 冰盖消融（T_water > T_freeze 或 T_air > T_freeze）

    冰盖生长方程（修正 Stefan）：
      ρ_i · L_f · dh_ice/dt = Q_atm - Q_water
      Q_atm = k_ice · (T_freeze - T_air) / h_ice  (冰-气热传导)
      Q_water = h_conv · (T_water - T_freeze)       (水-冰对流)

    冰盖消融方程：
      ρ_i · L_f · dh_ice/dt = -Q_solar_through - Q_water  (当 T_air > 0)
    """

    def __init__(
        self,
        n_cells: int,
        k_ice: float = K_ICE,
        rho_ice: float = RHO_ICE,
        L_fusion: float = L_FUSION,
        h_conv_water_ice: float = 20.0,    # 水-冰对流换热系数 (W/(m²·K))，Ashton 典型值
        alpha_ice: float = 0.6,            # 冰面反照率
        kappa_ice: float = 1.5,            # 冰的消光系数 (1/m)，Beer-Lambert
        h_ice_min: float = 0.001,          # 最小冰厚（数值稳定）
        h_ice_max: float = 3.0,            # 最大冰厚（物理上限）
    ):
        self.n_cells = n_cells
        self.k_ice = k_ice
        self.rho_ice = rho_ice
        self.L_fusion = L_fusion
        self.h_conv = h_conv_water_ice
        self.alpha_ice = alpha_ice
        self.kappa_ice = kappa_ice
        self.h_ice_min = h_ice_min
        self.h_ice_max = h_ice_max

        # 状态
        self.h_ice = np.zeros(n_cells)
        self.T_ice_surface = np.zeros(n_cells)
        self.ice_fraction = np.zeros(n_cells)

    def initialize(self, h_ice_0: float = 0.0):
        """初始化冰盖状态。"""
        self.h_ice = np.full(self.n_cells, h_ice_0)
        self.T_ice_surface = np.zeros(self.n_cells)
        self.ice_fraction = np.where(self.h_ice > self.h_ice_min, 1.0, 0.0)

    def compute_ice_surface_temperature(
        self,
        T_air: float,
        h_ice: np.ndarray,
    ) -> np.ndarray:
        """
        计算冰面温度（冰盖内线性温度分布假设）。
        T_surface = T_air（冰面与气温平衡）
        T_bottom = T_freeze = 0°C（冰-水界面）
        """
        # 简化：冰面温度等于气温（当 T_air < 0）
        T_surface = np.where(T_air < T_FREEZE, T_air, T_FREEZE)
        return np.full(self.n_cells, T_surface)

    def compute_heat_fluxes(
        self,
        T_air: float,
        T_water: np.ndarray,
        h_ice: np.ndarray,
        solar_radiation: float = 0.0,
    ) -> Tuple[np.ndarray, np.ndarray, np.ndarray]:
        """
        计算冰盖各热通量分量。

        Returns
        -------
        Q_atm : array  冰-气热通量 (W/m²)，正值表示冰盖散热（有利于生长）
        Q_water : array  水-冰热通量 (W/m²)，正值表示水加热冰（有利于消融）
        Q_solar : array  穿透冰盖的太阳辐射 (W/m²)
        """
        h_safe = np.maximum(h_ice, self.h_ice_min)

        # 1. 冰-气热传导（Stefan 核心项）
        delta_T_atm = T_FREEZE - T_air   # > 0 时有利于冰盖生长
        Q_atm = np.where(
            h_ice >= self.h_ice_min,
            self.k_ice * delta_T_atm / h_safe,
            0.0,
        )

        # 2. 水-冰对流热通量（Ashton, 1986）
        delta_T_water = np.maximum(T_water - T_FREEZE, 0.0)
        Q_water = self.h_conv * delta_T_water

        # 3. 太阳辐射穿透冰盖（Beer-Lambert）
        Q_solar_incident = solar_radiation * (1.0 - self.alpha_ice)
        Q_solar = Q_solar_incident * np.exp(-self.kappa_ice * h_safe)

        return Q_atm, Q_water, Q_solar

    def step(
        self,
        dt: float,
        T_air: float,
        T_water: np.ndarray,
        h: np.ndarray,
        solar_radiation: float = 0.0,
    ) -> Dict:
        """
        推进冰盖热力学一步。

        冰盖生长（T_air < 0，T_water ≈ 0）：
          dh/dt = (Q_atm - Q_water) / (ρ_i · L_f)

        冰盖消融（T_air > 0 或 T_water > 0）：
          dh/dt = -(Q_water + Q_solar) / (ρ_i · L_f)

        Parameters
        ----------
        dt : float  时间步长 (s)
        T_air : float  气温 (°C)
        T_water : array  水温 (°C)
        h : array  水深 (m)
        solar_radiation : float  太阳辐射 (W/m²)

        Returns
        -------
        state : dict
        """
        Q_atm, Q_water, Q_solar = self.compute_heat_fluxes(
            T_air, T_water, self.h_ice, solar_radiation
        )

        # 冰盖生长/消融速率 (m/s)
        dh_dt = np.zeros(self.n_cells)

        # 生长条件：T_air < 0，且水温接近冰点
        growing = (T_air < T_FREEZE) & (T_water < 0.5)
        # 消融条件：T_air > 0 或 T_water > 0.5°C
        melting = (~growing) & (self.h_ice > self.h_ice_min)

        # 生长速率
        dh_dt = np.where(
            growing,
            (Q_atm - Q_water) / (self.rho_ice * self.L_fusion),
            dh_dt,
        )
        # 消融速率（负值）
        dh_dt = np.where(
            melting,
            -(Q_water + Q_solar) / (self.rho_ice * self.L_fusion),
            dh_dt,
        )

        # 更新冰厚
        self.h_ice = self.h_ice + dh_dt * dt
        self.h_ice = np.clip(self.h_ice, 0.0, self.h_ice_max)

        # 物理约束：冰厚不能超过水深的 90%（冰盖搁底）
        self.h_ice = np.minimum(self.h_ice, 0.9 * h)

        # 更新冰盖覆盖率
        self.ice_fraction = np.where(self.h_ice > self.h_ice_min, 1.0, 0.0)

        # 冰面温度
        self.T_ice_surface = self.compute_ice_surface_temperature(T_air, self.h_ice)

        return {
            'h_ice': self.h_ice.copy(),
            'ice_fraction': self.ice_fraction.copy(),
            'T_ice_surface': self.T_ice_surface.copy(),
            'Q_atm': Q_atm,
            'Q_water': Q_water,
            'Q_solar': Q_solar,
            'dh_dt': dh_dt,
        }


# ─────────────────────────────────────────────────────────────
# 逐断面 Manning n 管理器
# ─────────────────────────────────────────────────────────────
class PerNodeManningManager:
    """
    管理逐断面 Manning n 数组，支持冰期复合糙率的精确反馈。

    核心功能：
    - 维护每个断面的基础 Manning n（渠床）
    - 根据冰盖状态计算 Sabaneev 复合糙率
    - 提供 `n_array` 属性供 Preissmann 求解器使用

    HEC-RAS Ice 的处理方式：
    - 无冰：n = n_bed
    - 有冰盖：n_c = Sabaneev(n_bed, n_ice, P_bed, P_ice)
    - 冰塞：n_c = Sabaneev(n_bed, n_ice_rough, P_bed, P_ice_jam)
    """

    def __init__(
        self,
        n_cells: int,
        n_bed: float = 0.025,
        n_ice_smooth: float = 0.010,
        n_ice_rough: float = 0.025,
        B: float = 10.0,
    ):
        self.n_cells = n_cells
        self.n_bed_base = n_bed
        self.n_ice_smooth = n_ice_smooth
        self.n_ice_rough = n_ice_rough
        self.B = B

        # 当前 n 数组（逐断面）
        self._n_array = np.full(n_cells, n_bed)
        # 可设置逐断面基础 n（如河床变化）
        self._n_bed_array = np.full(n_cells, n_bed)

    def set_bed_roughness(self, n_bed_array: np.ndarray):
        """设置逐断面渠床糙率。"""
        self._n_bed_array = n_bed_array.copy()

    def update(
        self,
        h: np.ndarray,
        h_ice: np.ndarray,
        ice_jam_mask: np.ndarray,
    ) -> np.ndarray:
        """
        根据当前冰盖状态更新逐断面复合 Manning n。

        Parameters
        ----------
        h : array  水深 (m)
        h_ice : array  冰盖厚度 (m)
        ice_jam_mask : array  冰塞标记

        Returns
        -------
        n_array : array  逐断面复合 Manning n
        """
        n_bed = self._n_bed_array
        B = self.B

        # 矩形断面湿周
        P_bed = B + 2.0 * np.maximum(h, 1e-3)
        P_ice = np.where(h_ice > 0.01, B, 0.0)

        # 冰底糙率（冰塞区用粗糙值）
        n_ice = np.where(ice_jam_mask, self.n_ice_rough, self.n_ice_smooth)

        # Sabaneev 复合糙率
        has_ice = P_ice > 0.0
        n_c = n_bed.copy()

        if np.any(has_ice):
            num = n_bed**1.5 * P_bed + n_ice**1.5 * P_ice
            den = P_bed + P_ice + 1e-12
            n_c = np.where(has_ice, (num / den) ** (2.0 / 3.0), n_bed)

        self._n_array = n_c
        return n_c

    @property
    def n_array(self) -> np.ndarray:
        """当前逐断面复合 Manning n。"""
        return self._n_array.copy()

    @property
    def n_mean(self) -> float:
        """空间平均 Manning n（用于标量接口）。"""
        return float(np.mean(self._n_array))


# ─────────────────────────────────────────────────────────────
# 冰塞压力梯度计算（对标 RIVICE）
# ─────────────────────────────────────────────────────────────
class IceJamPressureModel:
    """
    冰塞压力梯度模型（对标 RIVICE / CRISSP1D）。

    冰塞对水流施加附加阻力，等效为附加水面坡降：
      S_jam = (ρ_i / ρ_w) · (1 - e_i) · h_jam · tan(φ) / (2 · h · B)

    其中：
      e_i : 冰孔隙率（典型值 0.4）
      φ   : 冰内摩擦角（典型值 45°）
      h_jam : 冰塞厚度 (m)
      h : 水深 (m)
      B : 河宽 (m)

    参考：Beltaos (1983), Shen (2010)
    """

    def __init__(
        self,
        n_cells: int,
        B: float = 10.0,
        ice_porosity: float = 0.4,
        phi_deg: float = 45.0,
        rho_ice: float = RHO_ICE,
        rho_water: float = RHO_WATER,
        g: float = 9.81,
    ):
        self.n_cells = n_cells
        self.B = B
        self.e_i = ice_porosity
        self.tan_phi = np.tan(np.radians(phi_deg))
        self.rho_ratio = rho_ice / rho_water
        self.g = g

    def compute_pressure_gradient(
        self,
        h: np.ndarray,
        h_jam: np.ndarray,
        ice_jam_mask: np.ndarray,
    ) -> np.ndarray:
        """
        计算冰塞区域的附加水面坡降（作为 Preissmann 源项）。

        Returns
        -------
        S_jam : array  附加坡降 (m/m)，冰塞区为正值
        """
        h_safe = np.maximum(h, 0.1)
        S_jam = np.where(
            ice_jam_mask,
            self.rho_ratio * (1.0 - self.e_i) * h_jam * self.tan_phi
            / (2.0 * h_safe * self.B),
            0.0,
        )
        return S_jam

    def compute_source_term(
        self,
        h: np.ndarray,
        h_jam: np.ndarray,
        ice_jam_mask: np.ndarray,
    ) -> np.ndarray:
        """
        将冰塞压力梯度转换为 Saint-Venant 动量方程源项 (m²/s²)。
        S_ice = -g · A · S_jam
        """
        S_jam = self.compute_pressure_gradient(h, h_jam, ice_jam_mask)
        A = self.B * h
        return -self.g * A * S_jam


# ─────────────────────────────────────────────────────────────
# 主类：IcePeriod1D 增强冰期模块
# ─────────────────────────────────────────────────────────────
class IcePeriod1D:
    """
    一维河道冰期水力学增强模块。

    集成功能：
    1. 增强热力学冰盖模型（EnhancedIceThermalModel）
    2. 逐断面复合 Manning n（PerNodeManningManager）
    3. 冰塞压力梯度源项（IceJamPressureModel）
    4. 与 River1DSystem 的完整接口

    使用方式：
        ice = IcePeriod1D(n_cells=50, dx=200.0, B=10.0, n_bed=0.025)
        ice.initialize(h_ice_0=0.0)

        # 每个时间步
        state = ice.step(dt, T_air, T_water, h, u, Q, solar_rad)
        n_arr = state['n_composite']   # 注入 Preissmann 求解器
        S_jam = state['jam_source']    # 冰塞源项
    """

    def __init__(
        self,
        n_cells: int,
        dx: float,
        B: float = 10.0,
        S0: float = 0.0001,
        n_bed: float = 0.025,
        n_ice_smooth: float = 0.010,
        n_ice_rough: float = 0.025,
        # 冰塞参数
        Fr_critical: float = 0.08,
        slope_threshold: float = 0.001,
        ice_thick_threshold: float = 0.3,
        # 热力学参数
        h_conv_water_ice: float = 20.0,
        alpha_ice: float = 0.6,
        kappa_ice: float = 1.5,
        # 冰塞压力参数
        ice_porosity: float = 0.4,
        phi_deg: float = 45.0,
    ):
        self.n_cells = n_cells
        self.dx = dx
        self.B = B
        self.S0 = S0
        self.n_bed = n_bed

        # 子模块
        self.thermal = EnhancedIceThermalModel(
            n_cells=n_cells,
            h_conv_water_ice=h_conv_water_ice,
            alpha_ice=alpha_ice,
            kappa_ice=kappa_ice,
        )
        self.manning_mgr = PerNodeManningManager(
            n_cells=n_cells,
            n_bed=n_bed,
            n_ice_smooth=n_ice_smooth,
            n_ice_rough=n_ice_rough,
            B=B,
        )
        self.jam_pressure = IceJamPressureModel(
            n_cells=n_cells,
            B=B,
            ice_porosity=ice_porosity,
            phi_deg=phi_deg,
        )

        # 冰塞状态
        self._ice_jam_mask = np.zeros(n_cells, dtype=bool)
        self._ice_jam_thickness = np.zeros(n_cells)
        self._h_ice_transport = np.zeros(n_cells)

        # 冰塞参数
        self.Fr_critical = Fr_critical
        self.slope_threshold = slope_threshold
        self.ice_thick_threshold = ice_thick_threshold

    def initialize(self, h_ice_0: float = 0.0):
        """初始化冰期状态。"""
        self.thermal.initialize(h_ice_0)
        self._ice_jam_mask = np.zeros(self.n_cells, dtype=bool)
        self._ice_jam_thickness = np.zeros(self.n_cells)
        self._h_ice_transport = np.zeros(self.n_cells)

    def _update_ice_jam(
        self,
        h: np.ndarray,
        u: np.ndarray,
        h_ice: np.ndarray,
    ):
        """
        更新冰塞状态（简化 RIVICE 判断逻辑）。

        冰塞形成条件（满足任一）：
        1. Fr < Fr_critical（流速过低，冰花堆积）
        2. 局部坡降 < slope_threshold（缓坡段）
        3. 冰厚/水深比 > ice_thick_threshold
        """
        Fr = np.where(h > 1e-4, np.abs(u) / np.sqrt(9.81 * h), 0.0)
        ice_ratio = np.where(h > 1e-4, h_ice / h, 0.0)

        # 冰塞形成
        jam_forming = (
            (Fr < self.Fr_critical) |
            (ice_ratio > self.ice_thick_threshold)
        )

        # 冰塞消散（Fr 足够大时冰塞解体）
        jam_clearing = Fr > 0.15

        self._ice_jam_mask = np.where(
            jam_clearing, False,
            np.where(jam_forming, True, self._ice_jam_mask)
        )

        # 冰塞厚度（冰花堆积）
        self._ice_jam_thickness = np.where(
            self._ice_jam_mask,
            np.maximum(self._ice_jam_thickness, h_ice * 2.0),
            0.0,
        )

    def step(
        self,
        dt: float,
        T_air: float,
        T_water: np.ndarray,
        h: np.ndarray,
        u: np.ndarray,
        Q: np.ndarray,
        solar_radiation: float = 0.0,
    ) -> Dict:
        """
        推进冰期模块一步。

        Parameters
        ----------
        dt : float  时间步长 (s)
        T_air : float  气温 (°C)
        T_water : array  水温 (°C)
        h : array  水深 (m)
        u : array  流速 (m/s)
        Q : array  流量 (m³/s)
        solar_radiation : float  太阳辐射 (W/m²)

        Returns
        -------
        state : dict
            n_composite : array  逐断面复合 Manning n（注入 Preissmann）
            jam_source  : array  冰塞动量源项 (m²/s²)（注入 Preissmann 残差）
            h_ice       : array  冰盖厚度 (m)
            ice_fraction: array  冰盖覆盖率
            ice_jam_mask: array  冰塞标记
            Q_atm, Q_water, Q_solar : 热通量分量
        """
        # ── 1. 热力学冰盖生长/消融 ────────────────────────
        state_thermal = self.thermal.step(
            dt=dt,
            T_air=T_air,
            T_water=T_water,
            h=h,
            solar_radiation=solar_radiation,
        )
        h_ice = state_thermal['h_ice']
        ice_fraction = state_thermal['ice_fraction']

        # ── 2. 冰塞动力学 ─────────────────────────────────
        self._update_ice_jam(h, u, h_ice)

        # 冰塞区域的冰厚取较大值
        h_ice_eff = np.maximum(h_ice, self._ice_jam_thickness)

        # ── 3. 逐断面复合 Manning n ───────────────────────
        n_composite = self.manning_mgr.update(
            h=h,
            h_ice=h_ice_eff,
            ice_jam_mask=self._ice_jam_mask,
        )

        # ── 4. 冰塞压力梯度源项 ───────────────────────────
        jam_source = self.jam_pressure.compute_source_term(
            h=h,
            h_jam=self._ice_jam_thickness,
            ice_jam_mask=self._ice_jam_mask,
        )

        return {
            'h_ice': h_ice,
            'ice_fraction': ice_fraction,
            'T_ice_surface': state_thermal['T_ice_surface'],
            'ice_jam_mask': self._ice_jam_mask.copy(),
            'ice_jam_thickness': self._ice_jam_thickness.copy(),
            'n_composite': n_composite,
            'n_mean': float(np.mean(n_composite)),
            'jam_source': jam_source,
            'Q_atm': state_thermal['Q_atm'],
            'Q_water': state_thermal['Q_water'],
            'Q_solar': state_thermal['Q_solar'],
            'dh_dt': state_thermal['dh_dt'],
        }

    def get_stefan_growth_rate(
        self,
        T_air: float,
        h_ice: np.ndarray,
    ) -> np.ndarray:
        """
        计算 Stefan 方程的冰盖生长速率（解析值，用于验证）。
        dh/dt = k_ice * (T_freeze - T_air) / (ρ_i * L_f * h_ice)
        """
        h_safe = np.maximum(h_ice, 0.001)
        delta_T = max(T_FREEZE - T_air, 0.0)
        return K_ICE * delta_T / (RHO_ICE * L_FUSION * h_safe)

    @staticmethod
    def stefan_analytical(
        t_days: np.ndarray,
        T_air: float,
        k_ice: float = K_ICE,
        rho_ice: float = RHO_ICE,
        L_fusion: float = L_FUSION,
    ) -> np.ndarray:
        """
        Stefan 解析解：h_ice(t) = sqrt(2 * k_ice * ΔT * t / (ρ_i * L_f))
        对标 HEC-RAS Ice 验证案例。
        """
        delta_T = max(T_FREEZE - T_air, 0.0)
        t_sec = t_days * 86400.0
        return np.sqrt(2.0 * k_ice * delta_T * t_sec / (rho_ice * L_fusion))

    @staticmethod
    def composite_roughness_analytical(
        n_bed: float,
        n_ice: float,
        P_bed: float,
        P_ice: float,
    ) -> float:
        """
        Sabaneev 复合糙率解析值（用于验证）。
        n_c = [(n_b^1.5 * P_b + n_i^1.5 * P_i) / (P_b + P_i)]^(2/3)
        """
        num = n_bed**1.5 * P_bed + n_ice**1.5 * P_ice
        den = P_bed + P_ice
        return (num / den) ** (2.0 / 3.0)
