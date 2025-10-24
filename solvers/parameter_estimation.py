#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
参数在线估计

功能：
1. 糙率（Manning's n）在线估计
2. 渗漏率在线估计
3. 联合状态-参数估计（Augmented EKF）
4. 自适应参数更新

作者: Claude
日期: 2025-10-23
"""

import numpy as np
from typing import Dict, List, Tuple, Optional, Callable
import copy
import warnings

from solvers.hydrostatic_canal_solver import HydrostaticCanalSolver


class ParameterEstimator:
    """
    参数在线估计器

    使用增广卡尔曼滤波（Augmented EKF）：
    扩展状态向量 = [h, hu, n, leak_rate, ...]

    核心思想：
    - 将参数视为"慢变状态"
    - 参数动力学：n(k+1) = n(k) + w_n
    - 同时估计状态和参数
    """

    def __init__(
        self,
        solver: HydrostaticCanalSolver,
        dt: float = 1.0,
        estimate_roughness: bool = True,
        estimate_leakage: bool = False,
        process_noise_std: float = 0.01,
        parameter_process_noise: float = 1e-5,
        verbose: bool = True
    ):
        """
        初始化参数估计器

        Args:
            solver: 物理模型
            dt: 时间步长
            estimate_roughness: 是否估计糙率
            estimate_leakage: 是否估计渗漏率
            process_noise_std: 状态过程噪声
            parameter_process_noise: 参数过程噪声（很小）
            verbose: 是否输出详细信息
        """
        self.solver = solver
        self.dt = dt
        self.estimate_roughness = estimate_roughness
        self.estimate_leakage = estimate_leakage
        self.verbose = verbose

        # 状态维度
        self.nx = solver.nx
        self.state_dim = 2 * self.nx  # [h, hu]

        # 参数维度
        self.param_dim = 0
        self.param_names = []

        if estimate_roughness:
            self.param_dim += 1  # 单个糙率参数（假设全局糙率）
            self.param_names.append('roughness')

        if estimate_leakage:
            self.param_dim += self.nx  # 每个网格点的渗漏率
            self.param_names.extend([f'leak_{i}' for i in range(self.nx)])

        # 增广状态维度
        self.augmented_dim = self.state_dim + self.param_dim

        # 过程噪声协方差
        Q_state = np.eye(self.state_dim) * (process_noise_std ** 2)
        Q_param = np.eye(self.param_dim) * (parameter_process_noise ** 2)
        self.Q = np.block([
            [Q_state, np.zeros((self.state_dim, self.param_dim))],
            [np.zeros((self.param_dim, self.state_dim)), Q_param]
        ])

        # 增广状态协方差
        P_state = np.eye(self.state_dim) * 0.1
        P_param = np.eye(self.param_dim) * 0.01  # 参数初始不确定性
        self.P = np.block([
            [P_state, np.zeros((self.state_dim, self.param_dim))],
            [np.zeros((self.param_dim, self.state_dim)), P_param]
        ])

        # 参数初始值
        self.parameters = {}
        if estimate_roughness:
            self.parameters['roughness'] = solver.n  # 初始糙率
        if estimate_leakage:
            self.parameters['leakage'] = np.zeros(self.nx)  # 初始渗漏率为0

        # 传感器
        self.sensors = {}

        # 当前边界条件（用于敏感度计算）
        self.current_Q_upstream = 0.0
        self.current_h_downstream = 0.0

        # 历史记录
        self.history = {
            'time': [],
            'h': [],
            'Q': [],
            'parameters': {name: [] for name in self.param_names},
            'parameter_std': {name: [] for name in self.param_names},
            'measurements': [],
            'innovations': []
        }

        if self.verbose:
            print(f"参数估计器初始化:")
            print(f"  状态维度: {self.state_dim}")
            print(f"  参数维度: {self.param_dim}")
            print(f"  增广维度: {self.augmented_dim}")
            print(f"  估计参数: {', '.join(self.param_names)}")

    def add_sensor(
        self,
        name: str,
        sensor_type: str,
        location_idx: int,
        noise_std: float = 0.01
    ):
        """添加传感器"""
        self.sensors[name] = {
            'type': sensor_type,
            'location': location_idx,
            'noise_std': noise_std
        }

    def _get_parameter_vector(self) -> np.ndarray:
        """获取参数向量"""
        params = []

        if self.estimate_roughness:
            params.append(self.parameters['roughness'])

        if self.estimate_leakage:
            params.extend(self.parameters['leakage'])

        return np.array(params)

    def _set_parameter_vector(self, param_vec: np.ndarray):
        """设置参数向量"""
        idx = 0

        if self.estimate_roughness:
            self.parameters['roughness'] = param_vec[idx]
            # 更新求解器参数
            self.solver.n = max(0.01, min(0.1, param_vec[idx]))  # 约束范围
            idx += 1

        if self.estimate_leakage:
            self.parameters['leakage'] = param_vec[idx:idx + self.nx]
            idx += self.nx

    def _get_augmented_state(self) -> np.ndarray:
        """获取增广状态向量"""
        state = np.concatenate([self.solver.h, self.solver.hu])
        params = self._get_parameter_vector()
        return np.concatenate([state, params])

    def _set_augmented_state(self, aug_state: np.ndarray):
        """设置增广状态向量"""
        self.solver.h = aug_state[:self.nx]
        self.solver.hu = aug_state[self.nx:self.state_dim]
        self._set_parameter_vector(aug_state[self.state_dim:])

    def predict_step(
        self,
        Q_upstream: Optional[float] = None,
        h_downstream: Optional[float] = None
    ):
        """
        预测步（增广EKF）

        状态预测：使用物理模型
        参数预测：参数保持不变（随机游走模型）
        """
        # 保存边界条件（用于敏感度计算）
        self.current_Q_upstream = Q_upstream if Q_upstream is not None else 0.0
        self.current_h_downstream = h_downstream if h_downstream is not None else 0.0

        # 状态预测
        h_pred, hu_pred = self.solver.step_preissmann(
            dt=self.dt,
            max_iter=10,
            enforce_bc=True,
            Q_in=Q_upstream,
            h_out=h_downstream
        )

        self.solver.h = h_pred
        self.solver.hu = hu_pred

        # 参数保持不变（随机游走）
        # θ(k+1) = θ(k) + w_θ

        # 计算雅可比矩阵（简化：使用单位阵）
        F = np.eye(self.augmented_dim)

        # 协方差预测
        self.P = F @ self.P @ F.T + self.Q

    def _get_observation_matrix(self, sensor: Dict) -> np.ndarray:
        """
        获取观测矩阵（增广）

        H = [H_state | H_param]
        """
        H = np.zeros(self.augmented_dim)

        idx = sensor['location']
        sensor_type = sensor['type']

        if sensor_type == 'water_level':
            H[idx] = 1.0
        elif sensor_type == 'flow_rate':
            H[self.nx + idx] = self.solver.B
        elif sensor_type == 'velocity':
            h_current = self.solver.h[idx] + 1e-6
            H[self.nx + idx] = 1.0 / h_current

        # 参数部分：使用有限差分计算敏感度
        # ∂z/∂θ ≈ [z(θ+δθ) - z(θ)] / δθ
        if self.param_dim > 0:
            param_sensitivity = self._compute_parameter_sensitivity(
                sensor,
                self.current_Q_upstream,
                self.current_h_downstream
            )
            H[self.state_dim:] = param_sensitivity

        return H

    def _compute_parameter_sensitivity(
        self,
        sensor: Dict,
        Q_upstream: float,
        h_downstream: float
    ) -> np.ndarray:
        """
        使用动态有限差分计算参数敏感度

        通过扰动参数并运行一个时间步，测量状态变化，
        从而计算 ∂(observation)/∂(parameter)

        参数:
            sensor: 传感器信息
            Q_upstream: 当前上游流量
            h_downstream: 当前下游水位
        """
        sensitivity = np.zeros(self.param_dim)
        param_idx = 0

        # 保存当前状态
        h_save = self.solver.h.copy()
        hu_save = self.solver.hu.copy()

        # 基准观测值（当前参数）
        z_base = self._predict_measurement(sensor)

        if self.estimate_roughness:
            # 保存当前糙率
            n_base = self.solver.n

            # 扰动量（相对扰动1%）
            delta_n = max(0.0001, abs(n_base) * 0.01)

            # 扰动参数
            self.solver.n = n_base + delta_n

            # 运行一个时间步（使用扰动参数）
            try:
                h_pert, hu_pert = self.solver.step_preissmann(
                    dt=self.dt,
                    max_iter=10,
                    enforce_bc=True,
                    Q_in=Q_upstream,
                    h_out=h_downstream
                )

                # 更新求解器状态（临时）
                self.solver.h = h_pert
                self.solver.hu = hu_pert

                # 计算扰动后的观测值
                z_pert = self._predict_measurement(sensor)

                # 计算敏感度
                sensitivity[param_idx] = (z_pert - z_base) / delta_n

            except Exception as e:
                # 如果数值求解失败，使用零敏感度
                sensitivity[param_idx] = 0.0
                if self.verbose:
                    print(f"[警告] 敏感度计算失败: {e}")

            # 恢复参数和状态
            self.solver.n = n_base
            self.solver.h = h_save
            self.solver.hu = hu_save

            param_idx += 1

        if self.estimate_leakage:
            # 渗漏率敏感度分析
            # 渗漏率影响连续性方程: ∂h/∂t + ∂(hu)/∂x = -leak_rate

            # 保存原始渗漏率（如果存在）
            leak_base = getattr(self.solver, 'leak_rate', np.zeros(self.nx))
            if not hasattr(self.solver, 'leak_rate'):
                # 如果求解器没有渗漏率属性，添加它
                self.solver.leak_rate = np.zeros(self.nx)
                leak_base = self.solver.leak_rate.copy()

            # 对每个网格点的渗漏率进行扰动
            delta_leak = 1e-6  # 扰动量 (m/s)

            for i in range(self.nx):
                try:
                    # 保存当前状态
                    h_save = self.solver.h.copy()
                    hu_save = self.solver.hu.copy()

                    # 扰动第i个点的渗漏率
                    self.solver.leak_rate[i] += delta_leak

                    # 计算稳态（简化处理：假设渗漏率变化后快速达到新稳态）
                    # 在实际中，渗漏会通过连续性方程影响水深
                    # ∂h/∂t = -∂(hu)/∂x - leak_rate
                    # 稳态时: ∂(hu)/∂x = -leak_rate

                    # 简化估计：渗漏导致的水深变化
                    # Δh ≈ -leak_rate * dt（局部水量损失）
                    h_pert = self.solver.h.copy()
                    h_pert[i] -= delta_leak * self.dt  # 渗漏导致水深降低

                    # 更新求解器状态
                    self.solver.h = h_pert
                    # hu保持不变（一阶近似）

                    # 计算扰动后的观测值
                    z_pert = self._predict_measurement(sensor)

                    # 计算敏感度
                    sensitivity[param_idx] = (z_pert - z_base) / delta_leak

                except Exception as e:
                    # 如果计算失败，使用零敏感度
                    sensitivity[param_idx] = 0.0
                    if self.verbose:
                        print(f"[警告] 渗漏率敏感度计算失败 (i={i}): {e}")

                finally:
                    # 恢复参数和状态
                    self.solver.leak_rate[i] = leak_base[i]
                    self.solver.h = h_save
                    self.solver.hu = hu_save

                param_idx += 1

        return sensitivity

    def _predict_measurement(self, sensor: Dict) -> float:
        """预测传感器观测值"""
        idx = sensor['location']
        sensor_type = sensor['type']

        if sensor_type == 'water_level':
            return self.solver.h[idx]
        elif sensor_type == 'flow_rate':
            return self.solver.hu[idx] * self.solver.B
        elif sensor_type == 'velocity':
            h = self.solver.h[idx] + 1e-6
            return self.solver.hu[idx] / h
        else:
            raise ValueError(f"未知传感器类型: {sensor_type}")

    def update_step(
        self,
        measurements: Dict[str, float]
    ) -> Dict[str, float]:
        """
        更新步（增广EKF）

        同时更新状态和参数
        """
        innovations = {}

        for sensor_name, z in measurements.items():
            if sensor_name not in self.sensors:
                warnings.warn(f"未知传感器: {sensor_name}")
                continue

            sensor = self.sensors[sensor_name]

            # 观测矩阵
            H = self._get_observation_matrix(sensor)

            # 预测观测
            z_pred = self._predict_measurement(sensor)

            # 新息
            y = z - z_pred
            innovations[sensor_name] = y

            # 新息协方差
            R = sensor['noise_std'] ** 2
            S = H @ self.P @ H.T + R

            # 卡尔曼增益
            K = self.P @ H.T / S

            # 增广状态更新
            aug_state = self._get_augmented_state()
            aug_state_new = aug_state + K * y
            self._set_augmented_state(aug_state_new)

            # 协方差更新
            I = np.eye(self.augmented_dim)
            self.P = (I - np.outer(K, H)) @ self.P

        return innovations

    def run_estimation(
        self,
        t_end: float,
        Q_upstream_func: Callable[[float], float],
        h_downstream_func: Callable[[float], float],
        measurement_func: Callable[[float], Dict[str, float]],
        assimilation_interval: int = 1
    ) -> Dict:
        """
        运行参数估计

        Args:
            t_end: 结束时间
            Q_upstream_func: 上游流量函数
            h_downstream_func: 下游水深函数
            measurement_func: 测量函数
            assimilation_interval: 同化间隔

        Returns:
            结果字典
        """
        n_steps = int(t_end / self.dt)

        if self.verbose:
            print(f"\n{'='*60}")
            print(f"参数在线估计")
            print(f"{'='*60}")
            print(f"时间步长: {self.dt} s")
            print(f"总步数: {n_steps}")
            print(f"估计参数: {', '.join(self.param_names)}")
            print(f"{'='*60}\n")

        # 清空历史
        self.history = {
            'time': [],
            'h': [],
            'Q': [],
            'parameters': {name: [] for name in self.param_names},
            'parameter_std': {name: [] for name in self.param_names},
            'measurements': [],
            'innovations': []
        }

        for step in range(n_steps + 1):
            t_current = step * self.dt

            # 记录状态
            self.history['time'].append(t_current)
            self.history['h'].append(self.solver.h.copy())
            self.history['Q'].append(self.solver.hu * self.solver.B)

            # 记录参数
            param_vec = self._get_parameter_vector()
            param_std = np.sqrt(np.diag(self.P)[self.state_dim:])

            idx = 0
            if self.estimate_roughness:
                self.history['parameters']['roughness'].append(param_vec[idx])
                self.history['parameter_std']['roughness'].append(param_std[idx])
                idx += 1

            if self.estimate_leakage:
                for i in range(self.nx):
                    self.history['parameters'][f'leak_{i}'].append(param_vec[idx])
                    self.history['parameter_std'][f'leak_{i}'].append(param_std[idx])
                    idx += 1

            # 输出当前参数估计
            if self.verbose and step % 10 == 0:
                if self.estimate_roughness:
                    n_est = self.parameters['roughness']
                    n_std = param_std[0] if self.estimate_roughness else 0
                    print(f"t = {t_current:.1f} s: 糙率 n = {n_est:.4f} ± {n_std:.4f}")

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

        if self.verbose:
            print(f"\n{'='*60}")
            print(f"参数估计完成")
            self._print_final_parameters()
            print(f"{'='*60}\n")

        return self.history

    def _print_final_parameters(self):
        """打印最终参数估计"""
        print(f"\n最终参数估计:")

        if self.estimate_roughness:
            n_est = self.parameters['roughness']
            n_history = self.history['parameters']['roughness']
            n_std_history = self.history['parameter_std']['roughness']

            n_initial = n_history[0]
            n_final = n_history[-1]
            n_std_final = n_std_history[-1]

            print(f"  糙率 n:")
            print(f"    初始值: {n_initial:.4f}")
            print(f"    最终值: {n_final:.4f} ± {n_std_final:.4f}")
            print(f"    变化: {(n_final - n_initial)/n_initial*100:+.2f}%")

        if self.estimate_leakage:
            leak_mean = np.mean(self.parameters['leakage'])
            leak_std = np.std(self.parameters['leakage'])
            print(f"  渗漏率:")
            print(f"    平均: {leak_mean:.6f} m/s")
            print(f"    标准差: {leak_std:.6f} m/s")

    def get_parameter_estimates(self) -> Dict:
        """获取当前参数估计"""
        estimates = {}

        param_vec = self._get_parameter_vector()
        param_std = np.sqrt(np.diag(self.P)[self.state_dim:])

        idx = 0
        if self.estimate_roughness:
            estimates['roughness'] = {
                'value': param_vec[idx],
                'std': param_std[idx]
            }
            idx += 1

        if self.estimate_leakage:
            estimates['leakage'] = {
                'value': param_vec[idx:idx + self.nx],
                'std': param_std[idx:idx + self.nx]
            }

        return estimates
