#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
冰情预测模块 - Ice Condition Prediction System

南水北调中线工程冰情预测核心技术：
1. 水温预测模型（热平衡方程、简化热交换系数法）
2. 封冻判据系统（Froude数法、临界流速法）
3. 气温寒潮指数（TCI）
4. 冰厚预测（修正Stefan方程）
5. 多时段冰情预报（3/5/7/10/15天）

技术来源：
- 南水北调中线数字孪生冰情预测预报系统
- 统计学模型与河冰动力学模型双验证体系
- 实测精度：水温预测误差≤0.35℃，封冻时刻误差<1天

作者: HydroClaude Team
日期: 2025-11-02
"""

import numpy as np
from typing import Dict, List, Optional, Tuple, Union
from dataclasses import dataclass
from enum import Enum
import warnings


class IceConditionType(Enum):
    """冰情类型"""
    NO_ICE = "no_ice"           # 无冰
    SHORE_ICE = "shore_ice"      # 岸冰
    FRAZIL_ICE = "frazil_ice"    # 流冰/冰花
    ICE_COVER = "ice_cover"      # 冰盖
    ICE_JAM = "ice_jam"          # 冰塞/冰坝


class ColdWaveLevel(Enum):
    """寒潮等级（基于TCI指数）"""
    NONE = 0        # 无寒潮
    LIGHT = 1       # 轻度寒潮
    MODERATE = 2    # 中度寒潮
    SEVERE = 3      # 重度寒潮
    EXTREME = 4     # 极端寒潮


@dataclass
class FreezingCriteria:
    """封冻判据参数"""
    Fr_critical: float = 0.065    # 临界Froude数
    V_critical: float = 0.40      # 临界流速 (m/s)
    T_water_freeze: float = 0.0   # 封冻水温 (°C)
    T_supercool: float = -0.01    # 过冷却触发温度 (°C)


class WaterTemperaturePredictor:
    """
    水温预测模型

    基于热平衡方程的水温沿程预测：
    ∂T/∂t + V·∂T/∂x = Φ_net / (ρ·cp·h)

    简化热交换系数法：
    Φ_net ≈ K_wa · (T_eq - T_w)

    京石段推荐参数：K_wa = 18 W/(m²·K)
    实测精度：水温预测误差≤0.35℃（3天预报）
    """

    def __init__(
        self,
        n_cells: int,
        dx: float,
        K_wa: float = 18.0,      # 水面热交换系数 W/(m²·K)
        rho_w: float = 1000.0,   # 水密度 kg/m³
        cp_w: float = 4186.0     # 水比热容 J/(kg·K)
    ):
        """
        初始化水温预测模型

        Parameters
        ----------
        n_cells : int
            网格数量
        dx : float
            空间步长 (m)
        K_wa : float
            水面热交换系数 W/(m²·K)，京石段推荐18
        rho_w : float
            水密度 kg/m³
        cp_w : float
            水比热容 J/(kg·K)
        """
        self.n_cells = n_cells
        self.dx = dx
        self.K_wa = K_wa
        self.rho_w = rho_w
        self.cp_w = cp_w

        # 物理常数
        self.stefan_boltzmann = 5.67e-8  # Stefan-Boltzmann常数

    def compute_equilibrium_temperature(
        self,
        T_air: float,
        solar_radiation: float,
        wind_speed: float,
        relative_humidity: float,
        cloud_cover: float = 0.0
    ) -> float:
        """
        计算平衡温度

        平衡温度是水体在给定气象条件下趋向的稳态温度

        Parameters
        ----------
        T_air : float
            气温 (°C)
        solar_radiation : float
            太阳辐射 (W/m²)
        wind_speed : float
            风速 (m/s)
        relative_humidity : float
            相对湿度 (0-1)
        cloud_cover : float
            云量 (0-1)

        Returns
        -------
        T_eq : float
            平衡温度 (°C)
        """
        # 简化经验公式（基于Ryan & Harleman, 1973）
        # 太阳辐射贡献
        solar_contribution = 0.05 * solar_radiation * (1 - 0.08)  # 考虑反照率

        # 风速修正
        wind_factor = 1.0 + 0.1 * wind_speed

        # 平衡温度近似
        T_eq = T_air + solar_contribution / (self.K_wa * wind_factor) - 2.0 * (1 - relative_humidity)

        # 云量修正
        T_eq -= 3.0 * cloud_cover

        return T_eq

    def compute_net_heat_flux(
        self,
        T_water: np.ndarray,
        T_air: float,
        solar_radiation: float,
        wind_speed: float,
        relative_humidity: float,
        cloud_cover: float = 0.0,
        ice_fraction: Optional[np.ndarray] = None
    ) -> np.ndarray:
        """
        计算水面净热通量

        Φ_net = Φ_solar + Φ_atm - Φ_rad - Φ_evap - Φ_conv

        Parameters
        ----------
        T_water : np.ndarray
            水温 (°C)
        T_air : float
            气温 (°C)
        solar_radiation : float
            太阳辐射 (W/m²)
        wind_speed : float
            风速 (m/s)
        relative_humidity : float
            相对湿度 (0-1)
        cloud_cover : float
            云量 (0-1)
        ice_fraction : np.ndarray, optional
            冰盖覆盖率 (0-1)

        Returns
        -------
        Q_net : np.ndarray
            净热通量 (W/m²)，正值表示水体吸热
        """
        n = len(T_water)

        # 1. 短波太阳辐射（考虑反照率）
        albedo = 0.08  # 水面反照率
        if ice_fraction is not None:
            # 冰盖遮蔽太阳辐射
            effective_solar = solar_radiation * (1 - ice_fraction * 0.8)
        else:
            effective_solar = solar_radiation
        Q_solar = effective_solar * (1 - albedo)

        # 2. 大气长波辐射
        T_a_K = T_air + 273.15
        e_a = self._vapor_pressure(T_air, relative_humidity)
        emissivity_air = 0.64 + 0.045 * np.sqrt(e_a)
        emissivity_air *= (1 + 0.17 * cloud_cover**2)
        Q_atm = emissivity_air * self.stefan_boltzmann * T_a_K**4

        # 3. 水面长波辐射
        T_w_K = T_water + 273.15
        Q_back = 0.97 * self.stefan_boltzmann * T_w_K**4

        # 4. 蒸发散热（Penman公式）
        e_s = self._vapor_pressure(T_water, 1.0)
        f_wind = 9.2 + 0.46 * wind_speed**2  # W/(m²·mb)
        Q_evap = f_wind * (e_s - e_a)

        # 5. 对流换热（Bowen比）
        bowen_ratio = 0.61
        Q_conv = bowen_ratio * Q_evap * (T_water - T_air) / (e_s - e_a + 1e-6)

        # 净热通量
        Q_net = Q_solar + Q_atm - Q_back - Q_evap - Q_conv

        # 冰盖存在时，表面热交换大幅降低
        if ice_fraction is not None:
            Q_net = Q_net * (1 - ice_fraction * 0.9)

        return Q_net * np.ones(n) if np.isscalar(Q_net) else Q_net

    def _vapor_pressure(self, T: Union[float, np.ndarray], RH: float) -> Union[float, np.ndarray]:
        """计算水汽压力 (mb)，Magnus公式"""
        e_sat = 6.112 * np.exp(17.67 * T / (T + 243.5))
        return e_sat * RH

    def predict_temperature_profile(
        self,
        T_initial: np.ndarray,
        T_upstream: float,
        Q: float,
        B: float,
        h: np.ndarray,
        T_air: float,
        solar_radiation: float,
        wind_speed: float,
        relative_humidity: float,
        ice_fraction: Optional[np.ndarray] = None
    ) -> np.ndarray:
        """
        预测水温沿程分布（稳态解）

        解析解：T(x) = T_eq + (T_0 - T_eq) * exp(-K_wa*B*x / (ρ*cp*Q))

        Parameters
        ----------
        T_initial : np.ndarray
            初始水温分布 (°C)
        T_upstream : float
            上游边界水温 (°C)
        Q : float
            流量 (m³/s)
        B : float
            河宽 (m)
        h : np.ndarray
            水深 (m)
        T_air : float
            气温 (°C)
        solar_radiation : float
            太阳辐射 (W/m²)
        wind_speed : float
            风速 (m/s)
        relative_humidity : float
            相对湿度 (0-1)
        ice_fraction : np.ndarray, optional
            冰盖覆盖率

        Returns
        -------
        T_profile : np.ndarray
            水温沿程分布 (°C)
        """
        # 计算平衡温度
        T_eq = self.compute_equilibrium_temperature(
            T_air, solar_radiation, wind_speed, relative_humidity
        )

        # 衰减系数
        decay_rate = self.K_wa * B / (self.rho_w * self.cp_w * Q + 1e-10)

        # 沿程距离
        x = np.arange(self.n_cells) * self.dx

        # 解析解
        T_profile = T_eq + (T_upstream - T_eq) * np.exp(-decay_rate * x)

        # 冰盖修正（冰盖下水温趋近0°C）
        if ice_fraction is not None:
            T_profile = T_profile * (1 - ice_fraction) + 0.0 * ice_fraction

        # 限制水温不低于冰点
        T_profile = np.maximum(T_profile, 0.0)

        return T_profile

    def predict_multi_day(
        self,
        T_current: np.ndarray,
        T_air_forecast: List[float],
        Q: float,
        B: float,
        h: np.ndarray,
        solar_radiation_avg: float = 200.0,
        wind_speed: float = 5.0,
        relative_humidity: float = 0.6
    ) -> Dict[int, np.ndarray]:
        """
        多时段水温预测（3/5/7/10/15天）

        Parameters
        ----------
        T_current : np.ndarray
            当前水温分布 (°C)
        T_air_forecast : List[float]
            气温预报序列 (°C)
        Q : float
            流量 (m³/s)
        B : float
            河宽 (m)
        h : np.ndarray
            水深 (m)
        solar_radiation_avg : float
            平均太阳辐射 (W/m²)
        wind_speed : float
            平均风速 (m/s)
        relative_humidity : float
            相对湿度

        Returns
        -------
        predictions : dict
            各时段水温预测 {天数: 水温分布}
        """
        forecast_days = [3, 5, 7, 10, 15]
        predictions = {}

        T_prev = T_current.copy()

        for day in range(1, max(forecast_days) + 1):
            # 获取当天气温预报
            if day - 1 < len(T_air_forecast):
                T_air = T_air_forecast[day - 1]
            else:
                T_air = T_air_forecast[-1]  # 使用最后一天的预报

            # 预测水温
            T_pred = self.predict_temperature_profile(
                T_prev, T_prev[0], Q, B, h,
                T_air, solar_radiation_avg, wind_speed, relative_humidity
            )

            if day in forecast_days:
                predictions[day] = T_pred.copy()

            T_prev = T_pred

        return predictions


class FreezingCriteriaChecker:
    """
    封冻判据检查器

    封冻条件判断（双重约束）：
    1. 热力条件：T_water ≤ 0°C
    2. 水力条件：Fr ≤ Fr_critical 或 V ≤ V_critical

    南水北调中线参数：
    - 上游：V ≤ 0.40 m/s, Fr ≤ 0.065
    - 下游：V ≤ 0.35 m/s, Fr ≤ 0.055
    """

    def __init__(
        self,
        Fr_critical_upstream: float = 0.065,
        Fr_critical_downstream: float = 0.055,
        V_critical_upstream: float = 0.40,
        V_critical_downstream: float = 0.35,
        g: float = 9.81
    ):
        """
        初始化封冻判据检查器

        Parameters
        ----------
        Fr_critical_upstream : float
            上游临界Froude数
        Fr_critical_downstream : float
            下游临界Froude数
        V_critical_upstream : float
            上游临界流速 (m/s)
        V_critical_downstream : float
            下游临界流速 (m/s)
        g : float
            重力加速度 (m/s²)
        """
        self.Fr_critical_upstream = Fr_critical_upstream
        self.Fr_critical_downstream = Fr_critical_downstream
        self.V_critical_upstream = V_critical_upstream
        self.V_critical_downstream = V_critical_downstream
        self.g = g

    def check_freezing_potential(
        self,
        T_water: np.ndarray,
        u: np.ndarray,
        h: np.ndarray,
        is_upstream: Optional[np.ndarray] = None
    ) -> Dict[str, np.ndarray]:
        """
        检查封冻可能性

        Parameters
        ----------
        T_water : np.ndarray
            水温 (°C)
        u : np.ndarray
            流速 (m/s)
        h : np.ndarray
            水深 (m)
        is_upstream : np.ndarray, optional
            是否为上游段 (bool数组)

        Returns
        -------
        result : dict
            封冻检查结果
        """
        n = len(T_water)

        # 计算Froude数
        Fr = np.abs(u) / np.sqrt(self.g * h + 1e-6)

        # 确定上下游分界
        if is_upstream is None:
            is_upstream = np.ones(n, dtype=bool)

        # 临界值
        Fr_critical = np.where(
            is_upstream,
            self.Fr_critical_upstream,
            self.Fr_critical_downstream
        )
        V_critical = np.where(
            is_upstream,
            self.V_critical_upstream,
            self.V_critical_downstream
        )

        # 热力条件
        thermal_condition = T_water <= 0.0

        # 水力条件
        hydraulic_condition_fr = Fr <= Fr_critical
        hydraulic_condition_v = np.abs(u) <= V_critical
        hydraulic_condition = hydraulic_condition_fr & hydraulic_condition_v

        # 封冻可能性
        freezing_potential = thermal_condition & hydraulic_condition

        # 立封条件（低Fr，冰盖平稳形成）
        standing_freeze = freezing_potential & (Fr < 0.06)

        # 挤封条件（高Fr，流冰下潜堆积）
        juxtaposition_freeze = freezing_potential & (Fr >= 0.06)

        return {
            'Fr': Fr,
            'thermal_condition': thermal_condition,
            'hydraulic_condition': hydraulic_condition,
            'freezing_potential': freezing_potential,
            'standing_freeze': standing_freeze,
            'juxtaposition_freeze': juxtaposition_freeze,
            'Fr_margin': Fr_critical - Fr,
            'V_margin': V_critical - np.abs(u)
        }

    def predict_freeze_time(
        self,
        T_water_current: float,
        T_water_rate: float,  # °C/day
        T_air_forecast: List[float]
    ) -> Optional[int]:
        """
        预测封冻时刻

        Parameters
        ----------
        T_water_current : float
            当前水温 (°C)
        T_water_rate : float
            水温变化率 (°C/day)
        T_air_forecast : List[float]
            气温预报序列 (°C)

        Returns
        -------
        freeze_day : int or None
            预测封冻天数，None表示预报期内不封冻
        """
        T_water = T_water_current

        for day, T_air in enumerate(T_air_forecast):
            # 简化模型：水温趋向气温
            if T_air < 0:
                T_water += T_water_rate
            else:
                T_water += T_water_rate * 0.3  # 气温高于0时降温变缓

            if T_water <= 0.0:
                return day + 1

        return None


class ColdWaveIndex:
    """
    气温寒潮指数（TCI）

    基于3参数Log-logistic分布的气温寒潮指数法：
    - 累计负气温 (AFDD)
    - 降温幅度 (ΔT)
    - 降温连续性 (Duration)

    初冰时间与TCI的关系：
    初冰时间均发生在第一次寒潮或T7D第一次达到寒潮阈值区间时
    """

    # 寒潮等级阈值（基于南水北调中线实践）
    THRESHOLDS = {
        ColdWaveLevel.LIGHT: {'delta_T': 8, 'duration': 2, 'AFDD': 10},
        ColdWaveLevel.MODERATE: {'delta_T': 12, 'duration': 3, 'AFDD': 30},
        ColdWaveLevel.SEVERE: {'delta_T': 16, 'duration': 4, 'AFDD': 60},
        ColdWaveLevel.EXTREME: {'delta_T': 20, 'duration': 5, 'AFDD': 100},
    }

    def __init__(self, window_days: int = 7):
        """
        初始化寒潮指数计算器

        Parameters
        ----------
        window_days : int
            滑动窗口天数（T7D法）
        """
        self.window_days = window_days

    def compute_AFDD(self, T_air_series: np.ndarray) -> np.ndarray:
        """
        计算累计负气温度日 (Accumulated Freezing Degree Days)

        AFDD(t) = ∫₀ᵗ max(0, -T_air(τ)) dτ

        Parameters
        ----------
        T_air_series : np.ndarray
            气温时间序列 (°C)，每日数据

        Returns
        -------
        AFDD : np.ndarray
            累计负气温度日
        """
        negative_temps = np.maximum(0, -T_air_series)
        AFDD = np.cumsum(negative_temps)
        return AFDD

    def compute_T7D(self, T_air_series: np.ndarray) -> np.ndarray:
        """
        计算7日滑动平均气温 (T7D)

        Parameters
        ----------
        T_air_series : np.ndarray
            气温时间序列 (°C)

        Returns
        -------
        T7D : np.ndarray
            7日滑动平均气温
        """
        if len(T_air_series) < self.window_days:
            return np.mean(T_air_series) * np.ones(len(T_air_series))

        # 滑动平均
        kernel = np.ones(self.window_days) / self.window_days
        T7D = np.convolve(T_air_series, kernel, mode='valid')

        # 前面几天用部分平均
        prefix = [np.mean(T_air_series[:i+1]) for i in range(self.window_days - 1)]
        T7D = np.concatenate([prefix, T7D])

        return T7D

    def detect_cold_wave(
        self,
        T_air_series: np.ndarray
    ) -> List[Dict]:
        """
        检测寒潮事件

        Parameters
        ----------
        T_air_series : np.ndarray
            气温时间序列 (°C)

        Returns
        -------
        events : List[Dict]
            寒潮事件列表
        """
        events = []
        n = len(T_air_series)

        if n < 3:
            return events

        # 计算日降温幅度
        delta_T = np.diff(T_air_series)

        # 检测连续降温段
        in_cooling = False
        start_day = 0
        max_drop = 0
        duration = 0

        for i in range(len(delta_T)):
            if delta_T[i] < -2:  # 日降温超过2°C
                if not in_cooling:
                    in_cooling = True
                    start_day = i
                    max_drop = abs(delta_T[i])
                    duration = 1
                else:
                    max_drop += abs(delta_T[i])
                    duration += 1
            else:
                if in_cooling:
                    # 结束一个降温段
                    level = self._classify_cold_wave(max_drop, duration)
                    if level != ColdWaveLevel.NONE:
                        events.append({
                            'start_day': start_day,
                            'end_day': i,
                            'duration': duration,
                            'max_drop': max_drop,
                            'level': level,
                            'min_temp': np.min(T_air_series[start_day:i+1])
                        })
                    in_cooling = False

        return events

    def _classify_cold_wave(self, delta_T: float, duration: int) -> ColdWaveLevel:
        """分类寒潮等级"""
        for level in [ColdWaveLevel.EXTREME, ColdWaveLevel.SEVERE,
                      ColdWaveLevel.MODERATE, ColdWaveLevel.LIGHT]:
            thresh = self.THRESHOLDS[level]
            if delta_T >= thresh['delta_T'] and duration >= thresh['duration']:
                return level
        return ColdWaveLevel.NONE

    def compute_TCI(self, T_air_series: np.ndarray) -> Tuple[np.ndarray, ColdWaveLevel]:
        """
        计算综合寒潮指数 (Temperature Cold Index)

        TCI = f(AFDD, ΔT, Duration)

        Parameters
        ----------
        T_air_series : np.ndarray
            气温时间序列 (°C)

        Returns
        -------
        TCI : np.ndarray
            寒潮指数时间序列
        max_level : ColdWaveLevel
            最高寒潮等级
        """
        # 计算各分量
        AFDD = self.compute_AFDD(T_air_series)
        T7D = self.compute_T7D(T_air_series)

        # 归一化TCI（基于Log-logistic分布）
        # TCI = AFDD_norm + ΔT_norm + Duration_weight
        AFDD_norm = 1 / (1 + np.exp(-(AFDD - 30) / 20))  # Log-logistic

        # 7日平均气温贡献
        T7D_norm = 1 / (1 + np.exp((T7D + 5) / 3))

        TCI = 0.5 * AFDD_norm + 0.5 * T7D_norm

        # 检测寒潮事件，确定最高等级
        events = self.detect_cold_wave(T_air_series)
        if events:
            max_level = max(e['level'] for e in events)
        else:
            max_level = ColdWaveLevel.NONE

        return TCI, max_level

    def predict_first_ice(
        self,
        T_air_forecast: np.ndarray,
        T_water_current: float
    ) -> Dict:
        """
        预测初冰时间

        初冰时间均发生在第一次寒潮或T7D第一次达到寒潮阈值区间时

        Parameters
        ----------
        T_air_forecast : np.ndarray
            气温预报序列 (°C)
        T_water_current : float
            当前水温 (°C)

        Returns
        -------
        prediction : dict
            初冰预测结果
        """
        # 计算TCI和寒潮事件
        TCI, max_level = self.compute_TCI(T_air_forecast)
        T7D = self.compute_T7D(T_air_forecast)
        events = self.detect_cold_wave(T_air_forecast)

        # 找到T7D首次低于-3°C的时刻（寒潮阈值区间）
        first_cold_day = None
        for i, t7d in enumerate(T7D):
            if t7d < -3.0:
                first_cold_day = i
                break

        # 首次寒潮时刻
        first_wave_day = None
        if events:
            first_wave_day = events[0]['start_day']

        # 初冰时间预测（取较早者）
        predicted_ice_day = None
        if first_cold_day is not None and first_wave_day is not None:
            predicted_ice_day = min(first_cold_day, first_wave_day)
        elif first_cold_day is not None:
            predicted_ice_day = first_cold_day
        elif first_wave_day is not None:
            predicted_ice_day = first_wave_day

        # 考虑水温因素
        if predicted_ice_day is not None and T_water_current > 2.0:
            # 水温较高，延迟初冰
            predicted_ice_day += int(T_water_current / 0.5)

        return {
            'predicted_ice_day': predicted_ice_day,
            'first_cold_day': first_cold_day,
            'first_wave_day': first_wave_day,
            'max_cold_wave_level': max_level,
            'TCI': TCI,
            'T7D': T7D,
            'events': events
        }


class IceThicknessPredictor:
    """
    冰厚预测模型

    修正Stefan方程：
    dη/dt = (1/ρi·Lf) · [ki·(Tf-Ts)/η - h_wi·(Tw-Tf)]

    实测验证：南水北调中线近5年渠心最大冰厚14~32cm
    """

    def __init__(
        self,
        rho_ice: float = 917.0,      # 冰密度 kg/m³
        L_fusion: float = 3.34e5,    # 融化潜热 J/kg
        k_ice: float = 2.2,          # 冰导热系数 W/(m·K)
        h_wi: float = 20.0           # 冰水界面换热系数 W/(m²·K)
    ):
        """
        初始化冰厚预测模型

        Parameters
        ----------
        rho_ice : float
            冰密度 kg/m³
        L_fusion : float
            融化潜热 J/kg
        k_ice : float
            冰导热系数 W/(m·K)
        h_wi : float
            冰水界面换热系数 W/(m²·K)
        """
        self.rho_ice = rho_ice
        self.L_fusion = L_fusion
        self.k_ice = k_ice
        self.h_wi = h_wi
        self.T_freeze = 0.0  # 冰点

    def predict_by_stefan(self, AFDD: float) -> float:
        """
        经典Stefan公式预测冰厚

        η = √(2·ki/(ρi·Lf) · AFDD)

        Parameters
        ----------
        AFDD : float
            累计负气温度日 (°C·day)

        Returns
        -------
        h_ice : float
            冰厚 (m)
        """
        # 转换AFDD单位：°C·day -> °C·s
        AFDD_seconds = AFDD * 86400

        # Stefan公式
        h_ice = np.sqrt(2 * self.k_ice * AFDD_seconds / (self.rho_ice * self.L_fusion))

        return h_ice

    def predict_modified_stefan(
        self,
        dt: float,
        h_ice_current: float,
        T_air: float,
        T_water: float
    ) -> float:
        """
        修正Stefan方程求解冰厚增长

        考虑冰下对流换热：
        dη/dt = (1/ρi·Lf) · [ki·(Tf-Ts)/η - h_wi·(Tw-Tf)]

        Parameters
        ----------
        dt : float
            时间步长 (s)
        h_ice_current : float
            当前冰厚 (m)
        T_air : float
            气温 (°C)
        T_water : float
            水温 (°C)

        Returns
        -------
        h_ice_new : float
            新冰厚 (m)
        """
        if h_ice_current < 1e-6:
            # 无冰时，检查是否满足结冰条件
            if T_water <= self.T_freeze and T_air < 0:
                return 0.001  # 初始1mm
            return 0.0

        # 冰面温度（简化：取气温和冰点的平均）
        T_surface = min(0.5 * (T_air + self.T_freeze), self.T_freeze)

        # 上界面热通量（冰内导热）
        Q_up = self.k_ice * (self.T_freeze - T_surface) / h_ice_current

        # 下界面热通量（冰水界面对流）
        Q_down = self.h_wi * (T_water - self.T_freeze)

        # 净热通量
        Q_net = Q_up - Q_down

        # 冰厚变化率
        dh_dt = Q_net / (self.rho_ice * self.L_fusion)

        # 更新冰厚
        h_ice_new = h_ice_current + dh_dt * dt

        # 限制范围
        h_ice_new = max(0.0, h_ice_new)
        h_ice_new = min(0.5, h_ice_new)  # 最大0.5m

        return h_ice_new

    def predict_multi_day(
        self,
        h_ice_initial: float,
        T_air_forecast: List[float],
        T_water_forecast: List[float]
    ) -> Dict[int, float]:
        """
        多时段冰厚预测

        Parameters
        ----------
        h_ice_initial : float
            初始冰厚 (m)
        T_air_forecast : List[float]
            气温预报序列 (°C)
        T_water_forecast : List[float]
            水温预报序列 (°C)

        Returns
        -------
        predictions : dict
            各时段冰厚预测 {天数: 冰厚}
        """
        forecast_days = [3, 5, 7, 10, 15]
        predictions = {}

        h_ice = h_ice_initial
        dt = 86400.0  # 1天

        for day in range(1, max(forecast_days) + 1):
            idx = min(day - 1, len(T_air_forecast) - 1)
            T_air = T_air_forecast[idx]
            T_water = T_water_forecast[idx] if day - 1 < len(T_water_forecast) else 0.5

            h_ice = self.predict_modified_stefan(dt, h_ice, T_air, T_water)

            if day in forecast_days:
                predictions[day] = h_ice

        return predictions


class IntegratedIcePredictor:
    """
    综合冰情预测系统

    集成：
    - 水温预测
    - 封冻判据
    - 寒潮指数
    - 冰厚预测

    输出多时段预报（3/5/7/10/15天）
    """

    def __init__(
        self,
        n_cells: int,
        dx: float,
        K_wa: float = 18.0
    ):
        """
        初始化综合冰情预测系统

        Parameters
        ----------
        n_cells : int
            网格数量
        dx : float
            空间步长 (m)
        K_wa : float
            水面热交换系数
        """
        self.temp_predictor = WaterTemperaturePredictor(n_cells, dx, K_wa)
        self.freeze_checker = FreezingCriteriaChecker()
        self.cold_wave_index = ColdWaveIndex()
        self.ice_thickness = IceThicknessPredictor()

    def predict(
        self,
        T_water_current: np.ndarray,
        h_ice_current: np.ndarray,
        u: np.ndarray,
        h: np.ndarray,
        Q: float,
        B: float,
        T_air_forecast: List[float],
        solar_radiation_avg: float = 200.0,
        wind_speed: float = 5.0,
        relative_humidity: float = 0.6
    ) -> Dict:
        """
        综合冰情预测

        Parameters
        ----------
        T_water_current : np.ndarray
            当前水温分布 (°C)
        h_ice_current : np.ndarray
            当前冰厚分布 (m)
        u : np.ndarray
            流速 (m/s)
        h : np.ndarray
            水深 (m)
        Q : float
            流量 (m³/s)
        B : float
            河宽 (m)
        T_air_forecast : List[float]
            气温预报序列 (°C)
        solar_radiation_avg : float
            平均太阳辐射 (W/m²)
        wind_speed : float
            平均风速 (m/s)
        relative_humidity : float
            相对湿度

        Returns
        -------
        prediction : dict
            综合预测结果
        """
        # 1. 水温预测
        T_water_predictions = self.temp_predictor.predict_multi_day(
            T_water_current, T_water_current[0], Q, B, h,
            T_air_forecast, solar_radiation_avg, wind_speed, relative_humidity
        )

        # 2. 寒潮指数和初冰预测
        cold_wave_result = self.cold_wave_index.predict_first_ice(
            np.array(T_air_forecast),
            np.mean(T_water_current)
        )

        # 3. 封冻判据检查
        freeze_check = self.freeze_checker.check_freezing_potential(
            T_water_current, u, h
        )

        # 4. 冰厚预测
        T_water_forecast = [np.mean(T_water_predictions.get(d, T_water_current))
                           for d in [3, 5, 7, 10, 15]]
        ice_predictions = self.ice_thickness.predict_multi_day(
            np.mean(h_ice_current),
            T_air_forecast,
            T_water_forecast
        )

        # 5. 冰情类型判断
        ice_condition = self._classify_ice_condition(
            T_water_current, h_ice_current, u, h
        )

        # 6. 预警等级
        warning_level = self._compute_warning_level(
            cold_wave_result, freeze_check, np.mean(T_water_current)
        )

        return {
            'T_water_predictions': T_water_predictions,
            'ice_thickness_predictions': ice_predictions,
            'cold_wave': cold_wave_result,
            'freeze_check': freeze_check,
            'ice_condition': ice_condition,
            'warning_level': warning_level,
            'predicted_ice_day': cold_wave_result['predicted_ice_day']
        }

    def _classify_ice_condition(
        self,
        T_water: np.ndarray,
        h_ice: np.ndarray,
        u: np.ndarray,
        h: np.ndarray
    ) -> IceConditionType:
        """分类当前冰情类型"""
        avg_T = np.mean(T_water)
        avg_h_ice = np.mean(h_ice)
        avg_u = np.mean(np.abs(u))
        Fr = np.mean(np.abs(u) / np.sqrt(9.81 * h))

        if avg_h_ice < 0.001:
            if avg_T > 1.0:
                return IceConditionType.NO_ICE
            elif avg_T > 0.0:
                return IceConditionType.SHORE_ICE
            else:
                return IceConditionType.FRAZIL_ICE
        else:
            if Fr > 0.1:
                return IceConditionType.ICE_JAM
            else:
                return IceConditionType.ICE_COVER

    def _compute_warning_level(
        self,
        cold_wave_result: Dict,
        freeze_check: Dict,
        T_water_avg: float
    ) -> int:
        """
        计算预警等级 (0-4)

        0: 正常
        1: 关注（蓝色）
        2: 警戒（黄色）
        3: 警报（橙色）
        4: 紧急（红色）
        """
        level = 0

        # 寒潮等级
        cold_level = cold_wave_result['max_cold_wave_level']
        if cold_level == ColdWaveLevel.EXTREME:
            level = max(level, 4)
        elif cold_level == ColdWaveLevel.SEVERE:
            level = max(level, 3)
        elif cold_level == ColdWaveLevel.MODERATE:
            level = max(level, 2)
        elif cold_level == ColdWaveLevel.LIGHT:
            level = max(level, 1)

        # 水温触发
        if T_water_avg <= 1.2:
            level = max(level, 2)
        if T_water_avg <= 0.5:
            level = max(level, 3)
        if T_water_avg <= 0.0:
            level = max(level, 4)

        # 封冻可能性
        if np.any(freeze_check['freezing_potential']):
            level = max(level, 3)

        return level
