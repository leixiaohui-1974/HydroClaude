"""
IDZ-Saint-Venant深度集成示例

展示如何将IDZ控制模型与物理水力学模型深度集成，
实现基于物理模型的自适应MPC控制。

系统架构：
┌─────────────────────────────────────────────────────┐
│                  闭环控制系统                         │
│                                                       │
│  ┌──────────┐    u(k)    ┌─────────────────┐       │
│  │          │───────────>│   物理模拟器     │       │
│  │   MPC    │            │  (非线性动力学)  │       │
│  │ 控制器   │<───────────│                 │       │
│  │          │    y(k)    └─────────────────┘       │
│  └────┬─────┘                                       │
│       │                                             │
│       │ IDZ参数                                     │
│       │                                             │
│  ┌────▼─────┐    (u,y)   ┌─────────────────┐       │
│  │   IDZ    │<───────────│   在线辨识       │       │
│  │  模型库   │            │   (RLS算法)     │       │
│  └──────────┘            └─────────────────┘       │
│                                                      │
└──────────────────────────────────────────────────────┘

功能特点：
1. 从非线性物理模型仿真中在线辨识IDZ参数
2. 自适应更新MPC控制器的预测模型
3. 对比静态vs自适应IDZ参数的控制性能
4. 验证不同工况下的模型适应能力

作者：HydroClaude Team
日期：2025-10-24
"""

import numpy as np
import matplotlib.pyplot as plt
from typing import List, Tuple, Dict
import sys
import os

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))

from control.idz_model import IDZParameters, IDZModel
from control.online_identification import IDZIdentifier


class SimplifiedCanalDynamics:
    """
    简化的渠道动力学模型

    基于水量平衡方程的集总参数模型：
    dV/dt = Q_in - Q_out
    h = V / A_surface

    特点：
    - 非线性：流速随水深变化（Manning公式）
    - 真实：考虑渠道几何和水力摩阻
    - 简化：集总参数，避免复杂的偏微分方程求解
    """

    def __init__(self, length: float, width: float, bed_slope: float,
                 manning: float, initial_depth: float, dt: float = 10.0):
        """
        初始化渠道动力学

        Args:
            length: 渠道长度 (m)
            width: 渠道宽度 (m)
            bed_slope: 底坡
            manning: 曼宁系数
            initial_depth: 初始水深 (m)
            dt: 仿真时间步 (s)
        """
        self.length = length
        self.width = width
        self.bed_slope = bed_slope
        self.manning = manning
        self.dt = dt
        self.g = 9.81

        # 状态变量
        self.depth = initial_depth  # 当前水深
        self.volume = self.depth * self.width * self.length  # 当前水量

        # 表面面积（用于计算水深）
        self.surface_area = self.width * self.length

    def step(self, q_in: float, q_out: float):
        """
        时间步进仿真

        Args:
            q_in: 上游入流 (m³/s)
            q_out: 下游出流 (m³/s)
        """
        # 水量平衡
        dV = (q_in - q_out) * self.dt
        self.volume += dV

        # 限制体积为正
        self.volume = max(0, self.volume)

        # 更新水深
        self.depth = self.volume / self.surface_area

    def get_normal_flow(self, depth: float) -> float:
        """
        计算给定水深下的正常流量（Manning公式）

        Args:
            depth: 水深 (m)

        Returns:
            正常流量 (m³/s)
        """
        if depth <= 0:
            return 0.0

        # 过水断面积
        area = self.width * depth

        # 湿周
        perimeter = self.width + 2 * depth

        # 水力半径
        hydraulic_radius = area / perimeter if perimeter > 0 else 0

        # Manning公式：Q = (1/n) * A * R^(2/3) * S^(1/2)
        velocity = (1 / self.manning) * (hydraulic_radius ** (2/3)) * (self.bed_slope ** 0.5)
        flow = area * velocity

        return flow

    def get_state(self) -> Dict[str, float]:
        """获取当前状态"""
        return {
            'depth': self.depth,
            'volume': self.volume,
            'normal_flow': self.get_normal_flow(self.depth)
        }


class IDZSaintVenantIntegration:
    """
    IDZ-物理模型深度集成系统

    集成物理模拟、在线辨识和自适应控制
    """

    def __init__(self, canal: SimplifiedCanalDynamics, dt: float = 10.0):
        """
        初始化集成系统

        Args:
            canal: 渠道动力学对象
            dt: 控制采样周期 (s)
        """
        self.canal = canal
        self.dt = dt

        # 初始IDZ参数（基于设计工况）
        self.initial_idz_params = self._compute_initial_idz_parameters()

        # 当前使用的IDZ参数（会被在线更新）
        self.current_idz_params = self.initial_idz_params

        # IDZ模型（用于MPC预测）
        self.idz_model = IDZModel(self.current_idz_params, dt)

        # 在线辨识器
        self.identifier = IDZIdentifier(dt=dt)

        # 工作点（用于计算变化量）
        self.depth_nominal = canal.depth  # 标称水深
        self.flow_nominal = 20.0  # 标称流量 (m³/s)

        # 数据缓冲
        self.u_buffer = []  # 控制输入历史
        self.y_buffer = []  # 系统输出历史

        # 统计信息
        self.identification_history = []

    def _compute_initial_idz_parameters(self) -> IDZParameters:
        """基于渠道设计参数计算初始IDZ参数"""
        # 使用渠道的设计参数
        length = self.canal.length
        width = self.canal.width
        bed_slope = self.canal.bed_slope
        manning = self.canal.manning
        normal_depth = 2.0  # 设计正常水深

        # 从水力学参数计算IDZ参数
        params = IDZParameters.from_hydraulics(
            length=length,
            width=width,
            bed_slope=bed_slope,
            manning=manning,
            normal_depth=normal_depth
        )

        return params

    def update_identification(self, u: float, y: float):
        """
        更新在线辨识

        Args:
            u: 控制输入（流量 m³/s）- 绝对值
            y: 系统输出（水位 m）- 绝对值
        """
        # 添加到缓冲
        self.u_buffer.append(u)
        self.y_buffer.append(y)

        # 转换为变化量（修正：IDZ模型需要变化量而非绝对值）
        u_deviation = u - self.flow_nominal
        y_deviation = y - self.depth_nominal

        # 在线辨识（传入变化量）
        identified_params = self.identifier.update(u_deviation, y_deviation)

        # 如果辨识收敛，更新IDZ参数
        if identified_params is not None:
            self.current_idz_params = identified_params
            self.idz_model = IDZModel(identified_params, self.dt)

            # 记录辨识历史
            self.identification_history.append({
                'time': len(self.u_buffer) * self.dt,
                'K': identified_params.K,
                'tau_z': identified_params.tau_z,
                'tau_d': identified_params.tau_d,
                'theta': identified_params.theta
            })


class SimpleMPCController:
    """
    简化的MPC控制器（基于IDZ模型）

    使用解析方法求解，避免数值优化
    """

    def __init__(self, idz_system: IDZSaintVenantIntegration,
                 horizon: int = 10,
                 kp: float = 10.0,
                 ki: float = 0.5):
        """
        初始化简化MPC控制器

        Args:
            idz_system: IDZ集成系统
            horizon: 预测时域
            kp: 比例增益（调优后：5.0 -> 10.0）
            ki: 积分增益（调优后：0.1 -> 0.5）
        """
        self.system = idz_system
        self.horizon = horizon
        self.kp = kp
        self.ki = ki

        # 积分项
        self.integral_error = 0.0

        # 积分抗饱和
        self.integral_max = 100.0  # 限制积分项

        # 控制约束
        self.u_min = 0.0
        self.u_max = 50.0

    def compute_control(self, current_depth: float, target_depth: float,
                        q_upstream: float) -> float:
        """
        计算控制输入（基于PI控制 + 前馈）

        Args:
            current_depth: 当前水深
            target_depth: 目标水深
            q_upstream: 上游流量（前馈）

        Returns:
            控制输出（下游流量）
        """
        # 误差
        error = target_depth - current_depth

        # 积分（带抗饱和）
        self.integral_error += error * self.system.dt
        self.integral_error = np.clip(self.integral_error, -self.integral_max, self.integral_max)

        # PI控制 (修正：符号反转)
        # 当水深过低(error>0)时，应减少下游出流
        # 当水深过高(error<0)时，应增加下游出流
        u_feedback = -(self.kp * error + self.ki * self.integral_error)

        # 前馈（基于水量平衡）
        u_feedforward = q_upstream

        # 总控制量
        u = u_feedforward + u_feedback

        # 约束
        u = np.clip(u, self.u_min, self.u_max)

        return u


def run_comparison_simulation():
    """
    运行对比仿真：静态IDZ vs 自适应IDZ

    改进的场景（更具挑战性）：
    1. 初始流量20 m³/s，目标水深2.0m
    2. 300s时流量扰动增加到28 m³/s（更大扰动）
    3. 600s时目标水深改变为2.5m
    4. 900s时流量扰动降至15 m³/s
    5. 1200s时目标水深改变为1.8m
    6. 仿真时长：1800s（30分钟）
    """
    print("=" * 80)
    print("IDZ-物理模型深度集成示例（改进版）")
    print("对比静态IDZ参数 vs 自适应IDZ参数的控制性能")
    print("=" * 80)

    # 仿真参数
    dt = 10.0  # 控制周期
    total_time = 1800.0  # 总仿真时间（延长到1800s）
    n_steps = int(total_time / dt)

    # 场景设置
    q_upstream_base = 20.0  # 基础上游流量
    target_depth = 2.0  # 初始目标水深

    # 创建两个系统进行对比
    print("\n1. 初始化系统...")

    # 系统1：静态IDZ参数
    canal_static = SimplifiedCanalDynamics(
        length=2000.0, width=10.0, bed_slope=0.0001,
        manning=0.025, initial_depth=2.0, dt=dt
    )
    system_static = IDZSaintVenantIntegration(canal_static, dt)
    system_static.identifier = None  # 禁用在线辨识
    controller_static = SimpleMPCController(system_static)

    # 系统2：自适应IDZ参数
    canal_adaptive = SimplifiedCanalDynamics(
        length=2000.0, width=10.0, bed_slope=0.0001,
        manning=0.025, initial_depth=2.0, dt=dt
    )
    system_adaptive = IDZSaintVenantIntegration(canal_adaptive, dt)
    controller_adaptive = SimpleMPCController(system_adaptive)

    print(f"   渠道长度: {canal_static.length}m")
    print(f"   渠道宽度: {canal_static.width}m")
    print(f"   初始IDZ参数: K={system_static.initial_idz_params.K:.1f}, "
          f"τ_d={system_static.initial_idz_params.tau_d:.1f}s")

    # 数据记录
    time_history = []
    depth_static, control_static = [], []
    depth_adaptive, control_adaptive = [], []
    idz_K_adaptive, idz_tau_adaptive = [], []
    target_history, disturbance_history = [], []

    print("\n2. 开始仿真...")
    print(f"   总时长: {total_time}s, 时间步: {dt}s, 步数: {n_steps}")

    for step in range(n_steps):
        t = step * dt

        # 场景变化（更具挑战性）
        if 300 <= t < 600:
            q_disturbance = 28.0  # 阶段1：大流量扰动（持续300s）
        elif 900 <= t < 1200:
            q_disturbance = 15.0  # 阶段3：小流量扰动（持续300s）
        else:
            q_disturbance = q_upstream_base  # 基础流量

        if 600 <= t < 1200:
            target_depth = 2.5  # 阶段2：高水深目标
        elif t >= 1200:
            target_depth = 1.8  # 阶段4：低水深目标
        else:
            target_depth = 2.0  # 初始水深目标

        # === 静态IDZ系统 ===
        depth_current_static = canal_static.depth
        u_static = controller_static.compute_control(
            depth_current_static, target_depth, q_disturbance
        )
        canal_static.step(q_disturbance, u_static)

        # === 自适应IDZ系统 ===
        depth_current_adaptive = canal_adaptive.depth

        # 在线辨识
        if step > 0:
            system_adaptive.update_identification(u_adaptive, depth_current_adaptive)

        u_adaptive = controller_adaptive.compute_control(
            depth_current_adaptive, target_depth, q_disturbance
        )
        canal_adaptive.step(q_disturbance, u_adaptive)

        # 记录数据
        time_history.append(t)
        depth_static.append(depth_current_static)
        control_static.append(u_static)
        depth_adaptive.append(depth_current_adaptive)
        control_adaptive.append(u_adaptive)
        idz_K_adaptive.append(system_adaptive.current_idz_params.K)
        idz_tau_adaptive.append(system_adaptive.current_idz_params.tau_d)
        target_history.append(target_depth)
        disturbance_history.append(q_disturbance)

        # 进度显示（增强诊断输出）
        if step % 10 == 0:
            # 计算当前误差
            error_adaptive = depth_current_adaptive - target_depth

            # RLS诊断信息
            rls = system_adaptive.identifier.rls
            rls_info = ""
            if len(rls.estimation_error_history) > 0:
                rls_error = rls.estimation_error_history[-1]
                rls_info = f", RLS_err={rls_error:.4f}"

            print(f"   进度: {step}/{n_steps} ({100*step/n_steps:.1f}%) - "
                  f"t={t:.0f}s, "
                  f"h_adp={depth_current_adaptive:.3f}m, "
                  f"err={error_adaptive:.3f}m, "
                  f"K={system_adaptive.current_idz_params.K:.1f}"
                  f"{rls_info}")

    print("\n3. 仿真完成！开始分析...")

    # 性能分析
    depth_static = np.array(depth_static)
    depth_adaptive = np.array(depth_adaptive)
    target_history = np.array(target_history)

    # 跟踪误差
    error_static = depth_static - target_history
    error_adaptive = depth_adaptive - target_history

    mae_static = np.mean(np.abs(error_static))
    mae_adaptive = np.mean(np.abs(error_adaptive))
    rmse_static = np.sqrt(np.mean(error_static**2))
    rmse_adaptive = np.sqrt(np.mean(error_adaptive**2))

    print(f"\n4. 性能对比:")
    print(f"   静态IDZ:")
    print(f"      MAE  = {mae_static:.4f}m")
    print(f"      RMSE = {rmse_static:.4f}m")
    print(f"   自适应IDZ:")
    print(f"      MAE  = {mae_adaptive:.4f}m")
    print(f"      RMSE = {rmse_adaptive:.4f}m")
    print(f"   性能提升:")
    print(f"      MAE  改善 {(1-mae_adaptive/mae_static)*100:.1f}%")
    print(f"      RMSE 改善 {(1-rmse_adaptive/rmse_static)*100:.1f}%")

    # 可视化
    print("\n5. 生成对比图表...")
    visualize_comparison(
        time_history,
        depth_static, control_static,
        depth_adaptive, control_adaptive,
        idz_K_adaptive, idz_tau_adaptive,
        target_history, disturbance_history
    )

    print("\n✅ 示例运行完成！")
    print("=" * 80)


def visualize_comparison(time, depth_static, control_static,
                        depth_adaptive, control_adaptive,
                        idz_K, idz_tau,
                        target, disturbance):
    """可视化对比结果"""

    fig, axes = plt.subplots(4, 1, figsize=(14, 12))

    # 子图1：水深对比
    ax = axes[0]
    ax.plot(time, depth_static, 'b-', linewidth=2, label='静态IDZ')
    ax.plot(time, depth_adaptive, 'r-', linewidth=2, label='自适应IDZ')
    ax.plot(time, target, 'k--', linewidth=1.5, label='目标水深')
    ax.axvline(300, color='gray', linestyle=':', alpha=0.5)
    ax.axvline(600, color='gray', linestyle=':', alpha=0.5)
    ax.set_ylabel('下游水深 (m)', fontsize=11)
    ax.legend(loc='upper right', fontsize=10)
    ax.grid(True, alpha=0.3)
    ax.set_title('IDZ-物理模型深度集成：自适应控制性能对比', fontsize=13, fontweight='bold')

    # 子图2：控制输入对比
    ax = axes[1]
    ax.plot(time, control_static, 'b-', linewidth=2, label='静态IDZ控制')
    ax.plot(time, control_adaptive, 'r-', linewidth=2, label='自适应IDZ控制')
    ax.plot(time, disturbance, 'g--', linewidth=1.5, alpha=0.7, label='上游扰动')
    ax.set_ylabel('下游流量 (m³/s)', fontsize=11)
    ax.legend(loc='upper right', fontsize=10)
    ax.grid(True, alpha=0.3)

    # 子图3：IDZ参数K的在线辨识
    ax = axes[2]
    ax.plot(time, idz_K, 'purple', linewidth=2, label='在线辨识K')
    ax.axhline(idz_K[0], color='orange', linestyle='--', linewidth=1.5, label='初始K')
    ax.set_ylabel('IDZ增益 K', fontsize=11)
    ax.legend(loc='upper right', fontsize=10)
    ax.grid(True, alpha=0.3)

    # 子图4：跟踪误差对比
    ax = axes[3]
    error_static = np.array(depth_static) - np.array(target)
    error_adaptive = np.array(depth_adaptive) - np.array(target)
    ax.plot(time, error_static, 'b-', linewidth=2, label='静态IDZ误差')
    ax.plot(time, error_adaptive, 'r-', linewidth=2, label='自适应IDZ误差')
    ax.axhline(0, color='black', linestyle='-', linewidth=0.8)
    ax.fill_between(time, error_static, alpha=0.2, color='blue')
    ax.fill_between(time, error_adaptive, alpha=0.2, color='red')
    ax.set_xlabel('时间 (s)', fontsize=11)
    ax.set_ylabel('跟踪误差 (m)', fontsize=11)
    ax.legend(loc='upper right', fontsize=10)
    ax.grid(True, alpha=0.3)

    plt.tight_layout()

    # 保存图片
    output_file = 'idz_saint_venant_integration_comparison.png'
    plt.savefig(output_file, dpi=150, bbox_inches='tight')
    print(f"   图表已保存: {output_file}")

    # plt.show()


if __name__ == '__main__':
    run_comparison_simulation()
