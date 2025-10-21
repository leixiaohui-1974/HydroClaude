from dataclasses import dataclass, field
import numpy as np
from typing import Dict

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

@dataclass
class HydraulicState:
    """分布状态（用于高保真模型）"""
    h: np.ndarray = field(default_factory=lambda: np.array([]))  # 水深/水头
    Q: np.ndarray = field(default_factory=lambda: np.array([]))  # 流量
    V: np.ndarray = field(default_factory=lambda: np.array([]))  # 流速
