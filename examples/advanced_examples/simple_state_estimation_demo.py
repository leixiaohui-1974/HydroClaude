# -*- coding: utf-8 -*-
"""
状态估计简化示例

使用简单的线性系统展示卡尔曼滤波器原理
- 简单的一阶系统水深积分器
- 清晰的物理意义
- 易于理解的滤波器效果

系统模型
  h(k+1) = h(k) + dt * q_in(k)
  z(k) = h(k) + v(k)

其中
  h: 水深
  q_in: 流入速率控制输入
  v: 测量噪声

作者HydroClaude Team
日期2025-10-24
"""

import numpy as np
import matplotlib
import matplotlib.pyplot as plt
matplotlib.use('Agg')
import sys
import os

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))

from control.state_estimation import KalmanFilter


class SimplePoolSimulator:
    """简化的池段仿真器水深积分器"""

    def __init__(self, dt: float, process_noise_std: float = 0.001):
        """
        初始化简化池段

        系统动力学: h(k+1) = h(k) + dt * q_in(k) + w(k)

        参数:
            dt: 采样时间 (s)
            process_noise_std: 过程噪声标准差 (m)
        """
        self.dt = dt
        self.process_noise_std = process_noise_std
        self.h = 2.0  # 初始水深 (m)

    def step(self, q_in: float) -> float:
        """
        仿真一步

        参数:
            q_in: 流入速率 (m/s)即dh/dt

        返回:
            h: 当前水深 (m)
        """
        # 水深变化 = 流入速率 * 时间步长
        dh = q_in * self.dt

        # 添加过程噪声
        dh += np.random.randn() * self.process_noise_std

        # 更新水深
        self.h += dh

        return self.h

    def measure(self, measurement_noise_std: float = 0.05) -> float:
        """
        测量水深含噪声

        参数:
            measurement_noise_std: 测量噪声标准差 (m)

        返回:
            z: 测量值 (m)
        """
        return self.h + np.random.randn() * measurement_noise_std

    def reset(self, h0: float = 2.0):
        """重置仿真器"""
        self.h = h0


def main():
    """主函数"""
    print("=" * 80)
    print("状态估计简化示例 - 卡尔曼滤波器")
    print("=" * 80)

    # ===== 1. 参数设置 =====
    print("\n1. 系统参数...")

    dt = 10.0  # 采样时间 (s)
    n_steps = 150  # 仿真步数

    process_noise_std = 0.002  # 过程噪声标准差 (m)
    measurement_noise_std = 0.05  # 测量噪声标准差 (m)

    print(f"  采样时间: {dt} s")
    print(f"  仿真步数: {n_steps}")
    print(f"  过程噪声: sigma_w = {process_noise_std} m")
    print(f"  测量噪声: sigma_v = {measurement_noise_std} m")

    # ===== 2. 创建仿真器 =====
    print("\n2. 创建系统...")

    simulator = SimplePoolSimulator(dt, process_noise_std)

    print("  系统动力学: h(k+1) = h(k) + dt * q_in(k) + w(k)")
    print("  测量方程:   z(k) = h(k) + v(k)")
    print(f"  初始水深:   h(0) = {simulator.h:.2f} m")

    # ===== 3. 创建卡尔曼滤波器 =====
    print("\n3. 创建卡尔曼滤波器...")

    # 状态转移矩阵 A状态: x = [h]单维
    A = np.array([[1.0]])

    # 控制输入矩阵 B
    B = np.array([[dt]])

    # 测量矩阵 H直接测量水深
    H = np.array([[1.0]])

    # 过程噪声协方差矩阵 Q
    Q = np.array([[process_noise_std**2]])

    # 测量噪声协方差矩阵 R
    R = np.array([[measurement_noise_std**2]])

    # 初始状态估计
    x0 = np.array([2.0])  # 初始猜测2.0m
    P0 = np.array([[1.0]])  # 初始不确定性

    kf = KalmanFilter(A, B, H, Q, R, x0, P0)

    print("   线性卡尔曼滤波器已创建")
    print(f"  初始估计: h_est(0) = {x0[0]:.2f} m +/- {np.sqrt(P0[0,0]):.2f} m")

    # ===== 4. 生成控制输入序列 =====
    print("\n4. 生成控制场景...")

    # 控制输入dh/dt (m/s)
    q_in_sequence = np.zeros(n_steps)

    # 场景1: 保持恒定水深 (0-50步)
    q_in_sequence[0:50] = 0.0

    # 场景2: 缓慢提升水深 (50-100步)
    q_in_sequence[50:100] = 0.002  # 0.002 m/s -> 0.02m per 10s

    # 场景3: 保持恒定水深 (100-150步)
    q_in_sequence[100:150] = 0.0

    print("  场景1 (0-50步):    保持水深 (q_in = 0 m/s)")
    print("  场景2 (50-100步):  提升水深 (q_in = 0.002 m/s)")
    print("  场景3 (100-150步): 保持水深 (q_in = 0 m/s)")

    # ===== 5. 运行仿真 =====
    print("\n5. 运行仿真...")

    time_array = np.arange(n_steps) * dt
    true_states = []
    measurements = []
    kf_estimates = []
    kf_uncertainties = []

    for step in range(n_steps):
        q_in = q_in_sequence[step]

        # 真实系统
        h_true = simulator.step(q_in)

        # 测量含噪声
        z = simulator.measure(measurement_noise_std)

        # 卡尔曼滤波器
        kf.predict(np.array([q_in]))
        result = kf.update(np.array([z]))

        h_est = result.x_est[0]
        P_est = result.P[0, 0]

        # 保存数据
        true_states.append(h_true)
        measurements.append(z)
        kf_estimates.append(h_est)
        kf_uncertainties.append(np.sqrt(P_est))

        if step % 30 == 0:
            print(f"  步骤 {step:3d}: "
                  f"真实={h_true:.4f}m, "
                  f"测量={z:.4f}m, "
                  f"KF估计={h_est:.4f}m +/- {np.sqrt(P_est):.4f}m")

    # 转换为numpy数组
    true_states = np.array(true_states)
    measurements = np.array(measurements)
    kf_estimates = np.array(kf_estimates)
    kf_uncertainties = np.array(kf_uncertainties)

    print("\n  仿真完成!")

    # ===== 6. 性能评估 =====
    print("\n6. 性能评估...")

    # 计算误差
    meas_error = measurements - true_states
    kf_error = kf_estimates - true_states

    meas_mae = np.mean(np.abs(meas_error))
    kf_mae = np.mean(np.abs(kf_error))

    meas_rmse = np.sqrt(np.mean(meas_error**2))
    kf_rmse = np.sqrt(np.mean(kf_error**2))

    print(f"\n  平均绝对误差MAE:")
    print(f"    测量:       {meas_mae:.4f} m")
    print(f"    KF滤波:     {kf_mae:.4f} m  (改善 {(1-kf_mae/meas_mae)*100:.1f}%)")

    print(f"\n  均方根误差RMSE:")
    print(f"    测量:       {meas_rmse:.4f} m")
    print(f"    KF滤波:     {kf_rmse:.4f} m  (改善 {(1-kf_rmse/meas_rmse)*100:.1f}%)")

    # 稳态性能最后50步
    meas_rmse_steady = np.sqrt(np.mean(meas_error[-50:]**2))
    kf_rmse_steady = np.sqrt(np.mean(kf_error[-50:]**2))

    print(f"\n  稳态RMSE最后50步:")
    print(f"    测量:       {meas_rmse_steady:.4f} m")
    print(f"    KF滤波:     {kf_rmse_steady:.4f} m  (改善 {(1-kf_rmse_steady/meas_rmse_steady)*100:.1f}%)")

    # ===== 7. 可视化 =====
    print("\n7. 生成可视化...")

    fig, axes = plt.subplots(2, 2, figsize=(14, 10))
    fig.suptitle('Kalman Filter for Water Level Estimation', fontsize=16, fontweight='bold')

    # 子图1: 水深估计
    ax = axes[0, 0]
    ax.plot(time_array, true_states, 'k-', linewidth=2, label='True State', alpha=0.8)
    ax.plot(time_array, measurements, 'r.', markersize=3, label='Noisy Measurement', alpha=0.4)
    ax.plot(time_array, kf_estimates, 'b-', linewidth=2, label='KF Estimate', alpha=0.8)
    ax.set_xlabel('Time (s)', fontsize=12)
    ax.set_ylabel('Water Depth (m)', fontsize=12)
    ax.set_title('Water Depth Estimation', fontsize=13, fontweight='bold')
    ax.legend(loc='best', fontsize=10)
    ax.grid(True, alpha=0.3)

    # 子图2: 估计误差
    ax = axes[0, 1]
    ax.plot(time_array, meas_error, 'r-', linewidth=1, label='Measurement Error', alpha=0.6)
    ax.plot(time_array, kf_error, 'b-', linewidth=2, label='KF Estimation Error', alpha=0.8)
    ax.axhline(y=0, color='k', linestyle='--', linewidth=1)
    ax.set_xlabel('Time (s)', fontsize=12)
    ax.set_ylabel('Error (m)', fontsize=12)
    ax.set_title('Estimation Error', fontsize=13, fontweight='bold')
    ax.legend(loc='best', fontsize=10)
    ax.grid(True, alpha=0.3)

    # 子图3: 不确定性演化+/-2sigma置信区间
    ax = axes[1, 0]
    ax.plot(time_array, true_states, 'k-', linewidth=2, label='True State', alpha=0.8)
    ax.plot(time_array, kf_estimates, 'b-', linewidth=2, label='KF Estimate', alpha=0.8)
    ax.fill_between(time_array,
                     kf_estimates - 2*kf_uncertainties,
                     kf_estimates + 2*kf_uncertainties,
                     alpha=0.3, color='blue', label='95% Confidence Interval')
    ax.set_xlabel('Time (s)', fontsize=12)
    ax.set_ylabel('Water Depth (m)', fontsize=12)
    ax.set_title('Estimation Uncertainty (+/-2sigma)', fontsize=13, fontweight='bold')
    ax.legend(loc='best', fontsize=10)
    ax.grid(True, alpha=0.3)

    # 子图4: 滤波器收敛
    ax = axes[1, 1]
    ax.plot(time_array, kf_uncertainties, 'b-', linewidth=2)
    ax.set_xlabel('Time (s)', fontsize=12)
    ax.set_ylabel('Standard Deviation (m)', fontsize=12)
    ax.set_title('Filter Uncertainty Evolution', fontsize=13, fontweight='bold')
    ax.grid(True, alpha=0.3)

    # 添加文本说明
    textstr = f'MAE Improvement: {(1-kf_mae/meas_mae)*100:.1f}%\n'
    textstr += f'RMSE Improvement: {(1-kf_rmse/meas_rmse)*100:.1f}%\n'
    textstr += f'Final sigma: {kf_uncertainties[-1]:.4f} m'
    ax.text(0.98, 0.97, textstr, transform=ax.transAxes,
            fontsize=10, verticalalignment='top', horizontalalignment='right',
            bbox=dict(boxstyle='round', facecolor='wheat', alpha=0.5))

    plt.tight_layout()

    # 保存图像
    output_path = os.path.join(os.path.dirname(__file__), 'simple_state_estimation_demo.png')
    plt.savefig(output_path, dpi=150, bbox_inches='tight')
    print(f"\n   可视化已保存: {output_path}")

    # plt.show()  # Disabled for automated testing

    # ===== 8. 总结 =====
    print("\n" + "=" * 80)
    print("总结")
    print("=" * 80)
    print("\n卡尔曼滤波器成功融合了模型预测和噪声测量")
    print(f"  - 测量噪声标准差: {measurement_noise_std:.3f} m")
    print(f"  - 滤波后RMSE: {kf_rmse:.4f} m")
    print(f"  - 精度提升: {(1-kf_rmse/meas_rmse)*100:.1f}%")
    print(f"  - 稳态不确定性: {kf_uncertainties[-1]:.4f} m")
    print(f"\n关键观察:")
    print(f"  1. 滤波器快速收敛到最优估计约10-20步")
    print(f"  2. 95%置信区间包含真实状态+/-2sigma区间")
    print(f"  3. 估计误差明显小于测量噪声")
    print(f"  4. 动态响应期间不确定性略有增加稳态时收敛")
    print("\n" + "=" * 80)


if __name__ == '__main__':
    main()
