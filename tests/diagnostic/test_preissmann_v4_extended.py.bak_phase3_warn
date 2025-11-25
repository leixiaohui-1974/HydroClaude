#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Preissmann v4.0 扩展测试
- Test 1: 静止水体（已通过）
- Test 2: 恒定流
- Test 3: 简单非恒定流
"""

import numpy as np
import sys
sys.path.insert(0, '/workspace')

from physics.numerical_methods.legacy_preissmann.preissmann_solver_v4_linear import PreissmannSolverV4Linear


def test_steady_flow():
    """Test 2: 恒定流"""
    print("\n" + "="*80)
    print("Test 2: 恒定流 - Q=10 m^3/s")
    print("="*80)
    
    solver = PreissmannSolverV4Linear(verbose=False, tolerance=1e-4)
    
    # 参数
    n_cells = 20
    length = 1000.0
    dx = length / n_cells
    width = 10.0
    manning_n = 0.025
    slope = 0.001
    dt = 30.0
    g = 9.81
    
    # 计算均匀流水深（Manning公式）
    Q_target = 10.0
    A = width * 2.0  # 初始猜测
    for _ in range(10):
        P = width + 2 * (A/width)
        R = A / P
        Q_manning = A * (R**(2/3)) * (slope**0.5) / manning_n
        if abs(Q_manning - Q_target) / Q_target < 0.01:
            break
        A += 0.1 * (Q_target - Q_manning) / width
    
    h_uniform = A / width
    print(f"  目标流量: {Q_target} m^3/s")
    print(f"  均匀流水深: {h_uniform:.3f} m")
    
    # 初始条件：均匀流
    h_init = np.ones(n_cells + 1) * h_uniform
    Q_init = np.ones(n_cells + 1) * Q_target
    
    # 边界条件：固定流量和水位
    bc = {
        'upstream_flow': Q_target,  # 注意：这个需要实现
        'downstream_level': h_uniform
    }
    
    # 临时：上下游都固定水位
    bc = {
        'upstream_level': h_uniform,
        'downstream_level': h_uniform
    }
    
    initial_mass = np.sum(h_init[:-1] * width * dx)
    
    h = h_init.copy()
    Q = Q_init.copy()
    
    print(f"\n时间推进 10步:")
    for step in range(10):
        h, Q = solver.solve_canal_step(
            h, Q, dt, dx, width, manning_n, slope, bc
        )
        
        if step % 3 == 0:
            current_mass = np.sum(h[:-1] * width * dx)
            mass_error = (current_mass - initial_mass) / initial_mass * 100
            Q_avg = np.mean(Q[1:-1])
            Q_error = abs(Q_avg - Q_target) / Q_target * 100
            
            print(f"  步骤 {step+1}: 质量误差={mass_error:.4f}%, "
                  f"Q_avg={Q_avg:.2f} (误差{Q_error:.2f}%)")
    
    # 最终结果
    current_mass = np.sum(h[:-1] * width * dx)
    mass_error = (current_mass - initial_mass) / initial_mass * 100
    Q_avg = np.mean(Q[1:-1])
    Q_error = abs(Q_avg - Q_target) / Q_target * 100
    
    print(f"\n最终结果:")
    print(f"  质量守恒: {mass_error:.6f}% {'' if abs(mass_error) < 0.5 else ''}")
    print(f"  流量误差: {Q_error:.2f}% {'' if Q_error < 5 else ''}")
    print(f"  收敛迭代: {solver.last_iterations}")


def test_dam_break_simple():
    """Test 3: 简单溃坝（非恒定流）"""
    print("\n" + "="*80)
    print("Test 3: 简化溃坝测试")
    print("="*80)
    
    solver = PreissmannSolverV4Linear(verbose=False, tolerance=1e-4)
    
    # 参数
    n_cells = 50
    length = 100.0  # 短渠道
    dx = length / n_cells
    width = 10.0
    manning_n = 0.01  # 小粗糙度
    slope = 0.0      # 水平渠道
    dt = 0.1         # 小时间步
    
    # 初始条件：阶跃
    h_init = np.ones(n_cells + 1) * 1.0
    h_init[:n_cells//2] = 5.0  # 上游5m，下游1m
    Q_init = np.zeros(n_cells + 1)
    
    # 边界条件：自由（暂用固定）
    bc = {
        'upstream_level': 5.0,
        'downstream_level': 1.0
    }
    
    initial_mass = np.sum(h_init[:-1] * width * dx)
    
    h = h_init.copy()
    Q = Q_init.copy()
    
    print(f"  初始质量: {initial_mass:.2f} m^3")
    print(f"  初始上游: {h[0]:.2f} m, 下游: {h[-1]:.2f} m")
    
    # 时间推进
    t_end = 5.0
    n_steps = int(t_end / dt)
    
    print(f"\n时间推进至 t={t_end}s (n_steps={n_steps}):")
    
    for step in range(n_steps):
        h, Q = solver.solve_canal_step(
            h, Q, dt, dx, width, manning_n, slope, bc
        )
        
        if np.any(np.isnan(h)) or np.any(np.isnan(Q)):
            print(f"   步骤{step+1}出现NaN")
            break
        
        if step % 10 == 0:
            current_mass = np.sum(h[:-1] * width * dx)
            mass_error = (current_mass - initial_mass) / initial_mass * 100
            print(f"  t={step*dt:5.2f}s: 质量误差={mass_error:.4f}%, "
                  f"max(Q)={np.max(np.abs(Q)):.2f}")
    
    # 最终结果
    current_mass = np.sum(h[:-1] * width * dx)
    mass_error = (current_mass - initial_mass) / initial_mass * 100
    
    print(f"\n最终结果:")
    print(f"  质量守恒: {mass_error:.6f}% {'' if abs(mass_error) < 2 else '️'}")
    print(f"  稳定性: {' 无NaN' if not np.any(np.isnan(h)) else ' 有NaN'}")


if __name__ == "__main__":
    print("="*80)
    print("Preissmann v4.0 扩展测试套件")
    print("="*80)
    
    # Test 2: 恒定流
    test_steady_flow()
    
    # Test 3: 简单溃坝
    test_dam_break_simple()
    
    print("\n" + "="*80)
    print("测试完成！")
    print("="*80)
