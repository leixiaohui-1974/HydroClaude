"""
Preissmann求解器参数优化

系统性测试不同参数组合，寻找最优精度配置
"""

import numpy as np
import sys
import os
from itertools import product

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))

from physics.canal import Canal

def test_preissmann_config(n_sections: int, dt: float, theta: float,
                          Q_in: float = 22.0, Q_out: float = 20.0,
                          sim_time: float = 500.0):
    """测试单个Preissmann配置"""

    # 创建Canal
    canal = Canal(
        name=f"preissmann_n{n_sections}_dt{dt}_theta{theta}",
        volume_min=0.0,
        volume_max=1000 * 10 * 10,
        area=10 * 2.5,
        length=1000.0,
        slope=0.001,
        n_sections=n_sections,
        method='preissmann',
        manning_n=0.025,
        width=10.0,
        initial_depth=2.5,
        initial_flow=20.0
    )

    # 修改theta参数（需要访问solver）
    if hasattr(canal, 'solver'):
        canal.solver.theta = theta

    # 运行仿真
    n_steps = int(sim_time / dt)
    initial_h = np.mean(canal.hydraulic_state.h)

    for k in range(n_steps):
        inputs = {
            'upstream_flow': Q_in,
            'downstream_flow': Q_out
        }
        try:
            canal.update_high_fidelity(dt, inputs)
        except Exception as e:
            return {
                'n_sections': n_sections,
                'dt': dt,
                'theta': theta,
                'error': float('inf'),
                'error_pct': float('inf'),
                'converged': False,
                'error_msg': str(e)
            }

    # 计算误差
    final_h = np.mean(canal.hydraulic_state.h)
    actual_delta_h = final_h - initial_h

    width = 10.0
    length = 1000.0
    area_total = width * length
    volume_added = (Q_in - Q_out) * sim_time
    expected_delta_h = volume_added / area_total

    h_error = abs(actual_delta_h - expected_delta_h)
    h_error_pct = h_error / expected_delta_h * 100

    return {
        'n_sections': n_sections,
        'dt': dt,
        'theta': theta,
        'actual_dh': actual_delta_h,
        'expected_dh': expected_delta_h,
        'error': h_error,
        'error_pct': h_error_pct,
        'converged': True
    }

print("="*80)
print("Preissmann求解器参数优化")
print("="*80)

# 参数范围
n_sections_list = [21, 51, 101, 201]  # 空间离散
dt_list = [20.0, 10.0, 5.0, 2.5]      # 时间步长
theta_list = [0.50, 0.55, 0.60, 0.65, 0.70]  # 时间加权

print(f"\n测试参数空间:")
print(f"  n_sections: {n_sections_list}")
print(f"  dt: {dt_list}")
print(f"  theta: {theta_list}")
print(f"  总配置数: {len(n_sections_list) * len(dt_list) * len(theta_list)}")

# 测试所有组合
results = []
total_configs = len(n_sections_list) * len(dt_list) * len(theta_list)
config_idx = 0

print("\n开始测试...")
print("-"*80)

for n_sections, dt, theta in product(n_sections_list, dt_list, theta_list):
    config_idx += 1
    print(f"[{config_idx}/{total_configs}] 测试 n={n_sections}, dt={dt}s, theta={theta}...", end='')

    result = test_preissmann_config(n_sections, dt, theta)
    results.append(result)

    if result['converged']:
        print(f" 误差={result['error_pct']:.1f}%")
    else:
        print(f" ❌ 失败: {result['error_msg']}")

print("-"*80)

# 排序并显示Top 10
results_sorted = sorted([r for r in results if r['converged']],
                       key=lambda x: x['error_pct'])

print("\n🏆 Top 10 最优配置:")
print("-"*80)
print(f"{'排名':<5} {'n_sections':<12} {'dt(s)':<8} {'theta':<8} {'误差%':<10} {'实际Δh':<10}")
print("-"*80)

for i, r in enumerate(results_sorted[:10], 1):
    print(f"{i:<5} {r['n_sections']:<12} {r['dt']:<8.1f} {r['theta']:<8.2f} "
          f"{r['error_pct']:<10.2f} {r['actual_dh']:<10.4f}m")

print("\n"+"="*80)
print("最优配置:")
best = results_sorted[0]
print(f"  n_sections = {best['n_sections']}")
print(f"  dt = {best['dt']}s")
print(f"  theta = {best['theta']}")
print(f"  误差 = {best['error_pct']:.2f}%")
print(f"  实际Δh = {best['actual_dh']:.4f}m (理论 {best['expected_dh']:.4f}m)")

# 对比基准配置
baseline = next((r for r in results if r['n_sections']==51 and r['dt']==10.0 and r['theta']==0.60), None)
if baseline and baseline['converged']:
    improvement = baseline['error_pct'] - best['error_pct']
    improvement_pct = improvement / baseline['error_pct'] * 100
    print(f"\n相对基准配置改进:")
    print(f"  基准误差: {baseline['error_pct']:.2f}%")
    print(f"  最优误差: {best['error_pct']:.2f}%")
    print(f"  改进: {improvement:.2f}个百分点 ({improvement_pct:.1f}% 改善)")

print("="*80)

# 保存结果
import json
with open('preissmann_optimization_results.json', 'w') as f:
    json.dump(results, f, indent=2)
print("\n✅ 详细结果已保存到: preissmann_optimization_results.json")
