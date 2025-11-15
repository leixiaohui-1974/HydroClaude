#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
例子1：明渠非恒定流 - 嵌入动画版本

展示如何在示例脚本中嵌入动画生成功能，可通过--animate参数控制

使用方法:
    python 01_basic_with_animation.py              # 不生成动画
    python 01_basic_with_animation.py --animate    # 生成动画
    python 01_basic_with_animation.py --animate --animation-fps 15  # 自定义帧率

作者: Claude
日期: 2025-10-22
"""

import sys
import os
import numpy as np

from pathlib import Path
# ScriptHelper path setup
script_path = Path(__file__).resolve()
project_root = script_path.parents[3]
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))
from utils.script_helper import ScriptHelper
EXAMPLES_DIR = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(EXAMPLES_DIR))

from solvers.hydrostatic_canal_solver import CanalSolver
from utils.canal_utils import compute_steady_uniform_flow, get_convergence_metrics
from visualization.canal_visualizer import CanalVisualizer
from analysis.stability_evaluator import StabilityEvaluator


import argparse

# 添加项目根目录到路径
EXAMPLES_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from animation_utils import AnimationGenerator
def parse_args():
    """解析命令行参数"""
    parser = argparse.ArgumentParser(
        description='明渠非恒定流仿真 - 嵌入动画版本'
    )
    parser.add_argument(
        '--animate',
        action='store_true',
        help='生成动画（默认：不生成）'
    )
    parser.add_argument(
        '--animation-fps',
        type=int,
        default=10,
        help='动画帧率 (默认: 10)'
    )
    parser.add_argument(
        '--animation-dpi',
        type=int,
        default=100,
        help='动画DPI (默认: 100)'
    )
    return parser.parse_args()


def main():
    """主函数"""
    args = parse_args()

    print("=" * 80)
    print("例子1：明渠非恒定流仿真 - 嵌入动画版本")
    print("=" * 80)
    if args.animate:
        print(f"动画生成：已启用 (FPS={args.animation_fps}, DPI={args.animation_dpi})")
    else:
        print("动画生成：未启用（使用 --animate 参数启用）")

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

    # 边界条件
    Q_upstream = 8.0  # 上游流量 (m^3/s)

    # 计算理论水深
    h_downstream = compute_steady_uniform_flow(Q_upstream, B, S0, n)

    print(f"渠道长度: {length} m")
    print(f"渠道宽度: {B} m")
    print(f"渠底坡度: {S0}")
    print(f"Manning糙率: {n}")
    print(f"网格数: {nx}")
    print(f"上游流量: {Q_upstream} m^3/s")
    print(f"理论水深: {h_downstream:.6f} m")

    # 时间参数
    dt = 0.5        # 时间步长 (s)
    T_total = 300.0 # 总时间 (s)
    n_steps = int(T_total / dt)

    print(f"时间步长: {dt} s")
    print(f"总时间: {T_total} s")
    print(f"总步数: {n_steps}")

    # ========================================================================
    # 2. 创建求解器并初始化
    # ========================================================================
    print("\n2. 创建求解器")
    print("-" * 80)

    # 测试三种方法
    methods = ['EXPLICIT', 'PREISSMANN', 'HLL']
    solvers = {}
    results = {}

    for method in methods:
        print(f"  - {method} 求解器")
        solver = CanalSolver(
            length=length,
            nx=nx,
            B=B,
            S0=S0,
            n=n,
            method=method
        )
        # 使用恒定均匀流作为初值
        solver.reset_with_steady_state(Q_upstream)
        solvers[method] = solver

    # ========================================================================
    # 3. 运行仿真
    # ========================================================================
    print("\n3. 运行仿真")
    print("-" * 80)

    for method, solver in solvers.items():
        print(f"\n运行 {method} 方法...")

        for i in range(n_steps):
            # 执行一步
            h, Q = solver.step(dt, Q_upstream, h_downstream)

            # 保存历史（每10步保存一次）
            if i % 10 == 0:
                solver.save_state((i+1) * dt)

            # 打印进度（每100步）
            if (i+1) % 100 == 0:
                h_avg = np.mean(h)
                Q_avg = np.mean(Q)
                print(f"  Step {i+1}/{n_steps}: h_avg={h_avg:.6f} m, Q_avg={Q_avg:.6f} m^3/s")

        # 保存结果
        results[method] = {
            'h': solver.h.copy(),
            'Q': solver.Q.copy(),
            'history': solver.get_history()
        }

        print(f" {method} 完成")

    # ========================================================================
    # 4. 稳定性评估
    # ========================================================================
    print("\n4. 稳定性评估")
    print("-" * 80)

    evaluator = StabilityEvaluator()
    canal_params = {
        'length': length,
        'width': B,
        'slope': S0,
        'manning_n': n,
        'nx': nx
    }

    for method in methods:
        history = results[method]['history']
        eval_result = evaluator.evaluate(
            time=history['time'],
            h_history=history['h_history'],
            Q_history=history['Q_history'],
            canal_params=canal_params,
            method_name=method
        )

    evaluator.print_report()
    evaluator.compare_methods()

    # ========================================================================
    # 5. 可视化
    # ========================================================================
    print("\n5. 生成可视化图表")
    print("-" * 80)

    output_dir = os.path.join(
        os.path.dirname(os.path.abspath(__file__)),
        "..", "figures"
    )
    os.makedirs(output_dir, exist_ok=True)

    viz = CanalVisualizer(use_chinese=False)  # 使用英文以避免字体问题

    # 方法对比图
    comparison_data = {}
    for method in methods:
        comparison_data[method] = {
            'h': results[method]['h'],
            'Q': results[method]['Q']
        }

    save_path = os.path.join(output_dir, "example_01_with_anim_comparison.png")
    viz.plot_methods_comparison(
        x=solvers['PREISSMANN'].x,
        results=comparison_data,
        h_theory=h_downstream,
        Q_theory=Q_upstream,
        title="Methods Comparison - Final State",
        save_path=save_path
    )

    # 单个方法的时空分布
    for method in methods:
        save_path = os.path.join(output_dir, f"example_01_with_anim_{method.lower()}.png")
        viz.plot_spatial_distribution(
            x=solvers[method].x,
            h=results[method]['h'],
            Q=results[method]['Q'],
            h_theory=h_downstream,
            Q_theory=Q_upstream,
            title=f"{method} Method",
            save_path=save_path,
            h_margin=0.01,
            Q_margin=0.05
        )

    # ========================================================================
    # 6. 生成动画（如果启用）
    # ========================================================================
    if args.animate:
        print("\n6. 生成动画")
        print("-" * 80)

        animation_dir = os.path.join(
            os.path.dirname(os.path.abspath(__file__)),
            "..", "outputs", "animations"
        )

        anim_gen = AnimationGenerator(
            output_dir=animation_dir,
            fps=args.animation_fps,
            dpi=args.animation_dpi
        )

        # 为每个方法生成动画
        for method in methods:
            print(f"\n生成 {method} 方法的动画...")
            history = results[method]['history']

            # 提取时间序列数据（选取3个代表性位置：上游、中游、下游）
            time = history['time']
            h_history = history['h_history']
            Q_history = history['Q_history']

            nx_points = h_history.shape[1]
            idx_upstream = 0
            idx_midstream = nx_points // 2
            idx_downstream = -1

            # 时间序列动画
            try:
                gif_path = anim_gen.create_timeseries_animation(
                    t=time,
                    data={
                        'Upstream h': h_history[:, idx_upstream],
                        'Midstream h': h_history[:, idx_midstream],
                        'Downstream h': h_history[:, idx_downstream],
                        'Upstream Q': Q_history[:, idx_upstream],
                        'Midstream Q': Q_history[:, idx_midstream],
                        'Downstream Q': Q_history[:, idx_downstream],
                    },
                    filename=f'{method}_timeseries.gif',
                    title=f'{method} Method - Time Series',
                    xlabel='Time (s)',
                    ylabels={
                        'Upstream h': 'Water Depth (m)',
                        'Midstream h': 'Water Depth (m)',
                        'Downstream h': 'Water Depth (m)',
                        'Upstream Q': 'Flow Rate (m^3/s)',
                        'Midstream Q': 'Flow Rate (m^3/s)',
                        'Downstream Q': 'Flow Rate (m^3/s)',
                    },
                    reference_lines={
                        'Upstream h': h_downstream,
                        'Midstream h': h_downstream,
                        'Downstream h': h_downstream,
                        'Upstream Q': Q_upstream,
                        'Midstream Q': Q_upstream,
                        'Downstream Q': Q_upstream,
                    },
                    layout=(2, 3)
                )
                print(f"   时间序列动画已保存: {os.path.basename(gif_path)}")
            except Exception as e:
                print(f"   时间序列动画生成失败: {e}")

            # 空间分布动画
            try:
                # 准备二维数据 (时间 x 空间)
                x = solvers[method].x

                gif_path = anim_gen.create_spatial_animation(
                    x=x,
                    t=time,
                    data={
                        'Water Depth': h_history,
                        'Flow Rate': Q_history,
                    },
                    filename=f'{method}_spatial.gif',
                    title=f'{method} Method - Spatial Distribution',
                    xlabel='Distance (m)',
                    ylabels={
                        'Water Depth': 'h (m)',
                        'Flow Rate': 'Q (m^3/s)',
                    },
                    layout=(2, 1)
                )
                print(f"   空间分布动画已保存: {os.path.basename(gif_path)}")
            except Exception as e:
                print(f"   空间分布动画生成失败: {e}")

        print(f"\n所有动画已保存到: {animation_dir}")

    # ========================================================================
    # 7. 收敛性分析
    # ========================================================================
    print("\n7. 收敛性分析")
    print("-" * 80)

    for method in methods:
        history = results[method]['history']
        metrics = get_convergence_metrics(
            time=history['time'],
            h_history=history['h_history'],
            Q_history=history['Q_history']
        )

        print(f"\n{method}:")
        print(f"  上游水深CV: {metrics['cv_h_upstream']:.6f}%")
        print(f"  下游水深CV: {metrics['cv_h_downstream']:.6f}%")
        print(f"  上游流量CV: {metrics['cv_Q_upstream']:.6f}%")
        print(f"  下游流量CV: {metrics['cv_Q_downstream']:.6f}%")
        print(f"  最大CV: {metrics['max_cv']:.6f}%")
        print(f"  收敛状态: {' 收敛' if metrics['converged'] else ' 未收敛'}")

    # ========================================================================
    # 完成
    # ========================================================================
    print("\n" + "=" * 80)
    print("仿真完成！")
    print("=" * 80)
    print(f"\n所有图表已保存到: {output_dir}")
    if args.animate:
        print(f"所有动画已保存到: {animation_dir}")
    print("\n 例子1（嵌入动画版本）运行成功")


if __name__ == '__main__':
    main()
