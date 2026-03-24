"""验证自建 PT 表 vs HEC-RAS PT 表的一致性。

对比每个断面在多个水位下的 K 值，确认自建计算与 HEC-RAS 匹配。
"""

import sys
import os
import json
import numpy as np

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from physics.cross_section import NaturalSection
from physics.property_table import subdivided_conveyance_with_beta

REF_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                       "reports", "hecras_unsteady_reference")


def validate_case(json_path: str) -> dict:
    """对比单个案例的自建 K vs HEC-RAS K。"""
    with open(json_path, encoding="utf-8") as f:
        d = json.load(f)

    n_xs = d["n_cross_sections"]
    pt_list = d.get("hecras_pt")
    if not pt_list or not any(p for p in pt_list):
        return {"case": d["case_name"], "status": "SKIP", "reason": "No HEC-RAS PT"}

    print(f"\n=== {d['case_name']} ({n_xs} XS) ===")

    manning_n = [max(v, 0.001) if v else 0.03 for v in d["manning_n_ch"]]
    n_lob_raw = d["manning_n_lob"]
    n_rob_raw = d["manning_n_rob"]
    lb_raw = d["left_bank_sta_m"]
    rb_raw = d["right_bank_sta_m"]

    k_errors = []
    beta_errors = []

    for i in range(n_xs):
        xs = d["xs_profiles"][i]
        pt = pt_list[i]
        if pt is None:
            continue

        sta = np.array(xs["stations_m"])
        elev = np.array(xs["elevations_m"])
        bed = float(np.min(elev))

        n_ch = manning_n[i]
        n_lob = max(n_lob_raw[i], 0.01) if n_lob_raw[i] and n_lob_raw[i] > 0 else n_ch
        n_rob = max(n_rob_raw[i], 0.01) if n_rob_raw[i] and n_rob_raw[i] > 0 else n_ch
        lb = lb_raw[i] if lb_raw[i] is not None else 0.0
        rb = rb_raw[i] if rb_raw[i] is not None else float(sta[-1])

        # HEC-RAS PT 的 K 和 beta
        hecras_elev = np.array(pt["elevations_m"])
        hecras_K = np.array(pt["K_m3s"])
        hecras_beta = np.array(pt["beta"]) if "beta" in pt else None

        # 选择对比水位点（跳过太低和太高的）
        for wl in hecras_elev:
            if wl <= bed + 0.01:
                continue
            # 自建 K
            K_calc, A_calc, beta_calc = subdivided_conveyance_with_beta(
                sta, elev, wl, lb, rb, n_lob, n_ch, n_rob)
            # HEC-RAS K
            K_hecras = float(np.interp(wl, hecras_elev, hecras_K))

            if K_hecras > 1e-6 and K_calc > 1e-6:
                rel_err = abs(K_calc - K_hecras) / K_hecras
                k_errors.append(rel_err)

            if hecras_beta is not None:
                beta_hecras = float(np.interp(wl, hecras_elev, hecras_beta))
                if beta_hecras >= 1.0 and beta_calc >= 1.0:
                    beta_err = abs(beta_calc - beta_hecras) / max(beta_hecras, 1.0)
                    beta_errors.append(beta_err)

    if not k_errors:
        print("  No valid K comparisons")
        return {"case": d["case_name"], "status": "SKIP"}

    k_arr = np.array(k_errors)
    print(f"  K comparisons: {len(k_arr)}")
    print(f"  K relative error: mean={k_arr.mean():.4f}, max={k_arr.max():.4f}, "
          f"median={np.median(k_arr):.4f}")
    print(f"  K within 5%: {np.sum(k_arr < 0.05)}/{len(k_arr)} ({100*np.sum(k_arr < 0.05)/len(k_arr):.1f}%)")
    print(f"  K within 10%: {np.sum(k_arr < 0.10)}/{len(k_arr)} ({100*np.sum(k_arr < 0.10)/len(k_arr):.1f}%)")

    if beta_errors:
        b_arr = np.array(beta_errors)
        print(f"  Beta comparisons: {len(b_arr)}")
        print(f"  Beta relative error: mean={b_arr.mean():.4f}, max={b_arr.max():.4f}")

    verdict = "PASS" if k_arr.mean() < 0.05 else ("NEAR" if k_arr.mean() < 0.10 else "FAIL")
    print(f"  Verdict: [{verdict}]")

    return {
        "case": d["case_name"],
        "status": verdict,
        "k_mean_err": float(k_arr.mean()),
        "k_max_err": float(k_arr.max()),
        "n_comparisons": len(k_arr),
    }


if __name__ == "__main__":
    cases = [
        "MixedFlowRegime_unsteady_ref.json",
        "Example20_LateralWeir_unsteady_ref.json",
        "CulvertHydraulics_unsteady_ref.json",
        "DamBreaching_unsteady_ref.json",
        "JunctionHydraulics_unsteady_ref.json",
        "Example17_Unsteady_unsteady_ref.json",
        "MultipleReaches_unsteady_ref.json",
    ]

    results = []
    for fn in cases:
        path = os.path.join(REF_DIR, fn)
        if not os.path.exists(path):
            continue
        try:
            r = validate_case(path)
            results.append(r)
        except Exception as e:
            print(f"  ERROR: {e}")
            import traceback
            traceback.print_exc()

    print(f"\n{'='*60}")
    print("SUMMARY")
    print(f"{'='*60}")
    for r in results:
        if r["status"] == "SKIP":
            print(f"  {r['case']:<35} SKIP")
        else:
            print(f"  {r['case']:<35} K_err={r['k_mean_err']:.4f} [{r['status']}]")
