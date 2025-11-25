#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
MacDonald Test 2 详细质量平衡分析

目标：判断33.6%的质量"误差"是物理正确还是数值bug

分析方法：
1. 记录左右边界的通量演化
2. 计算理论质量变化 = 初始质量 + 累积流入 - 累积流出
3. 计算实际质量变化 = 最终质量 - 初始质量
4. 对比差异

关键问题：
- 左边界Q=2.0：流入量应该准确控制
- 右边界h=h_c：流出量由Riemann求解器决定
- 如果理论~=实际，说明数值方法正确，质量变化是物理行为
- 如果理论≠实际，说明有数值bug
"""

import sys
import warnings
warnings.filterwarnings("ignore")
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '../..'))

import numpy as np
try:
    from solvers.godunov_fvm_solver import GodunvFVMSolver
except ImportError as e:
    print(f"Import error: {e}")
    print("Make sure project root is in sys.path")
    sys.exit(1)



def test_macdonald_test2_detailed_mass():
    """MacDonald Test 2 详细质量平衡分析"""

    print("\n" + "="*80)
    print("MacDonald Test 2 - 详细质量平衡分析")
    print("="*80)

    # MacDonald Test 2参数
    B = 1.0
    n = 0.03
    S0 = 0.002
    L = 1000.0
    Q_bc = 2.0
    g = 9.81

    # 临界水深
    h_c = (Q_bc**2 / (g * B**2))**(1/3)

    print(f"\n测试参数：")
    print(f"  河道：L={L}m, B={B}m, n={n}, S0={S0}")
    print(f"  边界条件：")
    print(f"    左：Q = {Q_bc} m^3/s (固定流量)")
    print(f"    右：h = {h_c:.4f} m (临界水深)")
    print(f"\n边界条件类型：")
    print(f"  左边界（Q边界）：流入量受控")
    print(f"  右边界（h边界）：流出量由Riemann求解器决定")

    # 创建求解器
    n_cells = 50
    solver = GodunvFVMSolver(
        width=B,
        length=L,
        n_cells=n_cells,
        manning_n=n,
        slope=S0,
        cfl=0.4,
        order=1,
        use_numba=False
    )

    # 初始化为均匀流
    h_init = np.ones(n_cells) * h_c * 1.5
    Q_init = np.ones(n_cells) * Q_bc

    bc_left = {'type': 'Q', 'value': Q_bc}
    bc_right = {'type': 'h', 'value': h_c}

    solver.initialize(h_init, Q_init, bc_left, bc_right)

    # 初始质量
    mass_initial = solver.initial_mass

    print(f"\n初始状态：")
    print(f"  初始质量 = {mass_initial:.4f} m^3")
    print(f"  h范围：[{solver.h.min():.4f}, {solver.h.max():.4f}] m")
    print(f"  Q范围：[{solver.Q.min():.4f}, {solver.Q.max():.4f}] m^3/s")

    # 运行模拟
    t_end = 50.0
    cumulative_inflow = 0.0
    cumulative_outflow = 0.0

    # 记录边界通量历史
    time_history = []
    F_left_history = []
    F_right_history = []
    Q_left_history = []
    Q_right_history = []
    mass_history = []

    print(f"\n运行到 t={t_end}s...")
    print(f"\n{'时间(s)':<10} {'F_left':<12} {'F_right':<12} {'Q_in累积':<12} {'Q_out累积':<12} {'实际质量':<12}")
    print("-" * 80)

    step_count = 0
    while solver.t < t_end:
        # 记录步前状态
        Q_left = solver.Q[0]
        Q_right = solver.Q[-1]

        dt = solver.compute_dt()
        solver.step()
        step_count += 1

        # 累积通量
        if solver.last_F_h is not None:
            F_left = solver.last_F_h[0]
            F_right = solver.last_F_h[-1]

            cumulative_inflow += F_left * dt * B
            cumulative_outflow += F_right * dt * B

            # 记录历史
            time_history.append(solver.t)
            F_left_history.append(F_left)
            F_right_history.append(F_right)
            Q_left_history.append(Q_left)
            Q_right_history.append(Q_right)
            mass_history.append(np.sum(solver.h * solver.dx * solver.B))

        # 每50s打印
        if int(solver.t) % 50 < dt or solver.t >= t_end:
            mass_current = np.sum(solver.h * solver.dx * solver.B)
            if solver.last_F_h is not None:
                print(f"{solver.t:<10.1f} {F_left:<12.4f} {F_right:<12.4f} {cumulative_inflow:<12.2f} {cumulative_outflow:<12.2f} {mass_current:<12.2f}")

    # 最终分析
    mass_final = np.sum(solver.h * solver.dx * solver.B)

    # 实际质量变化
    delta_mass_actual = mass_final - mass_initial

    # 理论质量变化（基于边界通量）
    delta_mass_theory = cumulative_inflow - cumulative_outflow

    # 差异
    discrepancy = delta_mass_actual - delta_mass_theory
    discrepancy_pct = abs(discrepancy) / abs(delta_mass_theory) * 100 if delta_mass_theory != 0 else 0

    print(f"\n{'='*80}")
    print("最终质量平衡分析")
    print("="*80)

    print(f"\n1. 初始和最终状态：")
    print(f"   初始质量：{mass_initial:.4f} m^3")
    print(f"   最终质量：{mass_final:.4f} m^3")
    print(f"   实际变化：{delta_mass_actual:.4f} m^3")

    print(f"\n2. 边界通量统计：")
    print(f"   累积流入 ：{cumulative_inflow:.4f} m^3")
    print(f"   累积流出 ：{cumulative_outflow:.4f} m^3")
    print(f"   净通量   ：{cumulative_inflow - cumulative_outflow:.4f} m^3")
    print(f"   理论变化：{delta_mass_theory:.4f} m^3")

    print(f"\n3. 质量平衡检查：")
    print(f"   实际质量变化：{delta_mass_actual:.4f} m^3")
    print(f"   理论质量变化：{delta_mass_theory:.4f} m^3")
    print(f"   差异         ：{discrepancy:.4f} m^3 ({discrepancy_pct:.2f}%)")

    # 检查左边界通量强制
    if len(F_left_history) > 0:
        F_left_avg = np.mean(F_left_history)
        F_left_std = np.std(F_left_history)
        F_left_min = np.min(F_left_history)
        F_left_max = np.max(F_left_history)

        print(f"\n4. 左边界通量分析（应该~={Q_bc} m^2/s）：")
        print(f"   平均：{F_left_avg:.4f} m^2/s")
        print(f"   标准差：{F_left_std:.4f} m^2/s")
        print(f"   范围：[{F_left_min:.4f}, {F_left_max:.4f}] m^2/s")

        left_error = abs(F_left_avg - Q_bc) / Q_bc * 100
        print(f"   误差：{left_error:.2f}%")

        if left_error > 1.0:
            print(f"   ️ 左边界通量未被正确控制！")
        else:
            print(f"    左边界通量控制良好")

    # 检查右边界通量
    if len(F_right_history) > 0:
        F_right_avg = np.mean(F_right_history)
        F_right_std = np.std(F_right_history)
        F_right_min = np.min(F_right_history)
        F_right_max = np.max(F_right_history)

        print(f"\n5. 右边界通量分析（由Riemann求解器决定）：")
        print(f"   平均：{F_right_avg:.4f} m^2/s")
        print(f"   标准差：{F_right_std:.4f} m^2/s")
        print(f"   范围：[{F_right_min:.4f}, {F_right_max:.4f}] m^2/s")

    # 计算通量守恒性
    print(f"\n6. 通量守恒性检查：")
    print(f"   总步数：{step_count}")

    # 检查每一步的质量变化是否匹配通量差
    if len(mass_history) > 1:
        mass_changes = np.diff(mass_history)
        flux_diffs = []

        for i in range(1, len(time_history)):
            dt_i = time_history[i] - time_history[i-1]
            flux_diff = (F_left_history[i] - F_right_history[i]) * dt_i * B
            flux_diffs.append(flux_diff)

        flux_diffs = np.array(flux_diffs)

        # 计算每步的相对误差
        step_errors = []
        for i in range(len(mass_changes)):
            if abs(flux_diffs[i]) > 1e-10:
                error = abs(mass_changes[i] - flux_diffs[i]) / abs(flux_diffs[i]) * 100
                step_errors.append(error)

        if len(step_errors) > 0:
            avg_step_error = np.mean(step_errors)
            max_step_error = np.max(step_errors)

            print(f"   单步质量误差：")
            print(f"     平均：{avg_step_error:.2f}%")
            print(f"     最大：{max_step_error:.2f}%")

            if avg_step_error > 1.0:
                print(f"    单步质量不守恒（每步都有累积误差）")
            else:
                print(f"    单步质量基本守恒")

    # 最终判断
    print(f"\n{'='*80}")
    print("诊断结论")
    print("="*80)

    if discrepancy_pct < 1.0:
        print(f"\n 质量守恒良好 ({discrepancy_pct:.2f}%)")
        print(f"\n结论：")
        print(f"  - 实际质量变化与理论质量变化一致")
        print(f"  - 数值方法正确")
        print(f"  - 质量变化是h边界的物理行为（正确！）")

    elif discrepancy_pct < 5.0:
        print(f"\n️ 质量守恒较好，但有轻微差异 ({discrepancy_pct:.2f}%)")
        print(f"\n可能原因：")
        print(f"  - 数值耗散")
        print(f"  - 时间积分截断误差")
        print(f"  - 边界条件处理的小误差")

    else:
        print(f"\n 质量守恒有明显问题 ({discrepancy_pct:.2f}%)")
        print(f"\n问题定位：")

        # 检查左边界
        if len(F_left_history) > 0:
            left_error = abs(np.mean(F_left_history) - Q_bc) / Q_bc * 100
            if left_error > 1.0:
                print(f"  1.  左边界流入未被正确控制 ({left_error:.2f}%误差)")
                print(f"     -> 检查Q边界条件的实现")
            else:
                print(f"  1.  左边界流入正确")

        # 检查单步守恒性
        if len(step_errors) > 0 and np.mean(step_errors) > 1.0:
            print(f"  2.  单步质量不守恒 (平均{np.mean(step_errors):.2f}%误差)")
            print(f"     -> 检查通量计算和时间积分")
        else:
            print(f"  2.  单步质量守恒")

        # 如果上述都正确，问题可能在别处
        if len(F_left_history) > 0 and left_error < 1.0 and (len(step_errors) == 0 or np.mean(step_errors) < 1.0):
            print(f"  3. ️ 左边界和单步都正确，但总体不守恒")
            print(f"     -> 可能是长时间累积的数值误差")
            print(f"     -> 或者边界条件与内部格式的不一致")

    print("\n" + "="*80)

    return {
        'mass_initial': mass_initial,
        'mass_final': mass_final,
        'delta_mass_actual': delta_mass_actual,
        'delta_mass_theory': delta_mass_theory,
        'discrepancy': discrepancy,
        'discrepancy_pct': discrepancy_pct,
        'cumulative_inflow': cumulative_inflow,
        'cumulative_outflow': cumulative_outflow
    }


if __name__ == "__main__":
    result = test_macdonald_test2_detailed_mass()

    print(f"\n测试总结：")
    print(f"  质量差异：{result['discrepancy_pct']:.2f}%")

    if result['discrepancy_pct'] < 1.0:
        print(f"  状态： 优秀")
    elif result['discrepancy_pct'] < 5.0:
        print(f"  状态：️ 良好")
    else:
        print(f"  状态： 需要修复")
