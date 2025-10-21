import numpy as np
from enum import Enum
from dataclasses import dataclass

class DisturbanceType(Enum):
    """扰动类型"""
    STEP = "step"              # 阶跃
    RAMP = "ramp"              # 斜坡
    SINE = "sine"              # 正弦
    PULSE = "pulse"            # 脉冲
    RANDOM_WALK = "random_walk"  # 随机游走
    REALISTIC = "realistic"    # 真实模式

@dataclass
class DisturbanceConfig:
    """扰动配置"""
    name: str
    disturbance_type: DisturbanceType
    base_value: float = 0.0
    amplitude: float = 1.0
    frequency: float = 0.1  # Hz
    start_time: float = 0.0
    duration: float = float('inf')
    noise_std: float = 0.1

class DisturbanceGenerator:
    """扰动生成器"""

    def __init__(self, config: DisturbanceConfig):
        self.config = config
        self.current_value = config.base_value
        self.random_state = np.random.RandomState(42)

    def generate(self, time: float) -> float:
        """生成扰动值"""
        if time < self.config.start_time:
            return self.config.base_value

        if time > self.config.start_time + self.config.duration:
            return self.config.base_value

        t = time - self.config.start_time

        if self.config.disturbance_type == DisturbanceType.STEP:
            value = self.config.base_value + self.config.amplitude

        elif self.config.disturbance_type == DisturbanceType.RAMP:
            slope = self.config.amplitude / self.config.duration
            value = self.config.base_value + slope * t

        elif self.config.disturbance_type == DisturbanceType.SINE:
            value = self.config.base_value + \
                   self.config.amplitude * np.sin(2 * np.pi * self.config.frequency * t)

        elif self.config.disturbance_type == DisturbanceType.PULSE:
            pulse_width = 1.0 / self.config.frequency / 2
            if t % (1.0 / self.config.frequency) < pulse_width:
                value = self.config.base_value + self.config.amplitude
            else:
                value = self.config.base_value

        elif self.config.disturbance_type == DisturbanceType.RANDOM_WALK:
            change = self.random_state.normal(0, self.config.noise_std)
            self.current_value += change
            value = self.current_value

        elif self.config.disturbance_type == DisturbanceType.REALISTIC:
            # 模拟真实用水模式：日周期 + 随机波动
            daily_pattern = np.sin(2 * np.pi * t / 86400)  # 24小时周期
            weekly_pattern = 0.2 * np.sin(2 * np.pi * t / (86400 * 7))  # 周周期
            random_fluctuation = self.random_state.normal(0, self.config.noise_std)

            value = self.config.base_value + \
                   self.config.amplitude * (0.5 + 0.3 * daily_pattern +
                                           0.1 * weekly_pattern + 0.1 * random_fluctuation)
        else:
            value = self.config.base_value

        return max(0, value)  # 确保非负
