#!/usr/bin/env python
"""
简化的求解器对比测试
使用温和的初始条件避免数值不稳定
"""

import numpy as np
import matplotlib.pyplot as plt
import time
import sys
import os

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from solvers.godunov_fvm_solver import GodunvFVMSolver


def simple_comparison():
    """简单对比: HLL vs 精确"""

    print("="*70)
    print("简化求解器对比: HLL vs 精确")
    print("="*70)
    print()

    # 温和的配置
    length = 100.0
    width = 10.0
    n_cells = 50  # 减少单元数
    dx = length / n_cells

    # 温和的Dam Break
    h_L = 2.0  # 降低水深差
    h_R = 1.0
    t_final = 1.0  # 缩短时间

    print(f"配置:")
    print(f"  域: {length}m, {n_cells}单元, dx={dx:.2f}m")
    print(f"  时间: {t_final}s")
    print(f"  Dam Break: h_L={h_L}m, h_R={h_R}m")
    print()

    # 初始条件
    x = np.linspace(0.5*dx, length - 0.5*dx, n_cells)
    h_init = np.ones(n_cells)
    h_init[x < 50.0] = h_L
    h_init[x >= 50.0] = h_R
    Q_init = np.zeros(n_cells)

    # 固定h边界
    bc_left = {'type': 'h', 'value': h_L}
    bc_right = {'type': 'h', 'value': h_R}

    mass_init = np.sum(h_init * dx * width)

    # === HLL ===
    print("[1/2] HLL求解器...")
    solver_hll = GodunvFVMSolver(
        width=width, length=length, n_cells=n_cells,
        manning_n=0.0, cfl=0.5, order=1,  # 使用1阶避免MUSCL不稳定
        use_numba=True, riemann_solver='hll',
        well_balanced=False, slope=0.0
    )
    solver_hll.initialize(h_init.copy(), Q_init.copy(), bc_left, bc_right)

    t_start = time.time()
    step = 0
    while solver_hll.t < t_final and step < 10000:
        solver_hll.step()
        step += 1

        # 检查NaN
        if np.any(np.isnan(solver_hll.h)):
            print(f"  ❌ HLL在t={solver_hll.t:.3f}s, 步骤{step}出现NaN!")
            print(f"  h范围: [{np.nanmin(solver_hll.h):.3f}, {np.nanmax(solver_hll.h):.3f}]")
            break

    t_hll = time.time() - t_start

    # 检查最终状态
    if not np.any(np.isnan(solver_hll.h)):
        mass_hll = np.sum(solver_hll.h * dx * width)
        mass_error_hll = abs(mass_hll - mass_init) / mass_init * 100
        print(f"  ✅ 完成: t={solver_hll.t:.3f}s, {step}步, 耗时{t_hll:.3f}s")
        print(f"  质量守恒: {mass_error_hll:.6f}%")
        hll_success = True
    else:
        print(f"  ❌ HLL失败")
        hll_success = False

    print()

    # === 精确 ===
    print("[2/2] 精确求解器...")
    solver_exact = GodunvFVMSolver(
        width=width, length=length, n_cells=n_cells,
        manning_n=0.0, cfl=0.5, order=1,  # 使用1阶
        use_numba=True, riemann_solver='exact',
        well_balanced=False, slope=0.0
    )
    solver_exact.initialize(h_init.copy(), Q_init.copy(), bc_left, bc_right)

    t_start = time.time()
    step = 0
    while solver_exact.t < t_final and step < 10000:
        solver_exact.step()
        step += 1

        # 检查NaN
        if np.any(np.isnan(solver_exact.h)):
            print(f"  ❌ 精确在t={solver_exact.t:.3f}s, 步骤{step}出现NaN!")
            print(f"  h范围: [{np.nanmin(solver_exact.h):.3f}, {np.nanmax(solver_exact.h):.3f}]")
            break

    t_exact = time.time() - t_start

    # 检查最终状态
    if not np.any(np.isnan(solver_exact.h)):
        mass_exact = np.sum(solver_exact.h * dx * width)
        mass_error_exact = abs(mass_exact - mass_init) / mass_init * 100
        print(f"  ✅ 完成: t={solver_exact.t:.3f}s, {step}步, 耗时{t_exact:.3f}s")
        print(f"  质量守恒: {mass_error_exact:.6f}%")
        exact_success = True
    else:
        print(f"  ❌ 精确失败")
        exact_success = False

    print()

    # === 对比 ===
    if hll_success and exact_success:
        print("="*70)
        print("对比结果")
        print("="*70)
        print()

        print(f"性能:")
        print(f"  HLL:   {t_hll:.3f}s (1.00x)")
        print(f"  精确:  {t_exact:.3f}s ({t_exact/t_hll:.2f}x)")
        print()

        print(f"质量守恒:")
        print(f"  HLL:   {mass_error_hll:.6f}%")
        print(f"  精确:  {mass_error_exact:.6f}%")
        print()

        # 误差
        h_diff = solver_exact.h - solver_hll.h
        max_diff = np.max(np.abs(h_diff))
        rms_diff = np.sqrt(np.mean(h_diff**2))

        print(f"精度 (精确 vs HLL):")
        print(f"  Max |Δh|: {max_diff:.6f} m")
        print(f"  RMS(Δh):  {rms_diff:.6f} m")
        print()

        # 可视化
        fig, axes = plt.subplots(2, 1, figsize=(12, 8))

        # 水深
        ax1 = axes[0]
        ax1.plot(x, solver_hll.h, 'b-', linewidth=2, label='HLL')
        ax1.plot(x, solver_exact.h, 'r:', linewidth=2.5, label='Exact')
        ax1.set_ylabel('Depth h (m)', fontsize=12)
        ax1.set_title(f'Dam Break Comparison (t={t_final}s)', fontsize=13, weight='bold')
        ax1.legend()
        ax1.grid(True, alpha=0.3)

        # 误差
        ax2 = axes[1]
        ax2.plot(x, h_diff, 'g-', linewidth=2)
        ax2.axhline(0, color='gray', linestyle=':', alpha=0.5)
        ax2.set_xlabel('Position x (m)', fontsize=12)
        ax2.set_ylabel('Error (Exact - HLL) m', fontsize=12)
        ax2.set_title(f'Difference (Max={max_diff:.6f}m)', fontsize=12)
        ax2.grid(True, alpha=0.3)

        plt.tight_layout()

        output_dir = 'test_results'
        os.makedirs(output_dir, exist_ok=True)
        output_file = os.path.join(output_dir, 'simple_solver_comparison.png')
        plt.savefig(output_file, dpi=150, bbox_inches='tight')
        print(f"保存: {output_file}")
        print()

        print("="*70)
        print("✅ 测试成功!")
        print("="*70)
        return True

    else:
        print("="*70)
        print("❌ 测试失败: 求解器不稳定")
        print("="*70)
        return False


if __name__ == '__main__':
    print("\n")
    success = simple_comparison()
    print()
    sys.exit(0 if success else 1)
