#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
溃坝波验证 - Godunov-FVM求解器 (Ritter解析解)

使用高精度Godunov-FVM求解器验证溃坝问题
对比HLL和HLLC两种Riemann求解器的性能

理论基础：
Ritter (1892) 给出了瞬时溃坝的精确解析解

解析解（无摩阻、水平河床）：
- 波前位置: x_f = 2*sqrt(g*h0)*t
- 稀疏波区域: u = (2/3)*(x/t + sqrt(g*h0))
- 水深: h = (1/9g)*(2*sqrt(g*h0) - x/t)²

验收标准：
- 波前位置误差 < 5%
- 水深RMSE < 0.5m (对于h0=10m)
- 质量守恒误差 < 0.1%

参考：
- Ritter (1892) "Die Fortpflanzung der Wasserwellen"
- Toro (2001) "Shock-Capturing Methods for Free-Surface Shallow Flows"
- LeVeque (2002) "Finite Volume Methods for Hyperbolic Problems"

作者：HydroClaude Team
日期：2025-10-28
"""

import numpy as np
import matplotlib.pyplot as plt
import sys
import os
from datetime import datetime

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from solvers.godunov_fvm_solver import GodunvFVMSolver


def ritter_solution(x: np.ndarray, t: float, h_L: float, g: float = 9.81):
    """
    Ritter解析解（瞬时溃坝）

    Args:
        x: 位置数组 (m)
        t: 时间 (s)
        h_L: 初始左侧水深 (m)
        g: 重力加速度

    Returns:
        h: 水深 (m)
        u: 流速 (m/s)
    """
    c0 = np.sqrt(g * h_L)  # 初始波速

    # 波前和波尾位置
    x_tail = -c0 * t  # 稀疏波尾部（向上游传播）
    x_front = 2.0 * c0 * t  # 波前（向下游传播）

    h = np.zeros_like(x)
    u = np.zeros_like(x)

    for i, xi in enumerate(x):
        if xi <= x_tail:
            # 上游静止区域
            h[i] = h_L
            u[i] = 0.0
        elif xi < x_front:
            # 稀疏波区域
            u[i] = (2.0/3.0) * (xi/t + c0)
            c = (1.0/3.0) * (2.0*c0 - xi/t)
            h[i] = c**2 / g
        else:
            # 下游干床
            h[i] = 0.0
            u[i] = 0.0

    return h, u


def validate_dam_break_godunov(riemann_solver='hll'):
    """
    使用Godunov-FVM求解器验证溃坝问题

    Args:
        riemann_solver: 'hll' 或 'hllc'

    Returns:
        results: 验证结果字典
    """
    print("=" * 80)
    print(f"溃坝波验证 - Godunov-FVM ({riemann_solver.upper()})")
    print("=" * 80)

    # 参数设置
    b = 10.0       # 渠宽 (m)
    L = 2000.0     # 渠长 (m)
    g = 9.81       # 重力加速度

    h_L = 10.0     # 上游初始水深 (m)
    h_R = 0.0      # 下游初始水深 (m，干床)

    t_final = 50.0  # 模拟时间 (s)

    print(f"\n参数设置:")
    print(f"  渠宽 b = {b} m")
    print(f"  渠长 L = {L} m")
    print(f"  上游水深 h_L = {h_L} m")
    print(f"  下游水深 h_R = {h_R} m (干床)")
    print(f"  模拟时间 t = {t_final} s")
    print(f"  Riemann求解器: {riemann_solver.upper()}")

    # 1. 理论解析解
    print(f"\n[1] Ritter解析解...")

    c0 = np.sqrt(g * h_L)
    x_front_theory = 2.0 * c0 * t_final
    x_tail_theory = -c0 * t_final

    print(f"  初始波速 c0 = {c0:.2f} m/s")
    print(f"  波尾位置 x_tail = {x_tail_theory:.2f} m (向上游)")
    print(f"  波前位置 x_front = {x_front_theory:.2f} m (向下游)")
    print(f"  稀疏波长度 = {x_front_theory - x_tail_theory:.2f} m")

    # 2. 数值求解
    print(f"\n[2] Godunov-FVM数值求解...")

    n_cells = 400  # 增加网格分辨率
    dx = L / n_cells

    solver = GodunvFVMSolver(
        width=b,
        length=L,
        n_cells=n_cells,
        manning_n=0.0,  # 无摩阻（理想情况）
        slope=0.0,      # 水平河床
        g=g,
        cfl=0.5,
        riemann_solver=riemann_solver,
        order=2  # 二阶精度
    )

    # 初始条件：坝址在L/2处
    dam_position = L / 2.0
    h_init = np.zeros(n_cells)
    for i in range(n_cells):
        if solver.x[i] < dam_position:
            h_init[i] = h_L
        else:
            h_init[i] = h_R

    Q_init = np.zeros(n_cells)

    solver.h = h_init
    solver.Q = Q_init

    # 边界条件：外推
    solver.bc_left = {'type': 'h', 'value': h_L}
    solver.bc_right = {'type': 'h', 'value': h_R}

    # 记录初始质量
    solver.initial_mass = np.sum(solver.h * solver.dx * b)

    print(f"  初始质量: {solver.initial_mass:.2f} m³")
    print(f"  网格数: {n_cells}, dx = {dx:.2f} m")
    print(f"  时间推进...")

    # 时间推进
    t = 0
    n_steps = 0
    max_steps = 50000

    while t < t_final and n_steps < max_steps:
        solver.step()
        t += solver.dt
        n_steps += 1

        if n_steps % 1000 == 0:
            print(f"    t = {t:.2f}s / {t_final:.2f}s, n_steps = {n_steps}")

        # 检查NaN
        if np.any(np.isnan(solver.h)) or np.any(np.isnan(solver.Q)):
            print(f"  ✗ 警告：出现NaN，停止计算")
            break

    print(f"  完成 {n_steps} 步，最终时间 t = {t:.2f}s")

    # 3. 结果分析
    print(f"\n[3] 结果分析...")

    # 调整坐标（坝址在原点）
    x_adjusted = solver.x - dam_position

    # 计算解析解
    h_exact, u_exact = ritter_solution(x_adjusted, t, h_L, g)
    Q_exact = h_exact * u_exact * b

    # 数值解
    h_numerical = solver.h
    Q_numerical = solver.Q
    u_numerical = np.where(h_numerical > 1e-6, Q_numerical / (h_numerical * b), 0.0)

    # 找波前位置（数值解）
    # 波前定义为水深 > 0.01m的最右侧位置
    wave_front_indices = np.where(h_numerical > 0.01)[0]
    if len(wave_front_indices) > 0:
        x_front_numerical = x_adjusted[wave_front_indices[-1]]
    else:
        x_front_numerical = 0.0

    # 找波尾位置（数值解）
    # 波尾定义为水深 < 0.99*h_L的最左侧位置
    wave_tail_indices = np.where(h_numerical < 0.99 * h_L)[0]
    if len(wave_tail_indices) > 0:
        x_tail_numerical = x_adjusted[wave_tail_indices[0]]
    else:
        x_tail_numerical = x_adjusted[0]

    print(f"  波前位置:")
    print(f"    理论: {x_front_theory:.2f} m")
    print(f"    数值: {x_front_numerical:.2f} m")
    x_front_error = abs(x_front_numerical - x_front_theory) / abs(x_front_theory) * 100
    print(f"    误差: {x_front_error:.2f}%")

    print(f"  波尾位置:")
    print(f"    理论: {x_tail_theory:.2f} m")
    print(f"    数值: {x_tail_numerical:.2f} m")
    x_tail_error = abs(x_tail_numerical - x_tail_theory) / abs(x_tail_theory) * 100
    print(f"    误差: {x_tail_error:.2f}%")

    # 水深RMSE
    rmse_h = np.sqrt(np.mean((h_numerical - h_exact)**2))
    print(f"\n  水深RMSE: {rmse_h:.4f} m")

    # 流速RMSE（仅在有水区域）
    wet_mask = h_exact > 0.1
    if np.any(wet_mask):
        rmse_u = np.sqrt(np.mean((u_numerical[wet_mask] - u_exact[wet_mask])**2))
        print(f"  流速RMSE: {rmse_u:.4f} m/s (有水区域)")

    # 质量守恒
    final_mass = np.sum(solver.h * solver.dx * b)
    mass_error = abs(final_mass - solver.initial_mass) / solver.initial_mass * 100
    print(f"\n  质量守恒:")
    print(f"    初始质量: {solver.initial_mass:.2f} m³")
    print(f"    最终质量: {final_mass:.2f} m³")
    print(f"    误差: {mass_error:.4f}%")

    # 4. 绘图
    print(f"\n[4] 生成对比图...")

    fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(14, 10))

    # 子图1：水深对比
    ax1.plot(x_adjusted, h_exact, 'r--', linewidth=2, label='Ritter解析解', alpha=0.8)
    ax1.plot(x_adjusted, h_numerical, 'b-', linewidth=1.5, label=f'{riemann_solver.upper()}数值解')
    ax1.axvline(x_front_theory, color='r', linestyle=':', alpha=0.5, label=f'理论波前 ({x_front_theory:.0f}m)')
    ax1.axvline(x_front_numerical, color='b', linestyle=':', alpha=0.5, label=f'数值波前 ({x_front_numerical:.0f}m)')
    ax1.axvline(0, color='k', linestyle='-', linewidth=2, alpha=0.3, label='坝址')

    ax1.set_xlabel('距坝址距离 x (m)', fontsize=12)
    ax1.set_ylabel('水深 h (m)', fontsize=12)
    ax1.set_title(f'溃坝波验证 - 水深对比 (t={t:.1f}s, {riemann_solver.upper()})', fontsize=14, fontweight='bold')
    ax1.legend(fontsize=10, loc='upper right')
    ax1.grid(True, alpha=0.3)
    ax1.set_xlim([x_tail_theory - 200, x_front_theory + 200])
    ax1.set_ylim([0, h_L * 1.1])

    # 子图2：流速对比
    ax2.plot(x_adjusted, u_exact, 'r--', linewidth=2, label='Ritter解析解', alpha=0.8)
    ax2.plot(x_adjusted, u_numerical, 'b-', linewidth=1.5, label=f'{riemann_solver.upper()}数值解')
    ax2.axvline(0, color='k', linestyle='-', linewidth=2, alpha=0.3, label='坝址')

    ax2.set_xlabel('距坝址距离 x (m)', fontsize=12)
    ax2.set_ylabel('流速 u (m/s)', fontsize=12)
    ax2.set_title('流速分布', fontsize=14, fontweight='bold')
    ax2.legend(fontsize=10, loc='upper left')
    ax2.grid(True, alpha=0.3)
    ax2.set_xlim([x_tail_theory - 200, x_front_theory + 200])

    plt.tight_layout()

    # 保存图片
    os.makedirs('validation_cases/results', exist_ok=True)
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    fig_path = f'validation_cases/results/dam_break_godunov_{riemann_solver}_{timestamp}.png'
    plt.savefig(fig_path, dpi=300, bbox_inches='tight')
    print(f"✓ 图表已保存: {fig_path}")

    plt.close()

    # 5. 验证判断
    print("\n" + "=" * 80)
    print("验证结果")
    print("=" * 80)

    tolerance_front = 5.0   # 波前位置误差容差 (%)
    tolerance_rmse = 0.5    # 水深RMSE容差 (m)
    tolerance_mass = 0.1    # 质量守恒容差 (%)

    passed = True

    if x_front_error < tolerance_front:
        print(f"✓ 波前位置测试通过: {x_front_error:.2f}% < {tolerance_front}%")
    else:
        print(f"✗ 波前位置测试失败: {x_front_error:.2f}% >= {tolerance_front}%")
        passed = False

    if rmse_h < tolerance_rmse:
        print(f"✓ 水深RMSE测试通过: {rmse_h:.4f}m < {tolerance_rmse}m")
    else:
        print(f"✗ 水深RMSE测试失败: {rmse_h:.4f}m >= {tolerance_rmse}m")
        passed = False

    if mass_error < tolerance_mass:
        print(f"✓ 质量守恒测试通过: {mass_error:.4f}% < {tolerance_mass}%")
    else:
        print(f"✗ 质量守恒测试失败: {mass_error:.4f}% >= {tolerance_mass}%")
        passed = False

    print("=" * 80)

    if passed:
        print(f"🎉 溃坝波验证通过! ({riemann_solver.upper()})")
    else:
        print(f"⚠️ 溃坝波验证需要改进 ({riemann_solver.upper()})")

    print("=" * 80 + "\n")

    return {
        'riemann_solver': riemann_solver,
        'passed': passed,
        'x_front_error': x_front_error,
        'x_tail_error': x_tail_error,
        'rmse_h': rmse_h,
        'mass_error': mass_error,
        't_final': t,
        'n_steps': n_steps
    }


def compare_riemann_solvers():
    """对比HLL和HLLC在溃坝问题上的表现"""
    print("\n" + "=" * 80)
    print("HLL vs HLLC 溃坝波对比")
    print("=" * 80)

    results_hll = validate_dam_break_godunov('hll')
    print("\n" + "="*80 + "\n")
    results_hllc = validate_dam_break_godunov('hllc')

    print("\n" + "=" * 80)
    print("对比总结")
    print("=" * 80)

    print(f"\n波前位置误差:")
    print(f"  HLL:  {results_hll['x_front_error']:.2f}%")
    print(f"  HLLC: {results_hllc['x_front_error']:.2f}%")
    improvement = results_hll['x_front_error'] - results_hllc['x_front_error']
    print(f"  改进: {improvement:.2f}% ({'HLLC更好' if improvement > 0 else 'HLL更好'})")

    print(f"\n水深RMSE:")
    print(f"  HLL:  {results_hll['rmse_h']:.4f}m")
    print(f"  HLLC: {results_hllc['rmse_h']:.4f}m")
    improvement_rmse = (results_hll['rmse_h'] - results_hllc['rmse_h']) / results_hll['rmse_h'] * 100
    print(f"  改进: {improvement_rmse:.1f}% ({'HLLC更好' if improvement_rmse > 0 else 'HLL更好'})")

    print(f"\n质量守恒:")
    print(f"  HLL:  {results_hll['mass_error']:.4f}%")
    print(f"  HLLC: {results_hllc['mass_error']:.4f}%")

    print(f"\n验证结果:")
    print(f"  HLL:  {'✓ 通过' if results_hll['passed'] else '✗ 未通过'}")
    print(f"  HLLC: {'✓ 通过' if results_hllc['passed'] else '✗ 未通过'}")

    print("=" * 80 + "\n")


if __name__ == '__main__':
    # 可以单独运行一个求解器
    if len(sys.argv) > 1:
        solver_type = sys.argv[1].lower()
        if solver_type in ['hll', 'hllc']:
            result = validate_dam_break_godunov(solver_type)
            sys.exit(0 if result['passed'] else 1)
        else:
            print(f"错误: 未知的求解器类型 '{solver_type}'")
            print("使用方法: python dam_break_godunov.py [hll|hllc]")
            sys.exit(1)
    else:
        # 默认：对比两种求解器
        compare_riemann_solvers()
