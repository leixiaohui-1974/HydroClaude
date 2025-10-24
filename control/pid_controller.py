#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
PID控制器 - 增强版

包含以下特性：
- 标准PID控制
- 抗积分饱和（Anti-windup）
- 输出限幅
- 微分滤波
- 性能监控
- 自动调参支持

作者: Claude
日期: 2025-10-24
"""

import numpy as np
from typing import Optional, Dict, List
from dataclasses import dataclass


@dataclass
class PIDConfig:
    """PID控制器配置"""
    kp: float = 1.0          # 比例增益
    ki: float = 0.1          # 积分增益
    kd: float = 0.05         # 微分增益

    # 输出限制
    output_min: float = -float('inf')   # 输出下限
    output_max: float = float('inf')    # 输出上限

    # 积分限制（抗饱和）
    integral_min: float = -float('inf')  # 积分项下限
    integral_max: float = float('inf')   # 积分项上限

    # 微分滤波系数（0-1，越小滤波越强）
    derivative_filter: float = 0.1

    # 死区
    deadband: float = 0.0    # 误差死区

    # 采样时间（秒）
    dt: float = 1.0


class PIDController:
    """
    PID控制器（增强版）

    实现标准PID控制律：
    u(t) = Kp·e(t) + Ki·∫e(τ)dτ + Kd·de(t)/dt

    特性：
    - 抗积分饱和
    - 输出限幅
    - 微分滤波（减少测量噪声影响）
    - 死区控制
    - 性能监控
    """

    def __init__(self, config: PIDConfig, name: str = "PID"):
        """
        初始化PID控制器

        Args:
            config: PID配置
            name: 控制器名称
        """
        self.config = config
        self.name = name

        # 控制参数
        self.kp = config.kp
        self.ki = config.ki
        self.kd = config.kd

        # 状态变量
        self.setpoint = 0.0          # 设定值
        self.integral = 0.0          # 积分项
        self.last_error = 0.0        # 上次误差
        self.last_derivative = 0.0   # 上次微分（用于滤波）
        self.last_output = 0.0       # 上次输出

        # 性能监控
        self.error_history: List[float] = []
        self.output_history: List[float] = []
        self.integral_history: List[float] = []
        self.derivative_history: List[float] = []

        # 统计信息
        self.step_count = 0
        self.total_abs_error = 0.0
        self.max_error = 0.0

    def set_gains(self, kp: Optional[float] = None,
                  ki: Optional[float] = None,
                  kd: Optional[float] = None):
        """
        设置PID增益

        Args:
            kp: 比例增益
            ki: 积分增益
            kd: 微分增益
        """
        if kp is not None:
            self.kp = kp
        if ki is not None:
            self.ki = ki
        if kd is not None:
            self.kd = kd

    def set_setpoint(self, setpoint: float):
        """设置设定值"""
        self.setpoint = setpoint

    # 兼容旧接口
    def set_target(self, target: float):
        """设置设定值（兼容旧接口）"""
        self.set_setpoint(target)

    @property
    def target(self):
        """获取设定值（兼容旧接口）"""
        return self.setpoint

    @target.setter
    def target(self, value: float):
        """设置设定值（兼容旧接口）"""
        self.setpoint = value

    def compute(self, measurement: float, dt: Optional[float] = None) -> float:
        """
        计算PID控制输出

        Args:
            measurement: 当前测量值
            dt: 时间步长（如果None，使用配置中的dt）

        Returns:
            控制输出
        """
        if dt is None:
            dt = self.config.dt

        # 计算误差
        error = self.setpoint - measurement

        # 死区处理
        if abs(error) < self.config.deadband:
            error = 0.0

        # 比例项
        p_term = self.kp * error

        # 积分项（梯形积分）
        self.integral += error * dt

        # 积分限幅（抗饱和）
        self.integral = np.clip(
            self.integral,
            self.config.integral_min,
            self.config.integral_max
        )

        i_term = self.ki * self.integral

        # 微分项（带滤波）
        if dt > 0:
            raw_derivative = (error - self.last_error) / dt
            # 一阶低通滤波
            alpha = self.config.derivative_filter
            filtered_derivative = alpha * raw_derivative + (1 - alpha) * self.last_derivative
            self.last_derivative = filtered_derivative
        else:
            filtered_derivative = 0.0

        d_term = self.kd * filtered_derivative

        # 总控制输出
        output = p_term + i_term + d_term

        # 输出限幅
        output = np.clip(
            output,
            self.config.output_min,
            self.config.output_max
        )

        # 记录历史（用于分析）
        self.error_history.append(error)
        self.output_history.append(output)
        self.integral_history.append(self.integral)
        self.derivative_history.append(filtered_derivative)

        # 更新状态
        self.last_error = error
        self.last_output = output
        self.step_count += 1
        self.total_abs_error += abs(error)
        self.max_error = max(self.max_error, abs(error))

        return output

    def reset(self):
        """重置控制器状态"""
        self.integral = 0.0
        self.last_error = 0.0
        self.last_derivative = 0.0
        self.last_output = 0.0
        self.error_history.clear()
        self.output_history.clear()
        self.integral_history.clear()
        self.derivative_history.clear()
        self.step_count = 0
        self.total_abs_error = 0.0
        self.max_error = 0.0

    def get_performance_metrics(self) -> Dict:
        """
        获取性能指标

        Returns:
            性能指标字典
        """
        if self.step_count == 0:
            return {
                'mae': 0.0,  # 平均绝对误差
                'max_error': 0.0,
                'step_count': 0
            }

        mae = self.total_abs_error / self.step_count

        # 计算稳态误差（最后10%的数据）
        if len(self.error_history) > 10:
            n_steady = max(int(len(self.error_history) * 0.1), 10)
            steady_errors = self.error_history[-n_steady:]
            steady_state_error = np.mean(np.abs(steady_errors))
        else:
            steady_state_error = mae

        return {
            'mae': mae,
            'max_error': self.max_error,
            'steady_state_error': steady_state_error,
            'step_count': self.step_count,
            'current_integral': self.integral,
            'current_output': self.last_output
        }

    def auto_tune_ziegler_nichols(self, Ku: float, Tu: float, method: str = 'classic'):
        """
        Ziegler-Nichols自动调参

        Args:
            Ku: 临界增益
            Tu: 临界周期
            method: 方法（'classic', 'pessen', 'some_overshoot', 'no_overshoot'）
        """
        if method == 'classic':
            # 经典Ziegler-Nichols
            self.kp = 0.6 * Ku
            self.ki = 1.2 * Ku / Tu
            self.kd = 0.075 * Ku * Tu
        elif method == 'pessen':
            # Pessen积分规则
            self.kp = 0.7 * Ku
            self.ki = 1.75 * Ku / Tu
            self.kd = 0.105 * Ku * Tu
        elif method == 'some_overshoot':
            # 允许一定超调
            self.kp = 0.33 * Ku
            self.ki = 0.66 * Ku / Tu
            self.kd = 0.11 * Ku * Tu
        elif method == 'no_overshoot':
            # 无超调
            self.kp = 0.2 * Ku
            self.ki = 0.4 * Ku / Tu
            self.kd = 0.067 * Ku * Tu
        else:
            raise ValueError(f"Unknown tuning method: {method}")

    def __repr__(self) -> str:
        return (f"PIDController(name='{self.name}', "
                f"Kp={self.kp:.3f}, Ki={self.ki:.3f}, Kd={self.kd:.3f})")


if __name__ == "__main__":
    # 测试代码
    print("PID控制器测试")
    print("=" * 60)

    config = PIDConfig(
        kp=1.0,
        ki=0.1,
        kd=0.05,
        output_min=-10.0,
        output_max=10.0,
        dt=1.0
    )

    pid = PIDController(config, name="Test PID")
    pid.set_setpoint(5.0)

    # 模拟简单一阶系统
    x = 0.0
    for i in range(50):
        u = pid.compute(x, dt=1.0)
        # 简单一阶系统：dx/dt = -0.5*x + u
        x = x + (-0.5 * x + u) * 1.0

        if i % 10 == 0:
            print(f"Step {i}: measurement={x:.3f}, output={u:.3f}, error={5.0-x:.3f}")

    print("\n性能指标:")
    metrics = pid.get_performance_metrics()
    for key, value in metrics.items():
        print(f"  {key}: {value}")
