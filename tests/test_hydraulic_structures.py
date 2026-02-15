# -*- coding: utf-8 -*-
"""
Test cases for Hydraulic Structures (Spillway, Transition, Drop)

Tests the newly added water control structures:
- Spillway (WES, Ogee, Broad-crested)
- Transition (Expansion/Contraction)
- Drop (Hydraulic drop)

Author: Claude
Date: 2025-10-22
"""

import pytest
import warnings
warnings.filterwarnings("ignore")
import numpy as np
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

try:
    from solvers.gate import Spillway, Transition, Drop
except ImportError as e:
    pytest.skip(f"Required module not available: {e}", allow_module_level=True)



class TestSpillway:
    """Test Spillway class"""

    def test_wes_spillway_free_flow(self):
        """Test WES spillway free flow"""
        spillway = Spillway(
            position=1000.0,
            width=50.0,
            crest_elevation=100.0,
            spillway_type='wes',
            Cd=2.1
        )

        # Test free flow (downstream below crest)
        h_upstream = 105.0  # 5m above crest
        h_downstream = 95.0  # Below crest

        Q, flow_type = spillway.calculate_discharge(h_upstream, h_downstream)

        # Verify
        assert Q > 0, "Flow should be positive"
        assert flow_type == 'free', "Should be free flow"

        # Check formula: Q = Cd * B * H^(3/2)
        H = h_upstream - spillway.crest_elevation
        Q_expected = spillway.Cd * spillway.width * (H ** 1.5)
        assert abs(Q - Q_expected) / Q_expected < 0.01

        print(f"  WES free flow test passed: Q={Q:.2f} m3/s @ H={H}m")

    def test_spillway_submerged_flow(self):
        """Test spillway submerged flow"""
        spillway = Spillway(
            position=1000.0,
            width=50.0,
            crest_elevation=100.0,
            spillway_type='wes',
            Cd=2.1,
            submergence_threshold=0.67
        )

        # Test submerged flow
        h_upstream = 105.0  # 5m above crest
        h_downstream = 104.0  # 4m above crest (high submergence)

        Q, flow_type = spillway.calculate_discharge(h_upstream, h_downstream)

        # Verify
        assert Q > 0, "Flow should be positive"
        assert flow_type == 'submerged', "Should be submerged flow"

        # Submerged flow should be less than free flow
        Q_free, _ = spillway.calculate_discharge(h_upstream, 95.0)
        assert Q < Q_free, "Submerged flow should be less than free flow"

        print(f"  Submerged flow test passed: Q={Q:.2f} m3/s (Q_free={Q_free:.2f})")

    def test_spillway_no_flow(self):
        """Test spillway with water below crest"""
        spillway = Spillway(
            position=1000.0,
            width=50.0,
            crest_elevation=100.0,
            spillway_type='wes',
            Cd=2.1
        )

        # Water below crest
        h_upstream = 99.5  # Below crest
        h_downstream = 95.0

        Q, flow_type = spillway.calculate_discharge(h_upstream, h_downstream)

        assert abs(Q) < 1e-6, "Flow should be zero when water below crest"
        assert flow_type == 'no_flow'

        print("  No flow test passed")

    def test_spillway_types(self):
        """Test different spillway types"""
        spillways = {
            'wes': Spillway(1000.0, 50.0, 100.0, 'wes', Cd=2.1),
            'ogee': Spillway(1000.0, 50.0, 100.0, 'ogee', Cd=2.1),
            'broad_crested': Spillway(1000.0, 50.0, 100.0, 'broad_crested', Cd=0.848)
        }

        h_up = 105.0
        h_down = 95.0

        print("  Spillway type comparison:")
        for name, spillway in spillways.items():
            Q, flow_type = spillway.calculate_discharge(h_up, h_down)
            print(f"    {name:15s}: Q={Q:8.2f} m3/s")
            assert Q > 0, f"{name} should have positive flow"

    def test_spillway_derivatives(self):
        """Test spillway analytical derivatives"""
        spillway = Spillway(1000.0, 50.0, 100.0, 'wes', Cd=2.1)

        h_up = 105.0
        h_down = 95.0

        # Analytical derivatives
        dQ_dh_up, dQ_dh_down = spillway.calculate_discharge_derivatives(h_up, h_down)

        # Numerical derivatives
        eps = 1e-4
        Q0, _ = spillway.calculate_discharge(h_up, h_down)
        Q_up, _ = spillway.calculate_discharge(h_up + eps, h_down)

        dQ_dh_up_num = (Q_up - Q0) / eps

        # Verify (within 5%)
        rel_error = abs(dQ_dh_up - dQ_dh_up_num) / abs(dQ_dh_up_num)
        assert rel_error < 0.05, f"Derivative error too large: {rel_error*100:.2f}%"

        print(f"  Derivative test passed: error={rel_error*100:.2f}%")


class TestTransition:
    """Test Transition class"""

    def test_expansion_transition(self):
        """Test expansion transition"""
        transition = Transition(
            position=500.0,
            width_upstream=10.0,
            width_downstream=15.0,  # Expansion
            K_loss=0.3
        )

        assert transition.transition_type == 'expansion'

        h_up = 5.0
        h_down = 4.8

        Q, flow_type = transition.calculate_discharge(h_up, h_down)

        assert Q > 0, "Flow should be positive"
        assert flow_type == 'expansion'

        print(f"  Expansion test passed: Q={Q:.2f} m3/s")

    def test_contraction_transition(self):
        """Test contraction transition"""
        transition = Transition(
            position=500.0,
            width_upstream=15.0,
            width_downstream=10.0,  # Contraction
            K_loss=0.1
        )

        assert transition.transition_type == 'contraction'

        h_up = 5.0
        h_down = 5.2  # Slight increase due to contraction

        Q, flow_type = transition.calculate_discharge(h_up, h_down)

        # Flow might be zero or small if downstream is higher
        assert flow_type == 'contraction'

        print(f"  Contraction test passed: Q={Q:.2f} m3/s")

    def test_transition_derivatives(self):
        """Test transition derivatives (numerical)"""
        transition = Transition(
            position=500.0,
            width_upstream=10.0,
            width_downstream=15.0,
            K_loss=0.2
        )

        h_up = 5.0
        h_down = 4.5

        # Get derivatives
        dQ_dh_up, dQ_dh_down = transition.calculate_discharge_derivatives(h_up, h_down)

        # Derivatives should be finite
        assert np.isfinite(dQ_dh_up)
        assert np.isfinite(dQ_dh_down)

        print(f"  Transition derivatives test passed")


class TestDrop:
    """Test Drop class"""

    def test_drop_basic_flow(self):
        """Test basic drop flow"""
        drop = Drop(
            position=800.0,
            width=10.0,
            drop_height=2.0,  # 2m drop
            Cd=0.6
        )

        h_up = 3.0  # 3m upstream depth
        h_down = 1.0  # Downstream (not used)

        Q, flow_type = drop.calculate_discharge(h_up, h_down)

        assert Q > 0, "Flow should be positive"
        assert flow_type == 'drop'

        # Verify formula: Q = Cd * B * h * sqrt(2g * (h + delta_z))
        total_head = h_up + drop.drop_height
        Q_expected = drop.Cd * drop.width * h_up * np.sqrt(2 * drop.g * total_head)
        assert abs(Q - Q_expected) / Q_expected < 0.01

        print(f"  Drop flow test passed: Q={Q:.2f} m3/s @ h={h_up}m, Δz={drop.drop_height}m")

    def test_drop_no_flow(self):
        """Test drop with no upstream water"""
        drop = Drop(800.0, 10.0, 2.0, Cd=0.6)

        Q, flow_type = drop.calculate_discharge(0.0, 0.0)

        assert abs(Q) < 1e-6, "Flow should be zero with no upstream water"

        print("  Drop no flow test passed")

    def test_drop_derivatives(self):
        """Test drop analytical derivatives"""
        drop = Drop(800.0, 10.0, 2.0, Cd=0.6)

        h_up = 3.0

        # Analytical derivatives
        dQ_dh_up, dQ_dh_down = drop.calculate_discharge_derivatives(h_up, None)

        # Numerical derivative
        eps = 1e-4
        Q0, _ = drop.calculate_discharge(h_up, None)
        Q_up, _ = drop.calculate_discharge(h_up + eps, None)

        dQ_dh_up_num = (Q_up - Q0) / eps

        # Verify (within 5%)
        rel_error = abs(dQ_dh_up - dQ_dh_up_num) / abs(dQ_dh_up_num)
        assert rel_error < 0.05, f"Derivative error too large: {rel_error*100:.2f}%"

        # Downstream derivative should be zero
        assert abs(dQ_dh_down) < 1e-6, "Drop should not depend on downstream"

        print(f"  Drop derivative test passed: error={rel_error*100:.2f}%")

    def test_drop_flow_increases_with_depth(self):
        """Test that flow increases with upstream depth"""
        drop = Drop(800.0, 10.0, 2.0, Cd=0.6)

        depths = [1.0, 2.0, 3.0, 4.0, 5.0]
        flows = []

        for h in depths:
            Q, _ = drop.calculate_discharge(h, None)
            flows.append(Q)

        # Verify monotonic increase
        for i in range(len(flows) - 1):
            assert flows[i+1] > flows[i], "Flow should increase with depth"

        print("  Drop monotonic flow test passed")


class TestIntegration:
    """Integration tests for multiple structures"""

    def test_all_structures_instantiation(self):
        """Test that all structures can be created"""
        structures = [
            Spillway(1000.0, 50.0, 100.0, 'wes'),
            Spillway(2000.0, 50.0, 100.0, 'ogee'),
            Spillway(3000.0, 50.0, 100.0, 'broad_crested', Cd=0.848),
            Transition(4000.0, 10.0, 15.0, K_loss=0.2),
            Transition(5000.0, 15.0, 10.0, K_loss=0.1),
            Drop(6000.0, 10.0, 2.0, Cd=0.6),
        ]

        for struct in structures:
            assert struct is not None
            assert hasattr(struct, 'calculate_discharge')
            assert hasattr(struct, 'calculate_discharge_derivatives')

        print(f"  Instantiation test passed: {len(structures)} structures created")

    def test_all_structures_flow_calculation(self):
        """Test flow calculation for all structures"""
        test_cases = [
            (Spillway(1000.0, 50.0, 100.0, 'wes'), 105.0, 95.0),
            (Transition(2000.0, 10.0, 15.0), 5.0, 4.5),
            (Drop(3000.0, 10.0, 2.0), 3.0, None),
        ]

        print("  Flow calculation for all structures:")
        for struct, h_up, h_down in test_cases:
            Q, flow_type = struct.calculate_discharge(h_up, h_down)
            print(f"    {struct.__class__.__name__:15s}: Q={Q:8.2f} m3/s, type={flow_type}")
            assert Q >= 0, f"{struct.__class__.__name__} should have non-negative flow"


def run_all_tests():
    """Run all tests"""
    print("=" * 80)
    print("Hydraulic Structures Test Suite")
    print("=" * 80)

    test_classes = [
        TestSpillway,
        TestTransition,
        TestDrop,
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
