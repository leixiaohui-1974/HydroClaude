#!/usr/bin/env python
"""
诊断精确求解器质量损失问题
"""

import numpy as np
import warnings
warnings.filterwarnings("ignore")
import sys
import pytest
import os

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

try:
    from solvers.godunov_fvm_solver import GodunvFVMSolver
except ImportError as e:
    pytest.skip(f"Required module not available: {e}", allow_module_level=True)



def diagnose_mass_loss():
    """逐步诊断质量损失"""

    print("="*70)
    print("诊断精确求解器质量损失")
    print("="*70)
    print()

    # 配置
    length = 100.0
    width = 10.0
    n_cells = 100
    dx = length / n_cells

    # 初始条件
    x = np.linspace(0.5*dx, length - 0.5*dx, n_cells)
    h_init = np.ones(n_cells)
    h_init[x < 50.0] = 2.0
    h_init[x >= 50.0] = 1.0
    Q_init = np.zeros(n_cells)

    bc_left = {'type': 'h', 'value': 2.0}
    bc_right = {'type': 'h', 'value': 1.0}

    # 创建精确求解器
    solver = GodunvFVMSolver(
        width=width, length=length, n_cells=n_cells,
        manning_n=0.0, cfl=0.3, order=1,
        use_numba=True, riemann_solver='exact',
        well_balanced=False, slope=0.0
    )

    solver.initialize(h_init.copy(), Q_init.copy(), bc_left, bc_right)

    mass_init = np.sum(solver.h * dx * width)
    print(f"初始质量: {mass_init:.6f} m^3")
    print(f"初始h范围: [{np.min(solver.h):.3f}, {np.max(solver.h):.3f}] m")
    print()

    # 逐步模拟,监控质量
    print("逐步监控:")
    print(f"{'步骤':<6} {'时间(s)':<10} {'质量(m^3)':<15} {'误差(%)':<10} {'Max h':<10}")
    print("-"*60)

    for step in range(10):
        solver.step()

        mass = np.sum(solver.h * dx * width)
        mass_error = abs(mass - mass_init) / mass_init * 100
        max_h = np.max(solver.h)

        print(f"{step+1:<6} {solver.t:<10.3f} {mass:<15.6f} {mass_error:<10.6f} {max_h:<10.3f}")

        # 检查异常
        if np.any(np.isnan(solver.h)):
            print(f"\n 步骤{step+1}出现NaN!")
            break

        if mass_error > 50:
            print(f"\n 步骤{step+1}质量误差超过50%!")
            break

        if max_h > 100:
            print(f"\n 步骤{step+1}水深爆炸: max_h={max_h:.1f}m!")
            break

    print()

    # 最终状态
    mass_final = np.sum(solver.h * dx * width)
    mass_error = abs(mass_final - mass_init) / mass_init * 100

    print(f"最终状态:")
    print(f"  时间: t={solver.t:.3f}s")
    print(f"  质量: {mass_final:.6f} m^3")
    print(f"  误差: {mass_error:.6f}%")
    print(f"  h范围: [{np.min(solver.h):.3f}, {np.max(solver.h):.3f}] m")
    print()

    if mass_error > 1.0:
        print(f" 质量守恒失败: {mass_error:.2f}% > 1%")
        print()
        print("可能原因:")
        print("  1. 边界条件处理不当")
        print("  2. 精确求解器通量计算错误")
        print("  3. 时间积分问题")

        # 检查h分布
        print()
        print(f"水深分布 (前5和后5单元):")
        print(f"  前5: {solver.h[:5]}")
        print(f"  后5: {solver.h[-5:]}")

    else:
        print(f" 质量守恒良好: {mass_error:.6f}%")

    print()
    print("="*70)


if __name__ == '__main__':
    diagnose_mass_loss()
