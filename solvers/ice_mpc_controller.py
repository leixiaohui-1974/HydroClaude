#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
MPC冰期调度控制器 - Model Predictive Control for Ice Period Scheduling

南水北调中线工程冰期调度核心控制算法：
1. 基于ID模型的状态空间方程
2. 滚动时域优化（MPC）
3. 动态目标水位计算
4. 冰期特殊约束处理
5. 多渠池闸群联调

技术来源：
- 南水北调中线渠池控制ID模型
- MPC模型预测控制算法
- 数字孪生调度优化系统

控制目标：
- 水位稳定在目标水位附近
- 流速满足冰期约束 (V≤0.40m/s, Fr≤0.065)
- 闸门调节平稳

作者: HydroClaude Team
日期: 2025-11-02
"""

import numpy as np
from typing import Dict, List, Optional, Tuple, Callable
from dataclasses import dataclass
from enum import Enum
import warnings


class ControlMode(Enum):
    """控制模式"""
    NORMAL = "normal"           # 常规输水
    ICE_PERIOD = "ice_period"   # 冰期输水
    EMERGENCY = "emergency"     # 应急调度
    TRANSITION = "transition"   # 过渡期


@dataclass
class PoolParameters:
    """渠池参数"""
    length: float           # 渠池长度 (m)
    width: float            # 渠池宽度 (m)
    depth_design: float     # 设计水深 (m)
    slope: float            # 底坡
    manning_n: float        # 曼宁糙率
    delay_time: float       # 延迟时间 (s)
    storage_coeff: float    # 蓄量系数


@dataclass
class ControlConstraints:
    """控制约束"""
    h_min: float            # 最小水位 (m)
    h_max: float            # 最大水位 (m)
    Q_min: float            # 最小流量 (m³/s)
    Q_max: float            # 最大流量 (m³/s)
    V_max: float            # 最大流速 (m/s)
    Fr_max: float           # 最大Froude数
    G_min: float            # 最小闸门开度 (m)
    G_max: float            # 最大闸门开度 (m)
    dG_max: float           # 最大闸门调节速率 (m/step)


class IDPoolModel:
    """
    积分延迟(ID)渠池模型

    ID模型将复杂的Saint-Venant方程简化为积分器+纯延迟的低阶模型：
    Y(s) = (A_s/s) * e^(-τ_d*s) * U(s)

    时域形式：
    y(t) = A_s * ∫₀^(t-τ_d) u(τ) dτ

    其中：
    - A_s: 渠池蓄量系数 (backwater area)
    - τ_d: 延迟时间 (delay time)
    """

    def __init__(
        self,
        length: float,
        width: float,
        depth: float,
        slope: float,
        g: float = 9.81
    ):
        """
        初始化ID渠池模型

        Parameters
        ----------
        length : float
            渠池长度 (m)
        width : float
            渠池宽度 (m)
        depth : float
            设计水深 (m)
        slope : float
            底坡
        g : float
            重力加速度 (m/s²)
        """
        self.L = length
        self.B = width
        self.h0 = depth
        self.S0 = slope
        self.g = g

        # 计算ID模型参数
        self._compute_model_parameters()

    def _compute_model_parameters(self):
        """计算ID模型参数"""
        # 断面积
        A0 = self.B * self.h0

        # 波速
        c0 = np.sqrt(self.g * A0 / self.B)

        # 断面平均流速（假设正常水深）
        V0 = np.sqrt(self.S0 * self.g * self.h0)
        V0 = min(V0, 1.0)  # 限制最大流速

        # 延迟时间（基于特征线法）
        self.tau_d = self.L / (V0 + c0 + 1e-6)

        # 蓄量系数（闸前常水位控制）
        self.A_s = 1.0 / (self.B + 1e-6)

        # 流量增益
        self.K_q = 1.0

    def get_state_space_matrices(self, dt: float) -> Tuple[float, float]:
        """
        获取离散化状态空间矩阵

        x(k+1) = A * x(k) + B * u(k)

        Parameters
        ----------
        dt : float
            时间步长 (s)

        Returns
        -------
        A, B : float
            状态空间矩阵系数
        """
        # 一阶近似离散化
        A = 1.0 - dt / (self.tau_d + 1e-6)
        A = np.clip(A, 0.0, 1.0)

        B = self.K_q * dt / (self.tau_d + 1e-6)

        return A, B


class MultiPoolMPCController:
    """
    多渠池MPC控制器

    状态空间方程：
    x(k+1) = A*x(k) + B*u(k) + E*d(k)
    y(k) = C*x(k)

    目标函数：
    min J = Σ||y-y_ref||²_Q + Σ||Δu||²_R

    约束条件：
    - 水力约束：V ≤ 0.40 m/s, Fr ≤ 0.065
    - 冰情约束：T_w ≥ 1.2℃触发冰期模式
    - 设备约束：G_min ≤ G ≤ G_max, |ΔG| ≤ ΔG_max
    """

    def __init__(
        self,
        n_pools: int,
        pool_params: List[PoolParameters],
        constraints: ControlConstraints,
        dt: float = 300.0,      # 控制周期 (s)
        Np: int = 10,           # 预测时域
        Nc: int = 5,            # 控制时域
        Q_weight: float = 1.0,  # 水位偏差权重
        R_weight: float = 0.1   # 控制量变化权重
    ):
        """
        初始化多渠池MPC控制器

        Parameters
        ----------
        n_pools : int
            渠池数量
        pool_params : List[PoolParameters]
            各渠池参数
        constraints : ControlConstraints
            控制约束
        dt : float
            控制周期 (s)
        Np : int
            预测时域（步数）
        Nc : int
            控制时域（步数）
        Q_weight : float
            水位偏差权重
        R_weight : float
            控制量变化权重
        """
        self.n_pools = n_pools
        self.pool_params = pool_params
        self.constraints = constraints
        self.dt = dt
        self.Np = Np
        self.Nc = Nc
        self.Q_weight = Q_weight
        self.R_weight = R_weight

        # 控制模式
        self.mode = ControlMode.NORMAL

        # 初始化渠池模型
        self._init_pool_models()

        # 构建状态空间矩阵
        self._build_state_space()

        # 目标水位
        self.h_target = np.array([p.depth_design for p in pool_params])

        # 历史状态
        self.x_history = []
        self.u_history = []

    def _init_pool_models(self):
        """初始化各渠池ID模型"""
        self.pool_models = []
        for p in self.pool_params:
            model = IDPoolModel(
                length=p.length,
                width=p.width,
                depth=p.depth_design,
                slope=p.slope
            )
            self.pool_models.append(model)

    def _build_state_space(self):
        """构建多渠池状态空间矩阵"""
        n = self.n_pools

        # 状态矩阵 A (n x n)
        self.A = np.zeros((n, n))
        for i in range(n):
            A_i, _ = self.pool_models[i].get_state_space_matrices(self.dt)
            self.A[i, i] = A_i

        # 输入矩阵 B (n x (n+1))
        # 每个渠池受上游闸门流入和下游闸门流出影响
        self.B = np.zeros((n, n + 1))
        for i in range(n):
            _, B_i = self.pool_models[i].get_state_space_matrices(self.dt)
            self.B[i, i] = B_i       # 上游闸门流入
            self.B[i, i + 1] = -B_i  # 下游闸门流出

        # 输出矩阵 C (n x n)
        self.C = np.eye(n)

        # 扰动矩阵 E (n x n) - 取水扰动
        self.E = np.eye(n) * 0.01

    def set_control_mode(self, mode: ControlMode):
        """设置控制模式"""
        self.mode = mode

        # 根据模式调整约束
        if mode == ControlMode.ICE_PERIOD:
            self.constraints.V_max = 0.40
            self.constraints.Fr_max = 0.065
            self.constraints.Q_max = 58.0
        elif mode == ControlMode.NORMAL:
            self.constraints.V_max = 1.0
            self.constraints.Fr_max = 0.16
            self.constraints.Q_max = 350.0

    def compute_dynamic_target(
        self,
        Q_upstream: float,
        T_water: np.ndarray,
        T_air_forecast: float,
        ice_fraction: np.ndarray
    ) -> np.ndarray:
        """
        计算动态目标水位

        目标水位根据上游流量和冰情实时调整：
        h_target(k) = f(Q_upstream, T_w, T_air_forecast, ice_fraction)

        Parameters
        ----------
        Q_upstream : float
            上游流量 (m³/s)
        T_water : np.ndarray
            各渠池水温 (°C)
        T_air_forecast : float
            气温预报 (°C)
        ice_fraction : np.ndarray
            冰盖覆盖率

        Returns
        -------
        h_target : np.ndarray
            动态目标水位
        """
        h_target = self.h_target.copy()

        # 冰期调整：加大水位附近控制
        if self.mode == ControlMode.ICE_PERIOD:
            # 冰期水位提高10%
            ice_factor = 1.0 + 0.1 * ice_fraction
            h_target = h_target * ice_factor

        # 低温调整
        cold_factor = np.where(T_water < 1.2, 1.05, 1.0)
        h_target = h_target * cold_factor

        # 限制在允许范围内
        h_target = np.clip(h_target, self.constraints.h_min, self.constraints.h_max)

        return h_target

    def predict_states(
        self,
        x0: np.ndarray,
        u_sequence: np.ndarray,
        d_sequence: Optional[np.ndarray] = None
    ) -> np.ndarray:
        """
        预测未来状态序列

        Parameters
        ----------
        x0 : np.ndarray
            当前状态 (水位偏差)
        u_sequence : np.ndarray
            控制序列 (Nc x (n+1))
        d_sequence : np.ndarray, optional
            扰动序列 (Np x n)

        Returns
        -------
        x_pred : np.ndarray
            预测状态序列 (Np x n)
        """
        n = self.n_pools
        x_pred = np.zeros((self.Np, n))
        x = x0.copy()

        for k in range(self.Np):
            # 控制输入（超出控制时域后保持最后一个）
            u_k = u_sequence[min(k, self.Nc - 1)]

            # 扰动（如果提供）
            if d_sequence is not None:
                d_k = d_sequence[k]
            else:
                d_k = np.zeros(n)

            # 状态更新
            x = self.A @ x + self.B @ u_k + self.E @ d_k
            x_pred[k] = x

        return x_pred

    def solve_qp(
        self,
        x0: np.ndarray,
        h_target: np.ndarray,
        u_prev: np.ndarray,
        d_forecast: Optional[np.ndarray] = None
    ) -> np.ndarray:
        """
        求解MPC二次规划问题

        目标函数：
        min J = Σ||y-y_ref||²_Q + Σ||Δu||²_R

        Parameters
        ----------
        x0 : np.ndarray
            当前状态
        h_target : np.ndarray
            目标水位
        u_prev : np.ndarray
            上一步控制量
        d_forecast : np.ndarray, optional
            扰动预测

        Returns
        -------
        u_opt : np.ndarray
            最优控制序列
        """
        n = self.n_pools
        n_u = n + 1  # 闸门数量

        # 简化求解：使用梯度下降法
        # 初始化控制序列
        u_sequence = np.tile(u_prev, (self.Nc, 1))

        # 迭代优化
        learning_rate = 0.01
        max_iter = 50

        for iteration in range(max_iter):
            # 预测状态
            x_pred = self.predict_states(x0, u_sequence, d_forecast)

            # 计算目标函数
            J = 0.0
            for k in range(self.Np):
                # 水位偏差项
                y_error = x_pred[k] - (h_target - self.h_target)
                J += self.Q_weight * np.sum(y_error**2)

            for k in range(self.Nc):
                # 控制量变化项
                if k == 0:
                    delta_u = u_sequence[k] - u_prev
                else:
                    delta_u = u_sequence[k] - u_sequence[k-1]
                J += self.R_weight * np.sum(delta_u**2)

            # 数值梯度计算
            grad = np.zeros_like(u_sequence)
            eps = 1e-6

            for k in range(self.Nc):
                for j in range(n_u):
                    u_plus = u_sequence.copy()
                    u_plus[k, j] += eps
                    x_plus = self.predict_states(x0, u_plus, d_forecast)

                    J_plus = 0.0
                    for i in range(self.Np):
                        y_error = x_plus[i] - (h_target - self.h_target)
                        J_plus += self.Q_weight * np.sum(y_error**2)

                    grad[k, j] = (J_plus - J) / eps

            # 梯度更新
            u_sequence -= learning_rate * grad

            # 应用约束
            u_sequence = self._apply_constraints(u_sequence, u_prev)

        return u_sequence

    def _apply_constraints(
        self,
        u_sequence: np.ndarray,
        u_prev: np.ndarray
    ) -> np.ndarray:
        """应用控制约束"""
        n_u = self.n_pools + 1

        for k in range(self.Nc):
            # 闸门开度约束
            u_sequence[k] = np.clip(
                u_sequence[k],
                self.constraints.G_min,
                self.constraints.G_max
            )

            # 调节速率约束
            if k == 0:
                delta_u = u_sequence[k] - u_prev
            else:
                delta_u = u_sequence[k] - u_sequence[k-1]

            delta_u = np.clip(delta_u, -self.constraints.dG_max, self.constraints.dG_max)

            if k == 0:
                u_sequence[k] = u_prev + delta_u
            else:
                u_sequence[k] = u_sequence[k-1] + delta_u

        return u_sequence

    def step(
        self,
        h_current: np.ndarray,
        Q_upstream: float,
        T_water: np.ndarray,
        T_air_forecast: float,
        ice_fraction: np.ndarray,
        u_prev: np.ndarray,
        d_forecast: Optional[np.ndarray] = None
    ) -> Tuple[np.ndarray, Dict]:
        """
        执行一步MPC控制

        Parameters
        ----------
        h_current : np.ndarray
            当前水位 (m)
        Q_upstream : float
            上游流量 (m³/s)
        T_water : np.ndarray
            水温 (°C)
        T_air_forecast : float
            气温预报 (°C)
        ice_fraction : np.ndarray
            冰盖覆盖率
        u_prev : np.ndarray
            上一步控制量（闸门开度）
        d_forecast : np.ndarray, optional
            扰动预测

        Returns
        -------
        u_opt : np.ndarray
            最优闸门开度
        info : dict
            控制信息
        """
        # 检测控制模式切换
        if np.mean(T_water) < 1.2:
            self.set_control_mode(ControlMode.ICE_PERIOD)
        elif np.mean(T_water) > 3.0:
            self.set_control_mode(ControlMode.NORMAL)

        # 计算状态偏差
        x0 = h_current - self.h_target

        # 计算动态目标水位
        h_target_dynamic = self.compute_dynamic_target(
            Q_upstream, T_water, T_air_forecast, ice_fraction
        )

        # 求解MPC
        u_sequence = self.solve_qp(x0, h_target_dynamic, u_prev, d_forecast)

        # 取第一步控制量
        u_opt = u_sequence[0]

        # 保存历史
        self.x_history.append(x0.copy())
        self.u_history.append(u_opt.copy())

        # 控制信息
        info = {
            'mode': self.mode,
            'h_target': h_target_dynamic,
            'h_error': h_current - h_target_dynamic,
            'u_sequence': u_sequence,
            'x_predicted': self.predict_states(x0, u_sequence, d_forecast)
        }

        return u_opt, info


class JingShiIcePeriodController:
    """
    京石段冰期调度控制器

    针对南水北调中线京石段（217km，13渠池，14节制闸）的专用控制器

    特点：
    - 基于实测参数的ID模型
    - 冰期特殊约束（V≤0.40m/s, Fr≤0.065）
    - 动态目标水位（加大水位附近控制）
    - 与冰情预测系统联动
    """

    # 京石段13渠池参数
    JINGSHI_POOLS = [
        PoolParameters(length=15500, width=30.0, depth_design=3.0, slope=0.0001, manning_n=0.015, delay_time=7200, storage_coeff=0.033),
        PoolParameters(length=19700, width=28.0, depth_design=3.0, slope=0.0001, manning_n=0.015, delay_time=8500, storage_coeff=0.036),
        PoolParameters(length=17600, width=32.0, depth_design=3.2, slope=0.0001, manning_n=0.015, delay_time=7800, storage_coeff=0.031),
        PoolParameters(length=19200, width=30.0, depth_design=3.0, slope=0.0001, manning_n=0.015, delay_time=8200, storage_coeff=0.033),
        PoolParameters(length=16500, width=28.0, depth_design=2.8, slope=0.0001, manning_n=0.015, delay_time=7200, storage_coeff=0.036),
        PoolParameters(length=16500, width=26.0, depth_design=2.8, slope=0.0001, manning_n=0.015, delay_time=7000, storage_coeff=0.038),
        PoolParameters(length=17300, width=30.0, depth_design=3.0, slope=0.0001, manning_n=0.015, delay_time=7500, storage_coeff=0.033),
        PoolParameters(length=16300, width=32.0, depth_design=3.2, slope=0.0001, manning_n=0.015, delay_time=7200, storage_coeff=0.031),
        PoolParameters(length=16400, width=28.0, depth_design=2.8, slope=0.0001, manning_n=0.015, delay_time=7100, storage_coeff=0.036),
        PoolParameters(length=16500, width=26.0, depth_design=2.6, slope=0.0001, manning_n=0.015, delay_time=7000, storage_coeff=0.038),
        PoolParameters(length=16500, width=30.0, depth_design=3.0, slope=0.0001, manning_n=0.015, delay_time=7200, storage_coeff=0.033),
        PoolParameters(length=14500, width=28.0, depth_design=2.8, slope=0.0001, manning_n=0.015, delay_time=6300, storage_coeff=0.036),
        PoolParameters(length=14500, width=30.0, depth_design=3.0, slope=0.0001, manning_n=0.015, delay_time=6300, storage_coeff=0.033),
    ]

    # 冰期约束
    ICE_PERIOD_CONSTRAINTS = ControlConstraints(
        h_min=1.5,
        h_max=4.5,
        Q_min=10.0,
        Q_max=58.0,
        V_max=0.40,
        Fr_max=0.065,
        G_min=0.0,
        G_max=5.0,
        dG_max=0.1
    )

    def __init__(self, dt: float = 300.0):
        """
        初始化京石段冰期调度控制器

        Parameters
        ----------
        dt : float
            控制周期 (s)
        """
        self.dt = dt
        self.n_pools = 13
        self.n_gates = 14

        # 初始化MPC控制器
        self.mpc = MultiPoolMPCController(
            n_pools=self.n_pools,
            pool_params=self.JINGSHI_POOLS,
            constraints=self.ICE_PERIOD_CONSTRAINTS,
            dt=dt,
            Np=12,
            Nc=6
        )

        # 控制历史
        self.control_log = []

    def compute_ice_period_flow(
        self,
        T_water_avg: float,
        T_air_forecast: float,
        current_flow: float
    ) -> float:
        """
        计算冰期目标流量

        动态调度模式：
        - 水温 > 2.2°C: 常规流量 (350 m³/s)
        - 水温 1.2-2.2°C: 过渡期，线性调减
        - 水温 < 1.2°C: 冰期流量 (58/28 m³/s)

        Parameters
        ----------
        T_water_avg : float
            平均水温 (°C)
        T_air_forecast : float
            气温预报 (°C)
        current_flow : float
            当前流量 (m³/s)

        Returns
        -------
        Q_target : float
            目标流量 (m³/s)
        """
        Q_normal = 350.0
        Q_ice_high = 58.0
        Q_ice_low = 28.0
        T_trigger = 1.2

        if T_water_avg > T_trigger + 1.0:
            Q_target = Q_normal
        elif T_water_avg > T_trigger:
            # 过渡期
            ratio = (T_water_avg - T_trigger) / 1.0
            Q_target = Q_ice_high + ratio * (Q_normal - Q_ice_high)
        else:
            # 冰期
            if T_air_forecast < -10:
                Q_target = Q_ice_low
            else:
                Q_target = Q_ice_high

        # 平滑过渡，避免突变
        dQ_max = 10.0  # 每步最大流量变化
        Q_target = np.clip(Q_target, current_flow - dQ_max, current_flow + dQ_max)

        return Q_target

    def step(
        self,
        h_current: np.ndarray,
        Q_current: float,
        T_water: np.ndarray,
        T_air: float,
        T_air_forecast: List[float],
        ice_fraction: np.ndarray,
        gate_openings_prev: np.ndarray
    ) -> Tuple[np.ndarray, float, Dict]:
        """
        执行一步冰期调度

        Parameters
        ----------
        h_current : np.ndarray
            当前各渠池水位 (m)
        Q_current : float
            当前流量 (m³/s)
        T_water : np.ndarray
            各渠池水温 (°C)
        T_air : float
            当前气温 (°C)
        T_air_forecast : List[float]
            气温预报序列 (°C)
        ice_fraction : np.ndarray
            冰盖覆盖率
        gate_openings_prev : np.ndarray
            上一步闸门开度 (m)

        Returns
        -------
        gate_openings : np.ndarray
            最优闸门开度 (m)
        Q_target : float
            目标流量 (m³/s)
        info : dict
            调度信息
        """
        T_water_avg = np.mean(T_water)
        T_air_forecast_avg = np.mean(T_air_forecast[:3]) if len(T_air_forecast) >= 3 else T_air

        # 计算目标流量
        Q_target = self.compute_ice_period_flow(T_water_avg, T_air_forecast_avg, Q_current)

        # MPC控制
        gate_openings, mpc_info = self.mpc.step(
            h_current=h_current,
            Q_upstream=Q_target,
            T_water=T_water,
            T_air_forecast=T_air_forecast_avg,
            ice_fraction=ice_fraction,
            u_prev=gate_openings_prev
        )

        # 检查冰期约束
        violations = self._check_ice_constraints(h_current, Q_target, T_water, ice_fraction)

        # 记录日志
        log_entry = {
            'timestamp': len(self.control_log) * self.dt,
            'h_current': h_current.copy(),
            'Q_target': Q_target,
            'T_water_avg': T_water_avg,
            'T_air': T_air,
            'ice_fraction_avg': np.mean(ice_fraction),
            'gate_openings': gate_openings.copy(),
            'mode': self.mpc.mode,
            'violations': violations
        }
        self.control_log.append(log_entry)

        info = {
            **mpc_info,
            'Q_target': Q_target,
            'T_water_avg': T_water_avg,
            'violations': violations
        }

        return gate_openings, Q_target, info

    def _check_ice_constraints(
        self,
        h: np.ndarray,
        Q: float,
        T_water: np.ndarray,
        ice_fraction: np.ndarray
    ) -> Dict:
        """检查冰期约束"""
        violations = {
            'velocity': [],
            'froude': [],
            'water_level': [],
            'temperature': []
        }

        constraints = self.ICE_PERIOD_CONSTRAINTS
        g = 9.81

        for i in range(self.n_pools):
            pool = self.JINGSHI_POOLS[i]
            A = pool.width * h[i]
            V = Q / A

            # 流速约束
            if V > constraints.V_max:
                violations['velocity'].append({
                    'pool': i,
                    'value': V,
                    'limit': constraints.V_max
                })

            # Froude数约束
            Fr = V / np.sqrt(g * h[i])
            if Fr > constraints.Fr_max:
                violations['froude'].append({
                    'pool': i,
                    'value': Fr,
                    'limit': constraints.Fr_max
                })

            # 水位约束
            if h[i] < constraints.h_min or h[i] > constraints.h_max:
                violations['water_level'].append({
                    'pool': i,
                    'value': h[i],
                    'min': constraints.h_min,
                    'max': constraints.h_max
                })

        # 水温触发
        if np.mean(T_water) <= 1.2:
            violations['temperature'].append({
                'value': np.mean(T_water),
                'trigger': 1.2,
                'message': '已触发冰期调度模式'
            })

        return violations

    def get_control_summary(self) -> Dict:
        """获取控制总结"""
        if not self.control_log:
            return {}

        return {
            'total_steps': len(self.control_log),
            'current_mode': self.mpc.mode.value,
            'avg_water_level': np.mean([log['h_current'] for log in self.control_log]),
            'avg_flow': np.mean([log['Q_target'] for log in self.control_log]),
            'avg_water_temp': np.mean([log['T_water_avg'] for log in self.control_log]),
            'avg_ice_fraction': np.mean([log['ice_fraction_avg'] for log in self.control_log]),
            'total_violations': sum(
                len(log['violations']['velocity']) +
                len(log['violations']['froude']) +
                len(log['violations']['water_level'])
                for log in self.control_log
            )
        }
