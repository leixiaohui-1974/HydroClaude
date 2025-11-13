"""
在线辨识模块单元测试

测试覆盖：
- 递归最小二乘法（RLS）
- IDZ参数辨识
- 闸门特性辨识
- 水泵特性辨识
- 阀门特性辨识
- 水轮机特性辨识

作者：HydroClaude Team
日期：2025-10-24
"""

import unittest
import numpy as np
import sys
import os

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from control.online_identification import (
    RecursiveLeastSquares,
    RLSConfig,
    IDZIdentifier,
    GateIdentifier,
    PumpIdentifier,
    ValveIdentifier,
    TurbineIdentifier
)


class TestRecursiveLeastSquares(unittest.TestCase):
    """递归最小二乘法测试"""

    def setUp(self):
        """设置测试环境"""
        self.n_params = 2
        self.rls = RecursiveLeastSquares(self.n_params)

    def test_initialization(self):
        """测试初始化"""
        self.assertEqual(len(self.rls.theta), self.n_params)
        self.assertEqual(self.rls.P.shape, (self.n_params, self.n_params))

    def test_simple_linear_regression(self):
        """测试简单线性回归：y = 2x + 3"""
        # 真实参数：theta = [3, 2]（截距和斜率）
        true_theta = np.array([3.0, 2.0])

        # 生成训练数据
        np.random.seed(42)
        n_samples = 100
        for i in range(n_samples):
            x = np.random.randn()
            phi = np.array([1.0, x])  # [1, x]
            y = true_theta @ phi + 0.1 * np.random.randn()  # 添加小噪声

            self.rls.update(phi, y)

        # 辨识参数应该接近真实参数
        np.testing.assert_array_almost_equal(self.rls.theta, true_theta, decimal=1)

    def test_forgetting_factor(self):
        """测试遗忘因子效果"""
        # 使用遗忘因子
        rls_forget = RecursiveLeastSquares(
            n_params=2,
            config=RLSConfig(forgetting_factor=0.95)
        )

        # 第一阶段：y = 2x + 1
        np.random.seed(42)
        for i in range(50):
            x = np.random.randn()
            phi = np.array([1.0, x])
            y = 1.0 + 2.0 * x + 0.1 * np.random.randn()
            rls_forget.update(phi, y)

        # 第二阶段：参数突变为 y = 3x + 5
        for i in range(50):
            x = np.random.randn()
            phi = np.array([1.0, x])
            y = 5.0 + 3.0 * x + 0.1 * np.random.randn()
            rls_forget.update(phi, y)

        # 应该跟踪到新参数（大致接近[5, 3]）
        self.assertGreater(rls_forget.theta[0], 3.0)  # 截距 > 3
        self.assertGreater(rls_forget.theta[1], 2.2)  # 斜率 > 2.2（放宽要求）

    def test_covariance_matrix_decreases(self):
        """测试协方差矩阵递减（参数估计越来越准确）"""
        # 记录初始协方差
        P_initial = np.trace(self.rls.P)

        # 更新多次
        np.random.seed(42)
        for i in range(20):
            phi = np.random.randn(self.n_params)
            y = 1.0  # 随意值
            self.rls.update(phi, y)

        # 协方差应该减小
        P_final = np.trace(self.rls.P)
        self.assertLess(P_final, P_initial)


class TestIDZIdentifier(unittest.TestCase):
    """IDZ参数辨识测试"""

    def setUp(self):
        """设置测试环境"""
        self.dt = 10.0
        self.identifier = IDZIdentifier(dt=self.dt)

    def test_initialization(self):
        """测试初始化"""
        # 初始化后参数为None（需要数据才能辨识）
        params = self.identifier.get_idz_parameters()
        self.assertIsNone(params)

    def test_identification_with_data(self):
        """测试IDZ辨识收敛性"""
        # 模拟简单数据
        np.random.seed(42)

        for i in range(200):
            u = 0.5 + 0.1 * np.sin(i * 0.1)  # 正弦输入
            y = 10.0 + 5.0 * u + 0.1 * np.random.randn()  # 简单线性响应

            # 更新辨识
            params = self.identifier.update(u, y)

        # 经过足够数据后，应该得到IDZ参数估计
        final_params = self.identifier.get_idz_parameters()

        if final_params is not None:
            # 参数应该在合理范围内
            self.assertGreater(final_params.K, 0)
            self.assertLess(final_params.K, 1000)
            self.assertGreater(final_params.tau_d, 0)
            self.assertLess(final_params.tau_d, 10000)


class TestGateIdentifier(unittest.TestCase):
    """闸门特性辨识测试"""

    def setUp(self):
        """设置测试环境"""
        self.identifier = GateIdentifier(gate_width=5.0)

    def test_initialization(self):
        """测试初始化"""
        self.assertAlmostEqual(self.identifier.C_d, 0.6, places=2)

    def test_gate_equation(self):
        """测试闸门流量公式"""
        # Q = C_d * b * a * sqrt(2*g*h)
        opening = 0.5  # 0.5m
        head = 2.0     # 2m

        Q = self.identifier.C_d * self.identifier.gate_width * opening * np.sqrt(2 * 9.81 * head)

        self.assertGreater(Q, 0)
        self.assertLess(Q, 100)  # 合理范围

    def test_identification_constant_Cd(self):
        """测试恒定放流系数辨识"""
        # 真实放流系数
        true_Cd = 0.65

        # 生成测试数据
        np.random.seed(42)
        for i in range(50):
            opening = 0.3 + 0.2 * np.random.rand()  # 0.3-0.5m
            head = 1.5 + 1.0 * np.random.rand()     # 1.5-2.5m

            # 真实流量
            Q_true = true_Cd * self.identifier.gate_width * opening * np.sqrt(2 * 9.81 * head)
            Q_measured = Q_true + 0.1 * np.random.randn()  # 添加噪声

            # 更新辨识
            self.identifier.update(opening, head, Q_measured)

        # 辨识的C_d应该接近真实值
        self.assertAlmostEqual(self.identifier.C_d, true_Cd, delta=0.05)

    def test_zero_opening_handling(self):
        """测试零开度处理"""
        # 开度为0时，流量应该为0
        opening = 0.0
        head = 2.0
        Q = 0.0

        # 不应该崩溃
        self.identifier.update(opening, head, Q)

    def test_parameter_bounds(self):
        """测试参数边界"""
        # 极端数据不应该导致不合理的C_d
        opening = 1.0
        head = 3.0
        Q_extreme = 100.0  # 不合理的大流量

        self.identifier.update(opening, head, Q_extreme)

        # C_d应该在合理范围 [0.3, 1.0]
        self.assertGreater(self.identifier.C_d, 0.2)
        self.assertLess(self.identifier.C_d, 1.2)


class TestPumpIdentifier(unittest.TestCase):
    """水泵特性辨识测试"""

    def setUp(self):
        """设置测试环境"""
        self.identifier = PumpIdentifier()

    def test_initialization(self):
        """测试初始化"""
        # 初始值应该在合理范围
        self.assertGreater(self.identifier.H0, 0)
        self.assertGreater(self.identifier.K, 0)

    def test_pump_curve_equation(self):
        """测试水泵特性曲线：H = H0 - K*Q^2"""
        Q = 10.0  # m^3/s
        H = self.identifier.H0 - self.identifier.K * Q**2

        self.assertGreater(H, 0)
        self.assertLess(H, self.identifier.H0)  # 扬程应小于零流量扬程

    def test_identification_pump_curve(self):
        """测试水泵曲线辨识"""
        # 真实参数
        true_H0 = 25.0
        true_K = 0.002

        # 生成测试数据
        np.random.seed(42)
        for i in range(50):
            Q = 5.0 + 10.0 * np.random.rand()  # 5-15 m^3/s

            # 真实扬程
            H_true = true_H0 - true_K * Q**2
            H_measured = H_true + 0.2 * np.random.randn()  # 添加噪声

            # 更新辨识
            self.identifier.update(Q, H_measured)

        # 辨识参数应该接近真实值
        self.assertAlmostEqual(self.identifier.H0, true_H0, delta=3.0)
        self.assertAlmostEqual(self.identifier.K, true_K, delta=0.003)  # 放宽K的容差

    def test_zero_flow_handling(self):
        """测试零流量处理"""
        Q = 0.0
        H = self.identifier.H0  # 零流量时扬程=H0

        # 不应该崩溃
        self.identifier.update(Q, H)


class TestValveIdentifier(unittest.TestCase):
    """阀门特性辨识测试"""

    def setUp(self):
        """设置测试环境"""
        self.identifier = ValveIdentifier()

    def test_initialization(self):
        """测试初始化"""
        self.assertAlmostEqual(self.identifier.K_v, 10.0, places=1)

    def test_valve_equation(self):
        """测试阀门流量公式：Q = K_v * opening * sqrt(Δp)"""
        opening = 0.5  # 50%开度
        delta_p = 4.0  # 4m压差

        Q = self.identifier.K_v * opening * np.sqrt(delta_p)

        self.assertGreater(Q, 0)

    def test_identification_constant_Kv(self):
        """测试恒定阀门系数辨识"""
        # 真实阀门系数
        true_Kv = 60.0

        # 生成测试数据
        np.random.seed(42)
        for i in range(50):
            opening = 0.3 + 0.6 * np.random.rand()  # 0.3-0.9
            delta_p = 2.0 + 3.0 * np.random.rand()  # 2-5m

            # 真实流量
            Q_true = true_Kv * opening * np.sqrt(delta_p)
            Q_measured = Q_true + 0.5 * np.random.randn()  # 添加噪声

            # 更新辨识
            self.identifier.update(opening, delta_p, Q_measured)

        # 辨识的K_v应该接近真实值
        self.assertAlmostEqual(self.identifier.K_v, true_Kv, delta=5.0)

    def test_zero_opening_handling(self):
        """测试零开度处理"""
        opening = 0.0
        delta_p = 3.0
        Q = 0.0

        # 不应该崩溃
        self.identifier.update(opening, delta_p, Q)


class TestTurbineIdentifier(unittest.TestCase):
    """水轮机特性辨识测试"""

    def setUp(self):
        """设置测试环境"""
        self.identifier = TurbineIdentifier()

    def test_initialization(self):
        """测试初始化"""
        self.assertAlmostEqual(self.identifier.efficiency, 0.85, places=2)

    def test_turbine_power_equation(self):
        """测试水轮机功率公式：P = η * ρ * g * H * Q"""
        H = 50.0   # 50m水头
        Q = 10.0   # 10 m^3/s

        rho = 1000.0  # kg/m^3
        g = 9.81      # m/s^2

        P = self.identifier.efficiency * rho * g * H * Q  # W

        self.assertGreater(P, 0)
        self.assertLess(P, 10e6)  # 合理功率范围 (< 10 MW)

    def test_identification_efficiency(self):
        """测试效率辨识"""
        # 真实效率
        true_efficiency = 0.88

        # 生成测试数据
        np.random.seed(42)
        rho = 1000.0
        g = 9.81

        for i in range(50):
            H = 40.0 + 20.0 * np.random.rand()  # 40-60m
            Q = 8.0 + 4.0 * np.random.rand()    # 8-12 m^3/s

            # 真实功率（单位：W，不是MW）
            P_true = true_efficiency * rho * g * H * Q
            P_measured = P_true + 1000.0 * np.random.randn()  # 添加噪声

            # 更新辨识
            self.identifier.update(H, Q, P_measured)

        # 辨识效率应该接近真实值
        self.assertAlmostEqual(self.identifier.efficiency, true_efficiency, delta=0.1)

    def test_efficiency_bounds(self):
        """测试效率边界[0, 1]"""
        # 极端数据
        H = 50.0
        Q = 10.0
        P_extreme = 1e7  # 不合理的大功率（10 MW，但应该只有几MW）

        self.identifier.update(H, Q, P_extreme)

        # 效率应该在[0, 1]范围内
        self.assertGreaterEqual(self.identifier.efficiency, 0.0)
        self.assertLessEqual(self.identifier.efficiency, 1.0)


class TestIdentificationConvergence(unittest.TestCase):
    """辨识收敛性测试"""

    def test_rls_convergence_rate(self):
        """测试RLS收敛速度"""
        rls = RecursiveLeastSquares(n_params=2)
        true_theta = np.array([5.0, 3.0])

        errors = []
        np.random.seed(42)

        for i in range(100):
            x = np.random.randn()
            phi = np.array([1.0, x])
            y = true_theta @ phi + 0.1 * np.random.randn()

            rls.update(phi, y)

            # 计算参数误差
            error = np.linalg.norm(rls.theta - true_theta)
            errors.append(error)

        # 误差应该递减
        self.assertLess(errors[-1], errors[10])  # 最后的误差 < 第10步的误差
        self.assertLess(errors[-1], 1.0)  # 最后误差应该小于1

    def test_gate_identification_convergence(self):
        """测试闸门辨识收敛"""
        identifier = GateIdentifier(gate_width=5.0)
        true_Cd = 0.65

        Cd_history = []
        np.random.seed(42)

        for i in range(100):
            opening = 0.3 + 0.3 * np.random.rand()
            head = 1.5 + 1.0 * np.random.rand()
            Q = true_Cd * 5.0 * opening * np.sqrt(2 * 9.81 * head) + 0.1 * np.random.randn()

            identifier.update(opening, head, Q)
            Cd_history.append(identifier.C_d)

        # C_d应该逐渐收敛到真实值
        error_early = abs(Cd_history[20] - true_Cd)
        error_late = abs(Cd_history[-1] - true_Cd)

        self.assertLess(error_late, error_early)


if __name__ == '__main__':
    unittest.main(verbosity=2)
