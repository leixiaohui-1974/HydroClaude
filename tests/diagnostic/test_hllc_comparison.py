#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
HLL vs HLLC性能对比测试

测试不同参数配置下HLL和HLLC的性能差异
"""

import sys
import warnings
warnings.filterwarnings("ignore")
import os
sys.path.insert(0, '/workspace')

import numpy as np
import time

import pytest
try:
    from solvers.hydrostatic_canal_solver import HydrostaticCanalSolver
except ImportError as e:
    pytest.skip(f"Required module not available: {e}", allow_module_level=True)



def run_dam_break_test(solver_type='hllc', nx=501, dt=0.1, T=50.0):
    """
    运行Dam Break测试
    
    Args:
        solver_type: 'hll' or 'hllc'
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
        g=g
    )
    
    # 初始条件（溃坝）
    solver.h = np.where(solver.x < x_dam, h_L, h_R)
    solver.hu = np.zeros(nx)
    
    # 时间步进
    t = 0.0
    n_steps = int(T / dt)
    
    # 临时替换flux函数
    if solver_type == 'hll':
        solver.hllc_flux, original_hllc = solver.hll_flux, solver.hllc_flux
    
    start_time = time.time()
    
    for step in range(n_steps):
        h_new, hu_new = solver.step_explicit(dt)
        solver.h = h_new
        solver.hu = hu_new
        t += dt
    
    elapsed_time = time.time() - start_time
    
    # 恢复原始函数
    if solver_type == 'hll':
        solver.hllc_flux = original_hllc
    
    # 计算波前位置
    threshold = 0.1  # 水深阈值
    wavefront_indices = np.where(solver.h > threshold)[0]
    if len(wavefront_indices) > 0:
        x_wave = solver.x[wavefront_indices[-1]]
    else:
        x_wave = 0.0
    
    # 解析解波前
    c = np.sqrt(g * h_L)
    x_wave_exact = x_dam + 2 * c * T
    
    # 误差
    error = abs(x_wave - x_wave_exact) / x_wave_exact * 100
    
    return {
        'x_wave': x_wave,
        'x_wave_exact': x_wave_exact,
        'error': error,
        'time': elapsed_time,
        'h_final': solver.h.copy(),
        'x': solver.x.copy()
    }


def main():
    """主函数"""
    print("="*70)
    print("HLL vs HLLC 性能对比测试")
    print("="*70)
    
    # 测试配置
    configs = [
        {'name': '默认配置', 'nx': 501, 'dt': 0.1, 'T': 50.0},
        {'name': '更高分辨率', 'nx': 1001, 'dt': 0.1, 'T': 50.0},
        {'name': '更小时间步', 'nx': 501, 'dt': 0.05, 'T': 50.0},
        {'name': '最优配置', 'nx': 1001, 'dt': 0.01, 'T': 50.0},
    ]
    
    results = []
    
    for config in configs:
        print(f"\n{'='*70}")
        print(f"测试配置: {config['name']}")
        print(f"  nx={config['nx']}, dt={config['dt']}s, T={config['T']}s")
        print(f"{'='*70}")
        
        # 测试HLL
        print("\n  运行HLL...")
        result_hll = run_dam_break_test(
            solver_type='hll',
            nx=config['nx'],
            dt=config['dt'],
            T=config['T']
        )
        print(f"    波前位置: {result_hll['x_wave']:.2f}m (精确: {result_hll['x_wave_exact']:.2f}m)")
        print(f"    误差: {result_hll['error']:.2f}%")
        print(f"    耗时: {result_hll['time']:.2f}s")
        
        # 测试HLLC
        print("\n  运行HLLC...")
        result_hllc = run_dam_break_test(
            solver_type='hllc',
            nx=config['nx'],
            dt=config['dt'],
            T=config['T']
        )
        print(f"    波前位置: {result_hllc['x_wave']:.2f}m (精确: {result_hllc['x_wave_exact']:.2f}m)")
        print(f"    误差: {result_hllc['error']:.2f}%")
        print(f"    耗时: {result_hllc['time']:.2f}s")
        
        # 对比
        print(f"\n  对比:")
        print(f"    误差改进: {result_hll['error']:.2f}% -> {result_hllc['error']:.2f}% (Δ={result_hll['error']-result_hllc['error']:.2f}%)")
        print(f"    耗时比: {result_hllc['time']/result_hll['time']:.2f}x")
        
        results.append({
            'config': config,
            'hll': result_hll,
            'hllc': result_hllc
        })
    
    # 总结
    print(f"\n{'='*70}")
    print("总结")
    print(f"{'='*70}")
    
    print(f"\n{'配置':<15} {'HLL误差':<12} {'HLLC误差':<12} {'改进':<10} {'最佳'}")
    print("-"*70)
    
    for r in results:
        config_name = r['config']['name']
        hll_err = r['hll']['error']
        hllc_err = r['hllc']['error']
        improvement = hll_err - hllc_err
        best = '' if hllc_err < hll_err else '️'
        print(f"{config_name:<15} {hll_err:>10.2f}% {hllc_err:>10.2f}% {improvement:>8.2f}% {best}")


if __name__ == '__main__':
    main()
