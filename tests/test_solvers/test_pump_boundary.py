#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
离心泵边界条件测试
Test Pump Boundary Conditions

作者: HydroClaude Team
日期: 2025-10-30
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

try:
    from solvers.pump_boundary import (
except ImportError as e:
    print(f"Import error: {e}")
    print("Make sure project root is in sys.path")
    sys.exit(1)

    PumpCharacteristics, PumpBoundary, StandardPumps
)


class TestPumpCharacteristics:
    """测试泵特性曲线类"""

    def test_basic_pump_creation(self):
        """测试基本泵特性创建"""
        pump = PumpCharacteristics(
            Q_design=0.1,
            H_design=50.0,
            n_design=1500,
            efficiency_design=0.80,
            H_curve_a=60.0,
            H_curve_b=-50.0,
            H_curve_c=-100.0,
            WR2=10.0
        )

        assert pump.Q_design == 0.1
        assert pump.H_design == 50.0
        assert pump.WR2 == 10.0

    def test_head_at_flow(self):
        """测试扬程计算"""
        pump = PumpCharacteristics(
            Q_design=0.1,
            H_design=50.0,
            n_design=1500,
            efficiency_design=0.80,
            H_curve_a=60.0,
            H_curve_b=-50.0,
            H_curve_c=-100.0,
            WR2=10.0
        )

        # 零流量点
        H_zero = pump.head_at_flow(0.0)
        assert H_zero == pytest.approx(60.0, rel=1e-3)

        # 设计点
        H_design = pump.head_at_flow(0.1)
        expected_H = 60 - 50*0.1 - 100*0.1**2  # = 60 - 5 - 1 = 54
        assert H_design == pytest.approx(expected_H, rel=1e-3)

        # 扬程应随流量增大而减小（对于正常泵曲线）
        H_small = pump.head_at_flow(0.05)
        H_large = pump.head_at_flow(0.15)
        assert H_small > H_large

    def test_affinity_laws(self):
        """测试相似律（转速影响）"""
        pump = PumpCharacteristics(
            Q_design=0.1,
            H_design=50.0,
            n_design=1500,
            efficiency_design=0.80,
            H_curve_a=60.0,
            H_curve_b=-50.0,
            H_curve_c=-100.0,
            WR2=10.0
        )

        # 设计转速下的扬程
        H_1500 = pump.head_at_flow(0.1, n=1500)

        # 转速减半，扬程应为1/4
        H_750 = pump.head_at_flow(0.05, n=750)  # 流量also减半
        assert H_750 == pytest.approx(H_1500 / 4, rel=5e-2)

        # 转速加倍，扬程应为4倍
        H_3000 = pump.head_at_flow(0.2, n=3000)  # 流量也加倍
        assert H_3000 == pytest.approx(H_1500 * 4, rel=5e-2)

    def test_efficiency_at_flow(self):
        """测试效率计算"""
        pump = PumpCharacteristics(
            Q_design=0.1,
            H_design=50.0,
            n_design=1500,
            efficiency_design=0.80,
            H_curve_a=60.0,
            H_curve_b=-50.0,
            H_curve_c=-100.0,
            WR2=10.0
        )

        # 设计点效率最高
        eta_design = pump.efficiency_at_flow(0.1)
        assert eta_design == pytest.approx(0.80, rel=1e-3)

        # 偏离设计点效率下降
        eta_low = pump.efficiency_at_flow(0.05)
        eta_high = pump.efficiency_at_flow(0.15)

        assert eta_low < eta_design
        assert eta_high < eta_design

        # 效率应在0-1之间
        assert 0 <= eta_low <= 1
        assert 0 <= eta_high <= 1

    def test_power_at_flow(self):
        """测试功率计算"""
        pump = PumpCharacteristics(
            Q_design=0.1,
            H_design=50.0,
            n_design=1500,
            efficiency_design=0.80,
            H_curve_a=60.0,
            H_curve_b=-50.0,
            H_curve_c=-100.0,
            WR2=10.0
        )

        P = pump.power_at_flow(0.1)

        # P = ρ * g * Q * H / η
        # 近似估算
        rho = 1000
        g = 9.81
        Q = 0.1
        H = pump.head_at_flow(Q)
        eta = pump.efficiency_at_flow(Q)

        P_expected = rho * g * Q * H / eta

        assert P == pytest.approx(P_expected, rel=1e-3)
        assert P > 0

    def test_from_three_points(self):
        """测试从三点拟合泵曲线"""
        # 给定三个工况点
        Q1, H1 = 0.0, 60.0   # 零流量点
        Q2, H2 = 0.1, 50.0   # 设计点
        Q3, H3 = 0.2, 30.0   # 大流量点

        pump = PumpCharacteristics.from_three_points(
            Q1, H1, Q2, H2, Q3, H3,
            n_design=1500,
            WR2=10.0
        )

        # 验证拟合的曲线能通过这三个点
        assert pump.head_at_flow(Q1) == pytest.approx(H1, rel=1e-2)
        assert pump.head_at_flow(Q2) == pytest.approx(H2, rel=1e-2)
        assert pump.head_at_flow(Q3) == pytest.approx(H3, rel=1e-2)


class TestPumpBoundary:
    """测试泵边界条件类"""

    def test_pump_boundary_creation(self):
        """测试泵边界条件创建"""
        pump_chars = StandardPumps.small_booster_pump()
        boundary = PumpBoundary(
            pump_chars,
            pipe_area=0.07,
            wave_speed=1000.0
        )

        assert boundary.current_speed == pump_chars.n_design
        assert boundary.A == 0.07
        assert boundary.a == 1000.0

    def test_steady_state_boundary(self):
        """测试稳态边界条件"""
        pump_chars = StandardPumps.small_booster_pump()
        boundary = PumpBoundary(
            pump_chars,
            pipe_area=0.07,
            wave_speed=1000.0
        )

        # 模拟稳态（无转速变化）
        t = 0.0
        H_plus = 120.0  # 特征线值
        H_minus = 90.0
        Q_plus = 0.05
        Q_minus = 0.05
        dt = 0.01

        H, Q = boundary.apply_boundary(t, H_plus, H_minus, Q_plus, Q_minus, dt)

        # 水头和流量应该是合理的
        assert H > 0
        assert Q > 0
        print(f"\nSteady state: H={H:.2f}m, Q={Q:.4f}m^3/s")

    def test_speed_variation(self):
        """测试转速变化"""
        pump_chars = StandardPumps.small_booster_pump()

        # 创建渐进停机的转速函数
        speed_func = PumpBoundary.gradual_shutdown(
            t_start=1.0,
            t_end=3.0,
            n_initial=1450
        )

        boundary = PumpBoundary(
            pump_chars,
            speed_function=speed_func,
            pipe_area=0.07,
            wave_speed=1000.0
        )

        # 测试不同时刻的转速
        speeds = []
        for t in [0.5, 1.5, 2.5, 3.5]:
            H_plus, H_minus = 120.0, 90.0
            Q_plus, Q_minus = 0.05, 0.05

            H, Q = boundary.apply_boundary(t, H_plus, H_minus, Q_plus, Q_minus, 0.01)
            speeds.append(boundary.current_speed)

        print(f"\nSpeed variation: {speeds}")

        # 转速应该递减
        assert speeds[0] == 1450  # t=0.5, 未开始停机
        assert speeds[1] < speeds[0]  # t=1.5, 停机中
        assert speeds[2] < speeds[1]  # t=2.5, 停机中
        assert speeds[3] == 0  # t=3.5, 已停止

    def test_power_failure_function(self):
        """测试断电工况函数"""
        speed_func = PumpBoundary.power_failure(t_fail=2.0)

        # 断电前
        n_before = speed_func(1.0, n0=1500)
        assert n_before == 1500

        # 断电后转速衰减
        n_after_1s = speed_func(3.0, n0=1500, k=0.5)
        n_after_2s = speed_func(4.0, n0=1500, k=0.5)

        print(f"\nPower failure: n(t=3s)={n_after_1s:.1f}, n(t=4s)={n_after_2s:.1f}")

        assert n_after_1s < n_before
        assert n_after_2s < n_after_1s

    def test_startup_function(self):
        """测试启动工况函数"""
        speed_func = PumpBoundary.gradual_startup(
            t_start=0.0,
            t_end=5.0,
            n_final=1500
        )

        speeds = [speed_func(t) for t in [0, 1, 2.5, 5, 6]]

        print(f"\nStartup: {speeds}")

        # 启动前
        assert speeds[0] == 0

        # 启动中，转速递增
        assert 0 < speeds[1] < 1500
        assert 0 < speeds[2] < 1500
        assert speeds[1] < speeds[2]

        # 达到全速
        assert speeds[3] == 1500
        assert speeds[4] == 1500


class TestStandardPumps:
    """测试标准泵型库"""

    def test_small_booster_pump(self):
        """测试小型增压泵"""
        pump = StandardPumps.small_booster_pump()

        assert pump.Q_design == 0.05
        assert pump.H_design == 30.0
        assert pump.n_design == 1450

        # 验证泵曲线合理性
        H_zero = pump.head_at_flow(0.0)
        H_design = pump.head_at_flow(0.05)

        assert H_zero > H_design  # 零流量扬程应大于设计扬程

    def test_medium_pump(self):
        """测试中型泵"""
        pump = StandardPumps.medium_pump()

        assert pump.Q_design == 0.2
        assert pump.H_design == 50.0

    def test_large_pump(self):
        """测试大型泵"""
        pump = StandardPumps.large_pump()

        assert pump.Q_design == 1.0
        assert pump.H_design == 80.0


if __name__ == '__main__':
    pytest.main([__file__, '-v', '-s'])
