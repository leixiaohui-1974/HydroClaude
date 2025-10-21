from abc import ABC, abstractmethod
from typing import Tuple, Dict
import numpy as np
from scipy.optimize import fsolve

class BoundaryCondition(ABC):
    """边界条件基类"""

    @abstractmethod
    def apply(self, state, **kwargs) -> Tuple[float, float]:
        """应用边界条件"""
        pass

class GateBoundary(BoundaryCondition):
    """闸门内边界"""

    def __init__(self, width: float, Cd: float, opening: float):
        self.width = width
        self.Cd = Cd
        self.opening = opening

    def apply(self, state, **kwargs) -> Tuple[float, float]:
        h_up = kwargs.get('h_upstream', 5.0)
        Q_up = kwargs.get('Q_upstream', 5.0)
        h_down = kwargs.get('h_downstream', 4.0)
        Q_down = kwargs.get('Q_downstream', 5.0)

        g = 9.81
        dx = kwargs.get('dx', 100.0)
        dt = kwargs.get('dt', 1.0)
        A = kwargs.get('area', 100.0)

        def equations(vars):
            h_gate_up, h_gate_down, Q_gate = vars

            C_plus = Q_gate - (Q_up - g * A * dt / dx * (h_gate_up - h_up))
            C_minus = Q_gate - (Q_down + g * A * dt / dx * (h_down - h_gate_down))

            if self.opening < h_gate_up * 0.67:
                Q_capacity = self.Cd * self.width * self.opening * np.sqrt(2 * g * h_gate_up)
            else:
                delta_h = max(0.01, h_gate_up - h_gate_down)
                Q_capacity = self.Cd * self.width * self.opening * np.sqrt(2 * g * delta_h)

            gate_eq = Q_gate - Q_capacity

            return [C_plus, C_minus, gate_eq]

        try:
            solution = fsolve(equations, [h_up, h_down, (Q_up + Q_down) / 2])
            return solution[1], solution[2]
        except:
            return h_down, (Q_up + Q_down) / 2

class ValveBoundary(BoundaryCondition):
    """阀门内边界"""

    def __init__(self, Cv: float, opening: float, diameter: float):
        self.Cv = Cv
        self.opening = opening
        self.diameter = diameter

    def apply(self, state, **kwargs) -> Tuple[float, float]:
        H_up = kwargs.get('H_upstream', 40.0)
        Q_up = kwargs.get('Q_upstream', 5.0)
        H_down = kwargs.get('H_downstream', 35.0)
        Q_down = kwargs.get('Q_downstream', 5.0)

        a = kwargs.get('wave_speed', 1000.0)
        g = 9.81
        A = np.pi * (self.diameter / 2)**2

        C_plus = H_up + (a / (g * A)) * Q_up
        C_minus = H_down - (a / (g * A)) * Q_down

        def equations(vars):
            H_valve, Q_valve = vars
            eq1 = H_valve - (C_plus - (a / (g * A)) * Q_valve)
            eq2 = H_valve - (C_minus + (a / (g * A)) * Q_valve)

            delta_P = max(0.01, (C_plus - C_minus) / 2)
            Q_capacity = self.Cv * self.opening * np.sqrt(delta_P)
            eq3 = Q_valve - Q_capacity

            return [eq1 + eq2, eq3]

        try:
            solution = fsolve(equations, [H_up, Q_up])
            return solution[0], solution[1]
        except:
            return (H_up + H_down) / 2, (Q_up + Q_down) / 2

class PumpBoundary(BoundaryCondition):
    """泵站内边界"""

    def __init__(self, a: float, b: float, c: float):
        self.a = a
        self.b = b
        self.c = c

    def apply(self, state, **kwargs) -> Tuple[float, float]:
        H_in = kwargs.get('H_upstream', 20.0)
        Q_in = kwargs.get('Q_upstream', 5.0)
        H_out = kwargs.get('H_downstream', 40.0)
        Q_out = kwargs.get('Q_downstream', 5.0)

        a_wave = kwargs.get('wave_speed', 1000.0)
        g = 9.81
        A = kwargs.get('area', 1.0)

        C_plus = H_in + (a_wave / (g * A)) * Q_in
        C_minus = H_out - (a_wave / (g * A)) * Q_out

        def equations(vars):
            Q_pump, H_rise = vars

            H_inlet = C_plus - (a_wave / (g * A)) * Q_pump
            H_outlet = C_minus + (a_wave / (g * A)) * Q_pump

            H_characteristic = self.a * Q_pump**2 + self.b * Q_pump + self.c

            eq1 = H_rise - H_characteristic
            eq2 = H_outlet - (H_inlet + H_rise)

            return [eq1, eq2]

        try:
            solution = fsolve(equations, [Q_in, 30.0])
            return H_in + solution[1], solution[0]
        except:
            return H_out, Q_in
