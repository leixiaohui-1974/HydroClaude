# -*- coding: utf-8 -*-
"""
Valve - Hydraulic valve component for flow and pressure control

Supports multiple valve types and flow characteristics:
- Gate Valve: Linear characteristic
- Butterfly Valve: Equal percentage characteristic
- Ball Valve: Quick opening characteristic

Flow equation: Q = Cv(tau) * sqrt(Delta_P / rho)
where:
    Cv: Flow coefficient (varies with opening)
    tau: Opening (0-1)
    Delta_P: Pressure drop across valve (Pa)
    rho: Fluid density (kg/m3)

Author: Claude
Date: 2025-10-22
"""

import numpy as np
from core.base import HydraulicComponent
from core.states import ComponentState


class Valve(HydraulicComponent):
    """
    Valve base class - Flow and pressure control

    Supports 3 flow characteristic curves:
    - Quick opening: Flow increases rapidly with opening
    - Linear: Flow proportional to opening
    - Equal percentage: Equal percentage change in flow for equal opening change
    """

    def __init__(self, name: str, valve_type: str = 'linear',
                 Cv_max: float = 100.0, response_time: float = 5.0,
                 g: float = 9.81):
        """
        Args:
            name: Valve name
            valve_type: Valve type ('quick', 'linear', 'equal_percentage')
            Cv_max: Maximum flow coefficient
            response_time: Response time (s), 0 for instantaneous
            g: Gravity acceleration (m/s2)
        """
        super().__init__(name, "valve")
        self.valve_type = valve_type
        self.Cv_max = Cv_max
        self.response_time = response_time
        self.g = g

        # Equal percentage characteristic parameter
        self.R = 50  # Rangeability, typical value 50

        # Fluid density
        self.rho = 1000.0  # kg/m3, water

        self.state = ComponentState()
        self.state.opening = 1.0  # Opening (0-1), default fully open
        self.state.flow = 0.0
        self.state.pressure_drop = 0.0
        self.state.pressure = 0.0  # Downstream pressure

    def get_Cv(self, opening: float) -> float:
        """
        Calculate flow coefficient

        Args:
            opening: Valve opening (0-1)

        Returns:
            Flow coefficient
        """
        tau = np.clip(opening, 0.0, 1.0)

        if tau < 1e-6:
            return 0.0

        if self.valve_type == 'quick':
            # Quick opening: Cv = Cv_max * tau^2
            Cv = self.Cv_max * (tau ** 2)

        elif self.valve_type == 'linear':
            # Linear: Cv = Cv_max * tau
            Cv = self.Cv_max * tau

        elif self.valve_type == 'equal_percentage':
            # Equal percentage: Cv = Cv_max * R^(tau-1)
            Cv = self.Cv_max * (self.R ** (tau - 1))

        else:
            raise ValueError(f"Unknown valve type: {self.valve_type}")

        return Cv

    def calculate_flow(self, P_upstream: float, P_downstream: float,
                       opening: float = None) -> float:
        """
        Calculate flow through valve

        Q = Cv * sqrt(Delta_P / rho)

        Args:
            P_upstream: Upstream pressure (Pa)
            P_downstream: Downstream pressure (Pa)
            opening: Valve opening (0-1), uses current if None

        Returns:
            Flow rate (m3/s)
        """
        if opening is None:
            opening = self.state.opening

        delta_P = max(0.0, P_upstream - P_downstream)

        if delta_P < 1e-6:
            return 0.0

        Cv = self.get_Cv(opening)
        Q = Cv * np.sqrt(delta_P / self.rho)

        return Q

    def calculate_flow_derivatives(self, P_upstream: float, P_downstream: float,
                                  opening: float = None) -> tuple:
        """
        Calculate analytical derivatives of flow w.r.t. pressure (for Jacobian)

        Q = Cv * sqrt(Delta_P / rho)
        dQ/dP_up = Cv / (2 * sqrt(Delta_P * rho))
        dQ/dP_down = -dQ/dP_up

        Args:
            P_upstream: Upstream pressure (Pa)
            P_downstream: Downstream pressure (Pa)
            opening: Valve opening (0-1)

        Returns:
            (dQ/dP_up, dQ/dP_down): Derivatives
        """
        if opening is None:
            opening = self.state.opening

        delta_P = max(1e-4, P_upstream - P_downstream)
        Cv = self.get_Cv(opening)

        if delta_P > 1e-4:
            dQ_dP_up = Cv / (2.0 * np.sqrt(delta_P * self.rho))
            dQ_dP_down = -dQ_dP_up
        else:
            dQ_dP_up = Cv / (2.0 * np.sqrt(1e-4 * self.rho))
            dQ_dP_down = -dQ_dP_up

        return dQ_dP_up, dQ_dP_down

    def update_high_fidelity(self, dt: float, inputs: dict) -> ComponentState:
        """
        High-fidelity update (with dynamic response)

        Args:
            dt: Time step (s)
            inputs: Input dictionary
                - 'target_opening': Target opening (0-1)
                - 'upstream_pressure': Upstream pressure (Pa)
                - 'downstream_pressure': Downstream pressure (Pa)

        Returns:
            Updated state
        """
        target_opening = inputs.get('target_opening', self.state.opening)
        target_opening = np.clip(target_opening, 0.0, 1.0)

        # Dynamic response (first-order lag)
        if self.response_time > 0:
            tau = dt / self.response_time
            tau = min(tau, 1.0)
            self.state.opening += tau * (target_opening - self.state.opening)
        else:
            self.state.opening = target_opening

        self.state.opening = np.clip(self.state.opening, 0.0, 1.0)

        # Calculate flow
        P_up = inputs.get('upstream_pressure', 0.0)
        P_down = inputs.get('downstream_pressure', 0.0)

        self.state.flow = self.calculate_flow(P_up, P_down)
        self.state.pressure_drop = P_up - P_down
        self.state.pressure = P_down

        return self.state

    def update_reduced_order(self, dt: float, inputs: dict) -> ComponentState:
        """Reduced-order model (same as high-fidelity)"""
        return self.update_high_fidelity(dt, inputs)

    def get_constraints(self) -> dict:
        """Get constraints"""
        return {
            'opening': (0.0, 1.0),
            'Cv': (0.0, self.Cv_max),
            'flow': (0.0, np.inf),
            'pressure_drop': (0.0, np.inf)
        }

    def __repr__(self) -> str:
        return (f"{self.__class__.__name__}(name='{self.name}', "
                f"type={self.valve_type}, Cv_max={self.Cv_max}, "
                f"opening={self.state.opening:.2f})")


class GateValve(Valve):
    """Gate Valve - Linear characteristic"""

    def __init__(self, name: str, Cv_max: float = 100.0,
                 response_time: float = 10.0, **kwargs):
        super().__init__(name, valve_type='linear', Cv_max=Cv_max,
                        response_time=response_time, **kwargs)


class ButterflyValve(Valve):
    """Butterfly Valve - Equal percentage characteristic"""

    def __init__(self, name: str, Cv_max: float = 100.0,
                 response_time: float = 3.0, rangeability: float = 50.0,
                 **kwargs):
        super().__init__(name, valve_type='equal_percentage', Cv_max=Cv_max,
                        response_time=response_time, **kwargs)
        self.R = rangeability


class BallValve(Valve):
    """Ball Valve - Quick opening characteristic"""

    def __init__(self, name: str, Cv_max: float = 100.0,
                 response_time: float = 2.0, **kwargs):
        super().__init__(name, valve_type='quick', Cv_max=Cv_max,
                        response_time=response_time, **kwargs)


class ControlValve(ButterflyValve):
    """Control Valve - Alias for ButterflyValve"""
    pass


if __name__ == "__main__":
    print("=" * 80)
    print("Valve Class Test")
    print("=" * 80)

    # Create 3 valve types
    gate_valve = GateValve("GV1", Cv_max=50.0)
    butterfly_valve = ButterflyValve("BV1", Cv_max=80.0)
    ball_valve = BallValve("BLV1", Cv_max=30.0)

    print(f"\nCreated valves:")
    print(f"  1. {gate_valve}")
    print(f"  2. {butterfly_valve}")
    print(f"  3. {ball_valve}")

    # Test flow coefficient curves
    print(f"\nFlow coefficient comparison (normalized by Cv_max):")
    print(f"{'Opening':>8} {'Gate(Linear)':>15} {'Butterfly(EqPct)':>18} {'Ball(Quick)':>15}")
    print("-" * 60)

    openings = [0.0, 0.1, 0.2, 0.3, 0.4, 0.5, 0.6, 0.7, 0.8, 0.9, 1.0]
    for tau in openings:
        Cv_gate = gate_valve.get_Cv(tau) / gate_valve.Cv_max
        Cv_butterfly = butterfly_valve.get_Cv(tau) / butterfly_valve.Cv_max
        Cv_ball = ball_valve.get_Cv(tau) / ball_valve.Cv_max

        print(f"{tau:8.1f} {Cv_gate:15.4f} {Cv_butterfly:18.4f} {Cv_ball:15.4f}")

    # Test flow calculation
    print(f"\nFlow calculation test (P_up=500kPa, P_down=100kPa):")
    P_up = 500000.0
    P_down = 100000.0

    for valve in [gate_valve, butterfly_valve, ball_valve]:
        valve.state.opening = 0.5
        Q = valve.calculate_flow(P_up, P_down)
        print(f"  {valve.name:5s}: Q={Q:.3f} m3/s @ 50% opening")

    # Test derivatives
    print(f"\nDerivative test (analytical vs numerical):")
    valve = butterfly_valve
    valve.state.opening = 0.6

    dQ_dP_up, dQ_dP_down = valve.calculate_flow_derivatives(P_up, P_down)

    eps = 1e-3
    Q0 = valve.calculate_flow(P_up, P_down)
    Q_up = valve.calculate_flow(P_up + eps, P_down)
    Q_down = valve.calculate_flow(P_up, P_down + eps)

    dQ_dP_up_num = (Q_up - Q0) / eps
    dQ_dP_down_num = (Q_down - Q0) / eps

    print(f"  dQ/dP_up  (analytical): {dQ_dP_up:.6e}")
    print(f"  dQ/dP_up  (numerical):  {dQ_dP_up_num:.6e}")
    print(f"  Relative error: {abs(dQ_dP_up - dQ_dP_up_num)/abs(dQ_dP_up_num)*100:.2f}%")
    print()
    print(f"  dQ/dP_down(analytical): {dQ_dP_down:.6e}")
    print(f"  dQ/dP_down(numerical):  {dQ_dP_down_num:.6e}")
    print(f"  Relative error: {abs(dQ_dP_down - dQ_dP_down_num)/abs(dQ_dP_down_num)*100:.2f}%")

    # Test dynamic response
    print(f"\nDynamic response test (Gate valve, 0% to 100%):")
    valve = GateValve("GV_test", response_time=5.0)
    valve.state.opening = 0.0

    dt = 0.5
    times = []
    openings_list = []

    for i in range(20):
        t = i * dt
        valve.update_high_fidelity(dt, {
            'target_opening': 1.0,
            'upstream_pressure': P_up,
            'downstream_pressure': P_down
        })
        times.append(t)
        openings_list.append(valve.state.opening)

        if i % 4 == 0:
            print(f"  t={t:4.1f}s: Opening={valve.state.opening*100:5.1f}%, "
                  f"Flow={valve.state.flow:.3f} m3/s")

    print(f"\nValve class basic test complete!")
    print("=" * 80)
