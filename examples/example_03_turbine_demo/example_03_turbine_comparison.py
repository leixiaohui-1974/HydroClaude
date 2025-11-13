# -*- coding: utf-8 -*-
"""
Example 03: Hydraulic Turbine Comparison
========================================

Demonstrates and compares three types of hydraulic turbines:
- Francis turbine (medium head: 40-600m)
- Kaplan turbine (low head: 10-70m)
- Pelton turbine (high head: 300-1500m)

This example shows:
1. Operating characteristics at different loads
2. Efficiency curves
3. Power output comparison
4. Part-load performance
5. Specific speed classification

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

from physics.turbine import FrancisTurbine, KaplanTurbine, PeltonTurbine
from physics.turbine import select_turbine_type, calculate_specific_speed


def demo_francis_turbine():
    """Demonstrate Francis turbine characteristics"""

    print("\n" + "=" * 80)
    print("FRANCIS TURBINE DEMONSTRATION")
    print("=" * 80)

    # Create a medium-head Francis turbine (典型中水头水电站)
    francis = FrancisTurbine(
        position=0.0,
        rated_power=100.0,   # 100 MW
        rated_head=150.0,    # 150 m
        rated_flow=80.0,     # 80 m^3/s
        rated_speed=250.0,   # 250 rpm
        runner_diameter=2.5, # 2.5 m
        max_efficiency=0.93
    )

    print(f"\n{francis}")
    print(f"Specific Speed: {francis.specific_speed:.1f} (typical Francis: 60-400)")

    # Test at different loads
    print("\nPerformance at Different Loads:")
    print("-" * 80)
    print(f"{'Load (%)':>10} {'Flow (m^3/s)':>15} {'Power (MW)':>15} {'Efficiency (%)':>15} {'Mode':>12}")
    print("-" * 80)

    loads = [30, 50, 70, 85, 100, 110]
    powers = []
    efficiencies = []

    for load in loads:
        Q = (load / 100.0) * francis.rated_flow
        P, eta, mode = francis.calculate_power(Q, francis.rated_head)
        powers.append(P / 1e6)
        efficiencies.append(eta * 100)

        print(f"{load:>10.0f} {Q:>15.1f} {P/1e6:>15.2f} {eta*100:>15.1f} {mode:>12}")

    return francis, loads, powers, efficiencies


def demo_kaplan_turbine():
    """Demonstrate Kaplan turbine characteristics"""

    print("\n" + "=" * 80)
    print("KAPLAN TURBINE DEMONSTRATION")
    print("=" * 80)

    # Create a low-head Kaplan turbine (典型径流式水电站)
    kaplan = KaplanTurbine(
        position=0.0,
        rated_power=50.0,    # 50 MW
        rated_head=25.0,     # 25 m (low head)
        rated_flow=230.0,    # 230 m^3/s (high flow)
        rated_speed=115.0,   # 115 rpm (lower speed)
        runner_diameter=5.0, # 5 m (larger runner)
        max_efficiency=0.94
    )

    print(f"\n{kaplan}")
    print(f"Specific Speed: {kaplan.specific_speed:.1f} (typical Kaplan: 300-1000)")

    # Test at different loads (Kaplan maintains high efficiency at part load)
    print("\nPerformance at Different Loads (Note excellent part-load efficiency):")
    print("-" * 80)
    print(f"{'Load (%)':>10} {'Flow (m^3/s)':>15} {'Power (MW)':>15} {'Efficiency (%)':>15} {'Mode':>12}")
    print("-" * 80)

    loads = [30, 50, 70, 85, 100, 115]
    powers = []
    efficiencies = []

    for load in loads:
        Q = (load / 100.0) * kaplan.rated_flow
        P, eta, mode = kaplan.calculate_power(Q, kaplan.rated_head)
        powers.append(P / 1e6)
        efficiencies.append(eta * 100)

        print(f"{load:>10.0f} {Q:>15.1f} {P/1e6:>15.2f} {eta*100:>15.1f} {mode:>12}")

    return kaplan, loads, powers, efficiencies


def demo_pelton_turbine():
    """Demonstrate Pelton turbine characteristics"""

    print("\n" + "=" * 80)
    print("PELTON TURBINE DEMONSTRATION")
    print("=" * 80)

    # Create a high-head Pelton turbine (典型高水头山区电站)
    pelton = PeltonTurbine(
        position=0.0,
        rated_power=200.0,   # 200 MW
        rated_head=800.0,    # 800 m (high head)
        rated_flow=28.0,     # 28 m^3/s (low flow)
        rated_speed=500.0,   # 500 rpm (higher speed)
        runner_diameter=2.2, # 2.2 m (optimized for speed ratio)
        num_nozzles=4,       # 4 nozzles
        max_efficiency=0.90
    )

    print(f"\n{pelton}")
    print(f"Specific Speed: {pelton.specific_speed:.1f} (typical Pelton: 10-70)")

    # Jet characteristics
    v_jet = pelton.calculate_jet_velocity(pelton.rated_head)
    u = np.pi * pelton.runner_diameter * pelton.rated_speed / 60.0
    speed_ratio = u / v_jet

    print(f"\nJet Characteristics:")
    print(f"  Jet velocity:      {v_jet:.2f} m/s")
    print(f"  Runner velocity:   {u:.2f} m/s")
    print(f"  Speed ratio (u/v): {speed_ratio:.3f} (optimal ~0.47)")

    # Test at different loads
    print("\nPerformance at Different Loads:")
    print("-" * 80)
    print(f"{'Load (%)':>10} {'Flow (m^3/s)':>15} {'Power (MW)':>15} {'Efficiency (%)':>15} {'Mode':>12}")
    print("-" * 80)

    loads = [30, 50, 70, 85, 100, 105]
    powers = []
    efficiencies = []

    for load in loads:
        Q = (load / 100.0) * pelton.rated_flow
        P, eta, mode = pelton.calculate_power(Q, pelton.rated_head)
        powers.append(P / 1e6)
        efficiencies.append(eta * 100)

        print(f"{load:>10.0f} {Q:>15.1f} {P/1e6:>15.2f} {eta*100:>15.1f} {mode:>12}")

    return pelton, loads, powers, efficiencies


def plot_efficiency_curves(francis_data, kaplan_data, pelton_data):
    """Plot efficiency curves for all three turbines"""

    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(14, 5))

    # Efficiency vs Load
    ax1.plot(francis_data[1], francis_data[3], 'b-o', linewidth=2, label='Francis (150m)', markersize=6)
    ax1.plot(kaplan_data[1], kaplan_data[3], 'g-s', linewidth=2, label='Kaplan (25m)', markersize=6)
    ax1.plot(pelton_data[1], pelton_data[3], 'r-^', linewidth=2, label='Pelton (800m)', markersize=6)

    ax1.set_xlabel('Load (%)', fontsize=11)
    ax1.set_ylabel('Efficiency (%)', fontsize=11)
    ax1.set_title('Turbine Efficiency vs Load', fontsize=12, fontweight='bold')
    ax1.grid(True, alpha=0.3)
    ax1.legend()
    ax1.set_xlim(20, 120)
    ax1.set_ylim(70, 100)

    # Annotate Kaplan's excellent part-load efficiency
    ax1.annotate('Kaplan: Excellent part-load\nefficiency due to\ndouble regulation',
                xy=(50, kaplan_data[3][1]), xytext=(35, 75),
                arrowprops=dict(arrowstyle='->', color='green', lw=1.5),
                fontsize=9, color='green', fontweight='bold')

    # Power vs Load
    ax2.plot(francis_data[1], francis_data[2], 'b-o', linewidth=2, label='Francis (100 MW rated)', markersize=6)
    ax2.plot(kaplan_data[1], kaplan_data[2], 'g-s', linewidth=2, label='Kaplan (50 MW rated)', markersize=6)
    ax2.plot(pelton_data[1], pelton_data[2], 'r-^', linewidth=2, label='Pelton (200 MW rated)', markersize=6)

    ax2.set_xlabel('Load (%)', fontsize=11)
    ax2.set_ylabel('Power Output (MW)', fontsize=11)
    ax2.set_title('Turbine Power Output vs Load', fontsize=12, fontweight='bold')
    ax2.grid(True, alpha=0.3)
    ax2.legend()

    plt.tight_layout()
    plt.savefig('examples/example_03_turbine_demo/turbine_comparison.png', dpi=150)
    print(f"\nEfficiency curves saved to: turbine_comparison.png")


def plot_hill_chart_concept(francis):
    """Plot conceptual Hill chart for Francis turbine"""

    print("\n" + "=" * 80)
    print("HILL CHART ANALYSIS (Francis Turbine)")
    print("=" * 80)

    # Create meshgrid for flow and head ratios
    Q_ratios = np.linspace(0.3, 1.2, 30)
    H_ratios = np.linspace(0.7, 1.3, 30)
    Q_mesh, H_mesh = np.meshgrid(Q_ratios, H_ratios)

    # Calculate efficiency for each combination
    eta_mesh = np.zeros_like(Q_mesh)

    for i in range(len(H_ratios)):
        for j in range(len(Q_ratios)):
            Q = Q_ratios[j] * francis.rated_flow
            H = H_ratios[i] * francis.rated_head
            _, eta, _ = francis.calculate_power(Q, H)
            eta_mesh[i, j] = eta * 100

    # Plot Hill chart
    fig, ax = plt.subplots(figsize=(10, 7))

    # Contour plot
    levels = np.arange(70, 95, 2.5)
    cs = ax.contour(Q_mesh, H_mesh, eta_mesh, levels=levels, linewidths=1.5)
    ax.clabel(cs, inline=True, fontsize=8, fmt='%1.1f%%')

    # Fill contours
    csf = ax.contourf(Q_mesh, H_mesh, eta_mesh, levels=levels, cmap='RdYlGn', alpha=0.6)
    cbar = plt.colorbar(csf, ax=ax, label='Efficiency (%)')

    # Mark rated point
    ax.plot(1.0, 1.0, 'r*', markersize=20, label='Rated Point', markeredgecolor='black', markeredgewidth=1)

    ax.set_xlabel('Flow Ratio (Q/Q_rated)', fontsize=11)
    ax.set_ylabel('Head Ratio (H/H_rated)', fontsize=11)
    ax.set_title('Francis Turbine Hill Chart (Efficiency Map)', fontsize=12, fontweight='bold')
    ax.grid(True, alpha=0.3)
    ax.legend()

    plt.tight_layout()
    plt.savefig('examples/example_03_turbine_demo/hill_chart.png', dpi=150)
    print(f"Hill chart saved to: hill_chart.png")


def turbine_selection_guide():
    """Demonstrate turbine selection based on head"""

    print("\n" + "=" * 80)
    print("TURBINE SELECTION GUIDE")
    print("=" * 80)

    print("\nTurbine Selection by Available Head:")
    print("-" * 80)
    print(f"{'Head Range (m)':>20} {'Recommended Type':>20} {'Specific Speed':>20} {'Typical Efficiency':>20}")
    print("-" * 80)

    head_ranges = [
        (10, 70, 'Kaplan', '300-1000', '90-95%'),
        (40, 300, 'Francis', '60-400', '90-94%'),
        (300, 1500, 'Pelton', '10-70', '85-92%')
    ]

    for h_min, h_max, ttype, ns_range, eff_range in head_ranges:
        print(f"{h_min:>8.0f} - {h_max:<8.0f} {ttype:>20} {ns_range:>20} {eff_range:>20}")

    # Example calculations
    print("\n\nExample Site Evaluation:")
    print("-" * 80)

    sites = [
        ("Site A - Run-of-river", 20, 150, 5000),
        ("Site B - Medium dam", 120, 60, 7200),
        ("Site C - Mountain storage", 650, 25, 16250)
    ]

    print(f"{'Site':>25} {'Head (m)':>12} {'Flow (m^3/s)':>15} {'Power (MW)':>12} {'Type':>15} {'ns':>8}")
    print("-" * 80)

    for site_name, head, flow, power_annual in sites:
        # Calculate power (simplified)
        power_MW = 0.85 * 9.81 * flow * head / 1000  # Assuming 85% efficiency

        # Select turbine type
        ttype = select_turbine_type(head)

        # Calculate speed (estimated based on type)
        if ttype == 'Kaplan':
            speed = 100 + (70 - head) * 2  # Lower speed for lower head
        elif ttype == 'Francis':
            speed = 200 + (300 - head) * 0.5
        else:  # Pelton
            speed = 400 + (head - 300) * 0.1

        # Specific speed
        ns = calculate_specific_speed(power_MW, head, speed)

        print(f"{site_name:>25} {head:>12.0f} {flow:>15.1f} {power_MW:>12.1f} {ttype:>15} {ns:>8.1f}")


def main():
    """Main function"""

    print("\n" + "=" * 80)
    print("EXAMPLE 03: HYDRAULIC TURBINE COMPARISON AND SELECTION")
    print("=" * 80)
    print("\nThis example demonstrates:")
    print("  - Francis, Kaplan, and Pelton turbine characteristics")
    print("  - Efficiency curves at different loads")
    print("  - Part-load performance comparison")
    print("  - Hill chart for Francis turbine")
    print("  - Turbine selection guide")
    print("=" * 80)

    # Run demonstrations
    francis_data = demo_francis_turbine()
    kaplan_data = demo_kaplan_turbine()
    pelton_data = demo_pelton_turbine()

    # Plot comparisons
    plot_efficiency_curves(francis_data, kaplan_data, pelton_data)
    plot_hill_chart_concept(francis_data[0])

    # Selection guide
    turbine_selection_guide()

    # Summary
    print("\n" + "=" * 80)
    print("KEY FINDINGS")
    print("=" * 80)

    print("\n1. EFFICIENCY CHARACTERISTICS:")
    print("   - Francis:  Peak efficiency ~93% at rated point, drops at part-load")
    print("   - Kaplan:   Peak efficiency ~94%, EXCELLENT part-load performance")
    print("   - Pelton:   Peak efficiency ~90%, good over moderate range")

    print("\n2. SPECIFIC SPEED RANGES:")
    print(f"   - Francis:  {francis_data[0].specific_speed:.1f} (typical 60-400)")
    print(f"   - Kaplan:   {kaplan_data[0].specific_speed:.1f} (typical 300-1000)")
    print(f"   - Pelton:   {pelton_data[0].specific_speed:.1f} (typical 10-70)")

    print("\n3. APPLICATION GUIDELINES:")
    print("   - Kaplan:  Low head (10-70m), high flow, run-of-river")
    print("   - Francis: Medium head (40-300m), general purpose")
    print("   - Pelton:  High head (300-1500m), mountain storage")

    print("\n4. PART-LOAD PERFORMANCE:")
    print("   - Kaplan excels at part-load due to double regulation")
    print("   - Francis efficiency drops more significantly at part-load")
    print("   - Pelton maintains reasonable efficiency over moderate range")

    print("\n" + "=" * 80)
    print("EXAMPLE COMPLETED SUCCESSFULLY")
    print("=" * 80)
    print("\nOutput files:")
    print("  - turbine_comparison.png (efficiency and power curves)")
    print("  - hill_chart.png (Francis turbine efficiency map)")
    print("=" * 80)


if __name__ == "__main__":
    main()
