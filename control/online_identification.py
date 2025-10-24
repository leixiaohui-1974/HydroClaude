"""
在线辨识模块

支持两大类在线辨识：
1. 河管渠系统：IDZ模型参数辨识
2. 闸泵阀水轮机：非线性特性辨识

辨识算法：
- 递推最小二乘（RLS）
- 扩展卡尔曼滤波（EKF）
- 遗忘因子RLS
- 自适应遗忘因子

作者：HydroClaude Team
日期：2025-10-24
"""

import numpy as np
import sys
import os
from dataclasses import dataclass, field
from typing import Optional, List, Tuple, Callable
from enum import Enum
from scipy.optimize import minimize

# 添加项目根目录
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

try:
    from idz_model import IDZParameters
except ImportError:
    # 如果作为模块导入
    from control.idz_model import IDZParameters


class IdentificationMethod(Enum):
    """辨识方法"""
    RLS = "recursive_least_squares"
    FORGETTING_RLS = "forgetting_factor_rls"
    ADAPTIVE_RLS = "adaptive_forgetting_rls"
    EKF = "extended_kalman_filter"


@dataclass
class RLSConfig:
    """递推最小二乘配置"""
    initial_P: float = 1000.0  # 初始协方差
    forgetting_factor: float = 0.98  # 遗忘因子 (0.95-0.99)
    min_forgetting_factor: float = 0.90  # 最小遗忘因子
    max_forgetting_factor: float = 0.999  # 最大遗忘因子
    adaptive_threshold: float = 0.1  # 自适应阈值


class RecursiveLeastSquares:
    """
    递推最小二乘辨识器

    用于线性参数化模型：y = φ^T * θ

    其中：
    - y: 输出
    - φ: 回归向量
    - θ: 参数向量
    """

    def __init__(self, n_params: int, config: Optional[RLSConfig] = None):
        """
        初始化RLS辨识器

        Args:
            n_params: 参数数量
            config: RLS配置
        """
        self.n_params = n_params
        self.config = config or RLSConfig()

        # 参数估计
        self.theta = np.zeros(n_params)

        # 协方差矩阵
        self.P = np.eye(n_params) * self.config.initial_P

        # 遗忘因子
        self.lambda_f = self.config.forgetting_factor

        # 历史记录
        self.estimation_error_history = []
        self.parameter_history = []

    def update(self, phi: np.ndarray, y: float) -> Tuple[np.ndarray, float]:
        """
        RLS更新步骤

        Args:
            phi: 回归向量 [n_params]
            y: 实际输出

        Returns:
            theta: 更新后的参数估计
            error: 估计误差
        """
        phi = phi.reshape(-1, 1)

        # 预测输出
        y_pred = (phi.T @ self.theta.reshape(-1, 1))[0, 0]

        # 估计误差
        error = y - y_pred

        # 增益
        P_phi = self.P @ phi
        denominator = self.lambda_f + phi.T @ P_phi
        K = P_phi / denominator

        # 参数更新
        self.theta = self.theta.flatten() + (K * error).flatten()

        # 协方差更新（Joseph form for numerical stability）
        I_Kphi = np.eye(self.n_params) - K @ phi.T
        self.P = (I_Kphi @ self.P @ I_Kphi.T + K @ K.T * 0.001) / self.lambda_f

        # 记录历史
        self.estimation_error_history.append(error)
        self.parameter_history.append(self.theta.copy())

        return self.theta, error

    def update_adaptive(self, phi: np.ndarray, y: float) -> Tuple[np.ndarray, float]:
        """
        自适应遗忘因子RLS

        根据估计误差自动调整遗忘因子

        Args:
            phi: 回归向量
            y: 实际输出

        Returns:
            theta: 更新后的参数估计
            error: 估计误差
        """
        # 先用当前遗忘因子更新
        theta, error = self.update(phi, y)

        # 根据误差调整遗忘因子
        if len(self.estimation_error_history) > 10:
            recent_errors = self.estimation_error_history[-10:]
            error_std = np.std(recent_errors)

            if abs(error) > error_std + self.config.adaptive_threshold:
                # 误差变大，降低遗忘因子（更快遗忘）
                self.lambda_f = max(self.config.min_forgetting_factor,
                                   self.lambda_f * 0.99)
            else:
                # 误差稳定，提高遗忘因子（更多记忆）
                self.lambda_f = min(self.config.max_forgetting_factor,
                                   self.lambda_f * 1.001)

        return theta, error

    def get_parameters(self) -> np.ndarray:
        """获取当前参数估计"""
        return self.theta.copy()

    def reset(self):
        """重置辨识器"""
        self.theta = np.zeros(self.n_params)
        self.P = np.eye(self.n_params) * self.config.initial_P
        self.lambda_f = self.config.forgetting_factor
        self.estimation_error_history = []
        self.parameter_history = []


class IDZIdentifier:
    """
    IDZ模型参数辨识器

    辨识IDZ模型的参数：K, τ_z, τ_d

    使用输入-输出数据在线估计参数
    """

    def __init__(self, dt: float, method: IdentificationMethod = IdentificationMethod.FORGETTING_RLS):
        """
        初始化IDZ辨识器

        Args:
            dt: 采样时间
            method: 辨识方法
        """
        self.dt = dt
        self.method = method

        # 离散时间模型参数
        # y(k) = a1*y(k-1) + a2*y(k-2) + b0*u(k-d) + b1*u(k-d-1) + b2*u(k-d-2)
        self.n_params = 7  # [a1, a2, b0, b1, b2, delay_steps, offset]

        # RLS辨识器
        self.rls = RecursiveLeastSquares(5)  # 不包括delay和offset

        # 数据缓冲
        self.y_buffer = []
        self.u_buffer = []

        # 当前估计的IDZ参数
        self.idz_params: Optional[IDZParameters] = None

        # 延迟估计
        self.estimated_delay = 0

    def update(self, u: float, y: float) -> Optional[IDZParameters]:
        """
        更新辨识

        Args:
            u: 输入（流量）
            y: 输出（水位）

        Returns:
            估计的IDZ参数（如果收敛）
        """
        # 添加到缓冲
        self.u_buffer.append(u)
        self.y_buffer.append(y)

        # 需要足够的数据才能辨识
        if len(self.y_buffer) < 10:
            return None

        # 构建回归向量
        # y(k) = a1*y(k-1) + a2*y(k-2) + b0*u(k-d) + b1*u(k-d-1) + b2*u(k-d-2)
        k = len(self.y_buffer) - 1

        if k >= 5:  # 需要至少5个历史数据
            d = self.estimated_delay

            phi = np.array([
                self.y_buffer[k-1] if k >= 1 else 0,
                self.y_buffer[k-2] if k >= 2 else 0,
                self.u_buffer[k-d] if k >= d else 0,
                self.u_buffer[k-d-1] if k >= d+1 else 0,
                self.u_buffer[k-d-2] if k >= d+2 else 0,
            ])

            y_k = self.y_buffer[k]

            # RLS更新
            if self.method == IdentificationMethod.ADAPTIVE_RLS:
                theta, error = self.rls.update_adaptive(phi, y_k)
            else:
                theta, error = self.rls.update(phi, y_k)

            # 每10步转换为IDZ参数（修正：提高更新频率）
            if k % 10 == 0:
                self.idz_params = self._discrete_to_idz(theta)

        # 保持缓冲大小
        if len(self.y_buffer) > 1000:
            self.y_buffer.pop(0)
            self.u_buffer.pop(0)

        return self.idz_params

    def _discrete_to_idz(self, theta: np.ndarray) -> IDZParameters:
        """
        从离散参数转换为IDZ参数

        离散模型: y(k) = a1*y(k-1) + a2*y(k-2) + b0*u(k) + b1*u(k-1) + b2*u(k-2)
        对应连续系统: G(s) = K*(1 + τ_z*s) / (s*(1 + τ_d*s))

        Args:
            theta: 离散参数 [a1, a2, b0, b1, b2]

        Returns:
            IDZ参数
        """
        a1, a2, b0, b1, b2 = theta

        # 简化估计（需要更精确的转换）
        # 这里使用近似公式
        dt = self.dt

        # 增益估计
        K = (b0 + b1 + b2) / (1 - a1 - a2) if abs(1 - a1 - a2) > 1e-6 else 100.0

        # 时间常数估计（粗略）
        tau_d = -dt / np.log(abs(a1)) if 0 < abs(a1) < 1 else 100.0 * dt
        tau_z = tau_d * 0.9  # 近似

        theta_delay = self.estimated_delay * dt

        # 限制参数范围
        K = np.clip(K, 1.0, 1000.0)
        tau_z = np.clip(tau_z, dt, 10000.0)
        tau_d = np.clip(tau_d, dt, 10000.0)
        theta_delay = np.clip(theta_delay, 0, 3600.0)

        return IDZParameters(K=K, tau_z=tau_z, tau_d=tau_d, theta=theta_delay)

    def get_idz_parameters(self) -> Optional[IDZParameters]:
        """获取当前IDZ参数估计"""
        return self.idz_params


class GateIdentifier:
    """
    闸门特性辨识器

    辨识闸门流量系数

    闸门流量方程：Q = C_d * b * a * sqrt(2*g*h)
    其中：
    - Q: 流量
    - C_d: 流量系数（待辨识）
    - b: 闸门宽度
    - a: 闸门开度
    - h: 上游水位
    """

    def __init__(self, gate_width: float):
        """
        初始化闸门辨识器

        Args:
            gate_width: 闸门宽度 (m)
        """
        self.gate_width = gate_width
        self.g = 9.81

        # RLS辨识（辨识C_d）
        self.rls = RecursiveLeastSquares(n_params=1)

        # 当前估计
        self.C_d = 0.6  # 初始估计

    def update(self, opening: float, head: float, flow: float) -> float:
        """
        更新辨识

        Args:
            opening: 闸门开度 (m)
            head: 上游水位 (m)
            flow: 实测流量 (m³/s)

        Returns:
            估计的流量系数C_d
        """
        if opening < 0.01 or head < 0.01:
            return self.C_d

        # 回归模型：Q = C_d * (b * a * sqrt(2*g*h))
        # 令 phi = b * a * sqrt(2*g*h)，则 Q = C_d * phi

        phi = np.array([self.gate_width * opening * np.sqrt(2 * self.g * head)])

        # RLS更新
        theta, error = self.rls.update(phi, flow)

        self.C_d = max(0.1, min(1.0, theta[0]))  # 限制在合理范围

        return self.C_d

    def predict_flow(self, opening: float, head: float) -> float:
        """预测流量"""
        if opening < 1e-6 or head < 1e-6:
            return 0.0
        return self.C_d * self.gate_width * opening * np.sqrt(2 * self.g * head)


class PumpIdentifier:
    """
    泵站特性辨识器

    辨识泵站扬程-流量特性曲线

    泵站方程：H = H0 - K*Q²
    其中：
    - H: 扬程
    - Q: 流量
    - H0: 零流量扬程（待辨识）
    - K: 曲线系数（待辨识）
    """

    def __init__(self):
        """初始化泵站辨识器"""
        # RLS辨识（辨识[H0, K]）
        self.rls = RecursiveLeastSquares(n_params=2)

        # 当前估计
        self.H0 = 50.0  # 初始估计
        self.K = 0.1    # 初始估计

    def update(self, flow: float, head: float) -> Tuple[float, float]:
        """
        更新辨识

        Args:
            flow: 流量 (m³/s)
            head: 扬程 (m)

        Returns:
            (H0, K): 估计的泵站参数
        """
        # 回归模型：H = H0 - K*Q²
        # 重写为：H = H0*1 + K*(-Q²)
        # phi = [1, -Q²]^T

        phi = np.array([1.0, -flow**2])

        # RLS更新
        theta, error = self.rls.update(phi, head)

        self.H0 = max(0.0, theta[0])
        self.K = max(0.0, theta[1])

        return self.H0, self.K

    def predict_head(self, flow: float) -> float:
        """预测扬程"""
        return max(0.0, self.H0 - self.K * flow**2)

    def predict_flow(self, head: float) -> float:
        """从扬程预测流量"""
        if self.K < 1e-6:
            return 0.0
        Q_squared = (self.H0 - head) / self.K
        if Q_squared < 0:
            return 0.0
        return np.sqrt(Q_squared)


class ValveIdentifier:
    """
    阀门特性辨识器

    辨识阀门开度-流量关系

    阀门方程：Q = K_v * opening * sqrt(Δp)
    其中：
    - Q: 流量
    - K_v: 阀门系数（待辨识）
    - opening: 开度 (0-1)
    - Δp: 压差
    """

    def __init__(self):
        """初始化阀门辨识器"""
        # RLS辨识（辨识K_v）
        self.rls = RecursiveLeastSquares(n_params=1)

        # 当前估计
        self.K_v = 10.0

    def update(self, opening: float, pressure_diff: float, flow: float) -> float:
        """
        更新辨识

        Args:
            opening: 阀门开度 (0-1)
            pressure_diff: 压差 (kPa)
            flow: 实测流量 (m³/s)

        Returns:
            估计的阀门系数K_v
        """
        if opening < 0.01 or pressure_diff < 0.01:
            return self.K_v

        # 回归模型：Q = K_v * (opening * sqrt(Δp))
        phi = np.array([opening * np.sqrt(pressure_diff)])

        # RLS更新
        theta, error = self.rls.update(phi, flow)

        self.K_v = max(0.1, theta[0])

        return self.K_v

    def predict_flow(self, opening: float, pressure_diff: float) -> float:
        """预测流量"""
        if opening < 1e-6 or pressure_diff < 1e-6:
            return 0.0
        return self.K_v * opening * np.sqrt(pressure_diff)


class TurbineIdentifier:
    """
    水轮机特性辨识器

    辨识水轮机功率-流量关系

    简化模型：P = η * ρ * g * H * Q
    其中：
    - P: 功率
    - η: 效率（待辨识）
    - H: 水头
    - Q: 流量
    """

    def __init__(self, rho: float = 1000.0, g: float = 9.81):
        """
        初始化水轮机辨识器

        Args:
            rho: 水密度 (kg/m³)
            g: 重力加速度 (m/s²)
        """
        self.rho = rho
        self.g = g

        # RLS辨识（辨识η）
        self.rls = RecursiveLeastSquares(n_params=1)

        # 当前估计
        self.efficiency = 0.85

    def update(self, head: float, flow: float, power: float) -> float:
        """
        更新辨识

        Args:
            head: 水头 (m)
            flow: 流量 (m³/s)
            power: 实测功率 (W)

        Returns:
            估计的效率η
        """
        if head < 0.1 or flow < 0.01:
            return self.efficiency

        # 回归模型：P = η * (ρ * g * H * Q)
        phi = np.array([self.rho * self.g * head * flow])

        # RLS更新
        theta, error = self.rls.update(phi, power)

        self.efficiency = np.clip(theta[0], 0.1, 0.98)

        return self.efficiency

    def predict_power(self, head: float, flow: float) -> float:
        """预测功率"""
        return self.efficiency * self.rho * self.g * head * flow


if __name__ == "__main__":
    """测试在线辨识"""

    print("=" * 70)
    print("在线辨识测试")
    print("=" * 70)

    # 测试1：RLS基本功能
    print("\n[测试1] RLS辨识器 - 线性系统")
    print("-" * 70)

    # 真实参数
    true_params = np.array([2.0, -1.5, 0.8])
    print(f"真实参数: {true_params}")

    rls = RecursiveLeastSquares(n_params=3)

    # 生成数据并辨识
    np.random.seed(42)
    for k in range(100):
        # 生成输入
        phi = np.random.randn(3)

        # 真实输出（加噪声）
        y_true = phi @ true_params
        y = y_true + np.random.randn() * 0.1

        # RLS更新
        theta_est, error = rls.update(phi, y)

        if k % 20 == 0:
            print(f"  步骤 {k:3d}: 估计 = [{theta_est[0]:6.3f}, {theta_est[1]:6.3f}, {theta_est[2]:6.3f}], "
                  f"误差 = {error:7.4f}")

    print(f"\n最终估计: {rls.get_parameters()}")
    print(f"估计误差: {np.linalg.norm(rls.get_parameters() - true_params):.6f}")

    # 测试2：闸门特性辨识
    print("\n[测试2] 闸门流量系数辨识")
    print("-" * 70)

    gate_width = 5.0  # 5m
    true_C_d = 0.65

    gate_id = GateIdentifier(gate_width)

    print(f"真实流量系数: {true_C_d}")
    print(f"初始估计: {gate_id.C_d}")

    np.random.seed(42)
    for k in range(50):
        # 模拟闸门运行
        opening = 0.5 + 0.3 * np.sin(2 * np.pi * k / 50)  # 变化的开度
        head = 3.0 + 0.5 * np.sin(2 * np.pi * k / 50)     # 变化的水位

        # 真实流量（加噪声）
        flow_true = true_C_d * gate_width * opening * np.sqrt(2 * 9.81 * head)
        flow = flow_true + np.random.randn() * 0.1

        # 辨识
        C_d_est = gate_id.update(opening, head, flow)

        if k % 10 == 0:
            print(f"  步骤 {k:2d}: C_d = {C_d_est:.4f}, 误差 = {abs(C_d_est - true_C_d):.5f}")

    print(f"\n最终估计: {gate_id.C_d:.4f}")

    # 测试3：泵站特性辨识
    print("\n[测试3] 泵站扬程-流量曲线辨识")
    print("-" * 70)

    true_H0 = 60.0
    true_K = 0.15

    pump_id = PumpIdentifier()

    print(f"真实参数: H0 = {true_H0}, K = {true_K}")
    print(f"初始估计: H0 = {pump_id.H0}, K = {pump_id.K}")

    np.random.seed(42)
    for k in range(50):
        # 模拟泵站运行
        flow = 5.0 + 3.0 * np.sin(2 * np.pi * k / 50)  # 变化的流量

        # 真实扬程（加噪声）
        head_true = true_H0 - true_K * flow**2
        head = head_true + np.random.randn() * 0.5

        # 辨识
        H0_est, K_est = pump_id.update(flow, head)

        if k % 10 == 0:
            print(f"  步骤 {k:2d}: H0 = {H0_est:5.2f}, K = {K_est:.4f}")

    print(f"\n最终估计: H0 = {pump_id.H0:.2f}, K = {pump_id.K:.4f}")
    print(f"真实值:   H0 = {true_H0:.2f}, K = {true_K:.4f}")

    # 测试4：水轮机效率辨识
    print("\n[测试4] 水轮机效率辨识")
    print("-" * 70)

    true_efficiency = 0.88

    turbine_id = TurbineIdentifier()

    print(f"真实效率: {true_efficiency}")
    print(f"初始估计: {turbine_id.efficiency}")

    np.random.seed(42)
    for k in range(50):
        # 模拟水轮机运行
        head = 50.0 + 5.0 * np.sin(2 * np.pi * k / 50)
        flow = 10.0 + 2.0 * np.sin(2 * np.pi * k / 50)

        # 真实功率（加噪声）
        power_true = true_efficiency * 1000.0 * 9.81 * head * flow
        power = power_true + np.random.randn() * 10000

        # 辨识
        eff_est = turbine_id.update(head, flow, power)

        if k % 10 == 0:
            print(f"  步骤 {k:2d}: η = {eff_est:.4f}, 误差 = {abs(eff_est - true_efficiency):.5f}")

    print(f"\n最终估计: {turbine_id.efficiency:.4f}")

    print("\n" + "=" * 70)
    print("在线辨识测试完成！")
    print("=" * 70)
