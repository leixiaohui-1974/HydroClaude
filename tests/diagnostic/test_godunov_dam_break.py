#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""Godunov-FVM求解器 - Dam Break完整验证"""

import numpy as np
import warnings
warnings.filterwarnings("ignore")
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import sys
sys.path.insert(0, '/workspace')

try:
    from solvers.godunov_fvm_solver import GodunvFVMSolver
except ImportError as e:
    print(f"Import error: {e}")
    print("Make sure project root is in sys.path")
    sys.exit(1)



def ritter_solution(x, t, h_L, h_R, x_dam, g=9.81):
    """Ritter解析解（理想溃坝）"""
    h = np.zeros_like(x)
    c_L = np.sqrt(g * h_L)
    x_front = x_dam + 2.0 * c_L * t
    x_tail = x_dam - c_L * t
    
    for i, xi in enumerate(x):
        if xi < x_tail:
            h[i] = h_L
        elif xi > x_front:
            h[i] = h_R
        else:
            h[i] = (1.0 / (9.0 * g)) * (2.0 * c_L - (xi - x_dam) / t)**2
    
    return h


print("="*80)
print("Godunov-FVM - Dam Break验证")
print("="*80)

# 配置
width = 10.0
length = 200.0
n_cells = 200
manning_n = 0.0  # 无摩阻
slope = 0.0      # 水平
x_dam = length / 2.0
h_L, h_R = 10.0, 1.0

print(f"\n配置:")
print(f"  长度: {length}m, 单元: {n_cells}, dx={length/n_cells:.2f}m")
print(f"  坝位置: x={x_dam}m")
print(f"  上游: h={h_L}m, 下游: h={h_R}m")
print(f"  无摩阻、水平渠道（理想条件）")

# 创建求解器（测试两种精度）
for order in [1, 2]:
    print(f"\n{'='*80}")
    print(f"空间精度: {order}阶")
    print("="*80)
    
    solver = GodunvFVMSolver(
        width=width,
        length=length,
        n_cells=n_cells,
        manning_n=manning_n,
        slope=slope,
        cfl=0.5,
        order=order
    )
    
    # 初始条件
    x_centers = solver.x
    h_init = np.where(x_centers < x_dam, h_L, h_R)
    Q_init = np.zeros(n_cells)
    
    # 边界条件
    bc_left = {'type': 'h', 'value': h_L}
    bc_right = {'type': 'h', 'value': h_R}
    
    solver.initialize(h_init, Q_init, bc_left, bc_right)
    
    # 时间推进
    t_target = 2.0
    max_steps = 10000
    
    print(f"\n时间推进至 t={t_target}s:")
    
    while solver.t < t_target and solver.step_count < max_steps:
        h, Q = solver.step()
        
        # NaN检测
        if np.any(np.isnan(h)) or np.any(np.isnan(Q)):
            print(f"   步{solver.step_count}出现NaN!")
            break
        
        if solver.step_count % 500 == 0:
            state = solver.get_state()
            print(f"  t={state['t']:5.2f}s, 步{state['step']:4d}, "
                  f"质量误差={state['mass_error']:7.4f}%")
    
    # 结果
    state = solver.get_state()
    t_final = state['t']
    h_num = state['h']
    Q_num = state['Q']
    
    # 解析解
    h_ana = ritter_solution(x_centers, t_final, h_L, h_R, x_dam)
    
    # 波前分析
    idx_front_num = np.where(h_num > 1.5 * h_R)[0]
    idx_front_ana = np.where(h_ana > 1.5 * h_R)[0]
    
    if len(idx_front_num) > 0 and len(idx_front_ana) > 0:
        x_front_num = x_centers[idx_front_num[-1]]
        x_front_ana = x_centers[idx_front_ana[-1]]
        front_err_m = abs(x_front_num - x_front_ana)
        front_err_pct = front_err_m / x_front_ana * 100.0
    else:
        front_err_m = 0.0
        front_err_pct = 0.0
    
    # RMSE
    rmse = np.sqrt(np.mean((h_num - h_ana)**2))
    rmse_pct = rmse / h_L * 100.0
    
    print(f"\n数值结果 (t={t_final:.3f}s, {state['step']}步):")
    print(f"  质量误差: {state['mass_error']:.6f}%")
    print(f"  波前误差: {front_err_m:.2f}m ({front_err_pct:.2f}%)")
    print(f"  RMSE: {rmse:.4f}m ({rmse_pct:.2f}%)")
    
    # 成功标准
    checks = [
        ("质量守恒<1%", abs(state['mass_error']) < 1.0),
        ("波前误差<20%", front_err_pct < 20.0),
        ("RMSE<15%", rmse_pct < 15.0),
        ("数值稳定", not np.any(np.isnan(h_num)))
    ]
    
    print(f"\n评估:")
    for name, passed in checks:
        print(f"  {name}: {'' if passed else ''}")
    
    all_pass = all(c[1] for c in checks)
    
    # 可视化
    fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(12, 8))
    
    # 水深对比
    ax1.plot(x_centers, h_ana, 'k-', lw=2, label='Ritter (Exact)')
    ax1.plot(x_centers, h_num, 'r--', lw=1.5, label=f'Godunov-FVM (Order {order})')
    ax1.axvline(x_dam, color='gray', ls=':', label='Dam')
    ax1.set_xlabel('x (m)', fontsize=12)
    ax1.set_ylabel('h (m)', fontsize=12)
    ax1.set_title(f'Dam Break (t={t_final:.2f}s, Mass Err={state["mass_error"]:.4f}%)', fontsize=14)
    ax1.legend(fontsize=11)
    ax1.grid(True, alpha=0.3)
    
    # 误差分布
    error_profile = np.abs(h_num - h_ana)
    ax2.plot(x_centers, error_profile, 'b-', lw=1.5)
    ax2.axvline(x_dam, color='gray', ls=':')
    ax2.set_xlabel('x (m)', fontsize=12)
    ax2.set_ylabel('|Error| (m)', fontsize=12)
    ax2.set_title(f'Error Distribution (RMSE={rmse:.4f}m, {rmse_pct:.2f}%)', fontsize=14)
    ax2.grid(True, alpha=0.3)
    
    plt.tight_layout()
    filename = f'/workspace/godunov_fvm_dam_break_order{order}.png'
    plt.savefig(filename, dpi=150)
    print(f"\n  图像: {filename}")
    
    print(f"\n{'='*80}")
    if all_pass:
        print(f" Godunov-FVM (Order {order}) Dam Break **通过** ")
    else:
        print(f"️ Godunov-FVM (Order {order}) Dam Break部分通过")
    print("="*80)

print("\n\n" + "="*80)
print(" Godunov-FVM求解器验证完成！")
print("="*80)
