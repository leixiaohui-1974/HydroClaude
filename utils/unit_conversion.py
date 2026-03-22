"""统一单位转换模块。

HydroClaude 内部全部使用国际标准单位 (SI)。
HEC-RAS 数据为美制 (US Customary)。此模块提供双向转换。
"""

from dataclasses import dataclass


# ============================================================
# 基础换算常数
# ============================================================

FT_TO_M = 0.3048          # 1 ft = 0.3048 m
M_TO_FT = 1.0 / FT_TO_M  # 1 m = 3.28084 ft

CFS_TO_M3S = 0.0283168    # 1 cfs = 0.0283168 m³/s
M3S_TO_CFS = 1.0 / CFS_TO_M3S

FT2_TO_M2 = FT_TO_M ** 2  # 1 ft² = 0.09290 m²
M2_TO_FT2 = 1.0 / FT2_TO_M2

FT3_TO_M3 = FT_TO_M ** 3  # 1 ft³ = 0.02832 m³
M3_TO_FT3 = 1.0 / FT3_TO_M3

# Manning K 换算: K_SI = K_US × FT_TO_M^(8/3) / 1.486
MANNING_K_US_TO_SI = FT_TO_M ** (8.0 / 3.0) / 1.486
MANNING_K_SI_TO_US = 1.0 / MANNING_K_US_TO_SI

# Manning 公式系数: SI 用 1/n, US 用 1.486/n
MANNING_COEF_SI = 1.0
MANNING_COEF_US = 1.486

# 堰流系数换算: C_SI = C_US × ft^0.5
WEIR_COEF_US_TO_SI = FT_TO_M ** 0.5  # ≈ 0.5523


# ============================================================
# 长度转换
# ============================================================

def ft_to_m(ft: float) -> float:
    """英尺 → 米"""
    return ft * FT_TO_M


def m_to_ft(m: float) -> float:
    """米 → 英尺"""
    return m * M_TO_FT


# ============================================================
# 面积转换
# ============================================================

def ft2_to_m2(ft2: float) -> float:
    """平方英尺 → 平方米"""
    return ft2 * FT2_TO_M2


def m2_to_ft2(m2: float) -> float:
    """平方米 → 平方英尺"""
    return m2 * M2_TO_FT2


# ============================================================
# 流量转换
# ============================================================

def cfs_to_m3s(cfs: float) -> float:
    """立方英尺/秒 → 立方米/秒"""
    return cfs * CFS_TO_M3S


def m3s_to_cfs(m3s: float) -> float:
    """立方米/秒 → 立方英尺/秒"""
    return m3s * M3S_TO_CFS


# ============================================================
# Manning 输水能力 K 转换
# ============================================================

def k_us_to_si(k_us: float) -> float:
    """Manning K (US Customary) → SI"""
    return k_us * MANNING_K_US_TO_SI


def k_si_to_us(k_si: float) -> float:
    """Manning K (SI) → US Customary"""
    return k_si * MANNING_K_SI_TO_US


# ============================================================
# 堰流系数转换
# ============================================================

def weir_coef_us_to_si(c_us: float) -> float:
    """堰流系数 (US, ft^0.5 单位) → SI (m^0.5 单位)"""
    return c_us * WEIR_COEF_US_TO_SI


def weir_coef_si_to_us(c_si: float) -> float:
    """堰流系数 (SI) → US"""
    return c_si / WEIR_COEF_US_TO_SI


# ============================================================
# 批量断面转换
# ============================================================

@dataclass
class CrossSectionUS:
    """美制断面数据"""
    stations_ft: list[float]
    elevations_ft: list[float]
    left_bank_ft: float
    right_bank_ft: float
    len_channel_ft: float
    len_left_ft: float
    len_right_ft: float


@dataclass
class CrossSectionSI:
    """国际标准单位断面数据"""
    stations_m: list[float]
    elevations_m: list[float]
    left_bank_m: float
    right_bank_m: float
    len_channel_m: float
    len_left_m: float
    len_right_m: float


def convert_xs_us_to_si(xs: CrossSectionUS) -> CrossSectionSI:
    """将美制断面数据转换为 SI"""
    return CrossSectionSI(
        stations_m=[s * FT_TO_M for s in xs.stations_ft],
        elevations_m=[e * FT_TO_M for e in xs.elevations_ft],
        left_bank_m=xs.left_bank_ft * FT_TO_M,
        right_bank_m=xs.right_bank_ft * FT_TO_M,
        len_channel_m=xs.len_channel_ft * FT_TO_M,
        len_left_m=xs.len_left_ft * FT_TO_M,
        len_right_m=xs.len_right_ft * FT_TO_M,
    )


# ============================================================
# 检测单位系统
# ============================================================

def detect_unit_system(unit_str: str) -> str:
    """从 HEC-RAS 单位字符串检测单位系统。

    Returns:
        "SI" 或 "US"
    """
    s = unit_str.lower()
    if "metric" in s or "si" in s:
        return "SI"
    if "us" in s or "english" in s or "customary" in s:
        return "US"
    return "US"  # HEC-RAS 默认美制


def length_factor(unit_system: str) -> float:
    """返回长度换算系数: 输入单位 → m"""
    return FT_TO_M if unit_system == "US" else 1.0


def flow_factor(unit_system: str) -> float:
    """返回流量换算系数: 输入单位 → m³/s"""
    return CFS_TO_M3S if unit_system == "US" else 1.0
