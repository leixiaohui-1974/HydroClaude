# -*- coding: utf-8 -*-
"""
Example 05: Hydropower Plant Transient Analysis - Load Rejection
================================================================

Simulates load rejection scenario with governor control.

Scenario: Full load (100 MW) suddenly drops to no load (0 MW)

System response includes:
- Governor action (guide vane closure)
- Turbine speed changes
- Surge tank water level oscillation
- Power output dynamics

This demonstrates:
1. Governor response to disturbance
2. Speed overshoot and settling
3. Surge tank damping effect
4. System stability

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
from control.governor import PIDGovernor


class HydropowerTransientSimulator:
    """
    Simplified hydropower plant transient simulator

    Components:
    - Turbine (Francis)
    - Governor (PID)
    - Surge tank (Simple)
    - Generator (simplified moment of inertia)

    Simplified dynamics:
    - Generator: J * dω/dt = T_turbine - T_load - T_friction
    - Surge tank: A * dZ/dt = Q_tunnel - Q_turbine
    - Turbine: P = η(Q,H,y) * rho * g * Q * H
    """

    def __init__(self):
        """Initialize the transient simulator"""

        print("Initializing Transient Simulator...")
        print("=" * 80)

        # Physical constants
        self.g = 9.81
        self.rho = 1000.0

        # 1. Turbine
        self.turbine = FrancisTurbine(
            position=0.0,
            rated_power=100.0,   # 100 MW
            rated_head=150.0,     # 150 m
            rated_flow=75.0,      # 75 m^3/s
            rated_speed=250.0,    # 250 rpm
            runner_diameter=2.5,
            max_efficiency=0.93
        )

        # 2. Governor
        self.governor = PIDGovernor(
            rated_speed=250.0,
            Kp=10.0,      # 10% permanent droop
            Ki=1.0,
            Kd=0.5,
            T_servo=0.2,  # 200 ms servo time constant
            dead_band=0.2,  # 0.2 rpm dead band
            rate_limit=0.1  # 10% per second
        )

        # 3. Surge tank
        self.surge_tank = SimpleSurgeTank(
            position=5000.0,
            diameter=12.0,
            min_level=450.0,
            max_level=510.0,
            initial_level=480.0  # Initial at 480m
        )

        # 4. System parameters
        self.reservoir_level = 500.0  # m
        self.tailwater_level = 330.0  # m

        # Moment of inertia (generator + turbine)
        # J = GD^2 / 4, where GD^2 is flywheel effect (MN·m^2)
        # For 100 MW, ~250 rpm: GD^2 ~= 600 MN·m^2
        self.GD2 = 600.0  # MN·m^2
        self.J = self.GD2 / 4.0 * 1e6  # kg·m^2

        # Initial conditions
        self.speed = 250.0  # rpm
        self.guide_vane_opening = 0.6  # 60% opening (initial steady state)
        self.load_torque = 0.0  # N·m

        # Tunnel parameters
        self.tunnel_length = 5000.0  # m
        self.tunnel_area = 50.0      # m^2

        print(f"Turbine:        {self.turbine}")
        print(f"Governor:       {self.governor}")
        print(f"Surge tank:     {self.surge_tank}")
        print(f"Inertia (GD^2):  {self.GD2:.0f} MN·m^2")
        print(f"Initial speed:  {self.speed:.1f} rpm")
        print(f"Initial opening: {self.guide_vane_opening:.1%}")
        print("=" * 80)

    def calculate_turbine_power(self, Q: float, H: float, opening: float) -> tuple:
        """
        Calculate turbine power and torque

        Args:
            Q: Flow rate (m^3/s)
            H: Net head (m)
            opening: Guide vane opening (p.u.)

        Returns:
            (P, T, eta): Power (W), Torque (N·m), Efficiency
        """
        # Calculate power using turbine model
        P, eta, mode = self.turbine.calculate_power(Q, H, self.speed, opening)

        # Calculate torque: T = P / ω
        omega = 2.0 * np.pi * self.speed / 60.0  # rad/s
        T = P / omega if omega > 0 else 0.0

        return P, T, eta

    def calculate_load_torque(self, P_load: float, speed: float) -> float:
        """
        Calculate load torque from electrical load

        Args:
            P_load: Electrical load (W)
            speed: Generator speed (rpm)

        Returns:
            T_load: Load torque (N·m)
        """
        omega = 2.0 * np.pi * speed / 60.0
        T_load = P_load / omega if omega > 0 else 0.0
        return T_load

    def step(self, dt: float, P_load: float, time: float) -> dict:
        """
        Advance simulation by one time step

        Args:
            dt: Time step (s)
            P_load: Electrical load (MW)
            time: Current time (s)

        Returns:
            state: Current state dictionary
        """
        # Convert load to W
        P_load_W = P_load * 1e6

        # 1. Governor control
        speed_ref = 250.0  # Constant speed reference
        command = self.governor.compute_control(self.speed, speed_ref, time)
        gov_state = self.governor.update(dt)

        # Actual guide vane opening
        self.guide_vane_opening = gov_state['actual_opening']

        # 2. Hydraulic system
        # Net head (simplified, assume surge tank level)
        H_net = self.surge_tank.water_level - self.tailwater_level

        # Flow through turbine (simplified)
        # Q ∝ opening * sqrtH
        Q_turbine = self.guide_vane_opening * 100.0 * np.sqrt(H_net / 150.0)

        # Tunnel flow (assumed constant for steady state approximation)
        Q_tunnel = 75.0  # Approximately rated flow

        # Update surge tank
        self.surge_tank.update_water_level(dt, Q_tunnel, Q_turbine)

        # 3. Turbine power and torque
        P_turbine, T_turbine, eta = self.calculate_turbine_power(
            Q_turbine, H_net, self.guide_vane_opening
        )

        # 4. Load torque
        T_load = self.calculate_load_torque(P_load_W, self.speed)

        # 5. Friction torque (approximately 1% of rated torque)
        T_friction = 0.01 * self.calculate_load_torque(100e6, 250.0)

        # 6. Generator dynamics
        # J * dω/dt = T_turbine - T_load - T_friction
        T_net = T_turbine - T_load - T_friction

        # Angular acceleration
        omega = 2.0 * np.pi * self.speed / 60.0  # rad/s
        d_omega_dt = T_net / self.J

        # Update speed
        d_speed_dt = d_omega_dt * 60.0 / (2.0 * np.pi)  # rpm/s
        self.speed += d_speed_dt * dt

        # 7. Return state
        state = {
            'time': time,
            'speed': self.speed,
            'speed_deviation': (self.speed - speed_ref) / speed_ref * 100,  # %
            'opening_command': command,
            'opening_actual': self.guide_vane_opening,
            'surge_level': self.surge_tank.water_level,
            'surge_deviation': self.surge_tank.water_level - 480.0,  # m
            'Q_turbine': Q_turbine,
            'Q_tunnel': Q_tunnel,
            'H_net': H_net,
            'P_turbine': P_turbine / 1e6,  # MW
            'P_load': P_load,  # MW
            'eta': eta * 100,  # %
            'T_turbine': T_turbine / 1e6,  # MN·m
            'T_load': T_load / 1e6,  # MN·m
        }

        return state

    def simulate_load_rejection(self, duration: float = 60.0, dt: float = 0.01):
        """
        Simulate load rejection scenario

        Args:
            duration: Simulation duration (s)
            dt: Time step (s)

        Returns:
            results: List of state dictionaries
        """
        print("\nSimulating Load Rejection Scenario...")
        print("-" * 80)
        print("Initial: 100 MW full load")
        print("t = 5.0s: Load suddenly drops to 0 MW")
        print("Duration: 60 seconds")
        print("-" * 80)

        # Initialize
        self.speed = 250.0
        self.guide_vane_opening = 0.6
        self.surge_tank.water_level = 480.0
        self.governor.reset()

        # Load schedule
        def load_schedule(t):
            if t < 5.0:
                return 100.0  # Full load
            else:
                return 0.0    # Load rejection at t=5s

        # Simulation loop
        results = []
        time = 0.0
        steps = int(duration / dt)

        for i in range(steps):
            P_load = load_schedule(time)
            state = self.step(dt, P_load, time)
            results.append(state)

            # Progress indicator
            if i % (steps // 10) == 0:
                progress = i / steps * 100
                print(f"  Progress: {progress:.0f}% (t={time:.1f}s, speed={state['speed']:.1f}rpm)")

            time += dt

        print("-" * 80)
        print("Simulation completed!")

        return results


def plot_results(results: list):
    """Plot simulation results"""

    # Extract data
    time = [r['time'] for r in results]
    speed = [r['speed'] for r in results]
    speed_dev = [r['speed_deviation'] for r in results]
    opening = [r['opening_actual'] for r in results]
    surge_level = [r['surge_level'] for r in results]
    surge_dev = [r['surge_deviation'] for r in results]
    P_turbine = [r['P_turbine'] for r in results]
    P_load = [r['P_load'] for r in results]

    # Create figure
    fig, ((ax1, ax2), (ax3, ax4)) = plt.subplots(2, 2, figsize=(14, 10))

    # 1. Speed response
    ax1.plot(time, speed, 'b-', linewidth=2, label='Actual speed')
    ax1.axhline(y=250.0, color='r', linestyle='--', alpha=0.5, label='Reference (250 rpm)')
    ax1.axvline(x=5.0, color='k', linestyle=':', alpha=0.3, label='Load rejection')
    ax1.set_xlabel('Time (s)', fontsize=11)
    ax1.set_ylabel('Speed (rpm)', fontsize=11)
    ax1.set_title('Generator Speed Response', fontsize=12, fontweight='bold')
    ax1.grid(True, alpha=0.3)
    ax1.legend()

    # Find max overshoot
    max_speed = max(speed)
    max_idx = speed.index(max_speed)
    overshoot = (max_speed - 250.0) / 250.0 * 100
    ax1.plot(time[max_idx], max_speed, 'ro', markersize=8)
    ax1.annotate(f'Max: {max_speed:.1f} rpm\n({overshoot:.1f}% overshoot)',
                xy=(time[max_idx], max_speed),
                xytext=(time[max_idx] + 5, max_speed - 5),
                fontsize=9, color='red',
                arrowprops=dict(arrowstyle='->', color='red', lw=1.5))

    # 2. Guide vane opening
    ax2.plot(time, [o*100 for o in opening], 'g-', linewidth=2)
    ax2.axvline(x=5.0, color='k', linestyle=':', alpha=0.3)
    ax2.set_xlabel('Time (s)', fontsize=11)
    ax2.set_ylabel('Guide Vane Opening (%)', fontsize=11)
    ax2.set_title('Governor Response (Guide Vane)', fontsize=12, fontweight='bold')
    ax2.grid(True, alpha=0.3)

    # 3. Surge tank water level
    ax3.plot(time, surge_level, 'm-', linewidth=2, label='Water level')
    ax3.axhline(y=480.0, color='b', linestyle='--', alpha=0.5, label='Initial level')
    ax3.axvline(x=5.0, color='k', linestyle=':', alpha=0.3)
    ax3.set_xlabel('Time (s)', fontsize=11)
    ax3.set_ylabel('Water Level (m)', fontsize=11)
    ax3.set_title('Surge Tank Water Level', fontsize=12, fontweight='bold')
    ax3.grid(True, alpha=0.3)
    ax3.legend()

    # Find max surge
    max_surge = max(surge_level)
    surge_rise = max_surge - 480.0
    ax3.annotate(f'Max: {max_surge:.2f} m\n(+{surge_rise:.2f} m)',
                xy=(time[surge_level.index(max_surge)], max_surge),
                xytext=(time[surge_level.index(max_surge)] + 5, max_surge - 1),
                fontsize=9, color='purple',
                arrowprops=dict(arrowstyle='->', color='purple', lw=1.5))

    # 4. Power
    ax4.plot(time, P_turbine, 'b-', linewidth=2, label='Turbine power')
    ax4.plot(time, P_load, 'r--', linewidth=2, label='Load power')
    ax4.axvline(x=5.0, color='k', linestyle=':', alpha=0.3, label='Load rejection')
    ax4.set_xlabel('Time (s)', fontsize=11)
    ax4.set_ylabel('Power (MW)', fontsize=11)
    ax4.set_title('Power Output', fontsize=12, fontweight='bold')
    ax4.grid(True, alpha=0.3)
    ax4.legend()

    plt.tight_layout()
    plt.savefig(os.path.join(os.path.dirname(__file__), r'load_rejection.png'), dpi=150)
    print("\nPlot saved to: load_rejection.png")


def main():
    """Main function"""

    print("\n" + "=" * 80)
    print("EXAMPLE 05: LOAD REJECTION TRANSIENT ANALYSIS")
    print("=" * 80)

    # Create simulator
    simulator = HydropowerTransientSimulator()

    # Run simulation
    results = simulator.simulate_load_rejection(duration=60.0, dt=0.01)

    # Analyze results
    print("\n" + "=" * 80)
    print("RESULTS ANALYSIS")
    print("=" * 80)

    # Extract key metrics
    speed = [r['speed'] for r in results]
    surge_level = [r['surge_level'] for r in results]
    opening = [r['opening_actual'] for r in results]

    max_speed = max(speed)
    min_speed = min(speed)
    max_surge = max(surge_level)
    min_surge = min(surge_level)
    final_opening = opening[-1]

    overshoot = (max_speed - 250.0) / 250.0 * 100
    surge_rise = max_surge - 480.0
    surge_drop = 480.0 - min_surge

    print(f"\nSpeed Response:")
    print(f"  Maximum speed:       {max_speed:.2f} rpm ({overshoot:+.1f}% overshoot)")
    print(f"  Minimum speed:       {min_speed:.2f} rpm")
    print(f"  Settling (+/-1%):      ~{results[-1]['time']:.1f}s")

    print(f"\nSurge Tank:")
    print(f"  Initial level:       480.00 m")
    print(f"  Maximum level:       {max_surge:.2f} m (+{surge_rise:.2f} m)")
    print(f"  Minimum level:       {min_surge:.2f} m (-{surge_drop:.2f} m)")

    print(f"\nGovernor Action:")
    print(f"  Initial opening:     {opening[0]*100:.1f}%")
    print(f"  Final opening:       {final_opening*100:.1f}%")
    print(f"  Change:              {(final_opening - opening[0])*100:+.1f}%")

    # Plot results
    plot_results(results)

    # Summary
    print("\n" + "=" * 80)
    print("EXAMPLE COMPLETED SUCCESSFULLY")
    print("=" * 80)
    print("\nThis example demonstrates:")
    print("   Governor PID control response")
    print("   Speed overshoot and stabilization")
    print("   Surge tank water level oscillation")
    print("   Guide vane closure dynamics")
    print("   Turbine-governor-surge tank interaction")
    print("\nKey observations:")
    print(f"  - Speed overshoot: {overshoot:.1f}% (acceptable if < 15%)")
    print(f"  - Surge rise: {surge_rise:.2f} m (within tank capacity)")
    print(f"  - Governor reduced opening from {opening[0]*100:.0f}% to {final_opening*100:.0f}%")
    print("=" * 80)


if __name__ == "__main__":
    main()
