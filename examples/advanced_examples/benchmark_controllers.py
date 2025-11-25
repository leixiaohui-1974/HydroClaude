# -*- coding: utf-8 -*-
"""
控制器性能基准测试示例

对比不同控制策略的性能：
1. PID控制器
2. MPC控制器
3. 自适应MPC控制器

使用标准测试场景：
- 阶跃响应
- 斜坡跟踪
- 正弦跟踪
- 扰动抑制

作者：HydroClaude Team
日期：2025-10-24
"""

import numpy as np
import warnings
warnings.filterwarnings("ignore")
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from tools.performance_benchmark import (
    BenchmarkRunner,
    ControllerInterface,
    StepResponseScenario,
    RampTrackingScenario,
    SinusoidalTrackingScenario,
    DisturbanceRejectionScenario
)
from control.idz_model import IDZParameters, IDZModel
from control.online_identification import IDZIdentifier


# ==================== 简化系统模型 ====================

class SimplifiedPoolModel:
    """简化的池段模型（用于基准测试）"""

    def __init__(self, params: IDZParameters, dt: float):
        """
        初始化

        参数：
            params: IDZ参数
            dt: 采样时间
        """
        self.params = params
        self.dt = dt
        self.model = IDZModel(params, dt)
        self.current_output = 0.0

    def step(self, u: float, disturbance: float = 0.0) -> float:
        """
        仿真一步

        参数：
            u: 控制输入（流量差）
            disturbance: 扰动（上游流量变化）

        返回：
            y: 输出（水深）
        """
        # 实际输入是控制输入+扰动
        total_input = u + disturbance
        self.current_output = self.model.step(total_input)
        return self.current_output

    def reset(self):
        """重置模型状态"""
        self.model.reset()
        self.current_output = 0.0


# ==================== 控制器实现 ====================

class PIDController(ControllerInterface):
    """PID控制器"""

    def __init__(self, kp: float = 0.5, ki: float = 0.1, kd: float = 0.05,
                 dt: float = 1.0, u_min: float = -1.0, u_max: float = 1.0):
        """
        初始化PID控制器

        参数：
            kp: 比例增益
            ki: 积分增益
            kd: 微分增益
            dt: 采样时间
            u_min, u_max: 控制输入限幅
        """
        self.kp = kp
        self.ki = ki
        self.kd = kd
        self.dt = dt
        self.u_min = u_min
        self.u_max = u_max

        self.integral = 0.0
        self.last_error = 0.0

    def reset(self):
        """重置控制器状态"""
        self.integral = 0.0
        self.last_error = 0.0

    def compute_control(self, reference: float, output: float,
                       disturbance: float = 0.0) -> float:
        """计算PID控制"""
        error = reference - output

        # 比例项
        p_term = self.kp * error

        # 积分项（带抗饱和）
        self.integral += error * self.dt
        i_term = self.ki * self.integral

        # 微分项
        d_term = self.kd * (error - self.last_error) / self.dt
        self.last_error = error

        # 总控制量
        u = p_term + i_term + d_term

        # 限幅
        u = np.clip(u, self.u_min, self.u_max)

        # 抗饱和回退
        if u == self.u_min or u == self.u_max:
            # 如果饱和，回退积分
            self.integral -= error * self.dt * 0.5

        return u

    def get_name(self) -> str:
        return f"PID (Kp={self.kp}, Ki={self.ki}, Kd={self.kd})"


class MPCController(ControllerInterface):
    """模型预测控制器（基于IDZ模型）"""

    def __init__(self, idz_params: IDZParameters, dt: float,
                 horizon: int = 20, u_min: float = -1.0, u_max: float = 1.0):
        """
        初始化MPC控制器

        参数：
            idz_params: IDZ模型参数
            dt: 采样时间
            horizon: 预测时域
            u_min, u_max: 控制输入限幅
        """
        self.idz_model = IDZModel(idz_params, dt)
        self.dt = dt
        self.horizon = horizon
        self.u_min = u_min
        self.u_max = u_max

        # MPC权重
        self.Q = 10.0  # 输出权重
        self.R = 0.1   # 控制权重

    def reset(self):
        """重置控制器状态"""
        self.idz_model.reset()

    def compute_control(self, reference: float, output: float,
                       disturbance: float = 0.0) -> float:
        """
        计算MPC控制（简化版：只优化当前时刻）

        由于没有约束优化器，这里使用简化的MPC：
        - 评估多个候选控制输入
        - 选择使代价函数最小的输入
        """
        # 候选控制输入
        n_candidates = 21
        u_candidates = np.linspace(self.u_min, self.u_max, n_candidates)

        best_cost = float('inf')
        best_u = 0.0

        for u in u_candidates:
            # 保存当前状态
            x_backup = self.idz_model.x.copy()
            delay_backup = self.idz_model.delay_buffer.copy()

            # 预测未来轨迹
            u_sequence = np.ones(self.horizon) * u
            y_pred = self.idz_model.predict(u_sequence)

            # 计算代价
            tracking_error = np.sum((y_pred - reference)**2)
            control_effort = np.sum(u**2 * self.horizon)
            cost = self.Q * tracking_error + self.R * control_effort

            # 恢复状态
            self.idz_model.x = x_backup
            self.idz_model.delay_buffer = delay_backup

            # 更新最优控制
            if cost < best_cost:
                best_cost = cost
                best_u = u

        # 应用最优控制并更新模型状态
        self.idz_model.step(best_u)

        return best_u

    def get_name(self) -> str:
        return f"MPC (H={self.horizon}, Q={self.Q}, R={self.R})"


class AdaptiveMPCController(ControllerInterface):
    """自适应MPC控制器（在线辨识+MPC）"""

    def __init__(self, initial_params: IDZParameters, dt: float,
                 horizon: int = 20, u_min: float = -1.0, u_max: float = 1.0,
                 adaptation_enabled: bool = True):
        """
        初始化自适应MPC控制器

        参数：
            initial_params: 初始IDZ模型参数
            dt: 采样时间
            horizon: 预测时域
            u_min, u_max: 控制输入限幅
            adaptation_enabled: 是否启用自适应
        """
        self.dt = dt
        self.horizon = horizon
        self.u_min = u_min
        self.u_max = u_max
        self.adaptation_enabled = adaptation_enabled

        # IDZ模型（会被在线更新）
        self.idz_model = IDZModel(initial_params, dt)
        self.current_params = initial_params

        # 在线辨识器
        self.identifier = IDZIdentifier(dt=dt)

        # MPC权重
        self.Q = 10.0
        self.R = 0.1

        # 历史数据
        self.last_u = 0.0
        self.last_y = 0.0

    def reset(self):
        """重置控制器状态"""
        self.idz_model.reset()
        self.identifier = IDZIdentifier(dt=self.dt)
        self.last_u = 0.0
        self.last_y = 0.0

    def compute_control(self, reference: float, output: float,
                       disturbance: float = 0.0) -> float:
        """计算自适应MPC控制"""
        # 在线辨识（使用上一步的数据）
        if self.adaptation_enabled and self.last_u is not None:
            identified_params = self.identifier.update(self.last_u, output)

            # 如果辨识成功，更新模型
            if identified_params is not None:
                self.current_params = identified_params
                # 创建新的IDZ模型（保留状态的近似）
                old_x = self.idz_model.x.copy()
                self.idz_model = IDZModel(identified_params, self.dt)
                # 尝试保留部分状态（维度可能不同，简单处理）
                min_dim = min(len(old_x), len(self.idz_model.x))
                self.idz_model.x[:min_dim] = old_x[:min_dim]

        # MPC优化（与静态MPC相同）
        n_candidates = 21
        u_candidates = np.linspace(self.u_min, self.u_max, n_candidates)

        best_cost = float('inf')
        best_u = 0.0

        for u in u_candidates:
            # 保存当前状态
            x_backup = self.idz_model.x.copy()
            delay_backup = self.idz_model.delay_buffer.copy()

            # 预测
            u_sequence = np.ones(self.horizon) * u
            y_pred = self.idz_model.predict(u_sequence)

            # 代价
            tracking_error = np.sum((y_pred - reference)**2)
            control_effort = np.sum(u**2 * self.horizon)
            cost = self.Q * tracking_error + self.R * control_effort

            # 恢复状态
            self.idz_model.x = x_backup
            self.idz_model.delay_buffer = delay_backup

            if cost < best_cost:
                best_cost = cost
                best_u = u

        # 应用控制并更新模型
        self.idz_model.step(best_u)

        # 保存历史
        self.last_u = best_u
        self.last_y = output

        return best_u

    def get_name(self) -> str:
        adapt_str = "Adaptive" if self.adaptation_enabled else "Static"
        return f"{adapt_str} MPC (H={self.horizon})"


# ==================== 主程序 ====================

def main():
    """主函数"""
    print("=" * 80)
    print("控制器性能基准测试")
    print("=" * 80)

    # ===== 1. 定义系统 =====
    dt = 1.0
    idz_params = IDZParameters(
        K=100.0,
        tau_z=50.0,
        tau_d=100.0,
        theta=20.0
    )

    pool_model = SimplifiedPoolModel(idz_params, dt)

    # 创建系统模型函数（闭包）
    def system_model(u: float, disturbance: float) -> float:
        return pool_model.step(u, disturbance)

    # ===== 2. 定义控制器 =====
    controllers = [
        PIDController(kp=0.5, ki=0.1, kd=0.05, dt=dt, u_min=-1.0, u_max=1.0),
        MPCController(idz_params, dt=dt, horizon=20, u_min=-1.0, u_max=1.0),
        AdaptiveMPCController(idz_params, dt=dt, horizon=20, u_min=-1.0, u_max=1.0,
                            adaptation_enabled=True)
    ]

    # ===== 3. 定义测试场景 =====
    scenarios = [
        StepResponseScenario(
            duration=600.0, dt=dt,
            initial_value=0.0, final_value=2.0, step_time=60.0
        ),
        RampTrackingScenario(
            duration=600.0, dt=dt,
            initial_value=0.0, ramp_rate=0.005, ramp_start=60.0
        ),
        SinusoidalTrackingScenario(
            duration=600.0, dt=dt,
            mean_value=2.0, amplitude=0.5, frequency=0.005
        ),
        DisturbanceRejectionScenario(
            duration=600.0, dt=dt,
            setpoint=2.0, disturbance_magnitude=0.3, disturbance_time=200.0
        )
    ]

    # ===== 4. 创建基准测试运行器 =====
    runner = BenchmarkRunner(system_model, dt=dt)

    # ===== 5. 运行对比测试 =====
    # 注意：每个场景测试前需要重置系统
    results = {}
    for scenario in scenarios:
        scenario_results = []
        print(f"\n{'=' * 80}")
        print(f"场景: {scenario.name}")
        print(f"{'=' * 80}")

        for controller in controllers:
            # 重置系统
            pool_model.reset()

            # 运行基准测试
            metrics = runner.run_benchmark(controller, scenario, verbose=True)
            scenario_results.append(metrics)

        results[scenario.name] = scenario_results

    runner.results = results

    # ===== 6. 保存和可视化结果 =====
    output_dir = "benchmark_results"
    runner.save_results(output_dir)
    runner.plot_comparison(output_dir)

    # ===== 7. 打印总结 =====
    runner.print_summary()

    print("\n" + "=" * 80)
    print("基准测试完成！")
    print(f"结果已保存到: {output_dir}/")
    print("=" * 80)


if __name__ == '__main__':
    main()
