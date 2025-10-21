"""
递推最小二乘（RLS）参数辨识
在线实时估计系统参数
"""
import numpy as np
from typing import Dict, Optional, List
from dataclasses import dataclass

@dataclass
class RLSConfig:
    """RLS配置参数"""
    n_params: int  # 参数个数
    forgetting_factor: float = 0.98  # 遗忘因子 (0.95-0.99)
    initial_covariance: float = 1000.0  # 初始协方差
    regularization: float = 1e-6  # 正则化项

class RecursiveLeastSquares:
    """
    递推最小二乘辨识器

    模型形式：y[k] = phi[k]^T * theta

    其中：
    - y[k]: 输出（标量或向量）
    - phi[k]: 回归向量（包含历史输入输出）
    - theta: 参数向量

    递推公式：
    1. 增益: K[k] = P[k-1]*phi[k] / (lambda + phi[k]^T*P[k-1]*phi[k])
    2. 参数更新: theta[k] = theta[k-1] + K[k]*(y[k] - phi[k]^T*theta[k-1])
    3. 协方差更新: P[k] = (P[k-1] - K[k]*phi[k]^T*P[k-1]) / lambda
    """

    def __init__(self, config: RLSConfig):
        self.config = config

        # 参数向量
        self.theta = np.zeros((config.n_params, 1))

        # 协方差矩阵
        self.P = np.eye(config.n_params) * config.initial_covariance

        # 统计信息
        self.estimation_errors = []
        self.parameter_history = []
        self.update_count = 0

    def update(self, phi: np.ndarray, y: float) -> Dict:
        """
        RLS更新步骤

        Args:
            phi: 回归向量 [n_params, 1]
            y: 测量输出（标量）

        Returns:
            更新信息字典
        """
        phi = phi.reshape(-1, 1)  # 确保列向量

        # 预测输出
        y_pred = float(phi.T @ self.theta)

        # 预测误差
        e = y - y_pred

        # RLS更新
        lambda_f = self.config.forgetting_factor

        # 计算增益
        P_phi = self.P @ phi
        denominator = lambda_f + phi.T @ P_phi
        K = P_phi / (denominator + self.config.regularization)

        # 参数更新
        self.theta = self.theta + K * e

        # 协方差更新（Joseph form for numerical stability）
        I_minus_K_phi = np.eye(self.config.n_params) - K @ phi.T
        self.P = (I_minus_K_phi @ self.P @ I_minus_K_phi.T +
                 K @ K.T * self.config.regularization) / lambda_f

        # 记录历史
        self.estimation_errors.append(abs(e))
        self.parameter_history.append(self.theta.copy())
        self.update_count += 1

        # 限制历史长度
        max_history = 1000
        if len(self.estimation_errors) > max_history:
            self.estimation_errors = self.estimation_errors[-max_history:]
            self.parameter_history = self.parameter_history[-max_history:]

        return {
            'parameters': self.theta.copy(),
            'prediction_error': e,
            'covariance': self.P.copy(),
            'update_count': self.update_count
        }

    def get_parameters(self) -> np.ndarray:
        """获取当前参数估计"""
        return self.theta.copy()

    def get_confidence_intervals(self, confidence: float = 0.95) -> np.ndarray:
        """
        计算参数置信区间

        Args:
            confidence: 置信水平 (0-1)

        Returns:
            置信区间 [n_params, 2] (lower, upper)
        """
        from scipy import stats

        # t分布的临界值
        dof = max(1, self.update_count - self.config.n_params)
        t_critical = stats.t.ppf((1 + confidence) / 2, dof)

        # 标准差
        std = np.sqrt(np.diag(self.P)).reshape(-1, 1)

        # 置信区间
        lower = self.theta - t_critical * std
        upper = self.theta + t_critical * std

        return np.hstack([lower, upper])

    def reset(self):
        """重置辨识器"""
        self.theta = np.zeros((self.config.n_params, 1))
        self.P = np.eye(self.config.n_params) * self.config.initial_covariance
        self.estimation_errors = []
        self.parameter_history = []
        self.update_count = 0


class ARXIdentifier:
    """
    ARX模型辨识器

    模型：y[k] = a1*y[k-1] + ... + a_na*y[k-na] +
                 b1*u[k-d] + ... + b_nb*u[k-d-nb+1] + e[k]

    其中：
    - na: 输出阶数
    - nb: 输入阶数
    - d: 延迟
    """

    def __init__(self, na: int, nb: int, delay: int = 1,
                 forgetting_factor: float = 0.98):
        """
        Args:
            na: 输出阶数（AR部分）
            nb: 输入阶数（X部分）
            delay: 纯延迟
            forgetting_factor: 遗忘因子
        """
        self.na = na
        self.nb = nb
        self.delay = delay

        # 总参数个数
        n_params = na + nb

        # 创建RLS辨识器
        config = RLSConfig(
            n_params=n_params,
            forgetting_factor=forgetting_factor
        )
        self.rls = RecursiveLeastSquares(config)

        # 历史缓冲
        max_order = max(na, nb + delay)
        self.y_buffer = np.zeros(max_order)
        self.u_buffer = np.zeros(max_order)
        self.buffer_index = 0

    def update(self, u: float, y: float) -> Dict:
        """
        更新ARX模型

        Args:
            u: 当前输入
            y: 当前输出

        Returns:
            辨识信息
        """
        # 构造回归向量: phi = [y[k-1], ..., y[k-na], u[k-d], ..., u[k-d-nb+1]]
        phi = np.zeros((self.na + self.nb, 1))

        # AR部分（输出历史）
        for i in range(self.na):
            idx = (self.buffer_index - i - 1) % len(self.y_buffer)
            phi[i] = self.y_buffer[idx]

        # X部分（输入历史，考虑延迟）
        for i in range(self.nb):
            idx = (self.buffer_index - self.delay - i) % len(self.u_buffer)
            phi[self.na + i] = self.u_buffer[idx]

        # RLS更新
        result = self.rls.update(phi, y)

        # 更新缓冲区
        self.y_buffer[self.buffer_index] = y
        self.u_buffer[self.buffer_index] = u
        self.buffer_index = (self.buffer_index + 1) % len(self.y_buffer)

        # 解析参数
        theta = result['parameters']
        a_params = theta[:self.na].flatten()
        b_params = theta[self.na:].flatten()

        result['a_parameters'] = a_params
        result['b_parameters'] = b_params

        return result

    def predict(self, u: float, steps: int = 1) -> np.ndarray:
        """
        多步预测

        Args:
            u: 输入值（假设恒定）
            steps: 预测步数

        Returns:
            预测输出序列
        """
        theta = self.rls.get_parameters()
        a_params = theta[:self.na].flatten()
        b_params = theta[self.na:].flatten()

        y_pred = np.zeros(steps)
        y_hist = list(self.y_buffer[::-1][:self.na])
        u_hist = list(self.u_buffer[::-1][:self.nb + self.delay])

        for k in range(steps):
            # AR部分
            y_k = sum(a_params[i] * y_hist[i] for i in range(min(len(y_hist), self.na)))

            # X部分
            if k >= self.delay:
                for i in range(self.nb):
                    if i < len(u_hist):
                        y_k += b_params[i] * u_hist[i]

            y_pred[k] = y_k

            # 更新历史
            y_hist.insert(0, y_k)
            u_hist.insert(0, u)

            if len(y_hist) > self.na:
                y_hist.pop()
            if len(u_hist) > self.nb + self.delay:
                u_hist.pop()

        return y_pred

    def get_transfer_function(self) -> tuple:
        """
        获取传递函数表示

        Returns:
            (numerator, denominator) 多项式系数
        """
        theta = self.rls.get_parameters()
        a_params = theta[:self.na].flatten()
        b_params = theta[self.na:].flatten()

        # 分母: 1 - a1*z^-1 - a2*z^-2 - ...
        den = np.concatenate([[1], -a_params])

        # 分子: b1*z^-d + b2*z^-(d+1) + ...
        num = np.concatenate([np.zeros(self.delay), b_params])

        return num, den
