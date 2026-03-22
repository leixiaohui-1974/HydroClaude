# -*- coding: utf-8 -*-
"""侧向堰 (_solve_lateral_weir) 单元测试。

覆盖场景：无溢流、完全溢流、Villemonte 淹没、边界情况、流量守恒、水位合理性。
"""
import sys
import numpy as np
import pytest

sys.path.insert(0, "Z:/research/hydroclaude")
from solvers.steady_profile_solver import SteadyProfileSolver


def _make_solver(n_xs: int = 11, S0: float = 0.001) -> SteadyProfileSolver:
    """构造带床面高程的矩形渠道求解器。"""
    bed = [10.0 - i * S0 * 50.0 for i in range(n_xs)]
    rl = [50.0] * n_xs
    return SteadyProfileSolver(
        length=500.0, B=10.0, S0=S0, n=0.030, g=9.81,
        bed_elevations=bed,
        reach_lengths=rl,
    )


class TestLateralWeirEdgeCases:
    """边界情况测试。"""

    def test_empty_xs_returns_empty(self):
        solver = _make_solver()
        wp = {"weir_coef": 0.36, "crest_elevation_m": 10.5,
              "weir_length_m": 100.0, "start_xs": 2, "end_xs": 5}
        r = solver._solve_lateral_weir(50.0, 11.5, wp, [])
        assert r["converged"] is True
        assert len(r["W"]) == 0 and len(r["Q"]) == 0
        assert r["method"] == "lateral_weir"

    def test_single_xs_returns_downstream(self):
        solver = _make_solver()
        wp = {"weir_coef": 0.36, "crest_elevation_m": 10.5,
              "weir_length_m": 100.0, "start_xs": 2, "end_xs": 5}
        r = solver._solve_lateral_weir(50.0, 11.5, wp, [3])
        assert r["converged"] is True
        assert r["W"][0] == pytest.approx(11.5)
        assert r["Q"][0] == pytest.approx(50.0)


class TestLateralWeirPhysics:
    """物理正确性测试。"""

    def test_no_overflow_high_crest(self):
        """堰顶远高于水面：Q_lateral 应为零，流量不衰减。"""
        solver = _make_solver()
        xs = list(range(11))
        wp = {"weir_coef": 0.36, "crest_elevation_m": 20.0,
              "weir_length_m": 200.0, "start_xs": 2, "end_xs": 7}
        r = solver._solve_lateral_weir(30.0, 10.3, wp, xs)
        assert r["Q_lateral"][-1] == pytest.approx(0.0, abs=1e-8)
        assert r["Q"][0] == pytest.approx(30.0)

    def test_flow_decreases_monotonically_in_weir_zone(self):
        """堰段内流量应单调不增。"""
        solver = _make_solver(S0=0.0)
        xs = list(range(11))
        wp = {"weir_coef": 0.36, "crest_elevation_m": 11.2,
              "weir_length_m": 200.0, "start_xs": 3, "end_xs": 7}
        r = solver._solve_lateral_weir(50.0, 11.5, wp, xs)
        Q = r["Q"]
        for j in range(3, 7):
            assert Q[j] >= Q[j + 1] - 1e-9

    def test_flow_conservation(self):
        """流量守恒：Q_lateral[-1] == Q_upstream - Q[-1]。"""
        solver = _make_solver(S0=0.0)
        xs = list(range(11))
        wp = {"weir_coef": 0.36, "crest_elevation_m": 11.2,
              "weir_length_m": 200.0, "start_xs": 3, "end_xs": 7}
        r = solver._solve_lateral_weir(50.0, 11.5, wp, xs)
        total_lat = r["Q_lateral"][-1]
        total_consumed = 50.0 - r["Q"][-1]
        assert total_lat == pytest.approx(total_consumed, abs=1e-8)

    def test_wse_above_bed_everywhere(self):
        """所有断面水面高程不低于床面高程。"""
        solver = _make_solver(S0=0.001)
        xs = list(range(11))
        bed = solver._bed_elevations
        wp = {"weir_coef": 0.36, "crest_elevation_m": 10.5,
              "weir_length_m": 150.0, "start_xs": 2, "end_xs": 6}
        r = solver._solve_lateral_weir(30.0, 10.0, wp, xs)
        for k, i in enumerate(xs):
            assert r["W"][k] >= float(bed[i]) - 1e-6

    def test_villemonte_reduces_outflow(self):
        """淹没尾水时溢出量不超过自由出流。"""
        solver = _make_solver(S0=0.0)
        xs = list(range(11))
        wp_free = {"weir_coef": 0.36, "crest_elevation_m": 11.2,
                   "weir_length_m": 200.0, "start_xs": 3, "end_xs": 7}
        wp_subm = dict(wp_free)
        wp_subm["tailwater_elevation_m"] = 11.4
        r_free = solver._solve_lateral_weir(50.0, 11.5, wp_free, xs)
        r_subm = solver._solve_lateral_weir(50.0, 11.5, wp_subm, xs)
        assert r_subm["Q_lateral"][-1] <= r_free["Q_lateral"][-1] + 1e-6

    def test_result_has_required_keys(self):
        """返回字典包含所有必要键，类型正确。"""
        solver = _make_solver()
        xs = list(range(11))
        wp = {"weir_coef": 0.36, "crest_elevation_m": 11.0,
              "weir_length_m": 200.0, "start_xs": 2, "end_xs": 8}
        r = solver._solve_lateral_weir(40.0, 10.5, wp, xs)
        for key in ("W", "Q", "Q_lateral", "converged", "iterations", "method"):
            assert key in r
        assert r["method"] == "lateral_weir"
        assert isinstance(r["converged"], bool)
        assert isinstance(r["iterations"], int)
        assert len(r["W"]) == len(xs)
        assert len(r["Q"]) == len(xs)
        assert len(r["Q_lateral"]) == len(xs)

    def test_upstream_index_order_auto_corrected(self):
        """start_xs > end_xs 时自动纠正，结果与正序相同。"""
        solver = _make_solver(S0=0.0)
        xs = list(range(11))
        wp1 = {"weir_coef": 0.36, "crest_elevation_m": 11.2,
               "weir_length_m": 200.0, "start_xs": 3, "end_xs": 7}
        wp2 = dict(wp1)
        wp2["start_xs"] = 7
        wp2["end_xs"] = 3
        r1 = solver._solve_lateral_weir(50.0, 11.5, wp1, xs)
        r2 = solver._solve_lateral_weir(50.0, 11.5, wp2, xs)
        assert r1["Q_lateral"][-1] == pytest.approx(r2["Q_lateral"][-1], abs=1e-8)


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
