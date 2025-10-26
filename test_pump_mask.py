#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
测试泵站区域掩码是否正确工作
"""

import sys
import os
import numpy as np

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from solvers.hydrostatic_canal_solver import HydrostaticCanalSolver
from solvers.gate import PumpStation

def test_pump_mask():
    """测试泵站区域掩码"""
    
    # 创建一个简单的求解器
    length = 100000.0  # 100 km
    nx = 516  # 与实际配置相同
    pump_position = 50000.0  # 50 km
    
    # 创建泵站对象
    pump = PumpStation(position=pump_position, width=10.0, rated_flow=30.0, rated_head=5.0)
    
    # 创建求解器（在初始化时传递结构物）
    solver = HydrostaticCanalSolver(
        length=length,
        nx=nx,
        B=10.0,
        S0=0.0001,
        n=0.025,
        internal_structures=[(pump_position, pump)]
    )
    
    # 获取掩码
    pump_mask = solver._get_pump_region_mask()
    
    # 分析掩码
    print("=" * 90)
    print("泵站区域掩码分析")
    print("=" * 90)
    print(f"\n网格信息：")
    print(f"  总点数: {nx}")
    print(f"  渠道长度: {length/1000:.1f} km")
    print(f"  网格间距: {length/(nx-1):.1f} m")
    print(f"  泵站位置: {pump_position/1000:.1f} km")
    
    # 找到泵站索引
    pump_idx = np.argmin(np.abs(solver.x - pump_position))
    print(f"  泵站索引: {pump_idx}")
    print(f"  泵站实际位置: {solver.x[pump_idx]/1000:.3f} km")
    
    # 掩码统计
    mask_count = np.sum(pump_mask)
    mask_indices = np.where(pump_mask)[0]
    
    print(f"\n掩码信息：")
    print(f"  掩码点数: {mask_count}")
    
    if mask_count > 0:
        print(f"  掩码起始索引: {mask_indices[0]}")
        print(f"  掩码结束索引: {mask_indices[-1]}")
        print(f"  掩码起始位置: {solver.x[mask_indices[0]]/1000:.3f} km")
        print(f"  掩码结束位置: {solver.x[mask_indices[-1]]/1000:.3f} km")
        print(f"  掩码覆盖范围: {(solver.x[mask_indices[-1]] - solver.x[mask_indices[0]])/1000:.3f} km")
        
        print(f"\n掩码详细分布：")
        print(f"  {'索引':<8} {'位置(km)':<12} {'距泵站(km)':<15} {'区域'}")
        print("-" * 90)
        
        for idx in mask_indices:
            dist_to_pump = (solver.x[idx] - pump_position) / 1000
            
            if idx <= pump_idx - 2:
                region = "未知"
            elif idx <= pump_idx - 1:
                region = "上游过渡区"
            elif idx == pump_idx:
                region = "泵站中心"
            elif idx <= pump_idx + 10:
                region = "下游平台区"
            elif idx <= pump_idx + 12:
                region = "下游过渡区"
            else:
                region = "未知"
            
            print(f"  {idx:<8} {solver.x[idx]/1000:<12.3f} {dist_to_pump:<15.3f} {region}")
    else:
        print("  ✗ 掩码为空！泵站约束未被识别！")
    
    # 测试关键位置
    print(f"\n关键位置检查：")
    test_positions = [47.0, 48.0, 49.0, 50.0, 51.0, 52.0, 53.0]
    for pos_km in test_positions:
        pos_m = pos_km * 1000
        idx = np.argmin(np.abs(solver.x - pos_m))
        is_masked = pump_mask[idx]
        status = "✓ 在掩码内" if is_masked else "✗ 不在掩码内"
        print(f"  {pos_km:.1f} km (索引{idx}): {status}")
    
    print("\n" + "=" * 90)
    
    # 测试约束应用
    print("\n测试泵站约束应用...")
    print("=" * 90)
    
    # 初始化状态
    solver.h[:] = 2.0
    solver.hu[:] = 10.0 / 10.0  # Q=10 m³/s, B=10m
    
    print(f"\n应用约束前：")
    print(f"  泵站处水深: {solver.h[pump_idx]:.4f} m")
    if pump_idx + 2 < nx:
        print(f"  泵站后2km水深: {solver.h[pump_idx+10]:.4f} m")  # 约2km（10个点×200m）
    
    # 应用约束
    solver._apply_pump_region_constraints()
    
    print(f"\n应用约束后：")
    print(f"  泵站处水深: {solver.h[pump_idx]:.4f} m")
    if pump_idx + 10 < nx:
        print(f"  泵站后2km水深（平台区）: {solver.h[pump_idx+10]:.4f} m")
        expected_head = 2.0 + 5.0  # 上游2m + 扬程5m
        actual_head = solver.h[pump_idx+10]
        print(f"  预期水深: {expected_head:.4f} m")
        print(f"  实际扬程: {actual_head - 2.0:.4f} m")
        print(f"  精度: {(actual_head - 2.0) / 5.0 * 100:.1f}%")
    
    print("\n" + "=" * 90)

if __name__ == "__main__":
    test_pump_mask()
