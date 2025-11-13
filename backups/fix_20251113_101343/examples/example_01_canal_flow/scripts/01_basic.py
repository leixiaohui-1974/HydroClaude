#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
例子1：明渠非恒定流 - 重构版（简化）

使用新的基础库框架，代码更简洁、可维护

作者: Claude
日期: 2025-10-21
"""

import sys
import os
import numpy as np
import pandas as pd

# 添加项目根目录到路径
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))))

# DEPRECATED: Use HydrostaticCanalSolver instead
# # DEPRECATED: Use HydrostaticCanalSolver instead
# from solvers.canal_solver import CanalSolver
from utils.canal_utils import compute_steady_uniform_flow, get_convergence_metrics
from visualization.canal_visualizer import CanalVisualizer
from analysis.stability_evaluator import StabilityEvaluator

# Import output helper
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from output_helper import get_output_path, save_table


def main():
    """主函数"""
    print("=" * 80)
    print("例子1：明渠非恒定流仿真 - 重构版")
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

    # 边界条件
    Q_upstream = 8.0  # 上游流量 (m³/s)

    # 计算理论水深
    h_downstream = compute_steady_uniform_flow(Q_upstream, B, S0, n)

    print(f"渠道长度: {length} m")
    print(f"渠道宽度: {B} m")
    print(f"渠底坡度: {S0}")
    print(f"Manning糙率: {n}")
    print(f"网格数: {nx}")
    print(f"上游流量: {Q_upstream} m³/s")
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
                print(f"  Step {i+1}/{n_steps}: h_avg={h_avg:.6f} m, Q_avg={Q_avg:.6f} m³/s")

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

    viz = CanalVisualizer(use_chinese=False)  # 使用英文以避免字体问题

    # 方法对比图
    comparison_data = {}
    for method in methods:
        comparison_data[method] = {
            'h': results[method]['h'],
            'Q': results[method]['Q']
        }

    save_path = get_output_path('figures', "01_basic_comparison.png")
    viz.plot_methods_comparison(
        x=solvers['PREISSMANN'].x,
        results=comparison_data,
        h_theory=h_downstream,
        Q_theory=Q_upstream,
        title="Methods Comparison - Final State",
        save_path=save_path
    )
    print(f"   Saved figure: 01_basic_comparison.png")

    # 单个方法的时空分布
    for method in methods:
        save_path = get_output_path('figures', f"01_basic_{method.lower()}.png")
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
        print(f"   Saved figure: 01_basic_{method.lower()}.png")

    # ========================================================================
    # 6. 收敛性分析
    # ========================================================================
    print("\n6. 收敛性分析")
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
    # 7. 保存数据表
    # ========================================================================
    print("\n7. 保存数据表")
    print("-" * 80)

    # 保存收敛性结果表
    convergence_data = []
    for method in methods:
        history = results[method]['history']
        metrics = get_convergence_metrics(
            time=history['time'],
            h_history=history['h_history'],
            Q_history=history['Q_history']
        )
        convergence_data.append({
            'Method': method,
            'h_CV_upstream (%)': metrics['cv_h_upstream'],
            'h_CV_downstream (%)': metrics['cv_h_downstream'],
            'Q_CV_upstream (%)': metrics['cv_Q_upstream'],
            'Q_CV_downstream (%)': metrics['cv_Q_downstream'],
            'Max_CV (%)': metrics['max_cv'],
            'Converged': metrics['converged']
        })

    df = pd.DataFrame(convergence_data)
    save_table(df, '01_basic_convergence.csv', index=False)

    # 保存最终分布数据
    distribution_data = []
    for method in methods:
        x = solvers[method].x
        h = results[method]['h']
        Q = results[method]['Q']
        for i in range(len(x)):
            distribution_data.append({
                'Method': method,
                'Position (m)': x[i],
                'Water_Depth (m)': h[i],
                'Discharge (m³/s)': Q[i]
            })

    df_dist = pd.DataFrame(distribution_data)
    save_table(df_dist, '01_basic_distribution.csv', index=False)

    # ========================================================================
    # 完成
    # ========================================================================
    print("\n" + "=" * 80)
    print("仿真完成！")
    print("=" * 80)
    print(f"\n所有输出已保存到: results/")
    print("  Figures: results/figures/")
    print("  Tables: results/tables/")
    print("\n 例子1（重构版）运行成功")


if __name__ == '__main__':
    main()
