#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""快速验证牛顿法边界条件修复"""

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
print('牛顿法边界条件修复 - 收敛性验证')
print('='*80)

# 测试参数
length = 1000.0
nx = 51
B = 10.0
S0 = 0.001
n = 0.025
Q_target = 10.0

# 创建系统
system = SteadySaintVenantSystem(length, nx, B, S0, n)
h_uniform = compute_steady_uniform_flow(Q_target, B, S0, n)

print(f'\n系统配置:')
print(f'  渠道长度: {length} m')
print(f'  节点数: {nx}')
print(f'  目标流量: {Q_target} m^3/s')
print(f'  均匀流水深: {h_uniform:.3f} m')

# 设置边界条件（关键：同时指定Q和h）
system.set_boundary_conditions(
    Q_upstream=Q_target,
    h_upstream=h_uniform,
    h_downstream=h_uniform
)

# 初值
h_init = np.ones(nx) * h_uniform * 1.1
Q_init = np.ones(nx) * Q_target * 1.1
U_init = system.pack_state(h_init, Q_init)

# 验证Jacobian满秩
print(f'\nJacobian验证:')
J = system.compute_jacobian(U_init)
rank = np.linalg.matrix_rank(J.toarray())
cond = np.linalg.cond(J.toarray())
print(f'  Jacobian秩: {rank}/{2*nx}')
print(f'  满秩: {"YES" if rank == 2*nx else "NO"}')
print(f'  条件数: {cond:.2e}')

# 牛顿法求解
print(f'\n牛顿法求解:')
solver = NewtonSolver(max_iter=20, tol_residual=1e-8, verbose=True)

start_time = time.time()
U_solution, info = solver.solve(
    U_init,
    system.compute_residual,
    system.compute_jacobian
)
solve_time = time.time() - start_time

print(f'\n求解结果:')
print(f'  收敛: {"YES" if info["converged"] else "NO"}')
print(f'  迭代次数: {info["iterations"]}')
print(f'  最终残差: {info["residual_norm"]:.2e}')
print(f'  求解时间: {solve_time*1000:.2f} ms')

if info['converged']:
    h_sol, Q_sol = system.unpack_state(U_solution)
    print(f'\n解的物理检查:')
    print(f'  水深范围: [{h_sol.min():.3f}, {h_sol.max():.3f}] m')
    print(f'  流量范围: [{Q_sol.min():.3f}, {Q_sol.max():.3f}] m^3/s')
    print(f'  水深偏差: {np.abs(h_sol - h_uniform).max():.2e} m')
    print(f'  流量偏差: {np.abs(Q_sol - Q_target).max():.2e} m^3/s')

    if info['iterations'] <= 10:
        print(f'\nSUCCESS: 牛顿法快速收敛！({info["iterations"]}次迭代)')
        print(f'SUCCESS: Jacobian满秩修复成功！')
    else:
        print(f'\nWARNING: 收敛较慢 ({info["iterations"]}次迭代)')
else:
    print(f'\nFAILURE: 牛顿法未收敛')

print('='*80)
