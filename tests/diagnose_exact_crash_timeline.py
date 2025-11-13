#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
精确求解器崩溃时间线诊断
Diagnose timeline of Exact solver crash at t~1.8s

目标：
1. 记录t=1.0, 1.2, 1.4, 1.6, 1.8s的完整状态
2. 定位第一个出现非物理值的单元
3. 分析通量分布
4. 找出崩溃触发机制
"""

import numpy as np
import sys
import os
sys.path.insert(0, os.path.abspath('.'))

try:
    from solvers.godunov_fvm_solver import GodunvFVMSolver
except ImportError as e:
    print(f"Import error: {e}")
    print("Make sure project root is in sys.path")
    sys.exit(1)


def diagnose_crash_timeline(cfl=0.1, target_time=2.0):
    """
    详细诊断崩溃过程

    Args:
        cfl: CFL数
        target_time: 目标时间（预计在此之前崩溃）
    """
    print("=" * 80)
    print(f"精确求解器崩溃时间线诊断 (CFL={cfl})")
    print("=" * 80)

    width = 10.0
    length = 100.0
    n_cells = 100
    dx = length / n_cells

    # 溃坝初始条件
    h_init = np.zeros(n_cells)
    h_init[:25] = 2.0
    h_init[25:] = 1.0
    Q_init = np.zeros(n_cells)

    bc_left = {'type': 'h', 'value': 2.0}
    bc_right = {'type': 'h', 'value': 1.0}

    solver = GodunvFVMSolver(
        width=width, length=length, n_cells=n_cells,
        manning_n=0.0, slope=0.0, cfl=cfl, order=1,
        riemann_solver='exact', use_numba=False
    )

    solver.initialize(h_init.copy(), Q_init.copy(), bc_left, bc_right)
    mass_0 = np.sum(solver.h * solver.B * dx)

    print(f"\n初始质量: {mass_0:.6f} m^3")
    print(f"单元数: {n_cells}, dx={dx:.2f}m")

    # 记录检查点
    checkpoints = [1.0, 1.2, 1.4, 1.6, 1.8]
    snapshots = {}

    next_checkpoint_idx = 0
    crashed = False
    crash_time = None

    # 记录初始状态
    snapshots[0.0] = {
        'h': solver.h.copy(),
        'Q': solver.Q.copy(),
        'u': solver.Q / (solver.h * solver.B + 1e-10),
        'step': solver.step_count,
        'dt': 0.0
    }

    print(f"\n开始模拟...")
    print(f"{'时间(s)':<10} {'步数':<8} {'质量误差(%)':<15} {'h范围':<20} {'状态':<10}")
    print("-" * 80)

    while solver.t < target_time:
        dt_prev = solver.dt if solver.step_count > 0 else solver.compute_dt()

        try:
            solver.step()
        except Exception as e:
            crashed = True
            crash_time = solver.t
            print(f"\n 步进异常于t={crash_time:.4f}s: {str(e)}")
            break

        # 检查质量守恒
        mass = np.sum(solver.h * solver.B * dx)
        mass_error = abs(mass - mass_0) / mass_0 * 100
        h_min, h_max = np.min(solver.h), np.max(solver.h)

        # 检查物理合理性
        if np.any(np.isnan(solver.h)) or np.any(solver.h < 0):
            crashed = True
            crash_time = solver.t
            print(f"{solver.t:<10.4f} {solver.step_count:<8} {mass_error:<15.6f} [{h_min:.3f}, {h_max:.3f}] {'崩溃':<10}")
            break

        # 检查是否到达检查点
        if next_checkpoint_idx < len(checkpoints) and solver.t >= checkpoints[next_checkpoint_idx]:
            checkpoint_t = checkpoints[next_checkpoint_idx]

            snapshots[checkpoint_t] = {
                'h': solver.h.copy(),
                'Q': solver.Q.copy(),
                'u': solver.Q / (solver.h * solver.B + 1e-10),
                'step': solver.step_count,
                'dt': dt_prev,
                'mass_error': mass_error
            }

            status = "" if mass_error < 0.1 else ("" if mass_error < 1.0 else "")
            print(f"{solver.t:<10.4f} {solver.step_count:<8} {mass_error:<15.6f} [{h_min:.3f}, {h_max:.3f}] {status:<10}")

            next_checkpoint_idx += 1

        # 检查质量爆炸
        if mass_error > 100:
            crashed = True
            crash_time = solver.t
            print(f"{solver.t:<10.4f} {solver.step_count:<8} {mass_error:<15.6f} [{h_min:.3f}, {h_max:.3f}] {'质量爆炸':<10}")

            # 保存崩溃时刻快照
            snapshots['crash'] = {
                'h': solver.h.copy(),
                'Q': solver.Q.copy(),
                'u': solver.Q / (solver.h * solver.B + 1e-10),
                'step': solver.step_count,
                't': solver.t,
                'dt': dt_prev,
                'mass_error': mass_error
            }
            break

    # 分析快照
    print("\n" + "=" * 80)
    print("状态快照分析")
    print("=" * 80)

    sorted_times = sorted([t for t in snapshots.keys() if t != 'crash'])

    for i, t in enumerate(sorted_times):
        snap = snapshots[t]
        h = snap['h']
        Q = snap['Q']
        u = snap['u']

        print(f"\n时刻 t={t:.1f}s (步数={snap['step']}):")
        print(f"  dt = {snap['dt']:.6f}s")
        print(f"  h: min={np.min(h):.4f}, max={np.max(h):.4f}, mean={np.mean(h):.4f}")
        print(f"  Q: min={np.min(Q):.4f}, max={np.max(Q):.4f}, mean={np.mean(Q):.4f}")
        print(f"  u: min={np.min(u):.4f}, max={np.max(u):.4f}, mean={np.mean(u):.4f}")

        if 'mass_error' in snap:
            print(f"  质量误差: {snap['mass_error']:.6f}%")

        # 检查异常值
        if np.any(h < 0):
            neg_cells = np.where(h < 0)[0]
            print(f"    负深度单元: {neg_cells}")

        if np.any(np.abs(u) > 10):
            high_u_cells = np.where(np.abs(u) > 10)[0]
            print(f"    高速度单元: {high_u_cells}")

        # 边界单元状态
        print(f"  边界: h[0]={h[0]:.4f}, h[-1]={h[-1]:.4f}, Q[0]={Q[0]:.4f}, Q[-1]={Q[-1]:.4f}")

    # 崩溃时刻详细分析
    if crashed and 'crash' in snapshots:
        print("\n" + "=" * 80)
        print(f"崩溃时刻详细分析 (t={snapshots['crash']['t']:.4f}s)")
        print("=" * 80)

        h_crash = snapshots['crash']['h']
        Q_crash = snapshots['crash']['Q']
        u_crash = snapshots['crash']['u']

        # 找出所有异常单元
        print("\n异常单元诊断:")

        # 1. 负深度
        neg_h = np.where(h_crash < 0)[0]
        if len(neg_h) > 0:
            print(f"\n  负深度单元 ({len(neg_h)}个):")
            for i in neg_h[:5]:  # 只显示前5个
                print(f"    单元{i}: h={h_crash[i]:.6f}, Q={Q_crash[i]:.6f}")

        # 2. NaN值
        nan_h = np.where(np.isnan(h_crash))[0]
        if len(nan_h) > 0:
            print(f"\n  NaN深度单元 ({len(nan_h)}个):")
            for i in nan_h[:5]:
                print(f"    单元{i}: h={h_crash[i]}, Q={Q_crash[i]}")

        # 3. 极端速度
        extreme_u = np.where(np.abs(u_crash) > 20)[0]
        if len(extreme_u) > 0:
            print(f"\n  极端速度单元 ({len(extreme_u)}个, |u|>20m/s):")
            for i in extreme_u[:5]:
                print(f"    单元{i}: u={u_crash[i]:.6f}, h={h_crash[i]:.6f}")

        # 4. 边界附近 (前5个和后5个单元)
        print(f"\n  边界附近单元状态:")
        print(f"    左边界 (单元0-4):")
        for i in range(min(5, n_cells)):
            print(f"      单元{i}: h={h_crash[i]:.4f}, Q={Q_crash[i]:.4f}, u={u_crash[i]:.4f}")

        print(f"    右边界 (单元{n_cells-5}-{n_cells-1}):")
        for i in range(max(0, n_cells-5), n_cells):
            print(f"      单元{i}: h={h_crash[i]:.4f}, Q={Q_crash[i]:.4f}, u={u_crash[i]:.4f}")

        # 比较崩溃前的状态
        if len(sorted_times) > 0:
            prev_t = sorted_times[-1]
            h_prev = snapshots[prev_t]['h']

            # 找出变化最大的单元
            h_change = np.abs(h_crash - h_prev)
            top_change_idx = np.argsort(h_change)[-5:][::-1]

            print(f"\n  从t={prev_t:.1f}s到崩溃，变化最大的5个单元:")
            for idx in top_change_idx:
                print(f"    单元{idx}: Deltah={h_change[idx]:.6f} ({h_prev[idx]:.4f} -> {h_crash[idx]:.4f})")

    # 结论
    print("\n" + "=" * 80)
    print("诊断结论")
    print("=" * 80)

    if crashed:
        print(f"\n 成功捕获崩溃时刻: t={crash_time:.4f}s")
        print(f"   步数: {snapshots.get('crash', snapshots[sorted_times[-1]])['step']}")

        if 'crash' in snapshots:
            h_c = snapshots['crash']['h']
            if np.any(h_c < 0):
                print(f"\n 崩溃原因: 负深度出现")
                print(f"   -> 可能是边界条件与精确求解器的通量冲突")
            elif np.any(np.isnan(h_c)):
                print(f"\n 崩溃原因: NaN值出现")
                print(f"   -> 可能是Newton求解器在极端状态下失败")
            elif snapshots['crash']['mass_error'] > 100:
                print(f"\n 崩溃原因: 质量守恒严重失败")
                print(f"   -> 质量误差={snapshots['crash']['mass_error']:.2f}%")
    else:
        print(f"\n 未崩溃，成功到达t={solver.t:.4f}s")

    return snapshots, crashed, crash_time

if __name__ == "__main__":
    # 诊断CFL=0.1情况
    snapshots, crashed, crash_time = diagnose_crash_timeline(cfl=0.1, target_time=2.0)

    print("\n" + "=" * 80)
    print("诊断完成")
    print("=" * 80)
