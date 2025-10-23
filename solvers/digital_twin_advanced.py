#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
高级数字孪生框架（增强版）

新增功能：
1. 传感器网络管理
2. 传感器故障检测和隔离
3. 数据质量控制
4. 自适应噪声估计
5. 多传感器融合策略

作者: Claude
日期: 2025-10-23
"""

import numpy as np
from typing import Dict, List, Tuple, Optional, Callable
import copy
import warnings
from enum import Enum

from solvers.hydrostatic_canal_solver import HydrostaticCanalSolver


class SensorStatus(Enum):
    """传感器状态枚举"""
    NORMAL = "正常"
    DEGRADED = "降级"
    FAILED = "故障"
    OFFLINE = "离线"


class AdvancedSensor:
    """
    高级传感器类

    新增功能：
    - 状态监控
    - 故障检测
    - 数据质量评估
    - 自适应噪声估计
    """

    def __init__(
        self,
        name: str,
        sensor_type: str,
        location_idx: int,
        noise_std: float = 0.01,
        failure_detection_threshold: float = 3.0,
        bias: float = 0.0
    ):
        """
        Args:
            name: 传感器名称
            sensor_type: 类型 ('water_level', 'flow_rate', 'velocity')
            location_idx: 位置索引
            noise_std: 测量噪声标准差（初始值）
            failure_detection_threshold: 故障检测阈值（新息的σ倍数）
            bias: 系统偏差（可选）
        """
        self.name = name
        self.sensor_type = sensor_type
        self.location_idx = location_idx
        self.noise_std = noise_std
        self.initial_noise_std = noise_std
        self.failure_threshold = failure_detection_threshold
        self.bias = bias

        # 状态信息
        self.status = SensorStatus.NORMAL
        self.health_score = 1.0  # 0-1，1表示完全健康

        # 统计信息
        self.innovation_history = []  # 新息历史
        self.measurement_count = 0
        self.anomaly_count = 0

        # 自适应噪声估计
        self.adaptive_noise = True
        self.noise_history = []

    def measure(
        self,
        true_value: float,
        add_noise: bool = True,
        add_bias: bool = True
    ) -> Optional[float]:
        """
        模拟测量

        Args:
            true_value: 真实值
            add_noise: 是否添加噪声
            add_bias: 是否添加偏差

        Returns:
            测量值（如果传感器正常），否则None
        """
        if self.status == SensorStatus.OFFLINE or self.status == SensorStatus.FAILED:
            return None

        measurement = true_value

        if add_bias:
            measurement += self.bias

        if add_noise:
            # 根据健康分数调整噪声
            effective_noise = self.noise_std / np.sqrt(self.health_score)
            noise = np.random.normal(0, effective_noise)
            measurement += noise

        self.measurement_count += 1

        return measurement

    def update_innovation(
        self,
        innovation: float,
        predicted_uncertainty: float
    ):
        """
        更新新息统计并检测异常

        Args:
            innovation: 新息值（观测 - 预测）
            predicted_uncertainty: 预测不确定性（σ）
        """
        self.innovation_history.append(innovation)

        # 保留最近100个新息
        if len(self.innovation_history) > 100:
            self.innovation_history.pop(0)

        # 异常检测：新息超过阈值
        normalized_innovation = abs(innovation) / (predicted_uncertainty + 1e-6)

        if normalized_innovation > self.failure_threshold:
            self.anomaly_count += 1

            # 连续异常判定为故障
            if len(self.innovation_history) >= 5:
                recent_innovations = self.innovation_history[-5:]
                if all(abs(inn) / (predicted_uncertainty + 1e-6) > self.failure_threshold * 0.7
                      for inn in recent_innovations):
                    self.status = SensorStatus.FAILED
                    self.health_score = 0.0
                else:
                    self.status = SensorStatus.DEGRADED
                    self.health_score = 0.5
        else:
            # 恢复正常
            if self.status != SensorStatus.FAILED:
                self.status = SensorStatus.NORMAL
                self.health_score = min(1.0, self.health_score + 0.1)

        # 自适应噪声估计
        if self.adaptive_noise and len(self.innovation_history) >= 10:
            # 使用新息估计噪声（假设模型误差较小）
            estimated_noise = np.std(self.innovation_history[-10:])
            self.noise_std = 0.9 * self.noise_std + 0.1 * estimated_noise
            self.noise_history.append(self.noise_std)

    def get_reliability_weight(self) -> float:
        """
        获取可靠性权重（用于多传感器融合）

        Returns:
            权重值 (0-1)
        """
        if self.status == SensorStatus.OFFLINE or self.status == SensorStatus.FAILED:
            return 0.0
        elif self.status == SensorStatus.DEGRADED:
            return 0.3
        else:
            return self.health_score

    def reset_anomaly_counter(self):
        """重置异常计数器"""
        self.anomaly_count = 0

    def get_diagnostics(self) -> Dict:
        """获取诊断信息"""
        return {
            'name': self.name,
            'status': self.status.value,
            'health_score': self.health_score,
            'measurement_count': self.measurement_count,
            'anomaly_count': self.anomaly_count,
            'anomaly_rate': self.anomaly_count / max(1, self.measurement_count),
            'current_noise_std': self.noise_std,
            'initial_noise_std': self.initial_noise_std
        }


class SensorNetwork:
    """
    传感器网络管理器

    功能：
    - 传感器注册和管理
    - 网络健康监控
    - 数据质量评估
    - 冗余传感器融合
    """

    def __init__(self):
        self.sensors: Dict[str, AdvancedSensor] = {}
        self.sensor_groups: Dict[str, List[str]] = {}  # 按类型分组

    def add_sensor(
        self,
        sensor: AdvancedSensor
    ):
        """添加传感器到网络"""
        self.sensors[sensor.name] = sensor

        # 按类型分组
        if sensor.sensor_type not in self.sensor_groups:
            self.sensor_groups[sensor.sensor_type] = []
        self.sensor_groups[sensor.sensor_type].append(sensor.name)

    def get_sensor(self, name: str) -> Optional[AdvancedSensor]:
        """获取传感器"""
        return self.sensors.get(name)

    def get_healthy_sensors(self) -> List[AdvancedSensor]:
        """获取所有健康传感器"""
        return [s for s in self.sensors.values()
                if s.status not in [SensorStatus.FAILED, SensorStatus.OFFLINE]]

    def get_network_health(self) -> float:
        """
        获取网络整体健康度

        Returns:
            健康度 (0-1)
        """
        if not self.sensors:
            return 0.0

        total_health = sum(s.health_score for s in self.sensors.values())
        return total_health / len(self.sensors)

    def get_coverage_map(self, nx: int) -> np.ndarray:
        """
        获取传感器覆盖图

        Args:
            nx: 网格点数

        Returns:
            coverage: 每个网格点的传感器数量
        """
        coverage = np.zeros(nx)

        for sensor in self.get_healthy_sensors():
            coverage[sensor.location_idx] += 1

        return coverage

    def diagnose(self) -> Dict:
        """网络诊断"""
        diagnostics = {
            'total_sensors': len(self.sensors),
            'healthy_sensors': len([s for s in self.sensors.values()
                                   if s.status == SensorStatus.NORMAL]),
            'degraded_sensors': len([s for s in self.sensors.values()
                                    if s.status == SensorStatus.DEGRADED]),
            'failed_sensors': len([s for s in self.sensors.values()
                                  if s.status == SensorStatus.FAILED]),
            'network_health': self.get_network_health(),
            'sensor_details': [s.get_diagnostics() for s in self.sensors.values()]
        }

        return diagnostics


class AdvancedDigitalTwin:
    """
    高级数字孪生（增强版）

    新增功能：
    1. 传感器网络管理
    2. 自动故障检测和隔离
    3. 多传感器融合
    4. 自适应噪声估计
    5. 数据质量控制
    """

    def __init__(
        self,
        solver: HydrostaticCanalSolver,
        dt: float = 1.0,
        process_noise_std: float = 0.01,
        enable_fault_detection: bool = True,
        enable_adaptive_noise: bool = True,
        verbose: bool = True
    ):
        """
        初始化高级数字孪生

        Args:
            solver: 物理模型
            dt: 时间步长
            process_noise_std: 过程噪声标准差
            enable_fault_detection: 是否启用故障检测
            enable_adaptive_noise: 是否启用自适应噪声估计
            verbose: 是否输出详细信息
        """
        self.solver = solver
        self.dt = dt
        self.verbose = verbose

        # 状态维度
        self.nx = solver.nx
        self.state_dim = 2 * self.nx

        # 过程噪声
        self.Q = np.eye(self.state_dim) * (process_noise_std ** 2)

        # 状态协方差
        self.P = np.eye(self.state_dim) * 0.1

        # 传感器网络
        self.sensor_network = SensorNetwork()

        # 配置
        self.enable_fault_detection = enable_fault_detection
        self.enable_adaptive_noise = enable_adaptive_noise

        # 历史记录
        self.history = {
            'time': [],
            'h': [],
            'Q': [],
            'h_std': [],
            'measurements': [],
            'innovations': [],
            'sensor_diagnostics': []
        }

    def add_sensor(
        self,
        name: str,
        sensor_type: str,
        location_idx: int,
        noise_std: float = 0.01,
        failure_threshold: float = 3.0,
        bias: float = 0.0
    ):
        """添加传感器到数字孪生"""
        sensor = AdvancedSensor(
            name=name,
            sensor_type=sensor_type,
            location_idx=location_idx,
            noise_std=noise_std,
            failure_detection_threshold=failure_threshold,
            bias=bias
        )

        sensor.adaptive_noise = self.enable_adaptive_noise
        self.sensor_network.add_sensor(sensor)

        if self.verbose:
            print(f"添加传感器: {name} ({sensor_type}) @ grid {location_idx}, "
                  f"σ={noise_std:.3f}, 故障阈值={failure_threshold:.1f}σ")

    def predict_step(
        self,
        Q_upstream: Optional[float] = None,
        h_downstream: Optional[float] = None
    ):
        """预测步（EKF Prediction）"""
        h_pred, hu_pred = self.solver.step_preissmann(
            dt=self.dt,
            max_iter=10,
            enforce_bc=True,
            Q_in=Q_upstream,
            h_out=h_downstream
        )

        self.solver.h = h_pred
        self.solver.hu = hu_pred

        # 协方差预测
        F = np.eye(self.state_dim)
        self.P = F @ self.P @ F.T + self.Q

    def update_step(
        self,
        measurements: Dict[str, float]
    ) -> Dict[str, float]:
        """
        更新步（增强版）

        支持：
        - 传感器故障检测
        - 可靠性加权融合
        - 自适应噪声
        """
        innovations = {}
        fused_successfully = []

        for sensor_name, z in measurements.items():
            sensor = self.sensor_network.get_sensor(sensor_name)

            if sensor is None:
                warnings.warn(f"未知传感器: {sensor_name}")
                continue

            # 跳过故障传感器
            if sensor.status == SensorStatus.FAILED or sensor.status == SensorStatus.OFFLINE:
                continue

            # 观测矩阵
            H = self._get_observation_matrix(sensor)

            # 预测观测
            z_pred = self._predict_measurement(sensor)

            # 新息
            y = z - z_pred
            innovations[sensor_name] = y

            # 预测不确定性
            predicted_variance = H @ self.P @ H.T + sensor.noise_std ** 2
            predicted_std = np.sqrt(predicted_variance)

            # 故障检测
            if self.enable_fault_detection:
                sensor.update_innovation(y, predicted_std)

                if sensor.status == SensorStatus.FAILED:
                    if self.verbose:
                        print(f"⚠️  传感器故障检测: {sensor_name} (新息={y:.4f}, 阈值={predicted_std * sensor.failure_threshold:.4f})")
                    continue

            # 可靠性权重
            reliability = sensor.get_reliability_weight()

            if reliability < 0.1:
                continue

            # 新息协方差（加权）
            R_effective = (sensor.noise_std ** 2) / reliability
            S = H @ self.P @ H.T + R_effective

            # 卡尔曼增益
            K = self.P @ H.T / S

            # 状态更新
            self.solver.h += K[:self.nx] * y * reliability
            self.solver.hu += K[self.nx:] * y * reliability

            # 协方差更新
            I = np.eye(self.state_dim)
            self.P = (I - np.outer(K, H) * reliability) @ self.P

            fused_successfully.append(sensor_name)

        return innovations

    def _get_observation_matrix(self, sensor: AdvancedSensor) -> np.ndarray:
        """获取观测矩阵"""
        H = np.zeros(self.state_dim)
        idx = sensor.location_idx

        if sensor.sensor_type == 'water_level':
            H[idx] = 1.0
        elif sensor.sensor_type == 'flow_rate':
            H[self.nx + idx] = self.solver.B
        elif sensor.sensor_type == 'velocity':
            h_current = self.solver.h[idx] + 1e-6
            H[self.nx + idx] = 1.0 / h_current

        return H

    def _predict_measurement(self, sensor: AdvancedSensor) -> float:
        """预测传感器观测值"""
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
        assimilation_interval: int = 1,
        diagnostics_interval: int = 10
    ) -> Dict:
        """
        运行数据同化（增强版）

        Args:
            t_end: 结束时间
            Q_upstream_func: 上游流量函数
            h_downstream_func: 下游水深函数
            measurement_func: 测量函数
            assimilation_interval: 同化间隔
            diagnostics_interval: 诊断输出间隔

        Returns:
            结果字典
        """
        n_steps = int(t_end / self.dt)

        if self.verbose:
            print(f"\n{'='*60}")
            print(f"高级数字孪生数据同化")
            print(f"{'='*60}")
            print(f"时间步长: {self.dt} s")
            print(f"总步数: {n_steps}")
            print(f"同化间隔: {assimilation_interval} 步")
            print(f"传感器数量: {len(self.sensor_network.sensors)}")
            print(f"故障检测: {'启用' if self.enable_fault_detection else '禁用'}")
            print(f"自适应噪声: {'启用' if self.enable_adaptive_noise else '禁用'}")
            print(f"{'='*60}\n")

        # 清空历史
        self.history = {
            'time': [],
            'h': [],
            'Q': [],
            'h_std': [],
            'measurements': [],
            'innovations': [],
            'sensor_diagnostics': []
        }

        for step in range(n_steps + 1):
            t_current = step * self.dt

            # 记录状态
            self.history['time'].append(t_current)
            self.history['h'].append(self.solver.h.copy())
            self.history['Q'].append(self.solver.hu * self.solver.B)

            h_var = np.diag(self.P)[:self.nx]
            h_std = np.sqrt(np.maximum(h_var, 0))
            self.history['h_std'].append(h_std)

            # 定期输出诊断
            if self.verbose and step % diagnostics_interval == 0:
                network_health = self.sensor_network.get_network_health()
                print(f"t = {t_current:.1f} s: 网络健康度 = {network_health:.2%}")

            if step == n_steps:
                break

            # 预测步
            Q_up = Q_upstream_func(t_current)
            h_down = h_downstream_func(t_current)
            self.predict_step(Q_upstream=Q_up, h_downstream=h_down)

            # 更新步
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

            # 记录传感器诊断
            if step % diagnostics_interval == 0:
                diagnostics = self.sensor_network.diagnose()
                self.history['sensor_diagnostics'].append({
                    'time': t_current,
                    'diagnostics': diagnostics
                })

        if self.verbose:
            print(f"\n{'='*60}")
            print(f"数据同化完成")
            self._print_final_diagnostics()
            print(f"{'='*60}\n")

        return self.history

    def _print_final_diagnostics(self):
        """打印最终诊断信息"""
        diagnostics = self.sensor_network.diagnose()

        print(f"\n传感器网络诊断:")
        print(f"  总传感器数: {diagnostics['total_sensors']}")
        print(f"  健康: {diagnostics['healthy_sensors']}")
        print(f"  降级: {diagnostics['degraded_sensors']}")
        print(f"  故障: {diagnostics['failed_sensors']}")
        print(f"  网络健康度: {diagnostics['network_health']:.2%}")

        if diagnostics['failed_sensors'] > 0:
            print(f"\n故障传感器:")
            for detail in diagnostics['sensor_details']:
                if detail['status'] == SensorStatus.FAILED.value:
                    print(f"    - {detail['name']}: 异常率={detail['anomaly_rate']:.2%}")

    def forecast(
        self,
        forecast_horizon: float,
        Q_upstream_func: Callable[[float], float],
        h_downstream_func: Callable[[float], float]
    ) -> Dict:
        """预测功能（与基础版相同）"""
        h_saved = self.solver.h.copy()
        hu_saved = self.solver.hu.copy()
        P_saved = self.P.copy()

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

        # 恢复状态
        self.solver.h = h_saved
        self.solver.hu = hu_saved
        self.P = P_saved

        return forecast_result
