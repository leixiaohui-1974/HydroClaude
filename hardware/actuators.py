"""
执行器模型

支持多种水利工程执行器类型，包括：
- 闸门执行器
- 泵站执行器
- 阀门执行器

执行器特性：
- 速率限制（rate limit）
- 饱和限制（saturation）
- 死区（dead zone）
- 滞后（hysteresis）
- 延迟（delay）
- 量化（quantization）

支持YAML配置文件

作者：HydroClaude Team
更新：2025-10-24
"""

import numpy as np
from typing import Optional, Dict, Any, List
from enum import Enum
from dataclasses import dataclass
import yaml


class ActuatorType(Enum):
    """执行器类型"""
    GATE = "gate"
    PUMP = "pump"
    VALVE = "valve"


@dataclass
class ActuatorConfig:
    """执行器配置"""
    name: str
    actuator_type: ActuatorType

    # 速率限制
    rate_limit: Optional[float] = None  # 最大变化速率

    # 饱和限制
    min_value: float = 0.0
    max_value: float = 1.0

    # 死区
    dead_zone: float = 0.0  # 死区宽度

    # 滞后
    hysteresis: float = 0.0  # 滞后宽度

    # 延迟
    delay_steps: int = 0

    # 量化
    quantization_step: float = 0.0

    # 噪声（执行器本身的抖动）
    noise_std: float = 0.0


class Actuator:
    """
    基础执行器类（扩展版）

    向后兼容原有接口，同时支持更多功能
    """

    def __init__(self, name: str, rate_limit: Optional[float] = None,
                 config: Optional[ActuatorConfig] = None):
        """
        初始化执行器

        Args:
            name: 执行器名称
            rate_limit: 速率限制（向后兼容）
            config: 执行器配置（新功能）
        """
        self.name = name
        self.rate_limit = rate_limit
        self.current_value = 0.0

        # 如果提供配置，使用配置；否则使用默认配置
        if config is None:
            self.config = ActuatorConfig(
                name=name,
                actuator_type=ActuatorType.GATE,
                rate_limit=rate_limit if rate_limit is not None else float('inf')
            )
        else:
            self.config = config

        # 内部状态
        self._delay_buffer: List[float] = []
        self._hysteresis_state: int = 0  # -1: 下降, 0: 中性, 1: 上升
        self._last_command: float = 0.0

    def actuate(self, command: float, dt: float) -> float:
        """
        执行控制命令（向后兼容接口，同时支持新功能）

        Args:
            command: 控制命令
            dt: 时间步长

        Returns:
            实际执行值
        """
        # 应用死区
        command = self._apply_dead_zone(command)

        # 应用滞后
        command = self._apply_hysteresis(command)

        # 应用速率限制
        value = self._apply_rate_limit(command, dt)

        # 应用饱和
        value = np.clip(value, self.config.min_value, self.config.max_value)

        # 应用量化
        value = self._apply_quantization(value)

        # 添加噪声
        value = self._add_noise(value)

        # 应用延迟
        value = self._apply_delay(value)

        self.current_value = value
        self._last_command = command

        return value

    def _apply_rate_limit(self, command: float, dt: float) -> float:
        """应用速率限制"""
        if self.config.rate_limit is None or np.isinf(self.config.rate_limit):
            return command

        max_change = self.config.rate_limit * dt
        delta = np.clip(command - self.current_value, -max_change, max_change)
        return self.current_value + delta

    def _apply_dead_zone(self, command: float) -> float:
        """应用死区"""
        if self.config.dead_zone <= 0:
            return command

        # 相对于last_command的死区
        delta = command - self._last_command

        if abs(delta) < self.config.dead_zone:
            return self._last_command  # 在死区内，不响应
        else:
            return command

    def _apply_hysteresis(self, command: float) -> float:
        """应用滞后特性"""
        if self.config.hysteresis <= 0:
            return command

        # 判断变化方向
        delta = command - self.current_value

        if delta > self.config.hysteresis:
            self._hysteresis_state = 1  # 上升
            return command
        elif delta < -self.config.hysteresis:
            self._hysteresis_state = -1  # 下降
            return command
        else:
            # 在滞后区间内，保持当前值
            return self.current_value

    def _apply_quantization(self, value: float) -> float:
        """应用量化"""
        if self.config.quantization_step <= 0:
            return value

        return np.round(value / self.config.quantization_step) * self.config.quantization_step

    def _add_noise(self, value: float) -> float:
        """添加执行器噪声（抖动）"""
        if self.config.noise_std <= 0:
            return value

        noise = np.random.normal(0, self.config.noise_std)
        return value + noise

    def _apply_delay(self, value: float) -> float:
        """应用执行器延迟"""
        if self.config.delay_steps == 0:
            return value

        # 添加到延迟缓冲区
        self._delay_buffer.append(value)

        # 如果缓冲区未满，返回当前值
        if len(self._delay_buffer) <= self.config.delay_steps:
            return value

        # 返回延迟后的值
        delayed_value = self._delay_buffer[0]
        self._delay_buffer.pop(0)

        return delayed_value

    def reset(self):
        """重置执行器状态"""
        self.current_value = 0.0
        self._delay_buffer = []
        self._hysteresis_state = 0
        self._last_command = 0.0

    @classmethod
    def from_config_dict(cls, config_dict: Dict[str, Any]) -> 'Actuator':
        """从配置字典创建执行器"""
        actuator_type = ActuatorType(config_dict.get('actuator_type', 'gate'))

        config = ActuatorConfig(
            name=config_dict['name'],
            actuator_type=actuator_type,
            rate_limit=config_dict.get('rate_limit'),
            min_value=config_dict.get('min_value', 0.0),
            max_value=config_dict.get('max_value', 1.0),
            dead_zone=config_dict.get('dead_zone', 0.0),
            hysteresis=config_dict.get('hysteresis', 0.0),
            delay_steps=config_dict.get('delay_steps', 0),
            quantization_step=config_dict.get('quantization_step', 0.0),
            noise_std=config_dict.get('noise_std', 0.0)
        )

        return cls(config.name, config.rate_limit, config)


class GateActuator(Actuator):
    """闸门执行器"""
    def __init__(self, name: str, rate_limit: float = 0.1,
                 config: Optional[ActuatorConfig] = None):
        if config is None:
            config = ActuatorConfig(
                name=name,
                actuator_type=ActuatorType.GATE,
                rate_limit=rate_limit,  # 0.1 m/s
                min_value=0.0,
                max_value=10.0  # 最大开度10m
            )
        super().__init__(name, rate_limit, config)


class PumpActuator(Actuator):
    """泵站执行器"""
    def __init__(self, name: str, rate_limit: float = 10.0,
                 config: Optional[ActuatorConfig] = None):
        if config is None:
            config = ActuatorConfig(
                name=name,
                actuator_type=ActuatorType.PUMP,
                rate_limit=rate_limit,  # 10 rpm/s
                min_value=0.0,
                max_value=3000.0  # 最大3000 rpm
            )
        super().__init__(name, rate_limit, config)


class ValveActuator(Actuator):
    """阀门执行器"""
    def __init__(self, name: str, rate_limit: float = 0.2,
                 config: Optional[ActuatorConfig] = None):
        if config is None:
            config = ActuatorConfig(
                name=name,
                actuator_type=ActuatorType.VALVE,
                rate_limit=rate_limit,  # 20%/s
                min_value=0.0,
                max_value=1.0  # 0-100%开度
            )
        super().__init__(name, rate_limit, config)


def load_actuators_from_yaml(yaml_file: str) -> List[Actuator]:
    """
    从YAML配置文件加载执行器

    Args:
        yaml_file: YAML文件路径

    Returns:
        执行器列表
    """
    with open(yaml_file, 'r', encoding='utf-8') as f:
        config = yaml.safe_load(f)

    actuators = []
    for actuator_config in config.get('actuators', []):
        actuator = Actuator.from_config_dict(actuator_config)
        actuators.append(actuator)

    return actuators
