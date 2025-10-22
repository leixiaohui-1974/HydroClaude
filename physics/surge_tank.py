# -*- coding: utf-8 -*-
"""
Surge Tank Models
=================

Implements surge tanks for hydropower systems:
- Simple surge tank (圆筒式调压井)
- Differential surge tank (差动式调压井)
- Throttled surge tank (阻抗式调压井)

Surge tanks serve to:
- Dampen pressure oscillations (water hammer protection)
- Reduce pressure on turbine and penstock
- Improve regulation characteristics

Physical model:
- Mass balance equation: A_tank * dZ/dt = Q_tunnel - Q_penstock
- Momentum equation for throttle: ΔH = f(Q)

Author: Claude
Date: 2025-10-22
"""

import numpy as np
from typing import Optional, Tuple
from abc import ABC, abstractmethod


class SurgeTank(ABC):
    """
    Abstract base class for surge tanks

    All surge tanks must implement:
    - calculate_water_level(): Water level calculation
    - calculate_surge_period(): Natural oscillation period
    - calculate_derivatives(): Derivatives for transient analysis
    """

    def __init__(self, position: float, area: float, min_level: float,
                 max_level: float, initial_level: Optional[float] = None,
                 g: float = 9.81):
        """
        Base surge tank initialization

        Args:
            position: Surge tank position along tunnel (m)
            area: Cross-sectional area of surge tank (m²)
            min_level: Minimum allowable water level (m)
            max_level: Maximum allowable water level (m)
            initial_level: Initial water level (m), defaults to (min+max)/2
            g: Gravitational acceleration (m/s²)
        """
        self.position = position
        self.area = area
        self.min_level = min_level
        self.max_level = max_level
        self.initial_level = initial_level if initial_level is not None else (min_level + max_level) / 2.0
        self.g = g

        # Current state
        self.water_level = self.initial_level
        self.water_level_rate = 0.0  # dZ/dt

    @abstractmethod
    def calculate_water_level_derivative(self, Q_tunnel: float, Q_penstock: float) -> float:
        """
        Calculate rate of change of water level

        Mass balance: A * dZ/dt = Q_tunnel - Q_penstock

        Args:
            Q_tunnel: Flow from tunnel/headrace (m³/s)
            Q_penstock: Flow to penstock/turbine (m³/s)

        Returns:
            dZ/dt: Rate of water level change (m/s)
        """
        pass

    @abstractmethod
    def calculate_head_loss(self, Q: float) -> float:
        """
        Calculate head loss through throttle/orifice (if applicable)

        Args:
            Q: Flow rate (m³/s)

        Returns:
            h_loss: Head loss (m)
        """
        pass

    def update_water_level(self, dt: float, Q_tunnel: float, Q_penstock: float):
        """
        Update water level using explicit Euler method

        Args:
            dt: Time step (s)
            Q_tunnel: Tunnel inflow (m³/s)
            Q_penstock: Penstock outflow (m³/s)
        """
        dZ_dt = self.calculate_water_level_derivative(Q_tunnel, Q_penstock)
        self.water_level += dZ_dt * dt
        self.water_level_rate = dZ_dt

        # Enforce limits
        if self.water_level > self.max_level:
            self.water_level = self.max_level
            self.water_level_rate = 0.0
        elif self.water_level < self.min_level:
            self.water_level = self.min_level
            self.water_level_rate = 0.0

    @abstractmethod
    def calculate_surge_period(self, tunnel_length: float, tunnel_area: float) -> float:
        """
        Calculate natural surge period (Thoma formula)

        Args:
            tunnel_length: Length of headrace tunnel (m)
            tunnel_area: Cross-sectional area of tunnel (m²)

        Returns:
            T_surge: Surge period (s)
        """
        pass


class SimpleSurgeTank(SurgeTank):
    """
    Simple (cylindrical) surge tank (圆筒式调压井)

    Characteristics:
    - Constant cross-section
    - No throttle or orifice
    - Direct connection to tunnel

    Natural period (Thoma formula):
    T = 2π * √(L_tunnel * A_tank / (g * A_tunnel))

    where:
    - L_tunnel: tunnel length
    - A_tank: surge tank area
    - A_tunnel: tunnel area
    - g: gravity
    """

    def __init__(self, position: float, diameter: float, min_level: float,
                 max_level: float, initial_level: Optional[float] = None,
                 g: float = 9.81):
        """
        Simple surge tank initialization

        Args:
            position: Position along tunnel (m)
            diameter: Inner diameter of surge tank (m)
            min_level: Minimum water level (m)
            max_level: Maximum water level (m)
            initial_level: Initial water level (m)
            g: Gravitational acceleration (m/s²)
        """
        area = np.pi * (diameter / 2.0) ** 2
        super().__init__(position, area, min_level, max_level, initial_level, g)
        self.diameter = diameter
        self.tank_type = 'Simple'

    def calculate_water_level_derivative(self, Q_tunnel: float, Q_penstock: float) -> float:
        """
        Calculate dZ/dt for simple surge tank

        A * dZ/dt = Q_in - Q_out

        Args:
            Q_tunnel: Inflow from tunnel (m³/s)
            Q_penstock: Outflow to penstock (m³/s)

        Returns:
            dZ/dt (m/s)
        """
        return (Q_tunnel - Q_penstock) / self.area

    def calculate_head_loss(self, Q: float) -> float:
        """Simple surge tank has no throttle, so no head loss"""
        return 0.0

    def calculate_surge_period(self, tunnel_length: float, tunnel_area: float) -> float:
        """
        Calculate natural surge period using Thoma formula

        T = 2π√(L*A_tank/(g*A_tunnel))

        Args:
            tunnel_length: Headrace tunnel length (m)
            tunnel_area: Tunnel cross-section area (m²)

        Returns:
            T: Surge period (s)
        """
        T = 2.0 * np.pi * np.sqrt(tunnel_length * self.area / (self.g * tunnel_area))
        return T

    def __repr__(self):
        return (f"SimpleSurgeTank(pos={self.position}m, D={self.diameter:.1f}m, "
                f"A={self.area:.1f}m², Z={self.water_level:.2f}m, "
                f"range=[{self.min_level:.1f}, {self.max_level:.1f}]m)")


class ThrottledSurgeTank(SurgeTank):
    """
    Throttled surge tank with orifice (阻抗式调压井)

    Characteristics:
    - Orifice/throttle at connection to tunnel
    - Head loss proportional to Q²
    - Better damping of oscillations
    - Smaller required cross-section

    Head loss through orifice:
    Δh = ξ * v² / (2g) = ξ * Q² / (2g * A_orifice²)

    where ξ is the head loss coefficient
    """

    def __init__(self, position: float, diameter: float, min_level: float,
                 max_level: float, orifice_diameter: float,
                 loss_coefficient: float = 2.0, initial_level: Optional[float] = None,
                 g: float = 9.81):
        """
        Throttled surge tank initialization

        Args:
            position: Position along tunnel (m)
            diameter: Surge tank diameter (m)
            min_level: Minimum water level (m)
            max_level: Maximum water level (m)
            orifice_diameter: Diameter of throttle orifice (m)
            loss_coefficient: Head loss coefficient ξ (default 2.0)
            initial_level: Initial water level (m)
            g: Gravitational acceleration (m/s²)
        """
        area = np.pi * (diameter / 2.0) ** 2
        super().__init__(position, area, min_level, max_level, initial_level, g)
        self.diameter = diameter
        self.orifice_diameter = orifice_diameter
        self.orifice_area = np.pi * (orifice_diameter / 2.0) ** 2
        self.loss_coefficient = loss_coefficient
        self.tank_type = 'Throttled'

    def calculate_head_loss(self, Q: float) -> float:
        """
        Calculate head loss through throttle orifice

        Δh = ξ * v² / (2g) = ξ * Q² / (2g * A²)

        Args:
            Q: Flow rate (m³/s)

        Returns:
            h_loss: Head loss (m)
        """
        if abs(Q) < 1e-10:
            return 0.0

        v = Q / self.orifice_area
        h_loss = self.loss_coefficient * (v ** 2) / (2.0 * self.g)

        # Head loss sign follows flow direction
        return h_loss if Q > 0 else -h_loss

    def calculate_water_level_derivative(self, Q_tunnel: float, Q_penstock: float) -> float:
        """
        Calculate dZ/dt for throttled surge tank

        For throttled tank, the flow through orifice depends on head difference

        Args:
            Q_tunnel: Tunnel inflow (m³/s)
            Q_penstock: Penstock outflow (m³/s)

        Returns:
            dZ/dt (m/s)
        """
        # Net flow into tank
        Q_net = Q_tunnel - Q_penstock

        return Q_net / self.area

    def calculate_surge_period(self, tunnel_length: float, tunnel_area: float) -> float:
        """
        Calculate surge period for throttled tank

        Period is longer than simple tank due to damping

        Approximate formula (with throttle effect):
        T ≈ 2π√(L*A_tank/(g*A_tunnel)) * (1 + α)

        where α accounts for throttle damping
        """
        # Base period (same as simple tank)
        T_base = 2.0 * np.pi * np.sqrt(tunnel_length * self.area / (self.g * tunnel_area))

        # Correction factor for throttle (empirical)
        alpha = self.loss_coefficient * self.area / (2.0 * self.orifice_area)
        T = T_base * (1.0 + 0.1 * alpha)  # Approximate correction

        return T

    def __repr__(self):
        return (f"ThrottledSurgeTank(pos={self.position}m, D={self.diameter:.1f}m, "
                f"D_orifice={self.orifice_diameter:.1f}m, ξ={self.loss_coefficient:.1f}, "
                f"Z={self.water_level:.2f}m)")


class DifferentialSurgeTank(SurgeTank):
    """
    Differential surge tank (差动式调压井)

    Characteristics:
    - Upper chamber (smaller diameter)
    - Lower chamber (larger diameter)
    - Connection at intermediate level
    - More stable oscillations
    - Smaller required volume

    Structure:
    - Upper chamber: area A_upper, above connection level
    - Lower chamber: area A_lower, below connection level
    """

    def __init__(self, position: float, upper_diameter: float, lower_diameter: float,
                 connection_level: float, min_level: float, max_level: float,
                 initial_level: Optional[float] = None, g: float = 9.81):
        """
        Differential surge tank initialization

        Args:
            position: Position along tunnel (m)
            upper_diameter: Diameter of upper chamber (m)
            lower_diameter: Diameter of lower chamber (m)
            connection_level: Level where tunnel connects (m)
            min_level: Minimum water level (m)
            max_level: Maximum water level (m)
            initial_level: Initial water level (m)
            g: Gravitational acceleration (m/s²)
        """
        # Use lower chamber area as base area
        area_lower = np.pi * (lower_diameter / 2.0) ** 2
        super().__init__(position, area_lower, min_level, max_level, initial_level, g)

        self.upper_diameter = upper_diameter
        self.lower_diameter = lower_diameter
        self.area_upper = np.pi * (upper_diameter / 2.0) ** 2
        self.area_lower = area_lower
        self.connection_level = connection_level
        self.tank_type = 'Differential'

    def get_effective_area(self, water_level: Optional[float] = None) -> float:
        """
        Get effective cross-sectional area at current water level

        Args:
            water_level: Water level (m), defaults to current level

        Returns:
            A_eff: Effective area (m²)
        """
        Z = water_level if water_level is not None else self.water_level

        if Z > self.connection_level:
            return self.area_upper
        else:
            return self.area_lower

    def calculate_water_level_derivative(self, Q_tunnel: float, Q_penstock: float) -> float:
        """
        Calculate dZ/dt for differential surge tank

        The effective area changes with water level

        Args:
            Q_tunnel: Tunnel inflow (m³/s)
            Q_penstock: Penstock outflow (m³/s)

        Returns:
            dZ/dt (m/s)
        """
        Q_net = Q_tunnel - Q_penstock
        A_eff = self.get_effective_area()

        return Q_net / A_eff

    def calculate_head_loss(self, Q: float) -> float:
        """Differential surge tank typically has no additional throttle"""
        return 0.0

    def calculate_surge_period(self, tunnel_length: float, tunnel_area: float) -> float:
        """
        Calculate surge period for differential tank

        Uses average effective area
        """
        A_avg = (self.area_upper + self.area_lower) / 2.0
        T = 2.0 * np.pi * np.sqrt(tunnel_length * A_avg / (self.g * tunnel_area))
        return T

    def __repr__(self):
        return (f"DifferentialSurgeTank(pos={self.position}m, "
                f"D_upper={self.upper_diameter:.1f}m, D_lower={self.lower_diameter:.1f}m, "
                f"Z_conn={self.connection_level:.1f}m, Z={self.water_level:.2f}m)")


# Utility functions
def calculate_critical_section(tunnel_length: float, tunnel_area: float,
                               head: float, g: float = 9.81) -> float:
    """
    Calculate critical (minimum) surge tank area using Thoma criterion

    A_crit = (L * Q₀) / (2 * g * H₀)

    where:
    - L: tunnel length
    - Q₀: initial flow
    - H₀: initial head
    - g: gravity

    Args:
        tunnel_length: Headrace tunnel length (m)
        tunnel_area: Tunnel cross-section (m²)
        head: Operating head (m)
        g: Gravitational acceleration (m/s²)

    Returns:
        A_crit: Critical surge tank area (m²)
    """
    # Assume typical velocity in tunnel (e.g., 3 m/s)
    v_tunnel = 3.0  # m/s (typical)
    Q0 = v_tunnel * tunnel_area

    A_crit = (tunnel_length * Q0) / (2.0 * g * head)
    return A_crit


def estimate_max_surge_height(tunnel_length: float, tunnel_area: float,
                              tank_area: float, delta_Q: float,
                              g: float = 9.81) -> float:
    """
    Estimate maximum surge height using simplified formula

    Z_max ≈ (L * ΔQ) / (A_tank * √(2 * g))

    Args:
        tunnel_length: Tunnel length (m)
        tunnel_area: Tunnel area (m²)
        tank_area: Surge tank area (m²)
        delta_Q: Flow change (m³/s)
        g: Gravity (m/s²)

    Returns:
        Z_max: Maximum surge height above initial level (m)
    """
    Z_max = (tunnel_length * delta_Q) / (tank_area * np.sqrt(2.0 * g))
    return Z_max


if __name__ == "__main__":
    print("=" * 80)
    print("SURGE TANK MODULE")
    print("=" * 80)

    print("\nExample Surge Tanks:")
    print("-" * 80)

    # Simple surge tank
    simple = SimpleSurgeTank(
        position=5000.0,     # 5 km from intake
        diameter=12.0,       # 12 m diameter
        min_level=450.0,     # Minimum level
        max_level=480.0,     # Maximum level
        initial_level=465.0  # Initial level
    )
    print(f"1. {simple}")

    # Throttled surge tank
    throttled = ThrottledSurgeTank(
        position=5000.0,
        diameter=10.0,       # Smaller diameter due to throttle
        orifice_diameter=4.0,  # 4 m orifice
        min_level=450.0,
        max_level=480.0,
        initial_level=465.0,
        loss_coefficient=2.5
    )
    print(f"2. {throttled}")

    # Differential surge tank
    differential = DifferentialSurgeTank(
        position=5000.0,
        upper_diameter=8.0,   # 8 m upper chamber
        lower_diameter=15.0,  # 15 m lower chamber
        connection_level=465.0,
        min_level=450.0,
        max_level=480.0,
        initial_level=465.0
    )
    print(f"3. {differential}")

    # Calculate surge periods
    print("\nSurge Period Calculations:")
    print("-" * 80)

    tunnel_length = 5000.0  # 5 km
    tunnel_area = 50.0      # 50 m²

    T_simple = simple.calculate_surge_period(tunnel_length, tunnel_area)
    T_throttled = throttled.calculate_surge_period(tunnel_length, tunnel_area)
    T_differential = differential.calculate_surge_period(tunnel_length, tunnel_area)

    print(f"Simple tank:       T = {T_simple:.1f} s ({T_simple/60:.1f} min)")
    print(f"Throttled tank:    T = {T_throttled:.1f} s ({T_throttled/60:.1f} min)")
    print(f"Differential tank: T = {T_differential:.1f} s ({T_differential/60:.1f} min)")

    print("\n" + "=" * 80)
    print("Module loaded successfully!")
    print("=" * 80)
