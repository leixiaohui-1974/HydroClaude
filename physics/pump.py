# -*- coding: utf-8 -*-
"""
Pump - Hydraulic pump component with characteristic curves

Supports:
- Parabolic head-flow characteristic: H = H0 - a*Q^2
- Efficiency curve: eta(Q)
- Similarity laws for speed variation
- Operating point calculation

Flow equation: H_pump(Q, n) = H_system(Q)
where:
    H_pump: Pump head characteristic
    H_system: System head requirement
    n: Pump speed (rpm)
    Q: Flow rate (m3/s)

Author: Claude
Date: 2025-10-22
"""

import numpy as np
from core.base import HydraulicComponent
from core.states import ComponentState


class Pump(HydraulicComponent):
    """
    Pump with complete characteristic curves

    Uses parabolic head-flow curve and efficiency curve
    Supports speed variation via similarity laws
    """

    def __init__(self, name: str, rated_flow: float = 100.0,
                 rated_head: float = 50.0, rated_speed: float = 1500.0,
                 shutoff_head_ratio: float = 1.2, max_efficiency: float = 0.85):
        """
        Args:
            name: Pump name
            rated_flow: Rated flow rate (m3/s)
            rated_head: Rated head (m)
            rated_speed: Rated speed (rpm)
            shutoff_head_ratio: Ratio of shutoff head to rated head (typically 1.1-1.3)
            max_efficiency: Maximum efficiency (0-1)
        """
        super().__init__(name, "pump")
        self.rated_flow = rated_flow
        self.rated_head = rated_head
        self.rated_speed = rated_speed
        self.shutoff_head_ratio = shutoff_head_ratio
        self.eta_max = max_efficiency

        # Characteristic curve parameters (parabolic)
        # H = H0 - a*Q^2
        self.H0 = rated_head * shutoff_head_ratio  # Shutoff head (Q=0)
        self.a = -(self.H0 - rated_head) / (rated_flow ** 2)

        # Efficiency curve parameters
        self.Q_eta_max = rated_flow  # Flow at maximum efficiency

        # Physical constants
        self.rho = 1000.0  # Water density (kg/m3)
        self.g = 9.81      # Gravity (m/s2)

        self.state = ComponentState()
        self.state.flow = 0.0
        self.state.head = 0.0
        self.state.power = 0.0
        self.state.efficiency = 0.0
        self.state.speed = rated_speed  # Current speed (rpm)
        self.state.pressure = 0.0

    def calculate_head(self, Q: float, n: float = None) -> float:
        """
        Calculate pump head from flow rate and speed (characteristic curve)

        H = (n/n_rated)^2 * (H0 - a*Q_rated^2)
        where Q_rated = Q / (n/n_rated)

        Args:
            Q: Flow rate (m3/s)
            n: Speed (rpm), uses current speed if None

        Returns:
            Head (m)
        """
        if n is None:
            n = self.state.speed

        # Speed ratio
        speed_ratio = n / self.rated_speed

        if speed_ratio < 0.01:
            return 0.0

        # Convert flow to rated speed equivalent (similarity law)
        # Q1/Q2 = n1/n2
        Q_rated = Q / speed_ratio if speed_ratio > 0.01 else 0.0

        # Parabolic characteristic: H = H0 - a*Q^2
        H_rated = self.H0 + self.a * (Q_rated ** 2)
        H_rated = max(0.0, H_rated)

        # Head scales with speed squared: H1/H2 = (n1/n2)^2
        H = H_rated * (speed_ratio ** 2)

        return H

    def calculate_efficiency(self, Q: float, n: float = None) -> float:
        """
        Calculate pump efficiency

        Uses simplified parabolic efficiency curve:
        eta = eta_max * (1 - ((Q_rated - Q_opt) / Q_opt)^2)

        Args:
            Q: Flow rate (m3/s)
            n: Speed (rpm), uses current speed if None

        Returns:
            Efficiency (0-1)
        """
        if n is None:
            n = self.state.speed

        speed_ratio = n / self.rated_speed

        if speed_ratio < 0.01:
            return 0.0

        Q_rated = Q / speed_ratio if speed_ratio > 0.01 else 0.0

        if Q_rated < 1e-6:
            return 0.0

        # Parabolic efficiency curve (peak at Q_eta_max)
        deviation = (Q_rated - self.Q_eta_max) / self.Q_eta_max
        eta = self.eta_max * (1.0 - deviation ** 2)
        eta = np.clip(eta, 0.1, self.eta_max)

        return eta

    def calculate_power(self, Q: float, H: float, eta: float) -> float:
        """
        Calculate pump power (shaft power)

        P = rho * g * Q * H / eta

        Args:
            Q: Flow rate (m3/s)
            H: Head (m)
            eta: Efficiency (0-1)

        Returns:
            Power (W)
        """
        if eta < 0.01:
            return 0.0

        P = self.rho * self.g * Q * H / eta

        return P

    def solve_operating_point(self, H_system: float, n: float = None,
                             max_iter: int = 20, tol: float = 1e-4) -> float:
        """
        Solve for operating point: H_pump(Q) = H_system

        Uses analytical solution for parabolic curve:
        H0 - a*Q^2 = H_system
        Q = sqrt((H0 - H_system) / a)

        Args:
            H_system: System head requirement (m)
            n: Speed (rpm), uses current speed if None
            max_iter: Maximum iterations (unused, kept for interface)
            tol: Tolerance (unused, kept for interface)

        Returns:
            Flow rate at operating point (m3/s)
        """
        if n is None:
            n = self.state.speed

        speed_ratio = n / self.rated_speed

        if speed_ratio < 0.01:
            return 0.0

        # System head at rated speed
        H_system_rated = H_system / (speed_ratio ** 2)

        # Analytical solution: Q_rated = sqrt((H0 - H_system_rated) / a)
        if H_system_rated >= self.H0:
            # System head exceeds shutoff head, no flow
            return 0.0

        if abs(self.a) < 1e-9:
            # Flat curve, use rated flow
            return self.rated_flow * speed_ratio

        Q_rated_sq = (self.H0 - H_system_rated) / abs(self.a)

        if Q_rated_sq < 0:
            return 0.0

        Q_rated = np.sqrt(Q_rated_sq)

        # Convert to actual speed: Q = Q_rated * (n/n_rated)
        Q = Q_rated * speed_ratio

        return Q

    def update_high_fidelity(self, dt: float, inputs: dict) -> ComponentState:
        """
        High-fidelity update (using characteristic curves)

        Args:
            dt: Time step (s)
            inputs: Input dictionary
                - 'speed': Speed setpoint (rpm) or (0-100%)
                - 'suction_head': Suction head (m)
                - 'discharge_head': Discharge head (m)

        Returns:
            Updated state
        """
        # Parse speed input
        speed_input = inputs.get('speed', self.rated_speed)

        # If speed is in percentage (0-100), convert to rpm
        if speed_input <= 100.0:
            target_speed = self.rated_speed * speed_input / 100.0
        else:
            target_speed = speed_input

        self.state.speed = target_speed

        # Get system head requirement
        h_suction = inputs.get('suction_head', 0.0)
        h_discharge = inputs.get('discharge_head', 0.0)
        H_system = h_discharge - h_suction

        # Solve for operating point
        Q = self.solve_operating_point(H_system, target_speed)

        # Calculate head, efficiency, power
        H = self.calculate_head(Q, target_speed)
        eta = self.calculate_efficiency(Q, target_speed)
        P = self.calculate_power(Q, H, eta)

        # Update state
        self.state.flow = Q
        self.state.head = H
        self.state.efficiency = eta
        self.state.power = P
        self.state.pressure = H * self.rho * self.g  # Convert to Pa

        return self.state

    def update_reduced_order(self, dt: float, inputs: dict) -> ComponentState:
        """
        Reduced-order model (simplified linear relationship)

        Args:
            dt: Time step (s)
            inputs: Input dictionary

        Returns:
            Updated state
        """
        speed_input = inputs.get('speed', 100.0)

        # Convert percentage to ratio
        if speed_input <= 100.0:
            speed_ratio = speed_input / 100.0
        else:
            speed_ratio = speed_input / self.rated_speed

        # Linear approximation
        self.state.flow = self.rated_flow * speed_ratio
        self.state.head = self.rated_head * (speed_ratio ** 2)
        self.state.efficiency = self.eta_max
        self.state.power = self.calculate_power(self.state.flow,
                                                self.state.head,
                                                self.state.efficiency)
        self.state.pressure = self.state.head * self.rho * self.g
        self.state.speed = self.rated_speed * speed_ratio

        return self.state

    def get_constraints(self):
        """Get constraints"""
        return {
            'flow': (0.0, self.rated_flow * 1.2),
            'head': (0.0, self.H0),
            'speed': (0.0, self.rated_speed * 1.2),
            'efficiency': (0.0, self.eta_max),
            'power': (0.0, self.rated_flow * self.rated_head * self.rho * self.g / 0.5)
        }

    def __repr__(self) -> str:
        return (f"Pump(name='{self.name}', Q_rated={self.rated_flow:.1f}m3/s, "
                f"H_rated={self.rated_head:.1f}m, n={self.state.speed:.0f}rpm)")


if __name__ == "__main__":
    print("=" * 80)
    print("Pump Characteristic Curve Test")
    print("=" * 80)

    # Create pump
    pump = Pump(
        name="P1",
        rated_flow=50.0,      # 50 m3/s
        rated_head=100.0,     # 100 m
        rated_speed=1500.0,   # 1500 rpm
        shutoff_head_ratio=1.2,
        max_efficiency=0.85
    )

    print(f"\nPump parameters:")
    print(f"  {pump}")
    print(f"  Shutoff head H0 = {pump.H0:.1f} m")
    print(f"  Characteristic: H = {pump.H0:.1f} - {abs(pump.a):.6f} * Q^2")
    print(f"  Max efficiency: {pump.eta_max*100:.1f}%")

    # Test 1: Characteristic curve at rated speed
    print(f"\n1. Head-Flow Characteristic (at rated speed {pump.rated_speed} rpm):")
    print(f"{'Flow (m3/s)':>15} {'Head (m)':>12} {'Efficiency (%)':>17} {'Power (MW)':>12}")
    print("-" * 60)

    flows = np.linspace(0, pump.rated_flow * 1.1, 12)
    for Q in flows:
        H = pump.calculate_head(Q, pump.rated_speed)
        eta = pump.calculate_efficiency(Q, pump.rated_speed)
        P = pump.calculate_power(Q, H, eta)
        print(f"{Q:15.2f} {H:12.2f} {eta*100:17.1f} {P/1e6:12.3f}")

    # Test 2: Similarity laws (speed variation)
    print(f"\n2. Similarity Laws (at Q = {pump.rated_flow:.0f} m3/s):")
    print(f"{'Speed (rpm)':>15} {'Speed Ratio':>15} {'Head (m)':>12} {'Power (MW)':>12}")
    print("-" * 60)

    speeds = [1000, 1200, 1500, 1800, 2000]
    for n in speeds:
        speed_ratio = n / pump.rated_speed
        H = pump.calculate_head(pump.rated_flow, n)
        eta = pump.calculate_efficiency(pump.rated_flow, n)
        P = pump.calculate_power(pump.rated_flow, H, eta)
        print(f"{n:15.0f} {speed_ratio:15.3f} {H:12.2f} {P/1e6:12.3f}")

    # Test 3: Operating point calculation
    print(f"\n3. Operating Point Calculation:")
    print(f"{'H_system (m)':>15} {'Q_operating (m3/s)':>22} {'H_pump (m)':>12} {'Match?':>8}")
    print("-" * 60)

    H_systems = [80, 90, 100, 110, 115]
    for H_sys in H_systems:
        Q_op = pump.solve_operating_point(H_sys, pump.rated_speed)
        H_pump = pump.calculate_head(Q_op, pump.rated_speed)
        match = "Yes" if abs(H_pump - H_sys) < 0.5 else "No"
        print(f"{H_sys:15.1f} {Q_op:22.3f} {H_pump:12.2f} {match:>8}")

    # Test 4: Full system update
    print(f"\n4. Full System Update Test:")
    pump.update_high_fidelity(1.0, {
        'speed': 100.0,  # 100% = rated speed
        'suction_head': 5.0,
        'discharge_head': 105.0
    })

    print(f"  System head requirement: 100 m")
    print(f"  Operating flow: {pump.state.flow:.3f} m3/s")
    print(f"  Operating head: {pump.state.head:.3f} m")
    print(f"  Efficiency: {pump.state.efficiency*100:.1f}%")
    print(f"  Power: {pump.state.power/1e6:.3f} MW")

    # Test 5: Speed control
    print(f"\n5. Speed Control Test (H_system = 50 m):")
    print(f"{'Speed (%)':>12} {'Flow (m3/s)':>15} {'Head (m)':>12} {'Power (MW)':>12}")
    print("-" * 60)

    for speed_pct in [50, 70, 90, 100, 110]:
        pump.update_high_fidelity(1.0, {
            'speed': speed_pct,
            'suction_head': 0.0,
            'discharge_head': 50.0
        })
        print(f"{speed_pct:12.0f} {pump.state.flow:15.3f} {pump.state.head:12.2f} "
              f"{pump.state.power/1e6:12.3f}")

    print(f"\nPump characteristic curve test complete!")
    print("=" * 80)
