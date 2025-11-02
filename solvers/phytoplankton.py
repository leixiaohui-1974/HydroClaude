#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
藻类生长模块 (Phytoplankton Growth Module)

实现完整的藻类生长动力学模型，包括:
- 光限制 (Steele公式 + 冰雪遮蔽)
- 营养盐限制 (Monod动力学，N和P)
- 温度限制 (指数函数)
- 光合作用产氧
- 呼吸作用耗氧
- 营养盐吸收 (Redfield比)
- 死亡和沉降

对标: WASP Eutrophication模块, CE-QUAL-W2 Algae

作者: HydroClaude Team
日期: 2025-11-02
"""

import numpy as np
from typing import Dict, Optional, Tuple
from solvers.water_quality_adr import ADRSolver


class PhytoplanktonSolver(ADRSolver):
    """
    藻类生长求解器

    状态变量:
    - Chla: 叶绿素a浓度 (μg/L)

    耦合:
    - DO: 光合作用产氧, 呼吸耗氧
    - NH4, NO3, PO4: 营养盐吸收
    - 光照: 冰雪遮蔽效应

    对标:
    - WASP: Eutrophication模块
    - CE-QUAL-W2: Algae模块
    - MIKE ECO Lab: Phytoplankton模板
    """

    def __init__(
        self,
        n_cells: int,
        dx: float,
        # 藻类生长参数
        mu_max_20: float = 2.0,      # 最大生长速率 @ 20°C (1/day)
        K_N: float = 0.025,          # 氮半饱和常数 (mg N/L)
        K_P: float = 0.001,          # 磷半饱和常数 (mg P/L)
        I_s: float = 100.0,          # 饱和光照 (W/m²)
        k_d: float = 0.05,           # 死亡速率 @ 20°C (1/day)
        k_r: float = 0.05,           # 呼吸速率 @ 20°C (1/day)
        k_e: float = 0.15,           # 消光系数 (1/m)
        vs_algae: float = 0.1,       # 沉降速度 (m/day)
        # Redfield比 (C:N:P = 106:16:1)
        N_per_Chla: float = 0.08,    # mg N / μg Chla
        P_per_Chla: float = 0.005,   # mg P / μg Chla
        O2_per_Chla: float = 0.15,   # mg O2 / μg Chla (光合作用)
        # 其他
        use_numba: bool = True
    ):
        """
        初始化藻类求解器

        Parameters:
        -----------
        n_cells : int
            网格单元数
        dx : float
            网格间距 (m)
        mu_max_20 : float
            最大生长速率 @ 20°C (1/day)
        K_N : float
            氮半饱和常数 (mg N/L) - 典型值0.01-0.05
        K_P : float
            磷半饱和常数 (mg P/L) - 典型值0.001-0.005
        I_s : float
            饱和光照强度 (W/m²) - Steele公式
        k_d : float
            死亡速率 @ 20°C (1/day)
        k_r : float
            呼吸速率 @ 20°C (1/day)
        k_e : float
            消光系数 (1/m) - 包括水体+藻类自遮蔽
        vs_algae : float
            沉降速度 (m/day)
        N_per_Chla : float
            氮/叶绿素比 (mg N / μg Chla)
        P_per_Chla : float
            磷/叶绿素比 (mg P / μg Chla)
        O2_per_Chla : float
            光合作用产氧系数 (mg O2 / μg Chla / day)
        use_numba : bool
            是否使用Numba加速
        """
        super().__init__(n_cells, dx, use_numba=use_numba, use_muscl=True)

        # 状态变量
        self.Chla = np.ones(n_cells) * 10.0  # 叶绿素a (μg/L)

        # 生长参数
        self.mu_max_20 = mu_max_20
        self.K_N = K_N
        self.K_P = K_P
        self.I_s = I_s
        self.k_d = k_d
        self.k_r = k_r
        self.k_e = k_e
        self.vs_algae = vs_algae

        # 化学计量系数
        self.N_per_Chla = N_per_Chla
        self.P_per_Chla = P_per_Chla
        self.O2_per_Chla = O2_per_Chla

        # 温度系数
        self.theta_mu = 1.068   # 生长温度系数
        self.theta_d = 1.045    # 死亡温度系数
        self.theta_r = 1.045    # 呼吸温度系数

        # 最优温度范围
        self.T_opt = 20.0       # 最优温度 (°C)
        self.T_std = 8.0        # 温度标准差 (°C)

    def initialize(
        self,
        Chla_initial: np.ndarray
    ):
        """
        初始化叶绿素浓度

        Parameters:
        -----------
        Chla_initial : array
            初始叶绿素a浓度 (μg/L)
        """
        self.Chla = Chla_initial.copy()

    def compute_light_limitation(
        self,
        I_0: np.ndarray,
        h: np.ndarray,
        ice_cover_fraction: Optional[np.ndarray] = None
    ) -> np.ndarray:
        """
        计算光限制因子 (Steele公式 + 冰雪遮蔽)

        Steele公式:
        f_I = (I/I_s) * exp(1 - I/I_s)

        冰雪遮蔽:
        - 冰盖透光率: ~0.1-0.3 (取0.2)
        - 雪盖透光率: ~0.01-0.05

        Parameters:
        -----------
        I_0 : array
            水面光照强度 (W/m²)
        h : array
            水深 (m)
        ice_cover_fraction : array, optional
            冰盖覆盖率 (0-1)

        Returns:
        --------
        f_I : array
            光限制因子 (0-1)
        """
        # 冰雪遮蔽
        if ice_cover_fraction is not None:
            # 冰盖透光率 (假设无雪)
            ice_transmittance = 0.2
            I_surface = I_0 * (1 - ice_cover_fraction + ice_cover_fraction * ice_transmittance)
        else:
            I_surface = I_0

        # 水深平均光照 (指数衰减)
        # I_avg = I_surface * (1 - exp(-k_e*h)) / (k_e*h)
        k_h = self.k_e * h
        with np.errstate(divide='ignore', invalid='ignore'):
            I_avg = I_surface * (1 - np.exp(-k_h)) / (k_h + 1e-10)
        I_avg = np.where(k_h < 0.01, I_surface, I_avg)  # 浅水近似

        # Steele公式
        I_ratio = I_avg / self.I_s
        f_I = I_ratio * np.exp(1 - I_ratio)

        # 限制到[0, 1]
        f_I = np.clip(f_I, 0.0, 1.0)

        return f_I

    def compute_nutrient_limitation(
        self,
        NH4: np.ndarray,
        NO3: np.ndarray,
        PO4: np.ndarray
    ) -> Tuple[np.ndarray, np.ndarray]:
        """
        计算营养盐限制因子 (Monod动力学)

        氮限制: 藻类可以利用NH4和NO3
        f_N = (NH4 + NO3) / (K_N + NH4 + NO3)

        磷限制:
        f_P = PO4 / (K_P + PO4)

        Parameters:
        -----------
        NH4 : array
            氨氮浓度 (mg/L)
        NO3 : array
            硝态氮浓度 (mg/L)
        PO4 : array
            磷酸盐浓度 (mg/L)

        Returns:
        --------
        f_N : array
            氮限制因子 (0-1)
        f_P : array
            磷限制因子 (0-1)
        """
        # 氮限制 (总无机氮)
        TIN = NH4 + NO3
        f_N = TIN / (self.K_N + TIN)

        # 磷限制
        f_P = PO4 / (self.K_P + PO4)

        return f_N, f_P

    def compute_temperature_limitation(
        self,
        T: np.ndarray
    ) -> np.ndarray:
        """
        计算温度限制因子

        使用高斯型函数:
        f_T = exp(-((T - T_opt) / T_std)²)

        Parameters:
        -----------
        T : array
            水温 (°C)

        Returns:
        --------
        f_T : array
            温度限制因子 (0-1)
        """
        # 高斯型温度响应
        f_T = np.exp(-((T - self.T_opt) / self.T_std)**2)

        return f_T

    def compute_growth_rate(
        self,
        Chla: np.ndarray,
        I_0: np.ndarray,
        h: np.ndarray,
        T: np.ndarray,
        NH4: np.ndarray,
        NO3: np.ndarray,
        PO4: np.ndarray,
        ice_cover_fraction: Optional[np.ndarray] = None
    ) -> Tuple[np.ndarray, Dict]:
        """
        计算藻类生长速率

        Growth = mu_max * f_I * f_N * f_P * f_T * Chla

        Parameters:
        -----------
        Chla : array
            叶绿素a浓度 (μg/L)
        I_0 : array
            水面光照强度 (W/m²)
        h : array
            水深 (m)
        T : array
            水温 (°C)
        NH4, NO3, PO4 : array
            营养盐浓度 (mg/L)
        ice_cover_fraction : array, optional
            冰盖覆盖率

        Returns:
        --------
        growth_rate : array
            生长速率 (μg/L/day)
        diagnostics : dict
            诊断信息 (f_I, f_N, f_P, f_T, mu)
        """
        # 温度修正的最大生长速率
        mu_max_T = self.mu_max_20 * self.theta_mu**(T - 20)

        # 光限制
        f_I = self.compute_light_limitation(I_0, h, ice_cover_fraction)

        # 营养盐限制
        f_N, f_P = self.compute_nutrient_limitation(NH4, NO3, PO4)

        # 温度限制
        f_T = self.compute_temperature_limitation(T)

        # 实际生长速率
        mu = mu_max_T * f_I * np.minimum(f_N, f_P) * f_T

        # 生长速率
        growth_rate = mu * Chla

        # 诊断信息
        diagnostics = {
            'f_I': f_I,
            'f_N': f_N,
            'f_P': f_P,
            'f_T': f_T,
            'mu': mu,
            'limiting_factor': self._identify_limiting_factor(f_I, f_N, f_P)
        }

        return growth_rate, diagnostics

    def _identify_limiting_factor(
        self,
        f_I: np.ndarray,
        f_N: np.ndarray,
        f_P: np.ndarray
    ) -> np.ndarray:
        """
        识别限制因子

        Returns:
        --------
        limiting : array of strings
            'Light', 'Nitrogen', 'Phosphorus'
        """
        limiting = np.empty(len(f_I), dtype=object)

        for i in range(len(f_I)):
            if f_I[i] < min(f_N[i], f_P[i]):
                limiting[i] = 'Light'
            elif f_N[i] < f_P[i]:
                limiting[i] = 'Nitrogen'
            else:
                limiting[i] = 'Phosphorus'

        return limiting

    def compute_death_rate(
        self,
        Chla: np.ndarray,
        T: np.ndarray
    ) -> np.ndarray:
        """
        计算藻类死亡速率

        Death = k_d * θ^(T-20) * Chla

        Parameters:
        -----------
        Chla : array
            叶绿素a浓度 (μg/L)
        T : array
            水温 (°C)

        Returns:
        --------
        death_rate : array
            死亡速率 (μg/L/day)
        """
        # 温度修正
        k_d_T = self.k_d * self.theta_d**(T - 20)

        # 死亡速率
        death_rate = k_d_T * Chla

        return death_rate

    def compute_respiration_rate(
        self,
        Chla: np.ndarray,
        T: np.ndarray
    ) -> np.ndarray:
        """
        计算呼吸速率 (耗氧)

        Respiration = k_r * θ^(T-20) * Chla

        Parameters:
        -----------
        Chla : array
            叶绿素a浓度 (μg/L)
        T : array
            水温 (°C)

        Returns:
        --------
        respiration_rate : array
            呼吸速率 (μg/L/day)
        """
        # 温度修正
        k_r_T = self.k_r * self.theta_r**(T - 20)

        # 呼吸速率
        respiration_rate = k_r_T * Chla

        return respiration_rate

    def compute_settling(
        self,
        Chla: np.ndarray,
        h: np.ndarray
    ) -> np.ndarray:
        """
        计算藻类沉降

        Parameters:
        -----------
        Chla : array
            叶绿素a浓度 (μg/L)
        h : array
            水深 (m)

        Returns:
        --------
        settling_rate : array
            沉降速率 (μg/L/day)
        """
        settling_rate = -self.vs_algae * Chla / h

        return settling_rate

    def compute_nutrient_uptake(
        self,
        growth_rate: np.ndarray,
        NH4: np.ndarray,
        NO3: np.ndarray
    ) -> Tuple[np.ndarray, np.ndarray, np.ndarray]:
        """
        计算营养盐吸收

        基于Redfield比:
        N uptake = N_per_Chla * growth_rate
        P uptake = P_per_Chla * growth_rate

        氮优先吸收NH4，不足时吸收NO3

        Parameters:
        -----------
        growth_rate : array
            藻类生长速率 (μg/L/day)
        NH4 : array
            氨氮浓度 (mg/L)
        NO3 : array
            硝态氮浓度 (mg/L)

        Returns:
        --------
        NH4_uptake : array
            NH4吸收速率 (mg/L/day)
        NO3_uptake : array
            NO3吸收速率 (mg/L/day)
        PO4_uptake : array
            PO4吸收速率 (mg/L/day)
        """
        # 总氮需求
        N_demand = self.N_per_Chla * growth_rate

        # 优先吸收NH4
        NH4_uptake = np.minimum(NH4 * 10.0, N_demand)  # 限制吸收速率
        N_remaining = N_demand - NH4_uptake

        # 剩余需求从NO3吸收
        NO3_uptake = np.minimum(NO3 * 10.0, N_remaining)

        # 磷吸收
        PO4_uptake = self.P_per_Chla * growth_rate

        return NH4_uptake, NO3_uptake, PO4_uptake

    def compute_oxygen_production(
        self,
        growth_rate: np.ndarray,
        respiration_rate: np.ndarray
    ) -> np.ndarray:
        """
        计算DO产生/消耗

        光合作用产氧: O2_production = O2_per_Chla * growth_rate
        呼吸作用耗氧: O2_consumption = O2_per_Chla * respiration_rate

        Parameters:
        -----------
        growth_rate : array
            生长速率 (μg/L/day)
        respiration_rate : array
            呼吸速率 (μg/L/day)

        Returns:
        --------
        DO_change : array
            DO变化速率 (mg/L/day)
        """
        # 光合作用产氧
        O2_production = self.O2_per_Chla * growth_rate

        # 呼吸耗氧
        O2_consumption = self.O2_per_Chla * respiration_rate

        # 净DO变化
        DO_change = O2_production - O2_consumption

        return DO_change

    def step(
        self,
        dt: float,
        u: np.ndarray,
        h: np.ndarray,
        T: np.ndarray,
        I_0: np.ndarray,
        NH4: np.ndarray,
        NO3: np.ndarray,
        PO4: np.ndarray,
        ice_cover_fraction: Optional[np.ndarray] = None
    ) -> Dict:
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
        T : array
            水温 (°C)
        I_0 : array
            水面光照强度 (W/m²)
        NH4, NO3, PO4 : array
            营养盐浓度 (mg/L)
        ice_cover_fraction : array, optional
            冰盖覆盖率 (0-1)

        Returns:
        --------
        state : dict
            {'Chla': 叶绿素浓度,
             'growth_rate': 生长速率,
             'death_rate': 死亡速率,
             'NH4_uptake': NH4吸收,
             'NO3_uptake': NO3吸收,
             'PO4_uptake': PO4吸收,
             'DO_production': DO产生,
             'diagnostics': 诊断信息}
        """
        # 计算扩散系数
        D_L = self.compute_dispersion_coefficient(u, h)

        # 反应函数
        def reaction_function(C, dt_react):
            # 计算净生长速率常数 (1/day)
            # 温度修正的最大生长速率
            mu_max_T = self.mu_max_20 * self.theta_mu**(T - 20)

            # 光限制
            f_I = self.compute_light_limitation(I_0, h, ice_cover_fraction)

            # 营养盐限制
            f_N, f_P = self.compute_nutrient_limitation(NH4, NO3, PO4)

            # 温度限制
            f_T = self.compute_temperature_limitation(T)

            # 实际生长速率常数
            mu = mu_max_T * f_I * np.minimum(f_N, f_P) * f_T

            # 死亡速率常数
            k_d_T = self.k_d * self.theta_d**(T - 20)

            # 呼吸速率常数
            k_r_T = self.k_r * self.theta_r**(T - 20)

            # 沉降速率常数
            k_s = self.vs_algae / h

            # 净速率常数 (1/day -> 1/s)
            k_net = (mu - k_d_T - k_r_T - k_s) / 86400.0

            # 反应速率
            R = k_net * C

            return R

        # Strang分裂
        self.Chla = self.strang_splitting_step(
            dt, self.Chla, u, h, D_L, reaction_function
        )

        # 确保非负
        self.Chla = np.maximum(self.Chla, 0.0)

        # 计算诊断量 (用于输出和耦合)
        growth_rate, diagnostics = self.compute_growth_rate(
            self.Chla, I_0, h, T, NH4, NO3, PO4, ice_cover_fraction
        )
        death_rate = self.compute_death_rate(self.Chla, T)
        respiration_rate = self.compute_respiration_rate(self.Chla, T)

        NH4_uptake, NO3_uptake, PO4_uptake = self.compute_nutrient_uptake(
            growth_rate, NH4, NO3
        )

        DO_production = self.compute_oxygen_production(growth_rate, respiration_rate)

        return {
            'Chla': self.Chla,
            'growth_rate': growth_rate,
            'death_rate': death_rate,
            'respiration_rate': respiration_rate,
            'NH4_uptake': NH4_uptake,
            'NO3_uptake': NO3_uptake,
            'PO4_uptake': PO4_uptake,
            'DO_production': DO_production,
            'diagnostics': diagnostics
        }

    def get_state(self) -> Dict:
        """
        获取当前状态

        Returns:
        --------
        state : dict
            当前状态变量
        """
        return {
            'Chla': self.Chla.copy()
        }
