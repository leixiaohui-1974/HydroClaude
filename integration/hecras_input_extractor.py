"""HEC-RAS 输入数据统一提取器 — 从 HDF + 文本文件提取全部求解参数。"""
from pathlib import Path
import h5py
import numpy as np
import re
import json
import math
from typing import Optional, Iterable, Tuple, Dict, Any, List

LF = 0.3048  # ft to m
CFS_TO_M3S = 0.028316846592


def _b2s(x) -> Optional[str]:
    try:
        if x is None:
            return None
        if isinstance(x, (bytes, bytearray, np.bytes_)):
            return x.decode("utf-8", errors="ignore").strip()
        if isinstance(x, str):
            return x.strip()
        # h5py might give numpy.void for S fields boxed; attempt to cast to bytes then decode
        if isinstance(x, np.void):
            try:
                bx = bytes(x)
                return bx.decode("utf-8", errors="ignore").strip()
            except Exception:
                return str(x).strip()
        return str(x).strip()
    except Exception:
        return None


def _to_float(x, default=np.nan) -> float:
    try:
        if x is None:
            return default
        if isinstance(x, (float, int, np.floating, np.integer)):
            return float(x)
        sx = _b2s(x)
        if sx is None or sx == "":
            return default
        return float(sx)
    except Exception:
        return default


def _float_list_from_line(line: str) -> List[float]:
    nums = re.findall(r"[-+]?\d*\.?\d+(?:[eE][-+]?\d+)?", line)
    return [float(n) for n in nums]


def _get_field(row, name: str, default=None):
    try:
        if name in row.dtype.fields:
            return row[name]
    except Exception:
        pass
    return default


def _get_field_s(row, name: str, default=""):
    v = _get_field(row, name, None)
    s = _b2s(v)
    if s is None:
        return default
    return s


def _get_field_f(row, name: str, default=np.nan) -> float:
    v = _get_field(row, name, None)
    return _to_float(v, default)


def _ensure_list(x):
    if x is None:
        return []
    if isinstance(x, (list, tuple)):
        return list(x)
    return [x]


class HECRASInputExtractor:
    def __init__(self, project_dir: Path, plan_suffix: str = "p01"):
        self.project_dir = Path(project_dir)
        self.plan_suffix = plan_suffix.lower().strip().lstrip(".")  # e.g., p01
        self.case_name = None

        # Discovered paths
        self.geometry_hdf_path: Optional[Path] = None
        self.results_hdf_path: Optional[Path] = None
        self.flow_file_path: Optional[Path] = None
        self.geometry_g01_path: Optional[Path] = None
        self.geometry_g02_path: Optional[Path] = None
        self.project_prj_path: Optional[Path] = None
        self.plan_file_path: Optional[Path] = None

        # Run discovery
        try:
            self._discover_project_files()
        except Exception as e:
            # TODO: log/print if needed; keep silent for robustness
            pass

    # ------------------------- Discovery helpers -------------------------

    def _discover_project_files(self):
        # Find .prj (project) file
        prj_files = sorted(self.project_dir.glob("*.prj"))
        if prj_files:
            self.project_prj_path = prj_files[0]
            self.case_name = self._parse_case_name_from_prj(self.project_prj_path)
        if not self.case_name:
            # fallback: directory name
            self.case_name = self.project_dir.name

        # Find plan file for suffix (e.g., *.p01)
        plan_pattern = f"*.{self.plan_suffix}"
        plan_files = sorted(self.project_dir.glob(plan_pattern))
        if not plan_files:
            # try recursive search
            plan_files = sorted(self.project_dir.rglob(plan_pattern))
        if plan_files:
            self.plan_file_path = plan_files[0]

        # Geometry HDF: prefer *.g01.hdf then *.g02.hdf
        g01_hdf = sorted(self.project_dir.glob("*.g01.hdf"))
        if not g01_hdf:
            g01_hdf = sorted(self.project_dir.rglob("*.g01.hdf"))
        g02_hdf = sorted(self.project_dir.glob("*.g02.hdf"))
        if not g02_hdf:
            g02_hdf = sorted(self.project_dir.rglob("*.g02.hdf"))
        if g01_hdf:
            self.geometry_hdf_path = g01_hdf[0]
        elif g02_hdf:
            self.geometry_hdf_path = g02_hdf[0]

        # Results HDF: *.{plan_suffix}.hdf
        results_hdf = sorted(self.project_dir.glob(f"*.{self.plan_suffix}.hdf"))
        if not results_hdf:
            results_hdf = sorted(self.project_dir.rglob(f"*.{self.plan_suffix}.hdf"))
        if results_hdf:
            self.results_hdf_path = results_hdf[0]

        # Text geometry g01/g02
        g01_txt = sorted(self.project_dir.glob("*.g01"))
        if not g01_txt:
            g01_txt = sorted(self.project_dir.rglob("*.g01"))
        g02_txt = sorted(self.project_dir.glob("*.g02"))
        if not g02_txt:
            g02_txt = sorted(self.project_dir.rglob("*.g02"))
        if g01_txt:
            self.geometry_g01_path = g01_txt[0]
        if g02_txt:
            self.geometry_g02_path = g02_txt[0]

        # Flow file: determined by plan file "Flow File=" or fallback *.f01
        ff = None
        if self.plan_file_path and self.plan_file_path.exists():
            try:
                with open(self.plan_file_path, "r", encoding="utf-8", errors="ignore") as f:
                    text = f.read()
                m = re.search(r"(?im)^\s*Flow\s+File\s*=\s*(.+)\s*$", text)
                if m:
                    val = m.group(1).strip()
                    # Could be quoted or include extension or not
                    val = val.strip('"').strip("'").strip()
                    # If includes folder, keep relative to project_dir
                    candidate = Path(val)
                    if not candidate.suffix:
                        # Append flow suffix e.g., .f01 from plan suffix?
                        # Use .fXX if plan_suffix is pXX
                        fsfx = "f01"
                        if self.plan_suffix.startswith("p") and len(self.plan_suffix) == 3 and self.plan_suffix[1:].isdigit():
                            fsfx = "f" + self.plan_suffix[1:]
                        candidate = candidate.with_suffix("." + fsfx)
                    # Resolve relative
                    if not candidate.is_absolute():
                        candidate = self.project_dir / candidate
                    if candidate.exists():
                        ff = candidate
            except Exception:
                pass
        if ff is None:
            # fallback search *.f?? aligned with plan
            fpat = f"*.f{self.plan_suffix[1:]}" if (self.plan_suffix.startswith("p") and len(self.plan_suffix) == 3 and self.plan_suffix[1:].isdigit()) else "*.f01"
            ffiles = sorted(self.project_dir.glob(fpat))
            if not ffiles:
                ffiles = sorted(self.project_dir.rglob(fpat))
            if not ffiles:
                # broad fallback
                ffiles = sorted(self.project_dir.glob("*.f01"))
            if ffiles:
                ff = ffiles[0]
        self.flow_file_path = ff

    def _parse_case_name_from_prj(self, prj_path: Path) -> Optional[str]:
        try:
            with open(prj_path, "r", encoding="utf-8", errors="ignore") as f:
                for line in f:
                    m = re.match(r"^\s*Project\s+Title\s*=\s*(.+?)\s*$", line, flags=re.IGNORECASE)
                    if m:
                        title = m.group(1).strip()
                        title = title.strip('"').strip("'").strip()
                        if title:
                            return title
        except Exception:
            pass
        return None

    # ------------------------- HDF helpers -------------------------

    def _iter_datasets(self, hdf: h5py.File, root: Optional[h5py.Group] = None, prefix: str = "") -> Iterable[Tuple[str, h5py.Dataset]]:
        grp = root if root is not None else hdf
        for key, item in grp.items():
            path = f"{prefix}/{key}" if prefix else key
            if isinstance(item, h5py.Dataset):
                yield (path, item)
            elif isinstance(item, h5py.Group):
                yield from self._iter_datasets(hdf, item, path)

    def _find_dataset_paths_by_name(self, hdf: h5py.File, target_names: List[str]) -> Dict[str, str]:
        """Return mapping of matched target name -> dataset path; matches by last component equals name."""
        names_lower = {n.lower(): n for n in target_names}
        found: Dict[str, str] = {}
        for path, dset in self._iter_datasets(hdf):
            last = path.split("/")[-1]
            ll = last.lower()
            if ll in names_lower and names_lower[ll] not in found:
                found[names_lower[ll]] = path
        return found

    def _get_dataset(self, hdf: h5py.File, target_names: List[str]) -> Optional[h5py.Dataset]:
        found = self._find_dataset_paths_by_name(hdf, target_names)
        if not found:
            return None
        # choose first deterministically by target_names order
        for n in target_names:
            if n in found:
                try:
                    return hdf[found[n]]
                except Exception:
                    continue
        # fallback first value
        try:
            return hdf[list(found.values())[0]]
        except Exception:
            return None

    # ------------------------- HDF extractors -------------------------

    def _hdf_get(self, hdf: "h5py.File", *paths: str) -> "Optional[h5py.Dataset]":
        """Try multiple direct HDF paths, return first existing dataset or None."""
        for path in paths:
            try:
                if path in hdf:
                    return hdf[path]
            except Exception:
                pass
        return None

    def _extract_cross_sections(self, hdf) -> list[dict]:
        xs_list: List[dict] = []
        try:
            attrs_ds = self._hdf_get(hdf, "Geometry/Cross Sections/Attributes")
            if attrs_ds is None:
                return xs_list
            attrs = attrs_ds[...]
            n_xs = int(attrs.shape[0])

            # Station-Elevation pairing
            se_info_ds = self._hdf_get(hdf, "Geometry/Cross Sections/Station Elevation Info")
            se_vals_ds = self._hdf_get(hdf, "Geometry/Cross Sections/Station Elevation Values")
            se_info = se_info_ds[...] if se_info_ds is not None else None
            se_vals = se_vals_ds[...] if se_vals_ds is not None else None

            # Manning's n
            n_info_ds = self._hdf_get(hdf, "Geometry/Cross Sections/Manning's n Info",
                "Geometry/Cross Sections/Mannings n Info")
            n_info = n_info_ds[...] if n_info_ds is not None else None
            n_vals_ds = self._hdf_get(hdf, "Geometry/Cross Sections/Manning's n Values",
                "Geometry/Cross Sections/Mannings n Values")
            n_vals = n_vals_ds[...] if n_vals_ds is not None else None

            # Ineffective areas
            ia_list = self._extract_ineffective_areas(hdf, n_xs)

            for i in range(n_xs):
                row = attrs[i]
                river = _get_field_s(row, "River")
                reach = _get_field_s(row, "Reach")
                rs = _get_field_s(row, "RS")
                name = _get_field_s(row, "Name")
                desc = _get_field_s(row, "Description")

                len_left_ft = _get_field_f(row, "Len Left")
                len_ch_ft = _get_field_f(row, "Len Channel")
                len_right_ft = _get_field_f(row, "Len Right")
                left_bank_ft = _get_field_f(row, "Left Bank")
                right_bank_ft = _get_field_f(row, "Right Bank")
                friction_mode = _get_field_s(row, "Friction Mode")
                contr = _get_field_f(row, "Contr", default=np.nan)
                expan = _get_field_f(row, "Expan", default=np.nan)

                # station-elev slice
                station_elev_ft = []
                station_elev_m = []
                if se_info is not None and se_vals is not None:
                    try:
                        start = int(se_info[i, 0])
                        count = int(se_info[i, 1])
                        if count > 0 and start >= 0:
                            seg = se_vals[start:start + count, :]
                            for j in range(seg.shape[0]):
                                sta_ft = float(seg[j, 0])
                                ele_ft = float(seg[j, 1])
                                station_elev_ft.append([sta_ft, ele_ft])
                                station_elev_m.append([sta_ft * LF, ele_ft * LF])
                    except Exception:
                        pass

                # Manning's n curve per XS
                mannings_n = []
                if n_info is not None and n_vals is not None:
                    try:
                        n_start = int(n_info[i, 0])
                        n_count = int(n_info[i, 1])
                        if n_count > 0 and n_start >= 0:
                            seg = n_vals[n_start:n_start + n_count, :]
                            for j in range(seg.shape[0]):
                                sta_ft = float(seg[j, 0])
                                n_val = float(seg[j, 1])
                                mannings_n.append([sta_ft, n_val])
                    except Exception:
                        pass

                xs_entry = {
                    "index": i,
                    "river": river,
                    "reach": reach,
                    "rs": rs,
                    "name": name,
                    "description": desc,
                    "length_left_ft": float(len_left_ft) if not math.isnan(len_left_ft) else None,
                    "length_left_m": float(len_left_ft * LF) if not math.isnan(len_left_ft) else None,
                    "length_channel_ft": float(len_ch_ft) if not math.isnan(len_ch_ft) else None,
                    "length_channel_m": float(len_ch_ft * LF) if not math.isnan(len_ch_ft) else None,
                    "length_right_ft": float(len_right_ft) if not math.isnan(len_right_ft) else None,
                    "length_right_m": float(len_right_ft * LF) if not math.isnan(len_right_ft) else None,
                    "left_bank_station_ft": float(left_bank_ft) if not math.isnan(left_bank_ft) else None,
                    "left_bank_station_m": float(left_bank_ft * LF) if not math.isnan(left_bank_ft) else None,
                    "right_bank_station_ft": float(right_bank_ft) if not math.isnan(right_bank_ft) else None,
                    "right_bank_station_m": float(right_bank_ft * LF) if not math.isnan(right_bank_ft) else None,
                    "friction_mode": friction_mode,
                    "contraction_coef": float(contr) if not math.isnan(contr) else None,
                    "expansion_coef": float(expan) if not math.isnan(expan) else None,
                    "station_elevation_ft": station_elev_ft,
                    "station_elevation_m": station_elev_m,
                    "mannings_n": mannings_n,
                    "ineffective_areas": ia_list[i] if i < len(ia_list) else []
                }
                xs_list.append(xs_entry)
        except Exception:
            # return what we have collected so far
            return xs_list
        return xs_list

    def _extract_ineffective_areas(self, hdf, n_xs: int) -> list[list[dict]]:
        out: List[List[dict]] = [[] for _ in range(max(0, n_xs))]
        try:
            info_ds = self._hdf_get(hdf, "Geometry/Cross Sections/Ineffective Info")
            blocks_ds = self._hdf_get(hdf, "Geometry/Cross Sections/Ineffective Blocks")
            if info_ds is None or blocks_ds is None:
                return out
            info = info_ds[...]
            blocks = blocks_ds[...]
            for i in range(min(n_xs, info.shape[0])):
                try:
                    start = int(info[i, 0])
                    count = int(info[i, 1])
                except Exception:
                    start, count = -1, 0
                if count and start >= 0:
                    ias = []
                    seg = blocks[start:start + count]
                    for row in seg:
                        try:
                            ls = _get_field_f(row, "Left Sta")
                            rs = _get_field_f(row, "Right Sta")
                            elev = _get_field_f(row, "Elevation")
                            perm = _get_field(row, "Permanent", 0)
                            ls_ft = float(ls) if not math.isnan(ls) else None
                            ls_m = float(ls * LF) if not math.isnan(ls) else None
                            rs_ft = float(rs) if not math.isnan(rs) else None
                            rs_m = float(rs * LF) if not math.isnan(rs) else None
                            elev_ft = float(elev) if not math.isnan(elev) else None
                            elev_m = float(elev * LF) if not math.isnan(elev) else None
                            ias.append({
                                # 新格式字段
                                "left_station_ft": ls_ft,
                                "left_station_m": ls_m,
                                "right_station_ft": rs_ft,
                                "right_station_m": rs_m,
                                "elevation_ft": elev_ft,
                                "elevation_m": elev_m,
                                "permanent": bool(int(perm)) if perm is not None else False,
                                # 向后兼容别名（旧格式，供 steady_profile_solver 使用）
                                "left_sta_ft": ls_ft,
                                "left_sta_m": ls_m,
                                "right_sta_ft": rs_ft,
                                "right_sta_m": rs_m,
                            })
                        except Exception:
                            continue
                    out[i] = ias
        except Exception:
            return out
        return out

    def _extract_culverts(self, hdf) -> list[dict]:
        culverts: List[dict] = []
        try:
            structs_ds = self._hdf_get(hdf, "Geometry/Structures/Attributes")
            if structs_ds is None:
                return culverts
            structs = structs_ds[...]

            culv_groups_ds = self._hdf_get(hdf, "Geometry/Structures/Culvert Groups/Attributes")
            culv_barrels_ds = self._hdf_get(hdf, "Geometry/Structures/Culvert Groups/Barrels/Attributes")
            culv_groups = culv_groups_ds[...] if culv_groups_ds is not None else None
            culv_barrels = culv_barrels_ds[...] if culv_barrels_ds is not None else None

            # Build index: structure_id -> groups
            groups_by_sid: Dict[int, List[Dict[str, Any]]] = {}
            if culv_groups is not None:
                for idx, row in enumerate(culv_groups):
                    try:
                        sid = int(_get_field(row, "Structure ID", -1))
                        gidx = idx  # using row index as group id within culvert_groups array
                        if sid < 0:
                            continue
                        gname = _get_field_s(row, "Name")
                        shape_code = int(_get_field(row, "Shape", -1))
                        shape_name = _get_field_s(row, "Shape Name")
                        chart = int(_get_field(row, "Chart", -1))
                        chart_desc = _get_field_s(row, "Chart Desc")
                        scale = int(_get_field(row, "Scale", -1))
                        scale_desc = _get_field_s(row, "Scale Desc")
                        rise_ft = _get_field_f(row, "Rise")
                        span_ft = _get_field_f(row, "Span")
                        length_ft = _get_field_f(row, "Length")
                        us_dist_ft = _get_field_f(row, "US Distance")
                        mann_top = _get_field_f(row, "Mann Top")
                        mann_bot = _get_field_f(row, "Mann Bottom")
                        depth_for_bot_mann_ft = _get_field_f(row, "Depth for Bottom Mann")
                        depth_blocked_ft = _get_field_f(row, "Depth Blocked")
                        entrance_loss = _get_field_f(row, "Entrance Loss")
                        exit_loss = _get_field_f(row, "Exit Loss")
                        us_invert_ft = _get_field_f(row, "US Invert")
                        ds_invert_ft = _get_field_f(row, "DS Invert")
                        barrels = int(_get_field(row, "Barrels", 0))

                        groups_by_sid.setdefault(sid, []).append({
                            "culvert_group_id": gidx,
                            "name": gname,
                            "shape_code": shape_code,
                            "shape_name": shape_name,
                            "chart": chart,
                            "chart_desc": chart_desc,
                            "scale": scale,
                            "scale_desc": scale_desc,
                            "rise_ft": float(rise_ft) if not math.isnan(rise_ft) else None,
                            "rise_m": float(rise_ft * LF) if not math.isnan(rise_ft) else None,
                            "span_ft": float(span_ft) if not math.isnan(span_ft) else None,
                            "span_m": float(span_ft * LF) if not math.isnan(span_ft) else None,
                            "length_ft": float(length_ft) if not math.isnan(length_ft) else None,
                            "length_m": float(length_ft * LF) if not math.isnan(length_ft) else None,
                            "us_distance_ft": float(us_dist_ft) if not math.isnan(us_dist_ft) else None,
                            "us_distance_m": float(us_dist_ft * LF) if not math.isnan(us_dist_ft) else None,
                            "mannings_top": float(mann_top) if not math.isnan(mann_top) else None,
                            "mannings_bottom": float(mann_bot) if not math.isnan(mann_bot) else None,
                            "depth_for_bottom_mann_ft": float(depth_for_bot_mann_ft) if not math.isnan(depth_for_bot_mann_ft) else None,
                            "depth_for_bottom_mann_m": float(depth_for_bot_mann_ft * LF) if not math.isnan(depth_for_bot_mann_ft) else None,
                            "depth_blocked_ft": float(depth_blocked_ft) if not math.isnan(depth_blocked_ft) else None,
                            "depth_blocked_m": float(depth_blocked_ft * LF) if not math.isnan(depth_blocked_ft) else None,
                            "entrance_loss_coef": float(entrance_loss) if not math.isnan(entrance_loss) else None,
                            "exit_loss_coef": float(exit_loss) if not math.isnan(exit_loss) else None,
                            "us_invert_ft": float(us_invert_ft) if not math.isnan(us_invert_ft) else None,
                            "us_invert_m": float(us_invert_ft * LF) if not math.isnan(us_invert_ft) else None,
                            "ds_invert_ft": float(ds_invert_ft) if not math.isnan(ds_invert_ft) else None,
                            "ds_invert_m": float(ds_invert_ft * LF) if not math.isnan(ds_invert_ft) else None,
                            "barrels": barrels,
                            "barrels_attributes": []
                        })
                    except Exception:
                        continue

            # Attach barrels by (Structure ID, Culvert Group ID)
            if culv_barrels is not None:
                for brow in culv_barrels:
                    try:
                        sid = int(_get_field(brow, "Structure ID", -1))
                        gid = int(_get_field(brow, "Culvert Group ID", -1))
                        bname = _get_field_s(brow, "Name")
                        us_sta = _get_field_f(brow, "US Station")
                        ds_sta = _get_field_f(brow, "DS Station")
                        default_centerline = bool(int(_get_field(brow, "Default Centerline", 0)))
                        if sid in groups_by_sid:
                            # find group by culvert_group_id == gid
                            for g in groups_by_sid[sid]:
                                if g.get("culvert_group_id") == gid:
                                    g["barrels_attributes"].append({
                                        "name": bname,
                                        "us_station_ft": float(us_sta) if not math.isnan(us_sta) else None,
                                        "us_station_m": float(us_sta * LF) if not math.isnan(us_sta) else None,
                                        "ds_station_ft": float(ds_sta) if not math.isnan(ds_sta) else None,
                                        "ds_station_m": float(ds_sta * LF) if not math.isnan(ds_sta) else None,
                                        "default_centerline": default_centerline
                                    })
                                    break
                    except Exception:
                        continue

            # Build culvert structures from structures attributes
            for i, srow in enumerate(structs):
                try:
                    stype = _get_field_s(srow, "Type")
                    mode = _get_field_s(srow, "Mode")
                    river = _get_field_s(srow, "River")
                    reach = _get_field_s(srow, "Reach")
                    rs = _get_field_s(srow, "RS")
                    conn = _get_field_s(srow, "Connection")
                    groupname = _get_field_s(srow, "Groupname")
                    us_river = _get_field_s(srow, "US River")
                    us_reach = _get_field_s(srow, "US Reach")
                    us_rs = _get_field_s(srow, "US RS")
                    ds_river = _get_field_s(srow, "DS River")
                    ds_reach = _get_field_s(srow, "DS Reach")
                    ds_rs = _get_field_s(srow, "DS RS")
                    up_dist = _get_field_f(srow, "Upstream Distance")
                    weir_width = _get_field_f(srow, "Weir Width")
                    weir_max_sub = _get_field_f(srow, "Weir Max Submergence")
                    weir_min_el = _get_field_f(srow, "Weir Min Elevation")
                    weir_coef = _get_field_f(srow, "Weir Coef")
                    culv_groups_count = int(_get_field(srow, "Culvert Groups", 0))
                    gate_groups_count = int(_get_field(srow, "Gate Groups", 0))

                    # Identify culverts by culvert_groups_count > 0 or type string contains 'culvert'
                    if culv_groups_count > 0 or (stype and "culvert" in stype.lower()):
                        entry = {
                            "structure_id": i,
                            "type": stype,
                            "mode": mode,
                            "river": river,
                            "reach": reach,
                            "rs": rs,
                            "connection": conn,
                            "groupname": groupname,
                            "us_river": us_river,
                            "us_reach": us_reach,
                            "us_rs": us_rs,
                            "ds_river": ds_river,
                            "ds_reach": ds_reach,
                            "ds_rs": ds_rs,
                            "upstream_distance_ft": float(up_dist) if not math.isnan(up_dist) else None,
                            "upstream_distance_m": float(up_dist * LF) if not math.isnan(up_dist) else None,
                            "weir_width_ft": float(weir_width) if not math.isnan(weir_width) else None,
                            "weir_width_m": float(weir_width * LF) if not math.isnan(weir_width) else None,
                            "weir_max_submergence": float(weir_max_sub) if not math.isnan(weir_max_sub) else None,
                            "weir_min_elevation_ft": float(weir_min_el) if not math.isnan(weir_min_el) else None,
                            "weir_min_elevation_m": float(weir_min_el * LF) if not math.isnan(weir_min_el) else None,
                            "weir_coef": float(weir_coef) if not math.isnan(weir_coef) else None,
                            "culvert_groups_count": culv_groups_count,
                            "gate_groups_count": gate_groups_count,
                            "culvert_groups": groups_by_sid.get(i, [])
                        }
                        culverts.append(entry)
                except Exception:
                    continue
        except Exception:
            return culverts
        return culverts

    def _extract_gate_groups(self, hdf) -> list[dict]:
        gates: List[dict] = []
        try:
            gg_ds = self._hdf_get(hdf, "Geometry/Structures/Gate Groups/Attributes")
            go_ds = self._hdf_get(hdf, "Geometry/Structures/Gate Groups/Openings/Attributes")
            gg = gg_ds[...] if gg_ds is not None else None
            go = go_ds[...] if go_ds is not None else None
            if gg is None:
                return gates

            openings_by_sid_gid: Dict[Tuple[int, int], List[Dict[str, Any]]] = {}
            if go is not None:
                for idx, row in enumerate(go):
                    try:
                        sid = int(_get_field(row, "Structure ID", -1))
                        gid = int(_get_field(row, "Gate Group ID", -1))
                        name = _get_field_s(row, "Name")
                        sta = _get_field_f(row, "Station")
                        default_centerline = bool(int(_get_field(row, "Default Centerline", 0)))
                        openings_by_sid_gid.setdefault((sid, gid), []).append({
                            "name": name,
                            "station_ft": float(sta) if not math.isnan(sta) else None,
                            "station_m": float(sta * LF) if not math.isnan(sta) else None,
                            "default_centerline": default_centerline
                        })
                    except Exception:
                        continue

            for gid, row in enumerate(gg):
                try:
                    sid = int(_get_field(row, "Structure ID", -1))
                    name = _get_field_s(row, "Name")
                    width_ft = _get_field_f(row, "Width")
                    height_ft = _get_field_f(row, "Height")
                    invert_ft = _get_field_f(row, "Invert")
                    method = int(_get_field(row, "Method", -1))
                    sluice = _get_field_f(row, "Sluice Coef")
                    radial = _get_field_f(row, "Radial Coef")
                    orifice = _get_field_f(row, "Orifice Coef")
                    weir_coef = _get_field_f(row, "Weir Coef")
                    openings = int(_get_field(row, "Openings", 0))

                    gates.append({
                        "structure_id": sid,
                        "gate_group_id": gid,
                        "name": name,
                        "width_ft": float(width_ft) if not math.isnan(width_ft) else None,
                        "width_m": float(width_ft * LF) if not math.isnan(width_ft) else None,
                        "height_ft": float(height_ft) if not math.isnan(height_ft) else None,
                        "height_m": float(height_ft * LF) if not math.isnan(height_ft) else None,
                        "invert_ft": float(invert_ft) if not math.isnan(invert_ft) else None,
                        "invert_m": float(invert_ft * LF) if not math.isnan(invert_ft) else None,
                        "method": method,
                        "sluice_coef": float(sluice) if not math.isnan(sluice) else None,
                        "radial_coef": float(radial) if not math.isnan(radial) else None,
                        "orifice_coef": float(orifice) if not math.isnan(orifice) else None,
                        "weir_coef": float(weir_coef) if not math.isnan(weir_coef) else None,
                        "openings": openings,
                        "opening_stations": openings_by_sid_gid.get((sid, gid), [])
                    })
                except Exception:
                    continue
        except Exception:
            return gates
        return gates

    def _extract_bridges(self, hdf) -> list[dict]:
        bridges: List[dict] = []
        try:
            structs_ds = self._hdf_get(hdf, "Geometry/Structures/Attributes")
            if structs_ds is None:
                return bridges
            structs = structs_ds[...]

            # Piers
            piers_ds = self._hdf_get(hdf, "Geometry/Structures/Pier Attributes")
            piers = piers_ds[...] if piers_ds is not None else None
            piers_by_sid: Dict[int, List[Dict[str, Any]]] = {}
            if piers is not None:
                for row in piers:
                    try:
                        sid = int(_get_field(row, "Structure ID", -1))
                        us_sta = _get_field_f(row, "US Station")
                        ds_sta = _get_field_f(row, "DS Station")
                        use_debris = bool(int(_get_field(row, "Use Debris", 0)))
                        debris_w = _get_field_f(row, "Debris Width")
                        debris_h = _get_field_f(row, "Debris Height")
                        # Profiles indices ignored for now
                        piers_by_sid.setdefault(sid, []).append({
                            "us_station_ft": float(us_sta) if not math.isnan(us_sta) else None,
                            "us_station_m": float(us_sta * LF) if not math.isnan(us_sta) else None,
                            "ds_station_ft": float(ds_sta) if not math.isnan(ds_sta) else None,
                            "ds_station_m": float(ds_sta * LF) if not math.isnan(ds_sta) else None,
                            "use_debris": use_debris,
                            "debris_width_ft": float(debris_w) if not math.isnan(debris_w) else None,
                            "debris_width_m": float(debris_w * LF) if not math.isnan(debris_w) else None,
                            "debris_height_ft": float(debris_h) if not math.isnan(debris_h) else None,
                            "debris_height_m": float(debris_h * LF) if not math.isnan(debris_h) else None,
                        })
                    except Exception:
                        continue

            # Bridge coefficients
            bcoef_ds = self._hdf_get(hdf, "Geometry/Structures/Bridge Coefficient Attributes")
            bcoefs = bcoef_ds[...] if bcoef_ds is not None else None
            coef_by_sid: Dict[int, Dict[str, Any]] = {}
            if bcoefs is not None:
                for row in bcoefs:
                    try:
                        sid = int(_get_field(row, "Structure ID", -1))
                        method = int(_get_field(row, "Method", -1))
                        low_std_step = bool(int(_get_field(row, "Low Standard Step", 0)))
                        use_momentum = bool(int(_get_field(row, "Use Momentum", 0)))
                        momentum_cd = _get_field_f(row, "Momentum Cd")
                        use_yarnell = bool(int(_get_field(row, "Use Yarnell", 0)))
                        yarnell_k = _get_field_f(row, "Yarnell K")
                        coef_by_sid[sid] = {
                            "method": method,
                            "low_standard_step": low_std_step,
                            "use_momentum": use_momentum,
                            "momentum_cd": float(momentum_cd) if not math.isnan(momentum_cd) else None,
                            "use_yarnell": use_yarnell,
                            "yarnell_k": float(yarnell_k) if not math.isnan(yarnell_k) else None,
                        }
                    except Exception:
                        continue

            for i, srow in enumerate(structs):
                try:
                    stype = _get_field_s(srow, "Type")
                    if not stype or "bridge" not in stype.lower():
                        continue
                    river = _get_field_s(srow, "River")
                    reach = _get_field_s(srow, "Reach")
                    rs = _get_field_s(srow, "RS")
                    mode = _get_field_s(srow, "Mode")
                    up_dist = _get_field_f(srow, "Upstream Distance")
                    weir_width = _get_field_f(srow, "Weir Width")
                    # --- Extract Lid Profile (arch intrados) from Profile Data + Table Info ---
                    _lid_stations_ft: list[float] = []
                    _lid_elevations_ft: list[float] = []
                    _lid_offset_ft: float = 0.0
                    _bridge_opening_width_ft: float = float(weir_width) if not math.isnan(weir_width) else 0.0
                    _prof_data_ds = self._hdf_get(hdf, "Geometry/Structures/Profile Data")
                    _table_info_ds = self._hdf_get(hdf, "Geometry/Structures/Table Info")
                    _xs_se_info_ds = self._hdf_get(hdf, "Geometry/Cross Sections/Station Elevation Info")
                    _xs_se_vals_ds = self._hdf_get(hdf, "Geometry/Cross Sections/Station Elevation Values")
                    _xs_attrs_ds = self._hdf_get(hdf, "Geometry/Cross Sections/Attributes")
                    if (_prof_data_ds is not None and _table_info_ds is not None
                            and i < len(_table_info_ds[...])):
                        _prof_data = _prof_data_ds[...]
                        _table_info = _table_info_ds[...]
                        _ti = _table_info[i]
                        _ti_names = _ti.dtype.names if hasattr(_ti, "dtype") else ()
                        # Find US BR Lid Profile columns
                        _lid_idx_col = next((n for n in (_ti_names or ()) if "lid" in n.lower() and "us" in n.lower() and "index" in n.lower()), None)
                        _lid_cnt_col = next((n for n in (_ti_names or ()) if "lid" in n.lower() and "us" in n.lower() and "count" in n.lower()), None)
                        if _lid_idx_col is None:
                            # fallback: any lid index/count
                            _lid_idx_col = next((n for n in (_ti_names or ()) if "lid" in n.lower() and "index" in n.lower()), None)
                            _lid_cnt_col = next((n for n in (_ti_names or ()) if "lid" in n.lower() and "count" in n.lower()), None)
                        if _lid_idx_col and _lid_cnt_col:
                            _lid_start = int(_ti[_lid_idx_col])
                            _lid_count = int(_ti[_lid_cnt_col])
                            if _lid_count > 0 and _lid_start + _lid_count <= len(_prof_data):
                                _lid_data = _prof_data[_lid_start:_lid_start + _lid_count]
                                _lid_stations_ft = [float(r[0]) for r in _lid_data]
                                _lid_elevations_ft = [float(r[1]) for r in _lid_data]
                                # Opening width = station range where lid > 0
                                _lid_nonzero = [s for s, e in zip(_lid_stations_ft, _lid_elevations_ft) if e > 0.01]
                                if len(_lid_nonzero) >= 2:
                                    _bridge_opening_width_ft = float(_lid_nonzero[-1]) - float(_lid_nonzero[0])
                    # Get US approach XS min elevation as Lid Profile offset (relative -> absolute)
                    _us_rs_val = _get_field_s(srow, "US RS") if "US RS" in srow.dtype.names else ""
                    if (_xs_se_info_ds is not None and _xs_se_vals_ds is not None
                            and _xs_attrs_ds is not None and _us_rs_val):
                        try:
                            _se_info = _xs_se_info_ds[...]
                            _se_vals = np.asarray(_xs_se_vals_ds[...], dtype=float)
                            _xs_attrs_arr = _xs_attrs_ds[...]
                            for _xi, _xa in enumerate(_xs_attrs_arr):
                                _xa_rs = _get_field_s(_xa, "RS") if "RS" in _xa.dtype.names else ""
                                if _xa_rs.strip() == _us_rs_val.strip() and _xi < len(_se_info):
                                    _xstart = int(_se_info[_xi][0])
                                    _xcount = int(_se_info[_xi][1])
                                    if _xcount > 0 and _xstart + _xcount <= len(_se_vals):
                                        _lid_offset_ft = float(np.min(_se_vals[_xstart:_xstart + _xcount, 1]))
                                    break
                        except Exception:
                            _lid_offset_ft = 0.0

                    bridges.append({
                        "structure_id": i,
                        "type": stype,
                        "mode": mode,
                        "river": river,
                        "reach": reach,
                        "rs": rs,
                        "upstream_distance_ft": float(up_dist) if not math.isnan(up_dist) else None,
                        "upstream_distance_m": float(up_dist * LF) if not math.isnan(up_dist) else None,
                        "weir_width_ft": float(weir_width) if not math.isnan(weir_width) else None,
                        "weir_width_m": float(weir_width * LF) if not math.isnan(weir_width) else None,
                        "piers": piers_by_sid.get(i, []),
                        "coefficients": coef_by_sid.get(i, {}),
                        # Lid Profile (arch intrados) for arch bridge effective area calculation
                        "lid_stations_ft": _lid_stations_ft if _lid_stations_ft else None,
                        "lid_elevations_ft": _lid_elevations_ft if _lid_elevations_ft else None,
                        "lid_offset_ft": _lid_offset_ft if _lid_offset_ft != 0.0 or _lid_stations_ft else None,
                        "bridge_opening_width_ft": _bridge_opening_width_ft if _bridge_opening_width_ft > 0 else (
                            float(weir_width) if not math.isnan(weir_width) else None),
                        "bridge_opening_width_m": _bridge_opening_width_ft * LF if _bridge_opening_width_ft > 0 else (
                            float(weir_width * LF) if not math.isnan(weir_width) else None),
                    })
                except Exception:
                    continue
        except Exception:
            return bridges
        return bridges

    def _extract_junctions(self, hdf) -> list[dict]:
        out: List[dict] = []
        try:
            ds = self._hdf_get(hdf, "Geometry/Junctions/Attributes")
            if ds is None:
                return out
            arr = ds[...]
            for row in arr:
                try:
                    name = _get_field_s(row, "Name")
                    desc = _get_field_s(row, "Description")
                    momentum = bool(int(_get_field(row, "Momentum", 0)))
                    add_weight = bool(int(_get_field(row, "Add Weight", 0)))
                    add_friction = bool(int(_get_field(row, "Add Friction", 0)))
                    unsteady_energy = bool(int(_get_field(row, "Unsteady Energy", 0)))
                    out.append({
                        "name": name,
                        "description": desc,
                        "momentum": momentum,
                        "add_weight": add_weight,
                        "add_friction": add_friction,
                        "unsteady_energy": unsteady_energy
                    })
                except Exception:
                    continue
        except Exception:
            return out
        return out

    def _extract_reference_profiles(self, hdf) -> list[dict]:
        profiles_out: List[dict] = []
        try:
            # Try to locate the "Steady Profiles" group
            # Extract Profile Names
            prof_names_ds = None
            # We search for dataset named exactly "Profile Names"
            prof_names_ds = self._hdf_get(hdf,
                "Results/Steady/Output/Output Blocks/Base Output/Steady Profiles/Profile Names")
            profile_names: List[str] = []
            if prof_names_ds is not None:
                try:
                    raw = prof_names_ds[...]
                    for x in raw:
                        profile_names.append(_b2s(x) or "")
                except Exception:
                    profile_names = []

            # Water surface and Flow arrays: search for dataset named "Water Surface" and "Flow" under a group that contains "Cross Sections"
            ws_ds = None
            q_ds = None
            ws_path = None
            q_path = None
            for path, dset in self._iter_datasets(hdf):
                last = path.split("/")[-1].lower()
                if last == "water surface" and "/cross sections/" in path.lower():
                    ws_ds, ws_path = dset, path
                if last == "flow" and "/cross sections/" in path.lower():
                    q_ds, q_path = dset, path
            if ws_ds is None or q_ds is None:
                return profiles_out

            ws = ws_ds[...]
            q = q_ds[...]
            # ws, q shapes: (n_profiles, n_xs)
            n_profiles = int(ws.shape[0])
            n_xs = int(ws.shape[1]) if ws.ndim > 1 else int(ws.shape[0])

            # Cross Section identification order in Results HDF
            xs_attrs_results = None
            try:
                xs_attr_ds = hdf["Results"]["Steady"]["Output"]["Geometry Info"]["Cross Section Attributes"]
                xs_attrs_results = xs_attr_ds[...]
            except Exception:
                # fallback: search dataset named exactly "Cross Section Attributes" under a group named "Geometry Info"
                try:
                    for path, dset in self._iter_datasets(hdf):
                        if path.lower().endswith("/geometry info/cross section attributes"):
                            xs_attrs_results = dset[...]
                            break
                except Exception:
                    xs_attrs_results = None
            xs_keys: List[Dict[str, str]] = []
            if xs_attrs_results is not None:
                for row in xs_attrs_results:
                    try:
                        xs_keys.append({
                            "river": _get_field_s(row, "River"),
                            "reach": _get_field_s(row, "Reach"),
                            "station": _get_field_s(row, "Station"),
                            "name": _get_field_s(row, "Name")
                        })
                    except Exception:
                        xs_keys.append({"river": "", "reach": "", "station": "", "name": ""})
            else:
                # Without geometry info, provide index-based keys
                xs_keys = [{"river": "", "reach": "", "station": str(i), "name": ""} for i in range(n_xs)]

            for ip in range(n_profiles):
                try:
                    ws_row = ws[ip, :].tolist() if ws.ndim > 1 else [float(ws[ip])]
                    q_row = q[ip, :].tolist() if q.ndim > 1 else [float(q[ip])]
                    pname = profile_names[ip] if ip < len(profile_names) else f"Profile {ip+1}"
                    profiles_out.append({
                        "profile_index": ip,
                        "name": pname,
                        "water_surface_ft": [float(v) if not (v is None or np.isnan(v)) else None for v in ws_row],
                        "water_surface_m": [float(v * LF) if v is not None and not np.isnan(v) else None for v in ws_row],
                        "flow_cfs": [float(v) if not (v is None or np.isnan(v)) else None for v in q_row],
                        "flow_m3s": [float(v * CFS_TO_M3S) if v is not None and not np.isnan(v) else None for v in q_row],
                        "cross_sections": xs_keys
                    })
                except Exception:
                    continue
        except Exception:
            return profiles_out
        return profiles_out

    # ------------------------- Text parsers -------------------------

    def _read_text_file(self, path: Optional[Path]) -> str:
        if not path:
            return ""
        try:
            with open(path, "r", encoding="utf-8", errors="ignore") as f:
                return f.read()
        except Exception:
            return ""

    def _parse_flow_file(self) -> dict:
        info = {
            "title": None,
            "n_profiles": None,
            "profile_names": []
        }
        try:
            text = self._read_text_file(self.flow_file_path)
            if not text:
                return info
            mt = re.search(r"(?im)^\s*Flow\s+Title\s*=\s*(.+?)\s*$", text)
            if mt:
                info["title"] = mt.group(1).strip()
            mn = re.search(r"(?im)^\s*Number\s+of\s+Profiles\s*=\s*(\d+)\s*$", text)
            if mn:
                info["n_profiles"] = int(mn.group(1))
            mp = re.search(r"(?im)^\s*Profile\s+Names\s*=\s*(.+?)\s*$", text)
            if mp:
                names = [s.strip() for s in mp.group(1).split(",") if s.strip() != ""]
                info["profile_names"] = names
        except Exception:
            return info
        return info

    def _parse_upstream_flows(self) -> list[dict]:
        flows: List[dict] = []
        try:
            text = self._read_text_file(self.flow_file_path)
            if not text:
                return flows
            lines = text.splitlines()
            n_profiles = None
            m = re.search(r"(?im)^\s*Number\s+of\s+Profiles\s*=\s*(\d+)\s*$", text)
            if m:
                n_profiles = int(m.group(1))

            for i, line in enumerate(lines):
                if re.match(r"^\s*River\s+Rch\s*&\s*RM\s*=", line, flags=re.IGNORECASE):
                    try:
                        # Format: River Rch & RM=<River>,<Reach>,<RS>
                        after = line.split("=", 1)[1]
                        parts = [p.strip() for p in after.split(",")]
                        river = parts[0] if len(parts) > 0 else ""
                        reach = parts[1] if len(parts) > 1 else ""
                        rs = parts[2] if len(parts) > 2 else ""
                        # Next non-empty line should be N flows
                        j = i + 1
                        while j < len(lines) and lines[j].strip() == "":
                            j += 1
                        flow_line = lines[j] if j < len(lines) else ""
                        vals = _float_list_from_line(flow_line)
                        # Ensure match number of profiles if known
                        if n_profiles is not None and len(vals) != n_profiles:
                            # It might continue on next lines; try to collect until count reached
                            jj = j + 1
                            while n_profiles is not None and len(vals) < n_profiles and jj < len(lines):
                                vals.extend(_float_list_from_line(lines[jj]))
                                jj += 1
                            vals = vals[:n_profiles] if n_profiles is not None else vals
                        flows.append({
                            "river": river,
                            "reach": reach,
                            "rs": rs,
                            "flows_cfs": [float(v) for v in vals],
                            "flows_m3s": [float(v * CFS_TO_M3S) for v in vals]
                        })
                    except Exception:
                        continue
        except Exception:
            return flows
        return flows

    def _parse_boundary_conditions(self) -> list[dict]:
        bcs: List[dict] = []
        try:
            text = self._read_text_file(self.flow_file_path)
            if not text:
                return bcs
            lines = text.splitlines()
            i = 0
            while i < len(lines):
                line = lines[i]
                if re.match(r"^\s*Boundary\s+for\s+River\s+Rch\s*&\s*Prof#\s*=", line, flags=re.IGNORECASE):
                    try:
                        after = line.split("=", 1)[1]
                        # Boundary for River Rch & Prof#=<River>,<Reach>, <Prof#>
                        parts = [p.strip() for p in after.split(",")]
                        river = parts[0] if len(parts) > 0 else ""
                        reach = parts[1] if len(parts) > 1 else ""
                        prof_num = None
                        # parts[2] might include optional spaces
                        if len(parts) > 2:
                            try:
                                prof_num = int(re.findall(r"\d+", parts[2])[0])
                            except Exception:
                                prof_num = None

                        bc_entry = {
                            "river": river,
                            "reach": reach,
                            "profile_number": prof_num,
                            "up_type": None,
                            "dn_type": None,
                            "up_known_ws_ft": None,
                            "up_known_ws_m": None,
                            "up_slope": None,
                            "dn_known_ws_ft": None,  # can be missing for Type=0
                            "dn_known_ws_m": None,
                            "dn_slope": None,
                            "dn_rating_curve_pts": None,
                            "dn_rating_curve_values": []  # raw number list, semantics TBD
                        }

                        # Scan following lines until next 'Boundary for' or blank block end
                        j = i + 1
                        # Up Type / Dn Type and their associated optional lines
                        while j < len(lines) and not re.match(r"^\s*Boundary\s+for\s+River\s+Rch\s*&\s*Prof#", lines[j], flags=re.IGNORECASE):
                            l = lines[j].strip()
                            if l == "":
                                j += 1
                                continue
                            m_up = re.match(r"(?i)^Up\s+Type\s*=\s*(\d+)", l)
                            m_dn = re.match(r"(?i)^Dn\s+Type\s*=\s*(\d+)", l)
                            m_dnslope = re.match(r"(?i)^Dn\s+Slope\s*=\s*([-+]?\d*\.?\d+(?:[eE][-+]?\d+)?)", l)
                            m_dnws = re.match(r"(?i)^Dn\s+Known\s+WS\s*=\s*([-+]?\d*\.?\d+(?:[eE][-+]?\d+)?)", l)
                            m_upslope = re.match(r"(?i)^Up\s+Slope\s*=\s*([-+]?\d*\.?\d+(?:[eE][-+]?\d+)?)", l)
                            m_upws = re.match(r"(?i)^Up\s+Known\s+WS\s*=\s*([-+]?\d*\.?\d+(?:[eE][-+]?\d+)?)", l)
                            m_dnrc = re.match(r"(?i)^Dn\s+Rating\s+Curve\s+#\s*Pts\s*=\s*(\d+)", l)
                            m_uprc = re.match(r"(?i)^Up\s+Rating\s+Curve\s+#\s*Pts\s*=\s*(\d+)", l)

                            if m_up:
                                bc_entry["up_type"] = int(m_up.group(1))
                            elif m_dn:
                                bc_entry["dn_type"] = int(m_dn.group(1))
                            elif m_dnslope:
                                bc_entry["dn_slope"] = float(m_dnslope.group(1))
                            elif m_dnws:
                                v = float(m_dnws.group(1))
                                bc_entry["dn_known_ws_ft"] = v
                                bc_entry["dn_known_ws_m"] = v * LF
                            elif m_upslope:
                                bc_entry["up_slope"] = float(m_upslope.group(1))
                            elif m_upws:
                                v = float(m_upws.group(1))
                                bc_entry["up_known_ws_ft"] = v
                                bc_entry["up_known_ws_m"] = v * LF
                            elif m_dnrc:
                                npts = int(m_dnrc.group(1))
                                bc_entry["dn_rating_curve_pts"] = npts
                                vals: List[float] = []
                                k = j + 1
                                while k < len(lines) and len(vals) < npts:
                                    line_vals = _float_list_from_line(lines[k])
                                    if line_vals:
                                        vals.extend(line_vals)
                                    k += 1
                                bc_entry["dn_rating_curve_values"] = vals[:npts]
                                j = k - 1  # move index to last consumed
                            elif m_uprc:
                                # TODO: If upstream rating curve needed, parse similarly; keep as additional field
                                npts = int(m_uprc.group(1))
                                vals: List[float] = []
                                k = j + 1
                                while k < len(lines) and len(vals) < npts:
                                    line_vals = _float_list_from_line(lines[k])
                                    if line_vals:
                                        vals.extend(line_vals)
                                    k += 1
                                bc_entry["up_rating_curve_pts"] = npts
                                bc_entry["up_rating_curve_values"] = vals[:npts]
                                j = k - 1
                            j += 1

                            # Stop if next block begins
                            if j < len(lines) and re.match(r"^\s*Boundary\s+for\s+River\s+Rch\s*&\s*Prof#", lines[j], flags=re.IGNORECASE):
                                break

                        bcs.append(bc_entry)
                        i = j
                        continue
                    except Exception:
                        # If parsing error, skip to next
                        pass
                i += 1
        except Exception:
            return bcs
        return bcs

    def _parse_gate_openings(self) -> dict:
        """解析 .f01 文件中的 Gate Openings 数据。

        返回 {gate_name: [(opening_ft, n_open), ...]} 格式，每个 profile 一对数据。
        """
        out: Dict[str, Any] = {}
        try:
            text = self._read_text_file(self.flow_file_path)
            if not text:
                return out
            lines = text.splitlines()
            i = 0
            n_profiles = None
            m = re.search(r"(?im)^\s*Number\s+of\s+Profiles\s*=\s*(\d+)\s*$", text)
            if m:
                n_profiles = int(m.group(1))

            while i < len(lines):
                line = lines[i]
                if re.match(r"^\s*Gate\s+Openings\s*=", line, flags=re.IGNORECASE):
                    try:
                        after = line.split("=", 1)[1]
                        parts = [p.strip() for p in after.split(",")]
                        gate_name = parts[3] if len(parts) > 3 else ""
                        # 读取后续数字行，停止于下一个关键字行
                        j = i + 1
                        nums: List[float] = []
                        while j < len(lines):
                            next_line = lines[j]
                            # 遇到关键字行（字母开头且含 =）则停止
                            if re.match(r"^[A-Za-z]", next_line) and "=" in next_line:
                                break
                            line_nums = _float_list_from_line(next_line)
                            nums.extend(line_nums)
                            j += 1
                            if n_profiles is not None and len(nums) >= 2 * n_profiles:
                                break
                        # 截断到需要的数量
                        if n_profiles is not None:
                            nums = nums[:2 * n_profiles]
                        pairs: List[Tuple[int, int]] = []
                        k = 0
                        while k + 1 < len(nums):
                            pairs.append((int(nums[k]), int(nums[k + 1])))
                            k += 2
                        out[gate_name] = pairs
                        i = j - 1  # j 已指向下一个关键字行，回退一格
                    except Exception:
                        pass
                i += 1
        except Exception:
            return out
        return out

    def _parse_ice_cover(self) -> list[dict]:
        ices: List[dict] = []
        # Only parse if g02 text file exists (ice geometry)
        if not self.geometry_g02_path or not self.geometry_g02_path.exists():
            return ices
        try:
            text = self._read_text_file(self.geometry_g02_path)
            if not text:
                return ices
            lines = text.splitlines()

            # Regex for block header
            # Example: Type RM Length L Ch R = 1 ,42000   ,410,410,410
            hdr_re = re.compile(r"^Type\s+RM\s+Length\s+L\s+Ch\s+R\s*=\s*(\d+)\s*,\s*([-\d\.Ee+]+)\s*,\s*([-\d\.Ee+]*)\s*,\s*([-\d\.Ee+]*)\s*,\s*([-\d\.Ee+]*)", re.IGNORECASE)
            # Ice Thickness=,.5,
            thick_re = re.compile(r"^Ice\s+Thickness\s*=\s*,\s*([-\d\.Ee+]+)\s*,\s*$", re.IGNORECASE)
            mann_re = re.compile(r"^Ice\s+Mann\s*=\s*,\s*([-\d\.Ee+]+)\s*,\s*$", re.IGNORECASE)
            sg_re = re.compile(r"^Ice\s+Specific\s+Gravity\s*=\s*([-\d\.Ee+]+)\s*$", re.IGNORECASE)

            current = None
            for i, line in enumerate(lines):
                l = line.strip()
                mh = hdr_re.match(l)
                if mh:
                    # flush previous
                    if current:
                        ices.append(current)
                    # Start new block
                    try:
                        typ = int(mh.group(1))
                    except Exception:
                        typ = None
                    try:
                        rm_val = float(mh.group(2))
                    except Exception:
                        rm_val = None
                    current = {
                        "type": typ,
                        "rm": rm_val,  # river station
                        "length_ft": None,
                        "length_m": None,
                        "L_ft": None,
                        "Ch_ft": None,
                        "R_ft": None,
                        "thickness_ft": None,
                        "thickness_m": None,
                        "mannings_n": None,
                        "manning_n": None,  # 向后兼容别名（无s）
                        "specific_gravity": None
                    }
                    # Optional lengths
                    try:
                        length_ft = float(mh.group(3)) if mh.group(3) not in ("", None) else None
                    except Exception:
                        length_ft = None
                    try:
                        L_ft = float(mh.group(4)) if mh.group(4) not in ("", None) else None
                    except Exception:
                        L_ft = None
                    try:
                        R_ft = float(mh.group(5)) if mh.group(5) not in ("", None) else None
                    except Exception:
                        R_ft = None
                    current["length_ft"] = length_ft
                    current["length_m"] = length_ft * LF if length_ft is not None else None
                    current["L_ft"] = L_ft
                    current["L_m"] = L_ft * LF if L_ft is not None else None
                    current["R_ft"] = R_ft
                    current["R_m"] = R_ft * LF if R_ft is not None else None
                    continue

                if current is not None:
                    mt = thick_re.match(l)
                    if mt:
                        try:
                            t = float(mt.group(1))
                        except Exception:
                            t = None
                        current["thickness_ft"] = t
                        current["thickness_m"] = t * LF if t is not None else None
                        continue
                    mm = mann_re.match(l)
                    if mm:
                        try:
                            n = float(mm.group(1))
                        except Exception:
                            n = None
                        current["mannings_n"] = n
                        current["manning_n"] = n  # 向后兼容别名（无s）
                        continue
                    ms = sg_re.match(l)
                    if ms:
                        try:
                            sg = float(ms.group(1))
                        except Exception:
                            sg = None
                        current["specific_gravity"] = sg
                        continue

            if current:
                ices.append(current)
        except Exception:
            return ices
        return ices

    def _parse_lateral_weirs(self) -> list[dict]:
        # TODO: 没有明确格式说明，这里尝试从文本几何中基于关键字粗略提取；若失败返回空列表。
        weirs: List[dict] = []
        try:
            texts = []
            if self.geometry_g01_path and self.geometry_g01_path.exists():
                texts.append(self._read_text_file(self.geometry_g01_path))
            if self.geometry_g02_path and self.geometry_g02_path.exists():
                texts.append(self._read_text_file(self.geometry_g02_path))
            blob = "\n".join(texts)
            if not blob:
                return weirs

            # Heuristic: find blocks that start with "Lateral Weir" or "Lateral Structure"
            pattern = re.compile(r"(?is)(Lateral\s+(?:Weir|Structure)[^\n]*\n(?:.+?\n){0,50}?)\n(?=[A-Z][^\n]*=|\Z)")
            for m in pattern.finditer(blob):
                block = m.group(1)
                # Extract a few common fields, if present
                name = None
                mname = re.search(r"(?im)^\s*Name\s*=\s*(.+)$", block)
                if mname:
                    name = mname.group(1).strip()
                river = None
                reach = None
                rs = None
                mrrs = re.search(r"(?im)^\s*River\s*=\s*(.+?)\s*$", block)
                if mrrs:
                    river = mrrs.group(1).strip()
                mre = re.search(r"(?im)^\s*Reach\s*=\s*(.+?)\s*$", block)
                if mre:
                    reach = mre.group(1).strip()
                mrs = re.search(r"(?im)^\s*River\s+Station\s*=\s*(.+?)\s*$", block)
                if mrs:
                    rs = mrs.group(1).strip()
                crest_elev = None
                mce = re.search(r"(?im)^\s*Crest\s+Elev(?:ation)?\s*=\s*([-\d\.Ee+]+)", block)
                if mce:
                    try:
                        crest_elev = float(mce.group(1))
                    except Exception:
                        crest_elev = None
                length_ft = None
                ml = re.search(r"(?im)^\s*Weir\s+Length\s*=\s*([-\d\.Ee+]+)", block)
                if ml:
                    try:
                        length_ft = float(ml.group(1))
                    except Exception:
                        length_ft = None
                if name or crest_elev or length_ft:
                    weirs.append({
                        "name": name,
                        "river": river,
                        "reach": reach,
                        "rs": rs,
                        "crest_elev_ft": crest_elev,
                        "crest_elev_m": crest_elev * LF if crest_elev is not None else None,
                        "length_ft": length_ft,
                        "length_m": length_ft * LF if length_ft is not None else None
                    })
        except Exception:
            return []
        return weirs

    # ------------------------- Orchestrator -------------------------

    def extract_all(self) -> dict:
        data: Dict[str, Any] = {
            "schema_version": "2.0",
            "case_name": self.case_name,
            "files": {
                "project_prj": str(self.project_prj_path) if self.project_prj_path else None,
                "plan_file": str(self.plan_file_path) if self.plan_file_path else None,
                "geometry_hdf": str(self.geometry_hdf_path) if self.geometry_hdf_path else None,
                "results_hdf": str(self.results_hdf_path) if self.results_hdf_path else None,
                "flow_file": str(self.flow_file_path) if self.flow_file_path else None,
                "geometry_g01": str(self.geometry_g01_path) if self.geometry_g01_path else None,
                "geometry_g02": str(self.geometry_g02_path) if self.geometry_g02_path else None
            },
            "units": {
                "length": "ft",
                "flow": "cfs",
                "length_m": "m",
                "flow_m3s": "m3/s"
            }
        }

        # Geometry HDF content
        if self.geometry_hdf_path and Path(self.geometry_hdf_path).exists():
            try:
                with h5py.File(self.geometry_hdf_path, "r") as gh:
                    xs = self._extract_cross_sections(gh)
                    data["cross_sections"] = xs

                    # structures
                    culverts = self._extract_culverts(gh)
                    gates = self._extract_gate_groups(gh)
                    bridges = self._extract_bridges(gh)
                    junctions = self._extract_junctions(gh)

                    data["structures"] = {
                        "culverts": culverts,
                        "gate_groups": gates,
                        "bridges": bridges,
                        "junctions": junctions
                    }
            except Exception as e:
                data.setdefault("errors", []).append(f"Geometry HDF parse error: {e}")

        # Results reference profiles
        if self.results_hdf_path and Path(self.results_hdf_path).exists():
            try:
                with h5py.File(self.results_hdf_path, "r") as rh:
                    ref_profiles = self._extract_reference_profiles(rh)
                    data["reference_profiles"] = ref_profiles
            except Exception as e:
                data.setdefault("errors", []).append(f"Results HDF parse error: {e}")

        # Flow file parses
        flow_info = self._parse_flow_file()
        upstream_flows = self._parse_upstream_flows()
        boundary_conditions = self._parse_boundary_conditions()
        gate_openings = self._parse_gate_openings()

        data["flows"] = {
            "info": flow_info,
            "upstream_flows": upstream_flows,
            "boundary_conditions": boundary_conditions,
            "gate_openings": gate_openings
        }

        # Ice cover from g02
        ice_cover = self._parse_ice_cover()
        data["ice_cover"] = ice_cover

        # Lateral weirs (best-effort)
        lateral_weirs = self._parse_lateral_weirs()
        data["lateral_weirs"] = lateral_weirs

        # Add spec-required top-level aliases
        xs_list = data.get("cross_sections", [])
        ref_profiles = data.get("reference_profiles", [])
        data["n_cross_sections"] = len(xs_list)
        data["n_profiles"] = len(ref_profiles)
        data["boundary_conditions"] = data.get("flows", {}).get("boundary_conditions", [])
        data["flow_data"] = data.get("flows", {}).get("upstream_flows", [])
        data["profiles"] = ref_profiles
        data["gate_openings"] = data.get("flows", {}).get("gate_openings", {})
        data["geometry"] = {
            "cross_sections": xs_list,
            "culverts": data.get("structures", {}).get("culverts", []),
            "bridges": data.get("structures", {}).get("bridges", []),
            "inline_structures": data.get("structures", {}).get("gate_groups", []),
            "junctions": data.get("structures", {}).get("junctions", []),
        }
        # Embed ice cover into cross sections (per-XS alignment by order)
        ice_cover = data.get("ice_cover", [])
        for i, xs in enumerate(xs_list):
            if "ice_cover" not in xs:
                xs["ice_cover"] = ice_cover[i] if i < len(ice_cover) else None
        # Add spec-compatible field aliases for XS
        for xs in xs_list:
            if "len_channel_ft" not in xs:
                xs["len_channel_ft"] = xs.get("length_channel_ft")
            if "len_left_ft" not in xs:
                xs["len_left_ft"] = xs.get("length_left_ft")
            if "len_right_ft" not in xs:
                xs["len_right_ft"] = xs.get("length_right_ft")
            if "left_bank_ft" not in xs:
                xs["left_bank_ft"] = xs.get("left_bank_station_ft")
            if "right_bank_ft" not in xs:
                xs["right_bank_ft"] = xs.get("right_bank_station_ft")
            if "ineffective_areas" not in xs:
                xs["ineffective_areas"] = []
            # v1 兼容别名 — CLI 期望的短字段名
            if "station_elevation" not in xs:
                xs["station_elevation"] = xs.get("station_elevation_ft")
            if "manning_n" not in xs:
                xs["manning_n"] = xs.get("mannings_n")
            if "contraction" not in xs:
                xs["contraction"] = xs.get("contraction_coef")
            if "expansion" not in xs:
                xs["expansion"] = xs.get("expansion_coef")

        return data


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("project_dir", type=Path)
    parser.add_argument("--plan", default="p01")
    parser.add_argument("--output", type=Path, default=None)
    args = parser.parse_args()

    extractor = HECRASInputExtractor(args.project_dir, args.plan)
    data = extractor.extract_all()

    output = args.output or Path(f"{data.get('case_name', 'output')}.json")
    with open(output, 'w', encoding='utf-8') as f:
        json.dump(data, f, indent=2, ensure_ascii=False)
    print(f"Extracted to {output}")