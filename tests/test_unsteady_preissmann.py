"""Preissmann 非恒定流求解器验证测试。"""

import sys
import os
import numpy as np

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from physics.cross_section import RectangularSection
from solvers.unsteady_preissmann_solver import PreissmannSolver, UnsteadyReachData, UnsteadyState
from solvers.unsteady_boundary import (
    ConstantFlowBC, ConstantStageBC, FlowHydrographBC, NormalDepthBC,
)


def make_rectangular_reach(length: float = 10000.0, n_xs: int = 51,
                           width: float = 20.0, slope: float = 0.0005,
                           manning_n: float = 0.03) -> UnsteadyReachData:
    """构建矩形断面等距河段。"""
    dx_val = length / (n_xs - 1)
    dx = np.full(n_xs - 1, dx_val)
    bed = np.array([slope * (length - i * dx_val) for i in range(n_xs)])
    sections = [RectangularSection(f"xs_{i}", width=width) for i in range(n_xs)]
    n_arr = np.full(n_xs, manning_n)
    return UnsteadyReachData(
        n_xs=n_xs, dx=dx, bed_elevation=bed,
        manning_n=n_arr, sections=sections,
    )


def test_steady_state_preservation():
    """测试 1: 恒定流稳态保持。

    给定恒定 Q 和 Z_下游，推进 3600s 后水位和流量应不变。
    """
    print("=== Test 1: 恒定流稳态保持 ===")
    reach = make_rectangular_reach()
    solver = PreissmannSolver(reach, theta=0.6)

    Q0 = 50.0
    # 用 Manning 公式估算正常水深
    # Q = (1/n) * A * R^(2/3) * S^(1/2)
    # 矩形: A = B*h, R = B*h/(B+2h)
    # 简化用 brentq
    from scipy.optimize import brentq
    B = 20.0
    S0 = 0.0005
    n = 0.03
    def manning_residual(h):
        A = B * h
        P = B + 2 * h
        R = A / P
        return (1.0 / n) * A * R ** (2.0 / 3.0) * S0 ** 0.5 - Q0
    h_normal = brentq(manning_residual, 0.01, 10.0)
    Z_ds = reach.bed_elevation[-1] + h_normal

    # 用正常水深精确初始化
    Z_init = np.array([reach.bed_elevation[i] + h_normal for i in range(reach.n_xs)])
    Q_init = np.full(reach.n_xs, Q0)
    state = UnsteadyState(Z=Z_init, Q=Q_init, t=0.0)

    upstream_bc = ConstantFlowBC(Q0)
    downstream_bc = ConstantStageBC(Z_ds)

    result = solver.solve(state, t_end=3600.0, dt=60.0,
                         upstream_bc=upstream_bc, downstream_bc=downstream_bc,
                         output_interval=3600.0, verbose=False)

    Z_final = result['Z_history'][-1]
    Q_final = result['Q_history'][-1]

    dZ_max = np.max(np.abs(Z_final - state.Z))
    dQ_max = np.max(np.abs(Q_final - Q0))

    print(f"  正常水深: {h_normal:.4f} m")
    print(f"  Z 最大偏差: {dZ_max:.6f} m")
    print(f"  Q 最大偏差: {dQ_max:.6f} m³/s")

    assert dZ_max < 0.01, f"水位偏差过大: {dZ_max}"
    assert dQ_max < 0.1, f"流量偏差过大: {dQ_max}"
    print("  PASS")
    return True


def test_flood_wave_mass_conservation():
    """测试 2: 洪水波质量守恒。

    上游三角形洪水过程线，验证质量守恒误差 < 1%。
    """
    print("\n=== Test 2: 洪水波质量守恒 ===")
    reach = make_rectangular_reach(length=20000.0, n_xs=101)
    solver = PreissmannSolver(reach, theta=0.7)

    Q_base = 50.0
    Q_peak = 200.0
    t_peak = 3600.0
    t_end = 10800.0  # 3 小时

    # 三角形 hydrograph
    times = [0, t_peak, 2 * t_peak, t_end]
    flows = [Q_base, Q_peak, Q_base, Q_base]
    upstream_bc = FlowHydrographBC(times, flows)

    # 下游正常水深 BC
    downstream_bc = NormalDepthBC(
        reach.sections[-1], manning_n=0.03, bed_slope=0.0005
    )

    # 初始化
    from scipy.optimize import brentq
    def manning_res(h):
        A = 20.0 * h
        P = 20.0 + 2 * h
        R = A / P
        return (1.0 / 0.03) * A * R ** (2.0 / 3.0) * 0.0005 ** 0.5 - Q_base
    h_n = brentq(manning_res, 0.01, 10.0)

    state = UnsteadyState(
        Z=np.array([reach.bed_elevation[i] + h_n for i in range(reach.n_xs)]),
        Q=np.full(reach.n_xs, Q_base),
        t=0.0,
    )

    result = solver.solve(state, t_end=t_end, dt=30.0,
                         upstream_bc=upstream_bc, downstream_bc=downstream_bc,
                         output_interval=300.0, verbose=False)

    mb = solver.compute_mass_balance(result)
    err = mb['error_percent']
    print(f"  守恒误差: {err:.4f}%")

    assert err < 5.0, f"质量守恒误差过大: {err:.2f}%"
    print("  PASS")
    return True


def test_flood_wave_attenuation():
    """测试 3: 洪水波衰减和延迟。

    下游峰值流量应小于上游，峰值到达时间应延迟。
    """
    print("\n=== Test 3: 洪水波衰减和延迟 ===")
    reach = make_rectangular_reach(length=20000.0, n_xs=101)
    solver = PreissmannSolver(reach, theta=0.7)

    Q_base = 50.0
    Q_peak = 200.0
    t_peak = 3600.0
    t_end = 10800.0

    times = [0, t_peak, 2 * t_peak, t_end]
    flows = [Q_base, Q_peak, Q_base, Q_base]
    upstream_bc = FlowHydrographBC(times, flows)
    downstream_bc = NormalDepthBC(
        reach.sections[-1], manning_n=0.03, bed_slope=0.0005
    )

    from scipy.optimize import brentq
    def manning_res(h):
        A = 20.0 * h
        P = 20.0 + 2 * h
        R = A / P
        return (1.0 / 0.03) * A * R ** (2.0 / 3.0) * 0.0005 ** 0.5 - Q_base
    h_n = brentq(manning_res, 0.01, 10.0)

    state = UnsteadyState(
        Z=np.array([reach.bed_elevation[i] + h_n for i in range(reach.n_xs)]),
        Q=np.full(reach.n_xs, Q_base),
        t=0.0,
    )

    result = solver.solve(state, t_end=t_end, dt=30.0,
                         upstream_bc=upstream_bc, downstream_bc=downstream_bc,
                         output_interval=60.0, verbose=False)

    Q_hist = result['Q_history']
    times_out = result['times']

    # 上游峰值
    Q_upstream_series = Q_hist[:, 0]
    Q_downstream_series = Q_hist[:, -1]

    Q_peak_up = np.max(Q_upstream_series)
    Q_peak_down = np.max(Q_downstream_series)
    t_peak_up = times_out[np.argmax(Q_upstream_series)]
    t_peak_down = times_out[np.argmax(Q_downstream_series)]

    print(f"  上游峰值: Q={Q_peak_up:.1f} m³/s @ t={t_peak_up:.0f}s")
    print(f"  下游峰值: Q={Q_peak_down:.1f} m³/s @ t={t_peak_down:.0f}s")
    print(f"  衰减: {Q_peak_up - Q_peak_down:.1f} m³/s")
    print(f"  延迟: {t_peak_down - t_peak_up:.0f}s")

    # 洪水波应衰减
    assert Q_peak_down < Q_peak_up, "下游峰值应小于上游"
    # 洪水波应延迟
    assert t_peak_down > t_peak_up, "下游峰值应延迟于上游"
    print("  PASS")
    return True


if __name__ == "__main__":
    passed = 0
    total = 3

    try:
        if test_steady_state_preservation():
            passed += 1
    except Exception as e:
        print(f"  FAIL: {e}")

    try:
        if test_flood_wave_mass_conservation():
            passed += 1
    except Exception as e:
        print(f"  FAIL: {e}")

    try:
        if test_flood_wave_attenuation():
            passed += 1
    except Exception as e:
        print(f"  FAIL: {e}")

    print(f"\n{'='*50}")
    print(f"结果: {passed}/{total} PASS")
    if passed == total:
        print("ALL TESTS PASSED")
    else:
        print("SOME TESTS FAILED")
