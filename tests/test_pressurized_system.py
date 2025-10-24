#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
有压系统单元测试

测试内容：
1. 有压管道求解器基本功能
2. 结构物功能（阀门、泵站等）
3. 系统辨识算法
4. 边界条件设置

作者: Claude
日期: 2025-10-24
"""

import numpy as np
import pytest
import sys
sys.path.insert(0, '/home/user/HydroClaude')

from core.pressurized_solver import PressurizedFlowSolver, PipelineConfig
from core.pressurized_structures import (
    Valve, ValveCharacteristics, ValveType,
    PumpStation, SurgeTank, CheckValve
)
from identification.system_identification import (
    LeastSquaresIdentifier,
    RecursiveLeastSquares,
    PipelineParameterEstimator
)


class TestPressurizedSolver:
    """测试有压管道求解器"""

    def test_solver_initialization(self):
        """测试求解器初始化"""
        config = PipelineConfig(
            length=1000.0,
            diameter=0.5,
            thickness=0.01,
            roughness=0.0001
        )

        solver = PressurizedFlowSolver(config, nx=50)

        assert solver.nx == 50
        assert len(solver.x) == 50
        assert solver.wave_speed > 0
        assert solver.friction_factor > 0

    def test_steady_state_initialization(self):
        """测试稳态初始化"""
        config = PipelineConfig(
            length=1000.0,
            diameter=0.5,
            thickness=0.01,
            roughness=0.0001
        )

        solver = PressurizedFlowSolver(config, nx=50)
        solver.initialize_steady_state(Q0=0.1, H0=50.0)

        assert solver.H is not None
        assert solver.V is not None
        assert solver.Q is not None
        assert len(solver.H) == 50

    def test_boundary_conditions(self):
        """测试边界条件设置"""
        config = PipelineConfig(
            length=1000.0,
            diameter=0.5,
            thickness=0.01,
            roughness=0.0001
        )

        solver = PressurizedFlowSolver(config, nx=50)
        solver.initialize_steady_state(Q0=0.1, H0=50.0)

        # 设置边界条件
        bc_up = lambda t: ('H', 50.0)
        bc_down = lambda t: ('Q', 0.1)
        solver.set_boundary_conditions(bc_up, bc_down)

        assert solver.bc_upstream is not None
        assert solver.bc_downstream is not None

    def test_time_stepping(self):
        """测试时间步进"""
        config = PipelineConfig(
            length=1000.0,
            diameter=0.5,
            thickness=0.01,
            roughness=0.0001
        )

        solver = PressurizedFlowSolver(config, nx=50)
        solver.initialize_steady_state(Q0=0.1, H0=50.0)
        solver.set_boundary_conditions(
            lambda t: ('H', 50.0),
            lambda t: ('Q', 0.1)
        )

        # 运行几个时间步
        for i in range(10):
            success = solver.step(i * solver.dt)
            assert success

        assert solver.H is not None


class TestPressurizedStructures:
    """测试有压系统结构物"""

    def test_valve_creation(self):
        """测试阀门创建"""
        char = ValveCharacteristics(
            valve_type=ValveType.GATE,
            diameter=0.5,
            cv_full_open=100.0,
            loss_coeff_full_open=0.5
        )

        valve = Valve(char, initial_opening=1.0)
        assert valve.opening == 1.0

    def test_valve_flow_computation(self):
        """测试阀门流量计算"""
        char = ValveCharacteristics(
            valve_type=ValveType.GATE,
            diameter=0.5,
            cv_full_open=100.0,
            loss_coeff_full_open=0.5
        )

        valve = Valve(char, initial_opening=1.0)
        Q = valve.compute_flow(H_upstream=50.0, H_downstream=45.0)

        assert Q > 0
        assert np.isfinite(Q)

    def test_valve_opening_control(self):
        """测试阀门开度控制"""
        char = ValveCharacteristics(
            valve_type=ValveType.GATE,
            diameter=0.5,
            cv_full_open=100.0,
            loss_coeff_full_open=0.5
        )

        valve = Valve(char, initial_opening=1.0)
        valve.set_opening(0.5)

        assert valve.opening == 0.5

    def test_pump_station(self):
        """测试泵站"""
        pump = PumpStation(
            rated_flow=0.2,
            rated_head=30.0,
            rated_power=80.0,
            efficiency=0.80
        )

        pump.start()
        assert pump.is_running

        H = pump.compute_head(Q=0.2)
        assert H > 0
        assert np.isfinite(H)

    def test_surge_tank(self):
        """测试调压水箱"""
        tank = SurgeTank(
            area=100.0,
            height=10.0,
            initial_level=5.0
        )

        initial_level = tank.level
        tank.update(Q_in=0.6, Q_out=0.5, dt=10.0)

        # 入流大于出流，水位应上升
        assert tank.level > initial_level

    def test_check_valve(self):
        """测试止回阀"""
        check_valve = CheckValve(diameter=0.5)

        # 正向流动
        Q1 = check_valve.compute_flow(H_upstream=50.0, H_downstream=45.0, V=1.0)
        assert Q1 > 0
        assert check_valve.is_open

        # 倒流趋势
        Q2 = check_valve.compute_flow(H_upstream=45.0, H_downstream=50.0, V=1.0)
        assert Q2 == 0.0
        assert not check_valve.is_open


class TestSystemIdentification:
    """测试系统辨识"""

    def test_least_squares(self):
        """测试最小二乘法"""
        # 生成数据: y = 2*x1 + 3*x2 + noise
        np.random.seed(42)
        N = 100
        X = np.random.randn(N, 2)
        theta_true = np.array([2.0, 3.0])
        y = X @ theta_true + 0.1 * np.random.randn(N)

        # 辨识
        ls = LeastSquaresIdentifier()
        result = ls.fit(X, y)

        # 检查结果
        assert result.convergence
        assert result.r_squared > 0.9
        assert np.allclose(result.parameters, theta_true, atol=0.2)

    def test_recursive_least_squares(self):
        """测试递归最小二乘"""
        rls = RecursiveLeastSquares(n_params=2, forgetting_factor=0.98)

        # 生成数据
        np.random.seed(42)
        N = 100
        X = np.random.randn(N, 2)
        theta_true = np.array([2.0, 3.0])
        y = X @ theta_true + 0.1 * np.random.randn(N)

        # 递归更新
        for i in range(N):
            rls.update(X[i], y[i])

        # 检查结果
        result = rls.get_result()
        assert result.convergence
        assert np.allclose(result.parameters, theta_true, atol=0.3)

    def test_pipeline_parameter_estimator(self):
        """测试管道参数估计器"""
        estimator = PipelineParameterEstimator(measured_length=1000.0)

        # 模拟数据
        a_true = 1200.0
        L = 1000.0
        T_round = 2 * L / a_true

        t = np.linspace(0, 5, 500)
        H = 50 + 20 * np.exp(-0.1 * t) * np.sin(2 * np.pi * t / T_round)

        # 估计波速
        a_est, confidence = estimator.estimate_wave_speed(t, H, valve_position=L)

        assert np.isfinite(a_est)
        assert 0 <= confidence <= 1.0
        # 波速估计应该接近真实值（允许一定误差）
        assert abs(a_est - a_true) / a_true < 0.1


if __name__ == "__main__":
    pytest.main([__file__, '-v'])
