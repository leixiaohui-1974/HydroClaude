"""无迹卡尔曼滤波（UKF）参数辨识"""
import numpy as np
from typing import Callable

class UnscentedKalmanFilter:
    """UKF参数辨识器"""
    def __init__(self, n_states: int, n_params: int):
        self.n = n_states + n_params
        self.n_states = n_states
        
        self.x = np.zeros((self.n, 1))
        self.P = np.eye(self.n)
        self.Q = np.eye(self.n) * 0.01
        self.R = np.eye(n_states) * 0.1
        
        # UKF参数
        self.alpha = 1e-3
        self.beta = 2.0
        self.kappa = 0.0
        self.lambda_ = self.alpha**2 * (self.n + self.kappa) - self.n
        
        # 权重
        self.Wm = np.zeros(2*self.n + 1)
        self.Wc = np.zeros(2*self.n + 1)
        self.Wm[0] = self.lambda_ / (self.n + self.lambda_)
        self.Wc[0] = self.Wm[0] + (1 - self.alpha**2 + self.beta)
        for i in range(1, 2*self.n + 1):
            self.Wm[i] = 1 / (2 * (self.n + self.lambda_))
            self.Wc[i] = self.Wm[i]
    
    def _sigma_points(self):
        """生成sigma点"""
        n = self.n
        sqrt_matrix = np.linalg.cholesky((n + self.lambda_) * self.P)
        sigma = np.zeros((n, 2*n+1))
        sigma[:, 0] = self.x.flatten()
        for i in range(n):
            sigma[:, i+1] = self.x.flatten() + sqrt_matrix[:, i]
            sigma[:, n+i+1] = self.x.flatten() - sqrt_matrix[:, i]
        return sigma
    
    def predict(self, f: Callable, dt: float):
        """预测步"""
        sigma = self._sigma_points()
        sigma_pred = np.array([f(sigma[:, i].reshape(-1,1), dt).flatten() for i in range(2*self.n+1)]).T
        self.x = (sigma_pred @ self.Wm).reshape(-1, 1)
        self.P = self.Q.copy()
        for i in range(2*self.n+1):
            diff = (sigma_pred[:, i] - self.x.flatten()).reshape(-1, 1)
            self.P += self.Wc[i] * (diff @ diff.T)
        return self.x[:self.n_states]
    
    def update(self, z: np.ndarray, h: Callable):
        """更新步"""
        sigma = self._sigma_points()
        z_pred = np.array([h(sigma[:, i].reshape(-1,1)).flatten() for i in range(2*self.n+1)]).T
        z_mean = (z_pred @ self.Wm).reshape(-1, 1)
        Pzz = self.R.copy()
        Pxz = np.zeros((self.n, self.n_states))
        for i in range(2*self.n+1):
            dz = (z_pred[:, i] - z_mean.flatten()).reshape(-1, 1)
            dx = (sigma[:, i] - self.x.flatten()).reshape(-1, 1)
            Pzz += self.Wc[i] * (dz @ dz.T)
            Pxz += self.Wc[i] * (dx @ dz.T)
        K = Pxz @ np.linalg.inv(Pzz)
        self.x = self.x + K @ (z - z_mean)
        self.P = self.P - K @ Pzz @ K.T
        return self.x[:self.n_states], self.x[self.n_states:]
