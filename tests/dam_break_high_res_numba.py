#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
高精度溃坝测试（Numba加速版本）

展示Numba加速在实际应用中的威力

作者: HydroClaude Team
日期: 2025-10-29
"""

import numpy as np
import sys
import os
import time

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from solvers.godunov_fvm_solver import GodunvFVMSolver


def high_resolution_dam_break(n_cells=400, t_end=30.0, use_numba=True):
    """
    高精度溃坝模拟

    Args:
        n_cells: 网格数（400=高精度）
        t_end: 模拟结束时间
        use_numba: 是否使用Numba加速
    """
    print("=" * 80)
    print(f"高精度溃坝模拟")
    print("=" * 80)
    print(f"网格数: {n_cells}")
    print(f"模拟时间: {t_end} s")
    print(f"Numba加速: {'启用 🚀' if use_numba else '禁用'}")
    print()

    # 参数
    b = 10.0
    L = 2000.0
    h_L = 10.0
    h_R = 1.0
    g = 9.81

    # 创建求解器
    solver = GodunvFVMSolver(
        width=b, length=L, n_cells=n_cells,
        manning_n=0.0, slope=0.0,
        g=g, cfl=0.5, order=2,
        use_numba=use_numba
    )

    # 初始条件：溃坝
    h_init = np.where(solver.x < L/2, h_L, h_R)
    Q_init = np.zeros(n_cells)

    solver.initialize(
        h_init, Q_init,
        bc_left={'type': 'h', 'value': h_L},
        bc_right={'type': 'h', 'value': h_R}
    )

    print(f"\n初始条件:")
    print(f"  左侧水深: {h_L} m")
    print(f"  右侧水深: {h_R} m")
    print(f"  初始质量: {solver.initial_mass:.2f} m³")
    print()

    # 理论波速
    c0 = np.sqrt(g * h_L)
    x_front_theory = L/2 + 2*c0*t_end
    x_tail_theory = L/2 - c0*t_end

    print(f"理论预测 (t={t_end}s):")
    print(f"  波前位置: {x_front_theory:.1f} m")
    print(f"  波尾位置: {x_tail_theory:.1f} m")
    print()

    # 时间推进
    print("时间推进...")
    start_time = time.time()
    last_progress_time = start_time

    step = 0
    progress_interval = 5.0  # 每5秒报告一次

    while solver.t < t_end:
        solver.step()
        step += 1

        # 进度报告
        current_time = time.time()
        if current_time - last_progress_time >= progress_interval:
            elapsed = current_time - start_time
            progress = solver.t / t_end * 100
            eta = elapsed / progress * 100 - elapsed if progress > 0 else 0

            print(f"  进度: {progress:5.1f}% | t={solver.t:6.2f}s | "
                  f"步数: {step:6d} | 已耗时: {elapsed:6.1f}s | "
                  f"预计剩余: {eta:6.1f}s")
            last_progress_time = current_time

    end_time = time.time()
    total_time = end_time - start_time

    print(f"\n✅ 模拟完成!")
    print(f"  总步数: {step}")
    print(f"  模拟时间: {solver.t:.2f} s")
    print(f"  墙钟时间: {total_time:.2f} s")
    print(f"  平均每步: {total_time/step*1000:.3f} ms")
    print(f"  质量守恒误差: {solver.get_mass_conservation_error():.6f}%")
    print()

    # 分析结果
    print("=" * 80)
    print("结果分析")
    print("=" * 80)

    # 找到波前位置（水深突变点）
    h = solver.h
    x = solver.x

    # 波前：h从高到低的位置
    h_threshold = 0.5 * (h_L + h_R)
    front_mask = h > h_threshold
    if np.any(front_mask):
        x_front_num = x[front_mask][-1]
    else:
        x_front_num = x[-1]

    # 波尾：h从零开始的位置
    tail_mask = h > 0.1 * h_L
    if np.any(tail_mask):
        x_tail_num = x[tail_mask][0]
    else:
        x_tail_num = x[0]

    # 误差分析
    front_error = abs(x_front_num - x_front_theory) / x_front_theory * 100
    tail_error = abs(x_tail_num - x_tail_theory) / abs(x_tail_theory) * 100

    print(f"\n波前位置:")
    print(f"  理论值: {x_front_theory:.1f} m")
    print(f"  数值解: {x_front_num:.1f} m")
    print(f"  误差: {front_error:.2f}%")

    print(f"\n波尾位置:")
    print(f"  理论值: {x_tail_theory:.1f} m")
    print(f"  数值解: {x_tail_num:.1f} m")
    print(f"  误差: {tail_error:.2f}%")

    # 性能分析
    if use_numba:
        estimated_python_time = total_time * 68  # 基于68x加速比
        print(f"\n⚡ 性能对比:")
        print(f"  Numba JIT: {total_time:.1f} s")
        print(f"  预计纯Python: {estimated_python_time:.1f} s ({estimated_python_time/60:.1f} 分钟)")
        print(f"  节省时间: {estimated_python_time - total_time:.1f} s ({(estimated_python_time - total_time)/60:.1f} 分钟)")

    print()

    return {
        'n_cells': n_cells,
        'n_steps': step,
        'sim_time': solver.t,
        'wall_time': total_time,
        'front_error': front_error,
        'tail_error': tail_error,
        'mass_error': solver.get_mass_conservation_error()
    }


if __name__ == '__main__':
    print("\n")
    print("╔" + "═" * 78 + "╗")
    print("║" + " " * 20 + "高精度溃坝模拟 (Numba加速)" + " " * 27 + "║")
    print("╚" + "═" * 78 + "╝")
    print()

    # 测试1：400网格，30秒
    result = high_resolution_dam_break(n_cells=400, t_end=30.0, use_numba=True)

    print("\n" + "=" * 80)
    if result['front_error'] < 10 and result['mass_error'] < 1:
        print(f"✅✅✅ 高精度溃坝模拟成功！")
        print(f"  波前误差: {result['front_error']:.2f}%")
        print(f"  质量守恒: {result['mass_error']:.6f}%")
        print(f"  墙钟时间: {result['wall_time']:.1f}s")
    else:
        print(f"⚠️  精度需要进一步提升")
    print("=" * 80)
    print()

    # 可选：测试不同网格数
    if len(sys.argv) > 1 and sys.argv[1] == '--full':
        print("\n完整测试：不同网格数的性能")
        print("=" * 80)
        for n_cells in [100, 200, 400, 800]:
            print(f"\n网格数: {n_cells}")
            result = high_resolution_dam_break(n_cells=n_cells, t_end=15.0, use_numba=True)
            print(f"  完成时间: {result['wall_time']:.2f}s")
