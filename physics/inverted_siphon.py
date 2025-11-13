# -*- coding: utf-8 -*-
"""
Inverted Siphon Models
======================

Implements inverted siphons (倒虹吸) for water conveyance systems.

An inverted siphon is a U-shaped conduit that carries water under pressure
beneath obstacles such as rivers, roads, or valleys.

Structure:
- Inlet section (进口段)
- Throat/barrel section (管身段) - lowest point
- Outlet section (出口段)

Hydraulic considerations:
- Entrance loss
- Friction loss along barrel
- Exit loss
- Possible cavitation at crown
- Minimum velocity for sediment transport

Author: Claude
Date: 2025-10-22
"""

import numpy as np
from typing import Optional, Tuple


class InvertedSiphon:
    """
    Inverted Siphon (倒虹吸)

    A pressurized conduit that passes under an obstacle (river, road, etc.)

    Flow equation (energy balance):
    H_upstream = H_downstream + h_entrance + h_friction + h_exit

    where:
    - h_entrance = K_e * v² / (2g)
    - h_friction = f * L/D * v² / (2g)  (Darcy-Weisbach)
    - h_exit = K_ex * v² / (2g)
    """

    def __init__(self, position: float, length: float, diameter: float,
                 inlet_elevation: float, throat_elevation: float,
                 outlet_elevation: float, num_barrels: int = 1,
                 roughness: float = 0.0003, K_entrance: float = 0.5,
                 K_exit: float = 1.0, g: float = 9.81):
        """
        Initialize inverted siphon

        Args:
            position: Position along alignment (m)
            length: Total length of siphon barrel (m)
            diameter: Internal diameter of each barrel (m)
            inlet_elevation: Invert elevation at inlet (m)
            throat_elevation: Invert elevation at lowest point (m)
            outlet_elevation: Invert elevation at outlet (m)
            num_barrels: Number of parallel barrels (1-4 typical)
            roughness: Absolute roughness (m, default 0.3mm for concrete)
            K_entrance: Entrance loss coefficient (default 0.5)
            K_exit: Exit loss coefficient (default 1.0)
            g: Gravitational acceleration (m/s²)
        """
        self.position = position
        self.length = length
        self.diameter = diameter
        self.inlet_elevation = inlet_elevation
        self.throat_elevation = throat_elevation
        self.outlet_elevation = outlet_elevation
        self.num_barrels = num_barrels
        self.roughness = roughness
        self.K_entrance = K_entrance
        self.K_exit = K_exit
        self.g = g

        # Calculate cross-sectional area
        self.area_single = np.pi * (diameter / 2.0) ** 2
        self.area_total = self.area_single * num_barrels

        # Calculate depth below inlet
        self.depth = inlet_elevation - throat_elevation

    def calculate_friction_factor(self, velocity: float, diameter: Optional[float] = None) -> float:
        """
        Calculate Darcy-Weisbach friction factor using Swamee-Jain equation

        f = 0.25 / [log₁₀(ε/(3.7D) + 5.74/Re^0.9)]²

        Args:
            velocity: Flow velocity (m/s)
            diameter: Pipe diameter (m), defaults to siphon diameter

        Returns:
            f: Darcy-Weisbach friction factor
        """
        if diameter is None:
            diameter = self.diameter

        if velocity < 1e-6:
            return 0.02  # Default value for low velocity

        # Water properties (assume 15°C)
        nu = 1.14e-6  # Kinematic viscosity (m²/s)

        # Reynolds number
        Re = velocity * diameter / nu

        # Relative roughness
        epsilon_D = self.roughness / diameter

        # Swamee-Jain equation (valid for Re > 4000)
        if Re > 4000:
            f = 0.25 / (np.log10(epsilon_D / 3.7 + 5.74 / (Re ** 0.9))) ** 2
        else:
            # Laminar flow (Re < 2000)
            if Re < 2000:
                f = 64.0 / Re
            else:
                # Transition region (interpolate)
                f_lam = 64.0 / 2000
                f_turb = 0.25 / (np.log10(epsilon_D / 3.7 + 5.74 / (4000 ** 0.9))) ** 2
                f = f_lam + (f_turb - f_lam) * (Re - 2000) / 2000

        return f

    def calculate_head_loss(self, Q: float, h_upstream: float = None,
                           h_downstream: float = None) -> Tuple[float, dict]:
        """
        Calculate total head loss through inverted siphon

        h_total = h_entrance + h_friction + h_exit

        Args:
            Q: Flow rate (m³/s)
            h_upstream: Upstream water depth (m), optional
            h_downstream: Downstream water depth (m), optional

        Returns:
            (h_total, breakdown): Total head loss and breakdown dict
        """
        if Q <= 0:
            return 0.0, {'entrance': 0, 'friction': 0, 'exit': 0, 'total': 0}

        # Velocity in barrel
        v = Q / self.area_total

        # 1. Entrance loss
        h_entrance = self.K_entrance * (v ** 2) / (2.0 * self.g)

        # 2. Friction loss (Darcy-Weisbach)
        f = self.calculate_friction_factor(v)
        h_friction = f * (self.length / self.diameter) * (v ** 2) / (2.0 * self.g)

        # 3. Exit loss
        h_exit = self.K_exit * (v ** 2) / (2.0 * self.g)

        # Total loss
        h_total = h_entrance + h_friction + h_exit

        breakdown = {
            'entrance': h_entrance,
            'friction': h_friction,
            'exit': h_exit,
            'total': h_total,
            'velocity': v,
            'friction_factor': f
        }

        return h_total, breakdown

    def calculate_discharge(self, h_upstream: float, h_downstream: float) -> Tuple[float, str]:
        """
        Calculate discharge through siphon given upstream and downstream heads

        Energy equation:
        h_up = h_down + h_loss(Q)

        Solved iteratively for Q

        Args:
            h_upstream: Upstream water level (m)
            h_downstream: Downstream water level (m)

        Returns:
            (Q, flow_type): Discharge (m³/s) and flow type
        """
        # Available head
        delta_h = h_upstream - h_downstream

        if delta_h <= 0:
            return 0.0, 'no_flow'

        # Initial guess using simplified formula (neglect losses)
        # Q ≈ A * √(2 * g * Δh)
        Q_guess = self.area_total * np.sqrt(2.0 * self.g * delta_h)

        # Iterative solution
        Q = Q_guess
        max_iterations = 20
        tolerance = 1e-4

        for iteration in range(max_iterations):
            # Calculate head loss at current Q
            h_loss, _ = self.calculate_head_loss(Q)

            # Residual
            residual = h_upstream - h_downstream - h_loss

            if abs(residual) < tolerance:
                break

            # Update Q using Newton-like iteration
            # Derivative: dh_loss/dQ ≈ 2 * h_loss / Q
            if Q > 1e-6:
                dh_dQ = 2.0 * h_loss / Q
            else:
                dh_dQ = 1.0

            # Newton update
            Q += residual / dh_dQ if dh_dQ > 0 else 0.1 * residual

            # Keep Q positive
            Q = max(0.0, Q)

        # Determine flow type
        v = Q / self.area_total
        if v < 0.6:
            flow_type = 'low_velocity'  # Risk of sedimentation
        elif v > 3.0:
            flow_type = 'high_velocity'  # Risk of cavitation/erosion
        else:
            flow_type = 'normal'

        return Q, flow_type

    def check_cavitation_risk(self, Q: float, atmospheric_pressure: float = 101325.0,
                             vapor_pressure: float = 2340.0) -> Tuple[bool, float]:
        """
        Check cavitation risk at the crown (highest point of barrel)

        Cavitation occurs if pressure drops below vapor pressure

        Args:
            Q: Flow rate (m³/s)
            atmospheric_pressure: Atmospheric pressure (Pa, default 101.325 kPa)
            vapor_pressure: Vapor pressure of water (Pa, default 2.34 kPa @ 20°C)

        Returns:
            (at_risk, pressure_margin): Cavitation risk flag and pressure margin (Pa)
        """
        if Q <= 0:
            return False, 0.0

        # Velocity and velocity head
        v = Q / self.area_total
        v_head = (v ** 2) / (2.0 * self.g)

        # Pressure at throat (lowest point, highest pressure loss)
        # Assume hydrostatic + dynamic pressure
        # P_throat ≈ P_atm + ρ*g*depth - ρ*g*h_loss

        h_loss, _ = self.calculate_head_loss(Q)

        # Pressure head at throat
        rho = 1000.0  # kg/m³
        P_throat = atmospheric_pressure + rho * self.g * self.depth - rho * self.g * h_loss

        # Cavitation margin (should be positive)
        margin = P_throat - vapor_pressure

        at_risk = margin < 0.0

        return at_risk, margin

    def calculate_minimum_velocity(self, sediment_diameter: float = 0.001) -> float:
        """
        Calculate minimum velocity to prevent sedimentation

        Using simplified formula:
        v_min = K * √(d_s)

        where:
        - K ≈ 6-8 for fine sediment
        - d_s: sediment diameter (m)

        Args:
            sediment_diameter: Sediment particle diameter (m, default 1mm)

        Returns:
            v_min: Minimum velocity (m/s)
        """
        K = 7.0  # Typical coefficient
        v_min = K * np.sqrt(sediment_diameter)
        return v_min

    def calculate_derivatives(self, Q: float) -> Tuple[float, float]:
        """
        Calculate analytical derivatives for head loss

        dh/dQ ≈ 2 * h_loss / Q  (simplified)

        Args:
            Q: Flow rate (m³/s)

        Returns:
            (dh_dQ, d2h_dQ2): First and second derivatives
        """
        if Q < 1e-6:
            return 0.0, 0.0

        h_loss, _ = self.calculate_head_loss(Q)

        # First derivative (approximate)
        dh_dQ = 2.0 * h_loss / Q

        # Second derivative (approximate)
        d2h_dQ2 = -2.0 * h_loss / (Q ** 2)

        return dh_dQ, d2h_dQ2

    def __repr__(self):
        return (f"InvertedSiphon(pos={self.position}m, L={self.length}m, "
                f"D={self.diameter}m, barrels={self.num_barrels}, "
                f"depth={self.depth:.1f}m, "
                f"elevations=[{self.inlet_elevation:.1f}, {self.throat_elevation:.1f}, {self.outlet_elevation:.1f}]m)")


# Utility function
def design_inverted_siphon(Q_design: float, width_obstacle: float,
                          depth_below: float, max_velocity: float = 3.0,
                          num_barrels: int = 2) -> dict:
    """
    Preliminary design of inverted siphon

    Args:
        Q_design: Design flow rate (m³/s)
        width_obstacle: Width of obstacle to cross (m)
        depth_below: Required depth below obstacle (m)
        max_velocity: Maximum allowable velocity (m/s)
        num_barrels: Number of barrels

    Returns:
        design: Dictionary with design parameters
    """
    # Required total area
    A_total = Q_design / max_velocity

    # Area per barrel
    A_barrel = A_total / num_barrels

    # Diameter
    D = np.sqrt(4 * A_barrel / np.pi)

    # Round up to standard size
    standard_sizes = [0.5, 0.6, 0.8, 1.0, 1.2, 1.5, 1.8, 2.0, 2.5, 3.0, 3.5, 4.0, 4.5, 5.0]
    D_standard = min([d for d in standard_sizes if d >= D], default=D)

    # Barrel length (assume 1.5x obstacle width for slopes)
    L_barrel = width_obstacle * 1.5

    design = {
        'diameter': D_standard,
        'num_barrels': num_barrels,
        'barrel_length': L_barrel,
        'total_area': num_barrels * np.pi * (D_standard / 2) ** 2,
        'design_velocity': Q_design / (num_barrels * np.pi * (D_standard / 2) ** 2),
        'depth_below': depth_below
    }

    return design


if __name__ == "__main__":
    print("=" * 80)
    print("INVERTED SIPHON MODULE")
    print("=" * 80)

    # Example: River crossing siphon
    print("\nExample: Inverted Siphon for River Crossing")
    print("-" * 80)

    siphon = InvertedSiphon(
        position=0.0,
        length=150.0,          # 150 m barrel length
        diameter=2.0,          # 2 m diameter
        inlet_elevation=100.0, # Inlet at 100 m
        throat_elevation=85.0, # Throat at 85 m (15 m below inlet)
        outlet_elevation=100.0,# Outlet at 100 m
        num_barrels=2,         # 2 barrels
        roughness=0.0003,      # 0.3 mm (concrete)
        K_entrance=0.5,
        K_exit=1.0
    )

    print(f"{siphon}")

    # Calculate discharge
    print("\nHydraulic Analysis:")
    print("-" * 80)

    h_upstream = 105.0  # 5 m depth upstream
    h_downstream = 104.0  # 4 m depth downstream

    Q, flow_type = siphon.calculate_discharge(h_upstream, h_downstream)
    h_loss, breakdown = siphon.calculate_head_loss(Q)

    print(f"Upstream level:    {h_upstream:.2f} m")
    print(f"Downstream level:  {h_downstream:.2f} m")
    print(f"Available head:    {h_upstream - h_downstream:.2f} m")
    print(f"\nDischarge:         {Q:.2f} m³/s")
    print(f"Flow type:         {flow_type}")
    print(f"Velocity:          {breakdown['velocity']:.2f} m/s")
    print(f"\nHead Loss Breakdown:")
    print(f"  Entrance loss:   {breakdown['entrance']:.3f} m ({breakdown['entrance']/h_loss*100:.1f}%)")
    print(f"  Friction loss:   {breakdown['friction']:.3f} m ({breakdown['friction']/h_loss*100:.1f}%)")
    print(f"  Exit loss:       {breakdown['exit']:.3f} m ({breakdown['exit']/h_loss*100:.1f}%)")
    print(f"  Total loss:      {breakdown['total']:.3f} m")

    # Cavitation check
    at_risk, margin = siphon.check_cavitation_risk(Q)
    print(f"\nCavitation Check:")
    print(f"  At risk:         {'YES ️' if at_risk else 'NO '}")
    print(f"  Pressure margin: {margin/1000:.1f} kPa")

    # Minimum velocity check
    v_min = siphon.calculate_minimum_velocity(sediment_diameter=0.001)  # 1mm sediment
    print(f"\nSedimentation Check:")
    print(f"  Current velocity: {breakdown['velocity']:.2f} m/s")
    print(f"  Minimum velocity: {v_min:.2f} m/s (for 1mm sediment)")
    print(f"  Status:           {'OK ' if breakdown['velocity'] > v_min else 'Risk of sedimentation ️'}")

    # Design example
    print("\n" + "=" * 80)
    print("DESIGN EXAMPLE")
    print("=" * 80)

    Q_design = 50.0  # 50 m³/s design flow
    width = 100.0    # 100 m river width
    depth = 20.0     # 20 m depth below riverbed

    design = design_inverted_siphon(Q_design, width, depth, max_velocity=2.5, num_barrels=3)

    print(f"\nDesign Parameters for Q = {Q_design} m³/s:")
    print(f"  Number of barrels:  {design['num_barrels']}")
    print(f"  Diameter per barrel: {design['diameter']:.1f} m")
    print(f"  Total area:         {design['total_area']:.2f} m²")
    print(f"  Design velocity:    {design['design_velocity']:.2f} m/s")
    print(f"  Barrel length:      {design['barrel_length']:.1f} m")
    print(f"  Depth below:        {design['depth_below']:.1f} m")

    print("\n" + "=" * 80)
    print("Module loaded successfully!")
    print("=" * 80)
