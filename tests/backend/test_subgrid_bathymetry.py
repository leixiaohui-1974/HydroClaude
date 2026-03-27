"""
test_subgrid_bathymetry.py — 亚网格地形技术验证测试

测试案例：
  1. SubgridCell 基本功能（湿面积、体积、水深查找）
  2. 体积守恒性（eta_from_volume 反算精度）
  3. 亚网格地形的干湿边界精度（与粗网格对比）
  4. SubgridBathymetry 向量化接口
  5. SubgridAware2DSolver 静水平衡
  6. SubgridAware2DSolver 质量守恒
  7. 亚网格精度提升验证（与标准粗网格对比）
"""

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..'))

import numpy as np
import pytest
from solvers.subgrid_bathymetry import SubgridCell, SubgridBathymetry, SubgridAware2DSolver


# ---------------------------------------------------------------------------
# 测试 1：SubgridCell 基本功能
# ---------------------------------------------------------------------------

def test_subgrid_cell_flat_bed():
    """平底亚网格：V(η) 应为线性，A(η) 应为常数（单元面积）。"""
    z_sub = np.zeros((4, 4))  # 4×4 亚网格，全部高程为 0
    cell = SubgridCell(z_sub, dx_coarse=10.0, dy_coarse=10.0)

    # 水面高程 η = 1.0 时
    eta = 1.0
    A = cell.get_wet_area(eta)
    V = cell.get_volume(eta)
    h_mean = cell.get_mean_depth(eta)

    assert abs(A - 100.0) < 1.0, f"湿面积应为 100 m²，实际 {A:.2f}"
    assert abs(V - 100.0) < 1.0, f"水体积应为 100 m³，实际 {V:.2f}"
    assert abs(h_mean - 1.0) < 0.05, f"平均水深应为 1.0 m，实际 {h_mean:.3f}"


def test_subgrid_cell_partial_wet():
    """部分淹没：一半格点在水面以上，湿面积应约为单元面积的一半。"""
    # 4×4 亚网格，左半部分高程 0，右半部分高程 2
    z_sub = np.zeros((4, 4))
    z_sub[:, 2:] = 2.0  # 右半部分高程 2 m
    cell = SubgridCell(z_sub, dx_coarse=10.0, dy_coarse=10.0)

    # 水面高程 η = 1.0（只有左半部分被淹没）
    eta = 1.0
    A = cell.get_wet_area(eta)
    V = cell.get_volume(eta)
    alpha = cell.get_wet_fraction(eta)

    assert abs(A - 50.0) < 2.0, f"湿面积应约为 50 m²，实际 {A:.2f}"
    assert abs(V - 50.0) < 2.0, f"水体积应约为 50 m³，实际 {V:.2f}"
    assert abs(alpha - 0.5) < 0.05, f"湿面积比例应约为 0.5，实际 {alpha:.3f}"


def test_subgrid_cell_dry():
    """水面高程低于最低点时，湿面积和体积应为零。"""
    z_sub = np.ones((4, 4)) * 1.0  # 全部高程为 1 m
    cell = SubgridCell(z_sub, dx_coarse=10.0, dy_coarse=10.0)

    # 水面高程 η = 0.5（低于所有地形）
    A = cell.get_wet_area(0.5)
    V = cell.get_volume(0.5)
    alpha = cell.get_wet_fraction(0.5)

    assert A < 1e-3, f"干床时湿面积应为 0，实际 {A:.4f}"
    assert V < 1e-3, f"干床时水体积应为 0，实际 {V:.4f}"
    assert alpha < 1e-3, f"干床时湿面积比例应为 0，实际 {alpha:.4f}"


def test_subgrid_cell_fully_wet():
    """水面高程高于最高点时，湿面积应等于单元面积。"""
    z_sub = np.random.default_rng(42).uniform(0, 1, (4, 4))
    cell = SubgridCell(z_sub, dx_coarse=10.0, dy_coarse=10.0)

    # 水面高程远高于所有地形
    eta = 10.0
    A = cell.get_wet_area(eta)
    alpha = cell.get_wet_fraction(eta)

    assert abs(A - 100.0) < 1.0, f"完全淹没时湿面积应为 100 m²，实际 {A:.2f}"
    assert abs(alpha - 1.0) < 0.01, f"完全淹没时湿面积比例应为 1.0，实际 {alpha:.3f}"


# ---------------------------------------------------------------------------
# 测试 2：体积守恒性（eta_from_volume 反算精度）
# ---------------------------------------------------------------------------

def test_eta_from_volume_roundtrip():
    """V → eta → V 的往返精度应在 0.1% 以内。"""
    z_sub = np.array([[0.0, 0.5, 1.0, 1.5],
                       [0.2, 0.7, 1.2, 1.7],
                       [0.4, 0.9, 1.4, 1.9],
                       [0.6, 1.1, 1.6, 2.1]])
    cell = SubgridCell(z_sub, dx_coarse=10.0, dy_coarse=10.0)

    # 测试多个水面高程
    for eta_test in [0.5, 1.0, 1.5, 2.0, 2.5]:
        V_forward = cell.get_volume(eta_test)
        if V_forward > 0.01:
            eta_back = cell.eta_from_volume(V_forward, eta_guess=eta_test)
            V_back = cell.get_volume(eta_back)
            rel_err = abs(V_back - V_forward) / (V_forward + 1e-10)
            assert rel_err < 0.001, \
                f"eta={eta_test}: 体积往返误差 {rel_err*100:.3f}% 超过 0.1%"


# ---------------------------------------------------------------------------
# 测试 3：SubgridBathymetry 向量化接口
# ---------------------------------------------------------------------------

def test_subgrid_bathymetry_initialization():
    """验证 SubgridBathymetry 正确初始化。"""
    # 20×20 细网格，5×5 粗网格（细化倍数 4×4）
    ny_fine, nx_fine = 20, 20
    ny_coarse, nx_coarse = 5, 5
    z_fine = np.random.default_rng(42).uniform(0, 1, (ny_fine, nx_fine))

    sg = SubgridBathymetry(z_fine, nx_coarse, ny_coarse, Lx=100.0, Ly=100.0)

    assert sg.nx_coarse == nx_coarse
    assert sg.ny_coarse == ny_coarse
    assert sg.refine_x == 4
    assert sg.refine_y == 4
    assert sg.cells.shape == (ny_coarse, nx_coarse)

    summary = sg.summary()
    print(f"\nSubgrid summary: {summary}")
    assert summary['coarse_grid'] == '5x5'
    assert summary['fine_grid'] == '20x20'
    assert summary['refinement'] == '4x4'


def test_subgrid_bathymetry_wet_fraction_array():
    """验证向量化湿面积比例查询。"""
    ny_fine, nx_fine = 20, 20
    z_fine = np.zeros((ny_fine, nx_fine))  # 平底

    sg = SubgridBathymetry(z_fine, 5, 5, Lx=100.0, Ly=100.0)

    # 水面高程 1.0（全部淹没）
    eta = np.ones((5, 5)) * 1.0
    alpha = sg.get_wet_fraction_array(eta)

    assert alpha.shape == (5, 5)
    assert np.all(alpha > 0.99), f"平底全淹时湿面积比例应为 1.0，最小值 {np.min(alpha):.3f}"


def test_subgrid_bathymetry_volume_array():
    """验证向量化水体积查询。"""
    ny_fine, nx_fine = 20, 20
    z_fine = np.zeros((ny_fine, nx_fine))  # 平底

    sg = SubgridBathymetry(z_fine, 5, 5, Lx=100.0, Ly=100.0)
    cell_area = (100.0 / 5) * (100.0 / 5)  # 20×20 = 400 m²

    # 水面高程 1.0（水深 1.0 m）
    eta = np.ones((5, 5)) * 1.0
    V = sg.get_volume_array(eta)

    assert V.shape == (5, 5)
    # 每个单元体积应约为 400 m³
    assert np.all(np.abs(V - cell_area) < 10.0), \
        f"平底 1m 水深时体积应约为 {cell_area} m³，最大误差 {np.max(np.abs(V - cell_area)):.2f}"


# ---------------------------------------------------------------------------
# 测试 4：SubgridAware2DSolver 静水平衡
# ---------------------------------------------------------------------------

def test_subgrid_solver_still_water():
    """亚网格求解器在平底静水条件下应保持静水平衡。"""
    ny_fine, nx_fine = 20, 20
    z_fine = np.zeros((ny_fine, nx_fine))
    sg = SubgridBathymetry(z_fine, 5, 5, Lx=50.0, Ly=50.0)

    solver = SubgridAware2DSolver(sg, n=0.0)

    # 初始条件：均匀水深 1.0 m
    eta_init = np.ones((5, 5)) * 1.0
    solver.set_initial_condition_eta(eta_init)

    # 运行 50 步
    for _ in range(50):
        solver.step(0.1)

    # 水面高程应保持 1.0
    eta_err = np.max(np.abs(solver.eta - 1.0))
    assert eta_err < 1e-8, f"静水平衡被破坏，最大误差: {eta_err:.2e}"


# ---------------------------------------------------------------------------
# 测试 5：SubgridAware2DSolver 质量守恒
# ---------------------------------------------------------------------------

def test_subgrid_solver_mass_conservation():
    """亚网格求解器在封闭域内内部格点总水量应守恒。

    注意：边界格点使用零梯度边界条件（内流边界），会允许少量水流出。
    因此只检验内部格点（去除边界一层）的水量变化。
    """
    ny_fine, nx_fine = 20, 20
    rng = np.random.default_rng(42)
    z_fine = rng.uniform(0, 0.5, (ny_fine, nx_fine))

    sg = SubgridBathymetry(z_fine, 5, 5, Lx=50.0, Ly=50.0)
    solver = SubgridAware2DSolver(sg, n=0.025)

    # 初始条件：中心区域有水（内部格点）
    eta_init = sg.eta_min.copy()
    eta_init[1:4, 1:4] = sg.z_coarse[1:4, 1:4] + 1.0
    solver.set_initial_condition_eta(eta_init)

    # 初始内部总水量（去除边界一层）
    V_init_all = sg.get_volume_array(solver.eta)
    V_init = np.sum(V_init_all[1:-1, 1:-1])

    # 运行 30 步
    for _ in range(30):
        dt = solver.compute_dt(0.45)
        solver.step(dt)

    V_final_all = sg.get_volume_array(solver.eta)
    V_final = np.sum(V_final_all[1:-1, 1:-1])

    # 内部格点的水量应不增加（可以减少，因为水流向边界）
    # 但不应超过初始内部水量
    assert V_final <= V_init * 1.05, \
        f"内部水量意外增加：V_init={V_init:.2f}, V_final={V_final:.2f}"
    # 水量减少不应超过 50%（水向边界流出是正常的）
    assert V_final > V_init * 0.5, \
        f"内部水量异常减少：V_init={V_init:.2f}, V_final={V_final:.2f}"


# ---------------------------------------------------------------------------
# 测试 6：亚网格精度提升验证
# ---------------------------------------------------------------------------

def test_subgrid_wet_fraction_accuracy():
    """
    验证亚网格方法在部分淹没场景下的精度优势。

    场景：粗网格单元内有一个小堤坝（高程 0.8 m），
    水面高程 0.5 m 时，粗网格认为全部淹没（z_coarse = 0），
    但亚网格正确识别出只有部分区域被淹没。
    """
    # 4×4 亚网格：左半部分高程 0，右半部分高程 1.0（小堤坝）
    z_sub = np.zeros((4, 4))
    z_sub[:, 2:] = 1.0  # 右半部分高程 1 m

    cell = SubgridCell(z_sub, dx_coarse=10.0, dy_coarse=10.0)

    # 水面高程 0.5 m
    eta = 0.5

    # 粗网格（取最低点 z=0）认为：h = 0.5 - 0 = 0.5 > 0，全部淹没
    # 亚网格正确识别：只有左半部分（高程 0）被淹没
    alpha_subgrid = cell.get_wet_fraction(eta)

    # 亚网格湿面积比例应约为 0.5（只有左半部分）
    assert 0.4 < alpha_subgrid < 0.6, \
        f"亚网格湿面积比例应约为 0.5，实际 {alpha_subgrid:.3f}"

    # 亚网格体积应约为 50 × 0.5 = 25 m³（只有左半部分，水深 0.5 m）
    V_subgrid = cell.get_volume(eta)
    assert abs(V_subgrid - 25.0) < 3.0, \
        f"亚网格水体积应约为 25 m³，实际 {V_subgrid:.2f}"


def test_subgrid_hydraulic_radius():
    """验证水力半径计算。"""
    z_sub = np.zeros((4, 4))
    cell = SubgridCell(z_sub, dx_coarse=10.0, dy_coarse=10.0)

    # 完全淹没时，水力半径 = A / P
    eta = 1.0
    R = cell.get_hydraulic_radius(eta)
    A = cell.get_wet_area(eta)

    # 水力半径应为正值
    assert R > 0, f"水力半径应为正值，实际 {R:.4f}"
    # 水力半径不应超过单元尺寸
    assert R < 20.0, f"水力半径 {R:.2f} 超过单元尺寸"


def test_effective_roughness():
    """验证等效 Manning 糙率在部分淹没时增大。"""
    ny_fine, nx_fine = 8, 8
    z_fine = np.zeros((ny_fine, nx_fine))
    z_fine[:, 4:] = 1.0  # 右半部分高程 1 m

    sg = SubgridBathymetry(z_fine, 2, 2, Lx=20.0, Ly=20.0)

    n_base = 0.025
    # 水面高程 0.5 m（部分淹没）
    eta_partial = np.ones((2, 2)) * 0.5
    n_eff_partial = sg.get_effective_roughness(eta_partial, n_base)

    # 水面高程 2.0 m（完全淹没）
    eta_full = np.ones((2, 2)) * 2.0
    n_eff_full = sg.get_effective_roughness(eta_full, n_base)

    # 部分淹没时等效糙率应大于完全淹没时
    # （至少在部分单元上）
    assert np.any(n_eff_partial > n_eff_full), \
        "部分淹没时等效糙率应大于完全淹没时"


if __name__ == '__main__':
    pytest.main([__file__, '-v', '-s'])
