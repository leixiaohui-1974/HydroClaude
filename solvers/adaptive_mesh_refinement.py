"""
adaptive_mesh_refinement.py
============================
基于四叉树（Quadtree）的自适应网格细化（AMR）模块。

核心功能：
  - QuadtreeCell   : 四叉树单元，支持递归细化和粗化
  - AMRGrid        : 自适应网格管理器，管理整个计算域
  - AMRSolver2D    : 基于 AMR 网格的 2D 浅水方程求解器
  - RefinementCriteria : 细化/粗化判断准则

细化策略（参考 Basilisk / TUFLOW GPU）：
  1. 水面梯度准则：|∇η| > threshold_refine → 细化
  2. 弗劳德数准则：Fr > Fr_threshold → 细化（超临界流区域）
  3. 干湿边界准则：干湿交界处自动细化
  4. 粗化准则：|∇η| < threshold_coarsen 且 Fr < Fr_coarsen → 粗化

守恒插值：
  - 细化时：父格点的守恒量均匀分配给 4 个子格点
  - 粗化时：4 个子格点的守恒量体积加权平均给父格点

参考文献：
  - Popinet, S. (2011). Quadtree-adaptive tsunami modelling.
    Ocean Dynamics, 61(9), 1261-1285.
  - Liang, Q. (2012). A simplified adaptive Cartesian grid system
    for solving the 2D shallow water equations.
    Int. J. Numer. Meth. Fluids, 69(2), 442-458.
"""

from __future__ import annotations

import numpy as np
from dataclasses import dataclass, field
from typing import Optional, List, Tuple, Dict
import warnings


# ---------------------------------------------------------------------------
# 常量
# ---------------------------------------------------------------------------
G = 9.81
EPS_DRY = 1e-4


# ---------------------------------------------------------------------------
# 四叉树单元
# ---------------------------------------------------------------------------

@dataclass
class QuadtreeCell:
    """
    四叉树单元。

    坐标约定：
        x_min, x_max : x 方向范围
        y_min, y_max : y 方向范围

    守恒量（面积平均）：
        h  : 水深 (m)
        hu : x 方向动量 (m²/s)
        hv : y 方向动量 (m²/s)
        z  : 底部高程 (m)，不随时间变化
    """
    x_min: float
    x_max: float
    y_min: float
    y_max: float
    level: int = 0        # 细化层级（0 = 最粗）

    h:  float = 0.0
    hu: float = 0.0
    hv: float = 0.0
    z:  float = 0.0       # 底部高程

    children: Optional[List['QuadtreeCell']] = field(default=None, repr=False)
    parent:   Optional['QuadtreeCell']       = field(default=None, repr=False)

    @property
    def dx(self) -> float:
        return self.x_max - self.x_min

    @property
    def dy(self) -> float:
        return self.y_max - self.y_min

    @property
    def area(self) -> float:
        return self.dx * self.dy

    @property
    def cx(self) -> float:
        return 0.5 * (self.x_min + self.x_max)

    @property
    def cy(self) -> float:
        return 0.5 * (self.y_min + self.y_max)

    @property
    def eta(self) -> float:
        """水面高程 η = z + h"""
        return self.z + self.h

    @property
    def u(self) -> float:
        """x 方向流速"""
        return self.hu / self.h if self.h > EPS_DRY else 0.0

    @property
    def v(self) -> float:
        """y 方向流速"""
        return self.hv / self.h if self.h > EPS_DRY else 0.0

    @property
    def froude(self) -> float:
        """弗劳德数"""
        if self.h <= EPS_DRY:
            return 0.0
        c = np.sqrt(G * self.h)
        return np.sqrt(self.u**2 + self.v**2) / c

    @property
    def is_leaf(self) -> bool:
        """是否为叶节点（无子格点）"""
        return self.children is None

    def refine(self) -> List['QuadtreeCell']:
        """
        将当前格点细化为 4 个子格点（守恒插值）。

        子格点排列（Morton 顺序）：
            [0] SW (x_min, y_min) → (cx, cy)
            [1] SE (cx,   y_min) → (x_max, cy)
            [2] NW (x_min, cy)   → (cx, y_max)
            [3] NE (cx,   cy)    → (x_max, y_max)
        """
        if not self.is_leaf:
            return self.children

        cx, cy = self.cx, self.cy
        coords = [
            (self.x_min, cx,       self.y_min, cy),        # SW
            (cx,         self.x_max, self.y_min, cy),      # SE
            (self.x_min, cx,       cy,           self.y_max),  # NW
            (cx,         self.x_max, cy,         self.y_max),  # NE
        ]

        self.children = []
        for (xlo, xhi, ylo, yhi) in coords:
            child = QuadtreeCell(
                x_min=xlo, x_max=xhi,
                y_min=ylo, y_max=yhi,
                level=self.level + 1,
                h=self.h,    # 守恒插值：子格点继承父格点的守恒量
                hu=self.hu,
                hv=self.hv,
                z=self.z,    # 底部高程也继承（可后续用高分辨率 DEM 覆盖）
                parent=self,
            )
            self.children.append(child)

        return self.children

    def coarsen(self) -> bool:
        """
        将 4 个子格点粗化回父格点（守恒平均）。

        Returns:
            True 如果粗化成功，False 如果子格点还有自己的子格点
        """
        if self.is_leaf:
            return False
        # 检查所有子格点都是叶节点
        if not all(c.is_leaf for c in self.children):
            return False

        # 守恒平均：体积加权
        total_area = sum(c.area for c in self.children)
        self.h  = sum(c.h  * c.area for c in self.children) / total_area
        self.hu = sum(c.hu * c.area for c in self.children) / total_area
        self.hv = sum(c.hv * c.area for c in self.children) / total_area
        # 底部高程取平均
        self.z  = sum(c.z  * c.area for c in self.children) / total_area

        self.children = None
        return True


# ---------------------------------------------------------------------------
# 细化/粗化准则
# ---------------------------------------------------------------------------

@dataclass
class RefinementCriteria:
    """
    自适应细化/粗化准则。

    Attributes:
        eta_grad_refine  : 水面梯度细化阈值 (m/m)
        eta_grad_coarsen : 水面梯度粗化阈值 (m/m)
        froude_refine    : 弗劳德数细化阈值
        froude_coarsen   : 弗劳德数粗化阈值
        refine_dry_wet   : 是否在干湿边界处强制细化
        max_level        : 最大细化层级
        min_level        : 最小细化层级（不允许粗化到此层级以下）
    """
    eta_grad_refine:  float = 0.05
    eta_grad_coarsen: float = 0.01
    froude_refine:    float = 0.8
    froude_coarsen:   float = 0.5
    refine_dry_wet:   bool  = True
    max_level:        int   = 4
    min_level:        int   = 0

    def should_refine(self, cell: QuadtreeCell,
                      neighbors: List[QuadtreeCell]) -> bool:
        """判断格点是否需要细化。"""
        if cell.level >= self.max_level:
            return False

        # 弗劳德数准则
        if cell.froude > self.froude_refine:
            return True

        # 干湿边界准则
        if self.refine_dry_wet and cell.h > EPS_DRY:
            for nb in neighbors:
                if nb.h <= EPS_DRY:
                    return True

        # 水面梯度准则
        if neighbors:
            eta_grad = self._compute_gradient(cell, neighbors)
            if eta_grad > self.eta_grad_refine:
                return True

        return False

    def should_coarsen(self, cell: QuadtreeCell,
                       neighbors: List[QuadtreeCell]) -> bool:
        """判断格点是否可以粗化。"""
        if cell.level <= self.min_level:
            return False

        # 弗劳德数过高时不粗化
        if cell.froude > self.froude_coarsen:
            return False

        # 干湿边界附近不粗化
        if self.refine_dry_wet and cell.h > EPS_DRY:
            for nb in neighbors:
                if nb.h <= EPS_DRY:
                    return False

        # 水面梯度准则
        if neighbors:
            eta_grad = self._compute_gradient(cell, neighbors)
            if eta_grad > self.eta_grad_coarsen:
                return False

        return True

    @staticmethod
    def _compute_gradient(cell: QuadtreeCell,
                          neighbors: List[QuadtreeCell]) -> float:
        """计算格点的水面梯度（中心差分近似）。"""
        if not neighbors:
            return 0.0
        max_grad = 0.0
        for nb in neighbors:
            dist = np.sqrt((cell.cx - nb.cx)**2 + (cell.cy - nb.cy)**2)
            if dist > 0:
                grad = abs(cell.eta - nb.eta) / dist
                max_grad = max(max_grad, grad)
        return max_grad


# ---------------------------------------------------------------------------
# AMR 网格管理器
# ---------------------------------------------------------------------------

class AMRGrid:
    """
    自适应网格管理器。

    管理整个计算域的四叉树网格，提供：
    - 初始化均匀网格
    - 自适应细化/粗化
    - 叶节点遍历
    - 邻居查找
    - 守恒量的提取和设置
    """

    def __init__(self, x_min: float, x_max: float,
                 y_min: float, y_max: float,
                 nx_base: int, ny_base: int):
        """
        Args:
            x_min, x_max : 计算域 x 范围
            y_min, y_max : 计算域 y 范围
            nx_base      : 基础网格 x 方向格点数
            ny_base      : 基础网格 y 方向格点数
        """
        self.x_min = x_min
        self.x_max = x_max
        self.y_min = y_min
        self.y_max = y_max
        self.nx_base = nx_base
        self.ny_base = ny_base

        # 基础网格步长
        self.dx_base = (x_max - x_min) / nx_base
        self.dy_base = (y_max - y_min) / ny_base

        # 初始化基础网格（二维数组，每个元素是一个 QuadtreeCell）
        self.root_cells: List[List[QuadtreeCell]] = []
        self._init_base_grid()

    def _init_base_grid(self):
        """初始化基础均匀网格。"""
        self.root_cells = []
        for j in range(self.ny_base):
            row = []
            for i in range(self.nx_base):
                cell = QuadtreeCell(
                    x_min=self.x_min + i * self.dx_base,
                    x_max=self.x_min + (i+1) * self.dx_base,
                    y_min=self.y_min + j * self.dy_base,
                    y_max=self.y_min + (j+1) * self.dy_base,
                    level=0,
                )
                row.append(cell)
            self.root_cells.append(row)

    def get_all_leaves(self) -> List[QuadtreeCell]:
        """返回所有叶节点（当前活跃格点）。"""
        leaves = []
        def _collect(cell: QuadtreeCell):
            if cell.is_leaf:
                leaves.append(cell)
            else:
                for child in cell.children:
                    _collect(child)

        for row in self.root_cells:
            for cell in row:
                _collect(cell)
        return leaves

    def get_leaf_count(self) -> int:
        """返回当前叶节点总数。"""
        return len(self.get_all_leaves())

    def find_cell_at(self, x: float, y: float) -> Optional[QuadtreeCell]:
        """在网格中查找包含坐标 (x, y) 的叶节点。"""
        # 找到基础网格中的格点
        i = int((x - self.x_min) / self.dx_base)
        j = int((y - self.y_min) / self.dy_base)
        i = max(0, min(i, self.nx_base - 1))
        j = max(0, min(j, self.ny_base - 1))

        def _find(cell: QuadtreeCell) -> Optional[QuadtreeCell]:
            if cell.is_leaf:
                return cell
            for child in cell.children:
                if (child.x_min <= x < child.x_max and
                    child.y_min <= y < child.y_max):
                    return _find(child)
            return None

        return _find(self.root_cells[j][i])

    def set_bathymetry(self, z_func):
        """
        设置底部高程。

        Args:
            z_func : 函数 z_func(x, y) → z，或二维数组
        """
        for leaf in self.get_all_leaves():
            if callable(z_func):
                leaf.z = float(z_func(leaf.cx, leaf.cy))
            else:
                # 如果是数组，使用最近邻插值
                leaf.z = float(z_func)

    def set_initial_condition(self, h_func, hu_func=None, hv_func=None):
        """
        设置初始条件。

        Args:
            h_func  : 函数 h_func(x, y) → h，或常数
            hu_func : 函数 hu_func(x, y) → hu，或常数（默认 0）
            hv_func : 函数 hv_func(x, y) → hv，或常数（默认 0）
        """
        for leaf in self.get_all_leaves():
            x, y = leaf.cx, leaf.cy
            leaf.h  = float(h_func(x, y) if callable(h_func) else h_func)
            leaf.hu = float(hu_func(x, y) if callable(hu_func) else (hu_func or 0.0))
            leaf.hv = float(hv_func(x, y) if callable(hv_func) else (hv_func or 0.0))
            leaf.h  = max(leaf.h, 0.0)

    def adapt(self, criteria: RefinementCriteria):
        """
        执行一次自适应细化/粗化。

        策略：先细化，再粗化（避免刚细化的格点被立即粗化）。
        """
        leaves = self.get_all_leaves()

        # 第一步：细化
        refined = []
        for leaf in leaves:
            neighbors = self._get_neighbors_approx(leaf)
            if criteria.should_refine(leaf, neighbors):
                leaf.refine()
                refined.extend(leaf.children)

        # 第二步：粗化（只对未细化的叶节点的父节点操作）
        # 收集所有非叶节点（有子节点的节点）
        def _try_coarsen(cell: QuadtreeCell):
            if cell.is_leaf:
                return
            # 先递归处理子节点
            for child in cell.children:
                _try_coarsen(child)
            # 如果所有子节点都是叶节点，尝试粗化
            if all(c.is_leaf for c in cell.children):
                # 用子节点的平均状态判断是否粗化
                avg_h = np.mean([c.h for c in cell.children])
                avg_fr = np.mean([c.froude for c in cell.children])
                # 简单判断：梯度小且弗劳德数低则粗化
                eta_vals = [c.eta for c in cell.children]
                eta_range = max(eta_vals) - min(eta_vals)
                char_len = cell.dx
                eta_grad = eta_range / char_len if char_len > 0 else 0.0

                if (eta_grad < criteria.eta_grad_coarsen and
                    avg_fr < criteria.froude_coarsen and
                    cell.level > criteria.min_level):
                    cell.coarsen()

        for row in self.root_cells:
            for cell in row:
                _try_coarsen(cell)

    def _get_neighbors_approx(self, cell: QuadtreeCell,
                               radius: float = None) -> List[QuadtreeCell]:
        """
        近似邻居查找：搜索与格点中心距离在一定范围内的叶节点。

        性能说明：当前实现为 O(N) 复杂度（N = 叶节点总数）。
        对于大规模网格，建议使用空间索引（如 scipy.spatial.KDTree）加速。

        Args:
            cell   : 目标格点
            radius : 搜索半径（默认为格点对角线长度）
        """
        if radius is None:
            radius = np.sqrt(cell.dx**2 + cell.dy**2) * 1.5

        neighbors = []
        for leaf in self.get_all_leaves():
            if leaf is cell:
                continue
            dist = np.sqrt((leaf.cx - cell.cx)**2 + (leaf.cy - cell.cy)**2)
            if dist <= radius:
                neighbors.append(leaf)
        return neighbors

    def _get_face_neighbors(self, cell: QuadtreeCell) -> List[QuadtreeCell]:
        """
        精确面邻居查找：只返回与格点共享面（非顶点）的叶节点。

        通过坐标比较判断是否共享面，避免对角线邻居引入虚假通量。
        时间复杂度 O(N)，但结果比 _get_neighbors_approx 更精确。

        Args:
            cell : 目标格点

        Returns:
            face_neighbors : 共享面的叶节点列表，每个元素包含 (neighbor, direction)
                             direction: 'x_right', 'x_left', 'y_top', 'y_bottom'
        """
        result = []
        tol = 1e-10
        for leaf in self.get_all_leaves():
            if leaf is cell:
                continue
            # 检查是否共享 x 方向的面
            # 共享右面：cell.x_max ≈ leaf.x_min，且 y 范围有重叠
            if abs(cell.x_max - leaf.x_min) < tol:
                y_overlap = min(cell.y_max, leaf.y_max) - max(cell.y_min, leaf.y_min)
                if y_overlap > tol:
                    result.append((leaf, 'x_right'))
            # 共享左面：cell.x_min ≈ leaf.x_max
            elif abs(cell.x_min - leaf.x_max) < tol:
                y_overlap = min(cell.y_max, leaf.y_max) - max(cell.y_min, leaf.y_min)
                if y_overlap > tol:
                    result.append((leaf, 'x_left'))
            # 共享上面：cell.y_max ≈ leaf.y_min
            elif abs(cell.y_max - leaf.y_min) < tol:
                x_overlap = min(cell.x_max, leaf.x_max) - max(cell.x_min, leaf.x_min)
                if x_overlap > tol:
                    result.append((leaf, 'y_top'))
            # 共享下面：cell.y_min ≈ leaf.y_max
            elif abs(cell.y_min - leaf.y_max) < tol:
                x_overlap = min(cell.x_max, leaf.x_max) - max(cell.x_min, leaf.x_min)
                if x_overlap > tol:
                    result.append((leaf, 'y_bottom'))
        return result

    def to_uniform_array(self, nx: int, ny: int) -> Tuple[np.ndarray, np.ndarray, np.ndarray]:
        """
        将 AMR 网格插值到均匀网格（用于可视化和输出）。

        Returns:
            h_arr, u_arr, v_arr : 均匀网格上的水深和流速
        """
        h_arr  = np.zeros((ny, nx))
        hu_arr = np.zeros((ny, nx))
        hv_arr = np.zeros((ny, nx))

        dx = (self.x_max - self.x_min) / nx
        dy = (self.y_max - self.y_min) / ny

        for j in range(ny):
            for i in range(nx):
                x = self.x_min + (i + 0.5) * dx
                y = self.y_min + (j + 0.5) * dy
                cell = self.find_cell_at(x, y)
                if cell is not None:
                    h_arr[j, i]  = cell.h
                    hu_arr[j, i] = cell.hu
                    hv_arr[j, i] = cell.hv

        u_arr = np.where(h_arr > EPS_DRY, hu_arr / h_arr, 0.0)
        v_arr = np.where(h_arr > EPS_DRY, hv_arr / h_arr, 0.0)
        return h_arr, u_arr, v_arr

    def get_stats(self) -> Dict:
        """返回网格统计信息。"""
        leaves = self.get_all_leaves()
        levels = [l.level for l in leaves]
        return {
            'n_cells':   len(leaves),
            'min_level': min(levels) if levels else 0,
            'max_level': max(levels) if levels else 0,
            'avg_level': np.mean(levels) if levels else 0,
            'min_dx':    min(l.dx for l in leaves),
            'max_dx':    max(l.dx for l in leaves),
        }


# ---------------------------------------------------------------------------
# AMR 2D 求解器
# ---------------------------------------------------------------------------

class AMRSolver2D:
    """
    基于 AMR 四叉树网格的 2D 浅水方程求解器。

    采用有限体积法（FVM）+ 一阶 Godunov 格式 + Roe 近似黎曼求解器。
    在每个时间步后执行自适应细化/粗化。

    时间步长控制（CFL 条件）：
        dt = CFL * min(dx / (|u| + c)) over all leaves
    """

    def __init__(self, grid: AMRGrid,
                 criteria: RefinementCriteria = None,
                 cfl: float = 0.45,
                 n_manning: float = 0.025,
                 adapt_interval: int = 5):
        """
        Args:
            grid           : AMR 网格
            criteria       : 细化/粗化准则（默认使用标准准则）
            cfl            : CFL 数
            n_manning      : Manning 糙率系数
            adapt_interval : 每隔多少步执行一次自适应（1 = 每步都自适应）
        """
        self.grid           = grid
        self.criteria       = criteria or RefinementCriteria()
        self.cfl            = cfl
        self.n              = n_manning
        self.adapt_interval = adapt_interval
        self.g              = G
        self.t              = 0.0
        self.step_count     = 0

    def compute_dt(self) -> float:
        """根据 CFL 条件计算最大允许时间步长。"""
        dt_min = np.inf
        for leaf in self.grid.get_all_leaves():
            if leaf.h > EPS_DRY:
                c = np.sqrt(self.g * leaf.h)
                speed = abs(leaf.u) + c
                if speed > 0:
                    dt_cell = self.cfl * min(leaf.dx, leaf.dy) / speed
                    dt_min = min(dt_min, dt_cell)
        return dt_min if dt_min < np.inf else 0.1

    def _hllc_flux_1d(self, hL, huL, hvL, hR, huR, hvR):
        """
        1D HLLC 通量（x 方向）。
        用于计算两个相邻格点界面处的数值通量。
        """
        g = self.g
        dry_L = hL <= EPS_DRY
        dry_R = hR <= EPS_DRY

        if dry_L and dry_R:
            return 0.0, 0.0, 0.0

        uL = huL / hL if not dry_L else 0.0
        uR = huR / hR if not dry_R else 0.0
        vL = hvL / hL if not dry_L else 0.0
        vR = hvR / hR if not dry_R else 0.0
        cL = np.sqrt(g * hL) if not dry_L else 0.0
        cR = np.sqrt(g * hR) if not dry_R else 0.0

        # 波速估计（Einfeldt）
        if dry_L:
            sL = uR - 2.0 * cR
            sR = uR + cR
        elif dry_R:
            sL = uL - cL
            sR = uL + 2.0 * cL
        else:
            sL = min(uL - cL, uR - cR)
            sR = max(uL + cL, uR + cR)

        # 中间波速
        denom = hR * (sR - uR) - hL * (sL - uL)
        if abs(denom) > 1e-12:
            num = hR * uR * (sR - uR) - hL * uL * (sL - uL) + 0.5 * g * (hL**2 - hR**2)
            s_star = num / denom
        else:
            s_star = 0.5 * (uL + uR)
        s_star = np.clip(s_star, sL, sR)

        # 通量计算
        FL_h  = huL
        FL_hu = huL * uL + 0.5 * g * hL**2
        FL_hv = huL * vL
        FR_h  = huR
        FR_hu = huR * uR + 0.5 * g * hR**2
        FR_hv = huR * vR

        if sL >= 0:
            return FL_h, FL_hu, FL_hv
        elif s_star >= 0:
            coeff = hL * (sL - uL) / (sL - s_star + 1e-30)
            h_star  = max(coeff, 0.0)
            hu_star = h_star * s_star
            hv_star = h_star * vL
            return (FL_h  + sL * (h_star  - hL),
                    FL_hu + sL * (hu_star - huL),
                    FL_hv + sL * (hv_star - hvL))
        elif sR >= 0:
            coeff = hR * (sR - uR) / (sR - s_star + 1e-30)
            h_star  = max(coeff, 0.0)
            hu_star = h_star * s_star
            hv_star = h_star * vR
            return (FR_h  + sR * (h_star  - hR),
                    FR_hu + sR * (hu_star - huR),
                    FR_hv + sR * (hv_star - hvR))
        else:
            return FR_h, FR_hu, FR_hv

    def _wall_bc_flux(self, h: float, hu: float, hv: float,
                       direction: str) -> Tuple[float, float, float]:
        """
        计算固壁边界条件（反射 ghost cell）处的 HLLC 通量。

        对于固壁边界，ghost cell 的法向速度取反：
          - x 方向壁面：h_g = h, hu_g = -hu, hv_g = hv
          - y 方向壁面：h_g = h, hu_g = hu,  hv_g = -hv

        Args:
            h, hu, hv : 内部格点守恒量
            direction : 'x_left'  = 左边界（ghost 在左）
                        'x_right' = 右边界（ghost 在右）
                        'y_bottom'= 下边界（ghost 在下）
                        'y_top'   = 上边界（ghost 在上）

        Returns:
            (F_h, F_hu, F_hv) : 界面通量（从内部格点角度，离开为正）
        """
        if direction == 'x_right':
            # 内部格点在左，ghost 在右
            hL, huL, hvL = h,  hu,  hv
            hR, huR, hvR = h, -hu,  hv   # 法向速度取反
            F_h, F_hu, F_hv = self._hllc_flux_1d(hL, huL, hvL, hR, huR, hvR)
            return F_h, F_hu, F_hv
        elif direction == 'x_left':
            # ghost 在左，内部格点在右
            hL, huL, hvL = h, -hu,  hv   # 法向速度取反
            hR, huR, hvR = h,  hu,  hv
            F_h, F_hu, F_hv = self._hllc_flux_1d(hL, huL, hvL, hR, huR, hvR)
            return F_h, F_hu, F_hv
        elif direction == 'y_top':
            # 内部格点在下，ghost 在上（旋转坐标）
            hB, hvB, huB = h,  hv,  hu
            hT, hvT, huT = h, -hv,  hu   # 法向速度取反
            G_h, G_hv, G_hu = self._hllc_flux_1d(hB, hvB, huB, hT, hvT, huT)
            return G_h, G_hu, G_hv
        else:  # y_bottom
            # ghost 在下，内部格点在上（旋转坐标）
            hB, hvB, huB = h, -hv,  hu   # 法向速度取反
            hT, hvT, huT = h,  hv,  hu
            G_h, G_hv, G_hu = self._hllc_flux_1d(hB, hvB, huB, hT, hvT, huT)
            return G_h, G_hu, G_hv

    def step(self, dt: float = None) -> float:
        """
        推进一个时间步。

        Args:
            dt : 时间步长（None 则自动计算）

        Returns:
            dt : 实际使用的时间步长
        """
        if dt is None:
            dt = self.compute_dt()

        leaves = self.grid.get_all_leaves()

        # 计算每个叶节点的通量更新
        dh  = {id(l): 0.0 for l in leaves}
        dhu = {id(l): 0.0 for l in leaves}
        dhv = {id(l): 0.0 for l in leaves}

        # 对每个叶节点，计算与面邻居的界面通量
        # 使用精确面邻居查找（基于坐标共享判断），避免对角线邻居引入虚假通量
        # 每对相邻格点只处理一次（通过 processed_pairs 去重）
        processed_pairs = set()
        for leaf in leaves:
            face_nbs = self.grid._get_face_neighbors(leaf)
            for nb, direction in face_nbs:
                pair_key = (min(id(leaf), id(nb)), max(id(leaf), id(nb)))
                if pair_key in processed_pairs:
                    continue
                processed_pairs.add(pair_key)

                if direction == 'x_right':
                    # leaf 在左，nb 在右
                    hL, huL, hvL = leaf.h, leaf.hu, leaf.hv
                    hR, huR, hvR = nb.h,   nb.hu,   nb.hv
                    F_h, F_hu, F_hv = self._hllc_flux_1d(hL, huL, hvL, hR, huR, hvR)
                    # 界面长度 = 两格点 y 范围的重叠部分
                    face_len = min(leaf.y_max, nb.y_max) - max(leaf.y_min, nb.y_min)
                    dh[id(leaf)]  -= dt * F_h  * face_len / leaf.area
                    dhu[id(leaf)] -= dt * F_hu * face_len / leaf.area
                    dhv[id(leaf)] -= dt * F_hv * face_len / leaf.area
                    dh[id(nb)]    += dt * F_h  * face_len / nb.area
                    dhu[id(nb)]   += dt * F_hu * face_len / nb.area
                    dhv[id(nb)]   += dt * F_hv * face_len / nb.area

                elif direction == 'x_left':
                    # nb 在左，leaf 在右
                    hL, huL, hvL = nb.h,   nb.hu,   nb.hv
                    hR, huR, hvR = leaf.h, leaf.hu, leaf.hv
                    F_h, F_hu, F_hv = self._hllc_flux_1d(hL, huL, hvL, hR, huR, hvR)
                    face_len = min(leaf.y_max, nb.y_max) - max(leaf.y_min, nb.y_min)
                    dh[id(nb)]    -= dt * F_h  * face_len / nb.area
                    dhu[id(nb)]   -= dt * F_hu * face_len / nb.area
                    dhv[id(nb)]   -= dt * F_hv * face_len / nb.area
                    dh[id(leaf)]  += dt * F_h  * face_len / leaf.area
                    dhu[id(leaf)] += dt * F_hu * face_len / leaf.area
                    dhv[id(leaf)] += dt * F_hv * face_len / leaf.area

                elif direction == 'y_top':
                    # leaf 在下，nb 在上（旋转坐标：x→y, y→-x）
                    hB, hvB, huB = leaf.h, leaf.hv, leaf.hu
                    hT, hvT, huT = nb.h,   nb.hv,   nb.hu
                    G_h, G_hv, G_hu = self._hllc_flux_1d(hB, hvB, huB, hT, hvT, huT)
                    face_len = min(leaf.x_max, nb.x_max) - max(leaf.x_min, nb.x_min)
                    dh[id(leaf)]  -= dt * G_h  * face_len / leaf.area
                    dhu[id(leaf)] -= dt * G_hu * face_len / leaf.area
                    dhv[id(leaf)] -= dt * G_hv * face_len / leaf.area
                    dh[id(nb)]    += dt * G_h  * face_len / nb.area
                    dhu[id(nb)]   += dt * G_hu * face_len / nb.area
                    dhv[id(nb)]   += dt * G_hv * face_len / nb.area

                else:  # y_bottom
                    # nb 在下，leaf 在上
                    hB, hvB, huB = nb.h,   nb.hv,   nb.hu
                    hT, hvT, huT = leaf.h, leaf.hv, leaf.hu
                    G_h, G_hv, G_hu = self._hllc_flux_1d(hB, hvB, huB, hT, hvT, huT)
                    face_len = min(leaf.x_max, nb.x_max) - max(leaf.x_min, nb.x_min)
                    dh[id(nb)]    -= dt * G_h  * face_len / nb.area
                    dhu[id(nb)]   -= dt * G_hu * face_len / nb.area
                    dhv[id(nb)]   -= dt * G_hv * face_len / nb.area
                    dh[id(leaf)]  += dt * G_h  * face_len / leaf.area
                    dhu[id(leaf)] += dt * G_hu * face_len / leaf.area
                    dhv[id(leaf)] += dt * G_hv * face_len / leaf.area

        # ---------------------------------------------------------------
        # 固壁边界条件（反射 ghost cell）
        # 对于位于计算域边界的格点，在缺失的边界面上施加固壁 BC。
        # ---------------------------------------------------------------
        tol = 1e-10  # 浮点比较容差
        for leaf in leaves:
            # 左边界（x_min）
            if abs(leaf.x_min - self.grid.x_min) < tol:
                F_h, F_hu, F_hv = self._wall_bc_flux(leaf.h, leaf.hu, leaf.hv, 'x_left')
                face_len = leaf.dy
                # ghost 在左，通量进入格点（符号与右邻居情况相同）
                dh[id(leaf)]  += dt * F_h  * face_len / leaf.area
                dhu[id(leaf)] += dt * F_hu * face_len / leaf.area
                dhv[id(leaf)] += dt * F_hv * face_len / leaf.area

            # 右边界（x_max）
            if abs(leaf.x_max - self.grid.x_max) < tol:
                F_h, F_hu, F_hv = self._wall_bc_flux(leaf.h, leaf.hu, leaf.hv, 'x_right')
                face_len = leaf.dy
                # ghost 在右，通量离开格点（符号与左邻居情况相同）
                dh[id(leaf)]  -= dt * F_h  * face_len / leaf.area
                dhu[id(leaf)] -= dt * F_hu * face_len / leaf.area
                dhv[id(leaf)] -= dt * F_hv * face_len / leaf.area

            # 下边界（y_min）
            if abs(leaf.y_min - self.grid.y_min) < tol:
                F_h, F_hu, F_hv = self._wall_bc_flux(leaf.h, leaf.hu, leaf.hv, 'y_bottom')
                face_len = leaf.dx
                dh[id(leaf)]  += dt * F_h  * face_len / leaf.area
                dhu[id(leaf)] += dt * F_hu * face_len / leaf.area
                dhv[id(leaf)] += dt * F_hv * face_len / leaf.area

            # 上边界（y_max）
            if abs(leaf.y_max - self.grid.y_max) < tol:
                F_h, F_hu, F_hv = self._wall_bc_flux(leaf.h, leaf.hu, leaf.hv, 'y_top')
                face_len = leaf.dx
                dh[id(leaf)]  -= dt * F_h  * face_len / leaf.area
                dhu[id(leaf)] -= dt * F_hu * face_len / leaf.area
                dhv[id(leaf)] -= dt * F_hv * face_len / leaf.area

        # 更新守恒量 + 摩阻源项
        for leaf in leaves:
            leaf.h  = max(leaf.h  + dh[id(leaf)],  0.0)
            leaf.hu = leaf.hu + dhu[id(leaf)]
            leaf.hv = leaf.hv + dhv[id(leaf)]

            # 摩阻（半隐式）
            if leaf.h > EPS_DRY:
                speed = np.sqrt(leaf.u**2 + leaf.v**2)
                if speed > 1e-10:
                    Sf = self.n**2 * speed / (leaf.h**(4.0/3.0))
                    damp = 1.0 / (1.0 + dt * self.g * Sf / speed)
                    leaf.hu *= damp
                    leaf.hv *= damp
            else:
                leaf.hu = 0.0
                leaf.hv = 0.0

        self.t += dt
        self.step_count += 1

        # 自适应细化/粗化
        if self.step_count % self.adapt_interval == 0:
            self.grid.adapt(self.criteria)

        return dt

    def run(self, t_end: float, dt_fixed: float = None,
            max_steps: int = 100000) -> Dict:
        """
        运行模拟到指定时间。

        Args:
            t_end     : 模拟结束时间 (s)
            dt_fixed  : 固定时间步长（None 则自动 CFL）
            max_steps : 最大步数限制

        Returns:
            结果字典 {'t': 最终时间, 'n_steps': 步数, 'grid_stats': 网格统计}
        """
        step = 0
        while self.t < t_end and step < max_steps:
            dt = dt_fixed if dt_fixed is not None else self.compute_dt()
            dt = min(dt, t_end - self.t)
            if dt <= 0:
                break
            self.step(dt)
            step += 1

        return {
            't':          self.t,
            'n_steps':    step,
            'grid_stats': self.grid.get_stats(),
        }
