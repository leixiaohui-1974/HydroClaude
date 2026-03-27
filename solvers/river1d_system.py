#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
River1DSystem — 一维河道水动力-水质-冰期耦合系统
=======================================================
对标软件：
  - 水动力：HEC-RAS 1D, MIKE 11 HD
  - 水质：QUAL2K, CE-QUAL-RIV1, WASP 1D
  - 冰期：HEC-RAS Ice, MIKE 11 Ice, RIVICE, CRISSP1D

集成架构（算子分裂 Strang Splitting）：
  每个时间步 Δt 分三个半步：
    1. 水动力半步 (Δt/2)：Preissmann 求解 h, Q
       - 若有冰盖，用复合糙率替换 Manning n
       - 若有水工构筑物，施加源项
    2. 水质/冰期整步 (Δt)：
       a. 水温 ADR（对流-扩散-热交换）
       b. 冰盖生长/消融（Stefan 方程）
       c. 冰塞动力学（Froude 判断 + 堆积）
       d. DO-BOD（Streeter-Phelps + 复氧）
       e. 营养盐（N/P 循环）
       f. 藻类（光合作用 + 呼吸）
    3. 水动力半步 (Δt/2)：同步骤1

水质方程（对标 QUAL2K / CE-QUAL-RIV1）：
  ∂C/∂t + u·∂C/∂x = ∂/∂x(DL·∂C/∂x) + R(C, T, DO, ...)

冰盖方程（对标 HEC-RAS Ice / MIKE 11 Ice）：
  Stefan: ρi·Lf·dh_ice/dt = ki·(Tf - T_air)/h_ice - kw·(T_water - Tf)/δ_bl
  复合糙率: n_c = [(n_b^1.5·P_b + n_i^1.5·P_i)/(P_b+P_i)]^(2/3)  [Sabaneev]

作者: HydroClaude Team
日期: 2026-03-27
"""

import numpy as np
from typing import Dict, List, Optional, Tuple, Callable
import time

# ── 水动力求解器 ──────────────────────────────────────────────
from solvers.preissmann_unsteady_solver import PreissmannUnsteadySolver

# ── 水质模块 ──────────────────────────────────────────────────
from solvers.water_temperature import WaterTemperatureSolver
from solvers.dissolved_oxygen import DissolvedOxygenSolver
from solvers.nutrients import NutrientsSolver
from solvers.phytoplankton import PhytoplanktonSolver

# ── 冰期模块 ──────────────────────────────────────────────────
from solvers.ice_cover import IceCoverSolver
from solvers.ice_hydraulics import IceCoveredChannelHydraulics, CompositeRoughnessMethod
from solvers.ice_jam import IceJamSolver
from solvers.frazil_ice import FrazilIceSolver


# ─────────────────────────────────────────────────────────────
# 辅助：QUAL2K 风格的 DO 饱和度公式
# ─────────────────────────────────────────────────────────────
def do_saturation_qual2k(T: np.ndarray, elevation_m: float = 0.0) -> np.ndarray:
    """
    QUAL2K / APHA 标准溶解氧饱和浓度公式（Benson & Krause, 1984）。
    高程修正采用 QUAL2K 方法。

    Parameters
    ----------
    T : array  水温 (°C)
    elevation_m : float  海拔高程 (m)，用于气压修正

    Returns
    -------
    DO_sat : array  饱和 DO (mg/L)
    """
    T_K = T + 273.15
    ln_DO = (
        -139.34411
        + 1.575701e5 / T_K
        - 6.642308e7 / T_K**2
        + 1.2438e10 / T_K**3
        - 8.621949e11 / T_K**4
    )
    DO_sat = np.exp(ln_DO)
    # 气压修正（高程）
    P_atm = np.exp(-elevation_m / 8435.0)   # 标准大气压比值
    DO_sat *= P_atm
    return np.maximum(DO_sat, 0.0)


# ─────────────────────────────────────────────────────────────
# 辅助：QUAL2K 风格的 BOD 衰减
# ─────────────────────────────────────────────────────────────
def bod_decay_qual2k(
    BOD: np.ndarray,
    T: np.ndarray,
    kd_20: float = 0.2,
    ks_20: float = 0.05,
    theta_kd: float = 1.047,
    theta_ks: float = 1.024,
) -> np.ndarray:
    """
    QUAL2K BOD 衰减速率（含沉降项）。
    R_BOD = -(kd + ks) * BOD  (mg/L/day)
    """
    kd = kd_20 * theta_kd ** (T - 20.0)
    ks = ks_20 * theta_ks ** (T - 20.0)
    return -(kd + ks) * BOD


# ─────────────────────────────────────────────────────────────
# 辅助：QUAL2K 风格的复氧系数 Ka（O'Connor-Dobbins）
# ─────────────────────────────────────────────────────────────
def reaeration_oconnor_dobbins(
    u: np.ndarray,
    h: np.ndarray,
    T: np.ndarray,
    theta_ka: float = 1.024,
) -> np.ndarray:
    """
    O'Connor-Dobbins (1958) 复氧系数，QUAL2K 默认公式。
    Ka_20 = 3.93 * u^0.5 / h^1.5  (1/day)
    温度修正: Ka(T) = Ka_20 * 1.024^(T-20)
    """
    u_safe = np.maximum(np.abs(u), 0.01)
    h_safe = np.maximum(h, 0.1)
    Ka_20 = 3.93 * u_safe**0.5 / h_safe**1.5
    Ka = Ka_20 * theta_ka ** (T - 20.0)
    return Ka


# ─────────────────────────────────────────────────────────────
# 辅助：冰盖下的复合 Manning n（Sabaneev 公式）
# ─────────────────────────────────────────────────────────────
def composite_manning_sabaneev(
    n_bed: float,
    n_ice: np.ndarray,
    h: np.ndarray,
    B: float,
    h_ice: np.ndarray,
) -> np.ndarray:
    """
    Sabaneev (1956) 复合糙率公式，HEC-RAS Ice 和 MIKE 11 Ice 均采用此公式。
    n_c = [(n_b^1.5 * P_b + n_i^1.5 * P_i) / (P_b + P_i)]^(2/3)

    Parameters
    ----------
    n_bed : float      渠床 Manning n
    n_ice : array      冰底 Manning n（各断面可不同）
    h     : array      水深 (m)
    B     : float      渠宽 (m)（矩形断面）
    h_ice : array      冰盖厚度 (m)

    Returns
    -------
    n_c : array  复合 Manning n
    """
    # 矩形断面：P_bed = B + 2h，P_ice = B（冰盖宽度 ≈ 渠宽）
    P_bed = B + 2.0 * np.maximum(h, 1e-3)
    P_ice = np.where(h_ice > 0.01, B, 0.0)   # 仅有冰盖时才有冰底湿周

    has_ice = P_ice > 0.0
    n_c = np.full_like(h, n_bed)

    if np.any(has_ice):
        num = n_bed**1.5 * P_bed + n_ice**1.5 * P_ice
        den = P_bed + P_ice + 1e-12
        n_c = np.where(has_ice, (num / den) ** (2.0 / 3.0), n_bed)

    return n_c


# ─────────────────────────────────────────────────────────────
# 主类：River1DSystem
# ─────────────────────────────────────────────────────────────
class River1DSystem:
    """
    一维河道水动力-水质-冰期耦合系统。

    对标软件功能矩阵
    ─────────────────────────────────────────────────────────
    功能                    HEC-RAS  QUAL2K  CE-QUAL-RIV1  MIKE11  HydroClaude
    ─────────────────────────────────────────────────────────
    Saint-Venant (非恒定)    ✓        ✓        ✓            ✓        ✓ (Preissmann)
    水温 ADR                 ✓        ✓        ✓            ✓        ✓
    DO-BOD (Streeter-Phelps) ✓        ✓        ✓            ✓        ✓
    复氧 (O'Connor-Dobbins)  ✓        ✓        ✓            ✓        ✓
    营养盐 N/P 循环          -        ✓        ✓            ✓        ✓
    藻类 (Monod)             -        ✓        ✓            ✓        ✓
    冰盖 Stefan              ✓        -        -            ✓        ✓
    复合糙率 (Sabaneev)      ✓        -        -            ✓        ✓
    冰塞动力学               ✓        -        -            ✓        ✓
    冰花 (Frazil)            -        -        -            ✓        ✓
    水工构筑物               ✓        -        -            ✓        ✓ (闸/泵/涵)
    算子分裂耦合             -        -        -            -        ✓ (Strang)
    ─────────────────────────────────────────────────────────
    """

    def __init__(
        self,
        # ── 几何参数 ──
        length: float,
        nx: int,
        B: float,
        S0: float,
        n_bed: float = 0.025,
        # ── 水动力参数 ──
        theta: float = 0.6,
        structures: Optional[list] = None,
        # ── 水质开关 ──
        enable_temperature: bool = True,
        enable_do: bool = True,
        enable_nutrients: bool = True,
        enable_phytoplankton: bool = True,
        # ── 冰期开关 ──
        enable_ice_cover: bool = True,
        enable_ice_jam: bool = True,
        enable_frazil: bool = False,   # 计算量较大，默认关闭
        # ── 水质参数（QUAL2K 默认值）──
        kd_20: float = 0.2,           # BOD 衰减系数 @ 20°C (1/day)
        ks_20: float = 0.05,          # BOD 沉降系数 @ 20°C (1/day)
        SOD_20: float = 1.0,          # 底泥耗氧 @ 20°C (g/m²/day)
        kn_20: float = 0.1,           # 硝化系数 @ 20°C (1/day)
        kdn_20: float = 0.09,         # 反硝化系数 @ 20°C (1/day)
        mu_max_20: float = 2.0,       # 藻类最大生长率 @ 20°C (1/day)
        elevation_m: float = 0.0,     # 海拔高程 (m)，用于 DO 饱和度修正
        # ── 冰期参数 ──
        n_ice_smooth: float = 0.010,  # 光滑冰底糙率
        n_ice_rough: float = 0.025,   # 粗糙冰底/冰塞糙率
        # ── 数值参数 ──
        use_numba: bool = True,
        strang_splitting: bool = True,  # True: Strang 二阶分裂；False: Lie 一阶分裂
    ):
        self.length = length
        self.nx = nx
        self.B = B
        self.S0 = S0
        self.n_bed = n_bed
        self.elevation_m = elevation_m
        self.strang_splitting = strang_splitting

        # 冰期参数
        self.n_ice_smooth = n_ice_smooth
        self.n_ice_rough = n_ice_rough

        # 水质参数
        self.kd_20 = kd_20
        self.ks_20 = ks_20
        self.SOD_20 = SOD_20

        # 空间网格
        self.x = np.linspace(0, length, nx)
        self.dx = length / (nx - 1)

        # ── 水动力求解器 ──────────────────────────────────────
        self.hydro = PreissmannUnsteadySolver(
            length=length,
            nx=nx,
            B=B,
            S0=S0,
            n=n_bed,
            theta=theta,
            structures=structures or [],
        )

        # ── 水质求解器 ────────────────────────────────────────
        self.enable_temperature = enable_temperature
        self.enable_do = enable_do
        self.enable_nutrients = enable_nutrients
        self.enable_phytoplankton = enable_phytoplankton

        if enable_temperature:
            self.temp_solver = WaterTemperatureSolver(
                n_cells=nx, dx=self.dx, use_numba=use_numba
            )
        if enable_do:
            self.do_solver = DissolvedOxygenSolver(
                n_cells=nx, dx=self.dx,
                kd_20=kd_20, SOD_20=SOD_20,
                use_numba=use_numba,
            )
        if enable_nutrients:
            self.nutrients_solver = NutrientsSolver(
                n_cells=nx, dx=self.dx,
                kn_20=kn_20, kdn_20=kdn_20,
                use_numba=use_numba,
            )
        if enable_phytoplankton:
            self.algae_solver = PhytoplanktonSolver(
                n_cells=nx, dx=self.dx,
                mu_max_20=mu_max_20,
                use_numba=use_numba,
            )

        # ── 冰期求解器 ────────────────────────────────────────
        self.enable_ice_cover = enable_ice_cover
        self.enable_ice_jam = enable_ice_jam
        self.enable_frazil = enable_frazil

        if enable_ice_cover:
            self.ice_cover = IceCoverSolver(n_cells=nx)
        if enable_ice_jam:
            self.ice_jam = IceJamSolver(n_cells=nx, dx=self.dx)
        if enable_frazil:
            self.frazil = FrazilIceSolver(
                n_cells=nx, dx=self.dx, use_numba=use_numba
            )

        self.ice_hydraulics = IceCoveredChannelHydraulics(
            n_bed=n_bed,
            n_ice_smooth=n_ice_smooth,
            n_ice_rough=n_ice_rough,
        )

        # ── 状态变量 ──────────────────────────────────────────
        # 水动力
        self._h = np.ones(nx) * 1.0      # 水深 (m)
        self._Q = np.ones(nx) * 1.0      # 流量 (m³/s)
        # 水温
        self._T = np.ones(nx) * 15.0     # 水温 (°C)
        # DO-BOD
        self._DO = np.ones(nx) * 8.0     # 溶解氧 (mg/L)
        self._BOD = np.ones(nx) * 2.0    # BOD (mg/L)
        # 营养盐
        self._NH4 = np.ones(nx) * 0.5    # 氨氮 (mg/L)
        self._NO3 = np.ones(nx) * 2.0    # 硝态氮 (mg/L)
        self._PO4 = np.ones(nx) * 0.1    # 磷酸盐 (mg/L)
        # 藻类
        self._Chla = np.ones(nx) * 10.0  # 叶绿素 a (μg/L)
        # 冰期
        self._h_ice = np.zeros(nx)       # 冰盖厚度 (m)
        self._T_frazil = np.zeros(nx)    # 冰花浓度 (m³/m³)
        self._ice_jam_mask = np.zeros(nx, dtype=bool)

        # ── 时间 ──────────────────────────────────────────────
        self.t = 0.0
        self.n_steps = 0
        self._wallclock = 0.0

        # ── 边界条件回调 ──────────────────────────────────────
        # 可由用户设置为时间函数 f(t) → value
        self.bc_Q_upstream: Optional[Callable] = None
        self.bc_h_downstream: Optional[Callable] = None
        self.bc_T_upstream: Optional[Callable] = None
        self.bc_DO_upstream: Optional[Callable] = None
        self.bc_BOD_upstream: Optional[Callable] = None
        self.bc_T_air: Optional[Callable] = None       # 气温 f(t) → °C
        self.bc_solar_rad: Optional[Callable] = None   # 太阳辐射 f(t) → W/m²

    # ─────────────────────────────────────────────────────────
    # 初始化
    # ─────────────────────────────────────────────────────────
    def initialize(
        self,
        h0: float = 1.0,
        Q0: float = 1.0,
        T0: float = 15.0,
        DO0: float = 8.0,
        BOD0: float = 2.0,
        NH4_0: float = 0.5,
        NO3_0: float = 2.0,
        PO4_0: float = 0.1,
        Chla_0: float = 10.0,
        h_ice_0: float = 0.0,
        # 也可传入数组
        h_arr: Optional[np.ndarray] = None,
        Q_arr: Optional[np.ndarray] = None,
        T_arr: Optional[np.ndarray] = None,
        DO_arr: Optional[np.ndarray] = None,
        BOD_arr: Optional[np.ndarray] = None,
    ):
        """初始化所有状态变量，并同步到各子求解器。"""
        def _fill(arr, val, n):
            return arr.copy() if arr is not None else np.full(n, val)

        self._h = _fill(h_arr, h0, self.nx)
        self._Q = _fill(Q_arr, Q0, self.nx)
        self._T = _fill(T_arr, T0, self.nx)
        self._DO = _fill(DO_arr, DO0, self.nx)
        self._BOD = _fill(BOD_arr, BOD0, self.nx)
        self._NH4 = np.full(self.nx, NH4_0)
        self._NO3 = np.full(self.nx, NO3_0)
        self._PO4 = np.full(self.nx, PO4_0)
        self._Chla = np.full(self.nx, Chla_0)
        self._h_ice = np.full(self.nx, h_ice_0)

        # 同步到水动力求解器
        self.hydro.initialize_state(h_initial=h0, Q_initial=Q0)
        if h_arr is not None or Q_arr is not None:
            self.hydro.U_old = self.hydro.pack_state(self._h, self._Q)

        # 同步到水质求解器
        if self.enable_temperature:
            self.temp_solver.initialize(self._T)
        if self.enable_do:
            self.do_solver.DO = self._DO.copy()
            self.do_solver.BOD = self._BOD.copy()
        if self.enable_nutrients:
            self.nutrients_solver.NH4 = self._NH4.copy()
            self.nutrients_solver.NO3 = self._NO3.copy()
            self.nutrients_solver.PO4 = self._PO4.copy()
        if self.enable_phytoplankton:
            self.algae_solver.Chla = self._Chla.copy()

        # 同步到冰期求解器
        if self.enable_ice_cover:
            self.ice_cover.h_ice = self._h_ice.copy()

        self.t = 0.0
        self.n_steps = 0

    # ─────────────────────────────────────────────────────────
    # 边界条件设置
    # ─────────────────────────────────────────────────────────
    def set_boundary_conditions(
        self,
        Q_upstream: Optional[float] = None,
        h_downstream: Optional[float] = None,
        T_upstream: Optional[float] = None,
        DO_upstream: Optional[float] = None,
        BOD_upstream: Optional[float] = None,
        T_air: Optional[float] = None,
        solar_rad: Optional[float] = None,
        # 也可传入时间函数
        Q_upstream_func: Optional[Callable] = None,
        h_downstream_func: Optional[Callable] = None,
        T_air_func: Optional[Callable] = None,
    ):
        """设置边界条件（常数或时间函数）。"""
        if Q_upstream is not None:
            self.bc_Q_upstream = lambda t: Q_upstream
        if Q_upstream_func is not None:
            self.bc_Q_upstream = Q_upstream_func
        if h_downstream is not None:
            self.bc_h_downstream = lambda t: h_downstream
        if h_downstream_func is not None:
            self.bc_h_downstream = h_downstream_func
        if T_upstream is not None:
            self.bc_T_upstream = lambda t: T_upstream
        if DO_upstream is not None:
            self.bc_DO_upstream = lambda t: DO_upstream
        if BOD_upstream is not None:
            self.bc_BOD_upstream = lambda t: BOD_upstream
        if T_air is not None:
            self.bc_T_air = lambda t: T_air
        if T_air_func is not None:
            self.bc_T_air = T_air_func
        if solar_rad is not None:
            self.bc_solar_rad = lambda t: solar_rad

    # ─────────────────────────────────────────────────────────
    # 内部：获取当前边界值
    # ─────────────────────────────────────────────────────────
    def _get_bc(self, func, default):
        return func(self.t) if func is not None else default

    # ─────────────────────────────────────────────────────────
    # 内部：更新水动力求解器的 Manning n（冰期修正）
    # ─────────────────────────────────────────────────────────
    def _update_hydro_roughness(self):
        """
        根据当前冰盖厚度，用 Sabaneev 复合糙率更新 Preissmann 求解器的 Manning n。
        冰塞区域使用粗糙冰底糙率。
        """
        if not self.enable_ice_cover:
            return

        h_ice = self._h_ice
        ice_jam = self._ice_jam_mask if self.enable_ice_jam else np.zeros(self.nx, dtype=bool)

        # 冰底糙率：冰塞区用粗糙值，普通冰盖用光滑值
        n_ice = np.where(ice_jam, self.n_ice_rough, self.n_ice_smooth)

        n_c = composite_manning_sabaneev(
            n_bed=self.n_bed,
            n_ice=n_ice,
            h=self._h,
            B=self.B,
            h_ice=h_ice,
        )

        # 更新 Preissmann 求解器的 Manning n（取空间平均作为全局值）
        # 注：Preissmann 求解器当前为标量 n；此处用空间平均近似
        # 后续可扩展为逐断面 n 数组
        self.hydro.n = float(np.mean(n_c))

    # ─────────────────────────────────────────────────────────
    # 内部：水动力半步
    # ─────────────────────────────────────────────────────────
    def _hydro_step(self, dt: float):
        """推进水动力半步，更新 h, Q。"""
        # 更新边界条件
        Q_up = self._get_bc(self.bc_Q_upstream, self._Q[0])
        h_dn = self._get_bc(self.bc_h_downstream, self._h[-1])
        self.hydro.set_boundary_conditions(
            Q_upstream=Q_up,
            h_downstream=h_dn,
        )

        # 冰期修正 Manning n
        self._update_hydro_roughness()

        # 求解
        U_new = self.hydro.solve_step(self.hydro.U_old, dt)
        self.hydro.U_old = U_new
        self._h, self._Q = self.hydro.unpack_state(U_new)
        self._h = np.maximum(self._h, 1e-6)

    # ─────────────────────────────────────────────────────────
    # 内部：水质整步（算子分裂内的完整 Δt）
    # ─────────────────────────────────────────────────────────
    def _wq_ice_step(self, dt: float):
        """推进水质与冰期整步。"""
        h = self._h
        u = np.where(h > 1e-4, self._Q / (self.B * h), 0.0)
        dt_day = dt / 86400.0

        # ── Step 1: 水温 ────────────────────────────────────
        T_air = self._get_bc(self.bc_T_air, 20.0)
        I_0 = self._get_bc(self.bc_solar_rad, 200.0)   # W/m²

        if self.enable_temperature:
            T_new = self.temp_solver.step(
                dt=dt,
                u=u,
                h=h,
                T_air=T_air,
                solar_radiation=I_0,
                wind_speed=2.0,
                relative_humidity=0.7,
                ice_cover_thickness=self._h_ice if self.enable_ice_cover else None,
                ice_cover_fraction=np.where(self._h_ice > 0.01, 1.0, 0.0) if self.enable_ice_cover else None,
            )
            self._T = T_new if isinstance(T_new, np.ndarray) else T_new
        T = self._T

        # ── Step 2: 冰盖生长/消融（Stefan）────────────────
        if self.enable_ice_cover:
            state_ice = self.ice_cover.step(
                dt=dt,
                T_air=T_air,
                T_water=T,
            )
            self._h_ice = state_ice['h_ice']
            ice_cover_fraction = state_ice.get('ice_fraction', np.where(self._h_ice > 0.01, 1.0, 0.0))
        else:
            ice_cover_fraction = np.zeros(self.nx)

        # ── Step 3: 冰塞动力学 ──────────────────────────────
        if self.enable_ice_jam:
            S0_arr = np.full(self.nx, self.S0)
            state_jam = self.ice_jam.step(
                dt=dt,
                h=h,
                u=u,
                Q=self._Q,
                S0=S0_arr,
                h_ice_input=self._h_ice,
                manning_n=self.hydro.n,
                width=self.B,
            )
            self._ice_jam_mask = state_jam.get('ice_jam_mask', self._ice_jam_mask)
            # 冰塞堆积增加冰厚
            self._h_ice = np.maximum(
                self._h_ice,
                state_jam.get('ice_jam_thickness', self._h_ice)
            )

        # ── Step 4: 冰花（可选）────────────────────────────
        if self.enable_frazil:
            state_frazil = self.frazil.step(
                dt=dt,
                T=T,
                u=u,
                h=h,
            )
            self._T_frazil = state_frazil.get('total_volume', self._T_frazil)

        # ── Step 5: DO-BOD（QUAL2K / Streeter-Phelps）──────
        if self.enable_do:
            DO_sat = do_saturation_qual2k(T, self.elevation_m)
            Ka = reaeration_oconnor_dobbins(u, h, T)

            # 冰盖减弱复氧（冰盖覆盖率降低气-水界面）
            Ka_eff = Ka * (1.0 - 0.9 * ice_cover_fraction)

            # BOD 衰减
            R_BOD = bod_decay_qual2k(self._BOD, T, self.kd_20, self.ks_20)
            kd_T = self.kd_20 * 1.047 ** (T - 20.0)

            # DO 方程（QUAL2K 标准）：
            # dDO/dt = Ka*(DO_sat - DO) - kd*BOD - SOD/h
            SOD_T = self.SOD_20 * 1.065 ** (T - 20.0) / 1000.0  # g/m²/day → mg/L/day（÷h）
            SOD_flux = SOD_T / np.maximum(h, 0.1)

            dDO = (Ka_eff * (DO_sat - self._DO) + R_BOD * kd_T / (self.kd_20 + self.ks_20 + 1e-12) - SOD_flux) * dt_day
            dBOD = R_BOD * dt_day

            # 对流-扩散（用 ADR 求解器）
            DO_up = self._get_bc(self.bc_DO_upstream, self._DO[0])
            BOD_up = self._get_bc(self.bc_BOD_upstream, self._BOD[0])

            state_do = self.do_solver.step(
                dt=dt, u=u, h=h, T=T,
                manning_n=self.hydro.n,
                ice_cover_fraction=ice_cover_fraction,
            )
            # 叠加反应项（算子分裂：ADR 传输 + 额外反应修正）
            self._DO = state_do['DO'] + dDO
            self._BOD = state_do['BOD'] + dBOD
            # 同步到 do_solver 内部状态
            self.do_solver.DO = self._DO.copy()
            self.do_solver.BOD = self._BOD.copy()
            self._DO = np.clip(self._DO, 0.0, DO_sat * 1.1)
            self._BOD = np.maximum(self._BOD, 0.0)

        # ── Step 6: 营养盐 N/P 循环 ─────────────────────────
        if self.enable_nutrients:
            DO_for_nut = self._DO if self.enable_do else np.full(self.nx, 8.0)
            state_nut = self.nutrients_solver.step(
                dt=dt, u=u, h=h, T=T, DO=DO_for_nut
            )
            self._NH4 = state_nut['NH4']
            self._NO3 = state_nut['NO3']
            self._PO4 = state_nut['PO4']

        # ── Step 7: 藻类（Monod 动力学）────────────────────
        if self.enable_phytoplankton:
            NH4 = self._NH4 if self.enable_nutrients else np.full(self.nx, 0.5)
            NO3 = self._NO3 if self.enable_nutrients else np.full(self.nx, 2.0)
            PO4 = self._PO4 if self.enable_nutrients else np.full(self.nx, 0.1)
            state_alg = self.algae_solver.step(
                dt=dt, u=u, h=h, T=T, I_0=I_0,
                NH4=NH4, NO3=NO3, PO4=PO4,
                ice_cover_fraction=ice_cover_fraction,
            )
            self._Chla = state_alg['Chla']

            # 藻类光合作用对 DO 的贡献
            if self.enable_do:
                self._DO += state_alg.get('DO_production', np.zeros(self.nx)) * dt_day
                self._DO = np.clip(self._DO, 0.0, 20.0)

    # ─────────────────────────────────────────────────────────
    # 公开：单步推进
    # ─────────────────────────────────────────────────────────
    def step(self, dt: float) -> Dict:
        """
        推进一个时间步 Δt。

        采用 Strang 二阶算子分裂（若 strang_splitting=True）：
          H(Δt/2) → WQ(Δt) → H(Δt/2)
        或 Lie 一阶分裂（若 strang_splitting=False）：
          H(Δt) → WQ(Δt)

        Returns
        -------
        state : dict  当前所有状态变量
        """
        t0 = time.time()

        if self.strang_splitting:
            self._hydro_step(dt / 2.0)
            self._wq_ice_step(dt)
            self._hydro_step(dt / 2.0)
        else:
            self._hydro_step(dt)
            self._wq_ice_step(dt)

        self.t += dt
        self.n_steps += 1
        self._wallclock += time.time() - t0

        return self.get_state()

    # ─────────────────────────────────────────────────────────
    # 公开：批量运行
    # ─────────────────────────────────────────────────────────
    def run(
        self,
        t_end: float,
        dt: float,
        output_interval: int = 1,
        progress: bool = False,
    ) -> Dict:
        """
        从当前时刻运行到 t_end。

        Parameters
        ----------
        t_end : float          终止时刻 (s)
        dt    : float          时间步长 (s)
        output_interval : int  每隔多少步输出一次
        progress : bool        是否打印进度

        Returns
        -------
        results : dict  时间序列结果
        """
        times = []
        states = []

        step_count = 0
        while self.t < t_end - 1e-10:
            dt_actual = min(dt, t_end - self.t)
            state = self.step(dt_actual)
            step_count += 1
            if step_count % output_interval == 0:
                times.append(self.t)
                states.append({k: v.copy() if isinstance(v, np.ndarray) else v
                                for k, v in state.items()})
            if progress and step_count % 100 == 0:
                print(f"  t={self.t:.1f}s / {t_end:.1f}s  "
                      f"({100*self.t/t_end:.1f}%)  "
                      f"steps={self.n_steps}")

        return {
            'times': np.array(times),
            'states': states,
            'n_steps': self.n_steps,
            'wallclock': self._wallclock,
        }

    # ─────────────────────────────────────────────────────────
    # 公开：获取当前状态
    # ─────────────────────────────────────────────────────────
    def get_state(self) -> Dict:
        """返回当前所有状态变量的字典。"""
        u = np.where(self._h > 1e-4, self._Q / (self.B * self._h), 0.0)
        Fr = np.where(self._h > 1e-4, np.abs(u) / np.sqrt(9.81 * self._h), 0.0)
        DO_sat = do_saturation_qual2k(self._T, self.elevation_m)

        state = {
            # 时间
            't': self.t,
            'x': self.x.copy(),
            # 水动力
            'h': self._h.copy(),
            'Q': self._Q.copy(),
            'u': u,
            'Fr': Fr,
            # 水温
            'T': self._T.copy(),
            # DO-BOD
            'DO': self._DO.copy(),
            'BOD': self._BOD.copy(),
            'DO_sat': DO_sat,
            'DO_deficit': DO_sat - self._DO,
            # 营养盐
            'NH4': self._NH4.copy(),
            'NO3': self._NO3.copy(),
            'PO4': self._PO4.copy(),
            'TN': self._NH4 + self._NO3,
            'TP': self._PO4.copy(),
            # 藻类
            'Chla': self._Chla.copy(),
            # 冰期
            'h_ice': self._h_ice.copy(),
            'ice_cover_fraction': np.where(self._h_ice > 0.01, 1.0, 0.0),
            'ice_jam_mask': self._ice_jam_mask.copy(),
            # 复合糙率
            'n_composite': self.hydro.n,
            # 性能
            'n_steps': self.n_steps,
            'wallclock': self._wallclock,
        }
        return state

    # ─────────────────────────────────────────────────────────
    # 公开：获取 Streeter-Phelps 解析解（用于验证）
    # ─────────────────────────────────────────────────────────
    @staticmethod
    def streeter_phelps_analytical(
        x: np.ndarray,
        u: float,
        DO_0: float,
        BOD_0: float,
        DO_sat: float,
        Ka_20: float,
        kd_20: float,
        T: float = 20.0,
    ) -> Tuple[np.ndarray, np.ndarray]:
        """
        Streeter-Phelps (1925) 解析解，对标 QUAL2K 验证案例。

        dDO_deficit/dt = kd * BOD - Ka * D
        dBOD/dt = -kd * BOD

        Parameters
        ----------
        x       : array  沿程距离 (m)
        u       : float  流速 (m/s)
        DO_0    : float  上游 DO (mg/L)
        BOD_0   : float  上游 BOD (mg/L)
        DO_sat  : float  饱和 DO (mg/L)
        Ka_20   : float  复氧系数 @ 20°C (1/day)
        kd_20   : float  BOD 衰减系数 @ 20°C (1/day)
        T       : float  水温 (°C)

        Returns
        -------
        DO  : array  沿程 DO (mg/L)
        BOD : array  沿程 BOD (mg/L)
        """
        kd = kd_20 * 1.047 ** (T - 20.0)
        Ka = Ka_20 * 1.024 ** (T - 20.0)
        t = x / (u * 86400.0)   # 转换为天

        D_0 = DO_sat - DO_0
        BOD = BOD_0 * np.exp(-kd * t)
        D = (kd * BOD_0 / (Ka - kd)) * (np.exp(-kd * t) - np.exp(-Ka * t)) + D_0 * np.exp(-Ka * t)
        DO = DO_sat - D
        return np.maximum(DO, 0.0), BOD

    # ─────────────────────────────────────────────────────────
    # 公开：获取 Stefan 解析解（用于验证）
    # ─────────────────────────────────────────────────────────
    @staticmethod
    def stefan_analytical(
        t_days: np.ndarray,
        T_air: float,
        T_freeze: float = 0.0,
        k_ice: float = 2.2,
        rho_ice: float = 917.0,
        L_fusion: float = 3.34e5,
    ) -> np.ndarray:
        """
        Stefan 冰盖厚度解析解，对标 HEC-RAS Ice 验证案例。
        h_ice(t) = sqrt(2 * k_ice * (T_freeze - T_air) * t / (rho_ice * L_fusion))

        Parameters
        ----------
        t_days  : array  时间 (天)
        T_air   : float  气温 (°C)，应 < T_freeze
        T_freeze: float  冰点 (°C)
        k_ice   : float  冰导热系数 (W/(m·K))
        rho_ice : float  冰密度 (kg/m³)
        L_fusion: float  融化潜热 (J/kg)

        Returns
        -------
        h_ice : array  冰盖厚度 (m)
        """
        delta_T = max(T_freeze - T_air, 0.0)
        t_sec = t_days * 86400.0
        h_ice = np.sqrt(2.0 * k_ice * delta_T * t_sec / (rho_ice * L_fusion))
        return h_ice
