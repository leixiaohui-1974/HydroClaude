"""
示例1扩展：明渠闸门过流动力学分析（使用基础库重写）

使用基础库的CanalSolver和PreissmannSolver，确保数值稳定性

Author: Claude
Date: 2025-10-22
"""

import sys, os
# 添加项目根目录到路径
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

import numpy as np
import matplotlib.pyplot as plt
import matplotlib.animation as animation
from solvers.canal_solver import CanalSolver
from utils.canal_utils import compute_steady_uniform_flow


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

        Args:
            h_upstream: 上游水深 (m)
            h_downstream: 下游水深 (m)

        Returns:
            discharge: 流量 (m³/s)
            flow_type: 'free' or 'submerged'
        """
        e = self.opening

        # 流态判断
        if h_downstream > e or (h_upstream - h_downstream) < 0.1:
            # 淹没出流
            delta_h = max(0.001, h_upstream - h_downstream)
            discharge = self.Cd * self.width * e * np.sqrt(2 * self.g * delta_h)
            flow_type = 'submerged'
        else:
            # 自由出流
            discharge = self.Cd * self.width * e * np.sqrt(2 * self.g * h_upstream)
            flow_type = 'free'

        return discharge, flow_type


def run_sluice_gate_dynamics():
    """运行闸门流量动力学分析"""

    print("=" * 80)
    print("示例1扩展：明渠闸门过流动力学分析（基础库版本）")
    print("=" * 80)
    print()

    # === 系统配置 ===
    canal_length_total = 10000.0  # 总长度
    canal_width = 10.0
    gate_position = 5000.0  # 闸门位置（中点）
    n_points_total = 201  # 总空间点数

    # 渠道参数
    bed_slope = 0.0005  # 底坡
    manning_n = 0.025  # 曼宁糙率

    # 上下游段点数
    gate_idx = n_points_total // 2
    n_upstream = gate_idx + 1
    n_downstream = n_points_total - gate_idx

    # 创建上游渠道段
    upstream_solver = CanalSolver(
        length=gate_position,
        nx=n_upstream,
        B=canal_width,
        S0=bed_slope,
        n=manning_n,
        method='preissmann'
    )

    # 创建下游渠道段
    downstream_solver = CanalSolver(
        length=canal_length_total - gate_position,
        nx=n_downstream,
        B=canal_width,
        S0=bed_slope,
        n=manning_n,
        method='preissmann'
    )

    # 闸门
    gate = SluiceGate(
        width=canal_width,
        opening=1.5,
        Cd=0.6
    )

    print("系统配置:")
    print(f"  渠道总长度: {canal_length_total} m")
    print(f"  渠道宽度: {canal_width} m")
    print(f"  空间点数: {n_points_total}")
    print(f"  闸门位置: {gate_position} m")
    print(f"  闸门开度: {gate.opening} m")
    print(f"  底坡: {bed_slope*1000:.2f}‰")
    print(f"  曼宁糙率: {manning_n}")
    print(f"  求解器: Preissmann四点隐式格式")
    print()

    # === 步骤1: 计算初始稳态 ===
    print("=" * 80)
    print("步骤1: 计算初始稳态")
    print("-" * 80)

    Q_initial = 10.0  # 初始流量
    h_uniform = compute_steady_uniform_flow(Q_initial, canal_width, bed_slope, manning_n)

    print(f"  初始流量: {Q_initial} m³/s")
    print(f"  恒定均匀流水深: {h_uniform:.4f} m")

    # 设置初始状态
    upstream_solver.reset_with_steady_state(Q_initial)
    downstream_solver.reset_with_steady_state(Q_initial)

    # 运行到稳态
    print(f"\n运行到稳态...")
    dt_init = 1.0
    t_steady = 0
    max_steady_time = 1000.0

    for i in range(int(max_steady_time / dt_init)):
        # 获取闸门上下游水深
        h_gate_up = upstream_solver.h[-1]
        h_gate_down = downstream_solver.h[0]

        # 计算闸门流量
        Q_gate, _ = gate.calculate_discharge(h_gate_up, h_gate_down)

        # 更新上游段
        upstream_solver.step(dt_init, Q_initial, h_gate_up)

        # 更新下游段
        downstream_solver.step(dt_init, Q_gate, h_uniform)

        t_steady += dt_init

        # 检查收敛
        if i % 100 == 0:
            print(f"  t={t_steady:.0f}s: Q_gate={Q_gate:.3f} m³/s, "
                  f"h_up={h_gate_up:.3f}m, h_down={h_gate_down:.3f}m")

        # 简单收敛判断
        if i > 100 and abs(Q_gate - Q_initial) / Q_initial < 0.01:
            print(f"\n✓ 达到稳态 (t={t_steady:.0f}s)")
            break

    # 保存稳态
    h_steady_up = upstream_solver.h.copy()
    Q_steady_up = upstream_solver.Q.copy()
    h_steady_down = downstream_solver.h.copy()
    Q_steady_down = downstream_solver.Q.copy()

    print(f"\n稳态结果:")
    print(f"  闸前水深: {upstream_solver.h[-1]:.4f} m")
    print(f"  闸后水深: {downstream_solver.h[0]:.4f} m")
    print(f"  闸门流量: {Q_gate:.4f} m³/s")
    print()

    # 输出稳态图
    print("生成初始稳态图...")
    fig_steady, axes = plt.subplots(2, 1, figsize=(14, 10))

    x_full = np.concatenate([upstream_solver.x[:-1], downstream_solver.x + gate_position])
    h_full = np.concatenate([h_steady_up[:-1], h_steady_down])
    Q_full = np.concatenate([Q_steady_up[:-1], Q_steady_down])

    # 水深剖面
    ax = axes[0]
    ax.plot(x_full, h_full, 'b-', linewidth=2.5, label='Water Depth')
    ax.axvline(x=gate_position, color='r', linestyle='--', linewidth=2, alpha=0.7, label='Gate Position')
    ax.axhline(y=h_uniform, color='k', linestyle=':', alpha=0.5, label=f'Uniform Flow Depth ({h_uniform:.3f}m)')
    ax.set_xlabel('Distance (m)', fontsize=12)
    ax.set_ylabel('Water Depth (m)', fontsize=12)
    ax.set_title('Initial Steady State - Water Depth Profile', fontsize=14, fontweight='bold')
    ax.grid(True, alpha=0.3)
    ax.legend(fontsize=11)

    # 流量剖面
    ax = axes[1]
    ax.plot(x_full, Q_full, 'g-', linewidth=2.5, label='Flow Rate')
    ax.axvline(x=gate_position, color='r', linestyle='--', linewidth=2, alpha=0.7, label='Gate Position')
    ax.axhline(y=Q_initial, color='k', linestyle=':', alpha=0.5, label=f'Initial Flow ({Q_initial:.1f} m³/s)')
    ax.set_xlabel('Distance (m)', fontsize=12)
    ax.set_ylabel('Flow Rate (m³/s)', fontsize=12)
    ax.set_title('Initial Steady State - Flow Rate Distribution', fontsize=14, fontweight='bold')
    ax.grid(True, alpha=0.3)
    ax.legend(fontsize=11)

    plt.tight_layout()
    os.makedirs('reports/figures', exist_ok=True)
    steady_fig_path = 'reports/figures/example_01_sluice_gate_steady_state.png'
    plt.savefig(steady_fig_path, dpi=150, bbox_inches='tight')
    plt.close(fig_steady)
    print(f"  ✓ 稳态图已保存: {steady_fig_path}")
    print()

    # === 步骤2: 非恒定流仿真 (流量阶跃) ===
    print("=" * 80)
    print("步骤2: 非恒定流仿真 - 上游流量阶跃")
    print("-" * 80)

    Q_before_step = Q_initial
    Q_after_step = 12.0
    step_time = 500.0

    print(f"  阶跃前流量: {Q_before_step} m³/s")
    print(f"  阶跃后流量: {Q_after_step} m³/s")
    print(f"  阶跃时刻: {step_time} s")
    print()

    # 重新设置为稳态
    upstream_solver.h = h_steady_up.copy()
    upstream_solver.Q = Q_steady_up.copy()
    downstream_solver.h = h_steady_down.copy()
    downstream_solver.Q = Q_steady_down.copy()

    # 清空历史
    upstream_solver.clear_history()
    downstream_solver.clear_history()

    # 仿真参数
    dt = 2.0
    total_time = 2000.0
    n_steps = int(total_time / dt)

    # 监测点
    monitor_positions = {
        'Inlet': 1000.0,
        'Gate_Up': gate_position - 100.0,
        'Gate_Down': gate_position + 100.0,
        'Outlet': 9000.0,
    }

    # 数据存储
    time_series = []
    monitor_data = {name: {'h': [], 'Q': []} for name in monitor_positions}
    gate_upstream_h = []
    gate_downstream_h = []
    gate_flow = []

    print("开始非恒定流仿真...")
    for i in range(n_steps):
        t = i * dt

        # 上游边界：流量阶跃
        Q_up_bc = Q_before_step if t < step_time else Q_after_step

        # 获取闸门上下游水深
        h_gate_up = upstream_solver.h[-1]
        h_gate_down = downstream_solver.h[0]

        # 计算闸门流量
        Q_gate, f_type = gate.calculate_discharge(h_gate_up, h_gate_down)

        # 更新上游段
        upstream_solver.step(dt, Q_up_bc, h_gate_up)

        # 更新下游段
        downstream_solver.step(dt, Q_gate, h_uniform)

        # 记录数据
        time_series.append(t)
        gate_upstream_h.append(h_gate_up)
        gate_downstream_h.append(h_gate_down)
        gate_flow.append(Q_gate)

        # 监测点数据
        for name, pos in monitor_positions.items():
            if pos < gate_position:
                idx = int(pos / upstream_solver.dx)
                idx = min(idx, len(upstream_solver.h) - 1)
                monitor_data[name]['h'].append(upstream_solver.h[idx])
                monitor_data[name]['Q'].append(upstream_solver.Q[idx])
            else:
                idx = int((pos - gate_position) / downstream_solver.dx)
                idx = min(idx, len(downstream_solver.h) - 1)
                monitor_data[name]['h'].append(downstream_solver.h[idx])
                monitor_data[name]['Q'].append(downstream_solver.Q[idx])

        # 保存历史（用于动画）
        if i % 10 == 0:
            upstream_solver.save_state(t)
            downstream_solver.save_state(t)

        # 打印进度
        if i % 100 == 0 or abs(t - step_time) < dt:
            marker = " <-- STEP" if abs(t - step_time) < dt else ""
            print(f"  t={t:7.0f}s: Q_up={Q_up_bc:5.1f}, Q_gate={Q_gate:5.2f} m³/s, "
                  f"h_gate_up={h_gate_up:.2f}m, h_gate_down={h_gate_down:.2f}m{marker}")

    print()
    print(f"仿真完成！")
    print(f"  最终闸门流量: {gate_flow[-1]:.3f} m³/s (目标: {Q_after_step} m³/s)")
    print(f"  最终闸前水位: {gate_upstream_h[-1]:.3f} m (初始: {gate_upstream_h[0]:.3f} m)")
    print(f"  最终闸后水位: {gate_downstream_h[-1]:.3f} m (初始: {gate_downstream_h[0]:.3f} m)")
    print()

    # === 生成关键位置时间序列图 ===
    print("=" * 80)
    print("生成可视化")
    print("=" * 80)

    print("  生成关键位置时间序列图...")
    fig_key = plt.figure(figsize=(16, 10))

    # 2x2布局
    ax1 = plt.subplot(2, 2, 1)  # 流量 - 入口和闸前
    ax2 = plt.subplot(2, 2, 2)  # 流量 - 闸后和出口
    ax3 = plt.subplot(2, 2, 3)  # 水深 - 入口和闸前
    ax4 = plt.subplot(2, 2, 4)  # 水深 - 闸后和出口

    # 流量
    ax1.plot(time_series, monitor_data['Inlet']['Q'], 'b-', linewidth=2.5, label='Inlet')
    ax1.plot(time_series, monitor_data['Gate_Up']['Q'], 'r-', linewidth=2.5, label='Gate Upstream')
    ax1.axvline(x=step_time, color='k', linestyle='--', linewidth=1.5, alpha=0.5)
    ax1.axhline(y=Q_before_step, color='gray', linestyle=':', alpha=0.5)
    ax1.axhline(y=Q_after_step, color='gray', linestyle=':', alpha=0.5)
    ax1.set_xlabel('Time (s)', fontsize=12)
    ax1.set_ylabel('Flow Rate (m³/s)', fontsize=12)
    ax1.set_title('Upstream Flow Rate', fontsize=13, fontweight='bold')
    ax1.grid(True, alpha=0.3)
    ax1.legend(fontsize=11)

    ax2.plot(time_series, monitor_data['Gate_Down']['Q'], 'g-', linewidth=2.5, label='Gate Downstream')
    ax2.plot(time_series, monitor_data['Outlet']['Q'], 'm-', linewidth=2.5, label='Outlet')
    ax2.axvline(x=step_time, color='k', linestyle='--', linewidth=1.5, alpha=0.5)
    ax2.axhline(y=Q_before_step, color='gray', linestyle=':', alpha=0.5)
    ax2.axhline(y=Q_after_step, color='gray', linestyle=':', alpha=0.5)
    ax2.set_xlabel('Time (s)', fontsize=12)
    ax2.set_ylabel('Flow Rate (m³/s)', fontsize=12)
    ax2.set_title('Downstream Flow Rate', fontsize=13, fontweight='bold')
    ax2.grid(True, alpha=0.3)
    ax2.legend(fontsize=11)

    # 水深
    ax3.plot(time_series, monitor_data['Inlet']['h'], 'b-', linewidth=2.5, label='Inlet')
    ax3.plot(time_series, monitor_data['Gate_Up']['h'], 'r-', linewidth=2.5, label='Gate Upstream')
    ax3.axvline(x=step_time, color='k', linestyle='--', linewidth=1.5, alpha=0.5)
    ax3.set_xlabel('Time (s)', fontsize=12)
    ax3.set_ylabel('Water Depth (m)', fontsize=12)
    ax3.set_title('Upstream Water Depth', fontsize=13, fontweight='bold')
    ax3.grid(True, alpha=0.3)
    ax3.legend(fontsize=11)

    ax4.plot(time_series, monitor_data['Gate_Down']['h'], 'g-', linewidth=2.5, label='Gate Downstream')
    ax4.plot(time_series, monitor_data['Outlet']['h'], 'm-', linewidth=2.5, label='Outlet')
    ax4.axvline(x=step_time, color='k', linestyle='--', linewidth=1.5, alpha=0.5)
    ax4.set_xlabel('Time (s)', fontsize=12)
    ax4.set_ylabel('Water Depth (m)', fontsize=12)
    ax4.set_title('Downstream Water Depth', fontsize=13, fontweight='bold')
    ax4.grid(True, alpha=0.3)
    ax4.legend(fontsize=11)

    plt.tight_layout()
    key_fig_path = 'reports/figures/example_01_sluice_gate_key_locations.png'
    plt.savefig(key_fig_path, dpi=150, bbox_inches='tight')
    plt.close(fig_key)
    print(f"  ✓ 关键位置时间序列图")

    print()
    print("=" * 80)
    print("分析完成！")
    print("=" * 80)

    print(f"\n生成的文件:")
    print(f"  - {steady_fig_path}")
    print(f"  - {key_fig_path}")

    print("\n" + "=" * 80)


if __name__ == "__main__":
    run_sluice_gate_dynamics()
