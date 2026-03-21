"""HydroMind 原生数据格式 — 基于 HDF5 的水力模型数据标准。

参考 HEC-RAS HDF 结构设计，但更精简、更语义化、原生支持 SI 单位。
兼容读取 HEC-RAS HDF 和写出 HydroMind 格式。

HDF5 结构设计：

```
/HydroMind/
├── Metadata/
│   ├── version: "1.0"
│   ├── engine: "HydroClaude"
│   ├── created: ISO8601 timestamp
│   ├── units: "SI"  (始终 SI，读入时自动转换)
│   └── description: str
│
├── Geometry/
│   ├── Network/
│   │   ├── Rivers/           (Dataset: [{name, id}])
│   │   ├── Reaches/          (Dataset: [{id, river_id, us_junction, ds_junction}])
│   │   └── Junctions/        (Dataset: [{id, type, x, y, elevation}])
│   │
│   ├── CrossSections/
│   │   ├── Attributes        (Compound Dataset — 核心元数据表)
│   │   │   dtype: river, reach, station, name,
│   │   │          reach_length_m, left_bank_m, right_bank_m,
│   │   │          manning_n_lob, manning_n_channel, manning_n_rob,
│   │   │          contraction_coef, expansion_coef,
│   │   │          min_elevation_m, bed_elevation_m
│   │   │
│   │   ├── StationElevation/
│   │   │   ├── Info           (int32[n_xs, 2]: start_index, count)
│   │   │   └── Values         (float64[total_pts, 2]: station_m, elevation_m)
│   │   │
│   │   ├── ManningN/
│   │   │   ├── Info           (int32[n_xs, 2]: start_index, count)
│   │   │   └── Values         (float32[total_pts, 2]: station_m, manning_n)
│   │   │
│   │   └── BankStations       (float32[n_xs, 2]: left_bank, right_bank)
│   │
│   └── Structures/
│       ├── Bridges/           (Dataset: [{id, xs_us, xs_ds, type, span_m, ...}])
│       ├── Culverts/          (Dataset: [{id, xs_us, xs_ds, shape, diameter_m, ...}])
│       ├── InlineStructures/  (Dataset: [{id, xs_id, type, crest_elev_m, ...}])
│       └── LateralStructures/ (Dataset: [{id, xs_id, type, ...}])
│
├── BoundaryConditions/
│   ├── SteadyFlow/
│   │   ├── Profiles           (Dataset: [{name, total_flow_m3s}])
│   │   └── FlowChanges        (Dataset: [{reach_id, xs_station, flow_m3s}])
│   │
│   ├── UnsteadyFlow/
│   │   ├── Upstream/          (Dataset: [{reach_id, type, time_s[], value[]}])
│   │   ├── Downstream/        (Dataset: [{reach_id, type, time_s[], value[]}])
│   │   └── Lateral/           (Dataset: [{xs_id, type, time_s[], value[]}])
│   │
│   └── InitialConditions/
│       ├── WaterSurface_m     (float64[n_xs])
│       └── Flow_m3s           (float64[n_xs])
│
├── SolverConfig/
│   ├── solver_type: "standard_step" | "godunov" | "preissmann"
│   ├── mixed_flow: true | false
│   ├── gravity: 9.81
│   ├── convergence_tol: 0.0003  (m)
│   ├── max_iterations: 30
│   ├── friction_slope_method: "arithmetic" | "geometric" | "harmonic"
│   └── time_step_s: float  (for unsteady)
│
└── Results/
    ├── Steady/
    │   ├── Profiles/
    │   │   ├── Names           (str[n_profiles])
    │   │   └── CrossSections/
    │   │       ├── WaterSurface_m      (float64[n_profiles, n_xs])
    │   │       ├── EnergyGrade_m       (float64[n_profiles, n_xs])
    │   │       ├── Flow_m3s            (float64[n_profiles, n_xs])
    │   │       ├── Velocity_ms         (float64[n_profiles, n_xs])
    │   │       ├── Area_m2             (float64[n_profiles, n_xs])
    │   │       ├── TopWidth_m          (float64[n_profiles, n_xs])
    │   │       ├── WettedPerimeter_m   (float64[n_profiles, n_xs])
    │   │       ├── HydraulicRadius_m   (float64[n_profiles, n_xs])
    │   │       ├── FrictionSlope       (float64[n_profiles, n_xs])
    │   │       ├── FroudeNumber        (float64[n_profiles, n_xs])
    │   │       ├── Alpha               (float64[n_profiles, n_xs])
    │   │       ├── Conveyance          (float64[n_profiles, n_xs])
    │   │       └── ShearStress_Pa      (float64[n_profiles, n_xs])
    │   │
    │   └── ConvergenceLog/
    │       ├── Iterations      (int32[n_profiles, n_xs])
    │       └── Residual_m      (float64[n_profiles, n_xs])
    │
    ├── Unsteady/
    │   ├── TimeSteps_s         (float64[n_timesteps])
    │   └── CrossSections/
    │       ├── WaterSurface_m  (float64[n_timesteps, n_xs])
    │       ├── Flow_m3s        (float64[n_timesteps, n_xs])
    │       ├── Velocity_ms     (float64[n_timesteps, n_xs])
    │       └── FroudeNumber    (float64[n_timesteps, n_xs])
    │
    └── Comparison/              (HydroMind 独有 — HEC-RAS 没有)
        ├── Reference/
        │   ├── source: "HEC-RAS 6.6"
        │   ├── hdf_path: str
        │   └── WaterSurface_m  (float64[n_profiles, n_xs])
        │
        ├── Metrics/
        │   ├── WSE_MAE_m       (float64[n_profiles])
        │   ├── WSE_RMSE_m      (float64[n_profiles])
        │   ├── WSE_P95_m       (float64[n_profiles])
        │   ├── WSE_MaxError_m  (float64[n_profiles])
        │   ├── Flow_RelError   (float64[n_profiles])
        │   └── OverallPass     (bool[n_profiles])
        │
        └── TuningHistory/
            ├── Iterations      (int32)
            └── Log             (str — JSON)
```

设计原则：
1. **始终 SI 单位** — 不存英制，读 HEC-RAS 时自动转换
2. **扁平化结果数组** — [n_profiles, n_xs] 直接 numpy 切片
3. **完整逐断面元数据** — Attributes 表包含所有 HEC-RAS 有的字段
4. **内建对比** — Comparison 组是 HydroMind 独有，存参考软件结果和误差
5. **网络拓扑原生** — River/Reach/Junction 结构化存储
6. **向后兼容** — 可读 HEC-RAS HDF，可导出为 HEC-RAS 兼容格式
"""

from __future__ import annotations

import json
import logging
import time
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any

import h5py
import numpy as np

logger = logging.getLogger(__name__)

HYDROMIND_FORMAT_VERSION = "1.0"
HYDROMIND_ENGINE = "HydroClaude"


# ======================================================================
# Data Classes
# ======================================================================

@dataclass
class CrossSectionRecord:
    """Per-cross-section metadata (maps to Attributes compound dataset)."""
    river: str = ""
    reach: str = ""
    station: str = ""
    name: str = ""
    reach_length_m: float = 0.0
    left_bank_m: float = 0.0
    right_bank_m: float = 0.0
    manning_n_lob: float = 0.04
    manning_n_channel: float = 0.03
    manning_n_rob: float = 0.04
    contraction_coef: float = 0.1
    expansion_coef: float = 0.3
    min_elevation_m: float = 0.0
    bed_elevation_m: float = 0.0
    # Station-elevation profile (variable length per XS)
    sta_elev_stations: list[float] = field(default_factory=list)
    sta_elev_elevations: list[float] = field(default_factory=list)


@dataclass
class StructureRecord:
    """Hydraulic structure metadata."""
    structure_id: str = ""
    structure_type: str = ""  # bridge, culvert, inline_weir, lateral
    xs_upstream: str = ""
    xs_downstream: str = ""
    # Bridge-specific
    span_m: float = 0.0
    opening_height_m: float = 0.0
    pier_width_m: float = 0.0
    n_piers: int = 0
    # Culvert-specific
    shape: str = ""  # circular, rectangular, arch
    diameter_m: float = 0.0
    length_m: float = 0.0
    slope: float = 0.0
    inlet_type: str = "square_edge"


@dataclass
class BoundaryCondition:
    """Boundary condition specification."""
    location: str = ""  # reach_id or xs_station
    bc_type: str = ""  # known_wse, known_flow, normal_depth, rating_curve
    # Steady
    values: list[float] = field(default_factory=list)
    # Unsteady
    time_s: list[float] = field(default_factory=list)
    time_values: list[float] = field(default_factory=list)


@dataclass
class SolverConfig:
    """Solver configuration."""
    solver_type: str = "standard_step"
    mixed_flow: bool = False
    gravity: float = 9.81
    convergence_tol: float = 0.0003
    max_iterations: int = 30
    friction_slope_method: str = "arithmetic"
    time_step_s: float = 0.0


# ======================================================================
# Writer — HydroMind HDF5
# ======================================================================

class HydroMindWriter:
    """Write a HydroMind-format HDF5 file."""

    def __init__(self, path: str | Path):
        self.path = Path(path)
        self._xs_records: list[CrossSectionRecord] = []
        self._structures: list[StructureRecord] = []
        self._boundary_conditions: list[BoundaryCondition] = []
        self._solver_config = SolverConfig()
        self._results: dict[str, Any] = {}
        self._comparison: dict[str, Any] = {}
        self._metadata: dict[str, str] = {}

    def set_metadata(self, description: str = "", **kwargs: str) -> None:
        self._metadata["description"] = description
        self._metadata.update(kwargs)

    def add_cross_section(self, record: CrossSectionRecord) -> None:
        self._xs_records.append(record)

    def add_structure(self, record: StructureRecord) -> None:
        self._structures.append(record)

    def set_solver_config(self, config: SolverConfig) -> None:
        self._solver_config = config

    def set_steady_results(
        self,
        profile_names: list[str],
        water_surface_m: np.ndarray,
        energy_grade_m: np.ndarray | None = None,
        flow_m3s: np.ndarray | None = None,
        velocity_ms: np.ndarray | None = None,
        froude_number: np.ndarray | None = None,
        friction_slope: np.ndarray | None = None,
        alpha: np.ndarray | None = None,
        convergence_iterations: np.ndarray | None = None,
    ) -> None:
        self._results["steady"] = {
            "profile_names": profile_names,
            "water_surface_m": water_surface_m,
            "energy_grade_m": energy_grade_m,
            "flow_m3s": flow_m3s,
            "velocity_ms": velocity_ms,
            "froude_number": froude_number,
            "friction_slope": friction_slope,
            "alpha": alpha,
            "convergence_iterations": convergence_iterations,
        }

    def set_comparison(
        self,
        reference_source: str,
        reference_hdf_path: str,
        reference_wse: np.ndarray,
        wse_mae_m: np.ndarray,
        wse_rmse_m: np.ndarray,
        overall_pass: np.ndarray,
    ) -> None:
        self._comparison = {
            "source": reference_source,
            "hdf_path": reference_hdf_path,
            "reference_wse": reference_wse,
            "wse_mae_m": wse_mae_m,
            "wse_rmse_m": wse_rmse_m,
            "overall_pass": overall_pass,
        }

    def write(self) -> Path:
        """Write the HydroMind HDF5 file."""
        self.path.parent.mkdir(parents=True, exist_ok=True)
        with h5py.File(self.path, "w") as f:
            self._write_metadata(f)
            self._write_geometry(f)
            self._write_solver_config(f)
            self._write_results(f)
            if self._comparison:
                self._write_comparison(f)
        logger.info("HydroMind HDF written: %s", self.path)
        return self.path

    def _write_metadata(self, f: h5py.File) -> None:
        g = f.create_group("HydroMind/Metadata")
        g.attrs["version"] = HYDROMIND_FORMAT_VERSION
        g.attrs["engine"] = HYDROMIND_ENGINE
        g.attrs["created"] = time.strftime("%Y-%m-%dT%H:%M:%S")
        g.attrs["units"] = "SI"
        for key, val in self._metadata.items():
            g.attrs[key] = val

    def _write_geometry(self, f: h5py.File) -> None:
        geo = f.create_group("HydroMind/Geometry")

        if not self._xs_records:
            return

        n_xs = len(self._xs_records)

        # Attributes compound dataset
        dt = np.dtype([
            ("river", "S64"), ("reach", "S64"), ("station", "S32"), ("name", "S64"),
            ("reach_length_m", "f8"), ("left_bank_m", "f8"), ("right_bank_m", "f8"),
            ("manning_n_lob", "f4"), ("manning_n_channel", "f4"), ("manning_n_rob", "f4"),
            ("contraction_coef", "f4"), ("expansion_coef", "f4"),
            ("min_elevation_m", "f8"), ("bed_elevation_m", "f8"),
        ])
        attrs_data = np.zeros(n_xs, dtype=dt)
        for i, rec in enumerate(self._xs_records):
            attrs_data[i] = (
                rec.river.encode(), rec.reach.encode(), rec.station.encode(), rec.name.encode(),
                rec.reach_length_m, rec.left_bank_m, rec.right_bank_m,
                rec.manning_n_lob, rec.manning_n_channel, rec.manning_n_rob,
                rec.contraction_coef, rec.expansion_coef,
                rec.min_elevation_m, rec.bed_elevation_m,
            )
        xs_grp = geo.create_group("CrossSections")
        xs_grp.create_dataset("Attributes", data=attrs_data)

        # Station-Elevation profiles (variable length, packed)
        all_stations: list[float] = []
        all_elevations: list[float] = []
        info = np.zeros((n_xs, 2), dtype=np.int32)
        for i, rec in enumerate(self._xs_records):
            start = len(all_stations)
            count = len(rec.sta_elev_stations)
            info[i] = [start, count]
            all_stations.extend(rec.sta_elev_stations)
            all_elevations.extend(rec.sta_elev_elevations)

        se_grp = xs_grp.create_group("StationElevation")
        se_grp.create_dataset("Info", data=info)
        if all_stations:
            values = np.column_stack([all_stations, all_elevations])
            se_grp.create_dataset("Values", data=values.astype(np.float64))

        # Structures
        if self._structures:
            struct_grp = geo.create_group("Structures")
            struct_json = json.dumps([asdict(s) for s in self._structures], ensure_ascii=False)
            struct_grp.attrs["data_json"] = struct_json

    def _write_solver_config(self, f: h5py.File) -> None:
        g = f.create_group("HydroMind/SolverConfig")
        cfg = self._solver_config
        g.attrs["solver_type"] = cfg.solver_type
        g.attrs["mixed_flow"] = cfg.mixed_flow
        g.attrs["gravity"] = cfg.gravity
        g.attrs["convergence_tol"] = cfg.convergence_tol
        g.attrs["max_iterations"] = cfg.max_iterations
        g.attrs["friction_slope_method"] = cfg.friction_slope_method
        g.attrs["time_step_s"] = cfg.time_step_s

    def _write_results(self, f: h5py.File) -> None:
        if "steady" in self._results:
            data = self._results["steady"]
            g = f.create_group("HydroMind/Results/Steady/Profiles")
            names = data["profile_names"]
            g.create_dataset("Names", data=np.array([n.encode() for n in names]))
            xs_grp = g.create_group("CrossSections")
            for key, arr in data.items():
                if key == "profile_names":
                    continue
                if arr is not None and isinstance(arr, np.ndarray):
                    ds_name = key.replace("_", " ").title().replace(" ", "")
                    xs_grp.create_dataset(ds_name, data=arr.astype(np.float64))

    def _write_comparison(self, f: h5py.File) -> None:
        g = f.create_group("HydroMind/Results/Comparison")
        ref = g.create_group("Reference")
        ref.attrs["source"] = self._comparison["source"]
        ref.attrs["hdf_path"] = self._comparison["hdf_path"]
        ref.create_dataset("WaterSurface_m", data=self._comparison["reference_wse"])
        metrics = g.create_group("Metrics")
        metrics.create_dataset("WSE_MAE_m", data=self._comparison["wse_mae_m"])
        metrics.create_dataset("WSE_RMSE_m", data=self._comparison["wse_rmse_m"])
        metrics.create_dataset("OverallPass", data=self._comparison["overall_pass"])


# ======================================================================
# Reader — HydroMind HDF5 + HEC-RAS HDF5
# ======================================================================

class HydroMindReader:
    """Read HydroMind-format or HEC-RAS-format HDF5 files."""

    def __init__(self, path: str | Path):
        self.path = Path(path)
        if not self.path.exists():
            raise FileNotFoundError(f"HDF file not found: {self.path}")

    def detect_format(self) -> str:
        """Detect whether file is HydroMind or HEC-RAS format."""
        with h5py.File(self.path, "r") as f:
            if "HydroMind" in f:
                return "hydromind"
            if "Results" in f and ("Geometry" in f or "Plan Data" in f):
                return "hecras"
        return "unknown"

    def read_cross_sections(self) -> list[CrossSectionRecord]:
        """Read cross-section records from either format."""
        fmt = self.detect_format()
        if fmt == "hydromind":
            return self._read_xs_hydromind()
        elif fmt == "hecras":
            return self._read_xs_hecras()
        raise ValueError(f"Unknown HDF format: {fmt}")

    def read_steady_results(self) -> dict[str, Any]:
        """Read steady-state results from either format."""
        fmt = self.detect_format()
        if fmt == "hydromind":
            return self._read_results_hydromind()
        elif fmt == "hecras":
            return self._read_results_hecras()
        raise ValueError(f"Unknown HDF format: {fmt}")

    # --- HydroMind format ---

    def _read_xs_hydromind(self) -> list[CrossSectionRecord]:
        records: list[CrossSectionRecord] = []
        with h5py.File(self.path, "r") as f:
            attrs = f["HydroMind/Geometry/CrossSections/Attributes"][:]
            se_info = f["HydroMind/Geometry/CrossSections/StationElevation/Info"][:]
            se_vals = f["HydroMind/Geometry/CrossSections/StationElevation/Values"][:] if "HydroMind/Geometry/CrossSections/StationElevation/Values" in f else np.empty((0, 2))

            for i, row in enumerate(attrs):
                start, count = int(se_info[i, 0]), int(se_info[i, 1])
                sta = se_vals[start:start + count, 0].tolist() if count > 0 else []
                elev = se_vals[start:start + count, 1].tolist() if count > 0 else []

                records.append(CrossSectionRecord(
                    river=row["river"].decode().strip(),
                    reach=row["reach"].decode().strip(),
                    station=row["station"].decode().strip(),
                    name=row["name"].decode().strip(),
                    reach_length_m=float(row["reach_length_m"]),
                    left_bank_m=float(row["left_bank_m"]),
                    right_bank_m=float(row["right_bank_m"]),
                    manning_n_lob=float(row["manning_n_lob"]),
                    manning_n_channel=float(row["manning_n_channel"]),
                    manning_n_rob=float(row["manning_n_rob"]),
                    contraction_coef=float(row["contraction_coef"]),
                    expansion_coef=float(row["expansion_coef"]),
                    min_elevation_m=float(row["min_elevation_m"]),
                    bed_elevation_m=float(row["bed_elevation_m"]),
                    sta_elev_stations=sta,
                    sta_elev_elevations=elev,
                ))
        return records

    def _read_results_hydromind(self) -> dict[str, Any]:
        with h5py.File(self.path, "r") as f:
            base = "HydroMind/Results/Steady/Profiles"
            if base not in f:
                return {}
            names = [n.decode() for n in f[f"{base}/Names"][:]]
            xs = f[f"{base}/CrossSections"]
            result: dict[str, Any] = {"profile_names": names}
            for key in xs:
                result[key] = xs[key][:]
            return result

    # --- HEC-RAS format ---

    def _read_xs_hecras(self) -> list[CrossSectionRecord]:
        """Read HEC-RAS cross-sections and convert to HydroMind format."""
        from integration.hec_ras_adapter import (
            FT_TO_M, CFS_TO_M3S,
            _detect_unit_system, _length_factor,
        )
        records: list[CrossSectionRecord] = []
        prj_path = self.path.parent / (self.path.stem.split(".")[0] + ".prj")
        unit_system = _detect_unit_system(prj_path if prj_path.exists() else None)
        lf = _length_factor(unit_system)

        with h5py.File(self.path, "r") as f:
            geo_attrs_path = "Geometry/Cross Sections/Attributes"
            if geo_attrs_path not in f:
                return records

            geo_attrs = f[geo_attrs_path][:]
            se_info = f["Geometry/Cross Sections/Station Elevation Info"][:] if "Geometry/Cross Sections/Station Elevation Info" in f else np.empty((0, 2), dtype=np.int32)
            se_vals = f["Geometry/Cross Sections/Station Elevation Values"][:] if "Geometry/Cross Sections/Station Elevation Values" in f else np.empty((0, 2))
            mn_info = f["Geometry/Cross Sections/Manning's n Info"][:] if "Geometry/Cross Sections/Manning's n Info" in f else np.empty((0, 2), dtype=np.int32)
            mn_vals = f["Geometry/Cross Sections/Manning's n Values"][:] if "Geometry/Cross Sections/Manning's n Values" in f else np.empty((0, 2))

            for i, row in enumerate(geo_attrs):
                river = row["River"].decode().strip() if isinstance(row["River"], bytes) else str(row["River"]).strip()
                reach = row["Reach"].decode().strip() if isinstance(row["Reach"], bytes) else str(row["Reach"]).strip()
                rs = row["RS"].decode().strip() if isinstance(row["RS"], bytes) else str(row["RS"]).strip()

                # Station-elevation profile
                sta, elev = [], []
                if i < len(se_info):
                    start, count = int(se_info[i, 0]), int(se_info[i, 1])
                    if count > 0 and start + count <= len(se_vals):
                        sta = (se_vals[start:start + count, 0] * lf).tolist()
                        elev = (se_vals[start:start + count, 1] * lf).tolist()

                # Manning n (LOB/Channel/ROB)
                n_lob, n_ch, n_rob = 0.04, 0.03, 0.04
                if i < len(mn_info):
                    mn_start, mn_count = int(mn_info[i, 0]), int(mn_info[i, 1])
                    if mn_count >= 3 and mn_start + mn_count <= len(mn_vals):
                        # First = LOB, middle = Channel, last = ROB
                        n_lob = float(mn_vals[mn_start, 1])
                        n_ch = float(mn_vals[mn_start + mn_count // 2, 1])
                        n_rob = float(mn_vals[mn_start + mn_count - 1, 1])
                    elif mn_count == 1 and mn_start < len(mn_vals):
                        n_lob = n_ch = n_rob = float(mn_vals[mn_start, 1])

                rec = CrossSectionRecord(
                    river=river,
                    reach=reach,
                    station=rs,
                    reach_length_m=float(row["Len Channel"]) * lf if "Len Channel" in row.dtype.names else 0.0,
                    left_bank_m=float(row["Left Bank"]) * lf if "Left Bank" in row.dtype.names else 0.0,
                    right_bank_m=float(row["Right Bank"]) * lf if "Right Bank" in row.dtype.names else 0.0,
                    manning_n_lob=n_lob,
                    manning_n_channel=n_ch,
                    manning_n_rob=n_rob,
                    contraction_coef=float(row["Contr"]) if "Contr" in row.dtype.names else 0.1,
                    expansion_coef=float(row["Expan"]) if "Expan" in row.dtype.names else 0.3,
                    min_elevation_m=min(elev) if elev else 0.0,
                    bed_elevation_m=min(elev) if elev else 0.0,
                    sta_elev_stations=sta,
                    sta_elev_elevations=elev,
                )
                records.append(rec)
        return records

    def _read_results_hecras(self) -> dict[str, Any]:
        """Read HEC-RAS steady results and convert to HydroMind format."""
        from integration.hec_ras_adapter import _detect_unit_system, _length_factor, _flow_factor
        prj_path = self.path.parent / (self.path.stem.split(".")[0] + ".prj")
        unit_system = _detect_unit_system(prj_path if prj_path.exists() else None)
        lf = _length_factor(unit_system)
        qf = _flow_factor(unit_system)

        with h5py.File(self.path, "r") as f:
            base = "Results/Steady/Output/Output Blocks/Base Output/Steady Profiles/Cross Sections"
            if f"{base}/Water Surface" not in f:
                return {}

            ws = np.asarray(f[f"{base}/Water Surface"][:], dtype=float) * lf
            flow = np.asarray(f[f"{base}/Flow"][:], dtype=float) * qf
            eg = np.asarray(f[f"{base}/Energy Grade"][:], dtype=float) * lf if f"{base}/Energy Grade" in f else None

            names_raw = f["Results/Steady/Output/Output Blocks/Base Output/Steady Profiles/Profile Names"][:]
            names = [n.decode().strip() if isinstance(n, bytes) else str(n) for n in names_raw]

            result = {
                "profile_names": names,
                "WaterSurfaceM": ws,
                "FlowM3S": flow,
            }
            if eg is not None:
                result["EnergyGradeM"] = eg

            # Read additional variables if available
            addl_base = f"{base}/Additional Variables"
            for var_name in ["Alpha", "Friction Slope", "Velocity Channel",
                             "Area Flow Total", "Top Width Total",
                             "Wetted Perimeter Total", "Hydraulic Radius Total",
                             "Conveyance Total", "Shear"]:
                path = f"{addl_base}/{var_name}"
                if path in f:
                    key = var_name.replace(" ", "")
                    data = np.asarray(f[path][:], dtype=float)
                    if var_name in ("Area Flow Total", "Top Width Total",
                                    "Wetted Perimeter Total", "Hydraulic Radius Total"):
                        data *= lf  # length-dimension variables
                    result[key] = data

            return result


# ======================================================================
# Converter — HEC-RAS → HydroMind
# ======================================================================

def convert_hecras_to_hydromind(
    hecras_hdf_path: str | Path,
    output_path: str | Path | None = None,
    description: str = "",
) -> Path:
    """Convert a HEC-RAS plan HDF to HydroMind format.

    Args:
        hecras_hdf_path: Path to HEC-RAS .p*.hdf file.
        output_path: Output path for HydroMind .hm.hdf file.
            If None, places it next to the input with .hm.hdf suffix.
        description: Optional description for metadata.

    Returns:
        Path to the created HydroMind HDF5 file.
    """
    src = Path(hecras_hdf_path)
    if output_path is None:
        output_path = src.with_suffix(".hm.hdf")

    reader = HydroMindReader(src)
    xs_records = reader.read_cross_sections()
    results = reader.read_steady_results()

    writer = HydroMindWriter(output_path)
    writer.set_metadata(
        description=description or f"Converted from {src.name}",
        source_format="HEC-RAS",
        source_file=str(src),
    )

    for rec in xs_records:
        writer.add_cross_section(rec)

    if results:
        profile_names = results.pop("profile_names", [])
        ws = results.pop("WaterSurfaceM", None)
        eg = results.pop("EnergyGradeM", None)
        flow = results.pop("FlowM3S", None)
        alpha = results.pop("Alpha", None)
        sf = results.pop("FrictionSlope", None)
        vel = results.pop("VelocityChannel", None)

        if ws is not None:
            writer.set_steady_results(
                profile_names=profile_names,
                water_surface_m=ws,
                energy_grade_m=eg,
                flow_m3s=flow,
                velocity_ms=vel,
                friction_slope=sf,
                alpha=alpha,
            )

    return writer.write()
