# -*- coding: utf-8 -*-
"""
一阶MPC在非线性模型上的性能测试

测试目标：
1. 验证线性化MPC在非线性模型上的控制效果
2. 对比线性化模型与非线性模型的性能差异
3. 评估非线性失配的影响

非线性模型：使用非线性闸门方程Q = Cd*a*W*sqrt(2*g*Deltah)
线性化模型：工作点线性化的一阶模型H(s) = K/(taus+1)

作者：HydroClaude Team
日期：2025-10-24
"""

import numpy as np
import matplotlib.pyplot as plt
from typing import Dict
import sys
import os

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))

from examples.advanced_examples.linearized_canal_simulator import LinearizedCanalSimulator
from control.first_order_mpc import FirstOrderMPC, FirstOrderMPCConfig


def run_mpc_test(use_linear: bool, total_time: float = 800.0) -> Dict:
    """
    运行MPC控制测试

    Args:
        use_linear: True表示线性化模型，False表示非线性模型
        total_time: 仿真时间

    Returns:
        result: 测试结果字典
    """
    # 创建仿真器
    dt = 10.0
    simulator = LinearizedCanalSimulator(
        h_work=2.5,
        a_work=2.0,
        dt=dt,
        use_linear=use_linear
    )

    # 创建MPC控制器（基于线性化参数）
    K_linear, tau_linear = simulator.get_system_params()

    config = FirstOrderMPCConfig(
        prediction_horizon=15,
        control_horizon=10,
        dt=dt,
        Q=100.0,
        R=1.0,
        Qf=1000.0,
        u_min=0.1,
        u_max=4.0,
        du_max=0.5,
        solver='OSQP',
        verbose=False
    )

    controller = FirstOrderMPC(K=K_linear, tau=tau_linear, config=config)

    # 设定点
    setpoint = 2.5 + 0.3  # 2.8m

    # 扰动时间表
    disturbance_schedule = [
        (0, 20.0),
        (200, 25.0),
        (400, 18.0),
        (600, 23.0)
    ]

    # 仿真步数
    n_steps = int(total_time / dt)

    # 记录数组
    time_hist = []
    h_hist = []
    u_hist = []
    Q_in_hist = []
    error_hist = []

    current_Q_in = disturbance_schedule[0][1]

    for k in range(n_steps):
        t = k * dt

        # 更新扰动
        for t_switch, Q_new in disturbance_schedule:
            if abs(t - t_switch) < dt / 2:
                current_Q_in = Q_new
                simulator.set_disturbance(Q_new)
                break

        # 获取当前水位
        y = simulator.h

        # MPC计算控制量
        u, _ = controller.compute_control(y, setpoint)

        # 执行控制
        y_next = simulator.step(u)

        # 记录
        time_hist.append(t)
        h_hist.append(y)
        u_hist.append(u)
        Q_in_hist.append(current_Q_in)
        error_hist.append(abs(y - setpoint))

    # 计算性能指标
    h_array = np.array(h_hist)
    error_array = np.array(error_hist)

    mae = np.mean(error_array)
    rmse = np.sqrt(np.mean(error_array**2))
    max_error = np.max(error_array)

    # 计算调节时间（误差小于5%）
    settling_threshold = 0.05 * abs(setpoint - 2.5)
    settling_indices = np.where(error_array < settling_threshold)[0]
    settling_time = settling_indices[0] * dt if len(settling_indices) > 0 else total_time

    result = {
        'time': np.array(time_hist),
        'h': h_array,
        'u': np.array(u_hist),
        'Q_in': np.array(Q_in_hist),
        'error': error_array,
        'mae': mae,
        'rmse': rmse,
        'max_error': max_error,
        'settling_time': settling_time,
        'setpoint': setpoint,
        'model_type': 'Linearized' if use_linear else 'Nonlinear'
    }

    return result


def visualize_comparison(result_nonlin: Dict, result_lin: Dict):
    """可视化对比结果"""
    fig = plt.figure(figsize=(16, 10))

    # 子图1：水位对比
    ax1 = plt.subplot(2, 3, 1)
    ax1.plot(result_nonlin['time'], result_nonlin['h'], 'b-', linewidth=2, label='Nonlinear Model')
    ax1.plot(result_lin['time'], result_lin['h'], 'r--', linewidth=2, label='Linearized Model')
    ax1.axhline(result_nonlin['setpoint'], color='gray', linestyle=':', label='Setpoint')
    ax1.set_xlabel('Time (s)', fontsize=11)
    ax1.set_ylabel('Water Level (m)', fontsize=11)
    ax1.set_title('Water Level Comparison', fontsize=12, fontweight='bold')
    ax1.legend()
    ax1.grid(True, alpha=0.3)

    # 子图2：控制量对比
    ax2 = plt.subplot(2, 3, 2)
    ax2.plot(result_nonlin['time'], result_nonlin['u'], 'b-', linewidth=2, label='Nonlinear Model')
    ax2.plot(result_lin['time'], result_lin['u'], 'r--', linewidth=2, label='Linearized Model')
    ax2.set_xlabel('Time (s)', fontsize=11)
    ax2.set_ylabel('Gate Opening (m)', fontsize=11)
    ax2.set_title('Control Input Comparison', fontsize=12, fontweight='bold')
    ax2.legend()
    ax2.grid(True, alpha=0.3)

    # 子图3：误差对比
    ax3 = plt.subplot(2, 3, 3)
    ax3.plot(result_nonlin['time'], result_nonlin['error'] * 100, 'b-', linewidth=2, label='Nonlinear Model')
    ax3.plot(result_lin['time'], result_lin['error'] * 100, 'r--', linewidth=2, label='Linearized Model')
    ax3.set_xlabel('Time (s)', fontsize=11)
    ax3.set_ylabel('Absolute Error (cm)', fontsize=11)
    ax3.set_title('Tracking Error Comparison', fontsize=12, fontweight='bold')
    ax3.legend()
    ax3.grid(True, alpha=0.3)

    # 子图4：扰动
    ax4 = plt.subplot(2, 3, 4)
    ax4.step(result_nonlin['time'], result_nonlin['Q_in'], 'g-', linewidth=2, where='post')
    ax4.set_xlabel('Time (s)', fontsize=11)
    ax4.set_ylabel('Inflow (m^3/s)', fontsize=11)
    ax4.set_title('Disturbance (Inflow)', fontsize=12, fontweight='bold')
    ax4.grid(True, alpha=0.3)

    # 子图5：性能指标对比
    ax5 = plt.subplot(2, 3, 5)
    metrics = ['MAE\n(cm)', 'RMSE\n(cm)', 'Max Error\n(cm)', 'Settling\nTime (s)']
    nonlin_values = [result_nonlin['mae']*100, result_nonlin['rmse']*100,
                     result_nonlin['max_error']*100, result_nonlin['settling_time']]
    lin_values = [result_lin['mae']*100, result_lin['rmse']*100,
                  result_lin['max_error']*100, result_lin['settling_time']]

    x = np.arange(len(metrics))
    width = 0.35

    ax5.bar(x - width/2, nonlin_values, width, label='Nonlinear', color='blue', alpha=0.7)
    ax5.bar(x + width/2, lin_values, width, label='Linearized', color='red', alpha=0.7)
    ax5.set_xticks(x)
    ax5.set_xticklabels(metrics, fontsize=9)
    ax5.set_ylabel('Value', fontsize=11)
    ax5.set_title('Performance Metrics Comparison', fontsize=12, fontweight='bold')
    ax5.legend()
    ax5.grid(True, alpha=0.3, axis='y')

    # 子图6：模型失配分析
    ax6 = plt.subplot(2, 3, 6)
    h_diff = (result_nonlin['h'] - result_lin['h']) * 100  # cm
    u_diff = (result_nonlin['u'] - result_lin['u']) * 100  # cm

    ax6_twin = ax6.twinx()
    line1 = ax6.plot(result_nonlin['time'], h_diff, 'b-', linewidth=2, label='Water Level Diff')
    line2 = ax6_twin.plot(result_nonlin['time'], u_diff, 'r-', linewidth=2, label='Control Diff')

    ax6.set_xlabel('Time (s)', fontsize=11)
    ax6.set_ylabel('Water Level Difference (cm)', fontsize=11, color='b')
    ax6_twin.set_ylabel('Gate Opening Difference (cm)', fontsize=11, color='r')
    ax6.set_title('Nonlinearity Effect Analysis', fontsize=12, fontweight='bold')
    ax6.tick_params(axis='y', labelcolor='b')
    ax6_twin.tick_params(axis='y', labelcolor='r')
    ax6.grid(True, alpha=0.3)

    # 添加图例
    lines = line1 + line2
    labels = [l.get_label() for l in lines]
    ax6.legend(lines, labels, loc='upper right')

    plt.tight_layout()
    plt.savefig('mpc_nonlinear_comparison.png', dpi=150, bbox_inches='tight')
    print(f" 图片已保存: mpc_nonlinear_comparison.png")


def print_summary(result_nonlin: Dict, result_lin: Dict):
    """打印性能总结"""
    print("\n" + "="*80)
    print("MPC在非线性模型上的性能测试总结")
    print("="*80)

    print("\n【测试1】非线性模型（非线性闸门方程）")
    print("-" * 80)
    print(f"  MAE           = {result_nonlin['mae']*100:.2f} cm")
    print(f"  RMSE          = {result_nonlin['rmse']*100:.2f} cm")
    print(f"  最大误差      = {result_nonlin['max_error']*100:.2f} cm")
    print(f"  调节时间      = {result_nonlin['settling_time']:.1f} s")

    print("\n【测试2】线性化模型（基准）")
    print("-" * 80)
    print(f"  MAE           = {result_lin['mae']*100:.2f} cm")
    print(f"  RMSE          = {result_lin['rmse']*100:.2f} cm")
    print(f"  最大误差      = {result_lin['max_error']*100:.2f} cm")
    print(f"  调节时间      = {result_lin['settling_time']:.1f} s")

    print("\n【非线性失配影响分析】")
    print("-" * 80)
    mae_diff = (result_nonlin['mae'] - result_lin['mae']) * 100
    mae_diff_pct = (mae_diff / (result_lin['mae']*100)) * 100 if result_lin['mae'] > 0 else 0

    rmse_diff = (result_nonlin['rmse'] - result_lin['rmse']) * 100
    settling_diff = result_nonlin['settling_time'] - result_lin['settling_time']

    print(f"  MAE增加       = {mae_diff:+.2f} cm ({mae_diff_pct:+.1f}%)")
    print(f"  RMSE增加      = {rmse_diff:+.2f} cm")
    print(f"  调节时间变化  = {settling_diff:+.1f} s")

    # 判定
    if abs(mae_diff_pct) < 10:
        verdict = " 优秀：非线性失配影响极小（<10%）"
    elif abs(mae_diff_pct) < 20:
        verdict = "⭕ 良好：非线性失配影响可接受（10-20%）"
    elif abs(mae_diff_pct) < 30:
        verdict = "  一般：非线性失配影响较大（20-30%）"
    else:
        verdict = " 较差：非线性失配影响显著（>30%）"

    print(f"\n  综合评价：{verdict}")

    print("\n【关键发现】")
    print("-" * 80)
    if abs(mae_diff_pct) < 15:
        print("   线性化假设在工作点附近有效")
        print("   一阶MPC可直接应用于非线性系统")
        print("   控制性能基本不受非线性影响")
    else:
        print("    非线性效应不可忽略")
        print("   建议：考虑增益调度或多工作点MPC")

    print("\n" + "="*80)


def main():
    """主测试函数"""
    print("="*80)
    print("一阶MPC在非线性模型上的性能测试")
    print("="*80)
    print("\n测试配置：")
    print("  - 控制器: 一阶MPC (K=-0.3, tau=206s)")
    print("  - 非线性模型: 非线性闸门方程 + 水量平衡ODE")
    print("  - 线性化模型: 工作点线性化的一阶模型")
    print("  - 仿真时间: 800s")
    print("  - 扰动: 4次阶跃变化 (20->25->18->23 m^3/s)")
    print("\n开始测试...\n")

    print("【步骤1】运行非线性模型测试...")
    result_nonlin = run_mpc_test(use_linear=False)
    print(f"   非线性模型测试完成 - MAE = {result_nonlin['mae']*100:.2f} cm")

    print("\n【步骤2】运行线性化模型测试...")
    result_lin = run_mpc_test(use_linear=True)
    print(f"   线性化模型测试完成 - MAE = {result_lin['mae']*100:.2f} cm")

    print("\n【步骤3】生成对比可视化...")
    visualize_comparison(result_nonlin, result_lin)

    # 打印详细总结
    print_summary(result_nonlin, result_lin)

    print("\n测试完成！")


if __name__ == "__main__":
    main()
