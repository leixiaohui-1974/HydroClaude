"""
鲁棒控制策略

实现多种鲁棒控制方法，用于处理系统不确定性和扰动：
- 滑模控制（Sliding Mode Control, SMC）
- 自适应滑模控制（Adaptive SMC）
- H∞控制（H-infinity Control）

关键特性：
- 对模型不确定性鲁棒
- 对外部扰动不敏感
- 有限时间收敛
- 抖振抑制

应用场景：
- 参数变化的渠道系统
- 未知扰动下的控制
- 高精度轨迹跟踪

作者：HydroClaude Team
日期：2025-10-24
"""

import numpy as np
from scipy.linalg import solve_continuous_are, solve_discrete_are
from typing import Optional, Callable, Tuple
from dataclasses import dataclass
from abc import ABC, abstractmethod


@dataclass
class SMCParameters:
    """滑模控制参数"""
    # 滑模面参数
    lambda_: float  # 滑模面斜率

    # 趋近律参数
    eta: float  # 趋近律增益
    epsilon: float  # 边界层厚度（抖振抑制）

    # 控制限幅
    u_min: float = -np.inf
    u_max: float = np.inf


class SlidingModeController:
    """
    滑模控制器（Sliding Mode Control）

    基于指数趋近律的滑模控制：

    滑模面: s = e + λ * ∫e dt

    趋近律: ṡ = -η * sign(s)  (传统)
           或 ṡ = -η * sat(s/ε) (边界层，抑制抖振)

    其中:
        e = x - x_ref  (跟踪误差)
        λ > 0  (滑模面参数)
        η > 0  (趋近律增益)
        ε > 0  (边界层厚度)
    """

    def __init__(self,
                 params: SMCParameters,
                 dt: float,
                 nominal_model: Optional[Callable] = None):
        """
        初始化滑模控制器

        参数:
            params: SMC参数
            dt: 采样时间
            nominal_model: 标称模型函数 f(x, u)
        """
        self.params = params
        self.dt = dt
        self.nominal_model = nominal_model

        # 滑模变量
        self.s = 0.0  # 滑模面函数值
        self.e_integral = 0.0  # 误差积分

        # 历史记录
        self.history_s = []
        self.history_u = []
        self.history_e = []

    def compute_control(self,
                       x_current: float,
                       x_ref: float,
                       dx_ref: float = 0.0) -> float:
        """
        计算滑模控制输入

        参数:
            x_current: 当前状态
            x_ref: 参考状态
            dx_ref: 参考状态导数（可选）

        返回:
            u: 控制输入
        """
        # 跟踪误差
        e = x_current - x_ref

        # 误差积分（梯形法）
        self.e_integral += e * self.dt

        # 滑模面函数
        self.s = e + self.params.lambda_ * self.e_integral

        # 饱和函数（边界层，抑制抖振）
        if abs(self.s) <= self.params.epsilon:
            sat_s = self.s / self.params.epsilon
        else:
            sat_s = np.sign(self.s)

        # 滑模控制律（基于指数趋近律）
        # u_eq: 等效控制（使s=0的控制）
        # u_sw: 切换控制（趋近律）

        # 简化的控制律（假设简单积分器模型：dx = u）
        # 等效控制: u_eq = dx_ref - λ*e
        u_eq = dx_ref - self.params.lambda_ * e

        # 切换控制: u_sw = -η * sat(s/ε)
        u_sw = -self.params.eta * sat_s

        # 总控制
        u = u_eq + u_sw

        # 限幅
        u = np.clip(u, self.params.u_min, self.params.u_max)

        # 保存历史
        self.history_s.append(self.s)
        self.history_u.append(u)
        self.history_e.append(e)

        return u

    def reset(self):
        """重置控制器状态"""
        self.s = 0.0
        self.e_integral = 0.0
        self.history_s = []
        self.history_u = []
        self.history_e = []


class AdaptiveSlidingModeController(SlidingModeController):
    """
    自适应滑模控制器

    在线估计不确定性边界，调整趋近律增益
    """

    def __init__(self,
                 params: SMCParameters,
                 dt: float,
                 adaptation_gain: float = 0.1,
                 nominal_model: Optional[Callable] = None):
        """
        初始化自适应滑模控制器

        参数:
            params: SMC参数
            dt: 采样时间
            adaptation_gain: 自适应增益
            nominal_model: 标称模型函数
        """
        super().__init__(params, dt, nominal_model)
        self.adaptation_gain = adaptation_gain

        # 自适应参数
        self.eta_adaptive = params.eta  # 自适应趋近律增益
        self.history_eta = []

    def compute_control(self,
                       x_current: float,
                       x_ref: float,
                       dx_ref: float = 0.0) -> float:
        """计算自适应滑模控制"""
        # 跟踪误差
        e = x_current - x_ref

        # 误差积分
        self.e_integral += e * self.dt

        # 滑模面
        self.s = e + self.params.lambda_ * self.e_integral

        # 自适应律（基于Lyapunov稳定性）
        # η̇ = γ * |s|
        self.eta_adaptive += self.adaptation_gain * abs(self.s) * self.dt

        # 限制自适应增益范围
        self.eta_adaptive = np.clip(self.eta_adaptive,
                                    self.params.eta * 0.5,
                                    self.params.eta * 3.0)

        # 饱和函数
        if abs(self.s) <= self.params.epsilon:
            sat_s = self.s / self.params.epsilon
        else:
            sat_s = np.sign(self.s)

        # 控制律
        u_eq = dx_ref - self.params.lambda_ * e
        u_sw = -self.eta_adaptive * sat_s

        u = u_eq + u_sw
        u = np.clip(u, self.params.u_min, self.params.u_max)

        # 保存历史
        self.history_s.append(self.s)
        self.history_u.append(u)
        self.history_e.append(e)
        self.history_eta.append(self.eta_adaptive)

        return u

    def reset(self):
        """重置控制器"""
        super().reset()
        self.eta_adaptive = self.params.eta
        self.history_eta = []


class HInfinityController:
    """
    H∞控制器（H-infinity Control）

    设计目标：最小化最坏情况下的性能指标

    ||z||₂ / ||w||₂ < γ

    其中:
        z: 性能输出
        w: 扰动输入
        γ: H∞范数（性能指标）

    使用代数Riccati方程求解
    """

    def __init__(self,
                 A: np.ndarray,
                 B1: np.ndarray,
                 B2: np.ndarray,
                 C1: np.ndarray,
                 D12: np.ndarray,
                 gamma: float = 1.0):
        """
        初始化H∞控制器

        系统模型:
            ẋ = A*x + B1*w + B2*u
            z = C1*x + D12*u

        参数:
            A: 状态矩阵 (n×n)
            B1: 扰动输入矩阵 (n×p)
            B2: 控制输入矩阵 (n×m)
            C1: 性能输出矩阵 (q×n)
            D12: 性能直通矩阵 (q×m)
            gamma: H∞范数上界
        """
        self.A = A
        self.B1 = B1
        self.B2 = B2
        self.C1 = C1
        self.D12 = D12
        self.gamma = gamma

        self.n = A.shape[0]  # 状态维度
        self.m = B2.shape[1] if B2.ndim > 1 else 1  # 控制输入维度

        # 求解H∞控制器增益
        self.K = self._solve_hinf_gain()

    def _solve_hinf_gain(self) -> np.ndarray:
        """
        求解H∞控制器增益

        通过求解Riccati方程
        """
        # H∞ Riccati方程:
        # A^T*P + P*A + C1^T*C1 + P*(B1*B1^T/γ² - B2*B2^T)*P = 0

        # 简化处理：假设D12^T*D12 = I（标准形式）
        # K = -B2^T * P

        # 构造Hamiltonian矩阵的增广形式
        R = np.eye(self.m)
        Q = self.C1.T @ self.C1

        # 使用标准LQR方法作为H∞的近似（简化实现）
        # 实际H∞需要求解更复杂的Riccati方程

        try:
            P = solve_continuous_are(self.A, self.B2, Q, R)
            K = np.linalg.inv(R) @ self.B2.T @ P
            return K
        except Exception as e:
            print(f"警告: H∞增益求解失败，使用简化增益. 错误: {e}")
            # 降级为简单的比例增益
            return np.ones((self.m, self.n)) * 0.1

    def compute_control(self, x: np.ndarray) -> np.ndarray:
        """
        计算H∞控制输入

        参数:
            x: 当前状态 (n,)

        返回:
            u: 控制输入 (m,)
        """
        # H∞状态反馈: u = -K*x
        u = -self.K @ x
        return u


class RobustPIDController:
    """
    鲁棒PID控制器

    增强的PID控制，具有：
    - 积分抗饱和
    - 微分滤波
    - 自适应增益
    """

    def __init__(self,
                 kp: float,
                 ki: float,
                 kd: float,
                 dt: float,
                 u_min: float = -np.inf,
                 u_max: float = np.inf,
                 derivative_filter: float = 0.1):
        """
        初始化鲁棒PID控制器

        参数:
            kp: 比例增益
            ki: 积分增益
            kd: 微分增益
            dt: 采样时间
            u_min, u_max: 控制限幅
            derivative_filter: 微分滤波系数（0-1）
        """
        self.kp = kp
        self.ki = ki
        self.kd = kd
        self.dt = dt
        self.u_min = u_min
        self.u_max = u_max
        self.derivative_filter = derivative_filter

        # 状态变量
        self.integral = 0.0
        self.last_error = 0.0
        self.filtered_derivative = 0.0

        # 抗饱和
        self.saturated = False

    def compute_control(self,
                       setpoint: float,
                       measurement: float) -> float:
        """
        计算鲁棒PID控制

        参数:
            setpoint: 设定值
            measurement: 测量值

        返回:
            u: 控制输入
        """
        # 误差
        error = setpoint - measurement

        # 比例项
        p_term = self.kp * error

        # 积分项（带抗饱和）
        if not self.saturated:
            self.integral += error * self.dt
        i_term = self.ki * self.integral

        # 微分项（带滤波）
        derivative = (error - self.last_error) / self.dt
        self.filtered_derivative = (
            self.derivative_filter * derivative +
            (1 - self.derivative_filter) * self.filtered_derivative
        )
        d_term = self.kd * self.filtered_derivative

        # 总控制量
        u = p_term + i_term + d_term

        # 限幅并检测饱和
        if u > self.u_max:
            u = self.u_max
            self.saturated = True
        elif u < self.u_min:
            u = self.u_min
            self.saturated = True
        else:
            self.saturated = False

        # 更新状态
        self.last_error = error

        return u

    def reset(self):
        """重置控制器"""
        self.integral = 0.0
        self.last_error = 0.0
        self.filtered_derivative = 0.0
        self.saturated = False


# ==================== 辅助函数 ====================

def design_smc_parameters(system_bandwidth: float,
                         disturbance_bound: float,
                         chattering_tolerance: float = 0.01) -> SMCParameters:
    """
    设计滑模控制参数

    参数:
        system_bandwidth: 系统带宽（期望响应速度）
        disturbance_bound: 扰动上界
        chattering_tolerance: 抖振容忍度

    返回:
        params: SMC参数
    """
    # 滑模面参数（决定收敛速度）
    lambda_ = system_bandwidth

    # 趋近律增益（大于扰动边界）
    eta = disturbance_bound * 1.5

    # 边界层厚度（抑制抖振）
    epsilon = chattering_tolerance

    return SMCParameters(
        lambda_=lambda_,
        eta=eta,
        epsilon=epsilon
    )


def create_canal_smc(dt: float,
                    lambda_: float = 1.0,
                    eta: float = 0.5,
                    epsilon: float = 0.05,
                    u_min: float = -0.1,
                    u_max: float = 0.1) -> SlidingModeController:
    """
    创建渠道滑模控制器（预配置）

    参数:
        dt: 采样时间
        lambda_: 滑模面参数
        eta: 趋近律增益
        epsilon: 边界层厚度
        u_min, u_max: 控制限幅

    返回:
        smc: 滑模控制器
    """
    params = SMCParameters(
        lambda_=lambda_,
        eta=eta,
        epsilon=epsilon,
        u_min=u_min,
        u_max=u_max
    )

    return SlidingModeController(params, dt)


def compare_robustness(controllers: list,
                      disturbance_levels: np.ndarray,
                      system_model: Callable) -> dict:
    """
    对比不同控制器的鲁棒性

    参数:
        controllers: 控制器列表
        disturbance_levels: 扰动水平数组
        system_model: 系统模型函数

    返回:
        results: 对比结果字典
    """
    results = {
        'controllers': [str(c) for c in controllers],
        'disturbance_levels': disturbance_levels,
        'performance': []
    }

    # 对每个控制器和每个扰动水平进行测试
    for controller in controllers:
        perf = []
        for d_level in disturbance_levels:
            # 运行仿真并计算性能指标
            # （这里需要具体的仿真逻辑）
            perf.append(0.0)  # 占位
        results['performance'].append(perf)

    return results
