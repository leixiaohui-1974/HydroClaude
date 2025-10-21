import numpy as np
from typing import Dict
from collections import deque
from enum import Enum
from dataclasses import dataclass, field

class ActuatorFault(Enum):
    """执行器故障类型"""
    NORMAL = "normal"
    DELAY = "delay"            # 响应延迟
    SATURATION = "saturation"  # 饱和
    STUCK = "stuck"            # 卡滞
    SLOW_RESPONSE = "slow_response"  # 响应变慢
    DEAD_ZONE = "dead_zone"    # 死区增大
    HYSTERESIS = "hysteresis"  # 迟滞

@dataclass
class ActuatorConfig:
    """执行器配置"""
    name: str
    actuator_type: str  # 'gate', 'valve', 'pump'
    response_time: float = 1.0  # 时间常数
    max_rate: float = 1.0       # 最大变化率
    dead_zone: float = 0.01
    fault_type: ActuatorFault = ActuatorFault.NORMAL
    fault_params: Dict = field(default_factory=dict)

class ActuatorSimulator:
    """执行器仿真器"""

    def __init__(self, config: ActuatorConfig):
        self.config = config
        self.current_value = 0.0
        self.command_buffer = deque(maxlen=100)
        self.stuck_value = None

    def execute(self, command: float, dt: float) -> float:
        """执行控制命令（带故障模拟）"""
        self.command_buffer.append(command)

        # 响应延迟故障
        if self.config.fault_type == ActuatorFault.DELAY:
            delay_steps = self.config.fault_params.get('delay_steps', 5)
            if len(self.command_buffer) >= delay_steps:
                command = self.command_buffer[-delay_steps]

        # 卡滞故障
        if self.config.fault_type == ActuatorFault.STUCK:
            if self.stuck_value is None:
                self.stuck_value = self.current_value
            return self.stuck_value

        # 饱和故障
        if self.config.fault_type == ActuatorFault.SATURATION:
            saturation_level = self.config.fault_params.get('saturation_level', 0.8)
            command = np.clip(command, 0, saturation_level * command)

        # 死区
        dead_zone = self.config.dead_zone
        if self.config.fault_type == ActuatorFault.DEAD_ZONE:
            dead_zone *= self.config.fault_params.get('dead_zone_multiplier', 5)

        error = command - self.current_value
        if abs(error) < dead_zone:
            return self.current_value

        # 响应时间
        response_time = self.config.response_time
        if self.config.fault_type == ActuatorFault.SLOW_RESPONSE:
            response_time *= self.config.fault_params.get('slowdown_factor', 3)

        # 一阶惯性
        change = error * (dt / response_time)

        # 限制变化率
        max_rate = self.config.max_rate
        change = np.clip(change, -max_rate * dt, max_rate * dt)

        # 迟滞效应
        if self.config.fault_type == ActuatorFault.HYSTERESIS:
            hysteresis_width = self.config.fault_params.get('hysteresis_width', 0.1)
            if abs(error) < hysteresis_width:
                change *= 0.5

        self.current_value += change
        return self.current_value

    def reset_fault(self):
        """重置故障"""
        self.config.fault_type = ActuatorFault.NORMAL
        self.stuck_value = None
