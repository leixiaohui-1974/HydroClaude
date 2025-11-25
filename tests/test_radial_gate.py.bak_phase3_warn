#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
弧形闸门单元测试

测试内容：
1. 基本参数
2. 流量系数计算
3. 淹没判别
4. 自由出流
5. 淹没出流
6. 反算开度
7. 边界情况

作者：HydroClaude Team
日期：2025-10-28
"""

import pytest
import numpy as np
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from physics.structures.radial_gate import RadialGate


class TestRadialGateBasics:
    """测试弧形闸门基本功能"""

    def test_gate_creation(self):
        """测试闸门创建"""
        gate = RadialGate(
            width=15.0,
            crest_elevation=100.0,
            radius=8.0,
            design_head=10.0
        )

        assert gate.width == 15.0
        assert gate.crest_elevation == 100.0
        assert gate.radius == 8.0
        assert gate.design_head == 10.0
        assert gate.max_opening == 8.0  # 默认等于半径

    def test_custom_max_opening(self):
        """测试自定义最大开度"""
        gate = RadialGate(
            width=15.0,
            crest_elevation=100.0,
            radius=8.0,
            design_head=10.0,
            max_opening=6.0
        )

        assert gate.max_opening == 6.0


class TestSubmergenceCheck:
    """测试淹没判别"""

    def setup_method(self):
        """每个测试前的准备"""
        self.gate = RadialGate(
            width=15.0,
            crest_elevation=100.0,
            radius=8.0,
            design_head=10.0
        )

    def test_free_flow(self):
        """测试自由出流判别"""
        h_up = 110.0   # 堰顶以上10m
        h_down = 101.0  # 堰顶以上1m

        is_submerged, S = self.gate.check_submergence(h_up, h_down)

        assert not is_submerged
        assert S < 0.67
        print(f"\n自由出流: S = {S:.3f}")

    def test_submerged_flow(self):
        """测试淹没出流判别"""
        h_up = 110.0   # 堰顶以上10m
        h_down = 108.0  # 堰顶以上8m

        is_submerged, S = self.gate.check_submergence(h_up, h_down)

        assert is_submerged
        assert S >= 0.67
        print(f"\n淹没出流: S = {S:.3f}")

    def test_critical_submergence(self):
        """测试临界淹没状态"""
        h_up = 110.0
        h_down = 106.7  # S = 0.67

        is_submerged, S = self.gate.check_submergence(h_up, h_down)

        assert abs(S - 0.67) < 0.01
        print(f"\n临界淹没: S = {S:.3f}")


class TestDischargeCalculation:
    """测试流量计算"""

    def setup_method(self):
        """每个测试前的准备"""
        self.gate = RadialGate(
            width=15.0,
            crest_elevation=100.0,
            radius=8.0,
            design_head=10.0
        )

    def test_free_flow_discharge(self):
        """测试自由出流流量"""
        h_up = 110.0
        h_down = 101.0
        opening = 5.0

        Q, info = self.gate.compute_discharge(h_up, h_down, opening, 'absolute')

        assert Q > 0
        assert info['flow_type'] == 'free_flow'
        assert not info['is_submerged']
        assert 0.6 <= info['Cd'] <= 0.75

        print(f"\n自由出流: Q = {Q:.2f} m^3/s, Cd = {info['Cd']:.3f}")

    def test_submerged_flow_discharge(self):
        """测试淹没出流流量"""
        h_up = 110.0
        h_down = 108.0
        opening = 5.0

        Q, info = self.gate.compute_discharge(h_up, h_down, opening, 'absolute')

        assert Q > 0
        assert info['flow_type'] == 'submerged_flow'
        assert info['is_submerged']

        # 淹没出流流量应小于自由出流
        Q_free, _ = self.gate.compute_discharge(h_up, 101.0, opening, 'absolute')
        assert Q < Q_free

        print(f"\n淹没出流: Q = {Q:.2f} m^3/s, Cd = {info['Cd']:.3f}")
        print(f"自由出流: Q = {Q_free:.2f} m^3/s")
        print(f"流量比: {Q/Q_free:.3f}")

    def test_zero_opening(self):
        """测试零开度"""
        h_up = 110.0
        h_down = 101.0
        opening = 0.0

        Q, info = self.gate.compute_discharge(h_up, h_down, opening, 'absolute')

        assert Q == 0.0
        assert info['flow_type'] == 'no_flow'

    def test_no_head(self):
        """测试无水头"""
        h_up = 100.0   # 等于堰顶
        h_down = 101.0
        opening = 5.0

        Q, info = self.gate.compute_discharge(h_up, h_down, opening, 'absolute')

        assert Q == 0.0

    def test_percent_opening(self):
        """测试百分比开度"""
        h_up = 110.0
        h_down = 101.0
        opening_percent = 50.0  # 50% = 4m

        Q_percent, _ = self.gate.compute_discharge(h_up, h_down, opening_percent, 'percent')
        Q_absolute, _ = self.gate.compute_discharge(h_up, h_down, 4.0, 'absolute')

        # 两种表示方式应该给出相同结果
        assert abs(Q_percent - Q_absolute) < 1e-6

        print(f"\n50%开度: Q = {Q_percent:.2f} m^3/s")


class TestOpeningIncreaseFlow:
    """测试开度与流量关系"""

    def test_increasing_opening(self):
        """测试开度增加时流量增加"""
        gate = RadialGate(
            width=15.0,
            crest_elevation=100.0,
            radius=8.0,
            design_head=10.0
        )

        h_up = 110.0
        h_down = 101.0

        Q_prev = 0
        for opening in [1.0, 2.0, 3.0, 4.0, 5.0]:
            Q, _ = gate.compute_discharge(h_up, h_down, opening, 'absolute')
            assert Q > Q_prev
            Q_prev = Q
            print(f"开度 {opening}m: Q = {Q:.2f} m^3/s")


class TestInverseCalculation:
    """测试反算开度"""

    def setup_method(self):
        """每个测试前的准备"""
        self.gate = RadialGate(
            width=15.0,
            crest_elevation=100.0,
            radius=8.0,
            design_head=10.0
        )

    def test_inverse_for_target_flow(self):
        """测试反算开度"""
        h_up = 110.0
        h_down = 101.0
        Q_target = 500.0

        opening, info = self.gate.compute_opening_for_target_flow(
            h_up, h_down, Q_target
        )

        assert info['converged']
        assert 0 < opening <= self.gate.max_opening

        # 验证
        Q_check, _ = self.gate.compute_discharge(h_up, h_down, opening, 'absolute')
        error = abs(Q_check - Q_target) / Q_target * 100

        assert error < 1.0  # 误差小于1%

        print(f"\n目标流量: {Q_target:.2f} m^3/s")
        print(f"所需开度: {opening:.3f}m")
        print(f"验证流量: {Q_check:.2f} m^3/s")
        print(f"误差: {error:.3f}%")

    def test_inverse_convergence(self):
        """测试反算收敛性"""
        h_up = 110.0
        h_down = 101.0

        # 测试多个目标流量
        for Q_target in [100, 300, 500, 700, 900]:
            opening, info = self.gate.compute_opening_for_target_flow(
                h_up, h_down, Q_target
            )

            assert info['converged']
            assert info['iterations'] < 50

            Q_check, _ = self.gate.compute_discharge(h_up, h_down, opening, 'absolute')
            error = abs(Q_check - Q_target) / Q_target * 100
            assert error < 1.0


class TestDischargeCoefficient:
    """测试流量系数"""

    def test_cd_range(self):
        """测试流量系数在合理范围内"""
        gate = RadialGate(
            width=15.0,
            crest_elevation=100.0,
            radius=8.0,
            design_head=10.0
        )

        h_up = 110.0
        h_down = 101.0

        for opening in [1.0, 3.0, 5.0, 7.0]:
            _, info = gate.compute_discharge(h_up, h_down, opening, 'absolute')
            Cd = info['Cd']

            # 流量系数应在0.6-0.75之间
            assert 0.6 <= Cd <= 0.75

            print(f"开度 {opening}m: Cd = {Cd:.3f}")

    def test_cd_increases_with_opening(self):
        """测试流量系数随开度增加"""
        gate = RadialGate(
            width=15.0,
            crest_elevation=100.0,
            radius=8.0,
            design_head=10.0
        )

        h_up = 110.0
        h_down = 101.0

        Cd_prev = 0
        for opening in [1.0, 2.0, 3.0, 4.0, 5.0]:
            _, info = gate.compute_discharge(h_up, h_down, opening, 'absolute')
            Cd = info['Cd']

            # 流量系数应随开度增加（自由出流）
            assert Cd >= Cd_prev
            Cd_prev = Cd


class TestEdgeCases:
    """测试边界情况"""

    def test_max_opening(self):
        """测试最大开度"""
        gate = RadialGate(
            width=15.0,
            crest_elevation=100.0,
            radius=8.0,
            design_head=10.0
        )

        h_up = 110.0
        h_down = 101.0
        opening = 10.0  # 超过max_opening=8.0

        Q, info = gate.compute_discharge(h_up, h_down, opening, 'absolute')

        # 开度应被限制在max_opening
        assert info['opening'] == gate.max_opening

    def test_negative_opening(self):
        """测试负开度"""
        gate = RadialGate(
            width=15.0,
            crest_elevation=100.0,
            radius=8.0,
            design_head=10.0
        )

        h_up = 110.0
        h_down = 101.0
        opening = -1.0

        Q, info = gate.compute_discharge(h_up, h_down, opening, 'absolute')

        # 负开度应被限制为0
        assert Q == 0.0
        assert info['opening'] == 0.0


if __name__ == '__main__':
    # 运行所有测试
    pytest.main([__file__, '-v', '-s'])
