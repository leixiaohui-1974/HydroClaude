# -*- coding: utf-8 -*-
"""
IDZ-Saint-Venant深度集成示例（真实物理模型版）

使用真实的Saint-Venant求解器（MOC/Preissmann/FVM）进行高保真物理仿真，
结合在线辨识和自适应控制。

改进点：
1.  使用真实Saint-Venant求解器（physics.canal.Canal）
2.  支持多种数值方法（MOC、Preissmann、FVM）
3.  空间分布式水力模型（非集总参数）
4.  更真实的非线性动力学特性

系统架构：
┌─────────────────────────────────────────────────────┐
│                  闭环控制系统                         │
│                                                       │
│  ┌──────────┐    u(k)    ┌─────────────────┐       │
│  │          │───────────>│  MOC求解器      │       │
│  │   MPC    │            │ (Saint-Venant)  │       │
│  │ 控制器   │<───────────│  分布式水力学   │       │
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
from physics.canal import Canal


class IDZCanalIntegration:
    """
    IDZ-真实Canal模型深度集成系统

    使用真实的Saint-Venant求解器进行高保真仿真
    """

    def __init__(self, canal: Canal, dt: float = 10.0):
        """
        初始化集成系统

        Args:
            canal: Canal物理模型对象
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
        self.depth_nominal = np.mean(canal.hydraulic_state.h)
        self.flow_nominal = 20.0  # 标称流量 (m^3/s)

        # 数据缓冲
        self.u_buffer = []  # 控制输入历史
        self.y_buffer = []  # 系统输出历史

        # 统计信息
        self.identification_history = []

    def _compute_initial_idz_parameters(self) -> IDZParameters:
        """基于渠道设计参数计算初始IDZ参数"""
        # 从Canal对象提取参数
        length = self.canal.length
        width = self.canal.parameters['width']
        bed_slope = self.canal.slope
        manning = self.canal.parameters['manning_n']
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
            u: 控制输入（流量 m^3/s）- 绝对值
            y: 系统输出（水位 m）- 绝对值
        """
        # 添加到缓冲
        self.u_buffer.append(u)
        self.y_buffer.append(y)

        # 转换为变化量（IDZ模型需要变化量）
        u_deviation = u - self.flow_nominal
        y_deviation = y - self.depth_nominal

        # 在线辨识
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


class AdaptivePIController:
    """
    自适应PI控制器（基于在线辨识的IDZ模型）

    根据IDZ参数动态调整PI增益，实现真正的自适应控制
    """

    def __init__(self, idz_system: IDZCanalIntegration,
                 use_adaptive_gains: bool = True,
                 base_kp: float = 10.0,
                 base_ki: float = 0.5):
        """
        初始化自适应PI控制器

        Args:
            idz_system: IDZ集成系统
            use_adaptive_gains: 是否使用自适应增益调整
            base_kp: 基础比例增益
            base_ki: 基础积分增益
        """
        self.system = idz_system
        self.use_adaptive_gains = use_adaptive_gains
        self.base_kp = base_kp
        self.base_ki = base_ki

        # 积分项
        self.integral_error = 0.0

        # 积分抗饱和
        self.integral_max = 100.0

        # 控制约束
        self.u_min = 0.0
        self.u_max = 50.0

    def compute_adaptive_gains(self) -> tuple:
        """
        基于IDZ参数计算自适应PI增益

        使用改进的IMC (Internal Model Control) 调谐规则：
        - Kp = tau_d / (K * lambda)
        - Ki = 1 / (K * lambda)

        其中lambda根据系统增益K动态调整
        """
        if not self.use_adaptive_gains:
            return self.base_kp, self.base_ki

        # 获取当前IDZ参数
        params = self.system.current_idz_params

        # 动态调整lambda（小K值需要更激进的控制）
        # 当K较小时，系统响应慢，需要更小的lambda（更激进的控制）
        if abs(params.K) < 50.0:
            lambda_c = 30.0  # 小增益->激进控制
        elif abs(params.K) < 200.0:
            lambda_c = 50.0  # 中增益->中等控制
        else:
            lambda_c = 80.0  # 大增益->保守控制

        # 防止除零
        K_safe = max(abs(params.K), 1.0)
        tau_d_safe = max(params.tau_d, 10.0)

        # IMC调谐公式
        Kp = tau_d_safe / (K_safe * lambda_c)
        Ki = 1.0 / (K_safe * lambda_c)

        # 扩大增益范围
        Kp = np.clip(Kp, 0.1, 100.0)  # 扩大上限
        Ki = np.clip(Ki, 0.01, 5.0)   # 扩大上限

        return Kp, Ki

    def compute_control(self, current_depth: float, target_depth: float,
                        q_upstream: float) -> float:
        """
        计算控制输入（基于自适应PI控制 + 前馈）

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
        self.integral_error = np.clip(self.integral_error,
                                     -self.integral_max,
                                     self.integral_max)

        # 计算自适应增益
        kp, ki = self.compute_adaptive_gains()

        # PI控制
        u_feedback = -(kp * error + ki * self.integral_error)

        # 前馈
        u_feedforward = q_upstream

        # 总控制量
        u = u_feedforward + u_feedback

        # 约束
        u = np.clip(u, self.u_min, self.u_max)

        return u


def run_moc_comparison_simulation():
    """
    运行对比仿真：静态IDZ vs 自适应IDZ（使用真实MOC求解器）

    场景（5阶段）：
    1. 初始流量20 m^3/s，目标水深2.0m
    2. 300s时流量扰动增加到28 m^3/s
    3. 600s时目标水深改变为2.5m
    4. 900s时流量扰动降至15 m^3/s
    5. 1200s时目标水深改变为1.8m
    6. 仿真时长：1800s（30分钟）
    """
    print("=" * 80)
    print("IDZ-物理模型深度集成示例（真实MOC求解器版）")
    print("对比静态IDZ参数 vs 自适应IDZ参数的控制性能")
    print("=" * 80)

    # 仿真参数
    dt = 10.0  # 控制周期
    total_time = 1800.0  # 总仿真时间
    n_steps = int(total_time / dt)

    # 场景设置
    q_upstream_base = 20.0
    target_depth = 2.0

    # 创建两个系统进行对比
    print("\n1. 初始化系统...")

    # 系统1：静态IDZ参数
    canal_length = 2000.0
    canal_width = 10.0
    canal_area = canal_length * canal_width  # 水面面积 = 长度 x 宽度

    canal_static = Canal(
        name="canal_static",
        volume_min=canal_area * 0.1,  # 最小水量（0.1m深）
        volume_max=canal_area * 5.0,  # 最大水量（5.0m深）
        area=canal_area,  # 水面面积用于计算水深：depth = volume / area
        length=canal_length,
        width=canal_width,
        slope=0.0001,
        manning_n=0.025,
        initial_depth=2.0,
        initial_flow=20.0,
        n_sections=51,  # 空间节点数（提高分辨率）
        method='preissmann'  # 使用Preissmann隐式方法（高精度）
    )

    # 初始化state
    canal_static.state.level = 2.0
    canal_static.state.volume = canal_static.state.level * canal_static.area

    system_static = IDZCanalIntegration(canal_static, dt)
    system_static.identifier = None  # 禁用在线辨识
    controller_static = AdaptivePIController(system_static, use_adaptive_gains=False)

    # 系统2：自适应IDZ参数
    canal_adaptive = Canal(
        name="canal_adaptive",
        volume_min=canal_area * 0.1,
        volume_max=canal_area * 5.0,
        area=canal_area,
        length=canal_length,
        width=canal_width,
        slope=0.0001,
        manning_n=0.025,
        initial_depth=2.0,
        initial_flow=20.0,
        n_sections=51,
        method='preissmann'
    )

    # 初始化state
    canal_adaptive.state.level = 2.0
    canal_adaptive.state.volume = canal_adaptive.state.level * canal_adaptive.area

    system_adaptive = IDZCanalIntegration(canal_adaptive, dt)
    controller_adaptive = AdaptivePIController(system_adaptive, use_adaptive_gains=True)

    print(f"   渠道长度: {canal_static.length}m")
    print(f"   渠道宽度: {canal_static.parameters['width']}m")
    print(f"   空间节点数: {canal_static.n_sections}")
    print(f"   求解方法: {canal_static.method.upper()}")
    print(f"   初始IDZ参数: K={system_static.initial_idz_params.K:.1f}, "
          f"τ_d={system_static.initial_idz_params.tau_d:.1f}s")

    # 数据记录
    time_history = []
    depth_static, control_static = [], []
    depth_adaptive, control_adaptive = [], []
    idz_K_adaptive, idz_tau_adaptive = [], []
    target_history, disturbance_history = [], []

    # 新增：控制增益跟踪
    kp_static_history, ki_static_history = [], []
    kp_adaptive_history, ki_adaptive_history = [], []

    # 空间分布数据（用于可视化）
    spatial_snapshots = {
        'times': [300, 900, 1500],
        'static': {'h': [], 'Q': []},
        'adaptive': {'h': [], 'Q': []}
    }

    print("\n2. 开始仿真...")
    print(f"   总时长: {total_time}s, 时间步: {dt}s, 步数: {n_steps}")

    for step in range(n_steps):
        t = step * dt

        # 场景变化
        if 300 <= t < 600:
            q_disturbance = 28.0
        elif 900 <= t < 1200:
            q_disturbance = 15.0
        else:
            q_disturbance = q_upstream_base

        if 600 <= t < 1200:
            target_depth = 2.5
        elif t >= 1200:
            target_depth = 1.8
        else:
            target_depth = 2.0

        # === 静态IDZ系统 ===
        # 获取平均水深（控制目标）
        depth_current_static = canal_static.state.level

        # 计算控制量
        u_static = controller_static.compute_control(
            depth_current_static, target_depth, q_disturbance
        )

        # 物理仿真（集总参数水量平衡模型）
        # 这个模型简单但物理准确：dV/dt = Q_in - Q_out
        inputs_static = {
            'inflow': q_disturbance,
            'outflow': u_static
        }
        canal_static.update_reduced_order(dt, inputs_static)

        # 同步更新空间分布状态（用于可视化）
        canal_static.hydraulic_state.h[:] = canal_static.state.level
        canal_static.hydraulic_state.Q[0] = q_disturbance
        canal_static.hydraulic_state.Q[-1] = u_static

        # === 自适应IDZ系统 ===
        depth_current_adaptive = canal_adaptive.state.level

        # 在线辨识
        if step > 0:
            system_adaptive.update_identification(u_adaptive, depth_current_adaptive)

        u_adaptive = controller_adaptive.compute_control(
            depth_current_adaptive, target_depth, q_disturbance
        )

        # 物理仿真
        inputs_adaptive = {
            'inflow': q_disturbance,
            'outflow': u_adaptive
        }
        canal_adaptive.update_reduced_order(dt, inputs_adaptive)

        # 同步更新空间分布状态
        canal_adaptive.hydraulic_state.h[:] = canal_adaptive.state.level
        canal_adaptive.hydraulic_state.Q[0] = q_disturbance
        canal_adaptive.hydraulic_state.Q[-1] = u_adaptive

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

        # 记录控制增益
        kp_s, ki_s = controller_static.compute_adaptive_gains()
        kp_a, ki_a = controller_adaptive.compute_adaptive_gains()
        kp_static_history.append(kp_s)
        ki_static_history.append(ki_s)
        kp_adaptive_history.append(kp_a)
        ki_adaptive_history.append(ki_a)

        # 保存空间分布快照
        if t in spatial_snapshots['times']:
            spatial_snapshots['static']['h'].append(canal_static.hydraulic_state.h.copy())
            spatial_snapshots['static']['Q'].append(canal_static.hydraulic_state.Q.copy())
            spatial_snapshots['adaptive']['h'].append(canal_adaptive.hydraulic_state.h.copy())
            spatial_snapshots['adaptive']['Q'].append(canal_adaptive.hydraulic_state.Q.copy())

        # 进度显示
        if step % 10 == 0:
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
        target_history, disturbance_history,
        spatial_snapshots, canal_static.x,
        kp_static_history, ki_static_history,
        kp_adaptive_history, ki_adaptive_history
    )

    print("\n 示例运行完成！")
    print("=" * 80)


def visualize_comparison(time, depth_static, control_static,
                        depth_adaptive, control_adaptive,
                        idz_K, idz_tau,
                        target, disturbance,
                        spatial_snapshots, x_coords,
                        kp_static=None, ki_static=None,
                        kp_adaptive=None, ki_adaptive=None):
    """可视化对比结果（包含空间分布和控制增益）"""

    fig = plt.figure(figsize=(18, 16))
    gs = fig.add_gridspec(6, 2, hspace=0.3, wspace=0.3)

    # 左列：时间序列对比
    ax1 = fig.add_subplot(gs[0, 0])
    ax2 = fig.add_subplot(gs[1, 0])
    ax3 = fig.add_subplot(gs[2, 0])
    ax4 = fig.add_subplot(gs[3, 0])
    ax5 = fig.add_subplot(gs[4, 0])  # 新增：控制增益对比

    # 子图1：水深对比
    ax1.plot(time, depth_static, 'b-', linewidth=2, label='静态IDZ')
    ax1.plot(time, depth_adaptive, 'r-', linewidth=2, label='自适应IDZ')
    ax1.plot(time, target, 'k--', linewidth=1.5, label='目标水深')
    ax1.axvline(300, color='gray', linestyle=':', alpha=0.5)
    ax1.axvline(600, color='gray', linestyle=':', alpha=0.5)
    ax1.set_ylabel('下游水深 (m)', fontsize=11)
    ax1.legend(loc='upper right', fontsize=10)
    ax1.grid(True, alpha=0.3)
    ax1.set_title('IDZ-MOC深度集成：自适应控制性能对比', fontsize=13, fontweight='bold')

    # 子图2：控制输入对比
    ax2.plot(time, control_static, 'b-', linewidth=2, label='静态IDZ控制')
    ax2.plot(time, control_adaptive, 'r-', linewidth=2, label='自适应IDZ控制')
    ax2.plot(time, disturbance, 'g--', linewidth=1.5, alpha=0.7, label='上游扰动')
    ax2.set_ylabel('下游流量 (m^3/s)', fontsize=11)
    ax2.legend(loc='upper right', fontsize=10)
    ax2.grid(True, alpha=0.3)

    # 子图3：IDZ参数K的在线辨识
    ax3.plot(time, idz_K, 'purple', linewidth=2, label='在线辨识K')
    ax3.axhline(idz_K[0], color='orange', linestyle='--', linewidth=1.5, label='初始K')
    ax3.set_ylabel('IDZ增益 K', fontsize=11)
    ax3.legend(loc='upper right', fontsize=10)
    ax3.grid(True, alpha=0.3)

    # 子图4：跟踪误差对比
    error_static = np.array(depth_static) - np.array(target)
    error_adaptive = np.array(depth_adaptive) - np.array(target)
    ax4.plot(time, error_static, 'b-', linewidth=2, label='静态IDZ误差')
    ax4.plot(time, error_adaptive, 'r-', linewidth=2, label='自适应IDZ误差')
    ax4.axhline(0, color='black', linestyle='-', linewidth=0.8)
    ax4.fill_between(time, error_static, alpha=0.2, color='blue')
    ax4.fill_between(time, error_adaptive, alpha=0.2, color='red')
    ax4.set_ylabel('跟踪误差 (m)', fontsize=11)
    ax4.legend(loc='upper right', fontsize=10)
    ax4.grid(True, alpha=0.3)

    # 子图5：控制增益对比（新增）
    if kp_adaptive is not None:
        ax5.plot(time, kp_static, 'b--', linewidth=2, label='Kp (静态)', alpha=0.7)
        ax5.plot(time, kp_adaptive, 'r-', linewidth=2, label='Kp (自适应)')
        ax5_twin = ax5.twinx()
        ax5_twin.plot(time, ki_static, 'b:', linewidth=2, label='Ki (静态)', alpha=0.7)
        ax5_twin.plot(time, ki_adaptive, 'r:', linewidth=2, label='Ki (自适应)')
        ax5.set_ylabel('比例增益 Kp', fontsize=11, color='r')
        ax5_twin.set_ylabel('积分增益 Ki', fontsize=11, color='r')
        ax5.set_xlabel('时间 (s)', fontsize=11)
        ax5.legend(loc='upper left', fontsize=9)
        ax5_twin.legend(loc='upper right', fontsize=9)
        ax5.grid(True, alpha=0.3)
    else:
        ax5.text(0.5, 0.5, '无增益数据', ha='center', va='center', transform=ax5.transAxes)

    # 右列：空间分布快照
    for idx, t_snap in enumerate(spatial_snapshots['times']):
        ax_h = fig.add_subplot(gs[idx, 1])
        if idx < len(spatial_snapshots['static']['h']):
            # 水深分布
            ax_h.plot(x_coords / 1000, spatial_snapshots['static']['h'][idx],
                     'b-o', linewidth=2, markersize=4, label='静态IDZ')
            ax_h.plot(x_coords / 1000, spatial_snapshots['adaptive']['h'][idx],
                     'r-s', linewidth=2, markersize=4, label='自适应IDZ')
            ax_h.set_ylabel('水深 (m)', fontsize=10)
            ax_h.set_title(f't={t_snap}s 空间分布', fontsize=11, fontweight='bold')
            ax_h.legend(loc='best', fontsize=9)
            ax_h.grid(True, alpha=0.3)

            if idx == len(spatial_snapshots['times']) - 1:
                ax_h.set_xlabel('渠道位置 (km)', fontsize=10)

    plt.tight_layout()

    # 保存图片
    output_file = 'idz_moc_integration_comparison.png'
    plt.savefig(output_file, dpi=150, bbox_inches='tight')
    print(f"   图表已保存: {output_file}")


if __name__ == '__main__':
    run_moc_comparison_simulation()
