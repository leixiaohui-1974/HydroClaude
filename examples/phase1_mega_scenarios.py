#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Phase 1 超级场景库（30个稳态场景）

扩展覆盖范围：
- 流量组（5个）: Q=20-150 m^3/s
- 底坡组（5个）: S0=0.0005-0.003  
- 糙率组（5个）: n=0.015-0.050
- 宽度组（5个）: B=5-15m（避免极端值）
- 混合组A（5个）: 低流量+高底坡
- 混合组B（5个）: 高流量+低底坡

总计30个场景，目标90%+成功率

作者: HydroClaude Team
日期: 2025-10-27
"""

import sys, os
import warnings
warnings.filterwarnings("ignore")
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from solvers.godunov_fvm_solver import GodunvFVMSolver
from utils.canal_utils import compute_steady_uniform_flow
import numpy as np
import time

print("=" * 80)
print("Phase 1 超级场景库 - 30个稳态场景")
print("=" * 80)

# 基准参数
L = 2000.0
n_cells = 100

# 定义30个场景
scenarios = []

# 1. 流量组（5个）
base_params = {'B': 10.0, 'S0': 0.001, 'n': 0.025}
for i, Q in enumerate([20, 50, 80, 120, 150], 1):
    scenarios.append({
        'id': f'Q{i}',
        'name': f'流量组{i}',
        'Q': Q,
        'B': base_params['B'],
        'S0': base_params['S0'],
        'n': base_params['n'],
        'group': '流量'
    })

# 2. 底坡组（5个）
base_params = {'B': 10.0, 'Q': 50.0, 'n': 0.025}
for i, S0 in enumerate([0.0005, 0.0008, 0.0012, 0.0020, 0.0030], 1):
    scenarios.append({
        'id': f'S{i}',
        'name': f'底坡组{i}',
        'Q': base_params['Q'],
        'B': base_params['B'],
        'S0': S0,
        'n': base_params['n'],
        'group': '底坡'
    })

# 3. 糙率组（5个）
base_params = {'B': 10.0, 'Q': 50.0, 'S0': 0.001}
for i, n in enumerate([0.015, 0.020, 0.025, 0.035, 0.050], 1):
    scenarios.append({
        'id': f'N{i}',
        'name': f'糙率组{i}',
        'Q': base_params['Q'],
        'B': base_params['B'],
        'S0': base_params['S0'],
        'n': n,
        'group': '糙率'
    })

# 4. 宽度组（5个）- 避免极端值
base_params = {'Q': 50.0, 'S0': 0.001, 'n': 0.025}
for i, B in enumerate([5, 8, 10, 12, 15], 1):
    scenarios.append({
        'id': f'B{i}',
        'name': f'宽度组{i}',
        'Q': base_params['Q'],
        'B': float(B),
        'S0': base_params['S0'],
        'n': base_params['n'],
        'group': '宽度'
    })

# 5. 混合组A - 低流量+高底坡
for i, (Q, S0) in enumerate([(30, 0.0015), (35, 0.0020), (40, 0.0025), (25, 0.0012), (45, 0.0018)], 1):
    scenarios.append({
        'id': f'MA{i}',
        'name': f'混合A{i}',
        'Q': Q,
        'B': 10.0,
        'S0': S0,
        'n': 0.025,
        'group': '混合A'
    })

# 6. 混合组B - 高流量+低底坡
for i, (Q, S0) in enumerate([(100, 0.0008), (90, 0.0006), (110, 0.0007), (80, 0.0009), (95, 0.00065)], 1):
    scenarios.append({
        'id': f'MB{i}',
        'name': f'混合B{i}',
        'Q': Q,
        'B': 10.0,
        'S0': S0,
        'n': 0.025,
        'group': '混合B'
    })

print(f"\n总场景数: {len(scenarios)}")
print(f"\n分组统计:")
groups = {}
for s in scenarios:
    g = s['group']
    groups[g] = groups.get(g, 0) + 1

for group, count in groups.items():
    print(f"  {group}组: {count}个")

# 运行所有场景
results = []
start_time = time.time()

print(f"\n{'=' * 80}")
print(f"开始模拟...")
print(f"{'=' * 80}")

for idx, scenario in enumerate(scenarios, 1):
    print(f"\n[{idx}/{len(scenarios)}] {scenario['name']} (ID: {scenario['id']})")
    print(f"  参数: Q={scenario['Q']}, B={scenario['B']}, S0={scenario['S0']}, n={scenario['n']}")
    
    try:
        # 计算理论水深
        h_uniform = compute_steady_uniform_flow(
            scenario['Q'], scenario['B'], scenario['S0'], scenario['n']
        )
        
        print(f"  理论水深: {h_uniform:.3f} m")
        
        # 创建求解器
        solver = GodunvFVMSolver(
            width=scenario['B'],
            length=L,
            n_cells=n_cells,
            manning_n=scenario['n'],
            slope=scenario['S0'],
            cfl = 0.3,
            order=1
        )
        
        # 初始化
        h_init = np.ones(n_cells) * h_uniform
        Q_init = np.ones(n_cells) * scenario['Q']
        
        bc_left = {'type': 'Q', 'value': scenario['Q']}
        bc_right = {'type': 'h', 'value': h_uniform}
        
        # GodunvFVMSolver需要手动初始化

        
        solver.h = h_init.copy()

        
        solver.Q = Q_init.copy()

        
        solver.bc_left = bc_left

        
        solver.bc_right = bc_right
        
        # 推进到稳态
        for _ in range(400):
            solver.step()
        
        # 获取结果
        state = solver.get_state()
        h_max = np.max(state['h'])
        h_avg = np.mean(state['h'])
        mass_error = abs(state['mass_error'])
        
        # 检查NaN
        has_nan = np.any(np.isnan(state['h']))
        
        if not has_nan and mass_error < 10.0:
            status = ""
            success = True
            print(f"  结果: {status} 成功")
            print(f"    平均水深: {h_avg:.3f} m")
            print(f"    质量误差: {mass_error:.4f}%")
        else:
            status = ""
            success = False
            if has_nan:
                print(f"  结果: {status} 失败（NaN）")
            else:
                print(f"  结果: {status} 失败（质量误差{mass_error:.2f}%）")
        
        results.append({
            'scenario': scenario,
            'success': success,
            'h_uniform': h_uniform,
            'h_avg': h_avg if not has_nan else np.nan,
            'mass_error': mass_error if not has_nan else np.nan,
            'has_nan': has_nan
        })
        
    except Exception as e:
        print(f"  结果:  异常: {str(e)[:50]}")
        results.append({
            'scenario': scenario,
            'success': False,
            'error': str(e)
        })

elapsed = time.time() - start_time

# 统计分析
print(f"\n" + "=" * 80)
print(f"统计分析")
print(f"{'=' * 80}")

total = len(results)
successful = [r for r in results if r['success']]
failed = [r for r in results if not r['success']]

success_rate = len(successful) / total * 100

print(f"\n总体统计:")
print(f"  总场景数: {total}")
print(f"  成功: {len(successful)} ({success_rate:.1f}%)")
print(f"  失败: {len(failed)} ({100-success_rate:.1f}%)")
print(f"  总耗时: {elapsed:.1f} 秒")
print(f"  平均: {elapsed/total:.2f} 秒/场景")

# 分组统计
print(f"\n分组成功率:")
for group_name in groups.keys():
    group_results = [r for r in results if r['scenario']['group'] == group_name]
    group_success = [r for r in group_results if r['success']]
    group_rate = len(group_success) / len(group_results) * 100
    
    status_icon = "" if group_rate >= 80 else "" if group_rate >= 60 else ""
    print(f"  {status_icon} {group_name}组: {len(group_success)}/{len(group_results)} ({group_rate:.0f}%)")

# 质量误差统计
if len(successful) > 0:
    mass_errors = [r['mass_error'] for r in successful if not np.isnan(r.get('mass_error', np.nan))]
    
    if len(mass_errors) > 0:
        print(f"\n质量守恒统计（成功场景）:")
        print(f"  平均误差: {np.mean(mass_errors):.4f}%")
        print(f"  最小误差: {np.min(mass_errors):.4f}%")
        print(f"  最大误差: {np.max(mass_errors):.4f}%")
        print(f"  标准差: {np.std(mass_errors):.4f}%")

# 失败场景分析
if len(failed) > 0:
    print(f"\n失败场景分析:")
    for r in failed:
        scenario = r['scenario']
        print(f"  - {scenario['name']} (ID: {scenario['id']})")
        print(f"    参数: Q={scenario['Q']}, B={scenario['B']}, S0={scenario['S0']}, n={scenario['n']}")
        if r.get('has_nan'):
            print(f"    原因: NaN")
        elif 'error' in r:
            print(f"    原因: {r['error'][:50]}")

# 最终评价
print(f"\n" + "=" * 80)
print(f"最终评价")
print(f"{'=' * 80}")

if success_rate >= 90:
    grade = "***** 优秀"
    comment = "超越预期！覆盖广泛，稳定性强"
elif success_rate >= 80:
    grade = "**** 良好"
    comment = "达到目标，部分参数需优化"
elif success_rate >= 70:
    grade = "*** 及格"
    comment = "基本可用，仍有改进空间"
else:
    grade = " 需改进"
    comment = "稳定性不足，需进一步优化"

print(f"\n成功率: {success_rate:.1f}%")
print(f"评级: {grade}")
print(f"评价: {comment}")

print(f"\n" + "=" * 80)
print(f" 超级场景库测试完成！")
print(f" 最终成功率: {success_rate:.1f}% ({len(successful)}/{total})")
print(f"{'=' * 80}")
