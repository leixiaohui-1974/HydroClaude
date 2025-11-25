#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
工程案例4: 参数在线校准

场景：
  运行中的渠道系统，糙率因淤积而变化，需要实时校准

目标：
  使用增广卡尔曼滤波（Augmented EKF）在线估计糙率参数

作者: Claude
日期: 2025-10-24
"""

import sys
import warnings
warnings.filterwarnings("ignore")
import os
import numpy as np
import matplotlib.pyplot as plt

# 添加项目路径
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))))

from solvers.hydrostatic_canal_solver import HydrostaticCanalSolver
from solvers.gate import SluiceGate
from solvers.parameter_estimation import ParameterEstimator


def create_synthetic_data(solver, true_roughness, num_steps=100, dt=10.0):
    """
    生成合成观测数据（模拟真实系统）

    Args:
        solver: 求解器
        true_roughness: 真实糙率值
        num_steps: 时间步数
        dt: 时间步长

    Returns:
        观测数据列表
    """
    print("\n[1/4] 生成合成观测数据...")
    print(f"      真实糙率: n = {true_roughness:.4f}")

    # 设置真实糙率
    solver.n = true_roughness

    # 生成稳态初值
    # 注意：Q_in和h_downstream应该在调用前已设置
    solver.solve_steady_state(Q_target=solver.Q_in, h_downstream=solver.h_downstream)

    # 观测数据
    measurements = []

    # 添加小扰动模拟真实系统
    for step in range(num_steps):
        t = step * dt

        # 添加随机扰动到流量（模拟真实变化）
        if step % 20 == 0:
            flow_variation = 1.0 + 0.1 * np.random.randn()
            solver.Q_in = 10.0 * flow_variation

        # 时间推进
        h_new, hu_new = solver.step_preissmann(dt)
        solver.h = h_new
        solver.hu = hu_new

        # 模拟传感器观测（添加观测噪声）
        sensor_locations = [solver.nx // 3, solver.nx // 2, 2 * solver.nx // 3]
        obs = {}

        for loc in sensor_locations:
            # 水位观测（添加+/-1cm的噪声）
            h_obs = solver.h[loc] + 0.01 * np.random.randn()
            obs[f'level_{loc}'] = h_obs

        measurements.append({
            'time': t,
            'observations': obs
        })

    print(f"       已生成 {num_steps} 个时间步的观测数据")
    print(f"       传感器位置: {sensor_locations}")

    return measurements


def run_parameter_calibration():
    """运行参数校准"""
    print("=" * 90)
    print("工程案例4: 参数在线校准")
    print("=" * 90)
    print()
    print("场景: 运行中的渠道系统，糙率因淤积而变化")
    print("任务: 使用增广卡尔曼滤波在线估计糙率")
    print()

    # ========================================
    # 系统配置
    # ========================================
    L = 10000.0          # 渠道长度 (m)
    B = 8.0              # 渠道宽度 (m)
    S0 = 0.0002          # 底坡
    nx = 101             # 网格点数

    true_roughness = 0.028   # 真实糙率（未知）
    initial_guess = 0.020    # 初始猜测（偏差较大）

    Q_in = 10.0          # 上游流量 (m^3/s)
    h_downstream = 1.5   # 下游水深 (m)

    # ========================================
    # 第1步: 生成"真实"观测数据
    # ========================================

    # 创建"真实系统"求解器
    x = np.linspace(0, L, nx)
    true_solver = HydrostaticCanalSolver(
        length=L,
        nx=nx,
        B=B,
        S0=S0,
        n=true_roughness,
        g=9.81
    )
    true_solver.Q_in = Q_in
    true_solver.h_downstream = h_downstream

    # 生成合成观测数据
    measurements = create_synthetic_data(
        true_solver,
        true_roughness,
        num_steps=100,
        dt=10.0
    )

    # ========================================
    # 第2步: 创建估计系统
    # ========================================
    print("\n[2/4] 创建参数估计系统...")

    # 创建估计用的求解器（使用错误的初始猜测）
    est_solver = HydrostaticCanalSolver(
        length=L,
        nx=nx,
        B=B,
        S0=S0,
        n=initial_guess,  # 错误的初始值
        g=9.81
    )
    est_solver.Q_in = Q_in
    est_solver.h_downstream = h_downstream
    est_solver.solve_steady_state(Q_target=Q_in, h_downstream=h_downstream)

    # 创建参数估计器
    estimator = ParameterEstimator(
        solver=est_solver,
        dt=10.0,
        estimate_roughness=True,
        estimate_leakage=False,
        process_noise_std=0.01,
        parameter_process_noise=1e-5,
        verbose=False
    )

    print(f"       初始糙率猜测: n = {initial_guess:.4f}")
    print(f"       真实糙率值: n = {true_roughness:.4f}")
    print(f"       初始误差: {abs(initial_guess - true_roughness) / true_roughness * 100:.1f}%")

    # ========================================
    # 第3步: 在线参数估计
    # ========================================
    print("\n[3/4] 执行在线参数估计...")

    # 传感器配置
    sensors = [
        {'location': nx // 3, 'type': 'water_level', 'std': 0.01},
        {'location': nx // 2, 'type': 'water_level', 'std': 0.01},
        {'location': 2 * nx // 3, 'type': 'water_level', 'std': 0.01},
    ]

    # 记录估计历史
    roughness_history = [initial_guess]
    time_history = [0.0]

    # 在线估计循环
    for step, meas in enumerate(measurements):
        # 预测步
        estimator.predict_step(10.0)

        # 准备观测数据
        obs_data = {}
        for i, sensor in enumerate(sensors):
            key = f'level_{sensor["location"]}'
            if key in meas['observations']:
                obs_data[key] = meas['observations'][key]

        # 更新步
        if obs_data:
            innovations = estimator.update_step(obs_data)

        # 记录估计值
        current_roughness = estimator.solver.n
        roughness_history.append(current_roughness)
        time_history.append(meas['time'])

        # 每20步输出一次
        if step % 20 == 0:
            error = abs(current_roughness - true_roughness) / true_roughness * 100
            print(f"      步数 {step:3d}: n = {current_roughness:.5f}, 误差 = {error:.2f}%")

    print(f"       估计完成")

    # ========================================
    # 第4步: 结果分析和可视化
    # ========================================
    print("\n[4/4] 生成结果分析...")

    final_roughness = roughness_history[-1]
    final_error = abs(final_roughness - true_roughness) / true_roughness * 100

    print(f"\n最终结果:")
    print(f"  真实糙率:   n = {true_roughness:.5f}")
    print(f"  估计糙率:   n = {final_roughness:.5f}")
    print(f"  最终误差:   {final_error:.2f}%")
    print(f"  初始误差:   {abs(initial_guess - true_roughness) / true_roughness * 100:.1f}%")
    print(f"  误差减少:   {abs(initial_guess - true_roughness) / true_roughness * 100 - final_error:.1f}%")

    # 可视化
    fig, axes = plt.subplots(2, 1, figsize=(12, 8))

    # 子图1: 糙率估计历史
    axes[0].plot(np.array(time_history) / 60, roughness_history, 'b-', linewidth=2, label='估计值')
    axes[0].axhline(y=true_roughness, color='r', linestyle='--', linewidth=2, label='真实值')
    axes[0].axhline(y=initial_guess, color='g', linestyle=':', linewidth=1.5, label='初始猜测')
    axes[0].set_xlabel('时间 (min)', fontsize=12)
    axes[0].set_ylabel('糙率 n', fontsize=12)
    axes[0].set_title('参数估计历史 - 糙率收敛过程', fontsize=14, fontweight='bold')
    axes[0].legend(fontsize=10)
    axes[0].grid(True, alpha=0.3)

    # 子图2: 相对误差历史
    error_history = [abs(n - true_roughness) / true_roughness * 100 for n in roughness_history]
    axes[1].semilogy(np.array(time_history) / 60, error_history, 'r-', linewidth=2)
    axes[1].set_xlabel('时间 (min)', fontsize=12)
    axes[1].set_ylabel('相对误差 (%)', fontsize=12)
    axes[1].set_title('估计误差收敛曲线', fontsize=14, fontweight='bold')
    axes[1].grid(True, alpha=0.3)

    plt.tight_layout()

    # 保存结果
    output_dir = os.path.join(os.path.dirname(__file__), 'results')
    os.makedirs(output_dir, exist_ok=True)

    output_file = os.path.join(output_dir, 'parameter_calibration.png')
    plt.savefig(output_file, dpi=150, bbox_inches='tight')
    print(f"\n 结果图保存至: {output_file}")

    plt.close()

    print()
    print("=" * 90)
    print(" 参数校准完成！")
    print("=" * 90)


if __name__ == "__main__":
    run_parameter_calibration()
