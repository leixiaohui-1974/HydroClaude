#!/usr/bin/env python
"""
示例23: 控制策略性能对比 (PID vs MPC)

对比不同控制策略在明渠水位控制中的性能

场景:
- 被控对象：明渠系统
- 控制目标：维持水位稳定
- 扰动：入流变化
- 对比指标：稳定时间、超调量、能耗、鲁棒性

作者: HydroClaude Team
日期: 2025-10-22
"""

import sys
import os
import numpy as np
import matplotlib.pyplot as plt
from typing import Tuple, List, Dict

# 添加项目根目录到路径
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from core.constants import PhysicsConstants, CanalDefaults, ControlDefaults


class SimplePIDController:
    """简单的PID控制器"""

    def __init__(self, kp: float, ki: float, kd: float,
                 output_limit: Tuple[float, float] = (-1.0, 1.0)):
        self.kp = kp
        self.ki = ki
        self.kd = kd
        self.output_limit = output_limit

        self.integral = 0.0
        self.last_error = 0.0

    def compute(self, error: float, dt: float) -> float:
        """计算控制输出"""
        # 比例项
        p_term = self.kp * error

        # 积分项
        self.integral += error * dt
        i_term = self.ki * self.integral

        # 微分项
        d_term = self.kd * (error - self.last_error) / dt if dt > 0 else 0.0
        self.last_error = error

        # 总输出
        output = p_term + i_term + d_term

        # 限幅
        output = np.clip(output, self.output_limit[0], self.output_limit[1])

        # 抗饱和
        if output == self.output_limit[0] or output == self.output_limit[1]:
            self.integral -= error * dt  # 回退积分

        return output

    def reset(self):
        """重置控制器状态"""
        self.integral = 0.0
        self.last_error = 0.0


class SimpleMPCController:
    """简化的模型预测控制器"""

    def __init__(self, prediction_horizon: int = 10,
                 control_horizon: int = 3,
                 output_limit: Tuple[float, float] = (-1.0, 1.0)):
        self.N = prediction_horizon
        self.M = control_horizon
        self.output_limit = output_limit

        # 权重
        self.Q = 1.0   # 输出权重
        self.R = 0.01  # 输入权重

    def compute(self, current_state: float, setpoint: float,
                system_model, dt: float) -> float:
        """
        计算控制输出

        使用简化的MPC算法（贪心策略）
        """
        best_control = 0.0
        best_cost = float('inf')

        # 搜索最优控制输入（简化为离散搜索）
        test_controls = np.linspace(self.output_limit[0],
                                   self.output_limit[1], 21)

        for u in test_controls:
            # 预测未来状态
            state = current_state
            cost = 0.0

            for k in range(self.N):
                # 系统模型预测
                state = system_model(state, u, dt)

                # 计算成本
                state_error = state - setpoint
                cost += self.Q * state_error**2 + self.R * u**2

            if cost < best_cost:
                best_cost = cost
                best_control = u

        return best_control


def canal_water_balance_model(level: float, control_input: float,
                               inflow: float, dt: float,
                               area: float = 1000.0,
                               outflow_gain: float = 10.0) -> float:
    """
    简化的明渠水量平衡模型

    Args:
        level: 当前水位 (m)
        control_input: 控制输入 (归一化闸门开度 -1~1)
        inflow: 入流 (m³/s)
        dt: 时间步长 (s)
        area: 水面面积 (m²)
        outflow_gain: 出流增益

    Returns:
        新的水位 (m)
    """
    # 出流与闸门开度和水位的关系
    # Q_out = gain * opening * sqrt(h)
    opening = (control_input + 1.0) / 2.0  # 归一化到0-1
    opening = np.clip(opening, 0.05, 1.0)   # 避免完全关闭

    outflow = outflow_gain * opening * np.sqrt(max(level, 0.1))

    # 水量平衡
    dV = (inflow - outflow) * dt
    dh = dV / area

    new_level = level + dh

    return new_level


def generate_disturbance_scenario(duration: float, dt: float,
                                  base_inflow: float = 50.0) -> np.ndarray:
    """
    生成入流扰动场景

    Args:
        duration: 仿真时长 (s)
        dt: 时间步长 (s)
        base_inflow: 基准入流 (m³/s)

    Returns:
        入流时间序列
    """
    n_steps = int(duration / dt)
    time = np.arange(n_steps) * dt

    inflow = np.ones(n_steps) * base_inflow

    # 添加多种扰动
    # 1. 阶跃扰动 (t=100s)
    inflow[time >= 100] += 20

    # 2. 斜坡扰动 (t=200-300s)
    ramp_mask = (time >= 200) & (time < 300)
    inflow[ramp_mask] += (time[ramp_mask] - 200) / 100 * 15

    # 3. 持续扰动
    inflow[time >= 300] += 15

    # 4. 脉冲扰动 (t=400-420s)
    pulse_mask = (time >= 400) & (time < 420)
    inflow[pulse_mask] += 30

    # 5. 随机噪声
    noise = np.random.normal(0, 2, n_steps)
    inflow += noise

    return inflow


def run_control_comparison():
    """运行控制策略对比"""

    print("="*80)
    print("示例23: 控制策略性能对比")
    print("="*80)
    print()

    # ========================================
    # 1. 仿真参数设置
    # ========================================

    duration = 600.0  # 仿真时长 (s)
    dt = 1.0          # 时间步长 (s)
    n_steps = int(duration / dt)
    time = np.arange(n_steps) * dt

    # 系统参数
    target_level = 5.0      # 目标水位 (m)
    initial_level = 5.0     # 初始水位 (m)
    canal_area = 1000.0     # 水面面积 (m²)
    base_inflow = 50.0      # 基准入流 (m³/s)

    print("【仿真参数】")
    print(f"  仿真时长: {duration}s")
    print(f"  时间步长: {dt}s")
    print(f"  目标水位: {target_level}m")
    print(f"  水面面积: {canal_area}m²")
    print(f"  基准入流: {base_inflow}m³/s")
    print()

    # ========================================
    # 2. 创建控制器
    # ========================================

    # PID控制器
    pid_controller = SimplePIDController(
        kp=0.5,
        ki=0.05,
        kd=0.1,
        output_limit=(-1.0, 1.0)
    )

    # MPC控制器
    mpc_controller = SimpleMPCController(
        prediction_horizon=10,
        control_horizon=3,
        output_limit=(-1.0, 1.0)
    )

    print("【控制器配置】")
    print("PID控制器:")
    print(f"  Kp = {pid_controller.kp}")
    print(f"  Ki = {pid_controller.ki}")
    print(f"  Kd = {pid_controller.kd}")
    print()
    print("MPC控制器:")
    print(f"  预测时域: {mpc_controller.N}")
    print(f"  控制时域: {mpc_controller.M}")
    print(f"  输出权重 Q: {mpc_controller.Q}")
    print(f"  输入权重 R: {mpc_controller.R}")
    print()

    # ========================================
    # 3. 生成扰动
    # ========================================

    inflow = generate_disturbance_scenario(duration, dt, base_inflow)

    print("【扰动场景】")
    print(f"  t=0-100s: 基准流量 {base_inflow}m³/s")
    print(f"  t=100s: 阶跃扰动 +20m³/s")
    print(f"  t=200-300s: 斜坡扰动 +15m³/s")
    print(f"  t=400-420s: 脉冲扰动 +30m³/s")
    print(f"  全程: 随机噪声 σ=2m³/s")
    print()

    # ========================================
    # 4. 运行仿真
    # ========================================

    print("开始仿真...")
    print()

    # 系统模型函数 (用于MPC预测)
    def system_model(level, control, dt_step):
        return canal_water_balance_model(
            level, control, base_inflow, dt_step, canal_area)

    # PID仿真
    pid_level = np.zeros(n_steps)
    pid_control = np.zeros(n_steps)
    pid_level[0] = initial_level

    for i in range(1, n_steps):
        error = target_level - pid_level[i-1]
        u_pid = pid_controller.compute(error, dt)
        pid_control[i-1] = u_pid

        pid_level[i] = canal_water_balance_model(
            pid_level[i-1], u_pid, inflow[i], dt, canal_area)

    # MPC仿真
    mpc_level = np.zeros(n_steps)
    mpc_control = np.zeros(n_steps)
    mpc_level[0] = initial_level

    for i in range(1, n_steps):
        u_mpc = mpc_controller.compute(
            mpc_level[i-1], target_level, system_model, dt)
        mpc_control[i-1] = u_mpc

        mpc_level[i] = canal_water_balance_model(
            mpc_level[i-1], u_mpc, inflow[i], dt, canal_area)

    print("仿真完成!")
    print()

    # ========================================
    # 5. 性能评估
    # ========================================

    def evaluate_performance(level, control, target):
        """评估控制性能"""
        # 稳态误差
        steady_state_error = np.mean(np.abs(level[-100:] - target))

        # 最大偏差
        max_deviation = np.max(np.abs(level - target))

        # ISE (Integral Square Error)
        ise = np.sum((level - target)**2) * dt

        # ITAE (Integral Time Absolute Error)
        itae = np.sum(time * np.abs(level - target)) * dt

        # 控制能耗 (输入变化率)
        control_effort = np.sum(np.abs(np.diff(control))) * dt

        return {
            'steady_state_error': steady_state_error,
            'max_deviation': max_deviation,
            'ise': ise,
            'itae': itae,
            'control_effort': control_effort
        }

    pid_perf = evaluate_performance(pid_level, pid_control, target_level)
    mpc_perf = evaluate_performance(mpc_level, mpc_control, target_level)

    print("【性能评估】")
    print("-" * 80)
    print(f"{'指标':<25} {'PID':<15} {'MPC':<15} {'优势':<10}")
    print("-" * 80)

    metrics = [
        ('稳态误差 (m)', 'steady_state_error'),
        ('最大偏差 (m)', 'max_deviation'),
        ('ISE', 'ise'),
        ('ITAE', 'itae'),
        ('控制能耗', 'control_effort')
    ]

    for metric_name, metric_key in metrics:
        pid_val = pid_perf[metric_key]
        mpc_val = mpc_perf[metric_key]
        winner = 'PID' if pid_val < mpc_val else 'MPC'

        print(f"{metric_name:<25} {pid_val:<15.3f} {mpc_val:<15.3f} {winner:<10}")

    print()

    # ========================================
    # 6. 可视化
    # ========================================

    fig, axes = plt.subplots(3, 2, figsize=(15, 12))
    fig.suptitle('Control Strategy Performance Comparison (PID vs MPC)',
                fontsize=16, fontweight='bold')

    # 子图1: 水位响应
    ax1 = axes[0, 0]
    ax1.plot(time, pid_level, 'b-', label='PID', linewidth=2, alpha=0.8)
    ax1.plot(time, mpc_level, 'r-', label='MPC', linewidth=2, alpha=0.8)
    ax1.axhline(target_level, color='g', linestyle='--', linewidth=2,
                label='Target', alpha=0.6)
    ax1.set_xlabel('Time (s)')
    ax1.set_ylabel('Water Level (m)')
    ax1.set_title('Water Level Response')
    ax1.legend()
    ax1.grid(True, alpha=0.3)

    # 子图2: 控制输入
    ax2 = axes[0, 1]
    ax2.plot(time[:-1], pid_control[:-1], 'b-', label='PID', linewidth=2, alpha=0.8)
    ax2.plot(time[:-1], mpc_control[:-1], 'r-', label='MPC', linewidth=2, alpha=0.8)
    ax2.set_xlabel('Time (s)')
    ax2.set_ylabel('Control Input (normalized)')
    ax2.set_title('Control Input Signal')
    ax2.legend()
    ax2.grid(True, alpha=0.3)

    # 子图3: 跟踪误差
    ax3 = axes[1, 0]
    pid_error = pid_level - target_level
    mpc_error = mpc_level - target_level
    ax3.plot(time, pid_error, 'b-', label='PID', linewidth=2, alpha=0.8)
    ax3.plot(time, mpc_error, 'r-', label='MPC', linewidth=2, alpha=0.8)
    ax3.axhline(0, color='k', linestyle='--', alpha=0.3)
    ax3.set_xlabel('Time (s)')
    ax3.set_ylabel('Tracking Error (m)')
    ax3.set_title('Tracking Error')
    ax3.legend()
    ax3.grid(True, alpha=0.3)

    # 子图4: 入流扰动
    ax4 = axes[1, 1]
    ax4.plot(time, inflow, 'k-', linewidth=2, alpha=0.8)
    ax4.set_xlabel('Time (s)')
    ax4.set_ylabel('Inflow (m³/s)')
    ax4.set_title('Disturbance Input (Inflow Variation)')
    ax4.grid(True, alpha=0.3)

    # 子图5: 性能指标对比
    ax5 = axes[2, 0]
    metric_names = ['SSE', 'Max Dev', 'ISE/100', 'ITAE/1000', 'Effort/10']
    pid_values = [
        pid_perf['steady_state_error'],
        pid_perf['max_deviation'],
        pid_perf['ise']/100,
        pid_perf['itae']/1000,
        pid_perf['control_effort']/10
    ]
    mpc_values = [
        mpc_perf['steady_state_error'],
        mpc_perf['max_deviation'],
        mpc_perf['ise']/100,
        mpc_perf['itae']/1000,
        mpc_perf['control_effort']/10
    ]

    x = np.arange(len(metric_names))
    width = 0.35
    ax5.bar(x - width/2, pid_values, width, label='PID', alpha=0.8, color='blue')
    ax5.bar(x + width/2, mpc_values, width, label='MPC', alpha=0.8, color='red')
    ax5.set_ylabel('Performance Metrics (normalized)')
    ax5.set_title('Performance Metrics Comparison')
    ax5.set_xticks(x)
    ax5.set_xticklabels(metric_names, rotation=15, ha='right')
    ax5.legend()
    ax5.grid(True, alpha=0.3, axis='y')

    # 子图6: 局部放大 (显示扰动响应)
    ax6 = axes[2, 1]
    zoom_start = 95
    zoom_end = 150
    zoom_mask = (time >= zoom_start) & (time <= zoom_end)

    ax6.plot(time[zoom_mask], pid_level[zoom_mask], 'b-',
            label='PID', linewidth=2, alpha=0.8)
    ax6.plot(time[zoom_mask], mpc_level[zoom_mask], 'r-',
            label='MPC', linewidth=2, alpha=0.8)
    ax6.axhline(target_level, color='g', linestyle='--', linewidth=2,
               label='Target', alpha=0.6)
    ax6.set_xlabel('Time (s)')
    ax6.set_ylabel('Water Level (m)')
    ax6.set_title(f'Disturbance Response (Zoom: {zoom_start}-{zoom_end}s)')
    ax6.legend()
    ax6.grid(True, alpha=0.3)

    plt.tight_layout()

    output_path = '/home/user/HydroClaude/examples/example_23_control_comparison/control_comparison.png'
    plt.savefig(output_path, dpi=150, bbox_inches='tight')
    print(f"图像已保存到: {output_path}")
    print()

    # ========================================
    # 7. 结论
    # ========================================

    print("【对比结论】")
    print("-" * 80)
    print()

    print("PID控制器:")
    print("  优点:")
    print("    • 结构简单，易于实现")
    print("    • 参数少，调试方便")
    print("    • 计算量小")
    print("  缺点:")
    print("    • 对模型不确定性敏感")
    print("    • 难以处理约束")
    print("    • 大扰动下性能下降")
    print()

    print("MPC控制器:")
    print("  优点:")
    print("    • 能处理约束")
    print("    • 考虑未来预测")
    print("    • 多变量优化")
    print("  缺点:")
    print("    • 计算量大")
    print("    • 需要准确模型")
    print("    • 调参复杂")
    print()

    # 确定综合优胜者
    pid_wins = sum(1 for metric_key in ['steady_state_error', 'max_deviation',
                                        'ise', 'itae', 'control_effort']
                  if pid_perf[metric_key] < mpc_perf[metric_key])
    mpc_wins = 5 - pid_wins

    winner = 'PID' if pid_wins > mpc_wins else 'MPC'

    print(f"综合评分: PID {pid_wins}/5, MPC {mpc_wins}/5")
    print(f"在本场景中，{winner}控制器表现更优")
    print()

    return {
        'pid_performance': pid_perf,
        'mpc_performance': mpc_perf,
        'time': time,
        'pid_level': pid_level,
        'mpc_level': mpc_level
    }


if __name__ == '__main__':
    results = run_control_comparison()

    print("="*80)
    print("示例23完成!")
    print("="*80)
    print()
    print("关键成果:")
    print("  ✓ PID控制器实现")
    print("  ✓ MPC控制器实现")
    print("  ✓ 多种扰动场景")
    print("  ✓ 性能指标对比")
    print("  ✓ 可视化分析")
