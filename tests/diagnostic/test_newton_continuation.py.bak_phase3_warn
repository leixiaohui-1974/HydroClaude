#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
测试牛顿法 + 延拓策略

使用伪时间延拓逐渐逼近稳态解
"""

import numpy as np
import sys
import time

sys.path.insert(0, '.')

from physics.steady_saint_venant import SteadySaintVenantSystem
try:
    from solvers.newton_solver import NewtonSolver
except ImportError as e:
    print(f"Import error: {e}")
    print("Make sure project root is in sys.path")
    sys.exit(1)

from utils.canal_utils import compute_steady_uniform_flow

print('='*80)
print('牛顿法 + 伪时间延拓策略')
print('='*80)

# 测试参数
length = 1000.0
nx = 51
B = 10.0
S0 = 0.001
n = 0.025
Q_target = 10.0

# 计算均匀流
h_uniform = compute_steady_uniform_flow(Q_target, B, S0, n)

print(f'\n系统配置:')
print(f'  渠道长度: {length} m')
print(f'  节点数: {nx}')
print(f'  目标流量: {Q_target} m^3/s')
print(f'  均匀流水深: {h_uniform:.3f} m')

# 延拓策略：从大的pseudo_dt逐渐减小到0
pseudo_dt_values = [1.0, 0.1, 0.01, 0.001]

print(f'\n延拓策略: pseudo_dt = {pseudo_dt_values}')

# 初值
h_init = np.ones(nx) * h_uniform * 1.1
Q_init = np.ones(nx) * Q_target * 1.1

for i, pseudo_dt in enumerate(pseudo_dt_values):
    print(f'\n{"="*60}')
    print(f'延拓步骤 {i+1}/{len(pseudo_dt_values)}: pseudo_dt = {pseudo_dt}')
    print(f'{"="*60}')

    # 创建系统（使用当前的pseudo_dt）
    system = SteadySaintVenantSystem(
        length, nx, B, S0, n,
        pseudo_dt=pseudo_dt
    )

    # 设置边界条件
    system.set_boundary_conditions(
        Q_upstream=Q_target,
        h_upstream=h_uniform,
        h_downstream=h_uniform
    )

    # 使用上一步的解作为初值
    U_init = system.pack_state(h_init, Q_init)

    # 验证Jacobian
    J = system.compute_jacobian(U_init)
    rank = np.linalg.matrix_rank(J.toarray())
    print(f'Jacobian秩: {rank}/{2*nx}  满秩: {rank == 2*nx}')

    # 牛顿法求解
    solver = NewtonSolver(
        max_iter=30,
        tol_residual=1e-8,
        verbose=False
    )

    start_time = time.time()
    U_solution, info = solver.solve(
        U_init,
        system.compute_residual,
        system.compute_jacobian
    )
    solve_time = time.time() - start_time

    print(f'收敛: {info["converged"]:5}  迭代: {info["iterations"]:3}  '
          f'残差: {info["residual_norm"]:.2e}  时间: {solve_time*1000:.1f}ms')

    if info['converged']:
        # 使用当前解作为下一步的初值
        h_init, Q_init = system.unpack_state(U_solution)
        print(f'SUCCESS: 本步骤收敛，继续下一步')
    else:
        print(f'FAILURE: 本步骤未收敛，延拓终止')
        break

# 最终验证
print(f'\n{"="*80}')
print(f'最终结果验证')
print(f'{"="*80}')

h_sol, Q_sol = system.unpack_state(U_solution)

print(f'\n解的物理检查:')
print(f'  水深范围: [{h_sol.min():.3f}, {h_sol.max():.3f}] m')
print(f'  流量范围: [{Q_sol.min():.3f}, {Q_sol.max():.3f}] m^3/s')
print(f'  水深偏差: {np.abs(h_sol - h_uniform).max():.2e} m')
print(f'  流量偏差: {np.abs(Q_sol - Q_target).max():.2e} m^3/s')

# 检查是否接近均匀流
if np.allclose(h_sol, h_uniform, atol=1e-3) and np.allclose(Q_sol, Q_target, atol=1e-3):
    print(f'\nSUCCESS: 解与理论均匀流一致！')
    print(f'SUCCESS: 牛顿法 + 延拓策略有效！')
else:
    print(f'\nWARNING: 解与理论均匀流存在偏差')

print('='*80)
