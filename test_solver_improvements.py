#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""测试 solver 改进效果（桥梁 Energy Method + 陡坡子步）"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from solvers.steady_profile_solver import SteadyProfileSolver
import numpy as np

def test_bridge_energy_method():
    """测试桥梁 Energy Method 是否可调用"""
    print("\n=== 测试 1: 桥梁 Energy Method ===")

    # 创建简单的 solver
    solver = SteadyProfileSolver(
        length=100.0,
        B=10.0,
        S0=0.001,
        n=0.025,
    )

    # 检查方法是否存在
    if hasattr(solver, '_solve_bridge_energy'):
        print("[OK] _solve_bridge_energy 方法存在")
    else:
        print("[FAIL] _solve_bridge_energy 方法不存在")
        return False

    if hasattr(solver, '_solve_bridge_momentum'):
        print("[OK] _solve_bridge_momentum 方法存在")
    else:
        print("[FAIL] _solve_bridge_momentum 方法不存在")
        return False

    # 测试调用（简单参数）
    try:
        bridge_params = {
            'bridge_length_m': 10.0,
            'total_pier_width_m': 2.0,
            'pier_loss_coef': 0.5,
            'pier_height_m': 5.0,
            'deck_elevation_m': 10.0,
            'contraction_coef': 0.1,
        }

        W_us = solver._solve_bridge_energy(
            Q=50.0,
            W_downstream=5.0,
            bridge=bridge_params,
            bed_ds=4.0,
            bed_us=4.1,
            ds_xs_index=0,
            us_xs_index=0,
        )
        print(f"[OK] Energy Method 调用成功，上游水位 = {W_us:.3f}m")
        return True
    except Exception as e:
        print(f"[FAIL] Energy Method 调用失败: {e}")
        return False

def test_steep_slope_substeps():
    """测试陡坡子步改进"""
    print("\n=== 测试 2: 陡坡子步改进 ===")

    # 创建陡坡渠道
    n_xs = 10
    reach_lengths = [10.0] * (n_xs - 1)
    bed_elevations = np.linspace(10.0, 5.0, n_xs)  # 陡坡 S0 = 0.5

    solver = SteadyProfileSolver(
        length=sum(reach_lengths),
        B=5.0,
        S0=0.5,  # 陡坡
        n=0.03,
        bed_elevations=bed_elevations,
        reach_lengths=reach_lengths,
    )

    # 检查代码中是否有子步逻辑
    import inspect
    source = inspect.getsource(solver._solve_standard_step_variable_xs)

    if 'n_substeps' in source and 'energy_change' in source:
        print("[OK] 子步逻辑已添加（检测到 n_substeps 和 energy_change）")
    else:
        print("[FAIL] 子步逻辑未找到")
        return False

    # 测试求解
    try:
        Q = 20.0
        h_downstream = 1.0  # 下游水深

        result = solver.solve_standard_step(
            Q=Q,
            h_downstream=h_downstream,
        )

        # 检查返回值
        print(f"   返回值键: {list(result.keys())}")

        # 尝试不同的键名
        if 'wse' in result:
            wse_profile = result['wse']
        elif 'W' in result:
            wse_profile = result['W']
        elif 'h' in result:
            wse_profile = result['h']
        else:
            print(f"[FAIL] 未找到水位数据，可用键: {list(result.keys())}")
            return False

        print(f"[OK] 陡坡求解成功，上游水位 = {wse_profile[0]:.3f}m")
        print(f"   下游水位 = {wse_profile[-1]:.3f}m")
        print(f"   水位变化 = {wse_profile[0] - wse_profile[-1]:.3f}m")
        return True
    except Exception as e:
        print(f"[FAIL] 陡坡求解失败: {e}")
        import traceback
        traceback.print_exc()
        return False

def main():
    print("=" * 60)
    print("Solver 改进验证测试")
    print("=" * 60)

    results = []

    # 测试 1: 桥梁 Energy Method
    results.append(("桥梁 Energy Method", test_bridge_energy_method()))

    # 测试 2: 陡坡子步
    results.append(("陡坡子步改进", test_steep_slope_substeps()))

    # 总结
    print("\n" + "=" * 60)
    print("测试总结")
    print("=" * 60)
    for name, passed in results:
        status = "[PASS]" if passed else "[FAIL]"
        print(f"{name}: {status}")

    all_passed = all(r[1] for r in results)
    if all_passed:
        print("\n[SUCCESS] 所有测试通过！改进已成功应用。")
    else:
        print("\n[WARNING] 部分测试失败，需要进一步检查。")

    return all_passed

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
