#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
例子1扩展：不同下游边界条件的影响研究

研究三种下游边界条件：
1. 高水位边界（回水效应）
2. 恒定均匀流边界（基准）
3. 低水位边界（泵站/跌水）

并在时间中部施加上游流量阶跃，观察系统动态响应

作者: Claude
日期: 2025-10-21
"""

import sys
import os
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt

# 添加项目根目录到路径
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))))

from solvers.canal_solver import CanalSolver
from utils.canal_utils import compute_steady_uniform_flow, setup_chinese_fonts
from visualization.canal_visualizer import CanalVisualizer


def main():
    """主函数"""
    print("=" * 80)
    print("例子1扩展：不同下游边界条件的影响研究")
    print("=" * 80)

    # ========================================================================
    # 1. 参数设置
    # ========================================================================
    print("\n1. 参数设置")
    print("-" * 80)

    # 渠道参数
    length = 1000.0  # 渠道长度 (m)
    B = 10.0         # 渠道宽度 (m)
    S0 = 0.001       # 渠底坡度
    n = 0.025        # Manning糙率系数
    nx = 201         # 空间网格数

    # 上游流量边界（时间中部发生阶跃）
    Q_initial = 8.0   # 初始流量 (m³/s)
    Q_final = 10.0    # 阶跃后流量 (m³/s)
    t_step = 150.0    # 阶跃时刻 (s)

    # 计算恒定均匀流水深（基准）
    h_uniform_initial = compute_steady_uniform_flow(Q_initial, B, S0, n)
    h_uniform_final = compute_steady_uniform_flow(Q_final, B, S0, n)

    print(f"渠道长度: {length} m")
    print(f"渠道宽度: {B} m")
    print(f"渠底坡度: {S0}")
    print(f"Manning糙率: {n}")
    print(f"网格数: {nx}")
    print(f"\n上游流量:")
    print(f"  初始流量: {Q_initial} m³/s")
    print(f"  最终流量: {Q_final} m³/s")
    print(f"  阶跃时刻: {t_step} s")
    print(f"\n理论水深（恒定均匀流）:")
    print(f"  初始水深: {h_uniform_initial:.6f} m")
    print(f"  最终水深: {h_uniform_final:.6f} m")

    # 定义三种下游边界条件
    scenarios = {
        '高水位_回水效应': {
            'h_downstream': h_uniform_final + 0.15,  # 高出15cm
            'description': '下游高水位（回水区）',
            'color': '#d62728'  # 红色
        },
        '恒定均匀流_基准': {
            'h_downstream': h_uniform_final,  # 理论值
            'description': '恒定均匀流（基准）',
            'color': '#2ca02c'  # 绿色
        },
        '低水位_泵站': {
            'h_downstream': h_uniform_final - 0.10,  # 低10cm
            'description': '下游低水位（泵站抽水）',
            'color': '#1f77b4'  # 蓝色
        }
    }

    print(f"\n下游边界条件:")
    for name, params in scenarios.items():
        print(f"  {params['description']}: h = {params['h_downstream']:.6f} m "
              f"(Δh = {params['h_downstream'] - h_uniform_final:+.4f} m)")

    # 时间参数
    dt = 0.5        # 时间步长 (s)
    T_total = 400.0 # 总时间 (s)
    n_steps = int(T_total / dt)

    print(f"\n时间参数:")
    print(f"  时间步长: {dt} s")
    print(f"  总时间: {T_total} s")
    print(f"  总步数: {n_steps}")

    # ========================================================================
    # 2. 运行三种场景
    # ========================================================================
    print("\n2. 运行三种边界条件场景")
    print("-" * 80)

    results = {}

    for scenario_name, scenario_params in scenarios.items():
        print(f"\n运行场景: {scenario_params['description']}")
        print(f"  下游水深: {scenario_params['h_downstream']:.6f} m")

        # 创建求解器
        solver = CanalSolver(
            length=length,
            nx=nx,
            B=B,
            S0=S0,
            n=n,
            method='preissmann'  # 使用Preissmann格式
        )

        # 使用初始恒定均匀流作为初值
        solver.reset_with_steady_state(Q_initial)

        # 时间演化
        for i in range(n_steps):
            t = (i + 1) * dt

            # 上游流量边界（阶跃）
            if t < t_step:
                Q_upstream = Q_initial
            else:
                Q_upstream = Q_final

            # 下游水深边界（固定）
            h_downstream = scenario_params['h_downstream']

            # 执行一步
            h, Q = solver.step(dt, Q_upstream, h_downstream)

            # 保存历史（每5步保存一次）
            if i % 5 == 0:
                solver.save_state(t)

            # 打印进度（每100步）
            if (i + 1) % 100 == 0:
                h_avg = np.mean(h)
                Q_avg = np.mean(Q)
                print(f"  t={t:.1f}s: h_avg={h_avg:.6f} m, Q_avg={Q_avg:.6f} m³/s")

        # 保存结果
        results[scenario_name] = {
            'solver': solver,
            'h_final': solver.h.copy(),
            'Q_final': solver.Q.copy(),
            'history': solver.get_history(),
            'params': scenario_params
        }

        print(f"✓ 场景 '{scenario_params['description']}' 完成")

    # ========================================================================
    # 3. 可视化对比
    # ========================================================================
    print("\n3. 生成可视化图表")
    print("-" * 80)

    output_dir = os.path.join(
        os.path.dirname(os.path.abspath(__file__)),
        "..", "figures"
    )
    os.makedirs(output_dir, exist_ok=True)

    setup_chinese_fonts()

    # === 图1: 时间序列对比（上下游水深和流量）===
    fig, axes = plt.subplots(4, 1, figsize=(14, 12))

    for scenario_name, data in results.items():
        history = data['history']
        time = history['time']
        params = data['params']

        # 提取上游和下游的时间序列
        h_upstream = np.array([h[0] for h in history['h_history']])
        h_downstream_sim = np.array([h[-1] for h in history['h_history']])
        Q_upstream = np.array([Q[0] for Q in history['Q_history']])
        Q_downstream = np.array([Q[-1] for Q in history['Q_history']])

        # 上游水深
        axes[0].plot(time, h_upstream, label=params['description'],
                    color=params['color'], linewidth=2)

        # 下游水深
        axes[1].plot(time, h_downstream_sim, label=params['description'],
                    color=params['color'], linewidth=2)

        # 上游流量
        axes[2].plot(time, Q_upstream, label=params['description'],
                    color=params['color'], linewidth=2)

        # 下游流量
        axes[3].plot(time, Q_downstream, label=params['description'],
                    color=params['color'], linewidth=2)

    # 添加阶跃时刻的垂直线
    for ax in axes:
        ax.axvline(t_step, color='k', linestyle='--', linewidth=1.5,
                  label='流量阶跃时刻' if ax == axes[0] else '')

    # 添加理论值参考线
    axes[0].axhline(h_uniform_initial, color='gray', linestyle=':',
                   alpha=0.5, label='初始理论值')
    axes[0].axhline(h_uniform_final, color='gray', linestyle='-.',
                   alpha=0.5, label='最终理论值')
    axes[1].axhline(h_uniform_initial, color='gray', linestyle=':',
                   alpha=0.5, label='初始理论值')
    axes[1].axhline(h_uniform_final, color='gray', linestyle='-.',
                   alpha=0.5, label='最终理论值')

    # 设置标签和标题
    axes[0].set_ylabel('上游水深 (m)')
    axes[0].set_title('不同下游边界条件下的系统响应 - 上游水深')
    axes[0].legend(loc='best')
    axes[0].grid(True, alpha=0.3)

    axes[1].set_ylabel('下游水深 (m)')
    axes[1].set_title('不同下游边界条件下的系统响应 - 下游水深')
    axes[1].legend(loc='best')
    axes[1].grid(True, alpha=0.3)

    axes[2].set_ylabel('上游流量 (m³/s)')
    axes[2].set_title('不同下游边界条件下的系统响应 - 上游流量')
    axes[2].legend(loc='best')
    axes[2].grid(True, alpha=0.3)

    axes[3].set_ylabel('下游流量 (m³/s)')
    axes[3].set_xlabel('时间 (s)')
    axes[3].set_title('不同下游边界条件下的系统响应 - 下游流量')
    axes[3].legend(loc='best')
    axes[3].grid(True, alpha=0.3)

    plt.tight_layout()
    save_path = os.path.join(output_dir, "example_01_boundary_conditions_timeseries.png")
    plt.savefig(save_path, dpi=150, bbox_inches='tight')
    print(f"图表已保存: {save_path}")
    plt.close()

    # === 图2: 最终空间分布对比 ===
    fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(14, 10))

    x = results['恒定均匀流_基准']['solver'].x

    for scenario_name, data in results.items():
        params = data['params']

        # 水深分布
        ax1.plot(x, data['h_final'], label=params['description'],
                color=params['color'], linewidth=2)

        # 流量分布
        ax2.plot(x, data['Q_final'], label=params['description'],
                color=params['color'], linewidth=2)

    # 理论值参考线
    ax1.axhline(h_uniform_final, color='gray', linestyle='--',
               linewidth=2, label=f'理论值 ({h_uniform_final:.6f} m)')
    ax2.axhline(Q_final, color='gray', linestyle='--',
               linewidth=2, label=f'理论值 ({Q_final:.2f} m³/s)')

    ax1.set_xlabel('距离 x (m)')
    ax1.set_ylabel('水深 h (m)')
    ax1.set_title('最终状态空间分布 - 水深（t = 400s）')
    ax1.legend(loc='best')
    ax1.grid(True, alpha=0.3)

    ax2.set_xlabel('距离 x (m)')
    ax2.set_ylabel('流量 Q (m³/s)')
    ax2.set_title('最终状态空间分布 - 流量（t = 400s）')
    ax2.legend(loc='best')
    ax2.grid(True, alpha=0.3)

    plt.tight_layout()
    save_path = os.path.join(output_dir, "example_01_boundary_conditions_spatial.png")
    plt.savefig(save_path, dpi=150, bbox_inches='tight')
    print(f"图表已保存: {save_path}")
    plt.close()

    # === 图3: 回水曲线分析 ===
    fig, ax = plt.subplots(figsize=(14, 8))

    for scenario_name, data in results.items():
        params = data['params']
        # 计算相对于理论值的水深偏差
        h_deviation = data['h_final'] - h_uniform_final

        ax.plot(x, h_deviation * 100, label=params['description'],
               color=params['color'], linewidth=2.5)

    ax.axhline(0, color='gray', linestyle='--', linewidth=2,
              label='恒定均匀流基准')
    ax.set_xlabel('距离 x (m)')
    ax.set_ylabel('水深偏差 Δh (cm)')
    ax.set_title('回水效应分析 - 相对于恒定均匀流的水深偏差')
    ax.legend(loc='best')
    ax.grid(True, alpha=0.3)

    # 添加注释
    ax.text(50, ax.get_ylim()[1] * 0.9,
           '正值 = 回水\n负值 = 降落',
           bbox=dict(boxstyle='round', facecolor='wheat', alpha=0.5),
           fontsize=11)

    plt.tight_layout()
    save_path = os.path.join(output_dir, "example_01_boundary_conditions_backwater.png")
    plt.savefig(save_path, dpi=150, bbox_inches='tight')
    print(f"图表已保存: {save_path}")
    plt.close()

    # ========================================================================
    # 4. 定量分析
    # ========================================================================
    print("\n4. 定量分析")
    print("-" * 80)

    print("\n【回水效应分析】")
    for scenario_name, data in results.items():
        params = data['params']
        h_final = data['h_final']

        # 计算回水长度（水深偏差超过1cm的距离）
        h_deviation = h_final - h_uniform_final
        backwater_indices = np.where(np.abs(h_deviation) > 0.01)[0]

        if len(backwater_indices) > 0:
            backwater_length = x[backwater_indices[-1]] - x[backwater_indices[0]]
        else:
            backwater_length = 0.0

        # 最大水深偏差
        max_deviation = np.max(np.abs(h_deviation))

        # 上游影响
        h_upstream_deviation = h_final[0] - h_uniform_final

        print(f"\n{params['description']}:")
        print(f"  下游边界水深: {params['h_downstream']:.6f} m")
        print(f"  下游边界偏差: {params['h_downstream'] - h_uniform_final:+.4f} m "
              f"({(params['h_downstream'] - h_uniform_final)/h_uniform_final*100:+.2f}%)")
        print(f"  最大水深偏差: {max_deviation:.4f} m ({max_deviation*100:.2f} cm)")
        print(f"  上游水深偏差: {h_upstream_deviation:+.6f} m ({h_upstream_deviation*100:+.2f} cm)")
        print(f"  回水影响长度: {backwater_length:.1f} m ({backwater_length/length*100:.1f}%)")

    # ========================================================================
    # 完成
    # ========================================================================
    print("\n" + "=" * 80)
    print("仿真完成！")
    print("=" * 80)
    print(f"\n所有图表已保存到: {output_dir}")
    print("\n关键发现:")
    print("1. 高水位边界产生显著回水效应，影响上游水深")
    print("2. 低水位边界产生降落水面，上游水深略有降低")
    print("3. 恒定均匀流边界作为理想基准情况")
    print("4. 流量阶跃后系统需要时间重新达到新的平衡状态")
    print("\n✅ 例子1扩展（边界条件研究）运行成功")


if __name__ == '__main__':
    main()
