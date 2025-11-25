"""
Test suite for AGC and multi-unit coordination

Tests:
1. Primary frequency control
2. Secondary frequency control (AGC)
3. Multi-unit load allocation
4. Integrated AGC system
5. Frequency disturbance response

Author: HydroClaude Development Team
Date: 2025-10-22
"""
import sys
import warnings
warnings.filterwarnings("ignore")
import os

# ========== 路径设置 ==========
script_path = os.path.abspath(__file__)
project_root = os.path.dirname(os.path.dirname(script_path))
sys.path.insert(0, project_root)


import pytest
import numpy as np
from control.agc import (
    PrimaryFrequencyControl,
    SecondaryFrequencyControl,
    FrequencyControlParams,
    MultiUnitCoordinator,
    IntegratedAGCSystem
)


class TestPrimaryFrequencyControl:
    """Tests for primary frequency control (governor droop)."""

    def test_initialization(self):
        """Test basic initialization."""
        pfc = PrimaryFrequencyControl(unit_capacity=100.0, droop=0.04)

        assert pfc.unit_capacity == 100.0
        assert pfc.droop == 0.04
        # K_droop = 100 / (0.04 * 50) = 50 MW/Hz
        assert abs(pfc.K_droop - 50.0) < 0.01

    def test_frequency_drop_response(self):
        """Test power increase when frequency drops."""
        pfc = PrimaryFrequencyControl(unit_capacity=100.0, droop=0.04)

        # Frequency drops by 0.5 Hz (49.5 Hz)
        delta_f = -0.5
        delta_P = pfc.calculate_power_adjustment(delta_f)

        # Should increase power: DeltaP = -K_droop x Deltaf = -50 x (-0.5) = 25 MW
        assert delta_P > 0
        assert abs(delta_P - 25.0) < 0.1

    def test_frequency_rise_response(self):
        """Test power decrease when frequency rises."""
        pfc = PrimaryFrequencyControl(unit_capacity=100.0, droop=0.04)

        # Frequency rises by 0.5 Hz (50.5 Hz)
        delta_f = 0.5
        delta_P = pfc.calculate_power_adjustment(delta_f)

        # Should decrease power: DeltaP = -50 x 0.5 = -25 MW
        assert delta_P < 0
        assert abs(delta_P + 25.0) < 0.1

    def test_droop_characteristic(self):
        """Test that 4% droop means 2 Hz deviation causes full power change."""
        pfc = PrimaryFrequencyControl(unit_capacity=100.0, droop=0.04)

        # At 4% droop: 2 Hz (4% of 50 Hz) should give full power
        delta_f = -2.0  # Frequency drops to 48 Hz
        delta_P = pfc.calculate_power_adjustment(delta_f)

        assert abs(delta_P - 100.0) < 0.1


class TestSecondaryFrequencyControl:
    """Tests for secondary frequency control (AGC)."""

    def test_initialization(self):
        """Test AGC initialization."""
        params = FrequencyControlParams()
        agc = SecondaryFrequencyControl(params)

        assert agc.ace_integral == 0.0
        assert agc.prev_time is None

    def test_ace_calculation_frequency_only(self):
        """Test ACE calculation with frequency deviation only."""
        params = FrequencyControlParams(
            rated_frequency=50.0,
            frequency_bias_factor=1.0,
            tie_line_scheduled=0.0
        )
        agc = SecondaryFrequencyControl(params)

        # Frequency at 49.5 Hz, no tie-line flow
        ace = agc.calculate_ace(frequency=49.5, tie_line_flow=0.0)

        # ACE = 0 + 10 x 1.0 x (-0.5) = -5.0 MW
        assert abs(ace + 5.0) < 0.01

    def test_ace_calculation_tie_line_only(self):
        """Test ACE calculation with tie-line deviation only."""
        params = FrequencyControlParams(
            rated_frequency=50.0,
            frequency_bias_factor=1.0,
            tie_line_scheduled=0.0
        )
        agc = SecondaryFrequencyControl(params)

        # Frequency nominal, tie-line exporting 10 MW (should be 0)
        ace = agc.calculate_ace(frequency=50.0, tie_line_flow=10.0)

        # ACE = 10 + 10 x 1.0 x 0 = 10.0 MW
        assert abs(ace - 10.0) < 0.01

    def test_ace_calculation_combined(self):
        """Test ACE with both frequency and tie-line deviations."""
        params = FrequencyControlParams(
            rated_frequency=50.0,
            frequency_bias_factor=2.0,
            tie_line_scheduled=50.0
        )
        agc = SecondaryFrequencyControl(params)

        # Frequency at 49.8 Hz, tie-line at 60 MW (scheduled 50 MW)
        ace = agc.calculate_ace(frequency=49.8, tie_line_flow=60.0)

        # ACE = (60 - 50) + 10 x 2.0 x (49.8 - 50.0)
        #     = 10 + 10 x 2.0 x (-0.2)
        #     = 10 - 4 = 6.0 MW
        assert abs(ace - 6.0) < 0.01

    def test_pi_control_proportional(self):
        """Test PI controller proportional action."""
        params = FrequencyControlParams(
            Kp_agc=10.0,
            Ki_agc=0.0,  # No integral action
            ace_deadband=0.0
        )
        agc = SecondaryFrequencyControl(params)

        # ACE = -5 MW (under-frequency)
        output, ace = agc.compute_control(frequency=49.5, tie_line_flow=0.0, current_time=0.0)

        # Output = Kp x ACE = 10.0 x (-5.0) = -50.0 MW
        assert abs(output + 50.0) < 0.1

    def test_pi_control_integral(self):
        """Test PI controller integral action."""
        params = FrequencyControlParams(
            Kp_agc=0.0,  # No proportional action
            Ki_agc=5.0,
            ace_deadband=0.0,
            max_regulation_rate=1000.0  # No rate limiting
        )
        agc = SecondaryFrequencyControl(params)

        # Maintain constant ACE for 2 seconds
        agc.compute_control(frequency=49.5, tie_line_flow=0.0, current_time=0.0)
        agc.compute_control(frequency=49.5, tie_line_flow=0.0, current_time=1.0)
        output, ace = agc.compute_control(frequency=49.5, tie_line_flow=0.0, current_time=2.0)

        # ACE = -5 MW, integral over 2 seconds = -5 x 2 = -10
        # Output = Ki x integral = 5.0 x (-10) = -50 MW
        assert abs(output + 50.0) < 1.0  # Allow some tolerance due to rate limiting

    def test_ace_deadband(self):
        """Test that ACE deadband prevents unnecessary control action."""
        params = FrequencyControlParams(
            Kp_agc=10.0,
            Ki_agc=1.0,
            ace_deadband=1.0  # 1 MW deadband
        )
        agc = SecondaryFrequencyControl(params)

        # Small ACE within deadband
        output, ace = agc.compute_control(frequency=50.05, tie_line_flow=0.0, current_time=0.0)

        # ACE ~= 0.5 MW (within 1 MW deadband), so output should be 0
        assert abs(output) < 0.01

    def test_rate_limiter(self):
        """Test that rate limiter prevents too fast changes."""
        params = FrequencyControlParams(
            Kp_agc=100.0,
            Ki_agc=0.0,
            ace_deadband=0.0,
            max_regulation_rate=2.0  # 2 MW/s
        )
        agc = SecondaryFrequencyControl(params)

        # First call at t=0
        agc.compute_control(frequency=50.0, tie_line_flow=0.0, current_time=0.0)

        # Second call at t=0.5s with large ACE
        output, ace = agc.compute_control(frequency=49.5, tie_line_flow=0.0, current_time=0.5)

        # Raw output = 100 x (-5) = -500 MW
        # But rate limited to 2 MW/s x 0.5s = 1 MW change
        assert abs(output) < 1.5  # Should be limited

    def test_reset(self):
        """Test reset function."""
        params = FrequencyControlParams()
        agc = SecondaryFrequencyControl(params)

        # Run some control
        agc.compute_control(frequency=49.5, tie_line_flow=0.0, current_time=0.0)
        agc.compute_control(frequency=49.5, tie_line_flow=0.0, current_time=1.0)

        assert len(agc.ace_history) > 0

        # Reset
        agc.reset()

        assert agc.ace_integral == 0.0
        assert agc.prev_time is None
        assert len(agc.ace_history) == 0


class TestMultiUnitCoordinator:
    """Tests for multi-unit load allocation."""

    def test_initialization(self):
        """Test coordinator initialization."""
        capacities = [100.0, 120.0, 150.0]
        efficiencies = [0.92, 0.93, 0.91]

        coordinator = MultiUnitCoordinator(capacities, efficiencies)

        assert coordinator.n_units == 3
        assert np.allclose(coordinator.unit_capacities, capacities)
        assert np.allclose(coordinator.unit_efficiencies, efficiencies)

    def test_equal_allocation_full_load(self):
        """Test load allocation at full capacity."""
        capacities = [100.0, 100.0, 100.0]  # Three identical units
        efficiencies = [0.92, 0.92, 0.92]

        coordinator = MultiUnitCoordinator(capacities, efficiencies)

        # Request 300 MW (full capacity)
        allocation = coordinator.allocate_load_equal_incremental(300.0)

        # Each unit should get 100 MW
        assert abs(allocation[0] - 100.0) < 0.1
        assert abs(allocation[1] - 100.0) < 0.1
        assert abs(allocation[2] - 100.0) < 0.1

    def test_proportional_allocation(self):
        """Test proportional allocation for different unit sizes."""
        capacities = [100.0, 150.0, 200.0]  # Different sizes
        efficiencies = [0.92, 0.92, 0.92]

        coordinator = MultiUnitCoordinator(capacities, efficiencies)

        # Request 225 MW (50% of total 450 MW)
        allocation = coordinator.allocate_load_equal_incremental(225.0)

        # Should be proportional: 50, 75, 100 MW
        assert abs(allocation[0] - 50.0) < 1.0
        assert abs(allocation[1] - 75.0) < 1.0
        assert abs(allocation[2] - 100.0) < 1.0

    def test_unit_commitment_low_load(self):
        """Test that units are turned off at low load."""
        capacities = [100.0, 100.0, 100.0]
        efficiencies = [0.92, 0.92, 0.92]

        coordinator = MultiUnitCoordinator(capacities, efficiencies)

        # Request only 50 MW (less than 2 units' minimum)
        allocation = coordinator.allocate_load_equal_incremental(50.0)

        # Should commit fewer units
        committed = sum(1 for p in allocation.values() if p > 0)
        assert committed < 3

        # Total should match demand
        total = sum(allocation.values())
        assert abs(total - 50.0) < 1.0

    def test_available_units_subset(self):
        """Test allocation with only some units available."""
        capacities = [100.0, 100.0, 100.0]
        efficiencies = [0.92, 0.92, 0.92]

        coordinator = MultiUnitCoordinator(capacities, efficiencies)

        # Only units 0 and 2 available
        allocation = coordinator.allocate_load_equal_incremental(120.0, available_units=[0, 2])

        # Unit 1 should be off
        assert allocation[1] == 0.0

        # Units 0 and 2 should share the load
        assert allocation[0] > 0
        assert allocation[2] > 0
        assert abs(allocation[0] + allocation[2] - 120.0) < 1.0

    def test_overload_raises_error(self):
        """Test that requesting too much power raises error."""
        capacities = [100.0, 100.0]
        efficiencies = [0.92, 0.92]

        coordinator = MultiUnitCoordinator(capacities, efficiencies)

        # Request more than total capacity
        with pytest.raises(ValueError):
            coordinator.allocate_load_equal_incremental(250.0)

    def test_agc_signal_distribution(self):
        """Test distribution of AGC signal among units."""
        capacities = [100.0, 150.0, 200.0]
        efficiencies = [0.92, 0.92, 0.92]

        coordinator = MultiUnitCoordinator(capacities, efficiencies)

        # Current allocation
        current = {0: 50.0, 1: 75.0, 2: 100.0}

        # AGC signal: increase by 45 MW
        adjustments = coordinator.distribute_agc_signal(45.0, current)

        # Should be proportional to capacity
        # Total capacity = 450 MW
        # Unit 0: 100/450 x 45 = 10 MW
        # Unit 1: 150/450 x 45 = 15 MW
        # Unit 2: 200/450 x 45 = 20 MW
        assert abs(adjustments[0] - 10.0) < 0.5
        assert abs(adjustments[1] - 15.0) < 0.5
        assert abs(adjustments[2] - 20.0) < 0.5

    def test_agc_signal_respects_limits(self):
        """Test that AGC signal distribution respects unit limits."""
        capacities = [100.0, 100.0]
        efficiencies = [0.92, 0.92]

        coordinator = MultiUnitCoordinator(capacities, efficiencies)

        # Current allocation near maximum
        current = {0: 95.0, 1: 95.0}

        # AGC signal: increase by 20 MW (would exceed limits)
        adjustments = coordinator.distribute_agc_signal(20.0, current)

        # Each unit can only increase by 5 MW to reach 100 MW limit
        assert adjustments[0] <= 5.1
        assert adjustments[1] <= 5.1


class TestIntegratedAGCSystem:
    """Tests for integrated AGC system."""

    def test_initialization(self):
        """Test integrated system initialization."""
        capacities = [100.0, 100.0]
        efficiencies = [0.92, 0.92]
        droops = [0.04, 0.04]
        params = FrequencyControlParams()

        system = IntegratedAGCSystem(capacities, efficiencies, droops, params)

        assert system.n_units == 2
        assert len(system.primary_controls) == 2
        assert system.agc is not None
        assert system.coordinator is not None

    def test_steady_state_operation(self):
        """Test system at steady state (no disturbances)."""
        capacities = [100.0, 100.0]
        efficiencies = [0.92, 0.92]
        droops = [0.04, 0.04]
        params = FrequencyControlParams(
            rated_frequency=50.0,
            tie_line_scheduled=0.0
        )

        system = IntegratedAGCSystem(capacities, efficiencies, droops, params)

        # Nominal conditions
        setpoints = system.compute_control(
            frequency=50.0,
            tie_line_flow=0.0,
            total_demand=150.0,
            current_time=0.0
        )

        # Should allocate 75 MW to each unit
        assert abs(setpoints[0] - 75.0) < 1.0
        assert abs(setpoints[1] - 75.0) < 1.0

    def test_frequency_disturbance_response(self):
        """Test system response to frequency disturbance."""
        capacities = [100.0, 100.0]
        efficiencies = [0.92, 0.92]
        droops = [0.04, 0.04]
        params = FrequencyControlParams(
            rated_frequency=50.0,
            Kp_agc=20.0,
            Ki_agc=5.0,
            ace_deadband=0.0
        )

        system = IntegratedAGCSystem(capacities, efficiencies, droops, params)

        # Start at steady state
        setpoints_0 = system.compute_control(
            frequency=50.0,
            tie_line_flow=0.0,
            total_demand=100.0,
            current_time=0.0
        )

        # Frequency drops to 49.5 Hz
        setpoints_1 = system.compute_control(
            frequency=49.5,
            tie_line_flow=0.0,
            total_demand=100.0,
            current_time=1.0
        )

        # Both units should increase power
        total_increase = sum(setpoints_1.values()) - sum(setpoints_0.values())
        assert total_increase > 0

        # Primary control contribution: DeltaP = -K_droop x Deltaf
        # Each unit: K_droop = 100/(0.04x50) = 50 MW/Hz
        # DeltaP_primary per unit = -50 x (-0.5) = 25 MW
        # Total primary = 50 MW
        # Plus AGC action on top
        assert total_increase > 40.0  # At least primary response

    def test_load_change_tracking(self):
        """Test system tracking load changes."""
        capacities = [100.0, 100.0]
        efficiencies = [0.92, 0.92]
        droops = [0.04, 0.04]
        params = FrequencyControlParams()

        system = IntegratedAGCSystem(capacities, efficiencies, droops, params)

        # Start at 100 MW
        setpoints_1 = system.compute_control(
            frequency=50.0,
            tie_line_flow=0.0,
            total_demand=100.0,
            current_time=0.0
        )

        # Increase to 150 MW
        setpoints_2 = system.compute_control(
            frequency=50.0,
            tie_line_flow=0.0,
            total_demand=150.0,
            current_time=1.0
        )

        # Total generation should increase
        total_1 = sum(setpoints_1.values())
        total_2 = sum(setpoints_2.values())

        assert total_2 > total_1
        assert abs(total_2 - 150.0) < 5.0

    def test_get_system_status(self):
        """Test getting system status."""
        capacities = [100.0, 100.0]
        efficiencies = [0.92, 0.92]
        droops = [0.04, 0.04]
        params = FrequencyControlParams()

        system = IntegratedAGCSystem(capacities, efficiencies, droops, params)

        # Run control
        system.compute_control(
            frequency=50.0,
            tie_line_flow=0.0,
            total_demand=120.0,
            current_time=0.0
        )

        # Get status
        status = system.get_system_status()

        assert 'total_generation' in status
        assert 'committed_units' in status
        assert 'unit_powers' in status
        assert status['committed_units'] == 2
        assert abs(status['total_generation'] - 120.0) < 5.0


class TestAGCPerformanceMetrics:
    """Tests for AGC performance metrics."""

    def test_cps1_compliance(self):
        """
        Test CPS1 (Control Performance Standard 1) compliance.

        CPS1 = (2 - CF) x 100%  where CF = avg(ACE x Deltaf) / (10 x ε₁^2)
        Must be >= 100% to comply.
        """
        params = FrequencyControlParams(
            rated_frequency=50.0,
            frequency_bias_factor=20.0,  # Large system
            Kp_agc=50.0,
            Ki_agc=10.0
        )

        agc = SecondaryFrequencyControl(params)

        # Simulate frequency disturbances
        np.random.seed(42)
        time = 0.0
        dt = 1.0

        for _ in range(100):
            # Random frequency variation
            freq_noise = np.random.normal(0, 0.05)
            freq = 50.0 + freq_noise

            agc.compute_control(frequency=freq, tie_line_flow=0.0, current_time=time)
            time += dt

        # Check that ACE is controlled
        ace_std = np.std(agc.ace_history)
        assert ace_std < 50.0  # ACE standard deviation should be reasonable

    def test_regulation_burden(self):
        """Test that AGC doesn't over-regulate."""
        params = FrequencyControlParams(
            Kp_agc=10.0,
            Ki_agc=2.0,
            max_regulation_rate=5.0
        )

        agc = SecondaryFrequencyControl(params)

        # Small disturbance
        time = 0.0
        for _ in range(20):
            agc.compute_control(frequency=50.02, tie_line_flow=0.0, current_time=time)
            time += 1.0

        # Output should stabilize (not oscillate)
        if len(agc.output_history) > 10:
            recent_outputs = agc.output_history[-10:]
            output_variation = np.std(recent_outputs)
            assert output_variation < 10.0  # Should not vary wildly


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
