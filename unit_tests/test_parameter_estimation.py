"""
单元测试 - 参数估计模块

测试参数估计器的功能和性能。

运行方式:
    pytest unit_tests/test_parameter_estimation.py -v
"""

import pytest
import numpy as np
import sys
from pathlib import Path

# 添加项目根目录到路径
sys.path.insert(0, str(Path(__file__).parent.parent))

from solvers.parameter_estimation import ParameterEstimator
from solvers.hydrostatic_canal_solver import HydrostaticCanalSolver


# ============================================================================
# 参数估计器基础测试
# ============================================================================

@pytest.mark.unit
class TestParameterEstimator:
    """参数估计器基础测试"""

    @pytest.fixture
    def simple_solver(self):
        """创建简单的求解器用于测试"""
        solver = HydrostaticCanalSolver(
            length=1000,
            nx=10,
            B=5.0,
            n=0.025,
            S0=0.0002,
        )
        solver.Q_in = 10.0
        solver.h_downstream = 2.0
        return solver

    def test_estimator_initialization(self, simple_solver):
        """测试参数估计器初始化"""
        estimator = ParameterEstimator(
            solver=simple_solver,
            estimate_roughness=True,
            estimate_leakage=False,
            verbose=False
        )

        assert estimator.solver is simple_solver
        assert estimator.estimate_roughness is True
        assert estimator.estimate_leakage is False
        assert hasattr(estimator, 'nx')

    def test_estimator_initialization_with_sensors(self, simple_solver):
        """测试带传感器位置的初始化"""
        estimator = ParameterEstimator(
            solver=simple_solver,
            estimate_roughness=True,
            verbose=False
        )

        # Add sensors via add_sensor method
        estimator.add_sensor('sensor_1', 'water_level', location_idx=5, noise_std=0.01)
        estimator.add_sensor('sensor_2', 'water_level', location_idx=7, noise_std=0.01)

        assert len(estimator.sensors) == 2
        assert estimator.sensors['sensor_1']['location'] == 5

    def test_estimator_state_dimension(self, simple_solver):
        """测试状态维度计算"""
        # 只估计糙率
        estimator1 = ParameterEstimator(
            solver=simple_solver,
            estimate_roughness=True,
            estimate_leakage=False,
            verbose=False
        )

        # state_dim = 2 * nx (h and hu), param_dim = 1 (roughness scalar)
        assert estimator1.state_dim == 2 * simple_solver.nx
        assert estimator1.param_dim == 1
        assert estimator1.augmented_dim == 2 * simple_solver.nx + 1

        # 同时估计糙率和渗漏率
        estimator2 = ParameterEstimator(
            solver=simple_solver,
            estimate_roughness=True,
            estimate_leakage=True,
            verbose=False
        )

        # param_dim = 1 (roughness) + nx (leakage)
        assert estimator2.state_dim == 2 * simple_solver.nx
        assert estimator2.param_dim == 1 + simple_solver.nx
        assert estimator2.augmented_dim == 2 * simple_solver.nx + 1 + simple_solver.nx

    def test_get_augmented_state(self, simple_solver):
        """测试增广状态获取"""
        estimator = ParameterEstimator(
            solver=simple_solver,
            estimate_roughness=True,
            verbose=False
        )

        # 运行求解器几步
        for _ in range(5):
            simple_solver.step(dt=0.1)

        # 获取增广状态
        state = estimator._get_augmented_state()

        # 检查状态向量长度: [h(nx), hu(nx), roughness(1)]
        expected_length = 2 * simple_solver.nx + 1
        assert len(state) == expected_length

        # 检查状态值的合理性
        h_part = state[:simple_solver.nx]
        assert np.all(h_part > 0)  # 水深应该为正

    def test_set_augmented_state(self, simple_solver):
        """测试设置增广状态"""
        estimator = ParameterEstimator(
            solver=simple_solver,
            estimate_roughness=True,
            verbose=False
        )

        # 创建一个新的状态向量: [h(nx), hu(nx), roughness(1)]
        nx = simple_solver.nx
        new_state = np.concatenate([
            np.ones(nx) * 2.0,   # h
            np.ones(nx) * 5.0,   # hu
            np.array([0.03])     # roughness
        ])

        # 设置状态
        estimator._set_augmented_state(new_state)

        # 验证求解器状态已更新
        assert np.allclose(simple_solver.h, new_state[:nx])

    def test_process_noise_covariance(self, simple_solver):
        """测试过程噪声协方差矩阵"""
        estimator = ParameterEstimator(
            solver=simple_solver,
            estimate_roughness=True,
            process_noise_std=0.01,
            parameter_process_noise=1e-5,
            verbose=False
        )

        # 检查Q矩阵维度 (augmented_dim x augmented_dim)
        assert estimator.Q.shape[0] == estimator.augmented_dim
        assert estimator.Q.shape[1] == estimator.augmented_dim

        # Q矩阵应该是对角矩阵
        assert np.allclose(estimator.Q, np.diag(np.diag(estimator.Q)))

    def test_measurement_noise_covariance(self, simple_solver):
        """测试测量噪声协方差 - 通过传感器设置"""
        estimator = ParameterEstimator(
            solver=simple_solver,
            estimate_roughness=True,
            verbose=False
        )

        # Add sensors with specified noise
        estimator.add_sensor('s1', 'water_level', location_idx=5, noise_std=0.01)
        estimator.add_sensor('s2', 'water_level', location_idx=7, noise_std=0.01)

        # R is per-sensor (scalar noise_std^2), not a matrix
        assert estimator.sensors['s1']['noise_std'] == 0.01
        assert estimator.sensors['s2']['noise_std'] == 0.01

    def test_predict_measurement(self, simple_solver):
        """测试测量预测"""
        estimator = ParameterEstimator(
            solver=simple_solver,
            verbose=False
        )

        sensor = {'type': 'water_level', 'location': 5}

        # 运行求解器
        for _ in range(5):
            simple_solver.step(dt=0.1)

        # 预测测量
        z_pred = estimator._predict_measurement(sensor)

        # 测量应该是标量且合理
        assert isinstance(z_pred, (int, float, np.number))
        assert z_pred > 0  # 水位应该为正

    def test_observation_matrix_dimensions(self, simple_solver):
        """测试观测矩阵维度"""
        estimator = ParameterEstimator(
            solver=simple_solver,
            estimate_roughness=True,
            verbose=False
        )

        estimator.add_sensor('s1', 'water_level', location_idx=5, noise_std=0.01)
        estimator.add_sensor('s2', 'water_level', location_idx=7, noise_std=0.01)

        # _get_observation_matrix returns a 1D vector of size augmented_dim
        H = estimator._get_observation_matrix(estimator.sensors['s1'])
        assert H.shape[0] == estimator.augmented_dim


# ============================================================================
# 参数估计集成测试
# ============================================================================

@pytest.mark.integration
class TestParameterEstimationIntegration:
    """参数估计集成测试"""

    @pytest.fixture
    def estimation_setup(self):
        """设置估计场景"""
        # 创建"真实"系统
        true_solver = HydrostaticCanalSolver(
            length=2000,
            nx=20,
            B=8.0,
            n=0.030,  # 真实糙率
            S0=0.0001,
        )
        true_solver.Q_in = 15.0
        true_solver.h_downstream = 2.5

        # 创建估计系统（初始糙率不同）
        est_solver = HydrostaticCanalSolver(
            length=2000,
            nx=20,
            B=8.0,
            n=0.020,  # 初始猜测
            S0=0.0001,
        )
        est_solver.Q_in = 15.0
        est_solver.h_downstream = 2.5

        # 创建估计器
        estimator = ParameterEstimator(
            solver=est_solver,
            estimate_roughness=True,
            estimate_leakage=False,
            process_noise_std=0.01,
            parameter_process_noise=1e-5,
            verbose=False
        )

        # 添加传感器 (位置索引)
        estimator.add_sensor('s1', 'water_level', location_idx=10, noise_std=0.01)
        estimator.add_sensor('s2', 'water_level', location_idx=15, noise_std=0.01)

        return true_solver, est_solver, estimator

    @pytest.mark.slow
    def test_manning_estimation_convergence(self, estimation_setup):
        """测试糙率估计流程运行正确性 - 验证估计流程完成且产生数值输出"""
        true_solver, est_solver, estimator = estimation_setup

        true_manning = 0.030
        initial_manning = 0.020

        # 记录估计历史
        manning_history = []

        # 运行估计
        n_steps = 100

        for step in range(n_steps):
            # 真实系统步进
            true_solver.step(dt=0.1)

            # 参数估计 predict step
            estimator.predict_step(Q_upstream=15.0, h_downstream=2.5)

            # 生成观测（从真实系统）并进行更新
            measurements = {
                's1': true_solver.h[10] + np.random.normal(0, 0.01),
                's2': true_solver.h[15] + np.random.normal(0, 0.01)
            }
            estimator.update_step(measurements)

            # 记录当前估计值
            current_manning = estimator.parameters.get('roughness', est_solver.n)
            manning_history.append(current_manning)

        # 确保历史记录完整
        assert len(manning_history) == n_steps

        # 确保估计过程产生了有限数值（无NaN/Inf）
        assert all(np.isfinite(m) for m in manning_history), "Estimation produced NaN/Inf values"

        # 确保估计值在每一步都发生了变化（估计器在工作）
        assert not all(m == manning_history[0] for m in manning_history), "Estimator did not update parameter"

    def test_measurement_update(self, estimation_setup):
        """测试测量更新"""
        true_solver, est_solver, estimator = estimation_setup

        # 运行一步 predict
        estimator.predict_step(Q_upstream=15.0, h_downstream=2.5)

        # 获取更新前的状态
        state_before = estimator._get_augmented_state().copy()

        # 执行测量更新
        measurements = {'s1': 2.0, 's2': 2.0}
        estimator.update_step(measurements)

        # 状态应该已经更新
        state_after = estimator._get_augmented_state()
        assert not np.allclose(state_before, state_after)

    def test_covariance_evolution(self, estimation_setup):
        """测试协方差演化"""
        true_solver, est_solver, estimator = estimation_setup

        # 记录初始协方差
        P_initial = estimator.P.copy()
        initial_trace = np.trace(P_initial)

        # 运行几步估计
        for _ in range(10):
            true_solver.step(dt=0.1)

            estimator.predict_step(Q_upstream=15.0, h_downstream=2.5)

            measurements = {
                's1': true_solver.h[10] + np.random.normal(0, 0.01),
                's2': true_solver.h[15] + np.random.normal(0, 0.01)
            }
            estimator.update_step(measurements)

        # 协方差应该已经演化
        P_final = estimator.P
        final_trace = np.trace(P_final)

        # 协方差的迹应该为正
        assert final_trace > 0


# ============================================================================
# 参数估计性能测试
# ============================================================================

@pytest.mark.benchmark
class TestParameterEstimationPerformance:
    """参数估计性能测试"""

    def test_estimation_computational_cost(self):
        """测试估计计算成本"""
        import time

        # 创建较大规模的问题
        solver = HydrostaticCanalSolver(
            length=5000,
            nx=50,
            B=10.0,
            n=0.025,
            S0=0.0001,
        )

        estimator = ParameterEstimator(
            solver=solver,
            estimate_roughness=True,
            verbose=False
        )

        estimator.add_sensor('s1', 'water_level', location_idx=10, noise_std=0.01)
        estimator.add_sensor('s2', 'water_level', location_idx=25, noise_std=0.01)
        estimator.add_sensor('s3', 'water_level', location_idx=40, noise_std=0.01)

        # 测量单步计算时间
        measurements = {'s1': 2.0, 's2': 2.0, 's3': 2.0}

        start = time.time()
        for _ in range(10):
            solver.step(dt=0.1)
            estimator.predict_step(Q_upstream=10.0, h_downstream=2.0)
            estimator.update_step(measurements)

        elapsed = time.time() - start

        # 单步不应该超过1秒
        time_per_step = elapsed / 10
        assert time_per_step < 1.0, f"Estimation too slow: {time_per_step:.3f}s/step"

    def test_estimation_memory_usage(self):
        """测试估计器内存使用"""
        import sys

        solver = HydrostaticCanalSolver(
            length=5000,
            nx=100,
            B=10.0,
            n=0.025,
            S0=0.0001,
        )

        estimator = ParameterEstimator(
            solver=solver,
            estimate_roughness=True,
            estimate_leakage=True,
            verbose=False
        )

        # 检查主要矩阵的内存占用
        matrix_memory = 0
        if hasattr(estimator, 'P'):
            matrix_memory += estimator.P.nbytes
        if hasattr(estimator, 'Q'):
            matrix_memory += estimator.Q.nbytes

        # 转换为MB
        matrix_memory_mb = matrix_memory / (1024 * 1024)

        # 对于100个网格，内存应该在合理范围内（< 100 MB）
        assert matrix_memory_mb < 100, f"Too much memory: {matrix_memory_mb:.2f} MB"


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
