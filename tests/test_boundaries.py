#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
测试边界条件类

验证GateBoundary, ValveBoundary, PumpBoundary的基本功能
"""

import sys, os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import numpy as np
from physics.boundaries import GateBoundary, ValveBoundary, PumpBoundary

def test_gate_boundary():
    """测试闸门边界条件"""
    print("测试 GateBoundary...")

    # 创建闸门边界条件
    gate_bc = GateBoundary(width=10.0, Cd=0.6, opening=0.5)

    assert gate_bc.width == 10.0
    assert gate_bc.Cd == 0.6
    assert gate_bc.opening == 0.5

    # 测试apply方法
    h, Q = gate_bc.apply(
        None,
        h_upstream=5.0,
        Q_upstream=10.0,
        h_downstream=4.0,
        Q_downstream=9.8
    )

    assert isinstance(h, (float, np.ndarray))
    assert isinstance(Q, (float, np.ndarray))

    print(f"  闸门边界计算: h={h:.2f}, Q={Q:.2f}")
    print("  ✓ GateBoundary test passed")

def test_valve_boundary():
    """测试阀门边界条件"""
    print("\n测试 ValveBoundary...")

    # 创建阀门边界条件
    valve_bc = ValveBoundary(Cv=0.8, opening=0.8, diameter=0.5)

    assert valve_bc.Cv == 0.8
    assert valve_bc.opening == 0.8
    assert valve_bc.diameter == 0.5

    # 测试apply方法
    H, Q = valve_bc.apply(
        None,
        H_upstream=40.0,
        Q_upstream=5.0,
        H_downstream=35.0,
        Q_downstream=4.9
    )

    assert isinstance(H, (float, np.ndarray))
    assert isinstance(Q, (float, np.ndarray))

    print(f"  阀门边界计算: H={H:.2f}, Q={Q:.2f}")
    print("  ✓ ValveBoundary test passed")

def test_pump_boundary():
    """测试泵边界条件"""
    print("\n测试 PumpBoundary...")

    # 创建泵边界条件（H = a*Q² + b*Q + c）
    pump_bc = PumpBoundary(a=-0.01, b=0.1, c=50.0)

    assert pump_bc.a == -0.01
    assert pump_bc.b == 0.1
    assert pump_bc.c == 50.0

    # 测试apply方法
    H, Q = pump_bc.apply(
        None,
        H_upstream=20.0,
        Q_upstream=5.0,
        H_downstream=60.0,
        Q_downstream=4.8
    )

    assert isinstance(H, (float, np.ndarray))
    assert isinstance(Q, (float, np.ndarray))

    print(f"  泵边界计算: H={H:.2f}, Q={Q:.2f}")
    print("  ✓ PumpBoundary test passed")

if __name__ == "__main__":
    print("="*80)
    print("边界条件测试")
    print("="*80)

    try:
        test_gate_boundary()
        test_valve_boundary()
        test_pump_boundary()

        print("\n" + "="*80)
        print("所有边界条件测试通过!")
        print("="*80)

    except Exception as e:
        print(f"\n✗ 测试失败: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
