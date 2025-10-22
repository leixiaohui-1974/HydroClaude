# -*- coding: utf-8 -*-
"""
Test cases for Valve classes

Tests:
1. Valve characteristic curves
2. Flow calculation
3. Analytical derivatives (for Jacobian)
4. Dynamic response
5. Integration with hydraulic systems

Author: Claude
Date: 2025-10-22
"""

import pytest
import numpy as np
import sys
import os

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from physics.valve import Valve, GateValve, ButterflyValve, BallValve


class TestValveCharacteristics:
    """Test valve characteristic curves"""

    def test_linear_characteristic(self):
        """Test linear characteristic (Gate valve)"""
        valve = GateValve("GV1", Cv_max=100.0)

        # Test linear relationship
        openings = [0.0, 0.25, 0.5, 0.75, 1.0]
        expected_Cvs = [0.0, 25.0, 50.0, 75.0, 100.0]

        for opening, expected_Cv in zip(openings, expected_Cvs):
            Cv = valve.get_Cv(opening)
            assert abs(Cv - expected_Cv) < 0.1, f"Linear characteristic failed at opening={opening}"

        print("  Linear characteristic test passed")

    def test_quick_opening_characteristic(self):
        """Test quick opening characteristic (Ball valve)"""
        valve = BallValve("BV1", Cv_max=100.0)

        # Test quadratic relationship
        openings = [0.0, 0.5, 0.7, 1.0]
        expected_Cvs = [0.0, 25.0, 49.0, 100.0]

        for opening, expected_Cv in zip(openings, expected_Cvs):
            Cv = valve.get_Cv(opening)
            assert abs(Cv - expected_Cv) < 0.1, f"Quick opening failed at opening={opening}"

        # Verify it's more responsive at small openings than linear
        Cv_10pct = valve.get_Cv(0.1)
        Cv_linear = 0.1 * valve.Cv_max
        assert Cv_10pct < Cv_linear, "Quick opening should be less than linear at small openings"

        print("  Quick opening characteristic test passed")

    def test_equal_percentage_characteristic(self):
        """Test equal percentage characteristic (Butterfly valve)"""
        valve = ButterflyValve("BTF1", Cv_max=100.0, rangeability=50.0)

        # Test exponential relationship
        # At 100% opening: Cv = Cv_max * R^0 = Cv_max
        assert abs(valve.get_Cv(1.0) - 100.0) < 0.1

        # At 0% opening: Cv = 0
        assert valve.get_Cv(0.0) < 0.1

        # Test equal percentage property
        # Change from 30% to 31% should have same percentage change as 80% to 81%
        Cv_30 = valve.get_Cv(0.30)
        Cv_31 = valve.get_Cv(0.31)
        pct_change_30 = (Cv_31 - Cv_30) / Cv_30 if Cv_30 > 0 else 0

        Cv_80 = valve.get_Cv(0.80)
        Cv_81 = valve.get_Cv(0.81)
        pct_change_80 = (Cv_81 - Cv_80) / Cv_80

        # Should be approximately equal (within 1%)
        assert abs(pct_change_30 - pct_change_80) / pct_change_80 < 0.01

        print("  Equal percentage characteristic test passed")

    def test_characteristic_bounds(self):
        """Test that all characteristics are bounded [0, Cv_max]"""
        valves = [
            GateValve("GV", Cv_max=100.0),
            ButterflyValve("BTF", Cv_max=100.0),
            BallValve("BV", Cv_max=100.0)
        ]

        for valve in valves:
            for opening in np.linspace(0, 1, 21):
                Cv = valve.get_Cv(opening)
                assert 0 <= Cv <= valve.Cv_max, \
                    f"{valve.__class__.__name__} Cv out of bounds at opening={opening}"

        print("  Characteristic bounds test passed")


class TestFlowCalculation:
    """Test flow calculation"""

    def test_basic_flow_calculation(self):
        """Test basic flow calculation"""
        valve = GateValve("GV1", Cv_max=50.0)
        valve.state.opening = 0.5  # 50% opening

        P_up = 500000.0  # 500 kPa
        P_down = 100000.0  # 100 kPa

        Q = valve.calculate_flow(P_up, P_down)

        # Verify flow is positive
        assert Q > 0, "Flow should be positive"

        # Verify flow formula: Q = Cv * sqrt(Delta_P / rho)
        Cv = valve.get_Cv(0.5)
        delta_P = P_up - P_down
        Q_expected = Cv * np.sqrt(delta_P / valve.rho)

        assert abs(Q - Q_expected) / Q_expected < 0.01, "Flow calculation mismatch"

        print(f"  Basic flow calculation test passed: Q={Q:.3f} m3/s")

    def test_flow_with_pressure_diff(self):
        """Test that flow increases with pressure difference"""
        valve = GateValve("GV1", Cv_max=50.0)
        valve.state.opening = 0.5

        P_down = 100000.0

        # Test increasing upstream pressure
        P_ups = [200000.0, 300000.0, 500000.0, 800000.0]
        flows = []

        for P_up in P_ups:
            Q = valve.calculate_flow(P_up, P_down)
            flows.append(Q)

        # Verify monotonic increase
        for i in range(len(flows) - 1):
            assert flows[i+1] > flows[i], "Flow should increase with pressure difference"

        print("  Flow vs pressure difference test passed")

    def test_flow_with_opening(self):
        """Test that flow increases with opening"""
        valve = GateValve("GV1", Cv_max=50.0)

        P_up = 500000.0
        P_down = 100000.0

        openings = [0.2, 0.4, 0.6, 0.8, 1.0]
        flows = []

        for opening in openings:
            valve.state.opening = opening
            Q = valve.calculate_flow(P_up, P_down)
            flows.append(Q)

        # Verify monotonic increase
        for i in range(len(flows) - 1):
            assert flows[i+1] > flows[i], "Flow should increase with opening"

        print("  Flow vs opening test passed")

    def test_zero_pressure_diff(self):
        """Test zero flow when pressure difference is zero"""
        valve = GateValve("GV1", Cv_max=50.0)
        valve.state.opening = 1.0

        Q = valve.calculate_flow(100000.0, 100000.0)

        assert abs(Q) < 1e-6, "Flow should be zero when pressure difference is zero"

        print("  Zero pressure difference test passed")

    def test_closed_valve(self):
        """Test zero flow when valve is closed"""
        valve = GateValve("GV1", Cv_max=50.0)
        valve.state.opening = 0.0

        Q = valve.calculate_flow(500000.0, 100000.0)

        assert abs(Q) < 1e-6, "Flow should be zero when valve is closed"

        print("  Closed valve test passed")


class TestAnalyticalDerivatives:
    """Test analytical derivatives (for Jacobian)"""

    def test_derivatives_accuracy(self):
        """Test that analytical derivatives match numerical derivatives"""
        valves = [
            GateValve("GV", Cv_max=50.0),
            ButterflyValve("BTF", Cv_max=80.0),
            BallValve("BV", Cv_max=30.0)
        ]

        P_up = 600000.0
        P_down = 200000.0

        for valve in valves:
            valve.state.opening = 0.6

            # Analytical derivatives
            dQ_dP_up, dQ_dP_down = valve.calculate_flow_derivatives(P_up, P_down)

            # Numerical derivatives
            eps = 1e-3
            Q0 = valve.calculate_flow(P_up, P_down)
            Q_up = valve.calculate_flow(P_up + eps, P_down)
            Q_down = valve.calculate_flow(P_up, P_down + eps)

            dQ_dP_up_num = (Q_up - Q0) / eps
            dQ_dP_down_num = (Q_down - Q0) / eps

            # Verify accuracy (should be within 1%)
            rel_error_up = abs(dQ_dP_up - dQ_dP_up_num) / abs(dQ_dP_up_num)
            rel_error_down = abs(dQ_dP_down - dQ_dP_down_num) / abs(dQ_dP_down_num)

            assert rel_error_up < 0.01, \
                f"{valve.__class__.__name__}: dQ/dP_up error = {rel_error_up*100:.2f}%"
            assert rel_error_down < 0.01, \
                f"{valve.__class__.__name__}: dQ/dP_down error = {rel_error_down*100:.2f}%"

        print("  Derivatives accuracy test passed")

    def test_derivatives_at_small_pressure_diff(self):
        """Test derivatives at small pressure difference (near truncation point)"""
        valve = GateValve("GV", Cv_max=50.0)
        valve.state.opening = 0.5

        # Very small pressure difference
        P_up = 100001.0
        P_down = 100000.0

        # Should not raise error
        dQ_dP_up, dQ_dP_down = valve.calculate_flow_derivatives(P_up, P_down)

        # Derivatives should be finite
        assert np.isfinite(dQ_dP_up), "dQ/dP_up should be finite"
        assert np.isfinite(dQ_dP_down), "dQ/dP_down should be finite"

        # Derivative relationship: dQ/dP_down = -dQ/dP_up
        assert abs(dQ_dP_down + dQ_dP_up) / abs(dQ_dP_up) < 0.01

        print("  Derivatives at small pressure difference test passed")


class TestDynamicResponse:
    """Test dynamic response"""

    def test_instantaneous_response(self):
        """Test instantaneous response (response_time=0)"""
        valve = GateValve("GV", Cv_max=50.0, response_time=0.0)
        valve.state.opening = 0.0

        dt = 0.1
        valve.update_high_fidelity(dt, {'target_opening': 1.0})

        # Should immediately reach target
        assert abs(valve.state.opening - 1.0) < 1e-6

        print("  Instantaneous response test passed")

    def test_first_order_lag(self):
        """Test first-order lag response"""
        valve = GateValve("GV", Cv_max=50.0, response_time=5.0)
        valve.state.opening = 0.0

        dt = 0.5
        target = 1.0

        # Simulate for one time constant
        n_steps = int(5.0 / dt)  # One time constant
        for i in range(n_steps):
            valve.update_high_fidelity(dt, {'target_opening': target})

        # After one time constant, should reach ~63% of target
        expected = target * (1 - np.exp(-1))
        assert abs(valve.state.opening - expected) < 0.05

        print(f"  First-order lag test passed: opening={valve.state.opening:.3f} "
              f"(expected ~{expected:.3f})")

    def test_response_bounds(self):
        """Test that opening stays within [0, 1]"""
        valve = GateValve("GV", Cv_max=50.0, response_time=2.0)
        valve.state.opening = 0.5

        dt = 0.1

        # Test excessive target (should clip to 1.0)
        for i in range(50):
            valve.update_high_fidelity(dt, {'target_opening': 1.5})

        assert valve.state.opening <= 1.0

        # Test negative target (should clip to 0.0)
        for i in range(50):
            valve.update_high_fidelity(dt, {'target_opening': -0.5})

        assert valve.state.opening >= 0.0

        print("  Response bounds test passed")

    def test_flow_update_during_response(self):
        """Test that flow is calculated correctly during dynamic response"""
        valve = GateValve("GV", Cv_max=50.0, response_time=5.0)
        valve.state.opening = 0.2

        P_up = 500000.0
        P_down = 100000.0

        dt = 0.5
        for i in range(10):
            valve.update_high_fidelity(dt, {
                'target_opening': 0.8,
                'upstream_pressure': P_up,
                'downstream_pressure': P_down
            })

            # Verify flow is consistent with current opening
            Q_expected = valve.calculate_flow(P_up, P_down, valve.state.opening)
            assert abs(valve.state.flow - Q_expected) / Q_expected < 0.01

        print("  Flow update during response test passed")


class TestValveIntegration:
    """Test integration scenarios"""

    def test_multiple_valves_series(self):
        """Test multiple valves in series"""
        valve1 = GateValve("GV1", Cv_max=50.0)
        valve2 = ButterflyValve("BTF1", Cv_max=60.0)

        valve1.state.opening = 0.8
        valve2.state.opening = 0.6

        # Assume same flow through both valves
        P_in = 600000.0
        P_mid = 400000.0
        P_out = 100000.0

        Q1 = valve1.calculate_flow(P_in, P_mid)
        Q2 = valve2.calculate_flow(P_mid, P_out)

        # Flows should be similar (not exactly equal due to different Cv)
        # But both should be positive
        assert Q1 > 0 and Q2 > 0

        print(f"  Series valves test passed: Q1={Q1:.3f}, Q2={Q2:.3f} m3/s")

    def test_valve_types_comparison(self):
        """Compare different valve types under same conditions"""
        valves = [
            GateValve("GV", Cv_max=100.0),
            ButterflyValve("BTF", Cv_max=100.0),
            BallValve("BV", Cv_max=100.0)
        ]

        P_up = 500000.0
        P_down = 100000.0

        results = {}
        for valve in valves:
            valve.state.opening = 0.5
            Q = valve.calculate_flow(P_up, P_down)
            results[valve.__class__.__name__] = Q

        # At 50% opening:
        # Linear (Gate) should be highest
        # Equal percentage (Butterfly) should be lowest
        # Quick opening (Ball) should be in between
        assert results['GateValve'] > results['BallValve']
        assert results['BallValve'] > results['ButterflyValve']

        print(f"  Valve types comparison test passed")
        for name, Q in results.items():
            print(f"    {name:20s}: {Q:.3f} m3/s @ 50% opening")


def run_all_tests():
    """Run all tests"""
    print("=" * 80)
    print("Valve Test Suite")
    print("=" * 80)

    test_classes = [
        TestValveCharacteristics,
        TestFlowCalculation,
        TestAnalyticalDerivatives,
        TestDynamicResponse,
        TestValveIntegration
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
