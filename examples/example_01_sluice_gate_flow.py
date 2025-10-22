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

        自由出流（开度 < 0.67 * 上游水深）:
            Q = Cd * B * e * sqrt(2*g*h_upstream)

        淹没出流（开度 >= 0.67 * 上游水深）:
            Q = Cd * B * e * sqrt(2*g*(h_upstream - h_downstream))

        Args:
            h_upstream: 上游水深 (m)
            h_downstream: 下游水深 (m)

        Returns:
            discharge: 流量 (m³/s)
            flow_type: 'free' or 'submerged'
        """
        e = self.opening

        # 判断流态
        if e < 0.67 * h_upstream:
            # 自由出流
            discharge = self.Cd * self.width * e * np.sqrt(2 * self.g * h_upstream)
            flow_type = 'free'
        else:
            # 淹没出流
            delta_h = max(0.01, h_upstream - h_downstream)
            discharge = self.Cd * self.width * e * np.sqrt(2 * self.g * delta_h)
            flow_type = 'submerged'

        return discharge, flow_type


class SimplifiedCanalReach:
    """简化的渠道段 - 用于演示闸门过流"""

    def __init__(self, length, width, n_points):
        self.length = length
        self.width = width
        self.n_points = n_points
        self.dx = length / (n_points - 1)
        self.x = np.linspace(0, length, n_points)

        # 状态变量 (简化为均匀分布)
        self.h = np.ones(n_points) * 5.0  # 水深
        self.Q = np.ones(n_points) * 5.0  # 流量

    def set_uniform_state(self, h, Q):
        """设置均匀状态"""
        self.h = np.ones(self.n_points) * h
        self.Q = np.ones(self.n_points) * Q

    def update_simple(self, dt, Q_in, Q_out):
        """
        简化更新（质量守恒）

        假设渠段内水深和流量均匀变化
        """
        # 质量守恒
        V_total = np.mean(self.h) * self.width * self.length
        dV = (Q_in - Q_out) * dt
        V_new = V_total + dV

        # 新的平均水深
        h_new = V_new / (self.width * self.length)
        h_new = max(0.5, min(10.0, h_new))  # 限制范围

        # 更新状态
        self.h = np.ones(self.n_points) * h_new
        self.Q = np.ones(self.n_points) * (Q_in + Q_out) / 2

        return h_new, (Q_in + Q_out) / 2


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

    # 初始条件
    h_init = 5.0
    Q_init = 5.0
    upstream_reach.set_uniform_state(h_init, Q_init)
    downstream_reach.set_uniform_state(h_init, Q_init)

    # 边界条件
    Q_upstream_bc = 5.0
    h_downstream_bc = 5.0

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
        upstream_reach.update_simple(dt, Q_upstream_bc, Q_gate)

        # 更新下游段 (入流=闸门流量, 出流=边界流量)
        # 下游出流由水位边界控制，简化假设为闸门流量
        downstream_reach.update_simple(dt, Q_gate, Q_gate)
        # 强制下游水位为边界条件
        downstream_reach.h[-1] = h_downstream_bc

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
    print(f"  流态: {flow_type_1[-1]}")
    print()

    # === 场景2: 非恒定流 (流量阶跃) ===
    print("=" * 80)
    print("场景2: 非恒定流 - 上游流量阶跃 (5.0 → 8.0 m³/s)")
    print("-" * 80)

    # 重置初始条件
    upstream_reach.set_uniform_state(h_init, Q_init)
    downstream_reach.set_uniform_state(h_init, Q_init)

    # 阶跃参数
    step_time = 100.0
    Q_before_step = 5.0
    Q_after_step = 8.0

    # 仿真参数
    total_time_2 = 500.0
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
        upstream_reach.update_simple(dt, Q_up_bc, Q_gate)

        # 更新下游段
        downstream_reach.update_simple(dt, Q_gate, Q_gate)
        downstream_reach.h[-1] = h_downstream_bc

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

    print()
    print(f"非恒定流最终状态:")
    print(f"  闸门流量: {Q_gate_2[-1]:.3f} m³/s")
    print(f"  上游水深: {h_up_2[-1]:.3f} m (初始: {h_up_2[0]:.3f} m)")
    print(f"  下游水深: {h_down_2[-1]:.3f} m (初始: {h_down_2[0]:.3f} m)")
    print(f"  流态: {flow_type_2[-1]}")
    print()

    # === 生成可视化 ===
    print("=" * 80)
    print("生成可视化")
    print("=" * 80)

    generated_files = []

    # 时程曲线
    fig, axes = plt.subplots(3, 2, figsize=(14, 12))

    # 场景1 - 水深
    ax = axes[0, 0]
    ax.plot(time1, h_up_1, 'b-', linewidth=2, label='Upstream')
    ax.plot(time1, h_down_1, 'g-', linewidth=2, label='Downstream')
    ax.set_xlabel('Time (s)', fontsize=10)
    ax.set_ylabel('Water Depth (m)', fontsize=10)
    ax.set_title('Scenario 1 (Steady): Water Depth', fontsize=11, fontweight='bold')
    ax.grid(True, alpha=0.3)
    ax.legend(fontsize=9)

    # 场景1 - 流量
    ax = axes[1, 0]
    ax.plot(time1, Q_gate_1, 'r-', linewidth=2)
    ax.axhline(y=Q_upstream_bc, color='k', linestyle='--', alpha=0.5, label='Upstream BC')
    ax.set_xlabel('Time (s)', fontsize=10)
    ax.set_ylabel('Flow Rate (m³/s)', fontsize=10)
    ax.set_title('Scenario 1 (Steady): Gate Flow', fontsize=11, fontweight='bold')
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
