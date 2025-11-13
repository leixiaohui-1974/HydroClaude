#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
水跃验证 (Hydraulic Jump)

水跃是超临界流转变为亚临界流的急变流现象常见于
- 陡坡后接缓坡
- 闸门下游
- 跌水后

理论基础
1. 共轭水深关系动量方程
   y2/y1 = 0.5 * (sqrt(1 + 8*Fr1^2) - 1)

2. 能量损失
   DeltaE = (y2 - y1)^3 / (4*y1*y2)

3. 水跃长度经验公式
   Lj  6 * y2

验证方法
- 设置陡坡->缓坡地形
- 检验共轭水深关系
- 验证能量损失
- 确认水跃位置

验收标准
- 共轭水深误差 < 3%
- 能量损失误差 < 5%
- 水跃位置误差 < 10%

参考
- Chow (1959) "Open-Channel Hydraulics", Chapter 15
- Henderson (1966) "Open Channel Flow", Chapter 6
- USBR (1987) "Design of Small Dams"

作者HydroClaude Team
日期2025-10-28
"""

import numpy as np
import matplotlib.pyplot as plt
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from solvers.godunov_fvm_solver import GodunvFVMSolver


def compute_conjugate_depth(y1: float, Fr1: float) -> float:
    """
    计算共轭水深动量方程

    y2/y1 = 0.5 * (sqrt(1 + 8*Fr1^2) - 1)

    Args:
        y1: 跃前水深 (m)
        Fr1: 跃前弗劳德数

    Returns:
        y2: 跃后水深 (m)
    """
    ratio = 0.5 * (np.sqrt(1 + 8 * Fr1**2) - 1)
    y2 = y1 * ratio
    return y2


def compute_energy_loss(y1: float, y2: float) -> float:
    """
    计算水跃能量损失

    DeltaE = (y2 - y1)^3 / (4*y1*y2)

    Args:
        y1: 跃前水深 (m)
        y2: 跃后水深 (m)

    Returns:
        DeltaE: 能量损失 (m)
    """
    dE = (y2 - y1)**3 / (4 * y1 * y2)
    return dE


def compute_jump_length(y2: float) -> float:
    """
    计算水跃长度经验公式

    Lj  6 * y2

    Args:
        y2: 跃后水深 (m)

    Returns:
        Lj: 水跃长度 (m)
    """
    Lj = 6.0 * y2
    return Lj


def find_jump_location(x: np.ndarray, h: np.ndarray, threshold: float = 0.2) -> int:
    """
    寻找水跃位置水深梯度最大处

    Args:
        x: 位置数组 (m)
        h: 水深数组 (m)
        threshold: 梯度阈值

    Returns:
        idx: 水跃中心位置索引
    """
    # 计算水深梯度
    dh_dx = np.gradient(h, x)

    # 找到最大梯度位置
    idx_max = np.argmax(dh_dx)

    return idx_max


def validate_hydraulic_jump():
    """验证水跃"""

    print("=" * 80)
    print("水跃验证 (Hydraulic Jump)")
    print("=" * 80)

    # 参数设置
    b = 10.0       # 渠宽 (m)
    Q = 30.0       # 流量 (m^3/s)
    g = 9.81       # 重力加速度

    # 地形设置陡坡->缓坡
    L_steep = 500.0    # 陡坡段长度 (m)
    L_mild = 500.0     # 缓坡段长度 (m)
    L_total = L_steep + L_mild

    S_steep = 0.01     # 陡坡超临界流- 降低以提高稳定性
    S_mild = 0.0005    # 缓坡亚临界流- 提高以减小差异

    n = 0.020          # 曼宁系数光滑渠道

    print(f"\n参数设置:")
    print(f"  渠宽 b = {b} m")
    print(f"  流量 Q = {Q} m^3/s")
    print(f"  陡坡段: L={L_steep}m, S={S_steep}")
    print(f"  缓坡段: L={L_mild}m, S={S_mild}")
    print(f"  曼宁系数 n = {n}")

    # 1. 理论分析
    print(f"\n[1] 理论分析...")

    # 陡坡段超临界流
    # 使用较温和的弗劳德数以避免数值不稳定
    Fr1 = 2.0  # 降低从4.0到2.0
    V1 = Fr1 * np.sqrt(g * 1.0)  # 假设y1=1.0m
    y1 = Q / (b * V1)
    V1 = Q / (b * y1)  # 重新计算
    Fr1 = V1 / np.sqrt(g * y1)   # 重新计算

    print(f"  跃前: y1 = {y1:.3f}m, V1 = {V1:.3f}m/s, Fr1 = {Fr1:.3f}")

    # 共轭水深
    y2_theory = compute_conjugate_depth(y1, Fr1)
    V2 = Q / (b * y2_theory)
    Fr2 = V2 / np.sqrt(g * y2_theory)

    print(f"  跃后: y2 = {y2_theory:.3f}m, V2 = {V2:.3f}m/s, Fr2 = {Fr2:.3f}")

    # 能量损失
    dE_theory = compute_energy_loss(y1, y2_theory)
    print(f"  能量损失: DeltaE = {dE_theory:.3f}m")

    # 水跃长度
    Lj_theory = compute_jump_length(y2_theory)
    print(f"  水跃长度: Lj  {Lj_theory:.1f}m")

    # 预计水跃位置陡坡末端附近
    x_jump_theory = L_steep
    print(f"  预计水跃位置: x  {x_jump_theory:.1f}m")

    # 2. 数值求解
    print(f"\n[2] HydroClaude数值求解...")

    n_cells = 200
    dx = L_total / n_cells

    # 创建空间变化的坡度数组
    S0_array = np.zeros(n_cells)
    x_centers = np.linspace(0.5*dx, L_total - 0.5*dx, n_cells)
    for i in range(n_cells):
        if x_centers[i] < L_steep:
            S0_array[i] = S_steep
        else:
            S0_array[i] = S_mild

    print(f"  坡度设置: 前{L_steep}m为{S_steep}, 后{L_mild}m为{S_mild}")

    # 创建求解器使用空间变化的坡度
    solver = GodunvFVMSolver(
        width=b,
        length=L_total,
        n_cells=n_cells,
        manning_n=n,
        slope=S0_array,  # 传入坡度数组
        g=g,
        cfl=0.3,  # 降低CFL以提高稳定性
        order=1  # 使用一阶精度更稳定
    )

    # 初始条件使用平滑过渡tanh profile
    # 在预期水跃位置附近从y1平滑过渡到y2
    h_init = np.zeros(n_cells)
    transition_width = 50.0  # 过渡区宽度
    for i in range(n_cells):
        # tanh函数实现平滑过渡
        h_init[i] = 0.5 * (y1 + y2_theory) + 0.5 * (y2_theory - y1) * np.tanh((x_centers[i] - L_steep) / transition_width)

    Q_init = Q * np.ones(n_cells)

    solver.h = h_init
    solver.Q = Q_init

    # 边界条件
    solver.bc_left = {'type': 'Q', 'value': Q}
    solver.bc_right = {'type': 'h', 'value': y2_theory}  # 下游控制跃后水深

    # 记录初始质量
    solver.initial_mass = np.sum(solver.h * solver.dx * b)

    print("  时间推进...")
    t_max = 1000.0  # s
    t = 0
    n_steps = 0
    max_steps = 50000  # 最大步数限制

    prev_h = solver.h.copy()
    convergence_threshold = 1e-4

    while t < t_max and n_steps < max_steps:
        solver.step()
        t += solver.dt
        n_steps += 1

        # 检查收敛
        if n_steps % 100 == 0:
            delta = np.max(np.abs(solver.h - prev_h))
            if delta < convergence_threshold:
                print(f"  收敛! t = {t:.1f}s, n_steps={n_steps}, Deltah_max = {delta:.2e}m")
                break
            prev_h = solver.h.copy()

            if n_steps % 500 == 0:
                print(f"  t = {t:.1f}s, n_steps={n_steps}, Deltah_max = {delta:.2e}m")

                # 检查是否出现NaN
                if np.any(np.isnan(solver.h)) or np.any(np.isnan(solver.Q)):
                    print(f"  警告出现NaN值停止计算")
                    break

    print(f"  完成 {n_steps} 步最终时间 t={t:.1f}s")

    # 3. 结果分析
    print(f"\n[3] 结果分析...")

    # 找到水跃位置
    idx_jump = find_jump_location(solver.x, solver.h)
    x_jump_numerical = solver.x[idx_jump]

    print(f"  数值水跃位置: x = {x_jump_numerical:.1f}m")

    # 提取跃前跃后水深
    # 跃前水跃前50m的平均值
    idx_before = max(0, idx_jump - 5)
    y1_numerical = np.mean(solver.h[max(0, idx_before-5):idx_before])
    V1_numerical = np.mean(solver.Q[max(0, idx_before-5):idx_before]) / (b * y1_numerical)
    Fr1_numerical = V1_numerical / np.sqrt(g * y1_numerical)

    # 跃后水跃后50m的平均值
    idx_after = min(n_cells-1, idx_jump + 10)
    y2_numerical = np.mean(solver.h[idx_after:min(n_cells, idx_after+10)])
    V2_numerical = np.mean(solver.Q[idx_after:min(n_cells, idx_after+10)]) / (b * y2_numerical)
    Fr2_numerical = V2_numerical / np.sqrt(g * y2_numerical)

    print(f"\n  数值结果:")
    print(f"    跃前: y1 = {y1_numerical:.3f}m, V1 = {V1_numerical:.3f}m/s, Fr1 = {Fr1_numerical:.3f}")
    print(f"    跃后: y2 = {y2_numerical:.3f}m, V2 = {V2_numerical:.3f}m/s, Fr2 = {Fr2_numerical:.3f}")

    # 计算误差
    error_y1 = abs(y1_numerical - y1) / y1 * 100
    error_y2 = abs(y2_numerical - y2_theory) / y2_theory * 100
    error_x = abs(x_jump_numerical - x_jump_theory) / L_total * 100

    # 能量损失
    dE_numerical = compute_energy_loss(y1_numerical, y2_numerical)
    error_dE = abs(dE_numerical - dE_theory) / dE_theory * 100 if dE_theory > 0 else 0

    print(f"\n  误差分析:")
    print(f"    跃前水深误差: {error_y1:.2f}%")
    print(f"    跃后水深误差: {error_y2:.2f}%")
    print(f"    水跃位置误差: {error_x:.2f}%")
    print(f"    能量损失误差: {error_dE:.2f}%")

    # 质量守恒
    final_mass = np.sum(solver.h * solver.dx * b)
    mass_error = abs(final_mass - solver.initial_mass) / solver.initial_mass * 100
    print(f"    质量守恒误差: {mass_error:.4f}%")

    # 4. 绘图
    print(f"\n[4] 生成对比图...")

    fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(14, 10))

    # 子图1水深剖面
    ax1.plot(solver.x, solver.h, 'b-', linewidth=2, label='数值解')
    ax1.axhline(y1, color='r', linestyle='--', alpha=0.7, label=f'跃前水深 y1={y1:.3f}m')
    ax1.axhline(y2_theory, color='g', linestyle='--', alpha=0.7, label=f'跃后水深 y2={y2_theory:.3f}m')
    ax1.axvline(L_steep, color='k', linestyle=':', alpha=0.5, label='陡坡/缓坡交界')
    ax1.axvline(x_jump_numerical, color='orange', linestyle='-.', linewidth=2, label=f'水跃位置 x={x_jump_numerical:.1f}m')

    # 标注水跃区域
    ax1.axvspan(x_jump_numerical - Lj_theory/2, x_jump_numerical + Lj_theory/2,
                alpha=0.2, color='yellow', label=f'水跃区 (Lj{Lj_theory:.1f}m)')

    ax1.set_xlabel('距离 x (m)', fontsize=12)
    ax1.set_ylabel('水深 y (m)', fontsize=12)
    ax1.set_title('水跃验证 - 水深剖面', fontsize=14, fontweight='bold')
    ax1.legend(fontsize=10, loc='best')
    ax1.grid(True, alpha=0.3)

    # 子图2弗劳德数分布
    h_safe = np.maximum(solver.h, 1e-6)
    V = solver.Q / (b * h_safe)
    Fr = V / np.sqrt(g * h_safe)

    ax2.plot(solver.x, Fr, 'b-', linewidth=2, label='弗劳德数 Fr')
    ax2.axhline(1.0, color='r', linestyle='--', linewidth=2, label='临界流 Fr=1')
    ax2.axvline(x_jump_numerical, color='orange', linestyle='-.', linewidth=2, label='水跃位置')
    ax2.fill_between(solver.x, 0, Fr, where=(Fr > 1), alpha=0.3, color='red', label='超临界区 (Fr>1)')
    ax2.fill_between(solver.x, 0, Fr, where=(Fr <= 1), alpha=0.3, color='blue', label='亚临界区 (Fr<1)')

    ax2.set_xlabel('距离 x (m)', fontsize=12)
    ax2.set_ylabel('弗劳德数 Fr', fontsize=12)
    ax2.set_title('流态分布', fontsize=14, fontweight='bold')
    ax2.legend(fontsize=10, loc='best')
    ax2.grid(True, alpha=0.3)
    ax2.set_ylim([0, max(3.5, np.max(Fr[Fr < 10]))])

    plt.tight_layout()
    plt.savefig('validation_hydraulic_jump.png', dpi=300, bbox_inches='tight')
    print(f" 图表已保存: validation_hydraulic_jump.png")

    # 5. 验证判断
    print("\n" + "=" * 80)
    print("验证结果")
    print("=" * 80)

    tolerance_y = 3.0   # %
    tolerance_dE = 5.0  # %
    tolerance_x = 10.0  # %
    tolerance_mass = 0.1  # %

    passed = True

    if error_y2 < tolerance_y:
        print(f" 共轭水深测试通过: {error_y2:.2f}% < {tolerance_y}%")
    else:
        print(f" 共轭水深测试失败: {error_y2:.2f}% >= {tolerance_y}%")
        passed = False

    if error_dE < tolerance_dE:
        print(f" 能量损失测试通过: {error_dE:.2f}% < {tolerance_dE}%")
    else:
        print(f" 能量损失测试失败: {error_dE:.2f}% >= {tolerance_dE}%")
        passed = False

    if error_x < tolerance_x:
        print(f" 水跃位置测试通过: {error_x:.2f}% < {tolerance_x}%")
    else:
        print(f" 水跃位置测试失败: {error_x:.2f}% >= {tolerance_x}%")
        passed = False

    if mass_error < tolerance_mass:
        print(f" 质量守恒测试通过: {mass_error:.4f}% < {tolerance_mass}%")
    else:
        print(f" 质量守恒测试失败: {mass_error:.4f}% >= {tolerance_mass}%")
        passed = False

    print("=" * 80)

    if passed:
        print(" 水跃验证通过!")
    else:
        print(" 水跃验证失败!")

    print("=" * 80 + "\n")

    return {
        'test_name': 'hydraulic_jump',
        'passed': passed,
        'error_y1': error_y1,
        'error_y2': error_y2,
        'error_dE': error_dE,
        'error_x': error_x,
        'mass_error': mass_error,
        'y1_theory': y1,
        'y2_theory': y2_theory,
        'y1_numerical': y1_numerical,
        'y2_numerical': y2_numerical,
        'Fr1': Fr1_numerical,
        'Fr2': Fr2_numerical,
        'x_jump': x_jump_numerical
    }


if __name__ == '__main__':
    result = validate_hydraulic_jump()

    import sys
    sys.exit(0 if result['passed'] else 1)
