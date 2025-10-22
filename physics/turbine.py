# -*- coding: utf-8 -*-
"""
Hydraulic Turbine Models
========================

Implements hydraulic turbines for hydropower systems:
- Francis turbine (reaction, medium head)
- Kaplan turbine (axial flow, low head)
- Pelton turbine (impulse, high head)

Each turbine includes:
- Characteristic curves (Hill charts)
- Efficiency calculations
- Power output
- Speed control
- Analytical derivatives for Newton solver

Author: Claude
Date: 2025-10-22
"""

import numpy as np
from typing import Optional, Tuple
from abc import ABC, abstractmethod


class Turbine(ABC):
    """
    Abstract base class for hydraulic turbines

    All turbines must implement:
    - calculate_power(): Power output calculation
    - calculate_efficiency(): Efficiency calculation
    - calculate_torque(): Torque calculation
    - calculate_derivatives(): Analytical derivatives for Jacobian
    """

    def __init__(self, position: float, rated_power: float, rated_head: float,
                 rated_flow: float, rated_speed: float, g: float = 9.81,
                 rho: float = 1000.0):
        """
        Base turbine initialization

        Args:
            position: Turbine position (m)
            rated_power: Rated power output (MW)
            rated_head: Rated head (m)
            rated_flow: Rated flow rate (m³/s)
            rated_speed: Rated rotational speed (rpm)
            g: Gravitational acceleration (m/s²)
            rho: Water density (kg/m³)
        """
        self.position = position
        self.rated_power = rated_power * 1e6  # Convert MW to W
        self.rated_head = rated_head
        self.rated_flow = rated_flow
        self.rated_speed = rated_speed
        self.g = g
        self.rho = rho

        # Calculate rated efficiency (reverse from power equation)
        # P = η * ρ * g * Q * H
        self.rated_efficiency = self.rated_power / (self.rho * self.g * self.rated_flow * self.rated_head)

        # Runner diameter (estimated from specific speed)
        # Will be overridden by specific turbine types
        self.runner_diameter = 1.0

    @abstractmethod
    def calculate_power(self, Q: float, H: float, n: Optional[float] = None,
                       opening: Optional[float] = None) -> Tuple[float, float, str]:
        """
        Calculate turbine power output

        Args:
            Q: Flow rate (m³/s)
            H: Net head (m)
            n: Rotational speed (rpm), defaults to rated speed
            opening: Guide vane/nozzle opening (0-1), defaults to optimal

        Returns:
            (power, efficiency, operating_mode): Power (W), efficiency (0-1), mode string
        """
        pass

    @abstractmethod
    def calculate_efficiency(self, Q: float, H: float, n: Optional[float] = None,
                            opening: Optional[float] = None) -> float:
        """Calculate turbine efficiency"""
        pass

    def calculate_torque(self, P: float, n: float) -> float:
        """
        Calculate shaft torque

        Args:
            P: Power (W)
            n: Rotational speed (rpm)

        Returns:
            T: Torque (N·m)
        """
        # T = P / ω, where ω = 2πn/60
        omega = 2.0 * np.pi * n / 60.0
        return P / omega if omega > 0 else 0.0

    @abstractmethod
    def calculate_derivatives(self, Q: float, H: float, n: Optional[float] = None,
                             opening: Optional[float] = None) -> Tuple[float, float]:
        """
        Calculate analytical derivatives for Jacobian matrix

        Args:
            Q: Flow rate (m³/s)
            H: Net head (m)
            n: Rotational speed (rpm)
            opening: Guide vane/nozzle opening (0-1)

        Returns:
            (dP_dQ, dP_dH): Derivatives of power w.r.t. Q and H
        """
        pass


class FrancisTurbine(Turbine):
    """
    Francis Turbine (Reaction turbine, medium head: 40-600m)

    Characteristics:
    - Radial/mixed flow
    - Guide vanes for flow control
    - Hill chart efficiency curves
    - Typical efficiency: 90-95%
    - Head range: 40-600 m
    - Specific speed: 60-400 (metric)

    Efficiency Model:
    η = η_max * f(Q/Q_rated, H/H_rated, opening)

    Power:
    P = η * ρ * g * Q * H
    """

    def __init__(self, position: float, rated_power: float, rated_head: float,
                 rated_flow: float, rated_speed: float, runner_diameter: float = 2.0,
                 max_efficiency: float = 0.93, g: float = 9.81, rho: float = 1000.0):
        """
        Francis turbine initialization

        Args:
            position: Turbine position (m)
            rated_power: Rated power (MW)
            rated_head: Rated head (m)
            rated_flow: Rated flow rate (m³/s)
            rated_speed: Rated speed (rpm)
            runner_diameter: Runner diameter (m)
            max_efficiency: Maximum efficiency (default 0.93)
            g: Gravitational acceleration (m/s²)
            rho: Water density (kg/m³)
        """
        super().__init__(position, rated_power, rated_head, rated_flow, rated_speed, g, rho)
        self.runner_diameter = runner_diameter
        self.max_efficiency = max_efficiency
        self.turbine_type = 'Francis'

        # Calculate specific speed (metric)
        # ns = n * √P / H^(5/4), where P in kW
        power_kW = rated_power * 1000.0
        self.specific_speed = (rated_speed * np.sqrt(power_kW)) / (rated_head ** 1.25)

    def calculate_efficiency(self, Q: float, H: float, n: Optional[float] = None,
                            opening: Optional[float] = None) -> float:
        """
        Calculate Francis turbine efficiency using Hill chart approximation

        The efficiency depends on:
        - Flow ratio (Q/Q_rated)
        - Head ratio (H/H_rated)
        - Speed ratio (n/n_rated)

        Simplified model (parabolic approximation):
        η = η_max * exp(-a*(Q/Q_opt - 1)² - b*(H/H_opt - 1)²)
        """
        if Q <= 0 or H <= 0:
            return 0.0

        # Use rated values if not specified
        n = n if n is not None else self.rated_speed
        opening = opening if opening is not None else 1.0

        # Dimensionless parameters
        Q_ratio = Q / self.rated_flow
        H_ratio = H / self.rated_head
        n_ratio = n / self.rated_speed

        # Optimal operating point (depends on opening)
        Q_opt = opening * self.rated_flow * n_ratio
        H_opt = self.rated_head * (n_ratio ** 2)

        # Efficiency drop coefficients (empirical)
        a_Q = 0.5  # Flow sensitivity
        a_H = 0.3  # Head sensitivity

        # Parabolic efficiency curve
        if Q_opt > 0 and H_opt > 0:
            eta = self.max_efficiency * np.exp(
                -a_Q * ((Q / Q_opt - 1.0) ** 2) -
                a_H * ((H / H_opt - 1.0) ** 2)
            )
        else:
            eta = 0.0

        # Minimum efficiency floor
        eta = max(0.0, min(eta, self.max_efficiency))

        return eta

    def calculate_power(self, Q: float, H: float, n: Optional[float] = None,
                       opening: Optional[float] = None) -> Tuple[float, float, str]:
        """
        Calculate Francis turbine power output

        P = η(Q, H, n) * ρ * g * Q * H

        Returns:
            (power, efficiency, mode)
        """
        if Q <= 0 or H <= 0:
            return 0.0, 0.0, 'stopped'

        # Calculate efficiency
        eta = self.calculate_efficiency(Q, H, n, opening)

        # Power equation
        P = eta * self.rho * self.g * Q * H

        # Determine operating mode
        Q_ratio = Q / self.rated_flow
        if Q_ratio < 0.3:
            mode = 'part_load'
        elif Q_ratio > 1.1:
            mode = 'overload'
        else:
            mode = 'normal'

        return P, eta, mode

    def calculate_derivatives(self, Q: float, H: float, n: Optional[float] = None,
                             opening: Optional[float] = None) -> Tuple[float, float]:
        """
        Calculate analytical derivatives dP/dQ and dP/dH

        P = η(Q, H) * ρ * g * Q * H

        dP/dQ = ρ * g * H * (η + Q * dη/dQ)
        dP/dH = ρ * g * Q * (η + H * dη/dH)

        For simplicity, assume η is approximately constant (valid near rated point)
        This gives first-order approximation:

        dP/dQ ≈ ρ * g * H * η
        dP/dH ≈ ρ * g * Q * η
        """
        if Q <= 0 or H <= 0:
            return 0.0, 0.0

        eta = self.calculate_efficiency(Q, H, n, opening)

        # First-order approximation (constant efficiency)
        dP_dQ = self.rho * self.g * H * eta
        dP_dH = self.rho * self.g * Q * eta

        return dP_dQ, dP_dH

    def __repr__(self):
        return (f"FrancisTurbine(pos={self.position}m, "
                f"P_rated={self.rated_power/1e6:.1f}MW, "
                f"H_rated={self.rated_head:.1f}m, "
                f"Q_rated={self.rated_flow:.1f}m³/s, "
                f"n={self.rated_speed:.0f}rpm, "
                f"D={self.runner_diameter:.1f}m, "
                f"η_max={self.max_efficiency:.1%})")


class KaplanTurbine(Turbine):
    """
    Kaplan Turbine (Axial flow turbine, low head: 10-70m)

    Characteristics:
    - Axial flow (propeller type)
    - Double regulation: guide vanes + runner blade pitch
    - Excellent part-load efficiency
    - Typical efficiency: 90-95%
    - Head range: 10-70 m
    - Specific speed: 300-1000 (metric)

    The adjustable runner blades allow Kaplan turbines to maintain high
    efficiency over a wide range of flow rates.
    """

    def __init__(self, position: float, rated_power: float, rated_head: float,
                 rated_flow: float, rated_speed: float, runner_diameter: float = 4.0,
                 max_efficiency: float = 0.94, g: float = 9.81, rho: float = 1000.0):
        """
        Kaplan turbine initialization

        Args:
            position: Turbine position (m)
            rated_power: Rated power (MW)
            rated_head: Rated head (m)
            rated_flow: Rated flow rate (m³/s)
            rated_speed: Rated speed (rpm)
            runner_diameter: Runner diameter (m, typically larger than Francis)
            max_efficiency: Maximum efficiency (default 0.94)
            g: Gravitational acceleration (m/s²)
            rho: Water density (kg/m³)
        """
        super().__init__(position, rated_power, rated_head, rated_flow, rated_speed, g, rho)
        self.runner_diameter = runner_diameter
        self.max_efficiency = max_efficiency
        self.turbine_type = 'Kaplan'

        # Calculate specific speed (Kaplan has high specific speed)
        # ns = n * √P / H^(5/4), where P in kW
        power_kW = rated_power * 1000.0
        self.specific_speed = (rated_speed * np.sqrt(power_kW)) / (rated_head ** 1.25)

    def calculate_efficiency(self, Q: float, H: float, n: Optional[float] = None,
                            opening: Optional[float] = None) -> float:
        """
        Calculate Kaplan turbine efficiency

        Kaplan turbines have excellent part-load efficiency due to double regulation.
        The efficiency curve is flatter than Francis turbines.

        η = η_max * (1 - a*(Q/Q_rated - 1)²)

        with smaller 'a' coefficient due to blade pitch adjustment
        """
        if Q <= 0 or H <= 0:
            return 0.0

        n = n if n is not None else self.rated_speed
        opening = opening if opening is not None else 1.0

        # Dimensionless flow
        Q_ratio = Q / self.rated_flow
        n_ratio = n / self.rated_speed

        # Optimal flow (adjusted by speed)
        Q_opt = opening * self.rated_flow * n_ratio

        # Kaplan has flatter efficiency curve (smaller coefficient)
        a_Q = 0.2  # Much flatter than Francis (0.5)

        if Q_opt > 0:
            eta = self.max_efficiency * np.exp(-a_Q * ((Q / Q_opt - 1.0) ** 2))
        else:
            eta = 0.0

        eta = max(0.0, min(eta, self.max_efficiency))

        return eta

    def calculate_power(self, Q: float, H: float, n: Optional[float] = None,
                       opening: Optional[float] = None) -> Tuple[float, float, str]:
        """Calculate Kaplan turbine power output"""
        if Q <= 0 or H <= 0:
            return 0.0, 0.0, 'stopped'

        eta = self.calculate_efficiency(Q, H, n, opening)
        P = eta * self.rho * self.g * Q * H

        Q_ratio = Q / self.rated_flow
        if Q_ratio < 0.2:
            mode = 'part_load'
        elif Q_ratio > 1.15:
            mode = 'overload'
        else:
            mode = 'normal'

        return P, eta, mode

    def calculate_derivatives(self, Q: float, H: float, n: Optional[float] = None,
                             opening: Optional[float] = None) -> Tuple[float, float]:
        """Calculate analytical derivatives (same as Francis for first-order)"""
        if Q <= 0 or H <= 0:
            return 0.0, 0.0

        eta = self.calculate_efficiency(Q, H, n, opening)

        dP_dQ = self.rho * self.g * H * eta
        dP_dH = self.rho * self.g * Q * eta

        return dP_dQ, dP_dH

    def __repr__(self):
        return (f"KaplanTurbine(pos={self.position}m, "
                f"P_rated={self.rated_power/1e6:.1f}MW, "
                f"H_rated={self.rated_head:.1f}m, "
                f"Q_rated={self.rated_flow:.1f}m³/s, "
                f"n={self.rated_speed:.0f}rpm, "
                f"D={self.runner_diameter:.1f}m, "
                f"η_max={self.max_efficiency:.1%})")


class PeltonTurbine(Turbine):
    """
    Pelton Turbine (Impulse turbine, high head: 300-1500m)

    Characteristics:
    - Impulse turbine (jet hits buckets)
    - One or more nozzles
    - Atmospheric pressure runner
    - Typical efficiency: 85-92%
    - Head range: 300-1500 m
    - Specific speed: 10-70 (metric)

    Flow Control:
    - Nozzle needle position
    - Deflector for rapid load changes

    Jet Velocity:
    v_jet = Cv * √(2 * g * H)

    Power:
    P = η * ρ * Q * (v_jet)² / 2
      = η * ρ * g * Q * H  (same form as reaction turbines)
    """

    def __init__(self, position: float, rated_power: float, rated_head: float,
                 rated_flow: float, rated_speed: float, runner_diameter: float = 3.0,
                 num_nozzles: int = 1, jet_diameter: float = 0.2,
                 max_efficiency: float = 0.90, Cv: float = 0.98,
                 g: float = 9.81, rho: float = 1000.0):
        """
        Pelton turbine initialization

        Args:
            position: Turbine position (m)
            rated_power: Rated power (MW)
            rated_head: Rated head (m)
            rated_flow: Rated flow rate (m³/s, total for all nozzles)
            rated_speed: Rated speed (rpm)
            runner_diameter: Pitch circle diameter (m)
            num_nozzles: Number of nozzles (1-6)
            jet_diameter: Jet diameter at nozzle (m)
            max_efficiency: Maximum efficiency (default 0.90)
            Cv: Velocity coefficient (nozzle efficiency, default 0.98)
            g: Gravitational acceleration (m/s²)
            rho: Water density (kg/m³)
        """
        super().__init__(position, rated_power, rated_head, rated_flow, rated_speed, g, rho)
        self.runner_diameter = runner_diameter
        self.num_nozzles = num_nozzles
        self.jet_diameter = jet_diameter
        self.max_efficiency = max_efficiency
        self.Cv = Cv
        self.turbine_type = 'Pelton'

        # Calculate specific speed (Pelton has low specific speed)
        # ns = n * √P / H^(5/4), where P in kW
        power_kW = rated_power * 1000.0
        self.specific_speed = (rated_speed * np.sqrt(power_kW)) / (rated_head ** 1.25)

        # Jet area
        self.jet_area = np.pi * (jet_diameter / 2.0) ** 2 * num_nozzles

    def calculate_jet_velocity(self, H: float) -> float:
        """
        Calculate jet velocity from head

        v_jet = Cv * √(2 * g * H)

        Args:
            H: Net head (m)

        Returns:
            v_jet: Jet velocity (m/s)
        """
        return self.Cv * np.sqrt(2.0 * self.g * H)

    def calculate_efficiency(self, Q: float, H: float, n: Optional[float] = None,
                            opening: Optional[float] = None) -> float:
        """
        Calculate Pelton turbine efficiency

        Efficiency depends on the speed ratio:
        u / v_jet = optimal around 0.46-0.48

        where:
        u = runner pitch velocity = π * D * n / 60
        v_jet = jet velocity = Cv * √(2 * g * H)

        η = η_max * f(u/v_jet, Q/Q_rated)
        """
        if Q <= 0 or H <= 0:
            return 0.0

        n = n if n is not None else self.rated_speed
        opening = opening if opening is not None else 1.0

        # Runner peripheral velocity
        u = np.pi * self.runner_diameter * n / 60.0  # m/s

        # Jet velocity
        v_jet = self.calculate_jet_velocity(H)

        # Speed ratio
        speed_ratio = u / v_jet if v_jet > 0 else 0.0

        # Optimal speed ratio for Pelton
        optimal_speed_ratio = 0.47

        # Flow ratio
        Q_ratio = Q / self.rated_flow

        # Efficiency model
        # Penalty for deviation from optimal speed ratio
        a_speed = 2.0  # Speed ratio sensitivity
        a_flow = 0.4   # Flow ratio sensitivity

        eta = self.max_efficiency * np.exp(
            -a_speed * ((speed_ratio / optimal_speed_ratio - 1.0) ** 2) -
            a_flow * ((Q_ratio / opening - 1.0) ** 2)
        )

        eta = max(0.0, min(eta, self.max_efficiency))

        return eta

    def calculate_power(self, Q: float, H: float, n: Optional[float] = None,
                       opening: Optional[float] = None) -> Tuple[float, float, str]:
        """
        Calculate Pelton turbine power output

        P = η * ρ * g * Q * H
        """
        if Q <= 0 or H <= 0:
            return 0.0, 0.0, 'stopped'

        eta = self.calculate_efficiency(Q, H, n, opening)
        P = eta * self.rho * self.g * Q * H

        Q_ratio = Q / self.rated_flow
        if Q_ratio < 0.2:
            mode = 'part_load'
        elif Q_ratio > 1.05:
            mode = 'overload'
        else:
            mode = 'normal'

        return P, eta, mode

    def calculate_derivatives(self, Q: float, H: float, n: Optional[float] = None,
                             opening: Optional[float] = None) -> Tuple[float, float]:
        """Calculate analytical derivatives"""
        if Q <= 0 or H <= 0:
            return 0.0, 0.0

        eta = self.calculate_efficiency(Q, H, n, opening)

        dP_dQ = self.rho * self.g * H * eta
        dP_dH = self.rho * self.g * Q * eta

        return dP_dQ, dP_dH

    def __repr__(self):
        return (f"PeltonTurbine(pos={self.position}m, "
                f"P_rated={self.rated_power/1e6:.1f}MW, "
                f"H_rated={self.rated_head:.1f}m, "
                f"Q_rated={self.rated_flow:.1f}m³/s, "
                f"n={self.rated_speed:.0f}rpm, "
                f"D={self.runner_diameter:.1f}m, "
                f"nozzles={self.num_nozzles}, "
                f"η_max={self.max_efficiency:.1%})")


# Utility functions
def select_turbine_type(head: float) -> str:
    """
    Recommend turbine type based on head

    Args:
        head: Available head (m)

    Returns:
        turbine_type: Recommended type ('Kaplan', 'Francis', or 'Pelton')
    """
    if head < 70:
        return 'Kaplan'
    elif head < 300:
        return 'Francis'
    else:
        return 'Pelton'


def calculate_specific_speed(power_MW: float, head: float, speed_rpm: float) -> float:
    """
    Calculate specific speed (metric definition)

    ns = n * √P / H^(5/4)

    where:
    - n: rotational speed (rpm)
    - P: power (kW) - NOTE: input is MW, converted to kW internally
    - H: head (m)

    Typical ranges:
    - Pelton: 10-70
    - Francis: 60-400
    - Kaplan: 300-1000
    """
    power_kW = power_MW * 1000.0  # Convert MW to kW
    return (speed_rpm * np.sqrt(power_kW)) / (head ** 1.25)


if __name__ == "__main__":
    print("=" * 80)
    print("HYDRAULIC TURBINE MODULE")
    print("=" * 80)

    # Example: Create three types of turbines
    print("\nExample Turbines:")
    print("-" * 80)

    # Francis turbine (medium head hydropower plant)
    francis = FrancisTurbine(
        position=0.0,
        rated_power=100.0,  # MW
        rated_head=150.0,   # m
        rated_flow=80.0,    # m³/s
        rated_speed=250.0,  # rpm
        runner_diameter=2.5
    )
    print(f"1. {francis}")

    # Kaplan turbine (low head run-of-river)
    kaplan = KaplanTurbine(
        position=0.0,
        rated_power=50.0,   # MW
        rated_head=25.0,    # m
        rated_flow=230.0,   # m³/s
        rated_speed=115.0,  # rpm
        runner_diameter=5.0
    )
    print(f"2. {kaplan}")

    # Pelton turbine (high head mountain plant)
    pelton = PeltonTurbine(
        position=0.0,
        rated_power=200.0,  # MW
        rated_head=800.0,   # m
        rated_flow=28.0,    # m³/s
        rated_speed=500.0,  # rpm
        runner_diameter=3.0,
        num_nozzles=4
    )
    print(f"3. {pelton}")

    print("\n" + "=" * 80)
    print("Module loaded successfully!")
    print("=" * 80)
