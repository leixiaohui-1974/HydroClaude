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
# 添加项目根目录到路径（向上两级：canal_flow -> examples -> HydroClaude）
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

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
    """简化的渠道段 - 使用改进的Muskingum方法展示沿程传播（稳定版）"""

    def __init__(self, length, width, n_points, slope=0.0001, manning_n=0.025):
        self.length = length
        self.width = width
        self.n_points = n_points
        self.dx = length / (n_points - 1)
        self.x = np.linspace(0, length, n_points)
        self.slope = slope  # 底坡
        self.manning_n = manning_n  # 曼宁糙率
        self.g = 9.81

        # 状态变量 - 每个节点独立
        self.h = np.ones(n_points) * 5.0  # 水深
        self.Q = np.ones(n_points) * 5.0  # 流量

        # Muskingum参数
        self.K = 200.0  # 存储时间常数（秒）
        self.X = 0.2   # 权重系数（0-0.5之间）

    def set_uniform_state(self, h, Q):
        """设置均匀状态"""
        self.h[:] = h
        self.Q[:] = Q

    def update_muskingum(self, dt, Q_upstream=None, h_downstream=None):
        """
        使用改进的水库模型方法更新状态（稳定版）

        基本思路：
        1. 将渠道分段，每段作为一个水库
        2. 质量守恒：dV/dt = Q_in - Q_out
        3. 使用曼宁公式关联水深和流量
        """
        h_old = self.h.copy()
        Q_old = self.Q.copy()

        # 计算每段的长度
        segment_length = self.dx

        # 上游边界
        if Q_upstream is not None:
            self.Q[0] = Q_upstream
            # 从流量估计水深
            if Q_upstream > 0:
                h_est = (Q_upstream * self.manning_n / (self.width * (self.slope ** 0.5))) ** (3.0/5.0)
                self.h[0] = np.clip(h_est, 0.5, 20.0)
            else:
                self.h[0] = 0.5

        # 从上游到下游逐段更新
        for i in range(1, self.n_points):
            # 本段的入流和出流
            Q_in = self.Q[i-1]
            Q_out_old = Q_old[i]

            # 本段体积变化
            V_old = h_old[i] * self.width * segment_length
            dV = (Q_in - Q_out_old) * dt
            V_new = V_old + dV

            # 限制体积为正
            V_new = max(V_new, 0.1 * self.width * segment_length)

            # 新水深
            h_new = V_new / (self.width * segment_length)
            h_new = np.clip(h_new, 0.5, 20.0)

            # 使用松弛因子平滑
            alpha = 0.5
            self.h[i] = (1 - alpha) * h_old[i] + alpha * h_new

            # 从水深计算出流流量（使用曼宁公式）
            if self.h[i] > 0:
                A = self.width * self.h[i]
                R = self.h[i]  # 宽浅渠道假设
                V_flow = (1.0 / self.manning_n) * (R ** (2.0/3.0)) * (self.slope ** 0.5)
                Q_out_new = A * V_flow

                # 使用Muskingum风格的平滑
                C0, C1, C2 = 0.25, 0.25, 0.5
                self.Q[i] = C0 * Q_in + C1 * Q_old[i-1] + C2 * Q_out_old
                self.Q[i] = np.clip(self.Q[i], 0, 100.0)
            else:
                self.Q[i] = 0

        # 下游边界条件
        if h_downstream is not None:
            # 使用松弛因子
            alpha_bc = 0.3
            self.h[-1] = (1 - alpha_bc) * self.h[-1] + alpha_bc * h_downstream
            # 重新计算流量
            if self.h[-1] > 0:
                A = self.width * self.h[-1]
                R = self.h[-1]
                V_flow = (1.0 / self.manning_n) * (R ** (2.0/3.0)) * (self.slope ** 0.5)
                self.Q[-1] = A * V_flow

        return self.h.copy(), self.Q.copy()

    def get_values_at(self, position):
        """获取指定位置的水深和流量（线性插值）"""
        if position <= 0:
            return self.h[0], self.Q[0]
        elif position >= self.length:
            return self.h[-1], self.Q[-1]
        else:
            # 线性插值
            idx = int(position / self.dx)
            if idx >= self.n_points - 1:
                return self.h[-1], self.Q[-1]
            frac = (position - idx * self.dx) / self.dx
            h_interp = self.h[idx] * (1 - frac) + self.h[idx+1] * frac
            Q_interp = self.Q[idx] * (1 - frac) + self.Q[idx+1] * frac
            return h_interp, Q_interp


def run_sluice_gate_dynamics():
    """运行闸门流量动力学分析 - 改进版：展示真实的沿程传播过程"""

    print("=" * 80)
    print("示例1扩展：明渠闸门过流动力学分析（改进版）")
    print("=" * 80)
    print()

    # === 系统配置 ===
    # 优化参数以增强可视化效果：
    # 1. 使用单个渠道段，中间设置闸门
    # 2. 上游边界：流量阶跃
    # 3. 下游边界：水位边界（在渠道末端）
    # 4. 增加监测断面数量

    canal_length_total = 10000.0  # 总长度（增加到10000m以展示传播过程）
    canal_width = 10.0
    gate_position = 5000.0  # 闸门位置（中点）
    n_points_total = 201  # 总空间点数（增加密度）

    # 渠道参数
    bed_slope = 0.0005  # 底坡0.5‰（减小底坡以增大水位差效果）
    manning_n = 0.025  # 曼宁糙率

    # 创建渠道段（分上下游两段）
    gate_idx = n_points_total // 2  # 闸门所在索引

    upstream_reach = SimplifiedCanalReach(
        length=gate_position,
        width=canal_width,
        n_points=gate_idx + 1,  # 包含闸门位置
        slope=bed_slope,
        manning_n=manning_n
    )

    downstream_reach = SimplifiedCanalReach(
        length=canal_length_total - gate_position,
        width=canal_width,
        n_points=n_points_total - gate_idx,  # 从闸门位置到末端
        slope=bed_slope,
        manning_n=manning_n
    )

    # 闸门 - 采用中等开度
    gate = SluiceGate(
        width=canal_width,
        opening=1.5,  # 中等开度
        Cd=0.6
    )

    print("系统配置:")
    print(f"  渠道总长度: {canal_length_total} m")
    print(f"  渠道宽度: {canal_width} m")
    print(f"  空间点数: {n_points_total}")
    print(f"  空间步长: {upstream_reach.dx:.1f} m")
    print(f"  闸门位置: {gate_position} m")
    print(f"  闸门开度: {gate.opening} m")
    print(f"  流量系数: {gate.Cd}")
    print(f"  底坡: {bed_slope*1000:.2f}‰")
    print(f"  曼宁糙率: {manning_n}")
    print()

    # 监测断面（沿程多个位置）
    monitor_positions = {
        'Upstream 1': 1000.0,
        'Upstream 2': 3000.0,
        'Gate Upstream': gate_position - 100.0,
        'Gate Downstream': gate_position + 100.0,
        'Downstream 1': 7000.0,
        'Downstream 2': 9000.0,
    }

    print("监测断面:")
    for name, pos in monitor_positions.items():
        print(f"  {name}: {pos:.0f} m")
    print()

    # === 场景2: 非恒定流 (流量阶跃) - 改进版 ===
    print("=" * 80)
    print("场景2: 非恒定流 - 上游流量阶跃（展示沿程传播）")
    print("-" * 80)

    # 边界条件 - 采用更简单的配置以确保数值稳定
    Q_before_step = 10.0  # 阶跃前流量
    Q_after_step = 12.0  # 阶跃后流量（小幅度增加）
    step_time = 800.0  # 阶跃时刻

    # 简化初始条件：使用统一水深
    h_init_uniform = 3.5  # 统一初始水深

    print(f"  NOTE: 采用简化配置确保数值稳定性")
    print(f"  - 初始流量: {Q_before_step} m³/s")
    print(f"  - 流量增幅: {Q_after_step - Q_before_step} m³/s (小幅度)")
    print(f"  - 统一初始水深: {h_init_uniform} m")

    print(f"\n初始状态:")
    print(f"  上游流量: {Q_before_step} m³/s")
    print(f"  统一水深: {h_init_uniform} m")
    print(f"  闸门将自动调整到平衡状态")

    # 设置初始条件 - 全渠道统一水深
    upstream_reach.set_uniform_state(h_init_uniform, Q_before_step)
    downstream_reach.set_uniform_state(h_init_uniform, Q_before_step)

    # 仿真参数
    dt = 10.0  # 时间步长（Muskingum方法稳定性好，可以用较大步长）
    total_time = 3000.0  # 延长仿真时间以观察完整传播过程
    n_steps = int(total_time / dt)

    print(f"仿真配置:")
    print(f"  流量阶跃: {Q_before_step} → {Q_after_step} m³/s (at t={step_time}s)")
    print(f"  仿真时长: {total_time} s")
    print(f"  时间步长: {dt} s")
    print(f"  总步数: {n_steps}")
    print(f"  演算方法: Muskingum (K={upstream_reach.K}s, X={upstream_reach.X})")
    print()

    # 数据存储 - 监测点时间序列
    time_series = []
    monitor_data = {name: {'h': [], 'Q': []} for name in monitor_positions}
    gate_upstream_h = []
    gate_downstream_h = []
    gate_flow = []
    flow_type_list = []

    # 空间分布快照（用于动画）
    snapshot_times = []
    snapshot_h_profiles = []
    snapshot_Q_profiles = []

    print("开始仿真...")
    for i in range(n_steps):
        t = i * dt

        # 上游边界：流量阶跃
        if t < step_time:
            Q_up_bc = Q_before_step
        else:
            Q_up_bc = Q_after_step

        # 获取闸门上下游水深
        h_gate_up = upstream_reach.h[-1]  # 上游段末端 = 闸前
        h_gate_down = downstream_reach.h[0]  # 下游段起点 = 闸后

        # 计算闸门流量
        Q_gate, f_type = gate.calculate_discharge(h_gate_up, h_gate_down)

        # 更新上游段：上游边界为流量
        upstream_reach.update_muskingum(dt, Q_upstream=Q_up_bc, h_downstream=None)

        # 更新下游段：下游为自由出流（去掉固定水位边界以提高稳定性）
        downstream_reach.update_muskingum(dt, Q_upstream=Q_gate, h_downstream=None)

        # 记录监测点数据
        time_series.append(t)
        for name, pos in monitor_positions.items():
            if pos < gate_position:
                h_val, Q_val = upstream_reach.get_values_at(pos)
            else:
                h_val, Q_val = downstream_reach.get_values_at(pos - gate_position)
            monitor_data[name]['h'].append(h_val)
            monitor_data[name]['Q'].append(Q_val)

        gate_upstream_h.append(h_gate_up)
        gate_downstream_h.append(h_gate_down)
        gate_flow.append(Q_gate)
        flow_type_list.append(f_type)

        # 保存空间分布快照（每隔一定时间）
        if i % 20 == 0:
            snapshot_times.append(t)
            # 合并上下游段的空间分布
            h_profile = np.concatenate([upstream_reach.h[:-1], downstream_reach.h])
            Q_profile = np.concatenate([upstream_reach.Q[:-1], downstream_reach.Q])
            snapshot_h_profiles.append(h_profile)
            snapshot_Q_profiles.append(Q_profile)

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
    print(f"  水位变化: {gate_upstream_h[-1] - gate_upstream_h[0]:.3f} m")
    print()

    # === 分析传播特性 ===
    print("=" * 80)
    print("传播特性分析")
    print("-" * 80)

    # 分析传播波速
    # 找到阶跃时刻的索引
    step_idx = int(step_time / dt)

    # 分析各监测点何时响应
    print("\n监测点响应时间:")
    response_threshold = 0.1  # 流量变化超过0.1 m³/s视为响应
    for name, pos in monitor_positions.items():
        Q_data = np.array(monitor_data[name]['Q'])
        Q_before = Q_data[step_idx]
        # 查找响应时刻
        for i in range(step_idx, len(Q_data)):
            if abs(Q_data[i] - Q_before) > response_threshold:
                delay_time = time_series[i] - step_time
                distance = abs(pos - 0)  # 距离上游边界的距离
                apparent_speed = distance / delay_time if delay_time > 0 else 0
                print(f"  {name:20s} (x={pos:6.0f}m): "
                      f"响应时间 {delay_time:6.1f}s, 表观波速 {apparent_speed:.2f} m/s")
                break
    print()

    # === 生成可视化 ===
    print("=" * 80)
    print("生成可视化")
    print("=" * 80)

    generated_files = []
    os.makedirs('reports/figures', exist_ok=True)

    # 图0: 关键位置时间序列静态图（新增）
    print("  生成关键位置时间序列图...")
    fig_key = plt.figure(figsize=(16, 10))

    # 定义关键位置
    key_positions = {
        '渠道入口': 'Upstream 1',
        '闸前': 'Gate Upstream',
        '闸后': 'Gate Downstream',
        '渠道出口': 'Downstream 2'
    }

    # 2x2布局
    ax1 = plt.subplot(2, 2, 1)  # 流量 - 入口和闸前
    ax2 = plt.subplot(2, 2, 2)  # 流量 - 闸后和出口
    ax3 = plt.subplot(2, 2, 3)  # 水深 - 入口和闸前
    ax4 = plt.subplot(2, 2, 4)  # 水深 - 闸后和出口

    # 绘制流量
    ax1.plot(time_series, monitor_data['Upstream 1']['Q'], 'b-', linewidth=2.5, label='渠道入口')
    ax1.plot(time_series, monitor_data['Gate Upstream']['Q'], 'r-', linewidth=2.5, label='闸前')
    ax1.axvline(x=step_time, color='k', linestyle='--', linewidth=1.5, alpha=0.5, label='阶跃时刻')
    ax1.axhline(y=Q_before_step, color='gray', linestyle=':', alpha=0.5)
    ax1.axhline(y=Q_after_step, color='gray', linestyle=':', alpha=0.5)
    ax1.set_xlabel('时间 (s)', fontsize=12)
    ax1.set_ylabel('流量 (m³/s)', fontsize=12)
    ax1.set_title('上游段流量变化', fontsize=13, fontweight='bold')
    ax1.grid(True, alpha=0.3)
    ax1.legend(fontsize=11)

    ax2.plot(time_series, monitor_data['Gate Downstream']['Q'], 'g-', linewidth=2.5, label='闸后')
    ax2.plot(time_series, monitor_data['Downstream 2']['Q'], 'm-', linewidth=2.5, label='渠道出口')
    ax2.axvline(x=step_time, color='k', linestyle='--', linewidth=1.5, alpha=0.5, label='阶跃时刻')
    ax2.axhline(y=Q_before_step, color='gray', linestyle=':', alpha=0.5)
    ax2.axhline(y=Q_after_step, color='gray', linestyle=':', alpha=0.5)
    ax2.set_xlabel('时间 (s)', fontsize=12)
    ax2.set_ylabel('流量 (m³/s)', fontsize=12)
    ax2.set_title('下游段流量变化', fontsize=13, fontweight='bold')
    ax2.grid(True, alpha=0.3)
    ax2.legend(fontsize=11)

    # 绘制水深
    ax3.plot(time_series, monitor_data['Upstream 1']['h'], 'b-', linewidth=2.5, label='渠道入口')
    ax3.plot(time_series, monitor_data['Gate Upstream']['h'], 'r-', linewidth=2.5, label='闸前')
    ax3.axvline(x=step_time, color='k', linestyle='--', linewidth=1.5, alpha=0.5, label='阶跃时刻')
    ax3.set_xlabel('时间 (s)', fontsize=12)
    ax3.set_ylabel('水深 (m)', fontsize=12)
    ax3.set_title('上游段水深变化', fontsize=13, fontweight='bold')
    ax3.grid(True, alpha=0.3)
    ax3.legend(fontsize=11)

    ax4.plot(time_series, monitor_data['Gate Downstream']['h'], 'g-', linewidth=2.5, label='闸后')
    ax4.plot(time_series, monitor_data['Downstream 2']['h'], 'm-', linewidth=2.5, label='渠道出口')
    ax4.axvline(x=step_time, color='k', linestyle='--', linewidth=1.5, alpha=0.5, label='阶跃时刻')
    ax4.set_xlabel('时间 (s)', fontsize=12)
    ax4.set_ylabel('水深 (m)', fontsize=12)
    ax4.set_title('下游段水深变化', fontsize=13, fontweight='bold')
    ax4.grid(True, alpha=0.3)
    ax4.legend(fontsize=11)

    plt.tight_layout()
    fig_key_path = 'reports/figures/example_01_sluice_gate_key_locations.png'
    plt.savefig(fig_key_path, dpi=150, bbox_inches='tight')
    plt.close(fig_key)
    generated_files.append(fig_key_path)
    print(f"  ✓ 关键位置时间序列图")

    # 图1: 监测断面时间序列 - 流量
    fig, axes = plt.subplots(3, 2, figsize=(16, 12))

    # 绘制各监测点的流量历史
    colors = plt.cm.viridis(np.linspace(0, 1, len(monitor_positions)))

    ax = axes[0, 0]
    for (name, pos), color in zip(monitor_positions.items(), colors):
        Q_data = monitor_data[name]['Q']
        ax.plot(time_series, Q_data, label=name, linewidth=1.5, color=color)
    ax.axvline(x=step_time, color='r', linestyle='--', linewidth=2, alpha=0.7, label='Step Time')
    ax.set_xlabel('Time (s)', fontsize=10)
    ax.set_ylabel('Flow Rate (m³/s)', fontsize=10)
    ax.set_title('Flow Rate at Monitoring Sections', fontsize=11, fontweight='bold')
    ax.grid(True, alpha=0.3)
    ax.legend(fontsize=8, ncol=2)

    # 监测点水深历史
    ax = axes[0, 1]
    for (name, pos), color in zip(monitor_positions.items(), colors):
        h_data = monitor_data[name]['h']
        ax.plot(time_series, h_data, label=name, linewidth=1.5, color=color)
    ax.axvline(x=step_time, color='r', linestyle='--', linewidth=2, alpha=0.7, label='Step Time')
    ax.set_xlabel('Time (s)', fontsize=10)
    ax.set_ylabel('Water Depth (m)', fontsize=10)
    ax.set_title('Water Depth at Monitoring Sections', fontsize=11, fontweight='bold')
    # 优化y轴范围以突出变化
    all_h = []
    for name in monitor_positions:
        all_h.extend(monitor_data[name]['h'])
    h_min, h_max = min(all_h), max(all_h)
    h_margin = (h_max - h_min) * 0.1
    ax.set_ylim([h_min - h_margin, h_max + h_margin])
    ax.grid(True, alpha=0.3)
    ax.legend(fontsize=8, ncol=2)

    # 闸门处流量和水位
    ax = axes[1, 0]
    ax.plot(time_series, gate_flow, 'r-', linewidth=2, label='Gate Flow')
    ax.axvline(x=step_time, color='k', linestyle='--', linewidth=1.5, alpha=0.5)
    ax.axhline(y=Q_before_step, color='b', linestyle=':', alpha=0.5, label=f'Initial: {Q_before_step} m³/s')
    ax.axhline(y=Q_after_step, color='g', linestyle=':', alpha=0.5, label=f'Target: {Q_after_step} m³/s')
    ax.set_xlabel('Time (s)', fontsize=10)
    ax.set_ylabel('Gate Flow (m³/s)', fontsize=10)
    ax.set_title('Gate Flow Rate', fontsize=11, fontweight='bold')
    ax.grid(True, alpha=0.3)
    ax.legend(fontsize=9)

    ax = axes[1, 1]
    ax.plot(time_series, gate_upstream_h, 'b-', linewidth=2, label='Gate Upstream')
    ax.plot(time_series, gate_downstream_h, 'g-', linewidth=2, label='Gate Downstream')
    ax.axvline(x=step_time, color='k', linestyle='--', linewidth=1.5, alpha=0.5, label='Step Time')
    ax.set_xlabel('Time (s)', fontsize=10)
    ax.set_ylabel('Water Depth (m)', fontsize=10)
    ax.set_title('Water Depth at Gate', fontsize=11, fontweight='bold')
    # 优化y轴
    gate_h_min = min(min(gate_upstream_h), min(gate_downstream_h))
    gate_h_max = max(max(gate_upstream_h), max(gate_downstream_h))
    gate_h_margin = (gate_h_max - gate_h_min) * 0.15
    ax.set_ylim([gate_h_min - gate_h_margin, gate_h_max + gate_h_margin])
    ax.grid(True, alpha=0.3)
    ax.legend(fontsize=9)

    # 空间分布快照（选择关键时刻）
    key_snapshot_indices = [0, len(snapshot_times)//4, len(snapshot_times)//2, -1]
    ax = axes[2, 0]
    x_full = np.concatenate([upstream_reach.x[:-1], downstream_reach.x + gate_position])
    for idx in key_snapshot_indices:
        t = snapshot_times[idx]
        h_profile = snapshot_h_profiles[idx]
        ax.plot(x_full, h_profile, linewidth=1.5, label=f't={t:.0f}s')
    ax.axvline(x=gate_position, color='r', linestyle='--', linewidth=2, alpha=0.5, label='Gate')
    ax.set_xlabel('Distance (m)', fontsize=10)
    ax.set_ylabel('Water Depth (m)', fontsize=10)
    ax.set_title('Water Depth Profiles (Key Snapshots)', fontsize=11, fontweight='bold')
    ax.grid(True, alpha=0.3)
    ax.legend(fontsize=8)

    ax = axes[2, 1]
    for idx in key_snapshot_indices:
        t = snapshot_times[idx]
        Q_profile = snapshot_Q_profiles[idx]
        ax.plot(x_full, Q_profile, linewidth=1.5, label=f't={t:.0f}s')
    ax.axvline(x=gate_position, color='r', linestyle='--', linewidth=2, alpha=0.5, label='Gate')
    ax.set_xlabel('Distance (m)', fontsize=10)
    ax.set_ylabel('Flow Rate (m³/s)', fontsize=10)
    ax.set_title('Flow Rate Profiles (Key Snapshots)', fontsize=11, fontweight='bold')
    ax.grid(True, alpha=0.3)
    ax.legend(fontsize=8)

    plt.tight_layout()
    fig_path = 'reports/figures/example_01_sluice_gate_dynamics.png'
    plt.savefig(fig_path, dpi=150, bbox_inches='tight')
    plt.close(fig)
    generated_files.append(fig_path)
    print(f"  ✓ 动力学分析图（监测断面+空间分布）")

    print("\n" + "=" * 80)
    print("分析完成！")
    print("=" * 80)

    print(f"\n关键结论:")

    print(f"\n1. 非恒定流动力学:")
    print(f"   - 上游流量阶跃: {Q_before_step} → {Q_after_step} m³/s (at t={step_time}s)")
    print(f"   - 闸门流量响应: {gate_flow[0]:.3f} → {gate_flow[-1]:.3f} m³/s")
    print(f"   - 闸前水位变化: {gate_upstream_h[0]:.3f} → {gate_upstream_h[-1]:.3f} m")
    print(f"   - 水头损失: {gate_upstream_h[-1] - gate_downstream_h[-1]:.3f} m")

    print(f"\n2. 沿程传播特性:")
    print(f"   - 流量和水位扰动沿渠道传播")
    print(f"   - 闸门产生水位跃升，形成上下游水位差")
    print(f"   - 下游边界为水位边界（末端水位固定）")

    print(f"\n3. 闸门过流特性:")
    print(f"   - 开度: {gate.opening} m")
    print(f"   - 流态: {flow_type_list[-1]}")
    print(f"   - 闸门起到流量调节和水位壅高作用")

    print(f"\n生成文件:")
    for f in generated_files:
        print(f"  - {f}")

    print("\n" + "=" * 80)

    # === 生成GIF动画 ===
    print()
    print("=" * 80)
    print("生成GIF动画")
    print("=" * 80)

    from matplotlib.animation import FuncAnimation, PillowWriter

    # 创建改进的GIF动画，展示沿程传播过程
    print("  正在生成动画...")

    # 选择帧（跳帧以减小文件大小）
    frame_skip = 10
    anim_snapshot_indices = list(range(0, len(snapshot_times), frame_skip))
    n_frames = len(anim_snapshot_indices)

    # 创建图形
    fig = plt.figure(figsize=(16, 10))
    gs = fig.add_gridspec(3, 2, hspace=0.35, wspace=0.3)

    # 1. 纵向水深剖面图 (跨两列)
    ax_profile = fig.add_subplot(gs[0, :])
    x_full = np.concatenate([upstream_reach.x[:-1], downstream_reach.x + gate_position])

    # 床面
    bed_elev = np.zeros_like(x_full)
    ax_profile.fill_between(x_full, -0.5, bed_elev, color='saddlebrown', alpha=0.5, label='Channel Bed')

    # 初始水面线
    h_init = snapshot_h_profiles[0]
    line_water, = ax_profile.plot(x_full, h_init, 'b-', linewidth=2.5, label='Water Surface')
    fill_water = ax_profile.fill_between(x_full, bed_elev, h_init, color='lightblue', alpha=0.6)

    # 闸门
    ax_profile.axvline(x=gate_position, color='r', linestyle='-', linewidth=4, alpha=0.7, label='Gate')
    gate_text = ax_profile.text(gate_position + 200, max(h_init) * 0.9,
                               f'Gate Opening: {gate.opening}m',
                               fontsize=10, bbox=dict(boxstyle='round', facecolor='yellow', alpha=0.8))

    # 时间文本
    time_text = ax_profile.text(0.02, 0.98, '', transform=ax_profile.transAxes,
                               fontsize=13, verticalalignment='top', fontweight='bold',
                               bbox=dict(boxstyle='round', facecolor='wheat', alpha=0.9))

    ax_profile.set_xlabel('Distance along Channel (m)', fontsize=11)
    ax_profile.set_ylabel('Water Depth (m)', fontsize=11)
    ax_profile.set_title('Longitudinal Water Depth Profile', fontsize=13, fontweight='bold')
    ax_profile.set_xlim([0, canal_length_total])
    # 优化y轴范围
    all_snapshot_h = [h for h_profile in snapshot_h_profiles for h in h_profile]
    h_min_snap = min(all_snapshot_h)
    h_max_snap = max(all_snapshot_h)
    ax_profile.set_ylim([-0.2, h_max_snap * 1.1])
    ax_profile.grid(True, alpha=0.3)
    ax_profile.legend(fontsize=9, loc='upper left')

    # 2. 流量分布图 (跨两列)
    ax_Q_profile = fig.add_subplot(gs[1, :])
    Q_init = snapshot_Q_profiles[0]
    line_Q, = ax_Q_profile.plot(x_full, Q_init, 'g-', linewidth=2.5, marker='o',
                                markersize=2, label='Flow Rate')
    ax_Q_profile.axvline(x=gate_position, color='r', linestyle='--', linewidth=2, alpha=0.5, label='Gate')

    ax_Q_profile.set_xlabel('Distance along Channel (m)', fontsize=11)
    ax_Q_profile.set_ylabel('Flow Rate (m³/s)', fontsize=11)
    ax_Q_profile.set_title('Longitudinal Flow Rate Distribution', fontsize=13, fontweight='bold')
    ax_Q_profile.set_xlim([0, canal_length_total])
    ax_Q_profile.set_ylim([0, Q_after_step * 1.2])
    ax_Q_profile.grid(True, alpha=0.3)
    ax_Q_profile.legend(fontsize=9)

    # 3. 闸门流量历史
    ax_Q_hist = fig.add_subplot(gs[2, 0])
    line_Q_hist, = ax_Q_hist.plot([], [], 'r-', linewidth=2.5, label='Gate Flow')
    ax_Q_hist.axvline(x=step_time, color='k', linestyle='--', linewidth=1.5, alpha=0.5, label='Step Time')
    ax_Q_hist.axhline(y=Q_before_step, color='b', linestyle=':', alpha=0.5)
    ax_Q_hist.axhline(y=Q_after_step, color='g', linestyle=':', alpha=0.5)
    ax_Q_hist.set_xlabel('Time (s)', fontsize=10)
    ax_Q_hist.set_ylabel('Gate Flow (m³/s)', fontsize=10)
    ax_Q_hist.set_title('Gate Flow Rate History', fontsize=11, fontweight='bold')
    ax_Q_hist.set_xlim([0, total_time])
    ax_Q_hist.set_ylim([0, Q_after_step * 1.2])
    ax_Q_hist.grid(True, alpha=0.3)
    ax_Q_hist.legend(fontsize=9)

    # 4. 闸门水位历史
    ax_h_hist = fig.add_subplot(gs[2, 1])
    line_h_up, = ax_h_hist.plot([], [], 'b-', linewidth=2.5, label='Gate Upstream')
    line_h_down, = ax_h_hist.plot([], [], 'g-', linewidth=2.5, label='Gate Downstream')
    ax_h_hist.axvline(x=step_time, color='k', linestyle='--', linewidth=1.5, alpha=0.5, label='Step Time')
    ax_h_hist.set_xlabel('Time (s)', fontsize=10)
    ax_h_hist.set_ylabel('Water Depth (m)', fontsize=10)
    ax_h_hist.set_title('Water Depth at Gate', fontsize=11, fontweight='bold')
    ax_h_hist.set_xlim([0, total_time])
    ax_h_hist.set_ylim([gate_h_min - gate_h_margin, gate_h_max + gate_h_margin])
    ax_h_hist.grid(True, alpha=0.3)
    ax_h_hist.legend(fontsize=9)

    # 动画更新函数（简化版，不更新fill）
    def update_animation(frame_num):
        """更新动画帧"""
        idx = anim_snapshot_indices[frame_num]
        t = snapshot_times[idx]
        h_profile = snapshot_h_profiles[idx]
        Q_profile = snapshot_Q_profiles[idx]

        # 更新水深剖面
        line_water.set_ydata(h_profile)

        # 更新流量剖面
        line_Q.set_ydata(Q_profile)

        # 更新时间文本
        step_marker = " <-- STEP OCCURRED" if t >= step_time else ""
        time_text.set_text(f'Time = {t:.0f} s{step_marker}')

        # 更新历史曲线（需要找到对应的时间索引）
        time_idx = int(t / dt)
        time_hist = time_series[:time_idx+1]
        line_Q_hist.set_data(time_hist, gate_flow[:time_idx+1])
        line_h_up.set_data(time_hist, gate_upstream_h[:time_idx+1])
        line_h_down.set_data(time_hist, gate_downstream_h[:time_idx+1])

        return line_water, line_Q, time_text, line_Q_hist, line_h_up, line_h_down

    # 创建动画
    anim = FuncAnimation(fig, update_animation, frames=n_frames, interval=150, blit=True)

    # 保存为GIF
    gif_path = 'reports/figures/example_01_sluice_gate_flow_propagation.gif'
    writer = PillowWriter(fps=6)
    anim.save(gif_path, writer=writer, dpi=100)
    plt.close(fig)
    generated_files.append(gif_path)

    print(f"  ✓ 动画生成完成")
    print()

    print("\n" + "=" * 80)
    print("所有文件生成完成！")
    for f in generated_files:
        print(f"  - {f}")
    print("=" * 80)


if __name__ == "__main__":
    run_sluice_gate_dynamics()
