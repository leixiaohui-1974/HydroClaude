# -*- coding: utf-8 -*-
"""
鲁棒控制策略演示

对比不同控制策略在扰动和不确定性下的鲁棒性
1. PID控制器
2. 滑模控制SMC
3. 自适应滑模控制Adaptive SMC

测试场景
- 阶跃参考跟踪
- 阶跃扰动
- 参数不确定性

性能指标
- 跟踪误差
- 控制平滑度
- 扰动抑制能力

作者HydroClaude Team
日期2025-10-24
"""

import numpy as np
import warnings
warnings.filterwarnings("ignore")
import matplotlib
import matplotlib.pyplot as plt
matplotlib.use('Agg')
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from control.robust_control import (
    SlidingModeController, AdaptiveSlidingModeController,
    RobustPIDController, SMCParameters,
    design_smc_parameters, create_canal_smc
)


class CanalSystemWithDisturbance:
    """带扰动的渠道系统仿真"""

    def __init__(self, dt: float, nominal_gain: float = 1.0):
        """
        初始化

        系统模型: h(k+1) = h(k) + K * u(k) * dt + d(k)

        参数:
            dt: 采样时间
            nominal_gain: 标称增益
        """
        self.dt = dt
        self.nominal_gain = nominal_gain
        self.h = 2.0  # 初始水深

        # 系统参数不确定性可变
        self.actual_gain = nominal_gain

    def step(self, u: float, disturbance: float = 0.0) -> float:
        """
        仿真一步

        参数:
            u: 控制输入
            disturbance: 外部扰动

        返回:
            h: 当前水深
        """
        # 系统动力学带不确定性和扰动
        dh = self.actual_gain * u * self.dt + disturbance

        # 更新水深
        self.h += dh

        # 限制水深范围
        self.h = np.clip(self.h, 0.5, 5.0)

        return self.h

    def set_gain_uncertainty(self, gain: float):
        """设置增益不确定性"""
        self.actual_gain = gain

    def reset(self, h0: float = 2.0):
        """重置"""
        self.h = h0
        self.actual_gain = self.nominal_gain


def main():
    """主函数"""
    print("=" * 80)
    print("鲁棒控制策略演示")
    print("=" * 80)

    # ===== 1. 参数设置 =====
    print("\n1. 系统参数...")

    dt = 0.5  # 采样时间 (s)
    n_steps = 400  # 仿真步数

    nominal_gain = 1.0  # 标称增益

    print(f"  采样时间: {dt} s")
    print(f"  仿真步数: {n_steps}")
    print(f"  标称增益: {nominal_gain}")

    # ===== 2. 创建控制器 =====
    print("\n2. 创建控制器...")

    # PID控制器
    pid = RobustPIDController(
        kp=0.8,
        ki=0.2,
        kd=0.1,
        dt=dt,
        u_min=-0.5,
        u_max=0.5
    )

    # 滑模控制器
    smc_params = SMCParameters(
        lambda_=2.0,   # 滑模面参数
        eta=0.3,       # 趋近律增益
        epsilon=0.05,  # 边界层厚度
        u_min=-0.5,
        u_max=0.5
    )
    smc = SlidingModeController(smc_params, dt)

    # 自适应滑模控制器
    asmc = AdaptiveSlidingModeController(
        smc_params,
        dt,
        adaptation_gain=0.5
    )

    print("   PID控制器")
    print("   滑模控制器SMC")
    print("   自适应滑模控制器ASMC")

    # ===== 3. 生成测试场景 =====
    print("\n3. 测试场景...")

    # 参考轨迹
    reference = np.zeros(n_steps)
    reference[0:100] = 2.0
    reference[100:200] = 3.0  # 阶跃参考
    reference[200:300] = 2.5
    reference[300:400] = 3.2

    # 扰动序列
    disturbance = np.zeros(n_steps)
    disturbance[150:180] = 0.02  # 阶跃扰动1
    disturbance[250:280] = -0.015  # 阶跃扰动2

    # 增益不确定性变化
    gain_uncertainty = np.ones(n_steps) * nominal_gain
    gain_uncertainty[180:250] = nominal_gain * 0.7  # 30%增益下降

    print("  场景1 (0-100):    恒定参考 r=2.0m")
    print("  场景2 (100-200):  阶跃参考 r=3.0m")
    print("  场景3 (150-180):  阶跃扰动 d=0.02")
    print("  场景4 (180-250):  增益下降 30%")
    print("  场景5 (250-280):  阶跃扰动 d=-0.015")
    print("  场景6 (300-400):  阶跃参考 r=3.2m")

    # ===== 4. 运行仿真对比 =====
    print("\n4. 运行仿真对比...")

    # 仿真1: PID
    print("\n  场景1: PID控制")
    sys_pid = CanalSystemWithDisturbance(dt, nominal_gain)
    h_pid = []
    u_pid = []

    for step in range(n_steps):
        h = sys_pid.h
        r = reference[step]
        d = disturbance[step]
        sys_pid.set_gain_uncertainty(gain_uncertainty[step])

        u = pid.compute_control(r, h)
        h_next = sys_pid.step(u, d)

        h_pid.append(h)
        u_pid.append(u)

        if step % 80 == 0:
            print(f"    步骤 {step}: h={h:.3f}m, u={u:.4f}")

    # 仿真2: SMC
    print("\n  场景2: 滑模控制")
    sys_smc = CanalSystemWithDisturbance(dt, nominal_gain)
    h_smc = []
    u_smc = []

    for step in range(n_steps):
        h = sys_smc.h
        r = reference[step]
        d = disturbance[step]
        sys_smc.set_gain_uncertainty(gain_uncertainty[step])

        u = smc.compute_control(h, r, dx_ref=0.0)
        h_next = sys_smc.step(u, d)

        h_smc.append(h)
        u_smc.append(u)

        if step % 80 == 0:
            print(f"    步骤 {step}: h={h:.3f}m, u={u:.4f}, s={smc.s:.4f}")

    # 仿真3: Adaptive SMC
    print("\n  场景3: 自适应滑模控制")
    sys_asmc = CanalSystemWithDisturbance(dt, nominal_gain)
    h_asmc = []
    u_asmc = []

    for step in range(n_steps):
        h = sys_asmc.h
        r = reference[step]
        d = disturbance[step]
        sys_asmc.set_gain_uncertainty(gain_uncertainty[step])

        u = asmc.compute_control(h, r, dx_ref=0.0)
        h_next = sys_asmc.step(u, d)

        h_asmc.append(h)
        u_asmc.append(u)

        if step % 80 == 0:
            eta_adaptive = asmc.history_eta[-1] if asmc.history_eta else asmc.params.eta
            print(f"    步骤 {step}: h={h:.3f}m, u={u:.4f}, ={eta_adaptive:.4f}")

    # 转换为numpy数组
    time_array = np.arange(n_steps) * dt
    h_pid = np.array(h_pid)
    u_pid = np.array(u_pid)
    h_smc = np.array(h_smc)
    u_smc = np.array(u_smc)
    h_asmc = np.array(h_asmc)
    u_asmc = np.array(u_asmc)

    print("\n  仿真完成!")

    # ===== 5. 性能评估 =====
    print("\n5. 性能评估...")

    # 跟踪误差
    e_pid = h_pid - reference
    e_smc = h_smc - reference
    e_asmc = h_asmc - reference

    mae_pid = np.mean(np.abs(e_pid))
    mae_smc = np.mean(np.abs(e_smc))
    mae_asmc = np.mean(np.abs(e_asmc))

    rmse_pid = np.sqrt(np.mean(e_pid**2))
    rmse_smc = np.sqrt(np.mean(e_smc**2))
    rmse_asmc = np.sqrt(np.mean(e_asmc**2))

    # 控制平滑度
    smoothness_pid = np.sum(np.abs(np.diff(u_pid)))
    smoothness_smc = np.sum(np.abs(np.diff(u_smc)))
    smoothness_asmc = np.sum(np.abs(np.diff(u_asmc)))

    # 扰动抑制能力扰动期间的误差
    disturbance_periods = (disturbance != 0)
    if np.any(disturbance_periods):
        mae_pid_dist = np.mean(np.abs(e_pid[disturbance_periods]))
        mae_smc_dist = np.mean(np.abs(e_smc[disturbance_periods]))
        mae_asmc_dist = np.mean(np.abs(e_asmc[disturbance_periods]))
    else:
        mae_pid_dist = mae_smc_dist = mae_asmc_dist = 0.0

    print("\n  跟踪性能:")
    print(f"    PID:  MAE={mae_pid:.4f}m, RMSE={rmse_pid:.4f}m")
    print(f"    SMC:  MAE={mae_smc:.4f}m, RMSE={rmse_smc:.4f}m")
    print(f"    ASMC: MAE={mae_asmc:.4f}m, RMSE={rmse_asmc:.4f}m")

    print("\n  控制平滑度总变化量:")
    print(f"    PID:  {smoothness_pid:.4f}")
    print(f"    SMC:  {smoothness_smc:.4f}")
    print(f"    ASMC: {smoothness_asmc:.4f}")

    print("\n  扰动抑制能力扰动期间MAE:")
    print(f"    PID:  {mae_pid_dist:.4f}m")
    print(f"    SMC:  {mae_smc_dist:.4f}m")
    print(f"    ASMC: {mae_asmc_dist:.4f}m")

    # ===== 6. 可视化 =====
    print("\n6. 生成可视化...")

    fig, axes = plt.subplots(3, 2, figsize=(15, 12))
    fig.suptitle('Robust Control Comparison', fontsize=16, fontweight='bold')

    # 子图1: 水深跟踪
    ax = axes[0, 0]
    ax.plot(time_array, reference, 'k--', linewidth=2, label='Reference', alpha=0.8)
    ax.plot(time_array, h_pid, 'b-', linewidth=1.5, label='PID', alpha=0.7)
    ax.plot(time_array, h_smc, 'r-', linewidth=1.5, label='SMC', alpha=0.7)
    ax.plot(time_array, h_asmc, 'g-', linewidth=1.5, label='ASMC', alpha=0.7)
    ax.set_xlabel('Time (s)', fontsize=11)
    ax.set_ylabel('Water Depth (m)', fontsize=11)
    ax.set_title('Water Depth Tracking', fontsize=12, fontweight='bold')
    ax.legend(loc='best', fontsize=9)
    ax.grid(True, alpha=0.3)

    # 子图2: 跟踪误差
    ax = axes[0, 1]
    ax.plot(time_array, e_pid, 'b-', linewidth=1.5, label='PID', alpha=0.7)
    ax.plot(time_array, e_smc, 'r-', linewidth=1.5, label='SMC', alpha=0.7)
    ax.plot(time_array, e_asmc, 'g-', linewidth=1.5, label='ASMC', alpha=0.7)
    ax.axhline(y=0, color='k', linestyle='--', linewidth=1)
    ax.set_xlabel('Time (s)', fontsize=11)
    ax.set_ylabel('Tracking Error (m)', fontsize=11)
    ax.set_title('Tracking Error', fontsize=12, fontweight='bold')
    ax.legend(loc='best', fontsize=9)
    ax.grid(True, alpha=0.3)

    # 子图3: 控制输入
    ax = axes[1, 0]
    ax.plot(time_array, u_pid, 'b-', linewidth=1.5, label='PID', alpha=0.7)
    ax.plot(time_array, u_smc, 'r-', linewidth=1.5, label='SMC', alpha=0.7)
    ax.plot(time_array, u_asmc, 'g-', linewidth=1.5, label='ASMC', alpha=0.7)
    ax.set_xlabel('Time (s)', fontsize=11)
    ax.set_ylabel('Control Input', fontsize=11)
    ax.set_title('Control Input', fontsize=12, fontweight='bold')
    ax.legend(loc='best', fontsize=9)
    ax.grid(True, alpha=0.3)

    # 子图4: 扰动和增益不确定性
    ax = axes[1, 1]
    ax2 = ax.twinx()
    ax.plot(time_array, disturbance, 'r-', linewidth=2, label='Disturbance', alpha=0.7)
    ax2.plot(time_array, gain_uncertainty / nominal_gain, 'b--',
            linewidth=2, label='Gain Ratio', alpha=0.7)
    ax.set_xlabel('Time (s)', fontsize=11)
    ax.set_ylabel('Disturbance', fontsize=11, color='r')
    ax2.set_ylabel('Gain Ratio', fontsize=11, color='b')
    ax.set_title('Disturbances and Uncertainty', fontsize=12, fontweight='bold')
    ax.tick_params(axis='y', labelcolor='r')
    ax2.tick_params(axis='y', labelcolor='b')
    ax.grid(True, alpha=0.3)

    # 子图5: 滑模面SMC
    ax = axes[2, 0]
    s_smc = np.array(smc.history_s)
    s_asmc = np.array(asmc.history_s)
    ax.plot(time_array, s_smc, 'r-', linewidth=1.5, label='SMC', alpha=0.7)
    ax.plot(time_array, s_asmc, 'g-', linewidth=1.5, label='ASMC', alpha=0.7)
    ax.axhline(y=0, color='k', linestyle='--', linewidth=1)
    ax.axhline(y=smc_params.epsilon, color='gray', linestyle=':', linewidth=1, label='Boundary Layer')
    ax.axhline(y=-smc_params.epsilon, color='gray', linestyle=':', linewidth=1)
    ax.set_xlabel('Time (s)', fontsize=11)
    ax.set_ylabel('Sliding Surface s', fontsize=11)
    ax.set_title('Sliding Surface Evolution', fontsize=12, fontweight='bold')
    ax.legend(loc='best', fontsize=9)
    ax.grid(True, alpha=0.3)

    # 子图6: 性能对比柱状图
    ax = axes[2, 1]
    categories = ['MAE', 'RMSE', 'Smoothness', 'Disturbance\nRejection']
    pid_values = [mae_pid, rmse_pid, smoothness_pid/10, mae_pid_dist]
    smc_values = [mae_smc, rmse_smc, smoothness_smc/10, mae_smc_dist]
    asmc_values = [mae_asmc, rmse_asmc, smoothness_asmc/10, mae_asmc_dist]

    x = np.arange(len(categories))
    width = 0.25

    bars1 = ax.bar(x - width, pid_values, width, label='PID',
                   color='blue', alpha=0.7, edgecolor='black')
    bars2 = ax.bar(x, smc_values, width, label='SMC',
                   color='red', alpha=0.7, edgecolor='black')
    bars3 = ax.bar(x + width, asmc_values, width, label='ASMC',
                   color='green', alpha=0.7, edgecolor='black')

    ax.set_ylabel('Value', fontsize=11)
    ax.set_title('Performance Comparison', fontsize=12, fontweight='bold')
    ax.set_xticks(x)
    ax.set_xticklabels(categories, fontsize=9)
    ax.legend(fontsize=10)
    ax.grid(True, alpha=0.3, axis='y')

    plt.tight_layout()

    # 保存图像
    output_path = os.path.join(os.path.dirname(__file__), 'robust_control_demo.png')
    plt.savefig(output_path, dpi=150, bbox_inches='tight')
    print(f"\n   可视化已保存: {output_path}")

    # plt.show()  # Disabled for automated testing

    # ===== 7. 总结 =====
    print("\n" + "=" * 80)
    print("总结")
    print("=" * 80)
    print("\n鲁棒控制策略对比:")
    print(f"\n1. PID控制器:")
    print(f"   - 优点: 简单平滑")
    print(f"   - 缺点: 对扰动和不确定性敏感")
    print(f"   - MAE: {mae_pid:.4f}m, 扰动抑制: {mae_pid_dist:.4f}m")
    print(f"\n2. 滑模控制SMC:")
    print(f"   - 优点: 鲁棒性强对扰动不敏感")
    print(f"   - 缺点: 可能有抖振")
    print(f"   - MAE: {mae_smc:.4f}m, 扰动抑制: {mae_smc_dist:.4f}m")
    print(f"\n3. 自适应滑模控制ASMC:")
    print(f"   - 优点: 自适应调整最佳鲁棒性")
    print(f"   - 缺点: 计算复杂度略高")
    print(f"   - MAE: {mae_asmc:.4f}m, 扰动抑制: {mae_asmc_dist:.4f}m")
    print(f"\n关键观察:")
    print(f"  - 滑模控制在扰动和不确定性下表现更好")
    print(f"  - 自适应滑模控制能自动调整增益以适应变化")
    print(f"  - 边界层有效抑制了抖振")
    print("=" * 80)


if __name__ == '__main__':
    main()
