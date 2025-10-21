import numpy as np

from core.base import HydraulicComponent
from core.enums import ComponentType
from core.states import ComponentState


class Tank(HydraulicComponent):
    """水池"""

    def __init__(self, name: str, volume_min: float, volume_max: float, area: float):
        super().__init__(name, ComponentType.TANK)
        self.volume_min = volume_min
        self.volume_max = volume_max
        self.area = area
        self.state.volume = (volume_min + volume_max) / 2

    def update_high_fidelity(self, dt: float, mode: str = 'implicit') -> ComponentState:
        return self.update_reduced_order(dt)

    def update_reduced_order(self, dt: float) -> ComponentState:
        # 简化：从边界条件获取流入流出
        inflow = 5.0  # 应从拓扑获取
        outflow = 4.0

        self.state.volume += (inflow - outflow) * dt
        self.state.volume = np.clip(self.state.volume, self.volume_min, self.volume_max)
        self.state.level = self.state.volume / self.area
        return self.state
