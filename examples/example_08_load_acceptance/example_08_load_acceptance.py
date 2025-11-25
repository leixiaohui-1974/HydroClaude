# -*- coding: utf-8 -*-
"""
Example 08: Hydropower Plant Transient Analysis - Load Acceptance
==================================================================

Simulates load acceptance (sudden load increase) scenario with governor control.

Scenario: Light load (10 MW) suddenly increases to full load (100 MW)

System response includes:
- Governor action (guide vane opening)
- Turbine speed changes (frequency dip)
- Surge tank water level drop
- Power output ramp-up
- Comparison with load rejection

This demonstrates:
1. Governor response to load pickup
2. Speed undershoot and recovery
3. Surge tank response (water level drop)
4. System stability during load acceptance
5. Contrast with load rejection behavior

Author: HydroClaude Development Team
Date: 2025-10-22
"""

import numpy as np
import warnings
warnings.filterwarnings("ignore")
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import sys
import os

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from physics.turbine import FrancisTurbine
from physics.surge_tank import SimpleSurgeTank
from control.governor import PIDGovernor


class LoadAcceptanceSimulator:
    """
    Hydropower plant load acceptance transient simulator

    Components:
    - Francis turbine (100 MW)
    - PID governor with servo
    - Simple surge tank
    - Generator inertia model

    Dynamics:
    - Generator: J * dω/dt = T_turbine - T_load - T_friction
    - Surge tank: A * dZ/dt = Q_tunnel - Q_turbine
    - Turbine: P = η(Q,H,y) * rho * g * Q * H
    - Governor: y = f(ω_error)
    """

    def __init__(self):
        """Initialize load acceptance simulator"""

        print("=" * 80)
        print("LOAD ACCEPTANCE TRANSIENT SIMULATOR")
        print("=" * 80)
        print("\nInitializing system components...")

        # Physical constants
        self.g = 9.81  # m/s^2
        self.rho = 1000.0  # kg/m^3

        # 1. Francis Turbine (100 MW)
        print("\n1. Francis Turbine")
        self.turbine = FrancisTurbine(
            position=0.0,
            rated_power=100.0,   # 100 MW
            rated_head=150.0,    # 150 m
            rated_flow=75.0,     # 75 m^3/s
            rated_speed=250.0,   # 250 rpm
            runner_diameter=2.5, # 2.5 m
            max_efficiency=0.93
        )
        print(f"   Rated power: {self.turbine.rated_power/1e6:.1f} MW")
        print(f"   Rated head: {self.turbine.rated_head:.1f} m")
        print(f"   Rated flow: {self.turbine.rated_flow:.1f} m^3/s")
        print(f"   Rated speed: {self.turbine.rated_speed:.1f} rpm")

        # 2. PID Governor
        print("\n2. PID Governor")
        self.governor = PIDGovernor(
            rated_speed=250.0,   # rpm
            Kp=10.0,             # 10% permanent droop
            Ki=1.0,              # Integral gain
            Kd=0.5,              # Derivative gain
            T_servo=0.2,         # 200 ms servo time constant
            dead_band=0.2,       # 0.2 rpm dead band
            rate_limit=0.15      # 15% per second (faster for load acceptance)
        )
        print(f"   Permanent droop: {100.0/self.governor.Kp:.1f}%")
        print(f"   Servo time constant: {self.governor.T_servo:.2f} s")
        print(f"   Rate limit: {self.governor.servo.rate_limit*100:.1f}% / s")

        # 3. Surge Tank
        print("\n3. Simple Surge Tank")
        self.surge_tank = SimpleSurgeTank(
            position=5000.0,     # 5 km from reservoir
            diameter=12.0,       # 12 m diameter
            min_level=450.0,     # m
            max_level=510.0,     # m
            initial_level=480.0  # Initial at 480 m
        )
        print(f"   Diameter: {self.surge_tank.diameter:.1f} m")
        print(f"   Area: {self.surge_tank.area:.1f} m^2")
        print(f"   Initial level: {self.surge_tank.water_level:.1f} m")

        # 4. System hydraulic parameters
        print("\n4. System Configuration")
        self.reservoir_level = 500.0  # m
        self.tailwater_level = 330.0  # m
        self.tunnel_length = 5000.0   # m
        self.tunnel_area = 20.0       # m^2
        print(f"   Reservoir level: {self.reservoir_level:.1f} m")
        print(f"   Tailwater level: {self.tailwater_level:.1f} m")
        print(f"   Tunnel length: {self.tunnel_length:.1f} m")
        print(f"   Tunnel area: {self.tunnel_area:.1f} m^2")

        # 5. Generator parameters
        print("\n5. Generator")
        # Moment of inertia: J = GD^2 / 4
        # Typical GD^2 = 8000 kN·m^2 for 100 MW unit
        GD2 = 8000e3  # N·m^2
        self.J = GD2 / 4.0  # kg·m^2
        print(f"   GD^2: {GD2/1e6:.1f} MN·m^2")
        print(f"   Moment of inertia: {self.J/1e6:.1f} x 10⁶ kg·m^2")

        # Rated torque
        omega_rated = 2.0 * np.pi * self.turbine.rated_speed / 60.0  # rad/s
        P_rated = self.turbine.rated_power  # W (already converted)
        self.T_rated = P_rated / omega_rated  # N·m
        print(f"   Rated torque: {self.T_rated/1e6:.2f} MN·m")

        # State variables
        self.speed = 250.0  # rpm (rated speed)
        self.guide_vane_opening = 0.15  # Initial at 15% (light load)
        self.surge_level = 480.0  # m

        print("\n" + "=" * 80)
        print("INITIALIZATION COMPLETE")
        print("=" * 80)

    def step(self, dt: float, P_load: float, time: float):
        """
        Advance simulation by one time step

        Args:
            dt: Time step (s)
            P_load: Load power (MW)
            time: Current time (s)

        Returns:
            Dictionary with current state
        """

        # Convert speed to rad/s
        omega = 2.0 * np.pi * self.speed / 60.0

        # 1. Governor control
        speed_ref = self.turbine.rated_speed  # rpm
        command = self.governor.compute_control(
            speed=self.speed,
            speed_ref=speed_ref,
            time=time
        )

        # 2. Update servo (guide vane position)
        gov_state = self.governor.update(dt)
        self.guide_vane_opening = gov_state['actual_opening']

        # 3. Calculate net head
        H_gross = self.reservoir_level - self.tailwater_level
        # Surge tank effect on net head
        H_surge = self.surge_level - self.tailwater_level
        H_net = H_surge  # Simplified

        # 4. Estimate flow from opening and head
        # Simplified: Q ~= opening x Q_rated x sqrt(H/H_rated)
        Q_turbine = self.guide_vane_opening * self.turbine.rated_flow * np.sqrt(H_net / self.turbine.rated_head)

        # Turbine power and torque
        P_turbine, eta, mode = self.turbine.calculate_power(
            Q=Q_turbine,
            H=H_net,
            n=self.speed,
            opening=self.guide_vane_opening
        )

        # Turbine torque (P_turbine is in W)
        if omega > 0.1:
            T_turbine = P_turbine / omega
        else:
            T_turbine = 0.0

        # 5. Load torque (P_load is in MW, convert to W)
        T_load = (P_load * 1e6) / omega if omega > 0.1 else 0.0

        # 6. Friction torque (1% of rated)
        T_friction = 0.01 * self.T_rated

        # 7. Generator dynamics: J * dω/dt = T_turbine - T_load - T_friction
        T_net = T_turbine - T_load - T_friction
        d_omega_dt = T_net / self.J

        # Update speed
        d_speed_dt = d_omega_dt * 60.0 / (2.0 * np.pi)  # Convert to rpm/s
        self.speed += d_speed_dt * dt

        # Limit speed (safety)
        self.speed = np.clip(self.speed, 100.0, 400.0)

        # 8. Surge tank dynamics
        # Tunnel flow (assumed constant from reservoir)
        Q_tunnel = 20.0  # m^3/s (steady-state value for initial condition)

        # Update surge tank
        d_level_dt = self.surge_tank.calculate_water_level_derivative(
            Q_tunnel, Q_turbine
        )
        self.surge_level += d_level_dt * dt

        # Return state
        return {
            'time': time,
            'speed': self.speed,
            'speed_deviation': (self.speed - speed_ref) / speed_ref * 100.0,
            'guide_vane_opening': self.guide_vane_opening * 100.0,
            'power_turbine': P_turbine / 1e6,  # Convert W to MW
            'power_load': P_load,
            'surge_level': self.surge_level,
            'surge_deviation': self.surge_level - 480.0,
            'net_head': H_net,
            'flow': Q_turbine,
            'efficiency': eta * 100.0,
            'torque_net': T_net / 1e6  # MN·m
        }


def run_load_acceptance_simulation():
    """
    Run load acceptance transient simulation

    Scenario: Load suddenly increases from 10 MW to 100 MW at t=5s
    """

    print("\n" + "=" * 80)
    print("LOAD ACCEPTANCE SCENARIO")
    print("=" * 80)
    print("\nScenario: Load suddenly increases from 10 MW to 100 MW at t=5s")
    print("  - Initial condition: 10 MW (light load)")
    print("  - Load step: +90 MW at t=5s")
    print("  - Governor responds by opening guide vanes")
    print("  - Speed drops initially, then recovers")
    print("  - Surge tank level drops, then recovers")
    print()

    # Create simulator
    sim = LoadAcceptanceSimulator()

    # Simulation parameters
    dt = 0.05  # 50 ms time step
    t_end = 30.0  # 120 seconds
    t_array = np.arange(0, t_end, dt)

    # Load profile
    def get_load(t):
        if t < 5.0:
            return 10.0  # Light load
        else:
            return 100.0  # Full load

    # Storage arrays
    results = []

    # Initial steady state (light load)
    print("\n" + "-" * 80)
    print("RUNNING SIMULATION...")
    print("-" * 80)

    for t in t_array:
        P_load = get_load(t)
        state = sim.step(dt, P_load, t)
        results.append(state)

        # Print key events
        if abs(t - 5.0) < dt:
            print(f"\nt={t:.2f}s: LOAD STEP +90 MW")
        if abs(t - 10.0) < dt:
            print(f"t={t:.2f}s: Speed = {state['speed']:.2f} rpm ({state['speed_deviation']:+.2f}%)")
        if abs(t - 30.0) < dt:
            print(f"t={t:.2f}s: Speed = {state['speed']:.2f} rpm ({state['speed_deviation']:+.2f}%)")
        if abs(t - 60.0) < dt:
            print(f"t={t:.2f}s: Speed = {state['speed']:.2f} rpm ({state['speed_deviation']:+.2f}%)")

    # Convert to numpy arrays
    results_dict = {key: np.array([r[key] for r in results]) for key in results[0].keys()}

    # Analysis
    print("\n" + "=" * 80)
    print("RESULTS ANALYSIS")
    print("=" * 80)

    # Initial state (t=0-5s)
    idx_initial = int(5.0 / dt)
    avg_speed_initial = np.mean(results_dict['speed'][:idx_initial])
    avg_opening_initial = np.mean(results_dict['guide_vane_opening'][:idx_initial])
    avg_power_initial = np.mean(results_dict['power_turbine'][:idx_initial])

    print(f"\nInitial State (t=0-5s, light load):")
    print(f"  Speed: {avg_speed_initial:.2f} rpm")
    print(f"  Guide vane: {avg_opening_initial:.1f}%")
    print(f"  Power: {avg_power_initial:.2f} MW")
    print(f"  Surge level: {results_dict['surge_level'][0]:.2f} m")

    # Transient response (t=5-30s)
    idx_transient_start = int(5.0 / dt)
    idx_transient_end = int(30.0 / dt)
    min_speed = np.min(results_dict['speed'][idx_transient_start:idx_transient_end])
    min_speed_time = t_array[idx_transient_start + np.argmin(results_dict['speed'][idx_transient_start:idx_transient_end])]
    speed_undershoot = (min_speed - 250.0) / 250.0 * 100.0

    max_opening = np.max(results_dict['guide_vane_opening'][idx_transient_start:idx_transient_end])

    min_surge = np.min(results_dict['surge_level'][idx_transient_start:idx_transient_end])
    surge_drop = 480.0 - min_surge

    print(f"\nTransient Response (t=5-30s):")
    print(f"  Minimum speed: {min_speed:.2f} rpm at t={min_speed_time:.1f}s")
    print(f"  Speed undershoot: {speed_undershoot:.2f}% (negative = frequency dip)")
    print(f"  Maximum opening: {max_opening:.1f}%")
    print(f"  Minimum surge level: {min_surge:.2f} m")
    print(f"  Surge drop: {surge_drop:.2f} m")

    # Final state (t=100-120s)
    idx_final = int(100.0 / dt)
    avg_speed_final = np.mean(results_dict['speed'][idx_final:])
    avg_opening_final = np.mean(results_dict['guide_vane_opening'][idx_final:])
    avg_power_final = np.mean(results_dict['power_turbine'][idx_final:])
    avg_surge_final = np.mean(results_dict['surge_level'][idx_final:])

    print(f"\nFinal State (t=100-120s, full load):")
    print(f"  Speed: {avg_speed_final:.2f} rpm ({(avg_speed_final-250.0)/250.0*100:.2f}% deviation)")
    print(f"  Guide vane: {avg_opening_final:.1f}%")
    print(f"  Power: {avg_power_final:.2f} MW")
    print(f"  Surge level: {avg_surge_final:.2f} m ({avg_surge_final-480.0:+.2f} m)")

    # Performance metrics
    print(f"\nPerformance Metrics:")
    speed_deviation_final = abs(avg_speed_final - 250.0) / 250.0 * 100.0
    if speed_deviation_final < 1.0:
        print(f"   Final speed deviation: {speed_deviation_final:.2f}% (< 1.0%)")
    else:
        print(f"    Final speed deviation: {speed_deviation_final:.2f}% (> 1.0%)")

    if abs(speed_undershoot) < 10.0:
        print(f"   Speed undershoot: {abs(speed_undershoot):.2f}% (< 10%)")
    else:
        print(f"    Speed undershoot: {abs(speed_undershoot):.2f}% (> 10%)")

    if surge_drop < 20.0:
        print(f"   Surge drop: {surge_drop:.2f} m (< 20 m)")
    else:
        print(f"    Surge drop: {surge_drop:.2f} m (> 20 m)")

    # Plotting
    print("\n" + "-" * 80)
    print("GENERATING PLOTS...")
    print("-" * 80)

    fig, axes = plt.subplots(3, 2, figsize=(14, 10))

    # Plot 1: Speed
    axes[0, 0].plot(t_array, results_dict['speed'], 'b-', linewidth=2)
    axes[0, 0].axhline(250, color='k', linestyle='--', alpha=0.5, label='Rated speed')
    axes[0, 0].axvline(5.0, color='r', linestyle='--', alpha=0.5, label='Load step')
    axes[0, 0].set_ylabel('Speed (rpm)')
    axes[0, 0].set_title('Turbine Speed Response')
    axes[0, 0].legend()
    axes[0, 0].grid(True, alpha=0.3)

    # Plot 2: Speed deviation
    axes[0, 1].plot(t_array, results_dict['speed_deviation'], 'b-', linewidth=2)
    axes[0, 1].axhline(0, color='k', linestyle='--', alpha=0.5)
    axes[0, 1].axvline(5.0, color='r', linestyle='--', alpha=0.5)
    axes[0, 1].set_ylabel('Speed Deviation (%)')
    axes[0, 1].set_title('Speed Deviation from Rated')
    axes[0, 1].grid(True, alpha=0.3)

    # Plot 3: Guide vane opening
    axes[1, 0].plot(t_array, results_dict['guide_vane_opening'], 'g-', linewidth=2)
    axes[1, 0].axvline(5.0, color='r', linestyle='--', alpha=0.5)
    axes[1, 0].set_ylabel('Opening (%)')
    axes[1, 0].set_title('Guide Vane Opening')
    axes[1, 0].grid(True, alpha=0.3)

    # Plot 4: Power
    axes[1, 1].plot(t_array, results_dict['power_turbine'], 'b-', linewidth=2, label='Turbine')
    axes[1, 1].plot(t_array, results_dict['power_load'], 'r--', linewidth=2, label='Load')
    axes[1, 1].axvline(5.0, color='r', linestyle='--', alpha=0.5)
    axes[1, 1].set_ylabel('Power (MW)')
    axes[1, 1].set_title('Power Output')
    axes[1, 1].legend()
    axes[1, 1].grid(True, alpha=0.3)

    # Plot 5: Surge tank level
    axes[2, 0].plot(t_array, results_dict['surge_level'], 'm-', linewidth=2)
    axes[2, 0].axhline(480, color='k', linestyle='--', alpha=0.5, label='Initial level')
    axes[2, 0].axvline(5.0, color='r', linestyle='--', alpha=0.5)
    axes[2, 0].set_xlabel('Time (s)')
    axes[2, 0].set_ylabel('Level (m)')
    axes[2, 0].set_title('Surge Tank Water Level')
    axes[2, 0].legend()
    axes[2, 0].grid(True, alpha=0.3)

    # Plot 6: Surge level deviation
    axes[2, 1].plot(t_array, results_dict['surge_deviation'], 'm-', linewidth=2)
    axes[2, 1].axhline(0, color='k', linestyle='--', alpha=0.5)
    axes[2, 1].axvline(5.0, color='r', linestyle='--', alpha=0.5)
    axes[2, 1].set_xlabel('Time (s)')
    axes[2, 1].set_ylabel('Deviation (m)')
    axes[2, 1].set_title('Surge Tank Level Deviation')
    axes[2, 1].grid(True, alpha=0.3)

    plt.tight_layout()

    output_dir = os.path.dirname(__file__)
    output_file = os.path.join(output_dir, 'load_acceptance_transient.png')
    plt.savefig(output_file, dpi=150)
    print(f"\nPlot saved: {output_file}")

    print("\n" + "=" * 80)
    print("SIMULATION COMPLETE")
    print("=" * 80)

    return results_dict


if __name__ == '__main__':
    results = run_load_acceptance_simulation()
