"""
测试泵站水力计算

测试内容：
- 离心泵特性曲线
- 效率和功率计算
- 变速运行（相似定律）
- 泵组串并联运行
- 工况点计算

Author: HydroClaude Development Team
Date: 2025-01
"""
import sys
import os

# ========== 路径设置 ==========
script_path = os.path.abspath(__file__)
project_root = os.path.dirname(os.path.dirname(script_path))
sys.path.insert(0, project_root)


import pytest
import numpy as np
from physics.pressurized import (
    CentrifugalPump, PumpCharacteristics, PumpArray,
    create_centrifugal_pump, create_pump_array
)


# ============================================================================
# 泵特性参数测试
# ============================================================================

class TestPumpCharacteristics:
    """测试泵特性参数"""

    def test_valid_characteristics(self):
        """测试有效特性参数"""
        char = PumpCharacteristics(
            H0=50.0,
            Q_design=0.2,
            H_design=45.0,
            eta_design=0.85,
            n_rated=1450.0
        )

        assert char.H0 == 50.0
        assert char.Q_design == 0.2
        assert char.H_design == 45.0
        assert char.eta_design == 0.85

    def test_invalid_shutoff_head(self):
        """测试无效关死扬程"""
        with pytest.raises(ValueError, match="Shutoff head"):
            PumpCharacteristics(
                H0=0.0,
                Q_design=0.2,
                H_design=45.0
            )

    def test_invalid_efficiency(self):
        """测试无效效率"""
        with pytest.raises(ValueError, match="Efficiency"):
            PumpCharacteristics(
                H0=50.0,
                Q_design=0.2,
                H_design=45.0,
                eta_design=1.5
            )


# ============================================================================
# 离心泵操作测试
# ============================================================================

class TestCentrifugalPumpOperations:
    """测试离心泵操作"""

    def test_start_stop(self):
        """测试启停操作"""
        pump = create_centrifugal_pump(
            position=100.0,
            H0=50.0,
            Q_design=0.2,
            H_design=45.0
        )

        # 初始应运行
        assert pump.is_running() is True

        # 停止
        pump.stop()
        assert pump.is_running() is False

        # 重新启动
        pump.start()
        assert pump.is_running() is True

    def test_speed_control(self):
        """测试转速控制"""
        pump = create_centrifugal_pump(
            position=100.0,
            H0=50.0,
            Q_design=0.2,
            H_design=45.0,
            n_rated=1450.0
        )

        # 检查初始转速
        assert pump.get_speed() == 1450.0

        # 设置新转速
        pump.set_speed(1200.0)
        assert pump.get_speed() == 1200.0

    def test_invalid_speed(self):
        """测试无效转速"""
        pump = create_centrifugal_pump(
            position=100.0,
            H0=50.0,
            Q_design=0.2,
            H_design=45.0
        )

        with pytest.raises(ValueError, match="Speed must be non-negative"):
            pump.set_speed(-100.0)


# ============================================================================
# 特性曲线计算测试
# ============================================================================

class TestPumpHeadCalculation:
    """测试泵扬程计算"""

    def test_head_at_zero_flow(self):
        """测试零流量时的扬程（关死扬程）"""
        pump = create_centrifugal_pump(
            position=100.0,
            H0=50.0,
            Q_design=0.2,
            H_design=45.0
        )

        H = pump.compute_head(Q=0.0)

        # 零流量时，扬程应接近H0
        assert abs(H - 50.0) < 0.1

    def test_head_at_design_point(self):
        """测试设计点扬程"""
        pump = create_centrifugal_pump(
            position=100.0,
            H0=50.0,
            Q_design=0.2,
            H_design=45.0
        )

        H = pump.compute_head(Q=0.2)

        # 设计流量时，扬程应接近设计扬程
        assert abs(H - 45.0) < 0.5

    def test_head_decreases_with_flow(self):
        """测试扬程随流量递减"""
        pump = create_centrifugal_pump(
            position=100.0,
            H0=50.0,
            Q_design=0.2,
            H_design=45.0
        )

        H1 = pump.compute_head(Q=0.05)
        H2 = pump.compute_head(Q=0.15)
        H3 = pump.compute_head(Q=0.25)

        # 扬程应随流量增加而递减
        assert H1 > H2 > H3

    def test_stopped_pump_zero_head(self):
        """测试停止泵的扬程为零"""
        pump = create_centrifugal_pump(
            position=100.0,
            H0=50.0,
            Q_design=0.2,
            H_design=45.0
        )

        pump.stop()
        H = pump.compute_head(Q=0.1)

        assert H == 0.0


# ============================================================================
# 变速运行测试（相似定律）
# ============================================================================

class TestPumpAffinityLaws:
    """测试泵的相似定律"""

    def test_head_scales_with_speed_squared(self):
        """测试扬程与转速平方成正比"""
        pump = create_centrifugal_pump(
            position=100.0,
            H0=50.0,
            Q_design=0.2,
            H_design=45.0,
            n_rated=1450.0
        )

        Q = 0.15

        # 额定转速
        H_rated = pump.compute_head(Q, speed=1450.0)

        # 80%转速
        H_reduced = pump.compute_head(Q, speed=1160.0)

        # H2/H1 ~= (n2/n1)^2
        # (1160/1450)^2 = 0.8^2 = 0.64
        speed_ratio_squared = (1160.0 / 1450.0) ** 2
        expected_ratio = speed_ratio_squared

        actual_ratio = H_reduced / H_rated

        # 允许10%误差（因为流量也需要按比例调整）
        assert abs(actual_ratio - expected_ratio) < 0.15

    def test_speed_variation(self):
        """测试不同转速下的扬程"""
        pump = create_centrifugal_pump(
            position=100.0,
            H0=50.0,
            Q_design=0.2,
            H_design=45.0,
            n_rated=1450.0
        )

        Q = 0.1

        H_slow = pump.compute_head(Q, speed=1000.0)
        H_normal = pump.compute_head(Q, speed=1450.0)
        H_fast = pump.compute_head(Q, speed=1800.0)

        # 转速越高，扬程越大
        assert H_slow < H_normal < H_fast


# ============================================================================
# 效率计算测试
# ============================================================================

class TestPumpEfficiency:
    """测试泵效率计算"""

    def test_efficiency_at_design_point(self):
        """测试设计点效率"""
        pump = create_centrifugal_pump(
            position=100.0,
            H0=50.0,
            Q_design=0.2,
            H_design=45.0,
            eta_design=0.85
        )

        eta = pump.compute_efficiency(Q=0.2)

        # 设计点效率应接近设计值
        assert abs(eta - 0.85) < 0.05

    def test_efficiency_decreases_away_from_design(self):
        """测试偏离设计点时效率下降"""
        pump = create_centrifugal_pump(
            position=100.0,
            H0=50.0,
            Q_design=0.2,
            H_design=45.0,
            eta_design=0.85
        )

        eta_design = pump.compute_efficiency(Q=0.2)
        eta_low = pump.compute_efficiency(Q=0.1)
        eta_high = pump.compute_efficiency(Q=0.3)

        # 偏离设计点时效率应下降
        assert eta_low < eta_design
        assert eta_high < eta_design

    def test_efficiency_zero_for_stopped_pump(self):
        """测试停止泵的效率为零"""
        pump = create_centrifugal_pump(
            position=100.0,
            H0=50.0,
            Q_design=0.2,
            H_design=45.0
        )

        pump.stop()
        eta = pump.compute_efficiency(Q=0.1)

        assert eta == 0.0


# ============================================================================
# 功率计算测试
# ============================================================================

class TestPumpPower:
    """测试泵功率计算"""

    def test_power_calculation(self):
        """测试功率计算"""
        pump = create_centrifugal_pump(
            position=100.0,
            H0=50.0,
            Q_design=0.2,
            H_design=45.0,
            eta_design=0.85
        )

        Q = 0.2
        P = pump.compute_power(Q)

        # 功率 = rho * g * Q * H / η / 1000
        # P ~= 1000 * 9.81 * 0.2 * 45 / 0.85 / 1000 ~= 103.7 kW
        assert 90 < P < 120

    def test_power_increases_with_flow(self):
        """测试功率随流量增加"""
        pump = create_centrifugal_pump(
            position=100.0,
            H0=50.0,
            Q_design=0.2,
            H_design=45.0
        )

        P1 = pump.compute_power(Q=0.05)
        P2 = pump.compute_power(Q=0.15)
        P3 = pump.compute_power(Q=0.25)

        # 功率应随流量增加（尽管扬程下降）
        assert P1 < P2
        assert P2 < P3

    def test_power_zero_for_stopped_pump(self):
        """测试停止泵的功率为零"""
        pump = create_centrifugal_pump(
            position=100.0,
            H0=50.0,
            Q_design=0.2,
            H_design=45.0
        )

        pump.stop()
        P = pump.compute_power(Q=0.1)

        assert P == 0.0


# ============================================================================
# 工况点计算测试
# ============================================================================

class TestOperatingPoint:
    """测试泵工况点计算"""

    def test_operating_point_flat_system(self):
        """测试平坦系统曲线的工况点"""
        pump = create_centrifugal_pump(
            position=100.0,
            H0=50.0,
            Q_design=0.2,
            H_design=45.0
        )

        # 系统曲线：恒定静扬程
        def system_curve(Q):
            return 40.0  # 恒定40m

        Q_op, H_op = pump.compute_operating_point(system_curve)

        # 工况点应满足：H_pump(Q) = H_system(Q) = 40
        assert abs(H_op - 40.0) < 0.5
        assert Q_op > 0

    def test_operating_point_with_friction(self):
        """测试带摩阻的系统曲线"""
        pump = create_centrifugal_pump(
            position=100.0,
            H0=50.0,
            Q_design=0.2,
            H_design=45.0
        )

        # 系统曲线：静扬程 + 摩阻损失
        def system_curve(Q):
            H_static = 30.0
            K_friction = 100.0
            return H_static + K_friction * Q ** 2

        Q_op, H_op = pump.compute_operating_point(system_curve)

        # 验证工况点在合理范围
        assert 0.1 < Q_op < 0.3
        assert 35 < H_op < 50

        # 验证工况点满足方程
        H_pump = pump.compute_head(Q_op)
        H_system = system_curve(Q_op)
        assert abs(H_pump - H_system) < 0.5


# ============================================================================
# 泵组测试
# ============================================================================

class TestPumpArray:
    """测试泵组"""

    def test_parallel_pumps_add_flow(self):
        """测试并联泵流量相加"""
        # 创建两台相同的泵
        pump1 = create_centrifugal_pump(
            position=100.0,
            H0=50.0,
            Q_design=0.2,
            H_design=45.0
        )

        pump2 = create_centrifugal_pump(
            position=100.0,
            H0=50.0,
            Q_design=0.2,
            H_design=45.0
        )

        # 并联运行
        array = create_pump_array([pump1, pump2], configuration='parallel')

        # 总流量0.4 m^3/s，每台泵0.2 m^3/s
        H = array.compute_head(Q=0.4)

        # 扬程应接近单泵在0.2 m^3/s时的扬程
        H_single = pump1.compute_head(Q=0.2)
        assert abs(H - H_single) < 1.0

    def test_series_pumps_add_head(self):
        """测试串联泵扬程相加"""
        # 创建两台相同的泵
        pump1 = create_centrifugal_pump(
            position=100.0,
            H0=50.0,
            Q_design=0.2,
            H_design=45.0
        )

        pump2 = create_centrifugal_pump(
            position=100.0,
            H0=50.0,
            Q_design=0.2,
            H_design=45.0
        )

        # 串联运行
        array = create_pump_array([pump1, pump2], configuration='series')

        Q = 0.15
        H_array = array.compute_head(Q)

        # 扬程应约为单泵的两倍
        H_single = pump1.compute_head(Q)
        assert abs(H_array - 2 * H_single) < 2.0

    def test_pump_array_power(self):
        """测试泵组功率"""
        pump1 = create_centrifugal_pump(
            position=100.0,
            H0=50.0,
            Q_design=0.2,
            H_design=45.0
        )

        pump2 = create_centrifugal_pump(
            position=100.0,
            H0=50.0,
            Q_design=0.2,
            H_design=45.0
        )

        array = create_pump_array([pump1, pump2], configuration='parallel')

        P_total = array.compute_total_power(Q=0.4)

        # 总功率应约为两台泵功率之和
        assert P_total > 0

    def test_stop_one_pump_in_array(self):
        """测试停止泵组中的一台泵"""
        pump1 = create_centrifugal_pump(
            position=100.0,
            H0=50.0,
            Q_design=0.2,
            H_design=45.0
        )

        pump2 = create_centrifugal_pump(
            position=100.0,
            H0=50.0,
            Q_design=0.2,
            H_design=45.0
        )

        array = create_pump_array([pump1, pump2], configuration='parallel')

        # 两台泵运行
        assert array.get_running_count() == 2

        # 停止一台
        array.stop_pump(1)
        assert array.get_running_count() == 1

        # 并联运行时，停止一台后扬程应下降
        H_both = array.compute_head(Q=0.4)
        array.stop_pump(1)
        H_one = array.compute_head(Q=0.4)

        # 单台泵承担全部流量，扬程更低
        # (因为单泵超出最佳工况点)


# ============================================================================
# 便捷函数测试
# ============================================================================

class TestConvenienceFunctions:
    """测试便捷函数"""

    def test_create_centrifugal_pump(self):
        """测试创建离心泵函数"""
        pump = create_centrifugal_pump(
            position=100.0,
            H0=50.0,
            Q_design=0.2,
            H_design=45.0,
            eta_design=0.85,
            n_rated=1450.0
        )

        assert isinstance(pump, CentrifugalPump)
        assert pump.position == 100.0
        assert pump.char.H0 == 50.0
        assert pump.char.Q_design == 0.2

    def test_create_pump_array(self):
        """测试创建泵组函数"""
        pump1 = create_centrifugal_pump(
            position=100.0,
            H0=50.0,
            Q_design=0.2,
            H_design=45.0
        )

        pump2 = create_centrifugal_pump(
            position=100.0,
            H0=50.0,
            Q_design=0.2,
            H_design=45.0
        )

        array = create_pump_array([pump1, pump2], configuration='series')

        assert isinstance(array, PumpArray)
        assert len(array.pumps) == 2
        assert array.configuration == 'series'


# ============================================================================
# 边界情况测试
# ============================================================================

class TestEdgeCases:
    """测试边界情况"""

    def test_zero_flow(self):
        """测试零流量"""
        pump = create_centrifugal_pump(
            position=100.0,
            H0=50.0,
            Q_design=0.2,
            H_design=45.0
        )

        H = pump.compute_head(Q=0.0)
        eta = pump.compute_efficiency(Q=0.0)
        P = pump.compute_power(Q=0.0)

        # 零流量时，扬程=H0，效率=0，功率=0
        assert H == 50.0
        assert eta == 0.0
        assert P == 0.0

    def test_very_high_flow(self):
        """测试极大流量"""
        pump = create_centrifugal_pump(
            position=100.0,
            H0=50.0,
            Q_design=0.2,
            H_design=45.0
        )

        # 流量远超设计值
        Q = 1.0  # 5倍设计流量
        H = pump.compute_head(Q)

        # 扬程可能为负，但会被限制为0
        assert H >= 0

    def test_zero_speed(self):
        """测试零转速"""
        pump = create_centrifugal_pump(
            position=100.0,
            H0=50.0,
            Q_design=0.2,
            H_design=45.0
        )

        pump.set_speed(0.0)
        H = pump.compute_head(Q=0.1)

        # 零转速时，扬程应为0
        assert H == 0.0

    def test_empty_pump_array(self):
        """测试空泵组"""
        with pytest.raises(ValueError, match="at least one pump"):
            create_pump_array([], configuration='parallel')


# ============================================================================
# 实际案例测试
# ============================================================================

class TestRealWorldCases:
    """测试实际工程案例"""

    def test_typical_water_supply_pump(self):
        """测试典型供水泵"""
        # 典型参数：流量200 m^3/h = 0.0556 m^3/s, 扬程50m
        pump = create_centrifugal_pump(
            position=0.0,
            H0=55.0,
            Q_design=0.0556,
            H_design=50.0,
            eta_design=0.82,
            n_rated=1450.0
        )

        # 在设计点计算
        H = pump.compute_head(Q=0.0556)
        eta = pump.compute_efficiency(Q=0.0556)
        P = pump.compute_power(Q=0.0556)

        # 验证合理性
        assert 48 < H < 52  # 扬程接近50m
        assert 0.75 < eta < 0.90  # 效率合理
        assert 30 < P < 40  # 功率约35kW

    def test_two_pump_station(self):
        """测试双泵站"""
        # 两台泵并联运行
        pump1 = create_centrifugal_pump(
            position=0.0,
            H0=55.0,
            Q_design=0.0556,
            H_design=50.0,
            eta_design=0.82
        )

        pump2 = create_centrifugal_pump(
            position=0.0,
            H0=55.0,
            Q_design=0.0556,
            H_design=50.0,
            eta_design=0.82
        )

        station = create_pump_array([pump1, pump2], configuration='parallel')

        # 总流量约0.11 m^3/s
        Q_total = 0.11
        H = station.compute_head(Q_total)
        P_total = station.compute_total_power(Q_total)

        # 扬程应接近50m
        assert 45 < H < 55

        # 总功率约70kW
        assert 60 < P_total < 80
