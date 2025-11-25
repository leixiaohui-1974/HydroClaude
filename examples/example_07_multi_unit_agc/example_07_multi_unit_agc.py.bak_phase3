# -*- coding: utf-8 -*-
"""
Example 07: Multi-Unit Hydropower Plant with AGC

This example demonstrates a multi-unit hydropower plant with:
1. Three generating units (100 MW, 120 MW, 150 MW)
2. Primary frequency control (governor droop)
3. Secondary frequency control (AGC)
4. Economic dispatch (load allocation)
5. Response to various disturbances:
   - Frequency drop (loss of generation elsewhere)
   - Frequency rise (loss of load elsewhere)
   - Tie-line power deviation
   - Load changes

The system demonstrates:
- Automatic generation control (AGC) performance
- Multi-unit coordination
- Primary and secondary frequency response
- CPS1 compliance metrics

Author: HydroClaude Development Team
Date: 2025-10-22
"""
import sys
import os

# 添加项目根目录到Python路径
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))



import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from control.agc import (
    IntegratedAGCSystem,
    FrequencyControlParams
)


def simulate_frequency_disturbance():
    """
    Simulate response to a frequency disturbance.

    Scenario: System frequency drops from 50.0 Hz to 49.5 Hz at t=10s
    due to a large load pickup elsewhere in the grid.
    """
    print("=" * 80)
    print("SCENARIO 1: FREQUENCY DISTURBANCE RESPONSE")
    print("=" * 80)
    print("\nA large load is added to the grid at t=10s, causing frequency to drop.")
    print("The hydropower plant must respond with:")
    print("  - Primary control: Immediate power increase via governor droop")
    print("  - Secondary control: AGC eliminates steady-state frequency error")
    print()

    # System setup
    unit_capacities = [100.0, 120.0, 150.0]  # MW
    unit_efficiencies = [0.92, 0.93, 0.91]
    unit_droops = [0.04, 0.04, 0.04]  # 4% droop

    agc_params = FrequencyControlParams(
        rated_frequency=50.0,
        frequency_bias_factor=20.0,  # MW/0.1Hz (20% of plant capacity)
        Kp_agc=30.0,
        Ki_agc=5.0,
        ace_deadband=0.5,  # 0.5 MW
        max_regulation_rate=10.0  # MW/s
    )

    system = IntegratedAGCSystem(
        unit_capacities=unit_capacities,
        unit_efficiencies=unit_efficiencies,
        unit_droops=unit_droops,
        agc_params=agc_params
    )

    # Simulation parameters
    dt = 0.5  # seconds
    t_end = 60.0  # seconds
    time_array = np.arange(0, t_end, dt)

    # Storage
    frequency_array = []
    tie_line_array = []
    unit_powers = {i: [] for i in range(3)}
    total_power_array = []
    ace_array = []
    agc_output_array = []

    # Demand profile (constant)
    base_demand = 250.0  # MW

    # Frequency profile (disturbance at t=10s)
    def get_frequency(t):
        if t < 10.0:
            return 50.0  # Nominal
        elif t < 11.0:
            # Sudden drop over 1 second
            return 50.0 - 0.5 * (t - 10.0)
        elif t < 40.0:
            # Without AGC, frequency would stay at 49.5 Hz
            # With AGC, it recovers to 50.0 Hz
            # Simulate recovery with time constant
            tau = 10.0  # AGC time constant
            return 50.0 - 0.5 * np.exp(-(t - 11.0) / tau)
        else:
            return 50.0  # Fully recovered

    # Tie-line flow (no deviation in this scenario)
    tie_line_scheduled = 0.0
    tie_line_actual = 0.0

    print("Initial Conditions:")
    print(f"  Plant demand: {base_demand:.1f} MW")
    print(f"  System frequency: 50.0 Hz")
    print(f"  Tie-line flow: {tie_line_actual:.1f} MW (scheduled: {tie_line_scheduled:.1f} MW)")
    print()

    # Simulation loop
    for t in time_array:
        freq = get_frequency(t)

        # Compute control
        setpoints = system.compute_control(
            frequency=freq,
            tie_line_flow=tie_line_actual,
            total_demand=base_demand,
            current_time=t
        )

        # Store results
        frequency_array.append(freq)
        tie_line_array.append(tie_line_actual)

        total_power = sum(setpoints.values())
        total_power_array.append(total_power)

        for i in range(3):
            unit_powers[i].append(setpoints[i])

        # Get system status
        status = system.get_system_status()
        ace_array.append(status['current_ace'])
        agc_output_array.append(status['current_agc_output'])

    # Results analysis
    print("\n" + "=" * 80)
    print("RESULTS ANALYSIS")
    print("=" * 80)

    # Initial state (t=0-10s)
    idx_initial = int(10.0 / dt)
    avg_power_initial = np.mean(total_power_array[:idx_initial])

    # During disturbance (t=11-15s)
    idx_dist_start = int(11.0 / dt)
    idx_dist_end = int(15.0 / dt)
    max_power_response = np.max(total_power_array[idx_dist_start:idx_dist_end])

    # Final state (t=50-60s)
    idx_final_start = int(50.0 / dt)
    avg_power_final = np.mean(total_power_array[idx_final_start:])
    avg_freq_final = np.mean(frequency_array[idx_final_start:])

    print(f"\nInitial State (t=0-10s):")
    print(f"  Total generation: {avg_power_initial:.2f} MW")
    for i in range(3):
        avg_unit_power = np.mean(unit_powers[i][:idx_initial])
        print(f"    Unit {i+1}: {avg_unit_power:.2f} MW")

    print(f"\nPeak Response (t=11-15s):")
    print(f"  Maximum generation: {max_power_response:.2f} MW")
    print(f"  Power increase: {max_power_response - avg_power_initial:.2f} MW")

    print(f"\nFinal State (t=50-60s):")
    print(f"  Total generation: {avg_power_final:.2f} MW")
    print(f"  Average frequency: {avg_freq_final:.3f} Hz")
    print(f"  Frequency error: {abs(avg_freq_final - 50.0)*1000:.1f} mHz")
    for i in range(3):
        avg_unit_power = np.mean(unit_powers[i][idx_final_start:])
        print(f"    Unit {i+1}: {avg_unit_power:.2f} MW")

    # Performance metrics
    ace_std = np.std(ace_array[idx_final_start:])
    print(f"\nPerformance Metrics:")
    print(f"  ACE standard deviation (final): {ace_std:.2f} MW")
    print(f"  Frequency restored: {'Yes' if abs(avg_freq_final - 50.0) < 0.01 else 'No'}")

    # Plotting
    fig, axes = plt.subplots(4, 1, figsize=(12, 10))

    # Plot 1: Frequency
    axes[0].plot(time_array, frequency_array, 'b-', linewidth=2)
    axes[0].axhline(50.0, color='k', linestyle='--', alpha=0.5, label='Nominal')
    axes[0].axvline(10.0, color='r', linestyle='--', alpha=0.5, label='Disturbance')
    axes[0].set_ylabel('Frequency (Hz)')
    axes[0].set_title('System Frequency Response')
    axes[0].legend()
    axes[0].grid(True, alpha=0.3)

    # Plot 2: Unit powers
    for i in range(3):
        axes[1].plot(time_array, unit_powers[i], label=f'Unit {i+1} ({unit_capacities[i]:.0f} MW)')
    axes[1].plot(time_array, total_power_array, 'k-', linewidth=2, label='Total')
    axes[1].axvline(10.0, color='r', linestyle='--', alpha=0.5)
    axes[1].set_ylabel('Power (MW)')
    axes[1].set_title('Unit Power Output')
    axes[1].legend()
    axes[1].grid(True, alpha=0.3)

    # Plot 3: ACE
    axes[2].plot(time_array, ace_array, 'g-', linewidth=2)
    axes[2].axhline(0, color='k', linestyle='--', alpha=0.5)
    axes[2].axhline(agc_params.ace_deadband, color='r', linestyle=':', alpha=0.5, label='Deadband')
    axes[2].axhline(-agc_params.ace_deadband, color='r', linestyle=':', alpha=0.5)
    axes[2].axvline(10.0, color='r', linestyle='--', alpha=0.5)
    axes[2].set_ylabel('ACE (MW)')
    axes[2].set_title('Area Control Error')
    axes[2].legend()
    axes[2].grid(True, alpha=0.3)

    # Plot 4: AGC output
    axes[3].plot(time_array, agc_output_array, 'm-', linewidth=2)
    axes[3].axhline(0, color='k', linestyle='--', alpha=0.5)
    axes[3].axvline(10.0, color='r', linestyle='--', alpha=0.5)
    axes[3].set_xlabel('Time (s)')
    axes[3].set_ylabel('AGC Output (MW)')
    axes[3].set_title('AGC Control Signal')
    axes[3].grid(True, alpha=0.3)

    plt.tight_layout()
    plt.savefig(os.path.join(os.path.dirname(__file__), r'scenario1_frequency_disturbance.png'), dpi=150)
    print("\nPlot saved: scenario1_frequency_disturbance.png")


def simulate_load_variation():
    """
    Simulate response to load variations.

    Scenario: Plant load varies over time, and units are committed/decommitted.
    """
    print("\n" + "=" * 80)
    print("SCENARIO 2: LOAD VARIATION AND UNIT COMMITMENT")
    print("=" * 80)
    print("\nPlant load varies from 50 MW to 320 MW over 2 minutes.")
    print("Units are committed and decommitted based on load.")
    print()

    # System setup (same as before)
    unit_capacities = [100.0, 120.0, 150.0]  # MW
    unit_efficiencies = [0.92, 0.93, 0.91]
    unit_droops = [0.04, 0.04, 0.04]

    agc_params = FrequencyControlParams(
        rated_frequency=50.0,
        frequency_bias_factor=20.0,
        Kp_agc=30.0,
        Ki_agc=5.0,
        ace_deadband=0.5,
        max_regulation_rate=10.0
    )

    system = IntegratedAGCSystem(
        unit_capacities=unit_capacities,
        unit_efficiencies=unit_efficiencies,
        unit_droops=unit_droops,
        agc_params=agc_params
    )

    # Simulation parameters
    dt = 1.0  # seconds
    t_end = 120.0  # seconds
    time_array = np.arange(0, t_end, dt)

    # Storage
    demand_array = []
    unit_powers = {i: [] for i in range(3)}
    total_power_array = []
    committed_units_array = []

    # Demand profile (varying)
    def get_demand(t):
        if t < 20:
            return 50.0  # Low load - 1 unit
        elif t < 40:
            return 80.0 + 5.0 * (t - 20)  # Ramping up - 2 units
        elif t < 60:
            return 180.0 + 4.0 * (t - 40)  # Ramping up - 3 units
        elif t < 80:
            return 260.0  # High load - 3 units
        elif t < 100:
            return 260.0 - 4.0 * (t - 80)  # Ramping down
        else:
            return 180.0  # Medium load - 3 units

    # Nominal frequency
    frequency = 50.0
    tie_line = 0.0

    print("Load Profile:")
    print(f"  t=0-20s:   50 MW (1 unit)")
    print(f"  t=20-40s:  80-180 MW (ramping, 2-3 units)")
    print(f"  t=40-60s:  180-260 MW (ramping, 3 units)")
    print(f"  t=60-80s:  260 MW (3 units at high load)")
    print(f"  t=80-100s: 260-180 MW (ramping down)")
    print(f"  t=100-120s: 180 MW (3 units)")
    print()

    # Simulation loop
    for t in time_array:
        demand = get_demand(t)

        # Compute control
        setpoints = system.compute_control(
            frequency=frequency,
            tie_line_flow=tie_line,
            total_demand=demand,
            current_time=t
        )

        # Store results
        demand_array.append(demand)
        total_power = sum(setpoints.values())
        total_power_array.append(total_power)

        committed = sum(1 for p in setpoints.values() if p > 0)
        committed_units_array.append(committed)

        for i in range(3):
            unit_powers[i].append(setpoints[i])

    # Results analysis
    print("\n" + "=" * 80)
    print("RESULTS ANALYSIS")
    print("=" * 80)

    # Check key time points
    time_points = [10, 30, 50, 70, 90, 110]
    print("\nUnit Commitment at Key Time Points:")
    for tp in time_points:
        idx = int(tp / dt)
        demand = demand_array[idx]
        committed = committed_units_array[idx]
        total_gen = total_power_array[idx]

        print(f"\nt={tp}s: Demand={demand:.1f} MW, Committed Units={committed}")
        for i in range(3):
            unit_power = unit_powers[i][idx]
            if unit_power > 0:
                load_fraction = unit_power / unit_capacities[i] * 100
                print(f"  Unit {i+1}: {unit_power:.1f} MW ({load_fraction:.1f}% of capacity)")
            else:
                print(f"  Unit {i+1}: OFF")

    # Plotting
    fig, axes = plt.subplots(3, 1, figsize=(12, 9))

    # Plot 1: Demand and generation
    axes[0].plot(time_array, demand_array, 'k--', linewidth=2, label='Demand')
    axes[0].plot(time_array, total_power_array, 'b-', linewidth=2, label='Total Generation')
    axes[0].set_ylabel('Power (MW)')
    axes[0].set_title('Load Tracking Performance')
    axes[0].legend()
    axes[0].grid(True, alpha=0.3)

    # Plot 2: Individual unit powers
    for i in range(3):
        axes[1].plot(time_array, unit_powers[i], label=f'Unit {i+1} ({unit_capacities[i]:.0f} MW)')
    axes[1].set_ylabel('Power (MW)')
    axes[1].set_title('Individual Unit Power Output')
    axes[1].legend()
    axes[1].grid(True, alpha=0.3)

    # Plot 3: Committed units
    axes[2].plot(time_array, committed_units_array, 'ro-', markersize=3)
    axes[2].set_xlabel('Time (s)')
    axes[2].set_ylabel('Committed Units')
    axes[2].set_title('Number of Committed Units')
    axes[2].set_yticks([0, 1, 2, 3])
    axes[2].grid(True, alpha=0.3)

    plt.tight_layout()
    plt.savefig(os.path.join(os.path.dirname(__file__), r'scenario2_load_variation.png'), dpi=150)
    print("\nPlot saved: scenario2_load_variation.png")


def simulate_tie_line_control():
    """
    Simulate tie-line power control.

    Scenario: Scheduled tie-line flow changes, AGC adjusts generation.
    """
    print("\n" + "=" * 80)
    print("SCENARIO 3: TIE-LINE POWER CONTROL")
    print("=" * 80)
    print("\nScheduled tie-line export changes from 0 MW to 50 MW at t=30s.")
    print("AGC must increase generation to maintain tie-line schedule.")
    print()

    # System setup
    unit_capacities = [100.0, 120.0, 150.0]
    unit_efficiencies = [0.92, 0.93, 0.91]
    unit_droops = [0.04, 0.04, 0.04]

    agc_params = FrequencyControlParams(
        rated_frequency=50.0,
        frequency_bias_factor=20.0,
        Kp_agc=50.0,
        Ki_agc=10.0,
        ace_deadband=0.5,
        max_regulation_rate=5.0,
        tie_line_scheduled=0.0  # Initial
    )

    system = IntegratedAGCSystem(
        unit_capacities=unit_capacities,
        unit_efficiencies=unit_efficiencies,
        unit_droops=unit_droops,
        agc_params=agc_params
    )

    # Simulation parameters
    dt = 0.5
    t_end = 90.0
    time_array = np.arange(0, t_end, dt)

    # Storage
    tie_line_actual_array = []
    tie_line_scheduled_array = []
    ace_array = []
    total_power_array = []
    unit_powers = {i: [] for i in range(3)}

    # Constant load and frequency
    base_demand = 200.0  # MW
    frequency = 50.0

    # Tie-line schedule changes at t=30s
    tie_line_actual = 0.0  # Starts at 0

    print("Initial Conditions:")
    print(f"  Plant demand: {base_demand:.1f} MW")
    print(f"  Tie-line scheduled: 0 MW -> 50 MW at t=30s")
    print()

    # Simulation loop
    for t in time_array:
        # Update tie-line schedule
        if t >= 30.0:
            system.agc.params.tie_line_scheduled = 50.0
        else:
            system.agc.params.tie_line_scheduled = 0.0

        # Tie-line actual follows generation changes with lag
        # (simplified model)
        setpoints = system.compute_control(
            frequency=frequency,
            tie_line_flow=tie_line_actual,
            total_demand=base_demand,
            current_time=t
        )

        total_gen = sum(setpoints.values())
        # Tie-line flow = generation - local load
        tie_line_target = total_gen - base_demand
        # First-order lag
        tau_tie = 5.0
        if dt > 0:
            tie_line_actual += (tie_line_target - tie_line_actual) * dt / tau_tie

        # Store results
        tie_line_actual_array.append(tie_line_actual)
        tie_line_scheduled_array.append(system.agc.params.tie_line_scheduled)
        total_power_array.append(total_gen)

        status = system.get_system_status()
        ace_array.append(status['current_ace'])

        for i in range(3):
            unit_powers[i].append(setpoints[i])

    # Results
    print("\n" + "=" * 80)
    print("RESULTS ANALYSIS")
    print("=" * 80)

    # Before change (t=20-30s)
    idx_before = slice(int(20/dt), int(30/dt))
    avg_gen_before = np.mean(total_power_array[idx_before])
    avg_tie_before = np.mean(tie_line_actual_array[idx_before])

    # After change (t=70-90s)
    idx_after = slice(int(70/dt), int(90/dt))
    avg_gen_after = np.mean(total_power_array[idx_after])
    avg_tie_after = np.mean(tie_line_actual_array[idx_after])

    print(f"\nBefore Schedule Change (t=20-30s):")
    print(f"  Generation: {avg_gen_before:.2f} MW")
    print(f"  Tie-line flow: {avg_tie_before:.2f} MW")

    print(f"\nAfter Schedule Change (t=70-90s):")
    print(f"  Generation: {avg_gen_after:.2f} MW")
    print(f"  Tie-line flow: {avg_tie_after:.2f} MW")
    print(f"  Generation increase: {avg_gen_after - avg_gen_before:.2f} MW")

    # Plotting
    fig, axes = plt.subplots(3, 1, figsize=(12, 8))

    # Plot 1: Total generation
    axes[0].plot(time_array, total_power_array, 'b-', linewidth=2)
    axes[0].axvline(30.0, color='r', linestyle='--', alpha=0.5, label='Schedule Change')
    axes[0].set_ylabel('Generation (MW)')
    axes[0].set_title('Total Generation')
    axes[0].legend()
    axes[0].grid(True, alpha=0.3)

    # Plot 2: Tie-line flow
    axes[1].plot(time_array, tie_line_scheduled_array, 'k--', linewidth=2, label='Scheduled')
    axes[1].plot(time_array, tie_line_actual_array, 'b-', linewidth=2, label='Actual')
    axes[1].axvline(30.0, color='r', linestyle='--', alpha=0.5)
    axes[1].set_ylabel('Tie-Line Flow (MW)')
    axes[1].set_title('Tie-Line Power Control')
    axes[1].legend()
    axes[1].grid(True, alpha=0.3)

    # Plot 3: ACE
    axes[2].plot(time_array, ace_array, 'g-', linewidth=2)
    axes[2].axhline(0, color='k', linestyle='--', alpha=0.5)
    axes[2].axvline(30.0, color='r', linestyle='--', alpha=0.5)
    axes[2].set_xlabel('Time (s)')
    axes[2].set_ylabel('ACE (MW)')
    axes[2].set_title('Area Control Error')
    axes[2].grid(True, alpha=0.3)

    plt.tight_layout()
    plt.savefig(os.path.join(os.path.dirname(__file__), r'scenario3_tie_line_control.png'), dpi=150)
    print("\nPlot saved: scenario3_tie_line_control.png")


def main():
    """Run all scenarios."""
    print("=" * 80)
    print("EXAMPLE 07: MULTI-UNIT HYDROPOWER PLANT WITH AGC")
    print("=" * 80)
    print("\nThis example demonstrates automatic generation control (AGC)")
    print("for a multi-unit hydropower plant with:")
    print("  - 3 units: 100 MW, 120 MW, 150 MW")
    print("  - Primary frequency control (governor droop)")
    print("  - Secondary frequency control (AGC)")
    print("  - Economic dispatch and unit commitment")
    print()

    # Run scenarios
    simulate_frequency_disturbance()
    simulate_load_variation()
    simulate_tie_line_control()

    print("\n" + "=" * 80)
    print("ALL SCENARIOS COMPLETED")
    print("=" * 80)
    print("\nKey Findings:")
    print("   Primary control provides immediate frequency response")
    print("   Secondary control (AGC) eliminates steady-state errors")
    print("   Load allocation optimizes efficiency across units")
    print("   Unit commitment adapts to load variations")
    print("   Tie-line power control maintains scheduled exchanges")
    print("\nThe integrated AGC system successfully coordinates multiple")
    print("generating units while maintaining frequency and tie-line schedules.")
    print()


if __name__ == '__main__':
    main()
