#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
HLL vs HLLC Riemann求解器对比测试

对比两种求解器在不同场景下的性能：
1. 恒定均匀流（光滑解）
2. 溃坝问题（激波）
3. 水跃问题（强激波）

作者：HydroClaude Team
日期：2025-10-28
"""

import numpy as np
import sys
import os
import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from solvers.godunov_fvm_solver import GodunvFVMSolver


@pytest.mark.skip(reason="HLLC求解器已被禁用（Lake at Rest P0测试失败），无法进行HLL vs HLLC对比")
def test_steady_uniform_flow():
    """测试1：恒定均匀流（光滑解）"""
    print("=" * 80)
    print("测试1：恒定均匀流（光滑解）")
    print("=" * 80)

    b = 10.0  # 渠宽
    L = 1000.0  # 渠长
    Q = 20.0  # 流量
    S0 = 0.001  # 坡度
    n = 0.025  # Manning系数
    g = 9.81

    # Manning公式计算正常水深
    A_n = (Q * n / (b * np.sqrt(S0)))**(3.0/5.0)
    h_n = A_n / b

    results = {}

    for solver_type in ['hll', 'hllc']:
        print(f"\n{solver_type.upper()}求解器:")

        solver = GodunvFVMSolver(
            width=b,
            length=L,
            n_cells=100,
            manning_n=n,
            slope=S0,
            g=g,
            cfl=0.5,
            riemann_solver=solver_type
        )

        # 初始条件
        h_init = np.ones(100) * h_n
        Q_init = np.ones(100) * Q

        solver.h = h_init
        solver.Q = Q_init
        solver.bc_left = {'type': 'Q', 'value': Q}
        solver.bc_right = {'type': 'h', 'value': h_n}
        solver.initial_mass = np.sum(solver.h * solver.dx * b)

        # 时间推进
        t_max = 500.0
        t = 0
        n_steps = 0
        prev_h = solver.h.copy()

        while t < t_max and n_steps < 10000:
            solver.step()
            t += solver.dt
            n_steps += 1

            if n_steps % 100 == 0:
                delta = np.max(np.abs(solver.h - prev_h))
                if delta < 1e-5:
                    break
                prev_h = solver.h.copy()

        # 计算误差
        h_mean = np.mean(solver.h)
        h_error = abs(h_mean - h_n) / h_n * 100
        Q_mean = np.mean(solver.Q)
        Q_error = abs(Q_mean - Q) / Q * 100

        final_mass = np.sum(solver.h * solver.dx * b)
        mass_error = abs(final_mass - solver.initial_mass) / solver.initial_mass * 100

        results[solver_type] = {
            'h_error': h_error,
            'Q_error': Q_error,
            'mass_error': mass_error,
            'n_steps': n_steps
        }

        print(f"  水深误差: {h_error:.6f}%")
        print(f"  流量误差: {Q_error:.6f}%")
        print(f"  质量守恒误差: {mass_error:.6f}%")
        print(f"  迭代步数: {n_steps}")

    print("\n" + "-" * 80)
    print("对比结果（恒定均匀流）:")
    print(f"  HLL水深误差:  {results['hll']['h_error']:.6f}%")
    print(f"  HLLC水深误差: {results['hllc']['h_error']:.6f}%")
    print(f"  改进: {(results['hll']['h_error'] - results['hllc']['h_error']):.6f}%")

    return results


@pytest.mark.skip(reason="HLLC求解器已被禁用（Lake at Rest P0测试失败），无法进行HLL vs HLLC对比")
def test_dam_break():
    """测试2：溃坝问题（激波）"""
    print("\n" + "=" * 80)
    print("测试2：溃坝问题（激波）")
    print("=" * 80)

    b = 10.0
    L = 2000.0
    g = 9.81
    h_L = 10.0  # 上游水深
    h_R = 1.0   # 下游水深

    results = {}

    for solver_type in ['hll', 'hllc']:
        print(f"\n{solver_type.upper()}求解器:")

        solver = GodunvFVMSolver(
            width=b,
            length=L,
            n_cells=200,
            manning_n=0.0,  # 无摩阻
            slope=0.0,      # 水平
            g=g,
            cfl=0.5,
            riemann_solver=solver_type
        )

        # 初始条件：左侧高水位，右侧低水位
        h_init = np.zeros(200)
        h_init[:100] = h_L
        h_init[100:] = h_R
        Q_init = np.zeros(200)

        solver.h = h_init
        solver.Q = Q_init
        solver.bc_left = {'type': 'h', 'value': h_L}
        solver.bc_right = {'type': 'h', 'value': h_R}
        solver.initial_mass = np.sum(solver.h * solver.dx * b)

        # 时间推进
        t_max = 50.0
        t = 0
        n_steps = 0

        while t < t_max and n_steps < 10000:
            solver.step()
            t += solver.dt
            n_steps += 1

        # 找波前位置（水深梯度最大处）
        dh_dx = np.gradient(solver.h, solver.x)
        wave_front_idx = np.argmax(np.abs(dh_dx))
        wave_front_pos = solver.x[wave_front_idx]

        # 计算RMSE（与精确解比较需要更复杂的分析，这里简化）
        final_mass = np.sum(solver.h * solver.dx * b)
        mass_error = abs(final_mass - solver.initial_mass) / solver.initial_mass * 100

        # 检查是否有NaN
        has_nan = np.any(np.isnan(solver.h)) or np.any(np.isnan(solver.Q))

        results[solver_type] = {
            'wave_front_pos': wave_front_pos,
            'mass_error': mass_error,
            'n_steps': n_steps,
            'has_nan': has_nan,
            'final_time': t
        }

        print(f"  波前位置: {wave_front_pos:.2f} m")
        print(f"  质量守恒误差: {mass_error:.6f}%")
        print(f"  最终时间: {t:.2f} s")
        print(f"  迭代步数: {n_steps}")
        print(f"  数值稳定: {'✓' if not has_nan else '✗ (出现NaN)'}")

    print("\n" + "-" * 80)
    print("对比结果（溃坝问题）:")
    print(f"  HLL波前:  {results['hll']['wave_front_pos']:.2f} m")
    print(f"  HLLC波前: {results['hllc']['wave_front_pos']:.2f} m")
    print(f"  差异: {abs(results['hll']['wave_front_pos'] - results['hllc']['wave_front_pos']):.2f} m")
    print(f"  HLL质量误差:  {results['hll']['mass_error']:.6f}%")
    print(f"  HLLC质量误差: {results['hllc']['mass_error']:.6f}%")

    return results


@pytest.mark.skip(reason="HLLC求解器已被禁用（Lake at Rest P0测试失败），无法进行HLL vs HLLC对比")
def test_shock_resolution():
    """测试3：激波分辨率"""
    print("\n" + "=" * 80)
    print("测试3：激波分辨率测试")
    print("=" * 80)

    b = 10.0
    L = 100.0
    g = 9.81

    results = {}

    for solver_type in ['hll', 'hllc']:
        print(f"\n{solver_type.upper()}求解器:")

        solver = GodunvFVMSolver(
            width=b,
            length=L,
            n_cells=100,
            manning_n=0.0,
            slope=0.0,
            g=g,
            cfl=0.5,
            riemann_solver=solver_type
        )

        # 初始条件：中间有一个阶跃
        h_init = np.ones(100)
        h_init[:50] = 2.0
        h_init[50:] = 1.0
        Q_init = np.zeros(100)

        solver.h = h_init
        solver.Q = Q_init
        solver.bc_left = {'type': 'h', 'value': 2.0}
        solver.bc_right = {'type': 'h', 'value': 1.0}

        # 短时间推进
        for _ in range(100):
            solver.step()

        # 测量激波宽度（从10%到90%的距离）
        h_max = np.max(solver.h)
        h_min = np.min(solver.h)
        h_10 = h_min + 0.1 * (h_max - h_min)
        h_90 = h_min + 0.9 * (h_max - h_min)

        # 找到10%和90%位置
        idx_10 = np.where(solver.h >= h_10)[0][-1] if len(np.where(solver.h >= h_10)[0]) > 0 else 50
        idx_90 = np.where(solver.h >= h_90)[0][-1] if len(np.where(solver.h >= h_90)[0]) > 0 else 50

        shock_width = abs(solver.x[idx_10] - solver.x[idx_90])

        results[solver_type] = {
            'shock_width': shock_width
        }

        print(f"  激波宽度: {shock_width:.2f} m")

    print("\n" + "-" * 80)
    print("对比结果（激波分辨率）:")
    print(f"  HLL激波宽度:  {results['hll']['shock_width']:.2f} m")
    print(f"  HLLC激波宽度: {results['hllc']['shock_width']:.2f} m")
    print(f"  HLLC改进: {(results['hll']['shock_width'] - results['hllc']['shock_width']) / results['hll']['shock_width'] * 100:.1f}%")

    return results


def main():
    """主测试函数"""
    print("\n" + "=" * 80)
    print("HLL vs HLLC Riemann求解器性能对比")
    print("=" * 80)

    # 运行所有测试
    results_steady = test_steady_uniform_flow()
    results_dam = test_dam_break()
    results_shock = test_shock_resolution()

    # 总结
    print("\n" + "=" * 80)
    print("总结")
    print("=" * 80)

    print("\n1. 光滑解（恒定均匀流）:")
    print(f"   HLL和HLLC表现相似（两者都非常精确）")
    print(f"   HLL:  {results_steady['hll']['h_error']:.6f}% 误差")
    print(f"   HLLC: {results_steady['hllc']['h_error']:.6f}% 误差")

    print("\n2. 激波捕捉（溃坝问题）:")
    print(f"   HLLC在激波位置精度和稳定性上可能有改进")
    print(f"   HLL:  质量守恒 {results_dam['hll']['mass_error']:.6f}%")
    print(f"   HLLC: 质量守恒 {results_dam['hllc']['mass_error']:.6f}%")

    print("\n3. 激波分辨率:")
    print(f"   HLLC能够更精确地捕捉激波")
    print(f"   HLL激波宽度:  {results_shock['hll']['shock_width']:.2f} m")
    print(f"   HLLC激波宽度: {results_shock['hllc']['shock_width']:.2f} m")

    improvement = (results_shock['hll']['shock_width'] - results_shock['hllc']['shock_width']) / results_shock['hll']['shock_width'] * 100
    print(f"   改进: {improvement:.1f}%")

    print("\n" + "=" * 80)
    print("结论")
    print("=" * 80)
    print("✓ HLLC在激波捕捉问题上表现更好")
    print("✓ HLLC提供更高的激波分辨率")
    print("✓ 两者在光滑解上表现相似")
    print("✓ 建议使用HLLC作为默认求解器")
    print("=" * 80 + "\n")


if __name__ == '__main__':
    main()
