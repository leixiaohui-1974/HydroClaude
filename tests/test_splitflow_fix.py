#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""测试 Split-Flow Method 修复效果"""

import sys
import os
import numpy as np

# 设置输出编码
if sys.platform == 'win32':
    import io
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8')

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from solvers.steady_profile_solver import SteadyProfileSolver


def test_compute_critical_slope():
    """测试临界坡度计算"""
    print("\n=== Test _compute_critical_slope ===")
    
    solver = SteadyProfileSolver(length=1000, B=10.0, S0=0.01, n=0.015)
    Q = 50.0
    
    # 计算临界坡度
    Sc = solver._compute_critical_slope(Q, 0)
    
    print(f"Q = {Q} m3/s")
    print(f"Critical slope Sc = {Sc:.6f}")
    
    # 验证：临界坡度应该是正数且合理
    assert Sc > 0, "Sc should be > 0"
    assert Sc < 1.0, "Sc should be < 1.0"
    
    print("PASS: Critical slope calculation correct")


def test_identify_steep_sections():
    """测试陡坡段识别"""
    print("\n=== Test _identify_steep_sections ===")
    
    # 创建混合坡度渠道
    n_xs = 10
    x = np.linspace(0, 900, n_xs)
    
    # 前 5 个断面：陡坡 (S = 0.01)
    # 后 5 个断面：缓坡 (S = 0.0004)
    bed = np.zeros(n_xs)
    for i in range(5):
        bed[i] = 100 - i * 10  # 陡坡段
    for i in range(5, n_xs):
        bed[i] = 50 - (i - 5) * 0.4  # 缓坡段
    
    solver = SteadyProfileSolver(length=900, B=10.0, S0=0.005, n=0.015)
    Q = 50.0
    
    # 识别陡坡段
    controls = solver._identify_steep_sections(Q, bed, x)
    
    print(f"Steep section start indices: {controls}")
    print(f"Bed elevations: {bed}")
    
    # 验证：应该识别到陡坡段
    assert len(controls) > 0, "Should identify at least one steep section"
    assert controls[0] < 5, "First steep section should be in first 5 XS"
    
    print("PASS: Steep section identification correct")


def test_supercritical_boundary_condition():
    """测试超临界边界条件（0.95 * y_c）"""
    print("\n=== Test supercritical boundary condition ===")
    
    solver = SteadyProfileSolver(length=1000, B=10.0, S0=0.01, n=0.015)
    Q = 50.0
    
    n_xs = 10
    x = np.linspace(0, 1000, n_xs)
    bed = np.linspace(100, 90, n_xs)
    
    # 计算临界深度
    y_c = np.array([solver._compute_critical_depth(Q, i) for i in range(n_xs)])
    
    # 计算超临界剖面
    control_idx = 0
    W_control = bed[control_idx] + y_c[control_idx]
    
    W_super = solver._compute_supercritical_profile(
        Q=Q,
        control_idx=control_idx,
        W_control=W_control,
        bed=bed,
        x=x,
        y_c=y_c,
        end_idx=n_xs-1
    )
    
    # 验证边界条件
    h_control = W_super[control_idx] - bed[control_idx]
    
    print(f"Critical depth y_c = {y_c[control_idx]:.3f} m")
    print(f"Control section depth h = {h_control:.3f} m")
    print(f"Ratio h/y_c = {h_control/y_c[control_idx]:.3f}")
    
    # 验证：控制断面水深应该约为 0.95 * y_c
    assert 0.90 < h_control/y_c[control_idx] < 1.0, "Control depth should be slightly below critical"
    
    print("PASS: Boundary condition correct (0.95 * y_c)")


def test_supercritical_no_upper_constraint():
    """测试超临界约束（无上限）"""
    print("\n=== Test supercritical constraint (no upper limit) ===")
    
    solver = SteadyProfileSolver(length=1000, B=10.0, S0=0.01, n=0.015)
    Q = 50.0
    
    n_xs = 10
    x = np.linspace(0, 1000, n_xs)
    bed = np.linspace(100, 90, n_xs)
    
    y_c = np.array([solver._compute_critical_depth(Q, i) for i in range(n_xs)])
    
    control_idx = 0
    W_control = bed[control_idx] + y_c[control_idx]
    
    W_super = solver._compute_supercritical_profile(
        Q=Q,
        control_idx=control_idx,
        W_control=W_control,
        bed=bed,
        x=x,
        y_c=y_c,
        end_idx=n_xs-1
    )
    
    # 计算水深和 Froude 数
    h_super = W_super - bed
    
    print(f"Supercritical depths: {h_super[:5]}")
    print(f"Critical depths: {y_c[:5]}")
    
    # 验证：超临界流应该有 h < y_c
    supercritical_count = np.sum(h_super < y_c)
    print(f"Supercritical XS count: {supercritical_count}/{n_xs}")
    
    # 至少应该有一些断面是超临界的
    assert supercritical_count > 0, "Should have supercritical XS (h < y_c)"
    
    print("PASS: Supercritical constraint correct (allows h < y_c)")


def test_locate_control_sections_with_new_signature():
    """测试 _locate_control_sections 新签名"""
    print("\n=== Test _locate_control_sections new signature ===")
    
    solver = SteadyProfileSolver(length=1000, B=10.0, S0=0.01, n=0.015)
    Q = 50.0
    
    n_xs = 10
    x = np.linspace(0, 1000, n_xs)
    bed = np.linspace(100, 90, n_xs)
    
    # 创建一个亚临界剖面
    W_subcritical = bed + 2.0  # 假设水深 2m
    
    y_c = np.array([solver._compute_critical_depth(Q, i) for i in range(n_xs)])
    
    # 调用新签名的方法
    controls = solver._locate_control_sections(W_subcritical, bed, y_c, Q, x)
    
    print(f"Control sections: {controls}")
    
    # 验证：方法应该正常运行（不报错）
    assert isinstance(controls, list), "Return value should be a list"
    
    print("PASS: New signature works correctly")


if __name__ == "__main__":
    print("=" * 60)
    print("Split-Flow Method Fix Validation Tests")
    print("=" * 60)
    
    try:
        test_compute_critical_slope()
        test_identify_steep_sections()
        test_supercritical_boundary_condition()
        test_supercritical_no_upper_constraint()
        test_locate_control_sections_with_new_signature()
        
        print("\n" + "=" * 60)
        print("ALL TESTS PASSED!")
        print("=" * 60)
        
    except Exception as e:
        print(f"\nTEST FAILED: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
