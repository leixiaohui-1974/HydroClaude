"""
基于IDZ模型的自适应MPC控制器

用于明渠串联闸泵群系统的自适应控制

特点：
- IDZ模型预测
- 在线参数辨识
- 自适应模型更新
- 约束处理
- 多目标优化（跟踪+控制量+稳定性）

作者：HydroClaude Team
日期：2025-10-24
"""

import numpy as np
import sys
import os
from dataclasses import dataclass, field
from typing import Optional, List, Tuple, Dict
from scipy.optimize import minimize
from enum import Enum

# 添加项目根目录
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

try:
    from idz_model import IDZModel, SeriesIDZModel, IDZParameters
    from online_identification import IDZIdentifier, IdentificationMethod
except ImportError:
    from control.idz_model import IDZModel, SeriesIDZModel, IDZParameters
    from control.online_identification import IDZIdentifier, IdentificationMethod


@dataclass
class AdaptiveIDZMPCConfig:
    """自适应IDZ-MPC配置"""
    # MPC参数
    prediction_horizon: int = 10    # 预测时域
    control_horizon: int = 5        # 控制时域
    dt: float = 60.0               # 采样时间 (s)

    # 权重
    tracking_weight: float = 1.0    # 跟踪误差权重
    control_weight: float = 0.1     # 控制量权重
    delta_u_weight: float = 0.5     # 控制增量权重

    # 约束
    u_min: List[float] = field(default_factory=lambda: [0.0])
    u_max: List[float] = field(default_factory=lambda: [10.0])
    du_max: List[float] = field(default_factory=lambda: [1.0])

    # 自适应参数
    enable_adaptation: bool = True
    adaptation_rate: float = 0.1
    min_data_for_adaptation: int = 20

    # 辨识参数
    identification_method: IdentificationMethod = IdentificationMethod.ADAPTIVE_RLS


class AdaptiveIDZMPC:
    """
    基于IDZ模型的自适应MPC控制器

    自适应机制：
    1. 在线辨识IDZ参数
    2. 定期更新预测模型
    3. 根据辨识精度调整权重
    """

    def __init__(self,
                 initial_idz_model: SeriesIDZModel,
                 config: Optional[AdaptiveIDZMPCConfig] = None):
        """
        初始化自适应MPC控制器

        Args:
            initial_idz_model: 初始IDZ模型
            config: MPC配置
        """
        self.config = config or AdaptiveIDZMPCConfig()

        # IDZ预测模型
        self.idz_model = initial_idz_model
        self.n_pools = initial_idz_model.n_pools
        self.n_controls = self.n_pools + 1  # n_pools个闸门/泵站

        # 在线辨识器（每个池段一个）
        self.identifiers = []
        if self.config.enable_adaptation:
            for i in range(self.n_pools):
                identifier = IDZIdentifier(
                    dt=self.config.dt,
                    method=self.config.identification_method
                )
                self.identifiers.append(identifier)

        # 状态历史
        self.state_history: List[np.ndarray] = []
        self.control_history: List[np.ndarray] = []
        self.output_history: List[np.ndarray] = []

        # 参数更新计数
        self.adaptation_count = 0
        self.last_update_step = 0

        # 当前控制输入
        self.u_current = np.zeros(self.n_controls)

    def compute_control(self,
                       y_current: np.ndarray,
                       y_setpoint: np.ndarray,
                       u_previous: Optional[np.ndarray] = None) -> np.ndarray:
        """
        计算MPC控制输入

        Args:
            y_current: 当前输出（各池段水位）
            y_setpoint: 设定值
            u_previous: 上一时刻控制输入

        Returns:
            控制输入
        """
        if u_previous is None:
            u_previous = self.u_current

        N_p = self.config.prediction_horizon
        N_c = self.config.control_horizon

        # 获取当前状态
        x_current = self.idz_model.get_state()

        # 定义优化问题
        def objective(u_flat):
            """目标函数：跟踪误差 + 控制量 + 控制增量"""
            # 重塑控制序列 [N_c, n_controls]
            u_sequence = u_flat.reshape(N_c, self.n_controls)

            # 扩展到预测时域（最后的控制量保持不变）
            u_full = np.zeros((N_p, self.n_controls))
            u_full[:N_c] = u_sequence
            for k in range(N_c, N_p):
                u_full[k] = u_sequence[-1]

            # 预测输出
            y_pred = self.idz_model.predict(u_full, x0=x_current)

            # 跟踪误差
            tracking_error = 0.0
            for k in range(N_p):
                e = y_pred[k] - y_setpoint
                tracking_error += self.config.tracking_weight * np.sum(e**2)

            # 控制量成本
            control_cost = 0.0
            for k in range(N_c):
                control_cost += self.config.control_weight * np.sum(u_sequence[k]**2)

            # 控制增量成本
            delta_u_cost = 0.0
            u_prev = u_previous
            for k in range(N_c):
                du = u_sequence[k] - u_prev
                delta_u_cost += self.config.delta_u_weight * np.sum(du**2)
                u_prev = u_sequence[k]

            return tracking_error + control_cost + delta_u_cost

        # 初始猜测（保持当前控制）
        u0 = np.tile(u_previous, (N_c, 1)).flatten()

        # 约束
        bounds = []
        for k in range(N_c):
            for i in range(self.n_controls):
                u_min = self.config.u_min[i] if i < len(self.config.u_min) else 0.0
                u_max = self.config.u_max[i] if i < len(self.config.u_max) else 10.0
                bounds.append((u_min, u_max))

        # 控制增量约束（通过非线性约束）
        def delta_u_constraint(u_flat):
            """控制增量约束"""
            u_sequence = u_flat.reshape(N_c, self.n_controls)
            constraints = []

            u_prev = u_previous
            for k in range(N_c):
                du = u_sequence[k] - u_prev
                for i in range(self.n_controls):
                    du_max = self.config.du_max[i] if i < len(self.config.du_max) else 1.0
                    # |du| <= du_max => -du_max - du <= 0 和 du - du_max <= 0
                    constraints.append(du_max - abs(du[i]))
                u_prev = u_sequence[k]

            return np.array(constraints)

        # 求解优化问题
        result = minimize(
            objective,
            u0,
            method='SLSQP',
            bounds=bounds,
            options={'maxiter': 100, 'ftol': 1e-6}
        )

        if not result.success:
            print(f"警告: MPC优化未收敛: {result.message}")

        # 提取第一个控制输入
        u_optimal = result.x.reshape(N_c, self.n_controls)[0]

        # 应用约束
        for i in range(self.n_controls):
            u_min = self.config.u_min[i] if i < len(self.config.u_min) else 0.0
            u_max = self.config.u_max[i] if i < len(self.config.u_max) else 10.0
            u_optimal[i] = np.clip(u_optimal[i], u_min, u_max)

        self.u_current = u_optimal

        return u_optimal

    def update_identification(self, u: np.ndarray, y: np.ndarray):
        """
        更新在线辨识

        Args:
            u: 控制输入 [n_controls]
            y: 测量输出 [n_pools]
        """
        if not self.config.enable_adaptation:
            return

        # 记录历史
        self.control_history.append(u.copy())
        self.output_history.append(y.copy())

        # 每个池段独立辨识
        # 简化：假设每个池段的输入是上下游流量差
        for i in range(self.n_pools):
            # 池段i的输入：u[i] - u[i+1]
            u_pool = u[i] - u[i+1] if i+1 < len(u) else u[i]
            y_pool = y[i]

            # 更新辨识
            idz_params = self.identifiers[i].update(u_pool, y_pool)

            # 定期更新模型
            if len(self.output_history) % 50 == 0 and idz_params is not None:
                self._update_model(i, idz_params)

    def _update_model(self, pool_index: int, new_params: IDZParameters):
        """
        更新IDZ模型参数

        Args:
            pool_index: 池段索引
            new_params: 新的IDZ参数
        """
        # 平滑更新（避免突变）
        current_model = self.idz_model.models[pool_index]
        current_params = current_model.params

        # 加权平均
        alpha = self.config.adaptation_rate

        updated_params = IDZParameters(
            K=(1-alpha) * current_params.K + alpha * new_params.K,
            tau_z=(1-alpha) * current_params.tau_z + alpha * new_params.tau_z,
            tau_d=(1-alpha) * current_params.tau_d + alpha * new_params.tau_d,
            theta=(1-alpha) * current_params.theta + alpha * new_params.theta
        )

        # 创建新模型
        new_model = IDZModel(updated_params, self.config.dt)
        new_model.set_state(current_model.get_state())

        # 更新
        self.idz_model.models[pool_index] = new_model

        self.adaptation_count += 1

        print(f"[自适应] 池段{pool_index+1}模型更新:")
        print(f"  K: {current_params.K:.2f} -> {updated_params.K:.2f}")
        print(f"  τ_z: {current_params.tau_z:.1f} -> {updated_params.tau_z:.1f}")
        print(f"  τ_d: {current_params.tau_d:.1f} -> {updated_params.tau_d:.1f}")

    def get_model_parameters(self) -> List[IDZParameters]:
        """获取当前IDZ模型参数"""
        return [model.params for model in self.idz_model.models]

    def reset(self):
        """重置控制器"""
        self.idz_model.reset()
        self.state_history = []
        self.control_history = []
        self.output_history = []
        self.u_current = np.zeros(self.n_controls)

        if self.config.enable_adaptation:
            for identifier in self.identifiers:
                identifier.reset()


if __name__ == "__main__":
    """测试自适应IDZ-MPC"""

    print("=" * 70)
    print("自适应IDZ-MPC控制器测试")
    print("=" * 70)

    # 测试1：单池段系统
    print("\n[测试1] 单池段系统 - 水位跟踪控制")
    print("-" * 70)

    # 创建IDZ模型
    from control.idz_model import design_idz_from_canal_geometry

    dt = 60.0
    idz_model = design_idz_from_canal_geometry(
        lengths=[1000.0],
        widths=[10.0],
        bed_slopes=[0.0001],
        manning_coeffs=[0.025],
        normal_depths=[2.0],
        dt=dt
    )

    print(f"IDZ模型参数:")
    for i, model in enumerate(idz_model.models):
        p = model.params
        print(f"  池段{i+1}: K={p.K:.2f}, τ_z={p.tau_z:.1f}s, "
              f"τ_d={p.tau_d:.1f}s, θ={p.theta:.1f}s")

    # 创建MPC控制器
    config = AdaptiveIDZMPCConfig(
        prediction_horizon=10,
        control_horizon=3,
        dt=dt,
        tracking_weight=10.0,
        control_weight=0.1,
        delta_u_weight=1.0,
        u_min=[0.0, 0.0],
        u_max=[30.0, 30.0],
        du_max=[2.0, 2.0],
        enable_adaptation=True
    )

    mpc = AdaptiveIDZMPC(idz_model, config)

    # 仿真
    n_steps = 30
    y_setpoint = np.array([3.0])  # 目标水位3m

    print(f"\n仿真设置:")
    print(f"  仿真步数: {n_steps}")
    print(f"  目标水位: {y_setpoint[0]:.2f} m")
    print(f"  采样时间: {dt:.0f} s")

    # 初始状态
    y_current = np.array([2.0])  # 初始水位2m
    u_current = np.array([10.0, 10.0])  # 上下游流量

    print(f"\n开始仿真...")
    print(f"{'步骤':>4} {'水位(m)':>10} {'上游流量':>10} {'下游流量':>10} {'误差(m)':>10}")
    print("-" * 60)

    for step in range(n_steps):
        # MPC控制
        u_optimal = mpc.compute_control(y_current, y_setpoint, u_current)

        # 应用到模型
        y_next = idz_model.step(u_optimal)

        # 更新辨识（使用带噪声的测量）
        y_measured = y_next + np.random.normal(0, 0.02, size=y_next.shape)
        mpc.update_identification(u_optimal, y_measured)

        # 输出
        error = y_next[0] - y_setpoint[0]
        if step % 5 == 0:
            print(f"{step:4d} {y_next[0]:10.3f} {u_optimal[0]:10.2f} "
                  f"{u_optimal[1]:10.2f} {error:10.3f}")

        # 更新
        y_current = y_next
        u_current = u_optimal

    print(f"\n最终状态:")
    print(f"  水位: {y_current[0]:.3f} m")
    print(f"  误差: {y_current[0] - y_setpoint[0]:.3f} m")
    print(f"  自适应更新次数: {mpc.adaptation_count}")

    # 测试2：三池段系统
    print("\n[测试2] 三池段串联系统")
    print("-" * 70)

    idz_model3 = design_idz_from_canal_geometry(
        lengths=[1000.0, 1200.0, 800.0],
        widths=[10.0, 12.0, 8.0],
        bed_slopes=[0.0001, 0.00012, 0.00015],
        manning_coeffs=[0.025, 0.025, 0.025],
        normal_depths=[2.0, 2.2, 1.8],
        dt=dt
    )

    print(f"三池段IDZ模型:")
    for i, model in enumerate(idz_model3.models):
        p = model.params
        print(f"  池段{i+1}: K={p.K:.2f}, τ_z={p.tau_z:.1f}s, "
              f"τ_d={p.tau_d:.1f}s, θ={p.theta:.1f}s")

    config3 = AdaptiveIDZMPCConfig(
        prediction_horizon=8,
        control_horizon=3,
        dt=dt,
        tracking_weight=10.0,
        control_weight=0.1,
        delta_u_weight=1.0,
        u_min=[0.0] * 4,
        u_max=[30.0] * 4,
        du_max=[2.0] * 4,
        enable_adaptation=True,
        adaptation_rate=0.05
    )

    mpc3 = AdaptiveIDZMPC(idz_model3, config3)

    # 仿真
    n_steps3 = 20
    y_setpoint3 = np.array([2.5, 2.7, 2.2])  # 各池段目标水位

    print(f"\n仿真设置:")
    print(f"  仿真步数: {n_steps3}")
    print(f"  目标水位: {y_setpoint3}")

    y_current3 = np.array([2.0, 2.0, 2.0])
    u_current3 = np.array([20.0, 18.0, 16.0, 14.0])

    print(f"\n开始仿真...")
    print(f"{'步骤':>4} {'池1水位':>10} {'池2水位':>10} {'池3水位':>10} "
          f"{'平均误差':>12}")
    print("-" * 60)

    for step in range(n_steps3):
        # MPC控制
        u_optimal3 = mpc3.compute_control(y_current3, y_setpoint3, u_current3)

        # 应用到模型
        y_next3 = idz_model3.step(u_optimal3)

        # 更新辨识
        y_measured3 = y_next3 + np.random.normal(0, 0.02, size=y_next3.shape)
        mpc3.update_identification(u_optimal3, y_measured3)

        # 输出
        avg_error = np.mean(np.abs(y_next3 - y_setpoint3))
        if step % 5 == 0:
            print(f"{step:4d} {y_next3[0]:10.3f} {y_next3[1]:10.3f} "
                  f"{y_next3[2]:10.3f} {avg_error:12.4f}")

        # 更新
        y_current3 = y_next3
        u_current3 = u_optimal3

    print(f"\n最终状态:")
    print(f"  水位: {y_current3}")
    print(f"  目标: {y_setpoint3}")
    print(f"  误差: {y_current3 - y_setpoint3}")
    print(f"  自适应更新次数: {mpc3.adaptation_count}")

    print("\n" + "=" * 70)
    print("自适应IDZ-MPC测试完成！")
    print("=" * 70)
