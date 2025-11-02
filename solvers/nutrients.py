#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
营养盐循环模拟模块 - Nutrients Cycling Model

物理模型：
    氮循环:
    ∂NH4/∂t + u·∂NH4/∂x = DL·∂²NH4/∂x² - kn·NH4·θ(DO) + km1·OrgN - vs1·NH4/h
    ∂NO3/∂t + u·∂NO3/∂x = DL·∂²NO3/∂x² + kn·NH4·θ(DO) - kdn·NO3·(1-θ(DO))
    ∂OrgN/∂t + u·∂OrgN/∂x = DL·∂²OrgN/∂x² - km1·OrgN - vs2·OrgN/h

    磷循环:
    ∂PO4/∂t + u·∂PO4/∂x = DL·∂²PO4/∂x² + km2·OrgP - vs3·PO4/h + Prelease
    ∂OrgP/∂t + u·∂OrgP/∂x = DL·∂²OrgP/∂x² - km2·OrgP - vs4·OrgP/h

其中:
    - kn: 硝化速率 (1/day)
    - kdn: 反硝化速率 (1/day)
    - km: 矿化速率 (1/day)
    - vs: 沉降速度 (m/day)
    - θ(DO): DO限制函数 (Monod动力学)
    - Prelease: 底泥磷释放 (mg/L/day)

对标: WASP营养盐模块, CE-QUAL-W2

作者: HydroClaude Team
日期: 2025-11-02
"""

import numpy as np
from typing import Dict, Optional, Tuple
from .water_quality_adr import ADRSolver


class NutrientsSolver(ADRSolver):
    """
    营养盐循环求解器

    模拟氮磷循环的完整过程
    """

    def __init__(
        self,
        n_cells: int,
        dx: float,
        # 氮循环参数
        kn_20: float = 0.1,      # 硝化速率 @ 20°C (1/day)
        kdn_20: float = 0.09,    # 反硝化速率 @ 20°C (1/day)
        km_N_20: float = 0.075,  # 有机氮矿化速率 @ 20°C (1/day)
        vs_NH4: float = 0.0,     # NH4沉降速度 (m/day) - 溶解态不沉降
        vs_OrgN: float = 0.1,    # 有机氮沉降速度 (m/day)
        # 磷循环参数
        km_P_20: float = 0.075,  # 有机磷矿化速率 @ 20°C (1/day)
        vs_PO4: float = 0.0,     # PO4沉降速度 (m/day) - 溶解态不沉降
        vs_OrgP: float = 0.1,    # 有机磷沉降速度 (m/day)
        P_release_20: float = 5.0,  # 底泥磷释放 @ 20°C (mg/m²/day)
        # 其他参数
        use_numba: bool = True
    ):
        """
        初始化营养盐求解器

        Parameters:
        -----------
        n_cells : int
            网格单元数
        dx : float
            网格间距 (m)
        kn_20 : float
            硝化速率 @ 20°C (1/day)
        kdn_20 : float
            反硝化速率 @ 20°C (1/day)
        km_N_20 : float
            有机氮矿化速率 @ 20°C (1/day)
        vs_NH4 : float
            NH4沉降速度 (m/day)
        vs_OrgN : float
            有机氮沉降速度 (m/day)
        km_P_20 : float
            有机磷矿化速率 @ 20°C (1/day)
        vs_PO4 : float
            PO4沉降速度 (m/day)
        vs_OrgP : float
            有机磷沉降速度 (m/day)
        P_release_20 : float
            底泥磷释放 @ 20°C (mg/m²/day)
        use_numba : bool
            是否使用Numba加速
        """
        super().__init__(n_cells, dx, use_numba=use_numba, use_muscl=True)

        # 状态变量
        self.NH4 = np.ones(n_cells) * 0.5   # 氨氮 (mg/L)
        self.NO3 = np.ones(n_cells) * 2.0   # 硝态氮 (mg/L)
        self.OrgN = np.ones(n_cells) * 1.0  # 有机氮 (mg/L)
        self.PO4 = np.ones(n_cells) * 0.1   # 磷酸盐 (mg/L)
        self.OrgP = np.ones(n_cells) * 0.05 # 有机磷 (mg/L)

        # 氮循环参数
        self.kn_20 = kn_20
        self.kdn_20 = kdn_20
        self.km_N_20 = km_N_20
        self.vs_NH4 = vs_NH4
        self.vs_OrgN = vs_OrgN

        # 磷循环参数
        self.km_P_20 = km_P_20
        self.vs_PO4 = vs_PO4
        self.vs_OrgP = vs_OrgP
        self.P_release_20 = P_release_20

        # 温度系数
        self.theta_kn = 1.08    # 硝化温度系数
        self.theta_kdn = 1.045  # 反硝化温度系数
        self.theta_km = 1.047   # 矿化温度系数
        self.theta_P_release = 1.08  # 磷释放温度系数

        # Monod半饱和常数
        self.K_DO_nitrif = 0.5  # 硝化DO半饱和 (mg/L)
        self.K_DO_denitrif = 0.5  # 反硝化DO抑制 (mg/L)

        # DO-氮耦合系数
        self.O2_per_NH4 = 4.57  # 硝化耗氧系数 (mg O2 / mg NH4-N)

    def initialize(
        self,
        NH4_initial: np.ndarray,
        NO3_initial: np.ndarray,
        OrgN_initial: Optional[np.ndarray] = None,
        PO4_initial: Optional[np.ndarray] = None,
        OrgP_initial: Optional[np.ndarray] = None
    ):
        """
        初始化营养盐浓度

        Parameters:
        -----------
        NH4_initial : array
            初始NH4浓度 (mg/L)
        NO3_initial : array
            初始NO3浓度 (mg/L)
        OrgN_initial : array, optional
            初始有机氮浓度 (mg/L)
        PO4_initial : array, optional
            初始PO4浓度 (mg/L)
        OrgP_initial : array, optional
            初始有机磷浓度 (mg/L)
        """
        self.NH4 = NH4_initial.copy()
        self.NO3 = NO3_initial.copy()

        if OrgN_initial is not None:
            self.OrgN = OrgN_initial.copy()

        if PO4_initial is not None:
            self.PO4 = PO4_initial.copy()

        if OrgP_initial is not None:
            self.OrgP = OrgP_initial.copy()

    def compute_nitrification_rate(
        self,
        NH4: np.ndarray,
        DO: np.ndarray,
        T: np.ndarray
    ) -> Tuple[np.ndarray, np.ndarray]:
        """
        计算硝化速率

        NH4 + 2O2 → NO3 + H2O + 2H+

        Parameters:
        -----------
        NH4 : array
            氨氮浓度 (mg/L)
        DO : array
            溶解氧浓度 (mg/L)
        T : array
            水温 (°C)

        Returns:
        --------
        nitrif_rate : array
            硝化速率 (mg/L/day)
        DO_consumption : array
            硝化耗氧速率 (mg/L/day)
        """
        # 温度修正
        kn_T = self.kn_20 * self.theta_kn**(T - 20)

        # DO限制 (Monod动力学)
        DO_factor = DO / (DO + self.K_DO_nitrif)

        # 硝化速率
        nitrif_rate = kn_T * NH4 * DO_factor

        # 硝化耗氧
        DO_consumption = self.O2_per_NH4 * nitrif_rate

        return nitrif_rate, DO_consumption

    def compute_denitrification_rate(
        self,
        NO3: np.ndarray,
        DO: np.ndarray,
        T: np.ndarray
    ) -> np.ndarray:
        """
        计算反硝化速率

        NO3 → N2 (厌氧条件)

        Parameters:
        -----------
        NO3 : array
            硝态氮浓度 (mg/L)
        DO : array
            溶解氧浓度 (mg/L)
        T : array
            水温 (°C)

        Returns:
        --------
        denitrif_rate : array
            反硝化速率 (mg/L/day)
        """
        # 温度修正
        kdn_T = self.kdn_20 * self.theta_kdn**(T - 20)

        # DO抑制 (厌氧条件)
        # DO高时反硝化受抑制
        DO_inhibition = np.maximum(0, (self.K_DO_denitrif - DO)) / self.K_DO_denitrif

        # 反硝化速率
        denitrif_rate = kdn_T * NO3 * DO_inhibition

        return denitrif_rate

    def compute_organic_N_mineralization(
        self,
        OrgN: np.ndarray,
        T: np.ndarray
    ) -> np.ndarray:
        """
        计算有机氮矿化速率

        OrgN → NH4

        Parameters:
        -----------
        OrgN : array
            有机氮浓度 (mg/L)
        T : array
            水温 (°C)

        Returns:
        --------
        mineral_rate : array
            矿化速率 (mg/L/day)
        """
        # 温度修正
        km_T = self.km_N_20 * self.theta_km**(T - 20)

        # 一阶矿化
        mineral_rate = km_T * OrgN

        return mineral_rate

    def compute_settling_N(
        self,
        NH4: np.ndarray,
        OrgN: np.ndarray,
        h: np.ndarray
    ) -> Tuple[np.ndarray, np.ndarray]:
        """
        计算氮沉降

        Parameters:
        -----------
        NH4 : array
            氨氮浓度 (mg/L)
        OrgN : array
            有机氮浓度 (mg/L)
        h : array
            水深 (m)

        Returns:
        --------
        settling_NH4 : array
            NH4沉降速率 (mg/L/day)
        settling_OrgN : array
            有机氮沉降速率 (mg/L/day)
        """
        # NH4 (溶解态，通常不沉降)
        settling_NH4 = -self.vs_NH4 * NH4 / h

        # 有机氮 (颗粒态，沉降)
        settling_OrgN = -self.vs_OrgN * OrgN / h

        return settling_NH4, settling_OrgN

    def compute_organic_P_mineralization(
        self,
        OrgP: np.ndarray,
        T: np.ndarray
    ) -> np.ndarray:
        """
        计算有机磷矿化速率

        OrgP → PO4

        Parameters:
        -----------
        OrgP : array
            有机磷浓度 (mg/L)
        T : array
            水温 (°C)

        Returns:
        --------
        mineral_rate : array
            矿化速率 (mg/L/day)
        """
        # 温度修正
        km_T = self.km_P_20 * self.theta_km**(T - 20)

        # 一阶矿化
        mineral_rate = km_T * OrgP

        return mineral_rate

    def compute_P_sediment_release(
        self,
        DO: np.ndarray,
        T: np.ndarray,
        h: np.ndarray
    ) -> np.ndarray:
        """
        计算底泥磷释放

        厌氧条件下底泥释放磷

        Parameters:
        -----------
        DO : array
            溶解氧浓度 (mg/L)
        T : array
            水温 (°C)
        h : array
            水深 (m)

        Returns:
        --------
        release_rate : array
            磷释放速率 (mg/L/day)
        """
        # 温度修正
        P_release_T = self.P_release_20 * self.theta_P_release**(T - 20)

        # DO影响 (厌氧条件下释放更快)
        DO_factor = np.ones_like(DO)
        mask_anaerobic = DO < 1.0
        DO_factor[mask_anaerobic] = (1.0 - DO[mask_anaerobic])

        # 转换为浓度变化率 (mg/m²/day -> mg/L/day)
        release_rate = P_release_T * DO_factor / h  # mg/m²/day / m = mg/L/day

        return release_rate

    def compute_settling_P(
        self,
        PO4: np.ndarray,
        OrgP: np.ndarray,
        h: np.ndarray
    ) -> Tuple[np.ndarray, np.ndarray]:
        """
        计算磷沉降

        Parameters:
        -----------
        PO4 : array
            磷酸盐浓度 (mg/L)
        OrgP : array
            有机磷浓度 (mg/L)
        h : array
            水深 (m)

        Returns:
        --------
        settling_PO4 : array
            PO4沉降速率 (mg/L/day)
        settling_OrgP : array
            有机磷沉降速率 (mg/L/day)
        """
        # PO4 (溶解态)
        settling_PO4 = -self.vs_PO4 * PO4 / h

        # 有机磷 (颗粒态)
        settling_OrgP = -self.vs_OrgP * OrgP / h

        return settling_PO4, settling_OrgP

    def compute_nitrogen_reactions(
        self,
        NH4: np.ndarray,
        NO3: np.ndarray,
        OrgN: np.ndarray,
        DO: np.ndarray,
        T: np.ndarray,
        h: np.ndarray
    ) -> Tuple[np.ndarray, np.ndarray, np.ndarray, np.ndarray]:
        """
        计算氮循环所有反应项

        Parameters:
        -----------
        NH4, NO3, OrgN : array
            氮组分浓度 (mg/L)
        DO : array
            溶解氧 (mg/L)
        T : array
            水温 (°C)
        h : array
            水深 (m)

        Returns:
        --------
        R_NH4, R_NO3, R_OrgN : array
            反应速率 (mg/L/day)
        DO_consumption : array
            硝化耗氧速率 (mg/L/day)
        """
        # 硝化
        nitrif_rate, DO_nitrif = self.compute_nitrification_rate(NH4, DO, T)

        # 反硝化
        denitrif_rate = self.compute_denitrification_rate(NO3, DO, T)

        # 有机氮矿化
        mineral_N_rate = self.compute_organic_N_mineralization(OrgN, T)

        # 沉降
        settling_NH4, settling_OrgN = self.compute_settling_N(NH4, OrgN, h)

        # 氮循环反应速率
        R_NH4 = -nitrif_rate + mineral_N_rate + settling_NH4
        R_NO3 = nitrif_rate - denitrif_rate
        R_OrgN = -mineral_N_rate + settling_OrgN

        return R_NH4, R_NO3, R_OrgN, DO_nitrif

    def compute_phosphorus_reactions(
        self,
        PO4: np.ndarray,
        OrgP: np.ndarray,
        DO: np.ndarray,
        T: np.ndarray,
        h: np.ndarray
    ) -> Tuple[np.ndarray, np.ndarray]:
        """
        计算磷循环所有反应项

        Parameters:
        -----------
        PO4, OrgP : array
            磷组分浓度 (mg/L)
        DO : array
            溶解氧 (mg/L)
        T : array
            水温 (°C)
        h : array
            水深 (m)

        Returns:
        --------
        R_PO4, R_OrgP : array
            反应速率 (mg/L/day)
        """
        # 有机磷矿化
        mineral_P_rate = self.compute_organic_P_mineralization(OrgP, T)

        # 底泥释放
        release_rate = self.compute_P_sediment_release(DO, T, h)

        # 沉降
        settling_PO4, settling_OrgP = self.compute_settling_P(PO4, OrgP, h)

        # 磷循环反应速率
        R_PO4 = mineral_P_rate + release_rate + settling_PO4
        R_OrgP = -mineral_P_rate + settling_OrgP

        return R_PO4, R_OrgP

    def step(
        self,
        dt: float,
        u: np.ndarray,
        h: np.ndarray,
        T: np.ndarray,
        DO: np.ndarray,
        manning_n: float = 0.03
    ) -> Dict[str, np.ndarray]:
        """
        推进一个时间步

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
        DO : array
            溶解氧 (mg/L)
        manning_n : float
            Manning糙率系数

        Returns:
        --------
        state : dict
            当前状态 + DO耗氧速率
        """
        # 计算扩散系数
        D_L = self.compute_dispersion_coefficient(h, u, manning_n=manning_n)

        # 转换时间单位 s -> day
        dt_day = dt / 86400.0

        # ========== Step 1: 反应半步 ==========
        # 氮循环反应
        R_NH4, R_NO3, R_OrgN, DO_nitrif = self.compute_nitrogen_reactions(
            self.NH4, self.NO3, self.OrgN, DO, T, h
        )

        self.NH4 += 0.5 * dt_day * R_NH4
        self.NO3 += 0.5 * dt_day * R_NO3
        self.OrgN += 0.5 * dt_day * R_OrgN

        # 磷循环反应
        R_PO4, R_OrgP = self.compute_phosphorus_reactions(
            self.PO4, self.OrgP, DO, T, h
        )

        self.PO4 += 0.5 * dt_day * R_PO4
        self.OrgP += 0.5 * dt_day * R_OrgP

        # 非负约束
        self.NH4 = np.maximum(self.NH4, 0.0)
        self.NO3 = np.maximum(self.NO3, 0.0)
        self.OrgN = np.maximum(self.OrgN, 0.0)
        self.PO4 = np.maximum(self.PO4, 0.0)
        self.OrgP = np.maximum(self.OrgP, 0.0)

        # ========== Step 2: 输运整步 ==========
        self.NH4 = self.solve_transport(dt, self.NH4, u, h, D_L)
        self.NO3 = self.solve_transport(dt, self.NO3, u, h, D_L)
        self.OrgN = self.solve_transport(dt, self.OrgN, u, h, D_L)
        self.PO4 = self.solve_transport(dt, self.PO4, u, h, D_L)
        self.OrgP = self.solve_transport(dt, self.OrgP, u, h, D_L)

        # ========== Step 3: 反应半步 ==========
        # 氮循环反应
        R_NH4, R_NO3, R_OrgN, DO_nitrif = self.compute_nitrogen_reactions(
            self.NH4, self.NO3, self.OrgN, DO, T, h
        )

        self.NH4 += 0.5 * dt_day * R_NH4
        self.NO3 += 0.5 * dt_day * R_NO3
        self.OrgN += 0.5 * dt_day * R_OrgN

        # 磷循环反应
        R_PO4, R_OrgP = self.compute_phosphorus_reactions(
            self.PO4, self.OrgP, DO, T, h
        )

        self.PO4 += 0.5 * dt_day * R_PO4
        self.OrgP += 0.5 * dt_day * R_OrgP

        # 非负约束
        self.NH4 = np.maximum(self.NH4, 0.0)
        self.NO3 = np.maximum(self.NO3, 0.0)
        self.OrgN = np.maximum(self.OrgN, 0.0)
        self.PO4 = np.maximum(self.PO4, 0.0)
        self.OrgP = np.maximum(self.OrgP, 0.0)

        return self.get_state(DO_nitrif)

    def get_state(self, DO_consumption: Optional[np.ndarray] = None) -> Dict[str, np.ndarray]:
        """获取当前状态"""
        state = {
            'NH4': self.NH4.copy(),
            'NO3': self.NO3.copy(),
            'OrgN': self.OrgN.copy(),
            'PO4': self.PO4.copy(),
            'OrgP': self.OrgP.copy(),
            'TN': self.NH4 + self.NO3 + self.OrgN,  # 总氮
            'TP': self.PO4 + self.OrgP,             # 总磷
            'N_P_ratio': (self.NH4 + self.NO3 + self.OrgN) / (self.PO4 + self.OrgP + 1e-12)
        }

        if DO_consumption is not None:
            state['DO_nitrification'] = DO_consumption

        return state

    def get_diagnostics(
        self,
        DO: np.ndarray,
        T: np.ndarray,
        h: np.ndarray
    ) -> Dict[str, np.ndarray]:
        """
        获取诊断信息

        Returns:
        --------
        diag : dict
            诊断信息
        """
        # 计算各个过程速率
        nitrif_rate, DO_nitrif = self.compute_nitrification_rate(self.NH4, DO, T)
        denitrif_rate = self.compute_denitrification_rate(self.NO3, DO, T)
        mineral_N_rate = self.compute_organic_N_mineralization(self.OrgN, T)
        mineral_P_rate = self.compute_organic_P_mineralization(self.OrgP, T)
        P_release = self.compute_P_sediment_release(DO, T, h)

        diag = {
            'nitrification_rate': nitrif_rate,
            'denitrification_rate': denitrif_rate,
            'N_mineralization_rate': mineral_N_rate,
            'P_mineralization_rate': mineral_P_rate,
            'P_sediment_release': P_release,
            'DO_nitrification': DO_nitrif,
            'TN': self.NH4 + self.NO3 + self.OrgN,
            'TP': self.PO4 + self.OrgP,
            'inorganic_N': self.NH4 + self.NO3,
            'N_P_ratio': (self.NH4 + self.NO3 + self.OrgN) / (self.PO4 + self.OrgP + 1e-12)
        }

        return diag
