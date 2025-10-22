# -*- coding: utf-8 -*-
"""
Test cases for Surge Tank and Inverted Siphon

Tests:
- Surge tanks (Simple, Throttled, Differential)
- Inverted siphons
- Integration scenarios

Author: Claude
Date: 2025-10-22
"""

import pytest
import numpy as np
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from physics.surge_tank import SimpleSurgeTank, ThrottledSurgeTank, DifferentialSurgeTank
from physics.surge_tank import calculate_critical_section, estimate_max_surge_height
from physics.inverted_siphon import InvertedSiphon, design_inverted_siphon


class TestSimpleSurgeTank:
    """Test simple surge tank"""

    def test_initialization(self):
        """Test simple surge tank creation"""
        tank = SimpleSurgeTank(
            position=5000.0,
            diameter=12.0,
            min_level=450.0,
            max_level=480.0,
            initial_level=465.0
        )

        assert tank.diameter == 12.0
        assert tank.water_level == 465.0
        assert tank.tank_type == 'Simple'
        print(f"  Simple tank initialized: {tank}")

    def test_water_level_change(self):
        """Test water level derivative calculation"""
        tank = SimpleSurgeTank(
            position=5000.0,
            diameter=12.0,
            min_level=450.0,
            max_level=480.0,
            initial_level=465.0
        )

        # Case 1: Inflow > Outflow (level rises)
        Q_in = 100.0   # m³/s
        Q_out = 80.0   # m³/s

        dZ_dt = tank.calculate_water_level_derivative(Q_in, Q_out)

        assert dZ_dt > 0, "Water level should rise when inflow > outflow"

        # Expected: dZ/dt = (Q_in - Q_out) / A
        A = np.pi * (12.0 / 2.0) ** 2
        expected = (Q_in - Q_out) / A

        assert abs(dZ_dt - expected) / expected < 0.01

        print(f"  Water level rise rate: {dZ_dt:.4f} m/s (Q_in={Q_in}, Q_out={Q_out})")

    def test_surge_period(self):
        """Test surge period calculation"""
        tank = SimpleSurgeTank(
            position=5000.0,
            diameter=12.0,
            min_level=450.0,
            max_level=480.0
        )

        tunnel_length = 5000.0  # m
        tunnel_area = 50.0      # m²

        T = tank.calculate_surge_period(tunnel_length, tunnel_area)

        # Should be in reasonable range (minutes)
        assert 60 < T < 600, f"Surge period should be 1-10 minutes, got {T/60:.1f} min"

        print(f"  Surge period: {T:.1f} s ({T/60:.1f} min)")

    def test_water_level_update(self):
        """Test water level update over time"""
        tank = SimpleSurgeTank(
            position=5000.0,
            diameter=12.0,
            min_level=450.0,
            max_level=480.0,
            initial_level=465.0
        )

        Z_initial = tank.water_level

        # Simulate inflow > outflow for 10 seconds
        dt = 1.0  # Time step
        Q_in = 100.0
        Q_out = 80.0

        for _ in range(10):
            tank.update_water_level(dt, Q_in, Q_out)

        assert tank.water_level > Z_initial, "Water level should increase"
        print(f"  Water level after 10s: {Z_initial:.2f}m → {tank.water_level:.2f}m")


class TestThrottledSurgeTank:
    """Test throttled surge tank"""

    def test_initialization(self):
        """Test throttled surge tank creation"""
        tank = ThrottledSurgeTank(
            position=5000.0,
            diameter=10.0,
            orifice_diameter=4.0,
            min_level=450.0,
            max_level=480.0,
            loss_coefficient=2.5
        )

        assert tank.orifice_diameter == 4.0
        assert tank.loss_coefficient == 2.5
        assert tank.tank_type == 'Throttled'
        print(f"  Throttled tank initialized: {tank}")

    def test_head_loss(self):
        """Test throttle head loss calculation"""
        tank = ThrottledSurgeTank(
            position=5000.0,
            diameter=10.0,
            orifice_diameter=4.0,
            min_level=450.0,
            max_level=480.0,
            loss_coefficient=2.0
        )

        Q = 50.0  # m³/s
        h_loss = tank.calculate_head_loss(Q)

        # Should be positive and reasonable
        assert h_loss > 0, "Head loss should be positive for positive flow"
        assert h_loss < 10.0, "Head loss should be reasonable"

        # Negative flow
        h_loss_neg = tank.calculate_head_loss(-Q)
        assert h_loss_neg < 0, "Head loss should be negative for reverse flow"

        print(f"  Head loss @ Q={Q}m³/s: {h_loss:.3f}m")

    def test_longer_period(self):
        """Test that throttled tank has longer period than simple tank"""
        simple = SimpleSurgeTank(position=5000.0, diameter=10.0,
                                min_level=450.0, max_level=480.0)

        throttled = ThrottledSurgeTank(position=5000.0, diameter=10.0,
                                      orifice_diameter=4.0, min_level=450.0,
                                      max_level=480.0, loss_coefficient=2.5)

        tunnel_length = 5000.0
        tunnel_area = 50.0

        T_simple = simple.calculate_surge_period(tunnel_length, tunnel_area)
        T_throttled = throttled.calculate_surge_period(tunnel_length, tunnel_area)

        assert T_throttled > T_simple, "Throttled tank should have longer period"

        print(f"  Period comparison: Simple={T_simple:.1f}s, Throttled={T_throttled:.1f}s")


class TestDifferentialSurgeTank:
    """Test differential surge tank"""

    def test_initialization(self):
        """Test differential surge tank creation"""
        tank = DifferentialSurgeTank(
            position=5000.0,
            upper_diameter=8.0,
            lower_diameter=15.0,
            connection_level=465.0,
            min_level=450.0,
            max_level=480.0
        )

        assert tank.upper_diameter == 8.0
        assert tank.lower_diameter == 15.0
        assert tank.tank_type == 'Differential'
        print(f"  Differential tank initialized: {tank}")

    def test_effective_area(self):
        """Test effective area changes with water level"""
        tank = DifferentialSurgeTank(
            position=5000.0,
            upper_diameter=8.0,
            lower_diameter=15.0,
            connection_level=465.0,
            min_level=450.0,
            max_level=480.0,
            initial_level=465.0
        )

        # Below connection: use lower area
        A_below = tank.get_effective_area(460.0)
        assert abs(A_below - tank.area_lower) < 1e-6

        # Above connection: use upper area
        A_above = tank.get_effective_area(470.0)
        assert abs(A_above - tank.area_upper) < 1e-6

        print(f"  Effective area: below={A_below:.1f}m², above={A_above:.1f}m²")


class TestInvertedSiphon:
    """Test inverted siphon"""

    def test_initialization(self):
        """Test inverted siphon creation"""
        siphon = InvertedSiphon(
            position=0.0,
            length=150.0,
            diameter=2.0,
            inlet_elevation=100.0,
            throat_elevation=85.0,
            outlet_elevation=100.0,
            num_barrels=2
        )

        assert siphon.diameter == 2.0
        assert siphon.num_barrels == 2
        assert siphon.depth == 15.0
        print(f"  Siphon initialized: {siphon}")

    def test_head_loss_calculation(self):
        """Test head loss calculation"""
        siphon = InvertedSiphon(
            position=0.0,
            length=150.0,
            diameter=2.0,
            inlet_elevation=100.0,
            throat_elevation=85.0,
            outlet_elevation=100.0,
            num_barrels=2
        )

        Q = 20.0  # m³/s
        h_loss, breakdown = siphon.calculate_head_loss(Q)

        # Check components
        assert breakdown['entrance'] > 0
        assert breakdown['friction'] > 0
        assert breakdown['exit'] > 0
        assert abs(breakdown['total'] - h_loss) < 1e-6

        # Total should equal sum
        total_check = breakdown['entrance'] + breakdown['friction'] + breakdown['exit']
        assert abs(total_check - h_loss) / h_loss < 0.01

        print(f"  Head loss @ Q={Q}m³/s: {h_loss:.3f}m")
        print(f"    Entrance: {breakdown['entrance']:.3f}m ({breakdown['entrance']/h_loss*100:.1f}%)")
        print(f"    Friction: {breakdown['friction']:.3f}m ({breakdown['friction']/h_loss*100:.1f}%)")
        print(f"    Exit: {breakdown['exit']:.3f}m ({breakdown['exit']/h_loss*100:.1f}%)")

    def test_discharge_calculation(self):
        """Test discharge calculation"""
        siphon = InvertedSiphon(
            position=0.0,
            length=150.0,
            diameter=2.0,
            inlet_elevation=100.0,
            throat_elevation=85.0,
            outlet_elevation=100.0,
            num_barrels=2
        )

        h_up = 105.0
        h_down = 104.0

        Q, flow_type = siphon.calculate_discharge(h_up, h_down)

        assert Q > 0, "Discharge should be positive"
        assert flow_type in ['low_velocity', 'normal', 'high_velocity', 'no_flow']

        # Verify energy balance
        h_loss, _ = siphon.calculate_head_loss(Q)
        energy_residual = abs((h_up - h_down) - h_loss)

        assert energy_residual < 0.01, f"Energy balance error: {energy_residual:.4f}m"

        print(f"  Discharge: {Q:.2f}m³/s, flow_type={flow_type}")
        print(f"  Energy balance check: {energy_residual:.4e}m (should be ~0)")

    def test_cavitation_check(self):
        """Test cavitation risk assessment"""
        siphon = InvertedSiphon(
            position=0.0,
            length=150.0,
            diameter=2.0,
            inlet_elevation=100.0,
            throat_elevation=85.0,
            outlet_elevation=100.0,
            num_barrels=2
        )

        Q = 20.0
        at_risk, margin = siphon.check_cavitation_risk(Q)

        assert isinstance(at_risk, (bool, np.bool_))
        assert isinstance(margin, (float, np.floating))

        print(f"  Cavitation check @ Q={Q}m³/s: risk={at_risk}, margin={margin/1000:.1f}kPa")

    def test_friction_factor(self):
        """Test friction factor calculation"""
        siphon = InvertedSiphon(
            position=0.0,
            length=150.0,
            diameter=2.0,
            inlet_elevation=100.0,
            throat_elevation=85.0,
            outlet_elevation=100.0,
            num_barrels=2,
            roughness=0.0003
        )

        v = 3.0  # m/s
        f = siphon.calculate_friction_factor(v)

        # Reasonable range for turbulent flow
        assert 0.01 < f < 0.05, f"Friction factor {f} out of reasonable range"

        print(f"  Friction factor @ v={v}m/s: f={f:.4f}")


class TestUtilityFunctions:
    """Test utility functions"""

    def test_critical_section(self):
        """Test critical surge tank area calculation"""
        A_crit = calculate_critical_section(
            tunnel_length=5000.0,
            tunnel_area=50.0,
            head=150.0
        )

        assert A_crit > 0
        print(f"  Critical section area: {A_crit:.2f}m²")

    def test_max_surge_height(self):
        """Test maximum surge height estimation"""
        Z_max = estimate_max_surge_height(
            tunnel_length=5000.0,
            tunnel_area=50.0,
            tank_area=113.1,  # 12m diameter
            delta_Q=20.0
        )

        assert Z_max > 0
        print(f"  Maximum surge height: {Z_max:.2f}m")

    def test_siphon_design(self):
        """Test inverted siphon design function"""
        design = design_inverted_siphon(
            Q_design=50.0,
            width_obstacle=100.0,
            depth_below=20.0,
            max_velocity=2.5,
            num_barrels=3
        )

        assert design['diameter'] > 0
        assert design['num_barrels'] == 3
        assert design['design_velocity'] <= 2.5

        print(f"  Siphon design for Q=50m³/s:")
        print(f"    Diameter: {design['diameter']}m")
        print(f"    Barrels: {design['num_barrels']}")
        print(f"    Velocity: {design['design_velocity']:.2f}m/s")


class TestIntegration:
    """Integration tests"""

    def test_surge_tank_oscillation(self):
        """Test surge tank oscillation simulation"""
        tank = SimpleSurgeTank(
            position=5000.0,
            diameter=12.0,
            min_level=450.0,
            max_level=480.0,
            initial_level=465.0
        )

        # Simulate sudden load rejection
        Q_initial = 100.0
        Q_final = 20.0  # Sudden reduction

        dt = 1.0  # 1 second time step
        duration = 300.0  # 5 minutes

        Z_history = [tank.water_level]
        time_history = [0.0]

        # Simulate
        for t in np.arange(dt, duration, dt):
            Q_in = Q_initial  # Tunnel flow remains constant
            Q_out = Q_final if t > 10 else Q_initial  # Load rejection at t=10s

            tank.update_water_level(dt, Q_in, Q_out)
            Z_history.append(tank.water_level)
            time_history.append(t)

        # Check that water level oscillates
        Z_max = max(Z_history)
        Z_min = min(Z_history)

        assert Z_max > tank.initial_level, "Water level should rise above initial"
        assert Z_min <= tank.initial_level, "Water level should drop below initial (or stay)"

        print(f"  Surge tank oscillation:")
        print(f"    Initial level: {tank.initial_level:.2f}m")
        print(f"    Max level: {Z_max:.2f}m (+{Z_max - tank.initial_level:.2f}m)")
        print(f"    Min level: {Z_min:.2f}m ({Z_min - tank.initial_level:+.2f}m)")


def run_all_tests():
    """Run all tests"""
    print("=" * 80)
    print("SURGE TANK & INVERTED SIPHON TEST SUITE")
    print("=" * 80)

    test_classes = [
        TestSimpleSurgeTank,
        TestThrottledSurgeTank,
        TestDifferentialSurgeTank,
        TestInvertedSiphon,
        TestUtilityFunctions,
        TestIntegration
    ]

    total_tests = 0
    passed_tests = 0

    for test_class in test_classes:
        print(f"\n{test_class.__name__}:")
        print("-" * 60)

        test_instance = test_class()
        test_methods = [method for method in dir(test_instance) if method.startswith('test_')]

        for method_name in test_methods:
            total_tests += 1
            try:
                method = getattr(test_instance, method_name)
                method()
                passed_tests += 1
            except AssertionError as e:
                print(f"  FAILED: {method_name}")
                print(f"    {str(e)}")
            except Exception as e:
                print(f"  ERROR: {method_name}")
                print(f"    {str(e)}")

    print("\n" + "=" * 80)
    print(f"Test Summary: {passed_tests}/{total_tests} tests passed")
    if passed_tests == total_tests:
        print("ALL TESTS PASSED!")
    print("=" * 80)

    return passed_tests == total_tests


if __name__ == "__main__":
    success = run_all_tests()
    sys.exit(0 if success else 1)
