#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
测试优化的自适应网格参数

尝试更精细的网格参数以达到阶段1目标（0.1-0.5%精度）

作者: Claude
日期: 2025-10-23
"""

import sys
import os
import numpy as np

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

try:
    # DEPRECATED: Use HydrostaticCanalSolver instead
# from solvers.single_canal_solver import SingleCanalSolver
except ImportError as e:
    print(f"Import error: {e}")
    print("Make sure project root is in sys.path")
    sys.exit(1)

from solvers.gate import SluiceGate


def test_optimized_grid(dx_fine=2.0, refinement_radius=300.0, dx_coarse=40.0):
    """
    测试优化的网格参数

    Args:
        dx_fine: 精细区网格间距 (m)
        refinement_radius: 加密半径 (m)
        dx_coarse: 粗网格间距 (m)
    """

    print("=" * 80)
    print(f"测试优化网格参数")
    print("=" * 80)
    print(f"  精细区间距: {dx_fine} m")
    print(f"  加密半径: ±{refinement_radius} m")
    print(f"  粗网格间距: {dx_coarse} m")
    print()

    # 系统配置
    canal_length = 10000.0
    canal_width = 10.0
    bed_slope = 0.0005
    manning_n = 0.025
    Q_initial = 10.0

    # 创建三个闸门
    gate1 = SluiceGate(position=2500.0, width=canal_width, opening=4.5, Cd=0.6)
    gate2 = SluiceGate(position=5000.0, width=canal_width, opening=4.0, Cd=0.6)
    gate3 = SluiceGate(position=7500.0, width=canal_width, opening=5.0, Cd=0.6)

    # 自适应网格求解器
    solver = SingleCanalSolver(
        total_length=canal_length,
        structures=[gate1, gate2, gate3],
        nx_total=301,
        B=canal_width,
        S0=bed_slope,
        n=manning_n,
        use_adaptive_grid=True,
        refinement_radius=refinement_radius,
        dx_fine=dx_fine,
        dx_coarse=dx_coarse
    )

    solver.reset_with_steady_state(Q_initial)

    # 使用更长时间来确保充分收敛
    result = solver.solve_steady_state(
        Q_target=Q_initial,
        max_iterations=10000,  # 增加迭代次数
        convergence_tol=0.0001,  # 更严格的收敛标准
        check_interval=500,
        verbose=True
    )

    # 获取流量分布
    profile = solver.get_full_profile()
    Q = profile['Q']
    x = profile['x']

    # 计算误差
    Q_error = np.abs(Q - Q_initial) / Q_initial * 100
    max_error = np.max(Q_error)

    # 闸门位置的流量
    gate_flows = solver.get_gate_flows()

    print(f"\n结果:")
    print(f"  网格点数: {len(x)}")
    print(f"  最大相对误差: {max_error:.4f}%")
    print(f"  闸门1流量: {gate_flows[0]:.4f} m³/s (误差: {abs(gate_flows[0]-Q_initial)/Q_initial*100:.4f}%)")
    print(f"  闸门2流量: {gate_flows[1]:.4f} m³/s (误差: {abs(gate_flows[1]-Q_initial)/Q_initial*100:.4f}%)")
    print(f"  闸门3流量: {gate_flows[2]:.4f} m³/s (误差: {abs(gate_flows[2]-Q_initial)/Q_initial*100:.4f}%)")

    # 判断是否达到目标
    print(f"\n阶段1目标检验:")
    print(f"  目标: 0.1-0.5% 精度")
    print(f"  当前误差: {max_error:.4f}%")
    if max_error < 0.5:
        print(f"   达到阶段1目标！")
        return True, max_error
    elif max_error < 1.0:
        print(f"  ◐ 接近阶段1目标")
        return False, max_error
    else:
        print(f"   未达到阶段1目标")
        return False, max_error


if __name__ == "__main__":
    print("\n" + "=" * 80)
    print("自适应网格参数优化测试")
    print("=" * 80)
    print()

    # 测试多组参数（只测试最精细的以节省时间）
    test_cases = [
        {"dx_fine": 2.0, "refinement_radius": 300.0, "dx_coarse": 40.0, "name": "超精细网格"},
        # {"dx_fine": 3.0, "refinement_radius": 250.0, "dx_coarse": 35.0, "name": "精细网格"},
        # {"dx_fine": 5.0, "refinement_radius": 200.0, "dx_coarse": 33.0, "name": "标准网格（基准）"},
    ]

    results = []

    for i, case in enumerate(test_cases):
        print(f"\n{'='*80}")
        print(f"测试{i+1}/{len(test_cases)}: {case['name']}")
        print(f"{'='*80}\n")

        success, error = test_optimized_grid(
            dx_fine=case["dx_fine"],
            refinement_radius=case["refinement_radius"],
            dx_coarse=case["dx_coarse"]
        )

        results.append({
            "name": case["name"],
            "dx_fine": case["dx_fine"],
            "radius": case["refinement_radius"],
            "error": error,
            "success": success
        })

        print("\n")

    # 总结
    print("\n" + "=" * 80)
    print("测试总结")
    print("=" * 80)
    print()
    print(f"{'配置':<20} | dx_fine | 半径 | 误差(%) | 状态")
    print("-" * 70)

    for r in results:
        status = " 达标" if r["success"] else " 未达标"
        print(f"{r['name']:<20} | {r['dx_fine']:6.1f}m | {r['radius']:4.0f}m | {r['error']:7.4f} | {status}")

    print()

    # 找出最佳配置
    best = min(results, key=lambda x: x["error"])
    print(f"最佳配置: {best['name']}")
    print(f"  精细度: dx={best['dx_fine']}m, 半径={best['radius']}m")
    print(f"  误差: {best['error']:.4f}%")
    print(f"  {'达到' if best['success'] else '未达到'}阶段1目标（0.1-0.5%）")
    print()
