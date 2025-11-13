#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
诊断MacCormack质量守恒问题

当前问题：静止水体质量误差-1.88%

可能原因：
1. 边界条件不守恒
2. 预测-校正步不对称
3. 人工粘性（已禁用）
4. 通量计算误差
"""

import numpy as np
import sys
sys.path.insert(0, '/workspace')

from solvers.maccormack_solver import MacCormackSolver


def diagnose_mass_conservation():
    """详细诊断质量守恒"""
    
    print("="*80)
    print("MacCormack质量守恒诊断")
    print("="*80)
    
    # 简单配置
    width = 10.0
    length = 1000.0
    n_cells = 20  # 减少单元，便于分析
    manning_n = 0.025
    slope = 0.001
    
    solver = MacCormackSolver(
        width=width,
        length=length,
        n_cells=n_cells,
        manning_n=manning_n,
        slope=slope,
        cfl=0.5,
        use_artificial_viscosity=False  # 禁用人工粘性
    )
    
    # 初始条件：静止水体
    h_init = np.ones(n_cells + 1) * 2.0
    Q_init = np.zeros(n_cells + 1)
    
    # 边界条件
    bc_upstream = {'type': 'h', 'value': 2.0}
    bc_downstream = {'type': 'h', 'value': 2.0}
    
    solver.initialize(h_init, Q_init, bc_upstream, bc_downstream)
    
    print(f"\n初始状态:")
    print(f"  初始质量: {solver.total_mass:.6f} m³")
    print(f"  h[0] = {solver.h[0]:.6f}, h[-1] = {solver.h[-1]:.6f}")
    print(f"  Q[0] = {solver.Q[0]:.6f}, Q[-1] = {solver.Q[-1]:.6f}")
    
    # 单步详细分析
    print(f"\n第1步详细分析:")
    
    dt = solver.compute_dt()
    print(f"  dt = {dt:.6f} s")
    
    h_before = solver.h.copy()
    Q_before = solver.Q.copy()
    mass_before = solver._compute_total_mass()
    
    # 执行一步
    h_after, Q_after = solver.step(dt)
    mass_after = solver._compute_total_mass()
    
    # 分析变化
    dh = h_after - h_before
    dQ = Q_after - Q_before
    dmass = mass_after - mass_before
    
    print(f"\n  变化分析:")
    print(f"    质量变化: {dmass:.6e} m³ ({dmass/mass_before*100:.6f}%)")
    print(f"    max|dh|: {np.max(np.abs(dh)):.6e} m")
    print(f"    max|dQ|: {np.max(np.abs(dQ)):.6e} m³/s")
    
    # 边界贡献
    print(f"\n  边界分析:")
    print(f"    h[0]: {h_before[0]:.6f} → {h_after[0]:.6f} (dh={dh[0]:.6e})")
    print(f"    h[-1]: {h_before[-1]:.6f} → {h_after[-1]:.6f} (dh={dh[-1]:.6e})")
    print(f"    Q[0]: {Q_before[0]:.6f} → {Q_after[0]:.6f} (dQ={dQ[0]:.6e})")
    print(f"    Q[-1]: {Q_before[-1]:.6f} → {Q_after[-1]:.6f} (dQ={dQ[-1]:.6e})")
    
    # 内部节点
    print(f"\n  内部节点分析 (节点1-{n_cells-1}):")
    print(f"    max|dh|_internal: {np.max(np.abs(dh[1:-1])):.6e}")
    print(f"    max|dQ|_internal: {np.max(np.abs(dQ[1:-1])):.6e}")
    
    # 连续多步
    print(f"\n连续10步质量跟踪:")
    for step in range(10):
        solver.step()
        mass = solver._compute_total_mass()
        error = (mass - solver.total_mass) / solver.total_mass * 100
        
        if step % 2 == 0:
            print(f"  步骤 {step+2}: 质量={mass:.6f} m³, 误差={error:.6f}%")
    
    # 最终分析
    final_error = solver.get_mass_conservation_error()
    print(f"\n最终质量误差: {final_error:.6f}%")
    
    # 分析误差累积
    print(f"\n误差累积分析:")
    print(f"  每步平均误差: {final_error / 10:.6f}%")
    print(f"  累积方式: {'系统性（单向）' if abs(final_error) > 0.5 else '随机性（双向抵消）'}")
    
    return final_error


def test_boundary_mass_flux():
    """测试边界质量通量"""
    
    print("\n" + "="*80)
    print("边界质量通量测试")
    print("="*80)
    
    # 配置：有入流
    width = 10.0
    length = 1000.0
    n_cells = 20
    
    solver = MacCormackSolver(
        width=width,
        length=length,
        n_cells=n_cells,
        manning_n=0.025,
        slope=0.001,
        use_artificial_viscosity=False
    )
    
    # 初始：静止
    h_init = np.ones(n_cells + 1) * 2.0
    Q_init = np.zeros(n_cells + 1)
    
    # 边界：上游入流
    Q_in = 5.0  # m³/s
    bc_upstream = {'type': 'Q', 'value': Q_in}
    bc_downstream = {'type': 'h', 'value': 2.0}
    
    solver.initialize(h_init, Q_init, bc_upstream, bc_downstream)
    
    print(f"\n配置:")
    print(f"  上游入流: Q = {Q_in} m³/s")
    print(f"  下游水位: h = 2.0 m")
    print(f"  初始质量: {solver.total_mass:.2f} m³")
    
    # 运行一段时间
    t_end = 100.0
    while solver.t < t_end:
        solver.step()
    
    # 分析
    final_mass = solver._compute_total_mass()
    expected_increase = Q_in * t_end  # 理论上应该增加这么多
    actual_increase = final_mass - solver.total_mass
    
    print(f"\n结果 (t={t_end}s):")
    print(f"  初始质量: {solver.total_mass:.2f} m³")
    print(f"  最终质量: {final_mass:.2f} m³")
    print(f"  理论增加: {expected_increase:.2f} m³")
    print(f"  实际增加: {actual_increase:.2f} m³")
    print(f"  误差: {(actual_increase - expected_increase):.2f} m³ ({(actual_increase - expected_increase)/expected_increase*100:.2f}%)")


if __name__ == "__main__":
    # 诊断1：静止水体
    error1 = diagnose_mass_conservation()
    
    # 诊断2：边界通量
    test_boundary_mass_flux()
    
    print("\n" + "="*80)
    print("诊断完成")
    print("="*80)
    
    # 结论
    print("\n结论:")
    if abs(error1) > 0.5:
        print("   质量守恒有问题（误差>0.5%）")
        print("  可能原因:")
        print("    1. 边界条件处理不守恒")
        print("    2. 预测-校正不对称")
        print("    3. 时间积分误差累积")
    else:
        print("   质量守恒良好（误差<0.5%）")
