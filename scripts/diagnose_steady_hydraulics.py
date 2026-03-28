#!/usr/bin/env python3
"""逐断面诊断：对比 HydroClaude vs HEC-RAS 中间水力变量。

两种对比模式：
  1. 给定相同 WSE → 对比 K/A/P/alpha（纯几何/水力计算差异）
  2. HydroClaude 独立求解 → 对比 WSE 和所有中间变量

用法:
    python scripts/diagnose_steady_hydraulics.py [case_pattern] [profile_index]
    python scripts/diagnose_steady_hydraulics.py                     # 默认全部案例
    python scripts/diagnose_steady_hydraulics.py "example_1"         # Example 1
    python scripts/diagnose_steady_hydraulics.py "example_15" 2      # Example 15, profile 2
"""

import json
import sys
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from hydroclaude_cli import _build_from_ref, _make_solver, _run_profile
from physics.cross_section import NaturalSection

LF = 0.3048

# K 单位转换: HEC-RAS US → SI
# K_us = (1.486/n)*A_ft2*R_ft^(2/3), K_si = (1/n)*A_m2*R_m^(2/3)
# K_si = K_us * LF^(8/3) / 1.486
K_US_TO_SI = LF ** (8.0 / 3.0) / 1.486
A_US_TO_SI = LF ** 2


def _pct(hc_val: float, ras_val: float) -> float:
    if abs(ras_val) < 1e-9:
        return 0.0 if abs(hc_val) < 1e-9 else 999.9
    return (hc_val - ras_val) / ras_val * 100.0


def diagnose_at_hecras_wse(ref_path: Path, profile_idx: int = 0, verbose: bool = True) -> dict | None:
    """用 HEC-RAS 的 WSE 反推 HydroClaude 的 K/A/P/alpha，对比纯水力计算差异。"""
    with open(ref_path, encoding="utf-8") as f:
        ref = json.load(f)

    case_name = ref.get("case_name", ref_path.stem)
    profiles = ref.get("profiles", [])
    if profile_idx >= len(profiles):
        return None

    gd = ref.get("geometry", {}).get("cross_sections", [])
    if not gd or "station_elevation" not in gd[0]:
        return None

    pf = profiles[profile_idx]
    pf_name = pf.get("name", f"PF#{profile_idx}")
    hecras_xs = pf["cross_sections"]
    n_xs = len(hecras_xs)

    # Build solver (same way as CLI)
    data = _build_from_ref(ref)
    sections, bed_list, rl, rl_lob, rl_rob, nch, nlob, nrob, bsl, bsr, cc, ec, nsa, ifa, culverts, bridges, _ = data

    lat = [0.0] * n_xs

    # 冰盖参数（与 CLI 保持一致）
    _ice_data = ref.get("ice_cover")
    _ice_t_arr = None
    _ice_n_arr = None
    if _ice_data:
        _t = float(_ice_data.get("thickness_m", 0))
        _n = float(_ice_data.get("manning_n", 0))
        if _t > 0:
            _ice_t_arr = [_t] * n_xs
            _ice_n_arr = [_n if _n > 0 else 0.03] * n_xs

    sv = _make_solver(sections, bed_list, rl, nch, nlob, nrob, bsl, bsr, cc, ec, nsa, ifa, culverts, lat,
                      rl_lob=rl_lob, rl_rob=rl_rob, bridges=bridges,
                      ice_thickness=_ice_t_arr, n_ice=_ice_n_arr)

    bed = np.array(bed_list)
    rows = []
    for i in range(n_xs):
        hr = hecras_xs[i]
        wse_ras = float(hr["wse_m"])
        h_i = max(wse_ras - bed[i], 0.001)

        # HydroClaude 在 HEC-RAS 的 WSE 下计算的水力变量
        detail = sv._compute_subdivided_conveyance_detailed(h_i, i)
        K_hc = detail["K_total"]
        K_ch_hc = detail["K_ch"]
        K_lob_hc = detail["K_lob"]
        K_rob_hc = detail["K_rob"]
        A_hc = detail["A_total"]
        A_ch_hc = detail["A_ch"]
        A_lob_hc = detail["A_lob"]
        A_rob_hc = detail["A_rob"]
        alpha_hc = detail["alpha"]

        # HEC-RAS 参考值（转 SI），处理缺失字段
        K_ras = float(hr.get("conveyance_total", 0)) * K_US_TO_SI
        K_ch_ras = float(hr.get("conveyance_channel", 0)) * K_US_TO_SI
        K_lob_ras = float(hr.get("conveyance_left_ob", 0)) * K_US_TO_SI
        K_rob_ras = float(hr.get("conveyance_right_ob", 0)) * K_US_TO_SI
        A_ras = float(hr.get("area_flow_total", 0)) * A_US_TO_SI
        A_ch_ras = float(hr.get("area_flow_channel", 0)) * A_US_TO_SI
        A_lob_ras = float(hr.get("area_flow_left_ob", 0)) * A_US_TO_SI
        A_rob_ras = float(hr.get("area_flow_right_ob", 0)) * A_US_TO_SI
        alpha_ras = float(hr.get("alpha", 1.0))
        Sf_ras = float(hr.get("friction_slope", 0))

        Q_m3s = float(hr["flow_m3s"])
        Sf_hc = (Q_m3s / K_hc) ** 2 if K_hc > 0 else 0.0

        row = {
            "xs": i, "wse": wse_ras,
            "K_hc": K_hc, "K_ras": K_ras, "K_err%": _pct(K_hc, K_ras),
            "K_ch_hc": K_ch_hc, "K_ch_ras": K_ch_ras, "K_ch_err%": _pct(K_ch_hc, K_ch_ras),
            "K_lob_hc": K_lob_hc, "K_lob_ras": K_lob_ras, "K_lob_err%": _pct(K_lob_hc, K_lob_ras),
            "K_rob_hc": K_rob_hc, "K_rob_ras": K_rob_ras, "K_rob_err%": _pct(K_rob_hc, K_rob_ras),
            "A_hc": A_hc, "A_ras": A_ras, "A_err%": _pct(A_hc, A_ras),
            "A_ch_hc": A_ch_hc, "A_ch_ras": A_ch_ras, "A_ch_err%": _pct(A_ch_hc, A_ch_ras),
            "A_lob_hc": A_lob_hc, "A_lob_ras": A_lob_ras, "A_lob_err%": _pct(A_lob_hc, A_lob_ras),
            "A_rob_hc": A_rob_hc, "A_rob_ras": A_rob_ras, "A_rob_err%": _pct(A_rob_hc, A_rob_ras),
            "alpha_hc": alpha_hc, "alpha_ras": alpha_ras, "alpha_err%": _pct(alpha_hc, alpha_ras),
            "Sf_hc": Sf_hc, "Sf_ras": Sf_ras, "Sf_err%": _pct(Sf_hc, Sf_ras),
            "n_ch": detail["n_ch"], "n_lob": detail["n_lob"], "n_rob": detail["n_rob"],
            "manning_n_ras": float(hr.get("manning_n_channel", 0)),
        }
        rows.append(row)

    K_errs = [abs(r["K_err%"]) for r in rows]
    A_errs = [abs(r["A_err%"]) for r in rows]
    alpha_errs = [abs(r["alpha_err%"]) for r in rows]
    Sf_errs = [abs(r["Sf_err%"]) for r in rows]

    summary = {
        "case": case_name, "profile": pf_name, "n_xs": n_xs,
        "mean_K_err%": np.mean(K_errs), "max_K_err%": max(K_errs),
        "mean_A_err%": np.mean(A_errs),
        "mean_Sf_err%": np.mean(Sf_errs),
        "mean_alpha_err%": np.mean(alpha_errs),
    }

    if verbose:
        print(f"\n{'='*120}")
        print(f"  {case_name} — {pf_name}  (at HEC-RAS WSE)")
        print(f"{'='*120}")
        print(f"{'XS':>3} {'WSE':>8} | {'K_tot%':>7} {'K_ch%':>7} {'K_lob%':>7} {'K_rob%':>7} | "
              f"{'A_tot%':>7} {'A_ch%':>7} | {'Sf%':>8} {'α%':>7} | {'n_ch':>5} {'n_ras':>5}")
        print("-" * 120)
        for r in rows:
            flag = " ***" if abs(r["K_err%"]) > 10 else ""
            print(f"{r['xs']:3d} {r['wse']:8.3f} | "
                  f"{r['K_err%']:+7.1f} {r['K_ch_err%']:+7.1f} {r['K_lob_err%']:+7.1f} {r['K_rob_err%']:+7.1f} | "
                  f"{r['A_err%']:+7.1f} {r['A_ch_err%']:+7.1f} | "
                  f"{r['Sf_err%']:+8.1f} {r['alpha_err%']:+7.1f} | "
                  f"{r['n_ch']:.4f} {r['manning_n_ras']:.4f}{flag}")

        print(f"\n  K_err: mean={np.mean(K_errs):.1f}%  max={max(K_errs):.1f}%  (XS{int(np.argmax(K_errs))})")
        print(f"  A_err: mean={np.mean(A_errs):.1f}%  max={max(A_errs):.1f}%")
        print(f"  Sf_err: mean={np.mean(Sf_errs):.1f}%  alpha_err: mean={np.mean(alpha_errs):.1f}%")

        # Top 3 worst K
        worst = sorted(range(n_xs), key=lambda j: abs(rows[j]["K_err%"]), reverse=True)[:3]
        for j in worst:
            r = rows[j]
            print(f"  XS{j}: K_hc={r['K_hc']:.0f} K_ras={r['K_ras']:.0f} ({r['K_err%']:+.1f}%) | "
                  f"Kch={r['K_ch_hc']:.0f}/{r['K_ch_ras']:.0f} Klob={r['K_lob_hc']:.0f}/{r['K_lob_ras']:.0f} "
                  f"Krob={r['K_rob_hc']:.0f}/{r['K_rob_ras']:.0f}")

    return {"summary": summary, "rows": rows}


def diagnose_with_solve(ref_path: Path, profile_idx: int = 0, verbose: bool = True) -> dict | None:
    """运行 HydroClaude 求解，对比 WSE 和中间变量。"""
    with open(ref_path, encoding="utf-8") as f:
        ref = json.load(f)

    case_name = ref.get("case_name", ref_path.stem)
    profiles = ref.get("profiles", [])
    if profile_idx >= len(profiles):
        return None

    gd = ref.get("geometry", {}).get("cross_sections", [])
    if not gd or "station_elevation" not in gd[0]:
        return None

    data = _build_from_ref(ref)
    sections, bed_list, rl, rl_lob, rl_rob, nch, nlob, nrob, bsl, bsr, cc, ec, nsa, ifa, culverts, bridges, n_xs = data

    try:
        r0, wr, errs, Q, pf_name = _run_profile(ref, profile_idx, *data)
    except Exception as e:
        if verbose:
            print(f"  {case_name} PF#{profile_idx}: solve failed: {e}")
        return None

    W_hc = np.asarray(r0["W"], dtype=float)
    bed = np.array(bed_list)

    # Build a solver for post-hoc analysis
    lat = [0.0] * n_xs

    _ice_data = ref.get("ice_cover")
    _ice_t_arr = None
    _ice_n_arr = None
    if _ice_data:
        _t = float(_ice_data.get("thickness_m", 0))
        _n = float(_ice_data.get("manning_n", 0))
        if _t > 0:
            _ice_t_arr = [_t] * n_xs
            _ice_n_arr = [_n if _n > 0 else 0.03] * n_xs

    sv = _make_solver(sections, bed_list, rl, nch, nlob, nrob, bsl, bsr, cc, ec, nsa, ifa, culverts, lat,
                      rl_lob=rl_lob, rl_rob=rl_rob, bridges=bridges,
                      ice_thickness=_ice_t_arr, n_ice=_ice_n_arr)

    hecras_xs = profiles[profile_idx]["cross_sections"]
    mae = np.mean(errs)

    rows = []
    for i in range(n_xs):
        hr = hecras_xs[i]
        wse_ras = float(hr["wse_m"])
        wse_hc = float(W_hc[i])
        h_hc = max(wse_hc - bed[i], 0.001)

        detail = sv._compute_subdivided_conveyance_detailed(h_hc, i)
        K_hc = detail["K_total"]
        K_ch_hc = detail["K_ch"]
        K_lob_hc = detail["K_lob"]
        K_rob_hc = detail["K_rob"]
        A_hc = detail["A_total"]
        alpha_hc = detail["alpha"]

        K_ras = float(hr.get("conveyance_total", 0)) * K_US_TO_SI
        K_ch_ras = float(hr.get("conveyance_channel", 0)) * K_US_TO_SI
        K_lob_ras = float(hr.get("conveyance_left_ob", 0)) * K_US_TO_SI
        K_rob_ras = float(hr.get("conveyance_right_ob", 0)) * K_US_TO_SI
        A_ras = float(hr.get("area_flow_total", 0)) * A_US_TO_SI
        alpha_ras = float(hr.get("alpha", 1.0))
        Sf_ras = float(hr.get("friction_slope", 0))
        Q_m3s = float(hr["flow_m3s"])
        Sf_hc = (Q_m3s / K_hc) ** 2 if K_hc > 0 else 0.0

        rows.append({
            "xs": i, "wse_ras": wse_ras, "wse_hc": wse_hc, "wse_err": wse_hc - wse_ras,
            "K_hc": K_hc, "K_ras": K_ras, "K_err%": _pct(K_hc, K_ras),
            "K_ch_err%": _pct(K_ch_hc, K_ch_ras),
            "K_lob_err%": _pct(K_lob_hc, K_lob_ras),
            "K_rob_err%": _pct(K_rob_hc, K_rob_ras),
            "A_hc": A_hc, "A_ras": A_ras, "A_err%": _pct(A_hc, A_ras),
            "Sf_hc": Sf_hc, "Sf_ras": Sf_ras, "Sf_err%": _pct(Sf_hc, Sf_ras),
            "alpha_hc": alpha_hc, "alpha_ras": alpha_ras, "alpha_err%": _pct(alpha_hc, alpha_ras),
        })

    if verbose:
        print(f"\n{'='*120}")
        print(f"  {case_name} — {pf_name}  (MAE={mae:.4f}m)")
        print(f"{'='*120}")
        print(f"{'XS':>3} {'WSE_RAS':>9} {'WSE_HC':>9} {'Err':>7} | "
              f"{'K%':>7} {'Kch%':>7} {'Klob%':>7} {'Krob%':>7} | "
              f"{'A%':>7} {'Sf%':>8} {'α%':>7}")
        print("-" * 120)
        for r in rows:
            flag = " ***" if abs(r["wse_err"]) > 0.1 else ""
            print(f"{r['xs']:3d} {r['wse_ras']:9.3f} {r['wse_hc']:9.3f} {r['wse_err']:+7.4f} | "
                  f"{r['K_err%']:+7.1f} {r['K_ch_err%']:+7.1f} {r['K_lob_err%']:+7.1f} {r['K_rob_err%']:+7.1f} | "
                  f"{r['A_err%']:+7.1f} {r['Sf_err%']:+8.1f} {r['alpha_err%']:+7.1f}{flag}")

    return {"mae": mae, "rows": rows}


def find_all_refs() -> list[Path]:
    return sorted((ROOT / "reports" / "hecras_reference_data").glob("*.json"))


def main():
    args = sys.argv[1:]
    mode = "wse"  # Default: compare at same WSE
    if "--solve" in args:
        mode = "solve"
        args.remove("--solve")

    refs = find_all_refs()
    if args and args[0] != "all":
        pattern = args[0].lower()
        refs = [r for r in refs if pattern in r.stem.lower()]
        if not refs:
            print(f"No reference file matching '{args[0]}'")
            sys.exit(1)

    pi = int(args[1]) if len(args) > 1 else None

    all_summaries = []
    for rp in refs:
        with open(rp, encoding="utf-8") as f:
            ref_data = json.load(f)
        n_pf = ref_data.get("n_profiles", 1)
        gd = ref_data.get("geometry", {}).get("cross_sections", [])
        if not gd or "station_elevation" not in gd[0]:
            continue

        pf_range = [pi] if pi is not None and pi < n_pf else range(n_pf)
        for p in pf_range:
            try:
                if mode == "wse":
                    result = diagnose_at_hecras_wse(rp, p, verbose=True)
                else:
                    result = diagnose_with_solve(rp, p, verbose=True)
                if result and "summary" in result:
                    all_summaries.append(result["summary"])
            except Exception as e:
                print(f"  ERROR {rp.stem} PF#{p}: {e}")

    if all_summaries:
        print(f"\n{'='*90}")
        print("  OVERALL — K/A Error at HEC-RAS WSE (排除 WSE 差异影响)")
        print(f"{'='*90}")
        print(f"{'Case':<45} {'Profile':<12} {'K%':>6} {'A%':>6} {'Sf%':>6} {'α%':>6}")
        print("-" * 90)
        for s in sorted(all_summaries, key=lambda x: -x["mean_K_err%"]):
            print(f"{s['case'][:44]:<45} {s['profile'][:11]:<12} "
                  f"{s['mean_K_err%']:6.1f} {s['mean_A_err%']:6.1f} "
                  f"{s['mean_Sf_err%']:6.1f} {s['mean_alpha_err%']:6.1f}")


if __name__ == "__main__":
    main()
