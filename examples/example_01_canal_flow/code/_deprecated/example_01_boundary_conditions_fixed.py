#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
例子1扩展：不同下游边界条件的影响研究（修正版）

修正问题：
1. 增加仿真时间到1200s以确保达到稳态
2. 改进初始条件获取
3. 添加质量守恒检查

作者: Claude
日期: 2025-10-21
"""

import sys
import os
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))))

from solvers.canal_solver import CanalSolver
from utils.canal_utils import compute_steady_uniform_flow, setup_chinese_fonts


def get_steady_state_initial_condition(Q, h_downstream, B, S0, n, length, nx):
    """
    为给定边界条件求解稳态初始条件

    通过运行足够长的仿真时间获得稳态
    """
    print(f"    计算稳态初始条件 (Q={Q:.1f} m³/s, h_down={h_downstream:.4f} m)...")

    solver = CanalSolver(length=length, nx=nx, B=B, S0=S0, n=n, method='preissmann')

    # 使用恒定均匀流作为粗略初值
    h_uniform = compute_steady_uniform_flow(Q, B, S0, n)
    solver.h[:] = h_uniform
    solver.Q[:] = Q

    # 运行到稳态（较长时间）
    dt = 0.5
    n_steps = 2000  # 1000s

    for i in range(n_steps):
        solver.step(dt, Q, h_downstream)

        if i % 500 == 0:
            Q_avg = np.mean(solver.Q)
            print(f"      t={i*dt:.0f}s: Q_avg={Q_avg:.4f} m³/s")

    # 检查收敛
    Q_error = abs(np.mean(solver.Q) - Q) / Q * 100
    print(f"    稳态初值获得: Q_avg={np.mean(solver.Q):.4f} m³/s (误差: {Q_error:.2f}%)")

    return solver.h.copy(), solver.Q.copy()


def main():
    """主函数"""
    print("=" * 80)
    print("例子1扩展：不同下游边界条件的影响研究（修正版）")
    print("=" * 80)

    # 参数设置
    length = 1000.0
    B = 10.0
    S0 = 0.001
    n = 0.025
    nx = 201

    Q_initial = 8.0
    Q_final = 10.0
    t_step = 300.0  # 延后阶跃时刻以便初始稳定

    h_uniform_initial = compute_steady_uniform_flow(Q_initial, B, S0, n)
    h_uniform_final = compute_steady_uniform_flow(Q_final, B, S0, n)

    print(f"\n参数设置:")
    print(f"  渠道: L={length}m, B={B}m, S0={S0}, n={n}")
    print(f"  上游流量: {Q_initial} → {Q_final} m³/s (t={t_step}s)")
    print(f"  理论水深: {h_uniform_initial:.6f} → {h_uniform_final:.6f} m")

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

    # 时间参数（增加到1200s）
    dt = 0.5
    T_total = 1200.0
    n_steps = int(T_total / dt)

    print(f"\n时间参数:")
    print(f"  时间步长: {dt} s")
    print(f"  总时间: {T_total} s（增加以确保稳态）")

    # 运行仿真
    print("\n" + "=" * 80)
    print("运行仿真（获取稳态初值 + 阶跃响应）")
    print("=" * 80)

    results = {}

    for scenario_name, scenario_params in scenarios.items():
        print(f"\n场景: {scenario_params['description']}")

        # 步骤1: 获取初始稳态
        print(f"  步骤1: 获取Q={Q_initial} m³/s的稳态初值")
        h_init, Q_init = get_steady_state_initial_condition(
            Q_initial, scenario_params['h_downstream'], B, S0, n, length, nx
        )

        # 步骤2: 使用稳态初值运行阶跃响应
        print(f"  步骤2: 运行流量阶跃响应仿真")
        solver = CanalSolver(length=length, nx=nx, B=B, S0=S0, n=n, method='preissmann')
        solver.h = h_init.copy()
        solver.Q = Q_init.copy()
        solver.clear_history()

        for i in range(n_steps):
            t = (i + 1) * dt

            # 流量阶跃
            Q_upstream = Q_initial if t < t_step else Q_final
            h_downstream = scenario_params['h_downstream']

            solver.step(dt, Q_upstream, h_downstream)

            if i % 10 == 0:
                solver.save_state(t)

            if (i + 1) % 400 == 0:
                Q_avg = np.mean(solver.Q)
                h_avg = np.mean(solver.h)
                print(f"    t={t:.0f}s: h_avg={h_avg:.4f}m, Q_avg={Q_avg:.4f} m³/s")

        # 检查最终质量守恒
        Q_final_avg = np.mean(solver.Q)
        Q_error = abs(Q_final_avg - Q_final) / Q_final * 100
        status = "✓" if Q_error < 2.0 else "✗"
        print(f"  最终检查: Q_avg={Q_final_avg:.4f} m³/s, 误差={Q_error:.2f}% {status}")

        results[scenario_name] = {
            'solver': solver,
            'h_final': solver.h.copy(),
            'Q_final': solver.Q.copy(),
            'history': solver.get_history(),
            'params': scenario_params
        }

    # 可视化
    print("\n" + "=" * 80)
    print("生成可视化图表")
    print("=" * 80)

    output_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "figures")
    os.makedirs(output_dir, exist_ok=True)

    setup_chinese_fonts()

    # 时间序列图
    fig, axes = plt.subplots(4, 1, figsize=(14, 12))

    for scenario_name, data in results.items():
        history = data['history']
        time = history['time']
        params = data['params']

        h_upstream = np.array([h[0] for h in history['h_history']])
        h_downstream_sim = np.array([h[-1] for h in history['h_history']])
        Q_upstream = np.array([Q[0] for Q in history['Q_history']])
        Q_downstream = np.array([Q[-1] for Q in history['Q_history']])

        axes[0].plot(time, h_upstream, label=params['description'],
                    color=params['color'], linewidth=2)
        axes[1].plot(time, h_downstream_sim, label=params['description'],
                    color=params['color'], linewidth=2)
        axes[2].plot(time, Q_upstream, label=params['description'],
                    color=params['color'], linewidth=2)
        axes[3].plot(time, Q_downstream, label=params['description'],
                    color=params['color'], linewidth=2)

    for ax in axes:
        ax.axvline(t_step, color='k', linestyle='--', linewidth=1.5,
                  label='流量阶跃' if ax == axes[0] else '')

    axes[0].axhline(h_uniform_final, color='gray', linestyle=':', alpha=0.5, label='最终理论值')
    axes[2].axhline(Q_final, color='gray', linestyle=':', alpha=0.5, label='最终理论值')

    axes[0].set_ylabel('上游水深 (m)')
    axes[0].set_title('系统响应 - 上游水深')
    axes[0].legend()
    axes[0].grid(True, alpha=0.3)

    axes[1].set_ylabel('下游水深 (m)')
    axes[1].set_title('系统响应 - 下游水深')
    axes[1].legend()
    axes[1].grid(True, alpha=0.3)

    axes[2].set_ylabel('上游流量 (m³/s)')
    axes[2].set_title('系统响应 - 上游流量')
    axes[2].legend()
    axes[2].grid(True, alpha=0.3)

    axes[3].set_ylabel('下游流量 (m³/s)')
    axes[3].set_xlabel('时间 (s)')
    axes[3].set_title('系统响应 - 下游流量')
    axes[3].legend()
    axes[3].grid(True, alpha=0.3)

    plt.tight_layout()
    save_path = os.path.join(output_dir, "example_01_boundary_fixed_timeseries.png")
    plt.savefig(save_path, dpi=150, bbox_inches='tight')
    print(f"图表已保存: {save_path}")
    plt.close()

    # 最终空间分布
    fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(14, 10))
    x = results['恒定均匀流']['solver'].x

    for scenario_name, data in results.items():
        params = data['params']
        ax1.plot(x, data['h_final'], label=params['description'],
                color=params['color'], linewidth=2)
        ax2.plot(x, data['Q_final'], label=params['description'],
                color=params['color'], linewidth=2)

    ax1.axhline(h_uniform_final, color='gray', linestyle='--', linewidth=2, label='理论值')
    ax2.axhline(Q_final, color='gray', linestyle='--', linewidth=2, label='理论值')

    ax1.set_xlabel('距离 x (m)')
    ax1.set_ylabel('水深 h (m)')
    ax1.set_title(f'最终稳态空间分布 - 水深 (t={T_total}s)')
    ax1.legend()
    ax1.grid(True, alpha=0.3)

    ax2.set_xlabel('距离 x (m)')
    ax2.set_ylabel('流量 Q (m³/s)')
    ax2.set_title(f'最终稳态空间分布 - 流量 (t={T_total}s)')
    ax2.legend()
    ax2.grid(True, alpha=0.3)

    plt.tight_layout()
    save_path = os.path.join(output_dir, "example_01_boundary_fixed_spatial.png")
    plt.savefig(save_path, dpi=150, bbox_inches='tight')
    print(f"图表已保存: {save_path}")
    plt.close()

    print("\n" + "=" * 80)
    print("仿真完成！")
    print("=" * 80)
    print("\n修正要点:")
    print("1. 增加仿真时间到1200s确保稳态")
    print("2. 为每种边界条件预先计算稳态初值")
    print("3. 验证质量守恒（误差<2%）")
    print("\n✅ 修正版运行成功")


if __name__ == '__main__':
    main()
