"""
状态估计模块

实现多种状态估计算法用于渠道控制系统：
- 卡尔曼滤波器 (KF)
- 扩展卡尔曼滤波器 (EKF)
- 无迹卡尔曼滤波器 (UKF)

应用场景：
- 融合模型预测和传感器测量
- 处理测量噪声和模型不确定性
- 提供最优状态估计用于控制

作者：HydroClaude Team
日期：2025-10-24
"""

import numpy as np
from typing import Callable, Tuple, Optional, List
from dataclasses import dataclass
from abc import ABC, abstractmethod


@dataclass
class EstimationResult:
    """状态估计结果"""
    x_est: np.ndarray      # 状态估计
    P: np.ndarray          # 误差协方差矩阵
    innovation: np.ndarray # 新息（测量残差）
    innovation_cov: np.ndarray  # 新息协方差
    likelihood: float      # 对数似然


class StateEstimator(ABC):
    """状态估计器基类"""

    @abstractmethod
    def predict(self, u: Optional[np.ndarray] = None):
        """
        预测步

        参数:
            u: 控制输入（可选）
        """
        pass

    @abstractmethod
    def update(self, z: np.ndarray):
        """
        更新步

        参数:
            z: 测量值
        """
        pass

    @abstractmethod
    def get_state(self) -> np.ndarray:
        """获取当前状态估计"""
        pass

    @abstractmethod
    def get_covariance(self) -> np.ndarray:
        """获取当前误差协方差矩阵"""
        pass


class KalmanFilter(StateEstimator):
    """
    卡尔曼滤波器（线性系统）

    状态方程: x(k+1) = A*x(k) + B*u(k) + w(k)
    测量方程: z(k) = H*x(k) + v(k)

    其中:
        w(k) ~ N(0, Q) - 过程噪声
        v(k) ~ N(0, R) - 测量噪声
    """

    def __init__(self,
                 A: np.ndarray,
                 B: np.ndarray,
                 H: np.ndarray,
                 Q: np.ndarray,
                 R: np.ndarray,
                 x0: np.ndarray,
                 P0: np.ndarray):
        """
        初始化卡尔曼滤波器

        参数:
            A: 状态转移矩阵 (n×n)
            B: 控制输入矩阵 (n×m)
            H: 测量矩阵 (p×n)
            Q: 过程噪声协方差矩阵 (n×n)
            R: 测量噪声协方差矩阵 (p×p)
            x0: 初始状态估计 (n,)
            P0: 初始误差协方差矩阵 (n×n)
        """
        self.A = A
        self.B = B
        self.H = H
        self.Q = Q
        self.R = R

        self.n = A.shape[0]  # 状态维度
        self.m = B.shape[1] if B.ndim > 1 else 1  # 控制输入维度
        self.p = H.shape[0]  # 测量维度

        # 状态估计
        self.x = x0.copy()
        self.P = P0.copy()

        # 预测状态（用于存储predict结果）
        self.x_pred = None
        self.P_pred = None

        # 历史记录
        self.history_x = [x0.copy()]
        self.history_P = [P0.copy()]
        self.history_innovation = []
        self.history_likelihood = []

    def predict(self, u: Optional[np.ndarray] = None):
        """
        预测步（时间更新）

        参数:
            u: 控制输入 (m,)
        """
        # 状态预测
        if u is not None:
            self.x_pred = self.A @ self.x + self.B @ u
        else:
            self.x_pred = self.A @ self.x

        # 协方差预测
        self.P_pred = self.A @ self.P @ self.A.T + self.Q

    def update(self, z: np.ndarray) -> EstimationResult:
        """
        更新步（测量更新）

        参数:
            z: 测量值 (p,)

        返回:
            result: 估计结果
        """
        # 使用预测状态（如果predict未调用，使用当前状态）
        if self.x_pred is None:
            self.predict()

        # 新息（测量残差）
        y = z - self.H @ self.x_pred

        # 新息协方差
        S = self.H @ self.P_pred @ self.H.T + self.R

        # 卡尔曼增益
        K = self.P_pred @ self.H.T @ np.linalg.inv(S)

        # 状态更新
        self.x = self.x_pred + K @ y

        # 协方差更新（Joseph形式，数值稳定）
        I_KH = np.eye(self.n) - K @ self.H
        self.P = I_KH @ self.P_pred @ I_KH.T + K @ self.R @ K.T

        # 计算对数似然
        log_likelihood = -0.5 * (
            np.log(2 * np.pi) * self.p +
            np.log(np.linalg.det(S)) +
            y.T @ np.linalg.inv(S) @ y
        )

        # 保存历史
        self.history_x.append(self.x.copy())
        self.history_P.append(self.P.copy())
        self.history_innovation.append(y.copy())
        self.history_likelihood.append(log_likelihood)

        # 重置预测状态
        self.x_pred = None
        self.P_pred = None

        return EstimationResult(
            x_est=self.x.copy(),
            P=self.P.copy(),
            innovation=y,
            innovation_cov=S,
            likelihood=log_likelihood
        )

    def get_state(self) -> np.ndarray:
        """获取当前状态估计"""
        return self.x.copy()

    def get_covariance(self) -> np.ndarray:
        """获取当前误差协方差矩阵"""
        return self.P.copy()

    def reset(self, x0: np.ndarray, P0: np.ndarray):
        """
        重置滤波器

        参数:
            x0: 初始状态估计
            P0: 初始误差协方差矩阵
        """
        self.x = x0.copy()
        self.P = P0.copy()
        self.x_pred = None
        self.P_pred = None
        self.history_x = [x0.copy()]
        self.history_P = [P0.copy()]
        self.history_innovation = []
        self.history_likelihood = []


class ExtendedKalmanFilter(StateEstimator):
    """
    扩展卡尔曼滤波器（非线性系统）

    状态方程: x(k+1) = f(x(k), u(k)) + w(k)
    测量方程: z(k) = h(x(k)) + v(k)

    其中:
        f: 非线性状态转移函数
        h: 非线性测量函数
        w(k) ~ N(0, Q) - 过程噪声
        v(k) ~ N(0, R) - 测量噪声
    """

    def __init__(self,
                 f: Callable[[np.ndarray, Optional[np.ndarray]], np.ndarray],
                 h: Callable[[np.ndarray], np.ndarray],
                 F_jacobian: Callable[[np.ndarray, Optional[np.ndarray]], np.ndarray],
                 H_jacobian: Callable[[np.ndarray], np.ndarray],
                 Q: np.ndarray,
                 R: np.ndarray,
                 x0: np.ndarray,
                 P0: np.ndarray):
        """
        初始化扩展卡尔曼滤波器

        参数:
            f: 非线性状态转移函数 x(k+1) = f(x(k), u(k))
            h: 非线性测量函数 z(k) = h(x(k))
            F_jacobian: f的雅可比矩阵函数 ∂f/∂x
            H_jacobian: h的雅可比矩阵函数 ∂h/∂x
            Q: 过程噪声协方差矩阵 (n×n)
            R: 测量噪声协方差矩阵 (p×p)
            x0: 初始状态估计 (n,)
            P0: 初始误差协方差矩阵 (n×n)
        """
        self.f = f
        self.h = h
        self.F_jacobian = F_jacobian
        self.H_jacobian = H_jacobian
        self.Q = Q
        self.R = R

        self.n = len(x0)  # 状态维度
        self.p = R.shape[0]  # 测量维度

        # 状态估计
        self.x = x0.copy()
        self.P = P0.copy()

        # 预测状态
        self.x_pred = None
        self.P_pred = None

        # 历史记录
        self.history_x = [x0.copy()]
        self.history_P = [P0.copy()]
        self.history_innovation = []
        self.history_likelihood = []

    def predict(self, u: Optional[np.ndarray] = None):
        """
        预测步（时间更新）

        参数:
            u: 控制输入
        """
        # 状态预测（使用非线性函数）
        self.x_pred = self.f(self.x, u)

        # 计算雅可比矩阵
        F = self.F_jacobian(self.x, u)

        # 协方差预测（使用线性化）
        self.P_pred = F @ self.P @ F.T + self.Q

    def update(self, z: np.ndarray) -> EstimationResult:
        """
        更新步（测量更新）

        参数:
            z: 测量值 (p,)

        返回:
            result: 估计结果
        """
        # 使用预测状态
        if self.x_pred is None:
            self.predict()

        # 预测测量值
        z_pred = self.h(self.x_pred)

        # 新息
        y = z - z_pred

        # 计算测量雅可比矩阵
        H = self.H_jacobian(self.x_pred)

        # 新息协方差
        S = H @ self.P_pred @ H.T + self.R

        # 卡尔曼增益
        K = self.P_pred @ H.T @ np.linalg.inv(S)

        # 状态更新
        self.x = self.x_pred + K @ y

        # 协方差更新
        I_KH = np.eye(self.n) - K @ H
        self.P = I_KH @ self.P_pred @ I_KH.T + K @ self.R @ K.T

        # 计算对数似然
        log_likelihood = -0.5 * (
            np.log(2 * np.pi) * self.p +
            np.log(np.linalg.det(S)) +
            y.T @ np.linalg.inv(S) @ y
        )

        # 保存历史
        self.history_x.append(self.x.copy())
        self.history_P.append(self.P.copy())
        self.history_innovation.append(y.copy())
        self.history_likelihood.append(log_likelihood)

        # 重置预测状态
        self.x_pred = None
        self.P_pred = None

        return EstimationResult(
            x_est=self.x.copy(),
            P=self.P.copy(),
            innovation=y,
            innovation_cov=S,
            likelihood=log_likelihood
        )

    def get_state(self) -> np.ndarray:
        """获取当前状态估计"""
        return self.x.copy()

    def get_covariance(self) -> np.ndarray:
        """获取当前误差协方差矩阵"""
        return self.P.copy()

    def reset(self, x0: np.ndarray, P0: np.ndarray):
        """重置滤波器"""
        self.x = x0.copy()
        self.P = P0.copy()
        self.x_pred = None
        self.P_pred = None
        self.history_x = [x0.copy()]
        self.history_P = [P0.copy()]
        self.history_innovation = []
        self.history_likelihood = []


class UnscentedKalmanFilter(StateEstimator):
    """
    无迹卡尔曼滤波器（非线性系统）

    使用无迹变换处理非线性，避免计算雅可比矩阵。
    通过选取sigma点来捕捉状态分布的均值和协方差。

    状态方程: x(k+1) = f(x(k), u(k)) + w(k)
    测量方程: z(k) = h(x(k)) + v(k)
    """

    def __init__(self,
                 f: Callable[[np.ndarray, Optional[np.ndarray]], np.ndarray],
                 h: Callable[[np.ndarray], np.ndarray],
                 Q: np.ndarray,
                 R: np.ndarray,
                 x0: np.ndarray,
                 P0: np.ndarray,
                 alpha: float = 1e-3,
                 beta: float = 2.0,
                 kappa: float = 0.0):
        """
        初始化无迹卡尔曼滤波器

        参数:
            f: 非线性状态转移函数
            h: 非线性测量函数
            Q: 过程噪声协方差矩阵 (n×n)
            R: 测量噪声协方差矩阵 (p×p)
            x0: 初始状态估计 (n,)
            P0: 初始误差协方差矩阵 (n×n)
            alpha: sigma点分布参数（通常1e-4 到 1）
            beta: 先验分布参数（高斯分布取2）
            kappa: 次要缩放参数（通常取0）
        """
        self.f = f
        self.h = h
        self.Q = Q
        self.R = R

        self.n = len(x0)  # 状态维度
        self.p = R.shape[0]  # 测量维度

        # UKF参数
        self.alpha = alpha
        self.beta = beta
        self.kappa = kappa

        # 计算lambda和权重
        self.lambda_ = alpha**2 * (self.n + kappa) - self.n
        self.gamma = np.sqrt(self.n + self.lambda_)

        # Sigma点权重
        self.Wm = np.zeros(2 * self.n + 1)  # 均值权重
        self.Wc = np.zeros(2 * self.n + 1)  # 协方差权重

        self.Wm[0] = self.lambda_ / (self.n + self.lambda_)
        self.Wc[0] = self.lambda_ / (self.n + self.lambda_) + (1 - alpha**2 + beta)

        for i in range(1, 2 * self.n + 1):
            self.Wm[i] = 1.0 / (2 * (self.n + self.lambda_))
            self.Wc[i] = 1.0 / (2 * (self.n + self.lambda_))

        # 状态估计
        self.x = x0.copy()
        self.P = P0.copy()

        # 预测状态
        self.x_pred = None
        self.P_pred = None

        # 历史记录
        self.history_x = [x0.copy()]
        self.history_P = [P0.copy()]
        self.history_innovation = []
        self.history_likelihood = []

    def _generate_sigma_points(self, x: np.ndarray, P: np.ndarray) -> np.ndarray:
        """
        生成sigma点

        参数:
            x: 状态均值 (n,)
            P: 状态协方差 (n×n)

        返回:
            sigma_points: sigma点矩阵 (2n+1, n)
        """
        sigma_points = np.zeros((2 * self.n + 1, self.n))

        # 计算矩阵平方根（Cholesky分解）
        try:
            L = np.linalg.cholesky(P)
        except np.linalg.LinAlgError:
            # 如果P不是正定的，使用特征值分解
            eigvals, eigvecs = np.linalg.eigh(P)
            eigvals = np.maximum(eigvals, 1e-10)  # 确保正定
            L = eigvecs @ np.diag(np.sqrt(eigvals))

        # 第一个sigma点
        sigma_points[0] = x

        # 其余sigma点
        for i in range(self.n):
            sigma_points[i + 1] = x + self.gamma * L[:, i]
            sigma_points[self.n + i + 1] = x - self.gamma * L[:, i]

        return sigma_points

    def predict(self, u: Optional[np.ndarray] = None):
        """
        预测步（时间更新）

        参数:
            u: 控制输入
        """
        # 生成sigma点
        sigma_points = self._generate_sigma_points(self.x, self.P)

        # 通过非线性函数传播sigma点
        sigma_points_pred = np.zeros_like(sigma_points)
        for i in range(2 * self.n + 1):
            sigma_points_pred[i] = self.f(sigma_points[i], u)

        # 预测状态均值
        self.x_pred = np.sum(self.Wm[:, None] * sigma_points_pred, axis=0)

        # 预测状态协方差
        self.P_pred = self.Q.copy()
        for i in range(2 * self.n + 1):
            diff = sigma_points_pred[i] - self.x_pred
            self.P_pred += self.Wc[i] * np.outer(diff, diff)

    def update(self, z: np.ndarray) -> EstimationResult:
        """
        更新步（测量更新）

        参数:
            z: 测量值 (p,)

        返回:
            result: 估计结果
        """
        # 使用预测状态
        if self.x_pred is None:
            self.predict()

        # 生成预测状态的sigma点
        sigma_points_pred = self._generate_sigma_points(self.x_pred, self.P_pred)

        # 通过测量函数传播sigma点
        sigma_points_meas = np.zeros((2 * self.n + 1, self.p))
        for i in range(2 * self.n + 1):
            sigma_points_meas[i] = self.h(sigma_points_pred[i])

        # 预测测量均值
        z_pred = np.sum(self.Wm[:, None] * sigma_points_meas, axis=0)

        # 新息
        y = z - z_pred

        # 新息协方差
        S = self.R.copy()
        for i in range(2 * self.n + 1):
            diff = sigma_points_meas[i] - z_pred
            S += self.Wc[i] * np.outer(diff, diff)

        # 状态-测量交叉协方差
        Pxz = np.zeros((self.n, self.p))
        for i in range(2 * self.n + 1):
            diff_x = sigma_points_pred[i] - self.x_pred
            diff_z = sigma_points_meas[i] - z_pred
            Pxz += self.Wc[i] * np.outer(diff_x, diff_z)

        # 卡尔曼增益
        K = Pxz @ np.linalg.inv(S)

        # 状态更新
        self.x = self.x_pred + K @ y

        # 协方差更新
        self.P = self.P_pred - K @ S @ K.T

        # 计算对数似然
        log_likelihood = -0.5 * (
            np.log(2 * np.pi) * self.p +
            np.log(np.linalg.det(S)) +
            y.T @ np.linalg.inv(S) @ y
        )

        # 保存历史
        self.history_x.append(self.x.copy())
        self.history_P.append(self.P.copy())
        self.history_innovation.append(y.copy())
        self.history_likelihood.append(log_likelihood)

        # 重置预测状态
        self.x_pred = None
        self.P_pred = None

        return EstimationResult(
            x_est=self.x.copy(),
            P=self.P.copy(),
            innovation=y,
            innovation_cov=S,
            likelihood=log_likelihood
        )

    def get_state(self) -> np.ndarray:
        """获取当前状态估计"""
        return self.x.copy()

    def get_covariance(self) -> np.ndarray:
        """获取当前误差协方差矩阵"""
        return self.P.copy()

    def reset(self, x0: np.ndarray, P0: np.ndarray):
        """重置滤波器"""
        self.x = x0.copy()
        self.P = P0.copy()
        self.x_pred = None
        self.P_pred = None
        self.history_x = [x0.copy()]
        self.history_P = [P0.copy()]
        self.history_innovation = []
        self.history_likelihood = []


# ==================== 辅助函数 ====================

def compute_consistency_test(innovations: List[np.ndarray],
                             innovation_covs: List[np.ndarray]) -> float:
    """
    计算新息一致性检验统计量

    用于验证滤波器是否一致（即误差协方差是否准确）。
    统计量应服从卡方分布。

    参数:
        innovations: 新息序列
        innovation_covs: 新息协方差序列

    返回:
        statistic: 检验统计量
    """
    n_samples = len(innovations)
    statistic = 0.0

    for y, S in zip(innovations, innovation_covs):
        statistic += y.T @ np.linalg.inv(S) @ y

    return statistic / n_samples


def compute_nees(true_states: List[np.ndarray],
                estimated_states: List[np.ndarray],
                covariances: List[np.ndarray]) -> float:
    """
    计算归一化估计误差平方（NEES）

    用于评估滤波器性能。NEES应服从卡方分布。

    参数:
        true_states: 真实状态序列
        estimated_states: 估计状态序列
        covariances: 误差协方差序列

    返回:
        nees: 平均NEES
    """
    n_samples = len(true_states)
    nees = 0.0

    for x_true, x_est, P in zip(true_states, estimated_states, covariances):
        error = x_true - x_est
        nees += error.T @ np.linalg.inv(P) @ error

    return nees / n_samples
