#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
复合糙率功能测试

测试复式断面的分区糙率计算，确保：
1. 不同计算方法结果合理
2. 与手算结果对比
3. 流量分配正确（质量守恒）
4. 等效糙率系数合理

作者：HydroClaude Team
日期：2025-10-28
"""

import pytest
import warnings
warnings.filterwarnings("ignore")
import numpy as np
import sys
import os

# 添加项目路径
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from physics.composite_roughness import (
    CompositeRoughness, RoughnessZone, CompositeMethod,
    compute_friction_slope_composite
)
from physics.cross_section import CompoundSection


class TestRoughnessZone:
    """测试糙率分区基本功能"""

    def test_zone_creation(self):
        """测试分区创建"""
        zone = RoughnessZone("main", area=10.0, perimeter=12.0, manning_n=0.025)

        assert zone.name == "main"
        assert zone.area == 10.0
        assert zone.perimeter == 12.0
        assert zone.manning_n == 0.025
        assert abs(zone.hydraulic_radius - 10.0/12.0) < 1e-6

    def test_conveyance_calculation(self):
        """测试输沙能力计算"""
        # 矩形断面: b=10m, h=2m, n=0.025
        A = 20.0
        P = 14.0  # 10 + 2*2
        R = A / P
        n = 0.025

        zone = RoughnessZone("test", A, P, n)
        K = zone.compute_conveyance()

        # 手算: K = (1/n) * A * R^(2/3)
        K_expected = (1/n) * A * (R ** (2.0/3.0))

        assert abs(K - K_expected) < 1e-6

    def test_zero_area(self):
        """测试零面积情况"""
        zone = RoughnessZone("dry", 0.0, 1.0, 0.025)
        K = zone.compute_conveyance()
        assert K == 0.0


class TestCompositeRoughness:
    """测试复合糙率计算器"""

    def setup_method(self):
        """每个测试前的准备"""
        # 创建标准复式断面的三个分区
        # 主槽: b=10m, h=2m, m=1.5, n=0.025
        h_main = 2.0
        b_main = 10.0
        m_main = 1.5
        self.A_main = (b_main + m_main * h_main) * h_main
        self.P_main = b_main + 2 * h_main * np.sqrt(1 + m_main**2)

        # 滩地: 左右各15m, h=1m, n=0.060
        h_flood = 1.0
        b_flood = 15.0
        self.A_flood = b_flood * h_flood
        self.P_flood = h_flood

        self.zone_main = RoughnessZone("main", self.A_main, self.P_main, 0.025)
        self.zone_left = RoughnessZone("left", self.A_flood, self.P_flood, 0.060)
        self.zone_right = RoughnessZone("right", self.A_flood, self.P_flood, 0.060)

        self.zones = [self.zone_main, self.zone_left, self.zone_right]

    def test_hec_ras_method(self):
        """测试HEC-RAS方法"""
        calc = CompositeRoughness(method=CompositeMethod.HEC_RAS)
        K_total = calc.compute_composite_conveyance(self.zones)

        # 手算验证
        K_main = self.zone_main.compute_conveyance()
        K_left = self.zone_left.compute_conveyance()
        K_right = self.zone_right.compute_conveyance()
        K_expected = K_main + K_left + K_right

        assert abs(K_total - K_expected) < 1e-6

    def test_horton_method(self):
        """测试Horton公式"""
        calc = CompositeRoughness(method=CompositeMethod.HORTON)
        K_total = calc.compute_composite_conveyance(self.zones)

        # Horton公式应该给出不同的结果
        calc_hec = CompositeRoughness(method=CompositeMethod.HEC_RAS)
        K_hec = calc_hec.compute_composite_conveyance(self.zones)

        # 结果应该不同但在合理范围内
        assert K_total != K_hec
        assert K_total > 0
        assert 0.5 < K_total / K_hec < 1.5

    def test_lotter_method(self):
        """测试Lotter公式"""
        calc = CompositeRoughness(method=CompositeMethod.LOTTER)
        K_total = calc.compute_composite_conveyance(self.zones)

        assert K_total > 0

    def test_composite_manning_n(self):
        """测试等效曼宁系数计算"""
        calc = CompositeRoughness(method=CompositeMethod.HEC_RAS)
        n_eq = calc.compute_composite_manning_n(self.zones)

        # 等效糙率应该在主槽和滩地糙率之间
        assert 0.025 <= n_eq <= 0.060
        print(f"\n等效曼宁系数: n_eq = {n_eq:.4f}")

    def test_flow_distribution(self):
        """测试流量分配"""
        calc = CompositeRoughness(method=CompositeMethod.HEC_RAS)

        Q_total = 100.0  # m^3/s
        slope = 0.001

        flow_dist = calc.compute_flow_distribution(self.zones, Q_total, slope)

        # 检查质量守恒
        Q_sum = sum(flow_dist.values())
        assert abs(Q_sum - Q_total) < 1e-10

        # 检查所有分区都有流量
        for zone in self.zones:
            assert flow_dist[zone.name] > 0

        # 主槽流速应该比滩地快（糙率小）
        # 但滩地面积大，所以流量分配取决于输沙能力
        print(f"\n流量分配:")
        for name, Q in flow_dist.items():
            print(f"  {name}: {Q:.2f} m^3/s ({Q/Q_total*100:.1f}%)")

    def test_friction_slope(self):
        """测试摩阻坡度计算"""
        Q_total = 100.0
        Sf = compute_friction_slope_composite(self.zones, Q_total)

        assert Sf > 0
        assert Sf < 0.1  # 合理范围
        print(f"\n摩阻坡度: Sf = {Sf:.6f}")


class TestCompoundSectionRoughness:
    """测试复式断面类的糙率功能"""

    def test_zones_computation(self):
        """测试分区计算"""
        section = CompoundSection(
            name="Test",
            main_bottom_width=10.0,
            main_depth=3.0,
            main_side_slope=1.5,
            flood_width_left=15.0,
            flood_width_right=15.0,
            roughness_zones={
                'main': 0.025,
                'left_flood': 0.060,
                'right_flood': 0.060
            }
        )

        # 测试水深在主槽内
        depth = 2.0
        zones = section.compute_zones(depth)

        assert len(zones) == 1  # 只有主槽
        A, P, n, name = zones[0]
        assert name == 'main'
        assert n == 0.025
        assert A > 0
        assert P > 0

        # 测试水深超过主槽
        depth = 4.0  # 超过main_depth=3.0
        zones = section.compute_zones(depth)

        assert len(zones) == 3  # 主槽+左滩+右滩
        names = [z[3] for z in zones]
        assert 'main' in names
        assert 'left_flood' in names
        assert 'right_flood' in names

    def test_composite_conveyance(self):
        """测试复合输沙能力计算"""
        section = CompoundSection(
            name="Test",
            main_bottom_width=10.0,
            main_depth=3.0,
            main_side_slope=1.5,
            flood_width_left=15.0,
            flood_width_right=15.0,
            roughness_zones={
                'main': 0.025,
                'left_flood': 0.060,
                'right_flood': 0.060
            }
        )

        depth = 4.0  # 超过主槽
        K = section.compute_composite_conveyance(depth, method='hec_ras')

        assert K > 0
        print(f"\n复式断面输沙能力: K = {K:.2f} m^3/s")

    def test_composite_manning_n(self):
        """测试等效曼宁系数"""
        section = CompoundSection(
            name="Test",
            main_bottom_width=10.0,
            main_depth=3.0,
            main_side_slope=1.5,
            flood_width_left=15.0,
            flood_width_right=15.0,
            roughness_zones={
                'main': 0.025,
                'left_flood': 0.060,
                'right_flood': 0.060
            }
        )

        # 水深在主槽内：等效糙率应该接近主槽糙率
        depth = 2.0
        n_eq = section.compute_composite_manning_n(depth)
        assert abs(n_eq - 0.025) < 0.005

        # 水深超过主槽：等效糙率介于主槽和滩地之间
        depth = 4.0
        n_eq = section.compute_composite_manning_n(depth)
        assert 0.025 <= n_eq <= 0.060

        print(f"\n等效糙率 (h={depth}m): n_eq = {n_eq:.4f}")

    def test_different_roughness_zones(self):
        """测试不同的糙率组合"""
        # 场景1: 滩地糙率很大（茂密植被）
        section1 = CompoundSection(
            name="Heavy Vegetation",
            main_bottom_width=10.0,
            main_depth=3.0,
            main_side_slope=1.5,
            flood_width_left=15.0,
            flood_width_right=15.0,
            roughness_zones={
                'main': 0.025,
                'left_flood': 0.100,  # 茂密植被
                'right_flood': 0.100
            }
        )

        depth = 4.0
        K1 = section1.compute_composite_conveyance(depth)
        n1 = section1.compute_composite_manning_n(depth)

        # 场景2: 滩地糙率较小（草地）
        section2 = CompoundSection(
            name="Grass",
            main_bottom_width=10.0,
            main_depth=3.0,
            main_side_slope=1.5,
            flood_width_left=15.0,
            flood_width_right=15.0,
            roughness_zones={
                'main': 0.025,
                'left_flood': 0.035,  # 草地
                'right_flood': 0.035
            }
        )

        K2 = section2.compute_composite_conveyance(depth)
        n2 = section2.compute_composite_manning_n(depth)

        # 糙率大的应该输沙能力小、等效糙率大
        assert K1 < K2
        assert n1 > n2

        print(f"\n不同糙率对比 (h={depth}m):")
        print(f"  茂密植被: K={K1:.2f}, n_eq={n1:.4f}")
        print(f"  草地:     K={K2:.2f}, n_eq={n2:.4f}")


class TestMethodComparison:
    """对比不同复合糙率计算方法"""

    def test_method_comparison(self):
        """对比HEC-RAS、Horton、Lotter三种方法"""
        # 创建复式断面
        section = CompoundSection(
            name="Comparison",
            main_bottom_width=10.0,
            main_depth=3.0,
            main_side_slope=1.5,
            flood_width_left=15.0,
            flood_width_right=15.0,
            roughness_zones={
                'main': 0.025,
                'left_flood': 0.060,
                'right_flood': 0.060
            }
        )

        depth = 4.0

        methods = ['hec_ras', 'horton', 'lotter']
        results = {}

        print(f"\n不同方法对比 (h={depth}m):")
        print("-" * 60)

        for method in methods:
            K = section.compute_composite_conveyance(depth, method=method)
            n_eq = section.compute_composite_manning_n(depth, method=method)
            results[method] = {'K': K, 'n_eq': n_eq}

            print(f"{method:12s}: K = {K:8.2f} m^3/s, n_eq = {n_eq:.4f}")

        # HEC-RAS方法通常给出最大的K值（最保守）
        K_hec = results['hec_ras']['K']
        K_horton = results['horton']['K']
        K_lotter = results['lotter']['K']

        # 所有方法都应该给出正值
        assert K_hec > 0
        assert K_horton > 0
        assert K_lotter > 0


if __name__ == '__main__':
    # 运行所有测试
    pytest.main([__file__, '-v', '-s'])
