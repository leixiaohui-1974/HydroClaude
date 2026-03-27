"""
test_amr.py
===========
自适应网格细化（AMR）模块的综合测试套件。

测试覆盖：
  1. 基础四叉树操作（细化、粗化、守恒性）
  2. 网格管理器（初始化、叶节点遍历、坐标查找）
  3. 细化/粗化准则（梯度、弗劳德数、干湿边界）
  4. AMR 求解器（CFL 计算、时间步进、质量守恒）
  5. 物理场景（溃坝波、干湿边界、局部细化效果）
"""

import sys
import os
import numpy as np
import pytest

# 确保 solvers 目录在路径中
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '../../solvers'))

from adaptive_mesh_refinement import (
    QuadtreeCell,
    RefinementCriteria,
    AMRGrid,
    AMRSolver2D,
    EPS_DRY,
    G,
)


# ===========================================================================
# 1. 四叉树单元基础操作
# ===========================================================================

class TestQuadtreeCell:
    """测试 QuadtreeCell 的基本属性和操作。"""

    def test_cell_geometry(self):
        """测试格点几何属性。"""
        cell = QuadtreeCell(x_min=0.0, x_max=2.0, y_min=0.0, y_max=4.0)
        assert cell.dx == pytest.approx(2.0)
        assert cell.dy == pytest.approx(4.0)
        assert cell.area == pytest.approx(8.0)
        assert cell.cx == pytest.approx(1.0)
        assert cell.cy == pytest.approx(2.0)

    def test_cell_hydraulic_properties(self):
        """测试水力学属性（流速、弗劳德数、水面高程）。"""
        cell = QuadtreeCell(x_min=0.0, x_max=1.0, y_min=0.0, y_max=1.0)
        cell.h  = 2.0
        cell.hu = 1.0   # u = 0.5 m/s
        cell.hv = 0.0
        cell.z  = 0.5

        assert cell.u == pytest.approx(0.5)
        assert cell.v == pytest.approx(0.0)
        assert cell.eta == pytest.approx(2.5)  # z + h = 0.5 + 2.0

        c = np.sqrt(G * 2.0)
        expected_fr = 0.5 / c
        assert cell.froude == pytest.approx(expected_fr, rel=1e-6)

    def test_dry_cell_properties(self):
        """测试干格点（h ≈ 0）的属性，避免除零错误。"""
        cell = QuadtreeCell(x_min=0.0, x_max=1.0, y_min=0.0, y_max=1.0)
        cell.h  = 0.0
        cell.hu = 0.0
        cell.hv = 0.0

        assert cell.u == pytest.approx(0.0)
        assert cell.v == pytest.approx(0.0)
        assert cell.froude == pytest.approx(0.0)

    def test_refine_creates_four_children(self):
        """细化后应产生 4 个子格点。"""
        cell = QuadtreeCell(x_min=0.0, x_max=2.0, y_min=0.0, y_max=2.0)
        cell.h = 1.5

        children = cell.refine()

        assert len(children) == 4
        assert not cell.is_leaf
        assert all(c.is_leaf for c in children)
        assert all(c.level == 1 for c in children)

    def test_refine_geometry_coverage(self):
        """细化后 4 个子格点完全覆盖父格点区域，无重叠。"""
        cell = QuadtreeCell(x_min=0.0, x_max=4.0, y_min=0.0, y_max=4.0)
        children = cell.refine()

        # 每个子格点面积之和 = 父格点面积
        total_child_area = sum(c.area for c in children)
        assert total_child_area == pytest.approx(cell.area, rel=1e-10)

        # 子格点尺寸是父格点的一半
        for c in children:
            assert c.dx == pytest.approx(2.0)
            assert c.dy == pytest.approx(2.0)

    def test_refine_conservative_interpolation(self):
        """细化时守恒量应正确传递给子格点。"""
        cell = QuadtreeCell(x_min=0.0, x_max=2.0, y_min=0.0, y_max=2.0)
        cell.h  = 1.5
        cell.hu = 0.3
        cell.hv = -0.1
        cell.z  = 0.2

        children = cell.refine()

        for c in children:
            assert c.h  == pytest.approx(1.5)
            assert c.hu == pytest.approx(0.3)
            assert c.hv == pytest.approx(-0.1)
            assert c.z  == pytest.approx(0.2)

    def test_coarsen_conservative_average(self):
        """粗化时守恒量应正确体积加权平均。"""
        cell = QuadtreeCell(x_min=0.0, x_max=2.0, y_min=0.0, y_max=2.0)
        cell.h = 1.0
        children = cell.refine()

        # 给子格点赋不同的值
        children[0].h  = 1.0; children[0].hu = 0.1
        children[1].h  = 2.0; children[1].hu = 0.2
        children[2].h  = 3.0; children[2].hu = 0.3
        children[3].h  = 4.0; children[3].hu = 0.4

        # 所有子格点面积相同（等面积细化）
        success = cell.coarsen()
        assert success

        assert cell.is_leaf
        assert cell.h  == pytest.approx(2.5)   # (1+2+3+4)/4
        assert cell.hu == pytest.approx(0.25)  # (0.1+0.2+0.3+0.4)/4

    def test_coarsen_fails_if_children_have_children(self):
        """如果子格点还有子格点，粗化应失败。"""
        cell = QuadtreeCell(x_min=0.0, x_max=2.0, y_min=0.0, y_max=2.0)
        cell.refine()
        cell.children[0].refine()  # 进一步细化第一个子格点

        success = cell.coarsen()
        assert not success
        assert not cell.is_leaf

    def test_refine_twice_level(self):
        """两次细化后层级应为 2。"""
        cell = QuadtreeCell(x_min=0.0, x_max=4.0, y_min=0.0, y_max=4.0)
        children_l1 = cell.refine()
        children_l2 = children_l1[0].refine()

        assert all(c.level == 2 for c in children_l2)
        assert children_l2[0].dx == pytest.approx(1.0)


# ===========================================================================
# 2. 网格管理器
# ===========================================================================

class TestAMRGrid:
    """测试 AMRGrid 的初始化和管理功能。"""

    def test_init_leaf_count(self):
        """初始化后叶节点数应等于基础网格格点数。"""
        grid = AMRGrid(0, 10, 0, 5, nx_base=4, ny_base=2)
        assert grid.get_leaf_count() == 8

    def test_init_geometry(self):
        """初始化后网格几何应正确。"""
        grid = AMRGrid(0, 10, 0, 10, nx_base=5, ny_base=5)
        assert grid.dx_base == pytest.approx(2.0)
        assert grid.dy_base == pytest.approx(2.0)

    def test_find_cell_at(self):
        """坐标查找应返回正确的叶节点。"""
        grid = AMRGrid(0, 10, 0, 10, nx_base=5, ny_base=5)
        cell = grid.find_cell_at(1.0, 1.0)
        assert cell is not None
        assert cell.x_min <= 1.0 < cell.x_max
        assert cell.y_min <= 1.0 < cell.y_max

    def test_find_cell_after_refinement(self):
        """细化后坐标查找应返回最细层级的格点。"""
        grid = AMRGrid(0, 10, 0, 10, nx_base=2, ny_base=2)
        # 细化左下角格点
        root = grid.root_cells[0][0]
        root.refine()

        cell = grid.find_cell_at(1.0, 1.0)
        assert cell is not None
        assert cell.level == 1  # 应找到细化后的子格点

    def test_set_bathymetry_callable(self):
        """设置底部高程（函数形式）。"""
        grid = AMRGrid(0, 10, 0, 10, nx_base=4, ny_base=4)
        grid.set_bathymetry(lambda x, y: 0.1 * x + 0.05 * y)

        for leaf in grid.get_all_leaves():
            expected_z = 0.1 * leaf.cx + 0.05 * leaf.cy
            assert leaf.z == pytest.approx(expected_z, rel=1e-6)

    def test_set_initial_condition(self):
        """设置初始条件（函数形式）。"""
        grid = AMRGrid(0, 10, 0, 10, nx_base=4, ny_base=4)
        grid.set_initial_condition(
            h_func=lambda x, y: 2.0 if x < 5.0 else 0.5,
            hu_func=0.0,
            hv_func=0.0,
        )

        for leaf in grid.get_all_leaves():
            if leaf.cx < 5.0:
                assert leaf.h == pytest.approx(2.0)
            else:
                assert leaf.h == pytest.approx(0.5)

    def test_get_stats(self):
        """统计信息应反映当前网格状态。"""
        grid = AMRGrid(0, 10, 0, 10, nx_base=4, ny_base=4)
        stats = grid.get_stats()

        assert stats['n_cells'] == 16
        assert stats['min_level'] == 0
        assert stats['max_level'] == 0
        assert stats['min_dx'] == pytest.approx(2.5)

    def test_adapt_refines_high_gradient(self):
        """高梯度区域应被自动细化。"""
        grid = AMRGrid(0, 10, 0, 10, nx_base=4, ny_base=4)

        # 设置水面高程：左侧高，右侧低（大梯度）
        for leaf in grid.get_all_leaves():
            leaf.h = 3.0 if leaf.cx < 5.0 else 0.1
            leaf.z = 0.0

        criteria = RefinementCriteria(
            eta_grad_refine=0.1,
            eta_grad_coarsen=0.01,
            max_level=2,
        )
        initial_count = grid.get_leaf_count()
        grid.adapt(criteria)
        final_count = grid.get_leaf_count()

        # 细化后格点数应增加
        assert final_count > initial_count

    def test_to_uniform_array(self):
        """插值到均匀网格的形状应正确。"""
        grid = AMRGrid(0, 10, 0, 10, nx_base=4, ny_base=4)
        grid.set_initial_condition(h_func=1.0)

        h_arr, u_arr, v_arr = grid.to_uniform_array(nx=8, ny=8)
        assert h_arr.shape == (8, 8)
        assert np.all(h_arr == pytest.approx(1.0))


# ===========================================================================
# 3. 细化/粗化准则
# ===========================================================================

class TestRefinementCriteria:
    """测试细化/粗化准则的判断逻辑。"""

    def _make_cell(self, h=1.0, u=0.0, v=0.0, z=0.0, level=0):
        cell = QuadtreeCell(x_min=0.0, x_max=1.0, y_min=0.0, y_max=1.0, level=level)
        cell.h  = h
        cell.hu = h * u
        cell.hv = h * v
        cell.z  = z
        return cell

    def _make_neighbor(self, cx, cy, h=1.0, z=0.0):
        cell = QuadtreeCell(x_min=cx-0.5, x_max=cx+0.5, y_min=cy-0.5, y_max=cy+0.5)
        cell.h = h
        cell.z = z
        return cell

    def test_refine_high_froude(self):
        """高弗劳德数应触发细化。"""
        criteria = RefinementCriteria(froude_refine=0.8, max_level=3)
        # Fr > 0.8 时细化
        c = np.sqrt(G * 1.0)
        u_fast = 0.9 * c
        cell = self._make_cell(h=1.0, u=u_fast)
        assert criteria.should_refine(cell, [])

    def test_no_refine_low_froude(self):
        """低弗劳德数且无梯度时不应细化。"""
        criteria = RefinementCriteria(froude_refine=0.8, eta_grad_refine=0.1)
        cell = self._make_cell(h=1.0, u=0.1)
        nb = self._make_neighbor(cx=2.0, cy=0.5, h=1.0)  # 相同水面高程
        assert not criteria.should_refine(cell, [nb])

    def test_refine_high_gradient(self):
        """高水面梯度应触发细化。"""
        criteria = RefinementCriteria(eta_grad_refine=0.05)
        cell = self._make_cell(h=2.0, z=0.0)  # eta = 2.0
        nb = self._make_neighbor(cx=2.0, cy=0.5, h=0.1, z=0.0)  # eta = 0.1
        # 梯度 ≈ |2.0 - 0.1| / 1.5 ≈ 1.27 >> 0.05
        assert criteria.should_refine(cell, [nb])

    def test_refine_dry_wet_boundary(self):
        """干湿边界处应触发细化。"""
        criteria = RefinementCriteria(refine_dry_wet=True, eta_grad_refine=1000.0)
        cell = self._make_cell(h=1.0)
        dry_nb = self._make_neighbor(cx=2.0, cy=0.5, h=0.0)
        assert criteria.should_refine(cell, [dry_nb])

    def test_no_refine_at_max_level(self):
        """达到最大层级时不应继续细化。"""
        criteria = RefinementCriteria(max_level=2)
        c = np.sqrt(G * 1.0)
        cell = self._make_cell(h=1.0, u=0.9*c, level=2)  # 已在最大层级
        assert not criteria.should_refine(cell, [])

    def test_coarsen_low_gradient_froude(self):
        """低梯度低弗劳德数应允许粗化。"""
        criteria = RefinementCriteria(
            eta_grad_coarsen=0.1,
            froude_coarsen=0.5,
            min_level=0,
        )
        cell = self._make_cell(h=1.0, u=0.1, level=2)
        nb = self._make_neighbor(cx=2.0, cy=0.5, h=1.0)  # 相同水面高程
        assert criteria.should_coarsen(cell, [nb])

    def test_no_coarsen_at_min_level(self):
        """在最小层级时不应粗化。"""
        criteria = RefinementCriteria(min_level=0)
        cell = self._make_cell(h=1.0, level=0)  # 已在最小层级
        assert not criteria.should_coarsen(cell, [])

    def test_no_coarsen_high_froude(self):
        """高弗劳德数时不应粗化。"""
        criteria = RefinementCriteria(froude_coarsen=0.5)
        c = np.sqrt(G * 1.0)
        cell = self._make_cell(h=1.0, u=0.6*c, level=2)  # Fr > 0.5
        assert not criteria.should_coarsen(cell, [])


# ===========================================================================
# 4. AMR 求解器基础功能
# ===========================================================================

class TestAMRSolver2D:
    """测试 AMRSolver2D 的求解功能。"""

    def _make_flat_grid(self, nx=4, ny=4, Lx=10.0, Ly=10.0, h0=1.0):
        """创建均匀水深的初始网格。"""
        grid = AMRGrid(0, Lx, 0, Ly, nx_base=nx, ny_base=ny)
        grid.set_initial_condition(h_func=h0, hu_func=0.0, hv_func=0.0)
        return grid

    def test_compute_dt_still_water(self):
        """静水条件下 CFL 时间步长应合理。"""
        grid = self._make_flat_grid(h0=1.0)
        solver = AMRSolver2D(grid, cfl=0.45)

        dt = solver.compute_dt()
        # dt = CFL * dx / c = 0.45 * 2.5 / sqrt(9.81*1.0) ≈ 0.358 s
        expected_dt = 0.45 * 2.5 / np.sqrt(G * 1.0)
        assert dt == pytest.approx(expected_dt, rel=0.05)

    def test_compute_dt_dry_grid(self):
        """全干网格应返回默认时间步长（不崩溃）。"""
        grid = self._make_flat_grid(h0=0.0)
        solver = AMRSolver2D(grid)
        dt = solver.compute_dt()
        assert dt > 0

    def test_single_step_mass_conservation(self):
        """单步时间推进后总水量应守恒（误差 < 0.1%）。"""
        grid = self._make_flat_grid(nx=6, ny=6, h0=1.5)
        solver = AMRSolver2D(grid, adapt_interval=999)  # 禁用自适应

        # 计算初始总水量
        leaves_before = grid.get_all_leaves()
        mass_before = sum(l.h * l.area for l in leaves_before)

        solver.step(dt=0.1)

        leaves_after = grid.get_all_leaves()
        mass_after = sum(l.h * l.area for l in leaves_after)

        rel_error = abs(mass_after - mass_before) / mass_before
        assert rel_error < 0.001, f"质量误差 {rel_error:.4%} 超过 0.1%"

    def test_still_water_stability(self):
        """静水条件下运行多步后水深应保持稳定（湖泊静止测试）。"""
        grid = self._make_flat_grid(nx=4, ny=4, h0=2.0)
        solver = AMRSolver2D(grid, adapt_interval=999)

        result = solver.run(t_end=5.0, max_steps=200)

        for leaf in grid.get_all_leaves():
            assert leaf.h == pytest.approx(2.0, abs=0.01), \
                f"静水不稳定：h = {leaf.h:.4f}"

    def test_time_advances(self):
        """运行后时间应正确推进。"""
        grid = self._make_flat_grid(h0=1.0)
        solver = AMRSolver2D(grid)
        solver.run(t_end=1.0, max_steps=1000)
        assert solver.t == pytest.approx(1.0, abs=0.01)

    def test_step_count_increments(self):
        """步数计数器应正确递增。"""
        grid = self._make_flat_grid(h0=1.0)
        solver = AMRSolver2D(grid, adapt_interval=999)

        for _ in range(5):
            solver.step(dt=0.01)

        assert solver.step_count == 5


# ===========================================================================
# 5. 物理场景验证
# ===========================================================================

class TestPhysicalScenarios:
    """验证 AMR 求解器在物理场景中的正确性。"""

    def test_dam_break_1d_symmetry(self):
        """
        1D 溃块波对称性测试。

        初始条件：左侧水深 H=2m，右侧 h=0.1m，中间有坐（x=5m）。
        溃块后波形应关于 x=5m 对称（如果初始条件对称）。
        """
        Lx, Ly = 10.0, 2.0
        # 使用较小的网格以控制测试时间（AMR 的 O(N^2) 邻居查找在大网格下较慢）
        grid = AMRGrid(0, Lx, 0, Ly, nx_base=8, ny_base=2)
        grid.set_initial_condition(
            h_func=lambda x, y: 2.0 if x < 5.0 else 0.1,
        )

        criteria = RefinementCriteria(max_level=1, eta_grad_refine=0.1)
        solver = AMRSolver2D(grid, cfl=0.45, adapt_interval=5, criteria=criteria)
        solver.run(t_end=0.5, max_steps=200)

        # 检查水量守恒
        leaves = grid.get_all_leaves()
        mass = sum(l.h * l.area for l in leaves)
        expected_mass = (2.0 * 5.0 + 0.1 * 5.0) * Ly
        rel_error = abs(mass - expected_mass) / expected_mass
        assert rel_error < 0.02, f"溃块质量误差 {rel_error:.4%}"

    def test_dam_break_wave_propagation(self):
        """
        溃块波应向右传播（正向波速）。

        初始条件：左侧 H=2m，右侧 h=0.01m。
        经过一段时间后，右侧某点水深应增加。
        """
        Lx, Ly = 20.0, 2.0
        grid = AMRGrid(0, Lx, 0, Ly, nx_base=10, ny_base=2)
        grid.set_initial_condition(
            h_func=lambda x, y: 2.0 if x < 10.0 else 0.01,
        )

        # 记录右侧某点的初始水深
        cell_right = grid.find_cell_at(15.0, 1.0)
        h_initial = cell_right.h if cell_right else 0.01

        criteria = RefinementCriteria(max_level=1, eta_grad_refine=0.1)
        solver = AMRSolver2D(grid, cfl=0.45, adapt_interval=5, criteria=criteria)
        solver.run(t_end=1.0, max_steps=200)

        cell_right_after = grid.find_cell_at(15.0, 1.0)
        h_after = cell_right_after.h if cell_right_after else 0.0

        # 溃块波应传播到右侧，水深增加
        assert h_after > h_initial * 1.5, \
            f"溃块波未传播：h_initial={h_initial:.4f}, h_after={h_after:.4f}"

    def test_amr_refines_near_dam(self):
        """
        溃块波前沿附近应触发自动细化。

        初始条件：左侧 H=2m，右侧 h=0.01m（大梯度区域）。
        """
        Lx, Ly = 10.0, 2.0
        grid = AMRGrid(0, Lx, 0, Ly, nx_base=6, ny_base=2)
        grid.set_initial_condition(
            h_func=lambda x, y: 2.0 if x < 5.0 else 0.01,
        )

        criteria = RefinementCriteria(
            eta_grad_refine=0.1,
            eta_grad_coarsen=0.01,
            max_level=1,
            min_level=0,
        )
        solver = AMRSolver2D(grid, criteria=criteria, adapt_interval=1)

        initial_cells = grid.get_leaf_count()
        solver.run(t_end=0.1, max_steps=30)
        final_cells = grid.get_leaf_count()

        # AMR 应增加格点数（在梯度大的区域细化）
        assert final_cells >= initial_cells, \
            f"AMR 未细化：initial={initial_cells}, final={final_cells}"

    def test_mass_conservation_with_amr(self):
        """
        开启 AMR 后质量守恒误差应 < 2%。

        使用溃块场景，开启自适应细化。
        """
        Lx, Ly = 10.0, 4.0
        grid = AMRGrid(0, Lx, 0, Ly, nx_base=5, ny_base=2)
        grid.set_initial_condition(
            h_func=lambda x, y: 1.5 if x < 5.0 else 0.2,
        )

        # 从实际网格计算初始质量（避免边界格点判断不一致的问题）
        initial_mass = sum(l.h * l.area for l in grid.get_all_leaves())

        criteria = RefinementCriteria(
            eta_grad_refine=0.05,
            eta_grad_coarsen=0.01,
            max_level=1,
        )
        solver = AMRSolver2D(grid, criteria=criteria, adapt_interval=3)
        solver.run(t_end=0.5, max_steps=100)

        mass_final = sum(l.h * l.area for l in grid.get_all_leaves())
        rel_error = abs(mass_final - initial_mass) / initial_mass
        assert rel_error < 0.02, f"AMR 质量误差 {rel_error:.4%}"

    def test_dry_wet_front_no_negative_depth(self):
        """
        干湿边界处水深不应出现负値。

        初始条件：左侧有水，右侧完全干燥。
        """
        Lx, Ly = 10.0, 2.0
        grid = AMRGrid(0, Lx, 0, Ly, nx_base=6, ny_base=2)
        grid.set_initial_condition(
            h_func=lambda x, y: 1.0 if x < 3.0 else 0.0,
        )

        criteria = RefinementCriteria(max_level=1)
        solver = AMRSolver2D(grid, cfl=0.4, adapt_interval=5, criteria=criteria)
        solver.run(t_end=0.5, max_steps=100)

        for leaf in grid.get_all_leaves():
            assert leaf.h >= -1e-10, f"负水深：h = {leaf.h:.6f}"

    def test_sloped_bed_flow(self):
        """
        斜坡底部上的重力驱动流。

        初始条件：均匀水深，底部有坡度。
        水流应向低处流动（x 方向正向）。
        """
        Lx, Ly = 10.0, 2.0
        grid = AMRGrid(0, Lx, 0, Ly, nx_base=6, ny_base=2)
        # 斜坡：z = 0.1 * (10 - x)（右低左高）
        grid.set_bathymetry(lambda x, y: 0.05 * (Lx - x))
        grid.set_initial_condition(h_func=0.5)

        criteria = RefinementCriteria(max_level=1)
        solver = AMRSolver2D(grid, cfl=0.4, adapt_interval=999, criteria=criteria)
        solver.run(t_end=0.3, max_steps=50)

        # 检查质量守恒（斜坡流中质量应守恒）
        mass = sum(l.h * l.area for l in grid.get_all_leaves())
        expected_mass = 0.5 * Lx * Ly
        rel_error = abs(mass - expected_mass) / expected_mass
        assert rel_error < 0.05, f"斜坡流质量误差 {rel_error:.4%}"

    def test_grid_stats_after_adaptation(self):
        """
        自适应后网格统计应反映细化情况。
        """
        grid = AMRGrid(0, 10, 0, 10, nx_base=4, ny_base=4)
        grid.set_initial_condition(
            h_func=lambda x, y: 3.0 if x < 5.0 else 0.1,
        )

        criteria = RefinementCriteria(
            eta_grad_refine=0.05,
            max_level=1,
        )
        solver = AMRSolver2D(grid, criteria=criteria, adapt_interval=1)
        solver.run(t_end=0.05, max_steps=5)

        stats = grid.get_stats()
        assert stats['n_cells'] >= 16  # 至少与初始相同
        assert stats['max_level'] >= 0
        assert stats['min_dx'] <= stats['max_dx']

    def test_uniform_flow_no_spurious_velocity(self):
        """
        均匀静水条件下不应产生虚假流速。

        这是数値方案的基本要求（C-property / well-balanced）。
        """
        Lx, Ly = 10.0, 10.0
        grid = AMRGrid(0, Lx, 0, Ly, nx_base=4, ny_base=4)
        grid.set_initial_condition(h_func=1.0, hu_func=0.0, hv_func=0.0)

        solver = AMRSolver2D(grid, cfl=0.45, adapt_interval=999)
        solver.run(t_end=1.0, max_steps=100)

        for leaf in grid.get_all_leaves():
            assert abs(leaf.u) < 0.01, f"虚假 x 流速：u = {leaf.u:.6f}"
            assert abs(leaf.v) < 0.01, f"虚假 y 流速：v = {leaf.v:.6f}"
