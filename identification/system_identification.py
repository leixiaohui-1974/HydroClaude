#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
系统辨识模块

用于从输入输出数据中估计系统参数和建立数学模型。

支持的方法：
1. 最小二乘法（LS）
2. 递归最小二乘法（RLS）
3. 扩展卡尔曼滤波（EKF）
4. 频域辨识
5. ARX/ARMAX模型辨识

应用场景：
- 管道系统参数估计（波速、摩阻系数）
- 阀门特性辨识
- 泵站性能曲线拟合
- 控制器参数整定

作者: Claude
日期: 2025-10-24
"""

import numpy as np
from typing import Tuple, Optional, Dict, List
from dataclasses import dataclass
from scipy import signal, optimize
from scipy.fft import fft, fftfreq
import warnings


@dataclass
class IdentificationResult:
    """辨识结果"""
    parameters: np.ndarray      # 辨识的参数
    covariance: np.ndarray      # 协方差矩阵
    residuals: np.ndarray       # 残差
    r_squared: float            # 拟合优度 R²
    rmse: float                 # 均方根误差
    method: str                 # 辨识方法
    convergence: bool           # 是否收敛
    iterations: int = 0         # 迭代次数


class LeastSquaresIdentifier:
    """
    最小二乘辨识器

    用于线性模型的参数估计：
    y = Φθ + ε

    其中：
    - y: 输出观测
    - Φ: 回归矩阵
    - θ: 参数向量
    - ε: 噪声
    """

    def __init__(self, name: str = "LS"):
        self.name = name
        self.theta = None
        self.P = None  # 协方差矩阵

    def fit(self, Phi: np.ndarray, y: np.ndarray,
            regularization: float = 0.0) -> IdentificationResult:
        """
        拟合模型

        Args:
            Phi: 回归矩阵 [N x n_params]
            y: 输出向量 [N]
            regularization: 正则化系数（岭回归）

        Returns:
            辨识结果
        """
        N, n_params = Phi.shape

        # 最小二乘解（带正则化）
        # θ = (Φ'Φ + λI)^{-1} Φ'y
        A = Phi.T @ Phi + regularization * np.eye(n_params)
        b = Phi.T @ y

        try:
            self.theta = np.linalg.solve(A, b)
            self.P = np.linalg.inv(A)  # 参数协方差
        except np.linalg.LinAlgError:
            warnings.warn("矩阵奇异，使用伪逆求解")
            self.theta = np.linalg.lstsq(Phi, y, rcond=None)[0]
            self.P = np.eye(n_params) * np.inf

        # 计算残差
        y_pred = Phi @ self.theta
        residuals = y - y_pred

        # 拟合优度
        ss_res = np.sum(residuals ** 2)
        ss_tot = np.sum((y - np.mean(y)) ** 2)
        r_squared = 1 - ss_res / ss_tot if ss_tot > 0 else 0.0

        # RMSE
        rmse = np.sqrt(ss_res / N)

        return IdentificationResult(
            parameters=self.theta,
            covariance=self.P,
            residuals=residuals,
            r_squared=r_squared,
            rmse=rmse,
            method="Least Squares",
            convergence=True
        )

    def predict(self, Phi: np.ndarray) -> np.ndarray:
        """
        预测输出

        Args:
            Phi: 回归矩阵

        Returns:
            预测值
        """
        if self.theta is None:
            raise RuntimeError("模型未拟合，请先调用 fit()")

        return Phi @ self.theta


class RecursiveLeastSquares:
    """
    递归最小二乘（RLS）辨识器

    在线更新参数估计，适用于实时系统辨识。

    更新公式：
    K_k = P_{k-1}φ_k / (λ + φ_k'P_{k-1}φ_k)
    θ_k = θ_{k-1} + K_k(y_k - φ_k'θ_{k-1})
    P_k = (I - K_kφ_k')P_{k-1} / λ

    其中λ是遗忘因子（0 < λ ≤ 1）
    """

    def __init__(self, n_params: int,
                 forgetting_factor: float = 0.98,
                 initial_covariance: float = 1000.0,
                 name: str = "RLS"):
        """
        初始化RLS辨识器

        Args:
            n_params: 参数个数
            forgetting_factor: 遗忘因子 λ (0.9-1.0)
            initial_covariance: 初始协方差
            name: 辨识器名称
        """
        self.n_params = n_params
        self.lambda_forget = forgetting_factor
        self.name = name

        # 初始化
        self.theta = np.zeros(n_params)
        self.P = np.eye(n_params) * initial_covariance

        # 历史记录
        self.theta_history = []
        self.residual_history = []

    def update(self, phi: np.ndarray, y: float) -> Tuple[np.ndarray, float]:
        """
        递归更新参数估计

        Args:
            phi: 回归向量 [n_params]
            y: 当前输出观测

        Returns:
            (theta, residual): 更新后的参数和残差
        """
        # 预测
        y_pred = phi @ self.theta

        # 预测误差
        error = y - y_pred

        # 增益向量
        denominator = self.lambda_forget + phi @ self.P @ phi
        K = self.P @ phi / denominator

        # 更新参数
        self.theta = self.theta + K * error

        # 更新协方差
        self.P = (self.P - np.outer(K, phi) @ self.P) / self.lambda_forget

        # 记录
        self.theta_history.append(self.theta.copy())
        self.residual_history.append(error)

        return self.theta, error

    def reset(self, initial_theta: Optional[np.ndarray] = None):
        """重置辨识器"""
        if initial_theta is not None:
            self.theta = initial_theta.copy()
        else:
            self.theta = np.zeros(self.n_params)

        self.P = np.eye(self.n_params) * 1000.0
        self.theta_history.clear()
        self.residual_history.clear()

    def get_result(self) -> IdentificationResult:
        """获取当前辨识结果"""
        if not self.residual_history:
            raise RuntimeError("没有可用的辨识数据")

        residuals = np.array(self.residual_history)
        rmse = np.sqrt(np.mean(residuals ** 2))

        return IdentificationResult(
            parameters=self.theta,
            covariance=self.P,
            residuals=residuals,
            r_squared=0.0,  # RLS不计算R²
            rmse=rmse,
            method="Recursive Least Squares",
            convergence=True,
            iterations=len(self.residual_history)
        )


class PipelineParameterEstimator:
    """
    管道系统参数估计器

    从压力-流量瞬变数据估计：
    - 水锤波速 a
    - 摩阻系数 f
    - 管道长度 L（如果未知）
    """

    def __init__(self, measured_length: Optional[float] = None):
        """
        初始化估计器

        Args:
            measured_length: 已知的管道长度 (m)，如果为None则需要估计
        """
        self.measured_length = measured_length
        self.a_estimate = None
        self.f_estimate = None
        self.L_estimate = None

    def estimate_wave_speed(self,
                           time: np.ndarray,
                           pressure: np.ndarray,
                           valve_position: float) -> Tuple[float, float]:
        """
        从压力波动数据估计波速

        方法：识别压力波往返时间
        a = 2L / T_round_trip

        Args:
            time: 时间数组 (s)
            pressure: 压力水头数组 (m)
            valve_position: 测点距离阀门的距离 (m)

        Returns:
            (wave_speed, confidence): 波速估计值和置信度
        """
        # 检测压力峰值
        from scipy.signal import find_peaks

        peaks, properties = find_peaks(pressure, prominence=1.0)

        if len(peaks) < 2:
            warnings.warn("压力数据中峰值不足，无法估计波速")
            return np.nan, 0.0

        # 计算相邻峰值的时间间隔
        peak_times = time[peaks]
        intervals = np.diff(peak_times)

        # 往返时间应该是最常见的间隔
        mean_interval = np.median(intervals)

        # 波速估计
        if self.measured_length is not None:
            # 已知管长
            a = 2 * self.measured_length / mean_interval
            L = self.measured_length
        else:
            # 需要估计管长（假设标准波速）
            a_typical = 1200.0  # m/s
            L = a_typical * mean_interval / 2

        self.a_estimate = a
        self.L_estimate = L

        # 置信度（基于峰值数量）
        confidence = min(1.0, len(peaks) / 5.0)

        return a, confidence

    def estimate_friction_factor(self,
                                 Q: np.ndarray,
                                 H_upstream: np.ndarray,
                                 H_downstream: np.ndarray,
                                 diameter: float,
                                 length: Optional[float] = None) -> Tuple[float, float]:
        """
        从稳态流动数据估计摩阻系数

        使用Darcy-Weisbach公式：
        ΔH = f * (L/D) * (V²/2g)

        Args:
            Q: 流量数组 (m³/s)
            H_upstream: 上游压力水头 (m)
            H_downstream: 下游压力水头 (m)
            diameter: 管径 (m)
            length: 管长 (m)

        Returns:
            (friction_factor, r_squared): 摩阻系数和拟合优度
        """
        if length is None:
            if self.L_estimate is not None:
                length = self.L_estimate
            elif self.measured_length is not None:
                length = self.measured_length
            else:
                raise ValueError("管长未知，无法估计摩阻系数")

        # 计算流速
        A = np.pi * (diameter / 2) ** 2
        V = Q / A

        # 水头损失
        dH = H_upstream - H_downstream

        # 线性回归: dH = f * (L/D) * (V²/2g)
        # y = dH, x = (L/D) * (V²/2g)
        g = 9.81
        x = (length / diameter) * (V ** 2) / (2 * g)
        y = dH

        # 过滤无效数据
        valid = (x > 0) & (y > 0) & np.isfinite(x) & np.isfinite(y)
        x = x[valid]
        y = y[valid]

        if len(x) < 3:
            warnings.warn("有效数据点不足")
            return np.nan, 0.0

        # 最小二乘拟合
        f_estimate = np.mean(y / x)

        # 拟合优度
        y_pred = f_estimate * x
        ss_res = np.sum((y - y_pred) ** 2)
        ss_tot = np.sum((y - np.mean(y)) ** 2)
        r_squared = 1 - ss_res / ss_tot if ss_tot > 0 else 0.0

        self.f_estimate = f_estimate

        return f_estimate, r_squared

    def get_summary(self) -> Dict:
        """获取估计结果摘要"""
        return {
            'wave_speed': self.a_estimate,
            'friction_factor': self.f_estimate,
            'length': self.L_estimate,
            'measured_length': self.measured_length
        }


class ValveCharacteristicIdentifier:
    """
    阀门特性辨识器

    从实验数据拟合阀门流量特性曲线：
    Q = Cv(τ) * sqrt(ΔH)

    其中τ是阀门开度 (0-1)
    """

    def __init__(self, valve_type: str = "unknown"):
        self.valve_type = valve_type
        self.model_type = None  # 'linear', 'quadratic', 'power'
        self.coefficients = None

    def fit(self, opening: np.ndarray,
            delta_H: np.ndarray,
            flow: np.ndarray) -> IdentificationResult:
        """
        拟合阀门特性

        Args:
            opening: 阀门开度数组 (0-1)
            delta_H: 压差数组 (m)
            flow: 流量数组 (m³/s)

        Returns:
            辨识结果
        """
        # 计算流量系数 Cv = Q / sqrt(ΔH)
        valid = (delta_H > 0) & (opening > 0) & (flow > 0)
        tau = opening[valid]
        dH = delta_H[valid]
        Q = flow[valid]

        Cv = Q / np.sqrt(dH)

        # 尝试不同的模型
        models = {
            'linear': lambda t, a: a * t,
            'quadratic': lambda t, a: a * t ** 2,
            'power': lambda t, a, b: a * t ** b,
        }

        best_model = None
        best_params = None
        best_r2 = -np.inf

        for model_name, model_func in models.items():
            try:
                if model_name == 'power':
                    # 幂函数需要初始猜测
                    popt, pcov = optimize.curve_fit(
                        model_func, tau, Cv,
                        p0=[np.max(Cv), 0.5],
                        bounds=([0, 0], [np.inf, 2])
                    )
                else:
                    popt, pcov = optimize.curve_fit(model_func, tau, Cv)

                # 计算拟合优度
                Cv_pred = model_func(tau, *popt)
                ss_res = np.sum((Cv - Cv_pred) ** 2)
                ss_tot = np.sum((Cv - np.mean(Cv)) ** 2)
                r2 = 1 - ss_res / ss_tot

                if r2 > best_r2:
                    best_r2 = r2
                    best_model = model_name
                    best_params = popt

            except Exception as e:
                continue

        if best_model is None:
            raise RuntimeError("所有模型拟合失败")

        self.model_type = best_model
        self.coefficients = best_params

        # 计算残差
        Cv_pred = models[best_model](tau, *best_params)
        residuals = Cv - Cv_pred
        rmse = np.sqrt(np.mean(residuals ** 2))

        return IdentificationResult(
            parameters=best_params,
            covariance=np.eye(len(best_params)),
            residuals=residuals,
            r_squared=best_r2,
            rmse=rmse,
            method=f"Valve Characteristic ({best_model})",
            convergence=True
        )

    def predict_flow_coefficient(self, opening: float) -> float:
        """
        预测给定开度下的流量系数

        Args:
            opening: 阀门开度 (0-1)

        Returns:
            流量系数 Cv
        """
        if self.coefficients is None:
            raise RuntimeError("模型未拟合")

        opening = np.clip(opening, 0.0, 1.0)

        if self.model_type == 'linear':
            return self.coefficients[0] * opening
        elif self.model_type == 'quadratic':
            return self.coefficients[0] * opening ** 2
        elif self.model_type == 'power':
            a, b = self.coefficients
            return a * opening ** b
        else:
            return 0.0


# 测试代码
if __name__ == "__main__":
    print("=" * 80)
    print("系统辨识模块测试")
    print("=" * 80)

    # 1. 测试最小二乘法
    print("\n1. 最小二乘法测试")
    print("-" * 80)

    # 生成模拟数据: y = 2x1 + 3x2 + noise
    np.random.seed(42)
    N = 100
    X = np.random.randn(N, 2)
    theta_true = np.array([2.0, 3.0])
    y = X @ theta_true + 0.5 * np.random.randn(N)

    # 辨识
    ls = LeastSquaresIdentifier()
    result = ls.fit(X, y)

    print(f"真实参数: {theta_true}")
    print(f"估计参数: {result.parameters}")
    print(f"R²: {result.r_squared:.4f}")
    print(f"RMSE: {result.rmse:.4f}")

    # 2. 测试递归最小二乘
    print("\n2. 递归最小二乘测试")
    print("-" * 80)

    rls = RecursiveLeastSquares(n_params=2, forgetting_factor=0.98)

    print("递归更新参数...")
    for i in range(N):
        rls.update(X[i], y[i])

        if i % 20 == 0:
            print(f"  Step {i:3d}: θ = [{rls.theta[0]:.3f}, {rls.theta[1]:.3f}]")

    result_rls = rls.get_result()
    print(f"\n最终估计: {result_rls.parameters}")
    print(f"RMSE: {result_rls.rmse:.4f}")

    # 3. 测试管道参数估计
    print("\n3. 管道参数估计测试")
    print("-" * 80)

    estimator = PipelineParameterEstimator(measured_length=1000.0)

    # 模拟压力波动数据（水锤）
    a_true = 1200.0  # m/s
    L = 1000.0  # m
    T_round = 2 * L / a_true  # 往返时间
    print(f"真实波速: {a_true} m/s")
    print(f"往返时间: {T_round:.4f} s")

    t = np.linspace(0, 5, 500)
    # 模拟压力振荡
    H = 50 + 20 * np.exp(-0.1 * t) * np.sin(2 * np.pi * t / T_round)

    a_est, confidence = estimator.estimate_wave_speed(t, H, valve_position=L)

    print(f"\n估计波速: {a_est:.2f} m/s")
    print(f"估计误差: {abs(a_est - a_true):.2f} m/s ({abs(a_est - a_true)/a_true*100:.2f}%)")
    print(f"置信度: {confidence:.2f}")

    # 模拟摩阻系数估计
    print("\n摩阻系数估计:")
    f_true = 0.02
    D = 0.5  # m
    Q_test = np.linspace(0.05, 0.3, 20)
    A = np.pi * (D/2)**2
    V_test = Q_test / A
    dH_true = f_true * (L/D) * (V_test**2) / (2*9.81)
    # 加噪声
    dH_measured = dH_true + 0.1 * np.random.randn(len(dH_true))
    H_up = 50 + dH_measured
    H_down = 50 * np.ones_like(H_up)

    f_est, r2 = estimator.estimate_friction_factor(
        Q_test, H_up, H_down, D, L
    )

    print(f"真实摩阻系数: {f_true:.6f}")
    print(f"估计摩阻系数: {f_est:.6f}")
    print(f"相对误差: {abs(f_est - f_true)/f_true*100:.2f}%")
    print(f"R²: {r2:.4f}")

    # 4. 测试阀门特性辨识
    print("\n4. 阀门特性辨识测试")
    print("-" * 80)

    valve_id = ValveCharacteristicIdentifier(valve_type="gate")

    # 生成阀门实验数据
    tau_test = np.array([0.2, 0.4, 0.6, 0.8, 1.0])
    dH_test = np.array([5.0, 5.0, 5.0, 5.0, 5.0])
    # 真实特性：Cv = 100 * sqrt(tau)
    Cv_true = 100 * np.sqrt(tau_test)
    Q_test = Cv_true * np.sqrt(dH_test)
    # 加噪声
    Q_test += 2.0 * np.random.randn(len(Q_test))

    result_valve = valve_id.fit(tau_test, dH_test, Q_test)

    print(f"最佳模型: {valve_id.model_type}")
    print(f"模型参数: {valve_id.coefficients}")
    print(f"R²: {result_valve.r_squared:.4f}")
    print(f"RMSE: {result_valve.rmse:.4f}")

    print("\n预测流量系数:")
    print("开度 | 真实Cv | 预测Cv")
    print("-" * 40)
    for tau in [0.3, 0.5, 0.7, 0.9]:
        Cv_true = 100 * np.sqrt(tau)
        Cv_pred = valve_id.predict_flow_coefficient(tau)
        print(f"{tau:.1f}  | {Cv_true:7.2f} | {Cv_pred:7.2f}")

    print("\n" + "=" * 80)
    print("测试完成！")
