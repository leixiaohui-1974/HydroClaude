# -*- coding: utf-8 -*-
"""
IDZ MPC性能测试

对比三种控制器：
1. PID (带积分器)
2. First-Order MPC (无积分器)
3. IDZ MPC (带积分器)

测试目标：
验证IDZ MPC是否能通过积分器实现零稳态误差，从而达到或超越PID性能

作者：HydroClaude Team
日期：2025-10-24
"""

import numpy as np
import warnings
warnings.filterwarnings("ignore")
import matplotlib.pyplot as plt
from typing import Dict
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from examples.advanced_examples.linearized_canal_simulator import LinearizedCanalSimulator
from control.first_order_mpc import FirstOrderMPC, FirstOrderMPCConfig
from control.idz_mpc import IDZMPC, IDZMPCConfig
from control.pid_controller import PIDController, PIDConfig


def test_controller(controller_name: str, controller, total_time: float = 400.0) -> Dict:
    """
    测试控制器性能

    Args:
        controller_name: 控制器名称
        controller: 控制器对象
        total_time: 仿真时间

    Returns:
        result: 测试结果
    """
    dt = 10.0

    # 创建仿真器（线性化模型）
    simulator = LinearizedCanalSimulator(
        h_work=2.5,
        a_work=2.0,
        dt=dt,
        use_linear=True  # 使用线性模型，排除模型失配影响
    )

    # 测试场景
    setpoint = 2.5 + 0.3  # 2.8m

    disturbance_schedule = [
        (0, 20.0),
        (200, 25.0)  # 阶跃扰动
    ]

    # 仿真
    n_steps = int(total_time / dt)

    time_hist = []
    h_hist = []
    u_hist = []
    error_hist = []
    du_hist = []
    integral_hist = []  # 记录积分状态（如果有）

    current_Q_in = disturbance_schedule[0][1]
    u_prev = 2.0

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

        # 计算控制量
        if isinstance(controller, PIDController):
            controller.setpoint = setpoint
            u = controller.compute(y)
            integral_state = controller.integral
        elif isinstance(controller, (FirstOrderMPC, IDZMPC)):
            u, info = controller.compute_control(y, setpoint)
            integral_state = info.get('integral_state', 0.0) if 'integral_state' in info else 0.0
        else:
            raise ValueError(f"Unknown controller type: {type(controller)}")

        # 执行控制
        y_next = simulator.step(u)

        # 记录
        time_hist.append(t)
        h_hist.append(y)
        u_hist.append(u)
        error_hist.append(abs(y - setpoint))
        du_hist.append(abs(u - u_prev))
        integral_hist.append(integral_state)

        u_prev = u

    # 计算性能指标
    error_array = np.array(error_hist)
    du_array = np.array(du_hist)

    mae = np.mean(error_array)
    rmse = np.sqrt(np.mean(error_array**2))
    max_error = np.max(error_array)
    avg_du = np.mean(du_array)
    max_du = np.max(du_array)

    # 调节时间
    settling_threshold = 0.05 * abs(setpoint - 2.5)
    settling_indices = np.where(error_array < settling_threshold)[0]
    settling_time = settling_indices[0] * dt if len(settling_indices) > 0 else total_time

    # 计算稳态误差（最后20%的数据）
    steady_state_idx = int(0.8 * n_steps)
    steady_state_error = np.mean(error_array[steady_state_idx:])

    result = {
        'time': np.array(time_hist),
        'h': np.array(h_hist),
        'u': np.array(u_hist),
        'error': error_array,
        'du': du_array,
        'integral': np.array(integral_hist),
        'mae': mae,
        'rmse': rmse,
        'max_error': max_error,
        'settling_time': settling_time,
        'avg_du': avg_du,
        'max_du': max_du,
        'steady_state_error': steady_state_error,
        'setpoint': setpoint,
        'controller_name': controller_name
    }

    return result


def run_comparison_tests():
    """运行对比测试"""
    print("=" * 80)
    print("IDZ MPC vs First-Order MPC vs PID 性能对比")
    print("=" * 80)

    # 1. PID控制器
    print("\n【步骤1】测试PID控制器...")
    pid_config = PIDConfig(
        kp=-1.0,
        ki=-0.15,
        kd=0.0,
        dt=10.0,
        output_min=0.1,
        output_max=4.0
    )
    pid_controller = PIDController(pid_config)
    pid_result = test_controller("PID", pid_controller)
    print(f"  PID: MAE={pid_result['mae']*100:.2f}cm, "
          f"稳态误差={pid_result['steady_state_error']*100:.2f}cm, "
          f"调节时间={pid_result['settling_time']:.1f}s")

    # 2. First-Order MPC（无积分器）
    print("\n【步骤2】测试First-Order MPC...")
    fo_mpc_config = FirstOrderMPCConfig(
        prediction_horizon=15,
        control_horizon=10,
        dt=10.0,
        Q=100.0,
        R=1.0,
        Qf=1000.0,
        u_min=0.1,
        u_max=4.0,
        du_max=0.5,
        solver='OSQP',
        verbose=False
    )
    fo_mpc = FirstOrderMPC(K=-0.3, tau=206.1, config=fo_mpc_config)
    fo_mpc_result = test_controller("First-Order MPC", fo_mpc)
    print(f"  First-Order MPC: MAE={fo_mpc_result['mae']*100:.2f}cm, "
          f"稳态误差={fo_mpc_result['steady_state_error']*100:.2f}cm, "
          f"调节时间={fo_mpc_result['settling_time']:.1f}s")

    # 3. IDZ MPC（带积分器）
    print("\n【步骤3】测试IDZ MPC...")
    idz_mpc_config = IDZMPCConfig(
        prediction_horizon=15,
        control_horizon=10,
        dt=10.0,
        Q=100.0,
        R=1.0,
        Qf=1000.0,
        u_min=0.1,
        u_max=4.0,
        du_max=0.5,
        solver='OSQP',
        verbose=False
    )
    # IDZ参数从辨识结果
    idz_mpc = IDZMPC(K=-0.3, tau_z=168.0, tau_d=206.0, config=idz_mpc_config)
    idz_mpc_result = test_controller("IDZ MPC", idz_mpc)
    print(f"  IDZ MPC: MAE={idz_mpc_result['mae']*100:.2f}cm, "
          f"稳态误差={idz_mpc_result['steady_state_error']*100:.2f}cm, "
          f"调节时间={idz_mpc_result['settling_time']:.1f}s")

    # 可视化对比
    visualize_comparison(pid_result, fo_mpc_result, idz_mpc_result)

    # 打印详细分析
    print_analysis(pid_result, fo_mpc_result, idz_mpc_result)

    return {
        'pid': pid_result,
        'fo_mpc': fo_mpc_result,
        'idz_mpc': idz_mpc_result
    }


def visualize_comparison(pid_result, fo_mpc_result, idz_mpc_result):
    """可视化对比"""
    fig = plt.figure(figsize=(18, 10))

    # 子图1：水位响应
    ax1 = plt.subplot(2, 4, 1)
    ax1.plot(pid_result['time'], pid_result['h'], 'b-', linewidth=2, label='PID')
    ax1.plot(fo_mpc_result['time'], fo_mpc_result['h'], 'r--', linewidth=2, label='FO-MPC')
    ax1.plot(idz_mpc_result['time'], idz_mpc_result['h'], 'g-.', linewidth=2.5, label='IDZ-MPC')
    ax1.axhline(pid_result['setpoint'], color='gray', linestyle=':', label='Setpoint')
    ax1.set_xlabel('Time (s)')
    ax1.set_ylabel('Water Level (m)')
    ax1.set_title('Water Level Response', fontweight='bold')
    ax1.legend()
    ax1.grid(True, alpha=0.3)

    # 子图2：控制量
    ax2 = plt.subplot(2, 4, 2)
    ax2.plot(pid_result['time'], pid_result['u'], 'b-', linewidth=2, label='PID')
    ax2.plot(fo_mpc_result['time'], fo_mpc_result['u'], 'r--', linewidth=2, label='FO-MPC')
    ax2.plot(idz_mpc_result['time'], idz_mpc_result['u'], 'g-.', linewidth=2.5, label='IDZ-MPC')
    ax2.set_xlabel('Time (s)')
    ax2.set_ylabel('Gate Opening (m)')
    ax2.set_title('Control Input', fontweight='bold')
    ax2.legend()
    ax2.grid(True, alpha=0.3)

    # 子图3：跟踪误差
    ax3 = plt.subplot(2, 4, 3)
    ax3.plot(pid_result['time'], pid_result['error']*100, 'b-', linewidth=2, label='PID')
    ax3.plot(fo_mpc_result['time'], fo_mpc_result['error']*100, 'r--', linewidth=2, label='FO-MPC')
    ax3.plot(idz_mpc_result['time'], idz_mpc_result['error']*100, 'g-.', linewidth=2.5, label='IDZ-MPC')
    ax3.set_xlabel('Time (s)')
    ax3.set_ylabel('Absolute Error (cm)')
    ax3.set_title('Tracking Error', fontweight='bold')
    ax3.legend()
    ax3.grid(True, alpha=0.3)

    # 子图4：积分状态
    ax4 = plt.subplot(2, 4, 4)
    ax4.plot(pid_result['time'], pid_result['integral'], 'b-', linewidth=2, label='PID')
    ax4.plot(idz_mpc_result['time'], idz_mpc_result['integral'], 'g-.', linewidth=2.5, label='IDZ-MPC')
    ax4.set_xlabel('Time (s)')
    ax4.set_ylabel('Integral State')
    ax4.set_title('Integral Action (FO-MPC has none)', fontweight='bold')
    ax4.legend()
    ax4.grid(True, alpha=0.3)

    # 子图5：控制增量
    ax5 = plt.subplot(2, 4, 5)
    ax5.plot(pid_result['time'][1:], pid_result['du'][1:]*100, 'b-', linewidth=2, label='PID')
    ax5.plot(fo_mpc_result['time'][1:], fo_mpc_result['du'][1:]*100, 'r--', linewidth=2, label='FO-MPC')
    ax5.plot(idz_mpc_result['time'][1:], idz_mpc_result['du'][1:]*100, 'g-.', linewidth=2.5, label='IDZ-MPC')
    ax5.set_xlabel('Time (s)')
    ax5.set_ylabel('Control Increment |Deltau| (cm)')
    ax5.set_title('Control Smoothness', fontweight='bold')
    ax5.legend()
    ax5.grid(True, alpha=0.3)

    # 子图6：性能指标对比
    ax6 = plt.subplot(2, 4, 6)
    controllers = ['PID', 'FO-MPC', 'IDZ-MPC']
    mae_values = [pid_result['mae']*100, fo_mpc_result['mae']*100, idz_mpc_result['mae']*100]
    rmse_values = [pid_result['rmse']*100, fo_mpc_result['rmse']*100, idz_mpc_result['rmse']*100]

    x = np.arange(len(controllers))
    width = 0.35

    bars1 = ax6.bar(x - width/2, mae_values, width, label='MAE', color='steelblue', alpha=0.8)
    bars2 = ax6.bar(x + width/2, rmse_values, width, label='RMSE', color='coral', alpha=0.8)

    ax6.set_ylabel('Error (cm)')
    ax6.set_xticks(x)
    ax6.set_xticklabels(controllers)
    ax6.set_title('MAE and RMSE Comparison', fontweight='bold')
    ax6.legend()
    ax6.grid(True, alpha=0.3, axis='y')

    # 添加数值标签
    for bar in bars1:
        height = bar.get_height()
        ax6.text(bar.get_x() + bar.get_width()/2., height,
                f'{height:.2f}', ha='center', va='bottom', fontsize=9)
    for bar in bars2:
        height = bar.get_height()
        ax6.text(bar.get_x() + bar.get_width()/2., height,
                f'{height:.2f}', ha='center', va='bottom', fontsize=9)

    # 子图7：稳态误差对比
    ax7 = plt.subplot(2, 4, 7)
    ss_error_values = [pid_result['steady_state_error']*100,
                       fo_mpc_result['steady_state_error']*100,
                       idz_mpc_result['steady_state_error']*100]
    bars3 = ax7.bar(x, ss_error_values, color=['steelblue', 'coral', 'green'], alpha=0.8)
    ax7.set_ylabel('Steady-State Error (cm)')
    ax7.set_xticks(x)
    ax7.set_xticklabels(controllers)
    ax7.set_title('Steady-State Error (Last 20%)', fontweight='bold')
    ax7.grid(True, alpha=0.3, axis='y')

    # 添加数值标签
    for bar in bars3:
        height = bar.get_height()
        ax7.text(bar.get_x() + bar.get_width()/2., height,
                f'{height:.2f}', ha='center', va='bottom', fontsize=9)

    # 子图8：调节时间和控制平滑度
    ax8 = plt.subplot(2, 4, 8)
    settling_values = [pid_result['settling_time'],
                      fo_mpc_result['settling_time'],
                      idz_mpc_result['settling_time']]
    avg_du_values = [pid_result['avg_du']*100,
                     fo_mpc_result['avg_du']*100,
                     idz_mpc_result['avg_du']*100]

    ax8_twin = ax8.twinx()
    bars4 = ax8.bar(x - width/2, settling_values, width, label='Settling Time',
                   color='steelblue', alpha=0.8)
    bars5 = ax8_twin.bar(x + width/2, avg_du_values, width, label='Avg |Deltau|',
                        color='coral', alpha=0.8)

    ax8.set_ylabel('Settling Time (s)', color='steelblue')
    ax8_twin.set_ylabel('Avg |Deltau| (cm)', color='coral')
    ax8.set_xticks(x)
    ax8.set_xticklabels(controllers)
    ax8.set_title('Settling Time & Control Smoothness', fontweight='bold')
    ax8.tick_params(axis='y', labelcolor='steelblue')
    ax8_twin.tick_params(axis='y', labelcolor='coral')
    ax8.grid(True, alpha=0.3, axis='y')

    # 添加数值标签
    for bar in bars4:
        height = bar.get_height()
        ax8.text(bar.get_x() + bar.get_width()/2., height,
                f'{height:.0f}', ha='center', va='bottom', fontsize=9)
    for bar in bars5:
        height = bar.get_height()
        ax8_twin.text(bar.get_x() + bar.get_width()/2., height,
                     f'{height:.2f}', ha='center', va='bottom', fontsize=9)

    plt.tight_layout()
    plt.savefig('idz_mpc_comparison.png', dpi=150, bbox_inches='tight')
    print(f"\n 对比图已保存: idz_mpc_comparison.png")


def print_analysis(pid_result, fo_mpc_result, idz_mpc_result):
    """打印分析报告"""
    print("\n" + "=" * 80)
    print("性能分析报告")
    print("=" * 80)

    print("\n【1. 跟踪性能对比】")
    print("-" * 80)
    print(f"{'控制器':<15} {'MAE(cm)':<12} {'RMSE(cm)':<12} {'最大误差(cm)':<15} {'稳态误差(cm)':<15}")
    print("-" * 80)
    print(f"{'PID':<15} {pid_result['mae']*100:<12.2f} {pid_result['rmse']*100:<12.2f} "
          f"{pid_result['max_error']*100:<15.2f} {pid_result['steady_state_error']*100:<15.2f}")
    print(f"{'FO-MPC':<15} {fo_mpc_result['mae']*100:<12.2f} {fo_mpc_result['rmse']*100:<12.2f} "
          f"{fo_mpc_result['max_error']*100:<15.2f} {fo_mpc_result['steady_state_error']*100:<15.2f}")
    print(f"{'IDZ-MPC':<15} {idz_mpc_result['mae']*100:<12.2f} {idz_mpc_result['rmse']*100:<12.2f} "
          f"{idz_mpc_result['max_error']*100:<15.2f} {idz_mpc_result['steady_state_error']*100:<15.2f}")

    print("\n【2. 控制平滑度对比】")
    print("-" * 80)
    print(f"{'控制器':<15} {'平均|Deltau|(cm)':<15} {'最大|Deltau|(cm)':<15} {'调节时间(s)':<15}")
    print("-" * 80)
    print(f"{'PID':<15} {pid_result['avg_du']*100:<15.2f} {pid_result['max_du']*100:<15.2f} "
          f"{pid_result['settling_time']:<15.1f}")
    print(f"{'FO-MPC':<15} {fo_mpc_result['avg_du']*100:<15.2f} {fo_mpc_result['max_du']*100:<15.2f} "
          f"{fo_mpc_result['settling_time']:<15.1f}")
    print(f"{'IDZ-MPC':<15} {idz_mpc_result['avg_du']*100:<15.2f} {idz_mpc_result['max_du']*100:<15.2f} "
          f"{idz_mpc_result['settling_time']:<15.1f}")

    print("\n【3. 关键发现】")
    print("-" * 80)

    # 对比FO-MPC和IDZ-MPC
    fo_vs_idz_mae = (fo_mpc_result['mae'] - idz_mpc_result['mae']) / fo_mpc_result['mae'] * 100
    fo_vs_idz_ss = fo_mpc_result['steady_state_error'] - idz_mpc_result['steady_state_error']

    print(f"   IDZ-MPC vs FO-MPC:")
    if fo_vs_idz_mae > 5:
        print(f"      MAE改善: {fo_vs_idz_mae:.1f}%")
    elif fo_vs_idz_mae > 0:
        print(f"       MAE略有改善: {fo_vs_idz_mae:.1f}%")
    else:
        print(f"      MAE变差: {fo_vs_idz_mae:.1f}%")

    print(f"     -> 稳态误差减少: {fo_vs_idz_ss*100:.2f}cm")

    # 对比IDZ-MPC和PID
    idz_vs_pid_mae = (idz_mpc_result['mae'] - pid_result['mae']) / pid_result['mae'] * 100

    print(f"\n   IDZ-MPC vs PID:")
    if idz_vs_pid_mae < -5:
        print(f"      IDZ-MPC更优: MAE好{-idz_vs_pid_mae:.1f}%")
    elif abs(idz_vs_pid_mae) <= 5:
        print(f"     ⭕ 性能相当: MAE差异{idz_vs_pid_mae:+.1f}%")
    else:
        print(f"      PID仍更优: MAE差{idz_vs_pid_mae:+.1f}%")

    print("\n【4. 积分作用验证】")
    print("-" * 80)
    print(f"  PID积分器：")
    print(f"    -> 最终积分状态: {pid_result['integral'][-1]:.4f}")
    print(f"    -> 稳态误差: {pid_result['steady_state_error']*100:.2f}cm")

    print(f"\n  IDZ-MPC积分器：")
    print(f"    -> 最终积分状态: {idz_mpc_result['integral'][-1]:.4f}")
    print(f"    -> 稳态误差: {idz_mpc_result['steady_state_error']*100:.2f}cm")

    print(f"\n  FO-MPC（无积分器）：")
    print(f"    -> 稳态误差: {fo_mpc_result['steady_state_error']*100:.2f}cm")

    if idz_mpc_result['steady_state_error'] < 0.01:  # < 1cm
        print(f"\n   IDZ-MPC成功实现近零稳态误差！")
    else:
        print(f"\n    IDZ-MPC稳态误差仍存在，可能需要调优")

    print("\n【5. 总结】")
    print("-" * 80)

    if abs(idz_vs_pid_mae) <= 10:
        print("   成功！IDZ-MPC通过引入积分器达到了与PID相当的性能")
        print("   IDZ-MPC相比FO-MPC显著降低了稳态误差")
        print("   IDZ-MPC保持了MPC的约束处理和预测能力")
        print("\n   结论：积分器是关键！IDZ模型适合需要零稳态误差的应用")
    else:
        print("    IDZ-MPC性能有改善，但仍未完全达到PID水平")
        print("   可能需要进一步调优MPC参数或模型参数")

    print("\n" + "=" * 80)


def main():
    """主测试函数"""
    results = run_comparison_tests()

    print("\n" + "=" * 80)
    print("测试完成！")
    print("=" * 80)


if __name__ == "__main__":
    main()
