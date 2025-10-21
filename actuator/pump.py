from core.base import HydraulicComponent
from core.boundary_conditions import PumpBoundary
from core.enums import ComponentType
from core.states import ComponentState


class Pump(HydraulicComponent):
    """泵站 - 作为边界条件"""

    def __init__(self, name: str, a: float = -0.5, b: float = 0.1, c: float = 40.0):
        super().__init__(name, ComponentType.PUMP)
        self.a = a
        self.b = b
        self.c = c

        self.boundary_condition = PumpBoundary(a, b, c)

    def update_high_fidelity(self, dt: float, mode: str = 'implicit') -> ComponentState:
        """泵站边界已在管道中处理"""
        # 计算功率
        if self.state.flow > 0:
            self.state.head = self.a * self.state.flow**2 + self.b * self.state.flow + self.c
            eta = 0.75
            self.state.power = (9.81 * self.state.flow * self.state.head) / (eta * 1000)
        return self.state

    def update_reduced_order(self, dt: float) -> ComponentState:
        return self.update_high_fidelity(dt)
