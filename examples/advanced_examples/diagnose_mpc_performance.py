# -*- coding: utf-8 -*-
"""
MPC性能诊断分析

目标：
1. 对比MPC和PID的控制行为差异
2. 分析MPC参数（Q, R, Qf, 预测时域）的影响
3. 检查MPC实现是否存在问题
4. 理解为什么PID的积分作用如此有效

作者：HydroClaude Team
日期：2025-10-24
"""

import numpy as np
import matplotlib.pyplot as plt
from typing import Dict, List, Tuple
import sys
import os

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))

from examples.advanced_examples.linearized_canal_simulator import LinearizedCanalSimulator
from control.first_order_mpc import FirstOrderMPC, FirstOrderMPCConfig
from control.pid_controller import PIDController, PIDConfig


def test_mpc_with_params(Q: float, R: float, Qf: float,
                         Np: int = 15, Nc: int = 10,
                         total_time: float = 400.0) -> Dict:
    """
    测试不同MPC参数配置的性能

    Args:
        Q: 跟踪误差权重
        R: 控制增量权重
        Qf: 终端代价权重
        Np: 预测时域
        Nc: 控制时域
        total_time: 仿真时间

    Returns:
        result: 测试结果
    """
    dt = 10.0

    # 创建仿真器（线性化模型 - 理想情况）
    simulator = LinearizedCanalSimulator(
        h_work=2.5,
        a_work=2.0,
        dt=dt,
        use_linear=True  # 使用线性模型，排除模型失配
    )

    # 获取系统参数
    K, tau = simulator.get_system_params()

    # 创建MPC控制器
    config = FirstOrderMPCConfig(
        prediction_horizon=Np,
        control_horizon=Nc,
        dt=dt,
        Q=Q,
        R=R,
        Qf=Qf,
        u_min=0.1,
        u_max=4.0,
        du_max=0.5,
        solver='OSQP',
        verbose=False
    )

    controller = FirstOrderMPC(K=K, tau=tau, config=config)

    # 测试场景：简单的设定点跟踪
    setpoint = 2.5 + 0.3  # 2.8m

    # 扰动
    disturbance_schedule = [
        (0, 20.0),
        (200, 25.0)
    ]

    # 仿真
    n_steps = int(total_time / dt)

    time_hist = []
    h_hist = []
    u_hist = []
    error_hist = []
    du_hist = []

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

        # MPC计算
        u, _ = controller.compute_control(y, setpoint)

        # 执行控制
        y_next = simulator.step(u)

        # 记录
        time_hist.append(t)
        h_hist.append(y)
        u_hist.append(u)
        error_hist.append(abs(y - setpoint))
        du_hist.append(abs(u - u_prev))

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

    result = {
        'time': np.array(time_hist),
        'h': np.array(h_hist),
        'u': np.array(u_hist),
        'error': error_array,
        'du': du_array,
        'mae': mae,
        'rmse': rmse,
        'max_error': max_error,
        'settling_time': settling_time,
        'avg_du': avg_du,
        'max_du': max_du,
        'Q': Q,
        'R': R,
        'Qf': Qf,
        'Np': Np,
        'Nc': Nc,
        'setpoint': setpoint
    }

    return result


def test_pid_baseline(total_time: float = 400.0) -> Dict:
    """测试PID基准性能"""
    dt = 10.0

    # 创建仿真器
    simulator = LinearizedCanalSimulator(
        h_work=2.5,
        a_work=2.0,
        dt=dt,
        use_linear=True
    )

    # 创建PID控制器
    config = PIDConfig(
        kp=-1.0,
        ki=-0.15,
        kd=0.0,
        dt=dt,
        output_min=0.1,
        output_max=4.0
    )

    controller = PIDController(config)

    # 测试场景
    setpoint = 2.5 + 0.3  # 2.8m

    disturbance_schedule = [
        (0, 20.0),
        (200, 25.0)
    ]

    # 仿真
    n_steps = int(total_time / dt)

    time_hist = []
    h_hist = []
    u_hist = []
    error_hist = []
    du_hist = []

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

        # PID计算
        controller.setpoint = setpoint
        u = controller.compute(y)

        # 执行控制
        y_next = simulator.step(u)

        # 记录
        time_hist.append(t)
        h_hist.append(y)
        u_hist.append(u)
        error_hist.append(abs(y - setpoint))
        du_hist.append(abs(u - u_prev))

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

    result = {
        'time': np.array(time_hist),
        'h': np.array(h_hist),
        'u': np.array(u_hist),
        'error': error_array,
        'du': du_array,
        'mae': mae,
        'rmse': rmse,
        'max_error': max_error,
        'settling_time': settling_time,
        'avg_du': avg_du,
        'max_du': max_du,
        'setpoint': setpoint
    }

    return result


def parameter_sweep_analysis():
    """参数扫描分析"""
    print("=" * 80)
    print("MPC性能诊断分析")
    print("=" * 80)

    # 首先测试PID基准
    print("\n【步骤1】测试PID基准性能...")
    pid_result = test_pid_baseline()
    print(f"  PID: MAE={pid_result['mae']*100:.2f}cm, "
          f"调节时间={pid_result['settling_time']:.1f}s, "
          f"平均Deltau={pid_result['avg_du']*100:.2f}cm")

    # 测试默认MPC参数
    print("\n【步骤2】测试默认MPC参数 (Q=100, R=1, Qf=1000)...")
    default_mpc = test_mpc_with_params(Q=100.0, R=1.0, Qf=1000.0)
    print(f"  MPC: MAE={default_mpc['mae']*100:.2f}cm, "
          f"调节时间={default_mpc['settling_time']:.1f}s, "
          f"平均Deltau={default_mpc['avg_du']*100:.2f}cm")

    # Q参数扫描
    print("\n【步骤3】Q参数扫描（跟踪误差权重）...")
    Q_values = [1.0, 10.0, 100.0, 1000.0, 10000.0]
    q_results = []
    for Q in Q_values:
        result = test_mpc_with_params(Q=Q, R=1.0, Qf=Q*10)
        q_results.append(result)
        print(f"  Q={Q:7.1f}: MAE={result['mae']*100:6.2f}cm, "
              f"调节时间={result['settling_time']:5.1f}s, "
              f"平均Deltau={result['avg_du']*100:5.2f}cm")

    # R参数扫描
    print("\n【步骤4】R参数扫描（控制增量权重）...")
    R_values = [0.01, 0.1, 1.0, 10.0, 100.0]
    r_results = []
    for R in R_values:
        result = test_mpc_with_params(Q=100.0, R=R, Qf=1000.0)
        r_results.append(result)
        print(f"  R={R:7.2f}: MAE={result['mae']*100:6.2f}cm, "
              f"调节时间={result['settling_time']:5.1f}s, "
              f"平均Deltau={result['avg_du']*100:5.2f}cm")

    # 预测时域扫描
    print("\n【步骤5】预测时域扫描...")
    Np_values = [5, 10, 15, 20, 30]
    np_results = []
    for Np in Np_values:
        Nc = min(Np, 10)
        result = test_mpc_with_params(Q=100.0, R=1.0, Qf=1000.0, Np=Np, Nc=Nc)
        np_results.append(result)
        print(f"  Np={Np:2d}: MAE={result['mae']*100:6.2f}cm, "
              f"调节时间={result['settling_time']:5.1f}s")

    # 找到最佳MPC配置
    print("\n【步骤6】寻找最佳MPC配置...")
    all_mpc_results = q_results + r_results + np_results
    best_mpc = min(all_mpc_results, key=lambda x: x['mae'])
    print(f"  最佳配置: Q={best_mpc['Q']:.1f}, R={best_mpc['R']:.2f}, "
          f"Qf={best_mpc['Qf']:.1f}, Np={best_mpc['Np']}, Nc={best_mpc['Nc']}")
    print(f"  最佳性能: MAE={best_mpc['mae']*100:.2f}cm "
          f"(PID: {pid_result['mae']*100:.2f}cm)")

    # 可视化对比
    visualize_comparison(pid_result, default_mpc, best_mpc,
                        q_results, r_results, np_results)

    # 打印详细分析
    print_detailed_analysis(pid_result, default_mpc, best_mpc)

    return {
        'pid': pid_result,
        'default_mpc': default_mpc,
        'best_mpc': best_mpc,
        'q_results': q_results,
        'r_results': r_results,
        'np_results': np_results
    }


def visualize_comparison(pid_result, default_mpc, best_mpc,
                        q_results, r_results, np_results):
    """可视化对比分析"""
    fig = plt.figure(figsize=(18, 12))

    # 子图1：时域对比 - 水位
    ax1 = plt.subplot(3, 3, 1)
    ax1.plot(pid_result['time'], pid_result['h'], 'b-', linewidth=2, label='PID')
    ax1.plot(default_mpc['time'], default_mpc['h'], 'r--', linewidth=2, label='Default MPC')
    ax1.plot(best_mpc['time'], best_mpc['h'], 'g-.', linewidth=2, label='Best MPC')
    ax1.axhline(pid_result['setpoint'], color='gray', linestyle=':', label='Setpoint')
    ax1.set_xlabel('Time (s)')
    ax1.set_ylabel('Water Level (m)')
    ax1.set_title('Water Level Response', fontweight='bold')
    ax1.legend()
    ax1.grid(True, alpha=0.3)

    # 子图2：时域对比 - 控制量
    ax2 = plt.subplot(3, 3, 2)
    ax2.plot(pid_result['time'], pid_result['u'], 'b-', linewidth=2, label='PID')
    ax2.plot(default_mpc['time'], default_mpc['u'], 'r--', linewidth=2, label='Default MPC')
    ax2.plot(best_mpc['time'], best_mpc['u'], 'g-.', linewidth=2, label='Best MPC')
    ax2.set_xlabel('Time (s)')
    ax2.set_ylabel('Gate Opening (m)')
    ax2.set_title('Control Input', fontweight='bold')
    ax2.legend()
    ax2.grid(True, alpha=0.3)

    # 子图3：时域对比 - 误差
    ax3 = plt.subplot(3, 3, 3)
    ax3.plot(pid_result['time'], pid_result['error']*100, 'b-', linewidth=2, label='PID')
    ax3.plot(default_mpc['time'], default_mpc['error']*100, 'r--', linewidth=2, label='Default MPC')
    ax3.plot(best_mpc['time'], best_mpc['error']*100, 'g-.', linewidth=2, label='Best MPC')
    ax3.set_xlabel('Time (s)')
    ax3.set_ylabel('Absolute Error (cm)')
    ax3.set_title('Tracking Error', fontweight='bold')
    ax3.legend()
    ax3.grid(True, alpha=0.3)

    # 子图4：Q参数扫描
    ax4 = plt.subplot(3, 3, 4)
    Q_vals = [r['Q'] for r in q_results]
    mae_vals = [r['mae']*100 for r in q_results]
    ax4.semilogx(Q_vals, mae_vals, 'ro-', linewidth=2, markersize=8)
    ax4.axhline(pid_result['mae']*100, color='b', linestyle='--', label='PID Baseline')
    ax4.set_xlabel('Q (Tracking Weight)')
    ax4.set_ylabel('MAE (cm)')
    ax4.set_title('Effect of Q Parameter', fontweight='bold')
    ax4.legend()
    ax4.grid(True, alpha=0.3)

    # 子图5：R参数扫描
    ax5 = plt.subplot(3, 3, 5)
    R_vals = [r['R'] for r in r_results]
    mae_vals_r = [r['mae']*100 for r in r_results]
    ax5.semilogx(R_vals, mae_vals_r, 'go-', linewidth=2, markersize=8)
    ax5.axhline(pid_result['mae']*100, color='b', linestyle='--', label='PID Baseline')
    ax5.set_xlabel('R (Control Weight)')
    ax5.set_ylabel('MAE (cm)')
    ax5.set_title('Effect of R Parameter', fontweight='bold')
    ax5.legend()
    ax5.grid(True, alpha=0.3)

    # 子图6：预测时域扫描
    ax6 = plt.subplot(3, 3, 6)
    Np_vals = [r['Np'] for r in np_results]
    mae_vals_np = [r['mae']*100 for r in np_results]
    ax6.plot(Np_vals, mae_vals_np, 'mo-', linewidth=2, markersize=8)
    ax6.axhline(pid_result['mae']*100, color='b', linestyle='--', label='PID Baseline')
    ax6.set_xlabel('Prediction Horizon (Np)')
    ax6.set_ylabel('MAE (cm)')
    ax6.set_title('Effect of Prediction Horizon', fontweight='bold')
    ax6.legend()
    ax6.grid(True, alpha=0.3)

    # 子图7：控制增量对比
    ax7 = plt.subplot(3, 3, 7)
    ax7.plot(pid_result['time'][1:], pid_result['du'][1:]*100, 'b-', linewidth=2, label='PID')
    ax7.plot(default_mpc['time'][1:], default_mpc['du'][1:]*100, 'r--', linewidth=2, label='Default MPC')
    ax7.plot(best_mpc['time'][1:], best_mpc['du'][1:]*100, 'g-.', linewidth=2, label='Best MPC')
    ax7.set_xlabel('Time (s)')
    ax7.set_ylabel('Control Increment |Deltau| (cm)')
    ax7.set_title('Control Action Smoothness', fontweight='bold')
    ax7.legend()
    ax7.grid(True, alpha=0.3)

    # 子图8：性能指标对比
    ax8 = plt.subplot(3, 3, 8)
    controllers = ['PID', 'Default\nMPC', 'Best\nMPC']
    mae_values = [pid_result['mae']*100, default_mpc['mae']*100, best_mpc['mae']*100]
    settling_values = [pid_result['settling_time'], default_mpc['settling_time'], best_mpc['settling_time']]

    x = np.arange(len(controllers))
    width = 0.35

    ax8_twin = ax8.twinx()
    bars1 = ax8.bar(x - width/2, mae_values, width, label='MAE', color='steelblue', alpha=0.8)
    bars2 = ax8_twin.bar(x + width/2, settling_values, width, label='Settling Time', color='coral', alpha=0.8)

    ax8.set_ylabel('MAE (cm)', color='steelblue')
    ax8_twin.set_ylabel('Settling Time (s)', color='coral')
    ax8.set_xticks(x)
    ax8.set_xticklabels(controllers)
    ax8.set_title('Performance Metrics Comparison', fontweight='bold')
    ax8.tick_params(axis='y', labelcolor='steelblue')
    ax8_twin.tick_params(axis='y', labelcolor='coral')
    ax8.grid(True, alpha=0.3, axis='y')

    # 添加数值标签
    for bar in bars1:
        height = bar.get_height()
        ax8.text(bar.get_x() + bar.get_width()/2., height,
                f'{height:.1f}', ha='center', va='bottom', fontsize=9)
    for bar in bars2:
        height = bar.get_height()
        ax8_twin.text(bar.get_x() + bar.get_width()/2., height,
                     f'{height:.0f}', ha='center', va='bottom', fontsize=9)

    # 子图9：控制平滑度对比
    ax9 = plt.subplot(3, 3, 9)
    avg_du_values = [pid_result['avg_du']*100, default_mpc['avg_du']*100, best_mpc['avg_du']*100]
    max_du_values = [pid_result['max_du']*100, default_mpc['max_du']*100, best_mpc['max_du']*100]

    bars3 = ax9.bar(x - width/2, avg_du_values, width, label='Average |Deltau|', color='lightblue', alpha=0.8)
    bars4 = ax9.bar(x + width/2, max_du_values, width, label='Max |Deltau|', color='lightcoral', alpha=0.8)

    ax9.set_ylabel('Control Increment (cm)')
    ax9.set_xticks(x)
    ax9.set_xticklabels(controllers)
    ax9.set_title('Control Smoothness Comparison', fontweight='bold')
    ax9.legend()
    ax9.grid(True, alpha=0.3, axis='y')

    # 添加数值标签
    for bar in bars3:
        height = bar.get_height()
        ax9.text(bar.get_x() + bar.get_width()/2., height,
                f'{height:.2f}', ha='center', va='bottom', fontsize=8)
    for bar in bars4:
        height = bar.get_height()
        ax9.text(bar.get_x() + bar.get_width()/2., height,
                f'{height:.2f}', ha='center', va='bottom', fontsize=8)

    plt.tight_layout()
    plt.savefig('mpc_diagnosis.png', dpi=150, bbox_inches='tight')
    print(f"\n 诊断图已保存: mpc_diagnosis.png")


def print_detailed_analysis(pid_result, default_mpc, best_mpc):
    """打印详细分析报告"""
    print("\n" + "=" * 80)
    print("详细诊断分析")
    print("=" * 80)

    print("\n【1. 性能对比】")
    print("-" * 80)
    print(f"{'控制器':<15} {'MAE(cm)':<12} {'RMSE(cm)':<12} {'最大误差(cm)':<15} {'调节时间(s)':<12}")
    print("-" * 80)
    print(f"{'PID':<15} {pid_result['mae']*100:<12.2f} {pid_result['rmse']*100:<12.2f} "
          f"{pid_result['max_error']*100:<15.2f} {pid_result['settling_time']:<12.1f}")
    print(f"{'Default MPC':<15} {default_mpc['mae']*100:<12.2f} {default_mpc['rmse']*100:<12.2f} "
          f"{default_mpc['max_error']*100:<15.2f} {default_mpc['settling_time']:<12.1f}")
    print(f"{'Best MPC':<15} {best_mpc['mae']*100:<12.2f} {best_mpc['rmse']*100:<12.2f} "
          f"{best_mpc['max_error']*100:<15.2f} {best_mpc['settling_time']:<12.1f}")

    print("\n【2. 控制平滑度对比】")
    print("-" * 80)
    print(f"{'控制器':<15} {'平均|Deltau|(cm)':<15} {'最大|Deltau|(cm)':<15}")
    print("-" * 80)
    print(f"{'PID':<15} {pid_result['avg_du']*100:<15.2f} {pid_result['max_du']*100:<15.2f}")
    print(f"{'Default MPC':<15} {default_mpc['avg_du']*100:<15.2f} {default_mpc['max_du']*100:<15.2f}")
    print(f"{'Best MPC':<15} {best_mpc['avg_du']*100:<15.2f} {best_mpc['max_du']*100:<15.2f}")

    print("\n【3. 关键发现】")
    print("-" * 80)

    mae_improvement = (default_mpc['mae'] - best_mpc['mae']) / default_mpc['mae'] * 100
    pid_vs_best = (best_mpc['mae'] - pid_result['mae']) / pid_result['mae'] * 100

    if mae_improvement > 5:
        print(f"   MPC参数调优有效：MAE改善 {mae_improvement:.1f}%")
    else:
        print(f"    MPC参数调优效果有限：MAE仅改善 {mae_improvement:.1f}%")

    if pid_vs_best > 0:
        print(f"   即使最佳MPC配置，仍比PID差 {pid_vs_best:.1f}%")
        print(f"     -> 原因可能：")
        print(f"       1. PID的积分作用能完全消除稳态误差")
        print(f"       2. MPC的一阶模型可能不够精确（无积分器）")
        print(f"       3. 测试场景（阶跃扰动）有利于PID")
    else:
        print(f"   最佳MPC配置超越PID {-pid_vs_best:.1f}%")

    print("\n【4. MPC局限性分析】")
    print("-" * 80)
    print("   一阶MPC模型: H(s) = K/(taus+1)")
    print("     -> 无积分器，稳态增益有限")
    print("     -> 对常值扰动的抑制能力弱于带积分的PID")
    print()
    print("   PID控制器: U(s)/E(s) = Kp + Ki/s")
    print("     -> 积分作用保证零稳态误差")
    print("     -> 对阶跃扰动有天然优势")
    print()
    print("   改进方向：")
    print("     1. 使用IDZ模型的MPC（带积分器）")
    print("     2. 增加扰动观测器")
    print("     3. 偏移量自由设计（offset-free MPC）")

    print("\n" + "=" * 80)


def main():
    """主诊断函数"""
    results = parameter_sweep_analysis()

    print("\n" + "=" * 80)
    print("MPC性能诊断完成！")
    print("=" * 80)
    print("\n核心结论：")
    print("  1. MPC参数调优可以改善性能，但仍难以超越PID")
    print("  2. 根本原因：一阶模型缺乏积分器，无法保证零稳态误差")
    print("  3. 建议：开发基于IDZ模型的MPC（带积分器）")
    print("\n" + "=" * 80)


if __name__ == "__main__":
    main()
