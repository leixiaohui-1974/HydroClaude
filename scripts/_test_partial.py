"""from HEC-RAS unsteady HDF files extract reference data, save as SI-unit JSON.

Only for validation comparison, NOT as HydroClaude solver input.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict, List, Optional

import h5py
import numpy as np

SUITE_BASE = Path("C:/Users/lxh/AppData/Local/Temp/hydroclaude_hecras_suite")
OUTPUT_DIR = Path("Z:/research/hydroclaude/reports/hecras_unsteady_reference")

LF = 0.3048
CFS_TO_M3S = 0.028316846592
HR_TO_S = 3600.0

CASES = [
    ("055", "Example20_LateralWeir", "*.p07.hdf"),
    ("022", "JunctionHydraulics",    "*.p02.hdf"),
    ("030", "MultipleReaches",       "*.p01.hdf"),
    ("051", "Example17_Unsteady",    "*.p01.hdf"),
    ("016", "CulvertHydraulics",     "*.p01.hdf"),
    ("029", "MixedFlowRegime",       "*.p02.hdf"),
    ("018", "DamBreaching",          "*.p06.hdf"),
]
