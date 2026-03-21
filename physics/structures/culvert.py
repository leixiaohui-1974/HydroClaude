"""
Culvert Hydraulic Model

This module implements culvert hydraulics based on FHWA HDS 5
(Hydraulic Design of Highway Culverts, 3rd Edition, 2012).

Supports:
- Circular, rectangular, and arch cross-sections
- Inlet control (unsubmerged and submerged)
- Outlet control (energy equation method)
- Various inlet types with corresponding discharge coefficients
"""

from dataclasses import dataclass
from typing import Literal, Tuple, Optional

import numpy as np


# ============================================================================
# HDS-5 系数数据结构
# ============================================================================

@dataclass(frozen=True)
class InletCoefficients:
    """HDS-5 入口控制系数（无量纲）

    对应 HDS-5 Table 5-1 中的 K/M/c/Y 系数族。
    入口控制方程（SI 单位，无量纲参数 Q* = Q/(A*D^0.5)）：
      Form 1（未淹没）: HW/D = K * Q*^M + slope_term
      Form 2（淹没）  : HW/D = c * Q*^2 + Y + slope_term
    slope_term = -0.5*S（HDS-5 默认修正，可被 slope_coef 附加）
    """
    K: float             # 未淹没入口控制系数
    M: float             # 未淹没入口控制指数
    c: float             # 淹没入口控制系数
    Y: float             # 淹没入口控制截距
    slope_coef: float = 0.0          # 坡度修正附加系数（通常为 0）
    default_ke: float | None = None  # 建议入口损失系数 Ke


@dataclass(frozen=True)
class MaterialProperties:
    """管材物理属性"""
    default_n: float    # 默认 Manning 糙率
    inlet_family: str   # 入口系数族标识，用于索引 INLET_COEFF_TABLE


# ============================================================================
# 管材系数库
# ============================================================================

BARREL_MATERIALS: dict[str, MaterialProperties] = {
    # 混凝土圆管 / 箱涵
    "concrete": MaterialProperties(default_n=0.012, inlet_family="concrete"),
    # 波纹金属管（Corrugated Metal Pipe）
    "corrugated_metal": MaterialProperties(default_n=0.024, inlet_family="cmp"),
    # 光滑钢管
    "smooth_steel": MaterialProperties(default_n=0.012, inlet_family="smooth_pipe"),
    # 光滑塑料管（HDPE 等）
    "plastic_smooth": MaterialProperties(default_n=0.011, inlet_family="smooth_pipe"),
    # 混凝土箱涵（矩形专用族）
    "concrete_box": MaterialProperties(default_n=0.012, inlet_family="concrete_box"),
}


# ============================================================================
# HDS-5 入口控制系数表（Table 5-1，SI 单位）
# key = (断面形状, inlet_family, 入口类型)
# ============================================================================

INLET_COEFF_TABLE: dict[tuple[str, str, str], InletCoefficients] = {
    # ── 混凝土圆管（HDS-5 Table 5-1）────────────────────────────────────────
    ("circular", "concrete", "projecting"):
        InletCoefficients(K=0.0098, M=2.0, c=0.0398, Y=0.67),
    ("circular", "concrete", "headwall_square_edge"):
        InletCoefficients(K=0.0078, M=2.0, c=0.0292, Y=0.74),
    ("circular", "concrete", "headwall_groove_end"):
        InletCoefficients(K=0.0018, M=2.5, c=0.0243, Y=0.83),
    ("circular", "concrete", "mitered_to_slope"):
        InletCoefficients(K=0.0045, M=2.0, c=0.0317, Y=0.69),
    ("circular", "concrete", "beveled_ring"):
        InletCoefficients(K=0.0018, M=2.5, c=0.0243, Y=0.83),

    # 混凝土圆管旧键兼容（保留历史入口命名）
    ("circular", "concrete", "groove_end_projecting"):
        InletCoefficients(K=0.0045, M=2.0, c=0.0317, Y=0.69),
    ("circular", "concrete", "groove_end_headwall"):
        InletCoefficients(K=0.0018, M=2.5, c=0.0243, Y=0.83),

    # ── 波纹金属管 CMP（HDS-5 Table 5-1）────────────────────────────────────
    ("circular", "cmp", "projecting"):
        InletCoefficients(K=0.0078, M=2.0, c=0.0379, Y=0.69),
    ("circular", "cmp", "mitered"):
        InletCoefficients(K=0.0210, M=1.33, c=0.0463, Y=0.75),
    ("circular", "cmp", "headwall"):
        InletCoefficients(K=0.0078, M=2.0, c=0.0340, Y=0.74),

    # CMP 旧键兼容
    ("circular", "cmp", "mitered_to_slope"):
        InletCoefficients(K=0.0210, M=1.33, c=0.0463, Y=0.75),

    # ── 混凝土箱涵（HDS-5 Table 5-1）────────────────────────────────────────
    ("rectangular", "concrete_box", "headwall_thin_wall"):
        InletCoefficients(K=0.0083, M=2.0, c=0.0379, Y=0.69),
    ("rectangular", "concrete_box", "headwall_thick_wall"):
        InletCoefficients(K=0.0040, M=2.0, c=0.0179, Y=0.97),
    ("rectangular", "concrete_box", "wingwall_30deg"):
        InletCoefficients(K=0.0145, M=1.75, c=0.0419, Y=0.64),
    ("rectangular", "concrete_box", "wingwall_45deg"):
        InletCoefficients(K=0.0145, M=1.75, c=0.0419, Y=0.64),
    ("rectangular", "concrete_box", "wingwall_90deg"):
        InletCoefficients(K=0.0083, M=2.0, c=0.0379, Y=0.69),

    # 箱涵旧键兼容
    ("rectangular", "concrete_box", "headwall_square_edge"):
        InletCoefficients(K=0.0083, M=2.0, c=0.0379, Y=0.69),
    ("rectangular", "concrete_box", "wingwall_30_75"):
        InletCoefficients(K=0.0145, M=1.75, c=0.0419, Y=0.64),
    ("rectangular", "concrete_box", "wingwall_0_15"):
        InletCoefficients(K=0.0145, M=1.75, c=0.0419, Y=0.64),
    ("rectangular", "concrete_box", "parallel_headwall_bevel"):
        InletCoefficients(K=0.0040, M=2.0, c=0.0179, Y=0.97),

    # ── 塑料管（光滑内壁，HDS-5 Table 5-1 对应 smooth pipe 族）───────────────
    ("circular", "smooth_pipe", "projecting"):
        InletCoefficients(K=0.0098, M=2.0, c=0.0398, Y=0.67),
    ("circular", "smooth_pipe", "headwall"):
        InletCoefficients(K=0.0078, M=2.0, c=0.0292, Y=0.74),
}


# ============================================================================
# 入口类型别名映射（将常用俗称统一映射到系数表键名）
# ============================================================================

INLET_TYPE_ALIASES: dict[str, str] = {
    # ── 通用入口类型 ───────────────────────────────────────────────────────────
    "projecting": "projecting",                     # 突出式
    "headwall": "headwall",                         # 端墙（通用）

    # ── 混凝土圆管系列 ─────────────────────────────────────────────────────────
    "square_edge": "headwall_square_edge",          # 方口端墙
    "headwall_square": "headwall_square_edge",      # 方口端墙（别名）
    "headwall_square_edge": "headwall_square_edge", # 方口端墙（规范名）
    "groove_end": "headwall_groove_end",            # 头墙槽口（旧习惯名）
    "groove_headwall": "headwall_groove_end",       # 头墙槽口（旧习惯名）
    "headwall_groove": "headwall_groove_end",       # 头墙槽口（简写）
    "headwall_groove_end": "headwall_groove_end",   # 头墙槽口（规范名）
    "mitered": "mitered_to_slope",                  # 斜切与坡面齐平
    "mitered_to_slope": "mitered_to_slope",         # 斜切与坡面齐平（规范名）
    "beveled": "beveled_ring",                      # 倒角环口
    "beveled_ring": "beveled_ring",                 # 倒角环口（规范名）

    # ── 箱涵系列 ───────────────────────────────────────────────────────────────
    "thin_wall": "headwall_thin_wall",              # 薄壁端墙
    "thick_wall": "headwall_thick_wall",            # 厚壁端墙
    "wingwall": "wingwall_45deg",                   # 翼墙默认映射到 45°
    "wingwall_30": "wingwall_30deg",                # 翼墙 30°
    "wingwall_30deg": "wingwall_30deg",             # 翼墙 30°（规范名）
    "wingwall_45": "wingwall_45deg",                # 翼墙 45°
    "wingwall_45deg": "wingwall_45deg",             # 翼墙 45°（规范名）
    "wingwall_90": "wingwall_90deg",                # 翼墙 90°
    "wingwall_90deg": "wingwall_90deg",             # 翼墙 90°（规范名）
    "parallel_bevel": "headwall_thick_wall",        # 平行端墙倒角（旧名兼容）
}


# ============================================================================
# 几何数据结构
# ============================================================================

@dataclass
class CulvertGeometry:
    """
    Culvert geometry parameters

    Attributes
    ----------
    shape : str
        Cross-section shape: 'circular', 'rectangular', or 'arch'
    diameter : float, optional
        Diameter for circular culverts (m)
    width : float, optional
        Width for rectangular/arch culverts (m)
    height : float, optional
        Height for rectangular/arch culverts (m)
    length : float
        Culvert length (m)
    slope : float
        Culvert slope (dimensionless, default 0.001)
    invert_elevation : float
        进口底板高程（向后兼容字段，等同于 invert_elevation_us）
    invert_elevation_us : float
        上游进口底板高程 (m)
    invert_elevation_ds : float | None
        下游出口底板高程 (m)；None 时由 slope 推算
    n_barrels : int
        并联孔数（默认 1）
    """
    shape: Literal["circular", "rectangular", "arch"]
    length: float
    diameter: float | None = None
    width: float | None = None
    height: float | None = None
    slope: float = 0.001
    invert_elevation: float = 0.0        # 向后兼容旧字段
    invert_elevation_us: float = 0.0     # 新字段：上游底板高程
    invert_elevation_ds: float | None = None  # 新字段：下游底板高程
    n_barrels: int = 1                   # 新字段：并联孔数

    def __post_init__(self) -> None:
        """校验几何参数并处理历史字段向后兼容"""
        # 兼容旧字段：若新字段为默认 0.0 而旧字段非零，则用旧字段值初始化新字段
        if self.invert_elevation_us == 0.0 and self.invert_elevation != 0.0:
            self.invert_elevation_us = self.invert_elevation

        # 统一别名：保证旧代码通过 self.invert_elevation 读到的是上游底板高程
        self.invert_elevation = self.invert_elevation_us

        # 若未提供下游底板高程，则按纵坡推算
        if self.invert_elevation_ds is None:
            self.invert_elevation_ds = self.invert_elevation_us - self.slope * self.length

        # 校验多孔涵孔数
        if self.n_barrels <= 0:
            raise ValueError("n_barrels must be a positive integer")

        # 校验断面几何参数
        if self.shape == "circular":
            if self.diameter is None or self.diameter <= 0:
                raise ValueError("Circular culvert requires positive diameter")
        elif self.shape in ["rectangular", "arch"]:
            if self.width is None or self.width <= 0:
                raise ValueError(f"{self.shape} culvert requires positive width")
            if self.height is None or self.height <= 0:
                raise ValueError(f"{self.shape} culvert requires positive height")

        if self.length <= 0:
            raise ValueError("Culvert length must be positive")

    # ── 特征尺寸 ─────────────────────────────────────────────────────────────

    def rise(self) -> float:
        """返回特征高度：圆管为直径，矩形 / 拱形为高度"""
        if self.shape == "circular":
            return float(self.diameter)
        return float(self.height)

    # ── 满流面积 ─────────────────────────────────────────────────────────────

    def full_area(self) -> float:
        """返回满流断面面积（m^2）"""
        if self.shape == "circular":
            return float(np.pi * (self.diameter / 2) ** 2)
        if self.shape == "rectangular":
            return float(self.width * self.height)
        # 拱形：下部半圆 + 上部矩形（r = width/2）
        r = self.width / 2
        rect_h = max(self.height - r, 0.0)
        return float((np.pi / 2) * r ** 2 + self.width * rect_h)

    # ── 按水深计算几何量 ──────────────────────────────────────────────────────

    def area_at_depth(self, y: float) -> float:
        """按水深精确计算过水面积（m^2）

        Args:
            y: 水深，从底板算起 (m)

        Returns:
            过水面积 (m^2)
        """
        if y <= 0.0:
            return 0.0

        if self.shape == "circular":
            d = self.diameter
            if y >= d:
                return self.full_area()
            # 圆弓面积公式：theta = 2*arccos(1 - 2y/D)，A = D^2/8*(theta - sin(theta))
            theta = 2.0 * np.arccos(1.0 - 2.0 * y / d)
            return float((d ** 2 / 8.0) * (theta - np.sin(theta)))

        if self.shape == "rectangular":
            y_eff = min(max(y, 0.0), self.height)
            return float(self.width * y_eff)

        # 拱形：下部半圆段（y <= r）用圆弓面积；上部矩形段叠加
        y_eff = min(max(y, 0.0), self.height)
        r = self.width / 2.0
        rect_h = max(self.height - r, 0.0)

        if y_eff <= r:
            d = 2.0 * r
            theta = 2.0 * np.arccos(1.0 - 2.0 * y_eff / d)
            return float((d ** 2 / 8.0) * (theta - np.sin(theta)))

        lower_area = 0.5 * np.pi * r ** 2              # 下部完整半圆
        upper_area = self.width * min(y_eff - r, rect_h)  # 上部矩形
        return float(min(lower_area + upper_area, self.full_area()))

    def top_width(self, y: float) -> float:
        """按水深计算水面宽度（m）

        Args:
            y: 水深，从底板算起 (m)

        Returns:
            水面宽度 (m)；满流圆管返回 0（无自由液面）
        """
        if y <= 0.0:
            return 0.0

        if self.shape == "circular":
            d = self.diameter
            if y >= d:
                return 0.0  # 满流，无自由液面
            # 弦长公式：T = D * sin(arccos(1 - 2y/D))
            alpha = np.arccos(1.0 - 2.0 * y / d)
            return float(d * np.sin(alpha))

        if self.shape == "rectangular":
            return float(self.width) if y <= self.height else 0.0

        # 拱形：下半圆段按弦长，上部矩形段为等宽
        if y >= self.height:
            return 0.0
        r = self.width / 2.0
        if y <= r:
            # 弦长 = 2*sqrt(r^2 - (r-y)^2)
            return float(2.0 * np.sqrt(max(r ** 2 - (r - y) ** 2, 0.0)))
        return float(self.width)

    def wetted_perimeter(self, y: float) -> float:
        """按水深计算湿周（m）

        Args:
            y: 水深，从底板算起 (m)

        Returns:
            湿周 (m)
        """
        if y <= 0.0:
            return 0.0

        if self.shape == "circular":
            d = self.diameter
            if y >= d:
                return float(np.pi * d)
            theta = 2.0 * np.arccos(1.0 - 2.0 * y / d)
            return float(d * theta / 2.0)

        if self.shape == "rectangular":
            if y >= self.height:
                # 满流：上盖板也算湿周
                return float(2.0 * (self.width + self.height))
            y_eff = min(y, self.height)
            return float(self.width + 2.0 * y_eff)

        # 拱形：下半圆弧 + 两侧竖直壁（近似）
        # TODO: 精确拱形几何（如椭圆拱、抛物线拱）需进一步细化
        y_eff = min(y, self.height)
        r = self.width / 2.0
        rect_h = max(self.height - r, 0.0)

        if y_eff <= r:
            # 下半圆弧段：弧长 = r * theta（theta = 2*arccos(1 - y/r)）
            theta = 2.0 * np.arccos(max(-1.0, min(1.0, 1.0 - y_eff / r)))
            return float(r * theta)

        arc_part = np.pi * r                            # 下部完整半圆弧长
        wall_part = 2.0 * min(y_eff - r, rect_h)       # 两侧竖直壁
        return float(arc_part + wall_part)

    def hydraulic_radius_at_depth(self, y: float) -> float:
        """按水深计算水力半径 R = A/P（m）

        Args:
            y: 水深，从底板算起 (m)

        Returns:
            水力半径 (m)；湿周为零时返回 0
        """
        a = self.area_at_depth(y)
        p = self.wetted_perimeter(y)
        return float(a / p) if p > 0.0 else 0.0

    # ── 向后兼容方法 ──────────────────────────────────────────────────────────

    def area(self) -> float:
        """返回满流断面面积（向后兼容，等同于 full_area()）"""
        return self.full_area()

    def hydraulic_radius(self, depth: float) -> float:
        """按给定水深计算水力半径（向后兼容）

        满流圆管时直接返回 D/4（精确值），其余情况调用 hydraulic_radius_at_depth()。
        """
        if self.shape == "circular" and depth >= self.rise():
            return float(self.diameter / 4.0)
        return self.hydraulic_radius_at_depth(depth)

    def get_characteristic_height(self) -> float:
        """返回特征高度（向后兼容，等同于 rise()）"""
        return self.rise()

class Culvert:
    """
    Culvert hydraulic calculation class

    Implements FHWA HDS 5 methods for both inlet control
    and outlet control conditions.

    Parameters
    ----------
    position : float
        Position along channel (m)
    geometry : CulvertGeometry
        Culvert geometry parameters
    manning_n : float
        Manning's roughness coefficient (default 0.013)
    inlet_type : str
        Inlet type: 'square_edge', 'groove_end', 'groove_headwall', 'beveled'
    entrance_loss_coef : float
        Entrance loss coefficient Ke (default 0.5)
    exit_loss_coef : float
        Exit loss coefficient (default 1.0)

    Examples
    --------
    >>> geom = CulvertGeometry(shape='circular', diameter=1.2, length=30.0)
    >>> culvert = Culvert(position=100.0, geometry=geom)
    >>> Q, control = culvert.compute_discharge(h_upstream=1.5, h_downstream=0.6)
    >>> print(f"Flow: {Q:.2f} m³/s, Control: {control}")
    """

    def __init__(self,
                 position: float,
                 geometry: CulvertGeometry,
                 manning_n: float = 0.013,
                 inlet_type: Literal['square_edge', 'groove_end',
                                     'groove_headwall', 'beveled'] = 'square_edge',
                 entrance_loss_coef: float = 0.5,
                 exit_loss_coef: float = 1.0):

        self.position = position
        self.geom = geometry
        self.n = manning_n
        self.inlet_type = inlet_type
        self.K_e = entrance_loss_coef
        self.K_exit = exit_loss_coef

        # Get discharge coefficient based on inlet type
        self.C_d = self._get_discharge_coefficient()

        # Physical constant
        self.g = 9.81

    def _get_discharge_coefficient(self) -> float:
        """
        Get discharge coefficient based on inlet type

        Returns
        -------
        float
            Discharge coefficient Cd (dimensionless)

        References
        ----------
        FHWA HDS 5, Table 5-2
        """
        coef_map = {
            'square_edge': 0.47,
            'groove_end': 0.52,
            'groove_headwall': 0.53,
            'beveled': 0.57
        }
        return coef_map.get(self.inlet_type, 0.50)

    def _n_barrels(self) -> int:
        """获取孔数，未配置时默认为 1"""
        n_barrels = getattr(self.geom, 'n_barrels', 1)
        try:
            n_barrels = int(n_barrels)
        except (TypeError, ValueError):
            n_barrels = 1
        return max(1, n_barrels)

    def _full_area(self) -> float:
        """获取满流断面面积，兼容 Part 1 的几何接口"""
        if hasattr(self.geom, 'full_area'):
            return float(self.geom.full_area())
        return float(self.geom.area())

    def _rise(self) -> float:
        """获取特征高度（圆管直径或箱涵高度）"""
        if hasattr(self.geom, 'rise'):
            rise = self.geom.rise
            return float(rise() if callable(rise) else rise)
        return float(self.geom.get_characteristic_height())

    def _area_at_depth(self, depth: float) -> float:
        """按水深计算过水面积，优先使用 Part 1 提供的方法"""
        D = max(self._rise(), 1e-9)
        y = float(np.clip(depth, 0.0, D))

        if hasattr(self.geom, 'area_at_depth'):
            return float(self.geom.area_at_depth(y))

        if self.geom.shape == 'circular':
            if y <= 0.0:
                return 0.0
            if y >= D:
                return self._full_area()
            theta = 2.0 * np.arccos(1.0 - 2.0 * y / D)
            return (D ** 2 / 8.0) * (theta - np.sin(theta))
        if self.geom.shape == 'rectangular':
            width = float(self.geom.width)
            return width * y
        # arch 这里采用与现有几何一致的近似（矩形近似）
        width = float(self.geom.width)
        return width * y

    def _top_width_at_depth(self, depth: float) -> float:
        """按水深计算顶宽，用于临界水深方程"""
        D = max(self._rise(), 1e-9)
        y = float(np.clip(depth, 0.0, D))

        if hasattr(self.geom, 'top_width'):
            return float(self.geom.top_width(y))

        if self.geom.shape == 'circular':
            if y <= 0.0 or y >= D:
                return 0.0
            r = D / 2.0
            return 2.0 * np.sqrt(max(0.0, 2.0 * r * y - y ** 2))
        if self.geom.shape == 'rectangular':
            return float(self.geom.width) if y > 0.0 else 0.0
        return float(self.geom.width) if y > 0.0 else 0.0

    def _wetted_perimeter_at_depth(self, depth: float) -> float:
        """按水深计算湿周"""
        D = max(self._rise(), 1e-9)
        y = float(np.clip(depth, 0.0, D))

        if hasattr(self.geom, 'wetted_perimeter'):
            return float(self.geom.wetted_perimeter(y))

        if self.geom.shape == 'circular':
            if y <= 0.0:
                return 0.0
            if y >= D:
                return np.pi * D
            theta = 2.0 * np.arccos(1.0 - 2.0 * y / D)
            return D * theta / 2.0
        if self.geom.shape == 'rectangular':
            width = float(self.geom.width)
            return width + 2.0 * y if y > 0.0 else 0.0
        width = float(self.geom.width)
        return width + 2.0 * y if y > 0.0 else 0.0

    def _hydraulic_radius_at_depth(self, depth: float) -> float:
        """按水深计算水力半径"""
        if hasattr(self.geom, 'hydraulic_radius_at_depth'):
            return float(self.geom.hydraulic_radius_at_depth(depth))

        A = self._area_at_depth(depth)
        P = self._wetted_perimeter_at_depth(depth)
        return A / P if P > 0.0 else 0.0

    def _lookup_inlet_coeffs(self) -> dict:
        """
        从 INLET_COEFF_TABLE 查找入口控制系数。

        兼容字典和 dataclass 两种表项格式；若未找到则退化到保守默认值。
        """
        table = globals().get('INLET_COEFF_TABLE')
        coeff_item = None
        shape = getattr(self.geom, 'shape', None)
        material = getattr(self, 'material', None)
        inlet_family = getattr(self, 'inlet_family', None)

        if isinstance(table, dict):
            candidate_keys = []
            if material is not None:
                candidate_keys.extend([
                    (shape, material, self.inlet_type),
                    (shape, material),
                    (material, self.inlet_type),
                ])
            if inlet_family is not None:
                candidate_keys.extend([
                    (shape, inlet_family, self.inlet_type),
                    (shape, inlet_family),
                ])
            candidate_keys.extend([
                (shape, self.inlet_type),
                self.inlet_type,
                shape,
            ])

            for key in candidate_keys:
                if key in table:
                    coeff_item = table[key]
                    break

            # 再做一次宽松匹配，兼容 tuple key 的不同顺序
            if coeff_item is None:
                for key, value in table.items():
                    if not isinstance(key, tuple):
                        continue
                    key_tokens = {str(token) for token in key}
                    if str(shape) in key_tokens and str(self.inlet_type) in key_tokens:
                        coeff_item = value
                        break

        default_map = {
            'square_edge': {'K': 1.50, 'M': 1.75, 'c': 0.43, 'Y': 0.70, 'slope_coef': 0.0},
            'groove_end': {'K': 1.35, 'M': 1.70, 'c': 0.39, 'Y': 0.66, 'slope_coef': 0.0},
            'groove_headwall': {'K': 1.28, 'M': 1.68, 'c': 0.36, 'Y': 0.63, 'slope_coef': 0.0},
            'beveled': {'K': 1.15, 'M': 1.65, 'c': 0.32, 'Y': 0.58, 'slope_coef': 0.0},
        }
        defaults = default_map.get(self.inlet_type, default_map['square_edge'])

        def _read_coeff(name: str, fallback: float) -> float:
            if coeff_item is None:
                return float(fallback)
            if isinstance(coeff_item, dict):
                return float(coeff_item.get(name, fallback))
            if hasattr(coeff_item, name):
                return float(getattr(coeff_item, name))
            return float(fallback)

        K = max(_read_coeff('K', defaults['K']), 1e-9)
        M = max(_read_coeff('M', defaults['M']), 1e-9)
        c = max(_read_coeff('c', defaults['c']), 1e-9)
        Y = _read_coeff('Y', defaults['Y'])
        slope_coef = _read_coeff('slope_coef', defaults['slope_coef'])

        return {'K': K, 'M': M, 'c': c, 'Y': Y, 'slope_coef': slope_coef}

    def _required_headwater_inlet(self, q_per_barrel: float) -> float:
        """
        给定单孔流量，计算入口控制所需上游水头（相对进口底板）。

        Form 1 (未淹没): HW/D = K*(Q/(A*sqrt(D)))^M + slope - 0.5*S
        Form 2 (淹没):   HW/D = c*(Q/(A*sqrt(D)))^2 + Y + slope - 0.5*S
        在两式之间按 HW/D≈1.5 做线性插值平滑。
        """
        q = max(float(q_per_barrel), 0.0)
        if q <= 0.0:
            return 0.0

        coeffs = self._lookup_inlet_coeffs()
        A = max(self._full_area(), 1e-9)
        D = max(self._rise(), 1e-9)
        S = float(self.geom.slope)

        q_star = q / (A * np.sqrt(D))
        slope_term = coeffs['slope_coef'] * S
        base_term = slope_term - 0.5 * S

        hw_d_form1 = coeffs['K'] * (q_star ** coeffs['M']) + base_term
        hw_d_form2 = coeffs['c'] * (q_star ** 2.0) + coeffs['Y'] + base_term

        # 在 HW/D 约 1.5 附近平滑切换，避免分段突变
        trans_lo = 1.4
        trans_hi = 1.6
        if hw_d_form1 <= trans_lo:
            hw_d = hw_d_form1
        elif hw_d_form1 >= trans_hi:
            hw_d = hw_d_form2
        else:
            alpha = (hw_d_form1 - trans_lo) / (trans_hi - trans_lo)
            hw_d = (1.0 - alpha) * hw_d_form1 + alpha * hw_d_form2

        return max(0.0, hw_d * D)

    def _critical_depth(self, q_per_barrel: float) -> float:
        """用 Newton 迭代求解临界水深 y_c"""
        q = max(float(q_per_barrel), 0.0)
        D = max(self._rise(), 1e-9)
        if q <= 0.0:
            return 0.0

        eps = max(1e-6, 1e-6 * D)

        def residual(y: float) -> float:
            A = max(self._area_at_depth(y), 1e-12)
            T = max(self._top_width_at_depth(y), 1e-12)
            return q ** 2 * T / (self.g * A ** 3) - 1.0

        # 先做 Newton，加速收敛
        y = min(max(0.5 * D, eps), D - eps)
        for _ in range(40):
            f = residual(y)
            if abs(f) < 1e-8:
                return float(np.clip(y, 0.0, D))

            dy = max(1e-6, 1e-5 * D)
            y_l = max(eps, y - dy)
            y_r = min(D - eps, y + dy)
            f_l = residual(y_l)
            f_r = residual(y_r)
            denom = y_r - y_l
            if denom <= 0.0:
                break
            df = (f_r - f_l) / denom
            if abs(df) < 1e-12:
                break

            y_new = y - f / df
            if not (eps <= y_new <= D - eps):
                break
            if abs(y_new - y) < 1e-8:
                y = y_new
                return float(np.clip(y, 0.0, D))
            y = y_new

        # Newton 未收敛时，回退到区间二分保证稳定
        y_low = eps
        y_high = D - eps
        f_low = residual(y_low)
        f_high = residual(y_high)

        # 若全断面仍偏超临界，认为临界水深接近满流
        if f_high > 0.0:
            return D

        for _ in range(80):
            y_mid = 0.5 * (y_low + y_high)
            f_mid = residual(y_mid)
            if abs(f_mid) < 1e-8:
                return float(np.clip(y_mid, 0.0, D))
            if f_mid > 0.0:
                y_low = y_mid
            else:
                y_high = y_mid

        return float(np.clip(0.5 * (y_low + y_high), 0.0, D))

    def _normal_depth(self, q_per_barrel: float) -> float:
        """反解 Manning 方程求正常水深 y_n"""
        q = max(float(q_per_barrel), 0.0)
        D = max(self._rise(), 1e-9)
        S = float(self.geom.slope)
        if q <= 0.0:
            return 0.0
        if S <= 0.0:
            return D

        eps = max(1e-6, 1e-6 * D)
        sqrt_s = np.sqrt(S)

        def residual(y: float) -> float:
            A = max(self._area_at_depth(y), 1e-12)
            R = max(self._hydraulic_radius_at_depth(y), 1e-12)
            q_calc = (1.0 / self.n) * A * (R ** (2.0 / 3.0)) * sqrt_s
            return q_calc - q

        y = min(max(0.67 * D, eps), D - eps)
        for _ in range(40):
            f = residual(y)
            if abs(f) < 1e-8:
                return float(np.clip(y, 0.0, D))

            dy = max(1e-6, 1e-5 * D)
            y_l = max(eps, y - dy)
            y_r = min(D - eps, y + dy)
            f_l = residual(y_l)
            f_r = residual(y_r)
            denom = y_r - y_l
            if denom <= 0.0:
                break
            df = (f_r - f_l) / denom
            if abs(df) < 1e-12:
                break

            y_new = y - f / df
            if not (eps <= y_new <= D - eps):
                break
            if abs(y_new - y) < 1e-8:
                y = y_new
                return float(np.clip(y, 0.0, D))
            y = y_new

        y_low = eps
        y_high = D - eps
        f_low = residual(y_low)
        f_high = residual(y_high)

        # 若满流仍达不到给定 Q，说明处于满流受限状态
        if f_high < 0.0:
            return D
        if f_low > 0.0:
            return y_low

        for _ in range(80):
            y_mid = 0.5 * (y_low + y_high)
            f_mid = residual(y_mid)
            if abs(f_mid) < 1e-8:
                return float(np.clip(y_mid, 0.0, D))
            if f_mid > 0.0:
                y_high = y_mid
            else:
                y_low = y_mid

        return float(np.clip(0.5 * (y_low + y_high), 0.0, D))

    def _required_headwater_outlet(self, q_per_barrel: float, tw: float) -> float:
        """
        给定单孔流量与尾水深，计算出口控制所需上游水头。

        - y_c: 临界水深（Newton）
        - y_n: 正常水深（Manning 反解）
        - h_o: 满流用 max(tw, (y_c + D)/2)，非满流用 max(tw, y_c)
        - HW = h_o + H_f + H_e - L*S
        """
        q = max(float(q_per_barrel), 0.0)
        if q <= 0.0:
            return 0.0

        D = max(self._rise(), 1e-9)
        L = float(self.geom.length)
        S = float(self.geom.slope)
        tw_depth = max(float(tw), 0.0)

        y_c = self._critical_depth(q)
        y_n = self._normal_depth(q)

        # 满流判定：尾水或均匀流/临界流达到（或逼近）管顶
        barrel_full = max(tw_depth, y_c, y_n) >= (D - 1e-6)

        if barrel_full:
            h_o = max(tw_depth, 0.5 * (y_c + D))
            flow_depth = D
        else:
            h_o = max(tw_depth, y_c)
            flow_depth = min(D, max(y_c, y_n))

        A = max(self._area_at_depth(flow_depth), 1e-12)
        R = max(self._hydraulic_radius_at_depth(flow_depth), 1e-12)
        V = q / A

        # 满流公式在非满流时也以当前流深近似计算，保持连续
        H_f = (self.n * q) ** 2 * L / (R ** (4.0 / 3.0) * A ** 2)
        H_e = self.K_e * V ** 2 / (2.0 * self.g)

        hw_required = h_o + H_f + H_e - L * S
        return max(0.0, hw_required)

    def _solve_discharge_by_required_headwater(self, hw_available: float, required_hw_func) -> float:
        """通用二分求解器：在给定可用水头下反求流量"""
        hw_avail = max(float(hw_available), 0.0)
        if hw_avail <= 0.0:
            return 0.0

        n_barrels = self._n_barrels()
        A = max(self._full_area(), 1e-9)
        D = max(self._rise(), 1e-9)

        # 初值：按孔口量级估计，再逐步扩展包络
        q_per_barrel_guess = A * np.sqrt(2.0 * self.g * max(hw_avail, 0.05 * D))
        q_low = 0.0
        q_high = max(1e-6, q_per_barrel_guess * n_barrels)

        for _ in range(60):
            hw_high = required_hw_func(q_high / n_barrels)
            if hw_high >= hw_avail:
                break
            q_high *= 2.0
            if q_high > 1e6 * n_barrels:
                return q_high

        for _ in range(80):
            q_mid = 0.5 * (q_low + q_high)
            hw_mid = required_hw_func(q_mid / n_barrels)
            if hw_mid <= hw_avail:
                q_low = q_mid
            else:
                q_high = q_mid

        return q_low

    def _inlet_control(self, h_upstream: float) -> Tuple[float, float]:
        """
        兼容旧接口：给定上游水深，返回入口控制流量与所需水头。
        """
        hw_avail = max(float(h_upstream), 0.0)
        q_total = self._solve_discharge_by_required_headwater(hw_avail, self._required_headwater_inlet)
        q_per_barrel = q_total / self._n_barrels()
        hw_req = self._required_headwater_inlet(q_per_barrel)
        return q_total, hw_req

    def _outlet_control(self, h_upstream: float, h_downstream: float) -> Tuple[float, float]:
        """
        兼容旧接口：给定上/下游水深，返回出口控制流量与所需水头。
        """
        hw_avail = max(float(h_upstream), 0.0)
        tw_depth = max(float(h_downstream), 0.0)
        q_total = self._solve_discharge_by_required_headwater(
            hw_avail,
            lambda q_pb: self._required_headwater_outlet(q_pb, tw_depth)
        )
        q_per_barrel = q_total / self._n_barrels()
        hw_req = self._required_headwater_outlet(q_per_barrel, tw_depth)
        return q_total, hw_req

    def compute_discharge(self,
                         h_upstream: float,
                         h_downstream: float) -> Tuple[float, str]:
        """
        计算涵洞总流量（支持多孔）并自动判定控制类型。

        计算流程：
        1) 对每个候选 Q 计算单孔流量 q=Q/n_barrels
        2) 分别计算 HW_inlet(q) 与 HW_outlet(q, TW)
        3) HW_required(Q) = max(HW_inlet, HW_outlet)
        4) 求解 HW_required(Q) = HW_available 的 Q
        """
        hw_available = max(float(h_upstream), 0.0)
        tw_depth = max(float(h_downstream), 0.0)
        if hw_available <= 0.0:
            return 0.0, 'inlet'

        n_barrels = self._n_barrels()

        def required_hw_total(q_total: float) -> Tuple[float, str]:
            q_per_barrel = max(float(q_total), 0.0) / n_barrels
            hw_inlet = self._required_headwater_inlet(q_per_barrel)
            hw_outlet = self._required_headwater_outlet(q_per_barrel, tw_depth)
            if hw_outlet >= hw_inlet:
                return hw_outlet, 'outlet'
            return hw_inlet, 'inlet'

        A = max(self._full_area(), 1e-9)
        D = max(self._rise(), 1e-9)
        q_total_low = 0.0
        q_total_high = max(1e-6, n_barrels * A * np.sqrt(2.0 * self.g * max(hw_available, 0.05 * D)))

        # 先扩展上界，确保覆盖到所需水头
        for _ in range(60):
            hw_high, _ = required_hw_total(q_total_high)
            if hw_high >= hw_available:
                break
            q_total_high *= 2.0
            if q_total_high > 1e6 * n_barrels:
                break

        # 二分求解最大可过流量
        for _ in range(80):
            q_mid = 0.5 * (q_total_low + q_total_high)
            hw_mid, _ = required_hw_total(q_mid)
            if hw_mid <= hw_available:
                q_total_low = q_mid
            else:
                q_total_high = q_mid

        q_total = q_total_low
        _, control_type = required_hw_total(q_total)
        return q_total, control_type

    def compute_headloss(self, Q: float, h_downstream: float) -> float:
        """
        Compute total head loss through culvert

        Parameters
        ----------
        Q : float
            Discharge (m³/s)
        h_downstream : float
            Downstream water depth (m)

        Returns
        -------
        float
            Total head loss (m)

        Notes
        -----
        Total head loss includes:
        - Friction loss in barrel
        - Entrance loss
        - Exit loss
        """
        if Q <= 0:
            return 0.0

        A = self.geom.area()
        V = Q / A
        L = self.geom.length
        D = self.geom.get_characteristic_height()
        R_h = self.geom.hydraulic_radius(D)

        # Friction loss
        if R_h > 0:
            h_f = (self.n ** 2 * L * V ** 2) / (R_h ** (4/3))
        else:
            h_f = 0.0

        # Entrance loss
        h_e = self.K_e * V ** 2 / (2 * self.g)

        # Exit loss
        h_exit = self.K_exit * V ** 2 / (2 * self.g)

        return h_f + h_e + h_exit

    def get_derivatives(self,
                       Q: float,
                       h_upstream: float,
                       h_downstream: float) -> Tuple[float, float]:
        """
        Compute flow derivatives with respect to water depths

        Used for Newton-Raphson solver in steady-state calculations.

        Parameters
        ----------
        Q : float
            Current discharge (m³/s)
        h_upstream : float
            Upstream water depth (m)
        h_downstream : float
            Downstream water depth (m)

        Returns
        -------
        dQ_dh_up : float
            ∂Q/∂h_upstream
        dQ_dh_down : float
            ∂Q/∂h_downstream

        Notes
        -----
        Uses numerical differentiation with central differences.
        """
        delta_h = 0.001  # Small perturbation

        # Derivative with respect to upstream depth
        Q_plus_up, _ = self.compute_discharge(h_upstream + delta_h, h_downstream)
        Q_minus_up, _ = self.compute_discharge(h_upstream - delta_h, h_downstream)
        dQ_dh_up = (Q_plus_up - Q_minus_up) / (2 * delta_h)

        # Derivative with respect to downstream depth
        Q_plus_down, _ = self.compute_discharge(h_upstream, h_downstream + delta_h)
        Q_minus_down, _ = self.compute_discharge(h_upstream, h_downstream - delta_h)
        dQ_dh_down = (Q_plus_down - Q_minus_down) / (2 * delta_h)

        return dQ_dh_up, dQ_dh_down

    def __repr__(self) -> str:
        """String representation"""
        return (f"Culvert(position={self.position}, "
                f"shape={self.geom.shape}, "
                f"n={self.n}, inlet_type={self.inlet_type})")


# ============================================================================
# Convenience functions
# ============================================================================

def create_circular_culvert(position: float,
                           diameter: float,
                           length: float,
                           manning_n: float = 0.013,
                           inlet_type: str = 'square_edge',
                           slope: float = 0.001) -> Culvert:
    """
    Create a circular culvert

    Parameters
    ----------
    position : float
        Position along channel (m)
    diameter : float
        Culvert diameter (m)
    length : float
        Culvert length (m)
    manning_n : float
        Manning's roughness coefficient
    inlet_type : str
        Inlet type
    slope : float
        Culvert slope

    Returns
    -------
    Culvert
        Configured culvert object

    Examples
    --------
    >>> culvert = create_circular_culvert(
    ...     position=100.0,
    ...     diameter=1.2,
    ...     length=30.0
    ... )
    """
    geom = CulvertGeometry(
        shape='circular',
        diameter=diameter,
        length=length,
        slope=slope
    )
    return Culvert(position, geom, manning_n, inlet_type)


def create_rectangular_culvert(position: float,
                               width: float,
                               height: float,
                               length: float,
                               manning_n: float = 0.013,
                               inlet_type: str = 'square_edge',
                               slope: float = 0.001) -> Culvert:
    """
    Create a rectangular culvert

    Parameters
    ----------
    position : float
        Position along channel (m)
    width : float
        Culvert width (m)
    height : float
        Culvert height (m)
    length : float
        Culvert length (m)
    manning_n : float
        Manning's roughness coefficient
    inlet_type : str
        Inlet type
    slope : float
        Culvert slope

    Returns
    -------
    Culvert
        Configured culvert object

    Examples
    --------
    >>> culvert = create_rectangular_culvert(
    ...     position=100.0,
    ...     width=2.0,
    ...     height=1.5,
    ...     length=40.0
    ... )
    """
    geom = CulvertGeometry(
        shape='rectangular',
        width=width,
        height=height,
        length=length,
        slope=slope
    )
    return Culvert(position, geom, manning_n, inlet_type)


# ============================================================================
# Validation functions
# ============================================================================

def validate_culvert_design(culvert: Culvert,
                           Q_design: float,
                           h_upstream_max: float,
                           h_downstream: float) -> dict:
    """
    Validate culvert design for given flow conditions

    Parameters
    ----------
    culvert : Culvert
        Culvert to validate
    Q_design : float
        Design discharge (m³/s)
    h_upstream_max : float
        Maximum allowable upstream depth (m)
    h_downstream : float
        Downstream water depth (m)

    Returns
    -------
    dict
        Validation results with keys:
        - 'passes': bool
        - 'Q_actual': float
        - 'h_upstream_required': float
        - 'control_type': str
        - 'headloss': float
        - 'velocity': float
        - 'message': str
    """
    # Compute actual discharge
    Q_actual, control_type = culvert.compute_discharge(h_upstream_max, h_downstream)

    # Compute head loss
    headloss = culvert.compute_headloss(Q_actual, h_downstream)

    # Compute velocity
    A = culvert.geom.area()
    velocity = Q_actual / A if A > 0 else 0.0

    # Check if design passes
    passes = Q_actual >= Q_design

    if passes:
        message = f"Design passes: Q={Q_actual:.2f} m³/s >= {Q_design:.2f} m³/s"
    else:
        message = f"Design fails: Q={Q_actual:.2f} m³/s < {Q_design:.2f} m³/s"

    return {
        'passes': passes,
        'Q_actual': Q_actual,
        'h_upstream_required': h_upstream_max,
        'control_type': control_type,
        'headloss': headloss,
        'velocity': velocity,
        'message': message
    }
