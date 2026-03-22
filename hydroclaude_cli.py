#!/usr/bin/env python3
"""HydroClaude CLI — 稳态水面线计算命令行工具。

参考 pipedream CLI 设计模式。

命令:
  run      运行稳态水面线计算
  compare  与 HEC-RAS 参考数据对标
  batch    批量对标所有案例
  info     显示案例信息
"""

import argparse
import json
import sys
from pathlib import Path
from typing import Any

import numpy as np

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT))

from solvers.steady_profile_solver import SteadyProfileSolver
from physics.cross_section import NaturalSection

LF = 0.3048


def _to_jsonable(obj: Any) -> Any:
    if isinstance(obj, np.ndarray):
        return obj.tolist()
    if isinstance(obj, np.generic):
        return obj.item()
    if isinstance(obj, dict):
        return {str(k): _to_jsonable(v) for k, v in obj.items()}
    if isinstance(obj, (list, tuple)):
        return [_to_jsonable(v) for v in obj]
    return obj


def _build_from_ref(ref: dict):
    """从参考数据 JSON 构建求解器。"""
    n_xs = ref["n_cross_sections"]
    gd = ref["geometry"]["cross_sections"]
    sections, bed, rl, nch, nlob, nrob, bsl, bsr, cc, ec, nsa = (
        [], [], [], [], [], [], [], [], [], [], [])
    for i, xg in enumerate(gd):
        pts = xg["station_elevation"]
        dm = np.array([p[0] * LF for p in pts])
        em = np.array([p[1] * LF for p in pts])
        nr = xg.get("manning_n", [])
        nsa.append([(s * LF, n) for s, n in nr])
        vn = [n for _, n in nr if n is not None and n > 0]
        nc = vn[1] if len(vn) > 2 else (vn[0] if vn else 0.04)
        nl = vn[0] if vn else 0.1
        nrv = vn[-1] if len(vn) > 1 else nl
        lb = float(xg["left_bank_ft"]) * LF
        rb = float(xg["right_bank_ft"]) * LF
        sec = NaturalSection(name=f"XS{i}", elevations=em, distances=dm)
        sections.append(sec)
        bed.append(float(np.min(em)))
        rl.append(float(xg["len_channel_ft"]) * LF)
        nch.append(nc); nlob.append(nl); nrob.append(nrv)
        bsl.append(lb); bsr.append(rb)
        cc.append(float(xg.get("contraction", 0.1)))
        ec.append(float(xg.get("expansion", 0.3)))
    ifa = ref.get("ineffective_areas", [])

    # 涵洞参数：自动确定 us_xs_index（根据 invert 高程匹配最近断面）
    culverts_param = []
    for cv in ref.get("culverts", []):
        us_inv = cv.get("us_invert_m", 0)
        best_i = n_xs // 2  # 默认中间
        best_diff = 1e9
        for i in range(n_xs - 1):
            diff = abs(bed[i] - us_inv)
            if diff < best_diff:
                best_diff = diff
                best_i = i
        culverts_param.append({
            "us_xs_index": best_i,
            "shape": cv.get("shape", "circular"),
            "diameter_m": cv.get("diameter_m") or cv.get("height_m", 1.0),
            "height_m": cv.get("height_m", 1.0),
            "width_m": cv.get("width_m", 1.0),
            "length_m": cv.get("length_m", 30.0),
            "us_invert_m": cv.get("us_invert_m", 0),
            "ds_invert_m": cv.get("ds_invert_m", 0),
            "n_barrels": cv.get("n_barrels", 1),
            "manning_n": cv.get("manning_n", 0.013),
            "entrance_loss_coef": cv.get("entrance_loss_coef", 0.5),
        })

    return sections, bed, rl, nch, nlob, nrob, bsl, bsr, cc, ec, nsa, ifa, culverts_param, n_xs


def _make_solver(sections, bed, rl, nch, nlob, nrob, bsl, bsr, cc, ec, nsa, ifa, culverts, lat):
    sv = SteadyProfileSolver(
        length=max(sum(rl), 1), cross_sections=sections, bed_elevations=bed,
        reach_lengths=rl, manning_ns=nch, manning_n_lob=nlob, manning_n_rob=nrob,
        bank_stations=list(zip(bsl, bsr)), contraction_coefs=cc, expansion_coefs=ec,
        lateral_inflows=lat, culverts=culverts if culverts else None)
    sv._manning_n_segments = nsa
    sv._ineffective_areas = ifa
    return sv


def _run_profile(ref, p_idx, sections, bed, rl, nch, nlob, nrob, bsl, bsr, cc, ec, nsa, ifa, culverts, n_xs):
    profile = ref["profiles"][p_idx]
    xd = profile["cross_sections"]
    Q = float(xd[0]["flow_m3s"])
    wr = [float(x["wse_m"]) for x in xd]
    hd = max(wr[-1] - bed[-1], 0.5)
    lat = [0.0] * n_xs
    for i in range(1, n_xs):
        lat[i - 1] = float(xd[i]["flow_m3s"]) - float(xd[i - 1]["flow_m3s"])
    sv = _make_solver(sections, bed, rl, nch, nlob, nrob, bsl, bsr, cc, ec, nsa, ifa, culverts, lat)
    r = sv.solve_without_structures(Q=Q, h_downstream=hd)
    errs = [abs(float(r["W"][i]) - wr[i]) for i in range(n_xs)]
    return r, wr, errs, Q, profile["name"]


def cmd_run(args):
    with open(args.ref_data, encoding="utf-8") as f:
        ref = json.load(f)
    data = _build_from_ref(ref)
    r, wr, errs, Q, name = _run_profile(ref, args.profile, *data)
    n_xs = data[-1]
    print(f"{ref['case_name']} / {name} (Q={Q:.1f} m³/s)")
    for i in range(n_xs):
        e = float(r["W"][i]) - wr[i]
        print(f"  XS{i:2d}: HC={float(r['W'][i]):8.3f}  HR={wr[i]:8.3f}  err={e:+.3f}")
    print(f"MAE = {np.mean(errs):.4f} m")
    return 0


def cmd_compare(args):
    with open(args.ref_data, encoding="utf-8") as f:
        ref = json.load(f)
    data = _build_from_ref(ref)
    print(f"{ref['case_name']}")
    pc = 0
    for p_idx in range(len(ref["profiles"])):
        try:
            _, _, errs, Q, name = _run_profile(ref, p_idx, *data)
            mae = np.mean(errs)
            st = "PASS" if mae < 0.15 else ("NEAR" if mae < 0.5 else "FAIL")
        except Exception:
            mae = 99; st = "ERR"; Q = 0; name = f"PF{p_idx}"
        if st == "PASS":
            pc += 1
        print(f"  {name:15s} Q={Q:8.1f}  MAE={mae:.3f}  {st}")
    print(f"  通过: {pc}/{len(ref['profiles'])}")
    return 0


def cmd_batch(args):
    ref_dir = Path(args.ref_dir or "reports/hecras_reference_data")
    total = passed = near = fail = 0
    for rf in sorted(ref_dir.glob("*.json")):
        with rf.open(encoding="utf-8") as f:
            ref = json.load(f)
        gd = ref.get("geometry", {}).get("cross_sections", [])
        if not gd or "station_elevation" not in gd[0]:
            continue
        try:
            data = _build_from_ref(ref)
        except Exception:
            continue
        for p_idx in range(len(ref["profiles"])):
            try:
                _, _, errs, Q, name = _run_profile(ref, p_idx, *data)
                mae = np.mean(errs)
                st = "PASS" if mae < 0.15 else ("NEAR" if mae < 0.5 else "FAIL")
            except Exception:
                mae = 99; st = "ERR"; name = f"PF{p_idx}"
            total += 1
            if st == "PASS": passed += 1
            elif st == "NEAR": near += 1
            else: fail += 1
            if not args.quiet:
                print(f"  {ref['case_name']:42s} {name:12s} {mae:.3f} {st}")
    print(f"\nPASS: {passed}/{total} ({100*passed/total:.0f}%)  NEAR: {near}  FAIL: {fail}")
    return 0 if passed == total else 1


def cmd_info(args):
    with open(args.ref_data, encoding="utf-8") as f:
        ref = json.load(f)
    print(f"案例: {ref['case_name']}")
    print(f"断面: {ref['n_cross_sections']}")
    print(f"工况: {ref['n_profiles']}")
    for p in ref["profiles"]:
        print(f"  {p['name']}: Q={float(p['cross_sections'][0]['flow_cfs']):.0f} cfs")
    for feat in ["culverts", "ineffective_areas", "inline_structure"]:
        val = ref.get(feat)
        has = bool(val) and (val if not isinstance(val, list) else any(val))
        print(f"{feat}: {'有' if has else '无'}")
    return 0


def main():
    p = argparse.ArgumentParser(prog="hydroclaude", description="HydroClaude 稳态水面线 CLI")
    sp = p.add_subparsers(dest="cmd")
    r = sp.add_parser("run", help="运行计算")
    r.add_argument("ref_data"); r.add_argument("--profile", type=int, default=0)
    r.set_defaults(func=cmd_run)
    c = sp.add_parser("compare", help="对标 HEC-RAS")
    c.add_argument("ref_data"); c.set_defaults(func=cmd_compare)
    b = sp.add_parser("batch", help="批量对标")
    b.add_argument("--ref-dir"); b.add_argument("-q", "--quiet", action="store_true")
    b.set_defaults(func=cmd_batch)
    i = sp.add_parser("info", help="案例信息")
    i.add_argument("ref_data"); i.set_defaults(func=cmd_info)
    args = p.parse_args()
    if not args.cmd:
        p.print_help(); return 1
    return args.func(args)


if __name__ == "__main__":
    sys.exit(main())
