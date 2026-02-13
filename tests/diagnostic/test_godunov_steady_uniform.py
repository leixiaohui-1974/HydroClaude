#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Godunov-FVM - 稳态均匀流验证

测试Godunov-FVM能否达到稳态均匀流，并与理论值对比
"""

import numpy as np
import warnings
warnings.filterwarnings("ignore")
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import sys
sys.path.insert(0, '/workspace')

import pytest
try:
    from solvers.godunov_fvm_solver import GodunvFVMSolver
except ImportError as e:
    pytest.skip(f"Required module not available: {e}", allow_module_level=True)

from utils.canal_utils import compute_steady_uniform_flow


print("="*80)
print("Godunov-FVM - 稳态均匀流验证")
print("="*80)

# 配置
width = 10.0
length = 1000.0
n_cells = 100
manning_n = 0.025
slope = 0.001
Q_target = 50.0  # m^3/s

print(f"\n配置:")
print(f"  长度: {length}m, 单元: {n_cells}, dx={length/n_cells:.2f}m")
print(f"  宽度: {width}m")
print(f"  Manning n: {manning_n}")
print(f"  坡度: {slope}")
print(f"  目标流量: {Q_target} m^3/s")

# 理论均匀流水深
h_uniform = compute_steady_uniform_flow(
    Q=Q_target,
    B=width,
    S0=slope,
    n=manning_n
)

print(f"\n理论均匀流水深: {h_uniform:.4f} m")

# 测试两种精度
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
        g=9.81,
        cfl=0.5,
        order=order
    )
    
    # 初始条件：接近均匀流
    h_init = np.ones(n_cells) * h_uniform
    Q_init = np.ones(n_cells) * Q_target
    
    # 边界条件
    bc_left = {'type': 'Q', 'value': Q_target}  # 上游流量
    bc_right = {'type': 'h', 'value': h_uniform}  # 下游水深
    
    solver.initialize(h_init, Q_init, bc_left, bc_right)
    
    # 时间推进到稳态
    t_target = 1000.0  # 1000秒应该足够达到稳态
    max_steps = 10000
    
    print(f"\n时间推进至稳态 (t_max={t_target}s):")
    
    # 记录历史
    history = {
        't': [],
        'h_mean': [],
        'Q_mean': [],
        'mass_error': []
    }
    
    while solver.t < t_target and solver.step_count < max_steps:
        h, Q = solver.step()
        
        # NaN检测
        if np.any(np.isnan(h)) or np.any(np.isnan(Q)):
            print(f"   步{solver.step_count}出现NaN!")
            break
        
        # 记录
        if solver.step_count % 50 == 0:
            state = solver.get_state()
            history['t'].append(state['t'])
            history['h_mean'].append(np.mean(state['h']))
            history['Q_mean'].append(np.mean(state['Q']))
            history['mass_error'].append(state['mass_error'])
            
            if solver.step_count % 500 == 0:
                print(f"  t={state['t']:6.1f}s, 步{state['step']:4d}, "
                      f"<h>={np.mean(state['h']):.4f}m, "
                      f"<Q>={np.mean(state['Q']):.2f}m^3/s, "
                      f"质量误差={state['mass_error']:.4f}%")
    
    # 最终结果
    state = solver.get_state()
    h_final = state['h']
    Q_final = state['Q']
    
    # 分析稳态
    h_mean = np.mean(h_final)
    Q_mean = np.mean(Q_final)
    
    # 与理论对比
    h_error = abs(h_mean - h_uniform) / h_uniform * 100.0
    Q_error = abs(Q_mean - Q_target) / Q_target * 100.0
    
    # 均匀性（标准差）
    h_std = np.std(h_final)
    Q_std = np.std(Q_final)
    h_uniformity = h_std / h_mean * 100.0
    Q_uniformity = Q_std / Q_mean * 100.0
    
    print(f"\n稳态结果 (t={state['t']:.1f}s, {state['step']}步):")
    print(f"  质量误差: {state['mass_error']:.6f}%")
    print(f"  平均水深: {h_mean:.4f}m (理论: {h_uniform:.4f}m, 误差: {h_error:.2f}%)")
    print(f"  平均流量: {Q_mean:.2f}m^3/s (目标: {Q_target:.2f}m^3/s, 误差: {Q_error:.2f}%)")
    print(f"  水深均匀性: {h_uniformity:.4f}% (标准差/均值)")
    print(f"  流量均匀性: {Q_uniformity:.4f}%")
    
    # 成功标准
    checks = [
        ("质量守恒<1%", abs(state['mass_error']) < 1.0),
        ("水深误差<5%", h_error < 5.0),
        ("流量误差<5%", Q_error < 5.0),
        ("水深均匀<2%", h_uniformity < 2.0),
        ("数值稳定", not np.any(np.isnan(h_final)))
    ]
    
    print(f"\n评估:")
    for name, passed in checks:
        print(f"  {name}: {'' if passed else ''}")
    
    all_pass = all(c[1] for c in checks)
    
    # 可视化
    fig = plt.figure(figsize=(14, 10))
    gs = fig.add_gridspec(3, 2, hspace=0.3, wspace=0.3)
    
    # 水深剖面
    ax1 = fig.add_subplot(gs[0, 0])
    ax1.plot(solver.x, h_final, 'b-', lw=1.5, label='Numerical')
    ax1.axhline(h_uniform, color='r', ls='--', lw=2, label=f'Uniform ({h_uniform:.4f}m)')
    ax1.fill_between(solver.x, h_uniform - 0.01, h_uniform + 0.01, 
                      color='red', alpha=0.2, label='+/-1cm tolerance')
    ax1.set_xlabel('x (m)', fontsize=11)
    ax1.set_ylabel('h (m)', fontsize=11)
    ax1.set_title('Water Depth Profile', fontsize=12)
    ax1.legend(fontsize=10)
    ax1.grid(True, alpha=0.3)
    
    # 流量剖面
    ax2 = fig.add_subplot(gs[0, 1])
    ax2.plot(solver.x, Q_final, 'g-', lw=1.5, label='Numerical')
    ax2.axhline(Q_target, color='r', ls='--', lw=2, label=f'Target ({Q_target:.1f}m^3/s)')
    ax2.fill_between(solver.x, Q_target * 0.99, Q_target * 1.01,
                      color='red', alpha=0.2, label='+/-1% tolerance')
    ax2.set_xlabel('x (m)', fontsize=11)
    ax2.set_ylabel('Q (m^3/s)', fontsize=11)
    ax2.set_title('Discharge Profile', fontsize=12)
    ax2.legend(fontsize=10)
    ax2.grid(True, alpha=0.3)
    
    # 水深误差
    ax3 = fig.add_subplot(gs[1, 0])
    h_error_profile = (h_final - h_uniform) / h_uniform * 100.0
    ax3.plot(solver.x, h_error_profile, 'b-', lw=1.5)
    ax3.axhline(0, color='k', ls='-', lw=0.5)
    ax3.set_xlabel('x (m)', fontsize=11)
    ax3.set_ylabel('Depth Error (%)', fontsize=11)
    ax3.set_title(f'Depth Error (Mean: {h_error:.2f}%)', fontsize=12)
    ax3.grid(True, alpha=0.3)
    
    # 流量误差
    ax4 = fig.add_subplot(gs[1, 1])
    Q_error_profile = (Q_final - Q_target) / Q_target * 100.0
    ax4.plot(solver.x, Q_error_profile, 'g-', lw=1.5)
    ax4.axhline(0, color='k', ls='-', lw=0.5)
    ax4.set_xlabel('x (m)', fontsize=11)
    ax4.set_ylabel('Discharge Error (%)', fontsize=11)
    ax4.set_title(f'Discharge Error (Mean: {Q_error:.2f}%)', fontsize=12)
    ax4.grid(True, alpha=0.3)
    
    # 时间演化（水深）
    ax5 = fig.add_subplot(gs[2, 0])
    if len(history['t']) > 0:
        ax5.plot(history['t'], history['h_mean'], 'b-', lw=1.5)
        ax5.axhline(h_uniform, color='r', ls='--', lw=1)
        ax5.set_xlabel('Time (s)', fontsize=11)
        ax5.set_ylabel('Mean Depth (m)', fontsize=11)
        ax5.set_title('Convergence to Steady State (Depth)', fontsize=12)
        ax5.grid(True, alpha=0.3)
    
    # 时间演化（质量误差）
    ax6 = fig.add_subplot(gs[2, 1])
    if len(history['t']) > 0:
        ax6.plot(history['t'], history['mass_error'], 'r-', lw=1.5)
        ax6.axhline(0, color='k', ls='-', lw=0.5)
        ax6.set_xlabel('Time (s)', fontsize=11)
        ax6.set_ylabel('Mass Error (%)', fontsize=11)
        ax6.set_title('Mass Conservation Over Time', fontsize=12)
        ax6.grid(True, alpha=0.3)
    
    filename = f'/workspace/godunov_steady_uniform_order{order}.png'
    plt.savefig(filename, dpi=150)
    print(f"\n  图像: {filename}")
    
    print(f"\n{'='*80}")
    if all_pass:
        print(f" 稳态均匀流 (Order {order}) **通过** ")
    else:
        print(f"️ 稳态均匀流 (Order {order}) 部分通过")
    print("="*80)

print("\n\n" + "="*80)
print(" 稳态均匀流验证完成！")
print("="*80)
