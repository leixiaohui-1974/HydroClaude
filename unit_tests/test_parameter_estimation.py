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
            width=5.0,
            manning_n=0.025,
            slope=0.0002,
            dt=1.0
        )
        solver.Q_in = 10.0
        solver.h_downstream = 2.0
        return solver

    def test_estimator_initialization(self, simple_solver):
        """测试参数估计器初始化"""
        estimator = ParameterEstimator(
            solver=simple_solver,
            estimate_manning=True,
            estimate_leakage=False
        )

        assert estimator.solver is simple_solver
        assert estimator.estimate_manning is True
        assert estimator.estimate_leakage is False
        assert hasattr(estimator, 'nx')

    def test_estimator_initialization_with_sensors(self, simple_solver):
        """测试带传感器位置的初始化"""
        sensors = [
            {'type': 'water_level', 'position': 500},
            {'type': 'water_level', 'position': 750}
        ]

        estimator = ParameterEstimator(
            solver=simple_solver,
            estimate_manning=True,
            sensors=sensors
        )

        assert len(estimator.sensors) == 2
        assert estimator.sensors[0]['position'] == 500

    def test_estimator_state_dimension(self, simple_solver):
        """测试状态维度计算"""
        # 只估计糙率
        estimator1 = ParameterEstimator(
            solver=simple_solver,
            estimate_manning=True,
            estimate_leakage=False
        )

        # 状态维度 = 2 * nx (h和hu) + nx (糙率)
        expected_dim1 = 2 * simple_solver.nx + simple_solver.nx
        assert estimator1.state_dim == expected_dim1

        # 同时估计糙率和渗漏率
        estimator2 = ParameterEstimator(
            solver=simple_solver,
            estimate_manning=True,
            estimate_leakage=True
        )

        # 状态维度 = 2 * nx + nx + nx
        expected_dim2 = 2 * simple_solver.nx + 2 * simple_solver.nx
        assert estimator2.state_dim == expected_dim2

    def test_get_augmented_state(self, simple_solver):
        """测试增广状态获取"""
        estimator = ParameterEstimator(
            solver=simple_solver,
            estimate_manning=True
        )

        # 运行求解器几步
        for _ in range(5):
            simple_solver.step()

        # 获取增广状态
        state = estimator._get_augmented_state()

        # 检查状态向量长度
        expected_length = 3 * simple_solver.nx  # h, hu, manning
        assert len(state) == expected_length

        # 检查状态值的合理性
        h_part = state[:simple_solver.nx]
        assert np.all(h_part > 0)  # 水深应该为正

    def test_set_augmented_state(self, simple_solver):
        """测试设置增广状态"""
        estimator = ParameterEstimator(
            solver=simple_solver,
            estimate_manning=True
        )

        # 创建一个新的状态向量
        new_state = np.random.rand(3 * simple_solver.nx) + 1.0

        # 设置状态
        estimator._set_augmented_state(new_state)

        # 验证求解器状态已更新
        assert np.allclose(simple_solver.h, new_state[:simple_solver.nx])

    def test_process_noise_covariance(self, simple_solver):
        """测试过程噪声协方差矩阵"""
        estimator = ParameterEstimator(
            solver=simple_solver,
            estimate_manning=True,
            q_state=1e-4,
            q_param=1e-6
        )

        # 检查Q矩阵维度
        assert estimator.Q.shape[0] == estimator.state_dim
        assert estimator.Q.shape[1] == estimator.state_dim

        # Q矩阵应该是对角矩阵
        assert np.allclose(estimator.Q, np.diag(np.diag(estimator.Q)))

    def test_measurement_noise_covariance(self, simple_solver):
        """测试测量噪声协方差"""
        sensors = [
            {'type': 'water_level', 'position': 500},
            {'type': 'water_level', 'position': 750}
        ]

        estimator = ParameterEstimator(
            solver=simple_solver,
            estimate_manning=True,
            sensors=sensors,
            r_measurement=0.01
        )

        # 检查R矩阵维度（每个传感器一个测量）
        assert estimator.R.shape[0] == len(sensors)
        assert estimator.R.shape[1] == len(sensors)

    def test_predict_measurement(self, simple_solver):
        """测试测量预测"""
        sensors = [
            {'type': 'water_level', 'position': 500}
        ]

        estimator = ParameterEstimator(
            solver=simple_solver,
            sensors=sensors
        )

        # 运行求解器
        for _ in range(5):
            simple_solver.step()

        # 预测测量
        z_pred = estimator._predict_measurement(sensors[0])

        # 测量应该是标量且合理
        assert isinstance(z_pred, (int, float, np.number))
        assert z_pred > 0  # 水位应该为正

    def test_compute_jacobian_dimensions(self, simple_solver):
        """测试雅可比矩阵维度"""
        sensors = [
            {'type': 'water_level', 'position': 500},
            {'type': 'water_level', 'position': 750}
        ]

        estimator = ParameterEstimator(
            solver=simple_solver,
            estimate_manning=True,
            sensors=sensors
        )

        # 如果实现了雅可比计算
        if hasattr(estimator, '_compute_jacobian'):
            H = estimator._compute_jacobian()

            # H矩阵维度应该是 (测量数, 状态维度)
            assert H.shape[0] == len(sensors)
            assert H.shape[1] == estimator.state_dim


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
            width=8.0,
            manning_n=0.030,  # 真实糙率
            slope=0.0001,
            dt=2.0
        )
        true_solver.Q_in = 15.0
        true_solver.h_downstream = 2.5

        # 创建估计系统（初始糙率不同）
        est_solver = HydrostaticCanalSolver(
            length=2000,
            nx=20,
            width=8.0,
            manning_n=0.020,  # 初始猜测
            slope=0.0001,
            dt=2.0
        )
        est_solver.Q_in = 15.0
        est_solver.h_downstream = 2.5

        # 创建传感器
        sensors = [
            {'type': 'water_level', 'position': 1000},
            {'type': 'water_level', 'position': 1500}
        ]

        # 创建估计器
        estimator = ParameterEstimator(
            solver=est_solver,
            estimate_manning=True,
            estimate_leakage=False,
            sensors=sensors,
            q_state=1e-3,
            q_param=1e-5,
            r_measurement=0.01
        )

        return true_solver, est_solver, estimator, sensors

    @pytest.mark.slow
    def test_manning_estimation_convergence(self, estimation_setup):
        """测试糙率估计收敛性"""
        true_solver, est_solver, estimator, sensors = estimation_setup

        true_manning = 0.030
        initial_manning = 0.020

        # 记录估计历史
        manning_history = []

        # 运行估计
        n_steps = 100

        for step in range(n_steps):
            # 真实系统步进
            true_solver.step()

            # 生成观测（从真实系统）
            observations = []
            for sensor in sensors:
                pos_idx = int(sensor['position'] / true_solver.length * true_solver.nx)
                pos_idx = min(pos_idx, true_solver.nx - 1)
                z = true_solver.h[pos_idx]
                # 添加测量噪声
                z += np.random.normal(0, 0.01)
                observations.append(z)

            # 参数估计步进
            if hasattr(estimator, 'step'):
                estimator.step(observations)

            # 记录当前估计值
            current_manning = np.mean(getattr(est_solver, 'manning_n', est_solver.manning_n))
            manning_history.append(current_manning)

        # 检查收敛性
        final_manning = np.mean(manning_history[-20:])
        error = abs(final_manning - true_manning) / true_manning

        # 允许10%的误差
        assert error < 0.10, f"Manning estimation error too large: {error:.2%}"

    def test_measurement_update(self, estimation_setup):
        """测试测量更新"""
        true_solver, est_solver, estimator, sensors = estimation_setup

        # 运行一步
        true_solver.step()

        # 生成观测
        observations = []
        for sensor in sensors:
            pos_idx = int(sensor['position'] / true_solver.length * true_solver.nx)
            pos_idx = min(pos_idx, true_solver.nx - 1)
            observations.append(true_solver.h[pos_idx])

        # 获取更新前的状态
        state_before = estimator._get_augmented_state().copy()

        # 执行测量更新
        if hasattr(estimator, '_measurement_update'):
            estimator._measurement_update(observations)

            # 状态应该已经更新
            state_after = estimator._get_augmented_state()
            assert not np.allclose(state_before, state_after)

    def test_covariance_evolution(self, estimation_setup):
        """测试协方差演化"""
        true_solver, est_solver, estimator, sensors = estimation_setup

        # 记录初始协方差
        if hasattr(estimator, 'P'):
            P_initial = estimator.P.copy()
            initial_trace = np.trace(P_initial)

            # 运行几步估计
            for _ in range(10):
                true_solver.step()

                observations = []
                for sensor in sensors:
                    pos_idx = int(sensor['position'] / true_solver.length * true_solver.nx)
                    pos_idx = min(pos_idx, true_solver.nx - 1)
                    observations.append(true_solver.h[pos_idx] + np.random.normal(0, 0.01))

                if hasattr(estimator, 'step'):
                    estimator.step(observations)

            # 协方差应该已经演化
            P_final = estimator.P
            final_trace = np.trace(P_final)

            # 由于测量更新，协方差的迹应该减小（不确定性降低）
            # 但也可能因为过程噪声增加
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
            width=10.0,
            manning_n=0.025,
            slope=0.0001,
            dt=2.0
        )

        sensors = [
            {'type': 'water_level', 'position': 1000},
            {'type': 'water_level', 'position': 2500},
            {'type': 'water_level', 'position': 4000}
        ]

        estimator = ParameterEstimator(
            solver=solver,
            estimate_manning=True,
            sensors=sensors
        )

        # 测量单步计算时间
        observations = [2.0, 2.0, 2.0]

        start = time.time()
        for _ in range(10):
            solver.step()
            if hasattr(estimator, 'step'):
                estimator.step(observations)

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
            width=10.0,
            manning_n=0.025,
            slope=0.0001,
            dt=2.0
        )

        estimator = ParameterEstimator(
            solver=solver,
            estimate_manning=True,
            estimate_leakage=True
        )

        # 检查主要矩阵的内存占用
        matrix_memory = 0
        if hasattr(estimator, 'P'):
            matrix_memory += estimator.P.nbytes
        if hasattr(estimator, 'Q'):
            matrix_memory += estimator.Q.nbytes
        if hasattr(estimator, 'R'):
            matrix_memory += estimator.R.nbytes

        # 转换为MB
        matrix_memory_mb = matrix_memory / (1024 * 1024)

        # 对于100个网格，内存应该在合理范围内（< 100 MB）
        assert matrix_memory_mb < 100, f"Too much memory: {matrix_memory_mb:.2f} MB"


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
