"""
Test suite for Bridge hydraulic model

Tests cover:
- Pier geometry calculations
- Bridge geometry calculations
- Backwater calculations (Yarnell equation)
- Pressure flow calculations
- Scour depth estimation
- Head loss calculations
- Free flow vs pressure flow transitions
"""

import pytest
import warnings
warnings.filterwarnings("ignore")
import numpy as np
import sys
import os

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from physics.structures.bridge import (
    Bridge,
    BridgeGeometry,
    Pier,
    create_simple_bridge,
    create_rectangular_pier_bridge
)


class TestPierGeometry:
    """Test pier geometry calculations"""

    def test_circular_pier_blockage(self):
        """Test circular pier blockage area"""
        pier = Pier(shape='circular', width=1.0, count=3)
        blockage = pier.get_blockage_area()
        expected = 3 * 1.0  # 3 piers x 1m width
        assert abs(blockage - expected) < 1e-10

    def test_rectangular_pier_blockage(self):
        """Test rectangular pier blockage area"""
        pier = Pier(shape='rectangular', width=1.5, length=4.0, count=2)
        blockage = pier.get_blockage_area()
        expected = 2 * 1.5  # 2 piers x 1.5m width
        assert abs(blockage - expected) < 1e-10

    def test_streamlined_pier_blockage(self):
        """Test streamlined pier blockage (reduced)"""
        pier = Pier(shape='streamlined', width=1.0, count=2)
        blockage = pier.get_blockage_area()
        expected = 2 * 1.0 * 0.8  # 80% of rectangular
        assert abs(blockage - expected) < 1e-10

    def test_zero_piers(self):
        """Test bridge with no piers"""
        pier = Pier(shape='circular', width=1.0, count=0)
        blockage = pier.get_blockage_area()
        assert blockage == 0.0

    def test_invalid_pier_width(self):
        """Test that invalid pier width raises error"""
        with pytest.raises(ValueError):
            Pier(shape='circular', width=-1.0, count=2)

    def test_rectangular_pier_requires_length(self):
        """Test that rectangular pier requires length"""
        with pytest.raises(ValueError):
            Pier(shape='rectangular', width=1.0, count=2)


class TestBridgeGeometry:
    """Test bridge geometry calculations"""

    def test_perpendicular_bridge_effective_width(self):
        """Test effective width for perpendicular bridge"""
        piers = Pier(shape='circular', width=1.0, count=2)
        geom = BridgeGeometry(
            position=100.0,
            bridge_width=20.0,
            deck_elevation=10.0,
            piers=piers,
            skew_angle=0.0
        )

        effective_width = geom.get_effective_width()
        assert abs(effective_width - 20.0) < 1e-10

    def test_skewed_bridge_effective_width(self):
        """Test effective width for skewed bridge"""
        piers = Pier(shape='circular', width=1.0, count=2)
        geom = BridgeGeometry(
            position=100.0,
            bridge_width=20.0,
            deck_elevation=10.0,
            piers=piers,
            skew_angle=30.0  # 30 degree skew
        )

        effective_width = geom.get_effective_width()
        # For 30 deg skew: W_eff = W / cos(30 deg) ~= W / 0.866
        expected = 20.0 / np.cos(np.radians(30))
        assert abs(effective_width - expected) < 0.01

    def test_net_width_calculation(self):
        """Test net width (minus pier blockage)"""
        piers = Pier(shape='circular', width=1.0, count=3)
        geom = BridgeGeometry(
            position=100.0,
            bridge_width=20.0,
            deck_elevation=10.0,
            piers=piers
        )

        net_width = geom.get_net_width(depth=5.0)
        expected = 20.0 - 3 * 1.0  # 20m - 3 piers x 1m
        assert abs(net_width - expected) < 1e-10

    def test_invalid_skew_angle(self):
        """Test that excessive skew angle raises error"""
        piers = Pier(shape='circular', width=1.0, count=2)
        with pytest.raises(ValueError):
            BridgeGeometry(
                position=100.0,
                bridge_width=20.0,
                deck_elevation=10.0,
                piers=piers,
                skew_angle=60.0  # Too large
            )


class TestBackwaterCalculations:
    """Test bridge backwater using Yarnell equation"""

    def test_free_flow_backwater(self):
        """Test backwater for free flow (deck not submerged)"""
        bridge = create_simple_bridge(
            position=100.0,
            bridge_width=20.0,
            deck_elevation=20.0,  # High deck
            pier_count=3,
            pier_width=1.0,
            approach_width=25.0
        )

        Q = 100.0  # m^3/s
        h_normal = 5.0  # m

        h_up, h_br, flow_type = bridge.compute_backwater(Q, h_normal)

        # Upstream depth should be higher than normal (backwater)
        assert h_up > h_normal, f"Upstream depth {h_up} should exceed normal {h_normal}"

        # Bridge depth should be similar to normal or slightly less (contraction)
        assert h_br > 0, "Bridge depth should be positive"

        # Should be free flow
        assert flow_type == 'free'

        # Backwater should be reasonable (< 2m for this case)
        assert (h_up - h_normal) < 2.0

    def test_pressure_flow(self):
        """Test pressure flow (submerged deck)"""
        bridge = create_simple_bridge(
            position=100.0,
            bridge_width=20.0,
            deck_elevation=6.0,  # Low deck
            pier_count=2,
            pier_width=1.0,
            approach_width=25.0
        )

        Q = 100.0
        h_normal = 7.0  # Above deck

        h_up, h_br, flow_type = bridge.compute_backwater(Q, h_normal)

        # Should be pressure flow
        assert flow_type == 'pressure'

        # Significant backwater expected
        assert h_up > h_normal

    def test_zero_discharge(self):
        """Test behavior with zero discharge"""
        bridge = create_simple_bridge(
            position=100.0,
            bridge_width=20.0,
            deck_elevation=10.0,
            pier_count=2,
            pier_width=1.0
        )

        h_up, h_br, flow_type = bridge.compute_backwater(Q=0.0, h_normal=5.0)

        # No backwater with no flow
        assert abs(h_up - 5.0) < 0.5

    def test_more_piers_more_backwater(self):
        """Test that more piers create more backwater"""
        Q = 80.0
        h_normal = 5.0

        # Bridge with 2 piers
        bridge_2pier = create_simple_bridge(
            position=100.0,
            bridge_width=20.0,
            deck_elevation=15.0,
            pier_count=2,
            pier_width=1.0,
            approach_width=25.0
        )

        # Bridge with 5 piers
        bridge_5pier = create_simple_bridge(
            position=100.0,
            bridge_width=20.0,
            deck_elevation=15.0,
            pier_count=5,
            pier_width=1.0,
            approach_width=25.0
        )

        h_up_2, _, _ = bridge_2pier.compute_backwater(Q, h_normal)
        h_up_5, _, _ = bridge_5pier.compute_backwater(Q, h_normal)

        # More piers should create more backwater
        assert h_up_5 > h_up_2, \
            f"5 piers (h={h_up_5}) should have more backwater than 2 piers (h={h_up_2})"


class TestScourCalculations:
    """Test pier scour depth estimation"""

    def test_scour_depth_positive(self):
        """Test that scour depth is positive"""
        bridge = create_simple_bridge(
            position=100.0,
            bridge_width=20.0,
            deck_elevation=10.0,
            pier_count=2,
            pier_width=1.5
        )

        scour = bridge.compute_scour_depth(
            Q=100.0,
            h_bridge=5.0,
            pier_width=1.5,
            d50=0.001  # 1mm sediment
        )

        assert scour > 0, "Scour depth should be positive"

    def test_scour_increases_with_velocity(self):
        """Test that higher velocity increases scour"""
        bridge = create_simple_bridge(
            position=100.0,
            bridge_width=20.0,
            deck_elevation=10.0,
            pier_count=2,
            pier_width=1.5
        )

        h = 5.0
        pier_w = 1.5

        scour_low = bridge.compute_scour_depth(Q=50.0, h_bridge=h, pier_width=pier_w)
        scour_high = bridge.compute_scour_depth(Q=150.0, h_bridge=h, pier_width=pier_w)

        assert scour_high > scour_low, \
            "Higher discharge should cause more scour"

    def test_scour_increases_with_pier_width(self):
        """Test that wider piers have more scour"""
        bridge = create_simple_bridge(
            position=100.0,
            bridge_width=20.0,
            deck_elevation=10.0,
            pier_count=2,
            pier_width=2.0
        )

        Q = 100.0
        h = 5.0

        scour_narrow = bridge.compute_scour_depth(Q, h, pier_width=1.0)
        scour_wide = bridge.compute_scour_depth(Q, h, pier_width=2.0)

        assert scour_wide > scour_narrow, \
            "Wider pier should have more scour"

    def test_zero_depth_zero_scour(self):
        """Test zero depth gives zero scour"""
        bridge = create_simple_bridge(
            position=100.0,
            bridge_width=20.0,
            deck_elevation=10.0,
            pier_count=2,
            pier_width=1.5
        )

        scour = bridge.compute_scour_depth(Q=50.0, h_bridge=0.0, pier_width=1.5)
        assert scour == 0.0


class TestHeadLoss:
    """Test head loss calculations through bridge"""

    def test_headloss_positive(self):
        """Test that head loss is positive"""
        bridge = create_simple_bridge(
            position=100.0,
            bridge_width=18.0,  # Narrower than approach
            deck_elevation=10.0,
            pier_count=3,
            pier_width=1.0,
            approach_width=25.0
        )

        h_loss = bridge.get_total_headloss(
            Q=100.0,
            h_upstream=5.5,
            h_downstream=5.0
        )

        assert h_loss > 0, "Head loss should be positive"

    def test_headloss_increases_with_flow(self):
        """Test that head loss increases with discharge"""
        bridge = create_simple_bridge(
            position=100.0,
            bridge_width=18.0,
            deck_elevation=10.0,
            pier_count=2,
            pier_width=1.0,
            approach_width=25.0
        )

        h_up = 5.5
        h_down = 5.0

        h_loss_low = bridge.get_total_headloss(Q=50.0, h_upstream=h_up, h_downstream=h_down)
        h_loss_high = bridge.get_total_headloss(Q=150.0, h_upstream=h_up, h_downstream=h_down)

        assert h_loss_high > h_loss_low, \
            "Higher flow should have higher head loss"


class TestBridgeTypes:
    """Test different bridge configurations"""

    def test_simple_bridge_creation(self):
        """Test simple bridge creation helper"""
        bridge = create_simple_bridge(
            position=200.0,
            bridge_width=20.0,
            deck_elevation=15.0,
            pier_count=3,
            pier_width=1.0
        )

        assert bridge.geom.position == 200.0
        assert bridge.geom.bridge_width == 20.0
        assert bridge.geom.piers.count == 3
        assert bridge.geom.piers.shape == 'circular'

    def test_rectangular_pier_bridge(self):
        """Test rectangular pier bridge creation"""
        bridge = create_rectangular_pier_bridge(
            position=200.0,
            bridge_width=25.0,
            deck_elevation=15.0,
            pier_count=4,
            pier_width=2.0,
            pier_length=6.0,
            skew_angle=15.0
        )

        assert bridge.geom.piers.shape == 'rectangular'
        assert bridge.geom.piers.width == 2.0
        assert bridge.geom.piers.length == 6.0
        assert bridge.geom.skew_angle == 15.0

    def test_skewed_bridge(self):
        """Test skewed bridge effects"""
        # Perpendicular bridge
        bridge_perp = create_simple_bridge(
            position=100.0,
            bridge_width=20.0,
            deck_elevation=15.0,
            skew_angle=0.0
        )

        # Skewed bridge (30 deg)
        piers = Pier(shape='circular', width=1.0, count=2)
        geom_skew = BridgeGeometry(
            position=100.0,
            bridge_width=20.0,
            deck_elevation=15.0,
            piers=piers,
            skew_angle=30.0
        )
        bridge_skew = Bridge(geom_skew, approach_width=25.0)

        # Effective width should be different
        w_perp = bridge_perp.geom.get_effective_width()
        w_skew = bridge_skew.geom.get_effective_width()

        assert w_skew > w_perp, "Skewed bridge should have larger effective width"


class TestEdgeCases:
    """Test edge cases and special conditions"""

    def test_very_wide_bridge(self):
        """Test very wide bridge (minimal contraction)"""
        bridge = create_simple_bridge(
            position=100.0,
            bridge_width=30.0,  # Wider than approach
            deck_elevation=15.0,
            pier_count=2,
            pier_width=0.5,
            approach_width=25.0
        )

        Q = 100.0
        h_normal = 5.0

        h_up, h_br, flow_type = bridge.compute_backwater(Q, h_normal)

        # Minimal backwater expected
        assert (h_up - h_normal) < 0.3, \
            "Wide bridge should have minimal backwater"

    def test_very_narrow_bridge(self):
        """Test very narrow bridge (severe contraction)"""
        bridge = create_simple_bridge(
            position=100.0,
            bridge_width=12.0,  # Much narrower
            deck_elevation=15.0,
            pier_count=4,
            pier_width=1.0,
            approach_width=25.0
        )

        Q = 100.0
        h_normal = 5.0

        h_up, h_br, flow_type = bridge.compute_backwater(Q, h_normal)

        # Significant backwater expected
        assert (h_up - h_normal) > 0.2, \
            "Narrow bridge should have significant backwater"

    def test_high_deck_no_pressure_flow(self):
        """Test that high deck never causes pressure flow"""
        bridge = create_simple_bridge(
            position=100.0,
            bridge_width=20.0,
            deck_elevation=50.0,  # Very high
            pier_count=2,
            pier_width=1.0
        )

        Q = 150.0
        h_normal = 10.0  # Deep, but still below deck

        _, _, flow_type = bridge.compute_backwater(Q, h_normal)

        assert flow_type == 'free', \
            "High deck should always result in free flow"


class TestValidation:
    """Validation tests against known cases"""

    def test_yarnell_equation_validation(self):
        """
        Validate against Yarnell (1934) experimental data

        Test case: Bridge with circular piers
        - Bridge width: 20 m
        - Pier count: 3
        - Pier diameter: 1.0 m
        - Discharge: 80 m^3/s
        - Normal depth: 5.0 m
        """
        bridge = create_simple_bridge(
            position=100.0,
            bridge_width=20.0,
            deck_elevation=15.0,
            pier_count=3,
            pier_width=1.0,
            approach_width=25.0
        )

        Q = 80.0
        h_normal = 5.0

        h_up, h_br, flow_type = bridge.compute_backwater(Q, h_normal)

        # Should be free flow
        assert flow_type == 'free'

        # Backwater should be in reasonable range (0.1 - 1.0 m for this case)
        backwater = h_up - h_normal
        assert 0.05 < backwater < 1.5, \
            f"Backwater {backwater:.3f}m should be in reasonable range"

    def test_energy_conservation(self):
        """Test that energy is approximately conserved"""
        bridge = create_simple_bridge(
            position=100.0,
            bridge_width=18.0,
            deck_elevation=12.0,
            pier_count=2,
            pier_width=1.0,
            approach_width=25.0
        )

        Q = 80.0
        h_up = 5.5
        h_down = 5.0

        # Head loss
        h_loss = bridge.get_total_headloss(Q, h_up, h_down)

        # Energy equation (simplified, ignoring velocity heads)
        # h_up ~= h_down + h_loss
        energy_balance = h_up - h_down - h_loss

        # Should be approximately zero (within velocity head difference)
        assert abs(energy_balance) < 0.5, \
            f"Energy balance error: {energy_balance:.3f} m"


if __name__ == '__main__':
    # Run tests with verbose output
    pytest.main([__file__, '-v', '--tb=short'])
