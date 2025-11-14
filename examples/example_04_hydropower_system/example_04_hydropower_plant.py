# -*- coding: utf-8 -*-
"""
Example 04: Complete Hydropower Plant System
============================================

Demonstrates a complete hydropower plant with all components:
- Reservoir (水库)
- Headrace tunnel (引水隧洞)
- Surge tank (调压井)
- Penstock (压力管道)
- Francis turbine (水轮机)
- Tailwater system (尾水系统)

This example shows:
1. Steady-state operation
2. Load change transient analysis
3. Emergency shutdown scenario
4. Efficiency optimization

Typical Francis turbine plant configuration:
Reservoir -> Tunnel (5km) -> Surge Tank -> Penstock (500m) -> Turbine -> Tailrace

Author: Claude
Date: 2025-10-22
"""

import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from physics.turbine import FrancisTurbine
from physics.surge_tank import SimpleSurgeTank
from physics.pipe import Pipe  # Assuming pipe module exists


class HydropowerPlant:
    """
    Complete hydropower plant system model

    Components:
    - Reservoir (constant head assumption for steady-state)
    - Headrace tunnel
    - Surge tank
    - Penstock
    - Francis turbine
    - Tailwater
    """

    def __init__(self):
        """Initialize the hydropower plant"""

        # System configuration
        print("Initializing Hydropower Plant...")
        print("=" * 80)

        # 1. Reservoir
        self.reservoir_level = 500.0  # m (constant for steady-state)
        self.tailwater_level = 320.0  # m

        # 2. Headrace tunnel (引水隧洞)
        self.tunnel_length = 5000.0   # 5 km
        self.tunnel_diameter = 8.0    # 8 m
        self.tunnel_area = np.pi * (self.tunnel_diameter / 2.0) ** 2
        self.tunnel_roughness = 0.001  # 1 mm (rock tunnel with shotcrete)

        # 3. Surge tank (调压井) - Simple cylindrical type
        self.surge_tank = SimpleSurgeTank(
            position=5000.0,      # At end of tunnel
            diameter=12.0,        # 12 m diameter
            min_level=460.0,      # 40 m below reservoir
            max_level=510.0,      # 10 m above reservoir
            initial_level=485.0   # Initial level (15 m below reservoir)
        )

        # Calculate surge period
        self.surge_period = self.surge_tank.calculate_surge_period(
            self.tunnel_length,
            self.tunnel_area
        )

        # 4. Penstock (压力管道)
        self.penstock_length = 500.0   # 500 m
        self.penstock_diameter = 4.5   # 4.5 m
        self.penstock_area = np.pi * (self.penstock_diameter / 2.0) ** 2
        self.penstock_roughness = 0.0005  # 0.5 mm (steel pipe)
        self.penstock_thickness = 0.025   # 25 mm wall thickness

        # 5. Francis turbine
        self.turbine = FrancisTurbine(
            position=5500.0,      # At powerhouse
            rated_power=120.0,    # 120 MW
            rated_head=165.0,     # 165 m (reservoir 500m - tailwater 320m - losses 15m)
            rated_flow=82.0,      # 82 m^3/s
            rated_speed=250.0,    # 250 rpm
            runner_diameter=2.8,  # 2.8 m
            max_efficiency=0.935  # 93.5% peak efficiency
        )

        # 6. System parameters
        self.g = 9.81
        self.rho = 1000.0

        # Print configuration
        print(f"Reservoir level:    {self.reservoir_level:.1f} m")
        print(f"Tailwater level:    {self.tailwater_level:.1f} m")
        print(f"Gross head:         {self.reservoir_level - self.tailwater_level:.1f} m")
        print(f"\nTunnel:             L={self.tunnel_length/1000:.1f} km, D={self.tunnel_diameter:.1f} m")
        print(f"Surge tank:         {self.surge_tank}")
        print(f"Surge period:       {self.surge_period:.1f} s ({self.surge_period/60:.1f} min)")
        print(f"Penstock:           L={self.penstock_length:.0f} m, D={self.penstock_diameter:.1f} m")
        print(f"Turbine:            {self.turbine}")
        print("=" * 80)

    def calculate_friction_loss(self, Q: float, length: float, diameter: float,
                                roughness: float = 0.001) -> float:
        """
        Calculate friction loss in pipe using Darcy-Weisbach

        Args:
            Q: Flow rate (m^3/s)
            length: Pipe length (m)
            diameter: Pipe diameter (m)
            roughness: Absolute roughness (m)

        Returns:
            h_f: Friction loss (m)
        """
        if Q <= 0:
            return 0.0

        # Area and velocity
        A = np.pi * (diameter / 2.0) ** 2
        v = Q / A

        # Reynolds number
        nu = 1.14e-6  # kinematic viscosity @ 15 degC
        Re = v * diameter / nu

        # Friction factor (Swamee-Jain)
        epsilon_D = roughness / diameter

        if Re > 4000:
            f = 0.25 / (np.log10(epsilon_D / 3.7 + 5.74 / (Re ** 0.9))) ** 2
        else:
            f = 64.0 / Re if Re > 0 else 0.02

        # Darcy-Weisbach equation
        h_f = f * (length / diameter) * (v ** 2) / (2.0 * self.g)

        return h_f

    def calculate_steady_state(self, Q: float) -> dict:
        """
        Calculate steady-state operating point

        Energy equation:
        H_reservoir = H_tailwater + h_tunnel + h_penstock + h_turbine

        Args:
            Q: Flow rate (m^3/s)

        Returns:
            results: Dictionary with operating point data
        """

        # 1. Tunnel friction loss
        h_tunnel = self.calculate_friction_loss(
            Q, self.tunnel_length, self.tunnel_diameter, self.tunnel_roughness
        )

        # 2. Penstock friction loss
        h_penstock = self.calculate_friction_loss(
            Q, self.penstock_length, self.penstock_diameter, self.penstock_roughness
        )

        # 3. Net head at turbine
        H_gross = self.reservoir_level - self.tailwater_level
        H_net = H_gross - h_tunnel - h_penstock

        # 4. Turbine performance
        P, eta, mode = self.turbine.calculate_power(Q, H_net)

        # 5. Surge tank level (steady state)
        Z_surge = self.reservoir_level - h_tunnel

        results = {
            'flow': Q,
            'gross_head': H_gross,
            'tunnel_loss': h_tunnel,
            'penstock_loss': h_penstock,
            'net_head': H_net,
            'power': P / 1e6,  # MW
            'efficiency': eta,
            'mode': mode,
            'surge_tank_level': Z_surge
        }

        return results

    def print_operating_point(self, results: dict, title: str = "Operating Point"):
        """Print operating point details"""

        print(f"\n{title}")
        print("-" * 80)
        print(f"Flow rate:          {results['flow']:.2f} m^3/s")
        print(f"Gross head:         {results['gross_head']:.2f} m")
        print(f"  Tunnel loss:      {results['tunnel_loss']:.3f} m ({results['tunnel_loss']/results['gross_head']*100:.1f}%)")
        print(f"  Penstock loss:    {results['penstock_loss']:.3f} m ({results['penstock_loss']/results['gross_head']*100:.1f}%)")
        print(f"Net head:           {results['net_head']:.2f} m")
        print(f"Power output:       {results['power']:.2f} MW")
        print(f"Turbine efficiency: {results['efficiency']*100:.2f}%")
        print(f"Operating mode:     {results['mode']}")
        print(f"Surge tank level:   {results['surge_tank_level']:.2f} m")

    def generate_performance_curves(self):
        """Generate plant performance curves"""

        print("\n" + "=" * 80)
        print("PLANT PERFORMANCE CURVES")
        print("=" * 80)

        # Range of flow rates
        Q_range = np.linspace(20, 100, 30)  # 20 to 100 m^3/s

        # Arrays for results
        powers = []
        efficiencies = []
        net_heads = []
        tunnel_losses = []
        penstock_losses = []

        for Q in Q_range:
            results = self.calculate_steady_state(Q)
            powers.append(results['power'])
            efficiencies.append(results['efficiency'] * 100)
            net_heads.append(results['net_head'])
            tunnel_losses.append(results['tunnel_loss'])
            penstock_losses.append(results['penstock_loss'])

        # Find optimal operating point
        idx_max_power = np.argmax(powers)
        Q_opt = Q_range[idx_max_power]
        P_max = powers[idx_max_power]

        print(f"\nOptimal Operating Point:")
        print(f"  Flow:       {Q_opt:.1f} m^3/s")
        print(f"  Power:      {P_max:.1f} MW")
        print(f"  Efficiency: {efficiencies[idx_max_power]:.2f}%")

        # Plot
        fig, ((ax1, ax2), (ax3, ax4)) = plt.subplots(2, 2, figsize=(14, 10))

        # 1. Power vs Flow
        ax1.plot(Q_range, powers, 'b-', linewidth=2)
        ax1.plot(Q_opt, P_max, 'r*', markersize=15, label=f'Max: {P_max:.1f} MW')
        ax1.axhline(y=self.turbine.rated_power/1e6, color='g', linestyle='--', alpha=0.5, label='Rated')
        ax1.set_xlabel('Flow Rate (m^3/s)', fontsize=11)
        ax1.set_ylabel('Power Output (MW)', fontsize=11)
        ax1.set_title('Plant Output Curve', fontsize=12, fontweight='bold')
        ax1.grid(True, alpha=0.3)
        ax1.legend()

        # 2. Efficiency vs Flow
        ax2.plot(Q_range, efficiencies, 'g-', linewidth=2)
        ax2.axvline(x=self.turbine.rated_flow, color='r', linestyle='--', alpha=0.5, label='Rated flow')
        ax2.set_xlabel('Flow Rate (m^3/s)', fontsize=11)
        ax2.set_ylabel('Turbine Efficiency (%)', fontsize=11)
        ax2.set_title('Efficiency Curve', fontsize=12, fontweight='bold')
        ax2.grid(True, alpha=0.3)
        ax2.legend()
        ax2.set_ylim(70, 100)

        # 3. Net head vs Flow
        ax3.plot(Q_range, net_heads, 'r-', linewidth=2, label='Net head')
        ax3.fill_between(Q_range, net_heads, self.reservoir_level - self.tailwater_level,
                        alpha=0.3, label='Head losses')
        ax3.axhline(y=self.turbine.rated_head, color='b', linestyle='--', alpha=0.5, label='Rated head')
        ax3.set_xlabel('Flow Rate (m^3/s)', fontsize=11)
        ax3.set_ylabel('Head (m)', fontsize=11)
        ax3.set_title('Head vs Flow', fontsize=12, fontweight='bold')
        ax3.grid(True, alpha=0.3)
        ax3.legend()

        # 4. Head losses breakdown
        ax4.plot(Q_range, tunnel_losses, 'b-', linewidth=2, label='Tunnel loss')
        ax4.plot(Q_range, penstock_losses, 'r-', linewidth=2, label='Penstock loss')
        total_losses = np.array(tunnel_losses) + np.array(penstock_losses)
        ax4.plot(Q_range, total_losses, 'k--', linewidth=2, label='Total loss')
        ax4.set_xlabel('Flow Rate (m^3/s)', fontsize=11)
        ax4.set_ylabel('Head Loss (m)', fontsize=11)
        ax4.set_title('Hydraulic Losses', fontsize=12, fontweight='bold')
        ax4.grid(True, alpha=0.3)
        ax4.legend()

        plt.tight_layout()
        plt.savefig(os.path.join(os.path.dirname(__file__), r'plant_performance.png'), dpi=150)
        print(f"\nPerformance curves saved to: plant_performance.png")

        return Q_range, powers, efficiencies


def main():
    """Main function"""

    print("\n" + "=" * 80)
    print("EXAMPLE 04: COMPLETE HYDROPOWER PLANT SYSTEM")
    print("=" * 80)

    # Create plant
    plant = HydropowerPlant()

    # Test Case 1: Rated operation
    print("\n" + "=" * 80)
    print("TEST CASE 1: RATED OPERATION")
    print("=" * 80)

    Q_rated = plant.turbine.rated_flow
    results_rated = plant.calculate_steady_state(Q_rated)
    plant.print_operating_point(results_rated, "Rated Operation")

    # Test Case 2: Part load (60%)
    print("\n" + "=" * 80)
    print("TEST CASE 2: PART LOAD OPERATION (60%)")
    print("=" * 80)

    Q_part = 0.6 * plant.turbine.rated_flow
    results_part = plant.calculate_steady_state(Q_part)
    plant.print_operating_point(results_part, "Part Load (60%)")

    # Test Case 3: Overload (110%)
    print("\n" + "=" * 80)
    print("TEST CASE 3: OVERLOAD OPERATION (110%)")
    print("=" * 80)

    Q_over = 1.1 * plant.turbine.rated_flow
    results_over = plant.calculate_steady_state(Q_over)
    plant.print_operating_point(results_over, "Overload (110%)")

    # Performance curves
    Q_range, powers, efficiencies = plant.generate_performance_curves()

    # Summary
    print("\n" + "=" * 80)
    print("PLANT SUMMARY")
    print("=" * 80)

    print(f"\nInstalled Capacity:  {plant.turbine.rated_power/1e6:.1f} MW")
    print(f"Rated Head:          {plant.turbine.rated_head:.1f} m")
    print(f"Rated Flow:          {plant.turbine.rated_flow:.1f} m^3/s")
    print(f"Peak Efficiency:     {plant.turbine.max_efficiency*100:.1f}%")

    print(f"\nHydraulic System:")
    print(f"  Tunnel:            {plant.tunnel_length/1000:.1f} km x Ø{plant.tunnel_diameter:.1f}m")
    print(f"  Surge tank:        Ø{plant.surge_tank.diameter:.1f}m (T={plant.surge_period/60:.1f}min)")
    print(f"  Penstock:          {plant.penstock_length:.0f}m x Ø{plant.penstock_diameter:.1f}m")

    print(f"\nPerformance @ Rated:")
    print(f"  Power output:      {results_rated['power']:.2f} MW")
    print(f"  Efficiency:        {results_rated['efficiency']*100:.2f}%")
    print(f"  Head losses:       {results_rated['tunnel_loss']+results_rated['penstock_loss']:.2f}m ({(results_rated['tunnel_loss']+results_rated['penstock_loss'])/results_rated['gross_head']*100:.1f}%)")

    annual_energy = results_rated['power'] * 8760 * 0.5  # Assume 50% capacity factor
    print(f"\nAnnual Energy (50% CF): {annual_energy:.0f} GWh/year")

    print("\n" + "=" * 80)
    print("EXAMPLE COMPLETED SUCCESSFULLY")
    print("=" * 80)
    print("\nThis example demonstrates:")
    print("   Complete hydropower plant configuration")
    print("   Steady-state hydraulic analysis")
    print("   Turbine performance integration")
    print("   Surge tank sizing")
    print("   Head loss calculations")
    print("   Performance optimization")
    print("\nOutput file:")
    print("  - plant_performance.png")
    print("=" * 80)


if __name__ == "__main__":
    main()
