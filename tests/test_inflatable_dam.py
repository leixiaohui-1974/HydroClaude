#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
充气坝单元测试

测试内容：
1. 基本参数
2. 充气/放气操作
3. 流量计算
4. 高度控制
5. 时间计算
6. 应急场景

作者：HydroClaude Team
日期：2025-10-28
"""

import pytest
import numpy as np
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from physics.structures.inflatable_dam import InflatableDam


class TestInflatableDamBasics:
    """测试充气坝基本功能"""

    def test_dam_creation(self):
        """测试充气坝创建"""
        dam = InflatableDam(
            width=50.0,
            crest_elevation=100.0,
            max_height=3.0,
            shape_type='circular'
        )

        assert dam.width == 50.0
        assert dam.crest_elevation == 100.0
        assert dam.max_height == 3.0
        assert dam.current_height == 0.0  # 初始倒伏
        assert dam.shape_type == 'circular'

    def test_initial_deflated_state(self):
        """测试初始倒伏状态"""
        dam = InflatableDam(
            width=50.0,
            crest_elevation=100.0,
            max_height=3.0
        )

        status = dam.get_status()

        assert status['current_height'] == 0.0
        assert status['is_deflated']
        assert not status['is_fully_inflated']
        assert status['inflation_percent'] == 0.0


class TestInflationDeflation:
    """测试充气/放气操作"""

    def setup_method(self):
        """每个测试前的准备"""
        self.dam = InflatableDam(
            width=50.0,
            crest_elevation=100.0,
            max_height=3.0,
            inflation_rate=0.05,   # 5cm/min
            deflation_rate=0.10    # 10cm/min
        )

    def test_inflation(self):
        """测试充气操作"""
        duration = 30.0  # 30分钟
        final_height = self.dam.inflate(duration)

        expected_height = 0.0 + 0.05 * 30.0  # 1.5m
        assert abs(final_height - expected_height) < 1e-6

        print(f"\n充气30分钟: {final_height:.2f}m")

    def test_deflation(self):
        """测试放气操作"""
        # 先充气到最大
        self.dam.set_height(3.0)
        assert self.dam.current_height == 3.0

        # 放气20分钟
        duration = 20.0
        final_height = self.dam.deflate(duration)

        expected_height = 3.0 - 0.10 * 20.0  # 1.0m
        assert abs(final_height - expected_height) < 1e-6

        print(f"\n放气20分钟: {final_height:.2f}m")

    def test_inflation_limit(self):
        """测试充气上限"""
        # 充气时间很长，应该被限制在max_height
        duration = 100.0  # 100分钟
        final_height = self.dam.inflate(duration)

        assert final_height == self.dam.max_height
        assert self.dam.get_status()['is_fully_inflated']

    def test_deflation_limit(self):
        """测试放气下限"""
        self.dam.set_height(1.0)

        # 放气时间很长，应该被限制在0
        duration = 100.0
        final_height = self.dam.deflate(duration)

        assert final_height == 0.0
        assert self.dam.get_status()['is_deflated']

    def test_set_height_direct(self):
        """测试直接设置高度"""
        self.dam.set_height(2.5)

        assert self.dam.current_height == 2.5

        status = self.dam.get_status()
        assert status['current_height'] == 2.5
        assert status['inflation_percent'] == 2.5 / 3.0 * 100


class TestDischargeCalculation:
    """测试流量计算"""

    def setup_method(self):
        """每个测试前的准备"""
        self.dam = InflatableDam(
            width=50.0,
            crest_elevation=100.0,
            max_height=3.0
        )

    def test_deflated_no_obstruction(self):
        """测试倒伏状态无阻水"""
        self.dam.set_height(0.0)

        h_up = 101.0
        h_down = 100.5

        Q, info = self.dam.compute_discharge(h_up, h_down)

        # 倒伏状态应该有流量（作为堰流）
        assert Q > 0
        assert info['is_deflated']

        print(f"\n倒伏状态流量: Q = {Q:.2f} m^3/s")

    def test_inflated_overflow(self):
        """测试充气状态溢流"""
        self.dam.set_height(2.0)

        h_up = 103.0  # 高于坝顶
        h_down = 100.5

        Q, info = self.dam.compute_discharge(h_up, h_down)

        assert Q > 0
        assert info['flow_type'] in ['free_overflow', 'submerged_overflow']
        assert info['H'] > 0

        print(f"\n充气状态溢流: Q = {Q:.2f} m^3/s, H = {info['H']:.2f}m")

    def test_no_overflow(self):
        """测试无溢流"""
        self.dam.set_height(2.0)

        h_up = 101.5  # 低于坝顶 (100 + 2 = 102)
        h_down = 100.5

        Q, info = self.dam.compute_discharge(h_up, h_down)

        assert Q == 0.0
        assert info['flow_type'] == 'no_overflow'

    def test_increasing_height_decreases_flow(self):
        """测试坝高增加时流量减小"""
        h_up = 104.0
        h_down = 101.0

        Q_prev = float('inf')

        for height in [0.0, 1.0, 2.0, 3.0]:
            self.dam.set_height(height)
            Q, _ = self.dam.compute_discharge(h_up, h_down)

            # 坝高增加，过坝水头减小，流量应该减小
            assert Q < Q_prev
            Q_prev = Q

            print(f"坝高 {height}m: Q = {Q:.2f} m^3/s")


class TestDischargeCoefficient:
    """测试流量系数"""

    def test_cd_range(self):
        """测试流量系数在合理范围内"""
        dam = InflatableDam(
            width=50.0,
            crest_elevation=100.0,
            max_height=3.0,
            shape_type='circular'
        )

        dam.set_height(2.0)

        h_up = 104.0
        h_down = 101.0

        _, info = dam.compute_discharge(h_up, h_down)
        Cd = info['Cd']

        # 充气坝流量系数应在0.40-0.55之间
        assert 0.40 <= Cd <= 0.55

        print(f"\n流量系数: Cd = {Cd:.3f}")

    def test_shape_type_effect(self):
        """测试坝体形状对流量系数的影响"""
        dam_circular = InflatableDam(
            width=50.0,
            crest_elevation=100.0,
            max_height=3.0,
            shape_type='circular'
        )

        dam_streamlined = InflatableDam(
            width=50.0,
            crest_elevation=100.0,
            max_height=3.0,
            shape_type='streamlined'
        )

        dam_circular.set_height(2.0)
        dam_streamlined.set_height(2.0)

        h_up = 103.0
        h_down = 101.0

        Q_circular, info_c = dam_circular.compute_discharge(h_up, h_down)
        Q_streamlined, info_s = dam_streamlined.compute_discharge(h_up, h_down)

        # 流线型流量系数应该更大
        assert info_s['Cd'] >= info_c['Cd']
        assert Q_streamlined >= Q_circular

        print(f"\n圆弧形: Cd = {info_c['Cd']:.3f}, Q = {Q_circular:.2f} m^3/s")
        print(f"流线型: Cd = {info_s['Cd']:.3f}, Q = {Q_streamlined:.2f} m^3/s")


class TestTimeCalculation:
    """测试时间计算"""

    def setup_method(self):
        """每个测试前的准备"""
        self.dam = InflatableDam(
            width=50.0,
            crest_elevation=100.0,
            max_height=3.0,
            inflation_rate=0.05,
            deflation_rate=0.10
        )

    def test_inflation_time(self):
        """测试充气时间计算"""
        self.dam.set_height(0.0)
        target = 2.5

        time_needed = self.dam.compute_inflation_time(target)

        # 手算: 2.5 / 0.05 = 50 min
        expected_time = 2.5 / 0.05
        assert abs(time_needed - expected_time) < 1e-6

        print(f"\n充气到{target}m所需时间: {time_needed:.1f} min")

    def test_deflation_time(self):
        """测试放气时间计算"""
        self.dam.set_height(3.0)
        target = 0.5

        time_needed = self.dam.compute_inflation_time(target)

        # 手算: (3.0 - 0.5) / 0.10 = 25 min
        expected_time = (3.0 - 0.5) / 0.10
        assert abs(time_needed - expected_time) < 1e-6

        print(f"\n放气到{target}m所需时间: {time_needed:.1f} min")

    def test_no_change_time(self):
        """测试无需调整时间为0"""
        self.dam.set_height(2.0)
        target = 2.0

        time_needed = self.dam.compute_inflation_time(target)

        assert time_needed == 0.0


class TestEmergencyScenarios:
    """测试应急场景"""

    def test_flood_emergency_deflation(self):
        """测试洪水来临紧急泄洪"""
        dam = InflatableDam(
            width=50.0,
            crest_elevation=100.0,
            max_height=3.0,
            inflation_rate=0.05,
            deflation_rate=0.10  # 放气速度快
        )

        # 初始满充气状态
        dam.set_height(3.0)
        assert dam.get_status()['is_fully_inflated']

        # 计算完全倒伏所需时间
        time_to_deflate = dam.compute_inflation_time(0.0)

        print(f"\n应急泄洪时间: {time_to_deflate:.1f} min")

        # 执行放气
        dam.deflate(time_to_deflate)

        # 应该完全倒伏
        assert dam.current_height == 0.0
        assert dam.get_status()['is_deflated']

    def test_rapid_response_capability(self):
        """测试快速响应能力"""
        dam = InflatableDam(
            width=50.0,
            crest_elevation=100.0,
            max_height=3.0,
            inflation_rate=0.10,   # 快速充气
            deflation_rate=0.20    # 更快放气
        )

        # 从倒伏到满充气
        time_inflate = dam.compute_inflation_time(3.0)
        assert time_inflate == 3.0 / 0.10  # 30 min

        # 从满充气到倒伏
        dam.set_height(3.0)
        time_deflate = dam.compute_inflation_time(0.0)
        assert time_deflate == 3.0 / 0.20  # 15 min

        print(f"\n快速响应:")
        print(f"  充气时间: {time_inflate:.1f} min")
        print(f"  放气时间: {time_deflate:.1f} min")


class TestStatus:
    """测试状态查询"""

    def test_status_reporting(self):
        """测试状态报告"""
        dam = InflatableDam(
            width=50.0,
            crest_elevation=100.0,
            max_height=3.0
        )

        # 倒伏状态
        status = dam.get_status()
        assert status['is_deflated']
        assert not status['is_fully_inflated']
        assert status['inflation_percent'] == 0.0

        # 半充气状态
        dam.set_height(1.5)
        status = dam.get_status()
        assert not status['is_deflated']
        assert not status['is_fully_inflated']
        assert abs(status['inflation_percent'] - 50.0) < 1e-6

        # 满充气状态
        dam.set_height(3.0)
        status = dam.get_status()
        assert not status['is_deflated']
        assert status['is_fully_inflated']
        assert abs(status['inflation_percent'] - 100.0) < 1e-6

        print(f"\n状态测试:")
        print(f"  倒伏: ")
        print(f"  半充气: ")
        print(f"  满充气: ")


if __name__ == '__main__':
    # 运行所有测试
    pytest.main([__file__, '-v', '-s'])
