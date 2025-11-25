#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
MUSCL性能测试 - Dam Break

测试MUSCL二阶重构对Dam Break精度的改进
"""

import sys
import warnings
warnings.filterwarnings("ignore")
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



def run_dam_break(use_muscl=False, limiter='minmod', nx=501, dt=0.1, T=50.0):
    """
    运行Dam Break测试
    
    Args:
        use_muscl: 是否使用MUSCL
        limiter: MUSCL限制器类型
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
        use_muscl=use_muscl,
        muscl_limiter=limiter
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
    print("MUSCL性能测试 - Dam Break")
    print("="*80)
    
    # 测试1：默认配置
    print(f"\n{'='*80}")
    print("测试1: 默认配置（nx=501, dt=0.1s）")
    print(f"{'='*80}")
    
    print("\n运行一阶重构（原始）...")
    result_1st = run_dam_break(use_muscl=False, nx=501, dt=0.1, T=50.0)
    print(f"\n结果（一阶）:")
    print(f"  波前位置: {result_1st['x_wave']:.2f}m (精确: {result_1st['x_wave_exact']:.2f}m)")
    print(f"  波前误差: {result_1st['error']:.2f}%")
    print(f"  质量误差: {result_1st['mass_error']:.6f}%")
    
    print("\n运行MUSCL-minmod...")
    result_muscl_minmod = run_dam_break(use_muscl=True, limiter='minmod', nx=501, dt=0.1, T=50.0)
    print(f"\n结果（MUSCL-minmod）:")
    print(f"  波前位置: {result_muscl_minmod['x_wave']:.2f}m")
    print(f"  波前误差: {result_muscl_minmod['error']:.2f}%")
    print(f"  质量误差: {result_muscl_minmod['mass_error']:.6f}%")
    print(f"  改进: {result_1st['error'] - result_muscl_minmod['error']:.2f}%")
    
    print("\n运行MUSCL-van_leer...")
    result_muscl_vl = run_dam_break(use_muscl=True, limiter='van_leer', nx=501, dt=0.1, T=50.0)
    print(f"\n结果（MUSCL-van_leer）:")
    print(f"  波前位置: {result_muscl_vl['x_wave']:.2f}m")
    print(f"  波前误差: {result_muscl_vl['error']:.2f}%")
    print(f"  质量误差: {result_muscl_vl['mass_error']:.6f}%")
    print(f"  改进: {result_1st['error'] - result_muscl_vl['error']:.2f}%")
    
    print("\n运行MUSCL-superbee...")
    result_muscl_sb = run_dam_break(use_muscl=True, limiter='superbee', nx=501, dt=0.1, T=50.0)
    print(f"\n结果（MUSCL-superbee）:")
    print(f"  波前位置: {result_muscl_sb['x_wave']:.2f}m")
    print(f"  波前误差: {result_muscl_sb['error']:.2f}%")
    print(f"  质量误差: {result_muscl_sb['mass_error']:.6f}%")
    print(f"  改进: {result_1st['error'] - result_muscl_sb['error']:.2f}%")
    
    # 测试2：更小的时间步长
    print(f"\n{'='*80}")
    print("测试2: 更小时间步长（nx=501, dt=0.05s）")
    print(f"{'='*80}")
    
    print("\n运行一阶重构...")
    result_1st_dt05 = run_dam_break(use_muscl=False, nx=501, dt=0.05, T=50.0)
    print(f"\n结果（一阶）:")
    print(f"  波前误差: {result_1st_dt05['error']:.2f}%")
    print(f"  质量误差: {result_1st_dt05['mass_error']:.6f}%")
    
    print("\n运行MUSCL-minmod...")
    result_muscl_dt05 = run_dam_break(use_muscl=True, limiter='minmod', nx=501, dt=0.05, T=50.0)
    print(f"\n结果（MUSCL-minmod）:")
    print(f"  波前误差: {result_muscl_dt05['error']:.2f}%")
    print(f"  质量误差: {result_muscl_dt05['mass_error']:.6f}%")
    print(f"  改进: {result_1st_dt05['error'] - result_muscl_dt05['error']:.2f}%")
    
    # 总结
    print(f"\n{'='*80}")
    print("总结")
    print(f"{'='*80}")
    
    print(f"\n{'配置':<25} {'波前误差':<12} {'质量误差':<12} {'vs一阶'}")
    print("-"*80)
    print(f"{'一阶(nx=501,dt=0.1)':<25} {result_1st['error']:>10.2f}% {result_1st['mass_error']:>10.6f}% {'基准'}")
    print(f"{'MUSCL-minmod':<25} {result_muscl_minmod['error']:>10.2f}% {result_muscl_minmod['mass_error']:>10.6f}% {result_1st['error']-result_muscl_minmod['error']:>+7.2f}%")
    print(f"{'MUSCL-van_leer':<25} {result_muscl_vl['error']:>10.2f}% {result_muscl_vl['mass_error']:>10.6f}% {result_1st['error']-result_muscl_vl['error']:>+7.2f}%")
    print(f"{'MUSCL-superbee':<25} {result_muscl_sb['error']:>10.2f}% {result_muscl_sb['mass_error']:>10.6f}% {result_1st['error']-result_muscl_sb['error']:>+7.2f}%")
    print(f"{'一阶(nx=501,dt=0.05)':<25} {result_1st_dt05['error']:>10.2f}% {result_1st_dt05['mass_error']:>10.6f}% {result_1st['error']-result_1st_dt05['error']:>+7.2f}%")
    print(f"{'MUSCL-minmod(dt=0.05)':<25} {result_muscl_dt05['error']:>10.2f}% {result_muscl_dt05['mass_error']:>10.6f}% {result_1st['error']-result_muscl_dt05['error']:>+7.2f}%")
    
    # 绘图对比
    fig, axes = plt.subplots(1, 2, figsize=(16, 6))
    
    # 图1：水深剖面对比
    ax = axes[0]
    ax.plot(result_1st['x'], result_1st['h'], 'b-', linewidth=2, label='一阶重构', alpha=0.7)
    ax.plot(result_muscl_minmod['x'], result_muscl_minmod['h'], 'r--', linewidth=2, label='MUSCL-minmod')
    ax.plot(result_muscl_vl['x'], result_muscl_vl['h'], 'g-.', linewidth=1.5, label='MUSCL-van_leer')
    
    # 解析解（简化）
    c = np.sqrt(9.81 * 10.0)
    x_wave_exact = 500.0 + 2 * c * 50.0
    ax.axvline(x_wave_exact, color='k', linestyle=':', linewidth=2, label=f'理论波前 ({x_wave_exact:.0f}m)')
    
    ax.set_xlabel('x (m)', fontsize=12)
    ax.set_ylabel('Water Depth (m)', fontsize=12)
    ax.set_title('Dam Break: MUSCL vs 一阶重构', fontsize=14, fontweight='bold')
    ax.legend()
    ax.grid(True, alpha=0.3)
    
    # 图2：误差对比
    ax = axes[1]
    methods = ['一阶', 'MUSCL\nminmod', 'MUSCL\nvan_leer', 'MUSCL\nsuperbee', '一阶\ndt=0.05', 'MUSCL\ndt=0.05']
    errors = [
        result_1st['error'],
        result_muscl_minmod['error'],
        result_muscl_vl['error'],
        result_muscl_sb['error'],
        result_1st_dt05['error'],
        result_muscl_dt05['error']
    ]
    
    colors = ['blue', 'red', 'green', 'orange', 'cyan', 'magenta']
    bars = ax.bar(methods, errors, color=colors, alpha=0.7, edgecolor='black')
    
    # 添加数值标签
    for bar, err in zip(bars, errors):
        height = bar.get_height()
        ax.text(bar.get_x() + bar.get_width()/2., height,
                f'{err:.1f}%', ha='center', va='bottom', fontsize=10, fontweight='bold')
    
    ax.axhline(5, color='red', linestyle='--', linewidth=2, label='目标 (5%)')
    ax.set_ylabel('波前位置误差 (%)', fontsize=12)
    ax.set_title('MUSCL改进效果对比', fontsize=14, fontweight='bold')
    ax.legend()
    ax.grid(True, alpha=0.3, axis='y')
    
    plt.tight_layout()
    
    # 保存
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    fig_path = f'/workspace/validation_cases/results/muscl_comparison_{timestamp}.png'
    plt.savefig(fig_path, dpi=150, bbox_inches='tight')
    print(f"\n 图表已保存: {fig_path}")
    plt.close()


if __name__ == '__main__':
    main()
