#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
案例1: 溃坝模拟 - 方法对比

对比Phase 8.1+8.2与原始方法在经典溃坝问题上的性能：
- 原始WENO3
- Phase 8.1 PP-WENO3
- Phase 8.2 WD-Enhanced-WENO3

工程背景:
水坝溃决是水利工程中最严重的灾害，需要精确预测洪水波传播。
涉及干床、激波、湿干界面等复杂物理现象。

作者: HydroClaude Team
日期: 2025-10-31
阶段: Stage 8 - Phase 8.3
"""

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..', '..'))

import numpy as np
import matplotlib
matplotlib.use("Agg")  # Non-interactive mode
import matplotlib.pyplot as plt
from typing import Dict, List, Tuple

from solvers.godunov_fvm_weno3 import GodunvFVMWENO3
from solvers.positivity_preserving_weno3 import PositivityPreservingWENO3
from solvers.wet_dry_enhanced_weno3 import WetDryEnhancedWENO3


def stoker_analytical_solution(
    x: np.ndarray,
    t: float,
    h_L: float,
    h_R: float,
    x_dam: float,
    g: float = 9.81
) -> Tuple[np.ndarray, np.ndarray]:
    """
    Stoker (1957) 溃坝解析解（干床情况）

    假设：
    - 左侧水深h_L，右侧干床h_R=0
    - 瞬时溃坝
    - 无摩阻

    解的结构：
    - 稀疏波（左侧）
    - 洪水波前（右侧，速度c_front = 2*sqrt(g*h_L)）

    Args:
        x: 空间坐标数组
        t: 时间
        h_L: 上游水深
        h_R: 下游水深（通常=0）
        x_dam: 坝位置
        g: 重力加速度

    Returns:
        h, u: 水深和流速数组
    """
    n = len(x)
    h = np.zeros(n)
    u = np.zeros(n)

    if t <= 0:
        # 初始条件
        h = np.where(x <= x_dam, h_L, h_R)
        u = np.zeros_like(x)
        return h, u

    # 特征速度
    c_L = np.sqrt(g * h_L)

    # 稀疏波左边界
    x_left = x_dam - t * c_L

    # 洪水波前位置（速度 = 2*c_L）
    x_front = x_dam + 2.0 * t * c_L

    for i in range(n):
        if x[i] <= x_left:
            # 区域1：静止上游水
            h[i] = h_L
            u[i] = 0.0

        elif x[i] <= x_dam:
            # 区域2：稀疏波
            xi = (x[i] - x_dam) / t
            c = (2.0 * c_L - 2.0 * xi) / 3.0
            if c > 0:
                h[i] = c**2 / g
                u[i] = (2.0 / 3.0) * (c_L + xi)
            else:
                h[i] = 0.0
                u[i] = 0.0

        elif x[i] <= x_front:
            # 区域3：均匀流
            h[i] = (4.0 / 9.0) * h_L
            u[i] = (2.0 / 3.0) * c_L

        else:
            # 区域4：干床
            h[i] = h_R
            u[i] = 0.0

    return h, u


def compute_errors(
    h_num: np.ndarray,
    h_exact: np.ndarray,
    wet_mask: np.ndarray = None
) -> Dict[str, float]:
    """
    计算误差指标

    Args:
        h_num: 数值解
        h_exact: 精确解
        wet_mask: 湿区掩码（可选）

    Returns:
        dict: 误差指标
    """
    if wet_mask is None:
        wet_mask = (h_exact > 1e-6) | (h_num > 1e-6)

    # 只在湿区计算误差
    h_num_wet = h_num[wet_mask]
    h_exact_wet = h_exact[wet_mask]

    if len(h_num_wet) == 0:
        return {
            'L1_abs': 0.0,
            'L2_abs': 0.0,
            'Linf_abs': 0.0,
            'L1_rel': 0.0,
            'L2_rel': 0.0,
            'Linf_rel': 0.0
        }

    # 绝对误差
    err = np.abs(h_num_wet - h_exact_wet)
    L1_abs = np.mean(err)
    L2_abs = np.sqrt(np.mean(err**2))
    Linf_abs = np.max(err)

    # 相对误差（百分比）
    h_scale = np.max(h_exact_wet) if np.max(h_exact_wet) > 0 else 1.0
    L1_rel = L1_abs / h_scale * 100
    L2_rel = L2_abs / h_scale * 100
    Linf_rel = Linf_abs / h_scale * 100

    return {
        'L1_abs': L1_abs,
        'L2_abs': L2_abs,
        'Linf_abs': Linf_abs,
        'L1_rel': L1_rel,
        'L2_rel': L2_rel,
        'Linf_rel': Linf_rel
    }


def run_dam_break_simulation(
    solver_class,
    solver_name: str,
    h_upstream: float = 10.0,
    h_downstream: float = 0.0,
    dam_position: float = 500.0,
    channel_length: float = 2000.0,
    channel_width: float = 50.0,
    n_cells: int = 500,
    t_end: float = 30.0,
    cfl: float = 0.3,
    **solver_kwargs
) -> Dict:
    """
    运行溃坝模拟

    Args:
        solver_class: 求解器类
        solver_name: 求解器名称
        h_upstream: 上游水深 (m)
        h_downstream: 下游水深 (m，通常=0)
        dam_position: 坝位置 (m)
        channel_length: 渠道长度 (m)
        channel_width: 渠道宽度 (m)
        n_cells: 网格数
        t_end: 终止时间 (s)
        cfl: CFL数
        **solver_kwargs: 求解器额外参数

    Returns:
        dict: 模拟结果
    """
    print(f"\n{'='*70}")
    print(f"{solver_name}: 溃坝模拟")
    print(f"{'='*70}")

    print(f"\n配置:")
    print(f"  上游水深: {h_upstream} m")
    print(f"  下游水深: {h_downstream} m")
    print(f"  坝位置: {dam_position} m")
    print(f"  渠道长度: {channel_length} m")
    print(f"  网格数: {n_cells}")
    print(f"  模拟时间: {t_end} s")

    # 创建求解器
    solver = solver_class(
        width=channel_width,
        length=channel_length,
        n_cells=n_cells,
        manning_n=0.0,  # 无摩阻（对比解析解）
        slope=0.0,
        cfl=cfl,
        use_enhanced_bc=True,
        well_balanced=False,
        use_numba=False,
        **solver_kwargs
    )

    # 初始条件
    x = solver.x
    h_init = np.where(x <= dam_position, h_upstream, h_downstream)
    Q_init = np.zeros_like(x)  # 静止初值

    bc_left = {'type': 'transmissive'}
    bc_right = {'type': 'transmissive'}
    # GodunvFVMSolver需要手动初始化

    solver.h = h_init.copy()

    solver.Q = Q_init.copy()

    solver.bc_left = bc_left

    solver.bc_right = bc_right

    # 记录初始质量
    initial_mass = np.sum(solver.h * solver.dx * solver.B)

    # 运行模拟
    print(f"\n运行中...")
    step_count = 0
    h_min_history = []
    h_max_history = []
    t_history = []

    while solver.t < t_end:
        solver.step()
        step_count += 1

        h_min = np.min(solver.h)
        h_max = np.max(solver.h)
        h_min_history.append(h_min)
        h_max_history.append(h_max)
        t_history.append(solver.t)

        if step_count % 100 == 0:
            print(f"  Step {step_count}: t={solver.t:.3f}s, h∈[{h_min:.4f}, {h_max:.4f}]")

    print(f"\n完成！总步数: {step_count}, 最终时间: t={solver.t:.3f}s")

    # 计算最终质量
    final_mass = np.sum(solver.h * solver.dx * solver.B)
    mass_error = abs(final_mass - initial_mass) / initial_mass * 100 if initial_mass > 0 else 0.0

    # 数值解
    x_num = solver.x
    h_num = solver.h
    u_num = solver.Q / (solver.B * np.maximum(solver.h, solver.eps_dry))

    # 精确解（Stoker）
    x_exact = np.linspace(0, channel_length, 2000)
    h_exact, u_exact = stoker_analytical_solution(
        x_exact, solver.t, h_upstream, h_downstream, dam_position
    )

    # 插值数值解到精确解网格
    h_num_interp = np.interp(x_exact, x_num, h_num)

    # 计算误差
    errors = compute_errors(h_num_interp, h_exact)

    # 打印结果
    print(f"\n{'='*70}")
    print("结果汇总")
    print(f"{'='*70}")
    print(f"水深范围: [{np.min(h_num):.4f}, {np.max(h_num):.4f}] m")
    print(f"\n误差指标:")
    print(f"  L1  = {errors['L1_abs']:.4f} m  ({errors['L1_rel']:.2f}%)")
    print(f"  L2  = {errors['L2_abs']:.4f} m  ({errors['L2_rel']:.2f}%)")
    print(f"  L∞  = {errors['Linf_abs']:.4f} m  ({errors['Linf_rel']:.2f}%)")
    print(f"\n质量守恒误差: {mass_error:.4f}%")

    # 返回结果
    result = {
        'solver_name': solver_name,
        'x_num': x_num,
        'h_num': h_num,
        'u_num': u_num,
        'x_exact': x_exact,
        'h_exact': h_exact,
        'u_exact': u_exact,
        'errors': errors,
        'step_count': step_count,
        't_final': solver.t,
        'h_min_history': np.array(h_min_history),
        'h_max_history': np.array(h_max_history),
        't_history': np.array(t_history),
        'initial_mass': initial_mass,
        'final_mass': final_mass,
        'mass_error': mass_error
    }

    # 如果有统计信息，添加
    if hasattr(solver, 'get_statistics'):
        result['stats'] = solver.get_statistics()
        solver.print_statistics()

    # 正定性检查
    h_min_all = np.min(h_min_history)
    result['h_min_all'] = h_min_all
    if h_min_all >= 0.0:
        print(f"\n 正定性保持成功: h_min = {h_min_all:.6e} >= 0")
    else:
        print(f"\n 正定性违背: h_min = {h_min_all:.6e} < 0")

    return result


def plot_dam_break_comparison(
    results: List[Dict],
    save_path: str = None
):
    """
    绘制溃坝模拟对比图

    Args:
        results: 结果列表
        save_path: 保存路径
    """
    fig = plt.figure(figsize=(16, 12))
    gs = fig.add_gridspec(3, 2, hspace=0.3, wspace=0.3)

    # 1. 水深对比
    ax = fig.add_subplot(gs[0, :])
    for res in results:
        ax.plot(res['x_num'], res['h_num'], 'o-', label=res['solver_name'],
                markersize=3, alpha=0.7)
    ax.plot(results[0]['x_exact'], results[0]['h_exact'], 'k-',
            linewidth=2.5, label='Stoker Analytical', alpha=0.8)
    ax.set_xlabel('Distance x (m)', fontsize=12, fontweight='bold')
    ax.set_ylabel('Water Depth h (m)', fontsize=12, fontweight='bold')
    ax.set_title(f'Dam Break Simulation - Water Depth (t={results[0]["t_final"]:.1f}s)',
                 fontsize=14, fontweight='bold')
    ax.legend(fontsize=11)
    ax.grid(True, alpha=0.3)

    # 2. 误差对比（柱状图）
    ax = fig.add_subplot(gs[1, 0])
    solver_names = [res['solver_name'] for res in results]
    l2_errors = [res['errors']['L2_rel'] for res in results]
    colors = ['#1f77b4', '#ff7f0e', '#2ca02c']
    bars = ax.bar(range(len(solver_names)), l2_errors, color=colors[:len(results)], alpha=0.7)
    ax.set_xticks(range(len(solver_names)))
    ax.set_xticklabels(solver_names, rotation=15, ha='right')
    ax.set_ylabel('L2 Error (%)', fontsize=11, fontweight='bold')
    ax.set_title('L2 Error Comparison', fontsize=12, fontweight='bold')
    ax.grid(True, alpha=0.3, axis='y')

    # 添加数值标签
    for i, (bar, val) in enumerate(zip(bars, l2_errors)):
        ax.text(bar.get_x() + bar.get_width()/2, bar.get_height(),
                f'{val:.2f}%', ha='center', va='bottom', fontsize=10, fontweight='bold')

    # 3. 质量守恒误差
    ax = fig.add_subplot(gs[1, 1])
    mass_errors = [res['mass_error'] for res in results]
    bars = ax.bar(range(len(solver_names)), mass_errors, color=colors[:len(results)], alpha=0.7)
    ax.set_xticks(range(len(solver_names)))
    ax.set_xticklabels(solver_names, rotation=15, ha='right')
    ax.set_ylabel('Mass Error (%)', fontsize=11, fontweight='bold')
    ax.set_title('Mass Conservation Error', fontsize=12, fontweight='bold')
    ax.grid(True, alpha=0.3, axis='y')
    ax.axhline(0.1, color='r', linestyle='--', alpha=0.5, label='Target (<0.1%)')
    ax.legend(fontsize=9)

    for i, (bar, val) in enumerate(zip(bars, mass_errors)):
        ax.text(bar.get_x() + bar.get_width()/2, bar.get_height(),
                f'{val:.4f}%', ha='center', va='bottom', fontsize=9, fontweight='bold')

    # 4. 水深时间历史（最小值）
    ax = fig.add_subplot(gs[2, 0])
    for res in results:
        ax.plot(res['t_history'], res['h_min_history'], '-', label=res['solver_name'],
                linewidth=2, alpha=0.8)
    ax.set_xlabel('Time t (s)', fontsize=11, fontweight='bold')
    ax.set_ylabel('Minimum Depth (m)', fontsize=11, fontweight='bold')
    ax.set_title('Minimum Depth History (Positivity Check)', fontsize=12, fontweight='bold')
    ax.legend(fontsize=10)
    ax.grid(True, alpha=0.3)
    ax.axhline(0, color='r', linestyle='--', alpha=0.5)

    # 5. 统计信息对比
    ax = fig.add_subplot(gs[2, 1])

    # 检查是否有Phase 8.1+8.2统计
    has_pp_stats = any('stats' in res and 'activation_rate' in res['stats'] for res in results)

    if has_pp_stats:
        pp_rates = []
        wd_rates = []
        labels = []

        for res in results:
            if 'stats' in res:
                stats = res['stats']
                labels.append(res['solver_name'])
                pp_rates.append(stats.get('activation_rate', 0.0) * 100)
                wd_rates.append(stats.get('interface_flux_usage_rate', 0.0) * 100)

        x_pos = np.arange(len(labels))
        width = 0.35

        bars1 = ax.bar(x_pos - width/2, pp_rates, width, label='PP Activation', alpha=0.7)
        bars2 = ax.bar(x_pos + width/2, wd_rates, width, label='WD Interface', alpha=0.7)

        ax.set_ylabel('Activation Rate (%)', fontsize=11, fontweight='bold')
        ax.set_title('Phase 8.1+8.2 Activation Statistics', fontsize=12, fontweight='bold')
        ax.set_xticks(x_pos)
        ax.set_xticklabels(labels, rotation=15, ha='right')
        ax.legend(fontsize=10)
        ax.grid(True, alpha=0.3, axis='y')
    else:
        ax.text(0.5, 0.5, 'No Phase 8.1+8.2 statistics available',
                ha='center', va='center', transform=ax.transAxes, fontsize=11)
        ax.set_title('Phase 8.1+8.2 Activation Statistics', fontsize=12, fontweight='bold')

    plt.suptitle('Dam Break Simulation: Phase 8.1+8.2 vs Baseline',
                 fontsize=16, fontweight='bold')

    if save_path:
        plt.savefig(save_path, dpi=150, bbox_inches='tight')
        print(f"\n图表已保存: {save_path}")

    return fig


def main():
    """
    主函数：对比三种求解器在溃坝问题上的性能
    """
    print("\n" + "="*80)
    print("案例1: 溃坝模拟 - Phase 8.1+8.2 vs 原始WENO3")
    print("="*80)

    # 溃坝配置
    config = {
        'h_upstream': 10.0,
        'h_downstream': 0.0,
        'dam_position': 500.0,
        'channel_length': 2000.0,
        'channel_width': 50.0,
        'n_cells': 500,
        't_end': 10.0,  # 降低目标时长: 30s->10s (更实际的测试)
        'cfl': 0.3
    }

    # 求解器配置
    solvers = [
        {
            'class': GodunvFVMWENO3,
            'name': 'WENO3 (Original)',
            'kwargs': {}
        },
        {
            'class': PositivityPreservingWENO3,
            'name': 'PP-WENO3 (Phase 8.1)',
            'kwargs': {
                'eps_pp': 1e-10,
                'theta_min': 0.0,
                'use_pp': True
            }
        },
        {
            'class': WetDryEnhancedWENO3,
            'name': 'WD-Enhanced (Phase 8.2)',
            'kwargs': {
                'eps_pp': 1e-10,
                'theta_min': 0.0,
                'wet_dry_threshold': 1e-3,  # 放宽检测阈值: 1e-4->1e-3
                'interface_theta_max': 0.3,
                'use_pp': True,
                'use_wd_flux': True
            }
        }
    ]

    # 运行所有模拟
    results = []

    for solver_config in solvers:
        print(f"\n\n{'#'*80}")
        print(f"# {solver_config['name']}")
        print(f"{'#'*80}")

        try:
            result = run_dam_break_simulation(
                solver_class=solver_config['class'],
                solver_name=solver_config['name'],
                **config,
                **solver_config['kwargs']
            )
            results.append(result)
        except Exception as e:
            print(f"\n {solver_config['name']} 失败: {e}")
            import traceback
            traceback.print_exc()

    # 对比总结
    if len(results) > 0:
        print("\n\n" + "="*80)
        print("对比总结")
        print("="*80)

        for res in results:
            err = res['errors']
            print(f"\n{res['solver_name']}:")
            print(f"  L2误差:      {err['L2_rel']:.2f}%")
            print(f"  质量守恒:    {res['mass_error']:.4f}%")
            print(f"  h_min:       {res['h_min_all']:.6e}")
            print(f"  计算步数:    {res['step_count']}")

        # 改进百分比
        if len(results) >= 3:
            print("\n" + "="*80)
            print("Phase 8.2相比原始WENO3的改进")
            print("="*80)

            l2_orig = results[0]['errors']['L2_rel']
            l2_phase82 = results[2]['errors']['L2_rel']
            l2_improve = (l2_orig - l2_phase82) / l2_orig * 100

            mass_orig = results[0]['mass_error']
            mass_phase82 = results[2]['mass_error']
            mass_improve = (mass_orig - mass_phase82) / mass_orig * 100 if mass_orig > 0 else 0

            print(f"L2误差改进:    {l2_orig:.2f}% -> {l2_phase82:.2f}% ({l2_improve:.1f}%↓)")
            print(f"质量守恒改进:  {mass_orig:.4f}% -> {mass_phase82:.4f}% ({mass_improve:.1f}%↓)")

        # 绘制对比图
        print("\n\n生成对比图...")
        output_dir = os.path.join(os.path.dirname(__file__), 'results')
        os.makedirs(output_dir, exist_ok=True)
        save_path = os.path.join(output_dir, 'dam_break_comparison.png')

        fig = plot_dam_break_comparison(results, save_path=save_path)

    print("\n\n" + "="*80)
    print("案例1完成！")
    print("="*80)

    return results


if __name__ == '__main__':
    results = main()
    plt.savefig("output.png", dpi=100, bbox_inches="tight"); plt.close("all")  # 保存并关闭
