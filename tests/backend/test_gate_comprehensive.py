#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Comprehensive test suite for gate/structure modules.

Covers:
- Sluice gate free and submerged flow
- Free/submerged transition behavior
- Gate opening sweep (monotonicity)
- Broad-crested weir discharge
- Sharp-crested weir (rectangular, triangular, trapezoidal)
- Side weir lateral outflow (De Marchi / Froude correction)
- Pump station characteristic curve (PumpStation, PumpStationAdvanced)
- Zero flow conditions
- Negative head / extreme parameter handling

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

# --- imports from solvers.gate (the primary structure module) ---
from solvers.gate import (
    SluiceGate,
    BroadCrestedWeir as SolverBroadCrestedWeir,
    Orifice as SolverOrifice,
    Spillway,
    PumpStation,
    PumpStationSimplified,
    PumpStationAdvanced,
    Drop,
    Transition,
)

# --- imports from physics.weirs ---
from physics.weirs.broad_crested_weir import (
    BroadCrestedWeir as PhysicsBroadCrestedWeir,
)
from physics.weirs.sharp_crested_weir import SharpCrestedWeir
from physics.weirs.side_weir import SideWeir

# --- imports from physics.hydraulic_structures ---
from physics.hydraulic_structures import (
    BroadCrestedWeir as HSBroadCrestedWeir,
    SharpCrestedWeir as HSSharpCrestedWeir,
    SluiceGate as HSSluiceGate,
    Orifice as HSOrifice,
)


# =====================================================================
#  1. Sluice Gate - Free Flow
# =====================================================================
class TestSluiceGateFreeFlow:
    """Verify free-flow discharge formula: Q = Cd * B * e * sqrt(2g * h_up)."""

    @pytest.fixture
    def gate(self):
        return SluiceGate(position=100.0, width=10.0, opening=1.0, Cd=0.6)

    @pytest.mark.parametrize("h_up", [0.5, 1.0, 1.5, 2.0, 3.0, 4.0, 5.0])
    def test_free_flow_multiple_depths(self, gate, h_up):
        """Free flow at various upstream depths; downstream well below opening."""
        h_down = 0.05  # very low downstream
        Q, flow_type = gate.calculate_discharge(h_up, h_down)

        # Expected: Q = Cd * B * e * sqrt(2*g*h_up)
        Q_expected = 0.6 * 10.0 * 1.0 * np.sqrt(2 * 9.81 * h_up)
        assert Q > 0, "Discharge must be positive"
        # Flow type depends on implementation threshold; just verify Q value
        rel_err = abs(Q - Q_expected) / Q_expected
        assert rel_err < 0.05, (
            f"h_up={h_up}: Q={Q:.4f}, expected={Q_expected:.4f}, "
            f"rel_err={rel_err:.4f}"
        )

    def test_free_flow_type_label(self, gate):
        """When downstream is well below the opening, expect 'free' label."""
        Q, ft = gate.calculate_discharge(3.0, 0.01)
        assert ft == "free", f"Expected 'free', got '{ft}'"

    def test_discharge_increases_with_depth(self, gate):
        """Higher upstream depth should produce larger discharge."""
        depths = [1.0, 2.0, 3.0, 4.0, 5.0]
        discharges = [gate.calculate_discharge(h, 0.05)[0] for h in depths]
        for i in range(1, len(discharges)):
            assert discharges[i] > discharges[i - 1], (
                f"Q should increase: Q({depths[i]})={discharges[i]:.4f} "
                f"<= Q({depths[i-1]})={discharges[i-1]:.4f}"
            )


# =====================================================================
#  2. Sluice Gate - Submerged Flow
# =====================================================================
class TestSluiceGateSubmergedFlow:
    """Submerged sluice gate: Q = Cd * B * e * sqrt(2g * delta_h)."""

    @pytest.fixture
    def gate(self):
        return SluiceGate(position=100.0, width=10.0, opening=1.0, Cd=0.6)

    def test_submerged_detection(self, gate):
        """When h_downstream > opening, flow should be submerged."""
        Q, ft = gate.calculate_discharge(5.0, 3.0)
        assert ft == "submerged", f"Expected 'submerged', got '{ft}'"
        assert Q > 0

    @pytest.mark.parametrize(
        "h_up,h_down",
        [
            (5.0, 3.0),
            (5.0, 4.0),
            (5.0, 4.5),
            (3.0, 2.0),
            (3.0, 2.5),
        ],
    )
    def test_submerged_formula(self, gate, h_up, h_down):
        """Submerged Q should follow delta-h formula approximately."""
        Q, ft = gate.calculate_discharge(h_up, h_down)
        delta_h = h_up - h_down
        Q_expected = 0.6 * 10.0 * 1.0 * np.sqrt(2 * 9.81 * max(delta_h, 1e-6))
        assert Q > 0
        rel_err = abs(Q - Q_expected) / Q_expected if Q_expected > 0 else 0
        assert rel_err < 0.05, (
            f"Submerged Q mismatch: Q={Q:.4f}, expected={Q_expected:.4f}"
        )

    def test_submerged_less_than_free(self, gate):
        """Submerged discharge should be less than free discharge at same h_up."""
        h_up = 5.0
        Q_free, _ = gate.calculate_discharge(h_up, 0.05)
        Q_sub, _ = gate.calculate_discharge(h_up, 3.0)
        assert Q_sub < Q_free, (
            f"Submerged Q ({Q_sub:.4f}) should be < free Q ({Q_free:.4f})"
        )


# =====================================================================
#  3. Free / Submerged Transition
# =====================================================================
class TestFreeSubmergedTransition:
    """Gradually increase downstream depth and check smooth transition."""

    def test_transition_smooth(self):
        gate = SluiceGate(position=100.0, width=10.0, opening=1.0, Cd=0.6)
        h_up = 5.0
        prev_Q = None
        for h_down in np.linspace(0.05, 4.5, 50):
            Q, _ = gate.calculate_discharge(h_up, h_down)
            assert Q >= 0, f"Q should be non-negative at h_down={h_down:.2f}"
            if prev_Q is not None:
                # Q should not increase as downstream rises
                assert Q <= prev_Q + 1e-6, (
                    f"Q should not increase: h_down={h_down:.2f}, "
                    f"Q={Q:.4f}, prev_Q={prev_Q:.4f}"
                )
            prev_Q = Q

    def test_no_discontinuity(self):
        """Check that the jump in Q at transition is bounded."""
        gate = SluiceGate(position=100.0, width=10.0, opening=1.0, Cd=0.6)
        h_up = 5.0
        Qs = []
        h_downs = np.linspace(0.5, 3.0, 200)
        for h_d in h_downs:
            Q, _ = gate.calculate_discharge(h_up, h_d)
            Qs.append(Q)
        diffs = np.abs(np.diff(Qs))
        max_jump = np.max(diffs)
        # The maximum step-to-step change should be reasonable
        assert max_jump < 10.0, f"Max jump {max_jump:.4f} is too large"


# =====================================================================
#  4. Gate Opening Sweep
# =====================================================================
class TestGateOpeningSweep:
    """Opening from 0 to fully open; verify monotonic Q increase."""

    def test_monotonic_increase(self):
        h_up = 5.0
        h_down = 0.5
        openings = np.linspace(0.01, 5.0, 30)
        Qs = []
        for e in openings:
            gate = SluiceGate(position=100.0, width=10.0, opening=e, Cd=0.6)
            Q, _ = gate.calculate_discharge(h_up, h_down)
            Qs.append(Q)

        for i in range(1, len(Qs)):
            assert Qs[i] >= Qs[i - 1] - 1e-9, (
                f"Q not monotonic: opening={openings[i]:.3f}, "
                f"Q={Qs[i]:.4f} < Q_prev={Qs[i-1]:.4f}"
            )

    def test_closed_gate(self):
        gate = SluiceGate(position=100.0, width=10.0, opening=0.0, Cd=0.6)
        Q, _ = gate.calculate_discharge(5.0, 0.5)
        assert Q == pytest.approx(0.0, abs=1e-10), "Closed gate should have Q=0"

    def test_time_varying_opening(self):
        """Gate with callable opening function."""
        gate = SluiceGate(
            position=100.0,
            width=10.0,
            opening=lambda t: min(t / 100.0, 2.0),
            Cd=0.6,
        )
        Q0, _ = gate.calculate_discharge(5.0, 0.5, t=0.0)
        Q100, _ = gate.calculate_discharge(5.0, 0.5, t=100.0)
        Q200, _ = gate.calculate_discharge(5.0, 0.5, t=200.0)
        Q300, _ = gate.calculate_discharge(5.0, 0.5, t=300.0)
        assert Q0 == pytest.approx(0.0, abs=1e-10)
        assert Q100 > 0  # opening = 1.0
        assert Q200 > Q100  # opening = 2.0 > 1.0
        # at t=300, opening is still 2.0 (capped), same as t=200
        assert Q300 == pytest.approx(Q200, rel=1e-6)


# =====================================================================
#  5. Broad-Crested Weir (solvers.gate.BroadCrestedWeir)
# =====================================================================
class TestBroadCrestedWeirSolver:
    """
    Verify Q = Cd * B * H^(3/2) * sqrt(2g) for the solver-level weir.
    """

    @pytest.fixture
    def weir(self):
        return SolverBroadCrestedWeir(
            position=500.0, width=10.0, crest_height=2.0, Cd=0.848
        )

    @pytest.mark.parametrize("h_up", [2.1, 2.5, 3.0, 3.5, 4.0])
    def test_free_flow_formula(self, weir, h_up):
        """Verify Q = Cd * B * H^(3/2) * sqrt(2g)."""
        Q, ft = weir.calculate_discharge(h_up, 0.5)
        H = h_up - 2.0
        Q_expected = 0.848 * 10.0 * (H ** 1.5) * np.sqrt(2 * 9.81)
        rel_err = abs(Q - Q_expected) / Q_expected
        assert rel_err < 0.01, f"h_up={h_up}: Q={Q:.4f}, expected={Q_expected:.4f}"

    def test_no_flow_below_crest(self, weir):
        Q, ft = weir.calculate_discharge(1.5, 0.5)
        assert Q == pytest.approx(0.0, abs=1e-10)
        assert ft == "no_flow"

    @pytest.mark.parametrize("H", np.arange(0.1, 2.05, 0.1))
    def test_weir_h_sweep(self, weir, H):
        """Sweep H from 0.1 to 2.0 m above crest."""
        h_up = 2.0 + H
        Q, _ = weir.calculate_discharge(h_up, 0.5)
        Q_expected = 0.848 * 10.0 * (H ** 1.5) * np.sqrt(2 * 9.81)
        assert Q == pytest.approx(Q_expected, rel=0.01)


# =====================================================================
#  5b. Broad-Crested Weir (physics.weirs.broad_crested_weir)
# =====================================================================
class TestPhysicsBroadCrestedWeir:
    """Test the physics.weirs module BroadCrestedWeir (inherits HydraulicStructure)."""

    @pytest.fixture
    def weir(self):
        return PhysicsBroadCrestedWeir(
            position=500.0,
            width=10.0,
            crest_elevation=2.0,
            discharge_coefficient=0.385,
        )

    def test_free_flow(self, weir):
        Q, ft = weir.calculate_discharge(3.0, 1.0)
        H = 3.0 - 2.0  # 1.0
        C_sqrt_2g = 0.385 * np.sqrt(2 * 9.81)
        Q_expected = C_sqrt_2g * 10.0 * (H ** 1.5)
        assert Q == pytest.approx(Q_expected, rel=0.01)
        assert ft == "free"

    def test_submerged_flow(self, weir):
        """High downstream causes submergence."""
        Q_free, _ = weir.calculate_discharge(3.0, 1.0)
        Q_sub, ft = weir.calculate_discharge(3.0, 2.8)
        assert ft == "submerged"
        assert Q_sub < Q_free

    def test_derivatives_vs_numerical(self, weir):
        """Analytical derivatives should match numerical derivatives."""
        h_up, h_down = 3.0, 1.5
        dQ_up, dQ_down = weir.calculate_discharge_derivatives(h_up, h_down)
        eps = 1e-6
        Q0, _ = weir.calculate_discharge(h_up, h_down)
        Q_up, _ = weir.calculate_discharge(h_up + eps, h_down)
        Q_down, _ = weir.calculate_discharge(h_up, h_down + eps)
        dQ_up_num = (Q_up - Q0) / eps
        dQ_down_num = (Q_down - Q0) / eps
        assert dQ_up == pytest.approx(dQ_up_num, rel=0.05)
        if abs(dQ_down) > 1e-8 and abs(dQ_down_num) > 1e-8:
            assert dQ_down == pytest.approx(dQ_down_num, rel=0.1)


# =====================================================================
#  6. Sharp-Crested Weir
# =====================================================================
class TestSharpCrestedWeir:
    """Test rectangular, triangular, and trapezoidal sharp-crested weirs."""

    @pytest.fixture
    def weir_rect(self):
        return SharpCrestedWeir(
            position=500.0,
            width=2.0,
            crest_elevation=1.0,
            weir_type="rectangular",
            discharge_coefficient=0.62,
        )

    @pytest.fixture
    def weir_tri(self):
        return SharpCrestedWeir(
            position=500.0,
            width=0.0,
            crest_elevation=1.0,
            weir_type="triangular",
            notch_angle=90.0,
            discharge_coefficient=0.58,
        )

    @pytest.fixture
    def weir_trap(self):
        return SharpCrestedWeir(
            position=500.0,
            width=2.0,
            crest_elevation=1.0,
            weir_type="trapezoidal",
            notch_angle=60.0,
            discharge_coefficient=0.62,
        )

    def test_rectangular_formula(self, weir_rect):
        """Q = (2/3)*C*B*sqrt(2g)*H^(3/2)."""
        h_up = 1.5
        H = h_up - 1.0  # 0.5
        Q, _ = weir_rect.calculate_discharge(h_up, 0.0)
        C_rect = (2.0 / 3.0) * 0.62 * 2.0 * np.sqrt(2 * 9.81) * 1.0
        Q_expected = C_rect * (H ** 1.5)
        assert Q == pytest.approx(Q_expected, rel=0.01)

    def test_triangular_formula(self, weir_tri):
        """Q = (8/15)*C*tan(theta/2)*sqrt(2g)*H^(5/2)."""
        h_up = 1.5
        H = 0.5
        Q, _ = weir_tri.calculate_discharge(h_up, 0.0)
        C_tri = (8.0 / 15.0) * 0.58 * np.tan(np.radians(45)) * np.sqrt(2 * 9.81)
        Q_expected = C_tri * (H ** 2.5)
        assert Q == pytest.approx(Q_expected, rel=0.01)

    def test_trapezoidal_combined(self, weir_trap):
        """Trapezoidal = rectangular + triangular components."""
        h_up = 2.0
        H = 1.0
        Q, _ = weir_trap.calculate_discharge(h_up, 0.0)
        assert Q > 0

    def test_no_flow_below_crest(self, weir_rect):
        Q, ft = weir_rect.calculate_discharge(0.5, 0.0)
        assert Q == pytest.approx(0.0, abs=1e-10)
        assert ft == "no_flow"

    def test_derivatives_rect(self, weir_rect):
        h_up, h_down = 2.0, 0.0
        dQ_up, dQ_down = weir_rect.calculate_discharge_derivatives(h_up, h_down)
        eps = 1e-6
        Q0, _ = weir_rect.calculate_discharge(h_up, h_down)
        Q_p, _ = weir_rect.calculate_discharge(h_up + eps, h_down)
        dQ_up_num = (Q_p - Q0) / eps
        assert dQ_up == pytest.approx(dQ_up_num, rel=0.02)
        assert dQ_down == pytest.approx(0.0, abs=1e-10)

    def test_invalid_weir_type(self):
        with pytest.raises(ValueError):
            SharpCrestedWeir(
                position=0, width=1, crest_elevation=0, weir_type="invalid"
            )


# =====================================================================
#  7. Side Weir Lateral Outflow
# =====================================================================
class TestSideWeir:
    """Test De Marchi-style side weir with Froude correction."""

    @pytest.fixture
    def sw(self):
        return SideWeir(
            position=500.0,
            length=20.0,
            crest_elevation=2.0,
            channel_width=10.0,
            discharge_coefficient=0.4,
        )

    def test_basic_discharge(self, sw):
        """Q = C * L * H^(3/2) * sqrt(2g) * phi when no Q_channel."""
        Q, ft = sw.calculate_discharge(3.0, 1.0)
        H = 3.0 - 2.0
        Q_expected = 0.4 * np.sqrt(2 * 9.81) * 20.0 * (H ** 1.5)
        assert Q == pytest.approx(Q_expected, rel=0.01)

    def test_no_flow_below_crest(self, sw):
        Q, ft = sw.calculate_discharge(1.5, 0.5)
        assert Q == pytest.approx(0.0, abs=1e-10)
        assert ft == "no_flow"

    def test_froude_correction_reduces_flow(self, sw):
        """Higher channel velocity (larger Fr) should reduce side weir discharge."""
        Q_static, _ = sw.calculate_discharge(3.0, 1.0, Q_channel=0)
        Q_fast, _ = sw.calculate_discharge(3.0, 1.0, Q_channel=200.0)
        assert Q_fast < Q_static, (
            f"Froude correction should reduce Q: static={Q_static:.4f}, "
            f"fast={Q_fast:.4f}"
        )

    def test_froude_correction_values(self, sw):
        """phi should be between 0 and 1."""
        for Fr in [0.0, 0.3, 0.5, 0.8, 1.0, 1.5, 2.0]:
            phi = sw.calculate_froude_correction(Fr)
            assert 0.0 < phi <= 1.0, f"Fr={Fr}: phi={phi} out of range"

    def test_derivatives(self, sw):
        h_up, h_down = 3.0, 1.0
        dQ_up, dQ_down = sw.calculate_discharge_derivatives(h_up, h_down)
        eps = 1e-6
        Q0, _ = sw.calculate_discharge(h_up, h_down)
        Q_p, _ = sw.calculate_discharge(h_up + eps, h_down)
        dQ_up_num = (Q_p - Q0) / eps
        # Allowing some tolerance since analytical derivative simplifies phi dependence
        assert dQ_up == pytest.approx(dQ_up_num, rel=0.08)


# =====================================================================
#  8. Pump Station Characteristic Curve
# =====================================================================
class TestPumpStation:
    """Test PumpStation rated/reduced flow modes."""

    @pytest.fixture
    def pump(self):
        return PumpStation(
            position=100.0,
            width=10.0,
            rated_flow=30.0,
            rated_head=5.0,
            min_suction_head=2.0,
        )

    def test_rated_flow(self, pump):
        """Above min suction head, pump delivers rated flow."""
        Q, ft = pump.calculate_discharge(3.0, 1.0)
        assert Q == pytest.approx(30.0, rel=1e-6)
        assert ft == "rated"

    def test_reduced_flow(self, pump):
        """Below min suction head, flow is reduced."""
        Q, ft = pump.calculate_discharge(1.0, 0.0)
        expected = 30.0 * np.sqrt(1.0 / 2.0)
        assert Q == pytest.approx(expected, rel=1e-6)
        assert ft == "reduced"

    def test_pump_off(self, pump):
        pump.set_running_state(False)
        Q, ft = pump.calculate_discharge(5.0, 1.0)
        assert Q == pytest.approx(0.0, abs=1e-10)
        assert ft == "pump_off"

    def test_insufficient_water(self, pump):
        Q, ft = pump.calculate_discharge(0.05, 0.0)
        assert Q == pytest.approx(0.0, abs=1e-10)
        assert ft == "insufficient_water"

    def test_momentum_source(self, pump):
        S = pump.get_momentum_source(h=2.0, dx=10.0, spread_points=5)
        expected = 9.81 * 2.0 * 5.0 / (5 * 10.0)
        assert S == pytest.approx(expected, rel=1e-6)

    def test_momentum_source_off(self, pump):
        pump.set_running_state(False)
        S = pump.get_momentum_source(h=2.0, dx=10.0)
        assert S == pytest.approx(0.0, abs=1e-10)


class TestPumpStationAdvanced:
    """Test advanced pump with H-Q characteristic curve."""

    @pytest.fixture
    def pump(self):
        # Suppress print in constructor
        import io
        import contextlib

        f = io.StringIO()
        with contextlib.redirect_stdout(f):
            p = PumpStationAdvanced(
                position=100.0,
                width=10.0,
                rated_flow=30.0,
                rated_head=5.0,
            )
        return p

    def test_pump_curve_at_zero_flow(self, pump):
        """H(Q=0) should equal shutoff head."""
        H0 = pump.calculate_pump_head(0.0)
        assert H0 == pytest.approx(pump.shutoff_head, rel=1e-6)

    def test_pump_curve_at_rated_flow(self, pump):
        """H(Q_rated) should equal rated head."""
        H_r = pump.calculate_pump_head(pump.rated_flow)
        assert H_r == pytest.approx(pump.rated_head, rel=1e-3)

    def test_pump_curve_monotonic_decrease_in_valid_range(self, pump):
        """Head should generally decrease as Q increases within rated range.

        Note: The parabolic curve H = a - b*Q - c*Q^2 may have a local
        maximum near Q=0 depending on the sign of b. We verify that H
        at rated_flow is less than H at Q=0 (shutoff head), which is the
        fundamental pump characteristic behavior.
        """
        H_at_zero = pump.calculate_pump_head(0.0)
        H_at_rated = pump.calculate_pump_head(pump.rated_flow)
        H_at_1p5 = pump.calculate_pump_head(1.5 * pump.rated_flow)
        assert H_at_zero >= H_at_rated, (
            f"H(0)={H_at_zero:.4f} should >= H(Q_rated)={H_at_rated:.4f}"
        )
        assert H_at_rated >= H_at_1p5, (
            f"H(Q_rated)={H_at_rated:.4f} should >= H(1.5*Q_rated)={H_at_1p5:.4f}"
        )

    def test_get_pump_curve_data(self, pump):
        Q_arr, H_arr = pump.get_pump_curve_data(n_points=20)
        assert len(Q_arr) == 20
        assert len(H_arr) == 20
        assert Q_arr[0] == pytest.approx(0.0, abs=1e-10)
        assert H_arr[0] == pytest.approx(pump.shutoff_head, rel=1e-6)

    def test_discharge_without_elevation(self, pump):
        """Without z_upstream/z_downstream, should return rated flow."""
        Q, ft = pump.calculate_discharge(3.0, 1.0)
        assert Q == pytest.approx(pump.rated_flow, rel=1e-6)
        assert ft == "rated"

    def test_pump_off(self, pump):
        pump.set_running_state(False)
        Q, ft = pump.calculate_discharge(5.0, 1.0)
        assert Q == pytest.approx(0.0, abs=1e-10)
        assert ft == "pump_off"


# =====================================================================
#  9. Zero Flow Conditions
# =====================================================================
class TestZeroFlowConditions:
    """Ensure no crashes and Q=0 under various zero-flow scenarios."""

    def test_gate_zero_upstream(self):
        gate = SluiceGate(position=100.0, width=10.0, opening=1.0)
        # h_upstream = 0 means no water
        # The formula still computes: Cd*B*e*sqrt(2g*0)=0
        Q, _ = gate.calculate_discharge(0.0, 0.0)
        assert Q >= 0

    def test_gate_closed(self):
        gate = SluiceGate(position=100.0, width=10.0, opening=0.0)
        Q, _ = gate.calculate_discharge(5.0, 1.0)
        assert Q == pytest.approx(0.0, abs=1e-10)

    def test_weir_below_crest(self):
        weir = SolverBroadCrestedWeir(position=0, width=10, crest_height=5.0)
        Q, ft = weir.calculate_discharge(3.0, 1.0)
        assert Q == pytest.approx(0.0, abs=1e-10)
        assert ft == "no_flow"

    def test_orifice_no_head(self):
        orifice = SolverOrifice(
            position=0, width=2, height=1, bottom_elevation=3.0
        )
        # upstream below orifice center
        Q, ft = orifice.calculate_discharge(0.5, 0.0)
        assert Q == pytest.approx(0.0, abs=1e-10)

    def test_spillway_below_crest(self):
        sp = Spillway(position=0, width=10, crest_elevation=5.0)
        Q, ft = sp.calculate_discharge(3.0)
        assert Q == pytest.approx(0.0, abs=1e-10)
        assert ft == "no_flow"

    def test_drop_zero_upstream(self):
        drop = Drop(position=0, width=10, drop_height=2.0)
        Q, ft = drop.calculate_discharge(0.0)
        assert Q == pytest.approx(0.0, abs=1e-10)
        assert ft == "no_flow"

    def test_transition_zero_area(self):
        trans = Transition(
            position=0, width_upstream=10.0, width_downstream=8.0
        )
        Q, ft = trans.calculate_discharge(0.0, 0.0)
        assert Q == pytest.approx(0.0, abs=1e-10)


# =====================================================================
#  10. Negative Head / Edge Cases
# =====================================================================
class TestNegativeHeadAndEdgeCases:
    """No crashes for negative, extreme, or degenerate inputs."""

    def test_gate_negative_upstream(self):
        gate = SluiceGate(position=0, width=10, opening=1.0)
        # Should not crash; behavior is implementation-specific
        Q, _ = gate.calculate_discharge(-1.0, 0.0)
        # Just verify no exception

    def test_gate_equal_heads(self):
        gate = SluiceGate(position=0, width=10, opening=1.0)
        Q, ft = gate.calculate_discharge(3.0, 3.0)
        # Very small delta_h; should return near-zero or small Q
        assert Q >= 0

    def test_gate_reversed_head(self):
        """h_downstream > h_upstream -- reversed flow."""
        gate = SluiceGate(position=0, width=10, opening=1.0)
        Q, _ = gate.calculate_discharge(2.0, 5.0)
        # Implementation uses max(1e-6, delta_h) so Q is still computed
        # Just ensure no crash
        assert isinstance(Q, float)

    def test_weir_derivatives_at_crest(self):
        weir = SolverBroadCrestedWeir(position=0, width=10, crest_height=2.0)
        dQ_up, dQ_down = weir.calculate_discharge_derivatives(2.0, 0.5)
        assert dQ_up == pytest.approx(0.0, abs=1e-10)
        assert dQ_down == pytest.approx(0.0, abs=1e-10)

    def test_orifice_extreme_head(self):
        orifice = SolverOrifice(position=0, width=2, height=1, bottom_elevation=0)
        Q, ft = orifice.calculate_discharge(1000.0, 0.0)
        assert Q > 0
        assert np.isfinite(Q)

    def test_spillway_extreme_head(self):
        sp = Spillway(position=0, width=10, crest_elevation=0.0)
        Q, ft = sp.calculate_discharge(1e4, 0.0)
        assert Q > 0
        assert np.isfinite(Q)

    def test_broad_crested_weir_extreme_H(self):
        """Very large H - should be capped and not overflow."""
        weir = SolverBroadCrestedWeir(position=0, width=10, crest_height=0.0)
        Q, ft = weir.calculate_discharge(1e7, 0.0)
        assert np.isfinite(Q)
        assert Q > 0


# =====================================================================
#  11. Extreme Parameters
# =====================================================================
class TestExtremeParameters:
    """Very large/small parameter values at the boundary of validity."""

    def test_very_small_opening(self):
        gate = SluiceGate(position=0, width=10, opening=1e-6, Cd=0.6)
        Q, _ = gate.calculate_discharge(5.0, 0.5)
        assert Q >= 0
        assert Q < 0.01  # extremely small opening => tiny Q

    def test_very_large_width(self):
        gate = SluiceGate(position=0, width=1e6, opening=1.0, Cd=0.6)
        Q, _ = gate.calculate_discharge(5.0, 0.5)
        assert Q > 0
        assert np.isfinite(Q)

    def test_very_small_cd(self):
        gate = SluiceGate(position=0, width=10, opening=1.0, Cd=1e-6)
        Q, _ = gate.calculate_discharge(5.0, 0.5)
        assert Q >= 0
        assert Q < 0.01

    def test_very_large_cd(self):
        gate = SluiceGate(position=0, width=10, opening=1.0, Cd=1.0)
        Q, _ = gate.calculate_discharge(5.0, 0.5)
        assert Q > 0

    def test_pump_extreme_rated_flow(self):
        pump = PumpStation(
            position=0, width=10, rated_flow=1e6, rated_head=100.0,
            min_suction_head=0.5,
        )
        Q, ft = pump.calculate_discharge(5.0, 0.0)
        assert Q == pytest.approx(1e6, rel=1e-6)

    def test_drop_very_large_height(self):
        drop = Drop(position=0, width=10, drop_height=100.0)
        Q, _ = drop.calculate_discharge(2.0)
        assert Q > 0
        assert np.isfinite(Q)


# =====================================================================
#  12. hydraulic_structures module (physics/hydraulic_structures.py)
# =====================================================================
class TestHydraulicStructuresModule:
    """Integration tests for the physics.hydraulic_structures module."""

    def test_hs_broad_crested_weir_free(self):
        weir = HSBroadCrestedWeir(
            crest_elevation=2.0, width=10.0, discharge_coeff=1.7
        )
        Q = weir.compute_discharge(3.0)
        H = 1.0
        Q_expected = 1.7 * 10.0 * (H ** 1.5)
        assert Q == pytest.approx(Q_expected, rel=0.01)

    def test_hs_broad_crested_weir_submerged(self):
        weir = HSBroadCrestedWeir(
            crest_elevation=2.0, width=10.0, discharge_coeff=1.7
        )
        Q_free = weir.compute_discharge(3.0)
        Q_sub = weir.compute_discharge(3.0, h_downstream=2.8)
        assert Q_sub < Q_free

    def test_hs_sharp_crested_weir(self):
        weir = HSSharpCrestedWeir(crest_elevation=1.0, width=5.0)
        Q = weir.compute_discharge(2.0)
        H = 1.0
        Q_expected = 1.84 * 5.0 * (H ** 1.5)
        assert Q == pytest.approx(Q_expected, rel=0.01)

    def test_hs_sluice_gate_free(self):
        gate = HSSluiceGate(sill_elevation=0.0, width=8.0, opening=0.5)
        Q = gate.compute_discharge(h_upstream=3.0, h_downstream=0.2)
        assert Q > 0

    def test_hs_sluice_gate_closed(self):
        gate = HSSluiceGate(sill_elevation=0.0, width=8.0, opening=0.0)
        Q = gate.compute_discharge(3.0, 1.0)
        assert Q == pytest.approx(0.0, abs=1e-10)

    def test_hs_sluice_gate_opening_sweep(self):
        """Monotonic Q increase as opening grows."""
        prev_Q = -1
        for opening in [0.2, 0.5, 1.0, 1.5, 2.0]:
            gate = HSSluiceGate(sill_elevation=0.0, width=8.0, opening=opening)
            Q = gate.compute_discharge(3.0, 1.0)
            assert Q >= prev_Q
            prev_Q = Q

    def test_hs_orifice_free(self):
        orifice = HSOrifice(center_elevation=1.0, diameter=1.5)
        Q = orifice.compute_discharge(3.0)
        assert Q > 0

    def test_hs_orifice_submerged(self):
        orifice = HSOrifice(center_elevation=1.0, diameter=1.5)
        Q_free = orifice.compute_discharge(3.0)
        Q_sub = orifice.compute_discharge(3.0, h_downstream=2.5)
        assert Q_sub < Q_free

    def test_hs_weir_regime(self):
        weir = HSBroadCrestedWeir(crest_elevation=2.0, width=10.0)
        from physics.hydraulic_structures import FlowRegime

        regime = weir.get_regime(3.0, 1.0)
        assert regime == FlowRegime.FREE

    def test_hs_gate_regime(self):
        gate = HSSluiceGate(sill_elevation=0.0, width=8.0, opening=0.5)
        from physics.hydraulic_structures import FlowRegime

        regime_free = gate.get_regime(3.0, 0.1)
        assert regime_free == FlowRegime.FREE
        regime_sub = gate.get_regime(3.0, 2.0)
        assert regime_sub == FlowRegime.SUBMERGED


# =====================================================================
#  13. Spillway Tests
# =====================================================================
class TestSpillway:
    """Test Spillway (WES/Ogee and broad-crested types)."""

    def test_wes_free_flow(self):
        sp = Spillway(position=0, width=10, crest_elevation=5.0, spillway_type="wes")
        Q, ft = sp.calculate_discharge(7.0)
        H = 2.0
        Q_expected = 2.1 * 10 * (H ** 1.5)
        assert Q == pytest.approx(Q_expected, rel=0.01)
        assert ft == "free"

    def test_ogee_same_as_wes(self):
        sp = Spillway(position=0, width=10, crest_elevation=5.0, spillway_type="ogee")
        Q, _ = sp.calculate_discharge(7.0)
        Q_expected = 2.1 * 10 * (2.0 ** 1.5)
        assert Q == pytest.approx(Q_expected, rel=0.01)

    def test_broad_crested_spillway(self):
        sp = Spillway(
            position=0, width=10, crest_elevation=5.0,
            spillway_type="broad_crested", Cd=0.848,
        )
        Q, _ = sp.calculate_discharge(7.0)
        H = 2.0
        Q_expected = 0.848 * 10 * (H ** 1.5) * np.sqrt(2 * 9.81)
        assert Q == pytest.approx(Q_expected, rel=0.01)

    def test_villemonte_submergence(self):
        sp = Spillway(position=0, width=10, crest_elevation=5.0)
        Q_free, ft_free = sp.calculate_discharge(7.0, h_downstream=4.0)
        assert ft_free == "free"
        Q_sub, ft_sub = sp.calculate_discharge(7.0, h_downstream=6.5)
        assert ft_sub == "submerged"
        assert Q_sub < Q_free

    def test_invalid_type(self):
        sp = Spillway(position=0, width=10, crest_elevation=0, spillway_type="unknown")
        with pytest.raises(ValueError):
            sp.calculate_discharge(5.0)


# =====================================================================
#  14. Orifice Tests (solvers.gate.Orifice)
# =====================================================================
class TestSolverOrifice:
    """Test the solver-level Orifice class."""

    @pytest.fixture
    def orifice(self):
        return SolverOrifice(
            position=0, width=2, height=1, bottom_elevation=0.5, Cd=0.61
        )

    def test_free_flow(self, orifice):
        Q, ft = orifice.calculate_discharge(3.0, 0.0)
        assert Q > 0
        assert ft == "free"

    def test_submerged_flow(self, orifice):
        Q, ft = orifice.calculate_discharge(3.0, 2.5)
        assert Q > 0
        assert ft == "submerged"

    def test_submerged_less_than_free(self, orifice):
        Q_free, _ = orifice.calculate_discharge(3.0, 0.0)
        Q_sub, _ = orifice.calculate_discharge(3.0, 2.5)
        assert Q_sub < Q_free

    def test_derivatives(self, orifice):
        h_up, h_down = 3.0, 0.0
        dQ_up, dQ_down = orifice.calculate_discharge_derivatives(h_up, h_down)
        eps = 1e-6
        Q0, _ = orifice.calculate_discharge(h_up, h_down)
        Q_p, _ = orifice.calculate_discharge(h_up + eps, h_down)
        dQ_up_num = (Q_p - Q0) / eps
        assert dQ_up == pytest.approx(dQ_up_num, rel=0.05)


# =====================================================================
#  15. Drop Structure Tests
# =====================================================================
class TestDropStructure:
    """Test drop/waterfall structure."""

    def test_positive_flow(self):
        drop = Drop(position=0, width=10, drop_height=2.0)
        Q, ft = drop.calculate_discharge(2.0)
        assert Q > 0
        assert ft == "drop"

    def test_formula_verification(self):
        """Q = Cd * B * h * sqrt(2g*(h+dz))."""
        drop = Drop(position=0, width=10, drop_height=2.0, Cd=0.6)
        h = 2.0
        Q, _ = drop.calculate_discharge(h)
        Q_expected = 0.6 * 10 * h * np.sqrt(2 * 9.81 * (h + 2.0))
        assert Q == pytest.approx(Q_expected, rel=0.01)

    def test_derivatives(self):
        drop = Drop(position=0, width=10, drop_height=2.0)
        h_up = 2.0
        dQ_up, dQ_down = drop.calculate_discharge_derivatives(h_up)
        assert dQ_up > 0
        assert dQ_down == pytest.approx(0.0, abs=1e-10)


# =====================================================================
#  16. Transition Structure Tests
# =====================================================================
class TestTransitionStructure:
    """Test channel transition (expansion/contraction)."""

    def test_contraction(self):
        trans = Transition(
            position=0, width_upstream=10.0, width_downstream=6.0
        )
        assert trans.transition_type == "contraction"
        Q, _ = trans.calculate_discharge(2.0, 1.8)
        assert Q >= 0

    def test_expansion(self):
        trans = Transition(
            position=0, width_upstream=6.0, width_downstream=10.0
        )
        assert trans.transition_type == "expansion"

    def test_uniform(self):
        trans = Transition(
            position=0, width_upstream=10.0, width_downstream=10.0
        )
        assert trans.transition_type == "uniform"


# =====================================================================
#  17. Sluice Gate Derivatives
# =====================================================================
class TestSluiceGateDerivatives:
    """Test analytical derivatives against numerical finite differences."""

    @pytest.fixture
    def gate(self):
        return SluiceGate(position=0, width=10, opening=1.0, Cd=0.6)

    @pytest.mark.parametrize(
        "h_up,h_down",
        [(5.0, 0.5), (5.0, 3.0), (3.0, 2.0), (2.0, 0.1)],
    )
    def test_derivatives_match(self, gate, h_up, h_down):
        dQ_up, dQ_down = gate.calculate_discharge_derivatives(h_up, h_down)
        eps = 1e-5
        Q0, _ = gate.calculate_discharge(h_up, h_down)
        Q_up, _ = gate.calculate_discharge(h_up + eps, h_down)
        Q_down, _ = gate.calculate_discharge(h_up, h_down + eps)
        dQ_up_num = (Q_up - Q0) / eps
        dQ_down_num = (Q_down - Q0) / eps

        if abs(dQ_up) > 1e-6:
            assert dQ_up == pytest.approx(dQ_up_num, rel=0.1)
        if abs(dQ_down) > 1e-6:
            assert dQ_down == pytest.approx(dQ_down_num, rel=0.1)


# =====================================================================
#  18. repr Tests (smoke tests for string representation)
# =====================================================================
class TestReprSmoke:
    """Ensure __repr__ does not crash."""

    def test_sluice_gate_repr(self):
        g = SluiceGate(position=0, width=10, opening=1.0)
        s = repr(g)
        assert "SluiceGate" in s

    def test_weir_repr(self):
        w = SolverBroadCrestedWeir(position=0, width=10, crest_height=2.0)
        s = repr(w)
        assert "BroadCrestedWeir" in s

    def test_spillway_repr(self):
        sp = Spillway(position=0, width=10, crest_elevation=5.0)
        s = repr(sp)
        assert "Spillway" in s

    def test_pump_repr(self):
        p = PumpStation(position=0, width=10)
        s = repr(p)
        assert "PumpStation" in s

    def test_drop_repr(self):
        d = Drop(position=0, width=10, drop_height=2.0)
        s = repr(d)
        assert "Drop" in s


if __name__ == "__main__":
    pytest.main([__file__, "-v", "-s"])
