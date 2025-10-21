from __future__ import annotations
from abc import ABC, abstractmethod
from typing import List, Dict, Tuple, Optional
from dataclasses import dataclass
from enum import Enum

class ComponentType(Enum):
    """组件类型枚举"""
    RESERVOIR = "reservoir"
    CANAL = "canal"
    PIPE = "pipe"
    SETTLING_BASIN = "settling_basin"
    STORAGE_TANK = "storage_tank"
    GATE = "gate"
    VALVE = "valve"
    PUMP = "pump"
    DISTRIBUTION = "distribution_point"

@dataclass
class ComponentState:
    """组件状态"""
    volume: float = 0.0          # 蓄水量 (m³)
    level: float = 0.0           # 水位 (m)
    flow: float = 0.0            # 流量 (m³/s)
    velocity: float = 0.0        # 流速 (m/s)
    pressure: float = 0.0        # 压力 (m)
    head: float = 0.0            # 水头 (m)
    power: float = 0.0           # 功率 (kW)
    efficiency: float = 1.0      # 效率
    opening: float = 0.5         # 开度/开启度

    def to_dict(self) -> Dict:
        return self.__dict__.copy()

    def to_array(self) -> np.ndarray:
        """转为数组（用于数值计算）"""
        return np.array([self.volume, self.level, self.flow, self.velocity,
                        self.pressure, self.head, self.power])

class HydraulicComponent(ABC):
    """水力组件抽象基类"""

    def __init__(self, name: str, comp_type: ComponentType):
        self.name = name
        self.type = comp_type
        self.state = ComponentState()
        self.upstream_components: List['HydraulicComponent'] = []
        self.downstream_components: List['HydraulicComponent'] = []
        self.sensors: List['Sensor'] = []
        self.actuators: List['Actuator'] = []

    @abstractmethod
    def update_state(self, dt: float, inputs: Dict[str, float]) -> ComponentState:
        """更新状态（降阶模型）"""
        pass

    @abstractmethod
    def get_constraints(self) -> Dict[str, Tuple[float, float]]:
        """获取约束"""
        pass

    @abstractmethod
    def compute_derivatives(self, state_vector: np.ndarray,
                          inputs: Dict[str, float]) -> np.ndarray:
        """计算状态导数（高保真模型）"""
        pass

    def add_upstream(self, component: 'HydraulicComponent'):
        """添加上游组件"""
        self.upstream_components.append(component)
        component.downstream_components.append(self)

    def add_sensor(self, sensor: 'Sensor'):
        """添加传感器"""
        self.sensors.append(sensor)
        sensor.component = self

    def add_actuator(self, actuator: 'Actuator'):
        """添加执行器"""
        self.actuators.append(actuator)
        actuator.component = self
