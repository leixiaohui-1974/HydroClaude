"""断面属性预计算表 — 加速非恒定流 NR 迭代中的几何查询。

在 Preissmann 非恒定流求解器的 Newton-Raphson 迭代中，需要频繁查询
断面几何参数 A(Z), B(Z), K(Z), P(Z) 及其导数。直接调用
CrossSection.compute_geometry_from_wse() 每次都重新积分（NaturalSection
尤其耗时）。PropertyTable 预计算离散点上的值，运行时通过 numpy 线性插值
快速查询，避免重复积分。
"""

import numpy as np


class PropertyTable:
    """
    断面几何属性预计算插值表。

    在给定水位范围内预计算 A(Z), B(Z), K(Z), P(Z) 等参数，
    运行时通过 numpy 线性插值快速查询，避免重复积分。

    支持标量和 numpy 数组输入。
    """

    def __init__(
        self,
        section,
        manning_n: float,
        z_min: float | None = None,
        z_max: float | None = None,
        n_points: int = 201,
    ):
        """
        Args:
            section: CrossSection 实例（需实现 get_invert_elevation,
                     compute_geometry_from_wse, compute_conveyance）
            manning_n: Manning 糙率系数
            z_min: 最低水位（默认 = invert_elevation）
            z_max: 最高水位（默认 = invert_elevation + 30 m）
            n_points: 插值节点数（默认 201）
        """
        self.section = section
        self.manning_n = manning_n

        invert = section.get_invert_elevation()
        self.z_min = z_min if z_min is not None else invert
        self.z_max = z_max if z_max is not None else invert + 30.0
        self.n_points = n_points

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

        for i, z in enumerate(self.z_values):
            geom = self.section.compute_geometry_from_wse(z)
            self.area[i] = geom.area
            self.width[i] = geom.width
            self.perimeter[i] = geom.perimeter
            self.hydraulic_radius[i] = geom.hydraulic_radius
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
