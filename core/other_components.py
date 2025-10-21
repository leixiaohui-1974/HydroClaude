import numpy as np
from typing import Dict, Tuple
from core.base import HydraulicComponent
from core.enums import ComponentType
from core.states import ComponentState

class Pipe(HydraulicComponent):
    """有压管道"""
    def __init__(self, name: str, length: float, diameter: float,
                 roughness: float = 0.015):
        super().__init__(name, ComponentType.PIPE.value)
        self.length = length
        self.diameter = diameter
        self.roughness = roughness
        self.wave_speed = 1000.0  # 水击波速 m/s
        self.state = ComponentState()

    def update_high_fidelity(self, dt: float, inputs: Dict) -> ComponentState:
        flow = inputs.get('flow', 0.0)
        upstream_pressure = inputs.get('upstream_pressure', 40.0)

        self.state.flow = flow

        # 沿程水头损失（Darcy-Weisbach）
        velocity = flow / (np.pi * (self.diameter / 2)**2) if flow > 0 else 0
        Re = velocity * self.diameter / 1e-6  # 雷诺数
        if Re > 0:
            f = 0.02  # 简化摩阻系数
            head_loss = f * (self.length / self.diameter) * (velocity**2 / (2 * 9.81))
        else:
            head_loss = 0

        self.state.pressure = max(0, upstream_pressure - head_loss)

        return self.state

    def update_reduced_order(self, dt: float, inputs: Dict) -> ComponentState:
        return self.update_high_fidelity(dt, inputs)

    def get_constraints(self) -> Dict[str, Tuple[float, float]]:
        max_flow = np.pi * (self.diameter/2)**2 * 5.0  # 最大流速5m/s
        return {
            'flow': (0, max_flow),
            'pressure': (10, 100)
        }

class DistributionPoint(HydraulicComponent):
    """分水口"""

    def __init__(self, name: str, base_flow: float = 0.5):
        super().__init__(name, ComponentType.DISTRIBUTION.value)
        self.base_flow = base_flow
        self.state = ComponentState()
        self.state.flow = base_flow

    def update_high_fidelity(self, dt: float, inputs: Dict[str, float]) -> ComponentState:
        # 模拟用水变化
        time_of_day = inputs.get('time', 0.0) % 24
        self.state.flow = self.base_flow * (1 + 0.5 * np.sin(2 * np.pi * time_of_day / 24))
        self.state.flow += np.random.normal(0, 0.05)
        self.state.flow = max(0, self.state.flow)
        return self.state

    def get_constraints(self) -> Dict[str, Tuple[float, float]]:
        return {'flow': (0, self.base_flow * 2)}

    def update_reduced_order(self, dt: float, inputs: Dict) -> ComponentState:
        return self.update_high_fidelity(dt, inputs)
