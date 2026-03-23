"""断面属性预计算表 — 加速非恒定流 NR 迭代中的几何查询。

在 Preissmann 非恒定流求解器的 Newton-Raphson 迭代中，需要频繁查询
断面几何参数 A(Z), B(Z), K(Z), P(Z) 及其导数。直接调用
CrossSection.compute_geometry_from_wse() 每次都重新积分（NaturalSection
尤其耗时）。PropertyTable 预计算离散点上的值，运行时通过 numpy 线性插值
快速查询，避免重复积分。

支持 LOB/Channel/ROB 分区 K 计算（与 HEC-RAS 一致）。
"""

import numpy as np


# ------------------------------------------------------------------
# 独立几何计算函数（从 SteadyProfileSolver 提取）
# ------------------------------------------------------------------

def segment_area_perimeter(
    stations: np.ndarray,
    elevations: np.ndarray,
    water_level: float,
    sta_lo: float,
    sta_hi: float,
) -> tuple[float, float]:
    """计算 [sta_lo, sta_hi] 区间在给定水位下的面积和湿周。

    湿周不包含区间两端的垂直面（HEC-RAS / Posey 1967 惯例）。
    逻辑与 SteadyProfileSolver._segment_area_perimeter 完全一致。
    """
    area = 0.0
    perimeter = 0.0
    for j in range(len(stations) - 1):
        s1, s2 = float(stations[j]), float(stations[j + 1])
        z1, z2 = float(elevations[j]), float(elevations[j + 1])
        if s2 <= sta_lo or s1 >= sta_hi:
            continue
        if s1 < sta_lo:
            frac = (sta_lo - s1) / (s2 - s1)
            z1 = z1 + frac * (z2 - z1)
            s1 = sta_lo
        if s2 > sta_hi:
            frac = (sta_hi - s1) / (s2 - s1)
            z2 = z1 + frac * (z2 - z1)
            s2 = sta_hi
        ds = s2 - s1
        dz = z2 - z1
        if ds <= 0.0:
            if abs(dz) > 0.0 and abs(s1 - sta_lo) > 0.01 and abs(s1 - sta_hi) > 0.01:
                z_lo = min(z1, z2)
                z_hi = max(z1, z2)
                if z_lo < water_level:
                    wet_height = min(water_level, z_hi) - z_lo
                    perimeter += wet_height
            continue
        if z1 >= water_level and z2 >= water_level:
            continue
        elif z1 < water_level and z2 < water_level:
            area += 0.5 * (water_level - z1 + water_level - z2) * ds
            perimeter += np.sqrt(ds ** 2 + dz ** 2)
        elif z1 < water_level <= z2:
            fw = (water_level - z1) / (z2 - z1)
            dsw, dzw = ds * fw, dz * fw
            area += 0.5 * (water_level - z1) * dsw
            perimeter += np.sqrt(dsw ** 2 + dzw ** 2)
        else:
            fw = (water_level - z2) / (z1 - z2)
            dsw, dzw = ds * fw, dz * fw
            area += 0.5 * (water_level - z2) * dsw
            perimeter += np.sqrt(dsw ** 2 + dzw ** 2)
    return area, perimeter


def zone_conveyance(
    stations: np.ndarray,
    elevations: np.ndarray,
    water_level: float,
    sta_min: float,
    sta_max: float,
    n: float,
) -> tuple[float, float]:
    """计算单个分区的 K 和 A。

    K = (1/n) * A * R^(2/3)，R = A / P。
    """
    if sta_max - sta_min < 1e-6 or n <= 0.0:
        return 0.0, 0.0
    A, P = segment_area_perimeter(stations, elevations, water_level, sta_min, sta_max)
    if A <= 0.0 or P <= 0.0:
        return 0.0, 0.0
    R = A / P
    K = (1.0 / n) * A * R ** (2.0 / 3.0)
    return float(K), float(A)


def subdivided_conveyance(
    stations: np.ndarray,
    elevations: np.ndarray,
    water_level: float,
    left_bank: float,
    right_bank: float,
    n_lob: float,
    n_ch: float,
    n_rob: float,
) -> tuple[float, float]:
    """HEC-RAS LOB/Channel/ROB 分区 K 计算。

    K_total = K_LOB + K_Ch + K_ROB
    与 SteadyProfileSolver._compute_subdivided_conveyance 逻辑一致。

    Returns:
        (K_total, A_total)
    """
    sta_min = float(np.min(stations))
    sta_max = float(np.max(stations))

    K_lob, A_lob = 0.0, 0.0
    if left_bank > sta_min + 1e-6:
        K_lob, A_lob = zone_conveyance(
            stations, elevations, water_level, sta_min, left_bank, n_lob
        )

    K_ch, A_ch = zone_conveyance(
        stations, elevations, water_level, left_bank, right_bank, n_ch
    )

    K_rob, A_rob = 0.0, 0.0
    if right_bank < sta_max - 1e-6:
        K_rob, A_rob = zone_conveyance(
            stations, elevations, water_level, right_bank, sta_max, n_rob
        )

    K_total = K_lob + K_ch + K_rob
    A_total = A_lob + A_ch + A_rob
    return K_total, A_total


class PropertyTable:
    """断面几何属性预计算插值表。

    支持两种模式：
    1. 单一 Manning n（向后兼容）
    2. LOB/Channel/ROB 分区 K（与 HEC-RAS 一致，推荐）

    分区模式通过传入 left_bank, right_bank, manning_n_lob, manning_n_rob 启用。
    """

    def __init__(
        self,
        section,
        manning_n: float,
        z_min: float | None = None,
        z_max: float | None = None,
        n_points: int = 201,
        left_bank: float | None = None,
        right_bank: float | None = None,
        manning_n_lob: float | None = None,
        manning_n_rob: float | None = None,
    ):
        """
        Args:
            section: CrossSection 实例（需实现 get_invert_elevation,
                     compute_geometry_from_wse, compute_conveyance）
            manning_n: Manning 糙率系数（主槽）
            z_min: 最低水位（默认 = invert_elevation）
            z_max: 最高水位（默认 = invert_elevation + 30 m）
            n_points: 插值节点数（默认 201）
            left_bank: 左岸站号 (m)，启用分区 K
            right_bank: 右岸站号 (m)，启用分区 K
            manning_n_lob: 左滩 Manning n
            manning_n_rob: 右滩 Manning n
        """
        self.section = section
        self.manning_n = manning_n

        invert = section.get_invert_elevation()
        self.z_min = z_min if z_min is not None else invert
        self.z_max = z_max if z_max is not None else invert + 30.0
        self.n_points = n_points

        # 分区参数
        self.left_bank = left_bank
        self.right_bank = right_bank
        self.manning_n_lob = manning_n_lob if manning_n_lob is not None else manning_n
        self.manning_n_rob = manning_n_rob if manning_n_rob is not None else manning_n

        # 判断是否启用分区模式
        self._subdivided = (
            left_bank is not None
            and right_bank is not None
            and hasattr(section, 'distances')
            and hasattr(section, 'elevations')
        )

        self._build_table()

    # ------------------------------------------------------------------
    # 预计算
    # ------------------------------------------------------------------

    def _build_table(self) -> None:
        """预计算所有插值节点上的属性值及解析导数。"""
        self.z_values = np.linspace(self.z_min, self.z_max, self.n_points)

        self.area = np.zeros(self.n_points)
        self.width = np.zeros(self.n_points)
        self.perimeter = np.zeros(self.n_points)
        self.hydraulic_radius = np.zeros(self.n_points)
        self.conveyance = np.zeros(self.n_points)

        if self._subdivided:
            sta = np.asarray(self.section.distances, dtype=np.float64)
            ele = np.asarray(self.section.elevations, dtype=np.float64)

        for i, z in enumerate(self.z_values):
            geom = self.section.compute_geometry_from_wse(z)
            self.area[i] = geom.area
            self.width[i] = geom.width
            self.perimeter[i] = geom.perimeter
            self.hydraulic_radius[i] = geom.hydraulic_radius

            if self._subdivided:
                K, _A = subdivided_conveyance(
                    sta, ele, z,
                    self.left_bank, self.right_bank,
                    self.manning_n_lob, self.manning_n, self.manning_n_rob,
                )
                self.conveyance[i] = K if K > 0 else self.section.compute_conveyance(
                    z, self.manning_n
                )
            else:
                self.conveyance[i] = self.section.compute_conveyance(z, self.manning_n)

        # 导数：numpy.gradient 用中心差分（端点用一阶差分），步长均匀
        dz = self.z_values[1] - self.z_values[0]
        self.dA_dZ = np.gradient(self.area, dz)
        self.dK_dZ = np.gradient(self.conveyance, dz)

    # ------------------------------------------------------------------
    # 基本几何量查询
    # ------------------------------------------------------------------

    def get_area(self, z: float | np.ndarray) -> float | np.ndarray:
        """查询过水面积 A(Z)。"""
        return np.interp(z, self.z_values, self.area)

    def get_width(self, z: float | np.ndarray) -> float | np.ndarray:
        """查询水面宽度 B(Z)。"""
        return np.interp(z, self.z_values, self.width)

    def get_perimeter(self, z: float | np.ndarray) -> float | np.ndarray:
        """查询湿周 P(Z)。"""
        return np.interp(z, self.z_values, self.perimeter)

    def get_hydraulic_radius(self, z: float | np.ndarray) -> float | np.ndarray:
        """查询水力半径 R(Z)。"""
        return np.interp(z, self.z_values, self.hydraulic_radius)

    def get_conveyance(self, z: float | np.ndarray) -> float | np.ndarray:
        """查询输水能力 K(Z)。"""
        return np.interp(z, self.z_values, self.conveyance)

    # ------------------------------------------------------------------
    # 导数查询
    # ------------------------------------------------------------------

    def get_dA_dZ(self, z: float | np.ndarray) -> float | np.ndarray:
        """查询 dA/dZ（等于水面宽度 B，通过预计算梯度插值得到）。"""
        return np.interp(z, self.z_values, self.dA_dZ)

    def get_dK_dZ(self, z: float | np.ndarray) -> float | np.ndarray:
        """查询 dK/dZ。"""
        return np.interp(z, self.z_values, self.dK_dZ)

    # ------------------------------------------------------------------
    # 摩擦坡降及其偏导数（NR 雅可比矩阵所需）
    # ------------------------------------------------------------------

    def get_friction_slope(self, z: float, Q: float) -> float:
        """计算摩擦坡降 Sf = Q|Q| / K²。"""
        K = float(self.get_conveyance(z))
        if K <= 0.0:
            return 0.0
        return Q * abs(Q) / (K * K)

    def get_dSf_dZ(self, z: float, Q: float) -> float:
        """计算 dSf/dZ = -2·Q·|Q| / K³ · dK/dZ（链式法则解析导数）。"""
        K = float(self.get_conveyance(z))
        if K <= 0.0:
            return 0.0
        dK = float(self.get_dK_dZ(z))
        return -2.0 * Q * abs(Q) / (K ** 3) * dK

    def get_dSf_dQ(self, z: float, Q: float) -> float:
        """计算 dSf/dQ = 2·|Q| / K²。"""
        K = float(self.get_conveyance(z))
        if K <= 0.0:
            return 0.0
        return 2.0 * abs(Q) / (K * K)
