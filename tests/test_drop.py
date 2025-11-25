"""
测试跌水结构水力计算

测试内容：
- 几何参数验证
- 自由流流量计算
- 淹没流流量计算
- 尾水深度计算
- 能量消散计算
- 临界水深计算
- 边界情况处理

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
from physics.structures import Drop, DropGeometry, create_drop_structure


class TestDropGeometry:
    """测试跌水几何参数"""

    def test_valid_geometry(self):
        """测试有效几何参数"""
        geom = DropGeometry(
            position=100.0,
            width=5.0,
            drop_height=2.0,
            crest_elevation=10.0,
            shape='sharp'
        )

        assert geom.position == 100.0
        assert geom.width == 5.0
        assert geom.drop_height == 2.0
        assert geom.crest_elevation == 10.0
        assert geom.shape == 'sharp'

    def test_invalid_width(self):
        """测试无效宽度"""
        with pytest.raises(ValueError, match="width must be positive"):
            DropGeometry(
                position=100.0,
                width=0.0,
                drop_height=2.0
            )

    def test_invalid_drop_height(self):
        """测试无效跌水高度"""
        with pytest.raises(ValueError, match="height must be non-negative"):
            DropGeometry(
                position=100.0,
                width=5.0,
                drop_height=-1.0
            )

    def test_invalid_shape(self):
        """测试无效跌水形式"""
        with pytest.raises(ValueError, match="must be"):
            DropGeometry(
                position=100.0,
                width=5.0,
                drop_height=2.0,
                shape='invalid'
            )


class TestFreeFlowCalculations:
    """测试自由流计算"""

    def test_free_flow_discharge(self):
        """测试自由流流量计算"""
        drop = create_drop_structure(
            position=100.0,
            width=5.0,
            drop_height=2.0,
            shape='sharp'
        )

        Q, flow_type = drop.compute_discharge(
            h_upstream=1.0,
            h_downstream=0.5
        )

        # 验证流态
        assert flow_type == 'free'

        # 验证流量在合理范围
        # Q = Cd * b * H^1.5 * sqrt(2g)
        # Q = 0.4 * 5 * 1^1.5 * sqrt(2*9.81) ~= 8.86 m^3/s
        assert 8.0 < Q < 10.0

    def test_free_flow_increases_with_head(self):
        """测试流量随水头增加"""
        drop = create_drop_structure(
            position=100.0,
            width=5.0,
            drop_height=2.0,
            shape='broad'
        )

        Q1, _ = drop.compute_discharge(h_upstream=0.5, h_downstream=0.2)
        Q2, _ = drop.compute_discharge(h_upstream=1.0, h_downstream=0.2)
        Q3, _ = drop.compute_discharge(h_upstream=1.5, h_downstream=0.2)

        assert Q1 < Q2 < Q3

    def test_discharge_coefficients(self):
        """测试不同跌水类型的流量系数"""
        # 锐缘跌水
        drop_sharp = create_drop_structure(
            position=100.0, width=5.0, drop_height=2.0, shape='sharp'
        )
        assert drop_sharp.Cd == 0.40

        # 宽顶堰
        drop_broad = create_drop_structure(
            position=100.0, width=5.0, drop_height=2.0, shape='broad'
        )
        assert drop_broad.Cd == 0.55

        # 曲线堰
        drop_ogee = create_drop_structure(
            position=100.0, width=5.0, drop_height=2.0, shape='ogee'
        )
        assert drop_ogee.Cd == 0.48

        # 在相同条件下，宽顶堰流量最大
        Q_sharp, _ = drop_sharp.compute_discharge(1.0, 0.3)
        Q_broad, _ = drop_broad.compute_discharge(1.0, 0.3)
        Q_ogee, _ = drop_ogee.compute_discharge(1.0, 0.3)

        assert Q_sharp < Q_ogee < Q_broad


class TestSubmergedFlowCalculations:
    """测试淹没流计算"""

    def test_submerged_flow_detection(self):
        """测试淹没流判别"""
        drop = create_drop_structure(
            position=100.0,
            width=5.0,
            drop_height=1.0,
            shape='sharp'
        )

        # 高下游水位应该导致淹没流
        Q, flow_type = drop.compute_discharge(
            h_upstream=1.0,
            h_downstream=1.5  # 高下游水位
        )

        assert flow_type == 'submerged'

    def test_submerged_flow_reduced_discharge(self):
        """测试淹没流流量减小"""
        drop = create_drop_structure(
            position=100.0,
            width=5.0,
            drop_height=1.0,
            shape='sharp'
        )

        # 自由流
        Q_free, _ = drop.compute_discharge(h_upstream=1.0, h_downstream=0.3)

        # 淹没流
        Q_submerged, _ = drop.compute_discharge(h_upstream=1.0, h_downstream=1.5)

        # 淹没流流量应小于自由流
        assert Q_submerged < Q_free


class TestCriticalDepthCalculations:
    """测试临界水深计算"""

    def test_critical_depth(self):
        """测试临界水深计算"""
        drop = create_drop_structure(
            position=100.0,
            width=5.0,
            drop_height=2.0
        )

        Q = 10.0
        hc = drop.compute_critical_depth(Q)

        # 验证临界水深公式: hc = (q^2/g)^(1/3)
        q = Q / drop.geom.width  # = 2.0 m^2/s
        hc_expected = (q ** 2 / drop.g) ** (1.0 / 3.0)

        assert abs(hc - hc_expected) < 0.001

    def test_critical_depth_increases_with_discharge(self):
        """测试临界水深随流量增加"""
        drop = create_drop_structure(
            position=100.0,
            width=5.0,
            drop_height=2.0
        )

        hc1 = drop.compute_critical_depth(Q=5.0)
        hc2 = drop.compute_critical_depth(Q=10.0)
        hc3 = drop.compute_critical_depth(Q=15.0)

        assert hc1 < hc2 < hc3


class TestTailwaterDepthCalculations:
    """测试尾水深度计算"""

    def test_tailwater_depth_positive(self):
        """测试尾水深度为正"""
        drop = create_drop_structure(
            position=100.0,
            width=5.0,
            drop_height=2.0
        )

        h_tail = drop.compute_tailwater_depth(Q=10.0, h_upstream=1.0)

        assert h_tail > 0

    def test_tailwater_depth_increases_with_discharge(self):
        """测试尾水深度随流量增加"""
        drop = create_drop_structure(
            position=100.0,
            width=5.0,
            drop_height=2.0
        )

        h1 = drop.compute_tailwater_depth(Q=5.0, h_upstream=1.0)
        h2 = drop.compute_tailwater_depth(Q=10.0, h_upstream=1.0)
        h3 = drop.compute_tailwater_depth(Q=15.0, h_upstream=1.0)

        assert h1 < h2 < h3


class TestEnergyDissipation:
    """测试能量消散计算"""

    def test_energy_dissipation_positive(self):
        """测试能量消散为正"""
        drop = create_drop_structure(
            position=100.0,
            width=5.0,
            drop_height=2.0,
            crest_elevation=10.0
        )

        E_loss = drop.compute_energy_dissipation(
            Q=10.0,
            h_upstream=1.0,
            h_downstream=0.8
        )

        # 跌水应该消耗能量
        assert E_loss > 0

    def test_energy_dissipation_increases_with_drop_height(self):
        """测试能量消散随跌水高度增加"""
        drop1 = create_drop_structure(
            position=100.0, width=5.0, drop_height=1.0
        )
        drop2 = create_drop_structure(
            position=100.0, width=5.0, drop_height=2.0
        )
        drop3 = create_drop_structure(
            position=100.0, width=5.0, drop_height=3.0
        )

        E1 = drop1.compute_energy_dissipation(Q=10.0, h_upstream=1.0, h_downstream=0.8)
        E2 = drop2.compute_energy_dissipation(Q=10.0, h_upstream=1.0, h_downstream=0.8)
        E3 = drop3.compute_energy_dissipation(Q=10.0, h_upstream=1.0, h_downstream=0.8)

        # 跌水高度越大，能量消散越大
        assert E1 < E2 < E3

    def test_head_loss_method(self):
        """测试head_loss方法与energy_dissipation一致"""
        drop = create_drop_structure(
            position=100.0,
            width=5.0,
            drop_height=2.0
        )

        E_loss = drop.compute_energy_dissipation(Q=10.0, h_upstream=1.0, h_downstream=0.8)
        h_loss = drop.compute_head_loss(Q=10.0, h_upstream=1.0, h_downstream=0.8)

        assert abs(E_loss - h_loss) < 0.001


class TestEdgeCases:
    """测试边界情况"""

    def test_zero_upstream_head(self):
        """测试零上游水头"""
        drop = create_drop_structure(
            position=100.0,
            width=5.0,
            drop_height=2.0
        )

        Q, flow_type = drop.compute_discharge(h_upstream=0.0, h_downstream=0.5)

        assert Q == 0.0
        assert flow_type == 'free'

    def test_negative_upstream_head(self):
        """测试负上游水头"""
        drop = create_drop_structure(
            position=100.0,
            width=5.0,
            drop_height=2.0
        )

        Q, flow_type = drop.compute_discharge(h_upstream=-0.5, h_downstream=0.5)

        assert Q == 0.0

    def test_very_small_discharge(self):
        """测试极小流量"""
        drop = create_drop_structure(
            position=100.0,
            width=5.0,
            drop_height=2.0
        )

        Q, _ = drop.compute_discharge(h_upstream=0.01, h_downstream=0.0)

        # 应该有流量但很小
        assert Q > 0
        assert Q < 0.1

    def test_wide_drop(self):
        """测试宽跌水"""
        drop = create_drop_structure(
            position=100.0,
            width=20.0,  # 宽跌水
            drop_height=1.0
        )

        Q, flow_type = drop.compute_discharge(h_upstream=1.0, h_downstream=0.5)

        # 宽跌水应该有更大流量
        assert Q > 20.0  # 粗略检查
        assert flow_type == 'free'

    def test_custom_discharge_coefficient(self):
        """测试自定义流量系数"""
        geom = DropGeometry(
            position=100.0,
            width=5.0,
            drop_height=2.0,
            shape='sharp'
        )

        drop_custom = Drop(geom, discharge_coef=0.50)

        assert drop_custom.Cd == 0.50


class TestValidation:
    """验证计算与理论值对比"""

    def test_weir_equation_validation(self):
        """验证堰流公式"""
        # 使用标准条件验证
        drop = create_drop_structure(
            position=100.0,
            width=1.0,  # 单位宽度
            drop_height=1.0,
            shape='sharp'  # Cd = 0.4
        )

        H = 0.5  # m
        Q, flow_type = drop.compute_discharge(h_upstream=H, h_downstream=0.1)

        # 理论流量: Q = Cd * b * H^1.5 * sqrt(2g)
        Q_theory = 0.4 * 1.0 * (0.5 ** 1.5) * np.sqrt(2 * 9.81)
        # Q_theory ~= 0.628 m^3/s

        assert flow_type == 'free'
        assert abs(Q - Q_theory) / Q_theory < 0.01  # 1%误差

    def test_energy_conservation_check(self):
        """验证能量守恒（考虑损失）"""
        drop = create_drop_structure(
            position=100.0,
            width=5.0,
            drop_height=2.0,
            crest_elevation=10.0
        )

        Q = 10.0
        h_up = 1.0
        h_down = 0.8

        # 计算能量损失
        E_loss = drop.compute_energy_dissipation(Q, h_up, h_down)

        # 上游比能
        A_up = drop.geom.width * h_up
        V_up = Q / A_up
        E_up = h_up + V_up ** 2 / (2 * drop.g) + drop.geom.crest_elevation

        # 下游比能（相对于跌水后河底）
        A_down = drop.geom.width * h_down
        V_down = Q / A_down
        downstream_bed = drop.geom.crest_elevation - drop.geom.drop_height
        E_down = h_down + V_down ** 2 / (2 * drop.g) + downstream_bed

        # 能量损失应该等于上下游能量差
        E_diff = E_up - E_down

        assert abs(E_loss - E_diff) < 0.01


class TestConvenienceFunctions:
    """测试便捷函数"""

    def test_create_drop_structure(self):
        """测试create_drop_structure函数"""
        drop = create_drop_structure(
            position=100.0,
            width=5.0,
            drop_height=2.0,
            crest_elevation=10.0,
            shape='broad'
        )

        assert isinstance(drop, Drop)
        assert drop.geom.position == 100.0
        assert drop.geom.width == 5.0
        assert drop.geom.drop_height == 2.0
        assert drop.geom.crest_elevation == 10.0
        assert drop.geom.shape == 'broad'
        assert drop.Cd == 0.55  # broad coefficient
