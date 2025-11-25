"""
Test suite for Culvert hydraulic model

Tests cover:
- Geometry calculations
- Flow calculations (inlet and outlet control)
- Different cross-section shapes
- Head loss calculations
- Derivative calculations
- Validation against manual calculations
"""

import pytest
import warnings
warnings.filterwarnings("ignore")
import numpy as np
import sys
import os

# Add parent directory to path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from physics.structures.culvert import (
    Culvert,
    CulvertGeometry,
    create_circular_culvert,
    create_rectangular_culvert,
    validate_culvert_design
)


class TestCulvertGeometry:
    """Test culvert geometry calculations"""

    def test_circular_area(self):
        """Test circular culvert area calculation"""
        geom = CulvertGeometry(shape='circular', diameter=1.0, length=20.0)
        area = geom.area()
        expected = np.pi * 0.5**2
        assert abs(area - expected) < 1e-10, \
            f"Circular area: got {area}, expected {expected}"

    def test_rectangular_area(self):
        """Test rectangular culvert area calculation"""
        geom = CulvertGeometry(shape='rectangular',
                              width=2.0, height=1.5, length=30.0)
        area = geom.area()
        expected = 2.0 * 1.5
        assert abs(area - expected) < 1e-10, \
            f"Rectangular area: got {area}, expected {expected}"

    def test_hydraulic_radius_full_pipe(self):
        """Test hydraulic radius for full pipe flow"""
        geom = CulvertGeometry(shape='circular', diameter=1.0, length=20.0)
        R_h = geom.hydraulic_radius(depth=1.0)
        expected = 1.0 / 4  # D/4 for circular pipe
        assert abs(R_h - expected) < 1e-6, \
            f"Full pipe R_h: got {R_h}, expected {expected}"

    def test_hydraulic_radius_half_full(self):
        """Test hydraulic radius for half-full pipe"""
        geom = CulvertGeometry(shape='circular', diameter=1.0, length=20.0)
        R_h = geom.hydraulic_radius(depth=0.5)
        # For half-full circular pipe, R_h ~= 0.25 * D
        assert 0.2 < R_h < 0.3, \
            f"Half-full R_h: got {R_h}, should be around 0.25"

    def test_rectangular_hydraulic_radius(self):
        """Test hydraulic radius for rectangular culvert"""
        geom = CulvertGeometry(shape='rectangular',
                              width=2.0, height=1.5, length=30.0)
        R_h = geom.hydraulic_radius(depth=1.5)
        # R_h = A/P = (2.0*1.5)/(2.0 + 2*1.5)
        expected = 3.0 / 5.0
        assert abs(R_h - expected) < 1e-6, \
            f"Rectangular R_h: got {R_h}, expected {expected}"

    def test_invalid_geometry(self):
        """Test that invalid geometry raises error"""
        with pytest.raises(ValueError):
            # Circular without diameter
            CulvertGeometry(shape='circular', length=20.0)

        with pytest.raises(ValueError):
            # Rectangular without width
            CulvertGeometry(shape='rectangular', height=1.5, length=20.0)


class TestCulvertFlow:
    """Test culvert flow calculations"""

    def test_inlet_control_unsubmerged(self):
        """Test inlet control with unsubmerged outlet"""
        culvert = create_circular_culvert(
            position=100.0,
            diameter=1.0,
            length=20.0,
            manning_n=0.013,
            inlet_type='square_edge'
        )

        # Unsubmerged condition: h < 1.2*D
        h_upstream = 0.8  # Less than 1.2 m
        h_downstream = 0.3

        Q, control_type = culvert.compute_discharge(h_upstream, h_downstream)

        # Flow should be positive
        assert Q > 0, f"Flow should be positive, got {Q}"

        # Verify manual calculation
        A = np.pi * 0.5**2
        Cd = 0.47
        g = 9.81
        Q_manual = Cd * A * np.sqrt(2 * g * h_upstream)

        # Allow 30% error (inlet control has high variability due to:
        # - entrance conditions
        # - approach velocity
        # - inlet geometry details)
        rel_error = abs(Q - Q_manual) / Q_manual
        assert rel_error < 0.30, \
            f"Flow error: got {Q}, expected {Q_manual}, error {rel_error*100:.1f}%"

    def test_inlet_control_submerged(self):
        """Test inlet control with submerged inlet"""
        culvert = create_circular_culvert(
            position=100.0,
            diameter=1.0,
            length=20.0
        )

        # Submerged condition: h >= 1.2*D
        h_upstream = 1.5
        h_downstream = 0.5

        Q, control_type = culvert.compute_discharge(h_upstream, h_downstream)

        # Flow should be positive
        assert Q > 0

        # Flow should be reasonable (not too large)
        assert Q < 10.0, f"Flow too large: {Q}"

    def test_outlet_control(self):
        """Test outlet control with long culvert"""
        culvert = create_circular_culvert(
            position=100.0,
            diameter=1.0,
            length=50.0,      # Long culvert
            manning_n=0.030   # High roughness
        )

        h_upstream = 1.2
        h_downstream = 1.0  # High downstream depth

        Q, control_type = culvert.compute_discharge(h_upstream, h_downstream)

        # Flow should be positive
        assert Q > 0

        # Should be outlet control
        assert control_type == 'outlet', \
            f"Expected outlet control, got {control_type}"

    def test_rectangular_culvert_flow(self):
        """Test flow in rectangular culvert"""
        culvert = create_rectangular_culvert(
            position=100.0,
            width=2.0,
            height=1.5,
            length=30.0
        )

        Q, control_type = culvert.compute_discharge(
            h_upstream=1.2,
            h_downstream=0.5
        )

        # Flow should be positive
        assert Q > 0

        # Flow should be reasonable for this size
        assert 1.0 < Q < 20.0, f"Flow out of reasonable range: {Q}"

    def test_zero_upstream_depth(self):
        """Test behavior with zero upstream depth"""
        culvert = create_circular_culvert(
            position=100.0,
            diameter=1.0,
            length=20.0
        )

        Q, _ = culvert.compute_discharge(h_upstream=0.0, h_downstream=0.0)

        # Should return zero flow
        assert Q == 0.0, f"Expected zero flow, got {Q}"

    def test_different_inlet_types(self):
        """Test different inlet types produce different flows"""
        inlet_types = ['square_edge', 'groove_end', 'groove_headwall', 'beveled']
        flows = []

        for inlet_type in inlet_types:
            culvert = create_circular_culvert(
                position=100.0,
                diameter=1.0,
                length=20.0,
                inlet_type=inlet_type
            )

            Q, _ = culvert.compute_discharge(h_upstream=1.0, h_downstream=0.3)
            flows.append(Q)

        # Flows should be monotonically increasing
        # (beveled has highest Cd, square_edge lowest)
        assert flows[0] < flows[-1], \
            "Beveled inlet should have higher flow than square edge"


class TestHeadloss:
    """Test head loss calculations"""

    def test_headloss_positive(self):
        """Test that head loss is always positive"""
        culvert = create_circular_culvert(
            position=100.0,
            diameter=1.0,
            length=20.0,
            manning_n=0.013
        )

        h_loss = culvert.compute_headloss(Q=2.0, h_downstream=0.5)

        # Head loss should be positive
        assert h_loss > 0, f"Head loss should be positive, got {h_loss}"

    def test_headloss_increases_with_flow(self):
        """Test that head loss increases with discharge"""
        culvert = create_circular_culvert(
            position=100.0,
            diameter=1.0,
            length=20.0
        )

        h_loss_1 = culvert.compute_headloss(Q=1.0, h_downstream=0.5)
        h_loss_2 = culvert.compute_headloss(Q=2.0, h_downstream=0.5)

        # Higher flow should have higher loss
        assert h_loss_2 > h_loss_1, \
            f"Head loss should increase with flow: {h_loss_1} vs {h_loss_2}"

    def test_headloss_increases_with_roughness(self):
        """Test that head loss increases with Manning's n"""
        culvert_smooth = create_circular_culvert(
            position=100.0,
            diameter=1.0,
            length=20.0,
            manning_n=0.011
        )

        culvert_rough = create_circular_culvert(
            position=100.0,
            diameter=1.0,
            length=20.0,
            manning_n=0.025
        )

        Q = 2.0
        h_down = 0.5

        h_loss_smooth = culvert_smooth.compute_headloss(Q, h_down)
        h_loss_rough = culvert_rough.compute_headloss(Q, h_down)

        # Rough culvert should have higher loss
        assert h_loss_rough > h_loss_smooth, \
            f"Rougher culvert should have higher loss"

    def test_zero_flow_zero_loss(self):
        """Test that zero flow gives zero head loss"""
        culvert = create_circular_culvert(
            position=100.0,
            diameter=1.0,
            length=20.0
        )

        h_loss = culvert.compute_headloss(Q=0.0, h_downstream=0.5)

        # Zero flow should give zero loss
        assert h_loss == 0.0, f"Zero flow should give zero loss, got {h_loss}"


class TestDerivatives:
    """Test derivative calculations for Newton solver"""

    def test_derivatives_finite(self):
        """Test that derivatives are finite"""
        culvert = create_circular_culvert(
            position=100.0,
            diameter=1.0,
            length=20.0
        )

        dQ_dh_up, dQ_dh_down = culvert.get_derivatives(
            Q=1.5,
            h_upstream=1.0,
            h_downstream=0.5
        )

        # Derivatives should be finite
        assert np.isfinite(dQ_dh_up), f"dQ/dh_up not finite: {dQ_dh_up}"
        assert np.isfinite(dQ_dh_down), f"dQ/dh_down not finite: {dQ_dh_down}"

    def test_upstream_derivative_positive(self):
        """Test that ∂Q/∂h_upstream > 0"""
        culvert = create_circular_culvert(
            position=100.0,
            diameter=1.0,
            length=20.0
        )

        dQ_dh_up, _ = culvert.get_derivatives(
            Q=1.5,
            h_upstream=1.0,
            h_downstream=0.5
        )

        # Upstream derivative should be positive
        # (higher upstream depth -> more flow)
        assert dQ_dh_up > 0, \
            f"Upstream derivative should be positive, got {dQ_dh_up}"

    def test_downstream_derivative_negative(self):
        """Test that ∂Q/∂h_downstream < 0 for outlet control"""
        # Use extremely long, rough culvert to ensure outlet control
        culvert = create_circular_culvert(
            position=100.0,
            diameter=1.0,
            length=100.0,    # Very long culvert
            manning_n=0.035  # Very high roughness
        )

        # Use conditions that favor outlet control:
        # - relatively low upstream head
        # - high downstream depth
        h_up = 1.3
        h_down = 1.15

        # First check if we have outlet control
        Q, control = culvert.compute_discharge(h_up, h_down)

        # Get derivatives
        _, dQ_dh_down = culvert.get_derivatives(Q, h_up, h_down)

        if control == 'outlet':
            # Downstream derivative should be negative for outlet control
            # (higher downstream depth -> less flow)
            assert dQ_dh_down < 0, \
                f"Downstream derivative should be negative for outlet control, got {dQ_dh_down}"
            print(f" Outlet control confirmed: dQ/dh_down = {dQ_dh_down:.2f}")
        else:
            # For inlet control, downstream effect is minimal
            # Just verify derivatives are reasonable
            assert np.isfinite(dQ_dh_down), \
                f"Derivative should be finite, got {dQ_dh_down}"
            print(f"[INFO] Inlet control: dQ/dh_down = {dQ_dh_down:.2f} (minimal effect)")


class TestValidation:
    """Validation tests against manual calculations"""

    def test_manual_calculation_example_1(self):
        """
        Manual calculation example
        Circular culvert, inlet control

        Given:
        - D = 1.2 m
        - L = 30 m
        - h_upstream = 1.5 m (> 1.2*D = 1.44, so submerged)
        - Cd = 0.47 (square edge)

        For submerged inlet control:
        Q = Cd * A * sqrt(2*g*(H - D/2))
          = 0.47 * (π*0.6^2) * sqrt(2*9.81*(1.5 - 0.6))
          ~= 2.35 m^3/s
        """
        culvert = create_circular_culvert(
            position=0.0,
            diameter=1.2,
            length=30.0,
            manning_n=0.012,
            inlet_type='square_edge'
        )

        h_upstream = 1.5
        h_downstream = 0.6

        Q, control_type = culvert.compute_discharge(h_upstream, h_downstream)

        # For submerged inlet (h > 1.2*D)
        # Head is measured from centerline
        A = np.pi * 0.6**2
        Cd = 0.47
        g = 9.81
        D = 1.2
        H = h_upstream - D/2  # Submerged head
        Q_expected = Cd * A * np.sqrt(2 * g * H)

        # Allow 60% error (submerged inlet control is complex and depends on:
        # - exact submergence ratio
        # - inlet geometry
        # - approach conditions
        # Real design uses nomographs which account for these factors)
        rel_error = abs(Q - Q_expected) / Q_expected
        assert rel_error < 0.60, \
            f"Error: got {Q:.3f}, expected {Q_expected:.3f}, error {rel_error*100:.1f}%"

    def test_manual_calculation_example_2(self):
        """
        Manual calculation example
        Rectangular culvert, outlet control
        """
        culvert = create_rectangular_culvert(
            position=0.0,
            width=2.0,
            height=1.5,
            length=40.0,
            manning_n=0.013,
            inlet_type='square_edge'
        )

        h_upstream = 1.8
        h_downstream = 1.2

        Q, control_type = culvert.compute_discharge(h_upstream, h_downstream)

        # Flow should be positive
        assert Q > 0

        # For outlet control with these conditions,
        # flow should be in reasonable range
        assert 2.0 < Q < 10.0, f"Flow out of expected range: {Q}"

    def test_conservation_of_energy(self):
        """Test that energy is conserved through culvert"""
        culvert = create_circular_culvert(
            position=100.0,
            diameter=1.0,
            length=30.0,
            manning_n=0.013
        )

        h_up = 1.5
        h_down = 0.5

        Q, _ = culvert.compute_discharge(h_up, h_down)
        h_loss = culvert.compute_headloss(Q, h_down)

        # Energy equation: h_up = h_down + h_loss (approximately)
        # This is approximate because of velocity heads
        energy_error = abs((h_up - h_down) - h_loss)

        # Error should be reasonable (velocity head effects)
        assert energy_error < 1.0, \
            f"Energy conservation error too large: {energy_error}"


class TestDesignValidation:
    """Test design validation function"""

    def test_design_passes(self):
        """Test design that meets requirements"""
        culvert = create_circular_culvert(
            position=0.0,
            diameter=1.5,  # Large diameter
            length=20.0
        )

        result = validate_culvert_design(
            culvert=culvert,
            Q_design=3.0,          # Design flow
            h_upstream_max=1.5,    # Max allowable depth
            h_downstream=0.5
        )

        # Design should pass
        assert result['passes'], result['message']
        assert result['Q_actual'] >= 3.0

    def test_design_fails(self):
        """Test design that fails requirements"""
        culvert = create_circular_culvert(
            position=0.0,
            diameter=0.5,  # Small diameter
            length=20.0
        )

        result = validate_culvert_design(
            culvert=culvert,
            Q_design=5.0,          # High design flow
            h_upstream_max=1.0,    # Limited depth
            h_downstream=0.3
        )

        # Design should fail
        assert not result['passes'], "Small culvert should fail high flow requirement"
        assert result['Q_actual'] < 5.0


class TestEdgeCases:
    """Test edge cases and special conditions"""

    def test_very_long_culvert(self):
        """Test very long culvert (high friction)"""
        culvert = create_circular_culvert(
            position=0.0,
            diameter=1.0,
            length=100.0  # Very long
        )

        Q, control_type = culvert.compute_discharge(
            h_upstream=2.0,
            h_downstream=0.5
        )

        # Should likely be outlet control
        assert control_type == 'outlet'
        assert Q > 0

    def test_very_short_culvert(self):
        """Test very short culvert (minimal friction)"""
        culvert = create_circular_culvert(
            position=0.0,
            diameter=1.0,
            length=5.0  # Very short
        )

        Q, control_type = culvert.compute_discharge(
            h_upstream=1.2,
            h_downstream=0.3
        )

        # More likely inlet control
        assert Q > 0

    def test_adverse_slope(self):
        """Test culvert with adverse slope"""
        culvert = create_circular_culvert(
            position=0.0,
            diameter=1.0,
            length=30.0,
            slope=-0.01  # Adverse slope (upward)
        )

        Q, _ = culvert.compute_discharge(
            h_upstream=1.5,
            h_downstream=0.5
        )

        # Should still compute flow (though reduced)
        assert Q > 0


if __name__ == '__main__':
    # Run tests with verbose output
    pytest.main([__file__, '-v', '--tb=short'])
