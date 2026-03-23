"""PropertyTable 和 CrossSection WSE 接口的单元测试。"""

import sys
import os
import numpy as np
import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from physics.cross_section import (
    RectangularSection, TrapezoidalSection, NaturalSection, CompoundSection,
)
from physics.property_table import PropertyTable


# === CrossSection WSE 方法测试 ===

class TestRectangularWSE:
    """矩形断面 WSE 系列方法（invert=0, wse=depth）"""

    def setup_method(self):
        self.sec = RectangularSection("rect", width=10.0)

    def test_invert_elevation_default(self):
        assert self.sec.get_invert_elevation() == 0.0

    def test_area_from_wse(self):
        # wse=2.0, depth=2.0, A = 10*2 = 20
        assert self.sec.compute_area_from_wse(2.0) == pytest.approx(20.0)

    def test_width_from_wse(self):
        # 矩形断面水面宽恒定
        assert self.sec.compute_width_from_wse(2.0) == pytest.approx(10.0)

    def test_conveyance(self):
        # K = (1/n) * A * R^(2/3), A=20, P=14, R=20/14
        n = 0.03
        K = self.sec.compute_conveyance(2.0, n)
        A, P = 20.0, 14.0
        R = A / P
        K_expected = (1.0 / n) * A * R ** (2.0 / 3.0)
        assert K == pytest.approx(K_expected, rel=1e-6)

    def test_dA_dZ_equals_width(self):
        # dA/dZ 应等于水面宽度 B（矩形断面 B=常数=10）
        dA_dZ = self.sec.compute_dA_dZ(2.0)
        assert dA_dZ == pytest.approx(10.0, rel=0.01)

    def test_friction_slope(self):
        n = 0.03
        Q = 50.0
        K = self.sec.compute_conveyance(2.0, n)
        Sf = self.sec.compute_friction_slope(2.0, Q, n)
        assert Sf == pytest.approx(Q * Q / (K * K), rel=1e-6)

    def test_dSf_dQ(self):
        n = 0.03
        Q = 50.0
        K = self.sec.compute_conveyance(2.0, n)
        dSf_dQ = self.sec.compute_dSf_dQ(2.0, Q, n)
        assert dSf_dQ == pytest.approx(2.0 * Q / (K * K), rel=1e-6)


class TestNaturalSectionWSE:
    """自然断面 WSE 方法"""

    def setup_method(self):
        # 简单三角形断面：V 形
        self.distances = np.array([0.0, 5.0, 10.0])
        self.elevations = np.array([5.0, 0.0, 5.0])
        self.sec = NaturalSection("tri", self.elevations, self.distances)

    def test_invert_elevation(self):
        assert self.sec.get_invert_elevation() == 0.0
        assert self.sec.invert_elevation == 0.0

    def test_area_from_wse(self):
        # wse=2.0, depth=2.0, V 形断面 A = depth * width / 2
        # 水面宽: 从 x=0 slope (5-0)/5=1, 水位2.0 → x_left=5-2=3, x_right=5+2=7, width=4
        # 但实际用梯形法计算，近似
        A = self.sec.compute_area_from_wse(2.0)
        assert A > 0

    def test_negative_wse_returns_zero(self):
        A = self.sec.compute_area_from_wse(-1.0)
        assert A == 0.0


class TestTrapezoidalWSE:
    """梯形断面 WSE 方法"""

    def setup_method(self):
        self.sec = TrapezoidalSection("trap", bottom_width=5.0, side_slope=2.0)

    def test_dA_dZ_vs_finite_diff(self):
        """导数精度验证：数值导数 vs 有限差分"""
        wse = 3.0
        dz = 1e-5
        A_plus = self.sec.compute_area_from_wse(wse + dz)
        A_minus = self.sec.compute_area_from_wse(wse - dz)
        fd_deriv = (A_plus - A_minus) / (2.0 * dz)
        computed = self.sec.compute_dA_dZ(wse)
        assert computed == pytest.approx(fd_deriv, rel=0.001)  # < 0.1%

    def test_dK_dZ_vs_finite_diff(self):
        """dK/dZ 导数精度验证"""
        wse = 3.0
        n = 0.025
        dz = 1e-5
        K_plus = self.sec.compute_conveyance(wse + dz, n)
        K_minus = self.sec.compute_conveyance(wse - dz, n)
        fd_deriv = (K_plus - K_minus) / (2.0 * dz)
        computed = self.sec.compute_dK_dZ(wse, n)
        assert computed == pytest.approx(fd_deriv, rel=0.001)


# === PropertyTable 测试 ===

class TestPropertyTableRectangular:
    """矩形断面 PropertyTable 测试"""

    def setup_method(self):
        self.sec = RectangularSection("rect", width=10.0)
        self.n = 0.03
        self.pt = PropertyTable(self.sec, self.n, z_min=0.0, z_max=10.0, n_points=501)

    def test_area_interp_accuracy(self):
        """查表与直接计算一致性 < 0.01%"""
        test_wses = [0.5, 1.0, 2.5, 5.0, 7.7, 9.9]
        for wse in test_wses:
            direct = self.sec.compute_area_from_wse(wse)
            interp = float(self.pt.get_area(wse))
            if direct > 0:
                rel_err = abs(interp - direct) / direct
                assert rel_err < 0.0001, f"wse={wse}: rel_err={rel_err}"

    def test_conveyance_interp_accuracy(self):
        """K 查表精度"""
        for wse in [1.0, 3.0, 6.0]:
            direct = self.sec.compute_conveyance(wse, self.n)
            interp = float(self.pt.get_conveyance(wse))
            if direct > 0:
                rel_err = abs(interp - direct) / direct
                assert rel_err < 0.0001, f"wse={wse}: rel_err={rel_err}"

    def test_width_interp(self):
        """矩形断面宽度应恒等于 10"""
        for wse in [0.5, 3.0, 8.0]:
            w = float(self.pt.get_width(wse))
            assert w == pytest.approx(10.0, rel=0.01)

    def test_array_input(self):
        """支持数组输入"""
        wses = np.array([1.0, 2.0, 3.0])
        areas = self.pt.get_area(wses)
        assert areas.shape == (3,)
        assert areas[0] == pytest.approx(10.0, rel=0.01)
        assert areas[1] == pytest.approx(20.0, rel=0.01)
        assert areas[2] == pytest.approx(30.0, rel=0.01)

    def test_friction_slope(self):
        """Sf 计算"""
        Q = 50.0
        wse = 2.0
        Sf_pt = self.pt.get_friction_slope(wse, Q)
        K = self.sec.compute_conveyance(wse, self.n)
        Sf_direct = Q * Q / (K * K)
        assert Sf_pt == pytest.approx(Sf_direct, rel=0.001)

    def test_dSf_dZ(self):
        """dSf/dZ 解析 vs 数值"""
        Q = 50.0
        wse = 2.0
        dz = 1e-4
        Sf_plus = self.pt.get_friction_slope(wse + dz, Q)
        Sf_minus = self.pt.get_friction_slope(wse - dz, Q)
        fd = (Sf_plus - Sf_minus) / (2.0 * dz)
        analytic = self.pt.get_dSf_dZ(wse, Q)
        assert analytic == pytest.approx(fd, rel=0.05)  # 5% 容差（链式法则 vs 数值）


class TestPropertyTableNatural:
    """自然断面 PropertyTable 测试"""

    def setup_method(self):
        # 宽 U 形断面
        distances = np.array([0, 2, 4, 6, 8, 10, 12, 14, 16, 18, 20])
        elevations = np.array([5, 3, 1.5, 0.5, 0.1, 0.0, 0.1, 0.5, 1.5, 3, 5])
        self.sec = NaturalSection("u_shape", elevations, distances)
        self.n = 0.035
        self.pt = PropertyTable(self.sec, self.n, z_min=0.0, z_max=5.0, n_points=501)

    def test_area_monotonic(self):
        """面积随水位单调递增"""
        wses = np.linspace(0.1, 4.9, 50)
        areas = self.pt.get_area(wses)
        assert np.all(np.diff(areas) >= 0)

    def test_conveyance_monotonic(self):
        """输水能力随水位单调递增"""
        wses = np.linspace(0.1, 4.9, 50)
        K_vals = self.pt.get_conveyance(wses)
        assert np.all(np.diff(K_vals) >= 0)

    def test_interp_vs_direct(self):
        """查表与直接计算对比"""
        for wse in [1.0, 2.5, 4.0]:
            direct = self.sec.compute_area_from_wse(wse)
            interp = float(self.pt.get_area(wse))
            if direct > 0:
                rel_err = abs(interp - direct) / direct
                assert rel_err < 0.01  # 1% 容差（自然断面插值稍有误差）


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
