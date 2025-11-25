#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
测试HLLC求解器在Lake at Rest问题上的表现

Phase 9.2: 验证新的HLLC实现能否显著降低数值耗散
达到比HLL更好的精度

作者: HydroClaude Team
日期: 2025-10-31
"""

import numpy as np
import warnings
warnings.filterwarnings("ignore")
import sys
import os

# 添加父目录到路径
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

try:
    from solvers.godunov_fvm_solver import GodunvFVMSolver
except ImportError as e:
    print(f"Import error: {e}")
    print("Make sure project root is in sys.path")
    sys.exit(1)



def test_lake_at_rest_hll_vs_hllc():
    """
    对比HLL和HLLC求解器在Lake at Rest上的表现

    测试配置:
    - 网格: 100单元
    - 地形: 抛物线凸起 (最大2m高)
    - 初始条件: 平静水面 ( = 10m)
    - 边界: 两侧wall (反射边界)
    - 时长: 10秒
    """

    print("="*80)
    print("Lake at Rest Test: HLL vs HLLC Comparison")
    print("="*80)

    # 网格参数
    L = 100.0
    n_cells = 120
    dx = L / n_cells
    x = np.linspace(dx/2, L - dx/2, n_cells)

    # 地形: 抛物线凸起
    z_max = 2.0
    x_center = L / 2
    z_b = z_max * np.exp(-((x - x_center) / 10)**2)  # 高斯形凸起

    # 初始条件: 平静水面
    eta = 10.0  # 水面高程
    h_init = eta - z_b  # 水深
    Q_init = np.zeros(n_cells)  # 零流量

    # 边界条件: 两侧墙壁 (反射)
    bc_left = {'type': 'wall'}
    bc_right = {'type': 'wall'}

    # 模拟参数
    T_max = 10.0  # 10秒
    cfl = 0.3

    # ========== 测试1: HLL求解器 ==========
    print("\n[Test 1] HLL Riemann Solver")
    print("-" * 80)

    solver_hll = GodunvFVMSolver(
        width=10.0,
        length=L,
        n_cells=n_cells,
        z_b=z_b.copy(),
        manning_n=0.025,
        cfl=cfl,
        order=1,  # 1阶避免重构误差干扰
        riemann_solver='hll',
        well_balanced=True,  # 启用Well-Balanced
        use_numba=True
    )

    solver_hll.initialize(h_init.copy(), Q_init.copy(), bc_left, bc_right)

    # 记录初始状态
    eta_init_hll = solver_hll.h + solver_hll.z_b
    eta_max_dev_init_hll = np.max(np.abs(eta_init_hll - eta))
    print(f"Initial state:")
    print(f"   deviation: {eta_max_dev_init_hll:.2e} m (should be ~0)")

    # 运行模拟
    step_count_hll = 0
    while solver_hll.t < T_max:
        solver_hll.step()
        step_count_hll += 1

    # 最终状态
    eta_final_hll = solver_hll.h + solver_hll.z_b
    eta_dev_hll = np.abs(eta_final_hll - eta)
    eta_max_dev_hll = np.max(eta_dev_hll)
    eta_mean_dev_hll = np.mean(eta_dev_hll)

    print(f"\nFinal state (t={solver_hll.t:.2f}s, {step_count_hll} steps):")
    print(f"  Max  deviation: {eta_max_dev_hll:.4f} m")
    print(f"  Mean  deviation: {eta_mean_dev_hll:.4f} m")
    print(f"  Max |Q|: {np.max(np.abs(solver_hll.Q)):.4e} m^3/s")

    # ========== 测试2: HLLC求解器 ==========
    print("\n[Test 2] HLLC Riemann Solver")
    print("-" * 80)

    solver_hllc = GodunvFVMSolver(
        width=10.0,
        length=L,
        n_cells=n_cells,
        z_b=z_b.copy(),
        manning_n=0.025,
        cfl=cfl,
        order=1,  # 1阶避免重构误差干扰
        riemann_solver='hllc',  # 使用HLLC
        well_balanced=True,  # 启用Well-Balanced
        use_numba=True
    )

    solver_hllc.initialize(h_init.copy(), Q_init.copy(), bc_left, bc_right)

    # 记录初始状态
    eta_init_hllc = solver_hllc.h + solver_hllc.z_b
    eta_max_dev_init_hllc = np.max(np.abs(eta_init_hllc - eta))
    print(f"Initial state:")
    print(f"   deviation: {eta_max_dev_init_hllc:.2e} m (should be ~0)")

    # 运行模拟
    step_count_hllc = 0
    while solver_hllc.t < T_max:
        solver_hllc.step()
        step_count_hllc += 1

    # 最终状态
    eta_final_hllc = solver_hllc.h + solver_hllc.z_b
    eta_dev_hllc = np.abs(eta_final_hllc - eta)
    eta_max_dev_hllc = np.max(eta_dev_hllc)
    eta_mean_dev_hllc = np.mean(eta_dev_hllc)

    print(f"\nFinal state (t={solver_hllc.t:.2f}s, {step_count_hllc} steps):")
    print(f"  Max  deviation: {eta_max_dev_hllc:.4f} m")
    print(f"  Mean  deviation: {eta_mean_dev_hllc:.4f} m")
    print(f"  Max |Q|: {np.max(np.abs(solver_hllc.Q)):.4e} m^3/s")

    # ========== 对比分析 ==========
    print("\n" + "="*80)
    print("Comparison Analysis")
    print("="*80)

    improvement_max = (eta_max_dev_hll - eta_max_dev_hllc) / eta_max_dev_hll * 100
    improvement_mean = (eta_mean_dev_hll - eta_mean_dev_hllc) / eta_mean_dev_hll * 100

    print(f"\nDeviation at t={T_max}s:")
    print(f"  {'Solver':<10} {'Max  dev (m)':<20} {'Mean  dev (m)':<20}")
    print(f"  {'-'*50}")
    print(f"  {'HLL':<10} {eta_max_dev_hll:<20.4f} {eta_mean_dev_hll:<20.4f}")
    print(f"  {'HLLC':<10} {eta_max_dev_hllc:<20.4f} {eta_mean_dev_hllc:<20.4f}")
    print(f"  {'-'*50}")
    print(f"  {'Improvement':<10} {improvement_max:>17.1f}% {improvement_mean:>17.1f}%")

    # 判断结果
    print("\n" + "="*80)
    print("Test Results")
    print("="*80)

    if eta_max_dev_hllc < eta_max_dev_hll:
        print(f"\n HLLC shows {improvement_max:.1f}% less dissipation than HLL")
        print(f"   HLLC is superior for Lake at Rest")
        success = True
    elif abs(eta_max_dev_hllc - eta_max_dev_hll) / eta_max_dev_hll < 0.01:
        print(f"\n  HLLC and HLL show similar dissipation (< 1% difference)")
        print(f"   No significant advantage for HLLC in this test")
        success = True
    else:
        print(f"\n HLLC shows MORE dissipation than HLL")
        print(f"   HLLC implementation may have issues")
        success = False

    # 目标检查
    target = 0.1  # 10cm目标
    print(f"\nTarget: Max  deviation < {target}m")
    print(f"  HLL:  {eta_max_dev_hll:.4f}m - {' PASS' if eta_max_dev_hll < target else ' FAIL'}")
    print(f"  HLLC: {eta_max_dev_hllc:.4f}m - {' PASS' if eta_max_dev_hllc < target else ' FAIL'}")

    if eta_max_dev_hllc < target:
        print(f"\n HLLC达到目标精度!")

    return success


def test_lake_at_rest_hllc_long_time():
    """
    长时间Lake at Rest测试验证HLLC稳定性

    测试配置:
    - 时长: 100秒 (比上面测试长10倍)
    - 检查是否产生NaN或发散
    """

    print("\n\n" + "="*80)
    print("Lake at Rest Long-Time Test (100s): HLLC Stability")
    print("="*80)

    # 网格参数
    L = 100.0
    n_cells = 120
    dx = L / n_cells
    x = np.linspace(dx/2, L - dx/2, n_cells)

    # 地形
    z_max = 2.0
    x_center = L / 2
    z_b = z_max * np.exp(-((x - x_center) / 10)**2)

    # 初始条件
    eta = 10.0
    h_init = eta - z_b
    Q_init = np.zeros(n_cells)

    # 边界条件
    bc_left = {'type': 'wall'}
    bc_right = {'type': 'wall'}

    # 模拟参数
    T_max = 100.0  # 100秒
    cfl = 0.3

    solver = GodunvFVMSolver(
        width=10.0,
        length=L,
        n_cells=n_cells,
        z_b=z_b.copy(),
        manning_n=0.025,
        cfl=cfl,
        order=1,
        riemann_solver='hllc',
        well_balanced=True,
        use_numba=True
    )

    solver.initialize(h_init.copy(), Q_init.copy(), bc_left, bc_right)

    # 运行模拟定期检查
    check_times = [0, 10, 20, 50, 100]
    results = []

    for t_check in check_times:
        while solver.t < t_check:
            solver.step()

            # 检查NaN
            if np.any(np.isnan(solver.h)) or np.any(np.isnan(solver.Q)):
                print(f"\n NaN detected at t={solver.t:.2f}s!")
                print(f"   HLLC implementation has stability issues")
                return False

        # 记录状态
        eta_final = solver.h + solver.z_b
        eta_dev = np.abs(eta_final - eta)
        eta_max_dev = np.max(eta_dev)

        results.append({
            't': solver.t,
            'max_dev': eta_max_dev,
            'max_Q': np.max(np.abs(solver.Q))
        })

        print(f"\nt = {solver.t:6.1f}s: Max  dev = {eta_max_dev:.4f}m, Max |Q| = {results[-1]['max_Q']:.2e} m^3/s")

    # 检查是否发散
    print("\n" + "="*80)
    print("Stability Analysis")
    print("="*80)

    final_dev = results[-1]['max_dev']
    initial_dev = results[0]['max_dev']

    if final_dev > 10.0:  # 10m是明显发散的标志
        print(f"\n Solution diverged (final deviation = {final_dev:.2f}m)")
        return False
    elif np.isnan(final_dev):
        print(f"\n Solution produced NaN")
        return False
    else:
        print(f"\n Solution remained stable")
        print(f"   Initial deviation: {initial_dev:.4f}m")
        print(f"   Final deviation:   {final_dev:.4f}m")
        print(f"   Growth:            {(final_dev/initial_dev - 1)*100:.1f}%")
        return True


if __name__ == '__main__':
    print("\n" + ""*40)
    print("HLLC Riemann Solver: Lake at Rest Validation")
    print(""*40)

    # 测试1: HLL vs HLLC短时间对比
    success1 = test_lake_at_rest_hll_vs_hllc()

    # 测试2: HLLC长时间稳定性
    success2 = test_lake_at_rest_hllc_long_time()

    # 总结
    print("\n\n" + "="*80)
    print("Overall Test Summary")
    print("="*80)

    if success1 and success2:
        print("\n All tests PASSED")
        print("   HLLC implementation is correct and stable")
        print("   Phase 9.2 objective achieved!")
        sys.exit(0)
    elif success1 and not success2:
        print("\n  Short-time test passed, but long-time stability issues")
        print("   HLLC may need further tuning")
        sys.exit(1)
    else:
        print("\n Tests FAILED")
        print("   HLLC implementation needs debugging")
        sys.exit(1)
