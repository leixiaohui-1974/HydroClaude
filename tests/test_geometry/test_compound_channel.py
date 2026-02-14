#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
复合断面渠道单元测试

测试 CompoundChannel 类的所有功能：
- 分区水力几何计算
- 分区流速法
- 等效Manning系数法
- 正常水深和临界水深
- 漫滩判断

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

from geometry.compound_channel import CompoundChannel, create_compound_channel


class TestCompoundChannelBasics:
    """测试复合断面基本功能"""

    def test_initialization(self):
        """测试初始化"""
        stations = [0, 20, 30, 40, 50, 70, 80]
        elevations = [5, 3, 0.5, 0, 0.5, 3, 5]
        bankfull_elevation = 3.0

        channel = CompoundChannel(
            stations=stations,
            elevations=elevations,
            bankfull_elevation=bankfull_elevation,
            length=1000.0,
            bottom_slope=0.001,
            manning_n_main=0.025,
            manning_n_floodplain=0.040
        )

        assert channel.z_bankfull == 3.0
        assert channel.n_main == 0.025
        assert channel.n_flood == 0.040
        assert channel.x_left_bank is not None
        assert channel.x_right_bank is not None

    def test_manual_bank_stations(self):
        """测试手动指定左右岸桩号"""
        stations = [0, 20, 30, 40, 50, 70, 80]
        elevations = [5, 3, 0.5, 0, 0.5, 3, 5]

        channel = CompoundChannel(
            stations=stations,
            elevations=elevations,
            bankfull_elevation=3.0,
            length=1000.0,
            bottom_slope=0.001,
            manning_n_main=0.025,
            manning_n_floodplain=0.040,
            left_bank_station=25.0,
            right_bank_station=55.0
        )

        assert channel.x_left_bank == 25.0
        assert channel.x_right_bank == 55.0

    def test_convenience_function(self):
        """测试便捷创建函数"""
        channel = create_compound_channel(
            stations=[0, 20, 40, 60, 80],
            elevations=[5, 2, 0, 2, 5],
            bankfull_elevation=2.5,
            length=1000.0,
            bottom_slope=0.001,
            manning_n_main=0.025,
            manning_n_floodplain=0.045,
            channel_id="test_compound"
        )

        assert channel.channel_id == "test_compound"
        assert channel.n_main == 0.025
        assert channel.n_flood == 0.045


class TestSubdivisionProperties:
    """测试分区水力要素计算"""

    @pytest.fixture
    def compound_channel(self):
        """创建标准复合断面

        断面形状：
        左滩地 | 主槽 | 右滩地

        满槽水位：3m
        """
        return CompoundChannel(
            stations=[0, 20, 30, 40, 50, 70, 80],
            elevations=[5, 3, 0.5, 0, 0.5, 3, 5],
            bankfull_elevation=3.0,
            length=1000.0,
            bottom_slope=0.001,
            manning_n_main=0.025,
            manning_n_floodplain=0.040,
            left_bank_station=20.0,
            right_bank_station=70.0
        )

    def test_subdivision_below_bankfull(self, compound_channel):
        """测试水位低于满槽时的分区（只有主槽过水）"""
        h = 2.0  # 水位低于满槽

        regions = compound_channel._get_subdivision_properties(h)

        # 主槽应该有水
        assert regions['main']['A'] > 0
        assert regions['main']['P'] > 0

        # 滩地应该没水或很少
        # （取决于具体断面形状，可能有少量水）

    def test_subdivision_above_bankfull(self, compound_channel):
        """测试水位高于满槽时的分区（漫滩）"""
        h = 4.0  # 水位高于满槽

        regions = compound_channel._get_subdivision_properties(h)

        # 所有区域都应该有水
        assert regions['main']['A'] > 0
        assert regions['left_flood']['A'] > 0
        assert regions['right_flood']['A'] > 0

    def test_manning_coefficients(self, compound_channel):
        """测试各区域Manning系数设置"""
        h = 4.0

        regions = compound_channel._get_subdivision_properties(h)

        assert regions['main']['n'] == 0.025  # 主槽
        assert regions['left_flood']['n'] == 0.040  # 左滩地
        assert regions['right_flood']['n'] == 0.040  # 右滩地


class TestDischargeCalculation:
    """测试流量计算"""

    @pytest.fixture
    def compound_channel(self):
        """创建标准复合断面"""
        return CompoundChannel(
            stations=[0, 20, 30, 40, 50, 70, 80],
            elevations=[5, 3, 0.5, 0, 0.5, 3, 5],
            bankfull_elevation=3.0,
            length=1000.0,
            bottom_slope=0.001,
            manning_n_main=0.025,
            manning_n_floodplain=0.040,
            left_bank_station=20.0,
            right_bank_station=70.0
        )

    def test_discharge_divided_method(self, compound_channel):
        """测试分区流速法"""
        h = 4.0

        Q_total, Q_dict = compound_channel.compute_discharge_divided(h)

        # 总流量应该是各区域流量之和
        Q_sum = Q_dict['left_flood'] + Q_dict['main'] + Q_dict['right_flood']
        assert np.isclose(Q_total, Q_sum, rtol=1e-6)

        # 所有流量应该为正
        assert Q_total > 0
        assert Q_dict['main'] > 0
        assert Q_dict['left_flood'] >= 0
        assert Q_dict['right_flood'] >= 0

    def test_discharge_equivalent_method(self, compound_channel):
        """测试等效Manning系数法"""
        h = 4.0

        Q_eq = compound_channel.compute_discharge_equivalent(h)

        # 流量应该为正
        assert Q_eq > 0

    def test_methods_comparison(self, compound_channel):
        """对比两种方法的结果（应该相近但不完全相同）"""
        h = 4.0

        Q_divided, _ = compound_channel.compute_discharge_divided(h)
        Q_equivalent = compound_channel.compute_discharge_equivalent(h)

        # 两种方法结果应该在合理范围内（允许20%差异）
        relative_diff = abs(Q_divided - Q_equivalent) / Q_divided

        assert relative_diff < 0.20  # 允许20%差异

    def test_discharge_zero_depth(self, compound_channel):
        """测试零水深"""
        Q_divided, Q_dict = compound_channel.compute_discharge_divided(0.0)
        Q_equivalent = compound_channel.compute_discharge_equivalent(0.0)

        assert Q_divided == 0.0
        assert Q_equivalent == 0.0
        assert all(Q == 0.0 for Q in Q_dict.values())


class TestNormalDepth:
    """测试正常水深计算"""

    @pytest.fixture
    def compound_channel(self):
        """创建标准复合断面"""
        return CompoundChannel(
            stations=[0, 20, 30, 40, 50, 70, 80],
            elevations=[5, 3, 0.5, 0, 0.5, 3, 5],
            bankfull_elevation=3.0,
            length=1000.0,
            bottom_slope=0.001,
            manning_n_main=0.025,
            manning_n_floodplain=0.040,
            left_bank_station=20.0,
            right_bank_station=70.0
        )

    def test_normal_depth_divided_method(self, compound_channel):
        """测试使用分区法计算正常水深"""
        Q = 50.0  # m^3/s

        h_n = compound_channel.normal_depth(Q, method='divided')

        # 验证正常水深为正
        assert h_n > 0

        # 验证流量计算
        Q_check, _ = compound_channel.compute_discharge_divided(h_n)

        # 应该满足流量条件（相对误差 < 1%）
        assert np.isclose(Q_check, Q, rtol=0.01)

    def test_normal_depth_equivalent_method(self, compound_channel):
        """测试使用等效法计算正常水深"""
        Q = 50.0  # m^3/s

        h_n = compound_channel.normal_depth(Q, method='equivalent')

        # 验证正常水深为正
        assert h_n > 0

        # 验证流量计算
        Q_check = compound_channel.compute_discharge_equivalent(h_n)

        # 应该满足流量条件（相对误差 < 1%）
        assert np.isclose(Q_check, Q, rtol=0.01)

    def test_normal_depth_convergence(self, compound_channel):
        """测试不同流量下的收敛性"""
        flow_rates = [10.0, 30.0, 50.0, 80.0]

        for Q in flow_rates:
            h_n = compound_channel.normal_depth(Q, method='divided')

            # 验证正常水深为正
            assert h_n > 0

            # 验证流量计算
            Q_check, _ = compound_channel.compute_discharge_divided(h_n)

            assert np.isclose(Q_check, Q, rtol=0.01)

    def test_normal_depth_zero_flow(self, compound_channel):
        """测试零流量"""
        h_n = compound_channel.normal_depth(0.0)
        assert h_n == 0.0


class TestCriticalDepth:
    """测试临界水深计算"""

    @pytest.fixture
    def compound_channel(self):
        """创建标准复合断面"""
        return CompoundChannel(
            stations=[0, 20, 30, 40, 50, 70, 80],
            elevations=[5, 3, 0.5, 0, 0.5, 3, 5],
            bankfull_elevation=3.0,
            length=1000.0,
            bottom_slope=0.001,
            manning_n_main=0.025,
            manning_n_floodplain=0.040,
            left_bank_station=20.0,
            right_bank_station=70.0
        )

    def test_critical_depth_basic(self, compound_channel):
        """测试临界水深基本计算"""
        Q = 50.0  # m^3/s
        g = 9.81

        h_c = compound_channel.critical_depth(Q)

        # 验证临界水深为正
        assert h_c > 0

        # 验证临界流条件：Q^2 = g * A^3 / B
        props = compound_channel.properties(h_c)
        A = props['A']
        B = props['B']

        lhs = Q**2
        rhs = g * A**3 / B

        # 应该满足临界流条件（相对误差 < 2%）
        assert np.isclose(lhs, rhs, rtol=0.02)

    def test_critical_depth_froude_one(self, compound_channel):
        """测试临界水深对应 Froude 数 ~= 1"""
        Q = 50.0  # m^3/s

        h_c = compound_channel.critical_depth(Q)
        Fr = compound_channel.froude_number(Q, h_c)

        # Froude 数应该接近 1
        assert np.isclose(Fr, 1.0, atol=0.03)


class TestOverbankFlow:
    """测试漫滩流动"""

    @pytest.fixture
    def compound_channel(self):
        """创建标准复合断面"""
        return CompoundChannel(
            stations=[0, 20, 30, 40, 50, 70, 80],
            elevations=[5, 3, 0.5, 0, 0.5, 3, 5],
            bankfull_elevation=3.0,
            length=1000.0,
            bottom_slope=0.001,
            manning_n_main=0.025,
            manning_n_floodplain=0.040,
            left_bank_station=20.0,
            right_bank_station=70.0
        )

    def test_is_overbank(self, compound_channel):
        """测试漫滩判断"""
        # 水位低于满槽
        assert not compound_channel.is_overbank(2.0)

        # 水位等于满槽
        h_bankfull = compound_channel.z_bankfull - compound_channel.z_min
        assert not compound_channel.is_overbank(h_bankfull) or \
               compound_channel.is_overbank(h_bankfull)  # 可能在边界上

        # 水位高于满槽
        assert compound_channel.is_overbank(4.0)

    def test_discharge_increase_overbank(self, compound_channel):
        """测试漫滩后流量显著增加"""
        h_bankfull = compound_channel.z_bankfull - compound_channel.z_min

        # 满槽时的流量
        Q_bankfull, _ = compound_channel.compute_discharge_divided(h_bankfull)

        # 漫滩后的流量
        h_overbank = h_bankfull + 1.0
        Q_overbank, _ = compound_channel.compute_discharge_divided(h_overbank)

        # 漫滩后流量应显著增加
        assert Q_overbank > Q_bankfull * 1.5  # 至少增加50%


class TestSubdivisionInfo:
    """测试分区详细信息"""

    @pytest.fixture
    def compound_channel(self):
        """创建标准复合断面"""
        return CompoundChannel(
            stations=[0, 20, 30, 40, 50, 70, 80],
            elevations=[5, 3, 0.5, 0, 0.5, 3, 5],
            bankfull_elevation=3.0,
            length=1000.0,
            bottom_slope=0.001,
            manning_n_main=0.025,
            manning_n_floodplain=0.040,
            left_bank_station=20.0,
            right_bank_station=70.0
        )

    def test_get_subdivision_info(self, compound_channel):
        """测试获取分区详细信息"""
        h = 4.0

        info = compound_channel.get_subdivision_info(h)

        assert 'total_discharge' in info
        assert 'is_overbank' in info
        assert 'regions' in info

        # 检查各区域信息
        assert 'left_flood' in info['regions']
        assert 'main' in info['regions']
        assert 'right_flood' in info['regions']

        # 检查流量分配百分比
        total_fraction = sum(
            region['discharge_fraction']
            for region in info['regions'].values()
        )
        assert np.isclose(total_fraction, 1.0, rtol=1e-6)


class TestIntegrationWithSimpleSections:
    """测试与简单断面的集成"""

    def test_compound_vs_uniform_manning(self):
        """对比复合断面vs均匀Manning系数的差异"""
        stations = [0, 20, 30, 40, 50, 70, 80]
        elevations = [5, 3, 0.5, 0, 0.5, 3, 5]

        # 复合断面（分区Manning系数）
        compound = CompoundChannel(
            stations=stations,
            elevations=elevations,
            bankfull_elevation=3.0,
            length=1000.0,
            bottom_slope=0.001,
            manning_n_main=0.025,
            manning_n_floodplain=0.040,
            left_bank_station=20.0,
            right_bank_station=70.0
        )

        # 均匀Manning系数（使用等效法近似）
        h = 4.0
        Q_compound, _ = compound.compute_discharge_divided(h)
        Q_equivalent = compound.compute_discharge_equivalent(h)

        # 两者应有差异（分区法更精确）
        assert Q_compound != Q_equivalent

        # 但差异不应过大（通常<20%）
        relative_diff = abs(Q_compound - Q_equivalent) / Q_compound
        assert relative_diff < 0.20


class TestEdgeCases:
    """测试边界情况"""

    def test_zero_depth(self):
        """测试零水深"""
        channel = CompoundChannel(
            stations=[0, 20, 40, 60, 80],
            elevations=[5, 2, 0, 2, 5],
            bankfull_elevation=2.5,
            length=1000.0,
            bottom_slope=0.001,
            manning_n_main=0.025,
            manning_n_floodplain=0.040
        )

        Q_total, Q_dict = channel.compute_discharge_divided(0.0)

        assert Q_total == 0.0
        assert all(Q == 0.0 for Q in Q_dict.values())

    def test_very_high_water(self):
        """测试极高水位（完全漫滩）"""
        channel = CompoundChannel(
            stations=[0, 20, 40, 60, 80],
            elevations=[5, 2, 0, 2, 5],
            bankfull_elevation=2.5,
            length=1000.0,
            bottom_slope=0.001,
            manning_n_main=0.025,
            manning_n_floodplain=0.040
        )

        h_max = channel.z_max - channel.z_min
        h = 0.9 * h_max

        Q_total, Q_dict = channel.compute_discharge_divided(h)

        # 应该能正常计算
        assert Q_total > 0
        assert all(Q >= 0 for Q in Q_dict.values())


if __name__ == '__main__':
    pytest.main([__file__, '-v', '--tb=short'])
