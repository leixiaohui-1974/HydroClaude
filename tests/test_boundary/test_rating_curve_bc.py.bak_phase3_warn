#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Rating Curve 边界条件单元测试

测试 RatingCurveBoundary 类的各项功能，包括：
1. 基本初始化和参数验证
2. h -> Q 转换
3. Q -> h 反向转换
4. 线性插值
5. 样条插值
6. 幂律拟合
7. 外推方法
8. 文件读写

作者: HydroClaude Team
日期: 2025-10-29
"""

import pytest
import numpy as np
import tempfile
from pathlib import Path
import sys

# 添加项目路径
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from boundary.rating_curve_bc import RatingCurveBoundary, create_rating_curve


class TestRatingCurveInitialization:
    """测试 Rating Curve 初始化"""

    def test_basic_initialization(self):
        """测试基本初始化"""
        rc = RatingCurveBoundary(
            bc_id="RC001",
            h_data=[1.0, 1.5, 2.0, 2.5, 3.0],
            Q_data=[5.0, 15.0, 30.0, 50.0, 75.0]
        )

        assert rc.bc_id == "RC001"
        assert len(rc.h) == 5
        assert len(rc.Q) == 5
        assert rc.interpolation_method == "linear"  # 默认值

    def test_length_mismatch(self):
        """测试数据长度不匹配"""
        with pytest.raises(ValueError, match="Length mismatch"):
            RatingCurveBoundary(
                bc_id="RC_MISMATCH",
                h_data=[1.0, 2.0, 3.0],
                Q_data=[5.0, 10.0]  # 长度不同
            )

    def test_too_few_points(self):
        """测试数据点太少"""
        with pytest.raises(ValueError, match="Need at least 2 data points"):
            RatingCurveBoundary(
                bc_id="RC_FEW",
                h_data=[1.0],
                Q_data=[5.0]
            )

    def test_non_monotonic_h(self):
        """测试水位非单调"""
        with pytest.raises(ValueError, match="monotonically increasing"):
            RatingCurveBoundary(
                bc_id="RC_NON_MONO",
                h_data=[1.0, 2.0, 1.5, 3.0],  # 非单调
                Q_data=[5.0, 10.0, 15.0, 20.0]
            )

    def test_negative_Q(self):
        """测试负流量"""
        with pytest.raises(ValueError, match="non-negative"):
            RatingCurveBoundary(
                bc_id="RC_NEG",
                h_data=[1.0, 2.0, 3.0],
                Q_data=[5.0, -2.0, 10.0]  # 负值
            )

    def test_non_monotonic_Q(self):
        """测试流量非单调"""
        with pytest.raises(ValueError, match="monotonically increasing"):
            RatingCurveBoundary(
                bc_id="RC_Q_NON_MONO",
                h_data=[1.0, 2.0, 3.0],
                Q_data=[5.0, 15.0, 10.0]  # 非单调递增
            )

    def test_create_rating_curve_helper(self):
        """测试便捷创建函数"""
        rc = create_rating_curve(
            bc_id="RC002",
            h_data=[1.0, 2.0, 3.0],
            Q_data=[10.0, 30.0, 60.0]
        )

        assert isinstance(rc, RatingCurveBoundary)
        assert rc.bc_id == "RC002"


class TestHtoQConversion:
    """测试水位到流量转换"""

    def test_h_to_Q_exact_points(self):
        """测试在数据点上的精确值"""
        rc = RatingCurveBoundary(
            bc_id="RC_H2Q",
            h_data=[1.0, 1.5, 2.0, 2.5, 3.0],
            Q_data=[5.0, 15.0, 30.0, 50.0, 75.0]
        )

        # 在数据点上应返回精确值
        assert rc.h_to_Q(1.0) == pytest.approx(5.0)
        assert rc.h_to_Q(2.0) == pytest.approx(30.0)
        assert rc.h_to_Q(3.0) == pytest.approx(75.0)

    def test_h_to_Q_interpolation(self):
        """测试插值"""
        rc = RatingCurveBoundary(
            bc_id="RC_H2Q_INTERP",
            h_data=[1.0, 2.0],
            Q_data=[10.0, 30.0],
            interpolation_method="linear"
        )

        # 线性插值：h=1.5 应对应 Q=20.0
        assert rc.h_to_Q(1.5) == pytest.approx(20.0)

    def test_h_to_Q_increasing(self):
        """测试流量随水位单调递增"""
        rc = RatingCurveBoundary(
            bc_id="RC_MONO",
            h_data=[1.0, 1.5, 2.0, 2.5, 3.0],
            Q_data=[5.0, 15.0, 30.0, 50.0, 75.0]
        )

        h_values = [1.0, 1.2, 1.5, 1.8, 2.0, 2.3, 2.5, 2.8, 3.0]
        Q_prev = 0

        for h in h_values:
            Q = rc.h_to_Q(h)
            assert Q >= Q_prev  # 单调递增
            Q_prev = Q


class TestQtoHConversion:
    """测试流量到水位转换"""

    def test_Q_to_h_exact_points(self):
        """测试在数据点上的精确值"""
        rc = RatingCurveBoundary(
            bc_id="RC_Q2H",
            h_data=[1.0, 1.5, 2.0, 2.5, 3.0],
            Q_data=[5.0, 15.0, 30.0, 50.0, 75.0]
        )

        # 在数据点上应返回精确值
        assert rc.Q_to_h(5.0) == pytest.approx(1.0)
        assert rc.Q_to_h(30.0) == pytest.approx(2.0)
        assert rc.Q_to_h(75.0) == pytest.approx(3.0)

    def test_Q_to_h_interpolation(self):
        """测试反向插值"""
        rc = RatingCurveBoundary(
            bc_id="RC_Q2H_INTERP",
            h_data=[1.0, 2.0],
            Q_data=[10.0, 30.0],
            interpolation_method="linear"
        )

        # Q=20.0 应对应 h=1.5
        assert rc.Q_to_h(20.0) == pytest.approx(1.5)

    def test_bidirectional_consistency(self):
        """测试双向转换一致性"""
        rc = RatingCurveBoundary(
            bc_id="RC_BIDIRECT",
            h_data=[1.0, 1.5, 2.0, 2.5, 3.0],
            Q_data=[5.0, 15.0, 30.0, 50.0, 75.0]
        )

        # h -> Q -> h 应返回原值
        h_test = 2.2
        Q_intermediate = rc.h_to_Q(h_test)
        h_back = rc.Q_to_h(Q_intermediate)

        assert h_back == pytest.approx(h_test, abs=0.01)

        # Q -> h -> Q 应返回原值
        Q_test = 40.0
        h_intermediate = rc.Q_to_h(Q_test)
        Q_back = rc.h_to_Q(h_intermediate)

        assert Q_back == pytest.approx(Q_test, rel=0.01)


class TestInterpolationMethods:
    """测试不同插值方法"""

    def test_linear_interpolation(self):
        """测试线性插值"""
        rc = RatingCurveBoundary(
            bc_id="RC_LINEAR",
            h_data=[1.0, 2.0, 3.0],
            Q_data=[10.0, 30.0, 60.0],
            interpolation_method="linear"
        )

        # 线性插值
        Q = rc.h_to_Q(1.5)
        # 应在 10 和 30 之间
        assert 10 < Q < 30

    def test_cubic_interpolation(self):
        """测试三次样条插值"""
        rc = RatingCurveBoundary(
            bc_id="RC_CUBIC",
            h_data=[1.0, 1.5, 2.0, 2.5, 3.0],
            Q_data=[5.0, 15.0, 30.0, 50.0, 75.0],
            interpolation_method="cubic"
        )

        # 应能正常插值
        Q = rc.h_to_Q(1.7)
        assert np.isfinite(Q)
        assert Q > 0

    def test_cubic_fallback_to_linear(self):
        """测试数据点太少时退化为线性"""
        # 只有3个点，应退化为线性
        rc = RatingCurveBoundary(
            bc_id="RC_CUBIC_FALLBACK",
            h_data=[1.0, 2.0, 3.0],
            Q_data=[10.0, 30.0, 60.0],
            interpolation_method="cubic"
        )

        # 应能正常工作
        Q = rc.h_to_Q(1.5)
        assert np.isfinite(Q)


class TestExtrapolation:
    """测试外推"""

    def test_constant_extrapolation_h_to_Q(self):
        """测试常数外推 h -> Q"""
        rc = RatingCurveBoundary(
            bc_id="RC_CONST_EXTRAP",
            h_data=[2.0, 3.0, 4.0],
            Q_data=[20.0, 40.0, 70.0],
            extrapolation_method="constant"
        )

        # 低于范围：应返回第一个值
        assert rc.h_to_Q(1.0) == pytest.approx(20.0)

        # 高于范围：应返回最后一个值
        assert rc.h_to_Q(5.0) == pytest.approx(70.0)

    def test_linear_extrapolation_h_to_Q(self):
        """测试线性外推 h -> Q"""
        rc = RatingCurveBoundary(
            bc_id="RC_LINEAR_EXTRAP",
            h_data=[2.0, 3.0],
            Q_data=[20.0, 40.0],
            extrapolation_method="linear"
        )

        # 线性外推：斜率 = (40-20)/(3-2) = 20
        # h=1.0: Q = 20 + 20*(1-2) = 0
        Q_low = rc.h_to_Q(1.0)
        assert Q_low == pytest.approx(0.0, abs=0.1)

        # h=4.0: Q = 40 + 20*(4-3) = 60
        Q_high = rc.h_to_Q(4.0)
        assert Q_high == pytest.approx(60.0)

    def test_constant_extrapolation_Q_to_h(self):
        """测试常数外推 Q -> h"""
        rc = RatingCurveBoundary(
            bc_id="RC_CONST_EXTRAP_Q",
            h_data=[2.0, 3.0, 4.0],
            Q_data=[20.0, 40.0, 70.0],
            extrapolation_method="constant"
        )

        # 低于范围
        assert rc.Q_to_h(10.0) == pytest.approx(2.0)

        # 高于范围
        assert rc.Q_to_h(100.0) == pytest.approx(4.0)


class TestPowerLawFitting:
    """测试幂律拟合"""

    def test_power_law_fit(self):
        """测试幂律拟合"""
        # 生成符合幂律的数据：Q = 5 * (h - 1)^2
        h_data = np.array([1.5, 2.0, 2.5, 3.0, 3.5])
        Q_data = 5 * (h_data - 1.0) ** 2

        rc = RatingCurveBoundary(
            bc_id="RC_POWER",
            h_data=h_data,
            Q_data=Q_data,
            use_power_law=True
        )

        assert rc.power_law_params is not None
        # 参数应接近真实值
        assert rc.power_law_params['a'] == pytest.approx(5.0, rel=0.1)
        assert rc.power_law_params['b'] == pytest.approx(2.0, rel=0.1)
        assert rc.power_law_params['h0'] == pytest.approx(1.0, rel=0.1)

    def test_power_law_extrapolation(self):
        """测试幂律外推"""
        h_data = np.array([2.0, 2.5, 3.0])
        Q_data = np.array([10.0, 25.0, 50.0])

        rc = RatingCurveBoundary(
            bc_id="RC_POWER_EXTRAP",
            h_data=h_data,
            Q_data=Q_data,
            use_power_law=True,
            extrapolation_method="power_law"
        )

        # 外推应使用幂律公式
        Q_extrap = rc.h_to_Q(4.0)
        assert Q_extrap > 50.0  # 应大于最大值

    def test_evaluate_fit(self):
        """测试拟合质量评估"""
        h_data = np.array([1.5, 2.0, 2.5, 3.0, 3.5])
        Q_data = 5 * (h_data - 1.0) ** 2

        rc = RatingCurveBoundary(
            bc_id="RC_EVAL",
            h_data=h_data,
            Q_data=Q_data,
            use_power_law=True
        )

        fit_stats = rc.evaluate_fit()

        assert 'rmse' in fit_stats
        assert 'mae' in fit_stats
        assert 'r_squared' in fit_stats

        # 完美拟合数据，R^2 应接近 1
        assert fit_stats['r_squared'] > 0.99


class TestFileIO:
    """测试文件读写"""

    def test_to_file_and_from_file(self):
        """测试保存和加载"""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.csv', delete=False) as f:
            temp_file = f.name

        try:
            # 创建 Rating Curve
            rc_original = RatingCurveBoundary(
                bc_id="RC_FILE",
                h_data=[1.0, 1.5, 2.0, 2.5, 3.0],
                Q_data=[5.0, 15.0, 30.0, 50.0, 75.0]
            )

            # 保存
            rc_original.to_file(temp_file)

            # 加载
            rc_loaded = RatingCurveBoundary.from_file(
                bc_id="RC_FILE_LOADED",
                filepath=temp_file
            )

            # 验证数据一致
            assert len(rc_loaded.h) == len(rc_original.h)
            assert np.allclose(rc_loaded.h, rc_original.h)
            assert np.allclose(rc_loaded.Q, rc_original.Q)

        finally:
            Path(temp_file).unlink()

    def test_from_file_not_found(self):
        """测试文件不存在"""
        with pytest.raises(FileNotFoundError):
            RatingCurveBoundary.from_file(
                bc_id="RC_NOT_FOUND",
                filepath="nonexistent.csv"
            )


class TestRange:
    """测试范围查询"""

    def test_get_range(self):
        """测试获取数据范围"""
        rc = RatingCurveBoundary(
            bc_id="RC_RANGE",
            h_data=[1.5, 2.0, 2.5, 3.0, 3.5],
            Q_data=[10.0, 25.0, 45.0, 70.0, 100.0]
        )

        ranges = rc.get_range()

        assert ranges['h_range'] == (1.5, 3.5)
        assert ranges['Q_range'] == (10.0, 100.0)


class TestProperties:
    """测试属性查询"""

    def test_properties_output(self):
        """测试属性输出"""
        rc = RatingCurveBoundary(
            bc_id="RC_PROP",
            h_data=[1.0, 2.0, 3.0, 4.0],
            Q_data=[5.0, 20.0, 45.0, 80.0],
            interpolation_method="cubic",
            extrapolation_method="linear"
        )

        props = rc.properties()

        assert props['bc_id'] == "RC_PROP"
        assert props['interpolation_method'] == "cubic"
        assert props['extrapolation_method'] == "linear"
        assert props['n_points'] == 4
        assert props['use_power_law'] is False

    def test_properties_with_power_law(self):
        """测试包含幂律的属性"""
        rc = RatingCurveBoundary(
            bc_id="RC_PROP_POWER",
            h_data=[1.5, 2.0, 2.5, 3.0],
            Q_data=[10.0, 25.0, 45.0, 70.0],
            use_power_law=True
        )

        props = rc.properties()

        assert props['use_power_law'] is True
        assert 'power_law_params' in props
        assert 'fit_quality' in props

    def test_repr_string(self):
        """测试字符串表示"""
        rc = RatingCurveBoundary(
            bc_id="RC_REPR",
            h_data=[1.0, 2.0, 3.0],
            Q_data=[10.0, 30.0, 60.0]
        )

        repr_str = repr(rc)

        assert "RC_REPR" in repr_str
        assert "n_points=3" in repr_str


class TestEdgeCases:
    """测试边界情况"""

    def test_zero_flow(self):
        """测试零流量点"""
        rc = RatingCurveBoundary(
            bc_id="RC_ZERO",
            h_data=[1.0, 1.5, 2.0, 2.5],
            Q_data=[0.0, 5.0, 15.0, 30.0]  # 第一个点流量为0
        )

        assert rc.h_to_Q(1.0) == 0.0
        assert rc.Q_to_h(0.0) == 1.0

    def test_two_points_only(self):
        """测试只有两个点（最小情况）"""
        rc = RatingCurveBoundary(
            bc_id="RC_TWO",
            h_data=[1.0, 2.0],
            Q_data=[10.0, 30.0]
        )

        # 应能正常工作
        Q = rc.h_to_Q(1.5)
        assert Q == pytest.approx(20.0)

    def test_large_range(self):
        """测试大范围数据"""
        rc = RatingCurveBoundary(
            bc_id="RC_LARGE",
            h_data=[0.0, 5.0, 10.0, 15.0, 20.0],
            Q_data=[0.0, 100.0, 500.0, 1500.0, 3000.0]
        )

        # 应能正常工作
        Q = rc.h_to_Q(7.5)
        assert Q > 100.0
        assert Q < 500.0


class TestNumericalStability:
    """测试数值稳定性"""

    def test_very_small_increments(self):
        """测试很小的增量"""
        rc = RatingCurveBoundary(
            bc_id="RC_SMALL_INC",
            h_data=[1.0, 1.001, 1.002, 1.003],
            Q_data=[10.0, 10.1, 10.2, 10.3]
        )

        # 应能正常插值
        Q = rc.h_to_Q(1.0015)
        assert np.isfinite(Q)

    def test_very_large_values(self):
        """测试很大的值"""
        rc = RatingCurveBoundary(
            bc_id="RC_LARGE_VAL",
            h_data=[100.0, 110.0, 120.0],
            Q_data=[10000.0, 50000.0, 100000.0]
        )

        # 应能正常工作
        Q = rc.h_to_Q(115.0)
        assert Q > 10000.0
        assert Q < 100000.0


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
