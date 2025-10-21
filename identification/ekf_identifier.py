"""扩展卡尔曼滤波（EKF）参数辨识"""
import numpy as np
from typing import Callable

class ExtendedKalmanFilter:
    """EKF参数辨识器"""
    def __init__(self, n_states: int, n_params: int):
        self.n_states = n_states
        self.n_params = n_params
        n_total = n_states + n_params
        
        self.x = np.zeros((n_total, 1))  # 状态+参数
        self.P = np.eye(n_total) * 1.0
        self.Q = np.eye(n_total) * 0.01  # 过程噪声
        self.R = np.eye(n_states) * 0.1  # 测量噪声
    
    def predict(self, f: Callable, dt: float):
        """预测步"""
        F = self._numerical_jacobian(f, self.x, dt)
        self.x = f(self.x, dt)
        self.P = F @ self.P @ F.T + self.Q
        return self.x[:self.n_states]
    
    def update(self, z: np.ndarray, h: Callable):
        """更新步"""
        H = self._numerical_jacobian(h, self.x)
        y = z - h(self.x)
        S = H @ self.P @ H.T + self.R
        K = self.P @ H.T @ np.linalg.inv(S)
        self.x = self.x + K @ y
        self.P = (np.eye(len(self.x)) - K @ H) @ self.P
        return self.x[:self.n_states], self.x[self.n_states:]
    
    def _numerical_jacobian(self, f: Callable, x: np.ndarray, *args) -> np.ndarray:
        """数值雅可比"""
        eps = 1e-6
        n = len(x)
        J = np.zeros((n, n))
        f0 = f(x, *args)
        for i in range(n):
            x_eps = x.copy()
            x_eps[i] += eps
            J[:, i] = ((f(x_eps, *args) - f0) / eps).flatten()
        return J
