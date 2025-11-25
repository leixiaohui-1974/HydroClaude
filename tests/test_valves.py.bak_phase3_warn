"""
测试阀门水力计算

测试内容：
- 蝶阀水力损失和开度控制
- 球阀开关操作
- 减压阀压力控制
- 各种边界情况

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
    ButterflyValve, ButterflyValveGeometry,
    BallValve, BallValveGeometry,
    PressureReducingValve, PRVGeometry,
    create_butterfly_valve, create_ball_valve, create_prv
)


# ============================================================================
# 蝶阀测试
# ============================================================================

class TestButterflyValveGeometry:
    """测试蝶阀几何参数"""

    def test_valid_geometry(self):
        """测试有效几何参数"""
        geom = ButterflyValveGeometry(
            position=100.0,
            diameter=0.5,
            disc_thickness=0.05
        )

        assert geom.position == 100.0
        assert geom.diameter == 0.5
        assert geom.disc_thickness == 0.05

    def test_invalid_diameter(self):
        """测试无效直径"""
        with pytest.raises(ValueError, match="Diameter must be positive"):
            ButterflyValveGeometry(
                position=100.0,
                diameter=0.0
            )

    def test_invalid_disc_thickness(self):
        """测试无效蝶板厚度"""
        with pytest.raises(ValueError, match="Disc thickness must be non-negative"):
            ButterflyValveGeometry(
                position=100.0,
                diameter=0.5,
                disc_thickness=-0.01
            )


class TestButterflyValveOperations:
    """测试蝶阀操作"""

    def test_set_opening(self):
        """测试设置开度"""
        valve = create_butterfly_valve(position=100.0, diameter=0.5)

        # 设置不同开度
        valve.set_opening(75.0)
        assert valve.get_opening() == 75.0

        valve.set_opening(50.0)
        assert valve.get_opening() == 50.0

        valve.set_opening(0.0)
        assert valve.get_opening() == 0.0

    def test_invalid_opening(self):
        """测试无效开度"""
        valve = create_butterfly_valve(position=100.0, diameter=0.5)

        with pytest.raises(ValueError, match="Opening must be between 0 and 100"):
            valve.set_opening(-10.0)

        with pytest.raises(ValueError, match="Opening must be between 0 and 100"):
            valve.set_opening(150.0)

    def test_initial_opening(self):
        """测试初始开度设置"""
        valve = create_butterfly_valve(
            position=100.0,
            diameter=0.5,
            initial_opening=60.0
        )

        assert valve.get_opening() == 60.0


class TestButterflyValveLossCoefficient:
    """测试蝶阀损失系数"""

    def test_loss_coefficient_fully_open(self):
        """测试全开时的损失系数"""
        valve = create_butterfly_valve(
            position=100.0,
            diameter=0.5,
            valve_type='standard'
        )

        valve.set_opening(100.0)
        Kv = valve.get_loss_coefficient()

        # 全开时，标准蝶阀 Kv ~= 0.25
        assert 0.2 < Kv < 0.3

    def test_loss_coefficient_increases_with_closure(self):
        """测试损失系数随关闭增加"""
        valve = create_butterfly_valve(position=100.0, diameter=0.5)

        Kv_100 = valve.get_loss_coefficient(100.0)  # 全开
        Kv_70 = valve.get_loss_coefficient(70.0)
        Kv_50 = valve.get_loss_coefficient(50.0)
        Kv_30 = valve.get_loss_coefficient(30.0)
        Kv_10 = valve.get_loss_coefficient(10.0)

        # 损失系数应随关闭而增加
        assert Kv_100 < Kv_70 < Kv_50 < Kv_30 < Kv_10

    def test_high_performance_valve_lower_loss(self):
        """测试高性能阀门损失更小"""
        valve_std = create_butterfly_valve(
            position=100.0,
            diameter=0.5,
            valve_type='standard'
        )

        valve_hp = create_butterfly_valve(
            position=100.0,
            diameter=0.5,
            valve_type='high_performance'
        )

        valve_std.set_opening(100.0)
        valve_hp.set_opening(100.0)

        Kv_std = valve_std.get_loss_coefficient()
        Kv_hp = valve_hp.get_loss_coefficient()

        # 高性能阀门全开时损失更小
        assert Kv_hp < Kv_std

    def test_loss_coefficient_at_specific_openings(self):
        """测试特定开度下的损失系数"""
        valve = create_butterfly_valve(position=100.0, diameter=0.5)

        # 根据经验数据验证
        Kv_90 = valve.get_loss_coefficient(100.0)  # 全开
        Kv_70 = valve.get_loss_coefficient(78.0)   # 约70 deg
        Kv_50 = valve.get_loss_coefficient(56.0)   # 约50 deg

        # 粗略验证范围
        assert 0.2 < Kv_90 < 0.5
        assert 0.8 < Kv_70 < 2.0
        assert 15.0 < Kv_50 < 25.0  # 56%开度时损失系数较大


class TestButterflyValveHeadLoss:
    """测试蝶阀水头损失"""

    def test_head_loss_calculation(self):
        """测试水头损失计算"""
        valve = create_butterfly_valve(position=100.0, diameter=0.5)
        valve.set_opening(70.0)

        Q = 0.2  # m^3/s
        hL = valve.compute_head_loss(Q)

        # 水头损失应为正
        assert hL > 0

        # 粗略验证：70%开度，流量0.2 m^3/s，损失应在0.1-1.0 m范围
        assert 0.01 < hL < 2.0

    def test_head_loss_increases_with_flow(self):
        """测试水头损失随流量增加（平方关系）"""
        valve = create_butterfly_valve(position=100.0, diameter=0.5)
        valve.set_opening(80.0)

        hL_1 = valve.compute_head_loss(Q=0.1)
        hL_2 = valve.compute_head_loss(Q=0.2)

        # 水头损失与流量平方成正比
        # hL_2 / hL_1 ~= (Q_2 / Q_1)^2  = (0.2/0.1)^2 = 4
        ratio = hL_2 / hL_1
        assert 3.5 < ratio < 4.5

    def test_head_loss_increases_with_closure(self):
        """测试水头损失随关闭增加"""
        valve = create_butterfly_valve(position=100.0, diameter=0.5)

        Q = 0.15

        hL_100 = valve.compute_head_loss(Q, opening_percent=100.0)
        hL_70 = valve.compute_head_loss(Q, opening_percent=70.0)
        hL_40 = valve.compute_head_loss(Q, opening_percent=40.0)

        assert hL_100 < hL_70 < hL_40

    def test_zero_flow(self):
        """测试零流量"""
        valve = create_butterfly_valve(position=100.0, diameter=0.5)

        hL = valve.compute_head_loss(Q=0.0)

        assert hL == 0.0

    def test_negative_flow(self):
        """测试负流量（反向流动）"""
        valve = create_butterfly_valve(position=100.0, diameter=0.5)
        valve.set_opening(80.0)

        hL_positive = valve.compute_head_loss(Q=0.2)
        hL_negative = valve.compute_head_loss(Q=-0.2)

        # 水头损失应该相同（取绝对值）
        assert abs(hL_positive - hL_negative) < 0.001


class TestButterflyValveFlowCoefficient:
    """测试蝶阀流量系数"""

    def test_cv_calculation(self):
        """测试Cv计算"""
        valve = create_butterfly_valve(position=100.0, diameter=0.5)
        valve.set_opening(100.0)

        Cv = valve.compute_flow_coefficient()

        # Cv应为正
        assert Cv > 0

        # 对于直径0.5m（约20英寸），全开Cv应在数千到数万
        # 根据公式 Cv = 29.84 * D^2 / sqrtKv，大口径阀门Cv很大
        assert 10000 < Cv < 30000

    def test_cv_decreases_with_closure(self):
        """测试Cv随关闭减小"""
        valve = create_butterfly_valve(position=100.0, diameter=0.5)

        Cv_100 = valve.compute_flow_coefficient(100.0)
        Cv_70 = valve.compute_flow_coefficient(70.0)
        Cv_40 = valve.compute_flow_coefficient(40.0)

        # Cv随关闭而减小
        assert Cv_100 > Cv_70 > Cv_40


# ============================================================================
# 球阀测试
# ============================================================================

class TestBallValveGeometry:
    """测试球阀几何参数"""

    def test_valid_geometry(self):
        """测试有效几何参数"""
        geom = BallValveGeometry(
            position=100.0,
            diameter=0.3,
            port_type='full_port'
        )

        assert geom.position == 100.0
        assert geom.diameter == 0.3
        assert geom.port_type == 'full_port'

    def test_invalid_diameter(self):
        """测试无效直径"""
        with pytest.raises(ValueError, match="Diameter must be positive"):
            BallValveGeometry(position=100.0, diameter=0.0)

    def test_invalid_port_type(self):
        """测试无效通道类型"""
        with pytest.raises(ValueError, match="Port type must be"):
            BallValveGeometry(
                position=100.0,
                diameter=0.3,
                port_type='invalid'
            )


class TestBallValveOperations:
    """测试球阀操作"""

    def test_open_close(self):
        """测试开关操作"""
        valve = create_ball_valve(position=100.0, diameter=0.3)

        # 初始应为开启
        assert valve.is_open() is True

        # 关闭
        valve.close()
        assert valve.is_open() is False

        # 重新打开
        valve.open()
        assert valve.is_open() is True

    def test_initial_state_closed(self):
        """测试初始关闭状态"""
        valve = create_ball_valve(
            position=100.0,
            diameter=0.3,
            is_open=False
        )

        assert valve.is_open() is False


class TestBallValveLossCoefficient:
    """测试球阀损失系数"""

    def test_full_port_loss_coefficient(self):
        """测试全通径球阀损失系数"""
        valve = create_ball_valve(
            position=100.0,
            diameter=0.3,
            port_type='full_port'
        )

        Kv = valve.get_loss_coefficient()

        # 全通径球阀，Kv ~= 0.05
        assert 0.03 < Kv < 0.07

    def test_reduced_port_loss_coefficient(self):
        """测试缩径球阀损失系数"""
        valve = create_ball_valve(
            position=100.0,
            diameter=0.3,
            port_type='reduced_port'
        )

        Kv = valve.get_loss_coefficient()

        # 缩径球阀，Kv ~= 0.15
        assert 0.1 < Kv < 0.2

    def test_closed_valve_high_loss(self):
        """测试关闭阀门的高损失系数"""
        valve = create_ball_valve(position=100.0, diameter=0.3)

        valve.close()
        Kv = valve.get_loss_coefficient()

        # 关闭时，损失系数极大
        assert Kv > 1e9

    def test_full_port_lower_than_reduced(self):
        """测试全通径损失小于缩径"""
        valve_full = create_ball_valve(
            position=100.0,
            diameter=0.3,
            port_type='full_port'
        )

        valve_reduced = create_ball_valve(
            position=100.0,
            diameter=0.3,
            port_type='reduced_port'
        )

        Kv_full = valve_full.get_loss_coefficient()
        Kv_reduced = valve_reduced.get_loss_coefficient()

        assert Kv_full < Kv_reduced


class TestBallValveHeadLoss:
    """测试球阀水头损失"""

    def test_open_valve_small_loss(self):
        """测试开启阀门的小水头损失"""
        valve = create_ball_valve(
            position=100.0,
            diameter=0.3,
            port_type='full_port'
        )

        Q = 0.1  # m^3/s
        hL = valve.compute_head_loss(Q)

        # 全通径球阀全开时，损失极小
        assert hL < 0.2  # 应小于0.2m

    def test_closed_valve_high_loss(self):
        """测试关闭阀门的高水头损失"""
        valve = create_ball_valve(position=100.0, diameter=0.3)

        valve.close()

        Q = 0.1
        hL = valve.compute_head_loss(Q)

        # 关闭时，水头损失极大
        assert hL > 1000  # 实际应该完全截断

    def test_zero_flow(self):
        """测试零流量"""
        valve = create_ball_valve(position=100.0, diameter=0.3)

        hL = valve.compute_head_loss(Q=0.0)

        assert hL == 0.0


# ============================================================================
# 减压阀测试
# ============================================================================

class TestPRVGeometry:
    """测试减压阀几何参数"""

    def test_valid_geometry(self):
        """测试有效几何参数"""
        geom = PRVGeometry(
            position=100.0,
            diameter=0.4
        )

        assert geom.position == 100.0
        assert geom.diameter == 0.4

    def test_invalid_diameter(self):
        """测试无效直径"""
        with pytest.raises(ValueError, match="Diameter must be positive"):
            PRVGeometry(position=100.0, diameter=0.0)


class TestPRVOperations:
    """测试减压阀操作"""

    def test_set_target_pressure(self):
        """测试设置目标压力"""
        prv = create_prv(
            position=100.0,
            diameter=0.4,
            target_pressure=30.0
        )

        assert prv.target_pressure == 30.0

        # 修改目标压力
        prv.set_target_pressure(25.0)
        assert prv.target_pressure == 25.0

    def test_invalid_target_pressure(self):
        """测试无效目标压力"""
        prv = create_prv(position=100.0, diameter=0.4, target_pressure=30.0)

        with pytest.raises(ValueError, match="Target pressure must be non-negative"):
            prv.set_target_pressure(-5.0)

    def test_activate_deactivate(self):
        """测试激活/停用"""
        prv = create_prv(position=100.0, diameter=0.4, target_pressure=30.0)

        # 初始应激活
        assert prv.is_active() is True

        # 停用
        prv.deactivate()
        assert prv.is_active() is False

        # 重新激活
        prv.activate()
        assert prv.is_active() is True


class TestPRVHeadLoss:
    """测试减压阀水头损失"""

    def test_normal_operation(self):
        """测试正常减压工作"""
        prv = create_prv(position=100.0, diameter=0.4, target_pressure=30.0)

        p_upstream = 50.0  # m
        Q = 0.15  # m^3/s

        hL = prv.compute_head_loss(p_upstream, Q)

        # 水头损失 = 上游压力 - 目标压力
        assert abs(hL - (50.0 - 30.0)) < 0.01
        assert abs(hL - 20.0) < 0.01

    def test_insufficient_upstream_pressure(self):
        """测试上游压力不足"""
        prv = create_prv(position=100.0, diameter=0.4, target_pressure=30.0)

        p_upstream = 25.0  # 小于目标压力
        Q = 0.15

        hL = prv.compute_head_loss(p_upstream, Q)

        # 无法减压，水头损失应为0
        assert hL == 0.0

    def test_deactivated_prv(self):
        """测试停用的减压阀"""
        prv = create_prv(position=100.0, diameter=0.4, target_pressure=30.0)

        prv.deactivate()

        p_upstream = 50.0
        Q = 0.15

        hL = prv.compute_head_loss(p_upstream, Q)

        # 停用时，无水头损失
        assert hL == 0.0

    def test_equal_pressures(self):
        """测试上游压力等于目标压力"""
        prv = create_prv(position=100.0, diameter=0.4, target_pressure=30.0)

        p_upstream = 30.0  # 等于目标压力
        Q = 0.15

        hL = prv.compute_head_loss(p_upstream, Q)

        # 无需减压，损失为0
        assert hL == 0.0


class TestPRVDownstreamPressure:
    """测试减压阀下游压力"""

    def test_normal_pressure_reduction(self):
        """测试正常减压"""
        prv = create_prv(position=100.0, diameter=0.4, target_pressure=30.0)

        p_upstream = 50.0
        p_downstream = prv.compute_downstream_pressure(p_upstream)

        # 下游压力应等于目标压力
        assert abs(p_downstream - 30.0) < 0.01

    def test_insufficient_upstream(self):
        """测试上游压力不足时下游压力"""
        prv = create_prv(position=100.0, diameter=0.4, target_pressure=30.0)

        p_upstream = 25.0
        p_downstream = prv.compute_downstream_pressure(p_upstream)

        # 无法减压，下游=上游
        assert abs(p_downstream - p_upstream) < 0.01

    def test_deactivated_prv_downstream(self):
        """测试停用时下游压力"""
        prv = create_prv(position=100.0, diameter=0.4, target_pressure=30.0)

        prv.deactivate()

        p_upstream = 50.0
        p_downstream = prv.compute_downstream_pressure(p_upstream)

        # 停用时，下游=上游（无减压）
        assert abs(p_downstream - p_upstream) < 0.01


class TestPRVRequiredOpening:
    """测试减压阀所需开度"""

    def test_opening_calculation(self):
        """测试开度计算"""
        prv = create_prv(position=100.0, diameter=0.4, target_pressure=30.0)

        p_upstream = 50.0
        Q = 0.15

        opening = prv.compute_required_opening(p_upstream, Q)

        # 开度应该在合理范围内
        assert 0 < opening <= 100

        # 简化计算：opening = (30/50) * 100 = 60%
        assert 50 < opening < 70

    def test_opening_when_insufficient_pressure(self):
        """测试压力不足时的开度"""
        prv = create_prv(position=100.0, diameter=0.4, target_pressure=30.0)

        p_upstream = 25.0
        Q = 0.15

        opening = prv.compute_required_opening(p_upstream, Q)

        # 应该全开
        assert opening == 100.0

    def test_opening_when_deactivated(self):
        """测试停用时的开度"""
        prv = create_prv(position=100.0, diameter=0.4, target_pressure=30.0)

        prv.deactivate()

        p_upstream = 50.0
        Q = 0.15

        opening = prv.compute_required_opening(p_upstream, Q)

        # 应该全开
        assert opening == 100.0


# ============================================================================
# 便捷函数测试
# ============================================================================

class TestConvenienceFunctions:
    """测试便捷函数"""

    def test_create_butterfly_valve(self):
        """测试创建蝶阀函数"""
        valve = create_butterfly_valve(
            position=100.0,
            diameter=0.5,
            valve_type='high_performance',
            initial_opening=75.0
        )

        assert isinstance(valve, ButterflyValve)
        assert valve.geom.diameter == 0.5
        assert valve.valve_type == 'high_performance'
        assert valve.get_opening() == 75.0

    def test_create_ball_valve(self):
        """测试创建球阀函数"""
        valve = create_ball_valve(
            position=100.0,
            diameter=0.3,
            port_type='reduced_port',
            is_open=False
        )

        assert isinstance(valve, BallValve)
        assert valve.geom.diameter == 0.3
        assert valve.geom.port_type == 'reduced_port'
        assert valve.is_open() is False

    def test_create_prv(self):
        """测试创建减压阀函数"""
        prv = create_prv(
            position=100.0,
            diameter=0.4,
            target_pressure=35.0
        )

        assert isinstance(prv, PressureReducingValve)
        assert prv.geom.diameter == 0.4
        assert prv.target_pressure == 35.0
        assert prv.is_active() is True


# ============================================================================
# 比较测试
# ============================================================================

class TestValveComparisons:
    """测试不同阀门的比较"""

    def test_ball_valve_lower_loss_than_butterfly(self):
        """测试球阀全开损失小于蝶阀"""
        ball_valve = create_ball_valve(
            position=100.0,
            diameter=0.3,
            port_type='full_port'
        )

        butterfly_valve = create_butterfly_valve(
            position=100.0,
            diameter=0.3,
            valve_type='standard',
            initial_opening=100.0
        )

        Q = 0.1

        hL_ball = ball_valve.compute_head_loss(Q)
        hL_butterfly = butterfly_valve.compute_head_loss(Q)

        # 球阀全开损失应小于蝶阀全开
        assert hL_ball < hL_butterfly

    def test_prv_maintains_constant_downstream_pressure(self):
        """测试减压阀维持恒定下游压力"""
        prv = create_prv(position=100.0, diameter=0.4, target_pressure=30.0)

        # 不同上游压力
        p_ups = [40.0, 50.0, 60.0, 70.0]

        downstream_pressures = [
            prv.compute_downstream_pressure(p) for p in p_ups
        ]

        # 所有下游压力应该相同且等于目标值
        for p_down in downstream_pressures:
            assert abs(p_down - 30.0) < 0.01
