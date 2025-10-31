#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
生成Toro Riemann问题的对比可视化图

展示Phase 7.2成果：
- RP1, RP3, RP4, RP8的精确解 vs 数值解对比
- 误差分析图
"""

import sys
import os
sys.path.insert(0, os.path.dirname(__file__))

import numpy as np
import matplotlib.pyplot as plt
from matplotlib.gridspec import GridSpec

from solvers.godunov_fvm_weno3 import GodunvFVMWENO3
from tests.verification.toro_riemann_solver import exact_riemann_solution, riemann_structure


def create_rp_comparison(h_L, u_L, h_R, u_R, t_end, title, filename, cfl=0.2):
    """
    创建单个RP问题的对比图

    Args:
        h_L, u_L, h_R, u_R: Riemann初值
        t_end: 终止时间
        title: 图标题
        filename: 保存文件名
        cfl: CFL数
    """
    L = 100.0
    n_cells = 500
    x_dam = L / 2.0
    B = 10.0

    # 创建求解器
    solver = GodunvFVMWENO3(
        width=B, length=L, n_cells=n_cells,
        manning_n=0.0, slope=0.0,
        use_enhanced_bc=True, well_balanced=False,
        cfl=cfl, use_numba=True
    )

    # 初始条件
    x = solver.x
    h_init = np.where(x <= x_dam, h_L, h_R)
    Q_init = B * np.where(x <= x_dam, h_L * u_L, h_R * u_R)

    bc_left = {'type': 'transmissive'}
    bc_right = {'type': 'transmissive'}
    solver.initialize(h_init, Q_init, bc_left, bc_right)

    # 运行模拟
    while solver.t < t_end:
        solver.step()

    # 数值解
    x_num = solver.x
    h_num = solver.h
    u_num = solver.Q / (solver.B * np.maximum(solver.h, solver.eps_dry))

    # 精确解
    x_exact = np.linspace(0, L, 1000)
    h_exact, u_exact = exact_riemann_solution(
        x_exact, solver.t, h_L, u_L, h_R, u_R, x_dam
    )

    # 波结构
    structure = riemann_structure(h_L, u_L, h_R, u_R)

    # 计算误差
    h_num_interp = np.interp(x_exact, x_num, h_num)
    h_L2 = np.sqrt(np.mean((h_num_interp - h_exact)**2))
    h_scale = max(h_L, h_R) if max(h_L, h_R) > 0 else 1.0
    h_L2_rel = h_L2 / h_scale * 100

    # 创建图形
    fig = plt.figure(figsize=(14, 10))
    gs = GridSpec(3, 2, figure=fig, hspace=0.3, wspace=0.3)

    # 1. 水深对比
    ax1 = fig.add_subplot(gs[0, :])
    ax1.plot(x_exact, h_exact, 'k-', linewidth=2, label='Exact', alpha=0.8)
    ax1.plot(x_num, h_num, 'ro', markersize=4, label='WENO3', alpha=0.7)
    ax1.axvline(x_dam, color='gray', linestyle=':', alpha=0.5, label='Initial disc.')
    ax1.set_ylabel('Water Depth h (m)', fontsize=12, fontweight='bold')
    ax1.set_title(f'{title} - t={solver.t:.3f}s', fontsize=14, fontweight='bold')
    ax1.legend(fontsize=11, loc='best')
    ax1.grid(True, alpha=0.3)

    # 2. 流速对比
    ax2 = fig.add_subplot(gs[1, :])
    ax2.plot(x_exact, u_exact, 'k-', linewidth=2, label='Exact', alpha=0.8)
    ax2.plot(x_num, u_num, 'bo', markersize=4, label='WENO3', alpha=0.7)
    ax2.axvline(x_dam, color='gray', linestyle=':', alpha=0.5)
    ax2.set_ylabel('Velocity u (m/s)', fontsize=12, fontweight='bold')
    ax2.set_xlabel('Distance x (m)', fontsize=12, fontweight='bold')
    ax2.legend(fontsize=11, loc='best')
    ax2.grid(True, alpha=0.3)

    # 3. 误差分布
    ax3 = fig.add_subplot(gs[2, 0])
    h_error = h_num_interp - h_exact
    ax3.plot(x_exact, h_error, 'r-', linewidth=1.5)
    ax3.axhline(0, color='k', linestyle='--', alpha=0.5)
    ax3.set_xlabel('Distance x (m)', fontsize=11)
    ax3.set_ylabel('h Error (m)', fontsize=11, fontweight='bold')
    ax3.set_title('Water Depth Error', fontsize=12)
    ax3.grid(True, alpha=0.3)

    # 4. 波结构信息
    ax4 = fig.add_subplot(gs[2, 1])
    ax4.axis('off')

    info_text = f"""Wave Structure:

    Left:  {structure['wave_type_L'].upper()}
    Right: {structure['wave_type_R'].upper()}

    Star Region:
    h* = {structure['h_star']:.4f} m
    u* = {structure['u_star']:.4f} m/s

    Error Metrics:
    L2 = {h_L2:.4f} m ({h_L2_rel:.2f}%)

    Numerical Setup:
    Cells: {n_cells}
    CFL: {cfl}
    Steps: {solver.step_count}
    """

    ax4.text(0.1, 0.5, info_text, fontsize=11, family='monospace',
             verticalalignment='center', bbox=dict(boxstyle='round',
             facecolor='wheat', alpha=0.3))

    plt.savefig(filename, dpi=150, bbox_inches='tight')
    print(f"✅ 保存: {filename}")
    plt.close()

    return h_L2_rel


def create_summary_comparison():
    """创建多个RP问题的汇总对比图"""

    fig, axes = plt.subplots(2, 2, figsize=(16, 12))
    fig.suptitle('Toro Riemann Problems - HydroClaude WENO3 vs Exact Solutions',
                 fontsize=16, fontweight='bold')

    # RP配置
    rp_configs = [
        {'h_L': 10.0, 'u_L': 0.0, 'h_R': 5.0, 'u_R': 0.0, 't': 0.5,
         'title': 'RP1: Rarefaction + Shock', 'ax_idx': (0, 0)},
        {'h_L': 10.0, 'u_L': 0.0, 'h_R': 2.0, 'u_R': 0.0, 't': 0.5,
         'title': 'RP3: Shock + Rarefaction', 'ax_idx': (0, 1)},
        {'h_L': 2.0, 'u_L': 0.0, 'h_R': 10.0, 'u_R': 0.0, 't': 0.5,
         'title': 'RP4: Rarefaction + Shock', 'ax_idx': (1, 0)},
        {'h_L': 5.0, 'u_L': 0.1, 'h_R': 5.0, 'u_R': -0.1, 't': 1.0,
         'title': 'RP8: Near Steady', 'ax_idx': (1, 1)},
    ]

    for config in rp_configs:
        # 运行模拟
        L = 100.0
        n_cells = 500
        x_dam = L / 2.0
        B = 10.0

        solver = GodunvFVMWENO3(
            width=B, length=L, n_cells=n_cells,
            manning_n=0.0, slope=0.0,
            use_enhanced_bc=True, well_balanced=False,
            cfl=0.2, use_numba=True
        )

        x = solver.x
        h_init = np.where(x <= x_dam, config['h_L'], config['h_R'])
        Q_init = B * np.where(x <= x_dam,
                              config['h_L'] * config['u_L'],
                              config['h_R'] * config['u_R'])

        bc = {'type': 'transmissive'}
        solver.initialize(h_init, Q_init, bc, bc)

        while solver.t < config['t']:
            solver.step()

        # 精确解
        x_exact = np.linspace(0, L, 1000)
        h_exact, u_exact = exact_riemann_solution(
            x_exact, solver.t, config['h_L'], config['u_L'],
            config['h_R'], config['u_R'], x_dam
        )

        # 绘图
        ax = axes[config['ax_idx']]
        ax.plot(x_exact, h_exact, 'k-', linewidth=2, label='Exact', alpha=0.8)
        ax.plot(solver.x, solver.h, 'ro', markersize=3, label='WENO3', alpha=0.6)
        ax.set_xlabel('x (m)', fontsize=11)
        ax.set_ylabel('h (m)', fontsize=11)
        ax.set_title(config['title'], fontsize=12, fontweight='bold')
        ax.legend(fontsize=10)
        ax.grid(True, alpha=0.3)

    plt.tight_layout()
    plt.savefig('toro_summary_comparison.png', dpi=150, bbox_inches='tight')
    print(f"✅ 保存汇总图: toro_summary_comparison.png")
    plt.close()


if __name__ == '__main__':
    print("="*70)
    print("创建Toro Riemann问题可视化对比图")
    print("="*70)

    # 1. RP1 详细对比
    print("\n1. RP1 (稀疏波+激波)...")
    err1 = create_rp_comparison(
        h_L=10.0, u_L=0.0, h_R=5.0, u_R=0.0,
        t_end=0.5,
        title='RP1: Rarefaction + Shock',
        filename='toro_rp1_detailed.png'
    )

    # 2. RP3 详细对比
    print("\n2. RP3 (激波+稀疏波)...")
    err3 = create_rp_comparison(
        h_L=10.0, u_L=0.0, h_R=2.0, u_R=0.0,
        t_end=0.5,
        title='RP3: Shock + Rarefaction',
        filename='toro_rp3_detailed.png'
    )

    # 3. RP8 详细对比
    print("\n3. RP8 (近似静水)...")
    err8 = create_rp_comparison(
        h_L=5.0, u_L=0.1, h_R=5.0, u_R=-0.1,
        t_end=1.0,
        title='RP8: Near Steady State',
        filename='toro_rp8_detailed.png'
    )

    # 4. 汇总对比图
    print("\n4. 创建汇总对比图...")
    create_summary_comparison()

    print("\n" + "="*70)
    print("✅ 所有可视化图生成完成!")
    print("="*70)
    print(f"\n生成的文件:")
    print(f"  - toro_rp1_detailed.png (L2误差: {err1:.2f}%)")
    print(f"  - toro_rp3_detailed.png (L2误差: {err3:.2f}%)")
    print(f"  - toro_rp8_detailed.png (L2误差: {err8:.2f}%)")
    print(f"  - toro_summary_comparison.png (汇总)")
