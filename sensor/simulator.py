import numpy as np
from typing import Dict, Optional
from collections import deque
from enum import Enum
from dataclasses import dataclass, field

class SensorFault(Enum):
    """传感器故障类型"""
    NORMAL = "normal"
    BIAS = "bias"              # 偏差
    DRIFT = "drift"            # 漂移
    NOISE = "noise"            # 噪声增大
    STUCK = "stuck"            # 卡死
    INTERMITTENT = "intermittent"  # 间歇性失效
    COMPLETE_FAILURE = "complete_failure"  # 完全失效

@dataclass
class SensorConfig:
    """传感器配置"""
    name: str
    sensor_type: str  # 'level', 'flow', 'pressure'
    noise_std: float = 0.01
    delay: int = 0  # 延迟步数
    sampling_rate: float = 1.0  # 采样率（Hz）
    bias: float = 0.0
    fault_type: SensorFault = SensorFault.NORMAL
    fault_params: Dict = field(default_factory=dict)

class SensorSimulator:
    """传感器仿真器"""

    def __init__(self, config: SensorConfig):
        self.config = config
        self.measurement_buffer = deque(maxlen=100)
        self.time_since_sample = 0.0
        self.stuck_value = None
        self.drift_accumulator = 0.0

    def measure(self, true_value: float, dt: float) -> Optional[float]:
        """测量值（带故障模拟）"""
        self.time_since_sample += dt

        # 采样率控制
        if self.time_since_sample < 1.0 / self.config.sampling_rate:
            return None

        self.time_since_sample = 0.0

        # 故障模拟
        if self.config.fault_type == SensorFault.COMPLETE_FAILURE:
            return np.nan

        measured = true_value

        # 基础噪声
        noise = np.random.normal(0, self.config.noise_std)
        measured += noise

        # 偏差
        if self.config.fault_type == SensorFault.BIAS:
            bias_value = self.config.fault_params.get('bias_value', self.config.bias)
            measured += bias_value

        # 漂移
        if self.config.fault_type == SensorFault.DRIFT:
            drift_rate = self.config.fault_params.get('drift_rate', 0.001)
            self.drift_accumulator += drift_rate * dt
            measured += self.drift_accumulator

        # 噪声增大
        if self.config.fault_type == SensorFault.NOISE:
            noise_multiplier = self.config.fault_params.get('noise_multiplier', 10)
            measured += np.random.normal(0, self.config.noise_std * noise_multiplier)

        # 卡死
        if self.config.fault_type == SensorFault.STUCK:
            if self.stuck_value is None:
                self.stuck_value = measured
            measured = self.stuck_value

        # 间歇性失效
        if self.config.fault_type == SensorFault.INTERMITTENT:
            failure_prob = self.config.fault_params.get('failure_probability', 0.1)
            if np.random.random() < failure_prob:
                return np.nan

        self.measurement_buffer.append(measured)
        return measured

    def reset_fault(self):
        """重置故障"""
        self.config.fault_type = SensorFault.NORMAL
        self.stuck_value = None
        self.drift_accumulator = 0.0
