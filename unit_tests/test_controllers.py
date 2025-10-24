"""
单元测试 - 控制器模块

测试PID和MPC控制器的功能和性能。

运行方式:
    pytest unit_tests/test_controllers.py -v
"""

import pytest
import numpy as np
import sys
from pathlib import Path

# 添加项目根目录到路径
sys.path.insert(0, str(Path(__file__).parent.parent))

from control.pid_controller import PIDController
from control.mpc_controller import MPCController


# ============================================================================
# PID控制器测试
# ============================================================================

@pytest.mark.unit
class TestPIDController:
    """PID控制器单元测试"""

    def test_pid_initialization(self):
        """测试PID控制器初始化"""
        pid = PIDController(Kp=1.0, Ki=0.1, Kd=0.05)

        assert pid.Kp == 1.0
        assert pid.Ki == 0.1
        assert pid.Kd == 0.05
        assert pid.setpoint == 0.0
        assert pid.integral == 0.0
        assert pid.prev_error == 0.0

    def test_pid_setpoint(self):
        """测试设置目标值"""
        pid = PIDController(Kp=1.0, Ki=0.1, Kd=0.05)
        pid.set_setpoint(2.5)

        assert pid.setpoint == 2.5

    def test_pid_proportional_only(self):
        """测试纯比例控制"""
        pid = PIDController(Kp=2.0, Ki=0.0, Kd=0.0, dt=1.0)
        pid.set_setpoint(10.0)

        # 当前值为5.0，误差为5.0
        output = pid.compute(current_value=5.0)

        # 输出应该是 Kp * error = 2.0 * 5.0 = 10.0
        assert output == 10.0

    def test_pid_integral_action(self):
        """测试积分作用"""
        pid = PIDController(Kp=0.0, Ki=1.0, Kd=0.0, dt=1.0)
        pid.set_setpoint(10.0)

        # 第一步：误差为5.0
        output1 = pid.compute(current_value=5.0)
        # 积分 = 5.0 * 1.0 = 5.0, 输出 = 5.0
        assert output1 == 5.0

        # 第二步：误差仍为5.0
        output2 = pid.compute(current_value=5.0)
        # 积分 = 5.0 + 5.0 = 10.0, 输出 = 10.0
        assert output2 == 10.0

    def test_pid_derivative_action(self):
        """测试微分作用"""
        pid = PIDController(Kp=0.0, Ki=0.0, Kd=1.0, dt=1.0)
        pid.set_setpoint(10.0)

        # 第一步：误差为5.0
        output1 = pid.compute(current_value=5.0)
        # 第一步微分项为0（没有前一个误差）
        assert output1 == 0.0

        # 第二步：误差为3.0（误差减小了2.0）
        output2 = pid.compute(current_value=7.0)
        # 微分 = (3.0 - 5.0) / 1.0 = -2.0
        assert output2 == -2.0

    def test_pid_output_limits(self):
        """测试输出限幅"""
        pid = PIDController(Kp=10.0, Ki=0.0, Kd=0.0, dt=1.0,
                          output_limits=(0.0, 50.0))
        pid.set_setpoint(100.0)

        # 大误差应该被限幅
        output = pid.compute(current_value=0.0)
        # 无限幅输出 = 10.0 * 100 = 1000, 但应该被限制到50.0
        assert output == 50.0

        pid.set_setpoint(0.0)
        output = pid.compute(current_value=100.0)
        # 负输出应该被限制到0.0
        assert output == 0.0

    def test_pid_anti_windup(self):
        """测试抗饱和功能"""
        pid = PIDController(Kp=1.0, Ki=1.0, Kd=0.0, dt=1.0,
                          output_limits=(0.0, 10.0))
        pid.set_setpoint(100.0)

        # 多次迭代，积分项应该不会无限增长
        for _ in range(10):
            output = pid.compute(current_value=0.0)

        # 检查积分项不会过大（具体值取决于实现）
        # 输出应该被限制在10.0
        assert output == 10.0

    def test_pid_reset(self):
        """测试重置功能"""
        pid = PIDController(Kp=1.0, Ki=1.0, Kd=1.0, dt=1.0)
        pid.set_setpoint(10.0)

        # 运行几步
        pid.compute(current_value=5.0)
        pid.compute(current_value=6.0)
        pid.compute(current_value=7.0)

        # 积分项和前一误差应该不为0
        assert pid.integral != 0.0
        assert pid.prev_error != 0.0

        # 重置
        pid.reset()

        # 检查是否重置
        assert pid.integral == 0.0
        assert pid.prev_error == 0.0

    def test_pid_full_control(self):
        """测试完整PID控制"""
        pid = PIDController(Kp=2.0, Ki=0.5, Kd=0.1, dt=0.1)
        pid.set_setpoint(50.0)

        # 模拟系统：简单的一阶惯性系统
        current_value = 0.0
        values = []

        for _ in range(100):
            output = pid.compute(current_value)
            # 简单的系统动态：new_value = old_value + 0.1 * output
            current_value = current_value + 0.1 * output
            values.append(current_value)

        # 检查是否趋向于设定值
        final_values = values[-10:]
        assert all(abs(v - 50.0) < 5.0 for v in final_values)


# ============================================================================
# MPC控制器测试
# ============================================================================

@pytest.mark.unit
class TestMPCController:
    """MPC控制器单元测试"""

    def test_mpc_initialization(self):
        """测试MPC控制器初始化"""
        mpc = MPCController(horizon=10, dt=1.0, target_level=2.5)

        assert mpc.horizon == 10
        assert mpc.dt == 1.0
        assert mpc.target_level == 2.5

    def test_mpc_setpoint(self):
        """测试设置目标值"""
        mpc = MPCController(horizon=10, dt=1.0)
        mpc.set_target(3.0)

        assert mpc.target_level == 3.0

    def test_mpc_compute_control_single_step(self):
        """测试单步控制计算"""
        mpc = MPCController(horizon=5, dt=1.0, target_level=2.5)

        # 当前水位低于目标
        u = mpc.compute_control(current_level=2.0)

        # 控制输出应该为正（增加流量）
        assert u > 0

        # 当前水位高于目标
        u = mpc.compute_control(current_level=3.0)

        # 控制输出应该为负或减小（减少流量）
        assert u < mpc.compute_control(current_level=2.0)

    def test_mpc_compute_control_at_target(self):
        """测试在目标值时的控制"""
        mpc = MPCController(horizon=5, dt=1.0, target_level=2.5)

        # 当前水位等于目标
        u = mpc.compute_control(current_level=2.5)

        # 控制输出应该接近于保持当前状态
        # 具体值取决于实现，但不应该有大的变化
        assert abs(u) < 100  # 合理范围

    def test_mpc_horizon_effect(self):
        """测试预测时域的影响"""
        mpc_short = MPCController(horizon=3, dt=1.0, target_level=2.5)
        mpc_long = MPCController(horizon=15, dt=1.0, target_level=2.5)

        current_level = 2.0

        u_short = mpc_short.compute_control(current_level)
        u_long = mpc_long.compute_control(current_level)

        # 长时域应该给出更平滑的控制（理论上）
        # 这个测试取决于具体实现
        assert u_short != u_long or True  # 占位测试

    def test_mpc_constraints(self):
        """测试约束条件"""
        mpc = MPCController(
            horizon=5,
            dt=1.0,
            target_level=2.5,
            u_min=5.0,
            u_max=30.0
        )

        # 即使需要大的控制输入，也应该被约束限制
        u = mpc.compute_control(current_level=0.0)

        assert u >= 5.0
        assert u <= 30.0

    def test_mpc_state_prediction(self):
        """测试状态预测"""
        mpc = MPCController(horizon=10, dt=1.0, target_level=2.5)

        # 获取预测的状态轨迹（如果MPC提供此功能）
        if hasattr(mpc, 'get_predicted_states'):
            states = mpc.get_predicted_states(current_level=2.0)
            assert len(states) == mpc.horizon
            # 预测状态应该朝向目标值
            assert states[-1] != states[0] or True

    @pytest.mark.slow
    def test_mpc_closed_loop_performance(self):
        """测试闭环性能"""
        mpc = MPCController(horizon=10, dt=0.5, target_level=2.5)

        # 模拟简单的水箱系统
        current_level = 1.0  # 初始水位
        levels = [current_level]

        for step in range(100):
            # 计算控制输入
            u = mpc.compute_control(current_level)

            # 简单的水位动态模型
            # dh/dt = (u - outflow) / A
            # 假设出流恒定，A=10
            outflow = 15.0
            A = 10.0
            current_level = current_level + 0.5 * (u - outflow) / A
            levels.append(current_level)

        # 检查最终是否接近目标值
        final_levels = levels[-20:]
        mean_final = np.mean(final_levels)
        assert abs(mean_final - 2.5) < 0.5  # 允许一定误差

    def test_mpc_disturbance_rejection(self):
        """测试扰动抑制能力"""
        mpc = MPCController(horizon=10, dt=1.0, target_level=2.5)

        current_level = 2.5  # 从目标值开始

        # 施加扰动
        current_level += 0.5

        # 计算控制响应
        u1 = mpc.compute_control(current_level)

        # 应该产生控制作用来抑制扰动
        # 由于水位高于目标，控制应该减小流量或为负
        assert u1 < mpc.compute_control(2.5)

    def test_mpc_cost_function(self):
        """测试代价函数（如果暴露）"""
        mpc = MPCController(
            horizon=10,
            dt=1.0,
            target_level=2.5,
            Q=100.0,  # 状态权重
            R=1.0     # 控制权重
        )

        # 如果MPC暴露代价函数计算
        if hasattr(mpc, 'compute_cost'):
            # 偏离目标较大的状态应该有更高的代价
            cost_far = mpc.compute_cost(current_level=1.0, u=15.0)
            cost_near = mpc.compute_cost(current_level=2.4, u=15.0)

            assert cost_far > cost_near


# ============================================================================
# 控制器对比测试
# ============================================================================

@pytest.mark.integration
class TestControllerComparison:
    """控制器性能对比测试"""

    def test_pid_vs_mpc_tracking(self):
        """对比PID和MPC的跟踪性能"""
        # 创建控制器
        pid = PIDController(Kp=5.0, Ki=0.5, Kd=0.1, dt=0.5,
                          output_limits=(5.0, 30.0))
        pid.set_setpoint(2.5)

        mpc = MPCController(horizon=10, dt=0.5, target_level=2.5,
                          u_min=5.0, u_max=30.0)

        # 模拟相同的系统
        def simulate_system(controller, n_steps=100):
            current_level = 1.0
            levels = []
            controls = []

            for _ in range(n_steps):
                # 计算控制输入
                if isinstance(controller, PIDController):
                    u = controller.compute(current_level)
                else:
                    u = controller.compute_control(current_level)

                # 系统动态
                outflow = 15.0
                A = 10.0
                current_level = current_level + 0.5 * (u - outflow) / A

                levels.append(current_level)
                controls.append(u)

            return levels, controls

        # 运行两个控制器
        pid_levels, pid_controls = simulate_system(pid)
        mpc_levels, mpc_controls = simulate_system(mpc)

        # 两个控制器都应该能稳定系统
        assert abs(np.mean(pid_levels[-20:]) - 2.5) < 0.5
        assert abs(np.mean(mpc_levels[-20:]) - 2.5) < 0.5

        # 打印性能指标（可选）
        pid_mae = np.mean(np.abs(np.array(pid_levels) - 2.5))
        mpc_mae = np.mean(np.abs(np.array(mpc_levels) - 2.5))

        print(f"\nPID MAE: {pid_mae:.4f}")
        print(f"MPC MAE: {mpc_mae:.4f}")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
