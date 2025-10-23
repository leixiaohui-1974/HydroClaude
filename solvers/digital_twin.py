#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
数字孪生框架

实现水利工程数字孪生的核心功能：
- 状态估计（扩展卡尔曼滤波 EKF）
- 数据同化（将实测数据融合到模型）
- 实时校正和预测
- 不确定性量化

充分利用现有的HydrostaticCanalSolver作为物理模型

作者: Claude
日期: 2025-10-23
"""

import numpy as np
from typing import Dict, List, Tuple, Optional, Callable
import copy
import warnings

from solvers.hydrostatic_canal_solver import HydrostaticCanalSolver


class DigitalTwin:
    """
    水利工程数字孪生

    核心功能：
    1. 使用EKF进行状态估计
    2. 融合传感器数据（水位计、流速计）
    3. 实时更新模型状态
    4. 预测未来演化
    5. 量化不确定性
    """

    def __init__(
        self,
        solver: HydrostaticCanalSolver,
        dt: float = 1.0,
        process_noise_std: float = 0.01,
        verbose: bool = True
    ):
        """
        初始化数字孪生

        Args:
            solver: 物理模型（求解器）
            dt: 时间步长 (s)
            process_noise_std: 过程噪声标准差（模型不确定性）
            verbose: 是否输出详细信息
        """
        self.solver = solver
        self.dt = dt
        self.verbose = verbose

        # 状态维度
        self.nx = solver.nx
        self.state_dim = 2 * self.nx  # [h, hu]

        # 过程噪声协方差（模型不确定性）
        self.Q = np.eye(self.state_dim) * (process_noise_std ** 2)

        # 状态协方差矩阵（不确定性）
        self.P = np.eye(self.state_dim) * 0.1

        # 传感器配置
        self.sensors: Dict[str, Sensor] = {}

        # 历史记录
        self.history = {
            'time': [],
            'state': [],  # 估计状态
            'covariance': [],  # 不确定性
            'measurements': [],  # 观测值
            'innovations': []  # 新息（观测 - 预测）
        }

    def add_sensor(
        self,
        name: str,
        sensor_type: str,
        location_idx: int,
        noise_std: float = 0.01
    ):
        """
        添加传感器

        Args:
            name: 传感器名称
            sensor_type: 类型 ('water_level', 'flow_rate', 'velocity')
            location_idx: 位置索引（网格点）
            noise_std: 测量噪声标准差
        """
        sensor = Sensor(
            name=name,
            sensor_type=sensor_type,
            location_idx=location_idx,
            noise_std=noise_std
        )
        self.sensors[name] = sensor

        if self.verbose:
            print(f"添加传感器: {name} ({sensor_type}) @ grid {location_idx}, σ={noise_std:.3f}")

    def predict_step(
        self,
        Q_upstream: Optional[float] = None,
        h_downstream: Optional[float] = None
    ):
        """
        预测步（EKF Prediction）

        使用物理模型预测下一时刻状态

        Args:
            Q_upstream: 上游边界条件（流量）
            h_downstream: 下游边界条件（水深）
        """
        # 使用求解器进行一步预测
        h_pred, hu_pred = self.solver.step_preissmann(
            dt=self.dt,
            max_iter=10,
            enforce_bc=True,
            Q_in=Q_upstream,
            h_out=h_downstream
        )

        # 更新求解器状态
        self.solver.h = h_pred
        self.solver.hu = hu_pred

        # 计算雅可比矩阵（简化：使用有限差分）
        # F ≈ I（对于Preissmann隐式格式，系统接近线性）
        F = np.eye(self.state_dim)

        # 协方差预测：P = F * P * F^T + Q
        self.P = F @ self.P @ F.T + self.Q

    def update_step(
        self,
        measurements: Dict[str, float]
    ) -> Dict[str, float]:
        """
        更新步（EKF Update）

        融合传感器测量数据

        Args:
            measurements: {传感器名: 测量值}

        Returns:
            innovations: {传感器名: 新息}
        """
        innovations = {}

        for sensor_name, z in measurements.items():
            if sensor_name not in self.sensors:
                warnings.warn(f"未知传感器: {sensor_name}")
                continue

            sensor = self.sensors[sensor_name]

            # 观测矩阵 H
            H = self._get_observation_matrix(sensor)

            # 预测的观测值
            z_pred = self._predict_measurement(sensor)

            # 新息（innovation）
            y = z - z_pred
            innovations[sensor_name] = y

            # 新息协方差
            R = sensor.noise_std ** 2  # 测量噪声
            S = H @ self.P @ H.T + R

            # 卡尔曼增益
            K = self.P @ H.T / S

            # 状态更新
            self.solver.h += K[:self.nx] * y
            self.solver.hu += K[self.nx:] * y

            # 协方差更新：P = (I - K*H) * P
            I = np.eye(self.state_dim)
            self.P = (I - np.outer(K, H)) @ self.P

        return innovations

    def _get_observation_matrix(
        self,
        sensor: 'Sensor'
    ) -> np.ndarray:
        """
        获取观测矩阵 H

        H 将状态映射到观测: z = H * x

        Args:
            sensor: 传感器对象

        Returns:
            H: 观测矩阵 (1 x state_dim)
        """
        H = np.zeros(self.state_dim)

        idx = sensor.location_idx

        if sensor.sensor_type == 'water_level':
            # 观测水深 h
            H[idx] = 1.0

        elif sensor.sensor_type == 'flow_rate':
            # 观测流量 Q = hu * B
            H[self.nx + idx] = self.solver.B

        elif sensor.sensor_type == 'velocity':
            # 观测流速 u = hu / h
            # 简化：线性化 u ≈ hu / h_current
            h_current = self.solver.h[idx] + 1e-6
            H[self.nx + idx] = 1.0 / h_current

        return H

    def _predict_measurement(
        self,
        sensor: 'Sensor'
    ) -> float:
        """
        预测传感器观测值

        Args:
            sensor: 传感器对象

        Returns:
            预测的观测值
        """
        idx = sensor.location_idx

        if sensor.sensor_type == 'water_level':
            return self.solver.h[idx]

        elif sensor.sensor_type == 'flow_rate':
            return self.solver.hu[idx] * self.solver.B

        elif sensor.sensor_type == 'velocity':
            h = self.solver.h[idx] + 1e-6
            return self.solver.hu[idx] / h

        else:
            raise ValueError(f"未知传感器类型: {sensor.sensor_type}")

    def run_assimilation(
        self,
        t_end: float,
        Q_upstream_func: Callable[[float], float],
        h_downstream_func: Callable[[float], float],
        measurement_func: Callable[[float], Dict[str, float]],
        assimilation_interval: int = 1
    ) -> Dict:
        """
        运行数据同化循环

        交替执行预测和更新步骤

        Args:
            t_end: 结束时间 (s)
            Q_upstream_func: 上游流量函数 Q(t)
            h_downstream_func: 下游水深函数 h(t)
            measurement_func: 测量函数 measurements(t) -> {sensor_name: value}
            assimilation_interval: 同化间隔（每几步同化一次）

        Returns:
            结果字典
        """
        n_steps = int(t_end / self.dt)

        if self.verbose:
            print(f"\n{'='*60}")
            print(f"数字孪生数据同化")
            print(f"{'='*60}")
            print(f"时间步长: {self.dt} s")
            print(f"总步数: {n_steps}")
            print(f"同化间隔: {assimilation_interval} 步")
            print(f"传感器数量: {len(self.sensors)}")
            print(f"{'='*60}\n")

        # 清空历史
        self.history = {
            'time': [],
            'h': [],
            'Q': [],
            'h_std': [],  # 水深不确定性
            'measurements': [],
            'innovations': []
        }

        for step in range(n_steps + 1):
            t_current = step * self.dt

            # 记录当前状态
            self.history['time'].append(t_current)
            self.history['h'].append(self.solver.h.copy())
            self.history['Q'].append(self.solver.hu * self.solver.B)

            # 计算状态不确定性（水深部分的标准差）
            h_var = np.diag(self.P)[:self.nx]
            h_std = np.sqrt(np.maximum(h_var, 0))
            self.history['h_std'].append(h_std)

            if step == n_steps:
                break

            # 预测步
            Q_up = Q_upstream_func(t_current)
            h_down = h_downstream_func(t_current)

            self.predict_step(Q_upstream=Q_up, h_downstream=h_down)

            # 更新步（数据同化）
            if step % assimilation_interval == 0:
                measurements = measurement_func(t_current)

                if measurements:
                    innovations = self.update_step(measurements)

                    self.history['measurements'].append({
                        'time': t_current,
                        'data': measurements
                    })
                    self.history['innovations'].append({
                        'time': t_current,
                        'values': innovations
                    })

                    if self.verbose and step % 10 == 0:
                        avg_innovation = np.mean([abs(v) for v in innovations.values()])
                        print(f"t = {t_current:.1f} s: 同化完成, 平均新息 = {avg_innovation:.4f}")

        if self.verbose:
            print(f"\n{'='*60}")
            print(f"数据同化完成")
            print(f"{'='*60}\n")

        return self.history

    def forecast(
        self,
        forecast_horizon: float,
        Q_upstream_func: Callable[[float], float],
        h_downstream_func: Callable[[float], float]
    ) -> Dict:
        """
        从当前状态开始预测

        Args:
            forecast_horizon: 预测时长 (s)
            Q_upstream_func: 上游流量预测
            h_downstream_func: 下游水深预测

        Returns:
            预测结果字典
        """
        # 保存当前状态
        h_saved = self.solver.h.copy()
        hu_saved = self.solver.hu.copy()
        P_saved = self.P.copy()

        # 预测
        n_steps = int(forecast_horizon / self.dt)
        forecast_result = {
            'time': [],
            'h': [],
            'Q': [],
            'h_std': []
        }

        t_start = self.history['time'][-1] if self.history['time'] else 0.0

        for step in range(n_steps + 1):
            t = t_start + step * self.dt

            forecast_result['time'].append(t)
            forecast_result['h'].append(self.solver.h.copy())
            forecast_result['Q'].append(self.solver.hu * self.solver.B)

            h_var = np.diag(self.P)[:self.nx]
            h_std = np.sqrt(np.maximum(h_var, 0))
            forecast_result['h_std'].append(h_std)

            if step < n_steps:
                Q_up = Q_upstream_func(t)
                h_down = h_downstream_func(t)
                self.predict_step(Q_upstream=Q_up, h_downstream=h_down)

        # 恢复状态（预测不修改实际状态）
        self.solver.h = h_saved
        self.solver.hu = hu_saved
        self.P = P_saved

        return forecast_result


class Sensor:
    """传感器类"""

    def __init__(
        self,
        name: str,
        sensor_type: str,
        location_idx: int,
        noise_std: float = 0.01
    ):
        """
        Args:
            name: 传感器名称
            sensor_type: 类型 ('water_level', 'flow_rate', 'velocity')
            location_idx: 位置索引
            noise_std: 测量噪声标准差
        """
        self.name = name
        self.sensor_type = sensor_type
        self.location_idx = location_idx
        self.noise_std = noise_std

    def measure(
        self,
        true_value: float,
        add_noise: bool = True
    ) -> float:
        """
        模拟测量（添加噪声）

        Args:
            true_value: 真实值
            add_noise: 是否添加噪声

        Returns:
            测量值
        """
        if add_noise:
            noise = np.random.normal(0, self.noise_std)
            return true_value + noise
        else:
            return true_value
