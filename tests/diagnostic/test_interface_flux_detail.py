#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
界面通量详细诊断

根据质量平衡验证的发现：3.675%的质量在消失
本测试将打印所有界面通量，检查守恒性

核心验证：
对于守恒律：dm_i/dt = (F_{i-1/2} - F_{i+1/2}) * B
全域求和：d(Σm_i)/dt = (F_{-1/2} - F_{n+1/2}) * B = (F_left - F_right) * B

如果守恒性成立：Σ(F_{i+1/2} - F_{i-1/2}) = F_right - F_left
"""

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '../..'))

import numpy as np
try:
    from solvers.godunov_fvm_solver import GodunvFVMSolver
except ImportError as e:
    print(f"Import error: {e}")
    print("Make sure project root is in sys.path")
    sys.exit(1)



def test_interface_flux_detail():
    """详细检查界面通量"""

    print("\n" + "="*80)
    print("界面通量详细诊断")
    print("="*80)

    print("\n目标：验证Σ(F_{i+1/2} - F_{i-1/2}) = F_right - F_left")

    # 简单设置
    B = 1.0
    L = 1000.0
    n_cells = 20
    Q_bc = 2.0
    g = 9.81
    h_c = (Q_bc**2 / (g * B**2))**(1/3)

    print(f"\n测试参数：")
    print(f"  n_cells = {n_cells}")
    print(f"  dx = {L/n_cells:.1f} m")

    # 创建求解器
    solver = GodunvFVMSolver(
        width=B,
        length=L,
        n_cells=n_cells,
        manning_n=0.03,
        slope=0.002,
        cfl=0.4,
        order=1,
        well_balanced=False,
        use_numba=False
    )

    # 初始化
    h_init = np.linspace(h_c * 1.5, h_c, n_cells)
    Q_init = np.ones(n_cells) * Q_bc

    bc_left = {'type': 'Q', 'value': Q_bc}
    bc_right = {'type': 'h', 'value': h_c}

    solver.initialize(h_init, Q_init, bc_left, bc_right)

    print(f"  初始质量 = {solver.initial_mass:.2f} m^3")

    # 运行一步
    print(f"\n{'='*80}")
    print("单步通量详细分析")
    print("="*80)

    # 步前
    h_before = solver.h.copy()
    mass_before = np.sum(h_before * solver.dx * solver.B)

    print(f"\n步前质量 = {mass_before:.6f} m^3")

    # 计算时间步长
    dt = solver.compute_dt()
    print(f"时间步长 dt = {dt:.6f} s")

    # 执行一步
    solver.step()

    # 步后
    h_after = solver.h.copy()
    mass_after = np.sum(h_after * solver.dx * solver.B)
    delta_mass = mass_after - mass_before

    print(f"步后质量 = {mass_after:.6f} m^3")
    print(f"质量变化 = {delta_mass:.6f} m^3")

    # 获取界面通量
    F_h = solver.last_F_h

    if F_h is None:
        print("\n 错误：solver.last_F_h 是 None，未保存界面通量")
        return

    print(f"\n界面通量数组长度: {len(F_h)} (应为 {n_cells+1})")

    # 打印所有界面通量
    print(f"\n{'='*80}")
    print("所有界面通量（质量通量 F_h）")
    print("="*80)

    print(f"\n{'界面':<10} {'F_h (m^2/s)':<15} {'说明':<30}")
    print("-" * 60)

    for i in range(len(F_h)):
        if i == 0:
            desc = "左边界（流入）"
        elif i == len(F_h) - 1:
            desc = "右边界（流出）"
        else:
            desc = f"单元 {i-1} 和 {i} 之间"
        print(f"{i:<10} {F_h[i]:>14.6f} {desc}")

    # 检查通量守恒
    print(f"\n{'='*80}")
    print("通量守恒性检查")
    print("="*80)

    # 边界通量
    F_left = F_h[0]
    F_right = F_h[-1]

    print(f"\n边界通量：")
    print(f"  F_left  (流入) = {F_left:.6f} m^2/s")
    print(f"  F_right (流出) = {F_right:.6f} m^2/s")
    print(f"  净边界通量 = {F_left - F_right:.6f} m^2/s")

    # 计算每个单元的通量差
    print(f"\n单元通量平衡：")
    print(f"\n{'单元':<6} {'F_in':<12} {'F_out':<12} {'净通量':<12} {'Δm预期':<12} {'Δm实际':<12}")
    print("-" * 75)

    total_flux_diff = 0.0
    for i in range(n_cells):
        F_in = F_h[i]      # 左界面流入
        F_out = F_h[i+1]   # 右界面流出
        net_flux = F_in - F_out
        delta_m_expected = net_flux * dt * B
        delta_m_actual = (h_after[i] - h_before[i]) * solver.dx * B

        total_flux_diff += net_flux

        if i < 3 or i >= n_cells - 3:
            print(f"{i:<6} {F_in:>11.6f} {F_out:>11.6f} {net_flux:>11.6f} {delta_m_expected:>11.6f} {delta_m_actual:>11.6f}")
        elif i == 3:
            print("  ...")

    # 总和验证
    print(f"\n{'='*80}")
    print("全域守恒性验证")
    print("="*80)

    # 理论：Σ(F_in - F_out) = F_left - F_right
    sum_flux_diff = total_flux_diff
    boundary_flux_diff = F_left - F_right

    print(f"\n方法1（单元求和）：")
    print(f"  Σ(F_{{i-1/2}} - F_{{i+1/2}}) = {sum_flux_diff:.6f} m^2/s")

    print(f"\n方法2（边界差）：")
    print(f"  F_left - F_right = {boundary_flux_diff:.6f} m^2/s")

    print(f"\n差异：")
    discrepancy = sum_flux_diff - boundary_flux_diff
    print(f"  绝对差异 = {discrepancy:.9f} m^2/s")
    print(f"  相对差异 = {abs(discrepancy)/abs(boundary_flux_diff)*100:.6f}%")

    # 质量平衡验证
    print(f"\n质量平衡验证：")
    delta_m_from_boundary = boundary_flux_diff * dt * B
    print(f"  实际质量变化 = {delta_mass:.6f} m^3")
    print(f"  边界通量预期 = {delta_m_from_boundary:.6f} m^3")
    print(f"  差异 = {delta_mass - delta_m_from_boundary:.6f} m^3")
    print(f"  相对差异 = {abs(delta_mass - delta_m_from_boundary)/abs(delta_m_from_boundary)*100:.3f}%")

    # 诊断结论
    print(f"\n{'='*80}")
    print("诊断结论")
    print("="*80)

    if abs(discrepancy) / abs(boundary_flux_diff) < 1e-10:
        print(f"\n 通量求和完美守恒！")
        print(f"   Σ(F_{{i+1/2}} - F_{{i-1/2}}) ≡ F_right - F_left")
        print(f"   差异 < 10^-10")
    else:
        print(f"\n 通量求和不守恒！")
        print(f"   差异 = {discrepancy:.9f} m^2/s ({abs(discrepancy)/abs(boundary_flux_diff)*100:.6f}%)")

    mass_balance_error = abs(delta_mass - delta_m_from_boundary)/abs(delta_m_from_boundary)*100
    if mass_balance_error < 0.1:
        print(f"\n 单步质量平衡成立！")
        print(f"   实际质量变化 ~= 边界通量预期")
        print(f"   差异 < 0.1%")
        print(f"\n这说明通量计算本身是守恒的")
        print(f"但为什么长时间运行后有3.675%的质量消失？")
        print(f"\n可能原因：")
        print(f"  1. 边界条件处理的累积误差")
        print(f"  2. 干湿界面处理")
        print(f"  3. TVD-RK2时间积分的非守恒性")
    else:
        print(f"\n 单步质量平衡不成立！")
        print(f"   差异 = {mass_balance_error:.3f}%")
        print(f"\n问题定位：")
        print(f"  通量计算或时间积分有bug")

    # 长时间测试
    print(f"\n{'='*80}")
    print("长时间累积测试（500步）")
    print("="*80)

    # 重新初始化
    solver.initialize(h_init, Q_init, bc_left, bc_right)

    mass_initial = solver.initial_mass
    cumulative_inflow = 0.0
    cumulative_outflow = 0.0

    for step in range(500):
        dt_step = solver.compute_dt()
        solver.step()

        if solver.last_F_h is not None:
            cumulative_inflow += solver.last_F_h[0] * dt_step
            cumulative_outflow += solver.last_F_h[-1] * dt_step

        if (step + 1) % 100 == 0:
            mass_current = np.sum(solver.h * solver.dx * solver.B)
            mass_theory = mass_initial + cumulative_inflow - cumulative_outflow
            error = abs(mass_current - mass_theory) / abs(mass_theory) * 100
            print(f"  步数={step+1:3d}, t={solver.t:6.1f}s, 实际={mass_current:8.2f} m^3, 理论={mass_theory:8.2f} m^3, 差异={error:5.2f}%")

    mass_final = np.sum(solver.h * solver.dx * solver.B)
    mass_theory_final = mass_initial + cumulative_inflow - cumulative_outflow

    print(f"\n500步后：")
    print(f"  实际质量 = {mass_final:.2f} m^3")
    print(f"  理论质量 = {mass_theory_final:.2f} m^3")
    print(f"  差异 = {abs(mass_final - mass_theory_final):.2f} m^3 ({abs(mass_final - mass_theory_final)/abs(mass_theory_final)*100:.2f}%)")

    print("\n" + "="*80)
    print("测试完成")
    print("="*80)


if __name__ == "__main__":
    test_interface_flux_detail()
