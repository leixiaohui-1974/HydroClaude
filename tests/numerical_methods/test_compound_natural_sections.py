"""
复式断面和自然断面测试

验证求解器对以下断面类型的支持：
1. 复式断面 (CompoundSection) - 主槽+滩地
2. 自然河道断面 (NaturalSection) - 基于实测点

测试重点：
- 几何参数计算准确性
- 摩阻计算（分区糙率）
- 质量守恒
- Froude数计算

Phase 2.3 - Task 2.3.4, 2.3.5

作者: HydroClaude Team
日期: 2025-10-29
"""

import pytest
import warnings
warnings.filterwarnings("ignore")
import numpy as np
import sys
import os

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))

try:
    from solvers.godunov_fvm_solver import GodunvFVMSolver
except ImportError as e:
    pytest.skip(f"Required module not available: {e}", allow_module_level=True)

from physics.cross_section import CompoundSection, NaturalSection


@pytest.mark.p2
def test_compound_section_geometry():
    """测试复式断面几何参数计算"""
    # 复式断面：
    # - 主槽：底宽10m, 深度3m, 边坡1.0
    # - 滩地：左右各20m宽
    section = CompoundSection(
        "test_compound",
        main_bottom_width=10.0,
        main_depth=3.0,
        main_side_slope=1.0,
        flood_width_left=20.0,
        flood_width_right=20.0
    )

    # 测试1: 水深在主槽内 (h < 3m)
    h1 = 2.0
    geom1 = section.compute_geometry(h1)

    # 主槽梯形: A = (b + m*h)*h = (10 + 1*2)*2 = 24 m^2
    expected_A1 = (10.0 + 1.0*2.0) * 2.0
    assert abs(geom1.area - expected_A1) < 1e-6

    # 测试2: 水深超过主槽 (h > 3m)
    h2 = 4.0
    geom2 = section.compute_geometry(h2)

    # 主槽满水: A_main = (10 + 1*3)*3 = 39 m^2
    # 滩地: A_flood = (20+20)*(4-3) = 40 m^2
    # 总计: A_total = 39 + 40 = 79 m^2
    A_main = (10.0 + 1.0*3.0) * 3.0
    A_flood = (20.0 + 20.0) * (4.0 - 3.0)
    expected_A2 = A_main + A_flood

    assert abs(geom2.area - expected_A2) < 1e-6

    print(f" 复式断面几何计算准确")
    print(f"   主槽内 (h={h1}m): A={geom1.area:.3f} m^2 (预期:{expected_A1:.3f})")
    print(f"   漫滩 (h={h2}m): A={geom2.area:.3f} m^2 (预期:{expected_A2:.3f})")


@pytest.mark.p2
def test_compound_section_with_solver():
    """测试复式断面与求解器集成"""
    section = CompoundSection(
        "test_compound",
        main_bottom_width=10.0,
        main_depth=3.0,
        main_side_slope=1.0,
        flood_width_left=20.0,
        flood_width_right=20.0,
        roughness_zones={
            'main': 0.025,        # 主槽光滑
            'left_flood': 0.050,  # 滩地粗糙
            'right_flood': 0.050
        }
    )

    with pytest.warns(UserWarning, match="非矩形断面支持"):
        solver = GodunvFVMSolver(
            width=10.0,  # 向后兼容参数
            length=1000.0,
            n_cells=100,
            manning_n=0.025,  # 这个会被复式断面的等效糙率覆盖
            slope=0.001,
            cross_section=section
        )

    # 设置初始条件 - 漫滩情况
    h = 4.0
    solver.h[:] = h
    solver.Q[:] = 50.0

    # 验证质量计算
    mass = solver._compute_total_mass()
    geom = section.compute_geometry(h)
    expected_mass = geom.area * 1000.0

    assert abs(mass - expected_mass) < 1e-3

    # 验证Froude数计算
    Fr = solver.compute_froude_number()
    u = 50.0 / geom.area
    c = np.sqrt(9.81 * geom.hydraulic_depth)
    expected_Fr = u / c

    assert abs(Fr[50] - expected_Fr) < 1e-3

    print(f" 复式断面求解器集成正常")
    print(f"   漫滩深度: h={h}m")
    print(f"   总面积: A={geom.area:.3f} m^2")
    print(f"   Froude数: Fr={Fr[50]:.3f}")


@pytest.mark.p2
def test_compound_section_composite_roughness():
    """测试复式断面的复合糙率计算"""
    section = CompoundSection(
        "test_compound",
        main_bottom_width=10.0,
        main_depth=3.0,
        main_side_slope=1.0,
        flood_width_left=20.0,
        flood_width_right=20.0,
        roughness_zones={
            'main': 0.025,
            'left_flood': 0.060,  # 滩地很粗糙（草地）
            'right_flood': 0.060
        }
    )

    # 漫滩情况
    h = 4.0

    # 计算各分区
    zones = section.compute_zones(h)
    assert len(zones) == 3  # 主槽 + 左滩地 + 右滩地

    # 计算等效糙率
    n_eq = section.compute_composite_manning_n(h, method='hec_ras')

    # 等效糙率应该介于主槽(0.025)和滩地(0.060)之间
    assert 0.025 < n_eq < 0.060

    print(f" 复式断面复合糙率计算正常")
    print(f"   主槽糙率: n=0.025")
    print(f"   滩地糙率: n=0.060")
    print(f"   等效糙率: n_eq={n_eq:.4f}")


@pytest.mark.p2
def test_natural_section_geometry():
    """测试自然河道断面几何参数"""
    # 模拟实测断面数据 (U形河道)
    distances = np.array([0, 5, 10, 15, 20, 25, 30, 35, 40])
    elevations = np.array([5.0, 3.5, 2.0, 1.0, 0.5, 1.2, 2.5, 4.0, 5.5])

    section = NaturalSection("test_natural", elevations, distances)

    # 最低点高程
    assert section.min_elevation == 0.5

    # 测试不同水深
    h1 = 0.5  # 刚没过最低点
    geom1 = section.compute_geometry(h1)
    assert geom1.area > 0.0
    assert geom1.width > 0.0

    h2 = 2.0  # 较深水位
    geom2 = section.compute_geometry(h2)
    assert geom2.area > geom1.area
    assert geom2.width > geom1.width

    # 面积应该随水深单调增加
    h3 = 3.0
    geom3 = section.compute_geometry(h3)
    assert geom3.area > geom2.area

    print(f" 自然断面几何计算正常")
    print(f"   h={h1}m: A={geom1.area:.3f} m^2, B={geom1.width:.3f} m")
    print(f"   h={h2}m: A={geom2.area:.3f} m^2, B={geom2.width:.3f} m")
    print(f"   h={h3}m: A={geom3.area:.3f} m^2, B={geom3.width:.3f} m")


@pytest.mark.p2
def test_natural_section_with_solver():
    """测试自然断面与求解器集成"""
    # 梯形近似的自然河道
    distances = np.array([0, 10, 15, 20, 25, 30, 40])
    elevations = np.array([5.0, 2.0, 1.0, 0.0, 1.0, 2.0, 5.0])

    section = NaturalSection("test_natural", elevations, distances)

    with pytest.warns(UserWarning):
        solver = GodunvFVMSolver(
            width=20.0,  # 近似宽度
            length=1000.0,
            n_cells=100,
            manning_n=0.030,
            slope=0.001,
            cross_section=section
        )

    # 设置初始条件
    h = 2.0
    solver.h[:] = h
    solver.Q[:] = 30.0

    # 验证质量计算
    mass = solver._compute_total_mass()
    geom = section.compute_geometry(h)
    expected_mass = geom.area * 1000.0

    assert abs(mass - expected_mass) < 1e-3

    # 验证Froude数
    Fr = solver.compute_froude_number()
    u = 30.0 / geom.area
    c = np.sqrt(9.81 * geom.hydraulic_depth)
    expected_Fr = u / c

    assert abs(Fr[50] - expected_Fr) < 1e-3

    print(f" 自然断面求解器集成正常")
    print(f"   水深: h={h}m")
    print(f"   面积: A={geom.area:.3f} m^2")
    print(f"   Froude数: Fr={Fr[50]:.3f}")


@pytest.mark.p2
def test_friction_with_compound_section():
    """测试复式断面的摩阻计算"""
    section = CompoundSection(
        "test_compound",
        main_bottom_width=10.0,
        main_depth=3.0,
        main_side_slope=1.0,
        flood_width_left=20.0,
        flood_width_right=20.0
    )

    with pytest.warns(UserWarning):
        solver = GodunvFVMSolver(
            width=10.0,
            length=1000.0,
            n_cells=100,
            manning_n=0.025,
            slope=0.001,
            cross_section=section
        )

    # 测试主槽内摩阻
    h1 = 2.0
    Q1 = 20.0
    S1 = solver._compute_friction_source_term(h1, Q1, 50)

    # 测试漫滩摩阻
    h2 = 4.0
    Q2 = 50.0
    S2 = solver._compute_friction_source_term(h2, Q2, 50)

    # 摩阻应为负（阻力方向）
    assert S1 < 0.0
    assert S2 < 0.0

    # 漫滩时面积更大，相同流速下摩阻可能不同
    print(f" 复式断面摩阻计算正常")
    print(f"   主槽内 (h={h1}m, Q={Q1}): S={S1:.6f}")
    print(f"   漫滩 (h={h2}m, Q={Q2}): S={S2:.6f}")


@pytest.mark.p3
def test_cross_section_performance():
    """测试断面几何计算性能"""
    import time

    # 测试各种断面的计算性能
    sections = {
        '复式': CompoundSection("perf_test", 10, 3, 1, 20, 20),
        '自然': NaturalSection("perf_test",
                              np.array([5, 3, 2, 1, 0.5, 1, 2, 4, 5]),
                              np.array([0, 5, 10, 15, 20, 25, 30, 35, 40]))
    }

    for name, section in sections.items():
        start = time.time()
        for _ in range(10000):
            geom = section.compute_geometry(2.0)
        elapsed = time.time() - start

        print(f"   {name}断面: {elapsed*1000:.2f} ms / 10000次 = {elapsed/10:.2f} μs/次")

    # 10000次计算应该在合理时间内完成 (< 1秒)
    # 这确保求解器中频繁调用不会成为性能瓶颈
    assert elapsed < 1.0


if __name__ == "__main__":
    pytest.main([__file__, "-v", "-s"])
