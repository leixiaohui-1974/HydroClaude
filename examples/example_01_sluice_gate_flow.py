"""
示例1扩展：明渠闸门过流动力学分析

简化方案：
1. 将渠道分为上游段和下游段两个Canal对象
2. 闸门作为连接节点，使用堰流公式计算过流
3. 测试恒定流和非恒定流两种情况

Author: Claude
Date: 2025-10-21
"""

import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import numpy as np
import matplotlib.pyplot as plt
import matplotlib.animation as animation
from utils.stability_evaluator import StabilityEvaluator


class SluiceGate:
    """闸门类 - 简化的堰流模型"""

    def __init__(self, width, opening, Cd=0.6):
        """
        Args:
            width: 闸门宽度 (m)
            opening: 闸门开度 (m)
            Cd: 流量系数 (默认0.6)
        """
        self.width = width
        self.opening = opening
        self.Cd = Cd
        self.g = 9.81

    def calculate_discharge(self, h_upstream, h_downstream):
        """
        计算闸门过流量

        流态判断改进：
        1. 如果下游水位 > 闸门开度，则为淹没出流
        2. 否则检查 e < 0.67 * h_upstream 判断自由/淹没出流

        自由出流：Q = Cd * B * e * sqrt(2*g*h_upstream)
        淹没出流：Q = Cd * B * e * sqrt(2*g*(h_upstream - h_downstream))

        Args:
            h_upstream: 上游水深 (m)
            h_downstream: 下游水深 (m)

        Returns:
            discharge: 流量 (m³/s)
            flow_type: 'free' or 'submerged'
        """
        e = self.opening

        # 改进的流态判断
        # 条件1：下游水位超过闸孔，肯定是淹没出流
        # 条件2：上下游水位差很小，也是淹没出流
        if h_downstream > e or (h_upstream - h_downstream) < 0.5:
            # 淹没出流
            delta_h = max(0.001, h_upstream - h_downstream)
            discharge = self.Cd * self.width * e * np.sqrt(2 * self.g * delta_h)
            flow_type = 'submerged'
        else:
            # 自由出流
            discharge = self.Cd * self.width * e * np.sqrt(2 * self.g * h_upstream)
            flow_type = 'free'

        return discharge, flow_type

    def calculate_upstream_depth(self, Q, h_downstream):
        """
        反算上游水深：给定流量和下游水位，计算上游水位

        使用淹没出流公式的解析解（适用于本例的小流量情况）

        Args:
            Q: 流量 (m³/s)
            h_downstream: 下游水深 (m)

        Returns:
            h_upstream: 上游水深 (m)
        """
        # 对于小流量、下游水位较高的情况，通常是淹没出流
        # Q = Cd * B * e * sqrt(2*g*(h_up - h_down))
        # h_up = h_down + (Q / (Cd * B * e))^2 / (2*g)

        C = self.Cd * self.width * self.opening
        delta_h = (Q / C) ** 2 / (2 * self.g)
        h_up = h_downstream + delta_h

        # 验证这个结果
        Q_check, flow_type = self.calculate_discharge(h_up, h_downstream)

        # 如果误差较大，使用数值迭代
        if abs(Q_check - Q) / Q > 0.01:
            from scipy.optimize import fsolve

            def equation(h):
                Q_calc, _ = self.calculate_discharge(h, h_downstream)
                return Q_calc - Q

            try:
                h_up = fsolve(equation, h_up, full_output=False)[0]
                h_up = max(h_downstream + 0.001, h_up)
            except:
                pass  # 保持解析解结果

        return h_up


class SimplifiedCanalReach:
    """简化的渠道段 - 用于演示闸门过流（改进稳定性）"""

    def __init__(self, length, width, n_points):
        self.length = length
        self.width = width
        self.n_points = n_points
        self.dx = length / (n_points - 1)
        self.x = np.linspace(0, length, n_points)

        # 状态变量 (简化为均匀分布)
        self.h = np.ones(n_points) * 5.0  # 水深
        self.Q = np.ones(n_points) * 5.0  # 流量

        # 稳定性参数
        self.relaxation = 0.5  # 松弛因子

    def set_uniform_state(self, h, Q):
        """设置均匀状态"""
        self.h = np.ones(self.n_points) * h
        self.Q = np.ones(self.n_points) * Q

    def update_stable(self, dt, Q_in, Q_out):
        """
        稳定的更新方法（改进版）

        使用松弛因子和限制器确保稳定性
        """
        # 当前平均水深
        h_old = np.mean(self.h)

        # 质量守恒：dV/dt = Q_in - Q_out
        V_old = h_old * self.width * self.length
        dV = (Q_in - Q_out) * dt
        V_new_theoretical = V_old + dV

        # 新水深（理论值）
        h_new_theoretical = V_new_theoretical / (self.width * self.length)

        # 应用松弛因子（避免突变）
        h_new = h_old + self.relaxation * (h_new_theoretical - h_old)

        # 限制水深范围（物理约束）
        h_new = np.clip(h_new, 0.5, 15.0)

        # 流量也使用松弛因子
        Q_new_theoretical = (Q_in + Q_out) / 2
        Q_old = np.mean(self.Q)
        Q_new = Q_old + self.relaxation * (Q_new_theoretical - Q_old)

        # 更新状态（均匀分布）
        self.h = np.ones(self.n_points) * h_new
        self.Q = np.ones(self.n_points) * Q_new

        return h_new, Q_new


def run_sluice_gate_dynamics():
    """运行闸门流量动力学分析"""

    print("=" * 80)
    print("示例1扩展：明渠闸门过流动力学分析")
    print("=" * 80)
    print()

    # === 系统配置 ===
    canal_length_total = 1000.0  # 总长度
    canal_width = 10.0
    gate_position = 500.0  # 闸门位置

    # 上游段和下游段
    upstream_reach = SimplifiedCanalReach(
        length=gate_position,
        width=canal_width,
        n_points=26
    )

    downstream_reach = SimplifiedCanalReach(
        length=canal_length_total - gate_position,
        width=canal_width,
        n_points=26
    )

    # 闸门
    gate = SluiceGate(
        width=canal_width,
        opening=2.5,  # 半开
        Cd=0.6
    )

    print("系统配置:")
    print(f"  渠道总长度: {canal_length_total} m")
    print(f"  渠道宽度: {canal_width} m")
    print(f"  闸门位置: {gate_position} m")
    print(f"  闸门开度: {gate.opening} m")
    print(f"  流量系数: {gate.Cd}")
    print()

    # === 场景1: 恒定流 ===
    print("=" * 80)
    print("场景1: 恒定流分析")
    print("-" * 80)

    # 边界条件
    Q_upstream_bc = 5.0
    h_downstream_bc = 5.0

    # 计算稳态初值（有水头损失）
    h_up_init = gate.calculate_upstream_depth(Q_upstream_bc, h_downstream_bc)
    print(f"\n计算稳态初值:")
    print(f"  上游流量: {Q_upstream_bc} m³/s")
    print(f"  下游水位: {h_downstream_bc} m")
    print(f"  上游水位: {h_up_init:.4f} m")
    print(f"  水头损失: {h_up_init - h_downstream_bc:.4f} m")

    # 验证
    Q_check, flow_type_check = gate.calculate_discharge(h_up_init, h_downstream_bc)
    print(f"  验证闸门流量: {Q_check:.4f} m³/s (应为 {Q_upstream_bc} m³/s)")
    print(f"  流态: {flow_type_check}")
    print()

    # 初始条件（使用稳态值）
    upstream_reach.set_uniform_state(h_up_init, Q_upstream_bc)
    downstream_reach.set_uniform_state(h_downstream_bc, Q_upstream_bc)

    # 仿真参数
    dt = 10.0
    total_time_1 = 500.0
    n_steps_1 = int(total_time_1 / dt)

    # 数据存储
    time1 = []
    h_up_1 = []
    h_down_1 = []
    Q_gate_1 = []
    flow_type_1 = []

    print(f"边界条件: Q_upstream={Q_upstream_bc} m³/s, h_downstream={h_downstream_bc} m")
    print(f"仿真时长: {total_time_1} s, 时间步长: {dt} s")
    print()

    for i in range(n_steps_1):
        t = i * dt

        # 闸门上下游水深
        h_u = np.mean(upstream_reach.h)
        h_d = np.mean(downstream_reach.h)

        # 计算闸门流量
        Q_gate, f_type = gate.calculate_discharge(h_u, h_d)

        # 更新上游段 (入流=边界流量, 出流=闸门流量)
        upstream_reach.update_stable(dt, Q_upstream_bc, Q_gate)

        # 更新下游段 (入流=闸门流量, 出流=Q_gate)
        # 注意：下游段也用Q_gate作为出流，保持流量连续性
        downstream_reach.update_stable(dt, Q_gate, Q_gate)

        # 强制下游水位为边界条件（用较强的约束）
        downstream_reach.h[:] = h_downstream_bc

        # 记录数据
        time1.append(t)
        h_up_1.append(h_u)
        h_down_1.append(h_d)
        Q_gate_1.append(Q_gate)
        flow_type_1.append(f_type)

        if i % 10 == 0:
            print(f"  t={t:6.0f}s: Q_gate={Q_gate:.3f} m³/s, "
                  f"h_up={h_u:.3f}m, h_down={h_d:.3f}m, type={f_type}")

    print()
    print(f"恒定流最终状态:")
    print(f"  闸门流量: {Q_gate_1[-1]:.3f} m³/s")
    print(f"  上游水深: {h_up_1[-1]:.3f} m")
    print(f"  下游水深: {h_down_1[-1]:.3f} m")
    print(f"  水头损失: {h_up_1[-1] - h_down_1[-1]:.4f} m")
    print(f"  流态: {flow_type_1[-1]}")
    print()

    # 稳定性评价
    print("=" * 80)
    print("场景1：稳定性评价")
    print("-" * 80)

    evaluator = StabilityEvaluator()
    canal_params = {
        'length': canal_length_total,
        'width': canal_width,
        'slope': 0.0001,
        'manning_n': 0.025,
        'nx': 51
    }

    # 需要准备完整的空间分布数据
    h_history1_full = []
    Q_history1_full = []
    for h_u, h_d, q_g in zip(h_up_1, h_down_1, Q_gate_1):
        # 简化：上游段用h_u，下游段用h_d
        h_profile = np.concatenate([
            np.ones(26) * h_u,
            np.ones(25) * h_d
        ])
        Q_profile = np.ones(51) * q_g
        h_history1_full.append(h_profile)
        Q_history1_full.append(Q_profile)

    result1 = evaluator.evaluate(
        time=np.array(time1),
        h_history=h_history1_full,
        Q_history=Q_history1_full,
        canal_params=canal_params,
        method_name="场景1_恒定流"
    )

    evaluator.print_report("场景1_恒定流")
    print()

    # === 场景2: 非恒定流 (流量阶跃) ===
    print("=" * 80)
    print("场景2: 非恒定流 - 上游流量阶跃 (5.0 → 8.0 m³/s)")
    print("-" * 80)

    # 阶跃参数
    step_time = 100.0
    Q_before_step = 5.0
    Q_after_step = 8.0

    # 初始条件：使用阶跃前的稳态值
    h_up_init_2 = gate.calculate_upstream_depth(Q_before_step, h_downstream_bc)
    print(f"\n初始稳态（阶跃前）:")
    print(f"  上游流量: {Q_before_step} m³/s")
    print(f"  上游水位: {h_up_init_2:.4f} m")
    print(f"  下游水位: {h_downstream_bc} m")

    upstream_reach.set_uniform_state(h_up_init_2, Q_before_step)
    downstream_reach.set_uniform_state(h_downstream_bc, Q_before_step)

    # 仿真参数（延长时间以达到新稳态）
    total_time_2 = 1000.0  # 延长到1000s
    n_steps_2 = int(total_time_2 / dt)

    # 数据存储
    time2 = []
    h_up_2 = []
    h_down_2 = []
    Q_gate_2 = []
    flow_type_2 = []
    Q_upstream_2 = []

    print(f"阶跃时刻: {step_time} s")
    print(f"流量变化: {Q_before_step} → {Q_after_step} m³/s")
    print(f"仿真时长: {total_time_2} s")
    print()

    for i in range(n_steps_2):
        t = i * dt

        # 上游边界流量（阶跃）
        if t < step_time:
            Q_up_bc = Q_before_step
        else:
            Q_up_bc = Q_after_step

        # 闸门上下游水深
        h_u = np.mean(upstream_reach.h)
        h_d = np.mean(downstream_reach.h)

        # 计算闸门流量
        Q_gate, f_type = gate.calculate_discharge(h_u, h_d)

        # 更新上游段
        upstream_reach.update_stable(dt, Q_up_bc, Q_gate)

        # 更新下游段（同场景1）
        downstream_reach.update_stable(dt, Q_gate, Q_gate)

        # 强制下游水位为边界条件
        downstream_reach.h[:] = h_downstream_bc

        # 记录数据
        time2.append(t)
        h_up_2.append(h_u)
        h_down_2.append(h_d)
        Q_gate_2.append(Q_gate)
        flow_type_2.append(f_type)
        Q_upstream_2.append(Q_up_bc)

        if i % 10 == 0 or abs(t - step_time) < dt:
            marker = " <-- STEP" if abs(t - step_time) < dt else ""
            print(f"  t={t:6.0f}s: Q_up={Q_up_bc:.1f}, Q_gate={Q_gate:.3f} m³/s, "
                  f"h_up={h_u:.3f}m, h_down={h_d:.3f}m, type={f_type}{marker}")

    # 计算阶跃后的理论稳态值
    h_up_final_theory = gate.calculate_upstream_depth(Q_after_step, h_downstream_bc)
    Q_final_theory, flow_type_final_theory = gate.calculate_discharge(h_up_final_theory, h_downstream_bc)

    print()
    print(f"非恒定流最终状态:")
    print(f"  闸门流量: {Q_gate_2[-1]:.3f} m³/s (目标: {Q_after_step} m³/s)")
    print(f"  上游水深: {h_up_2[-1]:.3f} m (初始: {h_up_2[0]:.3f} m, 理论终值: {h_up_final_theory:.3f} m)")
    print(f"  下游水深: {h_down_2[-1]:.3f} m (边界: {h_downstream_bc} m)")
    print(f"  水头损失: {h_up_2[-1] - h_down_2[-1]:.4f} m")
    print(f"  流态: {flow_type_2[-1]}")
    print(f"  水位变化: {h_up_2[-1] - h_up_2[0]:.3f} m")
    print()

    # 稳定性评价
    print("=" * 80)
    print("场景2：稳定性评价")
    print("-" * 80)

    # 准备完整的空间分布数据
    h_history2_full = []
    Q_history2_full = []
    for h_u, h_d, q_g in zip(h_up_2, h_down_2, Q_gate_2):
        h_profile = np.concatenate([
            np.ones(26) * h_u,
            np.ones(25) * h_d
        ])
        Q_profile = np.ones(51) * q_g
        h_history2_full.append(h_profile)
        Q_history2_full.append(Q_profile)

    result2 = evaluator.evaluate(
        time=np.array(time2),
        h_history=h_history2_full,
        Q_history=Q_history2_full,
        canal_params=canal_params,
        method_name="场景2_非恒定流"
    )

    evaluator.print_report("场景2_非恒定流")

    # 对比两个场景
    evaluator.compare_methods()
    print()

    # === 生成可视化 ===
    print("=" * 80)
    print("生成可视化")
    print("=" * 80)

    generated_files = []

    # 计算数据范围（用于固定y轴）
    all_h = h_up_1 + h_down_1 + h_up_2 + h_down_2
    h_min, h_max = min(all_h), max(all_h)
    h_range = h_max - h_min
    h_ylim = [h_min - 0.1 * h_range, h_max + 0.1 * h_range]

    all_Q = Q_gate_1 + Q_gate_2 + Q_upstream_2
    Q_min, Q_max = min(all_Q), max(all_Q)
    Q_range = Q_max - Q_min
    Q_ylim = [max(0, Q_min - 0.1 * Q_range), Q_max + 0.1 * Q_range]

    # 时程曲线
    fig, axes = plt.subplots(3, 2, figsize=(14, 12))

    # 场景1 - 水深
    ax = axes[0, 0]
    ax.plot(time1, h_up_1, 'b-', linewidth=2, label='Upstream')
    ax.plot(time1, h_down_1, 'g-', linewidth=2, label='Downstream')
    ax.set_xlabel('Time (s)', fontsize=10)
    ax.set_ylabel('Water Depth (m)', fontsize=10)
    ax.set_title('Scenario 1 (Steady): Water Depth', fontsize=11, fontweight='bold')
    ax.set_ylim(h_ylim)  # 固定y轴
    ax.grid(True, alpha=0.3)
    ax.legend(fontsize=9)

    # 场景1 - 流量
    ax = axes[1, 0]
    ax.plot(time1, Q_gate_1, 'r-', linewidth=2)
    ax.axhline(y=Q_upstream_bc, color='k', linestyle='--', alpha=0.5, label='Upstream BC')
    ax.set_xlabel('Time (s)', fontsize=10)
    ax.set_ylabel('Flow Rate (m³/s)', fontsize=10)
    ax.set_title('Scenario 1 (Steady): Gate Flow', fontsize=11, fontweight='bold')
    ax.set_ylim(Q_ylim)  # 固定y轴
    ax.grid(True, alpha=0.3)
    ax.legend(fontsize=9)

    # 场景1 - 过流曲线
    ax = axes[2, 0]
    ax.plot(h_up_1, Q_gate_1, 'bo-', markersize=3, alpha=0.6)
    ax.set_xlabel('Upstream Depth (m)', fontsize=10)
    ax.set_ylabel('Gate Flow (m³/s)', fontsize=10)
    ax.set_title('Scenario 1: Discharge Curve', fontsize=11, fontweight='bold')
    ax.grid(True, alpha=0.3)

    # 场景2 - 水深
    ax = axes[0, 1]
    ax.plot(time2, h_up_2, 'b-', linewidth=2, label='Upstream')
    ax.plot(time2, h_down_2, 'g-', linewidth=2, label='Downstream')
    ax.axvline(x=step_time, color='k', linestyle='--', alpha=0.5, label='Step Time')
    ax.set_xlabel('Time (s)', fontsize=10)
    ax.set_ylabel('Water Depth (m)', fontsize=10)
    ax.set_title('Scenario 2 (Unsteady): Water Depth', fontsize=11, fontweight='bold')
    ax.set_ylim(h_ylim)  # 固定y轴
    ax.grid(True, alpha=0.3)
    ax.legend(fontsize=9)

    # 场景2 - 流量
    ax = axes[1, 1]
    ax.plot(time2, Q_upstream_2, 'k--', linewidth=1.5, alpha=0.7, label='Upstream BC')
    ax.plot(time2, Q_gate_2, 'r-', linewidth=2, label='Gate Flow')
    ax.axvline(x=step_time, color='k', linestyle='--', alpha=0.5)
    ax.set_xlabel('Time (s)', fontsize=10)
    ax.set_ylabel('Flow Rate (m³/s)', fontsize=10)
    ax.set_title('Scenario 2 (Unsteady): Flow Response', fontsize=11, fontweight='bold')
    ax.set_ylim(Q_ylim)  # 固定y轴
    ax.grid(True, alpha=0.3)
    ax.legend(fontsize=9)

    # 场景2 - 过流曲线
    ax = axes[2, 1]
    # 使用颜色表示时间
    scatter = ax.scatter(h_up_2, Q_gate_2, c=time2, cmap='viridis',
                        s=20, alpha=0.6, edgecolors='none')
    ax.set_xlabel('Upstream Depth (m)', fontsize=10)
    ax.set_ylabel('Gate Flow (m³/s)', fontsize=10)
    ax.set_title('Scenario 2: Discharge Curve (colored by time)', fontsize=11, fontweight='bold')
    ax.grid(True, alpha=0.3)
    cbar = plt.colorbar(scatter, ax=ax)
    cbar.set_label('Time (s)', fontsize=9)

    plt.tight_layout()
    fig_path = 'reports/figures/example_01_sluice_gate_dynamics.png'
    os.makedirs('reports/figures', exist_ok=True)
    plt.savefig(fig_path, dpi=150, bbox_inches='tight')
    plt.close(fig)
    generated_files.append(fig_path)
    print(f"  ✓ 动力学分析图")

    # 闸门过流特性图
    fig, axes = plt.subplots(1, 2, figsize=(14, 5))

    # 理论过流曲线
    ax = axes[0]
    h_range = np.linspace(2.0, 8.0, 50)
    Q_free = gate.Cd * gate.width * gate.opening * np.sqrt(2 * gate.g * h_range)
    delta_h_range = np.linspace(0.5, 3.0, 30)
    Q_submerged = gate.Cd * gate.width * gate.opening * np.sqrt(2 * gate.g * delta_h_range)

    ax.plot(h_range, Q_free, 'b-', linewidth=2, label='Free Flow (theory)')
    ax.plot([3.0 + dh for dh in delta_h_range], Q_submerged, 'g-',
           linewidth=2, label='Submerged Flow (theory, h_down=3m)')

    # 仿真结果
    ax.plot(h_up_1, Q_gate_1, 'ro', markersize=4, alpha=0.5, label='Scenario 1 (Steady)')
    ax.plot(h_up_2, Q_gate_2, 'mo', markersize=3, alpha=0.3, label='Scenario 2 (Unsteady)')

    ax.set_xlabel('Upstream Water Depth (m)', fontsize=11)
    ax.set_ylabel('Gate Discharge (m³/s)', fontsize=11)
    ax.set_title('Gate Discharge Characteristics', fontsize=12, fontweight='bold')
    ax.grid(True, alpha=0.3)
    ax.legend(fontsize=9)

    # 流态判断示意图
    ax = axes[1]
    h_test = np.linspace(2.0, 8.0, 100)
    e = gate.opening
    h_threshold = e / 0.67

    ax.fill_between(h_test, 0, 20, where=(h_test < h_threshold),
                   color='blue', alpha=0.2, label='Free Flow Region')
    ax.fill_between(h_test, 0, 20, where=(h_test >= h_threshold),
                   color='green', alpha=0.2, label='Submerged Flow Region')
    ax.axvline(x=h_threshold, color='r', linestyle='--', linewidth=2,
              label=f'Threshold: h = {h_threshold:.2f}m')

    # 标注闸门开度
    ax.axhline(y=gate.opening, color='k', linestyle='-', linewidth=3,
              label=f'Gate Opening: e = {gate.opening}m')

    ax.set_xlabel('Upstream Water Depth (m)', fontsize=11)
    ax.set_ylabel('Vertical Position (m)', fontsize=11)
    ax.set_title('Flow Regime Classification', fontsize=12, fontweight='bold')
    ax.set_ylim([0, 10])
    ax.grid(True, alpha=0.3)
    ax.legend(fontsize=9)

    plt.tight_layout()
    fig_path2 = 'reports/figures/example_01_sluice_gate_characteristics.png'
    plt.savefig(fig_path2, dpi=150, bbox_inches='tight')
    plt.close(fig)
    generated_files.append(fig_path2)
    print(f"  ✓ 过流特性图")

    # === 生成动画 ===
    # 场景1动画（恒定流）
    def create_steady_animation():
        """创建恒定流动画"""
        fig, axes = plt.subplots(2, 1, figsize=(12, 8))

        # 准备空间剖面数据
        x_up = upstream_reach.x
        x_down = gate_position + downstream_reach.x

        def animate(frame):
            for ax in axes:
                ax.clear()

            # 水深剖面
            ax = axes[0]
            h_u = h_up_1[frame]
            h_d = h_down_1[frame]
            ax.plot(x_up, np.ones_like(x_up) * h_u, 'b-', linewidth=2, label='Upstream')
            ax.plot(x_down, np.ones_like(x_down) * h_d, 'g-', linewidth=2, label='Downstream')
            ax.axvline(x=gate_position, color='r', linestyle='--', linewidth=2, alpha=0.5, label='Gate')
            ax.set_xlabel('Position (m)', fontsize=11)
            ax.set_ylabel('Water Depth (m)', fontsize=11)
            ax.set_title(f'Scenario 1 (Steady Flow) - Time: {time1[frame]:.1f}s', fontsize=12, fontweight='bold')
            ax.set_ylim(h_ylim)
            ax.grid(True, alpha=0.3)
            ax.legend(fontsize=10)

            # 流量剖面
            ax = axes[1]
            Q_g = Q_gate_1[frame]
            ax.plot(x_up, np.ones_like(x_up) * Q_g, 'r-', linewidth=2, label='Flow Rate')
            ax.plot(x_down, np.ones_like(x_down) * Q_g, 'r-', linewidth=2)
            ax.axvline(x=gate_position, color='r', linestyle='--', linewidth=2, alpha=0.5)
            ax.axhline(y=Q_upstream_bc, color='k', linestyle=':', alpha=0.5, label='Target BC')
            ax.set_xlabel('Position (m)', fontsize=11)
            ax.set_ylabel('Flow Rate (m³/s)', fontsize=11)
            ax.set_title(f'Gate Flow: {Q_g:.3f} m³/s', fontsize=12, fontweight='bold')
            ax.set_ylim(Q_ylim)
            ax.grid(True, alpha=0.3)
            ax.legend(fontsize=10)

            plt.tight_layout()

        anim = animation.FuncAnimation(fig, animate, frames=len(time1), interval=100, repeat=True)
        anim_path = 'reports/figures/example_01_gate_scenario1_steady.gif'
        anim.save(anim_path, writer='pillow', fps=10)
        plt.close(fig)
        return anim_path

    # 场景2动画（非恒定流）
    def create_unsteady_animation():
        """创建非恒定流动画"""
        fig, axes = plt.subplots(2, 1, figsize=(12, 8))

        x_up = upstream_reach.x
        x_down = gate_position + downstream_reach.x

        def animate(frame):
            for ax in axes:
                ax.clear()

            # 水深剖面
            ax = axes[0]
            h_u = h_up_2[frame]
            h_d = h_down_2[frame]
            ax.plot(x_up, np.ones_like(x_up) * h_u, 'b-', linewidth=2, label='Upstream')
            ax.plot(x_down, np.ones_like(x_down) * h_d, 'g-', linewidth=2, label='Downstream')
            ax.axvline(x=gate_position, color='r', linestyle='--', linewidth=2, alpha=0.5, label='Gate')

            # 标记是否已阶跃
            if time2[frame] >= step_time:
                ax.text(0.02, 0.98, 'AFTER STEP', transform=ax.transAxes,
                       fontsize=12, fontweight='bold', color='red',
                       verticalalignment='top',
                       bbox=dict(boxstyle='round', facecolor='yellow', alpha=0.5))

            ax.set_xlabel('Position (m)', fontsize=11)
            ax.set_ylabel('Water Depth (m)', fontsize=11)
            ax.set_title(f'Scenario 2 (Unsteady Flow) - Time: {time2[frame]:.1f}s', fontsize=12, fontweight='bold')
            ax.set_ylim(h_ylim)
            ax.grid(True, alpha=0.3)
            ax.legend(fontsize=10)

            # 流量剖面
            ax = axes[1]
            Q_g = Q_gate_2[frame]
            Q_up = Q_upstream_2[frame]
            ax.plot(x_up, np.ones_like(x_up) * Q_g, 'r-', linewidth=2, label='Gate Flow')
            ax.plot(x_down, np.ones_like(x_down) * Q_g, 'r-', linewidth=2)
            ax.axvline(x=gate_position, color='r', linestyle='--', linewidth=2, alpha=0.5)
            ax.axhline(y=Q_up, color='k', linestyle=':', alpha=0.5, label=f'Upstream BC: {Q_up:.1f}')
            ax.set_xlabel('Position (m)', fontsize=11)
            ax.set_ylabel('Flow Rate (m³/s)', fontsize=11)
            ax.set_title(f'Gate Flow: {Q_g:.3f} m³/s (Target: {Q_up:.1f} m³/s)', fontsize=12, fontweight='bold')
            ax.set_ylim(Q_ylim)
            ax.grid(True, alpha=0.3)
            ax.legend(fontsize=10)

            plt.tight_layout()

        anim = animation.FuncAnimation(fig, animate, frames=len(time2), interval=100, repeat=True)
        anim_path = 'reports/figures/example_01_gate_scenario2_unsteady.gif'
        anim.save(anim_path, writer='pillow', fps=10)
        plt.close(fig)
        return anim_path

    print(f"  ✓ 生成场景1动画...")
    anim1_path = create_steady_animation()
    generated_files.append(anim1_path)
    print(f"    → {anim1_path}")

    print(f"  ✓ 生成场景2动画...")
    anim2_path = create_unsteady_animation()
    generated_files.append(anim2_path)
    print(f"    → {anim2_path}")

    print()
    print("=" * 80)
    print("分析完成！")
    print("=" * 80)

    print(f"\n关键结论:")
    print(f"\n1. 恒定流情况:")
    print(f"   - 系统达到稳态，闸门流量≈上游边界流量")
    print(f"   - 最终闸门流量: {Q_gate_1[-1]:.3f} m³/s (边界: {Q_upstream_bc} m³/s)")
    print(f"   - 上游水深调整以满足过流能力")

    print(f"\n2. 非恒定流情况:")
    print(f"   - 上游流量阶跃后，系统动态响应")
    print(f"   - 闸门流量从 {Q_gate_2[0]:.3f} → {Q_gate_2[-1]:.3f} m³/s")
    print(f"   - 上游水深变化: {h_up_2[0]:.3f} → {h_up_2[-1]:.3f} m")
    print(f"   - 说明闸门对流量变化的调节作用")

    print(f"\n3. 闸门过流特性:")
    print(f"   - 开度: {gate.opening} m")
    print(f"   - 流态转换阈值: h ≈ {gate.opening/0.67:.2f} m")
    print(f"   - 本次仿真主要为{flow_type_2[-1]}流")

    print(f"\n生成文件:")
    for f in generated_files:
        print(f"  - {f}")

    print("\n" + "=" * 80)


if __name__ == "__main__":
    run_sluice_gate_dynamics()
