#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
测试混合求解器 - 简单场景

作者: Claude
日期: 2025-10-22
"""

import sys, os
import warnings
warnings.filterwarnings("ignore")
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import numpy as np
from physics.steady_saint_venant import SteadySaintVenantSystem
try:
    from solvers.hybrid_solver import HybridSolver
except ImportError as e:
    print(f"Import error: {e}")
    print("Make sure project root is in sys.path")
    sys.exit(1)

from solvers.gate import SluiceGate
from utils.canal_utils import compute_steady_uniform_flow


def test_simple_gate():
    """测试单闸门场景"""

    print("=" * 100)
    print("混合求解器测试 - 单闸门")
    print("=" * 100)
    print()

    # 简单场景
    length = 1000.0
    nx = 51
    B = 10.0
    S0 = 0.001
    n = 0.025
    Q_target = 10.0

    gate = SluiceGate(position=500.0, width=B, opening=5.0, Cd=0.6)
    h_uniform = compute_steady_uniform_flow(Q_target, B, S0, n)

    print(f"场景: 单闸门")
    print(f"  网格: {nx}点, {length}m")
    print(f"  流量: {Q_target} m^3/s")
    print(f"  均匀流水深: {h_uniform:.4f} m")
    print()

    # 创建系统
    system = SteadySaintVenantSystem(
        length, nx, B, S0, n,
        structures=[(gate.position, gate)],
        pseudo_dt=1.0  # 更大的pseudo_dt
    )
    system.set_boundary_conditions(
        Q_upstream=Q_target,
        h_upstream=h_uniform,
        h_downstream=h_uniform
    )

    # 初值均匀流
    h_init = np.ones(nx) * h_uniform
    Q_init = np.ones(nx) * Q_target
    U_init = system.pack_state(h_init, Q_init)
    system.U_prev = U_init.copy()

    # 混合求解器
    solver = HybridSolver(
        iter_max_iter=500,
        iter_tol=0.05,
        switch_threshold=0.15,  # 更宽松的切换阈值
        iter_min=5,
        newton_max_iter=20,
        newton_tol=1e-4,
        pseudo_dt=1.0,  # 更大的伪时间步
        verbose=True
    )

    U_sol, info = solver.solve(system, U_init, t=0.0)

    # 解析结果
    h_sol, Q_sol = system.unpack_state(U_sol)

    print("=" * 100)
    print("最终结果")
    print("=" * 100)
    print(f"  收敛: {'' if info['converged'] else ''}")
    print(f"  总迭代: {info['total_iterations']}")
    print(f"  总用时: {info['total_time']:.4f}s")
    print(f"  水深: {h_sol.min():.4f} - {h_sol.max():.4f} m")
    print(f"  流量: {Q_sol.min():.4f} - {Q_sol.max():.4f} m^3/s")
    print()

    # 对比纯Newton
    print("=" * 100)
    print("对比: 纯Newton求解")
    print("=" * 100)
    print()

    from solvers.newton_solver import NewtonSolver

    # 重新初始化系统
    system2 = SteadySaintVenantSystem(
        length, nx, B, S0, n,
        structures=[(gate.position, gate)],
        pseudo_dt=0.1
    )
    system2.set_boundary_conditions(
        Q_upstream=Q_target,
        h_upstream=h_uniform,
        h_downstream=h_uniform
    )
    system2.U_prev = U_init.copy()

    newton = NewtonSolver(
        max_iter=20,
        tol_residual=1e-4,
        verbose=True
    )

    import time
    start = time.time()
    U_newton, info_newton = newton.solve(
        U_init=U_init,
        residual_func=lambda U: system2.compute_residual(U, 0.0),
        jacobian_func=lambda U: system2.compute_jacobian(U, 0.0)
    )
    time_newton = time.time() - start

    h_newton, Q_newton = system2.unpack_state(U_newton)

    print()
    print(f"纯Newton结果:")
    print(f"  收敛: {'' if info_newton['converged'] else ''}")
    print(f"  迭代: {info_newton['iterations']}")
    print(f"  用时: {time_newton:.4f}s")
    print(f"  水深: {h_newton.min():.4f} - {h_newton.max():.4f} m")
    print(f"  流量: {Q_newton.min():.4f} - {Q_newton.max():.4f} m^3/s")
    print()


if __name__ == '__main__':
    test_simple_gate()
