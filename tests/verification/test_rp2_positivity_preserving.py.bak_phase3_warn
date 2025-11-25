#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
RP2测试（正定性保持改进版）

测试目标：
- 原始WENO3: RP2误差 90.55%
- 正定性保持WENO3: RP2误差 <30% (目标)

RP2配置：
- 对向流双激波
- h_L=5.0, u_L=5.0 (向右)
- h_R=5.0, u_R=-5.0 (向左)
- 精确解: h*=9.0517m (双激波)

作者: HydroClaude Team
日期: 2025-10-31
阶段: Stage 8 - Phase 8.1
"""

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..'))

import numpy as np
import matplotlib.pyplot as plt
from typing import Tuple, Dict

try:
    from solvers.godunov_fvm_weno3 import GodunvFVMWENO3
except ImportError as e:
    print(f"Import error: {e}")
    print("Make sure project root is in sys.path")
    sys.exit(1)

from solvers.positivity_preserving_weno3 import PositivityPreservingWENO3
from tests.verification.toro_riemann_solver import exact_riemann_solution, riemann_structure


def compute_errors(h_num: np.ndarray, h_exact: np.ndarray) -> Dict[str, float]:
    """
    计算误差指标

    Args:
        h_num: 数值解
        h_exact: 精确解

    Returns:
        dict: L1, L2, L∞误差（相对和绝对）
    """
    # 绝对误差
    h_err = np.abs(h_num - h_exact)
    h_L1_abs = np.mean(h_err)
    h_L2_abs = np.sqrt(np.mean(h_err**2))
    h_Linf_abs = np.max(h_err)

    # 相对误差（百分比）
    h_scale = np.max(h_exact) if np.max(h_exact) > 0 else 1.0
    h_L1_rel = h_L1_abs / h_scale * 100
    h_L2_rel = h_L2_abs / h_scale * 100
    h_Linf_rel = h_Linf_abs / h_scale * 100

    return {
        'L1_abs': h_L1_abs,
        'L2_abs': h_L2_abs,
        'Linf_abs': h_Linf_abs,
        'L1_rel': h_L1_rel,
        'L2_rel': h_L2_rel,
        'Linf_rel': h_Linf_rel
    }


def run_rp2_simulation(
    solver_class,
    solver_name: str,
    n_cells: int = 500,
    t_end: float = 0.5,
    cfl: float = 0.2,
    **solver_kwargs
) -> Dict:
    """
    运行RP2模拟

    Args:
        solver_class: 求解器类
        solver_name: 求解器名称
        n_cells: 网格数
        t_end: 终止时间
        cfl: CFL数
        **solver_kwargs: 求解器额外参数

    Returns:
        dict: 结果字典
    """
    print(f"\n{'='*70}")
    print(f"{solver_name}: RP2测试")
    print(f"{'='*70}")

    # 参数设置
    L = 100.0
    x_dam = L / 2.0
    B = 10.0

    # RP2初值
    h_L, u_L = 5.0, 5.0
    h_R, u_R = 5.0, -5.0

    print(f"初值: h_L={h_L}, u_L={u_L}, h_R={h_R}, u_R={u_R}")
    print(f"网格: {n_cells} cells, CFL={cfl}")

    # 创建求解器
    solver = solver_class(
        width=B,
        length=L,
        n_cells=n_cells,
        manning_n=0.0,
        slope=0.0,
        cfl=cfl,
        use_enhanced_bc=True,
        well_balanced=False,
        use_numba=False,  # 测试时不用Numba
        **solver_kwargs
    )

    # 初始条件
    x = solver.x
    h_init = np.where(x <= x_dam, h_L, h_R)
    Q_init = B * np.where(x <= x_dam, h_L * u_L, h_R * u_R)

    bc_left = {'type': 'transmissive'}
    bc_right = {'type': 'transmissive'}
    solver.initialize(h_init, Q_init, bc_left, bc_right)

    # 运行模拟
    print(f"\n运行中 (t_end={t_end}s)...")
    step_count = 0
    h_max_history = []

    while solver.t < t_end:
        solver.step()
        step_count += 1

        h_max = np.max(solver.h)
        h_max_history.append(h_max)

        if step_count % 50 == 0:
            print(f"  Step {step_count}: t={solver.t:.4f}s, h_max={h_max:.4f}m")

    print(f"\n完成！总步数: {step_count}, 最终时间: t={solver.t:.4f}s")

    # 数值解
    x_num = solver.x
    h_num = solver.h
    u_num = solver.Q / (solver.B * np.maximum(solver.h, solver.eps_dry))

    # 精确解
    x_exact = np.linspace(0, L, 1000)
    h_exact, u_exact = exact_riemann_solution(
        x_exact, solver.t, h_L, u_L, h_R, u_R, x_dam
    )

    # 插值数值解到精确解的网格上
    h_num_interp = np.interp(x_exact, x_num, h_num)

    # 计算误差
    errors = compute_errors(h_num_interp, h_exact)

    # 波结构
    structure = riemann_structure(h_L, u_L, h_R, u_R)

    # 打印结果
    print(f"\n{'='*70}")
    print("结果汇总")
    print(f"{'='*70}")
    print(f"数值解水深范围: [{np.min(h_num):.4f}, {np.max(h_num):.4f}] m")
    print(f"精确解中间状态: h* = {structure['h_star']:.4f} m")
    print(f"数值解最大水深: {np.max(h_num):.4f} m")
    print(f"过冲: {(np.max(h_num) - structure['h_star']) / structure['h_star'] * 100:.2f}%")
    print(f"\n误差指标:")
    print(f"  L1  = {errors['L1_abs']:.4f} m  ({errors['L1_rel']:.2f}%)")
    print(f"  L2  = {errors['L2_abs']:.4f} m  ({errors['L2_rel']:.2f}%)")
    print(f"  L∞  = {errors['Linf_abs']:.4f} m  ({errors['Linf_rel']:.2f}%)")

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
        'structure': structure,
        'step_count': step_count,
        'h_max_history': h_max_history,
        't_final': solver.t
    }

    # 如果是正定性保持求解器，添加统计信息
    if hasattr(solver, 'get_statistics'):
        result['pp_stats'] = solver.get_statistics()
        solver.print_statistics()

    return result


def plot_comparison(results: list, save_path: str = None):
    """
    绘制对比图

    Args:
        results: 结果列表
        save_path: 保存路径
    """
    fig, axes = plt.subplots(2, 2, figsize=(16, 12))

    # 1. 水深对比
    ax = axes[0, 0]
    for res in results:
        ax.plot(res['x_num'], res['h_num'], 'o-', label=res['solver_name'],
                markersize=3, alpha=0.7)
    ax.plot(results[0]['x_exact'], results[0]['h_exact'], 'k-',
            linewidth=2, label='Exact', alpha=0.8)
    ax.axhline(results[0]['structure']['h_star'], color='gray',
               linestyle='--', alpha=0.5, label=f"h*={results[0]['structure']['h_star']:.2f}m")
    ax.set_xlabel('Distance x (m)', fontsize=11, fontweight='bold')
    ax.set_ylabel('Water Depth h (m)', fontsize=11, fontweight='bold')
    ax.set_title('RP2: Water Depth Comparison', fontsize=13, fontweight='bold')
    ax.legend(fontsize=10)
    ax.grid(True, alpha=0.3)

    # 2. 误差对比（柱状图）
    ax = axes[0, 1]
    solver_names = [res['solver_name'] for res in results]
    l2_errors = [res['errors']['L2_rel'] for res in results]
    linf_errors = [res['errors']['Linf_rel'] for res in results]

    x_pos = np.arange(len(solver_names))
    width = 0.35

    ax.bar(x_pos - width/2, l2_errors, width, label='L2 Error', alpha=0.8)
    ax.bar(x_pos + width/2, linf_errors, width, label='L∞ Error', alpha=0.8)

    ax.set_ylabel('Error (%)', fontsize=11, fontweight='bold')
    ax.set_title('RP2: Error Comparison', fontsize=13, fontweight='bold')
    ax.set_xticks(x_pos)
    ax.set_xticklabels(solver_names, rotation=15, ha='right')
    ax.legend(fontsize=10)
    ax.grid(True, alpha=0.3, axis='y')

    # 添加目标线
    ax.axhline(30, color='r', linestyle='--', alpha=0.5, label='Target (<30%)')

    # 3. 水深历史（过冲演化）
    ax = axes[1, 0]
    for res in results:
        steps = np.arange(len(res['h_max_history']))
        ax.plot(steps, res['h_max_history'], label=res['solver_name'], alpha=0.7)
    ax.axhline(results[0]['structure']['h_star'], color='gray',
               linestyle='--', alpha=0.5, label=f"h* (exact)")
    ax.set_xlabel('Step', fontsize=11, fontweight='bold')
    ax.set_ylabel('Max Water Depth (m)', fontsize=11, fontweight='bold')
    ax.set_title('RP2: Maximum Depth Evolution', fontsize=13, fontweight='bold')
    ax.legend(fontsize=10)
    ax.grid(True, alpha=0.3)

    # 4. 误差分布
    ax = axes[1, 1]
    for res in results:
        h_err = np.abs(res['h_num'] - np.interp(res['x_num'], res['x_exact'], res['h_exact']))
        ax.plot(res['x_num'], h_err, label=res['solver_name'], alpha=0.7)
    ax.set_xlabel('Distance x (m)', fontsize=11, fontweight='bold')
    ax.set_ylabel('|h_num - h_exact| (m)', fontsize=11, fontweight='bold')
    ax.set_title('RP2: Error Distribution', fontsize=13, fontweight='bold')
    ax.legend(fontsize=10)
    ax.grid(True, alpha=0.3)

    plt.tight_layout()

    if save_path:
        plt.savefig(save_path, dpi=150, bbox_inches='tight')
        print(f"\n图表已保存: {save_path}")

    return fig


def main():
    """
    主测试函数：对比原始WENO3和正定性保持WENO3
    """
    print("\n" + "="*80)
    print("RP2改进测试：正定性保持WENO3 vs 原始WENO3")
    print("="*80)

    results = []

    # 1. 原始WENO3（参考）
    print("\n[1/2] 运行原始WENO3...")
    res_weno3 = run_rp2_simulation(
        solver_class=GodunvFVMWENO3,
        solver_name="WENO3 (Original)",
        n_cells=500,
        t_end=0.5,
        cfl=0.2
    )
    results.append(res_weno3)

    # 2. 正定性保持WENO3
    print("\n[2/2] 运行正定性保持WENO3...")
    res_pp = run_rp2_simulation(
        solver_class=PositivityPreservingWENO3,
        solver_name="PP-WENO3",
        n_cells=500,
        t_end=0.5,
        cfl=0.2,
        eps_pp=1e-10,
        theta_min=0.0,
        use_pp=True
    )
    results.append(res_pp)

    # 对比总结
    print("\n" + "="*80)
    print("对比总结")
    print("="*80)

    for res in results:
        err = res['errors']
        print(f"\n{res['solver_name']}:")
        print(f"  L2误差:  {err['L2_rel']:.2f}%")
        print(f"  L∞误差:  {err['Linf_rel']:.2f}%")
        print(f"  最大水深: {np.max(res['h_num']):.4f} m")
        print(f"  过冲:    {(np.max(res['h_num']) - res['structure']['h_star']) / res['structure']['h_star'] * 100:.2f}%")

    # 改进幅度
    l2_improvement = (res_weno3['errors']['L2_rel'] - res_pp['errors']['L2_rel']) / res_weno3['errors']['L2_rel'] * 100
    linf_improvement = (res_weno3['errors']['Linf_rel'] - res_pp['errors']['Linf_rel']) / res_weno3['errors']['Linf_rel'] * 100

    print(f"\n改进幅度:")
    print(f"  L2误差降低:  {l2_improvement:.1f}%")
    print(f"  L∞误差降低:  {linf_improvement:.1f}%")

    # 判断是否达标
    target_l2 = 30.0  # 目标L2误差<30%
    if res_pp['errors']['L2_rel'] < target_l2:
        print(f"\n 达标！PP-WENO3的L2误差({res_pp['errors']['L2_rel']:.2f}%) < 目标({target_l2}%)")
    else:
        print(f"\n️  未达标。PP-WENO3的L2误差({res_pp['errors']['L2_rel']:.2f}%) >= 目标({target_l2}%)")
        print(f"   需要进一步调整参数或策略。")

    # 绘制对比图
    print("\n生成对比图...")
    output_dir = os.path.join(os.path.dirname(__file__), '..', '..', 'results', 'phase8.1')
    os.makedirs(output_dir, exist_ok=True)
    save_path = os.path.join(output_dir, 'rp2_pp_weno3_comparison.png')

    fig = plot_comparison(results, save_path=save_path)

    print("\n" + "="*80)
    print("测试完成！")
    print("="*80)

    return results


if __name__ == '__main__':
    results = main()
    plt.show()
