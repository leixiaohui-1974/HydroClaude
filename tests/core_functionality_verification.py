#!/usr/bin/env python3
"""
核心功能验证测试
Core Functionality Verification Test

快速验证HydroClaude核心功能是否正常工作
"""

import numpy as np
import sys
import os

sys.path.insert(0, '.')

from solvers.godunov_fvm_solver import GodunvFVMSolver


def test_well_balanced_stability():
    """测试Well-Balanced格式稳定性"""
    print("\n" + "="*70)
    print("Test 1: Well-Balanced Stability")
    print("="*70)

    # 创建带凸起的底高程
    L = 100.0
    n_cells = 100
    x = np.linspace(0.5, L-0.5, n_cells)

    z_b = np.zeros(n_cells)
    for i in range(n_cells):
        if 40 <= x[i] <= 60:
            z_b[i] = 2.0 * (1.0 - 2.0*abs(x[i]-50)/20.0)

    # 初始静水条件
    eta = 10.0
    h = eta - z_b
    Q = np.zeros(n_cells)

    # 创建求解器
    solver = GodunvFVMSolver(
        width=10.0,
        length=L,
        n_cells=n_cells,
        manning_n=0.03,
        z_b=z_b,
        cfl=0.5,
        order=1,
        well_balanced=True
    )

    bc_left = {'type': 'h', 'value': h[0]}
    bc_right = {'type': 'h', 'value': h[-1]}
    solver.initialize(h, Q, bc_left, bc_right)

    mass_init = solver._compute_total_mass()

    # 运行10秒
    t = 0
    step = 0
    max_disturbance = 0.0

    while t < 10.0:
        dt = solver.compute_dt()
        solver.step(dt)
        t += dt
        step += 1

        eta_current = solver.h + solver.z_b
        disturbance = np.max(np.abs(eta_current - eta))
        max_disturbance = max(max_disturbance, disturbance)

    mass_final = solver._compute_total_mass()
    mass_error = abs(mass_final - mass_init) / mass_init * 100

    print(f"\n结果:")
    print(f"  模拟时间: {t:.1f}s")
    print(f"  总步数: {step}")
    print(f"  最大扰动: {max_disturbance:.3f} m")
    print(f"  质量误差: {mass_error:.3f} %")

    # 判定
    if max_disturbance < 5.0 and mass_error < 10.0:
        print(f"  状态: ✅ PASS")
        return True
    else:
        print(f"  状态: ❌ FAIL")
        return False


def test_flood_routing():
    """测试洪水演进"""
    print("\n" + "="*70)
    print("Test 2: Flood Routing (1 hour)")
    print("="*70)

    # 河道参数
    L = 50000.0  # 50 km
    n_cells = 100
    S0 = 1.0 / 2000.0

    # 初始条件
    h_init = 3.0 * np.ones(n_cells)
    Q_init = 100.0 * np.ones(n_cells)

    # 创建求解器
    solver = GodunvFVMSolver(
        width=100.0,
        length=L,
        n_cells=n_cells,
        manning_n=0.03,
        slope=S0,
        cfl=0.5,
        order=1,
        well_balanced=True
    )

    # 上游流量边界（时变洪峰）
    def inflow_hydrograph(t):
        t_hours = t / 3600.0
        if t_hours < 2:
            return 100 + 250 * t_hours
        elif t_hours < 6:
            return 600 - 100 * (t_hours - 2)
        else:
            return 200

    bc_left = {'type': 'Q', 'value': 100.0}
    bc_right = {'type': 'h', 'value': 3.0}

    solver.initialize(h_init, Q_init, bc_left, bc_right)

    # 运行1小时
    T_end = 3600.0
    t = 0
    step = 0

    Q_upstream_max = 0
    Q_downstream_max = 0

    while t < T_end:
        dt = solver.compute_dt()

        # 更新上游边界
        Q_in = inflow_hydrograph(t)
        bc_left['value'] = Q_in

        solver.step(dt)
        t += dt
        step += 1

        Q_upstream_max = max(Q_upstream_max, solver.Q[0])
        Q_downstream_max = max(Q_downstream_max, solver.Q[-1])

    print(f"\n结果:")
    print(f"  模拟时间: {t/3600:.1f} hours")
    print(f"  总步数: {step}")
    print(f"  上游洪峰: {Q_upstream_max:.1f} m³/s")
    print(f"  下游洪峰: {Q_downstream_max:.1f} m³/s")

    # 检查NaN
    has_nan = np.any(np.isnan(solver.h)) or np.any(np.isnan(solver.Q))

    if not has_nan and step > 100:
        print(f"  状态: ✅ PASS")
        return True
    else:
        print(f"  状态: ❌ FAIL")
        return False


def test_dam_break():
    """测试溃坝模拟"""
    print("\n" + "="*70)
    print("Test 3: Dam Break")
    print("="*70)

    # 参数
    L = 200.0
    n_cells = 200

    # 初始条件：上游10m，下游1m
    h_init = np.zeros(n_cells)
    h_init[:n_cells//2] = 10.0
    h_init[n_cells//2:] = 1.0
    Q_init = np.zeros(n_cells)

    # 创建求解器
    solver = GodunvFVMSolver(
        width=10.0,
        length=L,
        n_cells=n_cells,
        manning_n=0.0,
        slope=0.0,
        cfl=0.5,
        order=1,
        well_balanced=False
    )

    bc_left = {'type': 'h', 'value': 10.0}
    bc_right = {'type': 'h', 'value': 1.0}

    solver.initialize(h_init, Q_init, bc_left, bc_right)

    mass_init = solver._compute_total_mass()

    # 运行10秒
    T_end = 10.0
    t = 0
    step = 0

    while t < T_end:
        dt = solver.compute_dt()
        solver.step(dt)
        t += dt
        step += 1

    mass_final = solver._compute_total_mass()
    mass_error = abs(mass_final - mass_init) / mass_init * 100

    print(f"\n结果:")
    print(f"  模拟时间: {t:.1f}s")
    print(f"  总步数: {step}")
    print(f"  h范围: [{np.min(solver.h):.2f}, {np.max(solver.h):.2f}] m")
    print(f"  质量误差: {mass_error:.3f} %")

    # 检查
    has_nan = np.any(np.isnan(solver.h)) or np.any(np.isnan(solver.Q))

    if not has_nan and mass_error < 5.0:
        print(f"  状态: ✅ PASS")
        return True
    else:
        print(f"  状态: ❌ FAIL")
        return False


def main():
    """运行所有测试"""
    print("\n" + "="*70)
    print("HydroClaude 核心功能验证测试")
    print("Core Functionality Verification")
    print("="*70)

    results = []

    try:
        results.append(("Well-Balanced Stability", test_well_balanced_stability()))
    except Exception as e:
        print(f"\n❌ Test 1 Error: {e}")
        results.append(("Well-Balanced Stability", False))

    try:
        results.append(("Flood Routing", test_flood_routing()))
    except Exception as e:
        print(f"\n❌ Test 2 Error: {e}")
        results.append(("Flood Routing", False))

    try:
        results.append(("Dam Break", test_dam_break()))
    except Exception as e:
        print(f"\n❌ Test 3 Error: {e}")
        results.append(("Dam Break", False))

    # 总结
    print("\n" + "="*70)
    print("测试总结 / Test Summary")
    print("="*70)

    passed = sum(1 for _, result in results if result)
    total = len(results)

    for name, result in results:
        status = "✅ PASS" if result else "❌ FAIL"
        print(f"  {name:<30} {status}")

    print(f"\n总计: {passed}/{total} 通过 ({passed/total*100:.0f}%)")

    if passed == total:
        print("\n✅ 所有核心功能测试通过！")
        return 0
    else:
        print(f"\n⚠️  {total-passed}个测试失败")
        return 1


if __name__ == '__main__':
    sys.exit(main())
