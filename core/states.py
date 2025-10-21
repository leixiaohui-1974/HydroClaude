from dataclasses import dataclass, field
import numpy as np

@dataclass
class HydraulicState:
    """水力状态（空间分布）"""
    h: np.ndarray = None  # 水深/水头 (m)
    Q: np.ndarray = None  # 流量 (m³/s)
    V: np.ndarray = None  # 流速 (m/s)
    P: np.ndarray = None  # 压力 (m)

    def __post_init__(self):
        if self.h is None:
            self.h = np.array([5.0])
        if self.Q is None:
            self.Q = np.array([5.0])
        if self.V is None:
            self.V = np.array([1.0])
        if self.P is None:
            self.P = np.array([40.0])

@dataclass
class ComponentState:
    """组件集总状态"""
    volume: float = 0.0
    level: float = 0.0
    flow: float = 0.0
    pressure: float = 0.0
    head: float = 0.0
    power: float = 0.0
    opening: float = 0.5
