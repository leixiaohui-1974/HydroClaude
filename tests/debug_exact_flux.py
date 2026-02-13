#!/usr/bin/env python
"""
诊断精确Riemann求解器通量计算
"""

import numpy as np
import warnings
warnings.filterwarnings("ignore")
import sys
import pytest
import os

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

try:
    from solvers.riemann_exact import exact_riemann_flux, exact_riemann_flux_numba
except ImportError as e:
    pytest.skip(f"Required module not available: {e}", allow_module_level=True)

from solvers.riemann_numba import hll_flux_numba


def test_flux_comparison():
    """对比精确求解器和HLL的通量"""

    print("="*70)
    print("诊断精确求解器 vs HLL 通量对比")
    print("="*70)
    print()

    # 简单的dam break状态
    h_L = 3.0
    h_R = 1.0
    Q_L = 0.0
    Q_R = 0.0
    B = 10.0
    g = 9.81

    print(f"左状态:  h={h_L}m, Q={Q_L}m^3/s")
    print(f"右状态:  h={h_R}m, Q={Q_R}m^3/s")
    print(f"宽度: {B}m")
    print()

    # 计算HLL通量
    print("[1/2] HLL求解器:")
    F_h_hll, F_Q_hll = hll_flux_numba(h_L, Q_L, h_R, Q_R, B, g, eps_dry=1e-6)
    print(f"  F_h = {F_h_hll:.6f} m^3/s")
    print(f"  F_Q = {F_Q_hll:.6f} m^3/s^2")
    print()

    # 计算精确通量
    print("[2/2] 精确求解器:")
    try:
        F_h_exact, F_Q_exact = exact_riemann_flux_numba(
            h_L, Q_L, h_R, Q_R, B, g,
            eps_dry=1e-6, max_iter=50, tol=1e-10
        )
        print(f"  F_h = {F_h_exact:.6f} m^3/s")
        print(f"  F_Q = {F_Q_exact:.6f} m^3/s^2")
        print()

        # 对比
        print("差异:")
        print(f"  DeltaF_h = {abs(F_h_exact - F_h_hll):.6f} m^3/s ({abs(F_h_exact - F_h_hll)/abs(F_h_hll)*100:.2f}%)")
        print(f"  DeltaF_Q = {abs(F_Q_exact - F_Q_hll):.6f} m^3/s^2 ({abs(F_Q_exact - F_Q_hll)/abs(F_Q_hll)*100:.2f}%)")
        print()

        # 检查通量是否合理
        if abs(F_h_exact) > 100 or abs(F_Q_exact) > 10000:
            print(f"  警告: 精确求解器通量异常大!")
            print(f"  F_h_exact = {F_h_exact:.3e}")
            print(f"  F_Q_exact = {F_Q_exact:.3e}")
            return False

        if abs(F_h_exact - F_h_hll) / abs(F_h_hll) > 0.5:
            print("  警告: 精确与HLL通量差异>50%")
            return False

        print(" 通量计算合理")
        return True

    except Exception as e:
        print(f" 精确求解器失败: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_single_step_mass():
    """测试单步质量守恒"""

    print("="*70)
    print("诊断单步质量守恒")
    print("="*70)
    print()

    from solvers.godunov_fvm_solver import GodunvFVMSolver

    # 创建简单求解器
    solver = GodunvFVMSolver(
        width=10.0,
        length=10.0,  # 非常短的域
        n_cells = 100,    # 非常少的单元
        manning_n=0.0,
        cfl=0.1,      # 小CFL
        order=1,      # 1阶避免MUSCL带来的复杂性
        use_numba=True,
        riemann_solver='exact',
        slope=0.0
    )

    # 简单初始条件
    h_init = np.array([2.0, 2.0, 1.0, 1.0, 1.0])
    Q_init = np.zeros(5)

    bc_left = {'type': 'wall'}
    bc_right = {'type': 'wall'}

    solver.initialize(h_init, Q_init, bc_left, bc_right)

    print(f"初始状态:")
    print(f"  h = {solver.h}")
    print(f"  Q = {solver.Q}")

    mass_init = np.sum(solver.h * solver.dx * solver.B)
    print(f"  质量 = {mass_init:.6f} m^3")
    print()

    # 单步
    print("执行1步...")
    solver.step()

    print(f"步骤后状态:")
    print(f"  h = {solver.h}")
    print(f"  Q = {solver.Q}")

    mass_final = np.sum(solver.h * solver.dx * solver.B)
    mass_error = abs(mass_final - mass_init) / mass_init * 100

    print(f"  质量 = {mass_final:.6f} m^3")
    print(f"  误差 = {mass_error:.6f}%")
    print()

    if mass_error < 1.0:
        print(" 单步质量守恒良好")
        return True
    else:
        print(f" 单步质量守恒失败: {mass_error:.2f}%")

        # 诊断检查通量
        if hasattr(solver, 'last_F_h'):
            print(f"\n通量诊断:")
            print(f"  F_h = {solver.last_F_h}")
            print(f"  F_Q = {solver.last_F_Q}")

        return False


if __name__ == '__main__':
    print("\n")

    # 测试1: 通量对比
    success1 = test_flux_comparison()

    # 测试2: 单步质量守恒
    success2 = test_single_step_mass()

    print()
    print("="*70)
    if success1 and success2:
        print(" 诊断测试全部通过")
    else:
        print(" 发现问题!")
        if not success1:
            print("  - 通量计算异常")
        if not success2:
            print("  - 质量守恒失败")
    print("="*70)
    print()
