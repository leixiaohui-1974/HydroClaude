import numpy as np
from typing import Dict, Tuple
from core.base import HydraulicComponent
from core.enums import ComponentType
from core.states import ComponentState

class WaterBody(HydraulicComponent):
    """水体基类（渠池、水库等）"""

    def __init__(self, name: str, comp_type: ComponentType,
                 volume_min: float, volume_max: float,
                 area: float, length: float = 0.0):
        super().__init__(name, comp_type.value)
        self.volume_min = volume_min
        self.volume_max = volume_max
        self.area = area
        self.length = length
        self.state = ComponentState()
        self.state.volume = (volume_min + volume_max) / 2
        self.state.level = self.state.volume / area

    def get_constraints(self) -> Dict[str, Tuple[float, float]]:
        return {
            'volume': (self.volume_min, self.volume_max),
            'level': (self.volume_min / self.area, self.volume_max / self.area)
        }

    def update_high_fidelity(self, dt: float, inputs: Dict) -> ComponentState:
        return self.update_reduced_order(dt, inputs)

    def update_reduced_order(self, dt: float, inputs: Dict[str, float]) -> ComponentState:
        """水量平衡更新（降阶模型）"""
        inflow = inputs.get('inflow', 0.0)
        outflow = inputs.get('outflow', 0.0)
        disturbance = inputs.get('disturbance', 0.0)

        self.state.volume += (inflow - outflow - disturbance) * dt
        self.state.volume = np.clip(self.state.volume,
                                    self.volume_min, self.volume_max)
        self.state.level = self.state.volume / self.area if self.area > 0 else 0

        return self.state

class Reservoir(WaterBody):
    """水库"""
    def __init__(self, name: str, volume_min: float, volume_max: float, area: float):
        super().__init__(name, ComponentType.RESERVOIR, volume_min, volume_max, area)

class SettlingBasin(WaterBody):
    """稳流池"""
    def __init__(self, name: str, volume_min: float, volume_max: float, area: float):
        super().__init__(name, ComponentType.SETTLING_BASIN, volume_min, volume_max, area)

class StorageTank(WaterBody):
    """调蓄池/高位水池"""
    def __init__(self, name: str, volume_min: float, volume_max: float, area: float):
        super().__init__(name, ComponentType.STORAGE_TANK, volume_min, volume_max, area)
