#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
递推最小二乘 (RLS) 系统辨识

实现在线参数辨识，支持：
- ARMAX模型辨识
- 遗忘因子自适应
- 模型验证

作者: Claude AI
日期: 2025-10-26
"""

import numpy as np
from typing import Tuple, Dict, Optional
import warnings


class RLSIdentifier:
    """
    递推最小二乘辨识器
    
    模型结构：
    A(z^-1) y(k) = B(z^-1) u(k-d) + e(k)
    
    其中：
    A(z^-1) = 1 + a1*z^-1 + a2*z^-2 + ... + an*z^-n
    B(z^-1) = b0 + b1*z^-1 + b2*z^-2 + ... + bm*z^-m
    """
    
    def __init__(self, 
                 n_a: int = 2,
                 n_b: int = 2,
                 n_d: int = 1,
                 lambda_forget: float = 0.98,
                 delta_init: float = 1000.0):
        """
        初始化RLS辨识器
        
        Args:
            n_a: A多项式阶数
            n_b: B多项式阶数
            n_d: 时滞步数
            lambda_forget: 遗忘因子 (0.9-0.99)
            delta_init: 初始协方差矩阵系数
        """
        self.n_a = n_a
        self.n_b = n_b
        self.n_d = n_d
        self.lambda_forget = lambda_forget
        
        # 参数向量长度
        self.n_theta = n_a + n_b + 1
        
        # 初始化参数
        self.theta = np.zeros(self.n_theta)
        
        # 初始化协方差矩阵
        self.P = np.eye(self.n_theta) * delta_init
        
        # 历史数据缓存
        self.y_history = []
        self.u_history = []
        
        # 验证指标
        self.fit_history = []
        self.residuals = []
        
    def reset(self):
        """重置辨识器"""
        self.theta = np.zeros(self.n_theta)
        self.P = np.eye(self.n_theta) * 1000.0
        self.y_history = []
        self.u_history = []
        self.fit_history = []
        self.residuals = []
        
    def update(self, y: float, u: float) -> Dict:
        """
        更新参数估计
        
        Args:
            y: 当前输出
            u: 当前输入
            
        Returns:
            info: 包含估计信息的字典
        """
        # 添加到历史
        self.y_history.append(y)
        self.u_history.append(u)
        
        # 需要足够的数据才能开始辨识
        min_data = max(self.n_a, self.n_b + self.n_d) + 1
        if len(self.y_history) < min_data:
            return {
                'theta': self.theta.copy(),
                'updated': False,
                'fit': 0.0
            }
        
        # 构造回归向量 phi
        phi = self._build_regressor()
        
        # RLS更新
        # 1. 计算增益
        P_phi = self.P @ phi
        denominator = self.lambda_forget + phi.T @ P_phi
        K = P_phi / denominator
        
        # 2. 预测误差
        y_pred = phi.T @ self.theta
        epsilon = y - y_pred
        
        # 3. 更新参数
        self.theta = self.theta + K * epsilon
        
        # 4. 更新协方差矩阵
        self.P = (self.P - np.outer(K, P_phi)) / self.lambda_forget
        
        # 确保P对称正定
        self.P = (self.P + self.P.T) / 2
        
        # 计算拟合度
        fit = self._calculate_fit()
        self.fit_history.append(fit)
        self.residuals.append(epsilon)
        
        return {
            'theta': self.theta.copy(),
            'updated': True,
            'fit': fit,
            'epsilon': epsilon,
            'y_pred': y_pred
        }
    
    def _build_regressor(self) -> np.ndarray:
        """
        构造回归向量
        
        phi(k) = [-y(k-1), -y(k-2), ..., -y(k-na),
                  u(k-d), u(k-d-1), ..., u(k-d-nb)]
        """
        phi = np.zeros(self.n_theta)
        
        # A多项式部分 (输出的过去值)
        for i in range(self.n_a):
            if i + 1 < len(self.y_history):
                phi[i] = -self.y_history[-(i+2)]
        
        # B多项式部分 (输入的过去值，考虑时滞)
        for i in range(self.n_b + 1):
            idx = i + self.n_d
            if idx < len(self.u_history):
                phi[self.n_a + i] = self.u_history[-(idx+1)]
        
        return phi
    
    def _calculate_fit(self, window: int = 50) -> float:
        """
        计算拟合度 (FIT)
        
        FIT = 100 * (1 - ||y - y_pred|| / ||y - mean(y)||)
        
        Args:
            window: 计算窗口长度
            
        Returns:
            fit: 拟合度百分比
        """
        if len(self.y_history) < window:
            return 0.0
        
        # 最近window个数据
        y_recent = np.array(self.y_history[-window:])
        
        # 预测
        y_pred = []
        for i in range(window):
            idx = len(self.y_history) - window + i
            if idx >= max(self.n_a, self.n_b + self.n_d):
                phi = self._build_regressor_at(idx)
                y_pred.append(phi.T @ self.theta)
            else:
                y_pred.append(y_recent[i])
        
        y_pred = np.array(y_pred)
        
        # 计算FIT
        numerator = np.linalg.norm(y_recent - y_pred)
        denominator = np.linalg.norm(y_recent - np.mean(y_recent))
        
        if denominator < 1e-10:
            return 0.0
        
        fit = 100 * (1 - numerator / denominator)
        return max(0.0, min(100.0, fit))
    
    def _build_regressor_at(self, k: int) -> np.ndarray:
        """在特定时刻k构造回归向量"""
        phi = np.zeros(self.n_theta)
        
        # A多项式部分
        for i in range(self.n_a):
            if k - i - 1 >= 0:
                phi[i] = -self.y_history[k - i - 1]
        
        # B多项式部分
        for i in range(self.n_b + 1):
            idx = k - i - self.n_d
            if idx >= 0:
                phi[self.n_a + i] = self.u_history[idx]
        
        return phi
    
    def get_transfer_function(self, dt: float = 1.0) -> Tuple[np.ndarray, np.ndarray]:
        """
        获取传递函数系数
        
        Returns:
            num: 分子系数
            den: 分母系数
        """
        # 分母: 1 + a1*z^-1 + a2*z^-2 + ...
        den = np.concatenate(([1.0], self.theta[:self.n_a]))
        
        # 分子: b0 + b1*z^-1 + b2*z^-2 + ...
        num = np.concatenate(([0.0] * self.n_d, self.theta[self.n_a:]))
        
        return num, den
    
    def predict(self, u_future: np.ndarray, n_steps: int) -> np.ndarray:
        """
        多步预测
        
        Args:
            u_future: 未来输入序列
            n_steps: 预测步数
            
        Returns:
            y_pred: 预测输出
        """
        y_pred = []
        
        # 临时历史
        y_temp = self.y_history.copy()
        u_temp = self.u_history.copy()
        
        for i in range(n_steps):
            # 添加未来输入
            if i < len(u_future):
                u_temp.append(u_future[i])
            else:
                u_temp.append(u_temp[-1])  # 保持最后一个值
            
            # 构造回归向量
            phi = np.zeros(self.n_theta)
            
            # A多项式
            for j in range(self.n_a):
                if j + 1 < len(y_temp):
                    phi[j] = -y_temp[-(j+2)]
            
            # B多项式
            for j in range(self.n_b + 1):
                idx = j + self.n_d
                if idx < len(u_temp):
                    phi[self.n_a + j] = u_temp[-(idx+1)]
            
            # 预测
            y_next = phi.T @ self.theta
            y_pred.append(y_next)
            y_temp.append(y_next)
        
        return np.array(y_pred)
    
    def get_model_info(self) -> Dict:
        """
        获取模型信息
        
        Returns:
            info: 模型信息字典
        """
        num, den = self.get_transfer_function()
        
        return {
            'n_a': self.n_a,
            'n_b': self.n_b,
            'n_d': self.n_d,
            'theta': self.theta.copy(),
            'num': num,
            'den': den,
            'n_samples': len(self.y_history),
            'fit': self.fit_history[-1] if self.fit_history else 0.0,
            'lambda': self.lambda_forget
        }
    
    def validate(self, y_val: np.ndarray, u_val: np.ndarray) -> Dict:
        """
        模型验证
        
        Args:
            y_val: 验证输出数据
            u_val: 验证输入数据
            
        Returns:
            metrics: 验证指标
        """
        # 预测
        y_pred = []
        y_temp = self.y_history.copy()
        u_temp = self.u_history.copy()
        
        for i in range(len(u_val)):
            u_temp.append(u_val[i])
            
            phi = np.zeros(self.n_theta)
            
            for j in range(self.n_a):
                if j + 1 < len(y_temp):
                    phi[j] = -y_temp[-(j+2)]
            
            for j in range(self.n_b + 1):
                idx = j + self.n_d
                if idx < len(u_temp):
                    phi[self.n_a + j] = u_temp[-(idx+1)]
            
            y_next = phi.T @ self.theta
            y_pred.append(y_next)
            y_temp.append(y_val[i])  # 使用真实值更新
        
        y_pred = np.array(y_pred)
        
        # 计算指标
        mse = np.mean((y_val - y_pred)**2)
        rmse = np.sqrt(mse)
        mae = np.mean(np.abs(y_val - y_pred))
        
        # VAF (Variance Accounted For)
        vaf = 100 * (1 - np.var(y_val - y_pred) / np.var(y_val))
        
        # FIT
        fit = 100 * (1 - np.linalg.norm(y_val - y_pred) / np.linalg.norm(y_val - np.mean(y_val)))
        
        return {
            'mse': mse,
            'rmse': rmse,
            'mae': mae,
            'vaf': vaf,
            'fit': fit,
            'y_pred': y_pred
        }


class AdaptiveRLS(RLSIdentifier):
    """
    自适应RLS - 带变遗忘因子
    
    根据预测误差动态调整遗忘因子
    """
    
    def __init__(self, 
                 n_a: int = 2,
                 n_b: int = 2,
                 n_d: int = 1,
                 lambda_min: float = 0.95,
                 lambda_max: float = 0.995,
                 adaptation_gain: float = 0.1):
        """
        初始化自适应RLS
        
        Args:
            lambda_min: 最小遗忘因子
            lambda_max: 最大遗忘因子
            adaptation_gain: 自适应增益
        """
        super().__init__(n_a, n_b, n_d, lambda_max)
        
        self.lambda_min = lambda_min
        self.lambda_max = lambda_max
        self.adaptation_gain = adaptation_gain
        
    def update(self, y: float, u: float) -> Dict:
        """
        自适应更新
        """
        info = super().update(y, u)
        
        if info['updated']:
            # 根据误差调整遗忘因子
            epsilon = abs(info['epsilon'])
            
            # 误差大时减小lambda（快速跟踪）
            # 误差小时增大lambda（平滑估计）
            if epsilon > 0.1:  # 阈值可调
                self.lambda_forget = max(self.lambda_min,
                                        self.lambda_forget - self.adaptation_gain * epsilon)
            else:
                self.lambda_forget = min(self.lambda_max,
                                        self.lambda_forget + self.adaptation_gain * 0.01)
        
        info['lambda'] = self.lambda_forget
        return info


if __name__ == "__main__":
    """测试RLS辨识器"""
    print("RLS辨识器测试")
    print("=" * 60)
    
    # 生成测试数据（一阶系统 + 时滞）
    from scipy import signal
    
    # 真实系统: G(s) = 1/(s+1) 离散化
    dt = 1.0
    sys_cont = signal.TransferFunction([1], [1, 1])
    sys_disc = signal.cont2discrete((sys_cont.num, sys_cont.den), dt)
    
    # 生成输入（PRBS）
    np.random.seed(42)
    n_samples = 500
    u = np.random.choice([-1, 1], n_samples)
    
    # 生成输出（带噪声）
    _, y = signal.dlsim((sys_disc[0], sys_disc[1], dt), u)
    y = y.flatten() + np.random.normal(0, 0.05, n_samples)
    
    # RLS辨识
    rls = RLSIdentifier(n_a=1, n_b=1, n_d=0, lambda_forget=0.98)
    
    print("\n1. 在线辨识...")
    for i in range(n_samples):
        info = rls.update(y[i], u[i])
        
        if i % 100 == 0 and i > 0:
            print(f"  样本 {i}: FIT={info['fit']:.1f}%, θ={info['theta']}")
    
    # 模型信息
    model_info = rls.get_model_info()
    print(f"\n2. 最终模型:")
    print(f"  阶数: na={model_info['n_a']}, nb={model_info['n_b']}, nd={model_info['n_d']}")
    print(f"  参数: {model_info['theta']}")
    print(f"  拟合度: {model_info['fit']:.2f}%")
    
    # 验证
    u_val = np.random.choice([-1, 1], 100)
    _, y_val = signal.dlsim((sys_disc[0], sys_disc[1], dt), u_val)
    y_val = y_val.flatten() + np.random.normal(0, 0.05, 100)
    
    metrics = rls.validate(y_val, u_val)
    print(f"\n3. 验证指标:")
    print(f"  RMSE: {metrics['rmse']:.4f}")
    print(f"  MAE: {metrics['mae']:.4f}")
    print(f"  VAF: {metrics['vaf']:.2f}%")
    print(f"  FIT: {metrics['fit']:.2f}%")
    
    print("\n✓ 测试完成")
