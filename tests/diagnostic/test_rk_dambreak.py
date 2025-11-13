#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
RK时间积分性能测试 - Dam Break

测试Euler, RK2, RK3对Dam Break精度的改进
"""

import sys
sys.path.insert(0, '/workspace')

import numpy as np
import matplotlib.pyplot as plt
from datetime import datetime

try:
    from solvers.hydrostatic_canal_solver import HydrostaticCanalSolver
except ImportError as e:
    print(f"Import error: {e}")
    print("Make sure project root is in sys.path")
    sys.exit(1)



def run_dam_break(integrator='euler', nx=501, dt=0.1, T=50.0):
    """
    运行Dam Break测试
    
    Args:
        integrator: 时间积分方法 ('euler', 'rk2', 'rk3')
        nx: 空间分辨率
        dt: 时间步长
        T: 总时间
    """
    # 参数
    L = 1000.0
    h_L = 10.0
    h_R = 0.01
    x_dam = 500.0
    g = 9.81
    
    # 创建求解器
    solver = HydrostaticCanalSolver(
        length=L,
        nx=nx,
        B=1.0,
        S0=0.0,
        n=0.0,
        g=g,
        time_integrator=integrator
    )
    
    # 初始条件
    solver.h = np.where(solver.x < x_dam, h_L, h_R)
    solver.hu = np.zeros(nx)
    
    # 时间步进
    t = 0.0
    n_steps = int(T / dt)
    
    for step in range(n_steps):
        h_new, hu_new = solver.step_explicit(dt)
        solver.h = h_new
        solver.hu = hu_new
        t += dt
        
        if (step + 1) % 100 == 0:
            print(f"  Step {step+1}/{n_steps}, t={t:.1f}s, h_max={np.max(solver.h):.3f}m")
    
    # 计算波前位置
    threshold = 0.1
    wavefront_indices = np.where(solver.h > threshold)[0]
    if len(wavefront_indices) > 0:
        x_wave = solver.x[wavefront_indices[-1]]
    else:
        x_wave = 0.0
    
    # 解析解
    c = np.sqrt(g * h_L)
    x_wave_exact = x_dam + 2 * c * T
    
    # 误差
    error = abs(x_wave - x_wave_exact) / x_wave_exact * 100
    
    # 质量守恒
    mass_final = np.sum(solver.h * solver.dx)
    mass_init = h_L * (L / 2)
    mass_error = abs(mass_final - mass_init) / mass_init * 100
    
    return {
        'x_wave': x_wave,
        'x_wave_exact': x_wave_exact,
        'error': error,
        'mass_error': mass_error,
        'h': solver.h.copy(),
        'x': solver.x.copy()
    }


def main():
    """主函数"""
    print("="*80)
    print("RK时间积分性能测试 - Dam Break")
    print("="*80)
    
    # 测试1：标准配置（nx=501, dt=0.1）
    print(f"\n{'='*80}")
    print("测试1: 标准配置（nx=501, dt=0.1s）")
    print(f"{'='*80}")
    
    print("\n运行Euler...")
    result_euler = run_dam_break(integrator='euler', nx=501, dt=0.1, T=50.0)
    print(f"\n结果（Euler）:")
    print(f"  波前位置: {result_euler['x_wave']:.2f}m (精确: {result_euler['x_wave_exact']:.2f}m)")
    print(f"  波前误差: {result_euler['error']:.2f}%")
    print(f"  质量误差: {result_euler['mass_error']:.6f}%")
    
    print("\n运行RK2...")
    result_rk2 = run_dam_break(integrator='rk2', nx=501, dt=0.1, T=50.0)
    print(f"\n结果（RK2）:")
    print(f"  波前位置: {result_rk2['x_wave']:.2f}m")
    print(f"  波前误差: {result_rk2['error']:.2f}%")
    print(f"  质量误差: {result_rk2['mass_error']:.6f}%")
    print(f"  改进: {result_euler['error'] - result_rk2['error']:.2f}%")
    
    print("\n运行RK3...")
    result_rk3 = run_dam_break(integrator='rk3', nx=501, dt=0.1, T=50.0)
    print(f"\n结果（RK3）:")
    print(f"  波前位置: {result_rk3['x_wave']:.2f}m")
    print(f"  波前误差: {result_rk3['error']:.2f}%")
    print(f"  质量误差: {result_rk3['mass_error']:.6f}%")
    print(f"  改进: {result_euler['error'] - result_rk3['error']:.2f}%")
    
    # 测试2：更细的网格（nx=1001, dt=0.05）
    print(f"\n{'='*80}")
    print("测试2: 更细网格（nx=1001, dt=0.05s）")
    print(f"{'='*80}")
    
    print("\n运行Euler...")
    result_euler_fine = run_dam_break(integrator='euler', nx=1001, dt=0.05, T=50.0)
    print(f"\n结果（Euler, fine）:")
    print(f"  波前误差: {result_euler_fine['error']:.2f}%")
    print(f"  质量误差: {result_euler_fine['mass_error']:.6f}%")
    
    print("\n运行RK2...")
    result_rk2_fine = run_dam_break(integrator='rk2', nx=1001, dt=0.05, T=50.0)
    print(f"\n结果（RK2, fine）:")
    print(f"  波前误差: {result_rk2_fine['error']:.2f}%")
    print(f"  质量误差: {result_rk2_fine['mass_error']:.6f}%")
    print(f"  改进: {result_euler_fine['error'] - result_rk2_fine['error']:.2f}%")
    
    print("\n运行RK3...")
    result_rk3_fine = run_dam_break(integrator='rk3', nx=1001, dt=0.05, T=50.0)
    print(f"\n结果（RK3, fine）:")
    print(f"  波前误差: {result_rk3_fine['error']:.2f}%")
    print(f"  质量误差: {result_rk3_fine['mass_error']:.6f}%")
    print(f"  改进: {result_euler_fine['error'] - result_rk3_fine['error']:.2f}%")
    
    # 总结
    print(f"\n{'='*80}")
    print("总结")
    print(f"{'='*80}")
    
    print(f"\n{'配置':<25} {'波前误差':<12} {'质量误差':<12} {'vs Euler'}")
    print("-"*80)
    print(f"{'Euler (nx=501,dt=0.1)':<25} {result_euler['error']:>10.2f}% {result_euler['mass_error']:>10.6f}% {'基准'}")
    print(f"{'RK2 (nx=501,dt=0.1)':<25} {result_rk2['error']:>10.2f}% {result_rk2['mass_error']:>10.6f}% {result_euler['error']-result_rk2['error']:>+7.2f}%")
    print(f"{'RK3 (nx=501,dt=0.1)':<25} {result_rk3['error']:>10.2f}% {result_rk3['mass_error']:>10.6f}% {result_euler['error']-result_rk3['error']:>+7.2f}%")
    print()
    print(f"{'Euler (nx=1001,dt=0.05)':<25} {result_euler_fine['error']:>10.2f}% {result_euler_fine['mass_error']:>10.6f}% {result_euler['error']-result_euler_fine['error']:>+7.2f}%")
    print(f"{'RK2 (nx=1001,dt=0.05)':<25} {result_rk2_fine['error']:>10.2f}% {result_rk2_fine['mass_error']:>10.6f}% {result_euler['error']-result_rk2_fine['error']:>+7.2f}%")
    print(f"{'RK3 (nx=1001,dt=0.05)':<25} {result_rk3_fine['error']:>10.2f}% {result_rk3_fine['mass_error']:>10.6f}% {result_euler['error']-result_rk3_fine['error']:>+7.2f}%")
    
    # 绘图对比
    fig, axes = plt.subplots(1, 2, figsize=(16, 6))
    
    # 图1：水深剖面对比（标准配置）
    ax = axes[0]
    ax.plot(result_euler['x'], result_euler['h'], 'b-', linewidth=2, label='Euler', alpha=0.7)
    ax.plot(result_rk2['x'], result_rk2['h'], 'r--', linewidth=2, label='RK2')
    ax.plot(result_rk3['x'], result_rk3['h'], 'g-.', linewidth=2, label='RK3')
    
    # 解析解
    c = np.sqrt(9.81 * 10.0)
    x_wave_exact = 500.0 + 2 * c * 50.0
    ax.axvline(x_wave_exact, color='k', linestyle=':', linewidth=2, label=f'理论波前 ({x_wave_exact:.0f}m)')
    
    ax.set_xlabel('x (m)', fontsize=12)
    ax.set_ylabel('Water Depth (m)', fontsize=12)
    ax.set_title('Dam Break: RK vs Euler (nx=501)', fontsize=14, fontweight='bold')
    ax.legend()
    ax.grid(True, alpha=0.3)
    
    # 图2：误差对比
    ax = axes[1]
    methods = ['Euler\nstd', 'RK2\nstd', 'RK3\nstd', 'Euler\nfine', 'RK2\nfine', 'RK3\nfine']
    errors = [
        result_euler['error'],
        result_rk2['error'],
        result_rk3['error'],
        result_euler_fine['error'],
        result_rk2_fine['error'],
        result_rk3_fine['error']
    ]
    
    colors = ['blue', 'red', 'green', 'cyan', 'magenta', 'orange']
    bars = ax.bar(methods, errors, color=colors, alpha=0.7, edgecolor='black')
    
    # 添加数值标签
    for bar, err in zip(bars, errors):
        height = bar.get_height()
        ax.text(bar.get_x() + bar.get_width()/2., height,
                f'{err:.1f}%', ha='center', va='bottom', fontsize=10, fontweight='bold')
    
    ax.axhline(10, color='orange', linestyle='--', linewidth=2, label='优秀 (10%)')
    ax.axhline(5, color='green', linestyle='--', linewidth=2, label='商业软件 (5%)')
    ax.set_ylabel('波前位置误差 (%)', fontsize=12)
    ax.set_title('RK时间积分改进效果', fontsize=14, fontweight='bold')
    ax.legend()
    ax.grid(True, alpha=0.3, axis='y')
    
    plt.tight_layout()
    
    # 保存
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    fig_path = f'/workspace/validation_cases/results/rk_comparison_{timestamp}.png'
    plt.savefig(fig_path, dpi=150, bbox_inches='tight')
    print(f"\n 图表已保存: {fig_path}")
    plt.close()


if __name__ == '__main__':
    main()
