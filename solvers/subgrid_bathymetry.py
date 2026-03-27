"""
subgrid_bathymetry.py — 亚网格地形技术（Subgrid Bathymetry）

核心思想：
  在粗网格单元内存储高分辨率地形信息，通过预计算的亚网格查找表
  （水深-面积关系、水深-湿周关系）来提升干湿边界精度和水量守恒性。

方法来源：
  - Casulli & Stelling (2011): "Semi-implicit subgrid modelling of three-dimensional
    free-surface flows" - Int. J. Numer. Meth. Fluids
  - Volp et al. (2013): "A subgrid method for modelling large-scale propagation
    of surface gravity waves" - Ocean Modelling
  - MIKE FLOOD 亚网格方法（DHI, 2022）

亚网格技术的优势：
  1. 干湿边界精度：粗网格单元内的高分辨率地形使干湿前锋位置更准确
  2. 水量守恒：通过精确的水深-面积关系避免虚假水量
  3. 计算效率：仅需粗网格计算，但具有细网格的地形分辨率
  4. 复杂地形：能正确处理堤坝、道路等亚网格尺度的障碍物

查找表结构：
  对每个粗网格单元，预计算：
  - A(η)   : 水面高程 η 对应的湿面积（m²）
  - V(η)   : 水面高程 η 对应的水体积（m³）
  - P(η)   : 水面高程 η 对应的湿周（m）
  - η_min  : 单元内最低点高程（干床阈值）
  - η_max  : 单元内最高点高程（完全淹没阈值）
"""

from typing import Optional, Tuple
import numpy as np
from scipy.interpolate import interp1d


class SubgridCell:
    """
    单个粗网格单元的亚网格信息。

    存储高分辨率地形的统计信息，并提供水深-面积-体积的快速查找。

    Attributes:
        z_sub    : 亚网格地形高程数组（形状 (n_sub_y, n_sub_x)）
        eta_min  : 单元内最低点高程
        eta_max  : 单元内最高点高程
        cell_area: 粗网格单元面积（m²）
        n_levels : 查找表的高程层数
    """

    def __init__(self, z_sub: np.ndarray, dx_coarse: float, dy_coarse: float,
                 n_levels: int = 100):
        """
        Args:
            z_sub     : 亚网格地形高程，形状 (n_sub_y, n_sub_x)
            dx_coarse : 粗网格单元 x 方向尺寸 (m)
            dy_coarse : 粗网格单元 y 方向尺寸 (m)
            n_levels  : 查找表的高程层数
        """
        self.z_sub = z_sub.copy()
        self.n_sub_y, self.n_sub_x = z_sub.shape
        self.dx_coarse = dx_coarse
        self.dy_coarse = dy_coarse
        self.cell_area = dx_coarse * dy_coarse
        self.n_levels = n_levels

        # 亚网格单元面积
        self.dA_sub = (dx_coarse / self.n_sub_x) * (dy_coarse / self.n_sub_y)

        # 地形统计
        self.eta_min = float(np.min(z_sub))
        self.eta_max = float(np.max(z_sub))
        self.eta_mean = float(np.mean(z_sub))

        # 预计算查找表
        self._build_lookup_table()

    def _build_lookup_table(self):
        """预计算水面高程 → 湿面积/体积/湿周的查找表。"""
        # 高程范围：从最低点到最高点 + 足够大的余量（至少 10 m）
        # 保证查找表能覆盖实际可能的水面高程
        eta_range = max(self.eta_max - self.eta_min, 0.1)
        eta_margin = max(10.0, 5.0 * eta_range)  # 至少 10 m 的余量
        self._eta_table = np.linspace(
            self.eta_min - 0.1 * eta_range,
            self.eta_max + eta_margin,
            self.n_levels
        )

        n = self.n_levels
        self._A_table = np.zeros(n)   # 湿面积 (m²)
        self._V_table = np.zeros(n)   # 水体积 (m³)
        self._P_table = np.zeros(n)   # 湿周 (m)（简化为湿面积周长估计）

        z_flat = self.z_sub.flatten()

        for k, eta in enumerate(self._eta_table):
            # 湿格点（水面高程高于地形）
            wet_mask = eta > z_flat
            n_wet = np.sum(wet_mask)

            # 湿面积
            self._A_table[k] = n_wet * self.dA_sub

            # 水体积（积分水深）
            if n_wet > 0:
                h_sub = np.maximum(eta - z_flat[wet_mask], 0.0)
                self._V_table[k] = np.sum(h_sub) * self.dA_sub
            else:
                self._V_table[k] = 0.0

            # 湿周（简化：湿面积的平方根 × 4，近似矩形）
            self._P_table[k] = 4.0 * np.sqrt(self._A_table[k]) if n_wet > 0 else 0.0

        # 最大体积（完全淹没时）
        V_max = float(self._V_table[-1])
        P_max = float(self._P_table[-1])

        # 构建插值函数（线性插值）
        self._A_interp = interp1d(self._eta_table, self._A_table,
                                   kind='linear', fill_value=(0.0, self.cell_area),
                                   bounds_error=False)
        self._V_interp = interp1d(self._eta_table, self._V_table,
                                   kind='linear', fill_value=(0.0, V_max),
                                   bounds_error=False)
        self._P_interp = interp1d(self._eta_table, self._P_table,
                                   kind='linear', fill_value=(0.0, P_max),
                                   bounds_error=False)

        # dV/deta（用于水深计算）
        deta = self._eta_table[1] - self._eta_table[0]
        self._dVdeta_table = np.gradient(self._V_table, deta)
        self._dVdeta_interp = interp1d(self._eta_table, self._dVdeta_table,
                                        kind='linear', fill_value=(0.0, self.cell_area),
                                        bounds_error=False)

    def get_wet_area(self, eta: float) -> float:
        """
        查询水面高程 eta 对应的湿面积。

        Args:
            eta : 水面高程 (m)

        Returns:
            A : 湿面积 (m²)，范围 [0, cell_area]
        """
        return float(self._A_interp(eta))

    def get_volume(self, eta: float) -> float:
        """
        查询水面高程 eta 对应的水体积。

        Args:
            eta : 水面高程 (m)

        Returns:
            V : 水体积 (m³)
        """
        return float(self._V_interp(eta))

    def get_wet_fraction(self, eta: float) -> float:
        """
        查询水面高程 eta 对应的湿面积比例。

        Args:
            eta : 水面高程 (m)

        Returns:
            alpha : 湿面积比例，范围 [0, 1]
        """
        return min(max(self.get_wet_area(eta) / self.cell_area, 0.0), 1.0)

    def get_mean_depth(self, eta: float) -> float:
        """
        查询水面高程 eta 对应的平均水深（体积/湿面积）。

        Args:
            eta : 水面高程 (m)

        Returns:
            h_mean : 平均水深 (m)
        """
        A = self.get_wet_area(eta)
        V = self.get_volume(eta)
        if A > 1e-10:
            return V / A
        return 0.0

    def eta_from_volume(self, V: float, eta_guess: Optional[float] = None) -> float:
        """
        从水体积反算水面高程（牛顿迭代）。

        Args:
            V        : 水体积 (m³)
            eta_guess: 初始猜测值（可选）

        Returns:
            eta : 水面高程 (m)
        """
        if V <= 0.0:
            return self.eta_min

        # 初始猜测
        if eta_guess is None:
            eta_guess = self.eta_mean

        eta = eta_guess
        for _ in range(20):
            V_eta = self.get_volume(eta)
            dVdeta = float(self._dVdeta_interp(eta))
            if abs(dVdeta) < 1e-12:
                break
            delta = (V - V_eta) / dVdeta
            eta += delta
            if abs(delta) < 1e-8:
                break

        return eta

    def get_hydraulic_radius(self, eta: float) -> float:
        """
        查询水面高程 eta 对应的水力半径 R = A / P。

        Args:
            eta : 水面高程 (m)

        Returns:
            R : 水力半径 (m)
        """
        A = self.get_wet_area(eta)
        P = float(self._P_interp(eta))
        if P > 1e-10:
            return A / P
        return 0.0


class SubgridBathymetry:
    """
    粗网格的亚网格地形管理器。

    为整个计算域的每个粗网格单元维护亚网格地形信息，
    提供向量化的查找接口。

    使用方法：
        1. 初始化：提供高分辨率 DEM 和粗网格参数
        2. 查询：通过水面高程数组获取湿面积、体积等信息
        3. 集成：与 Hydrostatic2DSolver 或 GPU2DSolver 配合使用

    Attributes:
        nx_coarse, ny_coarse : 粗网格尺寸
        refine_x, refine_y   : 亚网格细化倍数
        cells                : SubgridCell 对象的二维数组
    """

    def __init__(self, z_fine: np.ndarray,
                 nx_coarse: int, ny_coarse: int,
                 Lx: float, Ly: float,
                 n_levels: int = 100):
        """
        Args:
            z_fine     : 高分辨率 DEM，形状 (ny_fine, nx_fine)
            nx_coarse  : 粗网格 x 方向格点数
            ny_coarse  : 粗网格 y 方向格点数
            Lx, Ly     : 计算域尺寸 (m)
            n_levels   : 每个单元查找表的高程层数
        """
        self.ny_fine, self.nx_fine = z_fine.shape
        self.nx_coarse = nx_coarse
        self.ny_coarse = ny_coarse
        self.Lx = Lx
        self.Ly = Ly

        # 检查整除性
        assert self.ny_fine % ny_coarse == 0, \
            f"ny_fine ({self.ny_fine}) 必须是 ny_coarse ({ny_coarse}) 的整数倍"
        assert self.nx_fine % nx_coarse == 0, \
            f"nx_fine ({self.nx_fine}) 必须是 nx_coarse ({nx_coarse}) 的整数倍"

        self.refine_y = self.ny_fine // ny_coarse
        self.refine_x = self.nx_fine // nx_coarse

        self.dx_coarse = Lx / nx_coarse
        self.dy_coarse = Ly / ny_coarse

        # 粗网格地形（取亚网格均值）
        self.z_coarse = self._coarsen_dem(z_fine)

        # 为每个粗网格单元构建 SubgridCell
        self.cells = np.empty((ny_coarse, nx_coarse), dtype=object)
        for j in range(ny_coarse):
            for i in range(nx_coarse):
                j0 = j * self.refine_y
                j1 = j0 + self.refine_y
                i0 = i * self.refine_x
                i1 = i0 + self.refine_x
                z_sub = z_fine[j0:j1, i0:i1]
                self.cells[j, i] = SubgridCell(
                    z_sub, self.dx_coarse, self.dy_coarse, n_levels
                )

        # 预计算各单元的 eta_min（干床阈值）
        self.eta_min = np.array([
            [self.cells[j, i].eta_min for i in range(nx_coarse)]
            for j in range(ny_coarse)
        ])

    def _coarsen_dem(self, z_fine: np.ndarray) -> np.ndarray:
        """将高分辨率 DEM 粗化为粗网格（取亚网格最低点，保守干湿处理）。"""
        z_coarse = np.zeros((self.ny_coarse, self.nx_coarse))
        for j in range(self.ny_coarse):
            for i in range(self.nx_coarse):
                j0 = j * self.refine_y
                j1 = j0 + self.refine_y
                i0 = i * self.refine_x
                i1 = i0 + self.refine_x
                # 取最低点（保证水量守恒）
                z_coarse[j, i] = np.min(z_fine[j0:j1, i0:i1])
        return z_coarse

    def get_wet_fraction_array(self, eta: np.ndarray) -> np.ndarray:
        """
        向量化查询所有粗网格单元的湿面积比例。

        Args:
            eta : 水面高程数组，形状 (ny_coarse, nx_coarse)

        Returns:
            alpha : 湿面积比例数组，形状 (ny_coarse, nx_coarse)
        """
        alpha = np.zeros_like(eta)
        for j in range(self.ny_coarse):
            for i in range(self.nx_coarse):
                alpha[j, i] = self.cells[j, i].get_wet_fraction(eta[j, i])
        return alpha

    def get_volume_array(self, eta: np.ndarray) -> np.ndarray:
        """
        向量化查询所有粗网格单元的水体积。

        Args:
            eta : 水面高程数组，形状 (ny_coarse, nx_coarse)

        Returns:
            V : 水体积数组 (m³)，形状 (ny_coarse, nx_coarse)
        """
        V = np.zeros_like(eta)
        for j in range(self.ny_coarse):
            for i in range(self.nx_coarse):
                V[j, i] = self.cells[j, i].get_volume(eta[j, i])
        return V

    def get_mean_depth_array(self, eta: np.ndarray) -> np.ndarray:
        """
        向量化查询所有粗网格单元的平均水深。

        Args:
            eta : 水面高程数组，形状 (ny_coarse, nx_coarse)

        Returns:
            h_mean : 平均水深数组 (m)，形状 (ny_coarse, nx_coarse)
        """
        h_mean = np.zeros_like(eta)
        for j in range(self.ny_coarse):
            for i in range(self.nx_coarse):
                h_mean[j, i] = self.cells[j, i].get_mean_depth(eta[j, i])
        return h_mean

    def eta_from_volume_array(self, V: np.ndarray,
                               eta_guess: Optional[np.ndarray] = None) -> np.ndarray:
        """
        向量化从水体积反算水面高程。

        Args:
            V        : 水体积数组 (m³)，形状 (ny_coarse, nx_coarse)
            eta_guess: 初始猜测值数组（可选）

        Returns:
            eta : 水面高程数组 (m)，形状 (ny_coarse, nx_coarse)
        """
        eta = np.zeros_like(V)
        for j in range(self.ny_coarse):
            for i in range(self.nx_coarse):
                guess = float(eta_guess[j, i]) if eta_guess is not None else None
                eta[j, i] = self.cells[j, i].eta_from_volume(V[j, i], guess)
        return eta

    def get_effective_roughness(self, eta: np.ndarray, n_manning: float) -> np.ndarray:
        """
        基于亚网格湿周计算等效 Manning 糙率（考虑部分淹没效应）。

        在部分淹没单元中，有效糙率比完全淹没时更大（因为湿周相对更小）。

        Args:
            eta       : 水面高程数组，形状 (ny_coarse, nx_coarse)
            n_manning : 基础 Manning 糙率系数

        Returns:
            n_eff : 等效 Manning 糙率数组，形状 (ny_coarse, nx_coarse)
        """
        alpha = self.get_wet_fraction_array(eta)
        # 部分淹没时，有效糙率增大（Casulli & Stelling 2011）
        # n_eff = n / alpha^(1/6)（近似）
        n_eff = np.where(alpha > 0.01,
                         n_manning / np.maximum(alpha, 0.01)**(1.0/6.0),
                         n_manning * 10.0)
        return n_eff

    def summary(self) -> dict:
        """返回亚网格地形的统计摘要。"""
        eta_min_all = np.min(self.eta_min)
        eta_max_all = np.max([self.cells[j, i].eta_max
                               for j in range(self.ny_coarse)
                               for i in range(self.nx_coarse)])
        return {
            'coarse_grid': f'{self.nx_coarse}x{self.ny_coarse}',
            'fine_grid': f'{self.nx_fine}x{self.ny_fine}',
            'refinement': f'{self.refine_x}x{self.refine_y}',
            'eta_min': eta_min_all,
            'eta_max': eta_max_all,
            'total_cells': self.nx_coarse * self.ny_coarse,
        }


# ---------------------------------------------------------------------------
# 亚网格感知的 2D 求解器（集成版）
# ---------------------------------------------------------------------------

class SubgridAware2DSolver:
    """
    集成亚网格地形技术的 2D 浅水方程求解器。

    在标准 Godunov 格式的基础上，通过亚网格查找表修正：
    1. 干湿边界的湿面积比例（α 修正）
    2. 水深-体积关系（非线性 V(η) 替代线性 h = V/A）
    3. 等效 Manning 糙率（部分淹没效应）

    这使得粗网格模拟具有细网格的干湿边界精度，
    同时保持粗网格的计算效率。

    Attributes:
        subgrid : SubgridBathymetry 对象
        eta     : 水面高程数组（主要状态变量，替代水深 h）
        hu, hv  : 单位宽度流量（守恒变量）
    """

    def __init__(self, subgrid: SubgridBathymetry,
                 n: float = 0.025, g: float = 9.81,
                 eps_dry: float = 1e-4):
        """
        Args:
            subgrid  : SubgridBathymetry 对象（包含亚网格地形信息）
            n        : Manning 糙率系数
            g        : 重力加速度 (m/s²)
            eps_dry  : 干床阈值 (m)
        """
        self.subgrid = subgrid
        self.n = n
        self.g = g
        self.eps_dry = eps_dry

        nx = subgrid.nx_coarse
        ny = subgrid.ny_coarse
        self.nx = nx
        self.ny = ny
        self.dx = subgrid.dx_coarse
        self.dy = subgrid.dy_coarse

        # 状态变量
        # 使用水面高程 η 作为主要状态变量（比水深 h 更适合亚网格方法）
        self.eta = subgrid.eta_min.copy()  # 初始水面高程 = 干床高程
        self.hu  = np.zeros((ny, nx))      # x 方向单位宽度流量
        self.hv  = np.zeros((ny, nx))      # y 方向单位宽度流量
        self.t   = 0.0

    @property
    def h(self) -> np.ndarray:
        """从水面高程和亚网格地形计算平均水深。"""
        return self.subgrid.get_mean_depth_array(self.eta)

    def set_initial_condition_eta(self, eta: np.ndarray):
        """
        通过水面高程设置初始条件。

        Args:
            eta : 初始水面高程数组，形状 (ny_coarse, nx_coarse)
        """
        self.eta = eta.copy()
        self.hu  = np.zeros((self.ny, self.nx))
        self.hv  = np.zeros((self.ny, self.nx))

    def set_initial_condition_h(self, h: np.ndarray):
        """
        通过水深设置初始条件（自动转换为水面高程）。

        Args:
            h : 初始水深数组，形状 (ny_coarse, nx_coarse)
        """
        # 简单近似：eta = z_coarse + h
        self.eta = self.subgrid.z_coarse + h
        self.hu  = np.zeros((self.ny, self.nx))
        self.hv  = np.zeros((self.ny, self.nx))

    def compute_dt(self, cfl: float = 0.45) -> float:
        """基于 CFL 条件计算最大允许时间步。"""
        h = self.h
        alpha = self.subgrid.get_wet_fraction_array(self.eta)
        wet = h > self.eps_dry

        u = np.where(wet, self.hu / np.maximum(h, self.eps_dry), 0.0)
        v = np.where(wet, self.hv / np.maximum(h, self.eps_dry), 0.0)
        c = np.sqrt(np.maximum(self.g * h, 0.0))

        max_spd_x = float(np.max(np.abs(u) + c)) + 1e-10
        max_spd_y = float(np.max(np.abs(v) + c)) + 1e-10

        dt_x = cfl * self.dx / max_spd_x
        dt_y = cfl * self.dy / max_spd_y
        return min(dt_x, dt_y)

    def step(self, dt: float):
        """
        推进一个时间步（亚网格感知的显式 Euler）。

        关键修正：
        1. 通量计算使用亚网格修正的湿面积比例 α
        2. 水量更新使用 V(η) 关系而非线性 h = V/A
        3. 摩阻使用等效 Manning 糙率

        Args:
            dt : 时间步长 (s)
        """
        g = self.g
        eps = self.eps_dry
        dx, dy = self.dx, self.dy

        # 当前状态
        eta = self.eta
        hu  = self.hu
        hv  = self.hv
        z   = self.subgrid.z_coarse

        # 亚网格修正：湿面积比例
        alpha = self.subgrid.get_wet_fraction_array(eta)

        # 平均水深（用于速度计算和通量）
        h = self.subgrid.get_mean_depth_array(eta)

        # 安全速度
        wet = h > eps
        u = np.where(wet, hu / np.maximum(h, eps), 0.0)
        v = np.where(wet, hv / np.maximum(h, eps), 0.0)

        # ---- 界面水位重构（Audusse + 亚网格修正）--------------------
        # x 方向界面
        eta_iph_L = eta[:, :-1]
        eta_iph_R = eta[:, 1:]
        z_iph = np.maximum(z[:, :-1], z[:, 1:])

        hL_x = np.maximum(eta_iph_L - z_iph, 0.0)
        hR_x = np.maximum(eta_iph_R - z_iph, 0.0)

        # 亚网格修正：界面湿面积比例（取两侧平均）
        alphaL_x = alpha[:, :-1]
        alphaR_x = alpha[:, 1:]
        alpha_iph = 0.5 * (alphaL_x + alphaR_x)

        uL_x = np.where(h[:, :-1] > eps, u[:, :-1], 0.0)
        uR_x = np.where(h[:, 1:]  > eps, u[:, 1:],  0.0)
        vL_x = np.where(h[:, :-1] > eps, v[:, :-1], 0.0)
        vR_x = np.where(h[:, 1:]  > eps, v[:, 1:],  0.0)

        huL_x = hL_x * uL_x
        huR_x = hR_x * uR_x
        hvL_x = hL_x * vL_x
        hvR_x = hR_x * vR_x

        # y 方向界面
        eta_jph_B = eta[:-1, :]
        eta_jph_T = eta[1:, :]
        z_jph = np.maximum(z[:-1, :], z[1:, :])

        hB_y = np.maximum(eta_jph_B - z_jph, 0.0)
        hT_y = np.maximum(eta_jph_T - z_jph, 0.0)

        alphaB_y = alpha[:-1, :]
        alphaT_y = alpha[1:, :]
        alpha_jph = 0.5 * (alphaB_y + alphaT_y)

        uB_y = np.where(h[:-1, :] > eps, u[:-1, :], 0.0)
        uT_y = np.where(h[1:, :]  > eps, u[1:, :],  0.0)
        vB_y = np.where(h[:-1, :] > eps, v[:-1, :], 0.0)
        vT_y = np.where(h[1:, :]  > eps, v[1:, :],  0.0)

        huB_y = hB_y * uB_y
        huT_y = hT_y * uT_y
        hvB_y = hB_y * vB_y
        hvT_y = hT_y * vT_y

        # ---- HLLC 通量（亚网格修正：乘以湿面积比例）-----------------
        Fx_h, Fx_hu, Fx_hv = self._hllc_x(hL_x, huL_x, hvL_x, hR_x, huR_x, hvR_x)
        Gy_h, Gy_hu, Gy_hv = self._hllc_y(hB_y, huB_y, hvB_y, hT_y, huT_y, hvT_y)

        # 亚网格修正：通量乘以界面湿面积比例
        Fx_h  *= alpha_iph
        Fx_hu *= alpha_iph
        Fx_hv *= alpha_iph
        Gy_h  *= alpha_jph
        Gy_hu *= alpha_jph
        Gy_hv *= alpha_jph

        # ---- 通量散度（内部格点）--------------------------------------
        div_h  = (Fx_h[1:-1, 1:]  - Fx_h[1:-1, :-1])  / dx \
               + (Gy_h[1:, 1:-1]  - Gy_h[:-1, 1:-1])  / dy
        div_hu = (Fx_hu[1:-1, 1:] - Fx_hu[1:-1, :-1]) / dx \
               + (Gy_hu[1:, 1:-1] - Gy_hu[:-1, 1:-1]) / dy
        div_hv = (Fx_hv[1:-1, 1:] - Fx_hv[1:-1, :-1]) / dx \
               + (Gy_hv[1:, 1:-1] - Gy_hv[:-1, 1:-1]) / dy

        # ---- 床面坡度源项（亚网格修正）--------------------------------
        Sx = -g * 0.5 * (hL_x + hR_x) * (z[:, 1:] - z[:, :-1]) / dx
        Sy = -g * 0.5 * (hB_y + hT_y) * (z[1:, :] - z[:-1, :]) / dy

        src_hu_int = 0.5 * (Sx[1:-1, :-1] + Sx[1:-1, 1:])
        src_hv_int = 0.5 * (Sy[:-1, 1:-1] + Sy[1:, 1:-1])

        # ---- 水面高程更新（亚网格守恒，dV/deta 线性化）-----------------
        # 使用 dV/deta ≈ A(eta)（湿面积）作为线性化系数
        # 连续性方程：dV/dt = -div(F_h) * dx*dy
        # => A(eta) * deta/dt = -div(F_h) * dx*dy
        # => deta = -dt * div_h * dx*dy / A(eta)
        A_wet = self.subgrid.get_wet_fraction_array(eta) * (dx * dy)
        A_wet = np.maximum(A_wet, 1e-6)  # 防止除零

        # 仅更新内部格点
        eta_new = eta.copy()
        eta_new[1:-1, 1:-1] -= dt * div_h * (dx * dy) / A_wet[1:-1, 1:-1]
        eta_new = np.maximum(eta_new, self.subgrid.eta_min)

        # ---- 动量更新（亚网格修正）------------------------------------
        hu_new = hu.copy()
        hv_new = hv.copy()

        hu_new[1:-1, 1:-1] = hu[1:-1, 1:-1] - dt * div_hu + dt * src_hu_int
        hv_new[1:-1, 1:-1] = hv[1:-1, 1:-1] - dt * div_hv + dt * src_hv_int

        # 边界：零梯度（反射边界）
        eta_new[0, :]  = eta_new[1, :]
        eta_new[-1, :] = eta_new[-2, :]
        eta_new[:, 0]  = eta_new[:, 1]
        eta_new[:, -1] = eta_new[:, -2]

        hu_new[0, :]   = hu_new[1, :]
        hu_new[-1, :]  = hu_new[-2, :]
        hu_new[:, 0]   = np.zeros(self.ny)
        hu_new[:, -1]  = np.zeros(self.ny)
        hv_new[0, :]   = np.zeros(self.nx)
        hv_new[-1, :]  = np.zeros(self.nx)
        hv_new[:, 0]   = hv_new[:, 1]
        hv_new[:, -1]  = hv_new[:, -2]

        # ---- 摩阻源项（等效 Manning 糙率）-----------------------------
        h_new = self.subgrid.get_mean_depth_array(eta_new)
        wet_new = h_new > eps
        u_new = np.where(wet_new, hu_new / np.maximum(h_new, eps), 0.0)
        v_new = np.where(wet_new, hv_new / np.maximum(h_new, eps), 0.0)
        spd   = np.sqrt(u_new**2 + v_new**2)

        # 亚网格等效 Manning 糙率
        n_eff = self.subgrid.get_effective_roughness(eta_new, self.n)
        Cf = np.where(wet_new,
                      g * n_eff**2 / np.maximum(h_new, eps)**(1.0/3.0),
                      0.0)

        denom_fric = 1.0 + Cf * spd * dt
        hu_new = np.where(wet_new, h_new * u_new / denom_fric, 0.0)
        hv_new = np.where(wet_new, h_new * v_new / denom_fric, 0.0)

        self.eta = eta_new
        self.hu  = hu_new
        self.hv  = hv_new
        self.t  += dt

    def _hllc_x(self, hL, huL, hvL, hR, huR, hvR):
        """x 方向 HLLC 通量（与 Hydrostatic2DSolver 相同）。"""
        g = self.g
        eps = self.eps_dry

        with np.errstate(divide='ignore', invalid='ignore'):
            uL = np.where(hL > eps, huL / np.maximum(hL, eps), 0.0)
            uR = np.where(hR > eps, huR / np.maximum(hR, eps), 0.0)
            vL = np.where(hL > eps, hvL / np.maximum(hL, eps), 0.0)
            vR = np.where(hR > eps, hvR / np.maximum(hR, eps), 0.0)

        cL = np.sqrt(g * np.maximum(hL, 0.0))
        cR = np.sqrt(g * np.maximum(hR, 0.0))

        sL = np.minimum(uL - cL, uR - cR)
        sR = np.maximum(uL + cL, uR + cR)

        dry_L = hL <= eps
        dry_R = hR <= eps
        sL = np.where(dry_L & ~dry_R, uR - 2.0 * cR, sL)
        sR = np.where(dry_L & ~dry_R, uR + 2.0 * cR, sR)
        sL = np.where(~dry_L & dry_R, uL - 2.0 * cL, sL)
        sR = np.where(~dry_L & dry_R, uL + 2.0 * cL, sR)

        num   = hR * uR * (sR - uR) - hL * uL * (sL - uL) + 0.5 * g * (hL**2 - hR**2)
        denom = hR * (sR - uR) - hL * (sL - uL)
        safe_denom = np.where(np.abs(denom) > 1e-12, denom, 1.0)
        s_star = np.where(np.abs(denom) > 1e-12, num / safe_denom, 0.5 * (uL + uR))
        s_star = np.clip(s_star, sL, sR)

        FL_h  = huL
        FL_hu = huL * uL + 0.5 * g * hL**2
        FL_hv = huL * vL
        FR_h  = huR
        FR_hu = huR * uR + 0.5 * g * hR**2
        FR_hv = huR * vR

        coeff_L = hL * (sL - uL) / (sL - s_star + 1e-30)
        coeff_R = hR * (sR - uR) / (sR - s_star + 1e-30)

        h_starL  = np.maximum(coeff_L, 0.0)
        hu_starL = h_starL * s_star
        hv_starL = h_starL * vL
        h_starR  = np.maximum(coeff_R, 0.0)
        hu_starR = h_starR * s_star
        hv_starR = h_starR * vR

        F_h  = np.where(sL >= 0, FL_h,
               np.where(s_star >= 0, FL_h  + sL * (h_starL  - hL),
               np.where(sR >= 0,     FR_h  + sR * (h_starR  - hR), FR_h)))
        F_hu = np.where(sL >= 0, FL_hu,
               np.where(s_star >= 0, FL_hu + sL * (hu_starL - huL),
               np.where(sR >= 0,     FR_hu + sR * (hu_starR - huR), FR_hu)))
        F_hv = np.where(sL >= 0, FL_hv,
               np.where(s_star >= 0, FL_hv + sL * (hv_starL - hvL),
               np.where(sR >= 0,     FR_hv + sR * (hv_starR - hvR), FR_hv)))

        both_dry = dry_L & dry_R
        F_h  = np.where(both_dry, 0.0, F_h)
        F_hu = np.where(both_dry, 0.0, F_hu)
        F_hv = np.where(both_dry, 0.0, F_hv)

        return F_h, F_hu, F_hv

    def _hllc_y(self, hB, huB, hvB, hT, huT, hvT):
        """y 方向 HLLC 通量（旋转对称）。"""
        G_h, G_hv, G_hu = self._hllc_x(hB, hvB, huB, hT, hvT, huT)
        return G_h, G_hu, G_hv
