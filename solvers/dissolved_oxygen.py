#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
溶解氧(DO)模拟模块 - Dissolved Oxygen Solver

物理模型：
    ∂DO/∂t + u·∂DO/∂x = DL·∂²DO/∂x² + Ka·(DO_sat - DO) - kd·BOD - SOD/h

    其中:
    - DO: 溶解氧浓度 (mg/L)
    - DO_sat: 饱和DO浓度 (mg/L), 温度依赖
    - Ka: 再曝气系数 (1/day), 流速和水深依赖
    - kd: BOD衰减系数 (1/day), 温度依赖
    - BOD: 生化需氧量 (mg/L)
    - SOD: 底泥耗氧速率 (g/m²/day)

对标: QUAL2K DO模块, WASP DO模型

作者: HydroClaude Team
日期: 2025-11-02
"""

import numpy as np
from typing import Dict, Optional, Tuple
from .water_quality_adr import ADRSolver


class DissolvedOxygenSolver(ADRSolver):
    """
    溶解氧求解器

    包含完整的DO过程:
    1. 大气再曝气
    2. BOD耗氧
    3. 底泥耗氧 (SOD)
    4. 硝化耗氧
    5. 光合作用产氧 (可选)
    6. 冰盖影响
    """

    def __init__(
        self,
        n_cells: int,
        dx: float,
        kd_20: float = 0.2,      # BOD衰减系数 @ 20°C (1/day)
        SOD_20: float = 1.0,     # 底泥耗氧 @ 20°C (g/m²/day)
        use_numba: bool = True
    ):
        """
        初始化DO求解器

        Parameters:
        -----------
        n_cells : int
            网格单元数
        dx : float
            网格间距 (m)
        kd_20 : float
            BOD衰减系数 @ 20°C (1/day)
        SOD_20 : float
            底泥耗氧速率 @ 20°C (g/m²/day)
        use_numba : bool
            是否使用Numba加速
        """
        super().__init__(n_cells, dx, use_numba=use_numba, use_muscl=True)

        # 状态变量
        self.DO = np.ones(n_cells) * 8.0   # 初始DO = 8 mg/L
        self.BOD = np.ones(n_cells) * 2.0  # 初始BOD = 2 mg/L

        # DO参数
        self.kd_20 = kd_20
        self.SOD_20 = SOD_20

        # 温度系数
        self.theta_ka = 1.024   # 再曝气温度系数
        self.theta_kd = 1.047   # BOD衰减温度系数
        self.theta_SOD = 1.065  # SOD温度系数

    def initialize(
        self,
        DO_initial: np.ndarray,
        BOD_initial: Optional[np.ndarray] = None
    ):
        """
        初始化DO和BOD浓度

        Parameters:
        -----------
        DO_initial : array
            初始DO浓度 (mg/L)
        BOD_initial : array, optional
            初始BOD浓度 (mg/L)
        """
        self.DO = DO_initial.copy()
        if BOD_initial is not None:
            self.BOD = BOD_initial.copy()

    def compute_DO_saturation(self, T: np.ndarray) -> np.ndarray:
        """
        计算饱和DO浓度

        使用Elmore & Hayes (1960) 公式:
            DO_sat = 14.652 - 0.41022*T + 0.007991*T² - 0.000077774*T³

        Parameters:
        -----------
        T : array
            水温 (°C)

        Returns:
        --------
        DO_sat : array
            饱和DO浓度 (mg/L)
        """
        DO_sat = (14.652
                  - 0.41022 * T
                  + 0.007991 * T**2
                  - 0.000077774 * T**3)

        return DO_sat

    def compute_reaeration_coefficient(
        self,
        u: np.ndarray,
        h: np.ndarray,
        T: np.ndarray,
        ice_cover_fraction: Optional[np.ndarray] = None
    ) -> np.ndarray:
        """
        计算再曝气系数

        使用O'Connor-Dobbins (1958) 公式:
            Ka(20) = 3.93 * u^0.5 / h^1.5  (1/day)

        温度修正:
            Ka(T) = Ka(20) * 1.024^(T-20)

        冰盖影响:
            Ka_ice = Ka * (1 - 0.9*f_ice)  # 冰盖降低90%再曝气

        Parameters:
        -----------
        u : array
            流速 (m/s)
        h : array
            水深 (m)
        T : array
            水温 (°C)
        ice_cover_fraction : array, optional
            冰盖覆盖率 (0-1)

        Returns:
        --------
        Ka : array
            再曝气系数 (1/day)
        """
        # O'Connor-Dobbins公式 @ 20°C
        Ka_20 = 3.93 * np.abs(u)**0.5 / h**1.5

        # 温度修正
        Ka_T = Ka_20 * self.theta_ka**(T - 20)

        # 冰盖影响
        if ice_cover_fraction is not None:
            # 冰盖下降低90%的再曝气能力
            ice_reduction = 1 - 0.9 * ice_cover_fraction
            Ka_T *= ice_reduction

        return Ka_T

    def compute_BOD_decay(
        self,
        BOD: np.ndarray,
        T: np.ndarray
    ) -> np.ndarray:
        """
        计算BOD衰减速率

        kd(T) = kd(20) * 1.047^(T-20)

        Parameters:
        -----------
        BOD : array
            BOD浓度 (mg/L)
        T : array
            水温 (°C)

        Returns:
        --------
        decay_rate : array
            BOD衰减速率 (mg/L/day)
        """
        # 温度修正的衰减系数
        kd_T = self.kd_20 * self.theta_kd**(T - 20)

        # 一阶衰减
        decay_rate = kd_T * BOD

        return decay_rate

    def compute_sediment_oxygen_demand(
        self,
        h: np.ndarray,
        T: np.ndarray
    ) -> np.ndarray:
        """
        计算底泥耗氧速率

        SOD(T) = SOD(20) * 1.065^(T-20)  (g/m²/day)

        转换为浓度变化率: SOD/h (mg/L/day)

        Parameters:
        -----------
        h : array
            水深 (m)
        T : array
            水温 (°C)

        Returns:
        --------
        sod_rate : array
            底泥耗氧速率 (mg/L/day)
        """
        # 温度修正
        SOD_T = self.SOD_20 * self.theta_SOD**(T - 20)

        # 转换为浓度变化率 (g/m²/day -> mg/L/day)
        # SOD单位: g/m²/day
        # 浓度变化 = SOD / h (m) = g/(m³·day) = 1000 mg/(1000 L·day) = mg/L/day
        sod_rate = SOD_T / h  # g/m²/day / m = mg/L/day

        return sod_rate

    def compute_reaction_terms(
        self,
        DO: np.ndarray,
        BOD: np.ndarray,
        u: np.ndarray,
        h: np.ndarray,
        T: np.ndarray,
        ice_cover_fraction: Optional[np.ndarray] = None
    ) -> np.ndarray:
        """
        计算DO反应项

        R(DO) = Ka*(DO_sat - DO) - kd*BOD - SOD/h

        Parameters:
        -----------
        DO : array
            DO浓度 (mg/L)
        BOD : array
            BOD浓度 (mg/L)
        u : array
            流速 (m/s)
        h : array
            水深 (m)
        T : array
            水温 (°C)
        ice_cover_fraction : array, optional
            冰盖覆盖率 (0-1)

        Returns:
        --------
        R_DO : array
            DO反应速率 (mg/L/day)
        """
        # 1. 再曝气
        DO_sat = self.compute_DO_saturation(T)
        Ka = self.compute_reaeration_coefficient(u, h, T, ice_cover_fraction)
        reaeration = Ka * (DO_sat - DO)

        # 2. BOD耗氧
        bod_consumption = -self.compute_BOD_decay(BOD, T)

        # 3. 底泥耗氧
        sod_consumption = -self.compute_sediment_oxygen_demand(h, T)

        # 总反应速率
        R_DO = reaeration + bod_consumption + sod_consumption

        return R_DO

    def compute_BOD_reaction(
        self,
        BOD: np.ndarray,
        T: np.ndarray
    ) -> np.ndarray:
        """
        计算BOD反应项

        R(BOD) = -kd*BOD

        Parameters:
        -----------
        BOD : array
            BOD浓度 (mg/L)
        T : array
            水温 (°C)

        Returns:
        --------
        R_BOD : array
            BOD反应速率 (mg/L/day)
        """
        R_BOD = -self.compute_BOD_decay(BOD, T)
        return R_BOD

    def step(
        self,
        dt: float,
        u: np.ndarray,
        h: np.ndarray,
        T: np.ndarray,
        manning_n: float = 0.03,
        ice_cover_fraction: Optional[np.ndarray] = None,
        BOD_source: Optional[np.ndarray] = None
    ) -> Dict[str, np.ndarray]:
        """
        推进一个时间步 (DO和BOD耦合求解)

        使用Strang Splitting:
        1. 反应半步
        2. 输运整步
        3. 反应半步

        Parameters:
        -----------
        dt : float
            时间步长 (s)
        u : array
            流速 (m/s)
        h : array
            水深 (m)
        T : array
            水温 (°C)
        manning_n : float
            Manning糙率系数
        ice_cover_fraction : array, optional
            冰盖覆盖率 (0-1)
        BOD_source : array, optional
            BOD外源 (mg/L/day)

        Returns:
        --------
        state : dict
            {'DO': array, 'BOD': array}
        """
        # 计算扩散系数
        D_L = self.compute_dispersion_coefficient(h, u, manning_n=manning_n)

        # 转换时间单位 s -> day
        dt_day = dt / 86400.0

        # ========== Step 1: 反应半步 ==========
        # DO反应
        R_DO = self.compute_reaction_terms(
            self.DO, self.BOD, u, h, T, ice_cover_fraction
        )
        self.DO += 0.5 * dt_day * R_DO
        self.DO = np.maximum(self.DO, 0.0)

        # BOD反应
        R_BOD = self.compute_BOD_reaction(self.BOD, T)
        if BOD_source is not None:
            R_BOD += BOD_source
        self.BOD += 0.5 * dt_day * R_BOD
        self.BOD = np.maximum(self.BOD, 0.0)

        # ========== Step 2: 输运整步 ==========
        self.DO = self.solve_transport(dt, self.DO, u, h, D_L)
        self.BOD = self.solve_transport(dt, self.BOD, u, h, D_L)

        # ========== Step 3: 反应半步 ==========
        # DO反应
        R_DO = self.compute_reaction_terms(
            self.DO, self.BOD, u, h, T, ice_cover_fraction
        )
        self.DO += 0.5 * dt_day * R_DO
        self.DO = np.maximum(self.DO, 0.0)

        # BOD反应
        R_BOD = self.compute_BOD_reaction(self.BOD, T)
        if BOD_source is not None:
            R_BOD += BOD_source
        self.BOD += 0.5 * dt_day * R_BOD
        self.BOD = np.maximum(self.BOD, 0.0)

        return self.get_state()

    def get_state(self) -> Dict[str, np.ndarray]:
        """获取当前状态"""
        return {
            'DO': self.DO.copy(),
            'BOD': self.BOD.copy()
        }

    def get_diagnostics(
        self,
        u: np.ndarray,
        h: np.ndarray,
        T: np.ndarray,
        ice_cover_fraction: Optional[np.ndarray] = None
    ) -> Dict[str, np.ndarray]:
        """
        获取诊断信息

        Returns:
        --------
        diag : dict
            包含各项速率的诊断信息
        """
        DO_sat = self.compute_DO_saturation(T)
        Ka = self.compute_reaeration_coefficient(u, h, T, ice_cover_fraction)
        kd_T = self.kd_20 * self.theta_kd**(T - 20)
        SOD_rate = self.compute_sediment_oxygen_demand(h, T)

        diag = {
            'DO_saturation': DO_sat,
            'DO_deficit': DO_sat - self.DO,
            'saturation_percent': 100 * self.DO / (DO_sat + 1e-12),
            'reaeration_coeff': Ka,
            'reaeration_rate': Ka * (DO_sat - self.DO),
            'BOD_decay_coeff': kd_T,
            'BOD_consumption': -kd_T * self.BOD,
            'SOD_rate': -SOD_rate
        }

        return diag


class StreeterPhelpsAnalytical:
    """
    Streeter-Phelps解析解 (用于验证DO求解器)

    经典DO垂距曲线解析解:
        DO_deficit(x) = (kd*L0)/(ka-kd) * (exp(-kd*t) - exp(-ka*t)) + D0*exp(-ka*t)

    其中:
        - L0: 初始BOD浓度
        - D0: 初始DO亏损
        - t = x/u (水团运动时间)
    """

    def __init__(
        self,
        ka: float,  # 再曝气系数 (1/day)
        kd: float,  # BOD衰减系数 (1/day)
        u: float    # 流速 (m/s)
    ):
        self.ka = ka
        self.kd = kd
        self.u = u

    def compute_deficit(
        self,
        x: np.ndarray,
        DO_sat: float,
        DO_0: float,
        BOD_0: float
    ) -> Tuple[np.ndarray, np.ndarray]:
        """
        计算DO亏损和DO浓度

        Parameters:
        -----------
        x : array
            距离 (m)
        DO_sat : float
            饱和DO (mg/L)
        DO_0 : float
            初始DO (mg/L)
        BOD_0 : float
            初始BOD (mg/L)

        Returns:
        --------
        DO : array
            DO浓度 (mg/L)
        deficit : array
            DO亏损 (mg/L)
        """
        # 运动时间 (day)
        t = x / self.u / 86400.0

        # 初始亏损
        D0 = DO_sat - DO_0

        # Streeter-Phelps解
        if abs(self.ka - self.kd) > 1e-6:
            deficit = (
                (self.kd * BOD_0) / (self.ka - self.kd)
                * (np.exp(-self.kd * t) - np.exp(-self.ka * t))
                + D0 * np.exp(-self.ka * t)
            )
        else:
            # ka ≈ kd的特殊情况
            deficit = (self.kd * BOD_0 * t * np.exp(-self.ka * t)
                       + D0 * np.exp(-self.ka * t))

        DO = DO_sat - deficit

        return DO, deficit

    def find_critical_point(
        self,
        DO_sat: float,
        DO_0: float,
        BOD_0: float
    ) -> Tuple[float, float]:
        """
        计算临界点 (DO最低点)

        tc = 1/(ka-kd) * ln[(ka/kd) * (1 - D0*(ka-kd)/(kd*BOD_0))]

        Returns:
        --------
        x_critical : float
            临界距离 (m)
        DO_critical : float
            临界DO (mg/L)
        """
        D0 = DO_sat - DO_0

        if abs(self.ka - self.kd) > 1e-6:
            term = (self.ka / self.kd) * (1 - D0 * (self.ka - self.kd) / (self.kd * BOD_0))
            if term > 0:
                t_critical = np.log(term) / (self.ka - self.kd)
            else:
                t_critical = 0
        else:
            t_critical = D0 / (self.kd * BOD_0)

        x_critical = t_critical * self.u * 86400.0  # m

        # 计算临界DO
        deficit_critical = (
            (self.kd * BOD_0) / (self.ka - self.kd)
            * (np.exp(-self.kd * t_critical) - np.exp(-self.ka * t_critical))
            + D0 * np.exp(-self.ka * t_critical)
        )
        DO_critical = DO_sat - deficit_critical

        return x_critical, DO_critical
