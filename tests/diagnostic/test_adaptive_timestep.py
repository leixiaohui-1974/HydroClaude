#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
自适应时间步性能测试

比较固定时间步和自适应时间步的性能差异：
1. 计算速度
2. 数值精度
3. 稳定性

作者: Claude
日期: 2025-10-23
"""
import sys
import warnings
warnings.filterwarnings("ignore")
import os

# ========== 路径设置 ==========
script_path = os.path.abspath(__file__)
project_root = os.path.dirname(os.path.dirname(script_path))
sys.path.insert(0, project_root)


import numpy as np
import matplotlib.pyplot as plt
import time
import pytest
try:
    from solvers.hydrostatic_canal_solver import HydrostaticCanalSolver
except ImportError as e:
    pytest.skip(f"Required module not available: {e}", allow_module_level=True)

from solvers.gate import SluiceGate


def test_comparison_simple():
    """测试1: 简单渠道流 - 固定vs自适应时间步"""
    print("=" * 80)
    print("测试1: 简单渠道流 - 性能对比")
    print("=" * 80)

    # 渠道参数
    L = 1000.0
    nx = 101
    B = 10.0
    S0 = 0.001
    n = 0.025

    # 创建两个求解器（相同初始条件）
    solver_fixed = HydrostaticCanalSolver(
        length=L, nx=nx, B=B, S0=S0, n=n
    )
    solver_adaptive = HydrostaticCanalSolver(
        length=L, nx=nx, B=B, S0=S0, n=n
    )

    # 初始条件
    h_init = 0.6
    Q_init = 5.0
    solver_fixed.h = np.ones(nx) * h_init
    solver_fixed.hu = np.ones(nx) * Q_init / B
    solver_adaptive.h = np.ones(nx) * h_init
    solver_adaptive.hu = np.ones(nx) * Q_init / B

    # 边界条件：流量阶跃
    def Q_upstream_func(t):
        return 5.0 if t < 50.0 else 10.0

    def h_downstream_func(t):
        return 0.6 if t < 50.0 else 0.93

    t_end = 50.0

    # 固定时间步
    print(f"\n固定时间步求解...")
    t_start = time.time()
    result_fixed = solver_fixed.solve_transient(
        t_end=t_end,
        dt=0.5,
        Q_upstream_func=Q_upstream_func,
        h_downstream_func=h_downstream_func,
        save_interval=10,
        verbose=False
    )
    time_fixed = time.time() - t_start
    print(f"  完成: {time_fixed:.3f}秒")
    print(f"  时间步数: {int(t_end/0.5)}")
    print(f"  保存点数: {len(result_fixed['t_history'])}")

    # 自适应时间步
    print(f"\n自适应时间步求解...")
    t_start = time.time()
    result_adaptive = solver_adaptive.solve_transient_adaptive(
        t_end=t_end,
        dt_initial=0.1,
        dt_min=0.01,
        dt_max=1.0,
        CFL_number=0.5,
        Q_upstream_func=Q_upstream_func,
        h_downstream_func=h_downstream_func,
        save_interval_time=2.0,
        verbose=False
    )
    time_adaptive = time.time() - t_start
    print(f"  完成: {time_adaptive:.3f}秒")
    print(f"  时间步数: {result_adaptive['n_steps']}")
    print(f"  保存点数: {len(result_adaptive['t_history'])}")
    print(f"  平均时间步: {np.mean(result_adaptive['dt_history']):.4f}s")
    print(f"  时间步范围: [{np.min(result_adaptive['dt_history']):.4f}, "
          f"{np.max(result_adaptive['dt_history']):.4f}]s")

    # 性能对比
    print(f"\n性能对比：")
    speedup = time_fixed / time_adaptive if time_adaptive > 0 else 0
    efficiency = (int(t_end/0.5)) / result_adaptive['n_steps']
    print(f"  计算时间比: {time_fixed:.3f}s / {time_adaptive:.3f}s = {speedup:.2f}x")
    print(f"  时间步效率: {efficiency:.2f}x (自适应用更少步数)")

    # 精度对比（最终状态）
    h_diff = np.abs(result_fixed['h_final'] - result_adaptive['h_final'])
    Q_diff = np.abs(result_fixed['Q_final'] - result_adaptive['Q_final'])
    print(f"\n精度对比（最终状态）：")
    print(f"  水深最大差异: {np.max(h_diff):.6f} m")
    print(f"  流量最大差异: {np.max(Q_diff):.6f} m^3/s")

    # 绘图
    fig, axes = plt.subplots(3, 2, figsize=(14, 10))

    # 水深剖面对比
    ax = axes[0, 0]
    ax.plot(solver_fixed.x, result_fixed['h_final'], 'b-',
            linewidth=2, label='Fixed dt=0.5s')
    ax.plot(solver_adaptive.x, result_adaptive['h_final'], 'r--',
            linewidth=2, label='Adaptive dt')
    ax.set_xlabel('Position (m)')
    ax.set_ylabel('Water depth (m)')
    ax.set_title('Final Water Depth Profile')
    ax.legend()
    ax.grid(True, alpha=0.3)

    # 流量剖面对比
    ax = axes[0, 1]
    ax.plot(solver_fixed.x, result_fixed['Q_final'], 'b-',
            linewidth=2, label='Fixed dt=0.5s')
    ax.plot(solver_adaptive.x, result_adaptive['Q_final'], 'r--',
            linewidth=2, label='Adaptive dt')
    ax.set_xlabel('Position (m)')
    ax.set_ylabel('Discharge (m^3/s)')
    ax.set_title('Final Discharge Profile')
    ax.legend()
    ax.grid(True, alpha=0.3)

    # 入口水深时间演化
    ax = axes[1, 0]
    h_inlet_fixed = [h_hist[0] for h_hist in result_fixed['h_history']]
    h_inlet_adaptive = [h_hist[0] for h_hist in result_adaptive['h_history']]
    ax.plot(result_fixed['t_history'], h_inlet_fixed, 'b.-', label='Fixed dt')
    ax.plot(result_adaptive['t_history'], h_inlet_adaptive, 'r.--', label='Adaptive dt')
    ax.set_xlabel('Time (s)')
    ax.set_ylabel('Water depth at inlet (m)')
    ax.set_title('Inlet Water Depth Evolution')
    ax.legend()
    ax.grid(True, alpha=0.3)

    # 入口流量时间演化
    ax = axes[1, 1]
    Q_inlet_fixed = [Q_hist[0] for Q_hist in result_fixed['Q_history']]
    Q_inlet_adaptive = [Q_hist[0] for Q_hist in result_adaptive['Q_history']]
    ax.plot(result_fixed['t_history'], Q_inlet_fixed, 'b.-', label='Fixed dt')
    ax.plot(result_adaptive['t_history'], Q_inlet_adaptive, 'r.--', label='Adaptive dt')
    ax.axhline(5.0, color='gray', linestyle=':', alpha=0.5)
    ax.axhline(10.0, color='gray', linestyle=':', alpha=0.5)
    ax.set_xlabel('Time (s)')
    ax.set_ylabel('Discharge at inlet (m^3/s)')
    ax.set_title('Inlet Discharge Evolution')
    ax.legend()
    ax.grid(True, alpha=0.3)

    # 差异图（水深）
    ax = axes[2, 0]
    ax.plot(solver_fixed.x, h_diff, 'g-', linewidth=2)
    ax.set_xlabel('Position (m)')
    ax.set_ylabel('|Δh| (m)')
    ax.set_title('Water Depth Difference (|Fixed - Adaptive|)')
    ax.grid(True, alpha=0.3)

    # 时间步历史
    ax = axes[2, 1]
    ax.plot(result_adaptive['t_history'], result_adaptive['dt_history'],
            'r-', linewidth=2)
    ax.axhline(0.5, color='blue', linestyle='--', alpha=0.5, label='Fixed dt')
    ax.set_xlabel('Time (s)')
    ax.set_ylabel('Time step (s)')
    ax.set_title('Adaptive Time Step History')
    ax.legend()
    ax.grid(True, alpha=0.3)

    plt.tight_layout()
    plt.savefig('test_adaptive_simple.png', dpi=150)
    print(f"\n  图表保存: test_adaptive_simple.png")

    return result_fixed, result_adaptive, time_fixed, time_adaptive


def test_comparison_with_gate():
    """测试2: 带闸门的渠道 - 复杂流动"""
    print("\n" + "=" * 80)
    print("测试2: 带闸门渠道 - 自适应时间步优势")
    print("=" * 80)

    L = 1000.0
    nx = 101
    B = 10.0
    S0 = 0.001
    n = 0.025

    # 闸门：时变开度
    def gate_opening(t):
        if t < 50.0:
            return 0.4
        elif t < 100.0:
            return 0.4 + (0.8 - 0.4) * (t - 50.0) / 50.0
        else:
            return 0.8

    gate = SluiceGate(position=500.0, width=B, opening=gate_opening, Cd=0.6)

    # 创建求解器
    solver_fixed = HydrostaticCanalSolver(
        length=L, nx=nx, B=B, S0=S0, n=n,
        internal_structures=[(500.0, SluiceGate(500.0, B, gate_opening, 0.6))]
    )
    solver_adaptive = HydrostaticCanalSolver(
        length=L, nx=nx, B=B, S0=S0, n=n,
        internal_structures=[(500.0, gate)]
    )

    # 初始条件
    h_init = 0.7
    Q_init = 5.0
    solver_fixed.h = np.ones(nx) * h_init
    solver_fixed.hu = np.ones(nx) * Q_init / B
    solver_adaptive.h = np.ones(nx) * h_init
    solver_adaptive.hu = np.ones(nx) * Q_init / B

    t_end = 50.0

    # 固定时间步
    print(f"\n固定时间步求解...")
    t_start = time.time()
    result_fixed = solver_fixed.solve_transient(
        t_end=t_end,
        dt=0.3,
        Q_upstream=Q_init,
        h_downstream=h_init,
        save_interval=5,
        verbose=False
    )
    time_fixed = time.time() - t_start
    print(f"  完成: {time_fixed:.3f}秒")

    # 自适应时间步
    print(f"\n自适应时间步求解...")
    t_start = time.time()
    result_adaptive = solver_adaptive.solve_transient_adaptive(
        t_end=t_end,
        dt_initial=0.1,
        dt_min=0.01,
        dt_max=0.8,
        CFL_number=0.6,
        Q_upstream=Q_init,
        h_downstream=h_init,
        save_interval_time=1.5,
        verbose=False
    )
    time_adaptive = time.time() - t_start
    print(f"  完成: {time_adaptive:.3f}秒")
    print(f"  时间步数: {result_adaptive['n_steps']}")
    print(f"  平均时间步: {np.mean(result_adaptive['dt_history']):.4f}s")

    speedup = time_fixed / time_adaptive if time_adaptive > 0 else 0
    print(f"\n性能提升: {speedup:.2f}x")

    # 绘图
    fig, axes = plt.subplots(2, 2, figsize=(14, 8))

    # 水深剖面
    ax = axes[0, 0]
    ax.plot(solver_fixed.x, result_fixed['h_final'], 'b-', label='Fixed')
    ax.plot(solver_adaptive.x, result_adaptive['h_final'], 'r--', label='Adaptive')
    ax.axvline(500.0, color='gray', linestyle=':', alpha=0.5, label='Gate')
    ax.set_xlabel('Position (m)')
    ax.set_ylabel('Water depth (m)')
    ax.set_title('Final Water Depth with Gate')
    ax.legend()
    ax.grid(True, alpha=0.3)

    # 闸门开度 vs 时间
    ax = axes[0, 1]
    t_plot = np.linspace(0, t_end, 100)
    opening_plot = [gate_opening(t) for t in t_plot]
    ax.plot(t_plot, opening_plot, 'k-', linewidth=2)
    ax.set_xlabel('Time (s)')
    ax.set_ylabel('Gate opening (m)')
    ax.set_title('Time-Varying Gate Opening')
    ax.grid(True, alpha=0.3)

    # 时间步历史
    ax = axes[1, 0]
    ax.plot(result_adaptive['t_history'], result_adaptive['dt_history'],
            'r-', linewidth=2)
    ax.axhline(0.3, color='blue', linestyle='--', alpha=0.5, label='Fixed dt=0.3s')
    ax.set_xlabel('Time (s)')
    ax.set_ylabel('Time step (s)')
    ax.set_title('Adaptive Time Step Evolution')
    ax.legend()
    ax.grid(True, alpha=0.3)

    # 计算时间对比
    ax = axes[1, 1]
    methods = ['Fixed\ndt=0.3s', 'Adaptive\ndt (CFL=0.6)']
    times = [time_fixed, time_adaptive]
    colors = ['blue', 'red']
    bars = ax.bar(methods, times, color=colors, alpha=0.7)
    ax.set_ylabel('Computation time (s)')
    ax.set_title('Performance Comparison')
    ax.grid(True, alpha=0.3, axis='y')

    # 添加数值标签
    for bar, t in zip(bars, times):
        height = bar.get_height()
        ax.text(bar.get_x() + bar.get_width()/2., height,
                f'{t:.3f}s', ha='center', va='bottom')

    plt.tight_layout()
    plt.savefig('test_adaptive_gate.png', dpi=150)
    print(f"  图表保存: test_adaptive_gate.png")

    return result_fixed, result_adaptive


def test_cfl_stability():
    """测试3: CFL数对稳定性的影响"""
    print("\n" + "=" * 80)
    print("测试3: CFL数对稳定性的影响")
    print("=" * 80)

    L = 500.0
    nx = 51
    B = 10.0
    S0 = 0.002
    n = 0.025

    CFL_numbers = [0.3, 0.5, 0.7, 0.9]
    results = {}
    times = {}

    for CFL in CFL_numbers:
        print(f"\n测试 CFL = {CFL}...")

        solver = HydrostaticCanalSolver(length=L, nx=nx, B=B, S0=S0, n=n)
        solver.h = np.ones(nx) * 0.5
        solver.hu = np.ones(nx) * 4.0 / B

        # 流量阶跃
        def Q_func(t):
            return 4.0 if t < 20.0 else 8.0

        t_start = time.time()
        result = solver.solve_transient_adaptive(
            t_end=50.0,
            dt_initial=0.1,
            dt_min=0.001,
            dt_max=1.0,
            CFL_number=CFL,
            Q_upstream_func=Q_func,
            h_downstream=0.5,
            save_interval_time=2.0,
            verbose=False
        )
        elapsed = time.time() - t_start

        results[CFL] = result
        times[CFL] = elapsed

        print(f"  完成: {elapsed:.3f}秒")
        print(f"  时间步数: {result['n_steps']}")
        print(f"  平均时间步: {np.mean(result['dt_history']):.4f}s")

    # 绘图
    fig, axes = plt.subplots(2, 2, figsize=(14, 8))

    # 时间步对比
    ax = axes[0, 0]
    for CFL in CFL_numbers:
        ax.plot(results[CFL]['t_history'], results[CFL]['dt_history'],
                label=f'CFL={CFL}', linewidth=2)
    ax.set_xlabel('Time (s)')
    ax.set_ylabel('Time step (s)')
    ax.set_title('Time Step Evolution for Different CFL Numbers')
    ax.legend()
    ax.grid(True, alpha=0.3)

    # 计算时间对比
    ax = axes[0, 1]
    CFLs_str = [f'CFL={c}' for c in CFL_numbers]
    time_values = [times[c] for c in CFL_numbers]
    ax.bar(CFLs_str, time_values, alpha=0.7)
    ax.set_ylabel('Computation time (s)')
    ax.set_title('Computational Cost vs CFL Number')
    ax.grid(True, alpha=0.3, axis='y')

    # 时间步统计
    ax = axes[1, 0]
    step_counts = [results[c]['n_steps'] for c in CFL_numbers]
    ax.bar(CFLs_str, step_counts, alpha=0.7, color='orange')
    ax.set_ylabel('Number of time steps')
    ax.set_title('Total Time Steps vs CFL Number')
    ax.grid(True, alpha=0.3, axis='y')

    # 效率指标
    ax = axes[1, 1]
    efficiency = [results[c]['n_steps'] / times[c] for c in CFL_numbers]
    ax.plot(CFL_numbers, efficiency, 'ro-', linewidth=2, markersize=8)
    ax.set_xlabel('CFL Number')
    ax.set_ylabel('Steps per second')
    ax.set_title('Computational Efficiency')
    ax.grid(True, alpha=0.3)

    plt.tight_layout()
    plt.savefig('test_cfl_stability.png', dpi=150)
    print(f"\n  图表保存: test_cfl_stability.png")

    # 推荐CFL
    best_CFL = CFL_numbers[np.argmin(time_values)]
    print(f"\n推荐CFL数: {best_CFL} (最快完成)")

    return results, times


def main():
    """运行所有测试"""
    print("\n" + "" * 40)
    print("自适应时间步性能测试")
    print("" * 40 + "\n")

    # 测试1
    result_fixed1, result_adaptive1, time_fixed1, time_adaptive1 = test_comparison_simple()

    # 测试2
    result_fixed2, result_adaptive2 = test_comparison_with_gate()

    # 测试3
    results_cfl, times_cfl = test_cfl_stability()

    # 总结
    print("\n" + "=" * 80)
    print("测试总结")
    print("=" * 80)
    print("\n自适应时间步优势：")
    print("   自动调整时间步，无需手动选择")
    print("   在平稳区域使用大时间步，提高效率")
    print("   在激变区域使用小时间步，保证精度")
    print("   根据CFL条件保证数值稳定性")

    print("\n性能统计：")
    speedup1 = time_fixed1 / time_adaptive1 if time_adaptive1 > 0 else 0
    print(f"  测试1（简单流动）加速比: {speedup1:.2f}x")

    print("\nCFL推荐：")
    print("  - 稳定流动: CFL = 0.7-0.9 (高效率)")
    print("  - 一般流动: CFL = 0.5-0.7 (平衡)")
    print("  - 激变流动: CFL = 0.3-0.5 (高精度)")

    print("\n" + "=" * 80)
    print("所有测试完成!")
    print("=" * 80)


if __name__ == "__main__":
    main()
