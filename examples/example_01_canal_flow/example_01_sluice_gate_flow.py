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

    # 闸门（增大开度确保恒定流时流量能够守恒）
    gate = SluiceGate(
        width=canal_width,
        opening=3.5,  # 进一步增大开度以减少流量损失
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
    print("步骤1: 计算初始稳态（恒定流）")
    print("-" * 80)

    Q_initial = 10.0  # 初始流量
    h_uniform = compute_steady_uniform_flow(Q_initial, canal_width, bed_slope, manning_n)

    print(f"  初始流量: {Q_initial} m³/s")
    print(f"  恒定均匀流水深: {h_uniform:.4f} m")
    print()

    # 设置初始状态
    upstream_solver.reset_with_steady_state(Q_initial)
    downstream_solver.reset_with_steady_state(Q_initial)

    # 改进策略：降低下游边界水位，确保闸门能够通过目标流量
    h_downstream_bc = h_uniform - 0.2  # 降低下游边界水位

    # 运行到稳态
    print(f"运行到稳态...")
    print(f"  下游边界水位: {h_downstream_bc:.4f} m")
    print()

    dt_init = 1.0
    t_steady = 0
    max_steady_time = 2000.0

    for i in range(int(max_steady_time / dt_init)):
        # 获取闸门上下游水深
        h_gate_up = upstream_solver.h[-1]
        h_gate_down = downstream_solver.h[0]

        # 计算闸门流量
        Q_gate, _ = gate.calculate_discharge(h_gate_up, h_gate_down)

        # 更新上游段（上游边界：流量；下游边界：使用均匀流水深而非固定闸门水深）
        # 这样可以让上游段的流量更自由地通过闸门
        upstream_solver.step(dt_init, Q_initial, h_uniform)

        # 更新下游段（上游边界：闸门流量；下游边界：固定水位）
        downstream_solver.step(dt_init, Q_gate, h_downstream_bc)

        t_steady += dt_init

        # 检查收敛
        if i % 100 == 0:
            Q_up_avg = np.mean(upstream_solver.Q)
            Q_down_avg = np.mean(downstream_solver.Q)
            print(f"  t={t_steady:5.0f}s: Q_gate={Q_gate:6.3f} m³/s, "
                  f"Q_up_avg={Q_up_avg:6.3f}, Q_down_avg={Q_down_avg:6.3f}, "
                  f"h_up={h_gate_up:.3f}m, h_down={h_gate_down:.3f}m")

        # 改进的收敛判断：闸门流量接近目标流量
        if i > 200:
            Q_up_avg = np.mean(upstream_solver.Q[1:-1])
            Q_down_avg = np.mean(downstream_solver.Q[1:-1])

            if (abs(Q_gate - Q_initial) / Q_initial < 0.02 and
                abs(Q_up_avg - Q_initial) / Q_initial < 0.05 and
                abs(Q_down_avg - Q_initial) / Q_initial < 0.05):
                print(f"\n✓ 达到恒定流稳态 (t={t_steady:.0f}s)")
                print(f"  上游平均流量: {Q_up_avg:.3f} m³/s")
                print(f"  闸门流量: {Q_gate:.3f} m³/s")
                print(f"  下游平均流量: {Q_down_avg:.3f} m³/s")
                print(f"  流量相对误差: {abs(Q_gate-Q_initial)/Q_initial*100:.1f}%")
                break

    # 保存稳态
    h_steady_up = upstream_solver.h.copy()
    Q_steady_up = upstream_solver.Q.copy()
    h_steady_down = downstream_solver.h.copy()
    Q_steady_down = downstream_solver.Q.copy()

    print(f"\n稳态结果:")
    print(f"  闸前水深: {upstream_solver.h[-1]:.4f} m")
    print(f"  闸后水深: {downstream_solver.h[0]:.4f} m")
    print(f"  水位差: {upstream_solver.h[-1] - downstream_solver.h[0]:.4f} m")
    print(f"  闸门流量: {Q_gate:.4f} m³/s")
    print()

    # === 生成初始稳态纵剖面图（含渠底高程） ===
    print("生成初始稳态纵剖面图（含渠底高程）...")

    fig_steady = plt.figure(figsize=(16, 10))

    # 拼接全渠道数据
    x_full = np.concatenate([upstream_solver.x[:-1], downstream_solver.x + gate_position])
    h_full = np.concatenate([h_steady_up[:-1], h_steady_down])
    Q_full = np.concatenate([Q_steady_up[:-1], Q_steady_down])

    # 计算渠底高程（以下游为基准0）
    z_bed = (canal_length_total - x_full) * bed_slope
    z_surface = z_bed + h_full  # 水面高程

    # === 子图1: 纵剖面（水面+渠底） ===
    ax1 = plt.subplot(3, 1, 1)
    ax1.fill_between(x_full, z_bed, z_surface, color='cyan', alpha=0.5, label='Water')
    ax1.plot(x_full, z_surface, 'b-', linewidth=2.5, label='Water Surface')
    ax1.plot(x_full, z_bed, 'k-', linewidth=2, label='Bed Level')
    ax1.axvline(x=gate_position, color='r', linestyle='--', linewidth=2.5, alpha=0.7, label='Gate')
    ax1.set_xlabel('Distance (m)', fontsize=12)
    ax1.set_ylabel('Elevation (m)', fontsize=12)
    ax1.set_title('Initial Steady State - Longitudinal Profile (Water Surface + Bed)', fontsize=14, fontweight='bold')
    ax1.grid(True, alpha=0.3)
    ax1.legend(fontsize=11, loc='upper right')
    ax1.set_xlim([0, canal_length_total])

    # === 子图2: 水深剖面 ===
    ax2 = plt.subplot(3, 1, 2)
    ax2.plot(x_full, h_full, 'b-', linewidth=2.5, label='Water Depth')
    ax2.axvline(x=gate_position, color='r', linestyle='--', linewidth=2, alpha=0.7, label='Gate Position')
    ax2.axhline(y=h_uniform, color='k', linestyle=':', alpha=0.5, label=f'Uniform Depth ({h_uniform:.3f}m)')
    ax2.set_xlabel('Distance (m)', fontsize=12)
    ax2.set_ylabel('Water Depth (m)', fontsize=12)
    ax2.set_title('Water Depth Distribution', fontsize=14, fontweight='bold')
    ax2.grid(True, alpha=0.3)
    ax2.legend(fontsize=11)
    ax2.set_xlim([0, canal_length_total])

    # === 子图3: 流量剖面 ===
    ax3 = plt.subplot(3, 1, 3)
    ax3.plot(x_full, Q_full, 'g-', linewidth=2.5, label='Flow Rate')
    ax3.axvline(x=gate_position, color='r', linestyle='--', linewidth=2, alpha=0.7, label='Gate Position')
    ax3.axhline(y=Q_initial, color='k', linestyle=':', alpha=0.5, label=f'Target Flow ({Q_initial:.1f} m³/s)')
    ax3.set_xlabel('Distance (m)', fontsize=12)
    ax3.set_ylabel('Flow Rate (m³/s)', fontsize=12)
    ax3.set_title('Flow Rate Distribution (Should be constant for steady uniform flow)', fontsize=14, fontweight='bold')
    ax3.grid(True, alpha=0.3)
    ax3.legend(fontsize=11)
    ax3.set_xlim([0, canal_length_total])

    plt.tight_layout()
    os.makedirs('reports/figures', exist_ok=True)
    steady_fig_path = 'reports/figures/example_01_sluice_gate_steady_state.png'
    plt.savefig(steady_fig_path, dpi=150, bbox_inches='tight')
    plt.close(fig_steady)
    print(f"  ✓ 稳态纵剖面图已保存: {steady_fig_path}")
    print()

    # === 步骤2: 非恒定流仿真 (流量阶跃) ===
    print("=" * 80)
    print("步骤2: 非恒定流仿真 - 上游流量阶跃")
    print("-" * 80)

    Q_before_step = Q_initial
    Q_after_step = 15.0  # 增大阶跃幅度以更明显地展示动态效果
    step_time = 300.0  # 提前阶跃时间

    print(f"  阶跃前流量: {Q_before_step} m³/s")
    print(f"  阶跃后流量: {Q_after_step} m³/s")
    print(f"  阶跃时刻: {step_time} s")
    print(f"  阶跃幅度: +{Q_after_step - Q_before_step} m³/s (+{(Q_after_step/Q_before_step-1)*100:.0f}%)")
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
    total_time = 1500.0  # 缩短总时间
    n_steps = int(total_time / dt)

    # 监测点
    monitor_positions = {
        'Inlet': 500.0,
        'Gate_Up': gate_position - 100.0,
        'Gate_Down': gate_position + 100.0,
        'Outlet': 9500.0,
    }

    # 数据存储
    time_series = []
    monitor_data = {name: {'h': [], 'Q': []} for name in monitor_positions}
    gate_upstream_h = []
    gate_downstream_h = []
    gate_flow = []

    # 用于GIF动画的完整状态历史
    snapshot_interval = 20  # 每20步保存一次
    h_snapshots = []
    Q_snapshots = []
    t_snapshots = []

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

        # 更新上游段（使用均匀流水深作为参考边界）
        upstream_solver.step(dt, Q_up_bc, h_uniform)

        # 更新下游段
        downstream_solver.step(dt, Q_gate, h_downstream_bc)

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

        # 保存快照用于GIF
        if i % snapshot_interval == 0:
            h_full_now = np.concatenate([upstream_solver.h[:-1], downstream_solver.h])
            Q_full_now = np.concatenate([upstream_solver.Q[:-1], downstream_solver.Q])
            h_snapshots.append(h_full_now)
            Q_snapshots.append(Q_full_now)
            t_snapshots.append(t)

        # 打印进度
        if i % 50 == 0 or abs(t - step_time) < dt:
            marker = " <-- STEP" if abs(t - step_time) < dt else ""
            print(f"  t={t:7.0f}s: Q_up={Q_up_bc:5.1f}, Q_gate={Q_gate:6.2f} m³/s, "
                  f"h_gate_up={h_gate_up:.3f}m, h_gate_down={h_gate_down:.3f}m{marker}")

    print()
    print(f"仿真完成！")
    print(f"  最终闸门流量: {gate_flow[-1]:.3f} m³/s (阶跃后目标: {Q_after_step} m³/s)")
    print(f"  最终闸前水位: {gate_upstream_h[-1]:.3f} m (初始: {gate_upstream_h[0]:.3f} m, 变化: +{(gate_upstream_h[-1]-gate_upstream_h[0])*100:.1f} cm)")
    print(f"  最终闸后水位: {gate_downstream_h[-1]:.3f} m (初始: {gate_downstream_h[0]:.3f} m, 变化: {(gate_downstream_h[-1]-gate_downstream_h[0])*100:+.1f} cm)")
    print()

    # === 生成关键位置时间序列图 ===
    print("=" * 80)
    print("生成可视化")
    print("=" * 80)

    print("  1. 生成关键位置时间序列图...")
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
    print(f"     ✓ 已保存: {key_fig_path}")

    # === 生成GIF动画 ===
    print("  2. 生成纵剖面动态GIF动画...")

    fig_anim = plt.figure(figsize=(16, 10))

    def animate(frame_idx):
        plt.clf()

        h_frame = h_snapshots[frame_idx]
        Q_frame = Q_snapshots[frame_idx]
        t_frame = t_snapshots[frame_idx]

        # 计算水面高程
        z_surface_frame = z_bed + h_frame

        # 子图1: 纵剖面
        ax1 = plt.subplot(3, 1, 1)
        ax1.fill_between(x_full, z_bed, z_surface_frame, color='cyan', alpha=0.5)
        ax1.plot(x_full, z_surface_frame, 'b-', linewidth=2.5, label='Water Surface')
        ax1.plot(x_full, z_bed, 'k-', linewidth=2, label='Bed Level')
        ax1.axvline(x=gate_position, color='r', linestyle='--', linewidth=2.5, alpha=0.7, label='Gate')
        ax1.set_xlabel('Distance (m)', fontsize=12)
        ax1.set_ylabel('Elevation (m)', fontsize=12)
        ax1.set_title(f'Longitudinal Profile - t = {t_frame:.0f}s', fontsize=14, fontweight='bold')
        ax1.grid(True, alpha=0.3)
        ax1.legend(fontsize=10, loc='upper right')
        ax1.set_xlim([0, canal_length_total])
        ax1.set_ylim([np.min(z_bed)-0.2, np.max(z_surface_frame)+0.3])

        # 子图2: 水深
        ax2 = plt.subplot(3, 1, 2)
        ax2.plot(x_full, h_frame, 'b-', linewidth=2.5)
        ax2.axvline(x=gate_position, color='r', linestyle='--', linewidth=2, alpha=0.7)
        ax2.axhline(y=h_uniform, color='k', linestyle=':', alpha=0.5)
        ax2.set_xlabel('Distance (m)', fontsize=12)
        ax2.set_ylabel('Water Depth (m)', fontsize=12)
        ax2.set_title('Water Depth Distribution', fontsize=13, fontweight='bold')
        ax2.grid(True, alpha=0.3)
        ax2.set_xlim([0, canal_length_total])
        ax2.set_ylim([h_uniform-0.1, np.max([np.max(h_snapshots), h_uniform+0.3])])

        # 子图3: 流量
        ax3 = plt.subplot(3, 1, 3)
        ax3.plot(x_full, Q_frame, 'g-', linewidth=2.5)
        ax3.axvline(x=gate_position, color='r', linestyle='--', linewidth=2, alpha=0.7)
        ax3.axhline(y=Q_initial, color='gray', linestyle=':', alpha=0.5, label=f'Initial: {Q_initial}')
        ax3.axhline(y=Q_after_step, color='orange', linestyle=':', alpha=0.5, label=f'Target: {Q_after_step}')
        ax3.set_xlabel('Distance (m)', fontsize=12)
        ax3.set_ylabel('Flow Rate (m³/s)', fontsize=12)
        ax3.set_title('Flow Rate Distribution', fontsize=13, fontweight='bold')
        ax3.grid(True, alpha=0.3)
        ax3.legend(fontsize=10)
        ax3.set_xlim([0, canal_length_total])
        ax3.set_ylim([Q_initial-2, Q_after_step+3])

        plt.tight_layout()

    # 创建动画
    n_frames = len(t_snapshots)
    anim = animation.FuncAnimation(fig_anim, animate, frames=n_frames, interval=100, repeat=True)

    # 保存GIF
    gif_path = 'reports/figures/example_01_sluice_gate_dynamics.gif'
    anim.save(gif_path, writer='pillow', fps=10, dpi=80)
    plt.close(fig_anim)
    print(f"     ✓ 已保存: {gif_path}")
    print(f"        (共 {n_frames} 帧, {total_time:.0f}s 模拟时长)")

    print()
    print("=" * 80)
    print("分析完成！")
    print("=" * 80)

    print(f"\n生成的文件:")
    print(f"  1. 初始稳态纵剖面图（含渠底）: {steady_fig_path}")
    print(f"  2. 关键位置时间序列图: {key_fig_path}")
    print(f"  3. 纵剖面动态GIF: {gif_path}")

    print("\n" + "=" * 80)


if __name__ == "__main__":
    run_sluice_gate_dynamics()
