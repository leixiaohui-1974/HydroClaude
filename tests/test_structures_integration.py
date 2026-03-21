import sys
from pathlib import Path

ROOT = Path("Z:/research/hydroclaude")
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import numpy as np

def _make_summary(has_structures=False, rivers=None):
    from integration.hec_ras_adapter import HECRASResultSummary
    n = 5
    ws = [list(np.linspace(10.0, 9.5, n))]
    flow = [list(np.full(n, 5.0))]
    bed_data = list(np.linspace(8.0, 7.5, n))
    return HECRASResultSummary(
        mode="steady", unit_system="si", hdf_path="/fake/project.p01.hdf",
        n_cross_sections=n, n_profiles=1, rivers=rivers or ["RiverA"]*n,
        reaches=["Reach1"]*n, stations_m=list(np.linspace(0, 1000, n)),
        water_surface_m=ws, flow_m3s=flow, energy_grade_m=ws, profile_names=["PF1"],
        bed_elevation_m=bed_data, manning_n_values=[0.03]*n,
        channel_width_m=[10.0]*n, has_structures=has_structures,
    )

def test_has_structures_default_false():
    s = _make_summary(has_structures=False)
    assert s.has_structures is False
    print("PASS test_has_structures_default_false")

def test_classify_structures_priority():
    from scripts.run_hecras_hydromind_comparison_suite import classify_case_type
    s = _make_summary(has_structures=True, rivers=["R1","R2","R3","R1","R2"])
    diag = {"regime":"subcritical","avg_depth_m":1.5,"representative_width_m":10.0,"has_structures":True}
    cls = classify_case_type(s, diag, "direct_candidate")
    assert cls.case_type == "has_structures", f"got {cls.case_type}"
    assert cls.comparable is False
    assert cls.wse_threshold_m == 0.50
    assert cls.flow_threshold_pct == 15.0
    print("PASS test_classify_structures_priority")

def test_classify_no_structures_passthrough():
    from scripts.run_hecras_hydromind_comparison_suite import classify_case_type
    s = _make_summary(has_structures=False)
    diag = {"regime":"subcritical","avg_depth_m":1.5,"representative_width_m":10.0,"has_structures":False}
    cls = classify_case_type(s, diag, "direct_candidate")
    assert cls.case_type != "has_structures", f"Should not be has_structures, got {cls.case_type}"
    print(f"PASS test_classify_no_structures_passthrough (type={cls.case_type})")

def test_tuning_skips_manning_for_structures():
    from scripts.run_hecras_hydromind_comparison_suite import _generate_tuning_candidates
    base = {"solver_type":"steady","manning_n":0.03,"slope":0.001,"width":10.0,
            "Q_upstream":5.0,"h_downstream":1.0,"length":1000.0,"nx":101}
    diag = {"has_structures": True}
    candidates = _generate_tuning_candidates(base, diag)
    manning_cands = [(p,r) for p,r in candidates if p.get("manning_n") != base["manning_n"]]
    assert len(manning_cands) == 0, f"Expected 0 Manning n candidates, got {manning_cands}"
    print(f"PASS test_tuning_skips_manning_for_structures ({len(candidates)} total candidates)")

def test_tuning_includes_manning_without_structures():
    from scripts.run_hecras_hydromind_comparison_suite import _generate_tuning_candidates
    base = {"solver_type":"steady","manning_n":0.03,"slope":0.001,"width":10.0,
            "Q_upstream":5.0,"h_downstream":1.0,"length":1000.0,"nx":101}
    diag = {"has_structures": False}
    candidates = _generate_tuning_candidates(base, diag)
    manning_cands = [(p,r) for p,r in candidates if p.get("manning_n") != base["manning_n"]]
    assert len(manning_cands) > 0, "Expected Manning n candidates when no structures"
    print(f"PASS test_tuning_includes_manning_without_structures ({len(manning_cands)} Manning n cands)")

def test_keyword_fallback_culvert():
    from scripts.run_hecras_hydromind_comparison_suite import run_comparison_for_record
    from unittest.mock import patch, MagicMock

    summary = _make_summary(has_structures=False)

    def fake_extract(hdf_path, project_file=None):
        return summary

    def fake_diagnose(s):
        return {
            "regime":"subcritical","curve_type":"M1","avg_depth_m":1.5,
            "representative_width_m":10.0,"avg_slope":0.001,"avg_manning_n":0.03,
            "representative_Q_m3s":5.0,"has_structures":False,
            "solver_recommendation":"steady","solver_reason":"test",
            "recommended_params":{"solver_type":"steady","manning_n":0.03,"slope":0.001,
                                  "width":10.0,"Q_upstream":5.0,"h_downstream":1.0,
                                  "length":1000.0,"nx":101},
        }

    record = {
        "project_name": "ConSpan Culvert Example",
        "status": "computed",
        "result_hdf_path": "/fake/culvert.p01.hdf",
        "comparability": {"level": "direct_candidate", "reason": "culvert case"},
    }

    with patch("scripts.run_hecras_hydromind_comparison_suite.extract_hecras_result_summary",
               side_effect=fake_extract), \
         patch("scripts.run_hecras_hydromind_comparison_suite.diagnose_flow_regime",
               side_effect=fake_diagnose), \
         patch("pathlib.Path.exists", return_value=True):
        result = run_comparison_for_record(record)

    cm = result.get("comparison_metrics", {})
    cls = result.get("case_classification", {})
    assert cm.get("case_type") == "has_structures", f"Expected has_structures, got cm={cm}"
    assert cm.get("comparable") is False, f"Expected comparable=False, got {cm}"
    assert cls.get("case_type") == "has_structures", f"Expected cls has_structures, got {cls}"
    print("PASS test_keyword_fallback_culvert")

def test_detect_structures_hdf():
    import h5py, tempfile, os
    from integration.hec_ras_adapter import _detect_structures

    with tempfile.NamedTemporaryFile(suffix=".hdf", delete=False) as f:
        tmp = f.name

    # HDF with structure group having children
    with h5py.File(tmp, "w") as hdf:
        hdf.create_group("Geometry/Culverts").create_dataset("data", data=[1,2,3])
    with h5py.File(tmp, "r") as hdf:
        assert _detect_structures(hdf) is True, "Expected True for Geometry/Culverts"

    # HDF without structure group
    with h5py.File(tmp, "w") as hdf:
        hdf.create_group("Geometry/Cross Sections")
    with h5py.File(tmp, "r") as hdf:
        assert _detect_structures(hdf) is False, "Expected False for no structure groups"

    os.unlink(tmp)
    print("PASS test_detect_structures_hdf")

if __name__ == "__main__":
    tests = [
        test_has_structures_default_false,
        test_classify_structures_priority,
        test_classify_no_structures_passthrough,
        test_tuning_skips_manning_for_structures,
        test_tuning_includes_manning_without_structures,
        test_keyword_fallback_culvert,
        test_detect_structures_hdf,
    ]
    failed = []
    for t in tests:
        try:
            t()
        except Exception as exc:
            import traceback
            print(f"FAIL {t.__name__}: {exc}")
            traceback.print_exc()
            failed.append(t.__name__)

    print(f"\n{'='*60}")
    print(f"Results: {len(tests)-len(failed)}/{len(tests)} passed")
    if failed:
        print(f"FAILED: {failed}")
        sys.exit(1)
    print("All tests PASSED")
