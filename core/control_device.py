import numpy as np
from typing import Dict, Tuple
from core.component import HydraulicComponent, ComponentType, ComponentState

class ControlDevice(HydraulicComponent):
    """控制设备基类"""

    def __init__(self, name: str, comp_type: ComponentType,
                 flow_min: float, flow_max: float):
        super().__init__(name, comp_type)
        self.flow_min = flow_min
        self.flow_max = flow_max
        self.state.flow = (flow_min + flow_max) / 2

    def get_constraints(self) -> Dict[str, Tuple[float, float]]:
        return {'flow': (self.flow_min, self.flow_max)}

    def compute_derivatives(self, state_vector: np.ndarray,
                          inputs: Dict[str, float]) -> np.ndarray:
        """控制设备状态变化较快，认为准稳态"""
        return np.zeros(4)

class Gate(ControlDevice):
    """闸门 - 实现堰流/孔流方程"""

    def __init__(self, name: str, flow_min: float, flow_max: float,
                 width: float = 3.0, max_opening: float = 5.0):
        super().__init__(name, ComponentType.GATE, flow_min, flow_max)
        self.width = width
        self.max_opening = max_opening
        self.state.opening = max_opening / 2
        self.Cd = 0.6  # 流量系数

    def update_state(self, dt: float, inputs: Dict[str, float]) -> ComponentState:
        """闸门水力学计算"""
        target_flow = inputs.get('target_flow', self.state.flow)
        upstream_level = inputs.get('upstream_level', 5.0)
        downstream_level = inputs.get('downstream_level', 4.0)

        # 限制目标流量
        target_flow = np.clip(target_flow, self.flow_min, self.flow_max)

        # 水头差
        delta_h = upstream_level - downstream_level

        if delta_h > 0:
            # 自由堰流（当开度较小时）
            if self.state.opening < upstream_level * 0.67:
                # 堰流公式: Q = Cd * b * a * sqrt(2*g*H)
                g = 9.81
                Q_capacity = self.Cd * self.width * self.state.opening * \
                            np.sqrt(2 * g * upstream_level)
            else:
                # 孔流公式: Q = Cd * A * sqrt(2*g*delta_h)
                area = self.width * self.state.opening
                Q_capacity = self.Cd * area * np.sqrt(2 * 9.81 * delta_h)

            # 实际流量不超过容量
            self.state.flow = min(target_flow, Q_capacity)
        else:
            self.state.flow = 0

        # 反算开度
        if upstream_level > 0:
            self.state.opening = self.state.flow / \
                (self.Cd * self.width * np.sqrt(2 * 9.81 * upstream_level) + 1e-6)
            self.state.opening = np.clip(self.state.opening, 0, self.max_opening)

        return self.state

class Valve(ControlDevice):
    """阀门 - 实现阀门特性方程"""

    def __init__(self, name: str, flow_min: float, flow_max: float,
                 diameter: float = 1.0, Cv: float = 100.0):
        super().__init__(name, ComponentType.VALVE, flow_min, flow_max)
        self.diameter = diameter
        self.Cv = Cv  # 阀门流量系数
        self.state.opening = 0.5  # 开度 0-1

    def update_state(self, dt: float, inputs: Dict[str, float]) -> ComponentState:
        """阀门水力学计算"""
        target_flow = inputs.get('target_flow', self.state.flow)
        upstream_pressure = inputs.get('upstream_pressure', 40.0)
        downstream_pressure = inputs.get('downstream_pressure', 35.0)

        self.state.flow = np.clip(target_flow, self.flow_min, self.flow_max)

        # 阀门方程: Q = Cv * tau * sqrt(delta_P)
        # tau 是开度函数，这里简化为线性
        delta_P = max(0.1, upstream_pressure - downstream_pressure)

        # 计算所需开度
        Q_max = self.Cv * np.sqrt(delta_P)
        self.state.opening = self.state.flow / (Q_max + 1e-6)
        self.state.opening = np.clip(self.state.opening, 0, 1)

        # 压降计算
        if self.state.opening > 0.01:
            actual_Cv = self.Cv * self.state.opening
            pressure_drop = (self.state.flow / actual_Cv)**2
        else:
            pressure_drop = upstream_pressure

        self.state.pressure = max(0, upstream_pressure - pressure_drop)

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
        # 三点确定抛物线
        # 点1: (0, head_max) - 零流量扬程
        # 点2: (rated_flow, rated_head) - 额定工况点
        # 点3: (flow_max, head_min) - 最大流量扬程

        Q = np.array([0, self.rated_flow, self.flow_max])
        H = np.array([self.head_max, self.rated_head, self.head_min])

        # 拟合二次曲线
        self.curve_coeffs = np.polyfit(Q, H, 2)
        self.a, self.b, self.c = self.curve_coeffs

    def _compute_head(self, flow: float) -> float:
        """根据特性曲线计算扬程"""
        return self.a * flow**2 + self.b * flow + self.c

    def _compute_efficiency(self, flow: float) -> float:
        """计算效率（简化为高斯曲线）"""
        if flow < 1e-6:
            return 0.1

        # 在额定点效率最高
        sigma = self.rated_flow * 0.3
        eta = self.state.efficiency * np.exp(-((flow - self.rated_flow)**2) / (2 * sigma**2))
        return max(0.1, min(0.95, eta))

    def update_state(self, dt: float, inputs: Dict[str, float]) -> ComponentState:
        """泵站特性计算"""
        target_flow = inputs.get('target_flow', self.state.flow)
        suction_level = inputs.get('suction_level', 0.0)
        discharge_level = inputs.get('discharge_level', 0.0)

        self.state.flow = np.clip(target_flow, self.flow_min, self.flow_max)

        if self.state.flow > 0.1:
            self.is_running = True

            # 根据特性曲线计算扬程
            self.state.head = self._compute_head(self.state.flow)
            self.state.pressure = self.state.head

            # 计算效率
            eta = self._compute_efficiency(self.state.flow)

            # 计算功率: P = ρ*g*Q*H / η
            rho = 1000  # kg/m³
            g = 9.81    # m/s²
            self.state.power = (rho * g * self.state.flow * self.state.head) / (eta * 1000)
            self.state.efficiency = eta
        else:
            self.is_running = False
            self.state.power = 0
            self.state.head = 0
            self.state.pressure = 0

        return self.state

    def get_constraints(self) -> Dict[str, Tuple[float, float]]:
        constraints = super().get_constraints()
        constraints['head'] = (self.head_min, self.head_max)
        constraints['power'] = (0, self.rated_power * 1.2)
        return constraints
