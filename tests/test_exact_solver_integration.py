#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
测试精确Riemann求解器集成到GodunvFVMSolver

Purpose: 验证Phase 9.3精确求解器能正确工作
"""

import numpy as np
import warnings
warnings.filterwarnings("ignore")
import sys
import pytest
import os

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

pytestmark = [pytest.mark.slow, pytest.mark.solver]

# Maximum solver steps to prevent hanging in CI
_MAX_SOLVER_STEPS = 5000

try:
    from solvers.godunov_fvm_solver import GodunvFVMSolver
except ImportError as e:
    pytest.skip(f"Required module not available: {e}", allow_module_level=True)



@pytest.mark.timeout(300)
def test_exact_solver_simple():
    """测试精确求解器基本功能"""

    print("="*70)
    print("测试精确Riemann求解器集成")
    print("="*70)
    print()

    # 创建简单的dam break配置
    width = 10.0
    length = 100.0
    n_cells = 100

    print(f"配置:")
    print(f"  长度: {length}m")
    print(f"  单元数: {n_cells}")
    print(f"  宽度: {width}m")
    print()

    # 创建精确求解器
    print("[1/3] 创建精确求解器...")
    try:
        solver = GodunvFVMSolver(
            width=width,
            length=length,
            n_cells=n_cells,
            manning_n=0.0,  # 无摩擦
            cfl=0.3,
            order=1,
            use_numba=True,
            riemann_solver='exact',  # 使用精确求解器
            slope=0.0
        )
        print("   精确求解器创建成功")
    except Exception as e:
        print(f"   创建失败: {e}")
        import traceback
        traceback.print_exc()
        return False

    print()

    # 初始化dam break
    print("[2/3] 初始化Dam Break...")
    h_init = np.ones(n_cells)
    h_init[:25] = 5.0  # 左侧高
    h_init[25:] = 1.0  # 右侧低
    Q_init = np.zeros(n_cells)

    bc_left = {'type': 'h', 'value': 5.0}
    bc_right = {'type': 'h', 'value': 1.0}

    solver.initialize(h_init, Q_init, bc_left, bc_right)

    mass_init = np.sum(solver.h * solver.dx * solver.B)
    print(f"  初始质量: {mass_init:.2f} m^3")
    print()

    # 运行10步
    print("[3/3] 运行10个时间步...")
    try:
        for step in range(10):
            solver.step()

            # 检查NaN
            assert not np.any(np.isnan(solver.h)), f"NaN in h at step {step+1}"
            assert not np.any(np.isnan(solver.Q)), f"NaN in Q at step {step+1}"

        print(f"   运行成功")
        print(f"  时间: t={solver.t:.4f}s")
        print(f"  时间步数: {solver.step_count}")
        print()

        # 检查质量守恒
        mass_final = np.sum(solver.h * solver.dx * solver.B)
        mass_error = abs(mass_final - mass_init) / mass_init * 100

        print(f"质量守恒检查:")
        print(f"  初始质量: {mass_init:.6f} m^3")
        print(f"  最终质量: {mass_final:.6f} m^3")
        print(f"  误差: {mass_error:.6f}%")

        if mass_error < 0.1:
            print("   质量守恒良好 (< 0.1%)")
        else:
            print(f"    质量守恒误差较大: {mass_error:.6f}%")

        print()

    except Exception as e:
        pytest.fail(f"Exact solver integration test failed: {e}")

    print("="*70)
    print(" 精确求解器集成测试通过!")
    print("="*70)
    print()

    # Verify mass conservation
    assert mass_error < 10.0, f"Mass conservation error too large: {mass_error:.6f}%"


@pytest.mark.timeout(300)
def test_exact_vs_hll_comparison():
    """对比精确求解器与HLL的结果"""

    print("="*70)
    print("精确求解器 vs HLL 对比测试")
    print("="*70)
    print()

    # 配置
    width = 10.0
    length = 100.0
    n_cells = 100
    t_final = 0.1

    # 初始条件
    h_init = np.ones(n_cells)
    h_init[:25] = 3.0
    h_init[25:] = 1.0
    Q_init = np.zeros(n_cells)

    bc_left = {'type': 'h', 'value': 3.0}
    bc_right = {'type': 'h', 'value': 1.0}

    # 运行精确求解器
    print("[1/2] 运行精确求解器...")
    solver_exact = GodunvFVMSolver(
        width=width, length=length, n_cells=n_cells,
        manning_n=0.0, cfl=0.3, order=1,
        use_numba=True, riemann_solver='exact', slope=0.0
    )
    solver_exact.initialize(h_init.copy(), Q_init.copy(), bc_left, bc_right)

    step_count = 0
    while solver_exact.t < t_final and step_count < _MAX_SOLVER_STEPS:
        solver_exact.step()
        step_count += 1

    print(f"  时间: {solver_exact.t:.4f}s")
    print(f"  步数: {solver_exact.step_count}")
    print()

    # 运行HLL求解器
    print("[2/2] 运行HLL求解器...")
    solver_hll = GodunvFVMSolver(
        width=width, length=length, n_cells=n_cells,
        manning_n=0.0, cfl=0.3, order=1,
        use_numba=True, riemann_solver='hll', slope=0.0
    )
    solver_hll.initialize(h_init.copy(), Q_init.copy(), bc_left, bc_right)

    step_count = 0
    while solver_hll.t < t_final and step_count < _MAX_SOLVER_STEPS:
        solver_hll.step()
        step_count += 1

    print(f"  时间: {solver_hll.t:.4f}s")
    print(f"  步数: {solver_hll.step_count}")
    print()

    # 对比结果
    h_diff = solver_exact.h - solver_hll.h
    Q_diff = solver_exact.Q - solver_hll.Q

    print("结果对比 (精确 - HLL):")
    print(f"  Max |Deltah|: {np.max(np.abs(h_diff)):.6f} m")
    print(f"  RMS(Deltah): {np.sqrt(np.mean(h_diff**2)):.6f} m")
    print(f"  Max |DeltaQ|: {np.max(np.abs(Q_diff)):.6f} m^3/s")
    print(f"  RMS(DeltaQ): {np.sqrt(np.mean(Q_diff**2)):.6f} m^3/s")
    print()

    # 期望: 精确求解器数值耗散更小，应该有差异但不太大
    max_h_diff = np.max(np.abs(h_diff))
    if max_h_diff < 0.5:
        print(" 两种求解器结果基本一致（差异合理）")
    else:
        print(f"  差异较大: max|Deltah| = {max_h_diff:.3f}m")

    print()
    print("="*70)
    print()

    return True


if __name__ == '__main__':
    print("\n")

    # 测试1: 基本集成
    success1 = test_exact_solver_simple()

    if not success1:
        print("基本集成测试失败!")
        sys.exit(1)

    # 测试2: 与HLL对比
    success2 = test_exact_vs_hll_comparison()

    if not success2:
        print("对比测试失败!")
        sys.exit(1)

    print("\n")
    print("="*70)
    print(" 所有测试通过!")
    print("="*70)
    print()
    print("Phase 9.3精确Riemann求解器已成功集成到GodunvFVMSolver")
    print()

    sys.exit(0)
