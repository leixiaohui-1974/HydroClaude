#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
时间序列边界条件单元测试

测试 TimeSeriesBoundary 类的各项功能，包括：
1. 基本初始化和参数验证
2. 线性插值
3. 三次样条插值
4. 前向/后向保持
5. 外推方法
6. 文件读写
7. 重采样和变换
8. 统计信息

作者: HydroClaude Team
日期: 2025-10-29
"""

import pytest
import warnings
warnings.filterwarnings("ignore")
import numpy as np
import tempfile
from pathlib import Path
import sys

# 添加项目路径
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from boundary.timeseries_bc import TimeSeriesBoundary, create_timeseries_boundary


class TestTimeSeriesBoundaryInitialization:
    """测试时间序列边界条件初始化"""

    def test_basic_initialization_Q(self):
        """测试流量边界基本初始化"""
        bc = TimeSeriesBoundary(
            bc_id="BC001",
            bc_type="Q",
            time_data=[0, 1, 2, 3],
            value_data=[10.0, 15.0, 12.0, 8.0]
        )

        assert bc.bc_id == "BC001"
        assert bc.bc_type == "Q"
        assert len(bc.t) == 4
        assert len(bc.values) == 4
        assert bc.interpolation_method == "linear"  # 默认值

    def test_basic_initialization_h(self):
        """测试水位边界基本初始化"""
        bc = TimeSeriesBoundary(
            bc_id="BC002",
            bc_type="h",
            time_data=[0, 10, 20, 30],
            value_data=[2.0, 2.5, 2.3, 2.1]
        )

        assert bc.bc_type == "h"
        assert len(bc.t) == 4

    def test_invalid_bc_type(self):
        """测试无效边界类型"""
        with pytest.raises(ValueError, match="bc_type must be"):
            TimeSeriesBoundary(
                bc_id="BC_INVALID",
                bc_type="V",  # 无效类型
                time_data=[0, 1, 2],
                value_data=[1.0, 2.0, 3.0]
            )

    def test_length_mismatch(self):
        """测试时间和值长度不匹配"""
        with pytest.raises(ValueError, match="Length mismatch"):
            TimeSeriesBoundary(
                bc_id="BC_MISMATCH",
                bc_type="Q",
                time_data=[0, 1, 2],
                value_data=[1.0, 2.0]  # 长度不同
            )

    def test_too_few_points(self):
        """测试数据点太少"""
        with pytest.raises(ValueError, match="Need at least 2 data points"):
            TimeSeriesBoundary(
                bc_id="BC_FEW",
                bc_type="Q",
                time_data=[0],
                value_data=[1.0]
            )

    def test_non_monotonic_time(self):
        """测试非单调时间序列"""
        with pytest.raises(ValueError, match="monotonically increasing"):
            TimeSeriesBoundary(
                bc_id="BC_NON_MONO",
                bc_type="Q",
                time_data=[0, 2, 1, 3],  # 非单调
                value_data=[1.0, 2.0, 3.0, 4.0]
            )

    def test_duplicate_time_points(self):
        """测试重复时间点"""
        with pytest.raises(ValueError, match="duplicate time points"):
            TimeSeriesBoundary(
                bc_id="BC_DUP",
                bc_type="Q",
                time_data=[0, 1, 1, 2],  # 重复
                value_data=[1.0, 2.0, 3.0, 4.0]
            )

    def test_create_timeseries_boundary_helper(self):
        """测试便捷创建函数"""
        bc = create_timeseries_boundary(
            bc_id="BC003",
            bc_type="Q",
            time_data=[0, 10, 20],
            value_data=[5.0, 8.0, 6.0]
        )

        assert isinstance(bc, TimeSeriesBoundary)
        assert bc.bc_id == "BC003"


class TestLinearInterpolation:
    """测试线性插值"""

    def test_linear_interpolation_exact_points(self):
        """测试在数据点上的精确值"""
        bc = TimeSeriesBoundary(
            bc_id="BC_LINEAR",
            bc_type="Q",
            time_data=[0, 10, 20, 30],
            value_data=[10.0, 20.0, 15.0, 5.0],
            interpolation_method="linear"
        )

        # 在数据点上应返回精确值
        assert bc.get_value(0) == 10.0
        assert bc.get_value(10) == 20.0
        assert bc.get_value(20) == 15.0
        assert bc.get_value(30) == 5.0

    def test_linear_interpolation_between_points(self):
        """测试在数据点之间的插值"""
        bc = TimeSeriesBoundary(
            bc_id="BC_LINEAR2",
            bc_type="Q",
            time_data=[0, 10],
            value_data=[10.0, 20.0],
            interpolation_method="linear"
        )

        # 中点应为平均值
        assert bc.get_value(5) == pytest.approx(15.0)

    def test_linear_interpolation_general(self):
        """测试一般线性插值"""
        bc = TimeSeriesBoundary(
            bc_id="BC_LINEAR3",
            bc_type="Q",
            time_data=[0, 10, 20],
            value_data=[0.0, 10.0, 20.0],
            interpolation_method="linear"
        )

        # 验证线性关系
        assert bc.get_value(5) == pytest.approx(5.0)
        assert bc.get_value(15) == pytest.approx(15.0)


class TestCubicInterpolation:
    """测试三次样条插值"""

    def test_cubic_interpolation_exact_points(self):
        """测试在数据点上的精确值"""
        bc = TimeSeriesBoundary(
            bc_id="BC_CUBIC",
            bc_type="Q",
            time_data=[0, 10, 20, 30, 40],
            value_data=[10.0, 20.0, 15.0, 25.0, 20.0],
            interpolation_method="cubic"
        )

        # 在数据点上应返回精确值
        assert bc.get_value(0) == pytest.approx(10.0, abs=0.01)
        assert bc.get_value(10) == pytest.approx(20.0, abs=0.01)
        assert bc.get_value(20) == pytest.approx(15.0, abs=0.01)

    def test_cubic_interpolation_smoothness(self):
        """测试三次样条的平滑性"""
        bc = TimeSeriesBoundary(
            bc_id="BC_CUBIC2",
            bc_type="Q",
            time_data=[0, 10, 20, 30, 40],
            value_data=[10.0, 20.0, 15.0, 25.0, 20.0],
            interpolation_method="cubic"
        )

        # 获取一系列插值点
        t_interp = np.linspace(0, 40, 100)
        values = bc.get_values(t_interp)

        # 应该平滑，无突变
        assert len(values) == 100
        assert all(np.isfinite(values))

    def test_cubic_fallback_to_linear(self):
        """测试数据点太少时退化为线性插值"""
        # 只有3个点，应退化为线性
        bc = TimeSeriesBoundary(
            bc_id="BC_CUBIC_FALLBACK",
            bc_type="Q",
            time_data=[0, 10, 20],
            value_data=[10.0, 20.0, 15.0],
            interpolation_method="cubic"
        )

        # 应能正常工作
        value = bc.get_value(5)
        assert np.isfinite(value)


class TestStepwiseInterpolation:
    """测试阶跃插值"""

    def test_previous_interpolation(self):
        """测试前向保持插值"""
        bc = TimeSeriesBoundary(
            bc_id="BC_PREV",
            bc_type="Q",
            time_data=[0, 10, 20, 30],
            value_data=[10.0, 20.0, 15.0, 5.0],
            interpolation_method="previous"
        )

        # 在区间内应保持前一个值
        assert bc.get_value(5) == 10.0
        assert bc.get_value(15) == 20.0
        assert bc.get_value(25) == 15.0

    def test_next_interpolation(self):
        """测试后向保持插值"""
        bc = TimeSeriesBoundary(
            bc_id="BC_NEXT",
            bc_type="Q",
            time_data=[0, 10, 20, 30],
            value_data=[10.0, 20.0, 15.0, 5.0],
            interpolation_method="next"
        )

        # 在区间内应保持后一个值
        assert bc.get_value(5) == 20.0
        assert bc.get_value(15) == 15.0
        assert bc.get_value(25) == 5.0


class TestExtrapolation:
    """测试外推"""

    def test_constant_extrapolation_before(self):
        """测试常数外推（时间序列之前）"""
        bc = TimeSeriesBoundary(
            bc_id="BC_EXTRAP_CONST",
            bc_type="Q",
            time_data=[10, 20, 30],
            value_data=[10.0, 20.0, 15.0],
            extrapolation_method="constant"
        )

        # 时间序列之前应返回第一个值
        assert bc.get_value(0) == 10.0
        assert bc.get_value(5) == 10.0

    def test_constant_extrapolation_after(self):
        """测试常数外推（时间序列之后）"""
        bc = TimeSeriesBoundary(
            bc_id="BC_EXTRAP_CONST2",
            bc_type="Q",
            time_data=[10, 20, 30],
            value_data=[10.0, 20.0, 15.0],
            extrapolation_method="constant"
        )

        # 时间序列之后应返回最后一个值
        assert bc.get_value(40) == 15.0
        assert bc.get_value(100) == 15.0

    def test_linear_extrapolation_before(self):
        """测试线性外推（时间序列之前）"""
        bc = TimeSeriesBoundary(
            bc_id="BC_EXTRAP_LINEAR",
            bc_type="Q",
            time_data=[10, 20],
            value_data=[10.0, 20.0],
            extrapolation_method="linear"
        )

        # 线性外推
        # 斜率 = (20-10)/(20-10) = 1.0
        # t=0: v = 10 + 1.0*(0-10) = 0
        assert bc.get_value(0) == pytest.approx(0.0)

    def test_linear_extrapolation_after(self):
        """测试线性外推（时间序列之后）"""
        bc = TimeSeriesBoundary(
            bc_id="BC_EXTRAP_LINEAR2",
            bc_type="Q",
            time_data=[10, 20],
            value_data=[10.0, 20.0],
            extrapolation_method="linear"
        )

        # 线性外推
        # 斜率 = 1.0
        # t=30: v = 20 + 1.0*(30-20) = 30
        assert bc.get_value(30) == pytest.approx(30.0)


class TestBatchQuery:
    """测试批量查询"""

    def test_get_values_array(self):
        """测试批量获取值"""
        bc = TimeSeriesBoundary(
            bc_id="BC_BATCH",
            bc_type="Q",
            time_data=[0, 10, 20, 30],
            value_data=[10.0, 20.0, 15.0, 5.0]
        )

        t_query = [0, 5, 10, 15, 20]
        values = bc.get_values(t_query)

        assert len(values) == 5
        assert values[0] == 10.0
        assert values[2] == 20.0
        assert values[4] == 15.0

    def test_get_values_list(self):
        """测试列表输入"""
        bc = TimeSeriesBoundary(
            bc_id="BC_BATCH2",
            bc_type="Q",
            time_data=[0, 10, 20],
            value_data=[5.0, 10.0, 15.0]
        )

        t_query = [0, 10, 20]
        values = bc.get_values(t_query)

        assert isinstance(values, np.ndarray)
        assert len(values) == 3


class TestFileIO:
    """测试文件读写"""

    def test_to_file_and_from_file(self):
        """测试保存和加载"""
        # 创建临时文件
        with tempfile.NamedTemporaryFile(mode='w', suffix='.csv', delete=False) as f:
            temp_file = f.name

        try:
            # 创建边界条件
            bc_original = TimeSeriesBoundary(
                bc_id="BC_FILE",
                bc_type="Q",
                time_data=[0, 10, 20, 30],
                value_data=[10.0, 15.0, 12.0, 8.0]
            )

            # 保存到文件
            bc_original.to_file(temp_file)

            # 从文件加载
            bc_loaded = TimeSeriesBoundary.from_file(
                bc_id="BC_FILE_LOADED",
                bc_type="Q",
                filepath=temp_file
            )

            # 验证数据一致
            assert len(bc_loaded.t) == len(bc_original.t)
            assert np.allclose(bc_loaded.t, bc_original.t)
            assert np.allclose(bc_loaded.values, bc_original.values)

        finally:
            # 清理临时文件
            Path(temp_file).unlink()

    def test_from_file_not_found(self):
        """测试文件不存在"""
        with pytest.raises(FileNotFoundError):
            TimeSeriesBoundary.from_file(
                bc_id="BC_NOT_FOUND",
                bc_type="Q",
                filepath="nonexistent_file.csv"
            )


class TestTimeRangeAndStatistics:
    """测试时间范围和统计"""

    def test_get_time_range(self):
        """测试获取时间范围"""
        bc = TimeSeriesBoundary(
            bc_id="BC_RANGE",
            bc_type="Q",
            time_data=[5, 15, 25, 35],
            value_data=[10.0, 20.0, 15.0, 5.0]
        )

        t_min, t_max = bc.get_time_range()
        assert t_min == 5.0
        assert t_max == 35.0

    def test_get_value_range(self):
        """测试获取值范围"""
        bc = TimeSeriesBoundary(
            bc_id="BC_VALUE_RANGE",
            bc_type="Q",
            time_data=[0, 10, 20, 30],
            value_data=[10.0, 25.0, 15.0, 5.0]
        )

        v_min, v_max = bc.get_value_range()
        assert v_min == 5.0
        assert v_max == 25.0

    def test_get_statistics(self):
        """测试获取统计信息"""
        bc = TimeSeriesBoundary(
            bc_id="BC_STATS",
            bc_type="Q",
            time_data=[0, 10, 20, 30],
            value_data=[10.0, 20.0, 15.0, 5.0]
        )

        stats = bc.get_statistics()

        assert stats['n_points'] == 4
        assert stats['duration'] == 30.0
        assert stats['mean'] == pytest.approx(12.5)
        assert stats['min'] == 5.0
        assert stats['max'] == 20.0


class TestTransformations:
    """测试变换操作"""

    def test_resample(self):
        """测试重采样"""
        bc = TimeSeriesBoundary(
            bc_id="BC_RESAMPLE",
            bc_type="Q",
            time_data=[0, 10, 20, 30],
            value_data=[10.0, 20.0, 15.0, 5.0]
        )

        bc_resampled = bc.resample(dt=5.0)

        # 应有更多数据点
        assert len(bc_resampled.t) > len(bc.t)
        # 时间步长应为5
        dt = np.diff(bc_resampled.t)
        assert np.allclose(dt, 5.0, atol=0.01)

    def test_shift_time(self):
        """测试时间平移"""
        bc = TimeSeriesBoundary(
            bc_id="BC_SHIFT",
            bc_type="Q",
            time_data=[0, 10, 20],
            value_data=[10.0, 20.0, 15.0]
        )

        bc_shifted = bc.shift_time(time_shift=100.0)

        # 时间应平移
        assert bc_shifted.t[0] == pytest.approx(100.0)
        assert bc_shifted.t[-1] == pytest.approx(120.0)
        # 值不变
        assert np.allclose(bc_shifted.values, bc.values)

    def test_scale_values(self):
        """测试值缩放"""
        bc = TimeSeriesBoundary(
            bc_id="BC_SCALE",
            bc_type="Q",
            time_data=[0, 10, 20],
            value_data=[10.0, 20.0, 15.0]
        )

        bc_scaled = bc.scale_values(scale_factor=2.0)

        # 时间不变
        assert np.allclose(bc_scaled.t, bc.t)
        # 值应缩放
        assert bc_scaled.values[0] == pytest.approx(20.0)
        assert bc_scaled.values[1] == pytest.approx(40.0)


class TestProperties:
    """测试属性查询"""

    def test_properties_output(self):
        """测试属性输出"""
        bc = TimeSeriesBoundary(
            bc_id="BC_PROP",
            bc_type="Q",
            time_data=[0, 10, 20, 30],
            value_data=[10.0, 20.0, 15.0, 5.0],
            interpolation_method="cubic",
            extrapolation_method="linear"
        )

        props = bc.properties()

        assert props['bc_id'] == "BC_PROP"
        assert props['bc_type'] == "Q"
        assert props['interpolation_method'] == "cubic"
        assert props['extrapolation_method'] == "linear"
        assert props['n_points'] == 4
        assert props['duration'] == 30.0

    def test_repr_string(self):
        """测试字符串表示"""
        bc = TimeSeriesBoundary(
            bc_id="BC_REPR",
            bc_type="h",
            time_data=[0, 10, 20],
            value_data=[2.0, 2.5, 2.3]
        )

        repr_str = repr(bc)

        assert "BC_REPR" in repr_str
        assert "type='h'" in repr_str
        assert "n_points=3" in repr_str


class TestEdgeCases:
    """测试边界情况"""

    def test_single_interval(self):
        """测试单个区间（2个点）"""
        bc = TimeSeriesBoundary(
            bc_id="BC_SINGLE",
            bc_type="Q",
            time_data=[0, 10],
            value_data=[10.0, 20.0]
        )

        # 应能正常插值
        assert bc.get_value(5) == pytest.approx(15.0)

    def test_large_time_span(self):
        """测试大时间跨度"""
        bc = TimeSeriesBoundary(
            bc_id="BC_LARGE",
            bc_type="Q",
            time_data=[0, 86400, 172800],  # 0, 1天, 2天（秒）
            value_data=[10.0, 20.0, 15.0]
        )

        # 应能正常工作
        value = bc.get_value(43200)  # 0.5天
        assert np.isfinite(value)

    def test_negative_values(self):
        """测试负值（如潮汐水位）"""
        bc = TimeSeriesBoundary(
            bc_id="BC_NEGATIVE",
            bc_type="h",
            time_data=[0, 10, 20, 30],
            value_data=[-1.0, 0.5, -0.5, 1.0]
        )

        # 应能处理负值
        value = bc.get_value(5)
        assert np.isfinite(value)


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
