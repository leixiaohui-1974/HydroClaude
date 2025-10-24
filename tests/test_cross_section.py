"""
河道断面模块单元测试

测试覆盖：
- 矩形断面
- 梯形断面
- 复式断面
- 自然河道断面
- IDZ参数计算

作者：HydroClaude Team
日期：2025-10-24
"""

import unittest
import numpy as np
import sys
import os

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from physics.cross_section import (
    RectangularSection,
    TrapezoidalSection,
    CompoundSection,
    NaturalSection,
    compute_idz_parameters_from_section
)


class TestRectangularSection(unittest.TestCase):
    """矩形断面测试"""

    def setUp(self):
        self.section = RectangularSection("TestRect", width=10.0)

    def test_geometry_zero_depth(self):
        """测试零水深"""
        geom = self.section.compute_geometry(0.0)
        self.assertEqual(geom.area, 0.0)
        self.assertEqual(geom.width, 10.0)

    def test_geometry_normal_depth(self):
        """测试正常水深"""
        geom = self.section.compute_geometry(2.0)

        # 面积 = 宽度 × 深度
        self.assertAlmostEqual(geom.area, 20.0, places=5)

        # 湿周 = 宽度 + 2×深度
        self.assertAlmostEqual(geom.perimeter, 14.0, places=5)

        # 水力半径 = 面积/湿周
        expected_R = 20.0 / 14.0
        self.assertAlmostEqual(geom.hydraulic_radius, expected_R, places=5)

        # 水面宽度
        self.assertEqual(geom.width, 10.0)

    def test_area_increases_linearly(self):
        """测试面积随水深线性增长"""
        depths = [0.5, 1.0, 2.0, 3.0]
        areas = [self.section.compute_area(h) for h in depths]

        # 矩形断面：A = b*h
        expected_areas = [d * 10.0 for d in depths]

        for actual, expected in zip(areas, expected_areas):
            self.assertAlmostEqual(actual, expected, places=5)


class TestTrapezoidalSection(unittest.TestCase):
    """梯形断面测试"""

    def setUp(self):
        self.section = TrapezoidalSection("TestTrap", bottom_width=8.0, side_slope=1.5)

    def test_geometry_normal_depth(self):
        """测试正常水深几何参数"""
        h = 2.0
        geom = self.section.compute_geometry(h)

        # 面积 = (b + m*h) * h
        expected_A = (8.0 + 1.5 * 2.0) * 2.0
        self.assertAlmostEqual(geom.area, expected_A, places=5)

        # 湿周 = b + 2*h*sqrt(1 + m²)
        expected_P = 8.0 + 2 * 2.0 * np.sqrt(1 + 1.5**2)
        self.assertAlmostEqual(geom.perimeter, expected_P, places=5)

        # 水面宽度 = b + 2*m*h
        expected_B = 8.0 + 2 * 1.5 * 2.0
        self.assertAlmostEqual(geom.width, expected_B, places=5)

    def test_area_increases_nonlinearly(self):
        """测试面积随水深非线性增长"""
        h1 = 1.0
        h2 = 2.0

        A1 = self.section.compute_area(h1)
        A2 = self.section.compute_area(h2)

        # 梯形面积增长快于线性（因为边坡）
        self.assertGreater(A2, 2 * A1)


class TestCompoundSection(unittest.TestCase):
    """复式断面测试"""

    def setUp(self):
        self.section = CompoundSection(
            "TestCompound",
            main_bottom_width=10.0,
            main_depth=3.0,
            main_side_slope=1.0,
            flood_width_left=20.0,
            flood_width_right=20.0
        )

    def test_main_channel_only(self):
        """测试水深在主槽内"""
        h = 2.0  # 小于主槽深度3.0
        geom = self.section.compute_geometry(h)

        # 应该只有主槽部分
        expected_A = (10.0 + 1.0 * 2.0) * 2.0
        self.assertAlmostEqual(geom.area, expected_A, places=5)

    def test_flood_plain_active(self):
        """测试水深超过主槽（滩地激活）"""
        h = 4.0  # 大于主槽深度3.0
        geom = self.section.compute_geometry(h)

        # 主槽满水
        main_A = (10.0 + 1.0 * 3.0) * 3.0

        # 滩地
        flood_h = 4.0 - 3.0
        flood_A = (20.0 + 20.0) * flood_h

        expected_A = main_A + flood_A
        self.assertAlmostEqual(geom.area, expected_A, places=5)

    def test_width_jump_at_bank(self):
        """测试水面宽度在主槽边缘的跳变"""
        h1 = 2.9  # 主槽内
        h2 = 3.1  # 刚漫滩

        B1 = self.section.compute_width(h1)
        B2 = self.section.compute_width(h2)

        # 漫滩后宽度应该显著增加
        self.assertGreater(B2 - B1, 30.0)  # 左右滩地至少增加40m


class TestNaturalSection(unittest.TestCase):
    """自然河道断面测试"""

    def setUp(self):
        # 简单V型河道
        distances = np.array([0, 5, 10, 15, 20])
        elevations = np.array([5.0, 2.5, 0.0, 2.5, 5.0])
        self.section = NaturalSection("TestNatural", elevations, distances)

    def test_min_elevation(self):
        """测试最低高程识别"""
        self.assertAlmostEqual(self.section.min_elevation, 0.0, places=5)

    def test_zero_depth(self):
        """测试零水深"""
        geom = self.section.compute_geometry(0.0)
        self.assertEqual(geom.area, 0.0)

    def test_symmetric_vee_section(self):
        """测试对称V型断面"""
        h = 2.0
        geom = self.section.compute_geometry(h)

        # V型断面，水深2m时应该覆盖中间部分
        self.assertGreater(geom.area, 0.0)
        self.assertGreater(geom.width, 0.0)
        self.assertGreater(geom.perimeter, 0.0)


class TestIDZParameterComputation(unittest.TestCase):
    """IDZ参数计算测试"""

    def test_rectangular_idz_parameters(self):
        """测试矩形断面IDZ参数计算"""
        section = RectangularSection("Test", width=10.0)

        params_dict = compute_idz_parameters_from_section(
            section=section,
            length=1000.0,
            normal_depth=2.0,
            normal_flow=20.0,
            manning_n=0.025,
            bed_slope=0.0001
        )

        # 检查所有参数存在
        self.assertIn('K', params_dict)
        self.assertIn('tau_z', params_dict)
        self.assertIn('tau_d', params_dict)
        self.assertIn('theta', params_dict)

        # 检查参数合理性
        self.assertGreater(params_dict['K'], 0)
        self.assertGreater(params_dict['tau_z'], 0)
        self.assertGreater(params_dict['tau_d'], 0)
        self.assertGreater(params_dict['theta'], 0)

        # 检查dA/dh计算
        self.assertIn('dA_dh', params_dict)
        self.assertAlmostEqual(params_dict['dA_dh'], 10.0, places=2)  # 矩形：dA/dh = 宽度

    def test_trapezoidal_vs_rectangular(self):
        """测试梯形vs矩形断面IDZ参数差异"""
        rect = RectangularSection("Rect", width=10.0)
        trap = TrapezoidalSection("Trap", bottom_width=8.0, side_slope=1.5)

        params_rect = compute_idz_parameters_from_section(
            rect, 1000.0, 2.0, 20.0, 0.025, 0.0001
        )

        params_trap = compute_idz_parameters_from_section(
            trap, 1000.0, 2.0, 20.0, 0.025, 0.0001
        )

        # 梯形dA/dh应该更大（边坡贡献）
        self.assertGreater(params_trap['dA_dh'], params_rect['dA_dh'])

        # 因此梯形K应该更小
        self.assertLess(params_trap['K'], params_rect['K'])

    def test_parameter_physical_range(self):
        """测试参数在物理合理范围内"""
        section = TrapezoidalSection("Test", bottom_width=10.0, side_slope=1.5)

        params = compute_idz_parameters_from_section(
            section, 5000.0, 2.5, 25.0, 0.025, 0.0001
        )

        # K应该在合理范围（对于5km渠道）
        self.assertGreater(params['K'], 10)
        self.assertLess(params['K'], 10000)

        # 时间常数应该在合理范围
        self.assertGreater(params['tau_d'], 10)
        self.assertLess(params['tau_d'], 100000)

        # 波速应该合理
        self.assertGreater(params['wave_celerity'], 0)
        self.assertLess(params['wave_celerity'], 100)  # m/s

        # 弗劳德数应该亚临界
        self.assertLess(params['froude'], 1.0)


if __name__ == '__main__':
    unittest.main(verbosity=2)
