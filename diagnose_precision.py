"""
精度问题精确诊断脚本

系统分析2.56%误差的真正来源

Author: Claude
Date: 2025-10-23
"""

import sys
import os
import numpy as np

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from solvers.single_canal_solver import SingleCanalSolver
from solvers.gate import SluiceGate

print("=" * 80)
print("精度问题精确诊断")
print("=" * 80)
print()

# 系统配置（与脚本11完全相同）
canal_length = 10000.0
canal_width = 10.0
n_points = 301
bed_slope = 0.0005
manning_n = 0.025
Q_initial = 10.0

# 三个闸门
gate1 = SluiceGate(position=2500.0, width=canal_width, opening=4.5, Cd=0.6)
gate2 = SluiceGate(position=5000.0, width=canal_width, opening=4.0, Cd=0.6)
gate3 = SluiceGate(position=7500.0, width=canal_width, opening=5.0, Cd=0.6)

print("配置:")
print(f"  渠道长度: {canal_length} m")
print(f"  网格点数: {n_points}")
print(f"  网格间距: dx = {canal_length/(n_points-1):.2f} m")
print(f"  目标流量: {Q_initial} m³/s")
print(f"  闸门数量: 3")
print()

# ==================== 测试1: 标准求解器（脚本11的方法）====================
print("=" * 80)
print("测试1: 标准求解器（与脚本11相同配置）")
print("=" * 80)

solver1 = SingleCanalSolver(
    total_length=canal_length,
    structures=[gate1, gate2, gate3],
    nx_total=n_points,
    B=canal_width,
    S0=bed_slope,
    n=manning_n
)

solver1.reset_with_steady_state(Q_initial)

# 使用与脚本11完全相同的参数
result1 = solver1.solve_steady_state(
    Q_target=Q_initial,
    max_iterations=5000,
    convergence_tol=0.001,  # 0.1%
    check_interval=500,
    verbose=True
)

profile1 = solver1.get_full_profile()
x1 = profile1['x']
Q1 = profile1['Q']

# 计算误差分布
Q1_error = np.abs(Q1 - Q_initial) / Q_initial * 100
Q1_max_error = np.max(Q1_error)
Q1_mean_error = np.mean(Q1_error)

print(f"\n标准求解器结果:")
print(f"  迭代次数: {result1['iterations']}")
print(f"  平均流量: {result1['Q_avg']:.6f} m³/s")
print(f"  最大相对误差: {Q1_max_error:.4f}%")
print(f"  平均相对误差: {Q1_mean_error:.4f}%")

# 分析误差分布
gate_flows = solver1.get_gate_flows()
print(f"\n闸门流量:")
for i, (gate, gf) in enumerate(zip([gate1, gate2, gate3], gate_flows)):
    error = abs(gf - Q_initial) / Q_initial * 100
    print(f"  闸门{i+1} (x={gate.position}m): Q={gf:.6f} m³/s, 误差={error:.4f}%")

# 找到最大误差的位置
max_error_idx = np.argmax(Q1_error)
print(f"\n最大误差位置:")
print(f"  位置: x={x1[max_error_idx]:.2f} m")
print(f"  流量: Q={Q1[max_error_idx]:.6f} m³/s")
print(f"  误差: {Q1_error[max_error_idx]:.4f}%")

# 分析不同区域的误差
regions = [
    ("上游段 (0-2500m)", 0, 2500),
    ("闸门1-2间 (2500-5000m)", 2500, 5000),
    ("闸门2-3间 (5000-7500m)", 5000, 7500),
    ("下游段 (7500-10000m)", 7500, 10000)
]

print(f"\n区域误差分析:")
for name, x_start, x_end in regions:
    mask = (x1 >= x_start) & (x1 <= x_end)
    region_error = Q1_error[mask]
    print(f"  {name}:")
    print(f"    平均误差: {np.mean(region_error):.4f}%")
    print(f"    最大误差: {np.max(region_error):.4f}%")

# ==================== 诊断: 收敛性分析 ====================
print(f"\n" + "=" * 80)
print("诊断: 收敛性分析")
print("=" * 80)

# 检查是否真正收敛
if result1['converged']:
    print(f" 求解器报告已收敛")
else:
    print(f" 求解器报告未收敛！")

print(f"  最终误差: {result1['final_error']*100:.4f}%")
print(f"  目标容差: {0.001*100:.4f}%")

# 检查流量守恒
Q_diff = np.diff(Q1)
max_diff = np.max(np.abs(Q_diff))
print(f"\n流量守恒性:")
print(f"  相邻点最大流量差: {max_diff:.6f} m³/s")
print(f"  相对于目标流量: {max_diff/Q_initial*100:.4f}%")

# ==================== 关键发现 ====================
print(f"\n" + "=" * 80)
print("关键发现")
print("=" * 80)

if Q1_max_error > 5.0:
    print(f"️  误差过大 ({Q1_max_error:.2f}%)，可能原因:")
    print(f"  1. 求解器未真正收敛")
    print(f"  2. 闸门参数配置导致数值不稳定")
    print(f"  3. 网格分辨率不足")
elif Q1_max_error > 1.0:
    print(f"️  误差较大 ({Q1_max_error:.2f}%)，主要问题:")
    print(f"  1. 闸门附近流量不守恒")
    print(f"  2. 需要更细的收敛容差")
else:
    print(f" 误差在可接受范围 ({Q1_max_error:.2f}%)")

print(f"\n建议:")
if not result1['converged']:
    print(f"  - 增加最大迭代次数")
    print(f"  - 降低收敛容差")
elif Q1_max_error > 2.0:
    print(f"  - 检查闸门开度配置是否合理")
    print(f"  - 考虑使用更密的网格")
    print(f"  - 优化闸门内部边界条件算法")

print("\n" + "=" * 80)
