#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
南水北调中线工程监测数据气象订正模块

基于中线工程各节制闸的气温、雨量、水温监测数据，
对气象预报进行本地化订正，替代气象大模型的高算力需求。

核心技术：
1. 模式输出统计（MOS）- 基于历史数据的系统性偏差校正
2. 卡尔曼滤波 - 实时动态偏差估计
3. 空间插值 - 站点间数据内插
4. 轻量级ML模型 - 随机森林/梯度提升回归

优势：
- 不需要GPU，普通服务器即可运行
- 基于本地监测数据，更贴合实际
- 实时更新，持续改进

作者: HydroClaude Team
日期: 2025-11-02
"""

import numpy as np
from typing import Dict, List, Optional, Tuple, Union
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from collections import deque
import warnings


@dataclass
class MonitoringStation:
    """监测站点信息"""
    station_id: str           # 站点ID
    name: str                 # 站点名称
    chainage: float           # 桩号 (km)
    longitude: float          # 经度
    latitude: float           # 纬度
    has_temperature: bool = True    # 是否有气温监测
    has_rainfall: bool = True       # 是否有雨量监测
    has_water_temp: bool = True     # 是否有水温监测
    has_wind: bool = False          # 是否有风速监测


# 京石段14座节制闸监测站配置
JINGSHI_MONITORING_STATIONS = [
    MonitoringStation("JK01", "岗头", 0.0, 114.53, 36.78),
    MonitoringStation("JK02", "古运河", 15.5, 114.58, 36.92),
    MonitoringStation("JK03", "漳河", 35.2, 114.62, 37.10),
    MonitoringStation("JK04", "滏阳河", 52.8, 114.65, 37.25),
    MonitoringStation("JK05", "七里河", 72.0, 114.70, 37.42),
    MonitoringStation("JK06", "午河", 88.5, 114.73, 37.55),
    MonitoringStation("JK07", "泜河", 105.0, 114.78, 37.70),
    MonitoringStation("JK08", "沙河", 122.3, 114.82, 37.85),
    MonitoringStation("JK09", "洺河", 138.6, 114.87, 37.98),
    MonitoringStation("JK10", "李阳河", 155.0, 114.92, 38.12),
    MonitoringStation("JK11", "槐河", 171.5, 114.98, 38.28),
    MonitoringStation("JK12", "蒲阳河", 188.0, 115.05, 38.45),
    MonitoringStation("JK13", "南拒马河", 202.5, 115.12, 38.60),
    MonitoringStation("JK14", "北拒马河", 217.0, 115.20, 38.75),
]


@dataclass
class RealtimeObservation:
    """实时监测数据"""
    timestamp: datetime
    station_id: str
    T_air: Optional[float] = None      # 气温 (°C)
    T_water: Optional[float] = None    # 水温 (°C)
    rainfall: Optional[float] = None   # 雨量 (mm)
    wind_speed: Optional[float] = None # 风速 (m/s)
    humidity: Optional[float] = None   # 相对湿度 (0-1)
    water_level: Optional[float] = None # 水位 (m)
    ice_observed: Optional[bool] = None # 是否观测到冰


class KalmanBiasCorrector:
    """
    卡尔曼滤波偏差校正器

    实时估计气象预报的系统性偏差，并进行动态校正。

    状态方程：x(k) = x(k-1) + w(k)  (偏差为缓变过程)
    观测方程：y(k) = x(k) + v(k)    (观测偏差=真实偏差+噪声)

    优点：
    - 能够自适应跟踪偏差变化
    - 对异常值有一定的鲁棒性
    - 计算量小，适合实时应用
    """

    def __init__(
        self,
        n_stations: int = 14,
        process_noise: float = 0.1,     # 过程噪声方差
        obs_noise: float = 1.0,         # 观测噪声方差
        initial_bias: float = 0.0,      # 初始偏差估计
        initial_variance: float = 10.0  # 初始方差
    ):
        """
        初始化卡尔曼滤波器

        Parameters
        ----------
        n_stations : int
            站点数量
        process_noise : float
            过程噪声方差 Q
        obs_noise : float
            观测噪声方差 R
        initial_bias : float
            初始偏差估计
        initial_variance : float
            初始估计方差
        """
        self.n_stations = n_stations
        self.Q = process_noise  # 过程噪声
        self.R = obs_noise      # 观测噪声

        # 各站点的状态（偏差估计）
        self.x = np.full(n_stations, initial_bias)  # 状态估计
        self.P = np.full(n_stations, initial_variance)  # 估计方差

        # 历史记录
        self.bias_history = [[] for _ in range(n_stations)]
        self.max_history = 1000

    def update(
        self,
        station_idx: int,
        forecast_value: float,
        observed_value: float
    ) -> float:
        """
        单站点卡尔曼滤波更新

        Parameters
        ----------
        station_idx : int
            站点索引
        forecast_value : float
            预报值
        observed_value : float
            观测值

        Returns
        -------
        corrected_value : float
            校正后的预报值
        """
        if np.isnan(observed_value) or np.isnan(forecast_value):
            return forecast_value

        # 计算观测偏差
        observation_bias = forecast_value - observed_value

        # 预测步
        x_pred = self.x[station_idx]  # 状态预测（假设偏差不变）
        P_pred = self.P[station_idx] + self.Q  # 方差预测

        # 更新步
        K = P_pred / (P_pred + self.R)  # 卡尔曼增益
        self.x[station_idx] = x_pred + K * (observation_bias - x_pred)  # 状态更新
        self.P[station_idx] = (1 - K) * P_pred  # 方差更新

        # 记录历史
        self.bias_history[station_idx].append(self.x[station_idx])
        if len(self.bias_history[station_idx]) > self.max_history:
            self.bias_history[station_idx] = self.bias_history[station_idx][-self.max_history:]

        # 返回校正后的预报值
        corrected_value = forecast_value - self.x[station_idx]
        return corrected_value

    def batch_update(
        self,
        forecast_values: np.ndarray,
        observed_values: np.ndarray
    ) -> np.ndarray:
        """
        批量更新所有站点

        Parameters
        ----------
        forecast_values : np.ndarray
            各站点预报值
        observed_values : np.ndarray
            各站点观测值

        Returns
        -------
        corrected_values : np.ndarray
            校正后的预报值
        """
        corrected = np.zeros_like(forecast_values)
        for i in range(min(len(forecast_values), self.n_stations)):
            corrected[i] = self.update(i, forecast_values[i], observed_values[i])
        return corrected

    def get_bias_estimate(self, station_idx: int) -> Tuple[float, float]:
        """
        获取当前偏差估计及其不确定性

        Returns
        -------
        bias : float
            偏差估计值
        std : float
            估计标准差
        """
        return self.x[station_idx], np.sqrt(self.P[station_idx])


class MOSCorrector:
    """
    模式输出统计（MOS）校正器

    基于历史预报-观测配对数据，建立回归关系进行校正。

    方法：
    1. 简单线性回归：y_corrected = a * y_forecast + b
    2. 多元回归：考虑多个预报变量
    3. 分段回归：不同温度区间使用不同系数

    适用场景：
    - 有足够的历史数据（建议至少30天）
    - 预报偏差有稳定的统计特征
    """

    def __init__(
        self,
        n_stations: int = 14,
        min_samples: int = 30,  # 最小样本数
        segment_bins: List[float] = None  # 分段温度区间
    ):
        """
        初始化MOS校正器

        Parameters
        ----------
        n_stations : int
            站点数量
        min_samples : int
            建立回归所需的最小样本数
        segment_bins : List[float], optional
            分段温度区间，如 [-20, -10, 0, 10, 20]
        """
        self.n_stations = n_stations
        self.min_samples = min_samples
        self.segment_bins = segment_bins or [-30, -10, 0, 10, 30]

        # 各站点的回归系数
        self.coefficients = {}  # {station_idx: {'a': float, 'b': float}}

        # 历史数据存储
        self.history = {i: {'forecast': [], 'observed': []} for i in range(n_stations)}
        self.max_history = 10000

        # 分段回归系数
        self.segment_coefficients = {}  # {station_idx: {bin_idx: {'a', 'b'}}}

    def add_sample(
        self,
        station_idx: int,
        forecast_value: float,
        observed_value: float
    ):
        """添加一个预报-观测配对样本"""
        if np.isnan(forecast_value) or np.isnan(observed_value):
            return

        self.history[station_idx]['forecast'].append(forecast_value)
        self.history[station_idx]['observed'].append(observed_value)

        # 限制历史长度
        if len(self.history[station_idx]['forecast']) > self.max_history:
            self.history[station_idx]['forecast'] = self.history[station_idx]['forecast'][-self.max_history:]
            self.history[station_idx]['observed'] = self.history[station_idx]['observed'][-self.max_history:]

    def fit(self, station_idx: int) -> bool:
        """
        为指定站点拟合回归模型

        Returns
        -------
        success : bool
            是否成功拟合
        """
        history = self.history[station_idx]
        n_samples = len(history['forecast'])

        if n_samples < self.min_samples:
            return False

        x = np.array(history['forecast'])
        y = np.array(history['observed'])

        # 简单线性回归: y = a*x + b
        # 使用最小二乘法
        x_mean = np.mean(x)
        y_mean = np.mean(y)

        numerator = np.sum((x - x_mean) * (y - y_mean))
        denominator = np.sum((x - x_mean) ** 2)

        if abs(denominator) < 1e-10:
            return False

        a = numerator / denominator
        b = y_mean - a * x_mean

        self.coefficients[station_idx] = {'a': a, 'b': b}

        # 分段回归
        self._fit_segmented(station_idx, x, y)

        return True

    def _fit_segmented(self, station_idx: int, x: np.ndarray, y: np.ndarray):
        """分段拟合"""
        self.segment_coefficients[station_idx] = {}

        for i in range(len(self.segment_bins) - 1):
            bin_min = self.segment_bins[i]
            bin_max = self.segment_bins[i + 1]

            mask = (x >= bin_min) & (x < bin_max)
            if np.sum(mask) < 10:  # 样本不足
                continue

            x_seg = x[mask]
            y_seg = y[mask]

            x_mean = np.mean(x_seg)
            y_mean = np.mean(y_seg)

            numerator = np.sum((x_seg - x_mean) * (y_seg - y_mean))
            denominator = np.sum((x_seg - x_mean) ** 2)

            if abs(denominator) < 1e-10:
                continue

            a = numerator / denominator
            b = y_mean - a * x_mean

            self.segment_coefficients[station_idx][i] = {'a': a, 'b': b}

    def correct(
        self,
        station_idx: int,
        forecast_value: float,
        use_segmented: bool = True
    ) -> float:
        """
        校正预报值

        Parameters
        ----------
        station_idx : int
            站点索引
        forecast_value : float
            预报值
        use_segmented : bool
            是否使用分段回归

        Returns
        -------
        corrected_value : float
            校正后的值
        """
        if station_idx not in self.coefficients:
            # 尝试拟合
            if not self.fit(station_idx):
                return forecast_value  # 无法校正，返回原值

        if use_segmented and station_idx in self.segment_coefficients:
            # 使用分段回归
            for i in range(len(self.segment_bins) - 1):
                if self.segment_bins[i] <= forecast_value < self.segment_bins[i + 1]:
                    if i in self.segment_coefficients[station_idx]:
                        coef = self.segment_coefficients[station_idx][i]
                        return coef['a'] * forecast_value + coef['b']
                    break

        # 使用全局回归
        coef = self.coefficients[station_idx]
        return coef['a'] * forecast_value + coef['b']

    def get_correction_stats(self, station_idx: int) -> Dict:
        """获取校正统计信息"""
        if station_idx not in self.coefficients:
            return {'fitted': False, 'n_samples': len(self.history[station_idx]['forecast'])}

        history = self.history[station_idx]
        x = np.array(history['forecast'])
        y = np.array(history['observed'])

        coef = self.coefficients[station_idx]
        y_pred = coef['a'] * x + coef['b']

        # 计算统计量
        mae = np.mean(np.abs(y - y_pred))
        rmse = np.sqrt(np.mean((y - y_pred) ** 2))
        bias = np.mean(y_pred - y)

        return {
            'fitted': True,
            'n_samples': len(x),
            'a': coef['a'],
            'b': coef['b'],
            'mae': mae,
            'rmse': rmse,
            'bias': bias
        }


class SpatialInterpolator:
    """
    空间插值器

    基于站点数据进行空间插值，用于：
    1. 填补缺测站点数据
    2. 获取任意位置的估计值
    3. 生成沿程分布数据

    方法：
    - 反距离加权（IDW）
    - 克里金插值（简化版）
    """

    def __init__(self, stations: List[MonitoringStation]):
        """
        初始化空间插值器

        Parameters
        ----------
        stations : List[MonitoringStation]
            监测站点列表
        """
        self.stations = stations
        self.n_stations = len(stations)

        # 提取站点位置
        self.positions = np.array([[s.chainage] for s in stations])

    def idw_interpolate(
        self,
        values: np.ndarray,
        target_positions: np.ndarray,
        power: float = 2.0
    ) -> np.ndarray:
        """
        反距离加权插值

        Parameters
        ----------
        values : np.ndarray
            站点观测值
        target_positions : np.ndarray
            目标位置（桩号，km）
        power : float
            距离权重幂次

        Returns
        -------
        interpolated : np.ndarray
            插值结果
        """
        n_targets = len(target_positions)
        interpolated = np.zeros(n_targets)

        for i, pos in enumerate(target_positions):
            # 计算到各站点的距离
            distances = np.abs(self.positions.flatten() - pos)

            # 处理重合点
            min_dist = np.min(distances)
            if min_dist < 0.1:  # 距离小于100m
                idx = np.argmin(distances)
                interpolated[i] = values[idx]
                continue

            # 反距离加权
            weights = 1.0 / (distances ** power + 1e-10)

            # 忽略NaN值
            valid_mask = ~np.isnan(values)
            if not np.any(valid_mask):
                interpolated[i] = np.nan
                continue

            weights = weights[valid_mask]
            valid_values = values[valid_mask]

            interpolated[i] = np.sum(weights * valid_values) / np.sum(weights)

        return interpolated

    def interpolate_to_grid(
        self,
        values: np.ndarray,
        n_cells: int = 217,
        method: str = 'idw'
    ) -> np.ndarray:
        """
        插值到渠道网格

        Parameters
        ----------
        values : np.ndarray
            站点观测值
        n_cells : int
            网格数量
        method : str
            插值方法 ('idw' 或 'linear')

        Returns
        -------
        grid_values : np.ndarray
            网格值
        """
        total_length = 217.0  # 京石段总长217km
        target_positions = np.linspace(0, total_length, n_cells)

        if method == 'idw':
            return self.idw_interpolate(values, target_positions)
        elif method == 'linear':
            # 线性插值
            valid_mask = ~np.isnan(values)
            if np.sum(valid_mask) < 2:
                return np.full(n_cells, np.nanmean(values))

            return np.interp(
                target_positions,
                self.positions.flatten()[valid_mask],
                values[valid_mask]
            )
        else:
            raise ValueError(f"Unknown method: {method}")


class LightweightWeatherCorrector:
    """
    轻量级气象预报校正系统

    集成卡尔曼滤波、MOS校正和空间插值，
    提供实用的气象预报订正方案。

    特点：
    - 不需要GPU，普通服务器即可运行
    - 基于中线工程监测数据
    - 实时更新，持续改进
    """

    def __init__(
        self,
        stations: List[MonitoringStation] = None,
        use_kalman: bool = True,
        use_mos: bool = True
    ):
        """
        初始化轻量级气象校正系统

        Parameters
        ----------
        stations : List[MonitoringStation], optional
            监测站点，默认使用京石段14站
        use_kalman : bool
            是否使用卡尔曼滤波
        use_mos : bool
            是否使用MOS校正
        """
        self.stations = stations or JINGSHI_MONITORING_STATIONS
        self.n_stations = len(self.stations)

        # 初始化各组件
        self.kalman = KalmanBiasCorrector(n_stations=self.n_stations) if use_kalman else None
        self.mos = MOSCorrector(n_stations=self.n_stations) if use_mos else None
        self.interpolator = SpatialInterpolator(self.stations)

        # 实时观测缓存
        self.recent_observations = deque(maxlen=1000)

        # 校正配置
        self.use_kalman = use_kalman
        self.use_mos = use_mos

        # 变量配置
        self.variables = ['T_air', 'T_water', 'rainfall', 'wind_speed']

    def ingest_observation(self, obs: RealtimeObservation):
        """
        接收实时观测数据

        Parameters
        ----------
        obs : RealtimeObservation
            实时观测
        """
        self.recent_observations.append(obs)

        # 找到对应站点索引
        station_idx = None
        for i, s in enumerate(self.stations):
            if s.station_id == obs.station_id:
                station_idx = i
                break

        if station_idx is None:
            return

        # TODO: 如果有对应的预报值，更新校正器
        # 这里需要配合预报数据使用

    def correct_forecast(
        self,
        forecast_values: Dict[str, np.ndarray],
        observed_values: Dict[str, np.ndarray],
        variable: str = 'T_air'
    ) -> np.ndarray:
        """
        校正气象预报

        Parameters
        ----------
        forecast_values : Dict[str, np.ndarray]
            各变量的预报值 {变量名: 站点值数组}
        observed_values : Dict[str, np.ndarray]
            各变量的观测值 {变量名: 站点值数组}
        variable : str
            要校正的变量

        Returns
        -------
        corrected : np.ndarray
            校正后的预报值
        """
        if variable not in forecast_values:
            raise ValueError(f"Variable {variable} not in forecast")

        forecast = forecast_values[variable]
        observed = observed_values.get(variable)

        if observed is None:
            return forecast

        corrected = forecast.copy()

        # 1. 卡尔曼滤波校正（实时偏差估计）
        if self.use_kalman and self.kalman is not None:
            corrected = self.kalman.batch_update(corrected, observed)

        # 2. MOS校正（统计回归）
        if self.use_mos and self.mos is not None:
            # 先添加样本
            for i in range(min(len(forecast), len(observed), self.n_stations)):
                self.mos.add_sample(i, forecast[i], observed[i])

            # 应用校正
            for i in range(len(corrected)):
                if i < self.n_stations:
                    corrected[i] = self.mos.correct(i, corrected[i])

        return corrected

    def correct_and_interpolate(
        self,
        forecast_values: Dict[str, np.ndarray],
        observed_values: Dict[str, np.ndarray],
        variable: str = 'T_air',
        n_cells: int = 217
    ) -> np.ndarray:
        """
        校正并插值到渠道网格

        Parameters
        ----------
        forecast_values : Dict
            预报值
        observed_values : Dict
            观测值
        variable : str
            变量名
        n_cells : int
            网格数

        Returns
        -------
        grid_values : np.ndarray
            插值到网格的校正值
        """
        # 校正
        corrected = self.correct_forecast(forecast_values, observed_values, variable)

        # 插值
        grid_values = self.interpolator.interpolate_to_grid(corrected, n_cells)

        return grid_values

    def get_correction_summary(self) -> Dict:
        """获取校正系统摘要"""
        summary = {
            'n_stations': self.n_stations,
            'use_kalman': self.use_kalman,
            'use_mos': self.use_mos,
            'recent_observations': len(self.recent_observations)
        }

        if self.kalman:
            summary['kalman_bias'] = {
                s.station_id: {
                    'bias': float(self.kalman.x[i]),
                    'std': float(np.sqrt(self.kalman.P[i]))
                }
                for i, s in enumerate(self.stations)
            }

        if self.mos:
            summary['mos_stats'] = {
                s.station_id: self.mos.get_correction_stats(i)
                for i, s in enumerate(self.stations)
            }

        return summary


class IcePeriodWeatherService:
    """
    冰期气象服务

    集成气象校正和冰情预测的完整服务。
    """

    def __init__(self):
        """初始化冰期气象服务"""
        self.corrector = LightweightWeatherCorrector()
        self.stations = JINGSHI_MONITORING_STATIONS

        # 预报缓存
        self.forecast_cache = {}

        # 冰情历史
        self.ice_history = []

    def process_observations(
        self,
        observations: List[RealtimeObservation]
    ) -> Dict:
        """
        处理实时观测数据

        Parameters
        ----------
        observations : List[RealtimeObservation]
            观测数据列表

        Returns
        -------
        processed : Dict
            处理后的数据
        """
        # 按变量整理数据
        T_air = np.full(len(self.stations), np.nan)
        T_water = np.full(len(self.stations), np.nan)
        rainfall = np.full(len(self.stations), np.nan)

        for obs in observations:
            for i, s in enumerate(self.stations):
                if s.station_id == obs.station_id:
                    if obs.T_air is not None:
                        T_air[i] = obs.T_air
                    if obs.T_water is not None:
                        T_water[i] = obs.T_water
                    if obs.rainfall is not None:
                        rainfall[i] = obs.rainfall
                    break

        return {
            'T_air': T_air,
            'T_water': T_water,
            'rainfall': rainfall,
            'timestamp': observations[0].timestamp if observations else None
        }

    def get_corrected_forecast(
        self,
        raw_forecast: Dict[str, np.ndarray],
        current_observations: Dict[str, np.ndarray]
    ) -> Dict[str, np.ndarray]:
        """
        获取校正后的气象预报

        Parameters
        ----------
        raw_forecast : Dict
            原始预报
        current_observations : Dict
            当前观测

        Returns
        -------
        corrected_forecast : Dict
            校正后的预报
        """
        corrected = {}

        for var in ['T_air', 'T_water']:
            if var in raw_forecast:
                corrected[var] = self.corrector.correct_forecast(
                    raw_forecast, current_observations, var
                )

        return corrected

    def estimate_water_temperature(
        self,
        T_air_forecast: np.ndarray,
        T_water_current: np.ndarray,
        hours_ahead: int = 72
    ) -> np.ndarray:
        """
        估计未来水温

        基于气温预报和当前水温，估计未来水温变化

        Parameters
        ----------
        T_air_forecast : np.ndarray
            气温预报序列
        T_water_current : np.ndarray
            当前水温
        hours_ahead : int
            预报时长（小时）

        Returns
        -------
        T_water_forecast : np.ndarray
            水温预报序列
        """
        n_steps = min(len(T_air_forecast), hours_ahead)
        T_water = np.zeros((n_steps, len(T_water_current)))
        T_water[0] = T_water_current

        # 简化热交换模型
        K_wa = 18.0  # 热交换系数 W/(m²·K)
        rho_cp_h = 1000 * 4186 * 3.0  # ρ·cp·h

        dt = 3600.0  # 1小时

        for t in range(1, n_steps):
            dT = K_wa * (T_air_forecast[t] - T_water[t-1]) / rho_cp_h * dt
            T_water[t] = T_water[t-1] + dT
            T_water[t] = np.maximum(T_water[t], 0.0)  # 不低于冰点

        return T_water

    def assess_ice_risk(
        self,
        T_water_forecast: np.ndarray,
        T_air_forecast: np.ndarray
    ) -> Dict:
        """
        评估冰情风险

        Parameters
        ----------
        T_water_forecast : np.ndarray
            水温预报
        T_air_forecast : np.ndarray
            气温预报

        Returns
        -------
        risk : Dict
            风险评估结果
        """
        # 找到水温首次低于1.2°C的时刻
        trigger_time = None
        for t, T in enumerate(T_water_forecast):
            if np.mean(T) <= 1.2:
                trigger_time = t
                break

        # 找到水温首次低于0°C的时刻
        freeze_time = None
        for t, T in enumerate(T_water_forecast):
            if np.mean(T) <= 0.0:
                freeze_time = t
                break

        # 累计负气温
        AFDD = np.cumsum(np.maximum(0, -T_air_forecast))

        # 风险等级
        if freeze_time is not None and freeze_time < 72:
            level = 4  # 紧急
            message = "未来3天可能结冰"
        elif trigger_time is not None and trigger_time < 72:
            level = 3  # 警报
            message = "未来3天需启动冰期调度"
        elif trigger_time is not None and trigger_time < 168:
            level = 2  # 警戒
            message = "未来7天可能需冰期调度"
        elif np.min(T_air_forecast) < -10:
            level = 1  # 关注
            message = "有强降温，请关注水温"
        else:
            level = 0  # 正常
            message = "冰情风险较低"

        return {
            'risk_level': level,
            'risk_message': message,
            'trigger_hour': trigger_time,
            'freeze_hour': freeze_time,
            'AFDD_max': AFDD[-1] if len(AFDD) > 0 else 0,
            'T_air_min': np.min(T_air_forecast),
            'T_water_min': np.min([np.mean(T) for T in T_water_forecast])
        }


def demo_local_correction():
    """演示本地化校正"""
    print("=" * 60)
    print("  南水北调中线气象预报本地化校正演示")
    print("=" * 60)

    # 初始化校正系统
    corrector = LightweightWeatherCorrector()

    # 模拟预报数据
    n_stations = 14
    raw_forecast = {
        'T_air': np.random.normal(-5, 3, n_stations),  # 预报气温
        'T_water': np.random.normal(2, 1, n_stations)   # 预报水温
    }

    # 模拟观测数据（比预报偏低1-2度）
    observed = {
        'T_air': raw_forecast['T_air'] - np.random.uniform(1, 2, n_stations),
        'T_water': raw_forecast['T_water'] - np.random.uniform(0.5, 1, n_stations)
    }

    print("\n原始预报 vs 观测：")
    print(f"  气温预报: {np.mean(raw_forecast['T_air']):.2f}°C")
    print(f"  气温观测: {np.mean(observed['T_air']):.2f}°C")
    print(f"  偏差: {np.mean(raw_forecast['T_air']) - np.mean(observed['T_air']):+.2f}°C")

    # 校正
    corrected = corrector.correct_forecast(raw_forecast, observed, 'T_air')

    print(f"\n校正后：")
    print(f"  气温校正: {np.mean(corrected):.2f}°C")
    print(f"  残差: {np.mean(corrected) - np.mean(observed['T_air']):+.2f}°C")

    # 插值到网格
    grid_values = corrector.correct_and_interpolate(
        raw_forecast, observed, 'T_air', n_cells=217
    )
    print(f"\n网格插值：")
    print(f"  网格点数: {len(grid_values)}")
    print(f"  气温范围: {grid_values.min():.2f} ~ {grid_values.max():.2f}°C")

    print("\n" + "=" * 60)
    print("  本地化校正无需GPU，普通服务器即可运行")
    print("=" * 60)


if __name__ == "__main__":
    demo_local_correction()
