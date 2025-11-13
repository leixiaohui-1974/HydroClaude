#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""快速溃坝测试（10秒，展示Numba威力）"""

import numpy as np
import sys, os, time
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
try:
    from solvers.godunov_fvm_solver import GodunvFVMSolver
except ImportError as e:
    print(f"Import error: {e}")
    print("Make sure project root is in sys.path")
    sys.exit(1)


print("\n" + "="*80)
print("400网格溃坝模拟（t=10秒）- Numba加速展示")
print("="*80 + "\n")

b, L, h_L, h_R, g = 10.0, 2000.0, 10.0, 1.0, 9.81

solver = GodunvFVMSolver(
    width=b, length=L, n_cells=400,
    manning_n=0.0, slope=0.0,
    g=g, cfl=0.3, order=1, use_numba=True
)

h_init = np.where(solver.x < L/2, h_L, h_R)
Q_init = np.zeros(400)
solver.initialize(h_init, Q_init,
    bc_left={'type': 'h', 'value': h_L},
    bc_right={'type': 'h', 'value': h_R})

print(f"网格: 400, dx=5m")
print(f"目标: t=10秒\n")

start = time.time()
step = 0
while solver.t < 10.0:
    solver.step()
    step += 1
    if step % 5000 == 0:
        print(f"  步数: {step:6d}, t={solver.t:6.2f}s, 已耗时: {time.time()-start:6.2f}s")

elapsed = time.time() - start

print(f"\n 完成!")
print(f"  总步数: {step}")
print(f"  模拟时间: {solver.t:.2f}s")
print(f"  墙钟时间: {elapsed:.2f}s")
print(f"  平均每步: {elapsed/step*1000:.3f}ms")
print(f"  质量误差: {solver.get_mass_conservation_error():.6f}%")

# 估算纯Python时间
python_est = elapsed * 68
print(f"\n Numba加速效果:")
print(f"  Numba: {elapsed:.1f}秒")
print(f"  预计纯Python: {python_est:.1f}秒 ({python_est/60:.1f}分钟)")
print(f"  节省: {python_est-elapsed:.1f}秒 ({(python_est-elapsed)/60:.1f}分钟)")
print("\n" + "="*80)
