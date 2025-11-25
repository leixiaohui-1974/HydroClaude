# -*- coding: utf-8 -*-
"""
Test cases for Hydraulic Turbines

Tests the three turbine types:
- Francis (medium head)
- Kaplan (low head)
- Pelton (high head)

Author: Claude
Date: 2025-10-22
"""

import pytest
import numpy as np
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from physics.turbine import FrancisTurbine, KaplanTurbine, PeltonTurbine
from physics.turbine import select_turbine_type, calculate_specific_speed


class TestFrancisTurbine:
    """Test Francis turbine"""

    def test_francis_initialization(self):
        """Test Francis turbine creation"""
        turbine = FrancisTurbine(
            position=0.0,
            rated_power=100.0,  # MW
            rated_head=150.0,
            rated_flow=80.0,
            rated_speed=250.0,
            runner_diameter=2.5
        )

        assert turbine.rated_power == 100e6  # Converted to W
        assert turbine.rated_head == 150.0
        assert turbine.rated_flow == 80.0
        assert turbine.turbine_type == 'Francis'
        assert turbine.max_efficiency <= 1.0

        print(f"  Francis initialized: {turbine}")

    def test_francis_rated_power(self):
        """Test Francis turbine at rated conditions"""
        turbine = FrancisTurbine(
            position=0.0,
            rated_power=100.0,
            rated_head=150.0,
            rated_flow=80.0,
            rated_speed=250.0
        )

        # At rated conditions
        P, eta, mode = turbine.calculate_power(
            Q=80.0,
            H=150.0,
            n=250.0,
            opening=1.0
        )

        assert P > 0, "Power should be positive at rated conditions"
        assert eta > 0.85, f"Efficiency should be high at rated point: {eta}"
        assert eta <= turbine.max_efficiency
        assert mode in ['normal', 'part_load', 'overload']

        print(f"  Francis rated: P={P/1e6:.2f} MW, η={eta:.1%}, mode={mode}")

    def test_francis_part_load(self):
        """Test Francis turbine at part load"""
        turbine = FrancisTurbine(
            position=0.0,
            rated_power=100.0,
            rated_head=150.0,
            rated_flow=80.0,
            rated_speed=250.0
        )

        # Part load (50%)
        Q_part = 40.0  # 50% flow

        P_part, eta_part, mode = turbine.calculate_power(
            Q=Q_part,
            H=150.0,
            n=250.0
        )

        # Full load
        P_full, eta_full, _ = turbine.calculate_power(
            Q=80.0,
            H=150.0
        )

        assert P_part > 0
        assert P_part < P_full, "Part load power should be less than full load"
        assert eta_part < eta_full, "Part load efficiency typically lower"

        print(f"  Francis part-load: P={P_part/1e6:.2f} MW, η={eta_part:.1%}")

    def test_francis_derivatives(self):
        """Test Francis analytical derivatives"""
        turbine = FrancisTurbine(
            position=0.0,
            rated_power=100.0,
            rated_head=150.0,
            rated_flow=80.0,
            rated_speed=250.0
        )

        Q = 80.0
        H = 150.0

        # Analytical derivatives
        dP_dQ, dP_dH = turbine.calculate_derivatives(Q, H)

        # Numerical derivatives
        eps = 1e-3
        P0, _, _ = turbine.calculate_power(Q, H)
        P_Q, _, _ = turbine.calculate_power(Q + eps, H)
        P_H, _, _ = turbine.calculate_power(Q, H + eps)

        dP_dQ_num = (P_Q - P0) / eps
        dP_dH_num = (P_H - P0) / eps

        # Check (within 10% for first-order approximation)
        error_Q = abs(dP_dQ - dP_dQ_num) / abs(dP_dQ_num) if dP_dQ_num != 0 else 0
        error_H = abs(dP_dH - dP_dH_num) / abs(dP_dH_num) if dP_dH_num != 0 else 0

        assert error_Q < 0.10, f"dP/dQ error: {error_Q*100:.1f}%"
        assert error_H < 0.10, f"dP/dH error: {error_H*100:.1f}%"

        print(f"  Francis derivatives: error_Q={error_Q*100:.2f}%, error_H={error_H*100:.2f}%")


class TestKaplanTurbine:
    """Test Kaplan turbine"""

    def test_kaplan_initialization(self):
        """Test Kaplan turbine creation"""
        turbine = KaplanTurbine(
            position=0.0,
            rated_power=50.0,
            rated_head=25.0,
            rated_flow=230.0,
            rated_speed=115.0,
            runner_diameter=5.0
        )

        assert turbine.turbine_type == 'Kaplan'
        assert turbine.runner_diameter == 5.0  # Larger than Francis
        print(f"  Kaplan initialized: {turbine}")

    def test_kaplan_rated_power(self):
        """Test Kaplan turbine at rated conditions"""
        turbine = KaplanTurbine(
            position=0.0,
            rated_power=50.0,
            rated_head=25.0,
            rated_flow=230.0,
            rated_speed=115.0
        )

        P, eta, mode = turbine.calculate_power(
            Q=230.0,
            H=25.0,
            n=115.0
        )

        assert P > 0
        assert eta > 0.88, "Kaplan should have high efficiency"
        assert eta <= turbine.max_efficiency

        print(f"  Kaplan rated: P={P/1e6:.2f} MW, η={eta:.1%}, mode={mode}")

    def test_kaplan_part_load_efficiency(self):
        """Test Kaplan's excellent part-load efficiency"""
        turbine = KaplanTurbine(
            position=0.0,
            rated_power=50.0,
            rated_head=25.0,
            rated_flow=230.0,
            rated_speed=115.0
        )

        # Test efficiency at different loads
        loads = [0.3, 0.5, 0.7, 1.0]
        efficiencies = []

        print("  Kaplan part-load efficiency:")
        for load in loads:
            Q = load * 230.0
            P, eta, _ = turbine.calculate_power(Q, 25.0)
            efficiencies.append(eta)
            print(f"    {load*100:3.0f}% load: η = {eta:.1%}")

        # Kaplan should maintain good efficiency at part load
        assert efficiencies[-1] > 0.88  # 100% load
        assert efficiencies[-2] > 0.85  # 70% load (should be still good)

    def test_kaplan_derivatives(self):
        """Test Kaplan analytical derivatives"""
        turbine = KaplanTurbine(
            position=0.0,
            rated_power=50.0,
            rated_head=25.0,
            rated_flow=230.0,
            rated_speed=115.0
        )

        Q = 230.0
        H = 25.0

        dP_dQ, dP_dH = turbine.calculate_derivatives(Q, H)

        # Should be finite
        assert np.isfinite(dP_dQ)
        assert np.isfinite(dP_dH)
        assert dP_dQ > 0
        assert dP_dH > 0

        print(f"  Kaplan derivatives: dP/dQ={dP_dQ:.2e}, dP/dH={dP_dH:.2e}")


class TestPeltonTurbine:
    """Test Pelton turbine"""

    def test_pelton_initialization(self):
        """Test Pelton turbine creation"""
        turbine = PeltonTurbine(
            position=0.0,
            rated_power=200.0,
            rated_head=800.0,
            rated_flow=28.0,
            rated_speed=500.0,
            num_nozzles=4
        )

        assert turbine.turbine_type == 'Pelton'
        assert turbine.num_nozzles == 4
        print(f"  Pelton initialized: {turbine}")

    def test_pelton_jet_velocity(self):
        """Test Pelton jet velocity calculation"""
        turbine = PeltonTurbine(
            position=0.0,
            rated_power=200.0,
            rated_head=800.0,
            rated_flow=28.0,
            rated_speed=500.0
        )

        # Jet velocity: v = Cv * sqrt(2*g*H)
        v_jet = turbine.calculate_jet_velocity(800.0)

        # Theoretical velocity (Cv=0.98)
        v_theo = 0.98 * np.sqrt(2 * 9.81 * 800.0)

        assert abs(v_jet - v_theo) / v_theo < 0.01
        assert v_jet > 100, "Jet velocity should be very high for high head"

        print(f"  Pelton jet velocity: {v_jet:.2f} m/s @ H=800m")

    def test_pelton_rated_power(self):
        """Test Pelton turbine at rated conditions"""
        # Use better matched parameters for optimal efficiency
        turbine = PeltonTurbine(
            position=0.0,
            rated_power=200.0,
            rated_head=800.0,
            rated_flow=28.0,
            rated_speed=500.0,
            runner_diameter=2.2  # Better matched to speed for optimal speed ratio
        )

        P, eta, mode = turbine.calculate_power(
            Q=28.0,
            H=800.0,
            n=500.0
        )

        assert P > 0
        assert eta > 0.70, "Pelton efficiency should be reasonable"
        assert eta <= turbine.max_efficiency

        print(f"  Pelton rated: P={P/1e6:.2f} MW, η={eta:.1%}, mode={mode}")

    def test_pelton_speed_ratio(self):
        """Test Pelton optimal speed ratio"""
        # Use properly matched runner diameter for optimal speed ratio
        turbine = PeltonTurbine(
            position=0.0,
            rated_power=200.0,
            rated_head=800.0,
            rated_flow=28.0,
            rated_speed=500.0,
            runner_diameter=2.2  # Properly sized for optimal speed ratio
        )

        # Runner peripheral velocity
        u = np.pi * turbine.runner_diameter * 500.0 / 60.0

        # Jet velocity
        v_jet = turbine.calculate_jet_velocity(800.0)

        # Speed ratio
        speed_ratio = u / v_jet

        # Optimal is around 0.46-0.48
        print(f"  Pelton speed ratio: {speed_ratio:.3f} (optimal ~0.47)")
        assert 0.4 < speed_ratio < 0.55, "Speed ratio should be near optimal"

    def test_pelton_derivatives(self):
        """Test Pelton analytical derivatives"""
        turbine = PeltonTurbine(
            position=0.0,
            rated_power=200.0,
            rated_head=800.0,
            rated_flow=28.0,
            rated_speed=500.0
        )

        Q = 28.0
        H = 800.0

        dP_dQ, dP_dH = turbine.calculate_derivatives(Q, H)

        assert np.isfinite(dP_dQ)
        assert np.isfinite(dP_dH)
        assert dP_dQ > 0
        assert dP_dH > 0

        print(f"  Pelton derivatives: dP/dQ={dP_dQ:.2e}, dP/dH={dP_dH:.2e}")


class TestUtilityFunctions:
    """Test utility functions"""

    def test_turbine_selection(self):
        """Test turbine type selection by head"""
        print("\n  Turbine selection by head:")

        test_cases = [
            (20, 'Kaplan'),
            (50, 'Kaplan'),
            (100, 'Francis'),
            (250, 'Francis'),
            (500, 'Pelton'),
            (1000, 'Pelton')
        ]

        for head, expected_type in test_cases:
            selected = select_turbine_type(head)
            print(f"    H={head:4.0f}m -> {selected:8s} (expected: {expected_type})")
            assert selected == expected_type

    def test_specific_speed(self):
        """Test specific speed calculation"""
        print("\n  Specific speed calculation:")

        # Francis example
        ns_francis = calculate_specific_speed(
            power_MW=100.0,
            head=150.0,
            speed_rpm=250.0
        )
        print(f"    Francis: ns = {ns_francis:.1f} (typical: 60-400)")
        assert 60 < ns_francis < 400, "Francis specific speed out of range"

        # Kaplan example
        ns_kaplan = calculate_specific_speed(
            power_MW=50.0,
            head=25.0,
            speed_rpm=115.0
        )
        print(f"    Kaplan:  ns = {ns_kaplan:.1f} (typical: 300-1000)")
        assert 300 < ns_kaplan < 1000, "Kaplan specific speed out of range"

        # Pelton example
        ns_pelton = calculate_specific_speed(
            power_MW=200.0,
            head=800.0,
            speed_rpm=500.0
        )
        print(f"    Pelton:  ns = {ns_pelton:.1f} (typical: 10-70)")
        assert 10 < ns_pelton < 70, "Pelton specific speed out of range"


class TestIntegration:
    """Integration tests for all turbine types"""

    def test_all_turbines_power_monotonic(self):
        """Test that power increases with flow for all turbines"""
        turbines = [
            FrancisTurbine(0, 100, 150, 80, 250),
            KaplanTurbine(0, 50, 25, 230, 115),
            PeltonTurbine(0, 200, 800, 28, 500)
        ]

        print("\n  Power monotonicity test:")
        for turbine in turbines:
            Q_values = [0.3, 0.5, 0.7, 1.0]
            Q_abs = [q * turbine.rated_flow for q in Q_values]
            powers = []

            for Q in Q_abs:
                P, _, _ = turbine.calculate_power(Q, turbine.rated_head)
                powers.append(P)

            # Check monotonic increase
            for i in range(len(powers) - 1):
                assert powers[i+1] > powers[i], \
                    f"{turbine.turbine_type}: Power should increase with flow"

            print(f"    {turbine.turbine_type:8s}: {powers[0]/1e6:.1f} MW -> {powers[-1]/1e6:.1f} MW ")

    def test_torque_calculation(self):
        """Test torque calculation for all turbines"""
        turbine = FrancisTurbine(0, 100, 150, 80, 250)

        P = 100e6  # 100 MW
        n = 250    # rpm

        T = turbine.calculate_torque(P, n)

        # Verify: P = T * ω = T * 2pi * n / 60
        omega = 2 * np.pi * n / 60
        P_check = T * omega

        assert abs(P - P_check) / P < 0.01, "Torque calculation error"

        print(f"\n  Torque test: P={P/1e6:.0f} MW, n={n} rpm -> T={T/1e6:.3f} MN·m")


def run_all_tests():
    """Run all tests"""
    print("=" * 80)
    print("TURBINE TEST SUITE")
    print("=" * 80)

    test_classes = [
        TestFrancisTurbine,
        TestKaplanTurbine,
        TestPeltonTurbine,
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
