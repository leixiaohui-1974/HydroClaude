#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
水锤MOC求解器单元测试 / Unit Tests for Water Hammer MOC Solver

作者: HydroClaude Team
日期: 2025-10-30
"""

import pytest
import warnings
warnings.filterwarnings("ignore")
import numpy as np
import sys
import os

# 添加项目根目录到路径
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

try:
    from solvers.water_hammer_moc_solver import WaterHammerMOCSolver, WaterHammerBoundary
except ImportError as e:
    pytest.skip(f"Required module not available: {e}", allow_module_level=True)



class TestWaterHammerMOCSolver:
    """水锤MOC求解器测试套件"""

    def test_solver_initialization(self):
        """测试求解器初始化"""
        solver = WaterHammerMOCSolver(
            L=1000.0,
            D=0.5,
            f=0.02,
            wave_speed=1000.0
        )

        assert solver.L == 1000.0
        assert solver.D == 0.5
        assert solver.f == 0.02
        assert solver.a == 1000.0
        assert abs(solver.A - np.pi * 0.5**2 / 4.0) < 1e-10
        print(" 求解器初始化测试通过")

    def test_wave_speed_calculation(self):
        """测试波速计算"""
        solver = WaterHammerMOCSolver(
            L=1000.0,
            D=0.5,
            f=0.02
        )

        # 使用默认参数计算波速
        a = solver.calculate_wave_speed(
            K=2.1e9,   # 水的体积模量
            E=2.0e11,  # 钢管弹性模量
            e=0.01,    # 壁厚
            rho=1000.0
        )

        # 验证波速在合理范围内 (800-1400 m/s for steel pipes)
        assert 800 < a < 1400
        print(f" 波速计算测试通过: a = {a:.1f} m/s")

    def test_wave_speed_formula(self):
        """测试波速计算公式"""
        solver = WaterHammerMOCSolver(L=1000, D=0.5, f=0.02)

        # 纯水中的波速（刚性管）
        K = 2.1e9
        rho = 1000.0
        a_rigid = np.sqrt(K / rho)
        assert abs(a_rigid - 1449.1) < 1.0  # 理论值约1449 m/s

        # 考虑管壁弹性
        E = 2.0e11
        e = 0.01
        a_elastic = solver.calculate_wave_speed(K, E, e, rho)

        # 弹性管中波速应低于刚性管
        assert a_elastic < a_rigid
        print(f" 波速公式验证通过: a_rigid={a_rigid:.1f}, a_elastic={a_elastic:.1f}")

    def test_grid_setup(self):
        """测试网格设置"""
        solver = WaterHammerMOCSolver(
            L=1000.0,
            D=0.5,
            f=0.02,
            wave_speed=1000.0
        )

        solver.set_grid(nx=51, cfl=1.0)

        assert solver.nx == 51
        assert abs(solver.dx - 1000.0 / 50) < 1e-10  # dx = L / (nx - 1)
        assert abs(solver.dt - solver.dx / solver.a) < 1e-10  # CFL = 1

        # 检查MOC系数
        expected_B = solver.a / (solver.g * solver.A)
        assert abs(solver.B - expected_B) < 1e-10

        expected_R = solver.f * solver.dt / (2.0 * solver.D * solver.A)
        assert abs(solver.R - expected_R) < 1e-10

        print(" 网格设置测试通过")

    def test_cfl_condition_violation(self):
        """测试CFL条件违反检测"""
        solver = WaterHammerMOCSolver(
            L=1000.0,
            D=0.5,
            f=0.02,
            wave_speed=1000.0
        )

        # 尝试使用过大的CFL数
        with pytest.raises(ValueError, match="违反CFL条件"):
            solver.set_grid(nx=10, cfl=2.0)

        print(" CFL条件违反检测测试通过")

    def test_joukowsky_formula(self):
        """测试Joukowsky公式"""
        solver = WaterHammerMOCSolver(
            L=1000.0,
            D=0.5,
            f=0.02,
            wave_speed=1000.0
        )

        V0 = 2.0  # m/s
        delta_H = solver.joukowsky_head_rise(V0)

        # Joukowsky: ΔH = a * ΔV / g
        expected = 1000.0 * 2.0 / 9.81
        assert abs(delta_H - expected) < 0.1

        print(f" Joukowsky公式测试通过: ΔH = {delta_H:.2f} m")

    def test_critical_closure_time(self):
        """测试临界关闭时间计算"""
        solver = WaterHammerMOCSolver(
            L=1000.0,
            D=0.5,
            f=0.02,
            wave_speed=1000.0
        )

        T_critical = solver.critical_closure_time()

        # T_critical = 2L / a
        expected = 2.0 * 1000.0 / 1000.0
        assert abs(T_critical - expected) < 1e-10

        print(f" 临界关闭时间测试通过: T_critical = {T_critical:.3f} s")

    def test_max_pressure_estimate(self):
        """测试最大压力估算"""
        solver = WaterHammerMOCSolver(
            L=1000.0,
            D=0.5,
            f=0.02,
            wave_speed=1000.0
        )

        V0 = 2.0

        # 直接水锤（快速关闭）
        delta_H_direct = solver.max_pressure_estimate(V0, closure_time=1.0)
        delta_H_joukowsky = solver.joukowsky_head_rise(V0)
        assert abs(delta_H_direct - delta_H_joukowsky) < 0.1

        # 间接水锤（缓慢关闭）
        T_critical = solver.critical_closure_time()
        delta_H_indirect = solver.max_pressure_estimate(V0, closure_time=5.0)
        assert delta_H_indirect < delta_H_direct  # 缓慢关闭压升更小

        print(" 最大压力估算测试通过")

    def test_steady_state_solution(self):
        """测试稳态解（无扰动）"""
        solver = WaterHammerMOCSolver(
            L=1000.0,
            D=0.5,
            f=0.02,
            wave_speed=1000.0
        )

        solver.set_grid(nx=11, cfl=1.0)

        # 边界条件：上游水库100m，下游水库99m（稳定流动）
        bc_up = WaterHammerBoundary('reservoir', value=100.0)
        bc_down = WaterHammerBoundary('reservoir', value=99.0)

        # 初始流量
        Q0 = 0.1

        result = solver.solve_transient(
            Q0=Q0,
            H0_up=100.0,
            bc_upstream=bc_up,
            bc_downstream=bc_down,
            duration=2.0
        )

        # 检查稳态是否维持
        Q_final = result['Q'][-1, :]
        assert np.all(np.abs(Q_final - Q0) < 0.05)  # 流量应保持稳定

        print(" 稳态解测试通过")

    def test_dead_end_boundary(self):
        """测试死端边界条件"""
        solver = WaterHammerMOCSolver(
            L=100.0,
            D=0.3,
            f=0.02,
            wave_speed=1000.0
        )

        solver.set_grid(nx=11, cfl=1.0)

        # 上游恒定水头，下游死端
        bc_up = WaterHammerBoundary('reservoir', value=100.0)
        bc_down = WaterHammerBoundary('dead_end')

        result = solver.solve_transient(
            Q0=0.05,
            H0_up=100.0,
            bc_upstream=bc_up,
            bc_downstream=bc_down,
            duration=1.0
        )

        # 下游死端流量应趋于0
        Q_down_final = result['Q'][-1, -1]
        assert abs(Q_down_final) < 1e-2

        print(" 死端边界条件测试通过")

    def test_valve_closure(self):
        """测试阀门关闭模拟"""
        solver = WaterHammerMOCSolver(
            L=1000.0,
            D=0.5,
            f=0.02,
            wave_speed=1000.0
        )

        solver.set_grid(nx=51, cfl=1.0)

        # 上游水库，下游阀门线性关闭
        bc_up = WaterHammerBoundary('reservoir', value=100.0)
        bc_down = WaterHammerBoundary('valve', closure_function=lambda t: max(0, 1 - t / 2.0))

        Q0 = 0.3
        V0 = Q0 / solver.A

        result = solver.solve_transient(
            Q0=Q0,
            H0_up=100.0,
            bc_upstream=bc_up,
            bc_downstream=bc_down,
            duration=5.0
        )

        # 检查水锤压力升高
        H_max = np.max(result['H'])
        delta_H_joukowsky = solver.joukowsky_head_rise(V0)

        # 压力升高应接近Joukowsky理论值（考虑摩阻和关闭时间）
        assert H_max > 100.0  # 应有压升
        assert H_max < 100.0 + 2.0 * delta_H_joukowsky  # 不应超过理论值2倍

        # 最终流量应接近0（阀门完全关闭）
        Q_final = result['Q'][-1, -1]
        assert abs(Q_final) < 0.01

        print(f" 阀门关闭模拟测试通过: H_max={H_max:.2f}m, ΔH_theory={delta_H_joukowsky:.2f}m")

    def test_output_fields(self):
        """测试输出字段完整性"""
        solver = WaterHammerMOCSolver(
            L=500.0,
            D=0.4,
            f=0.02,
            wave_speed=1000.0
        )

        solver.set_grid(nx=21, cfl=1.0)

        bc_up = WaterHammerBoundary('reservoir', value=50.0)
        bc_down = WaterHammerBoundary('reservoir', value=49.0)

        result = solver.solve_transient(
            Q0=0.1,
            H0_up=50.0,
            bc_upstream=bc_up,
            bc_downstream=bc_down,
            duration=1.0
        )

        # 检查所有必需字段
        assert 't' in result
        assert 'x' in result
        assert 'Q' in result
        assert 'H' in result
        assert 'V' in result
        assert 'p' in result

        # 检查数组形状
        assert result['t'].shape[0] > 0
        assert result['x'].shape[0] == 21
        assert result['Q'].shape[1] == 21
        assert result['H'].shape[1] == 21
        assert result['V'].shape[1] == 21
        assert result['p'].shape[1] == 21

        # 检查流速计算
        V_expected = result['Q'] / solver.A
        assert np.allclose(result['V'], V_expected)

        # 检查压力计算
        p_expected = 1000.0 * solver.g * result['H']
        assert np.allclose(result['p'], p_expected)

        print(" 输出字段完整性测试通过")


class TestWaterHammerBoundary:
    """水锤边界条件测试"""

    def test_reservoir_boundary(self):
        """测试水库边界"""
        bc = WaterHammerBoundary('reservoir', value=100.0)
        assert bc.bc_type == 'reservoir'
        assert bc.value == 100.0
        print(" 水库边界测试通过")

    def test_valve_boundary(self):
        """测试阀门边界"""
        closure_func = lambda t: max(0, 1 - t / 5.0)
        bc = WaterHammerBoundary('valve', closure_function=closure_func)

        assert bc.bc_type == 'valve'
        assert bc.closure_function(0) == 1.0
        assert bc.closure_function(5.0) == 0.0
        assert bc.closure_function(2.5) == 0.5
        print(" 阀门边界测试通过")

    def test_dead_end_boundary(self):
        """测试死端边界"""
        bc = WaterHammerBoundary('dead_end')
        assert bc.bc_type == 'dead_end'
        print(" 死端边界测试通过")


if __name__ == '__main__':
    pytest.main([__file__, '-v', '--tb=short'])
