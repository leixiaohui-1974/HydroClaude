#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
天然不规则断面渠道单元测试

测试 IrregularChannel 类的所有功能：
- 水力几何计算
- 正常水深计算
- 临界水深计算
- 边界情况处理
- 特殊断面形状

作者: HydroClaude Team
日期: 2025-10-29
"""

import pytest
import numpy as np
import sys
from pathlib import Path

# 添加项目路径
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from geometry.irregular_channel import IrregularChannel, create_irregular_channel


class TestIrregularChannelBasics:
    """测试不规则断面基本功能"""

    def test_initialization(self):
        """测试初始化"""
        stations = [0, 5, 10, 15, 20]
        elevations = [5, 2, 0, 2, 5]

        channel = IrregularChannel(
            stations=stations,
            elevations=elevations,
            length=1000.0,
            bottom_slope=0.001,
            manning_n=0.030
        )

        assert len(channel.x) == 5
        assert len(channel.z) == 5
        assert channel.n_points == 5
        assert channel.z_min == 0.0
        assert channel.z_max == 5.0
        assert channel.width_total == 20.0

    def test_invalid_parameters(self):
        """测试非法参数"""
        stations = [0, 5, 10]
        elevations = [3, 0, 3]

        # 桩号和高程数量不一致
        with pytest.raises(ValueError):
            IrregularChannel([0, 5], [3, 0, 3], 1000.0, 0.001, 0.03)

        # 点数太少（<3）
        with pytest.raises(ValueError):
            IrregularChannel([0, 5], [3, 0], 1000.0, 0.001, 0.03)

        # 桩号不是单调递增
        with pytest.raises(ValueError):
            IrregularChannel([0, 10, 5], [3, 0, 3], 1000.0, 0.001, 0.03)

        # 负长度
        with pytest.raises(ValueError):
            IrregularChannel(stations, elevations, -100.0, 0.001, 0.03)

        # 负底坡
        with pytest.raises(ValueError):
            IrregularChannel(stations, elevations, 1000.0, -0.001, 0.03)

        # 零Manning系数
        with pytest.raises(ValueError):
            IrregularChannel(stations, elevations, 1000.0, 0.001, 0.0)

    def test_convenience_function(self):
        """测试便捷创建函数"""
        channel = create_irregular_channel(
            stations=[0, 10, 20],
            elevations=[5, 0, 5],
            length=500.0,
            bottom_slope=0.002,
            manning_n=0.025,
            channel_id="test_channel"
        )

        assert channel.channel_id == "test_channel"
        assert channel.n_points == 3


class TestSymmetricVChannel:
    """测试对称V型断面（验证数值积分）"""

    @pytest.fixture
    def v_channel(self):
        """创建对称V型断面

        形状：
          |\   /|
          | \ / |
          |  V  |

        桩号：[0,  10, 20]
        高程：[5,   0,  5]
        """
        return IrregularChannel(
            stations=[0, 10, 20],
            elevations=[5, 0, 5],
            length=1000.0,
            bottom_slope=0.001,
            manning_n=0.030
        )

    def test_area_v_channel(self, v_channel):
        """测试V型断面面积计算

        V型断面面积解析解：
        A = 0.5 * B * h
        其中 B = 2 * 10 * (h/5) = 4h （两侧斜率相同）
        所以 A = 0.5 * 4h * h = 2h²
        """
        h = 2.0  # 水深2m

        A_calc = v_channel.area(h)

        # 解析解：A = 2h² = 2 * 2² = 8 m²
        A_expected = 2.0 * h**2

        assert np.isclose(A_calc, A_expected, rtol=0.01)
        assert np.isclose(A_calc, 8.0, rtol=0.01)

    def test_top_width_v_channel(self, v_channel):
        """测试V型断面水面宽度

        水面宽度：B = 2 * 10 * (h/5) = 4h
        """
        h = 2.0  # 水深2m

        B_calc = v_channel.top_width(h)

        # 解析解：B = 4h = 4 * 2 = 8 m
        B_expected = 4.0 * h

        assert np.isclose(B_calc, B_expected, rtol=0.01)
        assert np.isclose(B_calc, 8.0, rtol=0.01)

    def test_wetted_perimeter_v_channel(self, v_channel):
        """测试V型断面湿周

        湿周：P = 2 * √(10² + 5²) * (h/5)
             = 2 * √125 * (h/5)
             = 2 * 11.18 * 0.4 = 8.94 m (for h=2m)
        """
        h = 2.0  # 水深2m

        P_calc = v_channel.wetted_perimeter(h)

        # 斜边长度
        slope_length = np.sqrt(10**2 + 5**2)  # √125 ≈ 11.18
        # 水深比例
        ratio = h / 5.0  # 2/5 = 0.4
        # 湿周（两侧斜边）
        P_expected = 2.0 * slope_length * ratio

        assert np.isclose(P_calc, P_expected, rtol=0.01)
        assert np.isclose(P_calc, 8.94, rtol=0.01)


class TestRectangularChannel:
    """测试矩形断面（作为不规则断面的特例）"""

    @pytest.fixture
    def rect_channel(self):
        """创建矩形断面

        形状：
        |    |
        |    |
        |____|

        桩号：[0, 0,  5, 5]
        高程：[3, 0,  0, 3]
        """
        return IrregularChannel(
            stations=[0, 0, 5, 5],
            elevations=[3, 0, 0, 3],
            length=1000.0,
            bottom_slope=0.001,
            manning_n=0.020
        )

    def test_area_rectangle(self, rect_channel):
        """测试矩形断面面积：A = B * h"""
        h = 2.0
        B = 5.0  # 底宽

        A_calc = rect_channel.area(h)
        A_expected = B * h  # 5 * 2 = 10 m²

        assert np.isclose(A_calc, A_expected, rtol=0.01)

    def test_top_width_rectangle(self, rect_channel):
        """测试矩形断面水面宽度（保持不变）"""
        h = 2.0

        B_calc = rect_channel.top_width(h)
        B_expected = 5.0  # 固定底宽

        assert np.isclose(B_calc, B_expected, rtol=0.01)

    def test_wetted_perimeter_rectangle(self, rect_channel):
        """测试矩形断面湿周：P = B + 2h"""
        h = 2.0
        B = 5.0

        P_calc = rect_channel.wetted_perimeter(h)
        P_expected = B + 2 * h  # 5 + 2*2 = 9 m

        assert np.isclose(P_calc, P_expected, rtol=0.01)


class TestComplexChannel:
    """测试复杂形状断面"""

    @pytest.fixture
    def complex_channel(self):
        """创建复杂不对称断面

        形状：不对称，有多个转折点
        """
        return IrregularChannel(
            stations=[0, 5, 10, 15, 20, 30],
            elevations=[8, 4, 1, 0, 2, 6],
            length=1000.0,
            bottom_slope=0.001,
            manning_n=0.032
        )

    def test_properties_method(self, complex_channel):
        """测试properties方法"""
        h = 3.0
        props = complex_channel.properties(h)

        assert 'A' in props
        assert 'B' in props
        assert 'P' in props
        assert 'R' in props
        assert 'D' in props
        assert 'h' in props

        # 验证基本约束
        assert props['A'] > 0
        assert props['B'] > 0
        assert props['P'] > 0
        assert props['R'] > 0
        assert props['D'] > 0
        assert props['h'] == 3.0

    def test_hydraulic_radius(self, complex_channel):
        """测试水力半径计算"""
        h = 2.0

        R = complex_channel.hydraulic_radius(h)
        A = complex_channel.area(h)
        P = complex_channel.wetted_perimeter(h)

        # 验证 R = A / P
        assert np.isclose(R, A / P, rtol=1e-6)

    def test_hydraulic_depth(self, complex_channel):
        """测试水力深度计算"""
        h = 2.0

        D = complex_channel.hydraulic_depth(h)
        A = complex_channel.area(h)
        B = complex_channel.top_width(h)

        # 验证 D = A / B
        assert np.isclose(D, A / B, rtol=1e-6)


class TestNormalDepth:
    """测试正常水深计算"""

    @pytest.fixture
    def test_channel(self):
        """测试用断面"""
        return IrregularChannel(
            stations=[0, 10, 20, 30, 40],
            elevations=[5, 2, 0, 2, 5],
            length=1000.0,
            bottom_slope=0.001,
            manning_n=0.030
        )

    def test_normal_depth_basic(self, test_channel):
        """测试正常水深基本计算"""
        Q = 15.0  # m³/s

        h_n = test_channel.normal_depth(Q)

        # 验证正常水深为正值
        assert h_n > 0

        # 验证 Manning 公式
        props = test_channel.properties(h_n)
        A = props['A']
        R = props['R']
        Q_check = (1.0 / test_channel.n) * A * R**(2.0/3.0) * np.sqrt(test_channel.S0)

        # 应该满足 Manning 公式（相对误差 < 1%）
        assert np.isclose(Q_check, Q, rtol=0.01)

    def test_normal_depth_convergence(self, test_channel):
        """测试不同流量下的收敛性"""
        flow_rates = [5.0, 10.0, 15.0, 20.0]

        for Q in flow_rates:
            h_n = test_channel.normal_depth(Q)

            # 验证正常水深为正值
            assert h_n > 0

            # 验证 Manning 公式
            props = test_channel.properties(h_n)
            A = props['A']
            R = props['R']
            Q_check = (1.0 / test_channel.n) * A * R**(2.0/3.0) * np.sqrt(test_channel.S0)

            assert np.isclose(Q_check, Q, rtol=0.01)

    def test_normal_depth_zero_flow(self, test_channel):
        """测试零流量"""
        h_n = test_channel.normal_depth(0.0)
        assert h_n == 0.0

    def test_normal_depth_zero_slope(self):
        """测试零底坡（应该抛出异常）"""
        channel = IrregularChannel(
            stations=[0, 10, 20],
            elevations=[5, 0, 5],
            length=1000.0,
            bottom_slope=0.0,
            manning_n=0.030
        )

        with pytest.raises(ValueError):
            channel.normal_depth(10.0)


class TestCriticalDepth:
    """测试临界水深计算"""

    @pytest.fixture
    def test_channel(self):
        """测试用断面"""
        return IrregularChannel(
            stations=[0, 10, 20, 30, 40],
            elevations=[5, 2, 0, 2, 5],
            length=1000.0,
            bottom_slope=0.001,
            manning_n=0.030
        )

    def test_critical_depth_basic(self, test_channel):
        """测试临界水深基本计算"""
        Q = 15.0  # m³/s
        g = 9.81

        h_c = test_channel.critical_depth(Q)

        # 验证临界水深为正值
        assert h_c > 0

        # 验证临界流条件：Q² = g * A³ / B
        props = test_channel.properties(h_c)
        A = props['A']
        B = props['B']

        lhs = Q**2
        rhs = g * A**3 / B

        # 应该满足临界流条件（相对误差 < 1%）
        assert np.isclose(lhs, rhs, rtol=0.01)

    def test_critical_depth_froude_one(self, test_channel):
        """测试临界水深对应 Froude 数 ≈ 1"""
        Q = 15.0  # m³/s

        h_c = test_channel.critical_depth(Q)
        Fr = test_channel.froude_number(Q, h_c)

        # Froude 数应该接近 1
        assert np.isclose(Fr, 1.0, atol=0.02)

    def test_critical_depth_convergence(self, test_channel):
        """测试不同流量下的收敛性"""
        flow_rates = [5.0, 10.0, 15.0, 20.0]
        g = 9.81

        for Q in flow_rates:
            h_c = test_channel.critical_depth(Q)

            # 验证临界水深为正值
            assert h_c > 0

            # 验证临界流条件
            props = test_channel.properties(h_c)
            A = props['A']
            B = props['B']
            lhs = Q**2
            rhs = g * A**3 / B

            assert np.isclose(lhs, rhs, rtol=0.01)

    def test_critical_depth_zero_flow(self, test_channel):
        """测试零流量"""
        h_c = test_channel.critical_depth(0.0)
        assert h_c == 0.0


class TestFroudeNumber:
    """测试 Froude 数计算"""

    @pytest.fixture
    def test_channel(self):
        """测试用断面"""
        return IrregularChannel(
            stations=[0, 10, 20, 30, 40],
            elevations=[5, 2, 0, 2, 5],
            length=1000.0,
            bottom_slope=0.001,
            manning_n=0.030
        )

    def test_subcritical_flow(self, test_channel):
        """测试亚临界流（Fr < 1）"""
        Q = 15.0
        h = 4.0  # 较大水深 → 亚临界

        Fr = test_channel.froude_number(Q, h)

        assert Fr < 1.0
        assert Fr > 0.0

    def test_supercritical_flow(self, test_channel):
        """测试超临界流（Fr > 1）"""
        Q = 15.0
        h = 0.5  # 较小水深 → 超临界

        Fr = test_channel.froude_number(Q, h)

        assert Fr > 1.0

    def test_critical_flow(self, test_channel):
        """测试临界流（Fr ≈ 1）"""
        Q = 15.0
        h_c = test_channel.critical_depth(Q)

        Fr = test_channel.froude_number(Q, h_c)

        assert np.isclose(Fr, 1.0, atol=0.02)

    def test_zero_flow(self, test_channel):
        """测试零流量"""
        Fr = test_channel.froude_number(0.0, 2.0)
        assert Fr == 0.0

    def test_zero_depth(self, test_channel):
        """测试零水深"""
        Fr = test_channel.froude_number(15.0, 0.0)
        assert Fr == 0.0


class TestEdgeCases:
    """测试边界情况"""

    def test_zero_depth(self):
        """测试零水深"""
        channel = IrregularChannel(
            stations=[0, 10, 20],
            elevations=[5, 0, 5],
            length=1000.0,
            bottom_slope=0.001,
            manning_n=0.030
        )

        A = channel.area(0.0)
        B = channel.top_width(0.0)
        P = channel.wetted_perimeter(0.0)
        R = channel.hydraulic_radius(0.0)
        D = channel.hydraulic_depth(0.0)

        assert A == 0.0
        assert B == 0.0
        assert P == 0.0
        assert R == 0.0
        assert D == 0.0

    def test_negative_depth(self):
        """测试负水深（应返回0）"""
        channel = IrregularChannel(
            stations=[0, 10, 20],
            elevations=[5, 0, 5],
            length=1000.0,
            bottom_slope=0.001,
            manning_n=0.030
        )

        A = channel.area(-1.0)
        R = channel.hydraulic_radius(-1.0)

        assert A == 0.0
        assert R == 0.0

    def test_very_shallow_flow(self):
        """测试极浅水流"""
        channel = IrregularChannel(
            stations=[0, 10, 20, 30],
            elevations=[5, 1, 0, 5],
            length=1000.0,
            bottom_slope=0.001,
            manning_n=0.030
        )

        h = 0.01  # 1cm水深

        props = channel.properties(h)

        assert props['A'] > 0
        assert props['B'] > 0

    def test_full_depth(self):
        """测试满水深（接近最大深度）"""
        channel = IrregularChannel(
            stations=[0, 10, 20],
            elevations=[5, 0, 5],
            length=1000.0,
            bottom_slope=0.001,
            manning_n=0.030
        )

        h_max = channel.z_max - channel.z_min  # 5m
        h = 0.99 * h_max  # 接近满水深

        props = channel.properties(h)

        assert props['A'] > 0
        assert props['B'] > 0


class TestGetCrossSectionCoordinates:
    """测试断面坐标获取"""

    def test_get_coordinates(self):
        """测试获取断面坐标"""
        stations = [0, 10, 20]
        elevations = [5, 0, 5]

        channel = IrregularChannel(
            stations=stations,
            elevations=elevations,
            length=1000.0,
            bottom_slope=0.001,
            manning_n=0.030
        )

        x, z = channel.get_cross_section_coordinates()

        assert len(x) == 3
        assert len(z) == 3
        np.testing.assert_array_equal(x, stations)
        np.testing.assert_array_equal(z, elevations)


if __name__ == '__main__':
    pytest.main([__file__, '-v', '--tb=short'])
