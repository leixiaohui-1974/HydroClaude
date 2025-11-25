"""
IDZ模型模块单元测试

测试覆盖：
- IDZ参数验证
- 从水力学参数计算IDZ参数
- 单池IDZ模型离散化
- IDZ模型仿真（单步和多步）
- 串联池IDZ模型

作者：HydroClaude Team
日期：2025-10-24
"""

import unittest
import warnings
warnings.filterwarnings("ignore")
import numpy as np
import sys
import os

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from control.idz_model import (
    IDZParameters,
    IDZModel,
    SeriesIDZModel,
    design_idz_from_canal_geometry
)


class TestIDZParameters(unittest.TestCase):
    """IDZ参数测试"""

    def test_parameter_validation_valid(self):
        """测试有效参数"""
        params = IDZParameters(K=100.0, tau_z=50.0, tau_d=100.0, theta=20.0)
        # 不应该抛出异常
        params.validate()

    def test_parameter_validation_negative_K(self):
        """测试负增益"""
        params = IDZParameters(K=-100.0, tau_z=50.0, tau_d=100.0, theta=20.0)
        with self.assertRaises(ValueError):
            params.validate()

    def test_parameter_validation_negative_tau_z(self):
        """测试负零点时间常数"""
        params = IDZParameters(K=100.0, tau_z=-50.0, tau_d=100.0, theta=20.0)
        with self.assertRaises(ValueError):
            params.validate()

    def test_parameter_validation_negative_tau_d(self):
        """测试负延迟时间常数"""
        params = IDZParameters(K=100.0, tau_z=50.0, tau_d=-100.0, theta=20.0)
        with self.assertRaises(ValueError):
            params.validate()

    def test_parameter_validation_negative_theta(self):
        """测试负纯滞后"""
        params = IDZParameters(K=100.0, tau_z=50.0, tau_d=100.0, theta=-20.0)
        with self.assertRaises(ValueError):
            params.validate()

    def test_from_hydraulics_typical_canal(self):
        """测试从典型渠道水力学参数计算IDZ参数"""
        params = IDZParameters.from_hydraulics(
            length=1000.0,    # 1km
            width=10.0,       # 10m
            bed_slope=0.0001,
            manning=0.025,
            normal_depth=2.0
        )

        # 验证参数合理性
        self.assertGreater(params.K, 0)
        self.assertGreater(params.tau_z, 0)
        self.assertGreater(params.tau_d, 0)
        self.assertGreater(params.theta, 0)

        # 验证参数范围（经验值）
        self.assertGreater(params.K, 10)      # 增益应该较大
        self.assertLess(params.K, 10000)
        self.assertGreater(params.tau_d, 10)  # 时间常数几十到几百秒
        self.assertLess(params.tau_d, 10000)
        self.assertGreater(params.theta, 1)   # 纯滞后几秒到几十秒
        self.assertLess(params.theta, 1000)

    def test_from_hydraulics_parameter_relationships(self):
        """测试IDZ参数之间的关系"""
        params = IDZParameters.from_hydraulics(
            length=2000.0, width=10.0, bed_slope=0.0001,
            manning=0.025, normal_depth=2.0
        )

        # 对于常见渠道：tau_z < tau_d（零点时间常数 < 延迟时间常数）
        self.assertLess(params.tau_z, params.tau_d)

        # 纯滞后应该小于延迟时间常数
        self.assertLess(params.theta, params.tau_d)

    def test_from_hydraulics_length_scaling(self):
        """测试长度对IDZ参数的影响"""
        params_1km = IDZParameters.from_hydraulics(
            1000.0, 10.0, 0.0001, 0.025, 2.0
        )
        params_2km = IDZParameters.from_hydraulics(
            2000.0, 10.0, 0.0001, 0.025, 2.0
        )

        # 长度加倍，所有参数应该近似加倍（线性关系）
        self.assertAlmostEqual(params_2km.K / params_1km.K, 2.0, places=1)
        self.assertAlmostEqual(params_2km.tau_z / params_1km.tau_z, 2.0, places=1)
        self.assertAlmostEqual(params_2km.tau_d / params_1km.tau_d, 2.0, places=1)
        self.assertAlmostEqual(params_2km.theta / params_1km.theta, 2.0, places=1)


class TestIDZModel(unittest.TestCase):
    """单池IDZ模型测试"""

    def setUp(self):
        """设置测试环境"""
        self.params = IDZParameters(K=100.0, tau_z=50.0, tau_d=100.0, theta=20.0)
        self.dt = 10.0  # 10秒采样
        self.model = IDZModel(self.params, self.dt)

    def test_model_initialization(self):
        """测试模型初始化"""
        self.assertEqual(self.model.dt, self.dt)
        self.assertIsNotNone(self.model.A)
        self.assertIsNotNone(self.model.B)
        self.assertIsNotNone(self.model.C)
        self.assertIsNotNone(self.model.D)

    def test_state_dimension(self):
        """测试状态维度"""
        # IDZ模型至少是2阶系统（分母2阶 + 纯滞后）
        self.assertGreaterEqual(len(self.model.x), 2)

    def test_step_response_increases(self):
        """测试阶跃响应单调增加"""
        u_step = 0.1  # 小阶跃输入（避免数值问题）

        # 仿真多步
        y_values = []
        for _ in range(20):
            y = self.model.step(u_step)
            y_values.append(y)

        # IDZ模型对正阶跃输入，输出应该单调增加
        for i in range(1, len(y_values)):
            self.assertGreaterEqual(y_values[i], y_values[i-1])

    def test_step_linearity(self):
        """测试输入输出线性关系（叠加性）"""
        # 重置模型
        self.model.reset()

        # 输入u1
        y1_values = []
        for _ in range(10):
            y = self.model.step(0.1)
            y1_values.append(y)

        # 重置并输入u2 = 2*u1
        self.model.reset()
        y2_values = []
        for _ in range(10):
            y = self.model.step(0.2)
            y2_values.append(y)

        # 由于线性系统，y2应该约等于2*y1
        for y1, y2 in zip(y1_values[-5:], y2_values[-5:]):  # 检查后几步
            if y1 != 0:  # 避免除零
                ratio = y2 / y1
                self.assertAlmostEqual(ratio, 2.0, delta=0.2)

    def test_predict_single_step(self):
        """测试单步预测"""
        u_sequence = np.array([1.0])
        y_pred = self.model.predict(u_sequence)

        self.assertEqual(len(y_pred), 1)
        self.assertIsInstance(y_pred[0], (float, np.floating))

    def test_predict_multi_step(self):
        """测试多步预测"""
        horizon = 10
        u_sequence = np.ones(horizon)
        y_pred = self.model.predict(u_sequence)

        self.assertEqual(len(y_pred), horizon)

        # 阶跃输入下，输出应该单调增加（IDZ模型特性）
        for i in range(1, horizon):
            self.assertGreaterEqual(y_pred[i], y_pred[i-1])

    def test_predict_consistency_with_step(self):
        """测试predict与连续step的一致性"""
        # 重置模型
        self.model.reset()

        # 使用step仿真
        u_sequence = np.array([1.0, 0.5, 0.8, 1.2, 0.9])
        y_step = []
        for u in u_sequence:
            y_step.append(self.model.step(u))

        # 重置并使用predict
        self.model.reset()
        y_pred = self.model.predict(u_sequence)

        # 结果应该一致
        np.testing.assert_array_almost_equal(y_step, y_pred, decimal=5)

    def test_reset(self):
        """测试模型重置"""
        # 运行一段时间
        for _ in range(10):
            self.model.step(1.0)

        # 记录重置前的输出
        y_before = self.model.step(0.5)

        # 重置
        self.model.reset()

        # 状态应该回到零
        np.testing.assert_array_equal(self.model.x, np.zeros_like(self.model.x))

        # 延迟缓冲应该清零
        np.testing.assert_array_equal(self.model.delay_buffer, np.zeros_like(self.model.delay_buffer))

        # 重置后输出应该从接近零开始
        y_after = self.model.step(0.5)
        self.assertLess(abs(y_after), abs(y_before))

    def test_delay_effect(self):
        """测试纯滞后效应"""
        # 短纯滞后模型
        params_short = IDZParameters(K=100.0, tau_z=50.0, tau_d=100.0, theta=5.0)
        model_short = IDZModel(params_short, self.dt)

        # 长纯滞后模型
        params_long = IDZParameters(K=100.0, tau_z=50.0, tau_d=100.0, theta=30.0)
        model_long = IDZModel(params_long, self.dt)

        # 同样的阶跃输入
        u_sequence = np.ones(10)

        y_short = model_short.predict(u_sequence)
        y_long = model_long.predict(u_sequence)

        # 长滞后模型前几步输出应该小于短滞后模型
        self.assertLess(y_long[1], y_short[1])


class TestSeriesIDZModel(unittest.TestCase):
    """串联池IDZ模型测试"""

    def setUp(self):
        """设置测试环境"""
        # 创建3个池段
        self.pool_params = [
            IDZParameters(K=100.0, tau_z=50.0, tau_d=100.0, theta=20.0),
            IDZParameters(K=120.0, tau_z=55.0, tau_d=110.0, theta=22.0),
            IDZParameters(K=110.0, tau_z=52.0, tau_d=105.0, theta=21.0)
        ]
        self.dt = 10.0
        self.series_model = SeriesIDZModel(self.pool_params, self.dt)

    def test_model_initialization(self):
        """测试串联模型初始化"""
        self.assertEqual(self.series_model.n_pools, 3)
        self.assertEqual(len(self.series_model.models), 3)

    def test_step_inputs(self):
        """测试串联模型输入输出"""
        # 3个池段需要4个流量输入 (Q0, Q1, Q2, Q3)
        # Q0: 上游入流
        # Q1: 池1和池2之间的流量
        # Q2: 池2和池3之间的流量
        # Q3: 池3的出流
        u = np.array([0.1, 0.08, 0.06, 0.05])

        # 仿真多步
        y_history = []
        for _ in range(20):
            y = self.series_model.step(u)
            y_history.append(y.copy())

        # 输出维度应该等于池段数
        self.assertEqual(len(y_history[-1]), 3)

        # 所有池段都应该有输出
        y_final = y_history[-1]
        for i in range(3):
            self.assertIsNotNone(y_final[i])

    def test_predict_dimensions(self):
        """测试串联模型预测维度"""
        # 3个池段需要4个流量输入
        horizon = 20
        u_sequence = np.zeros((horizon, 4))
        u_sequence[:, 0] = 0.1  # 上游输入
        u_sequence[:, 1] = 0.08
        u_sequence[:, 2] = 0.06
        u_sequence[:, 3] = 0.05

        y_pred = self.series_model.predict(u_sequence)

        # 输出应该是 (horizon, n_pools)
        self.assertEqual(y_pred.shape, (horizon, 3))

        # 输出应该单调增加（正输入）
        for pool_idx in range(3):
            for t in range(1, horizon):
                self.assertGreaterEqual(y_pred[t, pool_idx], y_pred[t-1, pool_idx])

    def test_reset_all_pools(self):
        """测试重置所有池段"""
        # 运行一段时间
        u = np.array([0.1, 0.08, 0.06, 0.05])
        for _ in range(10):
            self.series_model.step(u)

        # 重置
        self.series_model.reset()

        # 所有池段状态应该清零
        for pool_model in self.series_model.models:
            np.testing.assert_array_equal(pool_model.x, np.zeros_like(pool_model.x))


class TestDesignIDZFromCanalGeometry(unittest.TestCase):
    """从渠道几何设计IDZ模型测试"""

    def test_design_uniform_canal(self):
        """测试均匀渠道设计"""
        # 3个相同池段
        lengths = [1500.0, 1500.0, 1500.0]
        widths = [10.0, 10.0, 10.0]
        bed_slopes = [0.0001, 0.0001, 0.0001]
        mannings = [0.025, 0.025, 0.025]
        normal_depths = [2.0, 2.0, 2.0]
        dt = 10.0

        model = design_idz_from_canal_geometry(
            lengths=lengths,
            widths=widths,
            bed_slopes=bed_slopes,
            manning_coeffs=mannings,
            normal_depths=normal_depths,
            dt=dt
        )

        # 应该创建3个池段
        self.assertEqual(model.n_pools, 3)

        # 所有池段参数应该相同（均匀渠道）
        K_values = [pool.params.K for pool in model.models]
        self.assertAlmostEqual(K_values[0], K_values[1], places=1)
        self.assertAlmostEqual(K_values[1], K_values[2], places=1)

    def test_design_nonuniform_canal(self):
        """测试非均匀渠道设计"""
        lengths = [1000.0, 1500.0, 2000.0]
        widths = [8.0, 10.0, 12.0]
        bed_slopes = [0.0001, 0.0001, 0.0001]
        mannings = [0.025, 0.025, 0.025]
        normal_depths = [2.0, 2.0, 2.0]
        dt = 10.0

        model = design_idz_from_canal_geometry(
            lengths=lengths,
            widths=widths,
            bed_slopes=bed_slopes,
            manning_coeffs=mannings,
            normal_depths=normal_depths,
            dt=dt
        )

        # 应该创建3个池段
        self.assertEqual(model.n_pools, 3)

        # 池段参数应该不同（非均匀渠道）
        K_values = [pool.params.K for pool in model.models]
        self.assertNotAlmostEqual(K_values[0], K_values[1], places=0)
        self.assertNotAlmostEqual(K_values[1], K_values[2], places=0)

        # K应该随长度增加（长度更长 -> K更大）
        # 随宽度增加而减小（宽度更大 -> 面积更大 -> K更小）
        # 第3段最长最宽，效果取决于具体数值

        # 至少验证所有K都是正数
        for K in K_values:
            self.assertGreater(K, 0)


if __name__ == '__main__':
    unittest.main(verbosity=2)
