"""
传感器模型

支持多种水利工程传感器类型，包括：
- 水位传感器（超声波、压力式、浮子式）
- 流量传感器（电磁、超声波、堰槽）
- 压力传感器
- 水质传感器（余氯、pH、浊度等）
- 闸阀位置传感器
- 泵站转速传感器

误差模型包括：
- 测量噪声（高斯、脉冲）
- 传感器延迟
- 传感器故障（漂移、卡死、间歇）
- 量化误差
- 饱和限制

支持YAML配置文件

作者：HydroClaude Team
更新：2025-10-24
"""

import numpy as np
from typing import Optional, Dict, Any, List
from enum import Enum
from dataclasses import dataclass, field
import yaml


class SensorType(Enum):
    """传感器类型"""
    LEVEL = "water_level"          # 水位
    FLOW = "flow_rate"             # 流量
    PRESSURE = "pressure"          # 压力
    CHLORINE = "chlorine"          # 余氯
    PH = "ph"                      # pH值
    TURBIDITY = "turbidity"        # 浊度
    GATE_POSITION = "gate_position"  # 闸门位置
    PUMP_SPEED = "pump_speed"      # 泵站转速
    VALVE_POSITION = "valve_position"  # 阀门位置
    TEMPERATURE = "temperature"     # 温度


class FaultType(Enum):
    """故障类型"""
    NONE = "none"
    DRIFT = "drift"                # 漂移
    STUCK = "stuck"                # 卡死
    INTERMITTENT = "intermittent"  # 间歇性故障
    BIAS = "bias"                  # 偏置
    NOISE_INCREASE = "noise_increase"  # 噪声增大


@dataclass
class SensorConfig:
    """传感器配置"""
    name: str
    sensor_type: SensorType

    # 噪声参数
    noise_std: float = 0.0          # 高斯噪声标准差
    impulse_prob: float = 0.0       # 脉冲噪声概率
    impulse_amplitude: float = 0.0  # 脉冲噪声幅度

    # 延迟参数
    delay_steps: int = 0            # 延迟步数

    # 量化参数
    quantization_step: float = 0.0  # 量化步长（0表示无量化）

    # 测量范围
    min_value: float = -np.inf
    max_value: float = np.inf

    # 故障参数
    fault_type: FaultType = FaultType.NONE
    drift_rate: float = 0.0         # 漂移速率
    stuck_value: Optional[float] = None  # 卡死值
    intermittent_prob: float = 0.0  # 间歇性故障概率
    bias: float = 0.0               # 偏置

    # 滤波参数
    use_filter: bool = False
    filter_alpha: float = 0.1       # 一阶滤波系数


class Sensor:
    """
    基础传感器类（扩展版）

    向后兼容原有接口，同时支持更多功能
    """

    def __init__(self, name: str, noise_std: float = 0.0,
                 config: Optional[SensorConfig] = None):
        """
        初始化传感器

        Args:
            name: 传感器名称
            noise_std: 噪声标准差（向后兼容）
            config: 传感器配置（新功能）
        """
        self.name = name
        self.noise_std = noise_std

        # 如果提供配置，使用配置；否则使用默认配置
        if config is None:
            self.config = SensorConfig(
                name=name,
                sensor_type=SensorType.LEVEL,
                noise_std=noise_std
            )
        else:
            self.config = config

        # 内部状态
        self._delay_buffer: List[float] = []
        self._filtered_value: float = 0.0
        self._drift_accumulation: float = 0.0
        self._is_stuck: bool = False
        self._measurement_count: int = 0

    def measure(self, true_value: float, dt: Optional[float] = None) -> float:
        """
        执行测量（向后兼容接口，同时支持新功能）

        Args:
            true_value: 真实值
            dt: 时间步长（用于漂移计算）

        Returns:
            测量值
        """
        # 应用故障
        value = self._apply_fault(true_value, dt)

        # 添加噪声
        value = self._add_noise(value)

        # 应用量化
        value = self._apply_quantization(value)

        # 应用饱和
        value = np.clip(value, self.config.min_value, self.config.max_value)

        # 应用延迟
        value = self._apply_delay(value)

        # 应用滤波
        if self.config.use_filter:
            value = self._apply_filter(value)

        self._measurement_count += 1

        return value

    def _add_noise(self, value: float) -> float:
        """添加测量噪声"""
        # 高斯噪声
        noise = np.random.normal(0, self.config.noise_std)
        value += noise

        # 脉冲噪声
        if np.random.rand() < self.config.impulse_prob:
            impulse = np.random.choice([-1, 1]) * self.config.impulse_amplitude
            value += impulse

        return value

    def _apply_delay(self, value: float) -> float:
        """应用传感器延迟"""
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

    def _apply_quantization(self, value: float) -> float:
        """应用量化"""
        if self.config.quantization_step <= 0:
            return value

        return np.round(value / self.config.quantization_step) * self.config.quantization_step

    def _apply_fault(self, value: float, dt: Optional[float]) -> float:
        """应用传感器故障"""
        if self.config.fault_type == FaultType.NONE:
            return value

        elif self.config.fault_type == FaultType.DRIFT:
            # 累积漂移
            if dt is not None:
                self._drift_accumulation += self.config.drift_rate * dt
            else:
                self._drift_accumulation += self.config.drift_rate
            return value + self._drift_accumulation

        elif self.config.fault_type == FaultType.STUCK:
            # 卡死在固定值
            if not self._is_stuck:
                if self.config.stuck_value is not None:
                    self._stuck_at = self.config.stuck_value
                else:
                    self._stuck_at = value
                self._is_stuck = True
            return self._stuck_at

        elif self.config.fault_type == FaultType.INTERMITTENT:
            # 间歇性故障（随机返回错误值）
            if np.random.rand() < self.config.intermittent_prob:
                return value + np.random.normal(0, self.config.noise_std * 10)
            return value

        elif self.config.fault_type == FaultType.BIAS:
            # 固定偏置
            return value + self.config.bias

        elif self.config.fault_type == FaultType.NOISE_INCREASE:
            # 噪声增大
            return value + np.random.normal(0, self.config.noise_std * 5)

        return value

    def _apply_filter(self, value: float) -> float:
        """应用一阶低通滤波"""
        if self._measurement_count == 1:
            self._filtered_value = value
        else:
            alpha = self.config.filter_alpha
            self._filtered_value = alpha * value + (1 - alpha) * self._filtered_value

        return self._filtered_value

    def reset(self):
        """重置传感器状态"""
        self._delay_buffer = []
        self._filtered_value = 0.0
        self._drift_accumulation = 0.0
        self._is_stuck = False
        self._measurement_count = 0

    @classmethod
    def from_config_dict(cls, config_dict: Dict[str, Any]) -> 'Sensor':
        """从配置字典创建传感器"""
        # 转换sensor_type
        sensor_type = SensorType(config_dict.get('sensor_type', 'water_level'))
        fault_type = FaultType(config_dict.get('fault_type', 'none'))

        config = SensorConfig(
            name=config_dict['name'],
            sensor_type=sensor_type,
            noise_std=config_dict.get('noise_std', 0.0),
            impulse_prob=config_dict.get('impulse_prob', 0.0),
            impulse_amplitude=config_dict.get('impulse_amplitude', 0.0),
            delay_steps=config_dict.get('delay_steps', 0),
            quantization_step=config_dict.get('quantization_step', 0.0),
            min_value=config_dict.get('min_value', -np.inf),
            max_value=config_dict.get('max_value', np.inf),
            fault_type=fault_type,
            drift_rate=config_dict.get('drift_rate', 0.0),
            stuck_value=config_dict.get('stuck_value'),
            intermittent_prob=config_dict.get('intermittent_prob', 0.0),
            bias=config_dict.get('bias', 0.0),
            use_filter=config_dict.get('use_filter', False),
            filter_alpha=config_dict.get('filter_alpha', 0.1)
        )

        return cls(config.name, config.noise_std, config)


# 向后兼容的专用传感器类
class LevelSensor(Sensor):
    """水位传感器"""
    def __init__(self, name: str, noise_std: float = 0.01,
                 config: Optional[SensorConfig] = None):
        if config is None:
            config = SensorConfig(
                name=name,
                sensor_type=SensorType.LEVEL,
                noise_std=noise_std
            )
        super().__init__(name, noise_std, config)


class FlowSensor(Sensor):
    """流量传感器"""
    def __init__(self, name: str, noise_std: float = 0.05,
                 config: Optional[SensorConfig] = None):
        if config is None:
            config = SensorConfig(
                name=name,
                sensor_type=SensorType.FLOW,
                noise_std=noise_std
            )
        super().__init__(name, noise_std, config)


class PressureSensor(Sensor):
    """压力传感器"""
    def __init__(self, name: str, noise_std: float = 0.02,
                 config: Optional[SensorConfig] = None):
        if config is None:
            config = SensorConfig(
                name=name,
                sensor_type=SensorType.PRESSURE,
                noise_std=noise_std
            )
        super().__init__(name, noise_std, config)


class ChlorineSensor(Sensor):
    """余氯传感器"""
    def __init__(self, name: str, noise_std: float = 0.01,
                 config: Optional[SensorConfig] = None):
        if config is None:
            config = SensorConfig(
                name=name,
                sensor_type=SensorType.CHLORINE,
                noise_std=noise_std,
                min_value=0.0,
                max_value=5.0
            )
        super().__init__(name, noise_std, config)


class GatePositionSensor(Sensor):
    """闸门位置传感器"""
    def __init__(self, name: str, noise_std: float = 0.005,
                 config: Optional[SensorConfig] = None):
        if config is None:
            config = SensorConfig(
                name=name,
                sensor_type=SensorType.GATE_POSITION,
                noise_std=noise_std,
                min_value=0.0,
                max_value=10.0  # 最大开度10m
            )
        super().__init__(name, noise_std, config)


class PumpSpeedSensor(Sensor):
    """泵站转速传感器"""
    def __init__(self, name: str, noise_std: float = 1.0,
                 config: Optional[SensorConfig] = None):
        if config is None:
            config = SensorConfig(
                name=name,
                sensor_type=SensorType.PUMP_SPEED,
                noise_std=noise_std,
                min_value=0.0,
                max_value=3000.0  # 最大3000 rpm
            )
        super().__init__(name, noise_std, config)


def load_sensors_from_yaml(yaml_file: str) -> List[Sensor]:
    """
    从YAML配置文件加载传感器

    Args:
        yaml_file: YAML文件路径

    Returns:
        传感器列表
    """
    with open(yaml_file, 'r', encoding='utf-8') as f:
        config = yaml.safe_load(f)

    sensors = []
    for sensor_config in config.get('sensors', []):
        sensor = Sensor.from_config_dict(sensor_config)
        sensors.append(sensor)

    return sensors
