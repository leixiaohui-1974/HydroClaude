#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Comprehensive test suite for boundary condition modules.

Covers:
1. Subcritical inlet BC (fixed Q upstream)
2. Subcritical outlet BC (fixed h downstream)
3. Supercritical inlet BC (both h and Q specified)
4. Transmissive (non-reflecting) outflow BC
5. Dry-wet front (eps_dry handling, no division by zero)
6. Critical flow BC (Fr=1 transition)
7. Reflective BC (wall boundary)
8. Riemann invariant round-trip
9. Froude number / flow regime identification
10. Edge cases: zero depth, zero velocity, extreme values

Tests target:
- solvers.boundary_conditions.CharacteristicBC (characteristic-based BC)
- physics.boundaries (GateBoundary, ValveBoundary, PumpBoundary)

Author: HydroClaude Test Team
Date: 2025-11-25
"""

import sys
import os
import warnings

warnings.filterwarnings("ignore")
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", ".."))

import numpy as np
import pytest

from solvers.boundary_conditions import (
    CharacteristicBC,
    FlowRegime,
    BoundaryConditionType,
)
from physics.boundaries import GateBoundary, ValveBoundary, PumpBoundary


# =====================================================================
#  Fixtures
# =====================================================================
@pytest.fixture
def bc():
    """Standard CharacteristicBC instance."""
    return CharacteristicBC(g=9.81)


# =====================================================================
#  1. Froude Number and Flow Regime Identification
# =====================================================================
class TestFroudeNumber:
    """Froude number computation and flow regime classification."""

    def test_subcritical(self, bc):
        h, u = 2.0, 1.0
        Fr = bc.compute_froude_number(h, u)
        expected = abs(u) / np.sqrt(9.81 * h)
        assert Fr == pytest.approx(expected, rel=1e-6)
        assert Fr < 1.0
        regime = bc.identify_flow_regime(h, u)
        assert regime == FlowRegime.SUBCRITICAL

    def test_supercritical(self, bc):
        h, u = 0.3, 5.0
        Fr = bc.compute_froude_number(h, u)
        assert Fr > 1.0
        regime = bc.identify_flow_regime(h, u)
        assert regime == FlowRegime.SUPERCRITICAL

    def test_critical(self, bc):
        """Construct exact critical flow: u = sqrt(g*h)."""
        h = 1.0
        u = np.sqrt(9.81 * h)
        Fr = bc.compute_froude_number(h, u)
        assert Fr == pytest.approx(1.0, rel=1e-6)
        regime = bc.identify_flow_regime(h, u)
        assert regime == FlowRegime.CRITICAL

    def test_zero_depth(self, bc):
        """Zero depth should return Fr=0, no crash."""
        Fr = bc.compute_froude_number(0.0, 5.0)
        assert Fr == 0.0

    def test_negative_velocity(self, bc):
        """Froude uses abs(u)."""
        Fr_pos = bc.compute_froude_number(2.0, 3.0)
        Fr_neg = bc.compute_froude_number(2.0, -3.0)
        assert Fr_pos == pytest.approx(Fr_neg, rel=1e-10)

    @pytest.mark.parametrize("h,u", [(0.5, 0.5), (1.0, 2.0), (3.0, 0.1)])
    def test_froude_formula(self, bc, h, u):
        Fr = bc.compute_froude_number(h, u)
        expected = abs(u) / np.sqrt(9.81 * h)
        assert Fr == pytest.approx(expected, rel=1e-10)


# =====================================================================
#  2. Riemann Invariants
# =====================================================================
class TestRiemannInvariants:
    """R+ = u + 2c, R- = u - 2c, round-trip recovery."""

    def test_compute(self, bc):
        h, u = 2.0, 3.0
        c = np.sqrt(9.81 * h)
        R_plus, R_minus = bc.compute_riemann_invariants(h, u)
        assert R_plus == pytest.approx(u + 2 * c, rel=1e-10)
        assert R_minus == pytest.approx(u - 2 * c, rel=1e-10)

    @pytest.mark.parametrize(
        "h,u", [(0.5, 1.0), (1.0, 0.0), (2.0, -1.0), (5.0, 3.0)]
    )
    def test_round_trip(self, bc, h, u):
        """Recover h, u from Riemann invariants."""
        R_plus, R_minus = bc.compute_riemann_invariants(h, u)
        h_rec, u_rec = bc.recover_from_riemann_invariants(R_plus, R_minus)
        assert h_rec == pytest.approx(h, rel=1e-6)
        assert u_rec == pytest.approx(u, rel=1e-6)

    def test_zero_velocity(self, bc):
        h, u = 3.0, 0.0
        R_plus, R_minus = bc.compute_riemann_invariants(h, u)
        assert R_plus == pytest.approx(-R_minus, rel=1e-10)
        h_rec, u_rec = bc.recover_from_riemann_invariants(R_plus, R_minus)
        assert u_rec == pytest.approx(0.0, abs=1e-10)
        assert h_rec == pytest.approx(h, rel=1e-6)


# =====================================================================
#  3. Subcritical Inlet BC (fixed Q upstream)
# =====================================================================
class TestSubcriticalInletBC:
    """
    Fr < 1 at inlet: 1 BC from exterior (Q), 1 Riemann invariant from interior.
    """

    def test_fixed_q_produces_correct_discharge(self, bc):
        h_interior = 2.0
        u_interior = 1.0  # Fr ~ 0.23 < 1
        Q_bc = 30.0
        B = 10.0

        h_bc, u_bc = bc.apply_subcritical_inlet(
            None, None, h_interior, u_interior,
            bc_value=Q_bc, bc_type="Q", B=B,
        )

        Q_actual = u_bc * h_bc * B
        assert Q_actual == pytest.approx(Q_bc, rel=0.02), (
            f"Inlet Q should match: actual={Q_actual:.4f}, expected={Q_bc}"
        )

    def test_fixed_h_inlet(self, bc):
        h_interior = 2.0
        u_interior = 1.0
        h_target = 2.5

        h_bc, u_bc = bc.apply_subcritical_inlet(
            None, None, h_interior, u_interior,
            bc_value=h_target, bc_type="h",
        )

        assert h_bc == pytest.approx(h_target, rel=1e-6)
        assert np.isfinite(u_bc)

    def test_invalid_bc_type(self, bc):
        with pytest.raises(ValueError):
            bc.apply_subcritical_inlet(
                None, None, 2.0, 1.0, bc_value=10.0, bc_type="invalid"
            )

    @pytest.mark.parametrize("Q_bc", [5.0, 10.0, 20.0, 50.0, 100.0])
    def test_various_q_values(self, bc, Q_bc):
        B = 10.0
        h_bc, u_bc = bc.apply_subcritical_inlet(
            None, None, 2.0, 1.0, bc_value=Q_bc, bc_type="Q", B=B,
        )
        Q_actual = u_bc * h_bc * B
        assert Q_actual == pytest.approx(Q_bc, rel=0.05)


# =====================================================================
#  4. Subcritical Outlet BC (fixed h downstream)
# =====================================================================
class TestSubcriticalOutletBC:
    """
    Fr < 1 at outlet: 1 BC from exterior (h), 1 Riemann invariant from interior.
    """

    def test_fixed_h_outlet(self, bc):
        h_interior = 2.0
        u_interior = 1.0
        h_target = 1.5

        h_bc, u_bc = bc.apply_subcritical_outlet(
            None, None, h_interior, u_interior,
            bc_value=h_target, bc_type="h",
        )

        assert h_bc == pytest.approx(h_target, rel=1e-6)
        assert np.isfinite(u_bc)

    def test_fixed_q_outlet(self, bc):
        h_interior = 2.0
        u_interior = 1.0
        Q_target = 15.0
        B = 10.0

        h_bc, u_bc = bc.apply_subcritical_outlet(
            None, None, h_interior, u_interior,
            bc_value=Q_target, bc_type="Q", B=B,
        )

        Q_actual = u_bc * h_bc * B
        assert Q_actual == pytest.approx(Q_target, rel=0.05)

    def test_outlet_invalid_type(self, bc):
        with pytest.raises(ValueError):
            bc.apply_subcritical_outlet(
                None, None, 2.0, 1.0, bc_value=1.0, bc_type="x"
            )

    @pytest.mark.parametrize("h_target", [0.5, 1.0, 1.5, 2.0, 3.0])
    def test_various_h_targets(self, bc, h_target):
        h_bc, u_bc = bc.apply_subcritical_outlet(
            None, None, 2.0, 1.0, bc_value=h_target, bc_type="h",
        )
        assert h_bc == pytest.approx(h_target, rel=1e-6)


# =====================================================================
#  5. Supercritical Inlet BC (both h and Q specified)
# =====================================================================
class TestSupercriticalInletBC:
    """Fr > 1: both characteristics enter from upstream, 2 BCs needed."""

    def test_both_values_imposed(self, bc):
        h_bc_val = 0.5
        Q_bc_val = 20.0
        B = 10.0

        h_bc, u_bc = bc.apply_supercritical_inlet(h_bc_val, Q_bc_val, B=B)

        assert h_bc == pytest.approx(h_bc_val, rel=1e-10)
        u_expected = Q_bc_val / (B * h_bc_val)
        assert u_bc == pytest.approx(u_expected, rel=1e-10)

    def test_verify_supercritical(self, bc):
        """The resulting flow should indeed be supercritical."""
        h = 0.3
        Q = 20.0
        B = 5.0
        h_bc, u_bc = bc.apply_supercritical_inlet(h, Q, B=B)
        Fr = bc.compute_froude_number(h_bc, u_bc)
        assert Fr > 1.0, f"Expected supercritical, Fr={Fr:.3f}"

    @pytest.mark.parametrize("h,Q", [(0.2, 10.0), (0.5, 30.0), (0.1, 5.0)])
    def test_various_supercritical(self, bc, h, Q):
        B = 5.0
        h_bc, u_bc = bc.apply_supercritical_inlet(h, Q, B=B)
        assert h_bc == pytest.approx(h, rel=1e-10)
        Q_actual = u_bc * h_bc * B
        assert Q_actual == pytest.approx(Q, rel=1e-10)


# =====================================================================
#  6. Supercritical Outlet BC (transmissive / extrapolation)
# =====================================================================
class TestSupercriticalOutletBC:
    """Fr > 1 at outlet: all information flows out, no exterior BC needed."""

    def test_extrapolation(self, bc):
        h_int, u_int = 0.5, 5.0
        h_bc, u_bc = bc.apply_supercritical_outlet(h_int, u_int)
        assert h_bc == pytest.approx(h_int, rel=1e-10)
        assert u_bc == pytest.approx(u_int, rel=1e-10)


# =====================================================================
#  7. Transmissive (Non-Reflecting) BC
# =====================================================================
class TestTransmissiveBC:
    """Absorbing outflow boundary using advection equation."""

    def test_no_reflection(self, bc):
        h_int, u_int = 2.0, 1.0
        h_prev, u_prev = 2.0, 1.0
        dt, dx = 0.1, 10.0

        h_bc, u_bc = bc.apply_transmissive_bc(
            h_int, u_int, h_prev, u_prev, dt, dx
        )

        # When prev == interior (steady state), result should stay ~ same
        assert h_bc == pytest.approx(h_int, rel=0.1)
        assert u_bc == pytest.approx(u_int, rel=0.1)

    def test_positive_depth(self, bc):
        """Depth must remain positive."""
        h_bc, u_bc = bc.apply_transmissive_bc(
            h_interior=0.1, u_interior=2.0,
            h_prev=0.5, u_prev=1.0,
            dt=0.01, dx=1.0,
        )
        assert h_bc > 0, "Transmissive BC must keep h > 0"

    def test_zero_wave_speed(self, bc):
        """When c ~ 0, should fall back to interior values."""
        # u_interior ~ 0 and h_interior ~ 0 => c ~ 0
        h_bc, u_bc = bc.apply_transmissive_bc(
            h_interior=1e-12, u_interior=0.0,
            h_prev=1e-12, u_prev=0.0,
            dt=0.1, dx=1.0,
        )
        assert np.isfinite(h_bc)
        assert np.isfinite(u_bc)

    @pytest.mark.parametrize("dt", [0.001, 0.01, 0.1, 1.0])
    def test_various_dt(self, bc, dt):
        h_bc, u_bc = bc.apply_transmissive_bc(
            h_interior=2.0, u_interior=1.0,
            h_prev=2.0, u_prev=1.0,
            dt=dt, dx=10.0,
        )
        assert h_bc > 0
        assert np.isfinite(h_bc)
        assert np.isfinite(u_bc)


# =====================================================================
#  8. Critical Flow BC (Fr = 1)
# =====================================================================
class TestCriticalFlowBC:
    """h_c = (Q^2/(g*B^2))^(1/3), Fr = 1 at the boundary."""

    def test_critical_depth_formula(self, bc):
        Q = 20.0
        B = 10.0
        h_c, u_c = bc.apply_critical_depth_bc(Q, B)

        h_c_expected = (Q ** 2 / (9.81 * B ** 2)) ** (1.0 / 3.0)
        assert h_c == pytest.approx(h_c_expected, rel=1e-6)

    def test_froude_equals_one(self, bc):
        Q = 20.0
        B = 10.0
        h_c, u_c = bc.apply_critical_depth_bc(Q, B)
        Fr = bc.compute_froude_number(h_c, u_c)
        assert Fr == pytest.approx(1.0, rel=0.01)

    def test_continuity(self, bc):
        """Q = u_c * h_c * B."""
        Q = 50.0
        B = 8.0
        h_c, u_c = bc.apply_critical_depth_bc(Q, B)
        Q_check = u_c * h_c * B
        assert Q_check == pytest.approx(Q, rel=1e-6)

    @pytest.mark.parametrize("Q", [5.0, 10.0, 30.0, 100.0])
    def test_various_discharges(self, bc, Q):
        B = 10.0
        h_c, u_c = bc.apply_critical_depth_bc(Q, B)
        Fr = bc.compute_froude_number(h_c, u_c)
        assert Fr == pytest.approx(1.0, rel=0.01)

    def test_custom_gravity(self):
        bc_custom = CharacteristicBC(g=10.0)
        Q, B = 20.0, 10.0
        h_c, u_c = bc_custom.apply_critical_depth_bc(Q, B, g=10.0)
        h_c_expected = (Q ** 2 / (10.0 * B ** 2)) ** (1.0 / 3.0)
        assert h_c == pytest.approx(h_c_expected, rel=1e-6)


# =====================================================================
#  9. Dry-Wet Front (eps_dry handling)
# =====================================================================
class TestDryWetFront:
    """Ensure no division by zero when h is very small."""

    def test_near_zero_depth_froude(self, bc):
        """Very small h should not cause division by zero."""
        Fr = bc.compute_froude_number(1e-12, 1.0)
        assert Fr == 0.0  # implementation returns 0 when h < 1e-10

    def test_near_zero_depth_riemann(self, bc):
        h = 1e-14
        u = 0.0
        R_plus, R_minus = bc.compute_riemann_invariants(h, u)
        assert np.isfinite(R_plus)
        assert np.isfinite(R_minus)

    def test_subcritical_inlet_near_dry(self, bc):
        """Interior near-dry should not crash."""
        h_bc, u_bc = bc.apply_subcritical_inlet(
            None, None,
            h_interior=1e-10, u_interior=0.0,
            bc_value=1.0, bc_type="Q", B=10.0,
        )
        assert np.isfinite(h_bc)
        assert np.isfinite(u_bc)

    def test_transmissive_near_dry(self, bc):
        h_bc, u_bc = bc.apply_transmissive_bc(
            h_interior=1e-12, u_interior=0.0,
            h_prev=1e-12, u_prev=0.0,
            dt=0.1, dx=1.0,
        )
        assert h_bc > 0
        assert np.isfinite(u_bc)

    def test_critical_depth_small_q(self, bc):
        """Very small Q should produce very small h_c, not crash."""
        h_c, u_c = bc.apply_critical_depth_bc(Q=1e-6, B=10.0)
        assert h_c > 0
        assert np.isfinite(u_c)


# =====================================================================
#  10. Reflective BC (Wall Boundary)
# =====================================================================
class TestReflectiveBC:
    """
    A reflective (wall) boundary sets u = 0 at the wall while preserving h.
    This is the simplest BC: ghost cell mirrors interior with negated velocity.

    While CharacteristicBC does not have a dedicated reflective method,
    we can verify the concept using supercritical outlet (extrapolation)
    combined with velocity negation, and also via the subcritical outlet
    with Q=0.
    """

    def test_wall_via_subcritical_outlet_q_zero(self, bc):
        """Setting Q=0 at outlet simulates a wall (no net flow)."""
        h_int, u_int = 2.0, 1.0
        B = 10.0
        h_bc, u_bc = bc.apply_subcritical_outlet(
            None, None, h_int, u_int,
            bc_value=0.0, bc_type="Q", B=B,
        )
        Q_bc = u_bc * h_bc * B
        assert Q_bc == pytest.approx(0.0, abs=0.5)

    def test_wall_depth_preserved(self, bc):
        """At a wall, water depth should remain approximately the interior depth."""
        h_int = 3.0
        u_int = 0.5
        h_bc, u_bc = bc.apply_subcritical_outlet(
            None, None, h_int, u_int,
            bc_value=0.0, bc_type="Q", B=10.0,
        )
        # Depth should not deviate wildly
        assert abs(h_bc - h_int) < 2.0, (
            f"Wall BC depth {h_bc:.4f} too far from interior {h_int:.4f}"
        )


# =====================================================================
#  11. GateBoundary (physics.boundaries)
# =====================================================================
class TestGateBoundary:
    """Test the GateBoundary internal BC from physics.boundaries."""

    @pytest.fixture
    def gate_bc(self):
        return GateBoundary(width=10.0, Cd=0.6, opening=1.0)

    def test_basic_apply(self, gate_bc):
        """Should return a tuple of (h, Q) without crashing."""
        h_result, Q_result = gate_bc.apply(
            state=None,
            h_upstream=5.0, Q_upstream=20.0,
            h_downstream=3.0, Q_downstream=20.0,
            dx=100.0, dt=1.0, area=100.0,
        )
        assert np.isfinite(h_result)
        assert np.isfinite(Q_result)

    def test_positive_flow(self, gate_bc):
        h, Q = gate_bc.apply(
            state=None,
            h_upstream=5.0, Q_upstream=20.0,
            h_downstream=2.0, Q_downstream=20.0,
        )
        assert Q > 0

    def test_small_opening(self):
        gate_bc = GateBoundary(width=10.0, Cd=0.6, opening=0.01)
        h, Q = gate_bc.apply(
            state=None,
            h_upstream=5.0, Q_upstream=20.0,
            h_downstream=2.0, Q_downstream=20.0,
        )
        assert np.isfinite(Q)


# =====================================================================
#  12. ValveBoundary (physics.boundaries)
# =====================================================================
class TestValveBoundary:
    """Test the valve internal boundary condition."""

    @pytest.fixture
    def valve_bc(self):
        return ValveBoundary(Cv=10.0, opening=0.5, diameter=0.5)

    def test_basic_apply(self, valve_bc):
        H, Q = valve_bc.apply(
            state=None,
            H_upstream=40.0, Q_upstream=5.0,
            H_downstream=35.0, Q_downstream=5.0,
            wave_speed=1000.0,
        )
        assert np.isfinite(H)
        assert np.isfinite(Q)

    def test_closed_valve(self):
        valve = ValveBoundary(Cv=10.0, opening=0.0, diameter=0.5)
        H, Q = valve.apply(
            state=None,
            H_upstream=40.0, Q_upstream=5.0,
            H_downstream=35.0, Q_downstream=5.0,
        )
        assert Q == pytest.approx(0.0, abs=0.1)


# =====================================================================
#  13. PumpBoundary (physics.boundaries)
# =====================================================================
class TestPumpBoundary:
    """Test the pump internal boundary condition (H = a*Q^2 + b*Q + c)."""

    @pytest.fixture
    def pump_bc(self):
        # Typical parabolic curve: H = -0.01*Q^2 + 0*Q + 50
        return PumpBoundary(a=-0.01, b=0.0, c=50.0)

    def test_basic_apply(self, pump_bc):
        H, Q = pump_bc.apply(
            state=None,
            H_upstream=20.0, Q_upstream=5.0,
            H_downstream=40.0, Q_downstream=5.0,
            wave_speed=1000.0, area=1.0,
        )
        assert np.isfinite(H)
        assert np.isfinite(Q)

    def test_positive_flow(self, pump_bc):
        H, Q = pump_bc.apply(
            state=None,
            H_upstream=20.0, Q_upstream=5.0,
            H_downstream=40.0, Q_downstream=5.0,
        )
        assert Q > 0


# =====================================================================
#  14. BoundaryConditionType Enum
# =====================================================================
class TestBCTypeEnum:
    """Verify the BoundaryConditionType enum values exist."""

    def test_fixed_depth(self):
        assert BoundaryConditionType.FIXED_DEPTH.value == "h"

    def test_fixed_discharge(self):
        assert BoundaryConditionType.FIXED_DISCHARGE.value == "Q"

    def test_critical(self):
        assert BoundaryConditionType.CRITICAL_DEPTH.value == "critical"

    def test_transmissive(self):
        assert BoundaryConditionType.TRANSMISSIVE.value == "transmissive"

    def test_riemann(self):
        assert BoundaryConditionType.RIEMANN.value == "riemann"


# =====================================================================
#  15. FlowRegime Enum
# =====================================================================
class TestFlowRegimeEnum:

    def test_subcritical(self):
        assert FlowRegime.SUBCRITICAL.value == "subcritical"

    def test_critical(self):
        assert FlowRegime.CRITICAL.value == "critical"

    def test_supercritical(self):
        assert FlowRegime.SUPERCRITICAL.value == "supercritical"


# =====================================================================
#  16. Edge Cases and Robustness
# =====================================================================
class TestEdgeCases:
    """Extreme / degenerate inputs should not crash."""

    def test_very_large_depth(self, bc):
        Fr = bc.compute_froude_number(1e6, 1.0)
        assert np.isfinite(Fr)
        assert Fr < 1.0  # large h => small Fr

    def test_very_large_velocity(self, bc):
        Fr = bc.compute_froude_number(1.0, 1e6)
        assert np.isfinite(Fr)
        assert Fr > 1.0

    def test_critical_depth_large_q(self, bc):
        h_c, u_c = bc.apply_critical_depth_bc(Q=1e6, B=100.0)
        assert np.isfinite(h_c)
        assert np.isfinite(u_c)
        assert h_c > 0

    def test_subcritical_inlet_large_q(self, bc):
        h_bc, u_bc = bc.apply_subcritical_inlet(
            None, None, 5.0, 0.5,
            bc_value=1e4, bc_type="Q", B=100.0,
        )
        assert np.isfinite(h_bc)
        assert np.isfinite(u_bc)

    def test_transmissive_large_dt(self, bc):
        """Large dt may cause numerical issues; should still be finite."""
        h_bc, u_bc = bc.apply_transmissive_bc(
            h_interior=2.0, u_interior=1.0,
            h_prev=2.0, u_prev=1.0,
            dt=1000.0, dx=10.0,
        )
        assert np.isfinite(h_bc)
        assert np.isfinite(u_bc)

    def test_supercritical_inlet_zero_depth(self, bc):
        """h=0 at supercritical inlet."""
        h_bc, u_bc = bc.apply_supercritical_inlet(0.0, 10.0, B=10.0)
        assert h_bc == pytest.approx(0.0, abs=1e-10)
        # u_bc will be 0 because h < 1e-10
        assert u_bc == pytest.approx(0.0, abs=1e-10)

    def test_recover_from_equal_invariants(self, bc):
        """R+ = R- means u=R+, c=0, h=0."""
        h, u = bc.recover_from_riemann_invariants(5.0, 5.0)
        assert u == pytest.approx(5.0, rel=1e-10)
        assert h == pytest.approx(0.0, abs=1e-10)


# =====================================================================
#  17. Consistency between Inlet and Outlet
# =====================================================================
class TestConsistency:
    """Cross-checks between inlet and outlet BCs."""

    def test_inlet_outlet_match_at_steady_state(self, bc):
        """
        At steady state with uniform flow, the inlet Q should equal
        the outlet Q.
        """
        h_uniform = 2.0
        Q_steady = 20.0
        B = 10.0
        u_uniform = Q_steady / (B * h_uniform)

        # Apply inlet BC with Q
        h_in, u_in = bc.apply_subcritical_inlet(
            None, None, h_uniform, u_uniform,
            bc_value=Q_steady, bc_type="Q", B=B,
        )
        Q_in = u_in * h_in * B

        # Apply outlet BC with h
        h_out, u_out = bc.apply_subcritical_outlet(
            None, None, h_uniform, u_uniform,
            bc_value=h_uniform, bc_type="h",
        )
        Q_out = u_out * h_out * B

        # Both should produce approximately the same flow
        assert Q_in == pytest.approx(Q_steady, rel=0.05)
        assert Q_out == pytest.approx(Q_steady, rel=0.1)

    def test_critical_depth_is_unique(self, bc):
        """For given Q and B, critical depth is unique."""
        Q, B = 30.0, 10.0
        h_c1, u_c1 = bc.apply_critical_depth_bc(Q, B)
        h_c2, u_c2 = bc.apply_critical_depth_bc(Q, B)
        assert h_c1 == pytest.approx(h_c2, rel=1e-10)
        assert u_c1 == pytest.approx(u_c2, rel=1e-10)


if __name__ == "__main__":
    pytest.main([__file__, "-v", "-s"])
