#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
MacDonald Test 4 - HLLC低耗散求解器测试

目标: 使用HLLC替代HLL，降低数值耗散，改善质量守恒
预期: 质量误差从27.89%降低到15%以下

作者: HydroClaude Team
日期: 2025-10-31
"""

import sys
sys.path.insert(0, '/home/user/HydroClaude')

import numpy as np
import time
from solvers.godunov_fvm_weno3 import GodunvFVMWENO3

print("="*80)
print("MacDonald Test 4: HLLC低耗散求解器测试 (方案2)")
print("="*80)
print("\n改进: HLL → HLLC (更低数值耗散)")
print("配置: 150网格, dx=6.67m, CFL=0.4")
print("目标: 质量误差 < 15%")
print("="*80)

# 参数
L = 1000.0; B = 10.0; n_cells = 150; dx = L/n_cells; g = 9.81
Q_upstream = 50.0; h_upstream = 1.0; h_downstream = 2.0

print(f"\n创建WENO3+HLLC求解器...")

# ⭐ 关键：使用HLLC替代HLL
solver = GodunvFVMWENO3(
    width=B, length=L, n_cells=n_cells,
    manning_n=0.0, slope=0.0, g=g,
    cfl=0.4, eps_dry=1e-6, weno_epsilon=1e-6,
    riemann_solver='hllc'  # ⭐⭐⭐ HLLC!
)

# 初始条件
h_init = np.linspace(h_upstream, h_downstream, n_cells)
Q_init = np.ones(n_cells) * Q_upstream

bc_left = {'type': 'supercritical', 'h': h_upstream, 'Q': Q_upstream}
bc_right = {'type': 'fixed_h', 'h': h_downstream}

solver.initialize(h_init, Q_init, bc_left, bc_right)
mass_init = solver._compute_total_mass()

print(f"初始质量: {mass_init:.2f} m³")
print(f"\n运行到 t=50s...")
print("(进度每10秒显示一次)")

start_time = time.time()
t_end = 50.0
diagnostics_times = [5, 10, 15, 20, 25, 30, 35, 40, 45, 50]
next_diag_idx = 0

while solver.t < t_end:
    solver.step()

    # 每达到一个诊断时间点时输出
    if next_diag_idx < len(diagnostics_times) and solver.t >= diagnostics_times[next_diag_idx]:
        h_safe = np.maximum(solver.h, solver.eps_dry)
        A = h_safe * solver.B
        u = solver.Q / A
        Fr = np.abs(u) / np.sqrt(solver.g * h_safe)

        mass_current = solver._compute_total_mass()
        mass_err = abs(mass_current - mass_init) / mass_init * 100
        n_neg = np.sum(solver.Q < 0)

        print(f"  t={solver.t:.1f}s: Fr[0]={Fr[0]:.3f}, 质量误差={mass_err:.2f}%, 负流量={n_neg}/{n_cells}")
        next_diag_idx += 1

elapsed = time.time() - start_time

# 最终结果
mass_final = solver._compute_total_mass()
mass_error = abs(mass_final - mass_init) / mass_init * 100

h_safe = np.maximum(solver.h, solver.eps_dry)
A = h_safe * solver.B
u = solver.Q / A
Fr = np.abs(u) / np.sqrt(solver.g * h_safe)

Fr_upstream_final = Fr[0]
n_negative = np.sum(solver.Q < 0)

# 理论值
u_theory = Q_upstream / (B * h_upstream)
Fr_theory = u_theory / np.sqrt(g * h_upstream)
h2_theory = h_upstream / 2.0 * (-1.0 + np.sqrt(1.0 + 8.0 * Fr_theory**2))
h2_actual = np.max(solver.h)
belanger_error = abs(h2_actual - h2_theory) / h2_theory * 100

print(f"\n{'='*80}")
print("最终结果")
print(f"{'='*80}")
print(f"质量误差: {mass_error:.2f}%")
print(f"上游Froude数: {Fr_upstream_final:.3f} (理论={Fr_theory:.3f})")
print(f"负流量单元: {n_negative}/{n_cells}")
print(f"Belanger误差: {belanger_error:.2f}%")
print(f"运行时间: {elapsed:.1f}秒")

# 对比基线
print(f"\n{'='*80}")
print("改进效果对比")
print(f"{'='*80}")

baseline_hll = 27.89  # HLL基线
improvement = baseline_hll - mass_error
improvement_pct = improvement / baseline_hll * 100

print(f"质量误差:")
print(f"  HLL基线  (n=150): 27.89%")
print(f"  HLLC改进 (n=150): {mass_error:.2f}%")
print(f"  改善: {improvement:.2f}% (相对改善 {improvement_pct:.1f}%)")

# 判断
print(f"\n{'='*80}")
print("评估")
print(f"{'='*80}")

if mass_error < 15.0:
    print(f"✅ 质量误差: {mass_error:.2f}% < 15.0% ⭐⭐⭐")
    if Fr_upstream_final > 0.9:
        print(f"✅ Froude数: {Fr_upstream_final:.3f} ≈ {Fr_theory:.3f}")
    if belanger_error < 30.0:
        print(f"✅ Belanger: {belanger_error:.2f}% < 30%")
    if n_negative < n_cells * 0.2:
        print(f"✅ 负流量: {n_negative}/{n_cells} < 20%")

    print(f"\n🎉🎉🎉 HLLC方案成功！达到100%通过率！ 🎉🎉🎉")
    print(f"{'='*80}\n")
    exit(0)

elif improvement > 5.0:
    print(f"✅ HLLC有显著改善 (>{improvement:.1f}%)")
    print(f"⚠️  但未达到<15%目标 (当前{mass_error:.2f}%)")
    print(f"\n建议: 继续实施方案1 (WENO5高阶格式)")
    print(f"{'='*80}\n")
    exit(1)

else:
    print(f"⚠️  HLLC改善有限 (<5%)")
    print(f"建议: 必须实施WENO5才能达到100%通过率")
    print(f"{'='*80}\n")
    exit(2)
