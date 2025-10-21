from abc import ABC, abstractmethod
from typing import Tuple
from scipy.optimize import fsolve
import numpy as np

from core.enums import BoundaryType
from core.states import HydraulicState


class BoundaryCondition(ABC):
    """边界条件抽象基类"""

    def __init__(self, boundary_type: BoundaryType):
        self.boundary_type = boundary_type

    @abstractmethod
    def apply(self, state: HydraulicState, **kwargs) -> Tuple[float, float]:
        """
        应用边界条件
        Returns: (h_boundary, Q_boundary)
        """
        pass

class UpstreamBoundary(BoundaryCondition):
    """上游边界（给定水位或流量）"""

    def __init__(self, fixed_type: str = 'level', value: float = 5.0):
        super().__init__(BoundaryType.UPSTREAM)
        self.fixed_type = fixed_type
        self.value = value

    def apply(self, state: HydraulicState, **kwargs) -> Tuple[float, float]:
        if self.fixed_type == 'level':
            return self.value, state.Q[0]
        else:  # flow
            return state.h[0], self.value

class DownstreamBoundary(BoundaryCondition):
    """下游边界（给定水位或流量）"""

    def __init__(self, fixed_type: str = 'level', value: float = 4.0):
        super().__init__(BoundaryType.DOWNSTREAM)
        self.fixed_type = fixed_type
        self.value = value

    def apply(self, state: HydraulicState, **kwargs) -> Tuple[float, float]:
        if self.fixed_type == 'level':
            return self.value, state.Q[-1]
        else:  # flow
            return state.h[-1], self.value

class GateBoundary(BoundaryCondition):
    """闸门内边界（特征线法+闸门方程）"""

    def __init__(self, width: float = 5.0, Cd: float = 0.6, opening: float = 2.0):
        super().__init__(BoundaryType.INTERNAL)
        self.width = width
        self.Cd = Cd
        self.opening = opening

    def apply(self, state: HydraulicState, **kwargs) -> Tuple[float, float]:
        """
        使用特征线法求解闸门边界
        上游: C+ 特征线
        下游: C- 特征线
        闸门方程: Q = Cd * b * a * sqrt(2*g*h_up)
        """
        # 从kwargs获取上下游状态
        h_up = kwargs.get('h_upstream')
        Q_up = kwargs.get('Q_upstream')
        h_down = kwargs.get('h_downstream')
        Q_down = kwargs.get('Q_downstream')

        g = 9.81
        dx = kwargs.get('dx', 100.0)
        dt = kwargs.get('dt', 1.0)

        # C+ 特征线（从上游传播）
        # Q_gate = Q_up - gA*dt/dx*(h_gate - h_up)
        A_up = kwargs.get('area', 100.0)

        # C- 特征线（从下游传播）
        # Q_gate = Q_down + gA*dt/dx*(h_down - h_gate)
        A_down = A_up

        # 闸门方程（自由堰流或孔流）
        def gate_equations(vars):
            h_gate_up, h_gate_down, Q_gate = vars

            # C+ 特征线
            C_plus = Q_gate - (Q_up - g * A_up * dt / dx * (h_gate_up - h_up))

            # C- 特征线
            C_minus = Q_gate - (Q_down + g * A_down * dt / dx * (h_down - h_gate_down))

            # 闸门方程
            if self.opening < h_gate_up * 0.67:  # 自由堰流
                Q_capacity = self.Cd * self.width * self.opening * np.sqrt(2 * g * h_gate_up)
            else:  # 孔流
                delta_h = max(0.01, h_gate_up - h_gate_down)
                area_opening = self.width * self.opening
                Q_capacity = self.Cd * area_opening * np.sqrt(2 * g * delta_h)

            gate_eq = Q_gate - Q_capacity

            return [C_plus, C_minus, gate_eq]

        # 初始猜测
        h_guess_up = h_up
        h_guess_down = h_down
        Q_guess = (Q_up + Q_down) / 2

        try:
            solution = fsolve(gate_equations, [h_guess_up, h_guess_down, Q_guess])
            h_gate_up, h_gate_down, Q_gate = solution
            return h_gate_down, Q_gate
        except:
            # 失败时返回简化结果
            Q_capacity = self.Cd * self.width * self.opening * np.sqrt(2 * g * h_up)
            return h_down, min(Q_capacity, (Q_up + Q_down) / 2)

class ValveBoundary(BoundaryCondition):
    """阀门内边界（水击方程MOC）"""

    def __init__(self, Cv: float = 100.0, opening: float = 0.5, diameter: float = 1.0):
        super().__init__(BoundaryType.INTERNAL)
        self.Cv = Cv
        self.opening = opening
        self.diameter = diameter

    def apply(self, state: HydraulicState, **kwargs) -> Tuple[float, float]:
        """
        使用MOC求解阀门边界
        C+ 特征线: H_valve = H_up - (a/gA)*Q_valve
        C- 特征线: H_valve = H_down + (a/gA)*Q_valve
        阀门方程: Q = Cv*τ*sqrt(ΔP)
        """
        H_up = kwargs.get('H_upstream')
        Q_up = kwargs.get('Q_upstream')
        H_down = kwargs.get('H_downstream')
        Q_down = kwargs.get('Q_downstream')

        a = kwargs.get('wave_speed', 1000.0)  # 波速
        g = 9.81
        A = np.pi * (self.diameter / 2)**2

        # C+ 特征线常数
        C_plus = H_up + (a / (g * A)) * Q_up

        # C- 特征线常数
        C_minus = H_down - (a / (g * A)) * Q_down

        # 联立求解
        def valve_equations(vars):
            H_valve, Q_valve = vars

            # C+ 特征线
            eq1 = H_valve - (C_plus - (a / (g * A)) * Q_valve)

            # C- 特征线
            eq2 = H_valve - (C_minus + (a / (g * A)) * Q_valve)

            # 阀门方程
            tau = self.opening  # 开度函数
            delta_P = max(0.01, (C_plus - C_minus) / 2)
            Q_capacity = self.Cv * tau * np.sqrt(delta_P)
            eq3 = Q_valve - Q_capacity

            return [eq1 + eq2, eq3]  # 组合前两个方程

        try:
            solution = fsolve(valve_equations, [H_up, Q_up])
            H_valve, Q_valve = solution
            return H_valve, Q_valve
        except:
            return (H_up + H_down) / 2, (Q_up + Q_down) / 2

class PumpBoundary(BoundaryCondition):
    """泵站内边界（特征线法+泵特性曲线）"""

    def __init__(self, a: float = -0.5, b: float = 0.1, c: float = 40.0):
        super().__init__(BoundaryType.INTERNAL)
        # 泵特性曲线系数: H = a*Q^2 + b*Q + c
        self.a = a
        self.b = b
        self.c = c

    def apply(self, state: HydraulicState, **kwargs) -> Tuple[float, float]:
        """
        泵站边界条件
        进口: C+ 特征线
        出口: C- 特征线
        泵特性: H_pump = a*Q^2 + b*Q + c
        能量方程: H_out = H_in + H_pump - h_losses
        """
        H_in = kwargs.get('H_upstream')
        Q_in = kwargs.get('Q_upstream')
        H_out = kwargs.get('H_downstream')
        Q_out = kwargs.get('Q_downstream')

        a_wave = kwargs.get('wave_speed', 1000.0)
        g = 9.81
        A = kwargs.get('area', 1.0)

        # C+ 特征线（进口）
        C_plus = H_in + (a_wave / (g * A)) * Q_in

        # C- 特征线（出口）
        C_minus = H_out - (a_wave / (g * A)) * Q_out

        # 联立求解
        def pump_equations(vars):
            Q_pump, H_pump_rise = vars

            # 进口特征线
            H_inlet = C_plus - (a_wave / (g * A)) * Q_pump

            # 出口特征线
            H_outlet = C_minus + (a_wave / (g * A)) * Q_pump

            # 泵特性曲线
            H_characteristic = self.a * Q_pump**2 + self.b * Q_pump + self.c

            # 能量方程
            eq1 = H_pump_rise - H_characteristic
            eq2 = H_outlet - (H_inlet + H_pump_rise)

            return [eq1, eq2]

        try:
            solution = fsolve(pump_equations, [Q_in, 30.0])
            Q_pump, H_rise = solution
            H_outlet = H_in + H_rise
            return H_outlet, Q_pump
        except:
            return H_out, Q_in
