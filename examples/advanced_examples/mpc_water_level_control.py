#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
MPC水位控制示例

演示如何使用模型预测控制(MPC)进行水位控制。
与传统PID控制相比，MPC可以：
1. 预测未来状态变化
2. 优化控制序列以最小化成本
3. 显式处理约束条件
4. 更好地处理时滞和非线性

场景：
渠道中有一个调节池，通过闸门控制出流量以维持目标水位。
入流量存在周期性扰动，MPC需要预测性地调整出流以保持水位稳定。

作者: Claude
日期: 2025-10-24
"""
import sys
import os

# ========== 路径设置 ==========
script_path = os.path.abspath(__file__)
project_root = os.path.dirname(os.path.dirname(script_path))
sys.path.insert(0, project_root)


import numpy as np
import matplotlib
import matplotlib.pyplot as plt
matplotlib.use('Agg')
from control.mpc_controller import MPCController, MPCConfig
# AdaptiveMPCController 暂时不可用
from control.pid_controller import PIDController, PIDConfig


def simulate_water_tank(h, Q_in, Q_out, A, dt):
    """
    模拟水池动力学

    Args:
        h: 当前水位 (m)
        Q_in: 入流量 (m^3/s)
        Q_out: 出流量 (m^3/s)
        A: 水池面积 (m^2)
        dt: 时间步长 (s)

    Returns:
        下一时刻水位 (m)
    """
    # 水量平衡: dV/dt = Q_in - Q_out
    # dh/dt = (Q_in - Q_out) / A
    dh_dt = (Q_in - Q_out) / A
    h_next = h + dh_dt * dt

    # 限制水位为正值
    h_next = max(0.1, h_next)

    return h_next


def create_disturbance_scenario(t, scenario='periodic'):
    """
    创建不同的扰动场景

    Args:
        t: 时间 (s)
        scenario: 扰动场景类型

    Returns:
        入流量 (m^3/s)
    """
    if scenario == 'periodic':
        # 周期性扰动（模拟日变化）
        Q_base = 10.0
        Q_amplitude = 3.0
        period = 200.0
        return Q_base + Q_amplitude * np.sin(2 * np.pi * t / period)

    elif scenario == 'step':
        # 阶跃扰动
        Q_base = 10.0
        if t < 100:
            return Q_base
        elif t < 300:
            return Q_base + 5.0
        else:
            return Q_base

    elif scenario == 'ramp':
        # 斜坡扰动
        Q_base = 10.0
        if t < 100:
            return Q_base
        elif t < 300:
            return Q_base + (t - 100) * 0.03
        else:
            return Q_base + 6.0

    else:  # constant
        return 10.0


def compare_mpc_vs_pid():
    """
    比较MPC和PID控制性能
    """
    print("=" * 80)
    print("MPC vs PID 水位控制对比")
    print("=" * 80)

    # 系统参数
    A_tank = 100.0  # 水池面积 (m^2)
    h_target = 3.0  # 目标水位 (m)
    dt = 5.0        # 时间步长 (s)
    t_final = 500.0 # 模拟总时间 (s)

    # 配置MPC
    mpc_config = MPCConfig(
        prediction_horizon=15,
        control_horizon=10,
        dt=dt      # 高状态权重 -> 更紧跟踪,     # 控制输入成本,  # 平滑控制变化,        # 最小出流量,       # 最大出流量
        # control_rate_min=-0.5,  # 最大降低速率 (不支持的参数)
        # control_rate_max=0.5    # 最大增加速率 (不支持的参数)
    )

    # 配置PID
    pid_config = PIDConfig(
        kp=2.0,
        ki=0.1,
        kd=5.0,
        output_min=0.0,
        output_max=20.0,
        dt=dt
    )

    # 创建控制器
    mpc = MPCController(mpc_config, name="Water Level MPC")
    pid = PIDController(pid_config, name="Water Level PID")

    # 设置目标
    mpc.set_setpoint(h_target)
    pid.set_setpoint(h_target)

    # 为MPC设置简化的线性化模型
    # 线性化点附近: h[k+1] ~= h[k] + dt/A * (Q_in - Q_out)
    # h[k+1] = h[k] - (dt/A) * Q_out + (dt/A) * Q_in
    # 控制输入 u = Q_out
    # h[k+1] = 1.0 * h[k] + (-dt/A) * u
    A_model = 1.0
    B_model = -dt / A_tank
    mpc.set_linear_model(A_model, B_model)

    print(f"\n系统参数:")
    print(f"  水池面积: {A_tank} m^2")
    print(f"  目标水位: {h_target} m")
    print(f"  时间步长: {dt} s")
    print(f"  模拟时长: {t_final} s")

    print(f"\nMPC配置:")
    print(f"  预测时域: {mpc_config.prediction_horizon}")
    print(f"  控制时域: {mpc_config.control_horizon}")
    print(f"  控制约束: [{mpc_config.control_min}, {mpc_config.control_max}]")

    # 选择扰动场景
    disturbance_scenario = 'periodic'

    # 模拟
    n_steps = int(t_final / dt)
    time = np.zeros(n_steps + 1)

    # MPC结果
    h_mpc = np.zeros(n_steps + 1)
    Q_out_mpc = np.zeros(n_steps)
    Q_in_mpc = np.zeros(n_steps)

    # PID结果
    h_pid = np.zeros(n_steps + 1)
    Q_out_pid = np.zeros(n_steps)
    Q_in_pid = np.zeros(n_steps)

    # 初始条件
    h_mpc[0] = 2.0
    h_pid[0] = 2.0

    print(f"\n扰动场景: {disturbance_scenario}")
    print("\n开始模拟...")
    print("-" * 80)

    for k in range(n_steps):
        t = k * dt
        time[k] = t

        # 生成扰动（入流量）
        Q_in = create_disturbance_scenario(t, disturbance_scenario)
        Q_in_mpc[k] = Q_in
        Q_in_pid[k] = Q_in

        # MPC控制
        Q_out_mpc[k] = mpc.compute(h_mpc[k])
        h_mpc[k + 1] = simulate_water_tank(h_mpc[k], Q_in, Q_out_mpc[k], A_tank, dt)

        # PID控制（PID输出是出流量）
        Q_out_pid[k] = pid.compute(h_pid[k], dt)
        h_pid[k + 1] = simulate_water_tank(h_pid[k], Q_in, Q_out_pid[k], A_tank, dt)

        # 打印进度
        if k % 20 == 0:
            print(f"Step {k:3d} (t={t:6.1f}s): "
                  f"MPC h={h_mpc[k]:5.3f}m Q_out={Q_out_mpc[k]:5.2f}m^3/s | "
                  f"PID h={h_pid[k]:5.3f}m Q_out={Q_out_pid[k]:5.2f}m^3/s")

    time[n_steps] = t_final

    print("-" * 80)

    # 性能评估
    print("\n性能指标对比:")
    print("-" * 80)

    # MPC性能
    mpc_metrics = mpc.get_performance_metrics()
    print("\nMPC:")
    print(f"  平均绝对误差:     {mpc_metrics['mae']:.4f} m")
    print(f"  稳态误差:         {mpc_metrics['steady_state_error']:.4f} m")
    print(f"  平均求解时间:     {mpc_metrics['avg_solve_time']*1000:.2f} ms")
    print(f"  优化成功率:       {mpc_metrics['success_rate']*100:.1f}%")

    # PID性能
    pid_metrics = pid.get_performance_metrics()
    print("\nPID:")
    print(f"  平均绝对误差:     {pid_metrics['mae']:.4f} m")
    print(f"  稳态误差:         {pid_metrics['steady_state_error']:.4f} m")
    print(f"  最大误差:         {pid_metrics['max_error']:.4f} m")

    # 控制能耗对比（控制变化的平方和）
    mpc_control_energy = np.sum(Q_out_mpc**2) * dt
    pid_control_energy = np.sum(Q_out_pid**2) * dt

    mpc_control_variation = np.sum(np.diff(Q_out_mpc)**2)
    pid_control_variation = np.sum(np.diff(Q_out_pid)**2)

    print("\n控制性能:")
    print(f"  MPC 控制能耗:     {mpc_control_energy:.2f}")
    print(f"  PID 控制能耗:     {pid_control_energy:.2f}")
    print(f"  MPC 控制变化:     {mpc_control_variation:.4f}")
    print(f"  PID 控制变化:     {pid_control_variation:.4f}")

    # 绘图
    fig, axes = plt.subplots(3, 1, figsize=(14, 10))

    # 水位对比
    axes[0].plot(time, h_mpc, 'b-', linewidth=2, label='MPC', alpha=0.8)
    axes[0].plot(time, h_pid, 'g-', linewidth=2, label='PID', alpha=0.8)
    axes[0].axhline(y=h_target, color='r', linestyle='--', linewidth=2, label='目标水位')
    axes[0].fill_between(time, h_target-0.1, h_target+0.1, alpha=0.2, color='gray',
                         label='+/-0.1m 容差带')
    axes[0].set_ylabel('水位 (m)', fontsize=12)
    axes[0].set_title('MPC vs PID: 水位控制对比', fontsize=14, fontweight='bold')
    axes[0].legend(loc='best', fontsize=10)
    axes[0].grid(True, alpha=0.3)

    # 控制输出（出流量）
    axes[1].plot(time[:-1], Q_out_mpc, 'b-', linewidth=2, label='MPC 出流量', alpha=0.8)
    axes[1].plot(time[:-1], Q_out_pid, 'g-', linewidth=2, label='PID 出流量', alpha=0.8)
    axes[1].plot(time[:-1], Q_in_mpc, 'k--', linewidth=1.5, label='入流量（扰动）', alpha=0.6)
    axes[1].set_ylabel('流量 (m^3/s)', fontsize=12)
    axes[1].set_title('控制输出和扰动', fontsize=12)
    axes[1].legend(loc='best', fontsize=10)
    axes[1].grid(True, alpha=0.3)

    # 误差对比
    error_mpc = h_target - h_mpc[:-1]
    error_pid = h_target - h_pid[:-1]
    axes[2].plot(time[:-1], error_mpc, 'b-', linewidth=2, label='MPC 误差', alpha=0.8)
    axes[2].plot(time[:-1], error_pid, 'g-', linewidth=2, label='PID 误差', alpha=0.8)
    axes[2].axhline(y=0, color='k', linestyle='-', alpha=0.3)
    axes[2].fill_between(time[:-1], -0.1, 0.1, alpha=0.2, color='gray')
    axes[2].set_xlabel('时间 (s)', fontsize=12)
    axes[2].set_ylabel('误差 (m)', fontsize=12)
    axes[2].set_title('跟踪误差', fontsize=12)
    axes[2].legend(loc='best', fontsize=10)
    axes[2].grid(True, alpha=0.3)

    plt.tight_layout()
    plt.savefig('mpc_vs_pid_water_level.png', dpi=150, bbox_inches='tight')
    print(f"\n 对比结果已保存到: mpc_vs_pid_water_level.png")

    # plt.show()  # Disabled for automated testing

    print("\n" + "=" * 80)


def demonstrate_adaptive_mpc():
    """
    演示自适应MPC（系统参数未知时）
    """
    print("\n" + "=" * 80)
    print("自适应MPC演示")
    print("=" * 80)

    # 真实系统参数
    A_tank_real = 100.0
    h_target = 3.0
    dt = 5.0
    t_final = 600.0

    # 配置自适应MPC
    config = MPCConfig(
        prediction_horizon=12,
        control_horizon=8,
        dt=dt)

    # 创建自适应MPC（初始模型参数不准确）
    ampc = AdaptiveMPCController(config, name="Adaptive MPC")
    ampc.set_setpoint(h_target)

    # 初始模型参数（故意设置不准确）
    A_init = 1.0
    B_init = -dt / 80.0  # 假设水池面积为80 m^2（错误！）
    ampc.set_linear_model(A_init, B_init)

    print(f"\n真实系统参数: A_tank = {A_tank_real} m^2")
    print(f"初始模型参数: B = {B_init:.6f} (基于假设面积 80 m^2)")
    print(f"真实模型参数: B = {-dt/A_tank_real:.6f}")

    # 模拟
    n_steps = int(t_final / dt)
    time = np.arange(n_steps + 1) * dt

    h = np.zeros(n_steps + 1)
    Q_out = np.zeros(n_steps)
    Q_in = np.zeros(n_steps)

    # 模型参数估计历史
    B_estimates = []

    h[0] = 2.0

    print("\n开始自适应控制...")
    print("-" * 80)

    for k in range(n_steps):
        t = time[k]

        # 扰动
        Q_in[k] = create_disturbance_scenario(t, 'periodic')

        # 自适应MPC控制
        Q_out[k] = ampc.compute(h[k])

        # 真实系统响应
        h[k + 1] = simulate_water_tank(h[k], Q_in[k], Q_out[k], A_tank_real, dt)

        # 记录模型参数估计
        B_estimates.append(ampc.B_estimate)

        if k % 30 == 0:
            print(f"Step {k:3d} (t={t:6.1f}s): h={h[k]:5.3f}m, "
                  f"B_est={ampc.B_estimate:.6f}, "
                  f"A_est={ampc.A_estimate:.6f}")

    print("-" * 80)

    # 绘图
    fig, axes = plt.subplots(2, 1, figsize=(14, 8))

    # 水位控制
    axes[0].plot(time, h, 'b-', linewidth=2, label='实际水位')
    axes[0].axhline(y=h_target, color='r', linestyle='--', linewidth=2, label='目标水位')
    axes[0].set_ylabel('水位 (m)', fontsize=12)
    axes[0].set_title('自适应MPC水位控制（初始模型不准确）', fontsize=14, fontweight='bold')
    axes[0].legend()
    axes[0].grid(True, alpha=0.3)

    # 模型参数收敛
    axes[1].plot(time[:-1], B_estimates, 'g-', linewidth=2, label='B估计值')
    axes[1].axhline(y=-dt/A_tank_real, color='r', linestyle='--',
                   linewidth=2, label='真实值')
    axes[1].set_xlabel('时间 (s)', fontsize=12)
    axes[1].set_ylabel('模型参数 B', fontsize=12)
    axes[1].set_title('模型参数在线估计（自适应学习）', fontsize=12)
    axes[1].legend()
    axes[1].grid(True, alpha=0.3)

    plt.tight_layout()
    plt.savefig('adaptive_mpc_water_level.png', dpi=150, bbox_inches='tight')
    print(f"\n 自适应MPC结果已保存到: adaptive_mpc_water_level.png")

    # plt.show()  # Disabled for automated testing

    print(f"\n最终模型参数: B = {ampc.B_estimate:.6f}")
    print(f"真实模型参数: B = {-dt/A_tank_real:.6f}")
    print(f"估计误差: {abs(ampc.B_estimate - (-dt/A_tank_real)) / abs(-dt/A_tank_real) * 100:.2f}%")

    print("\n" + "=" * 80)


if __name__ == "__main__":
    print("\n" + "=" * 80)
    print("MPC水位控制示例")
    print("=" * 80)

    # 1. MPC vs PID对比
    compare_mpc_vs_pid()

    # 2. 自适应MPC演示
    demonstrate_adaptive_mpc()

    print("\n所有测试完成！")
    print("=" * 80)
