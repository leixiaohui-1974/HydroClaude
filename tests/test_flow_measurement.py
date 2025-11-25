"""
测试流量测量设施

测试内容：
- 矩形堰流量计算
- 三角堰流量计算
- 巴歇尔槽流量计算
- 各种边界情况
- 反算水头功能
- 淹没条件判别

Author: HydroClaude Development Team
Date: 2025-01
"""
import sys
import warnings
warnings.filterwarnings("ignore")
import os

# ========== 路径设置 ==========
script_path = os.path.abspath(__file__)
project_root = os.path.dirname(os.path.dirname(script_path))
sys.path.insert(0, project_root)


import pytest
import numpy as np
from physics.structures.flow_measurement import (
    RectangularWeir, RectangularWeirGeometry,
    TriangularWeir, TriangularWeirGeometry,
    ParshallFlume, ParshallFlumeGeometry,
    create_rectangular_weir, create_triangular_weir, create_parshall_flume
)


# ============================================================================
# 矩形堰测试
# ============================================================================

class TestRectangularWeirGeometry:
    """测试矩形堰几何参数"""

    def test_valid_geometry(self):
        """测试有效几何参数"""
        geom = RectangularWeirGeometry(
            position=100.0,
            crest_width=2.0,
            crest_elevation=1.0,
            channel_width=3.0
        )

        assert geom.position == 100.0
        assert geom.crest_width == 2.0
        assert geom.crest_elevation == 1.0
        assert geom.channel_width == 3.0

    def test_invalid_crest_width(self):
        """测试无效堰宽"""
        with pytest.raises(ValueError, match="Crest width must be positive"):
            RectangularWeirGeometry(
                position=100.0,
                crest_width=0.0
            )

    def test_crest_wider_than_channel(self):
        """测试堰宽超过渠宽"""
        with pytest.raises(ValueError, match="cannot exceed channel width"):
            RectangularWeirGeometry(
                position=100.0,
                crest_width=5.0,
                channel_width=3.0
            )


class TestRectangularWeirCalculations:
    """测试矩形堰流量计算"""

    def test_discharge_calculation(self):
        """测试流量计算"""
        weir = create_rectangular_weir(
            position=100.0,
            crest_width=2.0
        )

        Q = weir.compute_discharge(h=0.3)

        # Q = Cd * b * sqrt(2g) * h^1.5
        # Q = 0.42 * 2.0 * sqrt(2*9.81) * 0.3^1.5
        # Q ~= 0.42 * 2.0 * 4.43 * 0.164 ~= 0.61 m^3/s
        assert 0.55 < Q < 0.70

    def test_discharge_increases_with_head(self):
        """测试流量随水头增加"""
        weir = create_rectangular_weir(position=100.0, crest_width=2.0)

        Q1 = weir.compute_discharge(h=0.2)
        Q2 = weir.compute_discharge(h=0.4)
        Q3 = weir.compute_discharge(h=0.6)

        assert Q1 < Q2 < Q3

    def test_discharge_increases_with_width(self):
        """测试流量随堰宽增加"""
        weir_narrow = create_rectangular_weir(position=100.0, crest_width=1.0)
        weir_wide = create_rectangular_weir(position=100.0, crest_width=3.0)

        Q_narrow = weir_narrow.compute_discharge(h=0.3)
        Q_wide = weir_wide.compute_discharge(h=0.3)

        assert Q_wide > Q_narrow * 2.5  # 约3倍关系

    def test_contracted_weir(self):
        """测试收缩堰（Francis公式）"""
        # 收缩堰（渠道宽度大于堰宽）
        weir_contracted = RectangularWeir(
            RectangularWeirGeometry(
                position=100.0,
                crest_width=2.0,
                channel_width=4.0  # 渠道更宽，有收缩
            )
        )

        # 全宽堰
        weir_full = create_rectangular_weir(position=100.0, crest_width=2.0)

        Q_contracted = weir_contracted.compute_discharge(h=0.3)
        Q_full = weir_full.compute_discharge(h=0.3)

        # 收缩堰流量应小于全宽堰
        assert Q_contracted < Q_full

    def test_head_from_discharge(self):
        """测试反算水头"""
        weir = create_rectangular_weir(position=100.0, crest_width=2.0)

        # 正算
        h_target = 0.5
        Q = weir.compute_discharge(h=h_target)

        # 反算
        h_computed = weir.compute_head(Q=Q)

        # 应该接近原始水头
        assert abs(h_computed - h_target) < 0.01  # 1 cm误差

    def test_zero_head(self):
        """测试零水头"""
        weir = create_rectangular_weir(position=100.0, crest_width=2.0)

        Q = weir.compute_discharge(h=0.0)

        assert Q == 0.0


# ============================================================================
# 三角堰测试
# ============================================================================

class TestTriangularWeirGeometry:
    """测试三角堰几何参数"""

    def test_valid_geometry(self):
        """测试有效几何参数"""
        geom = TriangularWeirGeometry(
            position=100.0,
            notch_angle=90.0,
            crest_elevation=1.0
        )

        assert geom.position == 100.0
        assert geom.notch_angle == 90.0
        assert geom.crest_elevation == 1.0

    def test_invalid_angle_too_small(self):
        """测试角度过小"""
        with pytest.raises(ValueError, match="between 10 deg and 120 deg"):
            TriangularWeirGeometry(position=100.0, notch_angle=5.0)

    def test_invalid_angle_too_large(self):
        """测试角度过大"""
        with pytest.raises(ValueError, match="between 10 deg and 120 deg"):
            TriangularWeirGeometry(position=100.0, notch_angle=150.0)


class TestTriangularWeirCalculations:
    """测试三角堰流量计算"""

    def test_discharge_calculation_90deg(self):
        """测试90 deg三角堰流量计算"""
        weir = create_triangular_weir(position=100.0, notch_angle=90.0)

        Q = weir.compute_discharge(h=0.2)

        # Q = (8/15) * Cd * tan(45 deg) * sqrt(2g) * h^2.5
        # Q = (8/15) * 0.58 * 1.0 * sqrt(19.62) * 0.2^2.5
        # Q ~= 0.309 * 4.43 * 0.0179 ~= 0.0245 m^3/s
        assert 0.020 < Q < 0.030

    def test_discharge_increases_with_head(self):
        """测试流量随水头增加（h^2.5关系）"""
        weir = create_triangular_weir(position=100.0, notch_angle=90.0)

        Q1 = weir.compute_discharge(h=0.1)
        Q2 = weir.compute_discharge(h=0.2)
        Q3 = weir.compute_discharge(h=0.3)

        assert Q1 < Q2 < Q3

        # 验证h^2.5关系
        # Q2/Q1 应该约等于 (0.2/0.1)^2.5 = 2^2.5 ~= 5.66
        ratio = Q2 / Q1
        assert 5.0 < ratio < 6.5

    def test_discharge_increases_with_angle(self):
        """测试流量随缺口角度增加"""
        weir_30 = create_triangular_weir(position=100.0, notch_angle=30.0)
        weir_60 = create_triangular_weir(position=100.0, notch_angle=60.0)
        weir_90 = create_triangular_weir(position=100.0, notch_angle=90.0)

        Q_30 = weir_30.compute_discharge(h=0.2)
        Q_60 = weir_60.compute_discharge(h=0.2)
        Q_90 = weir_90.compute_discharge(h=0.2)

        # 角度越大，流量越大（因为tan(theta/2)增大）
        assert Q_30 < Q_60 < Q_90

    def test_head_from_discharge(self):
        """测试反算水头"""
        weir = create_triangular_weir(position=100.0, notch_angle=90.0)

        # 正算
        h_target = 0.25
        Q = weir.compute_discharge(h=h_target)

        # 反算
        h_computed = weir.compute_head(Q=Q)

        # 应该精确匹配（直接公式反算）
        assert abs(h_computed - h_target) < 0.001

    def test_small_discharge_sensitivity(self):
        """测试小流量测量灵敏度"""
        weir = create_triangular_weir(position=100.0, notch_angle=90.0)

        # 三角堰对小流量更灵敏（h^2.5关系）
        Q_small = weir.compute_discharge(h=0.05)
        Q_double_head = weir.compute_discharge(h=0.10)

        # 水头翻倍，流量应该增加 2^2.5 ~= 5.66 倍
        ratio = Q_double_head / Q_small
        assert 5.0 < ratio < 6.5


# ============================================================================
# 巴歇尔槽测试
# ============================================================================

class TestParshallFlumeGeometry:
    """测试巴歇尔槽几何参数"""

    def test_valid_geometry_SI(self):
        """测试有效几何参数（SI单位）"""
        geom = ParshallFlumeGeometry(
            position=100.0,
            throat_width=0.5,
            crest_elevation=1.0,
            units='SI'
        )

        assert geom.position == 100.0
        assert geom.throat_width == 0.5
        assert geom.units == 'SI'

    def test_valid_geometry_Imperial(self):
        """测试有效几何参数（Imperial单位）"""
        geom = ParshallFlumeGeometry(
            position=100.0,
            throat_width=2.0,  # 2 ft
            units='Imperial'
        )

        assert geom.throat_width == 2.0
        assert geom.units == 'Imperial'

    def test_invalid_throat_width(self):
        """测试无效喉道宽度"""
        with pytest.raises(ValueError, match="must be positive"):
            ParshallFlumeGeometry(
                position=100.0,
                throat_width=0.0
            )

    def test_invalid_units(self):
        """测试无效单位系统"""
        with pytest.raises(ValueError, match="must be 'SI' or 'Imperial'"):
            ParshallFlumeGeometry(
                position=100.0,
                throat_width=1.0,
                units='Metric'
            )


class TestParshallFlumeCalculations:
    """测试巴歇尔槽流量计算"""

    def test_discharge_calculation_SI(self):
        """测试SI单位流量计算"""
        flume = create_parshall_flume(
            position=100.0,
            throat_width=0.5,  # 0.5 m
            units='SI'
        )

        Q, condition = flume.compute_discharge(H_upstream=0.3)

        # 流量应为正，条件为自由流
        assert Q > 0
        assert condition == 'free'

    def test_discharge_calculation_Imperial(self):
        """测试Imperial单位流量计算（1 ft喉道）"""
        flume = create_parshall_flume(
            position=100.0,
            throat_width=1.0,  # 1 ft
            units='Imperial'
        )

        Q, condition = flume.compute_discharge(H_upstream=0.5)  # 0.5 ft head

        # 1 ft巴歇尔槽: Q = 4.0 * H^1.522
        # Q = 4.0 * 0.5^1.522 ~= 4.0 * 0.348 ~= 1.39 ft^3/s
        assert 1.2 < Q < 1.6
        assert condition == 'free'

    def test_discharge_increases_with_head(self):
        """测试流量随水头增加"""
        flume = create_parshall_flume(position=100.0, throat_width=0.5, units='SI')

        Q1, _ = flume.compute_discharge(H_upstream=0.2)
        Q2, _ = flume.compute_discharge(H_upstream=0.4)
        Q3, _ = flume.compute_discharge(H_upstream=0.6)

        assert Q1 < Q2 < Q3

    def test_discharge_increases_with_throat_width(self):
        """测试流量随喉道宽度增加"""
        flume_narrow = create_parshall_flume(position=100.0, throat_width=0.3, units='SI')
        flume_wide = create_parshall_flume(position=100.0, throat_width=0.9, units='SI')

        Q_narrow, _ = flume_narrow.compute_discharge(H_upstream=0.3)
        Q_wide, _ = flume_wide.compute_discharge(H_upstream=0.3)

        # 宽喉道应有更大流量
        assert Q_wide > Q_narrow * 2.0

    def test_head_from_discharge(self):
        """测试反算水头"""
        flume = create_parshall_flume(position=100.0, throat_width=1.0, units='Imperial')

        # 正算
        H_target = 0.6
        Q, _ = flume.compute_discharge(H_upstream=H_target)

        # 反算
        H_computed = flume.compute_head(Q=Q)

        # 应该精确匹配
        assert abs(H_computed - H_target) < 0.001

    def test_submergence_check_free_flow(self):
        """测试自由流条件判别"""
        flume = create_parshall_flume(position=100.0, throat_width=1.0, units='Imperial')

        H_upstream = 0.5
        H_downstream = 0.25  # 低下游水位

        S, is_submerged = flume.check_submergence(H_upstream, H_downstream)

        # S = 0.25/0.5 = 0.5 < 0.7，应该是自由流
        assert S == 0.5
        assert is_submerged is False

    def test_submergence_check_submerged_flow(self):
        """测试淹没流条件判别"""
        flume = create_parshall_flume(position=100.0, throat_width=1.0, units='Imperial')

        H_upstream = 0.5
        H_downstream = 0.4  # 高下游水位

        S, is_submerged = flume.check_submergence(H_upstream, H_downstream)

        # S = 0.4/0.5 = 0.8 > 0.7，应该淹没
        assert S == 0.8
        assert is_submerged is True

    def test_standard_throat_widths_Imperial(self):
        """测试标准喉道宽度（Imperial）"""
        # 测试几个标准尺寸
        for W in [1.0, 2.0, 3.0, 4.0]:
            flume = create_parshall_flume(
                position=100.0,
                throat_width=W,
                units='Imperial'
            )

            Q, condition = flume.compute_discharge(H_upstream=0.5)

            # 流量应随喉道宽度增加
            assert Q > 0
            assert condition == 'free'


# ============================================================================
# 边界情况测试
# ============================================================================

class TestEdgeCases:
    """测试边界情况"""

    def test_zero_head_all_structures(self):
        """测试所有结构的零水头情况"""
        rect_weir = create_rectangular_weir(position=100.0, crest_width=2.0)
        tri_weir = create_triangular_weir(position=100.0, notch_angle=90.0)
        flume = create_parshall_flume(position=100.0, throat_width=1.0, units='Imperial')

        assert rect_weir.compute_discharge(h=0.0) == 0.0
        assert tri_weir.compute_discharge(h=0.0) == 0.0

        Q_flume, _ = flume.compute_discharge(H_upstream=0.0)
        assert Q_flume == 0.0

    def test_negative_head_handling(self):
        """测试负水头处理"""
        weir = create_rectangular_weir(position=100.0, crest_width=2.0)

        Q = weir.compute_discharge(h=-0.1)

        # 应该返回0或处理为0
        assert Q == 0.0

    def test_very_small_head(self):
        """测试极小水头"""
        tri_weir = create_triangular_weir(position=100.0, notch_angle=90.0)

        Q = tri_weir.compute_discharge(h=0.01)  # 1 cm

        # 三角堰对小水头敏感，应该有流量
        assert Q > 0
        assert Q < 0.001  # 但很小

    def test_large_head(self):
        """测试大水头"""
        rect_weir = create_rectangular_weir(position=100.0, crest_width=5.0)

        Q = rect_weir.compute_discharge(h=2.0)  # 2 m水头

        # 应该有大流量
        assert Q > 10.0  # 粗略检查


# ============================================================================
# 比较测试
# ============================================================================

class TestStructureComparisons:
    """测试不同结构的比较"""

    def test_rectangular_vs_triangular_small_flow(self):
        """测试矩形堰vs三角堰在小流量时的表现"""
        rect_weir = create_rectangular_weir(position=100.0, crest_width=1.0)
        tri_weir = create_triangular_weir(position=100.0, notch_angle=90.0)

        # 小水头
        h_small = 0.05  # 5 cm

        Q_rect = rect_weir.compute_discharge(h=h_small)
        Q_tri = tri_weir.compute_discharge(h=h_small)

        # 两者都应该有流量
        assert Q_rect > 0
        assert Q_tri > 0

        # 三角堰对小流量更敏感（更适合小流量测量）

    def test_precision_comparison(self):
        """测试不同结构的测量精度"""
        rect_weir = create_rectangular_weir(position=100.0, crest_width=2.0)
        tri_weir = create_triangular_weir(position=100.0, notch_angle=90.0)

        # 测试反算精度
        h_test = 0.3

        # 矩形堰
        Q_rect = rect_weir.compute_discharge(h=h_test)
        h_rect_back = rect_weir.compute_head(Q=Q_rect)

        # 三角堰
        Q_tri = tri_weir.compute_discharge(h=h_test)
        h_tri_back = tri_weir.compute_head(Q=Q_tri)

        # 两者反算精度都应该很好
        assert abs(h_rect_back - h_test) < 0.01
        assert abs(h_tri_back - h_test) < 0.001  # 三角堰直接公式，更精确


# ============================================================================
# 便捷函数测试
# ============================================================================

class TestConvenienceFunctions:
    """测试便捷函数"""

    def test_create_rectangular_weir(self):
        """测试创建矩形堰函数"""
        weir = create_rectangular_weir(
            position=100.0,
            crest_width=2.5,
            crest_elevation=5.0,
            channel_width=4.0
        )

        assert isinstance(weir, RectangularWeir)
        assert weir.geom.crest_width == 2.5
        assert weir.geom.crest_elevation == 5.0
        assert weir.geom.channel_width == 4.0

    def test_create_triangular_weir(self):
        """测试创建三角堰函数"""
        weir = create_triangular_weir(
            position=100.0,
            notch_angle=60.0,
            crest_elevation=3.0
        )

        assert isinstance(weir, TriangularWeir)
        assert weir.geom.notch_angle == 60.0
        assert weir.geom.crest_elevation == 3.0

    def test_create_parshall_flume(self):
        """测试创建巴歇尔槽函数"""
        flume = create_parshall_flume(
            position=100.0,
            throat_width=1.5,
            crest_elevation=2.0,
            units='Imperial'
        )

        assert isinstance(flume, ParshallFlume)
        assert flume.geom.throat_width == 1.5
        assert flume.geom.units == 'Imperial'
