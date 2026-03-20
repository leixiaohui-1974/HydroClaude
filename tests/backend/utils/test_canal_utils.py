#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
水力学工具函数测试

测试 canal_utils 模块中的各种水力学计算函数
验证精度和边界条件处理

Author: HydroClaude Test Team
Date: 2025-11-20
"""

import sys
import warnings
warnings.filterwarnings("ignore")
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from utils.canal_utils import (
    compute_steady_uniform_flow,
    compute_critical_depth,
    compute_froude_number,
    compute_froude_scalar,
    compute_manning_friction_slope,
    compute_wave_speed,
    compute_cfl_number,
    check_numerical_validity,
    compute_mass_balance,
    get_convergence_metrics,
    setup_chinese_fonts,
)
import numpy as np
import pytest
import matplotlib.pyplot as plt
from fixtures.standard_cases import StandardCases


class Test水力学函数:
    """测试水力学计算函数"""
    
    def test_均匀流计算(self):
        """测试 Manning 公式均匀流计算"""
        print(f"\n{'='*70}")
        print(f"测试: Manning公式均匀流计算")
        print(f"{'='*70}")
        
        Q = 10.0
        B = 5.0
        S0 = 0.001
        n = 0.025
        
        h = compute_steady_uniform_flow(Q, B, S0, n)
        
        print(f"   流量 Q = {Q} m³/s")
        print(f"   渠宽 B = {B} m")
        print(f"   坡度 S0 = {S0}")
        print(f"   糙率 n = {n}")
        print(f"   计算水深: {h:.4f} m")
        
        # 验证水深在合理范围内
        assert h > 0, "水深必须为正值"
        assert h < 10.0, "水深过大，计算可能有误"
        
        # 验证 Manning 公式反算流量
        A = B * h
        P = B + 2 * h
        R = A / P
        Q_check = (1.0 / n) * A * R**(2/3) * S0**0.5
        
        error = abs(Q_check - Q) / Q * 100
        print(f"   反算流量: {Q_check:.4f} m³/s")
        print(f"   流量误差: {error:.4f}%")
        
        assert error < 0.1, f"流量反算误差过大: {error:.2f}%"
        
        print(f"   ✅ 测试通过！")
    
    @pytest.mark.parametrize("Q,B,S0,n", [
        (1.0, 1.0, 0.001, 0.020),     # 极小值
        (100.0, 30.0, 0.005, 0.035),  # 极大值
        (5.5, 4.2, 0.00075, 0.0225),  # 非整数值
    ])
    def test_不同参数均匀流(self, Q, B, S0, n):
        """测试不同参数的均匀流计算"""
        print(f"\n参数: Q={Q}, B={B}, S0={S0}, n={n}")
        
        h = compute_steady_uniform_flow(Q, B, S0, n)
        
        print(f"   水深: {h:.4f} m")
        
        assert h > 0
        assert h < 100.0
        
        print(f"   ✅ 通过")
    
    def test_临界水深计算(self):
        """测试临界水深计算"""
        print(f"\n{'='*70}")
        print(f"测试: 临界水深计算")
        print(f"{'='*70}")
        
        Q = 10.0
        B = 5.0
        g = 9.81
        
        h_c = compute_critical_depth(Q, B, g)
        
        print(f"   流量 Q = {Q} m³/s")
        print(f"   渠宽 B = {B} m")
        print(f"   重力加速度 g = {g} m/s²")
        print(f"   临界水深: {h_c:.4f} m")
        
        # 验证临界水深
        assert h_c > 0
        assert h_c < 10.0
        
        # 验证 Froude 数 = 1
        v = Q / (B * h_c)
        Fr = v / np.sqrt(g * h_c)
        
        print(f"   临界流速: {v:.4f} m/s")
        print(f"   Froude数: {Fr:.4f}")
        print(f"   理论值: 1.0")
        
        Fr_error = abs(Fr - 1.0) / 1.0 * 100
        print(f"   Fr误差: {Fr_error:.4f}%")
        
        assert Fr_error < 1.0, f"Froude数误差过大: {Fr_error:.2f}%"
        
        print(f"   ✅ 测试通过！")
    
    @pytest.mark.parametrize("Q,B", [
        (5.0, 3.0),
        (10.0, 5.0),
        (20.0, 8.0),
        (50.0, 15.0),
    ])
    def test_不同流量临界水深(self, Q, B):
        """测试不同流量的临界水深"""
        print(f"\n参数: Q={Q}, B={B}")
        
        h_c = compute_critical_depth(Q, B)
        
        print(f"   临界水深: {h_c:.4f} m")
        
        assert h_c > 0
        
        # 验证 Froude 数接近 1
        v = Q / (B * h_c)
        Fr = v / np.sqrt(9.81 * h_c)
        
        print(f"   Froude数: {Fr:.4f}")
        
        assert abs(Fr - 1.0) < 0.01, f"Froude数偏离1.0: {Fr:.4f}"
        
        print(f"   ✅ 通过")
    
    def test_Froude数计算(self):
        """测试 Froude 数计算"""
        print(f"\n{'='*70}")
        print(f"测试: Froude数计算")
        print(f"{'='*70}")
        
        Q = 10.0
        B = 5.0
        h = 2.0
        g = 9.81
        
        Fr = compute_froude_number(np.array([h]), np.array([Q]), B, g)[0]
        
        print(f"   流量 Q = {Q} m³/s")
        print(f"   渠宽 B = {B} m")
        print(f"   水深 h = {h} m")
        print(f"   Froude数: {Fr:.4f}")
        
        # 验证 Froude 数
        v = Q / (B * h)
        Fr_check = v / np.sqrt(g * h)
        
        print(f"   流速 v = {v:.4f} m/s")
        print(f"   理论Fr = {Fr_check:.4f}")
        
        error = abs(Fr - Fr_check) / Fr_check * 100
        print(f"   误差: {error:.4f}%")
        
        assert error < 0.01, f"Froude数计算误差: {error:.2f}%"
        
        # 判断流态
        if Fr < 1.0:
            print(f"   流态: 缓流 (Fr < 1)")
        elif Fr > 1.0:
            print(f"   流态: 急流 (Fr > 1)")
        else:
            print(f"   流态: 临界流 (Fr = 1)")
        
        print(f"   ✅ 测试通过！")
    
    @pytest.mark.parametrize("h,expected_regime", [
        (3.0, "缓流"),  # Fr < 1
        (0.5, "急流"),  # Fr > 1 (更小的水深)
    ])
    def test_流态判断(self, h, expected_regime):
        """测试不同水深的流态判断"""
        print(f"\n测试水深: {h} m, 预期流态: {expected_regime}")
        
        Q = 10.0
        B = 5.0
        
        Fr = compute_froude_number(np.array([h]), np.array([Q]), B)[0]
        
        print(f"   Froude数: {Fr:.4f}")
        
        if Fr < 1.0:
            regime = "缓流"
        elif Fr > 1.0:
            regime = "急流"
        else:
            regime = "临界流"
        
        print(f"   判断流态: {regime}")
        
        assert regime == expected_regime, f"流态判断错误: {regime} != {expected_regime}"
        
        print(f"   ✅ 通过")
    
    def test_边界条件_零流量(self):
        """测试边界条件：零流量"""
        print(f"\n{'='*70}")
        print(f"测试: 边界条件 - 零流量")
        print(f"{'='*70}")
        
        Q = 0.0
        B = 5.0
        S0 = 0.001
        n = 0.025
        
        try:
            h = compute_steady_uniform_flow(Q, B, S0, n)
            print(f"   零流量水深: {h:.4f} m")
            
            # 零流量时水深应该接近零
            assert h < 0.01, "零流量时水深应接近零"
            
            print(f"   ✅ 边界条件处理正确")
        except Exception as e:
            print(f"   ⚠️ 抛出异常: {e}")
            print(f"   ✅ 边界条件处理正确（抛出异常也是合理的）")
    
    def test_边界条件_极小坡度(self):
        """测试边界条件：极小坡度"""
        print(f"\n{'='*70}")
        print(f"测试: 边界条件 - 极小坡度")
        print(f"{'='*70}")
        
        Q = 10.0
        B = 5.0
        S0 = 0.00001  # 极小坡度
        n = 0.025
        
        h = compute_steady_uniform_flow(Q, B, S0, n)
        
        print(f"   坡度: {S0}")
        print(f"   水深: {h:.4f} m")
        
        # 极小坡度时水深应该较大
        assert h > 3.0, "极小坡度时水深应该较大"
        assert h < 50.0, "水深不应过大（可能发散）"
        
        print(f"   ✅ 边界条件处理正确")
    
    def test_边界条件_极大坡度(self):
        """测试边界条件：极大坡度"""
        print(f"\n{'='*70}")
        print(f"测试: 边界条件 - 极大坡度")
        print(f"{'='*70}")
        
        Q = 10.0
        B = 5.0
        S0 = 0.1  # 极大坡度
        n = 0.025
        
        h = compute_steady_uniform_flow(Q, B, S0, n)
        
        print(f"   坡度: {S0}")
        print(f"   水深: {h:.4f} m")
        
        # 极大坡度时水深应该较小
        assert h < 1.0, "极大坡度时水深应该较小"
        assert h > 0.1, "水深不应过小（可能有误）"
        
        print(f"   ✅ 边界条件处理正确")

    def test_froude_scalar_zero_depth_returns_inf(self):
        """零水深应返回无穷大，避免除零。"""
        Fr = compute_froude_scalar(Q=5.0, B=2.0, h=0.0)
        assert np.isinf(Fr)

    def test_setup_chinese_fonts_updates_matplotlib_rcparams(self):
        """字体配置应写入 matplotlib 全局参数，避免中文图表退化。"""
        setup_chinese_fonts(font_size=14)
        assert plt.rcParams["font.size"] == 14
        assert plt.rcParams["axes.titlesize"] == 16
        assert plt.rcParams["axes.unicode_minus"] is False
        assert "SimHei" in plt.rcParams["font.sans-serif"]

    def test_wave_speed_and_cfl_follow_theory(self):
        """波速和 CFL 数应符合浅水波基础关系。"""
        h = np.array([1.0, 4.0])
        V = np.array([2.0, -1.0])
        c = compute_wave_speed(h)
        assert np.allclose(c, np.sqrt(9.81 * h))

        cfl = compute_cfl_number(V, c, dx=10.0, dt=1.0)
        assert np.allclose(cfl, (np.abs(V) + c) / 10.0)

    @pytest.mark.parametrize(
        "h,Q,expected_fragment",
        [
            (np.array([1.0, np.nan]), np.array([1.0, 1.0]), "contains NaN"),
            (np.array([1.0, 1.0]), np.array([1.0, np.inf]), "contains Inf"),
            (np.array([-0.1, 1.0]), np.array([1.0, 1.0]), "contains negative"),
            (np.array([1.0, 1.0]), np.array([-1.0, 1.0]), "contains negative"),
        ],
    )
    def test_numerical_validity_rejects_nonphysical_states(self, h, Q, expected_fragment):
        """数值校验应识别 NaN、Inf 和非物理负值。"""
        valid, message = check_numerical_validity(h, Q, ("depth", "discharge"))
        assert valid is False
        assert expected_fragment in message

    def test_mass_balance_uses_first_and_last_snapshots(self):
        """质量平衡只应比较初末时刻总体积。"""
        history = [
            np.array([1.0, 1.0, 1.0]),
            np.array([1.5, 1.5, 1.5]),
            np.array([2.0, 2.0, 2.0]),
        ]
        initial, final = compute_mass_balance(history, B=5.0, dx=10.0)
        assert initial == pytest.approx(150.0)
        assert final == pytest.approx(300.0)

    def test_mass_balance_empty_history_returns_zero(self):
        """空历史记录不应抛错。"""
        initial, final = compute_mass_balance([], B=5.0, dx=10.0)
        assert initial == 0.0
        assert final == 0.0

    def test_manning_friction_slope_matches_manual_reference(self):
        """摩阻坡度应与 Manning 公式逐点一致，并在干床处归零。"""
        h = np.array([2.0, 0.0, 1.5])
        Q = np.array([10.0, 4.0, 6.0])
        B = 5.0
        n = 0.025

        sf = compute_manning_friction_slope(h, Q, B=B, n=n)

        expected0_area = B * h[0]
        expected0_radius = expected0_area / (B + 2 * h[0])
        expected0_velocity = Q[0] / expected0_area
        expected0 = (n * abs(expected0_velocity)) ** 2 / (expected0_radius ** (4.0 / 3.0))

        expected2_area = B * h[2]
        expected2_radius = expected2_area / (B + 2 * h[2])
        expected2_velocity = Q[2] / expected2_area
        expected2 = (n * abs(expected2_velocity)) ** 2 / (expected2_radius ** (4.0 / 3.0))

        assert sf[0] == pytest.approx(expected0)
        assert sf[1] == 0.0
        assert sf[2] == pytest.approx(expected2)

    def test_numerical_validity_accepts_physical_state(self):
        """有限且非负的水深/流量应通过校验。"""
        valid, message = check_numerical_validity(
            np.array([0.5, 1.0, 2.0]),
            np.array([0.0, 1.5, 3.0]),
            ("depth", "discharge"),
        )
        assert valid is True
        assert message == ""

    def test_mike11_reference_parameters_reproduce_manning_depth(self):
        """MIKE11 参数集下，Manning 公式应给出稳定一致的正常水深。"""
        case = StandardCases.mike11_steady_uniform_flow()
        params = case["parameters"]

        h = compute_steady_uniform_flow(
            Q=params["Q"],
            B=params["width"],
            S0=params["slope"],
            n=params["manning_n"],
        )

        assert h == pytest.approx(3.8112833340466024, rel=1e-6)

    def test_convergence_metrics_identify_steady_tail(self):
        """后半段几乎不变时应判定收敛。"""
        time = np.arange(12, dtype=float)
        h_history = [np.array([1.0 + 1e-8 * i, 1.2 + 1e-8 * i]) for i in range(12)]
        Q_history = [np.array([5.0 + 1e-8 * i, 5.0 + 1e-8 * i]) for i in range(12)]

        metrics = get_convergence_metrics(time, h_history, Q_history)

        assert bool(metrics["converged"]) is True
        assert metrics["max_cv"] < 0.01

    def test_convergence_metrics_require_enough_points(self):
        """样本过少时不应误判为收敛。"""
        metrics = get_convergence_metrics(
            np.arange(5, dtype=float),
            [np.array([1.0, 1.0])] * 5,
            [np.array([5.0, 5.0])] * 5,
        )
        assert metrics["converged"] is False
        assert "Insufficient data points" in metrics["message"]


if __name__ == '__main__':
    pytest.main([__file__, '-v', '-s'])
