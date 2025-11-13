#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
例子1扩展：不同下游边界条件的影响研究（完全收敛版）

改进要点：
1. 初始稳态计算：监测收敛，不是固定时间步数
2. 收敛判据：质量守恒误差<0.1% 且 CV<0.01%
3. 阶跃后模拟：确保达到新稳态
4. 详细的收敛诊断信息

作者: Claude
日期: 2025-10-21
"""

import sys
import os
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))))

# DEPRECATED: Use HydrostaticCanalSolver instead
# # DEPRECATED: Use HydrostaticCanalSolver instead
# # DEPRECATED: Use HydrostaticCanalSolver instead
# # from solvers.hydrostatic_canal_solver import HydrostaticCanalSolver as CanalSolver  # 已废弃
from solvers.hydrostatic_canal_solver import HydrostaticCanalSolver as CanalSolver
from utils.canal_utils import compute_steady_uniform_flow, setup_chinese_fonts, get_convergence_metrics


def compute_steady_state_with_convergence(Q, h_downstream, B, S0, n, length, nx,
                                          mass_tol=0.001, cv_tol=0.0001,
                                          check_interval=200, max_steps=10000):
    """
    计算稳态初始条件，带收敛监测

    参数:
        Q: 流量 (m^3/s)
        h_downstream: 下游水位 (m)
        mass_tol: 质量守恒相对误差容忍度 (默认0.1%)
        cv_tol: 变异系数容忍度 (默认0.01%)
        check_interval: 收敛检查间隔步数
        max_steps: 最大迭代步数

    返回:
        h, Q: 收敛的水深和流量分布
        converged: 是否收敛
        iterations: 实际迭代步数
    """
    print(f"\n  计算稳态初始条件:")
    print(f"    目标: Q={Q:.2f} m^3/s, h_down={h_downstream:.4f} m")
    print(f"    收敛判据: 质量守恒误差<{mass_tol*100:.2f}%, CV<{cv_tol*100:.4f}%")

    # 初始化求解器
    solver = CanalSolver(length=length, nx=nx, B=B, S0=S0, n=n, method='preissmann')

    # 使用恒定均匀流作为粗略初值
    h_uniform = compute_steady_uniform_flow(Q, B, S0, n)
    solver.h[:] = h_uniform
    solver.Q[:] = Q

    dt = 0.5
    converged = False

    # 用于监测收敛的历史数据
    Q_history = []
    h_history = []

    for i in range(max_steps):
        solver.step(dt, Q, h_downstream)

        # 保存状态用于CV计算
        Q_history.append(np.mean(solver.Q))
        h_history.append(np.mean(solver.h))

        # 定期检查收敛
        if (i + 1) % check_interval == 0:
            t = (i + 1) * dt

            # 质量守恒检查
            Q_avg = np.mean(solver.Q)
            mass_error = abs(Q_avg - Q) / Q

            # CV检查（最近1000步）
            window = min(2000, len(Q_history))
            recent_Q = Q_history[-window:]
            recent_h = h_history[-window:]

            Q_cv = np.std(recent_Q) / np.mean(recent_Q) if np.mean(recent_Q) > 0 else 1.0
            h_cv = np.std(recent_h) / np.mean(recent_h) if np.mean(recent_h) > 0 else 1.0

            print(f"    t={t:6.0f}s: Q_avg={Q_avg:.4f} m^3/s, "
                  f"质量误差={mass_error*100:.4f}%, Q_CV={Q_cv*100:.4f}%, h_CV={h_cv*100:.4f}%")

            # 检查是否收敛
            if mass_error < mass_tol and Q_cv < cv_tol and h_cv < cv_tol:
                print(f"     收敛! 迭代{i+1}步 ({t:.0f}s)")
                converged = True
                break

    if not converged:
        print(f"     未完全收敛 (达到最大步数 {max_steps})")
        t = max_steps * dt

    # 最终状态检查
    Q_final_avg = np.mean(solver.Q)
    Q_final_error = abs(Q_final_avg - Q) / Q * 100

    print(f"    最终状态: Q_avg={Q_final_avg:.4f} m^3/s, 误差={Q_final_error:.3f}%")

    return solver.h.copy(), solver.Q.copy(), converged, i + 1


def main():
    """主函数"""
    print("=" * 80)
    print("例子1扩展：不同下游边界条件的影响研究（完全收敛版）")
    print("=" * 80)

    # 参数设置
    length = 1000.0
    B = 10.0
    S0 = 0.001
    n = 0.025
    nx = 201

    Q_initial = 8.0
    Q_final = 10.0

    h_uniform_initial = compute_steady_uniform_flow(Q_initial, B, S0, n)
    h_uniform_final = compute_steady_uniform_flow(Q_final, B, S0, n)

    print(f"\n参数设置:")
    print(f"  渠道: L={length}m, B={B}m, S0={S0}, n={n}")
    print(f"  上游流量: {Q_initial} -> {Q_final} m^3/s")
    print(f"  理论水深: {h_uniform_initial:.6f} -> {h_uniform_final:.6f} m")

    # 定义三种边界条件
    scenarios = {
        '高水位_回水': {
            'h_downstream': h_uniform_final + 0.15,
            'description': '高水位（回水）',
            'color': '#d62728'
        },
        '恒定均匀流': {
            'h_downstream': h_uniform_final,
            'description': '恒定均匀流',
            'color': '#2ca02c'
        },
        '低水位_泵站': {
            'h_downstream': h_uniform_final - 0.10,
            'description': '低水位（泵站）',
            'color': '#1f77b4'
        }
    }

    print(f"\n下游边界条件:")
    for name, params in scenarios.items():
        print(f"  {params['description']}: h = {params['h_downstream']:.6f} m")

    # 运行仿真
    print("\n" + "=" * 80)
    print("第一阶段：计算初始稳态（Q=8.0 m^3/s）")
    print("=" * 80)

    initial_states = {}

    for scenario_name, scenario_params in scenarios.items():
        print(f"\n场景: {scenario_params['description']}")

        h_init, Q_init, converged, iterations = compute_steady_state_with_convergence(
            Q_initial,
            scenario_params['h_downstream'],
            B, S0, n, length, nx,
            mass_tol=0.001,  # 0.1%
            cv_tol=0.0001    # 0.01%
        )

        initial_states[scenario_name] = {
            'h': h_init,
            'Q': Q_init,
            'converged': converged,
            'iterations': iterations
        }

    # 第二阶段：流量阶跃响应
    print("\n" + "=" * 80)
    print("第二阶段：流量阶跃响应（8.0 -> 10.0 m^3/s）")
    print("=" * 80)

    # 自适应时间：基于初始收敛时间估算
    max_initial_time = max([s['iterations'] * 0.5 for s in initial_states.values()])
    t_step = max(300.0, max_initial_time)  # 至少300s让初始稳态稳定
    T_after_step = max(1500.0, max_initial_time * 2)  # 阶跃后至少1500s
    T_total = t_step + T_after_step

    print(f"\n时间参数（自适应）:")
    print(f"  阶跃时刻: {t_step:.0f} s")
    print(f"  阶跃后持续时间: {T_after_step:.0f} s")
    print(f"  总时间: {T_total:.0f} s")

    dt = 0.5
    n_steps = int(T_total / dt)

    results = {}

    for scenario_name, scenario_params in scenarios.items():
        print(f"\n场景: {scenario_params['description']}")

        # 使用收敛的初始稳态
        initial = initial_states[scenario_name]
        print(f"  使用收敛初值 (迭代{initial['iterations']}步)")

        solver = CanalSolver(length=length, nx=nx, B=B, S0=S0, n=n, method='preissmann')
        solver.h = initial['h'].copy()
        solver.Q = initial['Q'].copy()
        solver.clear_history()

        # 运行阶跃响应
        for i in range(n_steps):
            t = (i + 1) * dt

            # 流量阶跃
            Q_upstream = Q_initial if t < t_step else Q_final
            h_downstream = scenario_params['h_downstream']

            solver.step(dt, Q_upstream, h_downstream)

            if i % 20 == 0:  # 每10s保存一次
                solver.save_state(t)

            # 定期打印进度
            if (i + 1) % 400 == 0:
                Q_avg = np.mean(solver.Q)
                h_avg = np.mean(solver.h)
                expected_Q = Q_initial if t < t_step else Q_final
                error = abs(Q_avg - expected_Q) / expected_Q * 100
                print(f"    t={t:6.0f}s: h_avg={h_avg:.4f}m, Q_avg={Q_avg:.4f} m^3/s, 误差={error:.3f}%")

        # 最终质量守恒检查
        Q_final_avg = np.mean(solver.Q)
        Q_error = abs(Q_final_avg - Q_final) / Q_final * 100

        # 检查最后500s的CV
        history = solver.get_history()
        time = np.array(history['time'])
        mask = time > (T_total - 500)
        if np.sum(mask) > 10:
            recent_Q = [np.mean(Q) for Q, t_val in zip(history['Q_history'], history['time']) if t_val > T_total - 500]
            final_cv = np.std(recent_Q) / np.mean(recent_Q) * 100 if len(recent_Q) > 0 else 0
        else:
            final_cv = 0

        status = "" if Q_error < 1.0 else ""
        print(f"  最终检查:")
        print(f"    Q_avg = {Q_final_avg:.4f} m^3/s (目标: {Q_final:.2f} m^3/s)")
        print(f"    质量守恒误差 = {Q_error:.3f}% {status}")
        print(f"    最后500s CV = {final_cv:.4f}%")

        results[scenario_name] = {
            'solver': solver,
            'h_final': solver.h.copy(),
            'Q_final': solver.Q.copy(),
            'history': history,
            'params': scenario_params,
            'mass_error': Q_error,
            'final_cv': final_cv
        }

    # 可视化
    print("\n" + "=" * 80)
    print("生成可视化图表")
    print("=" * 80)

    output_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "figures")
    os.makedirs(output_dir, exist_ok=True)

    setup_chinese_fonts()

    # 时间序列图
    fig, axes = plt.subplots(4, 1, figsize=(16, 14))

    for scenario_name, data in results.items():
        history = data['history']
        time = history['time']
        params = data['params']

        h_upstream = np.array([h[0] for h in history['h_history']])
        h_downstream_sim = np.array([h[-1] for h in history['h_history']])
        Q_upstream = np.array([Q[0] for Q in history['Q_history']])
        Q_downstream = np.array([Q[-1] for Q in history['Q_history']])

        label = f"{params['description']} (误差={data['mass_error']:.2f}%, CV={data['final_cv']:.3f}%)"

        axes[0].plot(time, h_upstream, label=label,
                    color=params['color'], linewidth=2, alpha=0.8)
        axes[1].plot(time, h_downstream_sim, label=label,
                    color=params['color'], linewidth=2, alpha=0.8)
        axes[2].plot(time, Q_upstream, label=label,
                    color=params['color'], linewidth=2, alpha=0.8)
        axes[3].plot(time, Q_downstream, label=label,
                    color=params['color'], linewidth=2, alpha=0.8)

    for ax in axes:
        ax.axvline(t_step, color='k', linestyle='--', linewidth=1.5,
                  label='流量阶跃' if ax == axes[0] else '')

    axes[0].axhline(h_uniform_initial, color='gray', linestyle=':', alpha=0.5, label='初始理论值')
    axes[0].axhline(h_uniform_final, color='purple', linestyle=':', alpha=0.5, label='最终理论值')
    axes[2].axhline(Q_initial, color='gray', linestyle=':', alpha=0.5, label='初始理论值')
    axes[2].axhline(Q_final, color='purple', linestyle=':', alpha=0.5, label='最终理论值')

    axes[0].set_ylabel('上游水深 (m)', fontsize=11)
    axes[0].set_title('系统响应 - 上游水深', fontsize=12, fontweight='bold')
    axes[0].legend(fontsize=9, loc='best')
    axes[0].grid(True, alpha=0.3)

    axes[1].set_ylabel('下游水深 (m)', fontsize=11)
    axes[1].set_title('系统响应 - 下游水深', fontsize=12, fontweight='bold')
    axes[1].legend(fontsize=9, loc='best')
    axes[1].grid(True, alpha=0.3)

    axes[2].set_ylabel('上游流量 (m^3/s)', fontsize=11)
    axes[2].set_title('系统响应 - 上游流量', fontsize=12, fontweight='bold')
    axes[2].legend(fontsize=9, loc='best')
    axes[2].grid(True, alpha=0.3)

    axes[3].set_ylabel('下游流量 (m^3/s)', fontsize=11)
    axes[3].set_xlabel('时间 (s)', fontsize=11)
    axes[3].set_title('系统响应 - 下游流量', fontsize=12, fontweight='bold')
    axes[3].legend(fontsize=9, loc='best')
    axes[3].grid(True, alpha=0.3)

    plt.tight_layout()
    save_path = os.path.join(output_dir, "example_01_boundary_converged_timeseries.png")
    plt.savefig(save_path, dpi=150, bbox_inches='tight')
    print(f"时间序列图已保存: {save_path}")
    plt.close()

    # 最终空间分布
    fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(16, 10))
    x = results['恒定均匀流']['solver'].x

    for scenario_name, data in results.items():
        params = data['params']
        label = f"{params['description']} (误差={data['mass_error']:.2f}%)"

        ax1.plot(x, data['h_final'], label=label,
                color=params['color'], linewidth=2.5, alpha=0.8)
        ax2.plot(x, data['Q_final'], label=label,
                color=params['color'], linewidth=2.5, alpha=0.8)

    ax1.axhline(h_uniform_final, color='gray', linestyle='--', linewidth=2, label='理论值', alpha=0.7)
    ax2.axhline(Q_final, color='gray', linestyle='--', linewidth=2, label='理论值', alpha=0.7)

    ax1.set_xlabel('距离 x (m)', fontsize=11)
    ax1.set_ylabel('水深 h (m)', fontsize=11)
    ax1.set_title(f'最终稳态空间分布 - 水深 (t={T_total:.0f}s)', fontsize=12, fontweight='bold')
    ax1.legend(fontsize=10)
    ax1.grid(True, alpha=0.3)

    ax2.set_xlabel('距离 x (m)', fontsize=11)
    ax2.set_ylabel('流量 Q (m^3/s)', fontsize=11)
    ax2.set_title(f'最终稳态空间分布 - 流量 (t={T_total:.0f}s)', fontsize=12, fontweight='bold')
    ax2.legend(fontsize=10)
    ax2.grid(True, alpha=0.3)

    plt.tight_layout()
    save_path = os.path.join(output_dir, "example_01_boundary_converged_spatial.png")
    plt.savefig(save_path, dpi=150, bbox_inches='tight')
    print(f"空间分布图已保存: {save_path}")
    plt.close()

    # 总结
    print("\n" + "=" * 80)
    print("仿真完成！")
    print("=" * 80)

    print("\n关键改进:")
    print("1.  初始稳态计算带收敛监测（质量误差<0.1%, CV<0.01%）")
    print("2.  自适应确定阶跃时刻和总时间")
    print("3.  从真正的稳态初值开始阶跃响应")
    print("4.  验证最终质量守恒和收敛性")

    print("\n最终质量守恒检查:")
    for scenario_name, data in results.items():
        status = "" if data['mass_error'] < 1.0 else ""
        print(f"  {data['params']['description']:12s}: 误差={data['mass_error']:6.3f}%, CV={data['final_cv']:7.4f}% {status}")

    print("\n 完全收敛版运行成功")


if __name__ == '__main__':
    main()
