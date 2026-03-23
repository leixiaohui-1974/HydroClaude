import math
import pytest
import numpy as np
from physics.cross_section import RectangularSection
from solvers.steady_profile_solver import SteadyProfileSolver


def _make_solver():
    stations = [0.0, 20.0, 40.0, 60.0]
    bed = [10.0, 9.9, 9.8, 9.7]
    xs_shapes = [RectangularSection(f"xs-{idx}", width=10.0) for idx in range(len(stations))]
    solver = SteadyProfileSolver(
        length=stations[-1] - stations[0],
        n=0.04,
        cross_sections=xs_shapes,
        bed_elevations=bed,
        manning_ns=[0.04] * len(stations),
    )
    return solver, stations, bed


def _default_bridge(**kwargs):
    br = {
        "bridge_length_m": 20.0,
        "total_pier_width_m": 0.5,
        "pier_cd": 2.0,
        "deck_elevation_m": 15.0,
        "pier_height_m": 5.0,
        "bridge_method": "momentum",
    }
    br.update(kwargs)
    return br


class TestHydrostaticPressureForce:

    def test_force_positive(self):
        solver, _, _ = _make_solver()
        assert solver._hydrostatic_pressure_force(2.0, 0) > 0

    def test_force_increases_with_depth(self):
        solver, _, _ = _make_solver()
        f1 = solver._hydrostatic_pressure_force(1.0, 0)
        f2 = solver._hydrostatic_pressure_force(2.0, 0)
        assert f2 > f1

    def test_near_zero_depth_no_crash(self):
        solver, _, _ = _make_solver()
        force = solver._hydrostatic_pressure_force(1e-8, 0)
        assert force >= 0

    def test_matches_formula(self):
        solver, _, _ = _make_solver()
        h = 1.5
        A, _P, _R, T = solver._get_geometry(h, 0)
        expected = 9810.0 * A * A / (2.0 * T)
        actual = solver._hydrostatic_pressure_force(h, 0)
        assert abs(actual - expected) / max(expected, 1.0) < 0.01


class TestSolveBridgeMomentum:

    def test_upstream_wse_geq_downstream(self):
        solver, _, bed = _make_solver()
        W_ds = bed[2] + 1.5
        W_us = solver._solve_bridge_momentum(
            Q=5.0, W_downstream=W_ds, bridge=_default_bridge(),
            bed_ds=bed[2], bed_us=bed[1],
            ds_xs_index=2, us_xs_index=1,
        )
        assert W_us >= W_ds

    def test_higher_discharge_larger_backwater(self):
        solver, _, bed = _make_solver()
        W_ds = bed[2] + 1.0
        W_lo = solver._solve_bridge_momentum(
            Q=3.0, W_downstream=W_ds, bridge=_default_bridge(),
            bed_ds=bed[2], bed_us=bed[1],
            ds_xs_index=2, us_xs_index=1,
        )
        W_hi = solver._solve_bridge_momentum(
            Q=10.0, W_downstream=W_ds, bridge=_default_bridge(),
            bed_ds=bed[2], bed_us=bed[1],
            ds_xs_index=2, us_xs_index=1,
        )
        assert W_hi >= W_lo

    def test_upstream_above_bed(self):
        solver, _, bed = _make_solver()
        W_ds = bed[2] + 1.5
        W_us = solver._solve_bridge_momentum(
            Q=8.0, W_downstream=W_ds, bridge=_default_bridge(),
            bed_ds=bed[2], bed_us=bed[1],
            ds_xs_index=2, us_xs_index=1,
        )
        assert W_us > bed[1]

    def test_pier_configuration_changes_solution(self):
        solver, _, bed = _make_solver()
        W_ds = bed[2] + 1.5
        W_with = solver._solve_bridge_momentum(
            Q=6.0, W_downstream=W_ds,
            bridge=_default_bridge(total_pier_width_m=2.0),
            bed_ds=bed[2], bed_us=bed[1],
            ds_xs_index=2, us_xs_index=1,
        )
        W_none = solver._solve_bridge_momentum(
            Q=6.0, W_downstream=W_ds,
            bridge=_default_bridge(total_pier_width_m=0.0),
            bed_ds=bed[2], bed_us=bed[1],
            ds_xs_index=2, us_xs_index=1,
        )
        assert abs(W_with - W_none) > 1e-3


class TestBridgeMethodDispatch:

    def test_momentum_returns_float(self):
        solver, _, bed = _make_solver()
        result = solver._solve_bridge_momentum(
            Q=5.0, W_downstream=bed[2] + 1.0,
            bridge=_default_bridge(),
            bed_ds=bed[2], bed_us=bed[1],
            ds_xs_index=2, us_xs_index=1,
        )
        assert isinstance(result, float)

    def test_no_bridge_method_key_uses_momentum(self):
        solver, _, bed = _make_solver()
        bridge_no_key = {
            "bridge_length_m": 10.0,
            "total_pier_width_m": 0.0,
            "deck_elevation_m": 20.0,
            "pier_height_m": 5.0,
        }
        result = solver._solve_bridge_momentum(
            Q=5.0, W_downstream=bed[2] + 1.0,
            bridge=bridge_no_key,
            bed_ds=bed[2], bed_us=bed[1],
            ds_xs_index=2, us_xs_index=1,
        )
        assert result >= bed[1]


class TestPhysicalConstraints:

    def test_upstream_total_head_not_less_than_downstream(self):
        solver, _, bed = _make_solver()
        bridge = {
            "bridge_length_m": 20.0,
            "total_pier_width_m": 0.5,
            "pier_cd": 2.0,
            "deck_elevation_m": 20.0,
            "pier_height_m": 6.0,
        }
        Q = 7.0
        W_ds = bed[2] + 1.2
        W_us = solver._solve_bridge_momentum(
            Q=Q, W_downstream=W_ds, bridge=bridge,
            bed_ds=bed[2], bed_us=bed[1],
            ds_xs_index=2, us_xs_index=1,
        )
        h_ds = W_ds - bed[2]
        h_us = W_us - bed[1]
        A_ds, _, _, _ = solver._get_geometry(h_ds, 2)
        A_us, _, _, _ = solver._get_geometry(h_us, 1)
        V_ds = Q / max(A_ds, 1e-9)
        V_us = Q / max(A_us, 1e-9)
        E_ds = W_ds + V_ds**2 / (2 * 9.81)
        E_us = W_us + V_us**2 / (2 * 9.81)
        assert E_us >= E_ds - 0.1

    def test_standard_step_bridge_dispatch_runs(self):
        solver, stations, bed = _make_solver()
        solver._bridges = [{
            "us_rs": stations[1],
            "ds_rs": stations[2],
            "bridge_length_m": 20.0,
            "total_pier_width_m": 0.5,
            "pier_cd": 2.0,
            "deck_elevation_m": 15.0,
            "pier_height_m": 5.0,
            "bridge_method": "momentum",
        }]
        solver._xs_station_labels = stations

        result = solver.solve_standard_step(Q=5.0, h_downstream=1.2)

        assert result["method"] == "standard_step_variable_xs"
        assert len(result["W"]) == len(stations)
        assert result["W"][1] > bed[1]


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
