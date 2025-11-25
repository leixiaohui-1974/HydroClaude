#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
桥梁水工建筑物单元测试

测试 Bridge 类的各项功能，包括：
1. 基本初始化和参数验证
2. 流态判断（自由流/压力流）
3. 堰流计算
4. 自由孔流计算
5. 压力流计算
6. 壅水效应计算
7. 边界条件和极端情况

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

from network.bridge_structure import Bridge, create_bridge


class TestBridgeInitialization:
    """测试桥梁初始化和参数验证"""

    def test_basic_initialization(self):
        """测试基本初始化"""
        bridge = Bridge(
            bridge_id="BR001",
            total_width=30.0,
            opening_height=5.0,
            bottom_elevation=100.0,
            n_piers=2,
            pier_width=1.5
        )

        assert bridge.bridge_id == "BR001"
        assert bridge.total_width == 30.0
        assert bridge.H_opening == 5.0
        assert bridge.z_bottom == 100.0
        assert bridge.z_deck == 105.0  # 100 + 5
        assert bridge.n_piers == 2
        assert bridge.pier_width == 1.5
        assert bridge.W_effective == 27.0  # 30 - 2*1.5

    def test_no_piers(self):
        """测试无桥墩情况"""
        bridge = Bridge(
            bridge_id="BR002",
            total_width=25.0,
            opening_height=4.0,
            bottom_elevation=98.0
        )

        assert bridge.n_piers == 0
        assert bridge.pier_width == 0.0
        assert bridge.W_effective == 25.0

    def test_default_coefficients(self):
        """测试默认流量系数"""
        bridge = Bridge(
            bridge_id="BR003",
            total_width=20.0,
            opening_height=3.0,
            bottom_elevation=95.0
        )

        assert bridge.Cd_weir == 0.5
        assert bridge.Cd_orifice == 0.7
        assert bridge.Cd_pressure == 0.8

    def test_custom_coefficients(self):
        """测试自定义流量系数"""
        bridge = Bridge(
            bridge_id="BR004",
            total_width=20.0,
            opening_height=3.0,
            bottom_elevation=95.0,
            Cd_weir=0.45,
            Cd_orifice=0.65,
            Cd_pressure=0.75
        )

        assert bridge.Cd_weir == 0.45
        assert bridge.Cd_orifice == 0.65
        assert bridge.Cd_pressure == 0.75

    def test_invalid_width(self):
        """测试无效宽度"""
        with pytest.raises(ValueError, match="total_width must be > 0"):
            Bridge(
                bridge_id="BR_INVALID",
                total_width=-10.0,
                opening_height=3.0,
                bottom_elevation=100.0
            )

    def test_invalid_height(self):
        """测试无效高度"""
        with pytest.raises(ValueError, match="opening_height must be > 0"):
            Bridge(
                bridge_id="BR_INVALID",
                total_width=20.0,
                opening_height=0.0,
                bottom_elevation=100.0
            )

    def test_invalid_pier_configuration(self):
        """测试无效桥墩配置（桥墩总宽 >= 桥孔宽）"""
        with pytest.raises(ValueError, match="Total pier width"):
            Bridge(
                bridge_id="BR_INVALID",
                total_width=10.0,
                opening_height=3.0,
                bottom_elevation=100.0,
                n_piers=5,
                pier_width=2.5  # 5 * 2.5 = 12.5 > 10.0
            )

    def test_invalid_coefficient_range(self):
        """测试无效流量系数范围"""
        with pytest.raises(ValueError, match="Cd_weir must be in"):
            Bridge(
                bridge_id="BR_INVALID",
                total_width=20.0,
                opening_height=3.0,
                bottom_elevation=100.0,
                Cd_weir=1.5  # > 1.0
            )

    def test_create_bridge_helper(self):
        """测试便捷创建函数"""
        bridge = create_bridge(
            bridge_id="BR005",
            total_width=35.0,
            opening_height=6.0,
            bottom_elevation=102.0,
            n_piers=3,
            pier_width=1.0
        )

        assert isinstance(bridge, Bridge)
        assert bridge.bridge_id == "BR005"
        assert bridge.W_effective == 32.0  # 35 - 3*1


class TestFlowRegimeClassification:
    """测试流态判断"""

    def setup_method(self):
        """设置测试桥梁"""
        self.bridge = Bridge(
            bridge_id="BR_TEST",
            total_width=30.0,
            opening_height=5.0,
            bottom_elevation=100.0,
            n_piers=0
        )
        # z_bottom = 100.0 m
        # z_deck = 105.0 m

    def test_free_flow_weir_regime(self):
        """测试自由堰流（上游水位较低）"""
        h_up = 102.0  # 桥底上 2m，< 0.8 * H_opening = 4.0m
        h_down = 101.0

        regime = self.bridge.classify_flow_regime(h_up, h_down)
        assert regime == "free_flow_weir"

    def test_free_flow_orifice_regime(self):
        """测试自由孔流（上游水位较高但下游未淹没）"""
        h_up = 104.5  # 桥底上 4.5m，> 0.8 * 5.0 = 4.0m
        h_down = 102.0  # < z_deck = 105.0

        regime = self.bridge.classify_flow_regime(h_up, h_down)
        assert regime == "free_flow_orifice"

    def test_pressure_flow_regime(self):
        """测试压力流（下游淹没桥面）"""
        h_up = 107.0
        h_down = 106.0  # > z_deck = 105.0

        regime = self.bridge.classify_flow_regime(h_up, h_down)
        assert regime == "pressure_flow"

    def test_regime_transition_boundary(self):
        """测试流态转换边界"""
        # 边界1：自由流 -> 压力流
        h_up = 107.0
        h_down_free = 104.9  # < z_deck
        h_down_pressure = 105.1  # > z_deck

        regime_free = self.bridge.classify_flow_regime(h_up, h_down_free)
        regime_pressure = self.bridge.classify_flow_regime(h_up, h_down_pressure)

        assert regime_free == "free_flow_orifice"
        assert regime_pressure == "pressure_flow"


class TestWeirFlow:
    """测试堰流计算"""

    def setup_method(self):
        """设置测试桥梁"""
        self.bridge = Bridge(
            bridge_id="BR_WEIR",
            total_width=20.0,
            opening_height=4.0,
            bottom_elevation=100.0,
            Cd_weir=0.5
        )

    def test_weir_flow_basic(self):
        """测试基本堰流计算"""
        h_up = 101.0  # 堰顶水头 1.0 m
        h_down = 100.5

        result = self.bridge.compute_discharge(h_up, h_down)

        # Q = Cd * B * h^(3/2) * √(2g)
        # Q = 0.5 * 20.0 * 1.0^1.5 * √(2*9.81)
        Q_expected = 0.5 * 20.0 * (1.0 ** 1.5) * np.sqrt(2 * 9.81)

        assert result['regime'] == "free_flow_weir"
        assert np.isclose(result['Q'], Q_expected, rtol=0.01)
        assert result['Q'] > 0

    def test_weir_flow_varying_head(self):
        """测试不同堰顶水头"""
        h_down = 100.5
        heads = [0.5, 1.0, 1.5, 2.0, 2.5]

        Q_prev = 0.0
        for h in heads:
            h_up = self.bridge.z_bottom + h
            result = self.bridge.compute_discharge(h_up, h_down)

            # 流量应随水头增加而增加（非线性）
            assert result['Q'] > Q_prev
            Q_prev = result['Q']

            # 验证堰流公式 Q ∝ h^(3/2)
            Q_expected = 0.5 * 20.0 * (h ** 1.5) * np.sqrt(2 * 9.81)
            assert np.isclose(result['Q'], Q_expected, rtol=0.01)

    def test_weir_flow_zero_head(self):
        """测试零水头情况"""
        h_up = self.bridge.z_bottom  # 刚好在桥底
        h_down = 99.5

        result = self.bridge.compute_discharge(h_up, h_down)
        assert result['Q'] == 0.0


class TestFreeOrificeFlow:
    """测试自由孔流计算"""

    def setup_method(self):
        """设置测试桥梁"""
        self.bridge = Bridge(
            bridge_id="BR_ORIFICE",
            total_width=25.0,
            opening_height=5.0,
            bottom_elevation=100.0,
            Cd_orifice=0.7
        )
        # z_deck = 105.0 m

    def test_free_orifice_flow_basic(self):
        """测试基本自由孔流"""
        h_up = 106.0  # 桥面上 1m
        h_down = 103.0  # 桥面下

        result = self.bridge.compute_discharge(h_up, h_down)

        # Q = Cd * A * √(2g * Δh)
        # Δh = h_up - z_deck = 106 - 105 = 1.0 m
        A = 25.0 * 5.0
        dh = h_up - self.bridge.z_deck
        Q_expected = 0.7 * A * np.sqrt(2 * 9.81 * dh)

        assert result['regime'] == "free_flow_orifice"
        assert np.isclose(result['Q'], Q_expected, rtol=0.01)

    def test_free_orifice_flow_varying_head_difference(self):
        """测试不同水头差"""
        h_down = 103.0
        dh_values = [0.5, 1.0, 2.0, 3.0, 4.0]

        Q_prev = 0.0
        for dh in dh_values:
            h_up = self.bridge.z_deck + dh
            result = self.bridge.compute_discharge(h_up, h_down)

            # 流量应随水头差增加而增加
            assert result['Q'] > Q_prev
            Q_prev = result['Q']

            # 验证孔流公式 Q ∝ √(Δh)
            A = 25.0 * 5.0
            Q_expected = 0.7 * A * np.sqrt(2 * 9.81 * dh)
            assert np.isclose(result['Q'], Q_expected, rtol=0.01)


class TestPressureFlow:
    """测试压力流计算"""

    def setup_method(self):
        """设置测试桥梁"""
        self.bridge = Bridge(
            bridge_id="BR_PRESSURE",
            total_width=30.0,
            opening_height=6.0,
            bottom_elevation=100.0,
            n_piers=2,
            pier_width=1.5,
            Cd_pressure=0.8
        )
        # z_deck = 106.0 m
        # W_effective = 27.0 m

    def test_pressure_flow_basic(self):
        """测试基本压力流"""
        h_up = 108.0
        h_down = 107.0  # > z_deck = 106.0

        result = self.bridge.compute_discharge(h_up, h_down)

        # Q = Cd * A * √(2g * Δh)
        # Δh = h_up - h_down = 1.0 m
        A = 27.0 * 6.0
        dh = h_up - h_down
        Q_expected = 0.8 * A * np.sqrt(2 * 9.81 * dh)

        assert result['regime'] == "pressure_flow"
        assert np.isclose(result['Q'], Q_expected, rtol=0.01)

    def test_pressure_flow_varying_head_difference(self):
        """测试不同压力差"""
        dh_values = [0.2, 0.5, 1.0, 1.5, 2.0]

        Q_prev = 0.0
        for dh in dh_values:
            h_up = 108.0
            h_down = h_up - dh
            result = self.bridge.compute_discharge(h_up, h_down)

            # 流量应随水头差增加而增加
            assert result['Q'] > Q_prev
            Q_prev = result['Q']

            # 验证压力流公式
            A = 27.0 * 6.0
            Q_expected = 0.8 * A * np.sqrt(2 * 9.81 * dh)
            assert np.isclose(result['Q'], Q_expected, rtol=0.01)

    def test_pressure_flow_zero_head_difference(self):
        """测试零水头差（平衡状态）"""
        h_up = 107.0
        h_down = 107.0

        result = self.bridge.compute_discharge(h_up, h_down)
        assert result['Q'] == 0.0


class TestBackwaterEffect:
    """测试壅水效应计算"""

    def setup_method(self):
        """设置测试桥梁"""
        self.bridge = Bridge(
            bridge_id="BR_BACKWATER",
            total_width=25.0,
            opening_height=5.0,
            bottom_elevation=100.0,
            Cd_pressure=0.8
        )

    def test_backwater_iterative_method(self):
        """测试迭代法壅水计算"""
        Q = 100.0  # 给定流量
        h_down = 106.0  # 下游水位

        # 反推上游水位
        h_up_computed = self.bridge.compute_backwater_effect(
            Q, h_down, method='iterative'
        )

        # 验证：用计算的上游水位正推流量，应该接近给定流量
        result = self.bridge.compute_discharge(h_up_computed, h_down)
        Q_check = result['Q']

        assert np.isclose(Q_check, Q, rtol=0.01)
        assert h_up_computed > h_down  # 上游水位应高于下游

    def test_backwater_analytical_method(self):
        """测试解析法壅水计算（压力流近似）"""
        Q = 150.0
        h_down = 107.0

        h_up_analytical = self.bridge.compute_backwater_effect(
            Q, h_down, method='analytical'
        )

        # 验证解析解
        A = 25.0 * 5.0
        dh_expected = (Q / (0.8 * A)) ** 2 / (2 * 9.81)
        h_up_expected = h_down + dh_expected

        assert np.isclose(h_up_analytical, h_up_expected, rtol=0.01)

    def test_backwater_comparison(self):
        """测试迭代法和解析法对比（压力流情况应相近）"""
        Q = 120.0
        h_down = 106.5

        h_up_iterative = self.bridge.compute_backwater_effect(
            Q, h_down, method='iterative'
        )
        h_up_analytical = self.bridge.compute_backwater_effect(
            Q, h_down, method='analytical'
        )

        # 压力流情况下，两种方法结果应接近（< 10% 差异）
        assert np.isclose(h_up_iterative, h_up_analytical, rtol=0.1)

    def test_backwater_zero_flow(self):
        """测试零流量壅水"""
        Q = 0.0
        h_down = 105.0

        h_up = self.bridge.compute_backwater_effect(Q, h_down)

        # 零流量时，上下游水位应相等
        assert np.isclose(h_up, h_down, atol=1e-6)


class TestDischargeComponents:
    """测试流量计算的完整输出"""

    def setup_method(self):
        """设置测试桥梁"""
        self.bridge = Bridge(
            bridge_id="BR_FULL",
            total_width=28.0,
            opening_height=5.5,
            bottom_elevation=100.0,
            n_piers=1,
            pier_width=2.0
        )
        # W_effective = 26.0 m

    def test_discharge_output_structure(self):
        """测试流量计算输出结构"""
        h_up = 107.0
        h_down = 106.0

        result = self.bridge.compute_discharge(h_up, h_down)

        # 检查输出包含所有必需字段
        assert 'Q' in result
        assert 'regime' in result
        assert 'velocity' in result
        assert 'head_loss' in result

        assert isinstance(result['Q'], (int, float))
        assert isinstance(result['regime'], str)
        assert isinstance(result['velocity'], (int, float))
        assert isinstance(result['head_loss'], (int, float))

    def test_velocity_calculation(self):
        """测试流速计算"""
        h_up = 106.0
        h_down = 105.0

        result = self.bridge.compute_discharge(h_up, h_down)

        # v = Q / A
        A = 26.0 * 5.5
        v_expected = result['Q'] / A

        assert np.isclose(result['velocity'], v_expected, rtol=0.01)
        assert result['velocity'] > 0

    def test_head_loss_calculation(self):
        """测试水头损失计算"""
        h_up = 108.0
        h_down = 106.5

        result = self.bridge.compute_discharge(h_up, h_down)

        # 水头损失 = 上游水位 - 下游水位
        head_loss_expected = h_up - h_down

        assert np.isclose(result['head_loss'], head_loss_expected, rtol=0.01)
        assert result['head_loss'] >= 0


class TestBridgeProperties:
    """测试桥梁属性查询"""

    def test_properties_output(self):
        """测试属性输出"""
        bridge = Bridge(
            bridge_id="BR_PROP",
            total_width=32.0,
            opening_height=6.0,
            bottom_elevation=98.0,
            n_piers=3,
            pier_width=1.2,
            Cd_weir=0.48,
            Cd_orifice=0.68,
            Cd_pressure=0.78
        )

        props = bridge.properties()

        assert props['total_width'] == 32.0
        assert np.isclose(props['effective_width'], 28.4)  # 32 - 3*1.2
        assert props['opening_height'] == 6.0
        assert props['bottom_elevation'] == 98.0
        assert props['deck_elevation'] == 104.0
        assert props['n_piers'] == 3
        assert props['pier_width'] == 1.2
        assert np.isclose(props['total_pier_width'], 3.6)
        assert np.isclose(props['opening_area'], 28.4 * 6.0)
        assert props['Cd_weir'] == 0.48
        assert props['Cd_orifice'] == 0.68
        assert props['Cd_pressure'] == 0.78


class TestEdgeCases:
    """测试边界条件和极端情况"""

    def test_upstream_below_bridge_bottom(self):
        """测试上游水位低于桥底（应报错）"""
        bridge = Bridge(
            bridge_id="BR_EDGE",
            total_width=20.0,
            opening_height=4.0,
            bottom_elevation=100.0
        )

        h_up = 99.0  # < z_bottom = 100.0
        h_down = 98.0

        with pytest.raises(ValueError, match="below bridge bottom"):
            bridge.compute_discharge(h_up, h_down)

    def test_very_small_head_difference(self):
        """测试极小水头差"""
        bridge = Bridge(
            bridge_id="BR_SMALL",
            total_width=25.0,
            opening_height=5.0,
            bottom_elevation=100.0
        )

        h_up = 106.001
        h_down = 106.0  # 压力流，水头差 0.001 m

        result = bridge.compute_discharge(h_up, h_down)

        assert result['regime'] == "pressure_flow"
        assert result['Q'] > 0
        assert result['Q'] < 20.0  # 小水头差但大断面，流量仍可能较大

    def test_large_head_difference(self):
        """测试大水头差（洪水情况）"""
        bridge = Bridge(
            bridge_id="BR_LARGE",
            total_width=30.0,
            opening_height=6.0,
            bottom_elevation=100.0
        )

        h_up = 115.0  # 桥面上 9m
        h_down = 107.0

        result = bridge.compute_discharge(h_up, h_down)

        assert result['regime'] == "pressure_flow"
        assert result['Q'] > 500.0  # 应该很大
        assert result['head_loss'] == 8.0

    def test_repr_string(self):
        """测试字符串表示"""
        bridge = Bridge(
            bridge_id="BR_STR",
            total_width=25.0,
            opening_height=5.0,
            bottom_elevation=100.0,
            n_piers=2,
            pier_width=1.0
        )

        repr_str = repr(bridge)

        assert "BR_STR" in repr_str
        assert "23.00" in repr_str  # W_effective = 25 - 2*1
        assert "5.00" in repr_str   # H_opening
        assert "n_piers=2" in repr_str


class TestPierEffects:
    """测试桥墩对过流能力的影响"""

    def test_piers_reduce_effective_width(self):
        """测试桥墩减小有效宽度"""
        # 无桥墩
        bridge_no_piers = Bridge(
            bridge_id="BR_NO_PIER",
            total_width=30.0,
            opening_height=5.0,
            bottom_elevation=100.0,
            n_piers=0
        )

        # 有桥墩
        bridge_with_piers = Bridge(
            bridge_id="BR_WITH_PIER",
            total_width=30.0,
            opening_height=5.0,
            bottom_elevation=100.0,
            n_piers=3,
            pier_width=1.5
        )

        h_up = 107.0
        h_down = 106.0

        Q_no_piers = bridge_no_piers.compute_discharge(h_up, h_down)['Q']
        Q_with_piers = bridge_with_piers.compute_discharge(h_up, h_down)['Q']

        # 有桥墩时流量应减小
        assert Q_with_piers < Q_no_piers

        # 流量比应等于有效宽度比（压力流情况）
        width_ratio = bridge_with_piers.W_effective / bridge_no_piers.W_effective
        Q_ratio = Q_with_piers / Q_no_piers

        assert np.isclose(Q_ratio, width_ratio, rtol=0.01)


class TestCoefficientSensitivity:
    """测试流量系数敏感性"""

    def test_weir_coefficient_sensitivity(self):
        """测试堰流系数对流量的影响"""
        h_up = 102.0
        h_down = 101.0

        Cd_values = [0.4, 0.5, 0.6]
        Q_values = []

        for Cd in Cd_values:
            bridge = Bridge(
                bridge_id="BR_CD",
                total_width=20.0,
                opening_height=5.0,
                bottom_elevation=100.0,
                Cd_weir=Cd
            )
            result = bridge.compute_discharge(h_up, h_down)
            Q_values.append(result['Q'])

        # 流量应与 Cd 成正比
        assert Q_values[1] / Q_values[0] == pytest.approx(0.5 / 0.4, rel=0.01)
        assert Q_values[2] / Q_values[1] == pytest.approx(0.6 / 0.5, rel=0.01)

    def test_pressure_coefficient_sensitivity(self):
        """测试压力流系数对流量的影响"""
        h_up = 108.0
        h_down = 107.0

        Cd_values = [0.7, 0.8, 0.9]
        Q_values = []

        for Cd in Cd_values:
            bridge = Bridge(
                bridge_id="BR_CD_P",
                total_width=25.0,
                opening_height=5.0,
                bottom_elevation=100.0,
                Cd_pressure=Cd
            )
            result = bridge.compute_discharge(h_up, h_down)
            Q_values.append(result['Q'])

        # 流量应与 Cd 成正比
        assert Q_values[1] / Q_values[0] == pytest.approx(0.8 / 0.7, rel=0.01)
        assert Q_values[2] / Q_values[1] == pytest.approx(0.9 / 0.8, rel=0.01)


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
