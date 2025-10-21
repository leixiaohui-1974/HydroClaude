from core.base import HydraulicComponent
from core.states import ComponentState

class Tank(HydraulicComponent):
    """水池/水库"""
    def __init__(self, name: str, volume_min: float, volume_max: float, area: float):
        super().__init__(name, "tank")
        self.volume_min = volume_min
        self.volume_max = volume_max
        self.area = area

        self.state = ComponentState()
        self.state.volume = (volume_min + volume_max) / 2
        self.state.level = self.state.volume / area

    def update_high_fidelity(self, dt: float, inputs: dict) -> ComponentState:
        return self.update_reduced_order(dt, inputs)

    def update_reduced_order(self, dt: float, inputs: dict) -> ComponentState:
        inflow = inputs.get('inflow', 0.0)
        outflow = inputs.get('outflow', 0.0)

        dV = (inflow - outflow) * dt
        self.state.volume = max(self.volume_min, min(self.volume_max, self.state.volume + dV))
        self.state.level = self.state.volume / self.area
        self.state.flow = outflow

        return self.state

    def get_constraints(self):
        return {
            'volume_min': self.volume_min,
            'volume_max': self.volume_max,
            'level_min': self.volume_min / self.area,
            'level_max': self.volume_max / self.area
        }
