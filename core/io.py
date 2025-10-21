import numpy as np
from typing import Optional
from core.component import HydraulicComponent

class Sensor:
    """传感器"""
    def __init__(self, name: str, sensor_type: str, noise_std: float = 0.01):
        self.name = name
        self.sensor_type = sensor_type
        self.noise_std = noise_std
        self.component: Optional[HydraulicComponent] = None
        self.bias = 0.0
        self.fault_probability = 0.0

    def measure(self) -> float:
        """测量值（带噪声和故障）"""
        if self.component is None:
            return 0.0

        # 传感器故障模拟
        if np.random.random() < self.fault_probability:
            return np.nan

        if self.sensor_type == 'level':
            true_value = self.component.state.level
        elif self.sensor_type == 'flow':
            true_value = self.component.state.flow
        elif self.sensor_type == 'pressure':
            true_value = self.component.state.pressure
        elif self.sensor_type == 'volume':
            true_value = self.component.state.volume
        else:
            true_value = 0.0

        noise = np.random.normal(0, self.noise_std)
        return true_value + noise + self.bias

class Actuator:
    """执行器"""
    def __init__(self, name: str, actuator_type: str,
                 response_time: float = 1.0, max_rate: float = 1.0):
        self.name = name
        self.actuator_type = actuator_type
        self.response_time = response_time
        self.max_rate = max_rate
        self.component: Optional[HydraulicComponent] = None
        self.setpoint = 0.0
        self.current_value = 0.0
        self.dead_zone = 0.01  # 死区

    def execute(self, command: float, dt: float) -> float:
        """执行控制命令"""
        self.setpoint = command

        error = self.setpoint - self.current_value

        # 死区处理
        if abs(error) < self.dead_zone:
            return self.current_value

        # 一阶惯性
        change = error * (dt / self.response_time)
        change = np.clip(change, -self.max_rate * dt, self.max_rate * dt)

        self.current_value += change
        return self.current_value
