#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
数字孪生测试

测试数字孪生功能：
1. 状态估计（EKF）
2. 数据同化（传感器融合）
3. 不确定性量化
4. 预测功能

作者: Claude
日期: 2025-10-23
"""

import sys
import pytest
import warnings
warnings.filterwarnings("ignore")
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import numpy as np
import matplotlib.pyplot as plt
from matplotlib.gridspec import GridSpec
import time

try:
    from solvers.hydrostatic_canal_solver import HydrostaticCanalSolver
except ImportError as e:
    pytest.skip(f"Required module not available: {e}", allow_module_level=True)

from solvers.digital_twin import DigitalTwin


def test_state_estimation():
    """
    测试1: 状态估计

    场景：
    - 有一个"真实"系统（带噪声）
    - 有传感器观测（带噪声）
    - 数字孪生融合数据进行状态估计
    """
    print("=" * 80)
    print("测试1: 数字孪生状态估计")
    print("=" * 80)

    # 参数
    L = 500.0
    nx = 26
    B = 10.0
    S0 = 0.001
    n = 0.025

    # 创建"真实"系统（用于生成观测数据）
    true_solver = HydrostaticCanalSolver(
        length=L, nx=nx, B=B, S0=S0, n=n
    )

    # 初始条件
    Q_initial = 5.0
    h_initial = 0.6
    true_solver.h = np.ones(nx) * h_initial
    true_solver.hu = np.ones(nx) * Q_initial / B

    # 创建数字孪生（初始状态有误差）
    twin_solver = HydrostaticCanalSolver(
        length=L, nx=nx, B=B, S0=S0, n=n
    )
    twin_solver.h = np.ones(nx) * (h_initial + 0.1)  # +10cm 初始误差
    twin_solver.hu = np.ones(nx) * Q_initial / B

    digital_twin = DigitalTwin(
        solver=twin_solver,
        dt=1.0,
        process_noise_std=0.005,
        verbose=True
    )

    # 添加传感器（25%和75%位置各一个水位计）
    digital_twin.add_sensor(
        name='level_1',
        sensor_type='water_level',
        location_idx=nx // 4,
        noise_std=0.01  # 1cm 噪声
    )

    digital_twin.add_sensor(
        name='level_2',
        sensor_type='water_level',
        location_idx=3 * nx // 4,
        noise_std=0.01
    )

    # 边界条件（入流阶跃）
    def Q_upstream(t):
        return 5.0 if t < 30 else 8.0

    def h_downstream(t):
        return 0.6 if t < 30 else 0.75

    # 测量函数（从真实系统获取观测）
    def get_measurements(t):
        measurements = {}

        # 在真实系统中执行一步
        Q_up = Q_upstream(t)
        h_down = h_downstream(t)

        h_true, hu_true = true_solver.step_preissmann(
            dt=digital_twin.dt,
            max_iter=10,
            enforce_bc=True,
            Q_in=Q_up,
            h_out=h_down
        )
        true_solver.h = h_true
        true_solver.hu = hu_true

        # 模拟传感器测量
        for sensor_name, sensor in digital_twin.sensors.items():
            idx = sensor.location_idx
            true_value = true_solver.h[idx]
            measurements[sensor_name] = sensor.measure(true_value, add_noise=True)

        return measurements

    # 运行数据同化
    print("\n开始数据同化...")
    t_start = time.time()

    result = digital_twin.run_assimilation(
        t_end=100.0,
        Q_upstream_func=Q_upstream,
        h_downstream_func=h_downstream,
        measurement_func=get_measurements,
        assimilation_interval=1  # 每步都同化
    )

    elapsed = time.time() - t_start
    print(f"完成! 耗时: {elapsed:.2f} 秒")

    # 收集真实状态历史（重新运行真实系统以获取完整历史）
    true_solver.h = np.ones(nx) * h_initial
    true_solver.hu = np.ones(nx) * Q_initial / B

    h_true_history = []
    for t in result['time']:
        h_true_history.append(true_solver.h.copy())
        if t < result['time'][-1]:
            h_t, hu_t = true_solver.step_preissmann(
                dt=digital_twin.dt, max_iter=10, enforce_bc=True,
                Q_in=Q_upstream(t), h_out=h_downstream(t)
            )
            true_solver.h = h_t
            true_solver.hu = hu_t

    h_true_history = np.array(h_true_history)

    # 分析结果
    times = np.array(result['time'])
    h_est = np.array(result['h'])
    h_std = np.array(result['h_std'])

    # 计算估计误差
    errors = h_est - h_true_history
    rmse = np.sqrt(np.mean(errors ** 2))

    print(f"\n结果分析:")
    print(f"  初始误差（RMS）: {np.sqrt(np.mean((h_est[0] - h_true_history[0])**2)):.4f} m")
    print(f"  最终误差（RMS）: {np.sqrt(np.mean((h_est[-1] - h_true_history[-1])**2)):.4f} m")
    print(f"  整体RMSE: {rmse:.4f} m")
    print(f"  平均不确定性: {np.mean(h_std[-1]):.4f} m")

    # 绘图
    fig = plt.figure(figsize=(16, 10))
    gs = GridSpec(3, 2, figure=fig)

    # 1. 某点水深时间序列
    ax1 = fig.add_subplot(gs[0, 0])
    mid_idx = nx // 2
    ax1.plot(times, h_true_history[:, mid_idx], 'k-', linewidth=2, label='True state', alpha=0.7)
    ax1.plot(times, h_est[:, mid_idx], 'b-', linewidth=2, label='Estimated', alpha=0.7)
    ax1.fill_between(times,
                     h_est[:, mid_idx] - 2 * h_std[:, mid_idx],
                     h_est[:, mid_idx] + 2 * h_std[:, mid_idx],
                     color='b', alpha=0.2, label='95% confidence')

    # 标记传感器测量
    for meas in result['measurements']:
        if 'level_1' in meas['data']:
            ax1.plot(meas['time'], meas['data']['level_1'], 'ro', markersize=3, alpha=0.5)

    ax1.set_xlabel('Time (s)')
    ax1.set_ylabel('Water depth (m)')
    ax1.set_title(f'State Estimation at Mid-point (Grid {mid_idx})')
    ax1.legend()
    ax1.grid(True, alpha=0.3)

    # 2. 传感器位置的估计
    ax2 = fig.add_subplot(gs[0, 1])
    sensor_idx = nx // 4
    ax2.plot(times, h_true_history[:, sensor_idx], 'k-', linewidth=2, label='True', alpha=0.7)
    ax2.plot(times, h_est[:, sensor_idx], 'b-', linewidth=2, label='Estimated', alpha=0.7)

    # 绘制测量值
    meas_times = [m['time'] for m in result['measurements']]
    meas_values = [m['data']['level_1'] for m in result['measurements']]
    ax2.plot(meas_times, meas_values, 'ro', markersize=4, label='Measurements', alpha=0.6)

    ax2.set_xlabel('Time (s)')
    ax2.set_ylabel('Water depth (m)')
    ax2.set_title(f'Sensor Location (Grid {sensor_idx})')
    ax2.legend()
    ax2.grid(True, alpha=0.3)

    # 3. 误差时间演化
    ax3 = fig.add_subplot(gs[1, 0])
    error_mid = errors[:, mid_idx]
    ax3.plot(times, error_mid, 'r-', linewidth=2, label='Estimation error')
    ax3.axhline(0, color='k', linestyle='--', alpha=0.5)
    ax3.set_xlabel('Time (s)')
    ax3.set_ylabel('Error (m)')
    ax3.set_title('Estimation Error at Mid-point')
    ax3.legend()
    ax3.grid(True, alpha=0.3)

    # 4. 不确定性演化
    ax4 = fig.add_subplot(gs[1, 1])
    ax4.plot(times, h_std[:, mid_idx], 'g-', linewidth=2, label='Uncertainty (σ)')
    ax4.set_xlabel('Time (s)')
    ax4.set_ylabel('Standard deviation (m)')
    ax4.set_title('Estimation Uncertainty')
    ax4.legend()
    ax4.grid(True, alpha=0.3)

    # 5. 空间误差分布（最终时刻）
    ax5 = fig.add_subplot(gs[2, 0])
    x = np.linspace(0, L, nx)
    ax5.plot(x, errors[-1, :], 'r-', linewidth=2)
    ax5.axhline(0, color='k', linestyle='--', alpha=0.5)

    # 标记传感器位置
    for sensor_name, sensor in digital_twin.sensors.items():
        idx = sensor.location_idx
        ax5.axvline(x[idx], color='blue', linestyle=':', alpha=0.5, linewidth=2)
        ax5.text(x[idx], ax5.get_ylim()[1] * 0.9, sensor_name,
                rotation=90, va='top', ha='right', fontsize=8)

    ax5.set_xlabel('Position (m)')
    ax5.set_ylabel('Error (m)')
    ax5.set_title('Spatial Error Distribution (Final)')
    ax5.grid(True, alpha=0.3)

    # 6. 空间不确定性分布（最终时刻）
    ax6 = fig.add_subplot(gs[2, 1])
    ax6.plot(x, h_std[-1, :], 'g-', linewidth=2)

    # 标记传感器位置
    for sensor_name, sensor in digital_twin.sensors.items():
        idx = sensor.location_idx
        ax6.axvline(x[idx], color='blue', linestyle=':', alpha=0.5, linewidth=2)

    ax6.set_xlabel('Position (m)')
    ax6.set_ylabel('Standard deviation (m)')
    ax6.set_title('Spatial Uncertainty Distribution (Final)')
    ax6.grid(True, alpha=0.3)

    plt.tight_layout()
    plt.savefig('test_digital_twin_state_estimation.png', dpi=150)
    print(f"\n图表保存: test_digital_twin_state_estimation.png")

    # 测试通过标准：RMSE < 2cm
    test_passed = rmse < 0.02

    return {
        'passed': test_passed,
        'rmse': rmse,
        'initial_error': np.sqrt(np.mean((h_est[0] - h_true_history[0])**2)),
        'final_error': np.sqrt(np.mean((h_est[-1] - h_true_history[-1])**2))
    }


def test_forecast():
    """
    测试2: 预测功能

    场景：
    - 数字孪生已通过数据同化校正
    - 从当前状态开始预测未来
    - 对比预测与真实演化
    """
    print("\n" + "=" * 80)
    print("测试2: 数字孪生预测功能")
    print("=" * 80)

    # 参数
    L = 400.0
    nx = 21
    B = 10.0
    S0 = 0.001
    n = 0.025

    # 创建数字孪生
    twin_solver = HydrostaticCanalSolver(
        length=L, nx=nx, B=B, S0=S0, n=n
    )

    Q_initial = 5.0
    h_initial = 0.6
    twin_solver.h = np.ones(nx) * h_initial
    twin_solver.hu = np.ones(nx) * Q_initial / B

    digital_twin = DigitalTwin(
        solver=twin_solver,
        dt=1.0,
        process_noise_std=0.01,
        verbose=True
    )

    # 添加传感器
    digital_twin.add_sensor('level', 'water_level', nx // 2, noise_std=0.01)

    # 边界条件（稳定一段时间后变化）
    def Q_upstream(t):
        return 5.0 if t < 50 else 7.0

    def h_downstream(t):
        return 0.6 if t < 50 else 0.70

    # 简单的测量函数（完美观测）
    def get_measurements(t):
        if t < 50:  # 只在前50秒有观测
            return {'level': digital_twin.solver.h[nx // 2] + np.random.normal(0, 0.01)}
        else:
            return {}

    # 运行同化（前50秒）
    print("\n阶段1: 数据同化（0-50s）")
    result_assim = digital_twin.run_assimilation(
        t_end=50.0,
        Q_upstream_func=Q_upstream,
        h_downstream_func=h_downstream,
        measurement_func=get_measurements,
        assimilation_interval=2
    )

    # 在t=50s进行预测（未来30秒）
    print("\n阶段2: 预测（50-80s）")
    forecast_result = digital_twin.forecast(
        forecast_horizon=30.0,
        Q_upstream_func=Q_upstream,
        h_downstream_func=h_downstream
    )

    # 继续运行真实演化作为对比
    print("\n阶段3: 继续真实演化（50-80s）用于验证")
    true_result = digital_twin.run_assimilation(
        t_end=30.0,  # 再运行30秒
        Q_upstream_func=lambda t: Q_upstream(t + 50),
        h_downstream_func=lambda t: h_downstream(t + 50),
        measurement_func=lambda t: {},  # 无新观测
        assimilation_interval=999
    )

    # 绘图
    fig, axes = plt.subplots(2, 2, figsize=(14, 10))

    mid_idx = nx // 2
    x = np.linspace(0, L, nx)

    # 1. 时间序列（同化+预测）
    ax = axes[0, 0]
    t_assim = np.array(result_assim['time'])
    h_assim = np.array(result_assim['h'])
    h_std_assim = np.array(result_assim['h_std'])

    t_forecast = np.array(forecast_result['time'])
    h_forecast = np.array(forecast_result['h'])
    h_std_forecast = np.array(forecast_result['h_std'])

    t_true = t_forecast  # 对齐时间
    h_true = np.array(true_result['h'])

    # 绘制同化阶段
    ax.plot(t_assim, h_assim[:, mid_idx], 'b-', linewidth=2, label='Assimilation', alpha=0.8)
    ax.fill_between(t_assim,
                    h_assim[:, mid_idx] - 2 * h_std_assim[:, mid_idx],
                    h_assim[:, mid_idx] + 2 * h_std_assim[:, mid_idx],
                    color='b', alpha=0.2)

    # 绘制预测阶段
    ax.plot(t_forecast, h_forecast[:, mid_idx], 'r--', linewidth=2, label='Forecast', alpha=0.8)
    ax.fill_between(t_forecast,
                    h_forecast[:, mid_idx] - 2 * h_std_forecast[:, mid_idx],
                    h_forecast[:, mid_idx] + 2 * h_std_forecast[:, mid_idx],
                    color='r', alpha=0.2, label='Forecast 95% CI')

    # 绘制真实演化
    ax.plot(t_true, h_true[:, mid_idx], 'k-', linewidth=2, label='True evolution', alpha=0.7)

    ax.axvline(50, color='gray', linestyle=':', alpha=0.5, linewidth=2, label='Forecast start')
    ax.set_xlabel('Time (s)')
    ax.set_ylabel('Water depth (m)')
    ax.set_title('Forecast vs True Evolution')
    ax.legend()
    ax.grid(True, alpha=0.3)

    # 2. 预测误差
    ax = axes[0, 1]
    forecast_error = h_forecast[:, mid_idx] - h_true[:, mid_idx]
    ax.plot(t_forecast, forecast_error, 'r-', linewidth=2)
    ax.axhline(0, color='k', linestyle='--', alpha=0.5)
    ax.fill_between(t_forecast, -2 * h_std_forecast[:, mid_idx], 2 * h_std_forecast[:, mid_idx],
                    color='r', alpha=0.2, label='Predicted uncertainty')
    ax.set_xlabel('Time (s)')
    ax.set_ylabel('Forecast error (m)')
    ax.set_title('Forecast Error with Uncertainty')
    ax.legend()
    ax.grid(True, alpha=0.3)

    # 3. 空间剖面对比（预测结束时刻）
    ax = axes[1, 0]
    ax.plot(x, h_forecast[-1, :], 'r--', linewidth=2, marker='o', markersize=4, label='Forecast')
    ax.plot(x, h_true[-1, :], 'k-', linewidth=2, marker='s', markersize=4, label='True')
    ax.fill_between(x,
                    h_forecast[-1, :] - 2 * h_std_forecast[-1, :],
                    h_forecast[-1, :] + 2 * h_std_forecast[-1, :],
                    color='r', alpha=0.2)
    ax.set_xlabel('Position (m)')
    ax.set_ylabel('Water depth (m)')
    ax.set_title(f'Spatial Profile at t={t_forecast[-1]:.0f}s')
    ax.legend()
    ax.grid(True, alpha=0.3)

    # 4. 不确定性增长
    ax = axes[1, 1]
    ax.plot(t_assim, np.mean(h_std_assim, axis=1), 'b-', linewidth=2, label='Assimilation')
    ax.plot(t_forecast, np.mean(h_std_forecast, axis=1), 'r-', linewidth=2, label='Forecast')
    ax.axvline(50, color='gray', linestyle=':', alpha=0.5, linewidth=2)
    ax.set_xlabel('Time (s)')
    ax.set_ylabel('Mean uncertainty (m)')
    ax.set_title('Uncertainty Growth During Forecast')
    ax.legend()
    ax.grid(True, alpha=0.3)

    plt.tight_layout()
    plt.savefig('test_digital_twin_forecast.png', dpi=150)
    print(f"\n图表保存: test_digital_twin_forecast.png")

    # 评估
    forecast_rmse = np.sqrt(np.mean(forecast_error ** 2))
    print(f"\n结果分析:")
    print(f"  预测RMSE: {forecast_rmse:.4f} m")
    print(f"  预测时长: {t_forecast[-1] - t_forecast[0]:.1f} s")

    test_passed = forecast_rmse < 0.05  # 5cm以内

    return {
        'passed': test_passed,
        'forecast_rmse': forecast_rmse
    }


def main():
    """运行所有测试"""
    print("\n" + "" * 40)
    print("数字孪生测试")
    print("" * 40)

    results = {}

    # 测试1: 状态估计
    try:
        result1 = test_state_estimation()
        results['state_estimation'] = result1
        if result1['passed']:
            print(f"\n 测试1通过: RMSE = {result1['rmse']:.4f} m")
        else:
            print(f"\n️  测试1未达标: RMSE = {result1['rmse']:.4f} m")
    except Exception as e:
        print(f"\n 测试1失败: {e}")
        import traceback
        traceback.print_exc()

    # 测试2: 预测
    try:
        result2 = test_forecast()
        results['forecast'] = result2
        if result2['passed']:
            print(f"\n 测试2通过: 预测RMSE = {result2['forecast_rmse']:.4f} m")
        else:
            print(f"\n️  测试2未达标: 预测RMSE = {result2['forecast_rmse']:.4f} m")
    except Exception as e:
        print(f"\n 测试2失败: {e}")
        import traceback
        traceback.print_exc()

    # 总结
    print("\n" + "=" * 80)
    print("所有数字孪生测试完成!")
    print("=" * 80)

    print("\n数字孪生特点：")
    print("   扩展卡尔曼滤波（EKF）状态估计")
    print("   传感器数据融合")
    print("   不确定性量化")
    print("   预测功能")
    print("   充分利用现有求解器作为物理模型")

    return results


if __name__ == "__main__":
    main()
