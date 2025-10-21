import numpy as np
from typing import Dict, Tuple
from core.base import HydraulicComponent
from core.enums import ComponentType
from core.states import ComponentState

class ControlDevice(HydraulicComponent):
    """控制设备基类"""

    def __init__(self, name: str, comp_type: ComponentType,
                 flow_min: float, flow_max: float):
        super().__init__(name, comp_type.value)
        self.flow_min = flow_min
        self.flow_max = flow_max
        self.state = ComponentState()
        self.state.flow = (flow_min + flow_max) / 2

    def get_constraints(self) -> Dict[str, Tuple[float, float]]:
        return {'flow': (self.flow_min, self.flow_max)}

    def update_high_fidelity(self, dt: float, inputs: Dict) -> ComponentState:
        """For control devices, high-fidelity is the same as reduced-order."""
        return self.update_reduced_order(dt, inputs)

    def update_reduced_order(self, dt: float, inputs: Dict) -> ComponentState:
        """Base implementation for reduced-order update."""
        # This will be overridden by child classes with specific logic.
        # Default is to do nothing.
        return self.state

class Gate(ControlDevice):
    """闸门 - 实现堰流/孔流方程"""

    def __init__(self, name: str, flow_min: float, flow_max: float,
                 width: float = 3.0, max_opening: float = 5.0):
        super().__init__(name, ComponentType.GATE, flow_min, flow_max)
        self.width = width
        self.max_opening = max_opening
        self.state.opening = max_opening / 2
        self.Cd = 0.6  # 流量系数

    def update_reduced_order(self, dt: float, inputs: Dict[str, float]) -> ComponentState:
        """闸门水力学计算"""
        target_flow = inputs.get('control', self.state.flow)

        # Simple implementation for now
        self.state.flow = np.clip(target_flow, self.flow_min, self.flow_max)

        return self.state

class Valve(ControlDevice):
    """阀门 - 实现阀门特性方程"""

    def __init__(self, name: str, flow_min: float, flow_max: float,
                 diameter: float = 1.0, Cv: float = 100.0):
        super().__init__(name, ComponentType.VALVE, flow_min, flow_max)
        self.diameter = diameter
        self.Cv = Cv  # 阀门流量系数
        self.state.opening = 0.5  # 开度 0-1

    def update_reduced_order(self, dt: float, inputs: Dict[str, float]) -> ComponentState:
        """阀门水力学计算"""
        target_flow = inputs.get('control', self.state.flow)
        self.state.flow = np.clip(target_flow, self.flow_min, self.flow_max)
        return self.state

class Pump(ControlDevice):
    """泵站 - 实现完整特性曲线"""

    def __init__(self, name: str, flow_min: float, flow_max: float,
                 head_min: float, head_max: float,
                 rated_flow: float = None, rated_head: float = None,
                 rated_power: float = 100.0, efficiency: float = 0.75):
        super().__init__(name, ComponentType.PUMP, flow_min, flow_max)
        self.head_min = head_min
        self.head_max = head_max
        self.rated_flow = rated_flow or (flow_min + flow_max) / 2
        self.rated_head = rated_head or (head_min + head_max) / 2
        self.rated_power = rated_power
        self.state.efficiency = efficiency
        self.is_running = False

        # 特性曲线系数（二次多项式）
        self._compute_curve_coefficients()

    def _compute_curve_coefficients(self):
        """计算H-Q特性曲线系数: H = a*Q^2 + b*Q + c"""
        Q = np.array([0, self.rated_flow, self.flow_max])
        H = np.array([self.head_max, self.rated_head, self.head_min])
        self.curve_coeffs = np.polyfit(Q, H, 2)

    def _compute_head(self, flow: float) -> float:
        """根据特性曲线计算扬程"""
        return np.polyval(self.curve_coeffs, flow)

    def _compute_efficiency(self, flow: float) -> float:
        """计算效率（简化为高斯曲线）"""
        if flow < 1e-6: return 0.1
        sigma = self.rated_flow * 0.3
        eta = self.state.efficiency * np.exp(-((flow - self.rated_flow)**2) / (2 * sigma**2))
        return max(0.1, min(0.95, eta))

    def update_reduced_order(self, dt: float, inputs: Dict[str, float]) -> ComponentState:
        """泵站特性计算"""
        target_flow = inputs.get('control', self.state.flow)
        self.state.flow = np.clip(target_flow, self.flow_min, self.flow_max)

        if self.state.flow > 0.1:
            self.is_running = True
            self.state.head = self._compute_head(self.state.flow)
            eta = self._compute_efficiency(self.state.flow)
            rho = 1000
            g = 9.81
            self.state.power = (rho * g * self.state.flow * self.state.head) / (eta * 1000) if eta > 0 else 0
            self.state.efficiency = eta
        else:
            self.is_running = False
            self.state.power = 0
            self.state.head = 0
        return self.state

    def get_constraints(self) -> Dict[str, Tuple[float, float]]:
        constraints = super().get_constraints()
        constraints['head'] = (self.head_min, self.head_max)
        constraints['power'] = (0, self.rated_power * 1.2)
        return constraints
