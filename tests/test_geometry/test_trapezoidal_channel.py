#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
梯形断面渠道单元测试

测试 TrapezoidalChannel 类的所有功能：
- 水力几何计算
- 正常水深计算
- 临界水深计算
- Froude数计算
- 边界情况处理

作者: HydroClaude Team
日期: 2025-10-29
"""

import pytest
import warnings
warnings.filterwarnings("ignore")
import numpy as np
import sys
from pathlib import Path

# 添加项目路径
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from geometry.trapezoidal_channel import TrapezoidalChannel, create_trapezoidal_channel


class TestTrapezoidalChannelBasics:
    """测试梯形断面基本功能"""

    def test_initialization(self):
        """测试初始化"""
        channel = TrapezoidalChannel(
            bottom_width=5.0,
            side_slope=1.5,
            length=1000.0,
            bottom_slope=0.001,
            manning_n=0.020
        )

        assert channel.B_bottom == 5.0
        assert channel.m == 1.5
        assert channel.L == 1000.0
        assert channel.S0 == 0.001
        assert channel.n == 0.020

    def test_invalid_parameters(self):
        """测试非法参数"""
        # 负底宽
        with pytest.raises(ValueError):
            TrapezoidalChannel(-1.0, 1.5, 1000.0, 0.001, 0.02)

        # 负边坡
        with pytest.raises(ValueError):
            TrapezoidalChannel(5.0, -0.5, 1000.0, 0.001, 0.02)

        # 负长度
        with pytest.raises(ValueError):
            TrapezoidalChannel(5.0, 1.5, -100.0, 0.001, 0.02)

        # 负底坡
        with pytest.raises(ValueError):
            TrapezoidalChannel(5.0, 1.5, 1000.0, -0.001, 0.02)

        # 零Manning系数
        with pytest.raises(ValueError):
            TrapezoidalChannel(5.0, 1.5, 1000.0, 0.001, 0.0)

    def test_rectangular_channel(self):
        """测试退化为矩形断面（m=0）"""
        channel = TrapezoidalChannel(
            bottom_width=5.0,
            side_slope=0.0,  # m=0 -> 矩形
            length=1000.0,
            bottom_slope=0.001,
            manning_n=0.020
        )

        h = 2.0

        # 矩形断面公式
        A_expected = 5.0 * 2.0  # B * h
        B_expected = 5.0  # 不变
        P_expected = 5.0 + 2 * 2.0  # B + 2h

        assert np.isclose(channel.area(h), A_expected)
        assert np.isclose(channel.top_width(h), B_expected)
        assert np.isclose(channel.wetted_perimeter(h), P_expected)

    def test_convenience_function(self):
        """测试便捷创建函数"""
        channel = create_trapezoidal_channel(
            bottom_width=3.0,
            side_slope=2.0,
            length=500.0,
            bottom_slope=0.002,
            manning_n=0.025,
            channel_id="test_channel"
        )

        assert channel.channel_id == "test_channel"
        assert channel.B_bottom == 3.0
        assert channel.m == 2.0


class TestHydraulicGeometry:
    """测试水力几何计算"""

    @pytest.fixture
    def standard_channel(self):
        """标准梯形渠道"""
        return TrapezoidalChannel(
            bottom_width=5.0,
            side_slope=1.5,
            length=1000.0,
            bottom_slope=0.001,
            manning_n=0.020
        )

    def test_area(self, standard_channel):
        """测试断面积计算"""
        h = 2.0
        # A = (B + m*h) * h = (5 + 1.5*2) * 2 = 8 * 2 = 16 m^2
        A_expected = (5.0 + 1.5 * 2.0) * 2.0
        A_calc = standard_channel.area(h)

        assert np.isclose(A_calc, A_expected, rtol=1e-6)
        assert np.isclose(A_calc, 16.0, rtol=1e-6)

    def test_top_width(self, standard_channel):
        """测试水面宽度计算"""
        h = 2.0
        # B = B_bottom + 2*m*h = 5 + 2*1.5*2 = 5 + 6 = 11 m
        B_expected = 5.0 + 2.0 * 1.5 * 2.0
        B_calc = standard_channel.top_width(h)

        assert np.isclose(B_calc, B_expected, rtol=1e-6)
        assert np.isclose(B_calc, 11.0, rtol=1e-6)

    def test_wetted_perimeter(self, standard_channel):
        """测试湿周计算"""
        h = 2.0
        # P = B_bottom + 2*h*√(1+m^2) = 5 + 2*2*√(1+1.5^2)
        # √(1+2.25) = √3.25 ~= 1.8028
        # P = 5 + 4*1.8028 = 5 + 7.2111 = 12.2111 m
        slope_factor = np.sqrt(1.0 + 1.5**2)
        P_expected = 5.0 + 2.0 * 2.0 * slope_factor
        P_calc = standard_channel.wetted_perimeter(h)

        assert np.isclose(P_calc, P_expected, rtol=1e-6)
        assert np.isclose(P_calc, 12.2111, rtol=1e-3)

    def test_hydraulic_radius(self, standard_channel):
        """测试水力半径计算"""
        h = 2.0
        A = standard_channel.area(h)  # 16 m^2
        P = standard_channel.wetted_perimeter(h)  # 12.2111 m
        R_expected = A / P  # 16 / 12.2111 ~= 1.3102 m

        R_calc = standard_channel.hydraulic_radius(h)

        assert np.isclose(R_calc, R_expected, rtol=1e-6)
        assert np.isclose(R_calc, 1.3102, rtol=1e-3)

    def test_hydraulic_depth(self, standard_channel):
        """测试水力深度计算"""
        h = 2.0
        A = standard_channel.area(h)  # 16 m^2
        B = standard_channel.top_width(h)  # 11 m
        D_expected = A / B  # 16 / 11 ~= 1.4545 m

        D_calc = standard_channel.hydraulic_depth(h)

        assert np.isclose(D_calc, D_expected, rtol=1e-6)
        assert np.isclose(D_calc, 1.4545, rtol=1e-3)

    def test_properties_method(self, standard_channel):
        """测试properties方法（一次性计算所有要素）"""
        h = 2.0
        props = standard_channel.properties(h)

        assert 'A' in props
        assert 'B' in props
        assert 'P' in props
        assert 'R' in props
        assert 'D' in props
        assert 'h' in props

        # 验证值的一致性
        assert np.isclose(props['A'], 16.0, rtol=1e-3)
        assert np.isclose(props['B'], 11.0, rtol=1e-3)
        assert np.isclose(props['P'], 12.2111, rtol=1e-3)
        assert np.isclose(props['R'], 1.3102, rtol=1e-3)
        assert np.isclose(props['D'], 1.4545, rtol=1e-3)
        assert props['h'] == 2.0

    def test_zero_depth(self, standard_channel):
        """测试零水深情况"""
        A = standard_channel.area(0.0)
        B = standard_channel.top_width(0.0)
        P = standard_channel.wetted_perimeter(0.0)
        R = standard_channel.hydraulic_radius(0.0)
        D = standard_channel.hydraulic_depth(0.0)

        assert A == 0.0
        assert B == standard_channel.B_bottom  # 底宽
        assert P == standard_channel.B_bottom  # 底宽
        assert R == 0.0
        assert D == 0.0

    def test_negative_depth(self, standard_channel):
        """测试负水深（应返回0或底宽）"""
        A = standard_channel.area(-1.0)
        R = standard_channel.hydraulic_radius(-1.0)

        assert A == 0.0
        assert R == 0.0


class TestNormalDepth:
    """测试正常水深计算"""

    @pytest.fixture
    def test_channel(self):
        """测试用梯形渠道"""
        return TrapezoidalChannel(
            bottom_width=5.0,
            side_slope=1.5,
            length=1000.0,
            bottom_slope=0.001,
            manning_n=0.020
        )

    def test_normal_depth_basic(self, test_channel):
        """测试正常水深基本计算"""
        Q = 10.0  # m^3/s

        h_n = test_channel.normal_depth(Q)

        # 验证 Manning 公式
        props = test_channel.properties(h_n)
        A = props['A']
        R = props['R']

        Q_check = (1.0 / test_channel.n) * A * R**(2.0/3.0) * np.sqrt(test_channel.S0)

        # 应该满足 Manning 公式（相对误差 < 1%）
        assert np.isclose(Q_check, Q, rtol=0.01)

    def test_normal_depth_convergence(self, test_channel):
        """测试不同流量下的收敛性"""
        flow_rates = [1.0, 5.0, 10.0, 20.0, 50.0]

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
        channel = TrapezoidalChannel(5.0, 1.5, 1000.0, 0.0, 0.020)

        with pytest.raises(ValueError):
            channel.normal_depth(10.0)


class TestCriticalDepth:
    """测试临界水深计算"""

    @pytest.fixture
    def test_channel(self):
        """测试用梯形渠道"""
        return TrapezoidalChannel(
            bottom_width=5.0,
            side_slope=1.5,
            length=1000.0,
            bottom_slope=0.001,
            manning_n=0.020
        )

    def test_critical_depth_basic(self, test_channel):
        """测试临界水深基本计算"""
        Q = 10.0  # m^3/s
        g = 9.81

        h_c = test_channel.critical_depth(Q)

        # 验证临界流条件：Q^2 = g * A^3 / B
        props = test_channel.properties(h_c)
        A = props['A']
        B = props['B']

        lhs = Q**2
        rhs = g * A**3 / B

        # 应该满足临界流条件（相对误差 < 1%）
        assert np.isclose(lhs, rhs, rtol=0.01)

    def test_critical_depth_froude_one(self, test_channel):
        """测试临界水深对应 Froude 数 = 1"""
        Q = 10.0  # m^3/s

        h_c = test_channel.critical_depth(Q)
        Fr = test_channel.froude_number(Q, h_c)

        # Froude 数应该接近 1
        assert np.isclose(Fr, 1.0, atol=0.01)

    def test_critical_depth_convergence(self, test_channel):
        """测试不同流量下的收敛性"""
        flow_rates = [1.0, 5.0, 10.0, 20.0, 50.0]
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
        """测试用梯形渠道"""
        return TrapezoidalChannel(
            bottom_width=5.0,
            side_slope=1.5,
            length=1000.0,
            bottom_slope=0.001,
            manning_n=0.020
        )

    def test_subcritical_flow(self, test_channel):
        """测试亚临界流（Fr < 1）"""
        Q = 10.0
        h = 3.0  # 较大水深 -> 亚临界

        Fr = test_channel.froude_number(Q, h)

        assert Fr < 1.0
        assert Fr > 0.0

    def test_supercritical_flow(self, test_channel):
        """测试超临界流（Fr > 1）"""
        Q = 10.0
        h = 0.5  # 较小水深 -> 超临界

        Fr = test_channel.froude_number(Q, h)

        assert Fr > 1.0

    def test_critical_flow(self, test_channel):
        """测试临界流（Fr ~= 1）"""
        Q = 10.0
        h_c = test_channel.critical_depth(Q)

        Fr = test_channel.froude_number(Q, h_c)

        assert np.isclose(Fr, 1.0, atol=0.01)

    def test_zero_flow(self, test_channel):
        """测试零流量"""
        Fr = test_channel.froude_number(0.0, 2.0)
        assert Fr == 0.0

    def test_zero_depth(self, test_channel):
        """测试零水深"""
        Fr = test_channel.froude_number(10.0, 0.0)
        assert Fr == 0.0


class TestComparisons:
    """测试正常水深vs临界水深关系"""

    @pytest.fixture
    def test_channel(self):
        """测试用梯形渠道"""
        return TrapezoidalChannel(
            bottom_width=5.0,
            side_slope=1.5,
            length=1000.0,
            bottom_slope=0.001,  # 缓坡
            manning_n=0.020
        )

    def test_normal_vs_critical_mild_slope(self, test_channel):
        """测试缓坡渠道（S < S_critical）：h_n > h_c"""
        Q = 10.0

        h_n = test_channel.normal_depth(Q)
        h_c = test_channel.critical_depth(Q)

        # 缓坡：正常水深 > 临界水深
        assert h_n > h_c

    def test_normal_vs_critical_steep_slope(self):
        """测试陡坡渠道（S > S_critical）：h_n < h_c"""
        # 陡坡渠道
        steep_channel = TrapezoidalChannel(
            bottom_width=5.0,
            side_slope=1.5,
            length=1000.0,
            bottom_slope=0.01,  # 陡坡
            manning_n=0.020
        )

        Q = 10.0

        h_n = steep_channel.normal_depth(Q)
        h_c = steep_channel.critical_depth(Q)

        # 陡坡：正常水深 < 临界水深
        assert h_n < h_c


class TestEdgeCases:
    """测试边界情况"""

    def test_very_small_flow(self):
        """测试极小流量"""
        channel = TrapezoidalChannel(5.0, 1.5, 1000.0, 0.001, 0.020)
        Q = 0.001  # 1 L/s

        h_n = channel.normal_depth(Q)
        h_c = channel.critical_depth(Q)

        assert h_n > 0
        assert h_c > 0
        assert h_n > h_c  # 缓坡

    def test_very_large_flow(self):
        """测试极大流量"""
        channel = TrapezoidalChannel(5.0, 1.5, 1000.0, 0.001, 0.020)
        Q = 100.0  # 100 m^3/s

        h_n = channel.normal_depth(Q)
        h_c = channel.critical_depth(Q)

        assert h_n > 0
        assert h_c > 0
        assert h_n > h_c  # 缓坡

    def test_wide_channel(self):
        """测试宽浅渠道"""
        channel = TrapezoidalChannel(50.0, 1.5, 1000.0, 0.001, 0.020)
        Q = 10.0

        props = channel.properties(1.0)

        assert props['A'] > 0
        assert props['B'] > 50.0  # 水面宽 > 底宽

    def test_steep_side_slope(self):
        """测试陡边坡（m很大）"""
        channel = TrapezoidalChannel(5.0, 5.0, 1000.0, 0.001, 0.020)
        Q = 10.0

        h_n = channel.normal_depth(Q)

        assert h_n > 0


if __name__ == '__main__':
    pytest.main([__file__, '-v', '--tb=short'])
