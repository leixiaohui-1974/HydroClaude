#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
MUSCL + 正确CFL测试

重新测试MUSCL，使用正确的CFL条件
"""

import sys
sys.path.insert(0, '/workspace')

import numpy as np
import matplotlib.pyplot as plt
from datetime import datetime

from solvers.hydrostatic_canal_solver import HydrostaticCanalSolver


def compute_cfl_timestep(solver, cfl_target=0.4):
    """
    计算满足CFL条件的最大时间步长
    
    Args:
        solver: 求解器
        cfl_target: 目标CFL数
    
    Returns:
        dt_max: 最大时间步长
    """
    # 计算每个单元的波速
    c = np.sqrt(solver.g * np.maximum(solver.h, solver.eps_dry))
    
    # 计算流速
    u = np.zeros_like(solver.h)
    mask = solver.h > solver.eps_dry
    u[mask] = solver.hu[mask] / solver.h[mask]
    
    # 最大特征波速
    lambda_max = np.max(np.abs(u) + c)
    
    if lambda_max > 0:
        dt_max = cfl_target * solver.dx / lambda_max
    else:
        dt_max = 0.1  # fallback
    
    return dt_max, lambda_max


def run_dam_break(
    integrator='rk2', 
    use_muscl=False, 
    limiter='minmod',
    nx=501, 
    cfl_target=0.4, 
    T=50.0
):
    """
    运行Dam Break测试（自适应时间步长）
    
    Args:
        integrator: 时间积分方法
        use_muscl: 是否使用MUSCL
        limiter: MUSCL限制器
        nx: 空间分辨率
        cfl_target: 目标CFL数
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
        time_integrator=integrator,
        use_muscl=use_muscl,
        muscl_limiter=limiter
    )
    
    # 初始条件
    solver.h = np.where(solver.x < x_dam, h_L, h_R)
    solver.hu = np.zeros(nx)
    
    # 时间步进（自适应）
    t = 0.0
    step = 0
    dt_history = []
    
    print(f"  开始时间步进 (target CFL={cfl_target})...")
    
    while t < T:
        # 计算自适应时间步长
        dt, lambda_max = compute_cfl_timestep(solver, cfl_target)
        dt = min(dt, T - t)  # 不超过总时间
        
        # 时间步进
        h_new, hu_new = solver.step_explicit(dt)
        solver.h = h_new
        solver.hu = hu_new
        
        t += dt
        step += 1
        dt_history.append(dt)
        
        if step % 100 == 0:
            print(f"  Step {step}, t={t:.2f}s, dt={dt:.4f}s, lambda_max={lambda_max:.2f}, h_max={np.max(solver.h):.3f}m")
    
    print(f"  完成！总步数：{step}, 平均dt={np.mean(dt_history):.4f}s")
    
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
        'x': solver.x.copy(),
        'n_steps': step,
        'avg_dt': np.mean(dt_history)
    }


def main():
    """主函数"""
    print("="*80)
    print("MUSCL + 正确CFL测试")
    print("="*80)
    
    # Baseline: 一阶 + Euler + CFL=0.9（固定dt=0.1）
    print(f"\n{'='*80}")
    print("Baseline: 一阶 + Euler (固定dt=0.1, CFL~0.9)")
    print(f"{'='*80}")
    L = 1000.0
    nx = 501
    dx = L / (nx - 1)
    g = 9.81
    c = np.sqrt(g * 10.0)
    dt_fixed = 0.1
    cfl_baseline = dt_fixed * c / dx
    print(f"  理论CFL = {cfl_baseline:.2f}")
    
    # 运行baseline（固定dt）
    solver_baseline = HydrostaticCanalSolver(
        length=L, nx=nx, B=1.0, S0=0.0, n=0.0, g=g,
        time_integrator='euler', use_muscl=False
    )
    solver_baseline.h = np.where(solver_baseline.x < 500.0, 10.0, 0.01)
    solver_baseline.hu = np.zeros(nx)
    
    t = 0.0
    T = 50.0
    n_steps = int(T / dt_fixed)
    for step in range(n_steps):
        solver_baseline.step_explicit(dt_fixed)
        t += dt_fixed
    
    x_wave_baseline = solver_baseline.x[np.where(solver_baseline.h > 0.1)[0][-1]]
    x_wave_exact = 500.0 + 2 * c * T
    error_baseline = abs(x_wave_baseline - x_wave_exact) / x_wave_exact * 100
    mass_baseline = np.sum(solver_baseline.h * dx)
    mass_error_baseline = abs(mass_baseline - 10.0 * 500.0) / (10.0 * 500.0) * 100
    
    print(f"\n结果:")
    print(f"  波前位置: {x_wave_baseline:.2f}m (精确: {x_wave_exact:.2f}m)")
    print(f"  波前误差: {error_baseline:.2f}%")
    print(f"  质量误差: {mass_error_baseline:.6f}%")
    
    # 测试1：一阶 + RK2 + CFL=0.4
    print(f"\n{'='*80}")
    print("测试1: 一阶 + RK2 + 自适应CFL=0.4")
    print(f"{'='*80}")
    result_1st_rk2 = run_dam_break(
        integrator='rk2', use_muscl=False, nx=501, cfl_target=0.4, T=50.0
    )
    print(f"\n结果:")
    print(f"  波前误差: {result_1st_rk2['error']:.2f}%")
    print(f"  质量误差: {result_1st_rk2['mass_error']:.6f}%")
    print(f"  vs Baseline: {error_baseline - result_1st_rk2['error']:+.2f}%")
    
    # 测试2：MUSCL + Euler + CFL=0.4
    print(f"\n{'='*80}")
    print("测试2: MUSCL-minmod + Euler + 自适应CFL=0.4")
    print(f"{'='*80}")
    result_muscl_euler = run_dam_break(
        integrator='euler', use_muscl=True, limiter='minmod',
        nx=501, cfl_target=0.4, T=50.0
    )
    print(f"\n结果:")
    print(f"  波前误差: {result_muscl_euler['error']:.2f}%")
    print(f"  质量误差: {result_muscl_euler['mass_error']:.6f}%")
    print(f"  vs Baseline: {error_baseline - result_muscl_euler['error']:+.2f}%")
    
    # 测试3：MUSCL + RK2 + CFL=0.4 ⭐ 关键测试
    print(f"\n{'='*80}")
    print("测试3: MUSCL-minmod + RK2 + 自适应CFL=0.4 ⭐")
    print(f"{'='*80}")
    result_muscl_rk2 = run_dam_break(
        integrator='rk2', use_muscl=True, limiter='minmod',
        nx=501, cfl_target=0.4, T=50.0
    )
    print(f"\n结果:")
    print(f"  波前误差: {result_muscl_rk2['error']:.2f}%")
    print(f"  质量误差: {result_muscl_rk2['mass_error']:.6f}%")
    print(f"  vs Baseline: {error_baseline - result_muscl_rk2['error']:+.2f}%")
    
    # 测试4：MUSCL + RK3 + CFL=0.4
    print(f"\n{'='*80}")
    print("测试4: MUSCL-minmod + RK3 + 自适应CFL=0.4")
    print(f"{'='*80}")
    result_muscl_rk3 = run_dam_break(
        integrator='rk3', use_muscl=True, limiter='minmod',
        nx=501, cfl_target=0.4, T=50.0
    )
    print(f"\n结果:")
    print(f"  波前误差: {result_muscl_rk3['error']:.2f}%")
    print(f"  质量误差: {result_muscl_rk3['mass_error']:.6f}%")
    print(f"  vs Baseline: {error_baseline - result_muscl_rk3['error']:+.2f}%")
    
    # 总结
    print(f"\n{'='*80}")
    print("总结")
    print(f"{'='*80}")
    
    print(f"\n{'配置':<30} {'波前误差':<12} {'质量误差':<12} {'vs Baseline'}")
    print("-"*85)
    print(f"{'Baseline (1st+Euler,CFL~0.9)':<30} {error_baseline:>10.2f}% {mass_error_baseline:>10.6f}% {'基准'}")
    print(f"{'一阶+RK2+CFL=0.4':<30} {result_1st_rk2['error']:>10.2f}% {result_1st_rk2['mass_error']:>10.6f}% {error_baseline-result_1st_rk2['error']:>+7.2f}%")
    print(f"{'MUSCL+Euler+CFL=0.4':<30} {result_muscl_euler['error']:>10.2f}% {result_muscl_euler['mass_error']:>10.6f}% {error_baseline-result_muscl_euler['error']:>+7.2f}%")
    print(f"{'MUSCL+RK2+CFL=0.4 ⭐':<30} {result_muscl_rk2['error']:>10.2f}% {result_muscl_rk2['mass_error']:>10.6f}% {error_baseline-result_muscl_rk2['error']:>+7.2f}%")
    print(f"{'MUSCL+RK3+CFL=0.4':<30} {result_muscl_rk3['error']:>10.2f}% {result_muscl_rk3['mass_error']:>10.6f}% {error_baseline-result_muscl_rk3['error']:>+7.2f}%")
    
    # 绘图
    fig, axes = plt.subplots(1, 2, figsize=(16, 6))
    
    # 图1：水深剖面对比
    ax = axes[0]
    ax.plot(solver_baseline.x, solver_baseline.h, 'b-', linewidth=2, label='Baseline (1st+Euler)', alpha=0.7)
    ax.plot(result_muscl_euler['x'], result_muscl_euler['h'], 'r--', linewidth=2, label='MUSCL+Euler')
    ax.plot(result_muscl_rk2['x'], result_muscl_rk2['h'], 'g-.', linewidth=2, label='MUSCL+RK2')
    ax.plot(result_muscl_rk3['x'], result_muscl_rk3['h'], 'm:', linewidth=2, label='MUSCL+RK3')
    
    ax.axvline(x_wave_exact, color='k', linestyle=':', linewidth=2, label=f'理论波前 ({x_wave_exact:.0f}m)')
    
    ax.set_xlabel('x (m)', fontsize=12)
    ax.set_ylabel('Water Depth (m)', fontsize=12)
    ax.set_title('Dam Break: MUSCL + 正确CFL', fontsize=14, fontweight='bold')
    ax.legend()
    ax.grid(True, alpha=0.3)
    
    # 图2：误差对比
    ax = axes[1]
    methods = ['Baseline\nCFL~0.9', '一阶+RK2\nCFL=0.4', 'MUSCL+Euler\nCFL=0.4', 'MUSCL+RK2\nCFL=0.4', 'MUSCL+RK3\nCFL=0.4']
    errors = [
        error_baseline,
        result_1st_rk2['error'],
        result_muscl_euler['error'],
        result_muscl_rk2['error'],
        result_muscl_rk3['error']
    ]
    
    colors = ['blue', 'cyan', 'red', 'green', 'magenta']
    bars = ax.bar(methods, errors, color=colors, alpha=0.7, edgecolor='black')
    
    for bar, err in zip(bars, errors):
        height = bar.get_height()
        ax.text(bar.get_x() + bar.get_width()/2., height,
                f'{err:.1f}%', ha='center', va='bottom', fontsize=10, fontweight='bold')
    
    ax.axhline(20, color='orange', linestyle='--', linewidth=2, label='良好 (20%)')
    ax.axhline(10, color='green', linestyle='--', linewidth=2, label='优秀 (10%)')
    ax.axhline(5, color='darkgreen', linestyle='--', linewidth=2, label='商业软件 (5%)')
    ax.set_ylabel('波前位置误差 (%)', fontsize=12)
    ax.set_title('CFL条件对精度的影响', fontsize=14, fontweight='bold')
    ax.legend()
    ax.grid(True, alpha=0.3, axis='y')
    
    plt.tight_layout()
    
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    fig_path = f'/workspace/validation_cases/results/muscl_correct_cfl_{timestamp}.png'
    plt.savefig(fig_path, dpi=150, bbox_inches='tight')
    print(f"\n✅ 图表已保存: {fig_path}")
    plt.close()


if __name__ == '__main__':
    main()
