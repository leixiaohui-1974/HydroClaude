# -*- coding: utf-8 -*-
"""
测试HighOrderCanalSolver的精度

对比HighOrderCanalSolver与Canal类中的其他求解器
"""

import numpy as np
import sys
import os

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))

from solvers.high_order_solver import HighOrderCanalSolver
from physics.canal import Canal

print("="*80)
print("HighOrderCanalSolver精度测试")
print("="*80)

# 测试配置
canal_length = 1000.0
canal_width = 10.0
initial_depth = 2.5
initial_flow = 20.0
Q_in = 22.0
Q_out = 20.0
dt = 10.0
sim_time = 500.0
n_steps = int(sim_time / dt)

# 理论水位变化
volume_added = (Q_in - Q_out) * sim_time
area_total = canal_width * canal_length
expected_delta_h = volume_added / area_total

print(f"\n测试配置:")
print(f"  渠道长度: {canal_length}m")
print(f"  渠道宽度: {canal_width}m")
print(f"  初始水深: {initial_depth}m")
print(f"  入流: {Q_in} m^3/s")
print(f"  出流: {Q_out} m^3/s")
print(f"  净入流: {Q_in - Q_out} m^3/s")
print(f"  仿真时间: {sim_time}s")
print(f"  理论Deltah: {expected_delta_h:.4f}m")

# ========== 测试1: HighOrderCanalSolverMUSCL+RK2 ==========
print("\n" + "="*80)
print("测试1: HighOrderCanalSolver (MUSCL+RK2)")
print("="*80)

solver_ho = HighOrderCanalSolver(
    length=canal_length,
    nx=51,  # 与Canal默认的n_sections一致
    B=canal_width,
    S0=0.001,
    n=0.025,
    muscl_limiter='minmod'
)

# 初始条件
solver_ho.h = np.ones(51) * initial_depth
solver_ho.hu = np.ones(51) * initial_flow / canal_width  # hu = Q/B

# 边界条件
def Q_upstream_func(t):
    return Q_in

def h_downstream_func(t):
    # 使用流量推算水深简化假设恒定流速
    # Q = V*A = V*B*h
    # 对于已知Q_out假设流速 V ~= initial_flow / (width * initial_depth)
    V_est = initial_flow / (canal_width * initial_depth)
    if V_est > 0:
        h_est = Q_out / (canal_width * V_est)
    else:
        h_est = initial_depth
    return h_est

# 运行瞬态求解
result_ho = solver_ho.solve_transient_high_order(
    t_end=sim_time,
    dt=dt,
    Q_upstream_func=Q_upstream_func,
    h_downstream_func=h_downstream_func,
    save_interval=1,
    use_muscl=True,
    use_rk2=True,
    verbose=False
)

initial_h_ho = initial_depth
final_h_ho = np.mean(result_ho['h_final'])
actual_delta_h_ho = final_h_ho - initial_h_ho

h_error_ho = abs(actual_delta_h_ho - expected_delta_h)
h_error_pct_ho = h_error_ho / expected_delta_h * 100

print(f"   测试完成")
print(f"     理论Deltah: {expected_delta_h:.4f}m")
print(f"     实际Deltah: {actual_delta_h_ho:.4f}m")
print(f"     误差: {h_error_ho:.4f}m ({h_error_pct_ho:.1f}%)")
print(f"     质量守恒误差: {h_error_pct_ho:.1f}%")

# ========== 测试2: HighOrderCanalSolver一阶方法 ==========
print("\n" + "="*80)
print("测试2: HighOrderCanalSolver (1st-order)")
print("="*80)

solver_1st = HighOrderCanalSolver(
    length=canal_length,
    nx=51,
    B=canal_width,
    S0=0.001,
    n=0.025,
    muscl_limiter='minmod'
)

# 初始条件
solver_1st.h = np.ones(51) * initial_depth
solver_1st.hu = np.ones(51) * initial_flow / canal_width

# 运行瞬态求解使用一阶方法
result_1st = solver_1st.solve_transient_high_order(
    t_end=sim_time,
    dt=dt,
    Q_upstream_func=Q_upstream_func,
    h_downstream_func=h_downstream_func,
    save_interval=1,
    use_muscl=False,  # 关闭MUSCL
    use_rk2=False,    # 关闭RK2
    verbose=False
)

initial_h_1st = initial_depth
final_h_1st = np.mean(result_1st['h_final'])
actual_delta_h_1st = final_h_1st - initial_h_1st

h_error_1st = abs(actual_delta_h_1st - expected_delta_h)
h_error_pct_1st = h_error_1st / expected_delta_h * 100

print(f"   测试完成")
print(f"     理论Deltah: {expected_delta_h:.4f}m")
print(f"     实际Deltah: {actual_delta_h_1st:.4f}m")
print(f"     误差: {h_error_1st:.4f}m ({h_error_pct_1st:.1f}%)")
print(f"     质量守恒误差: {h_error_pct_1st:.1f}%")

# ========== 测试3: Canal类的Preissmann求解器对比基准 ==========
print("\n" + "="*80)
print("测试3: Canal Preissmann (基准)")
print("="*80)

canal_preissmann = Canal(
    name="test_preissmann",
    volume_min=0.0,
    volume_max=canal_length * canal_width * 10,
    area=canal_width * initial_depth,
    length=canal_length,
    slope=0.001,
    n_sections=51,
    method='preissmann',
    manning_n=0.025,
    width=canal_width,
    initial_depth=initial_depth,
    initial_flow=initial_flow
)

initial_h_preissmann = np.mean(canal_preissmann.hydraulic_state.h)

for k in range(n_steps):
    inputs = {
        'upstream_flow': Q_in,
        'downstream_flow': Q_out
    }
    canal_preissmann.update_high_fidelity(dt, inputs)

final_h_preissmann = np.mean(canal_preissmann.hydraulic_state.h)
actual_delta_h_preissmann = final_h_preissmann - initial_h_preissmann

h_error_preissmann = abs(actual_delta_h_preissmann - expected_delta_h)
h_error_pct_preissmann = h_error_preissmann / expected_delta_h * 100

print(f"   测试完成")
print(f"     理论Deltah: {expected_delta_h:.4f}m")
print(f"     实际Deltah: {actual_delta_h_preissmann:.4f}m")
print(f"     误差: {h_error_preissmann:.4f}m ({h_error_pct_preissmann:.1f}%)")
print(f"     质量守恒误差: {h_error_pct_preissmann:.1f}%")

# ========== 精度排名 ==========
print("\n" + "="*80)
print("精度对比排名")
print("="*80)

results = [
    ("HighOrderCanalSolver (MUSCL+RK2)", h_error_pct_ho, h_error_ho),
    ("HighOrderCanalSolver (1st-order)", h_error_pct_1st, h_error_1st),
    ("Canal Preissmann", h_error_pct_preissmann, h_error_preissmann)
]

results_sorted = sorted(results, key=lambda x: x[1])

for i, (name, error_pct, error_m) in enumerate(results_sorted, 1):
    stars = "" * max(1, 6 - i)
    print(f"  {i}. {name:<40} {error_pct:>7.1f}% ({error_m:.4f}m) {stars}")

print("\n" + "="*80)
best_name, best_error_pct, _ = results_sorted[0]
print(f" 最优求解器: {best_name}")
print(f"   误差: {best_error_pct:.1f}%")
print("="*80)

# 保存结果
import json
output_data = {
    "HighOrderCanalSolver_MUSCL_RK2": {
        "error_pct": float(h_error_pct_ho),
        "actual_dh": float(actual_delta_h_ho),
        "expected_dh": float(expected_delta_h)
    },
    "HighOrderCanalSolver_1st_order": {
        "error_pct": float(h_error_pct_1st),
        "actual_dh": float(actual_delta_h_1st),
        "expected_dh": float(expected_delta_h)
    },
    "Canal_Preissmann": {
        "error_pct": float(h_error_pct_preissmann),
        "actual_dh": float(actual_delta_h_preissmann),
        "expected_dh": float(expected_delta_h)
    }
}

with open('high_order_solver_test_results.json', 'w', encoding='utf-8') as f:
    json.dump(output_data, f, indent=2)

print("\n 详细结果已保存到: high_order_solver_test_results.json")
