# -*- coding: utf-8 -*-
"""
示例1扩展[U+FF1A]明渠闸门过流动力学分析[U+FF08]高精度版本[U+FF09]

使用HydrostaticCanalSolver实现闸门流动模拟[U+FF08]Phase 2高精度求解器[U+FF09]
- 稳态[U+FF1A]恒定均匀流[U+FF0C]流量守恒精度 < 0.01%
- 自动结果验证和报告生成

Author: Claude
Date: 2025-10-23
"""

import sys, os

# Add project root to path
# Script is in: examples/example_01_canal_flow/scripts/
# Project root is 3 levels up
script_path = os.path.abspath(__file__)
project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(script_path))))
sys.path.insert(0, project_root)

# Add scripts directory to path for output_helper
script_dir = os.path.dirname(script_path)
sys.path.insert(0, script_dir)

import numpy as np
import pandas as pd
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from solvers.hydrostatic_canal_solver import HydrostaticCanalSolver
from solvers.gate import SluiceGate
from utils.canal_utils import compute_steady_uniform_flow
from utils.result_validator import ResultValidator, quick_validate_steady_state
from output_helper import get_output_path, save_figure, save_table


def run_sluice_gate_dynamics():
    """运行闸门流量动力学分析"""

    print("=" * 80)
    print("示例1扩展[U+FF1A]明渠闸门过流动力学分析[U+FF08]HydrostaticCanalSolver高精度版本[U+FF09]")
    print("=" * 80)
    print()

    # ==================== 系统配置 ====================
    canal_length = 10000.0  # 渠道总长度 (m)
    canal_width = 10.0      # 渠道宽度 (m)
    gate_position = 5000.0  # 闸门位置[U+FF08]中点[U+FF09]
    n_points = 201          # 总空间点数

    # 渠道参数
    bed_slope = 0.0005      # 底坡
    manning_n = 0.025       # 曼宁糙率

    # 闸门参数
    gate_opening = 5.0      # 闸门开度 (m)
    gate_Cd = 0.6           # 流量系数

    print("系统配置:")
    print(f"  渠道总长度: {canal_length} m")
    print(f"  渠道宽度: {canal_width} m")
    print(f"  空间点数: {n_points}")
    print(f"  闸门位置: {gate_position} m")
    print(f"  闸门开度: {gate_opening} m")
    print(f"  流量系数: {gate_Cd}")
    print(f"  底坡: {bed_slope*1000:.2f}[U+2030]")
    print(f"  曼宁糙率: {manning_n}")
    print()

    # ==================== 创建闸门和求解器 ====================
    # 创建平板闸门
    sluice_gate = SluiceGate(
        position=gate_position,
        width=canal_width,
        opening=gate_opening,
        Cd=gate_Cd
    )

    # 创建高精度求解器[U+FF08]Phase 2静水重构方法[U+FF09]
    solver = HydrostaticCanalSolver(
        length=canal_length,
        nx=n_points,
        B=canal_width,
        S0=bed_slope,
        n=manning_n,
        internal_structures=[(gate_position, sluice_gate)]
    )

    print(f"求解器: HydrostaticCanalSolver (Phase 2高精度)")
    print(f"  网格点数: {solver.nx}")
    print(f"  网格间距: {solver.dx:.2f} m")
    print(f"  内部结构: {len(solver.structure_objects)}个闸门")
    print()

    # ==================== 步骤1: 计算初始稳态 ====================
    print("=" * 80)
    print("步骤1: 计算初始稳态[U+FF08]恒定流[U+FF09]")
    print("-" * 80)

    Q_initial = 10.0  # 初始流量 (m^3/s)

    # 计算均匀流水深作为初始猜测
    h_uniform = compute_steady_uniform_flow(Q_initial, canal_width, bed_slope, manning_n)

    print(f"  初始流量: {Q_initial} m^3/s")
    print(f"  恒定均匀流水深: {h_uniform:.4f} m")
    print()

    # 初始化求解器
    solver.h[:] = h_uniform
    solver.hu[:] = Q_initial / canal_width

    # 使用高精度稳态求解器
    print("开始稳态求解[U+FF08]Phase 2静水重构方法[U+FF09]...")
    result = solver.solve_steady_state(
        Q_target=Q_initial,
        h_downstream=h_uniform,
        max_iterations=5000,
        convergence_tol = 0.1,
        dt=0.5,
        verbose=True
    )

    # ==================== 结果验证 ====================
    print("\n" + "=" * 80)
    print("结果验证")
    print("=" * 80)

    # 使用ResultValidator进行验证
    validator = quick_validate_steady_state(
        solver=solver,
        result_dict=result,
        Q_target=Q_initial,
        name="脚本07 - 闸门流动分析"
    )

    # ==================== 获取结果数据 ====================
    x_full = solver.x
    h_steady = result['h']
    Q_steady = result['Q']

    # 找到闸门位置的索引
    gate_idx = solver.structure_indices[0]

    print(f"\n详细结果:")
    print(f"  闸前水深: {h_steady[gate_idx-1]:.4f} m")
    print(f"  闸后水深: {h_steady[gate_idx+1]:.4f} m")
    print(f"  水位差: {h_steady[gate_idx-1] - h_steady[gate_idx+1]:.4f} m")

    # 计算闸门流量
    h_up = h_steady[gate_idx - 1]
    h_down = h_steady[gate_idx + 1]
    Q_gate, flow_type = sluice_gate.calculate_discharge(h_up, h_down)
    print(f"  闸门流量: {Q_gate:.4f} m^3/s")
    print(f"  流态: {flow_type}")
    print()

    # ==================== 生成初始稳态图 ====================
    print("=" * 80)
    print("生成可视化")
    print("=" * 80)
    print("  1. 生成稳态纵剖面图...")

    fig_steady = plt.figure(figsize=(16, 10))

    # 计算渠底高程[U+FF08]以下游为基准0[U+FF09]
    z_bed = (canal_length - x_full) * bed_slope
    z_surface = z_bed + h_steady  # 水面高程

    # 子图1: 纵剖面[U+FF08]水面+渠底[U+FF09]
    ax1 = plt.subplot(3, 1, 1)
    ax1.fill_between(x_full, z_bed, z_surface, color='cyan', alpha=0.5, label='Water')
    ax1.plot(x_full, z_surface, 'b-', linewidth=2.5, label='Water Surface')
    ax1.plot(x_full, z_bed, 'k-', linewidth=2, label='Bed Level')
    ax1.axvline(x=gate_position, color='r', linestyle='--', linewidth=2.5, alpha=0.7, label='Gate')
    ax1.set_xlabel('Distance (m)', fontsize=12)
    ax1.set_ylabel('Elevation (m)', fontsize=12)
    ax1.set_title('Steady State - Longitudinal Profile (HydrostaticCanalSolver)',
                  fontsize=14, fontweight='bold')
    ax1.grid(True, alpha=0.3)
    ax1.legend(fontsize=11, loc='upper right')
    ax1.set_xlim([0, canal_length])

    # 子图2: 水深剖面
    ax2 = plt.subplot(3, 1, 2)
    ax2.plot(x_full, h_steady, 'b-', linewidth=2.5, label='Water Depth')
    ax2.axvline(x=gate_position, color='r', linestyle='--', linewidth=2, alpha=0.7,
                label='Gate Position')
    ax2.axhline(y=h_uniform, color='k', linestyle=':', alpha=0.5,
                label=f'Uniform Depth ({h_uniform:.3f}m)')
    ax2.set_xlabel('Distance (m)', fontsize=12)
    ax2.set_ylabel('Water Depth (m)', fontsize=12)
    ax2.set_title('Water Depth Distribution', fontsize=14, fontweight='bold')
    ax2.grid(True, alpha=0.3)
    ax2.legend(fontsize=11)
    ax2.set_xlim([0, canal_length])

    # 子图3: 流量剖面[U+FF08]带验证标记[U+FF09]
    ax3 = plt.subplot(3, 1, 3)

    # 计算流量误差
    Q_error_pct = np.abs(Q_steady - Q_initial) / Q_initial * 100
    max_error = np.max(Q_error_pct)

    ax3.plot(x_full, Q_steady, 'g-', linewidth=2.5, label='Flow Rate')
    ax3.axvline(x=gate_position, color='r', linestyle='--', linewidth=2, alpha=0.7,
                label='Gate Position')
    ax3.axhline(y=Q_initial, color='k', linestyle=':', alpha=0.5,
                label=f'Target Flow ({Q_initial:.1f} m^3/s)')

    # 添加误差信息
    error_text = f'Max Error: {max_error:.6f}%'
    if max_error < 0.01:
        error_color = 'green'
        grade = '优秀'
    elif max_error < 0.1:
        error_color = 'blue'
        grade = '良好'
    else:
        error_color = 'orange'
        grade = '可接受'

    ax3.text(0.98, 0.95, f'{error_text}\n({grade})',
             transform=ax3.transAxes, fontsize=11, verticalalignment='top',
             horizontalalignment='right', bbox=dict(boxstyle='round',
             facecolor=error_color, alpha=0.2))

    ax3.set_xlabel('Distance (m)', fontsize=12)
    ax3.set_ylabel('Flow Rate (m^3/s)', fontsize=12)
    ax3.set_title('Flow Rate Distribution (Should be constant for steady flow)',
                  fontsize=14, fontweight='bold')
    ax3.grid(True, alpha=0.3)
    ax3.legend(fontsize=11)
    ax3.set_xlim([0, canal_length])

    plt.tight_layout()
    steady_fig_path = save_figure(fig_steady, '07_sluice_gate_steady_state_v2.png')
    plt.close(fig_steady)

    # ==================== 生成验证结果图 ====================
    print("  2. 生成验证结果图...")

    # 使用validator的plot功能
    fig_validation = validator.plot_flow_distribution(
        x=x_full,
        Q=Q_steady,
        Q_target=Q_initial,
        gate_positions=[gate_position],
        title="Flow Conservation Validation - Script 07",
        save_path=get_output_path('figures', '07_sluice_gate_validation.png')
    )
    plt.close(fig_validation)

    # Export steady state profile data to CSV
    steady_data = pd.DataFrame({
        'Distance_m': x_full,
        'Bed_Elevation_m': z_bed,
        'Water_Depth_m': h_steady,
        'Water_Surface_Elevation_m': z_surface,
        'Flow_Rate_m3s': Q_steady,
        'Flow_Error_pct': Q_error_pct
    })
    save_table(steady_data, '07_sluice_gate_steady_profile_v2.csv', index=False)

    # ==================== 保存验证报告 ====================
    print("  3. 保存验证报告...")

    report_path = get_output_path('reports', '07_sluice_gate_validation_report.txt')
    validator.save_report(report_path)

    print()
    print("=" * 80)
    print("分析完成[U+FF01]")
    print("=" * 80)

    print(f"\n生成的文件:")
    print(f"  Figures:")
    print(f"    - 07_sluice_gate_steady_state_v2.png")
    print(f"    - 07_sluice_gate_validation.png")
    print(f"  Tables:")
    print(f"    - 07_sluice_gate_steady_profile_v2.csv ({len(x_full)} rows)")
    print(f"  Reports:")
    print(f"    - 07_sluice_gate_validation_report.txt")

    print("\n关键指标:")
    print(f"  流量守恒误差: {result['Q_error_percent']:.6f}%")
    print(f"  收敛迭代次数: {result['iterations']}")
    print(f"  闸门流量误差: {abs(Q_gate-Q_initial)/Q_initial*100:.2f}%")

    # 最终判定
    if result['Q_error_percent'] < 0.01:
        print(f"\n   达到优秀精度标准[U+FF01][U+FF08]< 0.01%[U+FF09]")
    elif result['Q_error_percent'] < 0.1:
        print(f"\n   达到良好精度标准[U+FF01][U+FF08]< 0.1%[U+FF09]")
    else:
        print(f"\n   达到可接受精度标准[U+FF01][U+FF08]< 1.0%[U+FF09]")

    print("\n所有输出文件已保存到 results/ 目录")
    print("\n" + "=" * 80)

    return validator


if __name__ == "__main__":
    validator = run_sluice_gate_dynamics()
