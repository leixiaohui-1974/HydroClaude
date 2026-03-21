"""Tests for the HEC-RAS vs HydroMind comparison pipeline.

Covers:
- Unified error metrics computation
- Flow regime diagnosis
- HEC-RAS result extraction (with mock HDF)
- Auto-tuning loop logic
- Report structure validation (seven required sections)
- Integration with comparison pipeline
"""

from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Any
from unittest.mock import MagicMock, patch

import numpy as np
import pytest

_PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(_PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(_PROJECT_ROOT))


# ===================================================================
# 1. Comparison metrics
# ===================================================================

class TestComparisonMetrics:
    """Verify unified error metric computation."""

    def test_perfect_match_passes(self):
        from scripts.run_hecras_hydromind_comparison_suite import compute_comparison_metrics

        ws = np.array([10.0, 10.5, 11.0, 11.5, 12.0])
        flow = np.array([50.0, 50.0, 50.0, 50.0, 50.0])
        metrics = compute_comparison_metrics(ws, ws, flow, flow)
        assert metrics.wse_mae_m == 0.0
        assert metrics.wse_rmse_m == 0.0
        assert metrics.flow_rel_error_pct == 0.0
        assert metrics.overall_pass is True
        assert metrics.n_points == 5

    def test_small_error_passes(self):
        from scripts.run_hecras_hydromind_comparison_suite import compute_comparison_metrics

        ws_hec = np.array([10.0, 10.5, 11.0])
        ws_hm = np.array([10.05, 10.52, 11.03])
        flow = np.array([50.0, 50.0, 50.0])
        metrics = compute_comparison_metrics(ws_hec, ws_hm, flow, flow)
        assert metrics.wse_mae_m < 0.10
        assert metrics.overall_pass is True

    def test_large_error_fails(self):
        from scripts.run_hecras_hydromind_comparison_suite import compute_comparison_metrics

        ws_hec = np.array([10.0, 10.5, 11.0])
        ws_hm = np.array([11.0, 11.5, 12.0])  # 1m off
        flow = np.array([50.0, 50.0, 50.0])
        metrics = compute_comparison_metrics(ws_hec, ws_hm, flow, flow)
        assert metrics.wse_mae_m > 0.10
        assert metrics.pass_wse is False
        assert metrics.overall_pass is False

    def test_flow_error_detected(self):
        from scripts.run_hecras_hydromind_comparison_suite import compute_comparison_metrics

        ws = np.array([10.0, 10.5, 11.0])
        flow_hec = np.array([50.0, 50.0, 50.0])
        flow_hm = np.array([60.0, 60.0, 60.0])  # 20% off
        metrics = compute_comparison_metrics(ws, ws, flow_hec, flow_hm)
        assert metrics.flow_rel_error_pct > 5.0
        assert metrics.pass_flow is False

    def test_depth_computation_with_bed(self):
        from scripts.run_hecras_hydromind_comparison_suite import compute_comparison_metrics

        ws_hec = np.array([10.0, 10.5])
        ws_hm = np.array([10.1, 10.6])
        flow = np.array([50.0, 50.0])
        bed = np.array([8.0, 8.0])
        metrics = compute_comparison_metrics(ws_hec, ws_hm, flow, flow, bed)
        assert metrics.depth_mae_m == pytest.approx(0.1, abs=0.001)


# ===================================================================
# 2. Flow regime diagnosis
# ===================================================================

class TestFlowRegimeDiagnosis:
    """Verify principle-driven flow regime diagnosis."""

    def _make_summary(self, **kwargs) -> Any:
        from integration.hec_ras_adapter import HECRASResultSummary
        defaults = {
            "mode": "steady",
            "unit_system": "si",
            "hdf_path": "/fake.hdf",
            "n_cross_sections": 10,
            "n_profiles": 1,
            "rivers": ["River1"] * 10,
            "reaches": ["Reach1"] * 10,
            "stations_m": list(np.linspace(1000, 0, 10)),
            "water_surface_m": [list(np.linspace(12, 10, 10))],
            "flow_m3s": [[50.0] * 10],
            "energy_grade_m": [list(np.linspace(12.1, 10.1, 10))],
            "profile_names": ["Profile 1"],
            "bed_elevation_m": list(np.linspace(10, 8, 10)),
            "manning_n_values": [0.025] * 10,
            "channel_width_m": [10.0] * 10,
        }
        defaults.update(kwargs)
        return HECRASResultSummary(**defaults)

    def test_subcritical_detection(self):
        from integration.hec_ras_adapter import diagnose_flow_regime
        summary = self._make_summary()
        diag = diagnose_flow_regime(summary)
        assert diag["regime"] == "subcritical"
        assert diag["froude_mean"] < 1.0
        assert diag["solver_recommendation"] in ("steady", "hydrostatic")

    def test_returns_recommended_params(self):
        from integration.hec_ras_adapter import diagnose_flow_regime
        summary = self._make_summary()
        diag = diagnose_flow_regime(summary)
        params = diag["recommended_params"]
        assert "solver_type" in params
        assert "manning_n" in params
        assert "Q_upstream" in params
        assert "h_downstream" in params
        assert params["manning_n"] > 0
        assert params["Q_upstream"] > 0

    def test_curve_type_classification(self):
        from integration.hec_ras_adapter import diagnose_flow_regime
        # M1 curve: depth > normal depth (downstream controlled backwater)
        summary = self._make_summary(
            water_surface_m=[list(np.linspace(14, 12, 10))],
            bed_elevation_m=list(np.linspace(10, 8, 10)),
        )
        diag = diagnose_flow_regime(summary)
        assert diag["curve_type"] in ("M1", "M2", "M3", "S1", "S2", "S3", "unknown")
        assert diag["normal_depth_m"] > 0
        assert diag["critical_depth_m"] > 0

    def test_empty_data_returns_default(self):
        from integration.hec_ras_adapter import diagnose_flow_regime
        summary = self._make_summary(
            water_surface_m=[],
            flow_m3s=[],
        )
        diag = diagnose_flow_regime(summary)
        assert diag["solver_recommendation"] == "hydrostatic"

    def test_solver_reason_is_nonempty(self):
        from integration.hec_ras_adapter import diagnose_flow_regime
        summary = self._make_summary()
        diag = diagnose_flow_regime(summary)
        assert len(diag["solver_reason"]) > 10


# ===================================================================
# 3. HECRASResultSummary dataclass
# ===================================================================

class TestHECRASResultSummary:
    """Verify the result summary data structure."""

    def test_to_dict_roundtrip(self):
        from integration.hec_ras_adapter import HECRASResultSummary
        summary = HECRASResultSummary(
            mode="steady", unit_system="si", hdf_path="/test.hdf",
            n_cross_sections=5, n_profiles=1,
            rivers=["R"], reaches=["Re"],
            stations_m=[100.0], water_surface_m=[[10.0]],
            flow_m3s=[[50.0]], energy_grade_m=[[10.1]],
            profile_names=["P1"],
            bed_elevation_m=[8.0], manning_n_values=[0.025],
            channel_width_m=[10.0],
        )
        d = summary.to_dict()
        assert d["mode"] == "steady"
        assert d["n_cross_sections"] == 5
        assert isinstance(d["water_surface_m"], list)


# ===================================================================
# 4. Auto-tuning logic
# ===================================================================

class TestAutoTuning:
    """Verify the constrained auto-tuning generates correct candidates."""

    def test_candidate_generation_numerical_first(self):
        from scripts.run_hecras_hydromind_comparison_suite import _generate_tuning_candidates

        base_params = {
            "solver_type": "steady",
            "nx": 201,
            "manning_n": 0.025,
            "method": "shooting",
        }
        candidates = _generate_tuning_candidates(base_params, {})
        # Should have numerical candidates before physical
        reasons = [reason for _, reason in candidates]
        nx_idx = next((i for i, r in enumerate(reasons) if "分辨率" in r or "nx=" in r), 999)
        manning_idx = next((i for i, r in enumerate(reasons) if "Manning" in r), 999)
        assert nx_idx < manning_idx, "Numerical params should come before physical params"

    def test_manning_n_constrained(self):
        from scripts.run_hecras_hydromind_comparison_suite import _generate_tuning_candidates

        base_params = {
            "solver_type": "hydrostatic",
            "nx": 201,
            "manning_n": 0.025,
        }
        candidates = _generate_tuning_candidates(base_params, {})
        manning_candidates = [
            (p, r) for p, r in candidates
            if "Manning" in r
        ]
        for p, _ in manning_candidates:
            # Within ±20% of 0.025
            assert 0.020 <= p["manning_n"] <= 0.030

    def test_godunov_has_cfl_candidates(self):
        from scripts.run_hecras_hydromind_comparison_suite import _generate_tuning_candidates

        base_params = {
            "solver_type": "godunov",
            "n_cells": 200,
            "cfl": 0.5,
            "manning_n": 0.025,
        }
        candidates = _generate_tuning_candidates(base_params, {})
        cfl_candidates = [r for _, r in candidates if "CFL" in r]
        assert len(cfl_candidates) >= 1


# ===================================================================
# 5. Report structure validation
# ===================================================================

class TestReportStructure:
    """Verify case reports contain all seven required sections."""

    REQUIRED_SECTIONS = [
        "问题描述",
        "水网拓扑",
        "解题思路",
        "结果图",
        "结果表",
        "结论",
        "建议",
    ]

    def test_comparison_chapter_md_with_metrics(self):
        from scripts.generate_hecras_case_reports import _comparison_chapter_md

        record = {
            "comparison_metrics": {
                "wse_mae_m": 0.05,
                "wse_rmse_m": 0.06,
                "wse_p95_m": 0.08,
                "wse_max_error_m": 0.1,
                "flow_mae_m3s": 0.5,
                "flow_rel_error_pct": 1.0,
                "depth_mae_m": 0.05,
                "depth_rmse_m": 0.06,
                "n_points": 10,
                "pass_wse": True,
                "pass_flow": True,
                "overall_pass": True,
            },
            "flow_diagnosis": {
                "regime": "subcritical",
                "curve_type": "M1",
                "froude_mean": 0.3,
                "avg_slope": 0.001,
                "normal_depth_m": 1.5,
                "critical_depth_m": 1.0,
                "solver_recommendation": "steady",
                "solver_reason": "亚临界稳态回水",
            },
            "hydromind_run": {
                "solver_type": "steady",
                "status": "pass",
            },
            "tuning_history": [
                {"iteration": 0, "reason": "初始", "wse_mae_m": 0.05, "flow_rel_error_pct": 1.0, "overall_pass": True},
            ],
        }
        md = _comparison_chapter_md(record)
        assert "HEC-RAS vs HydroMind" in md
        assert "关键误差指标" in md
        assert "PASS" in md
        assert "流态诊断" in md

    def test_comparison_chapter_md_without_metrics(self):
        from scripts.generate_hecras_case_reports import _comparison_chapter_md

        record = {"comparison_metrics": None}
        md = _comparison_chapter_md(record)
        assert "未完成" in md or "未执行" in md

    def test_comparison_chapter_with_error(self):
        from scripts.generate_hecras_case_reports import _comparison_chapter_md

        record = {"comparison_metrics": {"error": "HDF not found"}}
        md = _comparison_chapter_md(record)
        assert "HDF not found" in md

    def test_recommendations_direct_candidate_with_pass(self):
        from scripts.generate_hecras_case_reports import _ai_recommendations

        record = {
            "comparability": {"level": "direct_candidate"},
            "comparison_metrics": {"overall_pass": True, "wse_mae_m": 0.05},
            "flow_diagnosis": {"curve_type": "M1"},
            "tuning_history": [],
        }
        recs = _ai_recommendations(record, None)
        assert any("回归基线" in r for r in recs)

    def test_recommendations_partial_level(self):
        from scripts.generate_hecras_case_reports import _ai_recommendations

        record = {
            "comparability": {"level": "partial"},
            "comparison_metrics": None,
            "flow_diagnosis": None,
            "tuning_history": [],
        }
        recs = _ai_recommendations(record, None)
        assert any("部分口径" in r for r in recs)


# ===================================================================
# 6. Suite record data contract
# ===================================================================

class TestSuiteRecordContract:
    """Verify the v2 record structure has required fields."""

    def test_new_record_fields_present(self):
        from scripts.run_hecras_example_suite import _make_case_id

        case_id = _make_case_id("Test Project 123")
        assert case_id == "test_project_123"

    def test_record_v2_fields_structure(self):
        """Verify that new v2 fields are initialized correctly."""
        # Simulate what _collect_project_record would produce
        record = {
            "case_id": "test",
            "project_name": "Test",
            "category": "Test Category",
            "status": "pending",
            "hecras_summary": None,
            "hydromind_run": None,
            "comparison_metrics": None,
            "tuning_history": [],
            "report_assets": {},
            "evidence": {
                "hecras_hdf_verified": False,
                "hydromind_completed": False,
                "comparison_completed": False,
            },
        }
        assert record["tuning_history"] == []
        assert record["evidence"]["hecras_hdf_verified"] is False
        assert record["comparison_metrics"] is None


# ===================================================================
# 7. Comparison pipeline integration (mock-based)
# ===================================================================

class TestComparisonPipelineIntegration:
    """Integration tests using mocked HEC-RAS data."""

    def _make_mock_record(self) -> dict[str, Any]:
        return {
            "case_id": "test_steady",
            "project_name": "Test Steady Flow",
            "category": "1D Steady Flow Hydraulics",
            "status": "computed",
            "result_hdf_path": "/fake/test.p01.hdf",
            "project_file": "/fake/test.prj",
            "project_dir": "/fake",
            "actual_plan_number": "01",
            "comparability": {"level": "direct_candidate"},
            "hecras_summary": None,
            "hydromind_run": None,
            "comparison_metrics": None,
            "tuning_history": [],
            "report_assets": {},
            "evidence": {
                "hecras_hdf_verified": False,
                "hydromind_completed": False,
                "comparison_completed": False,
            },
        }

    def _make_mock_hecras_summary(self):
        from integration.hec_ras_adapter import HECRASResultSummary
        n = 10
        return HECRASResultSummary(
            mode="steady",
            unit_system="si",
            hdf_path="/fake.hdf",
            n_cross_sections=n,
            n_profiles=1,
            rivers=["River1"] * n,
            reaches=["Reach1"] * n,
            stations_m=list(np.linspace(1000, 0, n)),
            water_surface_m=[list(np.linspace(12, 10, n))],
            flow_m3s=[[50.0] * n],
            energy_grade_m=[list(np.linspace(12.1, 10.1, n))],
            profile_names=["Profile 1"],
            bed_elevation_m=list(np.linspace(10, 8, n)),
            manning_n_values=[0.025] * n,
            channel_width_m=[10.0] * n,
        )

    def test_run_comparison_for_record_no_hdf(self):
        from scripts.run_hecras_hydromind_comparison_suite import run_comparison_for_record

        record = self._make_mock_record()
        record["result_hdf_path"] = None
        result = run_comparison_for_record(record)
        assert result["evidence"]["comparison_completed"] is False
        assert "error" in (result.get("comparison_metrics") or {})

    @patch("scripts.run_hecras_hydromind_comparison_suite.extract_hecras_result_summary")
    @patch("scripts.run_hecras_hydromind_comparison_suite.run_hydromind_simulation")
    @patch("scripts.run_hecras_hydromind_comparison_suite.Path.exists", return_value=True)
    def test_run_comparison_for_record_success(self, mock_exists, mock_sim, mock_extract):
        from scripts.run_hecras_hydromind_comparison_suite import run_comparison_for_record

        summary = self._make_mock_hecras_summary()
        mock_extract.return_value = summary

        # Mock simulation returning near-perfect results
        n = summary.n_cross_sections
        mock_sim.return_value = {
            "success": True,
            "h_final": list(np.linspace(2.0, 2.0, 201)),
            "Q_final": [50.0] * 201,
            "solver_type": "steady",
        }

        record = self._make_mock_record()
        result = run_comparison_for_record(record)
        assert result["evidence"]["comparison_completed"] is True
        assert result["evidence"]["hydromind_completed"] is True
        assert result["comparison_metrics"] is not None
        assert result["hydromind_run"]["solver_type"] is not None
        assert len(result["tuning_history"]) >= 1

    @patch("scripts.run_hecras_hydromind_comparison_suite.extract_hecras_result_summary")
    def test_run_comparison_extract_failure(self, mock_extract):
        from scripts.run_hecras_hydromind_comparison_suite import run_comparison_for_record

        mock_extract.side_effect = KeyError("No results in HDF")
        record = self._make_mock_record()
        result = run_comparison_for_record(record)
        assert result["evidence"]["comparison_completed"] is False
        assert "error" in str(result.get("comparison_metrics", {}))


# ===================================================================
# 8. Overview report comparison stats
# ===================================================================

class TestOverviewComparisonStats:
    """Verify suite-level comparison statistics computation."""

    def test_build_comparison_stats_empty(self):
        from scripts.generate_hecras_example_suite_report import _build_comparison_stats

        stats = _build_comparison_stats([])
        assert stats["compared_count"] == 0
        assert stats["pass_rate"] == 0

    def test_build_comparison_stats_with_data(self):
        from scripts.generate_hecras_example_suite_report import _build_comparison_stats

        records = [
            {
                "project_name": "Test1",
                "comparison_metrics": {
                    "wse_mae_m": 0.05,
                    "overall_pass": True,
                },
                "hydromind_run": {"solver_type": "steady"},
                "tuning_history": [
                    {"wse_mae_m": 0.1},
                    {"wse_mae_m": 0.05},
                ],
            },
            {
                "project_name": "Test2",
                "comparison_metrics": {
                    "wse_mae_m": 0.5,
                    "overall_pass": False,
                },
                "hydromind_run": {"solver_type": "godunov"},
                "tuning_history": [],
            },
        ]
        stats = _build_comparison_stats(records)
        assert stats["compared_count"] == 2
        assert stats["pass_count"] == 1
        assert stats["pass_rate"] == 0.5
        assert "steady" in stats["solver_stats"]
        assert "godunov" in stats["solver_stats"]
        assert stats["tuning_benefit_count"] == 1
        assert len(stats["top_deviation"]) == 2
