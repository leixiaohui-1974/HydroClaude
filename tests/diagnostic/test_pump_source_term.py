#!/usr/bin/env python3
"""
测试泵站源项是否正确工作
"""

import sys
import numpy as np
sys.path.insert(0, '/workspace')

try:
    from solvers.hydrostatic_canal_solver import HydrostaticCanalSolver
except ImportError as e:
    print(f"Import error: {e}")
    print("Make sure project root is in sys.path")
    sys.exit(1)

from solvers.gate import PumpStation

print("=" * 80)
print("泵站源项法调试测试")
print("=" * 80)

# 创建简单测试案例
L = 10000  # 10km
nx = 51    # 51个点
pump_pos = 5000  # 中间

solver = HydrostaticCanalSolver(
    length=L,
    nx=nx,
    B=10.0,
    S0=0.0001,
    n=0.025,
    internal_structures=[(pump_pos, PumpStation(position=pump_pos, width=10.0, rated_flow=10.0, rated_head=5.0))]
)

# 设置均匀流初始条件
solver.h[:] = 2.0
solver.hu[:] = 1.0  # Q=10 m^3/s

pump_idx = np.argmin(np.abs(solver.x - pump_pos))
print(f"\n泵站信息:")
print(f"  位置: {pump_pos/1000:.1f} km")
print(f"  索引: {pump_idx}")
print(f"  额定扬程: 5.0 m")

# 计算通量和源项
h_test = solver.h.copy()
hu_test = solver.hu.copy()
z_test = solver.z.copy()
dx_test = solver.dx

F_mass, F_momentum, S_mass, S_momentum = solver.compute_fluxes_and_sources(
    h_test, hu_test, z_test, dx_test
)

print(f"\n源项检查:")
print(f"  dx = {dx_test:.1f} m")
print(f"  预期源项强度: S_pump = g * H / dx = {solver.g * 5.0 / dx_test:.4f} N/m^3")

# 检查泵站附近的源项
print(f"\n泵站附近的动量源项:")
print(f"  {'索引':<8} {'位置(km)':<12} {'S_momentum':<15} {'说明'}")
print("-" * 60)
for i in range(max(0, pump_idx-3), min(nx, pump_idx+4)):
    label = ""
    if i == pump_idx - 1:
        label = "上游邻居"
    elif i == pump_idx:
        label = "泵站 ⭐"
    elif i == pump_idx + 1:
        label = "下游邻居"
    
    print(f"  {i:<8} {solver.x[i]/1000:<12.3f} {S_momentum[i]:<15.6f} {label}")

# 检查是否有非零源项
pump_source = S_momentum[pump_idx]
print(f"\n源项诊断:")
if abs(pump_source) > 1e-6:
    print(f"   泵站源项已添加: {pump_source:.6f} N/m^3")
    print(f"  源项占比: {abs(pump_source) / (abs(S_momentum).max() + 1e-10) * 100:.1f}%")
else:
    print(f"   泵站源项为零或极小")
    print(f"  可能原因:")
    print(f"    1. 泵站索引不在有效范围")
    print(f"    2. 泵站未被识别为运行状态")
    print(f"    3. 源项计算逻辑有问题")

# 检查泵站是否被正确识别
print(f"\n泵站状态检查:")
print(f"  structure_indices: {solver.structure_indices}")
print(f"  structure_objects: {solver.structure_objects}")
if solver.structure_objects:
    pump = solver.structure_objects[0]
    print(f"  泵站类型: {type(pump).__name__}")
    print(f"  is_running: {pump.is_running}")
    print(f"  rated_head: {pump.rated_head}")

print("=" * 80)
